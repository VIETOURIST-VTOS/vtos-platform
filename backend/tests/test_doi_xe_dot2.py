"""Đội xe Vietrip – Đợt 2: nhật trình chuyến, bảo dưỡng, đối soát nguồn ngoài.

Các quy tắc dưới đây là câu trả lời của chủ nghiệp vụ ngày 07/9/2026 cho phần trước đây còn để trống. Bộ test
nhắm vào bốn chỗ mà làm sai thì lệch TIỀN chứ không chỉ lệch màn hình:

  1. Nhập lại cùng một file sao kê hai lần KHÔNG được sinh bản ghi trùng – nhưng bản lặp vẫn phải giữ lại để
     chứng minh mình đã loại đúng cái gì. Đây là nghiệm thu Giai đoạn 1 mà tài liệu nêu đích danh.
  2. Xe đổi biển giữa kỳ: giao dịch ePass phải gộp theo XE, không theo biển số. Tra theo biển hiện tại thì
     nửa đầu kỳ rơi ra ngoài và người đối chiếu đi tìm một khoản tiền không thuộc về ai.
  3. Sửa chữa mặc định do CHỦ XE chịu (chốt 07/9/2026), không phải Vietourist tạm ứng.
  4. Một tài xế không nhận hai lệnh chồng ngày – giữ lại sau khi bỏ ràng buộc giờ lái.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe2.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe2.db"): os.remove("test_doi_xe2.db")
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def xe(plate: str) -> dict:
    return next(x for x in client.get("/api/v1/fleet/xe", headers=login("cntt")).json() if x["plate"] == plate)


# ---------------------------------------------------------------- Khử trùng dữ liệu nguồn ngoài
def _sao_ke() -> list:
    return [{"ma_gd": "EP-0001", "bien_so": "50E-957.34", "thoi_diem": f"{HOM_NAY}T08:15:00", "so_tien": 218920},
            {"ma_gd": "EP-0002", "bien_so": "50E-957.34", "thoi_diem": f"{HOM_NAY}T09:40:00", "so_tien": 163800}]


def test_nhap_lai_cung_mot_file_hai_lan_khong_sinh_ban_ghi_trung():
    """Nghiệm thu mà tài liệu nêu đích danh cho Giai đoạn 1. Báo cáo ePass tháng 8/2026 có 2 bản ghi lặp hoàn
    toàn giống nhau trị giá 218.920đ và 163.800đ – không lọc là tính dư đúng bằng số đó."""
    h = login("cntt")
    r1 = client.post("/api/v1/fleet/giao-dich/nhap", headers=h, json={"source": "epass", "rows": _sao_ke()})
    assert r1.status_code == 201, r1.text
    assert r1.json()["da_nhap"] == 2 and r1.json()["ban_ghi_lap"] == 0

    r2 = client.post("/api/v1/fleet/giao-dich/nhap", headers=h, json={"source": "epass", "rows": _sao_ke()})
    assert r2.status_code == 201, r2.text
    assert r2.json()["da_nhap"] == 0, "nhập lại cùng file không được thêm giao dịch mới"
    assert r2.json()["ban_ghi_lap"] == 2

    d = client.get("/api/v1/fleet/giao-dich?source=epass", headers=h).json()
    assert len(d["rows"]) == 2, "danh sách mặc định phải đã loại bản lặp"
    assert d["tong_tien"] == 218920 + 163800, "tổng tiền không được cộng gấp đôi"


def test_ban_ghi_lap_van_duoc_giu_lai_de_doi_chieu():
    """Xóa bản lặp là mất luôn khả năng chứng minh mình đã loại đúng cái gì – mà đây là dữ liệu dùng để chi
    tiền cho đối tác."""
    d = client.get("/api/v1/fleet/giao-dich?source=epass&gom_ban_trung=true", headers=login("cntt")).json()
    lap = [r for r in d["rows"] if r["trung"]]
    assert len(lap) == 2
    assert all("Bản ghi lặp" in r["ghi_chu"] for r in lap)


def test_giao_dich_epass_gop_theo_xe_chu_khong_theo_bien_so():
    """Ca thật trong tài liệu: 50F-046.92 đổi thành 50E-955.31 ngày 13/08/2026. Nếu tra theo biển hiện tại,
    toàn bộ giao dịch trước ngày đổi biển rơi ra ngoài chiếc xe đó."""
    v = xe("50E-955.31"); vid = v["id"]
    doi_ngay = HOM_NAY - timedelta(days=10)
    r = client.post(f"/api/v1/fleet/xe/{vid}/doi-bien", headers=login("cntt"),
                    json={"plate": "51D-777.88", "from_date": str(doi_ngay), "source": "Giấy đăng ký mới"})
    assert r.status_code == 201, r.text

    # Một giao dịch mang biển CŨ, phát sinh TRƯỚC ngày đổi biển
    r = client.post("/api/v1/fleet/giao-dich/nhap", headers=login("cntt"), json={
        "source": "epass", "rows": [{"ma_gd": "EP-OLD-1", "bien_so": "50E-955.31",
                                     "thoi_diem": f"{doi_ngay - timedelta(days=3)}T07:00:00", "so_tien": 55000}]})
    assert r.status_code == 201, r.text
    # Một giao dịch mang biển MỚI, sau ngày đổi
    client.post("/api/v1/fleet/giao-dich/nhap", headers=login("cntt"), json={
        "source": "epass", "rows": [{"ma_gd": "EP-NEW-1", "bien_so": "51D-777.88",
                                     "thoi_diem": f"{HOM_NAY}T07:00:00", "so_tien": 66000}]})

    rows = client.get("/api/v1/fleet/giao-dich?source=epass", headers=login("cntt")).json()["rows"]
    cua_xe = {r["ma_gd"] for r in rows if r["vehicle_id"] == vid}
    assert {"EP-OLD-1", "EP-NEW-1"} <= cua_xe, \
        "giao dịch trước và sau khi đổi biển phải cùng thuộc một chiếc xe"


def test_giao_dich_khong_tra_duoc_xe_thi_gan_co_do_chu_khong_bo_qua():
    """Giao dịch không gán được xe nào là khoản tiền không ai chịu trách nhiệm – phải nổi lên, không im lặng."""
    client.post("/api/v1/fleet/giao-dich/nhap", headers=login("cntt"), json={
        "source": "epass", "rows": [{"ma_gd": "EP-LA-1", "bien_so": "99Z-999.99",
                                     "thoi_diem": f"{HOM_NAY}T10:00:00", "so_tien": 12000}]})
    rows = client.get("/api/v1/fleet/giao-dich?source=epass", headers=login("cntt")).json()["rows"]
    la = next(r for r in rows if r["ma_gd"] == "EP-LA-1")
    assert la["vehicle_id"] is None and la["co"] == "do"
    assert "Chưa tra được xe" in la["ghi_chu"]


# ---------------------------------------------------------------- Bên chịu chi phí (chốt 07/9/2026)
def _tao_chuyen(vid: int, di: date, ve: date, km_dau=None, km_cuoi=None, **kw) -> dict:
    r = client.post("/api/v1/fleet/chuyen", headers=login("cntt"),
                    json={"vehicle_id": vid, "ngay_di": str(di), "ngay_ve": str(ve),
                          "km_dau": km_dau, "km_cuoi": km_cuoi, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_sua_chua_mac_dinh_do_chu_xe_chiu_khong_phai_vietourist_tam_ung():
    """Chốt 07/9/2026: Vietourist tạm ứng nhiên liệu, cầu đường, công tác phí, bãi xe – KHÔNG tạm ứng sửa
    chữa. Nếu phần mềm mặc định ngược lại thì mỗi kỳ quyết toán lại trừ nhầm vào công nợ chủ xe, đúng như
    khoản 22.291.048đ của xe 50H-496.23 tháng 8/2026."""
    vid = xe("50H-496.23")["id"]
    t = _tao_chuyen(vid, HOM_NAY + timedelta(days=60), HOM_NAY + timedelta(days=62), 100_000, 100_600)
    r = client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=login("cntt"),
                    json={"kind": "sua_chua", "amount": 3_000_000, "chung_tu": "HD-0001"})
    assert r.status_code == 201, r.text
    assert r.json()["ben_chiu"] == "chu_xe"

    r = client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=login("cntt"),
                    json={"kind": "dau", "amount": 2_000_000, "lit": 150, "chung_tu": "HD-0002"})
    assert r.json()["ben_chiu"] == "vietourist_tam_ung"

    ct = next(x for x in client.get(f"/api/v1/fleet/chuyen?vehicle_id={vid}", headers=login("cntt")).json()
              if x["id"] == t["id"])
    assert ct["tong_chi_chu_xe"] == 3_000_000
    assert ct["tong_chi_vietourist"] == 2_000_000


def test_khoan_chi_lon_khong_chung_tu_bi_chan_cung():
    """Chặn cứng B6 của đặc tả: mọi khoản chi trên 10 triệu phải có chứng từ gốc."""
    vid = xe("50H-496.23")["id"]
    t = _tao_chuyen(vid, HOM_NAY + timedelta(days=70), HOM_NAY + timedelta(days=71))
    r = client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=login("cntt"),
                    json={"kind": "sua_chua", "amount": 15_000_000})
    assert r.status_code == 422
    assert "chứng từ gốc" in r.json()["detail"]


# ---------------------------------------------------------------- Nhật trình chuyến
def test_km_de_trong_la_chua_do_chu_khong_phai_bang_khong():
    """Dùng 0 làm 'chưa có' là cách chắc chắn nhất để một ngày nào đó báo cáo hiện xe chạy âm mấy trăm nghìn km."""
    vid = xe("50E-957.34")["id"]
    t = _tao_chuyen(vid, HOM_NAY + timedelta(days=80), HOM_NAY + timedelta(days=81))
    assert t["co"] != "xanh", "chuyến chưa có số km mà báo xanh là sai"
    ct = next(x for x in client.get(f"/api/v1/fleet/chuyen?vehicle_id={vid}", headers=login("cntt")).json()
              if x["id"] == t["id"])
    assert ct["km_dau"] is None and ct["km_chay"] is None


def test_km_cuoi_nho_hon_km_dau_bi_tu_choi():
    vid = xe("50E-957.34")["id"]
    r = client.post("/api/v1/fleet/chuyen", headers=login("cntt"),
                    json={"vehicle_id": vid, "ngay_di": str(HOM_NAY + timedelta(days=85)),
                          "ngay_ve": str(HOM_NAY + timedelta(days=86)), "km_dau": 5000, "km_cuoi": 4000})
    assert r.status_code == 422 and "Km cuối nhỏ hơn" in r.json()["detail"]


def test_km_lech_gps_qua_nguong_thi_co_do():
    """Km đọc từ ảnh đồng hồ lệch GPS quá 5% là dấu hiệu đọc sai hoặc khai sai – tài liệu đặt mức đỏ."""
    vid = xe("50E-957.34")["id"]
    t = _tao_chuyen(vid, HOM_NAY + timedelta(days=90), HOM_NAY + timedelta(days=91),
                    km_dau=200_000, km_cuoi=201_000, km_gps=500)
    assert t["co"] == "do"
    assert any("lệch GPS" in x for x in t["ly_do"])


def test_km_noi_giua_hai_chuyen_lech_thi_canh_bao_co_chuyen_chua_khai():
    """Km cuối chuyến trước phải bằng km đầu chuyến sau. Lệch lớn nghĩa là có chuyến chưa khai báo, hoặc
    chặng chạy rỗng/đi garage chưa ghi – hệ thống nêu cả hai khả năng thay vì kết luận một bên."""
    vid = xe("50F-009.60")["id"] if any(x["plate"] == "50F-009.60" for x in
                                        client.get("/api/v1/fleet/xe", headers=login("cntt")).json()) else None
    if vid is None:
        vid = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()[0]["id"]
    _tao_chuyen(vid, HOM_NAY + timedelta(days=100), HOM_NAY + timedelta(days=101), 300_000, 300_500)
    t2 = _tao_chuyen(vid, HOM_NAY + timedelta(days=102), HOM_NAY + timedelta(days=103), 301_000, 301_400)
    assert t2["co"] in ("vang", "do")
    assert any("chưa khai báo" in x for x in t2["ly_do"])


def test_chuyen_con_co_do_thi_khong_xac_nhan_duoc():
    vid = xe("50E-957.34")["id"]
    t = _tao_chuyen(vid, HOM_NAY + timedelta(days=110), HOM_NAY + timedelta(days=111),
                    km_dau=400_000, km_cuoi=401_000, km_gps=500)
    r = client.post(f"/api/v1/fleet/chuyen/{t['id']}/xac-nhan", headers=login("cntt"))
    assert r.status_code == 422
    assert r.json()["detail"]["message"].startswith("Chuyến còn cờ đỏ")


# ---------------------------------------------------------------- Bảo dưỡng
def test_chua_co_lich_su_bao_duong_thi_noi_chua_biet_moc_chu_khong_suy_ra():
    """Đặc tả cấm dùng 9.000 km cố định cho mọi xe vì nguồn ghi các mốc khác nhau."""
    vid = xe("50E-957.34")["id"]
    r = client.get(f"/api/v1/fleet/kiem-tra?vehicle_id={vid}&date_from={HOM_NAY}&date_to={HOM_NAY}",
                   headers=login("tp.dieuhanh")).json()
    ma = {i["code"] for i in r["items"]}
    assert "CHUA_BIET_MOC_BAO_DUONG" in ma
    assert next(i for i in r["items"] if i["code"] == "CHUA_BIET_MOC_BAO_DUONG")["level"] == "UNKNOWN"


def test_vuot_moc_bao_duong_thi_chan_phat_lenh():
    """Chặn cứng B3: km hiện tại + km dự kiến vượt mốc bảo dưỡng kỳ tới."""
    vid = xe("50E-957.34")["id"]
    r = client.post("/api/v1/fleet/bao-duong", headers=login("cntt"),
                    json={"vehicle_id": vid, "ngay": str(HOM_NAY - timedelta(days=60)), "kind": "dinh_ky",
                          "km_luc_lam": 100_000, "km_ky_toi": 109_000, "garage": "Việt Nhân",
                          "so_tien": 5_000_000, "chung_tu": "HD-BD-01"})
    assert r.status_code == 201, r.text
    client.put(f"/api/v1/fleet/xe/{vid}", headers=login("cntt"),
               json={"odo_km": 110_000, "odo_at": str(HOM_NAY)})
    kq = client.get(f"/api/v1/fleet/kiem-tra?vehicle_id={vid}&date_from={HOM_NAY}&date_to={HOM_NAY}",
                    headers=login("tp.dieuhanh")).json()
    assert "VUOT_MOC_BAO_DUONG" in {i["code"] for i in kq["items"]}
    assert kq["muc"] == "BLOCK"


def test_moc_km_tren_phieu_lon_hon_dong_ho_thi_canh_bao_ghi_sai_ky():
    """Ca thật: xe 50H-496.23 có khoản bảo dưỡng mốc km 130.300 trong khi km cuối là 130.245."""
    vid = xe("50H-496.23")["id"]
    client.put(f"/api/v1/fleet/xe/{vid}", headers=login("cntt"), json={"odo_km": 130_245, "odo_at": str(HOM_NAY)})
    r = client.post("/api/v1/fleet/bao-duong", headers=login("cntt"),
                    json={"vehicle_id": vid, "ngay": str(HOM_NAY), "kind": "sua_chua",
                          "km_luc_lam": 130_300, "so_tien": 6_891_048, "chung_tu": "HD-SC-01"})
    assert r.status_code == 201, r.text
    assert any("kỳ phân bổ" in c for c in r.json()["canh_bao"])
    assert r.json()["ben_chiu"] == "chu_xe", "xe hợp tác: sửa chữa do chủ xe chịu"


# ---------------------------------------------------------------- Tài xế
def test_mot_tai_xe_khong_nhan_hai_lenh_chong_ngay():
    """Chốt 07/9/2026: bỏ ràng buộc giờ lái liên tục (xe chạy theo tour, theo tuyến), nhưng GIỮ ràng buộc
    một tài xế không nhận hai lệnh chồng ngày."""
    from app.db.session import SessionLocal
    from app.models.hr import DispatchOrder, Vehicle, Employee
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        drv = db.execute(sel(Employee).where(Employee.department == "doi_xe")).scalars().first()
        xe_a, xe_b = db.execute(sel(Vehicle).order_by(Vehicle.id)).scalars().all()[:2]
        db.add(DispatchOrder(tour_id=1, vehicle_id=xe_a.id, driver_id=drv.id,
                             date_from=HOM_NAY + timedelta(days=200), date_to=HOM_NAY + timedelta(days=202),
                             created_by="kiem_thu", status="da_xac_nhan"))
        db.commit()
        did, bid = drv.id, xe_b.id
    finally:
        db.close()
    kq = client.get(f"/api/v1/fleet/kiem-tra?vehicle_id={bid}&date_from={HOM_NAY + timedelta(days=201)}"
                    f"&date_to={HOM_NAY + timedelta(days=203)}&driver_id={did}",
                    headers=login("tp.dieuhanh")).json()
    assert "TAI_XE_TRUNG_LICH" in {i["code"] for i in kq["items"]}
    assert kq["muc"] == "BLOCK"


def test_tham_so_nghiep_vu_nam_trong_cau_hinh_khong_viet_cung_trong_ma():
    """Đặc tả: "Toàn bộ số dưới đây phải nằm trong bảng cấu hình có giao diện sửa, kèm lịch sử thay đổi.
    Lập trình viên không được viết thẳng vào mã." Kiểm cả giá trị đã chốt 07/9/2026."""
    ps = {p["key"]: p for p in client.get("/api/v1/params", headers=login("chutich")).json()}
    can = {"xe_chu_ky_bao_duong_km": "9000", "xe_bd_gap_km": "2000", "xe_giay_to_vang_ngay": "30",
           "xe_giay_to_do_ngay": "7", "xe_luong_khoan_hop_tac_thang": "7000000",
           "xe_phi_bai_dau_thang": "2000000", "xe_bai_dau_vat": "0.08",
           "xe_chung_tu_bat_buoc_tu": "10000000", "tai_xe_cong_tac_phi": "200000"}
    for k, v in can.items():
        assert k in ps, f"thiếu tham số {k} – đang bị viết cứng trong mã?"
        assert float(ps[k]["value"]) == float(v), f"{k}: {ps[k]['value']} ≠ {v}"


