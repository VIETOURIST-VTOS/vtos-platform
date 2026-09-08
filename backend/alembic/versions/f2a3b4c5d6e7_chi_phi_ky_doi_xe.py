"""Chi phí kỳ của đội xe: tầng chi phí không gắn vào chuyến nào

Bảng quyết toán xe tháng 6/2026 cho thấy khoảng cách giữa hai con số: cộng lãi gộp 21 chiếc được 938
triệu, nhưng sau bảo hiểm, lương tài xế, phí bãi và 327 triệu lãi vay thì đội xe còn 227 triệu. Trước
bản này VTOS chỉ có tầng đầu, nên bất kỳ ai đọc báo cáo cũng tưởng đội xe lãi gấp hơn bốn lần thực tế.

Cột pham_vi tách hai loại: chi phí quy được về từng chiếc (bảo hiểm, lương, bảo dưỡng) và chi phí của
cả đội (bãi xe, lãi vay, BHXH). Chi phí đội không chia về xe, vì chia theo doanh thu, theo ngày chạy
hay chia đều đều ra những con số khác nhau và đều "có lý" – mà người đọc lại nhớ nó như kết quả thật
của chiếc xe rồi lấy ra quyết định bán xe hay đổi tài xế.

Chỉ mục duy nhất (kỳ, nhóm, xe, diễn giải) chặn việc nhập lại bảng tháng lần thứ hai: chi phí nhân đôi
mà mỗi dòng vẫn trông đúng là lỗi khó thấy nhất của mọi bảng quyết toán.

Revision ID: f2a3b4c5d6e7
Revises: f7a8b9c0d1e2 (đầu nhánh trên origin – không nối theo thứ tự mình viết)
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "fleet_period_costs" in insp.get_table_names():
        return
    op.create_table(
        "fleet_period_costs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("pham_vi", sa.String(10), server_default="xe"),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("nhom", sa.String(20), nullable=False),
        sa.Column("mo_ta", sa.String(200), server_default=""),
        sa.Column("so_tien", sa.Float, server_default="0"),
        sa.Column("chung_tu", sa.String(200), server_default=""),
        sa.Column("nguon", sa.String(20), server_default="nhap_tay"),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_fleet_period_costs_ky", "fleet_period_costs", ["ky"])
    op.create_index("ux_fleet_period_costs", "fleet_period_costs",
                    ["ky", "nhom", "vehicle_id", "mo_ta"], unique=True)


def downgrade() -> None:
    op.drop_table("fleet_period_costs")
