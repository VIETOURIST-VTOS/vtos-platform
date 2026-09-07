"""Luồng chào chuyến cho hướng dẫn viên cộng tác viên.

Toàn bộ HDV là cộng tác viên từ 07/9/2026. Luật xét NỘI DUNG quan hệ chứ không xét tên hợp đồng, và dữ
liệu hệ thống chính là nơi lưu bằng chứng về nội dung đó. Bộ test này giữ năm điều làm nên khác biệt
giữa "đặt dịch vụ" và "giao việc":

  1. Từ chối ghi được thành TỪ CHỐI, không nằm mãi ở "chưa xác nhận" trông như một lần chậm trễ.
  2. Từ chối KHÔNG kèm chế tài và không sinh sự vụ.
  3. Hết hạn trả lời là LỜI CHÀO hết hiệu lực, không phải hướng dẫn viên vi phạm.
  4. Một chuyến chỉ có một lời chào sống — hai người cùng nhận là công ty trả thù lao hai lần.
  5. Không ai trả lời thay được lời chào của người khác, kể cả bằng cách đổi số trên đường dẫn.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_chao.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_chao.db"): os.remove("test_chao.db")
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; ID = {}


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
        from app.db.session import SessionLocal
        from app.models.core import User, Tour
        from app.models.hr import Employee
        from app.core.security import hash_password
        from app.services import hr as H
        from sqlalchemy import select
        with SessionLocal() as db:
            if _chua_co(db, "tp.huongdan"):
                db.add(User(username="tp.huongdan", full_name="Trưởng phòng Hướng dẫn", role="tp_hd",
                            department="Hướng dẫn", password_hash=hash_password("123456")))
            hdv = [e for e in db.execute(select(Employee).where(
                Employee.department == "huong_dan")).scalars()
                if H.guide_eligible(e, date.today())[0]]
            assert hdv, "bản demo phải có ít nhất một HDV đủ điều kiện"
            e = hdv[0]
            if _chua_co(db, "hdv.mot"):
                db.add(User(username="hdv.mot", full_name=e.full_name, role="xe_hdv",
                            department="Hướng dẫn", staff_code=e.code,
                            password_hash=hash_password("123456")))
            ID["hdv"] = e.id
            # Hai tour tương lai để chào – tách khỏi tour demo đã có lệnh phân chuyến sẵn.
            for i, ma in enumerate(("HD-TEST-01", "HD-TEST-02")):
                t = Tour(code=ma, name=f"Tuyến thử {i+1}", tour_type="le_noi_dia",
                         start_date=date.today() + timedelta(days=20 + i),
                         end_date=date.today() + timedelta(days=22 + i), operator_id=1, planned_pax=20)
                db.add(t); db.flush(); ID[ma] = t.id
            db.commit()
        yield


def chao(tour, **kw):
    return client.post("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan"),
                       json={"tour_id": ID[tour], "guide_id": ID["hdv"], "days": 3,
                             "rate_per_day": 450_000, **kw})


def test_chao_chuyen_ghi_han_tra_loi_theo_tham_so(_startup):
    r = chao("HD-TEST-01")
    assert r.status_code == 201, r.text
    ID["a1"] = r.json()["id"]
    ds = client.get("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan")).json()
    a = next(x for x in ds if x["id"] == ID["a1"])
    assert a["han_tra_loi"] and a["trang_thai"] == "cho_xac_nhan"
    assert a["thu_lao"] == 3 * 450_000


def test_mot_chuyen_chi_co_mot_loi_chao_song(_startup):
    """Hai người cùng nhận một chuyến thì công ty trả thù lao hai lần."""
    r = chao("HD-TEST-01")
    assert r.status_code == 422 and "trả thù lao hai lần" in r.json()["detail"]


def test_hdv_tu_choi_duoc_va_khong_bi_ghi_bat_loi(_startup):
    """Từ chối là quyền của người cung cấp dịch vụ. Hệ thống phạt việc từ chối là hệ thống tự ghi lại
    bằng chứng rằng công ty giao việc chứ không phải đặt dịch vụ."""
    su_vu_truoc = len(client.get("/api/v1/incidents", headers=login("hcns")).json())
    r = client.post(f"/api/v1/xe-hdv/chao-chuyen/{ID['a1']}/tu-choi", headers=login("hdv.mot"),
                    json={"ly_do": "Trùng lịch cá nhân"})
    assert r.status_code == 200, r.text
    assert "không có ghi chú bất lợi" in r.json()["message"]
    ds = client.get("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan")).json()
    a = next(x for x in ds if x["id"] == ID["a1"])
    assert a["trang_thai"] == "tu_choi" and a["ly_do"] == "Trùng lịch cá nhân"
    assert a["trang_thai"] != "cho_xac_nhan", "từ chối không được nằm lẫn với chậm trả lời"
    assert len(client.get("/api/v1/incidents", headers=login("hcns")).json()) == su_vu_truoc


def test_tu_choi_roi_thi_chao_lai_nguoi_khac_duoc(_startup):
    """Lời chào đã từ chối không còn chiếm chỗ của chuyến."""
    r = chao("HD-TEST-01")
    assert r.status_code == 201, r.text
    ID["a2"] = r.json()["id"]


def test_nhan_chuyen(_startup):
    r = client.post(f"/api/v1/xe-hdv/chao-chuyen/{ID['a2']}/nhan", headers=login("hdv.mot"))
    assert r.status_code == 200, r.text
    ds = client.get("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan")).json()
    assert next(x for x in ds if x["id"] == ID["a2"])["trang_thai"] == "da_xac_nhan"


def test_khong_tra_loi_thay_loi_chao_cua_nguoi_khac(_startup):
    """Đổi số trên đường dẫn mà nhận thay được thì người bị nhận thay là người phải đi dẫn."""
    r = chao("HD-TEST-02")
    aid = r.json()["id"]
    assert client.post(f"/api/v1/xe-hdv/chao-chuyen/{aid}/nhan",
                       headers=login("hdv.mot")).status_code in (200, 422)
    # người khác (tài xế/HDV khác) không đụng được vào lời chào này
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    with SessionLocal() as db:
        db.add(User(username="hdv.hai", full_name="HDV khác", role="xe_hdv", department="Hướng dẫn",
                    staff_code="KHONG-CO", password_hash=hash_password("123456")))
        db.commit()
    assert client.post(f"/api/v1/xe-hdv/chao-chuyen/{aid}/nhan",
                       headers=login("hdv.hai")).status_code == 404


def test_loi_chao_qua_han_thi_het_hieu_luc_chu_khong_phai_vi_pham(_startup):
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    from app.models.core import Tour
    from sqlalchemy import select
    with SessionLocal() as db:
        t = db.execute(select(Tour).where(Tour.code == "HD-TEST-02")).scalars().first()
        a = db.execute(select(GuideAssignment).where(GuideAssignment.tour_id == t.id)
                       .order_by(GuideAssignment.id.desc())).scalars().first()
        a.status = "cho_xac_nhan"; a.confirmed_at = None
        a.han_tra_loi = datetime.now() - timedelta(hours=1)
        db.commit(); aid = a.id
    r = client.post(f"/api/v1/xe-hdv/chao-chuyen/{aid}/nhan", headers=login("hdv.mot"))
    assert r.status_code == 422 and "Không phải lỗi của anh/chị" in r.json()["detail"]
    ds = client.get("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan")).json()
    assert next(x for x in ds if x["id"] == aid)["loi_chao_qua_han"] is True
    r2 = client.post(f"/api/v1/huong-dan/chao-chuyen/{aid}/dong", headers=login("tp.huongdan"),
                     json={"ly_do": "quá hạn trả lời"})
    assert r2.status_code == 200
    ds = client.get("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan")).json()
    assert next(x for x in ds if x["id"] == aid)["trang_thai"] == "het_han"


def test_cong_13_van_chan_du_co_quyen_chao(_startup):
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from app.services import hr as H
    from sqlalchemy import select
    with SessionLocal() as db:
        xau = next((e for e in db.execute(select(Employee).where(
            Employee.department == "huong_dan")).scalars()
            if not H.guide_eligible(e, date.today())[0]), None)
    if xau is None: pytest.skip("bản demo không có HDV thiếu điều kiện để kiểm")
    r = client.post("/api/v1/huong-dan/chao-chuyen", headers=login("tp.huongdan"),
                    json={"tour_id": ID["HD-TEST-02"], "guide_id": xau.id, "days": 2,
                          "rate_per_day": 400_000})
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "CONG_13"


def test_treo_chao_chuyen_khi_con_no_bao_cao_tour(_startup):
    """Chưa nghiệm thu xong việc trước thì chưa giao việc sau – điều kiện hợp đồng dịch vụ, không phải
    hình thức kỷ luật."""
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    from app.models.core import Tour
    from sqlalchemy import select
    with SessionLocal() as db:
        t = Tour(code="HD-TEST-CU", name="Tuyến đã kết thúc", tour_type="le_noi_dia",
                 start_date=date.today() - timedelta(days=12), end_date=date.today() - timedelta(days=10),
                 operator_id=1)
        db.add(t); db.flush()
        db.add(GuideAssignment(tour_id=t.id, guide_id=ID["hdv"], days=3, rate_per_day=400_000,
                               status="da_xac_nhan", report_submitted=False, advance_settled=True,
                               assigned_by="tp.huongdan"))
        tm = Tour(code="HD-TEST-03", name="Tuyến mới", tour_type="le_noi_dia",
                  start_date=date.today() + timedelta(days=25), end_date=date.today() + timedelta(days=27),
                  operator_id=1)
        db.add(tm); db.flush(); ID["HD-TEST-03"] = tm.id
        db.commit()
    r = chao("HD-TEST-03")
    assert r.status_code == 422 and "chưa nộp báo cáo tour" in r.json()["detail"]
