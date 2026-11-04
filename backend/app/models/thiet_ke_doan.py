"""TK-1 · Khách TỰ THIẾT KẾ TOUR ĐOÀN trên cổng khách — giai đoạn 1 (Chủ tịch 04/11/2026: «làm luôn giai đoạn 1»;
gộp bản Claude v7 với bản Codex «vtd-thiet-ke-chuyen-di-rieng»).

Hai bảng:
  · DonGiaDoan  — đơn giá dịch vụ đoàn mà VTOS CHƯA có nguồn: xe theo số chỗ, HDV, trưởng đoàn, bảo hiểm, nước, visa,
                  hội nghị, team building… ĐIỀU HÀNH NHẬP, người khác người nhập duyệt (TP Điều hành; Chủ tịch / TGĐ tự
                  duyệt được). Chỉ dòng «hiệu lực» và trong hạn mới vào tạm tính. Giá ở đây là GIÁ VỐN.
  · ThietKeDoan — mỗi lần khách gửi là một PHIÊN BẢN (ma + phien_ban). Bất biến sau khi ghi: thiết kế khách gửi,
                  dự toán MÁY CHỦ tính lại (bỏ qua mọi con số trình duyệt gửi), nguồn giá đã dùng. Sửa = phiên bản mới.

Khách sạn lấy từ gói giá VTD đã duyệt (KS-13), bữa ăn từ thực đơn nhà hàng (KH-2). Vé máy bay chưa có nguồn giá (VB-1
chỉ chuyển sang OTA) → dòng «Sales báo giá», không cộng vào tạm tính. Thiếu giá = ghi «chưa có giá», KHÔNG coi là 0.
"""
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Loại dịch vụ Điều hành nhập đơn giá. Đơn vị tính cố định theo loại để không ai nhập nhầm cách nhân.
LOAI_DON_GIA = {
    "xe": ("Xe du lịch (theo số chỗ)", "xe_ngay"),
    "hdv": ("Hướng dẫn viên suốt tuyến", "ngay"),
    "truong_doan": ("Trưởng đoàn kiêm hướng dẫn viên (tour xa)", "ngay"),
    "bao_hiem": ("Bảo hiểm du lịch", "khach"),
    "nuoc": ("Nước suối", "khach_ngay"),
    # Visa KHÔNG có đơn giá chung (Chủ tịch 04/11/2026: mỗi nước một loại visa, giá khác nhau) — Sales báo giá.
    "hoi_nghi": ("Phòng hội nghị (MICE)", "doan"),
    "team_building": ("Team building", "khach"),
    "khac": ("Dịch vụ khác", "doan"),
    # Vé máy bay theo CHẶNG (điểm đi → điểm đến, hạng vé): giá tham khảo Điều hành nhập cho đến khi nối API vé
    # (services/thiet_ke_doan.NGUON_VE). Giá người lớn ở `gia`, trẻ em / em bé ở cột riêng.
    "ve_may_bay": ("Vé máy bay theo chặng", "khach_chang"),
}
DON_VI = {"xe_ngay": "xe / ngày", "ngay": "ngày", "khach": "khách", "khach_ngay": "khách / ngày", "doan": "đoàn",
          "khach_chang": "khách / chặng"}
HANG_VE = {"pho_thong": "Phổ thông", "pho_thong_dac_biet": "Phổ thông đặc biệt", "thuong_gia": "Thương gia"}
PHAM_VI = {"dn": "Trong nước", "nn": "Nước ngoài", "ca_hai": "Cả hai"}
TRANG_THAI_DG = {"cho_duyet": "Chờ duyệt", "hieu_luc": "Hiệu lực", "tu_choi": "Từ chối", "ngung": "Ngừng"}


class DonGiaDoan(Base):
    __tablename__ = "don_gia_doan"
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(20), index=True)                 # khoá LOAI_DON_GIA
    ten: Mapped[str] = mapped_column(String(160))                              # «Xe 29 chỗ», «Bảo hiểm quốc tế gói A»
    pham_vi: Mapped[str] = mapped_column(String(8), default="ca_hai")
    tu_cho: Mapped[int | None] = mapped_column(Integer, nullable=True)        # chỉ loại xe: số chỗ khách
    # TK-3 (Chủ tịch 04/11/2026): đơn giá nước ngoài gắn CHÂU LỤC hoặc NƯỚC — rỗng = mọi nước. Tạm tính chọn dòng
    # khớp nhất với nước khách đi (nước > châu lục > mọi nước); visa Schengen không bị tính cho tour Thái Lan.
    khu_vuc: Mapped[str] = mapped_column(String(60), default="")
    gia: Mapped[float] = mapped_column(TIEN)                                   # GIÁ VỐN theo đơn vị của loại
    # chỉ loại ve_may_bay: chặng, hạng vé, giá trẻ em / em bé (rỗng = chưa có, KHÔNG phải 0)
    tu_diem: Mapped[str] = mapped_column(String(80), default="")
    den_diem: Mapped[str] = mapped_column(String(80), default="")
    hang_ve: Mapped[str] = mapped_column(String(20), default="")
    gia_tre_em: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_em_be: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tu_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)         # rỗng = còn hiệu lực
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    trang_thai: Mapped[str] = mapped_column(String(10), default="cho_duyet", index=True)
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do: Mapped[str] = mapped_column(String(300), default="")


