"""V10 – khóa chống ghi trùng: nhớ kết quả của một lần ghi để lần gọi thứ hai không ghi lại.

Vì sao cần, và vì sao bây giờ: Chủ tịch quyết "NHẬP LÀ DÙNG LUÔN" – bỏ khâu trưởng phòng duyệt từng
dòng. Từ lúc đó, mỗi lần bấm nút là một lần ghi thật vào sổ. Mà chuyện thường ngày là: mạng chập giữa
chừng nên người dùng bấm lại, hoặc bấm hai lần vì lần đầu không thấy gì nhúc nhích.

    Không có bảng này: bấm hai lần thành hai lô. Với bộ nạp có khóa chống trùng theo dòng thì lần hai
    chỉ tạo thêm một dòng nhật ký thừa. Với bộ nạp KHÔNG có khóa – "mỗi dòng là một đơn mới" – thì lần
    hai tạo thêm nguyên một lô đơn hàng, và không ai biết cho tới lúc đối chiếu công nợ.

CÁCH DÙNG – khóa đến từ đâu:

    1. Người gọi gửi khóa. Giao diện sinh một khóa cho MỘT lần bấm nút và gửi kèm ở đầu đề
       "X-Khoa-Ghi". Bấm lại cùng nút, cùng khóa – máy chủ trả lại kết quả cũ. Đây là cách đúng.
    2. Không có khóa thì suy từ nội dung, và CHỈ trong một cửa sổ ngắn. Suy từ nội dung mà không giới
       hạn thời gian là sai: nạp đúng cùng một tệp hai tháng sau có thể là việc thật – ví dụ đã xóa
       nhầm rồi nạp lại. Cửa sổ ngắn bắt đúng cái nó nhắm tới (bấm hai lần, mạng chập) và không cản
       việc thật.

Bảng này lưu CẢ NỘI DUNG TRẢ VỀ, không chỉ lưu dấu "đã chạy rồi". Nếu chỉ lưu dấu thì lần gọi thứ hai
biết là trùng nhưng không nói được kết quả lần đầu ra sao, và người dùng vẫn phải đi tra tay – tức là
chưa giải quyết gì.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class KhoaGhi(Base):
    __tablename__ = "khoa_ghi"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Khóa duy nhất TOÀN BẢNG chứ không duy nhất theo người: hai người khác nhau gửi cùng một khóa là
    # lỗi của bên gọi, và nuốt im lặng thì lần sau khó tìm hơn nhiều.
    khoa: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    duong_dan: Mapped[str] = mapped_column(String(200), default="")
    phuong_thuc: Mapped[str] = mapped_column(String(10), default="POST")
    boi: Mapped[str] = mapped_column(String(50), default="")
    trang_thai: Mapped[int] = mapped_column(Integer, default=200)
    tra_ve: Mapped[str] = mapped_column(Text, default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


Index("ix_khoa_ghi_duong_dan_luc", KhoaGhi.duong_dan, KhoaGhi.luc)
