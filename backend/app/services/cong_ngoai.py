"""CG-1 · Cổng kết nối VTD — đăng nhập bằng MÃ MỘT LẦN cho khách hàng, đối tác, cổ đông.

Chủ tịch duyệt bản xem thử 26/10/2026; kênh nhận mã: Zalo (ZNS) hoặc Email, người dùng tự chọn.

BỐN ĐIỀU KHÔNG ĐƯỢC LỎNG
  1. PHIÊN NGOÀI KÝ BẰNG KHOÁ KHÁC phiên nhân viên. `deps.current_user` giải mã bằng SECRET_KEY nên một
     phiên cổng ngoài đưa vào bất kỳ cửa nội bộ nào cũng là chữ ký sai → 401. Không có "chặn bằng vai
     trò" nào để quên.
  2. Mã lưu dưới dạng BĂM (HMAC theo khoá máy chủ + mã phiên gửi), dùng MỘT lần, sống 5 phút, sai 5
     lần là chết. Mỗi liên hệ tối đa 5 lần gửi mỗi giờ.
  3. Không thành máy dò: gửi mã trả cùng một câu dù liên hệ đã có tài khoản hay chưa.
  4. Kênh chưa cấu hình thì NÓI RA, không giả vờ đã gửi. Không gửi được thì không có mã nào sống.

Đối tác và cổ đông xác thực liên hệ xong mới chỉ có quyền GỬI HỒ SƠ. Vào được không gian riêng khi
người có thẩm quyền trên VTOS duyệt (NGUOI_DUYET). Khách hàng lần đầu phải đồng ý điều khoản dịch vụ;
không bao giờ tự bật nhận tin quảng cáo.
"""
import base64
import hashlib
import hmac
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.core import User, ROLES
from app.models.cong_ngoai import (TaiKhoanNgoai, MaXacThucNgoai, DonDangKy, MayDaNho,
                                   LOAI_NGOAI, LOAI_DOI_TAC, TRANG_THAI_NGOAI, KENH_MA)
from app.services import rules as R

SONG_MA_PHUT = 5
SAI_TOI_DA = 5
# DK-1 · Chủ tịch chốt 01/11/2026: tối thiểu 5 ký tự, KHÔNG bắt viết hoa, không bắt trộn số
# hay ký hiệu. Chuẩn NIST SP 800-63B đòi 15 cho mật khẩu đứng một mình — chỗ lệch ấy ghi
# trong sổ và bù bằng luật hỏi mã ở máy lạ (DK-2). Luật "phải có một chữ hoa" BỎ có lý do:
# ai cũng viết hoa chữ đầu, nên nó làm mật khẩu khó nhớ mà không khó đoán.
MK_TOI_THIEU = 5
MK_TOI_DA = 64
DON_SONG_GIO = 24
# DK-2 · vế sau của điều 6: mật khẩu ngắn thì máy phải quen. Mật khẩu từ 15 ký tự trở lên
# (mức chuẩn NIST đòi cho mật khẩu đứng một mình) thì cổng Khách hàng bỏ qua bước máy lạ;
# cổng Đối tác và Cổ đông thì LUÔN hỏi, kể cả mật khẩu dài — họ thấy công nợ và tài liệu
# chưa công bố.
NHO_MAY_NGAY = 90
NHO_MAY_TOI_DA = 5
MK_DU_DAI_KHOI_HOI = 15
DN_SAI_TOI_DA = 10
DN_KHOA_PHUT = 15
GUI_TOI_DA_MOI_GIO = 5
PHIEN_GIO = 12
AUD = "vtd-cong"
MUC_ZNS = "ma_xac_thuc"           # mục trong ZALO_ZNS_TEMPLATES: "ma_xac_thuc:<template_id>"

# Ai xử lý hồ sơ nào. Chủ tịch, TGĐ xử lý tất cả. Ban Kiểm soát chỉ xem (vai chỉ đọc bị chặn ghi ở
# tầng chung). Khách hàng không cần duyệt — chỉ có khoá / mở khoá, do Chủ tịch, TGĐ.
TOAN_QUYEN = ("chutich", "tgd")
NGUOI_DUYET = {
    ("doi_tac", "ncc"): ("tp_dh", "gd_kd"),
    ("doi_tac", "dai_ly"): ("gd_kd",),
    ("doi_tac", "ctv_ban_hang"): ("gd_kd",),
    ("doi_tac", ""): ("tp_dh", "gd_kd"),
    ("co_dong", ""): ("ir_phapche",),
}
CHI_XEM = ("bks", "robot_ks")
VAI_XEM = tuple(dict.fromkeys(TOAN_QUYEN + CHI_XEM + tuple(v for vs in NGUOI_DUYET.values() for v in vs)))


class LoiCong(ValueError):
    """Lỗi người dùng đọc được. `ma` để giao diện rẽ nhánh (ví dụ can_dong_y)."""
    def __init__(self, thong_diep: str, ma: str = "", status: int = 422):
        super().__init__(thong_diep)
        self.ma, self.status = ma, status


# ---------------------------------------------------------------- liên hệ

def chuan_lien_he(lh: str) -> tuple[str, str]:
    """("dien_thoai", "0912345678") hoặc ("email", "ten@x.vn")."""
    s = (lh or "").strip()
    if "@" in s:
        e = s.lower()
        if not re.fullmatch(r"[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}", e) or len(e) > 160:
            raise LoiCong("Email chưa đúng định dạng")
        return "email", e
    from app.services.zalo import norm_phone
    p = norm_phone(s)
    if not re.fullmatch(r"0\d{9}", p):
        raise LoiCong("Số điện thoại chưa đúng — nhập 10 số, ví dụ 0912345678")
    return "dien_thoai", p


def che(lh: str) -> str:
    if "@" in lh:
        a, b = lh.split("@", 1)
        return (a[:2] + "•••") + "@" + b
    return lh[:3] + "•••••" + lh[-2:]


# ---------------------------------------------------------------- kênh gửi

