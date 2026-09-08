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


def _chua_co(db, username: str) -> bool:
    """Bộ test chạy chung một tiến trình: tệp chạy TRƯỚC quyết định dùng CSDL nào, nên tệp chạy sau phải
    chấp nhận dữ liệu đã có thay vì chèn trùng và làm hỏng cả hai."""
    from app.models.core import User as _U
    from sqlalchemy import select as _s
    return db.execute(_s(_U).where(_U.username == username)).scalars().first() is None


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
            if _chua_co(db, "tp.huongdan"):
                db.add(User(username="tp.huongdan", full_name="Trưởng phòng Hướng dẫn", role="tp_hd",
                            department="Hướng dẫn", password_hash=hash_password("123456")))
            hdv = db.execute(select(Employee).where(Employee.department == "huong_dan")).scalars().first()
            if _chua_co(db, "hdv.khang"):
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
    # V10 – hai lần bấm nút khác nhau mang khóa chống ghi trùng khác nhau. Điều phép thử này canh là
    # lớp chống trùng THEO DÒNG (khóa = số thẻ HDV); để lớp khóa lô nuốt lời gọi thứ hai thì lớp trong
    # không còn được canh bởi phép thử nào.
    r = client.post("/api/v1/nap-du-lieu/nap", headers={**h, "X-Khoa-Ghi": "thu-hdv-1"},
                    json={"loai": "huong_dan_vien", "rows": [row]})
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    r2 = client.post("/api/v1/nap-du-lieu/nap", headers={**h, "X-Khoa-Ghi": "thu-hdv-2"},
                     json={"loai": "huong_dan_vien", "rows": [row]})
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


# ---------------------------------------------------------------- Form hồ sơ hành nghề
def test_form_ho_so_nhap_the_thi_qua_duoc_cong_13(_startup):
    """Cổng 13 chặn theo DỮ LIỆU, nên nhập thẻ là việc đầu tiên phải làm được – và làm được ngay trên
    màn hình của người phụ trách, không phải nhờ HCNS."""
    h = login("tp.huongdan")
    d = client.get("/api/v1/huong-dan/hdv", headers=h).json()
    e = next(x for x in d["rows"] if not x["du_dieu_kien"])
    r = client.put(f"/api/v1/huong-dan/hdv/{e['id']}", headers=h,
                   json={"the_so": "HDV-QT-2026-0777", "the_loai": "quoc_te",
                         "the_het_han": "2029-12-31", "hoi_vien": True,
                         "hop_dong_cong_tac": True, "han_muc_tam_ung": 5_000_000})
    assert r.status_code == 200, r.text
    assert r.json()["du_dieu_kien"] is True and "chào chuyến được" in r.json()["message"]


def test_thieu_dieu_kien_thi_luu_van_noi_ro_con_thieu_gi(_startup):
    h = login("tp.huongdan")
    r = client.post("/api/v1/huong-dan/hdv", headers=h,
                    json={"ho_ten": "Nguyễn Văn Mới", "the_so": "HDV-NĐ-2026-0888",
                          "the_loai": "noi_dia", "the_het_han": "2030-01-01"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["du_dieu_kien"] is False and "còn thiếu" not in d["message"]
    assert d["vi_sao"], "phải nói rõ còn thiếu điều kiện nào"


def test_khong_gan_trung_mot_so_the_cho_hai_nguoi(_startup):
    """Hai người cùng dẫn bằng một thẻ thì cả hai chuyến đều sai hồ sơ."""
    h = login("tp.huongdan")
    r = client.post("/api/v1/huong-dan/hdv", headers=h,
                    json={"ho_ten": "Người trùng thẻ", "the_so": "HDV-QT-2026-0777"})
    assert r.status_code == 422 and "đã gắn với" in r.json()["detail"]


def test_form_khong_sua_duoc_luong_hay_phong_ban(_startup):
    """Biểu mẫu nhận cả trường nó không có nhiệm vụ sửa là biểu mẫu sớm muộn sẽ sửa nhầm chúng."""
    h = login("tp.huongdan")
    d = client.get("/api/v1/huong-dan/hdv", headers=h).json()
    e = d["rows"][0]
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    with SessionLocal() as db:
        truoc = db.get(Employee, e["id"])
        luong, phong = truoc.base_salary, truoc.department
    client.put(f"/api/v1/huong-dan/hdv/{e['id']}", headers=h,
               json={"base_salary": 99_000_000, "department": "ketoan", "dien_thoai": "0900000000"})
    with SessionLocal() as db:
        sau = db.get(Employee, e["id"])
        assert sau.base_salary == luong and sau.department == phong
        assert sau.phone == "0900000000", "trường thuộc phạm vi form thì vẫn phải lưu được"


def test_chi_sua_duoc_ho_so_thuoc_phong_huong_dan(_startup):
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from sqlalchemy import select
    with SessionLocal() as db:
        ke_toan = db.execute(select(Employee).where(Employee.department == "ketoan")).scalars().first()
    if ke_toan is None: pytest.skip("bản demo không có nhân sự phòng khác để kiểm")
    r = client.put(f"/api/v1/huong-dan/hdv/{ke_toan.id}", headers=login("tp.huongdan"),
                   json={"dien_thoai": "0911111111"})
    assert r.status_code == 404
