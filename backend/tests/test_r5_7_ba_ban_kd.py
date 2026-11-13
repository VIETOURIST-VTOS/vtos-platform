"""R5-7 · Ba bàn Trưởng phòng / Trưởng nhóm / Chuyên viên Kinh doanh lẻ — Chủ tịch duyệt 13/11/2026.

Canh những chỗ dễ hỏng nhất:
    1. Chuyên viên KHÔNG BAO GIỜ thấy số của người khác (Chủ tịch chốt «chỉ của mình»).
    2. Trưởng nhóm thấy đúng nhóm mình, Trưởng phòng thấy cả phòng (đơn vị con cộng lên).
    3. Chỉ tiêu chưa giao → None «chưa giao», không 0 (Chủ tịch tự giao).
    4. Phải thu chỉ cộng booking của người trong phạm vi.
    5. Cửa chỉ mở cho ba vai; ba bàn là ba tệp riêng; /fit dựng đúng bàn theo vai.
"""
import datetime as dt
import pathlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.services import ban_kd_vai as S
from app.services import chi_tieu_kd as CT
from app.services import to_chuc_kd as TC
from app.api.v1 import ban_kd_le as API

HOM_NAY = dt.date.today()
GOC = pathlib.Path(__file__).resolve().parents[2]


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("hc", "hcns"), ("tp", "tp_kd"), ("tn1", "tn_kd"), ("nv1", "nv_kd"), ("nv2", "nv_kd"),
                     ("tn2", "tn_kd"), ("nv3", "nv_kd"), ("dh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    u = lambda t: s.execute(select(User).where(User.username == t)).scalars().first()  # noqa: E731
    hc = u("hc"); tu = HOM_NAY.replace(day=1) - dt.timedelta(days=40)
    cn = TC.tao_don_vi(s, hc, "LE-CN", "Chi nhánh HCM", "chi_nhanh", hieu_luc_tu=tu)
    phong = TC.tao_don_vi(s, hc, "LE-P", "Phòng Lẻ", "phong", cha_id=cn.id, hieu_luc_tu=tu)
    n1 = TC.tao_don_vi(s, hc, "LE-N1", "Nhóm 1", "team", cha_id=phong.id, hieu_luc_tu=tu)
    n2 = TC.tao_don_vi(s, hc, "LE-N2", "Nhóm 2", "team", cha_id=phong.id, hieu_luc_tu=tu)
    for ten, dv, vai in (("tp", phong, "truong_phong"), ("tn1", n1, "leader"), ("nv1", n1, "nhan_vien"),
                         ("nv2", n1, "nhan_vien"), ("tn2", n2, "leader"), ("nv3", n2, "nhan_vien")):
        TC.phan_cong(s, hc, u(ten).id, dv.id, vai, tu)
    s.commit()
    return s, u, {"phong": phong, "n1": n1, "n2": n2}


def _ban(s, u, nguoi, tien, ma, ngay_ket_thuc=None, paid=0):
    kt = ngay_ket_thuc or HOM_NAY
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=kt - dt.timedelta(days=2), end_date=kt,
             operator_id=u("dh").id, status="da_duyet", price_per_pax=tien, planned_pax=10, seats_open=10)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=u(nguoi).id, customer_name="K", customer_phone=f"09{t.id:08d}",
                       source="web", pax=1)
    s.add(r); s.flush()
    s.add(Booking(code=ma + "-B", tour_id=t.id, request_id=r.id, sales_id=u(nguoi).id, created_by=u(nguoi).id,
                  customer_name="K", customer_phone=f"09{t.id:08d}", source="web", pax=1, amount=tien, paid=paid))
    s.commit()


def test_chuyen_vien_chi_thay_so_cua_minh():
    s, u, _ = _db()
    _ban(s, u, "nv1", 10_000_000, "A"); _ban(s, u, "nv2", 30_000_000, "B")
    kq = S.tong_quan(s, u("nv1"))
    assert kq["vai"] == "nv" and kq["so_nguoi"] == 1
    assert kq["the"]["doanh_thu"]["so"] == 10_000_000
    assert kq["doi_ngu"] == [] and kq["theo_nhom"] == [], "chuyên viên không được thấy bảng người khác"
    assert "NV2" not in str(kq)


