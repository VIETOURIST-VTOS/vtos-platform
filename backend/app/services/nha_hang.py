"""KH-2 · Danh mục nhà hàng — phía VTOS (nhập, sửa, bật hiện cổng) và phía cổng khách (đọc).

Ai làm gì (Chủ tịch chốt 26/10/2026):
  · Điều hành (TP ĐH, NV ĐH) nhập và sửa nhà hàng, thực đơn.
  · TP / GĐ Kinh doanh bật «Hiện trên cổng». Người nhập không tự bật được.
  · Sửa NỘI DUNG BÁN của một nhà hàng đang hiện (tên, địa điểm, giá, thực đơn, điều kiện) → tự tắt,
    ghi lý do, chờ Kinh doanh bật lại. Sửa ghi chú nội bộ thì không tắt.
"""
import re
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.nha_hang import NhaHang, ThucDonNhaHang, HopDongNhaHang, NoiDungAmThuc, AM_THUC, LOAI_GOI

TOAN_QUYEN = ("chutich", "tgd")
VAI_NHAP = ("tp_dh", "nv_dh") + TOAN_QUYEN
# DT-2b (Chủ tịch 28/10/2026): bật «Hiện trên cổng» chuyển về TP ĐIỀU HÀNH (Kinh doanh không bật nữa).
# Vẫn hai người: người vừa nhập / sửa nhà hàng hay thực đơn không tự bật (trừ Chủ tịch, TGĐ).
VAI_BAT = ("tp_dh",) + TOAN_QUYEN
VAI_XEM = tuple(dict.fromkeys(VAI_NHAP + VAI_BAT + ("tp_kd", "gd_kd", "bks", "robot_ks", "nv_mkt", "ptgd_mkt", "ketoan")))
# AT-1 (Chủ tịch duyệt 28/10/2026)
# Chủ tịch 29/10/2026: Điều hành (NV, TP) cũng viết nội dung ẩm thực + tải ảnh, cùng Marketing.
VAI_NOI_DUNG = ("nv_mkt", "ptgd_mkt", "nv_dh", "tp_dh") + TOAN_QUYEN
VAI_HOP_DONG_XEM = tuple(dict.fromkeys(VAI_NHAP + ("ketoan", "bks")))   # tệp hợp đồng là riêng tư
LOAI_ND = {"mon": "Món ăn", "dac_san": "Đặc sản mang về", "danh_sach": "Danh sách gợi ý", "thanh_pho": "Giới thiệu thành phố",
           "bia": "Ảnh bìa trang"}
NHOM_MON = ("Món nước", "Bánh mì & bánh", "Bún – miến", "Cơm", "Món cuốn", "Ăn vặt", "Tráng miệng", "Món khác")
VAI_ANH_NH = tuple(dict.fromkeys(VAI_NHAP + VAI_NOI_DUNG))                 # ảnh nhà hàng: Điều hành hoặc Marketing
# Điểm đến ẩm thực theo THÀNH PHỐ LỚN (Chủ tịch chốt 28/10/2026: phân vùng theo thành phố, không nhập tỉnh).
# Tên hiển thị → (miền, các cách ghi khác trong tệp nguồn: tiếng Anh, không dấu, tên cũ).
THANH_PHO = {
    "Hà Nội": ("bac", ("hanoi",)), "Hạ Long": ("bac", ("halong", "ha long bay", "quang ninh")), "Hải Phòng": ("bac", ("haiphong",)),
    "Ninh Bình": ("bac", ("trang an", "tam coc")), "Sa Pa": ("bac", ("sapa", "lao cai")), "Hà Giang": ("bac", ("hagiang",)),
    "Mộc Châu": ("bac", ("moc chau",)), "Cao Bằng": ("bac", ()),
    "Thanh Hóa": ("trung", ("sam son",)), "Vinh": ("trung", ("nghe an",)), "Đồng Hới": ("trung", ("dong hoi", "quang binh", "phong nha")),
    "Huế": ("trung", ("hue city",)), "Đà Nẵng": ("trung", ("danang",)), "Hội An": ("trung", ("hoian", "quang nam")),
    "Quy Nhơn": ("trung", ("quy nhon", "qui nhon", "binh dinh")), "Tuy Hòa": ("trung", ("tuy hoa", "phu yen")),
    "Nha Trang": ("trung", ("nhatrang", "khanh hoa")), "Phan Rang": ("trung", ("ninh thuan", "phan rang thap cham")),
    "Pleiku": ("tay_nguyen", ("gia lai",)), "Buôn Ma Thuột": ("tay_nguyen", ("buon me thuot", "ban me thuot", "dak lak", "daklak")),
    "Kon Tum": ("tay_nguyen", ("kontum",)), "Đà Lạt": ("tay_nguyen", ("dalat", "lam dong")),
    "TP. Hồ Chí Minh": ("nam", ("ho chi minh city", "ho chi minh", "saigon", "sai gon", "hcmc", "tp hcm", "hcm")),
    "Vũng Tàu": ("nam", ("vung tau", "ba ria vung tau")), "Phan Thiết – Mũi Né": ("nam", ("phan thiet", "mui ne", "binh thuan")),
    "Cần Thơ": ("nam", ("cantho", "mekong delta", "mekong", "mien tay", "dong bang song cuu long")), "Châu Đốc": ("nam", ("chau doc", "an giang")), "Phú Quốc": ("nam", ("phu quoc island", "phuquoc")),
    "Bến Tre": ("nam", ()), "Trà Vinh": ("nam", ("travinh",)), "Cà Mau": ("nam", ()), "Côn Đảo": ("nam", ("con dao", "con son")),
    # KS-19n (Chủ tịch chọn «thêm theo thành phố» 06/11/2026): 15 điểm cho khách sạn 4–5★ đợt 34 tỉnh, thành còn thiếu
    # điểm đến. Vẫn theo thành phố lớn như lề 28/10; tên tỉnh cũ / không dấu để khớp tệp nguồn.
    "Bắc Ninh": ("bac", ("bac ninh",)), "Thái Nguyên": ("bac", ("thai nguyen",)), "Lạng Sơn": ("bac", ("lang son",)),
    "Hưng Yên": ("bac", ("hung yen", "yen my")), "Thái Bình": ("bac", ("thai binh",)),
    "Tam Đảo": ("bac", ("tam dao", "vinh phuc")), "Việt Trì": ("bac", ("viet tri", "phu tho")),
    "Sơn La": ("bac", ("son la",)), "Lai Châu": ("bac", ("lai chau",)), "Điện Biên Phủ": ("bac", ("dien bien phu", "dien bien")),
    "Hà Tĩnh": ("trung", ("ha tinh", "ky anh", "vung ang")), "Lý Sơn": ("trung", ("ly son",)),
    "Tây Ninh": ("nam", ("tay ninh",)), "Biên Hòa": ("nam", ("bien hoa", "dong nai")), "Mỹ Tho": ("nam", ("my tho", "tien giang"))}
MIEN = {"bac": "Miền Bắc", "trung": "Miền Trung", "tay_nguyen": "Tây Nguyên", "nam": "Miền Nam"}

TRUONG_NH = ("ten", "tinh_thanh", "khu_vuc", "am_thuc", "gio_phuc_vu", "tien_ich", "mo_ta")
TRUONG_TD = ("ten", "loai", "gia_nguoi_lon", "gia_tre_em", "so_khach_toi_thieu", "mo_ta", "dieu_kien", "dieu_kien_huy",
             "tu_ngay", "den_ngay", "dang_ban",
             # P1-03
             "gio_tu", "gio_den", "so_khach_toi_da", "tuoi_te_tu", "tuoi_te_den", "phu_thu", "han_phan_hoi_gio", "coc_moi_khach")
TRUONG_P103 = TRUONG_TD[-8:]
PHU_THU_THEO = {"khach": "mỗi khách", "ban": "mỗi bàn (đơn)"}


class LoiNhaHang(ValueError):
    pass


def _hom_nay() -> date:
    return date.today()


def _co(u: User, vai: tuple) -> bool:
    from app.services.vai_ke_thua import vai_va_cha
    return bool(set(vai_va_cha(u.role)) & set(vai))


def _tat(nh: NhaHang, ly_do: str) -> None:
    if nh.hien_cong:
        nh.hien_cong = False
        nh.tat_ly_do = ly_do[:200]


def _ma_moi(db: Session) -> str:
    n = db.execute(select(func.count(NhaHang.id))).scalar_one() + 1
    while db.execute(select(NhaHang.id).where(NhaHang.ma == f"NH-{n:03d}")).first():
        n += 1
    return f"NH-{n:03d}"


def luu_nha_hang(db: Session, u: User, d: dict, nha_hang_id: int | None = None, now: datetime | None = None) -> NhaHang:
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành nhập và sửa nhà hàng")
    now = now or datetime.now()
    ten = (d.get("ten") or "").strip()
    if not ten:
        raise LoiNhaHang("Ghi tên nhà hàng")
    if d.get("am_thuc") and d["am_thuc"] not in AM_THUC:
        raise LoiNhaHang("Loại ẩm thực không hợp lệ")
    if nha_hang_id:
        nh = db.get(NhaHang, nha_hang_id)
        if nh is None:
            raise LoiNhaHang("Không có nhà hàng này")
    else:
        nh = NhaHang(ma=_ma_moi(db), ten=ten, tao_boi=u.username, tao_luc=now)
        db.add(nh)
    doi = False
    truoc_dc = {"khu_vuc": nh.khu_vuc or "", "tinh_thanh": nh.tinh_thanh or ""}
    for k in TRUONG_NH:
        if k in d and d[k] is not None:
            v = str(d[k]).strip()
            if getattr(nh, k) != v:
                setattr(nh, k, v); doi = True
    if "ghi_chu_noi_bo" in d and d["ghi_chu_noi_bo"] is not None:
        nh.ghi_chu_noi_bo = str(d["ghi_chu_noi_bo"]).strip()
    # AT-2: đổi địa chỉ / thành phố thì ghim tự động cũ không còn đúng → xóa để nút «Lấy tọa độ» lấy lại.
    # Ghim tay (link Google Maps) giữ nguyên. Lưu hồ sơ KHÔNG gọi dịch vụ ngoài (lưu không phụ thuộc mạng).
    if nha_hang_id and nh.toa_do_nguon != "tay" and any(k in d and str(d.get(k) or "").strip() != truoc_dc.get(k, "")
                                                     for k in ("khu_vuc", "tinh_thanh")):
        nh.vi_do = nh.kinh_do = None
        nh.toa_do_nguon = ""
    if nha_hang_id and doi:
        _tat(nh, f"Thông tin nhà hàng vừa sửa bởi {u.username} — chờ Kinh doanh bật lại")
    nh.sua_boi, nh.sua_luc = u.username, now
    db.commit(); db.refresh(nh)
    return nh


def _ngay(v) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def luu_thuc_don(db: Session, u: User, nha_hang_id: int, d: dict, thuc_don_id: int | None = None, now: datetime | None = None) -> ThucDonNhaHang:
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành nhập và sửa thực đơn")
    now = now or datetime.now()
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    if thuc_don_id:
        td = db.get(ThucDonNhaHang, thuc_don_id)
        if td is None or td.nha_hang_id != nh.id:
            raise LoiNhaHang("Thực đơn không thuộc nhà hàng này")
    else:
        td = ThucDonNhaHang(nha_hang_id=nh.id, ten="")
        db.add(td)
    # Bản ghi mới chưa flush thì mọi cột còn là None (mặc định của SQLAlchemy chỉ áp lúc ghi) —
    # nên lấy mặc định NGHIỆP VỤ ở đây, không đọc từ đối tượng.
    goc = {"loai": "set", "so_khach_toi_thieu": 1, "dang_ban": True, "mo_ta": "", "dieu_kien": "", "dieu_kien_huy": ""} if not thuc_don_id else {}
    v = {k: d[k] if k in d and d[k] is not None else goc.get(k, getattr(td, k)) for k in TRUONG_TD}
    if "gia_tre_em" in d:
        v["gia_tre_em"] = d["gia_tre_em"]   # None có nghĩa: không bán vé trẻ em
    for k in TRUONG_P103:
        if k in d:
            v[k] = d[k]                       # P1-03: None / "" = Điều hành xóa ô đó (bỏ kiểm mục đó)
    v["ten"] = (v["ten"] or "").strip()
    if not v["ten"]:
        raise LoiNhaHang("Ghi tên gói / thực đơn")
    if v["loai"] not in LOAI_GOI:
        raise LoiNhaHang("Loại gói không hợp lệ")
    _chuan_p103(v)
    gl = v["gia_nguoi_lon"]
    if v["loai"] == "goi_mon" and v["coc_moi_khach"] and gl in (None, "", 0):
        v["gia_nguoi_lon"] = None             # P1-03: gọi món có cọc cố định — không bắt mức chi dự kiến
    elif gl in (None, "") or float(gl) <= 0:
        raise LoiNhaHang("Ghi giá bán người lớn (lớn hơn 0)")
    else:
        v["gia_nguoi_lon"] = float(gl)
    v["gia_tre_em"] = float(v["gia_tre_em"]) if v["gia_tre_em"] not in (None, "") else None
    if v["gia_tre_em"] is not None and v["gia_tre_em"] < 0:
        raise LoiNhaHang("Giá trẻ em không âm")
    v["so_khach_toi_thieu"] = max(int(v["so_khach_toi_thieu"] or 1), 1)
    v["tu_ngay"], v["den_ngay"] = _ngay(v["tu_ngay"]), _ngay(v["den_ngay"])
    if v["tu_ngay"] and v["den_ngay"] and v["den_ngay"] < v["tu_ngay"]:
        raise LoiNhaHang("Ngày kết thúc áp dụng phải sau ngày bắt đầu")
    v["dang_ban"] = bool(v["dang_ban"])
    for k in ("mo_ta", "dieu_kien", "dieu_kien_huy"):
        v[k] = (v[k] or "").strip()
    doi = bool(thuc_don_id) and any(getattr(td, k) != v[k] for k in TRUONG_TD) or not thuc_don_id
    for k in TRUONG_TD:
        setattr(td, k, v[k])
    td.sua_boi, td.sua_luc = u.username, now
    if doi:
        _tat(nh, f"Thực đơn «{td.ten}» vừa sửa bởi {u.username} — chờ Kinh doanh bật lại")
    db.commit(); db.refresh(td)
    return td


def _so_nguyen(x, ten: str, tu: int, den: int) -> int | None:
    if x in (None, ""):
        return None
    try:
        n = int(x)
    except (TypeError, ValueError):
        raise LoiNhaHang(f"{ten}: ghi số")
    if not tu <= n <= den:
        raise LoiNhaHang(f"{ten}: từ {tu} đến {den}")
    return n


def _chuan_p103(v: dict) -> None:
    """P1-03: kiểm và chuẩn hóa các ô điều kiện có cấu trúc của gói. Ô trống = không kiểm mục đó."""
    for k in ("gio_tu", "gio_den"):
        v[k] = (v.get(k) or "").strip()
        if v[k] and not GIO_RE.match(v[k]):
            raise LoiNhaHang("Khung giờ ghi dạng HH:MM")
    if bool(v["gio_tu"]) != bool(v["gio_den"]):
        raise LoiNhaHang("Khung giờ: ghi đủ giờ bắt đầu và giờ kết thúc, hoặc để trống cả hai")
    if v["gio_tu"] and v["gio_den"] <= v["gio_tu"]:
        raise LoiNhaHang("Khung giờ: giờ kết thúc phải sau giờ bắt đầu")
    v["so_khach_toi_da"] = _so_nguyen(v.get("so_khach_toi_da"), "Số khách tối đa", 1, 1000)
    if v["so_khach_toi_da"] and v["so_khach_toi_da"] < max(int(v.get("so_khach_toi_thieu") or 1), 1):
        raise LoiNhaHang("Số khách tối đa phải từ số khách tối thiểu trở lên")
    v["tuoi_te_tu"] = _so_nguyen(v.get("tuoi_te_tu"), "Tuổi trẻ em từ", 0, 17)
    v["tuoi_te_den"] = _so_nguyen(v.get("tuoi_te_den"), "Tuổi trẻ em đến", 0, 17)
    if (v["tuoi_te_tu"] is None) != (v["tuoi_te_den"] is None):
        raise LoiNhaHang("Tuổi tính giá trẻ em: ghi đủ «từ» và «đến», hoặc để trống cả hai")
    if v["tuoi_te_tu"] is not None and v["tuoi_te_den"] < v["tuoi_te_tu"]:
        raise LoiNhaHang("Tuổi tính giá trẻ em: «đến» phải từ «từ» trở lên")
    v["han_phan_hoi_gio"] = _so_nguyen(v.get("han_phan_hoi_gio"), "Hạn nhà hàng trả lời (giờ)", 1, 72)
    c = v.get("coc_moi_khach")
    v["coc_moi_khach"] = None if c in (None, "", 0) else float(c)
    if v["coc_moi_khach"] is not None:
        if v["loai"] != "goi_mon":
            raise LoiNhaHang("Cọc mỗi khách chỉ dùng cho gói gọi món")
        if v["coc_moi_khach"] < 0:
            raise LoiNhaHang("Cọc mỗi khách không âm")
    goi_mon = v["loai"] == "goi_mon"
    ds = []
    for i, p in enumerate(v.get("phu_thu") or []):
        ten = str((p or {}).get("ten") or "").strip()[:80]
        if not ten:
            raise LoiNhaHang(f"Phụ thu dòng {i + 1}: ghi tên")
        try:
            tien = float(p.get("so_tien"))
        except (TypeError, ValueError):
            raise LoiNhaHang(f"Phụ thu «{ten}»: ghi số tiền")
        if tien <= 0:
            raise LoiNhaHang(f"Phụ thu «{ten}»: số tiền lớn hơn 0")
        theo = p.get("theo") or "khach"
        if theo not in PHU_THU_THEO:
            raise LoiNhaHang(f"Phụ thu «{ten}»: tính theo khách hoặc theo bàn")
        if goi_mon and theo == "khach":
            raise LoiNhaHang(f"Phụ thu «{ten}»: gói gọi món chỉ có phụ thu theo bàn")
        try:
            tu, den = _ngay(p.get("tu_ngay")), _ngay(p.get("den_ngay"))
        except ValueError:
            raise LoiNhaHang(f"Phụ thu «{ten}»: ngày ghi dạng YYYY-MM-DD")
        if tu and den and den < tu:
            raise LoiNhaHang(f"Phụ thu «{ten}»: ngày kết thúc phải sau ngày bắt đầu")
        ds.append({"ten": ten, "so_tien": int(round(tien)), "theo": theo, "tu_ngay": tu.isoformat() if tu else None,
                   "den_ngay": den.isoformat() if den else None, "tu_chon": bool(p.get("tu_chon"))})
    if len(ds) > 10:
        raise LoiNhaHang("Tối đa 10 dòng phụ thu")
    v["phu_thu"] = ds or None