def kenh_san_sang(db: Session | None = None) -> dict:
    """{kenh: {"ok": bool, "ly_do": str}} — giao diện khoá nút kênh chưa cấu hình."""
    from app.services import zalo as Z
    try:
        cfg = Z.configured(db)
        co_oa, mau = bool(cfg.get("oa")), (cfg.get("zns_templates") or {}).get(MUC_ZNS, "")
    except Exception:            # bảng token chưa có (máy mới) — coi như chưa cấu hình
        co_oa, mau = False, ""
    zalo_ly = "" if (co_oa and mau) else (
        "Chưa có mẫu tin mã xác thực đã duyệt trên Zalo (mục ma_xac_thuc trong ZALO_ZNS_TEMPLATES)" if co_oa
        else "Chưa nối Zalo OA với VTOS")
    email_ok = bool(settings.SMTP_HOST and settings.SMTP_FROM)
    return {"zalo": {"ok": not zalo_ly, "ly_do": zalo_ly, "ten": "Zalo", "cho": "dien_thoai"},
            "email": {"ok": email_ok, "ly_do": "" if email_ok else "Chưa cấu hình hộp thư gửi (SMTP) trên máy chủ",
                      "ten": "Email", "cho": "email"}}


def _gui_zalo(db: Session, dien_thoai: str, ma: str) -> None:
    from app.services import zalo as Z
    mau = Z.configured(db)["zns_templates"][MUC_ZNS]
    j = Z.send_zns(db, dien_thoai, mau, {"otp": ma})
    if j.get("error") not in (0, None):
        raise RuntimeError(f"Zalo từ chối gửi: {j.get('message') or j.get('error')}")


def _gui_email(db: Session, email: str, ma: str) -> None:
    import smtplib
    from email.message import EmailMessage
    m = EmailMessage()
    m["Subject"] = f"Mã xác thực Vietourist: {ma}"
    m["From"], m["To"] = settings.SMTP_FROM, email
    m.set_content(f"Mã xác thực của bạn là {ma}. Mã dùng một lần, hết hạn sau {SONG_MA_PHUT} phút.\n"
                  "Vietourist không bao giờ hỏi mã này qua điện thoại. Nếu bạn không yêu cầu, hãy bỏ qua email này.\n\n"
                  f"{settings.COMPANY_NAME}")
    cls = smtplib.SMTP_SSL if settings.SMTP_SSL else smtplib.SMTP
    with cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
        if not settings.SMTP_SSL:
            s.starttls()
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.send_message(m)


# Phép thử thay hai hàm này bằng hàm ghi lại mã; mã thật không bao giờ trả về trình duyệt.
GUI = {"zalo": _gui_zalo, "email": _gui_email}


def _bam(khoa: str, ma: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{khoa}:{ma}".encode(), hashlib.sha256).hexdigest()


def gui_ma(db: Session, loai: str, lien_he: str, kenh: str, ip: str = "", now: datetime | None = None) -> dict:
    now = now or datetime.now()
    if loai not in LOAI_NGOAI:
        raise LoiCong("Cổng không hợp lệ")
    if kenh not in KENH_MA:
        raise LoiCong("Kênh nhận mã không hợp lệ")
    kieu, lh = chuan_lien_he(lien_he)
    can = kenh_san_sang(db)[kenh]
    if kieu != can["cho"]:
        raise LoiCong("Nhận mã qua Zalo thì nhập số điện thoại; qua Email thì nhập địa chỉ email")
    if not can["ok"]:
        raise LoiCong(f"Kênh {can['ten']} chưa mở: {can['ly_do']}. Chọn kênh còn lại hoặc liên hệ Vietourist.",
                      ma="kenh_chua_mo", status=503)
    dem = db.execute(select(func.count(MaXacThucNgoai.id)).where(
        MaXacThucNgoai.lien_he == lh, MaXacThucNgoai.tao_luc > now - timedelta(hours=1))).scalar() or 0
    if dem >= GUI_TOI_DA_MOI_GIO:
        raise LoiCong("Đã gửi quá nhiều mã cho liên hệ này trong một giờ — thử lại sau", ma="qua_nhieu", status=429)
    khoa = secrets.token_urlsafe(24)
    ma = f"{secrets.randbelow(10 ** 6):06d}"
    try:
        GUI[kenh](db, lh, ma)
    except Exception as ex:      # không gửi được thì không lưu mã nào — không có mã "sống" mà không ai nhận
        import logging
        logging.getLogger("vtos.cong").warning("gui ma %s that bai: %s", kenh, str(ex)[:300])
        raise LoiCong(f"Chưa gửi được mã qua {can['ten']} — thử lại sau ít phút hoặc chọn kênh còn lại.",
                      ma="gui_loi", status=502)
    db.add(MaXacThucNgoai(khoa=khoa, loai=loai, kenh=kenh, lien_he=lh, ma_bam=_bam(khoa, ma),
                          het_han=now + timedelta(minutes=SONG_MA_PHUT), ip=(ip or "")[:64], tao_luc=now))
    db.commit()
    return {"khoa": khoa, "gui_toi": che(lh), "kenh": kenh, "het_han_giay": SONG_MA_PHUT * 60,
            "message": f"Đã gửi mã 6 số qua {can['ten']} tới {che(lh)}."}


# ---------------------------------------------------------------- phiên

def _khoa_ky() -> str:
    # Khoá RIÊNG cho phiên ngoài: phiên này đưa vào cửa nội bộ là chữ ký sai, không cần dòng chặn nào.
    return hashlib.sha256(f"{settings.SECRET_KEY}|vtd-cong-ngoai".encode()).hexdigest()


def cap_phien(tk: TaiKhoanNgoai) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=PHIEN_GIO)
    return jwt.encode({"sub": f"ngoai:{tk.id}", "loai": tk.loai, "ph": tk.phien, "aud": AUD, "exp": exp},
                      _khoa_ky(), algorithm="HS256")


