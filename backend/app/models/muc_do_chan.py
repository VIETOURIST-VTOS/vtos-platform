"""Đợt E1 – bảng MỨC ĐỘ CHẶN: mỗi phép kiểm một dòng, Kế toán đặt mức.

Học từ MISA (đọc AMIS Kế toán của Vietourist Holdings ngày 09/10/2026). Trong MISA mọi phép kiểm
đều có một tham số ba mức do người dùng đặt, không phải một quyết định nằm trong mã:

    "Cảnh báo khi chi quá số tiền tồn tiền mặt hoặc tiền gửi"   → Cảnh báo và CÓ ghi sổ
    "Cảnh báo khi nhập trùng hóa đơn đầu vào"                   → Cảnh báo và CÓ cho cất
    "Cảnh báo nếu không nhập Email/SĐT nhân viên"               → Cảnh báo và KHÔNG cho cất

Vì sao chép cách ấy: suốt hai bản rà soát TC–KT, câu hỏi "cửa này chặn cứng hay chỉ cảnh báo"
được tranh luận ở cả hai phía, và CẢ HAI BÊN ĐỀU KHÔNG NÊN QUYẾT. Chặn quá tay thì nghiệp vụ hợp
lệ bị kẹt; cảnh báo suông thì sáu tháng sau không ai đọc. Người chịu trách nhiệm số liệu là người
đặt mức — robot viết bộ kiểm, không đặt mức.

BA ĐIỀU BẢNG NÀY CỐ Ý LÀM:

  · `muc_do` ĐỂ TRỐNG ĐƯỢC. Trống = CHƯA AI ĐẶT, không phải "không chặn". Phép kiểm chưa ai đặt
    mức thì chạy ở mức nhẹ nhất (ghi nhận, cho qua) NHƯNG bị đếm lên bảng "phép kiểm chưa đặt
    mức" – xem `services/ke_toan_chieu.phep_kiem_chua_dat_muc`. Im lặng mới là hỏng; cho qua mà
    có người đếm thì không.
  · BỐN LUẬT CỨNG KHÔNG CÓ DÒNG Ở ĐÂY. Sai pháp nhân, sai quyền, chi quá dư nghĩa vụ, nguồn
    trùng thật – bốn thứ này luôn chặn và không tham số hoá được. Có phép thử canh để không ai
    lén đưa chúng vào bảng rồi hạ mức.
  · Mỗi dòng phải nói AI xử lý và TRONG BAO LÂU. Một cảnh báo không có người và không có hạn là
    một dòng chữ, không phải một kiểm soát.

Bảng bắt đầu RỖNG (ranh giới 09/9/2026). Cửa nhập nằm trên màn hình /ket-so.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

MUC_DO = {
    "khong_canh_bao": "Không cảnh báo",
    "canh_bao_cho_qua": "Cảnh báo nhưng cho qua",
    "canh_bao_va_chan": "Cảnh báo và chặn",
}

# Mức áp dụng khi chưa ai đặt. Nhẹ nhất, nhưng KHÔNG im lặng: phép kiểm ở trạng thái này bị đếm
# lên cho tới khi có người ký.
MUC_DO_KHI_CHUA_KHAI = "canh_bao_cho_qua"

# Bốn luật cứng. KHÔNG được có dòng trong bảng muc_do_chan – xem test_le1.
LUAT_CUNG = (
    "sai_phap_nhan",
    "sai_quyen",
    "chi_qua_du_nghia_vu",
    "nguon_trung_that",
)


class MucDoChan(Base):
    """Một phép kiểm và mức chặn của nó. Robot viết phép kiểm; người có thẩm quyền đặt mức."""

    __tablename__ = "muc_do_chan"

    id: Mapped[int] = mapped_column(primary_key=True)
    ma_phep_kiem: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(200))
    mo_ta: Mapped[str] = mapped_column(Text, default="")

    # RỖNG = chưa ai đặt mức. Không phải "không chặn" – xem MUC_DO_KHI_CHUA_KHAI và phép đếm.
    muc_do: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Một cảnh báo không có người và không có hạn thì không phải kiểm soát.
    nguoi_xu_ly: Mapped[str] = mapped_column(String(40), default="")       # mã vai trò
    han_xu_ly_ngay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nguoi_thay_the: Mapped[str] = mapped_column(String(40), default="")    # vai thay khi quá hạn

    ngay_hieu_luc: Mapped[date | None] = mapped_column(Date, nullable=True)
    nguoi_ky: Mapped[str] = mapped_column(String(50), default="")
    can_cu: Mapped[str] = mapped_column(String(200), default="")

    dang_ap_dung: Mapped[bool] = mapped_column(Boolean, default=True)
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
