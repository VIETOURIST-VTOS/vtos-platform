"""KS-1 · Khách sạn qua OTA (Affiliate) — xem models/khach_san_ota.py cho bối cảnh.

BỐN ĐIỀU KIỆN BẬT MỘT OTA (đặc tả Khách sạn v1.1 mục 4): hợp tác ĐÃ DUYỆT · link HTTPS hợp lệ đúng tên
miền / đường dẫn đã khai · ĐÃ KIỂM link · OTA CHO PHÉP dùng trên web. Thiếu một điều là không bật được,
và đang bật mà mất một điều thì tự tắt. Chỉ Chủ tịch nhập và bật (Chủ tịch chọn 28/10/2026).

CHUYỂN KHÁCH: trình duyệt chỉ gửi mã OTA + request_id (UUID) + lựa chọn để nhắc khách; KHÔNG gửi link,
khách hàng, pháp nhân hay số tiền. Máy chủ ghi lượt rồi trả link đúng phiên bản. Cùng tài khoản + cùng
request_id = cùng lượt (bấm lặp không ghi hai lần); cùng request_id mà khác OTA = 409; link đã đổi
phiên bản hoặc OTA đã tắt thì lượt cũ KHÔNG phát lại link cũ.
"""
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.models.khach_san_ota import (PhapNhanHopDong, DoiTacOta, LuotChuyenOta, TRANG_THAI_HOP_TAC, CONG_NGOAI,
                                      SAN_PHAM, LOAI_LINK, HANG_VE)
from app.services import rules as R

VAI_SUA = ("chutich",)
VAI_XEM = ("chutich", "tgd", "bks", "robot_ks")
LUOT_TOI_DA_GIO = 60
LOI_NHAC = ("Bạn xem giá, đặt phòng và thanh toán trên {ota}, theo điều kiện của {ota}; đổi, hủy, hoàn tiền làm "
            "với {ota}. Vietourist có thể nhận hoa hồng từ đặt phòng hợp lệ — giá bạn trả không đổi. Vietourist "
            "không gửi số điện thoại, email của bạn cho {ota}.")
# VB-1: vé máy bay. Câu hoa hồng CHỈ có khi đối tác dùng link hoa hồng — trang công khai thì không nói.
LOI_NHAC_VE = ("Bạn xem giá, đặt vé và thanh toán trên {ota}, theo điều kiện của {ota}; đổi, hoàn vé, hành lý làm "
               "với {ota}.{hh} Vietourist không gửi số điện thoại, email của bạn cho {ota}.")
CAU_HOA_HONG_VE = " Vietourist có thể nhận hoa hồng từ đặt vé hợp lệ — giá bạn trả không đổi."
# Cổng được dùng mục vé máy bay (Chủ tịch chọn 28/10/2026): Khách hàng và Cổ đông — KHÔNG có Đối tác.
CONG_VE = ("khach_hang", "co_dong")


class LoiOta(ValueError):
    def __init__(self, thong_diep: str, status: int = 400):
        super().__init__(thong_diep)
        self.status = status


def _hom_nay() -> date:
    return date.today()


# ---------------------------------------------------------------- link và điều kiện

def _ds_mien(ten_mien: str) -> list[str]:
    return [m.strip().lower() for m in re.split(r"[,\s]+", ten_mien or "") if m.strip()]


def loi_link(link: str, ten_mien: str, duong_dan: str) -> str:
    """Câu lỗi, rỗng = link hợp lệ. Chặn http, userinfo (a@b), cổng lạ, #, \\, host giả (expedia.com.evil)."""
    link = (link or "").strip()
    if not link:
        return "Chưa có link"
    if "\\" in link or any(c.isspace() for c in link):
        return "Link có ký tự không hợp lệ"
    try:
        p = urlsplit(link)
        cong = p.port
    except ValueError:
        return "Link không đọc được"
    if p.scheme != "https":
        return "Link phải là https"
    if p.username or p.password or "@" in p.netloc:
        return "Link không được chứa tên đăng nhập"
    if cong is not None:
        return "Link không được chứa cổng riêng"
    if p.fragment or "#" in link:
        return "Link không được chứa #"
    mien = _ds_mien(ten_mien)
    if not mien:
        return "Khai tên miền cho phép của OTA"
    if (p.hostname or "").lower() not in mien:
        return f"Link không thuộc tên miền đã khai ({', '.join(mien)})"
    dd = (duong_dan or "").strip()
    if dd and not p.path.startswith(dd):
        return f"Link không bắt đầu bằng đường dẫn đã khai ({dd})"
    return ""


