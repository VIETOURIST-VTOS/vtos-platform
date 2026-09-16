# -*- coding: utf-8 -*-
"""TC-37 · Hai biểu đồ khối: cơ cấu theo hạn (05) và tồn đọng theo bộ phận (04c).

Anh Tuấn 15/9/2026 gửi mấy mẫu bảng điều hành (Power BI, dashboard bán hàng) và hỏi nên thêm biểu
đồ nào. Vòng này lắp hai cái đã hứa. Ba chỗ trong mẫu anh gửi mà VTOS CỐ Ý không bắt chước, ghi ra
đây vì sau này sẽ có người hỏi "sao không giống mẫu":

  · BÁNH TRÒN 10 PHẦN — mắt so được độ dài, không so được góc. Mười lát thì phải đọc chú thích mới
    biết lát nào là gì; cùng số ấy vẽ thanh ngang xếp thứ tự là đọc xong trong một giây.
  · ĐƯỜNG CONG MƯỢT — đường cong vẽ ra những giá trị NẰM GIỮA hai tháng, mà giữa tháng 5 và tháng 6
    không tồn tại số nào. Đó là số do máy vẽ tự sinh.
  · HAI TRỤC TUNG MỘT BIỂU ĐỒ — đổi thang trục là đổi được kết luận; hai đường cắt nhau ở đâu là do
    người vẽ chọn, không phải do số liệu.

Bộ kiểm này kiểm PHÉP TÍNH và LUẬT VẼ trong mã nguồn màn hình, không cần cơ sở dữ liệu.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
V14 = GOC / "web" / "components" / "KhoiV14.tsx"
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


def _than(nguon: str, ten: str) -> str:
    """Thân của một hàm/thành phần, từ chỗ khai đến chỗ khai kế tiếp."""
    i = nguon.index(ten)
    sau = nguon[i + len(ten):]
    ket = [m.start() for m in re.finditer(r"\nexport (?:function|const)|\nfunction ", sau)]
    return sau[: ket[0]] if ket else sau


# ═════════════════ 05 · THANH CƠ CẤU NĂM NHÓM HẠN ═════════════════

def test_co_cau_doi_du_ca_nam_nhom_moi_ve():
    """Tỉ lệ nào cũng tính trên TỔNG năm nhóm. Thiếu một nhóm thì tổng đã sai, và bốn khúc còn lại
    cùng phình to lên — nhìn vẫn rất hợp lý, nên không ai kiểm được."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "export function coCau"))
    assert "thieu.length" in t and "ve: false" in t
    assert "null" in t and "undefined" in t, "Phải coi cả null lẫn undefined là nhóm thiếu."


def test_co_cau_khong_quy_doi_nhom_thieu_thanh_0():
    t = _than(_doc(V14), "export function coCau")
    assert "không quy đổi nhóm thiếu thành 0" in t, (
        "Câu giải thích phải nói thẳng ra màn hình là không quy đổi — đây là luật 'rỗng khác không'."
    )


def test_co_cau_tu_choi_nhom_am():
    """Một phần âm của một tổng thì không có bề dài nào biểu diễn đúng được."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "export function coCau"))
    assert re.search(r"some\(\(x\)\s*=>\s*x\s*<\s*0\)", t), "Thiếu chốt chặn nhóm âm."


def test_tong_bang_0_la_so_that_khong_phai_cho_trong():
    """0 công nợ là tin tốt và phải được nói ra như tin tốt, khác hẳn 'chưa có nguồn số'."""
    t = _than(_doc(V14), "export function coCau")
    assert "tong === 0" in t
    assert "Đây là số THẬT" in t


def test_be_rong_khuc_dat_bang_flex_grow_khong_phai_phan_tram():
    """Năm khúc cách nhau 2px. Năm bề rộng phần trăm cộng đúng 100% thì tổng cả gap vượt khung và
    khúc CUỐI bị cắt cụt — tức nhóm 'Dài hạn' luôn trông nhỏ hơn sự thật. flex chia phần còn lại
    sau khi trừ gap nên tỉ lệ đúng."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function ThanhCoCau"))
    assert "flexGrow" in t and "flexBasis: 0" in t
    assert "width:" not in t, "Không đặt bề rộng khúc bằng width phần trăm."


