"""VPM-11 – SỔ NGHĨA VỤ THANH TOÁN. Mỗi nghĩa vụ MỘT DÒNG, MỘT MÃ GỐC.

────────────────────────────────────────────────────────────────────────────────
VẤN ĐỀ BẢNG NÀY SINH RA ĐỂ GIẢI
────────────────────────────────────────────────────────────────────────────────

Đề xuất chỉnh sửa giao diện v1.1 ngày 11/9/2026, mục IV.4, viết nguyên văn: "Một nghĩa vụ có mã gốc
liên kết hợp đồng, đề nghị chi, hóa đơn và thanh toán; chỉ tính phần còn lại một lần. Không cộng cả
công nợ và đề nghị chi của cùng nghĩa vụ." Mã nghiệm thu CF-03 kiểm đúng câu ấy.

Hôm nay MỘT khoản phải trả nhà cung cấp nằm rải ở ba chỗ: đơn đặt dịch vụ (`service_orders`), đề nghị
chi (`payment_requests`), và sổ công nợ dựng lại từ hai bảng trên. Bảng dòng tiền bốn mốc mà cộng
thẳng từ ba nguồn ấy thì một khoản nợ 100 triệu hiện lên thành 200–300 triệu, và nó sai theo hướng
PHÓNG ĐẠI nhu cầu tiền – lãnh đạo thấy thiếu tiền ở chỗ không thiếu, rồi đi vay một khoản không cần.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO LÀ MỘT BẢNG RIÊNG, KHÔNG PHẢI MỘT CỘT `ma_goc` GẮN VÀO BA BẢNG CŨ
────────────────────────────────────────────────────────────────────────────────

Gắn thêm cột mã vào ba bảng thì vẫn còn ba dòng mang cùng một mã, do ba phòng nhập, ở ba thời điểm,
và KHÔNG CÓ CHỖ NÀO giữ câu trả lời cho câu hỏi duy nhất mà bảng dòng tiền cần: "nghĩa vụ này còn
phải trả bao nhiêu?". Phải có một dòng đứng ra làm chủ con số ấy. Ba bảng kia vẫn là chứng từ gốc,
không đổi, không bị thay thế – sổ này là LỚP ĐỌC nằm trên chúng.

────────────────────────────────────────────────────────────────────────────────
HAI NGÀY, VÀ VÌ SAO KHÔNG GỘP LÀM MỘT
────────────────────────────────────────────────────────────────────────────────

`ngay_cam_ket` là ngày đã hứa với bên kia. `ngay_du_kien_tra` là ngày kế toán định trả thật. Đề xuất
mục III.3 đòi hai tab dùng hai cơ sở ngày khác nhau – gộp hai ngày làm một thì không bao giờ dựng
được hai tab, và tệ hơn: dời kế hoạch trả sẽ lặng lẽ xoá dấu vết đã quá hạn theo cam kết, đúng thứ
mục IV.4 cấm ("Thay lịch trả không tự xóa quá hạn theo cam kết").

Cả hai ngày đều CHO PHÉP RỖNG, và rỗng KHÔNG bị bỏ qua: dòng rỗng ngày đi vào rổ "Chưa đủ dữ liệu dự
báo" (CF-05). Bỏ im lặng một khoản không có ngày là cách chắc chắn nhất để bảng dòng tiền trông đẹp
hơn sự thật.

────────────────────────────────────────────────────────────────────────────────
K2: CỘT TIỀN RỖNG KHÁC 0
────────────────────────────────────────────────────────────────────────────────

`tong_nghia_vu` và `da_tra` đều `nullable`, không `default`. Rỗng nghĩa là CHƯA AI NHẬP, không phải
"không nợ đồng nào". Mọi chỗ ĐỌC hai cột này phải bọc `or 0`.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Hướng của nghĩa vụ. Hai giá trị, không hơn: tiền vào và tiền ra. Khoản "ghi nhớ" (thu hộ khách, ký
# quỹ) KHÔNG phải hướng thứ ba – chúng là `chi`/`thu` nhưng mang cờ `ghi_nho` ở dưới, vì bản chất
# chúng có thật, chỉ là không được cộng vào tiền khả dụng.
HUONG = {"thu": "Tiền dự kiến thu", "chi": "Tiền phải thanh toán"}

# Nhóm nghĩa vụ – KHỚP ĐÚNG các dòng của bảng dòng tiền ở mục III bảng 4 của đề xuất. Đổi danh sách
# này là đổi các dòng trên màn hình lãnh đạo, nên đừng thêm nhóm mới mà không sửa cả bảng ấy.
NHOM = {
    # ----- tiền vào -----
    "thu_khach":        ("thu", "Thu khách / booking / hợp đồng"),
    "thu_cong_no_khac": ("thu", "Thu công nợ khác"),
    "giai_ngan_vay":    ("thu", "Giải ngân vay đã ký khế ước"),
    # ----- tiền ra -----
    "tra_ncc":          ("chi", "Trả nhà cung cấp"),
    "hoan_khach":       ("chi", "Hoàn / trả khách hàng"),
    "hoa_hong":         ("chi", "Hoa hồng đại lý và cộng tác viên"),
    "tra_goc_vay":      ("chi", "Trả gốc vay ngân hàng"),
    "lai_phi_vay":      ("chi", "Lãi và phí ngân hàng"),
    "luong_bh":         ("chi", "Lương, bảo hiểm và liên quan"),
    "thue":             ("chi", "Thuế và nghĩa vụ khác"),
    "van_hanh_khac":    ("chi", "Vận hành và phải trả khác"),
    # ----- ghi nhớ: có thật, nhưng KHÔNG cộng vào tiền khả dụng (mục III.1) -----
    "thu_ho_khach":     ("thu", "Ghi nhớ — Tiền thu hộ khách"),
    "ky_quy_lu_hanh":   ("chi", "Ghi nhớ — Ký quỹ giấy phép lữ hành"),
}

GHI_NHO = ("thu_ho_khach", "ky_quy_lu_hanh")

# ══════════════════════════════════════════════════════════════════════════════
# AI ĐƯỢC XEM NHÓM NÀO — chốt của Chủ tịch ngày 11/9/2026
# ══════════════════════════════════════════════════════════════════════════════
#
# "Chủ tịch xem TẤT CẢ dòng tài chính; Tổng giám đốc CHỈ xem tài chính hoạt động kinh doanh TOUR và
# XE." Kế toán và Ban Kiểm soát giữ toàn cảnh. Hai Phó Tổng giám đốc không thấy khối này (họ đã bị
# chặn từ danh sách vai trò của cửa API, xem app/api/v1/finance.py).
#
# VÌ SAO LỌC Ở ĐÂY CHỨ KHÔNG Ở MÀN HÌNH: giấu một dòng trên giao diện thì gọi thẳng đường dẫn chi
# tiết hoặc bấm nút xuất Excel là thấy lại. Lọc phải nằm ở chỗ CỘNG, để mọi cửa đi qua nó — bảng
# tổng hợp, danh sách chi tiết, và tệp xuất ra đều cùng một phép lọc.
#
# Danh sách ghi theo lối LOẠI TRỪ, có chủ ý: thêm một nhóm nghĩa vụ mới mà quên khai thì nhóm ấy
# MẶC ĐỊNH HIỆN cho Tổng giám đốc. Lối ngược lại (danh sách cho phép) thì nhóm mới mặc định bị giấu
# — im lặng và không ai biết. Giữa "lộ một nhóm mới và có người kêu" với "giấu một nhóm mới và không
# ai biết", chọn cái thứ nhất, vì cái thứ hai không bao giờ tự lộ ra.
NHOM_NGOAI_TAM_TGD = {
    "giai_ngan_vay":   "khoản vay là việc của Hội đồng quản trị, không phải tài chính hoạt động tour–xe",
    "tra_goc_vay":     "trả gốc vay – cùng lý do với giải ngân",
    "lai_phi_vay":     "lãi và phí ngân hàng – cùng lý do",
    "thue":            "nghĩa vụ thuế của pháp nhân, không gắn hoạt động tour–xe",
    "ky_quy_lu_hanh":  "ký quỹ giấy phép lữ hành – tiền của pháp nhân bị giữ, không phải dòng tour–xe",
    # Chốt 11/9 cho Tổng giám đốc phần "lương–bảo hiểm BỘ PHẬN TOUR VÀ ĐỘI XE". Bảng nghĩa vụ hôm nay
    # KHÔNG CÓ dấu bộ phận nào để tách được phần ấy ra khỏi lương toàn công ty. Cho hiện cả nhóm là
    # để lộ quỹ lương của mọi phòng; cho hiện "phần tour–xe" bằng một phép đoán là bịa ra một con số.
    # Nên tạm để ngoài tầm, GHI RÕ LÝ DO, và mở lại khi có cột bộ phận. Đây là việc còn thiếu, không
    # phải quyết định về quyền.
    "luong_bh":        "chưa có dấu bộ phận để tách phần tour và đội xe khỏi lương toàn công ty – "
                       "mở lại khi bảng lương có cột bộ phận",
}


def nhom_duoc_xem(vai_tro: str) -> set[str]:
    """Nhóm nghĩa vụ mà một vai trò được cộng và được đọc chi tiết.

    Vai trò lạ (không nằm trong danh sách vai trò của cửa API) rơi vào nhánh Tổng giám đốc – hẹp hơn,
    không rộng hơn. Đoán rộng cho một vai trò chưa biết là cách để một lần khai quyền cẩu thả biến
    thành một lần lộ sổ.
    """
    if vai_tro in ("chutich", "ketoan", "bks", "cntt", "robot_ks"):
        return set(NHOM)
    return set(NHOM) - set(NHOM_NGOAI_TAM_TGD)


TRANG_THAI = {
    "du_kien":   "Dự kiến",
    "da_duyet":  "Đã duyệt, chờ chuyển",
    "qua_han":   "Quá hạn",
    "da_tra":    "Đã tất toán",
    "tranh_chap": "Đang tranh chấp",
    "huy":       "Đã huỷ",
}

# Trạng thái KHÔNG còn là nhu cầu tiền nữa. Tách ra thành hằng số vì ba chỗ dùng, và ba chỗ mà chép
# tay danh sách này thì sớm muộn lệch nhau.
TRANG_THAI_DONG = ("da_tra", "huy")


class NghiaVuThanhToan(Base):
    """Một nghĩa vụ = một dòng. Mã gốc là danh tính của nó, không phải id."""

    __tablename__ = "nghia_vu_thanh_toan"
    __table_args__ = (
        # Khoá chống trùng của phép đồng bộ: một chứng từ gốc sinh ra ĐÚNG MỘT dòng, chạy đồng bộ
        # mười lần vẫn thế. Không có ràng buộc này thì mỗi lần chạy lại là một lần nhân đôi sổ.
        Index("ux_nghia_vu_nguon", "nguon_bang", "nguon_id", unique=True),
        Index("ix_nghia_vu_ngay", "ngay_cam_ket", "nhom"),
        Index("ix_nghia_vu_pham_vi", "company_id", "huong"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # ---------- danh tính ----------
    ma_goc: Mapped[str] = mapped_column(String(40), unique=True, index=True)   # NV-2609-0001
    huong: Mapped[str] = mapped_column(String(4))                              # thu / chi
    nhom: Mapped[str] = mapped_column(String(24), index=True)                  # xem NHOM
    ghi_nho: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)

    # ---------- phạm vi ----------
    # Pháp nhân CHỊU nghĩa vụ. Rỗng là CHƯA XÁC ĐỊNH – KHÔNG mặc định về công ty mẹ, theo đúng ghi chú
    # đã có ở app/services/company_scope.py. Tiền của pháp nhân này không mặc định dùng được cho pháp
    # nhân khác, nên một nghĩa vụ chưa biết của ai thì không được cộng vào bảng của ai cả.
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    # Đơn vị trực thuộc phụ trách – TÁCH khỏi pháp nhân chịu trách nhiệm (đề xuất mục VI.2). Chi nhánh
    # Cần Thơ phụ trách một khoản của công ty mẹ là chuyện bình thường; gộp hai cột làm một thì mất
    # một trong hai câu trả lời.
    don_vi_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    doi_tuong: Mapped[str] = mapped_column(String(200), default="")            # NCC / khách / ngân hàng / cơ quan thuế
    noi_dung: Mapped[str] = mapped_column(String(300), default="")
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)

    # ---------- tiền (K2: rỗng ≠ 0) ----------
    tong_nghia_vu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_tra: Mapped[float | None] = mapped_column(TIEN, nullable=True)

    # Ngoại tệ: giữ NGUYÊN TỆ, kèm tỷ giá và ngày quy đổi (đề xuất mục IV.4). Quy đổi một lần rồi vứt
    # tỷ giá đi là mất khả năng giải thích vì sao con số hôm nay khác con số tuần trước.
    loai_tien: Mapped[str] = mapped_column(String(3), default="VND", server_default="VND")
    ty_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ngay_quy_doi: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ---------- hai ngày, xem ghi chú đầu tệp ----------
    ngay_cam_ket: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    ngay_du_kien_tra: Mapped[date | None] = mapped_column(Date, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(16), default="du_kien", index=True)

    # ---------- chứng từ nguồn: bấm vào số tiền phải ra được tờ giấy ----------
    nguon_bang: Mapped[str] = mapped_column(String(40), index=True)
    nguon_id: Mapped[int] = mapped_column(Integer, index=True)
    nguon_ma: Mapped[str] = mapped_column(String(50), default="")              # số hiệu chứng từ để người đọc

    # Cờ do phép đồng bộ đặt: dòng này NGHI trùng với một dòng khác (cùng tour, cùng đối tượng, cùng
    # số tiền, khác nguồn). KHÔNG tự gộp – chỉ nêu ra cho người quyết định. Tự gộp là tự đặt một quy
    # tắc kế toán chưa ai ký.
    nghi_trung_voi: Mapped[str] = mapped_column(String(40), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")

    # ---------- khoá ghi đè (VPM-8) ----------
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def con_lai(self) -> float:
        """Phần CÒN PHẢI trả/thu. Đây là con số duy nhất bảng dòng tiền được cộng.

        Bọc `or 0` cả hai vế vì cả hai cột đều được phép rỗng (K2). Không cho âm: trả thừa là một
        khoản PHẢI TRẢ LẠI, thuộc nhóm khác, không phải một nghĩa vụ âm làm nhẹ bớt cột tổng.
        """
        return max(0.0, float(self.tong_nghia_vu or 0) - float(self.da_tra or 0))
