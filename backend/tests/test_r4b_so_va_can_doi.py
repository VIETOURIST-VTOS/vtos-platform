# -*- coding: utf-8 -*-
"""Đợt R4b-1 (21/10/2026) — PHẦN ĐỌC: Dư Nợ/Dư Có, số dư hai bên, luỹ kế, tổng hợp chứng từ gốc.

VÌ SAO CÓ TỆP NÀY

Ba thứ đợt này thêm đều là PHÉP TÍNH, không phải cách bày:

 1. **Dư Nợ / Dư Có tách đôi.** Trước đây Sổ chi tiết in MỘT cột số dư mang dấu. Mẫu S38-DN in
    hai cột. Bên không có số thì BỎ TRỐNG — không ghi 0. Số 0 đọc là "đã tính và bằng không",
    bỏ trống đọc là "dư không nằm ở bên này". Hai câu khác nhau.

 2. **Số dư hai bên (không bù trừ).** 131 có khách nợ ta và có khách nộp thừa. Bù trừ ra MỘT số;
    không bù trừ ra HAI số. Con số "khách nộp thừa" KHÔNG đọc ra được từ bảng đã bù trừ — nó đã
    biến mất trong phép trừ, mà nó chính là một khoản PHẢI TRẢ.

 3. **Tổng hợp chứng từ gốc cùng loại.** VTOS mới khai BẢY mã loại chứng từ, MISA có 36, nên chắc
    chắn còn bút toán không rơi vào mã nào. Bỏ chúng ra ngoài thì tổng bảng không bằng sổ.

ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không khẳng định con số nào là ĐÚNG với sổ thật của công ty. Nó dựng
sổ thử của chính nó rồi hỏi phép tính có nhất quán không.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r4b.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                                    # noqa: E402
from sqlalchemy import create_engine                             # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import JournalEntry, JournalLine      # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import books as BK                             # noqa: E402
from app.services import chung_tu_loai as CTL                    # noqa: E402

TU, DEN = date(2026, 1, 1), date(2026, 6, 30)
_n = [0]


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ — cửa hẹp của CI chạy nhiều tệp trong MỘT tiến trình."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    return db


def _ct(db, dong, ngay=date(2026, 3, 15), loai="", status="da_ghi_so"):
    """Một chứng từ: mỗi dòng là (tài khoản, nợ, có, mã đối tượng)."""
    _n[0] += 1
    e = JournalEntry(code=f"R4B-{_n[0]}", entry_date=ngay, ngay_chung_tu=ngay,
                     period=f"{ngay:%Y-%m}", description="Sổ thử Đợt R4b",
                     status=status, source_type="thu_cong", source_ref="", loai_chung_tu=loai)
    db.add(e)
    db.flush()
    for tk, no, co, dt in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co, partner_code=dt))
    db.commit()
    return e


@pytest.fixture()
def db():
    d = _rieng()
    yield d
    d.close()


# ══════════════ 1 · SỔ CHI TIẾT — DƯ NỢ / DƯ CÓ ══════════════════════════════════════════════

def test_r4b_1_du_co_thi_cot_du_no_BO_TRONG_chu_khong_phai_so_0(db):
    """LUẬT CHÍNH của mục 1. Số 0 và ô trống là hai câu khác nhau."""
    _ct(db, [("331", None, 5_000_000, "NCC1"), ("1541", 5_000_000, None, "")])
    rep = BK.account_book(db, "331", TU, DEN, detail=True)
    d = rep["rows"][-1]
    assert d["balance_credit"] == 5_000_000, d
    assert d["balance_debit"] is None, (
        "331 đang dư Có, nên cột Dư Nợ phải BỎ TRỐNG. Ghi 0 vào đó là nói 'đã tính và bằng "
        "không', khác hẳn 'dư không nằm ở bên này'.")


def test_r4b_2_du_no_thi_nguoc_lai(db):
    _ct(db, [("131", 8_000_000, None, "KH1"), ("5111", None, 8_000_000, "")])
    d = BK.account_book(db, "131", TU, DEN, detail=True)["rows"][-1]
    assert d["balance_debit"] == 8_000_000 and d["balance_credit"] is None


def test_r4b_3_cot_balance_cu_van_con(db):
    """Màn hình cũ đọc `balance`. Bỏ nó đi là làm hỏng một thứ đang chạy để thêm một thứ mới."""
    _ct(db, [("331", None, 3_000_000, "NCC1"), ("1541", 3_000_000, None, "")])
    assert BK.account_book(db, "331", TU, DEN, detail=True)["rows"][-1]["balance"] == -3_000_000


# ══════════════ 2 · BẢNG CÂN ĐỐI — SỐ DƯ HAI BÊN ═════════════════════════════════════════════

def _hai_khach(db):
    """Khách A nợ ta 10 triệu; khách B nộp thừa 4 triệu. Cả hai ở 131, NGƯỢC chiều nhau."""
    _ct(db, [("131", 10_000_000, None, "KH-A"), ("5111", None, 10_000_000, "")], ngay=date(2025, 12, 1))
    _ct(db, [("1111", 4_000_000, None, ""), ("131", None, 4_000_000, "KH-B")], ngay=date(2025, 12, 2))


def test_r4b_4_bu_tru_ra_MOT_so(db):
    _hai_khach(db)
    r = [x for x in BK.trial_balance_range(db, TU, DEN)["rows"] if x["account"] == "131"][0]
    assert r["open_debit"] == 6_000_000 and r["open_credit"] == 0.0


def test_r4b_5_KHONG_bu_tru_ra_HAI_so(db):
    """ĐÂY LÀ PHÉP THỬ QUAN TRỌNG NHẤT của tệp.

    Bù trừ xong thì 4 triệu khách nộp thừa biến mất khỏi bảng và không cách nào đọc lại. Mà nó là
    một khoản PHẢI TRẢ, không phải một khoản phải thu âm.
    """
    _hai_khach(db)
    r = [x for x in BK.trial_balance_range(db, TU, DEN, bu_tru=False)["rows"] if x["account"] == "131"][0]
    assert r["open_debit"] == 10_000_000, r
    assert r["open_credit"] == 4_000_000, (
        "Không bù trừ mà vế Có vẫn bằng 0 nghĩa là phép tính vẫn đang trừ hai đối tượng cho nhau.")


def test_r4b_6_khong_bu_tru_KHONG_dung_vao_phat_sinh(db):
    """Tham số này chỉ đổi cách cộng SỐ DƯ. Phát sinh trong kỳ không được nhúc nhích."""
    _hai_khach(db)
    _ct(db, [("131", 2_000_000, None, "KH-A"), ("5111", None, 2_000_000, "")])
    a = BK.trial_balance_range(db, TU, DEN)
    b = BK.trial_balance_range(db, TU, DEN, bu_tru=False)
    ga = {r["account"]: (r["debit"], r["credit"]) for r in a["rows"]}
    gb = {r["account"]: (r["debit"], r["credit"]) for r in b["rows"]}
    assert ga == gb


def test_r4b_7_xem_kieu_nao_bang_van_phai_can(db):
    _hai_khach(db)
    for bt in (True, False):
        rep = BK.trial_balance_range(db, TU, DEN, bu_tru=bt)
        assert rep["balanced"], f"bu_tru={bt} làm bảng mất cân"


def test_r4b_8_dong_khong_co_ma_doi_tuong_van_duoc_tinh(db):
    """Sổ thật có dòng bỏ trống mã đối tượng. Bỏ chúng ra ngoài là làm bảng không khớp sổ."""
    _ct(db, [("331", None, 7_000_000, ""), ("1541", 7_000_000, None, "")], ngay=date(2025, 11, 5))
    r = [x for x in BK.trial_balance_range(db, TU, DEN, bu_tru=False)["rows"] if x["account"] == "331"][0]
    assert r["open_credit"] == 7_000_000


# ══════════════ 3 · LUỸ KẾ PHÁT SINH TỪ ══════════════════════════════════════════════════════

def test_r4b_9_khong_chon_moc_thi_KHONG_co_hai_cot(db):
    """Không hỏi thì không trả lời. Trả về hai cột rỗng là mời người đọc tưởng đã tính."""
    _ct(db, [("1111", 1_000_000, None, ""), ("5111", None, 1_000_000, "")])
    rep = BK.trial_balance_range(db, TU, DEN)
    assert "luy_ke_debit" not in rep["rows"][0]
    assert "luy_ke_debit" not in rep["total"]


def test_r4b_10_luy_ke_cong_tu_dung_moc_da_chon(db):
    """Luỹ kế đếm TỪ mốc chọn, không từ đầu kỳ xem."""
    _ct(db, [("1111", 1_000_000, None, ""), ("5111", None, 1_000_000, "")], ngay=date(2026, 2, 1))
    _ct(db, [("1111", 3_000_000, None, ""), ("5111", None, 3_000_000, "")], ngay=date(2026, 5, 1))
    rep = BK.trial_balance_range(db, date(2026, 4, 1), DEN, luy_ke_tu=date(2026, 1, 1))
    r = [x for x in rep["rows"] if x["account"] == "111"][0]
    assert r["debit"] == 3_000_000, "phát sinh trong kỳ xem chỉ có tháng 5"
    assert r["luy_ke_debit"] == 4_000_000, "luỹ kế từ 01/01 phải gồm cả tháng 2"


# ══════════════ 4 · TỔNG HỢP CHỨNG TỪ GỐC CÙNG LOẠI ══════════════════════════════════════════

def test_r4b_11_gom_dung_theo_loai(db):
    _ct(db, [("1111", 1_000_000, None, ""), ("131", None, 1_000_000, "KH-A")], loai="PT")
    _ct(db, [("1111", 2_000_000, None, ""), ("131", None, 2_000_000, "KH-B")], loai="PT")
    _ct(db, [("331", 5_000_000, None, "NCC1"), ("1121", None, 5_000_000, "")], loai="PC")
    rep = BK.chung_tu_goc(db, TU, DEN)
    g = {r["ma"]: r for r in rep["rows"]}
    assert g["PT"]["so_chung_tu"] == 2 and g["PT"]["debit"] == 3_000_000
    assert g["PC"]["so_chung_tu"] == 1
    assert g["PT"]["ten"] == CTL.LOAI_CHUNG_TU["PT"]


def test_r4b_12_chung_tu_CHUA_KHAI_LOAI_duoc_dem_rieng_chu_khong_bi_bo(db):
    """LUẬT CHÍNH của mục 4. Bảy mã khai so với 36 của MISA — sẽ luôn có phần chưa khai."""
    _ct(db, [("1111", 1_000_000, None, ""), ("131", None, 1_000_000, "KH-A")], loai="PT")
    _ct(db, [("642", 900_000, None, ""), ("1111", None, 900_000, "")], loai="")
    rep = BK.chung_tu_goc(db, TU, DEN)
    chua = [r for r in rep["rows"] if r["chua_khai"]]
    assert len(chua) == 1 and chua[0]["so_chung_tu"] == 1, rep["rows"]
    assert rep["so_chua_khai"] == 1


def test_r4b_13_tong_bang_PHAI_bang_tong_so(db):
    """Một bảng tổng hợp không khớp sổ thì không dùng để đối chiếu được."""
    _ct(db, [("1111", 1_000_000, None, ""), ("131", None, 1_000_000, "KH-A")], loai="PT")
    _ct(db, [("642", 900_000, None, ""), ("1111", None, 900_000, "")], loai="")
    _ct(db, [("331", 5_000_000, None, "NCC1"), ("1121", None, 5_000_000, "")], loai="PC")
    rep = BK.chung_tu_goc(db, TU, DEN)
    nkc = BK.journal_book(db, TU, DEN)
    assert rep["total"]["debit"] == nkc["total"]["debit"]
    assert rep["total"]["credit"] == nkc["total"]["credit"]


def test_r4b_14_chung_tu_NHAP_khong_len_bang(db):
    """Quy ước số 3 của `books.py`: chỉ lấy chứng từ đã ghi sổ."""
    _ct(db, [("1111", 1_000_000, None, ""), ("131", None, 1_000_000, "KH-A")], loai="PT")
    _ct(db, [("1111", 9_000_000, None, ""), ("131", None, 9_000_000, "KH-C")], loai="PT", status="nhap")
    g = {r["ma"]: r for r in BK.chung_tu_goc(db, TU, DEN)["rows"]}
    assert g["PT"]["so_chung_tu"] == 1 and g["PT"]["debit"] == 1_000_000


def test_r4b_15_tep_excel_dung_duoc(db):
    """Xuất Excel hỏng thì màn hình vẫn xanh mà người dùng không lấy được tệp."""
    _ct(db, [("1111", 1_000_000, None, ""), ("131", None, 1_000_000, "KH-A")], loai="PT")
    assert len(BK.chung_tu_goc_xlsx(BK.chung_tu_goc(db, TU, DEN))) > 2000
    assert len(BK.account_book_xlsx(BK.account_book(db, "131", TU, DEN, detail=True))) > 2000
    assert len(BK.trial_balance_xlsx(BK.trial_balance_range(db, TU, DEN, bu_tru=False))) > 2000
