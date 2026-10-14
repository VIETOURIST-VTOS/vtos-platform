"""Đợt E16 14/10/2026 — bộ số BCTC kiểm toán do người tải lên và ký.

Revision ID: e16c3d4e5f6a
Revises: e15b1c2d3e4f
Create Date: 2026-10-14

HAI bảng mới, KHÔNG đụng một cột nào của bảng cũ. Không đụng `journal_entries`: các bút toán chốt
sổ kiểm toán đã ghi trước đợt này GIỮ NGUYÊN — chúng là sổ, và sổ thì không viết lại bằng một bản
di trú.

KHÔNG NẠP SẴN BỘ SỐ CŨ. Ba mươi con số trong `app/data/kiem_toan_2026h1.json` do robot gõ vào kho
mã, chưa ai ký. Chép chúng vào bảng này và đóng dấu `da_ky` là làm đúng cái việc đợt này dựng ra để
chặn — một bộ số đã ký mà không có người ký. Tệp JSON ấy bị XOÁ ở đợt này; Kế toán tải lên bản
Excel đối chiếu với báo cáo Baker Tilly đã ký, rồi Chủ tịch ký.

HỆ QUẢ CÓ CHỦ Ý: từ lúc gộp đợt này cho tới lúc có một bộ số đã ký, cửa "Chốt sổ theo BCTC kiểm
toán" trả 422 kèm câu chỉ đúng việc phải làm. Đó là việc còn thiếu THẬT — nó vốn vẫn thiếu, chỉ là
trước đây một tệp trong kho mã che nó đi.
"""
import sqlalchemy as sa
from alembic import op

revision = "e16c3d4e5f6a"
down_revision = "e15b1c2d3e4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bo_so_kiem_toan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("ky", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("don_vi_kiem_toan", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("so_bao_cao", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("ngay_bao_cao", sa.Date(), nullable=True),
        sa.Column("loai_bao_cao", sa.String(length=20), nullable=False, server_default="soat_xet"),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("trang_thai", sa.String(length=16), nullable=False, server_default="cho_ky"),
        sa.Column("tai_len_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tai_len_vai", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("tai_len_luc", sa.DateTime(), nullable=True),
        sa.Column("ten_tep", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ky_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ky_vai", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("ky_luc", sa.DateTime(), nullable=True),
        sa.Column("tu_choi_ly_do", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("thay_the_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["thay_the_id"], ["bo_so_kiem_toan.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bo_so_kiem_toan_company_id", "bo_so_kiem_toan", ["company_id"])
    op.create_index("ix_bo_so_kiem_toan_as_of", "bo_so_kiem_toan", ["as_of"])
    op.create_index("ix_bo_so_kiem_toan_trang_thai", "bo_so_kiem_toan", ["trang_thai"])
    op.create_index("ix_bo_so_kiem_toan_tt_ngay", "bo_so_kiem_toan", ["trang_thai", "as_of"])

    op.create_table(
        "bo_so_kiem_toan_dong",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bo_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ma_doi_tuong", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ten_doi_tuong", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("open_d", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("open_c", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("close_d", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("close_c", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["bo_id"], ["bo_so_kiem_toan.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bo_so_kiem_toan_dong_bo_id", "bo_so_kiem_toan_dong", ["bo_id"])
    op.create_index("ix_bsktd_bo_tk", "bo_so_kiem_toan_dong", ["bo_id", "code"])


def downgrade() -> None:
    op.drop_index("ix_bsktd_bo_tk", table_name="bo_so_kiem_toan_dong")
    op.drop_index("ix_bo_so_kiem_toan_dong_bo_id", table_name="bo_so_kiem_toan_dong")
    op.drop_table("bo_so_kiem_toan_dong")
    op.drop_index("ix_bo_so_kiem_toan_tt_ngay", table_name="bo_so_kiem_toan")
    op.drop_index("ix_bo_so_kiem_toan_trang_thai", table_name="bo_so_kiem_toan")
    op.drop_index("ix_bo_so_kiem_toan_as_of", table_name="bo_so_kiem_toan")
    op.drop_index("ix_bo_so_kiem_toan_company_id", table_name="bo_so_kiem_toan")
    op.drop_table("bo_so_kiem_toan")
