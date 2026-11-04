"""Đợt QUY-2a 04/11/2026 — cột `so_goc` của bảng phiếu quỹ.

Số trên tờ phiếu quỹ GIẤY, và là khoá chống trùng của cửa tải lô sổ quỹ. Nạp lại cùng một tệp thì
dòng nào đã có số này sẽ bị bỏ qua, không lập phiếu thứ hai cho cùng một khoản tiền.

RỖNG ĐƯỢC: phiếu lập tay trên màn hình không có tờ giấy nào có trước nó.
"""
from alembic import op
import sqlalchemy as sa

revision = "quy2b8d1f3a5c7e9"
down_revision = "quy1a7e3b9c2d145"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("phieu_quy",
                  sa.Column("so_goc", sa.String(length=40), nullable=True, server_default=""))
    op.create_index("ix_phieu_quy_so_goc", "phieu_quy", ["so_goc"])


def downgrade():
    op.drop_index("ix_phieu_quy_so_goc", table_name="phieu_quy")
    op.drop_column("phieu_quy", "so_goc")
