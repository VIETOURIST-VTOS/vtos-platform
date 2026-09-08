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
    # Và phải chỉ đúng những chỗ nguy hiểm nhất – nhưng CHỈ những chỗ V9 CHƯA sửa.
    #
    # Bản đầu ghi cứng journal_lines.debit/credit làm ví dụ. V9 đợt 1 đổi đúng hai cột đó sang số
    # thập phân, và phép thử lập tức đỏ – tức là nó biến VIỆC SỬA THÀNH LỖI. Cách nhanh nhất để làm
    # xanh một phép thử như vậy là hoàn tác V9, và đó chính là điều không được để xảy ra.
    #
    # Nay danh sách ví dụ lấy từ mô hình HIỆN TẠI: cột nào còn là Float thì bộ kiểm phải thấy. Danh
    # sách tự ngắn lại theo từng đợt V9, và tới đợt cuối thì so_float_tien về 0 – lúc đó nhánh dưới
    # tự bỏ qua, không cần ai nhớ sửa phép thử này lần nữa.
    from app.db.session import Base
    from sqlalchemy import Float
    from app.services.ks_cot_tien import xep_theo_ten
    ten = {f"{r['bang']}.{r['cot']}" for r in d["rows"]}
    con_float_la_tien = {f"{t.name}.{c.name}" for t in Base.metadata.tables.values() for c in t.columns
                         if isinstance(c.type, Float) and xep_theo_ten(c.name)[0] == "tien"}
    thieu = con_float_la_tien - ten
    assert not thieu, f"cột tiền còn kiểu Float mà bộ kiểm không thấy: {sorted(thieu)[:5]}"


def test_kt2_cot_ro_rang_khong_phai_tien_thi_khong_bi_xep_nham():
    d = so()
    xep = {f"{r['bang']}.{r['cot']}": r["xep"] for r in d["rows"]}
    for x in ("companies.ownership_pct", "fin_contracts.interest_rate", "invoices.vat_rate",
              "ks_diem.diem", "leave_requests.days", "fleet_trip_costs.lit",
              "tour_cost_lines.qty", "visa_cases.fee_weight", "quy_tac_hach_toan.ty_le_thue"):
        assert xep.get(x) == "khong_tien", f"{x} không phải tiền mà bị xếp là {xep.get(x)}"
    assert d["so_khong_tien"] >= 20


def test_kt3_ten_cot_khong_noi_ro_thi_de_chua_ro_cho_nguoi_quyet():
    """Robot ĐỀ XUẤT theo tên và dừng lại ở chỗ tên không nói đủ.

    Tám cột này nay đã có người quyết (Chủ tịch, 08/9), nên phép thử soi vào ĐỀ XUẤT CỦA MÁY chứ không
    soi số dòng đang chờ: điều phải giữ là robot không tự tin xếp loại thứ nó không phân biệt được.
    """
    from app.services.ks_cot_tien import xep_theo_ten
    for cot in ("rate_per_day", "old_rate_per_day", "internal_rate_per_day", "moi_ky",
                "doi_tac_huong", "doi_tac_chiu", "chuyen_ky_sau"):
        xep, ly_do = xep_theo_ten(cot)
        assert xep == "chua_ro" and "cần người quyết" in ly_do, f"{cot} bị máy tự xếp thành {xep}"
    # và trong sổ, đề xuất của máy vẫn ghi "chưa rõ" kể cả sau khi người đã quyết – giữ được cả hai
    # cột thì sau này còn đo được máy đoán đúng bao nhiêu phần trăm
    d = so()
    con = {f"{r['bang']}.{r['cot']}": r for r in d["rows"]}
    x = con["guide_rates.rate_per_day"]
    assert x["xep_may"] == "chua_ro" and x["xep"] == "tien" and x["quyet_nguoi"] == "tien"


def test_kt4_robot_khong_duoc_quyet_xep_loai():
    d = so("can_doi_kieu"); i = d["rows"][0]["id"]
    than = {"dong": [{"id": i, "quyet_nguoi": "tien"}]}
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet", json=than, headers=login("bks")).status_code == 403, \
        "robot vừa xếp loại vừa chốt xếp loại thì con số nó báo lên Chủ tịch là con số nó tự đặt ra"
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet", json=than, headers=login("ketoan")).status_code == 200


