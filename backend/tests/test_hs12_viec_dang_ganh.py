# -*- coding: utf-8 -*-
"""HS-12 · Việc đang gánh, tách theo loại (Chủ tịch duyệt bản xem thử 18/10/2026).

Sáu con số của nhóm 6 trong hồ sơ nhân viên trước đây nằm trong `thieu_nguon`. Vòng này dựng
nguồn cho chúng, và các phép thử dưới đây canh ba chỗ dễ sai nhất:

  · «Quyết toán đang giữ» phải đi qua ĐÚNG cổng `chu_ho_so` — tour đoàn về Sale Admin, tour lẻ
    về Điều hành, và hồ sơ đã bàn giao thì về người nhận (Chủ tịch chọn giữ luật bàn giao).
    Một luật thứ hai viết tay ở đây là ngày hai màn hình nói hai người khác nhau.
  · «Đang mở» và «từ trước tới nay» là hai số khác nhau; việc đã huỷ không vào số nào.
  · Tài khoản chưa nối hồ sơ nhân sự thì lệnh xe là None («—»), không phải 0.
"""
import datetime as dt
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Param, Tour, User
from app.models.hr import DispatchOrder, Employee, Vehicle
from app.models.to_chuc_kd import DonViKD, PhanCongKD
from app.models.visa import VisaCase
from app.services import chu_ho_so as CHS
from app.services import ho_so_nhan_vien as HSNV
from app.services import rules as R

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("dh2", "nv_dh"), ("sa", "sales_admin"), ("kd", "nv_kd"),
                     ("visa", "nv_visa"), ("tx", "nv_dh")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    R.clear_param_cache()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


_n = [0]


def _tour(db, nguoi, loai="le_noi_dia", trang_thai="da_duyet", chu=None):
    _n[0] += 1
    ma = ("MICE-" if loai.startswith("doan") else "LE-") + str(_n[0])
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=HOM_NAY, end_date=HOM_NAY,
             operator_id=_u(db, nguoi).id, status=trang_thai, planned_pax=1,
             chu_ho_so_id=_u(db, chu).id if chu else None)
    db.add(t); db.commit(); db.refresh(t)
    return t


def _dat_sale_admin_doan(db):
    db.add(Param(key="chu_ho_so_doan", value="sa", label="Chủ hồ sơ quyết toán mảng Đoàn",
                 unit="tài khoản", effective_from=date(2026, 1, 1), status="active"))
    db.commit()
    R.clear_param_cache()
    CHS.quen_nho(db)


def _dem(db, ten, e=None):
    return HSNV.dem_viec_dang_ganh(db, _u(db, ten), e)


def test_hs12_1_tour_dieu_hanh_dem_hai_so_bo_tour_huy():
    db = _db()
    _tour(db, "dh", trang_thai="da_duyet")
    _tour(db, "dh", trang_thai="ket_thuc")
    _tour(db, "dh", trang_thai="khoa")
    _tour(db, "dh", trang_thai="huy")
    assert _dem(db, "dh")["so_tour"] == {"dang_mo": 2, "tong": 3}


def test_hs12_2_quyet_toan_doan_ve_sale_admin_le_ve_dieu_hanh():
    db = _db()
    _dat_sale_admin_doan(db)
    _tour(db, "dh", loai="doan_noi_dia", trang_thai="ket_thuc")
    _tour(db, "dh", loai="doan_noi_dia", trang_thai="da_dong_so")
    _tour(db, "dh", loai="le_noi_dia", trang_thai="ket_thuc")
    sa, dh = _dem(db, "sa"), _dem(db, "dh")
    assert sa["so_quyet_toan_giu"] == {"dang_mo": 1, "tong": 2}, (
        "Tour đoàn chưa chỉ đích danh ai thì quyết toán về Sale Admin theo tham số chu_ho_so_doan.")
    assert dh["so_quyet_toan_giu"] == {"dang_mo": 1, "tong": 1}, (
        "Điều hành chỉ giữ quyết toán tour lẻ; tour đoàn đã về Sale Admin.")
    assert dh["so_tour"]["tong"] == 3, "Dòng tour điều hành vẫn đếm cả tour đoàn — thưởng chuyến đi theo nó."


