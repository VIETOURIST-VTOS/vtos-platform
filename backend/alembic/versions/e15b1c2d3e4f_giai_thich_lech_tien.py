"""Đợt E15 14/10/2026 — bảng giải thích chênh lệch tiền.

Revision ID: e15b1c2d3e4f
Revises: dl2k8m4p6r2w51
Create Date: 2026-10-14

MỘT bảng mới, KHÔNG đụng một cột nào của bảng cũ. `chot_so_du` giữ nguyên: đợt này không sửa nghĩa
của một con số đã ký bao giờ.

KHÔNG NẠP SẴN GÌ. Những ngày đã chốt trước đợt này chưa ai giải thích chênh lệch — và đúng là chưa
ai giải thích. Nạp một dòng "chênh lệch cũ, không rõ lý do" là bịa ra một lời khai không có người
ký, rồi kỳ cũ sẽ khóa được vì một dòng do máy viết.

Hệ quả có chủ ý: kỳ cũ nào còn chênh lệch tiền sẽ KHÔNG khóa được cho tới khi có người giải thích. Đó là việc còn
thiếu thật, không phải việc bản di trú này làm cho xong.

NỐI SAU `dl2k8m4p6r2w51` CHỨ KHÔNG SAU `e14a2b3c4d5e`. Bản đầu của đợt này nối sau E14, và bộ
đếm đầu mạch trong chính tệp bấm ĐÃ DỪNG lại trước khi đẩy: một robot khác đã gộp
`dl2k8m4p6r2w51` cũng nối sau E14, nên mạch chẻ hai nhánh — và hai đầu mạch thì
`alembic upgrade head` hỏng NGAY LÚC KHỞI ĐỘNG container, trước khi bất kỳ phép thử nào kịp chạy.
Đã nối lại vào đầu mạch thật của main.
"""
import sqlalchemy as sa
from alembic import op

revision = "e15b1c2d3e4f"
down_revision = "dl2k8m4p6r2w51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "giai_thich_lech",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("nguon", sa.String(length=20), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), nullable=True),
        sa.Column("den_ngay", sa.Date(), nullable=False),
        sa.Column("so_tien", sa.Numeric(18, 2), nullable=False),
        sa.Column("ly_do", sa.String(length=300), nullable=False),
        sa.Column("trang_thai", sa.String(length=20), nullable=False,
                  server_default="hieu_luc"),
        sa.Column("boi", sa.String(length=50), nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("huy_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("huy_luc", sa.DateTime(), nullable=True),
        sa.Column("huy_ly_do", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["tai_khoan_id"], ["bank_accounts_cat.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_giai_thich_lech_company_id", "giai_thich_lech", ["company_id"])
    op.create_index("ix_giai_thich_lech_trang_thai", "giai_thich_lech", ["trang_thai"])
    op.create_index("ix_giai_thich_lech_ct_ngay", "giai_thich_lech",
                    ["company_id", "den_ngay", "trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_giai_thich_lech_ct_ngay", table_name="giai_thich_lech")
    op.drop_index("ix_giai_thich_lech_trang_thai", table_name="giai_thich_lech")
    op.drop_index("ix_giai_thich_lech_company_id", table_name="giai_thich_lech")
    op.drop_table("giai_thich_lech")
