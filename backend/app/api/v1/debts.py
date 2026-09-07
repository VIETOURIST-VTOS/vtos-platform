"""Sổ công nợ toàn hệ thống – mục "Công nợ" của nhóm Tài chính & Kế toán."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import debts as CN

router = APIRouter(prefix="/api/v1/cong-no", tags=["cong-no"])

# Công nợ là số tiền của cả công ty: lãnh đạo, kế toán, kiểm soát, CNTT và trưởng phòng điều hành.
# Nhân viên kinh doanh KHÔNG xem toàn bộ công nợ – họ theo dõi booking của mình ở màn hình bán hàng.
READ = ("chutich", "tgd", "bks", "ketoan", "ptgd_doan", "tp_dh", "cntt")   # khớp MENU_ROLES["/cong-no"]


@router.get("")
def so_cong_no(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Phải thu khách · phải trả nhà cung cấp · công nợ đội xe. Không có trường nào bù trừ hai vế."""
    return CN.so_cong_no_toan_he_thong(db)


@router.get("/phai-thu")
def phai_thu(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return CN.phai_thu_khach(db)


@router.get("/phai-tra")
def phai_tra(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return CN.phai_tra_ncc(db)
