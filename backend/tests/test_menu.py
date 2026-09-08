"""Menu nhóm nghiệp vụ (Đề xuất 06/9/2026 mục 2 – Đợt 2 mục 5, cập nhật theo chỉ đạo 07/9/2026).

Chốt chặn: mọi màn hình có trong ma trận phân quyền phải nằm trong một nhóm menu, nếu không
người dùng không còn lối vào; và ngược lại, menu không được trỏ tới đường dẫn không tồn tại.

Ngày 07/9/2026 Chủ tịch tách thêm hai đơn vị, nên bản đề xuất 8 nhóm ngày 06/9 thành 10 nhóm:
  - "Kinh doanh & Sản phẩm" tách đôi thành "Kinh doanh Lẻ" và "Kinh doanh Đoàn (MICE)";
  - xe và hướng dẫn viên rời "Điều hành" thành "Vận tải & Hướng dẫn viên".
Phần khẳng định số nhóm và tên nhóm ở đây là ĐẶC TẢ tổ chức nên thay đổi theo chỉ đạo; hai phép thử
lối vào và đường dẫn hỏng phía trên là chốt chặn kỹ thuật, không đổi.
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
    keys = re.findall(r'key:\s*"([a-z_]+)"', block)
    # 11 nhóm từ 07/9/2026: thêm nhóm "Tài khoản của tôi" chứa màn hình đổi mật khẩu. Nhóm này không phải
    # nghiệp vụ – nó tồn tại vì tài khoản còn mật khẩu tạm bị chặn mọi màn hình khác, nên phải có đúng một
    # lối đi mà mọi vai trò đều thấy, kể cả tài xế và chuyên viên visa vốn dùng danh sách cho phép.
    assert len(keys) == 11 and len(set(keys)) == 11, f"phải đủ 11 nhóm, đang có {keys}"
    for ten in ("Điều hành Holdings", "Marketing & CSKH", "Kinh doanh Lẻ", "Kinh doanh Đoàn (MICE)",
                "Điều hành", "Vận tải & Hướng dẫn viên",
                "Tài chính & Kế toán", "Hành chính & Nhân sự", "Kiểm soát & Chính sách", "Hệ thống & Tích hợp"):
        assert ten in block, f"thiếu nhóm {ten}"
    # ba mục đổi tên theo đề xuất
    assert "Báo cáo quản trị" in block and "Báo cáo công việc" in block and "Chính sách & định mức" in block
    assert "Robot báo cáo" not in block and "Tham số chính sách" not in block and "Báo cáo ngày" not in block
    # Hai phòng kinh doanh phải mở ĐÚNG mảng của mình, không cùng trỏ một danh sách rồi để người dùng tự lọc.
    for path in ("/tours?mang=le", "/requests?mang=le", "/bookings?mang=le",
                 "/tours?mang=doan", "/requests?mang=doan", "/bookings?mang=doan"):
        assert path in block, f"menu hai phòng kinh doanh phải trỏ {path}"


def test_muc_chua_xay_duoc_danh_dau_khong_phai_link_hong():
    """Mục chưa có màn hình phải để đường dẫn rỗng (hiện nhãn 'sắp có'), không được trỏ bừa."""
    _, block = menu_paths()
    chua_xay = re.findall(r'"([^"]+)",\s*""\]', block)
    # 08/9/2026 – V6 đã dựng chuỗi bán hàng nên "Giá & chính sách bán", "Báo giá", "Báo giá đoàn" và
    # "Hợp đồng" RỜI khỏi nhóm chưa xây; danh sách kiểm chúng nằm ngay dưới. Còn "Sự cố tour" thì
    # chưa – nó thuộc V7.
    for ten in ("Sự cố tour", "Văn bản"):
        assert ten in chua_xay, f"{ten} phải nằm trong nhóm mục chưa xây"
    assert len(chua_xay) >= 5
    # Đã xây thì phải rời khỏi nhóm "sắp có" và trỏ đúng màn hình – không để cả hai trạng thái cùng lúc.
    for ten, path in (("Công ty thành viên & liên kết", "/companies"), ("Cấu hình tổ chức", "/companies"),
                      ("Tài khoản & phân quyền", "/access"), ("Vị trí AI & quyền hạn", "/ai-roles"),
                      ("Chiến dịch", "/marketing"), ("Kế hoạch & ngân sách", "/marketing?tab=ngansach"),
                      ("Nội dung & thương hiệu", "/noi-dung"), ("Chăm sóc sau bán", "/cham-soc"),
                      ("Phản hồi & khiếu nại", "/khieu-nai"),
                      ("Giá & chính sách bán", "/bang-gia"), ("Báo giá", "/bao-gia?mang=kd_le"),
                      ("Báo giá đoàn", "/bao-gia?mang=kd_doan"), ("Hợp đồng", "/hop-dong-khach")):
        assert ten not in chua_xay, f"{ten} đã có màn hình, không được để 'sắp có'"
        assert f'["{ten}", "{path}"]' in block
