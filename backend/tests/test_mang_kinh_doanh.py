"""Mảng kinh doanh: Kinh doanh Lẻ và Kinh doanh Đoàn.

Đo trên dữ liệu thật ngày 07/9/2026 trước khi viết: 115 tour có chữ MICE thì cả 115 đều là doan_noi_dia và
đều BẮT ĐẦU bằng MICE; doan_noi_dia có 116 tour, đúng 1 tour không mang mã MICE (tour mẫu của bản demo).
Hai quy tắc trùng nhau hôm nay – nhưng bộ test này cố tình dựng ra các trường hợp chúng KHÔNG trùng, vì đó
mới là lúc phần mềm bộc lộ nó chọn bên nào. Chọn sai thì một phòng mất tour khỏi màn hình mà không ai biết
cho tới kỳ đối chiếu doanh số.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_mang.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_mang.db"): os.remove("test_mang.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def tao_tour(code: str, tour_type: str) -> int:
    """Tạo tour thẳng vào CSDL: ở đây đang kiểm cách PHÂN MẢNG, không kiểm cổng duyệt tour."""
    from app.db.session import SessionLocal
    from app.models.core import Tour, User
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        op = db.execute(sel(User).where(User.username == "dh.lan")).scalars().first()
        t = Tour(code=code, name=f"Kiểm thử {code}", tour_type=tour_type,
                 start_date=date.today() + timedelta(days=30), end_date=date.today() + timedelta(days=32),
                 operator_id=op.id, price_per_pax=1_000_000, fixed_cost=0, var_cost_per_pax=500_000,
                 planned_pax=10, status="da_duyet")
        db.add(t); db.commit()
        return t.id
    finally:
        db.close()


def codes(mang: str, who="chutich") -> set:
    r = client.get(f"/api/v1/tours?mang={mang}&limit=1000", headers=login(who))
    assert r.status_code == 200, r.text
    rows = r.json()
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    return {x["code"] for x in rows}


def test_hai_quy_tac_hop_nhat_khong_bo_sot_tour_nao():
    """Trường hợp nguy hiểm: tour mã MICE nhưng người nhập ghi nhầm loại chuyến là LẺ.

    Nếu chỉ lọc theo loại chuyến, tour này biến mất khỏi màn hình phòng Đoàn mà không ai biết. Hệ thống lấy
    HỢP của hai quy tắc nên nó vẫn nằm đúng chỗ."""
    tao_tour("MICEKT01-0930", "doan_noi_dia")     # đúng cả hai quy tắc
    tao_tour("MICEKT02-0930", "le_noi_dia")       # mã MICE nhưng loại chuyến ghi nhầm là lẻ
    tao_tour("DNKT03-0930", "doan_noi_dia")       # loại chuyến đoàn nhưng mã không theo quy ước MICE
    tao_tour("PTKT04-0930", "le_noi_dia")         # tour lẻ bình thường

    doan, le = codes("doan"), codes("le")
    assert "MICEKT01-0930" in doan
    assert "MICEKT02-0930" in doan, "mã MICE phải thuộc phòng Đoàn dù loại chuyến ghi nhầm"
    assert "DNKT03-0930" in doan, "loại chuyến đoàn phải thuộc phòng Đoàn dù mã không có MICE"
    assert "PTKT04-0930" in le

    # Và không tour nào nằm ở cả hai mảng – nếu không thì cộng doanh số hai phòng sẽ ra nhiều hơn thực tế
    assert doan & le == set()
    assert "MICEKT02-0930" not in le


def test_doi_chieu_chi_dich_danh_tour_hai_quy_tac_bat_dong():
    """Hệ thống không im lặng chọn một bên: nó nói ra đúng tour nào đang lệch để Kinh doanh sửa gốc."""
    r = client.get("/api/v1/mang", headers=login("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["quy_tac_doan"]["tien_to_ma"] == "MICE"
    dc = d["doi_chieu"]
    assert "MICEKT02-0930" in dc["ma_MICE_nhung_loai_chuyen_ghi_le"]
    assert "DNKT03-0930" in dc["loai_chuyen_doan_nhung_ma_khong_MICE"]
    assert dc["tong_lech"] >= 2


def test_khong_khai_mang_thi_thay_tat_ca_nhu_cu():
    """Bộ lọc là tùy chọn: màn hình cũ không truyền mảng thì hành vi không đổi."""
    tat_ca = codes("")
    assert {"MICEKT01-0930", "MICEKT02-0930", "DNKT03-0930", "PTKT04-0930"} <= tat_ca
    assert tat_ca >= codes("doan") | codes("le")


def test_mang_sai_thi_bao_loi_chu_khong_am_tham_bo_qua():
    """Gõ sai tên mảng mà hệ thống lặng lẽ trả về TẤT CẢ là kiểu sai nguy hiểm nhất: người dùng tưởng
    mình đang xem dữ liệu phòng mình."""
    for xau in ("doann", "MICE", "tour_doan"):
        r = client.get(f"/api/v1/tours?mang={xau}", headers=login("chutich"))
        assert r.status_code == 422, f"{xau} phải bị từ chối, nhận {r.status_code}"
        assert "Mảng không hợp lệ" in r.json()["detail"]


def test_booking_va_yeu_cau_loc_theo_mang_cua_tour():
    """Booking và yêu cầu không tự mang mảng – mảng nằm ở TOUR, nên phải nối bảng đúng."""
    h = login("kd.hoa")
    tid_doan = tao_tour("MICEKT05-0930", "doan_noi_dia")
    tid_le = tao_tour("PTKT06-0930", "le_noi_dia")
    for tid in (tid_doan, tid_le):
        r = client.post("/api/v1/requests", headers=h,
                        json={"tour_id": tid, "customer_name": "Khách kiểm thử", "customer_phone": "0900000001",
                              "source": "Khách quen", "pax": 2, "care_note": "Khách kiểm thử phân mảng"})
        assert r.status_code == 201, r.text
        rid = r.json()["request"]["id"]
        assert client.post(f"/api/v1/requests/{rid}/booking", headers=login("dh.lan")).status_code == 201

    hc = login("chutich")
    bk_doan = client.get("/api/v1/bookings?mang=doan&limit=1000", headers=hc).json()
    bk_le = client.get("/api/v1/bookings?mang=le&limit=1000", headers=hc).json()
    ids_doan = {b["tour_id"] for b in bk_doan if "tour_id" in b}
    ids_le = {b["tour_id"] for b in bk_le if "tour_id" in b}
    assert tid_doan in ids_doan and tid_doan not in ids_le
    assert tid_le in ids_le and tid_le not in ids_doan

    yc_doan = client.get("/api/v1/requests?mang=doan", headers=hc).json()
    assert any(x.get("tour_code") == "MICEKT05-0930" for x in yc_doan)
    assert not any(x.get("tour_code") == "PTKT06-0930" for x in yc_doan)


def test_tong_so_booking_giu_nguyen_pham_vi_mang_dang_xem():
    """Ô "tổng" phải là tổng CỦA MẢNG đang xem. Nếu lấy tổng toàn hệ thống thì phòng Đoàn nhìn thấy
    "12 / 10.074" và tưởng mình đang bị giấu dữ liệu."""
    hc = login("chutich")
    c_doan = client.get("/api/v1/bookings/count?mang=doan", headers=hc).json()
    c_all = client.get("/api/v1/bookings/count", headers=hc).json()
    assert c_doan["total"] <= c_all["total"]
    assert c_doan["total"] == c_doan["filtered"]        # không có bộ lọc phụ nào đang bật
    # Tổng hai mảng không được vượt tổng toàn hệ thống (chồng lấn nghĩa là cộng trùng doanh số)
    c_le = client.get("/api/v1/bookings/count?mang=le", headers=hc).json()
    assert c_doan["total"] + c_le["total"] <= c_all["total"]


def test_nhan_vien_kinh_doanh_van_chi_thay_phan_cua_minh():
    """Lọc theo mảng KHÔNG được nới phạm vi dữ liệu cá nhân đang có."""
    r = client.get("/api/v1/bookings?mang=doan&limit=1000", headers=login("kd.hoa"))
    assert r.status_code == 200
    ids = {b["id"] for b in r.json()}
    tat_ca = {b["id"] for b in client.get("/api/v1/bookings?limit=1000", headers=login("kd.hoa")).json()}
    assert ids <= tat_ca                                # lọc mảng chỉ thu hẹp, không mở rộng
