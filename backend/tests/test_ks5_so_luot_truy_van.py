"""KS-5 · Số lượt truy vấn không được tăng theo số bản ghi, và danh sách phải có trần.

Đếm LƯỢT chứ không bấm giờ. Thời gian phụ thuộc máy và lúc đo nên chỉ nói nhanh/chậm; số lượt truy
vấn nói được đúng/sai: số lượt tăng theo số dòng nghĩa là có truy vấn nằm trong vòng lặp, và điều đó
đúng ở mọi máy.

Ngày 10/9/2026 màn hình Khoản treo mất 55 giây mới mở, do đệm tham số tra lại theo từng dòng. Bấm
giờ chỉ nói "chậm"; đếm lượt nói thẳng số lượt tăng theo số dòng và chỉ đúng chỗ.

  T1  máy đếm phải đếm đúng (tự kiểm) — không có bước này thì mọi con số dưới đây vô nghĩa
  T2  gấp đôi số bản ghi, số lượt truy vấn phải GIỮ NGUYÊN
  T3  một lần đọc danh sách không được vượt trần số lượt
  T4  mọi danh sách phải có trần, và chỗ chưa có trần phải có tên trong bảng khai
  T5  chạm trần thì phải NÓI RA — cắt thì được, im lặng thì không

T4 và T5 đỏ ở GET /api/v1/alerts là có chủ đích: đó là việc còn nợ đang được đếm.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_ks5_truyvan.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_ks5_truyvan.db", "test_ks5_truyvan.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.models.core import Alert, Tour, User  # noqa: E402
from tools import ks5_dem_truy_van as D  # noqa: E402

client = TestClient(app)
MK = "ks5mk123456"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        if db.execute(select(User).where(User.username == "ks5_cntt")).scalars().first() is None:
            db.add(User(username="ks5_cntt", full_name="Thử KS5", role="cntt",
                        department="Kiểm thử", password_hash=hash_password(MK), active=True))
            db.commit()
        db.close()
        yield


def dang_nhap():
    r = client.post("/api/v1/auth/login", data={"username": "ks5_cntt", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


def _them_canh_bao(n: int, tu: int = 0):
    db = db_()
    for i in range(tu, tu + n):
        db.add(Alert(kind="ks5_thu", level="warn", ref=f"ks5:{i}",
                     message=f"dòng thử {i}", to_roles="cntt"))
    db.commit()
    db.close()


def _them_tour(n: int, tu: int = 0):
    db = db_()
    op = db.execute(select(User).where(User.role == "nv_dh")).scalars().first() \
        or db.execute(select(User)).scalars().first()
    d = date.today() + timedelta(days=30)
    for i in range(tu, tu + n):
        db.add(Tour(code=f"KS5-T-{i:04d}", name=f"Chuyến thử {i}", tour_type="le",
                    start_date=d, end_date=d + timedelta(days=2), operator_id=op.id,
                    status="nhap", planned_pax=10))
    db.commit()
    db.close()


# ------------------------------------------------------------------ T1

def test_t1_may_dem_phai_dem_dung():
    """Tự kiểm máy đo trước khi tin số nó đưa ra.

    Một bộ kiểm hiệu năng đếm sai còn tệ hơn không có: nó cho điểm xanh cho đúng thứ nó không thấy.
    """
    db = db_()
    with D.dem_truy_van() as so:
        db.execute(select(Alert).limit(1)).scalars().first()
        db.execute(select(Tour).limit(1)).scalars().first()
    db.close()
    assert so["n"] >= 2, f"chạy 2 truy vấn mà máy đếm ghi {so['n']} — máy đếm không bắt được sự kiện"


# ------------------------------------------------------------------ T2, T3

@pytest.mark.parametrize("duong,them", [
    ("/api/v1/alerts", _them_canh_bao),
    ("/api/v1/tours", _them_tour),
])
def test_t2_so_luot_khong_duoc_tang_theo_so_ban_ghi(duong, them):
    """Gấp đôi số dòng, số lượt truy vấn phải GIỮ NGUYÊN.

    Đây là phép thử bắt truy vấn trong vòng lặp mà đọc mã không thấy: quan hệ lười của SQLAlchemy
    sinh truy vấn lúc chạy, không lúc viết. Đúng loại đã làm màn hình Khoản treo mất 55 giây.
    """
    h = dang_nhap()
    them(40, 0)
    with D.dem_truy_van() as lan1:
        r1 = client.get(duong, headers=h)
    assert r1.status_code == 200, r1.text

    them(40, 40)
    with D.dem_truy_van() as lan2:
        r2 = client.get(duong, headers=h)
    assert r2.status_code == 200, r2.text

    assert lan2["n"] <= lan1["n"], (
        f"{duong}: 40 dòng → {lan1['n']} lượt truy vấn; 80 dòng → {lan2['n']} lượt. "
        f"Số lượt tăng theo số bản ghi nghĩa là có truy vấn nằm trong vòng lặp.\n"
        f"  Câu lặp nhiều nhất ở lượt hai: "
        f"{list(D.nhom_cau(lan2).items())[:3]}\n"
        f"  Sửa bằng selectinload/joinedload hoặc nạp một lượt rồi tra trong bộ nhớ — "
        f"KHÔNG sửa bằng cách nới trần.")


@pytest.mark.parametrize("duong", ["/api/v1/alerts", "/api/v1/tours"])
def test_t3_mot_lan_doc_danh_sach_khong_vuot_tran_so_luot(duong):
    h = dang_nhap()
    with D.dem_truy_van() as so:
        r = client.get(duong, headers=h)
    assert r.status_code == 200, r.text
    assert so["n"] <= D.TRAN_LUOT_DOC_DANH_SACH, (
        f"{duong} dùng {so['n']} lượt truy vấn cho một lần đọc (trần {D.TRAN_LUOT_DOC_DANH_SACH}).\n"
        f"  Câu lặp nhiều nhất: {list(D.nhom_cau(so).items())[:5]}")


# ------------------------------------------------------------------ T4

def test_t4_moi_danh_sach_phai_co_tran_hoac_co_ten_trong_bang_khai():
    """Chỗ chưa có trần phải có tên và lý do — để nó là một dòng đếm được, không phải chỗ im lặng.

    ĐỎ ở đây là việc còn nợ đang được đếm. Xoá dòng khai không làm hết nợ, chỉ làm hết đếm.
    """
    chua = {d: D.LY_DO_CHUA_CO_TRAN.get(d) for d, t in D.TRAN_DANH_SACH.items() if t is None}
    khong_ly_do = [d for d, ly in chua.items() if not ly]
    assert not khong_ly_do, (
        f"danh sách chưa có trần mà cũng không khai lý do: {khong_ly_do} — "
        f"thêm vào LY_DO_CHUA_CO_TRAN trong tools/ks5_dem_truy_van.py")
    assert not chua, (
        f"{len(chua)} phép đọc danh sách chưa có trần:\n"
        + "\n".join(f"  · {d}\n      {ly}" for d, ly in sorted(chua.items()))
        + "\n\n  Danh sách không trần nghĩa là số dòng trả về tăng mãi theo dữ liệu; "
          "hôm nay 1.703 dòng, sang năm không ai biết.")


# ------------------------------------------------------------------ T5

def test_t5_cham_tran_thi_phai_noi_ra():
    """Cắt thì được, im lặng thì không.

    Danh sách âm thầm cắt ở 300 dòng nguy hiểm hơn danh sách chậm: người đọc tin mình đang nhìn toàn
    bộ và ra quyết định trên phần bị cắt mà không biết mình chỉ nhìn một phần.
    """
    h = dang_nhap()
    tran = D.TRAN_DANH_SACH["GET /api/v1/tours"]
    db = db_()
    dang_co = len(db.execute(select(Tour)).scalars().all())
    db.close()
    if dang_co <= tran:
        _them_tour(tran - dang_co + 20, tu=9000)

    r = client.get("/api/v1/tours", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body if isinstance(body, list) else body.get("rows", body)
    assert len(rows) <= tran, f"trần {tran} mà trả về {len(rows)} dòng — trần không có tác dụng"

    noi_ra = isinstance(body, dict) and any(k in body for k in D.KHOA_NOI_RA)
    assert noi_ra, (
        f"GET /api/v1/tours cắt ở {tran} dòng nhưng phản hồi là một mảng trần, không có chỗ nào nói "
        f"rằng đã cắt. Giao diện không có cách nào biết để báo cho người đọc.\n"
        f"  Cách sửa: trả về {{\"rows\": [...], \"tong\": <tổng thật>, \"cham_tran\": true/false}} — "
        f"một trong các khoá {D.KHOA_NOI_RA}.\n"
        f"  Chủ: lane Viết phần mềm. Đây là việc còn nợ đang được đếm, không phải phép thử hỏng.")
