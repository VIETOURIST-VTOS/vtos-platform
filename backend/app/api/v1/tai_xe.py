"""Hồ sơ tài xế – cửa đọc cho màn hình Điều hành xe ▸ Tài xế.

Chỉ MỘT cửa và chỉ ĐỌC. Sửa hồ sơ nhân sự vẫn ở Nhân sự, nạp bằng lái vẫn ở bộ nạp tệp, gán xe cho
tài xế vẫn ở màn hình Đội xe. Thêm một cửa ghi thứ hai cho cùng dữ liệu là thêm một chỗ để hai bên
ghi lệch nhau, mà màn hình này không cần ghi gì cả.

Vai đọc: người điều hành đội xe, Nhân sự (giữ hồ sơ), Kế toán (lương tài xế là giá vốn chuyến) và
các vai giám sát. KHÔNG mở cho vai nhân viên kinh doanh: họ không điều xe, và danh sách này là hồ
sơ cá nhân của người khác. Cắt dòng nằm ở `require_roles` trên máy chủ, không ở giao diện.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import tai_xe as TX

router = APIRouter(prefix="/api/v1/tai-xe", tags=["tai-xe"])

# ĐÚNG BẰNG dòng "/doi-xe" trong ma trận quyền của access.py – hồ sơ tài xế và hồ sơ xe là cùng một
# tập hồ sơ đội xe, mở lệch nhau là mở một đường vòng. Giữ hai nơi khớp nhau bằng mắt chứ không bằng
# cách nhập access.py vào đây: tệp ấy nhập ngược lại các router, nhập vòng là hỏng lúc khởi động.
READ = ("chutich", "tgd", "bks", "robot_ks", "tp_dh", "nv_dh", "gd_doi_xe", "ketoan", "hcns", "cntt")


@router.get("")
def danh_sach(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách tài xế kèm tình trạng bằng lái và xe đang đứng tên. Không trả trường lương nào."""
    return TX.danh_sach(db)
