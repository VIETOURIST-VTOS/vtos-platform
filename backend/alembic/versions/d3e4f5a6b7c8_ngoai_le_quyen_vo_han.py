"""Ngoại lệ quyền không thời hạn: to_date được để trống

Mặc định vẫn là ngoại lệ CÓ HẠN – quyền có hạn thì tự co lại, quyền vô hạn thì chỉ nở ra. Nhưng có
trường hợp thật không hợp với hạn 90 ngày (kế toán trưởng thuê ngoài theo hợp đồng dịch vụ dài hạn),
nên mở đường vô hạn với hai điều kiện bù: chỉ Chủ tịch cấp được, và ngoại lệ vô hạn luôn nổi lên ở
danh sách rà quyền hằng tháng. Đổi "tự hết hạn" lấy "không bao giờ bị quên".

Revision ID: d3e4f5a6b7c8
Revises: b7c8d9e0f1a2
"""
from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b7c8"
down_revision = "b7c8d9e0f1a2"   # nối sau bản của phiên song song – kho luôn phải có MỘT đầu duy nhất
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_grants") as b:
        b.alter_column("to_date", existing_type=sa.Date(), nullable=True)


def downgrade():
    # Không hạ được an toàn: dòng vô hạn không có ngày để điền lại. Đặt hạn 90 ngày kể từ ngày cấp.
    op.execute("UPDATE user_grants SET to_date = from_date + INTERVAL '90 day' WHERE to_date IS NULL")
    with op.batch_alter_table("user_grants") as b:
        b.alter_column("to_date", existing_type=sa.Date(), nullable=False)
