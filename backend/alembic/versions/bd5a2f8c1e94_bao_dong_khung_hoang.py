"""Sổ gửi báo động khủng hoảng — ghi cả lần KHÔNG gửi được

Revision ID: bd5a2f8c1e94
Revises: tc76ct5a6b7c8d
Create Date: 2026-09-19

MỘT BẢNG, VÀ CỘT QUAN TRỌNG NHẤT LÀ CỘT THẤT BẠI

`canh_bao_gui` — mỗi hàng là MỘT LẦN GỬI một cảnh báo cho MỘT người trên MỘT kênh. Không gộp vào
`alerts` được: một cảnh báo sinh ba người × bốn kênh × hai vòng, nhét vào một hàng thì hoặc thành
mười sáu cột rỗng, hoặc thành một chuỗi JSON không đếm được.

`thanh_cong=False` kèm `ly_do` là hàng phải đọc: "chua_noi_zalo", "chua_cau_hinh_mau_zns",
"chua_co_o_nhap_email". Không có nó thì hệ báo "đã gửi cho 3/3 lãnh đạo" trong khi chỉ 2 máy kêu.

CHỈ MỤC: (alert_id) để dựng phép đo theo vụ, (kenh) và (thanh_cong) để dựng tỷ lệ tới được theo
kênh, (vong) để tách vòng đầu với vòng leo thang. Bốn chỉ mục cho một bảng nhỏ là nhiều, nhưng bảng
này SINH RA để bị nhóm lại mà đếm, và phép đo chạy hằng tháng thì chỉ mục rẻ hơn lần quét bảng.

KHÔNG thêm cột vào `alerts`: bảng ấy mọi làn đều đọc, và quan hệ này là một-nhiều.
"""
import sqlalchemy as sa
from alembic import op

revision = "bd5a2f8c1e94"
down_revision = "tc76ct5a6b7c8d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "canh_bao_gui",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kenh", sa.String(length=16), nullable=False),
        sa.Column("vong", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gui_luc", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        # server_default=sa.false() chứ KHÔNG phải sa.text("0"): Postgres không nhận "0" cho kiểu
        # boolean và bản di trú sẽ chết lúc khởi động hộp chứa, không phải lúc chạy phép thử.
        sa.Column("thanh_cong", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ly_do", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("ma_ngoai", sa.String(length=80), nullable=False, server_default=""),
    )
    op.create_index("ix_cbg_alert", "canh_bao_gui", ["alert_id"])
    op.create_index("ix_cbg_user", "canh_bao_gui", ["user_id"])
    op.create_index("ix_cbg_kenh", "canh_bao_gui", ["kenh"])
    op.create_index("ix_cbg_vong", "canh_bao_gui", ["vong"])
    op.create_index("ix_cbg_gui_luc", "canh_bao_gui", ["gui_luc"])
    op.create_index("ix_cbg_thanh_cong", "canh_bao_gui", ["thanh_cong"])


def downgrade():
    for t in ("ix_cbg_thanh_cong", "ix_cbg_gui_luc", "ix_cbg_vong", "ix_cbg_kenh",
              "ix_cbg_user", "ix_cbg_alert"):
        op.drop_index(t, table_name="canh_bao_gui")
    op.drop_table("canh_bao_gui")
