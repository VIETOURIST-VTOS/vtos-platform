# -*- coding: utf-8 -*-
"""TC-27 · Hai quyết định của anh Tuấn ngày 14/9/2026.

1. CỬA SỔ ĐIỀU HÀNH LẤY THEO BẢN VẼ — 14 NGÀY.
   Máy chủ đang lọc 21 ngày còn bản vẽ ghi 14, nên màn hình phải in cả hai con số ra cho khỏi ai
   đọc nhầm. In cả hai thì chẳng ai biết tin con nào — đó không phải minh bạch, đó là đùn quyết
   định sang người đọc. Nay MỘT con số, khai ở máy chủ, màn hình đọc chứ không gõ lại.

2. NÚT "XUẤT EXCEL" NỐI THẬT.
   Trước vòng này bấm vào chỉ hiện "đang xây dựng". Một nút hứa rồi không làm còn tệ hơn không có
   nút: lần sau người dùng không tin nút nào nữa.

   Bộ dựng tệp nhận ĐÚNG gói mà màn hình đang đọc, không truy vấn lại — truy vấn lại là mở đường
   cho Excel và màn hình nói khác nhau, và lúc lệch thì không ai biết tin bên nào. SEC-02 vẫn nằm
   ở máy chủ: gói vào đã cắt theo vai, bộ dựng tệp không biết vai là gì và không được biết.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DASH = GOC / "backend" / "app" / "services" / "dashboard.py"
XL = GOC / "backend" / "app" / "services" / "xuat_dong_tien_excel.py"
API = GOC / "backend" / "app" / "api" / "v1" / "dong_tien.py"
TRANG = GOC / "web" / "app" / "page.tsx"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
# TC-63 (18/9/2026) · Nút Xuất Excel theo bảng bốn mốc sang components/BangBonMoc.tsx khi anh Tuấn
# chốt "chuyển qua gộp với dòng tiền". Nút điều khiển CÁI BẢNG nên nó đi cùng bảng; luật ở đây —
# "không có nút hứa suông, nút phải gọi cửa tải tệp thật" — không đổi một chữ.
BANG = GOC / "web" / "components" / "BangBonMoc.tsx"
APITS = GOC / "web" / "lib" / "api.ts"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich_py(s: str) -> str:
    s = re.sub(r'"""(?:.|\n)*?"""', "", s)
    return re.sub(r"^\s*#.*$", "", s, flags=re.M)


def _bo_chu_thich_tsx(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", "", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", "", s)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


# ───────────────────────────── 1 · MỘT CON SỐ, KHÔNG HAI ─────────────────────────────

def test_may_chu_lay_14_ngay_theo_ban_ve():
    s = _doc(DASH)
    assert "SO_NGAY_SAP_KHOI_HANH = 14" in s, "Cửa sổ ngày khởi hành phải là 14 theo bản vẽ V1.4."
    ma = _bo_chu_thich_py(s)
    assert "timedelta(days=21)" not in ma, "Câu truy vấn vẫn còn cửa sổ 21 ngày."
    assert "timedelta(days=SO_NGAY_SAP_KHOI_HANH)" in ma, (
        "Câu truy vấn phải đọc hằng, không gõ lại con số — gõ lại là hai chỗ, và hai chỗ thì lệch."
    )


def test_may_chu_tra_so_ngay_ra_cho_man_hinh():
    ma = _bo_chu_thich_py(_doc(DASH))
    assert 'sec["sap_khoi_hanh_so_ngay"] = SO_NGAY_SAP_KHOI_HANH' in ma, (
        "Máy chủ phải trả số ngày ra để màn hình đọc, thay vì để màn hình gõ lại."
    )


def test_man_hinh_doc_chu_khong_go_lai():
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "21 ngày" not in ma, "Màn hình vẫn còn con số 21 gõ tay."
    # SỬA 22/10/2026 (TQ-1): ô «Sắp khởi hành» chuyển vào mục Vận hành — trường máy chủ đọc trong
    # `docDuLieuVanHanh`, in ra ở ô. Luật y nguyên: số ngày lấy từ máy chủ, không gõ tay.
    vh = _bo_chu_thich_tsx(_doc(GOC / "web" / "components" / "KhoiVanHanh.tsx"))
    assert "21 ngày" not in vh, "Mục Vận hành còn con số 21 gõ tay."
    assert "sap_khoi_hanh_so_ngay" in vh, "Màn hình chưa đọc số ngày từ máy chủ."
    assert "{d.so_ngay_kh} ngày tới" in vh, "Ô Sắp khởi hành phải in số ngày lấy từ máy chủ."


def test_bo_cau_in_ca_hai_con_so():
    """Câu 'bản vẽ ghi 14 · máy chủ tính 21' đã hết lý do tồn tại — còn nó là còn gợi ý rằng hai
    nơi vẫn đang lệch nhau."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "máy chủ đang tính" not in ma, "Vẫn còn câu đối chiếu hai con số trên màn hình."


