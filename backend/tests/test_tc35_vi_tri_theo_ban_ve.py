# -*- coding: utf-8 -*-
"""TC-35 · VỊ TRÍ khối theo bản vẽ V1.4 — không chỉ thứ tự dọc.

Vòng TC-31 xếp lại THỨ TỰ DỌC chín khối rồi tuyên bố "đúng bản vẽ". Thứ tự đúng thật. Nhưng anh
Tuấn mở trang 15/9/2026 và nói ngay: *"giao diện chưa giống bản vẽ, thứ tự vị trí bị sai"* — và
anh ấy đúng, vì TC-31 chỉ kiểm thứ tự, không kiểm VỊ TRÍ.

Đo hai bên ở bề rộng 1440px:

                     BẢN VẼ                TRANG THẬT (trước vòng này)
    Dòng tiền   trên 2189 · rộng 616    trên 5778 · rộng 1121
    Rủi ro      trên 2189 · rộng 440    trên 6629 · rộng 1121
    Nút In      trong hàng lọc          cạnh tiêu đề, cao hơn 87px
    Điều hành   cao 158                 cao 3.693
    Cả trang    cao 2.791               cao 8.192  (gấp 2,9 lần)

BÀI HỌC GHI LẠI, vì nó là gốc của cả ba chỗ sai: TC-31 xếp Dòng tiền và Rủi ro DỌC và tự biện hộ
rằng "bảng bốn mốc ép xuống nửa bề ngang thì vỡ cột". Câu ấy nghe hợp lý và KHÔNG ĐƯỢC ĐO. Đo lại
thì bảng cần tối thiểu 637px, bản vẽ cho 616px — hụt 21px, mà `.wrap` vốn đã có `overflow-x:auto`.
Một lý do nghe hợp lý mà không kèm số đo thì vẫn chỉ là phỏng đoán, và ở đây nó làm sai bố cục
suốt bốn vòng.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich_tsx(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", "", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", "", s)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


def _bo_chu_thich_css(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


# ─────────────── 1 · DÒNG TIỀN VÀ RỦI RO CÙNG MỘT HÀNG ───────────────

def test_dong_tien_va_rui_ro_nam_chung_mot_hang():
    """Bản vẽ đặt hai khối này CẠNH NHAU. Xếp dọc thì Rủi ro tụt xuống dưới 851px."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    m = re.search(r'<div className="mh01-hang-2">(.*?)</div>', ma, re.S)
    assert m, "Thiếu hàng hai cột `mh01-hang-2` cho Dòng tiền + Rủi ro."
    trong = m.group(1)
    assert "<KhoiDongTien" in trong and "<KhoiRuiRo" in trong, (
        "Hàng hai cột phải chứa ĐÚNG hai khối Dòng tiền và Rủi ro."
    )
    assert trong.index("<KhoiDongTien") < trong.index("<KhoiRuiRo"), (
        "Bản vẽ đặt Dòng tiền BÊN TRÁI (rộng 616), Rủi ro bên phải (rộng 440)."
    )


def test_ti_le_hai_cot_dung_ban_ve():
    """616 : 440 = 1,4 : 1. Chia đôi 1:1 thì Dòng tiền hụt so với bề rộng tối thiểu 637px."""
    css = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.mh01-hang-2\s*\{([^}]*)\}", css)
    assert m, "Thiếu kiểu .mh01-hang-2"
    than = m.group(1).replace(" ", "")
    assert "grid-template-columns:minmax(0,1.4fr)minmax(0,1fr)" in than, (
        "Tỉ lệ hai cột phải là 1,4 : 1 theo bản vẽ (616 : 440), và phải dùng minmax(0,…) — thiếu "
        "minmax thì ô lưới không co nhỏ hơn nội dung, bảng tự nong cột ra và đẩy vỡ cả hàng."
    )


def test_man_hep_thi_xuong_mot_cot():
    """Bảng dòng tiền cần tối thiểu 637px. Giữ hai cột trên màn hẹp mới đúng là chỗ nó vỡ thật."""
    css = _bo_chu_thich_css(_doc(CSS))
    i = css.index(".mh01-hang-2")
    khoi = css[i:i + 700].replace(" ", "")
    assert re.search(r"@media\(max-width:11\d\dpx\)\{\.mh01-hang-2\{grid-template-columns:1fr\}", khoi), (
        "Thiếu mốc chuyển về một cột cho màn hẹp."
    )


# ─────────────── 2 · NÚT IN Ở HÀNG LỌC, KHÔNG Ở TIÊU ĐỀ ───────────────

def _than_ham(ma: str, ten: str) -> str:
    i = ma.index(f"export function {ten}")
    j = ma.find("export function", i + 10)
    return ma[i:j if j > 0 else len(ma)]


