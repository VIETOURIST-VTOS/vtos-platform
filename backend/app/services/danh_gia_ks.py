"""KS-15 · ĐÁNH GIÁ KHÁCH SẠN VTD (Chủ tịch duyệt bản xem thử 30/10/2026) — luật ở `app/models/don_ks_vtd.py`.

Như đánh giá nhà hàng AT-3 (`danh_gia_nh.py`), khác ở: thang 10 như Agoda, năm mục (sạch sẽ, vị trí, phòng, phục vụ,
đáng giá tiền), tiêu đề, «đi cùng ai»; được viết khi đơn ĐÃ XÁC NHẬN và đã tới ngày trả phòng.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.don_ks_vtd import DI_CUNG, LY_DO_AN_DG_KS, MUC_DG_KS, DanhGiaKsVtd, DonKsVtd
from app.models.khach_san_vtd import KhachSanVtd
from app.services import rules as R

HAN_VIET_NGAY, HAN_SUA_NGAY, HAN_SUA_TRA_LOI_GIO = 30, 7, 24
NHAN_XET_TOI_DA, TIEU_DE_TOI_DA, TRA_LOI_TOI_DA, GHI_CHU_TOI_DA = 1000, 120, 600, 500
ANH_TOI_DA = 3
TOI_THIEU_HIEN_DIEM = 3
VAI_AN = ("nv_mkt", "ptgd_mkt")                      # như AT-3: CHỈ Marketing ẩn vì vi phạm
VAI_XEM_LAI = ("tp_dh", "chutich", "tgd")
MUC = tuple(MUC_DG_KS)


class LoiDanhGiaKs(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def che_ten(ten: str) -> str:
    """«Nguyễn Thị Lan» → «Khách L***» (chữ đầu của tên)."""
    t = (ten or "").strip().split()
    return f"Khách {t[-1][0].upper()}***" if t else "Khách ***"


def nhan(diem: float | None) -> str:
    if diem is None:
        return ""
    return "Xuất sắc" if diem >= 9 else "Tuyệt vời" if diem >= 8.5 else "Rất tốt" if diem >= 8 else "Tốt" if diem >= 7 else \
        "Dễ chịu" if diem >= 6 else "Trung bình"


def _diem(v, bat_buoc: bool) -> int | None:
    if v in (None, "", 0, "0") and not bat_buoc:
        return None
    try:
        x = int(v)
    except (TypeError, ValueError):
        x = 0
    if not 1 <= x <= 10:
        raise LoiDanhGiaKs("Chọn điểm chung từ 1 đến 10" if bat_buoc else "Điểm mỗi mục từ 1 đến 10")
    return x


def _han_viet(d: DonKsVtd) -> datetime:
    return datetime.combine(d.ra, datetime.min.time()) + timedelta(days=HAN_VIET_NGAY + 1)


def _mo_viet(d: DonKsVtd) -> datetime:
    return datetime.combine(d.ra, datetime.min.time())


def _don_cua(db: Session, tk, ma: str) -> DonKsVtd:
    d = db.execute(select(DonKsVtd).where(DonKsVtd.ma == (ma or "").strip().upper())).scalars().first()
    if d is None or d.tai_khoan_ngoai_id != tk.id:
        raise LoiDanhGiaKs("Không có đơn đặt phòng này trong tài khoản của bạn", 404)
    return d


def _cua_don(db: Session, did: int) -> DanhGiaKsVtd | None:
    return db.execute(select(DanhGiaKsVtd).where(DanhGiaKsVtd.don_id == did)).scalars().first()


def trang_thai_don(db: Session, d: DonKsVtd, now: datetime | None = None) -> dict:
    """Cho «Phòng đã đặt»: được viết / sửa không, hạn, bài đã viết."""
    now = now or datetime.now()
    g = _cua_don(db, d.id)
    han = _han_viet(d)
    duoc_viet = g is None and d.trang_thai == "da_xac_nhan" and _mo_viet(d) <= now < han
    duoc_sua = g is not None and now < g.tao_luc + timedelta(days=HAN_SUA_NGAY)
    return {"duoc_viet": duoc_viet, "duoc_sua": duoc_sua, "han_viet": (han - timedelta(days=1)).date().isoformat(),
            "con_ngay": max(0, (han - now).days) if duoc_viet else 0, "bai": _ra(g, rieng=True) if g else None}


def _luu_anh(db: Session, tk, k: KhachSanVtd, tep: list[tuple[str, bytes]]) -> list[dict]:
    from app.services import attachments as AT
    from app.services import nha_hang as NH
    ra = []
    for ten, data in tep:
        try:
            duoi = NH._kiem_tep_anh(ten, data)
        except NH.LoiNhaHang as ex:
            raise LoiDanhGiaKs(str(ex))
        hien, nho, _r, _c = NH._lam_nhe(data)
        if hien is None:
            # Không mở được như ảnh: KHÔNG giữ bản gốc còn EXIF / vị trí.
            raise LoiDanhGiaKs(f"Ảnh «{ten}» không mở được — chụp lại hoặc xuất JPG")
        try:
            a = AT.dinh_kem(db, "khach_san_vtd", f"ks{k.id}", f"dg.{duoi}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                            mo_ta=f"Ảnh khách đánh giá · {k.ma}", boi=f"cong:kh-{tk.id}", nguon="he_thong")[0]
            b = AT.dinh_kem(db, "khach_san_vtd", f"ks{k.id}", f"dg.{duoi}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                            mo_ta=f"Ảnh nhỏ khách đánh giá · {k.ma}", boi=f"cong:kh-{tk.id}", nguon="he_thong")[0]
        except ValueError as ex:
            raise LoiDanhGiaKs(str(ex))
        ra.append({"hien": a.id, "nho": b.id, "an": False, "ly_do": ""})
    return ra


def viet(db: Session, tk, ma: str, d: dict, tep: list[tuple[str, bytes]] | None = None,
         giu_anh: list[int] | None = None, now: datetime | None = None) -> DanhGiaKsVtd:
    """Viết mới, hoặc sửa trong 7 ngày (thay hẳn bài cũ). `giu_anh`: chỉ số ảnh cũ muốn giữ khi sửa."""
    now = now or datetime.now()
    don = _don_cua(db, tk, ma)
    g = _cua_don(db, don.id)
    if g is None:
        if don.trang_thai != "da_xac_nhan":
            raise LoiDanhGiaKs("Chỉ đánh giá được đơn đã được khách sạn xác nhận", 409)
        if now < _mo_viet(don):
            raise LoiDanhGiaKs("Đánh giá mở từ ngày trả phòng", 409)
        if now >= _han_viet(don):
            raise LoiDanhGiaKs(f"Đã quá {HAN_VIET_NGAY} ngày sau ngày trả phòng — đánh giá đã đóng", 409)
    elif now >= g.tao_luc + timedelta(days=HAN_SUA_NGAY):
        raise LoiDanhGiaKs(f"Chỉ sửa được trong {HAN_SUA_NGAY} ngày sau khi gửi", 409)
    if not d.get("dong_y"):
        raise LoiDanhGiaKs("Đánh dấu đồng ý cho Vietourist hiện đánh giá trên trang khách sạn")
    diem = _diem(d.get("diem"), True)
    phu = {k: _diem(d.get(k), False) for k in MUC}
    di = str(d.get("di_cung") or "")
    if di and di not in DI_CUNG:
        raise LoiDanhGiaKs("«Đi cùng» không hợp lệ")
    td = " ".join(str(d.get("tieu_de") or "").split())
    nx = (d.get("nhan_xet") or "").strip()
    if len(td) > TIEU_DE_TOI_DA:
        raise LoiDanhGiaKs(f"Tiêu đề tối đa {TIEU_DE_TOI_DA} ký tự")
    if len(nx) > NHAN_XET_TOI_DA:
        raise LoiDanhGiaKs(f"Nhận xét tối đa {NHAN_XET_TOI_DA:,} ký tự".replace(",", "."))
    k = db.get(KhachSanVtd, don.khach_san_id)
    cu = list(g.anh or []) if g else []
    giu = [cu[i] for i in sorted(set(giu_anh or [])) if 0 <= i < len(cu)] if g else []
    tep = [t for t in (tep or []) if t[1]]
    if len(giu) + len(tep) > ANH_TOI_DA:
        raise LoiDanhGiaKs(f"Tối đa {ANH_TOI_DA} ảnh")
    moi = _luu_anh(db, tk, k, tep)
    if g is None:
        lp = ", ".join(f"{x.get('so', 1)} × {x.get('loai_phong', '')}" if int(x.get("so") or 1) > 1 else str(x.get("loai_phong", ""))
                       for x in (don.dong or []))
        g = DanhGiaKsVtd(don_id=don.id, khach_san_id=don.khach_san_id, tai_khoan_id=tk.id, ten_hien=che_ten(don.ho_ten or tk.ho_ten),
                         loai_phong=lp[:160], so_dem=(don.ra - don.vao).days, ngay_tra=don.ra, tao_luc=now)
        db.add(g)
        hd = "danh_gia_ks_viet"
    else:
        g.sua_luc = now
        hd = "danh_gia_ks_sua"
    g.diem, g.tieu_de, g.nhan_xet, g.di_cung, g.anh = diem, td, nx, di, giu + moi
    for kk, v in phu.items():
        setattr(g, kk, v)
    db.flush()
    R.audit(db, f"cong:kh-{tk.id}", "khach", hd, f"danh_gia_ks:{g.id}", after={"don": don.ma, "diem": diem, "so_anh": len(g.anh)})
    db.commit(); db.refresh(g)
    return g


def _tb(xs: list) -> float | None:
    xs = [x for x in xs if x]
    return round(sum(xs) / len(xs), 1) if xs else None


def _ra(g: DanhGiaKsVtd, rieng: bool = False, noi_bo: bool = False, ks_ten: str = "") -> dict:
    anh = [{"i": i, "hien": f"/api/v1/ks-vtd-anh/dg/{g.id}/{i}/hien", "nho": f"/api/v1/ks-vtd-anh/dg/{g.id}/{i}/nho",
            **({"an": bool(a.get("an")), "ly_do": LY_DO_AN_DG_KS.get(a.get("ly_do"), "")} if (rieng or noi_bo) else {})}
           for i, a in enumerate(g.anh or []) if (rieng or noi_bo) or not a.get("an")]
    r = {"id": g.id, "ten": g.ten_hien, "loai_phong": g.loai_phong, "so_dem": g.so_dem, "thang_o": f"{g.ngay_tra:%m/%Y}",
         "di_cung": g.di_cung, "di_cung_ten": DI_CUNG.get(g.di_cung, ""), "diem": g.diem, "nhan": nhan(g.diem),
         **{k: getattr(g, k) for k in MUC}, "tieu_de": g.tieu_de, "nhan_xet": g.nhan_xet, "anh": anh,
         "tao_luc": g.tao_luc.isoformat(timespec="minutes"), "da_sua": g.sua_luc is not None,
         "tra_loi": (g.tra_loi if g.tra_loi and not g.tra_loi_an else ""),
         "tra_loi_luc": g.tra_loi_luc.isoformat(timespec="minutes") if g.tra_loi_luc and not g.tra_loi_an else None}
    if rieng or noi_bo:
        r["an"] = g.an
        r["an_ly_do"] = LY_DO_AN_DG_KS.get(g.an_ly_do, "")
    if noi_bo:
        r.update({"khach_san_id": g.khach_san_id, "khach_san": ks_ten, "don_id": g.don_id, "an_ghi_chu": g.an_ghi_chu,
                  "an_boi": g.an_boi, "an_luc": g.an_luc.isoformat(timespec="minutes") if g.an_luc else None,
                  "xem_lai": g.xem_lai, "xem_lai_boi": g.xem_lai_boi, "tra_loi": g.tra_loi, "tra_loi_an": g.tra_loi_an,
                  "tra_loi_an_ly_do": LY_DO_AN_DG_KS.get(g.tra_loi_an_ly_do, ""), "tra_loi_boi": g.tra_loi_boi})
    return r


def tom_tat(db: Session, kids: list[int]) -> dict[int, dict]:
    """Điểm trung bình theo khách sạn — chỉ bài đang hiện. Dưới 3 bài: diem_tb = None («Mới — chưa đủ đánh giá»)."""
    if not kids:
        return {}
    gs: dict[int, list] = {}
    for g in db.execute(select(DanhGiaKsVtd).where(DanhGiaKsVtd.khach_san_id.in_(kids), DanhGiaKsVtd.an.is_(False))).scalars():
        gs.setdefault(g.khach_san_id, []).append(g)
    ra = {}
    for kid in kids:
        ds = gs.get(kid, [])
        du = len(ds) >= TOI_THIEU_HIEN_DIEM
        tb = _tb([g.diem for g in ds]) if du else None
        ra[kid] = {"so_bai": len(ds), "du": du, "diem_tb": tb, "nhan": nhan(tb),
                   "muc": ({k: _tb([getattr(g, k) for g in ds]) for k in MUC} if du else {})}
    return ra


def cong(db: Session, kid: int, trang: int = 1, so: int = 10, xep: str = "moi") -> dict:
    """Trang khách: bài đang hiện của một khách sạn đang hiện (chỉ đọc)."""
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiDanhGiaKs("Khách sạn này không còn hiện trên VTD", 404)
    ds = db.execute(select(DanhGiaKsVtd).where(DanhGiaKsVtd.khach_san_id == kid, DanhGiaKsVtd.an.is_(False))).scalars().all()
    if xep == "cao":
        ds.sort(key=lambda g: (-g.diem, -g.id))
    elif xep == "thap":
        ds.sort(key=lambda g: (g.diem, -g.id))
    elif xep == "anh":
        ds = [g for g in ds if any(not a.get("an") for a in (g.anh or []))]
        ds.sort(key=lambda g: -g.id)
    else:
        ds.sort(key=lambda g: -g.id)
    trang, so = max(1, int(trang or 1)), max(1, min(int(so or 10), 50))
    return {"tom_tat": tom_tat(db, [kid])[kid], "bai": [_ra(g) for g in ds[(trang - 1) * so: trang * so]], "tong": len(ds),
            "muc_ten": MUC_DG_KS, "toi_thieu": TOI_THIEU_HIEN_DIEM}


def tep_anh(db: Session, gid: int, i: int, co: str):
    """Ảnh khách cho cổng: bài đang hiện, ảnh chưa bị ẩn, của khách sạn đang hiện; chỉ bản làm nhẹ."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    g = db.get(DanhGiaKsVtd, gid)
    if g is None or g.an or co not in ("hien", "nho") or not 0 <= i < len(g.anh or []) or g.anh[i].get("an"):
        raise LoiDanhGiaKs("Không có ảnh này", 404)
    k = db.get(KhachSanVtd, g.khach_san_id)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiDanhGiaKs("Không có ảnh này", 404)
    a = db.get(Attachment, g.anh[i][co])
    return AT.doc(db, a), a


