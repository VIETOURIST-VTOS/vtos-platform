# -*- coding: utf-8 -*-
"""Đợt E17 (14/10/2026) — CHỈ TIÊU 112, TƯƠNG ĐƯƠNG TIỀN.

VÌ SAO CÓ TỆP NÀY

Ngày 14/10/2026, sau khi Đợt E16 dựng cửa nạp bộ số BCTC đã ký, lần đối chiếu đầu tiên giữa BCTC
lập từ sổ VTOS và bản soát xét Baker Tilly cho 31/34 chỉ tiêu khớp tuyệt đối. Ba chỉ tiêu lệch, và
cả ba cùng một nguyên nhân: trong danh mục 125 tài khoản KHÔNG có mã nào ánh xạ chỉ tiêu 112.

  bản đã ký : 110 = 12.234.364.512  ·  111 = 8.030.563.416  ·  112 = 4.203.801.096  ·  123 = 508.355.556
  sổ VTOS   : 110 =  8.030.563.416  ·  111 = 8.030.563.416  ·  112 =             0  ·  123 = 4.712.156.652

Tổng 100/280 không đổi — tiền chỉ chạy sang dòng bên cạnh. Nhưng hai dòng ấy là hai dòng người đọc
báo cáo nhìn đầu tiên khi hỏi "công ty còn bao nhiêu tiền tiêu được ngay", nên sai chỗ này là sai
đúng câu hỏi quan trọng nhất.

TỆP NÀY CANH NĂM ĐIỀU

 1. CÓ một tài khoản ánh xạ chỉ tiêu 112, và chỉ MỘT — hai tài khoản cùng ánh xạ là cộng đôi.
 2. 1281 GIỮ NGUYÊN ánh xạ 123 — thêm tiểu khoản không được đổi nghĩa tài khoản đang có số dư thật.
 3. LUẬT nói KỲ HẠN GỐC, và nói rõ KHÔNG phải thời gian còn lại. Đây là chỗ dễ sửa sai nhất.
 4. BÁO CÁO CHẠY ĐÚNG: ghi vào 12811 thì lên 112, ghi vào 1281 thì lên 123, và 110 = 111 + 112.
 5. TIỀN GỬI PHẢI CÓ ĐỐI TƯỢNG: 12811 nằm trong `NEED_PARTNER` — một khoản tiền gửi không nói
    gửi ở ngân hàng nào thì sáu tháng sau không ai đối chiếu được với sao kê.

ĐỢT NÀY KHÔNG CHUYỂN MỘT ĐỒNG NÀO, và `test_e17_6` canh đúng điều đó.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e17.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import json                                                     # noqa: E402
import pathlib                                                  # noqa: E402

from sqlalchemy import select                                   # noqa: E402

from sqlalchemy import create_engine                          # noqa: E402
from sqlalchemy.orm import sessionmaker                        # noqa: E402

from app.db.session import Base                                # noqa: E402
from app.models.accounting import Account, JournalEntry, JournalLine   # noqa: E402
from app.services import accounting as ACC                      # noqa: E402
from app.services import bctc as BCTC                           # noqa: E402

def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ, không dùng chung với tệp phép thử khác.

    Cửa hẹp của CI chạy 16 tệp trong MỘT tiến trình, nên `SessionLocal` lúc ấy trỏ vào CSDL của tệp
    nào nhập trước. Phép thử này ghi bút toán để đo, mà ghi vào CSDL dùng chung thì nó làm lệch số
    của tệp khác (test_misa đối chiếu 280 với bộ số kiểm toán tới từng đồng) — hỏng theo kiểu khó
    tìm nhất: đỏ ở một tệp không hề liên quan.
    """
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _chart() -> dict:
    goc = pathlib.Path(ACC.__file__).resolve().parent.parent / "data" / "misa_tai_khoan.json"
    return {r["code"]: r for r in json.loads(goc.read_text(encoding="utf-8"))["tai_khoan"]}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. DANH MỤC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e17_1_dung_mot_tai_khoan_anh_xa_chi_tieu_112():
    """Không có tài khoản nào thì chỉ tiêu 112 luôn bằng 0 — chỗ hỏng của đợt này.
    Có HAI tài khoản thì cùng một khoản tiền được cộng hai lần — hỏng theo hướng ngược lại."""
    ch = _chart()
    co = sorted(c for c, r in ch.items() if (r.get("bs_debit") or "") == ACC.CHI_TIEU_TUONG_DUONG_TIEN)
    assert co == [ACC.TK_TUONG_DUONG_TIEN], (
        f"Chỉ tiêu {ACC.CHI_TIEU_TUONG_DUONG_TIEN} phải do ĐÚNG MỘT tài khoản "
        f"({ACC.TK_TUONG_DUONG_TIEN}) nuôi, đang thấy: {co}")
    r = ch[ACC.TK_TUONG_DUONG_TIEN]
    assert r["parent"] == "1281" and r["kind"] == "TS"
    assert "3 tháng" in r["name"], "Tên tài khoản phải tự nói ra điều kiện, vì người gõ đọc tên trước"


def test_e17_2_1281_giu_nguyen_anh_xa_123():
    """Thêm một tiểu khoản KHÔNG được đổi nghĩa tài khoản cha đang có số dư thật."""
    ch = _chart()
    assert ch["1281"]["bs_debit"] == "123"
    assert ch["128"]["bs_debit"] == "123"


