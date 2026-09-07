"""Nhật trình chuyến: mã phiếu gốc bên hệ thống nguồn

Nạp 92 chuyến tháng 8/2026 từ báo cáo quyết toán xe của VieTrip cần một khóa chống trùng: nạp
lại cùng một báo cáo mà sinh ra bộ chuyến thứ hai thì doanh thu và chi phí đều nhân đôi, và
không ai nhìn ra ngay vì mỗi dòng đều trông đúng.

Revision ID: e3f4a5b6c7d8
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "b1c2d3e4f5a6"   # nối sau bản của phiên song song – giữ MỘT đầu duy nhất
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("fleet_trips")}
    if "ma_phieu" not in cols:
        # Ràng buộc duy nhất đặt bằng CHỈ MỤC chứ không bằng UNIQUE trên cột: SQLite (máy lập trình) không
        # thêm được ràng buộc vào bảng đã tạo, còn chỉ mục duy nhất thì cả hai môi trường đều tạo được –
        # nên hai bên chạy cùng một lược đồ.
        op.add_column("fleet_trips", sa.Column("ma_phieu", sa.String(60), nullable=True))
        op.create_index("ux_fleet_trips_ma_phieu", "fleet_trips", ["ma_phieu"], unique=True)
    if "nguon" not in cols:
        op.add_column("fleet_trips", sa.Column("nguon", sa.String(40), server_default="nhap_tay"))


def downgrade() -> None:
    op.drop_index("ux_fleet_trips_ma_phieu", table_name="fleet_trips")
    op.drop_column("fleet_trips", "nguon")
    op.drop_column("fleet_trips", "ma_phieu")
