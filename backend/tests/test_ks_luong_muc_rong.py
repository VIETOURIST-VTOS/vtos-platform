"""KS-LUONG (08/11/2026) — bảng lương kỳ không được sập vì một người CHƯA KHAI mức lương hợp đồng.

Chủ tịch cho kiểm 75 màn hình của bốn phân hệ trên crm thật: trang Nhân sự, MỌI thẻ, báo 500 ở
`/payroll-runs/2026-10` và `/payroll-runs/2026-09`. Nhật ký Render:
    luong.py, line 111, in xac_dinh_theo_cong — f"{e.base_salary:,.0f}"
    TypeError: unsupported format string passed to NoneType.__format__
Một nhân viên chấm công theo ngày (Kế toán / HCNS) có `base_salary` rỗng, chưa nhập công thực tế →
câu giải thích định dạng số rỗng → cả bảng lương của mọi người trả 500.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ks_luong.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


class _E:
    def __init__(self, luong): self.base_salary = luong


def test_ks_luong_1_muc_rong_khong_no_va_noi_ra_chua_khai():
    from app.services import luong as L
    kq = L.xac_dinh_theo_cong(_E(None), 26, None)
    assert kq["muc_ky"] == 0 and kq["thieu_du_lieu"] is True
    assert "chưa khai mức lương hợp đồng" in kq["giai_thich"]
    assert "10,000,000" in L.xac_dinh_theo_cong(_E(10_000_000), 26, None)["giai_thich"]


def test_ks_luong_2_bang_luong_ky_van_mo_duoc_khi_co_nguoi_cham_cong_chua_khai_luong():
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from app.services import luong as L
    dept = next(k for k, v in L.CHE_DO_CONG.items() if v == L.CHAM_CONG)
    with SessionLocal() as db:
        db.add(Employee(code="KSL-1", full_name="Người chưa khai lương", department=dept,
                        base_salary=None, active=True))
        db.commit()
    tok = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"}).json()["access_token"]
    r = client.get("/api/v1/payroll-runs/2026-10?refresh=true", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text[:300]
