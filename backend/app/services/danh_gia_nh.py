"""AT-3 · ĐÁNH GIÁ SAO NHÀ HÀNG (Chủ tịch duyệt bản xem thử 29/10/2026).

  · Ai viết: CHỈ người đặt (tài khoản cổng) của một đơn đặt bàn nhà hàng đã báo «khách đã dùng»; một bài / đơn;
    trong 30 ngày sau bữa ăn. Sửa được trong 7 ngày (bản cũ không giữ), sau đó khóa.
  · Chấm: tổng 1–5 (bắt buộc) + món ăn, phục vụ, không gian, đáng giá tiền (không bắt buộc — rỗng khác 0) + nhận xét
    (≤ 1.000 ký tự) + tối đa 3 ảnh (máy làm nhẹ, bỏ EXIF / vị trí).
  · Hiện NGAY. Không ai ẩn được vì bài chê. Chỉ NV / PTGĐ Marketing ẩn vì VI PHẠM (4 lý do, bắt buộc ghi thêm);
    ẩn một ảnh thì bài vẫn hiện. TP Điều hành xem lại mọi bài bị ẩn: giữ ẩn hoặc hiện lại. Mọi lần ghi nhật ký.
  · Nhà hàng trả lời công khai một lần mỗi bài trên cổng NCC (≤ 600 ký tự), sửa được trong 24 giờ.
  · Trang khách: tên che còn chữ đầu; không số điện thoại, không mã đơn. Dưới 3 bài đang hiện: «Mới — chưa đủ
    đánh giá» thay điểm trung bình.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.dat_ban import DonDatBan
from app.models.nha_hang import LY_DO_AN_DG, MUC_DG, DanhGiaNhaHang, NhaHang
from app.services import rules as R

HAN_VIET_NGAY, HAN_SUA_NGAY, HAN_SUA_TRA_LOI_GIO = 30, 7, 24
NHAN_XET_TOI_DA, TRA_LOI_TOI_DA, GHI_CHU_TOI_DA = 1000, 600, 500
ANH_TOI_DA = 3
TOI_THIEU_HIEN_DIEM = 3
VAI_AN = ("nv_mkt", "ptgd_mkt")                      # Chủ tịch 29/10/2026: CHỈ Marketing ẩn
VAI_XEM_LAI = ("tp_dh", "chutich", "tgd")
MUC = tuple(MUC_DG)


class LoiDanhGia(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def che_ten(ten: str) -> str:
    """«Nguyễn Thị Lan» → «Khách L***». Lấy chữ đầu của TÊN (từ cuối)."""
    t = (ten or "").strip().split()
    return f"Khách {t[-1][0].upper()}***" if t else "Khách ***"


def _sao(v, bat_buoc: bool) -> int | None:
    if v in (None, "", 0) and not bat_buoc:
        return None
    try:
        x = int(v)
    except (TypeError, ValueError):
        x = 0
    if not 1 <= x <= 5:
        raise LoiDanhGia("Chọn từ 1 đến 5 sao cho điểm tổng" if bat_buoc else "Điểm mỗi mục từ 1 đến 5 sao")
    return x


def _han_viet(d: DonDatBan) -> datetime:
    return datetime.combine(d.ngay, datetime.min.time()) + timedelta(days=HAN_VIET_NGAY + 1)


def _don_cua(db: Session, tk: TaiKhoanNgoai, ma: str) -> DonDatBan:
    d = db.execute(select(DonDatBan).where(DonDatBan.ma == (ma or "").strip().upper())).scalars().first()
    if d is None or d.tai_khoan_id != tk.id:
        raise LoiDanhGia("Không có đơn đặt bàn này trong tài khoản của bạn", 404)
    return d


def _cua_don(db: Session, did: int) -> DanhGiaNhaHang | None:
    return db.execute(select(DanhGiaNhaHang).where(DanhGiaNhaHang.don_id == did)).scalars().first()


def trang_thai_don(db: Session, d: DonDatBan, now: datetime | None = None) -> dict:
    """Cho «Đơn của tôi»: được viết / sửa không, hạn, bài đã viết."""
    now = now or datetime.now()
    g = _cua_don(db, d.id)
    han = _han_viet(d)
    duoc_viet = g is None and d.trang_thai == "da_dung" and now < han
    duoc_sua = g is not None and now < g.tao_luc + timedelta(days=HAN_SUA_NGAY)
    return {"duoc_viet": duoc_viet, "duoc_sua": duoc_sua, "han_viet": (han - timedelta(days=1)).date().isoformat(),
            "con_ngay": max(0, (han - now).days) if duoc_viet else 0,
            "bai": _ra(g, rieng=True) if g else None}


def _luu_anh(db: Session, tk: TaiKhoanNgoai, nh: NhaHang, tep: list[tuple[str, bytes]]) -> list[dict]:
    from app.services import attachments as AT
    from app.services import nha_hang as NH
    ra = []
    for ten, data in tep:
        try:
            duoi = NH._kiem_tep_anh(ten, data)
        except NH.LoiNhaHang as ex:
            raise LoiDanhGia(str(ex))
        hien, nho, _r, _c = NH._lam_nhe(data)
        if hien is None:
            # Không mở được như ảnh (hoặc máy chủ thiếu thư viện ảnh): KHÔNG giữ bản gốc còn EXIF / vị trí.
            raise LoiDanhGia(f"Ảnh «{ten}» không mở được — chụp lại hoặc xuất JPG")
        ma = f"nh{nh.id}"
        try:
            a = AT.dinh_kem(db, "am_thuc", ma, f"dg.{duoi}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                            mo_ta=f"Ảnh khách đánh giá · {nh.ma}", boi=f"cong:kh-{tk.id}", nguon="he_thong")[0]
            b = AT.dinh_kem(db, "am_thuc", ma, f"dg.{duoi}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                            mo_ta=f"Ảnh nhỏ khách đánh giá · {nh.ma}", boi=f"cong:kh-{tk.id}", nguon="he_thong")[0]
        except ValueError as ex:
            raise LoiDanhGia(str(ex))
        ra.append({"hien": a.id, "nho": b.id, "an": False, "ly_do": ""})
    return ra


def viet(db: Session, tk: TaiKhoanNgoai, ma: str, d: dict, tep: list[tuple[str, bytes]] | None = None,
         giu_anh: list[int] | None = None, now: datetime | None = None) -> DanhGiaNhaHang:
    """Viết mới, hoặc sửa trong 7 ngày (thay hẳn bài cũ). `giu_anh`: chỉ số ảnh cũ muốn giữ khi sửa."""
    now = now or datetime.now()
    don = _don_cua(db, tk, ma)
    g = _cua_don(db, don.id)
    if g is None:
        if don.trang_thai != "da_dung":
            raise LoiDanhGia("Chỉ đánh giá được khi nhà hàng đã xác nhận bạn đã đến dùng bữa", 409)
        if now >= _han_viet(don):
            raise LoiDanhGia(f"Đã quá {HAN_VIET_NGAY} ngày sau bữa ăn — đánh giá đã đóng", 409)
    elif now >= g.tao_luc + timedelta(days=HAN_SUA_NGAY):
        raise LoiDanhGia(f"Chỉ sửa được trong {HAN_SUA_NGAY} ngày sau khi gửi", 409)
    if not d.get("dong_y"):
        raise LoiDanhGia("Đánh dấu đồng ý cho Vietourist hiện đánh giá trên trang nhà hàng")
    diem = _sao(d.get("diem"), True)
    phu = {k: _sao(d.get(k), False) for k in MUC}
    nx = (d.get("nhan_xet") or "").strip()
    if len(nx) > NHAN_XET_TOI_DA:
        raise LoiDanhGia(f"Nhận xét tối đa {NHAN_XET_TOI_DA:,} ký tự".replace(",", "."))
    nh = db.get(NhaHang, don.nha_hang_id)
    cu = list(g.anh or []) if g else []
    giu = [cu[i] for i in sorted(set(giu_anh or [])) if 0 <= i < len(cu)] if g else []
    tep = [t for t in (tep or []) if t[1]]
    if len(giu) + len(tep) > ANH_TOI_DA:
        raise LoiDanhGia(f"Tối đa {ANH_TOI_DA} ảnh")
    moi = _luu_anh(db, tk, nh, tep)
    if g is None:
        g = DanhGiaNhaHang(don_id=don.id, nha_hang_id=don.nha_hang_id, tai_khoan_id=tk.id, ten_hien=che_ten(tk.ho_ten or don.ten_khach),
                           ngay_an=don.ngay, so_khach=int(don.nguoi_lon or 0) + int(don.tre_em or 0), la_doan=bool(don.la_doan),
                           tao_luc=now)
        db.add(g)
        hd = "danh_gia_nh_viet"
    else:
        g.sua_luc = now
        hd = "danh_gia_nh_sua"
    g.diem, g.nhan_xet, g.anh = diem, nx, giu + moi
    for k, v in phu.items():
        setattr(g, k, v)
    db.flush()
    R.audit(db, f"cong:kh-{tk.id}", "khach", hd, f"danh_gia_nh:{g.id}", after={"don": don.ma, "diem": diem, "so_anh": len(g.anh)})
    db.commit(); db.refresh(g)
    return g


def _tb(xs: list[int]) -> float | None:
    xs = [x for x in xs if x]
    return round(sum(xs) / len(xs), 1) if xs else None


def _ra(g: DanhGiaNhaHang, rieng: bool = False, noi_bo: bool = False, nha_hang_ten: str = "") -> dict:
    anh = [{"i": i, "hien": f"/api/v1/am-thuc/anh/dg/{g.id}/{i}/hien", "nho": f"/api/v1/am-thuc/anh/dg/{g.id}/{i}/nho",
            **({"an": bool(a.get("an")), "ly_do": LY_DO_AN_DG.get(a.get("ly_do"), "")} if (rieng or noi_bo) else {})}
           for i, a in enumerate(g.anh or []) if (rieng or noi_bo) or not a.get("an")]
    r = {"id": g.id, "ten": g.ten_hien, "ngay_an": g.ngay_an.isoformat(), "so_khach": g.so_khach, "la_doan": g.la_doan,
         "diem": g.diem, **{k: getattr(g, k) for k in MUC}, "nhan_xet": g.nhan_xet, "anh": anh,
         "tao_luc": g.tao_luc.isoformat(timespec="minutes"), "da_sua": g.sua_luc is not None,
         "tra_loi": (g.tra_loi if g.tra_loi and not g.tra_loi_an else ""),
         "tra_loi_luc": g.tra_loi_luc.isoformat(timespec="minutes") if g.tra_loi_luc and not g.tra_loi_an else None}
    if rieng or noi_bo:
        r["an"] = g.an
        r["an_ly_do"] = LY_DO_AN_DG.get(g.an_ly_do, "")
    if noi_bo:
        r.update({"nha_hang_id": g.nha_hang_id, "nha_hang": nha_hang_ten, "don_id": g.don_id, "an_ghi_chu": g.an_ghi_chu,
                  "an_boi": g.an_boi, "an_luc": g.an_luc.isoformat(timespec="minutes") if g.an_luc else None,
                  "xem_lai": g.xem_lai, "xem_lai_boi": g.xem_lai_boi, "tra_loi": g.tra_loi, "tra_loi_an": g.tra_loi_an,
                  "tra_loi_an_ly_do": LY_DO_AN_DG.get(g.tra_loi_an_ly_do, ""), "tra_loi_boi": g.tra_loi_boi})
    return r


def tom_tat(db: Session, nids: list[int]) -> dict[int, dict]:
    """Điểm trung bình theo nhà hàng — chỉ bài đang hiện. Dưới 3 bài: diem_tb = None («Mới — chưa đủ đánh giá»)."""
    if not nids:
        return {}
    gs: dict[int, list] = {}
    for g in db.execute(select(DanhGiaNhaHang).where(DanhGiaNhaHang.nha_hang_id.in_(nids), DanhGiaNhaHang.an.is_(False))).scalars():
        gs.setdefault(g.nha_hang_id, []).append(g)
    ra = {}
    for nid in nids:
        ds = gs.get(nid, [])
        du = len(ds) >= TOI_THIEU_HIEN_DIEM
        ra[nid] = {"so_bai": len(ds), "du": du, "diem_tb": _tb([g.diem for g in ds]) if du else None,
                   "muc": ({k: _tb([getattr(g, k) for g in ds]) for k in MUC} if du else {}),
                   "phan_bo": ({s: sum(1 for g in ds if g.diem == s) for s in (5, 4, 3, 2, 1)} if du else {})}
    return ra


def cong(db: Session, nid: int, trang: int = 1, so: int = 20, xep: str = "moi") -> dict:
    """Trang khách: bài đang hiện của một nhà hàng (chỉ đọc)."""
    ds = db.execute(select(DanhGiaNhaHang).where(DanhGiaNhaHang.nha_hang_id == nid, DanhGiaNhaHang.an.is_(False))).scalars().all()
    if xep == "cao":
        ds.sort(key=lambda g: (-g.diem, -g.id))
    elif xep == "thap":
        ds.sort(key=lambda g: (g.diem, -g.id))
    elif xep == "anh":
        ds = [g for g in ds if any(not a.get("an") for a in (g.anh or []))]
        ds.sort(key=lambda g: -g.id)
    else:
        ds.sort(key=lambda g: -g.id)
    trang, so = max(1, int(trang or 1)), max(1, min(int(so or 20), 50))
    return {"tom_tat": tom_tat(db, [nid])[nid], "bai": [_ra(g) for g in ds[(trang - 1) * so: trang * so]], "tong": len(ds),
            "muc_ten": MUC_DG, "toi_thieu": TOI_THIEU_HIEN_DIEM}


def tep_anh(db: Session, gid: int, i: int, co: str):
    """Ảnh khách cho cổng: bài đang hiện, ảnh chưa bị ẩn, của nhà hàng đang hiện; chỉ bản làm nhẹ."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    g = db.get(DanhGiaNhaHang, gid)
    if g is None or g.an or co not in ("hien", "nho") or not 0 <= i < len(g.anh or []) or g.anh[i].get("an"):
        raise LoiDanhGia("Không có ảnh này", 404)
    nh = db.get(NhaHang, g.nha_hang_id)
    if nh is None or not nh.hien_cong or nh.ngung:
        raise LoiDanhGia("Không có ảnh này", 404)
    a = db.get(Attachment, g.anh[i][co])
    return AT.doc(db, a), a


