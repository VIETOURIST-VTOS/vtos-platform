"""V8 – khóa sổ một kỳ: sao kê vào sổ hàng loạt, kết chuyển cuối kỳ, và trạng thái cả kỳ.

Mọi đường GHI ở đây đều có một đường XEM TRƯỚC tương ứng, và màn hình bắt đi qua nó. Ghi sổ hàng
loạt mà không nhìn trước cả lô là cách tạo ra vài trăm bút toán sai trong một giây và mất vài ngày
để đảo lại từng cái.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ket_so as KS

router = APIRouter(prefix="/api/v1/ket-so", tags=["ket-so"])

XEM = ("chutich", "tgd", "ketoan", "bks", "cntt")
GHI = ("ketoan",)          # chỉ Kế toán ghi sổ. Chủ tịch và TGĐ xem, không ghi thay.


@router.get("/tinh-trang")
def tinh_trang(ky: str, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return KS.tinh_trang_ky(db, ky)


@router.get("/sao-ke/xem-truoc")
def sao_ke_xem_truoc(ky: str, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return KS.xem_truoc_sao_ke(db, ky)


class GhiLo(BaseModel):
    ky: str
    ids: list[int] | None = None
    # {"<id dòng sao kê>": {"muc_chi": "tra_ncc"}} – phân loại do KẾ TOÁN chọn, máy không đoán hộ.
    phan_loai: dict | None = None


@router.post("/sao-ke/ghi-so")
def sao_ke_ghi_so(body: GhiLo, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    try:
        kq = KS.ghi_so_sao_ke(db, u, body.ky, body.ids, body.phan_loai)
    except KS.KhongGhiDuoc as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return kq


@router.get("/ket-chuyen/xem-truoc")
def kc_xem_truoc(ky: str, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return KS.xem_truoc_ket_chuyen(db, ky)


class KetChuyen(BaseModel):
    ky: str
    buoc: list[int] | None = None


@router.post("/ket-chuyen")
def kc(body: KetChuyen, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    try:
        kq = KS.ket_chuyen(db, u, body.ky, body.buoc)
    except KS.KhongGhiDuoc as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return kq
