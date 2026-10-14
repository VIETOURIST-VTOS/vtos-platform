"""ĐỐI CHIẾU TIỀN — Đợt E15, 14/10/2026. Bảng giữ LỜI GIẢI THÍCH cho từng khoản chênh lệch.

VÌ SAO CÓ BẢNG NÀY

Đợt DT-2 đã dựng `chot_so_du`: Kế toán ký "đến hết ngày này, nguồn tiền này còn ngần này", và máy
cộng số của nó để đối chiếu — cột `so_may_cong` và `lech` ở bảng ấy. Đó là đối chiếu **tiền thật
với sao kê**.

Còn một câu nữa chưa ai hỏi: **sổ kế toán nói bao nhiêu?** Dư Nợ 112x và 111 trên sổ cái là con số
đi vào Bảng cân đối kế toán. Nó có thể khác số Kế toán đã chốt — và khi khác thì đó KHÔNG phải một
chuyện nhỏ: nó nghĩa là có tiền đã vào/ra tài khoản mà sổ chưa hạch toán, hoặc sổ đã hạch toán một
khoản chưa có tiền.

HAI CHÊNH LỆCH KHÁC NHAU, ĐỪNG GỘP

  (1) `chot_so_du.lech` = số Kế toán ký − số máy cộng từ giao dịch ngân hàng.
      Lệch ở đây thường là sao kê về chậm, hoặc tài khoản chưa nối SePay.

  (2) chênh lệch đợt này đo = SỐ SỔ KẾ TOÁN − SỐ ĐÃ CHỐT.
      Lệch ở đây là hạch toán thiếu hoặc thừa, và nó đi thẳng vào báo cáo tài chính.

Gộp hai thứ ấy làm một con số thì lệch ở đâu cũng không biết đường nào mà tìm. Bảng này CHỈ giải
thích chênh lệch (2); chênh lệch (1) đã có ô `ly_do_lech` của chính nó.

VÌ SAO LÀ NHIỀU DÒNG, KHÔNG PHẢI MỘT Ô CHỮ

"Chênh lệch chưa giải thích hết thì chưa phải đã đối chiếu" — câu ấy chỉ kiểm được bằng máy khi
từng khoản có SỐ TIỀN riêng, để cộng lại và so với chênh lệch. Một ô chữ 300 ký tự không cộng được,
nên máy không bao giờ biết đã giải thích hết hay chưa, và câu trên thành một lời nhắc chứ không
phải một phép chặn.

BA ĐIỀU BẢNG NÀY CỐ Ý KHÔNG LÀM

1. KHÔNG tự sinh lời giải thích. Mỗi dòng là một người gõ vào, có tên và có giờ. Máy đoán hộ nghĩa
   là máy ký hộ.
2. KHÔNG xoá. Gỡ một lời giải thích là chuyển nó sang `da_huy`, giữ cả người gỡ và lý do — ai đã
   giải thích sai và ai gỡ là câu kiểm toán sẽ hỏi.
3. KHÔNG bù trừ giữa hai pháp nhân, cũng không giữa hai tài khoản. Mỗi dòng gắn đúng một
   (pháp nhân, nguồn, tài khoản, ngày) — đúng khoá của một bản chốt.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

TRANG_THAI_GIAI_THICH = {
    "hieu_luc": "Đang có hiệu lực",
    "da_huy": "Đã gỡ",
}


class GiaiThichLech(Base):
    """Một khoản giải thích cho chênh lệch giữa SỐ SỔ KẾ TOÁN và SỐ ĐÃ CHỐT.

    Khoá nghiệp vụ là (pháp nhân, nguồn, tài khoản, ngày) — trùng khoá của `chot_so_du`, vì một lời
    giải thích luôn thuộc về đúng một lần chốt. CỐ Ý KHÔNG đặt khoá ngoại sang `chot_so_du.id`: bản
    chốt có thể bị THAY THẾ bởi một bản chốt sau (DT-2 giữ cả hai), mà lời giải thích thì vẫn đúng
    cho ngày ấy. Trỏ vào id là mất lời giải thích mỗi lần Kế toán chốt lại.
    """

    __tablename__ = "giai_thich_lech"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pháp nhân. RỖNG là CHƯA XÁC ĐỊNH — cùng quy ước với `chot_so_du.company_id`. Một dòng rỗng
    # pháp nhân KHÔNG được cộng vào phần đã giải thích của bất kỳ pháp nhân nào.
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True)

    nguon: Mapped[str] = mapped_column(String(20))                  # ngan_hang / tien_mat
    # RỖNG khi nguon='tien_mat' — quỹ tiền mặt không có số tài khoản.
    tai_khoan_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_accounts_cat.id"), nullable=True)
    den_ngay: Mapped[date] = mapped_column(Date)

    # Số tiền của RIÊNG khoản này. KHÔNG nullable: một lời giải thích không có số thì không cộng
    # được, mà cộng được chính là lý do bảng này tồn tại.
    #
    # CÓ DẤU, và dấu mang nghĩa: dương là "sổ đang CAO hơn số đã chốt vì khoản này", âm là "sổ đang
    # THẤP hơn vì khoản này". Bắt người dùng nhập trị tuyệt đối rồi chọn chiều ở một ô khác là thêm
    # một ô để gõ sai.
    so_tien: Mapped[float] = mapped_column(TIEN)

    # Lý do. Dịch vụ chặn rỗng — không để ràng buộc ở cơ sở dữ liệu, vì thông báo lỗi phải nói được
    # người dùng cần làm gì.
    ly_do: Mapped[str] = mapped_column(String(300))

    trang_thai: Mapped[str] = mapped_column(
        String(20), default="hieu_luc", server_default="hieu_luc", index=True)

    boi: Mapped[str] = mapped_column(String(50))
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Ai gỡ và vì sao. RỖNG khi dòng còn hiệu lực.
    huy_boi: Mapped[str] = mapped_column(String(50), default="", server_default="")
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    huy_ly_do: Mapped[str] = mapped_column(String(300), default="", server_default="")

    ghi_chu: Mapped[str] = mapped_column(Text, default="", server_default="")

    __table_args__ = (
        # Đọc theo (pháp nhân, ngày) là đường đi của MỌI lần mở màn hình đối chiếu, và của phép
        # chặn khóa kỳ. Đặt chỉ mục ngay từ đầu chứ không đợi bảng dài ra mới thêm.
        Index("ix_giai_thich_lech_ct_ngay", "company_id", "den_ngay", "trang_thai"),
    )