# ── nội bộ VTOS ─────────────────────────────────────────────────────────────────────────────────────────
def _co(u: User, vai) -> bool:
    return u.role in vai


def ds_noi_bo(db: Session, u: User, loc: str = "", now: datetime | None = None) -> dict:
    from app.services import nha_hang as NH
    if not _co(u, NH.VAI_XEM):
        raise LoiDanhGia("Không có quyền", 403)
    now = now or datetime.now()
    ds = db.execute(select(DanhGiaNhaHang).order_by(DanhGiaNhaHang.id.desc())).scalars().all()
    ten = {n.id: n.ten for n in db.execute(select(NhaHang)).scalars()}
    dem = {"ba_muoi_ngay": sum(1 for g in ds if g.tao_luc >= now - timedelta(days=30)),
           "thap_chua_tra_loi": sum(1 for g in ds if g.diem <= 2 and not g.an and not g.tra_loi),
           "cho_xem_lai": sum(1 for g in ds if (g.an or any(a.get("an") for a in g.anh or []) or g.tra_loi_an) and not g.xem_lai),
           "chua_cham": _don_chua_cham(db, now)}
    f = {"thap": lambda g: g.diem <= 2, "anh": lambda g: bool(g.anh), "chua_tra_loi": lambda g: not g.tra_loi,
         "da_an": lambda g: g.an or g.tra_loi_an or any(a.get("an") for a in g.anh or [])}.get(loc)
    if f:
        ds = [g for g in ds if f(g)]
    return {"bai": [_ra(g, noi_bo=True, nha_hang_ten=ten.get(g.nha_hang_id, "")) for g in ds[:300]], "dem": dem,
            "ly_do": LY_DO_AN_DG, "muc_ten": MUC_DG, "duoc_an": _co(u, VAI_AN), "duoc_xem_lai": _co(u, VAI_XEM_LAI)}


