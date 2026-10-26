"""KH-4 · Cổng khách — đánh giá, góp ý riêng lãnh đạo, yêu cầu hỗ trợ (Chủ tịch duyệt 27/10/2026).

  · `phieu_danh_gia_khach` — MỘT phiếu cho mỗi booking khách tự chấm trên cổng. Điểm từng mục KHÔNG
    nằm ở đây: chúng vào `danh_gia_sau_tour` (nguồn «khach») như phiếu khảo sát Zalo, để màn
    /danh-gia và hồ sơ HDV đọc chung một bảng. Bảng này chỉ giữ phần riêng của cổng: ai gửi, gửi
    lúc nào, sửa tới khi nào.
  · `gop_y_lanh_dao` — chỉ Chủ tịch và TGĐ đọc và trả lời (BKS đọc theo luật chung, không trả lời).
  · `ho_tro_khach` — đổi / hủy / hóa đơn / khác. Chỉ là YÊU CẦU: không tự hủy, không tự hoàn tiền,
    không tự xuất hóa đơn. Người nhận trả lời khách tại đây; việc thật làm ở màn của nó.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Date, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

TRANG_THAI_VIEC = {"moi": "Mới", "dang_xu_ly": "Đang xử lý", "da_tra_loi": "Đã trả lời", "dong": "Đã đóng"}
LOAI_HO_TRO = {"doi": "Đổi ngày / người đi", "huy": "Hủy đơn", "hoa_don": "Xuất hóa đơn", "khac": "Khác"}
BO_PHAN = {"kinh_doanh": "Kinh doanh", "ke_toan": "Kế toán", "sales_admin": "Sale Admin"}
MUC_GOP_Y = {"thuong": "Bình thường", "khan": "Khẩn"}
LIEN_HE_LAI = {"email": "Email đã xác minh", "zalo": "Zalo", "khong": "Không cần liên hệ"}


class PhieuDanhGiaKhach(Base):
    __tablename__ = "phieu_danh_gia_khach"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    care_id: Mapped[int] = mapped_column(ForeignKey("care_tickets.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    gui_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    han_sua: Mapped[date] = mapped_column(Date)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    so_lan_sua: Mapped[int] = mapped_column(Integer, default=0)
    cong_khai: Mapped[str] = mapped_column(String(6), default="")        # co / khong — hỏi riêng
    gop_y: Mapped[str] = mapped_column(Text, default="")


class GopYLanhDao(Base):
    __tablename__ = "gop_y_lanh_dao"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(12), unique=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tieu_de: Mapped[str] = mapped_column(String(200))
    noi_dung: Mapped[str] = mapped_column(Text)
    muc: Mapped[str] = mapped_column(String(8), default="thuong")
    lien_he_qua: Mapped[str] = mapped_column(String(8), default="email")
    trang_thai: Mapped[str] = mapped_column(String(12), default="moi", index=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")              # khách thấy
    ghi_chu_noi_bo: Mapped[str] = mapped_column(Text, default="")       # khách KHÔNG thấy
    tra_loi_boi: Mapped[str] = mapped_column(String(50), default="")
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cap_nhat_boi: Mapped[str] = mapped_column(String(50), default="")
    cap_nhat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class HoTroKhach(Base):
    __tablename__ = "ho_tro_khach"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(12), unique=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    loai: Mapped[str] = mapped_column(String(8))
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    hoa_don: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # ten_don_vi, mst, dia_chi, email
    bo_phan: Mapped[str] = mapped_column(String(12), index=True)
    giao_cho_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="moi", index=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    tra_loi_boi: Mapped[str] = mapped_column(String(50), default="")
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    cap_nhat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
