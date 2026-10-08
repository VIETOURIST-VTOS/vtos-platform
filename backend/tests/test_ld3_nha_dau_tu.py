"""Đợt D3 — quan hệ nhà đầu tư: danh bạ, sổ tiếp xúc, sổ cấp quyền xem hồ sơ.

  A. Không tự khai thêm quyền; bên trong còn hẹp hơn (che dữ liệu cá nhân).
  B. Ba bảng bắt đầu rỗng, và KHÔNG có cột sở hữu cổ phần.
  C. Lưu email/điện thoại phải có căn cứ thu thập (Nghị định 13/2023).
  D. Tiết lộ chọn lọc: đánh dấu có nói thông tin chưa công bố thì phải ghi đã nói gì, và phải nối
     tới bản công bố ĐÃ công bố.
  E. Cấp quyền xem hồ sơ chưa công bố phải có cam kết bảo mật có căn cứ.
  F. Cấp KHÔNG thời hạn có trạng thái riêng, không trộn vào "đang hiệu lực".
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_ld3.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ld3.db"):
    os.remove("test_ld3.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
P = "/api/v1/ir-phap-che"


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _lien_he(ten="Quỹ ABC", **kw):
    body = {"ten": ten, "to_chuc": "ABC Capital", "loai": "quy",
            "email": "ir@abccapital.example", "dien_thoai": "0900000111",
            "can_cu_thu_thap": "Danh thiếp nhận tại ĐHĐCĐ thường niên 2026", **kw}
    r = client.post(f"{P}/lien-he", json=body, headers=login("chutich"))
    assert r.status_code == 201, r.text
    return r.json()["lien_he"]["id"]


# ───────────────── A · phạm vi quyền ─────────────────
def test_a1_khong_tu_khai_them_lat_quyen():
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/ir-phap-che"] == ("/api/v1/ir-phap-che",)
    from app.api.v1.nha_dau_tu import router
    assert router.prefix == "/api/v1/ir-phap-che"


def test_a2_bks_cntt_doc_ma_khong_ghi():
    r = client.post(f"{P}/lien-he", json={"ten": "x"}, headers=login("cntt"))
    assert r.status_code == 403


def test_a3_che_du_lieu_ca_nhan_voi_vai_khong_can():
    """Thu hẹp, không nới: BKS cần biết đã tiếp xúc với ai, không cần số điện thoại của họ."""
    _lien_he("Quỹ che thử")
    r = client.get(f"{P}/nha-dau-tu", headers=login("bks"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["lien_he"]["da_che"] is True
    row = [x for x in d["lien_he"]["rows"] if x["ten"] == "Quỹ che thử"][0]
    assert "@" in row["email"] and "***" in row["email"]
    assert row["dien_thoai"].startswith("***")
    assert "abccapital" in row["email"], "che để không liên lạc được, vẫn nhận ra được tổ chức"

    r2 = client.get(f"{P}/nha-dau-tu", headers=login("chutich"))
    row2 = [x for x in r2.json()["lien_he"]["rows"] if x["ten"] == "Quỹ che thử"][0]
    assert row2["dien_thoai"] == "0900000111" and row2["da_che"] is False


# ───────────────── B · ba bảng rỗng, không có cột sở hữu ─────────────────
def test_b1_khong_co_cot_so_huu_co_phan():
    from app.models.nha_dau_tu import LienHeNhaDauTu
    cot = set(LienHeNhaDauTu.__table__.c.keys())
    for xau in ("so_co_phan", "co_phan", "ty_le_so_huu", "so_huu"):
        assert xau not in cot, "sở hữu là dữ liệu của sổ cổ đông – chép tay vào đây là tạo con số thứ hai"


def test_b2_ba_bang_khong_nap_san():
    from app.db.session import SessionLocal
    from app.models.nha_dau_tu import QuyenTruyCapHoSo, TuongTacNhaDauTu
    with SessionLocal() as db:
        # LienHeNhaDauTu đã có dòng do chính phép thử này tạo; hai bảng kia chưa ai động.
        assert db.query(TuongTacNhaDauTu).count() == 0
        assert db.query(QuyenTruyCapHoSo).count() == 0


# ───────────────── C · căn cứ thu thập dữ liệu cá nhân ─────────────────
def test_c1_co_email_ma_khong_co_can_cu_thi_bi_chan():
    r = client.post(f"{P}/lien-he",
                    json={"ten": "Ông A", "email": "a@example.com", "can_cu_thu_thap": "  "},
                    headers=login("chutich"))
    assert r.status_code == 422
    assert "CĂN CỨ THU THẬP" in r.json()["detail"]


def test_c2_khong_luu_lien_lac_thi_khong_doi_can_cu():
    r = client.post(f"{P}/lien-he", json={"ten": "Ông B", "to_chuc": "B Corp", "loai": "co_dong"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text


# ───────────────── D · tiết lộ chọn lọc ─────────────────
def test_d1_danh_dau_co_tiet_lo_ma_khong_ghi_noi_gi_thi_bi_chan():
    lid = _lien_he("Quỹ D1")
    r = client.post(f"{P}/tiep-xuc",
                    json={"lien_he_id": lid, "ngay": str(date.today()), "hinh_thuc": "gap",
                          "co_thong_tin_chua_cong_bo": True, "thong_tin_da_tiet_lo": ""},
                    headers=login("chutich"))
    assert r.status_code == 422


def test_d2_co_tiet_lo_chua_noi_cong_bo_thi_hien_la_viec_phai_xu_ly():
    lid = _lien_he("Quỹ D2")
    r = client.post(f"{P}/tiep-xuc",
                    json={"lien_he_id": lid, "ngay": str(date.today()), "hinh_thuc": "goi",
                          "co_thong_tin_chua_cong_bo": True,
                          "thong_tin_da_tiet_lo": "Doanh thu quý 3 ước đạt"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    assert r.json()["tiep_xuc"]["chua_xu_ly_tiet_lo"] is True
    d = client.get(f"{P}/nha-dau-tu", headers=login("chutich")).json()
    assert d["tiep_xuc"]["so_chua_xu_ly_tiet_lo"] >= 1


def test_d3_khong_noi_toi_mot_ban_ghi_chua_cong_bo():
    """Nối vào một bản ghi chưa công bố là nói rằng việc đã xong trong khi thông tin chưa ra."""
    h = login("chutich")
    client.post(f"{P}/nghia-vu", json={"ma": "ND3-NV", "ten": "Công bố bất thường",
                                       "can_cu": "Do Pháp chế khai", "chu_ky": "su_kien",
                                       "han_sau_ngay": 1}, headers=h)
    nv = [n for n in client.get(f"{P}/nghia-vu", headers=h).json()["rows"]
          if n["ma"] == "ND3-NV"][0]
    bg = client.post(f"{P}/ban-ghi", json={"nghia_vu_id": nv["id"], "ky": "ND3-K1",
                                           "moc_phat_sinh": str(date.today())},
                     headers=h).json()["ban_ghi"]
    lid = _lien_he("Quỹ D3")
    tt = client.post(f"{P}/tiep-xuc",
                     json={"lien_he_id": lid, "ngay": str(date.today()),
                           "co_thong_tin_chua_cong_bo": True,
                           "thong_tin_da_tiet_lo": "Kế hoạch phát hành"},
                     headers=h).json()["tiep_xuc"]
    r = client.post(f"{P}/tiep-xuc/{tt['id']}/noi-cong-bo",
                    json={"ban_ghi_cong_bo_id": bg["id"]}, headers=h)
    assert r.status_code == 422
    assert "CHƯA công bố" in r.json()["detail"]

    # công bố xong thì nối được
    client.post(f"{P}/ban-ghi/{bg['id']}/da-cong-bo", json={"noi_cong_bo": "HNX"}, headers=h)
    r2 = client.post(f"{P}/tiep-xuc/{tt['id']}/noi-cong-bo",
                     json={"ban_ghi_cong_bo_id": bg["id"]}, headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["tiep_xuc"]["chua_xu_ly_tiet_lo"] is False


# ───────────────── E · cấp quyền xem hồ sơ ─────────────────
def test_e1_ho_so_chua_cong_bo_phai_co_cam_ket_bao_mat():
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "BCTC quý 3 bản nháp", "nguoi_duoc_cap": "Ông C",
                          "ly_do": "Thẩm định đầu tư", "ho_so_chua_cong_bo": True,
                          "cam_ket_bao_mat": False, "tu_ngay": str(date.today())},
                    headers=login("chutich"))
    assert r.status_code == 422
    assert "CAM KẾT BẢO MẬT" in r.json()["detail"]


def test_e2_cam_ket_khong_co_can_cu_cung_bi_chan():
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "BCTC quý 3 bản nháp", "nguoi_duoc_cap": "Ông C",
                          "ly_do": "Thẩm định đầu tư", "ho_so_chua_cong_bo": True,
                          "cam_ket_bao_mat": True, "can_cu_cam_ket": "",
                          "tu_ngay": str(date.today())},
                    headers=login("chutich"))
    assert r.status_code == 422


def test_e3_khong_co_ly_do_thi_khong_cap():
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "Hồ sơ X", "nguoi_duoc_cap": "Ông D", "ly_do": "",
                          "ho_so_chua_cong_bo": False, "tu_ngay": str(date.today())},
                    headers=login("chutich"))
    assert r.status_code == 422
    assert "LÝ DO" in r.json()["detail"]


# ───────────────── F · cấp không thời hạn ─────────────────
def test_f1_khong_co_ngay_het_han_co_trang_thai_rieng():
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "Phòng dữ liệu thẩm định", "nguoi_duoc_cap": "Ông E",
                          "ly_do": "Due diligence", "ho_so_chua_cong_bo": True,
                          "cam_ket_bao_mat": True, "can_cu_cam_ket": "NDA số 07/2026 ký 01/10",
                          "tu_ngay": str(date.today())},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    assert r.json()["quyen"]["trang_thai"] == "khong_co_han", \
        "quyền không có ngày hết là quyền sẽ còn sống sau khi lý do cấp nó đã chết"


def test_f2_co_han_thi_dang_hieu_luc_va_dem_duoc_ngay_con_lai():
    den = date.today() + timedelta(days=3)
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "Phòng dữ liệu 2", "nguoi_duoc_cap": "Ông F",
                          "ly_do": "Due diligence", "ho_so_chua_cong_bo": True,
                          "cam_ket_bao_mat": True, "can_cu_cam_ket": "NDA số 08/2026",
                          "tu_ngay": str(date.today()), "den_ngay": str(den)},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    d = r.json()["quyen"]
    assert d["trang_thai"] == "dang_hieu_luc" and d["con_lai_ngay"] == 3 and d["sap_het_han"] is True


def test_f3_thu_hoi_mot_lan_va_khong_thu_hoi_lai():
    r = client.post(f"{P}/quyen-ho-so",
                    json={"ho_so": "Phòng dữ liệu 3", "nguoi_duoc_cap": "Ông G",
                          "ly_do": "Due diligence", "ho_so_chua_cong_bo": False,
                          "tu_ngay": str(date.today())},
                    headers=login("chutich"))
    qid = r.json()["quyen"]["id"]
    t1 = client.post(f"{P}/quyen-ho-so/{qid}/thu-hoi", headers=login("chutich"))
    assert t1.status_code == 200 and t1.json()["quyen"]["trang_thai"] == "da_thu_hoi"
    t2 = client.post(f"{P}/quyen-ho-so/{qid}/thu-hoi", headers=login("chutich"))
    assert t2.status_code == 422


def test_f4_bang_dem_dung_so_khong_co_han():
    d = client.get(f"{P}/nha-dau-tu", headers=login("chutich")).json()
    assert d["quyen"]["so_khong_co_han"] == len(
        [x for x in d["quyen"]["rows"] if x["trang_thai"] == "khong_co_han"])
    assert d["quyen"]["so_khong_co_han"] >= 1


# ───────────────── G · ba bảng mới đều có cửa nhập ─────────────────
def test_g1_ba_bang_moi_deu_da_khai_cua():
    from app.services.ks_cua_nhap import CUA_TAY, MAY_SINH
    for t in ("lien_he_nha_dau_tu", "tuong_tac_nha_dau_tu", "quyen_truy_cap_ho_so"):
        assert t in CUA_TAY or t in MAY_SINH, f"{t} chưa khai cửa nhập"
