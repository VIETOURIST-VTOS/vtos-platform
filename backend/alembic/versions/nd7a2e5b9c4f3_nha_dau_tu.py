"""Đợt D3 – quan hệ nhà đầu tư: danh bạ, sổ tiếp xúc, sổ cấp quyền xem hồ sơ.

Ba bảng, cả ba tạo ra RỖNG. Không chèn một dòng dữ liệu nào.

KHÔNG có cột số cổ phần sở hữu, và đó là chủ ý: sở hữu là dữ liệu của sổ cổ đông.

`down_revision` đo lại NGAY TRƯỚC KHI GỘP, không phải lúc viết.

Revision ID: nd7a2e5b9c4f3
Revises: pv6f1c4a8e2d9
"""
import sqlalchemy as sa
from alembic import op

revision = "nd7a2e5b9c4f3"
down_revision = "pv6f1c4a8e2d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lien_he_nha_dau_tu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ten", sa.String(160), nullable=False),
        sa.Column("to_chuc", sa.String(200), server_default=""),
        sa.Column("chuc_danh", sa.String(120), server_default=""),
        sa.Column("loai", sa.String(20), server_default="khac"),
        sa.Column("email", sa.String(160), server_default=""),
        sa.Column("dien_thoai", sa.String(40), server_default=""),
        sa.Column("can_cu_thu_thap", sa.Text(), server_default=""),
        sa.Column("ghi_chu", sa.Text(), server_default=""),
        sa.Column("dang_hoat_dong", sa.Boolean(), server_default=sa.true()),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_lien_he_nha_dau_tu_loai", "lien_he_nha_dau_tu", ["loai"])
    op.create_index("ix_lien_he_nha_dau_tu_loai_hd", "lien_he_nha_dau_tu",
                    ["loai", "dang_hoat_dong"])

    op.create_table(
        "tuong_tac_nha_dau_tu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lien_he_id", sa.Integer(), sa.ForeignKey("lien_he_nha_dau_tu.id"),
                  nullable=False),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("hinh_thuc", sa.String(20), server_default="gap"),
        sa.Column("noi_dung_tom_tat", sa.Text(), server_default=""),
        sa.Column("nguoi_du", sa.JSON(), nullable=True),
        sa.Column("co_thong_tin_chua_cong_bo", sa.Boolean(), server_default=sa.false()),
        sa.Column("ban_ghi_cong_bo_id", sa.Integer(), sa.ForeignKey("ban_ghi_cong_bo.id"),
                  nullable=True),
        sa.Column("thong_tin_da_tiet_lo", sa.Text(), server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tuong_tac_nha_dau_tu_lh", "tuong_tac_nha_dau_tu", ["lien_he_id"])
    op.create_index("ix_tuong_tac_nha_dau_tu_ngay", "tuong_tac_nha_dau_tu", ["ngay"])
    op.create_index("ix_tuong_tac_nha_dau_tu_ngay_lh", "tuong_tac_nha_dau_tu",
                    ["ngay", "lien_he_id"])

    op.create_table(
        "quyen_truy_cap_ho_so",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ho_so", sa.String(300), nullable=False),
        sa.Column("nguoi_duoc_cap", sa.String(160), nullable=False),
        sa.Column("to_chuc", sa.String(200), server_default=""),
        sa.Column("lien_he_id", sa.Integer(), sa.ForeignKey("lien_he_nha_dau_tu.id"),
                  nullable=True),
        sa.Column("ly_do", sa.Text(), server_default=""),
        sa.Column("ho_so_chua_cong_bo", sa.Boolean(), server_default=sa.true()),
        sa.Column("cam_ket_bao_mat", sa.Boolean(), server_default=sa.false()),
        sa.Column("can_cu_cam_ket", sa.Text(), server_default=""),
        sa.Column("tu_ngay", sa.Date(), nullable=False),
        # RỖNG = cấp không thời hạn, một việc phải xử lý. Không server_default.
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("thu_hoi_luc", sa.DateTime(), nullable=True),
        sa.Column("thu_hoi_boi", sa.String(50), server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_quyen_truy_cap_ho_so_tu_ngay", "quyen_truy_cap_ho_so", ["tu_ngay"])
    op.create_index("ix_quyen_truy_cap_ho_so_han", "quyen_truy_cap_ho_so",
                    ["den_ngay", "thu_hoi_luc"])


def downgrade() -> None:
    op.drop_table("quyen_truy_cap_ho_so")
    op.drop_table("tuong_tac_nha_dau_tu")
    op.drop_table("lien_he_nha_dau_tu")
