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

# Đối tượng gắn tệp: mã → (tên hiển thị, phòng ban chủ quản). Thêm phân hệ mới là thêm một dòng.
DOI_TUONG = {
    "chuyen_xe":     ("Chuyến xe", "doi_xe"),
    "xe":            ("Hồ sơ xe", "doi_xe"),
    "nha_cung_cap":  ("Nhà cung cấp", "dieu_hanh"),
    "don_dich_vu":   ("Đơn đặt dịch vụ", "dieu_hanh"),
    "tour":          ("Tour", "dieu_hanh"),
    "booking":       ("Booking", "kd_le"),
    "khach_hang":    ("Khách hàng", "kd_le"),
    "nhan_su":       ("Hồ sơ nhân sự", "hcns"),
    "bang_luong":    ("Bảng lương", "hcns"),
    "de_nghi_chi":   ("Đề nghị chi", "ketoan"),
    "sao_ke":        ("Sao kê ngân hàng", "ketoan"),
    "hoa_don":       ("Hóa đơn", "ketoan"),
    "visa":          ("Hồ sơ visa", "visa"),
    "van_ban":       ("Văn bản / quyết định", "ban_tgd"),
}

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
