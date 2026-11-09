# -*- coding: utf-8 -*-
"""Phiếu đề xuất chi của ĐỘI XE — bảy bước, có người lập khác người duyệt, có phiên bản.

Bản vẽ v3.3 anh Tuấn gửi 09/11/2026, mục §3. Trước bản này VTOS có cửa `POST /fleet/de-xuat-chi`
nhưng nó **chỉ ghi một dòng `fleet_external_txns`** nguồn `de_xuat_vietrip` — một dòng ĐỐI CHIẾU,
không phải một phiếu có tuyến duyệt. Chính giao diện đang nói ra điều đó: *"các dòng nguồn Đề xuất
chi trên phần mềm Vietrip là bản trích để đối chiếu và chạy thử, không phải sổ chi phí đã duyệt của
VTOS"*. Nên GĐ đội xe lập xong một "đề xuất" mà không ai được giao kiểm, không ai được giao duyệt,
và không có chỗ nào ghi vì sao nó bị trả lại.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA ĐIỀU BẢNG NÀY CỐ Ý LÀM, VÀ VÌ SAO
═══════════════════════════════════════════════════════════════════════════════════════════════

**1 · KHÔNG CÓ CỘT SỐ TÀI KHOẢN VÀ KHÔNG CÓ CỘT NGÂN HÀNG.**

v3.3 §2 và §7 ghi đích danh: *"GĐ đội xe không nhập hoặc thay tài khoản ngân hàng tùy ý trong màn
đề nghị"*, và ma trận quyền ghi *"Đổi thông tin ngân hàng — không theo vai GĐ"*. Cửa cũ có BA ô gõ
tay: người thụ hưởng · số tài khoản · ngân hàng.

Cách chữa không phải là ẩn ba ô ấy trên giao diện. Ẩn một ô thì cột vẫn còn, và cột còn thì ngày
nào đó có một cửa khác ghi vào nó — hoặc một bản sửa giao diện bỏ mất chỗ ẩn. Nên **cột không tồn
tại**: bên nhận là `supplier_id` trỏ vào danh mục nhà cung cấp, và số tài khoản được đọc từ
`suppliers` lúc Kế toán thanh toán. Đổi tài khoản của một nhà cung cấp đã có cửa riêng có nhật ký
(`supplier_bank_changes`) — không ai phải viết lại cửa ấy, và GĐ không đi qua nó.

`ben_nhan_de_nghi` là chỗ cho trường hợp thật: bên nhận CHƯA có trong danh mục. GĐ ghi tên vào đó
và phiếu **ở lại nháp** — không gửi được. Thiếu cửa này thì người lập bị chặn cứng và sẽ đi tìm
đường khác (nhờ người có quyền gõ hộ, hoặc lập phiếu dưới tên một nhà cung cấp không đúng), tức là
hàng rào đẩy việc ra khỏi hệ thống chứ không kiểm soát được việc.

**2 · MÃ KHOẢN GỐC LÀ KHÓA, KHÔNG PHẢI MỘT Ô CHỮ.**

WF06: *"báo cáo đã có khoản chi rồi lập đề nghị → cùng mã khoản gốc, chi phí không bị cộng lặp"*.
`trip_cost_id` là khóa thật trỏ vào `fleet_trip_costs`. `ma_khoan_goc` vẫn giữ, vì khoản gốc có thể
nằm ngoài VTOS (phiếu Vietrip, số chứng từ Kế toán) — nhưng nó là chuỗi ĐỂ ĐỐI CHIẾU, còn thứ phép
tính tin là khóa.

Vì sao cần cả hai, viết ra để sau không ai bỏ một cái: chỉ có chuỗi thì không chặn được cộng lặp
(chuỗi gõ sai một dấu là hai khoản khác nhau); chỉ có khóa thì không nối được với khoản chi phát
sinh ngoài VTOS, và những khoản ấy là phần lớn.

**3 · LƯU PHIÊN BẢN TRƯỚC, KHÔNG CHỈ LƯU TRẠNG THÁI SAU.**

§5 và AU04 đòi lưu nội dung trước/sau của từng lần sửa. `FleetDeXuatLog` giữ bản chụp JSON của
phiếu TRƯỚC mỗi lần chuyển bước, kèm lý do. Chỉ ghi "đã trả bổ sung" mà không ghi phiếu lúc ấy ghi
gì thì lúc tranh luận không ai dựng lại được, và tranh luận về một khoản chi là chuyện sẽ xảy ra.

═══════════════════════════════════════════════════════════════════════════════════════════════
BẢY BƯỚC CỦA §3 ↔ CHÍN TRẠNG THÁI Ở ĐÂY
═══════════════════════════════════════════════════════════════════════════════════════════════

§3 đếm BẢY bước, trong đó hai bước cuối mỗi bước có hai kết cục:

    1 Nháp            → nhap
    2 Chờ kiểm tra    → cho_kiem_tra
    3 Chờ duyệt       → cho_duyet
    4 Trả bổ sung     → tra_bo_sung
    5 Đã duyệt chờ TT → da_duyet
    6 Đã TT / một phần→ da_tt            | da_tt_mot_phan
    7 Đã đối soát/hủy → da_doi_soat      | huy

Chín trạng thái chứ không bảy, vì "một phần" và "hủy" phải PHÂN BIỆT ĐƯỢC khi đọc sổ: một phiếu đã
chi 60% và một phiếu đã chi đủ đều "ở bước 6", nhưng chỉ một trong hai còn tiền phải trả. Gộp lại
thành một trạng thái là bắt người đọc mở từng phiếu ra tính.
"""
from datetime import date, datetime

