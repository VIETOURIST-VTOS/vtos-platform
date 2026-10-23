"""Đợt R6b-1 — số dư đầu kỳ: một cửa chốt và bảy sổ phụ.

Revision ID: r6b1a4c7e2f9d5
Revises: cn2g4l8b1s30
Create Date: 2026-10-23

TÁM BẢNG MỚI, không đụng một cột nào của bảng đang có.

Cột `ma_doi_tuong` của bảy sổ phụ: NOT NULL, mặc định chuỗi rỗng. Rỗng là MỘT TRẠNG THÁI có
nghĩa — "chưa gán mã" — chứ không phải "chưa khai cột". Hai thứ ấy đọc ra khác nhau ở mọi phép
gom, và cho NULL vào thì mỗi câu tổng hợp phải nhớ coalesce một lần nữa; quên một lần là dòng
thiếu mã lặng lẽ vào tổng.

KHÔNG có ràng buộc DUY NHẤT trên (ky, tk, ma_doi_tuong), và đó là chủ ý: ba dòng chưa gán mã
trên cùng một tài khoản là ba dòng hợp lệ (xem app/models/so_du_dau_ky.py), mà một ràng buộc
duy nhất sẽ chặn đúng dòng thứ hai — người nhập mất số liệu ở chỗ đáng ra chỉ cần một cảnh báo.
"""
import sqlalchemy as sa
from alembic import op

revision = "r6b1a4c7e2f9d5"
down_revision = "cn2g4l8b1s30"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def _chung() -> list:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(length=7), nullable=False, index=True),
        sa.Column("tk", sa.String(length=10), sa.ForeignKey("accounts.code"),
                  nullable=False, index=True),
        sa.Column("ma_doi_tuong", sa.String(length=60), nullable=False,
                  server_default="", index=True),
        sa.Column("ten", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("nguon", sa.String(length=20), nullable=False, server_default="nhap_tay"),
        sa.Column("ghi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ghi_luc", sa.DateTime(), nullable=True),
    ]


def _no_co() -> list:
    # CHO RONG, KHONG mac dinh - xem quy tac 4 o app/models/so_du_dau_ky.py
    return [sa.Column("du_no", TIEN, nullable=True),
            sa.Column("du_co", TIEN, nullable=True)]


SO_PHU = {
    "so_du_dau_ky_ngan_hang": _no_co() + [
        sa.Column("so_tai_khoan", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("ngan_hang", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("loai_tien", sa.String(length=3), nullable=False, server_default="VND"),
        sa.Column("so_nguyen_te", TIEN, nullable=True),
        sa.Column("ty_gia", TIEN, nullable=True),
    ],
    "so_du_dau_ky_khach_hang": _no_co(),
    "so_du_dau_ky_nha_cung_cap": _no_co(),
    "so_du_dau_ky_nhan_vien": _no_co(),
    "so_du_dau_ky_tai_san": [
        sa.Column("nguyen_gia", TIEN, nullable=True),
        sa.Column("khau_hao_luy_ke", TIEN, nullable=True),
        sa.Column("gia_tri_con_lai", TIEN, nullable=True),
        sa.Column("so_ky_con", sa.Integer(), nullable=True),
        sa.Column("bo_phan", sa.String(length=20), nullable=False, server_default=""),
    ],
    "so_du_dau_ky_tra_truoc": [
        sa.Column("gia_tri_ban_dau", TIEN, nullable=True),
        sa.Column("da_phan_bo", TIEN, nullable=True),
        sa.Column("con_lai", TIEN, nullable=True),
        sa.Column("so_ky_con", sa.Integer(), nullable=True),
        sa.Column("khoan_muc", sa.String(length=40), nullable=False, server_default=""),
    ],
    "so_du_dau_ky_do_dang": [
        sa.Column("so_tien", TIEN, nullable=True),
    ],
}


def upgrade() -> None:
    op.create_table(
        "so_du_dau_ky",
        sa.Column("ky", sa.String(length=7), primary_key=True),
        sa.Column("tk", sa.String(length=10), sa.ForeignKey("accounts.code"), primary_key=True),
        sa.Column("du_no", TIEN, nullable=True),
        sa.Column("du_co", TIEN, nullable=True),
        sa.Column("nguon", sa.String(length=20), nullable=False, server_default="nhap_tay"),
        sa.Column("ghi_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("ghi_luc", sa.DateTime(), nullable=True),
    )
    for ten, rieng in SO_PHU.items():
        op.create_table(ten, *(_chung() + rieng))


def downgrade() -> None:
    for ten in reversed(list(SO_PHU)):
        op.drop_table(ten)
    op.drop_table("so_du_dau_ky")
