# -*- coding: utf-8 -*-
"""PC-1 · Trưởng phòng tự gửi yêu cầu Pháp chế, và hai chuông mới (Chủ tịch duyệt 19/10/2026).

Canh bốn luật của api/v1/gui_phap_che.py và hai chuông:
  · ai được gửi (trưởng phòng trở lên + HCNS, CNTT) và ai bị chặn (nhân viên);
  · phòng gửi / người gửi lấy từ TÀI KHOẢN, không nhận từ màn hình;
  · cửa đọc CHỈ trả yêu cầu của chính người gửi — gọi chéo mã của người khác ra 404;
  · bổ sung chỉ khi Pháp chế chờ bổ sung;
  · chuông «yêu cầu Pháp chế mới» bật khi gửi, tắt khi Pháp chế nhận việc;
  · chuông «Kế toán trả lại quyết toán» có CHỦ là người giữ hồ sơ, tắt khi đóng số lại.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_pc1.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_pc1.db", "test_pc1.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.core import Alert, User

MK = "pc1_123456"
P = "/api/v1/gui-phap-che"
client = TestClient(app)
NGUOI = (("pc1_tpkd", "tp_kd", "kinh_doanh", "TP Kinh doanh A"),
         ("pc1_tpdh", "tp_dh", "dieu_hanh", "TP Điều hành B"),
         ("pc1_gdkd", "gd_kd", "kinh_doanh", "GĐ Kinh doanh C"),
         ("pc1_hcns", "hcns", "hcns", "HCNS D"),
         ("pc1_nvkd", "nv_kd", "kinh_doanh", "NV KD E"),
         ("pc1_pc", "ir_phapche", "phap_che", "Pháp chế F"))


@pytest.fixture(scope="module", autouse=True)
def _du_lieu():
    global client
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for un, vai, phong, ten in NGUOI:
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=ten, role=vai, department=phong,
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


_TOK = {}


def _dn(un):
    if un not in _TOK:
        r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
        assert r.status_code == 200, r.text
        _TOK[un] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _TOK[un]


def _gui(un, tieu_de="Rà soát hợp đồng thuê xe", **them):
    return client.post(P, json={"loai": "ra_soat_hop_dong", "tieu_de": tieu_de, "noi_dung": "x",
                                "muc_do": "gap", **them}, headers=_dn(un))


def test_pc1_1_truong_phong_gui_duoc_nhan_vien_bi_chan():
    for un in ("pc1_tpkd", "pc1_gdkd", "pc1_hcns"):
        assert _gui(un).status_code == 201, un
    assert _gui("pc1_nvkd").status_code == 403


def test_pc1_2_phong_va_nguoi_gui_lay_tu_tai_khoan():
    r = _gui("pc1_tpdh", phong_gui="Ban Giám đốc", nguoi_gui="Chủ tịch")
    assert r.status_code == 201
    yc = r.json()["yeu_cau"]
    assert yc["phong_gui"] == "dieu_hanh" and yc["nguoi_gui"] == "TP Điều hành B"


def test_pc1_3_chi_doc_duoc_yeu_cau_cua_minh():
    a = _gui("pc1_tpkd", "Của TP KD").json()["yeu_cau"]["id"]
    b = _gui("pc1_tpdh", "Của TP ĐH").json()["yeu_cau"]["id"]
    ds_kd = {x["id"] for x in client.get(P, headers=_dn("pc1_tpkd")).json()["rows"]}
    ds_dh = {x["id"] for x in client.get(P, headers=_dn("pc1_tpdh")).json()["rows"]}
    assert a in ds_kd and b not in ds_kd
    assert b in ds_dh and a not in ds_dh
    r = client.post(f"{P}/{b}/bo-sung", json={"noi_dung_bo_sung": "x"}, headers=_dn("pc1_tpkd"))
    assert r.status_code == 404, "gọi chéo mã của người khác phải 404"
    assert client.get(f"{P}/{b}/tep", headers=_dn("pc1_tpkd")).status_code == 404


def test_pc1_4_bo_sung_chi_khi_phap_che_cho_bo_sung():
    yid = _gui("pc1_tpkd", "Cần bổ sung").json()["yeu_cau"]["id"]
    r = client.post(f"{P}/{yid}/bo-sung", json={"noi_dung_bo_sung": "thêm"}, headers=_dn("pc1_tpkd"))
    assert r.status_code == 422
    r = client.post(f"/api/v1/ir-phap-che/yeu-cau/{yid}/cho-bo-sung",
                    json={"can_bo_sung": "Gửi bản scan hợp đồng gốc"}, headers=_dn("pc1_pc"))
    assert r.status_code == 200, r.text
    r = client.post(f"{P}/{yid}/bo-sung", json={"noi_dung_bo_sung": "Đã gửi bản scan"},
                    headers=_dn("pc1_tpkd"))
    assert r.status_code == 200
    yc = r.json()["yeu_cau"]
    assert yc["trang_thai"] == "moi" and "Đã gửi bản scan" in yc["noi_dung"]


def test_pc1_5_chuong_phap_che_bat_khi_gui_tat_khi_nhan():
    from app.db.session import SessionLocal
    yid = _gui("pc1_gdkd", "Chuông").json()["yeu_cau"]["id"]
    with SessionLocal() as db:
        a = db.execute(select(Alert).where(Alert.kind == "phap_che_yc_moi",
                                           Alert.ref == f"yeu_cau_phap_che:{yid}")).scalars().one()
        assert a.resolved is False and a.to_roles == "ir_phapche" and a.level == "red"
    assert client.post(f"/api/v1/ir-phap-che/yeu-cau/{yid}/nhan", headers=_dn("pc1_pc")).status_code == 200
    with SessionLocal() as db:
        a = db.execute(select(Alert).where(Alert.kind == "phap_che_yc_moi",
                                           Alert.ref == f"yeu_cau_phap_che:{yid}")).scalars().one()
        assert a.resolved is True and a.trang_thai == "dong"


def test_pc1_6_gan_tep_va_phap_che_mo_duoc():
    yid = _gui("pc1_tpkd", "Có tệp").json()["yeu_cau"]["id"]
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    r = client.post(f"{P}/{yid}/tep", files={"tep": ("hop-dong.pdf", pdf, "application/pdf")},
                    headers=_dn("pc1_tpkd"))
    if r.status_code == 503:
        pytest.skip("kho tệp chưa cấu hình trong môi trường thử")
    assert r.status_code == 201, r.text
    assert client.get(f"{P}/{yid}/tep", headers=_dn("pc1_tpkd")).content == pdf
    assert client.get(f"/api/v1/ir-phap-che/yeu-cau/{yid}/tep", headers=_dn("pc1_pc")).content == pdf
    assert client.get(f"{P}/{yid}/tep", headers=_dn("pc1_tpdh")).status_code == 404


# ───────────── chuông «Kế toán trả lại quyết toán» ─────────────
def test_pc1_7_chuong_tra_lai_co_chu_va_tat_khi_dong_so_lai():
    from app.db.session import Base
    from app.models.core import Tour
    from app.services import tra_lai_quyet_toan as TLQ
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e, future=True)()
    dh = User(username="dh", full_name="dh", role="nv_dh", password_hash="x")
    db.add(dh); db.flush()
    t = Tour(code="LE-1", name="LE-1", tour_type="le_noi_dia", start_date=date.today(),
             end_date=date.today(), operator_id=dh.id, status="ket_thuc", planned_pax=1)
    db.add(t); db.commit()
    TLQ.bao_chuong_tra_lai(db, t, "Thiếu hoá đơn khách sạn"); db.commit()
    a = db.execute(select(Alert).where(Alert.kind == "qt_tra_lai")).scalars().one()
    assert a.nguoi_phu_trach == dh.id, "chuông phải có CHỦ: người giữ hồ sơ quyết toán"
    assert set(a.to_roles.split(",")) == {"tp_dh", "nv_dh"} and "Thiếu hoá đơn" in a.message
    TLQ.bao_chuong_tra_lai(db, t, "Lần hai"); db.commit()
    mo = db.execute(select(Alert).where(Alert.kind == "qt_tra_lai", Alert.resolved == False)).scalars().all()  # noqa: E712
    assert len(mo) == 1 and "Lần hai" in mo[0].message, "trả lại lần nữa thì một chuông mới thay chuông cũ"
    assert TLQ.tat_chuong_tra_lai(db, t, "đóng số lại") == 1
    db.commit()
    assert not db.execute(select(Alert).where(Alert.kind == "qt_tra_lai", Alert.resolved == False)).scalars().all()  # noqa: E712


def test_pc1_8_hai_chuong_co_nhan_tieng_viet():
    from app.services import canh_bao_trinh_bay as CB
    for k in ("qt_tra_lai", "phap_che_yc_moi"):
        assert not CB.nhan_cua(k).get("can_dat_ten"), k
