"""TK-1 · Khách tự thiết kế tour đoàn — giai đoạn 1 (Chủ tịch 04/11/2026).

Luồng: khách chọn trên cổng (điểm đến, số đêm, khách, phòng, khách sạn, bữa ăn, điểm tham quan, phương tiện từng chặng,
dịch vụ cả chuyến) → MÁY CHỦ tính tạm tính → khách gửi → yêu cầu tour đoàn vào hộp Sales (cong_khach.gui_yeu_cau) +
một phiên bản ThietKeDoan bất biến. Gửi lại cùng mã = phiên bản mới, bản cũ «thay_the».

TẠM TÍNH — chỉ tính từ nguồn giá có thật trong VTOS, mọi con số trình duyệt gửi lên đều bị bỏ qua:
  · Khách sạn: gói giá VTD đã duyệt, đang bán, phủ đủ các đêm (khach_san_vtd.gia_luu) × số phòng × (1 + thuế phí %).
  · Bữa trưa / tối: thực đơn nhà hàng đang mở đặt (nha_hang) × người lớn + trẻ em (thiếu giá trẻ em → giá người lớn).
  · Xe, HDV, trưởng đoàn, bảo hiểm, nước, visa, hội nghị, team building, vé máy bay theo chặng: DonGiaDoan Điều hành
    nhập và đã được duyệt.
  · Vé máy bay đi qua NGUON_VE — hôm nay chỉ có nguồn «Điều hành nhập»; nối API vé sau thì thêm một nguồn vào danh sách,
    phần còn lại không đổi.
  · Không có giá → dòng «thiếu giá» (Sales báo), KHÔNG coi là 0 và không cộng vào tạm tính.
Giá bán tạm tính = giá vốn ÷ (1 − BIEN_TAM_TINH), làm tròn lên nghìn đồng — khách chỉ thấy giá bán, Sales cũng vậy;
giá vốn và biên chỉ Điều hành / TP Điều hành / Kế toán / BKS / Chủ tịch / TGĐ xem.
NGUONG_DUYET: báo giá có biên dưới mức này phải Chủ tịch / TGĐ duyệt — áp ở bước duyệt báo giá (giai đoạn 2).
"""
from __future__ import annotations

import math
import unicodedata
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.thiet_ke_doan import (DON_VI, HANG_VE, LOAI_DON_GIA, PHAM_VI, TRANG_THAI_DG, DonGiaDoan,
                                      NgayLeTet, ThietKeDoan)
from app.services import rules as R

BIEN_TAM_TINH = 0.10          # Chủ tịch 04/11/2026: «biên lợi nhuận tạm tính là 10%»
NGUONG_DUYET = 0.10           # dưới mức này Chủ tịch / TGĐ duyệt (giai đoạn 2 — duyệt báo giá)

TOAN_QUYEN = ("chutich", "tgd")
VAI_NHAP_GIA = TOAN_QUYEN + ("tp_dh", "nv_dh")
VAI_DUYET_GIA = TOAN_QUYEN + ("tp_dh",)
VAI_GIA_VON = TOAN_QUYEN + ("tp_dh", "nv_dh", "ketoan", "bks", "robot_ks")   # robot Kiểm soát: chỉ đọc
VAI_XEM = VAI_GIA_VON + ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "sales_admin")

KHACH_TOI_DA, DIEM_TOI_DA, DEM_MOT_DIEM, NGAY_TOI_DA = 300, 15, 14, 30
DICH_VU_KHACH = {"hdv": "Hướng dẫn viên suốt tuyến", "bao_hiem": "Bảo hiểm du lịch", "nuoc": "Nước suối mỗi ngày",
                 "visa": "Visa nhập cảnh", "hoi_nghi": "Phòng hội nghị (MICE)", "team_building": "Team building"}
PHUONG_TIEN = {"xe": "Xe du lịch", "bay": "Máy bay", "tau": "Tàu hỏa", "thuyen": "Du thuyền / tàu cao tốc", "khac": "Khác"}
NHOM = {"gia_dinh": "Gia đình", "ban_be": "Bạn bè", "cong_ty": "Công ty / MICE"}
NHIP = {"thu_tha": "Thư thả", "can_bang": "Cân bằng", "nhieu": "Nhiều trải nghiệm"}
# Tour xa: trưởng đoàn kiêm HDV suốt tuyến (Chủ tịch 03/11/2026: Mỹ, châu Âu, Anh, Canada)
CHAU_AU = ["Pháp", "Ý", "Tây Ban Nha", "Bồ Đào Nha", "Đức", "Thụy Sĩ", "Áo", "Hà Lan", "Bỉ", "Luxembourg", "Anh", "Ireland",
           "Scotland", "Đan Mạch", "Na Uy", "Thụy Điển", "Phần Lan", "Iceland", "Ba Lan", "Séc", "Slovakia", "Hungary",
           "Slovenia", "Croatia", "Serbia", "Bosnia & Herzegovina", "Montenegro", "Bắc Macedonia", "Albania", "Hy Lạp",
           "Bulgaria", "Romania", "Moldova", "Ukraine", "Belarus", "Nga", "Litva", "Latvia", "Estonia", "Malta", "Monaco",
           "San Marino", "Vatican", "Andorra", "Liechtenstein", "Kosovo"]
TOUR_XA = set(CHAU_AU) | {"Hoa Kỳ", "Canada", "Anh", "Scotland", "Ireland"}


class LoiThietKe(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _co(u: User, vai: tuple) -> bool:
    return u.role in vai


def _quyen(u: User, vai: tuple, msg: str = "Không có quyền") -> None:
    if not _co(u, vai):
        raise LoiThietKe(msg, 403)


def khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").split())


def ban(von: float | None) -> int | None:
    """Giá bán tạm tính từ giá vốn: chia (1 − biên), làm tròn LÊN nghìn đồng."""
    if von is None:
        return None
    return int(math.ceil(float(von) / (1 - BIEN_TAM_TINH) / 1000.0) * 1000) if von > 0 else 0


def _sach(s, n: int = 200) -> str:
    return " ".join(str(s or "").replace("<", "").replace(">", "").split())[:n]


def _so(v, lo: int = 0, hi: int = 10**9) -> int:
    try:
        x = int(v or 0)
    except (TypeError, ValueError):
        raise LoiThietKe("Số không hợp lệ")
    return max(lo, min(hi, x))


def _ngay(v) -> date | None:
    if not v:
        return None
    try:
        return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])
    except ValueError:
        raise LoiThietKe("Ngày không hợp lệ")


def khop_diem(diem: str, tinh: str) -> bool:
    """Điểm đến của khách («Ninh Bình – Tràng An – Tam Cốc») khớp tỉnh / thành của khách sạn, nhà hàng («Ninh Bình»)."""
    a, b = khong_dau(diem), khong_dau(tinh)
    if not a or not b:
        return False
    phan = [khong_dau(x) for x in diem.replace("—", "–").split("–")]
    return a == b or b in phan or (len(b) >= 4 and b in a) or any(len(p) >= 4 and p in b for p in phan)


