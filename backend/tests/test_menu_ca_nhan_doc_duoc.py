"""Menu cá nhân trên thanh ngang phải ĐỌC ĐƯỢC — hàng rào thêm 12/10/2026.

CHUYỆN ĐÃ XẢY RA: `globals.css` tô mọi liên kết trong `.top .right` thành `color:#fff`, đúng cho
thanh điều hướng tối. Hộp menu xổ xuống từ tên người dùng lại đặt nền `--vtos-card`, tức TRẮNG —
nên bốn mục trong nó (Báo cáo công việc của tôi · Phiếu lương của tôi · Đổi mật khẩu · Thoát) là
chữ trắng trên nền trắng. Chữ vẫn ở đó, bấm vẫn chạy, không có lỗi nào trong bảng điều khiển.
Chủ tịch bấm vào một hộp trắng trơn mới phát hiện.

VÌ SAO ĐÁNG MỘT HÀNG RÀO, dù nó hẹp: kiểu hỏng này KHÔNG ném lỗi, KHÔNG làm đỏ phép thử nào, và
KHÔNG lộ ra khi đọc mã — màu chữ nằm ở một tệp, cái nền nằm ở tệp khác, và chúng chỉ gặp nhau lúc
trình duyệt dựng hình. Thứ duy nhất bắt được nó là MỘT NGƯỜI NHÌN VÀO MÀN HÌNH, và chỗ ấy thì
không ai nhìn vì menu cá nhân mở ra mỗi tháng một lần.

ĐIỀU HÀNG RÀO NÀY KHÔNG LÀM ĐƯỢC, nói thẳng để không ai yên tâm nhầm: nó KHÔNG kiểm được độ tương
phản thật. Nó chỉ canh đúng hai mắt xích của lần hỏng này — lớp `menu-toi` còn trên hộp, và CSS
còn đặt màu chữ cho liên kết bên trong lớp ấy. Một hộp nền sáng KHÁC mọc lên trong `.top` ngày mai
sẽ hỏng y hệt mà phép thử này im lặng. Hàng rào thật cho cả lớp bệnh ấy là dựng giao diện lên rồi
soi, và máy đang dùng chưa có `node_modules` để làm việc đó.
"""
import os, re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(GOC, "web", "components", "Shell.tsx")
CSS = os.path.join(GOC, "web", "app", "globals.css")


def _doc(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_hop_menu_ca_nhan_co_lop_rieng():
    """Mất lớp này là bốn mục trở lại vô hình, và mất êm ru."""
    s = _doc(SHELL)
    m = re.search(r'<span role="menu"[^>]*>', s, re.S)
    assert m, "không tìm thấy hộp menu cá nhân trong Shell.tsx"
    assert 'className="menu-toi"' in m.group(0), (
        "hộp menu cá nhân không còn lớp `menu-toi`. Nó nằm trong `.top .right`, nơi mọi liên kết "
        "bị tô trắng cho hợp thanh tối, mà nền hộp lại sáng — không có lớp riêng là chữ trắng "
        "trên nền trắng.")


def test_css_dat_mau_chu_cho_lien_ket_trong_menu_ca_nhan():
    s = _doc(CSS)
    assert re.search(r'\.top\s+\.right\s+\.menu-toi\s+a\s*\{[^}]*\bcolor\s*:', s), (
        "CSS không còn đặt màu chữ cho liên kết trong `.menu-toi` — chúng sẽ nhận `color:#fff` "
        "của `.top .right a` và biến mất trên nền sáng của hộp.")


def test_mau_chu_menu_khong_phai_mau_trang():
    """Đặt lại đúng màu trắng thì coi như không sửa gì — phép thử phải bắt được cả cách ấy."""
    s = _doc(CSS)
    m = re.search(r'\.top\s+\.right\s+\.menu-toi\s+a\s*\{([^}]*)\}', s)
    assert m, "không tìm thấy quy tắc màu chữ của menu cá nhân"
    mau = re.search(r'\bcolor\s*:\s*([^;}]+)', m.group(1))
    assert mau, "quy tắc có nhưng không khai màu chữ"
    v = mau.group(1).strip().lower().replace(" ", "")
    assert v not in ("#fff", "#ffffff", "white", "var(--vtos-text-on-navy)"), (
        f"màu chữ của menu cá nhân đang là {v} — trùng với nền sáng của hộp, tức vẫn vô hình.")


def test_go_le_trai_cua_thanh_ngang_khoi_danh_sach_doc():
    """`.top .right a` có `margin-left:10px` cho các mục NẰM NGANG. Trong một danh sách DỌC nó
    thành bốn dòng thụt vào vô cớ — nhỏ, nhưng là thứ làm menu trông như hỏng."""
    s = _doc(CSS)
    m = re.search(r'\.top\s+\.right\s+\.menu-toi\s+a\s*\{([^}]*)\}', s)
    assert m and re.search(r'margin-left\s*:\s*0', m.group(1)), (
        "menu cá nhân chưa gỡ lề trái 10px thừa hưởng từ `.top .right a`")
