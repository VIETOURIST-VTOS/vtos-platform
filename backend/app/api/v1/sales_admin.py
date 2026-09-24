"""Cửa đọc bàn làm việc của Sale Admin phòng Đoàn — vòng 3/3, 24/9/2026.

MỘT TIỀN TỐ RIÊNG `/api/v1/sales-admin`, cùng lập luận đã ghi ở `ptgd_doan.py`: gắn nhờ vào một
nhóm API có sẵn là nới CẢ nhóm ấy cho mọi vai mở được màn hình mới.

CHỈ ĐỌC — không một cửa ghi nào ở đây. Hai cửa ghi của vai này đã mở từ vòng 2 và nằm đúng chỗ của
chúng, trên chính chuyến: `POST /api/v1/tours/{id}/chuyen-dieu-hanh` và `.../tra-lai-kinh-doanh`.
Dựng bản thứ hai của chúng ở đây là tạo bản sao thứ hai của luật chuyển.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import sales_admin as S

# Hẹp đúng bằng dòng "/sales-admin" của MENU_ROLES. Phép thử đối chiếu hai bảng này.
XEM = ("chutich", "tgd", "bks", "robot_ks", "sales_admin", "ptgd_doan", "cntt")

router = APIRouter(prefix="/api/v1/sales-admin", tags=["sales-admin"])


@router.get("/ban-lam-viec")
def ban_lam_viec(u: User = Depends(require_roles(*XEM, mo_ta="bàn làm việc Sale Admin phòng Đoàn")),
                 db: Session = Depends(get_db)):
    """Không nhận tham số kỳ: sáu khối ở đây đều là việc ĐANG TỒN ĐỌNG hôm nay, không phải báo cáo
    một tháng đã qua. Thêm ô chọn kỳ vào một danh sách việc phải làm là mời người dùng xem việc của
    tháng trước rồi tưởng mình đã làm hết việc của hôm nay."""
    return S.ban_lam_viec(db)
