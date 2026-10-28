"""KS-4 — đặt lại bộ đếm id của `phap_nhan_hop_dong` (gieo bằng id gán tay nên bộ đếm tụt).

`ks1b4d6f8a2c37_khach_san_ota.py` gieo một dòng bằng id GÁN TAY:

    op.bulk_insert(pn, [{"id": 1, "ma": "INFINIS_CA", ...}])

PostgreSQL không đẩy bộ đếm của bảng theo một lượt gieo như thế. Đo được 29/10/2026 00:25, khi
Chủ tịch thêm pháp nhân Vietourist Holdings qua cửa `POST /api/v1/khach-san-ota/phap-nhan`:

    sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation)
    duplicate key value violates unique constraint "phap_nhan_hop_dong_pkey"

Lần ghi ấy xin id = 1, đụng dòng đã gieo, ngã 500. Cú ngã đẩy bộ đếm lên một nên lần thứ hai vào
được — tức trên hệ đang chạy nó đã tự lành. Bản vá này là cho mọi cơ sở dữ liệu dựng MỚI từ bộ
di trú (máy thử, bản sao để kiểm thử, hoặc khi phải khôi phục), nơi cái bẫy còn nguyên.

Năm dòng OTA trong cùng bản di trú ấy gieo KHÔNG gán id (số thứ ba là `thu_tu`), nên
`doi_tac_ota` không dính — đã đọc mã xác nhận, không suy từ việc thấy id 1–5.

Khuôn chép từ `8a1c2f3d4e5f_fix_vt_id_sequence.py`: cùng cách, cùng chỗ bảo vệ dialect.

Revision ID: ks4a7e2c9d1b53
"""
from alembic import op

revision = "ks4a7e2c9d1b53"
down_revision = "at1d6f8b0c3e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # `pg_get_serial_sequence` trả NULL nếu cột không có bộ đếm; `setval(NULL, ...)` trả NULL chứ
    # không ném lỗi — nên bản vá này an toàn cả khi bảng được dựng kiểu khác.
    op.execute(
        "SELECT setval(pg_get_serial_sequence('phap_nhan_hop_dong', 'id'), "
        "COALESCE((SELECT MAX(id) FROM phap_nhan_hop_dong), 0) + 1, false)"
    )


def downgrade() -> None:
    # Không lùi: đẩy bộ đếm lùi lại là tự dựng lại đúng cái bẫy vừa gỡ.
    pass
