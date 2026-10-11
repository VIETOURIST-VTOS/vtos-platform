# -*- coding: utf-8 -*-
"""HX-1 · Cửa nạp hồ sơ xe — chỗ chặn thật của việc nạp 9 tháng dữ liệu đội xe.

Đo ngày 11/10/2026: đội xe có SÁU cửa nạp (chuyến xe, nhiên liệu, phí cầu đường, bảo dưỡng, đăng
kiểm, chi phí kỳ) và KHÔNG có cửa nào nạp danh mục xe. Đó là cửa phải vào TRƯỚC TIÊN, vì cửa
`chuyen_xe` tra biển số về xe qua danh mục: xe không có trong danh mục thì 1.051 lượt nạp vào mà
không gắn được về chiếc nào.

Sheet `THEO DÕI CP` trong tệp quyết toán T5/T6 có đủ cho 23 xe: loại xe, số khung, số máy, hạn bảo
hiểm, giá bảo hiểm năm, tiền sim, hạn sim, số thẻ đổ dầu, đuôi thẻ. VTOS giữ được số khung; số máy
thì không có cột.

BỐN RANH GIỚI tệp này canh, và mỗi cái là một cách cửa nạp có thể làm hỏng dữ liệu:

  1. Cửa KHÔNG tạo xe mới. Một dòng gõ sai biển số sẽ sinh ra chiếc xe thứ 24 trong đội, và từ đó
     mọi báo cáo công suất chia cho một mẫu số sai mà không ai thấy.
  2. Ghi số ghế là XÁC NHẬN nó — lưu luôn ai xác nhận và lúc nào. `seats` mặc định 45 nên một chiếc
     chưa ai nhập đọc ra đúng y một chiếc 45 chỗ thật.
  3. Thẻ dầu ghi cho TÀI XẾ, không gắn vào xe. Quyết định Đợt 2 đội xe, Chủ tịch giữ nguyên
     11/10/2026: đổi tài xế mà thẻ gắn vào xe thì mọi giao dịch thẻ sau ngày bàn giao gán nhầm chi
     phí sang người khác. Sheet nguồn xếp thẻ theo DÒNG XE, nên cửa phải đọc từ dòng xe mà ghi sang
     người — và nói ra khi xe chưa có tài xế.
  4. GIÁ bảo hiểm KHÔNG nạp ở cửa bảo hiểm. Nó là tiền, đi qua cửa chi phí kỳ. Một khoản một cửa.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hx1.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.hr import Vehicle, Employee
from app.models.fleet import VehicleDocument
from app.services import intake as IN


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _xe(db):
    return db.execute(select(Vehicle).where(Vehicle.active == True).order_by(Vehicle.id)).scalars().first()


def _kiem(db, loai, rows):
    bo = IN.BO_NAP[loai]
    return [bo["kiem"](db, r) for r in rows]


def _nap(db, loai, r, boi="gd_doi_xe"):
    return IN.BO_NAP[loai]["nap"](db, r, boi)


# ─────────────────────────────────── Cửa có mặt và khai đúng
def test_hai_cua_moi_co_mat_va_thuoc_doi_xe():
    for loai in ("ho_so_xe", "bao_hiem_xe"):
        assert loai in IN.BO_NAP, f"chưa khai cửa {loai}"
        assert IN.BO_NAP[loai]["phong_ban"] == "doi_xe"
    assert IN.BO_NAP["ho_so_xe"]["bang_dich"] == "vehicles"
    assert IN.BO_NAP["bao_hiem_xe"]["bang_dich"] == "vehicle_documents"


def test_cua_ho_so_xe_khong_nam_trong_nhom_cham_tien():
    """Cửa này cố ý KHÔNG mang tiền — giá bảo hiểm đi qua cửa chi phí kỳ."""
    from app.services.intake_phong_ban_2 import CHAM_TIEN
    assert "ho_so_xe" not in CHAM_TIEN
    assert "bao_hiem_xe" not in CHAM_TIEN
    cot = {c["key"] for c in IN.BO_NAP["bao_hiem_xe"]["cot"]}
    assert "so_tien" not in cot and "gia_bao_hiem" not in cot, \
        "giá bảo hiểm phải đi qua cửa chi phí kỳ — ghi ở hai nơi là có ngày hai nơi nói khác nhau"


# ─────────────────────────────────── Ranh giới 1: không tạo xe mới
def test_bien_so_la_thi_TU_CHOI_chu_khong_tao_xe_moi(_startup):
    with SessionLocal() as db:
        truoc = len(db.execute(select(Vehicle)).scalars().all())
        loi, cb, trung = _kiem(db, "ho_so_xe", [{"bien_so": "99Z-999.99", "so_may": "X"}])[0]
        assert loi and "KHÔNG tạo xe mới" in loi[0]
        assert len(db.execute(select(Vehicle)).scalars().all()) == truoc
        db.rollback()


# ─────────────────────────────────── Ranh giới 2: ghi số ghế là xác nhận
def test_ghi_so_ghe_la_XAC_NHAN_co_nguoi_va_co_luc(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        assert not (v.seats_xac_nhan_boi or "").strip()
        _nap(db, "ho_so_xe", {"bien_so": v.plate, "so_ghe": 29}, boi="gd_doi_xe")
        db.refresh(v)
        assert v.seats == 29
        assert v.seats_xac_nhan_boi == "gd_doi_xe"
        assert v.seats_xac_nhan_luc is not None
        db.rollback()


def test_khong_ghi_so_ghe_thi_GIU_so_cu_va_van_la_chua_xac_nhan(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        cu = v.seats
        loi, cb, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "so_may": "ABC"}])[0]
        assert not loi
        assert any("CHƯA AI XÁC NHẬN" in c for c in cb), "phải nói ra là vẫn chưa ai xác nhận số ghế"
        _nap(db, "ho_so_xe", {"bien_so": v.plate, "so_may": "ABC"})
        db.refresh(v)
        assert v.seats == cu and not (v.seats_xac_nhan_boi or "").strip()
        assert v.engine_no == "ABC"
        db.rollback()


def test_doi_so_ghe_thi_NOI_RA_con_so_cu(_startup):
    """Đổi số ghế là đổi mẫu số của mọi phép 'đủ xe cho tour' — người nạp phải thấy mình sửa cái gì."""
    with SessionLocal() as db:
        v = _xe(db)
        loi, cb, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "so_ghe": 29}])[0]
        assert not loi
        assert any(f"{v.seats} → 29" in c for c in cb)
        db.rollback()


def test_so_ghe_vo_ly_thi_tu_choi(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        for n in (0, 101):
            loi, _, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "so_ghe": n}])[0]
            assert loi, f"số ghế {n} lẽ ra bị từ chối"
        db.rollback()


# ─────────────────────────────────── Ranh giới 3: thẻ dầu ghi cho người
def test_the_dau_ghi_cho_TAI_XE_chu_khong_gan_vao_xe(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        e = db.execute(select(Employee).order_by(Employee.id)).scalars().first()
        v.driver_id = e.id; e.fuel_card_last4 = ""; db.flush()
        _nap(db, "ho_so_xe", {"bien_so": v.plate, "the_dau_4so": "1753"})
        db.refresh(e)
        assert e.fuel_card_last4 == "1753", "thẻ không được ghi cho tài xế"
        cot = {c.name for c in Vehicle.__table__.columns}
        assert not any("fuel" in c or "the_dau" in c for c in cot), \
            "bảng xe mọc cột thẻ dầu — thẻ gắn với NGƯỜI (quyết định Đợt 2, Chủ tịch giữ 11/10/2026)"
        db.rollback()


def test_xe_chua_co_tai_xe_thi_NOI_RA_chu_khong_bo_the_di_im_lang(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        v.driver_id = None; db.flush()
        loi, cb, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "the_dau_4so": "1753"}])[0]
        assert not loi, "không chặn — vẫn nạp được phần còn lại của dòng"
        assert any("chưa gán tài xế" in c and "thẻ dầu" in c for c in cb)
        db.rollback()


def test_mot_the_khong_gan_cho_hai_nguoi(_startup):
    """Tiền dầu gán theo bốn số cuối thẻ. Hai người một thẻ là gán tiền sang người không dùng thẻ."""
    with SessionLocal() as db:
        es = db.execute(select(Employee).order_by(Employee.id)).scalars().all()[:2]
        v = _xe(db)
        es[0].fuel_card_last4 = "9999"
        v.driver_id = es[1].id; db.flush()
        loi, _, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "the_dau_4so": "9999"}])[0]
        assert loi and "đã gắn cho một người khác" in loi[0]
        db.rollback()


def test_the_phai_dung_bon_chu_so(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        for x in ("175", "17533", "17a3"):
            loi, _, _ = _kiem(db, "ho_so_xe", [{"bien_so": v.plate, "the_dau_4so": x}])[0]
            assert loi, f"'{x}' lẽ ra bị từ chối"
        db.rollback()


# ─────────────────────────────────── Cửa bảo hiểm xe
def test_bao_hiem_rong_han_la_CHUA_BIET_chu_khong_phai_con_han(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        loi, cb, _ = _kiem(db, "bao_hiem_xe", [{"bien_so": v.plate, "so_giay": "BH-1"}])[0]
        assert not loi
        assert any("chưa đủ dữ liệu" in c for c in cb), \
            "rỗng ngày hết hạn phải nói là chưa biết, không được hiện màu xanh"
        db.rollback()


def test_bao_hiem_moi_thi_giay_cu_thoi_hieu_luc_nhung_KHONG_bi_xoa(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        h1 = date.today() + timedelta(days=30)
        h2 = date.today() + timedelta(days=395)
        _nap(db, "bao_hiem_xe", {"bien_so": v.plate, "so_giay": "BH-CU", "ngay_het_han": h1.isoformat()})
        _nap(db, "bao_hiem_xe", {"bien_so": v.plate, "so_giay": "BH-MOI", "ngay_het_han": h2.isoformat()})
        ds = db.execute(select(VehicleDocument).where(
            VehicleDocument.vehicle_id == v.id, VehicleDocument.kind == "bao_hiem")).scalars().all()
        assert len(ds) == 2, "giấy cũ bị xoá mất — mất luôn khả năng chứng minh đã có bảo hiểm kỳ trước"
        cu = next(d for d in ds if d.number == "BH-CU")
        moi = next(d for d in ds if d.number == "BH-MOI")
        assert cu.active is False and moi.active is True
        db.rollback()


def test_bao_hiem_het_han_truoc_ngay_cap_thi_tu_choi(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        loi, _, _ = _kiem(db, "bao_hiem_xe", [{"bien_so": v.plate, "so_giay": "BH-X",
                                               "ngay_cap": "2026-06-01",
                                               "ngay_het_han": "2026-01-01"}])[0]
        assert loi and "trước ngày cấp" in loi[0]
        db.rollback()


def test_nap_lai_cung_so_giay_thi_bao_trung(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        _nap(db, "bao_hiem_xe", {"bien_so": v.plate, "so_giay": "BH-T",
                                 "ngay_het_han": (date.today() + timedelta(days=100)).isoformat()})
        loi, cb, trung = _kiem(db, "bao_hiem_xe", [{"bien_so": v.plate, "so_giay": "BH-T"}])[0]
        assert trung is not None, "nạp lại cùng một giấy mà không báo trùng là chi phí nhân đôi"
        db.rollback()


# ─────────────────────────────────── Mọi bảng phải có cửa
def test_bang_vehicles_nay_da_co_cua_tai_tep(_startup):
    """Bảng `vehicles` trước đây chỉ có cửa nhập tay; nay có cả cửa tải tệp."""
    bang = {b["bang_dich"] for b in IN.BO_NAP.values()}
    assert "vehicles" in bang
