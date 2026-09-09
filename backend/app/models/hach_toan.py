"""Quy tắc hạch toán: bảng quy ước máy đọc được, thay cho tệp Excel và trí nhớ của kế toán.

Nguyên tắc: máy chạy quy tắc, người sửa quy tắc chứ không sửa từng bút toán.
Một quy tắc chỉ có hiệu lực khi đủ hai chữ ký (Chủ tịch + TGĐ), giống bảng tham số chính sách.
Sửa quy tắc không sửa bút toán đã ghi – bút toán cũ giữ nguyên dấu vết quy tắc đã sinh ra nó.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


# Nguồn nghiệp vụ mà quy tắc áp vào
NGUON = {
    "tien_vao": "Tiền vào tài khoản (sao kê ngân hàng)",
    "tien_ra": "Tiền ra tài khoản (sao kê ngân hàng)",
    "mua_vao": "Chi phí mua vào (đề nghị chi / hóa đơn NCC)",
    "quyet_toan": "Quyết toán tour / dịch vụ hoàn thành",
    "luong": "Bảng lương",
    "ket_chuyen": "Kết chuyển cuối kỳ",
}

# Cách lấy mã đối tượng cho dòng bút toán
DOI_TUONG = {
    "": "Không cần đối tượng",
    "khach": "Khách hàng của đơn",
    "ncc": "Nhà cung cấp trên đề nghị chi",
    "nhan_vien": "Nhân viên / HDV nhận tạm ứng",
    "ngan_hang": "Ngân hàng của tài khoản",
}

BEN_THUE = {"": "Không có thuế", "no": "Thuế ghi bên Nợ (GTGT đầu vào 133)", "co": "Thuế ghi bên Có (GTGT đầu ra 3331)"}


class QuyTacHachToan(Base):
    """Một dòng quy ước: gặp nghiệp vụ thế này thì ghi Nợ tài khoản này – Có tài khoản kia."""
    __tablename__ = "quy_tac_hach_toan"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(40), index=True)          # TOUR_DOANH_THU – không unique vì có nhiều bản theo ngày hiệu lực
    ten: Mapped[str] = mapped_column(String(200))
    nguon: Mapped[str] = mapped_column(String(20), index=True)       # xem NGUON
    dieu_kien: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {"ma_bat_dau": ["KLE"], "chua": ["visa"], "khong_chua": [...], "loai_tour": [...], "muc_chi": [...]}
    tk_no: Mapped[str] = mapped_column(String(10))
    tk_co: Mapped[str] = mapped_column(String(10))
    tk_thue: Mapped[str] = mapped_column(String(10), default="")
    ben_thue: Mapped[str] = mapped_column(String(4), default="")     # no / co
    ty_le_thue: Mapped[float] = mapped_column(Float, default=0)      # 0.08 / 0.10 – 0 là không tách thuế
    doi_tuong: Mapped[str] = mapped_column(String(20), default="")   # xem DOI_TUONG
    can_cong_trinh: Mapped[bool] = mapped_column(Boolean, default=False)   # bắt buộc mã tour
    dien_giai: Mapped[str] = mapped_column(String(200), default="")  # mẫu diễn giải, {ma} {ten} {khach}
    uu_tien: Mapped[int] = mapped_column(Integer, default=100)       # số nhỏ xét trước
    can_cu: Mapped[str] = mapped_column(String(200), default="")     # điều khoản TT99 / quyết định nội bộ
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Hiệu lực và chữ ký – y hệt bảng tham số chính sách
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending / active / rejected / ngung
    signed_chutich: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_tgd: Mapped[bool] = mapped_column(Boolean, default=False)
    proposed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ThieuGiaVon(Base):
    """Hàng đợi cổng chặn: đơn có doanh thu mà chưa có giá vốn thì không được ghi doanh thu.

    Mọi đơn đều có doanh thu và giá vốn (quyết định 08/9/2026 của Chủ tịch). Thiếu giá vốn là
    thiếu dữ liệu, không phải bản chất khác – nên đơn nằm chờ ở đây cho tới khi Điều hành nhập đủ.
    """
    __tablename__ = "thieu_gia_von"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma_don: Mapped[str] = mapped_column(String(60), unique=True, index=True)   # mã tour / mã dịch vụ lẻ
    ky: Mapped[str] = mapped_column(String(7), default="", index=True)         # 2026-08
    ten: Mapped[str] = mapped_column(String(300), default="")
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ly_do: Mapped[str] = mapped_column(String(200), default="")   # thieu_gia_von / thieu_dien_giai / gia_von_am
    phong_ban: Mapped[str] = mapped_column(String(40), default="dieu_hanh")
    nguoi_phu_trach: Mapped[str] = mapped_column(String(120), default="")
    trang_thai: Mapped[str] = mapped_column(String(20), default="cho")         # cho / da_bo_sung / bo_qua
    giai_trinh: Mapped[str] = mapped_column(Text, default="")
    nguoi_xu_ly: Mapped[str] = mapped_column(String(50), default="")
    xu_ly_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    phat_hien_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
