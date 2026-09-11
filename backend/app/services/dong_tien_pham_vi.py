# -*- coding: utf-8 -*-
"""SEC-02 + CF-07 · Danh mục dòng của khối DÒNG TIỀN: ai xem được dòng nào, và dòng nào có cửa nhập.

TÊN DÒNG VÀ THỨ TỰ lấy nguyên từ bảng ở mục III của đề xuất giao diện v1.1 (11/9/2026). Không đặt
lại tên cho gọn: bảng ấy là thứ Chủ tịch và Tổng giám đốc đọc, và một dòng đổi tên giữa tài liệu
với màn hình là một lần hai bên họp về hai thứ khác nhau mà tưởng là một.

Chủ tịch chốt ba điều ngày 11/9/2026, cả ba đều là điều mà làm sai thì KHÔNG AI NHÌN RA:

  (1) CHỦ TỊCH xem TẤT CẢ các dòng tài chính.
  (2) TỔNG GIÁM ĐỐC CHỈ xem tài chính của hoạt động kinh doanh TOUR + XE.
  (3) CÁCH A: bảng của Tổng giám đốc KHÔNG có "Tiền khả dụng đầu kỳ", KHÔNG có "SỐ DƯ DỰ KIẾN CUỐI
      KHOẢNG", KHÔNG có "THIẾU SO VỚI MỨC DỰ PHÒNG". Dòng đáy mang tên
      "Dòng tiền thuần từ hoạt động tour và xe" – KHÔNG BAO GIỜ gọi là "số dư".

Vì sao (3) quan trọng hơn nó nghe: một bảng đã bị lọc mất dòng vay, dòng thuế và dòng lãi mà dòng
đáy vẫn đề chữ "số dư" thì con số ấy KHÔNG SAI THEO KIỂU DỄ THẤY – nó trông như đúng. Người số hai
của tập đoàn đọc "số dư cuối tháng: 4 tỷ", yên tâm duyệt một khoản chi, trong khi phần bị giấu đi
có một kỳ trả gốc 6 tỷ. Không dòng nào trên màn hình sai cả; chỉ cái TÊN của dòng đáy nói dối.

Nên ở tệp này, phạm vi xem và TÊN DÒNG ĐÁY đi cùng nhau, do cùng một hàm quyết định. Tách chúng ra
hai chỗ là mở đường cho một lần sửa giao diện làm gãy đúng chỗ này.

Nguyên tắc ĐÓNG MẶC ĐỊNH: vai trò nào không được khai trong BANG_QUYEN thì KHÔNG thấy gì. Mở mặc
định rồi liệt kê người bị cấm là kiểu khai mà mỗi lần thêm một vai trò mới là một lần rò rỉ, và
không có gì kêu lên.

CF-07 nằm ở nửa sau tệp: mỗi dòng phải có một CỬA NHẬP hoặc CỬA TẢI và một bộ phận chịu trách
nhiệm nhập. Dòng ghi "Chưa có" ở cột nguồn là việc phải dựng thêm màn hình – không phải việc bỏ
trống hoặc điền 0.
"""
from app.services.lam_tron_tien import bang_tien, o_tien  # noqa: F401  (dùng ở tầng dựng bảng)

# Mảng hoạt động của một dòng. Đây là thứ quyết định Tổng giám đốc có thấy dòng ấy hay không.
TOUR_XE = "tour_xe"          # kinh doanh tour và đội xe – phần TGĐ điều hành
TAI_CHINH = "tai_chinh"      # vay, lãi, thuế, ký quỹ – phần Chủ tịch quyết
CA_HAI = "ca_hai"            # có phần thuộc tour–xe, có phần không: phải tách theo từng bản ghi
MOI_VAI = "moi_vai"          # dòng ai mở được khối này cũng thấy (hai dòng TỔNG)

# `tu_tinh` là chuyện KHÁC HẲN với `mang`, và gộp hai thứ ấy làm một là chỗ đã suýt hỏng: "dòng
# này tính ra được" không nói gì về "ai được xem dòng này". Dòng TỔNG tự tính và ai cũng thấy;
# dòng SỐ DƯ DỰ KIẾN cũng tự tính nhưng CHỈ Chủ tịch thấy. Một cột không nói được cả hai.

# Phía của dòng trong bảng.
VAO, RA, GHI_NHO, SO_DU, TONG = "vao", "ra", "ghi_nho", "so_du", "tong"


