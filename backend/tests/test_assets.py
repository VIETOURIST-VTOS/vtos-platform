"""Phân hệ Tài sản cố định & Công cụ dụng cụ (theo cách MISA): thẻ tài sản, bảng tính khấu hao, phân bổ 242, ghi sổ."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_assets.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_assets.db"): os.remove("test_assets.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_khau_hao_tscd():
    h = login("ketoan")
    # Xe 45 chỗ: nguyên giá 1,2 tỷ, khấu hao 6 năm = 72 tháng → 16.666.667 đ/tháng
    r = client.post("/api/v1/fixed-assets", headers=h, json={
        "code": "TS-XE01", "name": "Xe khách 45 chỗ 51B-12345", "kind": "huu_hinh", "group": "Phương tiện vận tải",
        "expense_account": "6424", "department": "doi_xe", "start_date": "2026-01-01",
        "cost": 1_200_000_000, "depr_months": 72})
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["monthly"] == 16_666_667, a["monthly"]

    # Tài sản nạp từ số dư MISA: đã trích tới hết 2026-06 thì kỳ 06 KHÔNG trích lại
    r2 = client.post("/api/v1/fixed-assets", headers=h, json={
        "code": "TS-MAY01", "name": "Máy chủ phòng CNTT", "kind": "huu_hinh", "expense_account": "6424",
        "department": "cntt", "start_date": "2025-01-01", "cost": 360_000_000, "depr_months": 36,
        "opening_accumulated": 180_000_000, "opening_period": "2026-06"})
    assert r2.status_code == 201, r2.text

    tab6 = client.get("/api/v1/fixed-assets/depreciation?period=2026-06", headers=h).json()
    by = {x["code"]: x for x in tab6["rows"]}
    assert by["TS-MAY01"]["amount"] == 0, "kỳ đã có trong số dư đầu kỳ thì không trích lại"
    assert by["TS-XE01"]["amount"] == 16_666_667

    tab = client.get("/api/v1/fixed-assets/depreciation?period=2026-07", headers=h).json()
    by = {x["code"]: x for x in tab["rows"]}
    assert by["TS-MAY01"]["amount"] == 10_000_000              # 360tr/36 tháng
    assert by["TS-MAY01"]["prior_accumulated"] == 180_000_000
    assert by["TS-MAY01"]["accumulated"] == 190_000_000
    assert by["TS-MAY01"]["remaining"] == 170_000_000
    assert tab["total"] == 16_666_667 + 10_000_000
    assert not tab["posted"]

    # Ghi sổ: 1 chứng từ, Nợ 6424 / Có 2141, gộp theo bộ phận
    p = client.post("/api/v1/fixed-assets/depreciation/2026-07/post", headers=h)
    assert p.status_code == 200, p.text
    res = p.json()
    assert res["assets"] == 2 and res["total"] == 26_666_667
    e = client.get(f"/api/v1/journal?period=2026-07", headers=h).json()
    ent = [x for x in e if x["source_ref"] == "kh:2026-07"]
    assert len(ent) == 1
    lines = ent[0]["lines"]
    assert round(sum(l["debit"] for l in lines)) == 26_666_667
    assert {l["account"] for l in lines} == {"6424", "2141"}
    # ĐỢT R3a 16/10/2026 — bộ phận chuyển sang cột `bo_phan`; `item_code` nay chỉ còn chở mã
    # khoản mục chi phí. Bản này SIẾT hơn bản cũ: nó đòi thêm `item_code` phải RỖNG, tức
    # chứng minh bộ phận không còn rò sang cột khoản mục nữa.
    assert sorted(l["bo_phan"] for l in lines if l["debit"] > 0) == ["cntt", "doi_xe"]
    assert all(l["item_code"] == "" for l in lines), "bộ phận còn rò sang cột khoản mục"

    # Ghi sổ lần hai phải bị chặn
    assert client.post("/api/v1/fixed-assets/depreciation/2026-07/post", headers=h).status_code == 422

    # Kỳ sau: lũy kế đã cộng dồn đúng phần vừa ghi sổ
    tab8 = client.get("/api/v1/fixed-assets/depreciation?period=2026-08", headers=h).json()
    by8 = {x["code"]: x for x in tab8["rows"]}
    assert by8["TS-MAY01"]["prior_accumulated"] == 190_000_000

    # Thanh lý → thôi trích từ tháng thanh lý
    aid = by8["TS-XE01"]["asset_id"]
    d = client.post(f"/api/v1/fixed-assets/{aid}/dispose", headers=h, json={"on": "2026-08-10", "reason": "Bán xe"})
    assert d.status_code == 200, d.text
    tab8b = client.get("/api/v1/fixed-assets/depreciation?period=2026-08", headers=h).json()
    assert {x["code"]: x for x in tab8b["rows"]}["TS-XE01"]["amount"] == 0

    # Excel bảng tính khấu hao
    x = client.get("/api/v1/fixed-assets/depreciation.xlsx?period=2026-07", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_phan_bo_242():
    h = login("ketoan")
    r = client.post("/api/v1/prepaid", headers=h, json={
        "code": "CC-BH01", "name": "Bảo hiểm xe 12 tháng", "kind": "cp_tra_truoc", "expense_account": "6423",
        "department": "doi_xe", "start_date": "2026-07-01", "amount": 120_000_000, "months": 12})
    assert r.status_code == 201, r.text
    assert r.json()["monthly"] == 10_000_000

    tab = client.get("/api/v1/prepaid/allocation?period=2026-07", headers=h).json()
    row = {x["code"]: x for x in tab["rows"]}["CC-BH01"]
    assert row["amount"] == 10_000_000 and row["remaining"] == 110_000_000 and row["months_left"] == 11

    p = client.post("/api/v1/prepaid/allocation/2026-07/post", headers=h)
    assert p.status_code == 200, p.text
    ent = [x for x in client.get("/api/v1/journal?period=2026-07", headers=h).json() if x["source_ref"] == "pb:2026-07"]
    assert len(ent) == 1
    assert {l["account"] for l in ent[0]["lines"]} == {"6423", "242"}
    assert round(sum(l["debit"] for l in ent[0]["lines"])) == 10_000_000

    tab8 = client.get("/api/v1/prepaid/allocation?period=2026-08", headers=h).json()
    assert {x["code"]: x for x in tab8["rows"]}["CC-BH01"]["prior_allocated"] == 10_000_000

    x = client.get("/api/v1/prepaid/allocation.xlsx?period=2026-07", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_khong_trich_qua_gia_tri_con_lai():
    """Kỳ cuối chỉ trích đúng phần còn lại, không trích vượt nguyên giá."""
    h = login("ketoan")
    r = client.post("/api/v1/prepaid", headers=h, json={
        "code": "CC-LE01", "name": "Khoản lẻ 3 kỳ", "kind": "ccdc", "start_date": "2029-09-01",
        "amount": 10_000_000, "months": 3})
    assert r.status_code == 201, r.text
    monthly = r.json()["monthly"]                       # 3.333.333
    got = []
    for per in ("2029-09", "2029-10", "2029-11", "2029-12"):
        tab = client.get(f"/api/v1/prepaid/allocation?period={per}", headers=h).json()
        row = {x["code"]: x for x in tab["rows"]}.get("CC-LE01")
        amt = row["amount"] if row else 0
        got.append(amt)
        if amt > 0:
            assert client.post(f"/api/v1/prepaid/allocation/{per}/post", headers=h).status_code == 200
    assert got[0] == got[1] == monthly
    assert sum(got) == 10_000_000, got                   # kỳ cuối lấy đúng phần dư, tổng khớp giá trị gốc
    assert got[3] == 0


def test_khoa_ky_chan_ghi_so():
    h = login("ketoan")
    client.post("/api/v1/prepaid", headers=h, json={
        "code": "CC-KHOA", "name": "Khoản kỳ bị khóa", "start_date": "2030-01-01", "amount": 6_000_000, "months": 6})
    assert client.post("/api/v1/periods/2030-01/lock", headers=h, json={"note": "test"}).status_code == 200
    r = client.post("/api/v1/prepaid/allocation/2030-01/post", headers=h)
    assert r.status_code == 422 and "khóa" in r.json()["detail"]