# ── nội bộ VTOS ─────────────────────────────────────────────────────────────────────────────────────────
def ds_noi_bo(db: Session, u: User, loc: str = "", now: datetime | None = None) -> dict:
    from app.services import khach_san_vtd as KS
    if u.role not in KS.VAI_XEM:
        raise LoiDanhGiaKs("Không có quyền", 403)
    now = now or datetime.now()
    ds = db.execute(select(DanhGiaKsVtd).order_by(DanhGiaKsVtd.id.desc())).scalars().all()
    ten = {k.id: k.ten for k in db.execute(select(KhachSanVtd)).scalars()}
    dem = {"ba_muoi_ngay": sum(1 for g in ds if g.tao_luc >= now - timedelta(days=30)),
           "thap_chua_tra_loi": sum(1 for g in ds if g.diem <= 5 and not g.an and not g.tra_loi),
           "cho_xem_lai": sum(1 for g in ds if (g.an or any(a.get("an") for a in g.anh or []) or g.tra_loi_an) and not g.xem_lai),
           "chua_cham": _don_chua_cham(db, now)}
    f = {"thap": lambda g: g.diem <= 5, "anh": lambda g: bool(g.anh), "chua_tra_loi": lambda g: not g.tra_loi,
         "da_an": lambda g: g.an or g.tra_loi_an or any(a.get("an") for a in g.anh or [])}.get(loc)
    if f:
        ds = [g for g in ds if f(g)]
    return {"bai": [_ra(g, noi_bo=True, ks_ten=ten.get(g.khach_san_id, "")) for g in ds[:300]], "dem": dem,
            "ly_do": LY_DO_AN_DG_KS, "muc_ten": MUC_DG_KS, "duoc_an": u.role in VAI_AN, "duoc_xem_lai": u.role in VAI_XEM_LAI}