# ───────────────────────────── 2 · XUẤT EXCEL THẬT ─────────────────────────────

def test_khong_con_nut_hua_suong():
    ma = _bo_chu_thich_tsx(_doc(BANG))
    assert "đang xây dựng" not in ma, "Nút Xuất Excel vẫn chỉ hiện câu 'đang xây dựng'."
    assert "taiTep(" in ma, "Nút Xuất Excel chưa gọi cửa tải tệp."


def test_co_cua_tai_tep_gui_kem_the_dang_nhap():
    """Thẻ <a href> và window.open KHÔNG gửi được tiêu đề Authorization, nên máy chủ trả 401 và
    người dùng bị đá về trang đăng nhập ngay giữa lúc bấm nút tải."""
    s = _doc(APITS)
    assert "export async function taiTep" in s
    i = s.index("export async function taiTep")
    than = s[i:s.index("export async function login")]
    assert "Authorization" in than, "Cửa tải tệp không đính thẻ đăng nhập."
    assert "revokeObjectURL" in than, (
        "Không thu hồi URL tạm — mỗi lần bấm nút giữ lại một bản sao của tệp trong bộ nhớ."
    )
    assert "Content-Disposition" in than, "Tên tệp phải lấy từ máy chủ, không đặt ở trình duyệt."


def test_excel_dung_tu_dung_goi_cua_man_hinh():
    s = _doc(API)
    i = s.index('@router.get("/khung/{company_id}/excel")')
    than = s[i:i + 2200]
    assert "KHUNG.ghep(u.role" in than, (
        "Điểm nối Excel phải dùng lại đúng đường của màn hình (bang_bon_moc + ghep), không truy vấn "
        "riêng — hai đường là hai thời điểm, và lệch nhau là chuyện sớm muộn."
    )
    assert "XL.dung_tep(k)" in than


def test_excel_co_nhat_ky():
    """v1.1 §IV.3 đòi nút xuất Excel có nhật ký: một tệp dòng tiền rời khỏi hệ thống là một việc
    phải trả lời được câu 'ai lấy, lúc nào, của pháp nhân nào'."""
    s = _doc(API)
    i = s.index('@router.get("/khung/{company_id}/excel")')
    than = s[i:i + 2200]
    assert 'R.audit(' in than and '"xuat_excel_dong_tien"' in than, "Thiếu dòng nhật ký khi xuất."
    assert "db.commit()" in than, "Ghi nhật ký mà không commit thì nhật ký không được lưu."


def test_bo_dung_tep_khong_biet_vai_tro():
    """SEC-02: gói vào đã cắt theo vai. Bộ dựng tệp mà biết vai là nó có thể bày ra dòng màn hình
    đã giấu — nên trong tệp không được có một câu so sánh vai trò nào."""
    ma = _bo_chu_thich_py(_doc(XL))
    for vai in ('"chutich"', '"tgd"', '"ketoan"', '"bks"', '"ptgd'):
        assert vai not in ma, f"Bộ dựng tệp Excel đang xét vai trò {vai} — SEC-02 bắt đỏ."


def test_excel_giu_luat_rong_khac_khong():
    """Ô chưa có nguồn ghi CHỮ. Để trắng thì mở Excel bấm Sum một cột là nó cộng như thể ô ấy bằng
    0 — đúng cái nhầm mà cả hệ thống đang chống."""
    s = _doc(XL)
    assert 'CHUA_CO = "Chưa có nguồn"' in s
    ma = _bo_chu_thich_py(s)
    i = ma.index("def _o_tien")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert "o.value = CHUA_CO" in than, "Ô rỗng phải ghi chữ, không để trắng và không ghi 0."
    assert "= 0" not in than, "Có chỗ lấy 0 thay cho ô rỗng trong bộ dựng tệp."


