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
        m = re.search(r'\{ key: "%s", label: "[^"]+", icon: "\w+", href: "([^"]+)"' % khoa, shell)
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
