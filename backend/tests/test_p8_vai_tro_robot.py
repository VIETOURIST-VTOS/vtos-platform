"""P8 – ba robot có vai trò riêng, và hai điều cấm phải đứng được.

Vấn đề trước bản này KHÔNG nằm ở quyền mà nằm ở NHẬT KÝ. Robot Kiểm soát mượn vai trò bks, robot Phân
quyền và robot Viết phần mềm mượn vai trò cntt. Nên mọi việc ba robot làm đều mang tên một con người:
khi cần biết ai đã đổi cái gì thì câu trả lời là "cntt" – đúng và vô dụng. Người vận hành bị ghi tên
cho việc mình không làm, còn robot thì không truy được.

Hai điều cấm trong lệnh giao việc, và đây là hai phép thử quan trọng nhất tệp này:

  · robot Viết phần mềm KHÔNG đóng được ngoại lệ. Người viết phần mềm mà đóng được việc do chính mình
    gây ra thì lớp kiểm soát chỉ còn là hình thức – mọi phát hiện đều biến mất bằng một lần bấm của
    chính người bị phát hiện.

  · robot Phân quyền KHÔNG ghi được số nghiệp vụ. Robot cầm chìa khoá quyền mà ghi được số tiền thì
    nó vừa mở cửa vừa đi qua cửa, và không còn ai đứng ngoài để đối chiếu.

Cả hai điều cấm được canh ở HAI LỚP, vì mỗi lớp hỏng theo một kiểu khác nhau: hàng rào tiền tố (nới
nhầm một dòng trong bảng phạm vi) và chữ ký từng đường dẫn (thêm vai trò vào một require_roles cho
tiện). Phép thử chạm cả hai.
"""
import os, sys

os.environ["DATABASE_URL"] = "sqlite:///./test_p8_robot.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p8_robot.db", "test_p8_robot.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, ROLES, AuditLog
from app.services import access as AC

client = TestClient(app)
MK = "robot123456"

