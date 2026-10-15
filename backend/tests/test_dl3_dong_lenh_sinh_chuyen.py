# -*- coding: utf-8 -*-
"""DL-3 · Đóng lệnh thì máy sinh chuyến — và KHÔNG sinh khi sinh là đếm hai lần.

CHỖ ĐỨT, đo từ mã nguồn 14/10/2026: cột `fleet_trips.dispatch_id` tồn tại, cửa tạo chuyến nhận
được nó, nhưng KHÔNG một đường nào ghi. Đo trên bản chạy thật: 756 chuyến, 1 lệnh.

LUẬT KHÓ NHẤT, và là lý do tệp này dài:

  TẠO MỚI KHI ĐÃ CÓ CHUYẾN LÀ CỘNG DOANH THU HAI LẦN — sai theo hướng ĐẸP LÊN, tức hướng khó bị
  phát hiện nhất. Nên ba mức: đã có thì thôi; khớp CẢ BỐN thì gắn; nghi khớp thì KHÔNG làm gì cả
  và đưa cho người. Chỉ khi không có cả ba, máy mới dựng dòng mới.
"""
import os
import re
import tempfile
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.models.hr import DispatchOrder, Employee, Vehicle  # noqa: E402
from app.services import dong_lenh as DL  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nen(db, ma_tour="DL-0825"):
    v = Vehicle(plate="50H-934.08", code="XE0013", seats=45)
    nv = Employee(code="NV1", full_name="Điều hành viên", department="Điều hành")
    tx = Employee(code="TX1", full_name="Phan Tấn Thuận", department="doi_xe")
    db.add_all([v, nv, tx]); db.flush()
    t = Tour(code=ma_tour, name="Phan Thiết 2N1Đ", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 8, 16), end_date=date(2026, 8, 18))
    db.add(t); db.flush()
    return v, tx, t


def _lenh(db, trang_thai="da_xac_nhan", gia=10_500_000):
    v, tx, t = _nen(db)
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=tx.id,
                      date_from=date(2026, 8, 16), date_to=date(2026, 8, 18),
                      internal_price=gia, created_by="gd_doi_xe", status=trang_thai)
    db.add(d); db.flush()
    return d


# ═════════════════ 1 · SINH CHUYẾN ═════════════════

def test_dong_lenh_thi_SINH_dung_mot_chuyen(db):
    d = _lenh(db)
    kq = DL.dong(db, d, "chutich")
    assert kq["viec"] == "da_sinh"
    t = db.get(Trip, kq["chuyen_id"])
    assert t.dispatch_id == d.id
    assert t.vehicle_id == d.vehicle_id and t.driver_id == d.driver_id
    assert t.ngay_di == date(2026, 8, 16) and t.ngay_ve == date(2026, 8, 18)
    assert t.ten_tour == "Phan Thiết 2N1Đ"


def test_gia_noi_bo_thanh_DOANH_THU_va_co_DAU_NGUON(db):
    """Chủ tịch chốt 15/10/2026: chép sang, có đánh dấu nguồn. Số ấy do người lập lệnh khai —
    để trống thì mỗi chuyến máy sinh là một dòng doanh thu 0 kéo lãi lỗ xuống sai."""
    d = _lenh(db, gia=10_500_000)
    t = db.get(Trip, DL.dong(db, d)["chuyen_id"])
    assert float(t.doanh_thu) == 10_500_000
    assert t.nguon == DL.NGUON_LENH


def test_KHONG_chep_km_va_chi_phi(db):
    """Lệnh không có km thật, không dầu, không cầu đường. Mỗi con số một cửa nhập."""
    d = _lenh(db)
    t = db.get(Trip, DL.dong(db, d)["chuyen_id"])
    assert t.km_dau is None and t.km_cuoi is None and t.km_gps is None


# ═════════════════ 2 · KHÔNG SINH HAI LẦN ═════════════════

def test_dong_lenh_HAI_LAN_van_chi_mot_chuyen(db):
    d = _lenh(db)
    a = DL.dong(db, d)
    b = DL.dong(db, d)
    assert a["viec"] == "da_sinh" and b["viec"] == "da_co"
    assert b["chuyen_id"] == a["chuyen_id"]
    assert db.execute(sa.select(sa.func.count()).select_from(Trip)).scalar() == 1


