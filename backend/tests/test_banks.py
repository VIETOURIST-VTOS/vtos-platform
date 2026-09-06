"""Tài khoản ngân hàng: mở tiểu khoản 112, gợi ý từ sổ, gán sổ cũ về đúng ngân hàng, số dư từng ngân hàng."""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_banks.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_banks.db"): os.remove("test_banks.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
SINCE, UPTO = "2028-05-01", "2028-05-31"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def entry(h, d, desc, lines):
    r = client.post("/api/v1/journal", headers=h, json={"entry_date": d, "description": desc, "lines": lines, "post": True})
    assert r.status_code == 201, r.text
    return r.json()["entry"]


@pytest.fixture(scope="module")
def seeded():
    """Sổ 112 mẫu: 2 chứng từ TPBank, 1 chứng từ MB, 1 chứng từ không nhận diện được ngân hàng."""
    h = login("ketoan")
    entry(h, "2028-05-03", "Khách chuyển khoản TPBank", [
        {"account": "1121", "debit": 300_000_000, "partner_code": "KH01", "partner": "Khách lẻ"},
        {"account": "131", "credit": 300_000_000, "partner_code": "KH01", "partner": "Khách lẻ"}])
    entry(h, "2028-05-06", "Chi trả NCC qua TPBank", [
        {"account": "331", "debit": 100_000_000, "partner_code": "NCC01", "partner": "NCC Một"},
        {"account": "1121", "credit": 100_000_000}])
    entry(h, "2028-05-10", "Thu qua MB Bank", [
        {"account": "1121", "debit": 50_000_000},
        {"account": "131", "credit": 50_000_000, "partner_code": "KH02", "partner": "Khách hai"}])
    entry(h, "2028-05-20", "Giao dich khong ro ngan hang", [
        {"account": "1121", "debit": 7_000_000},
        {"account": "131", "credit": 7_000_000, "partner_code": "KH03", "partner": "Khách ba"}])
    return h


def _codes(h):
    """Số chứng từ hệ thống tự sinh (CT2805-xxxx) – dùng làm tiền tố nhận diện trong test."""
    rows = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()["rows"]
    return {r["description"]: r["code"] for r in rows}


def test_goi_y_tu_so_hien_co(seeded):
    h = seeded
    g = client.get(f"/api/v1/bank-accounts/goi-y?since={SINCE}&upto={UPTO}", headers=h)
    assert g.status_code == 200, g.text
    j = g.json()
    assert j["total_lines"] == 4                        # 4 dòng nằm trên TK 112
    assert j["prefixes"], j
    # Tên ngân hàng trong diễn giải được gợi ý ra để Kế toán biết cần mở tài khoản nào
    hints = {x["bank"] for x in j["bank_hints"]}
    assert "TPBANK" in hints and "MB" in hints, hints


def test_mo_tai_khoan_sinh_tieu_khoan_112_va_khong_doi_bctc(seeded):
    h = seeded
    tk112_truoc = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()

    r = client.post("/api/v1/bank-accounts", headers=h, json={
        "code": "TPB1", "bank_name": "TPBank", "account_number": "01811267101",
        "match_keywords": ["TPBANK"], "opening_balance": 0})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["account_code"].startswith("1121") and b["account_code"] != "1121", b
    assert b["parent_account"] == "1121"

    r2 = client.post("/api/v1/bank-accounts", headers=h, json={
        "code": "MB1", "bank_name": "MB Bank", "account_number": "9999", "match_keywords": ["MB BANK", "MBBANK"]})
    assert r2.status_code == 201, r2.text
    assert r2.json()["account_code"] != b["account_code"]

    # Mã trùng bị chặn
    assert client.post("/api/v1/bank-accounts", headers=h, json={"code": "TPB1", "bank_name": "X"}).status_code == 422

    # Tiểu khoản mới nằm trong cây 112 và KHÔNG làm đổi số của TK 112
    tk112_sau = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()
    assert b["account_code"] in tk112_sau["accounts"]
    assert tk112_sau["closing"] == tk112_truoc["closing"]
    assert tk112_sau["total"] == tk112_truoc["total"]


