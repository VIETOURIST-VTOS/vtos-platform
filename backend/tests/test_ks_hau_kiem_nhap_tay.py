"""K3 – hậu kiểm số nhân viên nhập tay. Lệnh Robot Kiểm soát 08/9/2026.

Đây là lớp bảo vệ THAY CHO khâu trưởng phòng duyệt từng dòng mà Chủ tịch đã bỏ. Bỏ một lớp chặn có
thật thì lớp còn lại phải chặt hơn, nên mỗi dấu hiệu dưới đây được dựng đúng tình huống rồi mới đòi
robot nhìn thấy.

  KN1  tài khoản máy (robot, vietrip) không bị đem ra hậu kiểm
  KN2  số tròn lặp lại ở khoản lớn thì bắt; tròn một lần thì không
  KN3  nhập ngoài giờ làm việc
  KN4  nhập dồn nhiều dòng trong năm phút
  KN5  một người nhập số cho phòng khác; không biết người đó phòng nào thì IM LẶNG
  KN6  nhập lùi ngày vào kỳ đã khóa – mức ĐỎ
  KN7  mọi ngưỡng đọc từ tham số chính sách, không viết cứng
  KN8  bảng đo ngưỡng: ngưỡng lỏng hơn thì ra ít dòng hơn
  KN9  bộ hậu kiểm đã gắn vào vòng quét, và một dấu hiệu hỏng không làm trắng cả bộ
"""
import os, sys
from datetime import datetime, date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ksnt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_ksnt.db", "test_ksnt.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
THANG = f"{date.today():%Y-%m}"


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        _dung_du_lieu()
        yield


def _dau(luc: datetime) -> datetime:
    """Giữ mốc trong THÁNG NÀY để phép thử không phụ thuộc ngày chạy."""
    d = date.today().replace(day=1)
    return datetime(d.year, d.month, 2, luc.hour, luc.minute, luc.second)


