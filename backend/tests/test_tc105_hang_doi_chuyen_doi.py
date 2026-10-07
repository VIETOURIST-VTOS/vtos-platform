"""TC-105 · Hàng đợi đẩy chuyển đổi ngược — nói lại cho nền tảng biết khách nào thật sự mua.

Bắt được cái chạm (TC-103) mới là nửa việc. Không nói ngược lại thì Google và Facebook chỉ học
được "có người điền form", và chúng sẽ rất giỏi mua thêm đúng loại khách ấy — rẻ nhất và không
chốt. Báo cáo Marketing tháng 9/2026 đã thấy hình dạng của việc này: TikTok "data nhiều nhưng tỷ
lệ chốt thấp nhất".

  C1  lead chốt tour thì mỗi nền tảng có dấu được MỘT dòng, và mỗi dòng mang doanh thu ĐẦY ĐỦ
  C2  chạy lại lượt sinh KHÔNG nhân đôi
  C3  booking chưa có số tiền thì KHÔNG gửi 0 — nằm riêng ở "thiếu doanh thu"
  C4  booking đã huỷ thì không sinh dòng nào
  C5  gửi lỗi thì giữ dòng lại, đếm lần thử, không xoá
  C6  cửa của bộ gửi đứng sau khoá máy chủ
  C7  bảng số nói thẳng rằng ba nền tảng KHÔNG được cộng lại
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc105.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "robot-tc105"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc105.db", "test_tc105.db-journal"):
    if os.path.exists(f): os.remove(f)

from datetime import date, datetime                 # noqa: E402
import pytest                                       # noqa: E402
from fastapi.testclient import TestClient           # noqa: E402
from app.main import app                            # noqa: E402

client = TestClient(app)
KHOA = {"X-Robot-Token": "robot-tc105"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _dung(sdt: str, ma_bk: str, tien, nen_tangs, huy=False):
    """Dựng một khách: tour, booking, lead đã chốt, và một dấu cho mỗi nền tảng."""
    from app.models.core import Tour, Booking, User
    from app.models.crm import Lead
    from app.services import dau_quang_cao as DQ
    db = _db()
    try:
        u = db.query(User).filter(User.username == "nguoi_thu").first()
        if not u:
            from app.core.security import hash_password
            u = User(username="nguoi_thu", full_name="Nguoi thu", role="nv_kd",
                     password_hash=hash_password("Vtos@Demo#2026"), active=True)
            db.add(u); db.commit(); db.refresh(u)
        t = db.query(Tour).filter(Tour.code == "T105").first()
        if not t:
            t = Tour(code="T105", name="Tour thu TC-105", tour_type="le_noi_dia",
                     operator_id=u.id, start_date=date(2026, 10, 20),
                     end_date=date(2026, 10, 23), status="mo")
            db.add(t); db.commit(); db.refresh(t)
        # request_id=0 và created_by=u.id: cùng cách các tệp phép thử sẵn có dựng booking
        # (xem test_cham_soc). Vòng này không kiểm luồng yêu cầu – chỉ cần một booking hợp lệ.
        b = Booking(code=ma_bk, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                    customer_name="Khach thu", customer_phone=sdt, source="vtos", pax=2,
                    amount=tien, cancelled=huy)
        db.add(b); db.commit(); db.refresh(b)
        l = Lead(phone=sdt, name="Khach thu", channel="Hotline 1",
                 lead_month=f"{datetime.now():%Y-%m}", booking_id=b.id,
                 converted_at=datetime.now(), status="chot", created_by="phepthu")
        db.add(l); db.commit(); db.refresh(l)
        for i, nt in enumerate(nen_tangs):
            DQ.ghi(db, {"nen_tang": nt, "loai_ma": "khac", "ma": f"{nt}-{ma_bk}-{i}",
                        "sdt": sdt, "cham_luc": "2026-10-05 08:00:00"})
        db.commit()
        return b.id, l.id
    finally:
        db.close()


def _sinh():
    return client.post("/api/v1/dau-quang-cao/chuyen-doi/sinh", headers=KHOA).json()


def test_c1_moi_nen_tang_mot_dong_va_doanh_thu_day_du_khong_chia():
    """Gửi cho Google một phần ba doanh thu vì khách còn chạm Facebook và hotline thì Google tối
    ưu theo một con số không phải giá trị thật của khách ấy, và ra giá thầu thấp hơn giá trị thật.
    Mỗi nền tảng dự phần nhận giá trị ĐẦY ĐỦ — đó là cách các nền tảng được thiết kế."""
    _dung("0901110001", "BK105001", 30_000_000, ["google", "facebook", "tong_dai"])
    r = _sinh()
    assert r["moi"] == 3, f"ba nền tảng phải ra ba dòng, nhận được {r}"
    ds = client.get("/api/v1/dau-quang-cao/chuyen-doi?trang_thai=cho_gui", headers=_dn("ptgd_mkt")).json()
    cua_bk = [x for x in ds if x["ma_booking"] == "BK105001"]
    assert len(cua_bk) == 3
    assert {x["nen_tang"] for x in cua_bk} == {"google", "facebook", "tong_dai"}
    assert all(float(x["doanh_thu"]) == 30_000_000 for x in cua_bk), (
        "mỗi nền tảng phải nhận doanh thu ĐẦY ĐỦ, không chia")


def test_c2_chay_lai_khong_nhan_doi():
    """Lượt sinh là việc robot chạy đều. Không chống trùng thì mỗi lượt lại báo lại một chuyển đổi
    đã báo, và nền tảng đếm một khách thành nhiều."""
    truoc = _sinh()
    assert truoc["moi"] == 0, "không có khách mới thì không sinh dòng nào"
    assert truoc["da_co"] >= 3


def test_c3_thieu_doanh_thu_thi_khong_gui_so_khong():
    """Gửi 0 đồng là dạy nền tảng rằng khách ấy vô giá trị – tệ hơn hẳn việc im lặng."""
    _dung("0901110002", "BK105002", None, ["google"])
    r = _sinh()
    assert r["moi"] == 1 and r["thieu_doanh_thu"] == 1
    cho = client.get("/api/v1/dau-quang-cao/chuyen-doi/cho-gui", headers=KHOA).json()
    assert not [x for x in cho if x["ma_booking"] == "BK105002"], (
        "dòng thiếu doanh thu KHÔNG được nằm trong việc của bộ gửi")
    ds = client.get("/api/v1/dau-quang-cao/chuyen-doi?trang_thai=thieu_doanh_thu",
                    headers=_dn("ptgd_mkt")).json()
    assert [x for x in ds if x["ma_booking"] == "BK105002"]


def test_c4_booking_da_huy_thi_khong_sinh():
    _dung("0901110003", "BK105003", 12_000_000, ["tiktok"], huy=True)
    _sinh()
    ds = client.get("/api/v1/dau-quang-cao/chuyen-doi", headers=_dn("ptgd_mkt")).json()
    assert not [x for x in ds if x["ma_booking"] == "BK105003"]


def test_c5_gui_loi_thi_giu_dong_lai_va_dem_lan_thu():
    """Xoá dòng lỗi là xoá luôn con số 'bao nhiêu chuyển đổi chưa tới được nền tảng'."""
    cho = client.get("/api/v1/dau-quang-cao/chuyen-doi/cho-gui", headers=KHOA).json()
    assert cho, "phải có việc để thử"
    cid = cho[0]["id"]
    r = client.post(f"/api/v1/dau-quang-cao/chuyen-doi/{cid}/ket-qua",
                    json={"xong": False, "loi": "token chua co"}, headers=KHOA).json()
    assert r["trang_thai"] == "loi" and r["lan_thu"] == 1 and "token" in r["loi_cuoi"]
    r2 = client.post(f"/api/v1/dau-quang-cao/chuyen-doi/{cid}/ket-qua",
                     json={"xong": True, "tra_loi": "ok"}, headers=KHOA).json()
    assert r2["trang_thai"] == "da_gui" and r2["lan_thu"] == 2 and r2["gui_luc"]


def test_c6_cua_cua_bo_gui_dung_sau_khoa_may_chu():
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/sinh").status_code == 401
    assert client.get("/api/v1/dau-quang-cao/chuyen-doi/cho-gui").status_code == 401
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/1/ket-qua",
                       json={"xong": True}).status_code == 401


def test_c7_bang_so_noi_thang_rang_ba_nen_tang_khong_duoc_cong_lai():
    """Một con số dễ bị cộng nhầm mà không có lời cảnh báo đi kèm thì sớm muộn sẽ bị cộng nhầm,
    và lần ấy nó nằm trong một bản trình Chủ tịch."""
    b = client.get("/api/v1/dau-quang-cao/chuyen-doi/bang-do", headers=_dn("ptgd_mkt")).json()
    assert set(b) >= {"tong", "theo_trang_thai", "ty_le_gui_duoc", "da_gui_nhung_huy", "luu_y"}
    assert "không" in b["luu_y"].lower() and "cộng" in b["luu_y"].lower()
    assert b["tong"] == sum(b["theo_trang_thai"].values())


_TOK: dict = {}


def _dn(u: str):
    if u not in _TOK:
        from app.models.core import User
        from app.core.security import hash_password
        db = _db()
        try:
            if not db.query(User).filter(User.username == u).first():
                db.add(User(username=u, full_name=u, role=u,
                            password_hash=hash_password("Vtos@Demo#2026"), active=True))
                db.commit()
        finally:
            db.close()
        _TOK[u] = client.post("/api/v1/auth/login",
                              data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {_TOK[u]}"}