def doc_phien(db: Session, token: str) -> TaiKhoanNgoai | None:
    try:
        d = jwt.decode(token or "", _khoa_ky(), algorithms=["HS256"], audience=AUD)
    except JWTError:
        return None
    sub = str(d.get("sub", ""))
    if not sub.startswith("ngoai:"):
        return None
    tk = db.get(TaiKhoanNgoai, int(sub.split(":", 1)[1]))
    if tk is None or tk.phien != d.get("ph") or tk.trang_thai in ("khoa", "tu_choi"):
        return None
    return tk


def xac_thuc(db: Session, khoa: str, ma: str, dong_y: bool = False, now: datetime | None = None) -> tuple[TaiKhoanNgoai, str]:
    now = now or datetime.now()
    c = db.execute(select(MaXacThucNgoai).where(MaXacThucNgoai.khoa == (khoa or ""))).scalars().first()
    if c is None or c.da_dung or c.het_han <= now or c.so_lan_sai >= SAI_TOI_DA:
        raise LoiCong("Mã đã hết hạn hoặc không còn dùng được — bấm Gửi lại mã", ma="ma_het")
    if not hmac.compare_digest(c.ma_bam, _bam(c.khoa, (ma or "").strip())):
        c.so_lan_sai += 1
        db.commit()
        con = SAI_TOI_DA - c.so_lan_sai
        raise LoiCong(f"Mã chưa đúng — còn {con} lần thử" if con > 0 else "Sai quá 5 lần — bấm Gửi lại mã",
                      ma="ma_sai" if con > 0 else "ma_het")
    cot = TaiKhoanNgoai.email if "@" in c.lien_he else TaiKhoanNgoai.dien_thoai
    tk = db.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.loai == c.loai, cot == c.lien_he)).scalars().first()
    if tk is not None and tk.trang_thai in ("khoa", "tu_choi"):
        c.da_dung = True; db.commit()
        raise LoiCong("Tài khoản này đang bị khoá hoặc hồ sơ đã bị từ chối — liên hệ Vietourist", ma="bi_khoa", status=403)
    if tk is None:
        if not dong_y:
            # KHÔNG tiêu mã: người dùng đồng ý điều khoản rồi gửi lại đúng mã này.
            raise LoiCong("Lần đầu dùng liên hệ này — đọc và đồng ý điều khoản dịch vụ để tạo tài khoản",
                          ma="can_dong_y", status=409)
        tk = TaiKhoanNgoai(loai=c.loai, trang_thai="hoat_dong" if c.loai == "khach_hang" else "ho_so",
                           dong_y_dieu_khoan_luc=now, tao_luc=now)
        if "@" in c.lien_he: tk.email = c.lien_he
        else: tk.dien_thoai = c.lien_he
        db.add(tk)
    c.da_dung = True
    tk.dang_nhap_cuoi, tk.kenh_ua_thich = now, c.kenh
    db.commit(); db.refresh(tk)
    return tk, cap_phien(tk)


def dang_xuat(db: Session, tk: TaiKhoanNgoai) -> None:
    tk.phien = (tk.phien or 1) + 1      # mọi phiên đang mở của tài khoản này mất hiệu lực
    db.commit()


# ---------------------------------------------------------------- hồ sơ (phía người dùng)

def toi_out(tk: TaiKhoanNgoai) -> dict:
    return {"id": tk.id, "loai": tk.loai, "loai_ten": LOAI_NGOAI[tk.loai], "ho_ten": tk.ho_ten,
            "dien_thoai": che(tk.dien_thoai) if tk.dien_thoai else "", "email": che(tk.email) if tk.email else "",
            "trang_thai": tk.trang_thai, "trang_thai_ten": TRANG_THAI_NGOAI.get(tk.trang_thai, tk.trang_thai),
            "loai_doi_tac": tk.loai_doi_tac, "ten_don_vi": tk.ten_don_vi, "ma_so_thue": tk.ma_so_thue,
            "tk_luu_ky": tk.tk_luu_ky, "ghi_chu_ho_so": tk.ghi_chu_ho_so, "ly_do": tk.ly_do,
            "nhan_tin_quang_cao": tk.nhan_tin_quang_cao, "kenh_ua_thich": tk.kenh_ua_thich,
            "gui_ho_so_luc": tk.gui_ho_so_luc, "dang_nhap_cuoi": tk.dang_nhap_cuoi,
            "loai_doi_tac_chon": LOAI_DOI_TAC, "da_noi": bool(tk.doi_tac_id)}


def cap_nhat_toi(db: Session, tk: TaiKhoanNgoai, ho_ten: str | None, nhan_tin: bool | None) -> TaiKhoanNgoai:
    if ho_ten is not None:
        tk.ho_ten = ho_ten.strip()[:160]
    if nhan_tin is not None:
        tk.nhan_tin_quang_cao = bool(nhan_tin)
    db.commit(); db.refresh(tk)
    return tk


def gui_ho_so(db: Session, tk: TaiKhoanNgoai, d: dict, now: datetime | None = None) -> TaiKhoanNgoai:
    if tk.loai == "khach_hang":
        raise LoiCong("Tài khoản khách hàng không cần gửi hồ sơ")
    if tk.trang_thai not in ("ho_so", "bo_sung"):
        raise LoiCong("Hồ sơ đang chờ duyệt hoặc đã được duyệt — không gửi lại được")
    ho_ten = (d.get("ho_ten") or "").strip()
    if not ho_ten:
        raise LoiCong("Ghi họ tên người đại diện / người đứng tên")
    if tk.loai == "doi_tac":
        if d.get("loai_doi_tac") not in LOAI_DOI_TAC:
            raise LoiCong("Chọn loại đối tác: nhà cung cấp, đại lý hoặc cộng tác viên bán hàng")
        if d.get("loai_doi_tac") != "ctv_ban_hang" and not (d.get("ten_don_vi") or "").strip():
            raise LoiCong("Ghi tên đơn vị")
        tk.loai_doi_tac = d["loai_doi_tac"]
        tk.ten_don_vi = (d.get("ten_don_vi") or "").strip()[:200]
        tk.ma_so_thue = re.sub(r"[^\d-]", "", d.get("ma_so_thue") or "")[:20]
    else:
        tk.ten_don_vi = (d.get("ten_don_vi") or "").strip()[:200]
        tk.giay_to = (d.get("giay_to") or "").strip()[:40]
        tk.tk_luu_ky = (d.get("tk_luu_ky") or "").strip()[:40]
        if not tk.giay_to:
            raise LoiCong("Ghi số CCCD hoặc mã số doanh nghiệp để IR đối chiếu sổ cổ đông")
    tk.ho_ten = ho_ten[:160]
    tk.ghi_chu_ho_so = (d.get("ghi_chu") or "").strip()[:2000]
    tk.trang_thai, tk.gui_ho_so_luc, tk.ly_do = "cho_duyet", now or datetime.now(), ""
    db.commit(); db.refresh(tk)
    return tk