# ══ CHUẨN HÓA THIẾT KẾ ══════════════════════════════════════════════════════════════════════════════
def chuan_hoa(d: dict, hom_nay: date | None = None) -> dict:
    """Làm sạch bản khách gửi: chỉ giữ trường biết, chặn số vô lý. Không tin bất kỳ con số tiền nào từ trình duyệt."""
    hom_nay = hom_nay or date.today()
    pv = "nn" if d.get("pham_vi") == "nn" else "dn"
    ngay_di = _ngay(d.get("ngay_di"))
    if ngay_di is None:
        raise LoiThietKe("Chọn ngày khởi hành")
    if ngay_di <= hom_nay:
        raise LoiThietKe("Ngày khởi hành phải sau hôm nay")
    k = d.get("khach") or {}
    nl, te, eb = _so(k.get("nl"), 0, KHACH_TOI_DA), _so(k.get("te"), 0, KHACH_TOI_DA), _so(k.get("eb"), 0, KHACH_TOI_DA)
    if nl < 1:
        raise LoiThietKe("Đoàn cần ít nhất 1 người lớn")
    if nl + te + eb > KHACH_TOI_DA:
        raise LoiThietKe(f"Tối đa {KHACH_TOI_DA} khách một yêu cầu")
    tuoi = [_so(x, 0, 17) for x in (k.get("tuoi_tre") or [])][:te]
    ph = d.get("phong") or {}
    phong = {"p2": _so(ph.get("p2"), 0, 200), "p3": _so(ph.get("p3"), 0, 200), "p1": _so(ph.get("p1"), 0, 200)}
    diem = []
    for x in (d.get("diem") or [])[:DIEM_TOI_DA]:
        ten = _sach(x.get("ten"), 80)
        if not ten:
            continue
        ks = x.get("ks") or {}
        diem.append({"ten": ten, "dem": _so(x.get("dem"), 0, DEM_MOT_DIEM),
                     "ks": {"khach_san_id": _so(ks.get("khach_san_id")) or None, "goi_id": _so(ks.get("goi_id")) or None,
                            "ten_khac": _sach(ks.get("ten_khac"), 120)}})
    if not diem:
        raise LoiThietKe("Thêm ít nhất một điểm đến")
    so_ngay = sum(max(1, x["dem"]) for x in diem) + 1
    if so_ngay > NGAY_TOI_DA:
        raise LoiThietKe(f"Hành trình tối đa {NGAY_TOI_DA} ngày")

    def bua(b) -> dict:
        b = b or {}
        if b.get("tu_tuc"):
            return {"tu_tuc": True}
        if b.get("thuc_don_id"):
            return {"thuc_don_id": _so(b.get("thuc_don_id"))}
        if b.get("khac"):
            return {"khac": _sach(b.get("khac"), 160)}
        return {}
    ngay = []
    for i, x in enumerate((d.get("ngay") or [])[:so_ngay]):
        x = x or {}
        ngay.append({"trua": bua(x.get("trua")), "toi": bua(x.get("toi")),
                     "tham_quan": [_sach(t, 120) for t in (x.get("tham_quan") or [])[:12] if _sach(t, 120)],
                     "ghi_chu": _sach(x.get("ghi_chu"), 300)})
    while len(ngay) < so_ngay:
        ngay.append({"trua": {}, "toi": {}, "tham_quan": [], "ghi_chu": ""})
    chang = []
    for x in (d.get("chang") or [])[:len(diem) + 1]:
        x = x or {}
        pt = x.get("pt") if x.get("pt") in PHUONG_TIEN else "xe"
        chang.append({"pt": pt, "hang_bay": _sach(x.get("hang_bay"), 80),
                      "hang_ve": x.get("hang_ve") if x.get("hang_ve") in HANG_VE else "pho_thong",
                      "khac": _sach(x.get("khac"), 160)})
    while len(chang) < len(diem) + 1:
        chang.append({"pt": "xe", "hang_bay": "", "hang_ve": "pho_thong", "khac": ""})
    dv = [x for x in dict.fromkeys(d.get("dich_vu") or []) if x in DICH_VU_KHACH]
    if pv == "dn":
        dv = [x for x in dv if x != "visa"]
    ns = d.get("ngan_sach")
    return {"pham_vi": pv, "khoi_hanh": _sach(d.get("khoi_hanh"), 80) or "TP HCM", "ngay_di": ngay_di.isoformat(),
            "nhom": d.get("nhom") if d.get("nhom") in NHOM else "", "nhip": d.get("nhip") if d.get("nhip") in NHIP else "",
            "ngan_sach": _so(ns, 0, 10**10) or None if ns not in (None, "") else None, "uu_tien": _sach(d.get("uu_tien"), 300),
            "khach": {"nl": nl, "te": te, "eb": eb, "tuoi_tre": tuoi}, "phong": phong,
            "hang_ks": str(d.get("hang_ks") or "") if str(d.get("hang_ks") or "") in ("", "3", "4", "5") else "",
            "diem": diem, "ngay": ngay, "chang": chang, "dich_vu": dv, "ghi_chu": _sach(d.get("ghi_chu"), 1000)}


def khung(tk: dict) -> list[dict]:
    """Từng ngày: điểm ở, đêm ngủ tại đâu, chặng di chuyển (nếu là ngày chuyển điểm)."""
    di = date.fromisoformat(tk["ngay_di"])
    ra, i = [], 0
    for hi, h in enumerate(tk["diem"]):
        for d in range(max(1, h["dem"])):
            tu = tk["khoi_hanh"] if hi == 0 else tk["diem"][hi - 1]["ten"]
            ra.append({"i": i, "ngay": (di + timedelta(days=i)).isoformat(), "o": h["ten"], "diem_i": hi,
                       "dem": h["dem"] > d, "chang_i": hi if d == 0 else None, "tu": tu if d == 0 else None,
                       "den": h["ten"] if d == 0 else None})
            i += 1
    cuoi = tk["diem"][-1]["ten"]
    ra.append({"i": i, "ngay": (di + timedelta(days=i)).isoformat(), "o": cuoi, "diem_i": len(tk["diem"]) - 1, "dem": False,
               "chang_i": len(tk["diem"]), "tu": cuoi, "den": tk["khoi_hanh"], "ve": True})
    return ra


# ══ NGUỒN GIÁ ═══════════════════════════════════════════════════════════════════════════════════════
def _dg_hieu_luc(db: Session, loai: str, pv: str, ngay: date) -> list[DonGiaDoan]:
    return db.execute(select(DonGiaDoan).where(
        DonGiaDoan.loai == loai, DonGiaDoan.trang_thai == "hieu_luc", DonGiaDoan.pham_vi.in_([pv, "ca_hai"]),
        or_(DonGiaDoan.tu_ngay.is_(None), DonGiaDoan.tu_ngay <= ngay),
        or_(DonGiaDoan.den_ngay.is_(None), DonGiaDoan.den_ngay >= ngay)).order_by(DonGiaDoan.id.desc())).scalars().all()


def _mot_gia(db: Session, loai: str, pv: str, ngay: date) -> DonGiaDoan | None:
    ds = _dg_hieu_luc(db, loai, pv, ngay)
    return ds[0] if ds else None


def chon_xe(ds: list[DonGiaDoan], so_cho: int) -> tuple[DonGiaDoan, int] | None:
    """Xe nhỏ nhất đủ chỗ; đoàn lớn hơn xe lớn nhất thì ghép nhiều xe lớn nhất."""
    xe = sorted([x for x in ds if x.tu_cho], key=lambda x: (x.tu_cho, float(x.gia)))
    if not xe or so_cho < 1:
        return None
    vua = [x for x in xe if x.tu_cho >= so_cho]
    if vua:
        return vua[0], 1
    lon = xe[-1]
    return lon, math.ceil(so_cho / lon.tu_cho)


def _ve_dieu_hanh_nhap(db: Session, tu: str, den: str, ngay: date, hang_ve: str, pv: str) -> dict | None:
    for x in _dg_hieu_luc(db, "ve_may_bay", pv, ngay):
        if khop_diem(tu, x.tu_diem) and khop_diem(den, x.den_diem) and (x.hang_ve or "pho_thong") == hang_ve:
            return {"nl": float(x.gia), "te": float(x.gia_tre_em) if x.gia_tre_em is not None else None,
                    "eb": float(x.gia_em_be) if x.gia_em_be is not None else None, "nguon": "Điều hành nhập",
                    "don_gia_id": x.id, "luc": None}
    return None


# ── TK-1b · bảng giá XE và thù lao HDV theo tuyến đã có trên VTOS (Chủ tịch + TGĐ ký) ───────────────────────────
import re as _re

XE_BANG_CHO = 45            # Chủ tịch 04/11/2026: bảng giá xe theo tuyến là giá xe 45 chỗ
_DUOI_TUYEN = _re.compile(r"\s*(\(.*?\)|\bnew\b|\d+(?:[.,]\d+)?\s*(?:n\d*đ?|ngày|n)\b.*)$", _re.I)


def _manh_tuyen(route: str) -> list[str]:
    """«Tà Đùng – Đà Lạt – Phan Thiết» → 3 mảnh; bỏ đuôi «2 ngày», «3N2Đ», «5N», «(mới)», «New»."""
    ra = []
    for m in _re.split(r"\s+[–—-]\s+", route or ""):
        m = _DUOI_TUYEN.sub("", m.strip()).strip()
        if m:
            ra.append(m)
    return ra


