# -*- coding: utf-8 -*-
"""Đợt R2 15/10/2026 — DANH MỤC KHOẢN MỤC CHI PHÍ.

VÌ SAO CÓ BẢNG NÀY, ĐO ĐƯỢC TRƯỚC KHI VIẾT

Đọc trực tiếp MISA AMIS của Vietourist ngày 15/10/2026: danh mục **Khoản mục chi phí TRỐNG HOÀN
TOÀN**. Hệ quả không ai nhìn thấy vì nó im lặng: cả một họ báo cáo "… theo khoản mục chi phí" của
MISA đều chạy ra bảng rỗng — không báo lỗi, chỉ không có dòng nào. Mà câu hỏi mà họ báo cáo ấy trả
lời là câu Vietourist hỏi hằng tháng: **một tour lỗ thì lỗ ở landtour, ở vé máy bay, hay ở khách
sạn?**

VTOS đã có CHỖ GHI từ trước: `JournalLine.item_code` ("mã khoản mục chi phí"). Thiếu đúng hai thứ:
một DANH MỤC để mã ấy trỏ vào, và một LUẬT nói dòng nào bắt buộc phải có nó. Đợt này làm cả hai.

RANH GIỚI 09/9/2026 — bảng này là CỬA TAY. Mười dòng nạp sẵn là khuôn ngành tour, không phải số
liệu: Kế toán sửa tên, thêm, hoặc ngừng dùng bất kỳ dòng nào qua `/api/v1/hach-toan/khoan-muc`.
`nap_mac_dinh` chạy được nhiều lần và KHÔNG đè lên dòng người đã sửa.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Nhóm khoản mục — để báo cáo gom được, và để một khoản mục mới phải chọn chỗ đứng của nó.
NHOM_KHOAN_MUC = {
    "gia_von":  "Giá vốn trực tiếp của tour",
    "ban_hang": "Chi phí bán hàng",
    "quan_ly":  "Chi phí quản lý doanh nghiệp",
    "tai_chinh": "Chi phí tài chính",
}


class KhoanMucChiPhi(Base):
    """Một khoản mục chi phí. `ma` là thứ `JournalLine.item_code` trỏ vào."""
    __tablename__ = "khoan_muc_chi_phi"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(200))
    nhom: Mapped[str] = mapped_column(String(20), default="gia_von", index=True)
    thu_tu: Mapped[int] = mapped_column(Integer, default=100)
    # `dung = False` là NGỪNG DÙNG, không phải xoá: bút toán cũ vẫn trỏ vào mã này, nên xoá dòng
    # danh mục là làm mồ côi mọi dòng sổ đã ghi. Ngừng dùng thì không chọn mới được nữa, còn báo
    # cáo của kỳ cũ vẫn đọc ra đúng tên khoản mục lúc ấy.
    dung: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
