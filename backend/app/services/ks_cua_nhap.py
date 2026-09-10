"""Mỗi con số phải có một CỬA cho người nhập – phép kiểm giữ cho quy tắc ấy không mòn.

Ranh giới Chủ tịch đặt ngày 09/9/2026: phần mềm viết cấu trúc, phép tính và luồng quản trị; SỐ LIỆU do
nhân viên các phòng tự nhập – gõ vào biểu, tải tệp, hoặc tải ảnh. Hệ quả trực tiếp: mỗi con số hệ thống
cần phải có ít nhất một cửa để người dùng đưa nó vào. Bảng nào không có cửa nào thì đó là VIỆC CÒN
THIẾU, không phải việc để ai đó nhập hộ vào cơ sở dữ liệu.

Ngày 09/9/2026 đã rà tay toàn bộ 128 bảng và ra kết quả: 120 bảng đủ cửa, 8 bảng máy sinh (đúng ra là
không cần cửa). Tệp này giữ cho kết quả ấy không mòn đi. Rà tay một lần chỉ đúng tại thời điểm rà; bảng
thứ 129 thêm vào tuần sau sẽ không có ai rà lại, và nó sẽ lặng lẽ nằm đó không cửa.

PHÉP KIỂM TRẢ LỜI ĐÚNG MỘT CÂU: có bảng nào trong mô hình mà chưa ai khai cửa cho nó không?

Ba nguồn cửa, và mức tin cậy của chúng KHÁC NHAU – nói rõ ra đây để không ai đọc bảng này rồi yên tâm
quá mức:

  1. CỬA TẢI TỆP – đọc SỐNG từ intake.BO_NAP[*]["bang_dich"]. Bỏ một bộ nạp đi là phép kiểm biết ngay.
  2. CỬA NHẬP TAY – danh sách KHAI, chép từ bản rà 09/9. Phép kiểm biết bảng đã ĐƯỢC KHAI là có cửa;
     nó KHÔNG tự kiểm màn hình ấy còn sống hay không. Xoá một màn hình nhập tay thì phép kiểm này im.
     Chỗ đó do K12 (đối chiếu ma trận quyền với thư mục màn hình) gác.
  3. MÁY SINH – danh sách KHAI, mỗi dòng kèm LÝ DO. Bắt buộc có lý do: "máy sinh" là cách dễ nhất để
     một bảng thiếu cửa được cho qua, nên phải viết ra ai ghi vào bảng đó và vì sao người không cần
     chạm tới. Không viết được lý do nghĩa là chưa chắc nó máy sinh.

Bảng có trong danh sách khai nhưng không còn trong mô hình thì KHÔNG phải lỗi: các nhánh đang làm dở
có bảng chưa gộp về (chuỗi bán hàng V6), và bảng đã bỏ thì dòng khai thừa ra là chuyện dọn dần.
"""
from sqlalchemy.orm import Session

CUA_TAY = (
    "accounts", "ai_pause", "ai_positions", "alerts", "attachments", "attendance_days", "audit_log",
    "auto_reports", "ban_doc_chung_tu", "bang_gia", "bang_gia_dong", "bank_accounts_cat",
    "bank_doc_map", "bank_transactions", "bao_gia", "bao_gia_ban", "bao_gia_dong", "bookings",
    "campaigns", "care_tickets", "cash_plan_items", "companies", "complaints", "content_items",
    "conversations", "daily_reports", "dependents", "dispatch_orders", "employee_profiles",
    "employees", "fin_contracts", "fin_schedules", "fleet_ai_runs", "fleet_collaterals",
    "fleet_debt_payments", "fleet_maintenance", "fleet_offset_applications", "fleet_partners",
    "fleet_period_costs", "fleet_repayment_installments", "fleet_repayment_plans",
    "fleet_sale_cases", "fleet_settlement_lines", "fleet_settlements", "fleet_shared_invoice_lines",
    "fleet_shared_invoices", "fleet_trip_costs", "fleet_trips", "fleet_verifications",
    "guide_assignments", "guide_rates", "hop_dong_khach", "incidents", "intake_runs", "invoices",
    "journal_entries", "journal_lines", "khoa_ghi", "labor_contracts", "lead_channel_stats",
    "leads", "leave_requests", "messages", "mkt_budget_lines", "mkt_budgets", "page_shifts",
    "params", "partners", "payment_requests", "payroll_runs", "period_locks", "products",
    "projects", "quy_tac_hach_toan", "receipts", "retentions", "service_orders", "service_requests",
    "supplier_bank_changes", "suppliers", "thieu_gia_von", "tour_cost_lines", "tour_events",
    "tac_vu_tu_dong",
    "tours", "user_grants", "users", "vehicle_documents", "vehicle_plates", "vehicle_rates",
    "vehicles", "visa_access_links", "visa_ai_suggestions", "visa_applications",
    "visa_appointments", "visa_cases", "visa_checklist_items", "visa_checklist_templates",
    "visa_customer_confirmations", "visa_document_reviews", "visa_document_versions",
    "visa_family_groups", "visa_files", "visa_form_versions", "visa_handovers", "visa_markets",
    "visa_results", "visa_tasks", "visa_waiver_requests", "vt_records", "zalo_messages",
    "zalo_oa_tokens",
)


