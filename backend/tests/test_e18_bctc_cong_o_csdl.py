# -*- coding: utf-8 -*-
"""Đợt E18 (15/10/2026) — CỬA BCTC CỘNG Ở CƠ SỞ DỮ LIỆU, KHÔNG KÉO CẢ SỔ VỀ BỘ NHỚ.

VÌ SAO CÓ TỆP NÀY

Ngày 15/10/2026 cửa `GET /reports/bctc` trả 502 liên tục trên máy chủ thật trong khi mọi cửa khác
chạy bình thường. Nguyên nhân không phải một sự cố nhất thời: MỘT lần lập BCTC gọi
`account_balances` SÁU lần và `income_statement` HAI lần, và cả hai hàm ấy đều đi qua một hàm
`_lines` kéo TOÀN BỘ dòng bút toán từ đầu sổ đến ngày báo cáo về bộ nhớ dưới dạng đối tượng ORM.
Với 25.715 chứng từ đã nạp từ MISA thì máy chủ 512 MB hết bộ nhớ trước khi tính xong — và sổ chỉ
dày thêm theo thời gian.

Đợt này ĐỔI CHỖ CỘNG, KHÔNG ĐỔI PHÉP CỘNG. Bản cũ bị XOÁ, nên từ nay thứ canh phép tính không còn
là "so với bản cũ" mà là TỆP NÀY: một sổ tự dựng, và đáp án viết tay bằng tay — không lấy từ máy.

TỆP NÀY CANH BẢY ĐIỀU

 1. BẢNG CÂN ĐỐI ra ĐÚNG từng đồng trên một sổ tự dựng, và bảng phải cân.
 2. KQKD ra ĐÚNG từng đồng, kể cả chỉ tiêu 24 (lãi vay) lấy thêm từ 6351.
 3. BỎ BÚT TOÁN KẾT CHUYỂN LÀ BỎ CẢ CHỨNG TỪ — bỏ mỗi dòng 911 thì vế Nợ 511 ở lại và triệt tiêu
    cả kỳ doanh thu. Canh cả hai dấu: chứng từ chạm 911 mà KHÔNG gắn nguồn, và chứng từ gắn nguồn
    `ket_chuyen` mà KHÔNG chạm 911.
 4. KHÓA ĐỐI TƯỢNG là `partner_code`, thiếu thì lấy `partner` (TÊN). Gộp thẳng theo `partner_code`
    sẽ dồn mọi dòng chỉ có tên vào cùng một ô rỗng, và chỉ tiêu 131/312 bù trừ nhau mất.
 5. BỎ BÚT TOÁN CHỐT SỔ KIỂM TOÁN khỏi LCTT cũng là bỏ CẢ CHỨNG TỪ.
 6. KHÔNG CÒN CÂU TRUY VẤN NÀO ĐỌC DÒNG BÚT TOÁN MÀ KHÔNG CỘNG DỒN Ở CƠ SỞ DỮ LIỆU — đây là phép
    thử canh đúng chỗ hỏng, vì một bản sửa ra số đúng mà vẫn kéo cả sổ về thì 502 quay lại.
 7. LUẬT KẾT CHUYỂN KHAI Ở ĐÚNG MỘT CHỖ. Trước đợt này nó nằm ở cả `bctc.py` lẫn `reports.py`, và
    hai chỗ là hai chỗ để lệch nhau.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e18.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import inspect                                                   # noqa: E402

import pytest                                                    # noqa: E402
from sqlalchemy import create_engine, event                       # noqa: E402
from sqlalchemy.orm import sessionmaker                           # noqa: E402

from app.db.session import Base                                   # noqa: E402
from app.models.accounting import JournalEntry, JournalLine       # noqa: E402
from app.services import accounting as ACC                        # noqa: E402
from app.services import bctc as BCTC                             # noqa: E402
from app.services import reports as RP                            # noqa: E402

UPTO = date(2026, 6, 30)
SINCE = date(2026, 1, 1)


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ, không dùng chung với tệp phép thử khác.

    Cửa hẹp của CI chạy 16 tệp trong MỘT tiến trình, nên `SessionLocal` lúc ấy trỏ vào CSDL của tệp
    nào nhập trước. Tệp này ghi bút toán để đo, mà ghi vào CSDL dùng chung thì làm lệch số của tệp
    khác (test_misa đối chiếu tới từng đồng) — hỏng theo kiểu khó tìm nhất: đỏ ở một tệp không liên
    quan. Trả về (session, engine) vì phép thử số 6 cần gắn tai nghe vào engine.
    """
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)(), e


