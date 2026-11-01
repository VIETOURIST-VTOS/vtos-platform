"""KH-2 · Danh mục NHÀ HÀNG cho cổng khách hàng (Chủ tịch duyệt bản xem thử 26/10/2026).

Điều hành nhập nhà hàng và các gói thực đơn; chỉ TP Điều hành bật «Hiện trên cổng» (DT-2b, Chủ tịch 28/10/2026 —
trước đó là Kinh doanh); người vừa nhập / sửa không tự bật.
Sửa nội dung bán (giá, thực đơn, điều kiện) của một nhà hàng đang hiện thì nó TỰ TẮT và chờ TP Điều hành
bật lại — giá lên cổng luôn là giá đã có người thứ hai nhìn qua.

Chỉ có GIÁ BÁN cho khách. Giá vốn / phí nhà cung cấp đi theo hợp đồng NCC ở chỗ khác, không nằm ở đây,
nên không có đường nào để chúng lọt ra cổng.
"""
from datetime import date, datetime
from sqlalchemy import JSON, String, Integer, Date, DateTime, Text, Boolean, Float, ForeignKey
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
    # PL-1 (Chủ tịch duyệt bản xem thử 30/10/2026): phân loại. «Đặc sản địa phương»: máy tự gắn khi nguồn là
    # TasteAtlas; Điều hành đổi tay qua đề xuất → chốt. Bậc sang trọng: máy GỢI Ý (thực đơn đang bán, hoặc hạng / mức
    # giá Michelin Điều hành nhập), NV ĐH đề xuất, TP ĐH chốt (Chủ tịch / TGĐ chốt ngay). Cổng chỉ hiện bậc ĐÃ CHỐT.
    dac_san_tay: Mapped[str] = mapped_column(String(4), default="")          # "" theo máy | gan | go
    dac_san_ly_do: Mapped[str] = mapped_column(String(200), default="")
    dac_san_de_xuat: Mapped[str] = mapped_column(String(4), default="")      # "" không có | gan | go | may
    dac_san_de_xuat_ly_do: Mapped[str] = mapped_column(String(200), default="")
    dac_san_de_xuat_boi: Mapped[str] = mapped_column(String(50), default="")
    dac_san_de_xuat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    michelin_hang: Mapped[str] = mapped_column(String(10), default="")       # "" chưa ghi | sao3 sao2 sao1 bib selected khong
    michelin_gia: Mapped[int] = mapped_column(Integer, default=0)            # 0 chưa ghi · 1–4 = ₫ … ₫₫₫₫
    michelin_boi: Mapped[str] = mapped_column(String(50), default="")
    michelin_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bac: Mapped[str] = mapped_column(String(12), default="")                 # ĐÃ CHỐT: binh_dan tam_trung cao_cap sang_trong
    bac_chot_boi: Mapped[str] = mapped_column(String(50), default="")
    bac_chot_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bac_de_xuat: Mapped[str] = mapped_column(String(12), default="")
    bac_de_xuat_boi: Mapped[str] = mapped_column(String(50), default="")
    bac_de_xuat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # AT-2 (Chủ tịch duyệt bản xem thử 01/11/2026): ghim bản đồ + công tắc mở thanh toán trực tuyến của từng nhà hàng.
    # toa_do_nguon: "" chưa lấy · tu_dong (OpenStreetMap từ địa chỉ) · tay (Điều hành dán link Google Maps) · khong_thay
    vi_do: Mapped[float | None] = mapped_column(Float, nullable=True)
    kinh_do: Mapped[float | None] = mapped_column(Float, nullable=True)
    toa_do_nguon: Mapped[str] = mapped_column(String(12), default="")
    mo_thanh_toan: Mapped[bool] = mapped_column(Boolean, default=False)      # cùng công tắc chung mới trả được


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


# ══ AT-2a · ALBUM ẢNH NHÀ HÀNG (Chủ tịch + Điều hành chốt 29/10/2026) ═══════════════════════════════════════
# Chỉ ảnh của chính nhà hàng. Mỗi ảnh ghi CĂN CỨ QUYỀN DÙNG; «Chưa xác minh» không duyệt được, không ra cổng.
# TP Điều hành duyệt, người tải không tự duyệt (trừ Chủ tịch, TGĐ). Chỉ ảnh «Đã duyệt» ra cổng khách.
# Bản gốc giữ trong kho (nội bộ); cổng khách chỉ nhận bản hiển thị nhẹ do máy tạo.
NHOM_ANH = {"mat_tien": "Mặt tiền", "khong_gian": "Không gian", "phong_rieng": "Phòng riêng", "mon_an": "Món ăn",
            "trai_nghiem": "Trải nghiệm"}
