# -*- coding: utf-8 -*-
"""Đợt E15 (14/10/2026) — ĐỐI CHIẾU TIỀN: sổ kế toán ↔ số đã chốt ↔ số máy cộng.

Ba con số, ba người nói. Lệch giữa SỔ và SỐ ĐÃ CHỐT là hạch toán thiếu/thừa — đi thẳng vào báo cáo
tài chính. Lệch giữa ĐÃ CHỐT và MÁY CỘNG là sao kê về chậm — đã có ô riêng từ DT-2.

"Chưa giải thích hết thì chưa phải đã đối chiếu": phép đo không hỏi "lệch có nhỏ không" mà hỏi
"phần chưa giải thích có bằng không chưa".
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e15.db")
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
from app.models.accounting import Account, JournalEntry, JournalLine  # noqa: E402
from app.models.banks import BankAccount                     # noqa: E402
from app.models.core import Company                          # noqa: E402
from app.models.doi_chieu_tien import GiaiThichLech          # noqa: E402
from app.models.dong_tien import ChotSoDu                    # noqa: E402
from app.services import doi_chieu_tien as DC                # noqa: E402

NGAY = date(2097, 3, 31)
KY = "2097-03"
TK_112 = "11211"


@pytest.fixture(scope="module")
def _so():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module")
def _nen(_so):
    """Một pháp nhân, một tài khoản ngân hàng, sổ có bút toán, và một bản chốt."""
    ct = Company(name="CT thử E15", code="E15", active=True)
    _so.add(ct); _so.flush()
    tk = BankAccount(code="E15B", bank_name="Ngân hàng thử", account_code=TK_112)
    _so.add(tk); _so.flush()
    for ma, ten, loai in ((TK_112, "Tiền gửi thử", "TS"), ("111", "Tiền mặt", "TS"),
                          ("511", "Doanh thu", "DT")):
        if _so.get(Account, ma) is None:
            _so.add(Account(code=ma, name=ten, kind=loai))
    _so.flush()
    # Sổ: thu 1.000.000.000 vào 112, và 200.000.000 vào quỹ tiền mặt.
    e = JournalEntry(code="E15-1", entry_date=NGAY, period=KY, description="thu tiền",
                     status="da_ghi_so", company_id=ct.id, source_type="thu_cong",
                     created_by="ketoan")
    _so.add(e); _so.flush()
    _so.add_all([JournalLine(entry_id=e.id, account_code=TK_112, debit=1_000_000_000, credit=0),
                 JournalLine(entry_id=e.id, account_code="111", debit=200_000_000, credit=0),
                 JournalLine(entry_id=e.id, account_code="511", debit=0, credit=1_200_000_000)])
    _so.commit()
    return {"ct": ct, "tk": tk}


def _chot(_so, _nen, nguon, tai_khoan_id, so_du, so_may_cong=None):
    b = ChotSoDu(company_id=_nen["ct"].id, nguon=nguon, tai_khoan_id=tai_khoan_id,
                 den_ngay=NGAY, so_du=so_du, so_may_cong=so_may_cong,
                 lech=None if so_may_cong is None else round(so_du - so_may_cong, 2),
                 trang_thai="hieu_luc", boi="ketoan")
    _so.add(b); _so.commit()
    return b


def _don(_so, _nen):
    """Dọn mọi bản chốt và lời giải thích của pháp nhân thử — mỗi phép thử tự dựng nền của nó."""
    for m in (GiaiThichLech, ChotSoDu):
        for r in _so.query(m).filter(m.company_id == _nen["ct"].id).all():
            _so.delete(r)
    _so.commit()


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# A. RỖNG KHÁC KHÔNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_e15_1_chua_ai_chot_thi_RONG_chu_khong_phai_0(_so, _nen):
    """Lấy 0 thay cho "chưa ai chốt" là biến một việc chưa làm thành một việc đã làm và khớp."""
    _don(_so, _nen)
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    tm = [r for r in b["rows"] if r["nguon"] == "tien_mat"][0]
    assert tm["so_da_chot"] is None, "chưa ai chốt mà bảng đã có số — đó là số bịa"
    assert tm["lech"] is None, "chênh lệch phải RỖNG khi một trong hai vế rỗng"
    assert tm["con_lai_chua_giai_thich"] is None
    assert tm["xong"] is False, "một dòng rỗng KHÔNG được tính là đã đối chiếu"
    assert "chưa ai chốt" in tm["vi_sao"], "mỗi ô rỗng phải nói được vì sao nó rỗng"


def test_e15_2_so_chua_co_but_toan_thi_so_so_RONG(_so, _nen):
    """Sổ chưa nói gì về tài khoản ấy, khác hẳn sổ nói rằng nó bằng không."""
    _don(_so, _nen)
    tk2 = BankAccount(code="E15C", bank_name="NH chưa ghi sổ", account_code="11299")
    _so.add(tk2); _so.flush()
    _chot(_so, _nen, "ngan_hang", tk2.id, 5_000_000)
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    r = [x for x in b["rows"] if x["tai_khoan_id"] == tk2.id][0]
    assert r["so_so"] is None
    assert r["lech"] is None
    assert "chưa có bút toán nào" in r["vi_sao"]


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# B. BA CON SỐ, VÀ LỆCH ĐÚNG CẶP
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_e15_3_khop_thi_lech_bang_0_va_xong(_so, _nen):
    _don(_so, _nen)
    _chot(_so, _nen, "ngan_hang", _nen["tk"].id, 1_000_000_000)
    _chot(_so, _nen, "tien_mat", None, 200_000_000)
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    assert b["xong"] is True, b["vi_sao_chua_xong"]
    for r in b["rows"]:
        assert r["lech"] == 0
        assert r["xong"] is True


def test_e15_4_lech_la_SO_SO_tru_SO_DA_CHOT_chu_khong_phai_chot_tru_may(_so, _nen):
    """Hai chênh lệch khác nhau, và gộp chúng là mất đường tìm.

    Dựng CỐ Ý một ô mà hai chênh lệch khác hẳn nhau: sổ 1.000.000.000, chốt 900.000.000, máy cộng
    950.000.000. Lệch của đợt này phải là +100.000.000 (sổ − chốt), KHÔNG phải −50.000.000
    (chốt − máy) vốn đã nằm sẵn ở `chot_so_du.lech`.
    """
    _don(_so, _nen)
    b0 = _chot(_so, _nen, "ngan_hang", _nen["tk"].id, 900_000_000, so_may_cong=950_000_000)
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    r = [x for x in b["rows"] if x["tai_khoan_id"] == _nen["tk"].id][0]
    assert r["so_so"] == 1_000_000_000
    assert r["so_da_chot"] == 900_000_000
    assert r["so_may_cong"] == 950_000_000
    assert r["lech"] == 100_000_000, "lệch của đợt này là SỔ − ĐÃ CHỐT"
    assert float(b0.lech) == -50_000_000, "lệch của DT-2 là ĐÃ CHỐT − MÁY CỘNG, không bị đụng tới"


def test_e15_5_khong_co_dong_tong_chenh_lech(_so, _nen):
    """+100 và −100 cộng lại bằng 0, và con số 0 ấy nói dối to hơn cả hai con số nó che đi."""
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    assert "tong_lech" not in b and "tong" not in b


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# C. "CHƯA GIẢI THÍCH HẾT THÌ CHƯA PHẢI ĐÃ ĐỐI CHIẾU"
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_e15_6_giai_thich_mot_phan_van_CHUA_xong(_so, _nen):
    _don(_so, _nen)
    _chot(_so, _nen, "ngan_hang", _nen["tk"].id, 900_000_000)
    _chot(_so, _nen, "tien_mat", None, 200_000_000)
    DC.them_giai_thich(_so, "ketoan", _nen["ct"].id, "ngan_hang", _nen["tk"].id, NGAY,
                       60_000_000, "phí ngân hàng chưa hạch toán")
    _so.commit()
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    r = [x for x in b["rows"] if x["tai_khoan_id"] == _nen["tk"].id][0]
    assert r["da_giai_thich"] == 60_000_000
    assert r["con_lai_chua_giai_thich"] == 40_000_000
    assert r["xong"] is False
    assert b["xong"] is False


def test_e15_7_giai_thich_het_thi_xong(_so, _nen):
    DC.them_giai_thich(_so, "ketoan", _nen["ct"].id, "ngan_hang", _nen["tk"].id, NGAY,
                       40_000_000, "lãi nhập gốc chưa hạch toán")
    _so.commit()
    b = DC.bang(_so, _nen["ct"].id, NGAY)
    r = [x for x in b["rows"] if x["tai_khoan_id"] == _nen["tk"].id][0]
    assert r["con_lai_chua_giai_thich"] == 0
    assert r["xong"] is True
    assert b["xong"] is True


def test_e15_8_go_mot_loi_giai_thich_thi_CHUA_xong_lai(_so, _nen):
    """Gỡ không xoá: ai giải thích sai và ai gỡ là câu kiểm toán sẽ hỏi."""
    g = _so.query(GiaiThichLech).filter(
        GiaiThichLech.company_id == _nen["ct"].id,
        GiaiThichLech.trang_thai == "hieu_luc").first()
    DC.huy_giai_thich(_so, "ketoan", g.id, "ghi nhầm tài khoản")
    _so.commit()
    assert _so.get(GiaiThichLech, g.id) is not None, "dòng bị XOÁ — phải là đánh dấu đã gỡ"
    assert _so.get(GiaiThichLech, g.id).huy_boi == "ketoan"
    assert DC.bang(_so, _nen["ct"].id, NGAY)["xong"] is False


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# D. CỬA GHI GIẢI THÍCH CHẶN GÌ
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_e15_9_bon_phep_chan_cua_cua_ghi(_so, _nen):
    cid = _nen["ct"].id
    with pytest.raises(DC.LoiDoiChieu):          # lý do rỗng
        DC.them_giai_thich(_so, "ketoan", cid, "ngan_hang", _nen["tk"].id, NGAY, 1_000_000, "  ")
    with pytest.raises(DC.LoiDoiChieu):          # số tiền 0
        DC.them_giai_thich(_so, "ketoan", cid, "ngan_hang", _nen["tk"].id, NGAY, 0, "gì đó")
    with pytest.raises(DC.LoiDoiChieu):          # tiền mặt mà có số tài khoản
        DC.them_giai_thich(_so, "ketoan", cid, "tien_mat", _nen["tk"].id, NGAY, 1_000_000, "x")
    with pytest.raises(DC.LoiDoiChieu):          # chưa ai chốt ngày ấy
        DC.them_giai_thich(_so, "ketoan", cid, "ngan_hang", _nen["tk"].id,
                           date(2097, 1, 1), 1_000_000, "x")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# E. PHÉP CHẶN KHÓA KỲ
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_e15_10_con_chenh_lech_chua_giai_thich_thi_khong_khoa_ky_duoc(_so, _nen):
    xau = DC.ly_do_chua_khoa_duoc(_so, KY)
    assert xau, "còn 40 triệu chưa giải thích mà phép chặn im lặng"
    assert any("chưa giải thích" in s for s in xau)


def test_e15_11_giai_thich_het_thi_khoa_duoc(_so, _nen):
    # Sau khi `test_e15_8` gỡ khoản 60tr, phần còn lại đúng 60tr. Con số này viết tay chứ không
    # đọc từ chính hàm đang thử — đọc từ nó thì phép thử luôn đúng, kể cả khi hàm sai.
    con_lai = [r for r in DC.bang(_so, _nen["ct"].id, NGAY)["rows"]
               if r["tai_khoan_id"] == _nen["tk"].id][0]["con_lai_chua_giai_thich"]
    assert con_lai == 60_000_000, f"nền của phép thử lệch: còn {con_lai}, chờ 60.000.000"
    DC.them_giai_thich(_so, "ketoan", _nen["ct"].id, "ngan_hang", _nen["tk"].id, NGAY,
                       60_000_000, "ghi lại khoản vừa gỡ, đúng tài khoản")
    _so.commit()
    assert DC.bang(_so, _nen["ct"].id, NGAY)["xong"] is True
    assert DC.ly_do_chua_khoa_duoc(_so, KY) == []


def test_e15_12_khong_chot_trong_ky_thi_phep_chan_KHONG_keu_va_do_la_lo_da_biet(_so, _nen):
    """Giới hạn CÓ CHỦ Ý, ghi lại ở đây để lần sau ai đọc cũng thấy nó hở ở đâu.

    Pháp nhân cả tháng không chốt lần nào thì không có bản chốt để so, nên phép chặn không kêu —
    tức là bỏ hẳn việc chốt thì khóa kỳ vẫn trôi. Bịt lỗ ấy là ĐÒI mỗi kỳ phải có chốt số dư, một
    nghĩa vụ hàng tháng mới, phải có người ký. Phép thử này canh đúng hành vi hiện tại; ngày ai đó
    thêm quy định ấy thì nó đỏ, và người sửa phải tới đọc dòng này.
    """
    assert DC.ly_do_chua_khoa_duoc(_so, "2097-01") == [], (
        "kỳ không ai chốt mà phép chặn đã kêu — hành vi đổi, đọc lại docstring")


def test_e15_13_lock_period_goi_dung_phep_chan_nay(_so):
    """Phép chặn phải NẰM TRONG đường khóa kỳ, không phải một hàm ai nhớ thì gọi."""
    import inspect
    from app.services import accounting as ACC
    nguon = inspect.getsource(ACC.lock_period)
    assert "ly_do_chua_khoa_duoc" in nguon, (
        "khóa kỳ không hỏi tới đối chiếu tiền — hàng rào nằm ngoài đường đi là hàng rào không có")
