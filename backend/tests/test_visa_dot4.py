"""Visa Đợt 4 – tài chính, báo cáo, chuyển dữ liệu từ Visa Portal.

Trọng tâm là tiêu chí nghiệm thu 14: "Số thu–chi trên Visa khớp phân hệ tài chính". Phép chia tiền cho nhiều
người luôn để lại phần dư; nếu mỗi chỗ làm tròn một kiểu thì tổng sẽ lệch vài đồng, và kế toán sẽ mất buổi
sáng đi tìm. Ở đây phần dư có quy tắc cố định và được kiểm bằng số lẻ cố tình chọn cho khó chia.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_visa_dot4.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_visa_dot4.db"): os.remove("test_visa_dot4.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
DEP = str(date.today() + timedelta(days=60))


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def make_booking(amount: float, cost: float, pax: int = 3) -> int:
    """Booking dịch vụ lẻ loại VISA – đúng cách VTOS ghi nhận visa lẻ."""
    r = client.post("/api/v1/non-package", headers=login("dh.lan"),
                    json={"service_type": "VISA", "description": "Visa UK gia đình (kiểm thử)",
                          "customer_name": "Gia đình kiểm thử", "customer_phone": "0900000000",
                          "pax": pax, "amount": amount, "cost_amount": cost, "country": "UK",
                          "source": "Khách quen"})
    assert r.status_code in (200, 201), r.text
    d = r.json()
    row = d.get("row") or d
    return row["id"]


def new_case(name, booking_id=None, **kw):
    body = {"applicant_name": name, "market_code": "UK", "departure_date": DEP, "on_duplicate": "independent",
            "note": "kiểm thử"}
    if booking_id:
        body["booking_id"] = booking_id
    body.update(kw)
    r = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"), json=body)
    assert r.status_code == 201, r.text
    return r.json()["case"]["id"]


# ---------- Phân bổ phí ----------

def test_nghiem_thu_14_tong_phan_bo_khop_tuyet_doi():
    """Số cố tình chọn cho khó chia: 10.000.000 chia 3 người. Tổng phân bổ phải bằng ĐÚNG số của booking."""
    bid = make_booking(10_000_000, 6_000_000, pax=3)
    ids = [new_case(f"Chia Deu {i}", bid) for i in range(3)]
    r = client.get(f"/api/v1/visa/doi-chieu-phan-bo/{bid}", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_ho_so"] == 3 and d["doanh_thu_booking"] == 10_000_000
    assert d["tong_phan_bo"] == 10_000_000 and d["lech"] == 0 and d["khop"] is True
    phan = sorted(x["phan_bo"] for x in d["chi_tiet"])
    assert phan == [3_333_333, 3_333_333, 3_333_334]      # phần dư dồn vào một hồ sơ, không rơi vãi

    # Số của từng hồ sơ đọc qua API cũng phải là số đã chia, và cộng lại vẫn khớp
    tong = 0
    for cid in ids:
        f = client.get(f"/api/v1/visa/ho-so/{cid}/thu-chi", headers=login("ketoan")).json()
        assert f["co_booking"] is True
        assert f["cua_booking"]["doanh_thu"] == 10_000_000
        tong += f["phan_bo_cho_ho_so_nay"]["doanh_thu"]
    assert tong == 10_000_000


def test_trong_so_khong_deu_va_ho_so_huy_khong_ganh_phi():
    """Người lớn 1, trẻ em 0,5. Hồ sơ đã hủy KHÔNG gánh phí – phí dồn về người còn lại."""
    bid = make_booking(9_000_000, 0, pax=3)
    a = new_case("Nguoi Lon A", bid)
    b = new_case("Nguoi Lon B", bid)
    c = new_case("Tre Em C", bid)
    assert client.post(f"/api/v1/visa/ho-so/{c}/trong-so-phi", headers=login("ketoan"),
                       json={"fee_weight": 0.5}).status_code == 200
    # Điều hành thấy hồ sơ nhưng không được đặt trọng số phân bổ tiền
    assert client.post(f"/api/v1/visa/ho-so/{c}/trong-so-phi", headers=login("dh.lan"),
                       json={"fee_weight": 2}).status_code in (403, 422)
    d = client.get(f"/api/v1/visa/doi-chieu-phan-bo/{bid}", headers=login("ketoan")).json()
    assert d["khop"] is True and d["tong_phan_bo"] == 9_000_000
    chia = {x["case_id"]: x["phan_bo"] for x in d["chi_tiet"]}
    assert chia[b] == 3_600_000 and chia[c] == 1_800_000 and chia[a] == 3_600_000   # 1 : 1 : 0,5

    client.post(f"/api/v1/visa/ho-so/{c}/huy", headers=login("tp.dieuhanh"), json={"reason": "Khách bỏ chuyến"})
    d2 = client.get(f"/api/v1/visa/doi-chieu-phan-bo/{bid}", headers=login("ketoan")).json()
    assert d2["so_ho_so"] == 2 and d2["khop"] is True
    chia2 = {x["case_id"]: x["phan_bo"] for x in d2["chi_tiet"]}
    assert chia2[a] == 4_500_000 and chia2[b] == 4_500_000 and c not in chia2


def test_visa_khong_co_so_thu_chi_rieng():
    """Số đọc ra phải khớp phân hệ tài chính, và phiếu thu hiện đúng như phân hệ Thu tiền ghi."""
    bid = make_booking(5_000_000, 2_000_000, pax=1)
    cid = new_case("Mot Minh", bid)
    f = client.get(f"/api/v1/visa/ho-so/{cid}/thu-chi", headers=login("ketoan")).json()
    assert f["cua_booking"]["doanh_thu"] == 5_000_000
    assert f["cua_booking"]["gia_von_ncc"] == 2_000_000
    assert f["cua_booking"]["da_thu"] == 0 and f["cua_booking"]["con_phai_thu"] == 5_000_000
    assert f["phan_bo_cho_ho_so_nay"]["lai_lo_du_kien"] == 3_000_000
    assert f["phieu_thu"] == []                       # chưa thu đồng nào thì không được tự bịa ra phiếu


def test_ho_so_chua_gan_booking_thi_noi_ro_chu_khong_bao_loi():
    cid = new_case("Chua Gan Booking")
    f = client.get(f"/api/v1/visa/ho-so/{cid}/thu-chi", headers=login("ketoan")).json()
    assert f["co_booking"] is False and "chưa gắn booking" in f["ghi_chu"]


def test_kinh_doanh_khong_xem_duoc_gia_von():
    """Ma trận quyền sẵn có của VTOS: Kinh doanh không xem cơ cấu giá vốn."""
    bid = make_booking(4_000_000, 3_000_000, pax=1)
    cid = new_case("Phan Quyen Tien", bid, sales_user_id=None)
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                json={"sales_user_id": next(x["id"] for x in client.get("/api/v1/users", headers=login("chutich")).json()
                                            if x["username"] == "kd.hoa")})
    r = client.get(f"/api/v1/visa/ho-so/{cid}/thu-chi", headers=login("kd.hoa"))
    assert r.status_code == 403                        # thấy hồ sơ (là sales phụ trách) nhưng không thấy tiền
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("kd.hoa")).status_code == 200


# ---------- Báo cáo ----------

def test_bao_cao_dem_theo_ho_so_va_ty_le_dau_tren_so_da_co_ket_qua():
    r = client.get("/api/v1/visa/bao-cao", headers=login("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tong_ho_so"] >= 1 and "UK" in d["theo_thi_truong"]
    uk = d["theo_thi_truong"]["UK"]
    assert uk["tong"] == uk["duoc_cap"] + uk["tu_choi"] + uk["dang_xu_ly"] + uk["huy"]
    assert uk["ty_le_duoc_cap"] is None or 0 <= uk["ty_le_duoc_cap"] <= 100
    assert "theo_chuyen_vien" in d and "theo_giai_doan" in d
    assert "tien" in d and d["tien"]["doanh_thu"] > 0      # Chủ tịch xem được tiền
    # Kinh doanh xem được báo cáo nhưng KHÔNG có phần tiền
    d2 = client.get("/api/v1/visa/bao-cao", headers=login("kd.hoa")).json()
    assert "tien" not in d2


def test_bao_cao_khong_cong_trung_booking_dung_chung():
    """Bốn hồ sơ chung một booking thì doanh thu chỉ tính MỘT lần, không nhân bốn."""
    truoc = client.get("/api/v1/visa/bao-cao", headers=login("chutich")).json()["tien"]["doanh_thu"]
    bid = make_booking(8_000_000, 0, pax=4)
    for i in range(4):
        new_case(f"Chung Booking {i}", bid)
    sau = client.get("/api/v1/visa/bao-cao", headers=login("chutich")).json()["tien"]["doanh_thu"]
    assert sau - truoc == 8_000_000       # không phải 32.000.000


# ---------- Chuyển dữ liệu từ Visa Portal ----------

CSV = (b"ma_ho_so,ho_ten,ngay_sinh,thi_truong,ngay_di,ghi_chu,test\n"
       b"VP-001,Nguyen Van Portal,1990-01-01,UK,2026-12-01,ho so cu,\n"
       b"VP-002,Tran Thi Portal,1992-02-02,UK,2026-12-05,,\n"
       b"VP-003,,1993-03-03,UK,2026-12-10,thieu ten,\n"
       b"VP-004,Le Van Test,1994-04-04,UK,2026-12-15,du lieu thu,1\n")


def _nap(apply: bool):
    return client.post(f"/api/v1/visa/nap-visa-portal?apply={'true' if apply else 'false'}",
                       headers=login("chutich"),
                       files={"file": ("portal.csv", CSV, "text/csv")})


def test_nap_portal_xem_truoc_khong_ghi_gi():
    truoc = client.get("/api/v1/visa/ho-so?include_test=true", headers=login("chutich")).json()["total"]
    r = _nap(False)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["che_do"] == "xem_truoc" and d["tao_moi"] == 3 and d["loi"] == 1
    assert d["chi_tiet"]["loi"][0]["ma_nguon"] == "VP-003"
    sau = client.get("/api/v1/visa/ho-so?include_test=true", headers=login("chutich")).json()["total"]
    assert sau == truoc                       # xem trước tuyệt đối không ghi gì vào cơ sở dữ liệu


def test_nap_portal_thuc_hien_va_nap_lai_khong_sinh_trung():
    d = _nap(True).json()
    assert d["che_do"] == "thuc_hien" and d["tao_moi"] == 3
    assert d["danh_dau_thu_nghiem"] == 1       # chỉ dòng CÓ ghi test mới là thử nghiệm, không suy cả lô
    # Nạp lại đúng tệp đó: nhận ra đã có, không tạo thêm bản ghi nào
    d2 = _nap(True).json()
    assert d2["tao_moi"] == 0 and d2["da_co_tu_truoc"] == 3
    # Hồ sơ nhập về giữ mã nguồn để truy vết
    ds = client.get("/api/v1/visa/ho-so?q=Portal&include_test=true", headers=login("chutich")).json()
    assert ds["total"] >= 2


def test_doi_chieu_sau_chuyen_doi():
    r = client.get("/api/v1/visa/doi-chieu-chuyen-doi", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tu_visa_portal"] == 3
    assert len(d["chua_gan_booking"]) == 3      # hồ sơ lịch sử chưa có booking – phải rà tay, không tự đoán
    assert d["thieu_ma_nguon"] == []


def test_chi_lanh_dao_moi_duoc_nap_du_lieu():
    r = client.post("/api/v1/visa/nap-visa-portal", headers=login("dh.lan"),
                    files={"file": ("portal.csv", CSV, "text/csv")})
    assert r.status_code == 403


# ---------- Vai trò Chuyên viên Visa (nv_visa) ----------

def _tao_nv_visa():
    """Vai trò nv_visa do phân hệ Nhân sự sinh ra từ bảng lương; ở đây tạo thẳng một tài khoản để kiểm quyền."""
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        if not db.execute(sel(User).where(User.username == "visa.chuyenvien")).scalars().first():
            db.add(User(username="visa.chuyenvien", full_name="Chuyên viên Visa (kiểm thử)",
                        role="nv_visa", department="Visa", password_hash=hash_password("Vtos@Demo#2026")))
            db.commit()
        return db.execute(sel(User).where(User.username == "visa.chuyenvien")).scalars().first().id
    finally:
        db.close()


def test_chuyen_vien_visa_dung_duoc_phan_he_cua_chinh_minh():
    """Phân hệ xây cho họ thì họ phải vào được. Bỏ sót tên vai trò ở lớp API là họ nhận 403 ở đúng menu duy nhất."""
    uid = _tao_nv_visa()
    h = login("visa.chuyenvien")
    assert client.get("/api/v1/visa/danh-muc", headers=h).status_code == 200
    assert client.get("/api/v1/visa/ho-so", headers=h).status_code == 200
    assert client.get("/api/v1/visa/tong-quan", headers=h).status_code == 200

    # Chỉ thấy hồ sơ ĐƯỢC GIAO, không thấy hồ sơ của người khác
    cid = new_case("Ho So Giao Chuyen Vien")
    assert client.get("/api/v1/visa/ho-so", headers=h).json()["total"] == 0
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=h).status_code == 403
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                json={"visa_owner_user_id": uid})
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=h).status_code == 200
    assert client.get("/api/v1/visa/ho-so", headers=h).json()["total"] == 1


def test_chuyen_vien_visa_lam_duoc_viec_nghiep_vu_nhung_khong_dung_vao_tien():
    """Duyệt tài liệu hồ sơ mình thì được; đụng vào phân bổ tiền hay nạp dữ liệu hàng loạt thì không."""
    uid = _tao_nv_visa()
    h = login("visa.chuyenvien")
    bid = make_booking(3_000_000, 1_000_000, pax=1)
    cid = new_case("Nghiep Vu Chuyen Vien", bid)
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                json={"visa_owner_user_id": uid})
    # Khai form, gửi, khách xác nhận – việc thường ngày của chuyên viên
    fv = client.post(f"/api/v1/visa/ho-so/{cid}/form", headers=h,
                     json={"data": {"ho_ten": "X", "so_ho_chieu": "C9999999"}}).json()
    assert client.post(f"/api/v1/visa/ho-so/{cid}/form/{fv['id']}/gui-khach", headers=h).status_code == 200
    assert client.post(f"/api/v1/visa/ho-so/{cid}/xac-nhan-form", headers=h,
                       json={"form_version_id": fv["id"], "confirmed_by_name": "Khách"}).status_code == 201
    # Nộp và duyệt tài liệu
    item = client.get(f"/api/v1/visa/ho-so/{cid}", headers=h).json()["checklist"][0]
    up = client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu", headers=h,
                     files={"file": ("hc.pdf", b"noi dung", "application/pdf")},
                     data={"checklist_item_id": str(item["id"])})
    assert up.status_code == 201
    assert client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{up.json()['id']}/kiem-tra", headers=h,
                       json={"decision": "ACCEPTED"}).status_code == 201

    # Nhưng KHÔNG đụng được vào tiền và KHÔNG nạp dữ liệu hàng loạt
    assert client.get(f"/api/v1/visa/ho-so/{cid}/thu-chi", headers=h).status_code == 403
    assert client.post(f"/api/v1/visa/ho-so/{cid}/trong-so-phi", headers=h,
                       json={"fee_weight": 2}).status_code == 403
    assert client.post("/api/v1/visa/nap-visa-portal", headers=h,
                       files={"file": ("p.csv", CSV, "text/csv")}).status_code == 403
    # Và không hủy được hồ sơ – hủy là quyền của trưởng bộ phận
    assert client.post(f"/api/v1/visa/ho-so/{cid}/huy", headers=h,
                       json={"reason": "thử"}).status_code == 422
