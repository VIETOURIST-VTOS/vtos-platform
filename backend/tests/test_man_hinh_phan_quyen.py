"""Màn hình Tài khoản & phân quyền – API (đặc tả 07/9/2026, phần B).

Ba điều được chốt ở đây:
  1. Màn hình CÔNG BỐ ma trận, không sửa nó. Bản công bố phải khớp từng ô với nguồn quyền trong mã –
     nếu lệch, người đọc tin bảng chứ không tin hệ thống, và rà quyền hằng tháng trở thành nghi thức.
  2. Đổi sang ba vai trò nhìn được toàn bộ tiền và sổ sách phải do Chủ tịch hoặc TGĐ. Quyền đó tương
     đương quyền ký; một người ở HCNS hay CNTT không nên tự trao được cho ai.
  3. Mọi thao tác đều bắt buộc có lý do bằng lời và để lại vết trong nhật ký bất biến.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_man_hinh_quyen.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Xóa cả tệp nhật ký đi kèm: sqlite để lại "<tên>.db-journal" khi tiến trình trước kết thúc giữa chừng,
# và nếu chỉ xóa tệp .db thì lần chạy sau nạp lại trạng thái cũ và đỏ một cách khó hiểu.
for _f in ("test_man_hinh_quyen.db", "test_man_hinh_quyen.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import access as AC
from app.models.core import ROLES

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def login(u, pw="123456"):
    r = client.post("/api/v1/auth/login", data={"username": u, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def tk(role):
    from app.db.session import SessionLocal
    from sqlalchemy import select
    from app.models.core import User
    db = SessionLocal()
    u = db.execute(select(User).where(User.role == role, User.active == True)).scalars().first()
    ra = (u.id, u.username) if u else (None, None)
    db.close(); return ra


# ---------- quyền vào màn hình ----------
def test_chi_nam_vai_tro_mo_duoc_man_hinh():
    assert set(AC.MENU_ROLES["/access"]) == set(AC.BASE_VIEW) | {"hcns", "cntt"}
    for vai in ("nv_kd", "tp_dh", "ketoan", "nv_dh"):
        _, un = tk(vai)
        if not un: continue
        assert client.get("/api/v1/access/accounts", headers=login(un)).status_code == 403, f"{vai} không được vào"


def test_ban_kiem_soat_xem_duoc_nhung_khong_thao_tac():
    _, bks = tk("bks")
    if not bks: pytest.skip("không có tài khoản Ban Kiểm soát")
    h = login(bks)
    assert client.get("/api/v1/access/accounts", headers=h).status_code == 200
    assert client.get("/api/v1/access/matrix", headers=h).status_code == 200
    uid, _ = tk("nv_kd")
    r = client.post(f"/api/v1/access/role-change/{uid}", headers=h, json={"role": "nv_dh", "reason": "thử"})
    assert r.status_code == 403, "Ban Kiểm soát chỉ đọc – mọi thao tác ghi phải bị chặn"


# ---------- bản công bố phải khớp nguồn quyền ----------
def test_ma_tran_cong_bo_khop_tung_o_voi_ma_nguon():
    _, cntt = tk("cntt")
    mt = client.get("/api/v1/access/matrix", headers=login(cntt)).json()
    assert set(mt["man_hinh"]) == set(AC.MENU_ROLES), "danh sách màn hình công bố lệch với ma trận thật"
    assert len(mt["rows"]) == len(ROLES)
    for row in mt["rows"]:
        vai = row["vai_tro"]
        that = (set(AC.RESTRICTED_ROLE_MENUS[vai]) if vai in AC.RESTRICTED_ROLE_MENUS
                else {p for p, v in AC.MENU_ROLES.items() if vai in v})
        for p in mt["man_hinh"]:
            assert row["man_hinh"][p] == (p in that), f"ô lệch: {vai} × {p}"


def test_ma_tran_danh_dau_dung_ba_vai_tro_dac_biet():
    _, cntt = tk("cntt")
    mt = client.get("/api/v1/access/matrix", headers=login(cntt)).json()
    tq = {r["vai_tro"] for r in mt["rows"] if r["toan_quyen"]}
    cd = {r["vai_tro"] for r in mt["rows"] if r["chi_doc"]}
    assert tq == {"chutich", "tgd"} and cd == {"bks"}


def test_xuat_excel_ma_tran_ra_tep_that():
    _, cntt = tk("cntt")
    r = client.get("/api/v1/access/matrix.xlsx", headers=login(cntt))
    assert r.status_code == 200 and r.content[:2] == b"PK", "phải là tệp xlsx thật, không phải trang lỗi"
    assert "attachment" in r.headers.get("content-disposition", "")


# ---------- đổi vai trò ----------
def test_doi_sang_vai_tro_nhay_cam_phai_do_lanh_dao():
    uid, _ = tk("nv_kd")
    _, hcns = tk("hcns")
    r = client.post(f"/api/v1/access/role-change/{uid}", headers=login(hcns),
                    json={"role": "ketoan", "reason": "thử"})
    assert r.status_code == 403, "HCNS không được tự trao vai trò nhìn toàn bộ tiền"
    r2 = client.post(f"/api/v1/access/role-change/{uid}", headers=login("chutich"),
                     json={"role": "ketoan", "reason": "bổ sung nhân sự kế toán"})
    assert r2.status_code == 200, r2.text
    # trả lại như cũ để không ảnh hưởng phép thử khác
    client.post(f"/api/v1/access/role-change/{uid}", headers=login("chutich"),
                json={"role": "nv_kd", "reason": "hoàn nguyên sau kiểm thử"})


def test_doi_vai_tro_bat_buoc_co_ly_do():
    uid, _ = tk("nv_mkt")
    if not uid: pytest.skip("không có tài khoản marketing")
    _, hcns = tk("hcns")
    r = client.post(f"/api/v1/access/role-change/{uid}", headers=login(hcns), json={"role": "nv_kd", "reason": "   "})
    assert r.status_code == 422


def test_khong_tu_doi_vai_tro_cua_chinh_minh():
    uid, hcns = tk("hcns")
    r = client.post(f"/api/v1/access/role-change/{uid}", headers=login(hcns), json={"role": "cntt", "reason": "thử"})
    assert r.status_code in (403, 422)


def test_doi_vai_tro_de_lai_vet_trong_nhat_ky():
    uid, _ = tk("nv_mkt")
    if not uid: pytest.skip("không có tài khoản marketing")
    _, hcns = tk("hcns")
    h = login(hcns)
    assert client.post(f"/api/v1/access/role-change/{uid}", headers=h,
                       json={"role": "nv_kd", "reason": "chuyển sang phòng kinh doanh"}).status_code == 200
    log = client.get("/api/v1/access/audit", headers=h).json()["rows"]
    dong = [r for r in log if r["action"] == "sua_tai_khoan"]
    assert dong and "ly_do" in (dong[0]["after"] or {}), "nhật ký phải giữ lại lý do bằng lời"
    client.post(f"/api/v1/access/role-change/{uid}", headers=h, json={"role": "nv_mkt", "reason": "hoàn nguyên"})


# ---------- đối chiếu ----------
def test_sau_danh_sach_doi_chieu_deu_co_mat():
    _, cntt = tk("cntt")
    g = client.get("/api/v1/access/gaps", headers=login(cntt)).json()
    for k in ("nhan_su_chua_co_tai_khoan", "tai_khoan_bo_quen", "con_mat_khau_tam",
              "bo_hoang", "chua_gan_phap_nhan", "ho_so_trung"):
        assert k in g["danh_sach"] and k in g["dem"]
    assert g["tong"] == sum(g["dem"].values())


def test_tai_khoan_ngoai_bien_che_khong_bi_bao_lech():
    """Kế toán trưởng thuê ngoài có tài khoản nhưng không có trong bảng lương – đánh dấu là hết báo lệch."""
    uid, un = tk("nv_kd")
    _, cntt = tk("cntt")
    h = login(cntt)
    truoc = client.get("/api/v1/access/gaps", headers=h).json()["dem"]["tai_khoan_bo_quen"]
    assert client.put(f"/api/v1/access/users/{uid}/bien-che", headers=h, json={"ngoai_bien_che": True}).status_code == 200
    sau = client.get("/api/v1/access/gaps", headers=h).json()["dem"]["tai_khoan_bo_quen"]
    assert sau <= truoc
    client.put(f"/api/v1/access/users/{uid}/bien-che", headers=h, json={"ngoai_bien_che": False})


def test_gan_phap_nhan_va_bo_trong_deu_duoc():
    uid, _ = tk("nv_kd")
    _, cntt = tk("cntt")
    h = login(cntt)
    cos = client.get("/api/v1/access/accounts", headers=h).json()["companies"]
    if not cos: pytest.skip("chưa có danh mục pháp nhân")
    assert client.put(f"/api/v1/access/users/{uid}/company", headers=h, json={"company_id": cos[0]["id"]}).status_code == 200
    # để trống là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ
    assert client.put(f"/api/v1/access/users/{uid}/company", headers=h, json={"company_id": None}).status_code == 200
    r = [x for x in client.get("/api/v1/access/accounts", headers=h).json()["rows"] if x["id"] == uid][0]
    assert r["company_id"] is None


def test_phap_nhan_khong_co_trong_danh_muc_bi_chan():
    uid, _ = tk("nv_kd")
    _, cntt = tk("cntt")
    assert client.put(f"/api/v1/access/users/{uid}/company", headers=login(cntt),
                      json={"company_id": 999999}).status_code == 422
