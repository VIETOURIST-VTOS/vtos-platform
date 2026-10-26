# -*- coding: utf-8 -*-
"""KH-4 · Cổng khách — đánh giá chuyến đi, góp ý riêng lãnh đạo, hỗ trợ đổi / hủy / hóa đơn.

Chủ tịch duyệt bản xem thử 27/10/2026:
  1. Đánh giá ghi vào `danh_gia_sau_tour` (nguồn «khach»), chỉ chuyến đã đi, mở 30 ngày, sửa 30 ngày;
     mục bỏ trống là RỖNG không phải 0; đồng ý công khai hỏi riêng, không mặc định; điểm thấp đi
     đúng luật mở khiếu nại của `cskh.ghi_ket_qua`.
  2. Góp ý riêng: chỉ Chủ tịch + TGĐ trả lời; BKS đọc, không ghi; vai khác không đọc; khách không
     thấy ghi chú nội bộ.
  3. Hỗ trợ: đổi/hủy → Sales của booking; hóa đơn → Kế toán; khác → Sale Admin; Sales chỉ thấy
     việc của mình; gửi yêu cầu hủy KHÔNG hủy booking.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 11, 10, 9, 0)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("kd", "nv_kd"), ("kd2", "nv_kd"), ("kt", "ketoan"), ("ktt", "ketoan_truong"),
                     ("sa", "sales_admin"), ("ct", "chutich"), ("tgd", "tgd"), ("bks", "bks"), ("tpkd", "tp_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "_hom_nay", lambda: NOW.date())
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


_n = {"i": 0}


def _bk(s, bat_dau, ket_thuc, sdt="0901234567", huy=False, trang_thai="ket_thuc"):
    from app.models.core import Tour, Booking, ServiceRequest
    _n["i"] += 1; i = _n["i"]
    t = Tour(code=f"T{i}", name=f"Huế {i}", tour_type="le_noi_dia", start_date=bat_dau, end_date=ket_thuc,
             operator_id=_u(s, "dh").id, status=trang_thai, price_per_pax=3_000_000, planned_pax=30)
    s.add(t); s.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(s, "kd").id, customer_name="An", customer_phone=sdt, source="web", pax=1)
    s.add(r); s.flush()
    b = Booking(code=f"BK2611{i:04d}", tour_id=t.id, request_id=r.id, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="An", customer_phone=sdt, source="web", pax=1, amount=3_000_000, discount=0, cancelled=huy)
    s.add(b); s.commit()
    return b


def _tk(s, sdt="0901234567"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai=sdt, trang_thai="hoat_dong", ho_ten="An")
    s.add(tk); s.commit()
    return tk


def _phieu(c, diem: dict):
    return [{"doi_tuong": m["doi_tuong"], "id": m["id"], "diem": diem.get(m["doi_tuong"]), "nhan_xet": ""} for m in c["muc"]]


# ── 1 · ĐÁNH GIÁ ─────────────────────────────────────────────────────────────────────────────

def test_chi_chuyen_da_di_trong_30_ngay_moi_cham(db):
    from app.services import cham_soc_khach as CK
    tk = _tk(db)
    xong = _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3))
    sap = _bk(db, dt.date(2026, 11, 20), dt.date(2026, 11, 22), trang_thai="da_duyet")
    cu = _bk(db, dt.date(2026, 9, 1), dt.date(2026, 9, 3))
    _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3), huy=True)
    ds = {c["ma"]: c for c in CK.chuyen_danh_gia(db, tk, NOW)}
    assert ds[xong.code]["trang_thai"] == "mo" and ds[sap.code]["trang_thai"] == "chua_di"
    assert ds[cu.code]["trang_thai"] == "het_han" and len(ds) == 3, "booking đã hủy không được chấm"
    muc = [m["doi_tuong"] for m in ds[xong.code]["muc"]]
    # chưa có đơn dịch vụ nào: hiện mục mảng để khách tự bỏ trống; nhiều ngày → có khách sạn; có Sales → tư vấn
    assert muc[:2] == ["tour", "hanh_trinh"] and {"xe", "khach_san", "an_uong", "tham_quan", "tu_van"} <= set(muc)
    for ma in (sap.code, cu.code):
        with pytest.raises(CK.LoiCham):
            CK.gui_danh_gia(db, tk, ma, {"diem": [{"doi_tuong": "tour", "id": None, "diem": 5}],
                                         "nhu_cau_tiep": "co", "cong_khai": "co"}, NOW)


def test_gui_ghi_vao_bang_danh_gia_chung_rong_khong_phai_0_va_dong_y_rieng(db):
    from app.services import cham_soc_khach as CK
    from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai
    from app.models.cskh import CareTicket
    tk = _tk(db)
    b = _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3))
    c = CK.chuyen_danh_gia(db, tk, NOW)[0]
    with pytest.raises(CK.LoiCham, match="công khai"):      # không có mặc định cho câu đồng ý
        CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {"tour": 5}), "nhu_cau_tiep": "co"}, NOW)
    with pytest.raises(CK.LoiCham, match="ít nhất"):
        CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {}), "nhu_cau_tiep": "co", "cong_khai": "co"}, NOW)
    r = CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {"tour": 5, "hanh_trinh": 4, "xe": 3}),
                                         "nhu_cau_tiep": "khong", "cong_khai": "co", "gop_y": "Tốt"}, NOW)
    assert r["han_sua"] == "2026-12-10"
    dong = db.execute(select(DanhGiaSauTour).where(DanhGiaSauTour.booking_id == b.id)).scalars().all()
    assert {d.doi_tuong: d.diem for d in dong} == {"tour": 5, "hanh_trinh": 4, "xe": 3}, "mục bỏ trống không được ghi 0"
    assert all(d.nguon == "khach" for d in dong)
    dy = db.execute(select(DongYCongKhai)).scalars().all()
    assert len(dy) == 3 and all(x.tra_loi == "co" and x.nguon == "cong_khach" for x in dy)
    care = db.execute(select(CareTicket).where(CareTicket.booking_id == b.id)).scalars().one()
    assert care.hinh_thuc == "cong" and care.hai_long == 5 and care.complaint_id is None
    c2 = CK.chuyen_danh_gia(db, tk, NOW)[0]
    assert c2["trang_thai"] == "da_gui" and c2["sua_duoc"] and c2["cong_khai"] == "co"


def test_diem_thap_mo_khieu_nai_bang_luat_cu_va_sua_trong_30_ngay(db):
    from app.services import cham_soc_khach as CK
    from app.models.cskh import CareTicket
    from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai
    tk = _tk(db)
    b = _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3))
    c = CK.chuyen_danh_gia(db, tk, NOW)[0]
    CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {"tour": 2, "an_uong": 2}), "nhu_cau_tiep": "khong", "cong_khai": "co"}, NOW)
    care = db.execute(select(CareTicket).where(CareTicket.booking_id == b.id)).scalars().one()
    assert care.complaint_id, "điểm thấp phải mở khiếu nại bằng đúng luật của cskh.ghi_ket_qua"
    kn = care.complaint_id
    # Sửa: đổi điểm, bỏ một mục (thành RỖNG), rút đồng ý công khai
    sau = NOW + dt.timedelta(days=20)
    CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {"tour": 4}), "nhu_cau_tiep": "co", "cong_khai": "khong"}, sau)
    db.refresh(care)
    assert care.complaint_id == kn, "sửa đánh giá không mở thêm khiếu nại"
    d = {x.doi_tuong: x.diem for x in db.execute(select(DanhGiaSauTour).where(DanhGiaSauTour.booking_id == b.id)).scalars()}
    assert d == {"tour": 4, "an_uong": None}
    assert all(x.rut_luc is not None for x in db.execute(select(DongYCongKhai)).scalars()), "rút đồng ý phải đi đường rút"
    with pytest.raises(CK.LoiCham, match="quá hạn sửa"):
        CK.gui_danh_gia(db, tk, b.code, {"diem": _phieu(c, {"tour": 5}), "nhu_cau_tiep": "co"}, NOW + dt.timedelta(days=31))


def test_khong_cham_muc_khong_thuoc_chuyen_va_don_nguoi_khac(db):
    from app.services import cham_soc_khach as CK
    tk = _tk(db)
    b = _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3))
    la = _bk(db, dt.date(2026, 11, 1), dt.date(2026, 11, 3), sdt="0988888888")
    with pytest.raises(CK.LoiCham, match="không thuộc"):
        CK.gui_danh_gia(db, tk, b.code, {"diem": [{"doi_tuong": "hdv", "id": 999, "diem": 1}],
                                         "nhu_cau_tiep": "co", "cong_khai": "co"}, NOW)
    with pytest.raises(CK.LoiCham, match="Không tìm thấy"):
        CK.gui_danh_gia(db, tk, la.code, {"diem": [{"doi_tuong": "tour", "id": None, "diem": 5}],
                                          "nhu_cau_tiep": "co", "cong_khai": "co"}, NOW)


# ── 2 · GÓP Ý RIÊNG LÃNH ĐẠO ───────────────────────────────────────────────────────────────────

def test_gop_y_chi_chu_tich_tgd_tra_loi_bks_chi_doc(db):
    from app.services import cham_soc_khach as CK
    tk = _tk(db)
    g = CK.gui_gop_y(db, tk, {"tieu_de": "Thái độ nhân viên", "noi_dung": "Nhân viên KD trả lời cộc lốc khi tôi đổi ngày"}, NOW)
    assert g.ma.startswith("GY-")
    for ten in ("kd", "tpkd", "kt", "sa"):
        with pytest.raises(CK.LoiCham):
            CK.ds_gop_y(db, _u(db, ten))
    assert len(CK.ds_gop_y(db, _u(db, "bks"))) == 1
    with pytest.raises(CK.LoiCham):
        CK.cap_nhat_gop_y(db, _u(db, "bks"), g.id, {"trang_thai": "dong"})
    with pytest.raises(CK.LoiCham, match="trả lời trước"):
        CK.cap_nhat_gop_y(db, _u(db, "ct"), g.id, {"trang_thai": "da_tra_loi"})
    CK.cap_nhat_gop_y(db, _u(db, "tgd"), g.id, {"trang_thai": "da_tra_loi", "tra_loi": "Đã chỉ đạo rút kinh nghiệm",
                                                "ghi_chu_noi_bo": "Giao TP KD xác minh"}, NOW)
    cua_khach = CK.gop_y_cua(db, tk)[0]
    assert cua_khach["tra_loi"] == "Đã chỉ đạo rút kinh nghiệm" and "ghi_chu_noi_bo" not in cua_khach


def test_menu_gop_y_dung_bon_vai_nen(db):
    from app.services import access as AC
    assert set(AC.MENU_ROLES["/gop-y-lanh-dao"]) == set(AC.BASE_VIEW)
    assert AC.MAN_HINH_API["/gop-y-lanh-dao"] == ("/api/v1/gop-y-lanh-dao",)
    assert AC.MAN_HINH_API["/yeu-cau-khach"] == ("/api/v1/yeu-cau-khach",)


# ── 3 · HỖ TRỢ ────────────────────────────────────────────────────────────────────────────────

def test_ho_tro_chuyen_dung_bo_phan_va_khong_tu_huy(db):
    from app.services import cham_soc_khach as CK
    from app.models.core import Booking
    tk = _tk(db)
    b = _bk(db, dt.date(2026, 11, 20), dt.date(2026, 11, 22), trang_thai="da_duyet")
    huy = CK.gui_ho_tro(db, tk, {"loai": "huy", "ma_don": b.code, "noi_dung": "Gia đình có việc"}, NOW)
    assert huy.bo_phan == "kinh_doanh" and huy.giao_cho_id == _u(db, "kd").id
    db.refresh(b)
    assert b.cancelled is False, "gửi yêu cầu hủy KHÔNG được hủy booking"
    with pytest.raises(CK.LoiCham, match="Mã số thuế"):
        CK.gui_ho_tro(db, tk, {"loai": "hoa_don", "ma_don": b.code,
                               "hoa_don": {"ten_don_vi": "ABC", "mst": "12AB", "dia_chi": "HN"}}, NOW)
    hd = CK.gui_ho_tro(db, tk, {"loai": "hoa_don", "ma_don": b.code,
                                "hoa_don": {"ten_don_vi": "Công ty ABC", "mst": "0101234567", "dia_chi": "Hà Nội"}}, NOW)
    khac = CK.gui_ho_tro(db, tk, {"loai": "khac", "noi_dung": "Cho tôi hỏi visa Nhật"}, NOW)
    assert hd.bo_phan == "ke_toan" and khac.bo_phan == "sales_admin"
    with pytest.raises(CK.LoiCham, match="chọn đơn"):
        CK.gui_ho_tro(db, tk, {"loai": "doi", "noi_dung": "đổi ngày"}, NOW)

    thay = lambda ten: {y["ma"] for y in CK.ds_ho_tro(db, _u(db, ten))}  # noqa: E731
    assert thay("kd") == {huy.ma}, "Sales chỉ thấy việc giao cho mình"
    assert thay("kd2") == set()
    assert thay("kt") == {hd.ma} and thay("ktt") == {hd.ma}, "Kế toán trưởng kế thừa Kế toán"
    assert thay("sa") == {huy.ma, khac.ma} and thay("tpkd") == {huy.ma, khac.ma}
    assert thay("ct") == {huy.ma, hd.ma, khac.ma}
    with pytest.raises(CK.LoiCham):
        CK.cap_nhat_ho_tro(db, _u(db, "kd2"), huy.id, {"hanh_dong": "nhan"})
    with pytest.raises(CK.LoiCham, match="Trả lời khách trước"):
        CK.cap_nhat_ho_tro(db, _u(db, "kd"), huy.id, {"hanh_dong": "dong"})
    CK.cap_nhat_ho_tro(db, _u(db, "kd"), huy.id, {"hanh_dong": "tra_loi", "tra_loi": "Phí hủy theo hợp đồng 10%, anh xác nhận giúp em"})
    CK.cap_nhat_ho_tro(db, _u(db, "kd"), huy.id, {"hanh_dong": "dong"})
    x = {y["ma"]: y for y in CK.ho_tro_cua(db, tk)}
    assert x[huy.ma]["trang_thai"] == "dong" and x[huy.ma]["tra_loi"].startswith("Phí hủy") and "giao_cho" not in x[huy.ma]
    CK.cap_nhat_ho_tro(db, _u(db, "sa"), khac.id, {"hanh_dong": "chuyen", "bo_phan": "ke_toan"})
    assert khac.ma in thay("kt") and khac.ma not in thay("sa")
