# -*- coding: utf-8 -*-
"""DL-6 · Chuyến máy sinh ra từ lệnh phải NÓI RA nó còn thiếu gì (Chủ tịch chốt 16/10/2026).

VÌ SAO CÓ VÒNG NÀY, và một chỗ em đã báo sai. Ngày 15/10 em nói với Chủ tịch «chưa có cửa nhập km
và chi phí thật». Đo lại: SAI. Cửa sửa chuyến có đủ ô km đầu, km cuối, km GPS và nguồn số km; bảng
chi phí chuyến (`fleet_trip_costs`) có loại, số tiền, SỐ LÍT, chứng từ, bên chịu, và có cả ba cửa
thêm – sửa – xoá. Cửa không thiếu.

Chỗ hỏng thật là chuyến máy sinh ra ĐẾN LẶNG LẼ, ba việc:

  1. `Trip.co` mặc định "vang" và `co_ly_do` RỖNG. Một chuyến vàng không nói vì sao thì người xem
     hoặc bỏ qua, hoặc đoán — đoán sai còn tệ hơn không có cờ.
  2. Lời đóng lệnh nói "km và chi phí còn trống" cho MỌI chuyến. Một câu luôn đúng là câu không
     ai đọc.
  3. Không có danh sách để làm theo.

KHÔNG CHẶN — Chủ tịch chọn «báo và đếm». 756 chuyến nạp bằng Excel đều thiếu km; một hàng rào
chặn ở đây sẽ chặn nhầm cả sổ cũ.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.fleet import Trip, TripCost  # noqa: E402
from app.models.hr import DispatchOrder, Employee, Vehicle  # noqa: E402
from app.services import dong_lenh as DL  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nen(db):
    v = Vehicle(plate="50H-934.08", code="XE0013", seats=45)
    nv = Employee(code="NV1", full_name="Điều hành viên", department="dieu_hanh")
    tx = Employee(code="TX1", full_name="Phan Tấn Thuận", department="doi_xe")
    db.add_all([v, nv, tx]); db.flush()
    t = Tour(code="DL-0825", name="Phan Thiết 2N1Đ", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 8, 16), end_date=date(2026, 8, 18))
    db.add(t); db.flush()
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=tx.id,
                      date_from=date(2026, 8, 16), date_to=date(2026, 8, 18),
                      internal_price=10_500_000, created_by="gddx", status="da_xac_nhan")
    db.add(d); db.flush()
    return v, tx, t, d


# ═══════════════ Cờ phải được chấm, và phải mang lý do
def test_chuyen_may_sinh_co_co_VA_co_ly_do(db):
    """Cờ vàng không có lý do thì người xem phải đoán — và đoán sai tệ hơn không có cờ."""
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    assert kq["viec"] == "da_sinh"
    ch = db.get(Trip, kq["chuyen_id"])
    assert ch.co in ("vang", "do")
    assert ch.co_ly_do.strip(), "chuyến sinh ra mang cờ mà không nói vì sao"
    assert "km" in ch.co_ly_do.lower()


def test_dung_CHINH_bo_cham_co_cua_doi_xe_chu_khong_dung_bo_thu_hai(db):
    """Hai bộ chấm cờ sẽ lệch nhau sau vài tháng, và lúc ấy không ai biết bộ nào đúng."""
    from app.services import fleet as FL
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    ch = db.get(Trip, kq["chuyen_id"])
    doc_lap = FL.kiem_chuyen(db, ch)
    assert ch.co == doc_lap["co"]
    assert ch.co_ly_do == " · ".join(doc_lap["ly_do"])


# ═══════════════ Lời đóng lệnh phải nói ĐÚNG cái đang thiếu
def test_loi_dong_lenh_noi_ro_thieu_gi(db):
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    assert DL.THIEU_KM in kq["thieu"]
    assert DL.THIEU_CHI_PHI in kq["thieu"]
    assert "Còn thiếu" in kq["noi"] and "km" in kq["noi"]


def test_du_so_roi_thi_KHONG_bao_thieu_nua(db):
    """Một câu luôn đúng là một câu không ai đọc. Đủ số thì im."""
    v, tx, t, d = _nen(db)
    # chuyến đã nạp sẵn đủ km và có một dòng chi phí, khớp cả bốn (xe, tour, ngày đi, ngày về)
    ch = Trip(vehicle_id=v.id, driver_id=tx.id, tour_id=t.id, ten_tour=t.name,
              ngay_di=d.date_from, ngay_ve=d.date_to, km_dau=120_000, km_cuoi=120_650,
              km_nguon="dong_ho", nguon="nhap_tay")
    db.add(ch); db.flush()
    db.add(TripCost(trip_id=ch.id, kind="nhien_lieu", amount=1_800_000, lit=120)); db.flush()
    kq = DL.dong(db, d, "gddx")
    assert kq["viec"] == "da_gan", "khớp cả bốn thì gắn vào chuyến có sẵn, không tạo dòng mới"


def test_gan_tay_cung_duoc_cham_co_va_cung_bao_thieu(db):
    """Bỏ sót ở đây thì ô đếm đúng với chuyến máy sinh mà sai với chuyến người gắn."""
    v, tx, t, d = _nen(db)
    ch = Trip(vehicle_id=v.id, driver_id=tx.id, tour_id=t.id, ten_tour=t.name,
              ngay_di=d.date_from, ngay_ve=date(2026, 8, 19), nguon="nhap_tay")
    db.add(ch); db.flush()
    kq = DL.gan_tay(db, d, ch)
    assert kq["viec"] == "da_gan_tay"
    assert DL.THIEU_KM in kq["thieu"]
    assert ch.co_ly_do.strip()


# ═══════════════ Ô đếm thứ ba: phải KÈM DANH SÁCH
def test_o_dem_tra_ve_ca_danh_sach_de_bam_vao_nhap(db):
    """Biết «còn 12 chuyến thiếu số» mà phải tự đi tìm 12 chuyến ấy thì con số chỉ làm người ta
    thấy có lỗi, không giúp sửa."""
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    ra = DL.chuyen_tu_lenh_thieu_so(db)
    assert ra["so"] == 1 and ra["tong_chuyen_tu_lenh"] == 1
    mot = ra["danh_sach"][0]
    assert mot["chuyen_id"] == kq["chuyen_id"] and mot["lenh_id"] == d.id
    assert DL.THIEU_KM in mot["thieu"] and DL.THIEU_CHI_PHI in mot["thieu"]
    assert mot["tour"] and mot["ngay_di"] == "2026-08-16"


def test_nhap_du_so_thi_o_dem_GIAM(db):
    """Con số phải giảm được. Một con số không bao giờ giảm thì chẳng mấy ai còn nhìn."""
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    assert DL.chuyen_tu_lenh_thieu_so(db)["so"] == 1
    ch = db.get(Trip, kq["chuyen_id"])
    ch.km_dau, ch.km_cuoi, ch.km_nguon = 120_000, 120_650, "dong_ho"
    db.add(TripCost(trip_id=ch.id, kind="nhien_lieu", amount=1_800_000, lit=120)); db.flush()
    assert DL.chuyen_tu_lenh_thieu_so(db)["so"] == 0


def test_thieu_mot_trong_hai_van_bi_dem(db):
    """Có km mà chưa có chi phí nào thì giá vốn vẫn thiếu một nửa — vẫn phải đếm."""
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    ch = db.get(Trip, kq["chuyen_id"])
    ch.km_dau, ch.km_cuoi, ch.km_nguon = 120_000, 120_650, "dong_ho"; db.flush()
    ra = DL.chuyen_tu_lenh_thieu_so(db)
    assert ra["so"] == 1
    assert ra["danh_sach"][0]["thieu"] == [DL.THIEU_CHI_PHI]


def test_so_cu_nap_bang_EXCEL_khong_bi_gop_vao_o_dem_nay(db):
    """756 chuyến nạp bằng tệp cũng thiếu km. Gộp vào thì con số này không bao giờ về 0 — và một
    con số không bao giờ về 0 sẽ bị bỏ qua như mọi con số không bao giờ về 0."""
    v, tx, t, d = _nen(db)
    for i in range(3):
        db.add(Trip(vehicle_id=v.id, ngay_di=date(2026, 7, 1 + i), ngay_ve=date(2026, 7, 2 + i),
                    nguon="nhap_tay"))
    db.flush()
    DL.dong(db, d, "gddx")
    ra = DL.chuyen_tu_lenh_thieu_so(db)
    assert ra["so"] == 1, "chỉ đếm chuyến sinh từ lệnh"
    assert ra["tong_chuyen_tu_lenh"] == 1


def test_o_dem_chi_doc_khong_ghi(db):
    v, tx, t, d = _nen(db)
    kq = DL.dong(db, d, "gddx")
    ch = db.get(Trip, kq["chuyen_id"])
    truoc = (ch.co, ch.co_ly_do, ch.phien_ban)
    DL.chuyen_tu_lenh_thieu_so(db)
    assert (ch.co, ch.co_ly_do, ch.phien_ban) == truoc


def test_cua_doc_chuoi_tra_ve_du_BA_o_dem(db):
    """Hai ô của DL-3 phải còn nguyên — thêm ô thứ ba không được làm mất ô nào."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_chuoi)
    for ten in ("lenh_xong_chua_co_chuyen", "chuyen_chua_gan_lenh", "chuyen_tu_lenh_thieu_so"):
        assert ten in src, f"cửa đọc chuỗi thiếu ô đếm {ten}"
