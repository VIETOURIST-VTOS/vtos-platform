"""KS-63 · phiếu đề xuất chi đội xe — bảy bước, có tuyến duyệt, có phiên bản

Revision ID: dx4a7e2b9c6f18
Revises: p103a7c2e9d4b6f1
Create Date: 2026-11-09

Nối sau `p103a7c2e9d4b6f1` (P1-03 gói nhà hàng), KHÔNG nối sau `mn3b7d9f1a2c4e57`. Bản này soạn
lúc `mn3b7d9f1a2c4e57` còn là đầu mạch; trong lúc soạn thì PR #767 gộp vào main và mang theo
`p103a7c2e9d4b6f1` cũng nối vào đúng gốc ấy. Nối cả hai vào một gốc là HAI ĐẦU, và alembic từ
chối chạy khi có hơn một đầu — Dockerfile chạy `alembic upgrade head` lúc container khởi động, nên
hai đầu nghĩa là container không lên và API sập ở lần deploy tới.

`tests/test_mach_migration.py` bắt được chỗ này khi chạy lại bộ vá trên main mới. Đúng cái việc
tệp phép thử ấy ghi là đã xảy ra BA lần trong một buổi ngày 07/9/2026, vì hai phiên làm việc song
song cùng viết migration mới trên cùng một gốc và người viết sau không thấy bản của người trước.

Bản vẽ v3.3 §3 (anh Tuấn gửi 09/11/2026). Trước bản này cửa `POST /fleet/de-xuat-chi` chỉ ghi một
dòng `fleet_external_txns` để ĐỐI CHIẾU, không phải một phiếu có người kiểm và người duyệt.

HAI BẢNG MỚI, KHÔNG ĐỤNG BẢNG NÀO ĐANG CÓ. Cửa cũ giữ nguyên: nó vẫn là cửa nhập bản trích từ
Vietrip, và tắt nó trong cùng một bản là bỏ mất đường đối chiếu đang dùng hằng ngày.

ĐÁNG CHÚ Ý — `fleet_de_xuat` KHÔNG CÓ CỘT `so_tai_khoan` VÀ KHÔNG CÓ CỘT `ngan_hang`. v3.3 §2/§7:
GĐ đội xe không nhập hay thay tài khoản ngân hàng ở màn đề nghị. Bên nhận là khóa `supplier_id`;
số tài khoản đọc từ `suppliers` lúc Kế toán thanh toán, và đổi tài khoản đi qua cửa riêng đã có
nhật ký (`supplier_bank_changes`). Cột không tồn tại thì không có cửa nào ghi vào nó được.
"""
import sqlalchemy as sa
from alembic import op

revision = "dx4a7e2b9c6f18"
down_revision = "p103a7c2e9d4b6f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fleet_de_xuat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column("pham_vi", sa.String(length=10), nullable=False, server_default="xe"),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("loai", sa.String(length=20), nullable=False, server_default="thanh_toan"),
        sa.Column("nhom", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("ben_nhan_de_nghi", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("so_tien", sa.Numeric(18, 2), nullable=True),
        sa.Column("ngay_can", sa.Date(), nullable=True),
        sa.Column("can_cu_thue", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("so_tien_da_tt", sa.Numeric(18, 2), nullable=True),
        sa.Column("so_chung_tu", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("hen_bo_sung", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ly_do_bo_sung", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("trip_cost_id", sa.Integer(), sa.ForeignKey("fleet_trip_costs.id"), nullable=True),
        sa.Column("ma_khoan_goc", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("buoc_nhap", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trang_thai", sa.String(length=20), nullable=False, server_default="nhap"),
        sa.Column("nguoi_lap", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nguoi_kiem_tra", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nguoi_duyet", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nguoi_thanh_toan", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nguoi_doi_soat", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ngay_lap", sa.Date(), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
        sa.Column("sua_luc", sa.DateTime(), nullable=True),
    )
    # Tên chỉ mục ở đây PHẢI trùng tên `create_all` đặt ra từ mô hình: bộ phép thử dựng bảng bằng
    # `create_all` còn bản chạy thật dựng bằng alembic, nên hai bên đặt tên khác nhau là hai lược
    # đồ khác nhau mà không phép thử nào nhìn thấy.
    op.create_index("ix_fleet_de_xuat_ma_phieu", "fleet_de_xuat", ["ma_phieu"], unique=True)
    op.create_index("ix_fleet_de_xuat_tt_ngay", "fleet_de_xuat", ["trang_thai", "ngay_can"])
    op.create_index("ix_fleet_de_xuat_nguoi_lap", "fleet_de_xuat", ["nguoi_lap", "trang_thai"])
    op.create_index("ix_fleet_de_xuat_khoan_goc", "fleet_de_xuat", ["ma_khoan_goc"])
    op.create_index("ix_fleet_de_xuat_ngay_lap", "fleet_de_xuat", ["ngay_lap"])

    op.create_table(
        "fleet_de_xuat_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("de_xuat_id", sa.Integer(), sa.ForeignKey("fleet_de_xuat.id"), nullable=False),
        sa.Column("hanh_dong", sa.String(length=20), nullable=False),
        sa.Column("tu_trang_thai", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("den_trang_thai", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("phien_ban_truoc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("noi_dung_truoc", sa.Text(), nullable=False, server_default=""),
        sa.Column("boi", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("vai", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fleet_de_xuat_log_phieu", "fleet_de_xuat_log", ["de_xuat_id", "luc"])
    op.create_index("ix_fleet_de_xuat_log_de_xuat_id", "fleet_de_xuat_log", ["de_xuat_id"])
    op.create_index("ix_fleet_de_xuat_log_luc", "fleet_de_xuat_log", ["luc"])


def downgrade():
    op.drop_table("fleet_de_xuat_log")
    op.drop_table("fleet_de_xuat")