def _ct(db, ma, ngay, dong, nguon="thu_cong", ref="", mo_ta="Sổ thử Đợt E18"):
    """Ghi MỘT chứng từ đã ghi sổ. `dong` = [(tài khoản, Nợ, Có, mã đối tượng, tên đối tượng)]."""
    e = JournalEntry(code=ma, entry_date=ngay, ngay_chung_tu=ngay, period=f"{ngay:%Y-%m}",
                     description=mo_ta, status="da_ghi_so", source_type=nguon, source_ref=ref)
    db.add(e)
    db.flush()
    for tk, no, co, mdt, tdt in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co,
                           partner_code=mdt, partner=tdt))
    db.commit()
    return e


def _so_co_ban(db):
    """SỔ THỬ — mười một dòng, đủ để mọi chỉ tiêu dưới đây tính được bằng tay.

    Mốc cuối: 30/06/2026. Kỳ KQKD: 01/01/2026 → 30/06/2026.
    """
    ACC.seed_accounts(db)
    # 1. Chủ sở hữu góp tiền
    _ct(db, "E18-1", date(2026, 1, 5), [("1111", 10_000_000_000, 0, "", ""),
                                        ("411", 0, 10_000_000_000, "", "")])
    # 2. Mua hàng tồn kho, còn nợ người bán (331 có MÃ đối tượng)
    _ct(db, "E18-2", date(2026, 1, 10), [("156", 2_500_000_000, 0, "", ""),
                                         ("331", 0, 2_500_000_000, "NCC01", "Nhà cung cấp 01")])
    # 3. Bán hàng cho khách có MÃ, còn phải thu
    _ct(db, "E18-3", date(2026, 3, 20), [("131", 3_300_000_000, 0, "KH01", "Khách hàng 01"),
                                         ("5111", 0, 3_000_000_000, "", ""),
                                         ("33311", 0, 300_000_000, "", "")])
    # 4. Giá vốn hàng đã bán
    _ct(db, "E18-4", date(2026, 3, 21), [("632", 2_000_000_000, 0, "", ""),
                                         ("156", 0, 2_000_000_000, "", "")])
    # 5. Trả lãi vay bằng tiền — 6351, chỉ tiêu 23 VÀ cộng thêm vào chỉ tiêu 24
    _ct(db, "E18-5", date(2026, 3, 25), [("6351", 100_000_000, 0, "", ""),
                                         ("1111", 0, 100_000_000, "", "")])
    # 6. Khách KHÔNG CÓ MÃ ứng tiền trước — chỉ có TÊN. Đây là chỗ canh khóa đối tượng (điều 4).
    _ct(db, "E18-6", date(2026, 5, 10), [("1111", 500_000_000, 0, "", ""),
                                         ("131", 0, 500_000_000, "", "Khách lẻ chưa có mã")])
    # 7. KẾT CHUYỂN cuối kỳ, LẬP TAY (nguồn `thu_cong`) nhưng chạm 911 — chứng từ nguy hiểm nhất,
    #    vì không có nhãn nào để đếm. Nếu chỉ bỏ các dòng 911 thì vế Nợ 5111 ở lại và triệt tiêu
    #    đúng cả kỳ doanh thu — đó là lỗi đã từng nằm trên màn hình Chủ tịch (xem test_tc).
    _ct(db, "E18-7", UPTO, [("5111", 3_000_000_000, 0, "", ""),
                            ("911", 0, 3_000_000_000, "", ""),
                            ("911", 2_100_000_000, 0, "", ""),
                            ("632", 0, 2_000_000_000, "", ""),
                            ("6351", 0, 100_000_000, "", ""),
                            ("911", 900_000_000, 0, "", ""),
                            ("421", 0, 900_000_000, "", "")],
        mo_ta="Kết chuyển xác định KQKD (lập tay, không gắn nguồn)")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. BẢNG CÂN ĐỐI — ĐÁP ÁN VIẾT TAY
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e18_1_bang_can_doi_dung_tung_dong():
    """Đáp án tính bằng tay từ bảy chứng từ ở `_so_co_ban`, KHÔNG lấy từ máy:

        1111 = 10.000.000.000 − 100.000.000 + 500.000.000 = 10.400.000.000  → chỉ tiêu 111
        156  =  2.500.000.000 − 2.000.000.000             =    500.000.000  → chỉ tiêu 141
        131  : KH01 +3.300.000.000 (dư Nợ → 131) · "Khách lẻ" −500.000.000 (dư Có → 312)
        331  : NCC01 −2.500.000.000 (dư Có)               → chỉ tiêu 311
        33311 =   −300.000.000                            → chỉ tiêu 314
        411   = −10.000.000.000                           → chỉ tiêu 411
        421   =    −900.000.000                           → chỉ tiêu 420
        5111/632/6351/911 : sau kết chuyển bằng 0         → lãi chưa kết chuyển = 0

        TÀI SẢN  = 10.400 + 3.300 +   500                      = 14.200.000.000
        NGUỒN VỐN=  2.500 +   500 +   300 + 10.000 + 900       = 14.200.000.000
    """
    db, _ = _rieng()
    try:
        _so_co_ban(db)
        bs = BCTC.balance_sheet_tt99(db, UPTO)
        v = bs["values"]
        assert v.get("111") == 10_400_000_000
        assert v.get("141") == 500_000_000
        assert v.get("131") == 3_300_000_000
        assert v.get("312") == 500_000_000
        assert v.get("311") == 2_500_000_000
        assert v.get("314") == 300_000_000
        assert v.get("411") == 10_000_000_000
        assert v.get("420") == 900_000_000
        assert v.get("100") == 14_200_000_000
        assert v.get("280") == 14_200_000_000
        assert v.get("310") == 3_300_000_000
        assert v.get("400") == 10_900_000_000
        assert v.get("440") == 14_200_000_000
        assert bs["balanced"] is True
        assert abs(bs["unposted_pl"]) < 0.5, "sổ thử đã kết chuyển hết, không còn lãi treo"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. KQKD — ĐÁP ÁN VIẾT TAY, VÀ CHỈ TIÊU 24
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e18_2_kqkd_dung_tung_dong_va_chi_tieu_24():
    """Đáp án viết tay (chứng từ 7 là kết chuyển, BỊ LOẠI TRỌN VẸN khỏi kỳ):

        01 = 3.000.000.000  ·  11 = 2.000.000.000  ·  23 = 100.000.000  ·  24 = 100.000.000
        10 = 01−02 = 3.000.000.000
        20 = 10−11 = 1.000.000.000
        30 = 20+21+22−23−25−26+27 = 1.000.000.000 − 100.000.000 = 900.000.000
        50 = 30+40 = 900.000.000  ·  60 = 50−51−52 = 900.000.000

    Chỉ tiêu 24 "Chi phí lãi vay" lấy THÊM từ 6351 — nó không thay 23 mà cộng song song, vì mẫu
    B02-DN khai 24 là dòng thuyết minh nằm TRONG 23. Bỏ chỗ ấy thì LCTT gián tiếp mất dòng 06 và
    dòng 70 không còn khớp tiền cuối kỳ.
    """
    db, _ = _rieng()
    try:
        _so_co_ban(db)
        v = BCTC.income_statement_tt99(db, SINCE, UPTO)["values"]
        assert v.get("01") == 3_000_000_000, (
            "Doanh thu phải là CẢ KỲ. Ra 0 nghĩa là bút toán kết chuyển chỉ bị bỏ mỗi dòng 911, "
            "vế Nợ 5111 ở lại và triệt tiêu đúng cả kỳ doanh thu.")
        assert v.get("11") == 2_000_000_000
        assert v.get("23") == 100_000_000
        assert v.get("24") == 100_000_000, "6351 phải cộng thêm vào chỉ tiêu 24"
        assert v.get("10") == 3_000_000_000
        assert v.get("20") == 1_000_000_000
        assert v.get("30") == 900_000_000
        assert v.get("50") == 900_000_000
        assert v.get("60") == 900_000_000
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. BỎ KẾT CHUYỂN LÀ BỎ CẢ CHỨNG TỪ — CẢ HAI DẤU
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e18_3_ket_chuyen_gan_nguon_ma_khong_cham_911_cung_bi_loai():
    """Dấu thứ hai: chứng từ do robot lập, gắn nguồn `ket_chuyen`, nhưng không có dòng 911 nào.

    Bỏ dấu này thì chứng từ lọt vào KQKD và doanh thu bị trừ đi đúng số đã kết chuyển.
    """
    db, _ = _rieng()
    try:
        _so_co_ban(db)
        _ct(db, "E18-8", UPTO, [("5111", 400_000_000, 0, "", ""),
                                ("421", 0, 400_000_000, "", "")],
            nguon="ket_chuyen", mo_ta="Kết chuyển do robot lập, không đi qua 911")
        v = BCTC.income_statement_tt99(db, SINCE, UPTO)["values"]
        assert v.get("01") == 3_000_000_000, (
            "Chứng từ nguồn `ket_chuyen` phải bị loại dù không chạm 911")
    finally:
        db.close()