# ---------------------------------------------------------------- phía VTOS (nhân viên)

def nguoi_duyet_cua(tk: TaiKhoanNgoai) -> tuple[str, ...]:
    if tk.loai == "khach_hang":
        return ()
    return NGUOI_DUYET.get((tk.loai, tk.loai_doi_tac if tk.loai == "doi_tac" else ""), NGUOI_DUYET[(tk.loai, "")])


def _vai(u: User) -> tuple[str, ...]:
    from app.services.vai_ke_thua import vai_va_cha
    return vai_va_cha(u.role)


def xem_duoc(u: User, tk: TaiKhoanNgoai) -> bool:
    v = _vai(u)
    return any(x in TOAN_QUYEN + CHI_XEM for x in v) or any(x in nguoi_duyet_cua(tk) for x in v)


def xu_ly_duoc(u: User, tk: TaiKhoanNgoai) -> bool:
    v = _vai(u)
    return any(x in TOAN_QUYEN for x in v) or any(x in nguoi_duyet_cua(tk) for x in v)


def quan_tri_out(tk: TaiKhoanNgoai, u: User) -> dict:
    d = toi_out(tk)
    d.update({"dien_thoai": tk.dien_thoai, "email": tk.email, "giay_to": tk.giay_to, "duyet_boi": tk.duyet_boi,
              "duyet_luc": tk.duyet_luc, "tao_luc": tk.tao_luc,
              "nguoi_duyet": [ROLES.get(x, x) for x in nguoi_duyet_cua(tk)],
              "xu_ly_duoc": xu_ly_duoc(u, tk), "doi_tac_id": tk.doi_tac_id,
              "loai_doi_tac_ten": LOAI_DOI_TAC.get(tk.loai_doi_tac, "")})
    return d


def danh_sach(db: Session, u: User, trang_thai: str = "") -> list[dict]:
    q = select(TaiKhoanNgoai).order_by(TaiKhoanNgoai.gui_ho_so_luc.desc().nullslast(), TaiKhoanNgoai.id.desc())
    if trang_thai:
        q = q.where(TaiKhoanNgoai.trang_thai == trang_thai)
    return [quan_tri_out(t, u) for t in db.execute(q.limit(500)).scalars() if xem_duoc(u, t)]


CHUYEN = {
    "duyet": (("cho_duyet",), "hoat_dong", False),
    "bo_sung": (("cho_duyet",), "bo_sung", True),
    "tu_choi": (("cho_duyet",), "tu_choi", True),
    "khoa": (("hoat_dong", "cho_duyet", "bo_sung", "ho_so"), "khoa", True),
    "mo_khoa": (("khoa",), None, False),
}


def xu_ly(db: Session, u: User, tk: TaiKhoanNgoai, hanh_dong: str, ly_do: str = "") -> TaiKhoanNgoai:
    if hanh_dong not in CHUYEN:
        raise LoiCong("Thao tác không hợp lệ")
    if not xu_ly_duoc(u, tk):
        raise LoiCong("Hồ sơ này không thuộc phần bạn được duyệt", status=403)
    if hanh_dong == "khoa" and tk.loai == "khach_hang" and not any(x in TOAN_QUYEN for x in _vai(u)):
        raise LoiCong("Chỉ Chủ tịch hoặc TGĐ khoá tài khoản khách hàng", status=403)
    tu, den, can_ly_do = CHUYEN[hanh_dong]
    if tk.trang_thai not in tu:
        raise LoiCong(f"Hồ sơ đang «{TRANG_THAI_NGOAI.get(tk.trang_thai)}» — không {hanh_dong.replace('_', ' ')} được")
    ly_do = (ly_do or "").strip()[:300]
    if can_ly_do and not ly_do:
        raise LoiCong("Ghi lý do để người gửi hồ sơ biết cần làm gì")
    truoc = tk.trang_thai
    if hanh_dong == "mo_khoa":
        den = "hoat_dong" if (tk.loai == "khach_hang" or tk.duyet_luc) else "cho_duyet"
    tk.trang_thai, tk.ly_do = den, ly_do
    if hanh_dong == "duyet":
        tk.duyet_boi, tk.duyet_luc = u.username, datetime.now()
    if hanh_dong in ("khoa", "tu_choi"):
        tk.phien = (tk.phien or 1) + 1     # phiên đang mở mất hiệu lực ngay
    R.audit(db, u.username, u.role, f"tai_khoan_ngoai_{hanh_dong}", f"tai_khoan_ngoai:{tk.id}",
            before={"trang_thai": truoc}, after={"trang_thai": den, "ly_do": ly_do})
    db.commit(); db.refresh(tk)
    return tk


# ──────────────────────────────────────────────────────────────── DK-1 · MẬT KHẨU

# Mức SÀN, không bao giờ rỗng. Máy chủ thật nạp thêm danh sách dài hơn; chỗ này là cái tối thiểu
# phải chặn được, và phép thử đo đúng nó.
MK_DA_LO = {
    "12345", "123456", "1234567", "12345678", "123456789", "1234567890",
    "111111", "000000", "121212", "123123", "654321", "11111", "00000",
    "qwerty", "qwertyuiop", "asdfgh", "zxcvbn", "iloveyou", "password",
    "passw0rd", "p@ssword", "admin", "administrator", "welcome", "letmein",
    "monkey", "dragon", "sunshine", "princess", "football", "baseball",
    "matkhau", "matkhau123", "vietnam", "hanoi", "saigon", "xinchao",
    "anhyeuem", "emyeuanh", "tinhyeu", "hoahong", "88888888", "99999999",
}


