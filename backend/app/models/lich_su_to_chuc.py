"""Đợt C – LỊCH SỬ TỔ CHỨC: một người thuộc phòng nào, chức vụ gì, TỪ ngày nào ĐẾN ngày nào.

VẤN ĐỀ

`employees.department` là MỘT GIÁ TRỊ HIỆN TẠI. Đổi phòng cho một người hôm nay thì mọi báo cáo của
quá khứ đọc theo phòng mới — lịch sử bị viết lại, lặng lẽ, không ai bấm nút nào gọi là "sửa lịch sử".
Một người chuyển từ Kinh doanh Lẻ sang Điều hành tháng này làm chi phí lương Điều hành của sáu tháng
trước tự nhiên tăng lên, và không có cách nào biết là nó đã tăng.

Khối Kinh doanh đã có mẫu đúng: `phan_cong_kd` với `tu_ngay` / `den_ngay`. Bảng này mở mẫu ấy cho
TOÀN BỘ nhân sự, không chỉ khối Kinh doanh.

GHI THEO MÃ NHÂN VIÊN, KHÔNG THEO id

`ma_nv` là `employees.code` — thứ xuất hiện trên bảng lương, trên sổ sự kiện thu nhập, trên bảng
chấm công. Dùng khoá ngoài tới `employees.id` thì nối được, nhưng lúc đối chiếu một kỳ lương cũ
với lịch sử tổ chức lại phải đi qua một phép nối nữa, và một hồ sơ bị dựng lại (mã cũ, id mới) sẽ
làm đứt lịch sử mà không báo gì.

MỘT CỜ PHẢI CÓ: `suy_ra`

Dòng đầu tiên của mỗi người KHÔNG phải do ai ghi lại lúc ấy — nó được dựng từ thứ hệ thống đang có
(phòng hiện tại + ngày vào làm) tại lần điều chuyển đầu tiên. Đó là một SUY RA, không phải một bản
ghi, và nó phải tự nói ra điều đó. Trộn hai thứ vào nhau là biến một phỏng đoán hợp lý thành một
chứng cứ, mà chứng cứ thì có người sẽ dựa vào để trả lời kiểm toán.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LichSuToChuc(Base):
    """Một chặng tổ chức của một người: phòng, chức vụ, văn phòng, pháp nhân, trong một khoảng ngày."""
    __tablename__ = "lich_su_to_chuc"
    __table_args__ = (
        # Truy vấn chạy nhiều nhất là "ngày ấy người này ở đâu" – đúng ba cột này.
        Index("ix_lich_su_to_chuc_nguoi_ngay", "ma_nv", "tu_ngay", "den_ngay"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ma_nv: Mapped[str] = mapped_column(String(20), index=True)
    phong: Mapped[str] = mapped_column(String(20))
    chuc_vu: Mapped[str] = mapped_column(String(20), default="nv")
    van_phong: Mapped[str] = mapped_column(String(20), default="")
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)   # pháp nhân trả lương

    tu_ngay: Mapped[date] = mapped_column(Date, index=True)
    # RỖNG = chặng đang mở, tức là chỗ người này đang ở. Không dùng cờ true/false: ngày kết thúc
    # trả lời được cả "còn hiệu lực không" lẫn "hiệu lực tới bao giờ", một cờ thì chỉ trả lời câu đầu.
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)

    ly_do: Mapped[str] = mapped_column(Text, default="")
    # True = chặng này do hệ thống DỰNG LẠI từ hồ sơ hiện có, không phải ai ghi lúc ấy. Xem đầu tệp.
    suy_ra: Mapped[bool] = mapped_column(Boolean, default=False)
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def dang_hieu_luc(self, ngay: date) -> bool:
        if ngay < self.tu_ngay:
            return False
        return self.den_ngay is None or ngay <= self.den_ngay
