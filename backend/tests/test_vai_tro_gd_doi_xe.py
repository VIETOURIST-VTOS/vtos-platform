"""Vai trò Giám đốc điều hành đội xe (mở 07/9/2026).

Lý do vai trò này tồn tại là một thế bí có thật trên hệ thống đang chạy: tài khoản GĐ Nguyễn Hồng Huấn mang
chung vai trò "Tài xế & Hướng dẫn viên" với 11 tài xế, mà vai trò đó bị khóa vào đúng một màn hình. Trong khi
đó tham số `xe_nguoi_lap_lenh` chỉ định ông là người DUY NHẤT được lập lệnh điều xe. Hệ quả: người có quyền
theo chỉ đạo thì không vào được cửa, người vào được cửa thì không có quyền theo chỉ đạo – KHÔNG AI lập được
lệnh điều xe.

Bộ phép thử này giữ hai vế của vai trò mới, và vế thứ hai quan trọng ngang vế thứ nhất:
  1. Ông LÀM ĐƯỢC phần đội xe: xem hồ sơ xe, ghi nhật trình chuyến, lập lệnh điều xe, lập đề xuất chi.
  2. Ông KHÔNG thấy phần không thuộc phạm vi: bảng lương, tài khoản ngân hàng, tour và booking khách.
     Mở một vai trò mới mà quên vế này là cách cấp thừa quyền mà không ai nhận ra.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_vai_tro_gd_doi_xe.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vai_tro_gd_doi_xe.db"): os.remove("test_vai_tro_gd_doi_xe.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import access as AC
from app.models.core import ROLES

client = TestClient(app); TOK = {}
HOM_NAY = date.today()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module")
def gd(_startup):
    """Tài khoản GĐ điều hành đội xe, và đặt tham số người lập lệnh trỏ đúng vào tài khoản đó."""
    from app.db.session import SessionLocal
    from app.models.core import User, Param
    from app.core.security import hash_password
    from sqlalchemy import select
    db = SessionLocal()
    u = User(username="gd.doixe.kt", full_name="GĐ điều hành đội xe kiểm thử", role="gd_doi_xe",
             department="doi_xe", staff_code="KT903", password_hash=hash_password("123456"), active=True)
    db.add(u)
    p = db.execute(select(Param).where(Param.key == "xe_nguoi_lap_lenh")).scalars().first()
    if p is not None: p.value = "gd.doixe.kt"
    db.commit(); db.close()
    return "gd.doixe.kt"


def test_vai_tro_co_trong_danh_muc(gd):
    assert ROLES["gd_doi_xe"] == "Giám đốc điều hành đội xe"


# ---------------------------------------------------------------- 1. Làm được phần đội xe
def test_thay_ba_man_hinh_doi_xe_va_khong_thay_gi_khac(gd):
    me = client.get("/api/v1/auth/me", headers=login(gd)).json()
    an = set(me["hidden_menus"])
    for trang in ("/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"):
        assert trang not in an, f"GĐ đội xe phải thấy {trang}"
    for trang in ("/payroll", "/bank-accounts", "/accounting", "/tours", "/requests", "/hr", "/audit"):
        assert trang in an, f"GĐ đội xe KHÔNG được thấy {trang}"


def test_doc_duoc_ho_so_xe_va_ghi_duoc_nhat_trinh(gd):
    h = login(gd)
    xe = client.get("/api/v1/fleet/xe", headers=h)
    assert xe.status_code == 200, xe.text
    v = xe.json()[0]
    r = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                          "km_dau": 500_000, "km_cuoi": 500_300, "doanh_thu": 9_000_000,
                          "ten_tour": "Chuyến kiểm thử GĐ đội xe"})
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert client.post(f"/api/v1/fleet/chuyen/{tid}/chi-phi", headers=h,
                       json={"kind": "dau", "amount": 3_000_000, "lit": 100}).status_code == 201
    assert client.put(f"/api/v1/fleet/chuyen/{tid}", headers=h,
                      json={"doanh_thu": 9_500_000}).status_code == 200


def test_lap_duoc_de_xuat_chi(gd):
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login(gd),
                    json={"ngay": str(HOM_NAY), "so_tien": 2_000_000, "noi_dung": "Sửa xe trên đường tour",
                          "nhom": "Chi phí riêng của xe"})
    assert r.status_code == 201, r.text


def test_lap_duoc_lenh_dieu_xe_khi_tham_so_tro_dung_vao_minh(gd):
    """Đây là thế bí mà vai trò này sinh ra để gỡ: trước bản này người được chỉ định lập lệnh không gọi nổi
    chính cái endpoint lập lệnh."""
    h = login(gd)
    xe = [x for x in client.get("/api/v1/fleet/xe", headers=h).json() if x.get("driver")]
    if not xe: pytest.skip("dữ liệu mẫu không có xe đã gán tài xế")
    tours = client.get("/api/v1/tours", headers=login("cntt"))
    ds = tours.json()["rows"] if tours.status_code == 200 else []
    if not ds: pytest.skip("dữ liệu mẫu không có tour")
    body = {"vehicle_id": xe[0]["id"], "tour_id": ds[0]["id"],
            "date_from": str(HOM_NAY + timedelta(days=400)), "date_to": str(HOM_NAY + timedelta(days=401)),
            "internal_price": 1_000_000}
    r = client.post("/api/v1/dispatch", headers=h, json=body)
    assert r.status_code in (201, 422), r.text
    assert r.status_code != 403, "người được chỉ định lập lệnh phải qua được cửa vai trò"


# ---------------------------------------------------------------- 2. KHÔNG với tới phần ngoài phạm vi
@pytest.mark.parametrize("duong_dan", [
    "/api/v1/hr/payroll", "/api/v1/banks/accounts", "/api/v1/tours", "/api/v1/bookings",
    "/api/v1/accounting/accounts",
])
def test_khong_goi_duoc_api_ngoai_pham_vi(gd, duong_dan):
    """Chặn ở MỘT chỗ theo danh sách cho phép: endpoint mới mặc định nằm NGOÀI phạm vi của vai trò bị giới
    hạn, nên thêm màn hình mới sau này không vô tình mở thêm dữ liệu cho ông."""
    r = client.get(duong_dan, headers=login(gd))
    assert r.status_code in (403, 404), f"{duong_dan} trả về {r.status_code}"


def test_khong_dong_duoc_ky_quyet_toan(gd):
    """Dựng bảng quyết toán là việc của ông; ĐÓNG kỳ – tức chốt con số với đối tác – vẫn là của Chủ tịch,
    TGĐ hoặc Kế toán."""
    h = login(gd)
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe kiểm thử GĐ"})
    assert pid.status_code == 201, pid.text
    ky = f"{HOM_NAY:%Y-%m}"
    st = client.post(f"/api/v1/fleet/quyet-toan/{ky}/{pid.json()['id']}/dung", headers=h)
    assert st.status_code == 200, st.text
    r = client.post(f"/api/v1/fleet/quyet-toan/{st.json()['id']}/dong-ky", headers=h)
    assert r.status_code == 403


def test_danh_sach_cho_phep_khong_bi_bo_ngo(gd):
    """Nếu ai đó xóa dòng cấu hình phạm vi thì vai trò này lập tức thấy mọi thứ như nhân viên văn phòng –
    phép thử này để việc đó không lặng lẽ xảy ra."""
    assert "gd_doi_xe" in AC.RESTRICTED_API_PREFIXES
    assert "gd_doi_xe" in AC.RESTRICTED_ROLE_MENUS
    assert set(AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"]) >= {"/doi-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe"}


# ---------------------------------------------------------------- 3. Có quyền mà không có cửa thì bằng không
def test_lay_duoc_tour_de_lap_lenh_bang_chinh_tai_khoan_cua_minh(gd):
    """Ông phải tự lấy được mã tour để điền vào lệnh – không phải hỏi người khác.

    Phép thử lập lệnh ở trên (07/9) mượn token của CNTT để lấy mã tour:

        tours = client.get("/api/v1/tours", headers=login("cntt"))

    Dòng ấy chứng minh endpoint lập lệnh chạy được, nhưng cũng nói ra – mà lúc viết không ai để ý – rằng
    chính người lập lệnh KHÔNG lấy nổi mã tour bằng tài khoản của mình. Trên máy thử thì mượn một token là
    xong; ngoài đời thì ông phải nhắn cho Điều hành hỏi mã tour trước mỗi lệnh, và cái phân hệ trông như
    đang chạy thật ra đang chạy bằng tin nhắn.

    Cách chữa KHÔNG phải mở /api/v1/tours cho ông (phép thử ngoài phạm vi ở trên giữ chỗ đó đóng): tour mang
    giá bán, dự toán và biên lợi nhuận. Đường /api/v1/fleet/de-lap-lenh trả đúng phần lịch trình.
    """
    h = login(gd)
    tu = HOM_NAY + timedelta(days=400)
    r = client.get(f"/api/v1/fleet/de-lap-lenh?tu={tu}&den={tu + timedelta(days=1)}", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) >= {"tour", "bang_gia", "nguoi_duoc_lap_lenh", "toi_duoc_lap"}
    assert d["toi_duoc_lap"] is True, "tham số đang trỏ vào ông mà đường này lại bảo ông không được lập"


def test_duong_de_lap_lenh_khong_kem_mot_con_so_tien_nao_cua_tour(gd):
    """Mở một cửa hẹp thì phải hẹp thật.

    Nếu đường này tiện tay trả nguyên bản ghi tour thì nó vừa chở theo giá bán, dự toán, biên lợi nhuận và
    giải trình dưới biên – tức là mở /api/v1/tours bằng lối khác, trong khi phép thử ngoài phạm vi ở trên
    vẫn xanh và không ai biết hàng rào đã thủng.
    """
    h = login(gd)
    tu = HOM_NAY
    r = client.get(f"/api/v1/fleet/de-lap-lenh?tu={tu}&den={tu + timedelta(days=60)}", headers=h)
    assert r.status_code == 200, r.text
    cam = {"price_per_pax", "fixed_cost", "var_cost_per_pax", "below_margin", "justification",
           "revenue", "profit", "margin", "doanh_thu", "loi_nhuan"}
    for t in r.json()["tour"]:
        thua = cam & set(t)
        assert not thua, f"đường lập lệnh đang chở theo số tiền của tour: {sorted(thua)}"
        assert set(t) == {"id", "code", "name", "start_date", "end_date", "planned_pax"}, (
            f"cột lạ trong danh sách tour để lập lệnh: {sorted(set(t))}")


def test_nguoi_khac_hoi_duong_nay_thi_duoc_bao_la_khong_duoc_lap(gd):
    """Đường trả sẵn câu trả lời cho câu hỏi "tôi có được chốt không", để màn hình nói bằng lời thay vì để
    người dùng bấm nút rồi nhận 403 – lỗi 403 không nói được ai mới là người được bấm."""
    tu = HOM_NAY
    r = client.get(f"/api/v1/fleet/de-lap-lenh?tu={tu}&den={tu}", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["toi_duoc_lap"] is False
    assert d["nguoi_duoc_lap_lenh"], "phải nói ra AI được lập, không chỉ nói 'anh thì không'"