def test_truong_nhom_thay_nhom_minh_truong_phong_thay_ca_phong():
    s, u, dv = _db()
    _ban(s, u, "nv1", 10_000_000, "A"); _ban(s, u, "nv2", 30_000_000, "B"); _ban(s, u, "nv3", 50_000_000, "C")
    _ban(s, u, "tn1", 5_000_000, "D")
    tn = S.tong_quan(s, u("tn1"))
    assert tn["the"]["doanh_thu"]["so"] == 45_000_000
    assert tn["the"]["doanh_thu_toi"]["so"] == 5_000_000, "Chủ tịch giữ ô «Doanh thu của tôi» cho Trưởng nhóm"
    assert {x["ho_ten"] for x in tn["doi_ngu"]} == {"TN1", "NV1", "NV2"}
    assert tn["theo_nhom"] == []
    tp = S.tong_quan(s, u("tp"))
    assert tp["the"]["doanh_thu"]["so"] == 95_000_000
    assert len(tp["doi_ngu"]) == 6 and tp["doi_ngu"][0]["ho_ten"] == "NV3"
    assert [g["ma"] for g in tp["theo_nhom"]] == ["LE-N1", "LE-N2"]
    assert [g["tien"] for g in tp["theo_nhom"]] == [45_000_000, 50_000_000]


def test_chi_tieu_chua_giao_la_none_giao_roi_thi_co():
    s, u, dv = _db()
    kq = S.tong_quan(s, u("nv1"))
    assert kq["the"]["doanh_thu"]["chi_tieu"] is None
    ky = f"{HOM_NAY:%Y-%m}"
    CT.dat(s, u("hc"), ky, 300_000_000, user_id=u("nv1").id, luong="le"); s.commit()
    CT.dat(s, u("hc"), ky, 900_000_000, don_vi_id=dv["n1"].id, luong="le"); s.commit()
    assert S.tong_quan(s, u("nv1"))["the"]["doanh_thu"]["chi_tieu"] == 300_000_000
    tn = S.tong_quan(s, u("tn1"))
    assert tn["the"]["doanh_thu"]["chi_tieu"] == 900_000_000
    assert next(x for x in tn["doi_ngu"] if x["ho_ten"] == "NV1")["chi_tieu"] == 300_000_000
    assert next(x for x in tn["doi_ngu"] if x["ho_ten"] == "NV2")["chi_tieu"] is None


def test_phai_thu_chi_cong_booking_trong_pham_vi():
    s, u, _ = _db()
    xa = HOM_NAY + dt.timedelta(days=20)
    _ban(s, u, "nv1", 10_000_000, "A", xa); _ban(s, u, "nv3", 7_000_000, "C", xa)
    assert S.tong_quan(s, u("nv1"))["the"]["phai_thu"]["so"] == 10_000_000
    assert S.tong_quan(s, u("tn2"))["the"]["phai_thu"]["so"] == 7_000_000
    assert S.tong_quan(s, u("tp"))["the"]["phai_thu"]["so"] == 17_000_000


def test_chua_phan_cong_thi_canh_bao_khong_muon_pham_vi():
    s, u, _ = _db()
    s.add(User(username="tp2", full_name="TP2", role="tp_kd", password_hash="x")); s.commit()
    kq = S.tong_quan(s, u("tp2"))
    assert kq["canh_bao"] and kq["so_nguoi"] == 1 and kq["the"]["doanh_thu"]["so"] is None


def test_cua_chi_mo_cho_ba_vai_va_ba_ban_rieng():
    assert set(API.VAI_PHONG) == {"tp_kd", "tn_kd", "nv_kd"}
    for tep, cua in (("BanTpKd", "/ban-kd-le/vai/tong-quan"), ("BanTnKd", "/ban-kd-le/vai/tong-quan"),
                     ("BanNvKd", "/ban-kd-le/vai/tong-quan")):
        src = (GOC / f"web/components/{tep}.tsx").read_text(encoding="utf-8")
        assert "export default function" in src and "<input" not in src and 'method: "POST"' not in src
    fit = (GOC / "web/app/fit/page.tsx").read_text(encoding="utf-8")
    for tep in ("BanTpKd", "BanTnKd", "BanNvKd"):
        assert f"<{tep} />" in fit
    nv = (GOC / "web/components/BanNvKd.tsx").read_text(encoding="utf-8")
    assert "/phieu-luong" in nv and "/reports" in nv, "Chuyên viên: lương của tôi, báo cáo / đề xuất (tạm dùng Báo cáo công việc)"
    chung = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")
    khoi = chung.split("<style>{`", 1)[1].split("`}</style>", 1)[0]
    assert "`" not in khoi
