"""Nhật ký nạp dữ liệu vào VTOS.

Bảng này tồn tại vì một câu hỏi sẽ được hỏi vào đúng lúc khó nhất: "con số này ở đâu ra?". Nạp hàng loạt
là lúc dữ liệu vào hệ thống nhanh nhất và ít người nhìn nhất – nên mỗi lần nạp phải để lại vết: ai nạp,
nạp loại gì, từ tệp nào, bao nhiêu dòng vào, bao nhiêu dòng bị bỏ, và MÃ BĂM của nội dung đã nạp.

Mã băm để trả lời được "lần nạp hôm đó đúng là tệp này chứ không phải tệp đã sửa sau đó".
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class IntakeRun(Base):
    __tablename__ = "intake_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(40))               # mã bộ nạp: nha_cung_cap, chuyen_xe…
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    nguon: Mapped[str] = mapped_column(String(40), default="nguoi_nhap")   # nguoi_nhap / ai / he_thong
    tac_nhan: Mapped[str] = mapped_column(String(80), default="")          # tên người hoặc tên tác vụ AI
    so_dong: Mapped[int] = mapped_column(Integer, default=0)
    da_nap: Mapped[int] = mapped_column(Integer, default=0)
    bo_qua_da_co: Mapped[int] = mapped_column(Integer, default=0)
    dong_loi: Mapped[int] = mapped_column(Integer, default=0)
    bo_qua_dong_loi: Mapped[bool] = mapped_column(Boolean, default=False)
    dau_vao_hash: Mapped[str] = mapped_column(String(64), default="")
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
