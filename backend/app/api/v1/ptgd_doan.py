"""Cửa đọc bàn làm việc của Phó Tổng giám đốc tour đoàn — 24/9/2026.

MỘT TIỀN TỐ RIÊNG `/api/v1/ptgd-doan`, không gắn nhờ vào `/api/v1/tours`. Cùng lập luận đã ghi ở
`so_con_no.py` ngày 18/9: gắn nhờ vào một nhóm có sẵn là nới CẢ nhóm ấy cho mọi vai mở được màn
hình mới, và phần dôi ra vẫn là quyền đã cấp dù hàng rào trong chưa cho dùng hôm nay.

CHỈ ĐỌC. Ký dự toán vẫn đi qua cửa cũ `POST /api/v1/tours/{id}/approve`, với đúng hàng rào cũ.
Dựng một cửa ký thứ hai ở đây là tạo bản sao thứ hai của luật ký — và bản sao nào rồi cũng lệch.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ptgd_doan as P

# Hẹp đúng bằng dòng "/ptgd-doan" của MENU_ROLES. Hai chỗ lệch nhau là có vai thấy mục menu rồi bấm
# vào nhận 403, hoặc mở được cửa mà không có mục menu để tới. Phép thử đối chiếu hai bảng này.
XEM = ("chutich", "tgd", "bks", "robot_ks", "ptgd_doan", "cntt")

router = APIRouter(prefix="/api/v1/ptgd-doan", tags=["ptgd-doan"])


@router.get("/ban-lam-viec")
def ban_lam_viec(ky: str,
                 u: User = Depends(require_roles(*XEM, mo_ta="bàn làm việc Phó TGĐ tour đoàn")),
                 db: Session = Depends(get_db)):
    """Kỳ dạng 2026-09. KHÔNG có giá trị mặc định: một bảng số thật in ra dưới một kỳ mà người xem
    không chọn là cách chắc chắn để họ đọc nhầm tháng."""
    try:
        return P.ban_lam_viec(db, ky)
    except (ValueError, IndexError):
        raise HTTPException(422, f"Kỳ không đọc được: {ky!r}. Dạng đúng là 2026-09.")