def test_hai_xe_hop_tac_chay_cung_ngay_khong_bi_bao_tai_xe_trung_lich():
    """Bẫy do chính ràng buộc trùng lịch tài xế tạo ra, phát hiện khi chạy lại toàn bộ bộ test.

    Xe hợp tác do đối tác tự lái nên hệ thống tạm gắn một nhân sự đội xe chỉ để có chỗ ghi. Nếu đem người
    thay thế đó đi kiểm trùng lịch thì hai xe hợp tác chạy cùng ngày sẽ báo "tài xế trùng lịch", trong khi
    ngoài đời là hai người của hai đối tác khác nhau – một rào chặn hoàn toàn tưởng tượng."""
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        hop_tac = db.execute(sel(Vehicle).where(Vehicle.op_right == "hop_tac", Vehicle.driver_id == None)
                             ).scalars().all()[:2]
        ids = [v.id for v in hop_tac]
    finally:
        db.close()
    if len(ids) < 2:
        pytest.skip("bản nền không có đủ hai xe hợp tác chưa gán tài xế")
    di, ve = HOM_NAY + timedelta(days=300), HOM_NAY + timedelta(days=301)
    ok = 0
    for vid in ids:
        r = client.post("/api/v1/dispatch", headers=login("dh.lan"),
                        json={"tour_id": 1, "vehicle_id": vid, "date_from": str(di), "date_to": str(ve),
                              "internal_price": 1_000_000})
        if r.status_code == 201: ok += 1
        else:
            assert not any(i["code"] == "TAI_XE_TRUNG_LICH" for i in r.json()["detail"]["vi_pham"]), \
                "hai xe hợp tác khác nhau không được báo trùng tài xế"
    assert ok == 2, "cả hai xe hợp tác đều phải lập được lệnh trong cùng ngày"
