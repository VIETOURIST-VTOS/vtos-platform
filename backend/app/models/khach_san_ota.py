"""KS-1 · Khách sạn qua OTA (Affiliate) — Chủ tịch duyệt bản xem thử 28/10/2026.

Khách chọn khách sạn trên OTA: VTD chỉ CHUYỂN khách sang OTA bằng link Affiliate chính thức; khách
xem giá, đặt và thanh toán trên OTA. VTOS ghi LƯỢT CHUYỂN — một lượt chuyển KHÔNG phải đặt phòng,
không phải doanh thu. Đối soát đặt phòng / hoa hồng do OTA báo về làm ở KS-2.

BA BẢNG
  · `phap_nhan_hop_dong` — pháp nhân ký hợp đồng Affiliate (THE INFINIS PATHWAY INC., Canada). CỐ Ý
    không nằm trong `companies`: bảng ấy là các pháp nhân của tập đoàn, đọc bởi hợp nhất, dòng tiền,
    suy pháp nhân booking. Một pháp nhân nước ngoài chỉ để nhận hoa hồng OTA lọt vào đó là làm lệch
    các phép tính ấy.
  · `doi_tac_ota` — một OTA: trạng thái hợp tác, link chính thức, tên miền / đường dẫn cho phép, bốn
    điều kiện bật. Đổi link = phiên bản mới, tự TẮT và phải kiểm lại.
  · `luot_chuyen_ota` — sổ lượt chuyển, chỉ ghi thêm. Không lưu SĐT / email; không đưa gì của khách
    vào link.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

TRANG_THAI_HOP_TAC = {"chua_dang_ky": "Chưa đăng ký", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt",
                      "tam_dung": "Tạm dừng"}
CONG_NGOAI = {"khach_hang": "Khách hàng", "doi_tac": "Đối tác", "co_dong": "Cổ đông"}


class PhapNhanHopDong(Base):
    __tablename__ = "phap_nhan_hop_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True)
    ten: Mapped[str] = mapped_column(String(200))
    quoc_gia: Mapped[str] = mapped_column(String(60), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")


class DoiTacOta(Base):
    __tablename__ = "doi_tac_ota"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True)
    ten: Mapped[str] = mapped_column(String(80))
    phap_nhan_id: Mapped[int | None] = mapped_column(ForeignKey("phap_nhan_hop_dong.id"), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(16), default="chua_dang_ky")
    link: Mapped[str] = mapped_column(String(500), default="")
    ten_mien: Mapped[str] = mapped_column(String(120), default="")      # host đúng của link, vd expedia.com
    duong_dan: Mapped[str] = mapped_column(String(200), default="")     # đường dẫn link phải bắt đầu bằng
    da_kiem_link: Mapped[bool] = mapped_column(Boolean, default=False)  # đã mở thử, đúng tài khoản Affiliate
    duoc_dung_web: Mapped[bool] = mapped_column(Boolean, default=False)  # OTA cho phép dùng trên vietourist.vn
    bat: Mapped[bool] = mapped_column(Boolean, default=False)
    phien_ban: Mapped[int] = mapped_column(Integer, default=1)
    bang_chung: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LuotChuyenOta(Base):
    __tablename__ = "luot_chuyen_ota"
    __table_args__ = (UniqueConstraint("tai_khoan_id", "request_id", name="uq_luot_chuyen_ota_req"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    doi_tac_ota_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ota.id"), index=True)
    phien_ban_link: Mapped[int] = mapped_column(Integer)
    cong: Mapped[str] = mapped_column(String(12))
    doi_tac_ban_hang_id: Mapped[int | None] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), nullable=True)
    diem_den: Mapped[str] = mapped_column(String(120), default="")
    nhan_phong: Mapped[date | None] = mapped_column(Date, nullable=True)
    tra_phong: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_phong: Mapped[int] = mapped_column(Integer, default=1)
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=2)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
