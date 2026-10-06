"""Phòng HDV Đợt 4 — đề xuất và bước duyệt có cấp (đặc tả v1.0 §10–§12).

  A. THIẾU CẤU HÌNH THÌ CHẶN TRÌNH — không tự chọn cấp duyệt.
  B. Cấu hình phải có chữ ký mới có hiệu lực; người trình không tự ký.
  C. Các bước lập ĐỦ ngay lúc trình, đúng thứ tự.
  D. Chỉ đúng vai của bước đang chờ mới quyết được; không ai tự duyệt hồ sơ mình trình.
  E. Trả bổ sung / từ chối BẮT BUỘC lý do.
  F. Bấm hai lần không thành hai quyết định.
  G. Rỗng vẫn là rỗng: đề xuất không mang tiền vẫn chạy; trần rỗng = không có trần.
  H. MỘT CẤP NHIỀU VAI (quyết định 06/10/2026): "chutich|tgd" là một cấp, ai ký cũng xong — khác
     "chutich,tgd" là hai cấp phải đủ cả hai chữ ký.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hdv4.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hdv4.db"):
    os.remove("test_hdv4.db")

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
ID = {}
LAP = "hcns"     # người lập/trình hồ sơ


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


def _lap_dx(**kw):
    than = {"loai": "thu_lao", "ly_do": "Phụ cấp đoàn dài ngày", "so_tien": 5_000_000}
    than.update(kw)
    return client.post("/api/v1/guide-assignments/de-xuat", json=than, headers=login(LAP))


def _trinh(did):
    return client.post(f"/api/v1/guide-assignments/de-xuat/{did}/trinh", json={}, headers=login(LAP))


def _quyet(did, vai, qd, y="", pb=None):
    than = {"quyet_dinh": qd, "y_kien": y}
    if pb is not None:
        than["phien_ban"] = pb
    return client.post(f"/api/v1/guide-assignments/de-xuat/{did}/quyet", json=than, headers=login(vai))


# ───────────────────── A · thiếu cấu hình thì chặn ─────────────────────
def test_a1_bang_cau_hinh_sinh_ra_rong():
    d = client.get("/api/v1/guide-assignments/de-xuat/cau-hinh", headers=login(LAP)).json()
    assert d["so_dong"] == 0, "các con số phê duyệt là chính sách, không phải thứ robot tự đặt"


def test_a2_trinh_khi_chua_co_cau_hinh_thi_BI_CHAN():
    r = _lap_dx()
    assert r.status_code == 201
    ID["dx_chan"] = r.json()["id"]
    r2 = _trinh(ID["dx_chan"])
    assert r2.status_code == 422
    ct = r2.json()["detail"]
    assert ct["gate"] == "THIEU_CAU_HINH_DUYET"
    assert "tiền lệ" in ct["message"], \
        "phải nói ra VÌ SAO chặn, nếu không người dùng chỉ thấy hệ thống dở"


def test_a3_cau_hinh_khong_co_cap_nao_thi_tu_choi():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "thu_lao", "cac_cap": []}, headers=login(LAP))
    assert r.status_code == 422, "một cấu hình không cấp nào là đường đi vòng qua mọi chữ ký"


# ───────────────────── B · cấu hình phải có chữ ký ─────────────────────
def test_b1_cau_hinh_chua_ky_thi_chua_co_hieu_luc():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "thu_lao", "tu_so_tien": 0, "den_so_tien": 10_000_000,
                          "cac_cap": ["ptgd_doan", "tgd"], "hieu_luc_tu": "2026-01-01"},
                    headers=login(LAP))
    assert r.status_code == 201
    ID["ch1"] = r.json()["id"]
    assert _trinh(ID["dx_chan"]).status_code == 422, "chưa ký thì vẫn chặn"


def test_b2_nguoi_trinh_cau_hinh_khong_tu_ky():
    """Người lập là hcns; nếu hcns cũng được ký thì cấu hình phê duyệt tự mình có hiệu lực."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hdv import CauHinhDuyetHdv
    db = SessionLocal()
    c = db.get(CauHinhDuyetHdv, ID["ch1"])
    cu = c.lap_boi
    c.lap_boi = "chutich"
    db.commit()
    db.close()
    try:
        r = client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{ID['ch1']}/ky",
                        headers=login("chutich"))
        assert r.status_code == 422
    finally:
        db = SessionLocal(); c = db.get(CauHinhDuyetHdv, ID["ch1"]); c.lap_boi = cu; db.commit(); db.close()