def _con_ban(td: ThucDonNhaHang, hom_nay: date) -> bool:
    return td.dang_ban and (td.den_ngay is None or td.den_ngay >= hom_nay)


def bat_hien(db: Session, u: User, nha_hang_id: int, bat: bool, now: datetime | None = None) -> NhaHang:
    if not _co(u, VAI_BAT):
        raise LoiNhaHang("Chỉ TP Điều hành bật hoặc tắt hiện trên cổng")
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    if bat:
        if nh.ngung:
            raise LoiNhaHang("Nhà hàng đã ngừng hợp tác")
        # AT-1: «Hiện trên cổng» = hiện GIỚI THIỆU trên web VTD; không còn đòi thực đơn. Mở đặt bàn do máy tính
        # từ điều kiện hợp đồng (dieu_kien_mo_dat), không có nút bật tay.
        tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == nh.id)).scalars().all()
        if u.role not in TOAN_QUYEN and u.username in ({nh.tao_boi, nh.sua_boi} | {t.sua_boi for t in tds}) - {""}:
            raise LoiNhaHang("Người nhập / sửa nhà hàng hoặc thực đơn không tự bật — nhờ người thứ hai (TP Điều hành khác, Chủ tịch, TGĐ)")
        nh.hien_cong, nh.hien_boi, nh.hien_luc, nh.tat_ly_do = True, u.username, now or datetime.now(), ""
    else:
        nh.hien_cong, nh.tat_ly_do = False, f"Tắt bởi {u.username}"
    db.commit(); db.refresh(nh)
    return nh


# ══ AT-2 (Chủ tịch duyệt bản xem thử 01/11/2026): bản đồ + công tắc mở thanh toán — cùng cách KS-16s ══════════
# Tọa độ: máy lấy từ địa chỉ qua OpenStreetMap (dùng chung hàm của khách sạn), Điều hành dán link Google Maps để
# sửa ghim lệch (nguồn «tay», máy không ghi đè). Thanh toán: công tắc chung + từng nhà hàng, CẢ HAI bật mới trả được.
LAY_TOA_DO = None            # phép thử gán hàm giả; None = dùng hàm của khách sạn (khach_san_vtd.LAY_TOA_DO)
KHOA_TT_NH = "mo_thanh_toan_nha_hang"


def _ks_mod():
    from app.services import khach_san_vtd as KS
    return KS


def _lay(q: str):
    return (LAY_TOA_DO or _ks_mod().LAY_TOA_DO)(q)


def doc_link_ggmap(link: str) -> tuple[float, float]:
    KS = _ks_mod()
    try:
        return KS.doc_link_ggmap(link)
    except KS.LoiKhachSan as ex:
        raise LoiNhaHang(str(ex).replace("khách sạn", "nhà hàng"))


def _cau_tim_nh(n: NhaHang) -> list[str]:
    tp = (n.tinh_thanh or "").replace("TP. ", "")
    ds = []
    if n.khu_vuc:
        kv = n.khu_vuc.strip()
        ds.append(", ".join([kv] + [x for x in (tp, "Việt Nam") if x and _khong_dau(x) not in _khong_dau(kv)]))
    ds.append(", ".join(x for x in (n.ten, tp, "Việt Nam") if x))
    return list(dict.fromkeys(ds))


def _tu_lay_toa_do_nh(n: NhaHang, nghi: float = 0) -> bool:
    import time
    KS = _ks_mod()
    for i, q in enumerate(_cau_tim_nh(n)):
        if i and nghi:
            time.sleep(nghi)
        try:
            kq = _lay(q)
        except Exception:   # noqa: BLE001 — mạng / dịch vụ ngoài lỗi: để trống, lần sau lấy lại
            return False
        if kq and KS._trong_vn(*kq):
            n.vi_do, n.kinh_do, n.toa_do_nguon = kq[0], kq[1], "tu_dong"
            return True
    n.toa_do_nguon = "khong_thay"
    return False


def dat_ghim(db: Session, u: User, nha_hang_id: int, link: str, now: datetime | None = None) -> NhaHang:
    """Điều hành dán link Google Maps để sửa ghim. Link trống = bỏ ghim tay, để máy lấy lại theo địa chỉ.
    Không tắt hiện nhà hàng (ghim không đổi nội dung khách đọc)."""
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành sửa ghim bản đồ")
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    from app.services import rules as R
    if (link or "").strip():
        lat, lng = doc_link_ggmap(link)
        nh.vi_do, nh.kinh_do, nh.toa_do_nguon = lat, lng, "tay"
        R.audit(db, u.username, u.role, "nh_toa_do_tay", f"nha_hang:{nh.ma}", after={"vi_do": lat, "kinh_do": lng})
    else:
        nh.vi_do = nh.kinh_do = None
        nh.toa_do_nguon = ""
        R.audit(db, u.username, u.role, "nh_toa_do_bo_tay", f"nha_hang:{nh.ma}")
    nh.sua_boi, nh.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(nh)
    return nh


def lay_toa_do_loat(db: Session, u: User, toi_da: int | None = None, nghi: float | None = None) -> dict:
    """Nút «Lấy tọa độ cho tất cả nhà hàng»: nơi chưa có tọa độ (bỏ qua ghim tay), tối đa 60 mỗi lần, 1 lượt / giây."""
    import time
    KS = _ks_mod()
    toi_da = KS.LOAT_TOI_DA if toi_da is None else toi_da
    nghi = KS.LOAT_NGHI_GIAY if nghi is None else nghi
    if not _co(u, VAI_BAT):
        raise LoiNhaHang("Chỉ TP Điều hành / Chủ tịch / TGĐ chạy lấy tọa độ hàng loạt")
    ds = db.execute(select(NhaHang).where(NhaHang.vi_do.is_(None), NhaHang.toa_do_nguon != "tay",
                                          NhaHang.ngung.is_(False)).order_by(NhaHang.hien_cong.desc(), NhaHang.ma)).scalars().all()
    co, khong = [], []
    for i, n in enumerate(ds[:toi_da]):
        if i and nghi:
            time.sleep(nghi)
        (co if _tu_lay_toa_do_nh(n, nghi) else khong).append(n.ma)
    from app.services import rules as R
    R.audit(db, u.username, u.role, "nh_toa_do_loat", "nha_hang:loat", after={"co": co, "khong_thay": khong})
    db.commit()
    return {"co": len(co), "khong_thay": khong, "con_lai": max(0, len(ds) - toi_da)}


def tt_chung_nh(db: Session) -> bool:
    from app.models.khach_san_vtd import CaiDatKsVtd
    r = db.get(CaiDatKsVtd, KHOA_TT_NH)
    return bool(r and r.gia_tri == "1")


def mo_thanh_toan_nh(db: Session, n: NhaHang, chung: bool | None = None) -> bool:
    return bool(n.mo_thanh_toan) and (tt_chung_nh(db) if chung is None else chung)


def bat_tt_chung_nh(db: Session, u: User, bat: bool, now: datetime | None = None) -> bool:
    from app.models.khach_san_vtd import CaiDatKsVtd
    from app.services import rules as R
    if not _co(u, VAI_BAT):
        raise LoiNhaHang("Chỉ TP Điều hành / Chủ tịch / TGĐ mở / đóng thanh toán trực tuyến nhà hàng")
    r = db.get(CaiDatKsVtd, KHOA_TT_NH)
    if r is None:
        r = CaiDatKsVtd(khoa=KHOA_TT_NH)
        db.add(r)
    r.gia_tri, r.sua_boi, r.sua_luc = ("1" if bat else "0"), u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "nh_tt_chung_mo" if bat else "nh_tt_chung_dong", "nha_hang:chung")
    db.commit()
    return bool(bat)


def bat_tt_nh(db: Session, u: User, nha_hang_id: int, bat: bool) -> NhaHang:
    from app.services import rules as R
    if not _co(u, VAI_BAT):
        raise LoiNhaHang("Chỉ TP Điều hành / Chủ tịch / TGĐ mở / đóng thanh toán của nhà hàng")
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    nh.mo_thanh_toan = bool(bat)
    R.audit(db, u.username, u.role, "nh_tt_mo" if bat else "nh_tt_dong", f"nha_hang:{nh.ma}")
    db.commit(); db.refresh(nh)
    return nh


def ngung(db: Session, u: User, nha_hang_id: int, ngung_: bool) -> NhaHang:
    if not _co(u, VAI_BAT + ("tp_dh",)):
        raise LoiNhaHang("Chỉ TP Điều hành / Chủ tịch / TGĐ đánh dấu ngừng hợp tác")
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    nh.ngung = bool(ngung_)
    if nh.ngung:
        _tat(nh, "Ngừng hợp tác")
    db.commit(); db.refresh(nh)
    return nh


def _td_out(t: ThucDonNhaHang, noi_bo: bool) -> dict:
    o = {"id": t.id, "ten": t.ten, "loai": t.loai, "loai_ten": LOAI_GOI.get(t.loai, t.loai),
         "gia_nguoi_lon": int(t.gia_nguoi_lon or 0), "gia_tre_em": int(t.gia_tre_em) if t.gia_tre_em is not None else None,
         "so_khach_toi_thieu": t.so_khach_toi_thieu, "mo_ta": t.mo_ta, "dieu_kien": t.dieu_kien, "dieu_kien_huy": t.dieu_kien_huy,
         "tu_ngay": t.tu_ngay.isoformat() if t.tu_ngay else None, "den_ngay": t.den_ngay.isoformat() if t.den_ngay else None,
         # P1-03
         "gio_tu": t.gio_tu or "", "gio_den": t.gio_den or "", "so_khach_toi_da": t.so_khach_toi_da,
         "tuoi_te_tu": t.tuoi_te_tu, "tuoi_te_den": t.tuoi_te_den, "phu_thu": t.phu_thu or [],
         "han_phan_hoi_gio": t.han_phan_hoi_gio, "coc_moi_khach": int(t.coc_moi_khach) if t.coc_moi_khach else None}
    if noi_bo:
        o.update({"dang_ban": t.dang_ban, "sua_boi": t.sua_boi})
    return o


def danh_sach_vtos(db: Session) -> dict:
    nhs = db.execute(select(NhaHang).order_by(NhaHang.ngung, NhaHang.ten)).scalars().all()
    tds = db.execute(select(ThucDonNhaHang).order_by(ThucDonNhaHang.id)).scalars().all()
    hds: dict = {}
    for h in db.execute(select(HopDongNhaHang).order_by(HopDongNhaHang.id.desc())).scalars():
        hds.setdefault(h.nha_hang_id, []).append(h)
    hn = _hom_nay()
    ht = hoan_thien_anh(db)
    ra = []
    for n in nhs:
        mine = [t for t in tds if t.nha_hang_id == n.id]
        ra.append({"id": n.id, "ma": n.ma, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "khu_vuc": n.khu_vuc, "am_thuc": n.am_thuc,
                   "gio_phuc_vu": n.gio_phuc_vu, "tien_ich": n.tien_ich, "mo_ta": n.mo_ta, "ghi_chu_noi_bo": n.ghi_chu_noi_bo,
                   "hien_cong": n.hien_cong, "hien_boi": n.hien_boi, "hien_luc": n.hien_luc.isoformat(timespec="minutes") if n.hien_luc else None,
                   "tat_ly_do": n.tat_ly_do, "ngung": n.ngung, "tao_boi": n.tao_boi,
                   "thuc_don": [_td_out(t, True) for t in mine], "so_dang_ban": sum(1 for t in mine if _con_ban(t, hn)),
                   # AT-1
                   "nguon": n.nguon, "nguon_ref": n.nguon_ref, "dia_danh_nguon": n.dia_danh_nguon, "mon_noi_bat": n.mon_noi_bat,
                   "lien_he_xac_minh": n.lien_he_xac_minh, "xac_minh_boi": n.xac_minh_boi, "supplier_id": n.supplier_id,
                   "dieu_kien": dieu_kien_mo_dat(db, n, mine, hn), "mo_dat": mo_dat(db, n, mine, hn),
                   "vi_do": n.vi_do, "kinh_do": n.kinh_do, "toa_do_nguon": n.toa_do_nguon or "",   # AT-2
                   "mo_thanh_toan": bool(n.mo_thanh_toan),
                   "hop_dong": [_hd_out(h) for h in hds.get(n.id, [])], "anh_id": n.anh_id, "anh_nguon": n.anh_nguon,
                   "anh_ht": ht.get(n.id, {"da_duyet": 0, "cho_duyet": 0, "nhap": 0, "an": 0, "co_bia": False, "mon": 0, "td": 0, "nd_cho": 0})})
    return {"nha_hang": ra, "am_thuc": list(AM_THUC), "loai_goi": LOAI_GOI, "noi_dung": ds_noi_dung(db), "loai_nd": LOAI_ND,
            "nhom_anh": NHOM_ANH, "can_cu_anh": CAN_CU_ANH, "so_anh_cho_duyet": sum(o["cho_duyet"] + o.get("nd_cho", 0) for o in ht.values()),
            "thanh_pho": [{"ten": t, "mien": MIEN[m]} for t, (m, _k) in THANH_PHO.items()], "nhom_mon": list(NHOM_MON),
            "tt_chung": tt_chung_nh(db), "chua_toa_do": sum(1 for n in nhs if n.vi_do is None and not n.ngung)}   # AT-2


# ── phía cổng khách ─────────────────────────────────────────────────────────────────────────────

def hop_dong_hien_hanh(db: Session, n: NhaHang, ngay: date | None = None) -> HopDongNhaHang | None:
    ngay = ngay or _hom_nay()
    for h in db.execute(select(HopDongNhaHang).where(HopDongNhaHang.nha_hang_id == n.id, HopDongNhaHang.con_dung.is_(True))
                        .order_by(HopDongNhaHang.id.desc())).scalars():
        if h.tu_ngay <= ngay and (h.den_ngay is None or ngay <= h.den_ngay):
            return h
    return None


def dieu_kien_mo_dat(db: Session, n: NhaHang, tds: list[ThucDonNhaHang] | None = None, ngay: date | None = None) -> list[dict]:
    """Năm điều kiện mở đặt bàn (AT-1). Tính tại máy chủ mỗi lần đọc — không có cờ bật tay."""
    ngay = ngay or _hom_nay()
    if tds is None:
        tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == n.id)).scalars().all()
    h = hop_dong_hien_hanh(db, n, ngay)
    return [{"ma": "hop_dong", "ten": "Đã ký hợp đồng, có tệp, còn hiệu lực", "ok": h is not None},
            {"ma": "ncc", "ten": "Đã gắn nhà cung cấp (cổng nhà hàng)", "ok": n.supplier_id is not None},
            {"ma": "thuc_don", "ten": "Có ít nhất 1 thực đơn đang bán", "ok": any(_con_ban(t, ngay) for t in tds)},
            {"ma": "lien_he", "ten": "Liên hệ đã xác minh", "ok": bool(n.lien_he_xac_minh)},
            {"ma": "hoa_hong", "ten": "Hoa hồng đã khai trong hợp đồng",
             "ok": h is not None and (h.hoa_hong_bps is not None or h.hoa_hong_co_dinh is not None)}]


def mo_dat(db: Session, n: NhaHang, tds: list[ThucDonNhaHang] | None = None, ngay: date | None = None) -> bool:
    return bool(n.hien_cong and not n.ngung and all(x["ok"] for x in dieu_kien_mo_dat(db, n, tds, ngay)))


