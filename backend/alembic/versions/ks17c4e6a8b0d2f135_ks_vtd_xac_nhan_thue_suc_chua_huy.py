"""KS-17 — khách sạn VTD: xác nhận thuế phí, mô tả thay thế của ảnh, sức chứa «chưa xác nhận», giờ chốt hủy.

Chủ tịch «làm luôn cả 5 việc» 03/11/2026, theo báo cáo cập nhật 41 khách sạn:
  · khach_san_vtd.thue_phi_xac_nhan — 0% mặc định không phải xác nhận; mọi dòng cũ = CHƯA xác nhận.
  · anh_khach_san_vtd.mo_ta_thay_the — chữ thay ảnh (alt).
  · loai_phong_vtd.tong_khach_toi_da + toi_da_nguoi_lon cho phép rỗng (= chưa xác nhận). Số cũ giữ nguyên.
  · goi_gia_vtd.huy_gio_chot, huy_mui_gio, cho_tra_sau — mặc định giữ đúng hành vi cũ (hết ngày, giờ VN, cho trả sau).

Revision ID: ks17c4e6a8b0d2f135
Revises: sa3c7e9a1b3d5f70
Create Date: 2026-11-03
"""
import sqlalchemy as sa
from alembic import op

revision = "ks17c4e6a8b0d2f135"
down_revision = "sa3c7e9a1b3d5f70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("khach_san_vtd") as t:
        t.add_column(sa.Column("thue_phi_xac_nhan", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("anh_khach_san_vtd") as t:
        t.add_column(sa.Column("mo_ta_thay_the", sa.String(200), nullable=False, server_default=""))
    with op.batch_alter_table("loai_phong_vtd") as t:
        t.add_column(sa.Column("tong_khach_toi_da", sa.Integer(), nullable=True))
        t.alter_column("toi_da_nguoi_lon", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("goi_gia_vtd") as t:
        t.add_column(sa.Column("huy_gio_chot", sa.String(5), nullable=False, server_default=""))
        t.add_column(sa.Column("huy_mui_gio", sa.String(40), nullable=False, server_default="Asia/Ho_Chi_Minh"))
        t.add_column(sa.Column("cho_tra_sau", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("goi_gia_vtd") as t:
        t.drop_column("cho_tra_sau")
        t.drop_column("huy_mui_gio")
        t.drop_column("huy_gio_chot")
    with op.batch_alter_table("loai_phong_vtd") as t:
        t.alter_column("toi_da_nguoi_lon", existing_type=sa.Integer(), nullable=False)
        t.drop_column("tong_khach_toi_da")
    with op.batch_alter_table("anh_khach_san_vtd") as t:
        t.drop_column("mo_ta_thay_the")
    with op.batch_alter_table("khach_san_vtd") as t:
        t.drop_column("thue_phi_xac_nhan")
