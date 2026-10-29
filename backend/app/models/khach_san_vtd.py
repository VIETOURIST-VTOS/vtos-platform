"""KS-13 · DANH MỤC KHÁCH SẠN HỢP TÁC VTD (Chủ tịch duyệt bản demo 30/10/2026).

Khác hẳn nhánh OTA (KS-1 … KS-11): ở đây VTD có hợp đồng trực tiếp với khách sạn, Điều hành nhập
khách sạn, ảnh, loại phòng và GIÁ BÁN theo mùa; khách xem, lọc, so sánh và chọn phòng như trên Agoda.
Đặt + thanh toán (KS-14) theo đúng đường của đặt bàn nhà hàng (DT-2). Ở bước 12a, khách «Gửi yêu cầu
giữ phòng» — yêu cầu đi vào hàng chờ KS-11 của Điều hành, mang theo phòng và giá khách đã chọn.

Ai làm gì:
  · NV / TP Điều hành nhập khách sạn, ảnh, loại phòng, gói giá và mùa giá.
  · TP Điều hành duyệt ảnh và gói giá; người vừa nhập / sửa không tự duyệt (trừ Chủ tịch, TGĐ).
  · TP Điều hành bật «Hiện trên cổng»; người vừa sửa hồ sơ không tự bật (trừ Chủ tịch, TGĐ).
  · Chỉ GIÁ BÁN cho khách ở đây. Giá vốn / hoa hồng theo hợp đồng NCC, không lên cổng.
Các bảng bắt đầu RỖNG — máy không nạp sẵn khách sạn nào.
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

LOAI_CHO_O = {"khach_san": "Khách sạn", "resort": "Resort", "can_ho": "Căn hộ", "homestay": "Homestay", "villa": "Villa"}
TIEN_ICH = {"ho_boi": "Hồ bơi", "wifi": "Wi-Fi miễn phí", "dua_don": "Đưa đón sân bay", "do_xe": "Bãi đỗ xe",
            "nha_hang": "Nhà hàng", "le_tan_24h": "Lễ tân 24 giờ", "gym": "Phòng gym", "spa": "Spa",
            "thang_may": "Thang máy", "bai_bien": "Bãi biển riêng", "tre_em": "Câu lạc bộ trẻ em",
            "bar": "Quầy bar", "giat_ui": "Giặt ủi", "phong_hop": "Phòng họp", "xe_dap": "Xe đạp miễn phí",
            "thu_cung": "Nhận thú cưng"}
NHOM_ANH_KS = {"mat_tien": "Mặt tiền", "phong": "Phòng", "ho_boi": "Hồ bơi", "sanh": "Sảnh",
               "nha_hang": "Nhà hàng", "tien_ich": "Tiện ích", "canh_quan": "Cảnh quan", "khac": "Khác"}
TRANG_THAI_ANH_KS = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt", "tra_lai": "Trả lại", "an": "Ẩn"}
TRANG_THAI_GOI = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt", "tra_lai": "Trả lại"}


class KhachSanVtd(Base):
    __tablename__ = "khach_san_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True)
    ten: Mapped[str] = mapped_column(String(160))
    tinh_thanh: Mapped[str] = mapped_column(String(80), default="", index=True)   # theo THANH_PHO của nhà hàng
    khu_vuc: Mapped[str] = mapped_column(String(120), default="")
    dia_chi: Mapped[str] = mapped_column(String(300), default="")
    sao: Mapped[int] = mapped_column(Integer, default=0)
    loai: Mapped[str] = mapped_column(String(12), default="khach_san")
    km_trung_tam: Mapped[float | None] = mapped_column(Float, nullable=True)
    gan: Mapped[str] = mapped_column(String(300), default="")          # «120 m tới biển · 3 km tới cầu Rồng»
    noi_bat: Mapped[str] = mapped_column(String(300), default="")      # một dòng nổi bật trên thẻ
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    tien_ich: Mapped[list] = mapped_column(JSON, default=list)           # khoá trong TIEN_ICH
    gio_nhan: Mapped[str] = mapped_column(String(5), default="14:00")
    gio_tra: Mapped[str] = mapped_column(String(5), default="12:00")
    cs_tre_em: Mapped[str] = mapped_column(String(300), default="")
    cs_giuong_phu: Mapped[str] = mapped_column(String(300), default="")
    cs_vat_nuoi: Mapped[str] = mapped_column(String(300), default="")
    cs_khac: Mapped[str] = mapped_column(Text, default="")
    # Giá Điều hành nhập là giá CHƯA gồm thuế phí; khách thấy «chưa gồm thuế và phí» và số thuế phí ở bước
    # thanh toán. Mức % theo từng khách sạn (VAT + phí phục vụ) — Điều hành nhập theo hợp đồng.
    thue_phi_pt: Mapped[float] = mapped_column(Float, default=0)
    lien_he_noi_bo: Mapped[str] = mapped_column(String(300), default="")  # KHÔNG ra cổng
    ghi_chu_noi_bo: Mapped[str] = mapped_column(Text, default="")         # KHÔNG ra cổng
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    hien_cong: Mapped[bool] = mapped_column(Boolean, default=False)
    hien_boi: Mapped[str] = mapped_column(String(50), default="")
    hien_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tat_ly_do: Mapped[str] = mapped_column(String(200), default="")
    ngung: Mapped[bool] = mapped_column(Boolean, default=False)
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AnhKhachSanVtd(Base):
    __tablename__ = "anh_khach_san_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    khach_san_id: Mapped[int] = mapped_column(ForeignKey("khach_san_vtd.id"), index=True)
    loai_phong_id: Mapped[int | None] = mapped_column(ForeignKey("loai_phong_vtd.id"), nullable=True, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))     # bản gốc — KHÔNG ra cổng
    hien_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))           # ≤1600px WEBP
    nho_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))            # ≤480px WEBP
    rong: Mapped[int] = mapped_column(Integer, default=0)
    cao: Mapped[int] = mapped_column(Integer, default=0)
    nhom: Mapped[str] = mapped_column(String(12), default="khac")
    chu_thich: Mapped[str] = mapped_column(String(200), default="")
    nguon: Mapped[str] = mapped_column(String(200), default="")      # ghi nội bộ: khách sạn gửi / VTD chụp …
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    la_bia: Mapped[bool] = mapped_column(Boolean, default=False)
    trang_thai: Mapped[str] = mapped_column(String(10), default="nhap", index=True)
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    tai_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LoaiPhongVtd(Base):
    __tablename__ = "loai_phong_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    khach_san_id: Mapped[int] = mapped_column(ForeignKey("khach_san_vtd.id"), index=True)
    ten: Mapped[str] = mapped_column(String(120))
    dien_tich: Mapped[int] = mapped_column(Integer, default=0)          # m²
    giuong: Mapped[str] = mapped_column(String(120), default="")
    mo_ta: Mapped[str] = mapped_column(String(300), default="")         # ban công, hướng biển…
    toi_da_nguoi_lon: Mapped[int] = mapped_column(Integer, default=2)
    toi_da_tre_em: Mapped[int] = mapped_column(Integer, default=0)
    so_phong: Mapped[int] = mapped_column(Integer, default=1)           # số phòng VTD được bán mỗi đêm
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    dang_ban: Mapped[bool] = mapped_column(Boolean, default=True)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GoiGiaVtd(Base):
    """Một gói giá của một loại phòng (Chỉ phòng / Có bữa sáng …) — điều kiện + các mùa giá. Duyệt CẢ GÓI:
    sửa điều kiện hoặc bất kỳ mùa nào của gói đã duyệt → gói về «Nháp», thôi hiện, chờ duyệt lại."""
    __tablename__ = "goi_gia_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    loai_phong_id: Mapped[int] = mapped_column(ForeignKey("loai_phong_vtd.id"), index=True)
    ten: Mapped[str] = mapped_column(String(80), default="Chỉ phòng")
    bua_sang: Mapped[bool] = mapped_column(Boolean, default=False)
    huy_truoc_ngay: Mapped[int | None] = mapped_column(Integer, nullable=True)   # None = không hoàn tiền
    dang_ban: Mapped[bool] = mapped_column(Boolean, default=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="nhap", index=True)
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gui_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MuaGiaVtd(Base):
    __tablename__ = "mua_gia_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    goi_id: Mapped[int] = mapped_column(ForeignKey("goi_gia_vtd.id"), index=True)
    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date] = mapped_column(Date)                         # GỒM ngày này (đêm cuối được tính)
    gia_thuong: Mapped[float] = mapped_column(TIEN)                       # giá bán / phòng / đêm, chưa thuế phí
    gia_cuoi_tuan: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # đêm thứ Sáu, thứ Bảy
    gia_niem_yet: Mapped[float | None] = mapped_column(TIEN, nullable=True)    # giá niêm yết của khách sạn (hiện gạch)
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")