def _nh_cong(db: Session, n: NhaHang, tds: list[ThucDonNhaHang], hn: date, anh: list | None = None,
             du_album: bool = False) -> dict:
    """anh: ảnh ĐÃ DUYỆT của nhà hàng (album_cong). Danh sách chỉ cần ảnh bìa; trang chi tiết lấy cả album."""
    dat = mo_dat(db, n, tds, hn)
    if anh is None:
        anh = album_cong(db, [n.id]).get(n.id, [])
    bia = _anh_cong_out(anh[0]) if anh else None
    ban = [t for t in tds if _con_ban(t, hn)] if dat else []
    return {"id": n.id, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "khu_vuc": n.khu_vuc, "am_thuc": n.am_thuc,
            "gio_phuc_vu": n.gio_phuc_vu, "tien_ich": n.tien_ich, "mo_ta": n.mo_ta, "mon_noi_bat": n.mon_noi_bat,
            "dia_danh_nguon": n.dia_danh_nguon, "mo_dat": dat, "da_xac_minh": bool(n.lien_he_xac_minh),
            "mien": THANH_PHO.get(n.tinh_thanh, ("",))[0],      # AT-2d: màu ô khi chưa có ảnh
            **_pl_cong(n),                                       # PL-1: nhãn đặc sản, bậc ĐÃ CHỐT, hạng Michelin
            # AT-2a: ảnh chỉ từ album đã duyệt (ảnh đơn cũ nha_hang.anh_id không ra cổng nữa)
            "anh": bia["hien"] if bia else None, "anh_nho": bia["nho"] if bia else None,
            "anh_alt": bia["alt"] if bia else "", "anh_nguon": bia["credit"] if bia else "", "so_anh": len(anh),
            **({"album": [_anh_cong_out(x) for x in anh], "mon": mon_cong(db, n.id), "thuc_don_nh": thuc_don_cong(db, n.id),
                "danh_gia": _dg_cong(db, n.id), **_video_cong(db, n.id)}
               if du_album else {}),
            "gia_tu": min(int(t.gia_nguoi_lon or 0) for t in ban) if ban else None, "thuc_don": [_td_out(t, False) for t in ban],
            # AT-2: bản đồ, công tắc thanh toán (chỉ nơi mở đặt), ảnh cho băng chuyền thẻ, nhãn «Phù hợp» từ dữ liệu thật
            "vi_do": n.vi_do, "kinh_do": n.kinh_do, "mo_thanh_toan": bool(dat) and mo_thanh_toan_nh(db, n),
            "anh_ds": [_anh_cong_out(x)["nho"] for x in anh[:6]],
            "phong_rieng": any(x.nhom == "phong_rieng" for x in anh) or "phòng riêng" in (n.tien_ich or "").lower()
                           or any(t.loai == "tiec" for t in ban),
            "gia_dinh": any(t.gia_tre_em is not None for t in ban) or "trẻ em" in (n.tien_ich or "").lower(),
            "tiec": any(t.loai == "tiec" or (t.so_khach_toi_thieu or 1) >= 10 for t in ban),
            "goi_mon": any(t.loai == "goi_mon" for t in ban)}


def _video_cong(db: Session, nid: int) -> dict:
    """KS-16f — video đang hiện của nhà hàng (giới thiệu trước)."""
    from app.services import video_dich_vu as VD
    v = VD.video_cong(db, "nha_hang", [nid]).get(nid, [])
    return {"video": v, "so_video": len(v)}


def _pl_cong(n: NhaHang) -> dict:
    from app.services import phan_loai_nh as PL
    return {"dac_san": PL.dac_san(n), "bac": n.bac or "", "bac_ten": PL.BAC.get(n.bac or "", ""),
            "michelin": PL.nhan_michelin(n), "la_michelin": PL.la_michelin(n)}


def _dg_cong(db: Session, nid: int) -> dict:
    from app.services import danh_gia_nh as DG
    return DG.cong(db, nid)


def _khong_dau(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _duong_anh(aid: int | None) -> str | None:
    return f"/api/v1/am-thuc/anh/{aid}" if aid else None


def _nh_hien(db: Session, hn: date) -> list[dict]:
    nhs = db.execute(select(NhaHang).where(NhaHang.hien_cong.is_(True), NhaHang.ngung.is_(False)).order_by(NhaHang.ten)).scalars().all()
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id.in_([n.id for n in nhs]))).scalars().all() if nhs else []
    al = album_cong(db, [n.id for n in nhs])
    return [(n, _nh_cong(db, n, [t for t in tds if t.nha_hang_id == n.id], hn, al.get(n.id, []))) for n in nhs]


def danh_sach_cong(db: Session, tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0, q: str = "", chi_dat: bool = False,
                   trang: int = 1, so: int = 24, loai: str = "", bac: str = "", toi_da: int = 60) -> dict:
    """Trang Khám phá ẩm thực: mọi nhà hàng đang hiện giới thiệu (chỉ nơi mở đặt mới có thực đơn, giá), thành phố,
    nội dung Marketing đã bật. Nhà hàng xếp: nơi đặt được qua Vietourist lên trước, rồi theo tên."""
    hn = _hom_nay()
    tat_ca = _nh_hien(db, hn)
    k = _khong_dau(q.strip()) if q.strip() else ""
    ra = []
    for n, o in tat_ca:
        if tinh and n.tinh_thanh != tinh:
            continue
        if am_thuc and n.am_thuc != am_thuc:
            continue
        if k and k not in _khong_dau(" ".join((n.ten, n.mon_noi_bat, n.tinh_thanh, n.khu_vuc, n.dia_danh_nguon))):
            continue
        if chi_dat and not o["mo_dat"]:
            continue
        if gia_toi_da and (o["gia_tu"] is None or o["gia_tu"] > gia_toi_da):
            continue
        if loai == "dac_san" and not o["dac_san"]:              # PL-1: bộ lọc loại / bậc (chỉ bậc đã chốt)
            continue
        if loai == "michelin" and not o["la_michelin"]:
            continue
        if bac and o["bac"] != bac:
            continue
        ra.append(o)
    # AT-2c (Chủ tịch 29/10/2026): nơi dưới 50% hoàn thiện xếp xuống cuối, không ẩn.
    dm = diem_hoan_thien(db, [o["id"] for o in ra])
    from app.services import danh_gia_nh as DG          # AT-3: sao trên thẻ (dưới 3 bài: «Mới — chưa đủ đánh giá»)
    sao = DG.tom_tat(db, [o["id"] for o in ra])
    for o in ra:
        t = sao.get(o["id"], {})
        o["sao"] = {"so_bai": t.get("so_bai", 0), "diem_tb": t.get("diem_tb")}
    ra.sort(key=lambda o: (not o["mo_dat"], dm.get(o["id"], {"diem": 0})["diem"] < NGUONG_THIEU, o["ten"]))
    trang, so = max(1, int(trang or 1)), max(1, min(int(so or 24), toi_da))
    dem: dict = {}
    for n, _o in tat_ca:
        if n.tinh_thanh:
            dem[n.tinh_thanh] = dem.get(n.tinh_thanh, 0) + 1
    nd = ds_noi_dung(db, cong=True, nha_hang={n.id: o for n, o in tat_ca})
    gioi = {x["ten"]: x for x in nd if x["loai"] == "thanh_pho"}
    tp = [{"ten": t, "mien": m, "mien_ten": MIEN[m], "so_nha_hang": dem.get(t, 0),
           "tom_tat": gioi.get(t, {}).get("tom_tat", ""), "anh": gioi.get(t, {}).get("anh")}
          for t, (m, _k) in THANH_PHO.items()]
    # PL-1: mục riêng «Đặc sản địa phương» — nơi có ảnh lên trước, rồi nơi đặt được, rồi theo tên
    ds_ds = sorted([o for _n, o in tat_ca if o["dac_san"]], key=lambda o: (not o["anh"], not o["mo_dat"], o["ten"]))
    from app.services import phan_loai_nh as PL
    dem_bac = {k: sum(1 for _n, o in tat_ca if o["bac"] == k) for k in PL.BAC}
    return {"nha_hang": ra[(trang - 1) * so: trang * so], "tong": len(ra), "trang": trang, "so": so,
            "dac_san_noi_bat": ds_ds[:8], "so_dac_san": len(ds_ds), "bac": PL.BAC, "dem_bac": dem_bac,
            "so_michelin": sum(1 for _n, o in tat_ca if o["la_michelin"]),
            "tinh_thanh": sorted(dem), "dem_tinh": dem, "thanh_pho": tp, "mien": MIEN, "nhom_mon": list(NHOM_MON),
            "so_mo_dat": sum(1 for _n, o in tat_ca if o["mo_dat"]), "tong_nha_hang": len(tat_ca),
            "am_thuc": list(AM_THUC), "noi_dung": nd}


def tat_ca_cong(db: Session) -> dict:
    """AT-2 · trang riêng kh.vietourist.vn/restaurant: MỌI nhà hàng đang hiện trong một lần (lọc, đếm, bản đồ chạy trên
    trình duyệt — như cổng khách sạn). Bỏ bớt phần nặng của thẻ: giới thiệu cắt ngắn; trang chi tiết tải đủ."""
    r = danh_sach_cong(db, so=2000, toi_da=2000)
    for o in r["nha_hang"]:
        mt = (o.get("mo_ta") or "").strip()
        o["mo_ta"] = (mt[:180].rsplit(" ", 1)[0] + "…") if len(mt) > 180 else mt
    r.pop("noi_dung", None)
    r["tt_chung"] = tt_chung_nh(db)
    return r


def mot_nha_hang_cong(db: Session, nha_hang_id: int) -> tuple[NhaHang, dict]:
    n = db.get(NhaHang, nha_hang_id)
    if n is None or not n.hien_cong or n.ngung:
        raise LoiNhaHang("Nhà hàng này không còn hiện trên VTD")
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == n.id)).scalars().all()
    return n, _nh_cong(db, n, tds, _hom_nay(), du_album=True)


GIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def tinh_goi(td: dict, ngay: date, nguoi_lon: int, tre_em: int, tuoi: list | None = None,
             chon_phu_thu: list | None = None, bat_tuoi: bool = False) -> dict:
    """P1-03: tách khách theo tuổi, cộng phụ thu, tính tạm tính và cọc cố định (gọi món). Hàm thuần — cổng
    hiện cùng phép tính này để khách hình dung, máy chủ tính lại số chính thức ở đây.

    `tuoi` = tuổi từng trẻ. Gói có khung tuổi mà không có `tuoi`: khi tạo đơn (`bat_tuoi`) thì bắt ghi;
    khi đổi lịch / số khách sau này thì mọi trẻ tính giá trẻ em như trước P1-03."""
    nl, te = int(nguoi_lon), int(tre_em)
    lon, tinh_te, mien = nl, te, 0
    a, b = td.get("tuoi_te_tu"), td.get("tuoi_te_den")
    if te and a is not None and b is not None:
        if tuoi is None or len(tuoi) != te:
            if bat_tuoi:
                raise LoiNhaHang("Ghi tuổi từng trẻ để tính đúng giá")
        else:
            lon, tinh_te = nl, 0
            for x in tuoi:
                try:
                    x = int(x)
                except (TypeError, ValueError):
                    raise LoiNhaHang("Tuổi trẻ em ghi bằng số")
                if not 0 <= x <= 17:
                    raise LoiNhaHang("Tuổi trẻ em từ 0 đến 17")
                if x < a:
                    mien += 1
                elif x <= b:
                    tinh_te += 1
                else:
                    lon += 1
    gl, gt = td.get("gia_nguoi_lon") or 0, td.get("gia_tre_em") or 0
    pt = []
    chon = set(int(i) for i in (chon_phu_thu or []))
    for i, p in enumerate(td.get("phu_thu") or []):
        if p.get("tu_chon") and i not in chon:
            continue
        if (p.get("tu_ngay") and ngay < date.fromisoformat(p["tu_ngay"])) or (p.get("den_ngay") and ngay > date.fromisoformat(p["den_ngay"])):
            continue
        so = (lon + tinh_te) if p["theo"] == "khach" else 1
        pt.append({"i": i, "ten": p["ten"], "so_tien": int(p["so_tien"]) * so, "don_gia": int(p["so_tien"]), "theo": p["theo"], "so": so})
    tong_pt = sum(x["so_tien"] for x in pt)
    coc = int(td.get("coc_moi_khach") or 0) * (nl + te) if td.get("loai") == "goi_mon" and td.get("coc_moi_khach") else 0
    tam = gl * lon + gt * tinh_te + tong_pt
    if coc:
        tam = max(tam, coc + tong_pt)          # gọi món chưa có mức chi dự kiến: tạm tính tối thiểu bằng phần trả trước
    return {"lon": lon, "te": tinh_te, "mien": mien, "tien_nl": gl * lon, "tien_te": gt * tinh_te, "phu_thu": pt,
            "tong_phu_thu": tong_pt, "coc_co_dinh": (coc + tong_pt) if coc else 0, "tam": int(round(tam))}


def kiem_dat_ban(db: Session, nha_hang_id: int, thuc_don_id: int, ngay: date | None, gio: str, nguoi_lon: int, tre_em: int,
                 hom_nay: date, tuoi: list | None = None, chon_phu_thu: list | None = None,
                 bat_tuoi: bool = False) -> tuple[dict, dict, int]:
    """Kiểm yêu cầu đặt bàn; trả (nhà hàng, gói, tạm tính). Tạm tính do MÁY tính từ giá đã lưu.
    Gói trả về kèm `tinh` (chi tiết P1-03: khách theo tuổi, phụ thu, cọc cố định)."""
    _n, o = mot_nha_hang_cong(db, nha_hang_id)
    if not o["mo_dat"]:
        raise LoiNhaHang("Nhà hàng này chưa mở đặt bàn qua VTD")
    if ngay is not None and not mo_dat(db, _n, None, ngay):
        raise LoiNhaHang("Ngày này nằm ngoài thời hạn hợp đồng của nhà hàng — chọn ngày khác")
    td = next((t for t in o["thuc_don"] if t["id"] == thuc_don_id), None)
    if td is None:
        raise LoiNhaHang("Chọn một gói đang bán của nhà hàng này")
    if ngay is None or ngay <= hom_nay:
        raise LoiNhaHang("Chọn ngày đến sau hôm nay")
    if (td["tu_ngay"] and ngay < date.fromisoformat(td["tu_ngay"])) or (td["den_ngay"] and ngay > date.fromisoformat(td["den_ngay"])):
        raise LoiNhaHang("Ngày đến ngoài thời gian áp dụng của gói")
    if not GIO_RE.match(gio or ""):
        raise LoiNhaHang("Ghi giờ đến dạng HH:MM")
    if not 1 <= int(nguoi_lon or 0) <= 500 or not 0 <= int(tre_em or 0) <= 500:
        raise LoiNhaHang("Số người lớn từ 1, trẻ em từ 0")
    if int(nguoi_lon) + int(tre_em) < td["so_khach_toi_thieu"]:
        raise LoiNhaHang(f"Gói này tối thiểu {td['so_khach_toi_thieu']} khách")
    # P1-03: khung giờ, số khách tối đa
    if td.get("gio_tu") and td.get("gio_den") and not td["gio_tu"] <= gio <= td["gio_den"]:
        raise LoiNhaHang(f"Gói này chỉ áp dụng {td['gio_tu']}–{td['gio_den']} — chọn giờ khác hoặc gói khác")
    if td.get("so_khach_toi_da") and int(nguoi_lon) + int(tre_em) > td["so_khach_toi_da"]:
        raise LoiNhaHang(f"Gói này tối đa {td['so_khach_toi_da']} khách / đơn — nhiều hơn vui lòng gửi yêu cầu đoàn để Sales báo giá")
    ct = tinh_goi(td, ngay, int(nguoi_lon), int(tre_em), tuoi, chon_phu_thu, bat_tuoi)
    return o, {**td, "tinh": ct}, ct["tam"]


# ══ AT-1 · nhập danh sách, xác minh, hợp đồng, nội dung (Chủ tịch duyệt 28/10/2026) ═══════════════════════════
# Bí danh cột, ƯU TIÊN theo thứ tự ghi. Gồm cột của tệp bàn giao «TasteAtlas-Viet-Nam-144-ho-so.csv» (29/10/2026):
# Ma_nguon, Thu_tu_hien_thi_khong_phai_hang, Ten_nguon, Ten_hien_thi, Dia_danh_nguon, Diem_den_hien_thi, Mon_nguon_nhac, Nguon.
COT_NHAP = {"ten": ("ten hien thi", "source_name", "ten nguon", "name", "ten nha hang", "ten", "nha hang", "restaurant"),
            "dia_danh": ("dia danh nguon", "source_city", "city", "dia danh", "thanh pho", "tinh", "dia diem", "location"),
            "diem_den": ("diem den hien thi", "diem den"),
            "mon": ("mon nguon nhac", "source_dishes", "dishes", "mon noi bat", "mon", "dish"),
            "ma": ("ma nguon", "source_id"),
            "thu_tu": ("thu tu hien thi khong phai hang", "source_order", "order", "stt", "thu tu"),
            "link": ("source_link", "link", "url", "nguon")}
