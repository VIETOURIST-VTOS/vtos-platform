"""Suy pháp nhân cho tài khoản từ hồ sơ nhân sự.

Đo trên hệ thống thật ngày 08/9/2026: 109/110 nhân sự đang làm việc đã có pháp nhân, nhưng chỉ 1/116
tài khoản đang hoạt động có. Phạm vi pháp nhân theo phiên đăng nhập vì thế đang giới hạn đúng một
người. Chỗ trống ấy không phải chỗ trống của quyết định – người quản trị đã quyết ở hồ sơ nhân sự,
chỉ chưa chép sang tài khoản.

Bốn phép thử quan trọng nhất tệp này đều canh những chỗ KHÔNG được làm, vì suy tự động sai thì hậu
quả không nhìn thấy được: một người mang pháp nhân sai vẫn dùng hệ thống bình thường, chỉ có báo cáo
của hai công ty là lệch, và lệch âm thầm.
"""
import os, sys

os.environ["DATABASE_URL"] = "sqlite:///./test_suy_phapnhan.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_suy_phapnhan.db", "test_suy_phapnhan.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, Company
from app.models.hr import Employee
from app.services import suy_phap_nhan as SPN

client = TestClient(app)
MK = "suyphapnhan123"
ID = {}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.core.security import hash_password
        db = _db()
        for ma, ten in (("SPN_A", "Công ty A"), ("SPN_B", "Công ty B")):
            if db.execute(select(Company).where(Company.code == ma)).scalars().first() is None:
                db.add(Company(code=ma, name=ten, kind="con"))
        db.commit()
        ID["A"] = db.execute(select(Company).where(Company.code == "SPN_A")).scalars().first().id
        ID["B"] = db.execute(select(Company).where(Company.code == "SPN_B")).scalars().first().id

        def tk(un, vai="nv_dh", ma="", cid=None):
            u = db.execute(select(User).where(User.username == un)).scalars().first()
            if u is None:
                u = User(username=un, full_name=f"Thử {un}", role=vai, department="Kiểm thử",
                         staff_code=ma, password_hash=hash_password(MK), active=True, company_id=cid)
                db.add(u); db.commit(); db.refresh(u)
            ID[un] = u.id
            return u

        def hs(ma, u=None, cid=None, active=True):
            e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
            if e is None:
                e = Employee(code=ma, full_name=f"HS {ma}", department="Kiểm thử")
                db.add(e)
            e.user_id = u.id if u else None
            e.company_id = cid
            e.active = active
            db.commit()
            return e

        # 1. nối bằng user_id, hồ sơ có pháp nhân → SUY ĐƯỢC
        hs("SPN01", tk("spn_uid"), ID["A"])
        # 2. nối bằng MÃ NHÂN VIÊN (hồ sơ chưa gắn user_id) → SUY ĐƯỢC
        tk("spn_ma", ma="SPN02"); hs("SPN02", None, ID["B"])
        # 3. hồ sơ chưa có pháp nhân → KHÔNG suy được, phải nói rõ vì sao
        hs("SPN03", tk("spn_hs_trong"), None)
        # 4. không có hồ sơ nào → KHÔNG suy được
        tk("spn_khong_ho_so")
        # 5. hồ sơ ĐÃ NGHỈ, có pháp nhân → KHÔNG suy: quan hệ đã chấm dứt
        hs("SPN05", tk("spn_ho_so_nghi"), ID["A"], active=False)
        # 6. tài khoản ĐÃ CÓ pháp nhân B, hồ sơ nói A → LỆCH, báo ra chứ không tự sửa
        hs("SPN06", tk("spn_lech", cid=ID["B"]), ID["A"])
        # 7. người bấm nút
        tk("spn_cntt", "cntt")
        tk("spn_bks", "bks")
        db.close()
        yield


def login(un):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def nhom(kq, ten):
    return {d["username"]: d for d in kq[ten]}


# ---------------- Suy đúng cái suy được ----------------
def test_suy_duoc_khi_noi_bang_user_id():
    kq = SPN.xem_truoc(_db())
    d = nhom(kq, "suy_duoc")["spn_uid"]
    assert d["company_id"] == ID["A"] and d["noi_bang"] == "user_id"


def test_suy_duoc_khi_chi_noi_duoc_bang_ma_nhan_vien():
    """Hai đường nối lệch nhau ở vài tài khoản là chuyện có thật, nên phải nối được cả hai đường –
    và theo đúng thứ tự mà phần còn lại của hệ thống đang dùng: user_id trước, mã sau."""
    d = nhom(SPN.xem_truoc(_db()), "suy_duoc")["spn_ma"]
    assert d["company_id"] == ID["B"] and d["noi_bang"] == "ma_nhan_vien"


# ---------------- Bốn chỗ KHÔNG được làm ----------------
def test_khong_doan_khi_ho_so_chua_co_phap_nhan():
    """Suy từ phòng ban hay mặc định về công ty mẹ là cách một khoản của công ty này chạy sang báo
    cáo của công ty kia mà không ai thấy."""
    kq = SPN.xem_truoc(_db())
    assert "spn_hs_trong" not in nhom(kq, "suy_duoc")
    d = nhom(kq, "khong_suy_duoc")["spn_hs_trong"]
    assert "SPN03" in d["ly_do"] and "chưa có pháp nhân" in d["ly_do"]