# Cửa GHI SỐ NGHIỆP VỤ – không robot nào được đi qua, dù robot nào.
CUA_GHI_SO = [
    ("POST", "/api/v1/tours", {"code": "X", "name": "X", "tour_type": "package",
                               "start_date": "2026-10-01", "end_date": "2026-10-02"}),
    ("POST", "/api/v1/requests", {"customer_name": "X", "customer_phone": "0900000000", "pax": 1}),
    ("POST", "/api/v1/requests/1/booking", None),
    ("POST", "/api/v1/journal", {"entry_date": "2026-10-01", "description": "X", "lines": []}),
    ("POST", "/api/v1/payment-requests", {"category": "khac", "supplier_name": "X",
                                          "amount": 1000, "description": "X"}),
]


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in AC.VAI_TRO_MAY:
            if db.execute(select(User).where(User.username == vai)).scalars().first() is None:
                db.add(User(username=vai, full_name=ROLES[vai], role=vai, department="",
                            password_hash=hash_password(MK), active=True))
        if db.execute(select(User).where(User.username == "p8_cntt")).scalars().first() is None:
            db.add(User(username="p8_cntt", full_name="Người vận hành", role="cntt", department="CNTT",
                        password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(un):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def goi(method, path, headers, json=None):
    return client.request(method, path, headers=headers, json=json)


# ---------------- Điều cấm 1: robot Viết phần mềm không đóng được ngoại lệ ----------------
def test_robot_viet_phan_mem_khong_dong_duoc_ngoai_le():
    h = login("robot_vpm")
    for path, body in (("/api/v1/ngoai-le/dong", {"ma": "X", "ket_luan": "xong"}),
                       ("/api/v1/ngoai-le/mo-lai", {"ma": "X", "ly_do": "x"}),
                       ("/api/v1/ngoai-le/ghi", {"ma": "X", "giai_trinh": "x", "da_lam": "x",
                                                 "nguoi_chiu_trach_nhiem": "x"}),
                       ("/api/v1/ngoai-le/nhan", {"ma": "X"})):
        r = client.post(path, json=body, headers=h)
        assert r.status_code == 403, f"robot Viết phần mềm đi qua được {path}: {r.status_code}"


def test_robot_viet_phan_mem_khong_doc_duoc_ca_danh_sach_ngoai_le():
    """Chặn cửa đóng mà để mở cửa đọc thì vẫn còn một nửa vấn đề: biết chính xác phát hiện nào đang
    chỉ vào mình là biết chính xác phải đi thuyết phục ai."""
    r = client.get("/api/v1/ngoai-le", headers=login("robot_vpm"))
    assert r.status_code == 403, f"robot Viết phần mềm đọc được danh sách ngoại lệ: {r.status_code}"


def test_tien_to_ngoai_le_khong_nam_trong_pham_vi_robot_viet_phan_mem():
    """Lớp thứ hai: hàng rào tiền tố. Nới ở đây mà quên chữ ký đường dẫn là mở lại đúng cửa vừa khoá."""
    assert not any(p.startswith("/api/v1/ngoai-le") for p in AC.pham_vi_day_du("robot_vpm"))


# ---------------- Điều cấm 2: robot Phân quyền không ghi số nghiệp vụ ----------------
def test_robot_phan_quyen_khong_ghi_duoc_so_nghiep_vu():
    h = login("robot_pq")
    for method, path, body in CUA_GHI_SO:
        r = goi(method, path, h, body)
        assert r.status_code == 403, f"robot Phân quyền ghi được {path}: {r.status_code}"


def test_khong_robot_nao_ghi_duoc_so_nghiep_vu():
    """Điều cấm viết cho robot Phân quyền, nhưng nó đúng với cả ba: không robot nào ghi số vào sổ."""
    for vai in AC.VAI_TRO_MAY:
        h = login(vai)
        for method, path, body in CUA_GHI_SO:
            r = goi(method, path, h, body)
            assert r.status_code == 403, f"{vai} ghi được {path}: {r.status_code}"


def test_doc_danh_sach_nghiep_vu_cung_bi_chan_chu_khong_chi_ghi():
    """Bản nháp của tệp này gọi POST vào một đường dẫn KHÔNG TỒN TẠI và nhận 405, suýt đọc thành
    "đã bị chặn". 405 là bộ định tuyến trả lời, hàng rào quyền chưa chạy tới. Nên canh thêm bằng GET
    – đường dẫn chắc chắn có thật – để phép thử nói về hàng rào chứ không nói về bảng định tuyến."""
    for vai in ("robot_pq", "robot_vpm"):
        h = login(vai)
        for path in ("/api/v1/tours", "/api/v1/bookings", "/api/v1/journal", "/api/v1/payment-requests"):
            r = client.get(path, headers=h)
            assert r.status_code == 403, f"{vai} đọc được {path}: {r.status_code}"


def test_robot_phan_quyen_khong_tu_sua_duoc_quyen():
    """Robot đề xuất, người quyết. Robot cầm chìa khoá quyền mà tự đổi được vai trò thì nó tự cấp cho
    mình bất cứ thứ gì, và không lần đổi nào cần ai đồng ý."""
    h = login("robot_pq")
    db_u = client.get("/api/v1/access/accounts", headers=h)
    assert db_u.status_code == 200, "robot Phân quyền phải ĐỌC được bàn làm việc của mình"
    uid = db_u.json()["rows"][0]["id"]
    for path, body in ((f"/api/v1/access/role-change/{uid}", {"role": "chutich", "ly_do": "x"}),
                       (f"/api/v1/access/users/{uid}/company", {"company_id": None})):
        r = client.request("PUT" if "company" in path else "POST", path, json=body, headers=h)
        assert r.status_code == 403, f"robot Phân quyền tự sửa được quyền qua {path}: {r.status_code}"


def test_robot_kiem_soat_doc_duoc_moi_thu_nhung_khong_ghi_duoc_gi():
    """Quyết định 09/9/2026: robot làm việc Ban Kiểm soát thì phải nhìn được thứ BKS nhìn.

    Điều cấm của nó vì thế đổi KIỂU chứ không đổi mức chặt: không còn là "không được chạm tiền tố nào"
    mà là "KHÔNG ĐƯỢC GHI GÌ CẢ" – rộng hơn và chặt hơn. Đọc bảng phân quyền là việc của người đi rà
    quyền; SỬA bảng phân quyền thì không, kể cả với robot đi soi người khác.
    """
    h = login("robot_ks")
    assert client.get("/api/v1/access/accounts", headers=h).status_code == 200, \
        "robot Kiểm soát không đọc được bảng phân quyền thì rà quyền bằng gì"
    for method, path, body in (
            ("POST", "/api/v1/access/role-change/1", {"role": "chutich", "ly_do": "x"}),
            ("PUT", "/api/v1/access/users/1/company", {"company_id": None}),
            ("POST", "/api/v1/params", {"key": "x", "value": "1"}),
            ("POST", "/api/v1/ngoai-le/dong", {"ma": "X", "ket_luan": "xong"})):
        r = client.request(method, path, json=body, headers=h)
        assert r.status_code == 403, f"robot Kiểm soát GHI được {method} {path}: {r.status_code}"


def test_robot_kiem_soat_bi_chan_ghi_o_lop_chung_chu_khong_tung_cua():
    """Hàng rào thật của robot_ks là READ_ONLY_ROLES – một lớp chặn MỌI phương thức ghi, không phải
    một danh sách cửa phải nhớ liệt kê. Danh sách cửa thì luôn thiếu đúng cái cửa vừa thêm hôm qua."""
    assert "robot_ks" in AC.READ_ONLY_ROLES
    assert "robot_ks" in AC.BASE_VIEW, "đọc toàn bộ như BKS thì phải nằm trong nền của mọi dòng ma trận"
    assert len(AC.pham_vi_day_du("robot_ks")) == len(AC.pham_vi_day_du("bks")), \
        "robot Kiểm soát phải nhìn đúng bằng Ban Kiểm soát, không hơn không kém"


# ---------------- Bảng điều cấm phải khớp hàng rào thật ----------------
def test_bang_dieu_cam_khop_voi_hang_rao_that():
    """CAM_CUA_ROBOT là lời tuyên bố; phạm vi là thứ thi hành. Hai cái lệch nhau thì lời tuyên bố trở
    thành thứ người đọc tin mà hệ thống không làm."""
    for vai, cam in AC.CAM_CUA_ROBOT.items():
        cho = AC.pham_vi_day_du(vai)
        for tien_to, ly_do in cam.items():
            assert not any(p.startswith(tien_to) or tien_to.startswith(p) for p in cho), \
                f"{vai} bị cấm {tien_to} nhưng phạm vi vẫn cho vào – {ly_do}"
            assert len(ly_do) > 30, f"{vai}/{tien_to}: điều cấm không ghi đủ lý do"


def test_khong_robot_nao_co_toan_quyen():
    """KHÔNG robot nào có FULL_ACCESS – đó là quyền đi qua mọi hàng rào, và nó chỉ dành cho Chủ tịch.

    robot_ks nằm trong BASE_VIEW từ 09/9/2026 (đọc toàn bộ như BKS) nhưng đó là quyền ĐỌC, chặn ghi
    vẫn nguyên. Hai robot kia không có cả hai."""
    from app.api.deps import FULL_ACCESS
    for vai in AC.VAI_TRO_MAY:
        assert vai not in FULL_ACCESS, f"{vai} có toàn quyền – đi qua được mọi hàng rào"
    for vai in ("robot_pq", "robot_vpm"):
        assert vai not in AC.BASE_VIEW, f"{vai} nằm trong nền BASE_VIEW – thấy mọi màn hình"
        assert vai not in AC.AUDIT_ROLES, f"{vai} đọc được nhật ký kiểm toán"


# ---------------- Mỗi robot vẫn làm được việc của mình ----------------
def test_robot_kiem_soat_van_chay_duoc_vong_quet():
    """Siết quyền dễ đúng về nguyên tắc mà sai về hậu quả. Robot Kiểm soát mất quyền quét là bộ kiểm
    của cả hệ thống đứng lại."""
    r = client.post("/api/v1/kiem-soat/quet", headers=login("robot_ks"))
    assert r.status_code == 200, r.text


def test_ba_robot_deu_doc_duoc_ban_lam_viec_kiem_soat():
    """Bàn Kiểm soát là nơi việc được giao cho từng robot – đọc không được thì không nhận được việc."""
    for vai in AC.VAI_TRO_MAY:
        r = client.get("/api/v1/kiem-soat", headers=login(vai))
        assert r.status_code == 200, f"{vai} không đọc được bàn làm việc: {r.status_code}"


def test_chi_robot_kiem_soat_duoc_cham_diem():
    """Hai robot kia đọc việc của mình chứ không tự chấm điểm cho mình – đó là toàn bộ lý do vị trí
    Kiểm soát tách khỏi hai vị trí kia."""
    for vai in ("robot_pq", "robot_vpm"):
        r = client.post("/api/v1/kiem-soat/quet", headers=login(vai))
        assert r.status_code == 403, f"{vai} tự chạy được vòng quét: {r.status_code}"


# ---------------- Điều kiện nghiệm thu: nhật ký phân biệt được ba robot ----------------
def test_nhat_ky_phan_biet_duoc_ba_robot():
    """Điều kiện nghiệm thu của P8. Trước bản này cả ba đều ghi tên 'cntt'."""
    from app.db.session import SessionLocal
    for vai in AC.VAI_TRO_MAY:
        login(vai)          # đăng nhập là một hành động có ghi nhật ký
    db = SessionLocal()
    ten = {r.actor: r.role for r in db.execute(
        select(AuditLog).where(AuditLog.action == "dang_nhap").order_by(AuditLog.id.desc()).limit(30)).scalars()}
    db.close()
    for vai in AC.VAI_TRO_MAY:
        assert ten.get(vai) == vai, f"nhật ký không phân biệt được {vai}: {ten}"
    assert len({v for v in ten.values() if v in AC.VAI_TRO_MAY}) == 3, \
        "ba robot không để lại ba vai trò khác nhau trong nhật ký"


def test_vai_tro_may_khong_lan_vao_bo_kiem_cua_nguoi():
    from app.db.session import SessionLocal
    from app.services import ks_robot as KS
    db = SessionLocal()
    thieu_nguoi = {x["vai_tro"] for x in KS._vai_tro_khong_co_nguoi(db)}
    db.close()
    assert not (thieu_nguoi & set(AC.VAI_TRO_MAY))
