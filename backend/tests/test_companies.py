"""Danh mục pháp nhân và công ty chủ quản của xe / HDV (Ý kiến thẩm định 06/9/2026, mục C1).

Đội xe thuộc Công ty TNHH Vận tải Vietrip – pháp nhân riêng trong phạm vi hợp nhất – nên lệnh điều xe
dùng xe đó là giao dịch nội bộ, phải nhận diện để loại trừ khi lập báo cáo hợp nhất.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_companies.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_companies.db"): os.remove("test_companies.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def test_danh_muc_du_8_phap_nhan_dung_loai():
    """Danh sách anh Tuấn cung cấp 06/9/2026."""
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    codes = {c["code"]: c for c in cs}
    mong_doi = {"VTD": "me", "VTRIP-VT": "con", "NNX-TN": "doc_lap", "LH-VTR": "doc_lap",
                "LANGAU": "lien_ket", "HKTN": "lien_ket", "LAVENDER": "doc_lap", "BUFFALO": "doc_lap",
                "MEDICSHARE": "lien_ket", "VMUINE": "lien_ket"}
    for code, kind in mong_doi.items():
        assert code in codes, f"thiếu pháp nhân {code}"
        assert codes[code]["kind"] == kind, f"{code} phải là {kind}"
    assert codes["LH-VTR"]["active"] is False, "Lữ hành Vietourist đang tạm ngưng"


def test_ty_le_so_huu_dung_bctc_hop_nhat_ban_nien_2026():
    """Thuyết minh I.5a–5b, BCTC hợp nhất giữa niên độ 6 tháng đầu 2026 (A&C soát xét 28/8/2026)."""
    cs = client.get("/api/v1/companies", headers=login("ketoan")).json()
    codes = {c["code"]: c for c in cs}
    assert codes["VTRIP-VT"]["ownership_pct"] == 100, "công ty con duy nhất – 100%"
    assert codes["MEDICSHARE"]["ownership_pct"] == 48.14
    assert codes["VMUINE"]["ownership_pct"] == 40
    assert codes["LANGAU"]["ownership_pct"] == 45
    assert codes["HKTN"]["ownership_pct"] == 45.33
    # bốn công ty độc lập không nằm trên BCTC hợp nhất nên không có tỷ lệ
    for code in ("NNX-TN", "LAVENDER", "BUFFALO", "LH-VTR"):
        assert codes[code]["ownership_pct"] == 0


def test_ma_so_thue_day_du_tru_hai_lien_ket_moi():
    cs = client.get("/api/v1/companies", headers=login("ketoan")).json()
    codes = {c["code"]: c for c in cs}
    for code in ("VTD", "VTRIP-VT", "LANGAU", "HKTN", "NNX-TN", "LAVENDER", "BUFFALO", "LH-VTR"):
        assert codes[code]["tax_code"], f"{code} phải có mã số thuế theo hồ sơ pháp nhân"
    assert codes["VTD"]["tax_code"] == "0311273634"
    # hai công ty liên kết lấy từ BCTC chưa có hồ sơ pháp nhân → chưa có MST
    for code in ("MEDICSHARE", "VMUINE"):
        assert codes[code]["tax_code"] == ""


def test_pham_vi_hop_nhat_va_ben_lien_quan():
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    codes = {c["code"]: c for c in cs}
    # chỉ mẹ + con nằm trong phạm vi hợp nhất
    assert set(c["code"] for c in cs if c["in_group"]) == {"VTD", "VTRIP-VT"}
    # liên kết và độc lập là bên liên quan – thuyết minh, KHÔNG loại trừ
    for code in ("LANGAU", "HKTN", "MEDICSHARE", "VMUINE", "NNX-TN", "LAVENDER", "BUFFALO", "LH-VTR"):
        assert codes[code]["related_party"] is True and codes[code]["in_group"] is False
    assert codes["VTRIP-VT"]["parent_id"] == codes["VTD"]["id"]
    assert codes["VTRIP-VT"]["ownership_pct"] == 100


def test_xe_noi_bo_duoc_gan_van_tai_vietrip_xe_hop_tac_thi_khong():
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    assert veh, "phải có xe trong dữ liệu mẫu"
    for v in veh:
        if v["kind"] == "noi_bo":
            assert v["company_code"] == "VTRIP-VT", f"xe nội bộ {v['plate']} phải thuộc Vận tải Vietrip"
        else:
            assert not v["company_id"], "xe hợp tác là xe thuê ngoài, không gán pháp nhân trong tập đoàn"


def test_lenh_dieu_xe_nhan_dien_giao_dich_noi_bo():
    disp = client.get("/api/v1/dispatch", headers=login("cntt")).json()
    for d in disp:
        if d["company_code"] == "VTRIP-VT":
            assert d["noi_bo"] is True and not d["canh_bao"]
        elif not d["company_code"]:
            assert d["noi_bo"] is False and "chưa gán" in d["canh_bao"]


def test_gan_va_go_chu_quan_xe():
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    v = veh[0]; cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    me = next(c for c in cs if c["code"] == "VTD")
    r = client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": me["id"]}, headers=login("ketoan"))
    assert r.status_code == 200
    assert next(x for x in client.get("/api/v1/vehicles", headers=login("cntt")).json() if x["id"] == v["id"])["company_code"] == "VTD"
    # trả về như cũ
    client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": v["company_id"]}, headers=login("ketoan"))
    assert client.put(f"/api/v1/vehicles/{v['id']}/company", json={"company_id": 99999}, headers=login("ketoan")).status_code == 422


def test_tai_xe_thuoc_bang_luong_cong_ty_me():
    """Anh Tuấn chốt 06/9/2026: xe thuộc Vận tải Vietrip nhưng tài xế hưởng lương ở công ty mẹ."""
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    me = next(c for c in cs if c["code"] == "VTD")
    tx = [e for e in emps if e["department"] == "doi_xe" or e["position"] == "tai_xe"]
    assert tx, "dữ liệu mẫu phải có tài xế"
    assert all(e["company_id"] == me["id"] for e in tx), "tài xế thuộc bảng lương công ty mẹ"
    # nhưng xe họ lái vẫn thuộc công ty con
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    noi_bo = [v for v in veh if v["kind"] == "noi_bo"]
    assert noi_bo and all(v["company_code"] == "VTRIP-VT" for v in noi_bo)


def test_hdv_thuoc_cong_ty_me():
    """Anh Tuấn chốt 06/9/2026: HDV vẫn thuộc Công ty Cổ phần Du lịch Vietourist, kể cả khi là cộng tác viên."""
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    hdv = [e for e in emps if e["department"] == "huong_dan"]
    assert hdv, "dữ liệu mẫu phải có HDV"
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    me = next(c for c in cs if c["code"] == "VTD")
    assert all(e["company_id"] == me["id"] for e in hdv), "HDV mặc định thuộc công ty mẹ"
    # HCNS vẫn đổi được sang pháp nhân khác khi ký qua công ty con
    vt = next(c for c in cs if c["code"] == "VTRIP-VT")
    assert client.put(f"/api/v1/employees/{hdv[0]['id']}/company", json={"company_id": vt["id"]}, headers=login("hcns")).status_code == 200
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    assert next(e for e in emps if e["id"] == hdv[0]["id"])["company_id"] == vt["id"]
    client.put(f"/api/v1/employees/{hdv[0]['id']}/company", json={"company_id": me["id"]}, headers=login("hcns"))


def test_bao_cao_do_phu_chu_quan():
    c = client.get("/api/v1/companies/coverage", headers=login("tgd")).json()
    assert c["xe"]["tong"] >= 1 and c["xe"]["da_gan"] >= 1
    assert c["hdv"]["tong"] >= 1 and c["hdv"]["chua_gan"] == 0
    assert c["phap_nhan"]["tong"] == 10 and c["phap_nhan"]["hop_nhat"] == 2 and c["phap_nhan"]["ben_lien_quan"] == 8
    assert c["phap_nhan"]["thieu_mst"] == 2, "chỉ còn Medicshare và Việt Mũi Né chưa có MST"
    assert c["phap_nhan"]["tam_ngung"] == 1


def test_vai_tro_khong_duoc_tao_phap_nhan():
    r = client.post("/api/v1/companies", json={"code": "X1", "name": "Thử", "kind": "con"}, headers=login("kd.hoa"))
    assert r.status_code == 403


def test_doi_chieu_va_nap_danh_sach_tai_xe():
    """Đối chiếu trước, nạp sau; không tạo hồ sơ nhân sự mới, không đoán khi trùng tên."""
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    tx = [e for e in emps if e["position"] == "tai_xe"]
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    assert tx and veh
    rows = [{"full_name": tx[0]["full_name"], "plate": veh[0]["plate"], "birth_date": "09/02/1992", "phone": "0945979310"},
            {"full_name": "NGƯỜI KHÔNG CÓ TRONG HỒ SƠ", "plate": "99Z-999.99"}]
    rc = client.post("/api/v1/drivers/reconcile", json={"rows": rows}, headers=login("hcns")).json()
    assert rc["trong_danh_sach"] == 2
    assert any(x["ten"] == "NGƯỜI KHÔNG CÓ TRONG HỒ SƠ" for x in rc["chua_co_ho_so_nhan_su"])
    assert any(x["bien_so"] == "99Z-999.99" for x in rc["thieu_xe_trong_he_thong"])

    r = client.post("/api/v1/drivers/apply", json={"rows": rows}, headers=login("hcns")).json()
    assert r["cap_nhat_nhan_su"] == 1 and r["gan_tai_xe_cho_xe"] == 1
    assert r["xe_tao_moi"] == [], "không tạo xe khi chưa được yêu cầu"
    assert any(b["ly_do"] == "không có hồ sơ" for b in r["bo_qua"])
    e = next(x for x in client.get("/api/v1/employees", headers=login("cntt")).json() if x["id"] == tx[0]["id"])
    assert e["phone"] == "0945979310" and e["birth_date"] == "1992-02-09"
    cs = client.get("/api/v1/companies", headers=login("cntt")).json()
    assert e["company_id"] == next(c for c in cs if c["code"] == "VTD")["id"]


def test_bien_so_so_khop_khong_phu_thuoc_dau_gach():
    from app.services.drivers import norm_plate, norm_name
    assert norm_plate("50F022.59") == norm_plate("50F-022.59") == norm_plate("50f 022,59")
    assert norm_name("NGUYỄN LONG HỒ") == norm_name("Nguyễn Long Hồ")


def test_bien_so_xe_tao_moi_dung_kieu_dang_dung():
    from app.services.drivers import pretty_plate
    assert pretty_plate("50H934.08") == "50H-934.08"
    assert pretty_plate("50h 944,58") == "50H-944.58"
    assert pretty_plate("51B-123.45") == "51B-123.45"


def test_chi_dich_danh_ho_so_khi_trung_ten():
    """Trùng tên thì phải ghi mã nhân sự; không có mã thì bỏ qua chứ không đoán."""
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    db = SessionLocal()
    a = Employee(code="TX9001", full_name="Người Trùng Tên", department="doi_xe", position="tai_xe")
    b = Employee(code="TX9002", full_name="Người Trùng Tên", department="doi_xe", position="tai_xe")
    db.add_all([a, b]); db.commit(); ma_b = b.code; db.close()

    r = client.post("/api/v1/drivers/apply", json={"rows": [{"full_name": "Người Trùng Tên", "phone": "0900000000"}]},
                    headers=login("hcns")).json()
    assert r["cap_nhat_nhan_su"] == 0 and "trùng 2 hồ sơ" in r["bo_qua"][0]["ly_do"]

    r = client.post("/api/v1/drivers/apply", json={"rows": [{"full_name": "Người Trùng Tên", "employee_code": ma_b, "phone": "0900000000"}]},
                    headers=login("hcns")).json()
    assert r["cap_nhat_nhan_su"] == 1 and not r["bo_qua"]
    emps = client.get("/api/v1/employees", headers=login("cntt")).json()
    assert next(e for e in emps if e["code"] == ma_b)["phone"] == "0900000000"
    assert next(e for e in emps if e["code"] == "TX9001")["phone"] == ""


def test_sua_ho_so_xe_va_xe_hop_tac_khong_phai_tai_san_tap_doan():
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    v = next(x for x in veh if x["kind"] == "noi_bo")
    assert client.put(f"/api/v1/vehicles/{v['id']}", json={"seats": 29}, headers=login("cntt")).status_code == 200
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    assert next(x for x in veh if x["id"] == v["id"])["seats"] == 29
    # chuyển sang xe hợp tác → gỡ pháp nhân sở hữu
    client.put(f"/api/v1/vehicles/{v['id']}", json={"kind": "hop_tac"}, headers=login("cntt"))
    veh = client.get("/api/v1/vehicles", headers=login("cntt")).json()
    x = next(y for y in veh if y["id"] == v["id"])
    assert x["kind"] == "hop_tac" and not x["company_id"]
    client.put(f"/api/v1/vehicles/{v['id']}", json={"kind": "noi_bo"}, headers=login("cntt"))