def _don_chua_cham(db: Session, now: datetime) -> int:
    co = set(db.execute(select(DanhGiaKsVtd.don_id)).scalars())
    tu = (now - timedelta(days=HAN_VIET_NGAY)).date()
    return sum(1 for did in db.execute(select(DonKsVtd.id).where(DonKsVtd.trang_thai == "da_xac_nhan", DonKsVtd.ra >= tu,
                                                                  DonKsVtd.ra <= now.date())).scalars() if did not in co)


def an(db: Session, u: User, gid: int, ly_do: str, ghi_chu: str, phan: str = "bai", now: datetime | None = None) -> DanhGiaKsVtd:
    """Ẩn VÌ VI PHẠM. phan: "bai" | "anh:<i>" | "tra_loi". «Bài chê» không phải lý do."""
    if u.role not in VAI_AN:
        raise LoiDanhGiaKs("Chỉ NV / PTGĐ Marketing ẩn đánh giá vi phạm", 403)
    if ly_do not in LY_DO_AN_DG_KS:
        raise LoiDanhGiaKs("Chọn một lý do vi phạm: " + ", ".join(LY_DO_AN_DG_KS.values()))
    ghi_chu = (ghi_chu or "").strip()
    if len(ghi_chu) < 5:
        raise LoiDanhGiaKs("Ghi thêm chỗ vi phạm (ít nhất 5 ký tự) để TP Điều hành xem lại")
    now = now or datetime.now()
    g = db.get(DanhGiaKsVtd, gid)
    if g is None:
        raise LoiDanhGiaKs("Không có đánh giá này", 404)
    if phan == "bai":
        if g.an:
            raise LoiDanhGiaKs("Bài đã ẩn", 409)
        g.an = True
    elif phan == "tra_loi":
        if not g.tra_loi or g.tra_loi_an:
            raise LoiDanhGiaKs("Không có lời trả lời đang hiện", 409)
        g.tra_loi_an, g.tra_loi_an_ly_do = True, ly_do
    elif phan.startswith("anh:"):
        try:
            i = int(phan[4:])
        except ValueError:
            i = -1
        anh = [dict(a) for a in (g.anh or [])]
        if not 0 <= i < len(anh) or anh[i].get("an"):
            raise LoiDanhGiaKs("Không có ảnh này", 404)
        anh[i]["an"], anh[i]["ly_do"] = True, ly_do
        g.anh = anh
    else:
        raise LoiDanhGiaKs("Phần cần ẩn không hợp lệ")
    if phan == "bai" or not g.an_ly_do:
        g.an_ly_do = ly_do
    g.an_ghi_chu = f"[{phan}] {ghi_chu[:GHI_CHU_TOI_DA]}"
    g.an_boi, g.an_luc, g.xem_lai, g.xem_lai_boi, g.xem_lai_luc = u.username, now, "", "", None
    R.audit(db, u.username, u.role, "danh_gia_ks_an", f"danh_gia_ks:{g.id}", after={"phan": phan, "ly_do": ly_do, "ghi_chu": ghi_chu[:200]})
    db.commit(); db.refresh(g)
    return g


