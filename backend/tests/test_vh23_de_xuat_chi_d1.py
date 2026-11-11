# -*- coding: utf-8 -*-
"""VH-23 · ĐỀ XUẤT CHI ĐỘI XE BẢN 2, ĐỢT 1 (Chủ tịch duyệt 12/11/2026).

  1. Danh sách trả `viec` theo người: Chủ tịch thấy «Ký lệnh chi»; người lập không thấy nút ký phiếu mình.
  2. Ký / trả bổ sung / từ chối chạy ngay ở cửa đội xe `/fleet/de-nghi-chi/{id}/buoc`, cùng luật `ops.step`.
  3. `kiem` nói ra phiếu thiếu chứng từ; cửa bước không nhận đề nghị chi không phải của đội xe.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh23_dxc.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh23_dxc.db"):
    os.remove("test_vh23_dxc.db")

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
GD = "gd.doixe.vh23"


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
            db.add(User(username=GD, full_name="GĐ đội xe thử VH23", role="gd_doi_xe", department="doi_xe",
                        staff_code="VH23GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
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




def _ds(u):
    return client.get("/api/v1/fleet/de-nghi-chi", headers=login(u)).json()["de_nghi"]


def test_1_viec_theo_nguoi_va_ky_tai_cho():
    r = _lap(so_tien=500_000, nhom="Tài xế (công tác phí, lương)", loai="hoan_ung", chung_tu="QT-1")
    assert r.status_code == 201, r.text
    CTX["id"] = r.json()["id"]
    x = next(d for d in _ds("chutich") if d["id"] == CTX["id"])
    assert ["approve", "Ký lệnh chi"] in x["viec"] and any(a == "reject" for a, _ in x["viec"])
    assert any(k["muc"] == "vang" and "chứng từ" in k["chu"] for k in x["kiem"]), x["kiem"]
    assert x["can_mst"] is False, "phiếu trả tài xế không đòi MST"
    y = next(d for d in _ds(GD) if d["id"] == CTX["id"])
    assert not any(a == "approve" for a, _ in y["viec"])
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{CTX['id']}/buoc", json={"action": "approve"}, headers=login("chutich"))
    assert r.status_code == 200 and r.json()["trang_thai"] == "cho_chi", r.text


def test_2_tu_choi_phai_co_ly_do_va_tra_bo_sung():
    r = _lap(so_tien=300_000, nhom="Tài xế (công tác phí, lương)", loai="hoan_ung", chung_tu="QT-2")
    rid = r.json()["id"]
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{rid}/buoc", json={"action": "reject"}, headers=login("chutich"))
    assert r.status_code == 422
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{rid}/buoc", json={"action": "tra_bo_sung", "reason": "Thiếu vé gửi xe"},
                    headers=login("chutich"))
    assert r.status_code == 200 and r.json()["trang_thai"] == "tra_bo_sung", r.text
    y = next(d for d in _ds(GD) if d["id"] == rid)
    assert ["gui_lai", "Bổ sung & gửi lại"] in y["viec"]


def test_3_cua_buoc_chi_nhan_phieu_doi_xe():
    db = SessionLocal()
    p = db.execute(select(PaymentRequest).where(PaymentRequest.category != "chi_doi_xe")).scalars().first()
    db.close()
    if p is None:
        pytest.skip("không có đề nghị chi loại khác trong dữ liệu mẫu")
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{p.id}/buoc", json={"action": "approve"}, headers=login("chutich"))
    assert r.status_code == 404