def test_b3_ky_roi_thi_co_hieu_luc_va_trinh_duoc():
    r = client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{ID['ch1']}/ky",
                    headers=login("chutich"))
    assert r.status_code == 200, r.text
    r2 = _trinh(ID["dx_chan"])
    assert r2.status_code == 200, r2.text
    assert r2.json()["duong_di"] == ["ptgd_doan", "tgd"]


# ───────────────────── C · lập đủ bước ngay lúc trình ─────────────────────
def test_c1_duong_di_hien_day_du_truoc_khi_ai_ky():
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == ID["dx_chan"]][0]
    assert [b["vai_tro"] for b in d["duong_di"]] == ["ptgd_doan", "tgd"]
    assert all(b["trang_thai"] == "cho" for b in d["duong_di"])
    assert d["cap_dang_cho"] == 1, "sinh dần từng bước thì không ai trả lời được 'bao giờ xong'"


def test_c2_khoang_tien_hep_hon_va_moi_hon_thang():
    """Hai dòng cùng khớp thì lấy dòng hẹp nhất và mới nhất. Lấy dòng rộng nhất thì một khoảng mới
    khai cho mức cao sẽ bị một dòng cũ 'từ 0 trở lên' nuốt mất."""
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "thu_lao", "tu_so_tien": 3_000_000, "den_so_tien": 10_000_000,
                          "cac_cap": ["ptgd_doan", "tgd", "chutich"], "hieu_luc_tu": "2026-02-01"},
                    headers=login(LAP))
    client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{r.json()['id']}/ky", headers=login("chutich"))
    r2 = _lap_dx(so_tien=5_000_000)
    ID["dx2"] = r2.json()["id"]
    assert _trinh(ID["dx2"]).json()["duong_di"] == ["ptgd_doan", "tgd", "chutich"]


# ───────────────────── D · ai quyết được ─────────────────────
def test_d1_sai_vai_thi_khong_quyet_duoc():
    r = _quyet(ID["dx_chan"], "tgd", "dong_y")
    assert r.status_code == 403, "bước 1 chờ ptgd_doan, TGĐ không nhảy cóc vào ký trước"


def test_d2_nguoi_trinh_khong_tu_duyet():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hdv import DeXuatHdv
    db = SessionLocal()
    d = db.get(DeXuatHdv, ID["dx_chan"])
    cu = d.nguoi_lap
    d.nguoi_lap = "ptgd.doan"
    db.commit()
    db.close()
    try:
        r = _quyet(ID["dx_chan"], "ptgd.doan", "dong_y")
        assert r.status_code == 422, "tự trình rồi tự duyệt thì cái duyệt ấy không kiểm gì cả"
    finally:
        db = SessionLocal(); d = db.get(DeXuatHdv, ID["dx_chan"]); d.nguoi_lap = cu; db.commit(); db.close()


def test_d3_dung_vai_thi_quyet_duoc_va_chuyen_cap():
    r = _quyet(ID["dx_chan"], "ptgd.doan", "dong_y")
    assert r.status_code == 200, r.text
    assert "cấp 2" in r.json()["message"]


def test_d4_du_cap_thi_da_duyet():
    r = _quyet(ID["dx_chan"], "tgd", "dong_y")
    assert r.status_code == 200 and r.json()["trang_thai"] == "da_duyet"


