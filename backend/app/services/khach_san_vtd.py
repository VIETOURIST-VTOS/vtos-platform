"""KS-13 · Danh mục khách sạn hợp tác VTD — phía VTOS (nhập, duyệt, bật hiện) và phía cổng khách (tìm, xem, chọn phòng).

Xem đầu app/models/khach_san_vtd.py cho ai làm gì. Ở bước 12a khách «Gửi yêu cầu giữ phòng»: yêu cầu vào hàng chờ
KS-11 của Điều hành (dat_phong_ota.gui_yeu_cau), mang phòng khách chọn và GIÁ DO MÁY TÍNH LẠI — không tin số
trình duyệt gửi lên.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.khach_san_vtd import (AnhKhachSanVtd, CaiDatKsVtd, GoiGiaVtd, KhachSanVtd, LoaiPhongVtd, MuaGiaVtd, LOAI_CHO_O,
                                      NHOM_ANH_KS, TIEN_ICH, TRANG_THAI_ANH_KS, TRANG_THAI_GOI, CACH_TINH_TRE, CAN_XAC_NHAN,
                                      NGUON_LP, NHAN_TRE_EM, TIEN_NGHI_PHONG, TRANG_THAI_DC, NHOM_TUOI, KIEU_GIA,
                                      CHE_DO_TRE_GOI)
from app.services.nha_hang import THANH_PHO, MIEN, _co, _khong_dau

TOAN_QUYEN = ("chutich", "tgd")
VAI_NHAP = ("tp_dh", "nv_dh") + TOAN_QUYEN
VAI_DUYET = ("tp_dh",) + TOAN_QUYEN
VAI_XEM = tuple(dict.fromkeys(VAI_NHAP + ("bks", "robot_ks", "gd_kd", "tp_kd", "nv_mkt", "ptgd_mkt")))
VAI_XEM = tuple(dict.fromkeys(VAI_XEM + ("ketoan", "tn_kd", "nv_kd", "sales_admin")))   # KS-14: Kế toán, Sales đọc danh mục để xử lý đơn
ANH_TOI_DA = 50                # KS-16p (Chủ tịch 01/11/2026): mỗi khách sạn 30–50 ảnh — dưới 30 chỉ nhắc
ANH_CHUAN = 30
DEM_TOI_DA = 30
NGAY_CUOI_TUAN = (4, 5)       # đêm thứ Sáu, thứ Bảy


class LoiKhachSan(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _audit(db: Session, u: User, viec: str, ma: str, truoc=None, sau=None) -> None:
    from app.services import rules as R
    R.audit(db, u.username, u.role, viec, f"khach_san_vtd:{ma}", before=truoc, after=sau)


def _ks(db: Session, kid: int) -> KhachSanVtd:
    k = db.get(KhachSanVtd, kid)
    if k is None:
        raise LoiKhachSan("Không có khách sạn này", 404)
    return k


def _quyen(u: User, vai: tuple, viec: str) -> None:
    if not _co(u, vai):
        raise LoiKhachSan(viec, 403)


def _ma_moi(db: Session) -> str:
    n = len(db.execute(select(KhachSanVtd.id)).all()) + 1
    while db.execute(select(KhachSanVtd.id).where(KhachSanVtd.ma == f"KS-{n:03d}")).first():
        n += 1
    return f"KS-{n:03d}"


# ══ GIÁ ═══════════════════════════════════════════════════════════════════════════════════════════════
def cac_dem(vao: date, ra: date) -> list[date]:
    return [vao + timedelta(days=i) for i in range((ra - vao).days)]


def gia_luu(goi: GoiGiaVtd, mua: list[MuaGiaVtd], vao: date, ra: date) -> dict | None:
    """Tiền MỘT phòng cho cả kỳ ở (chưa thuế phí). Đêm nào không có mùa giá phủ → None (gói không bán được kỳ này)."""
    tien, niem, co_niem = 0.0, 0.0, True
    for d in cac_dem(vao, ra):
        m = next((x for x in mua if x.tu_ngay <= d <= x.den_ngay), None)
        if m is None:
            return None
        g = float(m.gia_cuoi_tuan) if (d.weekday() in NGAY_CUOI_TUAN and m.gia_cuoi_tuan) else float(m.gia_thuong)
        tien += g
        if m.gia_niem_yet:
            niem += float(m.gia_niem_yet or 0)
        else:
            co_niem = False
    so = (ra - vao).days
    return {"tong": round(tien), "gia_dem": round(tien / so), "niem_yet_dem": round(niem / so) if co_niem and niem > tien else None}


# KS-17: múi giờ của giờ chốt hủy — khách sạn trong nước theo giờ Việt Nam; giờ OTA ghi kèm khi khác.
MUI_GIO_HUY = {"Asia/Ho_Chi_Minh": "Giờ Việt Nam (GMT+7)", "UTC": "UTC (GMT+0)", "Asia/Singapore": "Singapore (GMT+8)",
               "Asia/Bangkok": "Bangkok (GMT+7)"}


def han_huy(goi: GoiGiaVtd, vao: date) -> date | None:
    return vao - timedelta(days=goi.huy_truoc_ngay) if goi.huy_truoc_ngay is not None else None


def _kiem_ky(vao, ra, hom_nay: date | None = None) -> tuple[date, date]:
    hom_nay = hom_nay or date.today()
    try:
        vao = vao if isinstance(vao, date) else date.fromisoformat(str(vao)[:10])
        ra = ra if isinstance(ra, date) else date.fromisoformat(str(ra)[:10])
    except ValueError:
        raise LoiKhachSan("Ngày nhận / trả phòng không hợp lệ")
    if vao < hom_nay:
        raise LoiKhachSan("Ngày nhận phòng đã qua")
    if ra <= vao:
        raise LoiKhachSan("Ngày trả phòng phải sau ngày nhận phòng")
    if (ra - vao).days > DEM_TOI_DA:
        raise LoiKhachSan(f"Đặt tối đa {DEM_TOI_DA} đêm một lần")
    return vao, ra


# ══ VTOS · HỒ SƠ KHÁCH SẠN ════════════════════════════════════════════════════════════════════════
TRUONG_KS = ("ten", "tinh_thanh", "khu_vuc", "dia_chi", "sao", "loai", "km_trung_tam", "gan", "noi_bat", "mo_ta",
             "tien_ich", "gio_nhan", "gio_tra", "cs_tre_em", "cs_giuong_phu", "cs_vat_nuoi", "cs_khac", "thue_phi_pt",
             "thue_phi_xac_nhan",                                                                   # KS-17
             "phu_hop",                                                                             # KS-19
             "lien_he_noi_bo", "ghi_chu_noi_bo",
             # KS-16j
             "cs_nhan_tre_em", "cs_tre_tu_tuoi", "cs_moc_tuoi", "cs_phi_giuong_phu", "cs_giuong_phu_an_sang", "cs_noi",
             # KS-16k
             "cs_so_tre_mien_phi", "cs_tre_mp_tinh_suc_chua", "cs_giuong_phu_kieu")
TUOI_TRE_TOI_DA = 17
MO_TA_NGAN = 300
MO_TA_DAI = 3000


def _so_hoac_none(v, ten: str, lo: int, hi: int) -> int | None:
    """KS-16j: ô số có trạng thái «chưa xác nhận» — trống / None là chưa xác nhận, KHÔNG phải 0."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise LoiKhachSan(f"{ten} không hợp lệ")
    if not lo <= n <= hi:
        raise LoiKhachSan(f"{ten} từ {lo} đến {hi}")
    return n


def _tien_hoac_none(v, ten: str, hi: float = 50_000_000) -> float | None:
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LoiKhachSan(f"{ten} không hợp lệ")
    if not 0 <= x <= hi:
        raise LoiKhachSan(f"{ten} không hợp lệ")
    return x


def chuan_moc(m: dict) -> dict:
    """KS-16k: một nhóm tuổi về dạng chuẩn. Đọc được cả dạng KS-16j (phu_thu / nguoi_lon / an_sang True-False)."""
    cach = m.get("cach")
    if cach == "phu_thu":                       # KS-16j
        cach, gia = "co_dinh", m.get("phu_thu") or 0
    else:
        gia = m.get("gia") or 0
    an = m.get("an_sang")
    if isinstance(an, bool):                    # KS-16j: ô tick «gồm ăn sáng»
        an = 0 if an else None
    return {"tu": int(m["tu"]), "den": int(m["den"]), "nhom": m.get("nhom") or ("so_sinh" if int(m["den"]) <= 1 else "tre_em"),
            "cach": cach, "gia": float(gia or 0), "an_sang": None if an is None else float(an)}


def kiem_bang_tre(ds, ten: str = "Nhóm tuổi") -> list[dict]:
    """KS-16k: bảng giá trẻ em theo nhóm tuổi (kiểu Agoda). Trên tuổi lớn nhất của bảng = người lớn."""
    ra = []
    for i, m in enumerate(ds or [], start=1):
        try:
            tu, den = int(m.get("tu")), int(m.get("den"))
        except (TypeError, ValueError, AttributeError):
            raise LoiKhachSan(f"{ten} dòng {i}: tuổi không hợp lệ")
        cach = str(m.get("cach") or "")
        if cach == "nguoi_lon":                 # KS-16j: «tính như người lớn» = ngoài bảng
            continue
        if cach not in CACH_TINH_TRE and cach != "phu_thu":
            raise LoiKhachSan(f"{ten} dòng {i}: chọn cách tính")
        if not 0 <= tu <= den <= TUOI_TRE_TOI_DA:
            raise LoiKhachSan(f"{ten} dòng {i}: tuổi từ 0 đến {TUOI_TRE_TOI_DA}, «từ» không lớn hơn «đến»")
        nhom = str(m.get("nhom") or "tre_em")
        if nhom not in NHOM_TUOI:
            raise LoiKhachSan(f"{ten} dòng {i}: nhóm tuổi không hợp lệ")
        gia = _tien_hoac_none(m.get("gia") if cach != "phu_thu" else m.get("phu_thu"), f"{ten} dòng {i}: giá") or 0
        if cach == "phan_tram" and not 0 < gia <= 100:
            raise LoiKhachSan(f"{ten} dòng {i}: phần trăm giá phòng từ 1 đến 100")
        if cach in ("co_dinh", "phu_thu") and gia <= 0:
            raise LoiKhachSan(f"{ten} dòng {i}: ghi giá trẻ em mỗi đêm (miễn phí thì chọn «Luôn miễn phí»)")
        an = m.get("an_sang")
        an = (0 if an else None) if isinstance(an, bool) else _tien_hoac_none(an, f"{ten} dòng {i}: giá ăn sáng", 5_000_000)
        ra.append({"tu": tu, "den": den, "nhom": nhom, "cach": "co_dinh" if cach == "phu_thu" else cach,
                   "gia": gia if cach != "mien_phi" else 0, "an_sang": an})
    ra.sort(key=lambda x: x["tu"])
    for a, b in zip(ra, ra[1:]):
        if b["tu"] <= a["den"]:
            raise LoiKhachSan(f"Hai nhóm tuổi chồng nhau ({a['tu']}–{a['den']} và {b['tu']}–{b['den']})")
        if b["tu"] != a["den"] + 1:
            raise LoiKhachSan(f"Nhóm tuổi bị hở từ {a['den'] + 1} đến {b['tu'] - 1} tuổi")
    return ra


def _kiem_cs_tre(d: dict) -> dict:
    """KS-16j/16k: chính sách tuổi + giá trẻ em mặc định của khách sạn (theo cách Agoda YCS)."""
    o = {}
    o["cs_nhan_tre_em"] = str(d.get("cs_nhan_tre_em") or "chua_xac_nhan")
    if o["cs_nhan_tre_em"] not in NHAN_TRE_EM:
        raise LoiKhachSan("Chính sách nhận trẻ em không hợp lệ")
    o["cs_tre_tu_tuoi"] = _so_hoac_none(d.get("cs_tre_tu_tuoi"), "Tuổi tối thiểu của khách", 0, 18)
    if o["cs_nhan_tre_em"] == "tu_tuoi" and o["cs_tre_tu_tuoi"] is None:
        raise LoiKhachSan("Ghi tuổi tối thiểu của khách")
    if o["cs_nhan_tre_em"] != "tu_tuoi":
        o["cs_tre_tu_tuoi"] = None
    moc = kiem_bang_tre(d.get("cs_moc_tuoi"))
    if o["cs_nhan_tre_em"] in ("moi_tuoi", "tu_tuoi") and not moc:
        raise LoiKhachSan("Nhận trẻ em thì ghi ít nhất một nhóm tuổi (sơ sinh / trẻ em) và giá")
    if o["cs_nhan_tre_em"] == "tu_tuoi" and moc and moc[0]["tu"] < o["cs_tre_tu_tuoi"]:
        raise LoiKhachSan("Nhóm tuổi bắt đầu dưới tuổi tối thiểu của khách")
    o["cs_moc_tuoi"] = moc if o["cs_nhan_tre_em"] in ("moi_tuoi", "tu_tuoi") else []
    o["cs_giuong_phu_kieu"] = str(d.get("cs_giuong_phu_kieu") or "co_dinh")
    if o["cs_giuong_phu_kieu"] not in KIEU_GIA:
        raise LoiKhachSan("Kiểu giá giường phụ không hợp lệ")
    o["cs_phi_giuong_phu"] = _tien_hoac_none(d.get("cs_phi_giuong_phu"), "Giá giường phụ")
    if o["cs_giuong_phu_kieu"] == "phan_tram" and o["cs_phi_giuong_phu"] is not None and not 0 < o["cs_phi_giuong_phu"] <= 100:
        raise LoiKhachSan("Giá giường phụ theo % giá phòng: từ 1 đến 100")
    o["cs_so_tre_mien_phi"] = _so_hoac_none(d.get("cs_so_tre_mien_phi"), "Số trẻ miễn phí mỗi phòng", 0, 6)
    o["cs_tre_mp_tinh_suc_chua"] = bool(d.get("cs_tre_mp_tinh_suc_chua"))
    o["cs_giuong_phu_an_sang"] = bool(d.get("cs_giuong_phu_an_sang"))
    o["cs_noi"] = str(d.get("cs_noi") or "").strip()[:120]
    return o