def _chuan_mk(mk: str) -> str:
    """Chuẩn hoá NFC — "cà" gõ liền một ký tự và "cà" gõ rời hai ký tự phải là MỘT mật khẩu."""
    return unicodedata.normalize("NFC", mk or "")


def _goi_bam(mk: str) -> str:
    """bcrypt chỉ đọc 72 BYTE đầu rồi lặng lẽ bỏ phần sau. Tiếng Việt có dấu 3 byte một ký tự, nên
    64 ký tự có thể thành 192 byte: hai mật khẩu khác hẳn nhau sẽ cùng một băm, và người đặt mật
    khẩu dài lại hoá ra kém an toàn hơn người đặt ngắn. Băm sha256 trước, rồi mới bcrypt: mọi ký
    tự đều được đếm, đúng như chuẩn đòi (verify the entire password, no truncation)."""
    return base64.b64encode(hashlib.sha256(_chuan_mk(mk).encode()).digest()).decode()


def kiem_mat_khau(mk: str, lien_he: str = "", ho_ten: str = "") -> str:
    """Câu báo lỗi, hoặc chuỗi rỗng nếu đạt.

    TỪ CHỐI THÌ PHẢI NÓI RÕ VÌ SAO. "Mật khẩu không hợp lệ" là câu để người ta thử mò, không phải
    câu để sửa — chuẩn đòi nói lý do. Và KHÔNG có luật trộn hoa/số/ký hiệu nào ở đây.
    """
    s = _chuan_mk(mk)
    if len(s) < MK_TOI_THIEU:
        return f"Mật khẩu phải từ {MK_TOI_THIEU} ký tự trở lên"
    if len(s) > MK_TOI_DA:
        return f"Mật khẩu dài quá {MK_TOI_DA} ký tự — rút ngắn lại"
    t = s.strip().lower()
    if t in MK_DA_LO:
        return "Mật khẩu này nằm trong danh sách mật khẩu đã bị lộ — chọn mật khẩu khác"
    if "vietourist" in t or "vtourist" in t:
        return "Mật khẩu không được chứa chữ «vietourist»"
    lh = ""
    if lien_he:
        try:
            lh = chuan_lien_he(lien_he)[1]
        except LoiCong:
            lh = str(lien_he).strip().lower()
    goc = lh.split("@")[0] if lh else ""
    if goc and len(goc) >= 4 and goc in t:
        return "Mật khẩu không được chứa số điện thoại hoặc địa chỉ email của bạn"
    hn = (ho_ten or "").strip().lower()
    if hn and len(hn) >= 4 and hn in t:
        return "Mật khẩu không được chứa chính họ tên của bạn"
    return ""


def bam_mat_khau(mk: str) -> str:
    from app.core.security import hash_password
    return hash_password(_goi_bam(mk))


def dung_mat_khau(mk: str, bam: str) -> bool:
    """Tài khoản chưa có mật khẩu (bam rỗng) thì KHÔNG mật khẩu nào đúng — kể cả chuỗi rỗng."""
    from app.core.security import verify_password
    if not bam:
        return False
    return verify_password(_goi_bam(mk), bam)


# ─────────────────────────────────────────────────── DK-1 · ĐƠN ĐĂNG KÝ (bốn bước)
# Mã một lần ở BƯỚC CUỐI. Ba bước trước phải có chỗ đứng mà chưa có tài khoản — đó là `don_dang_ky`.

def _don(db: Session, khoa: str, now: datetime) -> DonDangKy:
    d = db.execute(select(DonDangKy).where(DonDangKy.khoa == (khoa or ""))).scalars().first()
    if d is None or d.het_han <= now:
        raise LoiCong(f"Đơn đăng ký đã quá hạn {DON_SONG_GIO} giờ — bắt đầu lại từ bước 1",
                      ma="don_het", status=410)
    return d


def _don_ra(d: DonDangKy, buoc: int) -> dict:
    return {"khoa": d.khoa, "loai": d.loai, "buoc": buoc, "ho_ten": d.ho_ten,
            "lien_he": che(d.dien_thoai or d.email), "het_han": d.het_han}


def dang_ky_b1(db: Session, loai: str, ho_ten: str, dien_thoai: str = "", email: str = "",
               ip: str = "", now: datetime | None = None) -> dict:
    """Bước 1 — ai và liên hệ nào.

    KHÔNG báo "số này đã đăng ký": nói ra là biến màn này thành máy dò — gõ một nghìn số là biết
    một nghìn người có phải khách của Vietourist hay không. Bước 4 nhắn cho chủ số, không nhắn cho
    người đang gõ.
    """
    now = now or datetime.now()
    if loai not in LOAI_NGOAI:
        raise LoiCong("Cổng không hợp lệ")
    ho_ten = (ho_ten or "").strip()
    if len(ho_ten) < 2:
        raise LoiCong("Ghi họ tên của bạn")
    dt = em = ""
    if (dien_thoai or "").strip():
        kieu, v = chuan_lien_he(dien_thoai)
        if kieu != "dien_thoai":
            raise LoiCong("Ô số điện thoại nhận số, không nhận email")
        dt = v
    if (email or "").strip():
        kieu, v = chuan_lien_he(email)
        if kieu != "email":
            raise LoiCong("Ô email nhận địa chỉ email")
        em = v
    if not dt and not em:
        raise LoiCong("Ghi ít nhất một liên hệ: số điện thoại hoặc email")
    d = DonDangKy(khoa=secrets.token_urlsafe(24), loai=loai, ho_ten=ho_ten[:160], dien_thoai=dt,
                  email=em, ip=(ip or "")[:64], het_han=now + timedelta(hours=DON_SONG_GIO),
                  tao_luc=now)
    db.add(d)
    db.commit()
    return _don_ra(d, 2)


