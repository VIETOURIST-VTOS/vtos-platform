"""Gỡ chỉ mục ngày hạch toán – nó làm chậm Sổ Cái 20 lần

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
from alembic import op
import sqlalchemy as sa

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    # Đo trên sổ thật sau khi thêm chỉ mục ix_journal_entries_entry_date (migration c9d0e1f2a3b4):
    #   - Bảng cân đối tài khoản H1: 1.164 ms → 705 ms  (nhanh hơn)
    #   - Sổ Cái TK 112 H1:          1.182 ms → 23.538 ms (CHẬM GẤP 20 LẦN)
    # Lý do: Sổ Cái sắp xếp theo (ngày hạch toán, chứng từ, dòng) rồi lấy 2.000 dòng đầu. Có chỉ mục ngày,
    # bộ tối ưu tưởng đi theo chỉ mục ngày sẽ dừng sớm, nhưng chỉ một phần nhỏ chứng từ có dòng thuộc tài
    # khoản đang xem nên nó phải quét gần hết khoảng ngày mới gom đủ dòng. Không có chỉ mục ngày thì nó dùng
    # chỉ mục tài khoản (rất chọn lọc) rồi mới sắp xếp – đúng và nhanh.
    # Sổ Cái là báo cáo Kế toán mở hằng ngày nên ưu tiên nó; phần tổng hợp chậm hơn chút không đáng kể.
    op.drop_index("ix_journal_entries_entry_date", table_name="journal_entries")


def downgrade():
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])
