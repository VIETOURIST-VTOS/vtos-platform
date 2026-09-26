"""CHS-1 · Chủ hồ sơ quyết toán + bậc thang đòi nợ

Chủ tịch quyết 25/9/2026, câu 4 (Sale Admin lập quyết toán đoàn) và câu 5 (thang bậc đòi nợ).

Hai cột, hai bảng, một bản nâng cấp — vì chúng ra đời trong cùng một lần quyết và cùng không mang
số liệu nào. `alerts.bac` để RỖNG với mọi loại cảnh báo không có thang, tức gần như toàn bộ bảng.

MỘT CỘT, ĐỂ TRỐNG ĐƯỢC, KHÔNG NẠP NGƯỢC. Trống nghĩa là "chưa chỉ đích danh ai", và khi đó
`services/chu_ho_so.py` rơi về mặc định của mảng Đoàn rồi tới `operator_id` — tức luật cũ. Nên
hơn một nghìn chuyến đang có không cần đụng tới, và bản nâng cấp này không viết một con số nào
vào dữ liệu đang chạy.

KHÔNG có cột tiền → không đụng hàng rào kiểu TIEN (V9).

Revision ID: ch1f5a8d3e6b
Revises: dg1c7e4b9a2f
Create Date: 2026-09-26
"""
import sqlalchemy as sa
from alembic import op

revision = "ch1f5a8d3e6b"
down_revision = "dg1c7e4b9a2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tours", sa.Column("chu_ho_so_id", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("bac", sa.Integer(), nullable=True))
    # Khoá ngoại khai rời, trong batch: SQLite không thêm được ràng buộc vào bảng đã có bằng
    # ALTER thường, và bản chạy thử của đội vẫn là SQLite.
    with op.batch_alter_table("tours") as b:
        b.create_foreign_key("fk_tours_chu_ho_so_id_users", "users", ["chu_ho_so_id"], ["id"])


def downgrade() -> None:
    op.drop_column("alerts", "bac")
    with op.batch_alter_table("tours") as b:
        b.drop_constraint("fk_tours_chu_ho_so_id_users", type_="foreignkey")
    op.drop_column("tours", "chu_ho_so_id")
