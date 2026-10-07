"""Khóa kỳ lương — chụp lại đầu vào, quy tắc và kết quả tại đúng lúc có chữ ký.

VÌ SAO PHẢI CÓ BẢNG NÀY

Trước bản này, kết quả một kỳ lương nằm trong `payroll_runs.rows`, và `get_or_draft(refresh=True)`
tính lại rồi GHI ĐÈ. Nghĩa là: sửa một dòng trong bảng `params` hôm nay có thể làm đổi con số của
một kỳ đã ký hôm qua, và không ai thấy. Không có vân tay, không có phiên bản, không chứng minh được
câu "cùng đầu vào ra cùng kết quả" — mà đó chính là câu người ta cần khi giải trình một kỳ lương
trước kiểm toán hoặc trước chính người lao động.

Bảng này lưu BẢN CHỤP, không phải bản tham chiếu. Chụp cả ba thứ:

  · `noi_dung`  – dòng lương và tổng, nguyên văn lúc ký;
  · `quy_tac`   – giá trị các tham số đã dùng để ra con số ấy (mốc chỉ tiêu, ngưỡng, thang F…);
  · `dau_van_tay` – băm của hai thứ trên, để một người thứ ba kiểm lại được mà không cần tin ai.

Chụp tham số là phần dễ quên nhất và quan trọng nhất: lưu mỗi kết quả thì năm sau không ai trả lời
được "vì sao tháng ấy ra số này", còn lưu cả tham số thì trả lời được bằng một phép so.

KHÔNG XOÁ CỘT CŨ. `kt_confirmed_by`, `hcns_by`, `tgd_by` của `payroll_runs` giữ nguyên: đó là lịch
sử những kỳ đã chạy qua chuỗi cũ. Bỏ cột là xoá chữ ký của người thật trong quá khứ.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Lý do mở lại một kỳ đã khóa. Mở lại KHÔNG xoá bản khóa cũ — nó sinh bản khóa mới mang số phiên bản
# tiếp theo, và bản cũ vẫn đọc được. Lịch sử lương là thứ không được viết lại.
LY_DO_MO = {
    "sai_dau_vao": "Phát hiện sai đầu vào sau khi ký",
    "sai_chinh_sach": "Áp sai chính sách hoặc tham số",
    "yeu_cau_lanh_dao": "Lãnh đạo yêu cầu xem lại",
}


class BangLuongKhoa(Base):
    """Một bản khóa của một kỳ lương. Mỗi lần ký sinh một bản; mở lại rồi ký lại sinh bản tiếp theo."""

    __tablename__ = "bang_luong_khoa"

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    ban_so: Mapped[int] = mapped_column(Integer, default=1)

    # Bản chụp. JSON chứ không phải khóa ngoại: bản chụp phải đứng độc lập với dữ liệu nguồn, vì cái
    # nó chứng minh chính là "lúc ấy số liệu nguồn trông như thế này".
    noi_dung: Mapped[dict] = mapped_column(JSON, default=dict)      # {"rows": [...], "totals": {...}}
    quy_tac: Mapped[dict] = mapped_column(JSON, default=dict)       # tham số đã dùng, kèm hiệu lực
    dau_van_tay: Mapped[str] = mapped_column(String(64), index=True)

    khoa_boi: Mapped[str] = mapped_column(String(50), default="")
    khoa_vai: Mapped[str] = mapped_column(String(20), default="")   # chutich hoặc tgd
    khoa_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Bản này đã bị một bản sau thay chưa. RỖNG nghĩa là đang có hiệu lực — khác 0 và khác False.
    bi_thay_boi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ly_do_mo: Mapped[str] = mapped_column(String(20), default="")
    ghi_chu_mo: Mapped[str] = mapped_column(Text, default="")
    mo_boi: Mapped[str] = mapped_column(String(50), default="")
    mo_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


Index("ix_bang_luong_khoa_ky_ban", BangLuongKhoa.period, BangLuongKhoa.ban_so, unique=True)
