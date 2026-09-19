# -*- coding: utf-8 -*-
"""NỐI TÀI KHOẢN VTOS VỚI ZALO (19/9/2026) — để cảnh báo tới được NGƯỜI, không chỉ tới màn hình.

VÌ SAO CẦN HAI BẢNG NÀY

Hàm gửi tin OA nhận vào một **UID Zalo**, không phải tên tài khoản VTOS. Bảng `users` không có ô
nào giữ UID Zalo, nên dù người ta đã bấm "Quan tâm" OA công ty, hệ thống vẫn không biết UID nào là
của ai — và báo động không tới được ai cả.

VÌ SAO BẢNG RIÊNG, KHÔNG THÊM CỘT VÀO `users`

`users` là bảng nóng nhất kho: mọi làn đều đọc nó, và một cột thêm vào đó là một chỗ đụng nhau.
Quan hệ này lại là một-một và rời rạc — nối được, gỡ được, phần lớn tài khoản không có — nên nó
đúng hình một bảng nối hơn là một cột.

VÌ SAO KHÔNG BẮT NGƯỜI DÙNG TỰ DÁN UID

UID Zalo không hiện ra ở đâu cho người thường thấy. Bắt dán UID nghĩa là phải có ai đó tra hộ, mà
người tra hộ ấy có thể dán nhầm UID của người khác — và từ đó cảnh báo của Chủ tịch đi tới máy
người khác mà không ai biết. Nên chiều nối phải NGƯỢC LẠI: người tự xin một mã trong VTOS rồi tự
nhắn mã ấy vào OA. Zalo nói cho mình biết UID; không ai phải gõ nó.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ZaloNoiTaiKhoan(Base):
    """Một tài khoản VTOS ↔ một UID Zalo."""
    __tablename__ = "zalo_noi_tai_khoan"
    id: Mapped[int] = mapped_column(primary_key=True)
    # MỖI BÊN DUY NHẤT. Một tài khoản chỉ một Zalo, và một Zalo chỉ một tài khoản.
    #
    # Ràng buộc thứ hai mới là ràng buộc quan trọng: thiếu nó thì một người có thể nối máy Zalo của
    # mình vào hai tài khoản, và cảnh báo dành riêng cho Chủ tịch sẽ tới một máy mà người khác cũng
    # đang cầm. Cơ sở dữ liệu chặn được chuyện ấy; một phép kiểm trong mã thì không, vì nó chỉ chạy
    # khi có ai gọi tới.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    zalo_uid: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    gan_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Ai bấm nối. Luôn là chính chủ — cửa API không cho nối hộ người khác — nhưng vẫn ghi ra, vì
    # ngày nào đó có người mở cửa "quản trị nối hộ" thì cột này là chỗ duy nhất nhìn thấy điều đó.
    gan_boi: Mapped[str] = mapped_column(String(50), default="")


class ZaloMaNoi(Base):
    """Mã dùng một lần để nối. Sống 10 phút, dùng xong là chết."""
    __tablename__ = "zalo_ma_noi"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ma: Mapped[str] = mapped_column(String(12), index=True)
    het_han: Mapped[datetime] = mapped_column(DateTime, index=True)
    da_dung: Mapped[bool] = mapped_column(Boolean, default=False)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Số lần mã này bị nhắn sai vào OA. Không dùng để khoá — xem ghi chú độ mạnh của mã ở
    # services/zalo_nguoi_dung.py — mà để ĐẾM: một con số này lớn bất thường nghĩa là có người
    # đang dò, và đó là thứ đáng biết trước khi nó thành chuyện.
    lan_sai: Mapped[int] = mapped_column(Integer, default=0)