def xem_lai(db: Session, u: User, gid: int, giu: bool, ghi_chu: str = "", now: datetime | None = None) -> DanhGiaKsVtd:
    """TP Điều hành xem lại: giữ ẩn, hoặc hiện lại MỌI phần đang ẩn. Người ẩn không tự xem lại."""
    if u.role not in VAI_XEM_LAI:
        raise LoiDanhGiaKs("Chỉ TP Điều hành xem lại bài bị ẩn", 403)
    now = now or datetime.now()
    g = db.get(DanhGiaKsVtd, gid)
    if g is None:
        raise LoiDanhGiaKs("Không có đánh giá này", 404)
    if not (g.an or g.tra_loi_an or any(a.get("an") for a in g.anh or [])):
        raise LoiDanhGiaKs("Bài này không có phần nào đang ẩn", 409)
    if g.an_boi == u.username:
        raise LoiDanhGiaKs("Người ẩn không tự xem lại — cần người thứ hai", 403)
    if not giu:
        g.an, g.tra_loi_an, g.tra_loi_an_ly_do = False, False, ""
        g.anh = [{**a, "an": False, "ly_do": ""} for a in (g.anh or [])]
    g.xem_lai, g.xem_lai_boi, g.xem_lai_luc = ("giu" if giu else "hien"), u.username, now
    R.audit(db, u.username, u.role, "danh_gia_ks_xem_lai", f"danh_gia_ks:{g.id}", after={"giu": giu, "ghi_chu": (ghi_chu or "")[:200]})
    db.commit(); db.refresh(g)
    return g


