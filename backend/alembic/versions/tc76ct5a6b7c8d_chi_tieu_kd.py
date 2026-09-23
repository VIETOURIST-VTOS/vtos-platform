"""TC-76: bang chi tieu kinh doanh theo don vi hoac theo nguoi

Revision ID: tc76ct5a6b7c8d
Revises: tc74nb1c2d3e4f
"""
import sqlalchemy as sa
from alembic import op

revision = "tc76ct5a6b7c8d"
down_revision = "tc74nb1c2d3e4f"   # noi SAU ban doi tac ban hang cua TC-74
branch_labels = None
depends_on = None

# MOT BANG MOI, RONG. Khong dong mot dong du lieu nao.
#
# BANG NAY TUNG BI RUT KHOI TC-74 vi luc do no chua co cua nhap - chua co API, chua co man hinh.
# Hai phep thu canh da bat dung cho ay (test_mo_hinh_va_ban_nang_cap_khong_duoc_lech_nhau va
# test_cn1_moi_bang_deu_phai_co_cua_hoac_duoc_khai_la_may_sinh). Ranh gioi 09/9/2026 noi ro: mot
# bang khong co cua la viec CON THIEU. Vong nay mang cua den cung no:
#     cua API   app/api/v1/kinh_doanh.py       POST /api/v1/kinh-doanh/chi-tieu
#     man hinh  web/app/kinh-doanh-le/page.tsx khung "Giao chi tieu"
#
# KHONG DIEN SAN CHI TIEU NAO, va day khong phai chuyen luoi. Chi tieu la dieu NGUOI TA QUYET DINH.
# Suy no tu thuc hien ky truoc thi thang nao ban kem, thang sau chi tieu tu ha xuong - thuoc do
# thanh cai bong cua chinh so bi do, ma khong ai thay gi bat thuong. Cung ly le da ghi cho bang
# ke_hoach_thang (TC-41).
#
# RANG BUOC DUY NHAT CO HAI COT CHO RONG, va do la mot gioi han THAT chu khong phai mot loi. Trong
# SQL thi RONG KHAC RONG: hai dong cung `ky`, cung `user_id`, cung `luong`, ca hai `don_vi_id` rong
# - co so du lieu coi la hai o khac nhau va cho ghi ca hai. Nen rang buoc nay chi la luoi THU HAI;
# luoi thu nhat la phep tim dong cu o app/services/chi_tieu_kd.py, va no khong bo duoc.


def upgrade() -> None:
    op.create_table(
        "chi_tieu_kd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ky", sa.String(length=7), nullable=False),
        # DUNG MOT trong hai cot duoi duoc dien. May chu chan o lop dich vu - rang buoc duy nhat
        # khong bat duoc chuyen nay, no chi chan trung o.
        sa.Column("don_vi_id", sa.Integer(), sa.ForeignKey("don_vi_kd.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("luong", sa.String(length=12), nullable=False, server_default="tat_ca"),
        sa.Column("muc_tieu", sa.Numeric(18, 2), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("ly_do_sua", sa.Text(), nullable=False, server_default=""),
        sa.Column("so_lan_sua", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nguoi_nhap", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("ky", "don_vi_id", "user_id", "luong", name="uq_chi_tieu_kd_o"),
    )
    op.create_index("ix_chi_tieu_kd_ky", "chi_tieu_kd", ["ky"])
    op.create_index("ix_chi_tieu_kd_don_vi_id", "chi_tieu_kd", ["don_vi_id"])
    op.create_index("ix_chi_tieu_kd_user_id", "chi_tieu_kd", ["user_id"])
    op.create_index("ix_chi_tieu_kd_ky_don_vi", "chi_tieu_kd", ["ky", "don_vi_id"])
    op.create_index("ix_chi_tieu_kd_ky_nguoi", "chi_tieu_kd", ["ky", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_chi_tieu_kd_ky_nguoi", table_name="chi_tieu_kd")
    op.drop_index("ix_chi_tieu_kd_ky_don_vi", table_name="chi_tieu_kd")
    op.drop_index("ix_chi_tieu_kd_user_id", table_name="chi_tieu_kd")
    op.drop_index("ix_chi_tieu_kd_don_vi_id", table_name="chi_tieu_kd")
    op.drop_index("ix_chi_tieu_kd_ky", table_name="chi_tieu_kd")
    op.drop_table("chi_tieu_kd")
