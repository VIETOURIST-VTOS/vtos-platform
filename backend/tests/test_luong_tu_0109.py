"""Bộ tính lương từ 01/9/2026 – Phụ lục đối chiếu đặc tả VTOS Nhân sự (Ban TGĐ, 27/8/2026).

Mã phép thử giữ nguyên quy ước VT01…VT14 của phụ lục để ghép vào bộ kiểm thử của đặc tả.
Điểm cốt lõi: phần chênh giữa mức hợp đồng và mức lương của kỳ là KẾT QUẢ XÁC ĐỊNH MỨC LƯƠNG, không
phải khoản trừ. Nếu mô hình hoá thành dòng trừ thì về hình thức là cắt lương thay xử lý kỷ luật – hành
vi bị cấm tại Điều 127 khoản 2 Bộ luật Lao động 2019.
"""
# Từ 07/9/2026 bảng lương tách khỏi hồ sơ nhân sự và theo VAI TRÒ chỉ còn HCNS (cùng Chủ tịch, TGĐ,
# Ban Kiểm soát). CNTT và Kế toán không còn mở được – nên các phép thử về lương đăng nhập bằng HCNS.
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_luong_tu_0109.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_luong_tu_0109.db"): os.remove("test_luong_tu_0109.db")
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services import luong as L
from app.models.hr import Employee

client = TestClient(app); TOK = {}