def test_d5_cho_toi_quyet_chi_tra_ho_so_dung_vai_va_khong_phai_cua_minh():
    d = client.get("/api/v1/guide-assignments/de-xuat/cho-toi-quyet", headers=login("ptgd.doan")).json()
    assert all(h["duong_di"][h["cap_dang_cho"] - 1]["vai_tro"] == "ptgd_doan" for h in d["ho_so"])


# ───────────────────── E · trả lại phải có lý do ─────────────────────
def test_e1_tra_bo_sung_khong_ly_do_thi_bi_chan():
    assert _quyet(ID["dx2"], "ptgd.doan", "tra_bo_sung").status_code == 422


def test_e2_tu_choi_khong_ly_do_thi_bi_chan():
    assert _quyet(ID["dx2"], "ptgd.doan", "tu_choi").status_code == 422


def test_e3_tra_bo_sung_co_ly_do_thi_ve_trang_thai_can_bo_sung():
    r = _quyet(ID["dx2"], "ptgd.doan", "tra_bo_sung", "Thiếu căn cứ tính phụ cấp")
    assert r.status_code == 200 and r.json()["trang_thai"] == "can_bo_sung"


def test_e4_trinh_lai_thi_lap_lai_duong_di_tu_dau():
    r = _trinh(ID["dx2"])
    assert r.status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == ID["dx2"]][0]
    assert all(b["trang_thai"] == "cho" for b in d["duong_di"]) and d["cap_dang_cho"] == 1


# ───────────────────── F · chống bấm lặp ─────────────────────
def test_f1_bam_hai_lan_khong_thanh_hai_quyet_dinh():
    _quyet(ID["dx2"], "ptgd.doan", "dong_y")
    r = _quyet(ID["dx2"], "ptgd.doan", "dong_y")
    assert r.status_code in (403, 422), "bước đã quyết thì không quyết lại"


def test_f2_lech_phien_ban_thi_409():
    r = _quyet(ID["dx2"], "tgd", "dong_y", pb=99)
    assert r.status_code == 409 and r.json()["detail"]["gate"] == "LECH_PHIEN_BAN"


# ───────────────────── G · rỗng vẫn là rỗng ─────────────────────
def test_g1_de_xuat_khong_mang_tien_van_chay_duoc():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "dao_tao", "tu_so_tien": 0, "cac_cap": ["tgd"],
                          "hieu_luc_tu": "2026-01-01"}, headers=login(LAP))
    client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{r.json()['id']}/ky", headers=login("chutich"))
    r2 = _lap_dx(loai="dao_tao", so_tien=None, ly_do="Xin thêm một HDV tiếng Nhật")
    assert r2.status_code == 201
    k = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == r2.json()["id"]][0]
    assert k["so_tien"] is None, "đề xuất không mang tiền phải hiện ô trống, không phải 0"
    assert _trinh(r2.json()["id"]).status_code == 200


def test_g2_tran_rong_nghia_la_khong_co_tran():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "phat_sinh_tour", "tu_so_tien": 0, "den_so_tien": None,
                          "cac_cap": ["chutich"], "hieu_luc_tu": "2026-01-01"}, headers=login(LAP))
    client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{r.json()['id']}/ky", headers=login("chutich"))
    r2 = _lap_dx(loai="phat_sinh_tour", so_tien=9_000_000_000, ly_do="Sự cố lớn")
    assert _trinh(r2.json()["id"]).status_code == 200, \
        "khoảng thiếu trần mà không coi là vô hạn thì hồ sơ lớn nhất lại không khớp dòng nào"


def test_g3_loai_ho_so_la_mot_danh_sach_dong():
    assert _lap_dx(loai="linh_tinh").status_code == 422