def _don_chua_cham(db: Session, now: datetime) -> int:
    co = {x for x in db.execute(select(DanhGiaNhaHang.don_id)).scalars()}
    tu = (now - timedelta(days=HAN_VIET_NGAY)).date()
    return sum(1 for d in db.execute(select(DonDatBan.id).where(DonDatBan.trang_thai == "da_dung", DonDatBan.ngay >= tu)).scalars()
               if d not in co)


def an(db: Session, u: User, gid: int, ly_do: str, ghi_chu: str, phan: str = "bai", now: datetime | None = None) -> DanhGiaNhaHang:
    """Ẩn VÌ VI PHẠM. phan: "bai" | "anh:<i>" | "tra_loi". Lý do «bài chê / không đúng» không có trong danh sách."""
    if not _co(u, VAI_AN):
        raise LoiDanhGia("Chỉ NV / PTGĐ Marketing ẩn đánh giá vi phạm", 403)
    if ly_do not in LY_DO_AN_DG:
        raise LoiDanhGia("Chọn một lý do vi phạm: " + ", ".join(LY_DO_AN_DG.values()))
    ghi_chu = (ghi_chu or "").strip()
    if len(ghi_chu) < 5:
        raise LoiDanhGia("Ghi thêm chỗ vi phạm (ít nhất 5 ký tự) để TP Điều hành xem lại")
    now = now or datetime.now()
    g = db.get(DanhGiaNhaHang, gid)
    if g is None:
        raise LoiDanhGia("Không có đánh giá này", 404)
    if phan == "bai":
        if g.an:
            raise LoiDanhGia("Bài đã ẩn", 409)
        g.an = True
    elif phan == "tra_loi":
        if not g.tra_loi or g.tra_loi_an:
            raise LoiDanhGia("Không có lời trả lời đang hiện", 409)
        g.tra_loi_an, g.tra_loi_an_ly_do = True, ly_do
    elif phan.startswith("anh:"):
        try:
            i = int(phan[4:])
        except ValueError:
            i = -1
        anh = [dict(a) for a in (g.anh or [])]
        if not 0 <= i < len(anh) or anh[i].get("an"):
            raise LoiDanhGia("Không có ảnh này", 404)
        anh[i]["an"], anh[i]["ly_do"] = True, ly_do
        g.anh = anh
    else:
        raise LoiDanhGia("Phần cần ẩn không hợp lệ")
    if phan == "bai" or not g.an_ly_do:
        g.an_ly_do = ly_do
    g.an_ghi_chu = f"[{phan}] {ghi_chu[:GHI_CHU_TOI_DA]}"
    g.an_boi, g.an_luc, g.xem_lai, g.xem_lai_boi, g.xem_lai_luc = u.username, now, "", "", None
    R.audit(db, u.username, u.role, "danh_gia_nh_an", f"danh_gia_nh:{g.id}", after={"phan": phan, "ly_do": ly_do, "ghi_chu": ghi_chu[:200]})
    db.commit(); db.refresh(g)
    return g


