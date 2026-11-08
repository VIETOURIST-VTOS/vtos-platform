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

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, false, true
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
# KS-16j
NHAN_TRE_EM = {"chua_xac_nhan": "Chưa xác nhận", "moi_tuoi": "Nhận trẻ em mọi lứa tuổi", "tu_tuoi": "Chỉ nhận trẻ từ … tuổi",
               "khong": "Không nhận trẻ em"}
CACH_TINH_TRE = {"mien_phi": "Luôn miễn phí (giường có sẵn)", "co_dinh": "Giá cố định / đêm", "phan_tram": "% giá phòng / đêm"}
NHOM_TUOI = {"so_sinh": "Trẻ sơ sinh", "tre_em": "Trẻ em"}
KIEU_GIA = {"co_dinh": "Cố định (đ / đêm)", "phan_tram": "% giá phòng / đêm"}
CHE_DO_TRE_GOI = {"": "Theo phòng / khách sạn", "rieng": "Giá trẻ em riêng cho gói", "nhu_nguoi_lon": "Tính trẻ em như người lớn"}
TIEN_NGHI_PHONG = ("Máy lạnh", "Wifi", "Vòi sen", "Bồn tắm", "Ban công", "Hướng biển", "Không hút thuốc", "Minibar",
                   "Két sắt", "Bếp nhỏ", "Hồ bơi riêng", "TV", "Máy sấy tóc", "Bàn làm việc",
                   "Hướng thành phố", "Hướng núi / vườn", "Máy giặt")   # KS-19: thêm cho bộ lọc hướng nhìn / tiện nghi
NGUON_LP = {"agoda": "Agoda", "booking": "Booking.com", "ks_gui": "Khách sạn gửi", "hop_dong": "Hợp đồng", "khac": "Khác"}
CAN_XAC_NHAN = {"ten_hang": "Tên hạng thực tế", "dien_tich": "Diện tích", "giuong": "Giường", "tre_em": "Trẻ em / giường phụ",
                "tien_nghi": "Tiện nghi mâu thuẫn", "hop_dong": "Hợp đồng", "han_muc": "Hạn mức", "gia": "Giá VTD"}
