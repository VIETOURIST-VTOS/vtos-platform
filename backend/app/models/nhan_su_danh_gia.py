"""Ba bảng HCNS mở cùng MỘT migration (Chủ tịch chốt 08–09/10/2026):

    5.6   Đánh giá nhân sự   → `danh_gia_nhan_su`
    5.9.2 Đề nghị mua        → `de_nghi_mua`
    5.9.3 Cấp phát tài sản   → `cap_phat_tai_san`

GOM BA BẢNG VÀO MỘT MIGRATION LÀ CÓ CHỦ Ý. Ngày 14/9/2026 một migration đã chặn deploy một lần, và
bốn làn đang cùng đẩy lên một nhánh chính — hai đầu migration mở song song thì alembic có hai head và
container không khởi động được. Ba bảng một lần là ba lần đụng rút còn một.

──────────────────────────────────────────────────────────────────────────────────────────────────
5.6 — VÌ SAO BẢNG CHẤM CHIA HAI CỘT, VÀ VÌ SAO KHÔNG CÓ CÔNG THỨC TRẢ TIỀN
──────────────────────────────────────────────────────────────────────────────────────────────────
VTOS đã có SỐ THẬT cho một phần việc: chỉ tiêu doanh thu, chuyến quá hạn quyết toán, sự vụ mức 2–3,
ngày công, đơn nghỉ. Phần còn lại — thái độ, phối hợp, chịu trách nhiệm — máy không đo được và KHÔNG
NÊN giả vờ đo. Trộn chung thành một điểm thì con số của máy che mất phần người phải nhìn. Nên ba ô
`a1/a2/a3` là MÁY ĐIỀN (người chấm không sửa được: không có cửa ghi nào nhận chúng), ba ô `b1/b2/b3`
là người chấm.

Chủ tịch chốt 09/10/2026: điểm **chỉ để XÉT thưởng**, TGĐ/Chủ tịch quyết mức tiền từng người bằng
tay. Hệ quả kỹ thuật đáng giá nhất của quyết định ấy: **không một dòng mã nào biến điểm thành tiền,
nên không có công thức nào để lách** — và không có chuyện phần mềm trả thưởng sai mà không ai ký.
Bảng này cố ý KHÔNG có cột tiền.

Ô "chưa có số" KHÁC HẲN ô 0 điểm. Phòng nào VTOS chưa có nguồn số cho A1 thì ô ấy để trống kèm chữ,
và `diem_tong` tính trung bình CÁC Ô CÓ SỐ — chấm 3 cho qua chuyện là bịa ra một con số rồi đem nó đi
xét thưởng.

ĐIỂM ĐẺ RA TIỀN THÌ ĐIỂM SẼ TRÔI. Ba ô máy điền không ai sửa được nên chúng là cái neo: hệ thống in
độ lệch "điểm người − điểm máy" theo từng trưởng phòng. Đó cũng là lý do mốc "chấm một kỳ chưa ra
tiền" đáng giá — nó không phải thủ tục, nó là CÁI THƯỚC để biết trung bình nhảy lên bao nhiêu.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

# ── 5.6 ───────────────────────────────────────────────────────────────────────────────────────────
# Ba kỳ, và chỉ MỘT kỳ phải chấm tay. Chấm tay cả ba là 11 trưởng phòng x 103 người x 17 lần/năm;
# tới lần thứ năm thì bảng bị bấm cho xong, và một bảng bị bấm cho xong in ra điểm mà không ai tin.
KY_LOAI = {
    "thang": "Tháng – trưởng phòng chấm tay",
    "quy":   "Quý – tự tổng hợp từ ba tháng, thêm một ô nhận xét",
    "nam":   "Năm – tự tổng hợp từ bốn quý, thêm một ô nhận xét",
}
KY_TU_TONG_HOP = ("quy", "nam")

# Thang điểm dùng chung cho cả sáu ô. Khai ở đây MỘT chỗ để màn hình và cửa máy chủ đọc cùng một bản.
THANG_DIEM = {5: "Vượt mong đợi", 4: "Tốt", 3: "Đạt", 2: "Cần cải thiện", 1: "Không đạt"}

# Ba ô máy điền. Khoá là tên cột, giá trị là nguồn số — in thẳng lên màn hình để người đọc biết con
# số từ đâu ra; một ô điểm không nói được nguồn thì người bị chấm không có cách nào cãi.
O_MAY_DIEN = {
    "a1": "Kết quả theo chỉ tiêu",
    "a2": "Kỷ luật thời gian (ngày công, nghỉ không phép, quyết toán quá hạn)",
    "a3": "Sự vụ mức 2 và mức 3 trong kỳ",
}
O_NGUOI_CHAM = {
    "b1": "Chất lượng công việc",
    "b2": "Phối hợp",
    "b3": "Chịu trách nhiệm & chủ động",
}

# Bắt buộc viết lý do ở hai đầu thang. Một bảng toàn điểm 4 không có chữ nào là một bảng không ai đọc
# lần thứ hai — mà chính những bảng ấy mới là bảng đem đi xét thưởng.
DIEM_BAT_BUOC_LY_DO = (5, 2, 1)

XEP_HANG = (
    (4.5, "xuat_sac",      "Xuất sắc"),
    (3.5, "tot",           "Tốt"),
    (2.5, "dat",           "Đạt"),
    (1.5, "can_cai_thien", "Cần cải thiện"),
    (0.0, "khong_dat",     "Không đạt"),
)
# Hai mức dưới BẮT BUỘC ghi việc phải sửa kỳ tới. Không có ô ấy thì "cần cải thiện" là một nhãn,
# không phải một việc.
XEP_HANG_PHAI_GHI_VIEC = ("can_cai_thien", "khong_dat")

DG_TRANG_THAI = {
    "nhap":    "Nháp – trưởng phòng đang chấm",
    "da_cham": "Đã chấm – nhân viên đọc được bản của mình",
    "da_gui":  "Đã gửi HCNS / TGĐ – khoá, muốn sửa phải mở lại",
}


class DanhGiaNhanSu(Base):
    """Một dòng = một người, một kỳ. Kỳ tháng chấm tay; kỳ quý và năm tự tổng hợp."""
    __tablename__ = "danh_gia_nhan_su"
    __table_args__ = (UniqueConstraint("employee_id", "ky_loai", "ky", name="uq_danh_gia_nguoi_ky"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    ky_loai: Mapped[str] = mapped_column(String(10), default="thang", index=True)   # thang / quy / nam
    ky: Mapped[str] = mapped_column(String(10), index=True)                         # 2026-10 / 2026-Q4 / 2026
    # Phòng được CHỤP LẠI vào lúc chấm, không đọc sống từ hồ sơ nhân sự: người chuyển phòng giữa năm
    # thì bản đánh giá cũ vẫn phải thuộc về phòng đã chấm nó, nếu không lịch sử tự viết lại.
    department: Mapped[str] = mapped_column(String(20), default="", index=True)

    # ── Ba ô MÁY ĐIỀN. `*_diem` để NULL nghĩa là "chưa có số", khác hẳn 0 điểm ──
    a1_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a1_nguon: Mapped[str] = mapped_column(String(200), default="")
    a2_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a2_nguon: Mapped[str] = mapped_column(String(200), default="")
    a3_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a3_nguon: Mapped[str] = mapped_column(String(200), default="")

    # ── Ba ô TRƯỞNG PHÒNG CHẤM ──
    b1_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    b1_ly_do: Mapped[str] = mapped_column(Text, default="")
    b2_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    b2_ly_do: Mapped[str] = mapped_column(Text, default="")
    b3_diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    b3_ly_do: Mapped[str] = mapped_column(Text, default="")

    diem_tong: Mapped[float | None] = mapped_column(Float, nullable=True)
    xep_hang: Mapped[str] = mapped_column(String(20), default="")
    nhan_xet: Mapped[str] = mapped_column(Text, default="")        # ô nhận xét của kỳ quý / năm
    viec_phai_sua: Mapped[str] = mapped_column(Text, default="")   # bắt buộc khi xếp hạng ở hai mức dưới
    de_xuat: Mapped[str] = mapped_column(Text, default="")         # trưởng phòng ghi khi xếp hạng Xuất sắc
    # Kỳ quý/năm tổng hợp từ các kỳ con. Thiếu tháng nào thì NÓI RA tháng ấy, không lấy hai tháng chia
    # ba rồi im lặng — một trung bình thiếu nguồn trông y hệt một trung bình đủ nguồn.
    thieu_ky_con: Mapped[str] = mapped_column(String(200), default="")

    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap", index=True)
    nguoi_cham: Mapped[str] = mapped_column(String(50), default="")
    vai_nguoi_cham: Mapped[str] = mapped_column(String(20), default="")
    cham_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    gui_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ── 5.9.2 ─────────────────────────────────────────────────────────────────────────────────────────
# Chủ tịch chốt 08/10/2026: "đề nghị mua đi qua TGĐ / Chủ tịch và Kế toán chi".
#
# HAI CHỮ KÝ, KHÔNG PHẢI MỘT. Người duyệt (TGĐ/Chủ tịch) nói ĐƯỢC MUA; Kế toán nói ĐÃ CHI. Gộp hai
# việc vào một trạng thái thì ngày Kế toán chưa chi được vì thiếu tiền, đề nghị vẫn hiện là "xong" —
# và người đề nghị ngồi đợi một món hàng không ai mua.
DNM_TRANG_THAI = {
    "nhap":      "Nháp – người đề nghị đang soạn",
    "cho_duyet": "Chờ TGĐ / Chủ tịch duyệt",
    "da_duyet":  "Đã duyệt – chờ Kế toán chi",
    "tu_choi":   "Không duyệt",
    "da_chi":    "Kế toán đã chi",
    "huy":       "Người đề nghị thu lại",
}
DNM_MUC_DO = {"thuong": "Bình thường", "gap": "Gấp", "khan": "Khẩn – dừng việc nếu không có"}


class DeNghiMua(Base):
    """Đề nghị mua sắm: phòng đề nghị → TGĐ/Chủ tịch duyệt → Kế toán chi."""
    __tablename__ = "de_nghi_mua"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)       # DNM2026-0001
    department: Mapped[str] = mapped_column(String(20), default="", index=True)
    nguoi_de_nghi: Mapped[str] = mapped_column(String(50), default="")
    noi_dung: Mapped[str] = mapped_column(String(300), default="")
    so_luong: Mapped[float] = mapped_column(Float, default=1)
    don_vi: Mapped[str] = mapped_column(String(20), default="cái")
    # Giá ƯỚC TÍNH, để NULL được: người đề nghị chưa hỏi giá thì cứ gửi, đừng bắt họ bịa một con số
    # rồi con số bịa ấy đi thẳng vào bảng tổng hợp chi phí dự kiến của Kế toán.
    uoc_tinh: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ly_do: Mapped[str] = mapped_column(Text, default="")
    muc_do: Mapped[str] = mapped_column(String(10), default="thuong")
    can_truoc_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap", index=True)
    # Chữ ký 1 – duyệt
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_vai: Mapped[str] = mapped_column(String(20), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duyet_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Chữ ký 2 – chi
    chi_boi: Mapped[str] = mapped_column(String(50), default="")
    chi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    so_tien_chi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chung_tu_ref: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ── 5.9.3 ─────────────────────────────────────────────────────────────────────────────────────────
# Chủ tịch chốt 08/10/2026: "cấp phát tài sản do HCNS làm".
#
# BẢNG NÀY KHÔNG PHẢI SỔ TÀI SẢN THỨ HAI. Sổ tài sản là `fixed_assets` (thẻ TSCĐ, có nguyên giá và
# khấu hao); bảng này chỉ ghi MỘT MÓN ĐANG Ở TAY AI. Nối bằng `asset_id`, và `asset_id` để NULL được
# vì phần lớn thứ HCNS cấp — điện thoại, SIM, chìa khoá, đồng phục, thẻ ra vào — không đủ nguyên giá
# để thành một thẻ TSCĐ. Bắt mọi món phải có thẻ TSCĐ trước khi cấp phát thì HCNS sẽ ghi ra giấy, và
# cái sổ máy này rỗng trong khi đồ vẫn đi.
CP_TRANG_THAI = {
    "dang_giu": "Đang giữ",
    "da_tra":   "Đã trả",
    "mat_hong": "Mất / hỏng",
}


class CapPhatTaiSan(Base):
    """Biên bản cấp phát: HCNS lập, người nhận ký nhận, trả thì ghi ngày trả và tình trạng."""
    __tablename__ = "cap_phat_tai_san"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)       # CP2026-0001
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("fixed_assets.id"), nullable=True)
    ten_tai_san: Mapped[str] = mapped_column(String(200), default="")
    so_luong: Mapped[float] = mapped_column(Float, default=1)
    don_vi: Mapped[str] = mapped_column(String(20), default="cái")
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    department: Mapped[str] = mapped_column(String(20), default="", index=True)
    cap_ngay: Mapped[date] = mapped_column(Date, index=True)
    muc_dich: Mapped[str] = mapped_column(String(300), default="")
    tinh_trang_khi_cap: Mapped[str] = mapped_column(String(100), default="")
    trang_thai: Mapped[str] = mapped_column(String(20), default="dang_giu", index=True)
    tra_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    tinh_trang_khi_tra: Mapped[str] = mapped_column(String(200), default="")
    nguoi_lap: Mapped[str] = mapped_column(String(50), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
