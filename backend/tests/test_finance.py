"""Tài chính: khế ước vay + lịch trả, hợp đồng đầu tư (NQ HĐQT bắt buộc), thực hiện lịch → bút toán & dư nợ, dự báo 13 tuần, báo cáo tuần."""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_fin.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_fin.db"): os.remove("test_fin.db")
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


def test_loan_schedule_settle_and_investment_gate():
    kt = login("ketoan")
    first = date.today() + timedelta(days=10)
    r = client.post("/api/v1/fin/contracts", json={"kind": "vay", "partner": "TPBank Bến Thành", "contract_no": "KU-2026-01", "principal": 1_200_000_000, "interest_rate": 9.0,
                                                   "collateral": "Xe 50F-009.60", "purpose": "Mua xe 45 chỗ", "months": 12, "first_due": str(first)}, headers=kt).json()
    c = r["contract"]
    assert len(c["schedule"]) == 24 and c["outstanding"] == 1_200_000_000
    goc = [s for s in c["schedule"] if s["kind"] == "tra_goc"][0]; lai = [s for s in c["schedule"] if s["kind"] == "tra_lai"][0]
    assert goc["amount"] == 100_000_000 and lai["amount"] == 9_000_000
    assert client.post("/api/v1/fin/contracts", json={"kind": "hop_tac_kd", "partner": "Nông nghiệp Xanh Tây Nguyên", "principal": 55_400_000_000}, headers=kt).status_code == 422  # thiếu NQ HĐQT
    inv = client.post("/api/v1/fin/contracts", json={"kind": "hop_tac_kd", "partner": "Nông nghiệp Xanh Tây Nguyên", "principal": 55_400_000_000, "approval_ref": "NQ 12/2025/HĐQT",
                                                     "maturity": str(date.today() + timedelta(days=60)), "owner": "KTT"}, headers=kt).json()["contract"]
    assert inv["schedule"][0]["kind"] == "thu_hoi" and inv["schedule"][0]["amount"] == 55_400_000_000
    assert client.post(f"/api/v1/fin/schedule/{goc['id']}/settle", json={"done_on": str(first), "bank_ref": "FT99"}, headers=login("cntt")).status_code == 403
    res = client.post(f"/api/v1/fin/schedule/{goc['id']}/settle", json={"done_on": str(first), "bank_ref": "FT99"}, headers=kt).json()
    assert "1,100,000,000" in res["message"]
    client.post(f"/api/v1/fin/schedule/{lai['id']}/settle", json={"done_on": str(first), "bank_ref": "FT100"}, headers=kt)
    # V12 – khoản VAY nay ghi sổ qua BẢNG QUY ƯỚC hạch toán, không dựng cặp tài khoản trong mã.
    # Hai điều đổi theo, và cả hai là sửa cho đúng chứ không phải đổi cho khác:
    #   · cặp tài khoản là 3411/1121 (đúng quy ước VAY_TRA_GOC), không phải 341/112 dựng tay;
    #   · source_ref là "khe_uoc:<mã>:ky<id>" để mỗi kỳ truy được về đúng dòng lịch của nó – bản cũ
    #     gộp mọi kỳ của một khế ước vào cùng một "fin:<mã>" nên không truy ngược được kỳ nào.
    js = [e for e in client.get("/api/v1/journal", headers=kt).json()
          if (e["source_ref"] or "").startswith(f"khe_uoc:{c['code']}:")]
    pairs = {(l["account"], l["debit"], l["credit"]) for e in js for l in e["lines"]}
    assert ("3411", 100_000_000, 0) in pairs, pairs
    assert ("635", 9_000_000, 0) in pairs, pairs
    assert ("1121", 0, 100_000_000) in pairs, pairs
    # Trả LÃI không được chạm dư nợ gốc – 1,2 tỷ trả 100 triệu gốc thì còn đúng 1,1 tỷ, dù đã trả
    # thêm 9 triệu lãi. Bản đầu của V12 để tra_lai rơi vào nhánh "cộng vào dư nợ" và dư nợ phình lên
    # đúng bằng số lãi vừa trả; phép thử này canh để không lặp lại.
    con = client.get("/api/v1/fin/contracts", headers=kt).json()
    ku = [x for x in con if x["code"] == c["code"]][0]
    assert ku["outstanding"] == 1_100_000_000, ku["outstanding"]


def test_forecast_and_weekly():
    kt = login("ketoan")
    client.post("/api/v1/fin/plan", json={"due_date": str(date.today() + timedelta(days=3)), "direction": "out", "category": "thue_van_phong", "description": "Thuê VP", "amount": 60_000_000, "recurring_monthly": True}, headers=kt)
    f = client.get("/api/v1/fin/forecast", headers=login("chutich")).json()
    assert len(f["weeks"]) == 13 and f["weeks"][0]["from"] <= str(date.today())
    assert sum(w["out"].get("thue_van_phong", 0) for w in f["weeks"]) >= 120_000_000     # lặp tháng
    assert sum(w["out"].get("tra_goc_vay", 0) for w in f["weeks"]) >= 200_000_000         # tháng 2, 3 của lịch vay
    assert sum(w["in"].get("thu_booking", 0) for w in f["weeks"]) > 0                    # booking còn phải thu
    assert f["alerts"]                                                                     # tiền âm → cảnh báo
    w = client.get("/api/v1/fin/weekly", headers=login("bks")).json()
    assert w["total_loans"] == 1_100_000_000 and w["investments_total"] == 55_400_000_000 and len(w["receivables_top10"]) >= 1
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
