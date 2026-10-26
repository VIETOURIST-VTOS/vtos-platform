# -*- coding: utf-8 -*-
"""DH-1 · Hoa hồng đối tác bán hàng theo D06 — Chủ tịch chốt 26/10/2026, duyệt bản xem thử cùng ngày.

  1. Phép tính lũy tiến từng phần đúng mọi vector của tài liệu D06 (đại lý, CTV, ranh giới, hoàn).
  2. Đủ điều kiện = booking không hủy, tour kết thúc VÀ trả đủ; vào tháng của ngày muộn hơn.
  3. Chưa chọn hình thức / giá NET thì không tính; đổi hình thức có hiệu lực từ tháng sau.
  4. Chưa có ngày hiệu lực thì chỉ tính thử: không ghi sổ, không chốt, không đề nghị chi.
  5. Sổ chỉ ghi thêm; chạy lại cùng nguồn không ghi; hoàn sau chốt ghi âm vào kỳ gốc; vượt chi hiện âm.
  6. Đề nghị chi đi luồng duyệt chi (loại hoa_hong, GĐ KD xác nhận, TK 6417); không đề nghị trùng.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
TR = 1_000_000


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import hoa_hong_d06 as H
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("kt", "ketoan"), ("gd", "gd_kd"), ("dh", "nv_dh"), ("kd", "nv_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: dt.date(2026, 11, 1))
    monkeypatch.setattr(H, "_hom_nay", lambda: dt.date(2026, 12, 5))
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _doi_tac(s, ma, loai="dai_ly"):
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    d = DoiTacBanHang(ma=ma, ten=f"Đối tác {ma}", loai=loai, hieu_luc_tu=dt.date(2026, 1, 1))
    s.add(d); s.commit(); return d


def _ban(s, dtc, gia, ket_thuc, tra_luc=None, tra=None, company_id=None, giam=0, ma=None):
    from app.models.core import Tour, Booking, ServiceRequest
    from app.models.payments import Receipt
    ma = ma or f"T{s.execute(select(Tour)).scalars().all().__len__() + 1}"
    t = Tour(code=ma, name=f"Tour {ma}", tour_type="le_noi_dia", start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status="ket_thuc", price_per_pax=gia, fixed_cost=0, var_cost_per_pax=0, planned_pax=1, seats_open=1)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="K", customer_phone="0900000000", source="dai_ly", pax=1)
    s.add(r); s.flush()
    b = Booking(code=f"BK-{ma}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "dh").id,
                customer_name="K", customer_phone="0900000000", source="dai_ly", pax=1, amount=gia, discount=giam,
                doi_tac_id=dtc.id, company_id=company_id)
    s.add(b); s.flush()
    if tra_luc:
        s.add(Receipt(code=f"PT-{ma}", booking_id=b.id, amount=tra if tra is not None else gia - giam, status="ke_toan_xac_nhan",
                      created_at=dt.datetime.combine(tra_luc, dt.time(10)), confirmed_at=dt.datetime.combine(tra_luc, dt.time(10))))
    s.commit()
    return b


def _ht(s, dtc, ht, monkeypatch=None, hom_nay=dt.date(2026, 11, 2)):
    from app.services import hoa_hong_d06 as H
    return H.dat_hinh_thuc(s, _u(s, "gd"), dtc.id, ht, hom_nay=hom_nay)


# ── 1 · phép tính ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("d,tong,co_ban,thuong", [
    (200 * TR, 6 * TR, 6 * TR, 0), (300 * TR, 9_500_000, 9 * TR, 500_000), (500 * TR, 16_500_000, 15 * TR, 1_500_000),
    (700 * TR, 24_500_000, 21 * TR, 3_500_000), (1000 * TR, 36_500_000, 30 * TR, 6_500_000), (0, 0, 0, 0),
    (450 * TR, 14_750_000, 13_500_000, 1_250_000)])
def test_dai_ly_dung_bang_d06(d, tong, co_ban, thuong):
    from app.services import hoa_hong_d06 as H
    q = H.quyen_huong(d, "dai_ly_d06")
    assert (q["tong"], q["co_ban"], q["thuong"]) == (tong, co_ban, thuong)


@pytest.mark.parametrize("d,tong,thuong", [(50 * TR, 1 * TR, 0), (100 * TR, 2_250_000, 250_000), (150 * TR, 3_500_000, 500_000),
                                           (200 * TR, 5 * TR, 1 * TR), (80 * TR, 1_750_000, 150_000)])
def test_ctv_dung_bang_d06(d, tong, thuong):
    from app.services import hoa_hong_d06 as H
    q = H.quyen_huong(d, "ctv_d06")
    assert q["tong"] == tong and q["thuong"] == thuong


def test_ranh_gioi_va_khong_tran():
    from app.services import hoa_hong_d06 as H
    assert H.quyen_huong(200 * TR - 1, "dai_ly_d06")["tong"] == 6 * TR       # 5.999.999,97 → 6.000.000 làm tròn một lần
    assert H.quyen_huong(200 * TR + 1, "dai_ly_d06")["tong"] == 6 * TR         # +0,035 đ
    assert H.quyen_huong(5000 * TR, "dai_ly_d06")["tong"] == 16_500_000 + 4500 * TR * 4 // 100, "không trần"
    assert H.bac_hien_tai(700 * TR, "dai_ly_d06")["toi_da"] is True
    assert H.bac_hien_tai(450 * TR, "dai_ly_d06")["con_toi_bac_sau"] == 50 * TR
    assert H.quyen_huong(700 * TR, "dai_ly_d06")["tong"] - H.quyen_huong(450 * TR, "dai_ly_d06")["tong"] == 9_750_000
    assert H.quyen_huong(200 * TR, "ctv_d06")["tong"] - H.quyen_huong(80 * TR, "ctv_d06")["tong"] == 3_250_000
    src = (GOC / "backend/app/services/hoa_hong_d06.py").read_text(encoding="utf-8")
    assert "float(" not in src.split("def quyen_huong")[1].split("def bac_hien_tai")[0], "phép tính không dùng float"


# ── 2 · đủ điều kiện và tháng ─────────────────────────────────────────────────────────────────

def test_du_dieu_kien_va_thang_cua_ngay_muon_hon(db):
    from app.services import hoa_hong_d06 as H
    a = _doi_tac(db, "A"); _ht(db, a, "dai_ly_d06")
    _ban(db, a, 100 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))           # tháng 11
    _ban(db, a, 50 * TR, dt.date(2026, 11, 28), dt.date(2026, 12, 2))            # trả đủ tháng 12 → tháng 12
    _ban(db, a, 70 * TR, dt.date(2026, 11, 20))                                  # chưa trả → chưa đủ
    _ban(db, a, 30 * TR, dt.date(2026, 11, 20), dt.date(2026, 11, 1), tra=10 * TR)  # trả thiếu
    _ban(db, a, 40 * TR, dt.date(2026, 11, 12), dt.date(2026, 11, 3), giam=5 * TR)  # sau giảm giá = 35 tr
    b = _ban(db, a, 90 * TR, dt.date(2026, 11, 15), dt.date(2026, 11, 1))
    b.cancelled = True; db.commit()
    t11 = H.tong_hop(db, "2026-11")
    dong = [x for x in t11["dong"] if x["doi_tac_id"] == a.id][0]
    assert dong["doanh_so"] == 135 * TR and len(dong["nguon"]) == 2
    assert {x["ly_do"] for x in t11["chua_du"]} == {"khách chưa trả đủ"}
    assert next(x for x in H.tong_hop(db, "2026-12")["dong"] if x["doi_tac_id"] == a.id)["doanh_so"] == 50 * TR


# ── 3 · hình thức ────────────────────────────────────────────────────────────────────────────

def test_chua_chon_va_gia_net_khong_tinh_doi_hinh_thuc_tu_thang_sau(db):
    from app.services import hoa_hong_d06 as H
    x, n = _doi_tac(db, "X", "ghep_le"), _doi_tac(db, "N")
    _ht(db, n, "gia_net")
    _ban(db, x, 100 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))
    _ban(db, n, 100 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))
    t = H.tong_hop(db, "2026-11")
    assert t["dong"] == [] and [c["doi_tac_id"] for c in t["chua_chon"]] == [x.id] and [c["doi_tac_id"] for c in t["gia_net"]] == [n.id]
    r = _ht(db, n, "dai_ly_d06", hom_nay=dt.date(2026, 11, 20))
    assert r.hieu_luc_tu == dt.date(2026, 12, 1), "đổi sau lần đầu: từ đầu tháng kế tiếp"
    assert H.hinh_thuc_cua(db, n.id, "2026-11") == "gia_net" and H.hinh_thuc_cua(db, n.id, "2026-12") == "dai_ly_d06"


# ── 4 · chưa bật ─────────────────────────────────────────────────────────────────────────────

def test_chua_bat_chi_tinh_thu(db, monkeypatch):
    from app.services import hoa_hong_d06 as H
    from app.models.hoa_hong_d06 import SoHoaHong
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: None)
    a = _doi_tac(db, "A"); _ht(db, a, "dai_ly_d06")
    _ban(db, a, 300 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))
    t = H.tong_hop(db, "2026-11")
    assert t["dang_bat"] is False and t["dong"][0]["tong"] == 9_500_000 and t["dong"][0]["da_ghi_so"] is False
    with pytest.raises(H.LoiD06):
        H.tinh_lai(db, _u(db, "kt"), "2026-11")
    assert db.execute(select(SoHoaHong)).first() is None
    # đã ghi sổ khi đang bật, sau đó ngày hiệu lực bị gỡ → không chốt, không đề nghị chi
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: dt.date(2026, 11, 1))
    kt = _u(db, "kt")
    H.tinh_lai(db, kt, "2026-11")
    kid = H.tong_hop(db, "2026-11")["dong"][0]["ky_id"]
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: None)
    with pytest.raises(H.LoiD06):
        H.chot(db, kt, kid)
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: dt.date(2026, 11, 1))
    H.chot(db, kt, kid)
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: None)
    with pytest.raises(H.LoiD06):
        H.de_nghi_chi(db, kt, kid)
    monkeypatch.setattr(H, "hieu_luc_tu", lambda db: dt.date(2026, 12, 1))
    assert H.dang_bat(db, "2026-11") is False and H.dang_bat(db, "2026-12") is True, "không tính hồi tố trước ngày hiệu lực"


# ── 5 · sổ ────────────────────────────────────────────────────────────────────────────────────

def test_so_chi_ghi_them_va_hoan_sau_chot_ghi_am_ky_goc(db):
    from app.services import hoa_hong_d06 as H
    from app.models.hoa_hong_d06 import SoHoaHong
    a = _doi_tac(db, "A"); _ht(db, a, "dai_ly_d06")
    _ban(db, a, 450 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))
    hoan = _ban(db, a, 250 * TR, dt.date(2026, 11, 12), dt.date(2026, 11, 6))
    kt = _u(db, "kt")
    H.tinh_lai(db, kt, "2026-11")
    assert "không có gì thay đổi" in H.tinh_lai(db, kt, "2026-11")["message"]
    n_dong = len(db.execute(select(SoHoaHong)).scalars().all())
    d = H.tong_hop(db, "2026-11")["dong"][0]
    assert d["tong"] == 24_500_000 and d["co_ban"] == 21 * TR and d["thuong"] == 3_500_000
    H.chot(db, kt, d["ky_id"])
    hoan.cancelled = True; db.commit()                                         # khách hoàn 250 tr sau khi chốt
    assert H.tong_hop(db, "2026-11")["dong"][0]["can_tinh_lai"] is True
    H.tinh_lai(db, kt, "2026-11")
    d = H.tong_hop(db, "2026-11")["dong"][0]
    assert d["tong"] == 14_750_000 and d["dieu_chinh"] == -9_750_000 and d["trang_thai"] == "da_chot"
    so = db.execute(select(SoHoaHong).order_by(SoHoaHong.id)).scalars().all()
    assert len(so) > n_dong and all(x.sau_chot for x in so[n_dong:]) and sum(x.so_tien for x in so[n_dong:]) == -9_750_000
    assert H.tong_hop(db, "2026-12")["dong"] == [], "không trừ vào tháng mới"


def test_chua_het_thang_khong_chot_va_tach_phap_nhan_tach_chuong_trinh(db, monkeypatch):
    from app.services import hoa_hong_d06 as H
    from app.models.core import Company
    c1, c2 = Company(code="VTD", name="VTD"), Company(code="VTRIP", name="VTRIP")
    db.add_all([c1, c2]); db.commit()
    a, c = _doi_tac(db, "A"), _doi_tac(db, "C", "ctv_ban_hang")
    _ht(db, a, "dai_ly_d06"); _ht(db, c, "ctv_d06")
    _ban(db, a, 150 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5), company_id=c1.id)
    _ban(db, a, 150 * TR, dt.date(2026, 11, 11), dt.date(2026, 11, 5), company_id=c2.id)
    _ban(db, c, 100 * TR, dt.date(2026, 11, 11), dt.date(2026, 11, 5), company_id=c1.id)
    H.tinh_lai(db, _u(db, "kt"), "2026-11")
    dong = H.tong_hop(db, "2026-11")["dong"]
    assert sorted((x["doi_tac_id"], x["phap_nhan"], x["tong"]) for x in dong) == sorted(
        [(a.id, "VTD", 4_500_000), (a.id, "VTRIP", 4_500_000), (c.id, "VTD", 2_250_000)]), "khác pháp nhân không cộng"
    monkeypatch.setattr(H, "_hom_nay", lambda: dt.date(2026, 11, 30))
    with pytest.raises(H.LoiD06):
        H.chot(db, _u(db, "kt"), dong[0]["ky_id"])


# ── 6 · đề nghị chi ───────────────────────────────────────────────────────────────────────────

def test_de_nghi_chi_di_luong_duyet_va_khong_trung(db):
    from app.services import hoa_hong_d06 as H
    from app.services import ops as O
    from app.services import misa as M
    from app.services import luong_viec as LV
    assert O.CATEGORY_CONFIRMER["hoa_hong"] == ("gd_kd",) and LV.NGUOI_XAC_NHAN_THEO_LOAI["hoa_hong"] == ("gd_kd",)
    assert M.CATEGORY_ACCOUNT["hoa_hong"] == "6417"
    a = _doi_tac(db, "A"); _ht(db, a, "dai_ly_d06")
    _ban(db, a, 300 * TR, dt.date(2026, 11, 10), dt.date(2026, 11, 5))
    kt = _u(db, "kt")
    H.tinh_lai(db, kt, "2026-11")
    kid = H.tong_hop(db, "2026-11")["dong"][0]["ky_id"]
    with pytest.raises(H.LoiD06):
        H.de_nghi_chi(db, kt, kid)                                   # chưa chốt
    H.chot(db, kt, kid)
    pr = H.de_nghi_chi(db, kt, kid)
    assert pr.category == "hoa_hong" and int(pr.amount) == 9_500_000 and pr.status == "cho_tp"
    with pytest.raises(H.LoiD06):
        H.de_nghi_chi(db, kt, kid)                                   # đang đề nghị — không lập trùng
    pr.status = "da_chi"; db.commit()
    d = H.tong_hop(db, "2026-11")["dong"][0]
    assert d["da_tra"] == 9_500_000 and d["con_phai_tra"] == 0


def test_cua_api_va_man_hinh():
    from app.api.v1 import hoa_hong_d06 as A
    from app.services import hoa_hong_d06 as H
    from app.services import access as AC
    assert H.VAI_KE_TOAN == ("ketoan",) and "gd_kd" not in H.VAI_KE_TOAN and "gd_kd" in H.VAI_HINH_THUC
    assert AC.MAN_HINH_API["/hoa-hong-d06"] == ("/api/v1/hoa-hong-d06",)
    from app.services.vai_ke_thua import vai_va_cha
    assert {v for v in AC.MENU_ROLES["/hoa-hong-d06"] if not set(vai_va_cha(v)) & set(H.VAI_XEM)} == set(), "menu có vai mà cửa API chặn"
    paths = {r.path for r in A.router.routes}
    assert {"/api/v1/hoa-hong-d06", "/api/v1/hoa-hong-d06/tinh-lai", "/api/v1/hoa-hong-d06/ky/{ky_id}/chot",
            "/api/v1/hoa-hong-d06/ky/{ky_id}/de-nghi-chi", "/api/v1/hoa-hong-d06/hinh-thuc"} <= paths
    src = (GOC / "web/app/hoa-hong-d06/page.tsx").read_text(encoding="utf-8")
    for s in ("Lập đề nghị chi", "Chốt kỳ", "tính thử", "Vượt chi", "Chưa chọn"):
        assert s in src, s
    from app.services import rules as R
    assert "d06_hieu_luc_tu" in R.THAM_SO_NGAY and any(p[0] == "d06_hieu_luc_tu" and p[1] == "" for p in R.DEFAULT_PARAMS)
