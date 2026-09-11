"""params.value – rỗng là một trạng thái hợp lệ, không phải dữ liệu thiếu.

Revises: v15c7f1a8d3e60

VÌ SAO BẢN NÂNG CẤP NÀY TỒN TẠI

Hai tham số `ngay_van_hanh_that` và `ngay_du_lieu_that_vietrip` CỐ Ý để trống: chúng là mốc chuyển
VTOS sang sổ thật, và chúng chờ hai chữ ký. Điền sẵn một ngày vào đó là ký thay Chủ tịch bằng một
dòng mã, nên seed_params tạo chúng với value = ''.

Bộ kiểm độ dài dữ liệu (K11) đọc MÔ HÌNH để biết cột nào "bắt buộc phải có người điền": cột chuỗi
không cho rỗng và KHÔNG khai mặc định. `params.value` trước bản này đúng khuôn ấy, nên K11 báo hai
dòng cố ý để trống là hai dòng dữ liệu thiếu — hai lane nói ngược nhau, và cả hai đều đọc đúng cái
mình được cho đọc. Chỗ sai nằm ở MÔ HÌNH: nó không nói ra rằng rỗng là hợp lệ.

Khai server_default '' là để mô hình nói đúng điều hệ thống đang làm. Không dòng dữ liệu nào đổi
nghĩa; bản này chỉ thêm mặc định ở phía máy chủ cho những lần chèn về sau không kèm cột này.

KHÔNG chuyển cột sang nullable: rỗng và NULL mà cùng tồn tại thì mỗi chỗ đọc lại phải nhớ kiểm hai
kiểu, và chỗ nào quên một kiểu thì hỏng lặng lẽ. Một cách nói "chưa chốt" là đủ.
"""
from alembic import op
import sqlalchemy as sa

revision = "v16d8e2b9f4a71"
down_revision = "v15c7f1a8d3e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite không ALTER được mặc định của cột; bỏ qua ở đó, mô hình vẫn khai default="" nên mọi
    # dòng do ứng dụng chèn đều có giá trị. Máy chủ thật chạy PostgreSQL – chỗ cần là chỗ này.
    if op.get_bind().dialect.name == "sqlite":
        return
    op.execute("UPDATE params SET value = '' WHERE value IS NULL")
    op.alter_column("params", "value", existing_type=sa.String(200),
                    existing_nullable=False, server_default=sa.text("''"))


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    op.alter_column("params", "value", existing_type=sa.String(200),
                    existing_nullable=False, server_default=None)
