"""KS-11 — chủ đơn khách sạn: cột cho cửa khách gửi yêu cầu.

Không có cột chủ đơn, quyền đọc một đơn chỉ còn dựa vào việc BIẾT thẻ tham chiếu — mà thẻ tham
chiếu là thứ được in ra, gửi qua tin nhắn, chụp màn hình. Đó là lý do KS-10 chỉ mở cửa cho Điều
hành. Vòng này thêm chủ đơn, và cửa cho khách mở được.

Mọi cột mới đều nullable hoặc có mặc định, và `ota_id` đổi sang nullable: đơn Điều hành tự dựng
(KS-10) không có chủ, còn yêu cầu của khách thì chưa có nguồn. Cả hai phải chạy tiếp được.

Revision ID: ks11a7c3e9d521
Revises: at3a5d8c2e7f4b19
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "ks11a7c3e9d521"
down_revision = "at3a5d8c2e7f4b19"
branch_labels = None
depends_on = None

BANG = "don_khach_san_ota"

COT_CHU = (
    ("cong", sa.String(length=20)),
    ("nguoi_nhan_phong", sa.String(length=160)),
    ("lien_he", sa.String(length=160)),
    ("noi_den", sa.String(length=160)),
)


def upgrade() -> None:
    op.add_column(BANG, sa.Column("tai_khoan_ngoai_id", sa.Integer(), nullable=True))
    op.create_index("ix_don_ks_ota_tkn", BANG, ["tai_khoan_ngoai_id"])
    op.create_foreign_key("fk_don_ks_ota_tkn", BANG, "tai_khoan_ngoai",
                          ["tai_khoan_ngoai_id"], ["id"])
    for ten, kieu in COT_CHU:
        op.add_column(BANG, sa.Column(ten, kieu, nullable=False, server_default=""))
    op.add_column(BANG, sa.Column("yeu_cau_them", sa.Text(), nullable=False, server_default=""))
    op.add_column(BANG, sa.Column("gui_luc", sa.DateTime(), nullable=True))
    # Yêu cầu của khách chưa có nguồn — Điều hành gắn vào ở bước hỏi giá.
    op.alter_column(BANG, "ota_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column(BANG, "ota_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column(BANG, "gui_luc")
    op.drop_column(BANG, "yeu_cau_them")
    for ten, _k in reversed(COT_CHU):
        op.drop_column(BANG, ten)
    op.drop_constraint("fk_don_ks_ota_tkn", BANG, type_="foreignkey")
    op.drop_index("ix_don_ks_ota_tkn", table_name=BANG)
    op.drop_column(BANG, "tai_khoan_ngoai_id")
