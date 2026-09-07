"""Marketing – Đợt 1: CHIẾN DỊCH.

Vì sao chiến dịch phải là một BẢN GHI CÓ MÃ chứ không phải một ô chữ tự do như trường `campaign` cũ trên
lead: hai người gõ "Tết 2026" và "tet2026" là hai chiến dịch khác nhau trong mắt máy, nên không bao giờ
cộng được chi phí trên mỗi lead. Có mã rồi thì lead, đề nghị chi, nội dung và khiếu nại mới trỏ về cùng
một chỗ, và câu hỏi "bỏ ra bao nhiêu, thu về bao nhiêu" mới trả lời được.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, ForeignKey, JSON
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
