"""Lời chào chuyến cho HDV cộng tác viên: từ chối, hết hạn, hạn trả lời

Toàn bộ hướng dẫn viên đã chuyển sang cộng tác viên (07/9/2026). Trước bản này một lệnh phân chuyến chỉ
có ba trạng thái: chờ xác nhận, đã xác nhận, hủy. Không có chỗ nào ghi được "người này từ chối" — nên
mọi lần từ chối nằm mãi ở "chờ xác nhận" và trông y hệt một lần chậm trễ.

Đó không phải chuyện thẩm mỹ dữ liệu. Từ chối một lời chào là quyền của người cung cấp dịch vụ; ghi nó
thành "chưa xác nhận" là tự dựng lên hồ sơ cho thấy công ty giao việc và người kia không tuân thủ —
đúng thứ mà cơ quan bảo hiểm nhìn vào khi xác định lại quan hệ lao động, bất kể hợp đồng mang tên gì.

Revision ID: e0f1a2b3c4d5
Revises: 0ac7b3a3346f (đầu nhánh trên origin lúc viết – kho luôn phải có MỘT đầu duy nhất)
"""
from alembic import op
import sqlalchemy as sa

revision = "e0f1a2b3c4d5"
down_revision = "760b24f75c38"   # phiên song song: nối sau ngân sách Marketing để mạch migration chỉ có MỘT đầu
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "guide_assignments" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("guide_assignments")}
    if "ly_do" not in cols:
        op.add_column("guide_assignments", sa.Column("ly_do", sa.String(200), server_default=""))
    if "han_tra_loi" not in cols:
        op.add_column("guide_assignments", sa.Column("han_tra_loi", sa.DateTime, nullable=True))
    if "tra_loi_luc" not in cols:
        op.add_column("guide_assignments", sa.Column("tra_loi_luc", sa.DateTime, nullable=True))


def downgrade() -> None:
    for c in ("tra_loi_luc", "han_tra_loi", "ly_do"):
        op.drop_column("guide_assignments", c)
