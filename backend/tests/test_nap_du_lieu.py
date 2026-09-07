"""Bộ nạp dữ liệu: một cửa cho người nhập, cho tệp tải lên, và cho AI.

Bốn cách nạp dữ liệu làm hỏng sổ, và bộ test này chặn cả bốn:

  1. Nạp thẳng không xem trước – 500 dòng rác vào sổ trong một cú bấm, dọn mất vài ngày.
  2. Im lặng bỏ qua dòng lỗi – người nạp tưởng đã vào hết.
  3. Nạp lại cùng tệp làm nhân đôi số liệu.
  4. Không để lại vết – đến lúc ai đó hỏi "con số này ở đâu ra" thì không ai trả lời được.
"""
import os, sys, io
os.environ["DATABASE_URL"] = "sqlite:///./test_nap_dl.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nap_dl.db"): os.remove("test_nap_dl.db")
import pytest
from fastapi.testclient import TestClient
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
        global client; client = c; yield


# ---------------------------------------------------------------- Khai báo cấu trúc
def test_bo_nap_tu_mo_ta_du_de_ai_gui_dung(_startup):
    """Tác vụ AI phải đọc được cấu trúc từ API, không phải đoán từ màn hình."""
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("ketoan")).json()
    ma = {b["ma"] for b in d["bo_nap"]}
    assert {"nha_cung_cap", "don_dich_vu", "chuyen_xe"} <= ma
    ncc = next(b for b in d["bo_nap"] if b["ma"] == "nha_cung_cap")
    assert any(c["bat_buoc"] for c in ncc["cot"]) and ncc["khoa_chong_trung"]
    assert any("Kiểm tra trước" in q for q in d["quy_tac"])


def test_tep_mau_co_dong_vi_du(_startup):
    r = client.get("/api/v1/nap-du-lieu/mau/nha_cung_cap", headers=login("ketoan"))
    assert r.status_code == 200
    dong = r.text.strip().splitlines()
    assert len(dong) >= 2 and "Tên nhà cung cấp" in dong[0]


# ---------------------------------------------------------------- 1. Kiểm tra trước, nạp sau
def test_kiem_tra_khong_ghi_gi_vao_he_thong(_startup):
    h = login("ketoan")
    truoc = len(client.get("/api/v1/ncc", headers=h).json())
    r = client.post("/api/v1/nap-du-lieu/kiem-tra", headers=h,
                    json={"loai": "nha_cung_cap",
                          "rows": [{"Tên nhà cung cấp": "Nhà hàng Sen Vàng", "Loại": "nha_hang"}]})
    assert r.status_code == 200 and r.json()["hop_le"] == 1
    assert len(client.get("/api/v1/ncc", headers=h).json()) == truoc, "bước xem trước không được ghi gì"


def test_bao_loi_theo_tung_dong_kem_so_dong(_startup):
    r = client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login("ketoan"),
                    json={"loai": "nha_cung_cap",
                          "rows": [{"Tên nhà cung cấp": "Có tên", "Loại": "nha_hang"},
                                   {"Tên nhà cung cấp": "", "Loại": "nha_hang"},
                                   {"Tên nhà cung cấp": "Sai loại", "Loại": "linh_tinh"}]})
    d = r.json()
    assert d["dong_loi"] == 2
    assert d["dong"][1]["dong"] == 3 and "Thiếu" in d["dong"][1]["loi"][0]
    assert "không hợp lệ" in d["dong"][2]["loi"][0]


def test_co_dong_loi_thi_mac_dinh_khong_nap_gi_ca(_startup):
    """Nạp một nửa mà không ai chọn là cách để người nạp tưởng đã vào hết."""
    h = login("ketoan")
    truoc = len(client.get("/api/v1/ncc", headers=h).json())
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap",
                          "rows": [{"Tên nhà cung cấp": "Khách sạn Hợp Lệ", "Loại": "khach_san"},
                                   {"Tên nhà cung cấp": "", "Loại": "khach_san"}]})
    assert r.status_code == 201
    assert r.json()["da_nap"] == 0 and "KHÔNG nạp gì cả" in r.json()["message"]
    assert len(client.get("/api/v1/ncc", headers=h).json()) == truoc