def _kiem_ks(d: dict) -> dict:
    o = {}
    o["ten"] = str(d.get("ten") or "").strip()[:160]
    if len(o["ten"]) < 3:
        raise LoiKhachSan("Ghi tên khách sạn")
    o["tinh_thanh"] = str(d.get("tinh_thanh") or "").strip()
    if o["tinh_thanh"] not in THANH_PHO:
        raise LoiKhachSan("Chọn thành phố trong danh sách")
    try:
        o["sao"] = int(d.get("sao") or 0)
    except (TypeError, ValueError):
        raise LoiKhachSan("Hạng sao không hợp lệ")
    if not 0 <= o["sao"] <= 5:
        raise LoiKhachSan("Hạng sao từ 1 đến 5 (0 = chưa xếp hạng)")
    o["loai"] = str(d.get("loai") or "khach_san")
    if o["loai"] not in LOAI_CHO_O:
        raise LoiKhachSan("Loại chỗ ở không hợp lệ")
    km = d.get("km_trung_tam")
    o["km_trung_tam"] = None if km in (None, "") else round(float(km), 1)
    if o["km_trung_tam"] is not None and not 0 <= o["km_trung_tam"] <= 200:
        raise LoiKhachSan("Khoảng cách tới trung tâm 0–200 km")
    ti = d.get("tien_ich") or []
    if any(x not in TIEN_ICH for x in ti):
        raise LoiKhachSan("Tiện ích không hợp lệ")
    o["tien_ich"] = list(dict.fromkeys(ti))
    for k in ("gio_nhan", "gio_tra"):
        v = str(d.get(k) or "").strip() or ("14:00" if k == "gio_nhan" else "12:00")
        if len(v) != 5 or v[2] != ":" or not (v[:2] + v[3:]).isdigit() or int(v[:2]) > 23 or int(v[3:]) > 59:
            raise LoiKhachSan("Giờ nhận / trả phòng dạng HH:MM")
        o[k] = v
    # KS-19 (Chủ tịch 05/11/2026: «giá đã gồm 8% VAT»): máy KHÔNG cộng thuế phí vào giá nữa — ô % cũ luôn lưu 0.
    # thue_phi_xac_nhan nay là «Đã xác nhận với khách sạn: giá nhập đã gồm 8% VAT» — vẫn là điều kiện duyệt giá / mở bán.
    o["thue_phi_pt"] = 0.0
    o["thue_phi_xac_nhan"] = bool(d.get("thue_phi_xac_nhan"))
    ph = d.get("phu_hop") or []
    if any(x not in PHU_HOP for x in ph):
        raise LoiKhachSan("«Phù hợp cho» không hợp lệ")
    o["phu_hop"] = list(dict.fromkeys(ph))
    for k, n in (("khu_vuc", 120), ("dia_chi", 300), ("gan", 300), ("noi_bat", 300), ("cs_tre_em", 300),
                 ("cs_giuong_phu", 300), ("cs_vat_nuoi", 300), ("lien_he_noi_bo", 300)):
        o[k] = str(d.get(k) or "").strip()[:n]
    for k in ("mo_ta", "cs_khac", "ghi_chu_noi_bo"):
        o[k] = str(d.get(k) or "").strip()[:6000]
    o.update(_kiem_cs_tre(d))
    return o


def luu_ks(db: Session, u: User, d: dict, kid: int | None = None, now: datetime | None = None) -> KhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập và sửa khách sạn")
    o = _kiem_ks(d)
    now = now or datetime.now()
    link = str(d.get("link_ggmap") or "").strip()
    toa_tay = doc_link_ggmap(link) if link else None          # KS-16s: Điều hành dán link Google Maps để sửa ghim
    if kid is None:
        k = KhachSanVtd(ma=_ma_moi(db), tao_boi=u.username, tao_luc=now, **o)
        db.add(k)
        db.flush()
        _audit(db, u, "ks_vtd_tao", k.ma, None, {"ten": k.ten})
    else:
        k = _ks(db, kid)
        truoc = {x: getattr(k, x) for x in TRUONG_KS}
        for x, v in o.items():
            setattr(k, x, v)
        _audit(db, u, "ks_vtd_sua", k.ma, truoc, o)
    if toa_tay:
        k.vi_do, k.kinh_do, k.toa_do_nguon = toa_tay[0], toa_tay[1], "tay"
        _audit(db, u, "ks_vtd_toa_do_tay", k.ma, None, {"vi_do": toa_tay[0], "kinh_do": toa_tay[1]})
    elif k.toa_do_nguon != "tay" and (kid is None or truoc.get("dia_chi") != k.dia_chi or truoc.get("tinh_thanh") != k.tinh_thanh
                                      or k.vi_do is None):
        _tu_lay_toa_do(k)
    k.sua_boi, k.sua_luc = u.username, now
    db.commit()
    db.refresh(k)
    return k


# KS-16l (Chủ tịch 01/11/2026): khách sạn lên cổng khi đủ hồ sơ + ảnh + giới thiệu, KHÔNG cần loại phòng đang bán.
# Chưa có gói đặt được thì chưa book trên cổng — bấm vào khách sạn mở trang ngoài LINK_KS_NGOAI ở tab mới.
# KS-16n (Chủ tịch 01/11/2026): www.vietourist.vn/hotel chưa có (404) → TẠM trỏ trang chủ; web chính có trang thì đổi lại.
LINK_KS_NGOAI = "/hotel"
VAT_PT = 8   # KS-19: giá phòng VTD đã gồm 8% VAT


def vat_trong(tong: float) -> int:
    """Phần VAT nằm TRONG tổng tiền (để xuất hóa đơn) — không cộng thêm."""
    return int(round(float(tong or 0) * VAT_PT / (100 + VAT_PT)))


# KS-19: «Phù hợp cho» (Điều hành chọn ở hồ sơ khách sạn) — bộ lọc trên cổng.
PHU_HOP = {"gia_dinh": "Gia đình có trẻ nhỏ", "cap_doi": "Cặp đôi", "cong_tac": "Công tác", "nhom_ban": "Nhóm bạn"}
# KS-19: tâm thành phố (vĩ độ, kinh độ) — máy tính «cách trung tâm» từ tọa độ khách sạn khi Điều hành chưa ghi km.
TAM_TP = {"Hà Nội": (21.0285, 105.8542), "Hạ Long": (20.9529, 107.0800), "Hải Phòng": (20.8449, 106.6881),
          "Ninh Bình": (20.2506, 105.9745), "Sa Pa": (22.3364, 103.8438), "Hà Giang": (22.8233, 104.9836),
          "Mộc Châu": (20.8431, 104.6340), "Cao Bằng": (22.6657, 106.2570), "Thanh Hóa": (19.8067, 105.7852),
          "Vinh": (18.6796, 105.6813), "Đồng Hới": (17.4688, 106.6223), "Huế": (16.4637, 107.5909),
          "Đà Nẵng": (16.0678, 108.2208), "Hội An": (15.8801, 108.3380), "Quy Nhơn": (13.7820, 109.2192),
          "Tuy Hòa": (13.0955, 109.3209), "Nha Trang": (12.2388, 109.1967), "Phan Rang": (11.5643, 108.9886),
          "Pleiku": (13.9833, 108.0000), "Buôn Ma Thuột": (12.6667, 108.0500), "Kon Tum": (14.3545, 108.0076),
          "Đà Lạt": (11.9404, 108.4583), "TP. Hồ Chí Minh": (10.7769, 106.7009), "Vũng Tàu": (10.3460, 107.0843),
          "Phan Thiết – Mũi Né": (10.9289, 108.1021), "Cần Thơ": (10.0452, 105.7469), "Châu Đốc": (10.7009, 105.1169),
          "Phú Quốc": (10.2270, 103.9637), "Bến Tre": (10.2415, 106.3759), "Trà Vinh": (9.9347, 106.3455),
          "Cà Mau": (9.1769, 105.1524), "Côn Đảo": (8.6829, 106.6080)}


