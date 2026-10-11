# -*- coding: utf-8 -*-
"""CỬA 4.4.2 CHƯƠNG TRÌNH TỪNG CHUYẾN.

Gắn màn hình `/tours` đã có — tab mới trên trang chi tiết chuyến, không dựng màn hình riêng:
chương trình là một mặt của chuyến, đứng cạnh Dự toán, Booking, HDV & xe.

XEM rộng bằng đúng những người mở được trang chuyến (Kinh doanh phải đọc được chương trình để trả
lời khách). GHI hẹp: chỉ Điều hành và hai vai nền — người chịu trách nhiệm chuyến là người soạn.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import chuong_trinh_tour as CT
from app.services.access import BASE_VIEW, FULL_VIEW, SALES, SALES_ADMIN, OPERATIONS

router = APIRouter(prefix="/api/v1/chuong-trinh", tags=["chuong-trinh"])

XEM = BASE_VIEW + SALES + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt")
# GHI đi qua FULL_VIEW, KHÔNG qua BASE_VIEW. Hai nhóm khác nhau đúng ở hai vai: `BASE_VIEW` gồm cả
# READ_ALL (`bks`, `robot_ks`). Lớp `READ_ONLY_ROLES` ở access.py chặn mọi lệnh ghi của hai vai ấy,
# nên viết BASE_VIEW vào đây không hở quyền — nhưng danh sách lại ĐỌC RA như thể Ban kiểm soát soạn
# được chương trình tour, và người sửa mã sau này tin vào danh sách chứ không đi tìm lớp chặn. Một
# hàng rào đúng nhờ một tệp khác là hàng rào sẽ mòn. Viết đúng người ở đây, và phép kiểm
# test_bks_va_robot_ks_khong_ghi_duoc_du_lop_chan_o_tep_khac đo luôn cả lớp chặn kia.
GHI = FULL_VIEW + OPERATIONS + ("cntt",)


class SuaIn(BaseModel):
    tieu_de: str | None = None
    noi_dung: str | None = None
    bua_sang: bool | None = None
    bua_trua: bool | None = None
    bua_toi: bool | None = None
    khach_san: str | None = None
    phuong_tien: str | None = None
    ghi_chu: str | None = None
    ly_do: str = ""


class XoaIn(BaseModel):
    ly_do: str


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return CT.meta()


@router.get("/{tour_id}")
def xem(tour_id: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    try:
        return CT.xem(db, tour_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{tour_id}/mo")
def mo(tour_id: int, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    """Dựng khung ngày RỖNG và chụp lại bản sản phẩm. Không đổ nội dung sản phẩm vào."""
    try:
        r = CT.mo(db, u, tour_id)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.get("/{tour_id}/de-xuat-tach")
def de_xuat_tach(tour_id: int, u: User = Depends(require_roles(*XEM)),
                 db: Session = Depends(get_db)):
    """ĐỀ XUẤT tách bản sản phẩm thành từng ngày. KHÔNG ghi gì — đọc rồi mới bấm nhận."""
    try:
        return CT.de_xuat_tach(CT.xem(db, tour_id)["ban_san_pham_goc"])
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{tour_id}/nhan-de-xuat")
def nhan_de_xuat(tour_id: int, u: User = Depends(require_roles(*GHI)),
                 db: Session = Depends(get_db)):
    try:
        r = CT.nhan_de_xuat(db, u, tour_id)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.put("/{tour_id}/ngay/{ngay_thu}")
def sua_ngay(tour_id: int, ngay_thu: int, body: SuaIn,
             u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    o = {k: v for k, v in body.model_dump().items() if k != "ly_do" and v is not None}
    try:
        r = CT.sua_ngay(db, u, tour_id, ngay_thu, o, body.ly_do)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.post("/{tour_id}/them-ngay")
def them_ngay(tour_id: int, u: User = Depends(require_roles(*GHI)),
              db: Session = Depends(get_db)):
    try:
        r = CT.them_ngay(db, u, tour_id)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.delete("/{tour_id}/ngay/{ngay_thu}")
def xoa_ngay(tour_id: int, ngay_thu: int, body: XoaIn,
             u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    try:
        r = CT.xoa_ngay(db, u, tour_id, ngay_thu, body.ly_do)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
