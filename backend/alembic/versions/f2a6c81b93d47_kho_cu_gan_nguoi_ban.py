"""Sổ gán người bán và sổ tệp↔chuyến cho kho quyết toán cũ T1–T6/2026

Revision ID: f2a6c81b93d47
Revises: e7b3f19a4c260
Create Date: 2026-09-13

HAI bảng mới, không sửa bảng nào đang có – nên bản này lùi lại được sạch.

    kho_cu_nguoi_ban    một cái tên trong cột SALES của kho cũ ↔ tài khoản VTOS
    kho_cu_tep_chuyen   tệp Excel nào đẻ ra chuyến nào – cầu nối sang bản đối chiếu H1

Vì sao phải là bảng chứ không phải tham số: 145 tên, trong đó 67 tên cần người chọn tay (6 trùng tên,
61 ngoài danh sách nhân sự). Lời giải của người phải được giữ lại để lần nạp sau không phải gán lại –
`params` là sổ chính sách một dòng một con số, không phải chỗ để một bảng ánh xạ 145 dòng.

`khoa_ten` là tên đã bỏ dấu và bỏ khoảng trắng, DUY NHẤT: "HỒNG NGHIỆP" và "Hong Nghiep" phải rơi vào
cùng một dòng, nếu không bảng phình theo lỗi gõ chứ không theo số người.
"""
import sqlalchemy as sa
from alembic import op

revision = "f2a6c81b93d47"
down_revision = "e7b3f19a4c260"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kho_cu_nguoi_ban",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khoa_ten", sa.String(length=120), nullable=False),
        sa.Column("ten_trong_tep", sa.String(length=120), nullable=False),
        # Rỗng CÓ NGHĨA: đã thấy tên này nhưng chưa gán được cho ai. Không mặc định về một tài khoản
        # nào cả – cộng doanh số nhầm cho người khác tệ hơn là để trống.
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cach_khop", sa.String(length=20), nullable=True, server_default=""),
        sa.Column("ung_vien", sa.String(length=400), nullable=True, server_default=""),
        sa.Column("so_dong", sa.Integer(), nullable=True, server_default="0"),
        # `sa.false()`, KHÔNG phải `sa.text("0")`. PostgreSQL từ chối `DEFAULT 0` cho cột BOOLEAN
        # ("column is of type boolean but default expression is of type integer") và cả lệnh
        # `alembic upgrade head` dừng ở đấy — container không khởi động được. SQLite thì nhận, nên
        # bộ thử ở máy (dùng create_all, không chạy migration) không bao giờ thấy.
        sa.Column("da_nghi", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("nguoi_gan", sa.String(length=50), nullable=True, server_default=""),
        sa.Column("gan_luc", sa.DateTime(), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_kho_cu_nguoi_ban_khoa_ten", "kho_cu_nguoi_ban", ["khoa_ten"], unique=True)
    op.create_index("ix_kho_cu_nguoi_ban_user_id", "kho_cu_nguoi_ban", ["user_id"])

    # Tệp nào đẻ ra chuyến nào. Bản đối chiếu H1 – chỗ duy nhất có tổng thu/tổng chi đúng ở mức
    # chuyến – gọi tên chuyến bằng TÊN TỆP: đo trên 624 dòng thì chỉ 10 dòng mang mã tour đúng dạng,
    # 507 dòng chỉ khớp được qua tên tệp. Mã tour lại nằm bên trong tệp Excel, nên cầu nối phải do
    # lúc nạp ghi lại.
    op.create_table(
        "kho_cu_tep_chuyen",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("khoa_tep", sa.String(length=200), nullable=False),
        sa.Column("ten_tep", sa.String(length=255), nullable=False),
        sa.Column("ma_tour", sa.String(length=30), nullable=True, server_default=""),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("tao_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_kho_cu_tep_chuyen_khoa_tep", "kho_cu_tep_chuyen", ["khoa_tep"], unique=True)
    op.create_index("ix_kho_cu_tep_chuyen_tour_id", "kho_cu_tep_chuyen", ["tour_id"])


def downgrade():
    op.drop_index("ix_kho_cu_tep_chuyen_tour_id", table_name="kho_cu_tep_chuyen")
    op.drop_index("ix_kho_cu_tep_chuyen_khoa_tep", table_name="kho_cu_tep_chuyen")
    op.drop_table("kho_cu_tep_chuyen")
    op.drop_index("ix_kho_cu_nguoi_ban_user_id", table_name="kho_cu_nguoi_ban")
    op.drop_index("ix_kho_cu_nguoi_ban_khoa_ten", table_name="kho_cu_nguoi_ban")
    op.drop_table("kho_cu_nguoi_ban")
