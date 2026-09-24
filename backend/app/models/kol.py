"""KOL / KOC — danh bạ người hợp tác nội dung, và từng lần hợp tác có tiền.

VÌ SAO HAI BẢNG CHỨ KHÔNG MỘT

Một KOL hợp tác nhiều lần, mỗi lần một chiến dịch khác, một khoản chi khác, một kết quả khác. Gộp
vào một bảng thì hoặc mất lịch sử (chỉ giữ lần gần nhất), hoặc phải chép lại tên và kênh của người
ấy ở mỗi dòng — và hai bản chép sẽ lệch nhau đúng ngày ai đó sửa một bên.

    mkt_kol           AI — danh bạ, mỗi kênh một dòng
    mkt_kol_hop_tac   LẦN NÀO, VIỆC GÌ, BAO NHIÊU TIỀN — mỗi lần một dòng

MỘT KOL LÀ MỘT KÊNH, KHÔNG PHẢI MỘT NGƯỜI. Một người có cả TikTok lẫn YouTube thì đó là HAI dòng,
và đó là chủ ý: thứ Marketing mua là một bài đăng trên một kênh, giá khác nhau, khán giả khác nhau,
hiệu quả khác nhau. Đo theo người thì hai kênh trộn vào nhau và không ai biết kênh nào đáng tiền.
Ràng buộc duy nhất trên (kênh, link_kenh) giữ đúng điều ấy — cùng một đường dẫn kênh không được
khai hai lần.

CÙNG TÊN THÌ CẢNH BÁO, KHÔNG CHẶN. Trùng tên là chuyện thường (và hai người thật có thể trùng tên),
còn trùng ĐƯỜNG DẪN KÊNH thì chắc chắn là một bản khai lặp. Hai mức khác nhau nên xử lý khác nhau —
cùng nếp với nhóm 2.8: trùng số điện thoại là bình thường, trùng dấu vân tay mới là rò.

TIỀN Ở ĐÂY LÀ TIỀN GHI CHÉP, KHÔNG PHẢI TIỀN KẾ TOÁN. `chi_phi` là con số Marketing thoả thuận với
KOL, để biết một lần hợp tác đáng bao nhiêu khi đọc bảng. Tiền THẬT ra khỏi tài khoản vẫn đi đường
ĐỀ NGHỊ CHI như mọi khoản khác, và `payment_request_id` nối sang đó. Hai con số này CỐ Ý không tự
đồng bộ: thoả thuận 20 triệu mà đề nghị chi 22 triệu là một việc có thật cần người giải thích, và
một phép tính tự động san bằng nó đi là xoá mất câu hỏi.

RỖNG `payment_request_id` NGHĨA LÀ CHƯA LẬP PHIẾU CHI, không phải "miễn phí". Một lần hợp tác
không mất tiền thì `chi_phi = 0` và ghi rõ trong ghi chú — đổi hàng, quà tặng, quan hệ. Còn CHƯA
THOẢ THUẬN GIÁ thì để RỖNG. Ba trạng thái, ba cách ghi, và bảng phải in ra được cả ba: rỗng là
"chưa có giá", 0 là "không mất tiền", số dương là giá đã chốt.
"""
from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Kênh của KOL. CỐ Ý không dùng chung `ND_KENH` của sổ nội dung: sổ ấy có "website" và "in ấn" —
# hai thứ không ai gọi là kênh của một KOL — còn ở đây cần "instagram" mà sổ kia không có.
KOL_KENH = {
    "facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube",
    "instagram": "Instagram", "threads": "Threads", "bao_chi": "Nhà báo / trang tin",
    "podcast": "Podcast", "khac": "Khác",
}

# `tam_dung` khác `ngung`: tạm dừng là còn dùng lại, ngừng là đã quyết định thôi — và phải ghi lý
# do. Một người bị loại mà không ai ghi vì sao thì sáu tháng sau có người lại đề xuất đúng người ấy.
KOL_TRANG_THAI = {"dang_hop_tac": "Đang hợp tác", "tam_dung": "Tạm dừng",
                  "ngung": "Ngừng hợp tác"}

HT_LOAI = {"bai_dang": "Bài đăng", "video": "Video", "livestream": "Livestream",
           "review": "Bài đánh giá", "di_tour": "Đi tour trải nghiệm", "khac": "Khác"}

# `du_kien` → đang thương lượng. `da_chot` → đã thoả thuận, chưa đăng. `da_dang` → đã ra mắt.
# `huy` → không làm nữa, và phải ghi lý do.
HT_TRANG_THAI = {"du_kien": "Dự kiến", "da_chot": "Đã chốt", "da_dang": "Đã đăng", "huy": "Huỷ"}


