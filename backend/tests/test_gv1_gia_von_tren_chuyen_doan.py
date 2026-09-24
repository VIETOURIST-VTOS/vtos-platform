"""GV-1 · Quyền xem giá vốn mở theo CHUYẾN ĐOÀN — hàng rào, 24/9/2026.

Chủ tịch quyết 24/9: Kinh doanh Đoàn tự lập dự toán, kể cả phần giá vốn. Muốn lập được thì phải
nhìn thấy. Đây là một lần NỚI trên một con số nhạy — giá mua của công ty — nên nó cần hàng rào
canh CẢ HAI CHIỀU, và chiều thứ hai mới là chiều quan trọng.

CHIỀU MỞ: người bán đoàn phải thấy giá vốn của đoàn, nếu không thì không lập nổi dự toán.

CHIỀU SIẾT — bốn chỗ lần nới này KHÔNG được lan tới, mỗi chỗ một lý do:

 1. TOUR LẺ. Phòng Lẻ bán trăm booking nhỏ; mở giá vốn ở đó không phục vụ việc gì đã giao, mà
    lại là con số đông người nhìn thấy nhất trong công ty.
 2. DANH MỤC SẢN PHẨM (`mask_product`). Giá vốn của MỘT đoàn đang thương lượng khác hẳn bảng
    giá mua của công ty trên toàn bộ mã sản phẩm. Trộn hai thứ làm một là nới thứ hai mà không
    ai quyết định.
 3. MÀN HÌNH NHÀ CUNG CẤP. Phần V bản mô tả cấm làm việc trực tiếp với NCC. Xem giá vốn là để
    SOÁT, không phải để gọi.
 4. CÁC VAI NGOÀI KHỐI KINH DOANH. Marketing, HCNS, hành chính không được ké theo lần nới này.

Và một điều KHÔNG kiểm ở đây mà phải nói ra: hàng rào này chặn việc NHÌN, không chặn việc bớt
biên có chủ ý. Cái chặn điều đó là cổng biên 10% cộng hai chữ ký — và cả hai vẫn nguyên vẹn.
"""
import datetime as dt

from app.models.core import ROLES, Tour, User
from app.services import access as AC
from app.services import rules as R

HOM_NAY = dt.date.today()


def _u(vai):
    return User(id=1, username="x", full_name="x", role=vai, password_hash="x")


def _tour(ma, loai):
    return Tour(code=ma, name=ma, tour_type=loai, start_date=HOM_NAY, end_date=HOM_NAY,
                operator_id=1, status="nhap", price_per_pax=1.0, planned_pax=1)


DOAN = _tour("MICE-2610-001", "doan_noi_dia")
LE = _tour("LE-2610-001", "le_noi_dia")


# ───────────────────────────── chiều MỞ ─────────────────────────────

def test_gv1_khoi_kinh_doanh_xem_duoc_gia_von_cua_chuyen_doan():
    for vai in AC.SALES:
        assert AC.can_see_cost_tren_chuyen(_u(vai), DOAN) is True, (
            f"{vai} không xem được giá vốn đoàn thì không lập nổi dự toán đoàn — "
            "đúng việc Chủ tịch giao 24/9/2026"
        )


def test_gv2_vai_von_da_co_quyen_thi_khong_doi():
    for vai in ("chutich", "tgd", "tp_dh", "nv_dh", "ketoan", "cntt", "ptgd_doan", "sales_admin"):
        assert AC.can_see_cost_tren_chuyen(_u(vai), DOAN) is True
        assert AC.can_see_cost_tren_chuyen(_u(vai), LE) is True, f"{vai} vốn xem được mọi chuyến"


# ───────────────────────────── chiều SIẾT ─────────────────────────────

def test_gv3_tour_LE_van_che_gia_von_voi_khoi_kinh_doanh():
    for vai in AC.SALES:
        assert AC.can_see_cost_tren_chuyen(_u(vai), LE) is False, (
            f"{vai} xem được giá vốn tour lẻ — lần nới 24/9 chỉ dành cho chuyến ĐOÀN"
        )


