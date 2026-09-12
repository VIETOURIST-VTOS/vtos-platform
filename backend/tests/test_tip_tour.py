# -*- coding: utf-8 -*-
"""Đ-6 · Tiền tip — đơn vị bắt buộc, tỷ lệ chờ chữ ký, và phép chia không được làm mất một đồng.

Chủ tịch chốt 12/9/2026: "tiền tip tour châu Âu chia 1 phần với công ty", và phần công ty giữ lại
ghi nhận là DOANH THU KHÁC của chuyến. Nguyên tắc đã chốt; TỶ LỆ thì chưa ký.

Số thật dùng trong tệp này lấy từ QUYẾT TOÁN CHÂU ÂU 6 NƯỚC 27.05–04.06/2026:

    sheet QT             T56 = 27 × 30 × 30.500 = 24.705.000 đ     → 27 €/khách/CHUYẾN
    sheet QUYẾT TOÁN TL  D11 = 3 × 9 × 30 = 810 €, ghi "3E/PAX/DAY X 9DAY X 30PAX"
                                                                    → 3 €/khách/NGÀY

Cùng một khoản tiền, HAI đơn vị, trong CÙNG MỘT TỆP. Đó là cái bẫy phép thử này canh.
"""
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
from app.db.session import Base
from app.models.core import Param
from app.models.lop3_tour import LOAI_DOANH_THU
from app.services import tip_tour as TIP
from app.services.rules import clear_param_cache


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    clear_param_cache()
    with Session(eng) as s:
        yield s
    clear_param_cache()


def _ky_ty_le(db, gia_tri: str, tu: date = date(2026, 1, 1)):
    db.add(Param(key=TIP.KHOA_TY_LE, value=gia_tri, label="Tỷ lệ tip công ty",
                 effective_from=tu, status="active", signed_chutich=True, signed_tgd=True))
    db.commit()
    clear_param_cache()


TY_GIA_EUR = 30_500
EU_TONG = 24_705_000


# =============================================================================================
# 1. CÁI BẪY: cùng một khoản tiền, hai đơn vị
# =============================================================================================

def test_hai_don_vi_khac_nhau_ra_CUNG_mot_so_tien_cua_te_p_that():
    """27 €/khách/chuyến và 3 €/khách/ngày × 9 ngày đều phải ra 24.705.000 đ."""
    ca_chuyen = TIP.tien_tip_thu(27, "moi_khach_ca_chuyen", 30, None, TY_GIA_EUR)
    moi_ngay = TIP.tien_tip_thu(3, "moi_khach_moi_ngay", 30, 9, TY_GIA_EUR)
    assert ca_chuyen == pytest.approx(EU_TONG)
    assert moi_ngay == pytest.approx(EU_TONG)


def test_go_don_gia_ca_chuyen_vao_o_moi_ngay_thi_SAI_GAP_CHIN_LAN():
    """Đây là con số chứng minh vì sao đơn vị phải là ô bắt buộc.

    Nếu hệ thống chỉ có một ô "đơn giá" và luôn nhân số ngày, người nhập gõ 27 (số ghi ở sheet QT)
    sẽ ra 222.345.000 đ thay vì 24.705.000 đ — và nó vẫn trông như một con số hợp lệ.
    """
    dung = TIP.tien_tip_thu(27, "moi_khach_ca_chuyen", 30, 9, TY_GIA_EUR)
    sai = TIP.tien_tip_thu(27, "moi_khach_moi_ngay", 30, 9, TY_GIA_EUR)
    assert dung == pytest.approx(EU_TONG)
    assert sai == pytest.approx(EU_TONG * 9)
    assert sai / dung == pytest.approx(9.0)


def test_khong_khai_don_vi_thi_TU_CHOI_tinh_chu_khong_doan():
    assert TIP.tien_tip_thu(27, None, 30, 9, TY_GIA_EUR) is None
    assert TIP.tien_tip_thu(27, "", 30, 9, TY_GIA_EUR) is None
    assert TIP.tien_tip_thu(27, "moi_khach", 30, 9, TY_GIA_EUR) is None, "đơn vị lạ cũng phải từ chối"


def test_don_vi_moi_ngay_ma_thieu_so_ngay_thi_RONG_chu_khong_coi_la_mot_ngay():
    assert TIP.tien_tip_thu(3, "moi_khach_moi_ngay", 30, None, TY_GIA_EUR) is None


def test_don_vi_ca_chuyen_thi_so_ngay_KHONG_anh_huong():
    a = TIP.tien_tip_thu(27, "moi_khach_ca_chuyen", 30, 9, TY_GIA_EUR)
    b = TIP.tien_tip_thu(27, "moi_khach_ca_chuyen", 30, 99, TY_GIA_EUR)
    assert a == b == pytest.approx(EU_TONG)


# =============================================================================================
# 2. Tỷ lệ chưa ký thì KHÔNG chia
# =============================================================================================

