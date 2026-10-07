"""Đợt B – SỔ SỰ KIỆN THU NHẬP: ai đã được trả khoản gì, vì căn cứ nào, trong kỳ nào.

VẤN ĐỀ BẢNG NÀY GIẢI

Trước bản này, mọi khoản thu nhập biến đổi đều được TÍNH LẠI TỪ ĐẦU mỗi lần chạy bảng lương, và dấu
vết duy nhất còn lại là một dòng chữ trong ô `ten` của JSON — thứ con người đọc được còn máy thì
không. Hệ quả: hệ thống KHÔNG CÓ CÁCH NÀO trả lời câu "người này đã được trả khoản này chưa".

Câu ấy quan trọng vì mọi khoản biến đổi đều gắn với một CĂN CỨ ở ngoài bảng lương — một chuyến đã
quyết toán, một quỹ của tháng, một lượt chỉ tiêu. Căn cứ nằm ngoài thì nó đổi được sau khi kỳ lương
đã ký: chuyến chốt lại, booking đổi người phụ trách, quỹ tính lại. Mỗi lần như thế là một lần cùng
một căn cứ có thể chảy vào hai kỳ lương, và không ai thấy — vì không có chỗ nào ghi lần thứ nhất.

VÌ SAO GHI LÚC KÝ, KHÔNG GHI LÚC NHÁP

Bản nháp tính lại nhiều lần trong ngày; ghi từ nháp thì sổ đầy dòng chưa ai trả và chính kỳ ấy sẽ tự
chặn mình ở lần tính thứ hai. Sổ này chỉ nhận dòng tại đúng lúc có chữ ký, trong cùng giao dịch với
`luong_khoa.khoa` — tức là nó ghi THỨ ĐÃ ĐƯỢC KÝ, không ghi thứ đang bàn.

KHOÁ DUY NHẤT LÀ MỘT HÀNG RÀO, KHÔNG PHẢI MỘT PHÉP KIỂM

`ux_su_kien_thu_nhap` trên (ma_nv, loai, can_cu) làm cơ sở dữ liệu từ chối dòng thứ hai. Phép kiểm
ở `kiem_co_so` nói ra chỗ trùng TRƯỚC khi ký để người xử lý; khoá duy nhất bắt chỗ trùng mà phép
kiểm không thấy — hai thứ khác nhau, và chỉ có cái sau là không vòng qua được.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN


class SuKienThuNhap(Base):
    """Một khoản thu nhập biến đổi ĐÃ ĐƯỢC KÝ, kèm căn cứ máy đọc được."""
    __tablename__ = "su_kien_thu_nhap"
    __table_args__ = (
        # Cùng một người, cùng một loại khoản, cùng một căn cứ – CHỈ MỘT LẦN, dù ở kỳ nào.
        Index("ux_su_kien_thu_nhap", "ma_nv", "loai", "can_cu", unique=True),
        Index("ix_su_kien_thu_nhap_ky", "period"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    ban_khoa_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ma_nv: Mapped[str] = mapped_column(String(20), index=True)
    loai: Mapped[str] = mapped_column(String(30), index=True)      # khoá trong LOAI_KHOAN
    can_cu: Mapped[str] = mapped_column(String(80), index=True)    # căn cứ kinh tế, máy đọc được
    so_tien: Mapped[float | None] = mapped_column(TIEN)            # K2: rỗng ≠ 0
    # Các vật thể ở ngoài đã nuôi con số này: mã chuyến, mã hồ sơ visa, mã lệnh điều xe.
    # Đây là thứ bắt được chỗ trùng mà `can_cu` không bắt được: căn cứ theo tháng thì hai tháng là
    # hai căn cứ khác nhau, nhưng CÙNG MỘT CHUYẾN nằm trong căn cứ của cả hai tháng là chuyện sai.
    nguon: Mapped[list] = mapped_column(JSON, default=list)
    dien_giai: Mapped[str] = mapped_column(Text, default="")
    ghi_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
