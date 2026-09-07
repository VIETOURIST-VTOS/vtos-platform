"""Tài khoản: pháp nhân, lần đăng nhập cuối, buộc đổi mật khẩu + bảng ngoại lệ quyền có thời hạn

Chỉ đạo 07/9/2026: quyền xem bảng lương toàn công ty cấp cho RIÊNG Kế toán trưởng chứ không cho vai trò
Kế toán – nên phải có bảng ngoại lệ theo người, không mở được bằng cách sửa vai trò.

Revision ID: b1c2d3e4f5a6
Revises: e3f4a5b6c7d8
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "e3f4a5b6c7d8"   # nối sau bản của phiên song song – kho phải luôn có MỘT đầu duy nhất,
                                 # Dockerfile chạy "alembic upgrade head" nên hai đầu là container không lên
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("company_id", sa.Integer, nullable=True))
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.add_column("users", sa.Column("last_login", sa.DateTime, nullable=True))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("ngoai_bien_che", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("role_changed_at", sa.DateTime, nullable=True))
    op.add_column("users", sa.Column("role_changed_by", sa.String(50), nullable=False, server_default=""))
    op.create_table(
        "user_grants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False, server_default="capability"),
        sa.Column("value", sa.String(80), nullable=False, server_default=""),
        sa.Column("from_date", sa.Date, nullable=False),
        sa.Column("to_date", sa.Date, nullable=False),
        sa.Column("reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("granted_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_user_grants_user_id", "user_grants", ["user_id"])


def downgrade():
    op.drop_table("user_grants")
    for c in ("role_changed_by", "role_changed_at", "ngoai_bien_che", "must_change_password", "last_login", "company_id"):
        op.drop_column("users", c)
