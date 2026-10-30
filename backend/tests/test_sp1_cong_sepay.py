# -*- coding: utf-8 -*-
"""SP-1 · Cổng thanh toán SePay thay OnePay cho thẻ (Chủ tịch chốt 29/10/2026).

  1. Chữ ký biểu mẫu: HMAC-SHA256 base64 trên «trường=giá trị» nối dấu phẩy theo đúng thứ tự tài liệu SePay.
  2. Có khóa SePay → bắt đầu trả thẻ trả về biểu mẫu POST (không phải đường dẫn); chưa có khóa → OnePay như cũ.
  3. IPN: sai X-Secret-Key → 401; đúng khóa + ORDER_PAID + APPROVED + đúng số → thành công; lệch số → không thành công;
     gửi lại không ghi thêm. Mã KS… về đơn khách sạn, mã NH… về đặt bàn.
"""
import base64
import datetime as dt
import hashlib
import hmac

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks14_dat_phong_vtd import NAY, _dat, _tk, k3  # noqa: F401


@pytest.fixture()
def bat_sepay(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "SEPAY_PG_MERCHANT_ID", "SP_TEST_1")
    monkeypatch.setattr(settings, "SEPAY_PG_SECRET_KEY", "bi-mat")
    monkeypatch.setattr(settings, "SEPAY_PG_IPN_KEY", "khoa-ipn")
    monkeypatch.setattr(settings, "SEPAY_PG_ENV", "sandbox")


def test_chu_ky_theo_thu_tu_tai_lieu(bat_sepay):
    from app.services import sepay_pg as SP
    f = SP.bieu_mau("KS2611ABCDT1", 5037000, "Dat phong KS2611ABCD", "https://kh.vietourist.vn/cong?ks_vtd=KS2611ABCD&the=cho",
                    "https://x/loi", "https://x/huy")
    assert f["action"] == "https://pay-sandbox.sepay.vn/v1/checkout/init"
    ten = [k for k, _ in f["fields"]]
    assert ten == ["order_amount", "merchant", "currency", "operation", "order_description", "order_invoice_number",
                   "success_url", "error_url", "cancel_url", "signature"]
    chuoi = ("order_amount=5037000,merchant=SP_TEST_1,currency=VND,operation=PURCHASE,order_description=Dat phong KS2611ABCD,"
             "order_invoice_number=KS2611ABCDT1,success_url=https://kh.vietourist.vn/cong?ks_vtd=KS2611ABCD&the=cho,"
             "error_url=https://x/loi,cancel_url=https://x/huy")
    ky = base64.b64encode(hmac.new(b"bi-mat", chuoi.encode(), hashlib.sha256).digest()).decode()
    assert dict(f["fields"])["signature"] == ky
    assert SP.khoa_ipn_dung("khoa-ipn") and not SP.khoa_ipn_dung("sai") and not SP.khoa_ipn_dung(None)


def _ipn(ma_gd, so, loai="ORDER_PAID", tt="APPROVED"):
    return {"timestamp": 1, "notification_type": loai,
            "order": {"order_status": "CAPTURED", "order_currency": "VND", "order_amount": f"{so}.00", "order_invoice_number": ma_gd},
            "transaction": {"payment_method": "CARD", "transaction_id": "68ba94", "transaction_status": tt,
                            "transaction_amount": str(so), "transaction_currency": "VND", "card_brand": "VISA", "card_number": "4111XXXX1111"}}


