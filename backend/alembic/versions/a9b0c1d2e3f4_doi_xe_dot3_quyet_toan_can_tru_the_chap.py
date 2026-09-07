"""Đội xe Đợt 3: chủ xe hợp tác, công nợ, lịch cấn trừ, tài sản thế chấp, quyết toán kỳ

Hai chỗ trong migration này là thiết kế có chủ đích chứ không phải mặc định:

1. `fleet_offset_applications.idem_key` DUY NHẤT ở tầng cơ sở dữ liệu. Đây là chốt chặn cuối cùng chống trừ
   hai lần cùng một khoản của đối tác. Kiểm ở tầng nghiệp vụ là đủ trong luồng bình thường, nhưng hai tiến
   trình chạy song song (người bấm dựng lại kỳ trong lúc tác vụ tự động đang chạy) thì chỉ ràng buộc ở cơ sở
   dữ liệu mới giữ được.

2. Lịch cấn trừ tách làm HAI bảng, không nhét vào một ô JSON. Đặc tả yêu cầu đúng như vậy: mỗi kỳ có trạng
   thái áp dụng riêng và phải truy được về chứng từ đã duyệt – một ô JSON thì không truy vấn được "kỳ nào
   chưa áp dụng", cũng không khóa được từng dòng.
"""
from alembic import op
import sqlalchemy as sa

revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_partners",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ho_ten", sa.String(160), nullable=False),
        sa.Column("tax_code", sa.String(20), server_default="", nullable=False),
        sa.Column("phone", sa.String(30), server_default="", nullable=False),
        sa.Column("company_id", sa.Integer, nullable=True),
        sa.Column("xac_minh", sa.String(20), server_default="nguon_ghi", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("active", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    with op.batch_alter_table("vehicles") as b:
        # Không kèm khóa ngoại, cùng lý do như operator_company_id ở Đợt 1: thêm cột có khóa ngoại vào bảng
        # đã tồn tại là ALTER ràng buộc mà SQLite không hỗ trợ, và để vậy thì máy lập trình chạy một lược đồ
        # còn máy chủ chạy lược đồ khác. Quan hệ khai báo ở tầng ORM.
        b.add_column(sa.Column("partner_id", sa.Integer, nullable=True))

    op.create_table(
        "fleet_sale_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("partner_id", sa.Integer, nullable=True),
        sa.Column("seller_company_id", sa.Integer, nullable=True),
        sa.Column("ngay_ky", sa.Date, nullable=True),
        sa.Column("gia_ban", sa.Float, server_default="0", nullable=False),
        sa.Column("da_thu", sa.Float, server_default="0", nullable=False),
        # Năm trục tách rời: chúng đi không cùng nhịp, và ca "đã bàn giao mà chưa giải chấp" chính là ca mà
        # chặn cứng B7 tồn tại để ngăn.
        sa.Column("stage", sa.String(20), server_default="hop_dong", nullable=False),
        sa.Column("da_ban_giao", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("da_giai_chap", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("van_ban_giai_chap", sa.String(200), server_default="", nullable=False),
        sa.Column("da_sang_ten", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("quyen_khai_thac_tiep", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("nguon", sa.String(200), server_default="", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )

    op.create_table(
        "fleet_collaterals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("contract_id", sa.Integer, sa.ForeignKey("fin_contracts.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("tu_ngay", sa.Date, nullable=True),
        sa.Column("den_ngay", sa.Date, nullable=True),
        sa.Column("van_ban_giai_chap", sa.String(200), server_default="", nullable=False),
        sa.Column("phuong_an_rut_tai_san", sa.String(300), server_default="", nullable=False),
        sa.Column("duyet_boi", sa.String(50), server_default="", nullable=False),
        sa.Column("nguon", sa.String(200), server_default="", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_fleet_collaterals_xe", "fleet_collaterals", ["vehicle_id", "den_ngay"])
    op.create_index("ix_fleet_collaterals_ke_uoc", "fleet_collaterals", ["contract_id", "den_ngay"])

    op.create_table(
        "fleet_repayment_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("partner_id", sa.Integer, sa.ForeignKey("fleet_partners.id"), nullable=False),
        sa.Column("sale_case_id", sa.Integer, nullable=True),
        sa.Column("creditor_company_id", sa.Integer, nullable=True),
        sa.Column("ten", sa.String(200), server_default="", nullable=False),
        sa.Column("principal", sa.Float, server_default="0", nullable=False),
        sa.Column("so_ky", sa.Integer, server_default="0", nullable=False),
        sa.Column("moi_ky", sa.Float, server_default="0", nullable=False),
        sa.Column("bat_dau", sa.Date, nullable=True),
        sa.Column("status", sa.String(24), server_default="nhap_chua_xac_nhan", nullable=False),
        sa.Column("can_tru_tu_dong", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("nguon", sa.String(200), server_default="", nullable=False),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )

    op.create_table(
        "fleet_repayment_installments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("fleet_repayment_plans.id"), nullable=False),
        sa.Column("ky", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("amount_due", sa.Float, server_default="0", nullable=False),
        sa.Column("amount_applied", sa.Float, server_default="0", nullable=False),
        sa.Column("note", sa.String(200), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_installments_plan", "fleet_repayment_installments", ["plan_id", "ky"])

    op.create_table(
        "fleet_settlements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ky", sa.String(7), nullable=False),
        sa.Column("partner_id", sa.Integer, sa.ForeignKey("fleet_partners.id"), nullable=False),
        sa.Column("company_id", sa.Integer, nullable=True),
        sa.Column("status", sa.String(24), server_default="nhap", nullable=False),
        sa.Column("co", sa.String(10), server_default="vang", nullable=False),
        sa.Column("doanh_thu", sa.Float, server_default="0", nullable=False),
        sa.Column("doi_tac_huong", sa.Float, server_default="0", nullable=False),
        sa.Column("doi_tac_chiu", sa.Float, server_default="0", nullable=False),
        sa.Column("dieu_chinh", sa.Float, server_default="0", nullable=False),
        sa.Column("truoc_can_tru", sa.Float, server_default="0", nullable=False),
        sa.Column("can_tru", sa.Float, server_default="0", nullable=False),
        sa.Column("sau_can_tru", sa.Float, server_default="0", nullable=False),
        # Số âm ghi vào đây (phải thu, chuyển kỳ sau) chứ KHÔNG thành phiếu chi mang dấu trừ.
        sa.Column("chuyen_ky_sau", sa.Float, server_default="0", nullable=False),
        sa.Column("ghi_chu", sa.Text, server_default="", nullable=False),
        sa.Column("closed_at", sa.DateTime, nullable=True),
        sa.Column("closed_by", sa.String(50), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_settlements_ky", "fleet_settlements", ["ky", "partner_id"])

    op.create_table(
        "fleet_settlement_lines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("settlement_id", sa.Integer, sa.ForeignKey("fleet_settlements.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("vehicle_id", sa.Integer, nullable=True),
        sa.Column("trip_id", sa.Integer, nullable=True),
        sa.Column("mo_ta", sa.String(300), server_default="", nullable=False),
        sa.Column("amount", sa.Float, server_default="0", nullable=False),
        sa.Column("ben_chiu", sa.String(24), server_default="", nullable=False),
        sa.Column("chung_tu", sa.String(200), server_default="", nullable=False),
        sa.Column("duyet_boi", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_settlement_lines_ky", "fleet_settlement_lines", ["settlement_id", "kind"])

    op.create_table(
        "fleet_offset_applications",
        sa.Column("id", sa.Integer, primary_key=True),
        # DUY NHẤT: chốt chặn cuối cùng chống trừ hai lần cùng một khoản của đối tác, kể cả khi hai tiến trình
        # chạy song song.
        sa.Column("idem_key", sa.String(160), nullable=False, unique=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("fleet_repayment_plans.id"), nullable=False),
        sa.Column("installment_id", sa.Integer, nullable=True),
        sa.Column("settlement_id", sa.Integer, nullable=True),
        sa.Column("amount", sa.Float, server_default="0", nullable=False),
        sa.Column("chung_tu", sa.String(200), server_default="", nullable=False),
        sa.Column("reversed_of", sa.Integer, nullable=True),
        sa.Column("note", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_fleet_offsets_plan", "fleet_offset_applications", ["plan_id"])

    op.create_table(
        "fleet_shared_invoices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("so_hoa_don", sa.String(60), nullable=False),
        sa.Column("ngay", sa.Date, nullable=False),
        sa.Column("nha_cung_cap", sa.String(160), server_default="", nullable=False),
        sa.Column("company_id", sa.Integer, nullable=True),
        sa.Column("loai", sa.String(20), server_default="giu_xe", nullable=False),
        sa.Column("tong_tien", sa.Float, server_default="0", nullable=False),
        sa.Column("vat", sa.Float, server_default="0", nullable=False),
        sa.Column("tieu_thuc", sa.String(40), server_default="deu", nullable=False),
        sa.Column("ghi_chu", sa.String(300), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), server_default="", nullable=False),
    )

    op.create_table(
        "fleet_shared_invoice_lines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("fleet_shared_invoices.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer, nullable=False),
        sa.Column("amount", sa.Float, server_default="0", nullable=False),
        sa.Column("he_so", sa.Float, server_default="1", nullable=False),
    )
    op.create_index("ix_fleet_shared_lines_hd", "fleet_shared_invoice_lines", ["invoice_id"])


def downgrade() -> None:
    for t in ("fleet_shared_invoice_lines", "fleet_shared_invoices", "fleet_offset_applications",
              "fleet_settlement_lines", "fleet_settlements", "fleet_repayment_installments",
              "fleet_repayment_plans", "fleet_collaterals", "fleet_sale_cases"):
        op.drop_table(t)
    with op.batch_alter_table("vehicles") as b:
        b.drop_column("partner_id")
    op.drop_table("fleet_partners")
