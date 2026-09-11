"""VPM-5 – một khoản tiền chia được cho nhiều booking.

Vì sao bộ kiểm này tồn tại: trước 11/9/2026 `receipts.booking_id` và `bank_transactions.booking_id`
đều là khoá ĐƠN. Khách chuyển một lần cho hai tour thì hệ thống KHÔNG làm được — không phải làm chưa
đẹp. UAT-06 và UAT-07 dựa vào chỗ này, nên bộ kiểm phải canh đúng cái ranh giới ấy: không chỉ "chia
được", mà chia xong thì SỔ SÁCH VẪN ĐÚNG và SỐ DƯ VẪN NÓI THẬT.

Bốn nhóm:
  A  CHIA ĐƯỢC – và mỗi dòng sinh đúng một phiếu thu, booking.paid theo kịp
  B  KHÔNG TẠO RA TIỀN – tổng phân bổ không vượt số tiền của giao dịch, cả lô hỏng thì không ghi gì
  C  SỐ DƯ NÓI THẬT – cột lưu luôn khớp với tổng các dòng, kể cả sau khi huỷ
  D  HUỶ CHỨ KHÔNG XOÁ – dòng huỷ còn lại kèm lý do, phiếu thu đi theo, tiền trả về số dư
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm5.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
os.environ["SEPAY_WEBHOOK_KEY"] = "test-key"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.SEPAY_WEBHOOK_KEY = "test-key"

client = TestClient(app)
TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


_SO = {"n": 7700}


def _giao_dich(so_tien: float, noi_dung: str = "CHUYEN TIEN KHONG GHI MA") -> int:
    """Một khoản tiền vào KHÔNG khớp được tự động – đúng tình huống cần phân bổ tay."""
    _SO["n"] += 1
    r = client.post("/api/v1/sepay/webhook", headers={"Authorization": "Apikey test-key"},
                    json={"id": _SO["n"], "gateway": "TPBank", "transactionDate": "2026-09-05 09:00:00",
                          "accountNumber": "0001", "transferType": "in", "transferAmount": so_tien,
                          "content": noi_dung, "referenceCode": f"REF{_SO['n']}"})
    assert r.status_code in (200, 201), r.text
    ds = client.get("/api/v1/bank-transactions", headers=login("ketoan")).json()
    return next(t["id"] for t in ds if t["sepay_id"] == str(_SO["n"]))


def _hai_booking():
    bs = client.get("/api/v1/bookings", headers=login("ketoan")).json()
    con = [b for b in bs if not b.get("cancelled")]
    assert len(con) >= 2, "dữ liệu mẫu cần ít nhất hai booking"
    return con[0], con[1]


# ══════════════════ A – CHIA ĐƯỢC ══════════════════
def test_a1_mot_khoan_tien_chia_duoc_cho_HAI_booking():
    """Chính là việc hệ thống cũ KHÔNG làm được. Nếu phép thử này đỏ thì VPM-5 chưa xong."""
    b1, b2 = _hai_booking()
    tid = _giao_dich(5_000_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 3_000_000, "ghi_chu": "phần tour 1"},
                                   {"booking_id": b2["id"], "so_tien": 2_000_000, "ghi_chu": "phần tour 2"}]})
    assert r.status_code == 200, r.text
    assert r.json()["da_them"] == 2
    assert r.json()["chua_phan_bo"] == 0

    b = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    assert b["da_phan_bo"] == 5_000_000 and b["chua_phan_bo"] == 0
    assert {d["booking_id"] for d in b["dong"]} == {b1["id"], b2["id"]}


def test_a2_moi_dong_phan_bo_sinh_DUNG_MOT_phieu_thu():
    """Dòng phân bổ không thay phiếu thu, nó sinh ra phiếu thu – nếu không thì booking.paid và sổ kế
    toán có hai nguồn khác nhau cho cùng một câu hỏi 'đã thu bao nhiêu'."""
    b1, _ = _hai_booking()
    truoc = client.get(f"/api/v1/bookings/{b1['id']}", headers=login("ketoan")).json().get("paid") or 0
    tid = _giao_dich(1_200_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 1_200_000}]})
    assert r.status_code == 200, r.text
    bang = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    assert bang["dong"][0]["phieu_thu"], "dòng phân bổ không sinh phiếu thu"
    sau = client.get(f"/api/v1/bookings/{b1['id']}", headers=login("ketoan")).json().get("paid") or 0
    assert round(sau - truoc) == 1_200_000, "booking.paid không theo kịp phân bổ"


def test_a3_chia_lam_NHIEU_LAN_chu_khong_bat_lam_mot_lan():
    """Kế toán thường chỉ biết phần thứ hai vào hôm sau. Ép khai đủ ngay là ép đoán."""
    b1, b2 = _hai_booking()
    tid = _giao_dich(4_000_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 1_000_000}]})
    giua = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    assert giua["chua_phan_bo"] == 3_000_000
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b2["id"], "so_tien": 3_000_000}]})
    cuoi = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    assert cuoi["chua_phan_bo"] == 0 and len([d for d in cuoi["dong"] if not d["huy"]]) == 2


# ══════════════════ B – KHÔNG TẠO RA TIỀN ══════════════════
def test_b1_tong_phan_bo_KHONG_duoc_vuot_so_tien_giao_dich():
    b1, b2 = _hai_booking()
    tid = _giao_dich(1_000_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 600_000},
                                   {"booking_id": b2["id"], "so_tien": 600_000}]})
    assert r.status_code == 422 and "vượt" in r.json()["detail"]


def test_b2_ca_lo_hong_thi_KHONG_GHI_GI_CA():
    """Ghi được hai dòng rồi hỏng ở dòng thứ ba để lại trạng thái không ai đọc được: tiền vào sổ một
    nửa, và người dùng không biết nên bấm lại hay không."""
    b1, b2 = _hai_booking()
    tid = _giao_dich(3_000_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 1_000_000},
                                   {"booking_id": b2["id"], "so_tien": 1_000_000},
                                   {"booking_id": 999_999, "so_tien": 500_000}]})
    assert r.status_code == 422
    bang = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    assert bang["dong"] == [] and bang["chua_phan_bo"] == 3_000_000, "lô hỏng mà vẫn ghi được vài dòng"


def test_b3_so_tien_khong_duong_thi_tu_choi():
    b1, _ = _hai_booking()
    tid = _giao_dich(1_000_000)
    for xau in (0, -5000):
        r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                        json={"dong": [{"booking_id": b1["id"], "so_tien": xau}]})
        assert r.status_code == 422


def test_b4_thu_du_thi_CANH_BAO_chu_khong_chan():
    """Khách trả dư là chuyện có thật hằng ngày. Chặn ở đây chỉ đẩy kế toán sang ghi chú tay, và lúc
    ấy hệ thống mất dấu vết thay vì có thêm."""
    b1, _ = _hai_booking()
    tid = _giao_dich(900_000_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 900_000_000}]})
    assert r.status_code == 200, r.text
    assert r.json()["canh_bao"], "thu dư mà không cảnh báo gì"


def test_b5_tien_RA_khong_phan_bo_cho_booking():
    """Tiền ra khớp với lệnh chi, không phải với booking. Mở ở đây là mở một đường ghi doanh thu từ
    một khoản chi."""
    _SO["n"] += 1
    client.post("/api/v1/sepay/webhook", headers={"Authorization": "Apikey test-key"},
                json={"id": _SO["n"], "gateway": "TPBank", "transactionDate": "2026-09-05 10:00:00",
                      "accountNumber": "0001", "transferType": "out", "amount_out": 500_000,
                      "content": "CHI TIEN", "referenceCode": f"OUT{_SO['n']}"})
    ds = client.get("/api/v1/bank-transactions", headers=login("ketoan")).json()
    tid = next(t["id"] for t in ds if t["sepay_id"] == str(_SO["n"]))
    b1, _ = _hai_booking()
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 100_000}]})
    assert r.status_code == 422 and "tiền VÀO" in r.json()["detail"]


# ══════════════════ C – SỐ DƯ NÓI THẬT ══════════════════
def test_c1_cot_luu_LUON_khop_voi_tong_cac_dong():
    """`chua_phan_bo` là bản chép lại của một phép tính. Bản chép lại thì có ngày lệch – nên phải có
    đúng một phép thử đứng canh chỗ ấy, tính lại từ nguồn và so tuyệt đối."""
    from app.db.session import SessionLocal
    from app.models.payments import BankTransaction
    from app.services import phan_bo_tien as PB
    with SessionLocal() as db:
        lech = []
        for t in db.execute(select(BankTransaction)).scalars():
            dong = PB.cac_dong(db, t.id)
            if not dong:
                continue
            that = round(float(t.amount or 0) - sum(float(d.so_tien or 0) for d in dong), 2)
            if round(float(t.chua_phan_bo if t.chua_phan_bo is not None else -1), 2) != that:
                lech.append(f"giao dịch {t.id}: cột lưu {t.chua_phan_bo} ≠ tính lại {that}")
        assert not lech, lech


def test_c2_giao_dich_CHUA_TUNG_phan_bo_thi_cot_du_la_RONG_khong_phai_0():
    """Rỗng = chưa ai chia khoản này. 0 = đã chia hết. Trộn hai cái đó là bảng bắt đầu nói dối."""
    tid = _giao_dich(2_500_000)
    t = next(x for x in client.get("/api/v1/bank-transactions", headers=login("ketoan")).json()
             if x["id"] == tid)
    assert t["chua_phan_bo"] is None and t["so_dong_phan_bo"] == 0


def test_c3_con_du_thi_giao_dich_VAN_LA_VIEC_DANG_DO():
    """Đánh dấu 'đã khớp' khi còn dư là cách một khoản tiền biến mất khỏi danh sách việc mà chưa xong."""
    b1, _ = _hai_booking()
    tid = _giao_dich(6_000_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 1_000_000}]})
    t = next(x for x in client.get("/api/v1/bank-transactions", headers=login("ketoan")).json()
             if x["id"] == tid)
    assert t["match_status"] == "cho_ke_toan" and t["chua_phan_bo"] == 5_000_000
    assert "chưa phân bổ" in t["match_note"]


# ══════════════════ D – HUỶ CHỨ KHÔNG XOÁ ══════════════════
def test_d1_huy_dong_thi_tien_TRA_VE_so_du_va_phieu_thu_di_theo():
    b1, _ = _hai_booking()
    tid = _giao_dich(2_000_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 2_000_000}]})
    bang = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    dong, ma_pt = bang["dong"][0], bang["dong"][0]["phieu_thu"]
    truoc = client.get(f"/api/v1/bookings/{b1['id']}", headers=login("ketoan")).json().get("paid") or 0

    r = client.post(f"/api/v1/bank-transactions/phan-bo/{dong['id']}/huy", headers=login("ketoan"),
                    json={"ly_do": "Kế toán gán nhầm booking"})
    assert r.status_code == 200, r.text
    assert r.json()["chua_phan_bo"] == 2_000_000

    sau = client.get(f"/api/v1/bookings/{b1['id']}", headers=login("ketoan")).json().get("paid") or 0
    assert round(truoc - sau) == 2_000_000, "huỷ phân bổ mà booking.paid không giảm theo"
    pt = next(x for x in client.get("/api/v1/receipts", headers=login("ketoan")).json() if x["code"] == ma_pt)
    assert pt["status"] == "huy", "dòng phân bổ huỷ mà phiếu thu của nó vẫn sống"


def test_d2_dong_da_huy_VAN_CON_trong_so_kem_ly_do():
    """Xoá dòng là xoá mất bằng chứng rằng tiền đã từng được hiểu sai – đúng thứ người tra cứu cần."""
    b1, _ = _hai_booking()
    tid = _giao_dich(1_500_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 1_500_000}]})
    did = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()["dong"][0]["id"]
    client.post(f"/api/v1/bank-transactions/phan-bo/{did}/huy", headers=login("ketoan"), json={"ly_do": "khách báo nhầm tour"})
    bang = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()
    d = next(x for x in bang["dong"] if x["id"] == did)
    assert d["huy"] and d["huy_ly_do"] == "khách báo nhầm tour" and d["huy_boi"] == "ketoan"


def test_d3_huy_KHONG_LY_DO_thi_tu_choi():
    b1, _ = _hai_booking()
    tid = _giao_dich(800_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 800_000}]})
    did = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()["dong"][0]["id"]
    r = client.post(f"/api/v1/bank-transactions/phan-bo/{did}/huy", headers=login("ketoan"), json={"ly_do": "   "})
    assert r.status_code == 422 and "lý do" in r.json()["detail"]


def test_d4_huy_het_thi_giao_dich_quay_ve_CHO_KE_TOAN():
    b1, _ = _hai_booking()
    tid = _giao_dich(700_000)
    client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan"),
                json={"dong": [{"booking_id": b1["id"], "so_tien": 700_000}]})
    did = client.get(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("ketoan")).json()["dong"][0]["id"]
    client.post(f"/api/v1/bank-transactions/phan-bo/{did}/huy", headers=login("ketoan"), json={"ly_do": "phân bổ lại"})
    t = next(x for x in client.get("/api/v1/bank-transactions", headers=login("ketoan")).json() if x["id"] == tid)
    assert t["match_status"] == "cho_ke_toan" and t["so_dong_phan_bo"] == 0


# ══════════════════ HÀNG RÀO QUYỀN ══════════════════
def test_e1_chi_ke_toan_va_cntt_duoc_phan_bo():
    """Phân bổ là quyết định KẾ TOÁN về việc tiền của ai. Sale xem được, không quyết được."""
    b1, _ = _hai_booking()
    tid = _giao_dich(1_000_000)
    r = client.post(f"/api/v1/bank-transactions/{tid}/phan-bo", headers=login("kd.hoa"),
                    json={"dong": [{"booking_id": b1["id"], "so_tien": 1_000_000}]})
    assert r.status_code == 403
