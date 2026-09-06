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
    src = open(SHELL, encoding="utf-8").read()
    block = src[src.index("export const GROUPS"):src.index("const isOn")]
    return set(re.findall(r'\["(/[^"]*)",', block)), block


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
    assert "Báo cáo quản trị tự động" in block and "Báo cáo công việc" in block and "Chính sách & định mức" in block
    assert "Robot báo cáo" not in block and "Tham số chính sách" not in block and "Báo cáo ngày" not in block
