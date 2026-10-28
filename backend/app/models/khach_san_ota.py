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

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

TRANG_THAI_HOP_TAC = {"chua_dang_ky": "Chưa đăng ký", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt",
                      "tam_dung": "Tạm dừng"}
CONG_NGOAI = {"khach_hang": "Khách hàng", "doi_tac": "Đối tác", "co_dong": "Cổ đông"}
# VB-1 (Chủ tịch duyệt 28/10/2026): cùng khung cho VÉ MÁY BAY qua OTA. Hai loại link: «hoa_hong» (link
# Affiliate, đủ bốn điều kiện) và «cong_khai» (trang công khai của OTA, CHƯA có hoa hồng — chỉ cần link đúng
# tên miền + đã kiểm). Trang công khai chỉ dùng cho vé máy bay; khách sạn giữ nguyên bốn điều kiện.
SAN_PHAM = {"khach_san": "Khách sạn", "ve_may_bay": "Vé máy bay"}
LOAI_LINK = {"hoa_hong": "Link hoa hồng", "cong_khai": "Trang công khai (chưa có hoa hồng)"}
HANG_VE = {"pho_thong": "Phổ thông", "pho_thong_dac_biet": "Phổ thông đặc biệt", "thuong_gia": "Thương gia"}


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
    san_pham: Mapped[str] = mapped_column(String(12), default="khach_san", index=True)   # VB-1
    loai_link: Mapped[str] = mapped_column(String(10), default="hoa_hong")              # VB-1
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
    # KS-2: gắn mã lượt chuyển vào link (SubID) — CHỈ khi OTA cho phép. Tên tham số do Chủ tịch khai.
    subid_cho_phep: Mapped[bool] = mapped_column(Boolean, default=False)
    subid_tham_so: Mapped[str] = mapped_column(String(30), default="")
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LuotChuyenOta(Base):
    __tablename__ = "luot_chuyen_ota"
    __table_args__ = (UniqueConstraint("tai_khoan_id", "request_id", name="uq_luot_chuyen_ota_req"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    doi_tac_ota_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ota.id"), index=True)
    ma_luot: Mapped[str | None] = mapped_column(String(16), nullable=True, unique=True)   # KS-2: mã ngẫu nhiên gắn vào link (SubID)
    phien_ban_link: Mapped[int] = mapped_column(Integer)
    cong: Mapped[str] = mapped_column(String(12))
    doi_tac_ban_hang_id: Mapped[int | None] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), nullable=True)
    diem_den: Mapped[str] = mapped_column(String(120), default="")
    nhan_phong: Mapped[date | None] = mapped_column(Date, nullable=True)
    tra_phong: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_phong: Mapped[int] = mapped_column(Integer, default=1)
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=2)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    # VB-1 · vé máy bay: ngày đi / ngày về dùng lại `nhan_phong` / `tra_phong`; điểm đến dùng `diem_den`.
    san_pham: Mapped[str] = mapped_column(String(12), default="khach_san")
    diem_di: Mapped[str] = mapped_column(String(120), default="")
    em_be: Mapped[int] = mapped_column(Integer, default=0)
    hang_ve: Mapped[str] = mapped_column(String(20), default="")
    loai_link: Mapped[str] = mapped_column(String(10), default="hoa_hong")   # loại link LÚC chuyển
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


# ---------------------------------------------------------------- KS-2 · đối soát

TRANG_THAI_LO = {"cho_duyet": "Chờ Chủ tịch duyệt", "da_duyet": "Đã duyệt · đã ghi sổ", "tu_choi": "Từ chối"}


class LoNapOta(Base):
    """Một lần Kế toán nạp tệp báo cáo OTA. Chưa duyệt thì KHÔNG chạm vào sổ."""
    __tablename__ = "lo_nap_ota"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True)
    doi_tac_ota_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ota.id"), index=True)
    ky: Mapped[str] = mapped_column(String(7), default="")
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    bam_tep: Mapped[str] = mapped_column(String(64), index=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho_duyet", index=True)
    dong: Mapped[list] = mapped_column(JSON, default=list)            # các dòng đã đọc, chuẩn hoá
    so_dong: Mapped[int] = mapped_column(Integer, default=0)
    so_loi: Mapped[int] = mapped_column(Integer, default=0)
    loi: Mapped[list] = mapped_column(JSON, default=list)
    nap_boi: Mapped[str] = mapped_column(String(50), default="")
    nap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do: Mapped[str] = mapped_column(String(300), default="")
    ket_qua: Mapped[dict] = mapped_column(JSON, default=dict)          # số mới / cập nhật / trùng lúc duyệt


class DatPhongOta(Base):
    """Một đặt phòng OTA báo về — trạng thái HIỆN TẠI. Mỗi lần OTA báo khác đi: phiên bản +1, sổ ghi phần chênh."""
    __tablename__ = "dat_phong_ota"
    __table_args__ = (UniqueConstraint("doi_tac_ota_id", "khoa", name="uq_dat_phong_ota_khoa"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tac_ota_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ota.id"), index=True)
    khoa: Mapped[str] = mapped_column(String(300))                    # mã đặt phòng OTA, hoặc khoá ghép khi báo cáo không có mã
    co_ma_rieng: Mapped[bool] = mapped_column(Boolean, default=False)
    ky: Mapped[str] = mapped_column(String(7), default="", index=True)  # tháng của ngày đặt
    ngay_dat: Mapped[date | None] = mapped_column(Date, nullable=True)
    san_pham: Mapped[str] = mapped_column(String(80), default="")
    thanh_pho: Mapped[str] = mapped_column(String(120), default="")
    quoc_gia: Mapped[str] = mapped_column(String(80), default="")
    link: Mapped[str] = mapped_column(String(300), default="")
    ngay_den: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_di: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_khach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tien_te: Mapped[str] = mapped_column(String(3), default="USD")
    gia_tri_cent: Mapped[int] = mapped_column(BigInteger, default=0)   # đơn vị nhỏ nhất (cent)
    hoa_hong_cent: Mapped[int] = mapped_column(BigInteger, default=0)
    trang_thai_chuyen: Mapped[str] = mapped_column(String(40), default="")
    trang_thai_tt: Mapped[str] = mapped_column(String(40), default="")
    ma_luot: Mapped[str] = mapped_column(String(40), default="")       # SubID OTA báo lại (nếu có)
    luot_id: Mapped[int | None] = mapped_column(ForeignKey("luot_chuyen_ota.id"), nullable=True, index=True)
    phien_ban: Mapped[int] = mapped_column(Integer, default=1)
    lo_id: Mapped[int] = mapped_column(ForeignKey("lo_nap_ota.id"))
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SoHoaHongOta(Base):
    """Sổ CHỈ GHI THÊM: mỗi lần duyệt ghi phần chênh hoa hồng của từng đặt phòng (âm khi hủy / giảm)."""
    __tablename__ = "so_hoa_hong_ota"
    id: Mapped[int] = mapped_column(primary_key=True)
    dat_phong_id: Mapped[int] = mapped_column(ForeignKey("dat_phong_ota.id"), index=True)
    lo_id: Mapped[int] = mapped_column(ForeignKey("lo_nap_ota.id"), index=True)
    phien_ban: Mapped[int] = mapped_column(Integer)
    tien_te: Mapped[str] = mapped_column(String(3), default="USD")
    chenh_cent: Mapped[int] = mapped_column(BigInteger)
    ly_do: Mapped[str] = mapped_column(String(120), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
