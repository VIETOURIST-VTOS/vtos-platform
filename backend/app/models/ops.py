"""Vận hành: báo cáo ngày (Điều 12), ca trực page (cổng 11), đề nghị chi – lệnh chi NCC (robot R3, cổng 14, 15)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


class DailyReport(Base):
    """Báo cáo công việc cá nhân 4 phần trước 20 giờ (thay chấm công ở khối KD, Đoàn, ĐH, MKT, CNTT)."""
    __tablename__ = "daily_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    part1_done: Mapped[str] = mapped_column(Text, default="")        # 1. Việc đã làm & kết quả
    part2_numbers: Mapped[str] = mapped_column(Text, default="")     # 2. Số liệu ngày (lead, booking, doanh thu, chuyến…)
    part3_issues: Mapped[str] = mapped_column(Text, default="")      # 3. Khó khăn – đề xuất
    part4_plan: Mapped[str] = mapped_column(Text, default="")        # 4. Kế hoạch ngày mai
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    on_time: Mapped[bool] = mapped_column(Boolean, default=True)     # trước 20:00
    robot_score: Mapped[float] = mapped_column(Float, default=0)      # điểm nháp 0–10
    robot_note: Mapped[str] = mapped_column(String(300), default="")
    manager_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manager_note: Mapped[str] = mapped_column(String(300), default="")
    reviewed_by: Mapped[str] = mapped_column(String(50), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PageShift(Base):
    """Ca trực fanpage do GĐ KD phân; robot AI đếm lượt sót > 5 phút; chế tài −100k/−200k/loại ca (chỉ trừ hoa hồng)."""
    __tablename__ = "page_shifts"
    id: Mapped[int] = mapped_column(primary_key=True)
    shift_date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[str] = mapped_column(String(20))                    # sang / chieu / toi
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    assigned_by: Mapped[str] = mapped_column(String(50), default="")
    missed: Mapped[int] = mapped_column(Integer, default=0)          # lượt sót > 5 phút (robot/CNTT nhập)
    missed_note: Mapped[str] = mapped_column(String(300), default="")
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded: Mapped[str] = mapped_column(String(300), default="")  # NV phản hồi trong 3 ngày


class PaymentRequest(Base):
    """Đề nghị chi (mẫu 05-TT). Bắt buộc mã tour với chi phí tour, NCC, số tiền, chứng từ đính kèm; hệ thống tự xếp cấp duyệt."""
    __tablename__ = "payment_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)        # DC2609-0001
    category: Mapped[str] = mapped_column(String(20))                 # chi_tour / marketing / hanh_chinh / hoan_tien
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    # Chi marketing gắn với chiến dịch nào. Không có ô này thì không bao giờ tính được chi phí thực tế
    # theo chiến dịch, và ngân sách marketing chỉ còn là một con số tổng không dùng để quyết định được.
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    # Hạng mục ngân sách marketing của khoản chi. Không có ô này thì màn hình ngân sách chỉ cộng được
    # TỔNG đã chi, không biết hạng mục nào sắp vượt – mà vượt hạng mục mới là thứ cần biết trước.
    marketing_muc: Mapped[str] = mapped_column(String(20), default="")
    supplier_name: Mapped[str] = mapped_column(String(160))
    supplier_tax_code: Mapped[str] = mapped_column(String(20), default="")
    supplier_bank: Mapped[str] = mapped_column(String(120), default="")   # số TK – ngân hàng (thay đổi cần 2 người xác nhận)
    amount: Mapped[float] = mapped_column(TIEN)
    description: Mapped[str] = mapped_column(String(300))
    has_document: Mapped[bool] = mapped_column(Boolean, default=False)    # hợp đồng/hóa đơn/báo giá đính kèm
    document_ref: Mapped[str] = mapped_column(String(120), default="")
    has_invoice: Mapped[bool] = mapped_column(Boolean, default=False)     # có hóa đơn GTGT (không → không được trừ TNDN)
    over_budget: Mapped[bool | None] = mapped_column(Boolean, default=False)     # ngoài dự toán → 2 chữ ký (cổng 15, nullable=True)
    two_signatures: Mapped[bool] = mapped_column(Boolean, default=False)  # cần Chủ tịch + TGĐ
    status: Mapped[str] = mapped_column(String(20), default="cho_tp")     # cho_tp / cho_kt / cho_duyet / cho_chi / da_chi / tu_choi
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    tp_by: Mapped[str] = mapped_column(String(50), default="")
    kt_by: Mapped[str] = mapped_column(String(50), default="")
    approved_by: Mapped[str] = mapped_column(String(50), default="")      # TGĐ (và Chủ tịch nếu 2 chữ ký)
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str] = mapped_column(String(300), default="")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_ref: Mapped[str] = mapped_column(String(120), default="")        # mã giao dịch ngân hàng / SePay
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # pháp nhân chủ quản – rỗng là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ
    # VPM-17 – NGÀY ĐẾN HẠN PHẢI TRẢ. Ngày đã hẹn với nhà cung cấp / người thụ hưởng, KHÔNG phải ngày
    # lập và cũng không phải ngày duyệt.
    #
    # Vì sao cột này sinh ra: bảng dòng tiền bốn mốc xếp mỗi khoản vào một cột theo NGÀY. Đề nghị chi
    # trước đây không có ngày nào cả, nên mọi khoản chi đang chờ đều rơi vào rổ "Chưa đủ dữ liệu dự
    # báo" – đếm được, nhưng không xếp được vào cột nào. Sổ nghĩa vụ (VPM-11) CỐ Ý không đoán một ngày
    # thay người dùng: ngày bịa ra trông y hệt ngày thật trên màn hình lãnh đạo.
    #
    # RỖNG nghĩa là CHƯA AI NHẬP – khác hẳn "không có hạn". Không đặt mặc định, không tự suy từ ngày
    # lập: một khoản chi có hạn 5 ngày và một khoản chưa ai hỏi hạn là hai việc khác nhau, và chỉ
    # người lập đề nghị mới biết mình đã hẹn nhà cung cấp ngày nào.
    ngay_den_han: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # Người gõ ngày và lúc gõ. Ngày đến hạn sửa được sau khi lập (thương lượng lại với NCC là chuyện
    # thường), nên phải biết ai gõ con số đang nằm đó.
    ngay_den_han_boi: Mapped[str] = mapped_column(String(50), default="")
    ngay_den_han_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_method: Mapped[str] = mapped_column(String(20), default="")      # chuyen_khoan / tien_mat
    entry_ids: Mapped[list] = mapped_column(JSON, default=list)
