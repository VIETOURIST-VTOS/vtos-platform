"""Đối chiếu sao kê khoản vay ngân hàng với khế ước đang theo dõi (sao kê TPBank & MB 07/9/2026).

Sao kê thật đặt ra bốn tình huống, mỗi tình huống dẫn tới một việc khác nhau nên không được gộp:
  S1 khớp mã nhưng LỆCH dư nợ  → hồ sơ nội bộ trễ, cập nhật là xong
  S2 hệ thống CÓ, sao kê KHÔNG  → nghi đã tất toán hoặc nằm ở pháp nhân khác. TUYỆT ĐỐI không tự đóng
  S3 sao kê CÓ, hệ thống KHÔNG  → ngân hàng đang cho vay mà mình chưa theo dõi
  S4 lệch lãi suất và thiếu ngày đáo hạn
Và một chốt chặn: đối chiếu chỉ ĐỌC; muốn ghi phải gọi bước cập nhật riêng, có nhật ký.
"""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_saoke.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_saoke.db"): os.remove("test_saoke.db")
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


SAO_KE_TP = [
    {"ke_uoc": "125/2025/GNN/Q4", "du_no": 8_711_111_104, "lai_suat": 13.7, "dao_han": "2031-05-09", "loai": "trung_dai_han"},
    {"ke_uoc": "125/2025/GNN/Q4/02", "du_no": 2_247_887_320, "lai_suat": 13.5, "dao_han": "2031-05-09", "loai": "trung_dai_han"},
    {"ke_uoc": "GNT8571286620162", "du_no": 2_000_000_000, "lai_suat": 9.6, "dao_han": "2027-01-15", "loai": "ngan_han",
     "muc_dich": "Vốn lưu động"},
]


def test_s0_nap_khe_uoc_nen():
    body = {"nguon": "Hồ sơ khế ước 07/7/2026", "khe_uoc": [
        {"contract_no": "125/2025/GNN/Q4", "partner": "TPBank", "entity": "Vietourist Holdings",
         "principal": 9_022_222_216, "outstanding": 9_022_222_216, "interest_rate": 13.5, "xe": []},
        {"contract_no": "125/2025/GNN/Q4/02", "partner": "TPBank", "entity": "Vietourist Holdings",
         "principal": 2_247_887_320, "outstanding": 2_247_887_320, "interest_rate": 13.5, "maturity": "2031-05-09", "xe": []},
        {"contract_no": "134/2023/GNN/Q4/01", "partner": "TPBank", "entity": "Vietourist Holdings",
         "principal": 1_767_406_654, "outstanding": 1_767_406_654, "interest_rate": 13.9,
         "collateral": "50F-046.92 + 50F-046.22", "xe": []}]}
    assert client.post("/api/v1/fin/vay-xe/nap", json=body, headers=login("chutich")).status_code == 200


def _dc():
    r = client.post("/api/v1/fin/doi-chieu-sao-ke",
                    json={"ngan_hang": "TPBank", "phap_nhan": "Vietourist Holdings", "den_ngay": "2026-09-07", "dong": SAO_KE_TP},
                    headers=login("ketoan"))
    assert r.status_code == 200
    return r.json()


def test_s1_lech_du_no_thi_neu_ro_chenh_bao_nhieu():
    d = _dc()
    l = [x for x in d["lech"] if x["ke_uoc"] == "125/2025/GNN/Q4"][0]
    du = [s for s in l["sai_lech"] if s["truong"] == "du_no"][0]
    assert du["he_thong"] == 9_022_222_216 and du["sao_ke"] == 8_711_111_104
    assert du["chenh"] == 8_711_111_104 - 9_022_222_216


def test_s2_he_thong_co_sao_ke_khong_thi_khong_tu_dong_ket_luan_da_tat_toan():
    d = _dc()
    kt = [x for x in d["khong_thay_tren_sao_ke"] if x["ke_uoc"] == "134/2023/GNN/Q4/01"]
    assert kt and "50F-046.92" in kt[0]["the_chap"]
    assert "không được đóng" in kt[0]["y_nghia"] or "Phải có xác nhận" in kt[0]["y_nghia"]
    # và khế ước vẫn còn hiệu lực trong hệ thống sau khi đối chiếu
    cs = client.get("/api/v1/fin/contracts", headers=login("ketoan")).json()
    c = [x for x in cs if x["contract_no"] == "134/2023/GNN/Q4/01"][0]
    assert c["status"] != "tat_toan" and c["outstanding"] == 1_767_406_654


def test_s3_ngan_hang_cho_vay_ma_he_thong_chua_theo_doi():
    d = _dc()
    ct = [x for x in d["chua_theo_doi"] if x["ke_uoc"] == "GNT8571286620162"]
    assert ct and ct[0]["du_no"] == 2_000_000_000 and d["tong_chua_theo_doi"] >= 2_000_000_000


