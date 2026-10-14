# -*- coding: utf-8 -*-
"""BỘ SỐ BCTC ĐÃ KIỂM TOÁN — Đợt E16, 14/10/2026. Kế toán TẢI LÊN, Chủ tịch KÝ.

CHỖ HỎNG MÀ ĐỢT NÀY SỬA

Trước đợt này, bộ số BCTC đã soát xét nằm trong KHO MÃ: `backend/app/data/kiem_toan_2026h1.json`,
ba mươi tài khoản, do robot gõ. Cửa `POST /misa/kiem-toan-checkpoint` KHÔNG nhận tệp — nó đọc thẳng
tệp ấy. Nút trên màn hình trông như một cửa nạp, nhưng nó chỉ phát lại một bộ số cố định.

Ba hệ quả, cả ba đều thật:

  1. VI PHẠM RANH GIỚI 09/9/2026 — mỗi con số phải có một cửa cho người dùng đưa vào. Ba mươi con
     số ấy đi qua tay robot, không có ai ký.
  2. KHÔNG SỬA ĐƯỢC. Kiểm toán ra bản chính thức khác bản soát xét thì Kế toán phải nhờ robot sửa
     tệp trong kho mã rồi đẩy một đợt.
  3. CHỈ MỘT PHÁP NHÂN, MỘT KỲ, MỘT BẢN. Không nạp được BCTC của Vietrip, không nạp được kỳ sau.

BỐN ĐIỀU BẢNG NÀY CỐ Ý KHÔNG LÀM

1. KHÔNG tự lấy số từ MISA. Bộ số kiểm toán KHÁC số MISA — đó chính là lý do cửa này tồn tại
   (MISA 31/12/2025 ghi 331 dư Nợ 100,6 tỷ, BCTC kiểm toán phân loại 55,4 tỷ sang phải thu khác).
   Tự suy là xóa mất đúng cái chênh lệch mà người ta cần nhìn.
2. KHÔNG cho sửa dòng sau khi đã ký. Muốn đổi số thì tải lên một BẢN MỚI; bản cũ chuyển sang
   `da_thay_the` và vẫn đọc được. Kiểm toán sẽ hỏi bản nào đã dùng để chốt sổ ngày nào.
3. KHÔNG tự chốt sổ lúc ký. Ký là xác nhận BỘ SỐ ĐÚNG; chốt sổ là một việc riêng, bấm riêng, và
   ghi một chứng từ riêng. Gộp hai việc thì không ai lùi lại được một bước.
4. KHÔNG thêm cột vào `ho_so_kiem_toan` (V7 Đợt 3). Bảng ấy là HỒ SƠ GIAO CHO KIỂM TOÁN VIÊN —
   kỳ nào, đơn vị nào, họ đòi tài liệu gì, ý kiến ra sao. Bảng này là BỘ SỐ. Một kỳ có đúng một hồ
   sơ nhưng có thể có nhiều bản bộ số nối tiếp nhau (soát xét → chính thức → nạp lại), nên nhét bộ
   số vào hồ sơ là ép hai nhịp đời khác nhau vào một dòng. Hai bảng dùng CHUNG bộ từ vựng
   `KT_LOAI` của hồ sơ, nhập từ đó chứ không khai lại — một luật, một chỗ.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.kieu_tien import TIEN

TRANG_THAI_BO_SO = {
    "cho_ky": "Kế toán đã tải lên, chờ Chủ tịch ký",
    "da_ky": "Chủ tịch đã ký — dùng được để chốt sổ",
    "tu_choi": "Chủ tịch từ chối",
    "da_thay_the": "Đã bị một bản tải lên sau thay thế",
}


class BoSoKiemToan(Base):
    """Một BẢN bộ số BCTC đã kiểm toán / soát xét, do Kế toán tải lên.

    Khai nguồn là BẮT BUỘC ở tầng dịch vụ — đơn vị kiểm toán, số báo cáo, ngày báo cáo. Một bộ số
    không nói được nó từ bản nào thì sáu tháng sau không ai đối chiếu lại được, và nó sẽ bị dùng
    như thể đã kiểm toán.
    """

    __tablename__ = "bo_so_kiem_toan"
    __table_args__ = (Index("ix_bo_so_kiem_toan_tt_ngay", "trang_thai", "as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pháp nhân. RỖNG là CHƯA XÁC ĐỊNH — cùng quy ước với `chot_so_du`. BCTC của công ty mẹ và của
    # Vietrip là hai bộ số khác nhau, không cộng vào nhau, nên mỗi bản gắn đúng một pháp nhân.
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True)

    as_of: Mapped[date] = mapped_column(Date, index=True)      # ngày kết thúc kỳ của bộ số
    ky: Mapped[str] = mapped_column(String(20), default="")    # "H1/2026", "Năm 2025"…

    # ── KHAI NGUỒN — ba ô này là thứ phân biệt một bộ số đã kiểm toán với một bảng Excel bất kỳ.
    don_vi_kiem_toan: Mapped[str] = mapped_column(String(160), default="")
    so_bao_cao: Mapped[str] = mapped_column(String(80), default="")
    ngay_bao_cao: Mapped[date | None] = mapped_column(Date, nullable=True)
    loai_bao_cao: Mapped[str] = mapped_column(String(20), default="soat_xet")   # khóa của KT_LOAI
    ghi_chu: Mapped[str] = mapped_column(Text, default="", server_default="")

    trang_thai: Mapped[str] = mapped_column(String(16), default="cho_ky", index=True)

    tai_len_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_len_vai: Mapped[str] = mapped_column(String(24), default="")
    tai_len_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ten_tep: Mapped[str] = mapped_column(String(200), default="")

    ky_boi: Mapped[str] = mapped_column(String(50), default="")
    ky_vai: Mapped[str] = mapped_column(String(24), default="")
    ky_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tu_choi_ly_do: Mapped[str] = mapped_column(String(500), default="")

    # Bản này thay thế bản nào. RỖNG là bản đầu tiên cho (pháp nhân, ngày).
    thay_the_id: Mapped[int | None] = mapped_column(
        ForeignKey("bo_so_kiem_toan.id"), nullable=True)

    dong: Mapped[list["DongBoSoKiemToan"]] = relationship(
        back_populates="bo", cascade="all, delete-orphan", lazy="selectin")


class DongBoSoKiemToan(Base):
    """Một dòng của bộ số: một tài khoản, hoặc một ĐỐI TƯỢNG của tài khoản ấy.

    HAI LOẠI DÒNG TRONG CÙNG MỘT BẢNG, phân biệt bằng `ma_doi_tuong` rỗng hay không:

      · `ma_doi_tuong` RỖNG  → dòng TÀI KHOẢN. Mọi tài khoản phải có đúng một dòng loại này.
      · `ma_doi_tuong` có   → dòng ĐỐI TƯỢNG của tài khoản ấy (131 theo từng khách, 331 theo từng
                              nhà cung cấp). BCTC tách Nợ/Có THEO TỪNG ĐỐI TƯỢNG chứ không theo
                              tổng tài khoản, nên thiếu lớp này thì chỉ tiêu 132/311 phồng lên —
                              lỗi đã gặp thật trên dữ liệu production.

    Tách thành hai bảng thì một bản bộ số phải nối hai bảng con để đọc một con số; để chung và nói
    rõ bằng một ô là đọc được bằng mắt trong cùng một bảng.

    BỐN Ô TIỀN KHÔNG NULLABLE: một dòng có mặt nghĩa là kiểm toán đã nói về tài khoản ấy, và
    "kiểm toán nói số dư bằng không" khác hẳn "không ai nói gì về tài khoản này" — cái sau thì
    KHÔNG có dòng, chứ không phải có dòng với ô rỗng.
    """

    __tablename__ = "bo_so_kiem_toan_dong"
    __table_args__ = (Index("ix_bsktd_bo_tk", "bo_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bo_id: Mapped[int] = mapped_column(ForeignKey("bo_so_kiem_toan.id"), index=True)

    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200), default="")
    ma_doi_tuong: Mapped[str] = mapped_column(String(50), default="", server_default="")
    ten_doi_tuong: Mapped[str] = mapped_column(String(200), default="", server_default="")
    open_d: Mapped[float] = mapped_column(TIEN, default=0)
    open_c: Mapped[float] = mapped_column(TIEN, default=0)
    close_d: Mapped[float] = mapped_column(TIEN, default=0)
    close_c: Mapped[float] = mapped_column(TIEN, default=0)

    bo: Mapped["BoSoKiemToan"] = relationship(back_populates="dong")