def thieu_de_bat(o: DoiTacOta) -> list[str]:
    t = []
    if o.loai_link == "cong_khai":
        # VB-1: trang công khai — không có hợp tác để duyệt, không có điều khoản Affiliate; chỉ cần link
        # đúng tên miền đã khai và đã mở thử. Chỉ cho vé máy bay.
        if o.san_pham != "ve_may_bay":
            t.append("trang công khai chỉ dùng cho vé máy bay")
        l = loi_link(o.link, o.ten_mien, o.duong_dan)
        if l:
            t.append(l[0].lower() + l[1:])
        if not o.da_kiem_link:
            t.append("chưa kiểm link")
        return t
    if o.trang_thai != "da_duyet":
        t.append("hợp tác chưa được duyệt")
    l = loi_link(o.link, o.ten_mien, o.duong_dan)
    if l:
        t.append(l[0].lower() + l[1:])
    if not o.da_kiem_link:
        t.append("chưa kiểm link")
    if not o.duoc_dung_web:
        t.append("chưa xác nhận được dùng trên web")
    return t


def dang_mo(o: DoiTacOta) -> bool:
    return bool(o.bat) and not thieu_de_bat(o)


# ---------------------------------------------------------------- phía VTOS

def _vai(u: User) -> tuple[str, ...]:
    from app.services.vai_ke_thua import vai_va_cha
    return vai_va_cha(u.role)


def sua_duoc(u: User) -> bool:
    return any(v in VAI_SUA for v in _vai(u))


def _quan_tri_out(db: Session, o: DoiTacOta, luot7: dict, u: User) -> dict:
    pn = db.get(PhapNhanHopDong, o.phap_nhan_id) if o.phap_nhan_id else None
    return {"id": o.id, "ma": o.ma, "ten": o.ten, "trang_thai": o.trang_thai,
            "trang_thai_ten": TRANG_THAI_HOP_TAC.get(o.trang_thai, o.trang_thai), "link": o.link, "ten_mien": o.ten_mien,
            "duong_dan": o.duong_dan, "da_kiem_link": o.da_kiem_link, "duoc_dung_web": o.duoc_dung_web, "bat": o.bat,
            "dang_mo": dang_mo(o), "thieu": thieu_de_bat(o), "loi_link": loi_link(o.link, o.ten_mien, o.duong_dan) if o.link else "",
            "phien_ban": o.phien_ban, "bang_chung": o.bang_chung, "ghi_chu": o.ghi_chu,
            "phap_nhan": {"ma": pn.ma, "ten": pn.ten, "quoc_gia": pn.quoc_gia} if pn else None,
            "sua_boi": o.sua_boi, "sua_luc": o.sua_luc.isoformat(timespec="minutes") if o.sua_luc else None,
            "luot_7_ngay": luot7.get(o.id, 0), "sua_duoc": sua_duoc(u),
            "subid_cho_phep": o.subid_cho_phep, "subid_tham_so": o.subid_tham_so,
            "san_pham": o.san_pham, "san_pham_ten": SAN_PHAM.get(o.san_pham, o.san_pham),
            "loai_link": o.loai_link, "loai_link_ten": LOAI_LINK.get(o.loai_link, o.loai_link)}


