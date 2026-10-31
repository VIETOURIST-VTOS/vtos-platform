# -*- coding: utf-8 -*-
"""KS-16i · Đơn nguồn CTV tích điểm VTD Rewards (Chủ tịch 01/11/2026, theo v3 mục 7): từ ngày áp v3, trong trần
chi phí ưu đãi của booking (đã tính hoa hồng nguồn bậc D06 cao nhất). Tour chưa có dự toán → không cộng.
Booking qua đại lý vẫn không tích."""
import datetime as dt

from sqlalchemy import select

from tests.test_ks16g_rewards_v3 import db, _u, CHU  # noqa: F401

TR = 1_000_000


def _dt(s, loai):
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    d = DoiTacBanHang(ma=f"DT-{loai}", ten=loai, loai=loai, hieu_luc_tu=dt.date(2026, 1, 1))
    s.add(d); s.commit()
    return d


def _bk(s, gia, cp, doi_tac, ket=dt.date(2026, 11, 20), ma="BK-C"):
    from app.models.core import Tour, Booking, ServiceRequest
    from app.models.payments import Receipt
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=ket - dt.timedelta(days=2), end_date=ket, operator_id=_u(s, "dh").id,
             status="ket_thuc", price_per_pax=gia, planned_pax=1, var_cost_per_pax=cp)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="An", customer_phone="0901234567", source="web", pax=1)
    s.add(r); s.flush()
    b = Booking(code=ma, tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id, customer_name="An",
                customer_phone="0901234567", source="web", pax=1, amount=gia, discount=0, doi_tac_id=doi_tac.id if doi_tac else None)
    s.add(b); s.flush()
    s.add(Receipt(code="PT" + ma, booking_id=b.id, amount=gia, status="ke_toan_xac_nhan",
                  created_at=dt.datetime.combine(ket, dt.time(9)), confirmed_at=dt.datetime.combine(ket, dt.time(9))))
    s.commit()
    return b


def _diem(s, ma):
    from app.models.rewards import SoDiem
    from app.models.core import Booking
    b = s.execute(select(Booking).where(Booking.code == ma)).scalars().one()
    return sum(r.so_diem for r in s.execute(select(SoDiem).where(SoDiem.booking_id == b.id, SoDiem.loai.in_(("CONG", "DAO")))).scalars())


def test_don_ctv_tich_diem_trong_tran(db):
    from app.services import rewards as RW
    ctv, dl = _dt(db, "ctv_ban_hang"), _dt(db, "dai_ly")
    _bk(db, 10 * TR, 8_500_000, ctv, ma="BK-CTV")          # G 1,5tr · trần 600k · nguồn 3% 300k → còn 300k
    _bk(db, 10 * TR, 9_300_000, ctv, ma="BK-HET")          # G 0,7tr · trần 200k < nguồn 300k → 0 điểm
    _bk(db, 10 * TR, None, ctv, ma="BK-KDT")               # chưa có dự toán
    _bk(db, 10 * TR, 8_000_000, dl, ma="BK-DL")            # đại lý: không tích
    RW.tinh(db, CHU, dt.date(2026, 11, 25))
    assert _diem(db, "BK-CTV") == 1000 and _diem(db, "BK-HET") == 0 and _diem(db, "BK-KDT") == 0 and _diem(db, "BK-DL") == 0
    assert RW.tinh(db, CHU, dt.date(2026, 11, 26))["ghi"] == 0, "chạy lại không ghi"


def test_don_ctv_truoc_ngay_ap_v3_khong_tich(db):
    from app.services import rewards as RW
    ctv = _dt(db, "ctv_ban_hang")
    _bk(db, 10 * TR, 8_500_000, ctv, ket=dt.date(2026, 11, 20), ma="BK-CTV")
    db._st["v3"] = dt.date(2026, 12, 1)
    RW.tinh(db, CHU, dt.date(2026, 11, 25))
    assert _diem(db, "BK-CTV") == 0
