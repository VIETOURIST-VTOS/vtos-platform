"""Đối tác bán hàng — bên ngoài công ty, bán được tour, KHÔNG đăng nhập được.

VÌ SAO KHÔNG DÙNG MỘT TÀI KHOẢN `User`

Trong VTOS, "người bán" của một booking là một dòng trong bảng `users`. Mà một dòng trong `users`
nghĩa là MỘT TÀI KHOẢN ĐĂNG NHẬP: có `password_hash`, có vai trò, mở được màn hình. Tạo tài khoản
cho J Travel hay JTV là mở cửa hệ thống cho người ngoài công ty — chỉ để ghi nhận họ bán được mấy
chuyến.

Đo trên máy thật 19/9/2026 mới thấy chuyện ấy đã bắt đầu xảy ra: trong 220 tài khoản có sẵn một
dòng tên `ĐỐI_TÁC` mang vai `nv_kd`. Nghĩa là ai đó đã phải lách, vì hệ thống không có chỗ cho đối
tác. Bảng này là cái chỗ ấy.

BA QUYẾT ĐỊNH ĐÁNG GHI LẠI

MỘT — KHÔNG CÓ MẬT KHẨU, KHÔNG CÓ VAI TRÒ. Đối tác không đăng nhập. Thiếu hai cột ấy là hàng rào
chắc nhất: không ai vô tình cấp quyền cho một dòng ở bảng này được, vì không có gì để cấp.

HAI — DOANH THU ĐỐI TÁC KHÔNG VÀO CHỈ TIÊU AI, NHƯNG PHẢI ĐẾM ĐƯỢC. Anh Tuấn 19/9/2026: bốn cái tên
J TRAVEL, JTV, JTRAVEL, VTOURIST là "đối tác hợp tác bán tour ghép lẻ", và riêng chúng đã gánh
khoảng 3,5 tỷ. Trước vòng này hệ thống chỉ có hai ngăn — một tài khoản nhân viên, hoặc "không phải
nhân viên" — nên tiền ấy rơi chung vào ngăn "chưa xác định".

Gộp "đối tác" với "chưa xác định" là mất hẳn một câu trả lời: *đã biết ai bán* khác *chưa biết ai
bán*. Sang năm hỏi "công ty bán qua đối tác bao nhiêu" thì không ai trả lời được, mà ghép lẻ với
đối tác là việc còn làm dài chứ không phải rác của lô dữ liệu cũ.

BA — CÓ HIỆU LỰC TỪ–ĐẾN, KHÔNG XOÁ. Hợp tác có lúc bắt đầu và có lúc dừng. Xoá một đối tác là xoá
nghĩa của mọi booking từng gắn vào họ. `hieu_luc_den` đóng lại; lịch sử vẫn đọc được. Cùng nếp với
`Company`, `DonViKD` và nhật ký giữ chỗ.

BẢNG NÀY KHÔNG GIỮ SỐ TIỀN NÀO. Tiền nằm ở `bookings.amount` như mọi booking khác; cột
`bookings.doi_tac_id` chỉ nói booking ấy do đối tác nào bán. Hoa hồng và công nợ đối tác là việc
riêng, chưa thuộc vòng này.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Kiểu hợp tác. Cố ý ngắn và mở rộng được: mỗi kiểu thêm vào đây phải trả lời được câu "cách tính
# tiền với họ khác gì nhau", nếu không thì nó chỉ là một cái nhãn.
LOAI = ("ghep_le", "dai_ly", "san_ve", "ctv_ban_hang", "khac")

NHAN_LOAI = {
    "ghep_le": "Đối tác ghép lẻ",
    "dai_ly": "Đại lý",
    "san_ve": "Sàn bán vé",
    # DH-1 26/10/2026 — cá nhân giới thiệu / bán tour hưởng hoa hồng D06 (2% / 2,5% / 3%). KHÁC «CTV»
    # hướng dẫn viên tự do ở phòng HDV: hai nghĩa của cùng một chữ, nên tên đầy đủ là «CTV bán hàng».
    "ctv_ban_hang": "CTV bán hàng",
    "khac": "Khác",
}


class DoiTacBanHang(Base):
    """Một đối tác bán hàng. Không phải nhân viên, không phải tài khoản đăng nhập."""
    __tablename__ = "doi_tac_ban_hang"
    __table_args__ = (Index("ix_doi_tac_ban_hang_hieu_luc", "hieu_luc_tu", "hieu_luc_den"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(160))
    loai: Mapped[str] = mapped_column(String(16), default="ghep_le")

    lien_he: Mapped[str] = mapped_column(String(160), default="")
    dien_thoai: Mapped[str] = mapped_column(String(30), default="")
    ma_so_thue: Mapped[str] = mapped_column(String(20), default="")

    hieu_luc_tu: Mapped[date] = mapped_column(Date)
    hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)

    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(64), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def dang_hieu_luc(self, ngay: date) -> bool:
        """`hieu_luc_den` rỗng = còn hợp tác. RỖNG KHÁC KHÔNG."""
        if ngay < self.hieu_luc_tu:
            return False
        return self.hieu_luc_den is None or ngay <= self.hieu_luc_den
