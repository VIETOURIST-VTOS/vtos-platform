"""Dashboard theo vai trò và robot R7 báo cáo ngày/tuần/tháng."""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_dash.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "rt"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dash.db"): os.remove("test_dash.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.ROBOT_TOKEN = "rt"; settings.ANTHROPIC_API_KEY = ""

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_dashboard_by_role():
    d = client.get("/api/v1/dashboard", headers=login("chutich")).json()
    assert "tien" in d["kpis"] and "kd_le" in d["sections"] and "sap_khoi_hanh" in d["sections"] and any("dự toán" in a["label"] for a in d["approvals"])
    k = client.get("/api/v1/dashboard", headers=login("ketoan")).json()
    assert "tien" in k["kpis"] and all("href" in a for a in k["approvals"])
    s = client.get("/api/v1/dashboard", headers=login("kd.hoa")).json()
    assert "tien" not in s["kpis"] and "kd_le" in s["sections"]


def test_auto_reports_and_robot_api():
    for kind in ("ngay", "tuan", "thang"):
        r = client.post(f"/api/v1/auto-reports/{kind}", headers=login("cntt")).json()["report"]
        assert r["content"].startswith("# Báo cáo") and "Nhận xét của robot" in r["content"] and r["comment"]
    assert client.post("/api/v1/auto-reports/nam", headers=login("cntt")).status_code == 422
    assert client.post("/api/v1/robot/report/ngay").status_code == 401
    rr = client.post("/api/v1/robot/report/ngay", headers={"X-Robot-Token": "rt"}).json()
    assert rr["period"] == str(date.today()) and "markdown" in rr
    lst = client.get("/api/v1/auto-reports", headers=login("bks")).json()
    assert len(lst) == 3                                   # chạy lại cùng kỳ → ghi đè, không nhân bản
    assert client.get("/api/v1/auto-reports", headers=login("kd.hoa")).status_code == 403
