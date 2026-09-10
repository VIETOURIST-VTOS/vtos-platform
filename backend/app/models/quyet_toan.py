"""Quyết toán tour theo điều hành – nguồn số lớn nhất của công ty.

495 chuyến trong hai tháng 7–8/2026 với 48.042.594.678 đ doanh thu. Trước bản này số đó vào VTOS bằng
đồng bộ Vietrip hoặc gõ tay.

Vì sao KHÔNG ghi thẳng vào bảng tours mà để một bảng riêng:

    Cột giá vốn ở bảng tours là Float mặc định 0 – nó không có cách nào nói "chưa có số". Mà đúng chỗ
    đó là chỗ hỏng: trong hai tệp thật có 76 dòng doanh thu 2.654.940.111 đ mà giá vốn để 0. Ghi thẳng
    vào một cột không phân biệt được "0 đồng" với "chưa ai điền" là sổ báo lãi 100% trên 2,65 tỷ, và
    bảng vẫn cân nên không ai nhìn ra.

    Ở bảng này gia_von để NULL được. Rỗng là rỗng. Ô 0 trong tệp nguồn cũng đọc thành rỗng, vì theo chỉ
    đạo 08/9 của Chủ tịch mọi đơn đều có giá vốn – "giá vốn bằng 0" không phải một bản chất nghiệp vụ,
    nó là ô chưa ai điền.

Và vì sao có cột phan_loai: 60 trong 76 dòng ấy là khách lẻ – bảo lưu do hủy tour, gia hạn visa, vé.
Xếp tất cả vào một hàng đợi "thiếu giá vốn" thì hàng đợi lúc nào cũng đầy những dòng không ai sửa
được, và người ta thôi mở nó – đúng kiểu một bộ kiểm báo oan 26 việc thì không ai đọc lần thứ hai.
Máy KHÔNG tự đoán dòng nào là bảo lưu; nó tách riêng và chờ người phân loại.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

LOAI_DON = {"tour": "Tour đoàn / tour ghép", "khach_le": "Khách lẻ do sale tự xử lý"}

TRANG_THAI_QT = {"da_qt": "Đã quyết toán", "du_toan": "Dự toán (chưa QT)"}

# Phân loại do NGƯỜI đặt cho dòng có doanh thu mà chưa có giá vốn. Mặc định là chưa phân loại: máy đọc
# tệp không biết một khoản 93 triệu là doanh thu khách lẻ hay là vé công tác của ban lãnh đạo.
PHAN_LOAI = {
    "": "Chưa phân loại",
    "cho_gia_von": "Chờ Điều hành nhập giá vốn",
    "bao_luu_huy_tour": "Bảo lưu do hủy tour – giá vốn chưa phát sinh",
    "chi_phi_noi_bo": "Không phải doanh thu – chi phí nội bộ, ghi nhầm vào đơn",
    "khong_phat_sinh_gia_von": "Dịch vụ không phát sinh giá vốn (đã xác nhận)",
}


class TourSettlement(Base):
    __tablename__ = "tour_settlements"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    __table_args__ = (
        Index("ux_tour_settlements_ma", "ma_tour", unique=True),
        Index("ix_tour_settlements_ky", "ky"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7))                        # kỳ tour KẾT THÚC, YYYY-MM
    ma_tour: Mapped[str] = mapped_column(String(60))
    ten_tour: Mapped[str] = mapped_column(String(300), default="")
    loai: Mapped[str] = mapped_column(String(20), default="tour")
    # Điều hành viên giữ NGUYÊN VĂN tên trong tệp, và operator_id khi tra ra người thật. Không bao giờ
    # điền tên tài khoản đã nạp tệp vào đây – người nạp không phải người chịu trách nhiệm về chuyến.
    dieu_hanh: Mapped[str] = mapped_column(String(120), default="")
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sale: Mapped[str] = mapped_column(String(120), default="")
    ngay_kh: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_kt: Mapped[date | None] = mapped_column(Date, nullable=True)
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # NULL nghĩa là CHƯA CÓ SỐ. Đây là lý do tồn tại của cả bảng này.
    gia_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    trang_thai_qt: Mapped[str] = mapped_column(String(20), default="du_toan")
    phan_loai: Mapped[str] = mapped_column(String(30), default="")
    phan_loai_boi: Mapped[str] = mapped_column(String(50), default="")
    phan_loai_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    han_bao_luu: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    nguon: Mapped[str] = mapped_column(String(30), default="nap_tep")
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def loi_nhuan(self):
        """Chưa có giá vốn thì KHÔNG có lợi nhuận – trả None, không trả doanh thu."""
        return None if self.gia_von is None else (self.doanh_thu or 0) - (self.gia_von or 0)