# Máy sinh – bảng KHÔNG cần cửa nhập, kèm lý do. Xem ghi chú đầu tệp: không viết được lý do nghĩa là
# chưa chắc nó máy sinh.
MAY_SINH = {
    "ai_runs": "Nhật ký robot chạy – hệ thống tự ghi, không ai nhập tay.",
    "ks_bao_cao": "Báo cáo robot Kiểm soát tự lập.",
    "ks_cot_tien": "Cột tiền robot Kiểm soát tự dựng từ sổ.",
    "ks_diem": "Điểm chấm tự tính, không nhập tay.",
    "ks_phat_hien": "Phát hiện của robot – tự ghi.",
    "ngoai_le_xu_ly": "Ngoại lệ do bộ nạp tự đẩy ra.",
    "prepaid_allocations": "ĐÃ KIỂM LẠI 09/9: bản rà đầu tiên xếp nhầm bảng này vào 'cần cửa'. Thực tế có cửa: màn hình /tai-san, nút ghi sổ phân bổ",
    "su_kien_ky_thuat": "Sự kiện kỹ thuật – hệ thống tự ghi.",
    # V11 – lịch tự động hóa. Sổ lần chạy do hệ thống chạy tác vụ BÁO VỀ (n8n hoặc chính vòng lặp
    # trong VTOS), qua POST /tu-dong/bao-cao. Người không gõ tay dòng nào ở đây, và KHÔNG NÊN gõ: một
    # dòng "đã chạy thành công" nhập tay là bằng chứng giả về một việc có thể chưa hề chạy.
    #
    # Ngược lại, bảng KHAI BÁO tác vụ (tac_vu_tu_dong) thì phải do người khai – nằm ở CUA_TAY, màn
    # hình /tu-dong-hoa. Hai bảng đi cùng nhau nhưng khác hẳn về cửa, và đó chính là thiết kế của
    # V11: máy tự khai tác vụ thì mất khả năng phát hiện tác vụ đã ngừng chạy.
    "lan_chay_tac_vu": "Lần chạy do hệ thống chạy tác vụ báo về qua /tu-dong/bao-cao – nhập tay một "
                       "dòng 'đã chạy thành công' là tạo bằng chứng giả về việc có thể chưa hề chạy.",
    "tong_dai_su_kien": "Nhật ký nguyên văn webhook tổng đài – tổng đài ghi vào, không ai nhập tay.",
}


def _bang_mo_hinh() -> set[str]:
    import app.main  # noqa: F401 – nạp trọn mô hình, nếu không thì chỉ thấy vài bảng tình cờ nạp trước
    from app.db.session import Base
    return {t for t in Base.metadata.tables} - {"alembic_version"}


def cua_tai_tep() -> dict[str, list[str]]:
    """{bảng đích: [mã bộ nạp]} – đọc SỐNG từ sổ bộ nạp, không chép lại."""
    from app.services.intake import BO_NAP
    ra: dict[str, list[str]] = {}
    for ma, bo in BO_NAP.items():
        b = bo.get("bang_dich")
        if b: ra.setdefault(b, []).append(ma)
    return ra


def bang(db: Session | None = None) -> dict:
    mo = _bang_mo_hinh()
    tep = cua_tai_tep()
    khong_cua = sorted(b for b in mo if b not in tep and b not in CUA_TAY and b not in MAY_SINH)
    return {
        "so_bang": len(mo),
        "co_cua_tep": sorted(b for b in mo if b in tep),
        "co_cua_tay": sorted(b for b in mo if b in CUA_TAY),
        "may_sinh": sorted(b for b in mo if b in MAY_SINH),
        "khong_cua": khong_cua,
        # Dòng khai cho bảng không còn trong mô hình. Không phải lỗi – nhánh chưa gộp thì bảng chưa có.
        "khai_thua": sorted((set(CUA_TAY) | set(MAY_SINH)) - mo),
    }


def quet(db: Session) -> list[dict]:
    b = bang(db)
    return [{"ma": f"bang_khong_cua_nhap#{t}", "loai": "bang_khong_cua_nhap", "muc": "vang",
             "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt", "doi_tuong": t,
             "tom_tat": f"Bảng “{t}” không có cửa nào để người dùng đưa số liệu vào – không bộ nạp tệp, "
                        f"không màn hình nhập tay, và cũng chưa khai là bảng máy sinh. Theo ranh giới "
                        f"09/9/2026 thì đây là việc CÒN THIẾU, không phải chỗ để nhập hộ vào cơ sở dữ liệu",
             "chi_tiet": {"bang": t}}
            for t in b["khong_cua"]]


def _cua_nhap_du_lieu(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot."""
    return quet(db)
