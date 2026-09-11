"""Lớp 3 bước 2: phần THANH TOÁN của dòng chi phí tour.

VÌ SAO CẦN NĂM CỘT NÀY

Rà soát 11/9/2026 đọc lại ba tệp quyết toán thật. Sheet Land_UK và HotelList của tệp UK ghi đủ những
thứ mà VTOS không có chỗ nào để chứa:

    Hình thức thanh toán   Bank transfer · Card · TM (tiền mặt)
    Thẻ / tài khoản đã trả Wise 9078 · Tech 735
    Ngày thanh toán thật   Paid Date – ngày tiền thật sự rời tài khoản
    Hạn thanh toán         Deadline của đối tác
    Loại chứng từ          Invoice · Receipt · Ticket · Agoda/Booking

Trước bản này, tour_cost_lines chỉ có cột `paid` là SỐ TIỀN đã trả. Biết đã trả bao nhiêu nhưng không
biết trả bằng đường nào, từ tài khoản nào, ngày nào. Hệ quả cụ thể, không phải giả định:

  1. Kế toán đối chiếu sao kê thẻ Wise và Techcombank với chi phí tour bằng cách mở tệp Excel gốc.
     Đó là công việc thủ công duy nhất còn lại trong chuỗi, và cũng là chỗ dễ bỏ sót nhất.
  2. Không trả lời được "khoản nào sắp quá hạn trả đối tác" – mà tour nước ngoài đặt phòng qua
     Agoda/Booking thì hạn thanh toán là ràng buộc thật, quá hạn là mất phòng.

Cả năm cột đều NULL được: đây là cửa nhập cho người làm, rỗng nghĩa là CHƯA NHẬP (quy ước K2), không
mặc định thành chuỗi rỗng hay ngày hôm nay.

CỘT TIỀN: KHÔNG THÊM CỘT TIỀN NÀO Ở BẢN NÀY

unit_price / qty / coef đã có sẵn trong tour_cost_lines từ trước – bản này không đụng tới. Việc còn
thiếu nằm ở MẪU (sheet CHI không có ba ô ấy) chứ không nằm ở bảng, nên sửa ở mẫu và bộ nạp.

Revision ID: y2d8e3f0a5b97
Revises: x1c7d2e9f4a86
"""
from alembic import op
import sqlalchemy as sa

revision = "y2d8e3f0a5b97"
down_revision = "x1c7d2e9f4a86"
branch_labels = None
depends_on = None


COT = (
    ("hinh_thuc_tt", sa.String(20)),       # bank / card / tien_mat / bu_tru
    ("tai_khoan_the", sa.String(60)),      # "Wise 9078", "Tech 735" – ghi đúng như người trả ghi
    ("ngay_thanh_toan", sa.Date()),        # ngày tiền RỜI tài khoản, không phải ngày lập chứng từ
    ("han_thanh_toan", sa.Date()),         # deadline của đối tác
    ("loai_chung_tu", sa.String(30)),      # invoice / receipt / ticket / booking_confirm / khong_co
)


# Bốn ô mẫu ĐANG THU mà không có chỗ chứa – nhân viên gõ xong thì mất.
#
# Chủ tịch yêu cầu thêm điện thoại và email vào sheet KHÁCH ngày 11/9; mẫu đã có bốn ô này nhưng
# booking_khach thì không, nên bộ nạp đọc xong rồi bỏ. Sắp nộp dữ liệu thật của sáu tháng, để rơi
# lúc này là mất thẳng chứ không phải bất tiện.
#
# CỐ Ý KHÔNG thêm cột "sale": sale là của PHIẾU ĐẶT (bookings.sales_id), và từ bản nâng cấp này dòng
# khách đã treo đúng phiếu đặt nên tra ra được. Chép sang đây là hai chỗ giữ cùng một sự thật, rồi
# một hôm hai chỗ nói khác nhau và không ai biết tin chỗ nào.
COT_KHACH = (
    ("gioi_tinh", sa.String(10)),
    ("dien_thoai", sa.String(20)),
    ("email", sa.String(120)),
    # CCCD tách khỏi so_ho_chieu: mẫu trong nước thu CCCD, mẫu nước ngoài thu hộ chiếu, và trước bản
    # này số CCCD nằm nhờ trong ô hộ chiếu. Hai loại giấy tờ chung một ô thì không lọc được và cũng
    # không kiểm được độ dài.
    ("cccd", sa.String(20)),
)


def upgrade() -> None:
    with op.batch_alter_table("tour_cost_lines") as b:
        for ten, kieu in COT:
            b.add_column(sa.Column(ten, kieu, nullable=True))
    with op.batch_alter_table("booking_khach") as b:
        for ten, kieu in COT_KHACH:
            b.add_column(sa.Column(ten, kieu, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("booking_khach") as b:
        for ten, _ in COT_KHACH:
            b.drop_column(ten)
    with op.batch_alter_table("tour_cost_lines") as b:
        for ten, _ in COT:
            b.drop_column(ten)