GOI_THU = {
    "xem_duoc": True, "vai_tro": "chutich", "phap_nhan": "VTD",
    "cau_pham_vi": "Bảng này gồm toàn bộ dòng tiền của pháp nhân đang xem.",
    "cot": [
        {"ma": "7n", "ten": "1 tuần", "tu_hien": "14-09-2026",
         "tu_hien_khoang": "14-09-2026", "den_hien": "20-09-2026"},
        {"ma": "14n", "ten": "2 tuần", "tu_hien": "14-09-2026",
         "tu_hien_khoang": "21-09-2026", "den_hien": "27-09-2026"},
    ],
    "dong": [
        {"ma": "tien_kha_dung_dau_ky", "ten": "Tiền khả dụng đầu kỳ", "mot_moc": True,
         "so_mot_moc": None, "la_dong_chay": False, "trang_thai": "con_thieu",
         "nhan_trang_thai": "Còn thiếu", "nguyen_nhan": "Chưa ai chốt số dư",
         "bo_phan": "Kế toán", "nguon": "Tài khoản ngân hàng", "cua": "Màn hình đối soát"},
        {"ma": "tong_thu", "ten": "TỔNG TIỀN DỰ KIẾN THU", "tu_tinh": True, "la_dong_chay": True,
         "so": {"7n": None, "14n": None}, "so_khoang": {"7n": None, "14n": None},
         "trang_thai": "con_thieu", "nhan_trang_thai": "Còn thiếu"},
        {"ma": "tra_ncc", "ten": "Trả nhà cung cấp", "la_dong_chay": True,
         "so": {"7n": 108_000_000, "14n": 108_000_000},
         "so_khoang": {"7n": 108_000_000, "14n": 0},
         "trang_thai": "day_du", "nhan_trang_thai": "Đầy đủ", "nguyen_nhan": "",
         "bo_phan": "Điều hành + Kế toán", "nguon": "Đặt dịch vụ NCC", "cua": "Lịch thanh toán"},
    ],
    "ten_dong_thuan": "Dòng tiền thuần trong khoảng",
    "dong_tien_thuan": {"7n": None, "14n": None},
    "dong_tien_thuan_khoang": {"7n": None, "14n": None},
    "tom_tat_trang_thai": {"day_du": 1, "chua_doi_soat": 0, "con_thieu": 2},
    "cong_bon_cot_la_sai": "Bốn cột LŨY KẾ chồng lên nhau – cộng lại là sai.",
    "cong_bon_cot_khi_xem_khoang": "Xem theo từng khoảng thì bốn cột RỜI NHAU.",
}


def _dung_thu():
    """Dựng thật một tệp rồi mở ra đọc. Soi mã nguồn chỉ biết được mã có gọi đúng hàm hay không;
    chỉ có dựng thật mới biết tệp mở lên nhìn ra cái gì."""
    import pytest
    try:
        from app.services import xuat_dong_tien_excel as X
        from openpyxl import load_workbook
    except ImportError as e:                      # máy không có đủ gói thì bỏ qua, không đỏ giả
        pytest.skip(f"không nạp được bộ dựng tệp: {e}")
    import io
    return X, load_workbook(io.BytesIO(X.dung_tep(GOI_THU)))


def test_excel_dung_that_ra_du_ba_trang():
    """Xuất mỗi kiểu đang xem thì hai người xuất hai lúc ra hai tệp khác nhau cùng tên."""
    _, wb = _dung_thu()
    assert wb.sheetnames == ["Lũy kế", "Trong từng khoảng", "Nguồn số"], wb.sheetnames


