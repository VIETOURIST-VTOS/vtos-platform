"""R5-9 · Khớp số Kinh doanh lẻ giữa màn Chủ tịch / TGĐ, bàn GĐ KD và bàn TP — Chủ tịch chốt 13/11/2026:
    «giữ 2 cơ sở, nối cho khớp» — xếp hạng NV Lẻ trên màn Chủ tịch đọc cơ sở chỉ tiêu (giá trị booking) như
    bàn TP; doanh thu phòng vẫn là doanh thu chuyến; mỗi bàn có dòng đối chiếu số kia.
    «GĐ tính cả khối KD» — chưa khai đơn vị thì ô doanh thu tính chỉ tiêu của GĐ cộng cả khối KD.
    «Tách nợ cũ cần đối soát» — chuyến đã đi quá 30 ngày mà còn nợ ra một dòng riêng; hai phần cộng đủ.
"""
import datetime as dt
import pathlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.services import ban_kd_le as GD

HOM_NAY = dt.date.today()
GOC = pathlib.Path(__file__).resolve().parents[2]


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nv", "nv_kd"), ("dh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    return s


def _u(s, t):
    return s.execute(select(User).where(User.username == t)).scalars().first()


def _ban(s, ma, di, tien, paid=0):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=di, end_date=di + dt.timedelta(days=2),
             operator_id=_u(s, "dh").id, status="da_duyet", price_per_pax=tien, planned_pax=10, seats_open=10)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "nv").id, customer_name="K", customer_phone=f"09{t.id:08d}",
                       source="web", pax=1)
    s.add(r); s.flush()
    s.add(Booking(code=ma + "-B", tour_id=t.id, request_id=r.id, sales_id=_u(s, "nv").id, created_by=_u(s, "nv").id,
                  customer_name="K", customer_phone=f"09{t.id:08d}", source="web", pax=1, amount=tien, paid=paid))
    s.commit()


def test_no_cu_tach_rieng_va_cong_du():
    s = _db()
    _ban(s, "CU", HOM_NAY - dt.timedelta(days=90), 40_000_000)       # đi 90 ngày trước, còn nợ → nợ cũ
    _ban(s, "GAN", HOM_NAY - dt.timedelta(days=5), 7_000_000)        # đi 5 ngày trước → quá hạn trong ô chính
    _ban(s, "TOI", HOM_NAY + dt.timedelta(days=10), 3_000_000)
    pt = GD.phai_thu_le(s, HOM_NAY)
    assert pt["tong"] == 10_000_000 and pt["so_booking"] == 2
    assert pt["no_cu"]["tong"] == 40_000_000 and pt["no_cu"]["so_booking"] == 1
    assert pt["tong"] + pt["no_cu"]["tong"] == 50_000_000, "hai phần phải cộng đủ số phải thu tour lẻ"


def test_gd_chua_khai_don_vi_thi_cong_ca_khoi_kd():
    s = _db()
    _ban(s, "A", HOM_NAY - dt.timedelta(days=2), 9_000_000)          # kết thúc trong tháng (nếu không sang tháng)
    kq = GD.tong_quan(s)
    o = kq["the"]["doanh_thu_chi_tieu"]
    assert kq["doanh_thu_pham_vi"] == "ca_khoi_kd"
    assert o["so"] is not None, "chưa khai đơn vị mà ô doanh thu tính chỉ tiêu của GĐ vẫn trống"
    assert "doi_chieu" in kq and "thang" in kq["doi_chieu"]


def test_man_chu_tich_xep_hang_le_doc_co_so_chi_tieu():
    src = (GOC / "backend/app/services/dashboard.py").read_text(encoding="utf-8")
    assert 'DT.thang(db, f"{today:%Y-%m}", "le", None)["theo_nguoi"]' in src
    assert 'sec["kd_le_co_so"]' in src
    khoi = (GOC / "web/components/KhoiKinhDoanh.tsx").read_text(encoding="utf-8")
    assert "giá trị booking" in khoi and "doanh thu chuyến" in khoi
    for tep in ("BanGdKdLe", "BanKdKhung"):
        t = (GOC / f"web/components/{tep}.tsx").read_text(encoding="utf-8")
        # R5-12: dòng đối chiếu màn Chủ tịch / TGĐ nay nằm trong khối chung `KhoiNhipDoanhThu` (BanKdKhung).
        # R5-14: phải thu (có `no_cu`) của bàn GĐ nay là khối chung `KhoiPhaiThu` trong BanKdKhung, gọi qua `HangTien`.
        assert ("no_cu" in t or "<HangTien" in t) and ("màn Chủ tịch / TGĐ" in t or "<HangTien" in t)


def test_r5_10_tong_khop_ham_man_chu_tich():
    """R5-10 (Chủ tịch 13/11/2026 23:52): mọi ô có ở màn Chủ tịch đọc ĐÚNG hàm của màn Chủ tịch."""
    gd = (GOC / "backend/app/services/ban_kd_le.py").read_text(encoding="utf-8")
    # R5-21: đọc thẳng dòng tháng của `ket_qua_that.thang` — đúng dòng `doanh_thu_phong` dùng cho ô tháng;
    # bằng số giữa hai đường canh ở test_r5_21_ban_tp_nhanh.
    assert 'KQT.thang(db, f"{d:%Y-%m}")["theo_mang"]["le"]' in gd           # doanh thu chuyến Lẻ
    assert '"dang_ban": gd.get("dang_ban")' in gd                          # tour theo giai đoạn
    assert "float(bk.discount or 0)" in gd                                 # phải thu: − giảm giá như KPI
    vai = (GOC / "backend/app/services/ban_kd_vai.py").read_text(encoding="utf-8")
    assert 'doi_chieu = GD.doi_chieu_chu_tich(db, d)' in vai and 'dt_pv = doi_chieu["thang"]' in vai and "GD.doanh_thu_le(db, nam)" in vai
