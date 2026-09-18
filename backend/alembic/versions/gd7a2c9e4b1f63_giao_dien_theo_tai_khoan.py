"""Giao diện riêng theo tài khoản – nền và cỡ chữ mỗi người tự chọn

Revision ID: gd7a2c9e4b1f63
Revises: tg9c4e1a7b52d8
Create Date: 2026-09-18

HAI cột thêm vào bảng `users`, KHÔNG sửa cột nào đang có, KHÔNG động tới bảng nào khác – nên bản
này lùi lại được sạch, và lùi xong không mất dữ liệu nào ngoài chính lựa chọn giao diện.

Anh Tuấn giao 18/9/2026, mục 3 của năm mục: *"Lưu lựa chọn riêng theo tài khoản nhân viên, giữ
nguyên khi chuyển trang và đăng nhập lại."*

VÌ SAO PHẢI LÀ CỘT TRONG CƠ SỞ DỮ LIỆU, KHÔNG PHẢI localStorage

localStorage đi theo MÁY, không đi theo NGƯỜI. Chỉnh trên máy tính rồi mở điện thoại là về mặc
định; xoá bộ nhớ trình duyệt là mất; hai người dùng chung một máy thì đè lên nhau. Chữ "đăng nhập
lại" trong câu anh Tuấn viết chỉ có một cách làm đúng, và nó nằm ở đây.

Trình duyệt VẪN giữ một bản chép, nhưng chỉ để vẽ ngay khi mở trang – không có bản chép ấy thì mỗi
lần đổi trang màn hình hiện nền mặc định một nhịp rồi mới nháy sang nền của người dùng. Bản CẤT là
hai cột này; bản chép là thứ vứt đi lúc nào cũng được.

HAI CỘT CHỨ KHÔNG MỘT CỘT "sang/18"

Hai câu trả lời khác nhau thì kiểm từng cái một, và đếm được riêng ("bao nhiêu người đang để nền
sáng", "ai đang để cỡ 20"). Gộp vào một chuỗi là sớm muộn có người ghi vào đó một dạng thứ ba mà
không cửa nào chặn.

RỖNG KHÁC MẶC ĐỊNH – ĐÂY LÀ ĐIỀU QUAN TRỌNG NHẤT CỦA BẢN NÀY

`gd_nen` để `""` và `gd_co_chu` để NULL, KHÔNG điền sẵn "toi" và 16 cho 103 tài khoản đang có.

    ""   = người này CHƯA CHỌN GÌ
    toi  = người này ĐÃ CHỌN nền tối

Hai điều ấy trông giống nhau trên màn hình (cả hai đều ra nền tối) và khác hẳn nhau vào đúng cái
ngày ai đó đổi mặc định của hệ thống: người chưa chọn phải đi theo mặc định mới, người đã chọn thì
không. Điền sẵn giá trị mặc định vào cột là xoá mất sự khác biệt ấy ngay từ phút chạy bản chuyển
đổi, và không cách nào lấy lại – vì không ai còn phân biệt được người nào từng bấm.

Đây là đúng quy ước "rỗng khác không" mà lược đồ VTOS dùng ở `users.company_id`, `tours`,
`bookings`, `vehicles`.

GHI CHÚ KỸ THUẬT

`gd_nen` có `server_default=""` vì cột NOT NULL thêm vào bảng đã có dòng thì PostgreSQL cần biết
điền gì vào 103 dòng cũ. `gd_co_chu` thì nullable nên không cần.

KHÔNG có cột boolean nào trong bản này. Nếu về sau thêm, nhớ `sa.false()` chứ KHÔNG phải
`sa.text("0")` – PostgreSQL từ chối `DEFAULT 0` cho cột BOOLEAN và cả lệnh `alembic upgrade head`
dừng ở đấy. Đã xảy ra thật ngày 14/9/2026.
"""
import sqlalchemy as sa
from alembic import op

revision = "gd7a2c9e4b1f63"
down_revision = "tg9c4e1a7b52d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("gd_nen", sa.String(length=8),
                                     nullable=False, server_default=""))
    op.add_column("users", sa.Column("gd_co_chu", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("users", "gd_co_chu")
    op.drop_column("users", "gd_nen")
