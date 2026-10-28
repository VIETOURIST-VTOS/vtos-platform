"""KH-2 · Danh mục NHÀ HÀNG cho cổng khách hàng (Chủ tịch duyệt bản xem thử 26/10/2026).

Điều hành nhập nhà hàng và các gói thực đơn; chỉ TP Điều hành bật «Hiện trên cổng» (DT-2b, Chủ tịch 28/10/2026 —
trước đó là Kinh doanh); người vừa nhập / sửa không tự bật.
Sửa nội dung bán (giá, thực đơn, điều kiện) của một nhà hàng đang hiện thì nó TỰ TẮT và chờ TP Điều hành
bật lại — giá lên cổng luôn là giá đã có người thứ hai nhìn qua.

Chỉ có GIÁ BÁN cho khách. Giá vốn / phí nhà cung cấp đi theo hợp đồng NCC ở chỗ khác, không nằm ở đây,
nên không có đường nào để chúng lọt ra cổng.
"""
from datetime import date, datetime
from sqlalchemy import JSON, String, Integer, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

AM_THUC = ("Việt Nam", "Hải sản", "Chay", "Á", "Âu", "Buffet", "Khác")
LOAI_GOI = {"set": "Set menu / người", "buffet": "Buffet / người", "goi_mon": "Gọi món (mức chi dự kiến / người)",
            "tiec": "Tiệc / phòng riêng (báo giá)"}


class NhaHang(Base):
    __tablename__ = "nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True)
    ten: Mapped[str] = mapped_column(String(160))
    tinh_thanh: Mapped[str] = mapped_column(String(80), default="")
    khu_vuc: Mapped[str] = mapped_column(String(200), default="")      # khu vực / địa chỉ hiển thị cho khách
    am_thuc: Mapped[str] = mapped_column(String(40), default="Việt Nam")
    gio_phuc_vu: Mapped[str] = mapped_column(String(120), default="")
    tien_ich: Mapped[str] = mapped_column(String(300), default="")
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    ghi_chu_noi_bo: Mapped[str] = mapped_column(Text, default="")      # KHÔNG bao giờ ra cổng
    hien_cong: Mapped[bool] = mapped_column(Boolean, default=False)
    hien_boi: Mapped[str] = mapped_column(String(50), default="")
    hien_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tat_ly_do: Mapped[str] = mapped_column(String(200), default="")     # vì sao đang tắt (vừa sửa giá…)
    ngung: Mapped[bool] = mapped_column(Boolean, default=False)         # ngừng hợp tác — không bật lại được
    # NCC-1: nhà hàng này thuộc NCC nào trong danh mục — để tài khoản NCC nhà hàng thấy đơn đặt bàn của mình.
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # AT-1 (Chủ tịch duyệt 28/10/2026): danh mục khám phá ẩm thực. Hiện giới thiệu ≠ mở đặt bàn: mở đặt do
    # máy tính từ hợp đồng + nhà cung cấp + thực đơn + liên hệ đã xác minh + hoa hồng đã khai.
    nguon: Mapped[str] = mapped_column(String(60), default="")             # «Danh mục TasteAtlas 28/10/2026», «Điều hành nhập»…
    nguon_ref: Mapped[str] = mapped_column(String(300), default="")        # thứ tự / đường dẫn nguồn (KHÔNG phải xếp hạng)
    dia_danh_nguon: Mapped[str] = mapped_column(String(120), default="")   # địa danh đúng như nguồn ghi
    mon_noi_bat: Mapped[str] = mapped_column(String(500), default="")
    lien_he_xac_minh: Mapped[bool] = mapped_column(Boolean, default=False)
    xac_minh_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_minh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # AT-1c: ảnh nhà hàng (tệp trong kho, đối tượng «am_thuc») + nguồn ảnh bắt buộc ghi
    anh_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    anh_nguon: Mapped[str] = mapped_column(String(200), default="")


class HopDongNhaHang(Base):
    """Hợp đồng nhà hàng — Điều hành ghi nhận đã ký + tải tệp. Bất biến: sửa = thêm bản mới kèm lý do."""
    __tablename__ = "hop_dong_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    phien_ban: Mapped[int] = mapped_column(Integer, default=1)
    so_hd: Mapped[str] = mapped_column(String(80))
    ngay_ky: Mapped[date] = mapped_column(Date)
    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)       # rỗng = không thời hạn
    hoa_hong_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1000 = 10%; rỗng = chưa khai
    hoa_hong_co_dinh: Mapped[int | None] = mapped_column(Integer, nullable=True)   # đồng / đơn
    co_so_hoa_hong: Mapped[str] = mapped_column(String(300), default="")
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))
    thay_cho_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ly_do: Mapped[str] = mapped_column(Text, default="")
    con_dung: Mapped[bool] = mapped_column(Boolean, default=True)              # bản mới nhất của nhà hàng
    ghi_boi: Mapped[str] = mapped_column(String(50), default="")
    ghi_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class NoiDungAmThuc(Base):
    """Nội dung VTD tự viết trên trang Khám phá ẩm thực (Marketing biên tập): món, đặc sản, danh sách gợi ý,
    giới thiệu thành phố, ảnh bìa. Không chép chữ / ảnh của trang ngoài; ảnh phải ghi nguồn."""
    __tablename__ = "noi_dung_am_thuc"
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(12))                 # mon | dac_san | danh_sach | thanh_pho | bia
    ten: Mapped[str] = mapped_column(String(160))
    ten_khac: Mapped[str] = mapped_column(String(160), default="")   # tên tiếng Anh / tên gọi khác
    nhom: Mapped[str] = mapped_column(String(40), default="")        # nhóm món (món nước, cơm…) / loại đặc sản
    tinh_thanh: Mapped[str] = mapped_column(String(80), default="")  # thành phố ẩm thực (THANH_PHO)
    tom_tat: Mapped[str] = mapped_column(String(300), default="")
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    vung: Mapped[str] = mapped_column(String(160), default="")
    nen_an: Mapped[str] = mapped_column(String(160), default="")
    thanh_phan: Mapped[str] = mapped_column(String(300), default="")
    cach_goi: Mapped[str] = mapped_column(String(300), default="")
    nha_hang_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)   # «Ăn ở đâu» — nhà hàng trong danh mục
    anh_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    anh_nguon: Mapped[str] = mapped_column(String(200), default="")
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    hien: Mapped[bool] = mapped_column(Boolean, default=False)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ThucDonNhaHang(Base):
    __tablename__ = "thuc_don_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    ten: Mapped[str] = mapped_column(String(160))
    loai: Mapped[str] = mapped_column(String(12), default="set")
    gia_nguoi_lon: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_tre_em: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_khach_toi_thieu: Mapped[int] = mapped_column(Integer, default=1)
    mo_ta: Mapped[str] = mapped_column(Text, default="")                # món trong set
    dieu_kien: Mapped[str] = mapped_column(String(300), default="")     # đồ uống, phụ thu…
    dieu_kien_huy: Mapped[str] = mapped_column(String(300), default="")
    tu_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    dang_ban: Mapped[bool] = mapped_column(Boolean, default=True)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
