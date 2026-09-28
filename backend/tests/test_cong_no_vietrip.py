# -*- coding: utf-8 -*-
"""Cửa nạp công nợ Vietrip hằng ngày (28/9/2026).

  CN1  nhóm và còn thiếu do MÁY CHỦ tính, không nhận từ ngoài
  CN2  booking hết nợ bị bỏ, bảo lưu nằm nhóm 0 và KHÔNG cộng vào tổng
  CN3  nạp lại cùng ngày THAY ảnh cũ, không cộng dồn
  CN4  trùng Booking ID trong lô thì chặn
  CN5  vai trò không được nạp thì bị chặn
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_congnovt.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_congnovt.db", "test_congnovt.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                              # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

from app.main import app                                   # noqa: E402
from app.api.v1.cong_no_vietrip import xep_nhom            # noqa: E402

client = TestClient(app)
NGAY = date(2026, 9, 27)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()  # noqa: E712
        assert u is not None, f"không có tài khoản vai trò {vai} trong dữ liệu mẫu"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _d(bid, tong, da_thu, kh, **kw):
    return {"booking_id": bid, "ma_tour": "HC001.02041026", "khach": "KHÁCH " + bid, "sales": kw.pop("sales", "A"),
            "sdt_khach": "0901000000", "tong": tong, "da_thu": da_thu,
            "khoi_hanh": str(kh) if kh else None, **kw}


def test_xep_nhom_bien():
    assert xep_nhom(NGAY, NGAY) == 1
    assert xep_nhom(NGAY + timedelta(days=14), NGAY) == 2
    assert xep_nhom(NGAY + timedelta(days=15), NGAY) == 3
    assert xep_nhom(date(2026, 10, 27), NGAY) == 3
    assert xep_nhom(date(2026, 10, 28), NGAY) == 4
    assert xep_nhom(None, NGAY) == 1
    assert xep_nhom(date(2026, 2, 28), date(2026, 1, 31)) == 3   # 31/1 + 1 tháng = 28/2


def test_nap_va_xem():
    h = login("ketoan")
    lo = [
        _d("127532", 1_690_000, 0, NGAY + timedelta(days=7)),                 # N2
        _d("100001", 5_000_000, 1_000_000, NGAY - timedelta(days=3), sales="B"),  # N1
        _d("100002", 2_000_000, 2_000_000, NGAY + timedelta(days=40)),        # hết nợ → bỏ
        _d("100003", 9_000_000, 0, NGAY + timedelta(days=60)),                # N4
        _d("101347", 61_400_000, 20_000_000, NGAY - timedelta(days=100), bao_luu=True),
    ]
    r = client.post("/api/v1/cong-no-vietrip/nap", headers=h, json={"ngay": str(NGAY), "dong": lo})
    assert r.status_code == 200, r.text
    k = r.json()
    assert k["so_booking"] == 3 and k["bo_qua_het_no"] == 1
    assert k["tong_con_thieu"] == 1_690_000 + 4_000_000 + 9_000_000
    nh = {x["nhom"]: x for x in k["nhom"]}
    assert nh[1]["so_booking"] == 1 and nh[2]["so_booking"] == 1 and nh[4]["so_booking"] == 1
    assert nh[0]["con_thieu"] == 41_400_000                                     # bảo lưu tách riêng

    x = client.get("/api/v1/cong-no-vietrip", headers=h).json()
    assert x["co_du_lieu"] and x["ngay"] == str(NGAY) and len(x["dong"]) == 4
    assert x["dong"][0]["booking_id"] == "100001"
    assert {s["sales"] for s in x["theo_sale"]} == {"A", "B"}


def test_nap_lai_thay_the():
    h = login("ketoan")
    r = client.post("/api/v1/cong-no-vietrip/nap", headers=h, json={
        "ngay": str(NGAY), "dong": [_d("127532", 1_690_000, 690_000, NGAY + timedelta(days=7))]})
    assert r.status_code == 200, r.text
    assert r.json()["so_booking"] == 1 and r.json()["tong_con_thieu"] == 1_000_000
    assert r.json()["so_lan_nap"] == 2
    ls = client.get("/api/v1/cong-no-vietrip/lich-su?so_ngay=400", headers=h).json()
    assert [a for a in ls if a["ngay"] == str(NGAY)][0]["tong_con_thieu"] == 1_000_000


def test_trung_booking_bi_chan():
    h = login("ketoan")
    lo = [_d("1", 10, 0, NGAY), _d("1", 20, 0, NGAY)]
    r = client.post("/api/v1/cong-no-vietrip/nap", headers=h, json={"ngay": str(NGAY), "dong": lo})
    assert r.status_code == 422


def test_vai_khong_duoc_nap():
    h = login("nv_kd")
    r = client.post("/api/v1/cong-no-vietrip/nap", headers=h, json={"ngay": str(NGAY), "dong": []})
    assert r.status_code == 403


def test_so_nghia_vu_phai_thu_lay_dung_theo_anh_vietrip():
    """28/9/2026 · "lấy đúng theo Vietrip": nạp ảnh xong thì phía thu khách của sổ nghĩa vụ = ảnh.

    Booking VTOS còn nợ theo bảng `bookings` nhưng KHÔNG có trong ảnh thì không còn là phải thu;
    bảo lưu không tính; tổng phải thu khách trong sổ bằng đúng tổng còn thiếu của ảnh.
    """
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models.nghia_vu import TRANG_THAI_DONG, NghiaVuThanhToan

    h = login("ketoan")
    ngay = date.today()
    lo = {"ngay": str(ngay), "dong": [
        _d("990001", 10_000_000, 4_000_000, ngay + timedelta(days=3)),
        _d("990002", 5_000_000, 0, ngay + timedelta(days=40)),
        _d("990003", 8_000_000, 8_000_000, ngay),                      # hết nợ → bỏ
        _d("990004", 7_000_000, 1_000_000, ngay + timedelta(days=5), bao_luu=True),
    ]}
    r = client.post("/api/v1/cong-no-vietrip/nap", json=lo, headers=h)
    assert r.status_code == 200, r.text
    assert "so_nghia_vu" in r.json(), r.json()
    with SessionLocal() as s:
        mo = s.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nhom == "thu_khach",
            NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG))).scalars().all()
        assert sorted(x.nguon_ma for x in mo) == ["VT990001", "VT990002"]
        assert round(sum(x.con_lai() for x in mo)) == 11_000_000
        assert s.execute(select(func.count()).select_from(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_ma == "VT990004")).scalar() == 0


def test_so_nghia_vu_phai_tra_lay_dung_theo_du_toan_vietrip():
    """29/9/2026 · "dựa vào dự toán tour để xác định số phải trả": nạp ảnh phải trả xong thì nhóm
    trả NCC của sổ = Tổng chi dự toán − Đã chi từng tour; tour đã chi đủ bị bỏ; hạn = ngày kết thúc."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.nghia_vu import TRANG_THAI_DONG, NghiaVuThanhToan

    h = login("ketoan")
    ngay = date.today()
    lo = {"ngay": str(ngay), "dong": [
        {"tour_id": 880001, "ma_tour": "ZZ001.01010126", "ten_tour": "Tour A",
         "khoi_hanh": str(ngay - timedelta(days=5)), "ket_thuc": str(ngay - timedelta(days=2)),
         "tong_chi": 30_000_000, "da_chi": 20_000_000},
        {"tour_id": 880002, "ma_tour": "ZZ001.02010126", "ten_tour": "Tour B",
         "khoi_hanh": str(ngay + timedelta(days=10)), "ket_thuc": str(ngay + timedelta(days=12)),
         "tong_chi": 8_000_000, "da_chi": 3_000_000},
        {"tour_id": 880003, "ma_tour": "ZZ001.03010126", "ten_tour": "Tour C",
         "tong_chi": 5_000_000, "da_chi": 5_000_000},                     # đã chi đủ → bỏ
    ]}
    r = client.post("/api/v1/cong-no-vietrip/nap-phai-tra", json=lo, headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["so_tour"] == 2 and round(j["tong_con_phai_chi"]) == 15_000_000
    assert "so_nghia_vu" in j, j
    with SessionLocal() as s:
        mo = s.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nhom == "tra_ncc",
            NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG))).scalars().all()
        assert all(x.nguon_bang == "phai_tra_vietrip" for x in mo), [x.nguon_bang for x in mo]
        assert round(sum(x.con_lai() for x in mo)) == 15_000_000
        a = next(x for x in mo if x.nguon_ma == "ZZ001.01010126")
        assert a.ngay_du_kien_tra == ngay - timedelta(days=2) and a.trang_thai == "qua_han"
    x = client.get("/api/v1/cong-no-vietrip/phai-tra", headers=h).json()
    assert x["co_du_lieu"] and x["so_tour"] == 2 and x["dong"][0]["ma_tour"] == "ZZ001.01010126"
