"""KH-1 · Cổng khách hàng VTD — YÊU CẦU khách gửi từ cổng (Chủ tịch duyệt 26/10/2026).

Một yêu cầu tour KHÔNG phải booking: không giữ chỗ, không báo giá cuối, không thu tiền. Nó vào hàng
chờ Kinh doanh như một lead kênh «Đặt tour web» để Sales liên hệ; bảng này giữ lại TỪNG lần khách
bấm gửi (lead gộp theo SĐT × tháng × kênh nên không đủ để khách xem lại yêu cầu của mình).
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

LOAI_YEU_CAU = {"tour": "Tour có lịch", "tour_doan": "Tour đoàn theo yêu cầu", "nha_hang": "Đặt bàn nhà hàng"}


class YeuCauKhach(Base):
    __tablename__ = "yeu_cau_khach"
    id: Mapped[int] = mapped_column(primary_key=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    loai: Mapped[str] = mapped_column(String(12), default="tour")
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    ten_tour: Mapped[str] = mapped_column(String(200), default="")      # bản chụp tên tour lúc gửi
    so_khach: Mapped[int] = mapped_column(Integer, default=1)
    ngay_mong_muon: Mapped[date | None] = mapped_column(Date, nullable=True)
    dien_thoai: Mapped[str] = mapped_column(String(20), default="")     # số Sales gọi lại
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    # KH-2 · đặt bàn nhà hàng (ngày đến = ngay_mong_muon)
    nha_hang_id: Mapped[int | None] = mapped_column(ForeignKey("nha_hang.id"), nullable=True)
    thuc_don_id: Mapped[int | None] = mapped_column(ForeignKey("thuc_don_nha_hang.id"), nullable=True)
    gio_den: Mapped[str] = mapped_column(String(5), default="")
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    tam_tinh: Mapped[int | None] = mapped_column(Integer, nullable=True)   # máy tính từ giá đã lưu, KHÔNG phải báo giá
    # DT-1 · CTV giới thiệu khách (loai «gioi_thieu»): tên khách CTV khai; tai_khoan_id là CTV.
    ten_khach: Mapped[str] = mapped_column(String(120), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
