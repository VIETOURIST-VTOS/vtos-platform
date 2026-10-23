# -*- coding: utf-8 -*-
"""TQ-1 · Mục «Vận hành & công việc» — phần máy chủ (Chủ tịch chốt v1.1 ngày 22/10/2026).

Canh đúng các ca nghiệm thu của bản v1.1:
  DL02  một hồ sơ nhiều loại cảnh báo → MỘT việc, số cảnh báo đủ, mức cao nhất
  DL04A khác loại hồ sơ, trùng mã → không gộp nhầm
  DL04B mã trần và mã có tiền tố của cùng hồ sơ → về một việc
  DL04C thiếu mã / kind lạ / cảnh báo hệ thống / mức lạ → không mất khỏi tổng, không dồn chung
  PQ01A lọc quyền TRƯỚC gộp: không lộ mức, số lượng của phần bị ẩn
  DL03  quá hạn quyết toán vượt 100 và 300 → tổng đủ, chia trang đủ, không lặp
  DL03B ba nhóm quyết toán: tổng = A + B, C là dòng phụ
  DL06  ranh giới hạn quyết toán: đúng ngày hạn thì CHƯA quá hạn
"""
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
import app.models  # noqa: F401
from app.models.core import Alert, Tour, User
from app.services import tong_quan_tour as TQT
from app.services import tong_quan_viec as TQV

HOM_NAY = date(2026, 10, 22)


@pytest.fixture()
def db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for un, vai in (("ct", "chutich"), ("nvdh", "nv_dh"), ("kt", "ketoan")):
        s.add(User(username=un, full_name=un, role=vai, password_hash="x", active=True))
    s.commit()
    global DH
    DH = s.query(User).filter_by(username="nvdh").one().id
    yield s
    s.close()


def _u(db, un):
    return db.query(User).filter_by(username=un).one()


def _a(db, kind, ref, level="warn", roles="chutich"):
    db.add(Alert(kind=kind, ref=ref, level=level, message="x", to_roles=roles, resolved=False))


# ───────────────────────────── ánh xạ ─────────────────────────────
@pytest.mark.parametrize("kind,ref,ky_vong", [
    ("qua_han_qt", "LE-2610-01", ("tour", "LE-2610-01")),
    ("r9_lech_doanh_thu", "tour:LE-2610-01", ("tour", "LE-2610-01")),
    ("qt_tra_lai", "tour:LE-2610-01", ("tour", "LE-2610-01")),
    ("het_han_giu_cho", "giucho:BK-9", ("booking", "BK-9")),
    ("chua_coc", "booking:BK-9", ("booking", "BK-9")),
    ("kn_qua_han", "KN-5", ("khieu_nai", "KN-5")),
    ("cham_soc_diem_thap", "KN-5", ("khieu_nai", "KN-5")),
    ("zalo_token_hong", "zalo_oa", ("he_thong", "zalo_token_hong")),
    ("r9_gd_cho_khop", "sepay", ("he_thong", "r9_gd_cho_khop")),
    ("sla_booking", "YC-12", ("yeu_cau_dich_vu", "12")),
    ("cong_cho_hcns", "cong:2026-09:ketoan", ("cong_phong_ky", "2026-09:ketoan")),
])
def test_tq1_1_anh_xa_theo_danh_sach_dong(kind, ref, ky_vong):
    assert TQV.khoa_ho_so(1, kind, ref) == ky_vong


def test_tq1_2_khong_anh_xa_duoc_thi_khong_doan():
    """DL04C: ref lạ hoặc rỗng → mỗi cảnh báo một việc riêng, không dồn mọi ref rỗng vào một."""
    assert TQV.khoa_ho_so(7, "loai_moi", "abc") == ("chua_anh_xa", "a7")
    assert TQV.khoa_ho_so(8, "qua_han_qt", "") == ("chua_anh_xa", "a8")
    assert TQV.khoa_ho_so(9, "x", "") != TQV.khoa_ho_so(10, "x", "")


