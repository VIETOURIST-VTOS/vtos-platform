"""V11 – hai bảng lịch tự động hóa: tác vụ khai báo và lần chạy báo về

Revision ID: v11d8e4b6a2f79
Revises: v12c5a9d3f2e81
"""
from alembic import op
import sqlalchemy as sa

revision = "v11d8e4b6a2f79"
# Nối sau V12 – đầu mạch của nhánh gop-dot2 tính tới 09/9/2026. Đếm trên ORIGIN chứ không trên thư
# mục đang mở: hai phiên làm song song thì thư mục của mỗi bên đều ra một đầu, và mạch chỉ tách làm
# hai vào đúng lúc gộp. Xem lại bản v10a7f3c9e1b48 – cùng một lỗi đã xảy ra hai lần trên cùng gốc.
down_revision = "v12c5a9d3f2e81"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tac_vu_tu_dong",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(60), nullable=False),
        sa.Column("ten", sa.String(200), nullable=False),
        sa.Column("mo_ta", sa.Text(), server_default="", nullable=False),
        sa.Column("he_thong", sa.String(10), server_default="n8n", nullable=False),
        sa.Column("lich_doc", sa.String(120), server_default="", nullable=False),
        sa.Column("lich_cron", sa.String(80), server_default="", nullable=False),
        sa.Column("phong_ban", sa.String(20), server_default="", nullable=False),
        sa.Column("nguoi_phu_trach", sa.String(80), server_default="", nullable=False),
        # 0 = không canh im lặng. Xem chú thích trong app/models/tu_dong.py.
        sa.Column("han_toi_da_phut", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quan_trong", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("bat", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("ly_do_tat", sa.String(300), server_default="", nullable=False),
        sa.Column("tao_boi", sa.String(50), server_default="", nullable=False),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tac_vu_tu_dong_ma", "tac_vu_tu_dong", ["ma"], unique=True)

    op.create_table(
        "lan_chay_tac_vu",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tac_vu_id", sa.Integer(), sa.ForeignKey("tac_vu_tu_dong.id"), nullable=False),
        sa.Column("ma_lan", sa.String(80), nullable=False),
        sa.Column("trang_thai", sa.String(12), server_default="dang_chay", nullable=False),
        sa.Column("bat_dau", sa.DateTime(), nullable=True),
        sa.Column("ket_thuc", sa.DateTime(), nullable=True),
        sa.Column("giay", sa.Float(), server_default="0", nullable=False),
        # ĐỂ RỖNG ĐƯỢC, có chủ ý: rỗng = "không đếm được", 0 = "chạy xong, không có gì để làm".
        # Đặt NOT NULL DEFAULT 0 ở đây là xóa mất chỗ khác nhau giữa hai câu đó.
        sa.Column("so_ban_ghi", sa.Integer(), nullable=True),
        sa.Column("thong_bao", sa.Text(), server_default="", nullable=False),
        sa.Column("chi_tiet", sa.JSON(), nullable=True),
        sa.Column("boi", sa.String(50), server_default="", nullable=False),
    )
    # Duy nhất theo mã lần: n8n thử lại khi mạng chập, và một lần chạy đếm thành hai làm hỏng đúng
    # con số mà màn hình này sinh ra để cho người ta tin.
    op.create_index("ix_lan_chay_tac_vu_ma_lan", "lan_chay_tac_vu", ["ma_lan"], unique=True)
    op.create_index("ix_lan_chay_tac_vu_tac_vu_id", "lan_chay_tac_vu", ["tac_vu_id"])
    op.create_index("ix_lan_chay_tac_vu_trang_thai", "lan_chay_tac_vu", ["trang_thai"])
    op.create_index("ix_lan_chay_tac_vu_bat_dau", "lan_chay_tac_vu", ["bat_dau"])
    op.create_index("ix_lan_chay_tac_vu_luc", "lan_chay_tac_vu", ["tac_vu_id", "bat_dau"])


def downgrade():
    op.drop_table("lan_chay_tac_vu")
    op.drop_table("tac_vu_tu_dong")
