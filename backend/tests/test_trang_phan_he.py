"""TRANG PHÂN HỆ /phan-he/<khoa> – anh Tuấn chốt phương án B ngày 13/9/2026.

Bấm một thanh phân hệ trên menu dọc thì mở mục lục đầy đủ của phân hệ ấy, dựng theo bản vẽ
"VTOS · Cấu trúc phân hệ đề xuất V1.3" (12/9/2026).

VÌ SAO CÓ TRANG NÀY thay vì nhồi cây v1.3 vào menu: v1.3 sâu bốn cấp và liệt kê 184 mục, VTOS thật
có 62 trang. Menu chốt tối đa hai cấp (§I.2) – nhồi vào là vừa phá đặc tả vừa dựng hơn một trăm
đường dẫn hỏng; ẩn phần chưa dựng đi thì không ai còn thấy hệ thống đang nợ những gì.

Phép thử ở đây canh HAI việc mà mắt người dễ bỏ sót khi cây dài:
  1. Mọi đường dẫn trong cây phải là màn hình CÓ THẬT – một mục lục trỏ vào hư không còn tệ hơn
     không có mục lục.
  2. Không màn hình nào của menu bị rơi khỏi cây – nếu rơi thì trang mục lục nói dối về quy mô
     phân hệ.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAY = os.path.join(ROOT, "web", "lib", "cay_phan_he.ts")
TRANG = os.path.join(ROOT, "web", "app", "phan-he", "[khoa]", "page.tsx")
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")

TAM_KHOA = ["tongquan", "marketing", "khachhang", "vanhanh",
            "nhansu", "taichinh", "baocao", "quantri"]


def _cay():
    return open(CAY, encoding="utf-8").read()


def _shell():
    return open(SHELL, encoding="utf-8").read()


def _khong_ghi_chu(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S)


def _duong_dan(src):
    """Mọi href trong một tệp, đã bỏ tham số ?tab=… và neo #… để so với thư mục trang."""
    ra = set()
    for h in re.findall(r'href: "(/[^"]*)"', src):
        ra.add(h.split("?")[0].split("#")[0])
    return ra


def test_du_tam_phan_he_va_dung_khoa_cua_menu():
    """Tám khoá của cây phải TRÙNG khoá nhóm menu, không phải một bộ tên khác.

    Lệch một chữ thì thanh phân hệ dẫn tới /phan-he/<khoa> không có thật và người dùng gặp trang
    "Không có phân hệ này" – lỗi chỉ lộ ra khi bấm đúng nhóm ấy.
    """
    cay = _cay()
    khoa_cay = re.findall(r'khoa: "(\w+)"', cay)
    assert khoa_cay == TAM_KHOA, f"cây phân hệ có {khoa_cay}, phải đúng tám khoá {TAM_KHOA}"
    khoa_menu = re.findall(r'\{ key: "(\w+)", label:', _shell())
    assert khoa_menu == TAM_KHOA, f"menu có {khoa_menu}, lệch khoá với cây phân hệ"


def test_moi_thanh_phan_he_deu_bam_di_duoc():
    """Bảy nhóm nghiệp vụ dẫn tới trang phân hệ; Tổng quan dẫn thẳng bảng điều hành.

    Bảng điều hành CHÍNH LÀ màn hình của phân hệ Tổng quan – dựng thêm một trang mục lục cho nó chỉ
    tổ thêm một cú bấm.
    """
    shell = _khong_ghi_chu(_shell())
    for khoa in TAM_KHOA:
        # ══ TC-69 · 18/9/2026 — NỚI KHUÔN DÒ, KHÔNG ĐỔI LUẬT ═══════════════════════════════════
        # Luật giữ nguyên: mỗi nhóm phải có `href`, và href phải trỏ đúng chỗ. Chỉ khuôn dò là nới.
        # Bản cũ đòi `icon` đứng NGAY SAU `label`. Từ 18/9 nhóm "nhansu" có thêm `label_ngan`
        # ("HC – NS") xen vào giữa, nên khuôn cũ trượt và phép thử báo "không có href" trong khi
        # href vẫn nằm nguyên đó – nó tố cáo sai, chứ mã không hỏng.
        # Khuôn mới cho phép bất kỳ thuộc tính nào nằm giữa `label` và `href`, nhưng `[^{}]*?`
        # KHÔNG cho phép vượt qua dấu ngoặc nhọn, nên nó không thể vơ nhầm `href` của nhóm kế tiếp:
        # cả `key`, `label` và `href` vẫn buộc phải ở trong CÙNG một khai báo nhóm.
        m = re.search(r'\{ key: "%s", label: "[^"]+",[^{}]*?href: "([^"]+)"' % khoa, shell)
        assert m, f"nhóm {khoa} không có href – bấm vào thanh phân hệ sẽ không đi đâu cả"
        mong = "/" if khoa == "tongquan" else f"/phan-he/{khoa}"
        assert m.group(1) == mong, f"nhóm {khoa} trỏ {m.group(1)}, phải là {mong}"


