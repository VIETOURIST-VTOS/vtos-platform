"""Bia mộ tài khoản — giữ tên đăng nhập → họ tên sau khi tài khoản bị xoá.

VÌ SAO BẢNG NÀY PHẢI CÓ TRƯỚC KHI CÓ NÚT XOÁ

Nhật ký nghiệp vụ của VTOS ghi người làm bằng TÊN ĐĂNG NHẬP dạng chữ, không phải khoá ngoại. Hệ
quả đã ghi từ TC-75 (19/9/2026): xoá một tài khoản thì nhật ký KHÔNG gãy — nó vẫn chạy, vẫn in ra
đủ dòng, chỉ là mỗi dòng trỏ tới một cái tên không còn tra ra ai. Im lặng mà sai, đúng kiểu hỏng
khó tìm nhất: ba tháng sau có người mở nhật ký ra soát một khoản chi và thấy `nv.thao` đã ký duyệt,
mà `nv.thao` không còn trong hệ thống và không ai nhớ đó là ai.

Bảng này là cái duy nhất làm cho nút xoá trở nên chấp nhận được. Mỗi lần xoá để lại đúng một dòng
ở đây, và dòng ấy KHÔNG BAO GIỜ bị xoá — nó không có cửa xoá, và cố ý.

KHÔNG PHẢI MỘT BẢN SAO CỦA `users`. Nó giữ đúng những gì cần để tra ngược một cái tên trong nhật
ký: tên đăng nhập, họ tên, mã nhân viên, vai lúc xoá. Không giữ mật khẩu, không giữ liên hệ,
không giữ gì có thể dùng để dựng lại tài khoản — xoá là xoá, bảng này chỉ để ĐỌC HIỂU quá khứ.

TÊN ĐĂNG NHẬP KHÔNG ĐẶT DUY NHẤT ở đây, và đó là chủ ý. Một tên đăng nhập có thể được cấp lại cho
người khác sau này (hiếm, nhưng có thật khi HC-NS dùng quy tắc đặt tên theo họ tên). Ràng buộc duy
nhất sẽ chặn đúng lần xoá thứ hai, tức là chặn việc ghi lại sự thật. Muốn biết dòng nhật ký nào
thuộc lần nào thì so `xoa_luc` với thời điểm của dòng nhật ký.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TaiKhoanDaXoa(Base):
    """Một tài khoản đã bị xoá. Dòng này không có cửa xoá — xem ghi chú đầu tệp."""
    __tablename__ = "tai_khoan_da_xoa"
    id: Mapped[int] = mapped_column(primary_key=True)
    # `users.id` cũ. KHÔNG phải khoá ngoại: hàng đã biến mất, khoá ngoại sẽ chặn chính việc ghi này.
    user_id_cu: Mapped[int] = mapped_column(Integer, index=True)
    tai_khoan: Mapped[str] = mapped_column(String(50), index=True)
    ho_ten: Mapped[str] = mapped_column(String(160))
    ma_nv: Mapped[str] = mapped_column(String(30), default="")
    vai: Mapped[str] = mapped_column(String(30), default="")
    # Rỗng nghĩa là xoá thẳng, không qua bước gộp. Có tên nghĩa là dữ liệu của người này đã chuyển
    # sang tài khoản ấy trước khi xoá — chỗ để người đọc nhật ký đi tiếp.
    da_gop_vao: Mapped[str] = mapped_column(String(50), default="")
    ly_do: Mapped[str] = mapped_column(Text, default="")
    xoa_boi: Mapped[str] = mapped_column(String(50))
    xoa_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
