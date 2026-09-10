"""Cửa nhập hoá đơn đầu vào trên dòng chi phí quyết toán

Revision ID: 8de308e27b31
Revises: zf6a7b8c9d0e
"""
from alembic import op
import sqlalchemy as sa
from app.models.kieu_tien import TIEN

revision = "8de308e27b31"
down_revision = "zf6a7b8c9d0e"
branch_labels = None
depends_on = None

# Chủ tịch yêu cầu lớp 2 của bảng lãi lỗ hiện chi tiết nhà cung cấp: tên, mã số thuế, địa chỉ, SỐ HOÁ ĐƠN.
# Ba thứ đầu đã có (địa chỉ lấy từ hồ sơ NCC). Số hoá đơn thì không: VTOS chỉ có một ô đúng/sai
# "có hoá đơn" trên đề nghị chi, và một ô ghi chú tự do.
#
# Biết CÓ hoá đơn mà không tra được hoá đơn NÀO thì không đối chiếu được với tờ khai thuế, và cũng
# không trả lời được câu hỏi đơn giản nhất lúc quyết toán: khoản chi này có chứng từ hợp lệ không.
# Đây là một cửa nhập còn thiếu, không phải một con số máy tự suy ra được.
#
# Cả bốn cột đều CHO PHÉP RỖNG và KHÔNG có mặc định – theo đúng quy ước K2 ngày 09/9/2026: để trống
# nghĩa là chưa nhập, không phải bằng 0 hay chuỗi rỗng.

COT = (
    ("so_hoa_don", sa.String(30)),
    ("ngay_hoa_don", sa.Date()),
    ("vat_hoa_don", TIEN),
)


def upgrade() -> None:
    for ten, kieu in COT:
        op.add_column("tour_cost_lines", sa.Column(ten, kieu, nullable=True))
    op.add_column("tour_cost_lines", sa.Column("supplier_id", sa.Integer(), nullable=True))
    op.create_index("ix_tour_cost_lines_supplier_id", "tour_cost_lines", ["supplier_id"])
    op.create_foreign_key("fk_tour_cost_lines_supplier", "tour_cost_lines", "suppliers", ["supplier_id"], ["id"])


def downgrade() -> None:
    """Hạ cấp XOÁ số hoá đơn đã nhập – không có cách nào giữ lại.

    Ghi rõ ở đây để người chạy biết trước: đây không phải thao tác đảo ngược vô hại. Nếu đã có người
    nhập hoá đơn thì hạ cấp là mất dữ liệu chứng từ thuế, và không phục hồi được bằng nâng cấp lại.
    """
    op.drop_constraint("fk_tour_cost_lines_supplier", "tour_cost_lines", type_="foreignkey")
    op.drop_index("ix_tour_cost_lines_supplier_id", table_name="tour_cost_lines")
    for ten in ("supplier_id", "vat_hoa_don", "ngay_hoa_don", "so_hoa_don"):
        op.drop_column("tour_cost_lines", ten)