def test_gv4_danh_muc_san_pham_van_che_nguyen_nhu_cu():
    """`mask_product` KHÔNG được nới theo. Xem ghi chú 2 ở đầu tệp."""
    for vai in AC.SALES:
        ra = AC.mask_product({"fixed_cost": 100, "var_cost_per_pax": 20, "cost_lines": [1, 2]}, _u(vai))
        assert ra["fixed_cost"] is None and ra["var_cost_per_pax"] is None and ra["cost_lines"] is None, (
            f"{vai} nhìn thấy cơ cấu chi phí của danh mục sản phẩm — đó là giá mua của công ty "
            "trên toàn bộ mã sản phẩm, không phải giá vốn của một đoàn đang thương lượng"
        )


def test_gv5_cac_vai_ngoai_khoi_kinh_doanh_khong_ke_theo():
    for vai in ("nv_mkt", "ptgd_mkt", "hcns", "hanh_chinh", "xe_hdv", "nv_visa", "tp_hd", "gd_doi_xe"):
        assert AC.can_see_cost_tren_chuyen(_u(vai), DOAN) is False, f"{vai} không nằm trong lần nới này"


def test_gv6_khong_mo_man_hinh_nha_cung_cap_cho_khoi_kinh_doanh():
    """Phần V bản mô tả: xem giá vốn là để SOÁT, không phải để gọi nhà cung cấp."""
    ncc = AC.MENU_ROLES.get("/nha-cung-cap", ())
    for vai in tuple(AC.SALES) + ("sales_admin",):
        assert vai not in ncc, f"{vai} mở được màn hình nhà cung cấp — lần nới 24/9 không đi xa tới đó"


def test_gv7_COST_ROLES_khong_bi_noi_ca_khoi():
    """Cách nới RỘNG NHẤT là thêm SALES vào COST_ROLES. Phép thử này khoá đúng cửa ấy.

    Nếu một ngày ai đó thấy `can_see_cost_tren_chuyen` rườm rà rồi 'dọn' bằng cách nhét SALES vào
    COST_ROLES, mọi màn hình vẫn chạy, không phép thử nghiệp vụ nào đỏ — và khối Kinh doanh lặng
    lẽ xem được giá vốn tour lẻ lẫn cả danh mục sản phẩm.
    """
    for vai in AC.SALES:
        assert vai not in AC.COST_ROLES, (
            f"{vai} đã vào COST_ROLES — đó là nới TOÀN CỤC, không phải nới theo chuyến đoàn. "
            "Quyết định 24/9/2026 chỉ mở giá vốn của chuyến đoàn."
        )


# ───────────────────────────── cách hỏi, không chỉ kết quả ─────────────────────────────

def test_gv8_hoi_lai_rules_is_doan_chu_khong_doc_thang_tour_type():
    """Một ngày mã MICE được coi là đoàn dù `tour_type` ghi lẻ — lúc ấy quyền phải đi theo.

    Nó chỉ đi theo nếu hàm hỏi lại `rules.is_doan` thay vì tự đọc `tour_type`. Cùng lập luận đã
    ghi trong chính `rules.is_doan`: hai định nghĩa song song thì sẽ có ngày một tour nằm ở màn
    hình phòng này mà tính tiền theo phòng kia.
    """
    import re
    nguon = open(AC.__file__, encoding="utf-8").read()
    i = nguon.find("def can_see_cost_tren_chuyen")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    than = re.sub(r'"""[\s\S]*?"""', "", than)
    than = re.sub(r"#[^\n]*", "", than)
    assert "is_doan" in than, "phải hỏi rules.is_doan, đừng dựng định nghĩa 'đoàn' thứ hai"
    assert "tour_type" not in than, "đọc thẳng tour_type ở đây là bản sao thứ hai của luật phân mảng"


