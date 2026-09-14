# -*- coding: utf-8 -*-
"""SEC-02 + CF-07 · Bảng TRÌNH BÀY của khối Dòng tiền: ai xem dòng nào, và dòng nào có cửa nhập.

────────────────────────────────────────────────────────────────────────────────────────────────
MỘT DANH MỤC DÒNG, KHÔNG HAI  (sửa 13/9/2026)
────────────────────────────────────────────────────────────────────────────────────────────────
Bản 11/9 của tệp này TỰ KHAI 13 mã dòng, trong khi `models/nghia_vu.py` (VPM-11) đã khai đúng 13
nhóm ấy để làm khoá dữ liệu. Hai bên trùng việc, và 7 trên 13 mã đặt khác tên nhau.

Nay tệp này KHÔNG khai mã nữa – nó NHẬP `NHOM` từ mô hình. Lý do chọn mã của VPM-11 làm chuẩn
không phải vì họ làm trước, mà vì mã của họ GẮN VÀO DỮ LIỆU THẬT: đã có bảng, đã có bước chuyển,
sắp có bản ghi. Mã ở một bảng trình bày thì đổi không tốn gì.

Phần tệp này giữ riêng, vì sổ nghĩa vụ không có và không nên có:
    · hai dòng TỔNG và ba dòng SỐ DƯ  – chúng là dòng của BẢNG, không phải nghĩa vụ
    · tên dòng đáy gắn với phạm vi xem
    · bảng CỬA NHẬP (CF-07)

────────────────────────────────────────────────────────────────────────────────────────────────
MỘT LUẬT QUYỀN, HAI TRỤC  (sửa 13/9/2026 theo phản biện)
────────────────────────────────────────────────────────────────────────────────────────────────
VPM-11 khai theo lối LOẠI TRỪ: nhóm mới quên khai thì MẶC ĐỊNH HIỆN. Bản 11/9 của tệp này khai
ĐÓNG MẶC ĐỊNH: chưa khai thì không thấy. Nhìn qua là mâu thuẫn, nhưng hai bên đang nói về HAI
TRỤC KHÁC NHAU, nên giữ được cả hai:

    Trục NHÓM NGHĨA VỤ   → theo VPM-11. Nhóm mới mà quên khai thì vẫn HIỆN và vẫn được CỘNG.
                           Lộ một nhóm mới thì có người kêu; giấu một nhóm mới thì không ai biết,
                           và bảng nhu cầu tiền nhẹ hơn sự thật.
    Trục VAI TRÒ         → theo bản này. Vai trò chưa khai thì KHÔNG THẤY GÌ. Thêm một vai trò mới
                           mà tự động cho xem sổ tiền là một lần rò rỉ không ai kêu.

Phản biện 13/9 tách thêm một tầng nữa, và tầng ấy mới là chỗ đúng nhất: PHÉP TÍNH khác QUYỀN XEM.
Nhóm chưa phân loại vẫn phải ĐƯỢC ĐẾM (không bỏ sót), nhưng bảng phải TỰ ĐÁNH DẤU là chưa đầy đủ
(không đoán). Hàm `day_du()` ở cuối tệp làm đúng việc ấy.

────────────────────────────────────────────────────────────────────────────────────────────────
RANH GIỚI TẦM NHÌN CỦA TỔNG GIÁM ĐỐC – Chủ tịch chốt 13/9/2026
────────────────────────────────────────────────────────────────────────────────────────────────
Nguyên văn: "Lương nằm trong tầm Tổng giám đốc; chỉ mảng TÀI CHÍNH KẾ TOÁN là không."

Nên ranh giới nay vẽ theo MẢNG, không vẽ theo từng dòng một: ngoài tầm đúng NĂM nhóm, và cả năm
đều là tài chính – kế toán (vay, trả gốc, lãi phí, thuế, ký quỹ). Mọi nhóm còn lại – kể cả lương –
thuộc tầm Tổng giám đốc.

ĐO ĐƯỢC 13/9, VÀ NÓ LÀM CHỐT NÀY THÀNH BẮT BUỘC CHỨ KHÔNG CHỈ LÀ MỘT LỰA CHỌN
    `services/hr.py` hàm `advance()` đã có sẵn dây chuyền ký bảng lương:
        nhap → (kế toán) kt_xac_nhan → (HCNS) hcns_lap → (TỔNG GIÁM ĐỐC) tgd_ky
    và chính chữ ký của Tổng giám đốc là chỗ gọi `post_payroll_entries()` ghi sổ.

    Tức TRƯỚC chốt hôm nay, người KÝ DUYỆT chi lương lại là người DUY NHẤT không được nhìn dòng
    lương trên bảng dòng tiền. Ký một khoản mà không thấy nó nằm ở đâu trong nhu cầu tiền của
    tháng là đúng thứ bảng này sinh ra để chặn. Chốt của Chủ tịch vá lại chỗ lệch ấy.

Chốt này BỎ hai thứ của bản trước:
  · `luong_bh` ra khỏi `NHOM_NGOAI_TAM_TGD` trong `models/nghia_vu.py` (sửa cùng lần đẩy này).
    Bản 11/9 xếp nó ra ngoài vì CHƯA TÁCH ĐƯỢC theo bộ phận, và tự ghi rằng đó là "việc còn
    thiếu, không phải quyết định về quyền". Nay Chủ tịch quyết đúng phần thẩm quyền ấy.
  · Cách thứ tư ("ô giá trị ghi chưa xác định") KHÔNG còn dòng nào dùng. Bộ máy vẫn giữ – xem
    `CHUA_TACH_DUOC` bên dưới – vì nó là hàng rào cho mọi dòng ngoài tầm về sau, không phải
    một chỗ khai riêng cho lương.

SỬA Ở MÔ HÌNH, KHÔNG KHAI ĐÈ Ở ĐÂY
    `nhom_duoc_xem()` lọc ngay tại CÂU TRUY VẤN (`services/nghia_vu.py` dòng 409), không phải
    ở màn hình. Mở dòng lương ở bảng trình bày mà không mở ở mô hình thì bảng hiện một dòng
    RỖNG – tệ hơn cả giấu hẳn, vì nó trông như công ty không phải trả lương.

VIỆC CÒN THIẾU THÌ VẪN CÒN, VÀ PHẢI NÓI RA
    Quyền đã mở, nhưng con số lương vẫn gồm cả khối văn phòng tập đoàn – nó RỘNG HƠN cái tên
    "tour và xe" trên đầu bảng. Cùng cảnh với `van_hanh_khac` (lẫn chi phí chung trụ sở). Hai
    dòng ấy giữ số, giữ phép cộng, và mang `GHI_CHU_LAN_SANG` nói thẳng điều đó.

    Chọn GHI CHÚ chứ không ẩn số, vì ẩn số của một dòng CHI làm dòng đáy CAO LÊN – bảng trông
    dư tiền hơn sự thật. Để nguyên số thì dòng đáy THẤP HƠN sự thật. Sai về phía thấp thì người
    đọc đi hỏi; sai về phía cao thì người đọc yên tâm.

    Ngày nào bảng lương có cột bộ phận thì tách được, và ghi chú ấy mới có đường biến mất.

TRỤC RIÊNG KHÔNG ĐỔI THEO CHỐT NÀY
    Xem SỐ TỔNG HỢP quỹ lương ≠ xem LƯƠNG TỪNG NGƯỜI. Chốt 13/9 mở cái thứ nhất cho Tổng giám
    đốc; cái thứ hai vẫn chỉ Chủ tịch, Kế toán và Ban Kiểm soát – xem `xem_chi_tiet_nhan_vien()`.
"""
from app.models.nghia_vu import GHI_NHO as NHOM_GHI_NHO
from app.models.nghia_vu import NHOM, nhom_duoc_xem
from app.services.lam_tron_tien import bang_tien, o_tien  # noqa: F401  (dùng ở tầng dựng bảng)