# Địa danh để đọc tên tuyến trong bảng giá xe / HDV («Đà Lạt Phan Thiết 4N3Đ» là HAI điểm dù không có gạch nối) và để
# xếp vùng cho thù lao HDV. Chia 5 vùng theo mức thù lao của bảng HDV (Chủ tịch 04/11/2026: tuyến chưa có phí thì lấy
# tương tự theo vùng của bảng giá mới).
VUNG_HDV: dict[str, list[str]] = {
    "Miền Bắc": ["Hà Nội", "Hạ Long", "Cát Bà", "Lan Hạ", "Cô Tô", "Yên Tử", "Hải Phòng", "Ninh Bình", "Tràng An", "Tam Cốc",
                 "Sapa", "Hà Giang", "Cao Bằng", "Bản Giốc", "Ba Bể", "Lạng Sơn", "Mộc Châu", "Mai Châu", "Mù Cang Chải",
                 "Điện Biên", "Lai Châu", "Tam Đảo", "Đền Hùng", "Bắc Ninh", "Thái Nguyên", "Nam Định", "Sầm Sơn",
                 "Thanh Hóa", "Pù Luông", "Miền Bắc"],
    "Bắc & Trung Trung Bộ": ["Cửa Lò", "Nghệ An", "Hà Tĩnh", "Phong Nha", "Quảng Bình", "Quảng Trị", "Huế", "Đà Nẵng",
                             "Hội An", "Bà Nà", "Lý Sơn", "Quảng Ngãi", "Di sản Miền Trung", "Miền Trung"],
    "Nam Trung Bộ": ["Quy Nhơn", "Phú Yên", "Tuy Hòa", "Nha Trang", "Bình Ba", "Bình Hưng", "Vĩnh Hy", "Ninh Thuận",
                     "Phan Thiết", "Mũi Né", "Tánh Linh", "Tà Pao", "La Ngâu", "Hòn Cò"],
    "Tây Nguyên": ["Đà Lạt", "Bảo Lộc", "Buôn Ma Thuột", "Buôn Mê", "Pleiku", "Gia Lai", "Kon Tum", "Măng Đen", "Tà Đùng",
                   "Tây Nguyên"],
    "Nam Bộ": ["TP Hồ Chí Minh", "Cần Giờ", "Vũng Tàu", "Hồ Tràm", "Long Hải", "Côn Đảo", "Tây Ninh", "Núi Bà Đen",
               "Nam Cát Tiên", "Bình Dương", "Mỹ Tho", "Tiền Giang", "Bến Tre", "Vĩnh Long", "Cần Thơ", "Đồng Tháp",
               "Châu Đốc", "An Giang", "Long An", "Trà Vinh", "Sóc Trăng", "Bạc Liêu", "Cà Mau", "Rạch Giá", "Hà Tiên",
               "Nam Du", "Phú Quốc", "Miền Tây"],
}
# Tên chung một vùng (không phải một điểm) — chỉ dùng để xếp vùng, không dùng để khớp đúng tuyến.
_TEN_VUNG = {"Miền Bắc", "Di sản Miền Trung", "Miền Trung", "Tây Nguyên", "Miền Tây"}


def _co_chu(chu: str, ten: str) -> bool:
    return bool(_re.search(r"(?<![a-z0-9])" + _re.escape(khong_dau(chu)) + r"(?![a-z0-9])", khong_dau(ten)))


def dia_danh(ten: str) -> set[str]:
    """Các địa danh (không tính tên vùng) đọc được trong một tên điểm đến hoặc tên tuyến."""
    return {d for ds in VUNG_HDV.values() for d in ds if d not in _TEN_VUNG and _co_chu(d, ten)}


def vung_cua(ten: str) -> set[str]:
    return {v for v, ds in VUNG_HDV.items() if any(_co_chu(d, ten) for d in ds)}


def khop_tuyen(route: str, diem: list[str]) -> bool:
    """Tuyến khớp hành trình. Đọc được địa danh ở cả hai phía thì so ĐÚNG tập địa danh (tuyến «Đà Lạt Phan Thiết» không
    khớp chuyến chỉ đi Đà Lạt); không đọc được thì so từng mảnh tên tuyến như cũ."""
    a = {x for m in _manh_tuyen(route) for x in dia_danh(m)}
    bs = [dia_danh(d) for d in diem]
    if a and diem and all(bs):
        # mỗi điểm khách chọn có mặt trong tuyến, và mỗi địa danh của tuyến thuộc một điểm khách chọn
        return all(x & a for x in bs) and a <= set().union(*bs)
    manh = _manh_tuyen(route)
    if not manh or not diem:
        return False
    return all(any(khop_diem(d, m) for d in diem) for m in manh) and all(any(khop_diem(d, m) for m in manh) for d in diem)


def _tu_hcm(tk: dict) -> bool:
    return khong_dau(tk["khoi_hanh"]).replace(".", "").replace(" ", "") in ("tphcm", "hcm", "tphochiminh", "hochiminh", "saigon")


def gia_xe_bang(db: Session, tk: dict, so_ngay: int, ngoi: int, ngay: date) -> dict | None:
    """Xe trong nước (TK-1b, TK-1d — Chủ tịch 04/11/2026), theo thứ tự:
      1. Đi xe từ TP HCM, trùng tuyến + số ngày trong bảng giá xe → giá trọn chuyến cột xe nhà × số xe 45 chỗ.
      2. Đơn giá ngày xe nhà (Đội xe nhập ở hồ sơ xe) — xe nhỏ nhất đủ chỗ × số ngày.
      3. Đi xe từ TP HCM, trùng tuyến nhưng lệch số ngày → giá tuyến (số ngày gần nhất) ÷ số ngày tuyến × số ngày đi.
    """
    from app.models.hr import Vehicle, VehicleRate
    so = max(1, math.ceil(ngoi / XE_BANG_CHO))
    diem = [h["ten"] for h in tk["diem"]]
    di_xe = all(c["pt"] == "xe" for c in tk["chang"])
    tuyen = []
    if di_xe and _tu_hcm(tk):
        tuyen = [r for r in db.execute(select(VehicleRate).where(VehicleRate.status == "active")).scalars()
                 if (r.effective_from is None or r.effective_from <= ngay) and (r.internal_price or 0) > 0
                 and khop_tuyen(r.route, diem)]
        rs = [r for r in tuyen if int(r.days or 0) == so_ngay]
        if rs:
            r = sorted(rs, key=lambda x: (x.effective_from or date.min, x.id))[-1]
            return {"ten": f"Xe {XE_BANG_CHO} chỗ · tuyến {r.route} (bảng giá xe)", "loai": f"xe {XE_BANG_CHO} chỗ",
                    "chi_tiet": f"{so} xe × trọn chuyến {so_ngay} ngày", "von": float(r.internal_price) * so,
                    "nguon": f"vehicle_rates:{r.id}"}
    xs = [v for v in db.execute(select(Vehicle).where(Vehicle.active.is_(True), Vehicle.kind == "noi_bo")).scalars()
          if (v.internal_rate_per_day or 0) > 0 and (v.seats or 0) > 0]
    if xs:
        theo_cho: dict[int, float] = {}
        for v in xs:
            theo_cho[v.seats] = min(theo_cho.get(v.seats, float(v.internal_rate_per_day)), float(v.internal_rate_per_day))
        vua = sorted(c for c in theo_cho if c >= ngoi)
        cho = vua[0] if vua else max(theo_cho)
        n = 1 if vua else math.ceil(ngoi / cho)
        return {"ten": f"Xe {cho} chỗ (đơn giá ngày xe nhà)", "loai": f"xe {cho} chỗ",
                "chi_tiet": f"{n} xe × {so_ngay} ngày", "von": theo_cho[cho] * n * so_ngay, "nguon": f"vehicles:seats={cho}"}
    tl = [r for r in tuyen if int(r.days or 0) > 0]
    if tl:
        r = sorted(tl, key=lambda x: (abs(int(x.days) - so_ngay), -(x.effective_from or date.min).toordinal(), -x.id))[0]
        ngay_gia = float(r.internal_price) / int(r.days)
        return {"ten": f"Xe {XE_BANG_CHO} chỗ · theo tuyến {r.route} {int(r.days)} ngày, quy theo ngày (bảng giá xe)",
                "loai": f"xe {XE_BANG_CHO} chỗ", "chi_tiet": f"{so} xe × {so_ngay} ngày",
                "von": ngay_gia * so_ngay * so, "nguon": f"vehicle_rates:{r.id}:quy_ngay"}
    return None


def bang_hdv(db: Session, ngay: date) -> list[dict]:
    """Bảng thù lao HDV đang hiệu lực, mỗi tuyến một dòng (bản «doan» trước, bản chung sau — hdv.tra_don_gia)."""
    from app.models.hr import GuideRate
    from app.services import hdv as HDV
    ra = []
    for t in sorted({r.route for r in db.execute(select(GuideRate).where(GuideRate.status == "active")).scalars()}):
        r = HDV.tra_don_gia(db, t, "doan", ngay)
        if r and r.rate_per_day:
            ra.append({"route": t, "days": float(r.days or 0), "gia": float(r.rate_per_day), "id": r.id,
                       "vung": sorted(vung_cua(t))})
    return ra


