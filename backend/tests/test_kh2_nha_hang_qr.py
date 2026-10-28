# -*- coding: utf-8 -*-
"""KH-2 · Nhà hàng trên cổng khách + thanh toán QR — Chủ tịch duyệt bản xem thử 26/10/2026.

  1. Điều hành nhập, Kinh doanh bật; người nhập không tự bật; cần ≥1 gói đang bán mới bật được.
  2. Sửa nội dung bán khi đang hiện → tự tắt kèm lý do; sửa ghi chú nội bộ thì không.
  3. Cổng khách chỉ thấy nhà hàng đang hiện, gói đang bán; không lộ ghi chú nội bộ.
  4. Yêu cầu đặt bàn: kiểm ngày, giờ, gói, số khách tối thiểu; tạm tính do MÁY tính; ra lead cho Sales.
  5. QR: chuẩn VietQR (CRC đúng), số tiền máy tính (cọc / toàn bộ), nội dung = mã booking khớp robot;
     tham số tài khoản chưa ký thì đóng; tham số chữ có hàm kiểm riêng.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
HOM_NAY = dt.date(2026, 11, 1)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import nha_hang as N, cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "tp_kd"), ("nvkd", "nv_kd"), ("kt", "ketoan")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(N, "_hom_nay", lambda: HOM_NAY)
    monkeypatch.setattr(K, "_hom_nay", lambda: HOM_NAY)
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _nh(s, ten="Bếp Việt", hien=True):
    from app.services import nha_hang as N
    n = N.luu_nha_hang(s, _u(s, "dh"), {"ten": ten, "tinh_thanh": "TP Hồ Chí Minh", "khu_vuc": "Q1", "am_thuc": "Việt Nam",
                                       "ghi_chu_noi_bo": "NCC chiết khấu 15%"})
    td = N.luu_thuc_don(s, _u(s, "dh"), n.id, {"ten": "Set Hương Việt", "loai": "set", "gia_nguoi_lon": 350000, "gia_tre_em": 200000,
                                               "so_khach_toi_thieu": 2, "tu_ngay": "2026-11-01", "den_ngay": "2026-12-31"})
    if hien:
        N.bat_hien(s, _u(s, "kd"), n.id, True)
    return n, td


# ── 1–2 ────────────────────────────────────────────────────────────────────────────────────────

def test_vai_va_tu_tat_khi_sua(db):
    from app.services import nha_hang as N
    with pytest.raises(N.LoiNhaHang):
        N.luu_nha_hang(db, _u(db, "nvkd"), {"ten": "X"})
    n = N.luu_nha_hang(db, _u(db, "dh"), {"ten": "Biển Xanh", "am_thuc": "Hải sản"})
    with pytest.raises(N.LoiNhaHang):
        N.bat_hien(db, _u(db, "kd"), n.id, True)                       # chưa có gói đang bán
    td = N.luu_thuc_don(db, _u(db, "dh"), n.id, {"ten": "Vị biển", "gia_nguoi_lon": 490000})
    with pytest.raises(N.LoiNhaHang):
        N.bat_hien(db, _u(db, "dh"), n.id, True)                       # người nhập không tự bật
    N.bat_hien(db, _u(db, "kd"), n.id, True)
    assert n.hien_cong is True
    N.luu_nha_hang(db, _u(db, "dh"), {"ten": "Biển Xanh", "am_thuc": "Hải sản", "ghi_chu_noi_bo": "gọi chị Lan"}, n.id)
    assert n.hien_cong is True, "ghi chú nội bộ không tắt"
    N.luu_thuc_don(db, _u(db, "dh"), n.id, {"ten": "Vị biển", "gia_nguoi_lon": 520000}, td.id)
    assert n.hien_cong is False and "Vị biển" in n.tat_ly_do
    with pytest.raises(N.LoiNhaHang):
        N.luu_thuc_don(db, _u(db, "dh"), n.id, {"ten": "Âm", "gia_nguoi_lon": 0})
    with pytest.raises(N.LoiNhaHang):
        N.luu_thuc_don(db, _u(db, "dh"), n.id, {"ten": "Ngày ngược", "gia_nguoi_lon": 1, "tu_ngay": "2026-12-01", "den_ngay": "2026-11-01"})


# ── 3–4 ────────────────────────────────────────────────────────────────────────────────────────

def test_cong_chi_thay_dang_hien_va_khong_lo_noi_bo(db):
    from app.services import nha_hang as N
    _nh(db, "Bếp Việt")
    _nh(db, "Chưa bật", hien=False)
    ds = N.danh_sach_cong(db)
    assert [x["ten"] for x in ds["nha_hang"]] == ["Bếp Việt"]
    assert "ghi_chu_noi_bo" not in str(ds) and "15%" not in str(ds) and "dang_ban" not in ds["nha_hang"][0]["thuc_don"][0]
    assert N.danh_sach_cong(db, gia_toi_da=300000)["nha_hang"] == []


def test_yeu_cau_dat_ban(db):
    from app.services import cong_khach as K
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.crm import Lead
    n, td = _nh(db)
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong", ho_ten="An"); db.add(tk); db.commit()
    now = dt.datetime(2026, 11, 1, 9)
    ok = {"nha_hang_id": n.id, "thuc_don_id": td.id, "gio": "18:30", "nguoi_lon": 3, "tre_em": 1}
    for sai in ({**ok, "gio": "25:00"}, {**ok, "nguoi_lon": 1, "tre_em": 0}, {**ok, "thuc_don_id": 999}):
        with pytest.raises(K.LoiKhach):
            K.gui_yeu_cau(db, tk, "nha_hang", None, 0, "", dt.date(2026, 11, 8), "", True, now=now, nha_hang=sai)
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk, "nha_hang", None, 0, "", dt.date(2027, 1, 5), "", True, now=now, nha_hang=ok)   # ngoài thời gian gói
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, tk, "nha_hang", None, 0, "", dt.date(2026, 11, 1), "", True, now=now, nha_hang=ok)  # hôm nay
    yc = K.gui_yeu_cau(db, tk, "nha_hang", None, 999, "", dt.date(2026, 11, 8), "ăn chay", True, now=now, nha_hang=ok)
    assert yc.so_khach == 4 and yc.tam_tinh == 3 * 350000 + 200000 and yc.gio_den == "18:30"
    lead = db.get(Lead, yc.lead_id)
    assert "Đặt bàn nhà hàng" in lead.note and "1.250.000" in lead.note and lead.channel == "Đặt tour web"


# ── 5 · QR ─────────────────────────────────────────────────────────────────────────────────────

def test_vietqr_chuan():
    from app.services import vietqr as Q
    assert Q.crc16("123456789") == "29B1"                               # CRC-16/CCITT-FALSE, giá trị kiểm chuẩn
    assert Q.bin_cua("Vietcombank") == "970436" and Q.bin_cua("Ngân hàng TMCP Tiên Phong (TPBank)") == "970423"
    assert Q.bin_cua("VietABank") == "970427" and Q.bin_cua("MB Bank") == "970422" and Q.bin_cua("Ngân hàng lạ") is None
    p = Q.payload("970436", "0071 000 123456", 2094000, "BK26100012")
    assert p.startswith("000201010212") and "0010A000000727" in p and "5303704" in p and "54072094000" in p
    assert "0810BK26100012" in p and p[-8:-4] == "6304" and Q.crc16(p[:-4]) == p[-4:]
    with pytest.raises(ValueError):
        Q.payload("970436", "123", 0, "x")


def test_qr_don_so_tien_va_tham_so(db, monkeypatch):
    from app.services import cong_khach as K, rules as R
    from app.models.core import Tour, Booking, ServiceRequest
    from app.models.payments import Receipt
    from app.models.banks import BankAccount
    from app.models.cong_ngoai import TaiKhoanNgoai
    t = Tour(code="PQ", name="Phú Quốc", tour_type="le_noi_dia", start_date=dt.date(2026, 11, 6), end_date=dt.date(2026, 11, 8),
             operator_id=_u(db, "dh").id, status="da_duyet", price_per_pax=3_490_000, planned_pax=30)
    db.add(t); db.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="An", customer_phone="0901234567", source="web", pax=2)
    db.add(r); db.flush()
    b = Booking(code="BK26100012", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id, created_by=_u(db, "nvkd").id,
                customer_name="An", customer_phone="0901234567", source="web", pax=2, amount=6_980_000, discount=0, deposit_pct=30)
    db.add(b)
    db.add(BankAccount(code="VCB1", bank_name="Vietcombank", account_number="0071000123456", account_name="CTCP VIETOURIST HOLDINGS"))
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong"); db.add(tk); db.commit()
    monkeypatch.setattr(R, "get_param_text", lambda db, k, on=None: "")
    with pytest.raises(K.LoiKhach):
        K.qr_don(db, tk, b.code)                                          # chưa ký tài khoản → đóng
    monkeypatch.setattr(R, "get_param_text", lambda db, k, on=None: "0071000123456")
    q = K.qr_don(db, tk, b.code)
    assert q["muc"] == "coc" and q["so_tien"] == 2_094_000 and q["con_lai"] == 6_980_000 and q["noi_dung"] == "BK26100012"
    assert K.qr_don(db, tk, b.code, "du")["so_tien"] == 6_980_000 and K.qr_don(db, tk, b.code, "du")["tu_khop"] is True
    db.add(Receipt(code="PT1", booking_id=b.id, amount=2_094_000, status="tu_dong")); db.commit()
    q = K.qr_don(db, tk, b.code)
    assert q["coc"] == 0 and q["muc"] == "du" and q["so_tien"] == 4_886_000
    with pytest.raises(K.LoiKhach):
        K.qr_don(db, tk, b.code, "coc")
    tk2 = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0909999999", trang_thai="hoat_dong"); db.add(tk2); db.commit()
    with pytest.raises(K.LoiKhach):
        K.qr_don(db, tk2, b.code)                                         # đơn người khác
    # tham số là SỐ TÀI KHOẢN (đi được cửa trình tham số chỉ nhận số); không khớp TK đang dùng → đóng
    monkeypatch.setattr(R, "get_param_text", lambda db, k, on=None: "9999")
    assert K.tai_khoan_qr(db) is None
    assert any(p[0] == "cong_qr_tai_khoan" and p[1] == "" for p in R.DEFAULT_PARAMS)
    float("0071000123456")


def test_cua_va_man_hinh():
    from app.services import access as AC, nha_hang as N
    from app.api.v1 import nha_hang as A, cong_khach as CK
    assert AC.MAN_HINH_API["/nha-hang"] == ("/api/v1/nha-hang",)
    assert {"tp_dh", "nv_dh", "tp_kd", "gd_kd"} <= set(AC.MENU_ROLES["/nha-hang"])
    assert "nv_kd" not in N.VAI_NHAP and "nv_dh" not in N.VAI_BAT
    assert {"/api/v1/cong/khach/nha-hang", "/api/v1/cong/khach/nha-hang/{nid}", "/api/v1/cong/khach/don/{ma}/qr"} <= {r.path for r in CK.router.routes}
    assert "/api/v1/nha-hang/{nid}/hien-cong" in {r.path for r in A.router.routes}
    for f, chu in (("web/app/nha-hang/page.tsx", ("Bật hiện cổng", "giá bán cho khách")),
                   # DT-2 (Chủ tịch 28/10/2026): đặt bàn có thanh toán — bàn giữ khi tiền đã vào, không còn «chưa giữ bàn».
                   ("web/components/cong/khach/NhaHangKhach.tsx", ("bàn chỉ giữ khi tiền đã vào", "Tạm tính")),
                   ("web/components/cong/khach/QrThanhToan.tsx", ("GIỮ NGUYÊN nội dung", "toDataURL"))):
        src = (GOC / f).read_text(encoding="utf-8")
        for c in chu:
            assert c in src, (f, c)
