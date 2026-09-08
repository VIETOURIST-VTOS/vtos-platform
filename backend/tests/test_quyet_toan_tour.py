"""V3 – bộ nạp quyết toán tour: nguồn số lớn nhất của công ty.

495 chuyến hai tháng 7–8/2026, 48.042.594.678 đ. Bộ test dựng lại đúng hình dạng tệp thật (mỗi điều
hành một sheet, thêm sheet khách lẻ, một sheet Tổng hợp) rồi canh sáu chỗ hỏng:

  1. Nạp cả sheet Tổng hợp → doanh thu cộng hai lần mà bảng vẫn cân.
  2. Ô giá vốn ghi 0 hiểu thành "0 đồng" → sổ báo lãi 100%. Trong tệp thật là 76 dòng, 2,65 tỷ.
  3. Trộn khách lẻ vào hàng đợi thiếu giá vốn → hàng đợi đầy dòng không ai sửa được, rồi không ai mở nó.
  4. Ngày kết thúc trước ngày khởi hành → chuyến rơi nhầm kỳ quyết toán. Tệp thật có 2 dòng như vậy.
  5. Điền tên người NẠP TỆP làm điều hành viên → mất dấu người chịu trách nhiệm về chuyến.
  6. Nạp lại cùng tệp → cộng đôi toàn bộ.

Tệp thật KHÔNG đưa vào kho mã: nó chứa 48 tỷ doanh thu và tên khách. Số của tệp thật được đối chiếu
bằng một lần chạy riêng, kết quả ghi trong nhật ký nạp.
"""
import io, os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_qttour.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
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


HDR = ["STT", "Mã tour", "Tên tour", "Ngày KH", "Ngày KT", "Doanh thu", "Giá vốn", "Lợi nhuận",
       "Trạng thái QT"]


def _wb(sheets: dict, tong_hop=True) -> bytes:
    """Dựng workbook đúng hình dạng tệp thật: tiêu đề ở hàng 3, dữ liệu từ hàng 4."""
    from openpyxl import Workbook
    wb = Workbook(); wb.remove(wb.active)
    if tong_hop:
        ws = wb.create_sheet("Tổng hợp")
        ws.append(["QUYẾT TOÁN TOUR THEO ĐIỀU HÀNH"]); ws.append([])
        ws.append(["STT", "Điều hành", "Số tour", "Doanh thu", "Giá vốn", "Lợi nhuận", "Tỷ suất"])
        ws.append([1, "NGUYỄN THỊ MAI", 2, 999_000_000, 888_000_000, 111_000_000, "11%"])
    for ten, rows in sheets.items():
        ws = wb.create_sheet(ten)
        ws.append([f"ĐIỀU HÀNH: {ten}"]); ws.append([])
        hdr = HDR + (["Sale"] if "khách lẻ" in ten.lower() else [])
        ws.append(hdr)
        for i, r in enumerate(rows, 1): ws.append([i] + list(r))
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def _tep(noi_dung: bytes, who="tp.dieuhanh"):
    return client.post("/api/v1/nap-du-lieu/kiem-tra-tep", headers=login(who),
                       files={"tep": ("quyet_toan.xlsx", io.BytesIO(noi_dung),
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                       data={"loai": "quyet_toan_tour"})


def _nap(rows, who="tp.dieuhanh", bo_qua=False):
    return client.post("/api/v1/nap-du-lieu/nap", headers=login(who),
                       json={"loai": "quyet_toan_tour", "rows": rows, "bo_qua_dong_loi": bo_qua,
                             "ten_tep": "quyet_toan.xlsx", "nguon": "nap_tep"})


DU = ("MICEDL.0001", "ĐÀ LẠT 3N2Đ", "17/07/2026", "19/07/2026", 100_000_000, 80_000_000, 20_000_000,
      "Đã quyết toán")
THIEU = ("MICEPT.0002", "PHAN THIẾT 2N1Đ", "12/07/2026", "13/07/2026", 60_000_000, 0, 60_000_000,
         "Đã quyết toán")
KLE = ("KLE130726", "gia hạn visa", "13/07/2026", "13/07/2026", 6_500_000, 0, 6_500_000,
       "Dự toán (chưa QT)", "LÊ THỊ UYỂN NHI")


def test_bo_qua_sheet_tong_hop(_startup):
    """Sheet Tổng hợp là số cộng lại. Nạp nó là cộng hai lần mà bảng vẫn cân – không ai nhìn ra."""
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU]})).json()
    assert d["so_dong"] == 1, d
    assert d["tong_doanh_thu"] == 100_000_000


