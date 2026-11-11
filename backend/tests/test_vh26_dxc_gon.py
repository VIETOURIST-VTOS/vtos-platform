# -*- coding: utf-8 -*-
"""VH-26 · MÀN ĐỀ XUẤT CHI GỌN (Chủ tịch 12/11/2026 01:06, 8 ảnh).

  1. Danh sách: mỗi đề xuất MỘT dòng ngang — bên nhận + nội dung một dòng, «xem thêm» mở chi tiết.
  2–4, 8. Bỏ các ghi chú dài (nháp lưu trong máy, «Cùng danh sách…», «Phiếu là một đề nghị chi 05-TT…»).
  5. Khoản gốc: tìm theo mã tour / mã phiếu (`/fleet/khoan-goc?q=`), và lựa chọn «xe thuê ngoài» tự ghi mã tour.
  6. Số hoá đơn bắt buộc (trừ tạm ứng / nạp quỹ).
  7. Ô tích xác nhận → nút chữ «Xác nhận».
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh26_dxc.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh26_dxc.db"):
    os.remove("test_vh26_dxc.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

client = TestClient(app)
TOK: dict = {}
CTX: dict = {}
GD = "gd.doixe.vh26"
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")


def _web(*p):
    with open(os.path.join(WEB, *p), encoding="utf-8") as f:
        return f.read()


def login(u: str) -> dict:
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from app.models.core import User
        from app.models.hr import Vehicle
        from app.models.fleet import Trip, TripCost
        from app.core.security import hash_password
        db = SessionLocal()
        db.add(User(username=GD, full_name="GĐ đội xe thử VH26", role="gd_doi_xe", department="doi_xe",
                    staff_code="VH26GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        v = Vehicle(code="XE-VH26", plate="51B-262.62")
        db.add(v)
        db.flush()
        for i, ma in enumerate(["VH26-DALAT-01", "VH26-NHATRANG-02"]):
            t = Trip(vehicle_id=v.id, ma_phieu=ma, ten_tour=f"Tour thử {ma}", ngay_di=date(2026, 11, 1 + i),
                     ngay_ve=date(2026, 11, 2 + i))
            db.add(t)
            db.flush()
            db.add(TripCost(trip_id=t.id, kind="cau_duong", amount=100_000 * (i + 1)))
        db.commit()
        CTX["xe"] = v.id
        db.close()
        yield


def test_tim_khoan_goc_theo_ma_tour():
    h = login(GD)
    tat = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe']}", headers=h)
    assert tat.status_code == 200, tat.text
    assert len(tat.json()["rows"]) == 2
    r = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe']}&q=nhatrang", headers=h)
    assert r.status_code == 200, r.text
    ten = [x["ten"] for x in r.json()["rows"]]
    assert len(ten) == 1 and "VH26-NHATRANG-02" in ten[0], ten
    r = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe']}&q=khongco", headers=h)
    assert r.json()["rows"] == []


def test_man_hinh_gon_theo_chu_tich():
    lap = _web("components", "doixe", "BonBuocDeXuatChi.tsx")
    ds = _web("components", "doixe", "DeXuatChiTaiCho.tsx")
    bb = _web("components", "doixe", "BonBuoc.tsx")
    for cu in ("Nháp tự lưu trong máy này", "Nháp không nằm trên máy chủ", "Phiếu là một đề nghị chi 05-TT"):
        assert cu not in lap, cu
    assert "Cùng danh sách dù mở từ nút trên tổng quan" not in ds
    assert "xem thêm" in ds and "dxc-dong" in ds                       # một dòng + xem thêm
    assert "&q=${encodeURIComponent(" in lap and "Xe thuê ngoài" in lap  # tìm mã tour + xe thuê ngoài
    assert "Ghi số hoá đơn — bắt buộc" in lap                            # số hoá đơn bắt buộc
    assert '"Xác nhận"' in bb and 'type="checkbox"' not in bb.split("export function OXacNhan")[1][:400]
