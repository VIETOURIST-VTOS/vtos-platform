# -*- coding: utf-8 -*-
"""Đợt TGIA-1 08/11/2026 — TÁCH CHÊNH LỆCH TỶ GIÁ VỀ TÀI KHOẢN CHI TIẾT.

Đo trên hệ thống THẬT 08/11/2026, đọc cửa `GET /ket-so/tach-ty-gia/xem-truoc` ba kỳ:

    2026-06 / 2026-10 / 2026-11  →  da_bat = true, tu_ngay = 2026-10-09, tách được 0 dòng

Tức máy tách ĐÃ BẬT nhưng chưa dòng ngoại tệ nào phát sinh sau mốc — chưa bút toán nào rơi vào
tài khoản cha. Đây là lúc RẺ NHẤT để nắn, đúng lập luận Đợt DL-7: siết khi con số còn bằng 0.

BỐN HẰNG SỐ của `chenh_lech_ty_gia` đều là TÀI KHOẢN TỔNG HỢP trong danh mục thật:
`413` (con 4131) · `632` (bảy con) · `635` (ba con) · `515` (bốn con).

Hai vế lỗ/lãi có con TRÙNG TÊN nên không phải hỏi ai: `6352` Lỗ tỷ giá, `5154` Lãi tỷ giá.
Vế giá vốn đi MỘT DÒNG `6326` cho cả kỳ (Chủ tịch chốt 08/11/2026) — giữ đúng quyết định đã ghi
sẵn trong `ket_so`: bút toán này là phân loại lại CẢ KỲ, «không thuộc riêng chuyến nào».

BỐN LUẬT:
  1. Bốn khóa mới nằm trong BẢNG CŨ, không khóa nào trỏ vào cha, và `ty_gia_gia_von` khai lý do.
  2. Bút toán tách ĐI VÀO tài khoản chi tiết — đo bằng dòng sổ ghi ra, không đọc mã.
  3. Thẻ in ra tài khoản chi tiết, và bốn hằng số GỐC vẫn còn cho phép đọc cây.
  4. Đợt này không đổi một con số tiền nào: lỗ, lãi và tổng tách y nguyên.
"""
import inspect
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tgia1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tgia1.db"):
    os.remove("test_tgia1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOI = ("ty_gia_lo", "ty_gia_lai", "ty_gia_gia_von", "ty_gia_danh_gia_lai")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _khong_cm(x) -> str:
    src = x if isinstance(x, str) else inspect.getsource(x)
    return "\n".join(d.split("#")[0] for d in src.split("\n"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tgia1_1_bon_khoa_moi_trong_BANG_CU_va_khai_du_ly_do():
    """Thêm vào bảng cũ, không mở bảng thứ hai — và hỏi DANH MỤC THẬT.

    `ty_gia_gia_von` trỏ vào `6326`, nằm dưới `632` tức trong nhóm BẮT BUỘC mã công trình. Nó
    chỉ an toàn vì nguồn `ket_chuyen` được `account_rule_check` miễn — và điều đó phải được
    KHAI RA ở `CAN_CONG_TRINH`, không phải nhớ trong đầu ai.
    """
    from app.services import rules as R
    from app.services import tk_chi_tiet as TK
    from app.services.accounting import NEED_PROJECT

    assert inspect.getsource(TK).count("KHOA: dict") == 1, "có bảng khai thứ hai"
    co = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    with _db() as db:
        for khoa in MOI:
            assert khoa in TK.KHOA, "chưa khai `" + khoa + "`"
            mac_dinh = TK.KHOA[khoa][0]
            assert TK.KEY(khoa) in co and co[TK.KEY(khoa)] == mac_dinh, (
                "hai nguồn đã lệch ở `" + khoa + "`")
            loi = TK.kiem(db, mac_dinh)
            assert not loi, khoa + " = " + mac_dinh + " → " + loi

        assert TK.chon(db, "ty_gia_lo") == "6352"
        assert TK.chon(db, "ty_gia_lai") == "5154"
        assert TK.chon(db, "ty_gia_gia_von") == "6326"
        assert TK.chon(db, "ty_gia_danh_gia_lai") == "4131"

    assert TK.KHOA["ty_gia_gia_von"][0].startswith(NEED_PROJECT), (
        "cảnh đo đã đổi — `6326` không còn nằm trong nhóm bắt buộc mã công trình, nên dòng dưới "
        "không còn đo gì; đọc lại trước khi sửa")
    assert "ty_gia_gia_von" in TK.CAN_CONG_TRINH, (
        "`ty_gia_gia_von` trỏ vào tài khoản BẮT BUỘC mã công trình mà chưa khai lý do")
    assert "ket_chuyen" in TK.CAN_CONG_TRINH["ty_gia_gia_von"], (
        "lý do phải nói đúng nguồn được miễn: " + TK.CAN_CONG_TRINH["ty_gia_gia_von"])


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tgia1_2_but_toan_tach_DI_VAO_tai_khoan_chi_tiet():
    """Khai đúng trong bảng mà bút toán vẫn ghi vào cha thì bằng không khai.

    Đo bằng DÒNG SỔ ghi ra: dựng hai dòng ngoại tệ lệch tỷ giá, chạy thật cửa tách, rồi đọc
    `account_code` của từng dòng.
    """
    from sqlalchemy import select
    from app.models.accounting import Account
    from app.services import chenh_lech_ty_gia as CL
    from app.services import tk_chi_tiet as TK

    with _db() as db:
        cha = {a.parent for a in db.execute(select(Account)).scalars() if a.parent}
        # DỰNG CẢNH, không bỏ qua. Sổ thật hôm nay chưa có dòng ngoại tệ nào sau mốc (đo
        # 08/11/2026: tách được 0 dòng ở cả ba kỳ), và bộ dữ liệu mẫu cũng vậy — nên nếu chỉ
        # đọc rồi `skip` thì luật này không đo gì cả. Dựng đúng một dòng lệch tỷ giá: sổ ghi
        # một giá, dòng doanh thu dùng một giá khác.
        from app.models.lop3_tour import TourDoanhThuDong
        from app.models.ty_gia import TyGia
        from app.models.core import Tour
        ngay = date(2026, 10, 20)       # sau mốc 2026-10-09
        t = db.execute(select(Tour)).scalars().first()
        assert t is not None, "bộ dữ liệu mẫu không có chuyến nào — DỪNG LẠI"
        db.add(TyGia(tien_te="USD", ngay=ngay, ty_gia=25_000, nguon="test"))
        db.add(TourDoanhThuDong(tour_id=t.id, noi_dung="Dòng phép thử TGIA-1",
                                tien_te="USD", ty_gia=25_400, ngay_ty_gia=ngay,
                                so_tien_goc=1_000, so_luong=1))
        db.flush()
        bt = CL.tinh_tach(db, "2026-10")["but_toan"]
        assert bt, "dựng cảnh rồi mà vẫn không ra bút toán nào — DỪNG LẠI, mô hình đã đổi"
        tks = [l["account"] for l in bt]
        assert tks, "bút toán không có dòng nào"
        assert not (set(tks) & cha), "còn dòng vào tài khoản cha: " + repr(sorted(set(tks) & cha))
        for x in ("635", "515", "632", "413"):
            assert x not in tks, "còn ghi vào `" + x + "` — tài khoản cha"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tgia1_3_the_in_tai_khoan_chi_tiet_va_GOC_doc_cay_van_con():
    """Hai chiều, và chiều thứ hai mới là chiều dễ mất.

    Bốn hằng số `TK_*` còn dùng làm GỐC và làm nhãn của bộ dò; bỏ chúng đi là mất phép đọc cây.
    Chỉ số hiệu đem GHI SỔ và đem IN mới đổi — đúng cách Đợt TKC-4 giữ `TK_CHI_PHI_DO_DANG`.
    """
    from app.services import chenh_lech_ty_gia as CL

    with _db() as db:
        tk = CL.tong_hop(db)["tai_khoan"]
        assert tk == {"danh_gia_lai": "4131", "lo": "6352", "lai": "5154"}, (
            "thẻ còn in tài khoản tổng hợp: " + repr(tk))

    ma = _khong_cm(CL)
    # Không còn GHI / IN bằng hằng số cấp cha…
    for x in ("TK_LO_TY_GIA", "TK_LAI_TY_GIA", "TK_GIA_VON", "TK_CHENH_LECH_DANH_GIA_LAI"):
        assert ('"account": ' + x) not in ma, "còn ghi sổ bằng hằng số cấp cha `" + x + "`"
    assert '"lo": TK_LO_TY_GIA' not in ma and '"lai": TK_LAI_TY_GIA' not in ma, (
        "thẻ còn in bằng hằng số cấp cha")
    # …nhưng bốn hằng số PHẢI CÒN, và còn mang đúng gốc cha.
    for x, goc in (("TK_CHENH_LECH_DANH_GIA_LAI", "413"), ("TK_GIA_VON", "632"),
                   ("TK_LO_TY_GIA", "635"), ("TK_LAI_TY_GIA", "515")):
        assert (x + ' = "' + goc + '"') in ma, (
            "đã bỏ mất hằng số gốc `" + x + "` — nó còn dùng làm gốc đọc cây và làm nhãn bộ dò")
    assert "def _tk(" in ma and "tk_chi_tiet import chon" in ma, (
        "tệp này không đọc bảng khai chung — gõ cứng số hiệu ở đây là dựng nguồn thứ hai")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tgia1_4_KHONG_doi_mot_con_so_tien_nao():
    """Đợt này nắn SỐ HIỆU TÀI KHOẢN, không đụng phép tính.

    Lỗ, lãi, số dòng tách được và tổng hai vế phải y nguyên — và hai vế của bút toán vẫn cân.
    Một đợt «chỉ đổi tài khoản» mà làm dịch một đồng là đợt đã làm hai việc.
    """
    from app.services import chenh_lech_ty_gia as CL
    with _db() as db:
        for ky in ("2026-06", "2026-10", "2026-11"):
            kq = CL.tinh_tach(db, ky)
            lo, lai = kq["lo"], kq["lai"]
            assert kq["rong"] == round(lo - lai), "ròng không bằng lỗ trừ lãi ở kỳ " + ky
            no = sum(l.get("debit", 0) for l in kq["but_toan"])
            co = sum(l.get("credit", 0) for l in kq["but_toan"])
            assert round(no - co) == 0, "bút toán kỳ " + ky + " không cân: Nợ " + str(no) + " / Có " + str(co)
            assert round(no) == round(lo + lai), (
                "tổng vế Nợ phải bằng lỗ cộng lãi ở kỳ " + ky)

    # Và phép tính KHÔNG đọc bảng khai — bảng khai chỉ nói ghi vào đâu, không nói bao nhiêu.
    ma_tinh = _khong_cm(CL.tinh_tach)
    i = ma_tinh.find('"but_toan"')
    truoc = ma_tinh[:i] if i > 0 else ma_tinh
    assert "_tk(" not in truoc, (
        "phép TÍNH đã đọc bảng khai — bảng ấy chỉ được nói ghi vào đâu, không được nói bao nhiêu")
