# -*- coding: utf-8 -*-
"""DH-1 · Tab "Phát sinh & sự cố" của trang chuyến, và hai bảng quyền thôi nói ngược nhau.

Mục 4.4.7 là mục cuối còn trống của khối Điều hành tour. Dữ liệu vốn đã có: bảng `su_co_tour` mang
cột `tour_id`, và `GET /su-co-tour?tour_id=N` lọc sẵn theo chuyến. Cái thiếu là một CÁI TAB — người
đang xem một chuyến muốn biết chuyến ấy có phát sinh gì thì phải nhớ ra màn hình khác rồi tự lọc.

ĐO ĐƯỢC TRONG LÚC LÀM, và nó là chỗ hỏng thật thứ hai: `sales_admin` nằm trong
`MENU_ROLES["/su-co-tour"]` (qua nhóm SALES_ADMIN) mà KHÔNG nằm trong `su_co_tour.XEM` — tức Sale
Admin mở được màn hình Sự cố tour và MỌI cửa trên đó trả 403. Một màn hình mở mà không cửa nào bấm
được thì tệ hơn một màn hình bị khoá: người dùng không biết mình thiếu quyền hay hệ thống hỏng.

PHÉP THỬ ĐẮT NHẤT TRONG TỆP là `test_hai_bang_quyen_phai_phu_nhau`: nó không biết vai nào đúng, nó
chỉ hỏi một câu — "ai mở được màn hình thì có gọi được cửa của màn hình ấy không". Câu ấy bắt được
cả chỗ hỏng cũ lẫn chỗ hỏng mà vòng này có thể vừa tạo ra.
"""
import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_dh1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dh1.db"):
    os.remove("test_dh1.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402

from app.main import app                             # noqa: E402
from app.api.v1 import su_co_tour as SCT             # noqa: E402
from app.services import access as AC                # noqa: E402

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web"
TRANG = WEB / "app" / "tours" / "[id]" / "page.tsx"
CAY = WEB / "lib" / "cay_phan_he.ts"

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _tep(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_hai_bang_quyen_phai_phu_nhau():
    """Ai MỞ ĐƯỢC một màn hình thì phải GỌI ĐƯỢC cửa của màn hình ấy — hỏi cho cả hai màn hình.

    Đây là phép thử không biết vai nào đúng và không cần biết. Nó bắt được chỗ hỏng cũ (Sale Admin
    mở được /su-co-tour mà mọi cửa trả 403) bằng đúng câu hỏi bắt được chỗ hỏng mà vòng này có thể
    vừa tạo ra (thêm tab vào /tours cho vai không được xem sự cố).
    """
    xem = set(SCT.XEM)
    for man_hinh in ("/su-co-tour", "/tours"):
        if "/api/v1/su-co-tour" not in AC.MAN_HINH_API.get(man_hinh, ()):
            continue
        thieu = set(AC.MENU_ROLES[man_hinh]) - xem
        assert not thieu, (
            f"{man_hinh} khai tiền tố /api/v1/su-co-tour nhưng {sorted(thieu)} không có trong "
            f"su_co_tour.XEM — mở được màn hình mà mọi cửa trả 403")


def test_trang_chuyen_co_tab_phat_sinh_va_khong_dung_cua_ghi_thu_hai():
    """Tab phải GỌI cửa lọc theo chuyến, và KHÔNG được mọc một cửa ghi thứ hai cho cùng bảng.

    Ngày nào trang chuyến ghi thẳng vào `su_co_tour` thì có hai chỗ ghi cho một bảng, và hai bộ luật
    sẽ lệch nhau ở lần sửa thứ nhất — lập sự cố và xử lý sự cố vẫn phải ở đúng màn hình sổ sự cố.
    """
    t = _tep(TRANG)
    assert '"phatsinh"' in t, "trang chuyến chưa có tab Phát sinh"
    # So ĐƯỜNG ĐẦY ĐỦ kèm tham số lọc, không `"/su-co-tour" in t`: khớp theo khúc đầu là hàng rào
    # trang trí — nó xanh đúng vào lúc đường gọi hỏng (đã vấp ba lần ở NS-2 và NS-3).
    assert re.search(r'/su-co-tour\?tour_id=\$\{[^}]+\}`', t), \
        "tab chưa gọi đúng cửa lọc theo chuyến"
    assert not re.search(r'api\(\s*`?/su-co-tour[^)]*method:\s*"POST"', t, re.S), \
        "trang chuyến mọc cửa GHI sự cố — một bảng chỉ được có một chỗ ghi"


def test_muc_4_4_7_va_4_9_1_noi_dung_su_that():
    """Hai mục cây của vòng này: 4.4.7 là TAB trong trang chuyến, 4.9.1 trỏ về /doi-xe."""
    cay = _tep(CAY)
    def _dong(ma: str) -> str:
        i = cay.index(f'ma: "{ma}"')
        return cay[i:cay.index("\n", i)]
    assert "tab: true" in _dong("4.4.7"), \
        "4.4.7 là tab bên trong trang chuyến, không phải một trang riêng"
    assert 'href: "/doi-xe"' in _dong("4.9.1"), "4.9.1 chưa trỏ về /doi-xe"


def _token(u: str) -> str:
    r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, f"{u}: {r.text}"
    return r.json()["access_token"]


def test_vai_moi_mo_nay_doc_duoc_so_su_co():
    """Chạy thật với vai vừa được mở: `ptgd_mkt` gọi được sổ sự cố.

    Soi mã nguồn bắt được chuyện ai đó xoá tên khỏi danh sách, nhưng không bắt được chuyện tên còn
    nguyên mà cửa vẫn từ chối — nhánh chết là loại hỏng đã xảy ra thật trong kho này.

    KHÔNG dùng `pytest.skip` khi bản demo thiếu tài khoản: một phép thử tự bỏ qua là một phép thử
    canh được 0 điều, và nó vẫn in ra màu xanh. Bản demo có `ptgd.mkt`, nên hỏi đúng vai ấy; còn
    `sales_admin` thì phần nguồn đã canh ở `test_hai_bang_quyen_phai_phu_nhau` phía trên.
    """
    h = {"Authorization": "Bearer " + _token("ptgd.mkt")}
    assert client.get("/api/v1/su-co-tour", headers=h).status_code == 200, \
        "vai vừa được Chủ tịch mở vẫn bị từ chối ở sổ sự cố"


def test_vai_ngoai_danh_sach_van_bi_chan_o_may_chu():
    """Nới cho hai vai KHÔNG được thành mở sổ sự cố cho mọi người.

    Hàng rào thật nằm ở chữ ký cửa, không ở màn hình: một vai ngoài danh sách phải nhận 403 dù có
    bấm thẳng vào đường dẫn.
    """
    h = {"Authorization": "Bearer " + _token("hcns")}
    assert client.get("/api/v1/su-co-tour", headers=h).status_code == 403, \
        "vai ngoài danh sách XEM vẫn đọc được sổ sự cố"
