"""Đội xe Đợt 4: ghi vết gợi ý điều xe và nhật ký tác vụ tự động

Hai cột `phuong_an_ai_goi_y` / `ly_do_khac_goi_y` trên lệnh điều xe không phải để hiển thị. Chúng là dữ liệu
duy nhất để sau mỗi quý trả lời được câu "thuật toán gợi ý có tốt lên không, và những lần người chốt lệnh
chọn khác là vì lý do gì" – không có chúng thì chỉ còn tranh luận bằng cảm nhận.

Bảng `fleet_ai_runs` giữ mã băm dữ liệu đầu vào của mỗi lần chạy, để câu "chạy lại cùng dữ liệu phải ra cùng
kết quả" là điều kiểm chứng được chứ không phải một lời hứa.
"""
from alembic import op
import sqlalchemy as sa

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dispatch_orders") as b:
        b.add_column(sa.Column("phuong_an_ai_goi_y", sa.Text, server_default="", nullable=False))
        b.add_column(sa.Column("phuong_an_da_chon", sa.String(60), server_default="", nullable=False))
        b.add_column(sa.Column("ly_do_khac_goi_y", sa.String(300), server_default="", nullable=False))

    op.create_table(
        "fleet_ai_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent", sa.String(20), nullable=False),
        sa.Column("rule_version", sa.String(20), server_default="", nullable=False),
        sa.Column("thoi_diem", sa.DateTime, nullable=True),
        sa.Column("dau_vao_hash", sa.String(64), server_default="", nullable=False),
        sa.Column("so_ban_ghi", sa.Integer, server_default="0", nullable=False),
        sa.Column("so_co", sa.Integer, server_default="0", nullable=False),
        sa.Column("ket_qua", sa.Text, server_default="", nullable=False),
        sa.Column("loi", sa.String(300), server_default="", nullable=False),
        sa.Column("chay_boi", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_ai_runs_agent", "fleet_ai_runs", ["agent", "thoi_diem"])


def downgrade() -> None:
    op.drop_table("fleet_ai_runs")
    with op.batch_alter_table("dispatch_orders") as b:
        for c in ("ly_do_khac_goi_y", "phuong_an_da_chon", "phuong_an_ai_goi_y"):
            b.drop_column(c)
