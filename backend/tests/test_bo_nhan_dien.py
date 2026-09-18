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


def test_mau_khong_tu_doi_theo_may_khi_nguoi_dung_chua_chon():
    """LUẬT NÀY ĐÃ BỊ ĐẢO MỘT NỬA NGÀY 18/9/2026. Ghi cả hai bên, vì cả hai đều đúng vào thời của nó.

    ══ BÊN CŨ · 13/9/2026 ════════════════════════════════════════════════════════════════════
    Tên cũ của phép thử: `test_mot_bang_mau_duy_nhat_khong_doi_theo_may`.
    globals.css chép nguyên văn: *"Vẫn KHÔNG có khối @media (prefers-color-scheme): màu không được
    đổi theo cài đặt của máy, vì như thế hai người mở cùng một trang thấy hai màu khác nhau."*
    Lúc ấy hệ thống chỉ có MỘT bảng màu, và người dùng không có cách nào chọn.

    ══ BÊN MỚI · 18/9/2026 ═══════════════════════════════════════════════════════════════════
    Anh Tuấn giao mục "Theo hệ thống" trong bảng chọn giao diện. Nay có HAI bảng màu, và người
    dùng chọn lấy một. Lý do cũ yếu đi thật: hồi 13/9 màu đổi là do CÀI ĐẶT MÁY TỰ NHẢY, không ai
    chọn; nay là NGƯỜI DÙNG TỰ CHỌN và biết mình đang chọn gì.
    Cái giá thì vẫn còn và vẫn thật, ghi lại để đừng ai quên: chụp màn hình gửi cho người khác thì
    người mở ở nền kia thấy màu khác, và hai bên bàn với nhau về "ô màu đỏ đó" sẽ lệch nhau.

    ══ PHẦN KHÔNG ĐẢO, VÀ VÌ SAO PHÉP THỬ NÀY CÒN SỐNG ═══════════════════════════════════════
    Khẳng định giữ nguyên: globals.css và tokens.css KHÔNG được chứa @media (prefers-color-scheme).
    Nhưng lý do đã khác. Một khối như thế trong CSS áp cho MỌI người, kể cả người chưa chọn gì và
    người đã cố ý chọn "Navy tối" – tức nó cướp mất chính cái lựa chọn mà vòng TC-67 vừa dựng.
    Nền "Theo máy" được giải quyết trong JavaScript (`matchMedia` ở ChonGiaoDien.tsx và ở kịch bản
    đầu layout.tsx), và CHỈ chạy cho người đã chọn "may". Đó là khác biệt giữa "máy quyết" và
    "người chọn để máy quyết".
    """
    for tep, ten in ((CSS, "globals.css"), (TOKENS, "tokens.css")):
        src = re.sub(r'/\*.*?\*/', '', _doc(tep), flags=re.S)      # bỏ chú thích rồi mới tìm
        assert "prefers-color-scheme" not in src, (
            f"{ten} còn khối đổi màu theo cài đặt máy – nó áp cho cả người đã cố ý chọn Navy tối. "
            'Nền "Theo máy" phải giải quyết bằng matchMedia trong JavaScript, chỉ cho người đã chọn.')

    # Và bên kia của luật: hai bảng màu PHẢI cùng tồn tại, cùng khoá trên `data-nen`.
    tok = _doc(TOKENS)
    assert ':root[data-nen="sang"]' in tok, "thiếu bảng màu sáng – mục 2 của yêu cầu 18/9 chưa có"
    assert re.search(r'^:root\s*\{', tok, re.M), "thiếu bảng màu tối ở :root – bản tối vẫn là mặc định"


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

    ══ ĐƠN VỊ ĐỔI 18/9/2026 (TC-67), NGƯỠNG KHÔNG ĐỔI ═════════════════════════════════════════
    TRƯỚC:  globals.css viết `font-size:13px`; phép thử đọc thẳng con số 13.
    TỪ NAY: viết `font-size:calc(13/14*1rem)`, để cỡ chữ đi theo lựa chọn của người dùng.

    Chia cho 14 vì thân bài TRƯỚC TC-67 là 14px: khi người dùng để núm ở 14 thì `13/14*1rem` ra
    đúng 13px, y hệt bản cũ. Tử số vì thế vẫn đúng nghĩa "13px ở cỡ gốc", và phép thử đọc tử số.
    Ngưỡng 13 của Quy tắc 5 giữ nguyên từng chữ.

    CÂU HỎI THẬT LÀ: kéo núm xuống thì có tụt dưới 13px không? KHÔNG – núm dừng ở 14, mà 14 chính
    là cỡ gốc, nên cỡ nhỏ nhất người dùng chọn được cũng vừa đúng bằng hôm nay. Đây là lý do dải
    cỡ chữ bắt đầu từ 14 chứ không từ 12: một dải rộng hơn trông thì rộng rãi, nhưng nó phá đúng
    quy tắc này mà không màn hình nào báo.
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
        # Nhận CẢ HAI cách viết: `13px` (bản trước TC-67) và `calc(13/14*1rem)` (từ TC-67).
        # Giữ lại nhánh đọc `px` chứ không xoá: nó vẫn phải bắt được, phòng khi ai đó gõ lại một
        # con số px cứng vào thanh navy – lúc ấy chữ không co giãn theo người dùng nữa, và đó là
        # một lỗi khác cũng cần bị chặn.
        for cd in re.findall(r'font-size:\s*(?:calc\(\s*([\d.]+)\s*/\s*14\s*\*\s*1rem\s*\)|([\d.]+)px)',
                             m.group(2)):
            so = float(cd[0] or cd[1])
            if so < 13:
                nho.append(f"{ten} → {so}px ở cỡ gốc")
    assert not nho, f"chữ trên nền navy dưới 13px: {nho}"


