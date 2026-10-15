"""HD-Q2a — ĐẾM LƯỢT MỞ CỬA ĐỌC, chưa siết quyền của ai.

Đo được trên main 5b6a794 trước vòng này: hệ thống KHÔNG có nhật ký đọc. `audit_log` được gọi 432
chỗ, toàn thao tác GHI; cả nhóm đánh giá chỉ ghi đúng `ghi_danh_gia_ho`. Nên câu Chủ tịch cần —
«mỗi ngày mỗi vai mở bao nhiêu phiếu» — không có dữ liệu nào trả lời được. Vòng này dựng bộ đếm.

  A. Bộ đếm ghi đúng, và số phút khác số lượt.
  B. Bộ đếm KHÔNG được làm hỏng cửa đọc mà nó đang đếm.
  C. Bảng đếm là dữ liệu theo dõi người lao động — cửa đọc nó hẹp, và nó không tự đếm chính nó.
  D. Mọi cửa đã KHAI đều thật sự có chỗ đếm, và không có chỗ đếm nào mang tên cửa chưa khai.
  E. Vòng này KHÔNG lấy bớt quyền của ai.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_q2a.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_q2a.db"):
    os.remove("test_q2a.db")

import ast  # noqa: E402
import pathlib  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import dem_luot as DEM  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
TU, DEN = "2026-01-01", "2027-12-31"
ID: dict[str, int] = {}
# Tên mang mã đợt — bài học HD-DG2: tên chung thì hai bộ chạy cùng lượt sập ở bước dựng.
AI = {"tp_hd": "tp_hd_q2a", "chutich": "chutich_q2a", "nv_mkt": "nv_mkt_q2a",
      "nv_dh": "nv_dh_q2a", "ketoan": "ketoan_q2a"}


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import Booking, Tour, User
        from app.models.cskh import CareTicket
        from app.models.danh_gia import DanhGiaSauTour
        from app.models.hr import Employee
        with SessionLocal() as db:
            for vai, ten in AI.items():
                if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                    db.add(User(username=ten, full_name="Thử " + ten, role=vai,
                                department="Thử", password_hash=hash_password(MK)))
            db.commit()
            op = db.execute(select(User)).scalars().first()

            e = Employee(code="Q2A-A", full_name="HDV thử", department="huong_dan", position="hdv",
                         start_date=date(2024, 1, 1), card_no="Q2A-A", card_type="quoc_te",
                         card_expiry=date(2030, 1, 1), member_org=True,
                         contract_type="ctv", ctv_contract=True)
            db.add(e); db.commit()
            ID["hdv"] = e.id

            t = Tour(code="Q2A-T", name="Chuyến thử", tour_type="le_noi_dia", operator_id=op.id,
                     start_date=date(2026, 11, 1), end_date=date(2026, 11, 3))
            db.add(t); db.commit()
            b = Booking(code="Q2A-B", tour_id=t.id, customer_name="KhachQ2ARieng", customer_phone="0900000777",
                        pax=1, sales_id=op.id, created_by=op.id, request_id=0, source="thu")
            db.add(b); db.commit()
            care = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="KhachQ2ARieng",
                              customer_phone="0900000777", han_lien_he=date(2026, 11, 5))
            db.add(care); db.commit()
            for diem in (5, 1):
                db.add(DanhGiaSauTour(care_id=care.id, booking_id=b.id, tour_id=t.id,
                                      doi_tuong="hdv", doi_tuong_id=ID["hdv"], diem=diem,
                                      doi_tuong_ten="x", nguon="khach"))
            db.commit()
        yield


def _h(vai):
    r = client.post("/api/v1/auth/login", data={"username": AI[vai], "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _dong(vai_key, cua):
    """Một dòng trong bảng đếm, đọc bằng cửa thật của Chủ tịch."""
    r = client.get(f"/api/v1/danh-gia/dem-luot?tu={TU}&den={DEN}", headers=_h("chutich"))
    assert r.status_code == 200, r.text
    for d in r.json()["rows"]:
        if d["username"] == AI[vai_key] and d["cua"] == cua:
            return d
    return None


def _xoa_dem():
    from sqlalchemy import delete

    from app.db.session import SessionLocal
    from app.models.core import LuotDocCua
    with SessionLocal() as db:
        db.execute(delete(LuotDocCua)); db.commit()


# ═════════ A · bộ đếm ghi đúng ═════════

def test_a1_mot_luot_mo_bang_diem_duoc_ghi_lai():
    _xoa_dem()
    assert _dong("tp_hd", "bang_diem") is None, "chưa mở mà đã có dòng đếm"
    r = client.get(f"/api/v1/danh-gia/bang-diem/hdv?tu={TU}&den={DEN}", headers=_h("tp_hd"))
    assert r.status_code == 200, r.text
    d = _dong("tp_hd", "bang_diem")
    assert d is not None, "mở cửa rồi mà bảng đếm không có dòng nào"
    assert d["so_luot"] == 1 and d["so_ngay"] == 1
    assert d["role"] == "tp_hd"


def test_a2_ba_luot_trong_cung_mot_phut_ra_ba_luot_nhung_MOT_phut():
    """Màn hình tự nạp lại làm số lượt phồng lên. Số phút khác nhau là con số chống được chuyện đó."""
    _xoa_dem()
    for _ in range(3):
        assert client.get(f"/api/v1/danh-gia/bang-diem/hdv?tu={TU}&den={DEN}",
                          headers=_h("tp_hd")).status_code == 200
    d = _dong("tp_hd", "bang_diem")
    assert d["so_luot"] == 3, d
    assert d["so_phut"] == 1, "ba lượt trong cùng một phút phải ra ĐÚNG MỘT phút"


def test_a3_so_dong_bang_dung_so_dong_cua_tra_ve():
    _xoa_dem()
    r = client.get(f"/api/v1/danh-gia/bang-diem/hdv?tu={TU}&den={DEN}", headers=_h("tp_hd"))
    that = len(r.json().get("rows") or [])
    assert that > 0, "cảnh thử không có dòng nào thì ca này không đo được gì"
    assert _dong("tp_hd", "bang_diem")["so_dong"] == that


def test_a4_cham_soc_dem_SAU_khi_loc_chu_khong_dem_so_dong_truy_van_tra_ve():
    """Con số cần đo là «người này ĐỌC ĐƯỢC bao nhiêu phiếu», không phải «câu truy vấn trả bao nhiêu
    dòng trước khi lọc». Hai con số ấy khác nhau ngay khi người dùng bật một bộ lọc trên màn hình.

    Ca này cố ý bật `qua_han=1` — bộ lọc chạy SAU truy vấn trong mã nguồn — để hai con số tách hẳn
    ra. Bản đầu của ca này gọi cửa không kèm bộ lọc nào, nên hai con số luôn bằng nhau và ca mang
    tên «đếm sau khi lọc» chưa từng nhìn thấy một phép lọc nào.
    """
    _xoa_dem()
    tat_ca = client.get("/api/v1/cham-soc", headers=_h("nv_mkt"))
    assert tat_ca.status_code == 200 and len(tat_ca.json()) > 0
    _xoa_dem()
    loc = client.get("/api/v1/cham-soc?qua_han=1", headers=_h("nv_mkt"))
    assert loc.status_code == 200
    assert len(loc.json()) < len(tat_ca.json()), "bộ lọc không cắt bớt dòng nào thì ca này vô nghĩa"
    d = _dong("nv_mkt", "cham_soc")
    assert d["so_luot"] == 1 and d["so_dong"] == len(loc.json()), (d, len(loc.json()))


def test_a5_cua_chua_khai_thi_KHONG_dem_chu_khong_tu_dat_ten_cua_moi():
    _xoa_dem()

    class U:
        username, role = "ai_do", "chutich"

    assert DEM.ghi(U, "mot_cua_chua_khai", 5) is False
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import LuotDocCua
    with SessionLocal() as db:
        assert db.execute(select(LuotDocCua)).scalars().first() is None


# ═════════ B · bộ đếm không được làm hỏng cửa nó đang đếm ═════════

def test_b1_bo_dem_hong_thi_cua_doc_VAN_tra_du_du_lieu(monkeypatch):
    """Một cái máy đếm làm hỏng việc nó đang đếm là cái máy đếm tệ nhất."""
    _xoa_dem()

    def no_ra_loi():
        raise RuntimeError("csdl bộ đếm chết")

    monkeypatch.setattr("app.services.dem_luot.SessionLocal", no_ra_loi)
    r = client.get(f"/api/v1/danh-gia/bang-diem/hdv?tu={TU}&den={DEN}", headers=_h("tp_hd"))
    assert r.status_code == 200, r.text
    assert len(r.json().get("rows") or []) > 0, "cửa đọc trả rỗng khi bộ đếm hỏng"


# ═════════ C · cửa đọc bảng đếm ═════════

def test_c1_chi_bon_vai_doc_duoc_bang_dem():
    assert client.get("/api/v1/danh-gia/dem-luot", headers=_h("chutich")).status_code == 200
    for vai in ("tp_hd", "nv_mkt", "nv_dh", "ketoan"):
        r = client.get("/api/v1/danh-gia/dem-luot", headers=_h(vai))
        assert r.status_code == 403, f"{vai}: {r.status_code}"


def test_c2_cua_dem_KHONG_tu_dem_chinh_no():
    """Đếm chính mình thì con số nói về người đi đo, không nói về người bị đo."""
    _xoa_dem()
    for _ in range(3):
        assert client.get("/api/v1/danh-gia/dem-luot", headers=_h("chutich")).status_code == 200
    r = client.get(f"/api/v1/danh-gia/dem-luot?tu={TU}&den={DEN}", headers=_h("chutich"))
    assert r.json()["rows"] == [], r.json()["rows"]


def test_c3_bang_dem_khong_chua_mot_chu_nao_ve_khach():
    _xoa_dem()
    assert client.get("/api/v1/cham-soc", headers=_h("nv_mkt")).status_code == 200
    r = client.get(f"/api/v1/danh-gia/dem-luot?tu={TU}&den={DEN}", headers=_h("chutich"))
    cho_phep = {"role", "username", "cua", "cua_ten", "so_luot", "so_phut", "so_dong",
                "so_ngay", "la_robot", "luot_moi_ngay"}
    for d in r.json()["rows"]:
        assert set(d) == cho_phep, set(d) ^ cho_phep
    # Tên và số điện thoại khách trong cảnh thử là chuỗi riêng, không trùng nhãn cửa nào — nên
    # tìm thấy chúng trong bảng đếm nghĩa là bảng đếm đã rò dữ liệu khách ra ngoài.
    assert "KhachQ2ARieng" not in r.text and "0900000777" not in r.text


def test_c4_vai_robot_duoc_danh_dau_rieng():
    """Gộp lượt của robot vào lượt người là biến một con robot thành một phòng chăm chỉ."""
    _xoa_dem()
    from app.db.session import SessionLocal
    from app.models.core import LuotDocCua
    with SessionLocal() as db:
        db.add(LuotDocCua(ngay=date.today(), username="robot", role="robot_ks", cua="bang_diem",
                          so_luot=500, so_phut=400, phut_cuoi="08:00", so_dong=9000))
        db.commit()
    r = client.get(f"/api/v1/danh-gia/dem-luot?tu={TU}&den={DEN}", headers=_h("chutich"))
    rb = [d for d in r.json()["rows"] if d["username"] == "robot"]
    assert len(rb) == 1 and rb[0]["la_robot"] is True


def test_c5_trung_binh_chia_cho_SO_NGAY_CUA_KY_chu_khong_chia_cho_so_ngay_co_dung():
    """Chia cho số ngày có dùng thì người mở đúng một hôm vẫn ra «mỗi ngày một lượt»."""
    _xoa_dem()
    from app.db.session import SessionLocal
    from app.models.core import LuotDocCua
    with SessionLocal() as db:
        db.add(LuotDocCua(ngay=date(2026, 1, 5), username="x1", role="nv_mkt", cua="bang_diem",
                          so_luot=10, so_phut=10, phut_cuoi="08:00", so_dong=10))
        db.commit()
    r = client.get("/api/v1/danh-gia/dem-luot?tu=2026-01-01&den=2026-01-10",
                   headers=_h("chutich")).json()
    assert r["so_ngay_ky"] == 10
    d = [x for x in r["rows"] if x["username"] == "x1"][0]
    assert d["so_ngay"] == 1 and d["luot_moi_ngay"] == 1.0


# ═════════ D · khai đủ, không khai thừa ═════════

def _ten_cua_duoc_goi():
    goc = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
    ra = []
    for f in goc.glob("*.py"):
        cay = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "ghi"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "DEM"
                    and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)):
                ra.append(n.args[1].value)
    return ra


def test_d1_moi_cua_da_khai_deu_co_dung_mot_cho_dem():
    """Khai một cửa rồi quên đặt chỗ đếm thì bảng báo 0 lượt — và 0 lẫn với «không ai dùng»."""
    goi = _ten_cua_duoc_goi()
    for ten in DEM.CUA:
        assert goi.count(ten) == 1, f"cửa {ten!r} có {goi.count(ten)} chỗ đếm, phải đúng 1"


def test_d2_khong_co_cho_dem_nao_mang_ten_cua_chua_khai():
    for ten in _ten_cua_duoc_goi():
        assert ten in DEM.CUA, f"đếm vào cửa {ten!r} chưa khai trong DEM.CUA"


# ═════════ E · vòng này không lấy bớt quyền của ai ═════════

def test_e1_marketing_va_dieu_hanh_VAN_vao_duoc_nhu_truoc():
    """Đợt này chỉ ĐẾM. Việc siết là Đợt HD-Q2b, sau khi Chủ tịch nhìn con số thật."""
    for vai in ("nv_mkt", "nv_dh"):
        assert client.get(f"/api/v1/danh-gia/bang-diem/hdv?tu={TU}&den={DEN}",
                          headers=_h(vai)).status_code == 200
        assert client.get("/api/v1/cham-soc", headers=_h(vai)).status_code == 200
