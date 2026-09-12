"""Bộ nhận diện VTOS v1.0 (09/2026) – anh Tuấn giao 12/9/2026, tệp docs/VTOS_Bo_giao_dien_IT_README.txt.

Tám quy tắc bắt buộc của README nằm ở đây dưới dạng phép thử, vì một quy tắc chỉ ghi trong tệp .txt
thì ba tháng nữa không ai nhớ. Chúng canh MÃ NGUỒN chứ không canh ảnh chụp: đổi một mã màu là đỏ
ngay, không phải chờ ai đó mở trang lên nhìn.

MỘT ĐIỀU KHÔNG CANH ĐƯỢC Ở ĐÂY: bộ nhận diện nói "mỗi màn hình chỉ MỘT nút chính màu navy"
(quy tắc 2). Đếm số nút chính của 76 màn hình bằng biểu thức chính quy thì sai nhiều hơn đúng –
việc ấy phải nhìn từng trang. Đã ghi vào việc còn nợ thay vì dựng một phép thử giả vờ.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = os.path.join(ROOT, "web", "app", "globals.css")
TOKENS = os.path.join(ROOT, "web", "app", "tokens.css")
LAYOUT = os.path.join(ROOT, "web", "app", "layout.tsx")


def _doc(p: str) -> str:
    return open(p, encoding="utf-8").read()


def test_tokens_css_co_du_va_khong_bi_sua():
    """tokens.css là bản GỐC của bộ nhận diện – ánh xạ ở globals.css, không sửa tệp này."""
    src = _doc(TOKENS)
    for bien, gia_tri in (("--vtos-navy", "#14538D"), ("--vtos-navy-dark", "#0B2545"),
                          ("--vtos-sky", "#2E7FB8"), ("--vtos-navy-light", "#5A9BD4"),
                          ("--vtos-success", "#3B8C43"), ("--vtos-danger", "#FC4D7A"),
                          ("--vtos-info", "#2E7FB8"), ("--vtos-surface", "#F4F7FA"),
                          ("--vtos-card", "#FFFFFF"), ("--vtos-line", "#E3E9EF"),
                          ("--vtos-text", "#0B2545")):
        assert re.search(re.escape(bien) + r":\s*" + gia_tri, src, re.I), \
            f"tokens.css thiếu hoặc sai {bien} = {gia_tri}"


def test_globals_nap_bo_nhan_dien():
    assert '@import "./tokens.css"' in _doc(CSS), "globals.css phải nạp tokens.css ngay đầu tệp"


def test_mot_bang_mau_duy_nhat_khong_doi_theo_may():
    """Anh Tuấn chốt 12/9: LUÔN SÁNG theo bộ nhận diện.

    Khối @media (prefers-color-scheme: dark) làm mỗi máy thấy một màu khác nhau – máy anh Tuấn để
    chế độ tối nên thấy nền đen, máy khác thấy nền sáng, và bộ nhận diện thì chỉ có một bảng màu.
    """
    src = re.sub(r'/\*.*?\*/', '', _doc(CSS), flags=re.S)      # bỏ chú thích rồi mới tìm
    assert "prefers-color-scheme" not in src, \
        "còn khối đổi màu theo cài đặt máy – bộ nhận diện chỉ có MỘT bảng màu"


def test_thanh_dieu_huong_navy_dac_va_muc_chon_phu_trang_14():
    """Quy tắc 1: thanh điều hướng trái LUÔN nền #14538D đặc; mục đang chọn làm sáng bằng lớp phủ
    trắng 14%, KHÔNG đổi sang màu khác."""
    src = _doc(CSS)
    m = re.search(r'aside\.side\{[^}]*\}', src)
    assert m and "background:var(--vtos-navy)" in m.group(0), \
        f"thanh dọc phải là navy đặc của bộ nhận diện, đang là: {m.group(0)[:120] if m else '(không thấy)'}"
    m = re.search(r'\.top\{[^}]*\}', src)
    assert m and "background:var(--vtos-navy)" in m.group(0), "thanh ngang cũng phải navy đặc"
    assert "rgba(255,255,255,.14)" in src, "mục đang chọn phải là lớp phủ trắng 14%"


def test_dung_ba_mau_trang_thai_khong_them_mau_thu_tu():
    """Quy tắc 3 + quy tắc 8: chỉ ba màu trạng thái, và không dùng lại xanh ngọc / xanh dương cũ.

    Cách canh: ngoài #fff ra, globals.css không được còn mã màu cứng nào – mọi màu phải đi qua biến
    của bộ nhận diện. Một mã màu gõ thẳng là một màu không ai duyệt.
    """
    src = re.sub(r'/\*.*?\*/', '', _doc(CSS), flags=re.S)
    la = {c.lower() for c in re.findall(r'#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b', src)} - {"#fff", "#ffffff"}
    assert not la, f"còn mã màu gõ thẳng ngoài bộ nhận diện: {sorted(la)}"
    for cam in ("01a381", "01b1f0"):
        assert cam not in src.lower(), f"quy tắc 8: không được dùng lại màu #{cam} của nhận diện cũ"


def test_tien_va_ma_dung_phong_mono():
    """Quy tắc 4: số tiền, mã chứng từ, mã nhân viên đặt bằng JetBrains Mono để cột dóng thẳng."""
    src = _doc(CSS)
    m = re.search(r'\.num\{[^}]*\}', src)
    assert m and "var(--vtos-font-mono)" in m.group(0), \
        f"cột số phải dùng phông mono của bộ nhận diện, đang là: {m.group(0)[:120] if m else '(không thấy)'}"


def test_chu_tren_nen_navy_toi_thieu_13px():
    """Quy tắc 5: chữ trên nền navy tối thiểu 13px, độ đậm từ 400 trở lên.

    Chỉ soi các quy tắc của thanh ngang (.top) và thanh dọc (aside.side) – đó là hai chỗ nền navy.
    """
    # MỘT NGOẠI LỆ, ghi thẳng ra đây để nó là một quyết định chứ không phải một chỗ lọt lưới:
    # `.top .brand small` là dòng "VIETOURIST OPERATING SYSTEM" nằm trong KHỐI LOGO. Quy tắc 5 nói về
    # chữ giao diện – chữ người dùng phải đọc để thao tác. Dòng này không mang thông tin thao tác
    # nào; anh Tuấn yêu cầu 12/9 cho nó nhỏ và mềm hơn để cân với dấu V. Mọi chỗ khác vẫn ≥13px.
    MIEN_TRU = {".top .brand small"}
    src = re.sub(r'/\*.*?\*/', '', _doc(CSS), flags=re.S)
    nho = []
    for m in re.finditer(r'(\.top[^{}]*|aside\.side[^{}]*)\{([^}]*)\}', src):
        ten = m.group(1).strip()
        if ten in MIEN_TRU:
            continue
        for cd in re.findall(r'font-size:\s*([\d.]+)px', m.group(2)):
            if float(cd) < 13:
                nho.append(f"{ten} → {cd}px")
    assert not nho, f"chữ trên nền navy dưới 13px: {nho}"


def test_logo_va_favicon_dung_bo_moi():
    """Quy tắc 6: logo trong giao diện không nhỏ hơn 22px; favicon dùng ô bo góc, không ký hiệu trần."""
    for ten in ("vtos-logo.svg", "vtos-logo-nen-toi.svg", "vtos-logo-trang.svg", "vtos-logo-don-sac.svg"):
        assert os.path.exists(os.path.join(ROOT, "web", "public", "thuong-hieu", ten)), f"thiếu {ten}"
    for ten in ("favicon.ico", "app-icon.svg", "icon-180.png", "icon-192.png", "icon-512.png"):
        assert os.path.exists(os.path.join(ROOT, "web", "public", "favicon", ten)), f"thiếu favicon/{ten}"

    lay = _doc(LAYOUT)
    assert "/favicon/app-icon.svg" in lay and "/favicon/icon-180.png" in lay, \
        "layout.tsx phải khai bộ favicon mới (ô bo góc), không dùng icon-192 trần như trước"
    assert '"#14538D"' in lay, "themeColor phải là navy thương hiệu"

    shell = _doc(os.path.join(ROOT, "web", "components", "Shell.tsx"))
    assert "/thuong-hieu/vtos-logo-nen-toi.svg" in shell, "thanh ngang phải dùng dấu VTOS bản nền tối"
    m = re.search(r'\.top \.brand \.brand-logo\{[^}]*height:(\d+)px', _doc(CSS))
    assert m and int(m.group(1)) >= 22, f"logo cao {m.group(1) if m else '?'}px – quy tắc 6 đòi ≥ 22px"


def test_ba_phong_duoc_nap():
    """Mục 3 của README: ba phông lấy từ Google Fonts, khai một lần ở tệp gốc."""
    lay = _doc(LAYOUT)
    for phong in ("Space+Grotesk", "Be+Vietnam+Pro", "JetBrains+Mono"):
        assert phong in lay, f"layout.tsx chưa nạp phông {phong.replace('+', ' ')}"
