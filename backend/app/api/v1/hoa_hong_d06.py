"""DH-1 · Hoa hồng đối tác bán hàng (D06) — màn Kế toán. Luật và phép tính: services/hoa_hong_d06.py."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import hoa_hong_d06 as H

router = APIRouter(prefix="/api/v1/hoa-hong-d06", tags=["hoa-hong-d06"])


def _ky(ky: str | None) -> str:
    if ky:
        try:
            H.dau_thang(ky)
            return ky
        except Exception:
            raise HTTPException(422, "Kỳ phải dạng YYYY-MM")
    d = H._hom_nay()
    return f"{d:%Y-%m}"


@router.get("")
def xem(ky: str | None = None, u: User = Depends(require_roles(*H.VAI_XEM)), db: Session = Depends(get_db)):
    return H.tong_hop(db, _ky(ky))


class KyIn(BaseModel):
    ky: str


@router.post("/tinh-lai")
def tinh_lai(data: KyIn, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        return H.tinh_lai(db, u, _ky(data.ky))
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))


@router.post("/ky/{ky_id}/chot")
def chot(ky_id: int, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        k = H.chot(db, u, ky_id)
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã chốt kỳ {k.ky}"}


@router.post("/ky/{ky_id}/de-nghi-chi")
def de_nghi_chi(ky_id: int, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        r = H.de_nghi_chi(db, u, ky_id)
    except (H.LoiD06, ValueError) as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã lập đề nghị chi {r.code} — {int(r.amount):,} đ, đi luồng duyệt chi".replace(",", "."), "code": r.code}


class HinhThucIn(BaseModel):
    doi_tac_id: int
    hinh_thuc: str


@router.post("/hinh-thuc")
def hinh_thuc(data: HinhThucIn, u: User = Depends(require_roles(*H.VAI_HINH_THUC)), db: Session = Depends(get_db)):
    try:
        r = H.dat_hinh_thuc(db, u, data.doi_tac_id, data.hinh_thuc)
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã đặt «{H.HINH_THUC[r.hinh_thuc]}» có hiệu lực từ {r.hieu_luc_tu:%d/%m/%Y}"}