def login(u, pw="123456"):
    k = (u, pw)
    if k not in TOK: TOK[k] = client.post("/api/v1/auth/login", data={"username": u, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[k]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def nv(luong=7_000_000, phong="kd_le", vi_tri="nv", ngay_vao=None):
    e = Employee(code="KTL" + str(abs(hash((luong, phong, vi_tri, ngay_vao))) % 100000), full_name="Nhân viên kiểm thử",
                 department=phong, position=vi_tri, base_salary=luong, start_date=ngay_vao)
    return e


# ---------------------------------------------------------------- VT01 & VT02
def test_vt01_duoi_moc_thi_muc_luong_cua_ky_giam_theo_phu_luc_c():
    e = nv()
    xd = L.xac_dinh_thang_doanh_thu(e, 150_000_000, 200_000_000, 700_000)
    assert xd["cap"] == 3 and xd["muc_ky"] == 4_900_000, xd
    assert xd["che_do"] == "thang_doanh_thu"
    assert "không phải khoản trừ" in xd["giai_thich"]


def test_vt01_dat_moc_thi_huong_du_muc_hop_dong():
    e = nv()
    assert L.xac_dinh_thang_doanh_thu(e, 200_000_000, 200_000_000, 700_000)["muc_ky"] == 7_000_000
    assert L.xac_dinh_thang_doanh_thu(e, 650_000_000, 200_000_000, 700_000)["cap"] == 0


def test_vt01_duoi_20_trieu_thi_muc_ky_bang_0_khong_am():
    e = nv()
    xd = L.xac_dinh_thang_doanh_thu(e, 5_000_000, 200_000_000, 700_000)
    assert xd["cap"] == 10 and xd["muc_ky"] == 0


def test_vt02_phan_chenh_khong_bao_gio_la_dong_tru():
    """Phần chênh 2.100.000 không được xuất hiện dưới dạng dòng EMPLOYEE_DEDUCTION ở bất kỳ đâu."""
    row = {"ma": "KT01", "khoan": [{"ten": "Thang giảm Phụ lục C: doanh thu dưới mốc", "tien": -2_100_000, "ghi_chu": ""}]}
    assert L.kiem_tra_khong_phai_khoan_tru(row), "dòng trừ bắt nguồn từ xếp bậc phải bị bắt"
    hop_le = {"ma": "KT01", "khoan": [{"ten": "Chế tài sự vụ ≥ mức 2 – chỉ trừ hoa hồng", "tien": -1_000_000, "ghi_chu": ""}]}
    assert L.kiem_tra_khong_phai_khoan_tru(hop_le) == [], "chế tài sự vụ trừ hoa hồng là hợp lệ"


def test_vt02_bang_luong_that_khong_co_dong_tru_tu_xep_bac():
    r = client.get("/api/v1/payroll-runs/2026-09?refresh=true", headers=login("hcns"))
    assert r.status_code == 200, r.text
    for row in r.json()["rows"]:
        assert L.kiem_tra_khong_phai_khoan_tru(row) == [], row["ma"]


# ---------------------------------------------------------------- VT03 & VT04
def test_vt03_binh_quan_ba_thang_ghi_ro_tung_ky():
    e = nv(8_000_000, "kd_doan")
    hist = [{"ky": "2026-07", "loi_nhuan": 12_000_000}, {"ky": "2026-08", "loi_nhuan": 6_000_000},
            {"ky": "2026-09", "loi_nhuan": 54_000_000}]
    from app.services.hr import DOAN_F
    xd = L.xac_dinh_thang_loi_nhuan(e, hist, 30_000_000, sorted(DOAN_F))
    assert xd["can_cu"]["binh_quan_3_thang"] == 24_000_000
    assert xd["bac"] == "f8" and xd["ty_le"] == 0.88
    assert xd["muc_ky"] == round(8_000_000 * 0.88)
    assert [x["ky"] for x in xd["lookback_inputs"]] == ["2026-07", "2026-08", "2026-09"]
    assert xd["snapshot_at"], "phải ghi thời điểm chụp số để sau này giải thích lại được"


def test_vt04_nguoi_moi_chia_cho_so_thang_thuc_co():
    e = nv(8_000_000, "kd_doan")
    hai_ky = [{"ky": "2026-08", "loi_nhuan": 30_000_000}, {"ky": "2026-09", "loi_nhuan": 30_000_000}]
    bq = L.binh_quan_ba_thang(e, hai_ky)
    assert bq["so_ky"] == 2 and bq["binh_quan"] == 30_000_000, "chia cho 2, không chia cho 3"


# ---------------------------------------------------------------- VT08
def test_vt08_nam_phong_khong_yeu_cau_cham_cong():
    for phong in ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt"):
        assert L.che_do_cong(nv(phong=phong)) == L.BAO_CAO_NGAY
    for phong in ("ketoan", "hcns"):
        assert L.che_do_cong(nv(phong=phong)) == L.CHAM_CONG
    assert L.che_do_cong(nv(phong="huong_dan")) == L.THEO_CHUYEN
    assert L.che_do_cong(nv(phong="doi_xe")) == L.LUONG_CTP

    run = client.get("/api/v1/payroll-runs/2026-09", headers=login("hcns")).json()
    for row in run["rows"]:
        if row["phong"] in ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt"):
            assert row["che_do_cong"] == "bao_cao_ngay"
            assert "công" not in (row.get("ghi_chu") or "").lower() or "chấm công" not in (row.get("ghi_chu") or "").lower()
    assert all(ma not in [r["ma"] for r in run["rows"] if r["phong"] in ("kd_le", "dieu_hanh")]
               for ma in run["totals"].get("thieu_cong", []))


def test_nhap_cong_chi_nhan_bo_phan_con_cham_cong():
    run = client.get("/api/v1/payroll-runs/2026-09", headers=login("hcns")).json()
    kt = next((r for r in run["rows"] if r["phong"] == "ketoan"), None)
    kd = next((r for r in run["rows"] if r["phong"] == "kd_le"), None)
    if kd:
        r = client.put("/api/v1/payroll-runs/2026-09/cham-cong", json={"cong_thuc_te": {kd["ma"]: 20}}, headers=login("hcns"))
        assert r.status_code == 422 and "chấm công theo ngày" in r.json()["detail"]
    if kt:
        r = client.put("/api/v1/payroll-runs/2026-09/cham-cong", json={"cong_chuan": 26, "cong_thuc_te": {kt["ma"]: 13}}, headers=login("hcns"))
        assert r.status_code == 200, r.text
        sau = next(x for x in r.json()["run"]["rows"] if x["ma"] == kt["ma"])
        assert sau["xac_dinh_luong"]["can_cu"] == {"cong_chuan": 26.0, "cong_thuc_te": 13.0}
        assert sau["luong_cb"] == round(sau["xac_dinh_luong"]["muc_hop_dong"] / 26 * 13)


# ---------------------------------------------------------------- VT06
def test_vt06_hoa_hong_qua_han_la_treo_va_hien_trong_bao_cao():
    r = client.get("/api/v1/payroll/khoan-treo", headers=login("hcns"))
    assert r.status_code == 200, r.text
    kq = r.json()
    assert "HOÃN, không phải cắt" in kq["ghi_chu"]
    for row in kq["rows"]:
        assert row["trang_thai"] == "treo"
        assert row["han_quyet_toan"] and row["tour_code"]
    # không có trường nào cho phép khoản treo hết hiệu lực theo thời gian
    assert all("het_han" not in row and "expires" not in row for row in kq["rows"])


def test_khoan_treo_nguoi_lao_dong_chi_thay_phan_cua_minh():
    r = client.get("/api/v1/payroll/khoan-treo", headers=login("kd.hoa"))
    assert r.status_code == 200
    kq = r.json()
    assert kq.get("chi_cua_toi") is True
    ma = {x["ma"] for x in kq["rows"]}
    assert len(ma) <= 1


# ---------------------------------------------------------------- VT13
def test_vt13_xung_dot_ho_so_chan_chay_ky_luong():
    from app.db.session import SessionLocal
    from app.models.hr import Employee as E
    db = SessionLocal()
    mau = db.query(E).filter(E.active == True, E.user_id != None).first()
    them = E(code="KT-XD-01", full_name="Người trùng tài khoản", department="kd_le", position="nv",
             user_id=mau.user_id, active=True)
    db.add(them); db.commit(); db.close()

    ds = client.get("/api/v1/payroll/xung-dot-ho-so", headers=login("hcns")).json()
    assert ds["so_luong"] >= 1 and any(x["loai"] == "trung_tai_khoan" for x in ds["rows"])
    r = client.get("/api/v1/payroll-runs/2026-10?refresh=true", headers=login("hcns"))
    assert r.status_code == 422 and "xung đột hồ sơ" in r.json()["detail"], r.text

    db = SessionLocal()
    x = db.query(E).filter(E.code == "KT-XD-01").first(); x.active = False; db.commit(); db.close()
    assert client.get("/api/v1/payroll-runs/2026-10?refresh=true", headers=login("hcns")).status_code == 200


# ---------------------------------------------------------------- VT14
def test_vt14_chan_xoa_bang_luong_trong_muoi_nam():
    ok, vi_sao = L.duoc_xoa_bang_luong("2026-09", date(2030, 1, 1))
    assert ok is False and "174/2016" in vi_sao
    assert L.duoc_xoa_bang_luong("2026-09", date(2036, 10, 1))[0] is True
    r = client.delete("/api/v1/payroll-runs/2026-09", headers=login("cntt"))
    assert r.status_code == 422 and "10 năm" in r.json()["detail"].replace("mười năm", "10 năm")


def test_chua_quyet_toan_thi_khong_duoc_hieu_la_doanh_thu_0():
    """Doanh thu tính chỉ tiêu chỉ đếm chuyến Kế toán ĐÃ xác nhận. Người còn chuyến chưa chốt mà ra 0 đồng
    là CHƯA ĐỦ CƠ SỞ TÍNH, không phải bán được 0 – trả lương 0 trong tình huống đó là trả sai."""
    e = nv()
    xd = L.xac_dinh_thang_doanh_thu(e, 0, 200_000_000, 700_000, chuyen_chua_quyet_toan=12)
    assert xd["chua_du_co_so"] is True
    assert "CHƯA ĐỦ CƠ SỞ TÍNH" in xd["giai_thich"] and "12 chuyến" in xd["giai_thich"]
    assert xd["can_cu"]["chuyen_chua_quyet_toan"] == 12

    # bán thật mà dưới mốc thì vẫn là xếp bậc bình thường, không nhầm sang "chưa đủ cơ sở"
    binh_thuong = L.xac_dinh_thang_doanh_thu(e, 150_000_000, 200_000_000, 700_000, chuyen_chua_quyet_toan=3)
    assert binh_thuong["chua_du_co_so"] is False and binh_thuong["muc_ky"] == 4_900_000

    # thật sự không có chuyến nào treo mà doanh thu 0 thì đúng là 0
    that_su_0 = L.xac_dinh_thang_doanh_thu(e, 0, 200_000_000, 700_000, chuyen_chua_quyet_toan=0)
    assert that_su_0["chua_du_co_so"] is False and that_su_0["muc_ky"] == 0


def test_bang_luong_liet_ke_nguoi_chua_du_co_so():
    run = client.get("/api/v1/payroll-runs/2026-09?refresh=true", headers=login("hcns")).json()
    assert "chua_du_co_so" in run["totals"]
    for r in run["rows"]:
        xd = r.get("xac_dinh_luong") or {}
        if xd.get("chua_du_co_so"):
            assert r["ma"] in run["totals"]["chua_du_co_so"]
            assert "CHƯA ĐỦ CƠ SỞ TÍNH" in r["ghi_chu"]


def test_khoan_treo_tach_cho_chot_va_chua_co_bang_quyet_toan():
    """Hai tình huống rất khác nhau về việc phải làm: bảng quyết toán đã có đủ số, chỉ thiếu thao tác chốt;
    và chưa ai lập bảng. Gộp lại thì Kế toán không biết bắt đầu từ đâu trong hàng trăm chuyến."""
    kq = client.get("/api/v1/payroll/khoan-treo", headers=login("hcns")).json()
    assert "cho_chot" in kq and "chua_co_bang_quyet_toan" in kq
    assert kq["cho_chot"] + kq["chua_co_bang_quyet_toan"] == kq["tong_chuyen"] - len(
        {r["tour_code"] for r in kq["rows"] if r["vai_tro"] == "Hướng dẫn viên"} -
        {r["tour_code"] for r in kq["rows"] if r["vai_tro"] != "Hướng dẫn viên"})
    for r in kq["rows"]:
        if r["vai_tro"] != "Hướng dẫn viên":
            assert r["buoc_tiep_theo"] in ("Đã có bảng quyết toán – chờ chốt", "Chưa có bảng quyết toán")
