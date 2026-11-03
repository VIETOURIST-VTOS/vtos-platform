"""TR-1 · Tour kiểu Agoda/Klook trên cổng khách + đặt tour online (Chủ tịch duyệt bản xem thử 01/11/2026,
nối nội dung web 02/11/2026).

CẤU TRÚC — hai bảng mới, và lý do không có bảng tiền riêng:
  · DonTourOnline   — phần CỔNG của một booking tour khách tự đặt: danh sách khách, cách trả (cọc / đủ), số phải
                      trả ngay, yêu cầu hóa đơn công ty, email đã gửi. TIỀN KHÔNG NẰM Ở ĐÂY: đơn online LÀ một
                      Booking thật (qua đủ cổng như Điều hành / đại lý tạo booking, giữ chỗ VPM-7), tiền vào là
                      Receipt của booking ấy — robot khớp QR, Kế toán xác nhận, bút toán như mọi booking tour.
                      Không mở đường kế toán thứ hai.
  · ThanhToanTourOnline — một lần khách bấm trả bằng thẻ qua cổng SePay / OnePay (mã giao dịch TR…). Thành công
                      thì máy sinh Receipt (chờ Kế toán xác nhận) vào booking; bảng này chỉ giữ dấu vết cổng thẻ.
Ảnh / lịch trình / bảng giá / bao gồm của tour KHÔNG có bảng riêng: đọc thẳng từ trang tour trên vietourist.com.vn
(Product.link_web → Product.noi_dung_web) — Chủ tịch 02/11/2026: không viết lại chương trình và hình ảnh.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

PHUONG_TIEN_TOUR = {"xe": "Xe du lịch", "may_bay": "Máy bay", "tau_hoa": "Tàu hỏa", "du_thuyen": "Du thuyền"}
CACH_TRA_TOUR = {"coc": "Giữ chỗ — đặt cọc", "du": "Thanh toán toàn bộ"}
KENH_TOUR = {"qr": "QR chuyển khoản", "sepay": "Thẻ (cổng SePay)", "onepay": "Thẻ (OnePay)"}


class DonTourOnline(Base):
    __tablename__ = "don_tour_online"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True, index=True)
    ma: Mapped[str] = mapped_column(String(30), index=True)                       # = mã booking (nội dung chuyển khoản)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    tai_khoan_ngoai_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=1)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    em_be: Mapped[int] = mapped_column(Integer, default=0)
    khach: Mapped[list] = mapped_column(JSON, default=list)                       # [{ho_ten, ngay_sinh, gioi_tinh, giay_to, loai}]
    email: Mapped[str] = mapped_column(String(160), default="")
    cach_tra: Mapped[str] = mapped_column(String(4), default="coc")               # coc | du
    tong: Mapped[float | None] = mapped_column(TIEN, default=0, nullable=True)
    phai_tra: Mapped[float] = mapped_column(TIEN, default=0)                      # số trả NGAY (cọc hoặc toàn bộ)
    han_tra_con_lai: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hoa_don_cong_ty: Mapped[dict | None] = mapped_column(JSON, nullable=True)     # {mst, ten, dia_chi, email} — Kế toán xuất
    hoa_don_da_xuat: Mapped[bool] = mapped_column(Boolean, default=False)
    hoa_don_xuat_boi: Mapped[str] = mapped_column(String(50), default="")
    hoa_don_xuat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_gui_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_moc: Mapped[int] = mapped_column(Integer, default=0)                    # số tiền đã báo bằng email lần gần nhất
    email_loi: Mapped[str] = mapped_column(String(300), default="")
    yeu_cau: Mapped[str] = mapped_column(Text, default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ThanhToanTourOnline(Base):
    __tablename__ = "thanh_toan_tour_online"
    id: Mapped[int] = mapped_column(primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_tour_online.id"), index=True)
    kenh: Mapped[str] = mapped_column(String(8), default="sepay")                 # sepay | onepay
    ma_gd: Mapped[str] = mapped_column(String(40), default="", index=True)
    so_tien: Mapped[float | None] = mapped_column(TIEN, default=0, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho")            # cho | thanh_cong | that_bai
    so_gd_cong: Mapped[str] = mapped_column(String(60), default="")
    ket_qua: Mapped[str] = mapped_column(String(40), default="")
    receipt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
