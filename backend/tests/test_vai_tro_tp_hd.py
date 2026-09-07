"""Trưởng phòng Hướng dẫn: vai trò riêng, và phạm vi đúng bằng công việc của người điều phối.

Bối cảnh 07/9/2026: toàn bộ hướng dẫn viên đã chuyển sang cộng tác viên; người điều phối là người duy
nhất trong phòng còn ký hợp đồng lao động và đóng BHXH. Trước bản này hệ thống KHÔNG có vai trò cho vị
trí đó — đúng kiểu lỗi đã gặp với Giám đốc điều hành đội xe: người phụ trách bị xếp chung vai trò với
nhân viên hiện trường, nên không mở được chính màn hình mình phụ trách.

Bốn điều bộ test này giữ:

  1. Người điều phối mở được phần hướng dẫn và chào được chuyến.
  2. Ông KHÔNG đọc được lương của người khác. Đây là lý do tồn tại của màn hình riêng: màn hình Điều
     hành cũ lấy danh sách người từ /employees, tức là kèm luôn lương của mọi phòng.
  3. Ông KHÔNG đọc được khách hàng, booking, ngân hàng — chọn người cho chuyến không cần biết ai đi.
  4. Hướng dẫn viên đọc được sự vụ ghi cho chính mình. Trước bản này màn hình sự vụ gọi mã "hdv" như
     một vai trò, nhưng "hdv" là mã chức danh; không tài khoản nào có vai trò đó, nên nhánh kiểm tra
     không bao giờ chạy tới và HDV bị khóa ngoài chính hồ sơ của mình.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tp_hd.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_tp_hd.db"): os.remove("test_tp_hd.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        # Tài khoản Trưởng phòng Hướng dẫn – vị trí có HĐLĐ duy nhất trong phòng.
        from app.db.session import SessionLocal
        from app.models.core import User
        from app.core.security import hash_password
        from app.models.hr import Employee
        from sqlalchemy import select
        with SessionLocal() as db:
            db.add(User(username="tp.huongdan", full_name="Trưởng phòng Hướng dẫn", role="tp_hd",
                        department="Hướng dẫn", password_hash=hash_password("123456")))
            hdv = db.execute(select(Employee).where(Employee.department == "huong_dan")).scalars().first()
            db.add(User(username="hdv.khang", full_name=hdv.full_name, role="xe_hdv",
                        department="Hướng dẫn", staff_code=hdv.code,
                        password_hash=hash_password("123456")))
            db.commit()
        yield


def test_vai_tro_ton_tai_trong_danh_muc(_startup):
    """Vai trò không có trong danh mục thì HCNS không cấp được cho ai – màn hình phân quyền không hiện ra."""
    from app.models.core import ROLES
    assert ROLES.get("tp_hd") == "Trưởng phòng Hướng dẫn"


def test_mo_duoc_man_hinh_cua_minh(_startup):
    h = login("tp.huongdan")
    for path in ("/api/v1/huong-dan/tong-quan", "/api/v1/huong-dan/hdv",
                 "/api/v1/huong-dan/chuyen-can-hdv", "/api/v1/huong-dan/chao-chuyen"):
        assert client.get(path, headers=h).status_code == 200, path


def test_danh_sach_hdv_khong_kem_luong_cua_ai(_startup):
    """Lý do tồn tại của màn hình riêng: cần biết ai còn hạn thẻ, KHÔNG cần biết ai lương bao nhiêu."""
    d = client.get("/api/v1/huong-dan/hdv", headers=login("tp.huongdan")).json()
    assert d["rows"], "bản demo phải có HDV để kiểm"
    cam = {"base_salary", "bhxh_base", "luong", "salary"}
    for r in d["rows"]:
        assert not (cam & set(r)), f"lộ trường lương: {cam & set(r)}"


def test_ba_dieu_kien_hanh_nghe_hien_rieng_tung_cot(_startup):
    """Gộp thành một chữ 'đạt' thì người điều phối biết là hỏng nhưng không biết đi đòi cái gì."""
    d = client.get("/api/v1/huong-dan/hdv", headers=login("tp.huongdan")).json()
    r = d["rows"][0]
    for k in ("the_het_han", "hoi_vien", "hop_dong_cong_tac", "du_dieu_kien", "vi_sao"):
        assert k in r
    hong = [x for x in d["rows"] if not x["du_dieu_kien"]]
    assert all(x["vi_sao"] for x in hong), "không đủ điều kiện thì phải nói rõ thiếu gì"


def test_khong_doc_duoc_luong_khach_hang_va_ngan_hang(_startup):
    """Phạm vi đúng bằng công việc: chọn người cho chuyến, không quản khách và không quản tiền."""
    h = login("tp.huongdan")
    for path in ("/api/v1/employees", "/api/v1/bookings", "/api/v1/tours",
                 "/api/v1/payroll-runs/2026-08", "/api/v1/bank-accounts"):
        assert client.get(path, headers=h).status_code == 403, f"{path} lẽ ra phải bị chặn"


def test_chao_chuyen_duoc_va_van_qua_cong_13(_startup):
    """Có quyền chào chuyến không có nghĩa là chào được cho người thiếu điều kiện hành nghề."""
    h = login("tp.huongdan")
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from app.models.core import Tour
    from sqlalchemy import select
    with SessionLocal() as db:
        hdv = db.execute(select(Employee).where(Employee.department == "huong_dan")).scalars().all()
        tour = db.execute(select(Tour)).scalars().first()
    from app.services import hr as H
    from datetime import date
    du = next((e for e in hdv if H.guide_eligible(e, date.today())[0]), None)
    khong = next((e for e in hdv if not H.guide_eligible(e, date.today())[0]), None)
    if khong is not None:
        r = client.post("/api/v1/guide-assignments", headers=h,
                        json={"tour_id": tour.id, "guide_id": khong.id, "days": 2, "rate_per_day": 400_000})
        assert r.status_code == 422 and r.json()["detail"]["gate"] == "CONG_13"
    if du is not None:
        r = client.post("/api/v1/guide-assignments", headers=h,
                        json={"tour_id": tour.id, "guide_id": du.id, "days": 2, "rate_per_day": 400_000})
        assert r.status_code == 201, r.text


def test_menu_chi_gom_phan_viec_cua_minh(_startup):
    d = client.get("/api/v1/auth/me", headers=login("tp.huongdan")).json()
    an = set(d.get("hidden_menus") or [])
    assert "/huong-dan" not in an
    for phai_an in ("/bookings", "/collections", "/hr", "/bank-accounts", "/expenses"):
        assert phai_an in an, f"{phai_an} lẽ ra phải bị ẩn khỏi menu"


def test_nap_duoc_danh_sach_hdv_nhung_khong_nap_duoc_so_ke_toan(_startup):
    h = login("tp.huongdan")
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=h).json()
    hd = next(b for b in d["bo_nap"] if b["ma"] == "huong_dan_vien")
    assert "tp_hd" in hd["vai_tro"] and hd["khoa_chong_trung"] == "Số thẻ hướng dẫn viên"
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "sao_ke_ngan_hang", "rows": [{"Mã giao dịch": "X", "Ngân hàng": "TPBank",
                                                                "Thời điểm": "01/08/2026", "Loại": "vao",
                                                                "Số tiền": "1000"}]})
    assert r.status_code == 403


def test_bo_nap_hdv_khoa_theo_so_the_va_khong_de_ho_so_cu(_startup):
    h = login("tp.huongdan")
    row = {"Số thẻ HDV": "HDV-NĐ-2026-9001", "Họ và tên": "Trần Thử Nghiệm",
           "Loại thẻ": "noi_dia", "Ngày hết hạn thẻ": "31/12/2029",
           "Hội viên tổ chức XH – nghề nghiệp": "x", "Đã ký hợp đồng cộng tác": "x",
           "Hạn mức tạm ứng": "5.000.000"}
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h, json={"loai": "huong_dan_vien", "rows": [row]})
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    r2 = client.post("/api/v1/nap-du-lieu/nap", headers=h, json={"loai": "huong_dan_vien", "rows": [row]})
    assert r2.json()["da_nap"] == 0 and r2.json()["da_co"] == 1


def test_khong_co_bo_nap_bang_don_gia_tuyen(_startup):
    """Đơn giá tuyến phải có chữ ký Chủ tịch và Tổng giám đốc; một tệp tải lên không thay được chữ ký."""
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("tp.huongdan")).json()
    assert "don_gia_tuyen" not in {b["ma"] for b in d["bo_nap"]}
    hd = next(b for b in d["bo_nap"] if b["ma"] == "huong_dan_vien")
    assert "không thay được chữ ký" in hd["mo_ta"]


def test_hdv_doc_duoc_su_vu_cua_chinh_minh(_startup):
    """Bị ghi nhận một sự vụ mà không được xem nó thì không đối chất được.

    Lỗi cũ: màn hình gọi mã "hdv" như một vai trò, nhưng đó là mã chức danh – không tài khoản nào có
    vai trò tên như vậy, nên nhánh lọc "chỉ xem sự vụ của mình" không bao giờ chạy tới."""
    from app.models.core import ROLES
    assert "hdv" not in ROLES, "nếu sau này có vai trò tên 'hdv' thì phải xem lại hai chỗ lọc ở màn hình sự vụ"
    r = client.get("/api/v1/incidents", headers=login("hdv.khang"))
    assert r.status_code == 200, r.text