from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# ── Bảy bước của §3, theo thứ tự đọc. Giao diện in `TRANG_THAI[x]`, không tự gõ lại nhãn tiếng Việt:
#    gõ lại là dựng chỗ cho hai màn hình gọi cùng một trạng thái bằng hai cái tên.
TRANG_THAI = {
    "nhap":           "Nháp",
    "cho_kiem_tra":   "Chờ kiểm tra",
    "cho_duyet":      "Chờ duyệt",
    "tra_bo_sung":    "Trả bổ sung",
    "da_duyet":       "Đã duyệt — chờ thanh toán",
    "da_tt_mot_phan": "Đã thanh toán một phần",
    "da_tt":          "Đã thanh toán",
    "da_doi_soat":    "Đã đối soát",
    "huy":            "Đã hủy",
}

# Trạng thái ĐÃ KHÉP: không chuyển đi đâu nữa, và không sửa nội dung được.
KHEP = ("da_doi_soat", "huy")

# Trạng thái mà phiếu còn nằm trong tay NGƯỜI LẬP — chỉ hai cái này cho sửa nội dung.
CON_SUA_DUOC = ("nhap", "tra_bo_sung")

# ── Loại đề nghị, đúng ba lựa chọn của bản vẽ (`type`: payment / advance / reimburse).
LOAI = {
    "thanh_toan": "Thanh toán",
    "tam_ung":    "Tạm ứng",
    "hoan_ung":   "Hoàn ứng / hoàn chi",
}

