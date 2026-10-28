"""CD-1 · Cổng Cổ đông đợt 1 (Chủ tịch duyệt bản xem thử 28/10/2026; màn CD01, CD07–CD10, CD14–CD15 bộ v3.2).

Bốn bảng, cả bốn bắt đầu RỖNG (ranh giới 09/9/2026: phần mềm viết cấu trúc, người nhập số liệu):

  1. `tai_lieu_cong_co_dong` — tài liệu đang hiện trên cổng. Mỗi dòng ĐỨNG TRÊN một bản ghi công bố
     ĐÃ CÔNG BỐ (Đợt D1, `ban_ghi_cong_bo`). Không có cửa nào đưa tài liệu lên cổng mà không qua bản
     ghi ấy — một tài liệu chưa công bố hiện cho cổ đông là tiết lộ chọn lọc.
  2. `su_kien_co_dong` — đại hội và sự kiện do IR – Pháp chế tạo.
  3. `quan_tam_su_kien` — cổ đông «ghi nhận quan tâm». KHÔNG phải đăng ký tham dự, KHÔNG phải ủy
     quyền, KHÔNG phải biểu quyết.
  4. `yeu_cau_ir` — câu hỏi cổ đông gửi IR, và câu trả lời.

KHÔNG có cột số cổ phần ở đâu cả — cùng lý do với `lien_he_nha_dau_tu`: sở hữu là dữ liệu của sổ cổ đông.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

NHOM_TAI_LIEU = {
    "tai_chinh": "Báo cáo tài chính",
    "thuong_nien": "Báo cáo thường niên",
    "nghi_quyet": "Nghị quyết / thông báo",
    "quan_tri": "Quản trị",
    "quyen": "Thông báo thực hiện quyền",
    "dai_hoi": "Tài liệu đại hội",
    "khac": "Khác",
}
PHAM_VI = {"cong_khai": "Công khai", "co_dong": "Chỉ cổ đông"}
TRANG_THAI_TAI_LIEU = {"hien": "Đang hiện", "thay_the": "Đã có bản thay", "go": "Đã gỡ"}

LOAI_SU_KIEN = {
    "dhdcd_thuong_nien": "Đại hội đồng cổ đông thường niên",
    "dhdcd_bat_thuong": "Đại hội đồng cổ đông bất thường",
    "gap_go": "Gặp gỡ cổ đông",
    "khac": "Sự kiện khác",
}
TRANG_THAI_SU_KIEN = {"nhap": "Bản nháp", "cong_bo": "Đã thông báo", "huy": "Đã hủy"}

CHU_DE_IR = {
    "tai_lieu": "Tài liệu công bố",
    "su_kien": "Đại hội / sự kiện",
    "tu_cach": "Tư cách / hồ sơ cổ đông",
    "quyen_loi": "Quyền lợi cổ đông",
    "khac": "Khác",
}
TRANG_THAI_IR = {"cho": "Chờ trả lời", "da_tra_loi": "Đã trả lời", "dong": "Đã đóng"}


class TaiLieuCongCoDong(Base):
    __tablename__ = "tai_lieu_cong_co_dong"
    __table_args__ = (Index("ix_tai_lieu_cong_co_dong_tt_pv", "trang_thai", "pham_vi"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ban_ghi_id: Mapped[int] = mapped_column(ForeignKey("ban_ghi_cong_bo.id"), index=True)
    tieu_de: Mapped[str] = mapped_column(String(300))
    nhom: Mapped[str] = mapped_column(String(20), default="khac")
    pham_vi: Mapped[str] = mapped_column(String(12), default="co_dong")
    # Tệp PDF người đưa lên — lưu qua kho tệp chung (attachments), đối chiếu băm mỗi lần đọc.
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))
    # Bản thay: tài liệu đang hiện bị thay bởi dòng này. Dòng cũ đổi sang `thay_the`, KHÔNG xoá.
    thay_cho_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ly_do_thay: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(10), default="hien")
    dang_boi: Mapped[str] = mapped_column(String(50), default="")
    dang_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    go_boi: Mapped[str] = mapped_column(String(50), default="")
    go_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_go: Mapped[str] = mapped_column(Text, default="")


class SuKienCoDong(Base):
    __tablename__ = "su_kien_co_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ten: Mapped[str] = mapped_column(String(200))
    loai: Mapped[str] = mapped_column(String(20), default="gap_go")
    bat_dau: Mapped[datetime] = mapped_column(DateTime, index=True)
    dia_diem: Mapped[str] = mapped_column(String(200), default="")
    ngay_chot_ds: Mapped[date | None] = mapped_column(Date, nullable=True)
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    # id các tài liệu trên cổng gắn với sự kiện (thư mời, chương trình họp…). Chỉ tài liệu đang hiện mới ra cổng.
    tai_lieu_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    nhan_quan_tam: Mapped[bool] = mapped_column(Boolean, default=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="nhap", index=True)
    ly_do_huy: Mapped[str] = mapped_column(Text, default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuanTamSuKien(Base):
    __tablename__ = "quan_tam_su_kien"
    __table_args__ = (UniqueConstraint("su_kien_id", "tai_khoan_id", name="uq_quan_tam_su_kien"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    su_kien_id: Mapped[int] = mapped_column(ForeignKey("su_kien_co_dong.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Bỏ quan tâm không xoá dòng: IR cần biết ai đã từng báo quan tâm rồi rút.
    bo_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class YeuCauIr(Base):
    __tablename__ = "yeu_cau_ir"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    chu_de: Mapped[str] = mapped_column(String(12), default="khac")
    noi_dung: Mapped[str] = mapped_column(Text)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho", index=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    # Người trả lời tự xác nhận câu trả lời không chứa thông tin chưa công bố. Thiếu thì máy chủ không nhận.
    xac_nhan_da_cong_bo: Mapped[bool] = mapped_column(Boolean, default=False)
    tra_loi_boi: Mapped[str] = mapped_column(String(50), default="")
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_dong: Mapped[str] = mapped_column(Text, default="")
    # CD-2: giấy tờ cổ đông gửi kèm khi xin xác minh sở hữu (kho tệp chung, dữ liệu cá nhân).
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------------------------------------------------------------- CD-2 · sổ cổ đông (Chủ tịch duyệt 28/10/2026)
# Số cổ phần CHỈ đến từ danh sách người sở hữu VSD do IR – Pháp chế tải lên và Chủ tịch duyệt — không có ô gõ
# số. Lô duyệt mới nhất là danh sách đang dùng; lô cũ giữ để tra. Số giấy tờ là dữ liệu cá nhân (NĐ 13/2023).
TRANG_THAI_LO_SCD = {"cho_duyet": "Chờ Chủ tịch duyệt", "da_duyet": "Đã duyệt", "tu_choi": "Từ chối"}


class LoSoCoDong(Base):
    __tablename__ = "lo_so_co_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    ngay_can_cu: Mapped[date] = mapped_column(Date, index=True)
    ten_tep: Mapped[str] = mapped_column(String(200), default="")
    bam_tep: Mapped[str] = mapped_column(String(64), index=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="cho_duyet", index=True)
    so_dong: Mapped[int] = mapped_column(Integer, default=0)
    tong_cp: Mapped[int] = mapped_column(BigInteger, default=0)
    loi: Mapped[list | None] = mapped_column(JSON, nullable=True)
    nap_boi: Mapped[str] = mapped_column(String(50), default="")
    nap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do: Mapped[str] = mapped_column(Text, default="")


class DongSoCoDong(Base):
    __tablename__ = "dong_so_co_dong"
    __table_args__ = (Index("ix_dong_so_co_dong_lo_gt", "lo_id", "giay_to"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lo_id: Mapped[int] = mapped_column(ForeignKey("lo_so_co_dong.id"), index=True)
    ho_ten: Mapped[str] = mapped_column(String(200), default="")
    giay_to: Mapped[str] = mapped_column(String(40))          # CCCD / ĐKKD đã chuẩn hóa (bỏ dấu cách, chấm, gạch)
    so_cp: Mapped[int] = mapped_column(BigInteger, default=0)
    tk_luu_ky: Mapped[str] = mapped_column(String(40), default="")


class NoiSoCoDong(Base):
    """Tài khoản cổ đông ↔ số giấy tờ trong sổ. Một tài khoản một dòng nối đang hiệu lực; gỡ có lý do, không xoá."""
    __tablename__ = "noi_so_co_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    giay_to: Mapped[str] = mapped_column(String(40), index=True)
    noi_boi: Mapped[str] = mapped_column(String(50), default="")
    noi_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    go_boi: Mapped[str] = mapped_column(String(50), default="")
    go_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_go: Mapped[str] = mapped_column(Text, default="")
