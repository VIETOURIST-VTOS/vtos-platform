"""Tệp và hình ảnh đính kèm – một kho dùng chung cho mọi phân hệ.

Vì sao một kho chung thay vì mỗi phòng ban một chỗ để ảnh:

  Chứng từ ảnh là thứ đi kèm gần như mọi nghiệp vụ: hóa đơn của một chuyến xe, biên lai thu tiền của một
  booking, hợp đồng lao động của một nhân sự, ảnh phòng của một nhà cung cấp. Nếu mỗi phân hệ tự nghĩ ra
  cách lưu thì mỗi nơi một quy tắc về kích thước, về loại tệp được nhận, về ai xem được, và về việc xóa
  đi thì còn lại gì. Một kho chung là một bộ quy tắc chung.

Bốn điều được ép trong cấu trúc chứ không nhắc bằng lời:

  1. KHÓA LƯU DO HỆ THỐNG SINH, không lấy tên tệp người dùng đặt. Tên tệp gốc chỉ để hiển thị.
  2. BĂM NỘI DUNG (sha256) LƯU CÙNG. Đọc ra mà băm lệch thì báo lỗi, không trả nội dung "gần đúng".
  3. CÙNG MỘT TỆP GẮN VÀO CÙNG MỘT ĐỐI TƯỢNG CHỈ MỘT LẦN. Tải lại ảnh cũ không tạo bản thứ hai.
  4. KHÔNG XÓA CỨNG. Gỡ một tệp là THU HỒI: ghi ai gỡ, lúc nào, vì sao; bản ghi vẫn còn để đối chiếu.
     Chứng từ biến mất không dấu vết là cách nhanh nhất để một cuộc kiểm toán bế tắc.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Chín nhóm hồ sơ CỐ ĐỊNH theo Mô hình quản trị số hóa mục 7 – giống nhau ở mọi pháp nhân. Nhóm cố định
# là điều kiện để kiểm toán tìm được hồ sơ ở pháp nhân họ chưa từng mở: cấu trúc thư mục ở đâu cũng thế.
NHOM_HO_SO = {
    "01_Phap_ly":        ("Pháp lý", "Vĩnh viễn"),
    "02_Ke_toan":        ("Kế toán", "10 năm (chứng từ ghi sổ)"),
    "03_Thue":           ("Thuế & hóa đơn", "10 năm"),
    "04_Ngan_hang_Vay":  ("Ngân hàng & vay", "10 năm"),
    "05_Tour":           ("Tour & booking", "10 năm"),
    "06_Nhan_su":        ("Nhân sự", "Thời gian làm việc + 5 năm"),
    "07_Hop_dong":       ("Hợp đồng", "10 năm"),
    "08_Kiem_toan":      ("Kiểm toán", "10 năm"),
    "09_HDQT_Co_dong":   ("HĐQT & cổ đông", "Vĩnh viễn"),
    # Thêm 09/9/2026. Ảnh và tệp nội dung sắp đăng không phải hồ sơ pháp lý hay chứng từ ghi sổ, nên
    # không nhét vào nhóm nào sẵn có – nhét bừa là làm hỏng thời hạn lưu của cả nhóm đó. Năm năm là đề
    # xuất của em, Chủ tịch lật được.
    "10_Marketing":      ("Marketing & nội dung", "5 năm"),
}

# Đối tượng gắn tệp: mã → (tên hiển thị, phòng ban chủ quản, nhóm hồ sơ, lưu theo đối tượng?).
# Cột cuối theo mục 7.2: tour và nhân sự lưu THEO ĐỐI TƯỢNG (mã tour, mã NV), các nhóm còn lại theo tháng.
DOI_TUONG_DAY_DU = {
    "chuyen_xe":     ("Chuyến xe", "doi_xe", "05_Tour", True),
    "xe":            ("Hồ sơ xe", "doi_xe", "01_Phap_ly", True),
    "nha_cung_cap":  ("Nhà cung cấp", "dieu_hanh", "07_Hop_dong", True),
    "don_dich_vu":   ("Đơn đặt dịch vụ", "dieu_hanh", "05_Tour", True),
    "tour":          ("Tour", "dieu_hanh", "05_Tour", True),
    "booking":       ("Booking", "kd_le", "05_Tour", True),
    "khach_hang":    ("Khách hàng", "kd_le", "05_Tour", True),
    "nhan_su":       ("Hồ sơ nhân sự", "hcns", "06_Nhan_su", True),
    "bang_luong":    ("Bảng lương", "hcns", "06_Nhan_su", False),
    "de_nghi_chi":   ("Đề nghị chi", "ketoan", "02_Ke_toan", False),
    "sao_ke":        ("Sao kê ngân hàng", "ketoan", "04_Ngan_hang_Vay", False),
    # Khế ước vay: bản gốc là giấy có chữ ký và dấu ngân hàng. Bộ nạp Excel chỉ mang được các CON SỐ
    # của khế ước; lúc đối chiếu dư nợ với ngân hàng thì thứ phải mở ra là bản gốc, không phải dòng số.
    # Lưu theo MÃ ĐỐI TƯỢNG (True) chứ không theo tháng: một khế ước sống nhiều năm, xếp theo tháng ký
    # thì phụ lục gia hạn năm sau nằm ở một thư mục khác với khế ước gốc.
    "khe_uoc_vay":   ("Khế ước vay & hợp đồng đầu tư", "ketoan", "04_Ngan_hang_Vay", True),
    "hoa_don":       ("Hóa đơn", "ketoan", "03_Thue", False),
    "visa":          ("Hồ sơ visa", "visa", "05_Tour", True),
    "van_ban":       ("Văn bản / quyết định", "ban_tgd", "09_HDQT_Co_dong", False),
    # Thêm 09/9/2026 – bản rà form & cửa tải tệp cho thấy bốn chỗ có nghiệp vụ nhưng không có cửa đưa
    # bằng chứng vào. Khiếu nại đứng đầu vì nó chạm tiền: hồ sơ bồi thường không có ảnh khách gửi thì
    # không khép được, mà tiền bồi thường vẫn phải chi.
    "khieu_nai":     ("Khiếu nại khách hàng", "mkt", "05_Tour", True),
    "phieu_thu":     ("Phiếu thu / đối soát thu", "ketoan", "02_Ke_toan", False),
    # Tách bút toán và kết sổ thành HAI đối tượng, dù cùng nhóm hồ sơ: id của chúng khác loại nhau
    # (số bút toán vs mã kỳ "2026-09"). Dùng chung một đối tượng thì hai không gian id nằm lẫn nhau, và
    # đó đúng là cách hồ sơ của kỳ này hiện ra trong bút toán của kỳ khác.
    "but_toan":      ("Chứng từ gốc của bút toán", "ketoan", "02_Ke_toan", False),
    "ket_so":        ("Hồ sơ kết sổ kỳ", "ketoan", "02_Ke_toan", False),
    "noi_dung":      ("Nội dung & thương hiệu", "mkt", "10_Marketing", True),
    # Thêm 10/9/2026 cùng V7 Đợt 3. Nhóm 08_Kiem_toan có trong danh mục hồ sơ từ đầu nhưng CHƯA có
    # đối tượng nào gắn tệp vào đó – tức là một nhóm hồ sơ rỗng vĩnh viễn. Đây là chỗ nó có người dùng.
    #
    # Gắn theo TỪNG MỤC của danh mục chứ không theo cả hồ sơ: kiểm toán hỏi "sổ chi tiết 131 đâu",
    # không hỏi "hồ sơ kỳ này đâu". Gắn theo cả hồ sơ thì mọi tệp đổ vào một đống và câu hỏi từng mục
    # lại phải trả lời bằng cách mở từng tệp ra xem.
    "ho_so_kiem_toan_muc": ("Mục hồ sơ kiểm toán", "ketoan", "08_Kiem_toan", True),
    # Bằng chứng sự cố: ảnh xe hỏng, thông báo dời chuyến của hãng bay, biên bản với khách sạn. Không
    # có cửa này thì hồ sơ sự cố chỉ còn là lời kể, và lúc đòi nhà cung cấp bồi hoàn thì không có gì
    # trong tay.
    "su_co_tour":    ("Sự cố tour", "dieu_hanh", "05_Tour", True),
}
DOI_TUONG = {k: (v[0], v[1]) for k, v in DOI_TUONG_DAY_DU.items()}

# Nhóm hồ sơ chứa dữ liệu cá nhân phải PHÂN QUYỀN RIÊNG (Nghị định 13/2023, và mục 7.3 của Mô hình quản
# trị số hóa). Không phải "ai xem được màn hình nhân sự cũng xem được hợp đồng lao động của từng người".
NHOM_NHAY_CAM = {"06_Nhan_su"}

LOAI_TEP = {"chung_tu": "Chứng từ gốc", "hoa_don": "Hóa đơn", "hop_dong": "Hợp đồng",
            "hinh_anh": "Hình ảnh", "bang_bieu": "Bảng biểu", "khac": "Khác"}


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_doi_tuong", "doi_tuong", "doi_tuong_id"),
        # Cùng nội dung gắn vào cùng đối tượng chỉ một lần. Đặt bằng CHỈ MỤC duy nhất chứ không bằng ràng
        # buộc trên cột: SQLite (máy lập trình) không thêm ràng buộc vào bảng đã tạo, chỉ mục thì cả hai
        # môi trường đều tạo được – nên hai bên chạy cùng một lược đồ.
        Index("ux_attachments_noi_dung", "doi_tuong", "doi_tuong_id", "checksum", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    doi_tuong: Mapped[str] = mapped_column(String(30))          # khóa trong DOI_TUONG
    doi_tuong_id: Mapped[str] = mapped_column(String(60))       # id hoặc mã của bản ghi được gắn
    phong_ban: Mapped[str] = mapped_column(String(20), default="")
    # Ba trường dựng nên cấu trúc kho theo Mô hình quản trị số hóa mục 7.2:
    #   Pháp nhân / Năm / Nhóm hồ sơ / Tháng hoặc Mã đối tượng / Tệp
    phap_nhan: Mapped[str] = mapped_column(String(30), default="")   # mã pháp nhân; rỗng = CHƯA XÁC ĐỊNH
    nam: Mapped[int] = mapped_column(Integer, default=0)
    nhom_ho_so: Mapped[str] = mapped_column(String(20), default="")  # 01_Phap_ly … 09_HDQT_Co_dong
    nhay_cam: Mapped[bool] = mapped_column(Boolean, default=False)   # dữ liệu cá nhân – phân quyền riêng
    loai: Mapped[str] = mapped_column(String(20), default="chung_tu")
    ten_tep: Mapped[str] = mapped_column(String(200))           # tên gốc, CHỈ để hiển thị
    kieu_noi_dung: Mapped[str] = mapped_column(String(80), default="")
    kich_thuoc: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    khoa_luu: Mapped[str] = mapped_column(String(200))          # khóa trên kho lưu trữ, do hệ thống sinh
    la_anh: Mapped[bool] = mapped_column(Boolean, default=False)
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nguoi_nhap")   # nguoi_nhap / ai / he_thong
    tac_nhan: Mapped[str] = mapped_column(String(80), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    thu_hoi: Mapped[bool] = mapped_column(Boolean, default=False)
    thu_hoi_boi: Mapped[str] = mapped_column(String(50), default="")
    thu_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_thu_hoi: Mapped[str] = mapped_column(String(200), default="")
