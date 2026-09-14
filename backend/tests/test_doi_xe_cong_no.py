"""Sổ công nợ đội xe – chi tiết theo chủ xe, theo hồ sơ bán xe, theo khế ước.

Bộ test này nhắm vào bốn cách mất tiền mà một sổ công nợ làm ẩu sẽ gây ra:

  1. Cộng chung bốn túi nợ với bốn đối tượng khác nhau thành một con số nghe rất gọn và vô nghĩa.
  2. Hiểu "đã đóng kỳ" là "đã trả tiền" – rồi trả lần thứ hai.
  3. Cộng bảng còn đang tính vào số phải trả, hoặc ngược lại giấu nó đi.
  4. Chủ xe chưa có bảng quyết toán nào thì ghi 0 thay vì "chưa biết".
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_congno_xe.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_congno_xe.db"): os.remove("test_congno_xe.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"{HOM_NAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def xe(plate: str) -> dict:
    return next(x for x in client.get("/api/v1/fleet/xe", headers=login("cntt")).json() if x["plate"] == plate)


@pytest.fixture(scope="module")
def kỳ_da_duyet(_startup):
    """Một chủ xe có một kỳ quyết toán ĐÃ DUYỆT – tức con số đã chốt, nhưng tiền chưa đi."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe công nợ A"}).json()["id"]
    v = xe("50E-955.31")
    client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h, json={"vehicle_id": v["id"], "partner_id": pid})
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                          "km_dau": 20_000, "km_cuoi": 20_300, "doanh_thu": 60_000_000,
                          "ten_tour": "Chuyến kiểm thử công nợ"}).json()
    client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=h,
                json={"kind": "dau", "amount": 10_000_000, "lit": 120, "chung_tu": "HD-CN-1"})
    st = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()
    r = client.post(f"/api/v1/fleet/quyet-toan/{st['id']}/dong-ky", headers=login("chutich"))
    assert r.status_code == 200, r.text
    return {"partner_id": pid, "settlement_id": st["id"], "vehicle_id": v["id"],
            "phai_tra": st["sau_can_tru"]}


# ---------------------------------------------------------------- 1. Bốn túi để riêng
def test_bon_tui_cong_no_de_rieng_khong_co_mot_con_so_tong(kỳ_da_duyet):
    """Nợ chủ xe hợp tác, tiền còn phải thu người mua xe, và dư nợ ngân hàng là ba khoản với ba đối tượng
    khác nhau. Một trường "tổng công nợ đội xe" gộp cả ba là con số không dùng được vào việc gì – và nguy
    hiểm hơn là nó trông như dùng được."""
    d = client.get("/api/v1/fleet/cong-no", headers=login("ketoan")).json()
    assert set(["voi_chu_xe", "ban_xe", "vay_the_chap_xe"]).issubset(d)
    assert not any(k.startswith("tong") for k in d), "không được có trường tổng gộp bốn túi"
    assert any("KHÔNG cộng chung" in g for g in d["giai_thich"])


# ---------------------------------------------------------------- 2. Đóng kỳ ≠ đã trả
def test_dong_ky_chua_phai_la_da_tra(kỳ_da_duyet):
    """Đóng kỳ nghĩa là hai bên thống nhất con số, không nghĩa là tiền đã đi. Nếu sổ hiểu nhầm hai điều này
    thì khoản đã trả biến mất khỏi công nợ trước khi trả, hoặc ngược lại được trả lần thứ hai."""
    d = client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}", headers=login("ketoan")).json()
    ky = next(k for k in d["cac_ky"] if k["settlement_id"] == kỳ_da_duyet["settlement_id"])
    assert ky["da_chot"] is True
    assert ky["da_tra"] == 0
    assert ky["con_phai_tra"] == ky["phai_tra_theo_bang"] > 0
    assert d["cong_ty_phai_tra"] == ky["con_phai_tra"]


