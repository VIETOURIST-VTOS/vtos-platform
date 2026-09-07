"""Ma trận phân quyền sau khi giải thể nhóm ALL_SEEING (chỉ đạo 07/9/2026).

Bộ phép thử này chốt một câu duy nhất và chốt cho chặt: "xem tất cả" là đặc quyền của ĐÚNG hai người,
cộng Ban Kiểm soát ở mức chỉ đọc. Trước đây câu đó không đúng – nhóm ALL_SEEING có bảy vai trò, và vì
mỗi màn hình mới đều viết "ALL_SEEING + ai đó" nên bảy vai trò cứ tự động nhìn thấy mọi thứ mới mà
không ai quyết định. Hai Phó TGĐ vì thế đọc được dòng tiền, sổ tiền gửi và nhật ký nghiệp vụ.

Các phép thử "ai MẤT gì" bên dưới cố ý viết thẳng tên vai trò và tên màn hình. Viết bằng công thức thì
công thức đổi theo mã, và phép thử sẽ xanh trong khi quyền đã âm thầm nới ra.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import access as AC
from app.models.core import ROLES

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def xem_duoc(vai: str) -> set:
    if vai in AC.RESTRICTED_ROLE_MENUS: return set(AC.RESTRICTED_ROLE_MENUS[vai])
    return {p for p, v in AC.MENU_ROLES.items() if vai in v}


# ---------- xương sống ----------
def test_chi_ba_vai_tro_xem_duoc_tat_ca():
    tat_ca = set(AC.MENU_ROLES)
    duoc = {r for r in ROLES if xem_duoc(r) == tat_ca}
    assert duoc == {"chutich", "tgd", "bks"}, (
        f"phải đúng Chủ tịch, TGĐ và Ban Kiểm soát xem được tất cả, đang là {sorted(duoc)}")


def test_moi_man_hinh_deu_mo_cho_ba_vai_tro_nen():
    for path, roles in AC.MENU_ROLES.items():
        for r in AC.BASE_VIEW:
            assert r in roles, f"{path} không mở cho {r} – Chủ tịch, TGĐ và Ban Kiểm soát phải xem được mọi màn hình"


def test_nhom_all_seeing_da_bi_go_khoi_ma():
    """Còn một chỗ dùng ALL_SEEING là còn một cửa cho bảy vai trò cũ quay lại."""
    con = []
    for d, _, fs in os.walk(os.path.join(ROOT, "backend", "app")):
        if "__pycache__" in d: continue
        for f in fs:
            if f.endswith(".py") and "ALL_SEEING" in open(os.path.join(d, f), encoding="utf-8").read():
                con.append(os.path.relpath(os.path.join(d, f), ROOT))
    con = [f for f in con if not f.endswith(os.path.join("services", "access.py"))]   # chỉ còn trong lời giải thích
    assert not con, f"còn dùng ALL_SEEING ở: {con}"
    assert not hasattr(AC, "ALL_SEEING"), "hằng số ALL_SEEING phải bị xóa hẳn, không để lại tên"


# ---------- ai mất gì (bảng anh Tuấn duyệt 07/9/2026) ----------
def test_hai_pho_tgd_khong_con_xem_tien_va_so_sach():
    for vai in ("ptgd_doan", "ptgd_mkt"):
        for man in ("/finance", "/bank-accounts", "/accounting", "/audit"):
            assert man not in xem_duoc(vai), f"{vai} vẫn xem được {man}"


def test_truong_phong_dieu_hanh_khong_con_xem_so_tien_gui():
    """Điều hành cần dòng tiền TỪNG TOUR, không cần sổ tiền gửi của công ty."""
    for man in ("/finance", "/bank-accounts"):
        assert man not in xem_duoc("tp_dh"), f"tp_dh vẫn xem được {man}"
    assert "tp_dh" in AC.COST_ROLES, "nhưng vẫn phải xem được giá vốn và dòng tiền tour"


def test_ke_toan_khong_xem_du_lieu_khach_cua_marketing():
    """Kế toán mất Hộp thư đa kênh và Nguồn khách – đây là dữ liệu khách của Marketing, kế toán không có
    việc gì ở đó. CNTT thì GIỮ: chính họ vận hành tích hợp Facebook và Zalo (facebook_poll, subscribe,
    zalo_send_pending đều yêu cầu vai trò cntt), lấy màn hình đi là bắt họ chạy một tích hợp mà không
    nhìn thấy nó. Bảng phân quyền 07/9 ghi CNTT ở dòng này; phần ghi chú của bảng viết ngược, đã sửa."""
    for man in ("/inbox", "/leads"):
        assert man not in xem_duoc("ketoan"), f"ketoan vẫn xem được {man}"
        assert man in xem_duoc("cntt"), f"cntt phải giữ {man} để vận hành tích hợp kênh"


def test_cntt_khong_xem_dong_tien_va_hieu_qua_doi_xe():
    for man in ("/finance", "/bank-accounts", "/hieu-qua-doi-xe"):
        assert man not in xem_duoc("cntt"), f"cntt vẫn xem được {man}"


def test_chi_ke_toan_giu_ba_man_hinh_tien():
    for man in ("/finance", "/bank-accounts"):
        assert set(AC.MENU_ROLES[man]) == set(AC.BASE_VIEW) | {"ketoan"}, f"{man} mở rộng hơn dự kiến"


def test_khoi_kinh_doanh_khong_thay_gia_von():
    for vai in AC.SALES + AC.MARKETING:
        assert vai not in AC.COST_ROLES, f"{vai} không được xem cơ cấu chi phí nhà cung cấp"


def test_khoi_kinh_doanh_khong_xem_doi_xe():
    for vai in AC.SALES + AC.MARKETING:
        for man in ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"):
            assert man not in xem_duoc(vai), f"{vai} vẫn xem được {man}"


# ---------- không ai được cấp thêm ----------
def test_khong_vai_tro_nao_ngoai_ba_vai_tro_nen_xem_qua_mot_nua():
    """Chốt mềm: nếu một vai trò nghiệp vụ bỗng xem được gần hết màn hình thì ma trận đã bị nới ở đâu đó."""
    tong = len(AC.MENU_ROLES)
    for r in ROLES:
        if r in ("chutich", "tgd", "bks"): continue
        n = len(xem_duoc(r))
        assert n <= tong - 3, f"{r} xem được {n}/{tong} màn hình – rà lại xem có nới nhầm không"


def test_moi_vai_tro_deu_co_ban_lam_viec():
    """Vai trò không có màn hình nào là vai trò đăng nhập vào rồi không làm được gì – đã từng xảy ra với
    'hanh_chinh': có trong danh mục nhưng không có trong bất kỳ dòng nào của ma trận."""
    for r in ROLES:
        assert xem_duoc(r), f"vai trò {r} không mở được màn hình nào"


def test_vai_tro_bi_gioi_han_khong_tu_dong_nhan_man_hinh_moi():
    for vai, cho_phep in AC.RESTRICTED_ROLE_MENUS.items():
        assert xem_duoc(vai) == set(cho_phep)
        assert "/doi-mat-khau" in cho_phep, f"{vai} phải đổi được mật khẩu tạm, nếu không là bị khóa ngoài"


def test_ban_kiem_soat_doc_tat_ca_nhung_khong_ghi_duoc():
    assert "bks" in AC.READ_ONLY_ROLES
    assert xem_duoc("bks") == set(AC.MENU_ROLES)