# ───────────── H · một cấp nhiều vai: Chủ tịch HOẶC TGĐ (quyết định 06/10/2026) ─────────────
def _ch_hieu_luc(loai, cac_cap, **kw):
    than = {"loai": loai, "tu_so_tien": 0, "cac_cap": cac_cap, "hieu_luc_tu": "2026-01-01"}
    than.update(kw)
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh", json=than, headers=login(LAP))
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert client.post(f"/api/v1/guide-assignments/de-xuat/cau-hinh/{cid}/ky",
                       headers=login("chutich")).status_code == 200
    return cid


def test_h1_mot_cap_hai_vai_sinh_dung_MOT_buoc():
    _ch_hieu_luc("tam_ung", ["chutich|tgd"])
    r = _lap_dx(loai="tam_ung", so_tien=3_000_000, ly_do="Tạm ứng chi trên tour")
    ID["h"] = r.json()["id"]
    assert _trinh(ID["h"]).status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == ID["h"]][0]
    assert len(d["duong_di"]) == 1, "một cấp hai vai là MỘT bước, không phải hai"
    assert d["duong_di"][0]["cac_vai"] == ["chutich", "tgd"]


def test_h2_man_hinh_doc_duoc_chu_HOAC():
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == ID["h"]][0]
    ten = d["duong_di"][0]["vai_tro_ten"]
    assert " hoặc " in ten, \
        "nhìn chuỗi chutich|tgd thì người dùng không phân biệt được với hai cấp nối tiếp"


def test_h3_tgd_ky_mot_minh_la_XONG():
    r = _quyet(ID["h"], "tgd", "dong_y", y="Đồng ý")
    assert r.status_code == 200, r.text
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == ID["h"]][0]
    assert d["trang_thai"] == "da_duyet", "một cấp ai cũng được: TGĐ ký là hồ sơ xong"
    assert d["duong_di"][0]["nguoi"] == "tgd"


def test_h4_chu_tich_cung_ky_duoc_mot_minh():
    _lap_dx(loai="tam_ung")
    r = _lap_dx(loai="tam_ung", so_tien=2_000_000, ly_do="Tạm ứng khác")
    did = r.json()["id"]
    assert _trinh(did).status_code == 200
    assert _quyet(did, "chutich", "dong_y", y="Đồng ý").status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == did][0]
    assert d["trang_thai"] == "da_duyet"


def test_h5_vai_ngoai_danh_sach_cua_buoc_van_bi_chan():
    r = _lap_dx(loai="tam_ung", so_tien=1_000_000, ly_do="Tạm ứng nữa")
    did = r.json()["id"]
    _trinh(did)
    r2 = _quyet(did, "ptgd.doan", "dong_y", y="Đồng ý")
    assert r2.status_code in (403, 422), \
        "mở cho hai vai không có nghĩa là mở cho vai thứ ba"


def test_h6_dau_phay_van_la_HAI_cap_phai_du_ca_hai_chu_ky():
    _ch_hieu_luc("doi_soat_ky", ["tgd", "chutich"])
    r = _lap_dx(loai="doi_soat_ky", so_tien=7_000_000, ly_do="Đối soát thù lao kỳ 9")
    did = r.json()["id"]
    assert _trinh(did).status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == did][0]
    assert len(d["duong_di"]) == 2, "dấu phẩy là hai cấp — nhầm dấu là nhầm số chữ ký"
    assert _quyet(did, "tgd", "dong_y", y="Đồng ý").status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == did][0]
    assert d["trang_thai"] == "cho_duyet", "hai cấp thì một chữ ký chưa xong"
    assert _quyet(did, "chutich", "dong_y", y="Đồng ý").status_code == 200


def test_h7_ten_vai_tro_viet_sai_bi_chan_ngay_o_cua_nhap():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "thue_ctv", "tu_so_tien": 0, "cac_cap": ["chutich|tgdd"],
                          "hieu_luc_tu": "2026-01-01"}, headers=login(LAP))
    assert r.status_code == 422, \
        "một tên vai viết sai sẽ thành cấp KHÔNG AI ký được, và hồ sơ đứng mãi mà không ai biết vì sao"


