# -*- coding: utf-8 -*-
"""CỬA 5.9.2 ĐỀ NGHỊ MUA và 5.9.3 CẤP PHÁT TÀI SẢN (Chủ tịch chốt 08/10/2026).

    /api/v1/de-nghi-mua → màn hình MỚI /de-nghi-mua, mở cho MỌI NGƯỜI LÀM VIỆC Ở ĐÂY
    /api/v1/cap-phat    → gắn màn hình /tai-san đã có (HCNS lập)

VÌ SAO ĐỀ NGHỊ MUA PHẢI CÓ MÀN HÌNH RIÊNG, VÀ MỞ RỘNG. Người đề nghị mua là người của MỌI phòng —
Kinh doanh hỏng máy in, Điều hành thiếu sim data. Gắn cửa ấy vào /tai-san (chỉ mở cho Kế toán,
CNTT, hành chính, HCNS) thì chín phòng còn lại không có đường gửi, và họ sẽ nhắn Zalo như hôm nay.
Cửa mở mà người không với tới thì cửa ấy chưa tồn tại.

Mở MÀN HÌNH rộng không phải mở QUYỀN: ba việc nặng vẫn hẹp, và hẹp ở tầng dịch vụ chứ không ở đây —
tạo đề nghị (ai cũng được), DUYỆT (chỉ TGĐ / Chủ tịch), GHI ĐÃ CHI (chỉ Kế toán). Một người thường
mở màn hình chỉ thấy đề nghị của mình và nút gửi.

5.9.3 KHÔNG mở rộng: Chủ tịch chốt "cấp phát tài sản do HCNS làm", nên nó ở lại /tai-san.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import mua_sam_cap_phat as MS
from app.services.access import BASE_VIEW, MOI_NHAN_VIEN, READ_ALL

router_mua = APIRouter(prefix="/api/v1/de-nghi-mua", tags=["mua-sam"])
router_cap = APIRouter(prefix="/api/v1/cap-phat", tags=["mua-sam"])

MO_CHO_MOI_NGUOI = MOI_NHAN_VIEN + READ_ALL
XEM_CAP_PHAT = BASE_VIEW + ("ketoan", "cntt", "hanh_chinh", "hcns")


class DeNghiIn(BaseModel):
    noi_dung: str
    so_luong: float = 1
    don_vi: str = "cái"
    uoc_tinh: float | None = None
    ly_do: str = ""
    muc_do: str = "thuong"
    can_truoc_ngay: date | None = None


class DuyetIn(BaseModel):
    dong_y: bool
    ghi_chu: str = ""


class ChiIn(BaseModel):
    so_tien: float
    chung_tu_ref: str = ""


class CapPhatIn(BaseModel):
    employee_id: int
    cap_ngay: date
    ten_tai_san: str = ""
    asset_id: int | None = None
    so_luong: float = 1
    don_vi: str = "cái"
    muc_dich: str = ""
    tinh_trang_khi_cap: str = ""
    ghi_chu: str = ""


class TraIn(BaseModel):
    tra_ngay: date
    tinh_trang: str
    mat_hong: bool = False


@router_mua.get("/meta")
def meta(u: User = Depends(require_roles(*MO_CHO_MOI_NGUOI))):
    return MS.meta()


@router_mua.get("")
def danh_sach(trang_thai: str = "", phong: str = "",
              u: User = Depends(require_roles(*MO_CHO_MOI_NGUOI)), db: Session = Depends(get_db)):
    return {"rows": MS.danh_sach_de_nghi(db, trang_thai, phong)}


@router_mua.post("")
def tao(body: DeNghiIn, u: User = Depends(require_roles(*MOI_NHAN_VIEN)),
        db: Session = Depends(get_db)):
    try:
        return MS.tao_de_nghi(db, u, **body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router_mua.post("/{de_nghi_id}/duyet")
def duyet(de_nghi_id: int, body: DuyetIn,
          u: User = Depends(require_roles(*MS.VAI_DUYET_MUA)), db: Session = Depends(get_db)):
    try:
        return MS.duyet(db, u, de_nghi_id, body.dong_y, body.ghi_chu)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router_mua.post("/{de_nghi_id}/da-chi")
def da_chi(de_nghi_id: int, body: ChiIn,
           u: User = Depends(require_roles(*MS.VAI_CHI)), db: Session = Depends(get_db)):
    try:
        return MS.ghi_da_chi(db, u, de_nghi_id, body.so_tien, body.chung_tu_ref)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── 5.9.3 ─────────────────────────────────────────────────────────────────────────────────────
@router_cap.get("")
def danh_sach_cap_phat(trang_thai: str = "", phong: str = "",
                       u: User = Depends(require_roles(*XEM_CAP_PHAT)),
                       db: Session = Depends(get_db)):
    return {"rows": MS.danh_sach_cap_phat(db, trang_thai, phong)}


@router_cap.get("/dang-giu/{employee_id}")
def dang_giu(employee_id: int, u: User = Depends(require_roles(*XEM_CAP_PHAT)),
             db: Session = Depends(get_db)):
    """Người này đang giữ những gì — câu HCNS phải hỏi mỗi lần có người nghỉ việc."""
    return {"rows": MS.dang_giu_cua_nguoi(db, employee_id)}


@router_cap.post("")
def cap_phat(body: CapPhatIn, u: User = Depends(require_roles(*MS.VAI_CAP_PHAT)),
             db: Session = Depends(get_db)):
    try:
        return MS.cap_phat(db, u, **body.model_dump())
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router_cap.post("/{cap_phat_id}/tra")
def ghi_tra(cap_phat_id: int, body: TraIn, u: User = Depends(require_roles(*MS.VAI_CAP_PHAT)),
            db: Session = Depends(get_db)):
    try:
        return MS.ghi_tra(db, u, cap_phat_id, body.tra_ngay, body.tinh_trang, body.mat_hong)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