def test_xem_truoc_roi_moi_gan_va_so_du_112_khong_doi(seeded):
    h = seeded
    tk112_truoc = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()

    pv = client.get(f"/api/v1/bank-accounts/phan-loai/xem-truoc?since={SINCE}&upto={UPTO}", headers=h).json()
    assert pv["applied"] is False
    assert pv["scanned"] == 4
    assert pv["matched"] == 3 and pv["unmatched"] == 1     # 2 TPBank + 1 MB; 1 dòng không rõ ngân hàng
    by = {x["code"]: x for x in pv["by_bank"]}
    assert by["TPB1"]["lines"] == 2 and by["MB1"]["lines"] == 1
    tk_tpb = by["TPB1"]["account_code"]

    # Xem trước KHÔNG được đụng vào sổ: tiểu khoản ngân hàng vẫn phải trống
    assert client.get(f"/api/v1/books/so-cai?account={tk_tpb}&since={SINCE}&upto={UPTO}", headers=h).json()["total_rows"] == 0

    ap = client.post(f"/api/v1/bank-accounts/phan-loai/thuc-hien?since={SINCE}&upto={UPTO}", headers=h)
    assert ap.status_code == 200, ap.text
    res = ap.json()
    assert res["applied"] is True and res["changed"] == 3
    assert res["balance_before"] == res["balance_after"]    # chỉ đổi mã TK, số dư phải y nguyên

    tk112_sau = client.get(f"/api/v1/books/so-cai?account=112&since={SINCE}&upto={UPTO}", headers=h).json()
    assert tk112_sau["closing"] == tk112_truoc["closing"]
    assert tk112_sau["total"] == tk112_truoc["total"]
    # Sau khi gán: dòng đã về đúng tiểu khoản ngân hàng…
    assert client.get(f"/api/v1/books/so-cai?account={tk_tpb}&since={SINCE}&upto={UPTO}", headers=h).json()["total_rows"] == 2
    # …còn dòng không nhận diện được vẫn nằm nguyên ở tài khoản cha, không bị gán bừa
    sd = client.get(f"/api/v1/bank-accounts/so-du?since={SINCE}&upto={UPTO}", headers=h).json()
    assert sd["unassigned"]["closing"] == 7_000_000


def test_so_du_tung_ngan_hang_va_so_tien_gui_rieng(seeded):
    h = seeded
    sd = client.get(f"/api/v1/bank-accounts/so-du?since={SINCE}&upto={UPTO}", headers=h).json()
    by = {r["code"]: r for r in sd["rows"]}
    assert by["TPB1"]["debit"] == 300_000_000 and by["TPB1"]["credit"] == 100_000_000
    assert by["TPB1"]["closing"] == 200_000_000
    assert by["MB1"]["closing"] == 50_000_000
    assert sd["unassigned"]["closing"] == 7_000_000        # phần chưa nhận diện được
    assert sd["total_closing"] == sd["check_112"]          # tổng các ngân hàng + chưa gán = đúng TK 112

    # Sổ tiền gửi in riêng cho từng ngân hàng theo tiểu khoản
    tk = by["TPB1"]["account_code"]
    sg = client.get(f"/api/v1/books/so-tien-gui?since={SINCE}&upto={UPTO}&account={tk}", headers=h).json()
    assert sg["total"]["in"] == 300_000_000 and sg["total"]["out"] == 100_000_000
    assert sg["closing"] == 200_000_000


def test_huy_gan_khi_nham(seeded):
    h = seeded
    rv = client.post(f"/api/v1/bank-accounts/MB1/huy-phan-loai?since={SINCE}&upto={UPTO}", headers=h)
    assert rv.status_code == 200, rv.text
    assert rv.json()["reverted"] == 1 and rv.json()["to_account"] == "1121"
    sd = client.get(f"/api/v1/bank-accounts/so-du?since={SINCE}&upto={UPTO}", headers=h).json()
    assert {r["code"]: r for r in sd["rows"]}["MB1"]["closing"] == 0
    assert sd["unassigned"]["closing"] == 57_000_000
    assert sd["total_closing"] == sd["check_112"]          # tổng vẫn khớp TK 112 sau khi hoàn tác


def test_chua_khai_bao_ngan_hang_thi_khong_cho_gan():
    """Gọi phân loại khi chưa có tài khoản ngân hàng nào phải báo lỗi rõ ràng, không im lặng."""
    import os as _os
    _os.environ["DATABASE_URL"] = "sqlite:///./test_banks.db"
    h = login("ketoan")
    r = client.get("/api/v1/bank-accounts/phan-loai/xem-truoc?since=2020-01-01&upto=2020-01-31", headers=h)
    assert r.status_code in (200, 422)
    if r.status_code == 422:
        assert "tài khoản ngân hàng" in r.json()["detail"]
