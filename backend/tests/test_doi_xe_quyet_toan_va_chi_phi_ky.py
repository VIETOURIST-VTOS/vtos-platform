"""Màn Hiệu quả đội xe: chuyến chưa quyết toán, và sổ chi phí kỳ.

Hai lỗ hổng đo được trên hệ thật ngày 03/11/2026, bộ test này đóng lại:

  1. Ô TIỀN cộng cả chuyến ĐANG CHẠY. Chuyến đang chạy thường đã biết doanh thu (hợp đồng chốt trước)
     mà chứng từ dầu/cầu đường chưa về, nên biên lợi nhuận của tháng đang chạy vọt lên gần 100% rồi tụt
     dần suốt tháng. Con số nhảy múa đó làm người đọc mất lòng tin vào cả màn hình.

  2. Màn này KHÔNG đọc sổ `chi-phi-ky` – bảo hiểm, đăng kiểm, lương tài xế, bãi xe, lãi vay. Màn Lãi lỗ
     đội xe đọc từ lâu. Hai màn cùng nói "lợi nhuận" của cùng một xe cùng một kỳ mà ra hai con số, và
     con số CAO HƠN lại là con số Chủ tịch nhìn. Tháng 10/2026 chênh 125,8 triệu trên một tháng.

Nguyên tắc chung của cả hai: cái bị bỏ ra khỏi ô tiền phải được NÓI RA, không biến mất lặng lẽ.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe_qt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe_qt.db"): os.remove("test_doi_xe_qt.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"{HOM_NAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def ds_xe():
    return client.get("/api/v1/fleet/xe", headers=login("cntt")).json()


def hieu_qua():
    return client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()


def hang_xe(hq, vid):
    return next((x for x in hq["xe"] if x["vehicle_id"] == vid), None)


def nap(rows):
    return client.post("/api/v1/fleet/chuyen/nhap-hang-loat", headers=login("ketoan"),
                       json={"nguon": "bao_cao_vietrip", "tao_xe_thieu": False, "rows": rows}).json()


# ----------------------------------------------------------------- 1. quyết toán

def test_chuyen_cu_mac_dinh_la_da_quyet_toan_nen_so_lich_su_khong_doi():
    """Bản nâng cấp không được phép đổi một đồng nào của quá khứ.

    Chuyến tạo qua cửa nhập tay, không ai nói gì về quyết toán → phải được tính tiền như trước."""
    v = ds_xe()[0]["id"]
    r = client.post("/api/v1/fleet/chuyen", headers=login("cntt"), json={
        "vehicle_id": v, "ten_tour": "Chuyến cũ", "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
        "km_dau": 1000, "km_cuoi": 1100, "doanh_thu": 5_000_000})
    assert r.status_code == 201
    assert hang_xe(hieu_qua(), v)["doanh_thu"] >= 5_000_000


def test_chuyen_dang_chay_khong_vao_o_tien_nhung_van_duoc_dem_o_o_van_hanh():
    """Xe đang trên đường vẫn là xe đang khai thác – bỏ nó khỏi công suất là báo thấp giả."""
    v = ds_xe()[1]["id"]
    bien = ds_xe()[1]["plate"]
    kq = nap([{"ma_phieu": f"QT-DANGCHAY-{v}", "bien_so": bien, "ngay_di": str(HOM_NAY),
               "ngay_ve": str(HOM_NAY), "ten_tour": "Đang chạy", "doanh_thu": 35_000_000,
               "quyet_toan": False}])
    assert kq["da_nhap"] == 1
    x = hang_xe(hieu_qua(), v)
    assert x["doanh_thu"] == 0, "doanh thu chuyến đang chạy KHÔNG được vào ô tiền"
    assert x["so_chuyen"] == 1, "nhưng vẫn phải đếm là một chuyến"
    assert x["ngay_khai_thac"] == 1, "và vẫn là một ngày khai thác"
    assert x["so_chuyen_chua_qt"] == 1
    assert x["doanh_thu_chua_qt"] == 35_000_000


def test_phan_bo_ra_khoi_o_tien_phai_duoc_noi_ra_chu_khong_bien_mat_lang_le():
    hq = hieu_qua()
    assert hq["tong"]["so_chuyen_chua_quyet_toan"] >= 1
    assert hq["tong"]["doanh_thu_chua_quyet_toan"] >= 35_000_000
    assert "chưa quyết toán" in hq["ghi_chu"]


def test_bien_loi_nhuan_khong_bi_thoi_len_boi_chuyen_chua_co_chi_phi():
    """Đây là lý do tồn tại của cả cột quyết_toán: doanh thu 35 triệu chi phí 0 thì biên ~100%."""
    v = ds_xe()[1]["id"]
    x = hang_xe(hieu_qua(), v)
    assert x["bien_loi_nhuan"] == "chua_du_du_lieu", "chưa có chuyến quyết toán nào thì chưa có biên"


def test_quyet_toan_xong_thi_tien_vao_so_qua_duong_mo_lai_roi_sua():
    """Chuyến đang chạy quyết toán xong phải bù được tiền vào – nếu không, nạp sớm là mất doanh thu."""
    v = ds_xe()[1]["id"]
    ds = client.get(f"/api/v1/fleet/chuyen?tu={HOM_NAY}&den={HOM_NAY}", headers=login("cntt")).json()
    t = next(x for x in ds if x["ma_phieu"] == f"QT-DANGCHAY-{v}")
    assert t["quyet_toan"] is False
    assert client.post(f"/api/v1/fleet/chuyen/{t['id']}/mo-lai", headers=login("ketoan"),
                       json={"ly_do": "lái xe đã nộp chứng từ"}).status_code == 200
    r = client.put(f"/api/v1/fleet/chuyen/{t['id']}", headers=login("ketoan"),
                   json={"doanh_thu": 35_000_000, "quyet_toan": True})
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=login("ketoan"),
                       json={"kind": "dau", "amount": 12_000_000, "lit": 390,
                             "chung_tu": "SAOKE-01"}).status_code == 201
    x = hang_xe(hieu_qua(), v)
    assert x["doanh_thu"] == 35_000_000, "quyết toán xong thì doanh thu phải vào sổ"
    assert x["so_chuyen_chua_qt"] == 0


# ----------------------------------------------------------------- 2. chi phí kỳ

def test_chi_phi_ky_pham_vi_xe_phai_tru_vao_loi_nhuan_cua_chinh_chiec_do():
    """Màn Lãi lỗ đội xe đã trừ từ lâu; màn Hiệu quả thì chưa. Hai màn phải nói cùng một con số."""
    v = ds_xe()[1]["id"]
    truoc = hang_xe(hieu_qua(), v)["loi_nhuan"]
    assert client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json={
        "ky": KY, "nhom": "bao_hiem", "vehicle_id": v, "so_tien": 6_070_300,
        "chung_tu": "BH-03471", "mo_ta": "TNDS bắt buộc"}).status_code == 201
    x = hang_xe(hieu_qua(), v)
    assert x["loi_nhuan"] == truoc - 6_070_300
    assert x["chi_phi_ky"] == 6_070_300
    assert x["chi_tiet_chi_phi_ky"]["bao_hiem"] == 6_070_300


def test_chi_phi_doi_tru_vao_loi_nhuan_cua_ky_nhung_khong_phan_bo_vao_xe_nao():
    """Phân bổ cần một tiêu thức, mà tiêu thức khác nhau cho ra thứ hạng xe khác nhau.

    Xếp hạng xe theo một tiêu thức người đọc không chọn là đổi kết luận thay họ."""
    truoc = hieu_qua()["tong"]["loi_nhuan"]
    tong_xe_truoc = sum(x["loi_nhuan"] for x in hieu_qua()["xe"])
    assert client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json={
        "ky": KY, "nhom": "bai_xe", "so_tien": 27_250_560, "chung_tu": "HD-4924+4925",
        "mo_ta": "Bãi Cảng Sài Gòn"}).status_code == 201
    hq = hieu_qua()
    assert hq["tong"]["chi_phi_doi"] == 27_250_560
    assert hq["tong"]["loi_nhuan"] == truoc - 27_250_560, "phải trừ vào lợi nhuận của KỲ"
    assert sum(x["loi_nhuan"] for x in hq["xe"]) == tong_xe_truoc, "nhưng không xê dịch xe nào"
    assert hq["tong"]["chi_tiet_chi_phi_doi"]["bai_xe"] == 27_250_560
    assert "phân bổ" in hq["ghi_chu"]


def test_tong_ky_khong_the_cong_tay_tu_cac_hang_xe():
    """Cộng tay các hàng xe sẽ bỏ sót chi phí đội – nên tổng phải do máy chủ tính và trả về."""
    hq = hieu_qua()
    assert hq["tong"]["chi_phi"] == hq["tong"]["chi_phi_xe"] + hq["tong"]["chi_phi_doi"]
    assert sum(x["chi_phi"] for x in hq["xe"]) == hq["tong"]["chi_phi_xe"]
    assert hq["tong"]["chi_phi_doi"] > 0, "bài test này vô nghĩa nếu không có chi phí đội"


def test_cung_mot_khoan_sua_xe_o_hai_bang_thi_canh_bao_chu_khong_tu_tru_bot():
    """Trừ nhầm thì mất một khoản chi có thật mà không ai biết. Máy viết phép tính, người quyết con số."""
    v = ds_xe()[2]["id"]
    assert client.post("/api/v1/fleet/bao-duong", headers=login("cntt"), json={
        "vehicle_id": v, "ngay": str(HOM_NAY), "kind": "dinh_ky",
        "so_tien": 6_891_048, "mo_ta": "BD 6.10"}).status_code == 201
    assert client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json={
        "ky": KY, "nhom": "bao_duong", "vehicle_id": v, "so_tien": 6_891_048,
        "chung_tu": "BD-21.10", "mo_ta": "Bảo dưỡng T10"}).status_code == 201
    hq = hieu_qua()
    assert hq["canh_bao"], "phải nói ra, không im lặng"
    assert any("hai lần" in c for c in hq["canh_bao"]), hq["canh_bao"]
    x = hang_xe(hq, v)
    assert x["sua_chua"] == 6_891_048 * 2, "KHÔNG tự trừ bớt – vẫn cộng cả hai, và cảnh báo"


# ----------------------------------------------------------------- 3. bên chịu

def test_khoan_chu_xe_tu_chiu_khong_vao_lai_lo_cua_vietourist():
    """Cộng khoản chủ xe tự gánh vào đây là làm Vietourist gánh chi phí của người khác.

    Đo trên hệ thật 03/11/2026: 1.796 dòng chi phí chuyến đều là `vietourist_tam_ung`, bảng bảo dưỡng
    trống. Nên hàng rào này dựng lúc nó chưa đổi một đồng nào – đúng lúc để dựng."""
    v = ds_xe()[3]["id"]
    r = client.post("/api/v1/fleet/chuyen", headers=login("cntt"), json={
        "vehicle_id": v, "ten_tour": "Có khoản chủ xe chịu", "ngay_di": str(HOM_NAY),
        "ngay_ve": str(HOM_NAY), "km_dau": 500, "km_cuoi": 700, "doanh_thu": 9_000_000})
    tid = r.json()["id"]
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=login("ketoan"), json={
        "kind": "dau", "amount": 3_000_000, "lit": 98, "chung_tu": "A1"}).status_code == 201
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=login("ketoan"), json={
        "kind": "sua_chua", "amount": 5_000_000, "ben_chiu": "chu_xe",
        "chung_tu": "B2"}).status_code == 201
    x = hang_xe(hieu_qua(), v)
    assert x["chi_phi"] == 3_000_000, "chỉ phần Vietourist tạm ứng mới là chi phí của Vietourist"
    assert x["chi_phi_chu_xe"] == 5_000_000, "phần chủ xe chịu vẫn phải nói ra, không biến mất"
    assert x["loi_nhuan"] == 9_000_000 - 3_000_000


def test_chuyen_nhap_va_chuyen_huy_khong_phai_so_lieu():
    """Nháp là đang ghi dở, hủy là chuyến không chạy. Cộng vào là đếm việc chưa xảy ra hoặc đã bỏ."""
    from app.db.session import SessionLocal
    from app.models.fleet import Trip
    v = ds_xe()[3]["id"]
    truoc = hang_xe(hieu_qua(), v)
    dt_truoc = truoc["doanh_thu"] if truoc else 0
    ch_truoc = truoc["so_chuyen"] if truoc else 0
    db = SessionLocal()
    try:
        for st in ("nhap", "huy"):
            db.add(Trip(vehicle_id=v, ten_tour=f"Chuyến {st}", ngay_di=HOM_NAY, ngay_ve=HOM_NAY,
                        doanh_thu=50_000_000, status=st, created_by="test"))
        db.commit()
    finally:
        db.close()
    sau = hang_xe(hieu_qua(), v)
    assert sau["doanh_thu"] == dt_truoc, "100 triệu của chuyến nháp/hủy không được vào sổ tiền"
    assert sau["so_chuyen"] == ch_truoc, "và cũng không được đếm là chuyến"


def test_chuyen_cho_xac_nhan_van_tinh_tien_nhung_duoc_noi_ra():
    """Loại chuyến đã chạy thật ra khỏi sổ chỉ vì thiếu một chữ ký là giấu doanh thu có thật."""
    hq = hieu_qua()
    assert hq["tong"]["so_chuyen_cho_xac_nhan"] >= 1
    assert any("CHỜ XÁC NHẬN" in c for c in hq["canh_bao"]), hq["canh_bao"]


# ----------------------------------------------------------------- 4. hàng rào chứng từ

def test_khoan_lon_trong_so_chi_phi_ky_bat_buoc_co_chung_tu():
    """Sổ chi phí kỳ ghi những khoản lớn nhất của đội xe – bảo hiểm, bảo dưỡng, bãi xe, lãi vay.

    Trước bản này ngưỡng chứng từ (chặn cứng B6) chỉ áp cho chi phí CHUYẾN, còn quyển sổ hàng trăm triệu
    này nhận `chung_tu` như chuỗi tự do không ai kiểm. Hàng rào đặt nhầm chỗ."""
    r = client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json={
        "ky": KY, "nhom": "lai_vay", "so_tien": 50_000_000, "mo_ta": "Lãi vay không chứng từ"})
    assert r.status_code == 422
    assert "chứng từ" in r.json()["detail"]


def test_nhap_lai_cung_khoan_van_nghe_dung_ly_do_chu_khong_nghe_thieu_chung_tu():
    """Báo sai lý do thì người nhập đi tìm chứng từ rồi nhập lại lần nữa – thành chi phí nhân đôi."""
    body = {"ky": KY, "nhom": "quan_ly", "so_tien": 3_580_000, "chung_tu": "SIM+CAM",
            "mo_ta": "SIM và camera"}
    assert client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"), json=body).status_code == 201
    lai = client.post("/api/v1/fleet/chi-phi-ky", headers=login("ketoan"),
                      json={**body, "chung_tu": ""})
    assert lai.status_code == 422
    assert "nhân đôi" in lai.json()["detail"], lai.json()["detail"]


# ----------------------------------------------------------------- 5. hủy chuyến

def test_huy_chuyen_phai_ghi_ly_do_va_chuyen_huy_roi_khoi_moi_bao_cao():
    """Trước bản này TRIP_STATUS khai giá trị "huy" nhưng không dòng mã nào gán – một chuyến gõ nhầm
    không có đường nào ra. Hai phiếu dò khuôn ZZPROBE ngày 19/10/2026 còn nằm trong sổ vì thế."""
    v = ds_xe()[0]["id"]
    tid = client.post("/api/v1/fleet/chuyen", headers=login("cntt"), json={
        "vehicle_id": v, "ten_tour": "Phiếu gõ nhầm", "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
        "doanh_thu": 99_000_000}).json()["id"]
    truoc = hang_xe(hieu_qua(), v)["doanh_thu"]
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/huy", headers=login("ketoan"),
                       json={"ly_do": ""}).status_code == 422, "hủy mà không ghi lý do phải bị chặn"
    r = client.post(f"/api/v1/fleet/chuyen/{tid}/huy", headers=login("ketoan"),
                    json={"ly_do": "phiếu dò khuôn, không phải chuyến thật"})
    assert r.status_code == 200, r.text
    assert hang_xe(hieu_qua(), v)["doanh_thu"] == truoc - 99_000_000
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/huy", headers=login("ketoan"),
                       json={"ly_do": "lần hai"}).status_code == 422, "hủy hai lần phải bị chặn"


def test_chuyen_da_huy_van_nam_trong_so_kem_ly_do_chu_khong_bien_mat():
    """Xóa đi thì sổ hôm nay không khớp sổ hôm qua mà không còn dấu vết nào giải thích."""
    ds = client.get(f"/api/v1/fleet/chuyen?tu={HOM_NAY}&den={HOM_NAY}", headers=login("cntt")).json()
    t = next(x for x in ds if x["ten_tour"] == "Phiếu gõ nhầm")
    assert t["status"] == "huy"
    assert "dò khuôn" in t["note"]


# ----------------------------------------------------------------- 6. khóa nối chống cộng trùng

def test_dong_chi_phi_noi_toi_phieu_bao_duong_thi_chi_tinh_mot_lan():
    """Cùng một hóa đơn garage nằm ở hai bảng. Khai khóa nối thì báo cáo biết đó là MỘT khoản."""
    v = ds_xe()[2]["id"]
    mid = client.post("/api/v1/fleet/bao-duong", headers=login("cntt"), json={
        "vehicle_id": v, "ngay": str(HOM_NAY), "kind": "sua_chua", "so_tien": 4_000_000,
        "chung_tu": "GARA-9", "noi_dung": "thay lốp"}).json()["id"]
    truoc = hang_xe(hieu_qua(), v)["chi_phi"]
    tid = client.post("/api/v1/fleet/chuyen", headers=login("cntt"), json={
        "vehicle_id": v, "ten_tour": "Chuyến có sửa xe", "ngay_di": str(HOM_NAY),
        "ngay_ve": str(HOM_NAY), "doanh_thu": 1_000_000}).json()["id"]
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=login("ketoan"), json={
        "kind": "sua_chua", "amount": 4_000_000, "chung_tu": "GARA-9",
        "maintenance_id": mid}).status_code == 201
    sau = hang_xe(hieu_qua(), v)["chi_phi"]
    assert sau == truoc, "khoản đã nối chỉ được tính một lần, không cộng thêm lần hai"


def test_khong_khai_khoa_noi_thi_cong_ca_hai_va_canh_bao_chu_khong_tu_tru():
    """Đoán bằng ngày và số tiền sẽ gộp nhầm hai khoản có thật – hai xe cùng thay một loại lốp."""
    v = ds_xe()[1]["id"]
    truoc = hang_xe(hieu_qua(), v)["chi_phi"]
    client.post("/api/v1/fleet/bao-duong", headers=login("cntt"), json={
        "vehicle_id": v, "ngay": str(HOM_NAY), "kind": "sua_chua", "so_tien": 2_500_000,
        "chung_tu": "GARA-10"})
    sau = hang_xe(hieu_qua(), v)["chi_phi"]
    assert sau == truoc + 2_500_000, "không khai khóa nối thì vẫn là một khoản riêng, phải cộng"
