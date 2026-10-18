# -*- coding: utf-8 -*-
"""CF-1 · Báo cáo lưu chuyển tiền tệ tháng KHÔNG được nạp cả sổ cái vào bộ nhớ (19/10/2026).

Đo trên hệ thật: mỗi lần gọi /reports/cash-flow máy chủ sập 1–2 phút — `_lines` kéo toàn bộ
JournalLine + JournalEntry (mọi kỳ) thành đối tượng Python rồi mới lọc kỳ, vượt 512 MB. Phép thử
canh hai điều: câu SQL mang điều kiện kỳ, và chỉ dòng của kỳ ấy được trả về.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_cf1.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                               # noqa: E402
from sqlalchemy import event                                 # noqa: E402

from app.db.session import Base, SessionLocal, engine        # noqa: E402
from app.models.accounting import Account                    # noqa: E402
from app.services import accounting as ACC                   # noqa: E402
from app.services import reports as RP                       # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    for c, n, k in (("112", "Tiền gửi", "TS"), ("411", "Vốn góp", "NV")):
        if not s.get(Account, c):
            s.add(Account(code=c, name=n, kind=k, is_detail=True))
    s.commit()
    for i, ngay in enumerate((date(2098, 1, 5), date(2098, 2, 5), date(2098, 3, 5)), 1):
        ACC.post_entry(s, "cf1", "ketoan", ngay, f"Góp vốn {i}",
                       [{"account": "112", "debit": 1000.0 * i}, {"account": "411", "credit": 1000.0 * i}],
                       "thu_cong", f"cf1:{i}", nghiep_vu="but_toan_tay")
    s.commit()
    yield s
    s.close()


def test_cf1_1_chi_tra_dong_cua_ky(db):
    rows = RP._lines(db, period="2098-02")
    assert rows and {e.period for _l, e in rows} == {"2098-02"}
    assert {e.period for _l, e in RP._lines(db, upto_period="2098-02")} == {"2098-01", "2098-02"}


def test_cf1_2_dieu_kien_ky_nam_trong_cau_sql(db):
    cau = []

    def nghe(conn, cursor, statement, params, context, executemany):
        cau.append(statement.lower())
    event.listen(engine, "before_cursor_execute", nghe)
    try:
        RP._lines(db, period="2098-02")
    finally:
        event.remove(engine, "before_cursor_execute", nghe)
    sel = [c for c in cau if "journal" in c and "select" in c]
    assert sel and all("period" in c.split("where", 1)[-1] for c in sel), (
        "câu SQL không lọc kỳ — báo cáo lại nạp cả sổ cái vào bộ nhớ")


def test_cf1_3_bao_cao_van_dung(db):
    r = {ma: so for ma, _t, so in RP.cash_flow(db, "2098-02")["rows"]}
    assert r["31"] == 2000.0 and r["50"] == 2000.0
