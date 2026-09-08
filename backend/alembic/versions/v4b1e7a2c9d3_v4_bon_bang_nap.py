"""V4 – bốn bảng đích của mười bốn bộ nạp phòng ban

Revision ID: v4b1e7a2c9d3
Revises: qt7f2c9a1e4b6
Create Date: 2026-09-08

Mười bốn bộ nạp của V4 đổ về mười bốn bảng; mười bảng đã có sẵn. Bốn bảng dưới đây là phần chưa có.

Mọi cột tiền để NULL được – quyết định K2 của Chủ tịch ngày 08/9: "chưa có số" phải nói ra được, và
bảng nào không nói được điều đó sẽ nói dối bằng số 0. Mỗi bảng có đúng một chỉ mục duy nhất làm khóa
chống nạp trùng, đặt ở tầng cơ sở dữ liệu chứ không ở tầng dịch vụ.
"""
from alembic import op
import sqlalchemy as sa

revision = "v4b1e7a2c9d3"
down_revision = "qt7f2c9a1e4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mkt_channel_spend",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(length=7), nullable=False, index=True),
        sa.Column("kenh", sa.String(length=20), nullable=False),
        sa.Column("chien_dich", sa.String(length=120), server_default="", nullable=False),
        sa.Column("so_tien", sa.Float(), nullable=True),
        sa.Column("luot_hien_thi", sa.Integer(), nullable=True),
        sa.Column("luot_nhap", sa.Integer(), nullable=True),
        sa.Column("so_lead", sa.Integer(), nullable=True),
        sa.Column("mo_ta", sa.String(length=300), server_default="", nullable=False),
        sa.Column("chung_tu", sa.String(length=200), server_default="", nullable=False),
        sa.Column("nguon", sa.String(length=20), server_default="nhap_tay", nullable=False),
        sa.Column("boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_mkt_channel_spend", "mkt_channel_spend",
                    ["ky", "kenh", "chien_dich"], unique=True)

    op.create_table(
        "sales_by_consultant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(length=7), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("nhom_kd", sa.String(length=20), server_default="", nullable=False),
        sa.Column("so_booking", sa.Integer(), nullable=True),
        sa.Column("so_khach", sa.Integer(), nullable=True),
        sa.Column("doanh_thu", sa.Float(), nullable=True),
        sa.Column("doanh_thu_da_thu", sa.Float(), nullable=True),
        sa.Column("hoa_hong", sa.Float(), nullable=True),
        sa.Column("ghi_chu", sa.String(length=300), server_default="", nullable=False),
        sa.Column("nguon", sa.String(length=20), server_default="nhap_tay", nullable=False),
        sa.Column("boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_sales_by_consultant", "sales_by_consultant",
                    ["ky", "employee_id"], unique=True)

    op.create_table(
        "purchase_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mst_nguoi_ban", sa.String(length=20), server_default="", nullable=False),
        sa.Column("ten_nguoi_ban", sa.String(length=200), server_default="", nullable=False),
        sa.Column("ky_hieu", sa.String(length=20), server_default="", nullable=False),
        sa.Column("so_hoa_don", sa.String(length=20), server_default="", nullable=False),
        sa.Column("ngay_hd", sa.Date(), nullable=True),
        sa.Column("noi_dung", sa.String(length=300), server_default="", nullable=False),
        sa.Column("tien_truoc_thue", sa.Float(), nullable=True),
        sa.Column("thue_suat", sa.Float(), nullable=True),
        sa.Column("tien_thue", sa.Float(), nullable=True),
        sa.Column("tong_tien", sa.Float(), nullable=True),
        sa.Column("ma_tour", sa.String(length=60), server_default="", nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("khop", sa.String(length=20), server_default="chua_khop", nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=True),
        sa.Column("chung_tu", sa.String(length=200), server_default="", nullable=False),
        sa.Column("nguon", sa.String(length=20), server_default="nhap_tay", nullable=False),
        sa.Column("ghi_chu", sa.String(length=300), server_default="", nullable=False),
        sa.Column("boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    # Bộ ba định danh một hóa đơn ở cơ quan thuế. Lấy số hóa đơn một mình thì hai nhà cung cấp cùng có
    # hóa đơn số 42 sẽ đè lên nhau.
    op.create_index("ux_purchase_invoices", "purchase_invoices",
                    ["mst_nguoi_ban", "ky_hieu", "so_hoa_don"], unique=True)

    op.create_table(
        "social_insurance_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(length=7), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("muc_dong", sa.Float(), nullable=True),
        sa.Column("cty_dong", sa.Float(), nullable=True),
        sa.Column("nld_dong", sa.Float(), nullable=True),
        sa.Column("so_ngay_dong", sa.Float(), nullable=True),
        sa.Column("trang_thai", sa.String(length=20), server_default="dang_dong", nullable=False),
        sa.Column("ghi_chu", sa.String(length=300), server_default="", nullable=False),
        sa.Column("nguon", sa.String(length=20), server_default="nhap_tay", nullable=False),
        sa.Column("boi", sa.String(length=50), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_social_insurance_periods", "social_insurance_periods",
                    ["ky", "employee_id"], unique=True)


def downgrade() -> None:
    for ix, tb in (("ux_social_insurance_periods", "social_insurance_periods"),
                   ("ux_purchase_invoices", "purchase_invoices"),
                   ("ux_sales_by_consultant", "sales_by_consultant"),
                   ("ux_mkt_channel_spend", "mkt_channel_spend")):
        op.drop_index(ix, table_name=tb)
        op.drop_table(tb)
