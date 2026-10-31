"""KH-3 · VTD Rewards — sổ điểm, voucher, yêu thích (Chủ tịch chốt số và duyệt bản xem thử 26/10/2026).

  · `so_diem_rewards` — sổ CHỈ GHI THÊM. Số dư = cộng mọi dòng; không có cột «số dư» để sửa.
    Chủ điểm là SĐT (hoặc email) trên booking — khách chưa mở tài khoản cổng vẫn được tích.
  · `voucher_rewards` — khách đổi điểm lấy voucher (điểm bị GIỮ); Sales áp vào booking.
  · `yeu_thich_khach` — tour khách lưu, kèm giá lúc lưu để nhắc khi giá giảm.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, BigInteger, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# CONG: cộng điểm chuyến đủ điều kiện · DAO: trừ khi booking bị hủy / hoàn / giảm giá trị sau khi đã cộng
# GIU: giữ điểm cho voucher · TRA_GIU: trả điểm (voucher hết hạn, booking dùng voucher bị hủy)
# HET_HAN: điểm quá 12 tháng chưa dùng
LOAI_DONG = {"CONG": "Cộng điểm", "DAO": "Trừ điểm (hủy / hoàn)", "GIU": "Đổi voucher", "TRA_GIU": "Trả điểm voucher",
             "HET_HAN": "Điểm hết hạn", "THUONG": "Thưởng (trưởng đoàn / giới thiệu)"}
# KS-16g (Chủ tịch duyệt v3, 31/10/2026): voucher không đổi từ điểm — chào mừng 50.000 đ, sinh nhật 100.000 đ
LOAI_VOUCHER = {"doi_diem": "Đổi điểm", "chao_mung": "Chào mừng", "sinh_nhat": "Sinh nhật"}
TRANG_THAI_VOUCHER = {"cho_dung": "Chưa dùng", "da_dung": "Đã dùng", "het_han": "Hết hạn — đã trả điểm", "da_hoan": "Đơn hủy — đã trả điểm"}


class SoDiem(Base):
    __tablename__ = "so_diem_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    chu: Mapped[str] = mapped_column(String(80), index=True)            # "sdt:0901234567" / "email:a@b.vn"
    loai: Mapped[str] = mapped_column(String(10))
    so_diem: Mapped[int] = mapped_column(BigInteger)                     # có dấu
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    # AT-1c (Chủ tịch 28/10/2026): điểm từ đơn đặt bàn nhà hàng qua Vietourist — tính như tour
    dat_ban_id: Mapped[int | None] = mapped_column(ForeignKey("don_dat_ban.id"), nullable=True, index=True)
    # KS-16 (Chủ tịch 30/10/2026): đơn khách sạn VTD tích điểm như tour
    don_ks_id: Mapped[int | None] = mapped_column(ForeignKey("don_ks_vtd.id"), nullable=True, index=True)
    voucher_id: Mapped[int | None] = mapped_column(ForeignKey("voucher_rewards.id"), nullable=True)
    het_han: Mapped[date | None] = mapped_column(Date, nullable=True)    # chỉ dòng cộng (CONG, TRA_GIU)
    co_so: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # B đủ điều kiện lúc tính
    he_so: Mapped[str] = mapped_column(String(10), default="")          # "5/4" — hệ số hạng chụp lần cộng đầu
    hang: Mapped[str] = mapped_column(String(12), default="")
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VoucherRewards(Base):
    __tablename__ = "voucher_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True)
    chu: Mapped[str] = mapped_column(String(80), index=True)
    so_diem: Mapped[int] = mapped_column(Integer)
    gia_tri: Mapped[int] = mapped_column(BigInteger)                     # đồng = điểm × 100
    han_dung: Mapped[date] = mapped_column(Date)
    han_diem_goc: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="cho_dung")
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    don_ks_id: Mapped[int | None] = mapped_column(ForeignKey("don_ks_vtd.id"), nullable=True)   # KS-16: khách tự áp
    dat_ban_id: Mapped[int | None] = mapped_column(ForeignKey("don_dat_ban.id"), nullable=True)  # KS-16b: đặt bàn
    ap_boi: Mapped[str] = mapped_column(String(50), default="")
    ap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # KS-16g: loại voucher · phạm vi dùng (tour / tat_ca) · giá trị đơn tối thiểu TRƯỚC voucher
    loai: Mapped[str] = mapped_column(String(12), default="doi_diem", server_default="doi_diem")
    pham_vi: Mapped[str] = mapped_column(String(10), default="tat_ca", server_default="tat_ca")
    don_toi_thieu: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


class GioiThieuRewards(Base):
    """KS-16g · Giới thiệu khách: mỗi tài khoản được giới thiệu MỘT lần, ghi mã TRƯỚC khi đặt tour đầu tiên.
    Người giới thiệu nhận 1.000 điểm khi tour đầu tiên trực tiếp (≥ 5 triệu) của người được giới thiệu hoàn tất."""
    __tablename__ = "gioi_thieu_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    chu_gioi_thieu: Mapped[str] = mapped_column(String(80), index=True)
    tai_khoan_gioi_thieu_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"))
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), unique=True)   # người được giới thiệu
    chu_duoc: Mapped[str] = mapped_column(String(80), index=True)
    ma: Mapped[str] = mapped_column(String(12))
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho")   # cho / da_thuong / khong_du
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class YeuThich(Base):
    __tablename__ = "yeu_thich_khach"
    __table_args__ = (UniqueConstraint("tai_khoan_id", "tour_id", name="uq_yeu_thich"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    gia_luc_luu: Mapped[int] = mapped_column(BigInteger, default=0)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
