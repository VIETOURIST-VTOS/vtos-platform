"""Cửa đọc bàn bán tour lẻ — Phòng Kinh doanh Lẻ, Chủ tịch quyết 25/9/2026.

MỘT TIỀN TỐ RIÊNG `/api/v1/ban-tour-le`, cùng lập luận đã ghi ở `ptgd_doan.py` và `sales_admin.py`:
gắn nhờ vào một nhóm API có sẵn là nới CẢ nhóm ấy cho mọi vai mở được màn hình mới.

CHỈ ĐỌC. Cửa ghi của vai này là cửa BÁN, và nó đã có từ đầu: gửi yêu cầu đặt chỗ ở
`POST /api/v1/requests`. Không dựng nút bán ở đây — bán một chỗ là việc phải đọc chuyến ấy trước,
và một nút "đặt" cạnh một dòng tóm tắt là lời mời đặt mà chưa mở ra xem.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ban_tour_le as S

# Hẹp đúng bằng dòng "/ban-tour-le" của MENU_ROLES. Phép thử đối chiếu hai bảng này.
# KHÔNG có `sales_admin` và `ptgd_doan`: hai vai ấy thuộc phòng Đoàn, và Chủ tịch nói rõ ngày
# 25/9/2026 — "ý là PKDL, còn PKDĐ vẫn giữ nguyên".
XEM = ("chutich", "tgd", "bks", "robot_ks", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "cntt")

router = APIRouter(prefix="/api/v1/ban-tour-le", tags=["ban-tour-le"])


@router.get("/ban-lam-viec")
def ban_lam_viec(pham_vi: str = "dang_ban", u: User = Depends(require_roles(*XEM, mo_ta="bàn bán tour lẻ")),
                 db: Session = Depends(get_db)):
    """Không nhận tham số kỳ: đây là danh sách chỗ ĐANG CÒN BÁN hôm nay, không phải báo cáo một
    tháng đã qua. Một ô chọn kỳ trên bảng chỗ trống là lời mời bán chỗ của chuyến đã khởi hành."""
    return S.ban_lam_viec(db, pham_vi)   # R5-16: «sap_mo_ban» / «da_di» chỉ xem