TRANG_THAI_DC = {"dang_doi_chieu": "Đang đối chiếu", "cho_ks": "Chờ khách sạn xác nhận", "da_xac_nhan": "Đã xác nhận"}
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
    # KS-16j: chính sách trẻ em có cấu trúc kiểu Agoda (Chủ tịch duyệt 01/11/2026). cs_tre_em / cs_giuong_phu ở trên
    # giờ là «ghi chú thêm». Mốc tuổi: [{tu, den, cach: mien_phi|phu_thu|nguoi_lon, phu_thu, an_sang}] — tiền / đêm, đã gồm 8% VAT (KS-19).
    cs_nhan_tre_em: Mapped[str] = mapped_column(String(14), default="chua_xac_nhan")   # NHAN_TRE_EM
    cs_tre_tu_tuoi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cs_moc_tuoi: Mapped[list] = mapped_column(JSON, default=list)
    cs_phi_giuong_phu: Mapped[float | None] = mapped_column(TIEN, nullable=True)       # / đêm, đã gồm 8% VAT (KS-19); None = chưa xác nhận
    cs_giuong_phu_an_sang: Mapped[bool] = mapped_column(Boolean, default=False)
    cs_noi: Mapped[str] = mapped_column(String(120), default="")                       # «Miễn phí, theo yêu cầu»
    # KS-16k (Chủ tịch duyệt 01/11/2026 — theo cách Agoda YCS): cs_moc_tuoi giờ là GIÁ TRẺ EM MẶC ĐỊNH theo nhóm tuổi
    # [{tu, den, nhom: so_sinh|tre_em, cach: mien_phi|co_dinh|phan_tram, gia, an_sang (đ/đêm, None = cần xác nhận)}];
    # trên tuổi «den» lớn nhất = người lớn. cs_tre_tu_tuoi = tuổi tối thiểu của khách (khi «tu_tuoi»).
    cs_so_tre_mien_phi: Mapped[int | None] = mapped_column(Integer, nullable=True)     # mỗi phòng; None = cần xác nhận
    cs_tre_mp_tinh_suc_chua: Mapped[bool] = mapped_column(Boolean, default=False)      # trẻ miễn phí có tính vào sức chứa
    cs_giuong_phu_kieu: Mapped[str] = mapped_column(String(10), default="co_dinh")     # co_dinh (đ) | phan_tram (% giá phòng)
    # KS-19 (Chủ tịch 05/11/2026): giá Điều hành nhập ĐÃ GỒM 8% VAT; máy không cộng thuế phí, ô % này luôn lưu 0
    # (giữ cột cho dữ liệu cũ). Trước KS-19: giá chưa gồm thuế phí, % theo từng khách sạn.
    thue_phi_pt: Mapped[float | None] = mapped_column(Float, default=0, nullable=True)
    # KS-17: 0% mặc định KHÔNG phải xác nhận «khách sạn không thu thuế». Chưa xác nhận thì không duyệt được gói giá
    # và không mở được thanh toán của khách sạn.
    thue_phi_xac_nhan: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    phu_hop: Mapped[list] = mapped_column(JSON, default=list)   # KS-19: khoá trong PHU_HOP (dịch vụ) — bộ lọc «Phù hợp cho»
    lien_he_noi_bo: Mapped[str] = mapped_column(String(300), default="")  # KHÔNG ra cổng
    ghi_chu_noi_bo: Mapped[str] = mapped_column(Text, default="")         # KHÔNG ra cổng
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    hien_cong: Mapped[bool] = mapped_column(Boolean, default=False)
    # KS-16s (Chủ tịch duyệt bản xem thử 01/11/2026): tọa độ cho «Xem trên bản đồ» — máy tự lấy từ địa chỉ
    # (OpenStreetMap) hoặc Điều hành dán link Google Maps («tay» thì máy không ghi đè).
    vi_do: Mapped[float | None] = mapped_column(Float, nullable=True)
    kinh_do: Mapped[float | None] = mapped_column(Float, nullable=True)
    toa_do_nguon: Mapped[str] = mapped_column(String(12), default="")      # "" | tu_dong | tay | khong_thay
    # KS-16s: công tắc mở thanh toán trực tuyến riêng khách sạn — chỉ trả được khi CẢ công tắc chung cũng bật.
    mo_thanh_toan: Mapped[bool] = mapped_column(Boolean, default=False)
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
    mo_ta_thay_the: Mapped[str] = mapped_column(String(200), default="", server_default="")   # KS-17: chữ thay ảnh (alt)
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
    mo_ta: Mapped[str] = mapped_column(String(300), default="")         # đặc điểm ngắn — quá 300 thì báo lỗi, không cắt
    mo_ta_dai: Mapped[str] = mapped_column(Text, default="")            # KS-16j: mô tả chi tiết (≤3.000), khách bấm «Xem thêm»
    tien_nghi: Mapped[list] = mapped_column(JSON, default=list)         # KS-16j: tên tiện nghi (chọn sẵn hoặc gõ thêm)
    toi_da_nguoi_lon: Mapped[int | None] = mapped_column(Integer, nullable=True)   # KS-17: None = chưa xác nhận
    tong_khach_toi_da: Mapped[int | None] = mapped_column(Integer, nullable=True)   # KS-17: tổng NL + TE một phòng; None = chưa xác nhận
    toi_da_tre_em: Mapped[int | None] = mapped_column(Integer, nullable=True)   # KS-16j: None = chưa xác nhận (khác 0)
    giuong_phu_toi_da: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = chưa xác nhận
    noi_cui: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # KS-16k: sức chứa kiểu Agoda + ghi đè giá trẻ em / giường phụ của riêng phòng này (None = theo khách sạn)
    suc_chua: Mapped[int | None] = mapped_column(Integer, nullable=True)            # sức chứa cơ bản; None = tối đa người lớn
    khach_them_toi_da: Mapped[int | None] = mapped_column(Integer, nullable=True)   # khách thêm (nằm giường phụ); None = cần xác nhận
    so_tre_mien_phi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phi_giuong_phu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    giuong_phu_kieu: Mapped[str] = mapped_column(String(10), default="")            # "" = theo khách sạn
    giuong_phu_xac_nhan: Mapped[bool] = mapped_column(Boolean, default=False)       # «theo xác nhận của KS» — vẫn bán ngay
    gia_tre_rieng: Mapped[list | None] = mapped_column(JSON, nullable=True)         # None = theo khách sạn
    # KS-16j: nguồn & đối chiếu — NỘI BỘ, không ra cổng khách
    nguon: Mapped[str] = mapped_column(String(12), default="")          # NGUON_LP
    ky_doi_chieu: Mapped[str] = mapped_column(String(120), default="")
    ma_hang: Mapped[str] = mapped_column(String(80), default="")        # mã hạng phòng của KS / OTA — ghi đúng nguồn
    ten_tuong_duong: Mapped[str] = mapped_column(String(160), default="")
    can_xac_nhan: Mapped[list] = mapped_column(JSON, default=list)      # khoá trong CAN_XAC_NHAN
    ghi_chu_doi_chieu: Mapped[str] = mapped_column(String(500), default="")
    trang_thai_dc: Mapped[str] = mapped_column(String(14), default="")  # TRANG_THAI_DC — Điều hành tự ghi, không chặn bán
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
    # KS-17: giờ chốt hủy trong ngày hạn hủy («» = hết ngày), múi giờ của giờ ấy, và gói có cho trả sau không.
    huy_gio_chot: Mapped[str] = mapped_column(String(5), default="", server_default="")
    huy_mui_gio: Mapped[str] = mapped_column(String(40), default="Asia/Ho_Chi_Minh", server_default="Asia/Ho_Chi_Minh")
    cho_tra_sau: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    dang_ban: Mapped[bool] = mapped_column(Boolean, default=True)
    trang_thai: Mapped[str] = mapped_column(String(10), default="nhap", index=True)
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    # KS-16k: giá trẻ em của gói — "" theo phòng / khách sạn · "rieng" dùng gia_tre · "nhu_nguoi_lon"
    tre_em_che_do: Mapped[str] = mapped_column(String(14), default="")
    gia_tre: Mapped[list | None] = mapped_column(JSON, nullable=True)
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
    gia_thuong: Mapped[float] = mapped_column(TIEN)                       # giá bán / phòng / đêm, đã gồm 8% VAT (KS-19)
    gia_cuoi_tuan: Mapped[float | None] = mapped_column(TIEN, nullable=True)   # đêm thứ Sáu, thứ Bảy
    gia_niem_yet: Mapped[float | None] = mapped_column(TIEN, nullable=True)    # giá niêm yết của khách sạn (hiện gạch)
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")


class CaiDatKsVtd(Base):
    """KS-16s: cài đặt chung của cổng khách sạn VTD (khóa → giá trị). Hiện có: mo_thanh_toan = "1" | "0"."""
    __tablename__ = "cai_dat_ks_vtd"
    khoa: Mapped[str] = mapped_column(String(40), primary_key=True)
    gia_tri: Mapped[str] = mapped_column(String(200), default="")
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
