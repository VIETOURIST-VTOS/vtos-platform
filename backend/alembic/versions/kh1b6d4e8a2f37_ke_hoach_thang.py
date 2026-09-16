"""Kế hoạch tháng – cửa nhập chỉ tiêu doanh thu và lợi nhuận trước thuế

Revision ID: kh1b6d4e8a2f37
Revises: a3d71e9c54b28
"""
from alembic import op
import sqlalchemy as sa

revision = "kh1b6d4e8a2f37"
down_revision = "a3d71e9c54b28"
branch_labels = None
depends_on = None

# Khoá duy nhất (ky, company_id, chi_tieu) là phần đáng chú ý nhất của bảng này. Nó biến thao tác
# "lưu ô kế hoạch" thành GHI ĐÈ thay vì THÊM DÒNG. Bảng kế hoạch mà thêm dòng được thì đến cuối năm
# một tháng có ba con số doanh thu, và không ai còn biết con số nào là chỉ tiêu đã chốt.
#
# Cột tiền dùng numeric(18,2) theo quy ước V9 (models/kieu_tien.TIEN), không dùng số thực nhị phân:
# kế hoạch là số đem đi so với sổ, và hai bên phải cùng một kiểu thì phép so mới sạch.


def upgrade() -> None:
    op.create_table(
        "ke_hoach_thang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(7), nullable=False, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"),
                  nullable=False, index=True),
        sa.Column("chi_tieu", sa.String(30), nullable=False, index=True),
        sa.Column("gia_tri", sa.Numeric(18, 2), nullable=False),
        sa.Column("ly_do_sua", sa.Text(), server_default=""),
        sa.Column("nguoi_nhap", sa.String(50), server_default=""),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        # server_default là CHUỖI "0" chứ không phải số 0: bản nâng cấp ngày 13/9 đã phải sửa lại
        # đúng lỗi này ở một cột Boolean ("cột Boolean không được mặc định bằng số thô").
        sa.Column("so_lan_sua_muon", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("ky", "company_id", "chi_tieu", name="uq_ke_hoach_thang_o"),
    )


def downgrade() -> None:
    """Hạ cấp XOÁ toàn bộ kế hoạch đã nhập, và không ai dựng lại được từ dữ liệu khác.

    Ghi rõ vì đây không phải thao tác đảo ngược vô hại. Doanh thu thực hiện thì cộng lại sổ quyết
    toán lúc nào cũng ra; kế hoạch thì không suy được từ bất kỳ đâu – nó là điều người ta QUYẾT ĐỊNH,
    không phải điều hệ thống đo được. Mất bảng này là mất luôn thước đo của mọi tháng đã qua.
    """
    op.drop_table("ke_hoach_thang")
