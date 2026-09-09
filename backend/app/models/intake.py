"""Nhật ký nạp dữ liệu vào VTOS.

Bảng này tồn tại vì một câu hỏi sẽ được hỏi vào đúng lúc khó nhất: "con số này ở đâu ra?". Nạp hàng loạt
là lúc dữ liệu vào hệ thống nhanh nhất và ít người nhìn nhất – nên mỗi lần nạp phải để lại vết: ai nạp,
nạp loại gì, từ tệp nào, bao nhiêu dòng vào, bao nhiêu dòng bị bỏ, và MÃ BĂM của nội dung đã nạp.

Mã băm để trả lời được "lần nạp hôm đó đúng là tệp này chứ không phải tệp đã sửa sau đó".
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, JSON, Numeric
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
    # ---- Bốn con số TIỀN, soi gương bốn con số DÒNG ở trên (K5, 09/9/2026).
    #
    # Vì sao đếm dòng thôi là chưa đủ: một dòng vào đủ nhưng mang sai số tiền thì phép đếm dòng vẫn
    # khớp hoàn hảo. Bốn số dòng trả lời "có mất dòng nào không"; bốn số tiền trả lời "có mất ĐỒNG nào
    # không". Đẳng thức phải đúng: tong_tien_tep = tong_tien_da_nap + tong_tien_bo_qua + tong_tien_loi.
    #
    # Numeric chứ không Float – đây đúng là cột mà K1 sinh ra để chặn: cộng vài nghìn dòng bằng số thực
    # nhị phân là lệch vài đồng ở chỗ không ai nhìn, và cột này tồn tại CHỈ để bắt lệch.
    #
    # `cot_tien` ghi lại ĐÃ CỘNG NHỮNG CỘT NÀO. Không có nó thì bốn con số trên là bốn con số không
    # kiểm chứng được: đổi cách xếp loại cột tiền một lần là mọi lô cũ mang ý nghĩa khác mà không ai hay.
    tong_tien_tep: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_tien_da_nap: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_tien_bo_qua: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_tien_loi: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    cot_tien: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dau_vao_hash: Mapped[str] = mapped_column(String(64), default="")
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