def ds_quan_tri(db: Session, u: User, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    luot7 = dict(db.execute(select(LuotChuyenOta.doi_tac_ota_id, func.count(LuotChuyenOta.id))
                            .where(LuotChuyenOta.tao_luc >= now - timedelta(days=7)).group_by(LuotChuyenOta.doi_tac_ota_id)).all())
    ds = db.execute(select(DoiTacOta).order_by(DoiTacOta.thu_tu, DoiTacOta.id)).scalars().all()
    return {"ota": [_quan_tri_out(db, o, luot7, u) for o in ds], "trang_thai": TRANG_THAI_HOP_TAC,
            "phap_nhan": [{"id": p.id, "ma": p.ma, "ten": p.ten, "quoc_gia": p.quoc_gia}
                          for p in db.execute(select(PhapNhanHopDong).order_by(PhapNhanHopDong.id)).scalars()],
            "sua_duoc": sua_duoc(u), "san_pham": SAN_PHAM, "loai_link": LOAI_LINK}


def _lay(db: Session, ota_id: int) -> DoiTacOta:
    o = db.get(DoiTacOta, ota_id)
    if o is None:
        raise LoiOta("Không có OTA này", 404)
    return o


def _snap(o: DoiTacOta) -> dict:
    return {k: getattr(o, k) for k in ("trang_thai", "link", "ten_mien", "duong_dan", "da_kiem_link", "duoc_dung_web",
                                       "bat", "phien_ban", "phap_nhan_id", "subid_cho_phep", "subid_tham_so", "loai_link")}


def sua(db: Session, u: User, ota_id: int, d: dict, now: datetime | None = None) -> DoiTacOta:
    if not sua_duoc(u):
        raise LoiOta("Chỉ Chủ tịch nhập và bật OTA", 403)
    o = _lay(db, ota_id)
    truoc = _snap(o)
    if "trang_thai" in d and d["trang_thai"] is not None:
        if d["trang_thai"] not in TRANG_THAI_HOP_TAC:
            raise LoiOta("Trạng thái hợp tác không hợp lệ")
        o.trang_thai = d["trang_thai"]
    if d.get("phap_nhan_id") is not None:
        if db.get(PhapNhanHopDong, int(d["phap_nhan_id"])) is None:
            raise LoiOta("Không có pháp nhân này")
        o.phap_nhan_id = int(d["phap_nhan_id"])
    doi_link = False
    if d.get("loai_link") is not None and d["loai_link"] != o.loai_link:
        if d["loai_link"] not in LOAI_LINK:
            raise LoiOta("Loại link không hợp lệ")
        if d["loai_link"] == "cong_khai" and o.san_pham != "ve_may_bay":
            raise LoiOta("Trang công khai chỉ dùng cho vé máy bay — khách sạn cần link hoa hồng")
        o.loai_link = d["loai_link"]; doi_link = True   # đổi loại link = phiên bản mới, tự tắt, kiểm lại
    for k, n in (("link", 500), ("ten_mien", 120), ("duong_dan", 200)):
        if d.get(k) is not None:
            v = str(d[k]).strip()[:n]
            if k == "ten_mien":
                v = ", ".join(_ds_mien(v))
            if v != getattr(o, k):
                setattr(o, k, v); doi_link = True
    if doi_link:
        # Link mới = phiên bản mới: TẮT, phải kiểm lại; lượt cũ không phát lại link cũ.
        o.phien_ban = (o.phien_ban or 1) + 1
        o.bat, o.da_kiem_link = False, False
        if o.link and (l := loi_link(o.link, o.ten_mien, o.duong_dan)):
            raise LoiOta(l)
    for k in ("da_kiem_link", "duoc_dung_web"):
        if d.get(k) is not None:
            setattr(o, k, bool(d[k]))
    if doi_link:
        # Cờ «đã kiểm» của link CŨ không được theo sang link MỚI. Màn Sửa gửi cả năm ô —
        # link, tên miền, đường dẫn, đã-kiểm, được-dùng-web — trong MỘT lượt, nên nhánh
        # `doi_link` phía trên vừa xoá cờ thì vòng lặp ngay trên đây ghi đè lại: phép kiểm
        # lại link bị xoá bởi đúng cái lượt đã đặt ra nó (đo 29/10/2026). Đặt lại ở ĐÂY,
        # sau mọi phép gán, nên không còn đường nào ghi đè được nữa.
        o.bat, o.da_kiem_link = False, False
    # KS-2: SubID — chỉ khi OTA cho phép; tên tham số chỉ chữ / số / gạch dưới, không trùng tham số sẵn có của link.
    if d.get("subid_tham_so") is not None:
        ts = str(d["subid_tham_so"]).strip()
        if ts and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,29}", ts):
            raise LoiOta("Tên tham số SubID chỉ gồm chữ, số, gạch dưới (vd sid, subid)")
        o.subid_tham_so = ts
    if d.get("subid_cho_phep") is not None:
        o.subid_cho_phep = bool(d["subid_cho_phep"])
    if o.subid_cho_phep and not o.subid_tham_so:
        raise LoiOta("Bật SubID thì phải khai tên tham số")
    if o.subid_tham_so and re.search(rf"[?&]{re.escape(o.subid_tham_so)}=", o.link or ""):
        raise LoiOta("Link đã có sẵn tham số này — chọn tên khác")
    for k in ("bang_chung", "ghi_chu"):
        if d.get(k) is not None:
            setattr(o, k, str(d[k]).strip()[:2000])
    if o.bat and thieu_de_bat(o):
        o.bat = False                           # mất một điều kiện thì tự tắt
    o.sua_boi, o.sua_luc = u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "sua_doi_tac_ota", f"doi_tac_ota:{o.ma}", before=truoc, after=_snap(o))
    db.commit(); db.refresh(o)
    return o


