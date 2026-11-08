# -*- coding: utf-8 -*-
"""Đợt R4c-4 02/11/2026 — VÁ NỐT HAI CHỖ GHI VÀO TÀI KHOẢN TIỀN CẤP CHA.

Chủ tịch chốt 02/11/2026 sau khi em báo lại một câu em đã nói SAI.

Em bảo Đợt R4c-3 đã chữa chỗ ghi vào tài khoản cha. Đúng, nhưng nó mới là **1 trong 3 chỗ**. Quét
cả kho thì có đúng ba chỗ GHI:

    ops.py:676          `_post_payment`            đề nghị chi → đã chi     ĐỢT R4c-3 đã chữa
    accounting.py:292   `on_receipt_confirmed`     MỌI phiếu thu của khách  đợt này
    finance.py:87–91    năm dòng khế ước           trả gốc/lãi, vay, …      đợt này

Chỗ thứ hai nặng nhất vì nó là đường tiền vào đông nhất hệ thống. Chạy thật `ngoai_luat` với hai
bút toán chỉ khác vế tiền: `112/131` NGOÀI LUẬT, `1121/131` trong luật.

VÀ MỘT RANH GIỚI CỦA ĐỢT NÀY, luật 4 canh nó: những chỗ ĐỌC ở cấp cha (`reports.CASH`,
`dashboard`, hai phép cộng số dư trong `finance`, `books.CASH_ACCOUNT/BANK_ACCOUNT`,
`banks.BANK_ROOT`) PHẢI GIỮ NGUYÊN. Đọc ở cấp cha là ĐÚNG — số dư tiền gộp cả tài khoản con. Chỉ
chỗ GHI mới phải xuống cấp chi tiết. Một bản vá "thay hết 112 thành 1121" sẽ làm sai mọi báo cáo
số dư tiền, và nó sẽ sai im lặng.
"""
import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.accounting import JournalEntry, JournalLine
from app.models.core import Booking, Tour, User
from app.models.hach_toan import HTTT_QUA_TIEN_MAT
from app.models.payments import Receipt
from app.services import accounting as ACC
from app.services import cap_dinh_khoan as CD
from app.services import hach_toan as HT

GOC = Path(__file__).resolve().parents[2]
BE = GOC / "backend" / "app"
TRANG = GOC / "web" / "app" / "collections" / "page.tsx"


def _bo_chu_py(s: str) -> str:
    """Bỏ lời chú thích trước khi đo. Bản vá này NÓI VỀ các con số cũ trong chú thích, nên một
    phép đo soi cả chú thích sẽ thấy `"112"` và báo đỏ dù việc đã làm xong. Va phải ba lần
    01/11/2026."""
    return "\n".join(d for d in s.splitlines() if not d.strip().startswith("#"))


def _bo_chu_tsx(s: str) -> str:
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    return "\n".join(d for d in s.splitlines() if not d.strip().startswith("//"))


def _rieng():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    HT.nap_mac_dinh(db)
    return db


def _booking(db, ma="BK-R4C4"):
    u = User(username="sale.r4c4", full_name="Sale", role="kd", password_hash="x")
    db.add(u)
    db.commit()
    t = Tour(code="TR-R4C4", name="Tour R4c-4", tour_type="trong_nuoc",
             start_date=date(2026, 10, 1), end_date=date(2026, 10, 3), operator_id=u.id)
    db.add(t)
    db.commit()
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.username,
                customer_name="Khách R4c-4", customer_phone="0900000000", source="web")
    db.add(b)
    db.commit()
    return b


def _phieu_thu(db, b, method, ma):
    r = Receipt(code=ma, booking_id=b.id, amount=1_000_000.0, method=method,
                payer="Khách R4c-4", status="ke_toan_xac_nhan",
                created_by="ketoan", confirmed_by="ketoan", confirmed_at=datetime(2026, 10, 5))
    db.add(r)
    db.commit()
    ACC.on_receipt_confirmed(db, r, "ketoan", "ketoan")
    db.commit()
    return r


# ───────────────────────────────────────────────────────────────────── LUẬT 1
def test_r4c4_1_phieu_thu_ghi_ve_tien_o_cap_chi_tiet():
    """ĐỌC SỔ, KHÔNG ĐỌC MÃ. Lập phiếu thu thật rồi xem `journal_lines` ghi vào đâu."""
    db = _rieng()
    b = _booking(db)
    _phieu_thu(db, b, "tien_mat", "PT-R4C4-TM")
    _phieu_thu(db, b, "chuyen_khoan", "PT-R4C4-CK")

    tk = [l.account_code for l in db.execute(
        select(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.source_type == "thu_tien")).scalars()]

    assert "1111" in tk, f"phiếu thu tiền mặt KHÔNG ghi 1111: {tk}"
    assert "1121" in tk, f"phiếu thu chuyển khoản KHÔNG ghi 1121: {tk}"
    assert "111" not in tk and "112" not in tk, f"sổ còn ghi vào tài khoản CHA: {tk}"


