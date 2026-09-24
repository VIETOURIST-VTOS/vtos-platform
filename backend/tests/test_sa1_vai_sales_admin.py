"""SA-1 · Vai Sale Admin phòng Đoàn — hàng rào, 24/9/2026.

Vai này mở theo Bản mô tả công việc "SALE ADMIN — PHÒNG KINH DOANH ĐOÀN", hiệu lực 01/9/2026. Phần
V của bản mô tả chia rất rõ ĐƯỢC LÀM / KHÔNG ĐƯỢC LÀM, và một ranh giới viết trên giấy thì chỉ có
giá trị bằng đúng hàng rào đóng nó trong mã.

BỐN ĐIỀU PHÉP THỬ NÀY CANH, và vì sao mỗi điều đáng một phép thử riêng:

 1. KHÔNG NẰM TRONG NHÓM `SALES`. Nhóm ấy là nguồn của `REQUEST_CREATE_ROLES` (gửi yêu cầu đặt dịch
    vụ) và `GIU_CHO_ROLES` (giữ chỗ) — đúng hai việc Phần V cấm. Nếu có ngày ai đó "dọn cho gọn"
    bằng cách gộp `sales_admin` vào `SALES`, mọi thứ vẫn chạy, không màn hình nào hỏng, và vị trí
    này lặng lẽ có lại quyền bán hàng. Đây là kiểu hỏng không ai nhìn thấy.

 2. ĐƯỢC XEM GIÁ VỐN. Đây là một lần NỚI (Chủ tịch quyết 24/9/2026) nên phải có phép thử ghim lại
    cùng lý do, chứ không để nó trôi vào bảng như một dòng vô danh. Mục 4.2 bản mô tả buộc vị trí
    này kiểm hoa hồng và quà tặng khách đã vào giá vốn của chính đoàn đó.

 3. XEM GIÁ VỐN KHÔNG KÉO THEO LÀM VIỆC VỚI NHÀ CUNG CẤP. Hai thứ hay bị gộp làm một. Phần V cấm
    "điều hành tour, đặt dịch vụ hoặc làm việc trực tiếp với nhà cung cấp" — nên vai này không mở
    màn hình /nha-cung-cap và không gửi được yêu cầu đặt dịch vụ.

 4. MENU VÀ CỬA API KHÔNG ĐƯỢC LỆCH NHAU. Lệch một chiều là thấy mục menu rồi bấm vào nhận 403;
    lệch chiều kia là mở được cửa mà không có đường nào tới.
"""
import inspect

from app.models.core import ROLES, User
from app.services import access as AC

VAI = "sales_admin"


def _u(vai=VAI):
    return User(id=1, username="salesadmin.doan", full_name="Sale Admin", role=vai, password_hash="x")


# ───────────────────────────── SA-1 · vai có thật ─────────────────────────────

def test_sa1_vai_co_trong_danh_muc_va_co_ten_tieng_viet():
    assert VAI in ROLES, "vai chưa khai trong ROLES thì màn hình Tài khoản không chọn được nó"
    assert ROLES[VAI].strip(), "vai phải có tên đọc được, không để chuỗi rỗng"


# ───────────────────────────── SA-2 · không phải người bán ─────────────────────────────

def test_sa2_khong_nam_trong_nhom_sales():
    assert VAI not in AC.SALES, (
        "gộp sales_admin vào SALES là trao lại bằng mã đúng thứ Phần V bản mô tả vừa lấy đi: "
        "REQUEST_CREATE_ROLES và GIU_CHO_ROLES đều dựng từ nhóm ấy"
    )
    assert AC.SALES_ADMIN == (VAI,), "nhóm riêng phải đứng riêng, đúng một vai"


def test_sa3_khong_gui_duoc_yeu_cau_dat_dich_vu():
    assert VAI not in AC.REQUEST_CREATE_ROLES, "Phần V: không bán hàng, không nhận khách, không chốt đoàn"


def test_sa4_khong_giu_cho_duoc():
    assert VAI not in AC.GIU_CHO_ROLES, "giữ chỗ là một ghế không bán cho khách khác – việc của người bán"


def test_sa5_khong_mo_man_hinh_nha_cung_cap():
    """Xem giá vốn là để SOÁT, không phải để gọi nhà cung cấp."""
    assert VAI not in AC.MENU_ROLES.get("/nha-cung-cap", ()), (
        "Phần V cấm làm việc trực tiếp với nhà cung cấp – mở màn hình NCC là mở đúng cánh cửa ấy"
    )


def test_sa6_khong_cham_vao_tien_luong_va_ngan_hang():
    for man in ("/hr", "/bank-accounts", "/finance", "/expenses", "/ket-so", "/access"):
        assert VAI not in AC.MENU_ROLES.get(man, ()), f"{man} ngoài phạm vi công việc của vị trí này"


# ───────────────────────────── SA-7 · lần nới, ghi rõ lý do ─────────────────────────────

def test_sa7_duoc_xem_gia_von():
    """Chủ tịch quyết 24/9/2026. Mục 4.2 bản mô tả: kiểm hoa hồng và quà tặng khách ĐÃ vào giá vốn
    của chính đoàn đó; Phần VI: báo cáo tháng lợi nhuận từng đoàn theo người chốt.

    Không thấy giá vốn thì không kiểm được cả hai, và biên kế hoạch in ra sẽ đẹp hơn sự thật đúng
    bằng khoản bỏ sót — cổng biên 10% mở cho một đoàn lẽ ra phải đi đường hai chữ ký.
    """
    assert AC.can_see_cost(_u()) is True
    assert VAI in AC.COST_ROLES


