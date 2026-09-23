"""Chỉ tiêu doanh thu của khối Kinh doanh — giao cho một ĐƠN VỊ hoặc một NGƯỜI, theo kỳ và luồng.

VÌ SAO KHÔNG DÙNG LẠI `ke_hoach_thang` (TC-41)

Hai bảng trông giống nhau và cố ý khác nhau. `ke_hoach_thang` giao chỉ tiêu cho một PHÁP NHÂN —
doanh thu và lợi nhuận trước thuế của Vietourist, của Vietrip, theo tháng. Bảng này giao chỉ tiêu
cho một ĐƠN VỊ KINH DOANH hoặc một NGƯỜI — team KD1 tháng 10 bao nhiêu, chị Vân Anh bao nhiêu.

Trộn hai thứ vào một bảng thì cột `company_id` và cột `don_vi_id` phải cùng cho rỗng, và từ đó mỗi
truy vấn đều phải hỏi "dòng này là loại nào" trước khi cộng. Đó là cách một bảng kế hoạch biến thành
một bảng không ai dám cộng.

BẢNG NÀY KHÔNG CÓ CỘT `company_id`, CÓ CHỦ Ý. Pháp nhân của một chỉ tiêu là pháp nhân của đơn vị
nhận chỉ tiêu — `don_vi_kd.company_id` đã giữ nó rồi. Chép sang đây là tạo ra một chỗ thứ hai có thể
nói khác, và ngày hai chỗ lệch nhau thì không ai biết bên nào đúng.

BẢNG NÀY KHÔNG CÓ CỘT `phien_ban`, CŨNG CÓ CHỦ Ý. Tiêu chí của `services/ghi_mot_lan.py` là "bản ghi
mà NHIỀU NGƯỜI cùng sửa trong một kỳ". Chỉ tiêu do một người giao — Giám đốc hoặc Ban Tổng giám đốc
— mỗi kỳ một lần, không phải thứ hai người gõ cùng lúc. Thêm cột khoá ở đây là thêm một cột không ai
đọc, mà một cột không ai đọc làm người sau tin rằng chỗ ấy đã được canh.

BỐN ĐIỀU ĐÁNG GHI LẠI

MỘT — ĐÚNG MỘT TRONG HAI: `don_vi_id` hoặc `user_id`, không được cả hai, không được cả hai rỗng.
Giao cho cả team lẫn từng người trong team trên CÙNG MỘT DÒNG thì cộng lên sẽ đếm hai lần. Máy chủ
chặn ở `services/chi_tieu_kd.py`, không để phép cộng phát hiện sau.

HAI — RÀNG BUỘC DUY NHẤT KHÔNG TỰ ĐỦ, VÀ ĐÂY LÀ CHỖ DỄ TIN NHẦM. `UniqueConstraint` bên dưới có hai
cột cho rỗng, mà trong SQL thì RỖNG KHÁC RỖNG: hai dòng cùng `ky`, cùng `user_id`, cùng `luong`, cả
hai đều `don_vi_id` rỗng — cơ sở dữ liệu coi là hai ô khác nhau và cho ghi cả hai. Nên ràng buộc này
chỉ là lưới thứ hai; lưới thứ nhất là phép kiểm trùng ở lớp dịch vụ, và nó KHÔNG bỏ được.

BA — SỬA THÌ ĐÈ LÊN DÒNG CŨ, KHÔNG THÊM DÒNG MỚI. Mỗi ô (kỳ × nơi nhận × luồng) có đúng một con số
đang hiệu lực. `so_lan_sua` và `ly_do_sua` giữ dấu vết, còn lịch sử đầy đủ nằm ở nhật ký nghiệp vụ —
cùng nếp với `ke_hoach_thang`.

BỐN — LUỒNG LÀ MỘT PHẦN CỦA Ô, KHÔNG PHẢI MỘT BỘ LỌC. Một team có thể nhận chỉ tiêu riêng cho tour
lẻ và riêng cho dịch vụ lẻ. `tat_ca` là một giá trị THẬT, nghĩa là "một con số chung cho mọi luồng",
không phải nghĩa là "tổng ba dòng kia" — cộng `tat_ca` với ba luồng là đếm hai lần.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Luồng của một chỉ tiêu. Ba giá trị đầu khớp `services/doanh_thu_kd.LUONG`; `tat_ca` là giá trị thứ
# tư chỉ có ở bảng này — xem điều BỐN ở đầu tệp.
LUONG_CHI_TIEU = ("le", "doan", "dich_vu_le", "tat_ca")


class ChiTieuKD(Base):
    """Một con số chỉ tiêu: kỳ nào, cho đơn vị nào hoặc người nào, luồng nào, bao nhiêu."""

    __tablename__ = "chi_tieu_kd"
    # Lưới thứ HAI, không phải lưới duy nhất — xem điều HAI ở đầu tệp.
    __table_args__ = (UniqueConstraint("ky", "don_vi_id", "user_id", "luong",
                                       name="uq_chi_tieu_kd_o"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # "2026-10". Chuỗi chứ không phải ngày, cùng lý do đã ghi ở `ke_hoach_thang`: chỉ tiêu thuộc về
    # CẢ THÁNG, lưu bằng kiểu ngày thì buộc phải chọn ngày 1 hay ngày cuối và sớm muộn có chỗ so
    # lệch một ngày.
    ky: Mapped[str] = mapped_column(String(7), index=True)

    # ĐÚNG MỘT trong hai cột này được điền — xem điều MỘT ở đầu tệp.
    don_vi_id: Mapped[int | None] = mapped_column(
        ForeignKey("don_vi_kd.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True)

    luong: Mapped[str] = mapped_column(String(12), default="tat_ca")   # LUONG_CHI_TIEU
    muc_tieu: Mapped[float] = mapped_column(TIEN)

    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Lý do của LẦN SỬA GẦN NHẤT. Rỗng nghĩa là dòng chưa từng bị sửa — không phải nghĩa là sửa mà
    # không nêu lý do.
    ly_do_sua: Mapped[str] = mapped_column(Text, default="")
    so_lan_sua: Mapped[int] = mapped_column(Integer, default=0)

    nguoi_nhap: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def nhan_la(self) -> str:
        """`don_vi` hay `nguoi` — dùng để đọc, không thay cho phép kiểm ở lớp dịch vụ."""
        return "don_vi" if self.don_vi_id is not None else "nguoi"


# Truy vấn chạy nhiều nhất là "chỉ tiêu của kỳ này, cho những nơi nhận này" — màn hình nào cũng mở
# bằng nó, nên có chỉ mục riêng thay vì dựa vào chỉ mục của từng cột.
Index("ix_chi_tieu_kd_ky_don_vi", ChiTieuKD.ky, ChiTieuKD.don_vi_id)
Index("ix_chi_tieu_kd_ky_nguoi", ChiTieuKD.ky, ChiTieuKD.user_id)
