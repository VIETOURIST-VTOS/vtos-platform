"""Nhật ký AI và quyền ba màn hình đội xe (chỉ đạo 07/9/2026).

Hai chốt chặn ở đây khác nhau về bản chất:
  - Phần quyền chốt một QUY ƯỚC dễ tái phạm: màn hình mới thêm vào giao diện mà quên khai quyền thì
    theo mặc định ai đăng nhập cũng thấy. Đã xảy ra hai lần (tài khoản ngân hàng, rồi ba màn hình đội xe).
  - Phần nhật ký chốt một LỜI HỨA: mọi lần dùng mô hình ngôn ngữ đều để lại vết, kể cả khi mô hình
    không gọi được và phần mềm rơi về câu trả lời theo quy tắc.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import access as AC
from app.services import ai_log as AL
from app.models.core import AI_TASKS, AI_LEVELS, AI_REVIEW_STATES

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ba_man_hinh_doi_xe_da_khai_quyen():
    for p in ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"):
        assert p in AC.MENU_ROLES, f"{p} chưa khai quyền – mặc định là mọi vai trò đăng nhập đều xem được"


def test_kinh_doanh_khong_con_xem_duoc_gia_von_doi_xe():
    """Nhân viên kinh doanh không có việc gì trên giá vốn và lợi nhuận đội xe."""
    for vai in ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt"):
        for p in ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"):
            assert vai not in AC.MENU_ROLES[p], f"{vai} vẫn xem được {p}"


def test_chu_tich_tgd_va_ban_kiem_soat_van_xem_duoc():
    for vai in AC.BASE_VIEW:
        for p in ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"):
            assert vai in AC.MENU_ROLES[p], f"{vai} phải xem được {p}"


def test_moi_trang_giao_dien_deu_duoc_khai_quyen_hoac_co_trong_danh_sach_mo():
    """Chốt chặn chống tái phạm: trang mới trong web/app phải hoặc khai quyền, hoặc nằm trong danh sách
    mở cho mọi người một cách CÓ Ý THỨC. Không có lựa chọn thứ ba là quên."""
    app_dir = os.path.join(ROOT, "web", "app")
    # `/y-kien/[ma]` là trang CÔNG KHAI cho khách tự chấm điểm sau tour (25/9/2026): khách không
    # có tài khoản nên không có vai trò nào để khai. Nó không dùng Shell, không gọi hàm `api` của
    # kho, và cửa máy chủ của nó khai ở tools/ks2_khai_quyen.CONG_KHAI kèm lý do.
    # `/cong` (CG-1) là cổng NGOÀI cho khách hàng / đối tác / cổ đông: phiên riêng (goiCong), không
    # dùng vai trò nhân viên nên không có gì để khai trong MENU_ROLES.
    # `/ban-kd-le` (R5-5, 13/11/2026): chỉ chuyển hướng sang /fit, không vẽ gì — miễn khai như /payroll ở
    # ks_ma_tran.NGOAI_LE (test_ks_ma_tran kiểm nó vẫn chỉ là trang chuyển hướng).
    bo_qua = {"/login", "/tours/[id]", "/y-kien/[ma]", "/cong", "/ban-kd-le"}   # đăng nhập · trang con /tours · trang khách · cổng ngoài
    for d, _, fs in os.walk(app_dir):
        if "page.tsx" not in fs: continue
        rel = os.path.relpath(d, app_dir).replace(os.sep, "/")
        p = "/" if rel == "." else "/" + rel
        if p in bo_qua or p.startswith("/kham-pha/"): continue   # /kham-pha/*: cửa hàng công khai cho khách
        assert p in AC.MENU_ROLES or p in AC.ALL_MENU_PATHS, (
            f"trang {p} chưa khai quyền trong MENU_ROLES và cũng không nằm trong ALL_MENU_PATHS – "
            f"nghĩa là mọi vai trò đăng nhập đều thấy mà không ai quyết định điều đó")


def test_bam_dau_vao_on_dinh_va_khong_lo_noi_dung():
    a = AL.bam("xin chào", "khách A")
    assert a == AL.bam("xin chào", "khách A"), "cùng dữ liệu vào phải ra cùng mã băm"
    assert a != AL.bam("xin chào", "khách B")
    assert len(a) == 64 and "khách" not in a
    # ghép chuỗi không được làm hai đầu vào khác nhau ra cùng mã băm
    assert AL.bam("ab", "c") != AL.bam("a", "bc")


def test_danh_muc_tac_vu_va_muc_khop_dac_ta():
    assert set(AI_LEVELS) == {1, 2, 3, 4}
    for k in ("tin_khach", "tin_khach_nhap", "cham_diem", "vb_noi_bo"):
        assert k in AI_TASKS
    for k in ("khong_can", "cho_hau_kiem", "chap_nhan", "da_sua", "thu_hoi"):
        assert k in AI_REVIEW_STATES


def test_moi_noi_goi_mo_hinh_deu_ghi_nhat_ky():
    """Chặn việc thêm một chỗ gọi mô hình ngôn ngữ mới mà quên ghi vết."""
    be = os.path.join(ROOT, "backend", "app")
    thieu = []
    for d, _, fs in os.walk(be):
        if "__pycache__" in d: continue
        for f in fs:
            if not f.endswith(".py"): continue
            src = open(os.path.join(d, f), encoding="utf-8").read()
            if "messages.create(" in src and "ai_log" not in src and "AL.ghi" not in src:
                thieu.append(os.path.relpath(os.path.join(d, f), ROOT))
    assert not thieu, f"gọi mô hình ngôn ngữ mà không ghi nhật ký AI: {thieu}"


def test_ty_le_bi_sua_khong_bao_0_khi_chua_ai_hau_kiem():
    """0% đọc ra là 'chưa sai lần nào'. Chưa hậu kiểm cái nào thì phải là 'chưa có số', không phải 0."""
    class _DbRong:
        def execute(self, *a, **k):
            class _S:
                def scalars(self): return []
            return _S()
    t = AL.tong_hop(_DbRong())
    assert t["ty_le_bi_sua"] is None
