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
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
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


def test_v9_nap_ho_so_khe_uoc_chay_lai_khong_tao_trung():
    body = {"nguon": "Hồ sơ khế ước TPBank/MB 07/9/2026",
            "tao_xe_da_ban": [{"plate": "50F-046.92", "note": "Đã sang tên và đổi biển 50E-955.31 ngày 13/08/2026"}],
            "khe_uoc": [{"contract_no": "134/2023/GNN/Q4/01", "partner": "TPBank", "entity": "Vietourist Holdings",
                         "principal": 1_767_406_654, "outstanding": 1_767_406_654, "interest_rate": 13.9,
                         "collateral": "50F-046.92 + 50F-046.22", "xe": ["50F-046.92", "50F-999.99"]},
                        {"contract_no": "125/2025/GNN/Q4", "partner": "TPBank", "entity": "Vietourist Holdings",
                         "principal": 9_022_222_216, "outstanding": 8_900_000_000, "interest_rate": 13.5, "xe": []}]}
    r = client.post("/api/v1/fin/vay-xe/nap", json=body, headers=login("chutich")).json()
    assert r["tao_moi"] == ["134/2023/GNN/Q4/01"] and r["cap_nhat"] == ["125/2025/GNN/Q4"]
    assert r["xe_da_ban_tao_moi"] == ["50F-046.92"] and r["bien_so_khong_co_trong_danh_muc"] == ["50F-999.99"]
    assert r["so_xe_gan_the_chap"] == 1
    r2 = client.post("/api/v1/fin/vay-xe/nap", json=body, headers=login("chutich")).json()
    assert r2["tao_moi"] == [] and r2["so_xe_gan_the_chap"] == 0 and r2["xe_da_ban_tao_moi"] == []
    d = _lay()
    k = [x for x in d["ke_uoc"] if x["contract_no"] == "125/2025/GNN/Q4"][0]
    assert k["du_no"] == 8_900_000_000                       # nạp lại thì cập nhật dư nợ, không tạo bản ghi thứ hai
    assert len([x for x in d["ke_uoc"] if x["contract_no"] == "134/2023/GNN/Q4/01"]) == 1
    # xe đã bán vẫn là tài sản bảo đảm → phải kêu gấp
    assert [c for c in d["canh_bao"] if c.get("xe") == "50F-046.92" and c["muc"] == "gap"]
    assert client.post("/api/v1/fin/vay-xe/nap", json=body, headers=login("hcns")).status_code == 403


def test_v10_xe_ngung_khai_thac_ma_vong_doi_chua_cap_nhat_van_phai_keu():
    """50F-034.37 trong hồ sơ thật: đã giao cho người mua, tài khoản xe bị ngưng, nhưng vòng đời vẫn
    ghi 'đang khai thác'. Nếu chỉ nhìn vòng đời thì cảnh báo quan trọng nhất im lặng đúng lúc cần kêu."""
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.plate == "50F-034.71").first()
    v.active = False; v.lifecycle = "dang_khai_thac"; db.commit(); db.close()
    d = _lay()
    cb = [c for c in d["canh_bao"] if c.get("xe") == "50F-034.71"]
    assert cb and cb[0]["muc"] == "gap" and "chưa cập nhật" in cb[0]["noi_dung"]


def test_v11_sua_xe_bang_truong_khong_nhan_thi_bao_loi_chu_khong_lang_le_bo_qua():
    """PUT /vehicles chỉ nhận vài trường vận hành. Gửi lifecycle vào đây từng trả 200 'Đã cập nhật xe'
    mà không sửa gì – phải báo 422 và chỉ sang PUT /fleet/xe/{id}."""
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle
    vid = _xe("50H-933.71")
    assert client.put(f"/api/v1/vehicles/{vid}", json={"lifecycle": "da_ban"}, headers=login("cntt")).status_code == 422
    assert client.put(f"/api/v1/vehicles/{vid}", json={"seats": 45}, headers=login("cntt")).status_code == 200
    r = client.put(f"/api/v1/fleet/xe/{vid}", json={"lifecycle": "da_ban"}, headers=login("chutich"))
    assert r.status_code == 200
    d = _lay()
    assert [c for c in d["canh_bao"] if c.get("xe") == "50H-933.71" and c["muc"] == "gap"]


def test_v12_xe_da_ban_con_the_chap_thi_canh_bao_noi_luon_con_phai_thu_bao_nhieu():
    """Ca 50H-496.23: đã bán cho người mua ngoài, chưa sang tên, còn nằm trong tài sản bảo đảm, và
    người mua chưa trả đủ tiền. Ba việc đó là MỘT câu chuyện – cảnh báo phải nói cả ba, vì tách ra
    thì người đọc phải tự ghép, và thường là không ghép."""
    vid = _xe("50H-496.23", lifecycle="da_ban")
    client.post("/api/v1/fleet/the-chap", json={"contract_id": CTX["vietrip"], "vehicle_id": vid}, headers=login("chutich"))
    r = client.post("/api/v1/fleet/ban-xe", json={"vehicle_id": vid, "gia_ban": 900_000_000, "da_thu": 500_000_000,
                                                  "nguoi_mua": "Mr.Huỳnh", "han_thu_du": "2026-12-31",
                                                  "nguon": "Hồ sơ bán xe đội xe"}, headers=login("chutich"))
    assert r.status_code == 201
    d = _lay()
    cb = [c for c in d["canh_bao"] if c.get("xe") == "50H-496.23"][0]
    assert cb["muc"] == "gap"
    assert cb["ban_xe"]["con_phai_thu"] == 400_000_000 and cb["ban_xe"]["nguoi_mua"] == "Mr.Huỳnh"
    assert cb["ban_xe"]["qua_han_thu"] is False and cb["ban_xe"]["da_giai_chap"] is False
    assert "400,000,000" in cb["noi_dung"] and "31/12/2026" in cb["noi_dung"]