def test_o_gia_von_bang_0_doc_thanh_chua_co_so(_startup):
    """Trong tệp thật là 76 dòng, 2,65 tỷ doanh thu. Hiểu 0 là '0 đồng' thì sổ báo lãi 100%."""
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, THIEU]})).json()
    dong = {x["ma_tour"]: x for x in d["dong"]}
    assert dong["MICEDL.0001"]["gia_von"] == 80_000_000
    assert dong["MICEPT.0002"]["gia_von"] is None, "0 phải đọc thành RỖNG"
    assert d["thieu_gia_von_tour"] == 1


def test_khach_le_khong_tron_vao_hang_doi_thieu_gia_von(_startup):
    """60 trong 76 dòng thiếu giá vốn của tệp thật là khách lẻ – bảo lưu do hủy tour, gia hạn visa, vé.
    Trộn chung thì hàng đợi lúc nào cũng đầy dòng không ai sửa được, và người ta thôi mở nó."""
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, THIEU], "Khách lẻ (Sale)": [KLE]})).json()
    assert d["thieu_gia_von_tour"] == 1 and d["thieu_gia_von_khach_le"] == 1
    kle = next(x for x in d["dong"] if x["ma_tour"] == "KLE130726")
    assert kle["loai"] == "khach_le" and kle["sale"] == "LÊ THỊ UYỂN NHI"


def test_ngay_ket_thuc_truoc_ngay_khoi_hanh_bi_chan(_startup):
    """Ngày kết thúc quyết định chuyến thuộc kỳ nào – sai ngày là sai kỳ quyết toán. Tệp thật T7–T8 có
    đúng hai dòng như vậy, tổng 375.302.000 đ."""
    xau = ("MICEVT.0003", "VŨNG TÀU", "23/07/2026", "22/07/2026", 296_342_000, 268_369_722, 0,
           "Đã quyết toán")
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, xau]})).json()
    assert d["dong_loi"] == 1
    assert "Ngày kết thúc trước ngày khởi hành" in next(
        x for x in d["dong"] if x["ma_tour"] == "MICEVT.0003")["loi"]


def test_co_dong_loi_thi_khong_nap_gi_ca(_startup):
    xau = ("MICEVT.0004", "VŨNG TÀU", "23/07/2026", "22/07/2026", 10_000_000, 8_000_000, 0, "Đã quyết toán")
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, xau]})).json()
    r = _nap(d["rows"])
    assert r.status_code == 201 and r.json()["da_nap"] == 0
    assert "KHÔNG nạp gì cả" in r.json()["message"]


def test_nap_that_va_hai_hang_doi_tach_rieng(_startup):
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, THIEU], "Khách lẻ (Sale)": [KLE]})).json()
    r = _nap(d["rows"])
    assert r.status_code == 201 and r.json()["da_nap"] == 3, r.text
    t = client.get("/api/v1/quyet-toan-tour/tong-hop", headers=login("tp.dieuhanh")).json()
    assert t["hang_doi_thieu_gia_von"]["so_don"] == 1
    assert t["khach_le_cho_phan_loai"]["so_don"] == 1
    assert t["doanh_thu"] == 166_500_000 and t["gia_von"] == 80_000_000


def test_nap_lai_cung_tep_khong_cong_doi(_startup):
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU, THIEU], "Khách lẻ (Sale)": [KLE]})).json()
    r = _nap(d["rows"])
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 3


