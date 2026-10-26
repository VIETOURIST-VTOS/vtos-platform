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
from app.models.nha_hang import NhaHang, ThucDonNhaHang, AM_THUC, LOAI_GOI

TOAN_QUYEN = ("chutich", "tgd")
VAI_NHAP = ("tp_dh", "nv_dh") + TOAN_QUYEN
VAI_BAT = ("tp_kd", "gd_kd") + TOAN_QUYEN
VAI_XEM = tuple(dict.fromkeys(VAI_NHAP + VAI_BAT + ("bks", "robot_ks")))

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
        raise LoiNhaHang("Chỉ TP / GĐ Kinh doanh bật hoặc tắt hiện trên cổng")
    nh = db.get(NhaHang, nha_hang_id)
    if nh is None:
        raise LoiNhaHang("Không có nhà hàng này")
    if bat:
        if nh.ngung:
            raise LoiNhaHang("Nhà hàng đã ngừng hợp tác")
        tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == nh.id)).scalars().all()
        if not any(_con_ban(t, _hom_nay()) for t in tds):
            raise LoiNhaHang("Chưa có thực đơn đang bán — Điều hành thêm thực đơn trước")
        nh.hien_cong, nh.hien_boi, nh.hien_luc, nh.tat_ly_do = True, u.username, now or datetime.now(), ""
    else:
        nh.hien_cong, nh.tat_ly_do = False, f"Tắt bởi {u.username}"
    db.commit(); db.refresh(nh)
    return nh


def ngung(db: Session, u: User, nha_hang_id: int, ngung_: bool) -> NhaHang:
    if not _co(u, VAI_BAT + ("tp_dh",)):
        raise LoiNhaHang("Chỉ TP Điều hành / Kinh doanh đánh dấu ngừng hợp tác")
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
    hn = _hom_nay()
    ra = []
    for n in nhs:
        mine = [t for t in tds if t.nha_hang_id == n.id]
        ra.append({"id": n.id, "ma": n.ma, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "khu_vuc": n.khu_vuc, "am_thuc": n.am_thuc,
                   "gio_phuc_vu": n.gio_phuc_vu, "tien_ich": n.tien_ich, "mo_ta": n.mo_ta, "ghi_chu_noi_bo": n.ghi_chu_noi_bo,
                   "hien_cong": n.hien_cong, "hien_boi": n.hien_boi, "hien_luc": n.hien_luc.isoformat(timespec="minutes") if n.hien_luc else None,
                   "tat_ly_do": n.tat_ly_do, "ngung": n.ngung, "tao_boi": n.tao_boi,
                   "thuc_don": [_td_out(t, True) for t in mine], "so_dang_ban": sum(1 for t in mine if _con_ban(t, hn))})
    return {"nha_hang": ra, "am_thuc": list(AM_THUC), "loai_goi": LOAI_GOI}


# ── phía cổng khách ─────────────────────────────────────────────────────────────────────────────

def _nh_cong(n: NhaHang, tds: list[ThucDonNhaHang], hn: date) -> dict | None:
    ban = [t for t in tds if _con_ban(t, hn)]
    if not ban:
        return None
    return {"id": n.id, "ten": n.ten, "tinh_thanh": n.tinh_thanh, "khu_vuc": n.khu_vuc, "am_thuc": n.am_thuc,
            "gio_phuc_vu": n.gio_phuc_vu, "tien_ich": n.tien_ich, "mo_ta": n.mo_ta,
            "gia_tu": min(int(t.gia_nguoi_lon or 0) for t in ban), "thuc_don": [_td_out(t, False) for t in ban]}


def danh_sach_cong(db: Session, tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0) -> dict:
    hn = _hom_nay()
    cau = select(NhaHang).where(NhaHang.hien_cong.is_(True), NhaHang.ngung.is_(False)).order_by(NhaHang.ten)
    if tinh:
        cau = cau.where(NhaHang.tinh_thanh == tinh)
    if am_thuc:
        cau = cau.where(NhaHang.am_thuc == am_thuc)
    nhs = db.execute(cau).scalars().all()
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id.in_([n.id for n in nhs]))).scalars().all() if nhs else []
    ra = []
    for n in nhs:
        o = _nh_cong(n, [t for t in tds if t.nha_hang_id == n.id], hn)
        if o and (not gia_toi_da or o["gia_tu"] <= gia_toi_da):
            ra.append(o)
    tinh_all = db.execute(select(NhaHang.tinh_thanh).where(NhaHang.hien_cong.is_(True), NhaHang.ngung.is_(False)).distinct()).scalars().all()
    return {"nha_hang": ra, "tinh_thanh": sorted(t for t in tinh_all if t), "am_thuc": list(AM_THUC)}


def mot_nha_hang_cong(db: Session, nha_hang_id: int) -> tuple[NhaHang, dict]:
    n = db.get(NhaHang, nha_hang_id)
    if n is None or not n.hien_cong or n.ngung:
        raise LoiNhaHang("Nhà hàng này không còn mở đặt trên cổng")
    tds = db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == n.id)).scalars().all()
    o = _nh_cong(n, tds, _hom_nay())
    if o is None:
        raise LoiNhaHang("Nhà hàng này chưa có thực đơn đang bán")
    return n, o


GIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def kiem_dat_ban(db: Session, nha_hang_id: int, thuc_don_id: int, ngay: date | None, gio: str, nguoi_lon: int, tre_em: int,
                 hom_nay: date) -> tuple[dict, dict, int]:
    """Kiểm yêu cầu đặt bàn; trả (nhà hàng, gói, tạm tính). Tạm tính do MÁY tính từ giá đã lưu."""
    _n, o = mot_nha_hang_cong(db, nha_hang_id)
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