def km_trung_tam(k: KhachSanVtd) -> float | None:
    """Điều hành ghi km thì dùng số đó; chưa ghi mà có tọa độ thì máy tính đường chim bay tới tâm thành phố."""
    if k.km_trung_tam is not None:
        return k.km_trung_tam
    tam = TAM_TP.get(k.tinh_thanh or "")
    if k.vi_do is None or k.kinh_do is None or not tam:
        return None
    import math
    la1, lo1, la2, lo2 = map(math.radians, (k.vi_do, k.kinh_do, tam[0], tam[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(h)), 1)   # KS-16q: trang riêng kh.vietourist.vn/hotel (cùng tên miền cổng)


# ══ KS-16s (Chủ tịch duyệt bản xem thử 01/11/2026): tọa độ cho «Xem trên bản đồ» ══════════════════════════
# Máy tự lấy từ địa chỉ qua dịch vụ tra địa chỉ miễn phí của OpenStreetMap (Nominatim: ≤1 lượt/giây, có User-Agent).
# Điều hành dán link Google Maps để sửa ghim lệch → nguồn «tay», máy không ghi đè.
NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA = "VTOS/1.0 (vietourist.com.vn)"
LOAT_TOI_DA = 60
LOAT_NGHI_GIAY = 1.1


PHOTON = "https://photon.komoot.io/api/"   # KS-19d: dịch vụ tra địa chỉ dự phòng (cũng dữ liệu OpenStreetMap)
LOI_TOA_DO: list[str] = []                 # KS-19d: lỗi gọi dịch vụ ngoài của lượt gần nhất — ghi vào nhật ký việc tự động


def _get_json(url: str):
    import json
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": NOMINATIM_UA, "Accept-Language": "vi"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _nominatim(q: str) -> list[tuple[float, float, str]]:
    """Nhiều ứng viên (lat, lon, loại) — người gọi tự chọn cái nằm gần tâm thành phố. Nominatim lỗi thì thử Photon."""
    import urllib.parse
    ra: list[tuple[float, float, str]] = []
    try:
        ds = _get_json(NOMINATIM + "?" + urllib.parse.urlencode({"format": "json", "limit": 3, "countrycodes": "vn", "q": q}))
        ra = [(round(float(x["lat"]), 6), round(float(x["lon"]), 6), str(x.get("type") or "")) for x in ds]
    except Exception as ex:   # noqa: BLE001
        LOI_TOA_DO.append(f"Nominatim: {type(ex).__name__} {str(ex)[:80]}")
    if ra:
        return ra
    try:
        ds = _get_json(PHOTON + "?" + urllib.parse.urlencode({"q": q, "limit": 3}))
        for f in ds.get("features") or []:
            pr, co = f.get("properties") or {}, (f.get("geometry") or {}).get("coordinates") or []
            if len(co) == 2 and (pr.get("countrycode") or "").upper() in ("VN", ""):
                ra.append((round(float(co[1]), 6), round(float(co[0]), 6), str(pr.get("osm_value") or pr.get("type") or "")))
    except Exception as ex:   # noqa: BLE001
        LOI_TOA_DO.append(f"Photon: {type(ex).__name__} {str(ex)[:80]}")
    return ra


LAY_TOA_DO = _nominatim   # phép thử thay bằng hàm giả — trả list (lat, lon, loại) hoặc (lat, lon) / None như bản cũ


def _trong_vn(lat: float, lng: float) -> bool:
    return 8.0 <= lat <= 23.6 and 102.0 <= lng <= 110.0


def doc_link_ggmap(link: str) -> tuple[float, float]:
    """Tách tọa độ từ link Google Maps đầy đủ: …/@16.06,108.24,17z · ?q=16.06,108.24 · !3d16.06!4d108.24."""
    import re
    import urllib.parse
    t = urllib.parse.unquote(link.strip())
    if re.search(r"(maps\.app\.goo\.gl|goo\.gl/maps)", t):
        raise LoiKhachSan("Link rút gọn (maps.app.goo.gl) máy không đọc được — mở link trên máy tính, chép link đầy đủ trên thanh địa chỉ")
    so = r"(-?\d{1,3}\.\d+)"
    for mau in (r"!3d" + so + r"!4d" + so, r"[?&](?:q|query|ll|destination)=" + so + r",\s*" + so, r"@" + so + r"," + so):
        m = re.search(mau, t)
        if m:
            lat, lng = round(float(m.group(1)), 6), round(float(m.group(2)), 6)
            if not _trong_vn(lat, lng):
                raise LoiKhachSan("Tọa độ trong link nằm ngoài Việt Nam — kiểm lại link")
            return lat, lng
    raise LoiKhachSan("Không thấy tọa độ trong link — mở khách sạn trên Google Maps, chép link đầy đủ (có @vĩ độ,kinh độ)")


def _cau_tim(k: KhachSanVtd) -> list[str]:
    """KS-19d: địa chỉ ghi theo đơn vị hành chính mới (vd «Bến Tre, Vĩnh Long») bản đồ thường chưa có — thử thêm: phố đầu
    + thành phố, phố bỏ số nhà + thành phố, khu vực + thành phố, tên khách sạn + thành phố."""
    import re
    tp = (k.tinh_thanh or "").replace("Phan Thiết – Mũi Né", "Phan Thiết").replace("TP. Hồ Chí Minh", "Hồ Chí Minh")
    ds = []
    phan = [x.strip() for x in (k.dia_chi or "").split(",") if x.strip()]
    if k.dia_chi:
        ds.append(", ".join(x for x in (k.dia_chi, "" if tp in k.dia_chi else tp, "" if "Việt Nam" in k.dia_chi else "Việt Nam") if x))
    if phan:
        ds.append(", ".join(phan[:2] + [tp]))
        ds.append(f"{phan[0]}, {tp}")
        ds.append(re.sub(r"^(số\s*)?[\d–\-/ ]+\s*", "", phan[0], flags=re.I) + f", {tp}")
    kv = re.sub(r"^(Đường|Khu vực)\s*", "", (k.khu_vuc or "").split("·")[0].strip(), flags=re.I)
    if kv:
        ds.append(f"{kv}, {tp}")
    ds.append(", ".join(x for x in (k.ten, tp) if x))
    return [x for x in dict.fromkeys(ds) if len(x) > 4]


def _hop_le_toa_do(k: KhachSanVtd, lat: float, lng: float, loai: str = "") -> bool:
    """Trong Việt Nam, không phải tâm thành phố / tỉnh (loại city, state…), và cách tâm thành phố của khách sạn < 40 km."""
    if not _trong_vn(lat, lng) or loai in ("city", "state", "province", "country", "county", "administrative"):
        return False
    tam = TAM_TP.get(k.tinh_thanh or "")
    if not tam:
        return True
    import math
    la1, lo1, la2, lo2 = map(math.radians, (lat, lng, tam[0], tam[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h)) < 40


def _tu_lay_toa_do(k: KhachSanVtd, nghi: float = 0) -> bool:
    """Thử lần lượt địa chỉ rồi tên + khu vực. Lỗi mạng không làm hỏng việc lưu hồ sơ."""
    import time
    for i, q in enumerate(_cau_tim(k)):
        if i and nghi:
            time.sleep(nghi)
        try:
            kq = LAY_TOA_DO(q)
        except Exception as ex:   # noqa: BLE001 — mạng / dịch vụ ngoài lỗi: để trống, lần sau lấy lại
            LOI_TOA_DO.append(f"{type(ex).__name__} {str(ex)[:80]}")
            return False
        ung = [kq] if isinstance(kq, tuple) else list(kq or [])
        for x in ung:
            lat, lng, loai = (x[0], x[1], x[2] if len(x) > 2 else "")
            if _hop_le_toa_do(k, lat, lng, loai):
                k.vi_do, k.kinh_do, k.toa_do_nguon = lat, lng, "tu_dong"
                return True
    k.toa_do_nguon = "khong_thay"
    return False


def may_lay_toa_do(db: Session, toi_da: int = 20, nghi: float = LOAT_NGHI_GIAY, now: datetime | None = None) -> tuple[int, str]:
    """KS-19c (Chủ tịch 05/11/2026: «máy tự bấm nút lấy tọa độ»): việc theo lịch, không cần ai bấm. Mỗi giờ lấy
    tọa độ cho khách sạn chưa có (bỏ qua ghim tay); khách sạn máy đã thử mà không thấy địa chỉ thì chỉ thử lại
    lúc 2 giờ sáng — không gọi dịch vụ ngoài mỗi giờ cho cùng một địa chỉ hỏng."""
    import time
    now = now or datetime.now()
    q = select(KhachSanVtd).where(KhachSanVtd.vi_do.is_(None), KhachSanVtd.toa_do_nguon != "tay", KhachSanVtd.ngung.is_(False))
    if now.hour != 2:
        q = q.where(KhachSanVtd.toa_do_nguon != "khong_thay")
    ds = db.execute(q.order_by(KhachSanVtd.ma)).scalars().all()
    co, khong = [], []
    LOI_TOA_DO.clear()
    for i, k in enumerate(ds[:toi_da]):
        if i and nghi:
            time.sleep(nghi)
        (co if _tu_lay_toa_do(k, nghi) else khong).append(k.ma)
    if co or khong:
        db.commit()
    return len(co), (f"Lấy được tọa độ {len(co)} khách sạn" + (f", chưa thấy {len(khong)}: {', '.join(khong[:10])}" if khong else "")
                     + (f"; còn {len(ds) - toi_da} chờ lượt sau" if len(ds) > toi_da else "")
                     + (f" · LỖI GỌI DỊCH VỤ BẢN ĐỒ: {'; '.join(dict.fromkeys(LOI_TOA_DO))[:300]}" if LOI_TOA_DO else "")) if ds \
        else "Không còn khách sạn nào chờ lấy tọa độ (thiếu mà máy đã thử không thấy thì thử lại lúc 2 giờ sáng)"


def lay_toa_do_loat(db: Session, u: User, toi_da: int = LOAT_TOI_DA, nghi: float = LOAT_NGHI_GIAY) -> dict:
    """Nút «Lấy tọa độ cho tất cả khách sạn»: khách sạn chưa có tọa độ (bỏ qua ghim tay), tối đa `toi_da` mỗi lần."""
    import time
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành / Chủ tịch / TGĐ chạy lấy tọa độ hàng loạt")
    ds = db.execute(select(KhachSanVtd).where(KhachSanVtd.vi_do.is_(None), KhachSanVtd.toa_do_nguon != "tay",
                                              KhachSanVtd.ngung.is_(False)).order_by(KhachSanVtd.ma)).scalars().all()
    co, khong = [], []
    for i, k in enumerate(ds[:toi_da]):
        if i and nghi:
            time.sleep(nghi)
        (co if _tu_lay_toa_do(k, nghi) else khong).append(k.ma)
    _audit(db, u, "ks_vtd_toa_do_loat", "loat", None, {"co": co, "khong_thay": khong})
    db.commit()
    return {"co": len(co), "khong_thay": khong, "con_lai": max(0, len(ds) - toi_da)}


# ══ KS-16s: công tắc mở thanh toán trực tuyến — chung + từng khách sạn; chỉ trả được khi CẢ HAI bật ══════
KHOA_TT = "mo_thanh_toan"


def tt_chung(db: Session) -> bool:
    r = db.get(CaiDatKsVtd, KHOA_TT)
    return bool(r and r.gia_tri == "1")


def mo_thanh_toan(db: Session, k: KhachSanVtd, chung: bool | None = None) -> bool:
    return bool(k.mo_thanh_toan) and (tt_chung(db) if chung is None else chung)


def bat_tt_chung(db: Session, u: User, bat: bool, now: datetime | None = None) -> bool:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành / Chủ tịch / TGĐ mở / đóng thanh toán trực tuyến")
    r = db.get(CaiDatKsVtd, KHOA_TT)
    if r is None:
        r = CaiDatKsVtd(khoa=KHOA_TT)
        db.add(r)
    r.gia_tri, r.sua_boi, r.sua_luc = ("1" if bat else "0"), u.username, now or datetime.now()
    _audit(db, u, "ks_vtd_tt_chung_mo" if bat else "ks_vtd_tt_chung_dong", "chung")
    db.commit()
    return bool(bat)


def bat_tt_ks(db: Session, u: User, kid: int, bat: bool) -> KhachSanVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành / Chủ tịch / TGĐ mở / đóng thanh toán của khách sạn")
    k = _ks(db, kid)
    if bat and not k.thue_phi_xac_nhan:
        raise LoiKhachSan("Chưa xác nhận thuế phí với khách sạn (giá đã gồm 8% VAT) — chưa mở thanh toán được")   # KS-17 → KS-19
    k.mo_thanh_toan = bool(bat)
    _audit(db, u, "ks_vtd_tt_mo" if bat else "ks_vtd_tt_dong", k.ma)
    db.commit()
    return k


def dieu_kien_hien(db: Session, k: KhachSanVtd) -> list[dict]:
    return [{"ma": "ho_so", "ten": "Đủ tên, thành phố, hạng sao", "ok": bool(k.ten and k.tinh_thanh in THANH_PHO and k.sao)},
            {"ma": "anh", "ten": "Có ảnh đã duyệt", "ok": bool(_anh_duyet(db, [k.id]).get(k.id))},
            {"ma": "mo_ta", "ten": "Có giới thiệu cho khách", "ok": len(k.mo_ta or "") >= 40}]


def bat_hien(db: Session, u: User, kid: int, bat: bool, now: datetime | None = None) -> KhachSanVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành bật / tắt hiện khách sạn trên cổng")
    k = _ks(db, kid)
    now = now or datetime.now()
    if bat:
        if k.ngung:
            raise LoiKhachSan("Khách sạn đã ngừng hợp tác")
        thieu = [c["ten"] for c in dieu_kien_hien(db, k) if not c["ok"]]
        if thieu:
            raise LoiKhachSan("Chưa bật được — còn thiếu: " + "; ".join(thieu))
        if k.sua_boi == u.username and not _co(u, TOAN_QUYEN):
            raise LoiKhachSan("Người vừa sửa hồ sơ không tự bật — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    k.hien_cong, k.hien_boi, k.hien_luc = bool(bat), u.username, now
    k.tat_ly_do = "" if bat else f"Tắt bởi {u.username}"
    _audit(db, u, "ks_vtd_bat" if bat else "ks_vtd_tat", k.ma)
    db.commit()
    return k


def bat_hien_loat(db: Session, u: User, now: datetime | None = None) -> dict:
    """KS-16l: bật hiện mọi khách sạn đủ điều kiện, chưa hiện, không ngừng hợp tác. Người vừa sửa hồ sơ không tự bật
    (trừ Chủ tịch / TGĐ) — khách sạn ấy được bỏ qua và kể tên."""
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành / Chủ tịch / TGĐ bật hiện trên cổng")
    now = now or datetime.now()
    bat, bo = [], []
    for k in db.execute(select(KhachSanVtd).where(KhachSanVtd.hien_cong.is_(False), KhachSanVtd.ngung.is_(False))
                        .order_by(KhachSanVtd.ma)).scalars():
        if not all(c["ok"] for c in dieu_kien_hien(db, k)):
            continue
        if k.sua_boi == u.username and not _co(u, TOAN_QUYEN):
            bo.append(k.ma)
            continue
        k.hien_cong, k.hien_boi, k.hien_luc, k.tat_ly_do = True, u.username, now, ""
        bat.append(k.ma)
    # entity của nhật ký chỉ 60 ký tự — danh sách mã để ở «after» (Postgres báo lỗi 500 khi dồn 32 mã vào entity)
    _audit(db, u, "ks_vtd_bat_loat", "loat", None, {"bat": bat, "bo_qua": bo})
    db.commit()
    return {"bat": bat, "bo_qua": bo}


def ngung(db: Session, u: User, kid: int, ngung_: bool) -> KhachSanVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành đổi trạng thái hợp tác")
    k = _ks(db, kid)
    k.ngung = bool(ngung_)
    if ngung_:
        k.hien_cong, k.tat_ly_do = False, "Ngừng hợp tác"
    _audit(db, u, "ks_vtd_ngung" if ngung_ else "ks_vtd_hop_tac_lai", k.ma)
    db.commit()
    return k


# ══ VTOS · LOẠI PHÒNG, GÓI GIÁ, MÙA GIÁ ═══════════════════════════════════════════════════════════
def _lp_cua(db: Session, kid: int) -> list[LoaiPhongVtd]:
    return db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id == kid)
                      .order_by(LoaiPhongVtd.thu_tu, LoaiPhongVtd.id)).scalars().all()


def luu_loai_phong(db: Session, u: User, kid: int, d: dict, lid: int | None = None, now: datetime | None = None) -> LoaiPhongVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập loại phòng")
    k = _ks(db, kid)
    ten = str(d.get("ten") or "").strip()[:120]
    if len(ten) < 2:
        raise LoiKhachSan("Ghi tên loại phòng")
    mo_ta, mo_ta_dai = str(d.get("mo_ta") or "").strip(), str(d.get("mo_ta_dai") or "").strip()
    # KS-16j: không tự cắt — báo lỗi để người nhập rút gọn (Điều hành báo 31/10/2026: máy cắt thầm ở 300 ký tự)
    if len(mo_ta) > MO_TA_NGAN:
        raise LoiKhachSan(f"Đặc điểm ngắn {len(mo_ta)}/{MO_TA_NGAN} ký tự — rút gọn, phần dài đưa xuống Mô tả chi tiết")
    if len(mo_ta_dai) > MO_TA_DAI:
        raise LoiKhachSan(f"Mô tả chi tiết {len(mo_ta_dai)}/{MO_TA_DAI} ký tự — rút gọn")
    try:
        sp = d.get("so_phong", 1)          # KS-16j: 0 là 0 (không còn đổi thành 1); trống = 0
        o = {"ten": ten, "dien_tich": int(d.get("dien_tich") or 0), "giuong": str(d.get("giuong") or "").strip()[:120],
             "mo_ta": mo_ta, "mo_ta_dai": mo_ta_dai,
             "so_phong": 0 if sp in (None, "") else int(sp),
             "thu_tu": int(d.get("thu_tu") or 0), "dang_ban": bool(d.get("dang_ban", True))}
    except (TypeError, ValueError):
        raise LoiKhachSan("Số liệu loại phòng không hợp lệ")
    # KS-17: trống = CHƯA XÁC NHẬN (bản cũ tự gán 2, giao diện tự gán 1). Phòng chưa xác nhận người lớn không bán được.
    o["toi_da_nguoi_lon"] = _so_hoac_none(d.get("toi_da_nguoi_lon"), "Tối đa người lớn", 1, 20)
    o["tong_khach_toi_da"] = _so_hoac_none(d.get("tong_khach_toi_da"), "Tổng khách tối đa", 1, 30)
    o["toi_da_tre_em"] = _so_hoac_none(d.get("toi_da_tre_em"), "Tối đa trẻ em", 0, 10)
    o["giuong_phu_toi_da"] = _so_hoac_none(d.get("giuong_phu_toi_da"), "Giường phụ tối đa", 0, 5)
    # KS-16k: sức chứa kiểu Agoda + ghi đè của riêng phòng (trống = theo khách sạn)
    o["suc_chua"] = _so_hoac_none(d.get("suc_chua"), "Sức chứa cơ bản", 1, 30)
    o["khach_them_toi_da"] = _so_hoac_none(d.get("khach_them_toi_da"), "Khách thêm tối đa", 0, 10)
    o["so_tre_mien_phi"] = _so_hoac_none(d.get("so_tre_mien_phi"), "Số trẻ miễn phí của phòng", 0, 6)
    o["giuong_phu_kieu"] = str(d.get("giuong_phu_kieu") or "")
    if o["giuong_phu_kieu"] and o["giuong_phu_kieu"] not in KIEU_GIA:
        raise LoiKhachSan("Kiểu giá giường phụ không hợp lệ")
    o["phi_giuong_phu"] = _tien_hoac_none(d.get("phi_giuong_phu"), "Giá giường phụ của phòng")
    if o["phi_giuong_phu"] is not None and not o["giuong_phu_kieu"]:
        o["giuong_phu_kieu"] = "co_dinh"
    if o["giuong_phu_kieu"] == "phan_tram" and o["phi_giuong_phu"] is not None and not 0 < o["phi_giuong_phu"] <= 100:
        raise LoiKhachSan("Giá giường phụ theo % giá phòng: từ 1 đến 100")
    o["giuong_phu_xac_nhan"] = bool(d.get("giuong_phu_xac_nhan"))
    o["gia_tre_rieng"] = kiem_bang_tre(d.get("gia_tre_rieng"), "Giá trẻ em của phòng") if d.get("gia_tre_rieng") else None
    nc = d.get("noi_cui")
    o["noi_cui"] = None if nc in (None, "") else bool(nc)
    tn = []
    for x in d.get("tien_nghi") or []:
        x = " ".join(str(x).split())[:40]
        if x and x not in tn:
            tn.append(x)
    if len(tn) > 30:
        raise LoiKhachSan("Tối đa 30 tiện nghi mỗi loại phòng")
    o["tien_nghi"] = tn
    o["nguon"] = str(d.get("nguon") or "")
    if o["nguon"] and o["nguon"] not in NGUON_LP:
        raise LoiKhachSan("Nguồn không hợp lệ")
    o["trang_thai_dc"] = str(d.get("trang_thai_dc") or "")
    if o["trang_thai_dc"] and o["trang_thai_dc"] not in TRANG_THAI_DC:
        raise LoiKhachSan("Trạng thái đối chiếu không hợp lệ")
    cx = list(dict.fromkeys(d.get("can_xac_nhan") or []))
    if any(x not in CAN_XAC_NHAN for x in cx):
        raise LoiKhachSan("Mục cần xác nhận không hợp lệ")
    o["can_xac_nhan"] = cx
    for x, n in (("ky_doi_chieu", 120), ("ma_hang", 80), ("ten_tuong_duong", 160), ("ghi_chu_doi_chieu", 500)):
        v = str(d.get(x) or "").strip()
        if len(v) > n:
            raise LoiKhachSan(f"Ô {x.replace('_', ' ')} quá {n} ký tự")
        o[x] = v
    if (o["tong_khach_toi_da"] is not None and o["toi_da_nguoi_lon"] is not None
            and o["tong_khach_toi_da"] < o["toi_da_nguoi_lon"]):
        raise LoiKhachSan("Tổng khách tối đa không nhỏ hơn số người lớn tối đa")
    if not 0 <= o["so_phong"] <= 500 or not 0 <= o["dien_tich"] <= 2000:
        raise LoiKhachSan("Số phòng 0–500, diện tích 0–2000 m²")
    if o["dang_ban"] and o["so_phong"] < 1:
        raise LoiKhachSan("Đang bán cần số phòng VTD được bán mỗi đêm ≥ 1 theo hợp đồng — chưa có thì bỏ chọn «Đang bán»")
    if lid is None:
        lp = LoaiPhongVtd(khach_san_id=k.id, **o)
        db.add(lp)
    else:
        lp = db.get(LoaiPhongVtd, lid)
        if lp is None or lp.khach_san_id != k.id:
            raise LoiKhachSan("Không có loại phòng này", 404)
        for x, v in o.items():
            setattr(lp, x, v)
    lp.sua_boi, lp.sua_luc = u.username, now or datetime.now()
    db.flush()
    _audit(db, u, "ks_vtd_loai_phong", k.ma, None, {"id": lp.id, **o})
    db.commit()
    db.refresh(lp)
    return lp


def _mua_cua(db: Session, gids: list[int]) -> dict[int, list[MuaGiaVtd]]:
    ra: dict[int, list] = {}
    if gids:
        for m in db.execute(select(MuaGiaVtd).where(MuaGiaVtd.goi_id.in_(gids)).order_by(MuaGiaVtd.tu_ngay)).scalars():
            ra.setdefault(m.goi_id, []).append(m)
    return ra


def _kiem_mua(ds: list) -> list[dict]:
    ra = []
    for i, m in enumerate(ds or [], start=1):
        try:
            tu, den = date.fromisoformat(str(m.get("tu_ngay"))[:10]), date.fromisoformat(str(m.get("den_ngay"))[:10])
            gt = float(m.get("gia_thuong") or 0)
            gc = float(m["gia_cuoi_tuan"]) if m.get("gia_cuoi_tuan") not in (None, "", 0) else None
            gn = float(m["gia_niem_yet"]) if m.get("gia_niem_yet") not in (None, "", 0) else None
        except (TypeError, ValueError):
            raise LoiKhachSan(f"Mùa giá dòng {i}: ngày hoặc giá không hợp lệ")
        if den < tu:
            raise LoiKhachSan(f"Mùa giá dòng {i}: «đến ngày» trước «từ ngày»")
        if gt < 10000 or (gc is not None and gc < 10000):
            raise LoiKhachSan(f"Mùa giá dòng {i}: giá bán mỗi đêm từ 10.000 đ")
        if max(gt, gc or 0) > 500_000_000:
            raise LoiKhachSan(f"Mùa giá dòng {i}: giá quá lớn — kiểm tra lại số 0")
        ra.append({"tu_ngay": tu, "den_ngay": den, "gia_thuong": gt, "gia_cuoi_tuan": gc, "gia_niem_yet": gn,
                   "ghi_chu": str(m.get("ghi_chu") or "").strip()[:200]})
    ra.sort(key=lambda x: x["tu_ngay"])
    for a, b in zip(ra, ra[1:]):
        if b["tu_ngay"] <= a["den_ngay"]:
            raise LoiKhachSan(f"Hai mùa giá chồng ngày nhau ({a['tu_ngay']:%d/%m} – {a['den_ngay']:%d/%m} và từ {b['tu_ngay']:%d/%m})")
    return ra


def luu_goi(db: Session, u: User, lid: int, d: dict, gid: int | None = None, now: datetime | None = None) -> GoiGiaVtd:
    """Lưu gói + toàn bộ mùa giá (thay hết). Gói về «Nháp» — phải gửi duyệt lại; gói đang duyệt thôi hiện."""
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập gói giá")
    lp = db.get(LoaiPhongVtd, lid)
    if lp is None:
        raise LoiKhachSan("Không có loại phòng này", 404)
    ten = str(d.get("ten") or "").strip()[:80]
    if len(ten) < 2:
        raise LoiKhachSan("Ghi tên gói (vd: Chỉ phòng, Có bữa sáng)")
    h = d.get("huy_truoc_ngay")
    h = None if h in (None, "", "khong") else int(h)
    if h is not None and not 0 <= h <= 60:
        raise LoiKhachSan("Miễn phí hủy trước 0–60 ngày, hoặc «không hoàn tiền»")
    gc = str(d.get("huy_gio_chot") or "").strip()                    # KS-17
    if gc and (len(gc) != 5 or gc[2] != ":" or not (gc[:2] + gc[3:]).isdigit() or int(gc[:2]) > 23 or int(gc[3:]) > 59):
        raise LoiKhachSan("Giờ chốt hủy dạng HH:MM, hoặc để trống = hết ngày")
    mg = str(d.get("huy_mui_gio") or "Asia/Ho_Chi_Minh").strip()
    if mg not in MUI_GIO_HUY:
        raise LoiKhachSan("Múi giờ hủy không hợp lệ")
    mua = _kiem_mua(d.get("mua") or [])
    if not mua:
        raise LoiKhachSan("Nhập ít nhất một mùa giá")
    che_do = str(d.get("tre_em_che_do") or "")      # KS-16k
    if che_do not in CHE_DO_TRE_GOI:
        raise LoiKhachSan("Chế độ giá trẻ em của gói không hợp lệ")
    gia_tre = kiem_bang_tre(d.get("gia_tre"), "Giá trẻ em của gói") if che_do == "rieng" else None
    if che_do == "rieng" and not gia_tre:
        raise LoiKhachSan("Giá trẻ em riêng cho gói: ghi ít nhất một nhóm tuổi")
    now = now or datetime.now()
    if gid is None:
        g = GoiGiaVtd(loai_phong_id=lid)
        db.add(g)
    else:
        g = db.get(GoiGiaVtd, gid)
        if g is None or g.loai_phong_id != lid:
            raise LoiKhachSan("Không có gói này", 404)
        for m in db.execute(select(MuaGiaVtd).where(MuaGiaVtd.goi_id == g.id)).scalars():
            db.delete(m)
    truoc = g.trang_thai if gid else None
    g.ten, g.bua_sang, g.huy_truoc_ngay, g.dang_ban = ten, bool(d.get("bua_sang")), h, bool(d.get("dang_ban", True))
    g.tre_em_che_do, g.gia_tre = che_do, gia_tre
    g.huy_gio_chot, g.huy_mui_gio, g.cho_tra_sau = gc, mg, bool(d.get("cho_tra_sau", True))   # KS-17
    g.trang_thai, g.ly_do_tra_lai, g.duyet_boi, g.duyet_luc = "nhap", "", "", None
    g.sua_boi, g.sua_luc = u.username, now
    db.flush()
    for m in mua:
        db.add(MuaGiaVtd(goi_id=g.id, **m))
    k = db.get(KhachSanVtd, lp.khach_san_id)
    _audit(db, u, "ks_vtd_goi_luu", k.ma, {"trang_thai": truoc}, {"goi": g.id, "ten": ten, "so_mua": len(mua)})
    db.commit()
    db.refresh(g)
    return g


def gui_duyet_goi(db: Session, u: User, gid: int) -> GoiGiaVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành gửi duyệt giá")
    g = db.get(GoiGiaVtd, gid)
    if g is None:
        raise LoiKhachSan("Không có gói này", 404)
    if g.trang_thai not in ("nhap", "tra_lai"):
        raise LoiKhachSan("Gói này không ở trạng thái nháp")
    g.trang_thai, g.gui_boi = "cho_duyet", u.username
    db.commit()
    return g


def duyet_goi(db: Session, u: User, gid: int, dong_y: bool, ly_do: str = "", now: datetime | None = None) -> GoiGiaVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành duyệt giá")
    g = db.get(GoiGiaVtd, gid)
    if g is None:
        raise LoiKhachSan("Không có gói này", 404)
    if g.trang_thai != "cho_duyet":
        raise LoiKhachSan("Gói này không chờ duyệt")
    if g.sua_boi == u.username and not _co(u, TOAN_QUYEN):
        raise LoiKhachSan("Người nhập giá không tự duyệt — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    if not dong_y and len((ly_do or "").strip()) < 5:
        raise LoiKhachSan("Trả lại phải ghi lý do")
    if dong_y:                                                        # KS-17: giá chưa thuế + thuế chưa xác nhận = giá sai
        lp0 = db.get(LoaiPhongVtd, g.loai_phong_id)
        k0 = db.get(KhachSanVtd, lp0.khach_san_id)
        if not k0.thue_phi_xac_nhan:
            raise LoiKhachSan("Chưa xác nhận thuế phí với khách sạn (giá đã gồm 8% VAT) — xác nhận ở hồ sơ khách sạn rồi mới duyệt giá")
        if lp0.toi_da_nguoi_lon is None:
            raise LoiKhachSan("Loại phòng chưa xác nhận số người lớn tối đa — xác nhận rồi mới duyệt giá")
    g.trang_thai = "da_duyet" if dong_y else "tra_lai"
    g.ly_do_tra_lai = "" if dong_y else ly_do.strip()[:300]
    g.duyet_boi, g.duyet_luc = u.username, now or datetime.now()
    lp = db.get(LoaiPhongVtd, g.loai_phong_id)
    k = db.get(KhachSanVtd, lp.khach_san_id)
    _audit(db, u, "ks_vtd_goi_duyet" if dong_y else "ks_vtd_goi_tra_lai", k.ma, None, {"goi": g.id, "ly_do": g.ly_do_tra_lai})
    db.commit()
    return g


# ══ VTOS · ẢNH ═════════════════════════════════════════════════════════════════════════════════════
def _anh_cua(db: Session, kid: int) -> list[AnhKhachSanVtd]:
    return db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id == kid)
                      .order_by(AnhKhachSanVtd.la_bia.desc(), AnhKhachSanVtd.thu_tu, AnhKhachSanVtd.id)).scalars().all()