# ───────────────────────────────────────────────────────────────────── LUẬT 2
def test_r4c4_2_duong_thu_tien_khong_con_ngoai_luat():
    """Rổ "định khoản ngoài luật" phải RỖNG cho đường thu tiền — đo thật, không soi chữ.

    Đây là cái rổ Kế toán trưởng mở ra để tìm bút toán sai. Một rổ mà mọi khoản thu đều rơi vào
    thì nó không còn chỉ ra chỗ phải nhìn nữa.
    """
    db = _rieng()
    b = _booking(db)
    _phieu_thu(db, b, "chuyen_khoan", "PT-R4C4-NL")

    kq = CD.ngoai_luat(db, date(2026, 12, 31))
    cap = [(c["tk_no"], c["tk_co"]) for c in kq["cap_ngoai_luat"]]
    assert ("112", "131") not in cap, "cặp 112/131 vẫn còn — vế tiền chưa xuống cấp chi tiết"
    assert kq["so_cap_ngoai_luat"] == 0, f"còn cặp ngoài luật: {cap}"


# ───────────────────────────────────────────────────────────────────── LUẬT 3
def test_r4c4_3_nam_dong_khe_uoc_ghi_1121():
    """Năm dòng khế ước đọc MỘT hằng số, không gõ cứng năm lần.

    Và luật này dựng đúng năm bộ dòng ấy rồi ghi sổ thật, để chứng rằng cặp sinh ra nằm trong
    bảng quy ước — chứ không chỉ chứng rằng chuỗi `"1121"` có mặt trong tệp.
    """
    from app.services import finance as FIN

    than = _bo_chu_py((BE / "services" / "finance.py").read_text(encoding="utf-8"))
    assert '{"account": "112", "credit": amt}' not in than, "khế ước còn ghi vào tài khoản cha"
    assert '{"account": "112", "debit": amt}' not in than, "khế ước còn ghi vào tài khoản cha"
    assert than.count("TK_TIEN_GUI_CT") >= 6, "năm dòng chưa đọc chung một hằng số"
    assert FIN.TK_TIEN_GUI_CT == "1121"

    # Hai phép cộng số dư ở cấp CHA phải CÒN — xem đầu tệp.
    # KS-TC (#729, 08/11/2026): phép thứ hai — số dư đầu kỳ của dự báo 13 tuần — nay đọc QUA bộ
    # nhớ số dư của bảng điều hành (`dashboard._so_du_no_vay_phai_thu`), nơi vẫn cộng đúng
    # ("111", "112") ở cấp cha. Đếm cả hai nơi: tổng vẫn phải là hai phép cộng cấp cha.
    than_db = _bo_chu_py((BE / "services" / "dashboard.py").read_text(encoding="utf-8"))
    assert than.count('("111", "112")') == 1, \
        "đã đụng vào phép ĐỌC số dư tiền ở cấp cha — đọc cấp cha là ĐÚNG"
    assert 'for c in ("111", "112"))' in than_db and "_so_du_no_vay_phai_thu(db" in than, \
        "số dư đầu kỳ dự báo phải đọc qua phép cộng cấp cha của bảng điều hành"

    # Và hằng số ấy phải là một tài khoản CHI TIẾT CÓ THẬT trong danh mục. Đo cái này chứ không
    # chỉ đo chuỗi: một lần gõ nhầm `"1120"` vẫn qua được mọi phép soi chữ ở trên, rồi `post_entry`
    # mới nổ lúc chạy thật — và nó nổ ở tay Kế toán, không ở đây.
    from app.models.accounting import Account

    db = _rieng()
    tk = db.execute(select(Account).where(Account.code == FIN.TK_TIEN_GUI_CT)).scalar_one_or_none()
    assert tk is not None, f"{FIN.TK_TIEN_GUI_CT} không có trong danh mục tài khoản"
    assert getattr(tk, "is_detail", False), \
        f"{FIN.TK_TIEN_GUI_CT} là tài khoản CHA — đúng cái lỗi đợt này đang vá"


# ───────────────────────────────────────────────────────────────────── LUẬT 4
def test_r4c4_4_khong_dung_mot_cho_doc_nao_o_cap_cha():
    """RANH GIỚI CỦA ĐỢT: chỉ chỗ GHI xuống cấp chi tiết; chỗ ĐỌC giữ nguyên cấp cha.

    Đọc ở cấp cha là ĐÚNG — số dư tiền gộp cả tài khoản con. Một bản vá "thay hết 112 thành 1121"
    sẽ làm sai mọi báo cáo số dư tiền, và nó sẽ sai IM LẶNG. Nên luật này đòi từng chỗ đọc CÒN
    NGUYÊN, và đòi đúng cái nó phải đòi.
    """
    from app.services import reports as RP
    from app.services import books as BK
    from app.services import banks as BN

    assert RP.CASH == ("111", "112"), "đã đụng reports.CASH — đây là chỗ ĐỌC"
    assert (BK.CASH_ACCOUNT, BK.BANK_ACCOUNT) == ("111", "112"), "đã đụng books — chỗ ĐỌC"
    assert BN.BANK_ROOT == "112", "đã đụng banks.BANK_ROOT — chỗ ĐỌC"

    dash = _bo_chu_py((BE / "services" / "dashboard.py").read_text(encoding="utf-8"))
    assert '("111", "112")' in dash, "đã đụng phép cộng tiền của dashboard — chỗ ĐỌC"

    # Và danh mục tài khoản vẫn khai đủ cả cha lẫn con.
    acc = (BE / "services" / "accounting.py").read_text(encoding="utf-8")
    assert '("111", "Tiền mặt", "TS", "")' in acc, "mất dòng khai tài khoản cha 111"