def test_khong_dien_ten_nguoi_nap_lam_dieu_hanh(_startup):
    """Người nạp tệp không phải người chịu trách nhiệm về chuyến. Tra không ra thì ghi nguyên văn và
    đánh dấu chưa ánh xạ, không mượn tạm tên tài khoản đang đăng nhập."""
    from app.db.session import SessionLocal
    from app.models.quyet_toan import TourSettlement
    from sqlalchemy import select
    with SessionLocal() as db:
        s = db.execute(select(TourSettlement).where(
            TourSettlement.ma_tour == "MICEDL.0001")).scalars().first()
        assert s.dieu_hanh == "NGUYỄN THỊ MAI"
        assert s.boi == "tp.dieuhanh" and s.dieu_hanh != s.boi


def test_loi_nhuan_khong_bang_doanh_thu_khi_chua_co_gia_von(_startup):
    from app.db.session import SessionLocal
    from app.models.quyet_toan import TourSettlement
    from sqlalchemy import select
    with SessionLocal() as db:
        s = db.execute(select(TourSettlement).where(
            TourSettlement.ma_tour == "MICEPT.0002")).scalars().first()
        assert s.gia_von is None and s.loi_nhuan() is None


def test_phan_loai_bao_luu_phai_co_han(_startup):
    """Bảo lưu không hạn là khoản nằm lại mãi ở trạng thái chờ, và tiền khách đã nộp không bao giờ được
    kết luận là doanh thu hay phải trả lại."""
    ds = client.get("/api/v1/quyet-toan-tour?cho_phan_loai=true", headers=login("tp.dieuhanh")).json()
    sid = next(x["id"] for x in ds if x["ma_tour"] == "KLE130726")
    r = client.post(f"/api/v1/quyet-toan-tour/{sid}/phan-loai", headers=login("tp.dieuhanh"),
                    json={"phan_loai": "bao_luu_huy_tour"})
    assert r.status_code == 422 and "phải có HẠN" in r.json()["detail"]
    r = client.post(f"/api/v1/quyet-toan-tour/{sid}/phan-loai", headers=login("tp.dieuhanh"),
                    json={"phan_loai": "bao_luu_huy_tour", "han_bao_luu": "2026-12-31",
                          "ghi_chu": "khách hủy tour Nhật, giữ tiền"})
    assert r.status_code == 200
    t = client.get("/api/v1/quyet-toan-tour/tong-hop", headers=login("tp.dieuhanh")).json()
    assert t["khach_le_cho_phan_loai"]["so_don"] == 0


def test_phan_loai_chi_phi_noi_bo_giu_lai_dong_chu_khong_xoa(_startup):
    """Vé công tác ban lãnh đạo ghi nhầm thành doanh thu khách lẻ: đánh dấu, không xóa. Xóa thì tháng
    sau nạp lại nó quay về."""
    noi_bo = ("KLE100826_2", "VÉ CÔNG TÁC BAN LÃNH ĐẠO", "10/08/2026", "10/08/2026", 93_390_000, 0,
              93_390_000, "Dự toán (chưa QT)", "LÊ THỊ DIỄM TRANG")
    d = _tep(_wb({"Khách lẻ (Sale)": [noi_bo]})).json()
    _nap(d["rows"])
    ds = client.get("/api/v1/quyet-toan-tour?cho_phan_loai=true", headers=login("tp.dieuhanh")).json()
    sid = next(x["id"] for x in ds if x["ma_tour"] == "KLE100826_2")
    r = client.post(f"/api/v1/quyet-toan-tour/{sid}/phan-loai", headers=login("tp.dieuhanh"),
                    json={"phan_loai": "chi_phi_noi_bo", "ghi_chu": "vé công tác BLĐ – điều chỉnh"})
    assert r.status_code == 200 and r.json()["phan_loai"] == "chi_phi_noi_bo"
    ds2 = client.get("/api/v1/quyet-toan-tour", headers=login("tp.dieuhanh")).json()
    assert any(x["ma_tour"] == "KLE100826_2" for x in ds2), "dòng phải còn, chỉ đổi phân loại"


def test_vai_tro_ngoai_dieu_hanh_khong_nap_duoc(_startup):
    d = _tep(_wb({"NGUYỄN THỊ MAI": [DU]}), who="tp.dieuhanh").json()
    r = _nap(d["rows"], who="kd.hoa")
    assert r.status_code == 403
