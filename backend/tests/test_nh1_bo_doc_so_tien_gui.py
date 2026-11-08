# -*- coding: utf-8 -*-
"""Đợt NH-1 09/11/2026 — BỘ ĐỌC SỔ TIỀN GỬI PHẢI HỎI TÊN CỘT, KHÔNG ĐẾM CỘT.

Đo trên hệ thống THẬT 08/11/2026, sau khi nạp bản đồ chứng từ hai năm 2025–2026:

    bản đồ 29.609 dòng · 29.114 chứng từ chỉ thuộc một ngân hàng
    gán được 10/27 dòng còn nằm trên `1121` — và CẢ MƯỜI khớp bằng lớp
    «số chứng từ chỉ thuộc 1 ngân hàng», KHÔNG MỘT DÒNG NÀO khớp bằng lớp có số tiền

Lớp có số tiền im lặng không khớp được gì, vì MỌI số tiền trong bản đồ là MÃ TÀI KHOẢN:
chứng từ `FT26167686276948` được ghi là («chi», 3388.0), `FT26105764354821` là («chi», 1121.0).

Nguyên nhân: cùng một báo cáo, MISA in ra hai bố cục. Bản gọn 8 cột để Thu ở cột F (số 5),
Chi ở cột G (số 6). Bản in đầy đủ 13 cột — có tiêu đề chi nhánh, «Mẫu số: S08-DN», ô gộp —
để Thu ở cột I (số 8), Chi ở cột K (số 10). Bộ đọc cũ gõ cứng `row[5]` / `row[6]`, nên với
bố cục 13 cột nó đọc đúng cột TK ĐỐI ỨNG.

Hỏng kiểu này không báo lỗi bao giờ. Sổ vẫn đúng vì lớp dưới gánh thay — nhưng 434 chứng từ
chuyển tiền nội bộ có mặt ở HAI ngân hàng thì vĩnh viễn không phân giải được, vì chỉ lớp có
số tiền mới tách nổi chúng.

Lỗi thứ hai, cùng bản chất «tin vào hình dạng»: `MISA-FT26167686276948-0617` không khớp được
dòng nào, vì trong sổ MISA chứng từ ấy tên là `FT26167686276948` — hậu tố `-0617` do VTOS gắn.
Nhưng cắt bừa là hỏng to: trong chính sổ ấy có 7.860 chứng từ mang hậu tố `-NNNN` THẬT.

BỐN LUẬT:
  1. Ba cột tìm theo TÊN — đo bằng hai bố cục thật, số tiền phải ra TIỀN.
  2. Hậu tố chỉ cắt cho mã gốc DÀI; 7.860 chứng từ gốc ngắn không được đụng tới.
  3. Dạng đầy đủ luôn thắng dạng rút gọn, và khớp rút gọn phải KHAI RA.
  4. Đợt này không ghi một dòng sổ nào.
"""
import io
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_nh1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_nh1.db"):
    os.remove("test_nh1.db")

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.services import banks as BA


@pytest.fixture(scope="module", autouse=True)
def _startup():
    """Dựng kho dữ liệu mẫu — luật 4 cần sổ thật để đếm trước/sau."""
    with TestClient(app):
        yield


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "SỔ TIỀN GỬI NGÂN HÀNG"
    for r in rows:
        ws.append(list(r))
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _bo_cuc_gon(dong):
    """Bản gọn 8 cột — y bố cục MISA xuất cho ba tệp tháng 01, 03, 06/2026.

    Ngày HT · Ngày CT · Số chứng từ · Diễn giải · TK đối ứng · Thu · Chi · Tồn
    """
    r = [("SỔ TIỀN GỬI NGÂN HÀNG",),
         ("Tài khoản: 1121, Loại tiền: VND",),
         (),
         ("Ngày hạch toán", "Ngày chứng từ", "Số chứng từ", "Diễn giải", "TK đối ứng",
          "Thu", "Chi", "Tồn")]
    for nh, doc, tkdu, thu, chi in dong:
        r.append(("Tài khoản ngân hàng: " + nh,))
        r.append(("01/01/2026", "01/01/2026", doc, "noi dung", tkdu, thu, chi, 0))
    return _xlsx(r)


