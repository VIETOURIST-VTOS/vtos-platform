"""CÔNG NỢ KHÁCH THEO VIETRIP – ảnh chụp mỗi ngày, chia 4 nhóm theo ngày khởi hành.

Anh Tuấn chốt 28/9/2026: báo cáo công nợ lấy từ Vietrip lúc 8h sáng mỗi ngày phải TỰ ĐỘNG cập nhật
lên VTOS, và tệp gốc lưu vào Cloudflare R2.

VÌ SAO LÀ ẢNH CHỤP, KHÔNG PHẢI SỬA THẲNG BOOKING
  Trang /cong-no hiện đọc SỔ của VTOS (booking đã đồng bộ + phiếu thu). Từ 01/10/2026 Vietrip mới bắt
  đầu đổ dữ liệu thật về hằng ngày, nên trong giai đoạn trộn ấy số của Vietrip và số của VTOS có thể
  lệch nhau. Ảnh chụp giữ nguyên con số Vietrip đã nói vào ngày ấy – để so, không để ghi đè.

BA ĐIỀU TRONG CẤU TRÚC
  1. MỘT NGÀY MỘT ẢNH (chỉ mục duy nhất trên `ngay`). Chạy lại trong ngày thì THAY ảnh của ngày ấy
     (khách nộp thêm buổi chiều), nhưng tệp gốc từng lần nạp vẫn nằm trên R2 – không mất dấu.
  2. `con_thieu` và `nhom` do MÁY CHỦ tính, không nhận từ bên gửi: con_thieu = tong − da_thu; nhóm
     theo khoi_hanh so với `ngay` của ảnh. Hai con số gõ sẵn từ ngoài vào là hai chỗ có thể lệch.
  3. Bảo lưu nằm trong ảnh nhưng `nhom = 0` và KHÔNG cộng vào tổng công nợ.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

TEN_NHOM = {
    0: "Bảo lưu (không tính nợ)",
    1: "NHÓM 1 – Quá hạn / đã khởi hành",
    2: "NHÓM 2 – Khởi hành ≤ 2 tuần",
    3: "NHÓM 3 – Khởi hành 2 tuần – 1 tháng",
    4: "NHÓM 4 – Lịch xa > 1 tháng",
}


class CongNoVietripAnh(Base):
    """Một ngày chụp."""
    __tablename__ = "cong_no_vietrip_anh"
    __table_args__ = (Index("ux_cong_no_vietrip_anh_ngay", "ngay", unique=True),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ngay: Mapped[date] = mapped_column(Date)                          # ngày của báo cáo
    so_booking: Mapped[int] = mapped_column(Integer, default=0)       # không tính bảo lưu
    tong_con_thieu: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # không tính bảo lưu
    so_lan_nap: Mapped[int] = mapped_column(Integer, default=1)
    tep_key: Mapped[str] = mapped_column(String(200), default="")     # khoá tệp gốc trên R2
    tep_sha256: Mapped[str] = mapped_column(String(64), default="")
    tep_ben_vung: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    nguoi_nap: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CongNoVietripDong(Base):
    """Một booking còn nợ trong một ngày chụp."""
    __tablename__ = "cong_no_vietrip_dong"
    __table_args__ = (Index("ix_cong_no_vietrip_dong_anh", "anh_id", "nhom"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    anh_id: Mapped[int] = mapped_column(ForeignKey("cong_no_vietrip_anh.id", ondelete="CASCADE"))
    booking_id: Mapped[str] = mapped_column(String(30))               # recID Vietrip – CHUỖI
    ma_tour: Mapped[str] = mapped_column(String(80), default="")
    ten_tour: Mapped[str] = mapped_column(Text, default="")
    khach: Mapped[str] = mapped_column(String(200), default="")
    sdt_khach: Mapped[str] = mapped_column(String(40), default="")
    sales: Mapped[str] = mapped_column(String(120), default="")
    sdt_sales: Mapped[str] = mapped_column(String(40), default="")
    tong: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    con_thieu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    khoi_hanh: Mapped[date | None] = mapped_column(Date, nullable=True)
    nhom: Mapped[int] = mapped_column(Integer, default=0)             # 0 = bảo lưu
    bao_luu: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    ghi_chu: Mapped[str] = mapped_column(Text, default="")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 29/9/2026 · PHẢI TRẢ NCC THEO DỰ TOÁN TOUR TRÊN VIETRIP
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# Anh Tuấn: "kiểm tra lại trên Vietrip, dựa vào dự toán tour để xác định số phải trả và sửa lại
# VTOS đúng theo Vietrip". Nguồn là trang Quyết toán tour (/tour-settlement/overview/{id}), khối
# "Thống kê thu chi": Tổng chi (dự toán) · Thực tế đã chi · Còn phải chi. Một ngày một ảnh, mỗi
# tour một dòng; `con_phai_chi` do MÁY CHỦ tính = tong_chi − da_chi.
class PhaiTraVietripAnh(Base):
    __tablename__ = "phai_tra_vietrip_anh"
    __table_args__ = (Index("ux_phai_tra_vietrip_anh_ngay", "ngay", unique=True),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ngay: Mapped[date] = mapped_column(Date)
    so_tour: Mapped[int] = mapped_column(Integer, default=0)
    tong_con_phai_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_lan_nap: Mapped[int] = mapped_column(Integer, default=1)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    nguoi_nap: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PhaiTraVietripDong(Base):
    __tablename__ = "phai_tra_vietrip_dong"
    __table_args__ = (Index("ix_phai_tra_vietrip_dong_anh", "anh_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    anh_id: Mapped[int] = mapped_column(ForeignKey("phai_tra_vietrip_anh.id", ondelete="CASCADE"))
    tour_id: Mapped[int] = mapped_column(Integer)                       # recID tour trên Vietrip
    ma_tour: Mapped[str] = mapped_column(String(80), default="")
    ten_tour: Mapped[str] = mapped_column(Text, default="")
    khoi_hanh: Mapped[date | None] = mapped_column(Date, nullable=True)
    ket_thuc: Mapped[date | None] = mapped_column(Date, nullable=True)
    tong_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    con_phai_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
