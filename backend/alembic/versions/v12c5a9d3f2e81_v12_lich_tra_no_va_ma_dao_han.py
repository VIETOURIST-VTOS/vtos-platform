"""V12 – kỳ trả nợ và mã đáo hạn trên lịch khế ước vay

Revision ID: v12c5a9d3f2e81
Revises: v6b4d8e2a71c3
Create Date: 2026-09-08

Hai cột trên fin_schedules:

  ky           – số kỳ trong lịch trả nợ. RỖNG cho dòng không thuộc lịch (giải ngân, thu hồi lẻ).
  ma_dao_han   – hai chân của một lần đảo nợ mang cùng một mã; bút toán sinh ra mang source_ref
                 "dao_han:<mã>" để cổng đáo hạn nhìn thấy chúng là một cặp.

ma_dao_han để CHUỖI RỖNG chứ không NULL: nó luôn được so bằng phép so chuỗi (`!= ""`), và trộn NULL
với chuỗi rỗng trong cùng một cột là cách chắc chắn để một nửa số dòng lọt khỏi mọi bộ lọc.

ky thì ngược lại – NULL, vì "không thuộc kỳ nào" khác hẳn "kỳ số 0".
"""
from alembic import op
import sqlalchemy as sa

revision = "v12c5a9d3f2e81"
down_revision = "v6b4d8e2a71c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fin_schedules", sa.Column("ky", sa.Integer(), nullable=True))
    op.add_column("fin_schedules", sa.Column("ma_dao_han", sa.String(40), nullable=False,
                                             server_default=""))
    op.create_index("ix_fin_schedules_ma_dao_han", "fin_schedules", ["ma_dao_han"])


def downgrade() -> None:
    op.drop_index("ix_fin_schedules_ma_dao_han", table_name="fin_schedules")
    op.drop_column("fin_schedules", "ma_dao_han")
    op.drop_column("fin_schedules", "ky")
