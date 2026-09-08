"""V9 đợt 2 – bốn mươi tám cột tiền của tour, kinh doanh và đội xe

Revision ID: v9b2e7c3a91d5
Revises: v9a1d6b4f8c02
Create Date: 2026-09-08

Đợt 1 lấy nhóm chạm thẳng vào sổ kế toán. Đợt này lấy nhóm SINH RA những con số đó: giá bán và giá
vốn của tour, tiền booking, quyết toán tour, và toàn bộ tiền của đội xe – từ chi phí chuyến, chi phí
kỳ, tới cấn trừ và lịch trả nợ với chủ xe hợp tác.

Vì sao tour và đội xe đi cùng một đợt: quyết toán đội xe cấn trừ vào công nợ chủ xe, và giá vốn tour
lấy một phần từ chi phí chuyến xe. Đổi một bên mà để bên kia là số thực nhị phân thì phép cấn trừ
vẫn chạy qua một lần làm tròn nhị phân ở giữa – tức là vẫn còn đúng cái đang muốn bỏ.

Danh sách 48 cột dưới đây SINH RA TỪ MÔ HÌNH, không gõ tay: đọc mọi cột đã khai kiểu TIEN rồi trừ đi
tám cột của đợt 1. Có phép thử canh mô hình và bản nâng cấp không lệch nhau.

Ba điều của đợt 1 vẫn nguyên: numeric(18,2) LÀM TRÒN chữ số thập phân thứ ba trở đi và không quay
lại được – chạy `python -m app.services.v9_doi_chieu truoc` để đếm trước; ALTER COLUMN TYPE khóa
bảng trên PostgreSQL nên chạy trong cửa sổ dừng hệ thống; SQLite đi qua batch_alter_table.

Đợt này KHÔNG đụng: tỷ lệ, hệ số, số lượng, số đo (lít, km, ngày công), và những cột K1 còn để "chưa
rõ" chờ Chủ tịch quyết.
"""
from alembic import op
import sqlalchemy as sa

revision = "v9b2e7c3a91d5"
down_revision = "v9a1d6b4f8c02"
branch_labels = None
depends_on = None

COT = [
    ("bookings", "amount", False),
    ("bookings", "discount", False),
    ("bookings", "paid", False),
    ("bookings", "cancel_charge", False),
    ("bookings", "cost_amount", False),
    ("dispatch_orders", "internal_price", False),
    ("fleet_debt_payments", "so_tien", False),
    ("fleet_external_txns", "so_tien", False),
    ("fleet_maintenance", "so_tien", False),
    ("fleet_offset_applications", "amount", False),
    ("fleet_period_costs", "so_tien", False),
    ("fleet_repayment_installments", "amount_due", False),
    ("fleet_repayment_installments", "amount_applied", False),
    ("fleet_repayment_plans", "principal", False),
    ("fleet_sale_cases", "gia_ban", False),
    ("fleet_sale_cases", "da_thu", False),
    ("fleet_settlement_lines", "amount", False),
    ("fleet_settlements", "doanh_thu", False),
    ("fleet_settlements", "dieu_chinh", False),
    ("fleet_settlements", "truoc_can_tru", False),
    ("fleet_settlements", "can_tru", False),
    ("fleet_settlements", "sau_can_tru", False),
    ("fleet_shared_invoice_lines", "amount", False),
    ("fleet_shared_invoices", "tong_tien", False),
    ("fleet_shared_invoices", "vat", False),
    ("fleet_trip_costs", "amount", False),
    ("fleet_trips", "doanh_thu", False),
    ("products", "reference_price", False),
    ("service_orders", "don_gia", False),
    ("service_orders", "thanh_tien", False),
    ("service_requests", "discount", False),
    ("tour_cost_lines", "unit_price", False),
    ("tour_cost_lines", "actual", False),
    ("tour_cost_lines", "paid", False),
    ("tour_cost_lines", "budget", False),
    ("tour_settlements", "doanh_thu", False),
    ("tour_settlements", "gia_von", True),
    ("tours", "price_per_pax", False),
    ("tours", "fixed_cost", False),
    ("tours", "var_cost_per_pax", False),
    ("tours", "actual_revenue", False),
    ("tours", "actual_cost", False),
    ("tours", "promo_value", False),
    ("tours", "price_chd", False),
    ("tours", "price_inf", False),
    ("tours", "price_promo", False),
    ("vehicle_rates", "internal_price", False),
    ("vehicle_rates", "partner_price", False),
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
