# -*- coding: utf-8 -*-
"""SỔ GÁN NGƯỜI BÁN cho kho quyết toán cũ T1–T6/2026.

VÌ SAO CẦN MỘT BẢNG RIÊNG, KHÔNG GÁN THẲNG LÚC NẠP

Cột SALES trong 604 tệp Excel ghi TÊN NGƯỜI, không ghi mã nhân viên. Đo ngày 13/9/2026 trên toàn bộ
kho: 18.162 dòng khách, 14.966 dòng có tên người bán (82%), 145 tên khác nhau. Khớp thẳng vào danh
sách nhân sự được 13.662 dòng (91% số dòng có tên). Phần còn lại KHÔNG khớp được bằng máy, và không
khớp theo hai kiểu khác hẳn nhau:

  · TRÙNG TÊN – "THÙY TRANG" ứng với cả Trần Thị Thùy Trang lẫn Quách Thị Thuỳ Trang. Máy đoán một
    trong hai là gán doanh số của người này cho người kia. Sáu tên như vậy, 286 dòng.
  · KHÔNG CÓ TRONG DANH SÁCH – 61 tên, 1.018 dòng. Phần lớn là người đã nghỉ trong nửa đầu năm; vài
    tên là đầu mối ngoài công ty (VP Cần Thơ, đại lý).

Cả hai kiểu chỉ người mới giải được. Nên bảng này tồn tại để lời giải ấy được GHI LẠI MỘT LẦN: gán
xong là gán mãi, nạp lại lô hay gỡ lô rồi nạp lại đều không phải gán lại. Không có bảng này thì mỗi
lần nạp là một lần ngồi gán 67 cái tên.

KHOÁ LÀ `khoa_ten`, KHÔNG PHẢI TÊN

`khoa_ten` là tên đã bỏ dấu, bỏ khoảng trắng, hạ chữ thường (app.services.staff.name_key). Cùng một
người viết "HỒNG NGHIỆP" ở tệp này và "Hong Nghiep" ở tệp kia phải rơi vào cùng một dòng, nếu không
thì bảng gán phình ra theo lỗi gõ chứ không theo số người.

`user_id` RỖNG CÓ NGHĨA, KHÔNG PHẢI CHƯA LÀM

Rỗng = đã nhìn thấy tên này nhưng CHƯA gán được cho ai. Doanh thu của những dòng ấy vẫn vào hệ thống
(tiền công ty thu thật), nhưng không tính vào chỉ tiêu của bất kỳ ai – cộng nhầm cho người khác tệ
hơn là để trống.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class KhoCuNguoiBan(Base):
    """Một cái tên trong cột SALES của kho cũ, và tài khoản VTOS tương ứng (nếu đã gán được)."""

    __tablename__ = "kho_cu_nguoi_ban"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tên đã chuẩn hoá – DUY NHẤT. Xem ghi chú đầu tệp về vì sao khoá không phải là tên thô.
    khoa_ten: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # Tên thô như trong tệp, giữ nguyên để người gán nhận ra mình đang gán cho ai.
    ten_trong_tep: Mapped[str] = mapped_column(String(120))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # "dung_ten" máy khớp đúng cả họ tên · "duoi_ten" máy khớp phần đuôi và CHỈ có một người ứng
    # · "nguoi_gan" người chọn tay · "trung_ten" nhiều người cùng ứng, máy KHÔNG chọn
    # · "ngoai_danh_sach" không có ai trong danh sách nhân sự
    cach_khop: Mapped[str] = mapped_column(String(20), default="")
    # Các ứng viên khi trùng tên, ghi lại để màn hình gán bày ra sẵn thay vì bắt người ta tự tìm.
    ung_vien: Mapped[str] = mapped_column(String(400), default="")

    so_dong: Mapped[int] = mapped_column(Integer, default=0)      # số dòng khách mang tên này
    # Người đã nghỉ: giữ cờ để báo cáo nói được "doanh số của người đã nghỉ", thay vì lẫn vào nhóm
    # chưa gán và bị hiểu là việc còn dở.
    da_nghi: Mapped[bool] = mapped_column(Boolean, default=False)

    nguoi_gan: Mapped[str] = mapped_column(String(50), default="")
    gan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class KhoCuTepChuyen(Base):
    """TỆP NÀO ĐẺ RA CHUYẾN NÀO. Một dòng cho mỗi tệp Excel mà cửa tạo chuyến đã dựng chuyến từ đó.

    VÌ SAO CẦN, VÀ VÌ SAO KHÔNG THỂ LÀM KHÁC

    Bản đối chiếu H1 mà Kế toán đã chốt (624 chuyến, khớp MISA) là chỗ DUY NHẤT có tổng thu và tổng
    chi đúng ở mức chuyến – bộ đọc tệp Excel chỉ rút được 90,7% doanh thu và 71,1% giá vốn. Nhưng
    bản đối chiếu ấy gọi tên chuyến bằng TÊN TỆP, không bằng mã tour: đo ngày 13/9/2026 trên 624
    dòng, chỉ 10 dòng mang mã tour đúng dạng, còn 507 dòng chỉ khớp được qua tên tệp.

    Mã tour thì nằm BÊN TRONG tệp Excel ("Mã tour: ..."), nên bản đối chiếu – vốn chỉ có tên tệp –
    không tự suy ra được. Cầu nối phải do lúc NẠP ghi lại, và đó là bảng này.

    Nó cũng trả lời được một câu mà trước đây phải đoán: "chuyến này ở VTOS đến từ tệp nào".
    """

    __tablename__ = "kho_cu_tep_chuyen"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tên tệp đã chuẩn hoá (bỏ dấu, bỏ ký tự lạ, bỏ phần mở rộng) – DUY NHẤT, và là khoá để ghép
    # với cột "File quyết toán" của bản đối chiếu. Tên thô giữ ở `ten_tep` để người đọc nhận ra.
    khoa_tep: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    ten_tep: Mapped[str] = mapped_column(String(255))
    ma_tour: Mapped[str] = mapped_column(String(30), default="")
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