def test_e18_4_luat_ket_chuyen_khai_o_dung_mot_cho():
    """Trước Đợt E18 luật này nằm ở cả `bctc.py` lẫn `reports.py`, viết tay hai lần cho cùng một
    câu hỏi. Hai chỗ là hai chỗ để lệch nhau — và chúng ĐÃ lệch nhau thật một lần (xem chú thích
    `reports._khong_phai_ket_chuyen`). Nay chỉ `bctc.khong_phai_ket_chuyen` được khai luật.
    """
    assert hasattr(BCTC, "khong_phai_ket_chuyen")
    nguon_rp = inspect.getsource(RP._khong_phai_ket_chuyen)
    ma = [l.strip() for l in nguon_rp.splitlines()
          if '911%' in l and not l.strip().startswith("#")]
    assert ma == [], (
        "`reports.py` không được viết lại điều kiện 911 — phải gọi "
        "`bctc.khong_phai_ket_chuyen()`. Đang thấy: " + repr(ma))
    assert "khong_phai_ket_chuyen()" in nguon_rp


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. KHÓA ĐỐI TƯỢNG: MÃ TRƯỚC, THIẾU THÌ TÊN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e18_5_khoa_doi_tuong_thieu_ma_thi_lay_ten():
    """Chứng từ 3 có khách CÓ MÃ (dư Nợ), chứng từ 6 có khách CHỈ CÓ TÊN (dư Có). Hai bên phải nằm
    ở HAI ô khác nhau, nên lên hai chỉ tiêu khác nhau: 131 (phải thu) và 312 (người mua ứng trước).

    ĐÃ THỬ PHÁ: gộp thẳng theo `partner_code` → cả hai dồn vào ô rỗng, net = 2.800.000.000, chỉ
    tiêu 131 còn 2.800.000.000 và 312 mất hẳn. Đây đúng là kiểu hỏng đã gặp một lần rồi.
    """
    db, _ = _rieng()
    try:
        _so_co_ban(db)
        bal = BCTC.account_balances(db, UPTO)
        bp = bal["131"]["by_partner"]
        assert bp.get("KH01") == 3_300_000_000
        assert bp.get("Khách lẻ chưa có mã") == -500_000_000, (
            "Dòng chỉ có TÊN đối tượng phải nằm ở ô riêng theo tên, không dồn vào ô rỗng. "
            f"Đang thấy các ô: {sorted(bp)}")
        assert bal["131"]["net"] == 2_800_000_000, "net của tài khoản vẫn là tổng đại số"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. BỎ CHỐT SỔ KIỂM TOÁN LÀ BỎ CẢ CHỨNG TỪ