def test_moi_duong_dan_trong_cay_deu_co_trang_that():
    """Mục lục trỏ vào hư không còn tệ hơn không có mục lục.

    Mục CHƯA DỰNG thì để trống href và trang tự ghi "Chưa dựng" – đó là cách nói thật. Cái không
    chấp nhận được là một href trông như thật mà bấm vào ra 404.
    """
    thieu = []
    for h in sorted(_duong_dan(_cay())):
        if h == "/":
            continue
        thu_muc = os.path.join(ROOT, "web", "app", h.strip("/"))
        if not os.path.isfile(os.path.join(thu_muc, "page.tsx")):
            thieu.append(h)
    assert not thieu, f"cây phân hệ trỏ tới trang không tồn tại: {thieu}"


def test_khong_man_hinh_nao_cua_menu_bi_rot_khoi_cay():
    """Menu và cây phải nói cùng một điều về quy mô phân hệ.

    Một màn hình có trong menu mà vắng trong cây nghĩa là trang mục lục đếm thiếu – anh Tuấn đọc
    "12/40 màn hình đã dựng" rồi tưởng còn nợ nhiều hơn thực tế.
    """
    trong_cay = _duong_dan(_cay())
    trong_menu = set()
    shell = _khong_ghi_chu(_shell())
    i = shell.index("export const GROUPS")
    # Dừng ở CA_NHAN: khối cá nhân (đổi mật khẩu, phiếu lương) nằm trên THANH NGANG, không thuộc
    # phân hệ nào – đòi nó có mặt trong cây là đòi sai chỗ.
    j = shell.index("const CA_NHAN")
    for m in re.finditer(r'\["[^"]+",\s*"(/[^"]+)"\]', shell[i:j]):
        trong_menu.add(m.group(1).split("?")[0].split("#")[0])
    thieu = sorted(trong_menu - trong_cay)
    assert not thieu, f"{len(thieu)} màn hình có trong menu nhưng vắng trong cây phân hệ: {thieu}"


def test_tab_khong_bao_gio_thanh_mot_man_hinh_rieng():
    """v1.3 ghi rõ "Tab / nhánh chi tiết": đây là tab BÊN TRONG một trang.

    Gắn href cho một tab là hứa một màn hình không tồn tại; và đếm nó vào tổng số màn hình thì con
    số "đã dựng / tổng" sai ngay từ mẫu số.
    """
    cay = _cay()
    # Đọc theo DÒNG chứ không theo khối: một mục cha có href hoàn toàn có thể chứa các tab bên
    # trong, nên bắt cả khối sẽ báo nhầm chính cái cấu trúc đúng.
    for dong in cay.splitlines():
        if "tab: true" in dong:
            assert "href:" not in dong, f"mục tab không được có đường dẫn riêng: {dong.strip()}"
    assert "if (!m.tab)" in open(TRANG, encoding="utf-8").read() or "!m.tab" in cay, \
        "phép đếm phải loại tab ra khỏi tổng số màn hình"


def test_trang_phan_he_khong_hien_mot_con_so_nghiep_vu_nao():
    """Ranh giới 09/9/2026: Claude viết CẤU TRÚC, không nhập và không tải SỐ LIỆU.

    Trang này là mục lục. Nó không được gọi máy chủ – có gọi là bắt đầu hiện số, mà số trên một
    trang mục lục thì không có cửa nhập nào đứng sau.
    """
    src = open(TRANG, encoding="utf-8").read()
    for cam in ("api(", "fetch(", "useEffect"):
        assert cam not in src, f"trang phân hệ không được {cam} – đây là mục lục, không phải báo cáo"


def test_ghi_ro_muc_nao_con_no():
    """Ba trạng thái phải hiện thành chữ, không chỉ bằng màu: Đã có · Chưa dựng · Tab trong trang."""
    src = open(TRANG, encoding="utf-8").read()
    for nhan in ("Đã có", "Chưa dựng", "Tab trong trang"):
        assert nhan in src, f"thiếu nhãn trạng thái “{nhan}”"


def test_cay_giu_du_muc_cua_ban_ve_v13():
    """184 mã của v1.3 phải có mặt đủ, kể cả mục chưa dựng.

    Bỏ bớt mục chưa dựng cho cây gọn là xoá mất phần việc còn nợ – đúng thứ trang này sinh ra để
    giữ. Con số 184 là số dòng có mã trong bản vẽ v1.3 ngày 12/9/2026.
    """
    ma = re.findall(r'ma: "(\d[\d.]*)"', _cay())
    v13 = [m for m in ma if not m.startswith("0")]
    assert len(set(v13)) >= 184, f"cây chỉ còn {len(set(v13))} mục, bản vẽ v1.3 có 184"