# ───────────────────────────────────────────────────────────────────── LUẬT 5
def test_r4c4_5_cua_lap_phieu_thu_nhan_hai_vai_va_cua_xac_nhan_KHONG_doi():
    """Cửa nói đúng như menu — và KHÔNG nói hơn.

    `access.MAN_HINH_THU_QUY` mở `/collections` cho `thu_quy` kèm chú thích ghi rõ "phiếu thu tiền
    mặt" là cửa của thủ quỹ. Đợt này làm cửa khớp bảng menu ĐÃ KÝ, không nới một quyền mới.

    Nhưng cùng lời chú thích ấy cũng nhắc "xác nhận phiếu thu". Mở CẢ lập lẫn xác nhận cho một vai
    là bỏ tách nhiệm — một quyết định phải có chữ ký riêng. Luật này canh đúng ranh giới ấy theo
    HAI chiều: cửa lập mở cho hai vai, cửa xác nhận KHÔNG đổi.
    """
    api = _bo_chu_py((BE / "api" / "v1" / "payments.py").read_text(encoding="utf-8"))

    i = api.index("def cash_receipt")
    dong_lap = api[api.rindex("\n", 0, i):api.index("\n", i)]
    assert 'require_roles("ketoan", "thu_quy")' in dong_lap, \
        "cửa lập phiếu thu tiền mặt chưa nhận vai thủ quỹ"

    j = api.index("def confirm_receipt")
    dong_xn = api[api.rindex("\n", 0, j):api.index("\n", j)]
    assert 'require_roles("ketoan",)' in dong_xn, \
        "đợt này ĐÃ ĐỤNG cửa xác nhận phiếu thu — chưa có chữ ký cho việc đó"

    # Và menu phải thật sự đang cấp màn hình ấy cho thủ quỹ — nếu không thì đợt này nới quyền thật.
    from app.services import access as AC
    assert "/collections" in AC.MAN_HINH_THU_QUY, \
        "menu KHÔNG cấp /collections cho thủ quỹ — vậy đây là nới quyền, phải có chữ ký"


# ───────────────────────────────────────────────────────────────────── LUẬT 6
def test_r4c4_6_man_hinh_va_may_chu_noi_cung_mot_cau():
    """Màn hình hiện khối lập phiếu cho đúng bộ vai máy chủ nhận, và đọc từ MỘT hằng số."""
    than = _bo_chu_tsx(TRANG.read_text(encoding="utf-8"))

    assert 'user?.role === "ketoan" && <><h2>Lập phiếu thu tiền mặt' not in than, \
        "màn hình còn chỉ hiện cho kế toán"
    assert "VAI_LAP_PHIEU_THU" in than, "màn hình chưa đọc bộ vai từ một hằng số"
    assert re.search(r'VAI_LAP_PHIEU_THU\s*=\s*\[\s*"ketoan"\s*,\s*"thu_quy"\s*\]', than), \
        "hằng số vai không đúng hai vai máy chủ nhận"
    # Gõ rời hai chỗ thì sửa một bên quên bên kia, và lúc ấy nút hiện ra để bấm vào nhận 403.
    assert than.count('"thu_quy"') == 1, "vai thủ quỹ bị gõ nhiều chỗ trên màn hình"


# ───────────────────────────────────────────────────────────────────── LUẬT 7
def test_r4c4_7_phep_thu_cu_doi_con_so_chu_khong_bo_phep_do():
    """Đợt này SỬA một phép thử đang xanh — và nói ra.

    `test_accounting.py::test_cash_receipt_posts_111_131` ghim `("111", 1000000, 0)`; tên hàm nói
    thẳng ra nó ghim con số nào. Ý định gốc của nó là "phiếu thu sinh một bút toán Nợ tiền – Có
    131", và CẤP của vế tiền đúng là thứ đợt này đổi. Nên em đổi đúng con số ấy và đổi tên hàm
    cho khớp, chứ KHÔNG bỏ phép đo nào — đếm trên main trước khi vá: 25.
    """
    t = (GOC / "backend" / "tests" / "test_accounting.py").read_text(encoding="utf-8")
    assert '("1111", 1000000, 0) in d' in t, "phép thử cũ chưa đổi sang cấp chi tiết"
    assert '("111", 1000000, 0) in d' not in t, "phép thử cũ còn ghim tài khoản cha"
    assert "def test_cash_receipt_posts_1111_131" in t, "tên hàm còn nói con số cũ"
    assert t.count("assert ") >= 25, \
        f"test_accounting.py còn {t.count('assert ')} phép đo — đợt này đã BỎ phép đo của tệp cũ"