def test_khong_doan_khi_khong_co_ho_so():
    kq = SPN.xem_truoc(_db())
    d = nhom(kq, "khong_suy_duoc")["spn_khong_ho_so"]
    assert "không nối được" in d["ly_do"]


def test_khong_suy_tu_ho_so_da_nghi():
    """Hồ sơ đã nghỉ vẫn giữ pháp nhân cũ; suy từ nó là gán theo một quan hệ đã chấm dứt."""
    kq = SPN.xem_truoc(_db())
    assert "spn_ho_so_nghi" not in nhom(kq, "suy_duoc")
    assert "spn_ho_so_nghi" in nhom(kq, "khong_suy_duoc")


def test_lech_thi_bao_ra_chu_khong_tu_sua():
    """Gán tay là quyết định của con người; suy tự động là phỏng theo dữ liệu. Cái sau không được ghi
    đè cái trước – nhưng cũng không được im lặng bỏ qua."""
    kq = SPN.xem_truoc(_db())
    d = nhom(kq, "lech_voi_ho_so")["spn_lech"]
    assert d["company_id"] == ID["B"] and d["ho_so_company"] == "SPN_A"
    assert "spn_lech" not in nhom(kq, "suy_duoc")


def test_ghi_xong_khong_dung_toi_tai_khoan_da_co_phap_nhan():
    db = _db()
    truoc = db.get(User, ID["spn_lech"]).company_id
    db.close()
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_cntt"))
    db = _db(); sau = db.get(User, ID["spn_lech"]).company_id; db.close()
    assert sau == truoc == ID["B"], "suy tự động đã ghi đè một giá trị gán tay"


# ---------------- Xem trước rồi mới ghi ----------------
def test_xem_truoc_khong_ghi_gi():
    db = _db()
    truoc = {u.id: u.company_id for u in db.execute(select(User)).scalars()}
    db.close()
    client.get("/api/v1/access/phap-nhan/suy-tu-ho-so", headers=login("spn_bks"))
    db = _db()
    sau = {u.id: u.company_id for u in db.execute(select(User)).scalars()}
    db.close()
    assert truoc == sau, "bảng xem trước đã ghi vào cơ sở dữ liệu"


def test_chay_lai_lan_hai_khong_ghi_them_gi():
    """Bấm hai lần là chuyện sẽ xảy ra. Lần hai phải không còn gì để ghi, chứ không phải ghi lại."""
    h = login("spn_cntt")
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=h)
    r2 = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=h)
    assert r2.json()["da_ghi"] == 0


def test_ghi_duoc_cho_rieng_may_tai_khoan_da_chon():
    """Người quản trị bỏ tick vài dòng ở bảng xem trước thì chỉ những dòng còn lại được ghi."""
    db = _db()
    u = db.get(User, ID["spn_uid"]); u.company_id = None
    v = db.get(User, ID["spn_ma"]); v.company_id = None
    db.commit(); db.close()
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so",
                    json={"user_ids": [ID["spn_uid"]]}, headers=login("spn_cntt"))
    assert r.json()["da_ghi"] == 1
    db = _db()
    assert db.get(User, ID["spn_uid"]).company_id == ID["A"]
    assert db.get(User, ID["spn_ma"]).company_id is None, "ghi cả dòng không được chọn"
    db.close()


# ---------------- Ai được xem, ai được ghi ----------------
def test_xem_duoc_ma_khong_can_quyen_ghi():
    """Ban Kiểm soát phải đối chiếu được bảng này mà không cần quyền ghi vào bảng tài khoản."""
    r = client.get("/api/v1/access/phap-nhan/suy-tu-ho-so", headers=login("spn_bks"))
    assert r.status_code == 200, r.text


def test_khong_phai_ai_cung_ghi_duoc():
    """Cùng bộ vai trò với gán lẻ. Rộng hơn thì hàng loạt thành đường vòng của lẻ."""
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_uid"))
    assert r.status_code == 403


def test_ban_kiem_soat_khong_ghi_duoc():
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_bks"))
    assert r.status_code == 403, "vai trò chỉ đọc ghi được vào bảng tài khoản"


# ---------------- Có dấu vết ----------------
def test_moi_lan_ghi_deu_de_lai_nhat_ky():
    db = _db()
    for un in ("spn_uid", "spn_ma"):
        x = db.get(User, ID[un]); x.company_id = None
    db.commit(); db.close()
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_cntt"))
    r = client.get("/api/v1/access/audit?limit=50", headers=login("spn_cntt"))
    assert r.status_code == 200, r.text
    rows = r.json()["rows"] if isinstance(r.json(), dict) else r.json()
    assert any("suy_phap_nhan_tai_khoan_tu_ho_so" in str(x) for x in rows), \
        "gán pháp nhân hàng loạt mà không có dòng nhật ký nào"
