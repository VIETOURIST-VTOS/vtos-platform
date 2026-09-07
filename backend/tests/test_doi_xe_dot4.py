"""Đội xe Vietrip – Đợt 4: gợi ý điều xe, hiệu quả xe và tài xế, bản tin sáng.

Đợt này phần mềm chuyển từ ghi chép sang tham mưu, nên rủi ro cũng đổi loại: không còn là mất tiền vì tính
sai, mà là người ta TIN một con số vô nghĩa. Bộ test nhắm vào đúng bốn chỗ sinh ra con số vô nghĩa:

  1. Hai chuyến trong cùng một ngày bị cộng thành hai ngày xe – thổi phồng mức sử dụng đội xe gần gấp đôi.
  2. Mẫu số bằng 0 ra kết quả 0 thay vì "chưa đủ dữ liệu" – và 0 đồng/km sẽ đứng đầu bảng tiết kiệm nhiên liệu.
  3. Chấm điểm tài xế bằng việc của người khác, do gán lịch sử theo tài xế HIỆN TẠI của xe.
  4. Xếp hạng không nói rõ kỳ nào, trong bao nhiêu xe, theo bộ quy tắc nào.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe4.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe4.db"): os.remove("test_doi_xe4.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"{HOM_NAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def ds_xe():
    return client.get("/api/v1/fleet/xe", headers=login("cntt")).json()



def _them_xe_hop_le(plate: str, code: str) -> int:
    """Thêm một xe ĐỦ điều kiện điều đi, dùng để dựng các tình huống cần nhiều hơn 3 xe hợp lệ.

    Phải gán tài xế: xe sở hữu chưa gán tài xế bị chặn ở bước lọc cứng, nên một chiếc xe "trắng" thêm vào
    không làm tăng số phương án hợp lệ."""
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle, Employee
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        v = db.execute(sel(Vehicle).where(Vehicle.plate == plate)).scalars().first()
        if v: return v.id
        e = Employee(code=f"NSKT{code[-4:]}", full_name=f"Tài xế kiểm thử {code}", department="doi_xe",
                     position="tai_xe", contract_type="hdld", base_salary=7_000_000)
        db.add(e); db.flush()
        v = Vehicle(plate=plate, code=code, seats=45, kind="noi_bo", driver_id=e.id,
                    internal_rate_per_day=3_000_000, op_right="so_huu")
        db.add(v); db.commit()
        return v.id
    finally:
        db.close()


def tao_chuyen(vid, di, ve, **kw):
    r = client.post("/api/v1/fleet/chuyen", headers=login("cntt"),
                    json={"vehicle_id": vid, "ngay_di": str(di), "ngay_ve": str(ve), **kw})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- Ngày khai thác
def test_hai_chuyen_cung_ngay_la_MOT_ngay_xe_khong_phai_hai():
    """Cộng thành hai ngày là thổi phồng mức sử dụng đội xe gần gấp đôi ở mùa cao điểm, và mọi chỉ số
    "lợi nhuận trên ngày chạy" đều sai theo."""
    v = ds_xe()[0]["id"]
    ngay = HOM_NAY.replace(day=min(HOM_NAY.day, 28))
    tao_chuyen(v, ngay, ngay, km_dau=1000, km_cuoi=1100, doanh_thu=5_000_000)
    tao_chuyen(v, ngay, ngay, km_dau=1100, km_cuoi=1150, doanh_thu=3_000_000)
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()
    r = next(x for x in hq["xe"] if x["vehicle_id"] == v)
    assert r["so_chuyen"] == 2
    assert r["ngay_khai_thac"] == 1, "hai chuyến cùng ngày phải là một ngày xe"


def test_chuyen_nhieu_ngay_dem_du_so_ngay():
    v = ds_xe()[1]["id"]
    d1 = HOM_NAY.replace(day=1)
    tao_chuyen(v, d1, d1 + timedelta(days=2), km_dau=500, km_cuoi=1000, doanh_thu=9_000_000)
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()
    r = next(x for x in hq["xe"] if x["vehicle_id"] == v)
    assert r["ngay_khai_thac"] == 3


# ---------------------------------------------------------------- Mẫu số bằng 0
def test_mau_so_bang_khong_tra_chua_du_du_lieu_chu_khong_tra_khong():
    """0 đồng/km sẽ đứng đầu bảng xếp hạng tiết kiệm nhiên liệu và được gợi ý điều xe đầu tiên – đúng chiếc
    xe chưa có số liệu nào."""
    v = ds_xe()[2]["id"]
    tao_chuyen(v, HOM_NAY, HOM_NAY, doanh_thu=1_000_000)      # không có km, không có chi phí dầu
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()
    r = next(x for x in hq["xe"] if x["vehicle_id"] == v)
    assert r["dau_dong_tren_km"] == "chua_du_du_lieu"
    assert r["km_moi_lit"] == "chua_du_du_lieu"
    assert r["sua_chua_tren_km"] == "chua_du_du_lieu"
    assert r["loi_nhuan_moi_ngay"] != "chua_du_du_lieu", "có ngày khai thác thì tính được lợi nhuận mỗi ngày"


def test_xep_hang_noi_ro_ky_tap_so_sanh_va_phien_ban_quy_tac():
    """"Hạng 3" không có nghĩa nếu không nói hạng 3 trong bao nhiêu xe, kỳ nào, theo bộ quy tắc nào."""
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()
    assert hq["ky"] == KY and hq["rule_version"]
    assert hq["tap_so_sanh_xe"] == len(hq["xe"])
    assert all(x["hang"] for x in hq["xe"])
    assert "chưa đủ dữ liệu" in hq["ghi_chu"] and "một ngày" in hq["ghi_chu"]
    assert "không đưa dữ liệu cá nhân ngoài công việc vào chấm điểm" in hq["gioi_han"]


def test_tai_xe_cham_theo_nguoi_thuc_hien_tung_chuyen():
    """Gán toàn bộ lịch sử cho tài xế HIỆN TẠI của xe là chấm điểm người này bằng việc của người khác."""
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle, Employee
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        drs = db.execute(sel(Employee).where(Employee.department == "doi_xe")).scalars().all()
        if len(drs) < 2: pytest.skip("bản nền chưa có hai tài xế")
        cu, moi = drs[0].id, drs[1].id
        v = db.execute(sel(Vehicle).order_by(Vehicle.id)).scalars().first()
        v.driver_id = cu; db.commit(); vid = v.id
    finally:
        db.close()
    ngay = HOM_NAY.replace(day=min(HOM_NAY.day, 20))
    tao_chuyen(vid, ngay, ngay, driver_id=moi, km_dau=5000, km_cuoi=5100, doanh_thu=7_000_000)
    # Đổi tài xế hiện tại của xe SAU khi chuyến đã chạy
    db = SessionLocal()
    try:
        db.get(Vehicle, vid).driver_id = cu; db.commit()
    finally:
        db.close()
    hq = client.get(f"/api/v1/fleet/hieu-qua?ky={KY}", headers=login("chutich")).json()
    r_moi = next((x for x in hq["tai_xe"] if x["driver_id"] == moi), None)
    assert r_moi is not None, "người thực hiện chuyến phải có mặt trong bảng tài xế"
    assert r_moi["doanh_thu"] >= 7_000_000


# ---------------------------------------------------------------- Gợi ý điều xe
def test_loc_cung_truoc_xep_hang_sau():
    """Xe bị chặn không được xuất hiện trong gợi ý dù điểm cao đến đâu. Nếu để chung một thang điểm thì một
    chiếc xe hết đăng kiểm vẫn có thể đứng trên một chiếc xe hợp lệ chỉ vì tốn ít dầu hơn."""
    v = ds_xe()[0]
    client.post("/api/v1/fleet/giay-to", headers=login("cntt"),
                json={"kind": "dang_kiem", "vehicle_id": v["id"], "number": "DK-HET",
                      "expires_on": str(HOM_NAY - timedelta(days=1)), "verify": "da_xac_minh"})
    d1 = HOM_NAY + timedelta(days=500)
    g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1 + timedelta(days=1)}",
                   headers=login("tp.dieuhanh")).json()
    assert v["id"] not in [p["vehicle_id"] for p in g["phuong_an"]]
    loai = next(x for x in g["bi_loai"] if x["vehicle_id"] == v["id"])
    assert any("Đăng kiểm" in l for l in loai["ly_do"])


def test_moi_phuong_an_kem_ly_do_bang_loi_va_khong_chi_mot_chi_so():
    """Đặc tả: "Không chỉ dựa vào điểm CSKH hoặc tiền dầu/km"."""
    d1 = HOM_NAY + timedelta(days=510)
    g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1 + timedelta(days=1)}&km_du_kien=400",
                   headers=login("tp.dieuhanh")).json()
    assert g["phuong_an"], "phải còn xe hợp lệ để gợi ý"
    assert len(g["phuong_an"]) <= 3
    for p in g["phuong_an"]:
        assert p["ly_do"], "mỗi phương án phải có lý do bằng lời cho người chốt lệnh đọc"
        assert any("ngày công" in l for l in p["ly_do"]), "phải có thành phần cân bằng ngày công"
    diem = [p["diem"] for p in g["phuong_an"]]
    assert diem == sorted(diem, reverse=True), "phải xếp theo điểm giảm dần"


def test_chay_lai_cung_du_lieu_ra_cung_ket_qua():
    """Đặc tả: "Chạy lại cùng dữ liệu phải ra cùng kết quả." Thứ tự phải ổn định, không phụ thuộc thứ tự
    trả về của cơ sở dữ liệu."""
    d1 = HOM_NAY + timedelta(days=520)
    url = f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1 + timedelta(days=1)}"
    a = client.get(url, headers=login("tp.dieuhanh")).json()["phuong_an"]
    b = client.get(url, headers=login("tp.dieuhanh")).json()["phuong_an"]
    assert [x["vehicle_id"] for x in a] == [x["vehicle_id"] for x in b]
    assert [x["diem"] for x in a] == [x["diem"] for x in b]


def test_chon_xe_he_thong_danh_gia_thap_hon_thi_phai_ghi_ly_do():
    """Ghi vết bắt buộc của đặc tả A1: đây là dữ liệu duy nhất để sau mỗi quý đánh giá lại chất lượng thuật
    toán gợi ý. Không có nó thì chỉ còn tranh luận bằng cảm nhận.

    Điều kiện là hệ thống ĐÁNH GIÁ THẤP HƠN, không phải chỉ "nằm ngoài top 3". Khi các xe điểm bằng nhau –
    đội xe nhỏ, hoặc chưa có số liệu vận hành – thì bắt giải trình vì sao chọn xe này thay vì xe kia là bắt
    người ta giải thích một khác biệt mà chính hệ thống không nhìn thấy, và ô lý do sẽ được điền cho xong.

    Nên test này dựng đúng tình huống hệ thống CÓ ý kiến: một xe mà tài xế đang nhiều ngày công nhất, tức bị
    trừ điểm ở tiêu chí cân bằng ngày công."""
    from app.db.session import SessionLocal
    from app.models.hr import DispatchOrder, Vehicle
    from sqlalchemy import select as sel
    d1 = HOM_NAY + timedelta(days=530)
    # Bản nền chỉ còn 3 xe hợp lệ nên cả ba lọt hết top 3 và không bao giờ có xe "ngoài nhóm đề xuất".
    # Thêm một xe hợp lệ nữa để dựng đúng tình huống cần kiểm.
    _them_xe_hop_le("51Z-777.77", "XE7777")
    # Chọn xe trong nhóm HỢP LỆ (đã qua lọc cứng) và có tài xế – xe bị chặn thì không có điểm để so.
    g0 = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}", headers=login("tp.dieuhanh")).json()
    ung_vien = next((p for p in g0["tat_ca"] if p["tai_xe_id"]), None)
    if ung_vien is None: pytest.skip("không có xe hợp lệ nào đã gán tài xế")
    vid, did = ung_vien["vehicle_id"], ung_vien["tai_xe_id"]
    db = SessionLocal()
    try:
        # Chất ngày công cho tài xế của xe này để hệ thống có lý do xếp nó thấp hơn.
        db.add(DispatchOrder(tour_id=1, vehicle_id=vid, driver_id=did,
                             date_from=d1 - timedelta(days=20), date_to=d1 - timedelta(days=5),
                             created_by="kiem_thu", status="da_xac_nhan"))
        db.commit()
    finally:
        db.close()

    g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}", headers=login("tp.dieuhanh")).json()
    diem = {p["vehicle_id"]: p["diem"] for p in g["tat_ca"]}
    thap_nhat_top = min(p["diem"] for p in g["phuong_an"])
    if diem.get(vid) is None or diem[vid] >= thap_nhat_top:
        pytest.skip("không dựng được tình huống hệ thống đánh giá thấp hơn trên bản nền này")

    t = client.get("/api/v1/tours", headers=login("cntt")).json()[0]
    body = {"tour_id": t["id"], "vehicle_id": vid, "date_from": str(d1), "date_to": str(d1),
            "internal_price": 1_000_000}
    r = client.post("/api/v1/dispatch", headers=login("dh.lan"), json=body)
    assert r.status_code == 422, r.text
    d = r.json()["detail"]
    assert "phải ghi lý do" in d["message"]
    assert d["diem_xe_chon"] < d["diem_thap_nhat_trong_nhom_de_xuat"]
    assert d["he_thong_nhan_xet"], "phải nói ra hệ thống chê điểm gì, không chỉ đưa hai con số điểm"
    assert d["goi_y"], "phải trả kèm danh sách gợi ý để người chốt lệnh so sánh"

    r2 = client.post("/api/v1/dispatch", headers=login("dh.lan"),
                     json={**body, "ly_do_khac_goi_y": "Khách yêu cầu đúng xe này vì đã đi lần trước"})
    assert r2.status_code == 201, r2.text
    assert r2.json()["kem_hon_de_xuat"] is True
    ds = client.get("/api/v1/fleet/lenh-dieu-xe", headers=login("chutich")).json()
    assert any(x["ly_do_khac_goi_y"] for x in ds), "lý do phải được lưu cùng lệnh"


def test_diem_bang_nhau_thi_khong_bat_giai_trinh():
    """Chốt an toàn của quyết định trên: khi hệ thống không phân biệt được hai xe, nó không được đòi người
    dùng giải thích sự khác biệt đó."""
    d1 = HOM_NAY + timedelta(days=560)
    g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}", headers=login("tp.dieuhanh")).json()
    if not g["phuong_an"]: pytest.skip("không còn xe hợp lệ")
    thap_nhat = min(p["diem"] for p in g["phuong_an"])
    bang_diem = [p for p in g["tat_ca"]
                 if p["vehicle_id"] not in [q["vehicle_id"] for q in g["phuong_an"]] and p["diem"] >= thap_nhat]
    if not bang_diem:
        # Bản nền ít xe nên cả tập hợp lệ lọt hết top 3. Thêm một xe hợp lệ nữa, chưa có số liệu vận hành –
        # nó sẽ bằng điểm với nhóm đề xuất và nằm ngoài top, đúng tình huống cần kiểm.
        _them_xe_hop_le("51Y-888.88", "XE8888")
        g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}",
                       headers=login("tp.dieuhanh")).json()
        thap_nhat = min(p["diem"] for p in g["phuong_an"])
        bang_diem = [p for p in g["tat_ca"]
                     if p["vehicle_id"] not in [q["vehicle_id"] for q in g["phuong_an"]] and p["diem"] >= thap_nhat]
    if not bang_diem: pytest.skip("không dựng được xe ngoài top mà điểm bằng nhóm đề xuất")
    t = client.get("/api/v1/tours", headers=login("cntt")).json()[0]
    r = client.post("/api/v1/dispatch", headers=login("dh.lan"),
                    json={"tour_id": t["id"], "vehicle_id": bang_diem[0]["vehicle_id"],
                          "date_from": str(d1), "date_to": str(d1), "internal_price": 1_000_000})
    assert r.status_code == 201, "điểm không thấp hơn thì không được đòi lý do: " + r.text


def test_chon_dung_xe_trong_top_thi_khong_bat_ghi_ly_do():
    d1 = HOM_NAY + timedelta(days=540)
    g = client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}", headers=login("tp.dieuhanh")).json()
    if not g["phuong_an"]: pytest.skip("không còn xe hợp lệ")
    t = client.get("/api/v1/tours", headers=login("cntt")).json()[0]
    r = client.post("/api/v1/dispatch", headers=login("dh.lan"),
                    json={"tour_id": t["id"], "vehicle_id": g["phuong_an"][0]["vehicle_id"],
                          "date_from": str(d1), "date_to": str(d1), "internal_price": 1_000_000})
    assert r.status_code == 201, r.text
    assert r.json()["theo_goi_y"] is True


# ---------------------------------------------------------------- Khuyến nghị bán xe
def test_gia_chao_thap_hon_dinh_gia_qua_nguong_thi_co_vang_va_neu_so_nam_loi_nhuan():
    """Để người quyết thấy mình đang đánh đổi bao nhiêu năm khai thác lấy một khoản tiền ngay."""
    v = ds_xe()[1]["id"]
    r = client.post("/api/v1/fleet/khuyen-nghi-ban-xe", headers=login("chutich"),
                    json={"vehicle_id": v, "gia_chao": 700_000_000, "dinh_gia_noi_bo": 1_000_000_000}).json()
    assert r["co"] == "vang"
    assert any("thấp hơn định giá nội bộ" in l for l in r["ly_do"])
    assert "so_nam_loi_nhuan_tuong_duong" in r


def test_chua_co_dinh_gia_noi_bo_thi_khong_ket_luan_gia_tot():
    r = client.post("/api/v1/fleet/khuyen-nghi-ban-xe", headers=login("chutich"),
                    json={"vehicle_id": ds_xe()[0]["id"], "gia_chao": 100_000_000}).json()
    assert r["co"] == "vang"
    assert any("Chưa có định giá nội bộ" in l for l in r["ly_do"])


# ---------------------------------------------------------------- Bản tin sáng và nâng mức cảnh báo
def test_ban_tin_sang_dat_canh_bao_do_len_dau_va_khong_goi_xe_thieu_ho_so_la_san_sang():
    bt = client.get("/api/v1/fleet/ban-tin-sang", headers=login("chutich")).json()
    assert "canh_bao_do" in bt and "xe_chay_hom_nay" in bt and "xe_ranh" in bt
    assert "KHÔNG phải là xe sẵn sàng chạy" in bt["ghi_chu"]
    for x in bt["xe_ranh"]:
        assert x["muc"] in ("OK", "UNKNOWN", "REVIEW", "APPROVAL_REQUIRED", "BLOCK")


def test_chi_nang_muc_canh_bao_da_co_nguoi_nhan():
    """Đặc tả có hai câu tưởng như trái nhau: "cảnh báo lặp quá 3 ngày tự nâng mức" và "không nâng mọi cảnh
    báo chỉ vì đã tồn tại ba ngày". Dung hòa: chỉ nâng cảnh báo có người nhận cụ thể. Nâng tất cả thì sau một
    tuần cả bảng đỏ rực và không ai đọc nữa."""
    from app.db.session import SessionLocal
    from app.models.core import Alert
    from datetime import datetime, timedelta as td
    cu = datetime.now() - td(days=5)
    db = SessionLocal()
    try:
        db.add(Alert(kind="kt_co_nguoi", level="warn", ref="xe:A", message="Có người nhận",
                     to_roles="tp_dh", created_at=cu))
        db.add(Alert(kind="kt_khong_nguoi", level="warn", ref="xe:B", message="Chưa gắn người nhận",
                     to_roles="", created_at=cu))
        db.commit()
    finally:
        db.close()
    kq = client.post("/api/v1/fleet/nang-muc-canh-bao", headers=login("cntt")).json()
    assert any(x["kind"] == "kt_co_nguoi" for x in kq["da_nang"])
    assert any(x["kind"] == "kt_khong_nguoi" for x in kq["bo_qua"])
    assert "chưa gắn người nhận" in next(x["ly_do"] for x in kq["bo_qua"] if x["kind"] == "kt_khong_nguoi")


def test_nhat_ky_tu_dong_ghi_ma_bam_du_lieu_dau_vao():
    """Không có nhật ký này thì không kiểm toán được phần mềm đã tự làm những gì."""
    d1 = HOM_NAY + timedelta(days=550)
    client.get(f"/api/v1/fleet/goi-y-dieu-xe?date_from={d1}&date_to={d1}", headers=login("tp.dieuhanh"))
    nk = client.get("/api/v1/fleet/nhat-ky-tu-dong?agent=A1", headers=login("chutich")).json()
    assert nk, "phải ghi lại lần chạy"
    assert nk[0]["dau_vao_hash"] and nk[0]["rule_version"]
    assert nk[0]["chay_boi"] == "tp.dieuhanh"


def test_ky_sai_dinh_dang_bi_tu_choi():
    assert client.get("/api/v1/fleet/hieu-qua?ky=2026", headers=login("chutich")).status_code == 422
