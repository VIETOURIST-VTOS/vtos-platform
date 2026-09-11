"""Báo cáo bán hàng tách theo mảng Kinh doanh Lẻ / Kinh doanh Đoàn (chỉ đạo 07/9/2026).

Bộ lọc trên màn hình danh sách đã có từ trước; đây là phần báo cáo – chỗ mà sai một quy tắc thì không chỉ
nhìn thiếu dòng mà còn ra sai con số doanh thu đưa lên bàn họp. Vì vậy các test dưới đây không kiểm "có lọc
hay không", mà kiểm ba điều dễ sai nhất:

  1. Tổng của hai mảng phải khớp tổng toàn hệ thống – không bỏ sót, cũng không đếm trùng.
  2. Báo cáo và màn hình danh sách phải dùng CÙNG một định nghĩa mảng, kể cả với tour hai quy tắc bất đồng.
  3. Gõ sai tên mảng thì báo lỗi, chứ không âm thầm trả về toàn hệ thống dưới nhãn của một phòng.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_bao_cao_mang.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_bao_cao_mang.db"): os.remove("test_bao_cao_mang.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"from={HOM_NAY.replace(day=1)}&to={HOM_NAY}&month={HOM_NAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def tao_tour(code: str, tour_type: str) -> int:
    from app.db.session import SessionLocal
    from app.models.core import Tour, User
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        op = db.execute(sel(User).where(User.username == "dh.lan")).scalars().first()
        t = Tour(code=code, name=f"Kiểm thử báo cáo {code}", tour_type=tour_type,
                 start_date=HOM_NAY + timedelta(days=20), end_date=HOM_NAY + timedelta(days=22),
                 operator_id=op.id, price_per_pax=10_000_000, fixed_cost=0, var_cost_per_pax=5_000_000,
                 planned_pax=10, status="da_duyet")
        db.add(t); db.commit(); return t.id
    finally:
        db.close()


def dat_cho(tour_id: int, ten: str, phone: str, pax: int = 2) -> dict:
    r = client.post("/api/v1/requests", headers=login("kd.hoa"),
                    json={"tour_id": tour_id, "customer_name": ten, "customer_phone": phone,
                          "source": "Zalo", "care_note": "Khách kiểm thử báo cáo", "pax": pax})
    assert r.status_code == 201, r.text
    rid = r.json()["request"]["id"]
    b = client.post(f"/api/v1/requests/{rid}/booking", headers=login("dh.lan"))
    assert b.status_code == 201, b.text
    return b.json()["booking"]


def bao_cao(key: str, mang: str = "", who: str = "chutich") -> dict:
    r = client.get(f"/api/v1/sales-reports/{key}?{KY}&mang={mang}", headers=login(who))
    assert r.status_code == 200, r.text
    return r.json()


def bao_cao_tour(mang: str = "") -> dict:
    """tour_le lọc theo NGÀY KHỞI HÀNH, không theo ngày tạo booking – nên phải mở kỳ tới ngày các tour kiểm
    thử khởi hành, nếu không bảng rỗng và phép thử không kiểm được gì."""
    r = client.get(f"/api/v1/sales-reports/tour_le?from={HOM_NAY.replace(day=1)}&to={HOM_NAY + timedelta(days=40)}&mang={mang}",
                   headers=login("chutich"))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module", autouse=True)
def _du_lieu(_startup):
    """Một tour đoàn đúng chuẩn, một tour mã MICE bị ghi nhầm loại chuyến, một tour lẻ bình thường."""
    global T_DOAN, T_LECH, T_LE
    T_DOAN = tao_tour("MICEBC01-0930", "doan_noi_dia")
    T_LECH = tao_tour("MICEBC02-0930", "le_noi_dia")     # mã MICE nhưng loại chuyến ghi là lẻ
    T_LE = tao_tour("PTBC03-0930", "le_noi_dia")
    dat_cho(T_DOAN, "Khách Đoàn", "0911000001", pax=4)
    dat_cho(T_LECH, "Khách Lệch", "0911000002", pax=2)
    dat_cho(T_LE, "Khách Lẻ", "0911000003", pax=3)
    yield


def test_hai_mang_cong_lai_dung_bang_toan_he_thong():
    """Không bỏ sót và không đếm trùng: cộng doanh thu hai phòng phải ra đúng doanh thu toàn hệ thống.

    Đây là phép thử mà bất kỳ sai sót nào trong điều kiện lọc đều lộ ra – thiếu một nhánh thì tổng hụt,
    thừa một nhánh thì tổng vượt."""
    tat_ca = bao_cao("ban_tour_le")["total"]
    le = bao_cao("ban_tour_le", "le")["total"]
    doan = bao_cao("ban_tour_le", "doan")["total"]
    assert le["revenue"] + doan["revenue"] == tat_ca["revenue"], "doanh thu hai mảng phải khớp tổng"
    assert le["bookings"] + doan["bookings"] == tat_ca["bookings"]
    assert le["pax"] + doan["pax"] == tat_ca["pax"]
    assert doan["revenue"] > 0 and le["revenue"] > 0, "dữ liệu kiểm thử phải có cả hai mảng, nếu không phép thử vô nghĩa"


def test_tour_ma_MICE_ghi_nham_loai_chuyen_van_thuoc_doanh_thu_phong_doan():
    """Tour MICEBC02 mã MICE nhưng loại chuyến ghi là lẻ. Nếu báo cáo chỉ nhìn loại chuyến thì doanh thu này
    chảy sang phòng Lẻ, và cuối tháng hai phòng cãi nhau về một con số mà không ai tra ra vì sao."""
    ma_doan = {r["tour_code"] for r in bao_cao("ban_tour_le", "doan")["detail"]}
    ma_le = {r["tour_code"] for r in bao_cao("ban_tour_le", "le")["detail"]}
    assert "MICEBC02-0930" in ma_doan
    assert "MICEBC02-0930" not in ma_le
    assert "PTBC03-0930" in ma_le and "PTBC03-0930" not in ma_doan


def test_bao_cao_va_man_hinh_danh_sach_khong_duoc_noi_khac_nhau():
    """Cùng một mảng, cùng một kỳ: danh sách booking và báo cáo phải kể cùng một câu chuyện."""
    h = login("chutich")
    for mang in ("le", "doan"):
        tours_ms = {t["code"] for t in client.get(f"/api/v1/tours?mang={mang}&limit=1000", headers=h).json()["rows"]}
        tours_bc = {r["tour_code"] for r in bao_cao("ban_tour_le", mang)["detail"]}
        assert tours_bc <= tours_ms, f"mảng {mang}: báo cáo có tour mà màn hình danh sách không công nhận"


def test_moi_bao_cao_deu_nhan_mang_chu_khong_chi_mot_cai():
    """Tách nửa vời còn nguy hiểm hơn không tách: người dùng thấy báo cáo đầu lọc đúng nên tin luôn các
    báo cáo sau."""
    for key in ("ban_tour_le", "nhac_thu", "huy_cho", "kinh_doanh", "tour_le"):
        for mang in ("le", "doan"):
            d = bao_cao(key, mang)
            assert d["mang"] == mang, f"{key} không giữ lại mảng đang xem trong kết quả"


def test_bao_cao_tour_le_khong_om_tour_cua_phong_doan():
    """Báo cáo hiệu quả chuyến của phòng Lẻ phải loại tour mã MICE ghi nhầm loại chuyến – nếu không, một
    chuyến vừa nằm ở màn hình phòng Đoàn vừa nằm trong bảng lãi lỗ của phòng Lẻ."""
    ma_le = {r["tour_code"] for r in bao_cao_tour("le")["summary"]}
    ma_doan = {r["tour_code"] for r in bao_cao_tour("doan")["summary"]}
    assert "MICEBC02-0930" not in ma_le
    assert {"MICEBC01-0930", "MICEBC02-0930"} <= ma_doan
    assert "PTBC03-0930" in ma_le
    assert ma_le & ma_doan == set()


def test_khong_chon_mang_thi_giu_nguyen_pham_vi_cu():
    """Ban Giám đốc, Kế toán, BKS vẫn cần một con số hợp nhất – bỏ tham số thì báo cáo chạy như trước."""
    d = bao_cao("ban_tour_le")
    assert d["mang"] == ""
    ts = {r["tour_code"] for r in d["detail"]}
    assert {"MICEBC01-0930", "MICEBC02-0930", "PTBC03-0930"} <= ts
    # Báo cáo tour lẻ khi không chọn mảng vẫn là "tour lẻ" theo loại chuyến như bản cũ
    cu = {r["tour_code"] for r in bao_cao_tour()["summary"]}
    assert "PTBC03-0930" in cu and "MICEBC01-0930" not in cu


def test_mang_sai_thi_422_chu_khong_tra_ve_toan_he_thong():
    """Trả về toàn hệ thống dưới nhãn một phòng là kiểu sai tệ nhất: số liệu sai mà trông vẫn hợp lý."""
    for xau in ("doann", "MICE", "kinh_doanh_le"):
        r = client.get(f"/api/v1/sales-reports/ban_tour_le?{KY}&mang={xau}", headers=login("chutich"))
        assert r.status_code == 422, f"{xau} phải bị từ chối, nhận {r.status_code}"
        assert "Mảng không hợp lệ" in r.json()["detail"]
    r = client.get(f"/api/v1/sales-reports/ban_tour_le/xlsx?{KY}&mang=doann", headers=login("chutich"))
    assert r.status_code == 422, "bản Excel cũng phải từ chối, không được xuất file sai nhãn"


def test_file_excel_ghi_ro_dang_xem_phong_nao():
    """File Excel rời khỏi phần mềm là mất ngữ cảnh. Hai bản của hai phòng trông giống hệt nhau thì sớm muộn
    cũng có người gửi nhầm bản của phòng kia đi họp."""
    from io import BytesIO
    from openpyxl import load_workbook
    for mang, nhan in (("doan", "Kinh doanh Đoàn"), ("le", "Kinh doanh Lẻ"), ("", "Toàn hệ thống")):
        r = client.get(f"/api/v1/sales-reports/ban_tour_le/xlsx?{KY}&mang={mang}", headers=login("chutich"))
        assert r.status_code == 200, r.text
        ws = load_workbook(BytesIO(r.content)).active
        assert nhan in str(ws["A2"].value), f"file mảng '{mang}' không ghi phạm vi: {ws['A2'].value}"


def test_loc_mang_khong_noi_rong_quyen_xem_cua_sale():
    """Bộ lọc mảng chỉ được thu hẹp. Nếu nó vô tình bỏ qua bước lọc theo quyền thì một nhân viên nhìn thấy
    doanh số của người khác."""
    rieng = bao_cao("ban_tour_le", "doan", who="kd.hoa")
    tat_ca_cua_minh = bao_cao("ban_tour_le", who="kd.hoa")
    ten_rieng = {r["sale"] for r in rieng["summary"]}
    ten_tat_ca = {r["sale"] for r in tat_ca_cua_minh["summary"]}
    assert ten_rieng <= ten_tat_ca
    assert rieng["total"]["revenue"] <= tat_ca_cua_minh["total"]["revenue"]


def test_hoa_hong_bac_thang_khong_ap_nham_cho_mang_doan():
    """Mảng Đoàn ăn theo chia lợi nhuận quyết toán chứ không theo bậc thang doanh thu. Báo cáo phải nói rõ
    điều đó thay vì để hai cột bằng 0 không giải thích."""
    d = bao_cao("kinh_doanh", "doan")
    assert d["total"]["revenue_target"] == 0
    assert d["total"]["commission_est"] == 0
    assert "chia lợi nhuận" in d["note"], "phải giải thích vì sao hai cột bằng 0"
    assert bao_cao("kinh_doanh", "le")["total"]["revenue_target"] > 0


def test_dinh_nghia_mang_dung_chung_cho_ca_tien_luong():
    """rules.is_doan quyết định định tuyến duyệt, hạn quyết toán và cách tính hoa hồng. Nếu nó nói khác bộ
    lọc mảng thì sẽ có tour nằm ở phòng Đoàn nhưng được trả hoa hồng theo bậc thang của phòng Lẻ."""
    from app.db.session import SessionLocal
    from app.models.core import Tour
    from app.services import rules as R
    from app.services import segments as SEG
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        for t in db.execute(sel(Tour)).scalars():
            assert R.is_doan(t) == (SEG.mang_of(t) == "doan"), f"{t.code}: hai định nghĩa mảng nói khác nhau"
    finally:
        db.close()
