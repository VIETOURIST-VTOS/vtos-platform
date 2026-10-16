# -*- coding: utf-8 -*-
"""Đợt R3b 17/10/2026 — DANH MỤC BỘ PHẬN.

VÌ SAO CÓ BẢNG NÀY, ĐO ĐƯỢC TRƯỚC KHI VIẾT

Trước đợt này, bộ phận trong hệ thống là CHỮ TỰ DO: `Asset.department` khai `String(20)` không
bảng, không ràng buộc, và Đợt R3a vừa thêm `JournalLine.bo_phan` cũng vậy. Hệ quả im lặng: "cntt",
"CNTT" và "IT" là BA bộ phận khác nhau trong mắt mọi phép gom. Dựng báo cáo theo bộ phận trên nền
ấy là dựng một bảng trông đúng mà cộng sai — và cộng sai kiểu này không báo lỗi, chỉ ra ba dòng
nhỏ thay vì một dòng đúng.

BÚT DANH, VÀ VÌ SAO KHÔNG SỬA SỔ

Chữ cũ đã nằm trong sổ không được viết đè. "cntt → BP_CNTT" là một quyết định của người HÔM NAY áp
lên những dòng ĐÃ GHI, mà kỳ đã khoá thì không ai được sửa — đó là lẽ của việc khoá sổ. Nên chữ cũ
vào `but_danh` của bộ phận, báo cáo tra ngược qua đó; sổ giữ nguyên chữ nó đã ghi. Đảo lại một
quyết định gán nhầm chỉ là xoá một bút danh, chứ không phải dựng lại sổ.

RANH GIỚI 09/9/2026 — bảng này là CỬA TAY. Tám dòng nạp sẵn là khuôn cơ cấu, không phải số liệu:
HCNS sửa tên, thêm, hoặc ngừng dùng qua `/api/v1/hach-toan/bo-phan`. `nap_mac_dinh` chạy được
nhiều lần và KHÔNG đè lên dòng người đã sửa.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class BoPhan(Base):
    """Một bộ phận. `ma` là thứ `JournalLine.bo_phan` và `Asset.department` trỏ vào."""
    __tablename__ = "bo_phan"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(200))
    thu_tu: Mapped[int] = mapped_column(Integer, default=100)
    # KHÔNG có cột `nhom` như danh mục khoản mục. Khoản mục cần nhóm vì báo cáo tài chính đòi tách
    # giá vốn với chi phí bán hàng; bộ phận thì không gom theo tầng nào cả — thêm một cột rỗng chỉ
    # để cho giống là thêm một ô người ta phải điền mà không ai đọc.
    # `dung = False` là NGỪNG DÙNG, không phải xoá: bút toán cũ vẫn trỏ vào mã này.
    dung: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Chữ cũ đã nằm trong sổ, mỗi dòng một chữ. Báo cáo tra ngược qua đây thay vì sửa sổ.
    but_danh: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
