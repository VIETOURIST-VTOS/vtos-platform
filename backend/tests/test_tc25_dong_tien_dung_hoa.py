# -*- coding: utf-8 -*-
"""TC-25 · Khối 06 Dòng tiền theo phương án dung hoà (14/9/2026).

BA VIỆC VÒNG NÀY LÀM, và vì sao mỗi việc cần một phép thử riêng.

1. BA MỨC TRẠNG THÁI thay cho cột "Cửa nhập · bộ phận" trên trang Chủ tịch.
   Bản vẽ V1.4 đòi bỏ hẳn cột ấy. Bỏ hẳn thì ngược ranh giới 09/9: mỗi con số phải có một cửa nhập,
   và cửa nào chưa có phải nhìn thấy được. Anh Tuấn chốt phương án dung hoà — trang Chủ tịch một
   nhãn ba mức, chi tiết chuyển sang trang riêng. Phép thử canh cả hai đầu: nhãn có ở trang chính,
   và nguyên nhân · bộ phận · cửa nhập KHÔNG biến mất mà nằm ở trang chi tiết.

2. XEM THEO TỪNG KHOẢNG. Bốn cột máy chủ trả về đều luỹ kế từ cùng một ngày. Số trong từng khoảng
   là HIỆU của hai cột liền nhau — đúng tuyệt đối vì mọi số đã làm tròn đến đồng. Nhưng chỉ đúng
   với DÒNG CHẢY: ba dòng mức (tiền đầu kỳ · số dư cuối khoảng · thiếu so với dự phòng) là mức tại
   một thời điểm, trừ chúng ra là vô nghĩa. Phép thử canh đúng chỗ ấy.

3. CÂU NHẮC PHẢI ĐỔI THEO KIỂU XEM. Ở luỹ kế, cộng bốn cột là sai. Ở theo khoảng, cộng bốn cột lại
   ĐÚNG. Giữ nguyên một câu cho cả hai kiểu là chắc chắn sai một nửa số lần.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DV = GOC / "backend" / "app" / "services" / "khung_dong_tien.py"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
NGUON = GOC / "web" / "app" / "dong-tien" / "nguon" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich_py(s: str) -> str:
    """Bóc chuỗi tài liệu và chú thích của tệp .py trước khi soi mã.

    LẦN THỨ NĂM cùng một cái bẫy trong chuỗi TC, nay sang cả tệp Python: đoạn docstring GIẢI THÍCH
    vì sao không được đọc thẳng `c.tu_de_xuat` lại chứa đúng chuỗi ấy, nên phép thử đỏ vì lời giải
    thích của chính nó."""
    s = re.sub(r'"""(?:.|\n)*?"""', "", s)
    s = re.sub(r"'''(?:.|\n)*?'''", "", s)
    return re.sub(r"^\s*#.*$", "", s, flags=re.M)


def _bo_chu_thich_tsx(s: str) -> str:
    """Chú thích của các tệp này GIẢI THÍCH những chuỗi đang bị cấm, nên phải bóc trước khi soi.
    Đây là lần thứ tư cùng một cái bẫy trong chuỗi TC — giữ hàm này ở mọi tệp thử đọc mã .tsx."""
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


# ─────────────────────────────── 1 · BA MỨC TRẠNG THÁI ───────────────────────────────

def test_may_chu_tinh_ba_muc():
    s = _doc(DV)
    for ma in ("con_thieu", "chua_doi_soat", "day_du"):
        assert f'"{ma}"' in s, f"Thiếu mức {ma} ở máy chủ."
    assert "def trang_thai_dong" in s, "Ba mức phải tính Ở MÁY CHỦ, không tính ở trình duyệt."
    assert '"Chưa đối soát"' in s and '"Còn thiếu"' in s and '"Đầy đủ"' in s


def test_khong_co_muc_thu_tu():
    """Đúng BA mức. Thêm mức thứ tư mà hệ thống không đo được là làm hỏng cả ba mức kia."""
    s = _doc(DV)
    i = s.index("NHAN_TRANG_THAI")
    khoi = s[i:s.index("}", i)]
    assert khoi.count(":") == 3, f"NHAN_TRANG_THAI phải có đúng ba mức, đang có {khoi.count(':')}"


def test_trang_chu_tich_hien_nhan_thay_cot_cua_nhap():
    ma = _bo_chu_thich_tsx(_doc(KHOI))
    assert "Cửa nhập · bộ phận" not in ma, (
        "Cột 'Cửa nhập · bộ phận' vẫn còn trên trang Chủ tịch — phương án dung hoà chuyển nó sang "
        "trang chi tiết."
    )
    assert "ChipTrangThai" in ma, "Thiếu nhãn ba mức thay cho cột đã bỏ."
    assert "nhan_trang_thai" in ma


def test_chi_tiet_khong_bien_mat_ma_chuyen_sang_trang_rieng():
    """Ranh giới 09/9: cửa nhập phải NHÌN THẤY ĐƯỢC ở đâu đó, không được bốc hơi."""
    ma = _bo_chu_thich_tsx(_doc(NGUON))
    for phai_co in ("Nguyên nhân", "Bộ phận chịu", "Cửa nhập phải dựng", "Nguồn hiện có"):
        assert phai_co in ma, f"Trang chi tiết thiếu cột '{phai_co}'."
    chinh = _bo_chu_thich_tsx(_doc(KHOI))
    assert "/dong-tien/nguon" in chinh, "Trang Chủ tịch không có lối sang trang chi tiết."


def test_han_xu_ly_khong_bia():
    """Bản vẽ muốn có cột hạn. Hệ thống chưa có chỗ nào ghi hạn — cột dựng nhưng ghi 'chưa đặt'."""
    ma = _bo_chu_thich_tsx(_doc(NGUON))
    assert "Hạn xử lý" in ma, "Bỏ luôn cột hạn thì việc còn thiếu biến mất khỏi tầm mắt."
    assert "chưa đặt" in ma, "Cột hạn phải nói rõ là chưa đặt, không để trống cho đẹp."


def test_trang_chi_tiet_khong_tu_loc_theo_vai():
    """SEC-02: cắt dòng ở máy chủ. Trang chi tiết không được nhắc tên vai trò nào."""
    ma = _bo_chu_thich_tsx(_doc(NGUON))
    for vai in ('"chutich"', '"tgd"', '"ketoan"', '"bks"'):
        assert vai not in ma, f"Trang chi tiết đang tự lọc theo vai {vai} — SEC-02 bắt đỏ."


# ─────────────────────────────── 2 · XEM THEO TỪNG KHOẢNG ───────────────────────────────

def test_hieu_tinh_o_may_chu():
    s = _doc(DV)
    assert "def theo_khoang" in s and "def moc_khoang" in s
    ma = _bo_chu_thich_tsx(_doc(KHOI))
    # Trình duyệt chỉ được ĐỌC so_khoang, không được tự trừ.
    assert "so_khoang" in ma
    assert re.search(r"\bso\[[^\]]+\]\s*-\s*so\[", ma) is None, (
        "Trình duyệt đang tự trừ hai cột — phép tính phải nằm ở máy chủ."
    )


def test_ba_dong_muc_khong_bi_tru():
    s = _doc(DV)
    i = s.index("DONG_LA_MUC")
    khoi = s[i:s.index(")", i)]
    for ma in ("tien_kha_dung_dau_ky", "so_du_du_kien_cuoi_khoang", "thieu_so_voi_muc_du_phong"):
        assert ma in khoi, f"{ma} phải nằm trong DONG_LA_MUC — trừ một MỨC ra là vô nghĩa."
    assert "la_dong_chay" in s, "Thiếu cờ phân biệt dòng chảy với dòng mức."


def test_rong_khac_khong_khi_tinh_hieu():
    """Thiếu một đầu thì khoảng ấy RỖNG. Lấy 0 thay cho 'chưa có số' là bịa ra một khoảng không có
    tiền chảy qua, trong khi sự thật là không ai biết."""
    s = _doc(DV)
    i = s.index("def theo_khoang")
    than = s[i:s.index("\ndef ", i + 5)]
    assert "ra[c] = None" in than, "Hàm tính hiệu phải trả None khi thiếu đầu vào."
    assert " or 0" not in than, "Có chỗ lấy 0 thay cho None trong hàm tính hiệu."


def test_ngay_dau_khoang_khong_de_len_ngay_goc():
    """Hai kiểu xem phải nói đúng ngày CỦA MÌNH: luỹ kế cùng bắt đầu từ ngày báo cáo, theo khoảng
    thì cột sau bắt đầu sau cột trước. Ghi đè lên cột gốc là kiểu luỹ kế in sai ngày."""
    s = _doc(DV)
    i = s.index("def moc_khoang")
    than = s[i:]
    assert "tu_ngay_khoang" in than
    assert "m = dict(c)" in than, "moc_khoang phải trả BẢN SAO, không sửa cột gốc."


# ─────────────────────────────── 3 · CÂU NHẮC ĐỔI THEO KIỂU XEM ───────────────────────────────

def test_cau_nhac_doi_theo_kieu_xem():
    s = _doc(DV)
    assert "cong_bon_cot_khi_xem_khoang" in s, (
        "Thiếu câu nhắc cho kiểu xem theo khoảng — ở kiểu ấy cộng bốn cột LÀ ĐÚNG, giữ nguyên câu "
        "của kiểu luỹ kế là nói ngược."
    )
    ma = _bo_chu_thich_tsx(_doc(KHOI))
    assert "cong_bon_cot_khi_xem_khoang" in ma and "cong_bon_cot_la_sai" in ma, (
        "Màn hình phải đổi câu nhắc theo kiểu xem đang chọn."
    )


def test_mac_dinh_van_la_luy_ke():
    """Đổi mặc định sang kiểu mới là hôm sau có người đọc bảng mới bằng thói quen cũ."""
    ma = _bo_chu_thich_tsx(_doc(KHOI))
    assert "useState(false)" in ma and "setKhoang" in ma, (
        "Kiểu xem mặc định phải là luỹ kế (khoang = false)."
    )


# ─────────────────────────────── VÁ PHÒNG THỦ GIỮA HAI LÀN ───────────────────────────────

def test_doc_phong_thu_ten_thuoc_tinh_cua():
    """Làn Phân quyền đã đổi tên `tu_de_xuat` thành `ngoai_bang_III4` trong thư mục làm việc của họ.
    Hôm nào họ đẩy lên, đọc thẳng `c.tu_de_xuat` sẽ ném AttributeError và tắt CẢ khối dòng tiền của
    Chủ tịch. Đọc cả hai tên là vá đỡ — hai làn vẫn phải thống nhất một tên."""
    s = _doc(DV)
    assert "def _cua_do_de_xuat" in s
    assert "tu_de_xuat" in s and "ngoai_bang_III4" in s
    assert re.search(r"c\.tu_de_xuat", _bo_chu_thich_py(s)) is None, (
        "Vẫn còn chỗ đọc thẳng c.tu_de_xuat — một cái tên đổi ở tệp bên kia là sập màn hình bên này."
    )


# ─────────────────────────────── GIAO DIỆN ───────────────────────────────

def test_co_css_cho_cap_nut_va_dong_tom_tat():
    css = _doc(CSS)
    for lop in (".dt-kieu", ".dt-tomtat"):
        assert lop in css, f"Thiếu luật CSS cho {lop}."


def test_khoi_640px_cuoi_cung_van_la_cua_tc4():
    """test_tc4_dien_thoai đọc bản điện thoại bằng rindex('@media (max-width:640px)'). Thêm một khối
    640px xuống CUỐI tệp là bốn phép thử TC-4 đỏ, mà lời báo lỗi lại nói về bảng trên điện thoại."""
    css = _doc(CSS)
    cuoi = css[css.rindex("@media (max-width:640px)"):]
    assert "bang-doc" in cuoi, "Có khối @media 640px mới nằm SAU khối của TC-4 — phải đặt trước."
