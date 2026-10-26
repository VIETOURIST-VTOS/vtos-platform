"""KH-4 · Hai màn VTOS nhận việc từ cổng khách: Yêu cầu khách (đổi / hủy / hóa đơn / khác) và Góp ý
riêng lãnh đạo (Chủ tịch + TGĐ trả lời; BKS đọc theo luật chung)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.core import User
from app.api.deps import require_roles
from app.services import cham_soc_khach as CK

router = APIRouter(prefix="/api/v1/yeu-cau-khach", tags=["yeu-cau-khach"])
router_gop_y = APIRouter(prefix="/api/v1/gop-y-lanh-dao", tags=["gop-y-lanh-dao"])

VAI_YEU_CAU = tuple(dict.fromkeys(CK.VAI_XEM_HET + sum(CK.VAI_BO_PHAN.values(), ())))


@router.get("")
def ds(trang_thai: str = "mo", u: User = Depends(require_roles(*VAI_YEU_CAU)), db: Session = Depends(get_db)):
    from app.models.cham_soc_khach import TRANG_THAI_VIEC, BO_PHAN
    return {"dong": CK.ds_ho_tro(db, u, trang_thai), "trang_thai": TRANG_THAI_VIEC, "bo_phan": BO_PHAN}


class CapNhatIn(BaseModel):
    hanh_dong: str
    tra_loi: str = ""
    bo_phan: str = ""


@router.post("/{yid}")
def cap_nhat(yid: int, data: CapNhatIn, u: User = Depends(require_roles(*VAI_YEU_CAU)), db: Session = Depends(get_db)):
    try:
        return CK.cap_nhat_ho_tro(db, u, yid, data.model_dump())
    except CK.LoiCham as ex:
        raise HTTPException(400, str(ex))


@router_gop_y.get("")
def ds_gop_y(trang_thai: str = "", u: User = Depends(require_roles(*CK.VAI_GOP_Y_DOC)), db: Session = Depends(get_db)):
    from app.models.cham_soc_khach import TRANG_THAI_VIEC
    return {"dong": CK.ds_gop_y(db, u, trang_thai), "trang_thai": TRANG_THAI_VIEC,
            "tra_loi_duoc": u.role in CK.VAI_GOP_Y_TRA_LOI}


class GopYIn(BaseModel):
    trang_thai: str = ""
    tra_loi: str = ""
    ghi_chu_noi_bo: str | None = None


@router_gop_y.post("/{gid}")
def cap_nhat_gop_y(gid: int, data: GopYIn, u: User = Depends(require_roles(*CK.VAI_GOP_Y_TRA_LOI)), db: Session = Depends(get_db)):
    d = data.model_dump()
    if d.get("ghi_chu_noi_bo") is None:
        d.pop("ghi_chu_noi_bo")
    try:
        return CK.cap_nhat_gop_y(db, u, gid, d)
    except CK.LoiCham as ex:
        raise HTTPException(400, str(ex))