TOI_DA_NHAP = 2000


def _bang_tep(ten_tep: str, data: bytes) -> list[list]:
    from app.services.so_co_dong import _bang
    return _bang(ten_tep, data)


def _chuan(s) -> str:
    return " ".join(_khong_dau(str(s or "")).split())


def _bang_tp() -> dict:
    b = {}
    for ten, (_m, khac) in THANH_PHO.items():
        for x in (ten, ten.replace("TP. ", ""), *khac):
            b[" ".join(_chuan(x).replace("–", " ").replace("-", " ").split())] = ten
    return b


# Tên chỉ phân biệt được khi CÒN DẤU (bỏ dấu là trùng nơi khác): so trước khi bỏ dấu.
CON_DAU = {"thạnh xuân": "TP. Hồ Chí Minh"}      # phường Thạnh Xuân, Q.12 — khác quận Thanh Xuân, Hà Nội


def tinh_tu_nguon(dia_danh: str) -> str:
    """Quy địa danh nguồn về thành phố ẩm thực (THANH_PHO). Không khớp thì giữ nguyên để Điều hành sửa tay.
    «Mekong Delta» (vùng) quy về Cần Thơ — thủ phủ miền Tây (Chủ tịch 29/10/2026: nhận hết nhà hàng VN trên nguồn)."""
    import unicodedata
    tho = " ".join(unicodedata.normalize("NFC", str(dia_danh or "")).lower().replace(",", " ").split())
    for a, b in CON_DAU.items():
        if tho == a or tho.startswith(a + " "):
            return b
    k = " ".join(_chuan(dia_danh).replace(".", " ").replace(",", " ").replace("-", " ").split())
    k = " ".join(w for w in k.split() if w not in ("vietnam", "city", "province", "tp", "tinh", "thanh", "pho")) or k
    k = k.replace("viet nam", "").strip()
    bang = _bang_tp()
    if k in bang:
        return bang[k]
    for a in sorted(bang, key=len, reverse=True):
        if k.startswith(a + " ") or k.endswith(" " + a) or f" {a} " in f" {k} ":
            return bang[a]
    return (dia_danh or "").strip()


def doc_tep_nhap(ten_tep: str, data: bytes) -> dict:
    """Đọc tệp CSV / Excel danh sách nhà hàng (không ghi gì)."""
    if not data:
        raise LoiNhaHang("Tệp rỗng")
    if (ten_tep or "").lower().endswith(".json"):
        import json
        try:
            rows = json.loads(data.decode("utf-8-sig"))
        except Exception:
            raise LoiNhaHang("Tệp JSON không đọc được")
        if isinstance(rows, dict):
            rows = next((v for v in rows.values() if isinstance(v, list)), [])
        keys = sorted({k for r in rows if isinstance(r, dict) for k in r})
        bang = [keys] + [[r.get(k) for k in keys] for r in rows if isinstance(r, dict)]
    else:
        try:
            bang = _bang_tep(ten_tep, data)
        except Exception as ex:
            raise LoiNhaHang(f"Không đọc được tệp: {ex}")
    dau, cot = None, {}
    for i, r in enumerate(bang[:20]):
        nhan = [_chuan(x).replace("_", " ") for x in r]
        m = {}
        for k, al in COT_NHAP.items():
            for a in al:                              # bí danh đứng trước thắng
                j = next((j for j, h in enumerate(nhan) if h and h == a.replace("_", " ") and j not in m.values()), None)
                if j is not None:
                    m[k] = j; break
        if {"ten", "dia_danh"} <= m.keys():
            dau, cot = i, m; break
    if dau is None:
        raise LoiNhaHang("Không thấy dòng tiêu đề có cột tên nhà hàng (source_name / Tên) và địa danh (source_city / Địa danh)")
    dong, loi = [], []
    for i, r in enumerate(bang[dau + 1:], start=dau + 2):
        g = lambda k: (r[cot[k]] if k in cot and cot[k] < len(r) else None)  # noqa: E731
        ten, dd = str(g("ten") or "").strip(), str(g("dia_danh") or "").strip()
        if not ten and not dd:
            continue
        if not ten or not dd:
            loi.append({"dong": i, "loi": "thiếu tên hoặc địa danh"}); continue
        mon = g("mon")
        mon = ", ".join(str(x).strip() for x in mon) if isinstance(mon, list) else str(mon or "").strip()
        tp = tinh_tu_nguon(dd)
        if tp not in THANH_PHO and g("diem_den"):            # địa danh gốc chưa khớp → thử điểm đến đã chuẩn hóa
            tp2 = tinh_tu_nguon(str(g("diem_den")))
            tp = tp2 if tp2 in THANH_PHO else tp
        dong.append({"ten": ten[:160], "dia_danh": dd[:120], "tinh": tp[:80], "mon": mon[:500], "khop": tp in THANH_PHO,
                     "ref": " · ".join(x for x in (str(g(k) or "").strip() for k in ("ma", "thu_tu", "link")) if x)[:300]})
    if len(dong) > TOI_DA_NHAP:
        raise LoiNhaHang(f"Tệp có {len(dong)} dòng — vượt {TOI_DA_NHAP}")
    return {"dong": dong, "loi": loi, "cot": {k: str(bang[dau][j]) for k, j in cot.items()}}


def nhap_tep(db: Session, u: User, ten_tep: str, data: bytes, nguon: str, thu: bool = True, now: datetime | None = None) -> dict:
    """Điều hành nhập danh sách. Trùng chính xác tên + địa danh (bỏ dấu, bỏ khoảng trắng thừa) thì bỏ qua — không tự gộp.
    Bản ghi mới: chưa hiện, chưa ghi nhận hợp đồng, liên hệ chưa xác minh."""
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành nhập danh sách nhà hàng")
    nguon = (nguon or "").strip()[:60]
    if not nguon:
        raise LoiNhaHang("Ghi nguồn danh sách (ví dụ: Danh mục TasteAtlas 28/10/2026)")
    r = doc_tep_nhap(ten_tep, data)
    co = {(_chuan(n.ten), _chuan(n.dia_danh_nguon or n.tinh_thanh)) for n in db.execute(select(NhaHang)).scalars()}
    moi, trung, thay = [], [], set()
    for d in r["dong"]:
        k = (_chuan(d["ten"]), _chuan(d["dia_danh"]))
        if k in co or k in thay:
            trung.append(d); continue
        thay.add(k); moi.append(d)
    if not thu:
        now = now or datetime.now()
        for d in moi:
            nh = NhaHang(ma=_ma_moi(db), ten=d["ten"], tinh_thanh=d["tinh"], dia_danh_nguon=d["dia_danh"], mon_noi_bat=d["mon"],
                         nguon=nguon, nguon_ref=d["ref"], tao_boi=u.username, tao_luc=now, hien_cong=False)
            db.add(nh); db.flush()
        from app.services import rules as R
        R.audit(db, u.username, u.role, "nha_hang_nhap_tep", f"nha_hang:nhap:{nguon}", after={"moi": len(moi), "trung": len(trung)})
        db.commit()
    return {"moi": len(moi), "trung": len(trung), "loi": r["loi"], "cot": r["cot"], "mau": moi[:10],
            "chua_khop_tp": [{"ten": d["ten"], "dia_danh": d["dia_danh"]} for d in moi if not d["khop"]],
            "trung_mau": trung[:10], "da_nhap": not thu}


def hien_hang_loat(db: Session, u: User, ids: list[int], bat: bool, now: datetime | None = None) -> dict:
    """TP Điều hành bật / tắt hiện giới thiệu nhiều nhà hàng một lần. Nơi chính người bật đã nhập / sửa thì bỏ qua."""
    if not _co(u, VAI_BAT):
        raise LoiNhaHang("Chỉ TP Điều hành bật hoặc tắt hiện trên cổng")
    ok, bo = 0, []
    for nid in ids[:500]:
        try:
            nh = db.get(NhaHang, int(nid))
            if nh is None or nh.hien_cong == bat:
                continue
            bat_hien(db, u, nh.id, bat, now)
            ok += 1
        except LoiNhaHang as ex:
            db.rollback()
            bo.append({"id": nid, "ly_do": str(ex)})
    return {"da_doi": ok, "bo_qua": bo}


def xac_minh_lien_he(db: Session, u: User, nid: int, ok: bool, now: datetime | None = None) -> NhaHang:
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành xác minh liên hệ nhà hàng")
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    nh.lien_he_xac_minh, nh.xac_minh_boi, nh.xac_minh_luc = bool(ok), u.username, now or datetime.now()
    db.commit(); db.refresh(nh)
    return nh


def _bps(v) -> int | None:
    if v in (None, ""):
        return None
    try:
        x = float(str(v).replace(",", ".").replace("%", ""))
    except ValueError:
        raise LoiNhaHang("Tỷ lệ hoa hồng không hợp lệ")
    if not 0 <= x <= 100:
        raise LoiNhaHang("Tỷ lệ hoa hồng từ 0 đến 100%")
    return int(round(x * 100))


def ghi_hop_dong(db: Session, u: User, nid: int, d: dict, ten_tep: str, kieu: str, data: bytes | None,
                 now: datetime | None = None) -> HopDongNhaHang:
    """Điều hành ghi nhận hợp đồng đã ký + tải tệp. Có bản cũ thì bản mới thay thế, bắt buộc lý do; bản cũ giữ nguyên."""
    from app.models.suppliers import Supplier
    from app.services import attachments as AT
    from app.services import rules as R
    if not _co(u, VAI_NHAP):
        raise LoiNhaHang("Chỉ Điều hành ghi nhận hợp đồng nhà hàng")
    now = now or datetime.now()
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    if not d.get("da_ky"):
        raise LoiNhaHang("Đánh dấu «Đã ký hợp đồng»")
    if not data:
        raise LoiNhaHang("Tải tệp hợp đồng đã ký (PDF / ảnh)")
    s = db.get(Supplier, nh.supplier_id) if nh.supplier_id else None
    if s is None:
        raise LoiNhaHang("Gắn nhà hàng với nhà cung cấp trước (màn Cổng nhà cung cấp) — hợp đồng lưu vào hồ sơ NCC")
    so_hd = (d.get("so_hd") or "").strip()
    if not so_hd:
        raise LoiNhaHang("Ghi số hợp đồng")
    ngay_ky, tu, den = _ngay(d.get("ngay_ky")), _ngay(d.get("tu_ngay")), _ngay(d.get("den_ngay"))
    if ngay_ky is None or tu is None:
        raise LoiNhaHang("Ghi ngày ký và ngày bắt đầu hiệu lực")
    if den is not None and den < tu:
        raise LoiNhaHang("Ngày kết thúc phải sau ngày bắt đầu")
    bps = _bps(d.get("hoa_hong_pct"))
    co_dinh = int(d["hoa_hong_co_dinh"]) if d.get("hoa_hong_co_dinh") not in (None, "") else None
    if co_dinh is not None and co_dinh < 0:
        raise LoiNhaHang("Hoa hồng cố định không âm")
    cu = db.execute(select(HopDongNhaHang).where(HopDongNhaHang.nha_hang_id == nh.id, HopDongNhaHang.con_dung.is_(True))
                    .order_by(HopDongNhaHang.id.desc())).scalars().first()
    ly_do = (d.get("ly_do") or "").strip()
    if cu is not None and len(ly_do) < 5:
        raise LoiNhaHang("Đã có hợp đồng ghi nhận — ghi lý do thay bản mới (gia hạn, phụ lục, sửa sai…)")
    try:
        a, _ = AT.dinh_kem(db, "nha_cung_cap", s.code, ten_tep, data, kieu=kieu, loai="hop_dong",
                           mo_ta=f"Hợp đồng nhà hàng {nh.ma} · {so_hd}", boi=u.username)
    except ValueError as ex:
        raise LoiNhaHang(str(ex))
    if cu is not None:
        cu.con_dung = False
    h = HopDongNhaHang(nha_hang_id=nh.id, phien_ban=(cu.phien_ban + 1) if cu else 1, so_hd=so_hd[:80], ngay_ky=ngay_ky,
                       tu_ngay=tu, den_ngay=den, hoa_hong_bps=bps, hoa_hong_co_dinh=co_dinh,
                       co_so_hoa_hong=(d.get("co_so") or "").strip()[:300], attachment_id=a.id,
                       thay_cho_id=cu.id if cu else None, ly_do=ly_do[:1000], con_dung=True, ghi_boi=u.username, ghi_luc=now)
    db.add(h); db.flush()
    R.audit(db, u.username, u.role, "nha_hang_ghi_hop_dong", f"nha_hang:{nh.ma}",
            after={"so_hd": so_hd, "phien_ban": h.phien_ban, "bps": bps, "co_dinh": co_dinh, "den": str(den or "")})
    db.commit(); db.refresh(h)
    return h


def tep_hop_dong(db: Session, u: User, hid: int):
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    from app.services import rules as R
    if not _co(u, VAI_HOP_DONG_XEM):
        raise LoiNhaHang("Không có quyền xem hợp đồng nhà hàng")
    h = db.get(HopDongNhaHang, hid)
    if h is None:
        raise LoiNhaHang("Không có hợp đồng này")
    a = db.get(Attachment, h.attachment_id)
    R.audit(db, u.username, u.role, "nha_hang_xem_hop_dong", f"hop_dong_nha_hang:{h.id}")
    db.commit()
    return AT.doc(db, a), a


def _hd_out(h: HopDongNhaHang) -> dict:
    return {"id": h.id, "phien_ban": h.phien_ban, "so_hd": h.so_hd, "ngay_ky": h.ngay_ky.isoformat(), "tu_ngay": h.tu_ngay.isoformat(),
            "den_ngay": h.den_ngay.isoformat() if h.den_ngay else None,
            "hoa_hong": (f"{h.hoa_hong_bps / 100:g}%" if h.hoa_hong_bps is not None else "")
            + (" + " if h.hoa_hong_bps is not None and h.hoa_hong_co_dinh is not None else "")
            + (f"{h.hoa_hong_co_dinh:,} đ/đơn".replace(",", ".") if h.hoa_hong_co_dinh is not None else ""),
            "co_so": h.co_so_hoa_hong, "con_dung": h.con_dung, "ly_do": h.ly_do, "ghi_boi": h.ghi_boi,
            "ghi_luc": h.ghi_luc.isoformat(timespec="minutes")}


def luu_gioi_thieu(db: Session, u: User, nid: int, mo_ta: str, mon_noi_bat: str, now: datetime | None = None) -> NhaHang:
    """Marketing viết giới thiệu do VTD biên tập (không chép nội dung nguồn ngoài)."""
    if not _co(u, VAI_NOI_DUNG):
        raise LoiNhaHang("Chỉ Marketing / Điều hành viết giới thiệu nhà hàng")
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    nh.mo_ta, nh.mon_noi_bat = (mo_ta or "").strip()[:4000], (mon_noi_bat or "").strip()[:500]
    nh.sua_boi, nh.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(nh)
    return nh


TRUONG_ND = ("ten_khac", "nhom", "tinh_thanh", "tom_tat", "noi_dung", "vung", "nen_an", "thanh_phan", "cach_goi", "anh_nguon")
DAI_ND = {"ten_khac": 160, "nhom": 40, "tinh_thanh": 80, "tom_tat": 300, "noi_dung": 8000, "vung": 160, "nen_an": 160,
          "thanh_phan": 300, "cach_goi": 300, "anh_nguon": 200}


def _nd_out(x: NoiDungAmThuc, noi_bo: bool = False, nha_hang: dict | None = None) -> dict:
    o = {"id": x.id, "loai": x.loai, "loai_ten": LOAI_ND.get(x.loai, x.loai), "ten": x.ten, "thu_tu": x.thu_tu,
         **{k: getattr(x, k) for k in TRUONG_ND}, "anh": _duong_anh(x.anh_id), "anh_nguon": x.anh_nguon if x.anh_id else ""}
    if noi_bo:
        o.update({"hien": x.hien, "sua_boi": x.sua_boi, "nha_hang_ids": list(x.nha_hang_ids or []), "co_anh": bool(x.anh_id)})
    else:   # «Ăn ở đâu»: chỉ nhà hàng đang hiện; nơi đặt được qua Vietourist lên trước
        nh = nha_hang or {}
        an = [nh[i] for i in (x.nha_hang_ids or []) if i in nh]
        an.sort(key=lambda o: not o["mo_dat"])
        o["an_o_dau"] = [{"id": a["id"], "ten": a["ten"], "khu_vuc": a["khu_vuc"], "tinh_thanh": a["tinh_thanh"],
                          "mo_dat": a["mo_dat"], "gia_tu": a["gia_tu"]} for a in an]
    return o


def ds_noi_dung(db: Session, cong: bool = False, nha_hang: dict | None = None) -> list[dict]:
    cau = select(NoiDungAmThuc).order_by(NoiDungAmThuc.loai, NoiDungAmThuc.thu_tu, NoiDungAmThuc.ten)
    if cong:
        cau = cau.where(NoiDungAmThuc.hien.is_(True))
        if nha_hang is None:
            nha_hang = {n.id: o for n, o in _nh_hien(db, _hom_nay())}
    return [_nd_out(x, not cong, nha_hang) for x in db.execute(cau).scalars()]


