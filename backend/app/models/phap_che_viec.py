"""Đợt D2 – bàn làm việc của Pháp chế: yêu cầu, rà soát hợp đồng, sổ chữ ký, xác nhận chủ số liệu.

Đợt D1 dựng chỗ để GIỮ kết quả (văn bản, sổ công bố). Đợt này dựng chỗ để thấy VIỆC ĐANG CHẠY —
và một việc đang chạy chỉ có ích nếu nó không biến mất khi người ta quên.

  1. `yeu_cau_phap_che`   – ai hỏi Pháp chế việc gì, từ bao giờ, và đã trả lời chưa.
  2. `ra_soat_hop_dong`   – một lần rà soát hợp đồng: kết luận và ĐIỀU KIỆN kèm theo.
  3. `ban_ghi_chu_ky`     – ai ký cái gì, ngày nào, THEO THẨM QUYỀN NÀO.
  4. `xac_nhan_chu_so_lieu` – trước khi công bố một con số, người chủ con số ấy xác nhận.

Bốn bảng đều BẮT ĐẦU RỖNG. Không nạp sẵn một dòng nào – ranh giới 09/9/2026.

KHÔNG có cột pháp nhân, giống D1: Pháp chế của tập đoàn làm việc cho cả tập đoàn (Chủ tịch chốt
08/10/2026). Không có cột `phien_ban` nào: tên ấy dành riêng cho khoá ghi một lần (VPM-8).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

LOAI_YEU_CAU = {
    "ra_soat_hop_dong": "Rà soát hợp đồng",
    "y_kien_phap_ly": "Xin ý kiến pháp lý",
    "soan_thao": "Soạn thảo văn bản",
    "ho_so_cong_bo": "Hồ sơ công bố thông tin",
    "tranh_chap": "Tranh chấp / khiếu nại",
    "khac": "Việc khác",
}

# Trạng thái của một yêu cầu. KHÔNG có "đã xong" nào mà người gõ thẳng vào: mỗi bước là một cửa
# riêng, và cửa đóng việc đòi phải ghi kết quả.
TRANG_THAI_YC = {
    "moi": "Mới gửi, chưa ai nhận",
    "dang_xu_ly": "Đã có người nhận, đang làm",
    "cho_bo_sung": "Chờ bên gửi bổ sung",
    "xong": "Đã trả kết quả",
    "tu_choi": "Không nhận – có ghi lý do",
}

MUC_DO = {"thuong": "Thường", "gap": "Gấp"}

# Kết luận rà soát. Ba mức, và mức giữa là mức hay bị nói trại thành mức trên.
KET_LUAN_RS = {
    "dat": "Đạt – ký được như hiện trạng",
    "dat_co_dieu_kien": "Đạt CÓ ĐIỀU KIỆN – phải sửa/bổ sung trước khi ký",
    "khong_dat": "Không đạt",
}

MUC_RUI_RO = {"cao": "Cao", "trung_binh": "Trung bình", "thap": "Thấp"}

LOAI_CHU_KY = {
    "tuoi": "Chữ ký tươi",
    "so": "Chữ ký số",
    "dau_treo": "Đóng dấu treo",
    "dau_giap_lai": "Đóng dấu giáp lai",
    "uy_quyen": "Ký theo uỷ quyền",
}

TRANG_THAI_XN = {
    "cho": "Chờ chủ số liệu xác nhận",
    "xac_nhan": "Đã xác nhận",
    "tu_choi": "Từ chối xác nhận – có ý kiến",
}


class YeuCauPhapChe(Base):
    """Một việc gửi tới Pháp chế. Bảng bắt đầu rỗng; mỗi dòng do người dùng khai qua cửa nhập."""
    __tablename__ = "yeu_cau_phap_che"
    __table_args__ = (
        Index("ix_yeu_cau_phap_che_tt", "trang_thai", "muc_do"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(30), index=True)        # LOAI_YEU_CAU
    tieu_de: Mapped[str] = mapped_column(String(300))
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    # Ai hỏi. Pháp chế ghi lại chứ không đoán: một việc không biết của ai thì không trả cho ai được.
    phong_gui: Mapped[str] = mapped_column(String(80), default="")
    nguoi_gui: Mapped[str] = mapped_column(String(80), default="")
    muc_do: Mapped[str] = mapped_column(String(10), default="thuong")
    # Hạn MONG MUỐN của bên gửi – không phải hạn pháp lý. Hai thứ ấy khác nhau và không trộn chung
    # một cột: hạn pháp lý nằm ở `nghia_vu_cong_bo` của Đợt D1, có căn cứ điều khoản đi kèm.
    han_mong_muon: Mapped[date | None] = mapped_column(Date, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(16), default="moi", index=True)
    nguoi_nhan: Mapped[str] = mapped_column(String(50), default="")
    nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    dong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RaSoatHopDong(Base):
    """Một lần rà soát hợp đồng, treo vào một yêu cầu."""
    __tablename__ = "ra_soat_hop_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    yeu_cau_id: Mapped[int] = mapped_column(ForeignKey("yeu_cau_phap_che.id"), index=True)
    so_hop_dong: Mapped[str] = mapped_column(String(80), default="")
    doi_tac: Mapped[str] = mapped_column(String(200), default="")
    loai_hop_dong: Mapped[str] = mapped_column(String(80), default="")
    # K2: RỖNG ≠ 0. Hợp đồng chưa biết giá trị khác hẳn hợp đồng giá trị 0. Không default.
    gia_tri: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    ngay_nhan: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_tra: Mapped[date | None] = mapped_column(Date, nullable=True)

    ket_luan: Mapped[str] = mapped_column(String(20), default="")    # KET_LUAN_RS
    # Danh sách rủi ro: [{"muc": "cao", "noi_dung": "...", "dieu_khoan": "..."}]
    rui_ro: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # BẮT BUỘC khi kết luận là "đạt có điều kiện" – xem services. Một kết luận "đạt có điều kiện"
    # mà không viết ra điều kiện thì khi đọc lại chỉ còn chữ "đạt".
    dieu_kien: Mapped[str] = mapped_column(Text, default="")
    nguoi_ra_soat: Mapped[str] = mapped_column(String(50), default="")
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BanGhiChuKy(Base):
    """Sổ chữ ký: ai ký cái gì, ngày nào, THEO THẨM QUYỀN NÀO."""
    __tablename__ = "ban_ghi_chu_ky"
    __table_args__ = (
        Index("ix_ban_ghi_chu_ky_ngay", "ngay_ky", "nguoi_ky"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    # Trỏ về một văn bản trong sổ của D1 nếu có; không thì mô tả bằng lời.
    van_ban_id: Mapped[int | None] = mapped_column(ForeignKey("van_ban_phap_che.id"), nullable=True)
    mo_ta: Mapped[str] = mapped_column(String(300), default="")
    nguoi_ky: Mapped[str] = mapped_column(String(80))
    chuc_danh: Mapped[str] = mapped_column(String(120), default="")
    ngay_ky: Mapped[date] = mapped_column(Date, index=True)
    loai_chu_ky: Mapped[str] = mapped_column(String(20), default="tuoi")
    # BẮT BUỘC, và đây là lý do bảng này tồn tại. Một chữ ký không nói được ký theo thẩm quyền nào
    # chính là câu hỏi đầu tiên của mọi lần soát lại – điều lệ, nghị quyết, hay giấy uỷ quyền nào.
    can_cu_tham_quyen: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class XacNhanChuSoLieu(Base):
    """Một con số trong hồ sơ công bố, và người chịu trách nhiệm về nó đã xác nhận hay chưa.

    Đây là chỗ nối lại với Đợt D1: một bản ghi công bố còn xác nhận ở trạng thái "chờ" thì cửa
    "ghi đã công bố" KHÔNG mở. Pháp chế không phải là người biết doanh thu quý đúng hay sai –
    người biết là chủ con số, và chữ ký của họ phải có trước khi con số ra khỏi công ty.
    """
    __tablename__ = "xac_nhan_chu_so_lieu"
    __table_args__ = (
        Index("ux_xac_nhan_chu_so_lieu", "ban_ghi_id", "chi_muc", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ban_ghi_id: Mapped[int] = mapped_column(ForeignKey("ban_ghi_cong_bo.id"), index=True)
    chi_muc: Mapped[str] = mapped_column(String(160))     # con số / mục nào
    chu_so_lieu: Mapped[str] = mapped_column(String(80))  # phòng hoặc người chịu trách nhiệm
    trang_thai: Mapped[str] = mapped_column(String(16), default="cho", index=True)
    y_kien: Mapped[str] = mapped_column(Text, default="")
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
