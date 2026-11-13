"""R5-12 · Chủ tịch 14/11/2026: «2 cái doanh thu & chỉ tiêu này làm chung 1 biểu đồ cho tất cả trên bàn GĐKD,
TP, NV đều thấy được của phòng và của tôi, dùng biểu đồ giống hình 1 (Nhịp phấn đấu)». Chốt: bàn GĐ KHÔNG có
«Của tôi»; chỉ tiêu phòng = cộng chỉ tiêu cá nhân (NV × 500 tr, TN và TP × 1 tỷ)."""
import datetime as dt
import pathlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.services import ban_kd_vai as V
from app.services import ket_qua_that as KQT

GOC = pathlib.Path(__file__).resolve().parents[2]
HOM = dt.date(2026, 11, 14)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai, nhom in (("nv1", "nv_kd", "KD1"), ("nv2", "nv_kd", "KD2"), ("tn", "tn_kd", "KD1"),
                           ("tp", "tp_kd", "VPCT"), ("ngoai", "nv_kd", "VPHN"), ("dh", "nv_dh", "")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x", sales_group=nhom))
    s.commit()
    return s


def _u(s, t):
    return s.execute(select(User).where(User.username == t)).scalars().first()


def _ban(s, ma, ket_thuc, tien, ai="nv1"):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status="da_duyet", price_per_pax=tien, planned_pax=10, seats_open=10)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, ai).id, customer_name="K", customer_phone=f"09{t.id:08d}",
                       source="web", pax=1)
    s.add(r); s.flush()
    s.add(Booking(code=ma + "-B", tour_id=t.id, request_id=r.id, sales_id=_u(s, ai).id, created_by=_u(s, ai).id,
                  customer_name="K", customer_phone=f"09{t.id:08d}", source="web", pax=1, amount=tien))
    s.commit()


def test_chi_tieu_phong_bang_cong_ca_nhan():
    s = _db()
    d = V.nhip(s, None, "phong", "thang", HOM)
    # 2 NV × 500 tr + TN 1 tỷ + TP 1 tỷ; người VPHN không thuộc phòng Lẻ
    assert d["so_nguoi"] == 4 and d["chi_tieu"] == 3_000_000_000
    assert V.nhip(s, None, "phong", "nam", HOM)["chi_tieu"] == 36_000_000_000
    assert V.nhip(s, None, "phong", "quy", HOM)["chi_tieu"] == 9_000_000_000


def test_cua_toi_luy_ke_theo_ngay_ket_thuc_va_dung_o_hom_nay():
    s = _db()
    _ban(s, "A", dt.date(2026, 11, 3), 40_000_000)
    _ban(s, "B", dt.date(2026, 11, 10), 60_000_000)
    _ban(s, "C", dt.date(2026, 11, 25), 99_000_000)            # sau hôm nay: không vào lũy kế
    d = V.nhip(s, _u(s, "nv1"), "toi", "thang", HOM)
    luy = [p["luy_ke"] for p in d["diem"]]
    assert luy[1] == 0 and luy[2] == 40_000_000 and luy[9] == 100_000_000 and luy[13] == 100_000_000
    assert all(v is None for v in luy[14:]), "sau hôm nay để rỗng, không vẽ"
    assert d["chi_tieu"] == 500_000_000
    assert d["diem"][-1]["nhip"] == 500_000_000
    assert round(d["lech"]) == round(100_000_000 - 500_000_000 * 14 / 30)


def test_theo_ngay_cong_ra_dung_theo_mang():
    s = _db()
    _ban(s, "A", dt.date(2026, 11, 3), 40_000_000)
    _ban(s, "B", dt.date(2026, 11, 10), 60_000_000)
    ds = list(s.execute(select(Tour)).scalars())
    so = {t.id: (float(t.price_per_pax), None) for t in ds}
    tm, tn = KQT._theo_mang(ds, so), KQT._theo_ngay_mang(ds, so)
    for m in KQT.NGAN:
        assert round(sum(tn[m].values())) == round(tm[m]["doanh_thu"])


def test_giao_dien_mot_khoi_tren_bon_ban():
    k = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")
    assert "export function KhoiNhipDoanhThu" in k and "BieuDoDuong" in k
    gd = (GOC / "web/components/BanGdKdLe.tsx").read_text(encoding="utf-8")
    # R5-14: khối nằm trong hàng tiền `HangTien` cùng Phải thu gọn.
    assert '<HangTien duong="/ban-kd-le/nhip" coToi={false}' in gd, "bàn GĐ chỉ «Của phòng»"
    assert "<KhoiNhipDoanhThu duong={duong} coToi={coToi} />" in k
    for f in ("BanTpKd", "BanTnKd", "BanNvKd"):
        t = (GOC / f"web/components/{f}.tsx").read_text(encoding="utf-8")
        assert '<HangTien duong="/ban-kd-le/vai/nhip" coToi' in t and "<BieuDo12" not in t
