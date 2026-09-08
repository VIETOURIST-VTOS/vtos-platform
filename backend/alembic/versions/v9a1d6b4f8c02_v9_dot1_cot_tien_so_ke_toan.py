"""V9 đợt 1 – tám cột tiền chạm sổ kế toán: số thực nhị phân → số thập phân

Revision ID: v9a1d6b4f8c02
Revises: gp3c8e5b1d47
Create Date: 2026-09-08

Tám cột, sáu bảng, và cả tám đều nằm đúng chỗ kiểm toán mở ra đầu tiên:

    journal_lines.debit / credit          – dòng bút toán, gốc của mọi con số trên báo cáo
    invoices.pre_tax / vat / total        – hóa đơn đầu ra
    receipts.amount                       – phiếu thu
    bank_transactions.amount              – giao dịch ngân hàng
    payment_requests.amount               – đề nghị chi

Không đổi `invoices.vat_rate`: K1 xếp nó là KHÔNG PHẢI TIỀN (0.08 là tỷ lệ). Đổi nhầm một cột không
phải tiền cũng tốn đúng một lần nâng cấp cơ sở dữ liệu, nên danh sách viết thẳng ra từng cột chứ
không viết thành quy tắc "cột nào tên có 'amount' thì đổi".

────────────────────────────────────────────────────────────────────────────────
ĐIỀU PHẢI ĐỌC TRƯỚC KHI CHẠY TRÊN HỆ THỐNG THẬT
────────────────────────────────────────────────────────────────────────────────

1. LÀM TRÒN. numeric(18,2) giữ hai chữ số thập phân. Giá trị nào đang có chữ số thứ ba trở đi sẽ bị
   làm tròn khi đổi kiểu. Với đồng Việt Nam thì phần đó chỉ sinh ra từ phép chia, nhưng ĐỪNG đoán:
   chạy `python -m app.services.v9_doi_chieu truoc` để đếm trước, và đối chiếu lại sau khi đổi.

2. KHÓA BẢNG. Trên PostgreSQL, ALTER COLUMN TYPE viết lại toàn bộ bảng và giữ khóa ACCESS EXCLUSIVE
   suốt thời gian đó. journal_lines là bảng lớn nhất – chạy trong cửa sổ dừng hệ thống, không chạy
   giữa giờ làm việc.

3. SQLITE KHÔNG ĐỔI KIỂU CỘT ĐƯỢC. Máy lập trình dùng SQLite nên phải đi qua batch_alter_table –
   nó tạo bảng mới, chép dữ liệu, đổi tên. Chậm hơn nhưng cùng một kết quả, và quan trọng hơn: hai
   môi trường chạy CÙNG một bản nâng cấp, không phải hai bản khác nhau.

4. QUAY VỀ ĐƯỢC. downgrade đưa lại Float. Nhưng phần thập phân đã làm tròn ở bước lên thì KHÔNG quay
   lại được – quay về chỉ khôi phục KIỂU, không khôi phục SỐ. Đó là lý do bước 1 phải đếm trước.
"""
from alembic import op
import sqlalchemy as sa

revision = "v9a1d6b4f8c02"
down_revision = "gp3c8e5b1d47"
branch_labels = None
depends_on = None

# Viết thẳng từng cột. Quy tắc thì mọi cột thêm về sau cũng bị đổi mà không ai nhìn thấy chúng.
COT = [
    ("journal_lines", "debit", False),
    ("journal_lines", "credit", False),
    ("invoices", "pre_tax", False),
    ("invoices", "vat", False),
    ("invoices", "total", False),
    ("receipts", "amount", False),
    ("bank_transactions", "amount", False),
    ("payment_requests", "amount", False),
]
TIEN = sa.Numeric(18, 2)


def _doi(kieu_moi) -> None:
    for bang, cot, cho_rong in COT:
        with op.batch_alter_table(bang) as b:
            b.alter_column(cot, type_=kieu_moi, existing_nullable=cho_rong)


def upgrade() -> None:
    _doi(TIEN)


def downgrade() -> None:
    _doi(sa.Float())