def luu_noi_dung(db: Session, u: User, d: dict, nd_id: int | None = None, now: datetime | None = None) -> NoiDungAmThuc:
    if not _co(u, VAI_NOI_DUNG):
        raise LoiNhaHang("Chỉ Marketing / Điều hành viết nội dung ẩm thực")
    if d.get("loai") not in LOAI_ND:
        raise LoiNhaHang("Chọn loại: món ăn, đặc sản, danh sách, giới thiệu thành phố hoặc ảnh bìa")
    ten = (d.get("ten") or "").strip()
    if not ten:
        raise LoiNhaHang("Ghi tên")
    if d["loai"] == "thanh_pho" and ten not in THANH_PHO:
        raise LoiNhaHang("Giới thiệu thành phố: chọn đúng tên trong danh sách thành phố ẩm thực")
    tp = (d.get("tinh_thanh") or "").strip()
    if tp and tp not in THANH_PHO:
        raise LoiNhaHang("Thành phố không có trong danh sách thành phố ẩm thực")
    if d["loai"] == "mon" and d.get("nhom") and d["nhom"] not in NHOM_MON:
        raise LoiNhaHang("Nhóm món không hợp lệ")
    ids = []
    for i in d.get("nha_hang_ids") or []:
        if db.get(NhaHang, int(i)) is None:
            raise LoiNhaHang(f"Không có nhà hàng mã số {i}")
        if int(i) not in ids:
            ids.append(int(i))
    x = db.get(NoiDungAmThuc, nd_id) if nd_id else None
    if nd_id and x is None:
        raise LoiNhaHang("Không có nội dung này")
    if x is None:
        x = NoiDungAmThuc(loai=d["loai"], ten=ten); db.add(x)
    x.loai, x.ten = d["loai"], ten[:160]
    for k in TRUONG_ND:
        if k in d and d[k] is not None:
            setattr(x, k, str(d[k]).strip()[:DAI_ND[k]])
    x.nha_hang_ids = ids
    x.thu_tu = int(d.get("thu_tu") or 0)
    if d.get("hien") and x.anh_id is None and d["loai"] in ("thanh_pho", "bia"):
        raise LoiNhaHang("Tải ảnh trước khi bật hiện mục này")
    x.hien = bool(d.get("hien"))
    x.sua_boi, x.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(x)
    return x


def gan_anh(db: Session, u: User, doi: str, oid: int, ten_tep: str, kieu: str, data: bytes, nguon: str) -> int:
    """Tải ảnh cho nhà hàng (doi="nha_hang") hoặc nội dung (doi="noi_dung"). Bắt buộc ghi nguồn ảnh
    (VTD chụp / nhà hàng cấp quyền / Unsplash – tên tác giả…). Ảnh cũ vẫn trong kho, chỉ thôi dùng."""
    from app.services import attachments as AT
    nguon = (nguon or "").strip()
    if len(nguon) < 3:
        raise LoiNhaHang("Ghi nguồn ảnh (VTD chụp, nhà hàng cấp quyền, Unsplash – tên tác giả…)")
    if doi == "nha_hang":
        # AT-2a: ảnh nhà hàng đi qua Album (căn cứ quyền dùng + TP Điều hành duyệt), không gắn ảnh đơn nữa.
        raise LoiNhaHang("Ảnh nhà hàng: dùng mục «Album ảnh» của nhà hàng")
    if doi == "noi_dung":
        if not _co(u, VAI_NOI_DUNG):
            raise LoiNhaHang("Chỉ Marketing / Điều hành tải ảnh nội dung ẩm thực")
        x = db.get(NoiDungAmThuc, oid)
    else:
        raise LoiNhaHang("Đối tượng ảnh không hợp lệ")
    if x is None:
        raise LoiNhaHang("Không có bản ghi này")
    if not data:
        raise LoiNhaHang("Chọn tệp ảnh")
    try:
        a, _ = AT.dinh_kem(db, "am_thuc", f"{'nh' if doi == 'nha_hang' else 'nd'}{oid}", ten_tep, data, kieu=kieu,
                           loai="hinh_anh", mo_ta=f"Nguồn ảnh: {nguon}", boi=u.username)
    except ValueError as ex:
        raise LoiNhaHang(str(ex))
    if not a.la_anh:
        db.rollback()
        raise LoiNhaHang("Chỉ nhận ảnh JPG / PNG / WEBP")
    x.anh_id, x.anh_nguon = a.id, nguon[:200]
    db.commit()
    return a.id


def anh_cong(db: Session, aid: int):
    """Ảnh cho trang công khai: chỉ ảnh đang dùng của nhà hàng đang hiện hoặc nội dung đã bật."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    # AT-2a: ảnh đơn cũ của nhà hàng (nha_hang.anh_id) KHÔNG còn ra cổng — ảnh nhà hàng chỉ qua album đã duyệt.
    ok = db.execute(select(NoiDungAmThuc.id).where(NoiDungAmThuc.anh_id == aid, NoiDungAmThuc.hien.is_(True))).first()
    if not ok:
        raise LoiNhaHang("Không có ảnh này")
    a = db.get(Attachment, aid)
    return AT.doc(db, a), a


def anh_noi_bo(db: Session, u: User, aid: int):
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    ok = db.execute(select(NhaHang.id).where(NhaHang.anh_id == aid)).first() or \
        db.execute(select(NoiDungAmThuc.id).where(NoiDungAmThuc.anh_id == aid)).first()
    if not ok:
        raise LoiNhaHang("Không có ảnh này")
    a = db.get(Attachment, aid)
    return AT.doc(db, a), a


# ══ AT-2a · ALBUM ẢNH NHÀ HÀNG (Chủ tịch + Điều hành chốt 29/10/2026) ═══════════════════════════════════════
from app.models.nha_hang import AnhNhaHang, NHOM_ANH, CAN_CU_ANH, TRANG_THAI_ANH  # noqa: E402

VAI_DUYET_ANH = ("tp_dh",) + TOAN_QUYEN
ANH_TOI_DA_MB = 10
ANH_TOI_DA_SO = 60
KIEU_ANH = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
CANH_HIEN, CANH_NHO = 1600, 480
# Đổi các trường này trên ảnh ĐÃ DUYỆT → ảnh về «Chờ duyệt» (thôi hiện) cho tới khi TP ĐH duyệt lại:
# chúng là chữ / căn cứ ra trước khách. Đổi nhóm, thứ tự, ảnh bìa thì không.
TRUONG_ANH_DUYET_LAI = ("chu_thich", "mo_ta_thay_the", "credit", "can_cu", "can_cu_ghi_chu")


def _lam_nhe(data: bytes) -> tuple[bytes | None, bytes | None, int, int]:
    """Bản hiển thị (≤1600px) và ảnh nhỏ (≤480px), WEBP, xoay theo EXIF rồi BỎ EXIF (vị trí GPS…).
    Không có thư viện ảnh / ảnh lỗi → (None, None, 0, 0): giữ bản gốc, cổng dùng bản gốc."""
    try:
        from io import BytesIO
        from PIL import Image, ImageOps
    except Exception:
        return None, None, 0, 0
    try:
        im = Image.open(BytesIO(data))
        if (im.format or "").upper() == "JPEG":
            im.draft("RGB", (CANH_HIEN * 2, CANH_HIEN * 2))        # giải mã thu nhỏ: đỡ bộ nhớ máy chủ 512 MB
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        rong, cao = im.size
        ra = []
        for canh, q in ((CANH_HIEN, 82), (CANH_NHO, 76)):
            b = im.copy()
            b.thumbnail((canh, canh))
            o = BytesIO()
            b.save(o, "WEBP", quality=q, method=4)
            ra.append(o.getvalue())
        return ra[0], ra[1], rong, cao
    except Exception:
        return None, None, 0, 0


def _anh_cua(db: Session, nid: int) -> list[AnhNhaHang]:
    return db.execute(select(AnhNhaHang).where(AnhNhaHang.nha_hang_id == nid)
                      .order_by(AnhNhaHang.thu_tu, AnhNhaHang.id)).scalars().all()


def _anh_out(x: AnhNhaHang, a_goc=None) -> dict:
    return {"id": x.id, "nha_hang_id": x.nha_hang_id, "nhom": x.nhom, "nhom_ten": NHOM_ANH.get(x.nhom, "Chưa phân nhóm"),
            "chu_thich": x.chu_thich, "mo_ta_thay_the": x.mo_ta_thay_the, "thu_tu": x.thu_tu, "la_bia": x.la_bia,
            "can_cu": x.can_cu, "can_cu_ten": CAN_CU_ANH.get(x.can_cu, x.can_cu), "can_cu_ghi_chu": x.can_cu_ghi_chu,
            "credit": x.credit, "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_ANH.get(x.trang_thai, x.trang_thai),
            "ly_do_tra_lai": x.ly_do_tra_lai, "tai_boi": x.tai_boi, "tai_luc": x.tai_luc.isoformat(timespec="minutes") if x.tai_luc else None,
            "duyet_boi": x.duyet_boi, "rong": x.rong, "cao": x.cao,
            "ten_tep": a_goc.ten_tep if a_goc is not None else "", "kich_thuoc": a_goc.kich_thuoc if a_goc is not None else 0,
            "nho": f"/api/v1/nha-hang/album/{x.id}/nho", "hien": f"/api/v1/nha-hang/album/{x.id}/hien",
            "goc": f"/api/v1/nha-hang/album/{x.id}/goc"}


def album(db: Session, u: User, nid: int) -> dict:
    from app.models.attachments import Attachment
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    ds = _anh_cua(db, nid)
    goc = {a.id: a for a in db.execute(select(Attachment).where(Attachment.id.in_([x.attachment_id for x in ds]))).scalars()} if ds else {}
    dem = {k: sum(1 for x in ds if x.trang_thai == k) for k in TRANG_THAI_ANH}
    return {"nha_hang": {"id": nh.id, "ten": nh.ten, "ma": nh.ma}, "anh": [_anh_out(x, goc.get(x.attachment_id)) for x in ds],
            "dem": dem, "tong": len(ds), "toi_da": ANH_TOI_DA_SO, "toi_da_mb": ANH_TOI_DA_MB,
            "nhom_anh": NHOM_ANH, "can_cu_anh": CAN_CU_ANH, "duoc_duyet": _co(u, VAI_DUYET_ANH),
            "duoc_tai": _co(u, VAI_ANH_NH), "toi": u.username}


def _kiem_can_cu(can_cu: str, nhom: str) -> None:
    if can_cu not in CAN_CU_ANH:
        raise LoiNhaHang("Chọn căn cứ quyền dùng: Nhà hàng cấp quyền / VTD tự chụp / Bên thứ ba cấp phép / Chưa xác minh")
    if nhom and nhom not in NHOM_ANH:
        raise LoiNhaHang("Nhóm ảnh không hợp lệ")


def _co_pil() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _kiem_tep_anh(ten_tep: str, data: bytes) -> str:
    if not data:
        raise LoiNhaHang("Chọn tệp ảnh")
    duoi = (ten_tep or "").rsplit(".", 1)[-1].lower() if "." in (ten_tep or "") else ""
    if duoi not in KIEU_ANH:
        raise LoiNhaHang("Chỉ nhận ảnh JPG / PNG / WEBP (ảnh HEIC của iPhone: xuất lại JPG)")
    mb = len(data) / 1024 / 1024
    if mb > ANH_TOI_DA_MB:
        raise LoiNhaHang(f"Ảnh nặng {mb:.1f} MB, quá {ANH_TOI_DA_MB} MB — xuất lại ảnh nhẹ hơn")
    return duoi


def _luu_tep(db: Session, u: User, nh: NhaHang, ten_tep: str, duoi: str, data: bytes, can_cu: str):
    """Cất bản gốc + bản hiển thị + ảnh nhỏ vào kho. Trả (gốc, hiển thị, nhỏ, rộng, cao)."""
    from app.services import attachments as AT
    hien, nho, rong, cao = _lam_nhe(data)
    if hien is None and _co_pil():
        raise LoiNhaHang("Tệp không mở được như một ảnh — kiểm tra lại tệp")
    ma = f"nh{nh.id}"
    try:
        a, _ = AT.dinh_kem(db, "am_thuc", ma, ten_tep, data, kieu=KIEU_ANH[duoi], loai="hinh_anh",
                           mo_ta=f"Album {nh.ma} · căn cứ: {CAN_CU_ANH.get(can_cu, can_cu)}", boi=u.username)
        ah = AT.dinh_kem(db, "am_thuc", ma, f"{ten_tep}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Bản hiển thị · album {nh.ma}", boi=u.username, nguon="he_thong")[0] if hien else a
        an = AT.dinh_kem(db, "am_thuc", ma, f"{ten_tep}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Ảnh nhỏ · album {nh.ma}", boi=u.username, nguon="he_thong")[0] if nho else ah
    except ValueError as ex:
        raise LoiNhaHang(str(ex))
    return a, ah, an, rong, cao


def _trung(db: Session, ds: list, data: bytes):
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    cs = AT._sha(data)
    for x in ds:
        a = db.get(Attachment, x.attachment_id)
        if a is not None and a.checksum == cs:
            return x
    return None


def tai_anh_album(db: Session, u: User, nid: int, ten_tep: str, kieu: str, data: bytes, d: dict,
                  now: datetime | None = None) -> tuple[AnhNhaHang, bool]:
    """Tải MỘT ảnh vào album (giao diện gửi từng tệp để báo tiến độ / thử lại riêng). Trả (ảnh, có phải ảnh mới).
    Cùng nội dung đã có trong album → trả đúng ảnh đó, không tạo bản trùng."""
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing tải ảnh nhà hàng")
    now = now or datetime.now()
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    duoi = _kiem_tep_anh(ten_tep, data)
    nhom, can_cu = (d.get("nhom") or "").strip(), (d.get("can_cu") or "").strip() or "chua_xac_minh"   # không bắt buộc
    if not nhom:
        raise LoiNhaHang("Chọn nhóm ảnh cho lô này")
    _kiem_can_cu(can_cu, nhom)
    ds = _anh_cua(db, nid)
    cu = _trung(db, ds, data)
    if cu is not None:
        return cu, False
    if len(ds) >= ANH_TOI_DA_SO:
        raise LoiNhaHang(f"Album đã đủ {ANH_TOI_DA_SO} ảnh — ẩn hoặc thay ảnh cũ thay vì tải thêm")
    a, ah, an, rong, cao = _luu_tep(db, u, nh, ten_tep, duoi, data, can_cu)
    x = AnhNhaHang(nha_hang_id=nid, attachment_id=a.id, hien_id=ah.id, nho_id=an.id, rong=rong, cao=cao, nhom=nhom,
                   chu_thich=(d.get("chu_thich") or "").strip()[:200], mo_ta_thay_the="",
                   thu_tu=(max([y.thu_tu for y in ds], default=0) + 1), la_bia=False, can_cu=can_cu,
                   can_cu_ghi_chu=(d.get("can_cu_ghi_chu") or "").strip()[:300], credit=(d.get("credit") or "").strip()[:160],
                   trang_thai="da_duyet", tai_boi=u.username, tai_luc=now,
                   duyet_boi="tu_dong", duyet_luc=now)              # KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh — tải là hiện
    db.add(x)
    db.commit(); db.refresh(x)
    return x, True


def _lay_anh(db: Session, pid: int) -> AnhNhaHang:
    x = db.get(AnhNhaHang, pid)
    if x is None:
        raise LoiNhaHang("Không có ảnh này")
    return x


def sua_anh(db: Session, u: User, pid: int, d: dict, now: datetime | None = None) -> AnhNhaHang:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing sửa ảnh nhà hàng")
    x = _lay_anh(db, pid)
    moi = {"nhom": (d.get("nhom") if d.get("nhom") is not None else x.nhom).strip(),
           "chu_thich": (d.get("chu_thich") if d.get("chu_thich") is not None else x.chu_thich).strip()[:200],
           "mo_ta_thay_the": (d.get("mo_ta_thay_the") if d.get("mo_ta_thay_the") is not None else x.mo_ta_thay_the).strip()[:200],
           "credit": (d.get("credit") if d.get("credit") is not None else x.credit).strip()[:160],
           "can_cu": (d.get("can_cu") if d.get("can_cu") is not None else x.can_cu).strip(),
           "can_cu_ghi_chu": (d.get("can_cu_ghi_chu") if d.get("can_cu_ghi_chu") is not None else x.can_cu_ghi_chu).strip()[:300]}
    _kiem_can_cu(moi["can_cu"], moi["nhom"])
    if not moi["nhom"] and x.nhom:
        raise LoiNhaHang("Chọn nhóm ảnh")
    duyet_lai = False                                    # KS-16c: không còn duyệt lại khi sửa
    for k, v in moi.items():
        setattr(x, k, v)
    if duyet_lai:
        x.trang_thai, x.duyet_boi, x.duyet_luc = "cho_duyet", "", None
    x.sua_boi, x.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(x)
    return x


def thay_anh(db: Session, u: User, pid: int, ten_tep: str, kieu: str, data: bytes, now: datetime | None = None) -> AnhNhaHang:
    """Thay TỆP của đúng một ảnh (giữ nhóm, chú thích, thứ tự, căn cứ). Tệp cũ vẫn trong kho. Ảnh về «Nháp»."""
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing thay ảnh nhà hàng")
    x = _lay_anh(db, pid)
    duoi = _kiem_tep_anh(ten_tep, data)
    cu = _trung(db, _anh_cua(db, x.nha_hang_id), data)
    if cu is not None:
        if cu.id == x.id:
            return x
        raise LoiNhaHang("Ảnh này đã có trong album (ảnh khác) — không thay bằng ảnh trùng")
    nh = db.get(NhaHang, x.nha_hang_id)
    a, ah, an, rong, cao = _luu_tep(db, u, nh, ten_tep, duoi, data, x.can_cu)
    x.attachment_id, x.hien_id, x.nho_id, x.rong, x.cao = a.id, ah.id, an.id, rong, cao
    if x.trang_thai != "an":                             # KS-16c: thay tệp là hiện luôn
        x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do_tra_lai = "da_duyet", "tu_dong", now or datetime.now(), ""
    x.sua_boi, x.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(x)
    return x


def gui_duyet(db: Session, u: User, nid: int, ids: list[int] | None = None, now: datetime | None = None) -> int:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing gửi duyệt ảnh")
    n = 0
    for x in _anh_cua(db, nid):
        if x.trang_thai == "nhap" and (not ids or x.id in ids):
            x.trang_thai, x.ly_do_tra_lai = "cho_duyet", ""
            x.sua_boi, x.sua_luc = u.username, now or datetime.now()
            n += 1
    db.commit()
    return n


def _ly_do_khong_duyet(u: User, x: AnhNhaHang) -> str:
    if x.trang_thai != "cho_duyet":
        return "Ảnh không ở trạng thái chờ duyệt"
    # Chủ tịch 29/10/2026: bỏ chặn theo «căn cứ quyền dùng» — căn cứ / nguồn chỉ còn là ghi chú nội bộ, không
    # chặn duyệt, không chặn ra cổng. Vẫn giữ quy tắc hai người (người tải / sửa không tự duyệt).
    if not x.nhom:
        return "Chưa chọn nhóm ảnh"
    if u.role not in TOAN_QUYEN and u.username in {x.tai_boi, x.sua_boi} - {""}:
        return "Người tải / sửa ảnh không tự duyệt — nhờ TP Điều hành khác, Chủ tịch hoặc TGĐ"
    return ""


def duyet_anh(db: Session, u: User, ids: list[int], duyet: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    """TP Điều hành duyệt / trả lại nhiều ảnh. Ảnh không đủ điều kiện thì bỏ qua, nói rõ vì sao."""
    if not _co(u, VAI_DUYET_ANH):
        raise LoiNhaHang("Chỉ TP Điều hành (hoặc Chủ tịch, TGĐ) duyệt ảnh")
    ly_do = (ly_do or "").strip()
    if not duyet and len(ly_do) < 3:
        raise LoiNhaHang("Trả lại phải ghi lý do")
    now = now or datetime.now()
    ok, bo = 0, []
    for pid in ids[:300]:
        x = db.get(AnhNhaHang, int(pid))
        if x is None:
            continue
        if duyet:
            loi = _ly_do_khong_duyet(u, x)
            if loi:
                bo.append({"id": x.id, "ly_do": loi}); continue
            x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do_tra_lai = "da_duyet", u.username, now, ""
        else:
            if x.trang_thai not in ("cho_duyet", "da_duyet"):
                bo.append({"id": x.id, "ly_do": "Ảnh không ở trạng thái chờ duyệt / đã duyệt"}); continue
            x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do_tra_lai = "nhap", "", None, ly_do[:300]
        ok += 1
    db.commit()
    return {"da_doi": ok, "bo_qua": bo}


def an_anh(db: Session, u: User, pid: int, an: bool, now: datetime | None = None) -> AnhNhaHang:
    """Ẩn: thôi hiện ở mọi nơi, tệp vẫn trong kho. Bỏ ẩn: về «Nháp» (phải gửi duyệt lại)."""
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing ẩn ảnh nhà hàng")
    x = _lay_anh(db, pid)
    if an:
        x.trang_thai, x.la_bia = "an", False
    elif x.trang_thai == "an":
        x.trang_thai, x.duyet_boi, x.duyet_luc = "da_duyet", "tu_dong", now or datetime.now()   # KS-16c
    x.sua_boi, x.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(x)
    return x


def xoa_anh(db: Session, u: User, pid: int) -> int:
    """KS-16c (Chủ tịch 31/10/2026): ai tải ảnh người đó tự xóa; TP Điều hành (và Chủ tịch, TGĐ) xóa mọi ảnh.
    Món đang dùng ảnh này thì bỏ gắn ảnh. Tệp vẫn trong kho chứng từ."""
    from app.models.nha_hang import MonNhaHang
    from app.services import rules as R
    x = _lay_anh(db, pid)
    if x.tai_boi != u.username and not _co(u, VAI_DUYET_ANH):
        raise LoiNhaHang("Chỉ người tải ảnh hoặc TP Điều hành xóa ảnh này")
    nid = x.nha_hang_id
    for m in db.execute(select(MonNhaHang).where(MonNhaHang.anh_id == x.id)).scalars().all():
        m.anh_id = None
    R.audit(db, u.username, u.role, "nha_hang_xoa_anh", f"nha_hang:{nid}", before={"anh": x.id, "tai_boi": x.tai_boi})
    db.delete(x)
    db.commit()
    return nid


def dat_bia(db: Session, u: User, pid: int) -> AnhNhaHang:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing chọn ảnh bìa")
    x = _lay_anh(db, pid)
    if x.trang_thai == "an":
        raise LoiNhaHang("Ảnh đang ẩn — bỏ ẩn trước")
    for y in _anh_cua(db, x.nha_hang_id):
        y.la_bia = y.id == x.id
    db.commit(); db.refresh(x)
    return x


def xep_anh(db: Session, u: User, nid: int, ids: list[int]) -> None:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing đổi thứ tự ảnh")
    ds = {x.id: x for x in _anh_cua(db, nid)}
    if set(int(i) for i in ids) != set(ds):
        raise LoiNhaHang("Danh sách ảnh không khớp album — tải lại trang rồi xếp lại")
    for i, pid in enumerate(ids, 1):
        ds[int(pid)].thu_tu = i
    db.commit()


def anh_cho_duyet(db: Session, u: User) -> dict:
    from app.models.attachments import Attachment
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    ds = db.execute(select(AnhNhaHang).where(AnhNhaHang.trang_thai == "cho_duyet").order_by(AnhNhaHang.nha_hang_id, AnhNhaHang.thu_tu)).scalars().all()
    nh = {n.id: n for n in db.execute(select(NhaHang).where(NhaHang.id.in_({x.nha_hang_id for x in ds}))).scalars()} if ds else {}
    goc = {a.id: a for a in db.execute(select(Attachment).where(Attachment.id.in_([x.attachment_id for x in ds]))).scalars()} if ds else {}
    return {"anh": [{**_anh_out(x, goc.get(x.attachment_id)), "nha_hang_ten": nh[x.nha_hang_id].ten if x.nha_hang_id in nh else "",
                     "khong_duyet": _ly_do_khong_duyet(u, x)} for x in ds],
            "duoc_duyet": _co(u, VAI_DUYET_ANH)}


def hoan_thien_anh(db: Session) -> dict[int, dict]:
    """Mức hoàn thiện ảnh từng nhà hàng cho cột danh sách VTOS (AT-2b: thêm số món đã duyệt, món / thực đơn chờ duyệt)."""
    from app.models.nha_hang import MonNhaHang, ThucDonBan
    ra: dict[int, dict] = {}
    goc = lambda nid: ra.setdefault(nid, {"da_duyet": 0, "cho_duyet": 0, "nhap": 0, "an": 0, "co_bia": False,  # noqa: E731
                                          "mon": 0, "td": 0, "nd_cho": 0})
    for m in db.execute(select(MonNhaHang)).scalars():
        if m.trang_thai == "da_duyet":
            goc(m.nha_hang_id)["mon"] += 1
        elif m.trang_thai == "cho_duyet":
            goc(m.nha_hang_id)["nd_cho"] += 1
    for b in db.execute(select(ThucDonBan)).scalars():
        if b.trang_thai == "duyet":
            goc(b.nha_hang_id)["td"] += 1
        elif b.trang_thai == "cho_duyet":
            goc(b.nha_hang_id)["nd_cho"] += 1
    for x in db.execute(select(AnhNhaHang)).scalars():
        o = goc(x.nha_hang_id)
        o[x.trang_thai] = o.get(x.trang_thai, 0) + 1
        if x.la_bia and x.trang_thai == "da_duyet":
            o["co_bia"] = True
    return ra


def album_cong(db: Session, nids: list[int]) -> dict[int, list[AnhNhaHang]]:
    """Ảnh ĐÃ DUYỆT (căn cứ đã xác minh) theo nhà hàng — ảnh bìa đứng đầu, rồi theo thứ tự."""
    if not nids:
        return {}
    ra: dict[int, list] = {}
    for x in db.execute(select(AnhNhaHang).where(AnhNhaHang.nha_hang_id.in_(nids), AnhNhaHang.trang_thai == "da_duyet")
                        .order_by(AnhNhaHang.thu_tu, AnhNhaHang.id)).scalars():
        ra.setdefault(x.nha_hang_id, []).append(x)
    for v in ra.values():
        v.sort(key=lambda x: not x.la_bia)
    return ra


def _anh_cong_out(x: AnhNhaHang) -> dict:
    return {"id": x.id, "nhom": x.nhom, "nhom_ten": NHOM_ANH.get(x.nhom, ""), "chu_thich": x.chu_thich,
            "alt": x.mo_ta_thay_the or x.chu_thich, "credit": x.credit, "rong": x.rong, "cao": x.cao,
            "nho": f"/api/v1/am-thuc/anh/nh/{x.id}/nho", "hien": f"/api/v1/am-thuc/anh/nh/{x.id}/hien"}


def tep_album(db: Session, u: User | None, pid: int, co: str):
    """Tệp ảnh album. u=None: cổng công khai — chỉ ảnh đã duyệt của nhà hàng đang hiện, không bao giờ bản gốc."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    x = db.get(AnhNhaHang, pid)
    if x is None or co not in ("nho", "hien", "goc"):
        raise LoiNhaHang("Không có ảnh này")
    if u is None:
        nh = db.get(NhaHang, x.nha_hang_id)
        if co == "goc" or x.trang_thai != "da_duyet" or nh is None or not nh.hien_cong or nh.ngung:
            raise LoiNhaHang("Không có ảnh này")
    elif not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    aid = {"nho": x.nho_id or x.hien_id or x.attachment_id, "hien": x.hien_id or x.attachment_id, "goc": x.attachment_id}[co]
    a = db.get(Attachment, aid)
    return AT.doc(db, a), a


