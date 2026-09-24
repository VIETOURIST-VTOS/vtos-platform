"""Kế hoạch & ngân sách marketing – Đợt 2.

Điểm sống còn của màn hình này là KHÔNG có ô nào cho người gõ "đã chi bao nhiêu". Đã chi đọc từ đề nghị
chi đã duyệt; màn hình ngân sách chỉ giữ phần dự toán. Hai nơi giữ hai con số chi phí của cùng một kỳ
là hai con số sẽ lệch nhau, và không ai biết tin con số nào.

  N1 kỳ sai định dạng, thiếu căn cứ, thiếu mục tiêu lead → không lập được
  N2 một kỳ × một pháp nhân chỉ một ngân sách còn hiệu lực
  N3 người lập không tự duyệt
  N4 đã chi / đang treo đọc từ đề nghị chi, tách theo hạng mục
  N5 chi chưa gán hạng mục nêu riêng, KHÔNG chia bừa vào hạng mục khác
  N6 chi vượt phần còn lại của hạng mục → cờ ngoài dự toán (từ 23/9/2026 KHÔNG còn bật hai chữ ký)
  N7 chưa có ngân sách hiệu lực KHÔNG phải là ngân sách vô hạn
  N8 kỳ quý cộng đúng chi phí của cả ba tháng
"""
import os, sys
from datetime import date, datetime
os.environ["DATABASE_URL"] = "sqlite:///./test_nsmkt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nsmkt.db"): os.remove("test_nsmkt.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}
KY = f"{date.today():%Y-%m}"


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


BASE = {"period": KY, "target_leads": 400, "target_revenue": 2_000_000_000,
        "rationale": "Theo doanh thu kỳ trước và mốc chỉ tiêu quý 4",
        "lines": [{"hang_muc": "quang_cao", "amount": 30_000_000},
                  {"hang_muc": "noi_dung", "amount": 10_000_000}]}


def test_n1_thieu_can_cu_thieu_muc_tieu_ky_sai_thi_khong_lap_duoc():
    mk = login("cntt")
    assert client.post("/api/v1/marketing/budgets", json=dict(BASE, period="2026/09"), headers=mk).status_code == 422
    assert client.post("/api/v1/marketing/budgets", json=dict(BASE, rationale=""), headers=mk).status_code == 422
    assert client.post("/api/v1/marketing/budgets", json=dict(BASE, target_leads=0), headers=mk).status_code == 422
    assert client.post("/api/v1/marketing/budgets", json=dict(BASE, lines=[]), headers=mk).status_code == 422
    # hai dòng cùng một hạng mục
    xau = dict(BASE, lines=[{"hang_muc": "quang_cao", "amount": 1}, {"hang_muc": "quang_cao", "amount": 2}])
    assert client.post("/api/v1/marketing/budgets", json=xau, headers=mk).status_code == 422


def test_n2_mot_ky_chi_mot_ngan_sach_con_hieu_luc():
    mk = login("cntt")
    b = client.post("/api/v1/marketing/budgets", json=BASE, headers=mk).json()["budget"]
    CTX["id"] = b["id"]
    assert b["status"] == "nhap"
    client.post(f"/api/v1/marketing/budgets/{b['id']}/trinh", headers=mk)
    r = client.post("/api/v1/marketing/budgets", json=BASE, headers=mk)
    assert r.status_code == 422 and "đã có ngân sách" in r.json()["detail"]


def test_n3_nguoi_lap_khong_tu_duyet():
    bid = CTX["id"]
    assert client.post(f"/api/v1/marketing/budgets/{bid}/duyet", headers=login("cntt")).status_code == 403
    r = client.post(f"/api/v1/marketing/budgets/{bid}/duyet", headers=login("tgd"))
    assert r.status_code == 200 and r.json()["budget"]["status"] == "hieu_luc"


def test_n4_da_chi_va_dang_treo_doc_tu_de_nghi_chi_tach_theo_hang_muc():
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    db.add(PaymentRequest(code="NS-01", category="marketing", marketing_muc="quang_cao", supplier_name="Meta",
                          amount=12_000_000, description="Ads", status="da_chi", created_by="cntt"))
    db.add(PaymentRequest(code="NS-02", category="marketing", marketing_muc="quang_cao", supplier_name="Google",
                          amount=5_000_000, description="Ads", status="cho_kt", created_by="cntt"))
    db.add(PaymentRequest(code="NS-03", category="marketing", marketing_muc="noi_dung", supplier_name="Studio",
                          amount=3_000_000, description="Quay clip", status="da_chi", created_by="cntt"))
    db.add(PaymentRequest(code="NS-04", category="marketing", marketing_muc="quang_cao", supplier_name="X",
                          amount=99_000_000, description="Bị từ chối", status="tu_choi", created_by="cntt"))
    db.commit(); db.close()
    bang = client.get(f"/api/v1/marketing/budgets/{CTX['id']}", headers=login("ptgd.mkt")).json()["bang"]
    qc = [r for r in bang["rows"] if r["hang_muc"] == "quang_cao"][0]
    assert qc["da_chi"] == 12_000_000 and qc["dang_treo"] == 5_000_000        # từ chối không tính vào đâu cả
    assert qc["con_lai"] == 30_000_000 - 17_000_000 and qc["vuot"] is False
    nd = [r for r in bang["rows"] if r["hang_muc"] == "noi_dung"][0]
    assert nd["da_chi"] == 3_000_000
    assert bang["chi_phi_lead_ke_hoach"] == 40_000_000 / 400


def test_n5_chi_chua_gan_hang_muc_neu_rieng_khong_chia_bua():
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    db.add(PaymentRequest(code="NS-05", category="marketing", marketing_muc="", supplier_name="Chưa rõ",
                          amount=7_000_000, description="Chưa gán mục", status="da_chi", created_by="cntt"))
    db.commit(); db.close()
    bang = client.get(f"/api/v1/marketing/budgets/{CTX['id']}", headers=login("ptgd.mkt")).json()["bang"]
    assert bang["chua_phan_muc"]["da_chi"] == 7_000_000
    qc = [r for r in bang["rows"] if r["hang_muc"] == "quang_cao"][0]
    assert qc["da_chi"] == 12_000_000, "khoản chưa gán mục không được cộng vào hạng mục nào"
    assert bang["tong_da_chi"] == 12_000_000 + 3_000_000 + 7_000_000


def test_n6_chi_vuot_con_lai_cua_hang_muc_thi_bat_co_ngoai_du_toan():
    mk = login("nv_mkt") if False else login("cntt")
    # còn lại quảng cáo = 30tr − 12tr đã chi − 5tr treo = 13tr
    r = client.post("/api/v1/payment-requests", json={"category": "marketing", "marketing_muc": "quang_cao",
                                                     "supplier_name": "Meta", "amount": 20_000_000,
                                                     "description": "Đẩy mạnh cuối kỳ"}, headers=mk)
    assert r.status_code == 201
    d = r.json()["request"] if "request" in r.json() else r.json()
    # 23/9/2026 — Chủ tịch chốt: chi Marketing đi MỘT chữ ký ở mọi mức tiền, kể cả khi vượt dự
    # toán. Cờ `over_budget` VẪN bật (nó là lời báo, và hai màn hình lãnh đạo đọc nó), nhưng nó
    # thôi kéo theo chữ ký thứ hai. Hai khẳng định dưới đây canh đúng ranh giới ấy: còn NÓI, hết
    # CHẶN. Bản trước đòi `two_signatures is True` — đổi ở đây là đổi theo luật, không phải nới
    # phép thử cho hết đỏ.
    assert d["over_budget"] is True, "vượt dự toán vẫn phải ghi cờ — thôi chặn không có nghĩa là thôi nói"
    assert d["two_signatures"] is False, "chi Marketing không còn chữ ký thứ hai (Chủ tịch chốt 23/9/2026)"
    assert "ngoài dự toán" in d["description"]
    # trong hạn mức thì không bật cờ
    r2 = client.post("/api/v1/payment-requests", json={"category": "marketing", "marketing_muc": "noi_dung",
                                                      "supplier_name": "Studio", "amount": 1_000_000,
                                                      "description": "Sửa clip"}, headers=mk).json()
    d2 = r2["request"] if "request" in r2 else r2
    assert d2["over_budget"] is False


def test_n7_chua_gan_hang_muc_cung_la_ngoai_du_toan():
    """Không đối chiếu được với hạn mức nào thì không được coi là trong dự toán."""
    r = client.post("/api/v1/payment-requests", json={"category": "marketing", "supplier_name": "Ai đó",
                                                     "amount": 500_000, "description": "Không ghi hạng mục"},
                    headers=login("cntt")).json()
    d = r["request"] if "request" in r else r
    assert d["over_budget"] is True
    assert d["two_signatures"] is False, "một chữ ký cho mọi hồ sơ Marketing – Chủ tịch chốt 23/9/2026"


def test_n8_ky_quy_cong_du_ba_thang():
    from app.services.marketing import thang_cua_ky, _khoang_ngay, ky_hop_le
    assert ky_hop_le("2026-Q4") and thang_cua_ky("2026-Q4") == ["2026-10", "2026-11", "2026-12"]
    dau, sau = _khoang_ngay("2026-Q4")
    assert dau == datetime(2026, 10, 1) and sau == datetime(2027, 1, 1)
    assert _khoang_ngay("2026-12") == (datetime(2026, 12, 1), datetime(2027, 1, 1))


def test_n9_vai_tro_ngoai_marketing_khong_lap_ngan_sach():
    assert client.post("/api/v1/marketing/budgets", json=BASE, headers=login("hcns")).status_code == 403
