"""TC-73: hai bảng cơ cấu tổ chức khối Kinh doanh - don_vi_kd va phan_cong_kd

Revision ID: tc73kd0a1b2c3d
Revises: bl7f4a2c9e1d83
"""
import sqlalchemy as sa
from alembic import op

revision = "tc73kd0a1b2c3d"
down_revision = "bl7f4a2c9e1d83"
branch_labels = None
depends_on = None

# Bản này chỉ TẠO hai bảng rỗng. Không chép một dòng nào từ `users.sales_group`,
# `users.department` hay `employees.office` sang.
#
# Chép được về mặt kỹ thuật, và đó chính là lý do phải nói rõ vì sao không chép: ba chuỗi ấy gõ tay
# suốt bốn năm, không ràng buộc nào, nên trong đó có cả lỗi chính tả lẫn nhóm đã giải thể. Chép sang
# là biến một đống chuỗi không ai dám tin thành một bảng quan hệ trông rất đáng tin — cùng dữ liệu,
# nhưng mất luôn cái dấu hiệu cho biết nó đáng ngờ. Hành chính – Nhân sự khai lại ở màn hình
# /to-chuc-kd, cột "Nhóm cũ" trên màn hình ấy để tra cứu khi khai.
#
# Cũng vì vậy bản này KHÔNG đụng tới ba cột cũ: chúng còn nguyên, còn chạy, còn là thứ
# `access.sales_ids_visible()` đang dùng. Bỏ chúng là việc của vòng sau, sau khi bảng mới đã đủ
# người và đã đối chiếu xong — gộp vào đây thì một lần triển khai hỏng là mất cả phạm vi xem.


def upgrade() -> None:
    op.create_table(
        "don_vi_kd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=32), nullable=False),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("cap", sa.String(length=16), nullable=False),
        sa.Column("mang", sa.String(length=8), nullable=False, server_default="le"),
        sa.Column("cha_id", sa.Integer(), sa.ForeignKey("don_vi_kd.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        sa.Column("hieu_luc_den", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_don_vi_kd_ma", "don_vi_kd", ["ma"], unique=True)
    op.create_index("ix_don_vi_kd_cha_id", "don_vi_kd", ["cha_id"])
    op.create_index("ix_don_vi_kd_mang_cap", "don_vi_kd", ["mang", "cap"])

    op.create_table(
        "phan_cong_kd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("don_vi_id", sa.Integer(), sa.ForeignKey("don_vi_kd.id"), nullable=False),
        sa.Column("vai", sa.String(length=16), nullable=False, server_default="nhan_vien"),
        sa.Column("tu_ngay", sa.Date(), nullable=False),
        # den_ngay CHO RỖNG và đó là điều bản này phải giữ: rỗng nghĩa là CHƯA KẾT THÚC, không phải
        # một ngày xa tít nào đó. Điền 9999-12-31 thay cho rỗng là cách mọi truy vấn "còn hiệu lực"
        # sau này phải nhớ một hằng số ma, và sớm muộn có chỗ quên.
        sa.Column("den_ngay", sa.Date(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_phan_cong_kd_user_id", "phan_cong_kd", ["user_id"])
    op.create_index("ix_phan_cong_kd_don_vi_id", "phan_cong_kd", ["don_vi_id"])
    op.create_index("ix_phan_cong_kd_nguoi_ngay", "phan_cong_kd", ["user_id", "tu_ngay", "den_ngay"])


def downgrade() -> None:
    op.drop_index("ix_phan_cong_kd_nguoi_ngay", table_name="phan_cong_kd")
    op.drop_index("ix_phan_cong_kd_don_vi_id", table_name="phan_cong_kd")
    op.drop_index("ix_phan_cong_kd_user_id", table_name="phan_cong_kd")
    op.drop_table("phan_cong_kd")
    op.drop_index("ix_don_vi_kd_mang_cap", table_name="don_vi_kd")
    op.drop_index("ix_don_vi_kd_cha_id", table_name="don_vi_kd")
    op.drop_index("ix_don_vi_kd_ma", table_name="don_vi_kd")
    op.drop_table("don_vi_kd")
