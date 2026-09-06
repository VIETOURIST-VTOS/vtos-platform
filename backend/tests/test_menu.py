"""Menu 8 nhóm nghiệp vụ (Đề xuất 06/9/2026 mục 2 – Đợt 2 mục 5).

Chốt chặn: mọi màn hình có trong ma trận phân quyền phải nằm trong một nhóm menu, nếu không
người dùng không còn lối vào; và ngược lại, menu không được trỏ tới đường dẫn không tồn tại.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import access as AC

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")


def menu_paths():
    """Đường dẫn trong menu, bỏ phần ?tab=; mục có đường dẫn rỗng là phần chưa xây ("sắp có")."""
    src = open(SHELL, encoding="utf-8").read()
    block = src[src.index("export const GROUPS"):src.index("/** Vai trò")]
    hrefs = re.findall(r',\s*"(/[^"]*)"\]', block)
    return {h.split("?")[0] for h in hrefs}, block


def test_moi_man_hinh_deu_co_loi_vao():
    paths, _ = menu_paths()
    for p in AC.MENU_ROLES:
        assert p in paths, f"{p} có trong ma trận phân quyền nhưng không nằm trong nhóm menu nào"


def test_menu_khong_tro_toi_trang_khong_ton_tai():
    paths, _ = menu_paths()
    app_dir = os.path.join(ROOT, "web", "app")
    for p in paths:
        d = app_dir if p == "/" else os.path.join(app_dir, p.strip("/"))
        assert os.path.exists(os.path.join(d, "page.tsx")), f"menu trỏ tới {p} nhưng không có trang"


def test_du_tam_nhom_va_dat_ten_theo_de_xuat():
    _, block = menu_paths()
    keys = re.findall(r'key:\s*"([a-z]+)"', block)
    assert len(keys) == 8 and len(set(keys)) == 8, f"phải đủ 8 nhóm nghiệp vụ, đang có {keys}"
    for ten in ("Điều hành Holdings", "Marketing & CSKH", "Kinh doanh & Sản phẩm", "Điều hành",
                "Tài chính & Kế toán", "Hành chính & Nhân sự", "Kiểm soát & Chính sách", "Hệ thống & Tích hợp"):
        assert ten in block, f"thiếu nhóm {ten}"
    # ba mục đổi tên theo đề xuất
    assert "Báo cáo quản trị" in block and "Báo cáo công việc" in block and "Chính sách & định mức" in block
    assert "Robot báo cáo" not in block and "Tham số chính sách" not in block and "Báo cáo ngày" not in block


def test_muc_chua_xay_duoc_danh_dau_khong_phai_link_hong():
    """Mục chưa có màn hình phải để đường dẫn rỗng (hiện nhãn 'sắp có'), không được trỏ bừa."""
    _, block = menu_paths()
    chua_xay = re.findall(r'"([^"]+)",\s*""\]', block)
    for ten in ("Tài khoản & phân quyền", "Vị trí AI & quyền hạn", "Báo giá", "Hợp đồng"):
        assert ten in chua_xay, f"{ten} phải nằm trong nhóm mục chưa xây"
    assert len(chua_xay) >= 15
    # Đã xây thì phải rời khỏi nhóm "sắp có" và trỏ đúng màn hình – không để cả hai trạng thái cùng lúc.
    for ten in ("Công ty thành viên & liên kết", "Cấu hình tổ chức"):
        assert ten not in chua_xay, f"{ten} đã có màn hình, không được để 'sắp có'"
        assert f'["{ten}", "/companies"]' in block