# ══ AT-2b · MÓN ĂN VÀ THỰC ĐƠN (Chủ tịch chốt 29/10/2026) ═══════════════════════════════════════════════════
from app.models.nha_hang import (MonNhaHang, ThucDonBan, ThucDonTrang, NHOM_MON_NH, DI_UNG,  # noqa: E402
                                 LOAI_THUC_DON)

MON_TOI_DA, MON_NOI_BAT_TOI_DA = 40, 6
TD_TOI_DA_TRANG = 20
TRUONG_MON_DUYET_LAI = ("ten", "ten_khac", "mo_ta", "di_ung", "cay", "chay", "anh_id")


def _mon_out(x: MonNhaHang, anh: AnhNhaHang | None, cong: bool = False) -> dict:
    o = {"id": x.id, "ten": x.ten, "ten_khac": x.ten_khac, "nhom": x.nhom, "nhom_ten": NHOM_MON_NH.get(x.nhom, x.nhom),
         "mo_ta": x.mo_ta, "di_ung": list(x.di_ung or []), "di_ung_ten": [DI_UNG[k] for k in (x.di_ung or []) if k in DI_UNG],
         "cay": x.cay, "chay": x.chay, "noi_bat": x.noi_bat, "thu_tu": x.thu_tu}
    if cong:
        ok = anh is not None and anh.trang_thai == "da_duyet"
        o["anh"] = f"/api/v1/am-thuc/anh/nh/{anh.id}/hien" if ok else None
        o["anh_nho"] = f"/api/v1/am-thuc/anh/nh/{anh.id}/nho" if ok else None
    else:
        o.update({"anh_id": x.anh_id, "anh_nho": f"/api/v1/nha-hang/album/{x.anh_id}/nho" if x.anh_id else None,
                  "anh_da_duyet": bool(anh and anh.trang_thai == "da_duyet"),
                  "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_ANH.get(x.trang_thai, x.trang_thai),
                  "ly_do_tra_lai": x.ly_do_tra_lai, "tao_boi": x.tao_boi, "sua_boi": x.sua_boi, "duyet_boi": x.duyet_boi})
    return o


def _mon_cua(db: Session, nid: int) -> list[MonNhaHang]:
    return db.execute(select(MonNhaHang).where(MonNhaHang.nha_hang_id == nid)
                      .order_by(MonNhaHang.noi_bat.desc(), MonNhaHang.thu_tu, MonNhaHang.id)).scalars().all()


def ds_mon(db: Session, u: User, nid: int) -> dict:
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    ds = _mon_cua(db, nid)
    anh = {a.id: a for a in db.execute(select(AnhNhaHang).where(AnhNhaHang.id.in_([m.anh_id for m in ds if m.anh_id]))).scalars()}
    return {"mon": [_mon_out(m, anh.get(m.anh_id)) for m in ds], "nhom_mon": NHOM_MON_NH, "di_ung": DI_UNG,
            "toi_da": MON_TOI_DA, "noi_bat_toi_da": MON_NOI_BAT_TOI_DA, "duoc_sua": _co(u, VAI_ANH_NH),
            "duoc_duyet": _co(u, VAI_DUYET_ANH)}


def luu_mon(db: Session, u: User, nid: int, d: dict, mid: int | None = None, now: datetime | None = None) -> MonNhaHang:
    """Thêm / sửa món. Không có trường giá (giá chỉ ở thực đơn). Sửa chữ / dị ứng / ảnh của món đã duyệt → «Chờ duyệt»."""
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing sửa món ăn")
    now = now or datetime.now()
    if db.get(NhaHang, nid) is None:
        raise LoiNhaHang("Không có nhà hàng này")
    ten = (d.get("ten") or "").strip()
    if not ten:
        raise LoiNhaHang("Ghi tên món")
    nhom = d.get("nhom") or "mon_chinh"
    if nhom not in NHOM_MON_NH:
        raise LoiNhaHang("Nhóm món không hợp lệ")
    di = [k for k in dict.fromkeys(d.get("di_ung") or [])]
    if any(k not in DI_UNG for k in di):
        raise LoiNhaHang("Thành phần dị ứng không hợp lệ")
    aid = d.get("anh_id") or None
    if aid is not None:
        a = db.get(AnhNhaHang, int(aid))
        if a is None or a.nha_hang_id != nid:
            raise LoiNhaHang("Ảnh món phải là ảnh trong album của chính nhà hàng này")
        aid = a.id
    ds = _mon_cua(db, nid)
    if mid:
        x = db.get(MonNhaHang, mid)
        if x is None or x.nha_hang_id != nid:
            raise LoiNhaHang("Món không thuộc nhà hàng này")
    else:
        if len(ds) >= MON_TOI_DA:
            raise LoiNhaHang(f"Đã đủ {MON_TOI_DA} món — ẩn bớt món cũ trước")
        x = MonNhaHang(nha_hang_id=nid, ten=ten, tao_boi=u.username, tao_luc=now, trang_thai="nhap",
                       thu_tu=max([m.thu_tu for m in ds], default=0) + 1, noi_bat=False, cay=False, chay=False, di_ung=[])
        db.add(x)
    moi = {"ten": ten[:160], "ten_khac": (d.get("ten_khac") or "").strip()[:160], "mo_ta": (d.get("mo_ta") or "").strip()[:500],
           "di_ung": di, "cay": bool(d.get("cay")), "chay": bool(d.get("chay")), "anh_id": aid}
    duyet_lai = bool(mid) and x.trang_thai == "da_duyet" and any(
        (list(getattr(x, k) or []) if k == "di_ung" else getattr(x, k)) != moi[k] for k in TRUONG_MON_DUYET_LAI)
    for k, v in moi.items():
        setattr(x, k, v)
    x.nhom = nhom
    if duyet_lai:
        x.trang_thai, x.duyet_boi, x.duyet_luc = "cho_duyet", "", None
    x.sua_boi, x.sua_luc = u.username, now
    db.commit(); db.refresh(x)
    return x