def gia_vung_hdv(bang: list[dict]) -> dict[str, float]:
    """Thù lao HDV suy cho mỗi vùng = trung vị (lấy số cao hơn khi chẵn) các tuyến nằm trong vùng ấy."""
    import statistics
    ra = {}
    for v in VUNG_HDV:
        # tuyến chỉ nằm trong vùng ấy trước (tuyến ghép hai vùng kéo lệch mức của vùng); không có thì lấy mọi tuyến chạm vùng
        gs = [x["gia"] for x in bang if x["vung"] == [v]] or [x["gia"] for x in bang if v in x["vung"]]
        if gs:
            ra[v] = float(statistics.median_high(gs))
    return ra


def gia_hdv_bang(db: Session, tk: dict, so_ngay: int, ngay: date) -> dict | None:
    """Thù lao HDV × số ngày, ngày lễ Tết ×2 (lịch lễ Tết ở màn /tour-doan).
      1. Trùng tuyến (đúng tập địa danh) → đơn giá tuyến ấy; nhiều bản thì số ngày gần nhất, bằng nhau lấy giá cao.
      2. Có tuyến chung địa danh → trung vị các tuyến ấy.
      3. Không có → suy theo VÙNG: giá vùng = trung vị các tuyến nằm trong vùng; chuyến đi nhiều vùng lấy vùng cao nhất.
    """
    bang = bang_hdv(db, ngay)
    if not bang:
        return None
    diem = [h["ten"] for h in tk["diem"]]
    khop = [x for x in bang if khop_tuyen(x["route"], diem)]
    if khop:
        # Chủ tịch 04/11/2026: tuyến có nhiều mức (Đà Lạt 3N2Đ 600k / 3N3Đ 500k) → lấy mức cao
        x = sorted(khop, key=lambda x: (-x["gia"], abs(x["days"] - so_ngay)))[0]
        return _hdv_dong(db, tk, so_ngay, x["gia"], f"{x['route']} (bảng thù lao HDV)", f"guide_rates:{x['id']}")
    # 2. Tuyến có chung địa danh với hành trình (khách đi Quy Nhơn → tuyến «Quy Nhơn Phú Yên») → trung vị các tuyến ấy
    import statistics
    co = set().union(*[dia_danh(d) for d in diem]) if diem else set()
    gan = [x for x in bang if co & {y for m in _manh_tuyen(x["route"]) for y in dia_danh(m)}]
    if gan:
        gia = float(statistics.median_high([x["gia"] for x in gan]))
        return _hdv_dong(db, tk, so_ngay, gia, f"tương tự tuyến {', '.join(x['route'] for x in gan[:3])} (bảng thù lao HDV)",
                         "guide_rates:gan")
    gv = gia_vung_hdv(bang)
    vs = [(gv[v], v) for d in diem for v in vung_cua(d) if v in gv]
    if not vs:
        return None
    gia, v = max(vs)
    return _hdv_dong(db, tk, so_ngay, gia, f"vùng {v} (suy từ bảng thù lao HDV)", f"guide_rates:vung:{v}")


def ngay_le_luat(nam: int) -> dict[date, str]:
    """TK-1f · Ngày lễ Tết MÁY TÍNH theo luật (Chủ tịch 04/11/2026: «áp dụng theo đúng ngày nghỉ»; Tết Âm lịch tính
    mùng 1–4; Quốc khánh lấy 1/9 và 2/9). Điều 112 Bộ luật Lao động + Nghị quyết 24/4/2026 (24/11 từ 1/7/2026)."""
    from app.services.am_lich import am_sang_duong
    ra = {date(nam, 1, 1): "Tết Dương lịch", date(nam, 4, 30): "Giải phóng miền Nam", date(nam, 5, 1): "Quốc tế Lao động",
          date(nam, 9, 1): "Quốc khánh (ngày liền kề)", date(nam, 9, 2): "Quốc khánh"}
    if date(nam, 11, 24) >= date(2026, 7, 1):
        ra[date(nam, 11, 24)] = "Ngày Văn hóa Việt Nam"
    for i in range(1, 5):
        ra[am_sang_duong(i, 1, nam)] = f"Tết Nguyên đán (mùng {i})"
    ra[am_sang_duong(10, 3, nam)] = "Giỗ Tổ Hùng Vương (10/3 âm lịch)"
    return ra


def so_ngay_le(db: Session, tu: date, so_ngay: int) -> int:
    """Số ngày của chuyến rơi vào ngày lễ Tết: lịch máy tính theo luật ∪ ngày Điều hành thêm (TK-1e, TK-1f)."""
    den = tu + timedelta(days=max(0, so_ngay - 1))
    le = set()
    for y in range(tu.year, den.year + 1):
        le |= {d for d in ngay_le_luat(y) if tu <= d <= den}
    le |= set(db.execute(select(NgayLeTet.ngay).where(NgayLeTet.ngay >= tu, NgayLeTet.ngay <= den)).scalars())
    return len(le)


def _hdv_dong(db: Session, tk: dict, so_ngay: int, gia: float, nguon_ten: str, nguon: str) -> dict:
    """Một dòng HDV: đơn giá × số ngày, ngày lễ Tết ×2 (Chủ tịch 04/11/2026)."""
    le = so_ngay_le(db, date.fromisoformat(tk["ngay_di"]), so_ngay)
    return {"ten": f"Hướng dẫn viên suốt tuyến · {nguon_ten}",
            "chi_tiet": f"{so_ngay} ngày" + (f", {le} ngày lễ Tết ×2" if le else ""),
            "von": gia * (so_ngay + le), "nguon": nguon}


# Thứ tự hỏi giá vé: nguồn đầu tiên trả lời được thì dùng. Nối API vé (hãng bay / nhà cung cấp vé) = thêm hàm cùng
# chữ ký vào ĐẦU danh sách, trả kèm «nguon» và «luc» (thời điểm lấy giá — giá vé đổi liên tục).
NGUON_VE = [_ve_dieu_hanh_nhap]


def gia_ve(db: Session, tu: str, den: str, ngay: date, hang_ve: str, pv: str) -> dict | None:
    for f in NGUON_VE:
        r = f(db, tu, den, ngay, hang_ve, pv)
        if r:
            return r
    return None


