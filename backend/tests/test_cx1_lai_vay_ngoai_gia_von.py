"""Lãi vay KHÔNG tính vào giá vốn đội xe — Chủ tịch quyết ngày 11/10/2026.

Bài học gốc, đo trên chính các tệp quyết toán của công ty ngày 11/10/2026:

    Các bảng T4–T9/2026 cộng lãi vay vào "TỔNG CHI PHÍ" đội xe rồi lấy doanh thu trừ đi để ra dòng
    "LỢI NHUẬN". Tháng 5/2026 bảng ghi 123.889.302. Lợi nhuận đội xe theo giá vốn vận tải là
    445.504.964 — lệch 3,6 lần. Tháng 6: 226.916.997 so với 554.291.419. Mọi báo cáo hiệu quả đội xe
    trình trước đó đều nói đội xe gần như không sinh lời, trong khi chỗ ăn hết lợi nhuận là cấu trúc
    vốn, không phải việc vận hành đội xe.

Lãi vay xe là chi phí TÀI CHÍNH (TK 635), không phải giá vốn vận tải (627 → 632).

Tệp này chốt bốn điều, và mỗi điều là một cách con số có thể lặng lẽ sai lại:

  1. Lãi vay không nằm trong `gia_von` và không nằm trong `loi_nhuan`.
  2. Nó KHÔNG mất đi: có dòng riêng `chi_phi_tai_chinh` và `ket_qua_sau_tai_chinh`. Bỏ hẳn khỏi báo
     cáo cũng là một cách nói dối — khi ấy không ai nhìn đội xe mà biết nó đang gánh bao nhiêu lãi.
  3. Phạm vi người nhập chọn KHÔNG thắng được quy ước công ty: một dòng lãi vay nhập với phạm vi "xe"
     vẫn phải nằm ngoài giá vốn, không chui vào kết quả của một chiếc xe.
  4. Không tiêu thức phân bổ nào chia lãi vay về từng xe.

Và một điều về chính danh sách: `NGOAI_GIA_VON` phải là một hằng số trong mô hình, cạnh
`NHOM_CHI_PHI_KY`. Nếu nó thành một ô người nhập tự tích thì tháng này tích tháng sau quên, và hai
tháng liền nhau không còn so được với nhau.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_cx1_laivay.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
import inspect
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; KY = "2026-07"
DT, DAU, CAU, CTP = 50_000_000, 20_000_000, 2_000_000, 1_000_000
BAI, LUONG, LAI_VAY = 4_000_000, 7_000_000, 300_000_000


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        h = login("ketoan")
        r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h, json={
            "nguon": "nhap_tay", "rows": [{
                "ma_phieu": "CX1-01", "bien_so": "50F-009.60", "ten_tour": "Tuyến thử lãi vay",
                "ngay_di": "2026-07-02", "ngay_ve": "2026-07-04",
                "km_dau": 200000, "km_cuoi": 203000, "doanh_thu": DT,
                "chi_phi": {"dau": DAU, "lit": 900, "cau_duong": CAU, "cong_tac_phi": CTP}}]})
        assert r.status_code == 201, r.text
        yield


def bc(phan_bo="khong"):
    r = client.get(f"/api/v1/fleet/lai-lo?ky={KY}&phan_bo={phan_bo}", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    return r.json()


def them(nhom, so_tien, vehicle_id=None, mo_ta=""):
    return client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"),
                       json={"ky": KY, "nhom": nhom, "so_tien": so_tien,
                             "vehicle_id": vehicle_id, "mo_ta": mo_ta})


def _xe_id():
    d = client.get("/api/v1/fleet/xe", headers=login("ketoan")).json()
    rows = d["rows"] if isinstance(d, dict) else d
    return next(x["id"] for x in rows if "009.60" in (x.get("plate") or x.get("bien_so") or ""))


# ------------------------------------------------- Danh sách nhóm ngoài giá vốn
def test_danh_sach_ngoai_gia_von_la_hang_so_trong_mo_hinh():
    """Quy ước kế toán của cả công ty, không phải ô người gõ bảng tháng tự tích."""
    from app.models.fleet import NGOAI_GIA_VON, NHOM_CHI_PHI_KY
    assert NGOAI_GIA_VON == ("lai_vay",), \
        "thêm hay bớt nhóm ngoài giá vốn là việc có người ký — sửa phép kiểm này cùng lúc"
    assert isinstance(NGOAI_GIA_VON, tuple), "phải là tuple để không ai bồi thêm vào lúc chạy"
    for n in NGOAI_GIA_VON:
        assert n in NHOM_CHI_PHI_KY, f"nhóm {n} ngoài giá vốn mà không có trong danh mục nhóm chi phí"


def test_mo_hinh_khong_doc_danh_sach_tu_choi_nguoi_nhap():
    """Phép tính giá vốn phải đọc hằng số, không đọc một ô trên biểu nhập."""
    from app.models.fleet import FleetPeriodCost
    cot = {c.name for c in FleetPeriodCost.__table__.columns}
    assert "ngoai_gia_von" not in cot and "vao_gia_von" not in cot, \
        "để người nhập tích từng dòng thì tháng này tích tháng sau quên"


# ------------------------------------------------- Lãi vay ra khỏi giá vốn
def test_lai_vay_khong_nam_trong_gia_von_va_khong_tru_vao_loi_nhuan(_startup):
    xid = _xe_id()
    assert them("luong_tai_xe", LUONG, xid, "Lương tháng 7").status_code == 201
    assert them("bai_xe", BAI, None, "Phí bãi tháng 7").status_code == 201
    assert them("lai_vay", LAI_VAY, None, "Lãi vay MB tháng 7").status_code == 201
    t = bc()["tong"]
    assert t["doanh_thu"] == DT
    assert t["chi_phi_chuyen"] == DAU + CAU + CTP
    assert t["chi_phi_xe"] == LUONG
    assert t["chi_phi_doi"] == BAI, "khối chi phí đội của giá vốn chỉ còn phí bãi"
    assert t["gia_von"] == DAU + CAU + CTP + LUONG + BAI
    assert t["loi_nhuan"] == DT - t["gia_von"]
    # Và lãi vay lớn hơn cả lợi nhuận — đúng hình của tháng 4/2026 thật, nơi kết quả sau lãi vay âm.
    assert t["chi_phi_tai_chinh"] == LAI_VAY
    assert t["ket_qua_sau_tai_chinh"] == t["loi_nhuan"] - LAI_VAY < 0
    assert t["loi_nhuan"] > 0, "lợi nhuận theo giá vốn vận tải vẫn dương — đó chính là điều phải thấy"


def test_lai_vay_khong_bien_mat_khoi_bao_cao(_startup):
    """Bỏ hẳn khỏi màn hình cũng là một cách nói dối: không ai biết đội xe gánh bao nhiêu lãi."""
    d = bc()
    assert any(c["nhom"] == "lai_vay" and c["so_tien"] == LAI_VAY
               for c in d["chi_tiet_chi_phi_tai_chinh"])
    assert "lai_vay" in d["nhom_ngoai_gia_von"]
    assert not d["nhom_tai_chinh_chua_nhap"], "kỳ này đã nhập lãi vay thì không được báo là thiếu"


def test_khong_tieu_thuc_nao_chia_lai_vay_ve_tung_xe(_startup):
    for tt in ("ngay_khai_thac", "doanh_thu", "deu"):
        d = bc(tt)
        t = d["tong"]
        assert sum(x["phan_bo_chi_phi_doi"] for x in d["xe"]) == t["chi_phi_doi"] == BAI, \
            f"tiêu thức {tt} đang chia cả phần ngoài giá vốn về xe"
        for x in d["xe"]:
            assert x["phan_bo_chi_phi_doi"] <= BAI
            assert x["ket_qua_sau_phan_bo"] == x["ket_qua_xe"] - x["phan_bo_chi_phi_doi"]
        assert t["chi_phi_tai_chinh"] == LAI_VAY


def test_nhap_lai_vay_voi_pham_vi_xe_thi_van_nam_ngoai_gia_von(_startup):
    """Phạm vi là ô người chọn. Quy ước công ty phải thắng ô ấy, không phụ thuộc người nhập cẩn thận."""
    from app.models.fleet import FleetPeriodCost
    from app.db.session import SessionLocal
    truoc = bc()["tong"]
    db = SessionLocal()
    try:
        db.add(FleetPeriodCost(ky=KY, pham_vi="xe", vehicle_id=_xe_id(), nhom="lai_vay",
                               mo_ta="nhap nham pham vi xe", so_tien=9_000_000, nguon="nhap_tay"))
        db.commit()
    finally:
        db.close()
    sau = bc()["tong"]
    assert sau["chi_phi_xe"] == truoc["chi_phi_xe"], "lãi vay chui vào giá vốn của một chiếc xe"
    assert sau["gia_von"] == truoc["gia_von"]
    assert sau["loi_nhuan"] == truoc["loi_nhuan"]
    assert sau["chi_phi_tai_chinh"] == truoc["chi_phi_tai_chinh"] + 9_000_000


# ------------------------------------------------- Màn hình
def test_man_hinh_in_hai_dong_tach_bach():
    """Một con số gộp thì người đọc không có cách nào biết phần nào là giá vốn."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                     "web", "app", "lai-lo-doi-xe", "page.tsx")
    s = open(p, encoding="utf-8").read()
    assert "t.chi_phi_tai_chinh" in s, "màn hình không in dòng lãi vay riêng"
    assert "t.ket_qua_sau_tai_chinh" in s, "màn hình không in dòng kết quả sau lãi vay"
    assert "không thuộc giá vốn" in s, "dòng lãi vay phải nói rõ nó không thuộc giá vốn"
    assert "theo giá vốn vận tải" in s, "dòng lợi nhuận phải nói rõ nó theo giá vốn nào"


def test_phep_tinh_doc_hang_so_chu_khong_viet_cung_ten_nhom():
    """Viết cứng "lai_vay" trong phép tính thì thêm nhóm thứ hai sẽ lặng lẽ rơi vào giá vốn."""
    from app.services import fleet_lai_lo as LL
    src = inspect.getsource(LL.bao_cao)
    assert "NGOAI_GIA_VON" in src
    assert '"lai_vay"' not in src and "'lai_vay'" not in src, \
        "phép tính đang so với tên nhóm viết cứng thay vì đọc NGOAI_GIA_VON"
