"""VB-1 · Hai cột ngày nghỉ việc trên `employees` — nền của mục 5.8 Báo cáo biến động nhân sự.

VÌ SAO PHẢI THÊM CỘT, chứ không tính từ thứ đang có:

VTOS hôm nay biết một người CÒN LÀM hay KHÔNG (`employees.active`), nhưng không biết người ấy nghỉ
TỪ HÔM NÀO. Mà một báo cáo biến động chỉ có đúng một phép tính: đầu kỳ + tăng trong kỳ − giảm trong
kỳ = cuối kỳ. Không có ngày nghỉ thì vế "giảm trong kỳ" không tính được, và cả báo cáo rút xuống
còn một con số đầu người hôm nay — thứ màn hình Tổng quan HCNS đã in sẵn.

`labor_contracts.terminated_on` KHÔNG thay được. Nó là ngày chấm dứt một HỢP ĐỒNG, không phải ngày
người ấy rời công ty: hết hạn hợp đồng rồi ký tiếp là chấm dứt một bản mà người vẫn ở lại. Và phần
lớn người VTOS phải đếm — hướng dẫn viên cộng tác, tài xế khoán — KHÔNG có bản hợp đồng lao động
nào, nên tính biến động từ bảng ấy là bỏ sót đúng nhóm đông nhất.

HAI CỘT NÀY ĐỀU RỖNG SAU KHI CHẠY, kể cả với người đang `active = False`. Không đoán ngược một ngày
nghỉ từ `created_at` hay từ bảng lương cuối cùng: một ngày đoán nằm trong báo cáo trông y hệt một
ngày thật, và nó sẽ đi vào tỷ lệ nghỉ việc mà HCNS báo cáo lên. Người đã nghỉ mà chưa có ngày thì
`bien_dong_ns.chua_biet_ngay_nghi()` ĐẾM RIÊNG và màn hình in ra — chỗ thiếu là việc của HCNS điền,
không phải việc của phần mềm đi đoán.

Revision ID: vb1e7c3a9d5f24
Revises: ns6b4d9a2e7c13
"""
import sqlalchemy as sa
from alembic import op

revision = "vb1e7c3a9d5f24"
down_revision = "ns6b4d9a2e7c13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("ended_on", sa.Date(), nullable=True))
    op.add_column("employees", sa.Column("end_kind", sa.String(20), server_default=""))
    op.add_column("employees", sa.Column("end_reason", sa.String(300), server_default=""))
    op.create_index("ix_employees_ended_on", "employees", ["ended_on"])


def downgrade() -> None:
    op.drop_index("ix_employees_ended_on", table_name="employees")
    op.drop_column("employees", "end_reason")
    op.drop_column("employees", "end_kind")
    op.drop_column("employees", "ended_on")