def xem_lai(db: Session, u: User, gid: int, giu: bool, ghi_chu: str = "", now: datetime | None = None) -> DanhGiaNhaHang:
    """TP Điều hành xem lại: giữ ẩn, hoặc hiện lại MỌI phần đang ẩn của bài. Người ẩn không tự xem lại."""
    if not _co(u, VAI_XEM_LAI):
        raise LoiDanhGia("Chỉ TP Điều hành xem lại bài bị ẩn", 403)
    now = now or datetime.now()
    g = db.get(DanhGiaNhaHang, gid)
    if g is None:
        raise LoiDanhGia("Không có đánh giá này", 404)
    if not (g.an or g.tra_loi_an or any(a.get("an") for a in g.anh or [])):
        raise LoiDanhGia("Bài này không có phần nào đang ẩn", 409)
    if g.an_boi == u.username:
        raise LoiDanhGia("Người ẩn không tự xem lại — cần người thứ hai", 403)
    if not giu:
        g.an, g.tra_loi_an, g.tra_loi_an_ly_do = False, False, ""
        g.anh = [{**a, "an": False, "ly_do": ""} for a in (g.anh or [])]
    g.xem_lai, g.xem_lai_boi, g.xem_lai_luc = ("giu" if giu else "hien"), u.username, now
    R.audit(db, u.username, u.role, "danh_gia_nh_xem_lai", f"danh_gia_nh:{g.id}", after={"giu": giu, "ghi_chu": (ghi_chu or "")[:200]})
    db.commit(); db.refresh(g)
    return g


