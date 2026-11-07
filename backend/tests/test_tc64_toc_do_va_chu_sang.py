# -*- coding: utf-8 -*-
"""TC-64 · BA CHỖ LÀM MÀN HÌNH CHẬM, VÀ BỐN NẤC CHỮ SÁNG LÊN MỘT BẬC.

    "Hãy kiểm tra lý do load rất chậm"                                — anh Tuấn, 18/9/2026
    "và chỉnh chữ màu trắng sáng trên toàn web"                       — anh Tuấn, 18/9/2026

══════════════════════════════════════════════════════════════════════════════════════════════
SỐ ĐO THẬT — ĐO TRƯỚC KHI SỬA, KHÔNG ĐOÁN
══════════════════════════════════════════════════════════════════════════════════════════════
Gọi thẳng từng cửa trên vtos.infinitytours.org, mỗi cửa ba lần liên tiếp (18/9/2026):

    /bao-cao/ket-qua-kinh-doanh   2,19s   2,28s   1,66s
    /dong-tien/khung/1            1,83s   2,60s   0,87s
    /dashboard                    8,04s   0,25s   0,25s     ← đã có chỗ nhớ từ trước
    /alerts                       0,87s   0,95s   1,30s
    /auth/me                      0,46s   0,24s   0,23s

Trang HTML về trong 0,2 giây (TTFB 94ms, load 205ms), nên chậm KHÔNG ở mạng hay trình duyệt.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG MÀ PHÉP THỬ NÀY CANH
══════════════════════════════════════════════════════════════════════════════════════════════
1. CHỖ NHỚ QUÊN VAI. `/dong-tien/khung` cắt tập dòng theo vai (SEC-02). Một chỗ nhớ đánh khoá mà
   bỏ vai ra là cách chắc chắn nhất để Tổng giám đốc nhận lại đúng gói vừa dựng cho Chủ tịch —
   và không lỗi nào báo, vì gói ấy hợp lệ, chỉ là của người khác.
2. CHỖ NHỚ KHÔNG CÓ CỬA XOÁ. Người vừa bấm "Chốt số dư" mà màn hình vẫn hiện số cũ suốt năm phút
   thì họ sẽ chốt lại lần nữa — và lần ấy mới là cái sai thật.
3. CHỖ NHỚ CỦA MỘT LẦN GỌI BIẾN THÀNH CHỖ NHỚ SỐNG LÂU. `nho` trong `ket_qua_kinh_doanh.bang`
   phải sinh ra và chết trong một lần gọi. Ai đó nâng nó lên cấp mô-đun "cho nhanh hơn nữa" là
   biến nó thành một chỗ nhớ không có hạn và không ai xoá.
4. BỐN NẤC CHỮ BỊ SÁNG ĐỀU THÀNH MỘT. Sáng tất cả lên trắng thì không còn phân biệt chữ chính với
   chữ phụ, và mọi màn hình đọc ra như một khối chữ phẳng.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
NHO = GOC / "backend" / "app" / "services" / "nho_tam.py"
KQKD = GOC / "backend" / "app" / "services" / "ket_qua_kinh_doanh.py"
KQT = GOC / "backend" / "app" / "services" / "ket_qua_that.py"
API_BC = GOC / "backend" / "app" / "api" / "v1" / "bao_cao.py"
API_DT = GOC / "backend" / "app" / "api" / "v1" / "dong_tien.py"
TOKENS = GOC / "web" / "app" / "tokens.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_py(p: Path) -> str:
    """Bỏ chuỗi tài liệu và chú thích — một cái tên nhắc trong chú thích không phải là mã dùng nó."""
    s = _doc(p)
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


# ───────────────────── 1 · MỘT CHỖ NHỚ DÙNG CHUNG, KHÔNG BA BẢN CHÉP ─────────────────────

def test_chi_co_mot_cach_lam_cho_nho():
    """`/dashboard` đã có chỗ nhớ 5 phút từ trước. Viết thêm hai chỗ nhớ nữa, mỗi chỗ một kiểu, là
    ba bản chép của cùng một phép tính thời gian — và ba bản chép thì sớm muộn lệch nhau (đúng lý
    lẽ đã dùng khi gom bốn bản vẽ biểu đồ về một bộ ở TC-40)."""
    ma = _ma_py(NHO)
    for can in ("class Kho", "def lay", "def dat", "def xoa", "def khoa_vai"):
        assert can in ma, f"services/nho_tam.py thiếu {can}."
    for p in (API_BC, API_DT):
        assert "nho_tam as NHO" in _ma_py(p), f"{p.name} tự dựng chỗ nhớ riêng thay vì dùng tệp chung."
    # Năm phút khai ĐÚNG MỘT chỗ; hai con số hạn khác nhau là hai cửa già đi khác nhau.
    assert _ma_py(NHO).count("SONG_GIAY = 300") == 1


def test_kho_khong_nho_cai_dang_loi():
    """Luật 3 của services/nho_tam.py: nhớ một lỗi năm phút là biến một trục trặc thoáng qua thành
    năm phút hỏng cho mọi người cùng vai."""
    ma = _ma_py(API_BC)
    i = ma.index("def ket_qua_kinh_doanh")
    than = ma[i:i + 1200]
    assert "except ValueError" in than and "HTTPException(422" in than, (
        "Cửa kết quả kinh doanh phải còn nhánh trả 422 cho mã kỳ sai."
    )
    # Lời gọi ghi vào kho phải nằm TRONG `try`, tức chỉ chạy khi đã có kết quả.
    j = than.index("try:")
    assert than.index("KHO_KQKD.dat(") > j, "Ghi vào kho trước khi biết có kết quả hay không."


# ───────────────────── 2 · KHOÁ MANG VAI, VÀ CÓ CỬA XOÁ ─────────────────────

def test_khoa_cua_khoi_dong_tien_mang_vai():
    """Chỗ hỏng số 1 — cửa này cắt tập dòng theo vai, nên khoá quên vai là lộ dữ liệu."""
    ma = _ma_py(API_DT)
    i = ma.index("def xem_khung")
    than = ma[i:ma.index("\n@router", i)]
    assert "NHO.khoa_vai(u.role" in than, (
        "Khoá chỗ nhớ của /dong-tien/khung phải mang vai trò. `khoa_vai` bắt nêu vai ra thành một "
        "tham số riêng chính vì việc này (SEC-02)."
    )
    assert "company_id" in than.split("NHO.khoa_vai")[1][:80], "Khoá phải mang cả mã pháp nhân."


def test_cua_ghi_xoa_cho_nho_cua_dung_phap_nhan():
    """Chỗ hỏng số 2 — canh cả hai cửa ghi có thật sự đổi số của khối bốn mốc."""
    ma = _ma_py(API_DT)
    chot = ma[ma.index("def chot_so_du"):]
    chot = chot[:chot.index("\n@router")]
    assert "KHO_KHUNG.xoa(" in chot, (
        "Chốt số dư mà không xoá chỗ nhớ thì người vừa nhập số vẫn thấy số cũ tới năm phút — và "
        "họ sẽ chốt lại lần nữa."
    )
    dong_bo = ma[ma.index("def dong_bo_nghia_vu"):]
    assert "KHO_KHUNG.xoa()" in dong_bo, (
        "Dựng lại sổ nghĩa vụ đổi số của MỌI pháp nhân, nên phải xoá sạch kho chứ không lọc."
    )


def test_hai_cua_nang_deu_co_duong_lam_moi():
    """Luật 2 của services/nho_tam.py: chỗ nhớ nào cũng phải có cửa làm mới, đúng như /dashboard."""
    for p, ten_ham in ((API_BC, "def ket_qua_kinh_doanh"), (API_DT, "def xem_khung")):
        ma = _ma_py(p)
        than = ma[ma.index(ten_ham):][:700]
        assert "refresh: bool = False" in than, f"{ten_ham} thiếu tham số refresh."
        assert "if not refresh" in than, f"{ten_ham} không dùng tới refresh."


# ───────────────────── 3 · CHỖ NHỚ CỦA MỘT LẦN GỌI ─────────────────────

def test_nho_cua_mot_lan_goi_sinh_ra_trong_ham():
    """Chỗ hỏng số 3 — `nho` phải sinh ra và chết trong MỘT lần dựng bảng.

    Nâng nó lên cấp mô-đun "cho nhanh hơn nữa" là biến nó thành một chỗ nhớ không có hạn, không ai
    xoá, và sẽ trả số cũ cho người vừa đóng số một chuyến.
    """
    ma = _ma_py(KQKD)
    than = ma[ma.index("def bang("):]
    assert "nho: dict = {}" in than, "`nho` phải được tạo mới ngay trong thân `bang()`."
    # Không có biến `nho` nào sống ở cấp mô-đun.
    truoc = ma[:ma.index("def bang(")]
    assert not re.search(r"(?m)^nho\s*[:=]", truoc), (
        "`nho` đang sống ở cấp mô-đun — nó sẽ giữ số cũ qua nhiều lần gọi mà không ai xoá."
    )


def test_ba_cho_hoi_cung_mot_thang_deu_dung_chung_mot_cho_nho():
    """Cái làm cửa này chậm là hỏi BA lần về cùng một tháng, chứ không phải một câu truy vấn nặng.

    Ba chỗ ấy: `thieu_thang` ngay trong `bang()`, chỉ tiêu doanh thu và chỉ tiêu lợi nhuận tour —
    hai cái sau đi qua `xu_huong.doc_that`. Chúng phải dùng CHUNG một `nho`; mỗi bên một cái thì
    vẫn hỏi máy hai lần.
    """
    ma = _ma_py(KQKD)
    assert "XH.doc_that(db, nho=nho)" in ma, "`doc_that` không nhận chỗ nhớ — hai bên vẫn hỏi riêng."
    assert "KQ.thang(db, t, nho=nho)" in ma, "`thieu_thang` không dùng chỗ nhớ."
    assert "KH.hop_nhat(db, t, nho=nho)" in ma, "Kế hoạch từng tháng không dùng chỗ nhớ."


def test_khong_truyen_nho_thi_chay_y_nhu_cu():
    """Mọi chỗ gọi khác trong hệ thống không phải đổi một chữ — `nho` là tham số CÓ MẶC ĐỊNH."""
    for p, ham in ((KQT, "def thang("),
                   (GOC / "backend" / "app" / "services" / "ke_hoach.py", "def hop_nhat("),
                   (GOC / "backend" / "app" / "services" / "xu_huong.py", "def doc_that(")):
        ma = _doc(p)
        dong = ma[ma.index(ham):ma.index(")", ma.index(ham))]
        assert "nho: dict | None = None" in dong, f"{p.name}:{ham} — `nho` phải có mặc định None."


# ───────────────────── 4 · BỐN NẤC CHỮ, KHÔNG PHẢI MỘT ─────────────────────

def _svg_l(h: str) -> float:
    h = h.lstrip("#")
    def lin(c):
        c = int(h[c:c + 2], 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(0) + 0.7152 * lin(2) + 0.0722 * lin(4)


def _tuong_phan(a: str, b: str) -> float:
    la, lb = _svg_l(a), _svg_l(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _bien(ten: str) -> str:
    m = re.search(re.escape(ten) + r":\s*(#[0-9A-Fa-f]{6})", _doc(TOKENS))
    assert m, f"tokens.css thiếu {ten}"
    return m.group(1)


def test_bon_nac_chu_deu_dat_nguong_AA_tren_moi_nen():
    """Nấc mờ nhất cũ (#7B93A8) chỉ đạt 3,96 trên nền thông tin — DƯỚI ngưỡng AA 4,5. Đó là lý do
    thật của vòng chỉnh chữ này, không phải chuyện thấy tối."""
    nen = {"màn hình": "--vtos-surface", "thẻ": "--vtos-card",
           "thanh": "--vtos-nav-bg", "thông tin": "--vtos-info-bg"}
    chu = ("--vtos-text", "--vtos-heading", "--vtos-text-mute", "--vtos-text-faint")
    for ten_nen, bien_nen in nen.items():
        for c in chu:
            tp = _tuong_phan(_bien(c), _bien(bien_nen))
            assert tp >= 4.5, f"{c} trên nền {ten_nen} chỉ đạt {tp:.2f} — dưới ngưỡng AA 4,5."


def test_van_con_bon_nac_ro_ret():
    """Chỗ hỏng số 4. Sáng đều tất cả lên trắng thì mọi màn hình đọc ra như một khối chữ phẳng.

    Thứ bậc phải đúng chiều: tiêu đề sáng nhất, rồi chữ thường, rồi chữ phụ, rồi chữ mờ. Trước
    TC-64 thứ bậc này SAI ở nấc đầu — `--vtos-heading` (#DCE9F4) tối hơn `--vtos-text` (#E8F1F8).
    """
    the = _bien("--vtos-card")
    tp = {c: _tuong_phan(_bien(c), the)
          for c in ("--vtos-heading", "--vtos-text", "--vtos-text-mute", "--vtos-text-faint")}
    assert tp["--vtos-heading"] >= tp["--vtos-text"], "Tiêu đề không được mờ hơn thân bài."
    assert tp["--vtos-text"] > tp["--vtos-text-mute"] > tp["--vtos-text-faint"], (
        f"Bốn nấc chữ không còn đúng thứ bậc: {tp}"
    )
    assert tp["--vtos-text"] - tp["--vtos-text-faint"] >= 4.0, (
        f"Nấc sáng nhất và nấc mờ nhất quá gần nhau ({tp['--vtos-text']:.2f} ↔ "
        f"{tp['--vtos-text-faint']:.2f}) — không còn phân biệt được chữ chính với chữ phụ."
    )


def test_mau_bieu_do_khong_bi_doi_ke_trong_vong_chinh_chu():
    """`--vtos-navy` vừa là màu CHỮ của số nổi bật vừa là màu TÔ của cột biểu đồ, và bộ ba màu
    biểu đồ đã được đo lại cho người không phân biệt màu ở TC-59 (ΔE ≥ 14,7). Đổi nó là phải đo
    lại cả bộ ba — việc riêng, không gộp vào vòng chỉnh chữ."""
    assert _bien("--vtos-navy").upper() == "#6FA8F0"
    assert _bien("--vtos-success").upper() == "#53C49A"
    assert _bien("--vtos-danger").upper() == "#FF6B90"   # KS-MUC 07/11: trả lại hồng
