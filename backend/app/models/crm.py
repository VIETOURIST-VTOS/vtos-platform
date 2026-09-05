"""CRM nhẹ: lead theo kênh (Hotline, VCHAT, Web, Tiktok Ads, Livestream, Appier, Zalo OA…), thống kê lead theo kênh × tháng,
tin nhắn Zalo (OA / ZNS) gửi cho lead – khách; đối chiếu lead ↔ booking để tính tỷ lệ chốt, khách mới / quay lại."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

LEAD_CHANNELS = ["Hotline 1", "Hotline 2", "Đặt tour web", "VCHAT", "Tiktok Ads", "Livestream", "Appier", "Zalo OA", "Facebook", "Khách cũ", "Khác"]
LEAD_STATUS = {"moi": "Mới", "dang_cham_soc": "Đang chăm sóc", "chot": "Đã chốt tour", "mat": "Không chốt"}


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("phone", "lead_month", "channel", name="uq_lead_phone_month_channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)                 # chuẩn hóa 0xxxxxxxxx
    name: Mapped[str] = mapped_column(String(120), default="")
    channel: Mapped[str] = mapped_column(String(40), index=True)
    lead_month: Mapped[str] = mapped_column(String(7), index=True)             # YYYY-MM tháng phát sinh lead
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    campaign: Mapped[str] = mapped_column(String(80), default="")
    interest: Mapped[str] = mapped_column(String(200), default="")             # tour quan tâm
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="moi")
    note: Mapped[str] = mapped_column(Text, default="")
    zalo_uid: Mapped[str] = mapped_column(String(40), default="")               # user_id Zalo OA (khi khách quan tâm OA)
    zalo_follow: Mapped[bool] = mapped_column(Boolean, default=False)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)       # booking chốt (đối chiếu theo SĐT)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LeadChannelStat(Base):
    """Tổng số lead theo kênh × tháng (khi không có danh sách thô – nhập từ báo cáo Marketing)."""
    __tablename__ = "lead_channel_stats"
    __table_args__ = (UniqueConstraint("lead_month", "channel", name="uq_lead_stat_month_channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_month: Mapped[str] = mapped_column(String(7), index=True)
    channel: Mapped[str] = mapped_column(String(40))
    leads: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)                       # chi phí kênh (nếu có) → chi phí/lead
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ZaloMessage(Base):
    """Nhật ký tin Zalo: OA (theo user_id, khách đã quan tâm OA) hoặc ZNS (theo SĐT, mẫu đã duyệt)."""
    __tablename__ = "zalo_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), default="oa")                 # oa / zns
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    zalo_uid: Mapped[str] = mapped_column(String(40), default="")
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_id: Mapped[str] = mapped_column(String(40), default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    text: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(String(30), default="")                # nhac_coc / xac_nhan_booking / cham_soc / khuyen_mai / cam_on
    status: Mapped[str] = mapped_column(String(20), default="cho_gui")          # cho_gui / da_gui / loi / cho_cau_hinh
    response: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
