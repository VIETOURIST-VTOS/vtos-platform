# -*- coding: utf-8 -*-
"""Đội xe · CHỐNG GHI CHI PHÍ HAI LẦN (Chủ tịch duyệt bản xem trước 10/11/2026, phần D).

  1. Khoản gốc CHỌN từ sổ của xe (`tc:<id>` dòng chi phí chuyến, `bd:<id>` phiếu bảo dưỡng); mã gõ tay bị từ chối.
  2. Khoản gốc của xe khác bị từ chối.
  3. Một khoản gốc chỉ một đề nghị chi — lần hai bị chặn, nêu mã DC cũ; hồ sơ đã từ chối thì nhả khoản gốc.
  4. Cùng số chứng từ ở đề nghị chi khác → cảnh báo (không chặn).
  5. Dòng chi phí chuyến hiện «đã có đề nghị chi DC…»; danh sách khoản gốc đánh dấu khoản đã dùng.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_cg1_kg.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cg1_kg.db"):
    os.remove("test_cg1_kg.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import Param  # noqa: E402
from app.models.ops import PaymentRequest  # noqa: E402
from app.services import ops as O  # noqa: E402
from app.services import rules as R  # noqa: E402

client = TestClient(app)
TOK: dict = {}
CTX: dict = {}
GD = "gd.doixe.cg1"


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
        from app.core.security import hash_password
        db = SessionLocal()
        if db.execute(select(User).where(User.username == GD)).scalars().first() is None:
            db.add(User(username=GD, full_name="GĐ đội xe thử CG1", role="gd_doi_xe", department="doi_xe",
                        staff_code="CG1GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        v = db.execute(select(Vehicle)).scalars().first()
        if v is None:
            v = Vehicle(code="XE-CG1", plate="51B-777.77")
            db.add(v)
        for p in db.execute(select(Param).where(Param.key == O.NGUONG_CHU_TICH_KEY,
                                                Param.proposed_by == "phep_thu")).scalars().all():
            db.delete(p)
        db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value="100000000", label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                     effective_from=date(2026, 9, 2), source="phép thử CG1", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="phep_thu"))
        db.commit()
        CTX["bien_so"] = v.plate
        db.close()
        R.clear_param_cache()
        yield


def _lap(**kw):
    body = {"so_tien": 1_200_000, "noi_dung": "Hoàn tiền dầu chuyến", "nguoi_thu_huong": "Tài xế A",
            "ma_so_thue": "", "chung_tu": "", "pham_vi": "xe", "bien_so": CTX["bien_so"],
            "loai": "thanh_toan", "nhom": "Sửa chữa – bảo dưỡng", "can_cu_so_tien": "Theo chứng từ"}
    body.update(kw)
    return client.post("/api/v1/fleet/de-nghi-chi", json=body, headers=login(GD))


def _chuan_bi():
    from app.models.fleet import Maintenance, Trip, TripCost
    from app.models.hr import Vehicle
    db = SessionLocal()
    v = db.execute(select(Vehicle).where(Vehicle.plate == CTX["bien_so"])).scalars().first()
    khac = Vehicle(code="XE-CG1-B", plate="51B-888.88")
    db.add(khac); db.flush()
    t = Trip(vehicle_id=v.id, ten_tour="Chuyến CG1", ngay_di=date(2026, 11, 5), ngay_ve=date(2026, 11, 6),
             created_by="phep_thu")
    t2 = Trip(vehicle_id=khac.id, ten_tour="Chuyến xe khác", ngay_di=date(2026, 11, 5), ngay_ve=date(2026, 11, 5),
              created_by="phep_thu")
    db.add_all([t, t2]); db.flush()
    c = TripCost(trip_id=t.id, kind="nhien_lieu", amount=1_200_000, chung_tu="HD-DAU-1")
    c2 = TripCost(trip_id=t2.id, kind="nhien_lieu", amount=500_000)
    b = Maintenance(vehicle_id=v.id, ngay=date(2026, 11, 1), noi_dung="Thay dầu máy", so_tien=900_000)
    db.add_all([c, c2, b]); db.commit()
    CTX.update(tc=f"tc:{c.id}", tc_khac=f"tc:{c2.id}", bd=f"bd:{b.id}", trip=t.id, xe_id=v.id)
    db.close()


def test_1_ma_go_tay_va_xe_khac_bi_tu_choi():
    _chuan_bi()
    r = _lap(ma_khoan_goc="PBD-001")
    assert r.status_code == 422 and "chọn trong danh sách" in r.text
    r = _lap(ma_khoan_goc=CTX["tc_khac"])
    assert r.status_code == 422 and "xe khác" in r.text


def test_2_mot_khoan_goc_mot_de_nghi_chi():
    r = _lap(ma_khoan_goc=CTX["tc"], chung_tu="HD-DAU-1")
    assert r.status_code == 201, r.text
    CTX["dc"] = r.json()["code"]
    CTX["dc_id"] = r.json()["id"]
    r = _lap(ma_khoan_goc=CTX["tc"], so_tien=1_000_000, chung_tu="HD-DAU-1B")
    assert r.status_code == 422 and CTX["dc"] in r.text and "một khoản gốc chỉ một đề nghị chi" in r.text


def test_3_tu_choi_thi_nha_khoan_goc():
    r = client.post(f"/api/v1/payment-requests/{CTX['dc_id']}/step",
                    json={"action": "reject", "reason": "lập nhầm"}, headers=login("chutich"))
    assert r.status_code == 200, r.text
    r = _lap(ma_khoan_goc=CTX["tc"], chung_tu="HD-DAU-1")
    assert r.status_code == 201, r.text
    CTX["dc"] = r.json()["code"]


def test_4_chung_tu_trung_canh_bao_khong_chan():
    r = _lap(ma_khoan_goc=CTX["bd"], chung_tu="HD-DAU-1", so_tien=900_000)
    assert r.status_code == 201, r.text
    j = r.json()
    assert CTX["dc"] in j["chung_tu_trung"] and "đã có ở" in j["message"]


def test_5_dong_chi_phi_va_danh_sach_khoan_goc_hien_ma_dc():
    r = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe_id']}", headers=login(GD))
    assert r.status_code == 200, r.text
    ds = {x["ma"]: x for x in r.json()["rows"]}
    assert ds[CTX["tc"]]["de_nghi_chi"] == CTX["dc"] and ds[CTX["bd"]]["de_nghi_chi"]
    assert CTX["tc_khac"] not in ds                                    # chỉ khoản của chính xe
    ch = client.get(f"/api/v1/fleet/chuyen?vehicle_id={CTX['xe_id']}", headers=login("ketoan")).json()
    t = next(x for x in ch if x["id"] == CTX["trip"])
    assert t["chi_phi"][0]["de_nghi_chi"] == CTX["dc"]
    db = SessionLocal()
    from app.models.fleet import Trip
    from app.services import quyet_toan_chuyen as QT
    d = QT.xem(db, db.get(Trip, CTX["trip"]))
    db.close()
    assert d["chi_phi"][0]["de_nghi_chi"] == CTX["dc"]


def _web(*p):
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return open(os.path.join(goc, "web", *p), encoding="utf-8").read()


def test_6_man_hinh_chon_khoan_goc():
    s = _web("components", "doixe", "BonBuocDeXuatChi.tsx")
    assert "/fleet/khoan-goc?xe_id=" in s and "disabled={!!k.de_nghi_chi" in s      # VH-29: || công ty đã trả
    assert "đã có đề nghị chi" in _web("components", "QuyetToanChuyen.tsx")