def test_nut_in_nam_trong_hang_loc():
    """Bản vẽ đặt nút In trong `.filters`, ngang với "Kỳ báo cáo" — nó là thao tác TRÊN KỲ ĐANG
    CHỌN. TC-31 đặt nhầm lên cạnh tiêu đề: đúng nút, sai chỗ."""
    ma = _bo_chu_thich_tsx(_doc(DAU))
    loc = _than_ham(ma, "DongLoc")
    assert "In / Lưu PDF" in loc and "window.print()" in loc, (
        "Nút In / Lưu PDF phải nằm trong hàng lọc `DongLoc`."
    )


def test_nut_in_khong_con_o_tieu_de():
    ma = _bo_chu_thich_tsx(_doc(DAU))
    assert "In / Lưu PDF" not in _than_ham(ma, "TieuDe"), (
        "Nút In vẫn còn ở tiêu đề — hai chỗ cùng một nút là một nút thừa."
    )


def test_chi_co_mot_nut_in_tren_man_hinh():
    ma = _bo_chu_thich_tsx(_doc(DAU))
    assert ma.count("In / Lưu PDF") == 1, "Màn hình đang có nhiều hơn một nút In."


# ─────────────── 3 · KHỐI DÀI CUỘN TRONG KHUNG, KHÔNG CẮT DÒNG ───────────────

def test_bang_dieu_hanh_cuon_trong_khung():
    """Khối Điều hành đo được cao 3.693px — 45% cả trang — vì 92 chuyến đổ hết ra một mạch."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "mh01-cuon" in ma, "Bảng chuyến chưa có khung cuộn."
    css = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.mh01-cuon\s*\{([^}]*)\}", css)
    assert m and "max-height" in m.group(1) and "overflow-y:auto" in m.group(1).replace(" ", ""), (
        "Khung cuộn phải có chiều cao trần và cuộn dọc."
    )


def test_dau_bang_dinh_lai_khi_cuon():
    """Cuộn giữa chừng mà mất tên cột thì bảy cột thành bảy cột không tên."""
    css = _bo_chu_thich_css(_doc(CSS))
    i = css.index(".mh01-cuon")
    khoi = css[i:i + 400].replace(" ", "")
    assert "position:sticky" in khoi and "top:0" in khoi, "Đầu bảng chưa dính khi cuộn."


def test_khong_cat_bot_dong_nao():
    """92 chuyến là 92 việc có thật trong 14 ngày tới. Cắt dòng là giấu đúng việc ấy — nên chỉ
    được CUỘN, không được `.slice(`."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    m = re.search(r"sec\.sap_khoi_hanh[^\n]*\.slice\(", ma)
    assert not m, "Bảng chuyến đang cắt bớt dòng thay vì cuộn."


def test_in_ra_giay_thi_bo_khung_cuon():
    """Giấy không cuộn được: giữ trần 420px khi in là mất phần lớn số chuyến."""
    css = _bo_chu_thich_css(_doc(CSS))
    i = css.index("@media print")
    khoi = css[i:].replace(" ", "")
    assert "mh01-cuon{max-height:none" in khoi, (
        "Kiểu in chưa bỏ trần chiều cao của khung cuộn."
    )


def test_danh_sach_dai_gap_lai_nhung_in_van_mo():
    """Danh sách 100 mã quá hạn gấp lại cho gọn, nhưng <details> đóng thì in ra mất chữ."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "mh01-gap" in ma and "<summary>" in ma, "Danh sách dài chưa gấp lại."
    assert "qua_han_qt.length" in ma, "Gấp lại thì phải ghi SỐ chuyến ra ngoài, không thì gấp mất tin."


# ─────────────── 4 · LUẬT CŨ KHÔNG BỊ PHÁ ───────────────

def test_khong_them_ma_mau_go_thang():
    css = _bo_chu_thich_css(_doc(CSS))
    thua = [m for m in re.findall(r"#[0-9a-fA-F]{3,8}", css) if m.lower() != "#fff"]
    assert not thua, f"Có mã màu gõ thẳng ngoài chú thích: {sorted(set(thua))}"


def test_thu_tu_doc_chin_khoi_van_giu_nguyen():
    """Vòng này sửa VỊ TRÍ, không được làm hỏng THỨ TỰ mà TC-31 đã chỉnh đúng."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    thu_tu = ["<KhoiQuyetDinh", "<TamThe", 'id="dieu-hanh"', "<KhoiHieuQuaXe",
              "<KhoiTonDongBoPhan", "<KhoiPhaiThu", "<KhoiPhaiTra", "<KhoiDongTien",
              "<KhoiRuiRo", "<KhoiTienDoBaoCao"]
    vi = [(m, ma.index(m)) for m in thu_tu if m in ma]
    assert len(vi) == len(thu_tu), f"Thiếu khối: {set(thu_tu) - {m for m, _ in vi}}"
    sai = [(a[0], b[0]) for a, b in zip(vi, vi[1:]) if a[1] > b[1]]
    assert not sai, "Thứ tự dọc bị phá: " + "; ".join(f"{x} phải TRƯỚC {y}" for x, y in sai)