def test_excel_hai_trang_ra_hai_bo_so_dung():
    """Phép thử đắt giá nhất của vòng này: mở tệp ra và ĐỌC SỐ.

    Trả nhà cung cấp hiện cùng một số ở cả hai cột luỹ kế; ở trang theo khoảng phải ra số ấy ở
    khoảng đầu rồi 0 — cả khoản rơi trọn trong tuần đầu. Trang luỹ kế mà in 0 ở cột hai là phép trừ
    đã chạy nhầm trang.
    """
    _, wb = _dung_thu()
    ly, kh = wb["Lũy kế"], wb["Trong từng khoảng"]
    hang = None
    for r in range(1, 20):
        if ly.cell(r, 1).value == "Trả nhà cung cấp":
            hang = r
            break
    assert hang, "Không tìm thấy dòng Trả nhà cung cấp trong tệp."
    assert [ly.cell(hang, 2).value, ly.cell(hang, 3).value] == [108_000_000, 108_000_000]
    assert [kh.cell(hang, 2).value, kh.cell(hang, 3).value] == [108_000_000, 0]


def test_excel_o_rong_ghi_chu_chu_khong_ghi_0():
    _, wb = _dung_thu()
    ly = wb["Lũy kế"]
    for r in range(1, 20):
        if ly.cell(r, 1).value == "TỔNG TIỀN DỰ KIẾN THU":
            assert ly.cell(r, 2).value == "Chưa có nguồn", (
                "Ô chưa có nguồn phải ghi chữ — để trắng thì bấm Sum một cột là Excel cộng như thể "
                "ô ấy bằng 0."
            )
            return
    raise AssertionError("Không tìm thấy dòng tổng thu trong tệp.")


def test_excel_trang_nguon_so_khong_bia_han():
    _, wb = _dung_thu()
    ws = wb["Nguồn số"]
    dau = [ws.cell(6, i).value for i in range(1, 8)]
    assert dau[0] == "Dòng tiền" and dau[6] == "Hạn xử lý", dau
    # Dòng tự cộng KHÔNG có cửa nhập nên không nằm trong danh sách đi đòi nguồn.
    ten = [ws.cell(r, 1).value for r in range(7, 12)]
    assert "TỔNG TIỀN DỰ KIẾN THU" not in ten, "Dòng tự cộng không được nằm ở trang Nguồn số."
    # HẠN XỬ LÝ — lời canh giữ nguyên qua hai vòng, cách giữ lời thì đổi.
    #
    # TC-27 (14/9 sáng): hệ thống chưa có chỗ nào ghi hạn, nên ô này ghi "chưa đặt".
    # TC-29 (14/9 chiều): anh Tuấn chốt hạn 24 giờ; `han_dong_tien` ghi hạn xuống lúc LƯỢT QUÉT phát
    # hiện, và gói đi vào bộ dựng tệp mang theo `han_hien` / `qua_han` / `han_chua_quet`.
    #
    # GOI_THU ở đây KHÔNG mang ba trường ấy — đúng như một gói do vai chưa quét tới trả về — nên ô
    # phải ra "—". Điều phép thử canh vẫn là điều cũ: bộ dựng tệp KHÔNG được tự nghĩ ra một hạn.
    assert ws.cell(7, 7).value == "—", (
        "Gói không mang hạn thì ô phải để '—'. Ra một ngày giờ nghĩa là bộ dựng tệp đã tự tính hạn."
    )
    # Và khi gói CÓ hạn thì ô phải nói đúng hạn ấy, kèm dấu quá hạn đọc được khi lướt mắt.
    import io
    from openpyxl import load_workbook
    from app.services import xuat_dong_tien_excel as X2
    goi = {**GOI_THU, "dong": [{**d} for d in GOI_THU["dong"]]}
    goi["dong"][0].update(han_hien="12-09-2026 09:00", qua_han=True, tre_hien="trễ 2 ngày")
    o = load_workbook(io.BytesIO(X2.dung_tep(goi)))["Nguồn số"].cell(7, 7).value
    assert "12-09-2026 09:00" in o and "QUÁ HẠN" in o and "trễ 2 ngày" in o, o


def test_cau_nhac_cong_bon_cot_di_theo_kieu_xem_trong_excel():
    """Tệp Excel đi xa khỏi màn hình, nên câu nhắc phải đi theo nó — và phải ĐÚNG kiểu xem của
    từng trang: luỹ kế thì cộng bốn cột là sai, theo khoảng thì cộng bốn cột lại đúng."""
    ma = _bo_chu_thich_py(_doc(XL))
    assert "cong_bon_cot_khi_xem_khoang" in ma and "cong_bon_cot_la_sai" in ma