# Phía của dòng trong bảng.
VAO, RA, GHI_NHO, SO_DU, TONG = "vao", "ra", "ghi_nho", "so_du", "tong"

# Hai mức xem.
TOAN_CANH = "toan_canh"
TOUR_XE_THOI = "tour_xe"


class Dong:
    """Một dòng của bảng TRÌNH BÀY.

    `tu_tinh` = cộng ra từ dòng khác, nên KHÔNG có cửa nhập. Bắt nó có cửa nhập tức là cho phép gõ
    đè lên một kết quả tính được – chỗ ấy là chỗ số liệu bắt đầu nói khác sổ.

    `tu_so_nghia_vu` = dòng này lấy số từ sổ nghĩa vụ (mã trùng với NHOM). Dòng không mang cờ này
    là dòng của riêng bảng.
    """

    def __init__(self, ma: str, ten: str, phia: str, tu_tinh: bool = False,
                 tu_so_nghia_vu: bool = False):
        self.ma, self.ten, self.phia = ma, ten, phia
        self.tu_tinh, self.tu_so_nghia_vu = tu_tinh, tu_so_nghia_vu


# =============================================================================================
# Danh mục dòng – 13 nhóm NHẬP từ sổ nghĩa vụ + 5 dòng riêng của bảng
# =============================================================================================
# Thứ tự lấy nguyên bảng mục III của v1.1: dòng TỔNG đứng TRƯỚC các dòng thành phần của nó.
def _nv(ma: str, phia: str) -> Dong:
    """Dựng một dòng từ nhóm nghĩa vụ. TÊN lấy thẳng từ mô hình – không chép lại, không đặt lại."""
    return Dong(ma, NHOM[ma][1], phia, tu_so_nghia_vu=True)


