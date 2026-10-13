# -*- coding: utf-8 -*-
"""HQ-2 · Ô chọn kỳ cho khối Chủ tịch, và ba chỉ số thêm vào.

VÌ SAO VÒNG NÀY CÓ MẶT. Khối «Hiệu quả đội xe» xưa nay chỉ tính được tháng này / quý này / năm nay
theo HÔM NAY. Đo trên hệ thật 13/10/2026: tháng 10 chưa nạp chuyến nào nên kỳ Tháng rỗng, quý 4 chỉ
có tháng 10 nên kỳ Quý cũng rỗng — chỉ còn kỳ Năm có số. Chín tháng dữ liệu nằm sẵn trong máy mà
không có đường nào mở ra: không xem được tháng 9, không so được tháng 9 với tháng 8.

BA LUẬT KHÓ NHẤT, và cả ba đều được kiểm ngược:

  1. KỲ TRƯỚC PHẢI CÙNG SỐ THÁNG. Quý 4 mới đi được một tháng mà đem so với quý 3 đủ ba tháng thì
     mọi chỉ số cộng được đều tụt xuống một phần ba — và mũi tên đỏ ấy nói về tờ lịch, không nói về
     đội xe.

  2. KỲ CHƯA HẾT THÌ KHÔNG SO. 13 ngày đầu tháng 10 so với trọn tháng 9 cũng là so lệch. Thà không
     có mũi tên còn hơn một mũi tên đọc ra điều không có thật.

  3. TIÊU HAO CHIA CHO KM CHUYẾN, KHÔNG CỘNG KM RỖNG. Số lít đo được là lít có hoá đơn gắn vào
     chuyến; quãng rỗng không có dòng chi phí dầu riêng. Cộng km rỗng vào mẫu thì tiêu hao đọc ra
     THẤP hơn sự thật — sai theo hướng đẹp lên.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip, TripCost, FuelNorm  # noqa: E402
from app.services import hieu_qua_xe as HQ  # noqa: E402

HOM_NAY = date(2026, 10, 13)          # ngày đo thật của vòng này


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _xe(db, bien="50F-017.37", cho=45, vao=date(2025, 1, 1)):
    v = Vehicle(plate=bien, seats=cho, ngay_vao_doi=vao)
    db.add(v); db.flush()
    return v


def _chuyen(db, v, ma, di, ve, kd, kc, dt=0.0, lit=0.0, tien_dau=0.0):
    t = Trip(ma_phieu=ma, vehicle_id=v.id, ngay_di=di, ngay_ve=ve, km_dau=kd, km_cuoi=kc,
             doanh_thu=dt, ten_tour="thử")
    db.add(t); db.flush()
    if lit:
        db.add(TripCost(trip_id=t.id, kind="dau", amount=tien_dau, lit=lit)); db.flush()
    return t


# ═══════════════════════ 1 · Ô CHỌN KỲ ═══════════════════════

def test_o_chon_ky_chi_liet_ke_ky_THAT_SU_co_chuyen(db):
    """Liệt kê đủ 12 tháng cho đẹp thì người đọc bấm vào tháng rỗng rồi lại tưởng màn hình hỏng."""
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 3, 2), date(2026, 3, 4), 1000, 1500)
    _chuyen(db, v, "B", date(2026, 9, 2), date(2026, 9, 4), 2000, 2500)
    assert HQ.ky_co_chuyen(db) == ["2026-09", "2026-03"], "mới nhất phải đứng trước"


def test_chua_co_chuyen_nao_thi_o_chon_ky_RONG_chu_khong_bia_ra_thang(db):
    assert HQ.ky_co_chuyen(db) == []


def test_moc_qua_khu_tra_so_cua_KY_AY_chu_khong_phai_cua_hom_nay(db):
    """Đây chính là việc vòng này sinh ra để làm."""
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 9, 2), date(2026, 9, 4), 1000, 1500, dt=9_000_000)
    t9 = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)
    t10 = HQ.theo_ky(db, HOM_NAY, hom_nay=HOM_NAY)
    assert t9["thang"]["ngay_xe_hoat_dong"] == 3
    assert t9["thang"]["doanh_thu"] == 9_000_000
    assert t10["thang"]["ngay_xe_hoat_dong"] is None, "tháng 10 chưa nạp chuyến nào"
    assert t10["thang"]["trong_vi_sao"] and "tháng 09/2026" in t10["thang"]["trong_vi_sao"]


# ═══════════════════════ 2 · SO VỚI KỲ TRƯỚC ═══════════════════════

def test_ky_truoc_LUON_cung_so_thang_voi_ky_dang_xem(db):
    assert HQ._ky_truoc("thang", date(2026, 10, 13), 1) == ["2026-09"]
    assert HQ._ky_truoc("thang", date(2026, 1, 5), 1) == ["2025-12"]
    # Quý 4 mới đi một tháng -> kỳ trước cũng LẤY MỘT THÁNG, không lấy trọn quý 3.
    assert HQ._ky_truoc("quy", date(2026, 10, 13), 1) == ["2026-07"]
    assert HQ._ky_truoc("quy", date(2026, 12, 31), 3) == ["2026-07", "2026-08", "2026-09"]
    assert HQ._ky_truoc("quy", date(2026, 2, 10), 2) == ["2025-10", "2025-11"]
    assert HQ._ky_truoc("nam", date(2026, 10, 13), 10) == [f"2025-{m:02d}" for m in range(1, 11)]


def test_ky_CHUA_HET_thi_KHONG_so_sanh_va_noi_ro_vi_sao(db):
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 10, 2), date(2026, 10, 4), 1000, 1500)
    o = HQ.theo_ky(db, HOM_NAY, hom_nay=HOM_NAY)["thang"]
    assert o["so_sanh"] is None
    assert o["chua_so_sanh_vi"] and "chưa hết" in o["chua_so_sanh_vi"]


def test_ky_DA_HET_thi_so_sanh_va_ra_dung_so_chenh(db):
    v = _xe(db)
    _chuyen(db, v, "T8", date(2026, 8, 2), date(2026, 8, 4), 1000, 1500, dt=5_000_000)   # 3 ngày
    _chuyen(db, v, "T9", date(2026, 9, 2), date(2026, 9, 6), 2000, 2500, dt=9_000_000)   # 5 ngày
    o = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["thang"]
    assert o["so_sanh"] is not None and o["chua_so_sanh_vi"] is None
    assert o["so_sanh"]["truoc"]["ngay_xe_hoat_dong"] == 3
    assert o["so_sanh"]["lech"]["ngay_xe_hoat_dong"] == 2
    assert o["so_sanh"]["lech"]["doanh_thu"] == 4_000_000


def test_mot_ben_khong_co_so_thi_de_TRONG_chu_khong_tru_ra_so_am(db):
    """Tháng trước rỗng không phải tháng trước bằng 0 — trừ ra là bịa một mức giảm chưa từng có."""
    v = _xe(db)
    _chuyen(db, v, "T9", date(2026, 9, 2), date(2026, 9, 6), 2000, 2500, dt=9_000_000)
    o = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["thang"]
    assert o["so_sanh"]["truoc"]["doanh_thu"] is None
    assert o["so_sanh"]["lech"]["doanh_thu"] is None


# ═══════════════════════ 3 · BA CHỈ SỐ THÊM ═══════════════════════

def test_tieu_hao_chia_cho_KM_CHUYEN_chu_khong_cong_km_rong(db):
    """Hai chuyến có khoảng hở 500 km. Mẫu số phải là 1.000 km chuyến, không phải 1.500."""
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, lit=50.0, tien_dau=1_000_000)
    _chuyen(db, v, "B", date(2026, 9, 10), date(2026, 9, 11), 2000, 2500, lit=50.0, tien_dau=1_000_000)
    o = HQ.chi_so(db, "2026-09")
    assert o["km_chay_rong"] == 500
    assert o["tieu_hao_l100"] == 10.0, "100 lít / 1.000 km chuyến = 10 L/100km"


def test_chua_ai_khai_nguong_thi_VAN_in_tieu_hao_va_noi_dang_cho_ai(db):
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, lit=50.0)
    o = HQ.chi_so(db, "2026-09")
    assert o["tieu_hao_l100"] == 10.0, "chưa có ngưỡng KHÔNG được giấu con số thật"
    assert o["tieu_hao_nguong_thieu"] == {"bo_phan": "Đội xe", "cua_nhap": "/doi-xe"}
    assert o["tieu_hao_vuot"] is None


def test_khai_nguong_roi_thi_xe_VUOT_duoc_goi_ten(db):
    v1 = _xe(db, "50F-017.37", cho=45)
    v2 = _xe(db, "50H-498.29", cho=45)
    _chuyen(db, v1, "A", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, lit=50.0)   # 10 L/100km
    _chuyen(db, v2, "B", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, lit=100.0)  # 20 L/100km
    db.add(FuelNorm(seats=45, l_100km=15.0)); db.flush()
    o = HQ.chi_so(db, "2026-09")
    assert o["tieu_hao_nguong_thieu"] is None
    assert [z["xe"] for z in o["tieu_hao_vuot"]] == ["50H-498.29"]
    assert o["tieu_hao_vuot"][0]["nguong"] == 15.0 and o["tieu_hao_vuot"][0]["tieu_hao"] == 20.0


def test_nguong_cua_so_cho_KHAC_khong_ap_nham_sang_xe_nay(db):
    """Khai ngưỡng cho xe 16 chỗ không được biến thành ngưỡng của xe 45 chỗ."""
    v = _xe(db, "50F-017.37", cho=45)
    _chuyen(db, v, "A", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, lit=100.0)  # 20 L/100km
    db.add(FuelNorm(seats=16, l_100km=9.0)); db.flush()
    o = HQ.chi_so(db, "2026-09")
    assert o["tieu_hao_vuot"] is None, "xe 45 chỗ chưa có ngưỡng thì không ai vượt ngưỡng nào cả"


def test_doanh_thu_loi_nhuan_cong_dung_qua_nhieu_ky(db):
    v = _xe(db)
    _chuyen(db, v, "T8", date(2026, 8, 2), date(2026, 8, 3), 1000, 1500, dt=5_000_000)
    _chuyen(db, v, "T9", date(2026, 9, 2), date(2026, 9, 3), 2000, 2500, dt=9_000_000)
    nam = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["nam"]
    assert nam["doanh_thu"] == 14_000_000


def test_ty_le_loi_nhuan_cua_QUY_tinh_LAI_tren_tong_chu_khong_lay_trung_binh(db):
    """Trung bình của hai tỷ lệ có mẫu khác nhau là một con số không nghĩa gì."""
    v = _xe(db)
    # Tháng 7 doanh thu 1 triệu, tháng 8 doanh thu 9 triệu — trung bình tỷ lệ sẽ lệch hẳn.
    _chuyen(db, v, "T7", date(2026, 7, 2), date(2026, 7, 3), 1000, 1500, dt=1_000_000,
            lit=10.0, tien_dau=500_000)
    _chuyen(db, v, "T8", date(2026, 8, 2), date(2026, 8, 3), 2000, 2500, dt=9_000_000,
            lit=10.0, tien_dau=500_000)
    q = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["quy"]
    t7, t8 = HQ.chi_so(db, "2026-07"), HQ.chi_so(db, "2026-08")
    tb = (t7["ty_le_loi_nhuan"] + t8["ty_le_loi_nhuan"]) / 2
    dung = round(q["loi_nhuan"] / q["doanh_thu"], 4)
    assert q["ty_le_loi_nhuan"] == dung
    assert q["ty_le_loi_nhuan"] != round(tb, 4), "không được lấy trung bình của hai tỷ lệ"


def test_tieu_hao_cua_QUY_cung_tinh_LAI_tren_tong_lit_va_tong_km(db):
    v = _xe(db)
    _chuyen(db, v, "T7", date(2026, 7, 2), date(2026, 7, 3), 1000, 1100, lit=20.0)   # 100 km, 20 L
    _chuyen(db, v, "T8", date(2026, 8, 2), date(2026, 8, 3), 2000, 2900, lit=90.0)   # 900 km, 90 L
    q = HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["quy"]
    assert q["tieu_hao_l100"] == 11.0, "110 lít / 1.000 km = 11,0 — không phải (20+10)/2"


def test_ba_chi_so_moi_nam_trong_hop_dong_cua_CA_chi_so_LAN_theo_ky(db):
    v = _xe(db)
    _chuyen(db, v, "A", date(2026, 9, 2), date(2026, 9, 3), 1000, 1500, dt=9_000_000, lit=50.0)
    for o in (HQ.chi_so(db, "2026-09"),
              HQ.theo_ky(db, date(2026, 9, 30), hom_nay=HOM_NAY)["quy"]):
        for k in ("doanh_thu", "loi_nhuan", "ty_le_loi_nhuan", "tieu_hao_l100",
                  "tieu_hao_nguong_thieu", "tieu_hao_vuot"):
            assert k in o, k