# ══ DỰ TOÁN ═════════════════════════════════════════════════════════════════════════════════════════
def du_toan(db: Session, tk: dict) -> dict:
    """Tính lại toàn bộ từ dữ liệu VTOS. Trả dòng có cả VỐN và BÁN — lớp gọi lọc theo người xem."""
    from app.models.khach_san_vtd import GoiGiaVtd, KhachSanVtd, LoaiPhongVtd
    from app.models.nha_hang import NhaHang, ThucDonNhaHang
    from app.services import khach_san_vtd as KS
    from app.services import nha_hang as NH

    pv, di = tk["pham_vi"], date.fromisoformat(tk["ngay_di"])
    nl, te, eb = tk["khach"]["nl"], tk["khach"]["te"], tk["khach"]["eb"]
    ngoi, tong_khach = nl + te, nl + te + eb
    ph = tk["phong"]
    so_phong = ph["p2"] + ph["p3"] + ph["p1"]
    N = khung(tk)
    so_ngay = len(N)
    dong, thieu, canh, bg, kbg = [], [], [], [], []

    def them(nhom: str, ten: str, chi_tiet: str, von: float):
        dong.append({"nhom": nhom, "ten": ten, "chi_tiet": chi_tiet, "von": round(von), "ban": ban(von)})

    def thieu_gia(nhom: str, ten: str, ly_do: str):
        thieu.append({"nhom": nhom, "ten": ten, "ly_do": ly_do})

    # Phòng: đủ chỗ ngủ chưa (em bé ngủ chung)
    cho_ngu = 2 * ph["p2"] + 3 * ph["p3"] + ph["p1"]
    if so_phong == 0:
        canh.append("Chưa xếp phòng")
    elif cho_ngu < ngoi:
        canh.append(f"Phòng chỉ đủ {cho_ngu}/{ngoi} khách — thêm phòng")

    # ── khách sạn theo từng điểm đến
    bua_sang: dict[int, bool] = {}
    off = 0
    for hi, h in enumerate(tk["diem"]):
        dem = h["dem"]
        if dem > 0:
            vao, ra_ = di + timedelta(days=off), di + timedelta(days=off + dem)
            ks = h["ks"]
            g = db.get(GoiGiaVtd, ks["goi_id"]) if ks.get("goi_id") else None
            lp = db.get(LoaiPhongVtd, g.loai_phong_id) if g else None
            k = db.get(KhachSanVtd, lp.khach_san_id) if lp else None
            if g and lp and k and k.id == ks.get("khach_san_id") and k.hien_cong and not k.ngung and lp.dang_ban \
                    and g.trang_thai == "da_duyet" and g.dang_ban:
                p = KS.gia_luu(g, KS._mua_cua(db, [g.id]).get(g.id, []), vao, ra_)
                if p is None:
                    thieu_gia("Khách sạn", f"{k.ten} · {lp.ten}", f"chưa có giá cho {vao:%d/%m}–{ra_:%d/%m}")
                elif so_phong:
                    von = p["tong"] * so_phong * (1 + float(k.thue_phi_pt or 0) / 100)
                    them("Khách sạn", f"{k.ten} · {lp.ten} · {g.ten}", f"{so_phong} phòng × {dem} đêm ({h['ten']})", von)
                    bg.append(f"{k.ten}" + (f" ({k.sao}★)" if k.sao else "") + f" tại {h['ten']}, {dem} đêm")
                    if ph["p3"] or ph["p1"]:
                        canh.append(f"{k.ten}: phòng 3 người / phòng đơn tạm tính theo giá gói «{g.ten}» — Điều hành xác nhận phụ thu")
                    for d in range(dem):
                        bua_sang[off + d] = bool(g.bua_sang)
            elif ks.get("ten_khac"):
                thieu_gia("Khách sạn", ks["ten_khac"], f"khách tự ghi tại {h['ten']} — Sales báo giá")
                bg.append(f"Khách sạn {ks['ten_khac']} tại {h['ten']}, {dem} đêm")
            else:
                thieu_gia("Khách sạn", h["ten"], f"chưa chọn khách sạn cho {dem} đêm")
        off += max(1, dem)

    # ── bữa ăn từng ngày
    co_sang = any(bua_sang.get(i - 1) for i in range(1, so_ngay))
    for d in N:
        x = tk["ngay"][d["i"]]
        if d["i"] > 0 and (d["i"] - 1) in bua_sang and not bua_sang[d["i"] - 1]:
            kbg.append("Ăn sáng (gói phòng không gồm ăn sáng)")
        for k_, ten_b in (("trua", "trưa"), ("toi", "tối")):
            b = x[k_]
            if b.get("tu_tuc"):
                kbg.append(f"Bữa {ten_b} tự túc")
            elif b.get("thuc_don_id"):
                td = db.get(ThucDonNhaHang, b["thuc_don_id"])
                n = db.get(NhaHang, td.nha_hang_id) if td else None
                ngay_an = date.fromisoformat(d["ngay"])
                if not (td and n and NH.mo_dat(db, n, None, ngay_an) and NH._con_ban(td, ngay_an)):
                    thieu_gia("Ăn uống", f"Ngày {d['i'] + 1} bữa {ten_b}", "thực đơn không còn mở đặt")
                    continue
                gnl = float(td.gia_nguoi_lon or 0)
                gte = float(td.gia_tre_em) if td.gia_tre_em is not None else gnl
                if gnl <= 0:
                    thieu_gia("Ăn uống", f"{n.ten} · {td.ten}", "thực đơn chưa có giá")
                    continue
                them("Ăn uống", f"Ngày {d['i'] + 1} · {ten_b} · {n.ten} — {td.ten}",
                     f"{nl} NL" + (f" + {te} trẻ em" if te else ""), gnl * nl + gte * te)
                if (td.so_khach_toi_thieu or 1) > ngoi:
                    canh.append(f"{n.ten} · {td.ten}: tối thiểu {td.so_khach_toi_thieu} khách")
                bg.append("Các bữa ăn theo chương trình")
            elif b.get("khac"):
                thieu_gia("Ăn uống", f"Ngày {d['i'] + 1} bữa {ten_b}: {b['khac']}", "khách tự ghi — Sales báo giá")
                bg.append("Các bữa ăn theo chương trình")
    if co_sang:
        bg.append("Ăn sáng tại khách sạn")

    # ── phương tiện từng chặng
    xe_ds = _dg_hieu_luc(db, "xe", pv, di)
    for d in N:
        if d["chang_i"] is None:
            continue
        c = tk["chang"][d["chang_i"]]
        ten_c = f"{d['tu']} → {d['den']}"
        if c["pt"] == "bay":
            v = gia_ve(db, d["tu"], d["den"], date.fromisoformat(d["ngay"]), c["hang_ve"], pv)
            if v is None:
                thieu_gia("Vé máy bay", ten_c, "Sales báo giá theo chuyến bay")
            else:
                gte = v["te"] if v["te"] is not None else v["nl"]
                von = v["nl"] * nl + gte * te + (v["eb"] or 0) * eb
                them("Vé máy bay", f"{ten_c} · {HANG_VE[c['hang_ve']]}" + (f" · {c['hang_bay']}" if c["hang_bay"] else ""),
                     f"{nl} NL" + (f" + {te} trẻ em" if te else "") + (f" + {eb} em bé" if eb else ""), von)
                if eb and v["eb"] is None:
                    thieu_gia("Vé máy bay", f"{ten_c} · em bé", "chưa có giá vé em bé — Sales báo")
            bg.append("Vé máy bay theo chương trình" + (f" ({c['hang_bay']})" if c["hang_bay"] else ""))
        elif c["pt"] in ("tau", "thuyen"):
            thieu_gia(PHUONG_TIEN[c["pt"]], ten_c, "Sales báo giá")
            bg.append(f"{PHUONG_TIEN[c['pt']]} chặng {ten_c}")
        elif c["pt"] == "khac":
            thieu_gia("Phương tiện", f"{ten_c}: {c['khac'] or 'khách tự ghi'}", "Sales báo giá")

    # ── xe theo đoàn suốt hành trình. TK-1b (Chủ tịch 04/11/2026): trong nước lấy BẢNG GIÁ XE có sẵn trên VTOS —
    # trùng tuyến + số ngày thì giá trọn chuyến cột xe nhà (xe 45 chỗ); lệch tuyến thì đơn giá ngày của xe × số ngày;
    # không có nữa mới rơi về đơn giá đoàn Điều hành nhập. Nước ngoài: đơn giá đoàn (xe tại điểm đến).
    xe_xong = False
    if pv == "dn":
        r = gia_xe_bang(db, tk, so_ngay, ngoi, di)
        if r:
            them("Xe", r["ten"], r["chi_tiet"], r["von"])
            bg.append(f"Xe du lịch đời mới đưa đón theo chương trình ({r['loai']})")
            xe_xong = True
    if not xe_xong:
        x = chon_xe(xe_ds, ngoi)
        if x:
            xe, so = x
            them("Xe", f"{xe.ten}", f"{so} xe × {so_ngay} ngày", float(xe.gia) * so * so_ngay)
            bg.append(f"Xe du lịch đời mới đưa đón theo chương trình ({xe.ten})")
        else:
            thieu_gia("Xe", f"Xe cho {ngoi} khách", "chưa có tuyến hoặc đơn giá ngày phù hợp")

    # ── dịch vụ cả chuyến
    xa = pv == "nn" and any(h["ten"] in TOUR_XA for h in tk["diem"])
    dvs = list(tk["dich_vu"])
    if xa and "hdv" in dvs:
        dvs[dvs.index("hdv")] = "truong_doan"
    for k_ in dvs:
        if k_ == "hdv" and pv == "dn":          # TK-1b: bảng thù lao HDV theo tuyến có sẵn trên VTOS
            r = gia_hdv_bang(db, tk, so_ngay, di)
            if r:
                them("Dịch vụ", r["ten"], r["chi_tiet"], r["von"])
                bg.append("Hướng dẫn viên suốt tuyến")
                continue
        dg = _mot_gia(db, k_, pv, di)
        ten = LOAI_DON_GIA[k_][0] if k_ in LOAI_DON_GIA else DICH_VU_KHACH.get(k_, k_)
        if dg is None:
            thieu_gia("Dịch vụ", ten, "Điều hành chưa nhập đơn giá")
            continue
        dv_ = LOAI_DON_GIA[k_][1]
        sl = {"ngay": so_ngay, "khach": tong_khach if k_ in ("bao_hiem", "visa") else ngoi,
              "khach_ngay": ngoi * so_ngay, "doan": 1}[dv_]
        them("Dịch vụ", dg.ten, f"{sl} {DON_VI[dv_]}" if dv_ != "doan" else "trọn đoàn", float(dg.gia) * sl)
        bg.append(dg.ten)
    if "bao_hiem" not in dvs:
        kbg.append("Bảo hiểm du lịch")
    if pv == "nn" and "visa" not in dvs:
        kbg.append("Visa nhập cảnh")

    # ── điểm tham quan: GĐ1 chưa có danh mục giá vé
    tq = [t for x_ in tk["ngay"] for t in x_["tham_quan"]]
    if tq:
        thieu_gia("Vé tham quan", f"{len(tq)} điểm tham quan", "Sales báo giá vé vào cổng")
        bg.append("Tham quan theo chương trình")
    kbg += ["Chi tiêu cá nhân, giặt ủi, điện thoại", "Thuế VAT nếu cần hóa đơn công ty (Sales báo)"]
    if pv == "nn":
        kbg.append("Tips tài xế và HDV địa phương — trưởng đoàn thu của khách và chi lại tại điểm đến")

    tong_von = sum(x_["von"] for x_ in dong)
    tong_ban = sum(x_["ban"] for x_ in dong)
    moi = round(tong_ban / max(1, ngoi)) if tong_ban else None
    if tk.get("ngan_sach") and moi and moi > tk["ngan_sach"]:
        canh.append(f"Tạm tính {moi:,} đ/khách vượt ngân sách {tk['ngan_sach']:,} đ/khách".replace(",", "."))
    bien = (tong_ban - tong_von) / tong_ban if tong_ban else None
    return {"dong": dong, "thieu_gia": thieu, "canh_bao": list(dict.fromkeys(canh)),
            "bao_gom": list(dict.fromkeys(bg)), "khong_bao_gom": list(dict.fromkeys(kbg)),
            "tong_ban": tong_ban, "tong_von": tong_von, "moi_khach": moi, "bien": round(bien, 4) if bien is not None else None,
            "can_chu_tich_duyet": bien is not None and bien < NGUONG_DUYET - 1e-9,
            "so_ngay": so_ngay, "so_dem": sum(h["dem"] for h in tk["diem"]), "so_khach": tong_khach,
            "ngay_ve": N[-1]["ngay"], "khung": N, "truong_doan": xa, "bien_tam_tinh": BIEN_TAM_TINH,
            "tinh_luc": datetime.now().isoformat(timespec="seconds")}


