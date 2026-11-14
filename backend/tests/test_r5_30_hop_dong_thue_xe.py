# -*- coding: utf-8 -*-
"""R5-30 · Đội xe tự nhận hợp đồng thuê xe (Chủ tịch 14/11/2026: phương án B; «CT duyệt, TGĐ thấy»)."""
import os
import tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r5_30.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
D1 = date.today() + timedelta(days=700)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(ten):
    for mk in (ten, "Vtos@Demo#2026"):
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": mk})
        if r.status_code == 200:
            return {"Authorization": f"Bearer {r.json()['access_token']}"}
    raise AssertionError(r.text)


def _hd(ma, gia=9_000_000, chi_phi=5_000_000):
    return {"ma": ma, "khach": "Công ty ABC", "lo_trinh": "HCM ⇄ Vũng Tàu", "ngay_di": str(D1),
            "ngay_ve": str(D1 + timedelta(days=1)), "so_xe": 1, "so_khach": 20, "gia": gia, "chi_phi": chi_phi,
            "diem_dung": "Trạm Long Thành"}


def test_chi_gd_doi_xe_tao_duoc():
    assert client.post("/api/v1/fleet/hop-dong-thue-xe", json=_hd("TX-T1"), headers=login("dh.lan")).status_code == 403
    assert client.post("/api/v1/fleet/hop-dong-thue-xe", json=_hd("TX-T1"), headers=login("cntt")).status_code == 403


def test_tron_vong_tao_trinh_ct_duyet_lap_lenh():
    gd = login("gd.doixe")
    r = client.post("/api/v1/fleet/hop-dong-thue-xe", json=_hd("TX-T2"), headers=gd)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    # chưa duyệt thì chưa lập lệnh được
    assert client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/lap-lenh", headers=gd).status_code == 422
    assert client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/trinh", json={}, headers=gd).status_code == 200
    # TGĐ thấy, không duyệt được
    ds = client.get("/api/v1/fleet/hop-dong-thue-xe", headers=login("tgd")).json()
    dong = next(x for x in ds["rows"] if x["id"] == tid)
    assert dong["trang_thai"] == "cho_duyet" and ds["duoc_duyet"] is False
    assert client.post(f"/api/v1/tours/{tid}/approve", json={}, headers=login("tgd")).status_code in (403, 422)
    r = client.post(f"/api/v1/tours/{tid}/approve", json={}, headers=login("chutich"))
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/lap-lenh", headers=gd)
    assert r.status_code == 200, r.text
    dn = r.json()["de_nghi_id"]
    assert client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/lap-lenh", headers=gd).json()["de_nghi_id"] == dn  # dùng lại
    xe = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={D1}&date_to={D1 + timedelta(days=1)}&so_khach=20",
                    headers=gd).json()["phuong_an"]
    if not xe:
        pytest.skip("dữ liệu mẫu không còn xe hợp lệ")
    body = {"tour_id": tid, "vehicle_id": xe[0]["vehicle_id"], "date_from": str(D1), "date_to": str(D1 + timedelta(days=1)),
            "de_nghi_id": dn, "so_khach": 20}
    r = client.post("/api/v1/dispatch", json=body, headers=gd)
    assert r.status_code == 201, r.text
    # số lệnh không quá số xe hợp đồng xin (1)
    assert client.post("/api/v1/dispatch", json={**body, "vehicle_id": (xe[1] if len(xe) > 1 else xe[0])["vehicle_id"]},
                       headers=gd).status_code == 422


def test_duoi_bien_phai_giai_trinh_va_van_chi_ct_duyet():
    gd = login("gd.doixe")
    tid = client.post("/api/v1/fleet/hop-dong-thue-xe", json=_hd("TX-T3", gia=5_000_000, chi_phi=4_900_000), headers=gd).json()["id"]
    r = client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/trinh", json={}, headers=gd)
    assert r.status_code == 422 and "giải trình" in r.json()["detail"]
    r = client.post(f"/api/v1/fleet/hop-dong-thue-xe/{tid}/trinh",
                    json={"giai_trinh": "Khách quen, giữ quan hệ — đi kèm hợp đồng tháng sau giá tốt hơn"}, headers=gd)
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/tours/{tid}/approve", json={}, headers=login("chutich")).status_code == 200


def test_hop_dong_doi_xe_vao_nhom_thue_xe_va_trang_con_khai_quyen():
    from app.services import access as AC
    assert "/lenh-dieu-xe/thue-xe" in AC.MAN_CON_LENH_DIEU_XE
