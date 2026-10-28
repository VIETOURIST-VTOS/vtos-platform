"""DT-2 · ĐẶT BÀN NHÀ HÀNG CÓ THANH TOÁN (Chủ tịch duyệt bản xem thử 28/10/2026).

Một đơn đặt bàn đi: gửi (khách / cổ đông / đại lý / CTV) → nhà hàng nhận bàn trên cổng NCC → người đặt trả
trước qua QR (tài khoản Vietourist) hoặc thẻ Visa / Master / JCB qua OnePay → bàn giữ → ăn xong khách trả
phần còn lại tại nhà hàng → nhà hàng báo «khách đã dùng» kèm bill → Kế toán chốt doanh số (đơn qua đối tác
thì vào D06).

  · Khách lẻ: cọc 10% hoặc trả đủ. Đoàn (từ 10 khách) đặt sẵn menu: cọc 50% hoặc trả đủ.
  · Hủy: trước 24 giờ hoàn đủ; 3–24 giờ giữ 10% bill; dưới 3 giờ / không đến giữ 10% (lẻ) hoặc 50% (đoàn).
    Giữ không quá số đã trả. Ngưỡng, tỷ lệ, mốc giờ là THAM SỐ (quy tắc hai người).
  · Mọi số tiền vào là số Kế toán xác nhận (QR) hoặc OnePay báo có chữ ký kiểm được (thẻ). Vietourist không
    thấy, không lưu số thẻ.

Hai bảng mới, bắt đầu RỖNG. Đơn nối 1–1 với `yeu_cau_khach` (đường lead cho Sales và màn nhà hàng nhận bàn
của NCC-1 giữ nguyên).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

TRANG_THAI = {"cho_nhan": "Chờ nhà hàng nhận bàn", "cho_tra": "Nhà hàng đã nhận · chờ thanh toán",
              "da_giu": "Đã giữ bàn", "het_han": "Quá hạn thanh toán · bàn đã trả lại",
              "tu_choi": "Nhà hàng từ chối", "da_dung": "Khách đã dùng", "khong_den": "Khách không đến",
              "huy": "Đã hủy"}
CACH_TT = {"coc": "Cọc", "du": "Trả đủ"}
NGUON = {"khach_hang": "Khách tự đặt", "co_dong": "Cổ đông", "dai_ly": "Đại lý", "ctv": "Cộng tác viên"}
HOAN_TT = {"": "", "cho_sales": "Chờ Sales xác nhận hoàn", "cho_chi": "Chờ Kế toán hoàn tiền", "da_hoan": "Đã hoàn",
           "khong_hoan": "Không phải hoàn"}
KENH = {"qr": "QR chuyển khoản", "onepay": "Thẻ (OnePay)"}
TT_THANH_TOAN = {"cho": "Đang thanh toán", "that_bai": "Không thành công", "thanh_cong": "OnePay báo thành công · chờ đối soát",
                 "da_doi_soat": "Đã đối soát", "da_xac_nhan": "Kế toán đã xác nhận"}
TT_DA_TRA = ("thanh_cong", "da_doi_soat", "da_xac_nhan")


class DonDatBan(Base):
    __tablename__ = "don_dat_ban"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)               # NH26110001 — nội dung chuyển khoản
    yeu_cau_id: Mapped[int] = mapped_column(ForeignKey("yeu_cau_khach.id"), unique=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)   # người đặt trên cổng
    nguon: Mapped[str] = mapped_column(String(12), default="khach_hang")
    doi_tac_id: Mapped[int | None] = mapped_column(ForeignKey("doi_tac_ban_hang.id"), nullable=True, index=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    thuc_don_id: Mapped[int] = mapped_column(ForeignKey("thuc_don_nha_hang.id"))
    ngay: Mapped[date] = mapped_column(Date, index=True)
    gio: Mapped[str] = mapped_column(String(5))
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=1)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    ten_khach: Mapped[str] = mapped_column(String(120), default="")
    dien_thoai: Mapped[str] = mapped_column(String(20), default="")
    la_doan: Mapped[bool] = mapped_column(Boolean, default=False)
    cach_tt: Mapped[str] = mapped_column(String(4), default="coc")
    ty_le_coc: Mapped[int] = mapped_column(Integer, default=10)
    tam_tinh: Mapped[float] = mapped_column(TIEN, default=0)            # máy tính từ giá thực đơn đã duyệt
    phai_tra_truoc: Mapped[float] = mapped_column(TIEN, default=0)
    trang_thai: Mapped[str] = mapped_column(String(10), default="cho_nhan", index=True)
    nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    han_tra: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Nhà hàng báo sau bữa ăn
    bill_thuc_te: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thu_tai_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    bill_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    dung_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dung_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Kế toán chốt doanh số (đơn qua đối tác → D06)
    doanh_so: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chot_boi: Mapped[str] = mapped_column(String(50), default="")
    chot_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Hủy và hoàn
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    huy_boi: Mapped[str] = mapped_column(String(60), default="")
    huy_ly_do: Mapped[str] = mapped_column(Text, default="")
    mien_phat: Mapped[bool] = mapped_column(Boolean, default=False)
    so_giu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_hoan: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    hoan_tt: Mapped[str] = mapped_column(String(10), default="")
    hoan_boi: Mapped[str] = mapped_column(String(50), default="")
    hoan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hoan_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ThanhToanDatBan(Base):
    __tablename__ = "thanh_toan_dat_ban"
    id: Mapped[int] = mapped_column(primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_dat_ban.id"), index=True)
    kenh: Mapped[str] = mapped_column(String(8))                        # qr | onepay
    so_tien: Mapped[float] = mapped_column(TIEN)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho", index=True)
    bank_txn_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transactions.id"), nullable=True, unique=True)
    ma_gd: Mapped[str] = mapped_column(String(40), default="", index=True)     # vpc_MerchTxnRef
    so_gd_cong: Mapped[str] = mapped_column(String(40), default="")            # vpc_TransactionNo
    ket_qua: Mapped[str] = mapped_column(String(10), default="")               # vpc_TxnResponseCode
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    goc: Mapped[str] = mapped_column(String(80), default="")                   # tên miền cổng để đưa khách về sau thẻ