def xuat_xlsx(db: Session, u: User) -> bytes:
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font
    b = ds_noi_bo(db, u)
    wb = Workbook(); ws = wb.active; ws.title = "Đánh giá"
    dau = ["Nhà hàng", "Ngày ăn", "Khách", "Số khách", "Sao", *MUC_DG.values(), "Nhận xét", "Số ảnh", "Nhà hàng trả lời",
           "Đang ẩn", "Lý do ẩn", "Xem lại", "Viết lúc"]
    ws.append(dau)
    for c in ws[1]:
        c.font = Font(bold=True)
    for o in b["bai"]:
        ws.append([o["nha_hang"], o["ngay_an"], o["ten"], o["so_khach"], o["diem"], *[o[k] for k in MUC], o["nhan_xet"],
                   len(o["anh"]), o["tra_loi"], "Có" if o["an"] else "", o["an_ly_do"], {"giu": "Giữ ẩn", "hien": "Hiện lại"}.get(o["xem_lai"], ""),
                   o["tao_luc"]])
    for col, w in zip("ABCDEFGHIJKLMNOPQ", (28, 12, 14, 9, 6, 8, 8, 10, 12, 60, 8, 40, 8, 26, 10, 18)):
        ws.column_dimensions[col].width = w
    o = BytesIO(); wb.save(o)
    return o.getvalue()


