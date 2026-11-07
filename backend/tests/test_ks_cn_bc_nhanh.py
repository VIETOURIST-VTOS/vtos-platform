"""KS-CN · KS-BC (08/11/2026) — trang Công nợ và bảng tổng hợp Báo cáo ngày: cùng số, ít câu hỏi.

Đo trên crm thật hai lượt: `/cong-no` 4,0–5,3 s (nạp nguyên hơn mười nghìn booking và mọi tour để
giữ lại những dòng còn chênh); `/daily-reports/tong-hop` 4,3–4,8 s (mỗi nhân viên hỏi riêng ngày
nghỉ, báo cáo, hạn nộp, số tệp, lịch sử xem).

Giữ một điều: cách mới ra ĐÚNG kết quả của cách cũ. Cách cũ của Công nợ chép nguyên vào đây làm
thước; cách cũ của Báo cáo ngày vẫn nằm trong mã (gọi `trang_thai_ngay` không truyền gì nạp sẵn).
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ks_cn_bc.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, event
from app.main import app

client = TestClient(app)


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


def _phai_thu_cu(db, hom_nay):
    """Bản trước KS-CN, chép nguyên — thước đối chiếu."""
    from app.models.core import Booking, Tour, User
    from app.services.debts import _q
    tours = {t.id: t for t in db.execute(select(Tour)).scalars()}
    sales = {u.id: u.full_name for u in db.execute(select(User)).scalars()}
    con_thu, tra_lai, qua_han = [], [], 0.0
    for b in db.execute(select(Booking).where(Booking.cancelled == False).order_by(Booking.id)).scalars():   # noqa: E712
        phai = _q((b.amount or 0) - (b.discount or 0)); da = _q(b.paid or 0)
        t = tours.get(b.tour_id)
        dong = {"booking_id": b.id, "code": b.code, "khach": b.customer_name,
                "tour": t.code if t else "", "ten_tour": t.name if t else "",
                "khoi_hanh": t.start_date.isoformat() if t and t.start_date else None,
                "sales": sales.get(b.sales_id, ""), "phai_thu": phai, "da_thu": da}
        con = _q(phai - da)
        if con > 0:
            dong["con_lai"] = con
            dong["qua_han"] = bool(t and t.start_date and t.start_date < hom_nay)
            if dong["qua_han"]: qua_han += con
            con_thu.append(dong)
        elif con < 0:
            dong["phai_tra_lai"] = _q(-con); tra_lai.append(dong)
    con_thu.sort(key=lambda x: -x["con_lai"]); tra_lai.sort(key=lambda x: -x["phai_tra_lai"])
    return {"tong_con_phai_thu": _q(sum(x["con_lai"] for x in con_thu)), "trong_do_qua_han": _q(qua_han),
            "so_booking": len(con_thu), "tong_thu_thua_phai_tra_lai": _q(sum(x["phai_tra_lai"] for x in tra_lai)),
            "chi_tiet": con_thu[:300], "thu_thua": tra_lai[:100]}


def test_ks_cn_1_phai_thu_khach_dung_nhu_cach_cu(db):
    from app.models.core import Booking
    from app.services import debts as CN
    bks = list(db.execute(select(Booking).where(Booking.cancelled == False)).scalars())   # noqa: E712
    assert bks
    # Đủ các ca: còn nợ, trả đủ, thu thừa, chênh lẻ dưới một đồng (làm tròn hai vế khác nhau).
    ca = [(10_000_000, 0, 4_000_000), (5_000_000, 0, 5_000_000), (3_000_000, 0, 3_500_000),
          (101.5, 0, 101.1), (100.4, 0, 100.0)]
    for b, (a, dc, p) in zip(bks, ca):
        b.amount, b.discount, b.paid = a, dc, p
    db.flush()
    hn = date.today()
    assert CN.phai_thu_khach(db, hn) == _phai_thu_cu(db, hn)


def test_ks_bc_1_tong_hop_bao_cao_ngay_dung_trang_thai_tung_nguoi(db):
    from app.models.core import User
    from app.services import ops as O, bao_cao_ngay_xem as XEM
    u = db.execute(select(User).where(User.username == "chutich")).scalars().first()
    d = date.today() - timedelta(days=1)
    while d.weekday() == 6:
        d -= timedelta(days=1)
    now = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=10)
    kq = XEM.tong_hop(db, u, d, "", now)
    theo = {x["user_id"]: x["thoi_han"] for x in kq["dong"]}
    emps = [e for e in O.nhan_vien_phai_nop(db) if e.user_id in theo]
    assert emps
    for e in emps:   # cách cũ: mỗi người tự hỏi
        assert O.trang_thai_ngay(db, e, e.user_id, d, now)["ma"] == theo[e.user_id], e.user_id


def test_ks_bc_2_so_cau_hoi_khong_tang_theo_so_nhan_vien(db):
    from app.db.session import engine
    from app.models.core import User
    from app.services import bao_cao_ngay_xem as XEM, ops as O
    u = db.execute(select(User).where(User.username == "chutich")).scalars().first()
    d = date.today() - timedelta(days=1)
    n = [0]
    cb = lambda *a, **k: n.__setitem__(0, n[0] + 1)
    event.listen(engine, "before_cursor_execute", cb)
    try:
        kq = XEM.tong_hop(db, u, d, "")
    finally:
        event.remove(engine, "before_cursor_execute", cb)
    so_nv = len(kq["dong"])
    assert so_nv >= 3
    # Trước KS-BC: ≥ 3 câu cho MỖI nhân viên. Nay một số cố định, không nhân theo đầu người.
    assert n[0] < 3 * so_nv, (n[0], so_nv)