# ───────────────────────────── gộp ─────────────────────────────
def test_tq1_3_mot_ho_so_nhieu_canh_bao_la_mot_viec(db):
    _a(db, "qua_han_qt", "LE-1", "red"); _a(db, "r9_lech_doanh_thu", "tour:LE-1", "warn")
    _a(db, "d7", "LE-1", "info"); db.commit()
    t = TQV.tong(db, _u(db, "ct"))
    assert (t["viec"], t["canh_bao"]) == (1, 3)
    assert [m["viec"] for m in t["theo_muc"]] == [1, 0, 0], "mức của việc = mức nặng nhất"


def test_tq1_4_khac_loai_trung_ma_khong_gop(db):
    _a(db, "chua_coc", "booking:X1"); _a(db, "r9_lech_doanh_thu", "tour:X1"); db.commit()
    assert TQV.tong(db, _u(db, "ct"))["viec"] == 2


def test_tq1_5_loc_quyen_truoc_roi_moi_gop(db):
    """PQ01A: cảnh báo đỏ gửi Kế toán, cảnh báo vàng gửi Điều hành, CÙNG một tour."""
    _a(db, "qua_han_qt", "LE-1", "red", roles="ketoan"); _a(db, "d7", "LE-1", "warn", roles="nv_dh")
    db.commit()
    t = TQV.tong(db, _u(db, "nvdh"))
    assert (t["viec"], t["canh_bao"]) == (1, 1)
    assert [m["viec"] for m in t["theo_muc"]][:2] == [0, 1], "không lộ mức đỏ của phần bị ẩn"
    assert TQV.tong(db, _u(db, "ct"))["theo_muc"][0]["viec"] == 1


def test_tq1_6_khong_mat_khoi_tong(db):
    """DL04C: mức lạ, ref lạ, cảnh báo hệ thống đều còn trong tổng."""
    _a(db, "qua_han_qt", "LE-1", "red"); _a(db, "d7", "LE-1", "do_sai_chinh_ta")
    _a(db, "loai_moi", "zzz"); _a(db, "loai_moi", ""); _a(db, "zalo_token_hong", "zalo_oa")
    db.commit()
    t = TQV.tong(db, _u(db, "ct"))
    assert t["canh_bao"] == 5 and t["viec"] == 4
    assert t["chua_anh_xa"] == 2 and t["canh_bao_chua_phan_loai"] == 1
    assert sum(m["viec"] for m in t["theo_muc"]) == t["viec"]
    assert sum(m["canh_bao"] for m in t["theo_muc"]) == t["canh_bao"]


def test_tq1_7_danh_sach_chia_trang_on_dinh(db):
    for i in range(130):
        _a(db, "qua_han_qt", f"T{i:03d}", "red" if i % 3 == 0 else "warn")
    db.commit()
    u = _u(db, "ct")
    thay = []
    for trang in (1, 2, 3):
        thay += [d["ma"] for d in TQV.danh_sach(db, u, trang=trang, co=50)["dong"]]
    assert len(thay) == 130 and len(set(thay)) == 130, "chia trang không lặp, không sót"
    do = TQV.danh_sach(db, u, muc="red", co=200)
    assert do["so_dong"] == 44 and all(d["muc"] == "red" for d in do["dong"])
    assert do["tong"]["viec"] == 130, "danh sách kèm tổng tính lại để màn hình so với ô"


def test_tq1_8_cua_alerts_dung_chung_luat_loc():
    import inspect
    from app.api.v1 import routes
    src = inspect.getsource(routes.list_alerts)
    assert "loc_theo_vai" in src and "Alert.to_roles.like" not in src, \
        "hai luật xem cho cùng một bảng là hai chỗ sẽ lệch nhau"


# ───────────────────────────── tour ─────────────────────────────
def _tour(db, code, status, end, start=None, loai="le_noi_dia"):
    db.add(Tour(code=code, name=code, tour_type=loai, start_date=start or end - timedelta(days=3),
                end_date=end, status=status, planned_pax=1, operator_id=DH))


