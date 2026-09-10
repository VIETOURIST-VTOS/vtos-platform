"""Bản LƯU của báo cáo theo lịch – lưu đúng CẤU TRÚC CHỈ TIÊU mà màn hình đang đọc.

Trước 10/9/2026 có hai thứ cùng tên "báo cáo" mà không nối với nhau:

  · màn hình /bao-cao đọc `bao_cao_phong.bao_cao()` – bảng chỉ tiêu, tính tại chỗ;
  · lịch tự động (`vtos_bao_cao_ngay/tuan/thang`) lại lưu bản của robot R7 – một BÀI VIẾT markdown,
    dựng từ phép tính riêng của nó.

Hai phép tính khác nhau cho cùng một câu hỏi thì sớm muộn ra hai con số, và lúc lệch thì không ai
biết bản nào đúng – đó là lúc người ta thôi dùng cả hai. Bảng này sửa gốc: bản lưu được sinh ra từ
CHÍNH hàm mà màn hình gọi, nên nó không thể lệch; nếu lệch thì là lệch theo thời điểm chụp, chứ
không phải lệch theo cách tính.

Vì sao vẫn cần bản lưu khi màn hình đã tính tại chỗ: màn hình trả lời "bây giờ thế nào", bản lưu trả
lời "cuối tháng trước thế nào". Câu thứ hai không tính lại được – dữ liệu đã đổi, và tour quá hạn
quyết toán hôm 30/9 hôm nay có thể đã quyết toán xong. Không chụp lại lúc ấy thì câu hỏi ấy vĩnh
viễn không có câu trả lời.

Khoá theo (kind, ky, pham_vi): chạy lại cùng một kỳ thì ĐÈ chứ không sinh dòng thứ hai. Sinh thêm
dòng là cách một bảng lưu biến thành bảng "có nhiều bản, không biết bản nào là bản chốt".
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class BaoCaoLuu(Base):
    __tablename__ = "bao_cao_luu"
    __table_args__ = (UniqueConstraint("kind", "ky", "pham_vi", name="uq_bao_cao_luu_ky"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)        # ngay / tuan / thang
    ky: Mapped[str] = mapped_column(String(12), index=True)          # 2026-09-10 / 2026-W37 / 2026-09
    pham_vi: Mapped[str] = mapped_column(String(30), index=True)     # toan_cty / dieu_hanh / visa …
    pham_vi_ten: Mapped[str] = mapped_column(String(80), default="")
    tu: Mapped[str] = mapped_column(String(10), default="")
    den: Mapped[str] = mapped_column(String(10), default="")

    # Nguyên văn danh sách chỉ tiêu – cùng dạng màn hình đang đọc, kèm cách tính và nguồn của từng
    # dòng. Lưu cả cách tính là có chủ ý: ba tháng sau mã đổi, mà bản lưu vẫn nói được con số hồi ấy
    # tính thế nào. Lưu mỗi con số thì bản lưu chỉ còn là một dãy số không giải thích được.
    chi_tieu: Mapped[list] = mapped_column(JSON, default=list)
    markdown: Mapped[str] = mapped_column(Text, default="")          # bản chữ để đọc nhanh / in ra

    # Ba con số đếm sẵn, để danh sách bản lưu hiện được ngay mà không phải mở JSON của từng dòng.
    so_viec_do: Mapped[int] = mapped_column(Integer, default=0)
    so_can_ra_soat: Mapped[int] = mapped_column(Integer, default=0)
    so_chua_co_so: Mapped[int] = mapped_column(Integer, default=0)

    tao_boi: Mapped[str] = mapped_column(String(50), default="lich")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
