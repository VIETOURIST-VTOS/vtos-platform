# -*- coding: utf-8 -*-
"""PQ-1 · Bảng LUỒNG CÔNG VIỆC – khai ra ai được ĐẨY VIỆC sang bước sau.

VÌ SAO CẦN TỆP NÀY

Ma trận quyền trong access.py trả lời được câu "ai được NHÌN màn hình nào". Nó KHÔNG trả lời được
câu "ai được đẩy việc sang bước sau" – mà đó mới là chuỗi chỉ huy thật của công ty. Chuỗi ấy có
tồn tại và rất chặt, nhưng đang nằm dưới dạng CHUỖI KÝ TỰ VIẾT CỨNG rải trong sáu tệp dịch vụ:

    if u.role not in ("chutich", "tgd"): ...
    if u.id != t.operator_id: ...

Ba hệ quả đo được của việc ấy:

  1. Bảng phân quyền Chủ tịch đã duyệt không mô tả chuỗi này. Với công ty đại chúng, đó là chỗ
     kiểm toán hỏi đầu tiên và hiện không có trang nào trả lời được.
  2. Bộ kiểm quyền của robot Kiểm soát chỉ đọc được khai báo ở chữ ký hàm. Đo ngày 10/9/2026:
     622 đường dẫn API – 518 khai ở chữ ký, 10 khai ở decorator, 38 ĐƯỜNG DẪN GHI không khai ở
     chỗ nào máy đọc được. 38 chỗ ấy không hở quyền, nhưng luật của chúng vô hình.
  3. Muốn đổi một bước – ví dụ cho Phó TGĐ đoàn duyệt thay TGĐ – phải đi sửa mã, và không ai
     ngoài người viết mã biết đã đổi gì.

RANH GIỚI CỦA BẢN NÀY

Tệp này CHÉP LẠI đúng luật đang chạy ngày 10/9/2026, KHÔNG sửa luật. Chỗ nào bảng và mã lệch
nhau thì MÃ ĐÚNG và bảng sai – có phép thử canh đúng điều đó
(tests/test_luong_viec.py::test_bang_khop_voi_luat_dang_chay).

Sửa luật là việc riêng, làm sau, và phải có người ký. Trộn hai việc vào một lần thay đổi là cách
chắc chắn nhất để không ai nhìn ra luật vừa bị đổi.

Việc thay chuỗi viết cứng trong hàm dịch vụ bằng lời gọi tra bảng này là VPM-3, thuộc làn Viết
phần mềm – không phải việc của làn Phân quyền.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------------------------
# Cách một bước được canh
# ---------------------------------------------------------------------------------------------
# Bốn kiểu, vì trong mã thật đang có đủ bốn – không gộp lại cho gọn, vì gộp là sửa luật:
#
#   chi_vai_tro     chỉ xét vai trò.                     vd: xác nhận dự toán – chỉ tp_dh
#   chi_chu_so_huu  chỉ xét có phải người phụ trách.     vd: đóng sổ quyết toán – "một cửa"
#   hoac            vai trò HOẶC người phụ trách.        vd: sửa dự toán – nv_dh phụ trách, hoặc tp_dh
#   va              phải đủ cả hai.                      (chưa dùng ở đâu, khai cho đủ)
CHI_VAI_TRO = "chi_vai_tro"
CHI_CHU_SO_HUU = "chi_chu_so_huu"
HOAC = "hoac"
VA = "va"

# Chủ sở hữu hồ sơ được xác định bằng cột nào
NGUOI_DIEU_HANH = "operator_id"   # người điều hành chuyến
SALE_PHU_TRACH = "sales_id"       # sale phụ trách booking
# Chủ hồ sơ quyết toán — Chủ tịch quyết 25/9/2026, câu 4. KHÔNG phải một cột: là kết quả của
# `chu_ho_so.chu_ho_so()`, đọc theo ba bậc (chỉ định riêng của chuyến → mặc định mảng Đoàn →
# người điều hành chuyến). Vẫn đúng MỘT người, nên vẫn canh bằng CHI_CHU_SO_HUU như trước.
CHU_HO_SO = "chu_ho_so"


@dataclass(frozen=True)
class Buoc:
    nghiep_vu: str
    ma: str
    ten: str
    vai_tro: tuple[str, ...] = ()
    chu_so_huu: str = ""
    cach_canh: str = CHI_VAI_TRO
    tu_trang_thai: str = ""
    den_trang_thai: str = ""
    chu_ky: int = 1                 # số chữ ký cần để bước hoàn tất
    vai_tro_dong: str = ""          # tên hàm tính vai trò lúc chạy, khi vai trò không cố định
    nguon: str = ""                 # tệp::hàm – nơi luật đang thực sự nằm
    vi_sao: str = ""

    def ai_duoc(self) -> str:
        """Câu mô tả bằng lời, dùng cho màn hình và cho bản xuất ra ký."""
        if self.vai_tro_dong:
            return f"vai trò tính theo {self.vai_tro_dong}"
        ten_vt = ", ".join(self.vai_tro) if self.vai_tro else "—"
        if self.cach_canh == CHI_CHU_SO_HUU:
            return f"chỉ {_TEN_CHU[self.chu_so_huu]}"
        if self.cach_canh == HOAC:
            return f"{ten_vt} hoặc {_TEN_CHU[self.chu_so_huu]}"
        if self.cach_canh == VA:
            return f"{ten_vt} và đồng thời là {_TEN_CHU[self.chu_so_huu]}"
        return ten_vt


_TEN_CHU = {NGUOI_DIEU_HANH: "người điều hành chuyến", SALE_PHU_TRACH: "sale phụ trách booking",
            CHU_HO_SO: "chủ hồ sơ quyết toán", "": "—"}


# ---------------------------------------------------------------------------------------------
# CHUYẾN TOUR – từ lập dự toán tới CNTT đối chiếu
# ---------------------------------------------------------------------------------------------
_TOUR = (
    Buoc("chuyen_tour", "tao", "Lập dự toán chuyến",
         vai_tro=("nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO,
         den_trang_thai="nhap", nguon="tours.py::create",
         vi_sao="Dự toán là số của Điều hành; phòng khác lập thì không ai chịu trách nhiệm về nó."),

    Buoc("chuyen_tour", "sua", "Sửa dự toán khi còn ở nháp",
         vai_tro=("tp_dh",), chu_so_huu=NGUOI_DIEU_HANH, cach_canh=HOAC,
         tu_trang_thai="nhap", den_trang_thai="nhap", nguon="tours.py::edit",
         vi_sao="Người điều hành chuyến sửa số của mình; Trưởng phòng sửa được của cả phòng."),

    Buoc("chuyen_tour", "trinh", "Trình dự toán",
         vai_tro=("nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="nhap", den_trang_thai="cho_xac_nhan", nguon="tours.py::submit",
         vi_sao="Bàn giao thứ nhất: số rời khỏi tay người lập."),

    Buoc("chuyen_tour", "xac_nhan", "Trưởng phòng Điều hành xác nhận dự toán",
         vai_tro=("tp_dh",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_xac_nhan", den_trang_thai="cho_duyet", nguon="tours.py::confirm",
         vi_sao="Một cửa ra khỏi phòng Điều hành. Không có đường nào khác lên bàn duyệt."),

    Buoc("chuyen_tour", "duyet", "Duyệt dự toán – chuyến ĐẠT biên",
         vai_tro_dong="rules.approver_role", cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_duyet", den_trang_thai="da_duyet", chu_ky=1,
         nguon="tours.py::approve + rules.py::approver_role",
         vi_sao="Điều 4 Văn bản đính chính: tour LẺ do TGĐ duyệt, tour ĐOÀN do Phó TGĐ tour đoàn."),

    Buoc("chuyen_tour", "duyet_duoi_bien", "Duyệt dự toán – chuyến DƯỚI biên, hai chữ ký",
         vai_tro=("chutich", "tgd"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_duyet", den_trang_thai="da_duyet", chu_ky=2,
         nguon="tours.py::approve",
         vi_sao="Dưới biên là bán lỗ so với ngưỡng đã chốt – phải đủ HAI chữ ký, không ai ký thay."),

    Buoc("chuyen_tour", "d7", "Quyết định mốc D-7: ghép, dời hoặc huỷ",
         vai_tro=("chutich", "tp_dh"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="da_duyet", nguon="tours.py::d7",
         vi_sao="TP Điều hành quyết ghép/dời/huỷ. Riêng chuyến DƯỚI HOÀ VỐN muốn chạy tiếp thì chỉ "
                "Chủ tịch – đó là quyết định tiêu tiền, không phải quyết định điều hành."),

    Buoc("chuyen_tour", "dong_so", "Đóng sổ quyết toán",
         chu_so_huu=CHU_HO_SO, cach_canh=CHI_CHU_SO_HUU,
         tu_trang_thai="ket_thuc|da_duyet", den_trang_thai="da_dong_so", nguon="tours.py::close",
         vi_sao="Cổng 6 – MỘT CHỦ HỒ SƠ. Ai soạn thì người ấy đóng, kể cả Trưởng phòng cũng không "
                "đóng thay: đóng thay là mất dấu người chịu trách nhiệm về con số. Đổi 25/9/2026: "
                "chủ hồ sơ không còn khoá cứng vào người điều hành chuyến, vì ở phòng Đoàn người "
                "gom chứng từ và gõ quyết toán là Sale Admin."),

    Buoc("chuyen_tour", "giao_ho_so", "Bàn giao hồ sơ quyết toán",
         vai_tro=("tp_dh",), chu_so_huu=CHU_HO_SO, cach_canh=HOAC,
         nguon="chu_ho_so.py::giao_ho_so",
         vi_sao="Trao đi được, LẤY VỀ thì không: `sales_admin` cố ý không có trong danh sách vai, "
                "vì cho người nhận tự lấy hồ sơ về tay mình là bỏ luôn ý nghĩa của bàn giao. "
                "Không chuyển thưởng chuyến – cột `operator_id` không đổi."),

    Buoc("chuyen_tour", "kt_xac_nhan", "Kế toán xác nhận quyết toán",
         vai_tro=("ketoan",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="da_dong_so", den_trang_thai="kt_xac_nhan", nguon="tours.py::kt_confirm",
         vi_sao="Bàn giao sang Kế toán. Từ đây số vào sổ."),

    Buoc("chuyen_tour", "kt_tra_lai", "Kế toán trả lại quyết toán",
         vai_tro=("ketoan",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="da_dong_so", den_trang_thai="ket_thuc", nguon="settlement.py::kt_return",
         vi_sao="Đường lùi duy nhất. Không có đường nào khác đưa quyết toán về lại Điều hành."),

    Buoc("chuyen_tour", "cntt_doi_chieu", "CNTT đối chiếu độc lập",
         vai_tro=("cntt",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="kt_xac_nhan", nguon="tours.py::cntt_check",
         vi_sao="Người đối chiếu không được là người ghi sổ."),
)

# ---------------------------------------------------------------------------------------------
# QUYẾT TOÁN – các dòng chi tiết bên trong một chuyến
# ---------------------------------------------------------------------------------------------
_QUYET_TOAN = (
    Buoc("quyet_toan", "soan_dong", "Thêm/sửa/huỷ dòng nhà cung cấp",
         chu_so_huu=CHU_HO_SO, cach_canh=CHI_CHU_SO_HUU,
         nguon="settlement.py::_assert_edit",
         vi_sao="Cùng cổng 6 với việc đóng sổ – soạn và đóng phải là một người. Dòng đầu tiên ghi "
                "vào đây còn ĐÓNG DẤU tên người ghi lên chuyến, để đổi tham số mảng Đoàn về sau "
                "không lấy được một hồ sơ đang soạn dở khỏi tay người đang soạn."),

    Buoc("quyet_toan", "gan_chung_tu", "Gắn chứng từ vào một dòng",
         vai_tro=("ketoan", "cntt"), chu_so_huu=CHU_HO_SO, cach_canh=HOAC,
         nguon="settlement.py::set_doc",
         vi_sao="Chứng từ có thể về tay Kế toán trước; mở thêm đúng hai vai trò ấy, không mở rộng hơn."),
)

# ---------------------------------------------------------------------------------------------
# ĐỀ NGHỊ CHI – confirm → check → approve → pay
# ---------------------------------------------------------------------------------------------
# Người xác nhận bước đầu đổi theo LOẠI CHI, nên khai thành bảng riêng thay vì một danh sách phẳng.
NGUOI_XAC_NHAN_THEO_LOAI = {
    "chi_tour":   ("tp_dh",),
    "marketing":  ("ptgd_mkt",),
    "hanh_chinh": ("hcns",),
    "hoan_tien":  ("gd_kd", "tp_kd", "tp_dh"),
    "tam_ung":    ("tp_dh",),
    # Đội xe – Chủ tịch quyết 05/10/2026. Giám đốc đội xe XÁC NHẬN nghiệp vụ; cửa DUYỆT vẫn là
    # TGĐ / Chủ tịch như mọi loại chi khác, nên bảng bước bên dưới không đổi một dòng nào.
    "sua_chua_xe":    ("gd_doi_xe",),
    "tam_ung_tai_xe": ("gd_doi_xe",),
}

_DE_NGHI_CHI = (
    Buoc("de_nghi_chi", "xac_nhan_bo_phan", "Người phụ trách bộ phận xác nhận",
         vai_tro=tuple(sorted({v for vs in NGUOI_XAC_NHAN_THEO_LOAI.values() for v in vs} | {"tgd"})),
         cach_canh=CHI_VAI_TRO, tu_trang_thai="cho_tp", den_trang_thai="cho_kt",
         nguon="ops.py::step(confirm) + CATEGORY_CONFIRMER",
         vi_sao="Vai trò cụ thể đổi theo loại chi – xem NGUOI_XAC_NHAN_THEO_LOAI. TGĐ xác nhận được "
                "mọi loại, vì bộ phận có lúc không có người."),

    Buoc("de_nghi_chi", "ke_toan_kiem", "Kế toán kiểm tra hồ sơ",
         vai_tro=("ketoan",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_kt", den_trang_thai="cho_duyet", nguon="ops.py::step(check)",
         vi_sao="Hai điều kiện chặn ở đây: phải có chứng từ đính kèm, và nhà cung cấp phải có MST "
                "(trừ hoàn tiền và tạm ứng). Thiếu thì không chuyển duyệt."),

    Buoc("de_nghi_chi", "duyet", "Duyệt chi",
         vai_tro=("tgd", "chutich"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_duyet", den_trang_thai="cho_chi", chu_ky=1,
         nguon="ops.py::step(approve)",
         vi_sao="TGĐ ký. Chủ tịch chỉ ký khi đề nghị cần hai chữ ký – ký một mình không đủ để duyệt."),

    Buoc("de_nghi_chi", "duyet_hai_chu_ky", "Duyệt chi – loại cần hai chữ ký",
         vai_tro=("tgd", "chutich"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_duyet", den_trang_thai="cho_chi", chu_ky=2,
         nguon="ops.py::step(approve)",
         vi_sao="Đủ chữ ký mới sang cho_chi; thiếu một chữ ký thì đề nghị vẫn nằm ở bước duyệt."),

    Buoc("de_nghi_chi", "ghi_da_chi", "Kế toán ghi nhận đã chi",
         vai_tro=("ketoan",), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="cho_chi", den_trang_thai="da_chi", nguon="ops.py::step(pay)",
         vi_sao="ĐÃ DUYỆT KHÔNG PHẢI ĐÃ CHI. Hai trạng thái này là hai con số khác nhau trên báo cáo "
                "dòng tiền – gộp lại là việc VTOS-06 phải sửa."),

    Buoc("de_nghi_chi", "tu_choi", "Từ chối đề nghị",
         vai_tro=("tp_dh", "ptgd_mkt", "hcns", "gd_kd", "tp_kd", "ketoan", "tgd", "chutich"),
         cach_canh=CHI_VAI_TRO, den_trang_thai="tu_choi", nguon="ops.py::step(reject)",
         vi_sao="Từ chối được ở mọi bước trừ khi đã chi, và bắt buộc có lý do."),
)

# ---------------------------------------------------------------------------------------------
# BOOKING và BẢO LƯU
# ---------------------------------------------------------------------------------------------
_BOOKING = (
    Buoc("booking", "tao", "Tạo booking",
         vai_tro=("nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO, nguon="tours.py::create_booking",
         vi_sao="Cổng 12 – một cửa vào chỗ ngồi. Kinh doanh gửi yêu cầu, Điều hành mới ghi chỗ."),

    Buoc("booking", "gui_yeu_cau", "Gửi yêu cầu đặt dịch vụ",
         vai_tro=("tp_dh", "nv_dh", "gd_kd", "tp_kd", "tn_kd", "nv_kd"), cach_canh=CHI_VAI_TRO,
         nguon="tours.py::create_request + access.REQUEST_CREATE_ROLES",
         vi_sao="Cửa vào của Kinh doanh: gửi yêu cầu thì rộng, ghi chỗ thì hẹp."),

    Buoc("booking", "sua_thong_tin_khach", "Sửa thông tin khách trên booking",
         vai_tro=("nv_dh", "tp_dh"), chu_so_huu=SALE_PHU_TRACH, cach_canh=HOAC,
         nguon="bookings.py::update_customer",
         vi_sao="Sale phụ trách sửa booking của mình; Điều hành sửa được của mọi booking."),

    Buoc("booking", "huy", "Huỷ booking",
         vai_tro=("nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO, nguon="bookings.py::cancel + CANCEL_ROLES",
         vi_sao="Huỷ là trả chỗ về kho và có thể sinh phí huỷ – một cửa, chỉ Điều hành."),

    Buoc("booking", "mo_khoa", "Mở khoá booking đã khoá",
         vai_tro=("tp_dh", "sales_admin", "cntt", "tgd"), cach_canh=CHI_VAI_TRO,
         nguon="bookings.py::unlock + UNLOCK_ROLES",
         vi_sao="Mở khoá là bẻ một quy tắc đã chặn, và nó là quyền SỬA SỐ SAU KHI ĐÃ CHỐT. "
                "Chủ tịch quyết 25/9/2026: gỡ Giám đốc và Trưởng phòng Kinh doanh – người bán "
                "không mở lại con số doanh thu của chính mình; thêm Sale Admin, vai giữ hồ sơ."),
)

_BAO_LUU = (
    Buoc("bao_luu", "tat_toan", "Tất toán khoản bảo lưu vào booking mới",
         vai_tro=("nv_dh", "tp_dh", "ketoan"), cach_canh=CHI_VAI_TRO,
         nguon="bookings.py::apply_retention",
         vi_sao="Chạm thẳng vào tiền của khách – hẹp hơn quyền đề xuất hoàn."),

    Buoc("bao_luu", "de_xuat_hoan", "Đề xuất hoàn tiền bảo lưu",
         vai_tro=("nv_dh", "tp_dh", "nv_kd", "tn_kd", "tp_kd", "gd_kd", "ketoan"),
         cach_canh=CHI_VAI_TRO, nguon="bookings.py::refund_retention",
         vi_sao="Đề XUẤT thì rộng – ai nghe khách nói cũng đề xuất được; quyết thì hẹp."),

    Buoc("bao_luu", "huy", "Huỷ khoản bảo lưu",
         vai_tro=("tp_dh", "gd_kd", "tp_kd", "tgd", "ketoan"), cach_canh=CHI_VAI_TRO,
         nguon="bookings.py::cancel_retention",
         vi_sao="Huỷ bảo lưu là xoá một nghĩa vụ với khách – cấp trưởng trở lên."),
)

# ---------------------------------------------------------------------------------------------
# DỊCH VỤ LẺ và SẢN PHẨM
# ---------------------------------------------------------------------------------------------
_DICH_VU_LE = (
    Buoc("dich_vu_le", "tao", "Tạo dịch vụ lẻ",
         vai_tro=("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO,
         nguon="nonpackage.py::create + CREATE_ROLES",
         vi_sao="Vé lẻ, visa lẻ: Kinh doanh bán trực tiếp, không qua Điều hành như tour trọn gói."),

    Buoc("dich_vu_le", "sua", "Sửa dịch vụ lẻ",
         vai_tro=("nv_dh", "tp_dh", "gd_kd", "tp_kd", "tn_kd"), chu_so_huu=SALE_PHU_TRACH,
         cach_canh=HOAC, nguon="nonpackage.py::update",
         vi_sao="Sale phụ trách sửa của mình; cấp trưởng sửa được của cả nhóm."),

    # Ô GIÁ VỐN tách thành một bước riêng, vì nó KHÁC quyền với các ô còn lại của cùng cửa `update`:
    # sửa tên khách là một việc, sửa giá vốn là sửa mẫu số của hoa hồng. KHÔNG có chủ sở hữu —
    # không đường vòng theo operator_id hay sales_id — nên nó là CHI_VAI_TRO thuần.
    Buoc("dich_vu_le", "sua_gia_von", "Sửa giá vốn / nhà cung cấp của dịch vụ lẻ",
         vai_tro=("nv_dh", "tp_dh"), cach_canh=CHI_VAI_TRO,
         nguon="nonpackage.py::create + update + GIA_VON_ROLES",
         vi_sao="Ghi ô này là ghi thẳng `t.fixed_cost` và một dòng TourCostLine — trên chuyến đoàn "
                "việc ấy khoá theo 'Một cửa'. Chủ tịch quyết 25/9/2026: Phòng Kinh doanh LẺ gỡ hết, "
                "kể cả sale phụ trách; họ vẫn XEM được số, chỉ không sửa. Giá vốn là số của bên đặt "
                "dịch vụ với nhà cung cấp. Phòng Kinh doanh ĐOÀN giữ nguyên quyền của mình."),

    Buoc("dich_vu_le", "chot_thang", "Chốt dịch vụ lẻ theo tháng",
         vai_tro=("ketoan",), cach_canh=CHI_VAI_TRO,
         nguon="nonpackage.py::close_month + CHOT_THANG_ROLES",
         vi_sao="Chốt tháng là khoá kỳ – sau đó số không sửa bằng tay được nữa. Và nút này đặt "
                "một lượt cả `kt_xac_nhan` lẫn `kt_confirmed_at`, tức là ĐÓNG SỐ và KÝ XÁC NHẬN "
                "KẾ TOÁN trong cùng một cú bấm; trên chuyến đoàn hai việc ấy là hai người và hai "
                "bước. Chủ tịch quyết 25/9/2026: gỡ tp_dh và tgd – không ai ký thay Kế toán."),

    Buoc("dich_vu_le", "mo_tour_tu_san_pham", "Mở chuyến khởi hành từ sản phẩm",
         vai_tro=("nv_dh", "tp_dh", "cntt"), cach_canh=CHI_VAI_TRO, nguon="products.py::open_tour",
         vi_sao="Điều 2 Điều hành: sản phẩm là khuôn, chuyến là lần chạy thật – chỉ Điều hành mở."),
)

# ---------------------------------------------------------------------------------------------
# BÁO HƯ HỎNG XE — Chủ tịch chọn 06/10/2026
# ---------------------------------------------------------------------------------------------
# Chuỗi này ngắn và cố ý ngắn: ba bước, không có cấp duyệt nào. Báo hỏng KHÔNG sinh tiền, nên nó
# không đi qua bàn ký nào cả. Tiền chỉ xuất hiện ở bước sau và đi bằng nghiệp vụ `de_nghi_chi`
# (loại `sua_chua_xe`), nơi TGĐ / Chủ tịch ký như mọi khoản chi khác.
_BAO_HONG = (
    Buoc("bao_hong_xe", "bao", "Báo xe hỏng",
         vai_tro=("cntt", "hcns", "tp_dh", "nv_dh", "gd_doi_xe", "tai_xe"), cach_canh=CHI_VAI_TRO,
         den_trang_thai="moi", nguon="fleet.py::them_bao_hong",
         vi_sao="Tài xế là người đứng cạnh chiếc xe. Trong hàm còn một lớp hẹp hơn vai trò: tài xế "
                "chỉ báo được xe mình đứng tên hoặc xe có lệnh điều cho mình."),

    Buoc("bao_hong_xe", "tiep_nhan", "Đội xe tiếp nhận báo hỏng",
         vai_tro=("cntt", "hcns", "tp_dh", "nv_dh", "gd_doi_xe"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="moi", den_trang_thai="da_tiep_nhan", nguon="fleet.py::tiep_nhan_bao_hong",
         vi_sao="Tiếp nhận KHÔNG đóng. Hai câu hỏi khác nhau – “đã có ai nhìn chưa” và “đã sửa xong "
                "chưa” – và gộp làm một thì một lần bấm cho hết hàng đợi là xe hỏng biến khỏi màn hình."),

    Buoc("bao_hong_xe", "dong", "Đóng báo hỏng",
         vai_tro=("cntt", "hcns", "tp_dh", "nv_dh", "gd_doi_xe"), cach_canh=CHI_VAI_TRO,
         tu_trang_thai="moi|da_tiep_nhan", den_trang_thai="da_dong", nguon="fleet.py::dong_bao_hong",
         vi_sao="Bắt buộc ghi kết quả. Đóng mà không nói đã làm gì thì sổ báo hỏng chỉ còn là một "
                "danh sách đã-bấm-nút, và lần sau cùng hiện tượng ấy không ai tra được lần trước xử lý sao."),
)

# ---------------------------------------------------------------------------------------------
# ĐƠN TỪ NHÂN SỰ – nghỉ phép, ốm đau, vắng việc, công tác, tăng ca
# ---------------------------------------------------------------------------------------------
# Chủ tịch quyết 30/9/2026, nhóm việc CON NGƯỜI: "nghỉ phép, ốm đau, vắng việc sẽ do Huấn duyệt,
# TGĐ và CT thấy." MỘT chữ ký, và chuỗi dừng ở đó – nhóm này không sinh tiền nên không đi qua bàn
# ký tiền. (Đơn nghỉ kéo theo trừ lương thì phần trừ lương đi đường bảng lương của HCNS, luồng
# khác, và Nghị định 13/2023 chặn không cho đọc bảng lương ở đây.)
#
# Bước duyệt KHÔNG khai cứng vai trò: người ký phụ thuộc PHÒNG của người làm đơn
# (`hrm.nguoi_ky_don`). Khai cứng ở đây là khai luật lần thứ hai, và hai bảng khai tay thì sớm
# muộn cũng lệch – lúc lệch thì bảng đem đi ký mô tả một chuỗi chỉ huy không có thật.
_DON_NHAN_SU = (
    Buoc("don_nhan_su", "gui", "Gửi đơn nghỉ / ốm / vắng việc",
         vai_tro=(), cach_canh=CHI_VAI_TRO, vai_tro_dong="mọi người cho đơn của chính mình",
         den_trang_thai="cho_duyet", nguon="hrm.py::create_leave",
         vi_sao="Đơn là của chính người gửi, nên không có danh sách vai trò nào cả – điều kiện là "
                "tài khoản đã ghép với hồ sơ nhân sự. Quỹ phép năm canh ngay lúc gửi, không đợi "
                "tới bàn ký: báo hết phép lúc đã nghỉ xong thì không còn là một lời cảnh báo."),

    Buoc("don_nhan_su", "quyet", "Duyệt hoặc từ chối đơn",
         vai_tro=(), cach_canh=CHI_VAI_TRO, vai_tro_dong="hrm.nguoi_ky_don(phòng của người làm đơn)",
         tu_trang_thai="cho_duyet", den_trang_thai="duyet|tu_choi", nguon="hrm.py::decide_leave",
         vi_sao="Đội xe một chữ ký của Giám đốc đội xe – Chủ tịch quyết 30/9/2026. TGĐ và Chủ tịch "
                "THẤY mọi đơn nhưng không ký ở bước này. Từ chối bắt buộc ghi lý do, và không ai "
                "tự ký đơn của chính mình kể cả khi đúng vai."),
)

LUONG_VIEC: tuple[Buoc, ...] = (_TOUR + _QUYET_TOAN + _DE_NGHI_CHI + _BOOKING + _BAO_LUU
                                + _DICH_VU_LE + _BAO_HONG + _DON_NHAN_SU)

NGHIEP_VU = {
    "chuyen_tour": "Chuyến tour – dự toán đến quyết toán",
    "quyet_toan": "Quyết toán – dòng nhà cung cấp",
    "de_nghi_chi": "Đề nghị chi",
    "booking": "Booking",
    "bao_luu": "Bảo lưu tiền khách",
    "dich_vu_le": "Dịch vụ lẻ và sản phẩm",
    "bao_hong_xe": "Báo hư hỏng xe",
    "don_nhan_su": "Đơn từ nhân sự – nghỉ phép, ốm đau, vắng việc",
}


# ---------------------------------------------------------------------------------------------
# Tra cứu
# ---------------------------------------------------------------------------------------------
def buoc(nghiep_vu: str, ma: str) -> Buoc | None:
    for b in LUONG_VIEC:
        if b.nghiep_vu == nghiep_vu and b.ma == ma:
            return b
    return None


def theo_nghiep_vu(nghiep_vu: str) -> tuple[Buoc, ...]:
    return tuple(b for b in LUONG_VIEC if b.nghiep_vu == nghiep_vu)


def buoc_cua_vai_tro(vai_tro: str) -> tuple[Buoc, ...]:
    """Những bước một vai trò đẩy được. Dùng cho trang tra cứu ngược ở màn hình /access."""
    return tuple(b for b in LUONG_VIEC if vai_tro in b.vai_tro)


def duoc_day(b: Buoc, vai_tro: str, la_chu_so_huu: bool = False,
             vai_tro_dong: str = "") -> tuple[bool, str]:
    """Vai trò này có đẩy được bước ấy không, và nếu không thì VÌ SAO.

    Trả kèm lý do vì thông điệp 403 phải nói được ba điều (P10): vai trò đang dùng, quyền còn
    thiếu, ai cấp được. Một câu "không có quyền" trơ trọi thì người dùng đọc là phần mềm hỏng.

    `vai_tro_dong` là vai trò do hàm tính lúc chạy, khi bước khai vai_tro_dong – bên gọi tính rồi
    truyền vào, vì bảng này CỐ Ý không nhập mã nghiệp vụ để tự tính.
    """
    if b.vai_tro_dong:
        if not vai_tro_dong:
            return False, f"bước '{b.ten}' có vai trò tính theo {b.vai_tro_dong}, bên gọi chưa tính"
        if vai_tro != vai_tro_dong:
            return False, f"bước '{b.ten}' do {vai_tro_dong} làm, không phải {vai_tro}"
        return True, ""

    co_vt = vai_tro in b.vai_tro
    if b.cach_canh == CHI_VAI_TRO:
        return (True, "") if co_vt else (
            False, f"bước '{b.ten}' chỉ dành cho: {', '.join(b.vai_tro)}")
    if b.cach_canh == CHI_CHU_SO_HUU:
        return (True, "") if la_chu_so_huu else (
            False, f"bước '{b.ten}' là cổng một cửa – chỉ {_TEN_CHU[b.chu_so_huu]} làm được")
    if b.cach_canh == HOAC:
        return (True, "") if (co_vt or la_chu_so_huu) else (
            False, f"bước '{b.ten}' dành cho {', '.join(b.vai_tro)} hoặc {_TEN_CHU[b.chu_so_huu]}")
    if b.cach_canh == VA:
        return (True, "") if (co_vt and la_chu_so_huu) else (
            False, f"bước '{b.ten}' cần vừa là {', '.join(b.vai_tro)} vừa là {_TEN_CHU[b.chu_so_huu]}")
    return False, f"bước '{b.ten}' khai cách canh không hợp lệ: {b.cach_canh}"


def bang() -> list[dict]:
    """Bảng phẳng cho màn hình và cho bản xuất ra ký."""
    return [{
        "nghiep_vu": b.nghiep_vu, "nghiep_vu_ten": NGHIEP_VU.get(b.nghiep_vu, b.nghiep_vu),
        "ma": b.ma, "ten": b.ten, "ai_duoc": b.ai_duoc(),
        "vai_tro": list(b.vai_tro), "chu_so_huu": b.chu_so_huu, "cach_canh": b.cach_canh,
        "tu_trang_thai": b.tu_trang_thai, "den_trang_thai": b.den_trang_thai,
        "chu_ky": b.chu_ky, "nguon": b.nguon, "vi_sao": b.vi_sao,
    } for b in LUONG_VIEC]
