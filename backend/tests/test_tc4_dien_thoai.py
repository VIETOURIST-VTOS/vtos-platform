"""TC-4 · UI-03 — bản điện thoại: canh bốn điều lệnh giao, đọc thẳng mã giao diện.

  P1  KHÔNG cuộn ngang: bảng đổi HÌNH trên điện thoại, không bọc trong một ô cuộn
  P2  mỗi ô trong bảng mang theo NHÃN CỘT của chính nó, và nhãn do bộ phận chung gắn
  P3  thẻ gập được, nhớ trạng thái THEO NGƯỜI DÙNG
  P4  đúng BỐN ô cảnh báo, xếp 2×2 trên điện thoại
  P5  MỘT ô chọn mốc, và tên mốc đang chọn đọc được thành chữ
  P6  vùng bấm đủ to cho ngón tay

Vì sao P1 là điều khó nhất trong bốn điều: cách chữa quen tay là bọc bảng trong một ô cuộn ngang.
Trên điện thoại nó hỏng theo kiểu im lặng – người dùng thấy ba cột đầu, không thấy có cột thứ tư,
và đọc một bảng tiền bị cắt mất cột mà tưởng đã đọc hết. Không ai báo lỗi, vì không ai biết mình
đang thiếu gì. Phép thử này canh đúng chỗ ấy: đổi hình bằng CSS, không bọc ô cuộn, không đo bề rộng
màn hình bằng JavaScript (đo bằng JavaScript thì lần vẽ đầu ở máy chủ luôn đoán sai).
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")
DT = os.path.join(WEB, "components", "dienthoai.tsx")
CSS = os.path.join(WEB, "app", "globals.css")

# Một ngưỡng đổi hình, không hai. Hai ngưỡng gần nhau đẻ ra một khoảng bề rộng mà không bản nào đúng.
NGUONG = "max-width:640px"


def _doc(p: str) -> str:
    assert os.path.exists(p), f"thiếu tệp {os.path.relpath(p, ROOT)}"
    return open(p, encoding="utf-8").read()


def _khoi_dien_thoai(css: str) -> str:
    """Phần CSS nằm trong khối @media của bản điện thoại mà TC-4 thêm vào."""
    i = css.rindex(f"@media ({NGUONG})")
    return css[i:]


# ------------------------------------------------------------------ P1

def test_p1_bang_doi_hinh_chu_khong_cuon_ngang():
    dt = _khoi_dien_thoai(_doc(CSS))
    assert "table.bang-doc td" in dt and "display:block" in dt, \
        "bảng phải đổi sang dạng thẻ trên điện thoại, không giữ nguyên hình bảng"
    # Không được chữa bằng cách bọc ô cuộn: đó đúng là cái hỏng im lặng cần tránh.
    assert not re.search(r"table\.bang-doc[^{}]*\{[^}]*overflow-x\s*:\s*auto", dt), \
        "bảng đọc-được đang bọc ô cuộn ngang – phải đổi hình, không đổi độ rộng"
    assert "overflow-x:hidden" in dt, "thân trang phải có chốt chặn không cho rộng hơn màn hình"


def test_p1b_khong_do_be_rong_man_hinh_bang_javascript():
    """Đo bằng JavaScript thì lần vẽ đầu ở máy chủ luôn đoán sai, và bảng nhảy một cái khi tải xong."""
    ma = _doc(DT)
    for cam in ("window.innerWidth", "matchMedia", "clientWidth", "getBoundingClientRect", "resize"):
        assert cam not in ma, (
            f"bộ phận bản điện thoại dùng '{cam}' để đoán bề rộng – phải đổi hình bằng CSS, "
            f"vì lần vẽ đầu ở máy chủ không có màn hình để đo")


# ------------------------------------------------------------------ P2

def test_p2_moi_o_mang_theo_nhan_cot_va_nhan_do_bo_phan_chung_gan():
    ma, dt = _doc(DT), _khoi_dien_thoai(_doc(CSS))
    assert "data-nhan" in ma, "bộ phận bảng phải gắn nhãn cột vào từng ô"
    assert "attr(data-nhan)" in dt, "trên điện thoại nhãn cột phải hiện ra cạnh giá trị"
    # Nhãn gắn ở MỘT chỗ. Để trang tự gắn thì chỗ nào quên là chỗ ấy hiện một con số không có tên,
    # và cái quên ấy chỉ lộ ra trên điện thoại – nơi gần như không ai thử.
    assert 'data-nhan={c.ten}' in ma, "nhãn phải lấy thẳng từ định nghĩa cột, không nhận từ trang gọi"
    assert "children" not in re.sub(r"/\*.*?\*/", " ", ma, flags=re.S).split("export function BangDoc")[1], \
        "BangDoc không được nhận children tự do – nhận thì trang lại tự dựng td và quên nhãn"


def test_p2b_dau_bang_an_nhung_van_doc_duoc_bang_trinh_doc_man_hinh():
    dt = _khoi_dien_thoai(_doc(CSS))
    kh = re.search(r"table\.bang-doc thead\{([^}]*)\}", dt)
    assert kh, "thiếu luật ẩn đầu bảng trên điện thoại"
    assert "display:none" not in kh.group(1), \
        "đầu bảng bị display:none – trình đọc màn hình mất luôn cấu trúc bảng; dùng clip thay vì bỏ hẳn"
    assert "clip:" in kh.group(1), "ẩn đầu bảng phải dùng clip để trợ năng còn đọc được"


# ------------------------------------------------------------------ P3

def test_p3_the_gap_duoc_va_nho_theo_nguoi_dung():
    ma = _doc(DT)
    assert "export function The(" in ma, "thiếu bộ phận thẻ gập được"
    assert "aria-expanded" in ma, "thẻ gập phải báo trạng thái cho trình đọc màn hình"
    # Nhớ theo NGƯỜI: hai người dùng chung một máy thì người sau không thừa hưởng thẻ người trước gập.
    assert re.search(r"\$\{KHOA_THE\}_\$\{nguoi\}_\$\{ma\}", ma), \
        "khóa nhớ trạng thái thẻ phải kèm tên người dùng"
    assert "nguoi ?" in ma, "không có người dùng thì không nhớ – thà quên còn hơn nhớ nhầm tài khoản"
    # Gập KHÔNG được gỡ phần thân khỏi cây: gỡ thì mỗi lần mở lại phải tải lại dữ liệu.
    assert "hidden={!mo}" in ma, "gập thẻ phải dùng hidden, không gỡ nội dung khỏi cây"


# ------------------------------------------------------------------ P4

def test_p4_dung_bon_o_canh_bao_va_xep_2x2_tren_dien_thoai():
    ma, css = _doc(DT), _doc(CSS)
    assert "o.slice(0, 4)" in ma, "phải cắt đúng bốn ô – 2×2 chỉ là 2×2 khi có bốn"
    assert "Còn {thua}" in ma, "cắt bớt thì phải nói ra, không lặng lẽ bỏ mất một cảnh báo"
    rong = re.search(r"\.bon-o\{([^}]*)\}", css)
    assert rong and "repeat(4,1fr)" in rong.group(1), "màn rộng: bốn ô một hàng"
    dt = _khoi_dien_thoai(css)
    hep = re.search(r"\.bon-o\{([^}]*)\}", dt)
    assert hep and "1fr 1fr" in hep.group(1), "điện thoại: bốn ô xếp 2×2, không phải một cột dài"


# ------------------------------------------------------------------ P5

def test_p5_mot_o_chon_moc_va_ten_moc_doc_duoc_thanh_chu():
    ma = _doc(DT)
    assert "export function ChonMoc(" in ma, "thiếu ô chọn mốc"
    assert ma.count("<select") == 1, "chỉ được MỘT ô chọn mốc trên bản điện thoại"
    assert "Đang xem mốc" in ma, (
        "phải có câu nói tên mốc đang chọn: người dùng cuộn xuống giữa bảng thì ô chọn đã trôi khỏi "
        "màn hình, và một cột tiền không có tên là một cột tiền đọc sai")
    assert 'htmlFor="chon-moc-o"' in ma, "ô chọn phải có nhãn gắn đúng, không phải chữ đứng cạnh"


# ------------------------------------------------------------------ P6

def test_p6_vung_bam_du_to_cho_ngon_tay():
    """Một mũi tên 12px ở góc thì bấm ba lần mới trúng. Đầu thẻ phải là nút chiếm hết bề ngang."""
    css = _doc(CSS)
    dau = re.search(r"\.the-dau\{([^}]*)\}", css)
    assert dau, "thiếu luật cho đầu thẻ gập"
    assert "width:100%" in dau.group(1), "đầu thẻ phải chiếm hết bề ngang để dễ bấm"
    cao = re.search(r"min-height:(\d+)px", dau.group(1))
    assert cao and int(cao.group(1)) >= 44, "vùng bấm phải cao ít nhất 44px theo mức thường dùng cho ngón tay"
