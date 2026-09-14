"""Hồ sơ visa của sales phụ trách – hai cửa từng nói ngược nhau.

Máy chủ khai nv_kd ở visa.READ, hồ sơ visa mang cột sales_user_id và có nút phân công người bán. Nhưng
dòng /visa trong ma trận menu lại bỏ khối Kinh doanh, nên hàng rào phạm vi (check_restricted_scope) chặn
họ ở /api/v1/visa: ô phân công thành ô chết, và nhân viên bán hàng không trả lời được câu "hồ sơ visa của
khách tôi tới đâu rồi".

Chốt 08/9/2026: khối Kinh doanh XEM được màn hình Visa. Không nới gì thêm – hai phép thử dưới đây canh
đúng hai chỗ dễ nới quá tay nhất, và chúng quan trọng hơn phép thử thứ nhất.

  VS1 sales được phân công mở được hồ sơ của mình
  VS2 sales KHÔNG được phân công vẫn không mở được hồ sơ khách của người khác
  VS3 sales phụ trách vẫn không xem được cơ cấu giá vốn của chính hồ sơ đó
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_visa_sales.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_visa_sales.db"): os.remove("test_visa_sales.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}
DEP = str(date.today() + timedelta(days=60))


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _uid(username):
    return next(x["id"] for x in client.get("/api/v1/users", headers=login("chutich")).json()
                if x["username"] == username)


def test_vs1_sales_duoc_phan_cong_mo_duoc_ho_so_cua_minh():
    """Ô phân công người bán chỉ có nghĩa khi người được phân công mở được hồ sơ đó."""
    r = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                    json={"applicant_name": "Khách của chị Hoa", "market_code": "UK",
                          "departure_date": DEP, "on_duplicate": "independent", "note": "kiểm phân quyền"})
    assert r.status_code == 201, r.text
    CTX["cid"] = cid = r.json()["case"]["id"]
    r2 = client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                     json={"sales_user_id": _uid("kd.hoa")})
    assert r2.status_code == 200, r2.text
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("kd.hoa")).status_code == 200


def test_vs2_sales_khong_duoc_phan_cong_van_khong_mo_duoc_ho_so_nguoi_khac():
    """Mở màn hình Visa cho khối Kinh doanh KHÔNG có nghĩa là mở mọi hồ sơ visa.

    Khoanh vùng nằm ở visa.scope(): chỉ hồ sơ mà người đăng nhập là người bán, người xử lý hoặc người
    giám sát. Phép thử này quan trọng hơn phép thử trên – nó canh chỗ nới quá tay."""
    # trước hết chắc rằng hàng rào phạm vi ĐÃ mở cho vai trò này – nếu không thì phép thử dưới xanh vì
    # lý do khác (bị chặn ngay ở cổng ngoài) và nó không kiểm được việc khoanh vùng theo phân công
    ds = client.get("/api/v1/visa/ho-so", headers=login("kd.tuan"))
    assert ds.status_code == 200, f"cổng ngoài vẫn chặn – phép thử này chưa kiểm được gì ({ds.status_code})"
    assert CTX["cid"] not in [x["id"] for x in ds.json()["rows"]], "hồ sơ của người khác lọt vào danh sách"
    r = client.get(f"/api/v1/visa/ho-so/{CTX['cid']}", headers=login("kd.tuan"))
    assert r.status_code in (403, 404), \
        f"sales không được phân công vẫn mở được hồ sơ khách của người khác ({r.status_code})"


def test_vs3_sales_phu_trach_van_khong_xem_duoc_co_cau_gia_von():
    """Thấy hồ sơ khách của mình là một chuyện; thấy giá vốn là chuyện khác."""
    assert client.get(f"/api/v1/visa/ho-so/{CTX['cid']}/thu-chi",
                      headers=login("kd.hoa")).status_code == 403
