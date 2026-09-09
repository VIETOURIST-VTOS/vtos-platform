"""K2 bước 1: 83 cột tiền được PHÉP rỗng (chưa đổi mặc định, chưa đụng dữ liệu)

Revision ID: ze5f6a7b8c9d
Revises: zd4e5f6a7b8c
"""
from alembic import op
import sqlalchemy as sa

revision = "ze5f6a7b8c9d"
down_revision = "zd4e5f6a7b8c"
branch_labels = None
depends_on = None

# Chủ tịch chốt 09/9/2026: ở những cột này, MỌI số 0 nghĩa là "chưa nhập dữ liệu". Quyết định ấy trả
# lời câu hỏi K2 cho cả 83 cột một lượt, không phải hỏi từng phòng.
#
# Nhưng nó KHÔNG thể thi hành trong một bước. Trong mã có 316 dòng làm phép toán trên các cột này, và
# 242 dòng CHƯA an toàn với giá trị rỗng – kiểu sum(l.debit for l in e.lines). Cho phép rỗng mà đồng
# thời để ô trống lưu thành rỗng là làm vỡ 242 chỗ đó, và vỡ ở báo cáo cuối tháng.
#
# Nên tách hai bước:
#   BƯỚC 1 (bản này) – cột ĐƯỢC PHÉP rỗng. Mặc định vẫn là 0, dữ liệu cũ vẫn là 0, không dòng mã nào
#                      đổi hành vi. Hôm nay không có gì khác đi; thứ có thêm là KHẢ NĂNG ghi "chưa nhập".
#   BƯỚC 2 (sau)     – gia cố 242 chỗ đọc, đổi mặc định sang rỗng, và mở ô trống trên biểu nhập.
#
# Bước 1 an toàn theo nghĩa chặt: nới ràng buộc không bao giờ làm hỏng dữ liệu đang có, và lệnh hạ cấp
# thì có thể hỏng – nếu lúc ấy đã có dòng mang giá trị rỗng thì không đặt lại NOT NULL được. Ghi rõ ở
# hàm downgrade.
COT = (
    ("asset_depreciations", "accumulated"),
    ("asset_depreciations", "amount"),
    ("asset_depreciations", "remaining"),
    ("bank_accounts_cat", "opening_balance"),
    ("bank_doc_map", "amount"),
    ("bookings", "amount"),
    ("bookings", "cancel_charge"),
    ("bookings", "cost_amount"),
    ("bookings", "discount"),
    ("bookings", "paid"),
    ("campaigns", "budget"),
    ("dispatch_orders", "internal_price"),
    ("employees", "advance_limit"),
    ("employees", "base_salary"),
    ("employees", "bhxh_base"),
    ("fin_contracts", "outstanding"),
    ("fin_contracts", "principal"),
    ("fixed_assets", "cost"),
    ("fixed_assets", "opening_accumulated"),
    ("fixed_assets", "salvage"),
    ("fleet_debt_payments", "so_tien"),
    ("fleet_external_txns", "so_tien"),
    ("fleet_maintenance", "so_tien"),
    ("fleet_offset_applications", "amount"),
    ("fleet_period_costs", "so_tien"),
    ("fleet_repayment_installments", "amount_applied"),
    ("fleet_repayment_installments", "amount_due"),
    ("fleet_repayment_plans", "principal"),
    ("fleet_sale_cases", "da_thu"),
    ("fleet_sale_cases", "gia_ban"),
    ("fleet_settlement_lines", "amount"),
    ("fleet_settlements", "can_tru"),
    ("fleet_settlements", "dieu_chinh"),
    ("fleet_settlements", "doanh_thu"),
    ("fleet_settlements", "sau_can_tru"),
    ("fleet_settlements", "truoc_can_tru"),
    ("fleet_shared_invoice_lines", "amount"),
    ("fleet_shared_invoices", "tong_tien"),
    ("fleet_shared_invoices", "vat"),
    ("fleet_trip_costs", "amount"),
    ("fleet_trips", "doanh_thu"),
    ("invoices", "pre_tax"),
    ("invoices", "total"),
    ("invoices", "vat"),
    ("journal_lines", "credit"),
    ("journal_lines", "debit"),
    ("labor_contracts", "allowance"),
    ("labor_contracts", "salary"),
    ("labor_contracts", "si_salary"),
    ("lead_channel_stats", "cost"),
    ("mkt_budget_lines", "amount"),
    ("mkt_budgets", "target_revenue"),
    ("prepaid_allocations", "allocated"),
    ("prepaid_allocations", "amount"),
    ("prepaid_allocations", "remaining"),
    ("prepaid_expenses", "amount"),
    ("prepaid_expenses", "opening_allocated"),
    ("products", "reference_price"),
    ("retentions", "amount"),
    ("retentions", "remaining"),
    ("service_orders", "don_gia"),
    ("service_orders", "thanh_tien"),
    ("service_requests", "discount"),
    ("thieu_gia_von", "doanh_thu"),
    ("thieu_gia_von", "gia_von"),
    ("tour_cost_lines", "actual"),
    ("tour_cost_lines", "budget"),
    ("tour_cost_lines", "paid"),
    ("tour_cost_lines", "unit_price"),
    ("tour_settlements", "doanh_thu"),
    ("tours", "actual_cost"),
    ("tours", "actual_revenue"),
    ("tours", "fixed_cost"),
    ("tours", "price_chd"),
    ("tours", "price_inf"),
    ("tours", "price_per_pax"),
    ("tours", "price_promo"),
    ("tours", "promo_value"),
    ("tours", "var_cost_per_pax"),
    ("vehicle_rates", "internal_price"),
    ("vehicle_rates", "partner_price"),
    ("visa_files", "revenue"),
    ("vt_records", "amount"),
)


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for bang, cot in COT:
        op.execute(sa.text(f'ALTER TABLE "{bang}" ALTER COLUMN "{cot}" DROP NOT NULL'))


def downgrade():
    """Đặt lại NOT NULL.

    CHỈ CHẠY ĐƯỢC khi chưa có dòng nào mang giá trị rỗng. Đã có rồi thì lệnh này dừng giữa chừng, và
    đó là hành vi ĐÚNG: nó không được phép âm thầm biến "chưa nhập" thành 0 – vì làm thế là dựng lại
    đúng chỗ mù mà K2 sinh ra để xoá.
    """
    if op.get_bind().dialect.name != "postgresql":
        return
    for bang, cot in COT:
        op.execute(sa.text(f'ALTER TABLE "{bang}" ALTER COLUMN "{cot}" SET NOT NULL'))
