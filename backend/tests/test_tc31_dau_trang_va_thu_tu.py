# -*- coding: utf-8 -*-
"""TC-31 · Màn hình 01 xếp ĐÚNG THỨ TỰ bản vẽ V1.4, và có đầu trang + nút In như bản vẽ.

Anh Tuấn gửi lại tệp bản vẽ ngày 14/9/2026 kèm ảnh chụp và nói form chưa giống. Đối chiếu từng
khối thì đúng — không phải thiếu khối, mà THỨ TỰ khác:

    BẢN VẼ:  Cần quyết định → 8 thẻ → Điều hành 14 ngày → Hiệu quả đội xe → Tồn đọng theo bộ phận
             → Phải thu → Phải trả → Dòng tiền → Rủi ro → Tiến độ báo cáo

    VTOS cũ: Cần quyết định → 8 thẻ → DÒNG TIỀN → Việc cần xử lý → Tồn đọng cần xử lý → Kinh doanh
             Lẻ → Kinh doanh Đoàn → Điều hành → Báo cáo ngày → … rồi mới tới phần còn lại

Khối Dòng tiền đứng ở vị trí 3 thay vì 8, và năm khối riêng của VTOS chen vào giữa. Đọc từ trên
xuống ra một trang khác hẳn bản vẽ, dù đủ khối.

Năm khối riêng ấy KHÔNG bỏ — chúng có số thật và người dùng thật. Chúng xuống dưới, sau khối cuối
của bản vẽ, dưới một đường ngăn nói rõ đây là phần thêm.
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


# ───────────────────────── 1 · THỨ TỰ KHỐI ĐÚNG BẢN VẼ ─────────────────────────

# Đúng thứ tự bản vẽ V1.4. Mỗi phần tử là một MỐC NHẬN DẠNG có thật trong mã.
THU_TU_BAN_VE = [
    "<KhoiQuyetDinh",            # 02 · Cần Chủ tịch quyết định
    "<TamThe",                   # 03 · tám thẻ chỉ tiêu
    'id="dieu-hanh"',            # 04a · Điều hành 14 ngày tới
    "<KhoiHieuQuaXe",            # 04b · Hiệu quả đội xe trong kỳ
    "<KhoiTonDongBoPhan",        # 04c · Tồn đọng theo bộ phận
    "<KhoiPhaiThu",              # 05a · Phải thu theo hạn
    "<KhoiPhaiTra",              # 05b · Phải trả theo hạn
    "<KhoiDongTien",             # 06  · Dòng tiền
    "<KhoiRuiRo",                # 07  · Rủi ro trọng yếu
    "<KhoiTienDoBaoCao",         # 08  · Tiến độ báo cáo
]


def test_muoi_khoi_xep_dung_thu_tu_ban_ve():
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    vi_tri = []
    for moc in THU_TU_BAN_VE:
        assert moc in ma, f"Không tìm thấy khối {moc!r} trên màn hình 01."
        vi_tri.append((moc, ma.index(moc)))
    sai = [(a[0], b[0]) for a, b in zip(vi_tri, vi_tri[1:]) if a[1] > b[1]]
    assert not sai, (
        "Thứ tự khối lệch bản vẽ V1.4 — các cặp đứng sai: "
        + "; ".join(f"{x} phải TRƯỚC {y}" for x, y in sai)
    )


def test_dong_tien_dung_sau_phai_tra_va_truoc_rui_ro():
    """Chỗ lệch cụ thể anh Tuấn chỉ ra: bản vẽ đặt Dòng tiền ở vị trí 8, VTOS đặt ở vị trí 3."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert ma.index("<KhoiPhaiTra") < ma.index("<KhoiDongTien") < ma.index("<KhoiRuiRo"), (
        "Khối Dòng tiền không nằm giữa Phải trả và Rủi ro như bản vẽ."
    )
    # Và KHÔNG được còn một bản thứ hai nằm ngay sau tám thẻ như trước.
    assert ma.count("<KhoiDongTien") == 1, "Khối Dòng tiền đang dựng hai lần."


def test_khoi_rieng_cua_vtos_xuong_duoi_khoi_cuoi_cua_ban_ve():
    """Năm khối riêng không bỏ, nhưng không được chen giữa các khối của bản vẽ nữa."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    cuoi_ban_ve = ma.index("<KhoiTienDoBaoCao")
    for moc, ten in (("Việc cần xử lý", "Việc cần xử lý"),
                     ("<KhoiTonDong ", "Tồn đọng cần xử lý"),
                     ("Kinh doanh Lẻ", "Kinh doanh Lẻ"),
                     ("Kinh doanh Đoàn", "Kinh doanh Đoàn"),
                     ("Báo cáo ngày (Điều 12)", "Báo cáo ngày")):
        assert moc in ma, f"Khối riêng {ten!r} đã biến mất — không được bỏ, chỉ được chuyển chỗ."
        assert ma.index(moc) > cuoi_ban_ve, (
            f"Khối riêng {ten!r} vẫn chen vào giữa các khối của bản vẽ."
        )


def test_co_duong_ngan_noi_ro_dau_la_phan_them():
    """Xuống dưới mà không nói gì thì người đọc tưởng bản vẽ có những khối ấy."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "mh01-ngan" in ma and "mh01-them" in ma, "Thiếu đường ngăn và nhãn phần thêm."
    css = _bo_chu_thich_css(_doc(CSS))
    assert ".mh01-ngan" in css and ".mh01-them" in css, "Thiếu kiểu cho đường ngăn."


# ───────────────────────── 2 · ĐẦU TRANG THEO BẢN VẼ ─────────────────────────

