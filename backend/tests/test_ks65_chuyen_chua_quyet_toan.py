"""KS-65 · 09/11/2026 — doanh thu của chuyến CHƯA QUYẾT TOÁN không được cộng vào lợi nhuận kỳ.

Lỗi gốc, đo thật trên hệ ngày 09/11/2026 (KS-62), kỳ 2026-11:

    17 chuyến · 7 đã quyết toán (64.000.000 đ doanh thu, 26 dòng chi phí)
                10 CHƯA quyết toán (94.000.000 đ doanh thu, KHÔNG một dòng chi phí nào)

`fleet_lai_lo.theo_chuyen` lấy mọi chuyến `status not in ("nhap","huy")`, nên 94 triệu doanh thu
vào kỳ mà chi phí của chính 10 chuyến ấy thì chưa — chi phí chỉ được nhập lúc quyết toán. Màn
Chủ tịch vì thế in biên lợi nhuận đội xe tháng 11 là **74,4%** trong khi phần đã quyết toán là
**36,9%**. Sai theo hướng ĐẸP LÊN, nên không ai nghi, và nó nằm trên màn hình dùng để quyết.

Bộ thử này giữ bốn điều, và điều thứ hai quan trọng ngang điều thứ nhất:

  1. Doanh thu chuyến chưa quyết toán KHÔNG vào lợi nhuận kỳ.
  2. Nó cũng KHÔNG BIẾN MẤT: phải đếm được, cộng được, và GỌI TÊN được từng chuyến. Trừ đi mà im
     lặng là một kiểu nói dối khác — người đọc thấy doanh thu nhỏ đi và không biết vì sao.
  3. Hai màn hình (Lãi lỗ đội xe và Hiệu quả đội xe của Chủ tịch) đếm CÙNG MỘT LUẬT. Mỗi lần hai
     màn lệch nhau là mất một ngày đi tìm, đúng như KS-39.
  4. Bảng THEO CHUYẾN vẫn in đủ mọi chuyến — người điều hành cần thấy chuyến đang chạy — nhưng mỗi
     dòng tự khai mình đã quyết toán hay chưa.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ks65.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; KY = "2026-07"
XONG_DT, XONG_CP = 30_000_000, 11_000_000      # chuyến đã quyết toán
TREO_DT = 44_000_000                            # chuyến chưa quyết toán, KHÔNG có dòng chi phí nào


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
        # MỘT chuyến đã quyết toán, đủ bộ chi phí.
        r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h, json={
            "nguon": "nhap_tay", "rows": [{
                "ma_phieu": "KS65-XONG", "bien_so": "50F-009.60", "ten_tour": "Chuyến đã quyết toán",
                "ngay_di": f"{KY}-02", "ngay_ve": f"{KY}-04",
                "km_dau": 200_000, "km_cuoi": 203_000, "doanh_thu": XONG_DT, "quyet_toan": True,
                "chi_phi": {"dau": 8_000_000, "lit": 260, "cau_duong": 1_500_000,
                            "cong_tac_phi": 1_000_000, "giu_xe": 500_000}}]})
        assert r.status_code in (200, 201), r.text
        # HAI chuyến chưa quyết toán, có doanh thu, KHÔNG gửi `chi_phi` — đúng hình dạng thật của
        # một chuyến đang chạy: doanh thu đã biết, chi phí chưa nhập.
        for i, ma in enumerate(["KS65-TREO-1", "KS65-TREO-2"]):
            r = client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=h, json={
                "nguon": "nhap_tay", "rows": [{
                    "ma_phieu": ma, "bien_so": "50F-009.60", "ten_tour": f"Chuyến đang chạy {i+1}",
                    "ngay_di": f"{KY}-1{i}", "ngay_ve": f"{KY}-1{i+2}",
                    "doanh_thu": TREO_DT / 2, "quyet_toan": False}]})
            assert r.status_code in (200, 201), r.text
        yield


def bc(ky=KY) -> dict:
    r = client.get(f"/api/v1/fleet/lai-lo?ky={ky}", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    return r.json()


# ───────────── 1 · doanh thu đang treo KHÔNG vào lợi nhuận kỳ ─────────────

def test_doanh_thu_chuyen_chua_quyet_toan_khong_vao_loi_nhuan():
    t = bc()["tong"]
    assert t["doanh_thu"] == XONG_DT, (
        f"doanh thu kỳ phải là {XONG_DT:,} (chỉ chuyến đã quyết toán), đang là {t['doanh_thu']:,}. "
        f"Nếu nó bằng {XONG_DT + TREO_DT:,} thì doanh thu của chuyến đang chạy lại được cộng vào.")
    assert t["loi_nhuan"] == XONG_DT - XONG_CP, t


def test_bien_loi_nhuan_khong_bi_thoi_phong():
    """Phép kiểm đúng hình dạng lỗi thật: cộng doanh thu mà không cộng chi phí làm BIÊN đẹp gấp đôi."""
    t = bc()["tong"]
    bien_that = (XONG_DT - XONG_CP) / XONG_DT
    bien_neu_cong_ca = (XONG_DT + TREO_DT - XONG_CP) / (XONG_DT + TREO_DT)
    assert abs(t["ty_le_loi_nhuan"] - bien_that) < 0.001, t["ty_le_loi_nhuan"]
    assert abs(t["ty_le_loi_nhuan"] - bien_neu_cong_ca) > 0.05, (
        "biên đang đọc như thể doanh thu chuyến chưa quyết toán cũng được tính")


# ───────────── 2 · phần để ra ngoài phải ĐẾM ĐƯỢC và GỌI TÊN ĐƯỢC ─────────────

def test_phan_de_ra_ngoai_khong_bien_mat():
    d = bc()
    t = d["tong"]
    assert t["so_chuyen_chua_quyet_toan"] == 2, t
    assert t["doanh_thu_chua_quyet_toan"] == TREO_DT, t
    ds = d["chuyen_chua_quyet_toan"]
    assert {x["ma_phieu"] for x in ds} == {"KS65-TREO-1", "KS65-TREO-2"}, ds
    # Số dòng chi phí là chỗ nhìn ra chuyến nào mới chỉ có doanh thu.
    assert all(x["so_dong_chi_phi"] == 0 for x in ds), ds
    assert all(x["xe"] and x["ten_tour"] for x in ds), "phải gọi tên được xe và tour, không chỉ mã phiếu"


def test_khong_co_chuyen_treo_thi_khong_in_dong_nao():
    """Kỳ đã quyết toán xong thì dòng cảnh báo phải biến mất, không đứng đó mãi với số 0."""
    t = bc("2026-05")["tong"]
    assert t["so_chuyen_chua_quyet_toan"] == 0 and t["doanh_thu_chua_quyet_toan"] == 0


# ───────────── 3 · hai màn hình đếm CÙNG MỘT LUẬT ─────────────

def test_hai_man_hinh_cung_mot_so_loi_nhuan():
    """KS-39 mất một ngày vì hai màn lệch nhau. Phép thử này là cái chuông cho lần sau."""
    h = login("ketoan")
    lai_lo = bc()["tong"]
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=h)
    assert hq.status_code == 200, hq.text
    a = hq.json()["tong"]
    assert round(a["doanh_thu"]) == round(lai_lo["doanh_thu"]), (a["doanh_thu"], lai_lo["doanh_thu"])
    assert round(a["loi_nhuan"]) == round(lai_lo["loi_nhuan"]), (a["loi_nhuan"], lai_lo["loi_nhuan"])
    # Và cả hai cùng đếm được phần đang treo, bằng cùng một tên trường.
    assert a["so_chuyen_chua_quyet_toan"] == lai_lo["so_chuyen_chua_quyet_toan"]
    assert round(a["doanh_thu_chua_quyet_toan"]) == round(lai_lo["doanh_thu_chua_quyet_toan"])


def test_khoi_chu_tich_cung_noi_ra_phan_dang_treo():
    """Màn Chủ tịch trừ phần treo đi thì phải NÓI RA, nếu không ông ấy thấy doanh thu nhỏ đi mà
    không biết vì sao."""
    r = client.get(f"/api/v1/fleet/hieu-qua-doi-xe?moc={KY}-31", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    o = r.json()["thang"]          # khối Chủ tịch có ba kỳ: tháng / quý / năm
    assert o.get("so_chuyen_chua_quyet_toan") == 2, o
    assert round(o.get("doanh_thu_chua_quyet_toan") or 0) == TREO_DT, o
    # Kỳ NĂM chứa tháng ấy nên cũng phải cộng được — hai ô này là số đếm và số tiền, cộng được
    # qua nhiều kỳ (khác với công suất hay biên lợi nhuận, những thứ phải tính lại trên tổng).
    # Không kiểm kỳ QUÝ ở đây: mốc 31/07 rơi vào tháng đầu quý, và khối cố ý lùi về quý ĐÃ XONG
    # (xem chú thích `moc.month % 3 == 1` trong hieu_qua_xe.theo_ky) — quý ấy không chứa tháng 7.
    assert r.json()["nam"]["so_chuyen_chua_quyet_toan"] == 2, r.json()["nam"]


# ───────────── 4 · bảng theo chuyến vẫn in ĐỦ, nhưng mỗi dòng tự khai ─────────────

def test_bang_theo_chuyen_van_in_du_va_tu_khai_quyet_toan():
    r = client.get(f"/api/v1/fleet/lai-lo/theo-chuyen?ky={KY}", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    ds = {x["ma_phieu"]: x for x in r.json()}
    for ma in ("KS65-XONG", "KS65-TREO-1", "KS65-TREO-2"):
        assert ma in ds, f"{ma} biến mất khỏi bảng theo chuyến — người điều hành cần thấy chuyến đang chạy"
    assert ds["KS65-XONG"]["quyet_toan"] is True
    assert ds["KS65-TREO-1"]["quyet_toan"] is False