CAC_DONG = [
    Dong("tien_kha_dung_dau_ky", "Tiền khả dụng đầu kỳ", SO_DU),

    Dong("tong_thu", "TỔNG TIỀN DỰ KIẾN THU", TONG, tu_tinh=True),
    _nv("thu_khach", VAO),
    _nv("thu_cong_no_khac", VAO),
    _nv("giai_ngan_vay", VAO),

    Dong("tong_chi", "TỔNG TIỀN PHẢI THANH TOÁN", TONG, tu_tinh=True),
    _nv("tra_ncc", RA),
    _nv("hoan_khach", RA),
    _nv("hoa_hong", RA),
    _nv("tra_goc_vay", RA),
    _nv("lai_phi_vay", RA),
    _nv("luong_bh", RA),
    _nv("thue", RA),
    _nv("van_hanh_khac", RA),

    Dong("so_du_du_kien_cuoi_khoang", "SỐ DƯ DỰ KIẾN CUỐI KHOẢNG", SO_DU, tu_tinh=True),
    Dong("thieu_so_voi_muc_du_phong", "THIẾU SO VỚI MỨC DỰ PHÒNG", SO_DU, tu_tinh=True),

    _nv("thu_ho_khach", GHI_NHO),
    _nv("ky_quy_lu_hanh", GHI_NHO),
]
DONG = {d.ma: d for d in CAC_DONG}

# Ba dòng CHỈ Chủ tịch – Cách A, Chủ tịch chốt 11/9. Dòng số dư đứng trên một bảng đã lọc là cho
# một cái mốc toàn cảnh làm chuẩn cho một bảng không toàn cảnh.
CHI_TOAN_CANH = ("tien_kha_dung_dau_ky", "so_du_du_kien_cuoi_khoang", "thieu_so_voi_muc_du_phong")


# =============================================================================================
# Quyền xem – hai trục
# =============================================================================================
# Trục VAI TRÒ: đóng mặc định. Vai trò không có ở đây thì KHÔNG mở được khối này.
BANG_QUYEN = {
    "chutich": TOAN_CANH,
    "ketoan": TOAN_CANH,      # người lập bảng, phải đối chiếu được với sổ quỹ
    "bks": TOAN_CANH,         # kiểm soát mà chỉ xem một phần thì không kiểm soát gì
    "cntt": TOAN_CANH,        # theo khai của VPM-11 – giữ cho hai bên nói cùng một thứ
    "robot_ks": TOAN_CANH,
    "tgd": TOUR_XE_THOI,
}
# Hai Phó Tổng giám đốc KHÔNG có trong bảng – khai VẮNG MẶT chứ không khai "cấm". Danh sách cấm
# phải sửa mỗi lần thêm vai trò mới; danh sách cho phép thì không.

# Quyền xem CHI TIẾT THEO NHÂN VIÊN, tách khỏi quyền xem số tổng hợp (Chủ tịch chốt 13/9). Đây là
# trục thứ ba, và nó hẹp hơn hẳn: một người được xem tổng quỹ lương không đương nhiên được xem
# lương từng người.
XEM_CHI_TIET_NHAN_VIEN = ("chutich", "ketoan", "bks")

