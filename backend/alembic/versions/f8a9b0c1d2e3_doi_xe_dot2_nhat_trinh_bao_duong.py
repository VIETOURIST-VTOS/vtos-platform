"""Đội xe Đợt 2: nhật trình chuyến, chi phí có bên chịu, bảo dưỡng, giao dịch nguồn ngoài

Điểm đáng chú ý: `fleet_external_txns` KHÔNG đặt ràng buộc duy nhất trên `ma_gd` ở tầng cơ sở dữ liệu, mà
khử trùng ở tầng nghiệp vụ và ghi bản lặp lại với cờ `trung`. Lý do là đặc tả yêu cầu đúng như vậy: "Bản ghi
trùng phải được giữ lại trong bảng thô để đối chiếu, chỉ loại ở tầng tính." Đặt duy nhất ở cơ sở dữ liệu thì
lần nhập thứ hai sẽ báo lỗi và không còn dấu vết mình đã loại cái gì – mà đây là dữ liệu dùng để chi tiền cho
đối tác, nên phải chứng minh được. Bù lại có chỉ mục (source, ma_gd) để tra nhanh.
"""
from alembic import op
import sqlalchemy as sa

# Nối SAU 27eb4f9b2c06 (đầu vào bảng lương) chứ không song song với nó. Hai migration cùng nhận
# e7f8a9b0c1d2 làm cha thì Alembic có HAI đầu, và "upgrade head" hỏng ở mọi lần triển khai. Bản kia đã
# đẩy lên rồi nên bản này nhường, nối vào sau – hai bản không đụng bảng nào của nhau nên thứ tự tùy ý.
revision = "f8a9b0c1d2e3"
down_revision = "27eb4f9b2c06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as b:
        b.add_column(sa.Column("fuel_card_last4", sa.String(8), server_default="", nullable=False))

    op.create_table(
        "fleet_trips",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", sa.Integer, nullable=True),
        sa.Column("dispatch_id", sa.Integer, nullable=True),
        sa.Column("tour_id", sa.Integer, nullable=True),
        sa.Column("ten_tour", sa.String(160), server_default="", nullable=False),
        sa.Column("ngay_di", sa.Date, nullable=False),
        sa.Column("ngay_ve", sa.Date, nullable=False),
        # Km để NULL nghĩa là chưa đo. Không dùng 0 làm "chưa có" – đó là cách chắc chắn nhất để một ngày
        # nào đó báo cáo hiện xe chạy âm mấy trăm nghìn km.
        sa.Column("km_dau", sa.Integer, nullable=True),
        sa.Column("km_cuoi", sa.Integer, nullable=True),
        sa.Column("km_gps", sa.Integer, nullable=True),
        sa.Column("km_nguon", sa.String(40), server_default="", nullable=False),
        sa.Column("doanh_thu", sa.Float, server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="cho_xac_nhan", nullable=False),
        sa.Column("co", sa.String(10), server_default="vang", nullable=False),
        sa.Column("co_ly_do", sa.Text, server_default="", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
        sa.Column("confirmed_at", sa.DateTime, nullable=True),
        sa.Column("confirmed_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_trips_xe_ngay", "fleet_trips", ["vehicle_id", "ngay_di"])

    op.create_table(
        "fleet_trip_costs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("trip_id", sa.Integer, sa.ForeignKey("fleet_trips.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float, server_default="0", nullable=False),
        # Ai chịu khoản này là một CỘT, không suy ra từ loại chi phí lúc quyết toán.
        sa.Column("ben_chiu", sa.String(24), server_default="vietourist_tam_ung", nullable=False),
        sa.Column("lit", sa.Float, server_default="0", nullable=False),
        sa.Column("chung_tu", sa.String(200), server_default="", nullable=False),
        sa.Column("nguon", sa.String(40), server_default="nhap_tay", nullable=False),
        sa.Column("ref_id", sa.Integer, nullable=True),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_trip_costs_trip", "fleet_trip_costs", ["trip_id"])

    op.create_table(
        "fleet_maintenance",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("ngay", sa.Date, nullable=False),
        sa.Column("kind", sa.String(20), server_default="dinh_ky", nullable=False),
        sa.Column("km_luc_lam", sa.Integer, nullable=True),
        sa.Column("km_ky_toi", sa.Integer, nullable=True),
        sa.Column("noi_dung", sa.String(300), server_default="", nullable=False),
        sa.Column("garage", sa.String(120), server_default="", nullable=False),
        sa.Column("so_tien", sa.Float, server_default="0", nullable=False),
        sa.Column("ben_chiu", sa.String(24), server_default="chu_xe", nullable=False),
        sa.Column("chung_tu", sa.String(200), server_default="", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_maintenance_xe", "fleet_maintenance", ["vehicle_id", "ngay"])

    op.create_table(
        "fleet_external_txns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("ma_gd", sa.String(120), nullable=False),
        sa.Column("tai_khoan", sa.String(40), server_default="", nullable=False),
        sa.Column("the_4so", sa.String(8), server_default="", nullable=False),
        sa.Column("bien_so", sa.String(20), server_default="", nullable=False),
        sa.Column("vehicle_id", sa.Integer, nullable=True),
        sa.Column("trip_id", sa.Integer, nullable=True),
        sa.Column("thoi_diem", sa.DateTime, nullable=False),
        sa.Column("so_tien", sa.Float, server_default="0", nullable=False),
        sa.Column("lit", sa.Float, server_default="0", nullable=False),
        sa.Column("mo_ta", sa.String(300), server_default="", nullable=False),
        sa.Column("trung", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("trung_cua_id", sa.Integer, nullable=True),
        sa.Column("khop", sa.String(20), server_default="chua_khop", nullable=False),
        sa.Column("co", sa.String(10), server_default="vang", nullable=False),
        sa.Column("ghi_chu", sa.String(300), server_default="", nullable=False),
        sa.Column("imported_at", sa.DateTime, nullable=True),
        sa.Column("imported_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_ext_nguon_ma", "fleet_external_txns", ["source", "ma_gd"])
    op.create_index("ix_fleet_ext_xe_luc", "fleet_external_txns", ["vehicle_id", "thoi_diem"])


def downgrade() -> None:
    op.drop_table("fleet_external_txns")
    op.drop_table("fleet_maintenance")
    op.drop_table("fleet_trip_costs")
    op.drop_table("fleet_trips")
    with op.batch_alter_table("employees") as b:
        b.drop_column("fuel_card_last4")
