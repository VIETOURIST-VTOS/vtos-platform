# -*- coding: utf-8 -*-
"""MKT-11 — MỘT BÀN LÀM VIỆC CHO PHÓ TGĐ MARKETING. Năm ô mới, và một trạng thái thứ ba.

CA QUAN TRỌNG NHẤT Ở ĐÂY LÀ `test_so_dien_thoai_bang_dung_so_cua_man_marketing`. Nó gọi CẢ HAI
cửa trên cùng một dữ liệu và đòi hai con số bằng nhau. Nếu một ngày nào đó ai đó "tối ưu" bằng
cách đếm lại số điện thoại ngay trong bàn, ca này đỏ — và nó đỏ TRƯỚC khi hai màn hình kịp hiện
hai con số khác nhau cho cùng một thứ.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI; nó chạy ở lượt hai của vòng.
"""
from __future__ import annotations

import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_mkt11.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_mkt11.db", "test_mkt11.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.core import User
from app.services import ban_mkt as BM

client = TestClient(app)
MK = "mkt11test123456"

# Bốn ô VIỆC của bàn — bốn ô duy nhất được cộng vào tổng, y như trước MKT-11.
O_VIEC = ("pr_qua_han", "noi_dung_cho_duyet", "chien_dich_cho_duyet", "ky_chua_chot")
# Năm ô MKT-11 thêm vào, cộng ô mẫu số cũ.
O_MAU_SO = ("chien_dich_dang_chay", "sdt_phat_sinh", "ty_le_chot", "ngan_sach_ky",
            "lead_qua_han_phong", "lead_chua_gan")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for vai in ("ptgd_mkt",):
            un = "m11_" + vai
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name="Thử " + vai, role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit()
        db.close()
        yield


def dau():
    r = client.post("/api/v1/auth/login", data={"username": "m11_ptgd_mkt", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def ban():
    r = client.get("/api/v1/marketing/ban-ptgd", headers=dau())
    assert r.status_code == 200, r.text
    return r.json()


def o_theo_khoa(d):
    return {x["khoa"]: x for x in d["o"]}


def test_ban_co_du_muoi_o_va_dung_khoa():
    """Mười ô, không thừa không thiếu. Thiếu một ô là một khối trống trên màn hình thật."""
    o = o_theo_khoa(ban())
    assert set(o) == set(O_VIEC) | set(O_MAU_SO), sorted(o)


def test_nam_o_moi_khong_cong_vao_tong_viec_cho():
    """Cộng lead với kỳ với bản thảo ra một con số không ai dùng được.

    Tài liệu bàn giao dặn thẳng: một lead có thể thuộc nhiều nhóm nên không cộng các nhóm thành
    tổng người. Nên tổng chỉ gồm bốn ô việc như trước MKT-11.
    """
    d = ban()
    o = o_theo_khoa(d)
    assert set(BM.MAU_SO) == set(O_MAU_SO), sorted(BM.MAU_SO)
    if d["tong_dang_cho"] is not None:
        assert d["tong_dang_cho"] == sum(o[k]["so_luong"] for k in O_VIEC)


def test_chua_xac_dinh_va_chua_lap_khong_bao_gio_la_so_khong():
    """Ba trạng thái khác nhau, và không trạng thái nào được vẽ thành 0.

    `leads.py` đã viết ra luật này: CHƯA ĐỐI CHIẾU THÌ KHÔNG XÁC ĐỊNH, KHÔNG PHẢI 0%.
    """
    o = o_theo_khoa(ban())
    for k in ("ty_le_chot", "ngan_sach_ky"):
        x = o[k]
        assert x["trang_thai"] in (BM.SAN_SANG, BM.CHUA_CO, BM.LOI), x
        if x["trang_thai"] == BM.CHUA_CO:
            assert x["so_luong"] is None, x
            assert x["chu"], "ô CHUA_CO phải mang CHỮ để vẽ thay cho số: " + k
            assert x["ghi_chu"], k


def test_moi_o_deu_co_cua_de_di_toi_cho_lam_viec():
    """Một con số không có cửa là một con số người đọc không làm gì được với nó."""
    for k, x in o_theo_khoa(ban()).items():
        if x["trang_thai"] != BM.LOI:
            assert x["den"].startswith("/"), (k, x["den"])
            assert x["nguon"], "ô phải nói nó đọc từ đâu: " + k


def test_lead_qua_han_phong_khong_cat_theo_nguoi():
    """Bàn nhân viên hỏi «sáng nay TÔI phải làm gì»; bàn Phó TGĐ hỏi «phòng tôi đang nợ bao nhiêu».

    Nên số của phòng không bao giờ nhỏ hơn số của một người trong phòng.
    """
    phong = o_theo_khoa(ban())["lead_qua_han_phong"]
    r = client.get("/api/v1/marketing/ban-nhan-vien", headers=dau())
    assert r.status_code == 200, r.text
    toi = {x["khoa"]: x for x in r.json()["o"]}["lead_qua_han_cua_toi"]
    if phong["trang_thai"] == BM.SAN_SANG and toi["trang_thai"] == BM.SAN_SANG:
        assert phong["so_luong"] >= toi["so_luong"], (phong["so_luong"], toi["so_luong"])


def test_so_dien_thoai_bang_dung_so_cua_man_marketing():
    """KHÔNG ĐẾM LẠI. Hai cửa, cùng dữ liệu, phải ra cùng một con số.

    Hàm đếm theo kênh trả về số điện thoại của TỪNG kênh; cộng lại là đếm hai lần một số nằm ở
    hai kênh. Ca này đỏ ngay nếu ai đó đếm lại trong bàn thay vì gọi đúng hàm màn Marketing gọi.
    """
    o = o_theo_khoa(ban())["sdt_phat_sinh"]
    if o["trang_thai"] != BM.SAN_SANG:
        pytest.skip("ô số điện thoại đang không đọc được")
    r = client.get("/api/v1/leads/conversion?month=" + BM.ky_nay(), headers=dau())
    assert r.status_code == 200, r.text
    assert o["so_luong"] == r.json()["total_current"]["so_sdt"]


def test_o_doc_hong_van_ve_chu_chu_khong_ve_so_khong(monkeypatch):
    """Một ô đọc hỏng mà hiện «0» là nói với người ngồi bàn rằng hôm nay không có gì phải làm."""
    def no(*a, **k):
        raise RuntimeError("thử làm hỏng ô")
    monkeypatch.setattr(BM, "_sdt_phat_sinh", no)
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        o = {x["khoa"]: x for x in BM.ban_ptgd(db)["o"]}["sdt_phat_sinh"]
    finally:
        db.close()
    assert o["trang_thai"] == BM.LOI, o
    assert o["so_luong"] is None, o
    assert "thử làm hỏng ô" in o["ly_do"]


def test_ban_nhan_vien_khong_bi_doi_theo():
    """Hai bàn nay là hai nguồn vẽ, nhưng CHUNG một máy chủ — bàn kia phải y nguyên."""
    r = client.get("/api/v1/marketing/ban-nhan-vien", headers=dau())
    assert r.status_code == 200, r.text
    o = {x["khoa"] for x in r.json()["o"]}
    assert "lead_qua_han_cua_toi" in o and "lead_chua_gan" in o
    assert "sdt_phat_sinh" not in o, "ô của bàn Phó TGĐ không được rơi sang bàn nhân viên"