def them_phap_nhan(db: Session, u: User, ma: str, ten: str, quoc_gia: str = "", ghi_chu: str = "") -> PhapNhanHopDong:
    if not sua_duoc(u):
        raise LoiOta("Chỉ Chủ tịch nhập và bật OTA", 403)
    ma = re.sub(r"[^A-Z0-9_]", "", (ma or "").strip().upper())[:30]
    ten = (ten or "").strip()[:200]
    if not ma or not ten:
        raise LoiOta("Ghi mã và tên pháp nhân")
    if db.execute(select(PhapNhanHopDong).where(PhapNhanHopDong.ma == ma)).scalars().first():
        raise LoiOta(f"Mã {ma} đã có")
    p = PhapNhanHopDong(ma=ma, ten=ten, quoc_gia=(quoc_gia or "").strip()[:60], ghi_chu=(ghi_chu or "").strip()[:2000])
    db.add(p); db.flush()
    R.audit(db, u.username, u.role, "them_phap_nhan_hop_dong", f"phap_nhan_hop_dong:{ma}", after={"ten": ten})
    db.commit(); db.refresh(p)
    return p


def bat_tat(db: Session, u: User, ota_id: int, bat: bool, now: datetime | None = None) -> DoiTacOta:
    if not sua_duoc(u):
        raise LoiOta("Chỉ Chủ tịch nhập và bật OTA", 403)
    o = _lay(db, ota_id)
    if bat:
        t = thieu_de_bat(o)
        if t:
            raise LoiOta(f"Chưa bật được {o.ten}: " + "; ".join(t))
    truoc = _snap(o)
    o.bat = bool(bat)
    o.sua_boi, o.sua_luc = u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "bat_doi_tac_ota" if bat else "tat_doi_tac_ota", f"doi_tac_ota:{o.ma}",
            before=truoc, after=_snap(o))
    db.commit(); db.refresh(o)
    return o


