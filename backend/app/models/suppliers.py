"""Danh mục nhà cung cấp và đơn đặt dịch vụ.

Đây là đầu chi lớn nhất của công ty mà đến nay chưa có sổ: chi phí tour đi ra bằng đề nghị chi, nhưng
KHÔNG có nơi nào trả lời được "đã đặt những gì, của ai, cho tour nào, và đã dùng chưa".

Hai chỗ được làm chặt hơn phần còn lại, vì cả hai là đường tiền ra khỏi công ty:

  1. ĐỔI SỐ TÀI KHOẢN NHÀ CUNG CẤP CẦN NGƯỜI THỨ HAI XÁC NHẬN. Đây là cách gian lận cổ điển nhất trong
     thanh toán: đổi số tài khoản của một nhà cung cấp thật rồi để hệ thống tự chuyển tiền vào đó. Bản ghi
     đổi nằm ở trạng thái CHỜ, số tài khoản đang hiệu lực KHÔNG đổi cho tới khi người thứ hai xác nhận, và
     người đề nghị không tự xác nhận được.

  2. ĐƠN ĐẶT DỊCH VỤ PHẢI GẮN TOUR. Chi phí không gắn tour thì không quy được vào giá thành, và cuối kỳ
     nó nằm trong một cục "chi phí chung" mà không ai chia lại được.

Nhà cung cấp KHÔNG xóa được, chỉ ngưng hoạt động: hợp đồng và phiếu chi cũ vẫn phải truy ra được đối tác.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

LOAI_NCC = {"khach_san": "Khách sạn / lưu trú", "nha_hang": "Nhà hàng", "van_chuyen": "Vận chuyển",
            "ve_tham_quan": "Vé tham quan", "hdv": "Hướng dẫn viên", "hang_khong": "Hàng không",
            "tau_thuyen": "Tàu / thuyền", "khac": "Khác"}
TRANG_THAI_DON = {"nhap": "Nháp", "da_gui": "Đã gửi nhà cung cấp", "da_xac_nhan": "NCC đã xác nhận",
                  "da_su_dung": "Đã sử dụng", "huy": "Hủy"}
TRANG_THAI_DOI_TK = {"cho_xac_nhan": "Chờ người thứ hai xác nhận", "da_xac_nhan": "Đã có hiệu lực",
                     "tu_choi": "Bị từ chối"}


class Supplier(Base):
    __tablename__ = "suppliers"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)          # NCC0001
    ten: Mapped[str] = mapped_column(String(200))
    # TÊN GIAO DỊCH ở trên, TÊN PHÁP NHÂN ở đây – hai thứ khác nhau và hoá đơn chỉ chấp nhận cái thứ
    # hai. Đo trên tệp danh mục thật của công ty (280 nhà cung cấp): "RESORT VĨNH HY" là tên người ta
    # gọi, còn hoá đơn mang tên "CTY TNHH PHÁT HOÀNG LONG"; "NEM NƯỚNG BÀ HÙNG" xuất hoá đơn dưới tên
    # "HỘ KINH DOANH HOÀNG LỆ GIANG".
    #
    # Gộp hai tên vào một cột thì hoặc mất tên để tra, hoặc mất tên để kê khai thuế.
    ten_phap_nhan: Mapped[str] = mapped_column(String(300), default="")
    loai: Mapped[str] = mapped_column(String(20), default="khac")
    ma_so_thue: Mapped[str] = mapped_column(String(20), default="")
    dia_chi: Mapped[str] = mapped_column(String(300), default="")
    nguoi_lien_he: Mapped[str] = mapped_column(String(120), default="")
    dien_thoai: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    # Số tài khoản ĐANG HIỆU LỰC. Chỉ đổi qua bảng SupplierBankChange có người thứ hai xác nhận.
    so_tai_khoan: Mapped[str] = mapped_column(String(40), default="")
    ngan_hang: Mapped[str] = mapped_column(String(120), default="")
    chu_tai_khoan: Mapped[str] = mapped_column(String(160), default="")
    dieu_khoan_tt: Mapped[str] = mapped_column(String(200), default="")   # điều khoản thanh toán đã thỏa thuận
    note: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")


class SupplierBankChange(Base):
    """Một lần đề nghị đổi thông tin tài khoản của nhà cung cấp, chờ người thứ hai xác nhận.

    Giữ cả số CŨ và số MỚI: sau này còn dựng lại được ai đổi, đổi từ đâu sang đâu, ai xác nhận."""
    __tablename__ = "supplier_bank_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    so_tk_cu: Mapped[str] = mapped_column(String(40), default="")
    ngan_hang_cu: Mapped[str] = mapped_column(String(120), default="")
    chu_tk_cu: Mapped[str] = mapped_column(String(160), default="")
    so_tk_moi: Mapped[str] = mapped_column(String(40))
    ngan_hang_moi: Mapped[str] = mapped_column(String(120), default="")
    chu_tk_moi: Mapped[str] = mapped_column(String(160), default="")
    ly_do: Mapped[str] = mapped_column(String(300), default="")
    chung_tu: Mapped[str] = mapped_column(String(200), default="")      # văn bản của NCC
    status: Mapped[str] = mapped_column(String(20), default="cho_xac_nhan")
    de_nghi_boi: Mapped[str] = mapped_column(String(50), default="")
    de_nghi_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")


class ServiceOrder(Base):
    """Đơn đặt dịch vụ gửi nhà cung cấp cho một tour cụ thể."""
    __tablename__ = "service_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)          # DV2609-0001
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))        # bắt buộc: chi phí phải quy về tour
    loai: Mapped[str] = mapped_column(String(20), default="khac")
    noi_dung: Mapped[str] = mapped_column(String(300))
    ngay_su_dung: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_luong: Mapped[float] = mapped_column(Float, default=1)
    don_vi: Mapped[str] = mapped_column(String(30), default="")
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="nhap")
    xac_nhan_ncc: Mapped[str] = mapped_column(String(200), default="")   # số/ảnh xác nhận của NCC
    payment_request_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(50), default="")
