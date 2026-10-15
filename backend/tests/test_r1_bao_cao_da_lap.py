# -*- coding: utf-8 -*-
"""Đợt R1 (15/10/2026) — BẢN BÁO CÁO ĐÃ LẬP: SỐ ĐÓNG BĂNG, KHÔNG TÍNH LẠI THEO SỔ.

VÌ SAO CÓ TỆP NÀY

Trước đợt này màn hình BCTC của VTOS tính lại từ sổ MỖI LẦN MỞ. Con số của một kỳ đã qua vì thế
đổi theo sổ: ai ghi thêm một bút toán đề ngày cũ thì báo cáo kỳ ấy khác đi, và không còn bản nào
để đối chiếu.

ĐÃ ĐO ĐƯỢC NGÀY 15/10/2026 trên sổ thử, trước khi viết một dòng mã nào của đợt này: sau khi chốt
mốc kiểm toán 30/06/2026 (đáp án 10 tỷ), nạp thêm mốc 31/12/2025 thì chỉ tiêu 111 tại 30/06/2026
**tụt từ 10.000.000.000 xuống 9.500.000.000**. Cửa chốt sổ ghi bút toán theo CHÊNH LỆCH, nên bút
toán mới đề ngày 31/12/2025 chảy xuôi vào số dư của ngày sau. Không có bản đóng băng thì không ai
biết nó đã tụt.

TỆP NÀY CANH TÁM ĐIỀU

 1. LẬP ra đúng số mà `BCTC.bctc()` tính tại thời điểm ấy — không phải một phép tính thứ hai.
 2. **SỐ KHÔNG ĐỔI KHI SỔ ĐỔI.** Đây là điều đợt này sinh ra để làm, và là phép thử quan trọng
    nhất của tệp: ghi thêm một bút toán ĐỀ NGÀY CŨ, sổ đổi, bản KHÔNG đổi.
 3. Người lập hoặc người trình KHÔNG tự ký.
 4. Ký thì bản cũ cùng (loại, pháp nhân, kỳ) chuyển `da_thay_the` — **không xoá**.
 5. Trình mà chưa điền người đại diện thì chặn: đó là tên sẽ in dưới bộ báo cáo.
 6. Từ chối bắt buộc có lý do.
 7. **RỖNG ≠ BỘ BÁO CÁO TOÀN SỐ 0**: chưa có bản nào đã ký thì `ban_da_ky` trả `None`.
 8. Luật chữ ký khai ở `chu_ky.VAI_KY_CAN`, KHÔNG viết tay trong dịch vụ; và đợt này KHÔNG đụng
    một dòng nào của `services/bctc.py`.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r1.db")
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
from sqlalchemy import create_engine                             # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import JournalEntry, JournalLine      # noqa: E402
from app.models.bao_cao_da_lap import BanBaoCao                  # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import bao_cao_da_lap as BBC                   # noqa: E402
from app.services import bctc as BCTC                            # noqa: E402
from app.services import chu_ky as CK                            # noqa: E402

TU, DEN = date(2026, 1, 1), date(2026, 6, 30)


class _U:
    """Người dùng tối thiểu: ba ô mà dịch vụ thật sự đọc."""

    def __init__(self, username, role, company_id=None):
        self.username, self.role, self.company_id = username, role, company_id
        self.id = abs(hash(username)) % 100000


KT = _U("ketoan", "ketoan_truong")
CT = _U("chutich", "chutich")


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ — cửa hẹp của CI chạy nhiều tệp trong MỘT tiến trình, nên ghi
    vào CSDL dùng chung thì làm lệch số của tệp khác (test_misa đối chiếu tới từng đồng)."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    return db


def _ct(db, ma, ngay, dong, nguon="thu_cong"):
    e = JournalEntry(code=ma, entry_date=ngay, ngay_chung_tu=ngay, period=f"{ngay:%Y-%m}",
                     description="Sổ thử Đợt R1", status="da_ghi_so", source_type=nguon,
                     source_ref="")
    db.add(e)
    db.flush()
    for tk, no, co in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co,
                           partner_code="", partner=""))
    db.commit()


def _so(db):
    """Sổ thử: góp vốn 10 tỷ, bán một chuyến 3 tỷ, giá vốn 2 tỷ."""
    _ct(db, "R1-1", date(2026, 1, 5), [("1111", 10_000_000_000, 0), ("411", 0, 10_000_000_000)])
    _ct(db, "R1-2", date(2026, 3, 20), [("131", 3_300_000_000, 0), ("5111", 0, 3_000_000_000),
                                        ("33311", 0, 300_000_000)])
    _ct(db, "R1-3", date(2026, 3, 21), [("632", 2_000_000_000, 0), ("1111", 0, 2_000_000_000)])


def _lap(db, u=KT, ky="2026-H1", dai_dien="Trần Văn Tuấn"):
    return BBC.lap(db, u, loai="bctc", loai_ky="tuy_chon", ky=ky, tu_ngay=TU, den_ngay=DEN,
                   nguoi_dai_dien=dai_dien)


def _gt(b, bang, ma):
    for d in b.dong:
        if d.bang == bang and d.ma == ma:
            return float(d.gia_tri)
    return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. LẬP — đúng số của sổ tại thời điểm lập
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r1_1_lap_ra_dung_so_cua_so():
    """Bản đóng băng phải trùng ĐÚNG số mà màn hình đang đọc — không phải một phép tính thứ hai."""
    db = _rieng()
    try:
        _so(db)
        rep = BCTC.bctc(db, DEN, TU)
        b = _lap(db)
        assert b.trang_thai == "nhap"
        assert b.lap_boi == "ketoan" and b.lap_luc is not None
        assert len(b.dong) > 50, "bộ BCTC phải có đủ chỉ tiêu, không phải vài dòng"
        for bang in ("thtc", "kqkd", "lctt"):
            cho = {r["code"]: float(r.get("now") or 0.0) for r in rep[bang] if r.get("code")}
            for ma, v in cho.items():
                assert abs(_gt(b, bang, ma) - v) < 0.005, f"{bang}/{ma} đóng băng sai"
        assert _gt(b, "thtc", "111") == 8_000_000_000
        assert _gt(b, "kqkd", "01") == 3_000_000_000
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. ĐIỀU ĐỢT NÀY SINH RA ĐỂ LÀM — sổ đổi, bản KHÔNG đổi
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r1_2_so_doi_nhung_ban_khong_doi():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP.

    Ghi thêm một bút toán ĐỀ NGÀY CŨ (đúng kiểu cửa chốt sổ kiểm toán vẫn ghi). Sổ đổi, nên
    `BCTC.bctc()` tính lại ra số khác. Bản đã lập PHẢI giữ nguyên số cũ — nếu nó cũng đổi thì
    bảng này vô nghĩa và 502-của-niềm-tin quay lại: không ai biết báo cáo đã phát hành ghi gì.
    """
    db = _rieng()
    try:
        _so(db)
        b = _lap(db)
        truoc = _gt(b, "thtc", "111")
        assert truoc == 8_000_000_000

        # Bút toán đề ngày CŨ, ghi sau khi đã lập bản — đúng cái cửa chốt sổ kiểm toán vẫn làm.
        _ct(db, "R1-SAU", date(2026, 2, 10),
            [("1111", 500_000_000, 0), ("411", 0, 500_000_000)], nguon="kiem_toan")

        moi = BCTC.bctc(db, DEN, TU)
        ht = {r["code"]: float(r.get("now") or 0.0) for r in moi["thtc"] if r.get("code")}
        assert ht["111"] == 8_500_000_000, "sổ PHẢI đổi — nếu không thì phép thử này không đo gì"

        db.expire_all()
        b2 = db.get(BanBaoCao, b.id)
        assert _gt(b2, "thtc", "111") == truoc, (
            "BẢN ĐÃ LẬP KHÔNG ĐƯỢC ĐỔI THEO SỔ. Đây là toàn bộ lý do bảng này tồn tại: ngày "
            "15/10/2026 chỉ tiêu 111 tại 30/06/2026 đã tụt 500 triệu vì một bút toán đề ngày cũ, "
            "và không có bản đóng băng thì không ai biết.")
        assert BBC.du_lieu(b2)["tu_ban"] is True
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CHỮ KÝ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r1_3_nguoi_lap_khong_tu_ky():
    """Việc trình và việc ký phải là hai người, bất kể hai người ấy to đến đâu."""
    db = _rieng()
    try:
        _so(db)
        b = _lap(db, u=CT)                      # Chủ tịch tự lập…
        BBC.trinh(db, CT, b)
        with pytest.raises(BBC.SaiBanBaoCao) as ex:
            BBC.ky(db, CT, b)                   # …rồi tự ký: chặn
        assert "không tự ký" in str(ex.value)
    finally:
        db.close()