def test_kt5_quyet_cua_nguoi_de_len_de_xuat_cua_may():
    truoc = so()
    # lấy một cột máy xếp là tiền rồi cho người đổi thành không phải tiền: quyết định của người thắng
    d = so("can_doi_kieu")
    chua = [r for r in d["rows"] if not r["quyet_nguoi"]]
    assert chua, "không còn cột nào chưa ai quyết thì phép thử này không nói lên điều gì"
    i = chua[0]["id"]; ten = f"{chua[0]['bang']}.{chua[0]['cot']}"
    r = client.post("/api/v1/kiem-soat/cot-tien/quyet",
                    json={"dong": [{"id": i, "quyet_nguoi": "khong_tien", "ghi_chu": "thử: người quyết khác máy"}]},
                    headers=login("ketoan"))
    assert r.status_code == 200 and r.json()["da_xep_loai"] == 1
    sau = so()
    assert sau["so_tien"] == truoc["so_tien"] - 1 and sau["so_khong_tien"] == truoc["so_khong_tien"] + 1
    assert sau["so_nguoi_da_quyet"] > truoc["so_nguoi_da_quyet"]
    con = {f"{x['bang']}.{x['cot']}": x for x in sau["rows"]}
    assert con[ten]["xep_may"] == "tien" and con[ten]["xep"] == "khong_tien"
    # "chưa rõ" là trạng thái CHỜ, không phải một quyết định
    assert client.post("/api/v1/kiem-soat/cot-tien/quyet",
                       json={"dong": [{"id": i, "quyet_nguoi": "chua_ro"}]},
                       headers=login("ketoan")).status_code == 422
    # trả lại như cũ để phép thử sau không lệch
    client.post("/api/v1/kiem-soat/cot-tien/quyet",
                json={"dong": [{"id": i, "quyet_nguoi": "tien", "ghi_chu": ""}]}, headers=login("ketoan"))


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


def test_kt12_quyet_dinh_08_09_da_duoc_ghi_va_khong_de_len_nguoi_khac():
    """Chủ tịch quyết ngày 08/9: tám cột “chưa rõ” là tiền, và toàn bộ cột tiền mặc định 0 thì SỬA.

    Hai điều phải đúng cùng lúc: quyết định có mặt sau mỗi lần triển khai, và hàm nạp KHÔNG bao giờ
    ghi đè lên quyết định người khác ghi sau đó – nạp mặc định mà đè quyết định của người là xoá dấu vết.
    """
    from app.services import ks_cot_tien as CT
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        CT.nap_quyet_dinh(db)
        d = CT.bang(db)
        con = {f"{r['bang']}.{r['cot']}": r for r in d["rows"]}
        for ten in CT.QUYET_08_09_2026:
            assert con[ten]["xep"] == "tien" and con[ten]["quyet_nguoi"] == "tien", ten
        # Tám cột của ngày 08/9 phải hết chờ. Nhưng KHÔNG đòi tổng số chờ bằng 0: mô hình còn lớn
        # lên, và mỗi cột tiền thêm vào sau đó phải VÀO HÀNG CHỜ chứ không được quyết hộ – đúng điều
        # chính phép thử này khẳng định ở đoạn dưới. Đòi tổng bằng 0 là vô tình biến "chưa ai quyết"
        # thành lỗi, và cách nhanh nhất để sửa một lỗi như vậy là quyết bừa cho hết danh sách.
        cho = {f"{r['bang']}.{r['cot']}" for r in d["rows"] if r["xep"] == "chua_ro"}
        assert not (cho & set(CT.QUYET_08_09_2026)), \
            f"cột đã có quyết định 08/9 mà vẫn nằm trong hàng chờ: {cho & set(CT.QUYET_08_09_2026)}"
        # Quyết "sửa" KHÔNG làm cột biến mất: nó vẫn hỏng cho tới khi mô hình đổi thật. Thứ đo tiến độ
        # của NGƯỜI là số cột chưa ai quyết.
        assert d["so_thieu_thanh_0"] > 0, "chưa ai đổi kiểu thì danh sách phải còn nguyên"
        # Cột thêm vào mô hình SAU ngày 08/9 thì KHÔNG bị quyết hộ – đây mới là điều phải giữ. Nếu
        # danh sách viết thành quy tắc thay vì liệt kê từng cột, mọi cột mới sẽ tự động mang chữ ký
        # của Chủ tịch mà ông chưa từng nhìn thấy chúng.
        moi = [f"{r['bang']}.{r['cot']}" for r in d["rows"]
               if r["thieu_thanh_0"] and f"{r['bang']}.{r['cot']}" not in CT.QUYET_K2_SUA_08_09_2026]
        assert d["so_k2_chua_quyet"] == len(moi), \
            f"cột chưa quyết phải đúng bằng số cột thêm sau ngày quyết. Đang chờ: {moi}"
        # ghi đè: đổi một cột sang "giữ" rồi nạp lại, quyết định của người phải còn nguyên
        from app.models.ra_soat_tien import KsCotTien
        from sqlalchemy import select
        r = db.execute(select(KsCotTien).where(KsCotTien.bang == "tours",
                                               KsCotTien.cot == "actual_revenue")).scalars().first()
        r.quyet_k2, r.quyet_k2_boi, r.ghi_chu = "giu", "ketoan", "thử ghi đè"
        db.commit()
        CT.nap_quyet_dinh(db); db.refresh(r)
        assert r.quyet_k2 == "giu" and r.quyet_k2_boi == "ketoan"
        r.quyet_k2, r.quyet_k2_boi = "sua", "chutich"; db.commit()
    finally:
        db.close()
