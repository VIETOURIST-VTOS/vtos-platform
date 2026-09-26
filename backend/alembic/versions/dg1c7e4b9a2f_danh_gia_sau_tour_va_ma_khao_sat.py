"""DG-1 · Đánh giá sau tour do khách tự chấm + mã khảo sát dùng một lần

Đề xuất tự động hoá CSKH qua Zalo, 25/9/2026 — bước 2.

KHÔNG có cột tiền nào trong hai bảng này, nên không đụng tới hàng rào kiểu TIEN (V9). Cột `diem`
để NULL được, và đó là cố ý: rỗng nghĩa là khách bỏ qua mục ấy, khác hẳn với chấm 0 điểm.

Revision ID: dg1c7e4b9a2f
Revises: hh1k4d9e2b7c
Create Date: 2026-09-25
"""
import sqlalchemy as sa
from alembic import op

revision = "dg1c7e4b9a2f"
down_revision = "hh1k4d9e2b7c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "danh_gia_sau_tour",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("care_id", sa.Integer(), sa.ForeignKey("care_tickets.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("doi_tuong", sa.String(length=12), nullable=False),
        sa.Column("doi_tuong_id", sa.Integer(), nullable=True),
        sa.Column("doi_tuong_ten", sa.String(length=120), nullable=False, server_default=""),
        # nullable=True và KHÔNG có server_default: rỗng ≠ 0. Xem chú thích ở models/danh_gia.py.
        sa.Column("diem", sa.Integer(), nullable=True),
        sa.Column("nhan_xet", sa.Text(), nullable=False, server_default=""),
        sa.Column("nguon", sa.String(length=10), nullable=False, server_default="khach"),
        sa.Column("nguoi_ghi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_danh_gia_sau_tour_care_id", "danh_gia_sau_tour", ["care_id"])
    op.create_index("ix_danh_gia_sau_tour_booking_id", "danh_gia_sau_tour", ["booking_id"])
    op.create_index("ix_danh_gia_sau_tour_tour_id", "danh_gia_sau_tour", ["tour_id"])
    op.create_index("ix_danh_gia_sau_tour_doi_tuong", "danh_gia_sau_tour", ["doi_tuong"])
    op.create_index("ix_danh_gia_sau_tour_doi_tuong_id", "danh_gia_sau_tour", ["doi_tuong_id"])
    op.create_index("ix_danh_gia_sau_tour_nguon", "danh_gia_sau_tour", ["nguon"])
    op.create_index("ix_danh_gia_sau_tour_tao_luc", "danh_gia_sau_tour", ["tao_luc"])
    # Một đối tượng chỉ được chấm MỘT lần trên một phiếu. Không có ràng buộc này thì một lần bấm
    # hai lần trên điện thoại yếu sóng sẽ thành hai điểm, và điểm trung bình lệch mà không ai biết.
    op.create_unique_constraint("uq_danh_gia_phieu_doi_tuong", "danh_gia_sau_tour",
                                ["care_id", "doi_tuong", "doi_tuong_id"])

    op.create_table(
        "ma_khao_sat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=64), nullable=False),
        sa.Column("care_id", sa.Integer(), sa.ForeignKey("care_tickets.id"), nullable=False),
        sa.Column("het_han", sa.DateTime(), nullable=False),
        sa.Column("dung_luc", sa.DateTime(), nullable=True),
        sa.Column("so_lan_mo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mo_lan_dau", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ma_khao_sat_ma", "ma_khao_sat", ["ma"], unique=True)
    op.create_index("ix_ma_khao_sat_care_id", "ma_khao_sat", ["care_id"], unique=True)
    op.create_index("ix_ma_khao_sat_het_han", "ma_khao_sat", ["het_han"])

    # Hàng đợi Zalo có GIỜ HẸN. Trước hôm nay `send_pending` gửi ngay khi tới lượt; đề xuất đòi gửi
    # lúc 9h sáng hôm sau. Rỗng = gửi ngay như cũ, nên cột này không đổi hành vi của tin đang chạy.
    op.add_column("zalo_messages", sa.Column("gui_tu_luc", sa.DateTime(), nullable=True))
    op.create_index("ix_zalo_messages_gui_tu_luc", "zalo_messages", ["gui_tu_luc"])


def downgrade() -> None:
    op.drop_index("ix_zalo_messages_gui_tu_luc", table_name="zalo_messages")
    op.drop_column("zalo_messages", "gui_tu_luc")
    op.drop_table("ma_khao_sat")
    op.drop_table("danh_gia_sau_tour")
