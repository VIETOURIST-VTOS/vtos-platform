"""Vai trò Tài xế & HDV và vai trò Chuyên viên Visa (chỉ đạo 07/9/2026).

Trước đây quy ước "trang không liệt kê trong MENU_ROLES = ai đăng nhập cũng thấy" là an toàn với nhân viên
văn phòng, nhưng sai với hai vai trò mới: nó cho tài xế thấy cả Bảng lương và Tài khoản ngân hàng chỉ vì hai
trang đó chưa được liệt kê. Với vai trò bị giới hạn, danh sách phải là DANH SÁCH CHO PHÉP.

Bộ phép thử này giữ hai điều: người ở hiện trường chỉ thấy đúng màn hình của mình, và màn hình đó chỉ trả
về việc của chính họ – không phải bản rút gọn của màn hình Điều hành.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vai_tro_xe_hdv_visa.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vai_tro_xe_hdv_visa.db"): os.remove("test_vai_tro_xe_hdv_visa.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import access as AC
from app.models.core import ROLES

client = TestClient(app); TOK = {}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def login(u, pw="123456"):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": pw})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


def tao_tai_khoan(username, role, ten, phong, vi_tri, ma):
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hr import Employee
    from app.core.security import hash_password
    db = SessionLocal()
    u = User(username=username, full_name=ten, role=role, department=phong, staff_code=ma,
             password_hash=hash_password("123456"), active=True)
    db.add(u); db.flush()
    e = db.execute(__import__("sqlalchemy").select(Employee).where(Employee.code == ma)).scalars().first()
    if e is None:
        e = Employee(code=ma, full_name=ten, department=phong, position=vi_tri); db.add(e); db.flush()
    e.user_id = u.id; e.department = phong; e.position = vi_tri; e.active = True
    db.commit(); eid = e.id; db.close()
    return eid


def test_hai_vai_tro_moi_co_trong_danh_muc():
    assert ROLES["xe_hdv"] and ROLES["nv_visa"]


def test_vai_tro_bi_gioi_han_chi_thay_dung_mot_man_hinh():
    tao_tai_khoan("taixe.kt", "xe_hdv", "Tài xế kiểm thử", "doi_xe", "tai_xe", "KT901")
    me = client.get("/api/v1/auth/me", headers=login("taixe.kt")).json()
    an = set(me["hidden_menus"])
    assert "/xe-hdv" not in an
    for trang in ("/payroll", "/bank-accounts", "/accounting", "/requests", "/tours", "/hr", "/ops", "/audit", "/companies", "/", "/alerts", "/reports"):
        assert trang in an, f"tài xế không được thấy {trang}"
    assert AC.menus_for(type("U", (), {"role": "xe_hdv"})()) == ["/xe-hdv"]


def test_visa_chi_thay_phan_he_visa():
    tao_tai_khoan("visa.kt", "nv_visa", "Chuyên viên visa kiểm thử", "visa", "visa", "KT902")
    me = client.get("/api/v1/auth/me", headers=login("visa.kt")).json()
    an = set(me["hidden_menus"])
    assert "/visa" not in an
    for trang in ("/payroll", "/bank-accounts", "/accounting", "/tours", "/hr", "/ops", "/"):
        assert trang in an, f"chuyên viên visa không được thấy {trang}"


def test_vai_tro_van_phong_khong_bi_anh_huong():
    """Thay đổi trên chỉ áp cho vai trò bị giới hạn – nhân viên kinh doanh vẫn thấy trang không liệt kê."""
    me = client.get("/api/v1/auth/me", headers=login("kd.hoa")).json()
    assert "/" not in me["hidden_menus"] and "/alerts" not in me["hidden_menus"]
    assert "/accounting" in me["hidden_menus"]


def test_man_hinh_cua_toi_chi_tra_ve_viec_cua_chinh_minh():
    eid = tao_tai_khoan("taixe.kt2", "xe_hdv", "Tài xế kiểm thử hai", "doi_xe", "tai_xe", "KT903")
    xe = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    x = next(v for v in xe if v["active"])
    assert client.put(f"/api/v1/vehicles/{x['id']}", json={"driver_id": eid}, headers=login("cntt")).status_code == 200

    d = client.get("/api/v1/xe-hdv/cua-toi", headers=login("taixe.kt2")).json()
    assert d["ho_so"]["code"] == "KT903"
    assert [v["plate"] for v in d["xe"]] == [x["plate"]], "chỉ thấy xe mình đứng tên"
    assert d["the_hdv"] is None

    khac = client.get("/api/v1/xe-hdv/cua-toi", headers=login("taixe.kt")).json()
    assert khac["xe"] == [], "tài xế khác không thấy xe của người này"


def test_tai_xe_khong_goi_duoc_api_dieu_hanh():
    for path in ("/api/v1/dispatch", "/api/v1/vehicles", "/api/v1/employees", "/api/v1/payroll-runs/2026-08", "/api/v1/tours"):
        r = client.get(path, headers=login("taixe.kt"))
        assert r.status_code == 403, f"{path} phải bị chặn với vai trò xe_hdv (đang trả {r.status_code})"


def test_tai_khoan_chua_ghep_ho_so_bao_loi_ro_rang():
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    db.add(User(username="taixe.mocoi", full_name="Tài xế chưa ghép", role="xe_hdv", department="doi_xe",
                password_hash=hash_password("123456"), active=True))
    db.commit(); db.close()
    r = client.get("/api/v1/xe-hdv/cua-toi", headers=login("taixe.mocoi"))
    assert r.status_code == 404 and "HCNS" in r.json()["detail"]


def test_hanh_chinh_khong_xem_duoc_bang_luong():
    """Bảo vệ, pháp chế, quan hệ nhà đầu tư thuộc phòng Hành chính nhưng KHÔNG được xem bảng lương
    (chỉ đạo 07/9/2026). Trước đây họ mang vai trò Nhân sự Hành chính nên thấy lương cả công ty."""
    tao_tai_khoan("baove.kt", "hanh_chinh", "Bảo vệ kiểm thử", "hcns", "khac", "KT904")
    me = client.get("/api/v1/auth/me", headers=login("baove.kt")).json()
    an = set(me["hidden_menus"])
    assert "/hr" in an, "không được thấy hồ sơ nhân sự và bảng lương (/payroll chỉ chuyển hướng sang /hr)"
    assert "/bank-accounts" in an
    assert "/reports" not in an, "vẫn phải nộp được báo cáo công việc"
    for path in ("/api/v1/payroll-runs/2026-08", "/api/v1/employees"):
        assert client.get(path, headers=login("baove.kt")).status_code == 403


def test_bang_luong_va_ngan_hang_khong_con_la_trang_ai_cung_thay():
    """Hai trang này trước đây không liệt kê trong ma trận, nghĩa là mọi vai trò đăng nhập đều thấy."""
    from app.services.access import MENU_ROLES
    assert "/bank-accounts" in MENU_ROLES and "nv_dh" not in MENU_ROLES["/bank-accounts"]
    assert "nv_kd" not in MENU_ROLES["/hr"], "bảng lương nằm trong /hr – khối kinh doanh không được thấy"