def test_r1_4_ky_thi_ban_cu_cung_ky_bi_THAY_THE_chu_khong_bi_xoa():
    db = _rieng()
    try:
        _so(db)
        b1 = _lap(db)
        BBC.trinh(db, KT, b1)
        BBC.ky(db, CT, b1)
        assert b1.trang_thai == "da_ky"
        assert BBC.ban_da_ky(db, "bctc", "2026-H1").id == b1.id

        b2 = _lap(db)                            # lập lại cùng kỳ
        BBC.trinh(db, KT, b2)
        BBC.ky(db, CT, b2)

        db.expire_all()
        cu = db.get(BanBaoCao, b1.id)
        assert cu is not None, "bản cũ KHÔNG được xoá — báo cáo xoá được là báo cáo không ai tin"
        assert cu.trang_thai == "da_thay_the"
        assert db.get(BanBaoCao, b2.id).thay_the_id == b1.id
        assert BBC.ban_da_ky(db, "bctc", "2026-H1").id == b2.id
    finally:
        db.close()


def test_r1_5_trinh_phai_co_nguoi_dai_dien_va_tu_choi_phai_co_ly_do():
    db = _rieng()
    try:
        _so(db)
        b = _lap(db, dai_dien="")
        with pytest.raises(BBC.SaiBanBaoCao) as ex:
            BBC.trinh(db, KT, b)
        assert "người đại diện" in str(ex.value)

        b.nguoi_dai_dien = "Trần Văn Tuấn"
        BBC.trinh(db, KT, b)
        with pytest.raises(BBC.SaiBanBaoCao):
            BBC.tu_choi(db, CT, b, "   ")
        BBC.tu_choi(db, CT, b, "Chỉ tiêu 420 chưa khớp thuyết minh")
        assert b.trang_thai == "tu_choi" and b.tu_choi_ly_do
    finally:
        db.close()