def test_ghi_chi_thi_cong_no_giam_dung_bang_so_da_chi(kỳ_da_duyet):
    h = login("ketoan"); sid = kỳ_da_duyet["settlement_id"]
    truoc = client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}", headers=h).json()["cong_ty_phai_tra"]
    r = client.post("/api/v1/fleet/cong-no/thanh-toan", headers=h,
                    json={"huong": "tra_chu_xe", "settlement_id": sid, "so_tien": 10_000_000,
                          "ngay": str(HOM_NAY), "idem_key": f"chi-{sid}-lan1", "chung_tu": "UNC-001"})
    assert r.status_code == 201, r.text
    sau = client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}", headers=h).json()["cong_ty_phai_tra"]
    assert sau == truoc - 10_000_000


def test_ghi_lai_cung_khoa_khong_tru_them_lan_hai(kỳ_da_duyet):
    """Bấm hai lần một nút, chạy lại một tác vụ, nhập lại từ sao kê – ba việc rất hay xảy ra, và cả ba
    không được thành hai lần trả."""
    h = login("ketoan"); sid = kỳ_da_duyet["settlement_id"]
    truoc = client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}", headers=h).json()["cong_ty_phai_tra"]
    r = client.post("/api/v1/fleet/cong-no/thanh-toan", headers=h,
                    json={"huong": "tra_chu_xe", "settlement_id": sid, "so_tien": 10_000_000,
                          "ngay": str(HOM_NAY), "idem_key": f"chi-{sid}-lan1", "chung_tu": "UNC-001"})
    assert r.status_code == 201 and r.json()["lap_lai"] is True
    sau = client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}", headers=h).json()["cong_ty_phai_tra"]
    assert sau == truoc, "ghi lại cùng khóa không được trừ thêm lần nữa"


def test_chi_vuot_so_con_phai_tra_thi_chan_va_noi_ro_con_bao_nhieu(kỳ_da_duyet):
    """Trả thừa rồi đòi lại khó hơn nhiều lần so với chặn ngay lúc ghi."""
    h = login("ketoan"); sid = kỳ_da_duyet["settlement_id"]
    con = next(k for k in client.get(f"/api/v1/fleet/cong-no/chu-xe/{kỳ_da_duyet['partner_id']}",
                                     headers=h).json()["cac_ky"] if k["settlement_id"] == sid)["con_phai_tra"]
    r = client.post("/api/v1/fleet/cong-no/thanh-toan", headers=h,
                    json={"huong": "tra_chu_xe", "settlement_id": sid, "so_tien": con + 1_000_000,
                          "ngay": str(HOM_NAY), "idem_key": f"chi-{sid}-vuot"})
    assert r.status_code == 422
    assert "vượt số còn phải trả" in r.json()["detail"] and f"{con:,.0f}" in r.json()["detail"]


def test_khong_chi_theo_bang_chua_chot(_startup):
    """Chi theo một bảng còn đang tính là chi theo con số sẽ thay đổi."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe công nợ B"}).json()["id"]
    v = xe("50H-496.23")
    client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h, json={"vehicle_id": v["id"], "partner_id": pid})
    client.post("/api/v1/fleet/chuyen", headers=h,
                json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                      "km_dau": 30_000, "km_cuoi": 30_200, "doanh_thu": 20_000_000, "ten_tour": "Chuyến B"})
    st = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()
    r = client.post("/api/v1/fleet/cong-no/thanh-toan", headers=h,
                    json={"huong": "tra_chu_xe", "settlement_id": st["id"], "so_tien": 1_000_000,
                          "ngay": str(HOM_NAY), "idem_key": f"chi-nhap-{st['id']}"})
    assert r.status_code == 422 and "chưa chốt" in r.json()["detail"]


# ---------------------------------------------------------------- 3. Chưa chốt không phải là nợ
def test_bang_dang_tinh_khong_cong_vao_phai_tra_nhung_cung_khong_bi_giau(_startup):
    """Hai lỗi ngược nhau đều sai: cộng bảng nháp vào số phải trả làm công nợ phồng lên, còn giấu nó đi làm
    người đọc tưởng đã hết việc."""
    d = client.get("/api/v1/fleet/cong-no", headers=login("ketoan")).json()["voi_chu_xe"]
    b = next(c for c in d["chi_tiet"] if c["ho_ten"] == "Chủ xe công nợ B")
    assert b["cong_ty_phai_tra"] == 0, "bảng chưa chốt không phải là số phải trả"
    assert b["dang_tinh_chua_chot"] > 0, "nhưng phải hiện ra ở dòng đang tính"


# ---------------------------------------------------------------- 4. Chưa có bảng ≠ hết nợ
def test_chu_xe_chua_co_bang_quyet_toan_thi_noi_chua_biet_chu_khong_ghi_0(_startup):
    """0 và "chưa biết" dẫn tới hai hành động khác nhau: một bên là đóng hồ sơ, một bên là đi dựng bảng."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe chưa quyết toán"}).json()["id"]
    d = client.get(f"/api/v1/fleet/cong-no/chu-xe/{pid}", headers=h).json()
    assert d["tinh_trang"] == "chua_co_bang_quyet_toan"
    assert "KHÔNG phải bằng 0" in d["ghi_chu"]


