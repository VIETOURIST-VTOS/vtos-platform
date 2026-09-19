"""TC-74: doi tac ban hang, quyen ban cua nhan vien, booking gan doi tac

Revision ID: tc74nb1c2d3e4f
Revises: zn8c3e1f7a4d26
"""
import sqlalchemy as sa
from alembic import op

revision = "tc74nb1c2d3e4f"
down_revision = "zn8c3e1f7a4d26"   # noi SAU ban noi tai khoan Zalo cua R1 (gop vao main 19/9)
branch_labels = None
depends_on = None

# BA THAY DOI, KHONG DONG MOT DONG DU LIEU NAO:
#   1. Bang moi `doi_tac_ban_hang` - rong.
#   2. Cot `users.duoc_ban_hang` - mac dinh FALSE, tuc la khong ai duoc mo them quyen gi.
#      Khoi Kinh doanh KHONG can cot nay: ho ban hang theo vai tro, xem services/nguoi_ban_hang.py.
#   3. Cot `bookings.doi_tac_id` - RONG cho toan bo 16.414 booking dang co.
#
# VI SAO KHONG TU DIEN SAN DOI TAC CHO LO KHO CU. Bon cai ten J TRAVEL, JTV, JTRAVEL, VTOURIST dang
# nam trong ghi chu cua 466 phieu kho cu, va suy nguoc ra doi tac thi lam duoc. Khong lam, vi hai le:
#   - Ranh gioi 09/9/2026: day la NHAP SO LIEU, viec cua nguoi dung. Man hinh /nguoi-ban-hang co cua
#     khai doi tac, man hinh gan ten kho cu co cua gan.
#   - Doc ten trong tep roi tu quyet "day la doi tac" la doan. Anh Tuan xac nhan 19/9 rang bon cai
#     ten ay la doi tac ghep le; ba cai con lai (MAI VIGO, SGS, TICKETBOX) thi chinh anh cung chua
#     chac. Ban alembic khong phai cho de ghi mot phong doan vao co so du lieu.


def upgrade() -> None:
    op.create_table(
        "doi_tac_ban_hang",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(length=32), nullable=False),
        sa.Column("ten", sa.String(length=160), nullable=False),
        sa.Column("loai", sa.String(length=16), nullable=False, server_default="ghep_le"),
        sa.Column("lien_he", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("dien_thoai", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("ma_so_thue", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("hieu_luc_tu", sa.Date(), nullable=False),
        # Rong = con hop tac. Khong dien mot ngay xa tit thay cho trong.
        sa.Column("hieu_luc_den", sa.Date(), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_doi_tac_ban_hang_ma", "doi_tac_ban_hang", ["ma"], unique=True)
    op.create_index("ix_doi_tac_ban_hang_hieu_luc", "doi_tac_ban_hang", ["hieu_luc_tu", "hieu_luc_den"])

    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("duoc_ban_hang", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("bookings") as b:
        b.add_column(sa.Column("doi_tac_id", sa.Integer(), nullable=True))
        b.create_foreign_key("fk_bookings_doi_tac", "doi_tac_ban_hang", ["doi_tac_id"], ["id"])
    op.create_index("ix_bookings_doi_tac_id", "bookings", ["doi_tac_id"])


def downgrade() -> None:
    op.drop_index("ix_bookings_doi_tac_id", table_name="bookings")
    with op.batch_alter_table("bookings") as b:
        b.drop_constraint("fk_bookings_doi_tac", type_="foreignkey")
        b.drop_column("doi_tac_id")
    with op.batch_alter_table("users") as b:
        b.drop_column("duoc_ban_hang")
    op.drop_index("ix_doi_tac_ban_hang_hieu_luc", table_name="doi_tac_ban_hang")
    op.drop_index("ix_doi_tac_ban_hang_ma", table_name="doi_tac_ban_hang")
    op.drop_table("doi_tac_ban_hang")