class Dong:
    """Một dòng của bảng dòng tiền.

    `ly_do` bắt buộc và phải nói VÌ SAO mảng ấy, không phải chép lại tên dòng. Một dòng khai
    mang="tai_chinh" mà không nói được vì sao thì rất có thể nó chỉ đang bị xếp nhầm.
    """

    def __init__(self, ma: str, ten: str, phia: str, mang: str, ly_do: str,
                 tu_tinh: bool = False):
        self.ma, self.ten, self.phia, self.mang, self.ly_do = ma, ten, phia, mang, ly_do
        # tu_tinh = cộng ra từ dòng khác, nên KHÔNG có cửa nhập. Bắt nó có cửa nhập tức là cho
        # phép gõ đè lên một kết quả tính được – chỗ ấy là chỗ số liệu bắt đầu nói khác sổ.
        self.tu_tinh = tu_tinh


# =============================================================================================
# Danh mục dòng – NGUYÊN VĂN VÀ ĐÚNG THỨ TỰ bảng mục III của v1.1
# =============================================================================================
CAC_DONG = [
    Dong("tien_kha_dung_dau_ky", "Tiền khả dụng đầu kỳ", SO_DU, TAI_CHINH,
         "gồm cả tiền từ vay và trừ đi phần không phải của mình; đặt con số toàn cảnh ấy lên một "
         "bảng đã lọc là cho một cái mốc toàn cảnh làm chuẩn cho một bảng không toàn cảnh"),

    Dong("tong_thu", "TỔNG TIỀN DỰ KIẾN THU", TONG, MOI_VAI,
         "cộng từ chính tập dòng thu mà vai trò ấy nhìn thấy, không phải cộng toàn cảnh rồi mới "
         "che bớt – che sau khi cộng thì con số tổng vẫn mang phần đã bị che", tu_tinh=True),
    Dong("thu_khach", "Thu khách / booking / hợp đồng", VAO, TOUR_XE,
         "tiền khách nộp cho chuyến và dịch vụ, chính là doanh thu của hoạt động TGĐ điều hành"),
    Dong("thu_cong_no_khac", "Thu công nợ khác", VAO, TOUR_XE,
         "công nợ sinh ra từ chuyến đã đi và dịch vụ đã đặt – cùng một hoạt động kinh doanh"),
    Dong("giai_ngan_vay", "Giải ngân vay đã ký khế ước", VAO, TAI_CHINH,
         "tiền vay không phải tiền kiếm được; trộn nó vào dòng kinh doanh làm một tháng lỗ trông "
         "như một tháng có tiền, và đó đúng là lúc người ta duyệt chi"),

    Dong("tong_chi", "TỔNG TIỀN PHẢI THANH TOÁN", TONG, MOI_VAI,
         "cộng từ chính tập dòng chi mà vai trò ấy nhìn thấy; cùng lý do với dòng tổng thu",
         tu_tinh=True),
    Dong("tra_ncc", "Trả nhà cung cấp", RA, TOUR_XE,
         "giá vốn của chuyến và của xe, cùng hoạt động với dòng thu của khách"),
    Dong("hoan_tra_khach", "Hoàn / trả khách hàng", RA, TOUR_XE,
         "khoản trả ngược cho khách của chính chuyến ấy, phải đứng cạnh dòng thu mới đọc được"),
    Dong("hoa_hong", "Hoa hồng đại lý và cộng tác viên", RA, TOUR_XE,
         "chi phí bán hàng của chuyến, biến động theo doanh thu của hoạt động tour"),
    Dong("tra_goc_vay", "Trả gốc vay ngân hàng", RA, TAI_CHINH,
         "kỳ trả gốc là nghĩa vụ tài chính, không do hoạt động kinh doanh sinh ra và TGĐ không "
         "điều tiết được – nhưng nó rút tiền mặt mạnh nhất trong cả bảng"),
    Dong("lai_phi_ngan_hang", "Lãi và phí ngân hàng", RA, TAI_CHINH,
         "giá của khoản vay, đi liền với kỳ trả gốc; tách khỏi nó là đọc thiếu một nửa chi phí vốn"),
    Dong("luong_bhxh", "Lương, bảo hiểm và liên quan", RA, CA_HAI,
         "TGĐ thấy phần bộ phận tour và đội xe; phần khối văn phòng tập đoàn và ban điều hành "
         "thuộc phần Chủ tịch quyết – tách theo bộ phận, chưa tách được thì chưa đưa xuống"),
    Dong("thue_nghia_vu", "Thuế và nghĩa vụ khác", RA, TAI_CHINH,
         "nghĩa vụ với ngân sách tính trên kết quả của cả pháp nhân, không thuộc một hoạt động"),
    Dong("van_hanh", "Vận hành và phải trả khác", RA, CA_HAI,
         "phần của chuyến và của xe thuộc TGĐ; vận hành trụ sở và chi phí chung tập đoàn thì không"),

    Dong("so_du_du_kien_cuoi_khoang", "SỐ DƯ DỰ KIẾN CUỐI KHOẢNG", SO_DU, TAI_CHINH,
         "kết quả của đầu kỳ cộng mọi dòng; thiếu một dòng nào thì con số này sai mà không ai thấy",
         tu_tinh=True),
    Dong("thieu_so_voi_muc_du_phong", "THIẾU SO VỚI MỨC DỰ PHÒNG", SO_DU, TAI_CHINH,
         "ngưỡng dự phòng chốt trên TOÀN CẢNH bằng hai chữ ký; so một phần với một ngưỡng toàn "
         "cảnh ra một con số không có nghĩa, mà lại trông như một con số có nghĩa", tu_tinh=True),

    Dong("ghi_nho_thu_ho", "Ghi nhớ — Tiền thu hộ khách (KHÔNG thuộc tiền khả dụng)", GHI_NHO,
         TOUR_XE,
         "nằm trong tài khoản nhưng là tiền của khách; phải nhìn thấy để không tiêu nhầm, và phải "
         "đứng ngoài phép cộng để không tự cho mình thêm tiền"),
    Dong("ghi_nho_ky_quy", "Ghi nhớ — Ký quỹ giấy phép lữ hành (KHÔNG thuộc tiền khả dụng)",
         GHI_NHO, TAI_CHINH,
         "khoản bị phong toả theo giấy phép lữ hành, là nghĩa vụ pháp lý của từng pháp nhân"),
]

