"""Đợt D2 — bàn làm việc Pháp chế: yêu cầu, rà soát hợp đồng, sổ chữ ký, xác nhận chủ số liệu.

  A. Không tự khai thêm quyền: cửa mới nằm trong ĐÚNG nhóm API đã khai của D1.
  B. Bốn bảng bắt đầu RỖNG.
  C. Đóng việc phải có kết quả viết ra.
  D. "Đạt có điều kiện" phải có điều kiện; mức rủi ro lạ bị chặn ngay.
  E. Chữ ký phải có căn cứ thẩm quyền.
  F. Xác nhận chủ số liệu chặn cửa "đã công bố" — và chỉ chặn đúng chỗ đã hỏi.
  G. K2: giá trị hợp đồng rỗng đi ra ngoài vẫn là rỗng, không thành 0.
  H. Tuổi việc tính lúc đọc, không lưu thành cột.
"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_ld2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ld2.db"):
    os.remove("test_ld2.db")

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


def _mo_yc(tieu_de="Rà soát hợp đồng thuê xe 2026", loai="ra_soat_hop_dong", **kw):
    body = {"loai": loai, "tieu_de": tieu_de, "phong_gui": "Điều hành",
            "nguoi_gui": "Trưởng phòng ĐH", **kw}
    r = client.post(f"{P}/yeu-cau", json=body, headers=login("chutich"))
    assert r.status_code == 201, r.text
    return r.json()["yeu_cau"]["id"]


# ───────────────── A · không tự khai thêm quyền ─────────────────
def test_a1_cua_moi_nam_trong_nhom_api_da_khai():
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/ir-phap-che"] == ("/api/v1/ir-phap-che",), \
        "đợt này KHÔNG mở thêm lát quyền nào – cửa mới đi vào đúng nhóm cũ"
    from app.api.v1.phap_che_viec import router
    assert router.prefix == "/api/v1/ir-phap-che"


def test_a2_bks_va_cntt_doc_ma_khong_ghi():
    from app.api.v1.phap_che_viec import GHI, XEM
    assert "bks" in XEM and "bks" not in GHI
    assert "cntt" in XEM and "cntt" not in GHI
    r = client.post(f"{P}/yeu-cau", json={"loai": "khac", "tieu_de": "x"}, headers=login("bks"))
    assert r.status_code == 403


def test_a3_vai_phong_ban_chua_co_cua_gui_va_viec_ay_duoc_noi_ra():
    """Chưa mở cửa cho phòng ban tự gửi — và đó là việc CÒN THIẾU, có ghi ra ở /meta-viec."""
    r = client.get(f"{P}/meta-viec", headers=login("chutich"))
    assert r.status_code == 200
    assert "con_thieu" in r.json() and r.json()["con_thieu"]


# ───────────────── B · bốn bảng bắt đầu rỗng ─────────────────
def test_b1_bon_bang_bat_dau_rong():
    from app.db.session import SessionLocal
    from app.models.phap_che_viec import (BanGhiChuKy, RaSoatHopDong, XacNhanChuSoLieu,
                                          YeuCauPhapChe)
    with SessionLocal() as db:
        for M in (YeuCauPhapChe, RaSoatHopDong, BanGhiChuKy, XacNhanChuSoLieu):
            assert db.query(M).count() == 0, f"{M.__tablename__} phải bắt đầu rỗng"


# ───────────────── C · đóng việc phải có kết quả ─────────────────
def test_c1_dong_viec_khong_ket_qua_bi_chan():
    yid = _mo_yc("Ý kiến về điều khoản phạt", loai="y_kien_phap_ly")
    r = client.post(f"{P}/yeu-cau/{yid}/dong", json={"trang_thai": "xong", "ket_qua": "  "},
                    headers=login("chutich"))
    assert r.status_code == 422
    assert "KẾT QUẢ" in r.json()["detail"]


def test_c2_dong_viec_co_ket_qua_thi_duoc_va_khong_dong_lai_lan_hai():
    yid = _mo_yc("Soạn quy chế công bố", loai="soan_thao")
    client.post(f"{P}/yeu-cau/{yid}/nhan", headers=login("chutich"))
    r = client.post(f"{P}/yeu-cau/{yid}/dong",
                    json={"trang_thai": "xong", "ket_qua": "Đã gửi bản thảo ngày 09/10"},
                    headers=login("chutich"))
    assert r.status_code == 200, r.text
    assert r.json()["yeu_cau"]["trang_thai"] == "xong"
    r2 = client.post(f"{P}/yeu-cau/{yid}/dong",
                     json={"trang_thai": "xong", "ket_qua": "lần hai"}, headers=login("chutich"))
    assert r2.status_code == 422


def test_c3_cho_bo_sung_phai_noi_can_bo_sung_gi():
    yid = _mo_yc("Hợp đồng thiếu phụ lục")
    r = client.post(f"{P}/yeu-cau/{yid}/cho-bo-sung", json={"can_bo_sung": ""},
                    headers=login("chutich"))
    assert r.status_code == 422
    r2 = client.post(f"{P}/yeu-cau/{yid}/cho-bo-sung",
                     json={"can_bo_sung": "Thiếu phụ lục giá"}, headers=login("chutich"))
    assert r2.status_code == 200
    assert r2.json()["yeu_cau"]["trang_thai"] == "cho_bo_sung"


# ───────────────── D · rà soát hợp đồng ─────────────────
def test_d1_dat_co_dieu_kien_phai_co_dieu_kien():
    yid = _mo_yc("Hợp đồng vận chuyển A")
    r = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                   json={"so_hop_dong": "HD-01", "doi_tac": "Nhà xe A",
                         "ket_luan": "dat_co_dieu_kien", "dieu_kien": ""},
                   headers=login("chutich"))
    assert r.status_code == 422
    assert "ĐIỀU KIỆN" in r.json()["detail"]


def test_d2_co_dieu_kien_thi_ghi_duoc():
    yid = _mo_yc("Hợp đồng vận chuyển B")
    r = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                   json={"so_hop_dong": "HD-02", "ket_luan": "dat_co_dieu_kien",
                         "dieu_kien": "Bỏ điều 7.2 về miễn trách nhiệm toàn bộ"},
                   headers=login("chutich"))
    assert r.status_code == 200, r.text
    assert r.json()["ra_soat"]["ket_luan"] == "dat_co_dieu_kien"


def test_d3_muc_rui_ro_la_bi_chan_ngay_tai_cua():
    yid = _mo_yc("Hợp đồng vận chuyển C")
    r = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                   json={"ket_luan": "dat",
                         "rui_ro": [{"muc": "rat_cao", "noi_dung": "phạt vô hạn"}]},
                   headers=login("chutich"))
    assert r.status_code == 422, "mức lạ lọt vào thì sẽ không bao giờ hiện ở bộ lọc rủi ro cao"


def test_d4_rui_ro_phai_co_noi_dung_va_dem_duoc_so_cao():
    yid = _mo_yc("Hợp đồng vận chuyển D")
    r = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                   json={"ket_luan": "dat", "rui_ro": [{"muc": "cao", "noi_dung": ""}]},
                   headers=login("chutich"))
    assert r.status_code == 422
    r2 = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                    json={"ket_luan": "dat",
                          "rui_ro": [{"muc": "cao", "noi_dung": "Không giới hạn trách nhiệm",
                                      "dieu_khoan": "Điều 9"},
                                     {"muc": "thap", "noi_dung": "Thiếu dấu giáp lai"}]},
                    headers=login("chutich"))
    assert r2.status_code == 200, r2.text
    assert r2.json()["ra_soat"]["so_rui_ro_cao"] == 1


# ───────────────── E · sổ chữ ký ─────────────────
def test_e1_chu_ky_khong_can_cu_tham_quyen_bi_chan():
    r = client.post(f"{P}/chu-ky",
                    json={"mo_ta": "Hợp đồng HD-09", "nguoi_ky": "Nguyễn Văn A",
                          "ngay_ky": str(date.today()), "can_cu_tham_quyen": "   "},
                    headers=login("chutich"))
    assert r.status_code == 422
    assert "THẨM QUYỀN" in r.json()["detail"]


def test_e2_khong_tro_van_ban_cung_khong_mo_ta_thi_khong_ghi():
    r = client.post(f"{P}/chu-ky",
                    json={"nguoi_ky": "Nguyễn Văn A", "ngay_ky": str(date.today()),
                          "can_cu_tham_quyen": "Điều lệ điều 30"},
                    headers=login("chutich"))
    assert r.status_code == 422


def test_e3_du_can_cu_thi_vao_so():
    r = client.post(f"{P}/chu-ky",
                    json={"mo_ta": "Hợp đồng HD-10", "nguoi_ky": "Nguyễn Văn A",
                          "chuc_danh": "Tổng giám đốc", "ngay_ky": str(date.today()),
                          "loai_chu_ky": "tuoi",
                          "can_cu_tham_quyen": "Điều lệ công ty, Điều 30 khoản 2"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    ds = client.get(f"{P}/chu-ky", headers=login("bks")).json()
    assert ds["so"] >= 1
    assert all(x["can_cu_tham_quyen"].strip() for x in ds["rows"]), \
        "không có dòng nào vào sổ mà thiếu căn cứ"


# ───────────────── F · xác nhận chủ số liệu chặn cửa công bố ─────────────────
def _mo_ban_ghi(ma="NV-TEST-1"):
    h = login("chutich")
    client.post(f"{P}/nghia-vu",
                json={"ma": ma, "ten": "Báo cáo tài chính quý", "can_cu": "Thông tư do Pháp chế khai",
                      "chu_ky": "quy", "han_sau_ngay": 20}, headers=h)
    nv = [n for n in client.get(f"{P}/nghia-vu", headers=h).json()["rows"] if n["ma"] == ma][0]
    r = client.post(f"{P}/ban-ghi",
                    json={"nghia_vu_id": nv["id"], "ky": f"2026-Q3-{ma}",
                          "moc_phat_sinh": str(date.today())}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["ban_ghi"]["id"]


def test_f1_khong_hoi_ai_thi_khong_chan():
    """Bắt buộc MỌI bản ghi phải có xác nhận là một quy tắc nghiệp vụ – phải có người ký. Ở đây
    chỉ chặn đúng chỗ ĐÃ HỎI mà chưa có trả lời."""
    bid = _mo_ban_ghi("NV-TEST-1")
    r = client.get(f"{P}/ban-ghi/{bid}/xac-nhan", headers=login("chutich"))
    assert r.status_code == 200 and r.json()["cong_bo_duoc"] is True


def test_f2_da_hoi_chua_tra_loi_thi_chan_cua_cong_bo():
    bid = _mo_ban_ghi("NV-TEST-2")
    r = client.post(f"{P}/ban-ghi/{bid}/xac-nhan",
                    json={"chi_muc": "Doanh thu quý 3", "chu_so_lieu": "Kế toán trưởng"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    cb = client.post(f"{P}/ban-ghi/{bid}/da-cong-bo",
                     json={"noi_cong_bo": "HNX"}, headers=login("chutich"))
    assert cb.status_code == 422, "con số ra khỏi công ty trước khi chủ số liệu xác nhận"
    assert "CHƯA về" in cb.json()["detail"]


def test_f3_xac_nhan_xong_thi_cong_bo_duoc():
    bid = _mo_ban_ghi("NV-TEST-3")
    h = login("chutich")
    x = client.post(f"{P}/ban-ghi/{bid}/xac-nhan",
                    json={"chi_muc": "Lợi nhuận sau thuế", "chu_so_lieu": "Kế toán trưởng"},
                    headers=h).json()["xac_nhan"]
    client.post(f"{P}/xac-nhan/{x['id']}/tra-loi", json={"dong_y": True}, headers=h)
    cb = client.post(f"{P}/ban-ghi/{bid}/da-cong-bo", json={"noi_cong_bo": "HNX"}, headers=h)
    assert cb.status_code == 200, cb.text


def test_f4_tu_choi_xac_nhan_van_chan_va_phai_co_y_kien():
    bid = _mo_ban_ghi("NV-TEST-4")
    h = login("chutich")
    x = client.post(f"{P}/ban-ghi/{bid}/xac-nhan",
                    json={"chi_muc": "Số lao động", "chu_so_lieu": "HCNS"},
                    headers=h).json()["xac_nhan"]
    r = client.post(f"{P}/xac-nhan/{x['id']}/tra-loi", json={"dong_y": False, "y_kien": ""},
                    headers=h)
    assert r.status_code == 422, "từ chối không nêu lý do thì người làm hồ sơ không biết sửa gì"
    client.post(f"{P}/xac-nhan/{x['id']}/tra-loi",
                json={"dong_y": False, "y_kien": "Số này chưa chốt bảng lương tháng 9"}, headers=h)
    cb = client.post(f"{P}/ban-ghi/{bid}/da-cong-bo", json={"noi_cong_bo": "HNX"}, headers=h)
    assert cb.status_code == 422
    assert "TỪ CHỐI" in cb.json()["detail"], "không công bố đè lên một lời từ chối"


def test_f5_mot_chi_muc_chi_hoi_mot_lan():
    bid = _mo_ban_ghi("NV-TEST-5")
    h = login("chutich")
    j = {"chi_muc": "Doanh thu", "chu_so_lieu": "Kế toán"}
    assert client.post(f"{P}/ban-ghi/{bid}/xac-nhan", json=j, headers=h).status_code == 201
    assert client.post(f"{P}/ban-ghi/{bid}/xac-nhan", json=j, headers=h).status_code == 422


# ───────────────── G · K2 rỗng ≠ 0 ─────────────────
def test_g1_gia_tri_hop_dong_rong_van_la_rong():
    yid = _mo_yc("Hợp đồng chưa báo giá")
    r = client.put(f"{P}/yeu-cau/{yid}/ra-soat",
                   json={"so_hop_dong": "HD-K2", "ket_luan": "dat"}, headers=login("chutich"))
    assert r.status_code == 200, r.text
    assert r.json()["ra_soat"]["gia_tri"] is None, "chưa biết giá trị khác hẳn giá trị 0"


def test_g2_cot_gia_tri_khong_co_default():
    from app.models.phap_che_viec import RaSoatHopDong
    c = RaSoatHopDong.__table__.c["gia_tri"]
    assert c.nullable is True and c.default is None and c.server_default is None


# ───────────────── H · tuổi việc tính lúc đọc ─────────────────
def test_h1_tuoi_viec_khong_phai_mot_cot():
    from app.models.phap_che_viec import YeuCauPhapChe
    assert "so_ngay_treo" not in YeuCauPhapChe.__table__.c, \
        "một con số không ai cập nhật là một con số sai một cách im lặng"


def test_h2_viec_dong_thi_khong_con_treo():
    from app.services import phap_che_viec as PV
    from app.db.session import SessionLocal
    from app.models.phap_che_viec import YeuCauPhapChe
    yid = _mo_yc("Việc sẽ đóng")
    client.post(f"{P}/yeu-cau/{yid}/dong", json={"trang_thai": "xong", "ket_qua": "xong rồi"},
                headers=login("chutich"))
    with SessionLocal() as db:
        yc = db.get(YeuCauPhapChe, yid)
        assert PV.so_ngay_treo(yc) is None


def test_h3_ton_tinh_theo_ngay_doc():
    from app.services import phap_che_viec as PV
    from app.db.session import SessionLocal
    from app.models.phap_che_viec import YeuCauPhapChe
    yid = _mo_yc("Việc để treo")
    with SessionLocal() as db:
        yc = db.get(YeuCauPhapChe, yid)
        assert PV.so_ngay_treo(yc, date.today()) == 0
        mai_mot = date.today() + timedelta(days=PV.NGAY_COI_LA_TON + 1)
        assert PV.so_ngay_treo(yc, mai_mot) >= PV.NGAY_COI_LA_TON


def test_h4_ban_lam_viec_dem_dung():
    r = client.get(f"{P}/yeu-cau", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_tat_ca"] == len(d["rows"])
    assert d["so_dang_chay"] == len([x for x in d["rows"]
                                     if x["trang_thai"] in ("moi", "dang_xu_ly", "cho_bo_sung")])


# ───────────────── bảng mới có cửa nhập ─────────────────
def test_i1_bon_bang_moi_deu_da_khai_cua():
    from app.services.ks_cua_nhap import CUA_TAY, MAY_SINH
    for t in ("yeu_cau_phap_che", "ra_soat_hop_dong", "ban_ghi_chu_ky", "xac_nhan_chu_so_lieu"):
        assert t in CUA_TAY or t in MAY_SINH, f"{t} chưa khai cửa nhập"