def test_bo_qua_dong_loi_phai_la_lua_chon_co_y_thuc(_startup):
    h = login("ketoan")
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "bo_qua_dong_loi": True,
                          "rows": [{"Tên nhà cung cấp": "Khách sạn Hợp Lệ", "Loại": "khach_san"},
                                   {"Tên nhà cung cấp": "", "Loại": "khach_san"}]})
    assert r.status_code == 201 and r.json()["da_nap"] == 1
    ten = {s["ten"] for s in client.get("/api/v1/ncc", headers=h).json()}
    assert "Khách sạn Hợp Lệ" in ten


# ---------------------------------------------------------------- 3. Nạp lại không nhân đôi
def test_nap_lai_cung_tep_khong_nhan_doi(_startup):
    h = login("ketoan")
    body = {"loai": "nha_cung_cap",
            "rows": [{"Tên nhà cung cấp": "Khách sạn Hợp Lệ", "Loại": "khach_san"}]}
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h, json=body)
    assert r.status_code == 201
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 1, "dòng đã có là 'đã có', không phải lỗi"
    ds = [s for s in client.get("/api/v1/ncc", headers=h).json() if s["ten"] == "Khách sạn Hợp Lệ"]
    assert len(ds) == 1


# ---------------------------------------------------------------- 4. Nhật ký
def test_moi_lan_nap_deu_de_lai_vet(_startup):
    d = client.get("/api/v1/nap-du-lieu/lich-su", headers=login("ketoan")).json()
    assert d, "phải có nhật ký nạp"
    r = d[0]
    assert r["hash"] and r["boi"] and r["so_dong"] >= 1 and r["ten_bo_nap"]


def test_ai_nap_thi_ghi_ro_la_ai(_startup):
    """AI đi cùng một cửa với người, nhưng nhật ký phải phân biệt được – nếu không thì sau này không ai
    biết dòng nào do máy tự nạp."""
    h = login("cntt")
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "nguon": "ai", "tac_nhan": "robot_doc_hop_dong",
                          "rows": [{"Tên nhà cung cấp": "Vận tải Đường Việt", "Loại": "van_chuyen"}]})
    assert r.status_code == 201 and r.json()["da_nap"] == 1
    ls = client.get("/api/v1/nap-du-lieu/lich-su", headers=h).json()
    assert ls[0]["nguon"] == "ai" and ls[0]["tac_nhan"] == "robot_doc_hop_dong"


# ---------------------------------------------------------------- Tệp tải lên
def test_tai_tep_csv_len_va_doc_dung_cot_tieng_viet(_startup):
    noi_dung = "Tên nhà cung cấp,Loại,Mã số thuế\nNhà hàng Biển Xanh,nha_hang,0311111111\n"
    r = client.post("/api/v1/nap-du-lieu/kiem-tra-tep", headers=login("ketoan"),
                    data={"loai": "nha_cung_cap"},
                    files={"tep": ("ncc.csv", noi_dung.encode("utf-8"), "text/csv")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_dong"] == 1 and d["hop_le"] == 1 and d["cot_khong_dung"] == []


def test_cot_la_duoc_bao_ra_chu_khong_im_lang_bo(_startup):
    """Cột lạ thường là dấu hiệu người dùng đang nạp nhầm tệp – im lặng bỏ qua là để họ nạp nhầm tiếp."""
    r = client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login("ketoan"),
                    json={"loai": "nha_cung_cap",
                          "rows": [{"Tên nhà cung cấp": "Có cột lạ", "Cột trời ơi": "x"}]})
    assert "cột trời ơi" in r.json()["cot_khong_dung"]


def test_so_tien_go_kieu_viet_van_doc_dung(_startup):
    """Người nhập gõ 1.200.000 hoặc 1,200,000 đều là một triệu hai – bắt họ gõ đúng một kiểu là cách chắc
    chắn nhất để có dữ liệu sai."""
    from app.services.intake import _so
    assert _so("1.200.000") == 1_200_000
    assert _so("1,200,000") == 1_200_000
    assert _so("1200000 đ") == 1_200_000
    assert _so("") == 0


def test_nhan_vien_kinh_doanh_khong_nap_du_lieu(_startup):
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    db.add(User(username="nvkd.nap.kt", full_name="NV kinh doanh", role="nv_kd", department="kinh_doanh",
                staff_code="KT920", password_hash=hash_password("123456"), active=True))
    db.commit(); db.close()
    r = client.post("/api/v1/nap-du-lieu/nap", headers=login("nvkd.nap.kt"),
                    json={"loai": "nha_cung_cap", "rows": [{"Tên nhà cung cấp": "X", "Loại": "khac"}]})
    assert r.status_code == 403