def test_moi_khuc_co_title_va_ca_thanh_co_aria_label():
    """Nhận dạng không được chỉ dựa vào màu: người mù màu và người dùng trình đọc màn hình vẫn phải
    biết khúc nào là nhóm nào."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function ThanhCoCau"))
    assert 'role="img"' in t and "aria-label" in t and "title=" in t


def test_chi_hien_ti_le_khi_ve_duoc_thanh():
    """Cùng một mẫu số. In tỉ lệ trong khi còn nhóm thiếu là in ra phần trăm tính trên tổng chưa
    đủ — con số ấy sai mà trông vẫn bình thường."""
    t = _bo_chu_thich_tsx(_doc(V14))
    assert re.search(r"cc\.ve\s*&&\s*<div className=\"v14-han-ty\"", t), (
        "Ô tỉ lệ phải nằm sau điều kiện cc.ve."
    )


def test_qua_han_mang_mau_trang_thai_khong_nam_trong_dai_hạn():
    """'Quá hạn' là tiền ĐÃ trễ, không phải nấc gần nhất của thang hạn còn lại. Tô nó cùng dải với
    bốn nhóm kia là để một khoản đã trễ trông như đầu một hàng đợi bình thường."""
    t = _bo_chu_thich_tsx(_doc(V14))
    assert re.search(r'\{ nhan: "Quá hạn".*do: true', t), "Nhóm Quá hạn phải khai do: true."
    # Phải trả KHÔNG có nhóm trạng thái trong năm nhóm — quá hạn của nó theo dõi riêng ở chân khối.
    pt = t[t.index("const PHAI_TRA"): t.index("function ThanhCoCau")]
    assert "do: true" not in pt, (
        "Phải trả quá hạn đã theo dõi riêng ở chân khối; đánh dấu thêm một nhóm trạng thái trong "
        "năm nhóm là đếm nó hai lần."
    )


def test_dai_mau_mot_sac_dam_dan_theo_han_gan_dan():
    """Năm nhóm là năm nấc của CÙNG một thứ (hạn còn lại), nên phải trông như một dải liên tục.
    Năm màu rời nói đây là năm loại khác nhau, và mắt sẽ đi tìm ý nghĩa của từng màu."""
    c = _bo_chu_thich_css(_doc(CSS))
    do_dam = [float(m) for m in re.findall(r"\.v14-mau-\d\{opacity:([\d.]+)\}", c)]
    assert len(do_dam) == 5, f"Phải đủ năm nấc, đang có {len(do_dam)}"
    assert do_dam == sorted(do_dam, reverse=True), (
        f"Độ đậm phải GIẢM dần theo hạn xa dần, đang là {do_dam}. Ngược thang là làm khoản xa "
        "nhất nổi bật nhất."
    )
    assert re.search(r"\.v14-mau-do\{background:var\(--vtos-danger\)", c)


# ═════════════════ 04c · THANH NGANG TỒN ĐỌNG THEO BỘ PHẬN ═════════════════

def test_duoi_hai_dong_co_so_thi_khong_ve():
    """Một thanh dài hết khung không so sánh với cái gì cả — nó chỉ làm người đọc tưởng bộ phận ấy
    đã chạm một ngưỡng nào đó. Trên bản chạy thật hôm nay đúng là trường hợp này: mọi hồ sơ đều rơi
    vào 'Chưa rõ bộ phận', nên khối không vẽ gì và bảng nói đủ."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function BieuDoBoPhan"))
    assert re.search(r"hang\.length\s*<\s*2\s*\|\|\s*coSo\.length\s*<\s*2", t)


def test_chua_co_so_thi_khung_net_dut_khong_phai_thanh_dai_0():
    """Thanh dài 0 đọc ra là 'bộ phận này sạch', mà sự thật là 'chưa ai đếm'."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function BieuDoBoPhan"))
    assert "v14-bp-khuyet" in t
    assert re.search(r"h\.so === null\s*\n?\s*\?\s*<span className=\"v14-bp-khuyet\"", t)


def test_bang_0_thi_rong_dung_0():
    """0 hồ sơ quá hạn là tin tốt và phải trông đúng như tin tốt. Kéo lên vài pixel 'cho dễ nhìn'
    là nói có hồ sơ ở đó."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function BieuDoBoPhan"))
    assert re.search(r"h\.so === 0 \? 0 :", t), "Giá trị 0 phải cho bề rộng đúng 0."


