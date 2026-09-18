"""Bộ nhận diện VTOS – v1.0 sáng (12/9/2026), v1.1 BẢN TỐI (13/9/2026).

CẬP NHẬT 13/9/2026: anh Tuấn chốt chuyển toàn bộ platform sang NỀN TỐI theo bản vẽ V1.4, và khai
bảng màu ấy THẲNG vào tokens.css thành bản chính thức của bộ nhận diện (chứ không gõ màu thẳng vào
globals.css). Các phép thử dưới đây đổi theo giá trị mới. Bộ màu sáng v1.0 còn nguyên trong phần
chú thích đầu tokens.css.

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


def test_tokens_css_dung_bang_mau_toi_v11():
    """tokens.css là bản GỐC của bộ nhận diện – mọi màu phải khai ở đây, không gõ vào globals.css.

    Bốn giá trị KHÁC bản vẽ V1.4 đều vì đo tương phản, không vì thẩm mỹ; lý do từng cái ghi trong
    phần chú thích đầu tokens.css. Ai muốn kéo chúng về đúng bản vẽ thì phải đo lại trước.

    TC-64 (18/9/2026) · BỐN NẤC CHỮ SÁNG LÊN MỘT BẬC — anh Tuấn: "chỉnh chữ màu trắng sáng trên
    toàn web". Luật của phép thử này KHÔNG đổi một chữ: tokens.css vẫn là bản GỐC, và mọi khác
    biệt so với bản vẽ vẫn phải có một con số đo được đi kèm. Chỉ có bốn giá trị chữ là đổi, và
    hai trong số đó sửa một cái SAI chứ không chỉ làm sáng hơn:
      · `--vtos-text-faint` cũ #7B93A8 trên nền thông tin chỉ đạt 3,96 — dưới ngưỡng AA 4,5;
      · `--vtos-heading` cũ #DCE9F4 TỐI HƠN chính chữ thường, tức tiêu đề mờ hơn thân bài.
    Giá trị cũ giữ lại trong chú thích của tokens.css để đo lại được.
    """
    src = _doc(TOKENS)
    for bien, gia_tri in (("--vtos-nav-bg", "#10273E"),    # bản vẽ --nav
                          ("--vtos-surface", "#091624"),   # bản vẽ --bg
                          ("--vtos-card", "#122C45"),      # bản vẽ --panel
                          ("--vtos-info-bg", "#183550"),   # bản vẽ --panel2
                          ("--vtos-text", "#F4F9FD"),      # TC-64 · sáng lên từ #E8F1F8
                          ("--vtos-text-mute", "#C3D5E4"), # TC-64 · sáng lên từ #9BB2C6
                          ("--vtos-text-faint", "#A7BDD0"),# TC-64 · cũ #7B93A8 chỉ đạt 3,96
                          ("--vtos-success", "#53C49A"),   # bản vẽ --green
                          ("--vtos-warning", "#F4C36A"),   # bản vẽ --gold
                          ("--vtos-line", "#2E4E6B"),      # nâng từ #29445D (bản vẽ chỉ 1,41 lần)
                          ("--vtos-navy", "#6FA8F0"),      # nâng từ #438BEA (chữ 13px chỉ 4,16)
                          ("--vtos-danger", "#FF6B90"),    # nâng từ #FC4D7A (chỉ 4,40)
                          ("--vtos-sky", "#1E63C8"),       # nền nút, chữ trắng 5,72
                          ("--vtos-heading", "#FFFFFF")):   # TC-64 · cũ #DCE9F4, mờ hơn thân bài
        assert re.search(re.escape(bien) + r":\s*" + gia_tri, src, re.I), \
            f"tokens.css thiếu hoặc sai {bien} = {gia_tri}"


def test_bo_mau_sang_v10_van_duoc_ghi_lai():
    """Bỏ hẳn bảng sáng khỏi tệp là mất luôn bản ghi – ngày nào cần dựng lại thì phải đi tìm."""
    src = _doc(TOKENS)
    for cu in ("#14538D", "#F4F7FA", "#0B2545"):
        assert cu in src, f"chú thích đầu tokens.css phải còn ghi bộ màu sáng v1.0 ({cu})"


def test_mot_bien_mot_vai_nen_va_chu_tach_han():
    """Trên nền tối, nền thanh phải tối còn chữ phải sáng – một biến không gánh được cả hai.

    Đây là lỗi dễ mắc nhất khi đổi sang nền tối: giữ nguyên `--vtos-navy` cho cả hai vai thì hoặc
    thanh điều hướng sáng loè, hoặc số liệu thành xanh đậm trên nền đậm không ai đọc được.
    """
    src = _doc(CSS)
    for luat in (r'\.top\{[^}]*\}', r'aside\.side\{[^}]*\}'):
        m = re.search(luat, src)
        assert m and "background:var(--vtos-nav-bg)" in m.group(0), \
            f"nền thanh phải dùng --vtos-nav-bg, đang là: {m.group(0)[:110] if m else '(không thấy)'}"
    m = re.search(r'h2\{[^}]*\}', src)
    assert m and "color:var(--vtos-heading)" in m.group(0), \
        "chữ tiêu đề phải dùng --vtos-heading, không dùng --vtos-navy-dark (đó là màu NỀN rất tối)"


def test_globals_nap_bo_nhan_dien():
    assert '@import "./tokens.css"' in _doc(CSS), "globals.css phải nạp tokens.css ngay đầu tệp"


def test_mot_bang_mau_duy_nhat_khong_doi_theo_may():
    """Anh Tuấn chốt 13/9: LUÔN TỐI theo bản vẽ V1.4 (12/9 từng chốt luôn sáng).

    Điều KHÔNG đổi qua cả hai lần chốt: chỉ có MỘT bảng màu. Khối @media (prefers-color-scheme)
    làm mỗi máy thấy một màu khác nhau, và bộ nhận diện thì chỉ định nghĩa một bảng.
    """
    src = re.sub(r'/\*.*?\*/', '', _doc(CSS), flags=re.S)      # bỏ chú thích rồi mới tìm
    assert "prefers-color-scheme" not in src, \
        "còn khối đổi màu theo cài đặt máy – bộ nhận diện chỉ có MỘT bảng màu"


def test_muc_dang_chon_van_la_lop_phu_trang_14():
    """Quy tắc 1: mục đang chọn làm sáng bằng lớp phủ trắng 14%, KHÔNG đổi sang một màu khác.

    Nền của hai thanh do test_mot_bien_mot_vai canh; ở đây chỉ canh cách đánh dấu mục đang chọn.
    """
    assert "rgba(255,255,255,.14)" in _doc(CSS), "mục đang chọn phải là lớp phủ trắng 14%"


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
    assert '"#10273E"' in lay, "themeColor phải bằng nền thanh ngang, nếu không mép trình duyệt lệch màu"

    shell = _doc(os.path.join(ROOT, "web", "components", "Shell.tsx"))
    assert "/thuong-hieu/vtos-logo-nen-toi.svg" in shell, "thanh ngang phải dùng dấu VTOS bản nền tối"
    m = re.search(r'\.top \.brand \.brand-logo\{[^}]*height:(\d+)px', _doc(CSS))
    assert m and int(m.group(1)) >= 22, f"logo cao {m.group(1) if m else '?'}px – quy tắc 6 đòi ≥ 22px"


def test_ba_phong_duoc_nap():
    """Mục 3 của README: ba phông lấy từ Google Fonts, khai một lần ở tệp gốc."""
    lay = _doc(LAYOUT)
    for phong in ("Space+Grotesk", "Be+Vietnam+Pro", "JetBrains+Mono"):
        assert phong in lay, f"layout.tsx chưa nạp phông {phong.replace('+', ' ')}"
