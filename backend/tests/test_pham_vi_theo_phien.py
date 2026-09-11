# -*- coding: utf-8 -*-
"""PQ-6 · Phạm vi pháp nhân theo phiên – khai chỗ phải lọc, và siết tài khoản chưa gán sau mốc.

Ba quy tắc viết ngày 08/9 (không gộp im lặng · không giấu · không khoá cửa bằng một cột chưa ai
điền) vẫn đúng nguyên và có phép thử riêng. Tệp này canh hai thứ chúng còn thiếu:

  1. Hàng rào đã dựng mà chưa bật. Đo 11/9/2026: 16 mô hình mang cột company_id, PV.loc() được gọi
     ĐÚNG 5 LẦN trong toàn bộ api/v1. Hàm loc() viết xong từ 08/9 và đúng – nó chỉ không được gọi.
     Nhìn vào mã thấy có hàng rào nên không ai đi dựng cái thứ hai; đó là kiểu hỏng khó thấy nhất.

  2. Quy tắc 3 không có hạn dùng. "Chưa gán thì thấy toàn bộ" là nhường nhịn hợp lý khi đang chạy
     thử. Sau ngày vận hành thật nó thành lỗ hổng: mở một tài khoản mà quên gán là vô tình trao
     quyền xem toàn tập đoàn, và không có gì kêu lên.
"""
from datetime import date

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Param, User
from app.services import pham_vi_phap_nhan as PV
from app.services import moi_truong_du_lieu as MT

@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _nguoi(vai_tro="nv_dh", company_id=None):
    return User(id=1, username="x", full_name="X", role=vai_tro, company_id=company_id)