def test_ten_tep_mang_phap_nhan_va_ngay():
    ma = _bo_chu_thich_py(_doc(XL))
    i = ma.index("def ten_tep")
    than = ma[i:]
    assert "phap_nhan" in than and "%d-%m-%Y" in than, (
        "Tên tệp phải nói rõ của pháp nhân nào và tính đến ngày nào — người nhận qua Zalo hay email "
        "không có màn hình bên cạnh để đối chiếu."
    )


# ───────────── 4 · LỖI 500 TRÊN TRANG THẬT 14/9/2026 · HÌNH DẠNG PHÁP NHÂN ─────────────
#
# Nút Xuất Excel vừa lên trang thật là trả 500 ngay lần bấm đầu. Bộ dựng tệp ĐOÁN `phap_nhan` là
# một chuỗi mã; máy chủ trả một ĐỐI TƯỢNG {id, ma, ten}. Nhét đối tượng ấy vào tên tệp ra một chuỗi
# có dấu ngoặc, dấu nháy và chữ có dấu — mà tiêu đề Content-Disposition chỉ nhận latin-1, nên máy
# chủ ném lỗi. Bốn phép thử dưới đây khoá cả ba hình dạng lại, để lần sau làn kia có đổi thì đỏ ở
# đây chứ không đỏ ở tay người bấm nút.

PHAP_NHAN_THAT = {"id": 8, "ma": "BUFFALO", "ten": "Công ty Cổ phần Việt Nam Buffalotours"}


def _bo_dung():
    import pytest
    try:
        from app.services import xuat_dong_tien_excel as X
    except ImportError as e:
        pytest.skip(f"không nạp được bộ dựng tệp: {e}")
    return X


def test_ten_tep_di_duoc_vao_tieu_de_http_khi_phap_nhan_la_doi_tuong():
    """Phép thử đúng bằng cái đã gãy: dựng tên tệp rồi ép qua latin-1 như tầng HTTP vẫn làm."""
    X = _bo_dung()
    ten = X.ten_tep({**GOI_THU, "phap_nhan": PHAP_NHAN_THAT})
    ten.encode("latin-1")                        # gãy ở đây nghĩa là điểm nối sẽ trả 500
    assert "BUFFALO" in ten, f"Tên tệp mất mã pháp nhân: {ten}"
    assert not set(ten) & set("{}'\" ,:"), f"Tên tệp còn ký tự không đi được vào tiêu đề: {ten}"


def test_ten_tep_khong_gay_voi_ca_ba_hinh_dang():
    """Đối tượng · chuỗi · thiếu hẳn. Làn kia đổi hình dạng lúc nào không báo, nên nhận cả ba."""
    X = _bo_dung()
    for pn in (PHAP_NHAN_THAT, "VTD", None, {"id": 3}, ""):
        ten = X.ten_tep({**GOI_THU, "phap_nhan": pn})
        ten.encode("latin-1")
        assert ten.endswith(".xlsx") and "VTOS_dong_tien_" in ten, (pn, ten)


def test_thieu_phap_nhan_van_ra_ten_doc_duoc():
    """Thiếu nguồn thì tên tệp lùi về VTOS — KHÔNG ra tên cụt kiểu 'VTOS_dong_tien__14-09-2026'."""
    X = _bo_dung()
    assert X.ten_tep({}) == f"VTOS_dong_tien_VTOS_{__import__('datetime').date.today():%d-%m-%Y}.xlsx"


def test_dau_trang_in_ten_day_du_cua_phap_nhan():
    """Tệp đi qua Zalo hay email, không có màn hình bên cạnh — nên phải tự nói nó của công ty nào.
    Mã 'BUFFALO' hợp cho tên tệp, nhưng người mở tệp cần đọc tên đầy đủ."""
    import pytest, io
    X = _bo_dung()
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        pytest.skip(f"không có openpyxl: {e}")
    wb = load_workbook(io.BytesIO(X.dung_tep({**GOI_THU, "phap_nhan": PHAP_NHAN_THAT})))
    dau = wb["Lũy kế"].cell(1, 1).value or ""
    assert "Công ty Cổ phần Việt Nam Buffalotours" in dau, dau