def test_r1_6_chua_co_ban_ky_thi_RONG_chu_khong_phai_bo_bao_cao_toan_so_0():
    """RỖNG ≠ 0. Nơi gọi phải nói ra điều ấy thành một câu người đọc được."""
    db = _rieng()
    try:
        _so(db)
        assert BBC.ban_da_ky(db, "bctc") is None
        b = _lap(db)
        assert BBC.ban_da_ky(db, "bctc") is None, "bản NHÁP chưa phải bản đã ký"
        BBC.trinh(db, KT, b)
        assert BBC.ban_da_ky(db, "bctc") is None, "bản CHỜ KÝ chưa phải bản đã ký"
        BBC.ky(db, CT, b)
        assert BBC.ban_da_ky(db, "bctc") is not None
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. RANH GIỚI CỦA ĐỢT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_r1_7_luat_chu_ky_khai_o_dung_mot_cho():
    """`bao_cao_da_lap.py` KHÔNG được viết tay tên vai. Một luật, một chỗ — cùng lẽ với Đợt E16."""
    assert CK.can_ky(BBC.LOAI_CHU_KY) == ("chutich",)
    nguon = inspect.getsource(BBC)
    ma = [l.strip() for l in nguon.splitlines()
          if '"chutich"' in l and not l.strip().startswith("#")]
    assert ma == [], (
        "Tên vai ký phải lấy từ `chu_ky.VAI_KY_CAN`, không gõ tay trong dịch vụ. Đang thấy: "
        + repr(ma))


def test_r1_8_dot_nay_khong_dung_mot_dong_nao_cua_bctc():
    """Bản đã lập GỌI `BCTC.bctc()`, không chép lại phép tính của nó.

    Chép lại là hai công thức cho cùng một câu hỏi, và chúng sẽ lệch nhau — đúng cái bệnh
    `reports.py::_khong_phai_ket_chuyen` đã ghi lại ngày 18/9/2026.
    """
    nguon = inspect.getsource(BBC)
    assert "BCTC.bctc(" in nguon, "phải gọi đúng hàm mà màn hình vẫn gọi"
    for cam in ("balance_sheet_tt99", "income_statement_tt99", "cash_flow_indirect_tt99",
                "account_balances"):
        assert cam not in nguon, (
            f"`bao_cao_da_lap.py` không được gọi thẳng `{cam}` — gọi `BCTC.bctc()` để bản đã lập "
            f"và màn hình luôn đi qua cùng một phép tính.")
    # Và `lap()` gọi ĐÚNG MỘT LẦN: hai lần gọi là hai bộ số tính ở hai thời điểm khác nhau nhét
    # vào cùng một bản, mà một bản phải là một lát cắt của sổ tại MỘT thời điểm.
    assert inspect.getsource(BBC.lap).count("BCTC.bctc(") == 1
