"""Phân bổ MỘT khoản tiền vào cho NHIỀU booking.

Trước 11/9/2026, một khoản tiền chỉ gắn được đúng một booking: `receipts.booking_id` và
`bank_transactions.booking_id` đều là khoá ĐƠN. Khách chuyển một lần cho hai tour thì kế toán không
có chỗ để nói điều đó — đường duy nhất là gán cả khoản cho một booking rồi chữa bằng ghi chú, hoặc
chờ khách chuyển lại. Đây không phải chỗ làm chưa đẹp; đây là việc hệ thống KHÔNG làm được.

Khuôn lấy nguyên từ bảng `retentions` (tiền bảo lưu): ở đó đã có sẵn cặp `remaining` +
`applied_booking_id`, tức là ý niệm "một khoản tiền tiêu dần" đã tồn tại trong kho từ trước. Nhân nó
ra cho tiền vào, không thiết kế một ý niệm thứ hai cho cùng một việc.

────────────────────────────────────────────────────────────────────────────────
BA QUYẾT ĐỊNH ĐÁNG GHI LẠI
────────────────────────────────────────────────────────────────────────────────

MỘT — dòng phân bổ KHÔNG thay phiếu thu, nó SINH RA phiếu thu. Mỗi dòng phân bổ tạo đúng một
`Receipt` cho booking ấy. Lý do: phiếu thu là chứng từ kế toán theo mẫu 01-TT, đã nối vào sổ và vào
`booking.paid`; dựng một đường tiền thứ hai không đi qua phiếu thu là tạo ra hai câu trả lời cho
"booking này đã thu bao nhiêu".

HAI — HUỶ, KHÔNG XOÁ. Phân bổ sai thì đánh dấu huỷ kèm lý do và người huỷ; phiếu thu tương ứng
chuyển trạng thái `huy`. Xoá dòng là xoá mất bằng chứng rằng tiền đã từng được hiểu sai — mà đó
chính là thứ người đi tra cứu về sau cần thấy.

BA — số dư chưa phân bổ được LƯU, không chỉ tính ra khi cần. Lệnh giao việc đòi nó "HIỆN ĐƯỢC trên
màn hình, không phải suy ra". Cột lưu thì có nguy cơ lệch với tổng các dòng, nên có một phép thử
canh đúng chỗ ấy: tính lại từ các dòng và bắt buộc khớp tuyệt đối.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


class PhanBoTien(Base):
    """Một dòng: khoản tiền X được hiểu là trả cho booking Y, số tiền Z."""
    __tablename__ = "phan_bo_tien"
    __table_args__ = (Index("ix_phan_bo_tien_txn_huy", "bank_txn_id", "huy"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_txn_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"), index=True)
    # ĐỢT E5 13/10/2026 — HAI NHÁNH, ĐÚNG MỘT NHÁNH ĐƯỢC ĐIỀN.
    #
    # Trước đợt này `booking_id` là cột BẮT BUỘC, nên bảng chỉ nhận được tiền VÀO: chi nhà cung
    # cấp, lương, thuế, trả gốc vay không có chỗ nào nói khoản tiền ấy trả cho nghĩa vụ nào —
    # trong khi sổ nghĩa vụ đã khai đủ 13 nhóm, có cả bốn nhóm ấy.
    #
    # VÌ SAO NỚI BẢNG NÀY MÀ KHÔNG DỰNG BẢNG THỨ HAI: "một khoản tiền chia cho nhiều chỗ" là MỘT
    # ý niệm. Dựng bảng thứ hai cho cùng ý niệm là tạo hai câu trả lời cho câu hỏi "khoản tiền
    # này đã phân bổ bao nhiêu" — và hai câu trả lời thì sớm muộn lệch nhau.
    #
    # Luật đúng-một-nhánh KHÔNG đặt bằng CHECK ở cơ sở dữ liệu mà đặt ở `_nhanh_cua` trong
    # services, vì nó phải nói ra được bằng tiếng người lúc sai; phép thử canh cả hai chiều.
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    nghia_vu_id: Mapped[int | None] = mapped_column(ForeignKey("nghia_vu_thanh_toan.id"), nullable=True, index=True)
    # Đợt là tuỳ chọn NGAY CẢ khi đã chọn nghĩa vụ: một nghĩa vụ không chia đợt vẫn trả được.
    dot_id: Mapped[int | None] = mapped_column(ForeignKey("dot_thanh_toan.id"), nullable=True, index=True)
    # Phiếu thu do chính dòng này sinh ra. Để RỖNG chỉ xảy ra khi lập phiếu thu hỏng – và khi ấy dòng
    # phân bổ cũng không được ghi, nên rỗng ở đây là dấu hiệu dữ liệu cũ, không phải trạng thái bình thường.
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"), nullable=True)
    so_tien: Mapped[float] = mapped_column(TIEN)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Huỷ chứ không xoá – xem chú thích "HAI" ở đầu tệp.
    huy: Mapped[bool] = mapped_column(Boolean, default=False)
    huy_boi: Mapped[str] = mapped_column(String(50), default="")
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    huy_ly_do: Mapped[str] = mapped_column(String(300), default="")

    def con_hieu_luc(self) -> bool:
        return not self.huy

    def nhanh(self) -> str:
        """`booking` hay `nghia_vu` — đọc từ chính dữ liệu, không từ một cột cờ riêng.

        Một cột cờ nói nhánh nào là một chỗ nữa để sai: nó có thể nói `booking` trong khi
        `booking_id` rỗng. Suy từ dữ liệu thì không lệch được.
        """
        if self.booking_id is not None:
            return "booking"
        if self.nghia_vu_id is not None:
            return "nghia_vu"
        return ""