# CÁCH THỨ TƯ – dòng có mặt trên bảng của vai trò xem một phần, nhưng ô giá trị ghi một câu thay
# cho con số. RỖNG từ 13/9/2026: chốt của Chủ tịch đưa lương vào tầm Tổng giám đốc, và không còn
# dòng nào vừa ngoài tầm vừa phải hiện.
#
# GIỮ LẠI BỘ MÁY dù đang rỗng, và giữ có chủ ý. Nó không phải chỗ khai riêng cho lương – nó là
# đường duy nhất để một dòng NGOÀI TẦM được phép có mặt trên bảng, và `an_gia_tri()` bảo đảm dòng
# đi đường ấy thì KHÔNG BAO GIỜ kèm số. Xoá đi thì lần sau ai cần lại phải dựng lại từ đầu, và
# nhiều khả năng dựng bằng một câu `if` theo tên dòng – tức đúng chỗ đã hỏng.
CHUA_TACH_DUOC: dict[str, str] = {}
CAU_CHUA_TACH = "chưa xác định phần thuộc phạm vi quản lý"

# Dòng VẪN HIỆN SỐ và VẪN VÀO PHÉP CỘNG, nhưng con số RỘNG HƠN cái tên bảng. Ghi chú, không phải
# phép ẩn – xem lý lẽ ở đầu tệp. Ai đọc dòng này phải biết nó đang rộng hơn phạm vi tour–xe.
#
# Đây là chỗ giữ lại VIỆC CÒN THIẾU sau khi quyền đã mở: Chủ tịch quyết Tổng giám đốc được XEM
# lương, nhưng quyết ấy không tạo ra cột bộ phận mà bảng lương đang thiếu.
GHI_CHU_LAN_SANG = {
    "luong_bh": "Gồm lương và bảo hiểm của TOÀN CÔNG TY – bảng lương chưa có cột bộ phận để tách "
                "phần bộ phận tour và đội xe, nên con số này RỘNG HƠN phạm vi tour–xe.",
    "van_hanh_khac": "Gồm cả chi phí chung của trụ sở – chưa tách được phần của chuyến và của xe, "
                     "nên con số này RỘNG HƠN phạm vi tour–xe.",
}

TEN_DONG_DAY = {
    TOAN_CANH: "SỐ DƯ DỰ KIẾN CUỐI KHOẢNG",
    TOUR_XE_THOI: "Dòng tiền thuần từ hoạt động tour và xe",
}

CANH_BAO = {
    "phai_tra_qua_han": (TOUR_XE_THOI, "Phải trả quá hạn"),
    "phai_tra_7_ngay": (TOUR_XE_THOI, "Phải trả trong 7 ngày tới"),
    "ngay_dau_thieu_tien": (TOAN_CANH, "Ngày đầu tiên dự kiến thiếu tiền"),
    "muc_thieu_lon_nhat": (TOAN_CANH, "Mức thiếu lớn nhất"),
}


def muc_xem(vai_tro: str) -> str | None:
    """Mức xem khối dòng tiền. None = không mở được khối này.

    Đóng mặc định: vai trò lạ trả None. Trả TOUR_XE_THOI cho vai trò chưa khai nghe có vẻ "an toàn
    hơn cấm hẳn", nhưng đó là mở quyền cho một người chưa ai xét.
    """
    return BANG_QUYEN.get(vai_tro)


def xem_duoc(vai_tro: str, ma_dong: str) -> bool:
    m = muc_xem(vai_tro)
    if m is None or ma_dong not in DONG:
        return False
    if m == TOAN_CANH:
        return True
    if ma_dong in CHI_TOAN_CANH:
        return False
    d = DONG[ma_dong]
    if not d.tu_so_nghia_vu:
        return True                      # hai dòng TỔNG: ai mở được khối cũng thấy
    if ma_dong in CHUA_TACH_DUOC:
        return True                      # cách thứ tư: DÒNG có mặt, SỐ thì không (xem an_gia_tri)
    # Trục NHÓM đi theo khai của sổ nghĩa vụ – nhóm mới chưa khai thì MẶC ĐỊNH HIỆN.
    return ma_dong in nhom_duoc_xem(vai_tro)


