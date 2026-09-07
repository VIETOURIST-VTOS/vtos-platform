"""Robot giữ vị trí ở từng phòng ban và mở thử mọi màn hình của mình.

VTOS đang xây, chưa vận hành, và chỉ một người thử – nên lỗi của một phòng ban chỉ lộ ra khi đúng
người của phòng đó đăng nhập. Tệp này thay cho việc đó: với MỖI vai trò, robot đăng nhập rồi gọi mọi
đường dẫn GET của hệ thống, và ghi lại kết quả.

Chỉ có MỘT điều được coi là lỗi phải chặn: máy chủ trả 5xx. 403 không phải lỗi – đó là ma trận phân
quyền đang làm đúng việc của nó, và bảng in ra cuối bài cho thấy mỗi phòng mở được bao nhiêu cửa.

Robot dùng tài khoản TẠO RIÊNG cho việc thử (robot_<vai_tro>), không mượn mật khẩu của nhân viên: mượn
tài khoản người thật thì nhật ký đăng nhập ghi tên họ vào lúc họ không hề đăng nhập.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_robot_vai_tro.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_robot_vai_tro.db", "test_robot_vai_tro.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.core import ROLES

client = TestClient(app)
MAT_KHAU = "robot123456"

# Đường dẫn robot KHÔNG gọi: đổi dữ liệu ngoài, tốn tiền, hoặc kéo hệ thống bên thứ ba.
BO_QUA = ("/api/v1/health", "/api/v1/auth/logout", "/api/v1/sepay", "/api/v1/vietrip/dong-bo",
          "/api/v1/facebook", "/api/v1/zalo", "/api/v1/robot/")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        _tao_tai_khoan_robot()
        yield


def _tao_tai_khoan_robot():
    from app.db.session import SessionLocal
    from app.core.security import hash_password
    from app.models.core import User
    from sqlalchemy import select
    db = SessionLocal()
    for vai in ROLES:
        un = f"robot_{vai}"
        u = db.execute(select(User).where(User.username == un)).scalars().first()
        if u is None:
            db.add(User(username=un, full_name=f"Robot thử vai trò {ROLES[vai]}", role=vai,
                        department="Kiểm thử", password_hash=hash_password(MAT_KHAU), active=True))
    db.commit(); db.close()


def duong_dan_get() -> list[str]:
    ra = []
    for r in app.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/api/v1") or "{" in p: continue
        if "GET" not in (getattr(r, "methods", None) or set()): continue
        if any(p.startswith(b) for b in BO_QUA): continue
        ra.append(p)
    return sorted(set(ra))


def dang_nhap(vai: str):
    r = client.post("/api/v1/auth/login", data={"username": f"robot_{vai}", "password": MAT_KHAU})
    assert r.status_code == 200, f"{vai}: không đăng nhập được – {r.text[:200]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_moi_vai_tro_deu_dang_nhap_duoc():
    for vai in ROLES:
        dang_nhap(vai)


def test_khong_mot_man_hinh_nao_lam_may_chu_no():
    """Phép thử duy nhất được phép đỏ ở đây: 5xx. Một phòng ban mở màn hình của mình ra mà gặp lỗi máy
    chủ thì đó là lỗi của mình, không phải của họ."""
    eps = duong_dan_get()
    assert len(eps) > 50, f"chỉ tìm thấy {len(eps)} đường dẫn – bộ dò đường dẫn hỏng"
    no = []
    bang = {}
    for vai in ROLES:
        h = dang_nhap(vai)
        mo = cam = 0
        for e in eps:
            r = client.get(e, headers=h)
            if r.status_code >= 500:
                no.append(f"{vai} → {e} = {r.status_code} :: {r.text[:160]}")
            elif r.status_code == 403: cam += 1
            elif r.status_code < 400: mo += 1
        bang[vai] = (mo, cam)

    print("\n--- Robot giữ vị trí từng phòng ban, mở thử " + str(len(eps)) + " đường dẫn ---")
    for vai, (mo, cam) in sorted(bang.items(), key=lambda x: -x[1][0]):
        print(f"  {ROLES[vai]:<32} mở được {mo:>3}   bị chặn {cam:>3}")
    assert not no, "Máy chủ nổ ở các chỗ sau:\n" + "\n".join(no[:40])


def test_moi_vai_tro_deu_mo_duoc_it_nhat_mot_man_hinh():
    """Một vai trò không mở được cửa nào là vai trò không dùng được – người đó đăng nhập vào và nhìn
    thấy một hệ thống trống."""
    eps = duong_dan_get()
    trong = []
    for vai in ROLES:
        h = dang_nhap(vai)
        if not any(client.get(e, headers=h).status_code < 400 for e in eps):
            trong.append(vai)
    assert not trong, f"Các vai trò đăng nhập vào nhưng không mở được gì: {trong}"


# Màn hình tiền và nhật ký: ẩn khỏi menu PHẢI đồng nghĩa với chặn ở API. Với những màn hình khác, ẩn menu
# mà API còn mở là chuyện có thể bàn; với năm nhóm dưới đây thì không – ẩn khỏi mắt mà vẫn đọc được bằng
# đường dẫn trực tiếp là không chặn gì cả.
CUA_TIEN = {
    "/bank-accounts": "/api/v1/bank-accounts",
    "/finance": "/api/v1/finance",
    "/accounting": "/api/v1/accounting",
    "/audit": "/api/v1/audit",
}


def test_man_hinh_tien_an_khoi_menu_thi_api_cung_phai_dong():
    from app.services.access import MENU_ROLES
    eps = duong_dan_get()
    ro = []
    for vai in ROLES:
        h = dang_nhap(vai)
        for man, pre in CUA_TIEN.items():
            if vai in MENU_ROLES.get(man, ()): continue
            for e in [x for x in eps if x.startswith(pre)]:
                r = client.get(e, headers=h)
                if r.status_code < 400:
                    ro.append(f"{ROLES[vai]} không thấy {man} trên menu nhưng GET {e} = {r.status_code}")
    assert not ro, "Menu ẩn nhưng API vẫn mở:\n" + "\n".join(ro[:30])
