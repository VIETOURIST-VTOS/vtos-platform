"""V1 – khuôn ba cửa nhập liệu: nhập tay, tải tệp, ảnh do AI đọc, cùng MỘT bộ kiểm.

Lệnh giao việc 08/9/2026. Quyết định của Chủ tịch bỏ khâu trưởng phòng duyệt từng dòng – nhập là dùng
luôn. Bỏ một lớp chặn có thật thì lớp còn lại phải chặt hơn chứ không lỏng hơn, nên bộ test này canh
đúng chỗ đó: KHÔNG có cửa nào đi vòng được bộ kiểm.

Bảy điều nó giữ:
  1. Mọi bộ nạp khai đủ: bảng đích và phòng ban sở hữu. Thiếu hai thứ đó thì lúc một con số bị nghi
     ngờ, không ai trả lời được "nó nằm ở bảng nào, phòng nào chịu trách nhiệm".
  2. Nhập tay và tải tệp cho CÙNG một kết quả trên cùng một dòng dữ liệu.
  3. Kỳ đã KHÓA SỔ thì cả hai cửa đều chặn – kỳ khóa là chốt chặn cuối khi đã bỏ khâu duyệt.
  4. Ô trống là CHƯA CÓ SỐ, không bị thay bằng 0.
  5. Số điền sẵn từ ảnh không có đường riêng: nó đi đúng cửa nhập tay và bắt buộc ghi tên tác vụ đã đọc.
  6. Khoảng hợp lệ và danh sách chọn khai ở cột, áp cho mọi cửa.
  7. Nhập tay hai lần cùng một khóa không thành hai bản ghi.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_bacua.db")
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
        global client; client = c
        # Tài khoản GĐ điều hành đội xe – bản demo chưa có, mà đây là vai trò sở hữu bộ nạp chuyến xe.
        from app.db.session import SessionLocal
        from app.models.core import User
        from app.core.security import hash_password
        from sqlalchemy import select
        with SessionLocal() as db:
            if db.execute(select(User).where(User.username == "gd.doixe")).scalars().first() is None:
                db.add(User(username="gd.doixe", full_name="GĐ điều hành đội xe", role="gd_doi_xe",
                            department="Đội xe", password_hash=hash_password("123456")))
                db.commit()
        yield


def _chuyen(ma, ngay_di="2026-08-05", **kw):
    return {"Mã phiếu gốc": ma, "Biển số xe": "50F-009.60", "Tour / khách hàng": "Tuyến thử",
            "Ngày đi": ngay_di, "Ngày về": "2026-08-07", "Doanh thu": "12.000.000",
            "Tiền dầu": "4.000.000", "Số lít": "450", **kw}


def mot_dong(row, loai="chuyen_xe", who="gd.doixe", **kw):
    return client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=login(who),
                       json={"loai": loai, "row": row, **kw})


# ---------------------------------------------------------------- 1. Khai báo
def test_moi_bo_nap_khai_du_bang_dich_va_phong_ban(_startup):
    """Thiếu hai thứ này thì lúc một con số bị nghi ngờ không ai trả lời được nó nằm đâu, ai chịu."""
    from app.services import intake as I
    from app.services.nhap_lieu import khai_bao_du
    thieu = {k: khai_bao_du(v) for k, v in I.BO_NAP.items() if khai_bao_du(v)}
    assert not thieu, f"bộ nạp khai thiếu: {thieu}"


def test_api_cong_bo_du_de_sinh_bieu_nhap_tay(_startup):
    """Biểu nhập tay sinh TỪ khai báo cột – khai một lần dùng cho cả ba cửa, không viết biểu riêng."""
    d = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login("ketoan")).json()
    assert set(d["cua"]) == {"nhap_tay", "nap_tep", "doc_anh"}
    assert d["kieu_cot"]
    for b in d["bo_nap"]:
        assert b["bang_dich"] and b["phong_ban"]
        assert all(c.get("kieu") in d["kieu_cot"] for c in b["cot"]), b["ma"]


# ---------------------------------------------------------------- 2. Hai cửa, một bộ kiểm
def test_nhap_tay_va_tai_tep_cho_cung_ket_qua(_startup):
    r1 = mot_dong(_chuyen("BC-TAY-01"))
    assert r1.status_code == 201 and r1.json()["da_ghi"] is True, r1.text
    r2 = client.post("/api/v1/nap-du-lieu/nap", headers=login("gd.doixe"),
                     json={"loai": "chuyen_xe", "rows": [_chuyen("BC-TEP-01")]})
    assert r2.status_code == 201 and r2.json()["da_nap"] == 1


def test_cung_mot_loi_bao_giong_nhau_o_ca_hai_cua(_startup):
    """Cửa nào tự kiểm riêng là cửa đó sẽ lọt – nên hai cửa phải nói cùng một câu."""
    xau = _chuyen("BC-XAU-01", **{"Biển số xe": ""})
    r1 = mot_dong(xau)
    assert r1.status_code == 201 and r1.json()["da_ghi"] is False
    r2 = client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login("gd.doixe"),
                     json={"loai": "chuyen_xe", "rows": [xau]})
    assert r2.json()["dong"][0]["loi"] == r1.json()["loi"]


# ---------------------------------------------------------------- 3. Kỳ khóa
def test_ky_da_khoa_thi_ca_hai_cua_deu_chan(_startup):
    """Kỳ khóa là chốt chặn CUỐI khi đã bỏ khâu duyệt từng dòng. Nếu nó không chặn thì số của một kỳ
    đã phát hành báo cáo vẫn đổi được, và bản đã gửi ra ngoài không dựng lại được từ dữ liệu."""
    from app.db.session import SessionLocal
    from app.models.accounting import PeriodLock
    with SessionLocal() as db:
        if db.get(PeriodLock, "2026-05") is None:
            db.add(PeriodLock(period="2026-05", locked_by="ketoan", note="thử")); db.commit()
    row = _chuyen("BC-KHOA-01", ngay_di="2026-05-10")
    row["Ngày về"] = "2026-05-12"
    r = mot_dong(row)
    assert r.json()["da_ghi"] is False
    assert any("ĐÃ KHÓA SỔ" in x for x in r.json()["loi"]), r.json()["loi"]
    r2 = client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login("gd.doixe"),
                     json={"loai": "chuyen_xe", "rows": [row]})
    assert any("ĐÃ KHÓA SỔ" in x for x in r2.json()["dong"][0]["loi"])


def test_ngay_o_tuong_lai_bi_tu_choi(_startup):
    row = _chuyen("BC-MAI-01", ngay_di="2099-01-01"); row["Ngày về"] = "2099-01-02"
    r = mot_dong(row)
    assert r.json()["da_ghi"] is False and any("tương lai" in x for x in r.json()["loi"])


# ---------------------------------------------------------------- 4. Trống ≠ 0
def test_o_trong_khong_bi_thay_bang_0(_startup):
    """76 dòng quyết toán T7–T8 không có giá vốn; ghi thẳng 0 là sổ báo lãi 100% trên 2,65 tỷ."""
    row = _chuyen("BC-TRONG-01"); row.pop("Tiền dầu"); row.pop("Số lít")
    r = mot_dong(row)
    assert r.json()["da_ghi"] is True, r.text
    ds = client.get("/api/v1/fleet/lai-lo/theo-chuyen?ky=2026-08", headers=login("ketoan")).json()
    d = next(x for x in ds if x["ma_phieu"] == "BC-TRONG-01")
    assert d["km_moi_lit"] is None and d["so_lit"] is None


# ---------------------------------------------------------------- 5. Cửa ảnh
def test_so_tu_anh_di_dung_cua_nhap_tay_va_phai_ghi_ten_tac_vu(_startup):
    """Ảnh không bao giờ tự thành sổ: giữa ảnh và bảng luôn có một lần bấm của người, và phải truy được
    con số đó do máy nào đọc."""
    r = mot_dong(_chuyen("BC-ANH-01"), cua="doc_anh")
    assert r.status_code == 422 and "tên tác vụ" in r.json()["detail"]
    r = mot_dong(_chuyen("BC-ANH-01"), cua="doc_anh", tac_nhan="doc_chung_tu_v1")
    assert r.status_code == 201 and r.json()["da_ghi"] is True, r.text
    ls = client.get("/api/v1/nap-du-lieu/lich-su?loai=chuyen_xe", headers=login("ketoan")).json()
    d = next(x for x in ls if x["nguon"] == "doc_anh")
    assert d["tac_nhan"] == "doc_chung_tu_v1"


def test_cua_la_thi_tu_choi(_startup):
    r = mot_dong(_chuyen("BC-LA-01"), cua="cua_sau")
    assert r.status_code == 422


# ---------------------------------------------------------------- 6-7. Khoảng, chọn, chống trùng
def test_nhap_tay_hai_lan_khong_thanh_hai_ban(_startup):
    r = mot_dong(_chuyen("BC-TAY-01"))
    assert r.json()["da_ghi"] is False and r.json()["da_co"] == "BC-TAY-01"
    assert "không ghi thêm bản thứ hai" in r.json()["message"]


def test_khoang_hop_le_khai_o_cot_ap_cho_moi_cua(_startup):
    """Cột khai min/max thì cả ba cửa cùng chặn, không phải nhắc lại ở từng màn hình."""
    from app.services import intake as I
    from app.services.nhap_lieu import kiem_dong
    from app.db.session import SessionLocal
    bo = dict(I.BO_NAP["chuyen_xe"])
    bo["cot"] = [I._c("so_lit", "Số lít", kieu="so", min=0, max=2000)]
    with SessionLocal() as db:
        loi, _ = kiem_dong(db, bo, {"so_lit": 5000})
        assert loi and "lớn hơn mức cho phép" in loi[0]
        assert kiem_dong(db, bo, {"so_lit": 450})[0] == []


def test_vai_tro_khong_thuoc_phong_thi_khong_nhap_tay_duoc(_startup):
    r = mot_dong(_chuyen("BC-QUYEN-01"), who="kd.hoa")
    assert r.status_code == 403 and "thuộc phòng khác" in r.json()["detail"]
