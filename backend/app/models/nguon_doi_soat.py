"""KS-16h · Nguồn đơn CTV và đối soát đối tác (Chủ tịch duyệt bản xem thử 31/10/2026, đề xuất v3 mục 5–7).

  · `nguon_don` — một lần GIỮ NGUỒN 30 ngày cho một SĐT khách: CTV gửi «Giới thiệu khách» (được bảo vệ) hoặc
    khách vào qua link CTV (last-click, chỉ khi chưa có nguồn được bảo vệ). Booking tạo trong thời hạn của
    khách ấy được MÁY gắn đối tác và khóa (`bookings.nguon_don_id`). Dòng không xóa: thua / bị thay / hết hạn
    đều ghi trạng thái và lý do.
  · `vu_viec_doi_tac` — khiếu nại có mã (nguồn đơn hoặc dòng đối soát), hạn 5 ngày làm việc.
  · `bang_doi_soat` / `dong_doi_soat` — bảng đối soát một tháng của một đối tác: Kế toán lập & gửi (hạn ngày
    5), đối tác đồng ý / khiếu nại từng đơn trong 5 ngày làm việc (quá hạn = đồng ý), hạn trả ngày 15.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, BigInteger, Date, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

LOAI_NGUON = {"gioi_thieu": "CTV giới thiệu", "link": "Link CTV"}
TRANG_THAI_NGUON = {"giu": "Đang giữ", "thua": "Không giữ được", "thay": "Bị link mới thay", "het_han": "Hết hạn",
                    "huy": "Hủy do vụ việc"}
TRANG_THAI_BANG = {"da_gui": "Chờ đối tác phản hồi", "dong_y": "Đối tác đồng ý", "qua_han": "Quá hạn — coi như đồng ý",
                   "co_khieu_nai": "Có đơn khiếu nại"}
TRANG_THAI_VV = {"mo": "Đang xử lý", "chap_nhan": "Chấp nhận", "bac": "Bác"}


class NguonDon(Base):
    __tablename__ = "nguon_don"
    id: Mapped[int] = mapped_column(primary_key=True)
    khach_sdt: Mapped[str] = mapped_column(String(20), index=True)          # 0xxxxxxxxx
    khach_ten: Mapped[str] = mapped_column(String(120), default="")
    doi_tac_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), index=True)
    loai: Mapped[str] = mapped_column(String(12))                            # gioi_thieu / link
    tu: Mapped[datetime] = mapped_column(DateTime)
    den: Mapped[datetime] = mapped_column(DateTime)
    trang_thai: Mapped[str] = mapped_column(String(10), default="giu")
    ly_do: Mapped[str] = mapped_column(String(300), default="")
    yeu_cau_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chinh_sach: Mapped[str] = mapped_column(String(20), default="v3-31/10/2026")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class VuViecDoiTac(Base):
    __tablename__ = "vu_viec_doi_tac"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True)
    doi_tac_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), index=True)
    loai: Mapped[str] = mapped_column(String(12))                            # nguon / doi_soat
    booking_ma: Mapped[str] = mapped_column(String(30), default="")
    khach_sdt: Mapped[str] = mapped_column(String(20), default="")
    dong_doi_soat_id: Mapped[int | None] = mapped_column(ForeignKey("dong_doi_soat.id"), nullable=True)
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(10), default="mo", index=True)
    han: Mapped[date] = mapped_column(Date)
    ket_qua: Mapped[str] = mapped_column(String(500), default="")
    xu_ly_boi: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BangDoiSoat(Base):
    __tablename__ = "bang_doi_soat"
    __table_args__ = (UniqueConstraint("doi_tac_id", "ky", name="uq_bang_doi_soat"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tac_id: Mapped[int] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), index=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)                  # YYYY-MM
    gui_boi: Mapped[str] = mapped_column(String(50), default="")
    gui_luc: Mapped[datetime] = mapped_column(DateTime)
    han_phan_hoi: Mapped[date] = mapped_column(Date)
    han_tra: Mapped[date] = mapped_column(Date)
    phan_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DongDoiSoat(Base):
    __tablename__ = "dong_doi_soat"
    id: Mapped[int] = mapped_column(primary_key=True)
    bang_id: Mapped[int] = mapped_column(ForeignKey("bang_doi_soat.id"), index=True)
    ma_don: Mapped[str] = mapped_column(String(30))
    ten: Mapped[str] = mapped_column(String(200), default="")
    doanh_so: Mapped[int] = mapped_column(BigInteger, default=0)
    hoa_hong: Mapped[int] = mapped_column(BigInteger, default=0)            # phần của đơn trong bậc lũy tiến
    y_kien: Mapped[str] = mapped_column(String(12), default="")             # "" chưa / dong_y / khieu_nai
    y_kien_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
