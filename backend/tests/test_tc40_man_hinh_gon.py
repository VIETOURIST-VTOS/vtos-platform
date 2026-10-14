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
BM = GOC / "web" / "components" / "BangBonMoc.tsx"   # TC-63 · bảng bốn mốc đã sang tệp riêng
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

# SỬA 16/9/2026 (TC-42): `<TamThe` đổi tên thành `<HangThe`, và hai khối mới `<KhoiDoanhThu`,
# `<KhoiLoiNhuan`, `<KhoiTonDongMuc` vào danh sách GIỮ. Đổi tên vì hàm nay bày NĂM thẻ chứ không
# tám — một hàm tên "TamThe" bày năm thẻ là một lời nói dối nhỏ nằm ngay trong mã.
# Danh sách BỎ không đổi một dòng: không khối nào anh Tuấn chốt gỡ được lắp lại.
# SỬA 16/9/2026 (TC-44): `<KhoiDoanhThu` + `<KhoiLoiNhuan` → `<KhoiKetQuaKinhDoanh`.
# SỬA 18/9/2026 (TC-65): `<KhoiQuyetDinh` rời danh sách GIỮ vì nó không còn là một khối — hàng
# nút chờ quyết nhập vào thanh ngang `<TieuDe`. Nó KHÔNG sang danh sách BỎ: việc chờ quyết vẫn
# trên màn hình, chỉ là không còn khung riêng. test_tc18 canh cả hai vế.
GIU = ["<HangThe", "<KhoiHieuQuaXe", "<KhoiDongTien",
       "<KhoiKetQuaKinhDoanh", "<KhoiTonDongMuc",
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
    # TC-63 (18/9/2026): hình bốn mốc và câu đọc hộ đổi tệp sang components/BangBonMoc.tsx khi anh
    # Tuấn chốt "chuyển qua gộp với dòng tiền". Luật giữ nguyên: dòng tiền phải có SỐ và có HÌNH,
    # và hình phải có một câu đọc hộ chỉ ra mốc âm sớm nhất.
    t = _doc(BM)
    assert "BieuDoCot" in t, "Bảng bốn mốc phải dùng bộ biểu đồ chung."
    assert "BieuDoDuong" in _doc(DT), "Khối dòng tiền màn hình Chủ tịch phải còn hình 13 tuần."
    assert "docHoDongTien" in t, "Thiếu câu đọc hộ."
    than = t[t.index("function docHoDongTien"): t.index("/** Hình bốn mốc dòng tiền thuần.")]
    # Mốc ÂM SỚM NHẤT là điều đáng lo nhất — nó là hạn phải xoay tiền.
    assert "am[0]" in than, "Câu đọc hộ phải chỉ ra mốc âm SỚM NHẤT, không phải mốc âm nặng nhất."


def test_khoi_06_dong_tien_nay_la_bieu_do_khong_con_bon_o_canh_bao():
    """TC-57 (17/9/2026) · LUẬT NÀY BỊ ĐẢO — GHI LẠI CẢ HAI VẾ.

    ══════════════════════════════════════════════════════════════════════════════════════════
    VẾ CŨ (TC-40, 15/9/2026)
    ══════════════════════════════════════════════════════════════════════════════════════════
    Anh Tuấn chốt "số 6 dòng tiền em giữ nguyên". Em có đề xuất gỡ bốn ô cảnh báo ấy — chúng đều
    ghi "Chưa có nguồn" và lặp lại dòng tóm tắt ngay trên — và anh Tuấn KHÔNG đồng ý. Phép thử này
    sinh ra để vòng sau không ai gỡ chúng lần nữa với cùng một lý do.

    ══════════════════════════════════════════════════════════════════════════════════════════
    VẾ MỚI (TC-57, 17/9/2026)
    ══════════════════════════════════════════════════════════════════════════════════════════
    Anh Tuấn mở trang, chụp đúng bốn ô ấy và bảo: "xoá bỏ cái này khỏi màn hình chủ tịch, thay vào
    đó là biểu đồ và số liệu phân tích dòng tiền ngang ở dưới PHẢI THU VÀ PHẢI TRẢ."

    Điều đổi giữa hai lần KHÔNG phải ý thích. Lần trước, bốn ô ấy là thứ duy nhất nói về dòng tiền
    ngoài một dòng tóm tắt — gỡ đi thì còn lại một khoảng trống, và đó là lý do anh Tuấn giữ. Lần
    này chúng được THAY bằng một biểu đồ 13 tuần cùng bốn con số của một phép cân. Có cái thay thế
    thì mới gỡ được; đó là khác biệt thật giữa hai quyết định, không phải đổi ý.

    Nên phép thử giữ nguyên chỗ đứng và ĐỔI VẾ: nay nó canh rằng bốn ô KHÔNG quay lại, và cái thay
    chúng phải có thật.
    """
    t = _doc(DT)
    assert '<div className="bon-o">' not in t, (
        "Bốn ô cảnh báo đã gỡ khỏi khối dòng tiền (anh Tuấn chốt 17/9/2026) — xem chuỗi tài liệu "
        "của phép thử này để đọc cả hai vế trước khi lắp lại."
    )
    assert "function O({ o }" not in t, (
        "Xoá luôn hàm dựng ô ấy: một thành phần không ai gọi vẫn qua được mọi phép kiểm, và vòng "
        "sau có người dựng lại bốn ô chỉ vì thấy hàm còn nằm đó."
    )
    # TC-59 (chiều cùng ngày) tách `DuBao13Tuan` làm hai — `Hinh13Tuan` (ba đường THU · CHI · TỒN)
    # và `BonMocDuBao` (bốn con số) — để gộp dải chú thích vào GIỮA chúng, trong cùng một khung.
    # Phép thử canh CÁI THAY THẾ CÓ THẬT, nên nó đi theo tên mới chứ không giữ tên cũ: giữ tên cũ
    # là canh một cái tên, còn điều phải canh là "chỗ này không được thành khoảng trống".
    assert "function Hinh13Tuan" in t and "function BonMocDuBao" in t, (
        "Phải có cái THAY THẾ — biểu đồ 13 tuần và bốn con số, không phải khoảng trống."
    )
    assert 'className="dt-moc"' in t, "Bốn con số của phép cân (đầu kỳ · thu · chi · cuối tuần 13)."


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
    có số cho quý.

    SỬA 14/10/2026 (Đợt E17) — VÀ ĐÂY LÀ MỘT PHÉP THỬ ĐÃ BÁO SAI, nên ghi lại cho rõ:

    Bản cũ so ĐÚNG TỪNG KÝ TỰ chuỗi `ky === "thang" ? (d || {}) : {}`. Sau đó có người SIẾT mã chặt
    hơn — thêm điều kiện `&& !moc`, tức là khi đang chọn một mốc thời gian thì kỳ Tháng cũng không
    mượn số mặc định nữa. Luật được giữ chặt hơn, còn phép thử thì đỏ, như thể việc siết là một lỗi.

    Nó đứng đỏ trên main nhiều ngày, và cái giá không phải là chỗ đỏ ấy: một phép thử đỏ mà ai cũng
    biết "đỏ sẵn, kệ nó" là một phép thử đã chết — ngày nó đỏ vì lý do THẬT thì không còn ai nhìn.

    Nay nó canh LUẬT chứ không canh chuỗi ký tự: lối lui (`d`, bộ số kỳ mặc định) chỉ được dùng
    DƯỚI điều kiện có `ky === "thang"`. Thêm điều kiện khác vào vế ấy thì vẫn xanh (siết chặt hơn
    là chuyện tốt); bỏ `ky === "thang"` đi, hoặc đem `d` ra ngoài điều kiện, thì ĐỎ.
    """
    t = _bo_chu_thich_tsx(_doc(V14))
    assert "coNguonKy" in t, "Phải nói ra khi kỳ đang chọn chưa có nguồn số."
    # Mọi chỗ dùng bộ số mặc định `d` làm lối lui, kèm phần điều kiện đứng ngay trước nó.
    loi_lui = list(re.finditer(r"\(\s*d\s*\|\|\s*\{\}\s*\)", t))
    assert loi_lui, (
        "Không còn chỗ nào dùng bộ số kỳ mặc định làm lối lui cho kỳ Tháng. Nếu đã bỏ hẳn lối lui "
        "thì sửa phép thử này cho đúng điều mới — đừng để nó canh một luật không còn ai theo.")
    for m in loi_lui:
        truoc = t[max(0, m.start() - 400):m.start()]
        dieu_kien = truoc.rsplit("?", 1)[0] if "?" in truoc else ""
        assert 'ky === "thang"' in dieu_kien[-200:], (
            "Kỳ Quý và Năm KHÔNG được lấy bộ số của kỳ Tháng làm lối lui: chỗ dùng `d || {}` phải "
            "nằm dưới một điều kiện có `ky === \"thang\"`. Thêm điều kiện khác vào vế ấy thì được, "
            "bỏ điều kiện ấy đi thì không.")

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
    trông dài bằng nhau — tức biểu đồ hết nói lên điều gì.

    ══════════════════════════════════════════════════════════════════════════════════════════
    LUẬT CHIỀU CAO BỊ ĐẢO NGÀY 17/9/2026 — GHI LẠI CẢ HAI VẾ
    ══════════════════════════════════════════════════════════════════════════════════════════
    TC-40 khai `align-items:start` và phép thử này canh nó, với lý lẽ: "khối ngắn bị kéo dài ra
    thành một vùng trống, và vùng trống ấy đọc ra là 'còn cái gì đó chưa hiện'".

    Trên bản chạy thật, điều ngược lại xảy ra. Ba khối cao thấp so le — Kinh doanh Lẻ thường chỉ
    có một câu, Kinh doanh Đoàn có sáu dòng giải thích cách chia lợi nhuận — làm cả hàng cuối
    trang trông như chưa dựng xong. Anh Tuấn mở trang ngày 17/9 và gọi đúng tên: "các ô ở dưới
    cùng chưa cân xứng".

    Nên luật nay là `stretch`. Khoảng trắng BÊN TRONG một khung có viền đọc ra là khoảng thở; ba
    đáy khung lệch nhau thì không đọc ra gì cả. Phép thử giữ nguyên tên và đổi vế, chứ không bị
    xoá — để vòng sau có người định khôi phục `start` thì đọc được vì sao nó đã bị bỏ.
    """
    assert 'className="mh01-hang-3"' in _doc(TRANG)
    c = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.mh01-hang-3\{([^}]*)\}", c)
    assert m, "Thiếu kiểu .mh01-hang-3"
    than = m.group(1).replace(" ", "")
    assert "auto-fit" in than and "minmax(300px" in than, (
        "Ba khối phải tự xuống cột khi mỗi khối hẹp hơn 300px."
    )
    assert "align-items:stretch" in than, (
        "Ba khối phải cao bằng nhau (anh Tuấn chốt 17/9/2026 — xem chuỗi tài liệu của phép thử "
        "này). Đáy ba khung lệch nhau làm cả hàng trông như chưa dựng xong."
    )


def test_khong_dung_mau_go_thang():
    c = _bo_chu_thich_css(_doc(CSS))
    la = set(re.findall(r"#[0-9a-fA-F]{3,8}", c))
    assert la <= {"#fff"}, f"Màu gõ thẳng ngoài chú thích: {sorted(la)}"
