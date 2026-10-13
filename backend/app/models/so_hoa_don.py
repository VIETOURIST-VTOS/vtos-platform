# -*- coding: utf-8 -*-
"""SỔ SỐ NHẢY HÓA ĐƠN — Đợt E7, 13/10/2026. Một bảng giữ số cuối của từng ký hiệu.

VÌ SAO KHÔNG ĐẾM LẠI TỪ CÁC HÓA ĐƠN

Trước đợt này số hóa đơn cấp bằng `max(Invoice.number) + 1` trong `LocalInvoiceProvider.issue`.
Phép ấy sai hai cách, và cả hai đều ra HAI TỜ MANG MỘT SỐ:

  1. HAI LẦN GỌI CÙNG LÚC cùng đọc một số lớn nhất, nên cùng ra một số. Không có khoá nào.
  2. MỘT TỜ ĐÃ HỦY MANG SỐ CUỐI thì số ấy được cấp lại — `max` không phân biệt tờ còn hiệu lực
     với tờ đã hủy. Hai tờ khác nhau, một số, và tờ trước đã nằm trong tay khách.

Một bảng giữ số thì CHỈ TĂNG, không bao giờ lùi: số đã cấp là đã tiêu, kể cả khi tờ ấy sau đó
bị hủy hoặc nhà cung cấp trả lời là chưa ra. Khoảng trống trong dãy số là điều CÓ THẬT và phải
nhìn thấy được, chứ không phải điều để vá bằng cách cấp lại.

VÀ ĐÂY LÀ NƠI DUY NHẤT TRẢ LỜI ĐƯỢC CÂU KIỂM TOÁN HỎI: *số hóa đơn có liên tục không, có số nào
nhảy mất không*. Đếm lại từ các hóa đơn thì một số đã cấp mà tờ của nó không bao giờ ra sẽ biến
mất khỏi phép đếm — tức đúng cái bất thường cần thấy lại là cái không thấy được.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SoNhayHoaDon(Base):
    """Số cuối đã CẤP của một ký hiệu hóa đơn. Chỉ tăng.

    `so_cuoi` là số đã TIÊU, không phải số đang dùng: cấp số 73 rồi nhà cung cấp trả lời là chưa
    ra tờ nào thì `so_cuoi` vẫn là 73, và 73 là một khoảng trống có lý do ghi lại được.
    """

    __tablename__ = "so_nhay_hoa_don"

    series: Mapped[str] = mapped_column(String(20), primary_key=True)
    so_cuoi: Mapped[int] = mapped_column(Integer, default=0)
    cap_nhat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cap_nhat_boi: Mapped[str] = mapped_column(String(50), default="")
