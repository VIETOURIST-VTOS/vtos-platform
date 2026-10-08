"""IR & Pháp chế: van_ban_phap_che, nghia_vu_cong_bo, ban_ghi_cong_bo

Đợt D1. Ba bảng, bắt đầu RỖNG cả ba.

Bản nâng cấp này KHÔNG nạp sẵn một nghĩa vụ công bố nào. Danh mục nghĩa vụ và thời hạn của chúng là
QUY ĐỊNH PHÁP LUẬT; điền chúng từ trí nhớ của lần viết phần mềm thì một hạn sai không hiện ra như
một lỗi phần mềm, nó hiện ra như một lần chậm công bố của một công ty niêm yết. Pháp chế khai từng
nghĩa vụ qua cửa nhập, kèm căn cứ điều khoản — và cửa nhập BẮT BUỘC có căn cứ.

Revision ID: pc5e8b3d1f7a2
Revises: ls4d7e2a9c3b6
"""
from alembic import op
import sqlalchemy as sa

revision = "pc5e8b3d1f7a2"
down_revision = "ls4d7e2a9c3b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "van_ban_phap_che",
        sa.Column("id", sa.Integer, primary_key=True),
        # Id của phiên bản 1 – "căn cước" của văn bản. Mọi phiên bản dùng chung giá trị này.
        sa.Column("goc_id", sa.Integer, nullable=True),
        # `so_ban`, không phải `phien_ban`: trong VTOS tên ấy dành riêng cho khoá ghi một lần
        # (VPM-8). Đây là SỐ BẢN của văn bản – dữ liệu nghiệp vụ, không phải cơ chế khoá.
        sa.Column("so_ban", sa.Integer, server_default="1"),
        sa.Column("loai", sa.String(30), nullable=False),
        sa.Column("so_hieu", sa.String(60), server_default=""),
        sa.Column("tieu_de", sa.String(300), nullable=False),
        sa.Column("tom_tat", sa.Text, server_default=""),
        sa.Column("trang_thai", sa.String(16), server_default="nhap"),
        sa.Column("hieu_luc_tu", sa.Date, nullable=True),
        sa.Column("hieu_luc_den", sa.Date, nullable=True),
        sa.Column("bi_thay_boi", sa.Integer, nullable=True),
        sa.Column("ly_do_sua", sa.Text, server_default=""),
        sa.Column("nguoi_ky", sa.String(80), server_default=""),
        sa.Column("ngay_ky", sa.Date, nullable=True),
        sa.Column("attachment_id", sa.Integer, sa.ForeignKey("attachments.id"), nullable=True),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime),
    )
    op.create_index("ix_van_ban_phap_che_goc", "van_ban_phap_che", ["goc_id", "so_ban"])
    op.create_index("ix_van_ban_phap_che_tt", "van_ban_phap_che", ["trang_thai", "loai"])
    op.create_index("ix_van_ban_phap_che_goc_id", "van_ban_phap_che", ["goc_id"])
    op.create_index("ix_van_ban_phap_che_loai", "van_ban_phap_che", ["loai"])
    op.create_index("ix_van_ban_phap_che_trang_thai", "van_ban_phap_che", ["trang_thai"])

    op.create_table(
        "nghia_vu_cong_bo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ma", sa.String(40), nullable=False),
        sa.Column("ten", sa.String(300), nullable=False),
        sa.Column("can_cu", sa.Text, server_default=""),
        sa.Column("chu_ky", sa.String(16), server_default="su_kien"),
        # RỖNG = hạn KHÔNG tính bằng số ngày. Khác hẳn 0 ngày.
        sa.Column("han_sau_ngay", sa.Integer, nullable=True),
        sa.Column("mo_ta_han", sa.Text, server_default=""),
        sa.Column("dang_ap_dung", sa.Boolean, server_default=sa.true()),
        sa.Column("khai_boi", sa.String(50), server_default=""),
        sa.Column("khai_luc", sa.DateTime),
    )
    op.create_index("ix_nghia_vu_cong_bo_ma", "nghia_vu_cong_bo", ["ma"], unique=True)

    op.create_table(
        "ban_ghi_cong_bo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nghia_vu_id", sa.Integer, sa.ForeignKey("nghia_vu_cong_bo.id"), nullable=False),
        sa.Column("ky", sa.String(30), nullable=False),
        sa.Column("moc_phat_sinh", sa.Date, nullable=True),
        # RỖNG = chưa xác định được hạn, KHÔNG phải "hạn là hôm nay".
        sa.Column("han_chot", sa.Date, nullable=True),
        sa.Column("da_cong_bo_luc", sa.DateTime, nullable=True),
        sa.Column("noi_cong_bo", sa.String(160), server_default=""),
        sa.Column("van_ban_id", sa.Integer, sa.ForeignKey("van_ban_phap_che.id"), nullable=True),
        sa.Column("ghi_chu", sa.Text, server_default=""),
        sa.Column("boi", sa.String(50), server_default=""),
        sa.Column("luc", sa.DateTime),
    )
    op.create_index("ux_ban_ghi_cong_bo_ky", "ban_ghi_cong_bo", ["nghia_vu_id", "ky"], unique=True)
    op.create_index("ix_ban_ghi_cong_bo_nv", "ban_ghi_cong_bo", ["nghia_vu_id"])


def downgrade() -> None:
    op.drop_index("ix_ban_ghi_cong_bo_nv", table_name="ban_ghi_cong_bo")
    op.drop_index("ux_ban_ghi_cong_bo_ky", table_name="ban_ghi_cong_bo")
    op.drop_table("ban_ghi_cong_bo")
    op.drop_index("ix_nghia_vu_cong_bo_ma", table_name="nghia_vu_cong_bo")
    op.drop_table("nghia_vu_cong_bo")
    for ten in ("ix_van_ban_phap_che_trang_thai", "ix_van_ban_phap_che_loai",
                "ix_van_ban_phap_che_goc_id", "ix_van_ban_phap_che_tt", "ix_van_ban_phap_che_goc"):
        op.drop_index(ten, table_name="van_ban_phap_che")
    op.drop_table("van_ban_phap_che")
