"""KS-63 · phiếu đề xuất chi đội xe — bảy bước, và ba hàng rào phải KÊU.

Bộ này không canh "cửa chạy được". Nó canh ba điều mà nếu tắt đi thì không ai thấy ngay, và đến
lúc thấy thì đã có tiền ra:

  1. **Người lập không duyệt được phiếu của mình.** Chặn theo TÀI KHOẢN, không theo vai — vì có
     người mang cả hai vai, và với người ấy hàng rào vai cho qua. Canh cả chiều ngược: người khác
     thì duyệt được, nếu không thì hàng rào này chỉ là một cửa chết.
  2. **Phiếu đã gửi không sửa đè.** Người kiểm tra đang đọc một con số thì con số ấy không được đổi
     dưới tay họ.
  3. **Bấm gửi hai lần không thành hai bước.** Cùng một khóa `X-Khoa-Ghi` phải trả lại ĐÚNG kết quả
     lần đầu — mà chuyển bước lần thứ hai ở đây nghĩa là một phiếu qua hai lần duyệt, hoặc một
     khoản tiền ghi thanh toán hai lần.

Và một hàng rào thuộc loại khác, canh trên MÔ HÌNH chứ không trên hành vi: bảng `fleet_de_xuat`
KHÔNG được có cột số tài khoản hay ngân hàng (v3.3 §2/§7). Canh bằng hành vi thì chỉ canh được cái
cửa hôm nay có; canh trên cột thì ngày ai đó thêm cột, phép thử đỏ ngay — và cột là thứ cửa sau
mới ghi vào được.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ks63_de_xuat.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks63_de_xuat.db"): os.remove("test_ks63_de_xuat.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
CTX: dict = {}
# Bản nền không có tài khoản Giám đốc đội xe — cùng cách test_doi_xe_cua_doc_va_cua_ghi_tien.py làm.
VAI_TO_TEN = {"gd_doi_xe": "gd.doixe.ks63"}


def login(vai):
    ten = VAI_TO_TEN.get(vai, vai)
    if ten not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, f"không đăng nhập được vai {vai} ({ten}): {r.text}"
        TOK[ten] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[ten]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.models.core import User
        from app.models.suppliers import Supplier
        from app.core.security import hash_password
        db = SessionLocal()
        db.add(User(username="gd.doixe.ks63", full_name="GĐ đội xe kiểm thử KS-63",
                    role="gd_doi_xe", department="doi_xe", staff_code="KT963",
                    password_hash=hash_password("Vtos@Demo#2026"), active=True))
        # Bên nhận phải có trong danh mục — đó chính là luật đang canh, nên bộ thử phải dựng sẵn
        # một nhà cung cấp chứ không mong bản nền có.
        ncc = db.query(Supplier).first()
        if ncc is None:
            ncc = Supplier(code="KS63NCC", ten="Nhà cung cấp kiểm thử KS-63", loai="khac")
            db.add(ncc)
        db.commit()
        CTX["ncc"] = ncc.id
        db.close()
        yield


# ───────────────────────── Hàng rào trên MÔ HÌNH ─────────────────────────

def test_bang_de_xuat_khong_co_cot_so_tai_khoan_va_ngan_hang():
    """v3.3 §2/§7 — GĐ đội xe không nhập hay thay tài khoản ngân hàng ở màn đề nghị.

    Cách chữa không phải ẩn ô trên giao diện: cột còn thì ngày nào đó có cửa khác ghi vào nó.
    """
    from app.models.fleet_de_xuat import FleetDeXuat
    cot = set(FleetDeXuat.__table__.columns.keys())
    for xau in ("so_tai_khoan", "ngan_hang", "chu_tai_khoan", "stk"):
        assert xau not in cot, (f"`fleet_de_xuat` có cột «{xau}» — v3.3 §2/§7 cấm GĐ đội xe nhập "
                               f"hay thay tài khoản ngân hàng. Bên nhận phải là supplier_id.")
    assert "supplier_id" in cot, "Bên nhận phải là khóa vào danh mục nhà cung cấp"


def test_bay_buoc_cua_v33_co_du_trong_bang_trang_thai():
    from app.models.fleet_de_xuat import TRANG_THAI
    for k in ("nhap", "cho_kiem_tra", "cho_duyet", "tra_bo_sung", "da_duyet",
              "da_tt_mot_phan", "da_tt", "da_doi_soat", "huy"):
        assert k in TRANG_THAI, f"thiếu trạng thái {k}"


# ───────────────────────── Một vòng đi hết tuyến ─────────────────────────

def test_01_lap_phieu_nhap():
    r = client.post("/api/v1/fleet/de-xuat", headers=login("gd_doi_xe"),
                    json={"pham_vi": "doi", "nhom": "chung_doi",
                          "noi_dung": "KS-63 chạy thử tuyến duyệt", "buoc_nhap": 0})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["trang_thai"] == "nhap" and p["ma_phieu"].startswith("DX-")
    assert p["tuyen"][0]["ai"] == "GĐ đội xe"
    CTX["id"] = p["id"]


def test_02_gui_khi_con_thieu_thi_tu_choi_va_noi_ro_thieu_gi():
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("gd_doi_xe"),
                    json={"hanh_dong": "gui"})
    assert r.status_code == 422, r.text
    assert "Bên nhận" in r.text or "bên nhận" in r.text


def test_03_ben_nhan_go_tay_van_khong_gui_duoc():
    """Ghi tên bên nhận vào ô chữ thì phiếu Ở LẠI NHÁP — nhưng ô ấy không bị bỏ đi, vì bên nhận
    chưa có trong danh mục là việc thật, và chặn cứng thì người lập sẽ đi đường khác."""
    client.put(f"/api/v1/fleet/de-xuat/{CTX['id']}", headers=login("gd_doi_xe"),
               json={"ben_nhan_de_nghi": "Nhà cung cấp chưa có trong danh mục",
                     "so_tien": 2500000, "ngay_can": "2026-11-20",
                     "can_cu_thue": "da_gom", "so_chung_tu": "KS63-TEST-001"})
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("gd_doi_xe"),
                    json={"hanh_dong": "gui"})
    assert r.status_code == 422
    assert "danh mục" in r.text


def test_04_chon_ben_nhan_tu_danh_muc_roi_gui_duoc():
    assert CTX.get("ncc"), "bộ thử phải dựng sẵn một nhà cung cấp trong danh mục"
    client.put(f"/api/v1/fleet/de-xuat/{CTX['id']}", headers=login("gd_doi_xe"),
               json={"supplier_id": CTX["ncc"]})
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("gd_doi_xe"),
                    json={"hanh_dong": "gui"})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "cho_kiem_tra"


def test_05_phieu_da_gui_thi_khong_sua_de():
    r = client.put(f"/api/v1/fleet/de-xuat/{CTX['id']}", headers=login("gd_doi_xe"),
                   json={"so_tien": 9999999})
    assert r.status_code == 403, r.text
    assert "không sửa đè" in r.text


def test_06_nguoi_lap_khong_tu_kiem_tra_duoc():
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("gd_doi_xe"),
                    json={"hanh_dong": "kiem_tra"})
    assert r.status_code == 403, r.text
    assert "chính mình" in r.text


def test_07_ke_toan_kiem_tra_duoc_nhung_khong_duyet_duoc():
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("ketoan"),
                    json={"hanh_dong": "kiem_tra"})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "cho_duyet"
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("ketoan"),
                    json={"hanh_dong": "duyet"})
    assert r.status_code == 403, "Kế toán không nằm trong tuyến DUYỆT — chỉ kiểm tra và thanh toán"


def test_08_chu_tich_duyet_duoc():
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("chutich"),
                    json={"hanh_dong": "duyet"})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "da_duyet"


def test_09_bam_hai_lan_cung_khoa_khong_thanh_hai_buoc():
    """Khóa chống gửi hai lần (WF05). Đây là chỗ đội xe còn thiếu so với payments/sepay/vietrip."""
    h = dict(login("ketoan")); h["X-Khoa-Ghi"] = "ks63-thu-khoa-mot-lan"
    body = {"hanh_dong": "thanh_toan", "so_tien_tra": 1000000}
    a = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=h, json=body)
    assert a.status_code == 200, a.text
    assert a.json()["trang_thai"] == "da_tt_mot_phan"
    b = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=h, json=body)
    assert b.status_code == 200, b.text
    assert b.json().get("lap_lai") is True, "lần bấm thứ hai phải trả kết quả lần đầu"
    p = client.get(f"/api/v1/fleet/de-xuat/{CTX['id']}", headers=login("ketoan")).json()
    assert float(p["so_tien_da_tt"]) == 1000000, "không được ghi thanh toán hai lần"


def test_10_tra_du_thi_khep_va_doi_soat_xong_thi_dong():
    h = dict(login("ketoan")); h["X-Khoa-Ghi"] = "ks63-thu-khoa-phan-con-lai"
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=h,
                    json={"hanh_dong": "thanh_toan", "so_tien_tra": 1500000})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "da_tt"
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("ketoan"),
                    json={"hanh_dong": "doi_soat"})
    assert r.status_code == 200, r.text
    assert r.json()["trang_thai"] == "da_doi_soat"
    r = client.post(f"/api/v1/fleet/de-xuat/{CTX['id']}/chuyen", headers=login("chutich"),
                    json={"hanh_dong": "huy", "ly_do": "thử đóng phiếu đã khép"})
    assert r.status_code == 403, "phiếu đã đối soát thì không chuyển bước nữa"


def test_11_tra_bo_sung_bat_buoc_ghi_ly_do():
    r = client.post("/api/v1/fleet/de-xuat", headers=login("gd_doi_xe"),
                    json={"pham_vi": "doi", "nhom": "chung_doi", "noi_dung": "KS-63 phiếu thứ hai",
                          "supplier_id": CTX["ncc"], "so_tien": 500000,
                          "ngay_can": "2026-11-25", "can_cu_thue": "khong_co",
                          "so_chung_tu": "KS63-TEST-002"})
    pid = r.json()["id"]
    client.post(f"/api/v1/fleet/de-xuat/{pid}/chuyen", headers=login("gd_doi_xe"),
                json={"hanh_dong": "gui"})
    r = client.post(f"/api/v1/fleet/de-xuat/{pid}/chuyen", headers=login("ketoan"),
                    json={"hanh_dong": "tra"})
    assert r.status_code == 422 and "lý do" in r.text
    r = client.post(f"/api/v1/fleet/de-xuat/{pid}/chuyen", headers=login("ketoan"),
                    json={"hanh_dong": "tra", "ly_do": "Thiếu ảnh chứng từ gốc, bổ sung trước 15/11"})
    assert r.status_code == 200 and r.json()["trang_thai"] == "tra_bo_sung"
    p = client.get(f"/api/v1/fleet/de-xuat/{pid}", headers=login("gd_doi_xe")).json()
    assert p["sua_duoc"] is True, "trả bổ sung rồi thì người lập phải sửa được"
    assert any(g["ly_do"].startswith("Thiếu ảnh") for g in p["nhat_ky"]), \
        "nhật ký phải giữ LÝ DO trả lại, không chỉ giữ trạng thái"
    assert any(g["hanh_dong"] == "tra" and g["tu"] for g in p["nhat_ky"])


def test_12_danh_muc_tra_tu_may_chu_du_bay_nhom_va_bon_buoc():
    d = client.get("/api/v1/fleet/de-xuat/danh-muc", headers=login("gd_doi_xe")).json()
    assert len(d["nhom"]) == 7, "bảy nhóm khoản của bản vẽ"
    assert d["buoc"] == ["Nội dung", "Tiền & chứng từ", "Kiểm tra", "Gửi xử lý"]
    assert d["han_muc_tgd"] > 0, "hạn mức phải có tham số, không nằm trong mã nguồn"
