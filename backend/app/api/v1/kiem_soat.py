"""Bàn làm việc của robot Kiểm soát (chỉ đạo 07/9/2026: vị trí Kiểm soát do AI giữ).

Ai xem: Chủ tịch, TGĐ, chính vai trò bks, và CNTT (người vận hành robot).
Ai chạy quét và chấm điểm: bks (robot) và CNTT; Chủ tịch, TGĐ đi qua FULL_ACCESS.
Ai HẬU KIỂM điểm: Chủ tịch và TGĐ. Điểm máy chấm là đề xuất cho tới lúc đó.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import ks_robot as KS

router = APIRouter(prefix="/api/v1/kiem-soat", tags=["kiem-soat"])

XEM = ("chutich", "tgd", "bks", "cntt")
CHAY = ("bks", "cntt")            # Chủ tịch và TGĐ vẫn qua được (FULL_ACCESS trong deps)
HAU_KIEM = ("chutich", "tgd")


@router.get("")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return KS.bang(db)


@router.post("/quet")
def quet(u: User = Depends(require_roles(*CHAY)), db: Session = Depends(get_db)):
    """Một vòng quét: mạch nâng cấp, quyền lệch, vai trò trống, ngoại lệ tồn, AI chưa hậu kiểm.
    Chỉ sinh báo cáo gửi Chủ tịch khi có việc NGHIÊM TRỌNG mới."""
    return KS.quet(db, boi=u.username)


@router.post("/cham-diem")
def cham_diem(ky: str | None = None, u: User = Depends(require_roles(*CHAY)), db: Session = Depends(get_db)):
    return KS.cham_diem(db, ky, boi=u.username)


class HauKiemIn(BaseModel):
    diem_id: int
    chap_nhan: bool
    ghi_chu: str = ""


@router.post("/hau-kiem-diem")
def hau_kiem_diem(data: HauKiemIn, u: User = Depends(require_roles(*HAU_KIEM)),
                  db: Session = Depends(get_db)):
    return {"message": KS.hau_kiem_diem(db, u, data.diem_id, data.chap_nhan, data.ghi_chu)}


class XemIn(BaseModel):
    bao_cao_id: int


@router.post("/da-xem")
def da_xem(data: XemIn, u: User = Depends(require_roles(*HAU_KIEM)), db: Session = Depends(get_db)):
    return {"message": KS.danh_dau_da_xem(db, u, data.bao_cao_id)}