def test_CO_SO_DU_LIEU_cung_chan_lenh_hai_chuyen(db):
    """Hàng rào THỨ HAI. Phép soát của lớp dịch vụ ĐỌC RỒI GHI, nên hai lần bấm gần nhau cùng
    lọt. Phép thử này ghi THẲNG vào bảng, bỏ qua mọi lớp dịch vụ — đúng chỗ chỉ mục duy nhất
    phải đỡ."""
    d = _lenh(db)
    DL.dong(db, d); db.commit()
    db.add(Trip(vehicle_id=d.vehicle_id, dispatch_id=d.id,
                ngay_di=date(2026, 8, 16), ngay_ve=date(2026, 8, 18)))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_lenh_HUY_thi_khong_sinh(db):
    d = _lenh(db, trang_thai="huy")
    assert DL.dong(db, d)["viec"] == "bo_qua"
    assert db.execute(sa.select(sa.func.count()).select_from(Trip)).scalar() == 0


# ═════════════════ 3 · GẶP CHUYẾN ĐÃ NẠP: GẮN hay CHỈ BÁO ═════════════════

def test_khop_CA_BON_thi_GAN_chu_khong_tao_them(db):
    d = _lenh(db)
    t = Trip(vehicle_id=d.vehicle_id, tour_id=d.tour_id, ten_tour="Phan Thiết 2N1Đ",
             ngay_di=d.date_from, ngay_ve=d.date_to, doanh_thu=10_500_000)
    db.add(t); db.flush()
    kq = DL.dong(db, d)
    assert kq["viec"] == "da_gan" and kq["chuyen_id"] == t.id
    assert db.execute(sa.select(sa.func.count()).select_from(Trip)).scalar() == 1
    assert t.dispatch_id == d.id


def test_LECH_mot_trong_bon_thi_KHONG_gan_KHONG_tao(db):
    """Chủ tịch chốt 15/10/2026: nghi khớp thì đưa cho người. Tự gắn là nối nhầm hai chuyến khác
    nhau; tự tạo là đếm doanh thu hai lần. Cả hai đều sai, nên máy dừng lại."""
    d = _lenh(db)
    t = Trip(vehicle_id=d.vehicle_id, tour_id=d.tour_id, ten_tour="Phan Thiết 2N1Đ",
             ngay_di=d.date_from, ngay_ve=date(2026, 8, 19), doanh_thu=10_500_000)
    db.add(t); db.flush()
    kq = DL.dong(db, d)
    assert kq["viec"] == "nghi_trung"
    assert t.dispatch_id is None
    assert db.execute(sa.select(sa.func.count()).select_from(Trip)).scalar() == 1


def test_cua_GAN_TAY_la_cho_nguoi_xac_nhan(db):
    d = _lenh(db)
    t = Trip(vehicle_id=d.vehicle_id, tour_id=d.tour_id, ten_tour="x",
             ngay_di=d.date_from, ngay_ve=date(2026, 8, 19))
    db.add(t); db.flush()
    assert DL.dong(db, d)["viec"] == "nghi_trung"
    DL.gan_tay(db, d, t)
    assert t.dispatch_id == d.id
    with pytest.raises(ValueError):
        DL.gan_tay(db, d, t)


# ═════════════════ 4 · HAI CON SỐ ĐẾM ═════════════════

def test_hai_con_so_dem_dung_cho_ho(db):
    d = _lenh(db, trang_thai="hoan_thanh")
    assert DL.lenh_xong_chua_co_chuyen(db)["so"] == 1
    db.add(Trip(vehicle_id=d.vehicle_id, ngay_di=date(2026, 1, 1), ngay_ve=date(2026, 1, 2)))
    db.flush()
    assert DL.chuyen_chua_gan_lenh(db)["so"] == 1
    DL.dong(db, d)
    assert DL.lenh_xong_chua_co_chuyen(db)["so"] == 0
    assert DL.chuyen_chua_gan_lenh(db)["so"] == 1     # dòng sổ cũ vẫn chưa gắn, đúng


# ═════════════════ 5 · MÀN HÌNH ═════════════════

def test_man_hinh_co_doc_hai_con_so_ay():
    """Đo được mà không ai nhìn thấy thì chỗ hở sẽ ở lại mãi."""
    p = Path(__file__).resolve().parents[2] / "web" / "app" / "lenh-dieu-xe" / "page.tsx"
    assert p.exists()
    tsx = p.read_text(encoding="utf-8")
    assert "/dispatch/chuoi-lenh-chuyen" in tsx
    assert "lenh_xong_chua_co_chuyen" in tsx and "chuyen_chua_gan_lenh" in tsx
