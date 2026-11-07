# -*- coding: utf-8 -*-
"""Đợt TKC-4 07/11/2026 — NHỊP 2b: BỐN ĐƯỜNG GHI TIẾP THEO VỀ TÀI KHOẢN CHI TIẾT.

Đợt TKC-3 (PR #720) dựng bảng khai chung `services/tk_chi_tiet.py` và nắn ba đường. Đợt này nắn
BỐN đường nữa, qua CÙNG bảng ấy — không mở bảng thứ hai, không gõ cứng số hiệu nào:

  hóa đơn · lương · vay · kết chuyển chi phí đội xe (627 → 154 → 632)

Ba trong bốn đường chọn tài khoản con TỪ DỮ LIỆU đã có, không hỏi ai:
  · doanh thu hóa đơn theo LOẠI TOUR của chuyến; hóa đơn không gắn chuyến ra «dịch vụ khác»
  · nợ gốc vay theo KỲ HẠN của khế ước (`maturity`) — phép phân loại của TT200
  · giá vốn quyết toán theo loại tour (đã làm ở TKC-3)

BỐN LUẬT:
  1. Bảng khai lớn thêm mà vẫn MỘT nguồn, và không khóa mới nào trỏ vào tài khoản CHA.
  2. Hóa đơn: doanh thu theo loại tour, và hóa đơn KHÔNG gắn chuyến KHÔNG rơi vào doanh thu tour.
  3. Vay: nợ gốc theo kỳ hạn, đo ở cả hai phía mốc 12 tháng và ở khế ước thiếu ngày đáo hạn.
  4. Bốn đường ĐI VÀO bút toán thật — đo bằng `account_code`, không đọc mã.
"""
import inspect
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_tkc4.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tkc4.db"):
    os.remove("test_tkc4.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOI = ("hd_doanh_thu_noi_dia", "hd_doanh_thu_nuoc_ngoai", "hd_doanh_thu_thue_xe",
       "hd_doanh_thu_khong_tour", "hd_gtgt_dau_ra", "luong_chi_phi_quan_ly",
       "luong_phai_tra_nld", "luong_ctv_gia_von", "luong_ctv_phai_tra",
       "vay_goc_ngan_han", "vay_goc_dai_han", "vay_lai", "kc_627_gia_von")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _khong_cm(ham) -> str:
    """Thân hàm đã BỎ chú thích `#` — bẫy đã mất hai lần (Đợt TZ-1, Đợt CPTT-1)."""
    return "\n".join(d.split("#")[0] for d in inspect.getsource(ham).split("\n"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tkc4_1_bang_khai_lon_them_ma_van_MOT_nguon_va_khong_khoa_nao_vao_CHA():
    """Đợt này thêm 13 khóa. Thêm vào BẢNG CŨ, không mở bảng thứ hai.

    Và không khóa mới nào được trỏ vào một tài khoản tổng hợp — hỏi DANH MỤC THẬT, không đoán
    theo độ dài mã: `1121` bốn chữ số mà là cha, `627` ba chữ số mà là chi tiết.
    """
    from app.services import rules as R
    from app.services import tk_chi_tiet as TK

    thieu = [k for k in MOI if k not in TK.KHOA]
    assert not thieu, "chưa khai trong bảng: " + repr(thieu)

    co = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    with _db() as db:
        xau = []
        for khoa in MOI:
            mac_dinh = TK.KHOA[khoa][0]
            assert TK.KEY(khoa) in co, (
                "khóa `" + khoa + "` không có dòng tham số — Kế toán trưởng không có chỗ để đổi")
            assert co[TK.KEY(khoa)] == mac_dinh, "hai nguồn đã lệch ở `" + khoa + "`"
            loi = TK.kiem(db, mac_dinh)
            if loi:
                xau.append(khoa + " = " + mac_dinh + " → " + loi)
        assert not xau, "khóa khai sai:\n  " + "\n  ".join(xau)

    # Mỗi loại tour ra một tài khoản DOANH THU chi tiết — kể cả loại lạ.
    with _db() as db:
        from app.models.core import Tour
        for loai in list(TK.DOANH_THU_THEO_LOAI) + ["", "loai_moi_chua_khai"]:
            tk = TK.doanh_thu_hoa_don(db, Tour(tour_type=loai))
            assert not TK.kiem(db, tk), "loại tour " + repr(loai) + " ra tài khoản " + tk


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tkc4_2_hoa_don_khong_gan_chuyen_KHONG_roi_vao_doanh_thu_tour():
    """Chỗ dễ hỏng nhất của đợt này, và nó hỏng im lặng.

    Lấy mặc định là «doanh thu tour nội địa» cho một hóa đơn không biết thuộc đâu thì sổ vẫn
    cân, tổng doanh thu vẫn đúng, chỉ có doanh thu theo DÒNG SẢN PHẨM sai — và cái sai ấy chỉ
    lộ ra lúc ai đó hỏi «tour nội địa năm nay bán được bao nhiêu», tức là rất muộn.
    """
    from app.models.core import Tour
    from app.services import tk_chi_tiet as TK
    with _db() as db:
        nd = TK.doanh_thu_hoa_don(db, Tour(tour_type="doan_noi_dia"))
        nn = TK.doanh_thu_hoa_don(db, Tour(tour_type="doan_nuoc_ngoai"))
        xe = TK.doanh_thu_hoa_don(db, Tour(tour_type="thue_xe"))
        khong = TK.doanh_thu_hoa_don(db, None)
        assert nd == "51131" and nn == "51137" and xe == "51133", (nd, nn, xe)
        assert khong == "51136", "hóa đơn không gắn chuyến ra " + khong
        assert khong != nd, (
            "hóa đơn KHÔNG gắn chuyến nào lại rơi vào doanh thu tour nội địa — cộng thêm vào "
            "doanh thu tour một khoản không phải của nó")

    # Và cửa phát hành hóa đơn phải ĐỌC hàm ấy, không tự chọn lấy.
    from app.services import accounting as ACC
    ma = _khong_cm(ACC.on_invoice_issued)
    assert "TKCT.doanh_thu_hoa_don(db, _t)" in ma, "cửa phát hành hóa đơn không đọc bảng khai"
    assert '"511"' not in ma and '"3331"' not in ma, "còn gõ cứng tài khoản cha trong hóa đơn"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tkc4_3_no_goc_vay_theo_KY_HAN_cua_khe_uoc():
    """`341` → `3411` → `34111` / `34112` / `34113`: HAI TẦNG, và tầng dưới là phép phân loại kỳ hạn.

    Đo ở CẢ HAI phía mốc 12 tháng và ở khế ước thiếu ngày đáo hạn. Đo một phía thì một hàm trả
    về hằng số vẫn xanh.
    """
    from app.models.finance import FinContract
    from app.services import tk_chi_tiet as TK
    hom_nay = date(2026, 11, 7)
    with _db() as db:
        gan = FinContract(maturity=hom_nay + timedelta(days=200))
        xa = FinContract(maturity=hom_nay + timedelta(days=400))
        sat_moc = FinContract(maturity=hom_nay + timedelta(days=365))
        trong = FinContract(maturity=None)
        assert TK.vay_goc(db, gan, hom_nay) == "34111", "đáo hạn trong 12 tháng phải là ngắn hạn"
        assert TK.vay_goc(db, xa, hom_nay) == "34112", "đáo hạn sau 12 tháng phải là dài hạn"
        assert TK.vay_goc(db, sat_moc, hom_nay) == "34111", "đúng 365 ngày vẫn là NGẮN hạn"
        assert TK.vay_goc(db, trong, hom_nay) == "34111", (
            "khế ước thiếu ngày đáo hạn phải về ngắn hạn — phía thận trọng khi đọc khả năng "
            "thanh toán")
        # `34113` là tài khoản của bước PHÂN LOẠI LẠI khi lập báo cáo, không phải chỗ ghi một
        # lần trả gốc vào. Không đường nào của hàm này được ra nó.
        for c in (gan, xa, sat_moc, trong):
            assert TK.vay_goc(db, c, hom_nay) != "34113"

    from app.services import finance as FN
    ma = _khong_cm(FN.settle)
    assert "TKCT.vay_goc(db, c)" in ma, "cửa khế ước không đọc bảng khai"
    assert '"341"' not in ma and '"635"' not in ma, "còn gõ cứng `341` / `635` ở khế ước"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tkc4_4_bon_duong_DI_VAO_but_toan_that():
    """Khai đúng trong bảng mà bút toán vẫn ghi vào cha thì bằng không khai.

    Đo bằng `account_code` của từng dòng sổ ghi ra. Lương đo bằng bút toán THẬT; hóa đơn, vay và
    kết chuyển đội xe đo trên mã đã bỏ chú thích vì dựng đủ bối cảnh cho chúng là dựng lại nửa
    bộ dữ liệu mẫu — và cả ba chỗ đo HAI CHIỀU (không còn số hiệu cha, VÀ có đọc bảng khai),
    đúng chỗ phép đo ngược của Đợt TKC-3 đã bắt được một luật nói nhiều hơn nó đo.
    """
    from sqlalchemy import select
    from app.models.accounting import Account, JournalEntry, JournalLine
    from app.services import tk_chi_tiet as TK

    with _db() as db:
        cha = {a.parent for a in db.execute(select(Account)).scalars() if a.parent}

        # ── đường LƯƠNG: chạy thật rồi đọc bút toán ghi ra.
        from app.models.hr import PayrollRun
        from app.services import hr as HR
        run = db.execute(select(PayrollRun)).scalars().first() or HR.get_or_draft(db, "2026-10")
        db.flush()
        ids = HR.post_payroll_entries(db, run)
        db.flush()
        # Kỳ lương mẫu có thể không phát sinh đồng nào — khi ấy không có bút toán để đọc, và
        # phép đo rơi về đọc MÃ ở ngay dưới. Nói ra chứ không lặng lẽ xanh.
        if ids:
            tks = [l.account_code for e in db.execute(
                       select(JournalEntry).where(JournalEntry.id.in_(ids))).scalars()
                   for l in db.execute(select(JournalLine).where(
                       JournalLine.entry_id == e.id)).scalars()]
            assert tks, "bút toán lương không có dòng nào"
            assert not (set(tks) & cha), "bút toán lương còn dòng vào tài khoản cha: " + repr(
                sorted(set(tks) & cha))

        # Dù kỳ lương có phát sinh hay không, MÃ phải đã nắn.
        ma_luong = "\n".join(d.split("#")[0] for d in inspect.getsource(HR).split("\n"))
        for x in ('{"account": "642"', '{"account": "334"', '{"account": "632"',
                  '{"account": "338"'):
            assert x not in ma_luong, "bảng lương còn gõ cứng " + x
        assert "TKCT.chon(db, \"luong_chi_phi_quan_ly\")" in ma_luong, (
            "bảng lương không đọc bảng khai")

        # ── đường KẾT CHUYỂN chi phí đội xe (627 → 154 → 632)
        from app.services import ket_so as KS
        ma_kc = "\n".join(d.split("#")[0] for d in inspect.getsource(KS).split("\n"))
        assert '"ve_tk": "154"' not in ma_kc, "bước kết chuyển 627 còn gõ cứng `154`"
        assert '"ve_khoa": "qt_do_dang"' in ma_kc, "bước kết chuyển 627 không đọc bảng khai"
        assert 'TKCT.chon(db, "kc_627_gia_von")' in ma_kc, (
            "chặng 154 → 632 không đọc bảng khai — `632` là tài khoản cha")
        assert '{"account": TK_GIA_VON' not in ma_kc and '{"account": TK_CHI_PHI_DO_DANG' not in ma_kc, (
            "còn GHI vào hằng số cấp cha")
        # Nhưng hai hằng số ấy PHẢI CÒN, vì phép ĐỌC CÂY cần gốc cha.
        assert "account_code.startswith(TK_CHI_PHI_DO_DANG)" in ma_kc, (
            "đã bỏ mất phép đọc cây theo gốc `154` — số dư dở dang sẽ chỉ đếm một tài khoản con")

        # ── và không khóa nào của bảng khai ra một tài khoản cha.
        for khoa in TK.KHOA:
            assert TK.chon(db, khoa) not in cha, khoa + " ra tài khoản cha"
