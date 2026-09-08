"""K1, K2, K6 – bàn làm việc cho phần NGƯỜI QUYẾT của robot Kiểm soát.

Robot liệt kê và đề xuất; ba đường dẫn dưới đây là chỗ người trả lời. Vai trò bks (robot) CỐ TÌNH
không nằm trong nhóm được quyết: robot vừa xếp loại vừa chốt xếp loại thì con số nó báo lên Chủ tịch
là con số nó tự đặt ra.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import ks_cot_tien as CT
from app.services import ky_thuat as KT

router = APIRouter(prefix="/api/v1/kiem-soat", tags=["kiem-soat"])

XEM = ("chutich", "tgd", "bks", "cntt", "ketoan")
# Ai được QUYẾT một cột là tiền hay không, và sửa hay giữ: Kế toán trưởng (nghiệp vụ) và CNTT (kỹ
# thuật), Chủ tịch/TGĐ đi qua FULL_ACCESS. Không có bks.
QUYET = ("ketoan", "cntt")


@router.get("/cot-tien")
def cot_tien(loc: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Sổ rà soát cột tiền. loc: tien | khong_tien | chua_ro | thieu_thanh_0 | can_doi_kieu."""
    return CT.bang(db, loc)


class QuyetDong(BaseModel):
    id: int
    quyet_nguoi: str = ""      # "" giữ nguyên · tien · khong_tien
    quyet_k2: str = ""         # "" giữ nguyên · sua · giu
    ghi_chu: str | None = None


class QuyetIn(BaseModel):
    dong: list[QuyetDong] = []


@router.post("/cot-tien/quyet")
def quyet_cot_tien(data: QuyetIn, u: User = Depends(require_roles(*QUYET)),
                   db: Session = Depends(get_db)):
    if not data.dong: raise HTTPException(422, "Chưa chọn dòng nào để quyết")
    try:
        return CT.quyet(db, u, [d.model_dump() for d in data.dong])
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))


@router.get("/su-kien-ky-thuat")
def su_kien(ngay: int = 7, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Lỗi 5xx, đường dẫn chậm, tác vụ nền hỏng, lần khởi động máy chủ."""
    return KT.bang(db, ngay)