def dang_ky_b2(db: Session, khoa: str, mat_khau: str, now: datetime | None = None) -> dict:
    """Bước 2 — mật khẩu. Băm NGAY tại đây; mật khẩu thô không bao giờ xuống đĩa."""
    now = now or datetime.now()
    d = _don(db, khoa, now)
    loi = kiem_mat_khau(mat_khau, d.dien_thoai or d.email, d.ho_ten)
    if loi:
        raise LoiCong(loi, ma="mk_yeu")
    d.mat_khau_bam = bam_mat_khau(mat_khau)
    db.commit()
    return _don_ra(d, 3)


def dang_ky_b3(db: Session, khoa: str, dong_y: bool, nhan_tin: bool = False,
               now: datetime | None = None) -> dict:
    """Bước 3 — điều khoản. Không bao giờ TỰ BẬT nhận tin quảng cáo."""
    now = now or datetime.now()
    d = _don(db, khoa, now)
    if not d.mat_khau_bam:
        raise LoiCong("Chưa đặt mật khẩu — quay lại bước 2", ma="thieu_buoc")
    if not dong_y:
        raise LoiCong("Phải đồng ý điều khoản dịch vụ mới tạo được tài khoản", ma="can_dong_y")
    d.dong_y_dieu_khoan_luc = now
    d.nhan_tin_quang_cao = bool(nhan_tin)
    db.commit()
    return _don_ra(d, 4)


def _don_du_ba_buoc(d: DonDangKy) -> None:
    if not d.ho_ten or not (d.dien_thoai or d.email):
        raise LoiCong("Chưa xong bước 1 — quay lại ghi họ tên và liên hệ", ma="thieu_buoc")
    if not d.mat_khau_bam:
        raise LoiCong("Chưa đặt mật khẩu — quay lại bước 2", ma="thieu_buoc")
    if not d.dong_y_dieu_khoan_luc:
        raise LoiCong("Chưa đồng ý điều khoản dịch vụ — quay lại bước 3", ma="thieu_buoc")


def dang_ky_gui_ma(db: Session, khoa: str, kenh: str, ip: str = "",
                   now: datetime | None = None) -> dict:
    """Bước 4a — gửi mã. Ba bước trước phải xong hết thì mới gửi."""
    now = now or datetime.now()
    d = _don(db, khoa, now)
    _don_du_ba_buoc(d)
    if kenh not in KENH_MA:
        raise LoiCong("Kênh nhận mã không hợp lệ")
    lh = d.dien_thoai if kenh == "zalo" else d.email
    if not lh:
        raise LoiCong("Chưa có liên hệ hợp với kênh này — quay lại bước 1", ma="thieu_buoc")
    r = gui_ma(db, d.loai, lh, kenh, ip, now)
    d.ma_khoa = r["khoa"]
    db.commit()
    r = dict(r)
    r["khoa"] = d.khoa          # trình duyệt chỉ cầm khoá ĐƠN, không cầm khoá lần gửi mã
    return r


def dang_ky_xong(db: Session, khoa: str, ma: str, now: datetime | None = None) -> tuple:
    """Bước 4b — gõ mã. ĐÂY là chỗ tài khoản ra đời, và chỉ ở đây."""
    now = now or datetime.now()
    d = _don(db, khoa, now)
    _don_du_ba_buoc(d)
    c = db.execute(select(MaXacThucNgoai).where(
        MaXacThucNgoai.khoa == (d.ma_khoa or ""))).scalars().first()
    if c is None or c.da_dung or c.het_han <= now or c.so_lan_sai >= SAI_TOI_DA:
        raise LoiCong("Mã đã hết hạn hoặc không còn dùng được — bấm Gửi lại mã", ma="ma_het")
    if not hmac.compare_digest(c.ma_bam, _bam(c.khoa, (ma or "").strip())):
        c.so_lan_sai += 1
        db.commit()
        con = SAI_TOI_DA - c.so_lan_sai
        raise LoiCong(f"Mã chưa đúng — còn {con} lần thử" if con > 0
                      else f"Sai quá {SAI_TOI_DA} lần — bấm Gửi lại mã",
                      ma="ma_sai" if con > 0 else "ma_het")
    c.da_dung = True
    dk = []
    if d.dien_thoai:
        dk.append(TaiKhoanNgoai.dien_thoai == d.dien_thoai)
    if d.email:
        dk.append(TaiKhoanNgoai.email == d.email)
    cu = db.execute(select(TaiKhoanNgoai).where(
        TaiKhoanNgoai.loai == d.loai, or_(*dk))).scalars().first()
    if cu is not None:
        # Mã đúng KHÔNG mở được tài khoản đã có. Cho vào là để mã thay mật khẩu — đúng cái Chủ
        # tịch cấm 01/11/2026. Người thật quên mật khẩu thì đi đường đặt lại, không đi đường này.
        db.delete(d)
        db.commit()
        raise LoiCong("Liên hệ này đã có tài khoản ở cổng này — hãy đăng nhập, hoặc dùng "
                      "«Quên mật khẩu» nếu không nhớ.", ma="da_co", status=409)
    tk = TaiKhoanNgoai(loai=d.loai, ho_ten=d.ho_ten, dien_thoai=d.dien_thoai, email=d.email,
                       mat_khau_bam=d.mat_khau_bam,
                       trang_thai="hoat_dong" if d.loai == "khach_hang" else "ho_so",
                       dong_y_dieu_khoan_luc=d.dong_y_dieu_khoan_luc,
                       nhan_tin_quang_cao=d.nhan_tin_quang_cao, kenh_ua_thich=c.kenh,
                       dang_nhap_cuoi=now, tao_luc=now)
    db.add(tk)
    db.delete(d)
    db.commit()
    db.refresh(tk)
    return tk, cap_phien(tk)


def don_qua_han(db: Session, now: datetime | None = None) -> int:
    """Dọn đơn quá hạn. Đơn chưa thành tài khoản vẫn giữ họ tên và liên hệ thật — để lại là giữ
    dữ liệu cá nhân của người chưa từng là khách."""
    now = now or datetime.now()
    ds = db.execute(select(DonDangKy).where(DonDangKy.het_han <= now)).scalars().all()
    for d in ds:
        db.delete(d)
    db.commit()
    return len(ds)