def _anh_duyet(db: Session, kids: list[int]) -> dict[int, list[AnhKhachSanVtd]]:
    ra: dict[int, list] = {}
    if kids:
        q = (select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id.in_(kids), AnhKhachSanVtd.trang_thai == "da_duyet")
             .order_by(AnhKhachSanVtd.la_bia.desc(), AnhKhachSanVtd.thu_tu, AnhKhachSanVtd.id))
        for a in db.execute(q).scalars():
            ra.setdefault(a.khach_san_id, []).append(a)
    return ra


def tai_anh(db: Session, u: User, kid: int, ten_tep: str, data: bytes, d: dict, now: datetime | None = None) -> tuple[AnhKhachSanVtd, bool]:
    from app.services import attachments as AT
    from app.services.nha_hang import KIEU_ANH, LoiNhaHang, _co_pil, _kiem_tep_anh, _lam_nhe
    _quyen(u, VAI_NHAP, "Chỉ Điều hành tải ảnh khách sạn")
    k = _ks(db, kid)
    try:
        duoi = _kiem_tep_anh(ten_tep, data)
    except LoiNhaHang as ex:
        raise LoiKhachSan(str(ex))
    nhom = str(d.get("nhom") or "").strip()
    if nhom not in NHOM_ANH_KS:
        raise LoiKhachSan("Chọn nhóm ảnh")
    lid = d.get("loai_phong_id")
    lid = int(lid) if lid not in (None, "", 0, "0") else None
    if lid is not None:
        lp = db.get(LoaiPhongVtd, lid)
        if lp is None or lp.khach_san_id != k.id:
            raise LoiKhachSan("Loại phòng không thuộc khách sạn này")
    ds = _anh_cua(db, kid)
    cs = AT._sha(data)
    from app.models.attachments import Attachment
    for x in ds:
        a = db.get(Attachment, x.attachment_id)
        if a is not None and a.checksum == cs:
            return x, False
    if len(ds) >= ANH_TOI_DA:
        raise LoiKhachSan(f"Album đã đủ {ANH_TOI_DA} ảnh — xóa bớt ảnh cũ trước khi tải thêm")
    hien, nho, rong, cao = _lam_nhe(data)
    if hien is None and _co_pil():
        raise LoiKhachSan("Tệp không mở được như một ảnh — kiểm tra lại tệp")
    ma = f"ks{k.id}"
    try:
        a, _ = AT.dinh_kem(db, "khach_san_vtd", ma, ten_tep, data, kieu=KIEU_ANH[duoi], loai="hinh_anh",
                           mo_ta=f"Album {k.ma}", boi=u.username)
        ah = AT.dinh_kem(db, "khach_san_vtd", ma, f"{ten_tep}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Bản hiển thị · {k.ma}", boi=u.username, nguon="he_thong")[0] if hien else a
        an = AT.dinh_kem(db, "khach_san_vtd", ma, f"{ten_tep}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Ảnh nhỏ · {k.ma}", boi=u.username, nguon="he_thong")[0] if nho else ah
    except ValueError as ex:
        raise LoiKhachSan(str(ex))
    x = AnhKhachSanVtd(khach_san_id=k.id, loai_phong_id=lid, attachment_id=a.id, hien_id=ah.id, nho_id=an.id,
                       rong=rong, cao=cao, nhom=nhom, chu_thich=str(d.get("chu_thich") or "").strip()[:200],
                       mo_ta_thay_the=str(d.get("mo_ta_thay_the") or "").strip()[:200],          # KS-17
                       nguon=str(d.get("nguon") or "").strip()[:200], thu_tu=max([y.thu_tu for y in ds], default=0) + 1,
                       la_bia=False, trang_thai="da_duyet", tai_boi=u.username, tai_luc=now or datetime.now(),
                       duyet_boi="tu_dong", duyet_luc=now or datetime.now())   # KS-16c: bỏ duyệt ảnh — tải là hiện
    db.add(x)
    db.commit()
    db.refresh(x)
    return x, True


def _lay_anh(db: Session, pid: int) -> AnhKhachSanVtd:
    x = db.get(AnhKhachSanVtd, pid)
    if x is None:
        raise LoiKhachSan("Không có ảnh này", 404)
    return x


def sua_anh(db: Session, u: User, pid: int, d: dict) -> AnhKhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành sửa ảnh khách sạn")
    x = _lay_anh(db, pid)
    if "nhom" in d:
        if d["nhom"] not in NHOM_ANH_KS:
            raise LoiKhachSan("Nhóm ảnh không hợp lệ")
        x.nhom = d["nhom"]
    if "loai_phong_id" in d:
        lid = d["loai_phong_id"]
        lid = int(lid) if lid not in (None, "", 0, "0") else None
        if lid is not None:
            lp = db.get(LoaiPhongVtd, lid)
            if lp is None or lp.khach_san_id != x.khach_san_id:
                raise LoiKhachSan("Loại phòng không thuộc khách sạn này")
        x.loai_phong_id = lid
    if "chu_thich" in d:
        x.chu_thich = str(d["chu_thich"] or "").strip()[:200]           # KS-16c: không còn duyệt lại
    if "mo_ta_thay_the" in d:                                           # KS-17: chữ thay ảnh cho trình đọc màn hình
        x.mo_ta_thay_the = str(d["mo_ta_thay_the"] or "").strip()[:200]
    if "thu_tu" in d:
        x.thu_tu = int(d["thu_tu"] or 0)
    if d.get("la_bia"):
        for y in _anh_cua(db, x.khach_san_id):
            y.la_bia = y.id == x.id
    db.commit()
    return x


def gui_duyet_anh(db: Session, u: User, ids: list[int]) -> int:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành gửi duyệt ảnh")
    n = 0
    for pid in ids[:200]:
        x = db.get(AnhKhachSanVtd, int(pid))
        if x is not None and x.trang_thai in ("nhap", "tra_lai"):
            x.trang_thai, n = "cho_duyet", n + 1
    db.commit()
    return n


