"""Robot đồng bộ phía máy chủ: phân tích HTML quyết toán/sản phẩm, API robot (token), trạng thái."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vtc.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "rb"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vtc.db"): os.remove("test_vtc.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import vietrip_client as VC

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


HTML = """<html><body><div>Tổng thu: 27,240,000 VNĐ</div><div>Tổng chi: 25.790.000 VNĐ</div>
<table><thead><tr><th>No</th></tr></thead><tbody>
<tr><td>1</td><td>HƯỚNG DẪN VIÊN<br>Cố định</td><td>GUIDE</td><td>NGUYỄN TẤT THẮNG</td><td>350,000</td><td>16</td><td>3</td><td></td><td>1,050,000</td><td>0</td><td></td></tr>
<tr><td>3</td><td>RESORT NOVELA<br>Theo khách</td><td>HOTEL</td><td>CÔNG TY VIỆT GROUP (3401254663)</td><td>600,000</td><td>16</td><td>1</td><td></td><td>9,600,000</td><td>9,600,000</td><td>ok</td></tr>
</tbody></table>
<h5>Bước 5: Lập Quyết toán Tour</h5><h4>Lịch sử hoạt động</h4>
<div>Phê duyệt dự toán thành công</div><div>05/09/2026 13:03 - NGUYỄN DƯƠNG TRUNG HIẾU</div>
<div>Đề nghị phê duyệt dự toán</div><div>05/09/2026 12:02 - NGUYỄN PHƯƠNG BẢO TRÂM</div><div>EM GỬI DỰ CHI TOUR - BIÊN THẤP NHỜ ANH DUYỆT</div>
<script>var cookie = 1;</script></body></html>"""


def test_parse_settlement():
    s = VC.parse_settlement(HTML, {"recID": 11775, "tourcode": "PT001.03060926"})
    assert s["tong_thu"] == 27240000 and s["tong_chi"] == 25790000 and len(s["lines"]) == 2
    assert s["lines"][1]["thuc_chi"] == 9600000 and s["lines"][1]["da_tt"] == 9600000 and s["lines"][0]["hs"] == 3 and "Cố định" in s["lines"][0]["mo_ta"]
    assert s["step"].startswith("Bước 5") and len(s["history"]) == 2 and s["history"][1]["actor"].startswith("NGUYỄN PHƯƠNG") and "BIÊN THẤP" in s["history"][1]["note"] and s["history"][0]["at"] == "2026-09-05T13:03:00"


def test_parse_product():
    h = """<form><input name="ProductCode" type="text" value="AU002"><input name="ProductName" value="MONO SYDNEY 5N4Đ">
    <select name="TourType"><option>Chọn</option><option selected>Quốc tế</option></select><input name="ReferencePrice" value="28,990,000"><input type="checkbox" name="RequiresConfirmation" checked>
    <input name="Flight" value="12,000,000"><select name="NVDH"><option value="1">A</option><option value="44" selected>NGUYỄN THỊ LAN</option></select>
    <textarea name="PriceInfo"><p>Ngày 1: HCM &ndash; Sydney</p><p>Ngày 2: City tour</p></textarea></form>"""
    p = VC.parse_product(h, 188, {"services": "", "status": "Hoạt động"})
    assert p["ProductCode"] == "AU002" and p["TourType"] == "Quốc tế" and p["ReferencePrice"] == "28,990,000" and p["RequiresConfirmation"] is True and p["Flight"] == "12,000,000"
    assert p["NVDH_name"] == "NGUYỄN THỊ LAN" and "Ngày 1" in p["PriceInfoText"] and "Ngày 2" in p["PriceInfoText"]


def test_robot_endpoints_and_status():
    assert client.post("/api/v1/robot/vietrip/sync", json={}, headers={"X-Robot-Token": "sai"}).status_code == 401
    st = client.get("/api/v1/import/vietrip/robot-status", headers=login("cntt")).json()
    assert st["running"] is False and st["credentials_set"] is False
    # chưa cấu hình tài khoản robot → chạy nền báo lỗi rõ ràng
    r = client.post("/api/v1/import/vietrip/sync", json={"from_date": "2026-09-01"}, headers=login("cntt")); assert r.status_code == 200
    import time; time.sleep(1.5)
    st = client.get("/api/v1/import/vietrip/robot-status", headers=login("cntt")).json()
    assert "VIETRIP_PHONE" in st["error"]
    assert client.post("/api/v1/import/vietrip/sync", json={}, headers=login("kd.hoa")).status_code == 403
