# -*- coding: utf-8 -*-
"""CHI MARKETING ĐI MỘT CHỮ KÝ — Chủ tịch chốt 23/9/2026, xác nhận lại 24/9/2026.

──────────────────────────────────────────────────────────────────────────────────────────────
LUẬT
──────────────────────────────────────────────────────────────────────────────────────────────

MỌI đề xuất chi Marketing do **P.TGĐ Marketing** duyệt là xong. Không mốc tiền, không nhánh.
Dữ liệu vẫn đẩy lên TGĐ và Chủ tịch — nhưng để XEM, không phải để bấm.

Đây là một bước NỚI, và tệp này ghi lại đúng nó nới những gì, để người đọc sau không tưởng là
chỗ sót. Trước 23/9 Marketing có HAI phanh, quyết định này gỡ cả hai:

  · `han_muc_mkt` = 5.000.000đ — từ mức ấy trở lên phải thêm chữ ký Chủ tịch
  · vượt phần còn lại của hạng mục ngân sách — cũng bật hai chữ ký

Chủ tịch đã được nêu rõ cả hai cùng hệ quả (một hồ sơ 500 triệu, hoặc một hồ sơ vượt dự toán,
nay cũng chỉ cần một chữ ký) và vẫn chốt bỏ.

BỐN THỨ KHÔNG BỊ GỠ — và mỗi thứ có một phép thử ở dưới:

  M1  Kế toán vẫn kiểm chứng từ và mã số thuế trước khi chi
  M2  cờ `over_budget` vẫn bật và vẫn ghi vào mô tả — thôi CHẶN, không thôi NÓI
  M3  P.TGĐ Marketing KHÔNG lập hồ sơ (nếu ông ấy lập thì không còn ai ký được ngoài chính mình)
  M4  người lập không tự duyệt — kể cả Chủ tịch toàn quyền

Và một thứ mới, vì luật mới đẻ ra một chỗ hỏng mới:

  M5  vai `ptgd_mkt` RỖNG thì mọi hồ sơ nằm chờ vĩnh viễn mà không ai thấy đỏ

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO M5 LÀ PHÉP THỬ QUAN TRỌNG NHẤT Ở ĐÂY
──────────────────────────────────────────────────────────────────────────────────────────────

Luật cũ có ba vai ký được (P.TGĐ, TGĐ, Chủ tịch), nên một vai trống thì hồ sơ vẫn đi tiếp. Luật
mới dồn tất cả vào MỘT vai. Vai ấy trống — người nghỉ, tài khoản bị khoá, đổi vai trò nhầm —
thì mọi hồ sơ chi Marketing đứng im, và trên màn hình nó trông y hệt "đang chờ duyệt". Không ai
báo lỗi, không ai thấy đỏ, tiền chỉ đơn giản là không được duyệt.

Đó là kiểu hỏng tệ nhất: im lặng. Nên luật mới phải đi kèm một cái miệng.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_mkt1ck.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_mkt1ck.db"):
    os.remove("test_mkt1ck.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import User  # noqa: E402
from app.services import ops as O  # noqa: E402

client = TestClient(app)
TOK = {}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    """Mở client theo kiểu ngữ cảnh để vòng đời ứng dụng chạy — đó là chỗ tạo bảng và nạp dữ liệu
    mẫu. Không có nó thì mọi truy vấn đều 'no such table: users', và đọc lỗi ấy rất dễ tưởng là
    mình viết sai truy vấn."""
    with TestClient(app) as c:
        global client
        client = c
        yield


def login(u: str) -> dict:
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


def _lap(nguoi: str = "cntt", tien: float = 2_000_000, muc: str = "quang_cao", **kw):
    # `supplier_tax_code` là bắt buộc ở bước Kế toán kiểm tra (không có MST thì không trừ được thuế).
    # Điền sẵn ở đây để các phép thử dưới đo đúng thứ chúng định đo là TUYẾN DUYỆT; riêng phép thử
    # M1 cố ý bỏ `has_document` để chứng minh bước Kế toán vẫn còn nguyên.
    body = {"category": "marketing", "marketing_muc": muc, "supplier_name": "Meta",
            "supplier_tax_code": "0301234567", "amount": tien,
            "description": "Quảng cáo tháng " + f"{date.today():%m}",
            "has_document": True, "document_ref": "BG-01", **kw}
    return client.post("/api/v1/payment-requests", json=body, headers=login(nguoi))


def _ai_giu_vai():
    db = SessionLocal()
    try:
        return O.ai_duyet_duoc_mkt(db)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Luật chính
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_mk1_tren_han_muc_cu_van_chi_mot_chu_ky():
    """20 triệu — gấp bốn lần `han_muc_mkt` cũ. Trước 23/9 là hai chữ ký; nay vẫn một."""
    r = _lap(tien=20_000_000)
    assert r.status_code == 201, r.text
    d = r.json()["request"]
    assert d["two_signatures"] is False, (
        "hồ sơ 20 triệu vẫn bật hai chữ ký — phanh `han_muc_mkt` chưa được gỡ khỏi Marketing")


def test_mk2_bo_luon_buoc_bo_phan_xac_nhan():
    """Người xác nhận bộ phận của Marketing CHÍNH LÀ P.TGĐ MKT, mà nay ông ấy duyệt ở cuối.

    Giữ cả hai bước là bắt cùng một người bấm hai lần cho cùng một hồ sơ.
    """
    d = _lap(tien=3_000_000).json()["request"]
    assert d["status"] == "cho_kt", f"hồ sơ Marketing phải vào thẳng bước Kế toán, đang ở {d['status']}"


def test_mk3_ptgd_mkt_khong_lap_ho_so():
    """M3. Nếu chính người duyệt lập hồ sơ thì hồ sơ ấy không còn ai ký được ngoài chính mình."""
    r = _lap(nguoi="ptgd.mkt")
    assert r.status_code == 422, "P.TGĐ Marketing vẫn lập được hồ sơ — lỗ tự duyệt chưa bịt"
    assert "không lập hồ sơ" in r.text


def test_mk4_ke_toan_van_kiem_chung_tu_truoc_khi_duyet():
    """M1. Một chữ ký KHÔNG có nghĩa là bỏ bước kiểm chứng từ — đó là kiểm soát tài chính."""
    d = _lap(tien=1_000_000, has_document=False).json()["request"]
    r = client.post(f"/api/v1/payment-requests/{d['id']}/step",
                    json={"action": "check"}, headers=login("ketoan"))
    assert r.status_code == 422 and "chứng từ" in r.text, "thiếu chứng từ mà Kế toán vẫn chuyển duyệt được"


def test_mk5_duyet_boi_ptgd_mkt_la_xong():
    """Đường đi đầy đủ: nhân viên lập → Kế toán kiểm → P.TGĐ MKT duyệt → sang lệnh chi."""
    d = _lap(tien=30_000_000, muc="noi_dung").json()["request"]
    rid = d["id"]
    assert client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": "check"},
                       headers=login("ketoan")).status_code == 200

    # TGĐ KHÔNG còn là người duyệt chi Marketing
    r_tgd = client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": "approve"},
                        headers=login("tgd"))
    assert r_tgd.status_code == 422, "TGĐ vẫn duyệt được chi Marketing — luật một chữ ký chưa vào"

    r = client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": "approve"},
                    headers=login("ptgd.mkt"))
    assert r.status_code == 200, r.text
    sau = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    ho_so = [x for x in sau if x["id"] == rid][0]
    assert ho_so["status"] == "cho_chi", "duyệt xong phải sang lệnh chi ngay, không chờ chữ ký nào nữa"
    assert ho_so["approved_by"] == "ptgd.mkt"


def test_mk6_nguoi_lap_khong_tu_duyet():
    """M4. Cửa lập đã chặn P.TGĐ MKT, nhưng Chủ tịch toàn quyền thì lập được — nên ranh giới này
    phải đứng ở bước DUYỆT mới kín."""
    d = _lap(nguoi="chutich", tien=4_000_000).json()["request"]
    rid = d["id"]
    client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": "check"}, headers=login("ketoan"))
    r = client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": "approve"},
                    headers=login("chutich"))
    assert r.status_code == 422 and "tự duyệt" in r.text, (
        "người lập tự duyệt được hồ sơ của chính mình")


def test_mk7_vuot_du_toan_van_noi_du_khong_con_chan():
    """M2. Cờ `over_budget` thôi CHẶN, không thôi NÓI."""
    d = _lap(tien=900_000_000, muc="quang_cao").json()["request"]
    assert d["over_budget"] is True, "khoản 900 triệu chắc chắn vượt dự toán mà không ghi cờ"
    assert d["two_signatures"] is False
    assert "ngoài dự toán" in d["description"], "phải ghi vào mô tả để người duyệt đọc thấy"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# M5 — chỗ hỏng mà chính luật mới đẻ ra
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_mk8_phai_co_nguoi_giu_vai_ptgd_mkt():
    """HÀNG RÀO. Vai này rỗng thì mọi hồ sơ chi Marketing nằm chờ vĩnh viễn mà không ai thấy đỏ.

    Đỏ ở đây KHÔNG phải lỗi mã. Nó nghĩa là: chưa gắn ai vào vai P.TGĐ Marketing, hoặc người đang
    giữ vai đã bị khoá tài khoản. Cách xử là vào Quản trị hệ thống → Phân quyền gắn người, KHÔNG
    phải sửa phép thử này.
    """
    ai = _ai_giu_vai()
    assert ai, (
        "KHÔNG TÀI KHOẢN ĐANG HOẠT ĐỘNG NÀO GIỮ VAI P.TGĐ MARKETING (`ptgd_mkt`).\n"
        "Từ 23/9/2026 mọi hồ sơ chi Marketing dừng ở MỘT chữ ký của vai này. Vai rỗng nghĩa là mọi "
        "hồ sơ đứng im — và trên màn hình nó trông y hệt 'đang chờ duyệt'.\n"
        "Cách xử: Quản trị hệ thống → Phân quyền → gắn một người vào vai `ptgd_mkt`.")


def test_mk9_vai_rong_thi_cua_lap_phai_noi_ra():
    """Hàng rào ở trên canh lúc dựng bản. Còn lúc CHẠY THẬT thì người lập phải được báo ngay.

    Khoá tạm tài khoản đang giữ vai, lập một hồ sơ, và đòi lời báo nói thẳng ra. Trả lại nguyên
    trạng ở cuối — phép thử không được để lại dấu vết trong dữ liệu.
    """
    db = SessionLocal()
    try:
        nguoi = db.execute(select(User).where(User.role == O.VAI_DUYET_MKT,
                                              User.active.is_(True))).scalars().all()
        for n in nguoi:
            n.active = False
        db.commit()
    finally:
        db.close()
    try:
        assert _ai_giu_vai() == [], "khoá hết rồi mà vẫn đếm ra người giữ vai"
        kq = _lap(tien=1_500_000, muc="noi_dung").json()
        assert "CHƯA AI GIỮ VAI" in kq["message"], (
            "vai duyệt đang rỗng mà cửa lập không nói gì — hồ sơ sẽ nằm chờ trong im lặng.\n"
            f"Lời báo đang là: {kq['message']}")
    finally:
        db = SessionLocal()
        try:
            for n in db.execute(select(User).where(User.role == O.VAI_DUYET_MKT)).scalars():
                n.active = True
            db.commit()
        finally:
            db.close()
    assert _ai_giu_vai(), "chưa trả lại nguyên trạng sau phép thử"