def _chot_moc_van_hanh(db, ngay="2026-12-01"):
    db.add(Param(key=MT.THAM_SO_MOC, value=ngay, label="Mốc vận hành thật",
                 effective_from=date(2026, 1, 1), status="active",
                 signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
    db.flush()
    from app.services import rules as R
    if hasattr(R, "clear_param_cache"):
        R.clear_param_cache()


# ---------------------------------------------------------------------------------------------
# 1. Khai chỗ phải lọc
# ---------------------------------------------------------------------------------------------

def test_moi_mo_hinh_co_cot_phap_nhan_deu_phai_duoc_khai_mot_lan():
    """Mô hình mang cột pháp nhân mà không khai gì thì không ai biết nó nên lọc hay không.

    Hai danh sách phải phủ kín và không chồng nhau: PHAI_LOC và CO_Y_KHONG_LOC.
    """
    khai = set(PV.PHAI_LOC) | set(PV.CO_Y_KHONG_LOC)
    assert not (set(PV.PHAI_LOC) & set(PV.CO_Y_KHONG_LOC)), "một mô hình khai ở cả hai danh sách"
    co_cot = {c.__name__ for c in PV.bang_co_cot_phap_nhan()}
    thieu = co_cot - khai
    assert not thieu, f"mô hình có cột pháp nhân mà chưa khai: {sorted(thieu)}"


def test_moi_dong_khai_deu_kem_ly_do():
    """'Cố ý không lọc' là lối thoát dễ nhất cho một chỗ quên nối – không viết được lý do thì
    nghĩa là chưa chắc đã cố ý."""
    for ten, ly_do in list(PV.PHAI_LOC.items()) + list(PV.CO_Y_KHONG_LOC.items()):
        assert len(ly_do) >= 25, f"{ten}: khai mà không nói vì sao"


def test_do_duoc_mo_hinh_nao_da_khai_ma_chua_noi_loc():
    """Phép đo cho bộ kiểm của làn Kiểm soát – danh sách rỗng nghĩa là đã nối xong.

    KHÔNG khẳng định danh sách phải rỗng ngay hôm nay: nối loc() vào từng truy vấn là việc VPM-C2.
    Phép thử này canh chuyện khác – rằng phép ĐO còn chạy được và còn nhìn thấy được cả hai chiều.
    """
    thieu = PV.mo_hinh_thieu_loc()
    assert isinstance(thieu, list)
    assert set(thieu) <= set(PV.PHAI_LOC), "báo thiếu một mô hình chưa từng khai là phải lọc"
    da_noi = set(PV.PHAI_LOC) - set(thieu)
    assert {"Tour", "Booking", "Receipt", "PaymentRequest", "JournalEntry"} <= da_noi, (
        "năm mô hình vốn ĐÃ nối loc() nay không còn – hàng rào vừa bị gỡ")


def test_phep_do_nhin_thay_khi_mot_cho_noi_bi_go(tmp_path):
    """Phép đo xanh vì không nhìn thấy gì thì vô dụng – thử ngược để chắc nó thật sự nhìn."""
    (tmp_path / "gia.py").write_text(
        "q = PV.loc(q, Tour, u)\nq = PV.loc(q, Booking, u)\n", encoding="utf-8")
    thieu = PV.mo_hinh_thieu_loc(str(tmp_path))
    assert "Tour" not in thieu and "Booking" not in thieu
    assert "Receipt" in thieu and "BaoGia" in thieu


# ---------------------------------------------------------------------------------------------
# 2. Siết tài khoản chưa gán, kể từ mốc vận hành thật
# ---------------------------------------------------------------------------------------------

def test_truoc_moc_thi_chua_gan_van_thay_toan_bo(db):
    """Bật lọc cứng lúc chưa ai kịp gán thì cả công ty đứng lại trong một buổi sáng."""
    p = PV.pham_vi_theo_phien(db, _nguoi("nv_dh", None))
    assert p["ly_do_khong_gioi_han"] == "tai_khoan_chua_gan_phap_nhan"
    assert p["chan_het"] is False
    assert "chưa được gán pháp nhân" in p["cau_hien_thi"]


def test_sau_moc_thi_chua_gan_KHONG_con_thay_toan_bo(db):
    """Sau ngày vận hành thật, 'chưa gán thì thấy tất' là lỗ hổng chứ không còn là nhường nhịn."""
    _chot_moc_van_hanh(db)
    assert MT.che_do(db, date(2026, 12, 5)) == MT.THAT, "mốc chốt rồi thì qua ngày ấy phải là THẬT"
    from unittest.mock import patch
    with patch.object(PV, "sau_moc_van_hanh_that", lambda _db: True):
        p = PV.pham_vi_theo_phien(db, _nguoi("nv_dh", None))
        assert p["chan_het"] is True
        assert "chưa xem được dữ liệu nào" in p["cau_hien_thi"]
        # và phải nói AI gán được – từ chối mà không chỉ đường thì người ta đi tìm đường vòng
        assert "Hành chính Nhân sự" in p["cau_hien_thi"] or "CNTT" in p["cau_hien_thi"]


def test_sau_moc_khong_dung_toi_vai_tro_toan_tap_doan_va_nguoi_da_gan(db):
    """Siết đúng một nhóm. Siết nhầm Chủ tịch hay Kế toán là làm hỏng báo cáo hợp nhất."""
    from unittest.mock import patch
    with patch.object(PV, "sau_moc_van_hanh_that", lambda _db: True):
        for vai in PV.TOAN_TAP_DOAN:
            assert PV.pham_vi_theo_phien(db, _nguoi(vai, None))["chan_het"] is False, vai
        assert PV.pham_vi_theo_phien(db, _nguoi("nv_dh", 3))["chan_het"] is False


def test_loc_theo_phien_khong_doi_hanh_vi_cua_loc_cu(db):
    """Năm chỗ đang gọi loc() phải giữ nguyên hệ quả – đổi ngầm là đổi luật mà không ai biết.

    Phải thử CẢ HAI hạng người, vì hai nhánh của hàm mới rẽ theo đúng chỗ đó:

      · người ĐÃ gán pháp nhân  – loc() cũ trả về câu có điều kiện company_id
      · người CHƯA gán           – loc() cũ trả về câu KHÔNG lọc (quy tắc 3, còn hiệu lực trước mốc)

    Bản đầu chỉ thử hạng thứ nhất, và một đột biến đổi điều kiện chặn thành `if pham_vi(u) is None`
    đã lọt qua cả bộ: với người đã gán thì pham_vi() không None nên nhánh sai không bao giờ chạy.
    Đột biến ấy chặn sạch đúng những người mà quy tắc 3 đang cố ý nhường – nghĩa là nó lặng lẽ bật
    sớm cái siết mà cả tệp này viết ra để hoãn lại tới ngày vận hành thật.
    """
    from app.models.core import Tour
    for u in (_nguoi("nv_dh", 3), _nguoi("nv_dh", None)):
        a = str(PV.loc(sa.select(Tour), Tour, u))
        b = str(PV.loc_theo_phien(sa.select(Tour), Tour, u))          # không truyền db
        assert a == b, f"đổi hành vi khi không có db (company_id={u.company_id})"
        c = str(PV.loc_theo_phien(sa.select(Tour), Tour, u, db))      # truyền db, chưa qua mốc
        assert a == c, f"đổi hành vi khi chưa qua mốc (company_id={u.company_id})"
    # và người chưa gán, TRƯỚC mốc, phải thật sự còn thấy – không phải xanh vì hai câu cùng sai
    assert "false" not in str(
        PV.loc_theo_phien(sa.select(Tour), Tour, _nguoi("nv_dh", None), db)).lower()


def test_loc_theo_phien_chan_het_bang_false_chu_khong_bang_dieu_kien_tu_mau_thuan(db):
    from unittest.mock import patch
    from app.models.core import Tour
    with patch.object(PV, "sau_moc_van_hanh_that", lambda _db: True):
        q = str(PV.loc_theo_phien(sa.select(Tour), Tour, _nguoi("nv_dh", None), db))
    assert "false" in q.lower()
    assert "IS NULL AND" not in q.upper(), "chặn bằng điều kiện tự mâu thuẫn – người đọc sau sẽ sửa nó"


def test_danh_sach_tai_khoan_phai_gan_truoc_moc(db):
    """Sau mốc, mỗi dòng còn lại trong danh sách này là một người sáng ra không mở được màn hình nào."""
    db.add_all([
        User(username="a", full_name="A", role="nv_dh", company_id=None, active=True, password_hash="x"),
        User(username="b", full_name="B", role="nv_dh", company_id=2, active=True, password_hash="x"),
        User(username="c", full_name="C", role="ketoan", company_id=None, active=True, password_hash="x"),
        User(username="d", full_name="D", role="nv_kd", company_id=None, active=False, password_hash="x"),
    ])
    db.flush()
    ds = {r["username"] for r in PV.tai_khoan_chua_gan(db)}
    assert ds == {"a"}, "phải bỏ người đã gán, vai trò toàn tập đoàn, và tài khoản đã khoá"
