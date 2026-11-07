"""KS-KSO (08/11/2026) — hai bản xem trước trên trang Kết sổ: cùng số, ít câu hỏi hơn.

Đo trên crm thật hai lượt: `/ket-so/tach-ty-gia/xem-truoc` và `/ket-so/bu-tru-gtgt/xem-truoc` mỗi
bản 4,3–4,8 giây. Tách tỷ giá nạp TOÀN BỘ bảy bảng ngoại tệ và toàn bộ tour để giữ lại vài dòng
của một kỳ; bù trừ GTGT đọc danh mục tài khoản hai lần và quét sổ cái năm lần.

Phép thử này giữ một điều: cách mới ra ĐÚNG con số của cách cũ. Cách cũ vẫn nằm trong mã
(`_cay_tk`, `_ps_cay`, `_du_tren_cha`; `_dong_ngoai_te` không lọc) và được dùng làm thước.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ks_kso.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _ghi(mo_ta, ngay, lines):
    r = client.post("/api/v1/journal", json={"entry_date": ngay, "description": mo_ta, "lines": lines, "post": True},
                    headers=login("ketoan"))
    return r.status_code in (200, 201)


def test_ks_kso_1_gtgt_hai_cau_hoi_ra_dung_nam_con_so_cu(db):
    from app.services import ket_so as KS
    ky_truoc, ky = "2026-09", "2026-10"
    # Dựng ít nhất vài dòng 1331 / 33311 ở kỳ trước và kỳ này (nếu cửa ghi tay nhận).
    _ghi("ks-kso gtgt vao truoc", "2026-09-10", [{"account": "1331", "debit": 1_000_000}, {"account": "1111", "credit": 1_000_000}])
    _ghi("ks-kso gtgt vao", "2026-10-10", [{"account": "1331", "debit": 700_000}, {"account": "1111", "credit": 700_000}])
    _ghi("ks-kso gtgt ra", "2026-10-12", [{"account": "1111", "debit": 2_000_000}, {"account": "33311", "credit": 2_000_000}])
    for k in (ky_truoc, ky, "2026-11"):
        cay_ra, cay_vao = KS._cay_tk(db, KS.TK_GTGT_RA_CHA), KS._cay_tk(db, KS.TK_GTGT_VAO_CHA)
        cu = (KS._ps_cay(db, cay_ra, k, luy_ke=False), KS._ps_cay(db, cay_vao, k, luy_ke=False),
              KS._ps_cay(db, cay_vao, k, luy_ke=True),
              KS._du_tren_cha(db, KS.TK_GTGT_RA_CHA, k), KS._du_tren_cha(db, KS.TK_GTGT_VAO_CHA, k))
        assert KS._so_lieu_gtgt(db, k) == cu, k


def test_ks_kso_2_gtgt_khong_con_goi_nam_lan_quet():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(goc, "app", "services", "ket_so.py"), encoding="utf-8").read()
    i = src.index("def xem_truoc_bu_tru_gtgt")
    than = src[i:src.index("\ndef ", i + 10)]
    assert "_so_lieu_gtgt(db, ky)" in than
    assert "_ps_cay(" not in than and "_du_tren_cha(" not in than


def test_ks_kso_3_tach_ty_gia_loc_som_ra_dung_bon_ro_cu(db, monkeypatch):
    from app.models.core import Tour
    from app.models.lop3_tour import TourPhuongTien
    from app.services import chenh_lech_ty_gia as CL
    t = db.execute(select(Tour)).scalars().first()
    for tt, tg, ngay in (("USD", 25_000, date(2026, 10, 3)), ("USD", 25_100, date(2026, 10, 3)),
                         ("EUR", 27_000, date(2026, 9, 30)), ("USD", None, date(2026, 10, 5)),
                         ("USD", 0, date(2026, 10, 6)), ("VND", 1, date(2026, 10, 7)),
                         ("GBP", 33_000, None), ("", 25_000, date(2026, 10, 8))):
        db.add(TourPhuongTien(tour_id=t.id, loai="xe", tien_te=tt or None if tt == "" else tt, ty_gia=tg,
                              ngay_ty_gia=ngay, so_tien_goc=100.0, so_luong=2.0))
    db.flush()
    moi = {k: CL.tinh_tach(db, k) for k in ("2026-09", "2026-10", None)}
    that = CL._dong_ngoai_te
    monkeypatch.setattr(CL, "_dong_ngoai_te", lambda db_, ky=None, co_ty_gia=False: that(db_))
    for k, kq in moi.items():
        assert CL.tinh_tach(db, k) == kq, k
