# -*- coding: utf-8 -*-
"""TR-8 (13/11/2026) · ALBUM ẢNH TOUR — bảng.

VÌ SAO CÓ BẢNG NÀY. Nội dung tour đọc từ `vietourist.com.vn` (Chủ tịch chốt mục 12 của KS-71),
nên chất lượng ảnh trên cổng bị chặn trần bởi web cũ: đo 13/11/2026 có 13 trong 85 tour KHÔNG
có một tấm ảnh nào, và tour có ảnh thì phần lớn là tờ rơi quảng cáo chữ cháy vào ảnh. Một tour
ba triệu không ảnh gần như không bán được qua mạng.

Đây KHÔNG phải quay lưng với mục 12. Ảnh đọc từ web vẫn giữ nguyên, không xoá dòng nào — ảnh
tải lên chỉ ĐỨNG TRƯỚC (Chủ tịch chốt 13/11/2026), nên phòng sản phẩm vá được chỗ nào hay chỗ
ấy, không phải chờ đủ bộ mới dùng được.

KHÔNG CÓ BƯỚC DUYỆT — tải là hiện, đúng bằng luật KS-16c Chủ tịch chốt cho cổng nhà hàng
31/10/2026 và nhắc lại cho cổng tour 13/11/2026. `trang_thai` vẫn còn để GỠ NHANH một tấm ảnh
sai (chuyển sang «an») mà không phải xoá hẳn.

Cột `can_cu` là cột quan trọng nhất về mặt pháp lý: ảnh này ở đâu ra, ai cho phép dùng. Đăng
ảnh không rõ nguồn lên internet thay mặt một công ty niêm yết là rủi ro thật, không phải thủ tục.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.services.anh_chung import CAN_CU_CHUNG, TRANG_THAI_CHUNG

NHOM_ANH_TOUR = {"diem_den": "Điểm đến", "luu_tru": "Nơi lưu trú", "am_thuc": "Ẩm thực",
                 "trai_nghiem": "Hoạt động · trải nghiệm", "phuong_tien": "Phương tiện",
                 "doan_khach": "Đoàn khách đã đi"}

# Dòng đầu khác cổng nhà hàng («Nhà hàng cấp quyền») vì chủ thể cấp quyền ở đây là nhà cung cấp
# dịch vụ của tour: khách sạn, khu du lịch, hãng tàu…
CAN_CU_ANH_TOUR = {"doi_tac": "Đối tác / nhà cung cấp cấp quyền", **CAN_CU_CHUNG}
TRANG_THAI_ANH_TOUR = dict(TRANG_THAI_CHUNG)

ANH_TOI_DA_SO = 40                      # mỗi sản phẩm; trang chi tiết chỉ bày 5, còn lại để xoay vòng


class AnhTour(Base):
    __tablename__ = "anh_tour"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))                   # bản gốc — chỉ nội bộ
    hien_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)   # bản hiển thị (≤1600px)
    nho_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)    # ảnh nhỏ (≤480px)
    rong: Mapped[int] = mapped_column(Integer, default=0)
    cao: Mapped[int] = mapped_column(Integer, default=0)
    nhom: Mapped[str] = mapped_column(String(20), default="")
    chu_thich: Mapped[str] = mapped_column(String(200), default="")
    mo_ta_thay_the: Mapped[str] = mapped_column(String(200), default="")   # alt — người khiếm thị và máy tìm kiếm
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    la_bia: Mapped[bool] = mapped_column(Boolean, default=False)
    can_cu: Mapped[str] = mapped_column(String(20), default="chua_xac_minh")
    can_cu_ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    credit: Mapped[str] = mapped_column(String(160), default="")
    trang_thai: Mapped[str] = mapped_column(String(12), default="da_duyet")
    tai_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
