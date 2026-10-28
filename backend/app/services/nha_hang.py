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
    "Bến Tre": ("nam", ()), "Trà Vinh": ("nam", ("travinh",)), "Cà Mau": ("nam", ()), "Côn Đảo": ("nam", ("con dao", "con son"))}
MIEN = {"bac": "Miền Bắc", "trung": "Miền Trung", "tay_nguyen": "Tây Nguyên", "nam": "Miền Nam"}

TRUONG_NH = ("ten", "tinh_thanh", "khu_vuc", "am_thuc", "gio_phuc_vu", "tien_ich", "mo_ta")
TRUONG_TD = ("ten", "loai", "gia_nguoi_lon", "gia_tre_em", "so_khach_toi_thieu", "mo_ta", "dieu_kien", "dieu_kien_huy",
             "tu_ngay", "den_ngay", "dang_ban")


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
    for k in TRUONG_NH:
        if k in d and d[k] is not None:
            v = str(d[k]).strip()
            if getattr(nh, k) != v:
                setattr(nh, k, v); doi = True
    if "ghi_chu_noi_bo" in d and d["ghi_chu_noi_bo"] is not None:
        nh.ghi_chu_noi_bo = str(d["ghi_chu_noi_bo"]).strip()
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
    v["ten"] = (v["ten"] or "").strip()
    if not v["ten"]:
        raise LoiNhaHang("Ghi tên gói / thực đơn")
    if v["loai"] not in LOAI_GOI:
        raise LoiNhaHang("Loại gói không hợp lệ")
    gl = v["gia_nguoi_lon"]
    if gl in (None, "") or float(gl) <= 0:
        raise LoiNhaHang("Ghi giá bán người lớn (lớn hơn 0)")
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
         "tu_ngay": t.tu_ngay.isoformat() if t.tu_ngay else None, "den_ngay": t.den_ngay.isoformat() if t.den_ngay else None}
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
                   "hop_dong": [_hd_out(h) for h in hds.get(n.id, [])], "anh_id": n.anh_id, "anh_nguon": n.anh_nguon})
    return {"nha_hang": ra, "am_thuc": list(AM_THUC), "loai_goi": LOAI_GOI, "noi_dung": ds_noi_dung(db), "loai_nd": LOAI_ND,
            "thanh_pho": [{"ten": t, "mien": MIEN[m]} for t, (m, _k) in THANH_PHO.items()], "nhom_mon": list(NHOM_MON)}


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


def _nh_cong(db: Session, n: NhaHang, tds: list[ThucDonNhaHang], hn: date) -> dict:
    dat = mo_dat(db, n, tds, hn)
    ban = [t for t in tds if _con_ban(t, hn)] if dat else []
    return {"id": n.id, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "khu_vuc": n.khu_vuc, "am_thuc": n.am_thuc,
            "gio_phuc_vu": n.gio_phuc_vu, "tien_ich": n.tien_ich, "mo_ta": n.mo_ta, "mon_noi_bat": n.mon_noi_bat,
            "dia_danh_nguon": n.dia_danh_nguon, "mo_dat": dat, "da_xac_minh": bool(n.lien_he_xac_minh),
            "anh": _duong_anh(n.anh_id), "anh_nguon": n.anh_nguon if n.anh_id else "",
            "gia_tu": min(int(t.gia_nguoi_lon or 0) for t in ban) if ban else None, "thuc_don": [_td_out(t, False) for t in ban]}


def _khong_dau(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _duong_anh(aid: int | None) -> str | None:
    return f"/api/v1/am-thuc/anh/{aid}" if aid else None


def _nh_hien(db: Session, hn: date) -> list[dict]:
    nhs = db.execute(select(NhaHang).where(NhaHang.hien_cong.is_(True), NhaHang.ngung.is_(False)).order_by(NhaHang.ten)).scalars().all()
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id.in_([n.id for n in nhs]))).scalars().all() if nhs else []
    return [(n, _nh_cong(db, n, [t for t in tds if t.nha_hang_id == n.id], hn)) for n in nhs]


def danh_sach_cong(db: Session, tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0, q: str = "", chi_dat: bool = False,
                   trang: int = 1, so: int = 24) -> dict:
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
        ra.append(o)
    ra.sort(key=lambda o: (not o["mo_dat"], o["ten"]))
    trang, so = max(1, int(trang or 1)), max(1, min(int(so or 24), 60))
    dem: dict = {}
    for n, _o in tat_ca:
        if n.tinh_thanh:
            dem[n.tinh_thanh] = dem.get(n.tinh_thanh, 0) + 1
    nd = ds_noi_dung(db, cong=True, nha_hang={n.id: o for n, o in tat_ca})
    gioi = {x["ten"]: x for x in nd if x["loai"] == "thanh_pho"}
    tp = [{"ten": t, "mien": m, "mien_ten": MIEN[m], "so_nha_hang": dem.get(t, 0),
           "tom_tat": gioi.get(t, {}).get("tom_tat", ""), "anh": gioi.get(t, {}).get("anh")}
          for t, (m, _k) in THANH_PHO.items()]
    return {"nha_hang": ra[(trang - 1) * so: trang * so], "tong": len(ra), "trang": trang, "so": so,
            "tinh_thanh": sorted(dem), "dem_tinh": dem, "thanh_pho": tp, "mien": MIEN, "nhom_mon": list(NHOM_MON),
            "so_mo_dat": sum(1 for _n, o in tat_ca if o["mo_dat"]), "tong_nha_hang": len(tat_ca),
            "am_thuc": list(AM_THUC), "noi_dung": nd}


def mot_nha_hang_cong(db: Session, nha_hang_id: int) -> tuple[NhaHang, dict]:
    n = db.get(NhaHang, nha_hang_id)
    if n is None or not n.hien_cong or n.ngung:
        raise LoiNhaHang("Nhà hàng này không còn hiện trên VTD")
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == n.id)).scalars().all()
    return n, _nh_cong(db, n, tds, _hom_nay())


GIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def kiem_dat_ban(db: Session, nha_hang_id: int, thuc_don_id: int, ngay: date | None, gio: str, nguoi_lon: int, tre_em: int,
                 hom_nay: date) -> tuple[dict, dict, int]:
    """Kiểm yêu cầu đặt bàn; trả (nhà hàng, gói, tạm tính). Tạm tính do MÁY tính từ giá đã lưu."""
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
    tam = td["gia_nguoi_lon"] * int(nguoi_lon) + (td["gia_tre_em"] or 0) * int(tre_em)
    return o, td, tam


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
        if not _co(u, VAI_ANH_NH):
            raise LoiNhaHang("Chỉ Điều hành hoặc Marketing tải ảnh nhà hàng")
        x = db.get(NhaHang, oid)
    elif doi == "noi_dung":
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
    ok = db.execute(select(NhaHang.id).where(NhaHang.anh_id == aid, NhaHang.hien_cong.is_(True), NhaHang.ngung.is_(False))).first() \
        or db.execute(select(NoiDungAmThuc.id).where(NoiDungAmThuc.anh_id == aid, NoiDungAmThuc.hien.is_(True))).first()
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