def an_gia_tri(vai_tro: str, ma_dong: str) -> bool:
    """Dòng có mặt nhưng ô giá trị KHÔNG hiện số – hiện "chưa xác định phần thuộc phạm vi quản lý".

    Suy ra từ RÀNG BUỘC, không tra theo tên dòng: một dòng lấy số từ sổ nghĩa vụ, hiện trên bảng
    của vai trò xem MỘT PHẦN, mà nhóm của nó nằm ngoài `nhom_duoc_xem()` thì BẮT BUỘC không có số.
    Viết theo lối này để `CHUA_TACH_DUOC` không bao giờ mở thêm được một dòng có số.

    Với người xem toàn cảnh thì dòng ấy vốn là cả dòng, không có gì phải tách.
    """
    if muc_xem(vai_tro) != TOUR_XE_THOI:
        return False
    d = DONG.get(ma_dong)
    if d is None or not d.tu_so_nghia_vu:
        return False
    if not xem_duoc(vai_tro, ma_dong):
        return False                     # không hiện thì không có ô nào để ẩn
    return ma_dong not in nhom_duoc_xem(vai_tro)


def xem_chi_tiet_nhan_vien(vai_tro: str) -> bool:
    """Xem được lương TỪNG NGƯỜI hay không. Hẹp hơn quyền xem số tổng hợp."""
    return vai_tro in XEM_CHI_TIET_NHAN_VIEN


def cac_dong_cho(vai_tro: str) -> list[Dong]:
    """Danh sách dòng của bảng, đã lọc. Thứ tự giữ nguyên bảng v1.1 – không xếp lại theo vai."""
    return [d for d in CAC_DONG if xem_duoc(vai_tro, d.ma)]


def dong_de_cong(vai_tro: str, phia: str) -> list[str]:
    """Mã các dòng dùng để cộng ra dòng TỔNG, theo đúng tập dòng vai trò ấy nhìn thấy.

    Dòng bị ẩn giá trị KHÔNG vào phép cộng: cộng một ô ghi "chưa xác định" là tự bịa ra một số.
    """
    return [d.ma for d in cac_dong_cho(vai_tro)
            if d.phia == phia and not an_gia_tri(vai_tro, d.ma)]


def ten_dong_day(vai_tro: str) -> str:
    """Tên dòng đáy. Hàm này và cac_dong_cho() phải luôn được gọi cùng nhau – một bảng đã lọc mà
    dòng đáy đề "số dư" thì con số ấy trông như đúng."""
    m = muc_xem(vai_tro)
    return "" if m is None else TEN_DONG_DAY[m]


def cac_canh_bao_cho(vai_tro: str) -> list[dict]:
    m = muc_xem(vai_tro)
    if m is None:
        return []
    return [{"ma": ma, "nhan": nhan} for ma, (can, nhan) in CANH_BAO.items()
            if m == TOAN_CANH or can == TOUR_XE_THOI]


def canh_bao_dong_day(vai_tro: str) -> str:
    """Câu đứng ngay dưới dòng đáy khi bảng còn dòng bị ẩn giá trị.

    Dán nhãn lên từng dòng thôi thì chưa đủ: người ta đọc dòng đáy rồi đi họp, không cuộn lên đọc
    ghi chú của dòng thứ chín.
    """
    an = [d for d in cac_dong_cho(vai_tro) if an_gia_tri(vai_tro, d.ma)]
    if not an:
        return ""
    return ("Con số này CHƯA gồm: " + ", ".join(d.ten for d in an)
            + f" — {CAU_CHUA_TACH}, nên "
            + ("dòng ấy" if len(an) == 1 else f"{len(an)} dòng ấy")
            + " đứng ngoài phép cộng.")


def ghi_chu_lan_sang(vai_tro: str) -> str:
    """Câu cho các dòng CÓ SỐ nhưng số rộng hơn phạm vi bảng. Khác hẳn câu trên: dòng vẫn được cộng.

    Hai câu phải đứng riêng. Gộp chúng lại thì người đọc không phân biệt được "thiếu khoản này"
    với "khoản này đang tính rộng hơn" – hai lỗi lệch về hai phía ngược nhau.
    """
    if muc_xem(vai_tro) != TOUR_XE_THOI:
        return ""
    ds = [d for d in cac_dong_cho(vai_tro)
          if d.ma in GHI_CHU_LAN_SANG and not an_gia_tri(vai_tro, d.ma)]
    if not ds:
        return ""
    return " ".join(f"{d.ten}: {GHI_CHU_LAN_SANG[d.ma]}" for d in ds)