# ── cổng NCC: khách sạn trả lời ─────────────────────────────────────────────────────────────────────────
def _ks_cua_ncc(db: Session, s) -> dict[int, str]:
    return {k.id: k.ten for k in db.execute(select(KhachSanVtd).where(KhachSanVtd.supplier_id == s.id)).scalars()}


def ds_ncc(db: Session, s, now: datetime | None = None) -> dict:
    ks = _ks_cua_ncc(db, s)
    if not ks:
        return {"khach_san": [], "bai": [], "muc_ten": MUC_DG_KS}
    now = now or datetime.now()
    ds = db.execute(select(DanhGiaKsVtd).where(DanhGiaKsVtd.khach_san_id.in_(list(ks)), DanhGiaKsVtd.an.is_(False))
                    .order_by(DanhGiaKsVtd.id.desc())).scalars().all()
    tt = tom_tat(db, list(ks))
    return {"khach_san": [{"id": k, "ten": v, **tt[k]} for k, v in ks.items()],
            "bai": [{**_ra(g), "khach_san": ks[g.khach_san_id], "tra_loi_cua_minh": g.tra_loi, "duoc_tra_loi": not g.tra_loi,
                     "duoc_sua_tra_loi": bool(g.tra_loi) and not g.tra_loi_an and g.tra_loi_luc is not None
                     and now < g.tra_loi_luc + timedelta(hours=HAN_SUA_TRA_LOI_GIO), "tra_loi_bi_an": g.tra_loi_an}
                    for g in ds[:300]],
            "muc_ten": MUC_DG_KS}


