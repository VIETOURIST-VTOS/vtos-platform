"""Vòng kéo bù Facebook chèn lặp toàn bộ lịch sử hội thoại mỗi lần chạy.

Đo trên dữ liệu thật ngày 07/9/2026: bảng messages có 117.208 dòng, nhưng hội thoại #10 có 778 tin
mà chỉ 11 nội dung khác nhau – mỗi nội dung lặp 78 lần, đúng bằng số lượt robot đã chạy.

Nguyên nhân: cột external_id chỉ 80 ký tự nên lúc GHI bị cắt bằng [:80], còn lúc KIỂM TRÙNG lại so
với chuỗi đầy đủ. mid của Facebook dài hơn 80 nên phép so không bao giờ khớp, và mỗi lượt kéo bù lại
chèn thêm một bản của toàn bộ lịch sử.

Đây là kiểu lỗi im lặng nguy hiểm: không có ngoại lệ, không có log lỗi, chỉ có bảng phình ra.
"""
import os, sys
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_tintrung.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_tintrung.db"): os.remove("test_tintrung.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
MID_DAI = "m_" + "A" * 120        # mid thật của Facebook dài hơn 80 ký tự


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_mid_dai_hon_80_ky_tu_van_phai_chan_duoc_trung():
    from app.db.session import SessionLocal
    from app.services import inbox as IB
    from app.models.crm import Message
    from sqlalchemy import select, func
    db = SessionLocal()
    m1 = IB.inbound(db, "facebook", "psid-1", "a lô", "page-1", "Khách A", MID_DAI)
    assert m1 is not None
    for _ in range(5):      # năm lượt kéo bù tiếp theo, cùng một tin
        assert IB.inbound(db, "facebook", "psid-1", "a lô", "page-1", "Khách A", MID_DAI) is None
    n = db.execute(select(func.count()).select_from(Message).where(Message.conversation_id == m1.conversation_id)).scalar()
    assert n == 1, f"tin lặp {n} lần dù cùng mid"
    db.close()


def test_thoi_diem_tin_lich_su_duoc_ghi_dung_khong_phai_luc_nap():
    from app.db.session import SessionLocal
    from app.services import inbox as IB
    db = SessionLocal()
    cu = datetime.now() - timedelta(days=30)
    m = IB.inbound(db, "facebook", "psid-2", "tin cũ 30 ngày", "page-1", "Khách B", "m_" + "B" * 120, None, cu)
    assert m is not None and abs((m.at - cu).total_seconds()) < 2, "tin lịch sử phải giữ đúng thời điểm gốc"
    db.close()


def test_dem_va_don_tin_trung_giu_lai_ban_dau_tien():
    from app.db.session import SessionLocal
    from app.models.crm import Message
    from sqlalchemy import select, func
    db = SessionLocal()
    cid = db.execute(select(Message.conversation_id)).scalars().first()
    for _ in range(7):      # dựng lại đúng cảnh đã xảy ra: cùng nội dung, không có mid
        db.add(Message(conversation_id=cid, direction="in", sender="khach", text="A cần đi âu châu"))
    db.commit()
    giu = db.execute(select(func.min(Message.id)).where(Message.text == "A cần đi âu châu")).scalar()
    db.close()

    d = client.get("/api/v1/inbox/tin-trung/kiem", headers=login("cntt")).json()
    assert d["so_ban_thua"] == 6 and d["con_lai_sau_khi_don"] == d["tong_tin"] - 6
    assert client.post("/api/v1/inbox/tin-trung/don", headers=login("hcns")).status_code == 403   # không phải ai cũng xoá được
    r = client.post("/api/v1/inbox/tin-trung/don", headers=login("cntt")).json()
    assert r["da_xoa"] == 6

    db = SessionLocal()
    con = db.execute(select(Message.id).where(Message.text == "A cần đi âu châu")).scalars().all()
    assert con == [giu], "phải giữ đúng bản đầu tiên"
    db.close()
    assert client.get("/api/v1/inbox/tin-trung/kiem", headers=login("cntt")).json()["so_ban_thua"] == 0
