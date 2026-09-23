# -*- coding: utf-8 -*-
"""SỔ GỬI BÁO ĐỘNG — 19/9/2026. Ghi lại TỪNG LẦN GỬI, kể cả lần không gửi được.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO PHẢI CÓ BẢNG NÀY, VÀ VÌ SAO NÓ GHI CẢ THẤT BẠI
──────────────────────────────────────────────────────────────────────────────────────────────

Bảng `alerts` trả lời "có cảnh báo gì". Nó KHÔNG trả lời được câu quan trọng hơn: **cảnh báo ấy
có tới được người không.**

Hai câu ấy khác nhau đúng ở chỗ làm hỏng mọi hệ báo động: gửi thành công tới một chiếc điện thoại
đang tắt vẫn là "gửi thành công". Một người chưa nối Zalo thì hệ hoàn toàn có thể báo "đã gửi cho
3/3 lãnh đạo" trong khi thực ra chỉ có 2 máy kêu — và không ai biết người thứ ba chưa bao giờ nhận
được gì.

Nên mỗi hàng ở đây là MỘT LẦN GỬI cho MỘT NGƯỜI trên MỘT KÊNH, và `thanh_cong=False` kèm `ly_do`
là hàng QUAN TRỌNG NHẤT của bảng. "chua_noi_zalo", "chua_cau_hinh_zns", "chua_co_email" — ba lý do
ấy nói rằng hệ thống đang mù một mảng, và chúng phải ĐẾM ĐƯỢC chứ không được im lặng bỏ qua.

VÌ SAO KHÔNG GỘP VÀO `alerts`

Một cảnh báo sinh ra NHIỀU lần gửi: ba người × bốn kênh × hai vòng. Nhét vào `alerts` là nhét một
quan hệ một-nhiều vào một hàng — hoặc thành mười sáu cột rỗng, hoặc thành một chuỗi JSON không đếm
được. Cả hai đều là cách để phép đo cuối tháng không làm được.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Vòng gửi. Số là SỐ PHÚT kể từ lúc cảnh báo sinh ra, không phải số thứ tự — để đọc nhật ký là
# hiểu ngay "hàng này là lần báo đầu hay lần đánh thức thêm người".
VONG_DAU = 0


class CanhBaoGui(Base):
    """Một lần gửi một cảnh báo cho một người trên một kênh."""
    __tablename__ = "canh_bao_gui"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # "chuong" · "zalo_oa" · "email" · "zns". Chuỗi chứ không phải Enum: thêm một kênh là việc
    # thường, và một bản di trú đổi Enum trên Postgres là một lần khoá bảng không cần thiết.
    kenh: Mapped[str] = mapped_column(String(16), index=True)
    # Số phút kể từ lúc cảnh báo sinh ra: 0 = báo ngay, 15 = vòng đánh thức thêm người.
    vong: Mapped[int] = mapped_column(Integer, default=VONG_DAU, index=True)
    gui_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    thanh_cong: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # BẮT BUỘC có khi thất bại. Một cột `thanh_cong=False` mà không nói vì sao thì đúng bằng không
    # có gì: người đọc bảng không phân biệt được "Zalo lỗi mạng" với "người này chưa nối máy" —
    # một cái là sự cố, một cái là việc còn thiếu, và hai cái cần hai cách xử lý khác hẳn nhau.
    ly_do: Mapped[str] = mapped_column(String(200), default="")
    # Mã tin bên nhà cung cấp trả về, để đối soát khi họ bảo "đã gửi" mà máy không kêu.
    ma_ngoai: Mapped[str] = mapped_column(String(80), default="")