def test_co_duong_dan_va_dong_phu():
    ma = _bo_chu_thich_tsx(_doc(DAU))
    assert "mh01-duong" in ma, "Thiếu đường dẫn (breadcrumb) ở đầu trang."
    assert "Không gian lãnh đạo" in ma, "Đường dẫn chưa đúng bản vẽ."
    assert "Kết quả · Phải thu · Phải trả · Dòng tiền · Quyết định" in ma, "Thiếu dòng phụ."
    css = _bo_chu_thich_css(_doc(CSS))
    for lop in (".mh01-duong", ".mh01-trang", ".mh01-phu"):
        assert lop in css, f"Thiếu kiểu {lop}."


def test_dau_trang_khong_dung_lai_ten_lop_cua_dau_khoi():
    """ĐẦU TRANG và ĐẦU KHỐI là hai việc khác nhau, phải mang hai tên lớp khác nhau.

    .mh01-dau đã có từ trước và là đầu KHỐI: một h2 kèm một thẻ nhãn, dùng ở cả sáu khối V14, khối
    Tồn đọng và khối Cần quyết định. Nếu đầu trang đặt lại đúng tên ấy thì quy tắc viết sau đè quy
    tắc viết trước — cùng một mức ưu tiên, khác nhau ở thứ tự — và mọi đầu khối trên màn hình nhận
    justify-content:space-between, thẻ nhãn văng sang mép phải panel.

    Đây là lỗi đã xảy ra thật khi dựng TC-31: dựng thử bằng trình duyệt chỉ soi đầu trang nên không
    thấy, vì chỗ hỏng nằm ở tám chỗ KHÁC. Phép thử này canh ngay trong mã nguồn.
    """
    dau = _bo_chu_thich_tsx(_doc(DAU))
    khoi_dau_trang = dau[dau.index("export function TieuDe"):]
    khoi_dau_trang = khoi_dau_trang[:khoi_dau_trang.index("export function", 1)]
    assert "mh01-dau" not in khoi_dau_trang, (
        "Đầu trang đang dùng lại lớp .mh01-dau của đầu khối — đè kiểu lên mọi đầu khối khác."
    )
    assert "mh01-trang" in khoi_dau_trang, "Đầu trang phải mang lớp riêng .mh01-trang."

    # Và trong CSS, .mh01-dau chỉ được khai MỘT LẦN (không kể quy tắc con "…-dau h2").
    css = _bo_chu_thich_css(_doc(CSS))
    lan = len(re.findall(r"(?m)^\.mh01-dau\s*\{", css))
    assert lan == 1, (
        f".mh01-dau được khai {lan} lần trong globals.css — hai lần là một lần đè lần kia."
    )


def test_duong_dan_khong_mang_ten_cua_ban_ve():
    """Bản vẽ ghi chặng cuối là "Thiết kế đề xuất" — đó là tên CỦA BẢN VẼ, không phải của trang
    thật. Chép nguyên vào trang chạy thật là nói với người dùng rằng họ đang xem một bản nháp."""
    ma = _bo_chu_thich_tsx(_doc(DAU))
    assert "Thiết kế đề xuất" not in ma, "Đường dẫn đang mang tên của bản vẽ."
    assert "Giao diện xanh navy" not in ma, (
        "Huy hiệu 'Giao diện xanh navy' là nhãn tài liệu thiết kế tự mô tả mình — dán lên trang "
        "thật thì thành một ô chữ không bấm được và không nói thêm điều gì."
    )


# ───────────────────────── 3 · NÚT IN / LƯU PDF LÀ VIỆC THẬT ─────────────────────────

def test_co_nut_in_va_no_in_that():
    ma = _bo_chu_thich_tsx(_doc(DAU))
    assert "In / Lưu PDF" in ma, "Thiếu nút In / Lưu PDF của bản vẽ."
    assert "window.print()" in ma, "Nút In chưa nối gì — một nút hứa rồi không làm còn tệ hơn không có nút."


def test_co_kieu_in_va_giay_khong_in_nen_toi():
    """Giấy là MÔI TRƯỜNG KHÁC, không phải màn hình thu nhỏ. Bảng màu nền tối in ra thì hoặc tốn
    cả hộp mực, hoặc trình duyệt bỏ nền và còn lại chữ sáng trên giấy trắng — không đọc được."""
    css = _bo_chu_thich_css(_doc(CSS))
    assert "@media print" in css, "Có nút In mà không có kiểu in — trang in ra sẽ mang nền tối."
    i = css.index("@media print")
    khoi = css[i:]
    assert "aside.side" in khoi and "display:none" in khoi, "Kiểu in chưa ẩn thanh điều hướng."
    assert "--vtos-text:" in khoi, "Kiểu in chưa đổi màu chữ — chữ sáng trên giấy trắng là mất chữ."
    assert "--vtos-text-mute:var(--vtos-sky)" in khoi.replace(" ", ""), (
        "Chữ phụ trên giấy phải đổi sang màu đậm hơn: --vtos-text-mute (#9BB2C6) trên giấy trắng "
        "chỉ đạt 2,19 lần tương phản."
    )


def test_kieu_in_khong_de_them_ma_mau_go_thang():
    """Luật bộ nhận diện: ngoài #fff, globals.css không được có mã màu gõ thẳng. Kiểu in đổi GIÁ
    TRỊ CỦA BIẾN chứ không gõ màu mới."""
    css = _bo_chu_thich_css(_doc(CSS))
    thua = [m for m in re.findall(r"#[0-9a-fA-F]{3,8}", css) if m.lower() != "#fff"]
    assert not thua, f"Có mã màu gõ thẳng ngoài chú thích: {sorted(set(thua))}"
