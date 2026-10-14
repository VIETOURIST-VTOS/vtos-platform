# -*- coding: utf-8 -*-
"""DL-2 · Số khách sống đến ngày đi.

Chủ tịch 13/10/2026: "số khách sẽ do nhân viên điều hành nhập tay và điều chỉnh đến ngày đi".

ĐO TRƯỚC KHI VIẾT: cửa `Đề nghị xe` chỉ có TẠO / TỪ CHỐI / HUỶ — không một đường PUT nào, không
một hàm sửa nào. Nên khi số khách đổi, Điều hành chỉ còn hai lối: huỷ rồi đề nghị lại từ đầu, hoặc
để nguyên con số cũ. Lối thứ hai dễ hơn nên nó sẽ là lối người ta đi — và Giám đốc đội xe thì quyết
điều mấy chiếc DỰA TRÊN con số ấy.

Đoàn khai 40 khách → lập lệnh một xe 45 chỗ → đến ngày đi thành 52 khách. Lệnh vẫn hiệu lực, vẫn
xanh, và chỗ phát hiện ra là bãi xe lúc 5 giờ sáng. Mốc 45 chỗ chính là ranh giới mà máy không biết
là có.

BA LUẬT, cả ba đều được kiểm ngược:
  1. Sửa được đến HẾT ngày đi, qua ngày đi thì thôi — và số cũ KHÔNG mất.
  2. Soát ghế đếm theo LỆNH CÒN HIỆU LỰC. Chưa có lệnh nào thì trả None, KHÔNG trả "đủ chỗ".
  3. Hàng rào đếm ngược chỉ nhắc đoàn CHƯA AI ĐỤNG vào số khách kể từ lúc lập.
"""
import os
import tempfile
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour, User  # noqa: E402
from app.models.hr import Vehicle, Employee, DispatchOrder  # noqa: E402
from app.models.de_nghi_xe import DeNghiXe  # noqa: E402
from app.services import de_nghi_xe as DN  # noqa: E402

HOM_NAY = date(2026, 10, 13)


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nguoi(db, ten="dieuhanh1", vai="nv_dh"):
    u = User(username=ten, full_name="Nhân viên ĐH", role=vai, password_hash="x")
    db.add(u); db.flush()
    return u


def _tour(db, ma="T-001"):
    nv = Employee(code=f"NV{ma}", full_name="Điều hành viên", department="Điều hành")
    db.add(nv); db.flush()
    t = Tour(code=ma, name="Đà Lạt 3N2Đ", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 10, 20), end_date=date(2026, 10, 22))
    db.add(t); db.flush()
    return t


def _de_nghi(db, t, khach=40, xe=1, di=date(2026, 10, 20), tt="cho_lap_lenh"):
    d = DeNghiXe(tour_id=t.id, ngay_di=di, ngay_ve=di + timedelta(days=2), so_khach=khach,
                 so_xe_can=xe, trang_thai=tt, nguoi_de_nghi="dieuhanh1")
    db.add(d); db.flush()
    return d


def _lenh(db, t, d, cho=45, bien="50F-017.37", status="cho_xac_nhan"):
    v = Vehicle(plate=bien, seats=cho); db.add(v); db.flush()
    e = Employee(code=f"TX{bien[-5:]}", full_name="Tài xế A", department="Đội xe")
    db.add(e); db.flush()
    o = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=e.id, de_nghi_id=d.id,
                      date_from=d.ngay_di, date_to=d.ngay_ve, status=status)
    db.add(o); db.flush()
    return o


# ═════════════════ 1 · CỬA SỬA ═════════════════

def test_sua_duoc_so_khach_va_SO_CU_KHONG_MAT(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, khach=40)
    DN.sua_so_khach(db, u, d.id, 52, ly_do="khách báo thêm 12", hom_nay=HOM_NAY)
    assert d.so_khach == 52
    ls = DN.lich_su_so_khach(db, d.id)
    assert len(ls) == 1
    assert ls[0]["so_khach_cu"] == 40 and ls[0]["so_khach_moi"] == 52
    assert ls[0]["ly_do"] == "khách báo thêm 12" and ls[0]["boi"] == "dieuhanh1"


def test_sua_duoc_ca_khi_DA_LAP_LENH(db):
    """Khoá lại sau khi lập lệnh là đẩy Điều hành về đúng hai lối cũ — huỷ cả đề nghị, hoặc im lặng."""
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, khach=40, tt="da_lap_lenh")
    _lenh(db, t, d, cho=45)
    kq = DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)
    assert kq["so_khach"] == 52


def test_qua_NGAY_DI_thi_khong_sua_o_day_nua(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, di=date(2026, 10, 12))
    with pytest.raises(ValueError, match="đã khởi hành"):
        DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)


def test_dung_NGAY_DI_van_sua_duoc(db):
    """Ranh giới là HẾT ngày đi, không phải trước ngày đi — đoàn đi chiều vẫn chốt số buổi sáng."""
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, di=HOM_NAY)
    assert DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)["so_khach"] == 52


