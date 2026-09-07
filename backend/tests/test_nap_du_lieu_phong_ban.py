"""Bộ nạp dữ liệu của các phòng ban: nhân sự, khách hàng, booking, sao kê ngân hàng, chấm công.

Mỗi test dưới đây ứng với một cách mà việc "tải tệp lên cho nhanh" phá sổ của một phòng cụ thể:

  Nhân sự  – tệp nạp lại đè lương của người đang làm việc, không còn biết mức cũ là bao nhiêu.
  Khách    – cùng danh sách khách nạp hai lần, số lead của tháng phồng lên gấp đôi, chi phí/lead sai theo.
  Booking  – ghi "đã thu" nhiều hơn số phải thu, tức là tiền của booking khác nằm nhầm chỗ.
  Sao kê   – tệp sao kê tự khớp booking, tiền được ghi nhận mà không ai chịu trách nhiệm về việc khớp.
  Lương    – nạp thẳng bảng lương đã tính là bỏ qua toàn bộ các bước xác nhận và ký.

Và một quy tắc chung: mở được màn hình nạp dữ liệu KHÔNG có nghĩa là nạp được sổ của phòng khác.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_nap_pb.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nap_pb.db"): os.remove("test_nap_pb.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def nap(who, loai, rows, **kw):
    return client.post("/api/v1/nap-du-lieu/nap", headers=login(who),
                       json={"loai": loai, "rows": rows, **kw})


def _luong(ma):
    from app.db.session import SessionLocal
    from app.models.hr import Employee
    from sqlalchemy import select
    with SessionLocal() as db:
        return db.execute(select(Employee).where(Employee.code == ma)).scalars().first().base_salary


def kiem(who, loai, rows):
    return client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login(who),
                       json={"loai": loai, "rows": rows})


# ---------------------------------------------------------------- Khai báo
def test_du_bo_nap_cho_cac_phong_ban(_startup):
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("cntt")).json()
    ma = {b["ma"] for b in d["bo_nap"]}
    assert {"nhan_su", "khach_hang", "booking", "sao_ke_ngan_hang", "cham_cong"} <= ma
    for b in d["bo_nap"]:
        assert b["phong_ban"], f"{b['ma']} chưa gắn phòng ban – màn hình không xếp được theo phòng"
        assert b["vai_tro"], f"{b['ma']} chưa khai vai trò – không khai thì ai cũng nạp được"
        assert b["cot"] and any(c["bat_buoc"] for c in b["cot"])


def test_moi_bo_nap_deu_co_tep_mau(_startup):
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("cntt")).json()
    for b in d["bo_nap"]:
        r = client.get(f"/api/v1/nap-du-lieu/mau/{b['ma']}", headers=login("cntt"))
        assert r.status_code == 200 and len(r.text.splitlines()) >= 2, b["ma"]


# ---------------------------------------------------------------- Phân quyền theo bộ nạp
def test_mo_duoc_man_hinh_khong_co_nghia_la_nap_duoc_so_phong_khac(_startup):
    """Kinh doanh nạp danh sách khách của mình thì được; nạp hồ sơ nhân sự thì không.

    Chặn ở cửa màn hình là không đủ: hoặc phải mở cho mọi phòng (ai cũng nạp được mọi thứ), hoặc đóng bớt
    phòng và họ sẽ nhờ người khác nạp hộ – nhật ký khi đó ghi sai tên người chịu trách nhiệm."""
    r = nap("kd.hoa", "nhan_su", [{"Mã nhân viên": "NS9001", "Họ và tên": "Thử", "Phòng ban": "kd_le"}])
    assert r.status_code == 403 and "phòng khác" in r.json()["detail"]
    r = nap("hcns", "sao_ke_ngan_hang", [{"Mã giao dịch": "X1", "Ngân hàng": "TPBank",
                                          "Thời điểm": "01/08/2026", "Loại": "vao", "Số tiền": "1000"}])
    assert r.status_code == 403


# ---------------------------------------------------------------- Nhân sự
def _ns(ma="NS9101", ten="Nguyễn Thử Việc", pb="kd_le", luong="9.000.000"):
    return {"Mã nhân viên": ma, "Họ và tên": ten, "Phòng ban": pb, "Vị trí": "nv",
            "Lương công việc": luong, "Ngày vào làm": "01/03/2026", "Điện thoại": "0903123456"}


def test_nhan_su_nap_duoc_va_doc_dung_so_co_dau_cham(_startup):
    r = nap("hcns", "nhan_su", [_ns()])
    assert r.status_code == 201, r.text
    assert r.json()["da_nap"] == 1
    assert _luong("NS9101") == 9_000_000


def test_nhan_su_nap_lai_khong_de_len_luong_nguoi_dang_lam(_startup):
    """Đè được lương bằng một tệp nạp nhầm là mất luôn giá trị cũ – không ai biết mức đúng là bao nhiêu."""
    r = nap("hcns", "nhan_su", [_ns(luong="1")])
    assert r.status_code == 201
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 1
    assert _luong("NS9101") == 9_000_000, "nạp lần hai đã ghi đè lương – đúng ra phải bỏ qua"


def test_nhan_su_phong_ban_la_thi_bao_ra(_startup):
    d = kiem("hcns", "nhan_su", [_ns(ma="NS9102", pb="phong_khong_co")]).json()
    assert d["dong_loi"] == 1 and "không có trong danh mục" in d["dong"][0]["loi"][0]


def test_nhan_su_trung_ten_thi_canh_bao_chu_khong_chan(_startup):
    """Công ty có người trùng tên thật – chặn là sai; im lặng cũng sai."""
    d = kiem("hcns", "nhan_su", [_ns(ma="NS9103", ten="Nguyễn Thử Việc")]).json()
    assert d["dong_loi"] == 0 and any("cùng tên" in c for c in d["dong"][0]["canh_bao"])


# ---------------------------------------------------------------- Khách hàng
def test_khach_hang_nap_lai_khong_thoi_phong_so_lead(_startup):
    row = {"Số điện thoại": "0903 111 222", "Tên khách": "Chị Lan", "Kênh": "Hotline 1",
           "Tháng phát sinh": "2026-08", "Tour quan tâm": "Đà Lạt"}
    r = nap("kd.hoa", "khach_hang", [row]); assert r.status_code == 201 and r.json()["da_nap"] == 1
    r = nap("kd.hoa", "khach_hang", [row])
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 1, "cùng số, cùng tháng, cùng kênh là một khách"


def test_khach_hang_so_dien_thoai_hong_thi_bao_ra(_startup):
    d = kiem("kd.hoa", "khach_hang", [{"Số điện thoại": "abc", "Kênh": "Hotline 1"}]).json()
    assert d["dong_loi"] == 1


def test_khach_hang_khac_kenh_la_khach_khac(_startup):
    """Cùng số nhưng đến từ kênh khác trong tháng khác là một lần phát sinh khác – không gộp."""
    r = nap("kd.hoa", "khach_hang", [{"Số điện thoại": "0903 111 222", "Kênh": "Zalo OA",
                                      "Tháng phát sinh": "2026-09"}])
    assert r.json()["da_nap"] == 1


# ---------------------------------------------------------------- Booking
def _bk(ma="BKNAP001", tien="24.000.000", thu="0"):
    return {"Mã booking": ma, "Mã tour": "PT-DL-0912", "Tên khách": "Khách nạp tệp",
            "Điện thoại": "0912345678", "Số khách": "4", "Tiền tour": tien, "Đã thu": thu,
            "Nguồn khách": "Hotline 1"}


def test_booking_khong_co_tour_thi_tu_choi(_startup):
    d = kiem("kd.hoa", "booking", [{**_bk(), "Mã tour": "KHONG-CO"}]).json()
    assert d["dong_loi"] == 1 and "không vào được kết quả của chuyến nào" in d["dong"][0]["loi"][0]


def test_booking_da_thu_lon_hon_phai_thu_thi_chan(_startup):
    """Thu nhiều hơn phải thu nghĩa là tiền của booking khác đang nằm nhầm chỗ, hoặc là tiền bảo lưu –
    cả hai đều phải làm rõ trước khi vào sổ, không ghi bừa rồi sửa sau."""
    d = kiem("kd.hoa", "booking", [_bk(tien="10000000", thu="12000000")]).json()
    assert d["dong_loi"] == 1 and "lớn hơn số phải thu" in d["dong"][0]["loi"][0]


def test_booking_nap_duoc_va_khong_nhan_doi(_startup):
    r = nap("kd.hoa", "booking", [_bk(thu="5000000")])
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    assert any("KHÔNG sinh phiếu thu" in c for c in r.json()["dong"][0]["canh_bao"])
    r2 = nap("kd.hoa", "booking", [_bk(thu="5000000")])
    assert r2.json()["da_nap"] == 0 and r2.json()["da_co"] == 1


# ---------------------------------------------------------------- Sao kê ngân hàng
def _sk(ma="FT26240012345", tien="24.000.000", loai="vao"):
    return {"Mã giao dịch": ma, "Ngân hàng": "TPBank", "Số tài khoản": "01811267101",
            "Thời điểm": "31/08/2026 14:20", "Loại": loai, "Số tiền": tien,
            "Nội dung chuyển khoản": "NGUYEN VAN A chuyen tien tour PT-DL-0912"}


def test_sao_ke_nap_len_o_trang_thai_chua_khop(_startup):
    """Tệp sao kê tự khớp booking là ghi nhận tiền mà không ai chịu trách nhiệm về việc khớp."""
    r = nap("ketoan", "sao_ke_ngan_hang", [_sk()])
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    from app.db.session import SessionLocal
    from app.models.payments import BankTransaction
    from sqlalchemy import select
    with SessionLocal() as db:
        t = db.execute(select(BankTransaction).where(
            BankTransaction.sepay_id.like("saoke:%FT26240012345"))).scalars().first()
        assert t is not None and t.match_status == "chua_khop" and t.booking_id is None


def test_sao_ke_nap_lai_khong_nhan_doi_tien(_startup):
    r = nap("ketoan", "sao_ke_ngan_hang", [_sk()])
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 1


def test_sao_ke_so_am_bi_tu_choi_voi_loi_giai_thich(_startup):
    """Ngân hàng xuất tiền ra bằng số âm; nếu nhận cả số âm thì cùng một tệp có hai cách hiểu về chiều tiền."""
    d = kiem("ketoan", "sao_ke_ngan_hang", [_sk(ma="FT-AM", tien="-5000000")]).json()
    assert d["dong_loi"] == 1 and "không ghi số âm" in d["dong"][0]["loi"][0]


def test_sao_ke_thieu_ma_giao_dich_thi_tu_choi(_startup):
    d = kiem("ketoan", "sao_ke_ngan_hang", [{**_sk(), "Mã giao dịch": ""}]).json()
    assert d["dong_loi"] == 1


# ---------------------------------------------------------------- Chấm công / bảng lương
def test_khong_co_bo_nap_bang_luong_thanh_pham(_startup):
    """Cố ý: nạp thẳng số lương đã tính là bỏ qua các bước Kế toán xác nhận – HCNS lập – TGĐ ký."""
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("hcns")).json()
    ma = {b["ma"] for b in d["bo_nap"]}
    assert "bang_luong" not in ma
    cc = next(b for b in d["bo_nap"] if b["ma"] == "cham_cong")
    assert "bỏ qua toàn bộ các bước xác nhận" in cc["mo_ta"]


def test_cham_cong_nap_vao_dau_vao_cua_ky(_startup):
    r = nap("hcns", "cham_cong", [{"Kỳ lương": "2026-08", "Mã nhân viên": "NS0016",
                                   "Công thực tế": "24"}])
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    r2 = nap("hcns", "cham_cong", [{"Kỳ lương": "2026-08", "Mã nhân viên": "NS0016",
                                    "Công thực tế": "12"}])
    assert r2.json()["da_nap"] == 0 and r2.json()["da_co"] == 1, "nạp lại phải bỏ qua, không sửa công lặng lẽ"


def test_cham_cong_ma_nhan_vien_khong_co_thi_tu_choi(_startup):
    d = kiem("hcns", "cham_cong", [{"Kỳ lương": "2026-08", "Mã nhân viên": "NS9999",
                                    "Công thực tế": "24"}]).json()
    assert d["dong_loi"] == 1 and "Không có nhân sự" in d["dong"][0]["loi"][0]


def test_cham_cong_qua_31_ngay_thi_tu_choi(_startup):
    d = kiem("hcns", "cham_cong", [{"Kỳ lương": "2026-08", "Mã nhân viên": "NS0016",
                                    "Công thực tế": "45"}]).json()
    assert d["dong_loi"] == 1
