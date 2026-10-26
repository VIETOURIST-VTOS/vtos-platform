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
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.core import User, ROLES
from app.models.cong_ngoai import (TaiKhoanNgoai, MaXacThucNgoai, LOAI_NGOAI, LOAI_DOI_TAC,
                                   TRANG_THAI_NGOAI, KENH_MA)
from app.services import rules as R

SONG_MA_PHUT = 5
SAI_TOI_DA = 5
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
            "loai_doi_tac_chon": LOAI_DOI_TAC}


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
              "xu_ly_duoc": xu_ly_duoc(u, tk),
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
