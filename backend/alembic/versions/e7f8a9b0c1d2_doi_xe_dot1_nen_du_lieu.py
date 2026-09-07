"""Đội xe Đợt 1: mã xe cố định, lịch sử biển số, giấy tờ có hạn, hàng đợi xác minh

Điểm cần chú ý khi đọc migration này: nó KHÔNG bỏ ràng buộc duy nhất trên `vehicles.plate`. Đặc tả nói biển
số chỉ là thuộc tính có thời gian hiệu lực, và điều đó đúng – nhưng cột `plate` ở đây được giữ với nghĩa hẹp
hơn: "biển ĐANG dùng". Hai chiếc xe đang chạy không thể cùng mang một biển, nên ràng buộc đó vẫn phản ánh
thực tế. Toàn bộ lịch sử biển nằm ở bảng mới `vehicle_plates`, nơi không có ràng buộc duy nhất vì một biển
có thể được cấp lại cho xe khác sau nhiều năm.

Làm như vậy còn tránh một việc nguy hiểm: gỡ ràng buộc duy nhất là thao tác ALTER mà SQLite không hỗ trợ, và
bản dev của dự án chạy SQLite. Giữ lại thì cả Postgres lẫn SQLite đều lên được.

Cuối migration có một bước chép dữ liệu: mỗi xe đang có được ghi một dòng lịch sử biển cho biển hiện tại, và
được gán mã xe XE0001, XE0002… theo id. Không có bước này thì màn hình lịch sử biển của xe cũ sẽ trống trơn
và trông như dữ liệu bị mất.
"""
from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vehicles") as b:
        b.add_column(sa.Column("code", sa.String(20), server_default="", nullable=False))
        b.add_column(sa.Column("vin", sa.String(40), server_default="", nullable=False))
        b.add_column(sa.Column("lifecycle", sa.String(20), server_default="dang_khai_thac", nullable=False))
        b.add_column(sa.Column("op_right", sa.String(20), server_default="so_huu", nullable=False))
        # Cột này KHÔNG kèm khóa ngoại ở tầng migration. Thêm một cột có khóa ngoại vào bảng đã tồn tại là
        # thao tác ALTER ràng buộc, mà SQLite không hỗ trợ – bản dev của dự án chạy SQLite nên nếu để khóa
        # ngoại ở đây thì máy lập trình không lên được, còn máy chủ thì lên được: hai bên chạy hai lược đồ
        # khác nhau, và lỗi chỉ lộ ra lúc triển khai. Quan hệ vẫn được khai báo ở tầng ORM (models/hr.py).
        b.add_column(sa.Column("operator_company_id", sa.Integer, nullable=True))
        b.add_column(sa.Column("partner_name", sa.String(120), server_default="", nullable=False))
        b.add_column(sa.Column("contract_ref", sa.String(60), server_default="", nullable=False))
        b.add_column(sa.Column("contract_from", sa.Date, nullable=True))
        b.add_column(sa.Column("contract_to", sa.Date, nullable=True))
        b.add_column(sa.Column("odo_km", sa.Integer, server_default="0", nullable=False))
        b.add_column(sa.Column("odo_at", sa.Date, nullable=True))
        b.add_column(sa.Column("source_note", sa.String(200), server_default="", nullable=False))

    op.create_table(
        "vehicle_plates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("plate", sa.String(20), nullable=False),
        sa.Column("from_date", sa.Date, nullable=True),
        sa.Column("to_date", sa.Date, nullable=True),
        sa.Column("source", sa.String(120), server_default="", nullable=False),
        sa.Column("verify", sa.String(20), server_default="nguon_ghi", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_vehicle_plates_vehicle", "vehicle_plates", ["vehicle_id"])
    op.create_index("ix_vehicle_plates_plate", "vehicle_plates", ["plate"])

    op.create_table(
        "vehicle_documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("number", sa.String(60), server_default="", nullable=False),
        sa.Column("issued_on", sa.Date, nullable=True),
        sa.Column("expires_on", sa.Date, nullable=True),
        sa.Column("source", sa.String(120), server_default="", nullable=False),
        sa.Column("verify", sa.String(20), server_default="nguon_ghi", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("active", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_vehicle_documents_xe", "vehicle_documents", ["vehicle_id", "kind"])
    op.create_index("ix_vehicle_documents_nguoi", "vehicle_documents", ["employee_id", "kind"])

    op.create_table(
        "fleet_verifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity", sa.String(30), server_default="vehicle", nullable=False),
        sa.Column("ref", sa.String(60), server_default="", nullable=False),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("issue", sa.String(300), nullable=False),
        sa.Column("source", sa.String(200), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="cho_xac_minh", nullable=False),
        sa.Column("resolution", sa.Text, server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("resolved_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_verifications_status", "fleet_verifications", ["status"])

    # --- Chép dữ liệu: xe đang có được cấp mã cố định và một dòng lịch sử biển cho biển hiện tại ---
    cn = op.get_bind()
    for vid, plate, kind in cn.execute(sa.text("SELECT id, plate, kind FROM vehicles ORDER BY id")).fetchall():
        cn.execute(sa.text("UPDATE vehicles SET code = :c, op_right = :r WHERE id = :i"),
                   {"c": f"XE{vid:04d}", "r": "hop_tac" if kind == "hop_tac" else "so_huu", "i": vid})
        cn.execute(sa.text("INSERT INTO vehicle_plates (vehicle_id, plate, source, verify, note) "
                           "VALUES (:v, :p, :s, 'nguon_ghi', :n)"),
                   {"v": vid, "p": plate, "s": "dữ liệu có sẵn trước Đợt 1",
                    "n": "Biển đang dùng khi nạp Đợt 1; ngày bắt đầu chưa biết nên để trống thay vì đoán"})


def downgrade() -> None:
    op.drop_table("fleet_verifications")
    op.drop_table("vehicle_documents")
    op.drop_table("vehicle_plates")
    with op.batch_alter_table("vehicles") as b:
        for c in ("source_note", "odo_at", "odo_km", "contract_to", "contract_from", "contract_ref",
                  "partner_name", "operator_company_id", "op_right", "lifecycle", "vin", "code"):
            b.drop_column(c)
