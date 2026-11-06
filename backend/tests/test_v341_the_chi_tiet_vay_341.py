# -*- coding: utf-8 -*-
"""Đợt V341-1 06/11/2026 — THẺ ĐỌC «CHI TIẾT VAY VÀ NỢ THUÊ TÀI CHÍNH THEO NGÂN HÀNG, TK 341».

Cửa `GET /reports/vay-341` đã có trên main từ trước, `test_misa.py` gọi nó nên nó chạy đúng.
Thứ thiếu là CHỖ ĐỌC: quét `web/**/*.tsx` ngày 06/11/2026 thì chuỗi `vay-341` xuất hiện 0 lần.
Đợt này KHÔNG ĐỔI MỘT CON SỐ NÀO và KHÔNG ĐỤNG BẢNG QUYỀN MỘT DÒNG NÀO.

BỐN LUẬT, hai luật đo máy chủ bằng cửa thật và hai luật đo màn hình:

  1. Cửa trả đủ mọi ô thẻ đọc, VÀ con số của nó khớp sổ — luật này TỰ DỰNG CẢNH (ghi bút toán
     vay thật) chứ không trông chờ bộ dữ liệu mẫu tình cờ có sẵn khoản vay nào. Bài học Đợt
     TKC-1 cùng ngày: một luật không bao giờ chạy thì không phải luật.
  2. Cửa giữ nguyên bộ vai `READ` của kế toán — KHÔNG mở thêm cho ai, và bảng quyền của màn
     `/accounting` không cần thêm dòng nào vì nhóm `/api/v1/reports` đã khai sẵn ở đó.
  3. Thân thẻ KHÔNG tự cộng lại dòng Cộng, và giữ bốn cột đứng riêng.
  4. Đối chiếu dùng ĐÚNG chỉ tiêu 321 + 339, không phải 320/338.

Hai luật về màn hình CẮT RIÊNG THÂN THẺ để đo, không đo cả tệp: `accounting/page.tsx` có nhiều
nút ghi thật ở chỗ khác (ghi sổ, khóa kỳ, ký bản đã lập), đo cả tệp là đo nhầm người — đúng bài
học Đợt R5b-2.
"""
import json
import os
import re
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_v341.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_v341.db"):
    os.remove("test_v341.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "accounting", "page.tsx")
MAU = os.path.join(GOC, "backend", "app", "data", "bctc_tt99_mau.json")

TU, DEN = str(date(date.today().year, 1, 1)), str(date.today())


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        _dung_canh()
        yield


def _dung_canh():
    """Ghi hai bút toán vay THẬT qua cửa, rồi bỏ mã đối tượng của khoản thứ hai NGAY TRONG CSDL.

    ĐO ĐƯỢC KHI VIẾT LUẬT NÀY, và nó đổi cách dựng cảnh: cửa ghi sổ TỪ CHỐI dòng vay không mang
    mã đối tượng — `services/accounting.py::account_rule_check` trả 422 «Tài khoản 34111 phải ghi
    mã đối tượng». Nên rổ «Đối tượng nội bộ chưa phân loại ngân hàng» của
    `bctc.py::loan_bank_detail_341` KHÔNG thể sinh ra từ cửa nhập tay; nó chỉ đến từ dữ liệu nạp
    vào bằng đường khác (nạp MISA, số dư đầu kỳ). Nhánh ấy vẫn có thật trên dữ liệu thật, nên
    luật vẫn phải đo nó — chỉ là phải dựng cảnh đúng cách nó sinh ra, tức ghi thẳng vào CSDL,
    chứ không giả vờ rằng cửa cho phép.
    """
    h = login("ketoan")
    ma_bt = []
    for mo_ta, tien in (("V341-1 dựng cảnh — vay có mã ngân hàng", 5_000_000),
                        ("V341-1 dựng cảnh — vay rồi gỡ mã đối tượng", 2_000_000)):
        r = client.post("/api/v1/journal", json={
            "entry_date": DEN, "description": mo_ta,
            "lines": [{"account": "112", "debit": tien},
                      {"account": "34111", "credit": tien, "partner_code": "NH-V341"}],
            "post": True}, headers=h)
        assert r.status_code in (200, 201), (
            "không dựng được cảnh vay (" + str(r.status_code) + "): " + r.text[:300])
        ma_bt.append(mo_ta)

    from sqlalchemy import select as _sel
    from app.db.session import SessionLocal
    from app.models.accounting import JournalEntry, JournalLine
    with SessionLocal() as db:
        e = db.execute(_sel(JournalEntry).where(
            JournalEntry.description == ma_bt[1])).scalars().first()
        assert e is not None, "không tìm lại được bút toán vừa ghi để dựng cảnh «chưa phân loại»"
        n = 0
        for l in db.execute(_sel(JournalLine).where(JournalLine.entry_id == e.id)).scalars():
            if l.account_code == "34111":
                l.partner_code, l.partner, n = "", "", n + 1
        assert n == 1, "cảnh «chưa phân loại» cần đúng một dòng 34111, thấy " + str(n)
        db.commit()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_v341_1_cua_tra_du_moi_o_the_doc_va_cong_dung_bang_tong_cac_dong():
    """Thẻ đọc ô nào thì cửa phải có ô ấy — và dòng Cộng phải bằng tổng các dòng.

    Ô nào thiếu thì thẻ in «undefined», và «undefined» trong một bảng tiền là tệ hơn một bảng
    trống: người đọc tưởng số bằng không.
    """
    r = client.get("/api/v1/reports/vay-341", headers=login("ketoan"),
                   params={"since": TU, "upto": DEN})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for o in ("since", "upto", "rows", "by_kind", "total"):
        assert o in d, "cửa thiếu ô `" + o + "` mà thẻ đọc"
    for o in ("open", "debit_in_period", "credit_in_period", "close"):
        assert o in d["total"], "ô `total." + o + "` thiếu — thẻ sẽ in undefined ở dòng Cộng"

    assert d["rows"], "cảnh đã dựng hai khoản vay mà cửa trả 0 dòng — luật này không đo được gì"
    for r0 in d["rows"]:
        for o in ("bank", "partner_code", "account", "open", "debit_in_period",
                  "credit_in_period", "close"):
            assert o in r0, "dòng thiếu ô `" + o + "`"
    assert all(a in d["by_kind"] for a in {x["account"] for x in d["rows"]}), (
        "`by_kind` thiếu tiểu khoản mà `rows` có — thẻ nhóm theo `by_kind` nên dòng ấy sẽ biến mất")

    # Dòng Cộng của MÁY CHỦ phải bằng tổng các dòng. Thẻ lấy thẳng `total`, nên nếu `total` sai thì
    # thẻ hiển thị sai mà không có cách nào biết — chỗ canh phải là ở đây.
    for o in ("open", "debit_in_period", "credit_in_period", "close"):
        assert abs(d["total"][o] - sum(x[o] for x in d["rows"])) < 1, (
            "`total." + o + "` không bằng tổng các dòng")

    # Cảnh đã dựng: 7 triệu vay thêm, trong đó 2 triệu không mang mã đối tượng.
    assert abs(d["total"]["credit_in_period"] - 7_000_000) < 1, (
        "vay thêm trong kỳ phải là 7.000.000 (cảnh dựng), nhận " + str(d["total"]["credit_in_period"]))
    assert any(not x["partner_code"] for x in d["rows"]), (
        "dòng vay KHÔNG mang mã đối tượng phải hiện ra thành một dòng riêng — gộp nó vào một ngân "
        "hàng nào đó là giấu mất chỗ dữ liệu chưa sạch")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_v341_2_cua_giu_nguyen_bo_vai_READ_va_man_accounting_khong_can_them_dong_quyen():
    """Đợt này KHÔNG ký nới quyền. Hai chiều, và cần cả hai.

    Chiều xuôi: nhóm `/api/v1/reports` đã nằm trong `MAN_HINH_API["/accounting"]`, nên đặt thẻ ở
    đó không phải thêm dòng nào. Chiều ngược: một vai ngoài `READ` vẫn phải nhận 403 — nếu không
    thì «không đụng bảng quyền» chỉ đúng trên giấy, còn cửa thì đã mở toang.
    """
    from app.services.access import MAN_HINH_API
    assert "/api/v1/reports" in MAN_HINH_API["/accounting"], (
        "màn `/accounting` không khai nhóm `/api/v1/reports` — đặt thẻ ở đó sẽ buộc phải thêm một "
        "dòng vào bảng quyền, và dòng ấy cộng phạm vi cho mọi vai đang có màn này")

    r = client.get("/api/v1/reports/vay-341", headers=login("kd.hoa"),
                   params={"since": TU, "upto": DEN})
    assert r.status_code == 403, (
        "một vai Kinh doanh phải nhận 403 ở cửa vay — nhận " + str(r.status_code) +
        ". Chi tiết vay theo ngân hàng là việc của Kế toán.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_v341_3_the_KHONG_tu_cong_lai_va_giu_BON_COT_dung_rieng():
    """Hai điều dễ mất nhất khi ai đó sửa thẻ về sau.

    Cộng lại ở màn hình là cộng cái mình đang thấy rồi gọi nó là tổng. Gộp bốn cột thành một số
    «biến động» là xoá mất câu hỏi người đọc cầm bảng này để hỏi.
    """
    s = open(MAN, encoding="utf-8").read()
    i = s.find("function Vay341(")
    assert i > 0, "không thấy thân thẻ `Vay341` trên màn Kế toán"
    j = s.find("\nfunction ", i + 1)
    than = s[i:j if j > i else len(s)]

    assert ".reduce(" not in than, (
        "thân thẻ tự cộng lại bằng `.reduce(` — dòng Cộng phải lấy thẳng từ `total` của máy chủ")
    assert "d.total.close" in than and "d.total.open" in than, (
        "dòng Cộng không đọc `total` của máy chủ")
    for o in ("debit_in_period", "credit_in_period"):
        assert "r." + o in than, (
            "thiếu cột `" + o + "` — trả nợ và vay thêm phải đứng riêng, không gộp thành một số")
    assert "vay-341.xlsx" in than, "thiếu nút xuất Excel, mà cửa `.xlsx` đã có sẵn trên main"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_v341_4_doi_chieu_dung_chi_tieu_321_va_339_va_the_duoc_GOI_dung_mot_lan():
    """Chỉ tiêu vay là 321 và 339. 320 và 338 là «phải trả khác» — hai thứ khác hẳn.

    Luật này đọc thẳng `data/bctc_tt99_mau.json` thay vì tin trí nhớ, vì chính chỗ này có một
    hằng số sai đang nằm trên main: `bctc.py::LOAN_KIND_BS` gán 34111 → "320". Nó vô hại hôm nay
    vì không chỗ nào gọi, nhưng nó là đúng loại bẫy mà một người sửa thẻ về sau sẽ chép theo.
    """
    mau = {m["code"]: m["name"] for m in json.load(open(MAU, encoding="utf-8"))["thtc"]}
    assert "Vay" in mau.get("321", ""), "chỉ tiêu 321 trong mẫu TT99 không còn là dòng vay — DỪNG LẠI"
    assert "Vay" in mau.get("339", ""), "chỉ tiêu 339 trong mẫu TT99 không còn là dòng vay — DỪNG LẠI"
    assert "Vay" not in mau.get("320", ""), "chỉ tiêu 320 không phải dòng vay"
    assert "Vay" not in mau.get("338", ""), "chỉ tiêu 338 không phải dòng vay"

    s = open(MAN, encoding="utf-8").read()
    i = s.find("function Vay341(")
    j = s.find("\nfunction ", i + 1)
    than = s[i:j if j > i else len(s)]
    assert 'ct("321")' in than and 'ct("339")' in than, (
        "thẻ không đối chiếu đúng hai chỉ tiêu vay 321 và 339")
    assert 'ct("320")' not in than and 'ct("338")' not in than, (
        "thẻ đối chiếu nhầm sang 320/338 — đó là «phải trả khác», không phải vay")

    # Thẻ chỉ gọi cửa trong nhóm `/reports` — gọi ra ngoài nhóm là mở một nhóm API mới cho màn này.
    for p in re.findall(r'api\(`([^`]+)`', than):
        assert p.startswith("/reports/"), (
            "thẻ gọi `" + p + "` nằm ngoài nhóm `/api/v1/reports` — màn `/accounting` sẽ phải khai "
            "thêm một nhóm vào bảng quyền, đúng thứ đợt này cố ý không làm")

    assert s.count("<Vay341 ") == 1, (
        "thẻ phải được gọi ĐÚNG MỘT LẦN trên màn, đếm được " + str(s.count("<Vay341 ")))
    # Gọi TRONG khối `{rep && …}`: thẻ phải tự ẩn với vai không đọc được BCTC, chứ không hiện ra
    # rồi nhận 403. `tp_dh` vào được màn này nhưng không nằm trong `READ` của accounting.
    k = s.find("<Vay341 ")
    assert s.rfind("{rep && <>", 0, k) > s.rfind("</>}", 0, k), (
        "thẻ nằm NGOÀI khối `{rep && …}` — vai không đọc được BCTC sẽ thấy một cái thẻ chỉ để "
        "nhận 403")
