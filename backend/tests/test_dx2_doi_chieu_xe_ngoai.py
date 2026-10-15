# -*- coding: utf-8 -*-
"""DX-2 · Báo cáo nhìn lại — đã trả tiền thuê xe ngoài trong khi xe nhà đậu bãi.

VÌ SAO CẦN BÁO CÁO NÀY khi đã có gợi ý điều xe. `goi_y_dieu_xe` nhìn VỀ TRƯỚC: giúp người sắp lập
lệnh chọn xe rảnh. Nó không trả lời được câu «tháng vừa rồi đã trả bao nhiêu ra ngoài một cách
không cần thiết» — và đó mới là câu làm người ta đổi cách làm. Số đã bắt được: 51.348.800 đ nhóm A
tháng 9/2026.

BA LUẬT KHÓ NHẤT, và là lý do tệp này dài hơn vẻ ngoài:

  1. BA NHÓM, KHÔNG MỘT CON SỐ. Gộp cả ba thành «đã phí bao nhiêu» là cách chắc chắn để không ai
     tin báo cáo sau lần thứ hai.
  2. «XE NHÀ RẢNH» ĐỌC NHẬT TRÌNH, KHÔNG ĐỌC LỆNH. Hôm nay có 0 lệnh điều xe và 780 chuyến; đếm
     theo lệnh thì mọi xe rảnh suốt và nhóm A phình lên bằng những dòng sai.
  3. SỐ CHỖ LÀ ĐIỀU KIỆN. Xe 16 chỗ rảnh không thay được chặng 45 khách.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.models.hr import Employee, Vehicle  # noqa: E402
from app.models.lop3_tour import TourPhuongTien  # noqa: E402
from app.services import doi_chieu_xe_ngoai as DX  # noqa: E402

KY = (date(2026, 9, 1), date(2026, 9, 30))


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nen(db):
    nv = Employee(code="NV1", full_name="Điều hành viên", department="dieu_hanh")
    db.add(nv); db.flush()
    v45 = Vehicle(plate="51B-456.78", code="XE0001", seats=45, active=True,
                  lifecycle="dang_khai_thac", op_right="so_huu")
    v16 = Vehicle(plate="51B-111.22", code="XE0002", seats=16, active=True,
                  lifecycle="dang_khai_thac", op_right="so_huu")
    db.add_all([v45, v16]); db.flush()
    t = Tour(code="DL-0901", name="Đà Lạt 3N2Đ", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 9, 10), end_date=date(2026, 9, 12))
    db.add(t); db.flush()
    return {"v45": v45, "v16": v16, "t": t, "nv": nv}


def _chang(db, n, **kw):
    """Mặc định gộp TRƯỚC `kw` để phép thử ghi đè được từng ô — truyền mặc định sau `**kw` thì
    Python ném `multiple values`, và mọi phép thử muốn đổi một ô đều đỏ vì lý do không liên quan."""
    mac_dinh = dict(tour_id=n["t"].id, loai="o_to", chang="HCM – Đà Lạt",
                    ngay=date(2026, 9, 10), nha_cung_cap="Nhà xe ABC",
                    so_cho=45, thanh_tien=18_000_000)
    x = TourPhuongTien(**{**mac_dinh, **kw})
    db.add(x); db.flush()
    return x


# ═══════════════ NHÓM A · đáng lẽ không cần thuê
def test_thue_ngoai_ma_xe_nha_ranh_thi_vao_nhom_A(db):
    n = _nen(db); _chang(db, n)
    ra = DX.soat(db, *KY)
    a = ra["a_dang_le_khong_can_thue"]
    assert a["so_chang"] == 1 and a["tien"] == 18_000_000
    assert a["danh_sach"][0]["xe_nha_ranh"][0]["bien"] == "51B-456.78"


def test_xe_nha_dang_chay_hom_ay_thi_KHONG_vao_nhom_A(db):
    """Lượt chạy thuê ngoài không nối tour VẪN TÍNH LÀ BẬN — Chủ tịch chốt 11/10/2026."""
    n = _nen(db); _chang(db, n)
    for v in (n["v45"], n["v16"]):
        db.add(Trip(vehicle_id=v.id, ngay_di=date(2026, 9, 9), ngay_ve=date(2026, 9, 11),
                    nguon="nhap_tay"))
    db.flush()
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0


def test_chuyen_da_HUY_khong_lam_xe_thanh_ban(db):
    n = _nen(db); _chang(db, n)
    for v in (n["v45"], n["v16"]):
        db.add(Trip(vehicle_id=v.id, ngay_di=date(2026, 9, 10), ngay_ve=date(2026, 9, 10),
                    status="huy", nguon="nhap_tay"))
    db.flush()
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 1


def test_xe_nho_hon_so_cho_can_thi_khong_tinh_la_thay_duoc(db):
    """Xe 16 chỗ rảnh không thay được chặng 45 khách. Một báo cáo sai ở chỗ dễ thấy thì không ai
    đọc tới chỗ khó thấy."""
    n = _nen(db); _chang(db, n)
    db.add(Trip(vehicle_id=n["v45"].id, ngay_di=date(2026, 9, 10), ngay_ve=date(2026, 9, 10),
                nguon="nhap_tay"))
    db.flush()
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0, \
        "chỉ còn xe 16 chỗ rảnh, không thay được chặng 45 chỗ"


def test_khong_co_so_cho_thi_lay_so_khach_thuc_dung(db):
    n = _nen(db); _chang(db, n, so_cho=None, so_khach_su_dung=40)
    db.add(Trip(vehicle_id=n["v45"].id, ngay_di=date(2026, 9, 10), ngay_ve=date(2026, 9, 10),
                nguon="nhap_tay"))
    db.flush()
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0


def test_xe_ngung_khai_thac_khong_duoc_goi_la_xe_nha_ranh(db):
    n = _nen(db); _chang(db, n)
    n["v45"].lifecycle = "ngung"; n["v16"].lifecycle = "ngung"; db.flush()
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0


def test_chang_chua_co_tien_duoc_dem_RIENG_chu_khong_bo_im(db):
    """Giấu đi thì con số tiền trông nhỏ hơn thực tế mà người đọc vẫn tin là đã soát hết."""
    n = _nen(db); _chang(db, n, thanh_tien=None)
    a = DX.soat(db, *KY)["a_dang_le_khong_can_thue"]
    assert a["so_chang"] == 1 and a["tien"] == 0 and a["so_chang_chua_co_tien"] == 1


# ═══════════════ NHÓM B · nghi khai nhầm
def test_bien_so_trung_xe_trong_danh_muc_thi_vao_nhom_B(db):
    """Nếu đúng là xe nhà thì khoản ấy là công nợ nội bộ, không phải tiền trả bên thứ ba."""
    n = _nen(db); _chang(db, n, so_hieu="51B-456.78")
    ra = DX.soat(db, *KY)
    assert ra["b_nghi_khai_nham"]["so_chang"] == 1
    assert ra["b_nghi_khai_nham"]["danh_sach"][0]["xe_trong_danh_muc"] == "51B-456.78"


def test_bien_so_viet_khac_dinh_dang_van_bat_duoc(db):
    n = _nen(db); _chang(db, n, so_hieu="51b 45678")
    assert DX.soat(db, *KY)["b_nghi_khai_nham"]["so_chang"] == 1


def test_nhom_B_KHONG_dong_thoi_bi_dem_vao_tien_cua_nhom_A(db):
    """Chưa biết nó có phải tiền trả ra ngoài hay không thì không được cộng vào tiền đã phí."""
    n = _nen(db); _chang(db, n, so_hieu="51B-456.78")
    ra = DX.soat(db, *KY)
    assert ra["b_nghi_khai_nham"]["so_chang"] == 1
    assert ra["a_dang_le_khong_can_thue"]["so_chang"] == 0
    assert ra["a_dang_le_khong_can_thue"]["tien"] == 0


def test_may_khong_tu_sua_chang_nao(db):
    n = _nen(db); x = _chang(db, n, so_hieu="51B-456.78")
    DX.soat(db, *KY)
    assert x.vehicle_id is None and not x.xe_nha, "cửa ĐỌC mà ghi là cửa đọc hỏng"


# ═══════════════ NHÓM C · không đối chiếu được
def test_chang_khong_co_ngay_dem_rieng(db):
    n = _nen(db); _chang(db, n, ngay=None)
    ra = DX.soat(db, *KY)
    assert ra["c_khong_doi_chieu_duoc"]["so_chang"] == 1
    assert ra["a_dang_le_khong_can_thue"]["so_chang"] == 0


# ═══════════════ Cái gì KHÔNG phải thuê ngoài
def test_chang_co_vehicle_id_la_xe_nha_du_o_danh_dau_khai_sai(db):
    """Một con trỏ tới hồ sơ xe là bằng chứng mạnh hơn một ô đánh dấu."""
    n = _nen(db); _chang(db, n, vehicle_id=n["v45"].id, xe_nha=0)
    ra = DX.soat(db, *KY)
    assert ra["a_dang_le_khong_can_thue"]["so_chang"] == 0
    assert ra["b_nghi_khai_nham"]["so_chang"] == 0


def test_chang_khai_ro_la_xe_nha_thi_bo_qua(db):
    n = _nen(db); _chang(db, n, xe_nha=1)
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0


def test_may_bay_va_tau_khong_vao_bao_cao_nay(db):
    """Xe nhà không thay được một chặng bay. Đưa vào là tạo ra những dòng không ai xử lý được."""
    n = _nen(db)
    db.add(TourPhuongTien(tour_id=n["t"].id, loai="may_bay", ngay=date(2026, 9, 10),
                          nha_cung_cap="Vietjet", so_cho=45, thanh_tien=90_000_000))
    db.flush()
    ra = DX.soat(db, *KY)
    assert ra["a_dang_le_khong_can_thue"]["so_chang"] == 0
    assert ra["c_khong_doi_chieu_duoc"]["so_chang"] == 0


# ═══════════════ Kỳ
def test_chang_ngoai_ky_khong_tinh(db):
    n = _nen(db); _chang(db, n, ngay=date(2026, 8, 20))
    assert DX.soat(db, *KY)["a_dang_le_khong_can_thue"]["so_chang"] == 0


def test_ky_thang_tinh_dung_ngay_cuoi(db):
    assert DX.ky_thang(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))
    assert DX.ky_thang(2026, 9) == (date(2026, 9, 1), date(2026, 9, 30))
    assert DX.ky_thang(2026, 12) == (date(2026, 12, 1), date(2026, 12, 31))


def test_ky_nguoc_thi_bi_chan(db):
    with pytest.raises(ValueError):
        DX.soat(db, date(2026, 9, 30), date(2026, 9, 1))


def test_cua_doc_mac_dinh_lay_THANG_TRUOC():
    """Báo cáo nhìn lại mà mặc định là tháng này thì nửa tháng đầu nó luôn gần rỗng."""
    import inspect
    from app.api.v1 import fleet as F
    src = inspect.getsource(F.doi_chieu_xe_ngoai)
    assert "month - 1" in src and "ky_thang" in src
