"""Danh mục pháp nhân và công ty chủ quản của xe / HDV (Ý kiến thẩm định 06/9/2026, mục C1).

Đội xe thuộc Công ty TNHH Vận tải Vietrip – pháp nhân riêng trong phạm vi hợp nhất – nên lệnh điều xe
dùng xe đó là giao dịch nội bộ, phải nhận diện để loại trừ khi lập báo cáo hợp nhất.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_companies.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_companies.db"): os.remove("test_companies.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_danh_muc_phap_nhan_co_me_va_van_tai_vietrip():
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    codes = {c["code"]: c for c in cs}
    assert "VTD" in codes and codes["VTD"]["kind"] == "me"
    vt = codes.get("VTRIP-VT")
    assert vt and vt["kind"] == "con" and vt["ownership_pct"] == 100
    assert vt["parent_id"] == codes["VTD"]["id"]
    assert vt["in_group"] is True, "công ty con nằm trong phạm vi hợp nhất"


def test_xe_noi_bo_duoc_gan_van_tai_vietrip_xe_hop_tac_thi_khong():
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    assert veh, "phải có xe trong dữ liệu mẫu"
    for v in veh:
        if v["kind"] == "noi_bo":
            assert v["company_code"] == "VTRIP-VT", f"xe nội bộ {v['plate']} phải thuộc Vận tải Vietrip"
        else:
            assert not v["company_id"], "xe hợp tác là xe thuê ngoài, không gán pháp nhân trong tập đoàn"


def test_lenh_dieu_xe_nhan_dien_giao_dich_noi_bo():
    disp = client.get("/api/v1/dispatch", headers=login("cntt")).json()
    for d in disp:
        if d["company_code"] == "VTRIP-VT":
            assert d["noi_bo"] is True and not d["canh_bao"]
        elif not d["company_code"]:
            assert d["noi_bo"] is False and "chưa gán" in d["canh_bao"]


def test_gan_va_go_chu_quan_xe():
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    v = veh[0]; cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    me = next(c for c in cs if c["code"] == "VTD")
    r = client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": me["id"]}, headers=login("ketoan"))
    assert r.status_code == 200
    assert next(x for x in client.get("/api/v1/vehicles", headers=login("cntt")).json() if x["id"] == v["id"])["company_code"] == "VTD"
    # trả về như cũ
    client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": v["company_id"]}, headers=login("ketoan"))
    assert client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": 99999}, headers=login("ketoan")).status_code == 422


def test_hdv_thuoc_cong_ty_me():
    """Anh Tuấn chốt 06/9/2026: HDV vẫn thuộc Công ty Cổ phần Du lịch Vietourist, kể cả khi là cộng tác viên."""
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    hdv = [e for e in emps if e["department"] == "huong_dan"]
    assert hdv, "dữ liệu mẫu phải có HDV"
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    me = next(c for c in cs if c["code"] == "VTD")
    assert all(e["company_id"] == me["id"] for e in hdv), "HDV mặc định thuộc công ty mẹ"
    # HCNS vẫn đổi được sang pháp nhân khác khi ký qua công ty con
    vt = next(c for c in cs if c["code"] == "VTRIP-VT")
    assert client.put(f"/api/v1/employees/{hdv[0]['id']}/company", json={"company_id": vt["id"]}, headers=login("hcns")).status_code == 200
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    assert next(e for e in emps if e["id"] == hdv[0]["id"])["company_id"] == vt["id"]
    client.put(f"/api/v1/employees/{hdv[0]['id']}/company", json={"company_id": me["id"]}, headers=login("hcns"))


def test_bao_cao_do_phu_chu_quan():
    c = client.get("/api/v1/companies/coverage", headers=login("tgd")).json()
    assert c["xe"]["tong"] >= 1 and c["xe"]["da_gan"] >= 1
    assert c["hdv"]["tong"] >= 1 and c["hdv"]["chua_gan"] == 0


def test_vai_tro_khong_duoc_tao_phap_nhan():
    r = client.post("/api/v1/companies", json={"code": "X1", "name": "Thử", "kind": "con"}, headers=login("kd.hoa"))
    assert r.status_code == 403