def test_ba_cot_rong_co_dinh_de_moi_dong_chung_mot_thuoc():
    """Lỗi ĐÃ ĐO trên bản dựng: để cột tên `minmax(90px,168px)` và cột số `auto` thì hai cột ấy co
    giãn theo nội dung TỪNG DÒNG — rãnh dòng 'Chưa rõ bộ phận' (số 1.750) rộng 882,5px trong khi
    rãnh dòng 'Kinh doanh Đoàn' (số 412) rộng 891,8px. Mỗi dòng một thước đo mà nhìn vẫn bình
    thường: đúng loại sai không ai kiểm được."""
    c = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.v14-bp-hang\{[^}]*grid-template-columns:([^;]+);", c)
    assert m, "Không tìm thấy khai cột của .v14-bp-hang"
    cot = m.group(1)
    assert "auto" not in cot, f"Cột co theo nội dung làm lệch thước giữa các dòng: {cot}"
    assert "minmax(0,1fr)" in cot, "Chỉ cột rãnh được co giãn."


def test_chua_co_so_nam_trong_rai_khong_nam_o_cot_so():
    """Hệ quả trực tiếp của phép đo trên: câu 'chưa có số' dài hơn mọi con số, để ở cột số thì nó
    bóp rãnh của chính dòng ấy hẹp hơn hẳn các dòng khác."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function BieuDoBoPhan"))
    rai = t[t.index("v14-bp-rai"): t.index("v14-bp-so")]
    assert "chưa có số" in rai


def test_chua_ro_bo_phan_luon_dung_cuoi_va_mang_mau_khac():
    """Nó KHÔNG phải một bộ phận. Tô cùng màu với các phòng là xếp một chỗ chưa ai nhận ngang hàng
    với một phòng có người chịu trách nhiệm."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "export function xepBoPhan"))
    assert "hang.push" in t, "Dòng chưa rõ phải ĐẨY XUỐNG CUỐI sau khi đã xếp, không trộn vào sổ."
    c = _bo_chu_thich_css(_doc(CSS))
    assert re.search(r"\.v14-bp-thanh\.chua-ro\{background:var\(--vtos-warning\)", c)


def test_dong_chua_co_so_don_xuong_cuoi_khong_coi_nhu_0():
    """Xếp theo độ lớn thì một dòng chưa có số không có chỗ nào cả. Nhét nó vào cuối THEO SỐ 0 là
    gán cho nó một giá trị mà nó không có."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "export function xepBoPhan"))
    assert "a.so === null" in t and "b.so === null" in t, (
        "Hàm xếp phải xử lý null riêng, không để phép trừ chạy trên null."
    )


def test_bieu_do_dung_TRUOC_bang():
    """Nhìn hình là biết bộ phận nào nặng nhất, rồi mới đọc bảng để biết hồ sơ nào, ai chịu, hạn
    nào. Bảng trước biểu đồ thì phải đọc hết bảng mới ra được cái biểu đồ nói trong một giây."""
    t = _bo_chu_thich_tsx(_doc(V14))
    assert t.index("<BieuDoBoPhan") < t.index('<table className="v14-bang">\n                <thead>') \
        or t.index("<BieuDoBoPhan") < t.rindex('<div className="wrap">')


def test_cau_chu_nam_trong_ham_ve_khong_chep_dieu_kien_lan_hai():
    """Đặt câu chú ở nơi gọi thì điều kiện 'có vẽ hay không' phải viết lại lần thứ hai, và hai bản
    chép ấy sớm muộn lệch nhau — lúc ấy màn hình có chú giải cho một biểu đồ không tồn tại."""
    t = _bo_chu_thich_tsx(_than(_doc(V14), "function BieuDoBoPhan"))
    assert "v14-bp-chu" in t, "Câu chú phải nằm trong chính hàm vẽ."


def test_cau_chu_khong_hua_mot_nguong_chua_ai_khai():
    """Thanh dài nhất chỉ là bộ phận tồn nhiều nhất. Nói 'vượt ngưỡng' khi chưa ai khai ngưỡng là
    dựng ra một mốc không tồn tại."""
    t = _doc(V14)
    assert "chưa có ngưỡng nào được khai" in t


# ═════════════════ CHUNG ═════════════════

def test_khong_dung_mau_go_thang_trong_css_moi():
    """Bộ nhận diện VTOS: mọi màu lấy từ biến, trừ #fff."""
    c = _bo_chu_thich_css(_doc(CSS))
    la = set(re.findall(r"#[0-9a-fA-F]{3,8}", c))
    assert la <= {"#fff"}, f"Màu gõ thẳng ngoài chú thích: {sorted(la)}"


def test_khong_ve_banh_tron_o_hai_khoi_nay():
    """Xem đầu tệp kiểm này: mắt so được độ dài chứ không so được góc."""
    t = _bo_chu_thich_tsx(_doc(V14)).lower()
    for xau in ("conic-gradient", "border-radius:50%", "<pie", "doughnut"):
        assert xau not in t, f"Có dấu vết bánh tròn: {xau}"