def _bo_cuc_day_du(dong):
    """Bản in đầy đủ 13 cột — y bố cục MISA xuất cho tệp hai năm 2025–2026.

    Cột TK đối ứng ở số 6, Thu ở số 8, Chi ở số 10. Chính cột số 6 là chỗ bản cũ đọc nhầm
    thành «Chi»: đó là lý do mọi số tiền trong bản đồ thật hoá ra là mã tài khoản.
    """
    O = None
    r = [("CHI NHÁNH PHAN THIẾT - CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS", O, O, O, O, O, O,
          "Mẫu số: S08-DN"),
         (O,) * 8,
         ("Số 22 Nguyễn Đình Chiểu",),
         (O,) * 8,
         ("Mã số thuế: 0311273634-016",),
         ("SỔ TIỀN GỬI NGÂN HÀNG",),
         ("Tài khoản: 1121, Loại tiền: VND",),
         (O,) * 8,
         ("Ngày hạch toán", "Ngày chứng từ", "Số chứng từ", "Diễn giải", O, O,
          "TK đối ứng", O, "Thu", O, "Chi", "Tồn", O)]
    for nh, doc, tkdu, thu, chi in dong:
        r.append(("Tài khoản ngân hàng: " + nh,))
        r.append(("01/01/2026", "01/01/2026", doc, "noi dung", O, O, tkdu, O, thu, O, chi, 0, O))
    return _xlsx(r)


# Một cảnh dùng chung cho cả hai bố cục. `tkdu` cố tình là 3388 / 1121 — đúng hai con số mà
# bản cũ nhặt nhầm thành tiền trên sổ thật, nên nếu ai gõ cứng lại số cột thì luật 1 đỏ ngay.
CANH = [
    ("01811267101 - Ngân hàng TMCP Tiên Phong", "TPB1-01358", "3388", 1290000, 0),
    ("1601100633008 - Ngân hàng TMCP Quân đội", "FT26167686276948", "1121", 0, 1350000),
]


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
@pytest.mark.parametrize("dung", [_bo_cuc_gon, _bo_cuc_day_du])
def test_nh1_1_ba_cot_tim_theo_TEN_tren_ca_hai_bo_cuc(dung):
    """Cùng một cảnh, hai bố cục, phải ra CÙNG một kết quả — và số tiền phải là TIỀN.

    Đây là phép đo HÀNH VI chứ không phải đo hình: nó không hỏi mã có chữ `tim_cot` hay không,
    nó đọc hai tệp khác bố cục rồi so số tiền lấy ra được.
    """
    kq = BA.parse_bank_book(dung(CANH))

    assert set(kq["accounts"]) == {"01811267101", "1601100633008"}, (
        "không tách đúng hai ngân hàng: " + repr(sorted(kq["accounts"])))

    ra = {(e["doc_no"], e["side"]): e["amount"] for e in kq["entries"]}
    assert ra == {("TPB1-01358", "thu"): 1290000.0,
                  ("FT26167686276948", "chi"): 1350000.0}, (
        "số tiền đọc ra không đúng — nếu thấy 3388 hay 1121 thì bộ đọc đang nhặt cột TK ĐỐI "
        "ỨNG làm tiền, đúng lỗi Đợt NH-1 bịt: " + repr(ra))

    # Và không có dòng nào mang số tiền BẰNG một mã tài khoản trong cảnh — cách nói khác của
    # cùng một điều, nhưng nói thẳng vào triệu chứng đã thấy trên sổ thật.
    assert not [e for e in kq["entries"] if e["amount"] in (3388.0, 1121.0)], (
        "còn dòng mang số tiền là mã tài khoản")


