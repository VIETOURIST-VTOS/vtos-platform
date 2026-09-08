"""Lệnh Robot Kiểm soát 08/9/2026 – K1, K2, K6.

Ba việc này viết TRƯỚC khi ai sửa mã, để đo được sửa tới đâu. Vì vậy hai phép thử đầu CỐ Ý còn ĐỎ
theo nghĩa nghiệp vụ: chúng khẳng định robot vẫn đang thấy 117 cột tiền sai kiểu. Cái phải xanh là
BỘ KIỂM chạy đúng và đếm đúng, không phải hệ thống đã sạch.

  KT1  K1 liệt kê từng cột tiền kiểu Float kèm tên bảng và tên cột
  KT2  cột rõ ràng không phải tiền (tỷ lệ, điểm, ngày, lít) không bị xếp nhầm vào tiền
  KT3  tên cột không nói rõ thì để "chưa rõ" chờ NGƯỜI QUYẾT, robot không tự xếp
  KT4  robot (bks) không được quyết xếp loại – nó đề xuất, người chốt
  KT5  người quyết rồi thì lần quét sau lấy quyết định của người, không lấy đề xuất của máy
  KT6  K2 chỉ tính cột tiền mặc định 0 và không cho rỗng; "giữ" phải kèm lý do
  KT7  K6 gây lỗi 500 có chủ đích thì robot phát hiện trong vòng quét kế tiếp
  KT8  sự kiện gom theo mã ổn định – một đường dẫn hỏng nhiều lần là MỘT dòng
  KT9  bảng sự kiện không chứa dữ liệu nghiệp vụ (không ghi tham số truy vấn)
  KT10 lỗi khi GHI nhật ký không được làm hỏng yêu cầu đang chạy
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_kscot.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_kscot.db"): os.remove("test_kscot.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app


@app.get("/api/v1/_thu_loi_500", include_in_schema=False)
def _thu_loi_500(bi_mat: str = ""):
    """Đường dẫn chỉ tồn tại trong tiến trình chạy thử, để dựng đúng tình huống nghiệm thu của K6."""
    raise RuntimeError("lỗi cố ý để thử bộ theo dõi")


client = TestClient(app, raise_server_exceptions=False); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app, raise_server_exceptions=False) as c:
        global client; client = c; yield


def so(loc=""):
    return client.get("/api/v1/kiem-soat/cot-tien" + (f"?loc={loc}" if loc else ""), headers=login("cntt")).json()


def test_kt1_liet_ke_tung_cot_tien_kieu_float_kem_ten_bang_va_cot():
    d = so("can_doi_kieu")
    assert d["tong_cot"] > 100, "phải quét được toàn bộ mô hình dữ liệu, không chỉ vài bảng"
    assert d["so_float_tien"] > 0, "còn cột tiền kiểu Float thì bộ kiểm phải nói ra"
    for r in d["rows"][:5]:
        assert r["bang"] and r["cot"] and r["kieu"] == "Float"
    # và phải chỉ đúng những chỗ nguy hiểm nhất: doanh thu, giá vốn, bút toán, lương
    ten = {f"{r['bang']}.{r['cot']}" for r in d["rows"]}
    for x in ("tours.actual_revenue", "journal_lines.debit", "journal_lines.credit"):
        assert x in ten, f"{x} là tiền mà bộ kiểm không thấy"


def test_kt2_cot_ro_rang_khong_phai_tien_thi_khong_bi_xep_nham():
    d = so()
    xep = {f"{r['bang']}.{r['cot']}": r["xep"] for r in d["rows"]}
    for x in ("companies.ownership_pct", "fin_contracts.interest_rate", "invoices.vat_rate",
              "ks_diem.diem", "leave_requests.days", "fleet_trip_costs.lit",
              "tour_cost_lines.qty", "visa_cases.fee_weight", "quy_tac_hach_toan.ty_le_thue"):
        assert xep.get(x) == "khong_tien", f"{x} không phải tiền mà bị xếp là {xep.get(x)}"
    assert d["so_khong_tien"] >= 20


def test_kt3_ten_cot_khong_noi_ro_thi_de_chua_ro_cho_nguoi_quyet():
    d = so("chua_ro")
    assert d["so_chua_ro"] > 0, "một bộ kiểm tự tin xếp loại đúng 100% cột chỉ bằng tên là bộ kiểm đang đoán"
    ten = {f"{r['bang']}.{r['cot']}" for r in d["rows"]}
    # đơn giá thuê theo ngày: chữ "rate" vừa là lãi suất vừa là đơn giá – một chữ không đủ để phân biệt
    assert "guide_rates.rate_per_day" in ten
    for r in d["rows"]:
        assert r["quyet_nguoi"] == "" and "cần người quyết" in r["ly_do_may"]


def test_kt4_robot_khong_duoc_quyet_xep_loai():
    d = so("chua_ro"); i = d["rows"][0]["id"]
    than = {"dong": [{"id": i, "quyet_nguoi": "tien"}]}
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet", json=than, headers=login("bks")).status_code == 403, \
        "robot vừa xếp loại vừa chốt xếp loại thì con số nó báo lên Chủ tịch là con số nó tự đặt ra"
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet", json=than, headers=login("ketoan")).status_code == 200


def test_kt5_quyet_cua_nguoi_de_len_de_xuat_cua_may():
    truoc = so()
    d = so("chua_ro")
    assert d["rows"], "phép thử trước đã quyết hết rồi thì phép thử này vô nghĩa"
    i = d["rows"][0]["id"]
    r = client.post("/api/v1/kiem-soat/cot-tien/quyet",
                    json={"dong": [{"id": i, "quyet_nguoi": "tien", "ghi_chu": "đơn giá theo ngày, là tiền"}]},
                    headers=login("ketoan"))
    assert r.status_code == 200 and r.json()["da_xep_loai"] == 1
    sau = so()
    assert sau["so_chua_ro"] == truoc["so_chua_ro"] - 1
    assert sau["so_tien"] == truoc["so_tien"] + 1
    assert sau["so_nguoi_da_quyet"] >= 1
    # "chưa rõ" là trạng thái CHỜ, không phải một quyết định
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet",
                       json={"dong": [{"id": i, "quyet_nguoi": "chua_ro"}]},
                       headers=login("ketoan")).status_code == 422


def test_kt6_thieu_khac_0_chi_tinh_cot_tien_va_giu_thi_phai_co_ly_do():
    d = so("thieu_thanh_0")
    assert d["so_thieu_thanh_0"] > 0
    for r in d["rows"]:
        assert r["xep"] == "tien" and r["mac_dinh_0"] and not r["cho_rong"]
    i = d["rows"][0]["id"]
    # giữ nguyên mà không nói vì sao thì lần rà sau không ai biết đã cân nhắc chưa
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet", json={"dong": [{"id": i, "quyet_k2": "giu"}]},
                       headers=login("ketoan")).status_code == 422
    r = client.post("/api/v1/kiem-soat/cot-tien/quyet",
                    json={"dong": [{"id": i, "quyet_k2": "giu", "ghi_chu": "0 ở cột này là chiết khấu bằng 0, là số thật"}]},
                    headers=login("ketoan"))
    assert r.status_code == 200
    assert so("thieu_thanh_0")["so_thieu_thanh_0"] == d["so_thieu_thanh_0"] - 1


def test_kt7_gay_loi_500_thi_robot_phat_hien_trong_vong_quet_ke_tiep():
    assert client.get("/api/v1/_thu_loi_500").status_code == 500
    r = client.post("/api/v1/kiem-soat/quet", headers=login("cntt"))
    assert r.status_code == 200 and not r.json()["loi_bo_kiem"]
    ds = client.get("/api/v1/kiem-soat", headers=login("cntt")).json()
    ma = {p["ma"] for p in ds["phat_hien"] if p["con"]}
    assert any(m.startswith("may_chu_loi#5xx") for m in ma), \
        f"robot vẫn mù với lỗi máy chủ. Các mã đang có: {sorted(ma)}"


def test_kt8_su_kien_gom_theo_ma_on_dinh_khong_nhan_ban():
    for _ in range(3): client.get("/api/v1/_thu_loi_500")
    d = client.get("/api/v1/kiem-soat/su-kien-ky-thuat", headers=login("cntt")).json()
    loi = [r for r in d["rows"] if r["loai"] == "loi_5xx" and "_thu_loi_500" in r["duong_dan"]]
    assert len(loi) == 1, "một đường dẫn hỏng nhiều lần phải là MỘT dòng, không phải nhiều dòng giống hệt"
    assert loi[0]["so_lan"] >= 4 and loi[0]["ma_trang_thai"] == 500


def test_kt9_bang_su_kien_khong_chua_du_lieu_nghiep_vu():
    client.get("/api/v1/_thu_loi_500?bi_mat=0987133383")
    d = client.get("/api/v1/kiem-soat/su-kien-ky-thuat", headers=login("cntt")).json()
    tat_ca = str(d)
    assert "0987133383" not in tat_ca and "bi_mat" not in tat_ca, \
        "bảng này có quyền xem rộng hơn nhiều bảng nó theo dõi – không bao giờ được chứa dữ liệu nghiệp vụ"


def test_kt10_loi_khi_ghi_nhat_ky_khong_lam_hong_yeu_cau():
    from app.services import ky_thuat as KT
    goc = KT.ghi
    KT.ghi = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("cơ sở dữ liệu nhật ký hỏng"))
    try:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/_thu_loi_500").status_code == 500
    finally:
        KT.ghi = goc


def test_kt11_ba_bo_kiem_moi_da_gan_vao_vong_quet():
    from app.services import ks_robot as KS
    ten = {f.__name__ for f in KS.BO_KIEM}
    for x in ("_cot_tien_float", "_thieu_khac_khong", "_su_kien_ky_thuat"):
        assert x in ten, f"{x} viết xong mà không gắn vào vòng quét thì không ai chạy nó"
