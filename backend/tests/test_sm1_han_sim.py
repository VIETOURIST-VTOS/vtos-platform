# -*- coding: utf-8 -*-
"""SM-1 · Hạn sim của xe — trường cuối còn thiếu của danh mục xe.

HẠN SIM KHÔNG PHẢI VIỆC GIẤY TỜ, và đó là cả điểm của đợt này. Xe hết đăng kiểm hay hết bảo hiểm
thì KHÔNG CHẠY ĐƯỢC. Sim hết hạn thì xe vẫn chạy — chỉ là cổng GPS tắt, và `km_nguon` của chuyến
mất đúng cái nguồn dùng để đối chiếu với km đồng hồ. Tháng sau không ai dựng lại được con số ấy.

HAI QUYẾT ĐỊNH CỦA CHỦ TỊCH 12/10/2026:
  1. `cong_gps` là một CỘT, không phải một câu trong ô ghi chú — vì lúc sim chết, câu hỏi ngay sau
     đó là "cổng nào, mất mấy xe", và chữ tự do thì không lọc được.
  2. Sim đứng DÒNG RIÊNG trên báo cáo phòng Đội xe — hai hậu quả khác nhau thì hai con số.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_sm1.db")
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
from app.models.fleet import VehicleDocument, CONG_GPS, KM_NGUON
from app.models.hr import Vehicle
from app.services import intake


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _xe(db):
    return db.execute(select(Vehicle)).scalars().first()


def _dong(db, **kw):
    r = {"bien_so": _xe(db).plate, "so_thue_bao": "0901234567", "cong_gps": "gps_ttc",
         "ngay_het_han": "01/03/2027"}
    r.update(kw)
    return r


# ───────────────────────────── Cổng GPS suy từ một bảng, không gõ lại
def test_CONG_GPS_suy_tu_KM_NGUON_chu_khong_go_lai():
    """Ngày nào đội xe thêm cổng thứ tư, thêm một dòng ở KM_NGUON là cả hai nơi cùng biết."""
    assert CONG_GPS == {k: v for k, v in KM_NGUON.items() if k.startswith("gps_")}
    assert set(CONG_GPS) == {"gps_ttc", "gps_tcd", "gps_vietmap"}


def test_cong_cu_gps_KHONG_phai_mot_cong_de_gan_sim():
    '''"gps" là cách ghi CŨ cho số km đã lỡ ghi, không phải một cổng có thật.'''
    assert "gps" in KM_NGUON and "gps" not in CONG_GPS


# ───────────────────────────── Cửa nạp
def test_cua_nap_sim_co_mat_va_thuoc_doi_xe(_startup):
    c = intake.BO_NAP["sim_xe"]
    assert c["bang_dich"] == "vehicle_documents" and c["phong_ban"] == "doi_xe"
    cot = {x["key"] for x in c["cot"]}
    assert {"bien_so", "so_thue_bao", "cong_gps", "ngay_het_han"} <= cot


def test_cong_gps_la_O_BAT_BUOC_va_chi_nhan_danh_muc(_startup):
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        loi, cb, _ = c["kiem"](db, _dong(db, cong_gps="Thành Công"))
        assert any("không có trong danh mục" in x for x in loi), loi
        loi, cb, _ = c["kiem"](db, _dong(db, cong_gps="gps_ttc"))
        assert not loi, loi
        db.rollback()


def test_khong_ghi_cong_thi_CANH_BAO_chu_khong_chan(_startup):
    """Chặn cứng là chặn đúng lượt nạp 9 tháng dữ liệu cũ, nơi không ai còn nhớ sim nào của cổng nào."""
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        loi, cb, _ = c["kiem"](db, _dong(db, cong_gps=""))
        assert not loi
        assert any("không ai biết cổng nào tắt" in x for x in cb), cb
        db.rollback()


def test_rong_ngay_het_han_la_CHUA_BIET_chu_khong_phai_con_han(_startup):
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        _, cb, _ = c["kiem"](db, _dong(db, ngay_het_han=""))
        assert any("chưa đủ dữ liệu" in x for x in cb), cb
        db.rollback()


def test_sim_da_het_han_thi_NOI_RA_hau_qua(_startup):
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        _, cb, _ = c["kiem"](db, _dong(db, ngay_het_han="01/01/2020"))
        assert any("cổng GPS của xe này có thể đang tắt" in x for x in cb), cb
        db.rollback()


def test_nap_ghi_dung_kind_va_cong(_startup):
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        c["nap"](db, _dong(db), "nguoi_nap")
        g = db.execute(select(VehicleDocument).where(VehicleDocument.kind == "sim")).scalars().first()
        assert g is not None and g.cong_gps == "gps_ttc" and g.number == "0901234567"
        db.rollback()


def test_gia_han_thi_sim_cu_THOI_HIEU_LUC_nhung_khong_bi_xoa(_startup):
    """Một chiếc xe từng mất GPS hai tháng là một dữ kiện có thật của quá khứ."""
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        c["nap"](db, _dong(db, ngay_het_han="01/03/2026"), "a")
        c["nap"](db, _dong(db, ngay_het_han="01/03/2027"), "a")
        ds = list(db.execute(select(VehicleDocument).where(VehicleDocument.kind == "sim")).scalars())
        assert len(ds) == 2, "bản cũ không được xoá"
        assert sum(1 for x in ds if x.active) == 1, "chỉ một bản còn hiệu lực"
        db.rollback()


def test_trung_so_thue_bao_cua_CUNG_XE_thi_bao(_startup):
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        c["nap"](db, _dong(db), "a")
        _, _, trung = c["kiem"](db, _dong(db))
        assert trung is not None
        db.rollback()


# ───────────────────────────── Báo cáo phòng: hai hậu quả, hai dòng
def test_bao_cao_doi_xe_co_DONG_SIM_RIENG(_startup):
    from app.services import bao_cao_phong as BC
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        c["nap"](db, _dong(db, ngay_het_han=(date.today() + timedelta(days=5)).strftime("%d/%m/%Y")), "a")
        tu, den, _ = BC.khoang("thang")
        ds = {x["ma"]: x for x in BC._doi_xe(db, tu, den)}
        assert "sim_xe" in ds, "sim phải có dòng riêng"
        # `ct()` của báo cáo phòng trả khoá "ma"/"gia_tri"; `_o()` của bàn làm việc trả
        # "khoa"/"so_luong". Hai khuôn khác nhau — em đã nhầm một lần ở đây, ghi lại để lần sau đọc
        # tên hàm trước khi gõ tên khoá.
        assert ds["sim_xe"]["gia_tri"] == 1
        assert "cổng GPS tắt" in ds["sim_xe"]["viec"]
        db.rollback()


def test_sim_KHONG_con_lan_vao_dong_giay_to(_startup):
    """Dòng giấy tờ khuyên 'xe hết đăng kiểm là không chạy được' — câu ấy nói sai về sim."""
    from app.services import bao_cao_phong as BC
    with SessionLocal() as db:
        c = intake.BO_NAP["sim_xe"]
        c["nap"](db, _dong(db, ngay_het_han=(date.today() + timedelta(days=5)).strftime("%d/%m/%Y")), "a")
        tu, den, _ = BC.khoang("thang")
        ds = {x["ma"]: x for x in BC._doi_xe(db, tu, den)}
        assert ds["giay_to"]["gia_tri"] == 0, "sim không được đếm vào dòng giấy tờ"
        db.rollback()


def test_sim_va_giay_to_dem_RIENG_khi_co_ca_hai(_startup):
    from app.services import bao_cao_phong as BC
    with SessionLocal() as db:
        v = _xe(db)
        gan = date.today() + timedelta(days=5)
        db.add(VehicleDocument(vehicle_id=v.id, kind="dang_kiem", number="DK-1", expires_on=gan))
        intake.BO_NAP["sim_xe"]["nap"](db, _dong(db, ngay_het_han=gan.strftime("%d/%m/%Y")), "a")
        db.flush()
        tu, den, _ = BC.khoang("thang")
        ds = {x["ma"]: x for x in BC._doi_xe(db, tu, den)}
        assert ds["giay_to"]["gia_tri"] == 1 and ds["sim_xe"]["gia_tri"] == 1
        db.rollback()
