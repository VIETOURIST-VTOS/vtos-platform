# -*- coding: utf-8 -*-
"""DT-1 · Cổng đối tác — Đại lý + CTV (Chủ tịch duyệt bản xem thử 27/10/2026).

  1. Nối hồ sơ: máy GỢI Ý theo MST trước rồi SĐT; nhiều đối tác khớp thì không tự chọn; người duyệt nối.
     Chưa nối = không có số liệu. Chỉ người duyệt đúng loại hồ sơ mới nối được.
  2. Đại lý giữ chỗ qua đủ cổng như Điều hành tạo booking (tour đã duyệt, sức chứa); người tiếp nhận là
     Sale Admin; doanh số không vào chỉ tiêu nhân viên; giá bán công bố, không giảm giá.
  3. Đại lý chỉ thấy booking của chính mình; công nợ hai chiều không bù trừ.
  4. CTV không giữ chỗ; giới thiệu khách = lead có dấu thời gian và mã đối tác; phải có đồng ý của khách.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 10, 27, 9, 0)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "nv_kd"), ("sa", "sales_admin"), ("gdkd", "gd_kd"), ("tpdh", "tp_dh"),
                     ("ct", "chutich"), ("bks", "bks"), ("kt", "ketoan")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: NOW.date())
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _dt(s, ma, ten, loai="dai_ly", mst="", sdt=""):
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    d = DoiTacBanHang(ma=ma, ten=ten, loai=loai, ma_so_thue=mst, dien_thoai=sdt, hieu_luc_tu=dt.date(2026, 1, 1))
    s.add(d); s.commit()
    return d


def _tk(s, loai_dt="dai_ly", mst="", sdt="0908000111", trang_thai="cho_duyet", doi_tac=None):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai="doi_tac", loai_doi_tac=loai_dt, dien_thoai=sdt, ma_so_thue=mst, trang_thai=trang_thai,
                       ho_ten="Đại diện", ten_don_vi="Công ty J", doi_tac_id=doi_tac.id if doi_tac else None)
    s.add(tk); s.commit()
    return tk


def _tour(s, cho=10, status="da_duyet", gia=3_490_000):
    from app.models.core import Tour
    t = Tour(code=f"PQ{cho}{status[:2]}", name="Phú Quốc 3N2Đ", tour_type="le_noi_dia", start_date=dt.date(2026, 11, 6),
             end_date=dt.date(2026, 11, 8), operator_id=_u(s, "dh").id, status=status, price_per_pax=gia,
             seats_open=cho, planned_pax=cho, imported=True)
    s.add(t); s.commit()
    return t


# ── 1 · NỐI HỒ SƠ ─────────────────────────────────────────────────────────────────────────────

def test_goi_y_mst_truoc_roi_sdt_nhieu_khop_khong_tu_chon(db):
    from app.services import doi_tac_cong as D
    j = _dt(db, "DT-0003", "J TRAVEL", mst="0312345678")
    _dt(db, "DT-0009", "Khác", sdt="0908000111")
    g = D.goi_y(db, _tk(db, mst="0312-345-678"))
    assert g["theo"] == "mã số thuế" and g["tu_chon"] == j.id and len(g["khop"]) == 1
    g2 = D.goi_y(db, _tk(db, mst="", sdt="0908000111"))
    assert g2["theo"] == "số điện thoại" and g2["tu_chon"] is not None
    _dt(db, "DT-0010", "Khác 2", sdt="0908 000 111")
    g3 = D.goi_y(db, _tk(db, mst="", sdt="0908000111"))
    assert len(g3["khop"]) == 2 and g3["tu_chon"] is None


def test_duyet_va_noi_chi_nguoi_duyet_dung_loai(db):
    from app.services import doi_tac_cong as D
    j = _dt(db, "DT-0003", "J TRAVEL", mst="0312345678")
    tk = _tk(db, mst="0312345678")
    with pytest.raises(D.LoiDoiTac):
        D.noi(db, _u(db, "tpdh"), tk, "noi", j.id, duyet=True)     # TP ĐH không duyệt hồ sơ đại lý
    with pytest.raises(D.LoiDoiTac):
        D.noi(db, _u(db, "bks"), tk, "noi", j.id, duyet=True)      # BKS chỉ xem
    ctv = _dt(db, "DT-0011", "CTV A", loai="ctv_ban_hang")
    with pytest.raises(D.LoiDoiTac):
        D.noi(db, _u(db, "gdkd"), tk, "noi", ctv.id)               # sai loại
    tk = D.noi(db, _u(db, "gdkd"), tk, "noi", j.id, duyet=True)
    assert tk.doi_tac_id == j.id and tk.trang_thai == "hoat_dong"


def test_tao_moi_tu_ho_so(db):
    from app.services import doi_tac_cong as D
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    tk = D.noi(db, _u(db, "gdkd"), _tk(db, loai_dt="ctv_ban_hang", mst=""), "tao_moi", duyet=True)
    d = db.get(DoiTacBanHang, tk.doi_tac_id)
    assert d.loai == "ctv_ban_hang" and d.ma.startswith("DT-") and tk.trang_thai == "hoat_dong"


def test_chua_noi_khong_co_so_lieu(db):
    from app.services import doi_tac_cong as D
    tk = _tk(db, trang_thai="hoat_dong")
    with pytest.raises(D.LoiDoiTac) as ex:
        D.ban_lam_viec(db, tk)
    assert ex.value.ma == "cho_noi" and ex.value.status == 403
    from app.models.cong_ngoai import TaiKhoanNgoai
    kh = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901", trang_thai="hoat_dong"); db.add(kh); db.commit()
    with pytest.raises(D.LoiDoiTac):
        D.bookings(db, kh)


# ── 2 · ĐẠI LÝ GIỮ CHỖ ────────────────────────────────────────────────────────────────────────

def test_giu_cho_qua_cong_sale_admin_khong_chi_tieu(db):
    from app.services import doi_tac_cong as D
    from app.models.core import Booking, Alert
    j = _dt(db, "DT-0003", "J TRAVEL")
    tk = _tk(db, trang_thai="hoat_dong", doi_tac=j)
    t = _tour(db, cho=10)
    b = D.giu_cho(db, tk, t.id, "Trần B", "0912 345 678", 4, 0, now=NOW)
    assert b.doi_tac_id == j.id and b.sales_id == _u(db, "sa").id and b.counts_for_target is False
    assert b.amount == 3_490_000 * 4 and (b.discount or 0) == 0 and b.giu_cho_den is not None
    assert db.execute(select(Alert).where(Alert.kind == "dai_ly_giu_cho")).scalars().first() is not None
    with pytest.raises(D.LoiDoiTac):                                   # cổng sức chứa: còn 6 chỗ
        D.giu_cho(db, tk, t.id, "C", "0912345679", 7, 0, now=NOW)
    nhap = _tour(db, cho=10, status="cho_duyet")
    with pytest.raises(D.LoiDoiTac):                                   # tour chưa duyệt
        D.giu_cho(db, tk, nhap.id, "C", "0912345679", 1, 0, now=NOW)
    assert db.execute(select(Booking)).scalars().all() == [b]


def test_ctv_khong_giu_cho_va_khong_sale_admin_thi_dong(db):
    from app.services import doi_tac_cong as D
    from app.models.core import User
    c = _dt(db, "DT-0011", "CTV A", loai="ctv_ban_hang")
    with pytest.raises(D.LoiDoiTac):
        D.giu_cho(db, _tk(db, loai_dt="ctv_ban_hang", trang_thai="hoat_dong", doi_tac=c), _tour(db).id, "A", "0912345678", 1, 0, now=NOW)
    j = _dt(db, "DT-0003", "J TRAVEL")
    _u(db, "sa").active = False; db.commit()
    with pytest.raises(D.LoiDoiTac) as ex:
        D.giu_cho(db, _tk(db, trang_thai="hoat_dong", doi_tac=j), _tour(db, cho=9).id, "A", "0912345678", 1, 0, now=NOW)
    assert ex.value.status == 409
    assert isinstance(_u(db, "sa"), User)


# ── 3 · CHỈ THẤY CỦA MÌNH · CÔNG NỢ HAI CHIỀU ────────────────────────────────────────────────

def test_chi_thay_booking_cua_minh_va_cong_no_tach(db):
    from app.services import doi_tac_cong as D
    j = _dt(db, "DT-0003", "J TRAVEL")
    k = _dt(db, "DT-0004", "K TRAVEL")
    tj = _tk(db, trang_thai="hoat_dong", doi_tac=j)
    tkk = _tk(db, trang_thai="hoat_dong", doi_tac=k, sdt="0908000222")
    t = _tour(db, cho=20)
    bj = D.giu_cho(db, tj, t.id, "Trần B", "0912345678", 2, 0, now=NOW)
    D.giu_cho(db, tkk, t.id, "Lê C", "0912345670", 3, 0, now=NOW)
    assert [x["ma"] for x in D.bookings(db, tj, NOW)] == [bj.code]
    with pytest.raises(D.LoiDoiTac) as ex:
        D.qr(db, tj, D.bookings(db, tkk, NOW)[0]["ma"])           # QR booking của đại lý khác
    assert ex.value.status == 404
    no = D.cong_no(db, tj, NOW)
    assert no["dai_ly_phai_tra"] == 2 * 3_490_000 and no["vietourist_phai_tra"] == 0
    blv = D.ban_lam_viec(db, tj, NOW)
    assert blv["phai_tra"] == 2 * 3_490_000 and len(blv["sap_het"]) == 1


# ── 4 · CTV GIỚI THIỆU ───────────────────────────────────────────────────────────────────────

def test_ctv_gioi_thieu_thanh_lead_co_nguon(db):
    from app.services import doi_tac_cong as D
    from app.models.crm import Lead
    c = _dt(db, "DT-0011", "CTV A", loai="ctv_ban_hang")
    tk = _tk(db, loai_dt="ctv_ban_hang", trang_thai="hoat_dong", doi_tac=c)
    t = _tour(db)
    with pytest.raises(D.LoiDoiTac):
        D.gioi_thieu(db, tk, t.id, "Lê D", "0987654321", 2, "", dong_y=False, now=NOW)
    D.gioi_thieu(db, tk, t.id, "Lê D", "0987654321", 2, "", dong_y=True, now=NOW)
    l = db.execute(select(Lead)).scalars().one()
    assert l.phone == "0987654321" and "DT-0011" in l.note and "27/10/2026 09:00" in l.note
    ds = D.gioi_thieu_ds(db, tk)
    assert ds[0]["khach"] == "Lê D" and ds[0]["trang_thai"].startswith("Đã gửi")
    j = _dt(db, "DT-0003", "J TRAVEL")
    with pytest.raises(D.LoiDoiTac):                                  # đại lý không dùng cửa CTV
        D.gioi_thieu(db, _tk(db, trang_thai="hoat_dong", doi_tac=j), None, "X", "0987654322", 1, "", True, now=NOW)


def test_cua_api_doi_phien_cong(db):
    from app.main import app
    paths = {r.path for r in app.routes}
    for p in ("/api/v1/cong/doi-tac/ban-lam-viec", "/api/v1/cong/doi-tac/giu-cho", "/api/v1/tai-khoan-ngoai/{tid}/doi-tac"):
        assert p in paths
