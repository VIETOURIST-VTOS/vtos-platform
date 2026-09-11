"""Nhà cung cấp & đặt dịch vụ – mục còn trống của nhóm Điều hành."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User, Tour
from app.models.suppliers import (Supplier, SupplierBankChange, ServiceOrder, LOAI_NCC, TRANG_THAI_DON,
                                  TRANG_THAI_DOI_TK)
from app.services import suppliers as S, rules as R

router = APIRouter(prefix="/api/v1/ncc", tags=["ncc"])

READ = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt")
WRITE = ("tp_dh", "nv_dh", "cntt")                 # Điều hành đặt dịch vụ
# Xác nhận đổi số tài khoản: người thứ hai, và phải là người cầm tiền hoặc lãnh đạo – không phải người đặt.
DUYET_TK = ("ketoan", "chutich", "tgd")


@router.get("/danh-muc")
def danh_muc(u: User = Depends(require_roles(*READ))):
    return {"loai_ncc": LOAI_NCC, "trang_thai_don": TRANG_THAI_DON, "trang_thai_doi_tk": TRANG_THAI_DOI_TK,
            "ghi_chu": "Số tài khoản nhà cung cấp chỉ đổi được qua đề nghị có người thứ hai xác nhận."}


def _ncc_out(db: Session, s: Supplier) -> dict:
    return {"id": s.id, "code": s.code, "ten": s.ten, "loai": s.loai,
            "loai_ten": LOAI_NCC.get(s.loai, s.loai), "ma_so_thue": s.ma_so_thue,
            "nguoi_lien_he": s.nguoi_lien_he, "dien_thoai": s.dien_thoai, "email": s.email,
            "dia_chi": s.dia_chi, "so_tai_khoan": s.so_tai_khoan, "ngan_hang": s.ngan_hang,
            "chu_tai_khoan": s.chu_tai_khoan, "dieu_khoan_tt": s.dieu_khoan_tt,
            "active": s.active, "note": s.note, "canh_bao": S.canh_bao(db, s)}


@router.get("")
def ds_ncc(q: str = "", loai: str = "", gom_ngung: bool = False,
           u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    sel = select(Supplier).order_by(Supplier.ten)
    if not gom_ngung: sel = sel.where(Supplier.active == True)
    if loai: sel = sel.where(Supplier.loai == loai)
    rows = [s for s in db.execute(sel).scalars()
            if not q or q.lower() in (s.ten + s.code + s.ma_so_thue).lower()]
    return [_ncc_out(db, s) for s in rows[:500]]


class NccIn(BaseModel):
    ten: str
    loai: str = "khac"
    ma_so_thue: str = ""
    dia_chi: str = ""
    nguoi_lien_he: str = ""
    dien_thoai: str = ""
    email: str = ""
    so_tai_khoan: str = ""
    ngan_hang: str = ""
    chu_tai_khoan: str = ""
    dieu_khoan_tt: str = ""
    note: str = ""


@router.post("", status_code=201)
def tao_ncc(data: NccIn, u: User = Depends(require_roles(*WRITE, "ketoan")), db: Session = Depends(get_db)):
    try:
        s = S.tao_ncc(db, data.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "tao_nha_cung_cap", f"ncc:{s.code}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": s.id, "code": s.code, "canh_bao": S.canh_bao(db, s),
            "message": f"Đã thêm nhà cung cấp {s.code} – {s.ten}"}


class NccSua(BaseModel):
    """KHÔNG có số tài khoản ở đây: đổi tài khoản đi đường riêng, có người thứ hai xác nhận."""
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm
    ten: str | None = None
    loai: str | None = None
    ma_so_thue: str | None = None
    dia_chi: str | None = None
    nguoi_lien_he: str | None = None
    dien_thoai: str | None = None
    email: str | None = None
    dieu_khoan_tt: str | None = None
    note: str | None = None
    active: bool | None = None


@router.put("/{sid}")
def sua_ncc(sid: int, data: NccSua, u: User = Depends(require_roles(*WRITE, "ketoan")),
            db: Session = Depends(get_db)):
    """Sửa hồ sơ nhà cung cấp. Số tài khoản KHÔNG sửa được ở đây – xem POST /{id}/doi-tai-khoan."""
    s = db.get(Supplier, sid)
    if s is None: raise HTTPException(404, "Không có nhà cung cấp này")
    d = data.model_dump(exclude_none=True)
    if "loai" in d and d["loai"] not in LOAI_NCC:
        raise HTTPException(422, f"Loại không hợp lệ. Chỉ nhận {', '.join(LOAI_NCC)}")
    before = {"ten": s.ten, "active": s.active}
    from app.services import ghi_mot_lan as GML
    GML.kiem_phien_ban(s, d.pop("phien_ban", None), f"Nhà cung cấp {s.code}",
                       lambda: {**before, "phien_ban": s.phien_ban})
    for k, v in d.items(): setattr(s, k, v)
    GML.tang_phien_ban(s)
    R.audit(db, u.username, u.role, "sua_nha_cung_cap", f"ncc:{s.code}", before=before,
            after=data.model_dump(mode="json", exclude_none=True))
    db.commit()
    return {"message": f"Đã cập nhật {s.code}", "canh_bao": S.canh_bao(db, s)}


class DoiTkIn(BaseModel):
    so_tk_moi: str
    ngan_hang_moi: str = ""
    chu_tk_moi: str = ""
    ly_do: str = ""
    chung_tu: str = ""


@router.post("/{sid}/doi-tai-khoan", status_code=201)
def de_nghi_doi_tk(sid: int, data: DoiTkIn, u: User = Depends(require_roles(*WRITE, "ketoan")),
                   db: Session = Depends(get_db)):
    """Đề nghị đổi số tài khoản. CHƯA có hiệu lực – số cũ vẫn là số dùng để chi cho tới khi người thứ hai
    xác nhận."""
    s = db.get(Supplier, sid)
    if s is None: raise HTTPException(404, "Không có nhà cung cấp này")
    try:
        c = S.de_nghi_doi_tk(db, s, data.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "de_nghi_doi_tk_ncc", f"ncc:{s.code}",
            before={"so_tk": c.so_tk_cu}, after={"so_tk_moi": c.so_tk_moi, "chung_tu": c.chung_tu})
    db.commit()
    return {"id": c.id, "status": c.status,
            "message": "Đã ghi đề nghị đổi tài khoản. Số đang hiệu lực CHƯA đổi – cần người thứ hai xác nhận."}


@router.get("/doi-tai-khoan/cho-xac-nhan")
def ds_cho_xac_nhan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    ten = {s.id: s.ten for s in db.execute(select(Supplier)).scalars()}
    rows = db.execute(select(SupplierBankChange).where(SupplierBankChange.status == "cho_xac_nhan")
                      .order_by(SupplierBankChange.id.desc())).scalars()
    return [{"id": c.id, "supplier_id": c.supplier_id, "ncc": ten.get(c.supplier_id, ""),
             "so_tk_cu": c.so_tk_cu, "ngan_hang_cu": c.ngan_hang_cu,
             "so_tk_moi": c.so_tk_moi, "ngan_hang_moi": c.ngan_hang_moi, "chu_tk_moi": c.chu_tk_moi,
             "ly_do": c.ly_do, "chung_tu": c.chung_tu, "de_nghi_boi": c.de_nghi_boi,
             "de_nghi_luc": c.de_nghi_luc} for c in rows]


class XacNhanIn(BaseModel):
    dong_y: bool
    ghi_chu: str = ""


@router.post("/doi-tai-khoan/{cid}/xac-nhan")
def xac_nhan_doi_tk(cid: int, data: XacNhanIn, u: User = Depends(require_roles(*DUYET_TK)),
                    db: Session = Depends(get_db)):
    c = db.get(SupplierBankChange, cid)
    if c is None: raise HTTPException(404, "Không có đề nghị này")
    try:
        kq = S.xac_nhan_doi_tk(db, c, u.username, data.dong_y, data.ghi_chu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "xac_nhan_doi_tk_ncc", f"ncc:{c.supplier_id}",
            before={"so_tk": c.so_tk_cu}, after={"so_tk": c.so_tk_moi, "ket_qua": kq["status"]})
    db.commit()
    return kq


# ====================== ĐƠN ĐẶT DỊCH VỤ ======================
class DonIn(BaseModel):
    supplier_id: int
    tour_id: int
    loai: str = ""
    noi_dung: str
    ngay_su_dung: date | None = None
    # VPM-17 – ngày tiền phải rời tài khoản. KHÁC `ngay_su_dung` ở trên: ngày dùng dịch vụ là ngày
    # khách lên xe, hai ngày có thể cách nhau hàng tháng. Để trống được, và trống thì đơn hiện ở
    # danh sách còn thiếu ngày chứ không bị gán ngày dùng thay thế.
    ngay_den_han: date | None = None
    so_luong: float = 1
    don_vi: str = ""
    don_gia: float | None = None
    thanh_tien: float | None = None
    note: str = ""


@router.post("/don", status_code=201)
def tao_don(data: DonIn, u: User = Depends(require_roles(*WRITE, "ketoan")), db: Session = Depends(get_db)):
    try:
        d = S.tao_don(db, data.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "dat_dich_vu", f"don:{d.code}", after=data.model_dump(mode="json"))
    db.commit()
    return {"id": d.id, "code": d.code, "thanh_tien": d.thanh_tien,
            "message": f"Đã tạo đơn đặt dịch vụ {d.code}"}


@router.get("/don")
def ds_don(tour_id: int | None = None, supplier_id: int | None = None, status: str = "",
           u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    ten = {s.id: s.ten for s in db.execute(select(Supplier)).scalars()}
    tours = {t.id: t.code for t in db.execute(select(Tour)).scalars()}
    q = select(ServiceOrder).order_by(ServiceOrder.id.desc())
    if tour_id: q = q.where(ServiceOrder.tour_id == tour_id)
    if supplier_id: q = q.where(ServiceOrder.supplier_id == supplier_id)
    if status: q = q.where(ServiceOrder.status == status)
    rows = list(db.execute(q.limit(500)).scalars())
    return {"rows": [{"id": d.id, "code": d.code, "ncc": ten.get(d.supplier_id, ""),
                      "supplier_id": d.supplier_id, "tour": tours.get(d.tour_id, ""), "tour_id": d.tour_id,
                      "loai": d.loai, "loai_ten": LOAI_NCC.get(d.loai, d.loai), "noi_dung": d.noi_dung,
                      "ngay_su_dung": d.ngay_su_dung, "so_luong": d.so_luong, "don_vi": d.don_vi,
                      "don_gia": d.don_gia, "thanh_tien": d.thanh_tien, "status": d.status,
                      "status_ten": TRANG_THAI_DON.get(d.status, d.status),
                      "xac_nhan_ncc": d.xac_nhan_ncc, "boi": d.created_by,
                      "ngay_den_han": d.ngay_den_han, "ngay_den_han_boi": d.ngay_den_han_boi}
                     for d in rows],
            "tong_tien": float(round(sum((d.thanh_tien or 0) for d in rows if d.status != "huy")))}


class ChuyenTrangThaiIn(BaseModel):
    status: str
    xac_nhan_ncc: str = ""


@router.post("/don/{did}/trang-thai")
def chuyen_trang_thai(did: int, data: ChuyenTrangThaiIn, u: User = Depends(require_roles(*WRITE, "ketoan")),
                      db: Session = Depends(get_db)):
    d = db.get(ServiceOrder, did)
    if d is None: raise HTTPException(404, "Không có đơn này")
    try:
        kq = S.chuyen_trang_thai(db, d, data.status, u.username, data.xac_nhan_ncc)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "trang_thai_don_dich_vu", f"don:{d.code}", after=data.model_dump(mode="json"))
    db.commit()
    return kq


# ══════════════════════════════════════════════════════════════════════════════
# VPM-17 – CỬA NHẬP NGÀY ĐẾN HẠN CHO ĐƠN ĐẶT DỊCH VỤ
#
# Đơn đã được nhà cung cấp xác nhận mà CHƯA lập đề nghị chi vẫn là nghĩa vụ thật – mục III.4 của đề
# xuất đòi bảng dòng tiền gồm cả "nghĩa vụ chưa lập đề nghị chi". Không có ngày ở đây thì chúng nằm
# mãi trong rổ "Chưa đủ dữ liệu dự báo".
#
# Vai trò: WRITE của phân hệ này là Điều hành (người đặt dịch vụ), cộng Kế toán — đúng dòng
# "Trả nhà cung cấp · Điều hành + Kế toán" ở bảng cửa nhập mục III.4. Giống hệt cửa tạo đơn và cửa
# chuyển trạng thái ngay trên, không mở rộng thêm vai trò nào.
# ══════════════════════════════════════════════════════════════════════════════

class NgayDenHanDonIn(BaseModel):
    # Gửi rỗng = gỡ ngày, quay về "chưa biết". Nhập nhầm phải sửa lại được.
    ngay_den_han: date | None = None
    ly_do: str = ""


@router.put("/don/{did}/ngay-den-han")
def dat_ngay_den_han_don(did: int, data: NgayDenHanDonIn,
                         u: User = Depends(require_roles(*WRITE, "ketoan")),
                         db: Session = Depends(get_db)):
    """Gõ hoặc sửa ngày phải trả của một đơn đặt dịch vụ."""
    d = db.get(ServiceOrder, did)
    if d is None: raise HTTPException(404, "Không có đơn đặt dịch vụ")
    if d.status == "huy":
        raise HTTPException(422, f"Đơn {d.code} đã huỷ – không đặt ngày đến hạn")
    truoc = d.ngay_den_han
    d.ngay_den_han = data.ngay_den_han
    d.ngay_den_han_boi = u.username if data.ngay_den_han else ""
    d.ngay_den_han_luc = datetime.now() if data.ngay_den_han else None
    R.audit(db, u.username, u.role, "dat_ngay_den_han_don_dich_vu", f"don:{d.code}",
            before={"ngay_den_han": str(truoc or "")},
            after={"ngay_den_han": str(data.ngay_den_han or ""), "ly_do": data.ly_do[:200]})
    db.commit()
    if data.ngay_den_han is None:
        return {"ngay_den_han": None,
                "message": f"Đã gỡ ngày đến hạn của {d.code} – đơn này quay lại danh sách chưa có hạn"}
    return {"ngay_den_han": d.ngay_den_han,
            "message": f"{d.code}: hạn trả {data.ngay_den_han:%d/%m/%Y}"}


@router.get("/don/thieu-ngay-den-han")
def don_thieu_ngay_den_han(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Đơn dịch vụ đã thành nghĩa vụ (NCC xác nhận / đã dùng) mà chưa ai gõ ngày phải trả."""
    ten = {s.id: s.ten for s in db.execute(select(Supplier)).scalars()}
    tours = {t.id: t.code for t in db.execute(select(Tour)).scalars()}
    ds = list(db.execute(select(ServiceOrder).where(
        ServiceOrder.status.in_(("da_xac_nhan", "da_su_dung")),
        ServiceOrder.ngay_den_han.is_(None)).order_by(desc(ServiceOrder.thanh_tien)).limit(300)).scalars())
    return {"so_khoan": len(ds),
            "tong_tien": float(round(sum((d.thanh_tien or 0) for d in ds))),
            "chi_tiet": [{"id": d.id, "code": d.code, "ncc": ten.get(d.supplier_id, ""),
                          "tour": tours.get(d.tour_id, ""), "noi_dung": d.noi_dung,
                          "thanh_tien": d.thanh_tien, "ngay_su_dung": d.ngay_su_dung,
                          "status": d.status, "boi": d.created_by} for d in ds]}