# ── Nhóm khoản, đúng bảy nhóm của bản vẽ. KHÔNG dùng lại `NHOM_CHI_PHI_KY` của chi phí kỳ: hai
# danh sách trả lời hai câu khác nhau. `NHOM_CHI_PHI_KY` phân loại một khoản ĐÃ CHI vào giá vốn;
# danh sách này phân loại một khoản ĐANG ĐỀ NGHỊ để định tuyến duyệt. Một đề nghị "Khác · cần phân
# loại" là việc thật — người lập chưa biết nó thuộc nhóm nào và người kiểm tra sẽ xếp — còn sổ giá
# vốn thì không được có nhóm "chưa biết".
#
# Cột thứ hai là PHẠM VI MẶC ĐỊNH, dùng để gợi ý, không để chốt: người lập vẫn chọn phạm vi.
NHOM_KHOAN = {
    "bao_duong":   ("Bảo dưỡng / sửa chữa", "xe"),
    "nhien_lieu":  ("Nhiên liệu", "xe"),
    "cau_duong":   ("Phí cầu đường / gửi xe", "xe"),
    "cong_tac_phi": ("Công tác phí tài xế", "xe"),
    "chi_phi_ky_xe": ("Chi phí kỳ của xe", "xe"),
    "chung_doi":   ("Chi phí chung đội xe", "doi"),
    "khac":        ("Khác · cần phân loại", "xe"),
}

# ── Căn cứ số tiền và thuế/phí. Bản vẽ ghi rõ ở §2: "không tự cộng VAT".
#
# Vì sao bắt buộc chọn thay vì để trống: một con số 2.500.000 không nói được nó đã gồm thuế chưa,
# mà Kế toán phải biết điều đó để hạch toán. Để trống thì người kiểm tra phải gọi điện hỏi lại, và
# chuyện gọi điện hỏi lại là chuyện không có trong nhật ký.
CAN_CU_THUE = {
    "da_gom":   "Đã gồm thuế / phí theo chứng từ",
    "khong_co": "Không phát sinh thuế / phí",
    "tam_tinh": "Tạm tính · chờ kế toán kiểm tra",
}