def test_sa7b_nhan_vien_kinh_doanh_van_KHONG_xem_duoc_gia_von():
    """Lần nới ở trên phải hẹp đúng bằng một vai. Nới nhầm cả khối là mở cơ cấu chi phí NCC cho
    người đang ngồi với khách — đúng điều `mask_product` sinh ra để chặn."""
    for vai in ("nv_kd", "tn_kd", "tp_kd", "gd_kd"):
        assert AC.can_see_cost(_u(vai)) is False, f"{vai} không được xem cơ cấu chi phí NCC"


# ───────────────────────────── SA-8 · màn hình đủ để làm việc ─────────────────────────────

CAN_CO = (
    "/tours",            # 4.1 hồ sơ đoàn · 4.2 dự toán
    "/bookings",         # 4.3 tiến độ thu tiền · 4.5 dữ liệu khách và thoả thuận chia data
    "/hop-dong-khach",   # 4.1 hợp đồng và phụ lục
    "/bao-gia",          # 4.1 báo giá đã gửi khách
    "/cong-no",          # 4.3 công nợ quá hạn theo từng hợp đồng
    "/so-con-no",        # 4.4 tiến độ quyết toán
    "/lai-lo-tour",      # Phần VI báo cáo tháng: lợi nhuận từng đoàn
    "/tep",              # 4.1 lưu hồ sơ theo mã đoàn
    "/nap-du-lieu",      # 4.5 tải lên danh sách khách
)


def test_sa8_mo_duoc_dung_nhung_man_hinh_ban_mo_ta_doi():
    thieu = [m for m in CAN_CO if VAI not in AC.MENU_ROLES.get(m, ())]
    assert not thieu, (
        f"thiếu màn hình {thieu} – bản mô tả giao việc mà hệ thống không mở cửa thì việc ấy sẽ được "
        "làm ở ngoài hệ thống, trên một tệp Excel không ai soát được"
    )


def test_sa9_menu_va_cua_api_khong_lech_nhau():
    """Mọi màn hình vai này mở được đều phải nằm trong bản đồ MAN_HINH_API.

    Thiếu một dòng ở bản đồ ấy là vai này thấy mục menu rồi bấm vào nhận 403 — một cánh cửa vẽ trên
    tường, khó chịu hơn không có cửa.
    """
    cua = [m for m, vais in AC.MENU_ROLES.items() if VAI in vais]
    assert cua, "vai không mở được màn hình nào thì nó không làm được gì"
    thieu = [m for m in cua if m not in AC.MAN_HINH_API]
    assert not thieu, f"màn hình {thieu} không có trong MAN_HINH_API – vai này sẽ nhận 403 khi bấm vào"


# ───────────────────────────── SA-10 · màn hình P.TGĐ đoàn ─────────────────────────────

def test_sa10_ban_lam_viec_ptgd_doan_hep_dung_mot_nguoi_ky():
    """Hàng đợi ký của một người. Thêm vai vào đây làm nó trông như hàng đợi của nhiều người, rồi
    ai cũng tưởng có người khác lo."""
    vais = AC.MENU_ROLES["/ptgd-doan"]
    assert "ptgd_doan" in vais
    for khong in ("tp_dh", "nv_dh", "gd_kd", "tp_kd", "tn_kd", "nv_kd", VAI, "ketoan"):
        assert khong not in vais, f"{khong} không đứng cùng phía với người duyệt dự toán"
    assert "/ptgd-doan" in AC.MAN_HINH_API, "màn hình mới phải khai nhóm API, nếu không mở ra là 403"


def test_sa10b_cua_api_va_menu_khai_cung_mot_danh_sach_vai():
    from app.api.v1 import ptgd_doan as API
    assert set(API.XEM) == set(AC.MENU_ROLES["/ptgd-doan"]), (
        "danh sách vai ở cửa API và ở ma trận menu phải bằng nhau – lệch một chiều là thấy menu rồi "
        "nhận 403, lệch chiều kia là mở được cửa mà không có đường nào tới"
    )


def test_sa10c_cua_ptgd_doan_chi_co_duong_doc():
    """Ký dự toán vẫn đi qua cửa cũ. Dựng cửa ký thứ hai ở đây là tạo bản sao thứ hai của luật ký."""
    from app.api.v1 import ptgd_doan as API
    for r in API.router.routes:
        assert set(getattr(r, "methods", set())) <= {"GET", "HEAD", "OPTIONS"}, (
            f"{r.path} là đường GHI – bàn làm việc này chỉ đọc, ký vẫn qua POST /api/v1/tours/{{id}}/approve"
        )


def test_sa10d_nhom_api_moi_khong_bi_gan_nho_vao_nhom_co_san():
    """Gắn nhờ vào /api/v1/tours là nới CẢ nhóm ấy cho mọi vai mở được màn hình này."""
    assert AC.MAN_HINH_API["/ptgd-doan"] == ("/api/v1/ptgd-doan",)
    from app.api.v1 import ptgd_doan as API
    assert API.router.prefix == "/api/v1/ptgd-doan"


def test_sa10e_ban_lam_viec_khong_co_ky_mac_dinh():
    """Một bảng số thật in ra dưới một kỳ người xem không chọn là cách chắc chắn để họ đọc nhầm tháng."""
    from app.api.v1 import ptgd_doan as API
    ky = inspect.signature(API.ban_lam_viec).parameters["ky"]
    assert ky.default is inspect.Parameter.empty, "tham số kỳ phải bắt buộc, không có giá trị mặc định"