def test_dat_phong_tra_the_sepay(db, k3, bat_sepay):
    from app.services import don_ks_vtd as S
    from app.services import sepay_pg as SP
    k, lp, g = k3
    d = _dat(db, k, g)
    r = S.the_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.2.3.4", NAY)
    assert "form" in r and "url" not in r
    t = db.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    assert t.kenh == "sepay" and dict(r["form"]["fields"])["order_invoice_number"] == t.ma_gd
    assert dict(r["form"]["fields"])["order_amount"] == "4370000"
    # lệch số → không thành công, đơn vẫn chờ
    S.sepay_ket_qua(db, SP.doc_ipn(_ipn(t.ma_gd, 100000)), NAY)
    assert t.trang_thai == "that_bai" and d.trang_thai == "cho_tra"
    S.sepay_ket_qua(db, SP.doc_ipn(_ipn(t.ma_gd, 4370000)), NAY + dt.timedelta(minutes=2))
    assert t.trang_thai == "thanh_cong" and d.trang_thai == "da_tra" and "VISA" in t.ghi_chu
    S.sepay_ket_qua(db, SP.doc_ipn(_ipn(t.ma_gd, 4370000)), NAY + dt.timedelta(minutes=3))   # gửi lại: không đổi
    assert S.da_tra(db, d) == 4370000
    S.kt_doi_soat(db, _u(db, "kt"), t.id, 80000, NAY)
    assert t.trang_thai == "da_doi_soat" and t.but_toan


def test_ipn_khoa_sai_va_dinh_tuyen(db, k3, bat_sepay, monkeypatch):
    from fastapi.testclient import TestClient
    from app.db.session import get_db
    from app.main import app
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    d = _dat(db, k, g)
    S.the_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.2.3.4", NAY)
    t = db.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    monkeypatch.setattr(S, "cap_nhat", lambda db_, d_, now=None: d_)     # đơn giữ 15 phút theo NAY — bỏ đồng hồ thật
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        assert c.post("/api/v1/sepay-pg/ipn", json=_ipn(t.ma_gd, 4370000), headers={"X-Secret-Key": "sai"}).status_code == 401
        assert t.trang_thai == "cho"
        r = c.post("/api/v1/sepay-pg/ipn", json=_ipn(t.ma_gd, 4370000), headers={"X-Secret-Key": "khoa-ipn"})
        assert r.status_code == 200 and r.json()["ghi"] is True
        db.refresh(t)
        assert t.trang_thai == "thanh_cong"
        r = c.post("/api/v1/sepay-pg/ipn", json=_ipn("NH99999999T1", 1000), headers={"X-Secret-Key": "khoa-ipn"})
        assert r.status_code == 200 and r.json()["ghi"] is False                 # mã đặt bàn không có → không ghi
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_chua_co_khoa_sepay_thi_onepay(db, k3, monkeypatch):
    from app.services import don_ks_vtd as S
    from app.services import onepay as OP
    k, lp, g = k3
    d = _dat(db, k, g)
    with pytest.raises(S.LoiDon, match="chưa mở"):
        S.the_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.2.3.4", NAY)
    monkeypatch.setattr(OP, "bat", lambda: True)
    monkeypatch.setattr(OP, "duong_thanh_toan", lambda *a, **kw: "https://onepay.test/pay")
    assert S.the_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.2.3.4", NAY) == {"url": "https://onepay.test/pay"}


def test_dat_ban_tra_the_sepay(bat_sepay):
    """DT-2 cũng đi SePay: biểu mẫu POST, IPN đúng số → bàn giữ."""
    import tests.test_dt2_dat_ban as T
    from app.services import dat_ban as S
    from app.services import sepay_pg as SP
    gen = T.db.__wrapped__() if hasattr(T.db, "__wrapped__") else None
    if gen is None:
        pytest.skip("fixture đặt bàn không gọi trực tiếp được")
    s = next(gen)
    try:
        d = T._nhan(s, T._dat(s))
        r = S.the_bat_dau(s, T._tk(s, "0901000001"), d.ma, "https://kh.vietourist.vn", "1.1.1.1", T.NAY)
        f = dict(r["form"]["fields"])
        assert f["order_invoice_number"].startswith(d.ma) and f["order_amount"] == str(int(d.phai_tra_truoc))
        S.sepay_ket_qua(s, SP.doc_ipn(_ipn(f["order_invoice_number"], int(d.phai_tra_truoc))), T.NAY)
        assert d.trang_thai == "da_giu"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