def test_h8_mot_cap_khai_trung_vai_bi_chan():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh",
                    json={"loai": "thue_ctv", "tu_so_tien": 0, "cac_cap": ["tgd|tgd"],
                          "hieu_luc_tu": "2026-01-01"}, headers=login(LAP))
    assert r.status_code == 422


# ───── I · cửa công bố luật một cấp (quyết định 06/10/2026, mọi mức tiền) ─────
def test_i1_chi_chu_tich_hoac_tgd_goi_duoc():
    for vai in (LAP, "tp.dieuhanh"):
        r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh/khai-mot-cap", headers=login(vai))
        assert r.status_code in (403, 404), \
            f"{vai} công bố được chính sách thì chữ ký của Chủ tịch không còn nghĩa gì"


def test_i2_chu_tich_cong_bo_thi_phu_du_SAU_loai():
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh/khai-mot-cap", headers=login("chutich"))
    assert r.status_code == 201, r.text
    d = r.json()
    assert len(d["da_khai"]) + len(d["bo_qua"]) == 6, "sáu loại hồ sơ phải phủ hết, không sót loại nào"
    ds = client.get("/api/v1/guide-assignments/de-xuat/cau-hinh", headers=login(LAP)).json()["dong"]
    for loai in ("thue_ctv", "thu_lao", "tam_ung", "phat_sinh_tour", "dao_tao", "doi_soat_ky"):
        assert any(c["loai"] == loai and c["trang_thai"] == "hieu_luc" for c in ds), loai


def test_i3_nguoi_ky_la_NGUOI_GOI_khong_phai_robot():
    ds = client.get("/api/v1/guide-assignments/de-xuat/cau-hinh", headers=login(LAP)).json()["dong"]
    moi = [c for c in ds if "06/10/2026" in (c["ghi_chu"] or "")]
    assert moi, "dòng công bố phải ghi rõ căn cứ"
    for c in moi:
        assert c["ky_boi"] == "chutich", "chữ ký phải là người thật, không phải robot"
        assert c["cac_cap"] == ["chutich|tgd"], "một cấp, hai vai thay nhau"
        assert c["tu_so_tien"] == 0 and c["den_so_tien"] is None, "mọi mức tiền: từ 0, không trần"


def test_i4_goi_lan_hai_KHONG_de_len_chinh_sach_dang_chay():
    truoc = client.get("/api/v1/guide-assignments/de-xuat/cau-hinh", headers=login(LAP)).json()["so_dong"]
    r = client.post("/api/v1/guide-assignments/de-xuat/cau-hinh/khai-mot-cap", headers=login("tgd"))
    assert r.status_code == 201
    assert r.json()["da_khai"] == [] and len(r.json()["bo_qua"]) == 6
    sau = client.get("/api/v1/guide-assignments/de-xuat/cau-hinh", headers=login(LAP)).json()["so_dong"]
    assert sau == truoc, "bấm hai lần không được sinh thêm dòng, và không được đè dòng đang chạy"


def test_i5_sau_cong_bo_thi_de_xuat_moi_di_qua_DUNG_MOT_cua():
    r = _lap_dx(loai="thue_ctv", so_tien=250_000_000, ly_do="Thuê CTV cho mùa cao điểm")
    did = r.json()["id"]
    assert _trinh(did).status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == did][0]
    assert len(d["duong_di"]) == 1, "mọi mức tiền một cấp: 250 triệu cũng chỉ một cửa"
    assert _quyet(did, "tgd", "dong_y", y="Đồng ý").status_code == 200
    d = [x for x in client.get("/api/v1/guide-assignments/de-xuat", headers=login(LAP)).json()
         if x["id"] == did][0]
    assert d["trang_thai"] == "da_duyet"