def tra_loi(db: Session, tk, s, gid: int, noi_dung: str, now: datetime | None = None) -> DanhGiaKsVtd:
    now = now or datetime.now()
    g = db.get(DanhGiaKsVtd, gid)
    if g is None or g.khach_san_id not in _ks_cua_ncc(db, s) or g.an:
        raise LoiDanhGiaKs("Không có đánh giá này", 404)
    nd = (noi_dung or "").strip()
    if not nd:
        raise LoiDanhGiaKs("Viết nội dung trả lời")
    if len(nd) > TRA_LOI_TOI_DA:
        raise LoiDanhGiaKs(f"Trả lời tối đa {TRA_LOI_TOI_DA} ký tự")
    if g.tra_loi:
        if g.tra_loi_an or g.tra_loi_luc is None or now >= g.tra_loi_luc + timedelta(hours=HAN_SUA_TRA_LOI_GIO):
            raise LoiDanhGiaKs(f"Mỗi bài trả lời một lần; chỉ sửa được trong {HAN_SUA_TRA_LOI_GIO} giờ", 409)
    else:
        g.tra_loi_luc = now
    g.tra_loi, g.tra_loi_boi = nd, f"cong:ncc-{tk.id}"
    R.audit(db, f"cong:ncc-{tk.id}", "ncc", "danh_gia_ks_tra_loi", f"danh_gia_ks:{g.id}", after={"do_dai": len(nd)})
    db.commit(); db.refresh(g)
    return g


def gan_ncc(db: Session, u: User, kid: int, ncc_id: int | None) -> KhachSanVtd:
    """Gắn khách sạn với một NCC — tài khoản cổng NCC nối với NCC đó thấy và trả lời đánh giá."""
    from app.models.suppliers import Supplier
    from app.services import cong_ncc as N
    if u.role not in N.VAI_NOI:
        raise LoiDanhGiaKs("Chỉ TP Điều hành, GĐ KD, Chủ tịch, TGĐ gắn khách sạn với NCC", 403)
    k = db.get(KhachSanVtd, kid)
    if k is None:
        raise LoiDanhGiaKs("Không có khách sạn này", 404)
    if ncc_id and db.get(Supplier, ncc_id) is None:
        raise LoiDanhGiaKs("Không có NCC này", 404)
    truoc = k.supplier_id
    k.supplier_id = ncc_id or None
    db.flush()
    R.audit(db, u.username, u.role, "cong_ncc_gan_khach_san", f"khach_san_vtd:{k.ma}", before={"supplier_id": truoc},
            after={"supplier_id": k.supplier_id})
    return k


def _hom_nay() -> date:
    return date.today()