# ══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("nguon,ref,mo_ta", [
    ("kiem_toan", "", "Chốt sổ theo BCTC kiểm toán"),
    ("thu_cong", "kt:20260630", "Chốt sổ theo BCTC kiểm toán"),
    ("thu_cong", "kt-close:20260630", "Kết chuyển KQKD để chốt sổ kiểm toán"),
    ("dao", "", "Đảo bút toán để nạp lại mốc kiểm toán 30/06/2026"),
])
def test_e18_6_bon_dau_cua_but_toan_chot_so_kiem_toan(nguon, ref, mo_ta):
    """Bút toán RESTATEMENT một lần để khớp sổ với bản đã kiểm toán — KHÔNG phải dòng tiền phát
    sinh trong kỳ. Tính vào biến động số dư thì LCTT hiểu nhầm thành thu chi khổng lồ.

    Loại là loại CẢ CHỨNG TỪ: cả vế 1111 lẫn vế 421 phải cùng biến mất.
    """
    db, _ = _rieng()
    try:
        _so_co_ban(db)
        _ct(db, "E18-9", UPTO, [("1111", 7_000_000, 0, "", ""),
                                ("421", 0, 7_000_000, "", "")],
            nguon=nguon, ref=ref, mo_ta=mo_ta)
        assert BCTC.account_balances(db, UPTO)["1111"]["net"] == 10_407_000_000, (
            "báo cáo THTC chính thức PHẢI thấy bút toán này — nó là số dư sổ sách thật")
        bo = BCTC.account_balances(db, UPTO, exclude_kiem_toan=True)
        assert bo["1111"]["net"] == 10_400_000_000, f"dấu {nguon!r}/{ref!r} chưa được nhận ra"
        assert bo["421"]["net"] == -900_000_000, "loại phải là loại CẢ CHỨNG TỪ, không phải một vế"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. CHỖ HỎNG CỦA ĐỢT NÀY: KHÔNG CÒN CÂU TRUY VẤN NÀO ĐỌC DÒNG MÀ KHÔNG CỘNG DỒN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e18_7_khong_cau_nao_doc_dong_but_toan_ma_khong_cong_don():
    """ĐÂY LÀ PHÉP THỬ CANH ĐÚNG CHỖ HỎNG. Một bản sửa ra đủ số đúng mà vẫn kéo cả sổ về bộ nhớ
    thì 502 quay lại nguyên vẹn, và sáu phép thử trên đều xanh.

    Đo bằng cách nghe mọi câu truy vấn thật mà cơ sở dữ liệu nhận: câu nào đọc `journal_lines` thì
    phải có `GROUP BY`. Truy vấn con lọc chứng từ kết chuyển nằm BÊN TRONG một câu có GROUP BY nên
    không phá điều kiện này.
    """
    db, e = _rieng()
    try:
        _so_co_ban(db)
        cau = []

        @event.listens_for(e, "before_cursor_execute")
        def _nghe(conn, cur, stmt, params, ctx, many):   # noqa: ANN001
            cau.append(" ".join(stmt.lower().split()))

        BCTC.bctc(db, UPTO, SINCE)
        event.remove(e, "before_cursor_execute", _nghe)

        doc_dong = [s for s in cau if "journal_lines" in s]
        assert doc_dong, "phép thử phải thực sự đo một lần lập BCTC"
        tho = [s for s in doc_dong if "group by" not in s]
        assert tho == [], (
            "Có câu truy vấn đọc `journal_lines` mà KHÔNG cộng dồn ở cơ sở dữ liệu — đúng chỗ hỏng "
            f"Đợt E18 vừa sửa. Câu đầu tiên: {tho[0][:300]}")
    finally:
        db.close()