def test_v13_ghi_dan_tien_thu_ban_xe_va_chan_thu_vuot_gia_ban():
    """Kế toán ghi tiền thu dần theo từng lần khách trả, nên sửa hồ sơ là thao tác lặp lại.
    Đã thu vượt giá bán bị chặn: để lọt thì 'còn phải thu' thành số âm và hồ sơ trông như đã thu xong."""
    ds = client.get("/api/v1/fleet/ban-xe", headers=login("ketoan")).json()
    sid = [x for x in ds if x["xe"] == "50H-496.23"][0]["id"]
    r = client.put(f"/api/v1/fleet/ban-xe/{sid}", json={"gia_ban": 1_800_000_000, "da_thu": 1_400_000_000},
                   headers=login("ketoan"))
    assert r.status_code == 200 and r.json()["con_phai_thu"] == 400_000_000
    assert client.put(f"/api/v1/fleet/ban-xe/{sid}", json={"da_thu": 2_000_000_000}, headers=login("ketoan")).status_code == 422
    assert client.put(f"/api/v1/fleet/ban-xe/{sid}", json={"da_thu": 1_500_000_000}, headers=login("hcns")).status_code == 403
    ds2 = client.get("/api/v1/fleet/ban-xe", headers=login("ketoan")).json()
    row = [x for x in ds2 if x["id"] == sid][0]
    assert row["con_phai_thu"] == 400_000_000 and row["chua_co_gia_ban"] is False
    d = _lay()
    cb = [c for c in d["canh_bao"] if c.get("xe") == "50H-496.23"][0]
    assert cb["ban_xe"]["gia_ban"] == 1_800_000_000 and cb["ban_xe"]["con_phai_thu"] == 400_000_000


def test_v14_go_khoi_theo_doi_khac_han_giai_chap():
    """Lãnh đạo có thể gỡ một xe khỏi danh sách theo dõi thế chấp. Nhưng bản ghi phải nói đúng
    bản chất: đây KHÔNG phải giải chấp. Ghi nhầm thành giải chấp là đưa vào sổ một điều ngân hàng
    chưa xác nhận, và sau này không ai phân biệt được xe nào thật sự đã được ngân hàng rút ra."""
    vid = _xe("50F-046.92", lifecycle="da_ban")
    kid = [x for x in _lay()["ke_uoc"] if x["contract_no"] == "LD2236078702"][0]["id"]
    r = client.post("/api/v1/fleet/the-chap", json={"contract_id": kid, "vehicle_id": vid}, headers=login("chutich"))
    assert r.status_code == 201
    d = _lay()
    cid = [x for x in d["xe"] if x["plate"] == "50F-046.92"][0]["khe_uoc"][0]["collateral_id"]
    assert client.post(f"/api/v1/fleet/the-chap/{cid}/go-khoi-theo-doi", json={"ly_do": ""}, headers=login("chutich")).status_code == 422
    assert client.post(f"/api/v1/fleet/the-chap/{cid}/go-khoi-theo-doi", json={"ly_do": "x"}, headers=login("ketoan")).status_code == 403
    r = client.post(f"/api/v1/fleet/the-chap/{cid}/go-khoi-theo-doi",
                    json={"ly_do": "Xe đã bán và giao 10/08/2026 – lãnh đạo quyết định thôi theo dõi"}, headers=login("chutich"))
    assert r.status_code == 200 and "KHÔNG phải giải chấp" in r.json()["message"]
    d2 = _lay()
    # gỡ khỏi ĐÚNG khế ước đó thôi. Xe còn nằm trong tài sản bảo đảm của khế ước khác thì cảnh báo
    # của khế ước kia vẫn phải kêu – gỡ một chỗ không được làm im cả những chỗ chưa ai đụng tới.
    k = [x for x in d2["ke_uoc"] if x["id"] == kid][0]
    assert "50F-046.92" not in k["xe_the_chap"] and "50F-046.92" in k["xe_da_giai_chap"]
    assert not [c for c in d2["canh_bao"] if c.get("xe") == "50F-046.92" and c.get("khe_uoc") == k["code"]]
    # gỡ hai lần bị chặn, và bản ghi KHÔNG bị gọi là đã giải chấp
    assert client.post(f"/api/v1/fleet/the-chap/{cid}/go-khoi-theo-doi", json={"ly_do": "lại"}, headers=login("chutich")).status_code == 422
    from app.db.session import SessionLocal
    from app.models.fleet import Collateral
    db = SessionLocal(); c = db.get(Collateral, cid)
    assert c.van_ban_giai_chap.startswith("GỠ KHỎI THEO DÕI (không phải giải chấp)"); db.close()