# ──────────────────────────────────────────── DK-2 · ĐĂNG NHẬP BẰNG MẬT KHẨU + NHỚ MÁY

# MỘT câu duy nhất cho mọi kiểu sai. Không có tài khoản, sai mật khẩu, tài khoản chưa đặt mật
# khẩu — cả ba trả đúng câu này. Tách ra là biến màn đăng nhập thành máy dò xem ai là khách.
SAI_DN = "Số điện thoại/email hoặc mật khẩu không đúng"


def _bam_dau(dau: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"may:{dau}".encode(), hashlib.sha256).hexdigest()


def _tim_tk(db: Session, loai: str, lien_he: str) -> TaiKhoanNgoai | None:
    try:
        kieu, lh = chuan_lien_he(lien_he)
    except LoiCong:
        return None
    cot = TaiKhoanNgoai.email if kieu == "email" else TaiKhoanNgoai.dien_thoai
    return db.execute(select(TaiKhoanNgoai).where(
        TaiKhoanNgoai.loai == loai, cot == lh)).scalars().first()


def may_quen_duoc(db: Session, tk: TaiKhoanNgoai, dau_nho: str,
                  now: datetime | None = None) -> MayDaNho | None:
    """Máy này đã xác minh và còn hạn chưa. Trả về bản ghi, hoặc None."""
    now = now or datetime.now()
    if not dau_nho:
        return None
    m = db.execute(select(MayDaNho).where(
        MayDaNho.tai_khoan_id == tk.id, MayDaNho.dau_bam == _bam_dau(dau_nho))).scalars().first()
    if m is None or m.het_han <= now:
        return None
    return m


def can_hoi_ma(tk: TaiKhoanNgoai, mat_khau: str) -> bool:
    """Máy lạ thì cổng nào cũng hỏi mã — trừ khách hàng đặt mật khẩu đủ dài."""
    if tk.loai != "khach_hang":
        return True
    return len(_chuan_mk(mat_khau)) < MK_DU_DAI_KHOI_HOI


