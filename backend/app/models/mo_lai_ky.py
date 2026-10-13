"""Hồ sơ MỞ LẠI một kỳ kế toán đã khóa — Đợt E6, 13/10/2026.

MỘT BẢNG RIÊNG, KHÔNG THÊM CỘT VÀO `period_locks`. Hai lẽ:

  1. `period_locks` là trạng thái HIỆN TẠI của một kỳ — có khóa hay không. Việc mở lại là một
     SỰ KIỆN có người trình, người ký, lý do và thời điểm; nhét nó vào bảng trạng thái thì kỳ
     mở lại lần thứ hai sẽ đè mất dấu vết lần thứ nhất.
  2. Khi Chủ tịch ký, dòng `period_locks` bị XOÁ (kỳ mở ra thật). Nếu dấu vết nằm trong dòng ấy
     thì nó biến mất đúng lúc cần nhất.

Bảng này vì thế KHÔNG BAO GIỜ XOÁ dòng nào: một kỳ mở lại ba lần là ba dòng, đọc từ trên xuống
ra đúng câu chuyện đã xảy ra.
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# cho_ky → da_ky → da_khoa_lai, hoặc cho_ky → tu_choi. Không có đường nào quay ngược.
TRANG_THAI = {
    "cho_ky": "Chờ Chủ tịch ký",
    "da_ky": "ĐANG MỞ LẠI – chưa khóa lại",
    "tu_choi": "Chủ tịch từ chối",
    "da_khoa_lai": "Đã khóa lại",
}


class MoLaiKy(Base):
    """Một lần xin mở lại một kỳ. Hai chữ ký, một lý do, và dấu vết của cả hai đầu."""

    __tablename__ = "mo_lai_ky"
    __table_args__ = (Index("ix_mo_lai_ky_tt_ky", "trang_thai", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), index=True)

    # Lý do là BẮT BUỘC ở tầng dịch vụ (tối thiểu 30 ký tự), không chặn bằng ràng buộc cột: câu
    # từ chối phải nói ra được bằng tiếng người, mà một ràng buộc cột chỉ ném ra lỗi cơ sở dữ liệu.
    ly_do: Mapped[str] = mapped_column(String(500), default="")
    # KHÔNG đặt `index=True` ở đây: chỉ mục ghép `ix_mo_lai_ky_tt_ky` ở trên đã mở đầu bằng cột
    # này, nên một chỉ mục riêng cho nó là chỉ mục thừa — và bản đầu của đợt này đặt cả hai, lúc ấy
    # SQLAlchemy sinh đúng một tên `ix_mo_lai_ky_trang_thai` cho hai chỉ mục khác nhau và
    # `create_all` đổ ngay ở phép thử đầu tiên. Ghi lại vì cái đổ ấy rẻ, còn nếu nó lọt qua thì
    # bản di trú và metadata sẽ lệch nhau lặng lẽ.
    trang_thai: Mapped[str] = mapped_column(String(16), default="cho_ky")

    trinh_boi: Mapped[str] = mapped_column(String(50), default="")
    trinh_vai: Mapped[str] = mapped_column(String(24), default="")
    trinh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ky_boi: Mapped[str] = mapped_column(String(50), default="")
    ky_vai: Mapped[str] = mapped_column(String(24), default="")
    ky_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tu_choi_ly_do: Mapped[str] = mapped_column(String(500), default="")

    # Khóa CŨ bị gỡ ra lúc ký — chép lại ở đây, vì dòng `period_locks` ấy bị xoá.
    khoa_cu_boi: Mapped[str] = mapped_column(String(50), default="")
    khoa_cu_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    khoa_cu_ghi_chu: Mapped[str] = mapped_column(String(200), default="")

    khoa_lai_boi: Mapped[str] = mapped_column(String(50), default="")
    khoa_lai_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
