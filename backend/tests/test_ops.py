"""Vận hành: báo cáo ngày (điểm robot, TP chấm, xếp loại, cảnh báo thiếu), ca trực page (chế tài), đề nghị chi R3 (cổng 14/15, luồng 4 bước, bút toán, dòng tiền, khớp SePay tiền ra)."""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ops.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
os.environ["SEPAY_WEBHOOK_KEY"] = "k"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ops.db"):
    os.remove("test_ops.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
settings.SEPAY_WEBHOOK_KEY = "k"
from app.services import ops as O

client = TestClient(app)
TOK = {}
TODAY = date.today()
P = f"{TODAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(scope="module", autouse=True)
def _nguong_f1(_startup):
    """ĐỢT F1 — bối cảnh: công ty ĐÃ CHỐT ngưỡng duyệt chi.

    Từ F1, bước duyệt một đề nghị chi KHÔNG đi được khi tham số `nguong_chu_tich_duyet_chi` còn
    rỗng: rỗng nghĩa là CHƯA AI CHỐT mốc phân cấp duyệt, và một công tắc an toàn hỏng phải hỏng
    về phía ĐÓNG. Bộ mặc định cố ý để trống, vì `seed_params` nạp mọi khóa kèm hai chữ ký mang
    tên "seed" — điền sẵn con số vào đó là ký thay Chủ tịch bằng một dòng mã.

    Nên tệp này phải tự dựng bối cảnh "đã ký", y như nó vẫn tự dựng tour mẫu và người dùng mẫu.
    Mốc 100 triệu ở đây là DỮ LIỆU CỦA PHÉP THỬ, không phải mốc đã ký của công ty. Luật mốc có
    bộ phép thử riêng ở `tests/test_f1_nguong_chu_tich.py`; chỗ này chỉ cần nó không chặn.
    """
    from datetime import date as _date
    from app.db.session import SessionLocal as _SL
    from app.models.core import Param as _P
    from app.services import ops as _O
    from app.services import rules as _R
    _db = _SL()
    try:
        _db.add(_P(key=_O.NGUONG_CHU_TICH_KEY, value="100000000",
                   label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                   effective_from=_date(2026, 9, 2), source="bối cảnh phép thử F1",
                   status="active", signed_chutich=True, signed_tgd=True,
                   proposed_by="phep_thu"))
        _db.commit()
    finally:
        _db.close()
    _R.clear_param_cache()
    yield


def tour(code):
    return next(t for t in client.get("/api/v1/tours", headers=login("tp.dieuhanh")).json()["rows"] if t["code"] == code)


LONG = "Nội dung đủ dài trên hai mươi ký tự để được tính điểm."


def test_daily_report_score_review_and_summary():
    r = client.post("/api/v1/daily-reports", json={"report_date": str(TODAY), "part1_done": LONG, "part2_numbers": "", "part3_issues": LONG, "part4_plan": LONG}, headers=login("kd.hoa")).json()
    assert r["report"]["robot_score"] in (5.0, 7.0)          # P1 3 + P3 2 + (đúng giờ 2), Phần 2 trống
    assert "Phần 2" in r["report"]["robot_note"]
    form = client.get("/api/v1/daily-reports/form", headers=login("kd.hoa")).json()
    assert form["department"] == "kd_le" and "Lead nhận trong ngày" in form["forms"]["kd_le"]["fields"] and len(form["forms"]) == 13   # BC-1 (26/10/2026): 7 mẫu cũ + Visa, Hướng dẫn, Đội xe, Ngân hàng, CSKH, IR–Pháp chế
    p2 = {k: "3" for k in form["forms"]["kd_le"]["fields"]}
    pv = client.post("/api/v1/daily-reports/preview", json={"report_date": str(TODAY), "part1_done": LONG, "part2_numbers": p2, "part3_issues": LONG, "part4_plan": LONG}, headers=login("kd.hoa")).json()
    assert pv["subject"].startswith("Báo cáo ngày · Lê Thị Hoa") and "PHẦN 2 — SỐ LIỆU TRONG NGÀY" in pv["body"] and "Lead nhận trong ngày: 3" in pv["body"]
    r2 = client.post("/api/v1/daily-reports", json={"report_date": str(TODAY), "part1_done": LONG, "part2_numbers": p2, "part3_issues": LONG, "part4_plan": LONG}, headers=login("kd.hoa")).json()
    assert r2["report"]["robot_score"] >= 8 and r2["report"]["part2"]["Lead nhận trong ngày"] == "3" and "mail_body" in r2
    # BC-1: «ngày tương lai» tính theo GIỜ VIỆT NAM, không theo đồng hồ máy chạy thử (máy CI chạy UTC).
    from app.services import ops as _O
    assert client.post("/api/v1/daily-reports", json={"report_date": str(_O.gio_vn().date() + timedelta(days=1)), "part1_done": LONG, "part4_plan": LONG}, headers=login("kd.hoa")).status_code == 422
    mine = client.get("/api/v1/daily-reports", headers=login("kd.hoa")).json()
    assert len(mine) == 1
    assert client.post(f"/api/v1/daily-reports/{mine[0]['id']}/review", json={"score": 9, "note": "Tốt"}, headers=login("kd.tuan")).status_code == 403
    assert client.post(f"/api/v1/daily-reports/{mine[0]['id']}/review", json={"score": 9, "note": "Tốt"}, headers=login("gd.kd")).status_code == 200
    assert client.post("/api/v1/daily-reports", json={"report_date": str(TODAY), "part1_done": LONG, "part4_plan": LONG}, headers=login("kd.hoa")).status_code == 422  # đã chấm
    s = client.get("/api/v1/daily-reports/summary", params={"period": P}, headers=login("hcns")).json()
    hoa = next(x for x in s["rows"] if x["code"] == "NS0002")
    assert hoa["submitted"] == 1 and hoa["reviewed"] == 1 and hoa["grade"] in "ABCD"
    n = client.post("/api/v1/daily-reports/check-missing", headers=login("cntt")).json()["new_alerts"]
    assert n >= 1                                              # nhiều người mẫu chưa nộp


def test_page_shift_penalties():
    assert O.shift_penalty(3) == (300_000, False) and O.shift_penalty(5) == (1_000_000, False) and O.shift_penalty(6) == (1_200_000, True)
    emps = {e["code"]: e for e in client.get("/api/v1/employees", headers=login("hcns")).json()}
    client.post("/api/v1/page-shifts", json={"shift_date": str(TODAY), "slot": "toi", "employee_id": emps["NS0002"]["id"]}, headers=login("gd.kd"))
    sh = client.get("/api/v1/page-shifts", headers=login("kd.hoa")).json()[0]
    msg = client.post(f"/api/v1/page-shifts/{sh['id']}/scan", json={"missed": 2, "note": "sót 2 tin lúc 21h"}, headers=login("cntt")).json()["message"]
    assert "200,000" in msg


def test_payment_request_gates_flow_and_journal():
    t = tour("PT-DL-0912")   # dự toán: 14tr + 850k × max(30, 9) = 39,5 triệu
    bad = client.post("/api/v1/payment-requests", json={"category": "chi_tour", "supplier_name": "KS Mũi Né", "amount": 5000000, "description": "Phòng"}, headers=login("dh.lan"))
    assert bad.status_code == 422 and bad.json()["detail"]["gate"] == "CONG_14"
    base = {"category": "chi_tour", "tour_id": t["id"], "supplier_name": "Khách sạn Mũi Né", "supplier_tax_code": "3400123456", "supplier_bank": "123456 – MB", "description": "Tiền phòng 30 khách"}
    r1 = client.post("/api/v1/payment-requests", json={**base, "amount": 20_000_000, "has_document": True, "document_ref": "HĐ 12/KS", "has_invoice": True}, headers=login("dh.lan")).json()["request"]
    assert r1["status"] == "cho_tp" and not r1["two_signatures"]
    r2 = client.post("/api/v1/payment-requests", json={**base, "supplier_name": "Nhà hàng Biển", "amount": 25_000_000, "description": "Ăn uống"}, headers=login("dh.lan")).json()
    assert r2["request"]["over_budget"] and r2["request"]["two_signatures"] and "NGOÀI DỰ TOÁN" in r2["message"]
    # 23/9/2026 — Chủ tịch chốt: chi Marketing đi MỘT chữ ký của P.TGĐ Marketing ở mọi mức tiền, và
    # chính P.TGĐ KHÔNG lập hồ sơ (lập thì không còn ai ký được ngoài chính mình). Bản trước lập hồ
    # sơ bằng tài khoản `ptgd.mkt` và đòi `two_signatures` — cả hai đều theo luật cũ.
    # Tuyến Marketing có bộ phép thử riêng ở `tests/test_mkt_mot_chu_ky.py`; ở đây chỉ canh hai điều
    # mà tệp này vốn canh: cửa lập chặn đúng người, và hồ sơ Marketing không đi lối hai chữ ký.
    assert client.post("/api/v1/payment-requests", json={"category": "marketing", "supplier_name": "Meta", "supplier_tax_code": "x", "amount": 6_000_000, "description": "Quảng cáo", "has_document": True}, headers=login("ptgd.mkt")).status_code == 422
    mk = client.post("/api/v1/payment-requests", json={"category": "marketing", "marketing_muc": "quang_cao", "supplier_name": "Meta", "supplier_tax_code": "x", "amount": 6_000_000, "description": "Quảng cáo", "has_document": True}, headers=login("cntt")).json()
    # ĐỢT F1b: hồ sơ Marketing thôi nhảy cóc qua bước bộ phận. Nó bắt đầu ở `cho_tp` như mọi
    # loại chi khác, và `cho_tp` chính là bước một — P.TGĐ Marketing duyệt nội dung.
    assert mk["request"]["two_signatures"] is False and mk["request"]["status"] == "cho_tp"
    # luồng r1: TP ĐH → KT → TGĐ → chi
    st = lambda rid, a, reason="", who="tp.dieuhanh": client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": a, "reason": reason}, headers=login(who))
    assert st(r1["id"], "check", who="ketoan").status_code == 422
    assert st(r1["id"], "confirm").json()["request"]["status"] == "cho_kt"
    assert st(r1["id"], "check", who="ketoan").json()["request"]["status"] == "cho_duyet"
    # LUẬT ĐỔI Ở ĐỢT F1. Câu cũ ở đây đòi Chủ tịch bị TỪ CHỐI, kèm chú thích "không cần 2 chữ ký
    # → Chủ tịch không ký" — và đó chính là chỗ hỏng F1 sửa: mã cũ từ chối Chủ tịch ở MỌI khoản
    # không bật cờ ngoài dự toán, kể cả khoản 300 triệu mà theo luật ông phải duyệt. Nay cấp duyệt
    # do MỐC TIỀN quyết, và Chủ tịch toàn quyền ký được cả hai mức (luật 06/9/2026).
    # Điều tệp này vốn canh — KHÔNG phải ai cũng ký được — vẫn được canh, bằng một vai khác.
    assert st(r1["id"], "approve", who="ketoan").status_code == 422
    res = st(r1["id"], "approve", who="tgd").json()
    assert res["request"]["status"] == "cho_chi" and len(res["request"]["entry_ids"]) == 1
    # SePay tiền ra khớp mã lệnh chi + số tiền → tự ghi đã chi
    hook = client.post("/api/v1/sepay/webhook", json={"id": 7001, "transferType": "out", "transferAmount": 20_000_000, "content": f"TT {r1['code']} khach san", "transactionDate": f"{TODAY} 10:00:00"}, headers={"Authorization": "Apikey k"}).json()
    assert hook["match_status"] == "da_khop"
    pr = next(x for x in client.get("/api/v1/payment-requests", headers=login("ketoan")).json() if x["id"] == r1["id"])
    assert pr["status"] == "da_chi" and len(pr["entry_ids"]) == 2
    js = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == f"dc:{r1['code']}"]
    pairs = {(l["account"], l["debit"], l["credit"]) for e in js for l in e["lines"]}
    # Đợt TKC-3: đề nghị chi `chi_tour` ghi vào `1541` (tài khoản chi tiết) thay cho `154` (cha).
    assert {("1541", 20_000_000, 0), ("331", 0, 20_000_000), ("331", 20_000_000, 0), ("1121", 0, 20_000_000)} <= pairs
    # r2 ngoài dự toán: Kế toán chặn vì thiếu chứng từ; 2 chữ ký
    st(r2["request"]["id"], "confirm")
    assert "chứng từ" in st(r2["request"]["id"], "check", who="ketoan").json()["detail"]
    assert st(r2["request"]["id"], "reject", "", who="tgd").status_code == 422
    assert st(r2["request"]["id"], "reject", "Vượt dự toán, chưa có báo giá", who="tgd").json()["request"]["status"] == "tu_choi"
    cf = client.get(f"/api/v1/tours/{t['id']}/cashflow", headers=login("dh.lan")).json()
    assert cf["paid"] == 20_000_000 and cf["pending"] == 0 and cf["budget"] == 39_500_000 and cf["red"] is True  # chưa thu tiền → chi vượt thu