CAN_CU_ANH = {"nha_hang": "Nhà hàng cấp quyền", "vtd_chup": "VTD tự chụp", "ben_thu_ba": "Bên thứ ba cấp phép",
              "chua_xac_minh": "Chưa xác minh"}
TRANG_THAI_ANH = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt", "an": "Ẩn"}


class AnhNhaHang(Base):
    __tablename__ = "anh_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))            # bản gốc — chỉ nội bộ
    hien_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)   # bản hiển thị (≤1600px)
    nho_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)    # ảnh nhỏ (≤480px)
    rong: Mapped[int] = mapped_column(Integer, default=0)
    cao: Mapped[int] = mapped_column(Integer, default=0)
    nhom: Mapped[str] = mapped_column(String(20), default="")          # NHOM_ANH; rỗng = ảnh chuyển từ ảnh đơn cũ
    chu_thich: Mapped[str] = mapped_column(String(200), default="")
    mo_ta_thay_the: Mapped[str] = mapped_column(String(200), default="")
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    la_bia: Mapped[bool] = mapped_column(Boolean, default=False)
    can_cu: Mapped[str] = mapped_column(String(20), default="chua_xac_minh")
    can_cu_ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    credit: Mapped[str] = mapped_column(String(160), default="")
    trang_thai: Mapped[str] = mapped_column(String(12), default="nhap")
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    tai_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══ AT-2b · MÓN ĂN VÀ THỰC ĐƠN NHÀ HÀNG (Chủ tịch chốt 29/10/2026) ═══════════════════════════════════════════
# Món KHÔNG có giá — giá chỉ nằm trên thực đơn nhà hàng; giá bán qua VTD vẫn chỉ ở gói đặt bàn (ThucDonNhaHang).
# Thực đơn 4 loại, mỗi lần thay là một phiên bản mới; bản cũ giữ nguyên. Không tính vào 60 ảnh album.
NHOM_MON_NH = {"khai_vi": "Khai vị", "mon_chinh": "Món chính", "mon_nuoc": "Món nước", "trang_mieng": "Tráng miệng",
               "do_uong": "Đồ uống"}
DI_UNG = {"dau_phong": "Đậu phộng", "hai_san_vo": "Hải sản có vỏ", "ca": "Cá", "gluten": "Gluten", "sua": "Sữa",
          "trung": "Trứng", "dau_nanh": "Đậu nành"}
LOAI_THUC_DON = {"goi_mon": "Gọi món", "set_menu": "Set menu", "buffet": "Buffet", "khach_doan": "Khách đoàn (set menu)"}


class MonNhaHang(Base):
    __tablename__ = "mon_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    ten: Mapped[str] = mapped_column(String(160))
    ten_khac: Mapped[str] = mapped_column(String(160), default="")
    nhom: Mapped[str] = mapped_column(String(20), default="mon_chinh")
    mo_ta: Mapped[str] = mapped_column(String(500), default="")
    di_ung: Mapped[list | None] = mapped_column(JSON, nullable=True)        # khóa trong DI_UNG — nhà hàng xác nhận
    cay: Mapped[bool] = mapped_column(Boolean, default=False)
    chay: Mapped[bool] = mapped_column(Boolean, default=False)
    anh_id: Mapped[int | None] = mapped_column(ForeignKey("anh_nha_hang.id"), nullable=True)   # ảnh trong album
    noi_bat: Mapped[bool] = mapped_column(Boolean, default=False)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    trang_thai: Mapped[str] = mapped_column(String(12), default="nhap")    # nhap | cho_duyet | da_duyet | an
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ThucDonBan(Base):
    """Một PHIÊN BẢN thực đơn của nhà hàng (một loại). Bất biến: thay = tải bản mới, bản cũ giữ."""
    __tablename__ = "thuc_don_ban"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    loai: Mapped[str] = mapped_column(String(20))
    so: Mapped[int] = mapped_column(Integer, default=1)                    # 1 → v1.0, 2 → v1.1 …
    hieu_luc_tu: Mapped[date] = mapped_column(Date)
    can_cu: Mapped[str] = mapped_column(String(300), default="")
    so_trang: Mapped[int] = mapped_column(Integer, default=0)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho_duyet")   # cho_duyet | duyet | tra_lai
    ly_do_tra_lai: Mapped[str] = mapped_column(String(300), default="")
    tai_boi: Mapped[str] = mapped_column(String(50), default="")
    tai_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ThucDonTrang(Base):
    __tablename__ = "thuc_don_trang"
    id: Mapped[int] = mapped_column(primary_key=True)
    ban_id: Mapped[int] = mapped_column(ForeignKey("thuc_don_ban.id"), index=True)
    thu_tu: Mapped[int] = mapped_column(Integer, default=1)
    attachment_id: Mapped[int] = mapped_column(ForeignKey("attachments.id"))        # tệp gốc (ảnh / PDF)
    hien_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    nho_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)