def duyet_anh(db: Session, u: User, ids: list[int], dong_y: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành duyệt ảnh")
    if not dong_y and len((ly_do or "").strip()) < 5:
        raise LoiKhachSan("Trả lại phải ghi lý do")
    now = now or datetime.now()
    doi, bo = 0, []
    for pid in ids[:200]:
        x = db.get(AnhKhachSanVtd, int(pid))
        if x is None or x.trang_thai != "cho_duyet":
            continue
        if x.tai_boi == u.username and not _co(u, TOAN_QUYEN):
            bo.append({"id": x.id, "ly_do": "Người tải không tự duyệt"})
            continue
        x.trang_thai = "da_duyet" if dong_y else "tra_lai"
        x.ly_do_tra_lai = "" if dong_y else ly_do.strip()[:300]
        x.duyet_boi, x.duyet_luc = u.username, now
        doi += 1
    db.commit()
    return {"da_doi": doi, "bo_qua": bo}


def an_anh(db: Session, u: User, pid: int, an: bool) -> AnhKhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành ẩn ảnh")
    x = _lay_anh(db, pid)
    x.trang_thai = "an" if an else "da_duyet"
    if an:
        x.la_bia = False
    db.commit()
    return x


def xoa_anh(db: Session, u: User, pid: int) -> int:
    """KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh — ai tải người đó tự xóa; TP Điều hành (và Chủ tịch, TGĐ) xóa mọi
    ảnh. Xóa khỏi album, tệp vẫn trong kho chứng từ."""
    x = _lay_anh(db, pid)
    if x.tai_boi != u.username and not _co(u, VAI_DUYET):
        raise LoiKhachSan("Chỉ người tải ảnh hoặc TP Điều hành xóa ảnh này", 403)
    kid = x.khach_san_id
    from app.services import rules as R
    R.audit(db, u.username, u.role, "ks_vtd_xoa_anh", f"khach_san_vtd:{kid}", before={"anh": x.id, "tai_boi": x.tai_boi})
    db.delete(x)
    db.commit()
    return kid


def tep_anh(db: Session, u: User | None, pid: int, co: str):
    """co: goc (chỉ VTOS) | hien | nho. Cổng (u=None): chỉ ảnh ĐÃ DUYỆT của khách sạn ĐANG HIỆN, không bao giờ bản gốc."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    x = _lay_anh(db, pid)
    if co not in ("goc", "hien", "nho"):
        raise LoiKhachSan("Không có cỡ ảnh này", 404)
    if u is None:
        k = db.get(KhachSanVtd, x.khach_san_id)
        if co == "goc" or x.trang_thai != "da_duyet" or k is None or not k.hien_cong or k.ngung:
            raise LoiKhachSan("Không có ảnh này", 404)
    else:
        _quyen(u, VAI_XEM, "Không có quyền")
    a = db.get(Attachment, {"goc": x.attachment_id, "hien": x.hien_id, "nho": x.nho_id}[co])
    return AT.doc(db, a), a


def _anh_out(x: AnhKhachSanVtd, cong: bool = False) -> dict:
    goc = "/api/v1/ks-vtd-anh" if cong else "/api/v1/khach-san-vtd/anh"
    o = {"id": x.id, "nhom": x.nhom, "nhom_ten": NHOM_ANH_KS.get(x.nhom, x.nhom), "chu_thich": x.chu_thich,
         "mo_ta_thay_the": x.mo_ta_thay_the or "",                                                        # KS-17
         "loai_phong_id": x.loai_phong_id, "la_bia": x.la_bia,
         "hien": f"{goc}/{x.id}/hien", "nho": f"{goc}/{x.id}/nho"}
    if not cong:
        o.update({"trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_ANH_KS.get(x.trang_thai, x.trang_thai),
                  "ly_do_tra_lai": x.ly_do_tra_lai, "nguon": x.nguon, "tai_boi": x.tai_boi, "duyet_boi": x.duyet_boi,
                  "thu_tu": x.thu_tu, "goc": f"{goc}/{x.id}/goc"})
    return o


# ══ VTOS · ĐỌC ═════════════════════════════════════════════════════════════════════════════════════
def _ks_noi_bo(k: KhachSanVtd) -> dict:
    return {**{x: getattr(k, x) for x in TRUONG_KS}, "cs_moc_tuoi": [chuan_moc(m) for m in (k.cs_moc_tuoi or []) if m.get("cach") != "nguoi_lon"],
            "cs_phi_giuong_phu": float(k.cs_phi_giuong_phu) if k.cs_phi_giuong_phu is not None else None, "id": k.id, "ma": k.ma, "hien_cong": k.hien_cong, "hien_boi": k.hien_boi,
            "tat_ly_do": k.tat_ly_do, "ngung": k.ngung,
            "vi_do": k.vi_do, "kinh_do": k.kinh_do, "toa_do_nguon": k.toa_do_nguon or "", "mo_thanh_toan": bool(k.mo_thanh_toan),   # KS-16s
            "sua_boi": k.sua_boi, "tao_boi": k.tao_boi,   # KS-19g: hai trường này trước đây nằm lẫn trong chú thích
            "sua_luc": k.sua_luc.isoformat(timespec="minutes") if k.sua_luc else None}


def _goi_out(g: GoiGiaVtd, mua: list[MuaGiaVtd]) -> dict:
    return {"id": g.id, "loai_phong_id": g.loai_phong_id, "ten": g.ten, "bua_sang": g.bua_sang, "huy_truoc_ngay": g.huy_truoc_ngay,
            "dang_ban": g.dang_ban, "trang_thai": g.trang_thai, "trang_thai_ten": TRANG_THAI_GOI.get(g.trang_thai, g.trang_thai),
            "ly_do_tra_lai": g.ly_do_tra_lai, "sua_boi": g.sua_boi, "duyet_boi": g.duyet_boi,
            "tre_em_che_do": g.tre_em_che_do or "", "gia_tre": [chuan_moc(m) for m in (g.gia_tre or [])],   # KS-16k
            "huy_gio_chot": g.huy_gio_chot or "", "huy_mui_gio": g.huy_mui_gio or "Asia/Ho_Chi_Minh",
            "cho_tra_sau": bool(g.cho_tra_sau),                                                           # KS-17
            "mua": [{"id": m.id, "tu_ngay": m.tu_ngay.isoformat(), "den_ngay": m.den_ngay.isoformat(), "gia_thuong": float(m.gia_thuong),
                     "gia_cuoi_tuan": float(m.gia_cuoi_tuan) if m.gia_cuoi_tuan else None,
                     "gia_niem_yet": float(m.gia_niem_yet) if m.gia_niem_yet else None, "ghi_chu": m.ghi_chu} for m in mua]}


def _goi_cua(db: Session, lids: list[int]) -> dict[int, list[GoiGiaVtd]]:
    ra: dict[int, list] = {}
    if lids:
        for g in db.execute(select(GoiGiaVtd).where(GoiGiaVtd.loai_phong_id.in_(lids)).order_by(GoiGiaVtd.id)).scalars():
            ra.setdefault(g.loai_phong_id, []).append(g)
    return ra


def ds_vtos(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    ks = db.execute(select(KhachSanVtd).order_by(KhachSanVtd.tinh_thanh, KhachSanVtd.ten)).scalars().all()
    ids = [k.id for k in ks]
    anh = {}
    lp = {}
    if ids:
        for a in db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id.in_(ids))).scalars():
            anh.setdefault(a.khach_san_id, []).append(a)
        for x in db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id.in_(ids))).scalars():
            lp.setdefault(x.khach_san_id, []).append(x)
    goi = _goi_cua(db, [x.id for v in lp.values() for x in v])
    dong = []
    for k in ks:
        gs = [g for x in lp.get(k.id, []) for g in goi.get(x.id, [])]
        a = anh.get(k.id, [])
        bia = next((x for x in a if x.la_bia and x.trang_thai == "da_duyet"), None) or next((x for x in a if x.trang_thai == "da_duyet"), None)
        dong.append({**_ks_noi_bo(k), "so_anh": len(a), "anh_duyet": sum(x.trang_thai == "da_duyet" for x in a),
                     "anh_cho": sum(x.trang_thai == "cho_duyet" for x in a), "so_loai_phong": len(lp.get(k.id, [])),
                     "goi_duyet": sum(g.trang_thai == "da_duyet" for g in gs), "goi_cho": sum(g.trang_thai == "cho_duyet" for g in gs),
                     "bia": _anh_out(bia)["nho"] if bia else None, "thieu_anh": max(0, ANH_CHUAN - len(a))})
    return {"khach_san": dong, "thanh_pho": [{"ten": t, "mien": MIEN[m]} for t, (m, _k) in THANH_PHO.items()],
            "loai": LOAI_CHO_O, "tien_ich": TIEN_ICH, "nhom_anh": NHOM_ANH_KS,
            "nhan_tre_em": NHAN_TRE_EM, "cach_tinh_tre": CACH_TINH_TRE, "tien_nghi_phong": TIEN_NGHI_PHONG, "phu_hop": PHU_HOP, "vat_pt": VAT_PT,   # KS-16j · KS-19
            "nguon_lp": NGUON_LP, "can_xac_nhan": CAN_XAC_NHAN, "trang_thai_dc": TRANG_THAI_DC,
            "nhom_tuoi": NHOM_TUOI, "kieu_gia": KIEU_GIA, "che_do_tre_goi": CHE_DO_TRE_GOI,   # KS-16k
            "mui_gio_huy": MUI_GIO_HUY,                                                          # KS-17
            "duoc_nhap": _co(u, VAI_NHAP), "duoc_duyet": _co(u, VAI_DUYET), "toi": u.username,
            "toan_quyen": _co(u, TOAN_QUYEN), "tt_chung": tt_chung(db),   # KS-16s
            "cho_duyet": {"anh": sum(d["anh_cho"] for d in dong), "goi": sum(d["goi_cho"] for d in dong)}}


def album_nhac(n: int) -> dict:
    """KS-16p: 30–50 ảnh / khách sạn. Dưới 30 chỉ NHẮC, không chặn bật hiện; đủ 50 thì chặn tải thêm."""
    return {"so": n, "toi_da": ANH_TOI_DA, "chuan": ANH_CHUAN, "thieu": max(0, ANH_CHUAN - n),
            "nhac": (f"Còn thiếu {ANH_CHUAN - n} ảnh để đạt {ANH_CHUAN}" if n < ANH_CHUAN else
                     f"Album đã đủ {ANH_TOI_DA} ảnh" if n >= ANH_TOI_DA else "")}


def mot_vtos(db: Session, u: User, kid: int) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    k = _ks(db, kid)
    lps = _lp_cua(db, kid)
    goi = _goi_cua(db, [x.id for x in lps])
    mua = _mua_cua(db, [g.id for v in goi.values() for g in v])
    from app.services import video_dich_vu as VD   # KS-16f
    return {"khach_san": _ks_noi_bo(k), "dieu_kien": dieu_kien_hien(db, k),
            "anh": [_anh_out(x) for x in _anh_cua(db, kid)], "so_video": len(VD._cua(db, "khach_san_vtd", kid, False)),
            "video_toi_da": VD.toi_da("khach_san_vtd"), "album": album_nhac(len(_anh_cua(db, kid))),   # KS-16p
            "loai_phong": [{"id": x.id, "ten": x.ten, "dien_tich": x.dien_tich, "giuong": x.giuong, "mo_ta": x.mo_ta,
                            "toi_da_nguoi_lon": x.toi_da_nguoi_lon, "toi_da_tre_em": x.toi_da_tre_em, "so_phong": x.so_phong,
                            "tong_khach_toi_da": x.tong_khach_toi_da,                                     # KS-17
                            "thu_tu": x.thu_tu, "dang_ban": x.dang_ban, **_lp_them(x),
                            "goi": [_goi_out(g, mua.get(g.id, [])) for g in goi.get(x.id, [])]} for x in lps]}


def _lp_them(x: LoaiPhongVtd) -> dict:
    """KS-16j: các ô mới của loại phòng (VTOS)."""
    return {"mo_ta_dai": x.mo_ta_dai or "", "tien_nghi": x.tien_nghi or [], "giuong_phu_toi_da": x.giuong_phu_toi_da,
            "noi_cui": x.noi_cui, "nguon": x.nguon or "", "ky_doi_chieu": x.ky_doi_chieu or "", "ma_hang": x.ma_hang or "",
            "ten_tuong_duong": x.ten_tuong_duong or "", "can_xac_nhan": x.can_xac_nhan or [],
            "ghi_chu_doi_chieu": x.ghi_chu_doi_chieu or "", "trang_thai_dc": x.trang_thai_dc or "",
            # KS-16k
            "suc_chua": x.suc_chua, "khach_them_toi_da": x.khach_them_toi_da, "so_tre_mien_phi": x.so_tre_mien_phi,
            "phi_giuong_phu": float(x.phi_giuong_phu) if x.phi_giuong_phu is not None else None,
            "giuong_phu_kieu": x.giuong_phu_kieu or "", "giuong_phu_xac_nhan": bool(x.giuong_phu_xac_nhan),
            "gia_tre_rieng": [chuan_moc(m) for m in x.gia_tre_rieng] if x.gia_tre_rieng else None}


def cho_duyet(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    anh = db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.trang_thai == "cho_duyet").order_by(AnhKhachSanVtd.id)).scalars().all()
    goi = db.execute(select(GoiGiaVtd).where(GoiGiaVtd.trang_thai == "cho_duyet").order_by(GoiGiaVtd.id)).scalars().all()
    lp = {x.id: x for x in db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.id.in_([g.loai_phong_id for g in goi] or [0]))).scalars()}
    kids = {a.khach_san_id for a in anh} | {x.khach_san_id for x in lp.values()}
    ks = {k.id: k for k in db.execute(select(KhachSanVtd).where(KhachSanVtd.id.in_(list(kids) or [0]))).scalars()}
    mua = _mua_cua(db, [g.id for g in goi])
    return {"anh": [{**_anh_out(a), "khach_san": ks[a.khach_san_id].ten} for a in anh],
            "goi": [{**_goi_out(g, mua.get(g.id, [])), "loai_phong": lp[g.loai_phong_id].ten,
                     "khach_san": ks[lp[g.loai_phong_id].khach_san_id].ten} for g in goi],
            "duoc_duyet": _co(u, VAI_DUYET), "toi": u.username, "toan_quyen": _co(u, TOAN_QUYEN)}


# ══ KS-16j · TRẺ EM & GIƯỜNG PHỤ KIỂU AGODA ════════════════════════════════════════════════════════
def doc_tuoi(tre_em: int, tuoi) -> list[int] | None:
    """Tuổi từng trẻ («4,8» hoặc [4, 8]). Thiếu / sai số lượng → None (máy không đoán tuổi)."""
    if tre_em <= 0:
        return []
    if isinstance(tuoi, str):
        tuoi = [x for x in tuoi.replace(";", ",").split(",") if x.strip() != ""]
    try:
        ds = [int(x) for x in (tuoi or [])]
    except (TypeError, ValueError):
        return None
    if len(ds) != tre_em or any(not 0 <= t <= TUOI_TRE_TOI_DA for t in ds):
        return None
    return ds


def bang_ap_dung(k: KhachSanVtd, lp: LoaiPhongVtd | None, g: GoiGiaVtd | None) -> tuple[list[dict] | None, str]:
    """KS-16k: bảng giá trẻ em máy dùng — gói (nếu có) → loại phòng (nếu có) → khách sạn. None = tính trẻ như người lớn."""
    if g is not None and g.tre_em_che_do == "nhu_nguoi_lon":
        return None, "goi"
    if g is not None and g.tre_em_che_do == "rieng" and g.gia_tre:
        return [chuan_moc(m) for m in g.gia_tre], "goi"
    if lp is not None and lp.gia_tre_rieng:
        return [chuan_moc(m) for m in lp.gia_tre_rieng], "phong"
    return [chuan_moc(m) for m in (k.cs_moc_tuoi or []) if m.get("cach") != "nguoi_lon"], "ks"


def _loai_tre(k: KhachSanVtd, bang: list[dict] | None, tuoi: list[int]) -> dict:
    """Xếp từng trẻ vào nhóm tuổi → {ok, ly_do, them_nl, tre: [{tuoi, nhom, cach, gia, an_sang}]} — trên bảng = người lớn."""
    nhan = k.cs_nhan_tre_em or "chua_xac_nhan"
    if not tuoi:
        return {"ok": True, "ly_do": "", "them_nl": 0, "tre": []}
    if nhan == "chua_xac_nhan":
        return {"ok": False, "ly_do": "Chính sách trẻ em cần khách sạn xác nhận — gửi yêu cầu để Vietourist báo"}
    if nhan == "khong":
        return {"ok": False, "ly_do": "Khách sạn không nhận trẻ em", "khong_nhan": True}
    if nhan == "tu_tuoi" and k.cs_tre_tu_tuoi is not None and min(tuoi) < k.cs_tre_tu_tuoi:
        return {"ok": False, "ly_do": f"Khách sạn chỉ nhận khách từ {k.cs_tre_tu_tuoi} tuổi", "khong_nhan": True}
    if bang is None:                         # gói tính trẻ như người lớn
        return {"ok": True, "ly_do": "", "them_nl": len(tuoi), "tre": []}
    tren = max((m["den"] for m in bang), default=-1)
    them, tre = 0, []
    for t in tuoi:
        if t > tren:
            them += 1
            continue
        m = next((x for x in bang if x["tu"] <= t <= x["den"]), None)
        if m is None:
            return {"ok": False, "ly_do": f"Chưa có giá cho trẻ {t} tuổi — gửi yêu cầu để Vietourist báo"}
        tre.append({"tuoi": t, **{x: m[x] for x in ("nhom", "cach", "gia", "an_sang")}})
    return {"ok": True, "ly_do": "", "them_nl": them, "tre": tre}


def _gia_kieu(kieu: str, gia: float, gia_dem: float) -> float:
    return gia_dem * gia / 100 if kieu == "phan_tram" else gia


def _mot_phong(k: KhachSanVtd, lp: LoaiPhongVtd, a: int, tre: list[dict], gia_dem: float, bua_sang: bool) -> dict:
    """Một phòng theo cách Agoda: a người lớn + trẻ. Trẻ «luôn miễn phí» và số trẻ miễn phí của phòng (nhỏ nhất trước)
    ở chung không mất tiền; vượt sức chứa cơ bản thì nằm giường phụ (trẻ lớn nhất trước, rồi người lớn) và trả giá
    giường phụ thay cho giá trẻ em; còn lại trả giá trẻ em của nhóm. Gói có bữa sáng: trẻ trả giá ăn sáng của nhóm."""
    ten = lp.ten
    if lp.toi_da_nguoi_lon is None:                                   # KS-17
        return {"ok": False, "ly_do": f"«{ten}»: số người lớn tối đa cần khách sạn xác nhận — gửi yêu cầu"}
    if lp.tong_khach_toi_da is not None and a + len(tre) > lp.tong_khach_toi_da:
        return {"ok": False, "ly_do": f"«{ten}» tối đa {lp.tong_khach_toi_da} khách một phòng", "vuot": True}
    if tre and lp.toi_da_tre_em is None:
        return {"ok": False, "ly_do": f"«{ten}»: số trẻ em của phòng cần khách sạn xác nhận — gửi yêu cầu"}
    if len(tre) > (lp.toi_da_tre_em or 0) + max(0, lp.toi_da_nguoi_lon - a):
        return {"ok": False, "ly_do": f"«{ten}» không đủ chỗ cho số trẻ em này", "vuot": True}
    co_phi = sorted([x for x in tre if x["cach"] != "mien_phi"], key=lambda x: x["tuoi"])
    so_mp = lp.so_tre_mien_phi if lp.so_tre_mien_phi is not None else k.cs_so_tre_mien_phi
    if co_phi and so_mp is None:
        return {"ok": False, "ly_do": f"«{ten}»: số trẻ miễn phí cần khách sạn xác nhận — gửi yêu cầu"}
    mp = {id(x) for x in tre if x["cach"] == "mien_phi"} | {id(x) for x in co_phi[:so_mp or 0]}
    dem_sc = a + len(tre) - (0 if k.cs_tre_mp_tinh_suc_chua else len(mp))
    goc = lp.suc_chua or lp.toi_da_nguoi_lon
    gp = max(0, dem_sc - goc)
    if gp:
        if lp.khach_them_toi_da is None or lp.giuong_phu_toi_da is None:
            return {"ok": False, "ly_do": f"«{ten}»: khách thêm / giường phụ cần khách sạn xác nhận — gửi yêu cầu"}
        if gp > min(lp.khach_them_toi_da, lp.giuong_phu_toi_da):
            return {"ok": False, "ly_do": f"«{ten}» không đủ chỗ cho số khách này", "vuot": True}
    kieu = lp.giuong_phu_kieu or k.cs_giuong_phu_kieu or "co_dinh"
    phi = lp.phi_giuong_phu if lp.phi_giuong_phu is not None else k.cs_phi_giuong_phu
    if gp and phi is None:
        return {"ok": False, "ly_do": f"«{ten}»: giá giường phụ cần khách sạn xác nhận — gửi yêu cầu"}
    # ai nằm giường phụ: trẻ phải trả tiền, lớn nhất trước; thiếu thì người lớn
    tinh_sc = [x for x in tre if id(x) not in mp] if not k.cs_tre_mp_tinh_suc_chua else list(tre)
    nam_gp = sorted(tinh_sc, key=lambda x: -x["tuoi"])[:gp]
    gp_nl = gp - len(nam_gp)
    dong, cong = [], 0.0
    p_gp = _gia_kieu(kieu, float(phi or 0), gia_dem)
    for x in sorted(tre, key=lambda x: -x["tuoi"]):
        if any(x is y for y in nam_gp):
            dong.append({"nhan": f"Bé {x['tuoi']} tuổi · giường phụ", "dem": p_gp}); cong += p_gp
        elif id(x) in mp:
            dong.append({"nhan": f"Bé {x['tuoi']} tuổi · ở chung miễn phí", "dem": 0.0})
        else:
            v = _gia_kieu(x["cach"], x["gia"], gia_dem)
            dong.append({"nhan": f"Bé {x['tuoi']} tuổi · ở chung", "dem": v}); cong += v
        if bua_sang:
            if x["an_sang"] is None:
                return {"ok": False, "ly_do": f"Giá ăn sáng cho trẻ {x['tuoi']} tuổi cần khách sạn xác nhận — gửi yêu cầu"}
            dong.append({"nhan": f"Bé {x['tuoi']} tuổi · ăn sáng", "dem": float(x["an_sang"])}); cong += float(x["an_sang"])
    if gp_nl:
        dong.append({"nhan": f"{gp_nl} người lớn · giường phụ", "dem": p_gp * gp_nl}); cong += p_gp * gp_nl
    return {"ok": True, "ly_do": "", "dem": cong, "giuong_phu": gp, "chi_tiet": dong,
            "cho_xac_nhan": bool(gp and lp.giuong_phu_xac_nhan)}


def phan_khach(k: KhachSanVtd, don_vi: list[tuple], nl: int, te: int, tuoi: list[int] | None) -> dict:
    """Chia khách vào các phòng đã chọn. don_vi = [(loại phòng, gói | None, giá phòng / đêm)] — mỗi phần tử một phòng.
    Trả phụ thu / đêm và chi tiết từng phòng (cùng thứ tự)."""
    if te > 0 and tuoi is None:
        return {"ok": False, "ly_do": "Chọn tuổi từng trẻ em để xem giá", "phong": []}
    n = len(don_vi)
    if n == 0:
        return {"ok": False, "ly_do": "Chọn ít nhất một phòng", "phong": []}
    # mỗi phòng có thể theo một bảng giá khác (gói / phòng) → xếp trẻ theo bảng của phòng đầu để chia, tính lại từng phòng
    loai = [_loai_tre(k, bang_ap_dung(k, lp, g)[0], tuoi or []) for lp, g, _p in don_vi]
    bad = next((x for x in loai if not x["ok"]), None)
    if bad:
        return {**bad, "phong": []}
    so_nl = nl + loai[0]["them_nl"]
    a = [so_nl // n + (1 if i < so_nl % n else 0) for i in range(n)]
    tuoi_tre = sorted([x["tuoi"] for x in loai[0]["tre"]], reverse=True)
    chia: list[list[int]] = [[] for _ in range(n)]
    for t in tuoi_tre:
        i = max(range(n), key=lambda j: ((don_vi[j][0].suc_chua or don_vi[j][0].toi_da_nguoi_lon or 0) + (don_vi[j][0].toi_da_tre_em or 0)
                                         - a[j] - len(chia[j]), -j))
        chia[i].append(t)
    ra = []
    for i, (lp, g, gia_dem) in enumerate(don_vi):
        x = _loai_tre(k, bang_ap_dung(k, lp, g)[0], chia[i])
        if not x["ok"]:
            return {**x, "phong": []}
        r = _mot_phong(k, lp, a[i] + x["them_nl"], x["tre"], float(gia_dem or 0), bool(g.bua_sang) if g else False)
        if not r["ok"]:
            return {**r, "phong": []}
        ra.append(r)
    return {"ok": True, "ly_do": "", "phong": ra, "dem": sum(r["dem"] for r in ra),
            "cho_xac_nhan": any(r["cho_xac_nhan"] for r in ra)}


# ══ KS-20b (Chủ tịch chọn «Máy nhận đúng cách chia», 06/11/2026 — bản v1.3 D2/M1/M2) ══════════════════════════════
# Khách khai riêng từng phòng (tối đa 9): [{nl, te, tuoi}]. Máy ghép mỗi phòng đã chọn với một nhóm khách sao cho
# mọi phòng hợp sức chứa (ghép cặp), tính phụ thu theo đúng người trong phòng ấy. Khách đổi được cách ghép (`xep`).
PHONG_TOI_DA = 9


def doc_chia(chia) -> list[dict] | None:
    """Đọc cách chia khách từng phòng. Rỗng → None (dùng tổng người lớn / trẻ em như trước)."""
    if not chia:
        return None
    if not isinstance(chia, list):
        raise LoiKhachSan("Cách chia phòng không hợp lệ")
    if len(chia) > PHONG_TOI_DA:
        raise LoiKhachSan(f"Tối đa {PHONG_TOI_DA} phòng một lần đặt")
    ra = []
    for i, c in enumerate(chia, 1):
        c = c if isinstance(c, dict) else {}
        try:
            nl, te = int(c.get("nl") or 0), int(c.get("te") or 0)
        except (TypeError, ValueError):
            raise LoiKhachSan(f"Phòng {i}: số khách không hợp lệ")
        if nl < 1:
            raise LoiKhachSan(f"Phòng {i} cần ít nhất 1 người lớn")
        if nl > 30 or not 0 <= te <= 20:
            raise LoiKhachSan(f"Phòng {i}: số khách không hợp lệ")
        tuoi = doc_tuoi(te, c.get("tuoi"))
        if tuoi is None:
            raise LoiKhachSan(f"Phòng {i}: chọn tuổi từng trẻ em")
        ra.append({"nl": nl, "te": te, "tuoi": tuoi})
    return ra


def tong_chia(chia: list[dict]) -> tuple[int, int, list[int]]:
    return sum(c["nl"] for c in chia), sum(c["te"] for c in chia), [t for c in chia for t in c["tuoi"]]


def ta_nhom(c: dict) -> str:
    """«2 người lớn + 1 trẻ (7 tuổi)»"""
    t = f"{c['nl']} người lớn"
    if c["te"]:
        t += f" + {c['te']} trẻ ({', '.join(str(x) for x in c['tuoi'])} tuổi)"
    return t


def _suc_lp(lp: LoaiPhongVtd) -> int:
    return int(lp.tong_khach_toi_da or ((lp.suc_chua or lp.toi_da_nguoi_lon or 0) + (lp.toi_da_tre_em or 0)
                                       + (lp.khach_them_toi_da or 0)))


def _phong_nhom(k: KhachSanVtd, lp: LoaiPhongVtd, g, gia_dem: float, c: dict) -> dict:
    x = _loai_tre(k, bang_ap_dung(k, lp, g)[0], c["tuoi"])
    if not x["ok"]:
        return x
    return _mot_phong(k, lp, c["nl"] + x["them_nl"], x["tre"], float(gia_dem or 0), bool(g.bua_sang) if g else False)


def phan_khach_chia(k: KhachSanVtd, don_vi: list[tuple], chia: list[dict], xep=None) -> dict:
    """Ghép mỗi phòng (don_vi, cùng thứ tự với phan_khach) với một nhóm khách. xep[i] = số thứ tự nhóm của phòng i.
    xep hợp lệ (hoán vị) thì giữ; không thì máy tự ghép: phòng rộng trước, nhóm đông trước, đổi cặp khi kẹt."""
    n = len(don_vi)
    if n != len(chia):
        thieu = len(chia) - n
        return {"ok": False, "lech": -thieu, "phong": [],
                "ly_do": (f"Bạn khai {len(chia)} phòng nhưng mới chọn {n} — chọn thêm {thieu} phòng" if thieu > 0 else
                          f"Bạn chọn {n} phòng nhưng chỉ khai {len(chia)} — bớt {-thieu} phòng hoặc thêm phòng ở «Chia phòng»")}
    kq: dict[tuple[int, int], dict] = {}

    def thu(i: int, j: int) -> dict:
        if (i, j) not in kq:
            lp, g, gia = don_vi[i]
            kq[(i, j)] = _phong_nhom(k, lp, g, gia, chia[j])
        return kq[(i, j)]

    try:
        xep = [int(x) for x in xep] if xep else None
    except (TypeError, ValueError):
        xep = None
    if xep is not None and sorted(xep) == list(range(n)):
        for i, j in enumerate(xep):
            r = thu(i, j)
            if not r["ok"]:
                return {**r, "phong": [], "ly_do": f"Phòng {j + 1} ({ta_nhom(chia[j])}) không xếp được vào «{don_vi[i][0].ten}»: {r['ly_do']}"}
    else:
        phong = sorted(range(n), key=lambda i: (-_suc_lp(don_vi[i][0]), i))
        nhom = sorted(range(n), key=lambda j: (-(chia[j]["nl"] + chia[j]["te"]), -chia[j]["nl"], j))
        cua: dict[int, int] = {}                                     # nhóm → phòng

        def tim(i: int, da: set) -> bool:                            # ghép cặp (đường tăng)
            for j in nhom:
                if j in da or not thu(i, j)["ok"]:
                    continue
                da.add(j)
                if j not in cua or tim(cua[j], da):
                    cua[j] = i
                    return True
            return False

        for i in phong:
            if not tim(i, set()):
                loi = next((r for (a, _b), r in kq.items() if a == i and not r["ok"]), None)
                if loi and (loi.get("khong_nhan") or "xác nhận" in loi["ly_do"]):
                    return {**loi, "phong": []}
                return {"ok": False, "phong": [], "vuot": True,
                        "ly_do": f"Không xếp được khách vào «{don_vi[i][0].ten}» — chọn loại phòng rộng hơn hoặc chia lại khách"}
        xep = [0] * n
        for j, i in cua.items():
            xep[i] = j
    ra = [{**thu(i, xep[i]), "nhom": xep[i]} for i in range(n)]
    return {"ok": True, "ly_do": "", "phong": ra, "xep": xep, "dem": sum(r["dem"] for r in ra),
            "cho_xac_nhan": any(r["cho_xac_nhan"] for r in ra)}


def _vnd(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", ".")


def _dong_bang(bang: list[dict]) -> list[str]:
    ra = []
    for m in bang:
        tuoi = f"{m['tu']}–{m['den']} tuổi" + (" (sơ sinh)" if m.get("nhom") == "so_sinh" else "")
        if m["cach"] == "mien_phi":
            o = "ở chung miễn phí"
        elif m["cach"] == "phan_tram":
            o = f"{m['gia']:g}% giá phòng / đêm (trong số trẻ miễn phí thì không tính)"
        else:
            o = f"{_vnd(m['gia'])} đ / đêm (trong số trẻ miễn phí thì không tính)"
        an = "ăn sáng: cần khách sạn xác nhận" if m.get("an_sang") is None else ("ăn sáng miễn phí" if not m["an_sang"] else f"ăn sáng {_vnd(m['an_sang'])} đ / đêm")
        ra.append(f"{tuoi}: {o}; {an}.")
    return ra


def chinh_sach_tre_cong(k: KhachSanVtd) -> dict:
    """Mục «Chính sách trẻ em» trên cổng khách — dòng chữ kiểu Agoda. Chưa xác minh thì nói đúng như vậy."""
    nhan = k.cs_nhan_tre_em or "chua_xac_nhan"
    bang = [chuan_moc(m) for m in (k.cs_moc_tuoi or []) if m.get("cach") != "nguoi_lon"]
    dong = []
    if nhan == "chua_xac_nhan":
        dong.append("Cần khách sạn xác nhận.")
    elif nhan == "khong":
        dong.append("Khách sạn không nhận trẻ em.")
    else:
        dong.append("Nhận khách mọi lứa tuổi." if nhan == "moi_tuoi" else f"Nhận khách từ {k.cs_tre_tu_tuoi} tuổi.")
        dong += _dong_bang(bang)
        if bang:
            dong.append(f"Từ {max(m['den'] for m in bang) + 1} tuổi: tính như người lớn.")
        dong.append("Số trẻ ở chung miễn phí mỗi phòng: cần khách sạn xác nhận." if k.cs_so_tre_mien_phi is None
                    else f"Mỗi phòng tối đa {k.cs_so_tre_mien_phi} trẻ ở chung miễn phí (dùng giường có sẵn), tùy loại phòng.")
    if k.cs_phi_giuong_phu is not None:
        g = f"{float(k.cs_phi_giuong_phu):g}% giá phòng" if (k.cs_giuong_phu_kieu or "co_dinh") == "phan_tram" else f"{_vnd(k.cs_phi_giuong_phu)} đ"
        dong.append(f"Giường phụ {g} / đêm, tùy loại phòng.")
    if k.cs_noi:
        dong.append(f"Nôi / cũi: {k.cs_noi} — yêu cầu khi nhận phòng.")
    for t in (k.cs_tre_em, k.cs_giuong_phu):
        if t:
            dong.append(t)
    return {"nhan": nhan, "dong": dong, "moc": bang,
            "phi_giuong_phu": float(k.cs_phi_giuong_phu) if k.cs_phi_giuong_phu is not None else None}


# ══ CỔNG KHÁCH ═════════════════════════════════════════════════════════════════════════════════════
def _hien(db: Session, tinh: str = "") -> list[KhachSanVtd]:
    q = select(KhachSanVtd).where(KhachSanVtd.hien_cong.is_(True), KhachSanVtd.ngung.is_(False))
    if tinh:
        q = q.where(KhachSanVtd.tinh_thanh == tinh)
    return db.execute(q.order_by(KhachSanVtd.ten)).scalars().all()


def _gop_ct(pk: dict, dem: int) -> list[dict]:
    """Chi tiết phụ thu cả kỳ, gộp dòng trùng nhãn (nhiều phòng)."""
    g: dict[str, float] = {}
    for r in pk.get("phong", []):
        for c in r["chi_tiet"]:
            g[c["nhan"]] = g.get(c["nhan"], 0) + c["dem"] * dem
    return [{"nhan": n, "tien": int(round(v)), "dem": dem} for n, v in g.items()]


def _phong_ban_duoc(db: Session, kids: list[int], vao: date, ra: date, nl: int, te: int, so_phong: int,
                    tuoi: list[int] | None = None) -> dict[int, list[dict]]:
    """{khách sạn: [loại phòng + các gói BÁN ĐƯỢC cho kỳ ở]} — chỉ gói đã duyệt, đang bán, phủ đủ mọi đêm."""
    if not kids:
        return {}
    lps = db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id.in_(kids), LoaiPhongVtd.dang_ban.is_(True))
                     .order_by(LoaiPhongVtd.thu_tu, LoaiPhongVtd.id)).scalars().all()
    goi = _goi_cua(db, [x.id for x in lps])
    mua = _mua_cua(db, [g.id for v in goi.values() for g in v])
    from app.services import don_ks_vtd as KV   # KS-14: số phòng còn bán cho cả kỳ ở
    con = KV.con_phong(db, lps, vao, ra)
    ksd = {k.id: k for k in db.execute(select(KhachSanVtd).where(KhachSanVtd.id.in_(kids))).scalars()}
    dem = (ra - vao).days
    ra_: dict[int, list] = {}
    for x in lps:
        k = ksd[x.khach_san_id]
        sp = max(1, so_phong)
        tu = tuoi if te else []
        gs = []
        for g in goi.get(x.id, []):
            if g.trang_thai != "da_duyet" or not g.dang_ban:
                continue
            p = gia_luu(g, mua.get(g.id, []), vao, ra)
            if p is None:
                continue
            hh = han_huy(g, vao)
            pk = phan_khach(k, [(x, g, p["tong"] / max(1, dem))] * sp, nl, te, tu)   # KS-16k: theo bảng của từng gói
            gs.append({"id": g.id, "ten": g.ten, "bua_sang": g.bua_sang, "huy_truoc_ngay": g.huy_truoc_ngay,
                       "huy_han": hh.isoformat() if hh else None, "mien_phi_huy": g.huy_truoc_ngay is not None,
                       "huy_gio_chot": g.huy_gio_chot or "", "huy_mui_gio": MUI_GIO_HUY.get(g.huy_mui_gio or "", ""),
                       "cho_tra_sau": bool(g.cho_tra_sau),                                                # KS-17
                       **p, "con": con.get(x.id, 0),
                       "vua": pk["ok"], "ly_do": pk["ly_do"], "phu_thu_ky": int(round(pk.get("dem", 0) * dem)),
                       "phu_thu_ct": _gop_ct(pk, dem), "cho_xac_nhan": bool(pk.get("cho_xac_nhan"))})
        gs.sort(key=lambda o: o["tong"])
        pk0 = phan_khach(k, [(x, None, 0)] * sp, nl, te, tu) if not gs else None
        vua = any(g["vua"] for g in gs) if gs else pk0["ok"]
        ly_do = "" if vua else (next((g["ly_do"] for g in gs if g["ly_do"]), "") if gs else pk0["ly_do"])
        ra_.setdefault(x.khach_san_id, []).append({
            "id": x.id, "ten": x.ten, "dien_tich": x.dien_tich, "giuong": x.giuong, "mo_ta": x.mo_ta,
            "toi_da_nguoi_lon": x.toi_da_nguoi_lon, "toi_da_tre_em": x.toi_da_tre_em, "so_phong": x.so_phong,
            "tong_khach_toi_da": x.tong_khach_toi_da,                                                     # KS-17
            "vua": vua, "goi": gs, "con": con.get(x.id, 0),
            # KS-16j/16k: mô tả chi tiết, tiện nghi, sức chứa, giường phụ; phụ thu trẻ em / giường phụ ở từng gói
            "mo_ta_dai": x.mo_ta_dai or "", "tien_nghi": x.tien_nghi or [], "giuong_phu_toi_da": x.giuong_phu_toi_da,
            "suc_chua": x.suc_chua or x.toi_da_nguoi_lon, "khach_them_toi_da": x.khach_them_toi_da,
            "noi_cui": x.noi_cui, "ly_do": ly_do,
            # KS-19b: cho bộ lọc phòng — kiểu giường đọc từ ô giường, phòng gia đình theo sức chứa
            "giuong_kieu": sorted(_kieu_giuong(x.giuong or "")),
            "gia_dinh": (x.suc_chua or x.toi_da_nguoi_lon or 0) + (x.khach_them_toi_da or 0) >= 4})
    return ra_


DAT_24H_TOI_THIEU = 2          # KS-16p: chỉ số thật — dưới 2 đơn không hiện
CON_IT_TOI_DA = 3


def dat_24h(db: Session, ids: list[int], now: datetime | None = None) -> dict[int, int]:
    """KS-16p: số đơn ĐÃ TRẢ / ĐÃ XÁC NHẬN tạo trong 24 giờ qua theo khách sạn (số thật, không cộng thêm)."""
    if not ids:
        return {}
    from app.models.don_ks_vtd import DonKsVtd
    tu = (now or datetime.now()) - timedelta(hours=24)
    ra: dict[int, int] = {}
    for kid, n in db.execute(select(DonKsVtd.khach_san_id, func.count(DonKsVtd.id))
                             .where(DonKsVtd.khach_san_id.in_(ids), DonKsVtd.tao_luc >= tu,
                                    DonKsVtd.trang_thai.in_(["da_tra", "da_xac_nhan"]))
                             .group_by(DonKsVtd.khach_san_id)).all():
        ra[kid] = int(n)
    return ra


def _con_it(phong: list[dict]) -> int:
    con = [p["con"] for p in phong if p["vua"] and p["goi"] and p.get("con", 0) > 0]
    return min(con) if con and min(con) <= CON_IT_TOI_DA else 0


def _kieu_giuong(giuong: str) -> set[str]:
    """KS-16s: lọc «Phòng & giường» — đọc chữ Điều hành ghi ở ô giường (1 giường đôi / 2 giường đơn / king / twin…)."""
    t = _khong_dau(giuong or "")
    o = set()
    if any(x in t for x in ("doi", "double", "king", "queen")):
        o.add("doi")
    if "twin" in t or ("don" in t and any(x in t for x in ("2 ", "hai"))) or "2 giuong don" in t:
        o.add("don2")
    return o


def _loc_them(phong: list[dict], hom_nay: date | None = None) -> dict:
    """KS-16s: số liệu cho bộ lọc kiểu Agoda — tính từ phòng / gói đang bán được (số thật)."""
    from app.services import don_ks_vtd as KV
    hn = hom_nay or date.today()
    goi = [g for p in phong if p["vua"] and p.get("con", 1) > 0 for g in p["goi"] if g.get("vua", True)]
    giuong = set()
    for p in phong:
        giuong |= _kieu_giuong(p.get("giuong") or "")
    return {"giuong_tom": sorted(giuong),
            "gia_dinh": any((p.get("suc_chua") or p.get("toi_da_nguoi_lon") or 0) + (p.get("khach_them_toi_da") or 0) >= 4 for p in phong),
            "co_chi_phong": any(not g["bua_sang"] for g in goi),
            "co_uu_dai": any((g.get("niem_yet_dem") or 0) > (g.get("gia_dem") or 0) for g in goi),
            "co_tra_sau": any(g.get("cho_tra_sau", True) and g.get("huy_han")                                  # KS-17
                              and date.fromisoformat(g["huy_han"]) - timedelta(days=KV.TRA_SAU_TRUOC_HUY) > hn
                              for g in goi),
            "co_tra_ngay": bool(goi)}


def _goi_ban(phong: list[dict], so_phong: int = 1, dem: int = 1, hom_nay: date | None = None) -> list[dict]:
    """KS-19b (Chủ tịch duyệt bộ lọc v1.3, 05/11/2026): mỗi «gói bán được» là MỘT offer — đúng loại phòng, đúng gói,
    đủ giá mọi đêm, đủ sức chứa, và còn ≥ số phòng khách cần ở MỌI đêm. Bộ lọc trên cổng chỉ giữ khách sạn có ít nhất
    một offer thỏa ĐỒNG THỜI mọi điều kiện (không ghép bữa sáng của gói này với hủy miễn phí của gói khác).
    Giá lọc = tổng offer (gồm phụ thu bắt buộc, đã gồm 8% VAT) ÷ số đêm ÷ số phòng."""
    from app.services import don_ks_vtd as KV
    hn = hom_nay or date.today()
    sp, dem = max(1, so_phong), max(1, dem)
    ra = []
    # KS-20d (Chủ tịch 06/11/2026 «Cộng các loại phòng»): nhiều phòng thì ghép được nhiều loại phòng (bản v1.3 D2:
    # Deluxe + Family + Superior) — mỗi loại chỉ cần còn ≥ 1 phòng; đủ tổng số phòng do tim() / du_phong() xét.
    can = sp if sp == 1 else 1
    for p in phong:
        if not p["vua"] or p.get("con", 0) < can:
            continue
        tn = list(p.get("tien_nghi") or [])
        for g in p["goi"]:
            if g.get("vua") is False:
                continue
            tong = int(g["tong"]) * sp + int(g.get("phu_thu_ky") or 0)
            tra_sau = bool(g.get("cho_tra_sau", True) and g.get("huy_han")
                           and date.fromisoformat(g["huy_han"]) - timedelta(days=KV.TRA_SAU_TRUOC_HUY) > hn)
            ra.append({"lp": p["id"], "lp_ten": p["ten"], "goi": g["id"], "goi_ten": g["ten"],
                       "dem_gia": round(tong / dem / sp), "tong": tong, "niem_yet_dem": g.get("niem_yet_dem"),
                       "bua_sang": bool(g["bua_sang"]), "mien_phi_huy": bool(g["mien_phi_huy"]), "huy_han": g.get("huy_han"),
                       "tra_sau": tra_sau, "giuong": sorted(_kieu_giuong(p.get("giuong") or "")), "tien_nghi": tn,
                       "khong_hut": "Không hút thuốc" in tn,
                       "gia_dinh": (p.get("suc_chua") or p.get("toi_da_nguoi_lon") or 0) + (p.get("khach_them_toi_da") or 0) >= 4,
                       "con": p.get("con", 0)})
    ra.sort(key=lambda o: o["dem_gia"])
    return ra


def du_phong(goi_ban: list[dict], so_phong: int) -> bool:
    """KS-20d: tổng số phòng còn của các loại phòng có ít nhất một offer đủ cho số phòng khách cần."""
    con: dict[int, int] = {}
    for o in goi_ban:
        con[o["lp"]] = max(con.get(o["lp"], 0), int(o.get("con") or 0))
    return sum(con.values()) >= max(1, so_phong)


def _the_cong(k: KhachSanVtd, anh: list[AnhKhachSanVtd], phong: list[dict], dg: dict | None = None, dat: int = 0,
              so_phong: int = 1, dem: int = 1) -> dict:
    co_gia = [g for p in phong if p["vua"] for g in p["goi"] if g.get("vua", True)]
    goi = [g for p in phong if p["vua"] and p.get("con", 1) > 0 for g in p["goi"] if g.get("vua", True)]   # KS-16k: theo từng gói   # KS-14: bỏ loại phòng đã hết
    re_nhat = min(goi, key=lambda g: g["gia_dem"]) if goi else None
    return {"id": k.id, "ten": k.ten, "sao": k.sao, "loai": k.loai, "loai_ten": LOAI_CHO_O.get(k.loai, k.loai),
            "tinh_thanh": k.tinh_thanh, "khu_vuc": k.khu_vuc, "km_trung_tam": km_trung_tam(k), "gan": k.gan,
            "noi_bat": k.noi_bat, "tien_ich": [TIEN_ICH[t] for t in (k.tien_ich or []) if t in TIEN_ICH],
            "mien": THANH_PHO.get(k.tinh_thanh, ("",))[0],
            "anh": [_anh_out(a, True) for a in anh[:8]], "so_anh": len(anh),
            "gia_tu": ({"gia_dem": re_nhat["gia_dem"], "niem_yet_dem": re_nhat["niem_yet_dem"], "bua_sang": re_nhat["bua_sang"],
                        "mien_phi_huy": re_nhat["mien_phi_huy"]} if re_nhat else None),
            "co_mien_phi_huy": any(g["mien_phi_huy"] for g in goi), "co_bua_sang": any(g["bua_sang"] for g in goi),
            "thue_phi_pt": 0, "vat_pt": VAT_PT,                              # KS-19: giá đã gồm VAT
            "tien_nghi_phong": sorted({t for p in phong if p["vua"] and p.get("con", 1) > 0 and p["goi"] for t in (p.get("tien_nghi") or [])}),
            "goi_ban": _goi_ban(phong, so_phong, dem),                       # KS-19b: offer cho bộ lọc «cùng một gói»
            "phu_hop": [PHU_HOP[x] for x in (k.phu_hop or []) if x in PHU_HOP],
            "het_phong": bool(co_gia) and not goi,
            # KS-16l: chưa có gói đặt được → chưa book trên cổng; bấm vào mở trang ngoài ở tab mới
            "dat_ngay": any(p["goi"] for p in phong), "link_ngoai": LINK_KS_NGOAI,
            # KS-16p: chỉ số thật — đơn 24h (≥2 mới hiện) và «chỉ còn N phòng» (≤3, theo phòng rẻ nhất đặt được)
            "dat_24h": dat if dat >= DAT_24H_TOI_THIEU else 0,
            "con_it": _con_it(phong),
            "vi_do": k.vi_do, "kinh_do": k.kinh_do, **_loc_them(phong),   # KS-16s: bản đồ + bộ lọc kiểu Agoda
            # KS-15: điểm thang 10 của khách đã ở — chỉ bài đang hiện; dưới 3 bài diem_tb = None («Mới»).
            "danh_gia": dg or {"so_bai": 0, "diem_tb": None, "du": False, "nhan": "", "muc": {}}}


def tim(db: Session, tinh: str, vao, ra, nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
        hom_nay: date | None = None, tuoi=None) -> dict:
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    nl, te, sp = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0)), max(1, int(so_phong or 1))
    if sp > 9 or nl > 30 or te > 20:
        raise LoiKhachSan("Tối đa 9 phòng, 30 người lớn, 20 trẻ em một lần đặt")
    tat_ca = _hien(db)
    dem_tp: dict[str, int] = {}
    for k in tat_ca:
        dem_tp[k.tinh_thanh] = dem_tp.get(k.tinh_thanh, 0) + 1
    ks = [k for k in tat_ca if not tinh or k.tinh_thanh == tinh]
    anh = _anh_duyet(db, [k.id for k in ks])
    tu = doc_tuoi(te, tuoi)
    phong = _phong_ban_duoc(db, [k.id for k in ks], vao, ra, nl, te, sp, tu)
    from app.services import danh_gia_ks as DGK
    dg = DGK.tom_tat(db, [k.id for k in ks])
    d24 = dat_24h(db, [k.id for k in ks])
    chung = tt_chung(db)
    the = [{**_the_cong(k, anh.get(k.id, []), phong.get(k.id, []), dg.get(k.id), d24.get(k.id, 0), sp, (ra - vao).days),
            "mo_thanh_toan": mo_thanh_toan(db, k, chung)} for k in ks]
    # KS-19 (Chủ tịch 05/11/2026: «bỏ luôn» luồng gửi yêu cầu): chỉ hiện khách sạn còn đủ phòng đặt được cho ngày,
    # số khách và số phòng đã chọn — không còn thẻ «gửi yêu cầu / báo giá riêng».
    the = [o for o in the if o["gia_tu"] is not None and o["goi_ban"] and du_phong(o["goi_ban"], sp)]   # KS-19b / KS-20d
    dem_tp = {}
    for o in the:
        dem_tp[o["tinh_thanh"]] = dem_tp.get(o["tinh_thanh"], 0) + 1
    the.sort(key=lambda o: o["ten"])
    return {"khach_san": the, "tong": len(the), "dem": (ra - vao).days, "vao": vao.isoformat(), "ra": ra.isoformat(),
            "nguoi_lon": nl, "tre_em": te, "so_phong": sp, "tuoi": tu or [],
            "thanh_pho": [{"ten": t, "so": dem_tp[t]} for t in sorted(dem_tp, key=lambda t: -dem_tp[t])],
            "loai": LOAI_CHO_O}


def chi_tiet_cong(db: Session, kid: int, vao, ra, nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
                  hom_nay: date | None = None, tuoi=None) -> dict:
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    nl, te, sp = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0)), max(1, int(so_phong or 1))
    anh = _anh_duyet(db, [k.id]).get(k.id, [])
    tu = doc_tuoi(te, tuoi)
    phong = _phong_ban_duoc(db, [k.id], vao, ra, nl, te, sp, tu).get(k.id, [])
    from app.services import video_dich_vu as VD   # KS-16f
    video = VD.video_cong(db, "khach_san_vtd", [k.id]).get(k.id, [])
    for p in phong:
        p["anh"] = [_anh_out(a, True) for a in anh if a.loai_phong_id == p["id"]][:6]
        # KS-ANH (Chủ tịch 05/11/2026: «khách sạn nào chưa có ảnh phòng em lấy ảnh đại diện khách sạn»): loại phòng
        # chưa có ảnh riêng thì hiện ảnh đại diện (ảnh bìa — `_anh_duyet` xếp bìa lên đầu), gắn cờ để màn hình biết.
        p["anh_dai_dien"] = not p["anh"] and bool(anh)
        if p["anh_dai_dien"]:
            p["anh"] = [_anh_out(anh[0], True)]
        p["video"] = [v for v in video if v["loai_phong_id"] == p["id"]]
    from app.services import danh_gia_ks as DGK
    the = _the_cong(k, anh, phong, DGK.tom_tat(db, [k.id])[k.id], dat_24h(db, [k.id]).get(k.id, 0), sp, (ra - vao).days)
    return {**the, "dia_chi": k.dia_chi, "mo_ta": k.mo_ta, "gio_nhan": k.gio_nhan, "gio_tra": k.gio_tra,
            "chinh_sach": {"tre_em": k.cs_tre_em, "giuong_phu": k.cs_giuong_phu, "vat_nuoi": k.cs_vat_nuoi, "khac": k.cs_khac,
                           "tre": chinh_sach_tre_cong(k)},   # KS-16j
            "anh": [_anh_out(a, True) for a in anh], "nhom_anh": NHOM_ANH_KS,
            "video": video, "so_video": len(video),
            "phong": phong, "dem": (ra - vao).days, "vao": vao.isoformat(), "ra": ra.isoformat(),
            "nguoi_lon": nl, "tre_em": te, "so_phong": sp, "tuoi": tu or [], "the_bat": _the_bat(),
            "mo_thanh_toan": mo_thanh_toan(db, k)}   # KS-16s: chỉ trả được khi công tắc chung + của khách sạn đều bật


def _the_bat() -> bool:
    from app.services import sepay_pg as SP   # SP-1: nút trả thẻ chỉ hiện khi có cổng thẻ
    return SP.cong_the_bat()


def phu_thu_dong(k: KhachSanVtd, dong: list[dict], lps: dict[int, LoaiPhongVtd], goi: dict[int, GoiGiaVtd],
                 nl: int, te: int, tuoi, dem: int, chia: list[dict] | None = None, xep=None) -> list[dict]:
    """KS-16j/16k: phụ thu trẻ em / ăn sáng trẻ / giường phụ CẢ KỲ cho từng dòng (gói) — máy tự tính theo bảng giá trẻ em
    của gói → phòng → khách sạn. Dòng cần: loai_phong_id, goi_id, so, gia_mot (giá một phòng cả kỳ).
    Không đặt ngay được (cần xác nhận / vượt sức chứa) thì báo lý do để khách gửi yêu cầu."""
    dem = max(1, dem)
    don_vi, chi = [], []
    for i, x in enumerate(dong):
        for _ in range(int(x["so"])):
            don_vi.append((lps[x["loai_phong_id"]], goi.get(x.get("goi_id")), float(x["gia_mot"]) / dem))
            chi.append(i)
    te = max(0, int(te or 0))
    if chia:                                                          # KS-20b: khách khai từng phòng
        pk = phan_khach_chia(k, don_vi, chia, xep)
    else:
        pk = phan_khach(k, don_vi, max(1, int(nl or 1)), te, doc_tuoi(te, tuoi))
    if not pk["ok"]:
        raise LoiKhachSan(pk["ly_do"])
    ra = [{"phu_thu": 0.0, "ct": {}, "cho_xac_nhan": False, "khach": []} for _ in dong]
    for i, r in zip(chi, pk["phong"]):
        ra[i]["phu_thu"] += r["dem"] * dem
        ra[i]["cho_xac_nhan"] = ra[i]["cho_xac_nhan"] or r["cho_xac_nhan"]
        for c in r["chi_tiet"]:
            ra[i]["ct"][c["nhan"]] = ra[i]["ct"].get(c["nhan"], 0) + c["dem"] * dem
        if chia:
            ra[i]["khach"].append({"phong": r["nhom"] + 1, **chia[r["nhom"]]})
    return [{"phu_thu": int(round(x["phu_thu"])), "cho_xac_nhan": x["cho_xac_nhan"],
             "phu_thu_ct": [{"nhan": n, "tien": int(round(v)), "dem": dem} for n, v in x["ct"].items()],
             **({"khach": x["khach"]} if chia else {})} for x in ra]


def _han_tra_sau(dong: list[dict], hom_nay: date | None) -> str | None:
    from app.services import don_ks_vtd as KV   # KS-16p
    h = KV.han_tra_sau(dong, hom_nay or date.today())
    return h.isoformat() if h else None


def tinh_lua_chon(db: Session, kid: int, vao, ra, chon: list[dict], hom_nay: date | None = None,
                  nguoi_lon: int = 1, tre_em: int = 0, tuoi=None, chia=None, xep=None) -> dict:
    """Máy TÍNH LẠI phòng khách chọn từ giá đã duyệt. chon = [{goi_id, so}] — không nhận số tiền nào từ trình duyệt.
    KS-20b: chia = [{nl, te, tuoi}] khách khai từng phòng; xep = cách ghép phòng ↔ nhóm (máy trả lại để khách đổi)."""
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    chia = doc_chia(chia)
    if chia:
        nguoi_lon, tre_em, tuoi = tong_chia(chia)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    dong, lps, goi_d = [], {}, {}
    for c in chon or []:
        n = int(c.get("so") or 0)
        if n <= 0:
            continue
        g = db.get(GoiGiaVtd, int(c.get("goi_id") or 0))
        lp = db.get(LoaiPhongVtd, g.loai_phong_id) if g else None
        if g is None or lp is None or lp.khach_san_id != k.id or g.trang_thai != "da_duyet" or not g.dang_ban or not lp.dang_ban:
            raise LoiKhachSan("Gói giá đã thay đổi — tải lại trang để xem giá mới", 409)
        if n > lp.so_phong:
            raise LoiKhachSan(f"«{lp.ten}» chỉ còn tối đa {lp.so_phong} phòng")
        p = gia_luu(g, _mua_cua(db, [g.id]).get(g.id, []), vao, ra)
        if p is None:
            raise LoiKhachSan(f"«{lp.ten} · {g.ten}» chưa có giá cho các ngày này", 409)
        lps[lp.id] = lp
        goi_d[g.id] = g
        dong.append({"loai_phong_id": lp.id, "goi_id": g.id, "loai_phong": lp.ten, "goi": g.ten, "so": n, "tong": p["tong"] * n,
                     "gia_mot": p["tong"], "bua_sang": g.bua_sang,
                     "huy_han": (han_huy(g, vao).isoformat() if g.huy_truoc_ngay is not None else None)})
    dem = (ra - vao).days
    if dong:
        for x, pt in zip(dong, phu_thu_dong(k, dong, lps, goi_d, nguoi_lon, tre_em, tuoi, dem, chia, xep)):
            x.update(pt)
            x["tong"] += pt["phu_thu"]
    tien = sum(x["tong"] for x in dong)
    so = sum(x["so"] for x in dong)
    thue = 0                                                          # KS-19: giá đã gồm 8% VAT — không cộng thêm
    return {"dong": dong, "so_phong": so, "tien_phong": tien, "phu_thu": sum(x.get("phu_thu", 0) for x in dong),
            "thue_phi": thue, "tong": tien + thue, "vat_pt": VAT_PT, "vat_trong": vat_trong(tien + thue), "dem": dem, "cho_xac_nhan": any(x.get("cho_xac_nhan") for x in dong),
            # KS-16p: «Đặt giữ, trả sau» được không, và hạn trả
            "han_tra_sau": _han_tra_sau(dong, hom_nay), "mo_thanh_toan": mo_thanh_toan(db, k),   # KS-16s
            "huy_mien_phi_den": min((x["huy_han"] for x in dong if x.get("huy_han")), default=None) if dong and all(x.get("huy_han") for x in dong) else None,
            # KS-20b: phòng nào cho nhóm nào (theo thứ tự từng phòng đã chọn) — khách đổi rồi gửi lại `xep`
            "chia": chia or [], "xep": [kh["phong"] - 1 for x in dong for kh in x.get("khach", [])] if chia else []}


def gui_yeu_cau_giu(db: Session, tk, kid: int, d: dict, hom_nay: date | None = None):
    """Khách gửi yêu cầu giữ phòng — đi vào hàng chờ KS-11 của Điều hành (Điều hành báo giá / giữ phòng với khách sạn)."""
    from app.services import dat_phong_ota as DP
    vao, ra = _kiem_ky(d.get("ngay_nhan"), d.get("ngay_tra"), hom_nay)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    lc = None
    if d.get("chon"):
        try:
            lc = tinh_lua_chon(db, kid, vao, ra, d.get("chon") or [], hom_nay, d.get("nguoi_lon") or 1, d.get("tre_em") or 0,
                               d.get("tuoi_tre_em"), d.get("chia"), d.get("xep"))
        except LoiKhachSan as ex:   # KS-16j: trẻ em / giường phụ chưa xác nhận — vẫn gửi yêu cầu, Điều hành báo giá
            if getattr(ex, "status", 400) != 400:
                raise
            try:
                lc = tinh_lua_chon(db, kid, vao, ra, d.get("chon") or [], hom_nay, 1, 0, [])
                lc["ghi_chu_tre"] = str(ex)
            except LoiKhachSan:
                lc = None
    dong = [f"Khách sạn hợp tác VTD: {k.ma} · {k.ten} ({k.tinh_thanh})"]
    if lc and lc["dong"]:
        for x in lc["dong"]:
            dong.append(f"- {x['so']} × {x['loai_phong']} · {x['goi']}: {x['tong']:,.0f} đ / {lc['dem']} đêm".replace(",", "."))
        dong.append(f"Giá VTD lúc gửi (đã gồm {VAT_PT}% VAT): {lc['tong']:,.0f} đ".replace(",", "."))
        if lc.get("ghi_chu_tre"):
            dong.append("Chưa gồm phụ thu trẻ em / giường phụ: " + lc["ghi_chu_tre"])
    elif d.get("loai_phong"):
        dong.append(f"Loại phòng quan tâm: {str(d['loai_phong'])[:120]}")
    chia = doc_chia(d.get("chia"))                                    # KS-20b: khách khai từng phòng
    if chia:
        d = {**d, "so_phong": len(chia)}
        d["nguoi_lon"], d["tre_em"], _t = tong_chia(chia)
        dong.append("Chia phòng: " + "; ".join(f"Phòng {i} — {ta_nhom(c)}" for i, c in enumerate(chia, 1)))
    else:
        tu = doc_tuoi(int(d.get("tre_em") or 0), d.get("tuoi_tre_em"))
        if tu:
            dong.append("Tuổi trẻ em: " + ", ".join(str(t) for t in tu))
    if str(d.get("gio_den") or "").strip():                         # KS-16s
        dong.append("Giờ đến dự kiến: " + str(d["gio_den"]).strip()[:20])
    if str(d.get("yeu_cau_them") or "").strip():
        dong.append("Ghi chú của khách: " + str(d["yeu_cau_them"]).strip()[:1200])
    so_phong = (lc["so_phong"] if lc and lc["so_phong"] else int(d.get("so_phong") or 1))
    gui = {"noi_den": f"{k.ten} · {k.tinh_thanh}"[:160], "ngay_nhan": vao, "ngay_tra": ra, "so_phong": so_phong,
           "nguoi_lon": int(d.get("nguoi_lon") or 1), "tre_em": int(d.get("tre_em") or 0),
           "nguoi_nhan_phong": d.get("nguoi_nhan_phong") or "", "lien_he": d.get("lien_he") or "",
           "yeu_cau_them": "\n".join(dong)}
    try:
        don = DP.gui_yeu_cau(db, tk, gui)
    except DP.LoiOta as ex:
        raise LoiKhachSan(str(ex), getattr(ex, "status", 400))
    return DP.tom_tat_khach(don)


def tim_ten(ds: list[dict], q: str) -> list[dict]:
    k = _khong_dau(q.strip())
    return [o for o in ds if k in _khong_dau(" ".join((o["ten"], o["khu_vuc"], o["gan"])))] if k else ds
