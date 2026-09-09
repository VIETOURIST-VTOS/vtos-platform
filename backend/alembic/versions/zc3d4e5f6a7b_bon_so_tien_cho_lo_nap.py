"""K5: bốn con số tiền cho mỗi lô nạp, soi gương bốn con số dòng

Revision ID: zc3d4e5f6a7b
Revises: zb2c3d4e5f6a
"""
from alembic import op
import sqlalchemy as sa

revision = "zc3d4e5f6a7b"
down_revision = "zb2c3d4e5f6a"
branch_labels = None
depends_on = None

COT = ("tong_tien_tep", "tong_tien_da_nap", "tong_tien_bo_qua", "tong_tien_loi")


def upgrade():
    # nullable: lô nạp CŨ không đo được tiền, và "chưa đo" phải khác "đo được và bằng không".
    # Điền 0 cho chúng là bịa ra một phép đo chưa từng chạy.
    for c in COT:
        op.add_column("intake_runs", sa.Column(c, sa.Numeric(18, 2), nullable=True))
    op.add_column("intake_runs", sa.Column("cot_tien", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("intake_runs", "cot_tien")
    for c in COT:
        op.drop_column("intake_runs", c)
