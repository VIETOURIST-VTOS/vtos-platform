"""Nhật ký giữ chỗ — vì sao một chỗ ngồi bị giữ, bị trả về, hay được giữ lại lần nữa.

VẤN ĐỀ BẢNG NÀY SINH RA ĐỂ GIẢI

Trước 11/9/2026, một booking chiếm chỗ của tour ngay khi được tạo và giữ chỗ ấy VĨNH VIỄN cho tới khi
có người vào huỷ tay. Hệ quả: khách gọi giữ chỗ rồi im, sale quên, và tour hiện "hết chỗ" trong khi
thực tế không ai trả đồng nào. Số chỗ còn lại trên màn hình là số SAI — sai theo hướng nguy hiểm nhất,
vì nó làm công ty từ chối khách thật.

Cảnh báo `chua_coc` đã có từ trước, nhưng cảnh báo chỉ nói; nó không trả chỗ về. Một con số sai mà có
người được nhắc vẫn là một con số sai.

BA QUYẾT ĐỊNH ĐÁNG GHI LẠI

MỘT — HẾT HẠN GIỮ CHỖ KHÔNG PHẢI LÀ HUỶ BOOKING. Hết hạn chỉ nói "chỗ này thôi không giữ nữa"; booking
vẫn sống, vẫn tra cứu được, khách trả tiền muộn thì lấy lại chỗ nếu còn. Huỷ booking là quyết định của
người: có phí huỷ, có lý do, có tiền bảo lưu đi kèm. Gộp hai chuyện làm một là để robot tự ý xoá cam kết
với khách, và đó là việc robot không được làm.

HAI — CÓ TIỀN VÀO THÌ KHÔNG HẾT HẠN. Khách đã đặt cọc, dù chỉ một phần, là đã có cam kết; chỗ ấy thuộc
về họ cho tới deadline hủy chỗ. Chỉ booking CHƯA THU ĐỒNG NÀO mới rơi vào diện trả chỗ.

BA — GIA HẠN PHẢI CÓ NGƯỜI KÝ, CÓ LÝ DO, VÀ ĐẾM ĐƯỢC. Gia hạn là chuyện bình thường (khách hẹn mai
chuyển). Gia hạn năm lần liên tiếp không phải chuyện bình thường — đó là một chỗ bị giữ chết dưới danh
nghĩa hợp lệ. Bảng này đếm, để người quản lý nhìn thấy điều ấy thay vì phải đoán.
"""
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class NhatKyGiuCho(Base):
    """Mỗi dòng là MỘT lần trạng thái giữ chỗ của booking đổi, kèm ai làm và vì sao.

    Không sửa, không xoá dòng nào: đây là chỗ trả lời câu "vì sao tour này còn chỗ / hết chỗ vào ngày ấy".
    """
    __tablename__ = "nhat_ky_giu_cho"
    __table_args__ = (Index("ix_nhat_ky_giu_cho_booking_luc", "booking_id", "luc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    viec: Mapped[str] = mapped_column(String(20))
    # dat_han   – đặt hạn giữ chỗ lúc tạo booking
    # gia_han   – người có thẩm quyền dời hạn ra sau
    # het_han   – robot trả chỗ về vì quá hạn mà chưa thu đồng nào
    # khoi_phuc – khách trả tiền muộn (hoặc người quyết định), chỗ được giữ lại

    han_cu: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    han_moi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    so_cho: Mapped[int | None] = mapped_column(Integer, nullable=True)   # số khách của booking LÚC ẤY –
    # chép lại chứ không đọc lại về sau, vì booking có thể đổi số khách và khi đó dòng nhật ký sẽ kể sai
    # chuyện đã xảy ra.

    ly_do: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
