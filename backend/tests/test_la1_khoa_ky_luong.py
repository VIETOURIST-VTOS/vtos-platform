"""Đợt A1 — khóa kỳ lương và chuỗi mới (Chủ tịch chốt 07/10/2026).

  A. Chuỗi mới: máy kiểm cơ sở → HCNS kiểm → Chủ tịch HOẶC TGĐ ký.
  B. Chưa kiểm cơ sở thì không trình được; còn cờ chặn thì không qua.
  C. Ký là khóa: có bản chụp, có vân tay, có tên người ký và vai của họ.
  D. Bản khóa chụp CẢ THAM SỐ, không chỉ kết quả.
  E. Sửa tham số sau khi ký KHÔNG đổi số đã ký, và phép đối chiếu nói ra chỗ lệch.
  F. Chủ tịch ký được — trước bản này ông không có cột để ký.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_la1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_la1.db"):
    os.remove("test_la1.db")

import pytest
from tests.cong_da_duyet import duyet_cong
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
P = f"{date.today() - timedelta(days=14):%Y-%m}"


def login(u):
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
        yield


def _kiem(ai="hcns"):
    duyet_cong(client, P, login)   # CN-1: công chưa duyệt thì kiểm cơ sở chặn
    return client.post(f"/api/v1/payroll-runs/{P}/kiem-co-so", headers=login(ai))


def _tien(ai):
    return client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login(ai))


# ───────────────────── A · chuỗi mới ─────────────────────
def test_a1_chua_kiem_co_so_thi_khong_trinh_duoc():
    client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns"))
    r = _tien("hcns")
    assert r.status_code == 422
    assert "kiem-co-so" in r.json()["detail"], \
        "thông điệp phải chỉ ra cửa cần gọi, không chỉ nói 'sai trạng thái'"


def test_a2_ke_toan_khong_con_dung_dau_chuoi():
    r = _tien("ketoan")
    assert r.status_code == 403, \
        "Kế toán chuyển về cuối chuỗi – thứ họ xác nhận ở đầu là sự thật máy tự kiểm được"


def test_a2b_cong_chua_duyet_thi_kiem_co_so_chan():
    """CN-1 (21/10/2026): phòng có người trong bảng mà công chưa duyệt thì kiểm cơ sở CHẶN."""
    d = client.post(f"/api/v1/payroll-runs/{P}/kiem-co-so", headers=login("hcns")).json()
    co = [c for c in d["co"] if c["ma"] == "CONG_CHUA_DUYET"]
    assert co and all(c["muc"] == "chan" for c in co), d["co"]
    assert d["dat"] is False and d["trang_thai"] == "nhap"


def test_a3_kiem_co_so_chay_duoc_va_doi_trang_thai():
    d = _kiem().json()
    assert d["dat"] is True, d["co"]
    assert d["trang_thai"] == "da_kiem_co_so"
    assert "không nghĩa là bảng đúng" in d["ghi_chu"], \
        "không có cờ KHÁC với bảng đúng – câu ấy phải nằm trong câu trả lời, không nằm trong tài liệu"


def test_a4_moi_co_deu_co_muc_va_bang_chung():
    d = _kiem().json()
    for c in d["co"]:
        assert c["muc"] in ("chan", "canh_bao")
        assert c.get("bang_chung"), f"cờ {c['ma']} không mở ra xem được – cảnh báo không mở được là cảnh báo bị bỏ qua"


def test_a5_hcns_kiem_roi_moi_den_chu_ky():
    assert _tien("hcns").json()["run"]["status"] == "hcns_kiem"


def test_a6_sua_cong_sau_khi_duyet_thi_chu_ky_dung_lai():
    """CN-1: kiểm cơ sở đã qua, nhưng HCNS sửa công trước lúc ký thì xác nhận hết hiệu lực và chữ ký
    phải dừng — kiểm lại ngay trong bước ký, không tin kết quả kiểm từ trước."""
    bang = client.get("/api/v1/attendance", params={"period": P, "department": "ketoan"},
                      headers=login("hcns")).json()
    if not bang["rows"]:
        pytest.skip("bản demo không có người phòng Kế toán")
    eid = bang["rows"][0]["employee_id"]
    r = client.post("/api/v1/attendance", json={"employee_id": eid, "day": f"{P}-02", "kind": "khong_luong",
                                                "work": 0, "ot_hours": 0, "note": "CN-1"}, headers=login("hcns"))
    assert r.status_code == 200, r.text
    r = _tien("chutich")
    assert r.status_code == 422 and "công chưa duyệt" in r.json()["detail"], r.text
    duyet_cong(client, P, login)


# ───────────────────── F · Chủ tịch ký được ─────────────────────
def test_f1_chu_tich_ky_duoc_bang_luong():
    r = _tien("chutich")
    assert r.status_code == 200, r.text
    assert r.json()["run"]["status"] == "da_ky"
    assert "Chủ tịch" in r.json()["message"]


def test_f2_ky_roi_khong_tinh_lai_duoc():
    r = client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns"))
    assert r.status_code == 422


# ───────────────────── C, D · bản khóa ─────────────────────
def test_c1_ky_la_khoa_co_van_tay_va_nguoi_ky():
    d = client.get(f"/api/v1/payroll-runs/{P}/ban-khoa", headers=login("hcns")).json()
    b = d["ban_khoa"]
    assert b is not None, "ký mà không khóa thì chữ ký không gắn vào gì cả"
    assert b["ban_so"] == 1 and b["khoa_vai"] == "chutich"
    assert len(b["dau_van_tay"]) == 64, "vân tay phải là băm sha256, không phải cả bản JSON"


def test_d1_ban_khoa_chup_ca_tham_so_khong_chi_ket_qua():
    b = client.get(f"/api/v1/payroll-runs/{P}/ban-khoa", headers=login("hcns")).json()["ban_khoa"]
    assert b["quy_tac"], "lưu mỗi kết quả thì sang năm không ai trả lời được 'vì sao tháng ấy ra số này'"
    assert "nguong_bien" in b["quy_tac"]


def test_d2_doi_chieu_ngay_sau_khi_ky_phai_khop():
    d = client.get(f"/api/v1/payroll-runs/{P}/ban-khoa", headers=login("hcns")).json()["doi_chieu"]
    assert d["co_ban_khoa"] is True
    assert d["khop"] is True, "cùng đầu vào phải ra cùng kết quả – nếu không thì bản khóa vô nghĩa"


# ───────────────────── E · sửa tham số sau khi ký ─────────────────────
def test_e1_sua_tham_so_sau_khi_ky_khong_doi_so_da_ky():
    truoc = client.get(f"/api/v1/payroll-runs/{P}", headers=login("hcns")).json()
    tong_truoc = truoc["totals"]["thuc_nhan"]

    from app.db.session import SessionLocal
    from app.models.core import Param
    db = SessionLocal()
    db.add(Param(key="nguong_bien", value="0.95", label="Ngưỡng biên (thử)",
                 effective_from=date(date.today().year - 1, 1, 1), status="active"))
    db.commit(); db.close()

    sau = client.get(f"/api/v1/payroll-runs/{P}", headers=login("hcns")).json()
    assert sau["totals"]["thuc_nhan"] == tong_truoc, \
        "sửa tham số hôm nay mà đổi được con số của một kỳ đã ký hôm qua là lỗi nặng nhất của bảng lương cũ"


def test_e2_doi_chieu_noi_ra_cho_lech():
    d = client.get(f"/api/v1/payroll-runs/{P}/ban-khoa", headers=login("hcns")).json()["doi_chieu"]
    assert d["van_tay_da_khoa"] != d["van_tay_tinh_lai"] or d["khop"] is True
    if not d["khop"]:
        assert "LỆCH" in d["thong_diep"] and "vẫn là số có hiệu lực" in d["thong_diep"], \
            "lệch không tự là sai, nhưng phải hiện ra chứ không được im"


# ───────────────────── B · cờ chặn ─────────────────────
def test_b1_co_chan_thi_khong_qua():
    from app.services import luong_khoa as LK
    co = [{"ma": "X", "muc": "chan", "thong_diep": "", "bang_chung": {}},
          {"ma": "Y", "muc": "canh_bao", "thong_diep": "", "bang_chung": {}}]
    assert len(LK.co_chan(co)) == 1


def test_b2_tham_so_moi_them_vao_bo_tinh_phai_khai_vao_ban_chup():
    """Quên khai một tham số là bản chụp THIẾU CĂN CỨ – nguy hơn không chụp, vì nó trông như đủ."""
    import re
    from pathlib import Path
    from app.services import luong_khoa as LK
    src = (Path(__file__).resolve().parents[1] / "app" / "services" / "hr.py").read_text(encoding="utf-8")
    dung = set(re.findall(r'get_param(?:_text)?\(db,\s*"([a-z_0-9]+)"', src))
    thieu = sorted(dung - set(LK.THAM_SO_LUONG))
    assert not thieu, (f"bộ tính lương đọc {thieu} nhưng bản khóa không chụp – thêm vào "
                       f"services/luong_khoa.THAM_SO_LUONG")
