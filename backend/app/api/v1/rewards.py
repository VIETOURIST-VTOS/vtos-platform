"""KH-3 · VTD Rewards — màn VTOS cho Kinh doanh: tra điểm khách, xem và áp voucher vào booking."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.core import User
from app.api.deps import require_roles
from app.services import rewards as RW

router = APIRouter(prefix="/api/v1/rewards", tags=["rewards"])


@router.get("/tra-cuu")
def tra_cuu(q: str, u: User = Depends(require_roles(*RW.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return RW.tra_cuu(db, q)
    except RW.LoiDiem as ex:
        raise HTTPException(400, str(ex))


@router.get("/voucher/{ma}")
def xem_voucher(ma: str, u: User = Depends(require_roles(*RW.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return RW.xem_voucher(db, ma)
    except RW.LoiDiem as ex:
        raise HTTPException(404, str(ex))


class ApIn(BaseModel):
    ma_voucher: str
    ma_booking: str


@router.post("/ap-voucher")
def ap_voucher(data: ApIn, u: User = Depends(require_roles(*RW.VAI_AP)), db: Session = Depends(get_db)):
    try:
        return RW.ap_voucher(db, u, data.ma_voucher, data.ma_booking)
    except RW.LoiDiem as ex:
        raise HTTPException(400, str(ex))
