"""KH-2 · Danh mục NHÀ HÀNG cho cổng khách hàng (Chủ tịch duyệt bản xem thử 26/10/2026).

Điều hành nhập nhà hàng và các gói thực đơn; chỉ TP / GĐ Kinh doanh bật «Hiện trên cổng».
Sửa nội dung bán (giá, thực đơn, điều kiện) của một nhà hàng đang hiện thì nó TỰ TẮT và chờ Kinh doanh
bật lại — giá lên cổng luôn là giá đã có người Kinh doanh nhìn qua.

Chỉ có GIÁ BÁN cho khách. Giá vốn / phí nhà cung cấp đi theo hợp đồng NCC ở chỗ khác, không nằm ở đây,
nên không có đường nào để chúng lọt ra cổng.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Date, DateTime, Text, Boolean, ForeignKey
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
