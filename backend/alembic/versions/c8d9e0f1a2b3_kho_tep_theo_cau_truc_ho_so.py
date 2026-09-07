"""Kho tệp xếp theo cấu trúc hồ sơ: pháp nhân / năm / nhóm hồ sơ

Mô hình quản trị số hóa mục 7.2 quy định kho chứng từ số xếp theo Pháp nhân / Năm / Nhóm hồ sơ /
Tháng hoặc Mã đối tượng / Tệp, với chín nhóm cố định giống nhau ở mọi pháp nhân. Cấu trúc cố định là
điều kiện để kiểm toán viên mở kho của một pháp nhân họ chưa từng làm việc cùng mà vẫn tìm được hồ sơ.

Cờ nhay_cam đánh dấu nhóm 06_Nhan_su: dữ liệu cá nhân phải phân quyền riêng theo Nghị định 13/2023 –
xem được màn hình nhân sự không đồng nghĩa với xem được hợp đồng lao động của từng người.

Cha là d3e4f5a6b7c8 chứ không phải b7c8d9e0f1a2: đầu nhánh phải nối theo thứ tự đã có TRÊN ORIGIN, không
theo thứ tự mình viết ra. Một bản migration mắc vào nhánh chưa đẩy lên là một lần deploy hỏng trên máy chủ.

Revision ID: c8d9e0f1a2b3
Revises: d3e4f5a6b7c8
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "attachments" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("attachments")}
    if "phap_nhan" not in cols:
        op.add_column("attachments", sa.Column("phap_nhan", sa.String(30), server_default=""))
    if "nam" not in cols:
        op.add_column("attachments", sa.Column("nam", sa.Integer, server_default="0"))
    if "nhom_ho_so" not in cols:
        op.add_column("attachments", sa.Column("nhom_ho_so", sa.String(20), server_default=""))
    if "nhay_cam" not in cols:
        op.add_column("attachments", sa.Column("nhay_cam", sa.Boolean, server_default=sa.false()))


def downgrade() -> None:
    for c in ("nhay_cam", "nhom_ho_so", "nam", "phap_nhan"):
        op.drop_column("attachments", c)
