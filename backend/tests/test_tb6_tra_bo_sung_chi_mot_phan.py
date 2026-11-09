# -*- coding: utf-8 -*-
"""05-TT · TRẢ BỔ SUNG + CHI MỘT PHẦN (Chủ tịch duyệt bản xem trước 10/11/2026, áp mọi đề nghị chi).

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

os.environ["DATABASE_URL"] = "sqlite:///./test_tb6_tbs.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_tb6_tbs.db"):
    os.remove("test_tb6_tbs.db")

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
GD = "gd.doixe.tb6"


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


def _lap(**kw):
    body = {"so_tien": 9_000_000, "noi_dung": "Thay má phanh", "nguoi_thu_huong": "Garage Minh Phát",
            "ma_so_thue": "0312345678", "chung_tu": f"HD-TB6-{len(CTX)}", "pham_vi": "xe", "bien_so": CTX["bien_so"],
            "loai": "thanh_toan", "nhom": "Sửa chữa – bảo dưỡng", "can_cu_so_tien": "Theo báo giá"}
    body.update(kw)
    r = client.post("/api/v1/fleet/de-nghi-chi", json=body, headers=login(GD))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _buoc(rid, hanh_dong, nguoi, **kw):
    return client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": hanh_dong, **kw}, headers=login(nguoi))


def _unc(rid, n):
    from app.models.attachments import Attachment
    db = SessionLocal()
    p = db.get(PaymentRequest, rid)
    p.has_document = True
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id=p.code, loai="unc", ten_tep=f"unc{n}.pdf",
                      checksum=f"tb6-{rid}-{n}", khoa_luu=f"unc/tb6/{rid}/{n}"))
    db.commit()
    db.close()


def _p(rid):
    db = SessionLocal()
    p = db.get(PaymentRequest, rid)
    db.expunge(p)
    db.close()
    return p


# ───────────────────────────────────────────── 1–3. trả bổ sung
def test_1_tra_bo_sung_bat_ly_do_va_dung_nguoi():
    rid = _lap()
    CTX["tra"] = rid
    r = _buoc(rid, "tra_bo_sung", "chutich")
    assert r.status_code == 422 and "lý do" in r.text
    r = _buoc(rid, "tra_bo_sung", "ketoan", reason="thiếu báo giá")     # chưa tới bước Kế toán
    assert r.status_code == 422 and "đang giữ bước" in r.text
    r = _buoc(rid, "tra_bo_sung", "chutich", reason="Bổ sung báo giá thứ hai")
    assert r.status_code == 200, r.text
    p = _p(rid)
    assert p.status == "tra_bo_sung" and p.reject_reason == "Bổ sung báo giá thứ hai"
    assert len(p.lan_tra) == 1 and p.lan_tra[0]["buoc"] == "cho_duyet" and p.lan_tra[0]["ban_truoc"]["amount"] == 9_000_000
    assert p.tp_by == "" and not p.signed_chutich


def test_2_chi_nguoi_lap_gui_lai_va_di_lai_tu_dau():
    rid = CTX["tra"]
    r = client.post(f"/api/v1/payment-requests/{rid}/gui-lai", json={"amount": 8_500_000}, headers=login("ketoan"))
    assert r.status_code == 403                                           # Kế toán không phải vai lập
    r = client.post(f"/api/v1/payment-requests/{rid}/gui-lai", json={"amount": 8_500_000}, headers=login("hcns"))
    assert r.status_code == 422 and "người lập" in r.text                 # vai lập được, nhưng không phải người lập
    r = client.post(f"/api/v1/fleet/de-nghi-chi/{rid}/gui-lai",
                    json={"so_tien": 8_500_000, "can_cu": "Báo giá 2 nơi"}, headers=login(GD))
    assert r.status_code == 200, r.text
    p = _p(rid)
    assert p.status == "cho_duyet" and p.amount == 8_500_000 and p.doi_xe["can_cu"] == "Báo giá 2 nơi"
    assert p.lan_tra[0]["da_sua"] == ["amount"] and p.lan_tra[0]["gui_lai_luc"]
    assert p.code.startswith("DC")                                        # cùng mã, không lập hồ sơ mới
    assert _buoc(rid, "approve", "chutich").status_code == 200            # Chủ tịch ký lại từ đầu


def test_3_khong_tra_ho_so_da_chi_mot_phan():
    rid = CTX["tra"]
    _unc(rid, 1)
    r = _buoc(rid, "pay", "ketoan", hinh_thuc_tt="chuyen_khoan", so_tien=3_000_000, reason="GD-1")
    assert r.status_code == 200, r.text
    r = _buoc(rid, "tra_bo_sung", "ketoan", reason="sai số")
    assert r.status_code == 422 and "đã chi" in r.text
    r = _buoc(rid, "reject", "ketoan", reason="sai số")
    assert r.status_code == 422 and "phần đã ra" in r.text


# ───────────────────────────────────────────── 4. chi một phần
def test_4_chi_nhieu_lan_khong_vuot_moi_lan_mot_unc_mot_but_toan():
    rid = CTX["tra"]
    p = _p(rid)
    assert p.status == "cho_chi" and p.da_chi_tien == 3_000_000 and len(p.lan_chi) == 1
    j = client.get("/api/v1/payment-requests?status=cho_chi", headers=login("ketoan")).json()
    x = next(r for r in j if r["id"] == rid)
    assert x["chi_mot_phan"] and x["con_phai_chi"] == 5_500_000 and "một phần" in x["next"]
    # lần 2 chưa có UNC riêng → chặn
    r = _buoc(rid, "pay", "ketoan", hinh_thuc_tt="chuyen_khoan", so_tien=1_000_000)
    assert r.status_code == 422 and "UNC" in r.text
    _unc(rid, 2)
    r = _buoc(rid, "pay", "ketoan", hinh_thuc_tt="chuyen_khoan", so_tien=6_000_000)
    assert r.status_code == 422 and "vượt phần còn phải chi" in r.text
    r = _buoc(rid, "pay", "ketoan", hinh_thuc_tt="tien_mat", reason="PC-2")     # rỗng = chi hết phần còn lại
    assert r.status_code == 200, r.text
    p = _p(rid)
    assert p.status == "da_chi" and p.da_chi_tien == 8_500_000 and len(p.lan_chi) == 2
    from app.models.accounting import JournalEntry, JournalLine
    db = SessionLocal()
    tien = []
    for lc in p.lan_chi:
        dong = db.execute(select(JournalLine).where(JournalLine.entry_id == lc["entry_id"])).scalars().all()
        tien.append(sum(float(d.debit or 0) for d in dong))
        assert db.get(JournalEntry, lc["entry_id"]) is not None
    db.close()
    assert tien == [3_000_000, 5_500_000]
    assert [x["hinh_thuc"] for x in p.lan_chi] == ["chuyen_khoan", "tien_mat"]


def test_5_no_phai_tra_chi_tinh_phan_con_lai():
    from app.services import debts as D
    rid = _lap(so_tien=4_000_000, chung_tu="HD-TB6-NO")
    assert _buoc(rid, "approve", "chutich").status_code == 200
    db = SessionLocal()
    truoc = D.phai_tra_ncc(db)["tong_phai_tra"]
    db.close()
    _unc(rid, 1)
    assert _buoc(rid, "pay", "ketoan", hinh_thuc_tt="chuyen_khoan", so_tien=1_000_000).status_code == 200
    db = SessionLocal()
    assert D.phai_tra_ncc(db)["tong_phai_tra"] == truoc - 1_000_000
    db.close()


def test_6_ho_so_may_lap_khong_tra_bo_sung():
    db = SessionLocal()
    p = db.get(PaymentRequest, CTX["tra"])
    p.category, p.status = "tra_ncc_thu_ho", "cho_kt"
    from app.models.core import User
    u = db.execute(select(User).where(User.username == "ketoan")).scalars().first()
    with pytest.raises(ValueError, match="máy tự lập"):
        O._tra_bo_sung(db, u, p, "thiếu")
    db.rollback()
    db.close()


# ───────────────────────────────────────────── giao diện
def _web(*p):
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return open(os.path.join(goc, "web", *p), encoding="utf-8").read()


def test_7_man_hinh_co_nut_va_o_so_tien():
    s = _web("app", "expenses", "page.tsx")
    for k in ('"Trả bổ sung", "tra_bo_sung"', '"Bổ sung & gửi lại", "gui_lai"', "Số tiền chi lần này",
              "/gui-lai", "Đã chi một phần", "so_tien"):
        assert k in s, k
    assert "/fleet/de-nghi-chi/${sua.id}/gui-lai" in _web("components", "doixe", "DeXuatChiTaiCho.tsx")

