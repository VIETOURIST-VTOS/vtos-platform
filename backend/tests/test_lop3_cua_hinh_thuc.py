"""Cửa khai HÌNH THỨC của chuyến – phép thử canh chừng một ngõ cụt đã xảy ra thật.

VÌ SAO CÓ TỆP NÀY

Biểu nhập quyết toán CHẶN khi tours.hinh_thuc còn rỗng, và lời chặn bảo người dùng "khai hình thức ở
tab Thông tin trước". Nhưng cột ấy sinh ra ở bản nâng cấp mà không cửa nào ghi được: không API, không
ô nhập trên màn hình. Chạy thử trên chính cơ sở dữ liệu của Chủ tịch ngày 11/9/2026: cả 5 chuyến đều
hinh_thuc = NULL, nghĩa là biểu quyết toán mở ra là gặp tường, và cái tường ấy chỉ sang một chỗ không
tồn tại. Phép thử tĩnh không bắt được vì mọi tên cột đều có mặt trong mã; chỉ chạy thật mới lộ.

Ba điều tệp này giữ:
    1. CÓ cửa ghi, và nó ghi được thật.
    2. Tờ trắng khai lần đầu KHÔNG bị đòi lý do – nếu không thì cửa có cũng như không.
    3. Tờ ĐÃ CÓ SỐ mà đổi hình thức thì buộc nêu lý do và phải để lại dấu vết.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lop3_ht.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lop3_ht.db"):
    os.remove("test_lop3_ht.db")

from datetime import date                                            # noqa: E402
import pytest                                                        # noqa: E402
from fastapi.testclient import TestClient                             # noqa: E402
from app.db.session import SessionLocal, Base, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.main import app                                              # noqa: E402
from app.api import deps                                              # noqa: E402
from app.models.core import Booking, Tour, User                       # noqa: E402
from app.models.lop3_tour import BookingKhach, SuaSauKy               # noqa: E402

Base.metadata.create_all(engine)


def _nguoi(db, ten, vai):
    u = db.query(User).filter(User.username == ten).first()
    if not u:
        u = User(username=ten, full_name=ten, role=vai, password_hash="x")
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _tour(db, ma, nuoc="", operator_id=1):
    t = db.query(Tour).filter(Tour.code == ma).first()
    if not t:
        t = Tour(code=ma, name=ma, tour_type="package", start_date=date(2026, 7, 10),
                 end_date=date(2026, 7, 12), operator_id=operator_id, country=nuoc)
        db.add(t)
        db.commit()
        db.refresh(t)
    return t


@pytest.fixture()
def moi_truong():
    db = SessionLocal()
    dh = _nguoi(db, "ht_dh", "nv_dh")
    _nguoi(db, "ht_xem", "bks")
    t1 = _tour(db, "HT-TRANG", "", dh.id)
    t2 = _tour(db, "HT-CO-SO", "", dh.id)
    t3 = _tour(db, "HT-NUOC-NGOAI", "Thái Lan", dh.id)
    t4 = _tour(db, "HT-VIET-NAM", "Việt Nam", dh.id)
    bk = db.query(Booking).filter(Booking.code == "HT-BK-1").first()
    if not bk:
        bk = Booking(code="HT-BK-1", tour_id=t2.id, request_id=0, sales_id=dh.id,
                     created_by=dh.id, customer_name="Cty ABC", customer_phone="0900",
                     source="test", pax=1)
        db.add(bk)
        db.commit()
        db.refresh(bk)
    ids = (t1.id, t2.id, t3.id, t4.id, bk.id)
    db.close()
    yield ids


def _client(vai="nv_dh", ten="ht_dh"):
    db = SessionLocal()
    u = db.query(User).filter(User.username == ten).first()
    db.close()
    app.dependency_overrides[deps.current_user] = lambda: u
    return TestClient(app)


def test_co_cua_ghi_hinh_thuc(moi_truong):
    """Cửa tồn tại và ghi được – đây là điều đã THIẾU và làm biểu không mở ra được."""
    t1 = moi_truong[0]
    c = _client()
    r = c.put(f"/api/v1/quyet-toan-lop3/{t1}/hinh-thuc", json={"hinh_thuc": "nuoc_ngoai"})
    assert r.status_code == 200, r.text
    assert r.json()["hinh_thuc"] == "nuoc_ngoai"

    db = SessionLocal()
    assert db.get(Tour, t1).hinh_thuc == "nuoc_ngoai"
    db.close()

    # Và biểu đọc lại thấy ngay, vì màn hình lấy hình thức từ soat-gia chứ không tự nhớ.
    assert c.get(f"/api/v1/quyet-toan-lop3/{t1}/soat-gia").json()["hinh_thuc"] == "nuoc_ngoai"


def test_to_trang_khai_lan_dau_khong_doi_ly_do(moi_truong):
    """Khai lần đầu không phải là 'sửa'. Đòi lý do ở đây thì cửa có cũng như không."""
    t2 = moi_truong[1]
    c = _client()
    r = c.put(f"/api/v1/quyet-toan-lop3/{t2}/hinh-thuc", json={"hinh_thuc": "trong_nuoc"})
    assert r.status_code == 200, r.text
    assert r.json()["da_doi"] is True


def test_to_da_co_so_doi_hinh_thuc_phai_neu_ly_do_va_de_lai_dau_vet(moi_truong):
    """Đổi hình thức khi tờ đã có dòng làm những dòng ngoại tệ mất chỗ khai tỷ giá."""
    t2 = moi_truong[1]
    db = SessionLocal()
    t = db.get(Tour, t2)
    t.hinh_thuc = "trong_nuoc"
    db.add(BookingKhach(tour_id=t2, booking_id=moi_truong[4], stt=1, ho_ten="Nguyễn Văn A"))
    db.commit()
    db.close()

    c = _client()
    r = c.put(f"/api/v1/quyet-toan-lop3/{t2}/hinh-thuc", json={"hinh_thuc": "nuoc_ngoai"})
    assert r.status_code == 422, r.text
    assert "lý do" in r.text.lower()

    r = c.put(f"/api/v1/quyet-toan-lop3/{t2}/hinh-thuc",
              json={"hinh_thuc": "nuoc_ngoai", "ly_do": "Khai nhầm, đoàn này đi Singapore"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    dv = db.query(SuaSauKy).filter(SuaSauKy.tour_id == t2,
                                   SuaSauKy.truong == "hinh_thuc").all()
    assert len(dv) == 1
    assert dv[0].gia_tri_cu == "trong_nuoc" and dv[0].gia_tri_moi == "nuoc_ngoai"
    db.close()


def test_goi_y_tu_nuoc_nhung_khong_tu_ghi(moi_truong):
    """Máy ĐOÁN để đỡ phải nghĩ, nhưng không tự ghi: suy ngầm rồi tính tiền theo cái suy ấy là lỗi lặng."""
    _, _, t_nn, t_vn, _bk = moi_truong
    c = _client()

    a = c.get(f"/api/v1/quyet-toan-lop3/{t_nn}/soat-gia").json()
    assert a["goi_y_hinh_thuc"] == "nuoc_ngoai"
    assert a["hinh_thuc"] is None, "gợi ý mà tự ghi vào cột là đúng cái lỗi lặng cần tránh"

    b = c.get(f"/api/v1/quyet-toan-lop3/{t_vn}/soat-gia").json()
    assert b["goi_y_hinh_thuc"] == "trong_nuoc"
    assert b["hinh_thuc"] is None


def test_gia_tri_la_bi_tu_choi(moi_truong):
    c = _client()
    r = c.put(f"/api/v1/quyet-toan-lop3/{moi_truong[0]}/hinh-thuc",
              json={"hinh_thuc": "TRONG_NUOC"})
    assert r.status_code == 422


def test_vai_tro_chi_xem_khong_khai_duoc(moi_truong):
    """Cửa này đòi quyền NHẬP. Biểu cũng hỏi máy chủ chứ không tự suy – xem soat-gia.nhap_duoc."""
    c = _client(ten="ht_xem")
    r = c.put(f"/api/v1/quyet-toan-lop3/{moi_truong[0]}/hinh-thuc",
              json={"hinh_thuc": "trong_nuoc"})
    assert r.status_code == 403
    assert c.get(f"/api/v1/quyet-toan-lop3/{moi_truong[0]}/soat-gia").json()["nhap_duoc"] is False