def mon_noi_bat(db: Session, u: User, mid: int, bat: bool) -> MonNhaHang:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing chọn món nổi bật")
    x = db.get(MonNhaHang, mid)
    if x is None:
        raise LoiNhaHang("Không có món này")
    if bat and not x.noi_bat and sum(1 for m in _mon_cua(db, x.nha_hang_id) if m.noi_bat) >= MON_NOI_BAT_TOI_DA:
        raise LoiNhaHang(f"Tối đa {MON_NOI_BAT_TOI_DA} món nổi bật — bỏ ★ một món khác trước")
    x.noi_bat = bool(bat)
    db.commit(); db.refresh(x)
    return x


def an_mon(db: Session, u: User, mid: int, an: bool) -> MonNhaHang:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing ẩn món")
    x = db.get(MonNhaHang, mid)
    if x is None:
        raise LoiNhaHang("Không có món này")
    if an:
        x.trang_thai, x.noi_bat = "an", False
    elif x.trang_thai == "an":
        x.trang_thai, x.duyet_boi, x.duyet_luc = "nhap", "", None
    x.sua_boi, x.sua_luc = u.username, datetime.now()
    db.commit(); db.refresh(x)
    return x


def gui_duyet_mon(db: Session, u: User, nid: int) -> int:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing gửi duyệt món")
    n = 0
    for x in _mon_cua(db, nid):
        if x.trang_thai == "nhap":
            x.trang_thai, x.ly_do_tra_lai, x.sua_boi, x.sua_luc = "cho_duyet", "", u.username, datetime.now()
            n += 1
    db.commit()
    return n


