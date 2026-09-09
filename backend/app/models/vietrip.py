"""Đồng bộ Vietrip → VTOS: bảng trung gian (staging) giữ nguyên dữ liệu gốc + bảng dòng chi phí quyết toán tour (bổ sung theo cấu trúc Vietrip)."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


class VtRecord(Base):
    """Bản ghi Vietrip thô: entity (tour/booking/receipt/supplier_payment/user/vehicle/proposal/settlement), vietrip_id, raw JSON. Idempotent."""
    __tablename__ = "vt_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(30), index=True)
    vietrip_id: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(60), default="", index=True)   # tourcode / bookingID để tra chéo
    on_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)          # đã ánh xạ sang bảng nghiệp vụ VTOS
    apply_note: Mapped[str] = mapped_column(String(200), default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class TourCostLine(Base):
    """Dòng chi phí dự toán / quyết toán của tour (theo mẫu bảng quyết toán Vietrip): mô tả, loại DV, NCC (MST), đơn giá, SL, hệ số, thực chi, đã thanh toán."""
    __tablename__ = "tour_cost_lines"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(200))
    cost_kind: Mapped[str] = mapped_column(String(20), default="co_dinh")   # co_dinh / theo_khach
    service_type: Mapped[str] = mapped_column(String(30), default="")        # GUIDE / HOTEL / LAND / BUS / MEAL / TICKET / VISA / INS…
    supplier_name: Mapped[str] = mapped_column(String(200), default="")
    supplier_tax_code: Mapped[str] = mapped_column(String(20), default="")
    unit_price: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    qty: Mapped[float] = mapped_column(Float, default=0)
    coef: Mapped[float] = mapped_column(Float, default=1)
    actual: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    paid: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(20), default="vietrip")
    budget: Mapped[float | None] = mapped_column(TIEN)                 # dự toán của dòng (để so lệch, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="hd")           # hd (hiệu lực) / huy
    version: Mapped[int] = mapped_column(Integer, default=1)                # phiên bản quyết toán khi tạo/sửa dòng
    doc_name: Mapped[str] = mapped_column(String(160), default="")          # tên tệp chứng từ
    doc_data: Mapped[str] = mapped_column(Text, default="")                 # data URL (ảnh/PDF ≤ 1,5 MB)
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