def test_luat_dien_thoai_moi_khong_duoc_nam_duoi_khoi_tc4():
    """Cái bẫy đã sập một lần, 13/9/2026 – ghi lại để không sập lần hai.

    test_tc4_dien_thoai đọc bản điện thoại bằng rindex("@media (max-width:640px)"): nó lấy từ lần
    xuất hiện CUỐI CÙNG tới hết tệp. Thêm một khối 640px xuống cuối globals.css thì bốn phép thử
    TC-4 đỏ, mà thông báo lỗi lại nói về bảng trên điện thoại chứ không hé một chữ nào về vị trí –
    mất nửa giờ mới lần ra. Phép thử này nói thẳng nguyên nhân.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    i = css.rindex("@media (max-width:640px)")
    cuoi = css[i:]
    assert "table.bang-doc" in cuoi, (
        "khối @media (max-width:640px) CUỐI CÙNG của globals.css không còn là khối TC-4 – "
        "luật điện thoại mới phải đặt TRƯỚC nó, nếu không bốn phép thử TC-4 đỏ vì lý do khác hẳn")


def test_khoa_muc_khong_co_quyen_chu_khong_giau_di():
    """Anh Tuấn chốt 13/9/2026: ai cũng thấy đủ tám phân hệ, mục không có quyền thì KHOÁ lại.

    Lần đầu em làm ngược – ẩn hẳn mục không có quyền. Anh Tuấn đổi, và lý do đúng: giấu thì nhân
    viên không biết hệ thống có những gì, không biết phải xin quyền ở đâu, và tưởng phần mềm chưa
    làm chức năng ấy. Cái lộ ra chỉ là TÊN chức năng – trang này không gọi máy chủ, không có một
    con số nghiệp vụ nào (xem phép thử ở trên).

    Luật áp dụng cho MỌI vai trò, kể cả tài xế, hướng dẫn viên và chuyên viên visa.
    """
    src = open(TRANG, encoding="utf-8").read()
    assert "hidden_menus" in src, "trang phân hệ phải đọc hidden_menus của phiên để biết mục nào khoá"
    assert "useShell" in src, "phải lấy người dùng từ Shell, không tự gọi máy chủ"
    assert "Không có quyền" in src, "thiếu nhãn khoá – mục không vào được phải nói ra bằng chữ"
    assert "Tài khoản & phân quyền" in src, "khoá thì phải chỉ chỗ xin quyền, nếu không người ta bế tắc"
    # Hàng chuyển nhanh KHÔNG được lọc: đủ tám phân hệ cho mọi vai là chính điều anh Tuấn chốt.
    assert "CAY_PHAN_HE.filter(" not in src, \
        "hàng chuyển nhanh đang lọc theo quyền – phải hiện đủ tám phân hệ cho mọi vai trò"
    ac = open(os.path.join(ROOT, "backend", "app", "services", "access.py"), encoding="utf-8").read()
    m = re.search(r'MAN_HINH_KHONG_DUOC_AN = \(([^)]*)\)', ac)
    assert m and "/phan-he/[khoa]" in m.group(1), (
        "trang phân hệ phải nằm trong MAN_HINH_KHONG_DUOC_AN – nếu không, ba vai bị giới hạn "
        "(tài xế, HDV, visa) vẫn bị ẩn mất trang mục lục")


def test_menu_giu_du_tam_phan_he_cho_moi_vai_tro():
    """Không nhóm nào rụng khỏi thanh dọc vì vai trò không có màn hình nào trong đó.

    Quyền vẫn nguyên ở hai chỗ khác: bảng xổ ra chỉ liệt kê màn hình vào được, và trang phân hệ
    khoá mục không có quyền.
    """
    src = re.sub(r'/\*.*?\*/|//[^\n]*', '', open(SHELL, encoding="utf-8").read(), flags=re.S)
    assert "filter((g) =>" not in src, \
        "bộ lọc nhóm đã quay lại – tám phân hệ phải hiện đủ với mọi vai trò"


def test_trang_phan_he_da_khai_quyen():
    """test_ai_log đòi mọi trang trong web/app phải khai quyền hoặc nằm trong danh sách mở.

    Trang này khai ở ALL_MENU_PATHS chứ không ở MENU_ROLES: nó không phải màn hình nghiệp vụ, nó chỉ
    liệt kê lại những màn hình người dùng vốn đã được thấy.
    """
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    ac = open(os.path.join(ROOT, "backend", "app", "services", "access.py"), encoding="utf-8").read()
    assert '"/phan-he/[khoa]"' in ac, "trang phân hệ chưa được khai trong ALL_MENU_PATHS"
