# -*- coding: utf-8 -*-
"""E13 · B03 trực tiếp xếp vốn góp và cổ tức như BCTC đã kiểm toán (Chủ tịch duyệt 19/10/2026).

Một kỳ sạch, đáp án tính tay:
  1. Góp vốn          Nợ 112 / Có 411   1.000.000.000   → dòng 31
  2. Trả lại vốn góp  Nợ 411 / Có 112     100.000.000   → dòng 32
  3. Trả cổ tức thẳng Nợ 421 / Có 112      50.000.000   → dòng 36
Dòng 40 = 1.000.000.000 − 100.000.000 − 50.000.000 = 850.000.000; HĐKD = 0; tiền cuối kỳ khớp.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e13b.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                               # noqa: E402

from app.db.session import Base, SessionLocal, engine        # noqa: E402
from app.models.accounting import Account                    # noqa: E402
from app.services import accounting as ACC                   # noqa: E402
from app.services import reports as RP                       # noqa: E402

Base.metadata.create_all(engine)
KY = "2099-05"
NGAY = date(2099, 5, 10)
TK = (("112", "Tiền gửi ngân hàng", "TS"), ("411", "Vốn góp của chủ sở hữu", "NV"),
      ("421", "Lợi nhuận sau thuế chưa phân phối", "NV"))
BUT_TOAN = [
    ("Góp vốn", [("112", 1_000_000_000, 0), ("411", 0, 1_000_000_000)]),
    ("Trả lại vốn góp", [("411", 100_000_000, 0), ("112", 0, 100_000_000)]),
    ("Trả cổ tức", [("421", 50_000_000, 0), ("112", 0, 50_000_000)]),
]


@pytest.fixture(scope="module")
def cf():
    db = SessionLocal()
    for c, n, k in TK:
        if not db.get(Account, c):
            db.add(Account(code=c, name=n, kind=k, is_detail=True))
    db.commit()
    for i, (dg, dong) in enumerate(BUT_TOAN, 1):
        ACC.post_entry(db, "e13b", "ketoan", NGAY, dg,
                       [{"account": a, "debit": d or None, "credit": c or None} for a, d, c in dong],
                       "thu_cong", f"e13b:{i}", nghiep_vu="but_toan_tay")
    db.commit()
    kq = RP.cash_flow(db, KY)
    db.close()
    return kq


def _r(kq):
    return {ma: so for ma, _t, so in kq["rows"]}


def test_e13b_1_von_gop_va_co_tuc_vao_hoat_dong_tai_chinh(cf):
    r = _r(cf)
    assert r["31"] == 1_000_000_000
    assert r["32"] == -100_000_000
    assert r["36"] == -50_000_000
    assert r["40"] == 850_000_000
    assert r["20"] == 0 and r["06"] == 0 and r["07"] == 0, "không còn rơi vào thu/chi khác của HĐKD"


def test_e13b_2_tien_cuoi_ky_van_khop(cf):
    r = _r(cf)
    assert cf["reconciled"] is True
    assert r["50"] == 850_000_000 and r["70"] == 850_000_000


def test_e13b_3_thu_tu_dong_va_dau_vet_cong_thuc(cf):
    ma = [x[0] for x in cf["rows"]]
    assert ma.index("30") < ma.index("31") < ma.index("32") < ma.index("33") < ma.index("34") \
        < ma.index("36") < ma.index("40")
    assert cf["cong_thuc"]["ngay"] == "2026-10-19" and "kiểm toán" in cf["cong_thuc"]["ghi_chu"]
