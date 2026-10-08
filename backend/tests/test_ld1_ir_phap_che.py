"""Đợt D1 — IR & Pháp chế: vai trò, văn bản có phiên bản, nghĩa vụ và bản ghi công bố.

  A. Vai `ir_phapche` khai đúng MỘT vai, phạm vi toàn tập đoàn; màn hình hẹp đúng năm vai.
  B. Sửa bản ĐÃ CÓ HIỆU LỰC sinh phiên bản mới; sửa bản nháp thì không.
  C. Ban hành đóng bản cũ trong cùng một lời gọi — không có khoảnh khắc hai bản cùng hiệu lực.
  D. Hệ thống KHÔNG nạp sẵn nghĩa vụ công bố nào, và cửa khai BẮT BUỘC có căn cứ.
  E. Trạng thái công bố do quy tắc tính ra; không có cửa nào gõ trạng thái.
  F. RỖNG ≠ "còn thời gian": chưa biết hạn có trạng thái riêng.
"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_ld1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ld1.db"):
    os.remove("test_ld1.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}


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


# ───────────────────── A · vai trò và phạm vi màn hình ─────────────────────
def test_a1_mot_vai_khong_phai_hai():
    from app.models.core import ROLES
    assert "ir_phapche" in ROLES
    assert "ir" not in ROLES and "phapche" not in ROLES, \
        "Chủ tịch chốt MỘT người kiêm – tách hai vai là dựng sẵn ranh giới chưa có người đứng hai bên"


def test_a2_man_hinh_hep_khong_mo_cho_phong_ban_nao():
    """Màn hình IR – Pháp chế KHÔNG mở cho một vai phòng ban nào. Giữ nguyên ý; sửa cách khai.

    08/10/2026 chiều — bản đầu khai CỨNG đúng năm tên `{chutich, tgd, ir_phapche, bks, cntt}`, và nó
    đụng một luật có trước: `test_ma_tran_quyen` đòi `robot_ks` có mặt ở MỌI dòng của ma trận (Chủ
    tịch quyết 09/9/2026 — "robot làm việc Ban Kiểm soát thì phải nhìn được thứ Ban Kiểm soát nhìn").
    Hai hàng rào cãi nhau thì main đỏ, và main đỏ thì mọi làn đỏ theo.

    Đọc lại lý do bản đầu tự ghi — "không phải việc của PHÒNG BAN" — thì nó nói về vai phòng ban, và
    chính bản ấy vẫn giữ `bks`. Nên việc thiếu `robot_ks` là hệ quả của khai tay một danh sách, không
    phải một quyết định loại robot ra khỏi màn hình này.

    Nay khai bằng `BASE_VIEW + (…)`: nền hệ thống cộng đúng hai vai được mở. Ý giữ nguyên từng chữ —
    KHÔNG một vai phòng ban nào — nhưng viết theo cách không chống lại luật nền, và phép thử hỏi
    thẳng điều cần giữ thay vì pin một tập tên.

    NẾU Chủ tịch muốn robot Kiểm soát KHÔNG đọc hồ sơ công bố HĐQT thì đây là một quyết định khác và
    phải sửa ở `test_ma_tran_quyen` bằng một ngoại lệ có khai lý do, không phải bằng cách khai tay lại
    danh sách ở đây.
    """
    from app.services.access import BASE_VIEW, MENU_ROLES
    assert set(MENU_ROLES["/ir-phap-che"]) == set(BASE_VIEW) | {"ir_phapche", "cntt"}, \
        "văn bản HĐQT và hồ sơ công bố không phải việc của phòng ban"
    # Điều phải giữ, nói thẳng ra: không một vai phòng ban nào lọt vào.
    PHONG_BAN = {"ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "nv_kd", "tn_kd", "tp_kd", "gd_kd",
                 "sales_admin", "nv_mkt", "ketoan", "hcns", "tai_xe", "hdv", "gd_doi_xe", "tp_hd",
                 "nv_visa", "hanh_chinh"}
    lot = PHONG_BAN & set(MENU_ROLES["/ir-phap-che"])
    assert not lot, f"vai phòng ban lọt vào màn hình IR – Pháp chế: {sorted(lot)}"


def test_a3_pham_vi_toan_tap_doan_khong_cat_theo_phap_nhan():
    """Chủ tịch chốt 08/10: IR nhìn toàn tập đoàn. Ba bảng này KHÔNG có cột pháp nhân, nên không
    có đường nào cắt chúng – kiểm bằng chính mô hình chứ không bằng lời hứa."""
    from app.models.phap_che import BanGhiCongBo, NghiaVuCongBo, VanBanPhapChe
    for M in (VanBanPhapChe, NghiaVuCongBo, BanGhiCongBo):
        assert "company_id" not in M.__table__.columns, \
            f"{M.__name__} có cột pháp nhân – sẽ bị cắt theo phiên, trái chỉ đạo toàn tập đoàn"


def test_a4_bks_va_cntt_doc_ma_khong_ghi():
    from app.api.v1.phap_che import GHI, XEM
    assert "bks" in XEM and "bks" not in GHI, \
        "kiểm soát mà sửa được thứ mình kiểm thì không còn là kiểm soát"
    assert "cntt" in XEM and "cntt" not in GHI


def test_a5_vai_khac_khong_mo_duoc():
    r = client.get("/api/v1/ir-phap-che/meta", headers=login("hcns"))
    assert r.status_code == 403


# ───────────────────── B · văn bản có phiên bản ─────────────────────
def _tao(tieu_de="Quy chế thử"):
    r = client.post("/api/v1/ir-phap-che/van-ban",
                    json={"loai": "quy_che", "so_hieu": "QC-01", "tieu_de": tieu_de},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    return r.json()["van_ban"]


def test_b1_ban_nhap_sua_tai_cho():
    v = _tao("Quy chế nháp")
    r = client.put(f"/api/v1/ir-phap-che/van-ban/{v['id']}",
                   json={"tieu_de": "Quy chế nháp (sửa)"}, headers=login("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["sinh_phien_ban_moi"] is False
    assert d["van_ban"]["phien_ban"] == 1 and d["van_ban"]["id"] == v["id"]


def test_b2_ban_da_hieu_luc_sinh_phien_ban_moi():
    v = _tao("Quy chế quản trị")
    client.post(f"/api/v1/ir-phap-che/van-ban/{v['id']}/ban-hanh", headers=login("chutich"))
    r = client.put(f"/api/v1/ir-phap-che/van-ban/{v['id']}",
                   json={"tieu_de": "Quy chế quản trị", "ly_do_sua": "Bổ sung Điều 7"},
                   headers=login("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["sinh_phien_ban_moi"] is True, \
        "sửa tại chỗ một bản đã có hiệu lực làm mọi quyết định theo bản cũ không giải trình được"
    assert d["van_ban"]["phien_ban"] == 2
    assert d["van_ban"]["id"] != v["id"]
    assert d["van_ban"]["trang_thai"] == "nhap"
    globals()["_GOC"] = v["goc_id"]
    globals()["_P2"] = d["van_ban"]["id"]


def test_b3_moi_phien_ban_deu_doc_lai_duoc():
    d = client.get(f"/api/v1/ir-phap-che/van-ban/{_GOC}/phien-ban", headers=login("bks")).json()
    assert d["so_phien_ban"] == 2
    assert [r["phien_ban"] for r in d["rows"]] == [1, 2]


# ───────────────────── C · ban hành đóng bản cũ ─────────────────────
def test_c1_ban_hanh_dong_ban_cu_trong_cung_mot_luot():
    r = client.post(f"/api/v1/ir-phap-che/van-ban/{_P2}/ban-hanh", headers=login("chutich"))
    assert r.status_code == 200, r.text
    d = client.get(f"/api/v1/ir-phap-che/van-ban/{_GOC}/phien-ban", headers=login("bks")).json()
    hieu_luc = [v for v in d["rows"] if v["trang_thai"] == "hieu_luc"]
    assert len(hieu_luc) == 1 and hieu_luc[0]["phien_ban"] == 2, \
        "hai phiên bản cùng hiệu lực là chỗ mọi lần hỏng rơi vào"
    cu = [v for v in d["rows"] if v["phien_ban"] == 1][0]
    assert cu["trang_thai"] == "thay_the"
    assert cu["bi_thay_boi"] == _P2, "phải nói ra bản NÀO đã thay, không chỉ nói 'đã bị thay'"
    assert date.fromisoformat(cu["hieu_luc_den"]) < date.fromisoformat(hieu_luc[0]["hieu_luc_tu"]), \
        "hai bản phủ cùng một ngày thì câu 'ngày ấy bản nào hiệu lực' có hai câu trả lời"


def test_c2_ban_hanh_lai_ban_dang_hieu_luc_thi_tu_choi():
    r = client.post(f"/api/v1/ir-phap-che/van-ban/{_P2}/ban-hanh", headers=login("chutich"))
    assert r.status_code == 422


# ───────────────────── D · không nạp sẵn nghĩa vụ ─────────────────────
def test_d1_he_thong_khong_nap_san_nghia_vu_nao():
    """Danh mục và thời hạn công bố là QUY ĐỊNH PHÁP LUẬT. Điền từ trí nhớ của phần mềm thì một
    hạn sai không hiện ra như lỗi phần mềm — nó hiện ra như một lần chậm công bố."""
    from app.db.session import SessionLocal
    from app.models.phap_che import NghiaVuCongBo
    from sqlalchemy import select
    with SessionLocal() as db:
        tu_may = [n for n in db.execute(select(NghiaVuCongBo)).scalars() if not n.khai_boi]
    assert not tu_may, f"có {len(tu_may)} nghĩa vụ không do người khai"


def test_d2_khai_nghia_vu_bat_buoc_co_can_cu():
    r = client.post("/api/v1/ir-phap-che/nghia-vu",
                    json={"ma": "TEST-KHONG-CAN-CU", "ten": "Thử"}, headers=login("chutich"))
    assert r.status_code == 422
    assert "CĂN CỨ" in r.json()["detail"], \
        "một nghĩa vụ không ai nhớ vì sao có là nghĩa vụ sẽ bị bỏ khi bận"


def test_d3_khai_duoc_khi_co_can_cu():
    r = client.post("/api/v1/ir-phap-che/nghia-vu",
                    json={"ma": "TEST-01", "ten": "Nghĩa vụ thử", "chu_ky": "su_kien",
                          "han_sau_ngay": 3, "can_cu": "Điều khoản do Pháp chế ghi khi khai"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    globals()["_NV"] = r.json()["id"]


# ───────────────────── E · trạng thái do quy tắc tính ─────────────────────
def test_e1_khong_co_cua_nao_go_trang_thai():
    import app.api.v1.phap_che as A
    import inspect
    src = inspect.getsource(A)
    assert "trang_thai:" not in src.replace("trang_thai_ban_ghi", ""), \
        "một ô 'đã công bố' gõ được biến cả sổ này thành một lời khai"


def test_e2_qua_han_va_dung_han_tinh_tu_du_lieu():
    from app.models.phap_che import BanGhiCongBo
    from app.services.phap_che import trang_thai_bg
    nay = date(2026, 10, 8)
    muon = BanGhiCongBo(nghia_vu_id=1, ky="x", han_chot=date(2026, 10, 1))
    assert trang_thai_bg(muon, nay) == "qua_han"
    muon.da_cong_bo_luc = datetime(2026, 10, 5)
    assert trang_thai_bg(muon, nay) == "cong_bo_tre", \
        "công bố sau hạn vẫn là trễ – gọi nó là 'đã công bố' là xoá mất một sự thật"
    dung = BanGhiCongBo(nghia_vu_id=1, ky="y", han_chot=date(2026, 10, 10),
                        da_cong_bo_luc=datetime(2026, 10, 9))
    assert trang_thai_bg(dung, nay) == "da_cong_bo"
    gan = BanGhiCongBo(nghia_vu_id=1, ky="z", han_chot=date(2026, 10, 12))
    assert trang_thai_bg(gan, nay) == "sap_den_han"
    xa = BanGhiCongBo(nghia_vu_id=1, ky="w", han_chot=date(2026, 12, 31))
    assert trang_thai_bg(xa, nay) == "chua_den_han"


def test_e3_han_suy_tu_moc_chi_khi_co_khai_so_ngay():
    from app.models.phap_che import NghiaVuCongBo
    from app.services.phap_che import han_tu_moc
    co = NghiaVuCongBo(ma="a", ten="a", han_sau_ngay=3)
    assert han_tu_moc(co, date(2026, 10, 1)) == date(2026, 10, 4)
    khong = NghiaVuCongBo(ma="b", ten="b", han_sau_ngay=None)
    assert han_tu_moc(khong, date(2026, 10, 1)) is None, \
        "đoán một hạn ở đây là đoán một con số pháp lý"


def test_e4_ghi_cong_bo_bat_buoc_co_noi_cong_bo():
    r = client.post("/api/v1/ir-phap-che/ban-ghi",
                    json={"nghia_vu_id": _NV, "ky": "2026-SK01",
                          "moc_phat_sinh": str(date.today() - timedelta(days=10))},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    bid = r.json()["ban_ghi"]["id"]
    assert r.json()["ban_ghi"]["trang_thai"] == "qua_han", \
        "mốc cách đây 10 ngày với hạn 3 ngày thì phải là quá hạn"
    r2 = client.post(f"/api/v1/ir-phap-che/ban-ghi/{bid}/da-cong-bo",
                     json={"noi_cong_bo": "  "}, headers=login("chutich"))
    assert r2.status_code == 422
    r3 = client.post(f"/api/v1/ir-phap-che/ban-ghi/{bid}/da-cong-bo",
                     json={"noi_cong_bo": "HNX"}, headers=login("chutich"))
    assert r3.status_code == 200, r3.text
    assert r3.json()["ban_ghi"]["trang_thai"] == "cong_bo_tre"


# ───────────────────── F · rỗng ≠ còn thời gian ─────────────────────
def test_f1_chua_biet_han_co_trang_thai_rieng():
    r = client.post("/api/v1/ir-phap-che/nghia-vu",
                    json={"ma": "TEST-02", "ten": "Hạn không tính bằng ngày",
                          "mo_ta_han": "Trong 24 giờ kể từ khi phát sinh",
                          "can_cu": "Điều khoản do Pháp chế ghi khi khai"},
                    headers=login("chutich"))
    assert r.status_code == 201, r.text
    nv2 = r.json()["id"]
    r2 = client.post("/api/v1/ir-phap-che/ban-ghi",
                     json={"nghia_vu_id": nv2, "ky": "2026-SK02",
                           "moc_phat_sinh": str(date.today())}, headers=login("chutich"))
    assert r2.status_code == 201, r2.text
    d = r2.json()
    assert d["ban_ghi"]["han_chot"] is None
    assert d["ban_ghi"]["trang_thai"] == "chua_ro_han", \
        "rỗng không phải 'còn nhiều thời gian' – chưa biết hạn là một việc phải xử lý"
    assert "CHƯA xác định được hạn" in d["message"]


def test_f2_ba_bang_deu_co_cua():
    from app.services.ks_cua_nhap import CUA_TAY
    for t in ("van_ban_phap_che", "nghia_vu_cong_bo", "ban_ghi_cong_bo"):
        assert t in CUA_TAY, f"{t} chưa khai cửa nhập"