def cho_khach(dt: dict) -> dict:
    """Bản khách / Sales thấy: bỏ giá vốn và biên."""
    o = {k: v for k, v in dt.items() if k not in ("tong_von", "bien", "can_chu_tich_duyet", "bien_tam_tinh")}
    o["dong"] = [{k: v for k, v in x.items() if k != "von"} for x in dt.get("dong", [])]
    return o


# ══ CỔNG KHÁCH ══════════════════════════════════════════════════════════════════════════════════════
def _khach(tk: TaiKhoanNgoai) -> None:
    from app.services import cong_khach as K
    try:
        K.la_khach_hoac_co_dong(tk)
    except K.LoiKhach as ex:
        raise LoiThietKe(str(ex), 403)


def khung_cong(db: Session, hom_nay: date | None = None) -> dict:
    """Những gì đang có nguồn giá — để màn thiết kế đánh dấu «có giá» / «Sales báo giá»."""
    from app.services import khach_san_vtd as KS
    from app.services import nha_hang as NH
    hn = hom_nay or date.today()
    dg = db.execute(select(DonGiaDoan).where(DonGiaDoan.trang_thai == "hieu_luc",
                                             or_(DonGiaDoan.den_ngay.is_(None), DonGiaDoan.den_ngay >= hn))).scalars().all()
    co = {pv: sorted({x.loai for x in dg if x.pham_vi in (pv, "ca_hai")}) for pv in ("dn", "nn")}
    return {"ks_tinh": sorted({k.tinh_thanh for k in KS._hien(db) if k.tinh_thanh}),
            "nh_tinh": sorted({o["tinh_thanh"] for _n, o in NH._nh_hien(db, hn) if o["mo_dat"] and o["thuc_don"]}),
            "co_gia": co, "ve_chang": sorted({(x.tu_diem, x.den_diem) for x in dg if x.loai == "ve_may_bay"}),
            "dich_vu": DICH_VU_KHACH, "phuong_tien": PHUONG_TIEN, "hang_ve": HANG_VE, "nhom": NHOM, "nhip": NHIP,
            "tour_xa": sorted(TOUR_XA)}


def nguon(db: Session, diem: str, vao, ra, nl: int = 2, te: int = 0, so_phong: int = 1, hom_nay: date | None = None) -> dict:
    """Khách sạn (gói bán được cho các đêm ở điểm này) và nhà hàng (thực đơn đang mở) — giá đã là GIÁ BÁN tạm tính."""
    from app.services import khach_san_vtd as KS
    from app.services import nha_hang as NH
    hn = hom_nay or date.today()
    ks_ra = []
    vao_, ra_ = _ngay(vao), _ngay(ra)
    if vao_ and ra_ and ra_ > vao_ and vao_ > hn:
        ks = [k for k in KS._hien(db) if khop_diem(diem, k.tinh_thanh)]
        phong = KS._phong_ban_duoc(db, [k.id for k in ks], vao_, ra_, max(1, nl), te, max(1, so_phong)) if ks else {}
        for k in ks:
            ps = []
            for p in phong.get(k.id, []):
                gs = [{"id": g["id"], "ten": g["ten"], "bua_sang": g["bua_sang"], "mien_phi_huy": g["mien_phi_huy"],
                       "gia_dem": ban(g["gia_dem"] * (1 + float(k.thue_phi_pt or 0) / 100)),
                       "tong_phong": ban(g["tong"] * (1 + float(k.thue_phi_pt or 0) / 100))} for g in p["goi"]]
                if gs:
                    ps.append({"id": p["id"], "ten": p["ten"], "giuong": p["giuong"], "suc_chua": p["suc_chua"], "goi": gs})
            ks_ra.append({"id": k.id, "ten": k.ten, "sao": k.sao, "khu_vuc": k.khu_vuc, "phong": ps,
                          "gia_tu": min((g["gia_dem"] for p in ps for g in p["goi"]), default=None)})
        ks_ra.sort(key=lambda o: (o["gia_tu"] is None, o["gia_tu"] or 0))
    nh_ra = []
    for _n, o in NH._nh_hien(db, hn):
        if not (o["mo_dat"] and o["thuc_don"] and khop_diem(diem, o["tinh_thanh"])):
            continue
        nh_ra.append({"id": o["id"], "ten": o["ten"], "am_thuc": o["am_thuc"], "khu_vuc": o["khu_vuc"],
                      "thuc_don": [{"id": t["id"], "ten": t["ten"], "loai": t["loai_ten"],
                                    "gia_nguoi_lon": ban(t["gia_nguoi_lon"]) if t["gia_nguoi_lon"] else None,
                                    "gia_tre_em": ban(t["gia_tre_em"]) if t["gia_tre_em"] is not None else None,
                                    "so_khach_toi_thieu": t["so_khach_toi_thieu"]} for t in o["thuc_don"]]})
    return {"diem": diem, "khach_san": ks_ra, "nha_hang": nh_ra}


def tinh_cong(db: Session, tk_: TaiKhoanNgoai, d: dict, hom_nay: date | None = None) -> dict:
    _khach(tk_)
    tk = chuan_hoa(d, hom_nay)
    return {"thiet_ke": tk, "du_toan": cho_khach(du_toan(db, tk))}


def _tom_tat(tk: dict, dt: dict) -> str:
    k = tk["khach"]
    hanh = " → ".join(f"{h['ten']} {h['dem']}đ" for h in tk["diem"])
    gia = f"tạm tính {dt['tong_ban']:,} đ".replace(",", ".") if dt["tong_ban"] else "chưa có tạm tính"
    return (f"Tự thiết kế ({'nước ngoài' if tk['pham_vi'] == 'nn' else 'trong nước'}): {tk['khoi_hanh']} → {hanh} · "
            f"{k['nl']} NL" + (f" + {k['te']} TE" if k["te"] else "") + (f" + {k['eb']} EB" if k["eb"] else "")
            + f" · {gia} · {len(dt['thieu_gia'])} mục Sales báo giá")


