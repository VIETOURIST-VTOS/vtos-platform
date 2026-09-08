"""K1 + K2 – sổ rà soát CỘT TIỀN của robot Kiểm soát.

Vì sao phải có một bảng chứ không chỉ một phép thử in ra màn hình: lệnh yêu cầu bộ kiểm "phân biệt cột
tiền với cột không phải tiền, và chỗ nào KHÔNG CHẮC thì liệt kê ra để NGƯỜI QUYẾT, không tự xếp loại".
Nếu không lưu quyết định của người ở đâu cả thì mỗi lần quét robot lại hỏi lại đúng những cột ấy, và
câu "số cột giảm dần qua từng đợt sửa" – tiêu chí nghiệm thu của K1 – không đo được.

Vậy nên: robot ĐỀ XUẤT xếp loại theo tên cột, người XÁC NHẬN, và cột nào người đã quyết thì lần quét
sau không hỏi lại. Đúng ranh giới 2 của lệnh: robot mở việc, đóng lại là quyền của người.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

XEP_LOAI = {"tien": "Là tiền", "khong_tien": "Không phải tiền", "chua_ro": "Chưa rõ – cần người quyết"}
# Quyết định của người ở K2: cột tiền đang mặc định 0 thì sửa cho phép rỗng, hay giữ vì 0 là số thật.
QUYET_K2 = {"": "Chưa quyết", "sua": "Phải sửa – cho phép rỗng", "giu": "Giữ – 0 ở đây là số thật"}


class KsCotTien(Base):
    """Một dòng cho mỗi cột số thực trong toàn bộ mô hình dữ liệu.

    `xep_may` là ĐỀ XUẤT của robot đọc từ tên cột; `quyet_nguoi` mới là câu trả lời có giá trị. Hai cột
    tách rời nhau để về sau còn đo được robot đoán đúng bao nhiêu phần trăm – gộp làm một thì mất luôn
    khả năng đó.
    """
    __tablename__ = "ks_cot_tien"
    __table_args__ = (UniqueConstraint("bang", "cot", name="uq_ks_cot_tien_bang_cot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    bang: Mapped[str] = mapped_column(String(80), index=True)
    cot: Mapped[str] = mapped_column(String(80))
    kieu: Mapped[str] = mapped_column(String(40), default="")          # Float / Numeric / …
    xep_may: Mapped[str] = mapped_column(String(12), default="chua_ro")
    ly_do_may: Mapped[str] = mapped_column(String(200), default="")    # robot dựa vào đâu mà xếp thế
    quyet_nguoi: Mapped[str] = mapped_column(String(12), default="")   # "" / tien / khong_tien
    quyet_boi: Mapped[str] = mapped_column(String(50), default="")
    quyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # --- phần của K2: "thiếu ≠ 0" ---
    cho_rong: Mapped[bool] = mapped_column(Boolean, default=False)     # cột có cho phép RỖNG không
    mac_dinh_0: Mapped[bool] = mapped_column(Boolean, default=False)   # đang khai giá trị mặc định 0
    quyet_k2: Mapped[str] = mapped_column(String(6), default="")       # "" / sua / giu
    quyet_k2_boi: Mapped[str] = mapped_column(String(50), default="")
    quyet_k2_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # --- vết quét ---
    lan_dau: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    lan_cuoi: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    con: Mapped[bool] = mapped_column(Boolean, default=True, index=True)   # cột còn tồn tại trong mô hình

    def xep(self) -> str:
        """Xếp loại có hiệu lực: người đã quyết thì lấy của người, chưa thì lấy đề xuất của máy."""
        return self.quyet_nguoi or self.xep_may