DONG = {d.ma: d for d in CAC_DONG}


# =============================================================================================
# Bảng quyền – ĐÓNG MẶC ĐỊNH
# =============================================================================================
TOAN_CANH = "toan_canh"      # thấy mọi dòng
TOUR_XE_THOI = "tour_xe"     # chỉ phần tour và xe

BANG_QUYEN = {
    "chutich": TOAN_CANH,
    "ketoan": TOAN_CANH,      # người lập bảng, và phải đối chiếu được với sổ quỹ
    "bks": TOAN_CANH,         # kiểm soát mà chỉ xem được một phần thì không kiểm soát gì
    "tgd": TOUR_XE_THOI,
}
# Hai Phó Tổng giám đốc KHÔNG có trong bảng – nghĩa là không thấy khối này. Khai vắng mặt chứ không
# khai "cấm": danh sách cấm phải sửa mỗi lần thêm vai trò mới, danh sách cho phép thì không.

# Tên dòng đáy đi LIỀN với phạm vi. Xem một phần mà dòng đáy đề "số dư" là một con số trông như đúng.
TEN_DONG_DAY = {
    TOAN_CANH: "SỐ DƯ DỰ KIẾN CUỐI KHOẢNG",
    TOUR_XE_THOI: "Dòng tiền thuần từ hoạt động tour và xe",
}

# Bốn ô cảnh báo trên đầu khối, và ai đọc được ô nào.
CANH_BAO = {
    "phai_tra_qua_han": (TOUR_XE_THOI, "Phải trả quá hạn",
                         "TGĐ thấy phần nhà cung cấp của tour và xe – đó là việc ông ấy xử lý được"),
    "phai_tra_7_ngay": (TOUR_XE_THOI, "Phải trả trong 7 ngày tới",
                        "cùng lý do: là lịch phải xoay tiền của chính hoạt động ông ấy điều hành"),
    "ngay_dau_thieu_tien": (TOAN_CANH, "Ngày đầu tiên dự kiến thiếu tiền",
                            "tính trên TOÀN CẢNH gồm cả kỳ trả gốc và thuế; tính trên một phần sẽ "
                            "ra một ngày MUỘN HƠN sự thật – tức là báo yên khi không yên"),
    "muc_thieu_lon_nhat": (TOAN_CANH, "Mức thiếu lớn nhất",
                           "cùng lý do, và sai theo cùng một chiều: bao giờ cũng nhẹ hơn thực tế"),
}