class ThietKeDoan(Base):
    __tablename__ = "thiet_ke_doan"
    __table_args__ = (UniqueConstraint("ma", "phien_ban", name="uq_thiet_ke_doan_ma_pb"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), index=True)                    # TK-000123 — giữ nguyên qua các phiên bản
    phien_ban: Mapped[int] = mapped_column(Integer, default=1)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    yeu_cau_id: Mapped[int | None] = mapped_column(ForeignKey("yeu_cau_khach.id"), nullable=True, index=True)
    thiet_ke: Mapped[dict] = mapped_column(JSON, default=dict)                 # bản khách gửi (đã làm sạch)
    du_toan: Mapped[dict] = mapped_column(JSON, default=dict)                  # máy chủ tính: dòng vốn + bán, thiếu giá
    tong_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)        # tạm tính khách thấy
    tong_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ngay_di: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_khach: Mapped[int] = mapped_column(Integer, default=0)
    tom_tat: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(12), default="da_gui")      # da_gui | thay_the (có phiên bản mới hơn)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class NgayLeTet(Base):
    """TK-1e (Chủ tịch 04/11/2026: thù lao HDV ngày lễ Tết nhân đôi trong tạm tính). Lịch ngày lễ Tết do Điều hành nhập
    ở màn /tour-doan — máy không tự suy lịch âm. Ngày đi tour trùng ngày ở đây thì thù lao HDV ngày ấy ×2."""
    __tablename__ = "ngay_le_tet"
    id: Mapped[int] = mapped_column(primary_key=True)
    ngay: Mapped[date] = mapped_column(Date, unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(120), default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ══ TK-2 · GIAI ĐOẠN 2 — BÁO GIÁ CHÍNH THỨC (Chủ tịch 04/11/2026, duyệt bản xem thử) ════════════════════════════
# Điều hành lập từ một phiên bản thiết kế khách gửi: máy chép dòng tạm tính kèm giá vốn, Điều hành sửa theo xác nhận
# thật của NCC, điền dòng thiếu giá. Biên ≥ 10% → TP Điều hành duyệt (khác người lập); < 10% → Chủ tịch / TGĐ, có lý
# do. Duyệt xong khóa (hash), hiện cho khách 24 giờ. Giá trẻ em = 75% người lớn (tour đi xe) / 80% (có chặng bay).
# Khách đồng ý → máy tạo hợp đồng khách NHÁP (hop_dong_khach) cho Sale Admin hoàn thiện. Đặt cọc là giai đoạn 3.
TRANG_THAI_BG = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "tra_lai": "Trả lại", "da_duyet": "Đã gửi khách",
                 "khach_dong_y": "Khách đồng ý", "het_han": "Hết hạn", "thay_the": "Bị thay (khách sửa thiết kế)"}


class BaoGiaDoan(Base):
    __tablename__ = "bao_gia_doan"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(24), unique=True, index=True)               # BGD-000001
    thiet_ke_id: Mapped[int] = mapped_column(ForeignKey("thiet_ke_doan.id"), index=True)
    thiet_ke_ma: Mapped[str] = mapped_column(String(20), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    dong: Mapped[list] = mapped_column(JSON, default=list)       # [{nhom, ten, chi_tiet, von|None, ban, nguon}]
    bien_pt: Mapped[float] = mapped_column(TIEN, default=10)     # %
    he_so_te: Mapped[float] = mapped_column(TIEN, default=0.75)
    so_nl: Mapped[int] = mapped_column(Integer, default=0)
    so_te: Mapped[int] = mapped_column(Integer, default=0)
    so_eb: Mapped[int] = mapped_column(Integer, default=0)
    tong_von: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tong_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)                # khách trả = NL × giá + TE × giá
    gia_nl: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_te: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    bao_gom: Mapped[list] = mapped_column(JSON, default=list)
    khong_bao_gom: Mapped[list] = mapped_column(JSON, default=list)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    trang_thai: Mapped[str] = mapped_column(String(14), default="nhap", index=True)
    cap_duyet: Mapped[str] = mapped_column(String(10), default="")        # tp_dh | ct_tgd
    ly_do_bien: Mapped[str] = mapped_column(String(300), default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    gui_duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_tra: Mapped[str] = mapped_column(String(300), default="")
    han_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ma_bam: Mapped[str] = mapped_column(String(64), default="")
    khach_dong_y_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hop_dong_id: Mapped[int | None] = mapped_column(ForeignKey("hop_dong_khach.id"), nullable=True)
