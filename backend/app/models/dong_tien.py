"""Dòng tiền – DT-2: chốt số dư đã đối soát theo ngày.

VÌ SAO BẢNG NÀY PHẢI CÓ TRƯỚC HÀM TIỀN KHẢ DỤNG
------------------------------------------------
DT-1 đòi hàm tiền khả dụng "trả kèm mốc đối soát đến ngày…". Rà kho mã ngày 11/9/2026 thì không có
chỗ nào giữ câu ấy:

  · `BankAccount.opening_balance` là số dư ĐẦU KỲ khi khai tài khoản, không phải số dư hôm nay.
  · `BankTransaction` là luồng giao dịch SePay đẩy về. Cộng dồn nó ra được một con số, nhưng con số
    ấy KHÔNG phải "đã đối soát" – SePay có thể đẩy thiếu, đẩy muộn, hoặc đẩy trùng; và tài khoản nào
    không nối SePay thì không có dòng nào cả.
  · Quỹ tiền mặt: chỉ có `method = 'tien_mat'` trên từng phiếu thu/chi. Đó là PHƯƠNG THỨC của một
    giao dịch, không phải số dư quỹ đã đếm.

Khác nhau giữa "máy cộng ra" và "người đã đối soát" là khác nhau giữa một con số để tham khảo và một
con số dám mang đi quyết định chi tiền. Bảng dòng tiền là bảng để quyết định chi tiền.

Nên bảng này giữ LỜI KHAI CỦA KẾ TOÁN, không giữ số máy tự cộng: đến hết ngày X, tài khoản này còn
ngần này, tôi đã soát với sao kê/sổ quỹ, và đây là tên tôi. Máy vẫn cộng số của mình để ĐỐI CHIẾU và
kêu khi lệch – xem `so_may_cong` và `lech` – nhưng số đem dùng là số người ký.

BA ĐIỀU BẢNG NÀY CỐ Ý KHÔNG LÀM
--------------------------------
1. KHÔNG tự suy số dư cho ngày chưa ai chốt. Chưa chốt thì DT-1 trả RỖNG kèm lý do, không trả 0 và
   không nội suy từ ngày trước – nội suy nghĩa là bịa ra một mốc đối soát không ai từng làm.
2. KHÔNG bù trừ giữa hai pháp nhân. Mỗi dòng gắn `company_id`; thiếu pháp nhân là dòng KHÔNG dùng
   được, không mặc định về công ty mẹ.
3. KHÔNG sửa đè im lặng. Chốt lại cùng một (pháp nhân, nguồn tiền, ngày) là một dòng MỚI mang
   `thay_the_id` trỏ về dòng cũ, và dòng cũ chuyển sang `da_thay_the`. Sổ giữ cả hai – ai đã chốt
   nhầm và ai đã sửa là câu kiểm toán sẽ hỏi.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Nguồn tiền được chốt. Cố ý KHÔNG gộp "ngân hàng" thành một dòng: mỗi tài khoản đối soát với một
# bản sao kê riêng, và gộp lại thì lệch ở tài khoản nào cũng không tìm ra.
NGUON_TIEN = {
    "ngan_hang": "Tài khoản ngân hàng – đối soát với sao kê",
    "tien_mat": "Quỹ tiền mặt – đối soát với sổ quỹ đã kiểm kê",
}

TRANG_THAI_CHOT = {
    "hieu_luc": "Đang có hiệu lực",
    "da_thay_the": "Đã bị một bản chốt sau thay thế",
}


class ChotSoDu(Base):
    """Một lần Kế toán chốt: đến hết ngày này, nguồn tiền này của pháp nhân này còn ngần này.

    Khoá duy nhất đặt trên (pháp nhân, nguồn, tài khoản, ngày, trạng thái hiệu lực) – xem
    `__table_args__`. Nghĩa là MỘT ngày chỉ có MỘT bản chốt đang hiệu lực; muốn sửa thì chốt lại, và
    lần chốt cũ bị đánh dấu đã thay thế chứ không bị xoá.
    """

    __tablename__ = "chot_so_du"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pháp nhân. RỖNG là CHƯA XÁC ĐỊNH – không mặc định về công ty mẹ, và dòng rỗng không được cộng
    # vào tiền khả dụng của bất kỳ pháp nhân nào. Cùng quy ước với payment_requests.company_id.
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True)

    nguon: Mapped[str] = mapped_column(String(20), index=True)          # ngan_hang / tien_mat
    # Tài khoản ngân hàng được chốt. RỖNG khi nguon='tien_mat' – quỹ tiền mặt không có số tài khoản.
    tai_khoan_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_accounts_cat.id"), nullable=True, index=True)

    # "Đã đối soát đến hết ngày này". Đây chính là mốc DT-1 phải trả kèm.
    den_ngay: Mapped[date] = mapped_column(Date, index=True)

    # Số dư người ký. KHÔNG nullable: chốt mà không có số thì không phải một lần chốt.
    so_du: Mapped[float] = mapped_column(TIEN)

    # Số máy cộng được tại thời điểm chốt, để đối chiếu. RỖNG nghĩa là máy không cộng được – tài
    # khoản chưa nối SePay, hoặc quỹ tiền mặt. Rỗng ≠ 0: 0 là "máy cộng ra bằng không".
    so_may_cong: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # so_du − so_may_cong. Cũng RỖNG khi máy không cộng được. Ghi 0 khi đã đối chiếu và khớp –
    # "đã đối chiếu, khớp" khác hẳn "không đối chiếu được", và một ô rỗng không phân biệt được.
    lech: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Bắt buộc giải thích khi lệch khác 0. Dịch vụ chặn, không để ràng buộc ở cơ sở dữ liệu: lý do
    # là chuyện nghiệp vụ, và thông báo lỗi phải nói được người dùng cần làm gì.
    ly_do_lech: Mapped[str] = mapped_column(String(300), default="", server_default="")

    trang_thai: Mapped[str] = mapped_column(
        String(20), default="hieu_luc", server_default="hieu_luc", index=True)
    # Bản chốt này thay thế bản nào. RỖNG là bản chốt đầu tiên cho (pháp nhân, nguồn, tài khoản, ngày).
    thay_the_id: Mapped[int | None] = mapped_column(
        ForeignKey("chot_so_du.id"), nullable=True)

    boi: Mapped[str] = mapped_column(String(50))                        # người chốt – Kế toán
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ghi_chu: Mapped[str] = mapped_column(Text, default="", server_default="")

    __table_args__ = (
        # Một ngày, một nguồn, một tài khoản, một pháp nhân – chỉ MỘT bản chốt hiệu lực.
        #
        # `trang_thai` nằm trong khoá là có chủ đích: bản cũ chuyển sang 'da_thay_the' thì nó rời
        # khỏi ô khoá, và bản mới vào được. Không có nó thì mỗi lần sửa lại phải xoá bản cũ – tức là
        # xoá đúng thứ kiểm toán cần đọc.
        #
        # SQLite và PostgreSQL đều coi NULL khác NULL trong UNIQUE, nên dòng thiếu pháp nhân hoặc
        # thiếu tài khoản KHÔNG bị khoá này chặn. Phép chặn thật nằm ở dịch vụ, nơi nói được vì sao.
        UniqueConstraint("company_id", "nguon", "tai_khoan_id", "den_ngay", "trang_thai",
                         name="uq_chot_so_du_mot_ngay_mot_ban"),
    )


# ---------------------------------------------------------------- DT-5 và DT-6 · sổ nghĩa vụ tiền
#
# KHÔNG CÓ BẢNG Ở ĐÂY. Sổ nghĩa vụ là `NghiaVuThanhToan` trong `app/models/nghia_vu.py` của lằn
# VPM-11. Bản đầu của tệp này có một bảng `nghia_vu_tien` riêng; ngày 11/9/2026, khi gộp, thấy hai
# bản làm cùng một việc và bản VPM-11 hoàn chỉnh hơn, nên bỏ bản ở đây. Chi tiết lý do ghi trong
# `app/services/dong_tien.py`, cuối tệp.
#
# Hai sổ nghĩa vụ song song là hai con số nợ phải trả cho cùng một công ty, và không ai biết phải
# tin cái nào. Bỏ một bản sớm rẻ hơn hợp nhất hai bản sau.
