"""Vá 10/10/2026 — hai bước của một cặp tách nhiệm là BẤT BIẾN sau khi tạo.

Lỗ được bản rà soát 10/10/2026 tìm ra trên `main`: cửa khai cặp kiểm "nới" cho đúng hai việc
(hạ mức, tắt cặp) rồi ghi `buoc_a`/`buoc_b` vô điều kiện. Giữ mã cặp mà đổi bước là gỡ kiểm
soát trong khi mức vẫn đọc là "chặn". 29 phép thử của Đợt E2a không có ca nào thử việc ấy —
nên tệp này tồn tại, và nó thử ĐÚNG việc ấy.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_le2c.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_le2c.db", "test_le2c.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                           # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402

from app.main import app                                # noqa: E402
from app.db.session import SessionLocal                 # noqa: E402
from app.models.tach_nhiem import CapTachNhiem          # noqa: E402

client = TestClient(app)
CUA = "/api/v1/hach-toan/cap-tach-nhiem"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _dn(vai):
    r = client.post("/api/v1/auth/login",
                    data={"username": vai, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, f"Khong dang nhap duoc vai {vai}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


MA = "le2c-cap-thu"


def _dung_cap(muc="canh_bao_va_chan"):
    db = SessionLocal()
    db.query(CapTachNhiem).filter(CapTachNhiem.ma_cap == MA).delete()
    db.add(CapTachNhiem(ma_cap=MA, buoc_a="duyet_lenh_chi", buoc_b="da_chi",
                        ten="cap thu", muc_do=muc, nguoi_ky="chutich",
                        can_cu="dung cho phep thu", dang_ap_dung=True))
    db.commit()
    db.close()


def _doc_cap():
    db = SessionLocal()
    c = db.query(CapTachNhiem).filter(CapTachNhiem.ma_cap == MA).first()
    ra = (c.buoc_a, c.buoc_b, c.muc_do) if c else None
    db.close()
    return ra


def test_a_doi_buoc_bi_tu_choi_va_so_khong_doi():
    """Lỗ gốc: giữ mã, đổi `buoc_b`, mức vẫn "chặn" — kiểm soát biến mất trong im lặng."""
    _dung_cap()
    r = client.post(CUA, headers=_dn("ketoan"), json={
        "ma_cap": MA, "buoc_a": "duyet_lenh_chi", "buoc_b": "lap_but_toan"})
    assert r.status_code == 422, f"Phai bi tu choi. Nhan {r.status_code}: {r.text}"
    assert _doc_cap() == ("duyet_lenh_chi", "da_chi", "canh_bao_va_chan"), (
        "Cuoc goi bi tu choi KHONG duoc de lai mot nua thay doi nao trong so")


def test_b_chu_tich_cung_khong_doi_duoc_bang_cua_nay():
    """Không phải việc "nới có ký" — là việc không làm ở cửa này, kể cả người ký được."""
    _dung_cap()
    r = client.post(CUA, headers=_dn("chutich"), json={
        "ma_cap": MA, "buoc_a": "ghi_so", "buoc_b": "khoa_so_ky",
        "can_cu": "co can cu day du"})
    assert r.status_code == 422, f"Nhan {r.status_code}: {r.text}"
    assert _doc_cap()[0] == "duyet_lenh_chi"


def test_c_doi_cho_hai_buoc_khong_phai_doi_noi_dung():
    """`a↔b` và `b↔a` là CÙNG một cặp — so bằng tập hợp, không so theo thứ tự."""
    _dung_cap()
    r = client.post(CUA, headers=_dn("ketoan"), json={
        "ma_cap": MA, "buoc_a": "da_chi", "buoc_b": "duyet_lenh_chi"})
    assert r.status_code == 200, f"Doi cho khong phai doi noi dung. {r.status_code}: {r.text}"


def test_d_van_dat_duoc_muc_binh_thuong():
    """Vá không được khóa luôn việc THẮT — Kế toán vẫn nâng mức được, không cần ký."""
    _dung_cap(muc="canh_bao_cho_qua")
    r = client.post(CUA, headers=_dn("ketoan"), json={
        "ma_cap": MA, "buoc_a": "duyet_lenh_chi", "buoc_b": "da_chi",
        "muc_do": "canh_bao_va_chan"})
    assert r.status_code == 200, r.text
    assert _doc_cap()[2] == "canh_bao_va_chan"


def test_e_ha_muc_van_doi_chu_ky():
    """Hàng rào cũ phải còn nguyên sau khi vá."""
    _dung_cap(muc="canh_bao_va_chan")
    r = client.post(CUA, headers=_dn("ketoan"), json={
        "ma_cap": MA, "buoc_a": "duyet_lenh_chi", "buoc_b": "da_chi",
        "muc_do": "khong_canh_bao"})
    assert r.status_code == 403, f"Ha muc phai doi chu ky. Nhan {r.status_code}: {r.text}"
    assert _doc_cap()[2] == "canh_bao_va_chan"


def test_f_tao_cap_moi_van_duoc():
    """Đường đi hợp lệ khi muốn canh cặp bước khác: tạo mã MỚI."""
    db = SessionLocal()
    db.query(CapTachNhiem).filter(CapTachNhiem.ma_cap == "le2c-cap-moi").delete()
    db.commit()
    db.close()
    r = client.post(CUA, headers=_dn("ketoan"), json={
        "ma_cap": "le2c-cap-moi", "buoc_a": "ghi_so", "buoc_b": "khoa_so_ky",
        "ten": "cap moi"})
    assert r.status_code == 200, r.text
