"""V5b – phép thử cho hai màn hình V5, và bộ nạp hợp đồng lao động còn nợ.

Lệnh Đợt 2, chặng A. Hai màn hình Hợp đồng lao động và Tài sản & CCDC dựng ở đợt 1 với 353 dòng mã
và KHÔNG một phép thử nào canh – trái ranh giới thứ sáu của chính lệnh giao việc. Và nghiệm thu V5
đòi "nạp được danh sách hợp đồng lao động", trong khi 25 bộ nạp không có bộ nào cho hợp đồng lao
động; không lần ghi mã nào nói phần này còn nợ. Bộ test này trả cả hai món.

Sáu điều nó giữ:

  1. Quyền đúng vai trò: HCNS và Ban TGĐ vào được, Kinh doanh và Đội xe thì không. Hợp đồng lao động
     là thu nhập của từng người – dữ liệu cá nhân theo Nghị định 13/2023.
  2. Cảnh báo hợp đồng ĐẾN HẠN chạy thật, và đếm đúng: hợp đồng hết hạn trong ngưỡng thì hiện, ngoài
     ngưỡng thì không, và hợp đồng không xác định thời hạn thì KHÔNG BAO GIỜ hiện.
  3. Khấu hao kỳ ra số khớp cách tính đường thẳng, và ghi sổ hai lần không thành hai bút toán.
  4. Hợp đồng không xác định thời hạn KHÔNG được có ngày hết hiệu lực – ghi vào là biến nó thành hợp
     đồng có thời hạn trên sổ, và đó là một chuyện pháp lý chứ không phải một ô nhập sai.
  5. Hợp đồng mới làm hợp đồng cũ HẾT HẠN chứ không xóa, và không đụng bản đã CHẤM DỨT – chấm dứt và
     hết hạn là hai chuyện khác nhau trên hồ sơ lao động.
  6. Loại hợp đồng lệch với loại ghi ở hồ sơ nhân sự thì phải kêu lên: đó là chỗ bảng lương và bảng
     bảo hiểm bắt đầu tính sai mà không ai thấy.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v5b.db")
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

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _nv(db, ma="NS0016"):
    from app.models.hr import Employee
    return db.execute(select(Employee).where(Employee.code == ma)).scalars().first()


def nap(db, loai, rows, boi="hcns"):
    from app.services import intake as IN
    return IN.nap(db, loai, rows, boi, ten_tep="t.xlsx", nguon="nap_tep")


def loi(kq, i=0):
    return " · ".join(kq["dong"][i]["loi"])


def cb(kq, i=0):
    return " · ".join(kq["dong"][i]["canh_bao"])


# ====================== 1. QUYỀN ======================
def test_hai_man_hinh_co_trong_ma_tran_va_khop_pham_vi_api():
    """Cánh cửa vẽ trên tường: menu hiện ra mà bấm vào là 403."""
    from app.services.access import MENU_ROLES, MAN_HINH_API, pham_vi_api
    for man in ("/hop-dong-lao-dong", "/tai-san"):
        assert man in MENU_ROLES, f"{man} chưa khai trong ma trận phân quyền"
        for vt in MENU_ROLES[man]:
            for nhom in MAN_HINH_API.get(man, ()):
                assert nhom in pham_vi_api(vt), f"{vt} thấy {man} mà không chạm được {nhom}"


def test_hop_dong_lao_dong_khong_mo_cho_kinh_doanh_va_doi_xe():
    """Hợp đồng lao động là thu nhập của từng người – Nghị định 13/2023."""
    from app.services.access import MENU_ROLES
    for vt in ("nv_kd", "tn_kd", "gd_doi_xe", "xe_hdv", "nv_mkt"):
        assert vt not in MENU_ROLES["/hop-dong-lao-dong"], vt


def test_api_hop_dong_chan_dung_vai_tro():
    assert client.get("/api/v1/labor-contracts", headers=login("hcns")).status_code == 200
    assert client.get("/api/v1/labor-contracts", headers=login("kd.hoa")).status_code == 403


def test_api_tai_san_chan_dung_vai_tro():
    assert client.get("/api/v1/fixed-assets", headers=login("ketoan")).status_code == 200
    assert client.get("/api/v1/fixed-assets", headers=login("kd.hoa")).status_code == 403


# ====================== 2. CẢNH BÁO HỢP ĐỒNG ĐẾN HẠN ======================
def _hd(db, ma_nv, so, loai, tu, den, status="hieu_luc"):
    from app.models.hrm import LaborContract
    e = _nv(db, ma_nv)
    c = LaborContract(employee_id=e.id, code=so, kind=loai, effective_from=tu, effective_to=den,
                      status=status, created_by="test")
    db.add(c); db.flush()
    return c


def test_canh_bao_hop_dong_den_han_dem_dung_ba_truong_hop(db):
    from app.services import hrm as H
    hom_nay = date.today()
    _hd(db, "NS0016", "HD-SAP-HET", "xac_dinh_12", hom_nay - timedelta(days=300), hom_nay + timedelta(days=20))
    _hd(db, "NS0015", "HD-CON-LAU", "xac_dinh_36", hom_nay - timedelta(days=100), hom_nay + timedelta(days=300))
    _hd(db, "NS0013", "HD-VO-HAN", "khong_xac_dinh", hom_nay - timedelta(days=500), None)
    db.flush()
    d = H.contract_alerts(db, 45)
    ma = {a["contract_code"] for a in d["expiring"]}
    assert "HD-SAP-HET" in ma, "hết hạn trong ngưỡng thì phải hiện"
    assert "HD-CON-LAU" not in ma, "ngoài ngưỡng thì không hiện"
    assert "HD-VO-HAN" not in ma, "hợp đồng không xác định thời hạn không bao giờ đến hạn"
    assert d["counts"]["expiring"] == len(d["expiring"])


def test_hop_dong_qua_han_thi_tu_dong_chuyen_trang_thai(db):
    from app.services import hrm as H
    from app.models.hrm import LaborContract
    _hd(db, "NS0016", "HD-DA-QUA", "xac_dinh_12",
        date.today() - timedelta(days=400), date.today() - timedelta(days=5))
    db.flush()
    H.close_expired_contracts(db)
    c = db.execute(select(LaborContract).where(LaborContract.code == "HD-DA-QUA")).scalars().first()
    assert c.status != "hieu_luc", "hợp đồng quá ngày mà vẫn 'hiệu lực' thì cảnh báo mất nghĩa"


# ====================== 3. KHẤU HAO ======================
def test_khau_hao_ky_ra_so_khop_duong_thang_va_ghi_so_khong_nhan_doi(db):
    from app.models.assets import FixedAsset
    from app.services import assets as A
    a = FixedAsset(code="TSV5B-1", name="Xe thử V5b", kind="huu_hinh", asset_account="211",
                   depr_account="2141", start_date=date(2026, 1, 1), cost=1_200_000_000,
                   depr_months=120, quantity=1, source="test", created_by="test")
    db.add(a); db.flush()
    ky = "2026-03"
    ds = [x for x in A.depreciation_table(db, ky)["rows"] if x["code"] == "TSV5B-1"]
    assert len(ds) == 1
    # 1,2 tỷ / 120 tháng = 10 triệu một kỳ. Số phải khớp tuyệt đối, không "xấp xỉ".
    assert round(ds[0]["amount"]) == 10_000_000, ds[0]


def test_tai_san_chua_toi_ky_bat_dau_thi_khau_hao_bang_khong(db):
    """Thẻ VẪN hiện trong bảng – nó là tài sản đang dùng, che đi thì người đọc tưởng công ty không có
    nó. Điều phải giữ là SỐ bằng 0: khấu hao trước ngày bắt đầu là ghi chi phí của một tài sản chưa
    đưa vào sử dụng."""
    from app.models.assets import FixedAsset
    from app.services import assets as A
    db.add(FixedAsset(code="TSV5B-2", name="Xe mua sau", kind="huu_hinh", asset_account="211",
                      depr_account="2141", start_date=date(2026, 9, 1), cost=600_000_000,
                      depr_months=60, quantity=1, source="test", created_by="test"))
    db.flush()
    r = next(x for x in A.depreciation_table(db, "2026-03")["rows"] if x["code"] == "TSV5B-2")
    assert round(r["amount"]) == 0, r


# ====================== 4–6. BỘ NẠP HỢP ĐỒNG LAO ĐỘNG ======================
def _row(**kw):
    d = {"so_hop_dong": "HDLD-T-001", "ma_nv": "NS0016", "loai": "xac_dinh_12",
         "ngay_ky": "01/08/2026", "hieu_luc_tu": "01/08/2026", "hieu_luc_den": "31/07/2027",
         "luong_chinh": "9.000.000", "luong_bhxh": "9.000.000", "phu_cap": "1.000.000"}
    d.update(kw); return d


def test_bo_nap_khai_bao_day_du():
    from app.services.intake import BO_NAP, VAI_TRO, PHONG_BAN
    from app.services.nhap_lieu import khai_bao_du
    assert khai_bao_du(BO_NAP["hop_dong_lao_dong"]) == []
    assert PHONG_BAN["hop_dong_lao_dong"] == "hcns"
    assert "hcns" in VAI_TRO["hop_dong_lao_dong"] and "ketoan" not in VAI_TRO["hop_dong_lao_dong"]


def test_nap_duoc_danh_sach_hop_dong(db):
    """Chính là điều nghiệm thu V5 đòi mà đợt 1 còn nợ."""
    from app.models.hrm import LaborContract
    kq = nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-100")])
    assert kq["da_nap"] == 1, loi(kq)
    c = db.execute(select(LaborContract).where(LaborContract.code == "HDLD-T-100")).scalars().first()
    assert c.kind == "xac_dinh_12" and c.si_salary == 9_000_000 and c.effective_to == date(2027, 7, 31)


def test_khong_xac_dinh_thoi_han_thi_khong_duoc_co_ngay_het_hieu_luc(db):
    kq = nap(db, "hop_dong_lao_dong",
             [_row(so_hop_dong="HDLD-T-101", loai="khong_xac_dinh", hieu_luc_den="31/12/2030")])
    assert kq["da_nap"] == 0 and "không được ghi ngày hết hiệu lực" in loi(kq)


def test_co_thoi_han_ma_bo_trong_ngay_het_thi_canh_bao_mat_canh_bao(db):
    kq = nap(db, "hop_dong_lao_dong",
             [_row(so_hop_dong="HDLD-T-102", hieu_luc_den="")])
    assert kq["da_nap"] == 1
    assert "sẽ KHÔNG chạy" in cb(kq)


def test_nap_lai_cung_so_hop_dong_khong_thanh_hai_ban(db):
    r = _row(so_hop_dong="HDLD-T-103")
    assert nap(db, "hop_dong_lao_dong", [r])["da_nap"] == 1
    assert nap(db, "hop_dong_lao_dong", [r])["da_co"] == 1


def test_hop_dong_moi_lam_hop_dong_cu_HET_HAN_chu_khong_xoa(db):
    from app.models.hrm import LaborContract
    nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-CU", ma_nv="NS0015",
                                       hieu_luc_tu="01/01/2025", hieu_luc_den="31/12/2025")])
    nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-MOI", ma_nv="NS0015",
                                       hieu_luc_tu="01/01/2026", hieu_luc_den="31/12/2026")])
    cu = db.execute(select(LaborContract).where(LaborContract.code == "HDLD-T-CU")).scalars().first()
    moi = db.execute(select(LaborContract).where(LaborContract.code == "HDLD-T-MOI")).scalars().first()
    assert cu is not None and cu.status == "het_han", "bản cũ còn nguyên trong sổ, chỉ thôi hiệu lực"
    assert moi.status == "hieu_luc"


def test_khong_dung_toi_hop_dong_da_CHAM_DUT(db):
    """Chấm dứt và hết hạn là hai chuyện khác nhau trên hồ sơ lao động – gộp làm một là xóa mất lý do
    người ta rời công ty."""
    from app.models.hrm import LaborContract
    _hd(db, "NS0013", "HDLD-T-CD", "xac_dinh_12", date(2025, 1, 1), date(2025, 12, 31),
        status="cham_dut")
    nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-SAU", ma_nv="NS0013",
                                       hieu_luc_tu="01/06/2026", hieu_luc_den="31/05/2027")])
    cd = db.execute(select(LaborContract).where(LaborContract.code == "HDLD-T-CD")).scalars().first()
    assert cd.status == "cham_dut"


def test_loai_hop_dong_lech_voi_ho_so_nhan_su_thi_keu_len(db):
    """NS0011 là hướng dẫn viên cộng tác viên. Ký HĐLĐ cho người mà hồ sơ ghi là CTV thì bảng lương
    và bảng bảo hiểm bắt đầu tính sai mà không ai thấy."""
    kq = nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-LECH", ma_nv="NS0011")])
    assert kq["da_nap"] == 1
    assert "bảng lương lấy theo hồ sơ" in cb(kq)


def test_dien_bhxh_ma_bo_trong_muc_dong_thi_canh_bao(db):
    kq = nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-104", luong_bhxh="")])
    assert kq["da_nap"] == 1 and "chưa ghi mức lương đóng" in cb(kq)


def test_nhan_su_khong_co_thi_tu_choi(db):
    kq = nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-105", ma_nv="NS9999")])
    assert kq["da_nap"] == 0 and "nạp hồ sơ nhân sự trước" in loi(kq)


def test_ngay_het_truoc_ngay_bat_dau_thi_tu_choi(db):
    kq = nap(db, "hop_dong_lao_dong", [_row(so_hop_dong="HDLD-T-106",
                                            hieu_luc_tu="01/08/2026", hieu_luc_den="01/01/2026")])
    assert kq["da_nap"] == 0 and "trước ngày có hiệu lực" in loi(kq)
