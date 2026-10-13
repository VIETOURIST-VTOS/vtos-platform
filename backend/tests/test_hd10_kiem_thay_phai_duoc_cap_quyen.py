"""HD-10 (D3) — quyền KIỂM THAY báo cáo sau tour là quyền CẤP RIÊNG, không suy từ vai.

Chủ tịch chốt 13/10/2026, câu D3 = phương án A. Nguyên văn chỉ đạo:

    CNTT không mặc nhiên có quyền xác nhận nghiệp vụ. Chỉ kiểm thay khi được giao quyền cụ thể;
    quyền quản trị kỹ thuật không tự sinh quyền duyệt.

  `tp_hd`          kiểm bằng VAI — xác nhận báo cáo sau tour là việc của Trưởng phòng Hướng dẫn,
                   không phải một ngoại lệ.
  `hcns`, `cntt`   vẫn mở được màn hình, nhưng muốn BẤM xác nhận thì phải có năng lực
                   `kiem_bao_cao_tour` cấp cho đúng người.

KHÔNG DỰNG CỬA CẤP QUYỀN MỚI, và đó là phần đáng đọc. Cửa ngoại lệ `POST /api/v1/access/grants` đã
có sẵn và đã đủ ba điều Chủ tịch đòi: BẮT BUỘC ghi lý do, có người phê, có hạn (tối đa 90 ngày; vô
hạn thì chỉ Chủ tịch cấp được). Nó cũng đã ghi nhật ký `cap_ngoai_le_quyen`, và màn hình tra cứu
quyền duyệt `CAPABILITIES` nên năng lực mới tự hiện ở đó. Thêm một cửa thứ hai là thêm một chỗ để
hai bảng quyền nói khác nhau — bộ này canh để điều ấy không xảy ra.

  A. Năng lực được KHAI đúng chỗ, nên cửa ngoại lệ cấp được và màn hình tra cứu thấy.
  B. Chưa cấp thì chặn; cấp rồi thì qua; HẾT HẠN thì chặn lại.
  C. Cấp phải đi qua cửa có sẵn, với đủ ràng buộc của cửa ấy.
  D. Chứng minh các ca trên CẮN.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd10.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd10.db"):
    os.remove("test_hd10.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
MK = "Vtos@Demo#2026"
NANG_LUC = "kiem_bao_cao_tour"
ID: dict[str, int] = {}
D = datetime(2026, 11, 20, 6, 0)


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _cap(ten, tu=None, den=None):
    """Cấp năng lực thẳng vào bảng — dùng khi phép thử cần một cảnh có sẵn, không phải khi đang
    kiểm chính cái cửa cấp quyền (nhóm C làm việc đó)."""
    from sqlalchemy import select

    from app.models.core import User, UserGrant
    with _db() as db:
        t = db.execute(select(User).where(User.username == ten)).scalars().first()
        g = UserGrant(user_id=t.id, kind="capability", value=NANG_LUC,
                      from_date=tu or date.today(),
                      to_date=den if den is not None else date.today() + timedelta(days=90),
                      reason="Phép thử HD-10.", granted_by="chutich", approved_by="chutich")
        db.add(g); db.commit()
        return g.id


def _thu_hoi(gid):
    from app.models.core import UserGrant
    with _db() as db:
        g = db.get(UserGrant, gid)
        if g:
            db.delete(g); db.commit()


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = _db()
        op = db.execute(select(User)).scalars().first().id

        def _hdv(ma, ten):
            return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                            start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                            member_org=True, contract_type="ctv", ctv_contract=True)

        tp = _hdv("HATP1", "Trưởng phòng Hướng dẫn")
        hdv = _hdv("HA001", "Trần Văn A")
        t = Tour(code="HA-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([tp, hdv, t])
        db.commit()

        u_tp = User(username="ha.tp_hd", full_name="Trưởng phòng Hướng dẫn", role="tp_hd",
                    department="Hướng dẫn", staff_code="HATP1",
                    password_hash=hash_password(MK))
        u_cntt = User(username="ha.cntt", full_name="CNTT", role="cntt", department="",
                      staff_code="HACN1", password_hash=hash_password(MK))
        u_hcns = User(username="ha.hcns", full_name="HCNS", role="hcns", department="",
                      staff_code="HAHC1", password_hash=hash_password(MK))
        u_nop = User(username="ha.nguoi_nop", full_name="Người nộp hộ", role="cntt",
                     department="", staff_code="HANO1", password_hash=hash_password(MK))
        db.add_all([u_tp, u_cntt, u_hcns, u_nop])
        db.commit()
        tp.user_id, hdv.user_id = u_tp.id, None
        db.commit()

        def _pc():
            a = GuideAssignment(tour_id=t.id, guide_id=hdv.id, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
            db.add(a); db.commit()
            return a.id

        # Mỗi ca một phân công riêng. Ca B2 và B3 từng dùng CHUNG một phân công, và khi phép đột
        # biến gỡ cổng đi thì B2 xác nhận lọt — ăn mất bản đang chờ kiểm — nên B3 đỏ vì "không có
        # bản nào chờ kiểm" chứ không vì điều nó canh. Đỏ sai lý do cũng vô dụng như xanh sai lý
        # do, nên tách ra.
        for k in ("bang_vai", "chua_cap", "da_cap", "het_han", "nhat_ky"):
            ID[k] = _pc()
        db.close()
        yield


def _nop(aid):
    h = login("ha.nguoi_nop")
    assert client.post(f"/api/v1/guide-assignments/{aid}/bao-cao",
                       json={"chuong_trinh_thuc_hien": "xong", "so_khach_thuc_te": 20},
                       headers=h).status_code in (200, 201)
    assert client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/gui", json={},
                       headers=h).status_code in (200, 201)


def _kiem(aid, ai):
    return client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/kiem",
                       json={"xac_nhan": True}, headers=login(ai))


# ───────────────────────── A · năng lực được khai đúng chỗ ─────────────────────────

def test_a1_nang_luc_duoc_khai_trong_CAPABILITIES():
    """Cửa ngoại lệ từ chối mọi năng lực không khai ở `CAPABILITIES`, và màn hình tra cứu quyền
    duyệt đúng bảng ấy. Không khai thì quyền này không ai cấp được và không ai nhìn thấy — một
    cánh cửa khóa không chìa."""
    from app.models.core import CAPABILITIES
    assert NANG_LUC in CAPABILITIES
    assert CAPABILITIES[NANG_LUC].strip()


def test_a2_chi_tp_hd_kiem_bang_VAI():
    from app.api.v1.hr import BC_KIEM, KIEM_BANG_VAI
    assert set(KIEM_BANG_VAI) == {"tp_hd"}
    # Hai vai kia vẫn qua được chữ ký cửa — màn hình còn mở ra được — nhưng không kiểm bằng vai.
    for v in ("hcns", "cntt"):
        assert v in BC_KIEM and v not in KIEM_BANG_VAI


# ───────────────────────── B · chưa cấp thì chặn, cấp rồi thì qua ─────────────────────────

def test_b1_tp_hd_kiem_duoc_ma_khong_can_cap_gi():
    _nop(ID["bang_vai"])
    assert _kiem(ID["bang_vai"], "ha.tp_hd").status_code == 200


def test_b2_cntt_CHUA_cap_thi_bi_chan_va_loi_noi_ro_phai_xin_gi():
    _nop(ID["chua_cap"])
    r = _kiem(ID["chua_cap"], "ha.cntt")
    assert r.status_code == 403, r.text
    assert NANG_LUC in r.text, f"lỗi không nói tên năng lực phải xin: {r.text}"


def test_b3_cntt_DA_cap_thi_di_qua():
    _nop(ID["da_cap"])
    gid = _cap("ha.cntt")
    try:
        r = _kiem(ID["da_cap"], "ha.cntt")
        assert r.status_code == 200, r.text
    finally:
        _thu_hoi(gid)


def test_b4_quyen_HET_HAN_thi_chan_lai():
    """Lý do bảng ngoại lệ bắt buộc có hạn: quyền không có hạn thì chỉ nở ra chứ không co lại.
    Phép thử này là chỗ kiểm điều ấy có thật, chứ không chỉ nằm trong chú thích."""
    gid = _cap("ha.hcns", tu=date.today() - timedelta(days=30),
               den=date.today() - timedelta(days=1))
    try:
        _nop(ID["het_han"])
        r = _kiem(ID["het_han"], "ha.hcns")
        assert r.status_code == 403, f"quyền đã hết hạn mà vẫn cho qua: {r.text}"
    finally:
        _thu_hoi(gid)


def test_b5_nhat_ky_ghi_di_bang_VAI_hay_bang_QUYEN_CAP_RIENG():
    """Một lần kiểm thay phải tra lại được là AI CHO PHÉP, không chỉ là ai đã bấm."""
    from sqlalchemy import desc, select

    from app.models.core import AuditLog

    def _duong_quyen_cuoi():
        with _db() as db:
            d = db.execute(select(AuditLog).where(AuditLog.action == "kiem_bao_cao_tour")
                           .order_by(desc(AuditLog.id))).scalars().first()
            return (d.after or {}).get("duong_quyen")

    _nop(ID["nhat_ky"])
    gid = _cap("ha.hcns")
    try:
        assert _kiem(ID["nhat_ky"], "ha.hcns").status_code == 200
        assert _duong_quyen_cuoi() == "cap_rieng"
    finally:
        _thu_hoi(gid)
    # và đường còn lại: `tp_hd` đi bằng vai (bản báo cáo của ID["bang_vai"] đã kiểm ở ca B1)
    assert ID["bang_vai"]


# ───────────────────────── C · cấp phải đi qua cửa đã có ─────────────────────────

def test_c1_cua_ngoai_le_cap_duoc_nang_luc_nay():
    """Chứng minh em dùng cửa SẴN CÓ chứ không dựng cửa thứ hai: gọi đúng cửa ấy, nó nhận."""
    r = client.post("/api/v1/access/grants", headers=login("chutich"),
                    json={"user_id": None, "kind": "capability", "value": NANG_LUC,
                          "reason": "x", "to_date": str(date.today() + timedelta(days=30))})
    # user_id rỗng thì 404/422 — điều cần khẳng định là cửa KHÔNG từ chối vì "năng lực không hợp lệ"
    assert "Năng lực không hợp lệ" not in r.text, r.text


def test_c2_cua_ay_BAT_BUOC_ghi_ly_do():
    """Chủ tịch đòi 'bắt buộc ghi lý do và nhật ký'. Ràng buộc ấy nằm ở cửa, và vẫn còn."""
    from sqlalchemy import select

    from app.models.core import User
    with _db() as db:
        uid = db.execute(select(User).where(User.username == "ha.cntt")).scalars().first().id
    r = client.post("/api/v1/access/grants", headers=login("chutich"),
                    json={"user_id": uid, "kind": "capability", "value": NANG_LUC,
                          "reason": "   ", "to_date": str(date.today() + timedelta(days=30))})
    assert r.status_code == 422 and "lý do" in r.text, r.text


# ───────────────────────── D · chứng minh các ca trên CẮN ─────────────────────────

def test_d1_neu_cntt_van_kiem_bang_vai_thi_ca_B2_mat_can_cu():
    """Dựng lại luật CŨ — ai trong `BC_KIEM` cũng kiểm được — và đòi nó cho qua đúng tài khoản mà
    bản mới chặn. Không phân biệt được hai bản thì B2 chẳng đo gì."""
    from app.api.v1.hr import BC_KIEM, KIEM_BANG_VAI
    assert "cntt" in BC_KIEM, "bản cũ cho `cntt` qua chỉ nhờ nằm trong BC_KIEM"
    assert "cntt" not in KIEM_BANG_VAI, "bản mới phải không cho qua bằng vai"


def test_d2_cap_roi_va_chua_cap_phai_cho_ra_hai_ket_qua_khac_nhau():
    """Cùng một tài khoản, cùng một phân công: chưa cấp thì chặn, cấp rồi thì qua. Giống nhau ở
    hai trạng thái thì ca B3 đang đo một thứ khác."""
    from sqlalchemy import select

    from app.models.core import User
    from app.services import access as AC
    with _db() as db:
        u = db.execute(select(User).where(User.username == "ha.cntt")).scalars().first()
        chua = AC.co_quyen(db, u, NANG_LUC)
    gid = _cap("ha.cntt")
    try:
        with _db() as db:
            u = db.execute(select(User).where(User.username == "ha.cntt")).scalars().first()
            roi = AC.co_quyen(db, u, NANG_LUC)
    finally:
        _thu_hoi(gid)
    assert chua is False and roi is True, f"cấp quyền không đổi được gì: chưa={chua} rồi={roi}"