def test_chua_ky_ty_le_thi_van_bao_TONG_nhung_khong_chia(db):
    """"Đã thu bao nhiêu" là câu trả lời được ngay. "Chia thế nào" mới là câu đang chờ chữ ký."""
    kq = TIP.tinh(db, don_gia=27, don_vi="moi_khach_ca_chuyen", so_khach=30, ty_gia=TY_GIA_EUR)
    assert kq["tong"] == pytest.approx(EU_TONG)
    assert kq["cong_ty"] is None and kq["truong_doan"] is None
    assert kq["chua_chia"] == "chua_ky_ty_le"
    assert "ty_le_tip_cong_ty" in kq["vi_sao"]


def test_ty_le_mac_dinh_de_TRONG_chu_khong_phai_0_hay_1(db):
    """0% (công ty không lấy gì) và 100% (công ty lấy hết) đều là chính sách hợp lệ.

    Mã không được đoán hộ bên nào, nên mặc định phải là RỖNG.
    """
    assert TIP.ty_le_cong_ty(db) is None


def test_ky_roi_thi_chia_va_hai_phan_cong_lai_dung_bang_tong(db):
    _ky_ty_le(db, "0.4")
    kq = TIP.tinh(db, don_gia=27, don_vi="moi_khach_ca_chuyen", so_khach=30, ty_gia=TY_GIA_EUR)
    assert kq["ty_le_cong_ty"] == pytest.approx(0.4)
    assert kq["cong_ty"] + kq["truong_doan"] == kq["tong"]
    assert kq["chua_chia"] == ""


def test_ty_le_ngoai_khoang_0_1_bi_TU_CHOI(db):
    """Tham số hỏng thì phép chia dừng, thay vì chia ra một phần âm hoặc phần lớn hơn số có thật."""
    _ky_ty_le(db, "1.5")
    assert TIP.ty_le_cong_ty(db) is None
    clear_param_cache()


def test_ty_le_co_hieu_luc_theo_NGAY(db):
    _ky_ty_le(db, "0.3", date(2026, 1, 1))
    _ky_ty_le(db, "0.6", date(2027, 1, 1))
    assert TIP.ty_le_cong_ty(db, date(2026, 6, 1)) == pytest.approx(0.3)
    assert TIP.ty_le_cong_ty(db, date(2027, 6, 1)) == pytest.approx(0.6), \
        "đoàn đã đi giữ nguyên tỷ lệ của ngày nó khởi hành"


# =============================================================================================
# 3. Phép chia không được làm mất hay đẻ ra một đồng
# =============================================================================================

@pytest.mark.parametrize("tong,ty_le", [
    (24_705_000, 0.4), (1, 0.5), (3, 0.5), (999_999, 1 / 3), (7, 0.7), (24_705_000, 0.333333),
])
def test_hai_phan_LUON_cong_bang_tong_du_ty_le_le_den_dau(tong, ty_le):
    """Làm tròn hai phía độc lập nhau thì tổng lệch một đồng, và một đồng lệch trên bảng chia tiền
    là chỗ người ta ngồi dò cả buổi mà không tìm ra vì không phía nào sai."""
    c = TIP.chia(tong, ty_le)
    assert c["cong_ty"] + c["truong_doan"] == c["tong"]
    assert c["cong_ty"] >= 0 and c["truong_doan"] >= 0


def test_chia_khi_thieu_mot_ve_thi_hai_phan_RONG_chu_khong_bang_0():
    assert TIP.chia(1_000_000, None)["cong_ty"] is None
    assert TIP.chia(None, 0.5)["cong_ty"] is None


# =============================================================================================
# 4. Hoàn tip cho đại lý, và chỗ ghi nhận
# =============================================================================================

def test_hoan_cho_tung_ben_ban_dung_hai_dong_cua_te_p_EU():
    """Tệp EU hoàn cho JTRAVEL 3 khách và VTOURIST 5 khách."""
    ra = TIP.hoan_cho_ben_ban(27, "moi_khach_ca_chuyen", None,
                              {"JTRAVEL": 3, "VTOURIST": 5}, TY_GIA_EUR)
    assert ra["JTRAVEL"] == pytest.approx(2_470_500)
    assert ra["VTOURIST"] == pytest.approx(4_117_500)


def test_ben_khong_co_khach_thi_KHONG_sinh_dong_hoan_bang_0():
    ra = TIP.hoan_cho_ben_ban(27, "moi_khach_ca_chuyen", None, {"JTRAVEL": 0}, TY_GIA_EUR)
    assert ra == {}


def test_phan_cong_ty_co_cho_ghi_nhan_la_DOANH_THU(db):
    """Chủ tịch chốt 12/9: phần công ty giữ lại là doanh thu khác của chuyến."""
    assert "tip_cong_ty" in LOAI_DOANH_THU
    assert "tip" in LOAI_DOANH_THU["tip_cong_ty"].lower()