def thong_ke(db: Session, so_ngay: int = 7, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    tu = now - timedelta(days=max(1, min(int(so_ngay or 7), 90)))
    otas = {o.id: o.ten + (" · vé máy bay" if o.san_pham == "ve_may_bay" else "") for o in db.execute(select(DoiTacOta)).scalars()}
    dts = {d.id: d.ten for d in db.execute(select(DoiTacBanHang)).scalars()}
    dem = Counter()
    for l in db.execute(select(LuotChuyenOta).where(LuotChuyenOta.tao_luc >= tu)).scalars():
        dem[(l.tao_luc.date().isoformat(), otas.get(l.doi_tac_ota_id, "?"), l.cong, dts.get(l.doi_tac_ban_hang_id, ""))] += 1
    dong = [{"ngay": k[0], "ota": k[1], "cong": k[2], "cong_ten": CONG_NGOAI.get(k[2], k[2]), "doi_tac": k[3], "luot": n}
            for k, n in sorted(dem.items(), key=lambda x: (x[0][0], -x[1]), reverse=True)]
    theo_cong = Counter()
    for k, n in dem.items():
        theo_cong[k[2]] += n
    return {"so_ngay": (now - tu).days, "tong": sum(dem.values()), "theo_cong": dict(theo_cong), "dong": dong}


# ---------------------------------------------------------------- phía cổng ngoài

def cong_cua(tk: TaiKhoanNgoai, san_pham: str = "khach_san") -> str:
    cong = ""
    if tk.loai == "khach_hang" and tk.trang_thai != "khoa":
        cong = "khach_hang"
    elif tk.loai in ("doi_tac", "co_dong") and tk.trang_thai == "hoat_dong":
        cong = tk.loai
    if not cong or (san_pham == "ve_may_bay" and cong not in CONG_VE):
        raise LoiOta(f"Tài khoản chưa dùng được mục {SAN_PHAM.get(san_pham, 'Khách sạn')}", 403)
    return cong


def ds_cong(db: Session, tk: TaiKhoanNgoai, san_pham: str = "khach_san") -> list[dict]:
    if san_pham not in SAN_PHAM:
        raise LoiOta("Sản phẩm không hợp lệ")
    cong_cua(tk, san_pham)
    return [{"ma": o.ma, "ten": o.ten, "co_hoa_hong": o.loai_link == "hoa_hong"}
            for o in db.execute(select(DoiTacOta).where(DoiTacOta.san_pham == san_pham)
                                .order_by(DoiTacOta.thu_tu, DoiTacOta.id)).scalars() if dang_mo(o)]


def _ngay(s) -> date | None:
    if not s:
        return None
    if isinstance(s, date):
        return s
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise LoiOta("Ngày không hợp lệ")


def _lua_chon(d: dict, hn: date) -> dict:
    nhan, tra = _ngay(d.get("nhan_phong")), _ngay(d.get("tra_phong"))
    if nhan and nhan < hn:
        raise LoiOta("Ngày nhận phòng đã qua")
    if nhan and tra and tra <= nhan:
        raise LoiOta("Ngày trả phòng phải sau ngày nhận phòng")
    sp, nl, te = int(d.get("so_phong") or 1), int(d.get("nguoi_lon") or 1), int(d.get("tre_em") or 0)
    if not (1 <= sp <= 9 and 1 <= nl <= 30 and 0 <= te <= 20):
        raise LoiOta("Số phòng 1–9, người lớn 1–30, trẻ em 0–20")
    return {"diem_den": str(d.get("diem_den") or "").strip()[:120], "nhan_phong": nhan, "tra_phong": tra,
            "so_phong": sp, "nguoi_lon": nl, "tre_em": te}


def _lua_chon_ve(d: dict, hn: date) -> dict:
    di, ve = _ngay(d.get("ngay_di")), _ngay(d.get("ngay_ve"))
    if di and di < hn:
        raise LoiOta("Ngày đi đã qua")
    if di and ve and ve < di:
        raise LoiOta("Ngày về phải từ ngày đi trở đi")
    nl, te, eb = int(d.get("nguoi_lon") or 1), int(d.get("tre_em") or 0), int(d.get("em_be") or 0)
    if not (1 <= nl <= 9 and 0 <= te <= 8 and 0 <= eb <= nl):
        raise LoiOta("Người lớn 1–9, trẻ em 0–8, em bé không nhiều hơn người lớn")
    hang = str(d.get("hang_ve") or "pho_thong")
    if hang not in HANG_VE:
        raise LoiOta("Hạng vé không hợp lệ")
    return {"diem_di": str(d.get("diem_di") or "").strip()[:120], "diem_den": str(d.get("diem_den") or "").strip()[:120],
            "nhan_phong": di, "tra_phong": ve, "so_phong": 1, "nguoi_lon": nl, "tre_em": te, "em_be": eb, "hang_ve": hang}


def _nhac(o: DoiTacOta, l: LuotChuyenOta) -> str:
    if l.san_pham == "ve_may_bay":
        phan = [" → ".join(x for x in (l.diem_di, l.diem_den) if x)] if (l.diem_di or l.diem_den) else []
        if l.nhan_phong:
            phan.append(f"{l.nhan_phong:%d/%m}" + (f" – {l.tra_phong:%d/%m}" if l.tra_phong else " · một chiều"))
        phan.append(f"{l.nguoi_lon} người lớn" + (f" · {l.tre_em} trẻ em" if l.tre_em else "") + (f" · {l.em_be} em bé" if l.em_be else ""))
        phan.append(HANG_VE.get(l.hang_ve, l.hang_ve))
        return " · ".join(p for p in phan if p)
    phan = [l.diem_den] if l.diem_den else []
    if l.nhan_phong:
        phan.append(f"{l.nhan_phong:%d/%m}" + (f" – {l.tra_phong:%d/%m}" if l.tra_phong else ""))
    phan.append(f"{l.so_phong} phòng · {l.nguoi_lon} người lớn" + (f" · {l.tre_em} trẻ em" if l.tre_em else ""))
    return " · ".join(phan)


def link_cua(o: DoiTacOta, l: LuotChuyenOta) -> str:
    """Link trả cho trình duyệt. Gắn mã lượt (ngẫu nhiên, không chứa gì của khách) khi OTA cho phép SubID."""
    if not (o.loai_link == "hoa_hong" and o.subid_cho_phep and o.subid_tham_so and l.ma_luot):
        return o.link
    from urllib.parse import quote
    return o.link + ("&" if "?" in o.link else "?") + f"{o.subid_tham_so}={quote(l.ma_luot)}"


def chuyen(db: Session, tk: TaiKhoanNgoai, ma_ota: str, request_id: str, lua_chon: dict | None = None,
           now: datetime | None = None) -> dict:
    now = now or datetime.now()
    try:
        rid = str(uuid.UUID(str(request_id or "")))
    except ValueError:
        raise LoiOta("Mã yêu cầu không hợp lệ — tải lại trang")
    o = db.execute(select(DoiTacOta).where(DoiTacOta.ma == str(ma_ota or ""))).scalars().first()
    if o is None or not dang_mo(o):
        raise LoiOta("OTA này chưa mở trên VTD", 404)
    cong = cong_cua(tk, o.san_pham)
    cu = db.execute(select(LuotChuyenOta).where(LuotChuyenOta.tai_khoan_id == tk.id, LuotChuyenOta.request_id == rid)).scalars().first()
    if cu is not None:
        if cu.doi_tac_ota_id != o.id:
            raise LoiOta("Yêu cầu này đã dùng cho OTA khác — tải lại trang", 409)
        if cu.phien_ban_link != o.phien_ban:
            raise LoiOta("Link của OTA đã đổi — tải lại trang", 409)
        l = cu
    else:
        gio = db.execute(select(func.count(LuotChuyenOta.id)).where(
            LuotChuyenOta.tai_khoan_id == tk.id, LuotChuyenOta.tao_luc >= now - timedelta(hours=1))).scalar_one()
        if gio >= LUOT_TOI_DA_GIO:
            raise LoiOta("Bạn mở OTA quá nhiều lần trong một giờ — thử lại sau", 429)
        lc = (_lua_chon_ve if o.san_pham == "ve_may_bay" else _lua_chon)(lua_chon or {}, now.date())
        from app.services.doi_soat_ota import ma_luot_moi
        l = LuotChuyenOta(tai_khoan_id=tk.id, request_id=rid, doi_tac_ota_id=o.id, phien_ban_link=o.phien_ban, cong=cong,
                          ma_luot=ma_luot_moi(db), san_pham=o.san_pham, loai_link=o.loai_link,
                          doi_tac_ban_hang_id=tk.doi_tac_id if cong == "doi_tac" else None, tao_luc=now, **lc)
        db.add(l); db.commit(); db.refresh(l)
    nhac = (LOI_NHAC_VE.format(ota=o.ten, hh=CAU_HOA_HONG_VE if o.loai_link == "hoa_hong" else "")
            if o.san_pham == "ve_may_bay" else LOI_NHAC.format(ota=o.ten))
    return {"luot_id": l.id, "url": link_cua(o, l), "ota": o.ten, "loi_nhac": nhac, "chon_lai": _nhac(o, l)}


def dat_phong_xac_minh(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    """KS-2: đặt phòng OTA báo về nối được bằng mã lượt của CHÍNH tài khoản này."""
    from app.services.doi_soat_ota import dat_phong_cua
    cong_cua(tk)
    ids = [i for (i,) in db.execute(select(LuotChuyenOta.id).where(LuotChuyenOta.tai_khoan_id == tk.id)).all()]
    return dat_phong_cua(db, ids)


def lich_su(db: Session, tk: TaiKhoanNgoai, san_pham: str = "khach_san") -> list[dict]:
    cong_cua(tk, san_pham)
    otas = {o.id: o for o in db.execute(select(DoiTacOta)).scalars()}
    ra = []
    for l in db.execute(select(LuotChuyenOta).where(LuotChuyenOta.tai_khoan_id == tk.id, LuotChuyenOta.san_pham == san_pham)
                        .order_by(LuotChuyenOta.tao_luc.desc()).limit(30)).scalars():
        o = otas.get(l.doi_tac_ota_id)
        ra.append({"luc": l.tao_luc.isoformat(timespec="minutes"), "ota": o.ten if o else "", "da_chon": _nhac(o, l) if o else ""})
    return ra
