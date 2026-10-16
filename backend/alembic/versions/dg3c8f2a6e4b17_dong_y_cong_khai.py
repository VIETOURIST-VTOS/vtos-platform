# -*- coding: utf-8 -*-
"""HD-DG3 — bang dong y cong khai nhan xet.

VI SAO MOT BANG RIENG chu khong them cot vao `danh_gia_sau_tour`: dong y la mot HANH VI co thoi
diem, co pham vi, co duong rut va co the bi rut lai. Nhet vao bang diem thi moi lan khach rut la
mot lan sua dong diem — va dong diem thi khong duoc sua, no la loi khach da noi.

Revision ID: dg3c8f2a6e4b17
Revises: <dat lai ngay truoc khi day — xem chu thich duoi>
"""
import sqlalchemy as sa
from alembic import op

revision = "dg3c8f2a6e4b17"
# DAU MACH PHAI DO LAI NGAY TRUOC KHI DAY, khong phai luc viet ban di tru nay.
# Bai hoc 16/10/2026: ban di tru q2a tro vao dx3b7e2a9c4f61 luc ay dang la dau mach; main nhich
# them PR #367 va R3a cung moc tu do, nen gop xong co HAI dau mach va `alembic upgrade head` dung.
# Gia tri duoi la dau mach do duoc luc viet; chay lai phep do truoc khi day.
down_revision = "q2a3d5f7b9c1e"
branch_labels = None
depends_on = None

BANG = "dong_y_cong_khai"


def upgrade() -> None:
    op.create_table(
        BANG,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("danh_gia_id", sa.Integer(), sa.ForeignKey("danh_gia_sau_tour.id"), nullable=False),
        sa.Column("care_id", sa.Integer(), nullable=False),
        sa.Column("tour_id", sa.Integer(), nullable=False),
        # Viec cua khach
        sa.Column("pham_vi", sa.String(length=32), nullable=False, server_default="ho_so_hdv_cong_khai"),
        sa.Column("cau_hoi", sa.Text(), nullable=False, server_default=""),
        sa.Column("tra_loi", sa.String(length=6), nullable=False),
        sa.Column("hoi_luc", sa.DateTime(), nullable=False),
        sa.Column("nguon", sa.String(length=12), nullable=False, server_default="khao_sat"),
        sa.Column("ma_rut", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("ma_rut_het_han", sa.DateTime(), nullable=True),
        sa.Column("rut_luc", sa.DateTime(), nullable=True),
        sa.Column("rut_ly_do", sa.String(length=500), nullable=False, server_default=""),
        # Viec cua cong ty
        sa.Column("duyet_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("duyet_bang_quyen", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("duyet_ket_qua", sa.String(length=12), nullable=False, server_default=""),
        sa.Column("duyet_ly_do", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("go_boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("go_luc", sa.DateTime(), nullable=True),
        sa.Column("go_ly_do", sa.String(length=1000), nullable=False, server_default=""),
        # MOT nhan xet MOT ban ghi. Hai ban ghi cho mot nhan xet la hai cau tra loi cho mot cau
        # hoi, va luc ay khong ai biet cau nao la y khach.
        sa.UniqueConstraint("danh_gia_id", name="uq_dong_y_cong_khai_danh_gia"),
    )
    op.create_index("ix_dong_y_cong_khai_danh_gia", BANG, ["danh_gia_id"])
    op.create_index("ix_dong_y_cong_khai_care", BANG, ["care_id"])
    op.create_index("ix_dong_y_cong_khai_tour", BANG, ["tour_id"])
    op.create_index("ix_dong_y_cong_khai_pham_vi", BANG, ["pham_vi"])
    op.create_index("ix_dong_y_cong_khai_tra_loi", BANG, ["tra_loi"])
    op.create_index("ix_dong_y_cong_khai_hoi_luc", BANG, ["hoi_luc"])
    # Ba chi muc duoi la ba cau hoi cua man hinh duyet: "cai nao dang cho", "cai nao da dang",
    # "cai nao khach da rut". Khong co chung thi moi lan mo man hinh la mot lan quet ca bang.
    op.create_index("ix_dong_y_cong_khai_ma_rut", BANG, ["ma_rut"])
    op.create_index("ix_dong_y_cong_khai_rut_luc", BANG, ["rut_luc"])
    op.create_index("ix_dong_y_cong_khai_duyet_luc", BANG, ["duyet_luc"])
    op.create_index("ix_dong_y_cong_khai_ket_qua", BANG, ["duyet_ket_qua"])


def downgrade() -> None:
    for ten in ("ket_qua", "duyet_luc", "rut_luc", "ma_rut", "hoi_luc", "tra_loi",
                "pham_vi", "tour", "care", "danh_gia"):
        op.drop_index(f"ix_dong_y_cong_khai_{ten}", table_name=BANG)
    op.drop_table(BANG)
