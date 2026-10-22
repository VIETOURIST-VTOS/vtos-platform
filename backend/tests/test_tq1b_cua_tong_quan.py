# -*- coding: utf-8 -*-
"""TQ-1 · Hai cửa danh sách của mục «Vận hành & công việc» và các trường mới trên /dashboard."""
import os, sys

os.environ["DATABASE_URL"] = "sqlite:///./test_tq1b.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_tq1b.db", "test_tq1b.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    global client
    with TestClient(app) as c:
        client = c
        yield


def test_tq1b_1_dashboard_chu_tich_co_du_truong_moi():
    s = client.get("/api/v1/dashboard", params={"refresh": True}, headers=login("chutich")).json()["sections"]
    v = s["viec_van_hanh"]
    assert v["pham_vi"] == "toan_bo" and v["viec"] <= v["canh_bao"]
    assert sum(m["viec"] for m in v["theo_muc"]) == v["viec"]
    c = s["cho_quyet_toan"]
    assert c["tong"] == c["ket_thuc"] + c["da_dong_so"]
    assert isinstance(s["qua_han_qt_tong"], int) and isinstance(s["thieu_lich"], int)


def test_tq1b_2_danh_sach_viec_khop_o_va_tinh_lai():
    o = client.get("/api/v1/dashboard", params={"refresh": True}, headers=login("chutich")).json()["sections"]["viec_van_hanh"]
    d = client.get("/api/v1/dashboard/viec", params={"co": 200}, headers=login("chutich")).json()
    assert d["tong"]["viec"] == o["viec"] and d["so_dong"] == o["viec"]
    assert d["tong"]["luc"], "danh sách kèm mốc tính lại"


def test_tq1b_3_vai_han_che_chi_thay_phan_cua_minh():
    tat = client.get("/api/v1/dashboard/viec", headers=login("chutich")).json()["tong"]
    kd = client.get("/api/v1/dashboard/viec", headers=login("kd.hoa")).json()["tong"]
    assert kd["pham_vi"] == "vai:nv_kd" and kd["canh_bao"] <= tat["canh_bao"]


def test_tq1b_4_qua_han_cung_bo_vai_voi_o():
    assert client.get("/api/v1/dashboard/qua-han-quyet-toan", headers=login("kd.hoa")).status_code == 403
    r = client.get("/api/v1/dashboard/qua-han-quyet-toan", headers=login("chutich"))
    assert r.status_code == 200 and r.json()["tong"] >= len(r.json()["dong"])
    s = client.get("/api/v1/dashboard", params={"refresh": True}, headers=login("chutich")).json()["sections"]
    assert r.json()["tong"] == s["qua_han_qt_tong"], "ô và danh sách dùng cùng một điều kiện"