def day_du(nhom_chua_phan_loai: list[str] | None = None) -> dict:
    """Báo cáo có đầy đủ không — TÁCH KHỎI quyền xem.

    Nhóm chưa phân loại vẫn được CỘNG vào tổng (không bỏ sót), nhưng bảng phải tự nói ra rằng nó
    chưa đầy đủ (không đoán). Đo được ngày 13/9: hạng mục lạ của `cash_plan_items` rơi thầm vào
    "Vận hành và phải trả khác" mà không có cờ nào – đây là hàm để cờ ấy có chỗ hiện lên.
    """
    ds = list(nhom_chua_phan_loai or [])
    if not ds:
        return {"day_du": True, "chua_phan_loai": [], "cau": ""}
    return {"day_du": False, "chua_phan_loai": ds,
            "cau": (f"Báo cáo CHƯA ĐẦY ĐỦ: {len(ds)} hạng mục chưa được phân loại vào dòng nào "
                    f"({', '.join(ds)}). Số tiền vẫn được cộng vào tổng, nhưng đang tạm xếp vào "
                    "'Vận hành và phải trả khác'.")}


def khung_bang(vai_tro: str, nhom_chua_phan_loai: list[str] | None = None) -> dict:
    """Khung bảng cho một vai trò: dòng nào, dòng nào ẩn giá trị, dòng đáy tên gì, ô cảnh báo nào.

    KHÔNG có số ở đây – số do tầng dựng bảng điền vào đúng khung này. Trả khung và số từ hai chỗ
    khác nhau là để một hôm nào đó khung thì lọc mà số thì không.
    """
    m = muc_xem(vai_tro)
    if m is None:
        return {"xem_duoc": False, "ly_do": "Vai trò này không mở khối Dòng tiền."}
    return {
        "xem_duoc": True,
        "muc_xem": m,
        "dong": [{"ma": d.ma, "ten": d.ten, "phia": d.phia,
                  "an_gia_tri": an_gia_tri(vai_tro, d.ma),
                  "hien": CAU_CHUA_TACH if an_gia_tri(vai_tro, d.ma) else None,
                  "ly_do_an": CHUA_TACH_DUOC.get(d.ma, "") if an_gia_tri(vai_tro, d.ma) else "",
                  "ghi_chu": ("" if an_gia_tri(vai_tro, d.ma) or m != TOUR_XE_THOI
                              else GHI_CHU_LAN_SANG.get(d.ma, ""))}
                 for d in cac_dong_cho(vai_tro)],
        "cong_thu": dong_de_cong(vai_tro, VAO),
        "cong_chi": dong_de_cong(vai_tro, RA),
        "ten_dong_day": ten_dong_day(vai_tro),
        "canh_bao": cac_canh_bao_cho(vai_tro),
        "canh_bao_dong_day": canh_bao_dong_day(vai_tro),
        "ghi_chu_lan_sang": ghi_chu_lan_sang(vai_tro),
        "xem_chi_tiet_nhan_vien": xem_chi_tiet_nhan_vien(vai_tro),
        "day_du": day_du(nhom_chua_phan_loai),
        "cau_pham_vi": ("Bảng này gồm toàn bộ dòng tiền của pháp nhân đang xem."
                        if m == TOAN_CANH else
                        "Bảng này CHỈ gồm dòng tiền của hoạt động kinh doanh tour và xe. "
                        "Không gồm vay, trả gốc, lãi, thuế và ký quỹ, nên không có dòng số dư."),
    }


# =============================================================================================
# CF-07 · Cửa nhập và chủ quản số liệu cho từng dòng
# =============================================================================================
# "Chưa có" ở cột nguồn là VIỆC PHẢI DỰNG THÊM MÀN HÌNH, không phải việc bỏ trống hoặc điền 0. Đó
# cũng là ranh giới chốt 09/9: hệ thống viết ra CẤU TRÚC và PHÉP TÍNH, còn SỐ thì bộ phận nghiệp vụ
# tự nhập hoặc tự tải.
CHUA_CO = "Chưa có"


class Cua:
    def __init__(self, nguon: str, cua: str, bo_phan: str, ngoai_bang_III4: bool = False):
        self.nguon, self.cua, self.bo_phan = nguon, cua, bo_phan
        # Bảng III.4 của v1.1 có 12 dòng, bảng dòng tiền có 18. Cờ này giữ lại sự thật ấy sau khi
        # Chủ tịch đã chốt cửa cho hai dòng ghi nhớ ngày 11/9: lần sau ai đối chiếu mã với tài liệu
        # sẽ thấy ngay vì sao lệch hai dòng, thay vì tưởng có người tự thêm bừa.
        self.ngoai_bang_III4 = ngoai_bang_III4

    def da_co_nguon(self) -> bool:
        return not self.nguon.startswith(CHUA_CO)