def test_e18_8_khong_con_ham_keo_ca_so_ve_bo_nho():
    """Bản cũ đã bị XOÁ, không để lại. Một hàm kéo cả sổ về mà còn nằm đó thì lần sau có người gọi
    lại — và không ai đọc chú thích trước khi gọi một hàm có sẵn.

    CÒN ĐÚNG MỘT CHỖ chọn cả đối tượng `JournalLine`, và nó được kể tên ở đây chứ không để lặng lẽ:
    `loan_bank_detail_341` (báo cáo chi tiết vay theo ngân hàng). Chỗ ấy KHÔNG nằm trên đường lập
    BCTC và đã lọc `account_code.in_(loan_codes)` nên nó chỉ đọc dòng của mấy tài khoản vay — không
    phồng theo cả sổ như `_lines` cũ. Đợt E18 cố ý không sửa nó: nó không phải chỗ hỏng, và sửa
    kèm thì đợt này đổi hai thứ cùng lúc. Phép thử dưới đây GHIM đúng một ngoại lệ ấy — thêm chỗ
    thứ hai, hoặc bỏ cái lọc theo tài khoản của nó, thì đỏ.
    """
    nguon = inspect.getsource(BCTC)
    assert "def _lines(" not in nguon, (
        "`bctc._lines` phải bị xoá hẳn: nó là hàm kéo toàn bộ dòng bút toán về bộ nhớ.")
    for ten in ("account_balances", "income_statement_tt99"):
        ham = inspect.getsource(getattr(BCTC, ten))
        assert "select(JournalLine)" not in ham and "select(JournalLine," not in ham, (
            f"`{ten}` phải chỉ chọn CỘT và cộng dồn bằng GROUP BY, không chọn cả đối tượng")
        assert "group_by" in ham, f"`{ten}` phải cộng dồn ở cơ sở dữ liệu"
    ca = [l.strip() for l in nguon.splitlines()
          if ("select(JournalLine)" in l or "select(JournalLine," in l)
          and not l.strip().startswith("#")]
    assert len(ca) == 1, (
        "Chỉ được còn ĐÚNG MỘT chỗ chọn cả đối tượng `JournalLine` trong `bctc.py` "
        f"(`loan_bank_detail_341`). Đang thấy {len(ca)} chỗ: {ca}")
    vay = inspect.getsource(BCTC.loan_bank_detail_341)
    assert "select(JournalLine," in vay, (
        "Ngoại lệ duy nhất phải nằm ở `loan_bank_detail_341`. Nếu nó đã được sửa rồi thì sửa luôn "
        "phép thử này cho khớp — đừng để một ngoại lệ ghi sẵn che một chỗ hỏng mới.")
    assert "account_code.in_(loan_codes)" in vay, (
        "`loan_bank_detail_341` chỉ được phép chọn cả đối tượng VÌ nó đã lọc theo tài khoản vay. "
        "Bỏ cái lọc ấy là nó đọc cả sổ, đúng chỗ hỏng Đợt E18 vừa sửa.")
