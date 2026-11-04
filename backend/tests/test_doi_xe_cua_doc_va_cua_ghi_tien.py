"""Ma trận kiểm soát đội xe: cửa ĐỌC phải khớp ma trận màn hình, cửa GHI TIỀN phải có người canh.

Hai lỗ hổng đo được ngày 03/11/2026:

  1. `GET /fleet/hieu-qua` dùng nhóm `READ` (10 vai trò), trong khi `MENU_ROLES["/hieu-qua-doi-xe"]`
     chỉ mở cho 8 và `test_ma_tran_quyen.py` khẳng định CNTT không xem được. Phép thử ấy vẫn XANH vì nó
     chỉ kiểm MENU. Giấu màn hình khỏi menu không phải là đóng cửa – ai gọi thẳng API vẫn lấy được số.

  2. Khoảng 57/69 cửa đội xe không có một phép thử quyền nào, trong đó có xóa dòng chi phí, xóa khoản
     chi phí kỳ, thanh toán công nợ, nạp chuyến hàng loạt. Các bộ thử hiện có gọi chúng bằng token
     `cntt`/`ketoan` và kiểm NGHIỆP VỤ, không kiểm AI BỊ TỪ CHỐI.

Bộ này đóng cả hai. Nó cố ý KHÔNG chép danh sách vai trò ra đây mà đối chiếu thẳng với ma trận – chép
là để hai nơi trôi khỏi nhau lần nữa.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe_cua.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe_cua.db"): os.remove("test_doi_xe_cua.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1 import fleet as F
from app.services import access as AC

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"{HOM_NAY:%Y-%m}"


# Tên tài khoản trong bản nền KHÁC tên vai trò (tp_dh → tp.dieuhanh). Tra bằng vai trò để bài test nói
# đúng thứ nó muốn nói – "Điều hành không xem được" chứ không phải "tài khoản tp_dh không tồn tại".
VAI_TO_TEN = {"tp_dh": "tp.dieuhanh", "nv_dh": "dh.lan", "nv_kd": "kd.hoa", "gd_doi_xe": "gd.doixe.kt"}


def login(vai):
    ten = VAI_TO_TEN.get(vai, vai)
    if ten not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, f"không đăng nhập được vai {vai} ({ten}): {r.text}"
        TOK[ten] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[ten]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        # Bản nền không có tài khoản Giám đốc đội xe – tạo một tài khoản kiểm thử, như
        # test_vai_tro_gd_doi_xe.py vẫn làm.
        from app.db.session import SessionLocal
        from app.models.core import User
        from app.core.security import hash_password
        db = SessionLocal()
        db.add(User(username="gd.doixe.kt", full_name="GĐ đội xe kiểm thử", role="gd_doi_xe",
                    department="doi_xe", staff_code="KT904",
                    password_hash=hash_password("Vtos@Demo#2026"), active=True))
        db.commit(); db.close()
        yield


# ------------------------------------------------- 1. cửa đọc khớp ma trận màn hình

def test_cua_doc_hieu_qua_va_lai_lo_khai_dung_bang_ma_tran_man_hinh():
    """Suy từ MENU_ROLES chứ không chép tay – sửa ma trận một chỗ thì cửa API đổi theo."""
    assert set(F.XEM_HIEU_QUA) == set(AC.MENU_ROLES["/hieu-qua-doi-xe"])
    assert set(F.XEM_LAI_LO) == set(AC.MENU_ROLES["/lai-lo-doi-xe"])


def test_cnt_khong_goi_duoc_hieu_qua_dung_nhu_ma_tran_da_hua():
    """`test_ma_tran_quyen` hứa CNTT không xem được màn này. Lời hứa ấy phải đúng ở CỬA, không chỉ ở menu."""
    assert "cntt" not in AC.MENU_ROLES["/hieu-qua-doi-xe"], "tiền đề của bài test đã đổi"
    r = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("cntt"))
    assert r.status_code == 403, "cửa API vẫn mở trong khi menu đã đóng"


def test_dieu_hanh_va_hcns_khong_goi_duoc_lai_lo_dung_nhu_chu_thich_trong_ma_tran():
    """access.py ghi rõ: "Điều hành và HCNS không xem" lãi lỗ đội xe."""
    for vai in ("tp_dh", "nv_dh", "hcns"):
        assert vai not in AC.MENU_ROLES["/lai-lo-doi-xe"], f"tiền đề đã đổi với {vai}"
        for duong in (f"/api/v1/fleet/lai-lo?ky={KY}", f"/api/v1/fleet/chi-phi-ky?ky={KY}"):
            assert client.get(duong, headers=login(vai)).status_code == 403, f"{vai} vẫn mở được {duong}"


def test_nhung_vai_duoc_ma_tran_cho_phep_thi_van_vao_duoc():
    """Thu hẹp quyền mà chặn nhầm người đang làm việc thì tệ hơn là không thu hẹp."""
    assert client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("gd_doi_xe")).status_code == 200
    assert client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("ketoan")).status_code == 200
    assert client.get(f"/api/v1/fleet/lai-lo?ky={KY}", headers=login("ketoan")).status_code == 200
    assert client.get(f"/api/v1/fleet/lai-lo?ky={KY}", headers=login("cntt")).status_code == 200


# ------------------------------------------------- 2. cửa ghi tiền có người canh

def _xe():
    return client.get("/api/v1/fleet/xe", headers=login("cntt")).json()[0]["id"]


def _chuyen():
    return client.post("/api/v1/fleet/chuyen", headers=login("cntt"), json={
        "vehicle_id": _xe(), "ten_tour": "Để thử quyền", "ngay_di": str(HOM_NAY),
        "ngay_ve": str(HOM_NAY), "doanh_thu": 1_000_000}).json()["id"]


def test_vai_ngoai_doi_xe_khong_ghi_duoc_tien_vao_chuyen():
    """Nhân viên kinh doanh không có mặt trong bất kỳ nhóm ghi nào của đội xe."""
    h = login("nv_kd")
    assert client.post("/api/v1/fleet/chuyen", headers=h, json={
        "vehicle_id": _xe(), "ten_tour": "X", "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
        "doanh_thu": 1_000_000}).status_code in (403, 404)


def test_bks_chi_doc_khong_ghi_duoc_mot_dong_tien_nao():
    """BKS là vai KIỂM SOÁT – đọc hết, không ghi gì. Hàng rào này xét theo phương thức HTTP."""
    h = login("bks")
    tid = _chuyen()
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=h, json={
        "kind": "dau", "amount": 1_000_000, "lit": 30}).status_code == 403
    assert client.post("/api/v1/fleet/chi-phi-ky", headers=h, json={
        "ky": KY, "nhom": "bai_xe", "so_tien": 1_000_000, "chung_tu": "X"}).status_code == 403
    assert client.delete(f"/api/v1/fleet/chuyen/{tid}/chi-phi/1?ly_do=thử").status_code in (401, 403)


def test_xoa_khoan_chi_phi_ky_chi_danh_cho_nhom_quyet_toan():
    """Cửa xóa một khoản chi phí kỳ trước nay không có một phép thử quyền nào."""
    r = client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json={
        "ky": KY, "nhom": "bai_xe", "so_tien": 2_000_000, "chung_tu": "HD-X",
        "mo_ta": "để thử quyền xóa"})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    for vai in ("tp_dh", "nv_dh", "hcns"):
        assert client.delete(f"/api/v1/fleet/chi-phi-ky/{cid}?ly_do=thử", headers=login(vai)).status_code == 403
    assert client.delete(f"/api/v1/fleet/chi-phi-ky/{cid}", headers=login("ketoan")).status_code == 422
    assert client.delete(f"/api/v1/fleet/chi-phi-ky/{cid}?ly_do=nhập nhầm",
                         headers=login("ketoan")).status_code == 200


def test_thanh_toan_cong_no_chi_danh_cho_nhom_duyet():
    """Cửa chuyển tiền thật. Trước nay không có phép thử quyền nào."""
    for vai in ("cntt", "gd_doi_xe", "tp_dh", "hcns"):
        r = client.post("/api/v1/fleet/cong-no/thanh-toan", headers=login(vai), json={
            "partner_id": 1, "huong": "tra", "so_tien": 1_000_000, "idem_key": f"thu-{vai}"})
        assert r.status_code == 403, f"{vai} gọi được cửa thanh toán công nợ"


def test_huy_chuyen_chi_danh_cho_nhom_mo_lai():
    """Hủy chuyến là cửa MỚI – khai quyền cùng nhóm với mở lại, và phải có người canh ngay từ đầu."""
    tid = _chuyen()
    for vai in ("cntt", "nv_dh", "hcns", "gd_doi_xe"):
        assert client.post(f"/api/v1/fleet/chuyen/{tid}/huy", headers=login(vai),
                           json={"ly_do": "thử"}).status_code == 403, f"{vai} hủy được chuyến"
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/huy", headers=login("ketoan"),
                       json={"ly_do": "phiếu thử"}).status_code == 200
