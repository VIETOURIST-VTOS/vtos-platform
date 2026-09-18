"""Sổ tài sản thương hiệu — tám cột trên chính bảng TSCĐ, không bảng mới

Revision ID: th5b8e2c7a1d94
Revises: mkt1a9c4e7b2d63
Create Date: 2026-09-18

Chủ tịch chốt 18/9/2026: *"dùng chung"* — sổ tài sản thương hiệu nằm trên bảng `fixed_assets` của
Kế toán chứ không dựng bảng riêng cho Marketing.

TÁM CỘT THÊM VÀO, KHÔNG SỬA CỘT NÀO ĐANG CÓ, KHÔNG ĐỘNG TỚI BẢNG NÀO KHÁC — nên bản này lùi lại
được sạch, và lùi xong chỉ mất chính phần quản trị nhận diện.

VÌ SAO KHÔNG ĐẶT MẶC ĐỊNH CHO 8 CỘT THEO KIỂU "ĐIỀN SẴN CHO ĐỦ"

`th_so` là cột duy nhất NOT NULL, mặc định `false`, vì nó là một câu hỏi có/không và mọi thẻ TSCĐ
đang có đều trả lời "không". Bảy cột còn lại để RỖNG: chúng chỉ có nghĩa khi `th_so` bật, và điền
sẵn một giá trị vào chúng cho toàn bộ thẻ máy móc, xe cộ đang có là đặt ra một câu trả lời cho một
câu hỏi chưa ai hỏi.

CHỖ NÀY TỪNG LÀM HỎNG MỘT LẦN TRIỂN KHAI, ghi lại để không lặp: cột Boolean thêm vào bảng đã có
dòng thì `server_default` phải là `sa.false()`, KHÔNG phải `sa.text("0")` — PostgreSQL từ chối
`DEFAULT 0` cho cột BOOLEAN và cả lệnh `alembic upgrade head` dừng ở đấy. Đã xảy ra thật ngày
14/9/2026.
"""
import sqlalchemy as sa
from alembic import op

revision = "th5b8e2c7a1d94"
down_revision = "mkt1a9c4e7b2d63"
branch_labels = None
depends_on = None

COT_CHU = (
    ("th_loai", 20),
    ("th_phien_ban", 30),
    ("th_trang_thai", 20),
    ("th_noi_su_dung", 200),
)
COT_NGAY = ("th_hieu_luc_tu", "th_hieu_luc_den")
COT_CO = ("th_so", "th_ky_chutich", "th_ky_ptgd_mkt")


def upgrade():
    for ten in COT_CO:
        op.add_column("fixed_assets",
                      sa.Column(ten, sa.Boolean(), nullable=False, server_default=sa.false()))
    for ten, dai in COT_CHU:
        op.add_column("fixed_assets",
                      sa.Column(ten, sa.String(length=dai), nullable=False, server_default=""))
    for ten in COT_NGAY:
        op.add_column("fixed_assets", sa.Column(ten, sa.Date(), nullable=True))
    # Chỉ mục trên đúng cột phân loại: mọi câu hỏi của màn hình Marketing đều bắt đầu bằng
    # "những thẻ thuộc sổ thương hiệu", còn mọi câu hỏi của Kế toán đều lọc nó ra.
    op.create_index("ix_fixed_assets_th_so", "fixed_assets", ["th_so"])


def downgrade():
    op.drop_index("ix_fixed_assets_th_so", table_name="fixed_assets")
    for ten in COT_NGAY:
        op.drop_column("fixed_assets", ten)
    for ten, _ in COT_CHU:
        op.drop_column("fixed_assets", ten)
    for ten in COT_CO:
        op.drop_column("fixed_assets", ten)
