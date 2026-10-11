"""Khoản trừ người lao động, phiếu lương cá nhân, bút toán theo pháp nhân và chữ ký kép.

Bốn việc hoàn thành ngày 07/9/2026 sau khi các văn bản đã đủ chữ ký:
1. BHXH 10,5% trên MỨC LƯƠNG HỢP ĐỒNG và đoàn phí công đoàn – trước đó "thực nhận" cao hơn số thật.
2. Phiếu lương cá nhân: người lao động tự xem được, kèm khoản đang treo của chính mình.
3. Bút toán lương lập riêng theo từng pháp nhân trả lương.
4. Bước duyệt đủ hai chữ ký, người trình không được ký hồ sơ mình trình.
"""
# Từ 07/9/2026 bảng lương tách khỏi hồ sơ nhân sự và theo VAI TRÒ chỉ còn HCNS (cùng Chủ tịch, TGĐ,
# Ban Kiểm soát). CNTT và Kế toán không còn mở được – nên các phép thử về lương đăng nhập bằng HCNS.
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_luong_khau_tru.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_luong_khau_tru.db"): os.remove("test_luong_khau_tru.db")
import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u, pw="Vtos@Demo#2026"):
    k = (u, pw)
    if k not in TOK: TOK[k] = client.post("/api/v1/auth/login", data={"username": u, "password": pw}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[k]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def run(period="2026-09", refresh=True):
    r = client.get(f"/api/v1/payroll-runs/{period}" + ("?refresh=true" if refresh else ""), headers=login("hcns"))
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- 1. khoản trừ
def _nap_muc(ma, muc):
    r = client.post("/api/v1/bhxh/nap", json={"rows": [{"ma": ma, "muc": muc}], "ky": "2026-08"}, headers=login("cntt"))
    assert r.status_code == 200, r.text
    return r.json()


def test_bhxh_tinh_tren_muc_dong_khong_phai_luong_hop_dong():
    """Danh sách đóng BHXH tháng 08/2026 ghi mức tham gia 5.310.000 trong khi lương hợp đồng nhiều người
    15–25 triệu. Lấy lương hợp đồng làm căn cứ là trừ của người lao động gấp nhiều lần số phải trừ."""
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    db = SessionLocal()
    e = db.query(Employee).filter(Employee.active == True, Employee.contract_type == "hdld",
                                  Employee.base_salary > 6_000_000).first()
    ma, luong_hd = e.code, e.base_salary
    db.close()
    _nap_muc(ma, 5_310_000)
    j = run()
    r = next(x for x in j["rows"] if x["ma"] == ma)
    assert r["bhxh"] == round(5_310_000 * 0.105) == 557_550
    assert r["bhxh"] != round(luong_hd * 0.105), "không được lấy lương hợp đồng làm căn cứ đóng"
    assert r["bhxh_base"] == 5_310_000


def test_chua_co_muc_dong_thi_khong_tru_va_noi_ro():
    """Đoán thừa còn tệ hơn đoán thiếu: trừ nhầm là lấy tiền của người ta."""
    j = run(refresh=False)
    thieu = [x for x in j["rows"] if x.get("thieu_muc_bhxh")]
    assert thieu, "dữ liệu kiểm thử phải còn người chưa nạp mức đóng"
    for x in thieu:
        assert x["bhxh"] == 0 and x["doan_phi"] == 0
        assert "CHƯA CÓ MỨC ĐÓNG BHXH" in x["ghi_chu"]
        assert x["ma"] in j["totals"]["thieu_muc_bhxh"]


def test_ctv_khong_dong_bhxh_chi_khau_tru_tncn():
    j = run(refresh=False)
    for r in j["rows"]:
        if r["hop_dong"] != "hdld":
            assert r["bhxh"] == 0 and r["doan_phi"] == 0


def test_doan_phi_tinh_tren_muc_dong_bhxh_va_chi_tru_doan_vien():
    """Thỏa thuận khấu trừ ghi rõ: mức đoàn phí tính trên tiền lương làm căn cứ đóng BHXH bắt buộc."""
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    db = SessionLocal()
    e = db.query(Employee).filter(Employee.active == True, Employee.contract_type == "hdld").first()
    ten, ma = e.full_name, e.code
    db.close()
    _nap_muc(ma, 5_310_000)
    r = client.post("/api/v1/doan-vien/nap", json={"ho_ten": [ten]}, headers=login("hcns"))
    assert r.status_code == 200, r.text
    j = run()
    dv = next(x for x in j["rows"] if x["ma"] == ma)
    assert dv["doan_phi"] == round(5_310_000 * 0.005) == 26_550
    assert all(x["doan_phi"] == 0 for x in j["rows"] if x["ma"] != ma), "chỉ trừ đoàn viên trong danh sách"


def test_nap_danh_sach_bao_lai_nguoi_chua_ghep_duoc():
    r = client.post("/api/v1/bhxh/nap", json={"rows": [{"ma": "KHONG-CO", "ten": "Người Không Tồn Tại", "muc": 5310000}]},
                    headers=login("hcns")).json()
    assert r["da_nap"] == 0 and r["khong_ghep_duoc"], "không được bỏ qua im lặng"
    d = client.post("/api/v1/doan-vien/nap", json={"ho_ten": ["Người Không Tồn Tại"], "thay_the": False}, headers=login("hcns")).json()
    assert d["khong_ghep_duoc"] == ["Người Không Tồn Tại"]


def test_phai_tra_bang_thu_nhap_tru_khoan_tru():
    j = run(refresh=False)
    for r in j["rows"]:
        assert r["khoan_tru"] == round(r["tru_su_vu"] + r["bhxh"] + r["doan_phi"] + r["tncn"])
        assert r["thuc_nhan"] == round(r["thu_nhap"] - r["khoan_tru"])
    t = j["totals"]
    assert t["thuc_nhan"] == round(t["thu_nhap"] - t["khoan_tru"])


def test_khoan_tru_khong_lam_am_khai_niem_thu_nhap():
    """Thu nhập chỉ gồm khoản dương; chế tài nằm ở khối khoản trừ, không trộn vào thu nhập."""
    j = run(refresh=False)
    for r in j["rows"]:
        assert r["thu_nhap"] >= r["luong_cb"]
        assert r["tru_su_vu"] >= 0


# ---------------------------------------------------------------- 2. phiếu lương
def test_phieu_luong_cua_chinh_minh():
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from app.models.core import User
    db = SessionLocal()
    e = db.query(Employee).filter(Employee.active == True, Employee.user_id != None).first()
    u = db.get(User, e.user_id); ten_tk, ma = u.username, e.code
    u.password_hash = __import__("app.core.security", fromlist=["x"]).hash_password("Vtos@Demo#2026")
    db.commit(); db.close()

    r = client.get("/api/v1/payroll-runs/2026-09/phieu-luong", headers=login("hcns"))
    assert r.status_code in (200, 404)
    p = client.get(f"/api/v1/payroll-runs/2026-09/phieu-luong?ma={ma}", headers=login("hcns"))
    assert p.status_code == 200, p.text
    d = p.json()
    assert d["nhan_su"]["ma"] == ma
    assert set(d["khoan_tru"]) >= {"che_tai_su_vu", "bhxh_nguoi_lao_dong", "doan_phi_cong_doan", "tncn_khau_tru", "tong"}
    assert d["thuc_nhan"] == d["thu_nhap"]["tong"] - d["khoan_tru"]["tong"]
    assert "khoan_dang_treo" in d


def test_khong_xem_duoc_phieu_luong_nguoi_khac():
    ds = client.get("/api/v1/employees?limit=1000", headers=login("cntt")).json()
    kh = next(x for x in ds if x["active"] and x["code"])
    r = client.get(f"/api/v1/payroll-runs/2026-09/phieu-luong?ma={kh['code']}", headers=login("kd.hoa"))
    assert r.status_code in (403, 404)


# ---------------------------------------------------------------- 3. theo pháp nhân
def test_bang_luong_tach_theo_phap_nhan():
    r = client.get("/api/v1/payroll-runs/2026-09/theo-phap-nhan", headers=login("hcns"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["rows"], "phải có ít nhất một nhóm"
    j = run(refresh=False)
    assert round(sum(g["thuc_nhan"] for g in d["rows"])) == round(j["totals"]["thuc_nhan"])
    # người chưa xác định pháp nhân phải là một dòng riêng, không dồn vào công ty mẹ
    assert all(("chua_xac_dinh" in g) for g in d["rows"])


# ---------------------------------------------------------------- 4. hai chữ ký
def test_nguoi_trinh_khong_duoc_ky_de_xuat_cua_chinh_minh():
    """ĐỔI Ở ĐỢT LG2, và đổi vì LUẬT đổi chứ không vì phép thử sai.

    Tham số chính sách đi MỘT chữ ký Chủ tịch từ 11/10/2026, nên TGĐ không còn nằm trong vai ký:
    bấm ký là 403, không còn là 422 "tự ký hồ sơ mình trình".

    CÂU HỎI CÂU NÀY CANH THÌ KHÔNG ĐỔI — người trình và người ký phải là hai người — nhưng nó
    hiện ra ở CHỖ KHÁC: Chủ tịch là người ký duy nhất, nên cửa TRÌNH chặn ông ngay, với lời nhắn
    nhờ người khác trình. Chặn ở cửa trình thay vì để hồ sơ lập ra rồi mới kẹt.
    """
    r = client.post("/api/v1/params", json={"key": "nguong_bien", "value": "0.12",
                                            "effective_from": str(date.today()), "source": "kiểm thử"},
                    headers=login("tgd"))
    assert r.status_code in (200, 201), r.text
    pid = r.json()["param"]["id"]
    tgd_ky = client.post(f"/api/v1/params/{pid}/sign", headers=login("tgd"))
    assert tgd_ky.status_code == 403, "TGD khong con trong vai ky tham so tu 11/10/2026"
    ok = client.post(f"/api/v1/params/{pid}/sign", headers=login("chutich"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["param"]["status"] == "active", "mot chu ky Chu tich la du hieu luc"
    tu_trinh = client.post("/api/v1/params", json={"key": "nguong_bien", "value": "0.13",
                                                   "effective_from": str(date.today()), "source": "x"},
                           headers=login("chutich"))
    assert tu_trinh.status_code == 422, "Chu tich la nguoi ky DUY NHAT nen khong tu trinh duoc"
    assert "không tự trình được" in tu_trinh.text


def test_mot_chu_ky_chu_tich_thi_tham_so_hieu_luc():
    """ĐỔI Ở ĐỢT LG2 — tên cũ là `test_du_hai_chu_ky_thi_tham_so_moi_hieu_luc`.

    Đổi tên vì cái tên cũ nói sai luật hiện hành, và người ta tìm luật bằng cách grep tên phép
    thử. Điều câu này canh vẫn y nguyên: HCNS trình, người KHÁC ký, và chỉ khi đủ chữ ký theo
    bảng `chu_ky.VAI_KY_CAN` thì tham số mới có hiệu lực.
    """
    r = client.post("/api/v1/params", json={"key": "sla_booking_phut", "value": "150",
                                            "effective_from": str(date.today()), "source": "kiểm thử 2"},
                    headers=login("hcns"))
    assert r.status_code in (200, 201), r.text
    pid = r.json()["param"]["id"]
    assert client.post(f"/api/v1/params/{pid}/sign", headers=login("tgd")).status_code == 403
    cuoi = client.post(f"/api/v1/params/{pid}/sign", headers=login("chutich"))
    assert cuoi.json()["param"]["status"] == "active"
