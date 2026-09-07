"""Việc XỬ LÝ một ngoại lệ – bảng duy nhất phải thêm cho màn hình "Ngoại lệ cần xử lý".

Bản thân ngoại lệ KHÔNG được chép sang bảng riêng. Nó đã nằm sẵn ở chỗ nó xảy ra: nhật ký bất biến,
cờ trên chuyến, bảng miễn nộp visa, bảng ngoại lệ quyền, nhật ký AI. Chép ra một bảng thứ hai thì sẽ
có ngày hai bảng nói khác nhau, và không ai biết bảng nào đúng.

Cái CHƯA có, và vì thế phải lưu ở đây, là phần con người: ai nhận việc, giải trình thế nào, đã làm gì
để nó không tái diễn, ai đóng và lúc nào. `ma` là khóa trỏ ngược về ngoại lệ gốc (xem services/ngoai_le.py),
ổn định qua mọi lần dò lại.

`nguoi_chiu_trach_nhiem` tồn tại cho đúng một tình huống: ngoại lệ mà hệ thống đã cho qua nhưng KHÔNG
ai ký. Loại đó không được đóng cho tới khi có tên một người – đóng mà không có tên thì chỉ là xóa dấu vết.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

TRANG_THAI = {
    "chua": "Chưa xử lý",
    "dang": "Đang xử lý",
    "dong": "Đã đóng",
}


class NgoaiLeXuLy(Base):
    __tablename__ = "ngoai_le_xu_ly"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(120), unique=True, index=True)   # loai#khoa – trỏ về ngoại lệ gốc
    trang_thai: Mapped[str] = mapped_column(String(8), default="chua", index=True)
    nguoi_nhan: Mapped[str] = mapped_column(String(50), default="")
    nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Tên người chịu trách nhiệm về chính ngoại lệ đó. Với ngoại lệ có chữ ký sẵn thì để rỗng (đã biết);
    # với ngoại lệ không ai ký thì đây là bắt buộc trước khi đóng.
    nguoi_chiu_trach_nhiem: Mapped[str] = mapped_column(String(80), default="")
    giai_trinh: Mapped[str] = mapped_column(Text, default="")              # vì sao đã phải bẻ quy tắc
    da_lam: Mapped[str] = mapped_column(Text, default="")                  # đã làm gì để không tái diễn
    dong_boi: Mapped[str] = mapped_column(String(50), default="")
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    so_lan_ghi: Mapped[int] = mapped_column(Integer, default=0)
