"""KS-5 — quyền Agoda đã cấp + môi trường trên `doi_tac_ota`.

Chính sách Agoda Fulfill Assisted: quyền là thứ NGUỒN CẤP, không phải thứ mình bật. Bộ đề xuất
v1.4 nói thẳng: có tài khoản Affiliate KHÔNG mặc nhiên cho quyền gọi API giá, đặt phòng, huỷ hay
dùng ảnh. Trước bản này hệ không có chỗ nào ghi Agoda đã cấp gì.

NẠP SẴN `quyen = 'AFFILIATE'` CHO DÒNG ĐANG BẬT — và đây là chỗ bản di trú này suýt làm hỏng hệ
đang chạy: `thieu_de_bat()` nay đòi quyền AFFILIATE, nên nếu để cột rỗng thì Expedia (đang bật
thật, đã có lượt chuyển 28/10/2026) rơi khỏi bốn điều kiện và BIẾN MẤT khỏi cổng khách ngay khi
di trú chạy. Một dòng đã qua bốn điều kiện và được Chủ tịch bật nghĩa là quyền Affiliate đã có
trên thực tế, nên nạp sẵn là đúng sự thật chứ không phải nới hàng rào.

Cơ sở dữ liệu dựng MỚI không có dòng `bat = true` nào nên không bị ảnh hưởng.

SEARCH / BOOK / CANCEL / CONTENT / POSTBOOK KHÔNG nạp cho ai: chưa nguồn nào cấp.

`moi_truong` mặc định `tat`. Dòng đang bật được đặt thẳng `that` (Chạy thật), vì chúng đang
chuyển khách THẬT qua link Affiliate chứ không phải đang thử — và chúng đã có bằng chứng trong
ô `bang_chung`, đúng thứ mà `sua()` đòi trước khi cho mở Chạy thật.

Revision ID: ks5b3e7d1a9c42
"""
import sqlalchemy as sa
from alembic import op

revision = "ks5b3e7d1a9c42"
down_revision = "ks4a7e2c9d1b53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doi_tac_ota", sa.Column("quyen", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("doi_tac_ota", sa.Column("moi_truong", sa.String(length=8), nullable=False, server_default="tat"))
    # Dòng Chủ tịch đã bật = đã qua bốn điều kiện = quyền Affiliate có trên thực tế.
    op.execute("UPDATE doi_tac_ota SET quyen = 'AFFILIATE', moi_truong = 'that' WHERE bat")   # viết trần cho chạy được cả PostgreSQL lẫn SQLite


def downgrade() -> None:
    op.drop_column("doi_tac_ota", "moi_truong")
    op.drop_column("doi_tac_ota", "quyen")
