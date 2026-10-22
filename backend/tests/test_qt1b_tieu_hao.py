# -*- coding: utf-8 -*-
"""QT-1b · Phép kiểm tiêu hao L/100km khi quyết toán chuyến (Chủ tịch chốt 22/10/2026).

Luật: vượt định mức theo số chỗ QUÁ 15% thì cảnh báo VÀNG — không chặn ký. Số lít lấy lít khai;
khoản không ghi lít thì quy tiền ÷ giá dầu đúng ngày đi; không có giá thì nói «chưa đo được».
Xe chưa có định mức cho số chỗ của nó → vàng, chỉ ra cửa khai định mức.

Số liệu dựng từ bộ hồ sơ thật 50F-046.22 (QT-1): 2.333 km, 599,771 lít → 25,7 L/100km.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip, TripCost, FuelNorm, GiaDauNgay  # noqa: E402
from app.services import quyet_toan_chuyen as QT  # noqa: E402

KM = 2333
LIT = 599.771            # 25,7 L/100km


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _chuyen(db, lit=LIT, tien=18_353_807, so_cho=45, dinh_muc=None, ma="QT1B"):
    v = Vehicle(plate=f"50F-{ma}", seats=so_cho, seats_xac_nhan_boi="gd_doi_xe")
    db.add(v); db.flush()
    if dinh_muc is not None:
        db.add(FuelNorm(seats=so_cho, l_100km=dinh_muc))
    t = Trip(ma_phieu=ma, vehicle_id=v.id, ten_tour="Di sản miền Trung",
             ngay_di=date(2026, 10, 6), ngay_ve=date(2026, 10, 12), km_dau=197_435, km_cuoi=199_768)
    db.add(t); db.flush()
    db.add(TripCost(trip_id=t.id, kind="dau", amount=tien, tra_bang="the_cong_ty", lit=lit))
    db.flush()
    return t


def _th(db, t):
    return [x for x in QT.kiem(db, t, km_tour_tren_giay=KM) if x["o"] == "tieu_hao"]


def test_qt1b_1_vuot_dinh_muc_thi_canh_bao_vang_khong_chan(db):
    t = _chuyen(db, dinh_muc=20.0)                     # 25,7 > 20 × 1,15 = 23,0
    c = _th(db, t)
    assert len(c) == 1 and c[0]["muc"] == "vang", c
    assert "25.7" in c[0]["noi"] and "20.0" in c[0]["noi"]
    assert not [x for x in QT.kiem(db, t, km_tour_tren_giay=KM) if x["muc"] == "do"], \
        "tiêu hao vượt chỉ được cảnh báo — đường xấu có thể vượt thật, chặn là chặn nhầm người đúng"


def test_qt1b_2_sat_bien_thi_khong_bao(db):
    # Định mức 20 → biên 23,0. Chuyến 536,59 lít / 2.333 km = 23,0 L/100km: ĐÚNG BẰNG biên, chưa vượt.
    t = _chuyen(db, lit=536.59, dinh_muc=20.0)
    assert QT.tieu_hao(db, t)["l_100km"] == 23.0
    assert _th(db, t) == []
    # Nhích 0,1 qua biên thì báo.
    t2 = _chuyen(db, lit=538.9, dinh_muc=None, ma="QT1B-2")
    assert QT.tieu_hao(db, t2)["l_100km"] == 23.1
    assert len(_th(db, t2)) == 1


def test_qt1b_3_be_nguoc_noi_dinh_muc_gap_doi_thi_ca_vuot_thoi_do(db):
    t = _chuyen(db, dinh_muc=40.0)                     # gấp đôi 20 → 25,7 không còn vượt
    assert _th(db, t) == []


def test_qt1b_4_chua_co_dinh_muc_thi_vang_va_chi_cua_khai(db):
    c = _th(db, _chuyen(db, dinh_muc=None, so_cho=29))
    assert len(c) == 1 and c[0]["muc"] == "vang" and "29 chỗ" in c[0]["noi"] and "định mức" in c[0]["noi"]


def test_qt1b_5_khoan_khong_ghi_lit_thi_quy_theo_gia_ngay(db):
    db.add(GiaDauNgay(ngay=date(2026, 10, 6), loai="do", gia_lit=30_600.0))
    t = _chuyen(db, lit=0, tien=30_600 * 600, dinh_muc=20.0)    # 600 lít → 25,7 L/100km
    th = QT.tieu_hao(db, t)
    assert th["lit"] == 600.0 and th["l_100km"] == 25.7
    assert len(_th(db, t)) == 1


def test_qt1b_6_khong_co_gia_ngay_thi_noi_chua_do_duoc_khong_doan(db):
    db.add(GiaDauNgay(ngay=date(2026, 10, 5), loai="do", gia_lit=30_600.0))  # giá NGÀY KHÁC
    t = _chuyen(db, lit=0, dinh_muc=20.0)
    th = QT.tieu_hao(db, t)
    assert th["l_100km"] is None and th["thieu"]
    c = _th(db, t)
    assert len(c) == 1 and "Chưa đo được" in c[0]["noi"], "không được lấy giá ngày gần nhất để đoán"


def test_qt1b_7_khong_co_khoan_dau_thi_khong_kiem(db):
    t = _chuyen(db, dinh_muc=20.0)
    db.query(TripCost).filter(TripCost.trip_id == t.id).delete(); db.flush()
    assert QT.tieu_hao(db, t) is None and _th(db, t) == []


def test_qt1b_8_bien_la_15_phan_tram_dung_luat_chu_tich_chot(db):
    from app.services import rules as R
    mac_dinh = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    assert float(mac_dinh["qt_tieu_hao_bien"]) == QT.BIEN_TIEU_HAO == 0.15
    assert QT.bien_tieu_hao(db) == 0.15


def test_qt1b_9_bien_doc_tu_bang_tham_so_chu_khong_go_cung(db, monkeypatch):
    """Kế toán nới biên ở màn tham số thì phép kiểm đổi theo — không phải sửa mã."""
    from app.services import rules as R
    goc = R.get_param
    monkeypatch.setattr(R, "get_param",
                        lambda db, k, on=None: 0.30 if k == "qt_tieu_hao_bien" else goc(db, k, on))
    t = _chuyen(db, dinh_muc=20.0)                     # 25,7 ≤ 20 × 1,30 = 26,0
    assert _th(db, t) == []
