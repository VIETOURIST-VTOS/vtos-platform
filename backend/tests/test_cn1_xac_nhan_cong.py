# -*- coding: utf-8 -*-
"""CN-1 · Xác nhận công tháng (Chủ tịch chốt 21/10/2026).

Canh:
  · phạm vi: phòng chấm công + phòng báo cáo ngày; Hướng dẫn và Đội xe KHÔNG áp dụng;
  · hai bước đúng vai: HCNS xác nhận → TGĐ (hoặc Chủ tịch) duyệt; vai khác bị từ chối;
  · sửa công sau khi duyệt thì xác nhận HẾT HIỆU LỰC (bẻ ngược: bỏ phép so dấu thì đỏ);
  · bảng lương chỉ chặn phòng có người trong bảng mà công chưa duyệt;
  · chuông: từ ngày 1 tháng sau, đỏ sau ngày 3, chuyển bước khi HCNS xác nhận, đóng khi duyệt;
  · ô «Được xác nhận công» của hồ sơ nhân viên.
"""
import os, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
import app.models  # noqa: F401
from app.models.core import Alert, User
from app.models.hr import Employee
from app.models.ops import DailyReport
from app.services import hrm as H
from app.services import xac_nhan_cong as X

KY = "2026-09"


@pytest.fixture()
def db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for un, vai in (("hcns1", "hcns"), ("tgd1", "tgd"), ("ct1", "chutich"), ("tp1", "tp_dh")):
        s.add(User(username=un, full_name=un, role=vai, password_hash="x", active=True))
    s.flush()
    nv = User(username="nvdh", full_name="NV ĐH", role="nv_dh", password_hash="x", active=True)
    s.add(nv); s.flush()
    s.add_all([Employee(code="KT1", full_name="Kế toán 1", department="ketoan", active=True),
               Employee(code="DH1", full_name="ĐH 1", department="dieu_hanh", user_id=nv.id, active=True),
               Employee(code="HD1", full_name="HDV 1", department="huong_dan", active=True)])
    s.commit()
    yield s
    s.close()


def _u(db, un):
    return db.execute(select(User).where(User.username == un)).scalars().one()


def _e(db, ma):
    return db.execute(select(Employee).where(Employee.code == ma)).scalars().one()


def test_cn1_1_pham_vi_lay_tu_che_do_cong():
    ap = X.phong_ap_dung()
    assert {"ketoan", "hcns", "dieu_hanh", "kd_le", "visa"} <= set(ap)
    assert "huong_dan" not in ap and "doi_xe" not in ap, "Chủ tịch chốt bỏ qua Hướng dẫn và Đội xe"


def test_cn1_2_hai_buoc_dung_vai(db):
    with pytest.raises(PermissionError):
        X.hcns_xac_nhan(db, _u(db, "tgd1"), KY, "ketoan")
    with pytest.raises(X.LoiXacNhan):
        X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")          # HCNS chưa xác nhận
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    assert X.trang_thai(db, KY, "ketoan")["trang_thai"] == "hcns_xac_nhan"
    with pytest.raises(PermissionError):
        X.tgd_duyet(db, _u(db, "hcns1"), KY, "ketoan")
    with pytest.raises(PermissionError):
        X.tgd_duyet(db, _u(db, "tp1"), KY, "ketoan")             # đơn nghỉ là của TP, công thì không
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    t = X.trang_thai(db, KY, "ketoan")
    assert t["trang_thai"] == "da_duyet" and t["tgd_by"] == "tgd1"
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "dieu_hanh")
    X.tgd_duyet(db, _u(db, "ct1"), KY, "dieu_hanh")              # Chủ tịch duyệt được
    with pytest.raises(X.LoiXacNhan):
        X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "huong_dan")


def test_cn1_3_sua_cong_sau_khi_duyet_thi_het_hieu_luc(db):
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    H.set_attendance(db, _u(db, "hcns1"), _e(db, "KT1").id, date(2026, 9, 8), "khong_luong", 0, 0, "")
    assert X.trang_thai(db, KY, "ketoan")["trang_thai"] == "het_hieu_luc"
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    assert X.trang_thai(db, KY, "ketoan")["trang_thai"] == "hcns_xac_nhan", "xác nhận lại xoá chữ duyệt cũ"
    H.set_attendance(db, _u(db, "hcns1"), _e(db, "KT1").id, date(2026, 9, 9), "khong_luong", 0, 0, "")
    with pytest.raises(X.LoiXacNhan, match="đã đổi"):
        X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")