def test_nh1_1b_thieu_ten_cot_thi_DUNG_LAI_chu_khong_doan():
    """Không đủ ba tên cột thì từ chối, và câu từ chối phải gọi tên thứ đang thiếu."""
    xau = _xlsx([("SỔ TIỀN GỬI NGÂN HÀNG",),
                 ("Ngày hạch toán", "Ngày chứng từ", "Diễn giải", "TK đối ứng", "Tồn"),
                 ("Tài khoản ngân hàng: 01811267101 - Tiên Phong",)])
    with pytest.raises(ValueError) as e:
        BA.parse_bank_book(xau)
    assert "Số chứng từ" in str(e.value) and "Thu" in str(e.value) and "Chi" in str(e.value), (
        "câu từ chối không nói rõ thiếu cột nào: " + str(e.value))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_nh1_2_hau_to_chi_cat_cho_MA_GOC_DAI():
    """7.860 chứng từ gốc ngắn không được đụng tới.

    Đo trên sổ thật 08/11/2026 (29.549 chứng từ của hai năm): mọi chứng từ mang hậu tố `-NNNN`
    THẬT đều có phần gốc dài 2–6 ký tự. Mã bị VTOS gắn thêm hậu tố thì gốc dài 16. Luật này
    canh đúng khoảng giữa ấy.
    """
    # Gốc NGẮN — hậu tố là của chính MISA, không được cắt.
    for ma in ("MISA-PT08-1063", "MISA-PC07-1705", "MISA-TPB1-0115", "MISA-UNC-0001"):
        dang = BA._doc_thu(ma)
        assert len(dang) == 1, ma + ": đã cắt hậu tố THẬT của MISA — " + repr(dang)
        assert dang[0][1] is False

    # Gốc DÀI — hậu tố do VTOS gắn, được phép thử thêm bản cắt, nhưng SAU bản đầy đủ.
    dang = BA._doc_thu("MISA-FT26167686276948-0617")
    assert dang == [("FT26167686276948-0617", False), ("FT26167686276948", True)], repr(dang)

    # Ngưỡng phải nằm GIỮA hai nhóm đo được, không dính mép nào.
    assert 6 < BA.GOC_TOI_THIEU < 16, (
        "ngưỡng cắt hậu tố ra ngoài khoảng đo được (gốc thật dài tối đa 6, gốc cần cắt dài 16): "
        + str(BA.GOC_TOI_THIEU))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_nh1_3_day_du_thang_rut_gon_va_rut_gon_phai_KHAI_RA():
    """Nới lỏng thì được, nhưng phải nói ra — và không bao giờ được chen lên trước.

    Dựng cảnh có CẢ HAI: một ngân hàng mang đúng mã đầy đủ, một ngân hàng khác mang mã đã cắt
    hậu tố. Nếu dạng rút gọn chen lên trước thì dòng sổ về nhầm ngân hàng mà không ai biết.
    """
    class _NH:
        def __init__(self, code):
            self.code, self.parent_account = code, "1121"
            self.match_prefixes, self.match_keywords = [], []

    A, B = _NH("11111111111"), _NH("22222222222")
    day_du, rut_gon = "FT26167686276948-0617", "FT26167686276948"

    # (a) Có cả hai → bản ĐẦY ĐỦ thắng, và lý do KHÔNG nói rút gọn.
    exact = {(day_du, 1350000.0, "chi"): A.code, (rut_gon, 1350000.0, "chi"): B.code}
    nh, ly_do = BA._match([A, B], "MISA-" + day_du, "", "1121", 1350000.0, "chi", exact, {})
    assert nh is A, "dạng rút gọn đã chen lên trước dạng đầy đủ"
    assert "rút gọn" not in ly_do, "khớp đầy đủ mà lại khai là rút gọn: " + ly_do

    # (b) Chỉ có bản rút gọn → vẫn khớp, nhưng PHẢI khai ra.
    nh, ly_do = BA._match([A, B], "MISA-" + day_du, "", "1121", 1350000.0, "chi",
                          {(rut_gon, 1350000.0, "chi"): B.code}, {})
    assert nh is B, "không khớp được bằng mã rút gọn — đúng dòng Đợt NH-1 phải cứu"
    assert "rút gọn" in ly_do, (
        "khớp bằng một phép NỚI LỎNG mà lý do không khai ra, người đọc sổ không biết: " + ly_do)

    # (c) Mã gốc NGẮN thì không có bản rút gọn nào để mà khớp.
    nh, _ = BA._match([A, B], "MISA-PT08-1063", "", "1121", 1290000.0, "thu",
                      {("PT08", 1290000.0, "thu"): B.code}, {})
    assert nh is None, "đã cắt hậu tố thật của MISA rồi khớp bừa sang ngân hàng khác"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_nh1_4_KHONG_ghi_mot_dong_so_nao():
    """Đợt này sửa cách ĐỌC, không đụng sổ.

    Nạp một quyển sổ tiền gửi thật qua đúng hàm nạp, rồi đếm lại dòng sổ và số dư cây `112`.
    """
    from sqlalchemy import func, select
    from app.db.session import SessionLocal
    from app.models.accounting import JournalLine
    from app.models.core import User

    def _do(db):
        n = db.execute(select(func.count()).select_from(JournalLine)).scalar() or 0
        du = db.execute(
            select(func.coalesce(func.sum(JournalLine.debit), 0)
                   - func.coalesce(func.sum(JournalLine.credit), 0))
            .where(JournalLine.account_code.like("112%"))).scalar() or 0
        return n, round(float(du))

    with SessionLocal() as db:
        u = db.execute(select(User)).scalars().first()
        assert u is not None, "bộ dữ liệu mẫu không có người dùng nào — DỪNG LẠI"
        truoc = _do(db)
        kq = BA.import_bank_book(db, u, _bo_cuc_day_du(CANH), "nh1.xlsx")
        db.commit()
        assert kq, "nạp không trả về kết quả nào"
        sau = _do(db)

    assert sau == truoc, (
        "nạp bản đồ mà sổ đổi — trước " + repr(truoc) + ", sau " + repr(sau))
