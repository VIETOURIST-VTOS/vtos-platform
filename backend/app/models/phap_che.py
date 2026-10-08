"""Đợt D1 – IR & Pháp chế: văn bản CÓ PHIÊN BẢN, nghĩa vụ công bố, và bản ghi công bố.

Ba bảng, và cả ba đều trả lời một câu mà hệ thống hiện chưa trả lời được.

  1. `van_ban_phap_che` – "bản nào đang có hiệu lực, và bản trước nó nói gì". Một quy chế sửa ba
     lần trong năm mà chỉ lưu bản mới nhất thì không giải trình được một quyết định đã ra theo bản
     cũ. Sửa văn bản ĐÃ CÓ HIỆU LỰC không ghi đè: nó sinh một phiên bản mới và đóng dấu bản cũ.

  2. `nghia_vu_cong_bo` – "công ty phải công bố những gì". VTD niêm yết UPCoM nên đây là nghĩa vụ
     có chế tài, không phải việc nội bộ.

  3. `ban_ghi_cong_bo` – "lần này đã công bố chưa, đúng hạn không, bằng văn bản nào".

KHÔNG NẠP SẴN MỘT DÒNG NGHĨA VỤ NÀO, và đây là điều quan trọng nhất của tệp này.

Danh mục nghĩa vụ công bố và thời hạn của chúng là QUY ĐỊNH PHÁP LUẬT. Lần viết phần mềm không
được điền chúng từ trí nhớ: một hạn ghi sai ở đây không hiện ra như một lỗi phần mềm, nó hiện ra
như một lần chậm công bố. Bảng bắt đầu RỖNG; Pháp chế khai từng nghĩa vụ qua cửa nhập, kèm `can_cu`
ghi rõ điều khoản nào. Ranh giới 09/9/2026: phần mềm viết cấu trúc, người khai số liệu.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

LOAI_VAN_BAN = {
    "dieu_le": "Điều lệ",
    "quy_che": "Quy chế",
    "quy_dinh": "Quy định / quy trình",
    "nghi_quyet_hdqt": "Nghị quyết HĐQT",
    "quyet_dinh": "Quyết định",
    "bien_ban": "Biên bản",
    "cong_van": "Công văn",
    "hop_dong_mau": "Hợp đồng mẫu",
    "khac": "Văn bản khác",
}

# Trạng thái của MỘT PHIÊN BẢN, không phải của cả văn bản. Một văn bản là một chuỗi phiên bản; tại
# mỗi thời điểm nhiều nhất MỘT phiên bản ở "hieu_luc".
TRANG_THAI_VB = {
    "nhap": "Bản nháp – sửa tại chỗ được",
    "dang_ra_soat": "Đang rà soát",
    "hieu_luc": "Đang có hiệu lực",
    "thay_the": "Đã bị một phiên bản sau thay thế",
    "het_hieu_luc": "Hết hiệu lực, không có bản thay",
}

CHU_KY_CONG_BO = {
    "su_kien": "Theo sự kiện (bất thường)",
    "quy": "Hằng quý",
    "ban_nien": "Bán niên",
    "nam": "Hằng năm",
    "khac": "Chu kỳ khác – mô tả ở phần hạn",
}


class VanBanPhapChe(Base):
    """Một PHIÊN BẢN của một văn bản. Các phiên bản của cùng văn bản dùng chung `goc_id`."""
    __tablename__ = "van_ban_phap_che"
    __table_args__ = (
        Index("ix_van_ban_phap_che_goc", "goc_id", "so_ban"),
        Index("ix_van_ban_phap_che_tt", "trang_thai", "loai"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    # RỖNG ở phiên bản 1 cho tới khi nó được lưu; từ phiên bản 2 trở đi trỏ về id của phiên bản 1.
    # Dùng id của bản đầu làm "căn cước" của văn bản thay vì một bảng cha riêng: một bảng cha chỉ để
    # giữ một cái tên là một bảng phải nối thêm ở mọi truy vấn, đổi lấy không gì cả.
    goc_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    # TÊN LÀ `so_ban`, KHÔNG PHẢI `phien_ban`, và đó là một lựa chọn chứ không phải một chỗ đặt tên
    # vụng. Trong VTOS, `phien_ban` là tên dành riêng cho KHOÁ GHI MỘT LẦN (VPM-8): một bộ kiểm quét
    # mọi bảng mang cột ấy và đòi khai cửa sửa có khoá. Cột ở đây là SỐ BẢN của văn bản — dữ liệu
    # nghiệp vụ, người đọc và người ký nhìn thấy — không phải cơ chế chống ghi đè đồng thời. Dùng
    # chung một cái tên cho hai thứ khác nhau là làm người đọc mã sau này tin rằng chỗ này đã được
    # canh bằng khoá, trong khi không.
    so_ban: Mapped[int] = mapped_column(Integer, default=1)

    loai: Mapped[str] = mapped_column(String(30), index=True)      # LOAI_VAN_BAN
    so_hieu: Mapped[str] = mapped_column(String(60), default="")   # số hiệu do người khai đặt
    tieu_de: Mapped[str] = mapped_column(String(300))
    tom_tat: Mapped[str] = mapped_column(Text, default="")

    trang_thai: Mapped[str] = mapped_column(String(16), default="nhap", index=True)
    hieu_luc_tu: Mapped[date | None] = mapped_column(Date, nullable=True)
    hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Phiên bản đã thay thế bản này. RỖNG = chưa bị thay. Số bản thay cho biết LUÔN bản nào đã thay
    # nó; một cờ true/false thì không nói được điều đó.
    bi_thay_boi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ly_do_sua: Mapped[str] = mapped_column(Text, default="")

    nguoi_ky: Mapped[str] = mapped_column(String(80), default="")
    ngay_ky: Mapped[date | None] = mapped_column(Date, nullable=True)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class NghiaVuCongBo(Base):
    """Một nghĩa vụ công bố thông tin. BẢNG BẮT ĐẦU RỖNG – xem chú thích đầu tệp."""
    __tablename__ = "nghia_vu_cong_bo"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(300))
    # Điều khoản pháp luật làm căn cứ, do Pháp chế ghi. Không có căn cứ thì không biết vì sao nghĩa
    # vụ này tồn tại, và một nghĩa vụ không ai nhớ vì sao có là nghĩa vụ sẽ bị bỏ khi bận.
    can_cu: Mapped[str] = mapped_column(Text, default="")
    chu_ky: Mapped[str] = mapped_column(String(16), default="su_kien")   # CHU_KY_CONG_BO
    # Số ngày kể từ mốc phát sinh. RỖNG nghĩa là hạn KHÔNG tính bằng số ngày (ví dụ "trong 24 giờ"
    # hoặc một mốc cố định trong năm) – lúc ấy `mo_ta_han` là nguồn duy nhất, và người lập bản ghi
    # tự điền hạn chốt. Rỗng ≠ 0 ngày.
    han_sau_ngay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mo_ta_han: Mapped[str] = mapped_column(Text, default="")
    dang_ap_dung: Mapped[bool] = mapped_column(Boolean, default=True)
    khai_boi: Mapped[str] = mapped_column(String(50), default="")
    khai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BanGhiCongBo(Base):
    """Một lần phải công bố: kỳ nào, hạn nào, đã công bố chưa, ở đâu, bằng văn bản nào."""
    __tablename__ = "ban_ghi_cong_bo"
    __table_args__ = (
        Index("ux_ban_ghi_cong_bo_ky", "nghia_vu_id", "ky", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    nghia_vu_id: Mapped[int] = mapped_column(ForeignKey("nghia_vu_cong_bo.id"), index=True)
    ky: Mapped[str] = mapped_column(String(30))              # "2026-Q3", "2026", hoặc mã sự kiện
    moc_phat_sinh: Mapped[date | None] = mapped_column(Date, nullable=True)
    # RỖNG = chưa xác định được hạn. Khác hẳn "hạn là hôm nay". Không bao giờ điền đoán.
    han_chot: Mapped[date | None] = mapped_column(Date, nullable=True)

    da_cong_bo_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    noi_cong_bo: Mapped[str] = mapped_column(String(160), default="")
    van_ban_id: Mapped[int | None] = mapped_column(ForeignKey("van_ban_phap_che.id"), nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
