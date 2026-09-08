"""K6 – sổ SỰ KIỆN KỸ THUẬT: chỗ robot Kiểm soát đọc được máy chủ có lỗi hay không.

Vì sao cần: ngày 07/9/2026 endpoint /meta trả 500 cho MỌI vai trò trên hệ thống thật, và thứ tìm ra nó
là bộ quét vai trò – tức là tìm ra do may, không phải do có ai theo dõi. Robot đang giám sát được số
liệu của các phòng ban nhưng mù hoàn toàn với sức khỏe của chính máy chủ.

Một bảng lỗi ghi mỗi lần một dòng sẽ tự nó thành đống rác: một endpoint hỏng gọi một nghìn lần là một
nghìn dòng giống hệt nhau. Nên bảng này GOM theo `ma` ổn định (loại + đường dẫn + đầu thông báo) và
đếm số lần, giống cách ngoại lệ chống nhân bản.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

LOAI_SU_KIEN = {
    "loi_5xx": "Máy chủ lỗi 5xx",
    "cham": "Đường dẫn chạy chậm bất thường",
    "tac_vu_nen": "Tác vụ nền thất bại",
    "khoi_dong": "Khởi động máy chủ / nâng cấp cơ sở dữ liệu",
}
MUC_SU_KIEN = {"do": "Nghiêm trọng", "vang": "Cần rà soát", "xanh": "Ghi nhận"}


class SuKienKyThuat(Base):
    __tablename__ = "su_kien_ky_thuat"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(200), unique=True, index=True)   # khóa gom, chống nhân bản
    loai: Mapped[str] = mapped_column(String(16), index=True)
    muc: Mapped[str] = mapped_column(String(6), default="vang")
    duong_dan: Mapped[str] = mapped_column(String(200), default="")
    phuong_thuc: Mapped[str] = mapped_column(String(8), default="")
    ma_trang_thai: Mapped[int] = mapped_column(Integer, default=0)
    mili_giay: Mapped[int] = mapped_column(Integer, default=0)              # lần chậm nhất đã ghi nhận
    vai_tro: Mapped[str] = mapped_column(String(30), default="")
    thong_bao: Mapped[str] = mapped_column(Text, default="")
    # Dấu vết chỉ giữ phần cuối và KHÔNG kèm dữ liệu người dùng: bảng này để chẩn đoán, không phải nơi
    # rò rỉ số liệu nghiệp vụ ra một chỗ có quyền xem rộng hơn.
    dau_vet: Mapped[str] = mapped_column(Text, default="")
    so_lan: Mapped[int] = mapped_column(Integer, default=1)
    lan_dau: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    lan_cuoi: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    da_bao: Mapped[bool] = mapped_column(Boolean, default=False)            # robot đã đưa vào phát hiện
    chi_tiet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