def test_chi_ho_chua_vao_ky_nao_thi_hien_rieng_theo_thang(_startup):
    """Tiền công ty đã bỏ ra mà tháng đó chưa ai dựng bảng thì không ai nợ nó trên giấy tờ – đúng chỗ tiền
    nằm im. Phải hiện ra kèm THÁNG để biết cần dựng bảng nào."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe treo chi hộ"}).json()["id"]
    v = xe("50E-957.34")
    client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h, json={"vehicle_id": v["id"], "partner_id": pid})
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": "2026-05-10", "ngay_ve": "2026-05-11",
                          "km_dau": 5_000, "km_cuoi": 5_400, "ten_tour": "Chuyến tháng 5"}).json()
    client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=h,
                json={"kind": "dau", "amount": 4_000_000, "lit": 60, "chung_tu": "HD-T5"})
    d = client.get(f"/api/v1/fleet/cong-no/chu-xe/{pid}", headers=h).json()
    assert any(x["ky"] == "2026-05" and x["so_tien"] == 4_000_000 for x in d["chi_ho_chua_vao_ky"])
    assert d["tong_chi_ho_chua_vao_ky"] == 4_000_000


# ---------------------------------------------------------------- Bán xe và thế chấp
def test_ban_xe_da_ban_giao_ma_con_phai_thu_thi_keu_len(_startup):
    """Xe đã ra khỏi tay mà tiền chưa vào đủ là rủi ro thật, không phải một dòng dữ liệu bình thường."""
    h = login("ketoan")
    v = xe("50F-009.60")
    sc = client.post("/api/v1/fleet/ban-xe", headers=login("chutich"),
                     json={"vehicle_id": v["id"], "gia_ban": 500_000_000, "da_thu": 300_000_000,
                           "ngay_ky": str(HOM_NAY)}).json()
    r = client.post(f"/api/v1/fleet/ban-xe/{sc['id']}/chuyen-buoc", headers=login("chutich"),
                    json={"stage": "ban_giao"})
    assert r.status_code == 200, r.text
    d = client.get("/api/v1/fleet/cong-no", headers=h).json()["ban_xe"]
    dong = next(b for b in d["chi_tiet"] if b["sale_case_id"] == sc["id"])
    assert dong["con_phai_thu"] == 200_000_000
    assert "còn phải thu" in dong["canh_bao"]


def test_du_no_vay_cong_theo_khe_uoc_khong_chia_ve_tung_xe(_startup):
    """Ngân hàng nhận cả gói nhiều xe cho một khoản vay. Chia dư nợ về từng xe rồi cộng lại sẽ ra một con số
    không tồn tại – nên ở đây mỗi dòng là một KHẾ ƯỚC, kèm danh sách xe đang thế chấp."""
    d = client.get("/api/v1/fleet/cong-no", headers=login("ketoan")).json()["vay_the_chap_xe"]
    for k in d["chi_tiet"]:
        assert "du_no" in k and "xe" in k
        assert all("du_no" not in x for x in k["xe"]), "không gán dư nợ vào từng xe"