CUA_NHAP = {
    "tien_kha_dung_dau_ky": Cua(
        "Tài khoản ngân hàng và đối soát SePay",
        "Màn hình đối soát ngân hàng: chốt số dư theo ngày, ghi DANH SÁCH TÀI KHOẢN và MỐC GIỜ, "
        "có người xác nhận", "Kế toán"),
    "thu_khach": Cua(
        "Booking và phiếu thu đã có · sổ nghĩa vụ nạp từ lich_thanh_toan_hd + bookings",
        "Lịch thu theo booking và hợp đồng, có ngày dự kiến thu và mức chắc chắn",
        "Kinh doanh + Kế toán"),
    "thu_cong_no_khac": Cua(
        "cash_plan_items hướng vào — kế toán nhập tay",
        "Màn hình công nợ phải thu có ngày đến hạn, nối tự động vào sổ nghĩa vụ", "Kế toán"),
    "giai_ngan_vay": Cua(
        "Khế ước vay · sổ nghĩa vụ nạp từ fin_schedules",
        "Lịch giải ngân trong hồ sơ khế ước", "Kế toán"),
    "tra_ncc": Cua(
        "Đặt dịch vụ NCC · sổ nghĩa vụ nạp từ service_orders + payment_requests",
        "Lịch thanh toán theo hợp đồng và đơn đặt dịch vụ, gồm cả nghĩa vụ chưa lập đề nghị chi",
        "Điều hành + Kế toán"),
    "hoan_khach": Cua(
        "payment_requests loại hoàn tiền",
        "Phiếu hoàn tiền có ngày cam kết hoàn", "Chăm sóc khách hàng + Kế toán"),
    "hoa_hong": Cua(
        CHUA_CO, "Bảng tính hoa hồng theo kỳ, có ngày chi dự kiến", "Kinh doanh + Kế toán"),
    "tra_goc_vay": Cua(
        "Khế ước vay · fin_schedules loại trả gốc",
        "Lịch trả gốc – lãi – phí trong hồ sơ khế ước; tách phần lãi ước tính", "Kế toán"),
    "lai_phi_vay": Cua(
        "Khế ước vay · fin_schedules loại trả lãi",
        "Lịch trả gốc – lãi – phí trong hồ sơ khế ước; tách phần lãi ước tính", "Kế toán"),
    # HAI SỐ CHO CÙNG MỘT KHOẢN TIỀN – đo được 13/9/2026, chưa vá.
    # Bảng lương `PayrollRun` đã có số thật (`run.totals`), có kỳ, có chữ ký TGĐ và đã ghi sổ kế
    # toán khi ký. Nhưng `NGUON_DONG_BO` của sổ nghĩa vụ KHÔNG có `payroll_runs` – dòng lương trên
    # bảng dòng tiền chỉ chảy vào qua `cash_plan_items` do kế toán gõ tay.
    # Nên hôm nay VTOS giữ HAI con số cho cùng một khoản lương: một số đã ký, một số gõ tay. Chúng
    # không có gì buộc phải bằng nhau, và lệch thì không ai kêu. Đúng loại lỗi mà sổ nghĩa vụ
    # ("một nghĩa vụ một dòng") sinh ra để diệt. Việc thuộc làn VPM – đã nêu, chưa nhận.
    "luong_bh": Cua(
        "cash_plan_items hạng mục lương — kế toán nhập tay "
        "(PayrollRun ĐÃ CÓ số đã ký nhưng CHƯA nối vào sổ nghĩa vụ)",
        "Nối PayrollRun vào sổ nghĩa vụ làm nguồn thứ bảy, và bổ sung CỘT BỘ PHẬN cho bảng lương",
        "Hành chính – Nhân sự"),
    "thue": Cua(
        "cash_plan_items hạng mục thuế — kế toán nhập tay",
        "Lịch nghĩa vụ thuế theo pháp nhân và sắc thuế", "Kế toán"),
    "van_hanh_khac": Cua(
        "payment_requests marketing / hành chính · cash_plan_items (hạng mục lạ rơi vào đây)",
        "Kế hoạch chi vận hành theo tháng, người phụ trách xác nhận", "Các phòng + Kế toán"),

    # Hai dòng ghi nhớ KHÔNG có trong bảng III.4 của v1.1 (bảng ấy 12 dòng). Làn Phân quyền đề xuất
    # cửa ngày 11/9 và CHỦ TỊCH ĐÃ CHỐT cùng ngày.
    "thu_ho_khach": Cua(
        CHUA_CO,
        "Sổ thu hộ – chi hộ theo khách và theo chuyến, chốt số dư thu hộ tại ngày đối soát, "
        "ghi rõ tài khoản nào đang giữ", "Kế toán", ngoai_bang_III4=True),
    "ky_quy_lu_hanh": Cua(
        CHUA_CO,
        "Hồ sơ giấy phép lữ hành: số tiền ký quỹ, NGÂN HÀNG VÀ TÀI KHOẢN GIỮ, ngày phong toả và "
        "ngày giải toả", "Hành chính – Pháp chế", ngoai_bang_III4=True),
}


