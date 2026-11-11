# -*- coding: utf-8 -*-
"""VH-27 · BÀN CHỦ TỊCH / THANH NGANG (Chủ tịch 12/11/2026 01:26, duyệt bản xem trước).

  1. «Lịch xe 90 ngày» rời thanh ngang, xuống đầu bàn làm việc cạnh ô ngày (mọi vai đang có nút).
  2. Tên bàn nhỏ lại (34 → 28px).
  3. Bấm một dòng của «Công việc» / «Chờ duyệt» → số trên nút giảm; máy chủ nhớ (đổi máy vẫn giữ).
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_vh27_dx.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vh27_dx.db"):
    os.remove("test_vh27_dx.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.api.v1 import routes as RT  # noqa: E402

client = TestClient(app)
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")


def _web(*p):
    with open(os.path.join(WEB, *p), encoding="utf-8") as f:
        return f.read()


def h():
    r = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def test_bam_dong_thi_so_giam_va_may_chu_nho():
    hd = h()
    d = client.get("/api/v1/dashboard/dem", headers=hd).json()
    uid = next(iter(RT._DEM_CACHE))
    # Dựng sẵn danh sách trong bản nhớ để phép thử không phụ thuộc dữ liệu mẫu.
    RT._DEM_CACHE[uid] = (RT._DEM_CACHE[uid][0], {**d, "cho_duyet": [
        {"label": "3 tờ quyết toán chờ CHỦ TỊCH duyệt", "href": "/xe", "so": 3},
        {"label": "Đề xuất chi đội xe · phiếu thử", "href": "/xe", "so": 1}], "so_cho_duyet": 4,
        "cong_viec": [{"label": "Ký chạy tour · T1", "href": "/tours/1", "so": 1}], "so_cong_viec": 1})
    d = client.get("/api/v1/dashboard/dem", headers=hd).json()
    assert d["so_cho_duyet"] == 4 and d["so_cong_viec"] == 1
    r = client.post("/api/v1/dashboard/da-xem", json={"loai": "duyet", "label": "3 tờ quyết toán chờ CHỦ TỊCH duyệt"}, headers=hd)
    assert r.status_code == 200, r.text
    client.post("/api/v1/dashboard/da-xem", json={"loai": "viec", "label": "Ký chạy tour · T1"}, headers=hd)
    d = client.get("/api/v1/dashboard/dem", headers=hd).json()
    assert d["so_cho_duyet"] == 1 and d["so_cong_viec"] == 0
    assert [x["da_xem"] for x in d["cho_duyet"]] == [True, False]
    # Có việc mới → nhãn đổi → số tăng lại.
    RT._DEM_CACHE[uid] = (RT._DEM_CACHE[uid][0], {**d, "cho_duyet": [
        {"label": "4 tờ quyết toán chờ CHỦ TỊCH duyệt", "href": "/xe", "so": 4}], "so_cho_duyet": 4})
    assert client.get("/api/v1/dashboard/dem", headers=hd).json()["so_cho_duyet"] == 4
    assert client.post("/api/v1/dashboard/da-xem", json={"loai": "x", "label": "a"}, headers=hd).status_code == 422


def test_man_hinh():
    sh = _web("components", "Shell.tsx")
    dau = _web("components", "DauManHinh01.tsx")
    css = _web("app", "globals.css")
    assert "<NutLich90" not in sh, "Lịch xe 90 ngày đã rời thanh ngang"
    assert "<NutLich90" in dau and "mh01-ban-cum" in dau
    assert ".mh01-ban-ten{margin:0;font-size:calc(28/14*1rem);" in css
    assert '"/dashboard/da-xem"' in sh and "nv-da" in sh
