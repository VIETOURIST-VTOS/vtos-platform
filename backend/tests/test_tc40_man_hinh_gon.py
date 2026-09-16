# -*- coding: utf-8 -*-
"""TC-40 · Màn hình Chủ tịch sau khi anh Tuấn soát từng khối (15/9/2026).

Anh Tuấn mở bản chạy thật, chụp ảnh từng khối và chốt bằng bốn câu:

  · "bỏ khỏi giao diện của chủ tịch những cái này"
  · "hiện tại các mục lặp lại khá nhiều, nên bỏ hết những phần lặp lại trên giao diện CT"
  · "8 mục này em đề xuất làm biểu đồ và số + phân tích ... kết quả đội xe sẽ update hàng ngày
     theo tháng, quý, năm"
  · "số 6 dòng tiền em giữ nguyên" · "dòng tiền rất quan trọng, cần có số và biểu đồ phân tích"

BA LUẬT RÚT RA, và cả ba kiểm được bằng máy:

 1. MỘT CON SỐ — MỘT CHỖ — MỘT HÌNH. Trước vòng này cảnh báo tồn đọng nằm ở BỐN chỗ (thẻ chỉ tiêu ·
    khối 04c · khối "Tồn đọng cần xử lý" · biểu đồ khu 3) và doanh thu nhân viên nằm ở HAI chỗ.
    Bốn chỗ cùng nói một chuyện thì không chỗ nào còn đáng đọc, và đến lúc bốn chỗ ra bốn con số
    thì không ai biết tin chỗ nào.

 2. BIỂU ĐỒ Ở CẠNH CON SỐ NÓ VẼ. Đường đi ba vòng: TC-37 vẽ trong khối → TC-38 gom ra ba khu riêng
    có đánh số → TC-40 đưa về. Gom ra khu riêng nghe rất hợp lý, nhưng trên bản chạy thật nó tách
    con số khỏi hình của chính con số ấy.

 3. KHỐI NÀO CÒN LẠI THÌ PHẢI CÓ ĐỦ BA THỨ: số · hình · một câu đọc hộ. Bốn con số trần thì phải
    tự so trong đầu mới ra được điều đáng lo.

Và một luật KHÔNG đổi, ghi lại vì nó là thứ dễ bị hiểu là đã nới: RANH GIỚI 09/9. Màn hình không
tính ra con số nghiệp vụ nào. Câu "đọc hộ" chỉ diễn đạt lại số máy chủ đã gửi.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
V14 = GOC / "web" / "components" / "KhoiV14.tsx"
KD = GOC / "web" / "components" / "KhoiKinhDoanh.tsx"
DT = GOC / "web" / "components" / "KhoiDongTien.tsx"
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


# ═════════════════ DANH SÁCH GIỮ / BỎ ═════════════════

GIU = ["<KhoiQuyetDinh", "<TamThe", "<KhoiHieuQuaXe", "<KhoiDongTien",
       "<KhoiPhaiThu", "<KhoiPhaiTra",
       "<KhoiKinhDoanhLe", "<KhoiKinhDoanhDoan", "<KhoiBaoCaoNgay"]

BO = ['id="dieu-hanh"', "<KhoiTonDongBoPhan", "<KhoiRuiRo", "<KhoiTienDoBaoCao",
      "<KhoiTonDong ", 'id="viec-cua-toi"']


def test_dung_danh_sach_khoi_anh_Tuan_chot():
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    for k in GIU:
        assert k in ma, f"Màn hình 01 thiếu khối {k} — anh Tuấn chốt GIỮ khối này."
    for k in BO:
        assert k not in ma, (
            f"Khối {k} đã được chốt gỡ ngày 15/9/2026. Lắp lại thì phải có lý do mới và phải sửa "
            f"phép kiểm này — để việc lắp lại là một quyết định, không phải một lần vô tình."
        )


def test_man_hinh_01_khong_con_bang_nao():
    """Hệ quả trực tiếp của luật 1: mọi bảng dài đã về khối của nó hoặc về màn hình của nó. Một
    bảng mọc lại thẳng trong page.tsx là dấu hiệu ai đó đang dựng lại cái vừa gỡ."""
    assert "<table" not in _doc(TRANG)


def test_ma_cua_khoi_da_go_van_con_de_lap_lai_duoc():
    """Gỡ khỏi màn hình KHÔNG phải xoá mã. Các `type` là hợp đồng với máy chủ — bản mô tả những
    trường máy chủ còn nợ; xoá đi là mất bản mô tả."""
    v14 = _doc(V14)
    for k in ("KhoiTonDongBoPhan", "KhoiRuiRo", "KhoiTienDoBaoCao"):
        assert f"export function {k}" in v14, f"Mã của {k} bị xoá — hợp đồng dữ liệu mất theo."
    assert (GOC / "web" / "components" / "KhoiDieuHanh.tsx").exists(), (
        "Khối Điều hành phải được tách thành tệp riêng, không xoá: nó mang theo bốn luật đã phải "
        "trả giá mới có (bảy đầu cột · mốc hoà vốn 0 không phải đạt mốc · không mặc định sẵn "
        "sàng · cuộn trong khung không cắt dòng)."
    )


# ═════════════════ SỐ · HÌNH · CÂU ĐỌC HỘ ═════════════════

def test_moi_khoi_nhan_bieu_do_cua_chinh_no():
    ma = _bo_chu_thich_tsx(_doc(TRANG))
    assert "bieuDoCua(sec)" in ma, "Trang phải dựng bộ biểu đồ một lần rồi giao cho từng khối."
    for khoi, khoa in (("<KhoiPhaiThu", "bd.phai_thu"), ("<KhoiPhaiTra", "bd.phai_tra"),
                       ("<KhoiKinhDoanhLe", "bd.kd_le"), ("<KhoiKinhDoanhDoan", "bd.kd_doan"),
                       ("<KhoiBaoCaoNgay", "bd.bao_cao_ngay")):
        assert khoa in ma, f"Khối {khoi} chưa nhận biểu đồ của nó ({khoa})."


def test_hai_khoi_kinh_doanh_co_cau_doc_ho():
    """Bảng cũ liệt kê từng nhân viên một dòng. Biểu đồ nói đúng ba thứ ấy và thêm thứ tự; câu đọc
    hộ nói cái mà cả hai đều không nói — ai dẫn đầu, mấy người đang âm."""
    t = _doc(KD)
    assert "export function docHoXepHang" in t
    than = t[t.index("export function docHoXepHang"): t.index("export function KhoiKinhDoanhLe")]
    # Số người ÂM và số người BẰNG 0 là hai việc khác nhau: âm là lỗ, 0 là chưa có chuyến nào chốt.
    assert "h.gt < 0" in than and "h.gt === 0" in than, (
        "Câu đọc hộ phải tách 'đang âm' khỏi 'chưa có chuyến nào quyết toán' — gộp hai cái là gọi "
        "một người chưa bán được chuyến nào là người đang lỗ."
    )


def test_cau_doc_ho_khong_tu_tinh_chi_tieu_moi():
    """Ranh giới 09/9 giữ nguyên: màn hình chỉ ĐẾM LẠI dòng máy chủ gửi và nói thành câu."""
    t = _doc(KD)
    than = _bo_chu_thich_tsx(
        t[t.index("export function docHoXepHang"): t.index("export function KhoiKinhDoanhLe")])
    # PHÉP NÀO LÀ "TỰ TÍNH": phép sinh ra một con số KHÔNG có trong dữ liệu máy chủ gửi. Chia và
    # nhân là hai phép đẻ ra chỉ tiêu mới (tỉ lệ, phần đóng góp, bình quân) — cấm hẳn. Cộng dồn
    # (`reduce`) cũng vậy: một cái tổng do màn hình tự cộng là một con số thứ hai cho cùng câu hỏi.
    for phep in (" / ", " * ", "reduce("):
        assert phep not in than, f"Câu đọc hộ đang tự tính: {phep!r}"
    # Cộng và trừ CÓ trong hàm, và cả hai đều không sinh số: `+` nối chuỗi, `-` là hàm so sánh của
    # `sort`. Soi từng dòng để hai phép ấy không lặng lẽ thành một phép tính thật.
    for d in than.split("\n"):
        if " - " in d:
            assert "sort(" in d, f"Phép trừ ngoài hàm so sánh của sort: {d.strip()!r}"
        if " + " in d:
            assert '"' in d, f"Phép cộng không phải nối chuỗi: {d.strip()!r}"


def test_the_chi_tieu_doc_ho_thanh_cau_khong_chi_mot_mui_ten():
    """Bản cũ in "▲ 25.0% 08/2026 so với 07/2026" — đúng nhưng phải tự dịch trong đầu, và khi phần
    trăm không tính được (kỳ trước bằng 0) thì ra "= —", đọc như một lỗi hiển thị.

    Chênh lệch TUYỆT ĐỐI luôn nói được, kể cả khi phần trăm không tồn tại — nên nó đứng trước."""
    t = _bo_chu_thich_tsx(_doc(DAU))
    assert "▲ tăng" in t and "▼ giảm" in t and "= không đổi" in t, (
        "Mũi tên phải đi kèm chữ: người không phân biệt được đỏ–xanh vẫn phải đọc được chiều."
    )
    assert "the-xh-chenh" in t, "Thiếu chênh lệch tuyệt đối — thứ luôn nói được."
    i_chenh = t.index("the-xh-chenh")
    i_pt = t.index("ss.phan_tram !== null")
    assert i_chenh < i_pt, "Chênh lệch tuyệt đối phải đứng TRƯỚC phần trăm."


def test_khoi_dong_tien_co_so_hinh_va_cau_doc_ho():
    """Anh Tuấn: "dòng tiền rất quan trọng, cần có số và biểu đồ phân tích"."""
    t = _doc(DT)
    assert "BieuDoCot" in t, "Khối dòng tiền phải dùng bộ biểu đồ chung."
    assert "docHoDongTien" in t, "Thiếu câu đọc hộ."
    than = t[t.index("function docHoDongTien"): t.index("/** Bốn mốc dòng tiền thuần.")]
    # Mốc ÂM SỚM NHẤT là điều đáng lo nhất — nó là hạn phải xoay tiền.
    assert "am[0]" in than, "Câu đọc hộ phải chỉ ra mốc âm SỚM NHẤT, không phải mốc âm nặng nhất."


def test_khoi_06_dong_tien_giu_nguyen_bon_o_canh_bao():
    """Anh Tuấn chốt "số 6 dòng tiền em giữ nguyên". Em có đề xuất gỡ bốn ô ấy (chúng lặp lại dòng
    tóm tắt ngay trên) và anh Tuấn không đồng ý. Ghi vào bộ kiểm để vòng sau không ai gỡ lần nữa
    với cùng một lý do."""
    t = _doc(DT)
    assert '<div className="bon-o">' in t, "Bốn ô cảnh báo của khối 06 phải giữ nguyên."
    assert "function O({ o }" in t


# ═════════════════ ĐỘI XE: THÁNG · QUÝ · NĂM ═════════════════

def test_doi_xe_co_ba_ky_xem():
    """Anh Tuấn: "kết quả đội xe sẽ update hàng ngày theo tháng, quý, năm"."""
    t = _doc(V14)
    assert "KY_XE" in t
    for ma in ('"thang"', '"quy"', '"nam"'):
        assert ma in t, f"Thiếu kỳ {ma}"
    assert "Cập nhật hằng ngày" in t


def test_ky_chua_co_nguon_thi_KHONG_bay_so_cua_ky_khac():
    """CHỖ RẤT DỄ LÀM SAI: dựng ba nút rồi để cả ba hiện CÙNG một bộ số là nói dối bằng giao diện.
    Người đọc bấm "Quý" thấy số không đổi sẽ kết luận quý bằng tháng, chứ không kết luận là chưa
    có số cho quý."""
    t = _bo_chu_thich_tsx(_doc(V14))
    assert 'ky === "thang" ? (d || {}) : {}' in t, (
        "Kỳ Quý và Năm KHÔNG được lấy bộ số của kỳ Tháng làm lối lui."
    )
    assert "coNguonKy" in t, "Phải nói ra khi kỳ đang chọn chưa có nguồn số."


def test_nut_ky_dang_chon_khac_han_hai_nut_kia():
    """Ba nút gần giống nhau thì người đọc không chắc mình đang xem kỳ nào — và đó là lúc con số
    bị đọc sai nhãn."""
    c = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.v14-ky-nut\.chon\{([^}]*)\}", c)
    assert m, "Thiếu kiểu cho nút kỳ đang chọn."
    assert "background:var(" in m.group(1), "Nút đang chọn phải đổi NỀN, không chỉ đậm hơn chút."
    assert ".v14-ky-nut:focus-visible" in c, "Nút phải có viền khi đi bằng bàn phím."


# ═════════════════ BỐ CỤC ═════════════════

def test_ba_khoi_kinh_doanh_mot_hang_va_xuong_cot_tren_man_hep():
    """Ép ba khối vào 900px thì mỗi khối còn 280px và thanh ngang trong đó ngắn tới mức mọi người
    trông dài bằng nhau — tức biểu đồ hết nói lên điều gì."""
    assert 'className="mh01-hang-3"' in _doc(TRANG)
    c = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.mh01-hang-3\{([^}]*)\}", c)
    assert m, "Thiếu kiểu .mh01-hang-3"
    than = m.group(1).replace(" ", "")
    assert "auto-fit" in than and "minmax(300px" in than, (
        "Ba khối phải tự xuống cột khi mỗi khối hẹp hơn 300px."
    )
    assert "align-items:start" in than, (
        "Không kéo ba khối cao bằng nhau: khối ngắn bị kéo dài ra thành một vùng trống, và vùng "
        "trống ấy đọc ra là 'còn cái gì đó chưa hiện'."
    )


def test_khong_dung_mau_go_thang():
    c = _bo_chu_thich_css(_doc(CSS))
    la = set(re.findall(r"#[0-9a-fA-F]{3,8}", c))
    assert la <= {"#fff"}, f"Màu gõ thẳng ngoài chú thích: {sorted(la)}"