def dong_chua_co_nguon() -> list[str]:
    """Dòng đã khai cửa nhưng NGUỒN còn 'Chưa có' – màn hình còn phải dựng.

    Danh sách VIỆC, không phải danh sách lỗi. Nó cạn dần khi các cửa được dựng xong.
    """
    return [ma for ma, c in CUA_NHAP.items() if not c.da_co_nguon()]


def dong_thieu_cua() -> list[str]:
    """Dòng của bảng mà KHÔNG có ai nhập – danh sách này phải RỖNG.

    Dòng tự tính (hai dòng TỔNG, SỐ DƯ DỰ KIẾN, THIẾU SO VỚI DỰ PHÒNG) không cần cửa. "Tiền khả
    dụng đầu kỳ" thì CÓ cần, dù cũng nằm ở phía số dư: nó là số người ta chốt và xác nhận trên màn
    hình đối soát ngân hàng, không phải số cộng ra được.
    """
    return [d.ma for d in CAC_DONG if not d.tu_tinh and d.ma not in CUA_NHAP]


def kiem_khop_voi_so_nghia_vu() -> list[str]:
    """Nhóm có trong sổ nghĩa vụ mà THIẾU trên bảng trình bày. Phải RỖNG.

    Đây là hàng rào chống lặp lại chuyện 11/9: hai bên khai hai danh sách rồi lệch nhau. Nay bảng
    nhập mã từ sổ, nên lệch chỉ còn xảy ra nếu ai đó thêm nhóm vào sổ mà quên thêm dòng vào bảng –
    và lúc ấy bảng lãnh đạo sẽ thiếu một dòng mà không ai biết.
    """
    return sorted(set(NHOM) - set(DONG))


def ghi_nho_khop_voi_so() -> bool:
    """Hai dòng ghi nhớ trên bảng phải đúng bằng hai nhóm mang cờ ghi nhớ trong sổ."""
    return {d.ma for d in CAC_DONG if d.phia == GHI_NHO} == set(NHOM_GHI_NHO)


def kiem_chua_tach_duoc() -> list[str]:
    """Mã khai trong CHUA_TACH_DUOC mà KHÔNG nằm ngoài tầm nhóm của vai trò xem một phần. Phải RỖNG.

    Khai một dòng ĐANG TRONG TẦM vào đây thì `xem_duoc()` cho hiện (không đổi gì, nó vốn đã hiện)
    nhưng `an_gia_tri()` trả False – tức khai xong mà không có tác dụng, và người khai tưởng đã
    giấu được con số. Câu này bắt đúng cái tưởng ấy.
    """
    ngoai_tam = set(NHOM) - nhom_duoc_xem("tgd")
    return sorted(set(CHUA_TACH_DUOC) - ngoai_tam)


def kiem_ghi_chu_lan_sang() -> list[str]:
    """Mã khai trong GHI_CHU_LAN_SANG mà lại bị ẩn số. Phải RỖNG.

    Hai bảng nói hai việc ngược nhau: một bên "dòng này vẫn có số, số hơi rộng", một bên "dòng này
    không có số". Một mã nằm cả hai chỗ là một câu tự mâu thuẫn hiện lên màn hình lãnh đạo.
    """
    return sorted(ma for ma in GHI_CHU_LAN_SANG if an_gia_tri("tgd", ma))