def gui(db: Session, tk_: TaiKhoanNgoai, d: dict, now: datetime | None = None) -> dict:
    """Gửi thiết kế cho Sales. Có «ma» của chính khách = phiên bản mới của yêu cầu cũ (không tạo yêu cầu thứ hai)."""
    from app.models.cong_khach import YeuCauKhach
    from app.services import cong_khach as K
    _khach(tk_)
    now = now or datetime.now()
    tk = chuan_hoa(d.get("thiet_ke") or {}, now.date())
    dt = du_toan(db, tk)
    tom = _tom_tat(tk, dt)
    ma = str(d.get("ma") or "").strip()
    cu = None
    if ma:
        cu = db.execute(select(ThietKeDoan).where(ThietKeDoan.ma == ma).order_by(ThietKeDoan.phien_ban.desc())).scalars().first()
        if cu is None or cu.tai_khoan_id != tk_.id:
            raise LoiThietKe("Không tìm thấy thiết kế này", 404)
    if cu is None:
        if not d.get("dong_y"):
            raise LoiThietKe("Đánh dấu ô xác nhận: tạm tính chưa phải báo giá, chưa giữ chỗ và chưa thu tiền")
        try:
            yc = K.gui_yeu_cau(db, tk_, "tour_doan", None, tk["khach"]["nl"] + tk["khach"]["te"] + tk["khach"]["eb"],
                               str(d.get("dien_thoai") or ""), date.fromisoformat(tk["ngay_di"]), tom[:1000], True, now)
        except K.LoiKhach as ex:
            raise LoiThietKe(str(ex))
        yc.ten_tour = ("Tự thiết kế: " + " → ".join(h["ten"] for h in tk["diem"]))[:200]
        yc.tam_tinh = int(dt["tong_ban"]) if dt["tong_ban"] else None
        so = (db.execute(select(func.max(ThietKeDoan.id))).scalar() or 0) + 1
        ma, pb, yid = f"TK-{so:06d}", 1, yc.id
    else:
        pb, yid = cu.phien_ban + 1, cu.yeu_cau_id
        for x in db.execute(select(ThietKeDoan).where(ThietKeDoan.ma == ma, ThietKeDoan.trang_thai == "da_gui")).scalars():
            x.trang_thai = "thay_the"
        from app.services import bao_gia_doan as BG       # TK-2: báo giá của phiên bản cũ hết hiệu lực
        BG.thay_the_khi_sua(db, ma)
        yc = db.get(YeuCauKhach, yid) if yid else None
        if yc is not None:
            yc.tam_tinh = int(dt["tong_ban"]) if dt["tong_ban"] else None
            yc.so_khach = tk["khach"]["nl"] + tk["khach"]["te"] + tk["khach"]["eb"]
            yc.ngay_mong_muon = date.fromisoformat(tk["ngay_di"])
            yc.ghi_chu = ((yc.ghi_chu or "") + f"\n[Phiên bản {pb} · {now:%d/%m %H:%M}] {tom}")[-2000:]
    row = ThietKeDoan(ma=ma, phien_ban=pb, tai_khoan_id=tk_.id, yeu_cau_id=yid, thiet_ke=tk, du_toan=dt,
                      tong_ban=dt["tong_ban"] or None, tong_von=dt["tong_von"] or None, ngay_di=date.fromisoformat(tk["ngay_di"]),
                      so_khach=dt["so_khach"], tom_tat=tom, trang_thai="da_gui", tao_luc=now)
    db.add(row)
    R.audit(db, f"cong:{tk_.id}", "khach", "thiet_ke_doan_gui", f"thiet_ke_doan:{ma}#{pb}",
            after={"tong_ban": dt["tong_ban"], "thieu_gia": len(dt["thieu_gia"])})
    db.commit()
    return {"ma": ma, "phien_ban": pb, "du_toan": cho_khach(dt),
            "message": f"Đã gửi thiết kế {ma} (phiên bản {pb}) — Sales Vietourist liên hệ báo giá chính thức"}


def cua_toi(db: Session, tk_: TaiKhoanNgoai) -> list[dict]:
    _khach(tk_)
    ds = db.execute(select(ThietKeDoan).where(ThietKeDoan.tai_khoan_id == tk_.id, ThietKeDoan.trang_thai == "da_gui")
                    .order_by(ThietKeDoan.tao_luc.desc()).limit(30)).scalars().all()
    from app.services import bao_gia_doan as BG
    ra_ = [{"ma": x.ma, "phien_ban": x.phien_ban, "tom_tat": x.tom_tat, "ngay_di": x.ngay_di.isoformat() if x.ngay_di else None,
            "tong_ban": x.tong_ban, "gui_luc": x.tao_luc.isoformat(timespec="minutes"), "thiet_ke": x.thiet_ke,
            "du_toan": cho_khach(x.du_toan or {}), "bao_gia": BG.cho_khach(db, tk_, x.ma)} for x in ds]   # TK-2
    db.commit()
    return ra_


# ══ VTOS ════════════════════════════════════════════════════════════════════════════════════════════
def _ra(x: ThietKeDoan, von: bool, db: Session | None = None) -> dict:
    dt = x.du_toan or {}
    bg = None
    if db is not None:                                   # TK-2: báo giá mới nhất của phiên bản này
        from app.models.thiet_ke_doan import BaoGiaDoan
        from app.services import bao_gia_doan as BG
        b = db.execute(select(BaoGiaDoan).where(BaoGiaDoan.thiet_ke_id == x.id).order_by(BaoGiaDoan.id.desc())).scalars().first()
        if b is not None:
            BG._het_han_neu_qua(b, datetime.now())
            bg = BG.ra(b, von)
    return {"id": x.id, "ma": x.ma, "phien_ban": x.phien_ban, "yeu_cau_id": x.yeu_cau_id, "tom_tat": x.tom_tat,
            "ngay_di": x.ngay_di.isoformat() if x.ngay_di else None, "so_khach": x.so_khach, "tong_ban": x.tong_ban,
            "gui_luc": x.tao_luc.isoformat(timespec="minutes"), "trang_thai": x.trang_thai, "thiet_ke": x.thiet_ke,
            "du_toan": dt if von else cho_khach(dt), **({"tong_von": x.tong_von} if von else {}), "bao_gia": bg}


def ds_vtos(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM)
    von = _co(u, VAI_GIA_VON)
    ds = db.execute(select(ThietKeDoan).where(ThietKeDoan.trang_thai == "da_gui").order_by(ThietKeDoan.tao_luc.desc())
                    .limit(200)).scalars().all()
    return {"thiet_ke": [_ra(x, von, db) for x in ds], "bien_tam_tinh": BIEN_TAM_TINH, "nguong_duyet": NGUONG_DUYET,
            "hdv_vung": gia_vung_hdv(bang_hdv(db, date.today())) if von else {},
            "duoc": {"gia_von": von, "nhap_gia": _co(u, VAI_NHAP_GIA), "duyet_gia": _co(u, VAI_DUYET_GIA),
                     "lap_bao_gia": _co(u, VAI_NHAP_GIA), "duyet_bao_gia": _co(u, VAI_DUYET_GIA), "toan_quyen": _co(u, TOAN_QUYEN),
                     "ten": u.username}}


def lich_su(db: Session, u: User, ma: str) -> list[dict]:
    _quyen(u, VAI_XEM)
    von = _co(u, VAI_GIA_VON)
    return [_ra(x, von) for x in db.execute(select(ThietKeDoan).where(ThietKeDoan.ma == ma)
                                            .order_by(ThietKeDoan.phien_ban.desc())).scalars()]


def _dg_out(x: DonGiaDoan) -> dict:
    return {"id": x.id, "loai": x.loai, "loai_ten": LOAI_DON_GIA.get(x.loai, (x.loai,))[0], "ten": x.ten, "pham_vi": x.pham_vi,
            "don_vi": DON_VI.get(LOAI_DON_GIA.get(x.loai, ("", "doan"))[1], ""), "tu_cho": x.tu_cho, "gia": x.gia,
            "tu_diem": x.tu_diem, "den_diem": x.den_diem, "hang_ve": x.hang_ve, "gia_tre_em": x.gia_tre_em, "gia_em_be": x.gia_em_be,
            "tu_ngay": x.tu_ngay.isoformat() if x.tu_ngay else None, "den_ngay": x.den_ngay.isoformat() if x.den_ngay else None,
            "ghi_chu": x.ghi_chu, "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_DG.get(x.trang_thai, x.trang_thai),
            "tao_boi": x.tao_boi, "duyet_boi": x.duyet_boi, "ly_do": x.ly_do}


