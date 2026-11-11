# -*- coding: utf-8 -*-
"""VH-34 · đề xuất chi bản 2 đợt 3 (Chủ tịch duyệt 12/11/2026): tài xế xem tiền trả cho mình; lịch sử
phiên bản; KT trưởng từ chối được («Đã chi» vẫn chỉ Kế toán — NL-2). Khung dựng từ phép thử TB6.

05-TT · TRẢ BỔ SUNG + CHI MỘT PHẦN (Chủ tịch duyệt bản xem trước 10/11/2026, áp mọi đề nghị chi).

  1. «Trả bổ sung» phải có lý do; hồ sơ về người lập, giữ nguyên mã; chữ ký cũ xoá, bản trước lưu ở `lan_tra`.
  2. Chỉ người lập gửi lại; gửi lại thì đi lại tuyến từ đầu (đội xe: lên lại Chủ tịch; loại khác: bộ phận).
  3. Chỉ người đang giữ bước trả được; hồ sơ máy lập, đã chi một phần, đã ghi công nợ thì không trả.
  4. Chi nhiều lần: tổng không vượt số duyệt; mỗi lần một UNC; mỗi lần một bút toán đúng số lần ấy;
     trạng thái giữ «cho_chi» tới khi đủ rồi mới «da_chi».
  5. Bảng nợ phải trả và dòng tiền chỉ tính phần CÒN phải chi.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_vh34_tbs.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh34_tbs.db"):
    os.remove("test_vh34_tbs.db")

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
GD = "gd.doixe.vh34"


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
            db.add(User(username=GD, full_name="GĐ đội xe thử TB6", role="gd_doi_xe", department="doi_xe",
                        staff_code="TB6GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        v = db.execute(select(Vehicle)).scalars().first()
        if v is None:
            v = Vehicle(code="XE-TB6", plate="51B-666.66")
            db.add(v)
        for p in db.execute(select(Param).where(Param.key == O.NGUONG_CHU_TICH_KEY,
                                                Param.proposed_by == "phep_thu")).scalars().all():
            db.delete(p)
        db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value="100000000", label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                     effective_from=date(2026, 9, 2), source="phép thử TB6", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="phep_thu"))
        db.commit()
        CTX["bien_so"] = v.plate
        db.close()
        R.clear_param_cache()
        yield



TX = "taixe.vh34"


def _lap(**kw):
    body = {"so_tien": 600_000, "noi_dung": "Công tác phí chuyến thử", "nguoi_thu_huong": "Tài xế Thử VH34",
            "ma_so_thue": "", "chung_tu": f"HD-VH34-{len(CTX)}", "pham_vi": "xe", "bien_so": CTX["bien_so"],
            "loai": "hoan_ung", "nhom": "Tài xế (công tác phí, lương)", "can_cu_so_tien": "Theo chứng từ"}
    body.update(kw)
    r = client.post("/api/v1/fleet/de-nghi-chi", json=body, headers=login(GD))
    assert r.status_code == 201, r.text
    return r.json()


def _tai_xe():
    from app.models.core import User
    from app.models.hr import Employee
    from app.core.security import hash_password
    db = SessionLocal()
    u = User(username=TX, full_name="Tài xế Thử VH34", role="tai_xe", department="doi_xe", staff_code="VH34TX",
             password_hash=hash_password("Vtos@Demo#2026"), active=True)
    db.add(u); db.flush()
    e = Employee(code="NVVH34", full_name="Tài xế Thử VH34", user_id=u.id, department="doi_xe", position="tai_xe")
    db.add(e); db.commit()
    CTX["ma_nv"] = e.code
    db.close()


def test_1_tai_xe_xem_dung_phieu_cua_minh():
    _tai_xe()
    a = _lap(ben_nhan_ma=CTX["ma_nv"])
    b = _lap(nguoi_thu_huong="Tài xế Thử VH34 (tài xế)", so_tien=30_000)     # phiếu không có mã: khớp họ tên
    c = _lap(nguoi_thu_huong="Người khác", so_tien=50_000)
    r = client.get("/api/v1/nhan-lenh/tien-cua-toi", headers=login(TX))
    assert r.status_code == 200, r.text
    ma = {x["code"] for x in r.json()["rows"]}
    assert a["code"] in ma and b["code"] in ma and c["code"] not in ma, ma
    assert client.get("/api/v1/nhan-lenh/tien-cua-toi", headers=login(GD)).status_code == 403
    CTX["a"] = a


def test_2_lich_su_phien_ban():
    rid = CTX["a"]["id"]
    assert _buoc(rid, "tra_bo_sung", "chutich", reason="Tách gửi xe").status_code == 200
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{rid}/gui-lai", json={"so_tien": 570_000}, headers=login(GD))
    assert r.status_code == 200, r.text
    x = next(d for d in client.get("/api/v1/fleet/de-nghi-chi", headers=login("chutich")).json()["de_nghi"] if d["id"] == rid)
    pb = x["phien_ban"]
    assert [p["loai"] for p in pb] == ["lap", "tra", "gui_lai"], pb
    assert pb[1]["ly_do"] == "Tách gửi xe"
    assert pb[2]["ban"] == 2 and pb[2]["doi"][0]["o"] == "Số tiền" and pb[2]["doi"][0]["moi"] == 570_000, pb[2]


def test_3_ke_toan_truong_tu_choi_duoc_nhung_khong_bam_da_chi():
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    if db.execute(select(User).where(User.username == "ktt.vh34")).scalars().first() is None:
        db.add(User(username="ktt.vh34", full_name="KTT thử", role="ketoan_truong", department="ke_toan",
                    staff_code="VH34KT", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        db.commit()
    db.close()
    rid = CTX["a"]["id"]
    assert _buoc(rid, "approve", "chutich").status_code == 200
    from app.api.v1 import fleet as F
    from app.services import ops as O
    db = SessionLocal()
    p = db.get(PaymentRequest, rid)
    u = db.execute(select(User).where(User.username == "ktt.vh34")).scalars().first()
    viec = [v[0] for v in F._dxc_chi_tiet(db, u, p, p.doi_xe or {})["viec"]]
    db.close()
    assert "reject" in viec and "pay" not in viec, viec
    assert "ketoan_truong" not in O.VAI_GHI_DA_CHI


def _buoc(rid, hanh_dong, nguoi, **kw):
    return client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": hanh_dong, **kw}, headers=login(nguoi))
