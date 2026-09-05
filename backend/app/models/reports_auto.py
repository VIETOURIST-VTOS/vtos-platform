"""Báo cáo tự động do robot R7 sinh (ngày / tuần / tháng) kèm nhận xét."""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class AutoReport(Base):
    __tablename__ = "auto_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)      # ngay / tuan / thang
    period: Mapped[str] = mapped_column(String(12), index=True)    # 2026-09-05 / 2026-W36 / 2026-09
    content: Mapped[str] = mapped_column(Text, default="")         # markdown
    comment: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(50), default="robot")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