def test_e17_3_luat_noi_ky_han_goc_chu_khong_phai_thoi_gian_con_lai():
    """Chỗ dễ làm sai nhất, và làm sai thì sai theo hướng THỔI PHỒNG TIỀN: một khoản gửi 12 tháng
    còn 2 tháng nữa đáo hạn KHÔNG phải tương đương tiền, dù nhìn thì "sắp rút được".

    ĐÃ THỬ PHÁ: đổi luật thành "thời gian còn lại" → tệp này đỏ ngay.
    """
    q = ACC.QUY_TAC_TUONG_DUONG_TIEN
    assert "KỲ HẠN GỐC" in q, "Luật phải nói rõ xét theo kỳ hạn GỐC"
    assert "KHÔNG phải thời gian còn lại" in q, (
        "Luật phải nói thẳng điều nó LOẠI TRỪ. Một luật chỉ nói điều nó cho phép thì người đọc sau "
        "sẽ tự suy ra điều nó cấm, và suy sai.")
    assert "3 tháng" in q


def test_e17_4_tien_gui_phai_co_doi_tuong():
    """Một khoản tiền gửi không nói gửi ở ngân hàng nào thì không đối chiếu được với sao kê."""
    assert ACC.TK_TUONG_DUONG_TIEN.startswith(ACC.NEED_PARTNER)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. BÁO CÁO CHẠY ĐÚNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _so(db, dong):
    e = JournalEntry(code="E17-1", entry_date=date(2026, 6, 30), period="2026-06",
                     description="Số dư thử Đợt E17", status="da_ghi_so", source_type="kiem_toan",
                     source_ref="kt:20260630")
    db.add(e)
    db.flush()
    for tk, no, co in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co,
                           partner_code="NH_THU" if tk.startswith("1281") else ""))
    db.commit()


def test_e17_5_ghi_12811_len_112_ghi_1281_len_123():
    """Phép đo thật: dựng sổ, lập báo cáo, đọc hai chỉ tiêu. Không đo bằng cách đọc danh mục —
    danh mục đúng mà đường tính sai thì báo cáo vẫn sai."""
    db = _rieng()
    try:
        ACC.seed_accounts(db)
        assert db.get(Account, ACC.TK_TUONG_DUONG_TIEN) is not None, "seed phải mở tài khoản mới"
        assert db.get(Account, "1281").is_detail is False, (
            "1281 nay là tài khoản CHA — đúng lệ `banks.py` khi mở tiểu khoản 112 theo ngân hàng")

        _so(db, [("1111", 1_000_000_000, 0),      # tiền mặt      → chỉ tiêu 111
                 ("12811", 4_000_000_000, 0),     # gốc ≤ 3 tháng → chỉ tiêu 112
                 ("1281", 500_000_000, 0),        # phần còn lại  → chỉ tiêu 123
                 ("411", 0, 5_500_000_000)])
        v = BCTC.balance_sheet_tt99(db, date(2026, 6, 30))["values"]
        assert v.get("111") == 1_000_000_000
        assert v.get("112") == 4_000_000_000, "tiền gửi gốc ≤ 3 tháng phải lên ĐÚNG dòng 112"
        assert v.get("123") == 500_000_000, "phần còn lại của 1281 vẫn ở 123"
        assert v.get("110") == 5_000_000_000, "110 = 111 + 112"
        assert v.get("120") == 500_000_000
        # KHÔNG cộng trùng: tổng hai chỉ tiêu đúng bằng tiền đã ghi, không hơn một đồng
        assert v.get("112") + v.get("123") == 4_500_000_000
        assert abs(v.get("280", 0) - v.get("440", 0)) < 1, "bảng vẫn phải cân"
    finally:
        db.close()


def test_e17_6_dot_nay_khong_chuyen_mot_dong_nao():
    """Thêm tài khoản chỉ mở CHỖ cho con số. Số dư 1281 đang có nằm nguyên tại 1281 cho tới khi
    Kế toán tải lên một bộ số BCTC tách hai dòng, Chủ tịch ký, rồi chốt sổ lại (đường Đợt E16).

    Máy KHÔNG tự suy phần nào có kỳ hạn gốc ≤ 3 tháng: điều ấy nằm ở hợp đồng tiền gửi, không nằm
    trong sổ. Tự suy là bịa ra một lời khai không ai ký — đúng cái Đợt E16 vừa dựng cửa để chặn.
    """
    import inspect
    nguon = inspect.getsource(ACC)
    ma = [l.strip() for l in nguon.splitlines()
          if ACC.TK_TUONG_DUONG_TIEN in l and not l.strip().startswith("#")]
    assert ma == [f'TK_TUONG_DUONG_TIEN = "{ACC.TK_TUONG_DUONG_TIEN}"'], (
        f"Mã 12811 chỉ được nằm ở ĐÚNG MỘT dòng mã trong `accounting.py` — dòng khai "
        f"`TK_TUONG_DUONG_TIEN` (chú thích thì tùy). Gõ nó vào một phép tính là bước đầu của việc "
        f"chuyển số dư bằng robot, mà kỳ hạn gốc nằm ở hợp đồng tiền gửi chứ không nằm trong sổ. "
        f"Đang thấy: {ma}")
    assert ACC.TK_TUONG_DUONG_TIEN not in inspect.getsource(BCTC), (
        "`bctc.py` không được biết mã 12811 — ánh xạ chỉ tiêu đọc từ danh mục tài khoản, không "
        "viết tay trong phép tính.")
    assert "seed_accounts" in nguon and ACC.TK_TUONG_DUONG_TIEN not in inspect.getsource(
        ACC.seed_accounts), "`seed_accounts` chỉ nạp danh mục, không gọi tên tài khoản nào"