def muc_xem(vai_tro: str) -> str | None:
    """Mức xem khối dòng tiền của một vai trò. None = không thấy khối này.

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
    return DONG[ma_dong].mang in (TOUR_XE, CA_HAI, MOI_VAI)


def cac_dong_cho(vai_tro: str) -> list[Dong]:
    """Danh sách dòng của bảng, đã lọc. Thứ tự giữ nguyên bảng của v1.1 – không xếp lại theo vai."""
    return [d for d in CAC_DONG if xem_duoc(vai_tro, d.ma)]


def dong_de_cong(vai_tro: str, phia: str) -> list[str]:
    """Mã các dòng dùng để cộng ra một dòng TỔNG, theo đúng tập dòng vai trò ấy nhìn thấy.

    Đây là chỗ dễ hỏng nhất của dòng tổng: cộng toàn cảnh rồi mới che bớt thì con số tổng vẫn mang
    phần đã bị che. Phải cộng TỪ tập đã lọc.
    """
    return [d.ma for d in cac_dong_cho(vai_tro) if d.phia == phia]


def ten_dong_day(vai_tro: str) -> str:
    """Tên dòng đáy. Hàm này và cac_dong_cho() phải luôn được gọi cùng nhau."""
    m = muc_xem(vai_tro)
    if m is None:
        return ""
    return TEN_DONG_DAY[m]


def cac_canh_bao_cho(vai_tro: str) -> list[dict]:
    m = muc_xem(vai_tro)
    if m is None:
        return []
    return [{"ma": ma, "nhan": nhan} for ma, (can, nhan, _) in CANH_BAO.items()
            if m == TOAN_CANH or can == TOUR_XE_THOI]


def khung_bang(vai_tro: str) -> dict:
    """Khung bảng dòng tiền cho một vai trò: dòng nào, dòng đáy tên gì, ô cảnh báo nào.

    KHÔNG có số ở đây – số do tầng dựng bảng điền vào đúng khung này. Trả khung và số từ hai chỗ
    khác nhau là để một hôm nào đó khung thì lọc mà số thì không.
    """
    m = muc_xem(vai_tro)
    if m is None:
        return {"xem_duoc": False, "ly_do": "Vai trò này không mở khối Dòng tiền."}
    return {
        "xem_duoc": True,
        "muc_xem": m,
        "dong": [{"ma": d.ma, "ten": d.ten, "phia": d.phia} for d in cac_dong_cho(vai_tro)],
        "cong_thu": dong_de_cong(vai_tro, VAO),
        "cong_chi": dong_de_cong(vai_tro, RA),
        "ten_dong_day": ten_dong_day(vai_tro),
        "canh_bao": cac_canh_bao_cho(vai_tro),
        "cau_pham_vi": ("Bảng này gồm toàn bộ dòng tiền của pháp nhân đang xem."
                        if m == TOAN_CANH else
                        "Bảng này CHỈ gồm dòng tiền của hoạt động kinh doanh tour và xe. "
                        "Không gồm vay, trả gốc, lãi, thuế và ký quỹ, nên không có dòng số dư."),
    }


# =============================================================================================
# CF-07 · Cửa nhập và chủ quản số liệu cho từng dòng (bảng mục III.4 của v1.1)
# =============================================================================================
# "Chưa có" ở cột nguồn là VIỆC PHẢI DỰNG THÊM MÀN HÌNH, không phải việc bỏ trống hoặc điền 0. Đó
# cũng là ranh giới đã chốt ngày 09/9: hệ thống viết ra CẤU TRÚC và PHÉP TÍNH, còn SỐ thì bộ phận
# nghiệp vụ tự nhập hoặc tự tải. Mỗi con số không có cửa là một việc còn thiếu.
CHUA_CO = "Chưa có"


class Cua:
    def __init__(self, nguon: str, cua: str, bo_phan: str, tu_de_xuat: bool = False):
        self.nguon, self.cua, self.bo_phan, self.tu_de_xuat = nguon, cua, bo_phan, tu_de_xuat

    def da_co_nguon(self) -> bool:
        return not self.nguon.startswith(CHUA_CO)


CUA_NHAP = {
    "tien_kha_dung_dau_ky": Cua(
        "Tài khoản ngân hàng và đối soát SePay",
        "Màn hình đối soát ngân hàng: chốt số dư theo ngày, có người xác nhận", "Kế toán"),
    "thu_khach": Cua(
        "Booking và phiếu thu đã có",
        "Lịch thu theo booking và hợp đồng, có ngày dự kiến thu và mức chắc chắn",
        "Kinh doanh + Kế toán"),
    "thu_cong_no_khac": Cua(
        CHUA_CO, "Màn hình công nợ phải thu có ngày đến hạn", "Kế toán"),
    "giai_ngan_vay": Cua(
        "Khế ước vay đã có", "Lịch giải ngân trong hồ sơ khế ước", "Kế toán"),
    "tra_ncc": Cua(
        "Đặt dịch vụ nhà cung cấp (mới một phần)",
        "Lịch thanh toán theo hợp đồng và đơn đặt dịch vụ, gồm cả nghĩa vụ chưa lập đề nghị chi",
        "Điều hành + Kế toán"),
    "hoan_tra_khach": Cua(
        CHUA_CO, "Phiếu hoàn tiền có ngày cam kết hoàn", "Chăm sóc khách hàng + Kế toán"),
    "hoa_hong": Cua(
        CHUA_CO, "Bảng tính hoa hồng theo kỳ, có ngày chi dự kiến", "Kinh doanh + Kế toán"),
    "tra_goc_vay": Cua(
        "Khế ước vay đã có",
        "Lịch trả gốc – lãi – phí trong hồ sơ khế ước; tách phần lãi ước tính", "Kế toán"),
    "lai_phi_ngan_hang": Cua(
        "Khế ước vay đã có",
        "Lịch trả gốc – lãi – phí trong hồ sơ khế ước; tách phần lãi ước tính", "Kế toán"),
    "luong_bhxh": Cua(
        CHUA_CO + " — hệ thống hiện chưa có hợp đồng lao động nào",
        "Màn hình hợp đồng lao động và lịch chi lương, bảo hiểm theo tháng", "Hành chính – Nhân sự"),
    "thue_nghia_vu": Cua(
        CHUA_CO, "Lịch nghĩa vụ thuế theo pháp nhân và sắc thuế", "Kế toán"),
    "van_hanh": Cua(
        CHUA_CO, "Kế hoạch chi vận hành theo tháng, người phụ trách xác nhận", "Các phòng + Kế toán"),

    # HAI DÒNG DƯỚI KHÔNG CÓ TRONG BẢNG III.4 CỦA v1.1 – bảng ấy có 12 dòng, nhưng bảng dòng tiền ở
    # mục III có thêm hai dòng ghi nhớ. Một dòng trên bảng mà không ai chịu trách nhiệm nhập thì
    # đến ngày vận hành thật nó sẽ hiện "Chưa có" mãi mãi và không ai biết phải hỏi ai. Hai dòng
    # dưới là ĐỀ XUẤT của làn Phân quyền, đánh dấu tu_de_xuat=True, chờ Chủ tịch hoặc TGĐ chốt.
    "ghi_nho_thu_ho": Cua(
        CHUA_CO,
        "Sổ thu hộ – chi hộ theo khách và theo chuyến, chốt số dư thu hộ tại ngày đối soát",
        "Kế toán", tu_de_xuat=True),
    "ghi_nho_ky_quy": Cua(
        CHUA_CO,
        "Hồ sơ giấy phép lữ hành: số tiền ký quỹ, ngân hàng giữ, ngày phong toả và ngày giải toả",
        "Hành chính – Pháp chế", tu_de_xuat=True),
}


def dong_chua_co_nguon() -> list[str]:
    """Dòng đã có cửa được khai nhưng NGUỒN còn 'Chưa có' – tức là màn hình còn phải dựng.

    Đây là danh sách việc, không phải danh sách lỗi. Nó cạn dần khi các cửa nhập được dựng xong.
    """
    return [ma for ma, c in CUA_NHAP.items() if not c.da_co_nguon()]


def dong_thieu_cua() -> list[str]:
    """Dòng của bảng mà KHÔNG có dòng nào trong CUA_NHAP nói ai nhập – danh sách này phải RỖNG.

    Dòng tự tính (hai dòng TỔNG, SỐ DƯ DỰ KIẾN, THIẾU SO VỚI DỰ PHÒNG) không cần cửa. "Tiền khả
    dụng đầu kỳ" thì CÓ cần, dù nó cũng nằm ở phía số dư: nó là số người ta chốt và xác nhận trên
    màn hình đối soát ngân hàng, không phải số cộng ra được.
    """
    return [d.ma for d in CAC_DONG if not d.tu_tinh and d.ma not in CUA_NHAP]