def test_s4_lech_lai_suat_va_thieu_ngay_dao_han():
    d = _dc()
    l = [x for x in d["lech"] if x["ke_uoc"] == "125/2025/GNN/Q4"][0]
    ls = [s for s in l["sai_lech"] if s["truong"] == "lai_suat"][0]
    assert ls["he_thong"] == 13.5 and ls["sao_ke"] == 13.7
    dh = [s for s in l["sai_lech"] if s["truong"] == "dao_han"][0]
    assert dh["he_thong"] == "chưa có"
    # khế ước /02 đã có sẵn ngày đúng nên chỉ lệch dư nợ, không lệch đáo hạn
    l2 = [x for x in d["lech"] if x["ke_uoc"] == "125/2025/GNN/Q4/02"]
    assert not l2 or not [s for s in l2[0]["sai_lech"] if s["truong"] == "dao_han"]


def test_s5_doi_chieu_chi_doc_muon_ghi_phai_goi_buoc_rieng():
    truoc = [x for x in client.get("/api/v1/fin/contracts", headers=login("ketoan")).json() if x["contract_no"] == "125/2025/GNN/Q4"][0]
    _dc()
    sau = [x for x in client.get("/api/v1/fin/contracts", headers=login("ketoan")).json() if x["contract_no"] == "125/2025/GNN/Q4"][0]
    assert sau["outstanding"] == truoc["outstanding"] == 9_022_222_216
    assert client.post("/api/v1/fin/cap-nhat-theo-sao-ke", json={"ngan_hang": "TPBank", "dong": SAO_KE_TP},
                       headers=login("hcns")).status_code == 403
    r = client.post("/api/v1/fin/cap-nhat-theo-sao-ke",
                    json={"ngan_hang": "TPBank", "den_ngay": "2026-09-07", "dong": SAO_KE_TP}, headers=login("ketoan")).json()
    assert "GNT8571286620162" in r["khong_co_trong_he_thong"]     # dòng lạ không tự tạo khế ước mới
    sau2 = [x for x in client.get("/api/v1/fin/contracts", headers=login("ketoan")).json() if x["contract_no"] == "125/2025/GNN/Q4"][0]
    assert sau2["outstanding"] == 8_711_111_104 and sau2["interest_rate"] == 13.7 and sau2["maturity"] == "2031-05-09"
    d2 = _dc()
    assert [x for x in d2["khop"] if x["ke_uoc"] == "125/2025/GNN/Q4"]     # đối chiếu lại thì khớp
    # khế ước không có trên sao kê vẫn nguyên vẹn sau khi cập nhật
    assert [x for x in d2["khong_thay_tren_sao_ke"] if x["ke_uoc"] == "134/2023/GNN/Q4/01"]


def test_s6_khoan_vay_bds_von_luu_dong_la_ngoai_pham_vi_chu_khong_phai_thieu_sot():
    """Sao kê gộp chung vay mua xe, vay bất động sản và vay vốn lưu động. Dòng ngoài phạm vi phải
    được gọi đúng tên: gộp chung với "chưa theo dõi" thì một việc thật chìm giữa 51 dòng không phải việc."""
    dong = SAO_KE_TP + [
        {"ke_uoc": "GNU9306258180806", "du_no": 4_000_000_000, "lai_suat": 9.6, "nhom": "von_luu_dong"},
        {"ke_uoc": "BDS-2025-01", "du_no": 12_000_000_000, "lai_suat": 11.0, "nhom": "bds"},
    ]
    d = client.post("/api/v1/fin/doi-chieu-sao-ke", json={"ngan_hang": "TPBank", "dong": dong}, headers=login("ketoan")).json()
    ma_ngoai = [x["ke_uoc"] for x in d["ngoai_pham_vi"]]
    assert "GNU9306258180806" in ma_ngoai and "BDS-2025-01" in ma_ngoai
    assert d["tong_ngoai_pham_vi"] == 16_000_000_000
    # dòng không ghi nhóm vẫn nằm ở "chưa theo dõi" – không tự cho là ngoài phạm vi
    assert "GNT8571286620162" in [x["ke_uoc"] for x in d["chua_theo_doi"]]
    assert "ngoài phạm vi" in d["tom_tat"]


def test_s7_man_hinh_vay_xe_khong_om_khoan_vay_ngoai_doi_xe():
    """Khế ước xếp nhóm không phải vay xe thì không xuất hiện trên bản đồ vay – thế chấp xe."""
    r = client.post("/api/v1/fin/vay-xe/nap", json={"nguon": "test", "khe_uoc": [
        {"contract_no": "BDS-2025-01", "partner": "TPBank", "entity": "Vietourist Holdings",
         "loan_group": "bds", "principal": 12_000_000_000, "outstanding": 12_000_000_000, "interest_rate": 11.0, "xe": []}]},
        headers=login("chutich")).json()
    assert r["tao_moi"] == ["BDS-2025-01"]
    d = client.get("/api/v1/fin/vay-xe", headers=login("ketoan")).json()
    assert "BDS-2025-01" not in [k["contract_no"] for k in d["ke_uoc"]]
    assert "125/2025/GNN/Q4" in [k["contract_no"] for k in d["ke_uoc"]]
    # tổng đúng bằng ba khế ước vay xe, khoản bất động sản 12 tỷ không cộng vào
    assert d["tong_du_no"] == 8_711_111_104 + 2_247_887_320 + 1_767_406_654
