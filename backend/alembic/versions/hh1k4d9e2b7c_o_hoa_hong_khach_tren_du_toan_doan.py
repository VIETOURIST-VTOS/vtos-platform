"""Ô bắt buộc "hoa hồng khách" trên dự toán đoàn — Chủ tịch quyết 24/9/2026

Revision ID: hh1k4d9e2b7c
Revises: tc83bm6d1a4f9c
Create Date: 2026-09-24

HAI CỘT TRÊN `tours`

`hoa_hong_khach` — chuỗi ba trạng thái: "" chưa trả lời · "co" · "khong".

    KHÔNG DÙNG BOOLEAN. Một cột boolean chỉ có hai giá trị, nên trạng thái "chưa trả lời" phải mượn
    NULL — và một cột boolean có NULL với server_default là đúng chỗ đã chặn deploy ngày 14/9/2026
    (Postgres không nhận "0" cho kiểu boolean, bản di trú chết lúc khởi động hộp chứa chứ không phải
    lúc chạy phép thử). Ba trạng thái thì khai ba giá trị bằng chữ, và chuỗi rỗng là mặc định hợp lệ
    cho mọi hàng đã có.

`hoa_hong_khach_tien` — cột TIỀN, dùng đúng kiểu chung `TIEN` (Numeric 18,2) của V9, không dùng
    Float. Dùng THẲNG tên `TIEN` nhập từ `models/kieu_tien.py`, không viết lại `sa.Numeric(18, 2)`
    và cũng không ghép từ hai hằng số rời: hàng rào V9 (`test_v9_cot_tien`) đọc thư mục versions
    bằng cây cú pháp và chỉ nhận ra cột tiền khi kiểu viết là `TIEN` hoặc `Numeric(18, 2)` với hai
    con số viết thẳng. Ghép từ biến thì bản nâng cấp có thật mà phép thử không thấy — và nó báo
    "mô hình đã đổi mà không có bản nâng cấp", một câu đúng hình thức nhưng chỉ vào sai chỗ.

    NULLABLE, KHÔNG server_default="0". Bản đầu của tệp này khai `nullable=False, server_default="0"`
    và hàng rào K2 (`test_kt12_quyet_dinh_08_09...`) đỏ ngay — đúng việc nó sinh ra để làm. Một cột
    tiền vừa mặc định 0 vừa không cho rỗng thì "chưa nhập" bị ghi thành 0, và cả đợt K2 tồn tại để
    xoá đúng chỗ mù ấy. Ở cột này sự phân biệt còn quan trọng hơn: số tiền CHỈ có nghĩa khi câu
    trả lời là "co"; với "khong" và với chuyến chưa ai trả lời thì không có khoản tiền nào cả.

VÌ SAO KHÔNG SUY NGƯỢC CHO CÁC CHUYẾN CŨ. Mọi chuyến đã có đều nhận "" — chưa trả lời. Đoán rằng
chuyến cũ "không có hoa hồng khách" là viết một câu trả lời vào miệng người chưa từng được hỏi, và
câu ấy sau này đọc y như một câu họ đã khai. Cổng chỉ chặn ở bước CHUYỂN, nên chuyến cũ đã chạy
không việc gì; chuyến cũ còn ở `nhap_kd` thì người phụ trách trả lời một lần rồi đi tiếp.
"""
import sqlalchemy as sa
from alembic import op

from app.models.kieu_tien import TIEN

revision = "hh1k4d9e2b7c"
down_revision = "tc83bm6d1a4f9c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tours", sa.Column("hoa_hong_khach", sa.String(length=10),
                                     nullable=False, server_default=""))
    op.add_column("tours", sa.Column("hoa_hong_khach_tien", TIEN, nullable=True))


def downgrade():
    op.drop_column("tours", "hoa_hong_khach_tien")
    op.drop_column("tours", "hoa_hong_khach")