def ds_don_gia(db: Session, u: User) -> dict:
    _quyen(u, VAI_GIA_VON, "Đơn giá đoàn là giá vốn — chỉ Điều hành, Kế toán, BKS, Chủ tịch, TGĐ xem")
    ds = db.execute(select(DonGiaDoan).order_by(DonGiaDoan.loai, DonGiaDoan.trang_thai, DonGiaDoan.id.desc())).scalars().all()
    return {"don_gia": [_dg_out(x) for x in ds], "loai": {k: {"ten": v[0], "don_vi": DON_VI[v[1]]} for k, v in LOAI_DON_GIA.items()},
            "pham_vi": PHAM_VI, "hang_ve": HANG_VE, "trang_thai": TRANG_THAI_DG,
            "duoc": {"nhap": _co(u, VAI_NHAP_GIA), "duyet": _co(u, VAI_DUYET_GIA)}}


def _tien(v, ten: str, rong: bool = False) -> float | None:
    if v in (None, ""):
        if rong:
            return None
        raise LoiThietKe(f"Nhập {ten}")
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LoiThietKe(f"{ten} không hợp lệ")
    if x < 0 or x > 10**10:
        raise LoiThietKe(f"{ten} không hợp lệ")
    return x


def luu_don_gia(db: Session, u: User, d: dict, dg_id: int | None = None, now: datetime | None = None) -> dict:
    """Điều hành nhập / sửa. Mọi lần lưu đưa dòng về «chờ duyệt» — giá chưa duyệt không vào tạm tính."""
    _quyen(u, VAI_NHAP_GIA, "Chỉ Điều hành nhập đơn giá đoàn")
    now = now or datetime.now()
    loai = d.get("loai")
    if loai not in LOAI_DON_GIA:
        raise LoiThietKe("Chọn loại dịch vụ")
    ten = _sach(d.get("ten"), 160)
    if not ten:
        raise LoiThietKe("Nhập tên dịch vụ")
    pv = d.get("pham_vi") if d.get("pham_vi") in PHAM_VI else "ca_hai"
    o = {"loai": loai, "ten": ten, "pham_vi": pv, "gia": _tien(d.get("gia"), "giá"),
         "tu_ngay": _ngay(d.get("tu_ngay")), "den_ngay": _ngay(d.get("den_ngay")), "ghi_chu": _sach(d.get("ghi_chu"), 300),
         "tu_cho": None, "tu_diem": "", "den_diem": "", "hang_ve": "", "gia_tre_em": None, "gia_em_be": None}
    if o["tu_ngay"] and o["den_ngay"] and o["den_ngay"] < o["tu_ngay"]:
        raise LoiThietKe("Ngày hết hiệu lực phải sau ngày bắt đầu")
    if loai == "xe":
        o["tu_cho"] = _so(d.get("tu_cho"), 0, 80)
        if not o["tu_cho"]:
            raise LoiThietKe("Nhập số chỗ khách của xe")
    if loai == "ve_may_bay":
        o["tu_diem"], o["den_diem"] = _sach(d.get("tu_diem"), 80), _sach(d.get("den_diem"), 80)
        if not o["tu_diem"] or not o["den_diem"]:
            raise LoiThietKe("Nhập điểm đi và điểm đến của chặng bay")
        o["hang_ve"] = d.get("hang_ve") if d.get("hang_ve") in HANG_VE else "pho_thong"
        o["gia_tre_em"] = _tien(d.get("gia_tre_em"), "giá trẻ em", True)
        o["gia_em_be"] = _tien(d.get("gia_em_be"), "giá em bé", True)
    if dg_id:
        x = db.get(DonGiaDoan, dg_id)
        if x is None:
            raise LoiThietKe("Không có đơn giá này", 404)
        truoc = _dg_out(x)
    else:
        x, truoc = DonGiaDoan(tao_boi=u.username, tao_luc=now), None
        db.add(x)
    for k, v in o.items():
        setattr(x, k, v)
    x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do, x.tao_boi = "cho_duyet", "", None, "", u.username
    db.flush()
    R.audit(db, u.username, u.role, "don_gia_doan_luu", f"don_gia_doan:{x.id}", before=truoc, after=_dg_out(x))
    db.commit()
    return _dg_out(x)


def duyet_don_gia(db: Session, u: User, dg_id: int, dong_y: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    _quyen(u, VAI_DUYET_GIA, "Chỉ TP Điều hành, Chủ tịch, TGĐ duyệt đơn giá đoàn")
    x = db.get(DonGiaDoan, dg_id)
    if x is None:
        raise LoiThietKe("Không có đơn giá này", 404)
    if x.trang_thai != "cho_duyet":
        raise LoiThietKe("Dòng này không ở trạng thái chờ duyệt", 409)
    if x.tao_boi == u.username and u.role not in TOAN_QUYEN:
        raise LoiThietKe("Người nhập không tự duyệt đơn giá của mình", 403)
    if not dong_y and not _sach(ly_do):
        raise LoiThietKe("Ghi lý do từ chối")
    x.trang_thai = "hieu_luc" if dong_y else "tu_choi"
    x.duyet_boi, x.duyet_luc, x.ly_do = u.username, now or datetime.now(), _sach(ly_do, 300)
    R.audit(db, u.username, u.role, "don_gia_doan_duyet", f"don_gia_doan:{x.id}", after={"trang_thai": x.trang_thai})
    db.commit()
    return _dg_out(x)


def ngung_don_gia(db: Session, u: User, dg_id: int, now: datetime | None = None) -> dict:
    _quyen(u, VAI_DUYET_GIA, "Chỉ TP Điều hành, Chủ tịch, TGĐ ngừng đơn giá")
    x = db.get(DonGiaDoan, dg_id)
    if x is None:
        raise LoiThietKe("Không có đơn giá này", 404)
    x.trang_thai = "ngung"
    R.audit(db, u.username, u.role, "don_gia_doan_ngung", f"don_gia_doan:{x.id}")
    db.commit()
    return _dg_out(x)


# ══ TK-1e · LỊCH NGÀY LỄ TẾT (Điều hành nhập) ════════════════════════════════════════════════════════
def ds_ngay_le(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM)
    ds = db.execute(select(NgayLeTet).order_by(NgayLeTet.ngay)).scalars().all()
    nam = date.today().year
    luat = sorted({**ngay_le_luat(nam), **ngay_le_luat(nam + 1)}.items())
    return {"ngay_le": [{"id": x.id, "ngay": x.ngay.isoformat(), "ten": x.ten, "tao_boi": x.tao_boi} for x in ds],
            "theo_luat": [{"ngay": d.isoformat(), "ten": t} for d, t in luat],
            "duoc": {"nhap": _co(u, VAI_NHAP_GIA)}}


def luu_ngay_le(db: Session, u: User, d: dict, now: datetime | None = None) -> dict:
    _quyen(u, VAI_NHAP_GIA, "Chỉ Điều hành nhập lịch ngày lễ Tết")
    ngay = _ngay(d.get("ngay"))
    if ngay is None:
        raise LoiThietKe("Chọn ngày")
    ten = _sach(d.get("ten"), 120)
    if not ten:
        raise LoiThietKe("Ghi tên ngày lễ (ví dụ Tết Nguyên đán, 30/4)")
    x = db.execute(select(NgayLeTet).where(NgayLeTet.ngay == ngay)).scalars().first()
    if x is None:
        x = NgayLeTet(ngay=ngay, tao_boi=u.username, tao_luc=now or datetime.now())
        db.add(x)
    x.ten = ten
    db.flush()
    R.audit(db, u.username, u.role, "ngay_le_tet_luu", f"ngay_le_tet:{ngay.isoformat()}", after={"ten": ten})
    db.commit()
    return {"id": x.id, "ngay": x.ngay.isoformat(), "ten": x.ten}


def xoa_ngay_le(db: Session, u: User, nid: int) -> dict:
    _quyen(u, VAI_NHAP_GIA, "Chỉ Điều hành sửa lịch ngày lễ Tết")
    x = db.get(NgayLeTet, nid)
    if x is None:
        raise LoiThietKe("Không có ngày này", 404)
    R.audit(db, u.username, u.role, "ngay_le_tet_xoa", f"ngay_le_tet:{x.ngay.isoformat()}", before={"ten": x.ten})
    db.delete(x)
    db.commit()
    return {"message": "Đã bỏ ngày khỏi lịch lễ Tết"}
