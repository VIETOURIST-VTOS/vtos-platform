"""VPM-11 – sổ nghĩa vụ thanh toán (mã gốc, chống đếm trùng)

Revision ID: a4e8g3b6d1f29
Revises: v16d8e2b9f4a71

Chỉ THÊM một bảng. Không đụng `payment_requests`, `service_orders`, `fin_schedules`,
`lich_thanh_toan_hd`, `bookings`, `cash_plan_items` – sáu bảng nguồn giữ nguyên vẹn, vì sổ này là lớp
ĐỌC nằm trên chúng chứ không thay thế chúng. Bản vá này gỡ ra được mà không mất dữ liệu nghiệp vụ nào.

RÀNG BUỘC DUY NHẤT (`nguon_bang`, `nguon_id`) LÀ PHẦN QUAN TRỌNG NHẤT CỦA BẢN VÁ. Phép đồng bộ phải
chạy lại được; nếu chỉ dựa vào mã trong Python để chống trùng thì hai lần chạy song song (lịch tự
động V11 và một người bấm tay cùng lúc) vẫn sinh ra hai dòng cho một chứng từ, và bảng dòng tiền nhân
đôi nhu cầu tiền của công ty mà không ai nhìn ra ngay.

`tong_nghia_vu` và `da_tra` nullable KHÔNG default – luật K2: rỗng là chưa ai nhập, không phải 0.
`ty_gia` cũng là TIEN vì nó là số cần chính xác thập phân; `loai_tien` mặc định VND.
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "a4e8g3b6d1f29"
down_revision = "v16d8e2b9f4a71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nghia_vu_thanh_toan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma_goc", sa.String(length=40), nullable=False),
        sa.Column("huong", sa.String(length=4), nullable=False),
        sa.Column("nhom", sa.String(length=24), nullable=False),
        sa.Column("ghi_nho", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("don_vi_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("doi_tuong", sa.String(length=200), nullable=True),
        sa.Column("noi_dung", sa.String(length=300), nullable=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
        sa.Column("tong_nghia_vu", TIEN, nullable=True),
        sa.Column("da_tra", TIEN, nullable=True),
        sa.Column("loai_tien", sa.String(length=3), nullable=False, server_default="VND"),
        sa.Column("ty_gia", TIEN, nullable=True),
        sa.Column("ngay_quy_doi", sa.Date(), nullable=True),
        sa.Column("ngay_cam_ket", sa.Date(), nullable=True),
        sa.Column("ngay_du_kien_tra", sa.Date(), nullable=True),
        sa.Column("trang_thai", sa.String(length=16), nullable=True),
        sa.Column("nguon_bang", sa.String(length=40), nullable=False),
        sa.Column("nguon_id", sa.Integer(), nullable=False),
        sa.Column("nguon_ma", sa.String(length=50), nullable=True),
        sa.Column("nghi_trung_voi", sa.String(length=40), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("boi", sa.String(length=50), nullable=True),
        sa.Column("luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_nghia_vu_thanh_toan_ma_goc", "nghia_vu_thanh_toan", ["ma_goc"], unique=True)
    op.create_index("ux_nghia_vu_nguon", "nghia_vu_thanh_toan", ["nguon_bang", "nguon_id"], unique=True)
    op.create_index("ix_nghia_vu_ngay", "nghia_vu_thanh_toan", ["ngay_cam_ket", "nhom"])
    op.create_index("ix_nghia_vu_pham_vi", "nghia_vu_thanh_toan", ["company_id", "huong"])
    op.create_index("ix_nghia_vu_thanh_toan_nhom", "nghia_vu_thanh_toan", ["nhom"])
    op.create_index("ix_nghia_vu_thanh_toan_trang_thai", "nghia_vu_thanh_toan", ["trang_thai"])
    op.create_index("ix_nghia_vu_thanh_toan_company_id", "nghia_vu_thanh_toan", ["company_id"])
    op.create_index("ix_nghia_vu_thanh_toan_tour_id", "nghia_vu_thanh_toan", ["tour_id"])
    op.create_index("ix_nghia_vu_thanh_toan_ngay_cam_ket", "nghia_vu_thanh_toan", ["ngay_cam_ket"])
    op.create_index("ix_nghia_vu_thanh_toan_nguon_bang", "nghia_vu_thanh_toan", ["nguon_bang"])
    op.create_index("ix_nghia_vu_thanh_toan_nguon_id", "nghia_vu_thanh_toan", ["nguon_id"])


def downgrade() -> None:
    op.drop_table("nghia_vu_thanh_toan")