def test_hs12_3_ban_giao_thang_mac_dinh():
    db = _db()
    _dat_sale_admin_doan(db)
    _tour(db, "dh", loai="doan_noi_dia", trang_thai="ket_thuc", chu="dh2")
    _tour(db, "dh", loai="le_noi_dia", trang_thai="ket_thuc", chu="dh2")
    assert _dem(db, "dh2")["so_quyet_toan_giu"] == {"dang_mo": 2, "tong": 2}
    assert _dem(db, "sa")["so_quyet_toan_giu"]["tong"] == 0
    assert _dem(db, "dh")["so_quyet_toan_giu"]["tong"] == 0


def test_hs12_4_khop_tung_chuyen_voi_cong_chu_ho_so():
    """Không được có luật thứ hai: tổng của mọi người phải bằng số chuyến, và mỗi chuyến đúng
    một người — chính người cổng `chu_ho_so` trả về."""
    db = _db()
    _dat_sale_admin_doan(db)
    for loai, chu in (("doan_noi_dia", None), ("le_noi_dia", None), ("doan_nuoc_ngoai", "dh2"),
                      ("le_nuoc_ngoai", "sa"), ("non_package", None)):
        _tour(db, "dh", loai=loai, trang_thai="ket_thuc", chu=chu)
    tong = sum(_dem(db, u)["so_quyet_toan_giu"]["tong"] for u in ("dh", "dh2", "sa", "kd"))
    assert tong == 5
    for t in db.execute(select(Tour)).scalars():
        ai = db.get(User, CHS.chu_ho_so(db, t)).username
        assert _dem(db, ai)["so_quyet_toan_giu"]["tong"] >= 1


def test_hs12_5_booking_visa_phan_cong():
    db = _db()
    t_mo = _tour(db, "dh", trang_thai="da_duyet")
    t_xong = _tour(db, "dh", trang_thai="khoa")
    kd = _u(db, "kd")
    for i, (t, huy) in enumerate(((t_mo, False), (t_mo, True), (t_xong, False))):
        db.add(Booking(code=f"BK{i}", tour_id=t.id, request_id=0, sales_id=kd.id, created_by=kd.id,
                       customer_name="x", customer_phone="x", source="x", cancelled=huy))
    vs = _u(db, "visa")
    for i, tt in enumerate(("ACTIVE", "ON_HOLD", "CLOSED", "CANCELLED")):
        db.add(VisaCase(case_code=f"V{i}", applicant_name="x", market_code="X",
                        visa_owner_user_id=vs.id, lifecycle_status=tt))
    dv = DonViKD(ma="KD1", ten="KD1", cap="phong", hieu_luc_tu=date(2026, 1, 1))
    db.add(dv); db.flush()
    db.add(PhanCongKD(user_id=kd.id, don_vi_id=dv.id, tu_ngay=date(2025, 1, 1),
                      den_ngay=date(2025, 12, 31)))
    db.add(PhanCongKD(user_id=kd.id, don_vi_id=dv.id, tu_ngay=date(2026, 1, 1)))
    db.commit()
    assert _dem(db, "kd")["so_booking"] == {"dang_mo": 1, "tong": 2}
    assert _dem(db, "visa")["so_visa"] == {"dang_mo": 2, "tong": 3}
    assert _dem(db, "kd")["so_phan_cong_kd"] == {"dang_mo": 1, "tong": 2}


def test_hs12_6_lenh_xe_none_khi_chua_noi_ho_so_va_dem_khi_co():
    db = _db()
    assert _dem(db, "tx")["so_lenh_xe"] is None, "Chưa nối hồ sơ nhân sự thì «—», không phải 0."
    e = Employee(code="TX1", full_name="tx", department="doi_xe", position="tai_xe", active=True)
    xe = Vehicle(plate="51B-00001")
    db.add_all([e, xe]); db.flush()
    t = _tour(db, "dh")
    for tt in ("cho_xac_nhan", "hoan_thanh", "huy"):
        db.add(DispatchOrder(tour_id=t.id, vehicle_id=xe.id, driver_id=e.id,
                             date_from=HOM_NAY, date_to=HOM_NAY, status=tt))
    db.commit()
    assert _dem(db, "tx", e)["so_lenh_xe"] == {"dang_mo": 1, "tong": 2}


def test_hs12_7_nhom_6_khai_du_sau_khoa():
    truong = HSNV.NHOM_THEO_MA["6"]["truong"]
    for k in ("so_tour", "so_quyet_toan_giu", "so_booking", "so_lenh_xe", "so_visa",
              "so_phan_cong_kd"):
        assert k in truong
