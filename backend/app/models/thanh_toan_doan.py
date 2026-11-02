"""TR-1d · Link thanh toán tour đoàn riêng (Chủ tịch duyệt bản xem thử 02/11/2026).

Một dòng = một link cho MỘT ĐỢT của lịch thanh toán hợp đồng khách (`lich_thanh_toan_hd`). Ba điều đã chốt:
  · SỐ TIỀN do máy lấy: báo giá khách đã chốt → hợp đồng → số còn thiếu của đợt lúc tạo link. Không ai gõ số.
  · HẠN link là hạn của đợt.
  · CHỈ Sale Admin phòng Đoàn tạo / hủy link. Tour đoàn KHÔNG nhận thẻ — chỉ chuyển khoản (QR hoặc chuyển tay).

TIỀN KHÔNG NẰM Ở ĐÂY: tiền vào là Receipt của booking nối với hợp đồng — robot khớp nội dung «TD……» + đúng số,
Kế toán xác nhận, bút toán như mọi booking. Bảng này chỉ giữ link, trạng thái, và dấu email đã gửi.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

TRANG_THAI_LINK = {"mo": "Đang mở", "da_tra": "Đã trả", "huy": "Đã hủy"}   # «hết hạn» là phép tính (han < hôm nay), không lưu


class LinkThanhToanDoan(Base):
    __tablename__ = "link_thanh_toan_doan"

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True, default="")   # TD000123 — nội dung chuyển khoản
    hop_dong_id: Mapped[int] = mapped_column(ForeignKey("hop_dong_khach.id"), index=True)
    lich_id: Mapped[int] = mapped_column(ForeignKey("lich_thanh_toan_hd.id"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    so_tien: Mapped[float] = mapped_column(TIEN)
    han: Mapped[date] = mapped_column(Date)
    trang_thai: Mapped[str] = mapped_column(String(10), default="mo", index=True)
    email: Mapped[str] = mapped_column(String(120), default="")
    dien_thoai: Mapped[str] = mapped_column(String(30), default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    huy_boi: Mapped[str] = mapped_column(String(50), default="")
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_huy: Mapped[str] = mapped_column(String(300), default="")
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"), nullable=True)
    tra_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_link_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_hd_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_loi: Mapped[str] = mapped_column(String(300), default="")
