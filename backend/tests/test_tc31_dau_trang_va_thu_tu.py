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
# TC-40 (15/9/2026) · THỨ TỰ CÒN LẠI SAU KHI ANH TUẤN SOÁT TỪNG KHỐI.
#
# Luật KHÔNG đổi: các khối còn trên màn hình phải giữ đúng thứ tự tương đối của bản vẽ V1.4, vì
# thứ tự ấy là thứ tự đọc. Cái đổi là DANH SÁCH khối — anh Tuấn mở bản chạy thật, chụp ảnh từng
# khối và chốt bỏ bốn khối chưa có sổ nào phía sau (04a Điều hành · 04c Tồn đọng theo bộ phận ·
# 07 Rủi ro · 08 Tiến độ báo cáo).
#
# Đây là chỗ dễ hiểu nhầm nhất khi đọc lại về sau, nên nói thẳng: màn hình KHÁC bản vẽ ở bốn chỗ,
# và đó là khác CÓ CHỦ Ý. Bản vẽ là bản vẽ của một hệ thống ĐÃ CÓ SỐ; hôm nay VTOS đang dựng.
# TC-42 (16/9/2026) · THỨ TỰ DỰNG LẠI THEO CÁCH ĐỌC, KHÔNG THEO SỐ HIỆU BẢN VẼ.
#
# Anh Tuấn mở bản chạy thật lần nữa và chốt: sáu mục phải NGHĨ mới hiểu (doanh thu · lợi nhuận ·
# dòng tiền · phải thu · phải trả · tồn đọng) thành sáu Ô LỚN có biểu đồ, đứng trên cùng; năm mục
# chỉ để LIẾC (tour đang bán · chờ quyết toán · sắp khởi hành · đội xe · marketing) xuống một hàng
# thẻ nhỏ phía dưới.
#
# Vì thế thứ tự ở đây KHÔNG còn là thứ tự số hiệu của bản vẽ V1.4, và nói thẳng ra để vòng sau
# không "sửa lại cho đúng bản vẽ": bản vẽ xếp theo NHÓM NGHIỆP VỤ (04 vận hành, 05 công nợ, 06
# dòng tiền); màn hình nay xếp theo CÁCH ĐỌC. Ba khối Dòng tiền, Phải thu, Phải trả chuyển hẳn lên
# nhóm sáu ô — không để lại bản sao ở dưới, đúng luật "một con số, một chỗ, một hình" của TC-40.
THU_TU_BAN_VE = [
    "<KhoiQuyetDinh",            # 02  · Cần Chủ tịch quyết định
    "<KhoiDoanhThu",             # Ô 1 · Doanh thu (tháng / quý / năm)
    "<KhoiLoiNhuan",             # Ô 2 · Lợi nhuận trước thuế (tháng / quý / năm)
    "<KhoiDongTien",             # Ô 3 · Dòng tiền — anh Tuấn: "giữ nguyên"
    "<KhoiPhaiThu",              # Ô 4 · Phải thu theo hạn
    "<KhoiPhaiTra",              # Ô 5 · Phải trả theo hạn
    "<KhoiTonDongMuc",           # Ô 6 · Tồn đọng theo mức độ
    "<HangThe",                  # hàng năm thẻ số nhỏ
    "<KhoiHieuQuaXe",            # 04b · Hiệu quả đội xe
]

# Bốn khối đã gỡ. Lắp lại khối nào thì phải có lý do mới và phải sửa phép kiểm này — để việc lắp
# lại là một quyết định, không phải một lần vô tình.
DA_GO = ['id="dieu-hanh"', "<KhoiTonDongBoPhan", "<KhoiRuiRo", "<KhoiTienDoBaoCao"]


def test_bon_khoi_da_go_khong_quay_lai_man_hinh_01():
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    con = [k for k in DA_GO if k in ma]
    assert not con, (
        "Khối đã được anh Tuấn chốt gỡ ngày 15/9/2026 lại xuất hiện trên màn hình 01: "
        + ", ".join(con)
    )


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


def test_dong_tien_dung_giua_nhom_sau_o_va_truoc_hai_khoi_cong_no():
    """SỬA 16/9/2026 (TC-42) — LUẬT GIỮ NGUYÊN, VỊ TRÍ ĐỔI VÌ MÀN HÌNH ĐỔI.

    Luật là MẠCH ĐỌC: cần quyết gì → công ty đang ở đâu → tiền ra vào thế nào → ai nợ mình, mình
    nợ ai. Trước TC-42, "công ty đang ở đâu" là tám thẻ chỉ tiêu cộng khối Hiệu quả đội xe, nên
    Dòng tiền đứng sau đội xe.

    Nay hai ô Doanh thu và Lợi nhuận GÁNH vế "công ty đang ở đâu" — chúng có cả số, cả biểu đồ ba
    kỳ, cả so với kế hoạch. Hiệu quả đội xe thành số liệu của một bộ phận và xuống dưới hàng thẻ.
    Mạch đọc không đổi; thứ đứng ở vế thứ hai thì đổi.
    """
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert ma.index("<KhoiDoanhThu") < ma.index("<KhoiLoiNhuan") < ma.index("<KhoiDongTien"), (
        "Dòng tiền phải đứng sau hai ô kết quả kinh doanh."
    )
    assert ma.index("<KhoiDongTien") < ma.index("<KhoiPhaiThu") < ma.index("<KhoiPhaiTra"), (
        "Dòng tiền phải đứng trước hai khối công nợ: tiền ra vào trước, ai nợ ai sau."
    )

def test_ba_khoi_kinh_doanh_dung_cuoi_va_khong_chen_giua():
    """TC-40: năm khối riêng của VTOS nay còn BA — Kinh doanh Lẻ · Kinh doanh Đoàn · Báo cáo ngày.
    Anh Tuấn chốt giữ ba cái ấy và bỏ hai cái kia ("Việc cần xử lý", "Tồn đọng cần xử lý").

    Luật giữ nguyên: khối riêng của VTOS KHÔNG được chen vào giữa các khối của bản vẽ. Chen vào
    thì đọc từ trên xuống ra một thứ tự khác hẳn bản vẽ dù đủ khối — đúng lỗi đã mất bốn vòng để
    chữa ở TC-31/TC-35.
    """
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    cuoi_ban_ve = ma.index("<KhoiPhaiTra")     # khối cuối cùng của bản vẽ còn trên màn hình
    for moc, ten in (("<KhoiKinhDoanhLe", "Kinh doanh Lẻ"),
                     ("<KhoiKinhDoanhDoan", "Kinh doanh Đoàn"),
                     ("<KhoiBaoCaoNgay", "Báo cáo ngày")):
        assert moc in ma, f"Khối riêng {ten!r} đã biến mất — anh Tuấn chốt GIỮ ba khối này."
        assert ma.index(moc) > cuoi_ban_ve, (
            f"Khối riêng {ten!r} chen vào giữa các khối của bản vẽ."
        )


def test_hai_khoi_rieng_da_go_khong_quay_lai():
    """"Việc cần xử lý" và "Tồn đọng cần xử lý" đã gỡ 15/9/2026. Cái sau trùng thẳng với thẻ chỉ
    tiêu "Tồn đọng cần xử lý" ở tám thẻ — cùng một con số, hai chỗ."""
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    for moc, ten in (('id="viec-cua-toi"', "Việc cần xử lý"), ("<KhoiTonDong ", "Tồn đọng cần xử lý")):
        assert moc not in ma, f"Khối {ten!r} đã được chốt gỡ khỏi màn hình 01."


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