def test_tq1_9_qua_han_dem_du_vuot_300(db):
    from app.services import rules as R
    han = int(R.get_param(db, "han_qt_le"))
    for i in range(350):
        _tour(db, f"Q{i:03d}", "ket_thuc", HOM_NAY - timedelta(days=han + 5 + i % 7))
    _tour(db, "DS", "da_dong_so", HOM_NAY - timedelta(days=han + 30))        # chờ Kế toán: không vào
    _tour(db, "BIEN", "ket_thuc", HOM_NAY - timedelta(days=han))              # đúng ngày hạn: chưa quá
    db.commit()
    kq = TQT.qua_han_quyet_toan(db, HOM_NAY, trang=1, co=200)
    assert kq["tong"] == 350, "không còn trần 100/300"
    ma = [r["code"] for r in kq["dong"]] + [r["code"] for r in TQT.qua_han_quyet_toan(db, HOM_NAY, 2, 200)["dong"]]
    assert len(ma) == 350 and len(set(ma)) == 350
    assert "DS" not in ma and "BIEN" not in ma


def test_tq1_10_cho_quyet_toan_ba_nhom(db):
    _tour(db, "A1", "ket_thuc", HOM_NAY - timedelta(days=2)); _tour(db, "A2", "ket_thuc", HOM_NAY)
    _tour(db, "B1", "da_dong_so", HOM_NAY - timedelta(days=1))
    _tour(db, "C1", "da_duyet", HOM_NAY - timedelta(days=1))                  # đã về, chưa đóng sổ
    _tour(db, "D1", "da_duyet", HOM_NAY + timedelta(days=9))                  # còn bán: không vào nhóm nào
    db.commit()
    c = TQT.cho_quyet_toan(db, HOM_NAY)
    assert (c["ket_thuc"], c["da_dong_so"], c["da_ve_chua_dong_so"]) == (2, 1, 1)
    assert c["tong"] == 3, "Chủ tịch chốt: tổng = A + B; C là dòng phụ"


def test_tq1_11_thieu_lich_chi_dem_phan_nam_trong_dang_chay():
    """Đúng ba nhánh của dem_tour.theo_giai_doan. Mô hình để ngày NOT NULL nên đo trên dữ liệu thật
    là 0 — phép đếm vẫn phải đúng cho bảng dựng qua bản nâng cấp cũ."""
    h = HOM_NAY
    cap = [(h - timedelta(days=1), None),          # thiếu ngày về → đang chạy → ĐẾM
           (None, None),                           # thiếu cả hai → đang chạy → ĐẾM
           (h + timedelta(days=5), None),          # ngày đi tương lai → đang bán
           (None, h - timedelta(days=4)),          # ngày về quá khứ → đã về
           (h - timedelta(days=1), h + timedelta(days=1))]   # đủ ngày, đang chạy → không thiếu lịch
    assert TQT.dem_thieu_lich(cap, h) == 2


def test_tq1_12_thieu_lich_tren_csdl(db):
    _tour(db, "Y1", "da_duyet", HOM_NAY + timedelta(days=1), start=HOM_NAY - timedelta(days=1)); db.commit()
    assert TQT.thieu_lich(db, HOM_NAY) == 0


def test_tq1_13_nhan_canh_bao_do_may_chu_dich(db):
    """Màn hình không tự dịch mã loại: máy chủ trả nhãn cùng bảng GD-1; mã chưa khai giữ nguyên."""
    _a(db, "qua_han_qt", "LE-7", "red"); _a(db, "ma_chua_khai_xyz", "tour:LE-7"); db.commit()
    d = TQV.danh_sach(db, _u(db, "ct"))["dong"][0]
    assert d["loai_canh_bao"] == ["ma_chua_khai_xyz", "qua_han_qt"]
    assert d["nhan_canh_bao"] == ["ma_chua_khai_xyz", "Chuyến quá hạn quyết toán"]