def test_cn1_4_bao_cao_ngay_dem_dung(db):
    nv = _u(db, "nvdh")
    db.add_all([DailyReport(user_id=nv.id, report_date=date(2026, 9, 1), on_time=True, manager_score=8),
                DailyReport(user_id=nv.id, report_date=date(2026, 9, 2), on_time=False)])
    db.commit()
    d = X.so_lieu(db, KY, "dieu_hanh")[0]
    assert (d["ngay_bao_cao"], d["dung_gio"], d["tp_da_cham"]) == (2, 1, 1)
    assert "ngày không báo cáo" in d["can_xem"]
    # «cần xem» là lời nhắc suy ra — không vào dấu, nên sang ngày mới không làm hết hiệu lực.
    assert X.van_tay([{**d, "can_xem": "khác"}]) == X.van_tay([d])


def test_cn1_5_bang_luong_chi_chan_phong_co_nguoi_trong_bang(db):
    chua = X.phong_chua_duyet(db, KY, ["KT1", "HD1"])
    assert [t["phong"] for t in chua] == ["ketoan"], "Hướng dẫn không áp dụng; Điều hành không có người trong bảng"
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    assert [t["phong"] for t in X.phong_chua_duyet(db, KY, ["KT1"])] == ["ketoan"], "HCNS xác nhận chưa đủ"
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    assert X.phong_chua_duyet(db, KY, ["KT1", "HD1"]) == []


def _chuong(db, kind):
    return db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == f"cong:{KY}:ketoan",
                                          Alert.resolved == False)).scalars().all()  # noqa: E712


def test_cn1_6_chuong_theo_buoc_va_han(db):
    X.quet(db, hom_nay=date(2026, 10, 2))
    a = _chuong(db, X.CHUONG_HCNS)
    assert len(a) == 1 and a[0].level == "warn" and a[0].to_roles == "hcns"
    X.quet(db, hom_nay=date(2026, 10, 2))
    assert len(_chuong(db, X.CHUONG_HCNS)) == 1, "quét lại không sinh chuông trùng"
    X.quet(db, hom_nay=date(2026, 10, 4))
    a = _chuong(db, X.CHUONG_HCNS)
    assert len(a) == 1 and a[0].level == "red", "quá ngày 3 thì chuông đỏ"
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    assert not _chuong(db, X.CHUONG_HCNS) and len(_chuong(db, X.CHUONG_TGD)) == 1
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    X.quet(db, hom_nay=date(2026, 10, 4))
    assert not _chuong(db, X.CHUONG_HCNS) and not _chuong(db, X.CHUONG_TGD)


def test_cn1_7_o_ho_so_nhan_vien(db):
    hn = date(2026, 10, 5)
    assert X.cho_ho_so(db, _e(db, "HD1"), hn).startswith("Không áp dụng")
    assert "chưa xác nhận" in X.cho_ho_so(db, _e(db, "KT1"), hn)
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    assert X.cho_ho_so(db, _e(db, "KT1"), hn).startswith(f"Kỳ {KY}: đã duyệt (tgd1")


def test_cn1_8_ky_tuong_lai_bi_tu_choi(db):
    with pytest.raises(X.LoiXacNhan):
        X.hcns_xac_nhan(db, _u(db, "hcns1"), "2099-01", "ketoan")


def test_cn1_9_be_nguoc_bo_so_dau_thi_do(db, monkeypatch):
    """Bẻ ngược: dấu không đổi theo số (như một bản quên so dấu) thì phép 3 phải bắt được."""
    X.hcns_xac_nhan(db, _u(db, "hcns1"), KY, "ketoan")
    X.tgd_duyet(db, _u(db, "tgd1"), KY, "ketoan")
    monkeypatch.setattr(X, "van_tay", lambda d: "co_dinh")
    x = X._dong(db, KY, "ketoan"); x.van_tay = "co_dinh"; db.commit()
    H.set_attendance(db, _u(db, "hcns1"), _e(db, "KT1").id, date(2026, 9, 8), "khong_luong", 0, 0, "")
    assert X.trang_thai(db, KY, "ketoan")["trang_thai"] == "da_duyet", \
        "không so dấu thì sửa công không bị phát hiện — đúng cái phép 3 canh"
