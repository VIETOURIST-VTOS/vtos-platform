"""Marketing – Đợt 1: CHIẾN DỊCH.

Vì sao chiến dịch phải là một BẢN GHI CÓ MÃ chứ không phải một ô chữ tự do như trường `campaign` cũ trên
lead: hai người gõ "Tết 2026" và "tet2026" là hai chiến dịch khác nhau trong mắt máy, nên không bao giờ
cộng được chi phí trên mỗi lead. Có mã rồi thì lead, đề nghị chi, nội dung và khiếu nại mới trỏ về cùng
một chỗ, và câu hỏi "bỏ ra bao nhiêu, thu về bao nhiêu" mới trả lời được.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

CAMPAIGN_STATUS = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "dang_chay": "Đang chạy",
                   "tam_dung": "Tạm dừng", "ket_thuc": "Kết thúc", "da_danh_gia": "Đã đánh giá"}
MUC_TIEU = {"ra_lead": "Ra lead", "nhan_dien": "Nhận diện thương hiệu",
            "ban_tour": "Bán tour cụ thể", "cham_khach_cu": "Chăm sóc khách cũ"}
KENH = ("facebook", "zalo", "google", "tiktok", "email", "su_kien", "doi_tac", "khac")
KENH_TEN = {"facebook": "Facebook", "zalo": "Zalo OA", "google": "Google", "tiktok": "TikTok",
            "email": "Email", "su_kien": "Sự kiện", "doi_tac": "Đối tác", "khac": "Khác"}


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)              # CD2609-01
    name: Mapped[str] = mapped_column(String(160))
    objective: Mapped[str] = mapped_column(String(20))                      # MUC_TIEU
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    mang: Mapped[str] = mapped_column(String(6), default="le")              # le / doan
    channels: Mapped[list] = mapped_column(JSON, default=list)
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)       # rỗng = đang chạy
    budget: Mapped[float] = mapped_column(Float, default=0)
    target_leads: Mapped[int] = mapped_column(Integer, default=0)
    target_bookings: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="nhap")
    evaluation: Mapped[str] = mapped_column(Text, default="")               # bắt buộc khi chuyển sang da_danh_gia
    note: Mapped[str] = mapped_column(Text, default="")
    # Ai điền tờ trình này. AI được phép ĐỀ XUẤT nhưng bản do AI lập luôn dừng ở nháp và phải người
    # có thẩm quyền duyệt – cùng nguyên tắc đã áp cho AI trả lời khách ở hộp thư.
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")      # nguoi / ai
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")               # AI giải thích căn cứ đề xuất
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_by: Mapped[str] = mapped_column(String(50), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------- Đợt 2: KẾ HOẠCH & NGÂN SÁCH ----------
HANG_MUC = {"quang_cao": "Quảng cáo trả phí", "noi_dung": "Nội dung – sản xuất", "su_kien": "Sự kiện",
            "an_pham": "Ấn phẩm – quà tặng", "nghien_cuu": "Nghiên cứu thị trường", "khac": "Khác"}
BUDGET_STATUS = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "hieu_luc": "Đang hiệu lực", "dong": "Đã đóng kỳ"}


class MarketingBudget(Base):
    """Ngân sách marketing một kỳ, một pháp nhân.

    Bảng này chỉ giữ phần DỰ TOÁN. Số ĐÃ CHI không nằm ở đây mà đọc từ đề nghị chi đã duyệt – hai nơi
    giữ hai con số chi phí của cùng một kỳ là hai con số sẽ lệch nhau, và không ai biết tin con số nào.
    """
    __tablename__ = "mkt_budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(8), index=True)              # 2026-09 hoặc 2026-Q4
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    target_leads: Mapped[int] = mapped_column(Integer, default=0)
    target_revenue: Mapped[float] = mapped_column(Float, default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")               # căn cứ – bắt buộc
    status: Mapped[str] = mapped_column(String(10), default="nhap")
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_by: Mapped[str] = mapped_column(String(50), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MarketingBudgetLine(Base):
    """Một hạng mục của ngân sách kỳ. Tổng không lưu thành cột riêng – tổng luôn cộng từ các dòng này."""
    __tablename__ = "mkt_budget_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("mkt_budgets.id"), index=True)
    hang_muc: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(String(300), default="")


# ---------- Đợt 5: NỘI DUNG & THƯƠNG HIỆU ----------
# Vietourist là công ty đại chúng (mã VTD, sàn UPCoM). Một bài đăng hứa "cam kết hoàn tiền 100%" hay một
# con số tài chính đưa ra ngoài mà chưa ai duyệt là rủi ro pháp lý và rủi ro công bố thông tin, không phải
# chuyện nội bộ Marketing. Vì vậy bảng này là SỔ DUYỆT, không phải thư viện ảnh.
ND_LOAI = {"bai_dang": "Bài đăng", "video": "Video", "an_pham": "Ấn phẩm in", "email": "Email",
           "kich_ban": "Kịch bản tư vấn", "thong_cao": "Thông cáo báo chí"}
ND_KENH = {"website": "Website", "facebook": "Facebook", "zalo": "Zalo OA", "tiktok": "TikTok",
           "youtube": "YouTube", "in_an": "In ấn", "bao_chi": "Báo chí"}
ND_TRANG_THAI = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "cho_ky_2": "Chờ chữ ký thứ hai",
                 "da_duyet": "Đã duyệt", "da_dang": "Đã đăng", "go": "Đã gỡ / hết hiệu lực"}


class ContentItem(Base):
    __tablename__ = "content_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)              # ND2609-014
    title: Mapped[str] = mapped_column(String(200))
    loai: Mapped[str] = mapped_column(String(12))
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    kenh: Mapped[list] = mapped_column(JSON, default=list)
    ngay_du_kien: Mapped[date] = mapped_column(Date)
    ban_thao: Mapped[str] = mapped_column(String(400), default="")          # đường dẫn bản thảo – bắt buộc
    # Hai ô quyết định có cần chữ ký thứ hai hay không. Trả lời "Có" ở một trong hai thì bản thảo phải qua
    # người ký thứ hai (Ban TGĐ hoặc Pháp chế) trước khi được duyệt.
    co_cam_ket: Mapped[bool] = mapped_column(Boolean, default=False)
    co_so_lieu_tc: Mapped[bool] = mapped_column(Boolean, default=False)
    nguoi_soan: Mapped[str] = mapped_column(String(50), default="")
    nguoi_duyet: Mapped[str] = mapped_column(String(160), default="")       # nhiều chữ ký: ngăn bởi dấu phẩy
    status: Mapped[str] = mapped_column(String(12), default="nhap")
    link_dang: Mapped[str] = mapped_column(String(400), default="")
    ly_do_go: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