def test_de_nghi_da_huy_thi_khong_con_so_khach_de_sua(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, tt="huy")
    with pytest.raises(ValueError, match="từ chối hoặc đã huỷ"):
        DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)


def test_khong_ghi_mot_lan_sua_RONG(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, khach=40, xe=1)
    with pytest.raises(ValueError, match="không đổi"):
        DN.sua_so_khach(db, u, d.id, 40, 1, hom_nay=HOM_NAY)
    assert DN.lich_su_so_khach(db, d.id) == []


def test_so_khach_bang_0_bi_chan(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t)
    with pytest.raises(ValueError, match="lớn hơn 0"):
        DN.sua_so_khach(db, u, d.id, 0, hom_nay=HOM_NAY)


# ═════════════════ 2 · SOÁT GHẾ ═════════════════

def test_vuot_ghe_thi_NOI_RA_va_dem_dung_so_thieu(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, khach=40, tt="da_lap_lenh")
    _lenh(db, t, d, cho=45)
    kq = DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)
    c = kq["canh_bao_ghe"]
    assert c["du_cho"] is False and c["thieu_ghe"] == 7
    assert "THIẾU 7 chỗ" in c["noi"]


def test_chua_co_lenh_nao_thi_tra_None_chu_KHONG_noi_du_cho(db):
    """Trả 'đủ chỗ' cho một đề nghị chưa có xe nào là nói một điều không có nghĩa, và người đọc tin."""
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, khach=40)
    assert DN.soat_ghe(db, d) is None
    assert DN.sua_so_khach(db, u, d.id, 52, hom_nay=HOM_NAY)["canh_bao_ghe"] is None


def test_lenh_DA_HUY_khong_duoc_tinh_la_con_cho(db):
    """Đếm cả lệnh đã huỷ là báo đủ chỗ cho một đoàn thật ra không còn xe nào."""
    t = _tour(db)
    d = _de_nghi(db, t, khach=40, tt="da_lap_lenh")
    _lenh(db, t, d, cho=45, status="huy")
    assert DN.soat_ghe(db, d) is None, "mọi lệnh đã huỷ thì coi như chưa có lệnh"


def test_hai_xe_thi_cong_ghe_cua_ca_hai(db):
    t = _tour(db)
    d = _de_nghi(db, t, khach=70, xe=2, tt="da_lap_lenh")
    _lenh(db, t, d, cho=45, bien="50F-017.37")
    _lenh(db, t, d, cho=29, bien="50H-498.29")
    c = DN.soat_ghe(db, d)
    assert c["tong_ghe"] == 74 and c["du_cho"] is True and c["thieu_ghe"] == 0


def test_bang_dem_thieu_ghe_chi_dem_de_nghi_DA_CO_LENH(db):
    t = _tour(db)
    d1 = _de_nghi(db, t, khach=52, tt="da_lap_lenh"); _lenh(db, t, d1, cho=45)
    _de_nghi(db, t, khach=99, tt="cho_lap_lenh")      # chưa có lệnh – chưa tới lượt soát
    kq = DN.thieu_ghe(db)
    assert kq["so"] == 1 and kq["rows"][0]["de_nghi"] == d1.id


# ═════════════════ 3 · HÀNG RÀO ĐẾM NGƯỢC ═════════════════

def test_nhac_doan_sap_di_ma_CHUA_AI_dung_vao_so_khach(db):
    t = _tour(db)
    _de_nghi(db, t, di=HOM_NAY + timedelta(days=1))
    kq = DN.can_xac_nhan_lai(db, gio=48, hom_nay=HOM_NAY)
    assert kq["so"] == 1 and "chưa ai xác nhận lại" in kq["rows"][0]["noi"]


def test_sua_roi_thi_THOI_NHAC(db):
    u, t = _nguoi(db), _tour(db)
    d = _de_nghi(db, t, di=HOM_NAY + timedelta(days=1))
    DN.sua_so_khach(db, u, d.id, 44, hom_nay=HOM_NAY)
    assert DN.can_xac_nhan_lai(db, gio=48, hom_nay=HOM_NAY)["so"] == 0


def test_doan_con_xa_thi_chua_nhac(db):
    """Nhắc dày quá thì người ta tắt, và một hàng rào bị tắt thì tệ hơn không có."""
    t = _tour(db)
    _de_nghi(db, t, di=HOM_NAY + timedelta(days=20))
    assert DN.can_xac_nhan_lai(db, gio=48, hom_nay=HOM_NAY)["so"] == 0


def test_doan_da_bi_huy_thi_khong_nhac(db):
    t = _tour(db)
    _de_nghi(db, t, di=HOM_NAY + timedelta(days=1), tt="huy")
    assert DN.can_xac_nhan_lai(db, gio=48, hom_nay=HOM_NAY)["so"] == 0
