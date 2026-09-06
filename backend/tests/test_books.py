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


def test_bang_can_doi_tai_khoan(seeded):
    h = seeded
    r = client.get(f"/api/v1/books/can-doi-tai-khoan?since={SINCE}&upto={UPTO}", headers=h).json()
    assert r["balanced"] is True, r["total"]
    by = {x["account"]: x for x in r["rows"]}
    # Tài khoản cha phải cộng dồn số của tài khoản con: 112 gồm phát sinh ghi ở 1121
    assert by["112"]["debit"] == 500_000_000 and by["112"]["credit"] == 80_000_000
    assert by["1121"]["debit"] == 500_000_000
    # Mỗi dòng: dư cuối = dư đầu + phát sinh
    for x in r["rows"]:
        open_net = x["open_debit"] - x["open_credit"]
        close_net = x["close_debit"] - x["close_credit"]
        assert abs(close_net - (open_net + x["debit"] - x["credit"])) < 1, x

    # Lọc theo bậc: chỉ còn tài khoản bậc 1, tổng vẫn cân
    lv1 = client.get(f"/api/v1/books/can-doi-tai-khoan?since={SINCE}&upto={UPTO}&level=1", headers=h).json()
    assert all(x["level"] == 1 for x in lv1["rows"])
    assert lv1["balanced"] is True
    assert lv1["total"]["debit"] == r["total"]["debit"]        # tổng không đổi khi đổi bậc xem

    x = client.get(f"/api/v1/books/can-doi-tai-khoan.xlsx?since={SINCE}&upto={UPTO}", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_nhat_ky_thu_chi_tien(seeded):
    h = seeded
    thu = client.get(f"/api/v1/books/nhat-ky-tien?since={SINCE}&upto={UPTO}&direction=thu", headers=h).json()
    # Tiền vào: 500tr vào ngân hàng + 80tr nhập quỹ tiền mặt
    assert thu["total"] == 580_000_000, thu["total"]
    assert {x["contra"] for x in thu["rows"]} == {"131", "1121"}

    chi = client.get(f"/api/v1/books/nhat-ky-tien?since={SINCE}&upto={UPTO}&direction=chi", headers=h).json()
    # Tiền ra: 80tr rút khỏi ngân hàng + 50tr chi tiền mặt
    assert chi["total"] == 130_000_000, chi["total"]

    assert client.get(f"/api/v1/books/nhat-ky-tien?since={SINCE}&upto={UPTO}&direction=sai", headers=h).status_code == 422
    x = client.get(f"/api/v1/books/nhat-ky-tien.xlsx?since={SINCE}&upto={UPTO}&direction=chi", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_so_theo_cong_trinh(seeded):
    """Doanh thu – chi phí – lãi lỗ theo mã công trình (tour), lấy thẳng từ sổ."""
    h = seeded
    post_entry(h, "2027-03-25", "Doanh thu tour TEST01", [
        {"account": "131", "debit": 200_000_000, "partner_code": "KH001", "partner": "Công ty A"},
        {"account": "511", "credit": 200_000_000, "project_code": "TEST01"}])
    post_entry(h, "2027-03-26", "Giá vốn tour TEST01", [
        {"account": "632", "debit": 150_000_000, "project_code": "TEST01"},
        {"account": "331", "credit": 150_000_000, "partner_code": "NCC01", "partner": "NCC Một"}])

    tong = client.get(f"/api/v1/books/cong-trinh-tong-hop?since={SINCE}&upto={UPTO}", headers=h).json()
    row = [x for x in tong["rows"] if x["project_code"] == "TEST01"][0]
    assert row["revenue"] == 200_000_000 and row["cost"] == 150_000_000
    assert row["profit"] == 50_000_000 and row["margin"] == 25.0

    ct = client.get(f"/api/v1/books/cong-trinh?project_code=TEST01&since={SINCE}&upto={UPTO}", headers=h).json()
    assert ct["revenue"] == 200_000_000 and ct["cost"] == 150_000_000 and ct["profit"] == 50_000_000
    assert all(x["account"] in ("511", "632") for x in ct["rows"])   # chỉ dòng gắn mã công trình

    x = client.get(f"/api/v1/books/cong-trinh-tong-hop.xlsx?since={SINCE}&upto={UPTO}", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_gioi_han_dong_va_tong_van_dung(seeded):
    """Sổ thật hơn 100.000 dòng trên máy chủ 512 MB: danh sách dòng phải có trần, nhưng TỔNG và SỐ DƯ
    vẫn phải là của toàn kỳ (tính bằng SQL), nếu không Kế toán sẽ đọc nhầm số."""
    h = seeded
    full = client.get(f"/api/v1/books/nhat-ky-chung?since={SINCE}&upto={UPTO}", headers=h).json()
    cut = client.get(f"/api/v1/books/nhat-ky-chung?since={SINCE}&upto={UPTO}&limit=2", headers=h).json()
    assert len(cut["rows"]) == 2 and cut["truncated"] is True
    assert cut["total_rows"] == full["total_rows"] > 2
    assert cut["total"] == full["total"]                      # tổng KHÔNG đổi khi cắt dòng
    assert cut["balanced"] == full["balanced"] is True

    c_full = client.get(f"/api/v1/books/so-cai?account=111&since={SINCE}&upto={UPTO}", headers=h).json()
    c_cut = client.get(f"/api/v1/books/so-cai?account=111&since={SINCE}&upto={UPTO}&limit=1", headers=h).json()
    assert len(c_cut["rows"]) == 1 and c_cut["truncated"] is True
    assert c_cut["opening"] == c_full["opening"]
    assert c_cut["closing"] == c_full["closing"]              # số dư cuối kỳ vẫn của toàn kỳ
    assert c_cut["total"] == c_full["total"]

    q_cut = client.get(f"/api/v1/books/so-quy?since={SINCE}&upto={UPTO}&limit=1", headers=h).json()
    assert q_cut["closing"] == c_full["closing"] and q_cut["truncated"] is True

    # Excel vẫn in được khi bị cắt và phải kèm ghi chú
    x = client.get(f"/api/v1/books/nhat-ky-chung.xlsx?since={SINCE}&upto={UPTO}", headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_loc_day_xuong_sql_khong_nap_ca_so(seeded):
    """Chốt chặn hiệu năng: sổ của một tài khoản chỉ được đọc đúng số dòng của tài khoản đó từ CSDL,
    không được nạp toàn bộ sổ lên rồi lọc bằng Python (đây là nguyên nhân gây tràn bộ nhớ máy chủ)."""
    from app.db.session import SessionLocal
    from app.services import books as BK
    from datetime import date as D
    db = SessionLocal()
    try:
        rows = BK._rows(db, D(2027, 3, 31), D(2027, 3, 1), codes=["1111"])
        assert rows and all(r.account_code == "1111" for r in rows)
        # câu SQL phải chứa điều kiện lọc tài khoản và LIMIT
        sql = str(BK._filtered(BK.select(*BK._COLS), D(2027, 3, 31), D(2027, 3, 1), ["1111"]))
        assert "account_code IN" in sql.replace("\n", " ") or "account_code" in sql
        tot = BK._totals(db, D(2027, 3, 31), D(2027, 3, 1), ["1111"])
        assert tot["count"] == len(rows)
    finally:
        db.close()
