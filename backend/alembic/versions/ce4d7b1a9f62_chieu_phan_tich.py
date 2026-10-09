"""Đợt E1 – khai chiều phân tích trên tài khoản, và bảng mức độ chặn.

KHÔNG CHÈN MỘT DÒNG DỮ LIỆU NÀO. Bảng `muc_do_chan` tạo ra rỗng; các cột mới trên `accounts`
thêm vào với giá trị TRỐNG hoặc FALSE, và trống ở đây là một câu nói thật:

  · `tinh_chat` để NULL cho cả 273 tài khoản đang có. NULL = CHƯA AI KHAI, không phải "dư Nợ".
    Đặt mặc định "du_no" là bịa ra một lời khai cho 273 dòng mà không ai ký – và phép kiểm số
    dư bất thường sẽ báo sai hàng loạt ngay ngày đầu. Nguyên tắc K2: trống khác không.
  · Các cờ `td_*` mặc định FALSE. Ở đây FALSE đúng với hiện trạng: hôm nay KHÔNG tài khoản nào
    bắt buộc chiều nào, vì chưa có cơ chế nào bắt. Thêm cột với FALSE không đổi hành vi của một
    dòng bút toán nào – hành vi chỉ đổi khi Kế toán bật cờ, và đó là việc có người ký.

`down_revision` đo lại NGAY TRƯỚC KHI GỘP, không phải lúc viết.

Revision ID: ce4d7b1a9f62
Revises: vb1e7c3a9d5f24
"""
import sqlalchemy as sa
from alembic import op

revision = "ce4d7b1a9f62"
down_revision = "vb1e7c3a9d5f24"
branch_labels = None
depends_on = None

COT_MOI = (
    # (tên cột, kiểu, server_default)
    ("tinh_chat", sa.String(12), None),                  # du_no / du_co / luong_tinh – NULL = chưa khai
    ("co_ngoai_te", sa.Boolean(), sa.false()),
    ("ngung_su_dung", sa.Boolean(), sa.false()),
    ("td_doi_tuong", sa.Boolean(), sa.false()),
    ("td_doi_tuong_loai", sa.String(10), ""),            # kh / ncc / nv / tat_ca
    ("td_cong_trinh", sa.Boolean(), sa.false()),
    ("td_khoan_muc", sa.Boolean(), sa.false()),
)


def upgrade() -> None:
    with op.batch_alter_table("accounts") as b:
        for ten, kieu, mac_dinh in COT_MOI:
            b.add_column(sa.Column(ten, kieu, nullable=True, server_default=mac_dinh))

    op.create_table(
        "muc_do_chan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma_phep_kiem", sa.String(60), nullable=False),
        sa.Column("ten", sa.String(200), nullable=False),
        sa.Column("mo_ta", sa.Text(), server_default=""),
        # RỖNG = chưa ai đặt mức. Không server_default, và đó là chủ ý.
        sa.Column("muc_do", sa.String(20), nullable=True),
        sa.Column("nguoi_xu_ly", sa.String(40), server_default=""),
        sa.Column("han_xu_ly_ngay", sa.Integer(), nullable=True),
        sa.Column("nguoi_thay_the", sa.String(40), server_default=""),
        sa.Column("ngay_hieu_luc", sa.Date(), nullable=True),
        sa.Column("nguoi_ky", sa.String(50), server_default=""),
        sa.Column("can_cu", sa.String(200), server_default=""),
        sa.Column("dang_ap_dung", sa.Boolean(), server_default=sa.true()),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ux_muc_do_chan_ma", "muc_do_chan", ["ma_phep_kiem"], unique=True)


def downgrade() -> None:
    op.drop_table("muc_do_chan")
    with op.batch_alter_table("accounts") as b:
        for ten, _k, _d in reversed(COT_MOI):
            b.drop_column(ten)
