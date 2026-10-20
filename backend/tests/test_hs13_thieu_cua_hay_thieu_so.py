# -*- coding: utf-8 -*-
"""HS-13 · «Hệ thống chưa có cửa nhập» khác «người này chưa có số» (Chủ tịch duyệt 20/10/2026).

Canh ba điều:
  · bốn trường trước đây không nguồn (số quyền, xe đang gắn, được duyệt nghỉ, lý do nghỉ) nay máy
    tự tính, và tính ĐÚNG — đếm nghỉ chỉ đơn đã duyệt trong tháng, xe chỉ xe đang chạy;
  · trường có cửa mà thiếu số thì đi vào `chua_co_so_lieu` theo đúng cửa; chỉ «được xác nhận công»
    còn ở `thieu_nguon`;
  · phép canh ngược: ai bỏ một trường khỏi `CUA_NHAP` thì trường ấy QUAY VỀ «chưa có cửa» — không
    bao giờ lặng lẽ biến mất.
"""
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
import app.models  # noqa: F401  — nạp đủ bảng
from app.models.core import User
from app.models.hr import Employee, Vehicle
from app.models.hrm import LeaveRequest
from app.services import ho_so_nhan_vien as HS


@pytest.fixture()
def db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    yield s
    s.close()


def _nguoi(db, voi_ho_so=True):
    u = User(username="hs13", full_name="Thử HS13", role="nv_dh", department="dieu_hanh",
             staff_code="HS13", password_hash="x", active=True)
    db.add(u); db.flush()
    e = None
    if voi_ho_so:
        e = Employee(code="HS13", full_name="Thử HS13", department="dieu_hanh", user_id=u.id, active=True)
        db.add(e); db.flush()
    db.commit()
    return u, e


def test_hs13_1_bon_truong_may_tu_tinh(db):
    u, e = _nguoi(db)
    dau = date.today().replace(day=1)
    db.add_all([
        LeaveRequest(employee_id=e.id, date_from=dau, date_to=dau, days=1.5, reason="khám bệnh", status="duyet"),
        LeaveRequest(employee_id=e.id, date_from=dau, date_to=dau, days=4, reason="chưa duyệt", status="cho_duyet"),
        LeaveRequest(employee_id=e.id, date_from=dau - timedelta(days=40), date_to=dau - timedelta(days=40),
                     days=2, reason="tháng trước", status="duyet"),
        Vehicle(plate="51B-123.45", driver_id=e.id, active=True),
        Vehicle(plate="51B-999.99", driver_id=e.id, active=False),
    ])
    db.commit()
    hs, thieu = HS.thu_thap(db, u)
    assert hs["duoc_duyet_nghi"] == 1.5, "chỉ đơn ĐÃ DUYỆT trong THÁNG NÀY"
    assert hs["ly_do_nghi"] == "khám bệnh", "lý do của đơn đã duyệt gần nhất"
    assert hs["xe_dang_gan"] == "51B-123.45", "xe ngừng chạy không còn là xe đang gắn"
    assert hs["so_quyen"].endswith("ngoại lệ còn hạn") and "màn hình" in hs["so_quyen"]
    for k in ("so_quyen", "xe_dang_gan", "duoc_duyet_nghi", "ly_do_nghi"):
        assert k not in thieu


def test_hs13_2_chi_xac_nhan_cong_con_chua_co_cua(db):
    u, _ = _nguoi(db)
    hs, thieu_tat = HS.thu_thap(db, u)
    chua_cua, theo_cua = HS.phan_loai_thieu(thieu_tat, hs.pop("_khong_ho_so"))
    assert chua_cua == ["duoc_xac_nhan_cong"], chua_cua
    cua = {c["cua"]: c for c in theo_cua}
    assert "contract_type_hd" in cua["Hợp đồng lao động"]["truong"]
    assert cua["Hợp đồng lao động"]["duong"] == "/hop-dong-lao-dong"
    assert "id_number" in cua["Hồ sơ nhân sự"]["truong"]
    assert "diem_danh_gia" in cua["Đánh giá & sự vụ"]["truong"]
    # mỗi trường thiếu nằm ở ĐÚNG MỘT chỗ
    tat = chua_cua + [t for c in theo_cua for t in c["truong"]]
    assert sorted(tat) == sorted(thieu_tat)


def test_hs13_3_chua_noi_ho_so_thi_chi_ve_cua_noi_tai_khoan(db):
    u, _ = _nguoi(db, voi_ho_so=False)
    hs, thieu_tat = HS.thu_thap(db, u)
    chua_cua, theo_cua = HS.phan_loai_thieu(thieu_tat, hs.pop("_khong_ho_so"))
    assert chua_cua == ["duoc_xac_nhan_cong"]
    assert [c["duong"] for c in theo_cua] == ["/access"]


def test_hs13_4_bo_cua_thi_truong_quay_ve_chua_co_cua(monkeypatch):
    """Phép canh ngược: gỡ một trường khỏi CUA_NHAP thì nó phải hiện lại ở «chưa có cửa»."""
    monkeypatch.delitem(HS.CUA_NHAP, "contract_end")
    chua_cua, theo_cua = HS.phan_loai_thieu(["contract_end", "contract_type_hd"], False)
    assert chua_cua == ["contract_end"]
    assert theo_cua[0]["truong"] == ["contract_type_hd"]


def test_hs13_5_cua_nhap_chi_ke_truong_da_khai():
    da_khai = {c for n in HS.NHOM_TRUONG for c in n["truong"]}
    for k in list(HS.CUA_NHAP) + list(HS.KHONG_CO_CUA):
        assert k in da_khai, f"{k} không có trong NHOM_TRUONG"
