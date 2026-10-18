# -*- coding: utf-8 -*-
"""EM-1 · Email công việc trên /access, và nguồn liên lạc của báo động khủng hoảng.

Chủ tịch duyệt bản xem thử 18/10/2026: cột riêng trên tài khoản (tách email cá nhân của hồ sơ),
đuôi BẮT BUỘC @vietourist.com.vn, CNTT/HCNS/Chủ tịch/TGĐ ghi (cùng bộ vai cửa pháp nhân), hai tài
khoản đang hoạt động không trùng địa chỉ. Báo động: email đọc cột này, ZNS đọc SĐT hồ sơ nhân sự.
Chưa có bộ gửi thật nên mọi kênh vẫn trả thất bại CÓ LÝ DO — không bao giờ báo thành công giả.
"""
import os, re, sys
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_em1.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_em1.db", "test_em1.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.core import AuditLog, User
from app.services import email_cong_viec as EM

BE = Path(__file__).resolve().parents[1]
WEB = BE.parent / "web" / "app" / "access" / "page.tsx"
MK = "em1_123456"
client = TestClient(app)
ID = {}


@pytest.fixture(scope="module", autouse=True)
def _du_lieu():
    global client
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for ten, vai in (("em1_cntt", "cntt"), ("em1_kd", "nv_kd"), ("em1_a", "nv_dh"), ("em1_b", "nv_dh")):
            u = db.execute(select(User).where(User.username == ten)).scalars().first()
            if u is None:
                u = User(username=ten, full_name=ten, role=vai, password_hash=hash_password(MK), active=True)
                db.add(u); db.flush()
            ID[ten] = u.id
        db.commit(); db.close()
        yield


def _dn(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ghi(ai, ai_bi, email):
    return client.put(f"/api/v1/access/users/{ID[ai_bi]}/email-cong-viec",
                      json={"email_cong_viec": email}, headers=_dn(ai))


# ---------------------------------------------------------------- luật đuôi, phép tính thuần
def test_em1_1_duoi_bat_buoc():
    assert EM.chuan("  Nv.A@VIETOURIST.com.vn ") == "nv.a@vietourist.com.vn"
    assert EM.chuan("") == "" and EM.chuan(None) == ""
    for sai in ("a@gmail.com", "a@vietourist.com", "@vietourist.com.vn", "a@notvietourist.com.vn",
                "a@vietourist.com.vn.evil.com", "a b@vietourist.com.vn", "khong-phai-email"):
        with pytest.raises(EM.EmailSai):
            EM.chuan(sai)


# ---------------------------------------------------------------- cửa ghi
def test_em1_2_cntt_ghi_duoc_va_de_vet():
    r = _ghi("em1_cntt", "em1_a", "NV.A@vietourist.com.vn")
    assert r.status_code == 200, r.text
    assert r.json()["email_cong_viec"] == "nv.a@vietourist.com.vn"
    from app.db.session import SessionLocal
    db = SessionLocal()
    v = db.execute(select(AuditLog).where(AuditLog.entity == "user:em1_a")
                   .order_by(AuditLog.id.desc())).scalars().first()
    assert v is not None and v.after == {"email_cong_viec": "nv.a@vietourist.com.vn"}
    assert v.actor == "em1_cntt"
    db.close()
    rows = client.get("/api/v1/access/accounts", headers=_dn("em1_cntt")).json()["rows"]
    assert [x["email_cong_viec"] for x in rows if x["id"] == ID["em1_a"]] == ["nv.a@vietourist.com.vn"]


def test_em1_3_sai_duoi_la_422_khong_ghi():
    r = _ghi("em1_cntt", "em1_b", "nv.b@gmail.com")
    assert r.status_code == 422 and "@vietourist.com.vn" in r.json()["detail"]


def test_em1_4_khong_trung_dia_chi():
    assert _ghi("em1_cntt", "em1_a", "trung@vietourist.com.vn").status_code == 200
    r = _ghi("em1_cntt", "em1_b", "Trung@vietourist.com.vn")
    assert r.status_code == 422 and "em1_a" in r.json()["detail"]


def test_em1_5_de_trong_duoc():
    assert _ghi("em1_cntt", "em1_a", "").status_code == 200


def test_em1_6_vai_khac_khong_ghi_duoc():
    assert _ghi("em1_kd", "em1_b", "x@vietourist.com.vn").status_code == 403


# ---------------------------------------------------------------- báo động
def _db_mem():
    from app.db.session import Base
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def test_em1_7_kenh_email_doc_cot_moi():
    from app.services import bao_dong_khung_hoang as BD
    u = User(username="x", full_name="x", role="chutich", password_hash="x")
    assert BD._kenh_email(None, None, u, "") == (False, "thieu_email_cong_viec", "")
    u.email_cong_viec = "x@vietourist.com.vn"
    assert BD._kenh_email(None, None, u, "") == (False, "chua_co_hop_thu_gui", "")


def test_em1_8_kenh_zns_doc_sdt_ho_so(monkeypatch):
    from app.models.hr import Employee
    from app.models.hrm import EmployeeProfile
    from app.services import bao_dong_khung_hoang as BD
    db = _db_mem()
    u = User(username="ld", full_name="ld", role="chutich", password_hash="x", staff_code="E1")
    db.add(u); db.flush()
    monkeypatch.setattr(BD.ZL, "configured", lambda _db: {"zns_templates": {}})
    assert BD._kenh_zns(db, None, u, "")[1] == "chua_cau_hinh_mau_zns"
    monkeypatch.setattr(BD.ZL, "configured", lambda _db: {"zns_templates": {"bao_dong_khung_hoang": "1"}})
    assert BD._kenh_zns(db, None, u, "")[1] == "thieu_sdt_ho_so", "Chưa nối hồ sơ nhân sự thì thiếu SĐT."
    e = Employee(code="E1", full_name="ld", department="x", position="nv", active=True, user_id=u.id)
    db.add(e); db.flush()
    db.add(EmployeeProfile(employee_id=e.id, phone="0900000001")); db.commit()
    ok, ly, _ = BD._kenh_zns(db, None, u, "")
    assert ok is False and ly == "chua_noi_bo_gui_zns", "Có SĐT mà chưa có bộ gửi: thất bại CÓ LÝ DO."


# ---------------------------------------------------------------- màn hình và bản nâng cấp
def test_em1_9_o_nhap_chi_hien_o_dong_dang_sua():
    if not WEB.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = WEB.read_text(encoding="utf-8")
    i = src.find("/email-cong-viec")
    assert i > 0, "Màn /access chưa gọi cửa email công việc"
    truoc = src[max(0, src.rfind("<td>", 0, i) - 10):i]
    assert "emUid === r.id" in truoc, "Ô nhập email phải nằm sau điều kiện emUid === r.id (bảng nhẹ)."
    assert "<th>Email công việc</th>" in src


def test_em1_10_ban_nang_cap_noi_dung_dau():
    vs = (BE / "alembic" / "versions" / "em1_users_email_cong_viec.py").read_text(encoding="utf-8")
    assert 'down_revision = "dx5t0u7s9e4a"' in vs
    assert re.search(r'server_default=""', vs)
