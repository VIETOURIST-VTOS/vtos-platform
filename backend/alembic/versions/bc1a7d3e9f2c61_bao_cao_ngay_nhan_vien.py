"""BC-1 — báo cáo ngày phía nhân viên: lần nộp đầu, phiên bản, vướng mắc có người nhận, kiêm nhiệm.

Revision ID: bc1a7d3e9f2c61
Revises: r6b1a4c7e2f9d5
Create Date: 2026-10-26

Bốn cột thêm vào `daily_reports` đều có mặc định, nên báo cáo cũ đọc ra như trước. Cột
`first_submitted_at` để RỖNG cho báo cáo cũ — không điền hộ bằng `submitted_at`: báo cáo cũ có thể
đã nộp lại nhiều lần, và điền hộ là bịa ra một lần nộp đầu không ai biết có thật không. Chỗ đọc
lấy `submitted_at` khi cột này rỗng, và cờ `on_time` cũ giữ nguyên, không tính lại.
"""
import sqlalchemy as sa
from alembic import op

revision = "bc1a7d3e9f2c61"
down_revision = "r6b1a4c7e2f9d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("daily_reports") as b:
        b.add_column(sa.Column("first_submitted_at", sa.DateTime(), nullable=True))
        b.add_column(sa.Column("so_lan_nop", sa.Integer(), nullable=False, server_default="1"))
        b.add_column(sa.Column("vuong_mac_cho", sa.String(length=20), nullable=False, server_default=""))
        b.add_column(sa.Column("vuong_mac_han", sa.Date(), nullable=True))
    op.create_table(
        "daily_report_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id"), nullable=False, index=True),
        sa.Column("lan", sa.Integer(), nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=False),
        sa.Column("du_lieu", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "report_extra_forms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("mau", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("report_extra_forms")
    op.drop_table("daily_report_versions")
    with op.batch_alter_table("daily_reports") as b:
        b.drop_column("vuong_mac_han")
        b.drop_column("vuong_mac_cho")
        b.drop_column("so_lan_nop")
        b.drop_column("first_submitted_at")
