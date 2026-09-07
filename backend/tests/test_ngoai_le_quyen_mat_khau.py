"""Ngoại lệ quyền có thời hạn, tách quyền tab Nhân sự, và mật khẩu tạm (chỉ đạo 07/9/2026).

Ba điều được chốt ở đây, đều là chỗ nếu làm sai thì sai âm thầm:

  1. Quyền xem bảng lương toàn công ty cấp cho MỘT NGƯỜI, không cho cả vai trò. Vai trò "ketoan" có
     nhiều người; nếu chỉ có vai trò làm công cụ thì mở cho Kế toán trưởng là mở cho cả phòng.
  2. Ngoại lệ BẮT BUỘC có hạn và tự hết. Quyền không có hạn chỉ nở ra chứ không co lại – người ta nhớ
     lúc cấp và quên lúc thu.
  3. Mật khẩu do người khác đặt là mật khẩu TẠM. Mặc định nó bằng mã nhân viên, thứ nằm công khai trên
     bảng lương, nên trước khi đổi thì phiên đăng nhập chưa chứng minh được ai đang ngồi trước máy.
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ngoai_le_quyen.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ngoai_le_quyen.db"): os.remove("test_ngoai_le_quyen.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import access as AC
from app.models.core import GRANT_MAX_DAYS, CAPABILITIES

client = TestClient(app); TOK = {}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def login(u, pw="123456"):
    r = client.post("/api/v1/auth/login", data={"username": u, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def tao(username, role, ten="Người kiểm thử", ma="KT999", pw="123456"):
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    u = User(username=username, full_name=ten, role=role, staff_code=ma,
             password_hash=hash_password(pw), active=True)
    db.add(u); db.commit(); uid = u.id; db.close()
    return uid


def tim_tai_khoan(role):
    from app.db.session import SessionLocal
    from sqlalchemy import select
    from app.models.core import User
    db = SessionLocal()
    u = db.execute(select(User).where(User.role == role, User.active == True)).scalars().first()
    ra = (u.id, u.username) if u else (None, None)
    db.close(); return ra


# ---------- tách quyền tab Nhân sự ----------
def test_ke_toan_khong_con_xem_bang_luong_theo_vai_tro():
    assert "ketoan" not in AC.HR_TAB_ROLES["payroll"], "vai trò Kế toán không được mở bảng lương theo vai trò"
    assert "ketoan" in AC.HR_TAB_ROLES["employees"], "Kế toán vẫn cần Hồ sơ nhân sự để hạch toán theo mã NV"


def test_chi_hcns_va_lanh_dao_xem_bang_luong_theo_vai_tro():
    assert set(AC.HR_TAB_ROLES["payroll"]) == set(AC.BASE_VIEW) | {"hcns"}


def test_man_hinh_nhan_su_van_mo_cho_moi_vai_tro_co_it_nhat_mot_tab():
    for tab, roles in AC.HR_TAB_ROLES.items():
        for r in roles:
            assert r in AC.MENU_ROLES["/hr"], f"{r} có tab {tab} nhưng không mở được màn hình /hr"


def test_api_bang_luong_chan_ke_toan():
    uid, un = tim_tai_khoan("ketoan")
    if not un: pytest.skip("dữ liệu mẫu không có tài khoản kế toán")
    r = client.get("/api/v1/payroll-runs/2026-07", headers=login(un))
    assert r.status_code == 403, f"Kế toán vẫn mở được bảng lương: {r.status_code}"


# ---------- ngoại lệ theo người ----------
def test_ngoai_le_mo_bang_luong_cho_dung_mot_nguoi():
    uid, un = tim_tai_khoan("ketoan")
    if not un: pytest.skip("dữ liệu mẫu không có tài khoản kế toán")
    ct = login("chutich")
    r = client.post("/api/v1/access/grants", headers=ct, json={
        "user_id": uid, "kind": "capability", "value": "bang_luong",
        "to_date": str(date.today() + timedelta(days=30)), "reason": "Kế toán trưởng thuê ngoài – hợp đồng dịch vụ"})
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    assert client.get("/api/v1/payroll-runs/2026-07", headers=login(un)).status_code != 403
    me = client.get("/api/v1/auth/me", headers=login(un)).json()
    assert "payroll" in me["hr_tabs"]
    # người khác cùng vai trò KHÔNG được hưởng lây
    uid2 = tao("ketoan.khac", "ketoan", "Kế toán khác", "KT998")
    assert client.get("/api/v1/payroll-runs/2026-07", headers=login("ketoan.khac")).status_code == 403
    # thu hồi sớm thì mất ngay
    assert client.delete(f"/api/v1/access/grants/{gid}", headers=ct).status_code == 200
    assert client.get("/api/v1/payroll-runs/2026-07", headers=login(un)).status_code == 403


def test_ngoai_le_bat_buoc_co_han_va_co_ly_do():
    uid, un = tim_tai_khoan("hcns")
    if not un: pytest.skip("dữ liệu mẫu không có tài khoản HCNS")
    ct = login("chutich")
    qua_han = {"user_id": uid, "kind": "capability", "value": "bang_luong",
               "to_date": str(date.today() + timedelta(days=GRANT_MAX_DAYS + 1)), "reason": "thử"}
    assert client.post("/api/v1/access/grants", headers=ct, json=qua_han).status_code == 422
    khong_ly_do = dict(qua_han, to_date=str(date.today() + timedelta(days=10)), reason="  ")
    assert client.post("/api/v1/access/grants", headers=ct, json=khong_ly_do).status_code == 422


def test_ngoai_le_het_han_tu_mat_hieu_luc():
    """Không cần ai nhớ thu lại: quá ngày là hàm hieu_luc() trả False."""
    from app.models.core import UserGrant
    g = UserGrant(user_id=1, kind="capability", value="bang_luong",
                  from_date=date.today() - timedelta(days=40), to_date=date.today() - timedelta(days=1),
                  reason="đã hết hạn", granted_by="chutich", approved_by="chutich", active=True)
    assert not g.hieu_luc()
    g.to_date = date.today()
    assert g.hieu_luc(), "ngày cuối cùng vẫn còn hiệu lực"


def test_chi_chu_tich_hoac_tgd_cap_duoc_ngoai_le():
    uid, un = tim_tai_khoan("hcns")
    if not un: pytest.skip("dữ liệu mẫu không có tài khoản HCNS")
    for vai in ("cntt", "hcns"):
        _, tk = tim_tai_khoan(vai)
        if not tk: continue
        r = client.post("/api/v1/access/grants", headers=login(tk), json={
            "user_id": uid, "kind": "capability", "value": "bang_luong",
            "to_date": str(date.today() + timedelta(days=10)), "reason": "thử"})
        assert r.status_code == 403, f"{vai} không được tự cấp ngoại lệ quyền"


def test_ngoai_le_chua_duyet_thi_chua_co_hieu_luc():
    from app.models.core import UserGrant
    g = UserGrant(user_id=1, kind="capability", value="bang_luong", from_date=date.today(),
                  to_date=date.today() + timedelta(days=5), reason="chờ duyệt",
                  granted_by="hcns", approved_by="", active=True)
    assert not g.hieu_luc(), "ngoại lệ chưa có người duyệt thì chưa được tính"


# ---------- mật khẩu tạm ----------
def test_dat_lai_mat_khau_bat_co_buoc_doi_va_chan_vao_he_thong():
    uid = tao("nv.matkhau", "nv_kd", "NV mật khẩu", "KT997")
    _, cntt = tim_tai_khoan("cntt")
    if not cntt: pytest.skip("dữ liệu mẫu không có tài khoản CNTT")
    r = client.post(f"/api/v1/users/{uid}/reset-password", headers=login(cntt), json={"new_password": "tam123"})
    assert r.status_code == 200, r.text
    h = login("nv.matkhau", "tam123")
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert me["must_change_password"] is True
    # còn mật khẩu tạm thì mọi màn hình khác đều đóng
    assert client.get("/api/v1/tours", headers=h).status_code == 403
    assert client.get("/api/v1/users", headers=h).status_code == 403
    # nhưng đổi mật khẩu thì được, và đổi xong là mở
    assert client.post("/api/v1/auth/password", headers=h,
                       json={"old_password": "tam123", "new_password": "matkhaumoi1"}).status_code == 200
    h2 = login("nv.matkhau", "matkhaumoi1")
    assert client.get("/api/v1/auth/me", headers=h2).json()["must_change_password"] is False
    assert client.get("/api/v1/tours", headers=h2).status_code == 200


def test_khong_duoc_dat_lai_mat_khau_bang_ma_nhan_vien():
    uid = tao("nv.matkhau2", "nv_kd", "NV mật khẩu 2", "KT996")
    h = login("nv.matkhau2")
    r = client.post("/api/v1/auth/password", headers=h, json={"old_password": "123456", "new_password": "KT996"})
    assert r.status_code == 422, "mã nhân viên nằm công khai trên bảng lương – không dùng làm mật khẩu"


def test_dang_nhap_ghi_lai_lan_cuoi():
    from app.db.session import SessionLocal
    from sqlalchemy import select
    from app.models.core import User
    tao("nv.lastlogin", "nv_kd", "NV last login", "KT995")
    login("nv.lastlogin")
    db = SessionLocal()
    u = db.execute(select(User).where(User.username == "nv.lastlogin")).scalars().first()
    ll = u.last_login; db.close()
    assert ll is not None, "không ghi lần đăng nhập cuối thì không rà được tài khoản bỏ hoang"


def test_danh_muc_nang_luc_co_bang_luong():
    assert "bang_luong" in CAPABILITIES
