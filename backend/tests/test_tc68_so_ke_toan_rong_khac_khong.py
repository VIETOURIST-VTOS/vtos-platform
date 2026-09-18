# -*- coding: utf-8 -*-
"""TC-68 · SỐ KẾ TOÁN: RỖNG KHÁC KHÔNG, VÀ KẾT CHUYỂN KHÔNG PHẢI DOANH THU.

Anh Tuấn 18/9/2026: *"lợi nhuận trước thuế em lấy theo số đang có trên VTOS để viết hoàn thành
code cấu trúc, thuật toán và form nhập; số chính xác sẽ sửa bổ sung sau"*, và duyệt cả hai việc
sau khi xem số đo.

══════════════════════════════════════════════════════════════════════════════════════════════
HAI CHỖ HỎNG, ĐO ĐƯỢC TRÊN SỔ THẬT NGÀY 18/9/2026
══════════════════════════════════════════════════════════════════════════════════════════════

1 · RỖNG ĐỌC THÀNH 0.  Kỳ 2026-07, 2026-08, 2026-09 có ĐÚNG 0 chứng từ đã ghi sổ. `movements()`
    trả về dict rỗng, mọi phép cộng ra 0,0, và `xu_huong` gọi `float(...)` lên con số ấy. Màn
    hình Chủ tịch in ra "0" — tức nói rằng công ty hoà vốn ba tháng liền.

    Đây là luật xương sống của kho ("rỗng khác không") bị lọt ở đúng một dòng.

2 · KẾT CHUYỂN BỊ CỘNG VÀO DOANH THU.  Kỳ 2026-06 của cả tập đoàn:

        doanh thu (dòng 01) = −45.216.354.515      giá vốn (dòng 11) = −36.373.329.530

    Doanh thu ÂM. Bút toán kết chuyển cuối kỳ ghi Nợ 511 đúng bằng cả kỳ doanh thu và triệt tiêu
    nó. Con số ấy đã nằm trên màn hình Chủ tịch dưới nhãn "Doanh thu".

    VÀ LUẬT LOẠI KẾT CHUYỂN ĐÃ CÓ SẴN TRONG KHO: `services/bctc.py` (`_lines(exclude_closing)`)
    loại đúng hai điều kiện — chạm 911, hoặc `source_type == "ket_chuyen"`. Báo cáo BCTC TT99 đọc
    đúng; `income_statement` mà màn hình Chủ tịch đang đọc thì không. Hai công thức cho cùng một
    câu hỏi, và chúng đã lệch nhau thật.

══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ NGUY HIỂM NHẤT CỦA VÒNG NÀY, và vì sao có hẳn một phép thử riêng canh nó
══════════════════════════════════════════════════════════════════════════════════════════════
Loại kết chuyển là ĐÚNG cho báo cáo kết quả kinh doanh và SAI cho bảng cân đối kế toán. Chính bút
toán kết chuyển đưa lãi về 421 và làm bảng cân; loại nó khỏi số dư là bảng cân đối lệch đúng bằng
lợi nhuận cả kỳ — và bảng vẫn hiện ra bình thường, không lỗi nào báo.

Nên `bo_ket_chuyen` mặc định TẮT, chỉ `income_statement` bật. `test_bang_can_doi_khong_duoc_doi`
canh đúng chỗ ấy.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.core import Company
from app.services import reports as RP

GOC = Path(__file__).resolve().parent.parent
BAO_CAO = GOC / "app" / "services" / "reports.py"
XU_HUONG = GOC / "app" / "services" / "xu_huong.py"
KQKD = GOC / "app" / "services" / "ket_qua_kinh_doanh.py"
KHOI = GOC.parent / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _ma_py(src: str) -> str:
    """Bỏ chuỗi tài liệu và chú thích — phép thử phải canh MÃ CHẠY, không canh lời hứa trong chú thích."""
    src = re.sub(r'""".*?"""', "", src, flags=re.S)
    return re.sub(r"(?m)^\s*#.*$", "", src)


def _db():
    """Kho rỗng trong bộ nhớ, dựng đúng những bảng khai được — cùng cách với TC-44/45/46/47."""
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _so_gia():
    """Một cuốn sổ nhỏ, dựng ĐÚNG ba tình huống mà sổ thật đang có.

    2026-05  doanh thu thường, KHÔNG có kết chuyển  → mốc so sánh
    2026-06  doanh thu thường CỘNG một bút toán kết chuyển → chỗ hỏng số 2
    2026-07  không một chứng từ nào                 → chỗ hỏng số 1
    """
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    db.add(me); db.commit()
    for ma, ten, loai in (("511", "Doanh thu bán hàng", "DT"), ("632", "Giá vốn hàng bán", "CP"),
                          ("131", "Phải thu khách hàng", "TS"), ("911", "Xác định kết quả", "XD")):
        db.add(Account(code=ma, name=ten, kind=loai))
    db.commit()

    n = [0]

    def but_toan(ky, ngay, mo_ta, cac_dong, nguon="thu_cong"):
        n[0] += 1
        e = JournalEntry(code=f"CT{n[0]:04d}", entry_date=ngay, period=ky, description=mo_ta,
                         source_type=nguon, status="da_ghi_so", company_id=me.id)
        db.add(e); db.flush()
        for tk, no, co in cac_dong:
            db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co))
        db.commit()

    # Tháng 5: bán 100, giá vốn 60. Không kết chuyển.
    but_toan("2026-05", dt.date(2026, 5, 10), "Bán tour", [("131", 100.0, None), ("511", None, 100.0)])
    but_toan("2026-05", dt.date(2026, 5, 11), "Ghi giá vốn", [("632", 60.0, None), ("131", None, 60.0)])

    # Tháng 6: bán 200, giá vốn 120, RỒI kết chuyển cả hai sang 911 — đúng cái làm doanh thu âm.
    but_toan("2026-06", dt.date(2026, 6, 10), "Bán tour", [("131", 200.0, None), ("511", None, 200.0)])
    but_toan("2026-06", dt.date(2026, 6, 11), "Ghi giá vốn", [("632", 120.0, None), ("131", None, 120.0)])
    but_toan("2026-06", dt.date(2026, 6, 30), "Kết chuyển doanh thu sang 911",
             [("511", 200.0, None), ("911", None, 200.0)], nguon="ket_chuyen")
    but_toan("2026-06", dt.date(2026, 6, 30), "Kết chuyển giá vốn sang 911",
             [("911", 120.0, None), ("632", None, 120.0)], nguon="ket_chuyen")

    # Tháng 7: KHÔNG ghi gì cả.
    return db, me


# ═════════════════ 1 · KẾT CHUYỂN KHÔNG PHẢI DOANH THU ═════════════════

def test_ket_chuyen_khong_lam_doanh_thu_am():
    """Chỗ hỏng số 2. Tháng 6 bán 200 thì doanh thu phải là 200, không phải 0 cũng không phải âm."""
    db, me = _so_gia()
    pl = RP.income_statement(db, "2026-06", company_id=me.id)
    m = {r[0]: r[2] for r in pl["rows"]}
    assert m["01"] == 200.0, (
        f"doanh thu tháng 6 ra {m['01']} — bút toán kết chuyển đang bị cộng vào phát sinh. "
        "Đây đúng là chỗ làm sổ thật ra −45,2 tỷ ngày 18/9/2026.")
    assert m["11"] == 120.0, f"giá vốn tháng 6 ra {m['11']}, phải là 120"
    assert m["50"] == 80.0, f"lợi nhuận trước thuế tháng 6 ra {m['50']}, phải là 200 − 120 = 80"


def test_ban_doi_chung_luat_cu_that_su_lam_am():
    """BẢN ĐỐI CHỨNG — chạy luật CŨ trên cùng cuốn sổ để chứng minh chỗ hỏng có thật.

    Không có phép thử này thì phép thử trên chỉ nói "hôm nay đúng", chứ không nói "trước đây sai".
    Và một vòng sửa mà không chứng minh được cái nó sửa thì vòng sau sẽ có người lặng lẽ bỏ đi.
    """
    db, me = _so_gia()
    cu = RP.movements(db, "2026-06", company_id=me.id, bo_ket_chuyen=False)
    dt_cu = cu.get("511", {}).get("credit", 0.0) - cu.get("511", {}).get("debit", 0.0)
    assert dt_cu == 0.0, (
        "Luật cũ phải cho ra doanh thu bị kết chuyển triệt tiêu — nếu không thì cuốn sổ giả này "
        "chưa dựng đúng tình huống của sổ thật.")
    moi = RP.movements(db, "2026-06", company_id=me.id, bo_ket_chuyen=True)
    dt_moi = moi.get("511", {}).get("credit", 0.0) - moi.get("511", {}).get("debit", 0.0)
    assert dt_moi == 200.0 and dt_moi != dt_cu, "luật mới phải cho ra số khác luật cũ"


def test_loai_ca_chung_tu_chu_khong_chi_loai_dong_911():
    """Bút toán kết chuyển có hai vế: Nợ 511 và Có 911. Bỏ mỗi vế 911 thì vế phá số vẫn ở lại.

    Phép thử này canh chính chỗ dễ sửa sai nhất: viết `account_code != '911'` trông rất hợp lý,
    chạy qua được phép thử tổng, mà doanh thu vẫn âm.
    """
    db, me = _so_gia()
    m = RP.movements(db, "2026-06", company_id=me.id, bo_ket_chuyen=True)
    assert "911" not in m, "tài khoản 911 không được còn phát sinh nào sau khi loại"
    assert m["511"]["debit"] == 0.0, (
        "vế Nợ 511 của bút toán kết chuyển vẫn còn — mới chỉ loại dòng 911, chưa loại cả chứng từ")


def test_bat_duoc_ca_ket_chuyen_lap_tay_khong_gan_nguon():
    """Chứng từ kết chuyển lập tay, `source_type` để mặc định, chỉ nhận ra được nhờ tài khoản 911.

    Đây là loại nguy hiểm nhất: không ai gắn nhãn, nên không đếm được, và nếu chỉ lọc theo
    `source_type` thì nó lọt hoàn toàn.
    """
    db, me = _so_gia()
    e = JournalEntry(code="CTTAY", entry_date=dt.date(2026, 5, 31), period="2026-05",
                     description="Ket chuyen lap tay", source_type="thu_cong",
                     status="da_ghi_so", company_id=me.id)
    db.add(e); db.flush()
    db.add(JournalLine(entry_id=e.id, account_code="511", debit=100.0, credit=None))
    db.add(JournalLine(entry_id=e.id, account_code="911", debit=None, credit=100.0))
    db.commit()
    pl = RP.income_statement(db, "2026-05", company_id=me.id)
    m = {r[0]: r[2] for r in pl["rows"]}
    assert m["01"] == 100.0, (
        f"doanh thu tháng 5 ra {m['01']} — chứng từ kết chuyển lập tay đang lọt vì chỉ lọc theo "
        "source_type. Phải bắt cả bằng điều kiện chạm tài khoản 911.")


# ═════════════════ 2 · RỖNG KHÁC KHÔNG ═════════════════

def test_ky_chua_ai_ghi_so_thi_khong_phai_hoa_von():
    """Chỗ hỏng số 1. Tháng 7 chưa ai ghi gì — không được nói là kết quả bằng 0."""
    db, me = _so_gia()
    pl = RP.income_statement(db, "2026-07", company_id=me.id)
    assert pl["co_but_toan"] is False, (
        "Kỳ không có chứng từ nào phải nói ra là chưa có số. Không có trường này thì mọi nơi đọc "
        "dòng '50' đều thấy 0,0 và không cách nào biết đó là hoà vốn hay là chưa ai ghi sổ.")
    assert RP.so_but_toan(db, "2026-07", company_id=me.id) == 0


def test_ky_da_co_so_thi_bao_la_da_co():
    db, me = _so_gia()
    assert RP.income_statement(db, "2026-05", company_id=me.id)["co_but_toan"] is True
    assert RP.so_but_toan(db, "2026-05", company_id=me.id) == 2


def test_ky_chi_co_moi_but_toan_ket_chuyen_van_la_da_ghi_so():
    """Một kỳ chỉ có bút toán kết chuyển: phát sinh bằng 0 THẬT, nhưng đã có người ghi sổ.

    Hai điều ấy khác nhau, và trường `co_but_toan` phải nói đúng điều thứ hai. Đếm SAU khi loại
    kết chuyển thì kỳ này bị báo nhầm là "chưa ai ghi", rồi màn hình giục Kế toán đi nhập một
    tháng mà họ đã làm xong.
    """
    db, me = _so_gia()
    e = JournalEntry(code="CTKC", entry_date=dt.date(2026, 8, 31), period="2026-08",
                     description="Ket chuyen", source_type="ket_chuyen",
                     status="da_ghi_so", company_id=me.id)
    db.add(e); db.flush()
    db.add(JournalLine(entry_id=e.id, account_code="511", debit=10.0, credit=None))
    db.add(JournalLine(entry_id=e.id, account_code="911", debit=None, credit=10.0))
    db.commit()
    pl = RP.income_statement(db, "2026-08", company_id=me.id)
    assert pl["co_but_toan"] is True, "kỳ đã có người ghi sổ thì không được báo là chưa có số"
    assert {r[0]: r[2] for r in pl["rows"]}["01"] == 0.0, "phát sinh sau khi loại kết chuyển là 0 thật"


def test_xu_huong_tra_o_trong_chu_khong_tra_so_khong():
    """Vế màn hình của chỗ hỏng số 1: `xu_huong` phải hỏi `co_but_toan` TRƯỚC khi float(...)."""
    ma = _ma_py(_doc(XU_HUONG))
    # Neo vào ĐÚNG chỗ ĐỌC, không phải chỗ khai chỉ tiêu ở đầu tệp — `ln_ke_toan_thang` xuất hiện
    # ở cả hai nơi, và neo nhầm thì phép thử soi một đoạn mã không liên quan gì.
    i = ma.find('if ma == "ln_ke_toan_thang"')
    assert i > 0, "không tìm thấy chỗ đọc lợi nhuận trước thuế trong xu_huong"
    doan = ma[i:i + 900]
    assert 'co_but_toan' in doan, (
        "Chỗ đọc lợi nhuận trước thuế phải hỏi kỳ đã có bút toán chưa. Không hỏi thì một kỳ rỗng "
        "ra float(0) và màn hình in ra số 0 như một kết quả kinh doanh.")
    assert doan.index("co_but_toan") < doan.index('["50"]'), (
        "phải hỏi TRƯỚC khi đọc dòng 50, không phải sau")


# ═════════════════ 3 · CHỖ NGUY HIỂM: BẢNG CÂN ĐỐI KHÔNG ĐƯỢC ĐỔI ═════════════════

def test_bang_can_doi_khong_duoc_doi():
    """Loại kết chuyển khỏi SỐ DƯ là làm bảng cân đối lệch đúng bằng lợi nhuận cả kỳ.

    Chính bút toán kết chuyển đưa lãi về 911/421; bỏ nó khỏi số dư thì bảng không cân nữa — và
    bảng vẫn hiện ra bình thường, không lỗi nào báo. Đây là chỗ hỏng đắt nhất mà vòng này có thể
    gây ra, nên nó có phép thử riêng.
    """
    db, me = _so_gia()
    b = RP.balances(db, "2026-06")
    assert b.get("911") == -80.0, (
        f"số dư 911 ra {b.get('911')} — bảng cân đối phải GIỮ bút toán kết chuyển. "
        "Nếu 911 biến mất thì `balances` đã bật nhầm cờ loại kết chuyển.")


def test_mac_dinh_phai_la_khong_loai():
    """Cờ mới phải mặc định TẮT: hàm này còn phục vụ số dư, lưu chuyển tiền và báo cáo hợp nhất."""
    ma = _ma_py(_doc(BAO_CAO))
    assert "bo_ket_chuyen: bool = False" in ma, (
        "Mặc định bật là đổi ngầm số của những báo cáo không ai yêu cầu đổi.")
    assert "bo_ket_chuyen=True" in ma, "income_statement phải là nơi DUY NHẤT bật cờ này"
    assert ma.count("bo_ket_chuyen=True") == 1, (
        f"có {ma.count('bo_ket_chuyen=True')} chỗ bật cờ — chỉ được một chỗ, ở income_statement")


# ═════════════════ 4 · KHÔNG ĐẺ THÊM LƯỢT TRUY VẤN (bài học TC-64b) ═════════════════

def test_dem_nhieu_ky_bang_mot_luot_truy_van():
    """Hỏi mười hai tháng bằng mười hai lượt là đi lùi đúng cái vòng TC-64b vừa sửa."""
    db, me = _so_gia()
    d = RP.so_but_toan_nhieu_ky(db, ["2026-05", "2026-06", "2026-07"], company_id=me.id)
    assert d.get("2026-05") == 2 and d.get("2026-06") == 4
    assert "2026-07" not in d, "kỳ không có dòng nào thì vắng mặt, bên gọi dùng .get(ky, 0)"

    ma = _ma_py(_doc(KQKD))
    assert "so_but_toan_nhieu_ky" in ma, (
        "Khối Kết quả kinh doanh phải hỏi cả kỳ bằng MỘT lượt, không gọi so_but_toan từng tháng.")


def test_khong_dem_them_khi_ky_da_co_phat_sinh():
    """Kỳ đang có số thì KHÔNG được tốn thêm một lượt đếm — `bool(m)` phải đứng trước."""
    ma = _ma_py(_doc(BAO_CAO))
    i = ma.find('"co_but_toan"')
    assert i > 0, "thiếu trường co_but_toan"
    dong = ma[i:i + 160]
    assert dong.index("bool(m)") < dong.index("so_but_toan("), (
        "Phải kiểm `bool(m)` trước: kỳ có phát sinh thì chắc chắn đã có bút toán, hỏi thêm cơ sở "
        "dữ liệu một lượt nữa là thừa. Đây là hầu hết các kỳ.")


# ═════════════════ 5 · MÀN HÌNH NÓI RA, VÀ CHỈ ĐƯỜNG ═════════════════

def test_khoi_noi_ro_thang_nao_thieu_va_chi_duong_toi_cua():
    """Ranh giới 09/9: mỗi con số phải có một cửa nhập. Cửa đã có sẵn — thiếu là đường dẫn tới nó."""
    ma = _doc(KHOI)
    assert "thang_chua_ghi_so" in ma, "Khối phải đọc danh sách tháng chưa ghi sổ."
    assert "/accounting" in ma, (
        "Phải có lối tắt sang cửa ghi sổ. Một ô trống không kèm đường đi thì người đọc chỉ biết là "
        "thiếu, không biết thiếu ở đâu mà bù.")
    assert "KHÔNG phải bằng 0" in ma, (
        "Phải nói thẳng ô trống khác số 0 — đó là cả nội dung của vòng này.")


def test_may_chu_noi_ten_thang_chu_khong_noi_so_luong():
    """"3 tháng chưa có số" không cho ai biết phải mở tháng nào ra nhập."""
    ma = _ma_py(_doc(KQKD))
    assert "def _thang_chua_ghi_so" in ma
    assert "return [t for t in cac_thang if not dem.get(t)]" in ma, (
        "Phải trả về danh sách TÊN THÁNG, không phải một con số đếm.")


def test_chua_biet_cong_ty_me_thi_khong_khang_dinh_gi():
    """Chưa xác định được công ty mẹ thì không nói 'cả ba tháng chưa ghi sổ' — ta không biết gì cả."""
    ma = _ma_py(_doc(KQKD))
    i = ma.find("def _thang_chua_ghi_so")
    doan = ma[i:i + 700]
    assert "if me is None" in doan and "return []" in doan, (
        "Chưa có công ty mẹ thì trả danh sách rỗng, không phải trả tất cả các tháng.")
