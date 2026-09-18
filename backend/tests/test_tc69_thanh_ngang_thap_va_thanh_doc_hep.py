# -*- coding: utf-8 -*-
"""TC-69 · THANH NGANG THẤP LẠI, THANH DỌC HẸP LẠI — anh Tuấn 18/9/2026, duyệt sau khi xem mockup.

Ba việc, và LOGO KHÔNG NẰM TRONG SỐ ĐÓ: bản mockup đầu em đề xuất đổi sang logo đơn sắc trắng và
bỏ khối chuyển sắc; anh Tuấn xem rồi trả lời "giữ lại logo hiện tại". Nên phương án A ngày 12/9
(khối logo nổi lên khỏi thanh, có dải chuyển sắc, viền sáng, bóng đổ, vệt sáng chéo) ĐỨNG NGUYÊN.
`test_logo_khong_bi_dung_toi` canh đúng chuyện ấy — một vòng sửa bố cục rất dễ tiện tay dọn luôn
mấy lớp trang trí mà không ai yêu cầu.

══════════════════════════════════════════════════════════════════════════════════════════════
CÂU HỎI CỦA ANH TUẤN, VÀ CÂU TRẢ LỜI NẰM Ở MỘT CHỮ TRONG CSS
══════════════════════════════════════════════════════════════════════════════════════════════
Anh hỏi thẳng: *"nếu 73px thì có bị tràn chữ không?"*

Không — và lý do không nằm ở con số 73, mà ở chỗ `.top` khai `min-height` chứ không phải `height`.
Con số ấy là SÀN, không phải TRẦN: nội dung cần cao hơn thì thanh tự nở ra. Đo 90 khổ (2 bản × 3
cỡ chữ × 15 bề rộng): số phần tử bị cắt theo chiều cao là 0 ở tất cả.

Đổi `min-height` thành `height` là xoá đúng tính chất đã trả lời câu hỏi ấy, và màn hình sẽ nuốt
chữ ở cỡ 20px mà không lỗi nào báo. `test_thanh_ngang_la_san_khong_phai_tran` canh chỗ này.

══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ BẢN NHÁP CỦA CHÍNH VÒNG NÀY ĐÃ SAI, ghi lại vì nó là bài học đắt nhất ở đây
══════════════════════════════════════════════════════════════════════════════════════════════
Mockup đầu đề xuất thanh dọc 224px, đo "không cắt chữ". Phép đo ấy chạy khi **Be Vietnam Pro đã
tải xong**. Lúc Google Fonts chưa về, trình duyệt rơi về phông dự phòng RỘNG HƠN 8%, và 224px cắt
nhãn. Chú thích 12/9 trong test_menu đã dặn đúng điều này — bản nháp đọc lướt qua.

Bài học thành luật: **đo bề rộng chữ thì phải đo ở phông DỰ PHÒNG, không phải phông thật.**
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = os.path.join(ROOT, "web", "app", "globals.css")
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")


def _doc(p: str) -> str:
    return open(p, encoding="utf-8").read()


def _khong_chu_thich(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


# ═════════════════ 1 · THANH NGANG ═════════════════

def test_thanh_ngang_thap_lai_dung_64():
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"--top-h:\s*calc\((\d+)/14\*1rem\)", css)
    assert m, "không tìm thấy --top-h dạng co giãn"
    assert int(m.group(1)) == 64, (
        f"--top-h đang là {m.group(1)}, anh Tuấn chốt 64 ở cỡ gốc (tức 73px ở cỡ 16)")


def test_thanh_ngang_la_san_khong_phai_tran():
    """Đây là phép thử TRẢ LỜI CÂU HỎI của anh Tuấn, không phải một phép thử hình thức.

    `min-height` nghĩa là thanh NỞ RA khi nội dung cần — nên hạ chiều cao không bao giờ cắt chữ.
    `height` nghĩa là thanh KHOÁ CỨNG — và lúc ấy chữ ở cỡ 20px bị nuốt, im lặng.
    """
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"\.top\{([^}]*)\}", css)
    assert m, "không tìm thấy luật .top"
    than = m.group(1)
    assert "min-height:var(--top-h)" in than, (
        "`.top` phải khai min-height — đó là thứ làm cho việc hạ chiều cao thanh không cắt chữ.")
    assert not re.search(r"(?<!min-)height:\s*var\(--top-h\)", than), (
        "`.top` không được khai `height` cố định: khoá cứng chiều cao là nuốt chữ ở cỡ chữ lớn.")


def test_dem_doc_thanh_ngang_vua_khoi_logo():
    """Thanh thấp xuống thì đệm dọc phải bớt theo, nếu không khối logo 55px chạm mép.

    6 + 55 + 6 = 67px, nằm trong 64–72px của §I.2 khi tính cả viền dưới.
    """
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"\.top\{([^}]*)\}", css)
    assert re.search(r"padding:6px 16px", m.group(1)), (
        "đệm dọc của thanh ngang phải là 6px sau khi hạ --top-h xuống 64")


# ═════════════════ 2 · THANH DỌC ═════════════════

def test_thanh_doc_hep_lai_va_van_du_cho_nhan_dai_nhat():
    """232px: dư 7px trên trần 225px của nhãn 'Báo cáo – Phân tích' (đo ở phông dự phòng).

    Con số 232 KHÔNG phải làm tròn cho đẹp. 225 đo trên Chromium/Linux; người dùng chạy Windows,
    nơi "system-ui" là Segoe UI với bề rộng khác. 7px là khoảng dự phòng cho chỗ chênh ấy.
    """
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"aside\.side\{flex:0 0 calc\((\d+)/14\*1rem\)", css)
    assert m, "không tìm thấy bề rộng thanh dọc dạng co giãn"
    rong = int(m.group(1))
    assert rong == 232, f"bề rộng thanh dọc đang là {rong}, anh Tuấn chốt 232 ở cỡ gốc"
    assert rong >= 228, "dưới 228 là cắt nhãn khi phông dự phòng chưa về"


def test_nut_phan_he_gon_lai():
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"aside\.side \.grp\{([^}]*)\}", css)
    assert m, "không tìm thấy luật nút phân hệ"
    than = m.group(1)
    assert "padding:11px 12px" in than, "đệm dọc nút phải là 11px (từ 15px)"
    assert "margin:0 8px 6px" in than, "khe giữa hai nút phải là 6px (từ 8px)"


def test_bo_gach_chan_duoi_chu():
    """Anh Tuấn 18/9: "bỏ đường gạch dưới chữ".

    Tám nút là thẻ <a>, mà luật `a{...}` ở đầu tệp KHÔNG tắt gạch chân — nên nếu ai đó lỡ xoá dòng
    `text-decoration:none` thì trình duyệt vẽ lại ngay, và không có gì báo. Đó là lý do phép thử
    này canh dòng ấy chứ không tin là "đã sửa rồi thì thôi".
    """
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"aside\.side \.grp\{([^}]*)\}", css)
    assert "text-decoration:none" in m.group(1), (
        "nút phân hệ phải tắt gạch chân — thẻ <a> mặc định có gạch chân, và luật a{} chung không tắt")


def test_bo_mui_ten_va_khong_de_lai_lop_mo_coi():
    """Anh Tuấn 18/9: "bỏ ... mũi tên của 8 phân hệ này".

    Bỏ thì bỏ CẢ HAI ĐẦU: thẻ trong Shell.tsx và lớp `.grp-mui` trong globals.css. Để lại lớp mồ
    côi là vòng sau có người thấy nó, tưởng còn dùng, rồi dựng lại mũi tên — đúng bài học TC-60.
    """
    assert "grp-mui" not in _doc(SHELL), "thẻ mũi tên vẫn còn trong Shell.tsx"
    css = _khong_chu_thich(_doc(CSS))
    assert ".grp-mui" not in css, (
        "lớp .grp-mui vẫn còn trong globals.css (ngoài chú thích) — xoá cả lớp, đừng để mồ côi")
    assert "`.grp-mui` ĐÃ XOÁ" in _doc(CSS), (
        "phải giữ chú thích ghi lại lớp ấy từng nói gì và vì sao bỏ — không xoá im lặng")


# ═════════════════ 3 · NHÃN NGẮN, NHƯNG TÊN THẬT KHÔNG MẤT ═════════════════

def test_nhan_menu_ngan_lai_ma_ten_phan_he_giu_nguyen():
    """Anh Tuấn 18/9: "đổi nhãn menu thành HC – NS".

    CHỮ VẼ RA ngắn lại; TÊN PHÂN HỆ thì không. Rút gọn thẳng `label` là rút gọn tên phân hệ trong
    cả hệ thống — trong khi việc được giao chỉ là chữ vẽ ra cho vừa thanh dọc.
    """
    src = _doc(SHELL)
    assert 'label: "Nhân sự – Hành chính"' in src, (
        "TÊN phân hệ phải giữ nguyên — chỉ chữ vẽ ra mới rút gọn.")
    assert 'label_ngan: "HC – NS"' in src, "thiếu nhãn ngắn cho thanh dọc"
    assert "label_ngan?: string" in src, "kiểu Group phải khai trường nhãn ngắn"


def test_re_chuot_van_doc_duoc_ten_day_du():
    """Bớt chữ thì thứ nó nói phải còn ở đâu đó — luật của kho, và ở đây là `title` + `aria-label`.

    "HC – NS" một mình không cho ai biết đó là phân hệ gì. Người dùng chuột đọc được ở nhãn rê,
    người dùng máy đọc màn hình đọc được ở aria-label — miễn là hai chỗ ấy vẫn giữ `g.label`.
    """
    src = _doc(SHELL)
    assert "title={g.label} aria-label={g.label}" in src, (
        "title và aria-label phải giữ TÊN ĐẦY ĐỦ, không được đổi sang nhãn ngắn.")
    assert "{g.label_ngan || g.label}" in src, (
        "chữ vẽ ra dùng nhãn ngắn, và rơi về tên đầy đủ khi nhóm không khai nhãn ngắn.")


# ═════════════════ 4 · LOGO KHÔNG ĐƯỢC ĐỤNG TỚI ═════════════════

def test_logo_khong_bi_dung_toi():
    """Anh Tuấn 18/9: "giữ lại logo hiện tại" — sau khi em đề xuất đổi sang đơn sắc trắng.

    Vòng này sửa bố cục, và một vòng sửa bố cục rất dễ tiện tay dọn luôn mấy lớp trang trí. Bốn
    thứ dưới đây là phương án A anh Tuấn chọn ngày 12/9; bỏ cái nào cũng là đảo một quyết định mà
    anh vừa nhắc lại là không đảo.
    """
    css = _doc(CSS)
    m = re.search(r"\.top \.brand\{([^}]*)\}", _khong_chu_thich(css))
    assert m, "không tìm thấy luật khối logo"
    than = m.group(1)
    assert "linear-gradient(112deg" in than, "dải chuyển sắc của khối logo bị bỏ"
    assert "border:1px solid rgba(255,255,255,.20)" in than, "viền sáng của khối logo bị bỏ"
    assert "box-shadow" in than, "bóng đổ của khối logo bị bỏ"
    assert ".top .brand::after" in _khong_chu_thich(css), "vệt sáng chéo của khối logo bị bỏ"

    src = _doc(os.path.join(ROOT, "web", "components", "Shell.tsx"))
    assert "vtos-logo-nen-toi.svg" in src, (
        "tệp logo phải giữ nguyên bản ba màu — bản đơn sắc trắng đã bị anh Tuấn bác.")


# ═════════════════ 5 · VÙNG NỘI DUNG NHẬN ĐÚNG PHẦN NHẢ RA ═════════════════

def test_thanh_doc_va_noi_dung_cung_mot_con_so():
    """Thanh dọc nhả ra bao nhiêu thì nội dung chính nhận bấy nhiêu — không có con số thứ ba.

    `main` không khai bề rộng cố định; nó lấy phần còn lại của hàng ngang. Ai đó đặt `width` cho
    `main` là lúc hai bên bắt đầu cãi nhau và phần nhả ra rơi vào khoảng trống.
    """
    css = _khong_chu_thich(_doc(CSS))
    m = re.search(r"\.shell\{([^}]*)\}", css)
    assert m, "không tìm thấy luật .shell"
    assert "display:flex" in m.group(1), ".shell phải là hàng ngang để nội dung tự lấy phần còn lại"
