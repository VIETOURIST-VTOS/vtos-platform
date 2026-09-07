"""Bản đồ khế ước vay ↔ xe thế chấp (hồ sơ khoản vay 12 xe, 07/9/2026).

Ba rủi ro có thật trong hồ sơ hiện tại, mỗi rủi ro một bài kiểm thử:
  V1 xe đã bán/đã giao nhưng vẫn nằm trong tài sản bảo đảm  → phải kêu GẤP
  V2 khế ước đáo hạn trong 30 ngày                          → phải kêu GẤP
  V3 khế ước không có ngày đáo hạn trong hồ sơ               → phải kêu THIẾU DỮ LIỆU, không được đoán
  V4 xe đang khai thác không thuộc khế ước nào               → nêu ra để rà, KHÔNG được kết luận là đã giải chấp
  V5 dư nợ phân bổ/xe chỉ để tham khảo, tổng dư nợ cộng theo KHẾ ƯỚC nên không trùng
  V6 lãi/tháng và dư nợ tách đúng theo pháp nhân
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_vayxe.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vayxe.db"): os.remove("test_vayxe.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _xe(plate, lifecycle="dang_khai_thac"):
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.plate == plate).first()
    if not v:
        v = Vehicle(plate=plate, seats=45, lifecycle=lifecycle); db.add(v)
    else:
        v.lifecycle = lifecycle
    db.commit(); vid = v.id; db.close()
    return vid


def test_v0_dung_bo_du_lieu_thuc():
    kt = login("ketoan")
    goi4 = client.post("/api/v1/fin/contracts", json={"kind": "vay", "entity": "Vietourist Holdings", "partner": "TPBank", "contract_no": "125/2025/GNN/Q4",
                                                      "principal": 9_022_222_216, "interest_rate": 13.5, "collateral": "Gói 4 xe"}, headers=kt).json()["contract"]
    rieng = client.post("/api/v1/fin/contracts", json={"kind": "vay", "entity": "Vietourist Holdings", "partner": "MB Bank", "contract_no": "LD2236078702",
                                                       "principal": 444_600_000, "interest_rate": 12.1,
                                                       "maturity": str(date.today() + timedelta(days=110))}, headers=kt).json()["contract"]
    vietrip = client.post("/api/v1/fin/contracts", json={"kind": "vay", "entity": "CTY TNHH Vận tải VIETRIP", "partner": "MB Bank", "contract_no": "LD2607831521",
                                                         "principal": 1_700_000_000, "interest_rate": 10.3,
                                                         "maturity": str(date.today() + timedelta(days=12))}, headers=kt).json()["contract"]
    CTX.update(goi4=goi4["id"], rieng=rieng["id"], vietrip=vietrip["id"])
    ids = [_xe(p) for p in ("50H-643.38", "50H-933.71", "50H-938.27", "50H-934.08")]
    CTX["goi4_xe"] = ids
    for vid in ids:
        assert client.post("/api/v1/fleet/the-chap", json={"contract_id": goi4["id"], "vehicle_id": vid}, headers=login("chutich")).status_code == 201
    CTX["da_ban"] = _xe("50F-034.37", lifecycle="da_ban")
    CTX["con_lai"] = _xe("50F-034.71")
    for vid in (CTX["da_ban"], CTX["con_lai"]):
        client.post("/api/v1/fleet/the-chap", json={"contract_id": rieng["id"], "vehicle_id": vid}, headers=login("chutich"))
    CTX["mo_coi"] = _xe("50F-017.37")


def _lay():
    r = client.get("/api/v1/fin/vay-xe", headers=login("ketoan"))
    assert r.status_code == 200
    return r.json()


def test_v1_xe_da_ban_van_the_chap_thi_bao_gap():
    d = _lay()
    cb = [c for c in d["canh_bao"] if c["loai"] == "xe_da_ra_khoi_doi_van_the_chap" and c.get("xe") == "50F-034.37"]
    assert cb and cb[0]["muc"] == "gap"
    assert "giải chấp" in cb[0]["viec"]


def test_v2_dao_han_trong_30_ngay_thi_bao_gap():
    d = _lay()
    cb = [c for c in d["canh_bao"] if c["loai"] == "dao_han" and "LD2607831521" in c["noi_dung"]]
    assert cb and cb[0]["muc"] == "gap"


def test_v3_thieu_ngay_dao_han_thi_khong_doan():
    d = _lay()
    k = [x for x in d["ke_uoc"] if x["contract_no"] == "125/2025/GNN/Q4"][0]
    assert k["maturity"] is None and k["con_ngay"] is None and k["muc_do"] == "thieu_du_lieu"
    assert any(c["loai"] == "thieu_ngay_dao_han" and "125/2025/GNN/Q4" in c["noi_dung"] for c in d["canh_bao"])


def test_v4_xe_khong_thuoc_khe_uoc_nao_thi_khong_ket_luan_da_giai_chap():
    d = _lay()
    assert "50F-017.37" in [x["xe"] for x in d["thieu_ho_so"]]
    cb = [c for c in d["canh_bao"] if c["loai"] == "xe_khong_thuoc_khe_uoc_nao"][0]
    assert "KHÔNG có nghĩa là đã được rút" in cb["viec"]


def test_v5_du_no_phan_bo_chi_de_tham_khao_tong_cong_theo_khe_uoc():
    d = _lay()
    xe = {x["plate"]: x for x in d["xe"]}
    g = xe["50H-643.38"]["khe_uoc"][0]
    assert g["so_xe_trong_goi"] == 4 and g["du_no_phan_bo"] == round(9_022_222_216 / 4)
    tong_theo_xe = sum(k["du_no_phan_bo"] for x in d["xe"] for k in x["khe_uoc"])
    assert d["tong_du_no"] >= 9_022_222_216 + 444_600_000 + 1_700_000_000
    assert abs(tong_theo_xe - d["tong_du_no"]) < d["tong_du_no"]  # phân bổ không phải nguồn để cộng tổng


def test_v6_lai_thang_va_du_no_tach_theo_phap_nhan():
    d = _lay()
    tpn = d["theo_phap_nhan"]
    assert "CTY TNHH Vận tải VIETRIP" in tpn
    assert tpn["CTY TNHH Vận tải VIETRIP"]["lai_thang"] == round(1_700_000_000 * 0.103 / 12)
    k = [x for x in d["ke_uoc"] if x["contract_no"] == "125/2025/GNN/Q4"][0]
    assert k["lai_thang"] == round(9_022_222_216 * 0.135 / 12)
    assert sorted(k["xe_the_chap"]) == ["50H-643.38", "50H-933.71", "50H-934.08", "50H-938.27"]


def test_v7_giai_chap_co_van_ban_thi_het_canh_bao():
    d = _lay()
    cid = [x for x in d["xe"] if x["plate"] == "50F-034.37"][0]["khe_uoc"][0]["collateral_id"]
    assert client.post(f"/api/v1/fleet/the-chap/{cid}/giai-chap", json={"van_ban": ""}, headers=login("ketoan")).status_code == 422
    assert client.post(f"/api/v1/fleet/the-chap/{cid}/giai-chap", json={"van_ban": "CV 118/TPB-2026"}, headers=login("ketoan")).status_code == 200
    d2 = _lay()
    assert not [c for c in d2["canh_bao"] if c.get("xe") == "50F-034.37"]
    k = [x for x in d2["ke_uoc"] if x["contract_no"] == "LD2236078702"][0]
    assert "50F-034.37" in k["xe_da_giai_chap"] and "50F-034.71" in k["xe_the_chap"]


def test_v8_vai_tro_khong_duoc_xem():
    assert client.get("/api/v1/fin/vay-xe", headers=login("hcns")).status_code == 403
