"""Đợt A2 – khúc cuối của chuỗi bảng lương: Kế toán CHI, tải Ủy nhiệm chi, máy đối chiếu, ghi ĐÃ TRẢ.

Chuỗi Chủ tịch chốt ngày 07/10/2026:

    máy tính nháp → AI kiểm cơ sở → HCNS KIỂM → trình
      → Chủ tịch HOẶC TGĐ ký        ← khóa bản chụp tại đây (Đợt A1)
      → ghi sổ → Kế toán CHI, tải UNC lên
      → AI đối chiếu → ghi nhận ĐÃ TRẢ (đủ / một phần / lỗi)     ← bảng này

VÌ SAO GẮN VÀO BẢN KHÓA, KHÔNG GẮN VÀO KỲ LƯƠNG

`ban_khoa_id` trỏ tới đúng bản chụp đã ký, không trỏ tới `payroll_runs`. Kỳ lương là một thứ còn
đổi được (mở kỳ, tính lại, ký lại thành bản 2); bản khóa thì không. Đối chiếu một lần chi với một
thứ còn đổi được nghĩa là kết luận "đã trả đủ" hôm nay có thể tự biến thành "trả thiếu" vào tháng
sau mà không ai đụng vào tiền. Gắn vào bản khóa thì câu hỏi luôn có dạng trả lời được: "lần chi này
trả cho BẢN NÀO", và nếu kỳ được ký lại thành bản 2 thì bản 2 là một việc phải đối chiếu lại, hiện
ra chứ không im.

VÌ SAO MỘT KỲ CÓ NHIỀU DÒNG

`lan` là lần chi. Trả lương hai đợt, trả bù một người bị sót, chuyển nhầm rồi chuyển lại – đều là
lần chi riêng. Gộp vào một dòng và cộng dồn số tiền là xóa mất câu "tiền ra khỏi tài khoản mấy lần",
mà đó là câu ngân hàng và kiểm toán hỏi trước tiên.

K2 – RỖNG KHÔNG PHẢI SỐ 0

`so_tien_unc` để trống khi máy chưa đọc được mặt UNC. Rỗng nghĩa là "chưa biết"; 0 nghĩa là "đã
biết, và bằng không". Điền 0 cho chỗ chưa biết là lỗi đã làm sổ báo lãi 100% trên 2,65 tỷ doanh thu.
"""
from datetime import datetime, date

from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Kết luận của một lần đối chiếu. Ba trạng thái Chủ tịch gọi tên ngày 07/10/2026.
KET_LUAN = {
    "du": "Đã trả đủ – tổng khớp và từng người khớp",
    "mot_phan": "Đã trả một phần – có người chưa nhận hoặc nhận thiếu",
    "loi": "Có lỗi – số tiền ra khỏi tài khoản không khớp bảng đã ký",
}

# Trạng thái trả tiền của CẢ KỲ, cộng lại từ các lần chi. Ghi lên payroll_runs.tra_trang_thai.
TRA_TRANG_THAI = {
    "": "Chưa chi",
    "dang_chi": "Đã chi một phần – còn người chưa nhận đủ",
    "da_tra_du": "Đã trả đủ cho tất cả",
    "loi_chi": "Có lần chi sai số – cần kế toán xử lý",
}


class ChiKyLuong(Base):
    """Một lần kế toán chi lương cho một bản khóa, kèm UNC và kết quả máy đối chiếu."""
    __tablename__ = "chi_ky_luong"
    __table_args__ = (
        Index("ix_chi_ky_luong_ky_lan", "period", "lan", unique=True),
        Index("ix_chi_ky_luong_ban_khoa", "ban_khoa_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    # Bản chụp đã ký mà lần chi này trả cho. Xem chú thích đầu tệp.
    ban_khoa_id: Mapped[int] = mapped_column(ForeignKey("bang_luong_khoa.id"))
    lan: Mapped[int] = mapped_column(Integer, default=1)

    # ---- MẶT UỶ NHIỆM CHI ----
    # Không có một trường nào ở đây là dữ liệu của người lao động: số tài khoản dưới đây là tài khoản
    # CHI của công ty, không phải tài khoản người nhận.
    unc_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    ngan_hang: Mapped[str] = mapped_column(String(60), default="")
    tai_khoan_cong_ty: Mapped[str] = mapped_column(String(40), default="")
    ngay_chuyen: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_tham_chieu: Mapped[str] = mapped_column(String(80), default="")
    so_tien_unc: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # K2: rỗng ≠ 0
    noi_dung_unc: Mapped[str] = mapped_column(String(300), default="")

    # ---- PHỤ LỤC DANH SÁCH TỪNG NGƯỜI ----
    # Mở đọc bằng máy theo chữ ký Chủ tịch 07/10/2026, và mở HẸP: chỉ HỌ TÊN và SỐ TIỀN.
    # Khai ở models/doc_chung_tu.py::MO_DOC_CO_CHU_KY, có phép thử canh.
    phu_luc_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    dong_phu_luc: Mapped[list] = mapped_column(JSON, default=list)   # [{"ho_ten": ..., "so_tien": ...}]
    phu_luc_ai_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phu_luc_ghi_chu: Mapped[str] = mapped_column(Text, default="")

    # ---- KẾT QUẢ ĐỐI CHIẾU ----
    ket_luan: Mapped[str] = mapped_column(String(12), default="", index=True)   # KET_LUAN
    ket_qua: Mapped[dict] = mapped_column(JSON, default=dict)
    doi_chieu_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    chi_boi: Mapped[str] = mapped_column(String(50), default="")
    chi_vai: Mapped[str] = mapped_column(String(30), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
