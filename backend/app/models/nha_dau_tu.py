"""Đợt D3 – quan hệ nhà đầu tư: danh bạ, sổ tiếp xúc, và sổ cấp quyền xem hồ sơ.

Ba bảng, và cả ba sinh ra từ một chuyện: VTD niêm yết UPCoM, nên việc "ai được biết gì, trước ai"
không còn là chuyện lịch sự — nó là chuyện có chế tài.

  1. `lien_he_nha_dau_tu`  – danh bạ cổ đông, quỹ, công ty chứng khoán, báo chí tài chính.
  2. `tuong_tac_nha_dau_tu` – mỗi lần gặp/gọi/email, và câu quan trọng nhất: lần ấy CÓ nói ra
     thông tin chưa công bố không.
  3. `quyen_truy_cap_ho_so` – ai được xem hồ sơ chưa công bố, vì sao, tới bao giờ.

HAI ĐIỀU BẢNG NÀY CỐ Ý KHÔNG LÀM:

  · KHÔNG lưu số cổ phần sở hữu. Sở hữu là dữ liệu của sổ cổ đông (VSD/đơn vị quản lý sổ). Chép
    tay một con số sở hữu vào đây là tạo ra con số thứ hai, và hai con số về cùng một thứ thì sớm
    muộn sẽ lệch — lúc ấy không ai biết con số nào sai.
  · KHÔNG nạp sẵn một dòng nào. Cả ba bảng bắt đầu rỗng (ranh giới 09/9/2026).

DỮ LIỆU CÁ NHÂN: email và điện thoại của nhà đầu tư là dữ liệu cá nhân (Nghị định 13/2023). Cột
`can_cu_thu_thap` BẮT BUỘC ghi rõ thông tin ấy từ đâu mà có, và đường ra ngoài CHE bớt cho những
vai chỉ cần biết "đã tiếp xúc với ai" chứ không cần số điện thoại — xem services/nha_dau_tu.py.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

LOAI_LIEN_HE = {
    "co_dong_lon": "Cổ đông lớn",
    "co_dong": "Cổ đông",
    "quy": "Quỹ đầu tư",
    "cong_ty_ck": "Công ty chứng khoán / phân tích",
    "bao_chi_tc": "Báo chí tài chính",
    "co_quan_quan_ly": "Cơ quan quản lý",
    "khac": "Khác",
}

HINH_THUC_TIEP_XUC = {
    "gap": "Gặp trực tiếp",
    "goi": "Gọi điện",
    "email": "Email / văn bản",
    "dhdcd": "Đại hội đồng cổ đông",
    "roadshow": "Roadshow / hội nghị nhà đầu tư",
    "khac": "Khác",
}


class LienHeNhaDauTu(Base):
    """Một đầu mối quan hệ nhà đầu tư. KHÔNG có cột sở hữu – xem chú thích đầu tệp."""
    __tablename__ = "lien_he_nha_dau_tu"
    __table_args__ = (
        Index("ix_lien_he_nha_dau_tu_loai_hd", "loai", "dang_hoat_dong"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ten: Mapped[str] = mapped_column(String(160))
    to_chuc: Mapped[str] = mapped_column(String(200), default="")
    chuc_danh: Mapped[str] = mapped_column(String(120), default="")
    loai: Mapped[str] = mapped_column(String(20), default="khac", index=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    dien_thoai: Mapped[str] = mapped_column(String(40), default="")
    # BẮT BUỘC khi có email hoặc điện thoại. Nghị định 13/2023: thu thập dữ liệu cá nhân phải có
    # căn cứ. Một danh bạ không nói được số điện thoại từ đâu ra là một danh bạ không giải trình
    # được, và đó là loại rủi ro chỉ hiện ra khi có người hỏi.
    can_cu_thu_thap: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    dang_hoat_dong: Mapped[bool] = mapped_column(Boolean, default=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class TuongTacNhaDauTu(Base):
    """Một lần tiếp xúc. Câu quan trọng nhất của bảng này là `co_thong_tin_chua_cong_bo`."""
    __tablename__ = "tuong_tac_nha_dau_tu"
    __table_args__ = (
        Index("ix_tuong_tac_nha_dau_tu_ngay_lh", "ngay", "lien_he_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    lien_he_id: Mapped[int] = mapped_column(ForeignKey("lien_he_nha_dau_tu.id"), index=True)
    ngay: Mapped[date] = mapped_column(Date, index=True)
    hinh_thuc: Mapped[str] = mapped_column(String(20), default="gap")
    noi_dung_tom_tat: Mapped[str] = mapped_column(Text, default="")
    nguoi_du: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # CÔNG BỐ CÔNG BẰNG. Nói một thông tin chưa công bố cho một nhà đầu tư trước những người khác
    # là tiết lộ chọn lọc. Hệ thống không ngăn được việc ấy xảy ra, nhưng nó bắt phải GHI LẠI, và
    # bắt nối tới bản công bố đã làm cho thông tin ấy thành công khai.
    co_thong_tin_chua_cong_bo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Bản ghi công bố (Đợt D1) đã đưa thông tin ấy ra công chúng. RỖNG khi đã đánh dấu có tiết lộ
    # = một việc PHẢI xử lý, không phải một ô để trống cho xong.
    ban_ghi_cong_bo_id: Mapped[int | None] = mapped_column(
        ForeignKey("ban_ghi_cong_bo.id"), nullable=True)
    thong_tin_da_tiet_lo: Mapped[str] = mapped_column(Text, default="")

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class QuyenTruyCapHoSo(Base):
    """Một lần cấp quyền xem hồ sơ. Ai, hồ sơ gì, vì sao, TỚI BAO GIỜ."""
    __tablename__ = "quyen_truy_cap_ho_so"
    __table_args__ = (
        Index("ix_quyen_truy_cap_ho_so_han", "den_ngay", "thu_hoi_luc"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ho_so: Mapped[str] = mapped_column(String(300))
    nguoi_duoc_cap: Mapped[str] = mapped_column(String(160))
    to_chuc: Mapped[str] = mapped_column(String(200), default="")
    lien_he_id: Mapped[int | None] = mapped_column(
        ForeignKey("lien_he_nha_dau_tu.id"), nullable=True)
    ly_do: Mapped[str] = mapped_column(Text, default="")
    # Hồ sơ này đã công bố chưa. Nếu CHƯA, cửa cấp quyền đòi cam kết bảo mật – xem services.
    ho_so_chua_cong_bo: Mapped[bool] = mapped_column(Boolean, default=True)
    cam_ket_bao_mat: Mapped[bool] = mapped_column(Boolean, default=False)
    can_cu_cam_ket: Mapped[str] = mapped_column(Text, default="")

    tu_ngay: Mapped[date] = mapped_column(Date, index=True)
    # RỖNG = cấp không thời hạn. Đó là một việc PHẢI xử lý, không phải một việc để yên tâm – cùng
    # một lối nghĩ với `chua_ro_han` của Đợt D1. Quyền xem hồ sơ chưa công bố mà không có ngày hết
    # là quyền sẽ còn sống sau khi lý do cấp nó đã chết.
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    thu_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    thu_hoi_boi: Mapped[str] = mapped_column(String(50), default="")

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