def test_settlement_uses_335_for_uninvoiced_difference():
    t = tour("DN-HCM-0820")
    r = client.post("/api/v1/payment-requests", json={"category": "chi_tour", "tour_id": t["id"], "supplier_name": "KS Đà Nẵng", "supplier_tax_code": "0400", "amount": 100_000_000, "description": "Phòng đoàn", "has_document": True, "has_invoice": True}, headers=login("dh.lan")).json()["request"]
    # 100 triệu ĐÚNG BẰNG mốc của bối cảnh phép thử, và "từ 100 triệu" tính CẢ mốc → CHỦ TỊCH
    # duyệt, không phải TGĐ (Đợt F1). Giữ nguyên "tgd" ở đây thì đỏ, và đỏ ấy là luật mới đang
    # làm việc chứ không phải một hỏng hóc.
    for a, w in (("confirm", "tp.dieuhanh"), ("check", "ketoan"), ("approve", "chutich")):
        assert client.post(f"/api/v1/payment-requests/{r['id']}/step", json={"action": a}, headers=login(w)).status_code == 200
    client.post(f"/api/v1/tours/{t['id']}/close", json={"actual_revenue": 189000000, "actual_cost": 158000000}, headers=login("dh.lan"))
    assert client.post(f"/api/v1/tours/{t['id']}/kt-confirm", headers=login("ketoan")).status_code == 200
    es = [e for e in client.get("/api/v1/journal", headers=login("ketoan")).json() if e["source_ref"] == "tour:DN-HCM-0820"]
    pairs = {(l["account"], l["debit"], l["credit"]) for e in es for l in e["lines"]}
    # Đợt TKC-3: giá vốn vào `6321` (tour nội địa) thay cho `632` (cha). `335` chưa nắn trong đợt
    # này — con của nó (`3351`) chưa có trong danh mục mẫu đi kèm mã; để lại Đợt TKC-4.
    assert ("335", 0, 58_000_000) in pairs and ("6321", 158_000_000, 0) in pairs
    assert client.get("/api/v1/audit", headers=login("bks")).json()["chain_ok"] is True
