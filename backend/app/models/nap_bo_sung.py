"""Bốn bảng đích còn thiếu của V4 – mười bốn bộ nạp phòng ban (lệnh giao việc 08/9/2026).

Mười bốn bộ nạp của V4 đổ về mười bốn bảng. Mười bảng đã có sẵn: giao dịch nguồn ngoài của đội xe,
bảo dưỡng, giấy tờ xe, chi phí kỳ đội xe, phân công hướng dẫn viên, thẻ tài sản cố định, thẻ công cụ
dụng cụ, bảng khấu hao kỳ, bảng lương. Bốn bảng dưới đây là phần chưa có, và mỗi bảng chỉ ra đời vì
KHÔNG có chỗ nào khác giữ được con số đó mà không làm hỏng ý nghĩa của bảng cũ.

Hai quy ước áp cho cả bốn bảng, cùng nguồn gốc với quyết định K2 ngày 08/9 của Chủ tịch:

  1. CỘT TIỀN ĐỂ TRỐNG ĐƯỢC. Mọi cột tiền ở đây là nullable. "Chưa có số" và "bằng 0" là hai chuyện
     khác nhau, và bảng nào không nói được điều thứ nhất sẽ nói dối bằng điều thứ hai.
  2. MỘT KHÓA CHỐNG TRÙNG THẬT SỰ, đặt ở tầng cơ sở dữ liệu chứ không ở tầng dịch vụ. Nạp lại một tệp
     là việc bình thường của người dùng; chống trùng bằng cách "nhớ đừng bấm hai lần" thì sớm muộn cũng
     có một tháng chi phí gấp đôi mà từng dòng vẫn trông đúng.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


# ====================== MARKETING – CHI THEO KÊNH ======================
KENH_MKT = {
    "google_ads": "Google Ads", "facebook_ads": "Facebook / Meta Ads", "tiktok_ads": "TikTok Ads",
    "zalo_ads": "Zalo Ads", "seo": "SEO – nội dung website", "email": "Email marketing",
    "kol": "KOL / KOC – hợp tác nội dung", "in_an": "In ấn – ấn phẩm", "su_kien": "Sự kiện – hội chợ",
    "bao_chi": "Báo chí – PR", "khac": "Kênh khác",
}


class MktChannelSpend(Base):
    """Chi phí quảng cáo THỰC CHI của một kỳ, theo kênh, kèm số đo của kênh đó.

    Vì sao không nhét vào bảng ngân sách marketing: mkt_budgets giữ phần DỰ TOÁN, và chính docstring của
    nó nói rõ số đã chi không nằm ở đó. Giữ nguyên ranh giới ấy – nhưng vẫn phải có một chỗ ghi số thực
    chi theo kênh, vì tháng nào chạy tám kênh là tám lần gõ tay, và không có bảng nào đối chiếu được
    "tiêu bao nhiêu ra bao nhiêu lead".

    Số đo (hiển thị, nhấp, lead) để RỖNG khi nhà quảng cáo không xuất ra được, chứ không ghi 0: một kênh
    thật sự không ra lead nào và một kênh chưa lấy được báo cáo phải phân biệt được, nếu không thì phép
    tính chi phí trên mỗi lead sẽ chia cho một số 0 giả.
    """
    __tablename__ = "mkt_channel_spend"
    __table_args__ = (
        Index("ux_mkt_channel_spend", "ky", "kenh", "chien_dich", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)                  # YYYY-MM
    kenh: Mapped[str] = mapped_column(String(20))
    chien_dich: Mapped[str] = mapped_column(String(120), default="")        # rỗng = chi chung của kênh
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    luot_hien_thi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    luot_nhap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_lead: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mo_ta: Mapped[str] = mapped_column(String(300), default="")
    chung_tu: Mapped[str] = mapped_column(String(200), default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ====================== KINH DOANH – DOANH SỐ THEO TƯ VẤN VIÊN ======================
class SalesByConsultant(Base):
    """Doanh số một kỳ của một tư vấn viên, theo cách bộ phận Kinh doanh chốt với nhau.

    Đây CỐ Ý là một bảng ghi nhận, không phải một phép tính. VTOS cộng được doanh số từ booking, nhưng
    con số Kinh doanh dùng để tính hoa hồng có quy ước riêng (tính theo ngày thu tiền hay ngày khởi hành,
    có trừ khách hủy hay không, khách chung của hai người chia thế nào). Ép hai con số thành một bằng
    cách bỏ đi con số của Kinh doanh không làm chúng giống nhau – nó chỉ làm mất chỗ để nhìn thấy chênh
    lệch. Bảng này giữ số họ chốt; đối chiếu với số máy cộng là một màn hình riêng.

    `hoa_hong` để rỗng khi kỳ chưa duyệt tỷ lệ – không ghi 0.
    """
    __tablename__ = "sales_by_consultant"
    __table_args__ = (
        Index("ux_sales_by_consultant", "ky", "employee_id", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    nhom_kd: Mapped[str] = mapped_column(String(20), default="")
    so_booking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_khach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    doanh_thu_da_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    hoa_hong: Mapped[float | None] = mapped_column(Float, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ====================== KẾ TOÁN – HÓA ĐƠN ĐẦU VÀO ======================
class PurchaseInvoice(Base):
    """Hóa đơn GTGT ĐẦU VÀO. Bảng `invoices` là hóa đơn ĐẦU RA công ty phát hành cho khách – hai chiều
    ngược nhau, không dùng chung một bảng được: đầu ra công ty tự cấp số, đầu vào thì số do người bán cấp
    và công ty chỉ nhận.

    Khóa chống trùng là bộ ba MST người bán + ký hiệu + số hóa đơn, đúng bộ ba định danh một hóa đơn trên
    hệ thống của cơ quan thuế. Không lấy số hóa đơn một mình: hai nhà cung cấp khác nhau cùng có hóa đơn
    số 42 là chuyện thường ngày.

    `khop` mặc định là "chua_khop": nạp một hóa đơn lên KHÔNG tự ghi sổ và không tự gắn vào tour nào. Ghép
    hóa đơn vào chi phí của đoàn là việc có người chịu trách nhiệm, không phải hệ quả kèm theo của thao
    tác tải tệp – cùng nguyên tắc đã áp cho sao kê ngân hàng.
    """
    __tablename__ = "purchase_invoices"
    __table_args__ = (
        Index("ux_purchase_invoices", "mst_nguoi_ban", "ky_hieu", "so_hoa_don", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    mst_nguoi_ban: Mapped[str] = mapped_column(String(20), default="")
    ten_nguoi_ban: Mapped[str] = mapped_column(String(200), default="")
    ky_hieu: Mapped[str] = mapped_column(String(20), default="")            # 1C26TAA
    so_hoa_don: Mapped[str] = mapped_column(String(20), default="")
    ngay_hd: Mapped[date | None] = mapped_column(Date, nullable=True)
    noi_dung: Mapped[str] = mapped_column(String(300), default="")
    tien_truoc_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thue_suat: Mapped[float | None] = mapped_column(Float, nullable=True)   # 0 / 0.05 / 0.08 / 0.1
    tien_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ma_tour: Mapped[str] = mapped_column(String(60), default="")            # gợi ý của người nạp, chưa phải ràng buộc
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    khop: Mapped[str] = mapped_column(String(20), default="chua_khop")      # chua_khop / da_khop / khong_khop
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)    # chứng từ ghi sổ, nếu đã ghi
    chung_tu: Mapped[str] = mapped_column(String(200), default="")          # khóa tệp ảnh/PDF trong kho
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")      # nhap_tay / nap_tep / doc_anh
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ====================== HCNS – BẢO HIỂM THEO KỲ ======================
class SocialInsurancePeriod(Base):
    """Số bảo hiểm phải đóng của một kỳ, theo từng người.

    Lệnh giao việc 08/9 ghi: "Số bảo hiểm đã chốt là LẤY TỪ BẢNG LƯƠNG". Đúng về nguồn gốc, nhưng số
    chốt với cơ quan bảo hiểm và số trên bảng lương KHÔNG phải lúc nào cũng bằng nhau – người vào giữa
    tháng, người nghỉ không lương, người vượt trần đóng, kỳ truy thu. Bảng này giữ số ĐÃ CHỐT VỚI CƠ QUAN
    BẢO HIỂM để đối chiếu với số bảng lương tính ra; nếu chỉ giữ một con số thì mỗi lần lệch sẽ không có
    cách nào biết bên nào sai.

    Không có cột nào ghi lý do sức khỏe, và cố ý không có: bảng này là số tiền đóng theo kỳ, không phải
    hồ sơ y tế của người lao động.
    """
    __tablename__ = "social_insurance_periods"
    __table_args__ = (
        Index("ux_social_insurance_periods", "ky", "employee_id", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    muc_dong: Mapped[float | None] = mapped_column(Float, nullable=True)      # mức lương làm căn cứ đóng
    cty_dong: Mapped[float | None] = mapped_column(Float, nullable=True)      # phần công ty đóng
    nld_dong: Mapped[float | None] = mapped_column(Float, nullable=True)      # phần người lao động đóng
    so_ngay_dong: Mapped[float | None] = mapped_column(Float, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="dang_dong")  # dang_dong / bao_giam / truy_thu
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
