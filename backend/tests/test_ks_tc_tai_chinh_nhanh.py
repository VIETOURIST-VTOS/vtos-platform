"""KS-TC (08/11/2026) — trang Tài chính: danh sách giao dịch ngân hàng và dự báo 13 tuần.

Chủ tịch chọn «Kiểm tốc độ các trang crm» rồi «Sửa cả 4 trang». Đo trên crm thật, hai lượt:
trang Tài chính chờ 6–8 giây — `/bank-transactions` 6–7,6 s (mỗi dòng hỏi riêng mã booking và
số dòng phân bổ: 1 + 2×200 câu hỏi), `/fin/forecast` 4–5 s (cộng lại cả sổ cái để lấy số dư
tiền mà bảng điều hành vừa cộng xong và đang nhớ).

Không đổi số, không đổi khuôn trả về — chỉ đổi số câu hỏi gửi tới cơ sở dữ liệu.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ks_tc.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks_tc.db"): os.remove("test_ks_tc.db")
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
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


class _Dem:
    def __init__(self, engine): self.e, self.n = engine, 0
    def _cb(self, *a, **k): self.n += 1
    def __enter__(self): event.listen(self.e, "before_cursor_execute", self._cb); return self
    def __exit__(self, *a): event.remove(self.e, "before_cursor_execute", self._cb)


def _tao_giao_dich(n: int):
    from app.db.session import SessionLocal
    from app.models.core import Booking
    from app.models.payments import BankTransaction
    from app.models.phan_bo_tien import PhanBoTien
    db = SessionLocal()
    try:
        bks = list(db.execute(select(Booking).limit(3)).scalars())
        assert bks
        bat_dau = datetime(2026, 11, 1, 8)
        for i in range(n):
            t = BankTransaction(sepay_id=f"kstc-{i}", transaction_date=bat_dau + timedelta(minutes=i),
                                transfer_type="in", amount=1_000_000 + i, content=f"KSTC {i}",
                                match_status="da_khop" if i % 2 == 0 else "cho_ke_toan",
                                booking_id=bks[i % len(bks)].id if i % 2 == 0 else None,
                                raw={"id": i})
            db.add(t); db.flush()
            if i % 3 == 0:
                cot = {c.name for c in PhanBoTien.__table__.columns}
                du = {"bank_txn_id": t.id}
                for ten, gt in (("so_tien", 1_000_000), ("huy", False), ("loai", "booking"),
                                ("tao_boi", "test"), ("nguoi_tao", "test")):
                    if ten in cot: du[ten] = gt
                try:
                    db.add(PhanBoTien(**du)); db.flush()
                except Exception:
                    db.rollback(); raise
        db.commit()
    finally:
        db.close()


def test_ks_tc_1_danh_sach_giao_dich_so_cau_hoi_khong_tang_theo_so_dong():
    try:
        _tao_giao_dich(40)
    except Exception:
        pytest.skip("không dựng được dòng phân bổ mẫu trên lược đồ này")
    from app.db.session import engine
    h = login("ketoan")
    with _Dem(engine) as d:
        r = client.get("/api/v1/bank-transactions?limit=200", headers=h)
    assert r.status_code == 200
    ds = r.json()
    assert len(ds) >= 40
    # 40 dòng trở lên mà chỉ vài câu hỏi: đăng nhập + danh sách + hai bảng tra. Trước KS-TC là ≥ 80.
    assert d.n <= 15, d.n
    # Cùng khuôn trả về: mã booking và số dòng phân bổ vẫn đúng từng dòng.
    co_bk = [x for x in ds if x["sepay_id"].startswith("kstc-") and x["booking_id"]]
    assert co_bk and all(x["booking_code"] for x in co_bk)
    pb = {x["sepay_id"]: x["so_dong_phan_bo"] for x in ds if x["sepay_id"].startswith("kstc-")}
    assert pb["kstc-0"] == 1 and pb["kstc-1"] == 0 and pb["kstc-3"] == 1
    assert "raw" not in ds[0]


def test_ks_tc_2_du_bao_doc_so_du_qua_bo_nho_cua_bang_dieu_hanh(monkeypatch):
    from datetime import date
    from app.db.session import SessionLocal
    from app.services import finance as F, dashboard as DB, reports as RP
    db = SessionLocal()
    try:
        DB._NHO_SO_DU.clear()
        b = RP.balances(db, f"{date.today():%Y-%m}")
        dung = sum(b.get(c, 0.0) for c in ("111", "112"))
        assert F.forecast_13w(db)["opening"] == dung        # cùng con số như cũ
        goi = []
        that = RP.balances
        monkeypatch.setattr(RP, "balances", lambda *a, **k: goi.append(1) or that(*a, **k))
        assert F.forecast_13w(db)["opening"] == dung
        assert goi == []                                    # lần hai không cộng lại sổ cái
    finally:
        db.close()


def test_ks_tc_3_ma_nguon_giu_ba_cau_hoi_cho_ca_danh_sach():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(goc, "app", "api", "v1", "payments.py"), encoding="utf-8").read()
    i = src.index("def list_txns")
    than = src[i:src.index("@router", i + 10)]
    assert "txn_out(t, db, ma_bk," in than and "defer(BankTransaction.raw)" in than
