"""Canh cửa cho ba đường chậm đã sửa ngày 10/9/2026 (ưu tiên 1 trong báo cáo rà soát).

Đo trên bản chạy thật trước khi sửa:
    /api/v1/collections/summary                     106.832 ms
    /api/v1/payroll/khoan-treo                       55.516 ms
    /api/v1/payroll-runs/{ky}/theo-phap-nhan         52.639 ms

Ba nguyên nhân khác nhau, nhưng cùng một hình dạng: mã nguồn duyệt một danh sách rồi HỎI CƠ SỞ DỮ LIỆU
MỘT LẦN CHO MỖI DÒNG. Máy không chậm; cái chậm là số vòng đi–về tới Postgres. Trên máy lập trình với
SQLite thì cùng đoạn mã ấy chạy trong một giây, nên KHÔNG được canh bằng đồng hồ – đo bằng giây ở đây
sẽ luôn xanh và ta lại thả lỗi lên bản chạy thật.

Nên phép thử này ĐẾM CÂU TRUY VẤN. Ý nghĩa của các trần bên dưới không phải "phải nhanh" mà là: số câu
truy vấn KHÔNG ĐƯỢC TĂNG THEO SỐ DÒNG DỮ LIỆU. Vì vậy mỗi phép thử chạy hai lần với hai cỡ dữ liệu và
đòi số câu gần như không đổi – một mức trần đơn lẻ có thể xanh giả trên bộ dữ liệu demo bé tí.

Phép thử cuối canh chuyện SAI chứ không phải chuyện chậm: mở màn hình bảng lương không được GHI vào
bảng lương. Trước khi sửa, mỗi lần đọc là một lần tính lại và `db.commit()`, nên hai người cùng mở thì
đè lên nhau và dấu thời gian nhảy – mất luôn câu trả lời "số này chốt lúc nào".
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ut1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ut1.db"):
    os.remove("test_ut1.db")

from datetime import date, datetime, timedelta                      # noqa: E402
import pytest                                                       # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from sqlalchemy import event, select                                # noqa: E402
from app.db.session import SessionLocal, engine                     # noqa: E402
from app.main import app                                            # noqa: E402
from app.models.core import Booking, Tour                           # noqa: E402
from app.models.hr import Employee                                  # noqa: E402

client = TestClient(app)
TOK: dict[str, dict] = {}
DEM = {"n": 0, "ghi": []}


@event.listens_for(engine, "before_cursor_execute")
def _dem(conn, cur, stm, params, ctx, many):
    DEM["n"] += 1
    s = " ".join(stm.split()).lower()
    if s.startswith(("insert", "update", "delete")) and "payroll_runs" in s:
        DEM["ghi"].append(s[:120])


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def login(u: str) -> dict:
    if u not in TOK:
        TOK[u] = {"Authorization": "Bearer " + client.post(
            "/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]}
    return TOK[u]


DOT = {"n": 0}


def them(n_tour: int, n_booking: int):
    """Thêm dữ liệu để đo lại ở cỡ lớn hơn. `moc` chỉ để mã không trùng giữa các đợt thêm."""
    DOT["n"] += 1; moc = DOT["n"]
    db = SessionLocal()
    sales = [e.user_id for e in db.execute(select(Employee).where(Employee.user_id != None)).scalars()] or [1]
    goc = date(2026, 1, 1)
    ts = []
    for i in range(n_tour):
        kt = goc + timedelta(days=i % 250)
        chot = i % 3 == 0
        t = Tour(code=f"UT{moc}{i:04d}", name=f"Chuyến {moc}-{i}", tour_type="le_noi_dia" if i % 4 else "doan",
                 start_date=kt, end_date=kt + timedelta(days=3), status="kt_xac_nhan" if chot else "duyet",
                 kt_confirmed_at=datetime(2026, 9, 1 + (i % 28)) if chot else None,
                 actual_revenue=100_000_000 + i, actual_cost=70_000_000 + i,
                 operator_id=sales[i % len(sales)], planned_pax=40)
        ts.append(t); db.add(t)
    db.flush()
    for j in range(n_booking):
        t = ts[j % n_tour]
        db.add(Booking(code=f"UB{moc}{j:05d}", tour_id=t.id, customer_name=f"Khách {moc}-{j}", pax=2,
                       amount=5_000_000 + j, discount=0, paid=0, request_id=0, customer_phone="",
                       source="thu", created_by=sales[0], sales_id=sales[j % len(sales)]))
    db.commit(); db.close()


def so_cau(duong: str, tai_khoan: str) -> tuple[int, dict]:
    h = login(tai_khoan)
    DEM["n"] = 0
    r = client.get(duong, headers=h)
    assert r.status_code == 200, r.text[:300]
    return DEM["n"], r.json()


def khong_tang_theo_du_lieu(duong: str, tai_khoan: str, tran: int):
    """Đo ở hai cỡ dữ liệu. Số câu phải nằm dưới trần Ở CẢ HAI, và không được phình theo số dòng."""
    them(60, 400)
    it, _ = so_cau(duong, tai_khoan)
    them(180, 1600)
    nhieu, _ = so_cau(duong, tai_khoan)
    assert nhieu <= tran, (
        f"{duong}: {nhieu} câu truy vấn cho một lần mở màn hình (trần {tran}). Gần như chắc chắn có chỗ "
        f"hỏi cơ sở dữ liệu một lần cho mỗi dòng. Sửa bằng cách gộp thành một câu (xem "
        f"payments.paid_amount_map) hoặc nạp sẵn quan hệ bằng selectinload – đừng nới trần.")
    assert nhieu - it <= max(5, tran // 4), (
        f"{duong}: dữ liệu tăng gấp bốn thì số câu tăng {it} → {nhieu}. Số câu đang phụ thuộc số dòng; "
        f"trên bản chạy thật với hàng vạn dòng thì đây là hàng vạn vòng đi–về tới Postgres.")


def test_collections_summary_khong_hoi_tung_booking():
    khong_tang_theo_du_lieu("/api/v1/collections/summary", "ketoan", 20)


def test_khoan_treo_khong_hoi_tung_chuyen():
    khong_tang_theo_du_lieu("/api/v1/payroll/khoan-treo", "ketoan", 30)


def test_bang_luong_theo_phap_nhan_khong_hoi_tung_chuyen():
    khong_tang_theo_du_lieu("/api/v1/payroll-runs/2026-09/theo-phap-nhan", "hcns", 120)


def test_collections_summary_cong_san_tong_con_phai_thu():
    """Máy chủ cộng sẵn thì giao diện không phải giữ cả vạn dòng để cộng – và hai bên phải khớp."""
    _, than = so_cau("/api/v1/collections/summary", "ketoan")
    tay = sum(b["due"] for b in than["bookings"] if b["due"] > 0)
    assert round(than["tong_con_phai_thu"]) == round(tay)
    assert than["so_booking_con_no"] == len([b for b in than["bookings"] if b["due"] > 0])


def test_chi_con_no_chi_tra_booking_con_no():
    _, than = so_cau("/api/v1/collections/summary?chi_con_no=1", "ketoan")
    assert than["bookings"], "phải còn booking chưa thu đủ trong bộ dữ liệu này"
    assert all(b["due"] > 0 for b in than["bookings"])
    assert than["so_booking_con_no"] == len(than["bookings"])


def test_mo_bang_luong_khong_ghi_vao_bang_luong():
    """Nửa SAI của việc số 1: một yêu cầu ĐỌC không được ghi.

    Hai người cùng mở màn hình bảng lương thì bản cũ ghi đè qua lại, ai bấm sau thắng, không ai biết.
    Và `updated_at` nhảy mỗi lần mở nên không còn dùng để giải trình một kỳ lương.
    """
    h = login("hcns")
    client.get("/api/v1/payroll-runs/2026-09", headers=h)      # lần đầu được phép tạo bản ghi
    DEM["ghi"].clear()
    moc = [client.get("/api/v1/payroll-runs/2026-09", headers=h).json()["updated_at"] for _ in range(3)]
    assert not DEM["ghi"], f"Đọc bảng lương mà vẫn ghi: {DEM['ghi']}"
    assert len(set(moc)) == 1, f"updated_at đổi qua ba lần chỉ đọc: {moc}"


def test_nhap_cong_van_tinh_lai_that():
    """Chỉ-ghi-khi-đổi không được biến thành không-bao-giờ-tính-lại: HCNS nhập công xong, số phải đổi."""
    h = login("hcns")
    truoc = client.get("/api/v1/payroll-runs/2026-09", headers=h).json()
    ma = next((r["ma"] for r in truoc["rows"] if r.get("che_do_cong") == "cham_cong"), None)
    assert ma, "bộ dữ liệu demo phải có ít nhất một người chấm công theo ngày"
    r = client.put("/api/v1/payroll-runs/2026-09/cham-cong", headers=h,
                   json={"cong_chuan": 26, "cong_thuc_te": {ma: 13}})
    assert r.status_code == 200, r.text[:300]
    sau = client.get("/api/v1/payroll-runs/2026-09", headers=h).json()
    a = next(x for x in truoc["rows"] if x["ma"] == ma)
    b = next(x for x in sau["rows"] if x["ma"] == ma)
    assert b["luong_cb"] != a["luong_cb"], "nhập nửa tháng công mà mức lương của kỳ không đổi – đệm sai"
    assert sau["updated_at"] != truoc["updated_at"]