# ── cổng NCC: nhà hàng trả lời ──────────────────────────────────────────────────────────────────────────
def _nh_cua_ncc(db: Session, s) -> dict[int, str]:
    return {n.id: n.ten for n in db.execute(select(NhaHang).where(NhaHang.supplier_id == s.id)).scalars()}


def ds_ncc(db: Session, s) -> dict:
    nh = _nh_cua_ncc(db, s)
    if not nh:
        return {"nha_hang": [], "bai": []}
    ds = db.execute(select(DanhGiaNhaHang).where(DanhGiaNhaHang.nha_hang_id.in_(list(nh)), DanhGiaNhaHang.an.is_(False))
                    .order_by(DanhGiaNhaHang.id.desc())).scalars().all()
    tt = tom_tat(db, list(nh))
    now = datetime.now()
    return {"nha_hang": [{"id": k, "ten": v, **tt[k]} for k, v in nh.items()],
            "bai": [{**_ra(g), "nha_hang": nh[g.nha_hang_id], "tra_loi_cua_minh": g.tra_loi,
                     "duoc_tra_loi": not g.tra_loi, "duoc_sua_tra_loi": bool(g.tra_loi) and not g.tra_loi_an and g.tra_loi_luc is not None
                     and now < g.tra_loi_luc + timedelta(hours=HAN_SUA_TRA_LOI_GIO), "tra_loi_bi_an": g.tra_loi_an}
                    for g in ds[:300]],
            "muc_ten": MUC_DG}


def tra_loi(db: Session, tk: TaiKhoanNgoai, s, gid: int, noi_dung: str, now: datetime | None = None) -> DanhGiaNhaHang:
    now = now or datetime.now()
    g = db.get(DanhGiaNhaHang, gid)
    if g is None or g.nha_hang_id not in _nh_cua_ncc(db, s) or g.an:
        raise LoiDanhGia("Không có đánh giá này", 404)
    nd = (noi_dung or "").strip()
    if not nd:
        raise LoiDanhGia("Viết nội dung trả lời")
    if len(nd) > TRA_LOI_TOI_DA:
        raise LoiDanhGia(f"Trả lời tối đa {TRA_LOI_TOI_DA} ký tự")
    if g.tra_loi:
        if g.tra_loi_an or g.tra_loi_luc is None or now >= g.tra_loi_luc + timedelta(hours=HAN_SUA_TRA_LOI_GIO):
            raise LoiDanhGia(f"Mỗi bài trả lời một lần; chỉ sửa được trong {HAN_SUA_TRA_LOI_GIO} giờ", 409)
    else:
        g.tra_loi_luc = now
    g.tra_loi, g.tra_loi_boi = nd, f"cong:ncc-{tk.id}"
    R.audit(db, f"cong:ncc-{tk.id}", "ncc", "danh_gia_nh_tra_loi", f"danh_gia_nh:{g.id}", after={"do_dai": len(nd)})
    db.commit(); db.refresh(g)
    return g
