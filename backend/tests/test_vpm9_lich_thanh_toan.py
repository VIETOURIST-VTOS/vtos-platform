"""VPM-9 – hợp đồng khách trả làm nhiều đợt, và câu hỏi "đến hôm nay khách phải trả bao nhiêu".

Vì sao bộ kiểm này tồn tại: trước 11/9/2026 `hop_dong_khach` chỉ có MỘT `han_thanh_toan` và MỘT
`dat_coc`. Hợp đồng đoàn vài trăm triệu thực tế trả ba bốn đợt, và hệ thống không có chỗ nào nói
được điều đó — nên câu hỏi đơn giản nhất của người thu công nợ không có câu trả lời trong phần mềm.

Điều bộ kiểm canh:

  A  TỔNG KHỚP        – tổng các đợt phải bằng giá trị hợp đồng, lệch thì KHÔNG ghi gì
  B  HẠN CÓ CĂN CỨ    – hạn tính từ mốc ra ngày thật; mốc sai hoặc thiếu căn cứ thì bị chặn
  C  ĐẾN HÔM NAY      – phép chia tiền đã thu vào các đợt, và con số "phải trả đến hôm nay"
  D  HỨA KHÔNG TỰ ĐỔI – đổi ngày khởi hành thì hệ thống KÊU LÊN chứ không tự dời hạn
  E  DỜI HẠN CÓ NGƯỜI – phải có lý do, và giữ lại hạn gốc để thấy đã dời bao nhiêu
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm9.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
KD, KETOAN, DH = "kd.hoa", "ketoan", "dh.lan"


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


def _phien():
    from app.db.session import SessionLocal
    return SessionLocal()


_N = {"i": 0}


def _hop_dong(gia_tri: float = 300_000_000, noi_booking: bool = True):
    """Dựng thẳng một hợp đồng trong kho: chuỗi báo giá đầy đủ không phải điều VPM-9 canh."""
    from app.models.ban_hang import HopDongKhach
    from app.models.core import Booking
    from sqlalchemy import select
    _N["i"] += 1
    db = _phien()
    try:
        bid = None
        if noi_booking:
            b = db.execute(select(Booking).where(Booking.cancelled == False)).scalars().first()  # noqa: E712
            bid = b.id if b else None
        hd = HopDongKhach(so_hop_dong=f"HD-VPM9-{_N['i']:03d}", khach_ten="Công ty thử VPM-9",
                          ngay_ky=date.today(), gia_tri=gia_tri, trang_thai="da_ky", booking_id=bid)
        db.add(hd); db.commit()
        return hd.id, bid
    finally:
        db.close()


def _dat(hid: int, dot: list[dict], ai: str = KD):
    return client.post(f"/api/v1/ban-hang/hop-dong/{hid}/lich-thanh-toan",
                       headers=login(ai), json={"dot": dot})


def _xem(hid: int):
    r = client.get(f"/api/v1/ban-hang/hop-dong/{hid}/lich-thanh-toan", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    return r.json()


# ══════════════════ A – TỔNG KHỚP ══════════════════
def test_a1_chia_duoc_ba_dot_va_tong_khop_gia_tri():
    """Chính là việc hệ thống cũ không làm được: một hợp đồng, nhiều hạn, nhiều số tiền."""
    hid, _ = _hop_dong(300_000_000)
    r = _dat(hid, [
        {"ten": "Đặt cọc khi ký", "so_tien": 90_000_000, "ty_le": 30, "moc": "ngay_ky", "moc_so_ngay": 0},
        {"ten": "Trước khởi hành 7 ngày", "so_tien": 120_000_000, "ty_le": 40,
         "moc": "truoc_khoi_hanh", "moc_so_ngay": 7},
        {"ten": "Sau tour 15 ngày", "so_tien": 90_000_000, "ty_le": 30,
         "moc": "sau_khoi_hanh", "moc_so_ngay": 15},
    ])
    assert r.status_code == 200, r.text
    assert r.json()["so_dot"] == 3
    b = _xem(hid)
    assert b["khop_gia_tri"] is True
    assert b["tong_cac_dot"] == 300_000_000
    assert [d["dot"] for d in b["dot"]] == [1, 2, 3]


def test_a2_tong_lech_thi_KHONG_GHI_GI():
    """Lệch một đồng cũng không ghi: một lịch không khớp tổng thì người thu nợ vẫn phải tự cộng lại."""
    hid, _ = _hop_dong(100_000_000)
    r = _dat(hid, [{"ten": "Đợt 1", "so_tien": 60_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
                   {"ten": "Đợt 2", "so_tien": 39_999_000, "moc": "ngay_ky", "moc_so_ngay": 30}])
    assert r.status_code == 422
    assert "không bằng giá trị hợp đồng" in r.text
    assert _xem(hid)["dot"] == [], "lô hỏng mà vẫn ghi được dòng vào sổ"


def test_a3_so_tien_khong_duong_bi_tu_choi():
    hid, _ = _hop_dong(10_000_000)
    r = _dat(hid, [{"ten": "Đợt 1", "so_tien": 12_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
                   {"ten": "Đợt 2", "so_tien": -2_000_000, "moc": "ngay_ky", "moc_so_ngay": 10}])
    assert r.status_code == 422
    assert _xem(hid)["dot"] == []


def test_a4_hop_dong_chua_co_gia_tri_thi_chan():
    hid, _ = _hop_dong(0)
    r = _dat(hid, [{"ten": "Đợt 1", "so_tien": 1_000_000, "moc": "ngay_ky", "moc_so_ngay": 0}])
    assert r.status_code == 422
    assert "giá trị hợp đồng" in r.text


def test_a5_dat_lai_thi_THAY_TRON_lich_cu():
    """Nửa cũ nửa mới là thứ không ai đọc được, và tổng của nó không còn ai bảo đảm."""
    hid, _ = _hop_dong(200_000_000)
    _dat(hid, [{"ten": "A", "so_tien": 100_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
               {"ten": "B", "so_tien": 100_000_000, "moc": "ngay_ky", "moc_so_ngay": 30}])
    r = _dat(hid, [{"ten": "Một lần duy nhất", "so_tien": 200_000_000, "moc": "ngay_ky", "moc_so_ngay": 15}])
    assert r.status_code == 200, r.text
    b = _xem(hid)
    assert len(b["dot"]) == 1 and b["dot"][0]["ten"] == "Một lần duy nhất"


# ══════════════════ B – HẠN CÓ CĂN CỨ ══════════════════
def test_b1_han_tinh_tu_moc_ra_NGAY_THAT():
    hid, _ = _hop_dong(100_000_000)
    r = _dat(hid, [{"ten": "Cọc", "so_tien": 100_000_000, "moc": "ngay_ky", "moc_so_ngay": 10}])
    assert r.status_code == 200, r.text
    d = _xem(hid)["dot"][0]
    assert d["han"] == (date.today() + timedelta(days=10)).isoformat()
    assert d["moc"] == "ngay_ky" and d["moc_so_ngay"] == 10


def test_b2_moc_khong_hop_le_bi_tu_choi():
    hid, _ = _hop_dong(50_000_000)
    r = _dat(hid, [{"ten": "X", "so_tien": 50_000_000, "moc": "khi_nao_do", "moc_so_ngay": 3}])
    assert r.status_code == 422
    assert "không hợp lệ" in r.text


def test_b3_moc_co_dinh_ma_khong_nhap_ngay_thi_bi_chan():
    """Mốc cố định nghĩa là người tự chọn ngày – không chọn thì đợt ấy không có hạn, và một đợt
    không hạn thì không bao giờ đến hạn, tức là im lặng mãi mãi."""
    hid, _ = _hop_dong(50_000_000)
    r = _dat(hid, [{"ten": "X", "so_tien": 50_000_000, "moc": "co_dinh"}])
    assert r.status_code == 422
    assert "phải nhập ngày" in r.text


def test_b4_han_hop_dong_di_theo_dot_CUOI():
    """`han_thanh_toan` cũ vẫn được nhiều chỗ đọc – để nó nói khác lịch là tạo hai câu trả lời."""
    from app.models.ban_hang import HopDongKhach
    hid, _ = _hop_dong(100_000_000)
    _dat(hid, [{"ten": "A", "so_tien": 40_000_000, "moc": "ngay_ky", "moc_so_ngay": 5},
               {"ten": "B", "so_tien": 60_000_000, "moc": "ngay_ky", "moc_so_ngay": 45}])
    db = _phien()
    try:
        hd = db.get(HopDongKhach, hid)
        assert hd.han_thanh_toan == date.today() + timedelta(days=45)
    finally:
        db.close()


# ══════════════════ C – ĐẾN HÔM NAY ══════════════════
def test_c1_tien_da_thu_duoc_RAI_vao_cac_dot_theo_thu_tu_han():
    from app.models.core import Booking
    hid, bid = _hop_dong(100_000_000)
    if not bid:
        pytest.skip("dữ liệu mẫu không có booking để nối")
    _dat(hid, [{"ten": "A", "so_tien": 30_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
               {"ten": "B", "so_tien": 70_000_000, "moc": "ngay_ky", "moc_so_ngay": 30}])
    b = _xem(hid)
    assert b["da_thu"] == b["dot"][0]["da_rai"] + b["dot"][1]["da_rai"] + b["chua_gan_dot"], \
        "tiền đã thu không được rải hết – có đồng nào biến mất khỏi bảng"
    assert sum(d["da_rai"] + d["con_thieu"] for d in b["dot"]) == 100_000_000


def test_c2_phai_tra_den_hom_nay_dung_bang_phan_DA_DEN_HAN_tru_da_thu():
    """Đây là con số người thu công nợ cần, và trước VPM-9 không có chỗ nào trả lời."""
    hid, _ = _hop_dong(100_000_000)
    _dat(hid, [{"ten": "Đã tới hạn", "so_tien": 40_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
               {"ten": "Chưa tới hạn", "so_tien": 60_000_000, "moc": "ngay_ky", "moc_so_ngay": 60}])
    b = _xem(hid)
    assert b["den_han_hom_nay"] == 40_000_000
    assert b["phai_tra_den_hom_nay"] == round(max(0.0, 40_000_000 - b["da_thu"]), 2)


def test_c3_dot_qua_han_chua_thu_du_thi_vao_danh_sach_doi_no():
    hid, _ = _hop_dong(80_000_000)
    _dat(hid, [{"ten": "Quá hạn", "so_tien": 80_000_000, "moc": "co_dinh",
                "han": (date.today() - timedelta(days=9)).isoformat()}])
    r = client.get("/api/v1/ban-hang/hop-dong-qua-han", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    ds = [x for x in r.json()["dong"] if x["hop_dong_id"] == hid]
    assert ds, "đợt quá hạn không xuất hiện trong danh sách đòi công nợ"
    assert ds[0]["tre_ngay"] == 9


def test_c4_man_hinh_noi_ro_rai_tien_la_phep_chia_de_doc():
    """Tiền vào không mang nhãn. Màn hình phải nói thế, thay vì để người đọc tưởng hệ thống biết
    khoản nào trả cho đợt nào."""
    hid, _ = _hop_dong(10_000_000)
    _dat(hid, [{"ten": "A", "so_tien": 10_000_000, "moc": "ngay_ky", "moc_so_ngay": 0}])
    b = _xem(hid)
    assert "phép chia để đọc" in b["ghi_chu_man_hinh"]


# ══════════════════ D – HỨA KHÔNG TỰ ĐỔI ══════════════════
def test_d1_doi_ngay_khoi_hanh_thi_KEU_LEN_chu_khong_tu_doi_han():
    from app.models.core import Booking, Tour
    hid, bid = _hop_dong(100_000_000)
    if not bid:
        pytest.skip("dữ liệu mẫu không có booking để nối")
    _dat(hid, [{"ten": "Trước khởi hành 7 ngày", "so_tien": 100_000_000,
                "moc": "truoc_khoi_hanh", "moc_so_ngay": 7}])
    han_cu = _xem(hid)["dot"][0]["han"]

    db = _phien()
    try:
        b = db.get(Booking, bid); t = db.get(Tour, b.tour_id)
        cu = t.start_date
        t.start_date = cu + timedelta(days=20); db.commit()
    finally:
        db.close()
    try:
        b2 = _xem(hid)
        assert b2["dot"][0]["han"] == han_cu, "hệ thống tự dời hạn đã báo cho khách"
        assert b2["canh_bao"], "ngày khởi hành đổi mà hệ thống im lặng"
        assert "không tự đổi lời hứa" in b2["canh_bao"][0]
    finally:
        db = _phien()
        try:
            b = db.get(Booking, bid); t = db.get(Tour, b.tour_id)
            t.start_date = cu; db.commit()
        finally:
            db.close()


# ══════════════════ E – DỜI HẠN CÓ NGƯỜI ══════════════════
def _dot_dau(hid: int) -> int:
    return _xem(hid)["dot"][0]["id"]


def test_e1_doi_han_khong_ly_do_bi_tu_choi():
    hid, _ = _hop_dong(20_000_000)
    _dat(hid, [{"ten": "A", "so_tien": 20_000_000, "moc": "ngay_ky", "moc_so_ngay": 5}])
    r = client.post(f"/api/v1/ban-hang/hop-dong/lich-thanh-toan/{_dot_dau(hid)}/doi-han",
                    headers=login(KETOAN),
                    json={"han": (date.today() + timedelta(days=20)).isoformat(), "ly_do": "  "})
    assert r.status_code == 422


def test_e2_doi_han_giu_lai_HAN_GOC_va_ly_do():
    hid, _ = _hop_dong(20_000_000)
    _dat(hid, [{"ten": "A", "so_tien": 20_000_000, "moc": "ngay_ky", "moc_so_ngay": 5}])
    goc = _xem(hid)["dot"][0]["han"]
    moi = (date.today() + timedelta(days=25)).isoformat()
    r = client.post(f"/api/v1/ban-hang/hop-dong/lich-thanh-toan/{_dot_dau(hid)}/doi-han",
                    headers=login(KETOAN), json={"han": moi, "ly_do": "Khách xin lùi, TGĐ đồng ý"})
    assert r.status_code == 200, r.text
    d = _xem(hid)["dot"][0]
    assert d["han"] == moi and d["han_goc"] == goc and d["da_doi_han"] is True
    assert "TGĐ đồng ý" in d["ghi_chu"]


def test_e3_vai_tro_khong_co_tham_quyen_thi_khong_dat_lich_duoc():
    hid, _ = _hop_dong(10_000_000)
    r = _dat(hid, [{"ten": "A", "so_tien": 10_000_000, "moc": "ngay_ky", "moc_so_ngay": 0}], ai=DH)
    assert r.status_code in (403, 422)


def test_e4_man_hinh_hop_dong_co_cua_dat_lich():
    """Không có nút thì luật này chỉ sống trong mã."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "web", "app", "hop-dong-khach", "page.tsx")
    if not os.path.exists(p):
        pytest.skip("không có thư mục web trong bản sao này")
    s = open(p, encoding="utf-8").read()
    assert "lich-thanh-toan" in s, "màn hình hợp đồng không có cửa đặt lịch thanh toán"
    assert "doi-han" in s, "màn hình hợp đồng không có cửa dời hạn"
