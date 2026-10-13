# -*- coding: utf-8 -*-
"""Đợt E14 (13/10/2026) — HAI MỐC THỜI GIAN CỦA BÚT TOÁN ĐIỀU CHỈNH.

Đợt E3 đã tách NGÀY CHỨNG TỪ khỏi NGÀY GHI SỔ. Bút toán ĐIỀU CHỈNH cần hai mốc nữa, và thiếu
chúng thì hai câu hỏi không trả lời được — cả hai đều có người hỏi thật:

  1. "SỬA CHO KỲ NÀO?" — thuyết minh BCTC phải nói *điều chỉnh của kỳ 09*. Không có ô này thì một
     bút toán ghi tháng 10 sửa số tháng 9 trông Y HỆT một nghiệp vụ phát sinh tháng 10.
  2. "BIẾT TỪ BAO GIỜ, SỬA SAU BAO LÂU?" — kiểm toán hỏi đúng câu này.

PHÉP KIỂM ĐI CẢ HAI CHIỀU, và đó là chỗ dễ bỏ sót nhất: điều chỉnh mà THIẾU hai mốc là mất câu
trả lời, còn nghiệp vụ thường mà ĐIỀN hai mốc là một lời nói dối nhỏ nằm ngay trong sổ.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e14.db")
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
from app.models.accounting import Account                    # noqa: E402
from app.services import accounting as ACC                   # noqa: E402
from app.services import chung_tu_loai as CTL                # noqa: E402
from app.services import dieu_chinh as DC                    # noqa: E402

Base.metadata.create_all(engine)

NGAY = date(2098, 10, 20)        # kỳ ghi sổ 2098-10
KY_GOC = "2098-09"


@pytest.fixture(scope="module", autouse=True)
def _so():
    db = SessionLocal()
    for c, n, k in (("642", "Chi phí quản lý", "CP"), ("112", "Tiền gửi ngân hàng", "TS")):
        if not db.get(Account, c):
            db.add(Account(code=c, name=n, kind=k, is_detail=True))
    db.commit()
    yield db
    db.close()


_dem = [0]


def _ghi(db, **kw):
    _dem[0] += 1
    return ACC.post_entry(db, "e14", "ketoan", kw.pop("entry_date", NGAY),
                          kw.pop("description", "Phép thử E14 %d" % _dem[0]),
                          [{"account": "642", "debit": 100_000}, {"account": "112", "credit": 100_000}],
                          "thu_cong", "e14:%d" % _dem[0], **kw)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. LOẠI NGHIỆP VỤ ĐIỀU CHỈNH — KHAI RA, không suy theo tên
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e14_1_danh_sach_khai_ra_chu_khong_suy_theo_ten():
    """Suy theo tên ("mã nào có chữ dieu_chinh") thì `dieu_chinh_ty_gia` sẽ tự rơi vào đây mà
    không ai quyết — mà đánh giá lại tỷ giá cuối kỳ KHÔNG phải sửa sai sót kỳ trước."""
    ma = open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "app", "services", "dieu_chinh.py"), encoding="utf-8").read()
    assert "NGHIEP_VU_DIEU_CHINH = (" in ma
    assert 'startswith("dieu_chinh' not in ma and '"dieu_chinh" in' not in ma
    for x in DC.NGHIEP_VU_DIEU_CHINH:
        assert x in CTL.NGHIEP_VU, f"{x} khai là điều chỉnh mà không có trong bảng nghiệp vụ"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. PHÉP KIỂM ĐI CẢ HAI CHIỀU
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e14_2_dieu_chinh_thieu_ky_goc_thi_KHONG_ghi_duoc(_so):
    with pytest.raises(DC.SaiDieuChinh) as ex:
        _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ngay_phat_hien=date(2098, 10, 15))
    assert "SỬA CHO KỲ NÀO" in str(ex.value)


def test_e14_3_dieu_chinh_thieu_ngay_phat_hien_thi_KHONG_ghi_duoc(_so):
    with pytest.raises(DC.SaiDieuChinh) as ex:
        _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc=KY_GOC)
    assert "NGÀY PHÁT HIỆN" in str(ex.value)


def test_e14_4_nghiep_vu_THUONG_ma_dien_hai_moc_thi_cung_KHONG_ghi_duoc(_so):
    """Chiều ngược, và nó quan trọng ngang chiều kia: điền hai mốc cho một bút toán bình thường
    là khai nó thành bút toán sửa sai — một lời nói dối nhỏ nằm ngay trong sổ."""
    with pytest.raises(DC.SaiDieuChinh) as ex:
        _ghi(_so, nghiep_vu="but_toan_tay", ky_goc=KY_GOC, ngay_phat_hien=date(2098, 10, 15))
    assert "chỉ dành cho bút toán ĐIỀU CHỈNH" in str(ex.value)


def test_e14_5_ky_goc_khong_duoc_nam_SAU_ky_ghi_so(_so):
    with pytest.raises(DC.SaiDieuChinh) as ex:
        _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc="2098-12",
             ngay_phat_hien=date(2098, 10, 15))
    assert "chưa tới" in str(ex.value)


def test_e14_6_ngay_phat_hien_khong_duoc_nam_SAU_ngay_ghi_so(_so):
    """Không ai sửa một sai sót trước khi phát hiện ra nó."""
    with pytest.raises(DC.SaiDieuChinh) as ex:
        _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc=KY_GOC,
             ngay_phat_hien=date(2098, 10, 25))
    assert "trước khi phát hiện" in str(ex.value)


def test_e14_7_but_toan_thuong_khong_khai_gi_thi_ghi_binh_thuong(_so):
    """Đường đi cũ KHÔNG đổi một chữ — đây là phép thử giữ cho đợt này không làm hỏng việc đang chạy."""
    e = _ghi(_so)
    assert e.ky_goc is None and e.ngay_phat_hien is None
    assert e.loai_nghiep_vu == "but_toan_tay"
    assert DC.so_ngay_de_sua(e) is None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. GHI ĐÚNG, VÀ CON SỐ KIỂM TOÁN HỎI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e14_8_dieu_chinh_du_hai_moc_thi_ghi_duoc_va_tra_loi_duoc_ca_hai_cau(_so):
    e = _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc=KY_GOC,
             ngay_phat_hien=date(2098, 10, 15))
    assert e.ky_goc == KY_GOC
    assert e.ngay_phat_hien == date(2098, 10, 15)
    assert e.period == "2098-10", "bút toán vẫn ghi vào kỳ ĐANG MỞ, không ghi vào kỳ gốc"
    assert DC.so_ngay_de_sua(e) == 5, "phát hiện 15/10, ghi sổ 20/10 → 5 ngày"


def test_e14_9_ky_goc_KHONG_MO_duoc_ky_da_khoa(_so):
    """`ky_goc` là một NHÃN, không phải một đường vòng qua cửa mở lại kỳ của Đợt E6.

    Đây là phép thử giữ cho Đợt E6 còn nghĩa: nếu khai `ky_goc` mà bút toán ghi thẳng vào kỳ ấy
    thì cửa hai-người-ký của E6 bị đi vòng ngay ngày đợt này lên.
    """
    from app.models.accounting import PeriodLock
    if not _so.get(PeriodLock, KY_GOC):
        _so.add(PeriodLock(period=KY_GOC, locked_by="ketoan", note="khóa để thử E14"))
        _so.commit()
    e = _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc=KY_GOC,
             ngay_phat_hien=date(2098, 10, 15))
    assert e.period == "2098-10", "ghi vào kỳ đang mở"
    assert ACC.is_locked(_so, KY_GOC) is True, "kỳ gốc vẫn khóa — nhãn không mở gì cả"


def test_e14_10_so_ngay_de_sua_TINH_LAI_chu_khong_luu(_so):
    """Lưu thì nó đóng băng, mà hai ngày kia còn sửa được lúc chứng từ chưa ghi sổ."""
    ma = open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "app", "models", "accounting.py"), encoding="utf-8").read()
    assert "so_ngay_de_sua" not in ma, "con số này bị lưu thành cột — nó phải tính lại lúc đọc"
    e = _ghi(_so, nghiep_vu="dieu_chinh_ky_truoc", ky_goc=KY_GOC,
             ngay_phat_hien=date(2098, 10, 1))
    assert DC.so_ngay_de_sua(e) == 19
    e.ngay_phat_hien = date(2098, 10, 18)
    assert DC.so_ngay_de_sua(e) == 2, "sửa ngày phát hiện thì con số phải đi theo"


def test_e14_11_cua_chot_so_kiem_toan_KHONG_bi_doi_khai_hai_moc():
    """`dieu_chinh_kiem_toan` CÓ chữ "điều chỉnh" trong tên nhưng KHÔNG nằm trong danh sách.

    Cửa chốt sổ theo BCTC kiểm toán (`misa.import_audited_checkpoint`) ghi bút toán vào đúng ngày
    `as_of` của bộ số kiểm toán: "sửa cho kỳ nào" luôn trùng kỳ ghi sổ, "ngày phát hiện" luôn trùng
    ngày ghi sổ. Hai mốc ở đấy không trả lời câu gì.

    Phép thử này không phải thủ tục. Lúc viết đợt này em đã xếp nó vào danh sách theo cái tên, và
    cửa chốt sổ kiểm toán ĐỎ ngay — 422 "phải khai SỬA CHO KỲ NÀO" trên một cửa đang chạy đúng.
    Phép thử ghi lại đúng chỗ đó: ai thêm nó vào danh sách thì đỏ ở đây, kèm việc phải làm là
    truyền hai mốc từ `misa.py`, chứ không phải đi xóa phép thử.
    """
    assert "dieu_chinh_kiem_toan" not in DC.NGHIEP_VU_DIEU_CHINH, (
        "Thêm `dieu_chinh_kiem_toan` vào NGHIEP_VU_DIEU_CHINH thì cửa chốt sổ theo BCTC kiểm toán "
        "(misa.import_audited_checkpoint) sẽ 422 vì nó không truyền hai mốc. Muốn thêm thì sửa "
        "chỗ gọi `post_entry` trong misa.py TRƯỚC, rồi mới sửa danh sách.")
    import inspect
    from app.services import misa as MISA
    nguon = inspect.getsource(MISA.import_audited_checkpoint)
    assert 'nghiep_vu="dieu_chinh_kiem_toan"' in nguon, (
        "Cửa chốt sổ kiểm toán đổi tên nghiệp vụ — đọc lại phép thử này trước khi sửa nó")
    assert "ky_goc" not in nguon, (
        "misa.py bắt đầu truyền `ky_goc` — nếu thế thì nó ĐƯỢC phép vào danh sách, và phép thử "
        "này phải đổi theo, có người ký")
