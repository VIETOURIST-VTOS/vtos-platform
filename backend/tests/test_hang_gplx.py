"""Hạng bằng lái và số chỗ ngồi – cổng mà đội xe đang thiếu.

Trước bản này cổng điều xe hỏi đúng một câu về người lái: "giấy còn hạn không". Một tấm giấy còn hạn
mười năm mà hạng chỉ đủ 30 chỗ vẫn không cho phép cầm lái xe 45 chỗ – và đó mới là câu hỏi mà 45
hành khách trên xe quan tâm.

Chỗ khó, và là lý do bộ test này dài hơn ta tưởng: VIỆT NAM ĐANG CÓ HAI HỆ HẠNG CÙNG LƯU HÀNH, VÀ
CHÚNG ĐẢO NGHĨA CỦA CHỮ D.

    Luật cũ (giấy cấp trước 01/01/2025):  D = 10–30 chỗ,  E = trên 30 chỗ
    Luật mới (từ 01/01/2025):             D1 = 8–16,  D2 = 17–29,  D = TRÊN 29 chỗ

Một chiếc 45 chỗ: hạng D theo luật cũ thì KHÔNG được lái, hạng D theo luật mới thì ĐƯỢC. Cùng một
chữ cái, hai kết luận ngược nhau. Đọc theo luật cũ cho mọi tấm giấy thì chặn oan người đủ điều kiện;
đọc theo luật mới cho mọi tấm giấy thì cho một tài xế hạng D cũ cầm lái xe 45 khách. Cả hai chiều
đều sai, nên bộ test này canh cả hai chiều.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hanggplx.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

CU = date(2023, 4, 10)          # giấy cấp theo luật cũ
MOI = date(2026, 1, 10)         # giấy cấp theo luật mới


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


# ====================== ĐỌC HẠNG ======================
def test_hang_E_luat_cu_lai_duoc_moi_co_xe():
    from app.services.hang_gplx import so_cho_toi_da
    toi_da, ly_do = so_cho_toi_da("E", CU)
    assert toi_da is None and "không giới hạn" in ly_do


def test_chu_D_dao_nghia_giua_hai_luat():
    """Đây là toàn bộ lý do tệp hang_gplx.py tồn tại."""
    from app.services.hang_gplx import so_cho_toi_da
    assert so_cho_toi_da("D", CU)[0] == 30           # luật cũ: tối đa 30 chỗ
    assert so_cho_toi_da("D", MOI)[0] is None        # luật mới: hạng cao nhất


def test_hang_D_khong_co_ngay_cap_thi_khong_doan():
    """Thiếu ngày cấp là thiếu. Đoán về phía 'đủ' là cho một người không đủ hạng cầm lái 45 khách;
    đoán về phía 'không đủ' là chặn oan. Không đoán bên nào cả."""
    from app.services.hang_gplx import so_cho_toi_da
    toi_da, ly_do = so_cho_toi_da("D", None)
    assert toi_da == -1 and "không đọc được" in ly_do


def test_giay_nhieu_hang_lay_hang_rong_nhat():
    from app.services.hang_gplx import so_cho_toi_da
    assert so_cho_toi_da("A1, E, FC", CU)[0] is None      # E mở hết, A1 và FC không thu hẹp lại
    assert so_cho_toi_da("D, CE", MOI)[0] is None


def test_hang_chi_lai_xe_tai_hoac_mo_to_thi_khong_cho_khach():
    from app.services.hang_gplx import so_cho_toi_da
    toi_da, ly_do = so_cho_toi_da("A1", CU)
    assert toi_da == 0 and "không cho phép chở người" in ly_do


def test_thieu_hang_thi_bao_thieu_chu_khong_bao_dat():
    from app.services.hang_gplx import so_cho_toi_da
    assert so_cho_toi_da("", CU)[0] == -1


def test_hang_D2_luat_moi_toi_da_30_cho():
    from app.services.hang_gplx import so_cho_toi_da
    assert so_cho_toi_da("D2", MOI)[0] == 30


# ====================== CỔNG ĐIỀU XE ======================
def _tai_xe(db, ten, hang, cap, het=None):
    from app.models.hr import Employee
    from app.models.fleet import VehicleDocument
    ma = f"NSGP{abs(hash(ten)) % 9000 + 1000}"
    e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
    if e is None:
        e = Employee(code=ma, full_name=ten, department="doi_xe", position="tai_xe",
                     contract_type="hdld", start_date=date(2025, 1, 1))
        db.add(e); db.flush()
    db.add(VehicleDocument(employee_id=e.id, kind="gplx", number="790000000001",
                           hang=hang, issued_on=cap,
                           expires_on=het or (date.today() + timedelta(days=900)),
                           source="test", verify="da_xac_minh"))
    db.flush()
    return e


def _cong(db, e, so_cho=45):
    """Chạy cổng điều xe cho một chiếc xe `so_cho` chỗ với tài xế này."""
    from app.services import fleet as F
    from app.models.hr import Vehicle
    v = db.execute(select(Vehicle).where(Vehicle.plate == "50F-009.60")).scalars().first()
    cu = v.seats
    v.seats = so_cho; db.flush()
    try:
        d1 = date.today() + timedelta(days=7)
        return F.kiem_tra_dieu_xe(db, v, d1, d1 + timedelta(days=2), driver_id=e.id)
    finally:
        v.seats = cu; db.flush()


def _ma(kq):
    return {x["code"] for x in kq["items"]}


def test_hang_E_luat_cu_khong_bi_chan_tren_xe_45_cho(db):
    e = _tai_xe(db, "Tài xế hạng E cũ", "E", CU)
    assert "HANG_BANG_KHONG_DU" not in _ma(_cong(db, e, 45))


def test_hang_D_LUAT_MOI_khong_bi_chan_tren_xe_45_cho(db):
    """Hai trong 11 giấy phép Chủ tịch gửi ngày 08/9 rơi đúng vào ca này. Đọc theo luật cũ là chặn
    oan hai tài xế đủ điều kiện."""
    e = _tai_xe(db, "Tài xế hạng D mới", "D", MOI)
    assert "HANG_BANG_KHONG_DU" not in _ma(_cong(db, e, 45))


def test_hang_D_LUAT_CU_BI_CHAN_tren_xe_45_cho(db):
    e = _tai_xe(db, "Tài xế hạng D cũ", "D", CU)
    kq = _cong(db, e, 45)
    assert "HANG_BANG_KHONG_DU" in _ma(kq)
    x = next(x for x in kq["items"] if x["code"] == "HANG_BANG_KHONG_DU")
    assert x["level"] == "BLOCK" and "45 chỗ" in x["msg"] and "30 chỗ" in x["msg"]


def test_hang_D_luat_cu_van_lai_duoc_xe_29_cho(db):
    e = _tai_xe(db, "Tài xế hạng D cũ 29", "D", CU)
    assert "HANG_BANG_KHONG_DU" not in _ma(_cong(db, e, 29))


def test_thieu_hang_thi_chua_du_du_lieu_chu_khong_phai_dat(db):
    """Chỗ dễ mặc định thành 'không sao' rồi để một người không đủ hạng cầm lái 45 khách."""
    e = _tai_xe(db, "Tài xế chưa ghi hạng", "", CU)
    ma = _ma(_cong(db, e, 45))
    assert "CHUA_DOC_DUOC_HANG_BANG" in ma and "HANG_BANG_KHONG_DU" not in ma


def test_xe_chua_ghi_so_cho_thi_noi_ro_la_chua_doi_chieu_duoc(db):
    e = _tai_xe(db, "Tài xế xe chưa có số chỗ", "E", CU)
    assert "XE_CHUA_CO_SO_CHO" in _ma(_cong(db, e, 0))


# ====================== BỘ NẠP BẰNG LÁI ======================
def _nap(db, rows, boi="gd.doixe"):
    from app.services import intake as IN
    return IN.nap(db, "bang_lai_xe", rows, boi, ten_tep="gplx.xlsx", nguon="nap_tep")


def _co_nv(db, ma="NSGPLX01"):
    from app.models.hr import Employee
    e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
    if e is None:
        e = Employee(code=ma, full_name="Tài xế thử bộ nạp", department="doi_xe", position="tai_xe",
                     contract_type="hdld", start_date=date(2025, 1, 1))
        db.add(e); db.flush()
    return e


def test_bo_nap_khai_bao_day_du():
    from app.services.intake import BO_NAP, VAI_TRO, PHONG_BAN
    from app.services.nhap_lieu import khai_bao_du
    assert khai_bao_du(BO_NAP["bang_lai_xe"]) == []
    assert "bang_lai_xe" in VAI_TRO and PHONG_BAN["bang_lai_xe"] == "doi_xe"


def test_nap_ghi_ca_hang_va_ngay_cap(db):
    from app.models.fleet import VehicleDocument
    e = _co_nv(db)
    kq = _nap(db, [{"ma_nv": e.code, "so_gplx": "790118255611", "hang": "E",
                    "ngay_cap": "30/08/2022", "ngay_het_han": "30/08/2027"}])
    assert kq["da_nap"] == 1, " · ".join(kq["dong"][0]["loi"])
    g = db.execute(select(VehicleDocument).where(
        VehicleDocument.number == "790118255611")).scalars().first()
    assert g.hang == "E" and g.issued_on == date(2022, 8, 30) and g.kind == "gplx"


def test_nap_lai_cung_bang_khong_thanh_hai_ban(db):
    e = _co_nv(db, "NSGPLX02")
    r = {"ma_nv": e.code, "so_gplx": "740132004896", "hang": "E",
         "ngay_cap": "27/06/2022", "ngay_het_han": "27/06/2027"}
    assert _nap(db, [r])["da_nap"] == 1
    assert _nap(db, [r])["da_co"] == 1


def test_nap_canh_bao_khi_so_gplx_khong_phai_12_chu_so(db):
    e = _co_nv(db, "NSGPLX03")
    kq = _nap(db, [{"ma_nv": e.code, "so_gplx": "1234", "hang": "E",
                    "ngay_cap": "01/01/2023", "ngay_het_han": "01/01/2028"}])
    assert kq["da_nap"] == 1
    assert any("12 chữ số" in c for c in kq["dong"][0]["canh_bao"])


def test_nap_canh_bao_khi_hang_gioi_han_so_cho(db):
    """Nạp được, nhưng người nạp phải BIẾT ngay là người này không điều được xe lớn."""
    e = _co_nv(db, "NSGPLX04")
    kq = _nap(db, [{"ma_nv": e.code, "so_gplx": "790103006325", "hang": "D",
                    "ngay_cap": "01/06/2020", "ngay_het_han": "01/06/2030"}])
    assert kq["da_nap"] == 1
    assert any("tối đa 30 chỗ" in c for c in kq["dong"][0]["canh_bao"])


def test_nap_tu_choi_hang_khong_cho_duoc_khach(db):
    e = _co_nv(db, "NSGPLX05")
    kq = _nap(db, [{"ma_nv": e.code, "so_gplx": "790000000009", "hang": "A1",
                    "ngay_cap": "01/06/2020", "ngay_het_han": "01/06/2030"}])
    assert kq["da_nap"] == 0 and "không cho phép chở người" in " · ".join(kq["dong"][0]["loi"])


def test_nap_bat_buoc_co_nhan_su_truoc(db):
    kq = _nap(db, [{"ma_nv": "KHONG-CO", "so_gplx": "790000000010", "hang": "E",
                    "ngay_cap": "01/06/2020", "ngay_het_han": "01/06/2030"}])
    assert kq["da_nap"] == 0 and "nạp hồ sơ nhân sự trước" in " · ".join(kq["dong"][0]["loi"])


def test_bang_moi_lam_bang_cu_thoi_hieu_luc_nhung_khong_xoa(db):
    from app.models.fleet import VehicleDocument
    e = _co_nv(db, "NSGPLX06")
    _nap(db, [{"ma_nv": e.code, "so_gplx": "790000000011", "hang": "D",
               "ngay_cap": "01/06/2018", "ngay_het_han": "01/06/2023"}])
    _nap(db, [{"ma_nv": e.code, "so_gplx": "790000000012", "hang": "E",
               "ngay_cap": "01/06/2023", "ngay_het_han": "01/06/2028"}])
    cu = db.execute(select(VehicleDocument).where(
        VehicleDocument.number == "790000000011")).scalars().first()
    moi = db.execute(select(VehicleDocument).where(
        VehicleDocument.number == "790000000012")).scalars().first()
    assert cu is not None and cu.active is False      # còn nguyên trong sổ
    assert moi.active is True
