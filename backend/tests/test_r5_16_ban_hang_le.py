"""R5-16 · Chủ tịch duyệt 14/11/2026: tab «Bán hàng» Phòng KD Lẻ — bỏ Báo giá; «Lịch khởi hành» gộp vào Bàn bán
tour lẻ (phạm vi Đang bán / Sắp mở bán / Đã đi); «Giá & chính sách bán» → «Chính sách bán» (đọc thẳng D06 và VTD
Rewards); Dịch vụ lẻ thêm «Gửi khách – hưởng hoa hồng» (ghi giá khách trả + giá trả đối tác)."""
import datetime as dt
import json
import pathlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.ban_hang import ChinhSachBan
from app.models.core import SERVICE_KINDS, Booking, Tour, User
from app.services import ban_tour_le as BTL
from app.services import chinh_sach_ban as CSB
from app.services import nonpackage as NP

GOC = pathlib.Path(__file__).resolve().parents[2]
W = GOC / "web/components"
HOM = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("gd", "gd_kd"), ("tp", "tp_kd"), ("nv", "nv_kd"), ("dh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    return s


def _u(s, t):
    return s.execute(select(User).where(User.username == t)).scalars().first()


def test_ban_tab_ban_hang_bo_bao_gia_va_lich_khoi_hanh():
    for f in ("BanGdKdLe", "BanTpKd", "BanTnKd", "BanNvKd"):
        t = (W / f"{f}.tsx").read_text(encoding="utf-8")
        assert '/bao-gia?mang=kd_le"' not in t and 'ten: "Lịch khởi hành"' not in t and '"/bang-gia"' not in t, f
        assert 'toi: "/chinh-sach-ban"' in t and 'toi: "/non-package"' in t, f


def test_chinh_sach_ban_hanh_khep_ban_cu_va_rong_khong_phai_0():
    s = _db()
    with pytest.raises(HTTPException):
        CSB.ban_hanh(s, _u(s, "nv"), {"hieu_luc_tu": HOM.isoformat()})
    a = CSB.ban_hanh(s, _u(s, "gd"), {"hieu_luc_tu": (HOM - dt.timedelta(days=10)).isoformat(),
                                      "noi_dung": {"chiet_khau": {"nv_kd": "3"}, "tre_em": {"tre_em_pct": ""}}})
    assert a["noi_dung"]["chiet_khau"] == {"nv_kd": 3.0, "tn_kd": None, "tp_kd": None}
    assert a["noi_dung"]["tre_em"]["tre_em_pct"] is None, "ô trống = chưa ban hành, không phải 0"
    CSB.ban_hanh(s, _u(s, "tp"), {"hieu_luc_tu": HOM.isoformat(), "noi_dung": {"chiet_khau": {"nv_kd": 4}}})
    cu = s.get(ChinhSachBan, a["id"])
    assert cu.hieu_luc_den == HOM - dt.timedelta(days=1), "bản cũ khép, không xoá"
    tq = CSB.tong_hop(s, _u(s, "nv"))
    assert tq["hien_hanh"]["noi_dung"]["chiet_khau"]["nv_kd"] == 4.0 and len(tq["cac_ban"]) == 1
    assert not tq["duoc_ban_hanh"]
    lk = tq["lien_ket"]
    assert {"d06", "rewards"} <= set(lk) and lk["d06"]["bac"] and lk["rewards"]["hang"], "đọc thẳng D06 + Rewards"
    with pytest.raises(HTTPException):
        CSB.ban_hanh(s, _u(s, "gd"), {"hieu_luc_tu": HOM.isoformat(), "noi_dung": {"chiet_khau": {"nv_kd": 120}}})


def _tour(s, ma, di, st):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=di, end_date=di + dt.timedelta(days=2),
             operator_id=_u(s, "dh").id, status=st, price_per_pax=1_000_000, planned_pax=10, seats_open=10)
    s.add(t); s.commit()


def test_ban_ban_tour_le_ba_pham_vi():
    s = _db()
    _tour(s, "A", HOM + dt.timedelta(days=5), "da_duyet")
    _tour(s, "B", HOM + dt.timedelta(days=30), "nhap")
    _tour(s, "C", HOM - dt.timedelta(days=30), "ket_thuc")
    _tour(s, "D", HOM + dt.timedelta(days=9), "huy")
    d = BTL.ban_lam_viec(s)
    assert d["pham_vi"] == "dang_ban" and [r["code"] for r in d["rows"]] == ["A"]
    assert d["dem_pham_vi"] == {"dang_ban": 1, "sap_mo_ban": 1, "da_di": 1}
    assert [r["code"] for r in BTL.ban_lam_viec(s, "sap_mo_ban")["rows"]] == ["B"]
    assert [r["code"] for r in BTL.ban_lam_viec(s, "da_di")["rows"]] == ["C"]


def test_gui_khach_huong_hoa_hong():
    assert SERVICE_KINDS["GUI_KHACH"] == "Gửi khách – hưởng hoa hồng"
    s = _db()
    nv = _u(s, "nv")
    base = {"service_type": "GUI_KHACH", "customer_name": "K", "customer_phone": "0900000001", "source": "Zalo", "amount": 12_500_000}
    with pytest.raises(HTTPException):
        NP.create(s, nv, dict(base))                                            # thiếu đối tác + số trả
    with pytest.raises(HTTPException):
        NP.create(s, nv, dict(base, supplier_name="XYZ", cost_amount=13_000_000))   # trả đối tác > giá khách trả
    t, b = NP.create(s, nv, dict(base, supplier_name="Công ty XYZ", cost_amount=11_250_000))
    assert b.amount == 12_500_000 and b.cost_amount == 11_250_000 and b.supplier_name == "Công ty XYZ"
    with pytest.raises(HTTPException):                                          # loại khác: KD vẫn không nhập giá vốn
        NP.create(s, nv, dict(base, service_type="VISA", cost_amount=1, supplier_name="NCC"))