def test_moi_co_chu_deu_co_gian_theo_nguoi_dung():
    """TC-67 · KHÔNG CÒN MỘT CỠ CHỮ NÀO KHOÁ CỨNG BẰNG px trong globals.css.

    Anh Tuấn 18/9/2026 mục 4: "áp dụng cho toàn hệ thống … tiêu đề, nhãn giãn theo tỉ lệ".
    Sót MỘT khai báo px là một chỗ trên màn hình không giãn theo, và nó lọt lưới đúng kiểu khó
    thấy nhất: người dùng kéo cỡ chữ lên 20, cả trang to lên, riêng một cái nhãn đứng nguyên – ai
    cũng thấy là lạ mà không ai chỉ ra được chỗ nào.

    Canh Ở ĐÂY chứ không canh trong vòng TC-67 rồi thôi: luật này phải sống lâu hơn cái vòng đẻ ra
    nó. Người viết màn hình mới sáu tháng nữa sẽ gõ `font-size:12px` theo thói quen, và phải có
    cái gì đó chặn lại ngay lúc ấy.
    """
    src = re.sub(r'/\*.*?\*/', '', _doc(CSS), flags=re.S)
    sot = re.findall(r'font-size:\s*[\d.]+px', src)
    assert not sot, (
        f"còn {len(sot)} cỡ chữ khoá cứng bằng px: {sot[:6]} – "
        "viết `calc(N/14*1rem)` để chữ đi theo lựa chọn cỡ chữ của người dùng")


def test_hai_bang_mau_cung_du_bon_nac_chu():
    """TC-67 · Bản sáng phải khai ĐỦ bốn nấc chữ, không được thiếu nấc nào.

    Thiếu một nấc thì nấc ấy rơi về giá trị của BẢN TỐI – tức một màu chữ sáng nằm trên nền trắng,
    gần như vô hình. Kiểu hỏng này không làm trang vỡ, không có lỗi nào trong bảng điều khiển, chỉ
    có một dòng chữ mà người dùng phải nghiêng màn hình mới đọc được.

    Bốn nấc chứ không phải "có khai là được": bản tối cố ý giữ bốn nấc để phân biệt chữ chính với
    chữ phụ; bản sáng gộp bớt là mọi màn hình đọc ra thành một khối chữ phẳng.
    """
    khoi = re.search(r':root\[data-nen="sang"\]\s*\{(.*?)\}', _doc(TOKENS), re.S)
    assert khoi, 'tokens.css chưa có khối :root[data-nen="sang"] – bản sáng chưa tồn tại'
    than = khoi.group(1)
    for bien in ("--vtos-text", "--vtos-heading", "--vtos-text-mute", "--vtos-text-faint",
                 "--vtos-surface", "--vtos-card", "--vtos-line"):
        assert re.search(rf'{bien}\s*:', than), f"bản sáng thiếu {bien} – nấc này sẽ rơi về màu của bản tối"


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