# ══ AT-2c · BIÊN TẬP VÀ MỨC HOÀN THIỆN (Chủ tịch chốt 29/10/2026) ═══════════════════════════════════════════
# Điểm hoàn thiện do MÁY tính từ dữ liệu đã duyệt — không lưu, không chấm tay. Bảng này chỉ giữ việc giao:
# Chủ tịch giao nhà hàng cho một người biên tập (NV Điều hành / NV Marketing) kèm hạn.
class BienTapNhaHang(Base):
    __tablename__ = "bien_tap_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), unique=True)
    nguoi: Mapped[str] = mapped_column(String(50), default="")
    han: Mapped[date | None] = mapped_column(Date, nullable=True)
    giao_boi: Mapped[str] = mapped_column(String(50), default="")
    giao_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    da_xin_boi: Mapped[str] = mapped_column(String(50), default="")
    da_xin_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══ AT-3 · ĐÁNH GIÁ SAO NHÀ HÀNG (Chủ tịch duyệt bản xem thử 29/10/2026) ═════════════════════════════════════
# Chỉ NGƯỜI ĐẶT của một đơn đặt bàn nhà hàng đã báo «khách đã dùng» mới viết được; một bài / đơn; trong 30 ngày
# sau bữa ăn; sửa được 7 ngày. Hiện NGAY. Không ai ẩn được vì bài chê: chỉ NV / PTGĐ Marketing ẩn vì vi phạm
# (4 lý do, bắt buộc ghi), TP Điều hành xem lại. Nhà hàng trả lời công khai một lần, sửa trong 24 giờ.
LY_DO_AN_DG = {"chui_boi": "Chửi bới, xúc phạm", "thong_tin_ca_nhan": "Lộ thông tin cá nhân",
               "quang_cao": "Quảng cáo / spam", "anh_sai": "Ảnh không phải món ăn, không gian"}
MUC_DG = {"diem_mon": "Món ăn", "diem_phuc_vu": "Phục vụ", "diem_khong_gian": "Không gian", "diem_gia": "Đáng giá tiền"}


class DanhGiaNhaHang(Base):
    __tablename__ = "danh_gia_nha_hang"
    id: Mapped[int] = mapped_column(primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_dat_ban.id"), unique=True)
    nha_hang_id: Mapped[int] = mapped_column(ForeignKey("nha_hang.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    ten_hien: Mapped[str] = mapped_column(String(40), default="")        # đã che, chụp lúc viết
    ngay_an: Mapped[date] = mapped_column(Date)
    so_khach: Mapped[int] = mapped_column(Integer, default=1)
    la_doan: Mapped[bool] = mapped_column(Boolean, default=False)
    diem: Mapped[int] = mapped_column(Integer)                            # 1–5, bắt buộc
    # Bốn mục phụ: RỖNG khác 0 — bỏ trống thì không tính vào điểm mục đó.
    diem_mon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_phuc_vu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_khong_gian: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_gia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nhan_xet: Mapped[str] = mapped_column(Text, default="")
    anh: Mapped[list] = mapped_column(JSON, default=list)                 # [{goc, hien, nho, an, ly_do}]
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    an: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    an_ly_do: Mapped[str] = mapped_column(String(20), default="")
    an_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    an_boi: Mapped[str] = mapped_column(String(50), default="")
    an_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    xem_lai: Mapped[str] = mapped_column(String(6), default="")          # "" chờ · "giu" · "hien"
    xem_lai_boi: Mapped[str] = mapped_column(String(50), default="")
    xem_lai_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    tra_loi_boi: Mapped[str] = mapped_column(String(60), default="")
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tra_loi_an: Mapped[bool] = mapped_column(Boolean, default=False)
    tra_loi_an_ly_do: Mapped[str] = mapped_column(String(20), default="")
