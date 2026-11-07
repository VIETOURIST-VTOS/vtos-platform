# -*- coding: utf-8 -*-
"""Đợt TKC-3 07/11/2026 — NHỊP 2a: NẮN ĐƯỜNG GHI VỀ TÀI KHOẢN CHI TIẾT.

Nhịp 1 (Đợt TKC-2, PR #716) đo trên sổ THẬT: 187 dòng đã ghi vào 13 tài khoản cha. Bảng «Theo
đường ghi» chỉ thấy MỘT đường (`de_nghi_chi`) — 13 đường còn lại chưa phát sinh, không phải đã
đúng. Đọc mã 07/11/2026 đếm được 14 chỗ gõ cứng tài khoản cha vào bút toán.

Chủ tịch chốt 07/11/2026: MỘT bảng khai chung (`services/tk_chi_tiet.py`), Kế toán trưởng ký một
lần trên màn Tham số, mã đọc bảng ấy — không sửa số cứng rải rác ở 14 tệp.

ĐỢT NÀY NẮN BA ĐƯỜNG: đề nghị chi, quyết toán tour, kết chuyển lãi/lỗ. Không bật chặn (nhịp 3),
không đụng bảng quyền, không mở cửa nào.

BỐN LUẬT:
  1. Bảng khai có MỘT nguồn: tham số sinh ra từ `KHOA`, không chép tay.
  2. Không khóa nào trỏ vào tài khoản CHA của danh mục thật.
  3. `chon` từ chối tài khoản cha KỂ CẢ khi tham số bị ký sai, và hai bảng loại chi phải khớp.
  4. Ba đường ghi đã nắn ĐI VÀO bút toán thật — đo bằng bút toán ghi ra, không đọc mã.
"""
import inspect
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_tkc3.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_tkc3.db"):
    os.remove("test_tkc3.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _ma_khong_chu_thich(ham) -> str:
    """Thân hàm đã BỎ chú thích `#`.

    Bẫy đã mất hai lần (Đợt TZ-1 06/11, Đợt CPTT-1 07/11): phép tự kiểm tìm thấy chuỗi mình
    đang cấm — ở ngay dòng chú thích giải thích vì sao nó bị cấm.
    """
    return "\n".join(d.split("#")[0] for d in inspect.getsource(ham).split("\n"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tkc3_1_bang_khai_co_MOT_nguon_tham_so_sinh_ra_tu_KHOA():
    """Chép mặc định sang `DEFAULT_PARAMS` bằng tay là dựng nguồn thứ hai, và nguồn thứ hai lệch.

    Đúng thứ đang hỏng ở `ops.CATEGORY_ACCOUNT` / `misa.CATEGORY_ACCOUNT` — xem luật 3.
    """
    from app.services import rules as R
    from app.services import tk_chi_tiet as TK
    assert TK.KHOA, "bảng khai rỗng"

    co = {k: (v, lbl) for k, v, lbl, *_ in R.DEFAULT_PARAMS}
    for khoa, (mac_dinh, _mo_ta) in TK.KHOA.items():
        k = TK.KEY(khoa)
        assert k in co, (
            "khóa `" + k + "` không có dòng nào trong DEFAULT_PARAMS — Kế toán trưởng không có "
            "chỗ nào để đổi, tức bảng khai không có cửa")
        assert co[k][0] == mac_dinh, (
            "mặc định của `" + k + "` trong DEFAULT_PARAMS là " + repr(co[k][0]) +
            " còn trong KHOA là " + repr(mac_dinh) + " — HAI NGUỒN ĐÃ LỆCH")

    # Và lệch được là vì ai đó CHÉP. Đo rằng rules.py SINH RA các dòng ấy.
    src = "\n".join(d.split("#")[0] for d in inspect.getsource(R).split("\n"))
    assert "tk_chi_tiet import tham_so_mac_dinh" in src and "DEFAULT_PARAMS +=" in src, (
        "`rules.DEFAULT_PARAMS` không NỐI từ `tk_chi_tiet.tham_so_mac_dinh()` — nếu các dòng tham "
        "số được gõ tay thì sớm muộn chúng lệch khỏi KHOA mà không ai thấy")

    # Mỗi khóa đúng MỘT dòng — hai dòng cùng khóa thì `seed_params` nạp dòng đầu, người sửa
    # dòng sau, và không ai hiểu vì sao sửa không ăn.
    keys = [k for k, *_ in R.DEFAULT_PARAMS if k.startswith("tk_")]
    assert len(keys) == len(set(keys)), "có khóa `tk_` khai trùng trong DEFAULT_PARAMS"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tkc3_2_khong_khoa_nao_tro_vao_tai_khoan_CHA():
    """Đây là chính việc của đợt. Một mặc định trỏ vào cha là đợt tự phá chính mình.

    Hỏi DANH MỤC THẬT trong cơ sở dữ liệu, không đoán theo độ dài mã: `1121` bốn chữ số mà vẫn
    là cha (20 tài khoản ngân hàng nằm dưới nó), còn `627` ba chữ số thì là tài khoản chi tiết.
    """
    from app.services import tk_chi_tiet as TK
    with _db() as db:
        xau = []
        for khoa, (mac_dinh, _) in TK.KHOA.items():
            loi = TK.kiem(db, mac_dinh)
            if loi:
                xau.append(khoa + " = " + mac_dinh + " → " + loi)
        assert not xau, "khóa khai sai:\n  " + "\n  ".join(xau)

        # Và mọi loại tour đều ra được một tài khoản giá vốn chi tiết — kể cả loại lạ.
        for loai in list(TK.GIA_VON_THEO_LOAI) + ["", "loai_la_hoac_moi"]:
            tk = TK.gia_von_tour(db, loai)
            assert not TK.kiem(db, tk), "loại tour " + repr(loai) + " ra tài khoản " + tk


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tkc3_3_chon_tu_choi_tai_khoan_cha_va_HAI_bang_loai_chi_phai_khop():
    """Hai điều, và điều thứ hai là lỗ đã đo được trên sổ thật.

    (a) Cửa Tham số không được thành đường vòng đi quanh luật đợt này: ký `tk_qt_gia_von_noi_dia
        = 632` là bút toán lại ghi vào cha, im lặng như cũ.
    (b) `ops.CATEGORY_ACCOUNT` (cấp cha) và `misa.CATEGORY_ACCOUNT` (cấp con) là HAI bảng cùng
        nói một luật và ĐÃ LỆCH: cùng một khoản chi nằm ở `154` trong sổ VTOS và `1541` trong
        bảng kê xuất sang MISA. Luật này buộc chúng khớp, và khớp qua `tk_chi_tiet`.
    """
    from app.models.core import Param
    from app.services import rules as R
    from app.services import tk_chi_tiet as TK
    from app.services import misa as MS
    from app.services import ops as OPS

    with _db() as db:
        # (a) ký một tham số SAI rồi đòi `chon` vẫn từ chối.
        db.add(Param(key=TK.KEY("qt_gia_von_noi_dia"), value="632", label="phép thử",
                     unit="", effective_from=date(2026, 11, 1), source="test",
                     status="active", signed_chutich=True, signed_tgd=True, proposed_by="test"))
        db.commit()
        R.clear_param_cache()
        try:
            with pytest.raises(ValueError) as ex:
                TK.chon(db, "qt_gia_von_noi_dia")
            assert "tổng hợp" in str(ex.value), (
                "từ chối rồi nhưng không nói rõ sai gì: " + str(ex.value))
        finally:
            for p in db.execute(
                    __import__("sqlalchemy").select(Param).where(
                        Param.key == TK.KEY("qt_gia_von_noi_dia"))).scalars():
                db.delete(p)
            db.commit()
            R.clear_param_cache()
        assert TK.chon(db, "qt_gia_von_noi_dia") == "6321", "bỏ tham số sai rồi phải về mặc định"

        # (b) hai bảng loại chi phải khớp — và `ops` phải trỏ sang bảng khai, không giữ số riêng.
        for loai, khoa in OPS.CATEGORY_TK_KHOA.items():
            assert khoa in TK.KHOA, "loại chi `" + loai + "` trỏ vào khóa lạ: " + repr(khoa)
            assert loai in MS.CATEGORY_ACCOUNT, (
                "loại chi `" + loai + "` ghi sổ được mà không có trong bảng kê MISA")
            assert TK.chon(db, khoa) == MS.CATEGORY_ACCOUNT[loai], (
                "loại chi `" + loai + "`: sổ VTOS ghi " + TK.chon(db, khoa) + " còn bảng kê MISA "
                "ghi " + MS.CATEGORY_ACCOUNT[loai] + " — HAI BẢNG LỆCH, đúng lỗ đợt này bịt")

    # Và `ops` không còn giữ một bảng số hiệu tài khoản của riêng nó.
    ma = _ma_khong_chu_thich(OPS._post_liability)
    assert "tk_chi_tiet" in ma or "TKCT" in ma, "`_post_liability` không đọc bảng khai chung"
    assert not any(('"' + x + '"') in ma for x in ("154", "641", "642")), (
        "`_post_liability` còn gõ cứng một tài khoản cha")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_tkc3_4_ba_duong_ghi_DI_VAO_but_toan_that():
    """Khai đúng trong bảng mà bút toán vẫn ghi vào cha thì bằng không khai.

    Đo bằng BÚT TOÁN GHI RA, không đọc mã: chạy thật ba đường rồi đọc `account_code` của từng
    dòng sổ, và đòi không dòng nào rơi vào một tài khoản cha.
    """
    from sqlalchemy import select
    from app.models.accounting import Account, JournalLine
    from app.services import tk_chi_tiet as TK

    with _db() as db:
        cha = {a.parent for a in db.execute(select(Account)).scalars() if a.parent}

        def _tk_cua(e):
            return [l.account_code for l in db.execute(
                select(JournalLine).where(JournalLine.entry_id == e.id)).scalars()]

        from app.models.core import Tour
        from sqlalchemy import select as _sel
        from app.models.core import User
        _u = db.execute(_sel(User)).scalars().first()
        t = Tour(code="TKC3TOUR", name="Chuyến phép thử TKC-3", tour_type="doan_nuoc_ngoai",
                 start_date=date(2026, 10, 1), end_date=date(2026, 10, 5),
                 operator_id=_u.id, actual_cost=7_000_000)
        db.add(t)
        db.flush()

        # ── đường 1: đề nghị chi đã duyệt → ghi công nợ
        #
        # Có `tour_id` là CỐ Ý, và nó nói ra một hệ quả thật của đợt này: `1541` khai chiều «mã
        # công trình» bắt buộc còn `154` thì không, nên một đề nghị chi `chi_tour` không gắn
        # chuyến nào nay bị `post_entry` từ chối thay vì ghi im lặng vào tài khoản cha. Đó là
        # siết đúng chỗ — chi phí tour không gắn chuyến thì không tính được lãi lỗ chuyến.
        from app.models.ops import PaymentRequest
        from app.services import ops as OPS
        r = PaymentRequest(code="TKC3-DC", category="chi_tour", supplier_name="NCC phép thử",
                           description="Phép thử Đợt TKC-3", amount=11_000_000, tour_id=t.id,
                           status="cho_chi", has_invoice=True, created_by="robot")
        db.add(r)
        db.flush()
        OPS._post_liability(db, r)
        db.flush()
        assert r.entry_ids, "đề nghị chi không ghi được bút toán nào"
        from app.models.accounting import JournalEntry
        tks = _tk_cua(db.get(JournalEntry, r.entry_ids[-1]))
        assert tks, "bút toán không có dòng nào"
        assert "154" not in tks, "đề nghị chi vẫn ghi vào `154` — tài khoản cha"
        assert TK.chon(db, "dn_chi_chi_tour") in tks, (
            "không thấy tài khoản chi tiết của bảng khai trong bút toán: " + repr(tks))
        assert not (set(tks) & cha), "bút toán đề nghị chi còn dòng vào tài khoản cha: " + repr(tks)

        # ── đường 2: quyết toán tour → hoàn ứng / trích trước / giá vốn
        from app.services import accounting as ACC
        es = ACC.on_settlement_confirmed(db, t, "robot", "robot")
        db.flush()
        assert es, "quyết toán không ghi được bút toán nào"
        moi = [tk for e in es for tk in _tk_cua(e)]
        assert "154" not in moi, "quyết toán vẫn ghi vào `154` — tài khoản cha"
        assert "632" not in moi, "quyết toán vẫn ghi vào `632` — tài khoản cha"
        # Chuyến NƯỚC NGOÀI phải vào giá vốn nước ngoài, không phải nội địa.
        assert TK.chon(db, "qt_gia_von_nuoc_ngoai") in moi, (
            "chuyến nước ngoài ghi giá vốn vào " + repr(moi) + " — giá vốn phải chọn theo loại tour")
        assert TK.chon(db, "qt_gia_von_noi_dia") not in moi, (
            "chuyến nước ngoài lại ghi vào giá vốn NỘI ĐỊA")

        # ── đường 3: kết chuyển lãi/lỗ → lợi nhuận sau thuế chưa phân phối
        #
        # Đo bằng MÃ chứ không bằng bút toán, và nói rõ vì sao: dựng được một kỳ có đủ doanh thu
        # lẫn chi phí để `closing_entries_draft` chạy đòi một chuyến thật, một bộ chứng từ thật
        # và một kỳ chưa kết chuyển — tức dựng lại nửa bộ dữ liệu mẫu chỉ để đọc một dòng. Nên
        # chỗ này đo HAI chiều trên mã đã bỏ chú thích: không còn MỘT số hiệu `421` nào gõ cứng,
        # VÀ có đọc bảng khai. Thiếu chiều thứ hai thì đổi `421` thành một hằng số khác vẫn xanh;
        # thiếu chiều thứ nhất thì gọi bảng khai rồi vẫn ghi `421` cũng xanh. Phép đo ngược
        # 07/11/2026 đã bắt được đúng chỗ này: bản đầu chỉ tìm `"account": "421"` nên sửa thành
        # `tk_ln = "421"` vẫn qua.
        from app.services import reports as RP
        from app.services import misa as MS
        for ten, ma in (("kết chuyển lãi/lỗ", _ma_khong_chu_thich(RP.closing_entries_draft)),
                        ("chốt sổ kiểm toán", _ma_khong_chu_thich(MS.import_audited_checkpoint))):
            assert '"421"' not in ma, ten + " còn gõ cứng `421` — tài khoản cha"
            assert '"kc_lai_lo"' in ma, ten + " không đọc bảng khai `tk_chi_tiet`"
        assert TK.chon(db, "kc_lai_lo") == "4212", "kết chuyển lãi/lỗ phải về `4212` (năm nay)"
