"""VPM-7 – giữ chỗ có thời hạn: chỗ ngồi phải quay về tour khi không ai trả tiền cho nó.

Vì sao bộ kiểm này tồn tại: trước 11/9/2026 một booking chiếm chỗ ngay khi được tạo và giữ chỗ ấy
VĨNH VIỄN cho tới khi có người vào huỷ tay. Khách gọi giữ chỗ rồi im, sale quên, và tour hiện "hết
chỗ" trong khi không ai trả đồng nào. Cảnh báo `chua_coc` đã có sẵn, nhưng cảnh báo chỉ NÓI — nó
không trả chỗ về. UAT-05 dựa vào chỗ này.

Điều bộ kiểm canh KHÔNG PHẢI là "có cột giữ chỗ trong bảng", mà là:

  A  SỐ CHỖ NÓI THẬT   – hết hạn thì chỗ quay về tour, và số chỗ còn lại đổi theo
  B  KHÔNG HUỶ HỘ AI   – hết hạn ≠ huỷ booking; có tiền vào thì KHÔNG hết hạn
  C  GIA HẠN CÓ NGƯỜI  – phải có lý do, không vượt deadline hủy chỗ, và ĐẾM được
  D  KHÔI PHỤC CÓ CHỖ  – hết chỗ thì không cho quay lại, để khỏi bán trùng ghế
  E  DẤU VẾT           – mỗi lần đổi đều có một dòng nhật ký kèm ai làm và vì sao
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm7.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


# ---------- tiện ích ----------
# Mỗi phép thử dựng RIÊNG một booking qua đúng cửa thật (yêu cầu → booking), không dùng chung booking
# mẫu: dùng chung thì phép thử này để lại trạng thái cho phép thử kia, và lúc đỏ không ai biết vì sao.
SALE, DIEU_HANH, TPDH, KETOAN = "kd.hoa", "dh.lan", "tp.dieuhanh", "ketoan"


def _phien():
    from app.db.session import SessionLocal
    return SessionLocal()


def _tour_mo_ban() -> int:
    ds = client.get("/api/v1/tours", headers=login(KETOAN)).json()
    ds = ds if isinstance(ds, list) else ds.get("items", [])
    for t in ds:
        if t.get("status") == "da_duyet":
            return t["id"]
    pytest.skip("dữ liệu mẫu không có tour đã duyệt")


def _tao_booking(pax: int = 1):
    tid = _tour_mo_ban()
    r = client.post("/api/v1/requests", headers=login(SALE),
                    json={"tour_id": tid, "customer_name": "Khách thử giữ chỗ", "customer_phone": "0900000000",
                          "source": "hotline", "care_note": "phép thử VPM-7", "pax": pax})
    assert r.status_code in (200, 201), r.text
    rid = r.json()["request"]["id"]
    r2 = client.post(f"/api/v1/requests/{rid}/booking", headers=login(DIEU_HANH))
    assert r2.status_code in (200, 201), r2.text
    return r2.json()["booking"]["id"], tid


def _dat_qua_han(bid: int, gio_truoc: int = 5):
    from app.models.core import Booking
    db = _phien()
    try:
        b = db.get(Booking, bid)
        b.giu_cho_den = datetime.now() - timedelta(hours=gio_truoc)
        b.giu_cho_het = False
        db.commit()
    finally:
        db.close()


def _chay_robot():
    from app.services import giu_cho as GC
    db = _phien()
    try:
        return GC.het_han_giu_cho(db)
    finally:
        db.close()


def _con_trong(tid: int) -> int:
    from app.models.core import Tour
    from app.services import giu_cho as GC
    db = _phien()
    try:
        return GC.con_trong(db, db.get(Tour, tid))
    finally:
        db.close()


# ══════════════════ A – SỐ CHỖ NÓI THẬT ══════════════════
def test_a1_booking_moi_duoc_dat_han_giu_cho():
    """Hạn phải có NGAY lúc tạo booking. Đặt muộn hơn thì có một quãng không ai biết nó hết hạn khi nào."""
    bid, _ = _tao_booking()
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    assert v.get("giu_cho_den"), "booking không có hạn giữ chỗ"


def test_a2_het_han_thi_CHO_QUAY_VE_tour():
    """Đây là toàn bộ lý do VPM-7 tồn tại. Phép thử này đỏ nghĩa là việc chưa xong."""
    _chay_robot()          # dọn các booking mẫu vốn đã quá hạn sẵn, để phép đo dưới đây chỉ còn MỘT biến
    bid, tid = _tao_booking()
    truoc = _con_trong(tid)
    _dat_qua_han(bid)
    kq = _chay_robot()
    assert kq["het_han"] >= 1
    sau = _con_trong(tid)
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    assert sau > truoc, "chỗ KHÔNG quay về tour sau khi hết hạn giữ"
    assert sau - truoc == v["pax"], "số chỗ trả về không đúng số khách của booking"


def test_a3_con_trong_khong_am_va_dem_dung_sau_khi_khoi_phuc():
    bid, tid = _tao_booking()
    _dat_qua_han(bid); _chay_robot()
    sau_het = _con_trong(tid)
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/khoi-phuc", headers=login(TPDH),
                    json={"note": "Khách báo chuyển tiền chiều nay"})
    assert r.status_code == 200, r.text
    assert _con_trong(tid) < sau_het, "khôi phục mà chỗ không bị giữ lại"


# ══════════════════ B – KHÔNG HUỶ HỘ AI ══════════════════
def test_b1_het_han_KHONG_PHAI_la_huy_booking():
    """Robot trả chỗ về, nhưng KHÔNG được xoá cam kết với khách: booking vẫn sống, vẫn tra cứu được."""
    bid, _ = _tao_booking()
    _dat_qua_han(bid); _chay_robot()
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    assert v["giu_cho_het"] is True
    assert v.get("cancelled") is not True, "hết hạn giữ chỗ đã huỷ luôn booking – sai"
    assert not v.get("cancel_reason"), "booking bị gán lý do huỷ mà không ai huỷ"


def test_b2_da_co_tien_vao_thi_KHONG_het_han():
    """Khách đặt cọc dù một phần là đã có cam kết. Chỗ ấy thuộc về họ tới deadline hủy chỗ."""
    from app.models.core import Booking
    bid, _ = _tao_booking()
    db = _phien()
    try:
        b = db.get(Booking, bid)
        b.paid = 1_000_000
        b.giu_cho_den = datetime.now() - timedelta(hours=5)
        b.giu_cho_het = False
        db.commit()
    finally:
        db.close()
    _chay_robot()
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    assert v["giu_cho_het"] is False, "booking đã có tiền vào mà vẫn bị trả chỗ"
    db = _phien()
    try:
        b = db.get(Booking, bid); b.paid = 0; db.commit()
    finally:
        db.close()


def test_b3_booking_chua_co_han_thi_ROBOT_DAT_HAN_chu_khong_tuyen_het_han():
    """Booking cũ (trước 11/9/2026) có `giu_cho_den` rỗng. Rỗng là CHƯA ĐẶT HẠN, không phải hết hạn."""
    from app.models.core import Booking
    bid, _ = _tao_booking()
    db = _phien()
    try:
        b = db.get(Booking, bid)
        b.giu_cho_den = None; b.giu_cho_het = False; db.commit()
    finally:
        db.close()
    kq = _chay_robot()
    assert kq["dat_han"] >= 1
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    assert v.get("giu_cho_den"), "robot không đặt hạn cho booking cũ"
    assert v["giu_cho_het"] is False, "vừa đặt hạn đã tuyên hết hạn trong cùng một lượt"


# ══════════════════ C – GIA HẠN CÓ NGƯỜI ══════════════════
def test_c1_gia_han_khong_ly_do_bi_tu_choi():
    bid, _ = _tao_booking()
    den = (datetime.now() + timedelta(hours=6)).isoformat()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(TPDH),
                    json={"den": den, "ly_do": "   "})
    assert r.status_code == 422, "gia hạn không lý do vẫn lọt"


def test_c2_gia_han_ve_QUA_KHU_bi_tu_choi():
    bid, _ = _tao_booking()
    den = (datetime.now() - timedelta(hours=1)).isoformat()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(TPDH),
                    json={"den": den, "ly_do": "thử"})
    assert r.status_code == 422


def test_c3_khong_gia_han_qua_DEADLINE_HUY_CHO():
    """Qua mốc ấy tour đã đóng – giữ chỗ thêm là giữ một ghế không còn bán lại được."""
    bid, _ = _tao_booking()
    v = client.get(f"/api/v1/bookings/{bid}", headers=login(KETOAN)).json()
    dl = datetime.fromisoformat(v["cancel_deadline"])
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(TPDH),
                    json={"den": (dl + timedelta(days=1)).isoformat(), "ly_do": "khách xin thêm"})
    assert r.status_code == 422
    assert "deadline" in r.text.lower()


def test_c4_gia_han_duoc_DEM_va_qua_nguong_thi_keu_len():
    bid, _ = _tao_booking()
    lan_cuoi = 0
    for i in range(4):
        den = (datetime.now() + timedelta(hours=6 + i)).isoformat()
        r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(TPDH),
                        json={"den": den, "ly_do": f"khách hẹn lần {i + 1}"})
        assert r.status_code == 200, r.text
        lan_cuoi = r.json()["gia_han_lan"]
    assert lan_cuoi >= 4
    assert r.json()["canh_bao"], "gia hạn quá ngưỡng mà hệ thống im lặng"


def test_c5_vai_tro_khong_co_tham_quyen_thi_khong_gia_han_duoc():
    bid, _ = _tao_booking()
    den = (datetime.now() + timedelta(hours=6)).isoformat()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(KETOAN),
                    json={"den": den, "ly_do": "kế toán tự gia hạn"})
    assert r.status_code in (403, 422)


# ══════════════════ D – KHÔI PHỤC CÓ CHỖ ══════════════════
def test_d1_het_cho_thi_KHONG_khoi_phuc_duoc():
    """Cho quay lại khi tour đã đầy là bán trùng ghế – lỗi khách nhìn thấy ở sân bay, không phải trên màn hình."""
    from app.models.core import Booking, Tour
    bid, tid = _tao_booking()
    _dat_qua_han(bid); _chay_robot()
    db = _phien()
    try:
        t = db.get(Tour, tid)
        cu = t.seats_open
        b = db.get(Booking, bid)
        from app.services import rules as R
        t.seats_open = R.booked_pax(t)      # tour vừa đủ đầy, không còn chỗ cho booking quay lại
        db.commit()
        pax = b.pax
    finally:
        db.close()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/khoi-phuc", headers=login(TPDH),
                    json={"note": "khách trả tiền muộn"})
    assert r.status_code == 422, "tour hết chỗ mà vẫn cho khôi phục"
    assert str(pax) in r.text or "chỗ" in r.text
    db = _phien()
    try:
        t = db.get(Tour, tid); t.seats_open = cu; db.commit()
    finally:
        db.close()


def test_d2_khoi_phuc_booking_dang_giu_binh_thuong_bi_tu_choi():
    bid, _ = _tao_booking()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/khoi-phuc", headers=login(TPDH),
                    json={"note": "không có gì để khôi phục"})
    assert r.status_code == 422


# ══════════════════ E – DẤU VẾT ══════════════════
def test_e1_moi_lan_doi_deu_co_mot_dong_nhat_ky_kem_nguoi_va_ly_do():
    bid, _ = _tao_booking()
    r = client.post(f"/api/v1/bookings/{bid}/giu-cho/gia-han", headers=login(TPDH),
                    json={"den": (datetime.now() + timedelta(hours=9)).isoformat(),
                          "ly_do": "Khách chờ duyệt ngân sách công ty"})
    assert r.status_code == 200, r.text
    b = client.get(f"/api/v1/bookings/{bid}/giu-cho", headers=login(KETOAN)).json()
    dong = [n for n in b["nhat_ky"] if n["viec"] == "gia_han"]
    assert dong, "gia hạn xong mà không có dòng nhật ký"
    cuoi = dong[-1]
    assert cuoi["boi"] == TPDH and "ngân sách" in cuoi["ly_do"]
    assert cuoi["han_moi"], "dòng nhật ký không ghi hạn mới"


def test_e2_dong_het_han_ghi_ro_so_cho_tra_ve():
    bid, _ = _tao_booking()
    _dat_qua_han(bid); _chay_robot()
    b = client.get(f"/api/v1/bookings/{bid}/giu-cho", headers=login(KETOAN)).json()
    dong = [n for n in b["nhat_ky"] if n["viec"] == "het_han"]
    assert dong, "trả chỗ về mà không ghi lại"
    assert dong[-1]["so_cho"] == b["pax"]
    assert dong[-1]["boi"] == "robot"


def test_e3_tong_hop_dem_duoc_cho_dang_giu_va_cho_da_tra_ve():
    r = client.get("/api/v1/bookings/giu-cho/tong-hop", headers=login(TPDH))
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) == {"cho_dang_giu_chua_thu", "booking_sap_het_han_12h", "cho_da_tra_ve"}
    assert all(isinstance(v, int) and v >= 0 for v in d.values())


def test_e4_man_hinh_bookings_co_cua_gia_han():
    """Không có nút thì luật này chỉ sống trong mã – Điều hành không dùng được."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "web", "app", "bookings", "page.tsx")
    if not os.path.exists(p):
        pytest.skip("không có thư mục web trong bản sao này")
    s = open(p, encoding="utf-8").read()
    assert "giu-cho/gia-han" in s, "màn hình booking không có cửa gia hạn giữ chỗ"
    assert "giu-cho/khoi-phuc" in s, "màn hình booking không có cửa khôi phục giữ chỗ"