class MktKol(Base):
    """Một kênh của một người hợp tác nội dung. Xem ghi chú đầu tệp: một KOL là một KÊNH."""
    __tablename__ = "mkt_kol"
    __table_args__ = (
        # Chặn bản khai lặp của CÙNG một kênh. Không chặn trùng tên — xem ghi chú đầu tệp.
        #
        # Đây là lưới THỨ HAI. Lưới thứ nhất là câu hỏi trên màn hình lúc người dùng gõ trùng, và
        # nó bắt được nhiều hơn vì nó nhìn cả tên. Ràng buộc này bắt phần mà lưới kia bỏ lọt: hai
        # người cùng bấm một lúc, và một bộ nạp chạy hai lần.
        UniqueConstraint("kenh", "link_kenh", name="uq_mkt_kol_kenh_link"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)      # KOL-0001
    ho_ten: Mapped[str] = mapped_column(String(160))
    biet_danh: Mapped[str] = mapped_column(String(160), default="")           # tên kênh hay dùng
    kenh: Mapped[str] = mapped_column(String(16))
    link_kenh: Mapped[str] = mapped_column(String(400))
    # Số người theo dõi LÚC KHAI, kèm ngày đo. Con số này rơi rụng rất nhanh, nên để trần nó ra:
    # in "1,2 triệu (đo 12/9)" thì người đọc tự biết nên tin tới đâu; in mỗi "1,2 triệu" thì không.
    luong_theo_doi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theo_doi_do_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Giá tham khảo một bài, để ước khi chọn người. KHÔNG phải giá đã chốt — giá chốt nằm ở từng
    # dòng hợp tác, vì nó thay đổi theo gói và theo mùa.
    gia_tham_khao: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguoi_lien_he: Mapped[str] = mapped_column(String(160), default="")
    dien_thoai: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    trang_thai: Mapped[str] = mapped_column(String(14), default="dang_hop_tac")
    ly_do_ngung: Mapped[str] = mapped_column(String(300), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True,
                                                   index=True)
    nguoi_tao: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MktKolHopTac(Base):
    """Một lần hợp tác: chiến dịch nào, nội dung gì, chi bao nhiêu, đã đăng chưa."""
    __tablename__ = "mkt_kol_hop_tac"
    id: Mapped[int] = mapped_column(primary_key=True)
    kol_id: Mapped[int] = mapped_column(ForeignKey("mkt_kol.id"), index=True)
    # Chiến dịch. RỖNG NGHĨA LÀ CHƯA GẮN, không phải "chi chung" — cùng luật với dòng chi marketing
    # ở nhóm 2.7, và phần rỗng cũng nằm riêng chứ không bị chia đều cho các chiến dịch.
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True,
                                                    index=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)                    # 2026-09
    loai: Mapped[str] = mapped_column(String(14), default="bai_dang")
    noi_dung: Mapped[str] = mapped_column(String(300))
    link_bai: Mapped[str] = mapped_column(String(400), default="")
    ngay_dang: Mapped[date | None] = mapped_column(Date, nullable=True)
    # RỖNG KHÁC KHÔNG, và bản đầu của vòng này làm sai đúng chỗ ấy: khai `default=0.0` không cho
    # rỗng, nên "chưa thoả thuận giá" bị ghi thành số 0 — giống hệt "miễn phí, đổi hàng lấy bài".
    # Hai việc khác hẳn nhau, và trên bảng chúng trông y như nhau. `test_ks_cot_tien_ky_thuat` bắt
    # được, đúng cái nó sinh ra để bắt.
    chi_phi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Nối sang tiền THẬT. Xem ghi chú đầu tệp: hai con số cố ý không tự đồng bộ.
    payment_request_id: Mapped[int | None] = mapped_column(ForeignKey("payment_requests.id"),
                                                           nullable=True, index=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="du_kien")
    ly_do_huy: Mapped[str] = mapped_column(String(300), default="")
    # Kết quả đo được, do người nhập. CỐ Ý để rỗng được và KHÔNG có công thức nào suy ra chúng:
    # số liệu nền tảng nằm ngoài VTOS, nhân viên đọc từ trang quản trị của kênh rồi gõ vào.
    luot_xem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    luot_tuong_tac: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_lead_khai: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ghi_chu: Mapped[Text] = mapped_column(Text, default="")
    nguoi_tao: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