def _dung_du_lieu():
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    from app.models.accounting import JournalEntry, PeriodLock
    from app.models.payments import Receipt
    from app.models.core import Booking
    from sqlalchemy import select
    db = SessionLocal()
    n = 0

    def chi(code, tien, nguoi, luc):
        nonlocal n; n += 1
        db.add(PaymentRequest(code=code, category="hanh_chinh", supplier_name="NCC thử", amount=tien,
                              description="dựng cho phép thử", created_by=nguoi, created_at=luc,
                              status="cho_tp"))

    # KN1: tài khoản máy nhập một loạt số tròn – phải bị bỏ qua
    for i in range(6): chi(f"DCROB{i:03d}", 50_000_000, "robot", _dau(datetime(2026, 1, 1, 10, i)))
    # KN2: người thật nhập đúng 30 triệu bốn lần
    for i in range(4): chi(f"DCTRON{i:03d}", 30_000_000, "hcns", _dau(datetime(2026, 1, 1, 9, i)))
    # số tròn nhưng chỉ một lần – không được bắt
    chi("DCTRON900", 77_000_000, "hcns", _dau(datetime(2026, 1, 1, 9, 40)))
    # KN3: bốn dòng lúc 2 giờ sáng
    for i in range(4): chi(f"DCDEM{i:03d}", 1_234_567 + i, "hcns", _dau(datetime(2026, 1, 1, 2, i)))
    # KN4: mười hai dòng trong ba phút, trong giờ
    for i in range(12): chi(f"DCDON{i:03d}", 900_000 + i, "ketoan", _dau(datetime(2026, 1, 1, 14, i // 5, i)))

    # KN5: sổ Phiếu thu là của Kế toán, nhưng nhân viên kinh doanh nhập
    bk = db.execute(select(Booking)).scalars().first()
    for i in range(3):
        db.add(Receipt(code=f"PTKD{i:03d}", booking_id=bk.id, amount=5_000_000, method="tien_mat",
                       payer="Khách thử", created_by="kd.hoa", created_at=_dau(datetime(2026, 1, 1, 10, i))))

    # KN6: khóa một kỳ cũ rồi ghi bút toán mang ngày thuộc kỳ đó
    ky_cu = (date.today().replace(day=1) - timedelta(days=40))
    ky = f"{ky_cu:%Y-%m}"
    db.add(PeriodLock(period=ky, locked_by="ketoan", note="khóa cho phép thử"))
    for i in range(2):
        db.add(JournalEntry(code=f"CTLUI{i:03d}", entry_date=ky_cu, period=ky, description="lùi ngày",
                            status="da_ghi_so", created_by="ketoan", created_at=_dau(datetime(2026, 1, 1, 11, i))))
    db.commit(); db.close()


def ds(thang=None):
    return client.get(f"/api/v1/kiem-soat/nhap-tay?thang={thang or THANG}", headers=login("cntt")).json()


def loc(d, loai, nguoi=None):
    return [r for r in d["rows"] if r["loai"] == loai and (nguoi is None or r.get("nguoi") == nguoi)]


def test_kn1_tai_khoan_may_khong_bi_dem_ra_hau_kiem():
    d = ds()
    may = [r for r in d["rows"] if (r.get("nguoi") or "").lower() in ("robot", "vietrip", "sepay")]
    assert not may, ("robot nạp dữ liệu không phải người nhập; để lại thì mọi dấu hiệu đều chỉ vào nó "
                     f"và phần của con người chìm nghỉm. Đang thấy: {may}")


def test_kn2_so_tron_lap_lai_thi_bat_tron_mot_lan_thi_khong():
    d = ds()
    r = loc(d, "nt_so_tron", "hcns")
    assert r, "bốn dòng đúng 30.000.000đ của cùng một người mà không bắt thì dấu hiệu này vô dụng"
    assert any(x["chi_tiet"]["so_tien"] == 30_000_000 and x["chi_tiet"]["so_lan"] >= 4 for x in r)
    assert not any(x["chi_tiet"]["so_tien"] == 77_000_000 for x in r), \
        "một con số tròn xuất hiện một lần không nói lên điều gì – bắt là báo oan"


def test_kn3_nhap_ngoai_gio_lam_viec():
    d = ds()
    r = [x for x in loc(d, "nt_ngoai_gio", "hcns") if "ngoài giờ" in x["tom_tat"]]
    assert r and r[0]["chi_tiet"]["so_dong"] >= 4


def test_kn4_nhap_don_nhieu_dong_trong_nam_phut():
    d = ds()
    r = [x for x in loc(d, "nt_ngoai_gio", "ketoan") if "5 phút" in x["tom_tat"]]
    assert r and r[0]["chi_tiet"]["dong_5_phut"] >= 10


def test_kn5_mot_nguoi_nhap_so_cho_phong_khac():
    d = ds()
    r = loc(d, "nt_khac_phong", "kd.hoa")
    assert r, "Phiếu thu là sổ của Kế toán mà nhân viên kinh doanh nhập – phải hiện ra"
    assert r[0]["chi_tiet"]["phong_so"] == "Kế toán" and r[0]["chi_tiet"]["phong_nguoi"] == "Kinh doanh"
    # người không có trong danh mục vai trò thì im lặng, không đoán
    assert all(x["chi_tiet"]["phong_nguoi"] for x in loc(d, "nt_khac_phong"))


def test_kn6_nhap_lui_ngay_vao_ky_da_khoa_la_muc_do():
    d = ds()
    r = loc(d, "nt_lui_ngay", "ketoan")
    assert r and r[0]["chi_tiet"]["so_dong"] >= 2
    from app.services.ks_nhap_tay import _hau_kiem_nhap_tay
    from app.db.session import SessionLocal
    db = SessionLocal(); ph = _hau_kiem_nhap_tay(db); db.close()
    lui = [p for p in ph if "lùi ngày" in p["tom_tat"] or "ĐÃ KHÓA" in p["tom_tat"]]
    assert lui and all(p["muc"] == "do" for p in lui), \
        "kỳ khóa là chốt chặn cuối cùng còn lại sau khi bỏ khâu duyệt – lách nó không thể là mức vàng"


def test_kn7_moi_nguong_doc_tu_tham_so_khong_viet_cung():
    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    truoc = len(loc(ds(), "nt_so_tron", "hcns"))
    assert truoc >= 1
    db = SessionLocal()
    db.add(Param(key="ks_tron_lap", value="99", label="thử", unit="lần", source="thử",
                 status="active", effective_from=date.today()))
    db.commit(); R.clear_param_cache(); db.close()
    try:
        assert len(loc(ds(), "nt_so_tron", "hcns")) == 0, \
            "đổi tham số mà kết quả không đổi nghĩa là ngưỡng đang nằm trong mã nguồn"
    finally:
        db = SessionLocal()
        db.add(Param(key="ks_tron_lap", value="3", label="trả lại", unit="lần", source="thử",
                     status="active", effective_from=date.today()))
        db.commit(); R.clear_param_cache(); db.close()


def test_kn8_bang_do_nguong_cho_nguoi_chon_bang_so_lieu():
    d = client.get(f"/api/v1/kiem-soat/nhap-tay/do-nguong?thang={THANG}&lan=2,3,5,10",
                   headers=login("cntt")).json()
    assert [x["lech_bao_nhieu_lan"] for x in d["bang"]] == [2, 3, 5, 10]
    tong = [x["tong_dong"] for x in d["bang"]]
    assert tong == sorted(tong, reverse=True), \
        f"ngưỡng lỏng hơn phải ra ít dòng hơn hoặc bằng, đang là {tong}"
    assert set(d["loai"]) == {"nt_lech_ky", "nt_so_tron", "nt_ngoai_gio", "nt_khac_phong",
                              "nt_lui_ngay", "nt_sua_da_chot"}, "phải đủ sáu dấu hiệu lệnh giao"


def test_kn9_da_gan_vao_vong_quet_va_mot_dau_hieu_hong_khong_lam_trang_ca_bo():
    from app.services import ks_robot as KS
    from app.services import ks_nhap_tay as NT
    from app.db.session import SessionLocal
    assert "_hau_kiem_nhap_tay" in {f.__name__ for f in KS.BO_KIEM}
    goc = NT._so_tron
    NT._so_tron = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("dấu hiệu hỏng"))
    try:
        db = SessionLocal(); ra = NT.quet_thang(db, THANG); db.close()
        assert any(x.get("loi") for x in ra), "dấu hiệu hỏng phải được NÓI RA, không nuốt im lặng"
        assert any(x["loai"] == "nt_khac_phong" for x in ra), "các dấu hiệu còn lại vẫn phải chạy"
    finally:
        NT._so_tron = goc
    r = client.post("/api/v1/kiem-soat/quet", headers=login("cntt")).json()
    assert not r["loi_bo_kiem"]