def test_gv9_tour_rong_thi_tu_choi_chu_khong_cho_qua():
    """Không có chuyến thì không có câu trả lời 'được xem'. Mặc định phải là ĐÓNG.

    Một hàm quyền mà trả True khi thiếu dữ liệu là hàm sẽ mở cửa đúng lúc dữ liệu hỏng.

    GHI RÕ PHÉP THỬ NÀY CANH ĐƯỢC GÌ, vì em đã đo: bỏ dòng `or tour is None` trong hàm thì phép
    thử vẫn XANH, bởi `rules.is_doan(None)` hôm nay cũng trả về False. Nghĩa là nó canh KẾT QUẢ
    (thiếu chuyến thì đóng), không canh dòng chắn ấy còn hay mất. Dòng chắn vẫn nên giữ: nó là
    lớp thứ hai, và nó sẽ có ích đúng vào ngày `is_doan` đổi thành ném lỗi khi nhận None.
    """
    for vai in AC.SALES:
        assert AC.can_see_cost_tren_chuyen(_u(vai), None) is False


def test_gv10_moi_vai_trong_ROLES_deu_tra_loi_duoc_khong_no_loi():
    for vai in ROLES:
        for t in (DOAN, LE, None):
            assert AC.can_see_cost_tren_chuyen(_u(vai), t) in (True, False)


def test_gv11_cua_doc_tour_hoi_theo_chuyen_chu_khong_theo_vai():
    """Cửa `GET /tours/{id}` phải gọi hàm theo-chuyến. Gọi `can_see_cost(u)` như cũ thì lần nới
    này không tới được màn hình, và Kinh doanh Đoàn vẫn không lập nổi dự toán."""
    import re
    from app.api.v1 import routes as RT
    nguon = open(RT.__file__, encoding="utf-8").read()
    i = nguon.find("def get_tour")
    than = re.sub(r"#[^\n]*", "", nguon[i:nguon.find("\n@router", i)])
    assert "can_see_cost_tren_chuyen" in than, "cửa đọc chuyến phải hỏi theo CHUYẾN"
    assert not re.search(r"can_see_cost\(", than), "còn chỗ hỏi theo vai trò – hai luật song song sẽ lệch"


def test_gv11b_cua_MAN_HINH_CHI_TIET_cung_hoi_theo_chuyen():
    """`GET /tours/{id}/detail` là cửa màn hình chi tiết THẬT SỰ dùng — không phải `GET /tours/{id}`.

    Vòng 2 sửa đúng cửa thứ hai và bỏ sót cửa này, nên Kinh doanh Đoàn mở chính chuyến mình vừa lập
    vẫn nhận `calc = None`. Quyền nằm trong mã mà màn hình vẫn che thì trên thực tế là chưa mở.

    Hai cửa đọc cùng một chuyến mà hỏi hai luật khác nhau: luật lỏng hơn thành vô nghĩa, luật chặt
    hơn thành lỗi người dùng báo về. Phép thử này khoá cả hai cửa vào một luật.
    """
    import re
    from app.api.v1 import products as PR
    nguon = open(PR.__file__, encoding="utf-8").read()
    i = nguon.find("def tour_detail")
    than = re.sub(r"#[^\n]*", "", nguon[i:nguon.find("\n@router", i)])
    assert "can_see_cost_tren_chuyen" in than, "cửa chi tiết phải hỏi theo CHUYẾN"
    assert not re.search(r"can_see_cost\(", than), "còn chỗ hỏi theo vai trò – hai luật song song sẽ lệch"


def test_gv12_cong_bien_va_hai_chu_ky_khong_bi_dung_toi():
    """Lần nới này đổi việc NHÌN, không đổi việc DUYỆT.

    Đây là câu quan trọng nhất của cả tệp: mở giá vốn cho người bán làm việc bớt biên có chủ ý dễ
    hơn, và thứ chặn điều đó không phải hàng rào ở trên mà là cổng biên cộng hai chữ ký.
    """
    assert R.approver_role(DOAN) == "ptgd_doan"
    assert R.approver_role(LE) == "tgd"
    nguon = open(R.__file__, encoding="utf-8").read()
    assert '("nguong_bien", "0.10"' in nguon, "ngưỡng biên kế hoạch phải còn nguyên 10%"
