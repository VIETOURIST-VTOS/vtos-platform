# -*- coding: utf-8 -*-
"""HD-Q2a — bảng đếm lượt mở cửa đọc.

VÌ SAO PHẢI CÓ MỘT BẢNG MỚI thay vì dùng `audit_log` có sẵn: `audit_log` là một CHUỖI BẤT BIẾN,
mỗi bản ghi băm nối vào bản ghi trước. Nhét lượt đọc vào đó nghĩa là mỗi lần ai mở một màn hình,
máy chủ phải đọc bản ghi cuối cùng của cả hệ thống rồi băm — một phép ghi tuần tự đặt ngay trên
đường đi của mọi phép đọc. Chuỗi ấy sinh ra để chứng minh «không ai sửa lén sổ»; lượt đọc màn hình
không thuộc loại ấy, và dồn vào cùng một chuỗi chỉ làm chuỗi dài gấp trăm lần mà không chứng minh
thêm điều gì.

Bảng này gộp sẵn theo NGÀY × NGƯỜI × CỬA nên nó không lớn lên theo số lần bấm: một trăm người mở
năm cửa mỗi ngày là năm trăm dòng một ngày, chứ không phải một dòng mỗi lượt.

Revision ID: q2a3d5f7b9c1e
Revises: dx3b7e2a9c4f61
"""
import sqlalchemy as sa
from alembic import op

revision = "q2a3d5f7b9c1e"
down_revision = "dx3b7e2a9c4f61"   # 16/10: main nhich them DX-3, va DX-3 cung moc
                                   # tren dl3f7a2c9e4b16. Giu nguyen la kho co HAI dau
                                   # mach, va `alembic upgrade head` DUNG -- may chu
                                   # khong len duoc. Noi sau dau that moi.
branch_labels = None
depends_on = None

BANG = "luot_doc_cua"


def upgrade() -> None:
    op.create_table(
        BANG,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ngay", sa.Date(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("cua", sa.String(length=40), nullable=False),
        sa.Column("so_luot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_phut", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phut_cuoi", sa.String(length=5), nullable=False, server_default=""),
        sa.Column("so_dong", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("ngay", "username", "cua", name="uq_luot_doc_cua"),
    )
    op.create_index("ix_luot_doc_cua_ngay", BANG, ["ngay"])
    op.create_index("ix_luot_doc_cua_username", BANG, ["username"])
    op.create_index("ix_luot_doc_cua_role", BANG, ["role"])
    op.create_index("ix_luot_doc_cua_cua", BANG, ["cua"])


def downgrade() -> None:
    op.drop_index("ix_luot_doc_cua_cua", table_name=BANG)
    op.drop_index("ix_luot_doc_cua_role", table_name=BANG)
    op.drop_index("ix_luot_doc_cua_username", table_name=BANG)
    op.drop_index("ix_luot_doc_cua_ngay", table_name=BANG)
    op.drop_table(BANG)
