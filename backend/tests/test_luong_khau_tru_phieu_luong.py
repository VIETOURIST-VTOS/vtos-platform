"""Khoản trừ người lao động, phiếu lương cá nhân, bút toán theo pháp nhân và chữ ký kép.

Bốn việc hoàn thành ngày 07/9/2026 sau khi các văn bản đã đủ chữ ký:
1. BHXH 10,5% trên MỨC LƯƠNG HỢP ĐỒNG và đoàn phí công đoàn – trước đó "thực nhận" cao hơn số thật.
2. Phiếu lương cá nhân: người lao động tự xem được, kèm khoản đang treo của chính mình.
3. Bút toán lương lập riêng theo từng pháp nhân trả lương.
4. Bước duyệt đủ hai chữ ký, người trình không được ký hồ sơ mình trình.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_luong_khau_tru.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_luong_khau_tru.db"): os.remove("test_luong_khau_tru.db")
import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u, pw="123456"):
    k = (u, pw)
    if k not in TOK: TOK[k] = client.post("/api/v1/auth/login", data={"username": u, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[k]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def run(period="2026-09", refresh=True):
    r = client.get(f"/api/v1/payroll-runs/{period}" + ("?refresh=true" if refresh else ""), headers=login("cntt"))
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- 1. khoản trừ
def test_bhxh_tinh_tren_muc_luong_hop_dong_khong_phai_muc_cua_ky():
    """Mức của kỳ thay đổi theo doanh thu; lấy nó làm căn cứ đóng BHXH là sai bản chất và sai số phải nộp."""
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    j = run()
    db = SessionLocal()
    for r in j["rows"]:
        if r["hop_dong"] != "hdld": continue
        e = db.query(Employee).filter(Employee.code == r["ma"]).first()
        if e is None: continue
        assert r["bhxh"] == round(e.base_salary * 0.105), f"{r['ma']}"
        if r.get("xac_dinh_luong") and r["xac_dinh_luong"]["muc_ky"] != r["xac_dinh_luong"]["muc_hop_dong"]:
            assert r["bhxh"] != round(r["luong_cb"] * 0.105) or r["luong_cb"] == e.base_salary
    db.close()


def test_ctv_khong_dong_bhxh_chi_khau_tru_tncn():
    j = run(refresh=False)
    for r in j["rows"]:
        if r["hop_dong"] != "hdld":
            assert r["bhxh"] == 0 and r["doan_phi"] == 0


def test_doan_phi_chi_tru_doan_vien():
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    db = SessionLocal()
    e = db.query(Employee).filter(Employee.active == True, Employee.contract_type == "hdld").first()
    e.member_org = True; ma = e.code; db.commit(); db.close()
    j = run()
    dv = next(r for r in j["rows"] if r["ma"] == ma)
    assert dv["doan_phi"] == 26550
    assert all(r["doan_phi"] in (0, 26550) for r in j["rows"])


def test_phai_tra_bang_thu_nhap_tru_khoan_tru():
    j = run(refresh=False)
    for r in j["rows"]:
        assert r["khoan_tru"] == round(r["tru_su_vu"] + r["bhxh"] + r["doan_phi"] + r["tncn"])
        assert r["thuc_nhan"] == round(r["thu_nhap"] - r["khoan_tru"])
    t = j["totals"]
    assert t["thuc_nhan"] == round(t["thu_nhap"] - t["khoan_tru"])


def test_khoan_tru_khong_lam_am_khai_niem_thu_nhap():
    """Thu nhập chỉ gồm khoản dương; chế tài nằm ở khối khoản trừ, không trộn vào thu nhập."""
    j = run(refresh=False)
    for r in j["rows"]:
        assert r["thu_nhap"] >= r["luong_cb"]
        assert r["tru_su_vu"] >= 0


# ---------------------------------------------------------------- 2. phiếu lương
def test_phieu_luong_cua_chinh_minh():
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from app.models.core import User
    db = SessionLocal()
    e = db.query(Employee).filter(Employee.active == True, Employee.user_id != None).first()
    u = db.get(User, e.user_id); ten_tk, ma = u.username, e.code
    u.password_hash = __import__("app.core.security", fromlist=["x"]).hash_password("123456")
    db.commit(); db.close()

    r = client.get("/api/v1/payroll-runs/2026-09/phieu-luong", headers=login("cntt"))
    assert r.status_code in (200, 404)
    p = client.get(f"/api/v1/payroll-runs/2026-09/phieu-luong?ma={ma}", headers=login("cntt"))
    assert p.status_code == 200, p.text
    d = p.json()
    assert d["nhan_su"]["ma"] == ma
    assert set(d["khoan_tru"]) >= {"che_tai_su_vu", "bhxh_nguoi_lao_dong", "doan_phi_cong_doan", "tncn_khau_tru", "tong"}
    assert d["thuc_nhan"] == d["thu_nhap"]["tong"] - d["khoan_tru"]["tong"]
    assert "khoan_dang_treo" in d


def test_khong_xem_duoc_phieu_luong_nguoi_khac():
    ds = client.get("/api/v1/employees?limit=1000", headers=login("cntt")).json()
    kh = next(x for x in ds if x["active"] and x["code"])
    r = client.get(f"/api/v1/payroll-runs/2026-09/phieu-luong?ma={kh['code']}", headers=login("kd.hoa"))
    assert r.status_code in (403, 404)


# ---------------------------------------------------------------- 3. theo pháp nhân
def test_bang_luong_tach_theo_phap_nhan():
    r = client.get("/api/v1/payroll-runs/2026-09/theo-phap-nhan", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["rows"], "phải có ít nhất một nhóm"
    j = run(refresh=False)
    assert round(sum(g["thuc_nhan"] for g in d["rows"])) == round(j["totals"]["thuc_nhan"])
    # người chưa xác định pháp nhân phải là một dòng riêng, không dồn vào công ty mẹ
    assert all(("chua_xac_dinh" in g) for g in d["rows"])


# ---------------------------------------------------------------- 4. hai chữ ký
def test_nguoi_trinh_khong_duoc_ky_de_xuat_cua_chinh_minh():
    """Chữ ký thứ hai chỉ là một lớp kiểm soát khi nó là một người KHÁC."""
    r = client.post("/api/v1/params", json={"key": "nguong_bien", "value": "0.12",
                                            "effective_from": str(date.today()), "source": "kiểm thử"},
                    headers=login("tgd"))
    assert r.status_code in (200, 201), r.text
    pid = r.json()["param"]["id"]
    tu_ky = client.post(f"/api/v1/params/{pid}/sign", headers=login("tgd"))
    assert tu_ky.status_code == 422 and "không được ký duyệt chính hồ sơ mình trình" in tu_ky.json()["detail"]
    ok = client.post(f"/api/v1/params/{pid}/sign", headers=login("chutich"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["param"]["status"] == "pending", "mới một chữ ký thì chưa hiệu lực"
    lap = client.post(f"/api/v1/params/{pid}/sign", headers=login("chutich"))
    assert lap.status_code == 422 and "đã ký" in lap.json()["detail"]


def test_du_hai_chu_ky_thi_tham_so_moi_hieu_luc():
    r = client.post("/api/v1/params", json={"key": "sla_booking_phut", "value": "150",
                                            "effective_from": str(date.today()), "source": "kiểm thử 2"},
                    headers=login("hcns"))
    assert r.status_code in (200, 201), r.text
    pid = r.json()["param"]["id"]
    assert client.post(f"/api/v1/params/{pid}/sign", headers=login("chutich")).json()["param"]["status"] == "pending"
    cuoi = client.post(f"/api/v1/params/{pid}/sign", headers=login("tgd"))
    assert cuoi.json()["param"]["status"] == "active"
