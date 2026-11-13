# -*- coding: utf-8 -*-
"""R5-20 (Chủ tịch 14/11/2026 «1 và 2 ok»).
  1. Người bán (Chuyên viên, Trưởng nhóm, Trưởng phòng KD) không nhận cột chi phí / lợi nhuận / biên trong
     báo cáo bán hàng — máy chủ cắt, cả bản xem lẫn Excel (quyết 25/9/2026: KD Lẻ không liên quan giá vốn).
  2. Trưởng nhóm bấm được «đã xem» / «trả bổ sung» báo cáo ngày của người trong nhóm; người ngoài nhóm thì không.
"""
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

D = date(2026, 10, 27)
NOP = datetime(2026, 10, 27, 18, 0)
SAU = datetime(2026, 10, 28, 9, 0)
DAI = "Nội dung đủ dài trên hai mươi ký tự để tính điểm."


class _U:
    def __init__(self, role): self.role = role


def _rep():
    return {"summary": [{"tour_code": "T1", "revenue": 10, "cost": 6, "profit": 4, "margin": .4}], "detail": [],
            "total": {"revenue": 10, "cost": 6, "profit": 4},
            "columns": {"summary": [("tour_code", "Tour"), ("revenue", "Doanh thu"), ("cost", "Chi phí"),
                                    ("profit", "Lợi nhuận"), ("margin", "Biên")], "detail": []}}


@pytest.mark.parametrize("vai", ["nv_kd", "tn_kd", "tp_kd"])
def test_nguoi_ban_khong_nhan_gia_von(vai):
    from app.api.v1.sales_reports import _an_gia_von
    r = _rep(); _an_gia_von(_U(vai), r)
    assert [c[0] for c in r["columns"]["summary"]] == ["tour_code", "revenue"]
    assert set(r["summary"][0]) == {"tour_code", "revenue"} and set(r["total"]) == {"revenue"}


@pytest.mark.parametrize("vai", ["chutich", "ketoan", "tp_dh", "gd_kd"])
def test_vai_khac_giu_nguyen(vai):
    from app.api.v1.sales_reports import _an_gia_von
    r = _rep(); _an_gia_von(_U(vai), r)
    assert "cost" in r["summary"][0] and "profit" in r["total"]


def test_xuat_excel_cung_di_qua_cat():
    from pathlib import Path
    s = (Path(__file__).resolve().parents[1] / "app/api/v1/sales_reports.py").read_text(encoding="utf-8")
    run = s.split("def _run(")[1].split("\n@router")[0]
    assert "_an_gia_von(u, rep)" in run and "rep = _run(db, key, u," in s.split("def export_report(")[1]


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def _nguoi(db, ten, vai, nhom):
    from app.models.core import User
    from app.models.hr import Employee
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x", active=True, sales_group=nhom)
    db.add(u); db.flush()
    db.add(Employee(code=f"NV-{ten}", full_name=ten.upper(), department="kd_le", position="nv", user_id=u.id, active=True))
    db.flush()
    return u


def test_truong_nhom_xem_xet_nguoi_trong_nhom(db):
    from app.services import ops as O
    from app.services import bao_cao_ngay_xem as X
    tn = _nguoi(db, "tn.kd1", "tn_kd", "KD1")
    a = _nguoi(db, "nv.kd1", "nv_kd", "KD1")
    b = _nguoi(db, "nv.kd2", "nv_kd", "KD2")
    ra = O.submit_report(db, a, D, DAI, "{}", "", DAI, now=NOP)
    rb = O.submit_report(db, b, D, DAI, "{}", "", DAI, now=NOP)
    rt = O.submit_report(db, tn, D, DAI, "{}", "", DAI, now=NOP)
    db.commit()
    th = X.tong_hop(db, tn, D, now=SAU)
    dong = {d["ten"]: d for d in th["dong"]}
    assert dong["NV.KD1"]["xem_xet_duoc"] is True and th["xu_ly"]["cho_xem"] == 1
    assert dong["TN.KD1"]["xem_xet_duoc"] is False                     # không xem xét báo cáo của chính mình
    X.xem_xet(db, tn, ra, "bo_sung", ly_do="Bổ sung số khách gọi lại")
    assert X.trang_thai_xem(ra) == "can_bo_sung"
    with pytest.raises(PermissionError):
        X.xem_xet(db, tn, rb, "da_xem")                                 # ngoài nhóm
    with pytest.raises(PermissionError):
        X.xem_xet(db, tn, rt, "da_xem")                                 # của chính mình
