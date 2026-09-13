"""Đ-7 – thu hộ chi hộ: chủ tiền và hạn xử lý.

Revises: a1e4d7c2f8b93

BỐN CỘT, HAI BẢNG, VÀ MỘT CỜ CHẾT ĐƯỢC HỒI SINH

Cột `tour_hdv_chi.thu_ho_khach` đã có từ trước và đúng về ý: nó đánh dấu khoản tiền của KHÁCH mà
trưởng đoàn đang cầm — mẫu UK ghi "TL thu của khách 126 GBP (mua dùm khách vé tham quan)". Nhưng
không chỗ nào trong hệ thống cộng trừ nó vào bản chốt. Hệ thống biết khoản này là tiền của khách,
mà vẫn không trả lời được câu hỏi duy nhất đáng hỏi: **giờ ai đang cầm bao nhiêu tiền của ai.**

Bốn cột này biến cờ ấy thành một số dư thật:

    tour_doanh_thu_dong.chu_tien   / .han_xu_ly     – vế THU HỘ
    tour_hdv_chi.chu_tien          / .han_xu_ly     – vế CHI HỘ

CHỦ TIỀN ĐỂ RỖNG LÀ MỘT TRẠNG THÁI CÓ NGHĨA, không phải dữ liệu thiếu: nó nghĩa là CHƯA AI XÁC
ĐỊNH. Và đó là chỗ DUY NHẤT Đ-7 chặn đóng số — một khoản tiền của người khác nằm trong két công ty
mà không ai biết của ai thì không trả lại được cho ai. Rỗng KHÔNG được đọc thành "của công ty";
đọc như vậy là biến tiền của khách thành doanh thu mà không ai bấm nút nào.

HẠN XỬ LÝ để rỗng nghĩa là chưa đặt hạn. Số dư giữ hộ không có hạn thì nằm đó mãi và không bao giờ
thành việc của ai — nên bộ soát nói ra, ở mức cảnh báo.

VÌ SAO KHÔNG DỰNG BẢNG RIÊNG cho tiền giữ hộ: tiền thu hộ đi vào cùng cửa với tiền thu thật (người
nhập gõ một dòng), tiền chi hộ đi vào cùng cửa với chi HDV. Tách sang bảng thứ ba là bắt người dùng
nhớ hai nơi cho cùng một thao tác, và bắt mọi phép cộng phải đi ghép thêm một bảng nữa. Hai cột trên
đúng bảng đang dùng thì rẻ hơn và không quên được.

CHA LÀ `a1e4d7c2f8b93` (DT-2) — đo đầu mạch NGAY TRƯỚC KHI ghi tệp này, không phải lúc bắt đầu viết.
Mạch nâng cấp đã có HAI ĐẦU hai lần trong ngày 11/9, cả hai lần đều vì hai làn nối bản của mình vào
cùng một cha mà không biết. Nếu thứ tự gộp đổi thì sửa đúng dòng `down_revision` dưới đây, và CHỈ
dòng ấy.

KHÔNG có dữ liệu nào phải chuyển: bốn cột đều nullable và mặc định rỗng. Dòng cũ giữ nguyên nghĩa —
chưa ai xác định chủ tiền, đúng như sự thật.
"""
from alembic import op
import sqlalchemy as sa

revision = "c1f5a8d3e7b62"
down_revision = "a1e4d7c2f8b93"
branch_labels = None
depends_on = None


BANG = ("tour_doanh_thu_dong", "tour_hdv_chi")


def upgrade() -> None:
    for b in BANG:
        op.add_column(b, sa.Column("chu_tien", sa.String(length=200), nullable=True))
        op.add_column(b, sa.Column("han_xu_ly", sa.Date(), nullable=True))


def downgrade() -> None:
    for b in BANG:
        op.drop_column(b, "han_xu_ly")
        op.drop_column(b, "chu_tien")
