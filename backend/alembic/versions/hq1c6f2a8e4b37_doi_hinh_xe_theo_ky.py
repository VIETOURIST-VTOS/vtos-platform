"""HQ-1: ngày vào đội và ngày rời đội của xe — để mẫu số công suất là đội hình TẠI KỲ ẤY.

Đo trên hệ thật 13/10/2026: màn hình lãi lỗ kỳ 2026-01 in "14/12 xe có chạy trong kỳ". Tử lớn hơn
mẫu vì tử đếm theo KỲ còn mẫu đếm theo HÔM NAY. Hai cột này là chỗ duy nhất trả lời được "tháng 1
chiếc ấy còn trong đội không".

Revision ID: hq1c6f2a8e4b37
Revises: sm1b9e3f7d2a48
"""
from alembic import op
import sqlalchemy as sa

revision = "hq1c6f2a8e4b37"
down_revision = "sm1b9e3f7d2a48"
branch_labels = None
depends_on = None


def _co_cot(bang: str, cot: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return cot in {c["name"] for c in insp.get_columns(bang)}


def upgrade() -> None:
    # Hàng rào `_co_cot` giữ nguyên thói quen của mạch này: bản vá chạy lại trên một cơ sở dữ liệu đã
    # có cột (do một lần deploy dở dang) thì đi qua chứ không nổ.
    for c in ("ngay_vao_doi", "ngay_roi_doi"):
        if not _co_cot("vehicles", c):
            op.add_column("vehicles", sa.Column(c, sa.Date(), nullable=True))


def downgrade() -> None:
    for c in ("ngay_roi_doi", "ngay_vao_doi"):
        if _co_cot("vehicles", c):
            op.drop_column("vehicles", c)