class FleetDeXuat(Base):
    """Một phiếu đề xuất chi của đội xe."""
    __tablename__ = "fleet_de_xuat"
    __table_args__ = (
        # Tên KHÔNG được là `ix_fleet_de_xuat_trang_thai`: SQLAlchemy tự đặt đúng tên ấy cho chỉ
        # mục của cột `trang_thai` nếu cột khai `index=True`, và hai chỉ mục cùng tên thì
        # `create_all` nổ ngay — bắt được lúc chạy thử 09/11/2026 chứ không phải lúc deploy.
        # Nên cột không khai `index=True`; chỉ mục ghép này đã phủ luôn phần tra theo trạng thái.
        Index("ix_fleet_de_xuat_tt_ngay", "trang_thai", "ngay_can"),
        Index("ix_fleet_de_xuat_nguoi_lap", "nguoi_lap", "trang_thai"),
        # Mã khoản gốc chỉ được một phiếu CÒN SỐNG dùng — nhưng không khai unique ở đây, vì phiếu bị
        # hủy rồi lập lại cùng khoản gốc là việc đúng. Luật ấy nằm ở `fleet_de_xuat.kiem_trung`,
        # nơi đọc được trạng thái; một chỉ mục unique thì không đọc được.
        Index("ix_fleet_de_xuat_khoan_goc", "ma_khoan_goc"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String(30), unique=True, index=True)   # DX-202611-0001

    # ── Phạm vi và đối tượng
    pham_vi: Mapped[str] = mapped_column(String(10), default="xe")               # xe / doi
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)

    # ── Nội dung đề nghị
    loai: Mapped[str] = mapped_column(String(20), default="thanh_toan")          # khóa trong LOAI
    nhom: Mapped[str] = mapped_column(String(20), default="")                    # khóa trong NHOM_KHOAN
    noi_dung: Mapped[str] = mapped_column(Text, default="")

    # ── Bên nhận. Xem mục 1 ở đầu tệp: KHÔNG có cột số tài khoản, KHÔNG có cột ngân hàng.
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    ben_nhan_de_nghi: Mapped[str] = mapped_column(String(200), default="")

    # ── Tiền
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ngay_can: Mapped[date | None] = mapped_column(Date, nullable=True)
    can_cu_thue: Mapped[str] = mapped_column(String(20), default="")             # khóa trong CAN_CU_THUE
    so_tien_da_tt: Mapped[float | None] = mapped_column(TIEN, nullable=True)

    # ── Chứng từ. Tệp thật nằm ở kho `attachments` với `doi_tuong="de_xuat_chi_xe"`; ở đây chỉ giữ
    # số chứng từ gốc và lời hẹn bổ sung.
    so_chung_tu: Mapped[str] = mapped_column(String(200), default="")
    hen_bo_sung: Mapped[bool] = mapped_column(Boolean, default=False)
    ly_do_bo_sung: Mapped[str] = mapped_column(String(300), default="")

    # ── Chống ghi nhận hai lần (WF06). Xem mục 2 ở đầu tệp.
    trip_cost_id: Mapped[int | None] = mapped_column(ForeignKey("fleet_trip_costs.id"), nullable=True)
    ma_khoan_goc: Mapped[str] = mapped_column(String(60), default="")

    ghi_chu: Mapped[str] = mapped_column(Text, default="")

    # ── Nháp bốn bước (§5, B4). `buoc_nhap` là bước người lập đang dừng, 0..3 — để mở lại đúng chỗ
    # thay vì bắt nhập lại từ đầu. Nó KHÔNG phải trạng thái phiếu: một phiếu nháp ở bước 3 vẫn là nháp.
    buoc_nhap: Mapped[int] = mapped_column(Integer, default=0)

    # ── Tuyến xử lý
    trang_thai: Mapped[str] = mapped_column(String(20), default="nhap")
    nguoi_lap: Mapped[str] = mapped_column(String(50), default="")
    nguoi_kiem_tra: Mapped[str] = mapped_column(String(50), default="")
    nguoi_duyet: Mapped[str] = mapped_column(String(50), default="")
    nguoi_thanh_toan: Mapped[str] = mapped_column(String(50), default="")
    nguoi_doi_soat: Mapped[str] = mapped_column(String(50), default="")

    # Phiên bản cho `ghi_mot_lan.kiem_phien_ban`: người sau biết mình đang đè lên người trước.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1)

    ngay_lap: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FleetDeXuatLog(Base):
    """Nhật ký chuyển bước của một phiếu — có LÝ DO và có bản chụp phiếu TRƯỚC khi chuyển.

    Vì sao không dùng `R.audit` chung là đủ: nhật ký chung trả lời "ai làm gì lúc nào" cho cả hệ
    thống. Bảng này trả lời một câu hẹp hơn mà màn hình phải in ra ngay dưới phiếu — "phiếu này đã
    đi qua những tay nào, bị trả lại vì gì, và lúc bị trả lại nó ghi bao nhiêu tiền". Đọc câu ấy từ
    nhật ký chung thì phải lọc theo chuỗi mô tả, và lọc theo chuỗi mô tả là thứ hỏng lần đầu có ai
    sửa câu mô tả.
    """
    __tablename__ = "fleet_de_xuat_log"
    __table_args__ = (Index("ix_fleet_de_xuat_log_phieu", "de_xuat_id", "luc"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    de_xuat_id: Mapped[int] = mapped_column(ForeignKey("fleet_de_xuat.id"), index=True)
    hanh_dong: Mapped[str] = mapped_column(String(20))              # gui / kiem_tra / duyet / tra / tt / doi_soat / huy / sua
    tu_trang_thai: Mapped[str] = mapped_column(String(20), default="")
    den_trang_thai: Mapped[str] = mapped_column(String(20), default="")
    ly_do: Mapped[str] = mapped_column(Text, default="")
    phien_ban_truoc: Mapped[int] = mapped_column(Integer, default=0)
    # Bản chụp JSON của phiếu TRƯỚC khi chuyển. Text chứ không JSON column: SQLite và Postgres cùng
    # đọc được Text, và bảng này chỉ để ĐỌC LẠI bằng mắt, không để truy vấn theo trường bên trong.
    noi_dung_truoc: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
    vai: Mapped[str] = mapped_column(String(30), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
