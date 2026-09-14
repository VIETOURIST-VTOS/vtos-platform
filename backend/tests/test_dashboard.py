"""Dashboard theo vai trò và robot R7 báo cáo ngày/tuần/tháng."""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_dash.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "rt"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dash.db"): os.remove("test_dash.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.ROBOT_TOKEN = "rt"; settings.ANTHROPIC_API_KEY = ""

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_dashboard_by_role():
    d = client.get("/api/v1/dashboard", headers=login("chutich")).json()
    assert "tien" in d["kpis"] and "kd_le" in d["sections"] and "sap_khoi_hanh" in d["sections"] and any("dự toán" in a["label"] for a in d["approvals"])
    k = client.get("/api/v1/dashboard", headers=login("ketoan")).json()
    assert "tien" in k["kpis"] and all("href" in a for a in k["approvals"])
    s = client.get("/api/v1/dashboard", headers=login("kd.hoa")).json()
    assert "tien" not in s["kpis"] and "kd_le" in s["sections"]


def test_auto_reports_and_robot_api():
    for kind in ("ngay", "tuan", "thang"):
        r = client.post(f"/api/v1/auto-reports/{kind}", headers=login("cntt")).json()["report"]
        assert r["content"].startswith("# Báo cáo") and "Nhận xét của robot" in r["content"] and r["comment"]
    assert client.post("/api/v1/auto-reports/nam", headers=login("cntt")).status_code == 422
    assert client.post("/api/v1/robot/report/ngay").status_code == 401
    rr = client.post("/api/v1/robot/report/ngay", headers={"X-Robot-Token": "rt"}).json()
    assert rr["period"] == str(date.today()) and "markdown" in rr
    lst = client.get("/api/v1/auto-reports", headers=login("bks")).json()
    assert len(lst) == 3                                   # chạy lại cùng kỳ → ghi đè, không nhân bản
    assert client.get("/api/v1/auto-reports", headers=login("kd.hoa")).status_code == 403


def test_trang_chu_co_bang_rieng_cho_phong_doan():
    """Trước 07/9/2026 trang chủ chỉ có bảng của phòng Lẻ. Người phòng Đoàn mở trang chủ ra không thấy gì về
    phần việc của mình – mà đúng cách tính lương của họ (chia lợi nhuận quyết toán) cũng không thấy."""
    for who in ("chutich", "kd.hoa"):
        sec = client.get("/api/v1/dashboard?refresh=1", headers=login(who)).json()["sections"]
        assert "kd_doan" in sec, f"{who}: thiếu bảng phòng Đoàn"
        assert "rows" in sec["kd_doan"] and "so_chuyen" in sec["kd_doan"]
        # Hai phòng đo bằng hai thước đo khác nhau: Lẻ theo doanh thu so mốc, Đoàn theo lợi nhuận chia.
        assert all("pct" in r and "revenue" in r for r in sec["kd_le"])
        assert all("profit_share" in r and "revenue" not in r for r in sec["kd_doan"]["rows"]), \
            "bảng phòng Đoàn không được hiện doanh thu như phòng Lẻ – họ không hưởng theo doanh thu"


def _dung_chuyen_doan_da_quyet_toan(ma: str, doanh_thu: int, gia_von: int) -> str:
    """Dựng một chuyến đoàn ĐÃ quyết toán trong tháng, kèm một booking, để bảng phòng Đoàn có số thật.

    Ghi thẳng vào CSDL: ở đây đang kiểm CÁCH CHIA lợi nhuận lên trang chủ, không kiểm quy trình quyết toán
    (quy trình đó đã có bộ test riêng)."""
    from datetime import datetime, timedelta
    from app.db.session import SessionLocal
    from app.models.core import Tour, Booking, User
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        op = db.execute(sel(User).where(User.username == "dh.lan")).scalars().first()
        sale = db.execute(sel(User).where(User.username == "kd.hoa")).scalars().first()
        hom_nay = date.today()
        t = Tour(code=ma, name=f"Đoàn quyết toán {ma}", tour_type="doan_noi_dia",
                 start_date=hom_nay - timedelta(days=10), end_date=hom_nay - timedelta(days=8),
                 operator_id=op.id, price_per_pax=doanh_thu, fixed_cost=0, var_cost_per_pax=gia_von,
                 planned_pax=1, status="kt_xac_nhan", actual_revenue=doanh_thu, actual_cost=gia_von,
                 kt_confirmed_at=datetime.now(), closed_at=datetime.now())
        db.add(t); db.flush()
        db.add(Booking(code=f"BK{ma}", tour_id=t.id, request_id=0, sales_id=sale.id, created_by=sale.id,
                       customer_name="Khách đoàn", customer_phone="0912000001", source="Khách quen", pax=1,
                       amount=doanh_thu, discount=0, paid=doanh_thu))
        db.commit()
        return sale.full_name
    finally:
        db.close()


def test_loi_nhuan_chia_cho_phong_doan_len_dung_tren_trang_chu():
    """Dựng một chuyến đoàn quyết toán lãi 40 triệu và kiểm con số chia đúng lên bảng phòng Đoàn.

    Nếu chỉ kiểm "có khóa kd_doan" thì bảng rỗng cũng đỗ, và ngày phần mềm tính sai không ai biết."""
    ten_sale = _dung_chuyen_doan_da_quyet_toan("MICEDB01-0930", 100_000_000, 60_000_000)
    # refresh=1 bắt buộc: bảng điều khiển có bộ nhớ đệm 5 phút theo vai trò, mà các test trước đã gọi rồi.
    # Không có nó thì test đọc lại bản cũ và "đỗ" hay "trượt" tùy thứ tự chạy – kiểu test tệ nhất.
    sec = client.get("/api/v1/dashboard?refresh=1", headers=login("chutich")).json()["sections"]
    dong = [r for r in sec["kd_doan"]["rows"] if r["sales"] == ten_sale]
    assert dong, "chuyến đoàn đã quyết toán mà bảng phòng Đoàn vẫn rỗng"
    assert round(dong[0]["profit_share"]) == 40_000_000, dong[0]
    assert sec["kd_doan"]["so_chuyen"] >= 1
    # Và lợi nhuận đoàn KHÔNG được lẫn sang bảng phòng Lẻ dưới dạng doanh thu tính chỉ tiêu
    assert not any(r["sales"] == ten_sale and r["revenue"] >= 100_000_000 for r in sec["kd_le"]), \
        "doanh thu chuyến đoàn chảy nhầm sang chỉ tiêu phòng Lẻ"