def duyet_mon(db: Session, u: User, ids: list[int], duyet: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    if not _co(u, VAI_DUYET_ANH):
        raise LoiNhaHang("Chỉ TP Điều hành (hoặc Chủ tịch, TGĐ) duyệt món")
    ly_do = (ly_do or "").strip()
    if not duyet and len(ly_do) < 3:
        raise LoiNhaHang("Trả lại phải ghi lý do")
    now = now or datetime.now()
    ok, bo = 0, []
    for mid in ids[:300]:
        x = db.get(MonNhaHang, int(mid))
        if x is None:
            continue
        if x.trang_thai != "cho_duyet" and not (not duyet and x.trang_thai == "da_duyet"):
            bo.append({"id": x.id, "ly_do": "Món không ở trạng thái chờ duyệt"}); continue
        if duyet and u.role not in TOAN_QUYEN and u.username in {x.tao_boi, x.sua_boi} - {""}:
            bo.append({"id": x.id, "ly_do": "Người thêm / sửa món không tự duyệt — nhờ TP Điều hành khác, Chủ tịch hoặc TGĐ"}); continue
        if duyet:
            x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do_tra_lai = "da_duyet", u.username, now, ""
        else:
            x.trang_thai, x.duyet_boi, x.duyet_luc, x.ly_do_tra_lai = "nhap", "", None, ly_do[:300]
        ok += 1
    db.commit()
    return {"da_doi": ok, "bo_qua": bo}


def mon_cong(db: Session, nid: int) -> list[dict]:
    ds = [m for m in _mon_cua(db, nid) if m.trang_thai == "da_duyet"]
    anh = {a.id: a for a in db.execute(select(AnhNhaHang).where(AnhNhaHang.id.in_([m.anh_id for m in ds if m.anh_id]))).scalars()}
    return [_mon_out(m, anh.get(m.anh_id), cong=True) for m in ds]


# ── thực đơn theo phiên bản ─────────────────────────────────────────────────────────────────────
def _ten_ban(so: int) -> str:
    return f"v1.{so - 1}"


def _tach_pdf(data: bytes) -> list[bytes]:
    """PDF → danh sách trang PNG (150 dpi). Lỗi / quá trang → LoiNhaHang."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise LoiNhaHang("Máy chủ chưa đọc được PDF — tải thực đơn dạng ảnh JPG / PNG")
    from io import BytesIO
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception:
        raise LoiNhaHang("Tệp PDF không mở được")
    try:
        if len(pdf) > TD_TOI_DA_TRANG:
            raise LoiNhaHang(f"PDF có {len(pdf)} trang, quá {TD_TOI_DA_TRANG} trang mỗi bản")
        ra = []
        for i in range(len(pdf)):
            im = pdf[i].render(scale=150 / 72).to_pil()
            o = BytesIO(); im.convert("RGB").save(o, "JPEG", quality=88); ra.append(o.getvalue())
        return ra
    finally:
        pdf.close()


def _ban_hien_hanh(bans: list[ThucDonBan], hn: date) -> ThucDonBan | None:
    ok = [b for b in bans if b.trang_thai == "duyet" and b.hieu_luc_tu <= hn]
    return max(ok, key=lambda b: (b.hieu_luc_tu, b.so)) if ok else None


def _trang_cua(db: Session, ban_ids: list[int]) -> dict[int, list[ThucDonTrang]]:
    ra: dict[int, list] = {}
    if ban_ids:
        for t in db.execute(select(ThucDonTrang).where(ThucDonTrang.ban_id.in_(ban_ids)).order_by(ThucDonTrang.thu_tu)).scalars():
            ra.setdefault(t.ban_id, []).append(t)
    return ra


def ds_thuc_don(db: Session, u: User, nid: int) -> dict:
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    hn = _hom_nay()
    bans = db.execute(select(ThucDonBan).where(ThucDonBan.nha_hang_id == nid).order_by(ThucDonBan.loai, ThucDonBan.so.desc())).scalars().all()
    tr = _trang_cua(db, [b.id for b in bans])
    ra = {}
    for loai, ten in LOAI_THUC_DON.items():
        bl = [b for b in bans if b.loai == loai]
        hh = _ban_hien_hanh(bl, hn)
        ra[loai] = {"ten": ten, "hien_hanh": hh.id if hh else None, "ban": [
            {"id": b.id, "ten": _ten_ban(b.so), "hieu_luc_tu": b.hieu_luc_tu.isoformat(), "can_cu": b.can_cu, "so_trang": b.so_trang,
             "trang_thai": ("dang_dung" if hh and b.id == hh.id else
                            "cho_hieu_luc" if b.trang_thai == "duyet" and b.hieu_luc_tu > hn else
                            "da_thay" if b.trang_thai == "duyet" else b.trang_thai),
             "ly_do_tra_lai": b.ly_do_tra_lai, "tai_boi": b.tai_boi, "duyet_boi": b.duyet_boi,
             "trang": [{"id": t.id, "nho": f"/api/v1/nha-hang/thuc-don/trang/{t.id}/nho", "hien": f"/api/v1/nha-hang/thuc-don/trang/{t.id}/hien",
                        "goc": f"/api/v1/nha-hang/thuc-don/trang/{t.id}/goc"} for t in tr.get(b.id, [])]} for b in bl]}
    return {"loai": ra, "toi_da_trang": TD_TOI_DA_TRANG, "toi_da_mb": ANH_TOI_DA_MB, "duoc_tai": _co(u, VAI_ANH_NH),
            "duoc_duyet": _co(u, VAI_DUYET_ANH)}


def tai_thuc_don(db: Session, u: User, nid: int, loai: str, tep: list[tuple[str, bytes]], hieu_luc_tu, can_cu: str,
                 now: datetime | None = None) -> ThucDonBan:
    """Tải MỘT phiên bản mới: nhiều ảnh (mỗi ảnh một trang) hoặc một PDF (máy tách trang). Vào «Chờ duyệt»."""
    from app.services import attachments as AT
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành hoặc Marketing tải thực đơn")
    now = now or datetime.now()
    nh = db.get(NhaHang, nid)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    if loai not in LOAI_THUC_DON:
        raise LoiNhaHang("Chọn loại thực đơn: gọi món, set menu, buffet hoặc khách đoàn")
    can_cu = (can_cu or "").strip()
    if len(can_cu) < 5:
        raise LoiNhaHang("Ghi căn cứ: ai gửi thực đơn, qua kênh nào, ngày nào")
    hl = _ngay(hieu_luc_tu) or _hom_nay()
    if not tep:
        raise LoiNhaHang("Chọn tệp thực đơn (ảnh hoặc PDF)")
    trang: list[tuple[str, bytes, bytes | None]] = []        # (tên, bytes gốc, bytes ảnh trang nếu tách từ PDF)
    goc_pdf = None
    for ten, data in tep:
        mb = len(data) / 1024 / 1024
        if mb > ANH_TOI_DA_MB:
            raise LoiNhaHang(f"«{ten}» nặng {mb:.1f} MB, quá {ANH_TOI_DA_MB} MB")
        duoi = (ten or "").rsplit(".", 1)[-1].lower() if "." in (ten or "") else ""
        if duoi == "pdf":
            if len(tep) > 1:
                raise LoiNhaHang("Một bản thực đơn: hoặc MỘT tệp PDF, hoặc nhiều ảnh — không trộn")
            goc_pdf = (ten, data)
            for i, b in enumerate(_tach_pdf(data), 1):
                trang.append((f"{ten}.trang{i}.jpg", b, None))
        elif duoi in KIEU_ANH:
            trang.append((ten, data, None))
        else:
            raise LoiNhaHang(f"«{ten}»: chỉ nhận PDF hoặc ảnh JPG / PNG / WEBP")
    if len(trang) > TD_TOI_DA_TRANG:
        raise LoiNhaHang(f"{len(trang)} trang, quá {TD_TOI_DA_TRANG} trang mỗi bản")
    cu = db.execute(select(func.max(ThucDonBan.so)).where(ThucDonBan.nha_hang_id == nid, ThucDonBan.loai == loai)).scalar() or 0
    b = ThucDonBan(nha_hang_id=nid, loai=loai, so=cu + 1, hieu_luc_tu=hl, can_cu=can_cu[:300], so_trang=len(trang),
                   trang_thai="cho_duyet", tai_boi=u.username, tai_luc=now)
    db.add(b); db.flush()
    ma = f"td{nid}"
    try:
        a_pdf = AT.dinh_kem(db, "am_thuc", ma, goc_pdf[0], goc_pdf[1], kieu="application/pdf", loai="hinh_anh",
                            mo_ta=f"Thực đơn {nh.ma} {LOAI_THUC_DON[loai]} {_ten_ban(b.so)} (PDF gốc)", boi=u.username)[0] if goc_pdf else None
        for i, (ten, data, _x) in enumerate(trang, 1):
            hien, nho, _r, _c = _lam_nhe(data)
            if hien is None and _co_pil():
                raise LoiNhaHang(f"«{ten}» không mở được như một ảnh")
            duoi = ten.rsplit(".", 1)[-1].lower()
            a = a_pdf or AT.dinh_kem(db, "am_thuc", ma, ten, data, kieu=KIEU_ANH.get(duoi, "image/jpeg"), loai="hinh_anh",
                                     mo_ta=f"Thực đơn {nh.ma} {_ten_ban(b.so)} trang {i}", boi=u.username)[0]
            ah = AT.dinh_kem(db, "am_thuc", ma, f"{ten}.hien.webp", hien, kieu="image/webp", loai="hinh_anh", boi=u.username,
                             nguon="he_thong", mo_ta=f"Trang {i} · {_ten_ban(b.so)}")[0] if hien else None
            an = AT.dinh_kem(db, "am_thuc", ma, f"{ten}.nho.webp", nho, kieu="image/webp", loai="hinh_anh", boi=u.username,
                             nguon="he_thong", mo_ta=f"Trang {i} nhỏ · {_ten_ban(b.so)}")[0] if nho else None
            if hien is None and a_pdf is not None:      # không có thư viện ảnh: lưu chính trang đã tách làm bản hiển thị
                ah = AT.dinh_kem(db, "am_thuc", ma, ten, data, kieu="image/jpeg", loai="hinh_anh", boi=u.username, nguon="he_thong")[0]
            db.add(ThucDonTrang(ban_id=b.id, thu_tu=i, attachment_id=a.id, hien_id=ah.id if ah else a.id,
                                nho_id=an.id if an else (ah.id if ah else a.id)))
    except ValueError as ex:
        db.rollback()
        raise LoiNhaHang(str(ex))
    except LoiNhaHang:
        db.rollback()
        raise
    db.commit(); db.refresh(b)
    return b


def duyet_thuc_don(db: Session, u: User, bid: int, duyet: bool, ly_do: str = "", now: datetime | None = None) -> ThucDonBan:
    if not _co(u, VAI_DUYET_ANH):
        raise LoiNhaHang("Chỉ TP Điều hành (hoặc Chủ tịch, TGĐ) duyệt thực đơn")
    b = db.get(ThucDonBan, bid)
    if b is None:
        raise LoiNhaHang("Không có bản thực đơn này")
    if b.trang_thai != "cho_duyet":
        raise LoiNhaHang("Bản này không ở trạng thái chờ duyệt")
    if duyet:
        if u.role not in TOAN_QUYEN and u.username == b.tai_boi:
            raise LoiNhaHang("Người tải thực đơn không tự duyệt — nhờ TP Điều hành khác, Chủ tịch hoặc TGĐ")
        b.trang_thai, b.duyet_boi, b.duyet_luc = "duyet", u.username, now or datetime.now()
    else:
        if len((ly_do or "").strip()) < 3:
            raise LoiNhaHang("Trả lại phải ghi lý do")
        b.trang_thai, b.ly_do_tra_lai = "tra_lai", ly_do.strip()[:300]
    db.commit(); db.refresh(b)
    return b


def thuc_don_cong(db: Session, nid: int) -> list[dict]:
    hn = _hom_nay()
    bans = db.execute(select(ThucDonBan).where(ThucDonBan.nha_hang_id == nid, ThucDonBan.trang_thai == "duyet")).scalars().all()
    hh = {loai: _ban_hien_hanh([b for b in bans if b.loai == loai], hn) for loai in LOAI_THUC_DON}
    tr = _trang_cua(db, [b.id for b in hh.values() if b])
    return [{"loai": loai, "ten": LOAI_THUC_DON[loai], "ban": _ten_ban(b.so), "hieu_luc_tu": b.hieu_luc_tu.isoformat(),
             "trang": [{"hien": f"/api/v1/am-thuc/anh/td/{t.id}/hien", "nho": f"/api/v1/am-thuc/anh/td/{t.id}/nho"} for t in tr.get(b.id, [])]}
            for loai, b in hh.items() if b]


def tep_trang(db: Session, u: User | None, tid: int, co: str):
    """Trang thực đơn. u=None (cổng): chỉ trang của bản ĐANG DÙNG, nhà hàng đang hiện; không bao giờ tệp gốc."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    t = db.get(ThucDonTrang, tid)
    if t is None or co not in ("nho", "hien", "goc"):
        raise LoiNhaHang("Không có trang này")
    b = db.get(ThucDonBan, t.ban_id)
    if u is None:
        nh = db.get(NhaHang, b.nha_hang_id)
        hh = _ban_hien_hanh(db.execute(select(ThucDonBan).where(ThucDonBan.nha_hang_id == b.nha_hang_id, ThucDonBan.loai == b.loai))
                            .scalars().all(), _hom_nay())
        if co == "goc" or hh is None or hh.id != b.id or nh is None or not nh.hien_cong or nh.ngung:
            raise LoiNhaHang("Không có trang này")
    elif not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    a = db.get(Attachment, {"nho": t.nho_id or t.hien_id or t.attachment_id, "hien": t.hien_id or t.attachment_id, "goc": t.attachment_id}[co])
    return AT.doc(db, a), a


def cho_duyet_noi_dung(db: Session, u: User) -> dict:
    """Món và thực đơn chờ TP Điều hành duyệt (ảnh: anh_cho_duyet)."""
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    mons = db.execute(select(MonNhaHang).where(MonNhaHang.trang_thai == "cho_duyet").order_by(MonNhaHang.nha_hang_id, MonNhaHang.thu_tu)).scalars().all()
    bans = db.execute(select(ThucDonBan).where(ThucDonBan.trang_thai == "cho_duyet").order_by(ThucDonBan.nha_hang_id)).scalars().all()
    nh = {n.id: n.ten for n in db.execute(select(NhaHang).where(NhaHang.id.in_({m.nha_hang_id for m in mons} | {b.nha_hang_id for b in bans}))).scalars()}
    anh = {a.id: a for a in db.execute(select(AnhNhaHang).where(AnhNhaHang.id.in_([m.anh_id for m in mons if m.anh_id]))).scalars()}
    tr = _trang_cua(db, [b.id for b in bans])
    return {"mon": [{**_mon_out(m, anh.get(m.anh_id)), "nha_hang_ten": nh.get(m.nha_hang_id, ""),
                     "khong_duyet": ("Người thêm / sửa món không tự duyệt" if u.role not in TOAN_QUYEN and u.username in {m.tao_boi, m.sua_boi} - {""} else "")}
                    for m in mons],
            "thuc_don": [{"id": b.id, "nha_hang_ten": nh.get(b.nha_hang_id, ""), "loai_ten": LOAI_THUC_DON.get(b.loai, b.loai),
                          "ten": _ten_ban(b.so), "hieu_luc_tu": b.hieu_luc_tu.isoformat(), "can_cu": b.can_cu, "so_trang": b.so_trang,
                          "tai_boi": b.tai_boi, "trang_dau": f"/api/v1/nha-hang/thuc-don/trang/{tr[b.id][0].id}/nho" if tr.get(b.id) else None,
                          "khong_duyet": ("Người tải không tự duyệt" if u.role not in TOAN_QUYEN and u.username == b.tai_boi else "")}
                         for b in bans],
            "duoc_duyet": _co(u, VAI_DUYET_ANH)}


# ══ AT-2c · BIÊN TẬP VÀ MỨC HOÀN THIỆN (Chủ tịch chốt 29/10/2026) ═══════════════════════════════════════════
# Trọng số Chủ tịch duyệt: bìa 20, album 20, món 15, thực đơn 15, giới thiệu 15, liên hệ 15. ≥ 80% = «đủ».
# Chỉ tính thứ đã DUYỆT. Giao việc: CHỈ Chủ tịch; người nhận là NV Điều hành / NV Marketing.
# Trang khách: nơi dưới 50% xếp xuống cuối (không ẩn).
from app.models.nha_hang import BienTapNhaHang  # noqa: E402

VAI_GIAO_BIEN_TAP = ("chutich",)
VAI_NHAN_BIEN_TAP = ("nv_dh", "nv_mkt")
NGUONG_DU, NGUONG_THIEU = 80, 50
ALBUM_TOI_THIEU, MON_TOI_THIEU, GIOI_THIEU_TOI_THIEU = 5, 3, 300
# AT-3 (Chủ tịch duyệt 29/10/2026): thêm «Đánh giá khách» 10 — album 20 → 15, giới thiệu 15 → 10; tổng vẫn 100.
MUC_HT = (("bia", "Ảnh bìa đã duyệt", 20, "album"), ("album", "Album ảnh", 15, "album"), ("mon", "Món ăn có ảnh", 15, "mon"),
          ("thuc_don", "Thực đơn đang dùng", 15, "tdnh"), ("gioi_thieu", "Giới thiệu VTD viết", 10, "gt"),
          ("lien_he", "Liên hệ, giờ mở cửa, khu vực", 15, "tt"), ("danh_gia", "Đánh giá khách", 10, "dg"))
DANH_GIA_TOI_THIEU = 3          # chấm theo SỐ bài đang hiện, không theo số sao


def _cham(n: NhaHang, anh: list, mons: list, co_td: bool, so_dg: int = 0) -> dict:
    """Chấm MỘT nhà hàng từ dữ liệu đã duyệt. Trả {"diem", "muc": [...]}."""
    duyet = [a for a in anh if a.trang_thai == "da_duyet"]
    nhom = {a.nhom for a in duyet if a.nhom}
    co_bia = any(a.la_bia for a in duyet)
    so_mon = sum(1 for m in mons if m["anh_ok"])
    gt_dai, co_mnb = len((n.mo_ta or "").strip()), bool((n.mon_noi_bat or "").strip())
    lh = [bool(n.lien_he_xac_minh), bool((n.gio_phuc_vu or "").strip()), bool((n.khu_vuc or "").strip())]
    ty = {"bia": 1.0 if co_bia else 0.0,
          "album": min(len(duyet), ALBUM_TOI_THIEU) / ALBUM_TOI_THIEU * (1.0 if len(nhom) >= 2 or len(duyet) == 0 else 0.75),
          "mon": min(so_mon, MON_TOI_THIEU) / MON_TOI_THIEU,
          "thuc_don": 1.0 if co_td else 0.0,
          "gioi_thieu": (0.5 if gt_dai >= GIOI_THIEU_TOI_THIEU else min(gt_dai, GIOI_THIEU_TOI_THIEU) / GIOI_THIEU_TOI_THIEU * 0.5) + (0.5 if co_mnb else 0.0),
          "lien_he": sum(lh) / 3,
          "danh_gia": min(so_dg, DANH_GIA_TOI_THIEU) / DANH_GIA_TOI_THIEU}
    chi_tiet = {"bia": "Có ảnh bìa đã duyệt" if co_bia else ("Ảnh bìa chưa duyệt" if any(a.la_bia for a in anh) else "Chưa chọn ảnh bìa"),
                "album": f"{len(duyet)}/{ALBUM_TOI_THIEU} ảnh đã duyệt · {len(nhom)} nhóm",
                "mon": f"{so_mon}/{MON_TOI_THIEU} món đã duyệt có ảnh",
                "thuc_don": "Có thực đơn đang dùng" if co_td else "Chưa có thực đơn đang dùng",
                "gioi_thieu": f"{gt_dai}/{GIOI_THIEU_TOI_THIEU} ký tự · " + ("có món nổi bật" if co_mnb else "chưa có món nổi bật"),
                "lien_he": ", ".join(t for ok, t in zip(lh, ("liên hệ đã xác minh", "có giờ mở cửa", "có khu vực")) if ok) or "Chưa có",
                "danh_gia": f"{so_dg}/{DANH_GIA_TOI_THIEU} bài khách đã đến ăn (không xét số sao)"}
    muc = [{"ma": ma, "ten": ten, "diem_toi_da": w, "diem": round(w * ty[ma], 1), "dat": ty[ma] >= 0.999, "chi_tiet": chi_tiet[ma], "tab": tab}
           for ma, ten, w, tab in MUC_HT]
    return {"diem": int(round(sum(m["diem"] for m in muc))), "muc": muc}


def _muc_do(diem: int) -> str:
    return "du" if diem >= NGUONG_DU else "dang" if diem >= NGUONG_THIEU else "thieu"


def diem_hoan_thien(db: Session, nids: list[int] | None = None) -> dict[int, dict]:
    """Điểm hoàn thiện mọi nhà hàng (hoặc các nid). Tính lại mỗi lần đọc."""
    cau = select(NhaHang)
    if nids is not None:
        if not nids:
            return {}
        cau = cau.where(NhaHang.id.in_(nids))
    nhs = db.execute(cau).scalars().all()
    ids = [n.id for n in nhs]
    anh: dict[int, list] = {}
    for a in db.execute(select(AnhNhaHang).where(AnhNhaHang.nha_hang_id.in_(ids))).scalars():
        anh.setdefault(a.nha_hang_id, []).append(a)
    ok_anh = {a.id for v in anh.values() for a in v if a.trang_thai == "da_duyet"}
    mons: dict[int, list] = {}
    for m in db.execute(select(MonNhaHang).where(MonNhaHang.nha_hang_id.in_(ids), MonNhaHang.trang_thai == "da_duyet")).scalars():
        mons.setdefault(m.nha_hang_id, []).append({"anh_ok": m.anh_id in ok_anh})
    hn = _hom_nay()
    td: set[int] = set()
    bans: dict[tuple, list] = {}
    for b in db.execute(select(ThucDonBan).where(ThucDonBan.nha_hang_id.in_(ids), ThucDonBan.trang_thai == "duyet")).scalars():
        bans.setdefault((b.nha_hang_id, b.loai), []).append(b)
    for (nid, _l), bl in bans.items():
        if _ban_hien_hanh(bl, hn):
            td.add(nid)
    from app.models.nha_hang import DanhGiaNhaHang
    dg: dict[int, int] = {}
    for x in db.execute(select(DanhGiaNhaHang.nha_hang_id).where(DanhGiaNhaHang.nha_hang_id.in_(ids), DanhGiaNhaHang.an.is_(False))).scalars():
        dg[x] = dg.get(x, 0) + 1
    return {n.id: _cham(n, anh.get(n.id, []), mons.get(n.id, []), n.id in td, dg.get(n.id, 0)) for n in nhs}


def _cot(diem: int, bt: BienTapNhaHang | None, cho: int) -> str:
    if diem >= NGUONG_DU:
        return "du"
    if cho:
        return "cho_duyet"
    if bt is not None and bt.da_xin_luc and (bt.giao_luc is None or bt.da_xin_luc >= bt.giao_luc):
        return "dang_xin"
    return "chua_lam"


COT_HT = {"chua_lam": "Chưa làm", "dang_xin": "Đang xin nhà hàng", "cho_duyet": "Chờ TP ĐH duyệt", "du": "Đủ ≥ 80%"}


def bang_hoan_thien(db: Session, u: User, chi_cua: str = "") -> dict:
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    hn = _hom_nay()
    nhs = db.execute(select(NhaHang).where(NhaHang.ngung.is_(False)).order_by(NhaHang.ten)).scalars().all()
    dm = diem_hoan_thien(db, [n.id for n in nhs])
    bt = {b.nha_hang_id: b for b in db.execute(select(BienTapNhaHang)).scalars()}
    ht = hoan_thien_anh(db)
    ra = []
    for n in nhs:
        b = bt.get(n.id)
        if chi_cua and (b is None or b.nguoi != chi_cua):
            continue
        d = dm[n.id]
        cho = ht.get(n.id, {}).get("cho_duyet", 0) + ht.get(n.id, {}).get("nd_cho", 0)
        ra.append({"id": n.id, "ma": n.ma, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "hien_cong": n.hien_cong, "diem": d["diem"],
                   "muc_do": _muc_do(d["diem"]), "muc": [{k: m[k] for k in ("ma", "dat", "diem", "diem_toi_da", "chi_tiet")} for m in d["muc"]],
                   "nguoi": b.nguoi if b else "", "han": b.han.isoformat() if b and b.han else None,
                   "qua_han": bool(b and b.han and b.han < hn and d["diem"] < NGUONG_DU), "cho_duyet": cho,
                   "cot": _cot(d["diem"], b, cho)})
    ra.sort(key=lambda o: (o["diem"], o["ten"]))
    dem = {k: sum(1 for o in ra if o["muc_do"] == k) for k in ("du", "dang", "thieu")}
    nguoi_nhan = [{"username": x.username, "ten": x.full_name, "role": x.role} for x in
                  db.execute(select(User).where(User.role.in_(VAI_NHAN_BIEN_TAP), User.active.is_(True)).order_by(User.full_name)).scalars()]
    return {"nha_hang": ra, "dem": dem, "chua_giao": sum(1 for o in ra if not o["nguoi"]), "cot": COT_HT,
            "muc_ten": {ma: ten for ma, ten, _w, _t in MUC_HT}, "nguong": {"du": NGUONG_DU, "thieu": NGUONG_THIEU},
            "duoc_giao": u.role in VAI_GIAO_BIEN_TAP, "nguoi_nhan": nguoi_nhan if u.role in VAI_GIAO_BIEN_TAP else []}


def giao_bien_tap(db: Session, u: User, ids: list[int], nguoi: str, han, now: datetime | None = None) -> int:
    """Chủ tịch giao (hoặc đổi người / bỏ giao khi nguoi rỗng) nhiều nhà hàng một lần."""
    if u.role not in VAI_GIAO_BIEN_TAP:
        raise LoiNhaHang("Chỉ Chủ tịch giao việc biên tập nhà hàng")
    now = now or datetime.now()
    nguoi = (nguoi or "").strip()
    if nguoi:
        x = db.execute(select(User).where(User.username == nguoi)).scalars().first()
        if x is None or not x.active or x.role not in VAI_NHAN_BIEN_TAP:
            raise LoiNhaHang("Người biên tập phải là NV Điều hành hoặc NV Marketing đang làm việc")
    hn = _ngay(han)
    if nguoi and hn is not None and hn < _hom_nay():
        raise LoiNhaHang("Hạn phải từ hôm nay trở đi")
    n = 0
    for nid in ids[:500]:
        if db.get(NhaHang, int(nid)) is None:
            continue
        b = db.execute(select(BienTapNhaHang).where(BienTapNhaHang.nha_hang_id == int(nid))).scalars().first()
        if b is None:
            b = BienTapNhaHang(nha_hang_id=int(nid)); db.add(b)
        b.nguoi, b.han, b.giao_boi, b.giao_luc = nguoi, hn if nguoi else None, u.username, now
        n += 1
    db.commit()
    return n


def ghi_da_xin(db: Session, u: User, nid: int, now: datetime | None = None) -> BienTapNhaHang:
    if not _co(u, VAI_ANH_NH):
        raise LoiNhaHang("Chỉ Điều hành / Marketing ghi đã xin nhà hàng")
    if db.get(NhaHang, nid) is None:
        raise LoiNhaHang("Không có nhà hàng này")
    b = db.execute(select(BienTapNhaHang).where(BienTapNhaHang.nha_hang_id == nid)).scalars().first()
    if b is None:
        b = BienTapNhaHang(nha_hang_id=nid); db.add(b)
    b.da_xin_boi, b.da_xin_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(b)
    return b


def _tin_xin(n: NhaHang, d: dict) -> str:
    """Soạn sẵn tin xin nhà hàng bổ sung (người biên tập tự gửi — máy không gửi)."""
    can = []
    for m in d["muc"]:
        if m["dat"]:
            continue
        if m["ma"] == "bia":
            can.append("Một ảnh mặt tiền hoặc không gian để làm ảnh bìa (kèm xác nhận cho phép Vietourist sử dụng)")
        elif m["ma"] == "album":
            can.append(f"Thêm ảnh không gian, phòng riêng, món ăn (cần ít nhất {ALBUM_TOI_THIEU} ảnh) kèm xác nhận quyền sử dụng")
        elif m["ma"] == "mon":
            can.append(f"Ảnh và tên của {MON_TOI_THIEU} món nên thử, kèm thành phần dễ dị ứng nếu có")
        elif m["ma"] == "thuc_don":
            can.append("Thực đơn mới nhất (ảnh hoặc PDF) và ngày bắt đầu áp dụng")
        elif m["ma"] == "lien_he":
            can.append("Xác nhận địa chỉ, giờ mở cửa và số điện thoại liên hệ")
    if not can:
        return ""
    return f"Chào anh/chị, Vietourist cần bổ sung cho trang giới thiệu {n.ten}:\n" + \
        "\n".join(f"{i}. {t}." for i, t in enumerate(can, 1)) + "\nCảm ơn anh/chị."


def hoan_thien_mot(db: Session, u: User, nid: int) -> dict:
    if not _co(u, VAI_XEM):
        raise LoiNhaHang("Không có quyền")
    n = db.get(NhaHang, nid)
    if n is None:
        raise LoiNhaHang("Không có nhà hàng này")
    d = diem_hoan_thien(db, [nid])[nid]
    b = db.execute(select(BienTapNhaHang).where(BienTapNhaHang.nha_hang_id == nid)).scalars().first()
    nk = []
    for a in db.execute(select(AnhNhaHang).where(AnhNhaHang.nha_hang_id == nid)).scalars():
        nk.append((a.tai_luc, f"{a.tai_boi} tải ảnh #{a.id}"))
        if a.duyet_luc:
            nk.append((a.duyet_luc, f"{a.duyet_boi} duyệt ảnh #{a.id}"))
    for m in db.execute(select(MonNhaHang).where(MonNhaHang.nha_hang_id == nid)).scalars():
        nk.append((m.tao_luc, f"{m.tao_boi} thêm món {m.ten}"))
        if m.duyet_luc:
            nk.append((m.duyet_luc, f"{m.duyet_boi} duyệt món {m.ten}"))
    for t in db.execute(select(ThucDonBan).where(ThucDonBan.nha_hang_id == nid)).scalars():
        nk.append((t.tai_luc, f"{t.tai_boi} tải thực đơn {LOAI_THUC_DON.get(t.loai, t.loai)} {_ten_ban(t.so)}"))
        if t.duyet_luc:
            nk.append((t.duyet_luc, f"{t.duyet_boi} duyệt thực đơn {_ten_ban(t.so)}"))
    if b and b.giao_luc:
        nk.append((b.giao_luc, f"{b.giao_boi} giao cho {b.nguoi or '(bỏ giao)'}"))
    if b and b.da_xin_luc:
        nk.append((b.da_xin_luc, f"{b.da_xin_boi} ghi đã xin nhà hàng bổ sung"))
    nk = [x for x in nk if x[0]]
    nk.sort(key=lambda x: x[0], reverse=True)
    return {**d, "muc_do": _muc_do(d["diem"]), "nguong": {"du": NGUONG_DU, "thieu": NGUONG_THIEU},
            "nguoi": b.nguoi if b else "", "han": b.han.isoformat() if b and b.han else None,
            "da_xin_luc": b.da_xin_luc.isoformat(timespec="minutes") if b and b.da_xin_luc else None,
            "tin_xin": _tin_xin(n, d), "nhat_ky": [{"luc": x[0].isoformat(timespec="minutes"), "viec": x[1]} for x in nk[:15]]}


def xuat_thieu_xlsx(db: Session, u: User) -> bytes:
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font
    b = bang_hoan_thien(db, u)
    wb = Workbook(); ws = wb.active; ws.title = "Thiếu"
    ws.append(["Mã", "Nhà hàng", "Thành phố", "Điểm %"] + [b["muc_ten"][ma] for ma, *_r in MUC_HT] + ["Người biên tập", "Hạn"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for o in b["nha_hang"]:
        if o["diem"] >= NGUONG_DU:
            continue
        ws.append([o["ma"], o["ten"], o["tinh_thanh"], o["diem"]] + ["✓" if m["dat"] else m["chi_tiet"] for m in o["muc"]] + [o["nguoi"], o["han"] or ""])
    for col, w in zip("ABCDEFGHIJKLM", (9, 32, 18, 8, 26, 26, 26, 26, 30, 30, 30, 16, 12)):
        ws.column_dimensions[col].width = w
    o = BytesIO(); wb.save(o)
    return o.getvalue()
