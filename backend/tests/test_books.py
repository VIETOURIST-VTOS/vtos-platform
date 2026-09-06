"""Sổ kế toán chuẩn theo mẫu MISA: Nhật ký chung, Sổ Cái (có TK đối ứng), Sổ chi tiết, Sổ quỹ, Sổ tiền gửi, Sổ công nợ."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_books.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_books.db"): os.remove("test_books.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
# Đặt sau mốc chốt sổ kiểm toán 30/06/2026 để không làm lệch số BCTC mà test_misa kiểm tra
SINCE, UPTO = "2027-03-01", "2027-03-31"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def post_entry(h, d, desc, lines):
    """Lập và GHI SỔ luôn – sổ kế toán chỉ lấy chứng từ đã ghi sổ, chứng từ nháp không lên sổ."""
    r = client.post("/api/v1/journal", headers=h, json={"entry_date": d, "description": desc, "lines": lines, "post": True})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def seeded():
    """Ba bút toán mẫu trong tháng 3/2027 để soi đúng từng cột của sổ."""
    h = login("ketoan")
    # 1. Khách VIETRIP trả tiền vào ngân hàng TPBank: Nợ 1121 / Có 131
    post_entry(h, "2027-03-05", "Khách A chuyển khoản tiền tour", [
        {"account": "1121", "debit": 500_000_000, "partner_code": "TPB", "partner": "TPBank"},
        {"account": "131", "credit": 500_000_000, "partner_code": "KH001", "partner": "Công ty A"}])
    # 2. Rút tiền gửi về quỹ tiền mặt: Nợ 1111 / Có 1121
    post_entry(h, "2027-03-10", "Rút tiền gửi nhập quỹ", [
        {"account": "1111", "debit": 80_000_000},
        {"account": "1121", "credit": 80_000_000, "partner_code": "TPB", "partner": "TPBank"}])
    # 3. Chi tiền mặt trả 2 nhà cung cấp (chứng từ nhiều vế → TK đối ứng phải liệt kê cả hai)
    post_entry(h, "2027-03-20", "Chi tiền mặt trả nhà cung cấp", [
        {"account": "331", "debit": 30_000_000, "partner_code": "NCC01", "partner": "NCC Một"},
        {"account": "331", "debit": 20_000_000, "partner_code": "NCC02", "partner": "NCC Hai"},
        {"account": "1111", "credit": 50_000_000}])
    return h


def test_nhat_ky_chung(seeded):
    h = seeded
    r = client.get(f"/api/v1/books/nhat-ky-chung?since={SINCE}&upto={UPTO}", headers=h)
    assert r.status_code == 200, r.text
    rep = r.json()
    mine = [x for x in rep["rows"] if x["code"] and x["description"].startswith(("Khách A", "Rút tiền", "Chi tiền mặt"))]
    assert len(mine) == 7                              # 2 + 2 + 3 dòng
    assert rep["balanced"] is True                     # tổng Nợ = tổng Có
    thu = [x for x in mine if x["account"] == "1121" and x["debit"] > 0][0]
    assert thu["contra"] == "131"                      # TK đối ứng của vế Nợ là vế Có
    x = client.get(f"/api/v1/books/nhat-ky-chung.xlsx?since={SINCE}&upto={UPTO}", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_so_cai_gom_tai_khoan_con_va_tk_doi_ung(seeded):
    h = seeded
    # Sổ Cái TK 112 (tổng) phải gồm phát sinh ghi ở TK con 1121
    r = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()
    assert "1121" in r["accounts"]
    codes = {x["account"] for x in r["rows"]}
    assert codes == {"1121"}, codes
    assert r["total"]["debit"] == 500_000_000 and r["total"]["credit"] == 80_000_000
    assert r["closing"] == r["opening"] + 420_000_000

    # Số dư luỹ kế chạy đúng theo thứ tự ngày
    bal = r["opening"]
    for row in r["rows"]:
        bal += row["debit"] - row["credit"]
        assert row["balance"] == bal

    # Chứng từ nhiều vế: dòng Có 1111 đối ứng với CẢ HAI dòng Nợ 331
    tm = client.get(f"/api/v1/books/so-cai?account=111&since={SINCE}&upto={UPTO}", headers=h).json()
    chi = [x for x in tm["rows"] if x["credit"] > 0][0]
    assert chi["contra"] == "331", chi["contra"]
    thu = [x for x in tm["rows"] if x["debit"] > 0][0]
    assert thu["contra"] == "1121"

    x = client.get(f"/api/v1/books/so-cai.xlsx?account=112&since={SINCE}&upto={UPTO}", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"
    assert client.get(f"/api/v1/books/so-cai?account=999&since={SINCE}&upto={UPTO}", headers=h).status_code == 404


def test_so_quy_va_so_tien_gui(seeded):
    h = seeded
    q = client.get(f"/api/v1/books/so-quy?since={SINCE}&upto={UPTO}", headers=h).json()
    assert q["total"]["in"] == 80_000_000 and q["total"]["out"] == 50_000_000
    assert q["closing"] == q["opening"] + 30_000_000
    tail = q["rows"][-1]
    assert tail["balance"] == q["closing"]

    # Sổ tiền gửi lọc theo từng ngân hàng
    banks = client.get(f"/api/v1/books/ngan-hang?since={SINCE}&upto={UPTO}", headers=h).json()
    tpb = [b for b in banks["rows"] if b["partner_code"] == "TPB"][0]
    assert tpb["debit"] == 500_000_000 and tpb["credit"] == 80_000_000

    sg = client.get(f"/api/v1/books/so-tien-gui?since={SINCE}&upto={UPTO}&partner_code=TPB", headers=h).json()
    assert sg["total"]["in"] == 500_000_000 and sg["total"]["out"] == 80_000_000
    assert all(x["partner_code"] == "TPB" for x in sg["rows"])
    sg0 = client.get(f"/api/v1/books/so-tien-gui?since={SINCE}&upto={UPTO}&partner_code=KHONGCO", headers=h).json()
    assert sg0["rows"] == [] and sg0["total"]["in"] == 0

    for url in (f"/api/v1/books/so-quy.xlsx?since={SINCE}&upto={UPTO}",
                f"/api/v1/books/so-tien-gui.xlsx?since={SINCE}&upto={UPTO}&partner_code=TPB"):
        x = client.get(url, headers=h)
        assert x.status_code == 200 and x.content[:2] == b"PK"


def test_so_cong_no_theo_doi_tuong(seeded):
    h = seeded
    tong = client.get(f"/api/v1/books/cong-no-tong-hop?account=331&since={SINCE}&upto={UPTO}", headers=h).json()
    by = {r["partner_code"]: r for r in tong["rows"]}
    assert by["NCC01"]["debit"] == 30_000_000 and by["NCC02"]["debit"] == 20_000_000
    for r in tong["rows"]:
        assert r["closing"] == r["opening"] + r["debit"] - r["credit"]

    ct = client.get(f"/api/v1/books/cong-no?account=331&partner_code=NCC01&since={SINCE}&upto={UPTO}", headers=h).json()
    assert ct["partner_name"] == "NCC Một"
    assert len(ct["rows"]) == 1 and ct["rows"][0]["debit"] == 30_000_000
    assert ct["rows"][0]["contra"] == "1111"

    for url in (f"/api/v1/books/cong-no-tong-hop.xlsx?account=331&since={SINCE}&upto={UPTO}",
                f"/api/v1/books/cong-no.xlsx?account=331&partner_code=NCC01&since={SINCE}&upto={UPTO}"):
        x = client.get(url, headers=h)
        assert x.status_code == 200 and x.content[:2] == b"PK"


def test_danh_muc_so_va_phan_quyen(seeded):
    h = seeded
    cat = client.get("/api/v1/books", headers=h).json()
    assert {c["key"] for c in cat} >= {"nhat-ky-chung", "so-cai", "so-quy", "so-tien-gui", "cong-no"}
    # Sổ kế toán không mở cho vai trò kinh doanh
    kd = client.post("/api/v1/auth/login", data={"username": "kd.hoa", "password": "123456"})
    if kd.status_code == 200:
        hk = {"Authorization": f"Bearer {kd.json()['access_token']}"}
        assert client.get(f"/api/v1/books/nhat-ky-chung?since={SINCE}&upto={UPTO}", headers=hk).status_code == 403
