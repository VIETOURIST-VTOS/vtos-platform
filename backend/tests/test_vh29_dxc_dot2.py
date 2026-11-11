# -*- coding: utf-8 -*-
"""VH-29 · ĐỀ XUẤT CHI BẢN 2 ĐỢT 2 (Chủ tịch duyệt bản xem trước; chọn đóng TT-TBS rồi sửa ops.py 12/11/2026).

  Nhiều khoản gốc trên một phiếu; số không vượt TỔNG; khoản công ty đã trả không làm khoản gốc; bên nhận
  ngoài danh mục thì gắn cờ cho Kế toán. (Mẫu dựng từ phép thử VH-21.)

VH-21 · CHẶN CHI TRÙNG HAI ĐƯỜNG (Chủ tịch chốt 11/11/2026, thử thật phiếu #866 / DC2611-0001).

  1. Số đề xuất chi KHÔNG được vượt khoản gốc đã gắn (630.000 xin trên khoản gốc 600.000 → chặn).
  2. Đề xuất chi là đường chi chuẩn: khoản tài xế ứng đã có đề xuất chi thì tờ quyết toán Mẫu 2 trừ ra
     khỏi «tài xế còn được nhận» — Kế toán không chi lại ở quyết toán.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh29_kg.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh29_kg.db"):
    os.remove("test_vh29_kg.db")

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
GD = "gd.doixe.vh29"


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
            db.add(User(username=GD, full_name="GĐ đội xe thử VH29", role="gd_doi_xe", department="doi_xe",
                        staff_code="VH29GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
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
    from app.models.fleet import Trip, TripCost
    from app.models.hr import Vehicle
    db = SessionLocal()
    v = db.execute(select(Vehicle).where(Vehicle.plate == CTX["bien_so"])).scalars().first()
    t = Trip(vehicle_id=v.id, ten_tour="Đà Lạt VH29", ngay_di=date(2026, 11, 8), ngay_ve=date(2026, 11, 10),
             created_by="phep_thu", quyet_toan=False)
    db.add(t); db.flush()
    ctp = TripCost(trip_id=t.id, kind="cong_tac_phi", amount=600_000, tra_bang="tai_xe_tien_mat")
    gx = TripCost(trip_id=t.id, kind="giu_xe", amount=30_000, tra_bang="tai_xe_tien_mat")
    dau = TripCost(trip_id=t.id, kind="dau", amount=5_599_390, tra_bang="the_cong_ty")
    db.add_all([ctp, gx, dau]); db.commit()
    CTX.update(trip=t.id, xe_id=v.id, ctp=f"tc:{ctp.id}", gx=f"tc:{gx.id}", dau=f"tc:{dau.id}")
    db.close()


def _tong():
    from app.models.fleet import Trip
    from app.services import quyet_toan_chuyen as QT
    db = SessionLocal()
    try:
        return QT.tong(db, db.get(Trip, CTX["trip"]))
    finally:
        db.close()


TX = dict(nhom="Tài xế (công tác phí, lương)", loai="hoan_ung")


def test_1_khoan_cong_ty_da_tra_khong_lam_khoan_goc():
    _chuan_bi()
    r = _lap(ma_khoan_goc_ds=[CTX["dau"]], so_tien=100_000, **TX)
    assert r.status_code == 422 and "công ty đã trả" in r.text, r.text
    kg = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe_id']}", headers=login(GD)).json()["rows"]
    assert next(k for k in kg if k["ma"] == CTX["dau"])["cong_ty_da_tra"]


def test_2_vuot_tong_nhieu_khoan_bi_chan():
    r = _lap(ma_khoan_goc_ds=[CTX["ctp"], CTX["gx"]], so_tien=640_000, **TX)
    assert r.status_code == 422 and "vượt khoản gốc" in r.text, r.text


def test_3_hai_khoan_mot_phieu_va_quyet_toan_tru_ca_hai():
    r = _lap(ma_khoan_goc_ds=[CTX["ctp"], CTX["gx"]], so_tien=630_000, nguoi_thu_huong="Người lạ VH29", **TX)
    assert r.status_code == 201, r.text
    ma = r.json()["code"]
    g = _tong()
    assert g["tai_xe_da_de_nghi_chi"] == 630_000 and g["tai_xe_con_nhan"] == 0
    # khoản thứ hai cũng đã khoá — không lập phiếu khác gắn nó được
    r2 = _lap(ma_khoan_goc_ds=[CTX["gx"]], so_tien=30_000, **TX)
    assert r2.status_code == 422 and ma in r2.text, r2.text
    kg = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe_id']}", headers=login(GD)).json()["rows"]
    assert next(k for k in kg if k["ma"] == CTX["gx"])["de_nghi_chi"] == ma
    x = next(d for d in client.get("/api/v1/fleet/de-nghi-chi", headers=login(GD)).json()["de_nghi"] if d["code"] == ma)
    assert x["khoan_goc"]["so_tien"] == 630_000 and len(x["khoan_goc_ds"]) == 2
    assert any("ngoài" in k["chu"] or "không có trong danh mục" in k["chu"] for k in x["kiem"]), x["kiem"]


def test_4_danh_muc_ben_nhan():
    r = client.get("/api/v1/fleet/ben-nhan-chon", headers=login(GD))
    assert r.status_code == 200 and isinstance(r.json()["rows"], list)
    assert all("so_tai_khoan" not in b for b in r.json()["rows"]), "không trả số tài khoản"
