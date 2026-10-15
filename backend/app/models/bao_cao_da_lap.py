# -*- coding: utf-8 -*-
"""BẢN BÁO CÁO ĐÃ LẬP — Đợt R1, 15/10/2026. Kế toán LẬP, Chủ tịch KÝ, SỐ ĐÓNG BĂNG.

VÌ SAO CÓ BẢNG NÀY

Trước đợt này, màn hình BCTC của VTOS **tính lại từ sổ mỗi lần mở**. Nghĩa là con số của một kỳ
đã qua đổi theo sổ: ai ghi thêm một bút toán đề ngày cũ thì báo cáo kỳ ấy khác đi, và không còn
bản nào để đối chiếu.

ĐÃ ĐO ĐƯỢC NGÀY 15/10/2026, trên sổ thử: sau khi chốt mốc kiểm toán 30/06/2026 (đáp án 10 tỷ),
nạp thêm mốc 31/12/2025 thì chỉ tiêu 111 tại 30/06/2026 **tụt từ 10.000.000.000 xuống
9.500.000.000** — vì cửa chốt sổ ghi bút toán theo CHÊNH LỆCH, và bút toán mới đề ngày 31/12/2025
chảy xuôi vào số dư của ngày sau. Không có bản đóng băng thì không ai biết nó đã tụt.

MISA tách hai việc, và đó là chỗ đợt này học: **LẬP** (tính từ sổ theo tham số) và **LƯU BẢN**
(chốt bản ấy lại). Hộp tham số của họ có ô "Lấy dữ liệu từ báo cáo tài chính đã lập".

BA ĐIỀU BẢNG NÀY KHAI, VÀ VÌ SAO TỪNG ĐIỀU

 1. **THAM SỐ ĐÃ DÙNG, lưu nguyên văn.** Một bản không nói được nó tính bằng tham số nào thì sáu
    tháng sau không ai dựng lại được nó. Lưu cả chuỗi JSON chứ không tách cột: tham số sẽ còn
    thêm ô, mà bản cũ phải đọc được bằng đúng tham số của ngày nó được lập.
 2. **SỐ ĐÓNG BĂNG THEO TỪNG CHỈ TIÊU**, không lưu lại cả tệp. Lưu tệp thì không so sánh được hai
    bản với nhau; lưu từng chỉ tiêu thì một câu truy vấn trả lời được "chỉ tiêu 110 của kỳ này
    khác kỳ trước bao nhiêu".
 3. **BẢN CŨ KHÔNG XOÁ**, chuyển sang `da_thay_the` và trỏ `thay_the_id`. Một báo cáo tài chính
    của công ty đại chúng mà xoá được là một báo cáo không ai tin được.

CÙNG HÌNH DÁNG VỚI ĐỢT E16 (bộ số kiểm toán): Kế toán trình, Chủ tịch ký, bản cũ bị thay thế chứ
không mất. Luật chữ ký khai ở `services/chu_ky.py::VAI_KY_CAN`, KHÔNG viết tay ở đây — một luật,
một chỗ.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Trạng thái của một BẢN. Năm trạng thái, và `nhap` tách khỏi `cho_ky` là có chủ ý: Kế toán lập
# thử nhiều lần trước khi trình, và một bản nháp chưa phải một lời khai.
TRANG_THAI_BAN = {
    "nhap":        "Kế toán đã lập, chưa trình",
    "cho_ky":      "Đã trình, chờ Chủ tịch ký",
    "da_ky":       "Chủ tịch đã ký — bản chính thức của kỳ",
    "tu_choi":     "Chủ tịch từ chối",
    "da_thay_the": "Đã bị một bản lập sau thay thế",
}

# Loại báo cáo lập được. Khai thành bảng để thêm loại là thêm MỘT DÒNG, không phải một bảng mới.
LOAI_BAN = {
    "bctc": "Bộ báo cáo tài chính TT99 (B01 + B02 + B03)",
}

# Ba bảng số trong một bộ BCTC — đúng ba khóa mà `services/bctc.py::bctc()` trả về.
BANG_SO = {
    "thtc": "Báo cáo tình hình tài chính (B01-DN)",
    "kqkd": "Báo cáo kết quả hoạt động kinh doanh (B02-DN)",
    "lctt": "Báo cáo lưu chuyển tiền tệ gián tiếp (B03-DN-GT)",
}

# Kỳ báo cáo — đúng bộ từ vựng của MISA ở họ báo cáo tài chính.
LOAI_KY = {
    "nam":      "Năm",
    "quy":      "Quý",
    "thang":    "Tháng",
    "tuy_chon": "Tùy chọn (tự nhập từ ngày – đến ngày)",
}


class BanBaoCao(Base):
    """Một BẢN báo cáo đã lập của một kỳ, của một pháp nhân."""

    __tablename__ = "bao_cao_da_lap"
    __table_args__ = (
        Index("ix_bao_cao_da_lap_tra", "loai", "company_id", "ky", "trang_thai"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pháp nhân. RỖNG là CHƯA XÁC ĐỊNH — cùng quy ước với `chot_so_du` và `bo_so_kiem_toan`.
    # BCTC của công ty mẹ và của Vietrip là hai bản khác nhau, không cộng vào nhau.
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True)

    loai: Mapped[str] = mapped_column(String(20), default="bctc", index=True)   # khóa của LOAI_BAN
    loai_ky: Mapped[str] = mapped_column(String(12), default="nam")             # khóa của LOAI_KY
    ky: Mapped[str] = mapped_column(String(24), default="", index=True)         # "2026-H1", "Năm 2025"

    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date] = mapped_column(Date, index=True)
    # Mốc của CỘT SO SÁNH. Rỗng nghĩa là bản này không có cột so sánh — khác hẳn với "so sánh ra 0".
    so_sanh_den: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Tham số đã dùng, nguyên văn JSON. Xem chú thích (1) ở đầu tệp.
    tham_so: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")

    nguoi_dai_dien: Mapped[str] = mapped_column(String(160), default="")
    ngay_lap: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="", server_default="")

    trang_thai: Mapped[str] = mapped_column(String(16), default="nhap", index=True)

    lap_boi: Mapped[str] = mapped_column(String(50), default="")
    lap_vai: Mapped[str] = mapped_column(String(24), default="")
    lap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trinh_boi: Mapped[str] = mapped_column(String(50), default="")
    trinh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ky_boi: Mapped[str] = mapped_column(String(50), default="")
    ky_vai: Mapped[str] = mapped_column(String(24), default="")
    ky_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tu_choi_ly_do: Mapped[str] = mapped_column(String(500), default="")

    # Bản này thay thế bản nào. RỖNG là bản đầu tiên của (loại, pháp nhân, kỳ).
    thay_the_id: Mapped[int | None] = mapped_column(
        ForeignKey("bao_cao_da_lap.id"), nullable=True)

    dong: Mapped[list["DongBanBaoCao"]] = relationship(
        back_populates="ban", cascade="all, delete-orphan", lazy="selectin")


class DongBanBaoCao(Base):
    """Một chỉ tiêu đã đóng băng của một bản.

    HAI Ô TIỀN KHÔNG NULLABLE. Một dòng có mặt nghĩa là chỉ tiêu ấy ĐÃ ĐƯỢC TÍNH tại thời điểm
    lập; "tính ra 0" khác hẳn "không tính". Chỉ tiêu không tính thì KHÔNG có dòng.

    `gia_tri_ss` là cột so sánh (số đầu năm của B01, cùng kỳ năm trước của B02). Bảng LCTT không
    có cột so sánh nên `gia_tri_ss` của nó luôn bằng 0 — và `so_sanh_den` rỗng nói ra điều ấy ở
    tầng bản, nên không ai đọc nhầm số 0 kia thành một phép so sánh đã làm.
    """

    __tablename__ = "bao_cao_da_lap_dong"
    __table_args__ = (Index("ix_bcdld_ban_bang_ma", "ban_id", "bang", "ma"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ban_id: Mapped[int] = mapped_column(
        ForeignKey("bao_cao_da_lap.id", ondelete="CASCADE"), index=True)

    bang: Mapped[str] = mapped_column(String(8))      # khóa của BANG_SO
    ma: Mapped[str] = mapped_column(String(12))       # mã chỉ tiêu: "110", "01", "20"…
    ten: Mapped[str] = mapped_column(String(300), default="")

    gia_tri: Mapped[float] = mapped_column(TIEN)
    gia_tri_ss: Mapped[float] = mapped_column(TIEN)

    ban: Mapped["BanBaoCao"] = relationship(back_populates="dong")
