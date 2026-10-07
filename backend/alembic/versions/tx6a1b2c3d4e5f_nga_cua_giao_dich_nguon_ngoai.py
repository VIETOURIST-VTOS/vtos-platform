"""TX-6 · Ngả của một giao dịch nguồn ngoài: xe / đội / chủ xe / tour / không phải chi phí

Revision ID: tx6a1b2c3d4e5f
Revises: cl2b8e4f1a7d3
"""
from alembic import op
import sqlalchemy as sa

revision = "tx6a1b2c3d4e5f"
down_revision = "cl2b8e4f1a7d3"
branch_labels = None
depends_on = None

# MỘT ĐẦU MẠCH. Bản này nối tiếp `cl2b8e4f1a7d3`, KHÔNG nối `tc105cdg3b8f1a` như bản nháp đầu.
#
# Vì sao phải sửa, ghi lại để lần sau khỏi mắc: viết bản này lúc main còn ở 8e1b280, khi ấy
# `tc105cdg3b8f1a` đúng là đầu mạch. Trong lúc dựng, hai làn khác gộp vào main hai bản nâng cấp bảng
# lương (`lk1a7f3c9e2b4` rồi `cl2b8e4f1a7d3`) và bản thứ nhất CŨNG nối vào `tc105cdg3b8f1a`. Giữ
# nguyên thì mạch có HAI ĐẦU, và `alembic upgrade head` chạy lúc máy chủ khởi động sẽ dừng với lỗi
# "multiple heads" — tức là CHẶN TRIỂN KHAI, đúng kiểu hỏng đã xảy ra ngày 14/9/2026.
#
# Đầu mạch phải đo lại NGAY TRƯỚC KHI ĐẨY, không phải lúc bắt đầu viết: bốn làn cùng đẩy vào một kho
# thì khoảng giữa hai thời điểm ấy đủ để ai đó thêm một bản.
#
# Vì sao có bản này — số đo trên hệ thật ngày 07/10/2026:
#
#   tab "Đối soát nguồn ngoài" của /doi-xe : tổng chi phí      1.121.825.494 đ
#                                            chưa quy về xe    1.121.825.494 đ  (100%, cả 36 dòng)
#   màn hình Lãi lỗ đội xe, kỳ 08/2026     : LỢI NHUẬN              50,3%
#
# Ba tầng chi phí của báo cáo lãi lỗ đọc `fleet_trip_costs`, `fleet_maintenance` và
# `fleet_period_costs`. Nó KHÔNG đọc `fleet_external_txns`. Nên một tỷ hai nằm ngoài sổ, và không
# màn hình nào nói ra — người đọc thấy 50,3% và tin đó là kết quả của đội xe.
#
# Cách sửa KHÔNG phải "tra lại xe cho 36 dòng". Bản khảo sát Vietrip 05/9/2026 ghi bộ trường của
# phiếu đề xuất chi: *tour · nhà cung cấp · hình thức thanh toán · loại tiền · dòng dịch vụ*. Không
# có ô xe, và sẽ không có — phiếu ấy gắn vào TOUR. Hỏi "của xe nào" là hỏi sai câu.
#
# Bốn cột này mở một câu hỏi đúng hơn: khoản này chạy về NGẢ nào. Người đọc chứng từ trả lời, kèm lý
# do và tên người — vì ngả quyết định tiền vào sổ của ai, nên nó phải có dấu vết.
#
# BẢN NÀY CHỈ THÊM CỘT, KHÔNG ĐỤNG MỘT DÒNG DỮ LIỆU NÀO. Mặc định là chuỗi RỖNG = "chưa định tuyến",
# cố ý: 36 dòng đang có không được tự nhận một ngả nào. Đặt sẵn "doi" cho đủ form là đẩy một tỷ hai
# vào chi phí đội xe mà chưa ai đọc chứng từ — sai theo chiều ngược lại và khó phát hiện hơn, vì lúc
# ấy báo cáo trông đã "đầy đủ".
COT = (
    ("nga", sa.String(20), ""),
    ("nga_ly_do", sa.String(300), ""),
    ("nga_boi", sa.String(50), ""),
)


def upgrade() -> None:
    for ten, kieu, mac_dinh in COT:
        op.add_column("fleet_external_txns",
                      sa.Column(ten, kieu, nullable=False, server_default=mac_dinh))
    op.add_column("fleet_external_txns", sa.Column("nga_luc", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Gỡ bốn cột. Lùi bản này là MẤT dấu vết định tuyến — ai chọn ngả nào, vì sao.

    Không có cách giữ lại: thông tin ấy chỉ nằm ở đây. Nên chỉ lùi khi chưa ai định tuyến dòng nào,
    và người lùi phải biết mình đang xoá cái gì."""
    for ten in ("nga_luc", "nga_boi", "nga_ly_do", "nga"):
        op.drop_column("fleet_external_txns", ten)
