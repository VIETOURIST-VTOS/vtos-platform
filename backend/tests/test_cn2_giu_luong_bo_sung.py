# -*- coding: utf-8 -*-
"""CN-2 · Giữ lương phòng chưa duyệt công và bảng lương bổ sung (Chủ tịch chốt 21/10/2026).

Đi trọn một vòng thật qua cửa HTTP, trên bản demo:
  1. Duyệt công mọi phòng TRỪ một phòng → ký bảng chính: phòng ấy bị giữ, bản khoá không có họ,
     bút toán và lệnh chi chỉ phần còn lại; chuông và tin Zalo xếp hàng.
  2. Phiếu lương người bị giữ chỉ ghi «đang giữ», KHÔNG có số tiền.
  3. Chưa duyệt công thì không lập được bảng bổ sung; duyệt rồi thì lập, đi CÙNG CHUỖI (kiểm cơ sở →
     HCNS kiểm → Chủ tịch/TGĐ ký), khoá bản riêng — bảng chính vẫn là bản hiệu lực của kỳ.
  4. Ký xong: chuông tắt, phiếu đọc dòng bảng bổ sung, lần chi gắn vào bản khoá bảng bổ sung.
  5. Bẻ ngược: một người đã có trong bảng chính mà lọt vào bảng bổ sung thì kiểm cơ sở CHẶN.
"""
import os, sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_cn2.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_cn2.db", "test_cn2.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app

client = TestClient(app)
TOK = {}
P = f"{date.today() - timedelta(days=14):%Y-%m}"
S = {}                                  # trạng thái chia giữa các bước


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    global client
    with TestClient(app) as c:
        client = c
        yield


def _xn():
    return client.get("/api/v1/attendance/xac-nhan-cong", params={"period": P}, headers=login("hcns")).json()


def _duyet(phong):
    a = client.post(f"/api/v1/attendance/xac-nhan-cong/{P}/{phong}/hcns", headers=login("hcns"))
    assert a.status_code == 200, a.text
    b = client.post(f"/api/v1/attendance/xac-nhan-cong/{P}/{phong}/duyet", headers=login("tgd"))
    assert b.status_code == 200, b.text


def test_cn2_1_ky_bang_chinh_giu_phong_chua_duyet():
    run = client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns")).json()
    ap = {k["phong"] for k in _xn()["phong"]}
    co_nguoi = sorted({r["phong"] for r in run["rows"]} & ap)
    if len(co_nguoi) < 2:
        pytest.skip("bản demo cần ít nhất hai phòng áp dụng xác nhận công có người trong bảng lương")
    giu = co_nguoi[0]
    S["phong"] = giu
    S["ma_giu"] = sorted(r["ma"] for r in run["rows"] if r["phong"] == giu)
    for p in ap - {giu}:
        _duyet(p)
    d = client.post(f"/api/v1/payroll-runs/{P}/kiem-co-so", headers=login("hcns")).json()
    assert d["dat"] is True and any(c["ma"] == "GIU_LUONG" for c in d["co"]), d["co"]
    assert client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns")).status_code == 200
    r = client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("chutich"))
    assert r.status_code == 200, r.text
    assert "GIỮ LẠI" in r.json()["message"] and giu in r.json()["message"]
    assert r.json()["run"]["giu_lai"][giu]["ma"] == S["ma_giu"]

    from app.db.session import SessionLocal
    from app.models.core import Alert
    from app.services import luong_khoa as LK
    with SessionLocal() as db:
        ban = LK.ban_dang_hieu_luc(db, P)
        ma_ban = {x["ma"] for x in ban.noi_dung["rows"]}
        assert not (ma_ban & set(S["ma_giu"])), "người bị giữ không được nằm trong bản khoá bảng chính"
        assert ban.noi_dung["totals"]["so_nguoi"] == len(run["rows"]) - len(S["ma_giu"])
        S["ban_chinh"] = ban.id
        a = db.execute(select(Alert).where(Alert.kind == "luong_dang_giu",
                                           Alert.ref == f"luong:{P}:{giu}")).scalars().one()
        assert a.resolved is False and "hcns" in a.to_roles.split(",")


def test_cn2_2_phieu_luong_nguoi_bi_giu_chi_ghi_dang_giu():
    ma = S["ma_giu"][0]
    r = client.get(f"/api/v1/payroll-runs/{P}/phieu-luong", params={"ma": ma}, headers=login("hcns")).json()
    assert r["dang_giu"] is True and "đang giữ" in r["thong_bao"]
    assert "thuc_nhan" not in r and "thu_nhap" not in r, "Chủ tịch chốt: chỉ ghi «đang giữ», không số dự kiến"


