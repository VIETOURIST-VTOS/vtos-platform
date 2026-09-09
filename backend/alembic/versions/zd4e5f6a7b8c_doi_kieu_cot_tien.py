"""V9/K1: 47 cột tiền đổi từ số thực nhị phân sang numeric(18,2)

Revision ID: zd4e5f6a7b8c
Revises: zc3d4e5f6a7b
"""
from alembic import op
import sqlalchemy as sa

revision = "zd4e5f6a7b8c"
down_revision = "zc3d4e5f6a7b"
branch_labels = None
depends_on = None

# 47 cột, lấy từ bàn quyết K1 trên hệ thống thật (bảng ks_cot_tien, cột can_doi_kieu).
# Viết THẲNG ra đây chứ không suy từ mô hình lúc chạy: mô hình sẽ còn đổi, còn mạch nâng cấp thì phải
# mô tả đúng những gì nó làm tại THỜI ĐIỂM này – một năm sau đọc lại vẫn biết nó đã đụng vào cột nào.
#
# KHÔNG có purchase_invoices.thue_suat trong danh sách. Máy xếp nó là "tiền" vì tên chứa "thue", nhưng
# đó là thuế SUẤT (8, 10), không phải tiền – và chưa ai xem lại. Bốn cột rate_per_day thì ngược lại:
# máy xếp "chưa rõ", người quyết "tiền", và người quyết đúng (đơn giá thuê xe/HDV theo ngày là tiền).
COT = (
    ("asset_depreciations", "accumulated"),
    ("asset_depreciations", "amount"),
    ("asset_depreciations", "remaining"),
    ("bank_accounts_cat", "opening_balance"),
    ("bank_doc_map", "amount"),
    ("campaigns", "budget"),
    ("cash_plan_items", "amount"),
    ("employees", "advance_limit"),
    ("employees", "base_salary"),
    ("employees", "bhxh_base"),
    ("fin_contracts", "outstanding"),
    ("fin_contracts", "principal"),
    ("fin_schedules", "amount"),
    ("fixed_assets", "cost"),
    ("fixed_assets", "opening_accumulated"),
    ("fixed_assets", "salvage"),
    ("fleet_repayment_plans", "moi_ky"),
    ("fleet_settlements", "chuyen_ky_sau"),
    ("fleet_settlements", "doi_tac_chiu"),
    ("fleet_settlements", "doi_tac_huong"),
    ("guide_assignments", "rate_per_day"),
    ("guide_rates", "old_rate_per_day"),
    ("guide_rates", "rate_per_day"),
    ("labor_contracts", "allowance"),
    ("labor_contracts", "salary"),
    ("labor_contracts", "si_salary"),
    ("lead_channel_stats", "cost"),
    ("mkt_budget_lines", "amount"),
    ("mkt_budgets", "target_revenue"),
    ("mkt_channel_spend", "so_tien"),
    ("prepaid_allocations", "allocated"),
    ("prepaid_allocations", "amount"),
    ("prepaid_allocations", "remaining"),
    ("prepaid_expenses", "amount"),
    ("prepaid_expenses", "opening_allocated"),
    ("purchase_invoices", "tien_thue"),
    ("purchase_invoices", "tien_truoc_thue"),
    ("purchase_invoices", "tong_tien"),
    ("retentions", "amount"),
    ("retentions", "remaining"),
    ("sales_by_consultant", "doanh_thu"),
    ("sales_by_consultant", "doanh_thu_da_thu"),
    ("thieu_gia_von", "doanh_thu"),
    ("thieu_gia_von", "gia_von"),
    ("vehicles", "internal_rate_per_day"),
    ("visa_files", "revenue"),
    ("vt_records", "amount"),
)

# Sai số cho phép khi đối chiếu tổng. Không phải 0: cộng số thực nhị phân vốn đã có sai số tích luỹ,
# nên tổng "trước" tự nó đã không chính xác tuyệt đối. Một đồng cho mỗi cột là đủ chặt để bắt mất mát
# thật và đủ lỏng để không đỏ vì chính cái sai số mà việc này sinh ra để loại bỏ.
SAI_SO = 1.0


def _la_postgres(conn) -> bool:
    return conn.dialect.name == "postgresql"


def upgrade():
    conn = op.get_bind()
    if not _la_postgres(conn):
        # SQLite (máy lập trình) không ép kiểu cột; đổi kiểu ở đó không có nghĩa, và phép đối chiếu
        # tổng cũng không chứng minh được gì. Mô hình đã khai TIEN nên phép thử vẫn chạy đúng.
        return

    lech = []
    for bang, cot in COT:
        truoc = conn.execute(sa.text(
            f'SELECT COALESCE(SUM("{cot}"), 0)::float8 FROM "{bang}"')).scalar() or 0.0

        # ROUND rõ ràng thay vì để PostgreSQL tự ép: viết ra ý định, và đọc lại thì thấy ngay
        # phép làm tròn nằm ở đâu.
        op.execute(sa.text(
            f'ALTER TABLE "{bang}" ALTER COLUMN "{cot}" '
            f'TYPE numeric(18,2) USING ROUND("{cot}"::numeric, 2)'))

        sau = conn.execute(sa.text(
            f'SELECT COALESCE(SUM("{cot}"), 0)::float8 FROM "{bang}"')).scalar() or 0.0

        if abs(float(truoc) - float(sau)) > SAI_SO:
            lech.append(f"{bang}.{cot}: trước {truoc:.2f} → sau {sau:.2f} "
                        f"(lệch {float(truoc) - float(sau):.2f})")

    if lech:
        # Lệnh DDL của PostgreSQL nằm trong giao dịch, nên ném lỗi ở đây là CUỘN LẠI TOÀN BỘ 47 cột –
        # không có trạng thái nửa vời. Đây là lý do phép đối chiếu đặt trong chính mạch nâng cấp chứ
        # không đặt ở một kịch bản chạy sau.
        raise RuntimeError(
            "Đổi kiểu cột tiền làm LỆCH tổng, đã cuộn lại toàn bộ. Chi tiết:\n" + "\n".join(lech))


def downgrade():
    """Trả kiểu về số thực nhị phân.

    NÓI RÕ: lệnh này khôi phục KIỂU, KHÔNG khôi phục SỐ. Chữ số thập phân thứ ba trở đi đã bị làm tròn
    ở chiều lên thì không có ở đây để trả lại. Đo trước khi đổi (09/9/2026) cho thấy không cột tiền nào
    có phần lẻ dưới đồng, nên lần này chiều lên không mất gì – nhưng câu trên vẫn đúng cho mọi lần sau.
    """
    conn = op.get_bind()
    if not _la_postgres(conn):
        return
    for bang, cot in COT:
        op.execute(sa.text(
            f'ALTER TABLE "{bang}" ALTER COLUMN "{cot}" '
            f'TYPE double precision USING "{cot}"::float8'))
