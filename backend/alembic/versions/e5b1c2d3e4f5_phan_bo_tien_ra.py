"""Đợt E5 13/10/2026 — phân bổ tiền RA: nới `phan_bo_tien` sang nghĩa vụ và đợt.

Revision ID: e5b1c2d3e4f5
Revises: e4a1b2c3d4e5
Create Date: 2026-10-13

BA VIỆC, VÀ KHÔNG VIỆC NÀO ĐỘNG VÀO DỮ LIỆU ĐANG CÓ:

  1. `booking_id` thôi BẮT BUỘC. Mọi dòng đang có đều có booking, nên nới ràng buộc không làm
     dòng nào đổi nghĩa.
  2. Thêm `nghia_vu_id` và `dot_id`, đều rỗng được. Dòng cũ rỗng hai cột này — đúng, vì chúng là
     nhánh booking.
  3. Hai chỉ mục cho hai cột mới, để sổ nghĩa vụ tra ngược "đợt này trả bằng khoản tiền nào" mà
     không quét cả bảng.

SQLite KHÔNG đổi được NOT NULL bằng ALTER, nên dùng `batch_alter_table` — Alembic dựng bảng mới,
chép dữ liệu, đổi tên. Postgres thì chạy ALTER thẳng. Cùng một đoạn mã cho cả hai.
"""
import sqlalchemy as sa
from alembic import op

revision = "e5b1c2d3e4f5"
# Đợt E5b 13/10/2026 — NỐI LẠI MẠCH. Bản đầu khai `e4a1b2c3d4e5`, trùng điểm nối với bản
# di trú `qt1f3a8c6e2b94` của làn QT-1 gộp ngay trước đó (PR #316, rồi E5 là #317). Hai bản
# cùng trỏ về một cha thì mạch chia đôi, và `alembic upgrade head` không biết đi về đâu —
# máy chủ chạy lệnh ấy lúc khởi động nên deploy chết. Nối E5 vào SAU QT-1: E5 gộp sau, và
# hai bản không đụng bảng nào của nhau nên thứ tự không đổi kết quả.
down_revision = "qt1f3a8c6e2b94"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phan_bo_tien") as b:
        b.alter_column("booking_id", existing_type=sa.Integer(), nullable=True)
        b.add_column(sa.Column("nghia_vu_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("dot_id", sa.Integer(), nullable=True))
    op.create_index("ix_phan_bo_tien_nghia_vu", "phan_bo_tien", ["nghia_vu_id"])
    op.create_index("ix_phan_bo_tien_dot", "phan_bo_tien", ["dot_id"])


def downgrade() -> None:
    # Hạ cấp XOÁ hai cột, nên mọi dòng phân bổ tiền RA mất theo. Ghi ra đây chứ không làm im lặng:
    # ai chạy hạ cấp này trên kho đã có dữ liệu thật thì đang xoá sổ một phần lịch sử thanh toán.
    op.drop_index("ix_phan_bo_tien_dot", table_name="phan_bo_tien")
    op.drop_index("ix_phan_bo_tien_nghia_vu", table_name="phan_bo_tien")
    with op.batch_alter_table("phan_bo_tien") as b:
        b.drop_column("dot_id")
        b.drop_column("nghia_vu_id")
