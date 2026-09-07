"""Giao dịch nguồn ngoài: cột nhóm và cờ "không phải chi phí"

Bộ đề xuất chi tháng 8/2026 của Vietrip có 36 khoản liên quan đội xe, trong đó 3 khoản
(127.360.494 đ) là ĐIỀU CHUYỂN TIỀN giữa các tài khoản của chính công ty chứ không phải chi
phí. Không tách ra thì mỗi lần cộng "chi phí đội xe tháng 8" đều dư đúng khoản đó, và bảng
vẫn trông hợp lý.

Revision ID: d2e3f4a5b6c7
Revises: a1b2c3d4e5f7
"""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "a1b2c3d4e5f7"   # nối sau bản vá của phiên song song – giữ MỘT đầu duy nhất
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("fleet_external_txns")}
    if "nhom" not in cols:
        op.add_column("fleet_external_txns", sa.Column("nhom", sa.String(60), server_default=""))
    if "khong_phai_chi_phi" not in cols:
        op.add_column("fleet_external_txns",
                      sa.Column("khong_phai_chi_phi", sa.Boolean(), server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("fleet_external_txns", "khong_phai_chi_phi")
    op.drop_column("fleet_external_txns", "nhom")