def test_cn2_3_chua_duyet_thi_chua_lap_duoc_bang_bo_sung():
    r = client.post(f"/api/v1/payroll-runs/{P}/bo-sung", headers=login("hcns"))
    assert r.status_code == 422, r.text
    assert client.post(f"/api/v1/payroll-runs/{P}/bo-sung", headers=login("chutich")).status_code == 403


def test_cn2_4_bang_bo_sung_di_cung_chuoi():
    _duyet(S["phong"])
    ds = client.get(f"/api/v1/payroll-runs/{P}/bo-sung", headers=login("hcns")).json()
    assert ds["phong_lap_duoc"] == [S["phong"]]
    r = client.post(f"/api/v1/payroll-runs/{P}/bo-sung", headers=login("hcns"))
    assert r.status_code == 201, r.text
    b = r.json()["bang"]
    assert b["so"] == 1 and sorted(x["ma"] for x in b["rows"]) == S["ma_giu"]
    assert client.post(f"/api/v1/payroll-runs/{P}/bo-sung/1/advance", headers=login("hcns")).status_code == 422, \
        "chưa kiểm cơ sở thì chưa trình"
    k = client.post(f"/api/v1/payroll-runs/{P}/bo-sung/1/kiem-co-so", headers=login("hcns")).json()
    assert k["dat"] is True, k["co"]
    assert client.post(f"/api/v1/payroll-runs/{P}/bo-sung/1/advance", headers=login("tgd")).status_code == 403, \
        "TGĐ không nhảy qua bước HCNS kiểm"
    assert client.post(f"/api/v1/payroll-runs/{P}/bo-sung/1/advance", headers=login("hcns")).status_code == 200
    r = client.post(f"/api/v1/payroll-runs/{P}/bo-sung/1/advance", headers=login("tgd"))
    assert r.status_code == 200, r.text
    assert r.json()["bang"]["status"] == "da_ky" and r.json()["bang"]["ban_khoa_id"]
    S["ban_bs"] = r.json()["bang"]["ban_khoa_id"]

    from app.db.session import SessionLocal
    from app.models.core import Alert
    from app.services import luong_khoa as LK
    with SessionLocal() as db:
        assert LK.ban_dang_hieu_luc(db, P).id == S["ban_chinh"], "ký bảng bổ sung KHÔNG được thay bảng chính"
        a = db.execute(select(Alert).where(Alert.kind == "luong_dang_giu",
                                           Alert.ref == f"luong:{P}:{S['phong']}")).scalars().one()
        assert a.resolved is True


def test_cn2_5_phieu_doc_bang_bo_sung_va_chi_gan_dung_ban():
    ma = S["ma_giu"][0]
    r = client.get(f"/api/v1/payroll-runs/{P}/phieu-luong", params={"ma": ma}, headers=login("hcns")).json()
    assert r["dang_giu"] is False and r["bo_sung_so"] == 1 and "thuc_nhan" in r
    c = client.post(f"/api/v1/payroll-runs/{P}/chi", params={"bo_sung": 1}, headers=login("ketoan"))
    assert c.status_code == 201, c.text
    assert c.json()["chi"]["ban_khoa_id"] == S["ban_bs"]
    c = client.post(f"/api/v1/payroll-runs/{P}/chi", headers=login("ketoan"))
    assert c.json()["chi"]["ban_khoa_id"] == S["ban_chinh"]


def test_cn2_6_be_nguoc_tra_hai_lan_bi_chan():
    """Bẻ ngược: chèn một người của bảng chính vào một bảng bổ sung mới — kiểm cơ sở phải CHẶN."""
    from app.db.session import SessionLocal
    from app.models.luong_khoa import BangLuongBoSung, BangLuongKhoa
    from app.services import giu_luong as GL
    with SessionLocal() as db:
        ban = db.get(BangLuongKhoa, S["ban_chinh"])
        nguoi = ban.noi_dung["rows"][0]
        b = BangLuongBoSung(period=P, so=99, phong=[], rows=[nguoi], totals={}, status="nhap")
        db.add(b); db.commit()
        co = GL.kiem_co_so(db, b)
        assert any(c["ma"] == "TRA_HAI_LAN" and c["muc"] == "chan" for c in co), co
        db.delete(b); db.commit()


def test_cn2_7_doi_chieu_ban_chinh_van_khop_khi_co_giu():
    d = client.get(f"/api/v1/payroll-runs/{P}/ban-khoa", headers=login("hcns")).json()["doi_chieu"]
    assert d["khop"] is True, "bản khoá bảng chính so với đúng phần không bị giữ – không được báo LỆCH giả"
