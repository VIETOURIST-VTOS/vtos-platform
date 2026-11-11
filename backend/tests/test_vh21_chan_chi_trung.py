# -*- coding: utf-8 -*-
"""VH-21 · CHẶN CHI TRÙNG HAI ĐƯỜNG (Chủ tịch chốt 11/11/2026, thử thật phiếu #866 / DC2611-0001).

  1. Số đề xuất chi KHÔNG được vượt khoản gốc đã gắn (630.000 xin trên khoản gốc 600.000 → chặn).
  2. Đề xuất chi là đường chi chuẩn: khoản tài xế ứng đã có đề xuất chi thì tờ quyết toán Mẫu 2 trừ ra
     khỏi «tài xế còn được nhận» — Kế toán không chi lại ở quyết toán.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh21_kg.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh21_kg.db"):
    os.remove("test_vh21_kg.db")

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
GD = "gd.doixe.vh21"


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
            db.add(User(username=GD, full_name="GĐ đội xe thử VH21", role="gd_doi_xe", department="doi_xe",
                        staff_code="VH21GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
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
    khac = Vehicle(code="XE-VH21-B", plate="51B-888.21")
    db.add(khac); db.flush()
    t = Trip(vehicle_id=v.id, ten_tour="Chuyến VH21", ngay_di=date(2026, 11, 5), ngay_ve=date(2026, 11, 6),
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




def _chuan_bi_vh21():
    from app.models.fleet import Trip, TripCost
    from app.models.hr import Vehicle
    db = SessionLocal()
    v = db.execute(select(Vehicle).where(Vehicle.plate == CTX["bien_so"])).scalars().first()
    t = Trip(vehicle_id=v.id, ten_tour="Đà Lạt VH21", ngay_di=date(2026, 11, 8), ngay_ve=date(2026, 11, 10),
             created_by="phep_thu", quyet_toan=False)
    db.add(t); db.flush()
    ctp = TripCost(trip_id=t.id, kind="cong_tac_phi", amount=600_000, tra_bang="tai_xe_tien_mat")
    gx = TripCost(trip_id=t.id, kind="giu_xe", amount=30_000, tra_bang="tai_xe_tien_mat")
    dau = TripCost(trip_id=t.id, kind="dau", amount=5_599_390, tra_bang="the_cong_ty")
    db.add_all([ctp, gx, dau]); db.commit()
    CTX.update(trip=t.id, ctp=f"tc:{ctp.id}", gx=f"tc:{gx.id}")
    db.close()


def _tong():
    from app.models.fleet import Trip
    from app.services import quyet_toan_chuyen as QT
    db = SessionLocal()
    try:
        return QT.tong(db, db.get(Trip, CTX["trip"]))
    finally:
        db.close()


def test_1_vuot_khoan_goc_bi_chan():
    _chuan_bi_vh21()
    r = _lap(ma_khoan_goc=CTX["ctp"], so_tien=630_000, nhom="Tài xế (công tác phí, lương)", loai="hoan_ung")
    assert r.status_code == 422 and "vượt khoản gốc" in r.text, r.text


def test_2_quyet_toan_tru_phan_da_co_de_xuat_chi():
    g = _tong()
    assert g["tai_xe_chi"] == 630_000 and g["tai_xe_da_de_nghi_chi"] == 0 and g["tai_xe_con_nhan"] == 630_000
    r = _lap(ma_khoan_goc=CTX["ctp"], so_tien=600_000, nhom="Tài xế (công tác phí, lương)", loai="hoan_ung")
    assert r.status_code == 201, r.text
    g = _tong()
    # tổng tài xế chi vẫn đủ 630.000 (đối chiếu giấy), nhưng còn nhận chỉ 30.000 — 600.000 chi ở đề xuất chi
    assert g["tai_xe_chi"] == 630_000 and g["tai_xe_da_de_nghi_chi"] == 600_000 and g["tai_xe_con_nhan"] == 30_000
    assert g["tong_chi_phi_tour"] == 6_229_390, "chi phí tour không đổi"
