# -*- coding: utf-8 -*-
"""VH-24 · HAI NÚT «CÔNG VIỆC» / «CHỜ DUYỆT» CÓ SỐ (Chủ tịch duyệt 12/11/2026, chốt 1.1.1).

  1. `GET /dashboard/dem`: số «Chờ duyệt» chỉ đếm việc PHẢI BẤM; dòng «để xem» nằm riêng, không cộng vào số.
  2. Có đề nghị chi mới chờ Chủ tịch ký thì số tăng (sau khi bản nhớ 60 giây hết hạn).
  3. Ai đăng nhập cũng gọi được; mỗi người ra việc của mình.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh24_dem.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh24_dem.db"):
    os.remove("test_vh24_dem.db")

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
GD = "gd.doixe.vh24"


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
            db.add(User(username=GD, full_name="GĐ đội xe thử VH24", role="gd_doi_xe", department="doi_xe",
                        staff_code="VH24GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
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




def test_1_dem_chi_viec_phai_bam_va_tang_khi_co_de_nghi_moi():
    from app.api.v1 import routes as RT
    RT._DEM_CACHE.clear()
    d0 = client.get("/api/v1/dashboard/dem", headers=login("chutich")).json()
    assert set(d0) >= {"cho_duyet", "so_cho_duyet", "de_xem", "cong_viec", "so_cong_viec"}
    assert d0["so_cho_duyet"] == sum(x["so"] for x in d0["cho_duyet"])
    assert all("để xem" not in x["label"] for x in d0["cho_duyet"]), "dòng để xem lọt vào số đỏ"
    r = _lap(so_tien=400_000, nhom="Tài xế (công tác phí, lương)", loai="hoan_ung", chung_tu="QT-24")
    assert r.status_code == 201, r.text
    RT._DEM_CACHE.clear()
    d1 = client.get("/api/v1/dashboard/dem", headers=login("chutich")).json()
    assert d1["so_cho_duyet"] == d0["so_cho_duyet"] + 1, (d0["cho_duyet"], d1["cho_duyet"])


def test_2_vai_khac_goi_duoc_va_khong_thay_viec_cua_chu_tich():
    r = client.get("/api/v1/dashboard/dem", headers=login(GD))
    assert r.status_code == 200
    assert not any("CHỦ TỊCH ký" in x["label"] for x in r.json()["cho_duyet"])


def test_3_dau_trang_chi_con_ten_ban_va_ngay():
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[2]
    dau = (goc / "web" / "components" / "DauManHinh01.tsx").read_text(encoding="utf-8")
    than = dau[dau.index("export function TieuDe"):]
    than = than[:than.index("export function", 1)]
    assert '"Bàn làm việc Chủ tịch HĐQT"' in dau
    for bo in ("In / Lưu PDF", "Quý và năm", "mh01-qd-nut"):
        assert bo not in than, f"{bo} sống lại trên đầu trang"
    shell = (goc / "web" / "components" / "Shell.tsx").read_text(encoding="utf-8")
    assert "/#viec-cua-toi" not in shell and "/#cho-toi-duyet" not in shell, "hai nút lại trỏ vào neo chết"