def dang_nhap(db: Session, loai: str, lien_he: str, mat_khau: str, dau_nho: str = "",
              kenh: str = "", ip: str = "", now: datetime | None = None) -> dict:
    """Bước 1 của đăng nhập: kiểm mật khẩu.

    Trả một trong hai:
      {"xong": True,  "phien": ..., "toi": {...}}            — máy đã quen, vào thẳng
      {"xong": False, "can_ma": True, "khoa": ..., ...}      — máy lạ, phải gõ mã
    """
    now = now or datetime.now()
    if loai not in LOAI_NGOAI:
        raise LoiCong("Cổng không hợp lệ")
    tk = _tim_tk(db, loai, lien_he)
    if tk is not None and tk.dn_khoa_den and tk.dn_khoa_den > now:
        con = int((tk.dn_khoa_den - now).total_seconds() // 60) + 1
        raise LoiCong(f"Đã sai quá nhiều lần — thử lại sau {con} phút", ma="dn_khoa", status=429)
    if tk is None or not dung_mat_khau(mat_khau, tk.mat_khau_bam):
        if tk is not None:
            tk.dn_sai = (tk.dn_sai or 0) + 1
            if tk.dn_sai >= DN_SAI_TOI_DA:
                tk.dn_khoa_den = now + timedelta(minutes=DN_KHOA_PHUT)
                tk.dn_sai = 0
            db.commit()
        raise LoiCong(SAI_DN, ma="sai_dn", status=401)
    if tk.trang_thai in ("khoa", "tu_choi"):
        # Mật khẩu đúng nên người này đã chứng minh là chủ tài khoản — nói thật được.
        raise LoiCong("Tài khoản này đang bị khoá hoặc hồ sơ đã bị từ chối — liên hệ Vietourist",
                      ma="bi_khoa", status=403)
    tk.dn_sai, tk.dn_khoa_den = 0, None
    m = may_quen_duoc(db, tk, dau_nho, now)
    if m is not None or not can_hoi_ma(tk, mat_khau):
        if m is not None:
            m.dung_cuoi, m.ip_cuoi = now, (ip or "")[:64]
            m.het_han = now + timedelta(days=NHO_MAY_NGAY)
        tk.dang_nhap_cuoi = now
        db.commit()
        db.refresh(tk)
        return {"xong": True, "phien": cap_phien(tk), "toi": toi_out(tk)}
    db.commit()
    k = kenh or tk.kenh_ua_thich or ("zalo" if tk.dien_thoai else "email")
    lh = tk.dien_thoai if k == "zalo" else tk.email
    if not lh:
        k = "email" if tk.email else "zalo"
        lh = tk.email or tk.dien_thoai
    r = gui_ma(db, tk.loai, lh, k, ip, now)
    r.update({"xong": False, "can_ma": True,
              "message": "Mật khẩu đúng rồi. Chưa nhận ra máy này — " + r["message"].lower()})
    return r


def dang_nhap_xac_minh(db: Session, khoa: str, ma: str, nho_may: bool = False, ten_may: str = "",
                       ip: str = "", now: datetime | None = None) -> dict:
    """Bước 2 của đăng nhập từ máy lạ: gõ mã. Mã một mình KHÔNG mở được gì — phải qua bước 1."""
    now = now or datetime.now()
    c = db.execute(select(MaXacThucNgoai).where(
        MaXacThucNgoai.khoa == (khoa or ""))).scalars().first()
    if c is None or c.da_dung or c.het_han <= now or c.so_lan_sai >= SAI_TOI_DA:
        raise LoiCong("Mã đã hết hạn hoặc không còn dùng được — bấm Gửi lại mã", ma="ma_het")
    if not hmac.compare_digest(c.ma_bam, _bam(c.khoa, (ma or "").strip())):
        c.so_lan_sai += 1
        db.commit()
        con = SAI_TOI_DA - c.so_lan_sai
        raise LoiCong(f"Mã chưa đúng — còn {con} lần thử" if con > 0
                      else f"Sai quá {SAI_TOI_DA} lần — bấm Gửi lại mã",
                      ma="ma_sai" if con > 0 else "ma_het")
    tk = _tim_tk(db, c.loai, c.lien_he)
    if tk is None:
        raise LoiCong("Mã này không gắn với tài khoản nào", ma="ma_het")
    c.da_dung = True
    dau = ""
    if nho_may:
        dau = secrets.token_urlsafe(32)
        db.add(MayDaNho(tai_khoan_id=tk.id, dau_bam=_bam_dau(dau),
                        ten_may=(ten_may or "").strip()[:80], ip_cuoi=(ip or "")[:64],
                        dung_cuoi=now, het_han=now + timedelta(days=NHO_MAY_NGAY), tao_luc=now))
        db.flush()
        cu = db.execute(select(MayDaNho).where(MayDaNho.tai_khoan_id == tk.id)
                        .order_by(MayDaNho.dung_cuoi.desc().nullslast(),
                                  MayDaNho.id.desc())).scalars().all()
        for m in cu[NHO_MAY_TOI_DA:]:      # máy thứ 6 đẩy máy cũ nhất ra
            db.delete(m)
    tk.dang_nhap_cuoi, tk.dn_sai, tk.dn_khoa_den = now, 0, None
    db.commit()
    db.refresh(tk)
    return {"xong": True, "phien": cap_phien(tk), "toi": toi_out(tk), "dau_nho": dau}


# ──────────────────────────────────────────── DK-2 · QUÊN MẬT KHẨU

CAU_QUEN = "Nếu liên hệ này có tài khoản, Vietourist vừa gửi mã tới đó."


def quen_mat_khau_gui_ma(db: Session, loai: str, lien_he: str, kenh: str, ip: str = "",
                         now: datetime | None = None) -> dict:
    """Trả CÙNG MỘT CÂU dù liên hệ có tài khoản hay không — không thành máy dò."""
    now = now or datetime.now()
    if loai not in LOAI_NGOAI:
        raise LoiCong("Cổng không hợp lệ")
    tk = _tim_tk(db, loai, lien_he)
    if tk is None:
        # Không gửi gì, nhưng câu trả lời không đổi một chữ.
        return {"message": CAU_QUEN, "khoa": "", "gui_toi": che(chuan_lien_he(lien_he)[1])}
    r = gui_ma(db, loai, lien_he, kenh, ip, now)
    r["message"] = CAU_QUEN
    return r


def quen_mat_khau_dat_lai(db: Session, khoa: str, ma: str, mat_khau_moi: str,
                          now: datetime | None = None) -> dict:
    """Đặt lại mật khẩu: ĐĂNG XUẤT MỌI NƠI và QUÊN MỌI MÁY.

    Người đổi mật khẩu thường là người vừa nghi bị chiếm tài khoản. Giữ lại dấu nhớ cũ là giữ
    luôn đường vào cho kẻ chiếm.
    """
    now = now or datetime.now()
    c = db.execute(select(MaXacThucNgoai).where(
        MaXacThucNgoai.khoa == (khoa or ""))).scalars().first()
    if c is None or c.da_dung or c.het_han <= now or c.so_lan_sai >= SAI_TOI_DA:
        raise LoiCong("Mã đã hết hạn hoặc không còn dùng được — bấm Gửi lại mã", ma="ma_het")
    if not hmac.compare_digest(c.ma_bam, _bam(c.khoa, (ma or "").strip())):
        c.so_lan_sai += 1
        db.commit()
        con = SAI_TOI_DA - c.so_lan_sai
        raise LoiCong(f"Mã chưa đúng — còn {con} lần thử" if con > 0
                      else f"Sai quá {SAI_TOI_DA} lần — bấm Gửi lại mã",
                      ma="ma_sai" if con > 0 else "ma_het")
    tk = _tim_tk(db, c.loai, c.lien_he)
    if tk is None:
        raise LoiCong("Mã này không gắn với tài khoản nào", ma="ma_het")
    loi = kiem_mat_khau(mat_khau_moi, c.lien_he, tk.ho_ten)
    if loi:
        raise LoiCong(loi, ma="mk_yeu")       # KHÔNG tiêu mã: để người ta đặt lại cho đạt
    c.da_dung = True
    tk.mat_khau_bam = bam_mat_khau(mat_khau_moi)
    tk.phien = (tk.phien or 1) + 1            # mọi phiên đang mở mất hiệu lực
    tk.dn_sai, tk.dn_khoa_den = 0, None
    for m in db.execute(select(MayDaNho).where(MayDaNho.tai_khoan_id == tk.id)).scalars().all():
        db.delete(m)                          # quên sạch mọi máy
    db.commit()
    return {"message": "Đã đặt mật khẩu mới. Mọi phiên và mọi máy đã nhớ đều bị đăng xuất."}


# ──────────────────────────────────────────── DK-2 · MÀN TỰ XEM MÁY ĐÃ NHỚ

def may_cua_toi(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    ds = db.execute(select(MayDaNho).where(MayDaNho.tai_khoan_id == tk.id)
                    .order_by(MayDaNho.dung_cuoi.desc().nullslast())).scalars().all()
    return [{"id": m.id, "ten_may": m.ten_may or "Máy không đặt tên",
             "dung_cuoi": m.dung_cuoi, "het_han": m.het_han,
             "con_han": m.het_han > now} for m in ds]


def go_may(db: Session, tk: TaiKhoanNgoai, may_id: int) -> None:
    m = db.get(MayDaNho, may_id)
    if m is None or m.tai_khoan_id != tk.id:
        raise LoiCong("Không có máy này trong danh sách của bạn", status=404)
    db.delete(m)
    db.commit()


def don_may_qua_han(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now()
    ds = db.execute(select(MayDaNho).where(MayDaNho.het_han <= now)).scalars().all()
    for m in ds:
        db.delete(m)
    db.commit()
    return len(ds)
