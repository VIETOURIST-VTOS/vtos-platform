"""Quyền AI theo vị trí, hạn mức và nút tắt khẩn (đặc tả 07/9/2026, phần C).

Phép thử quan trọng nhất trong tệp này là test_bang_quyen_dieu_khien_hanh_vi_that: nó chứng minh bảng
KHÔNG phải bảng trang trí. Một bảng phân quyền mà hệ thống không đọc thì đến lúc có chuyện, nó chỉ
chứng minh rằng người ta đã tưởng là mình kiểm soát được.
"""
import os, sys
from datetime import datetime, date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_quyen_ai.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_quyen_ai.db", "test_quyen_ai.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import ai_quyen as AQ
from app.models.core import AI_GROUPS, AI_LEVELS, ROLES

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def login(u, pw="123456"):
    r = client.post("/api/v1/auth/login", data={"username": u, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


def tk(role):
    """Tên đăng nhập của một tài khoản mang vai trò này – tên đăng nhập KHÁC mã vai trò."""
    from sqlalchemy import select
    from app.models.core import User
    db = db_()
    u = db.execute(select(User).where(User.role == role, User.active == True)).scalars().first()
    ra = u.username if u else None
    db.close(); return ra


def dat(vai, tac_vu, muc, han_muc=None):
    return client.put("/api/v1/ai/positions", headers=login("chutich"),
                      json={"vai_tro": vai, "tac_vu": tac_vu, "muc": muc, "han_muc": han_muc})


HM = {"khung_gio": "00:00-23:59", "so_luot_ngay": 30,
      "loai_noi_dung": "lịch khởi hành, giá công bố", "nguoi_hau_kiem": "ptgd_mkt"}


# ---------- bảng ----------
def test_nap_mac_dinh_du_19_vi_tri_va_6_nhom_viec():
    b = client.get("/api/v1/ai/positions", headers=login("cntt")).json()
    assert len(b["rows"]) == len(ROLES)
    assert set(b["cot"]) == set(AI_GROUPS)
    for r in b["rows"]:
        assert set(r["o"]) == set(AI_GROUPS)


def test_chi_hai_o_muc_3_trong_bang_mac_dinh():
    """Theo Phụ lục A: chỉ Phó TGĐ Marketing và NV Marketing ở mức 3, đều là việc gửi tin cho khách."""
    ba = [(v, c) for v, mucs in AQ.MAC_DINH.items() for c, m in zip(AQ.COT, mucs) if m == 3]
    assert set(ba) == {("ptgd_mkt", "tin_khach"), ("nv_mkt", "tin_khach")}


def test_mo_hinh_ngon_ngu_khong_bao_gio_len_muc_4():
    """Mức 4 dành cho robot mã xác định. Sáu nhóm việc do mô hình làm có trần là mức 3."""
    for vai, mucs in AQ.MAC_DINH.items():
        for c, m in zip(AQ.COT, mucs):
            if c != "canh_bao":
                assert m <= 3, f"{vai}/{c} đặt mức {m} – việc do mô hình ngôn ngữ làm không được quá 3"


def test_bon_viec_ai_khong_duoc_lam_co_trong_ban_cong_bo():
    b = client.get("/api/v1/ai/positions", headers=login("cntt")).json()
    assert len(b["viec_ai_khong_duoc_lam"]) == 4
    assert any("tiền ra" in x for x in b["viec_ai_khong_duoc_lam"])


# ---------- hạn mức ----------
def test_muc_3_thieu_han_muc_thi_khong_luu_duoc():
    r = dat("nv_kd", "tin_khach", 3, {"khung_gio": "08:00-21:00"})
    assert r.status_code == 422, "mức 3 không hạn mức chính là tình trạng trước 07/9"
    ct = r.json()["detail"]
    assert "so_luot_ngay" in ct["thieu"] and "nguoi_hau_kiem" in ct["thieu"]


def test_muc_3_du_han_muc_thi_luu_duoc():
    assert dat("nv_kd", "tin_khach", 3, HM).status_code == 200
    dat("nv_kd", "tin_khach", 2, None)


def test_khung_gio_sai_dinh_dang_thi_coi_la_ngoai_gio():
    """Hỏng thì đóng, không mở: một chuỗi khung giờ vô nghĩa không được thành 'lúc nào cũng gửi được'."""
    assert AQ._trong_khung_gio("bậy bạ", datetime.now()) is False
    assert AQ._trong_khung_gio("", datetime.now()) is False


# ---------- bảng điều khiển hành vi thật ----------
def test_bang_quyen_dieu_khien_hanh_vi_that():
    """Hạ ô 'gửi tin cho khách' của vai trò chủ quản hộp thư xuống mức 2 thì robot NGỪNG tự gửi."""
    d = db_()
    assert dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, HM).status_code == 200
    duoc, _ = AQ.duoc_tu_gui(d, datetime.now()); assert duoc is True
    assert dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 2, None).status_code == 200
    d.expire_all()
    duoc, ly_do = AQ.duoc_tu_gui(d, datetime.now())
    assert duoc is False and "mức đang áp dụng là 2" in ly_do
    dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, HM); d.close()


def test_ngoai_khung_gio_thi_khong_tu_gui():
    d = db_()
    assert dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, dict(HM, khung_gio="08:00-09:00")).status_code == 200
    d.expire_all()
    duoc, ly_do = AQ.duoc_tu_gui(d, datetime.now().replace(hour=23, minute=30))
    assert duoc is False and "ngoài khung giờ" in ly_do
    dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, HM); d.close()


def test_het_luot_trong_ngay_thi_khong_tu_gui():
    from app.models.core import AiRun
    d = db_()
    assert dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, dict(HM, so_luot_ngay=2)).status_code == 200
    for _ in range(2):
        d.add(AiRun(tac_vu="tin_khach", muc=3, nguon="claude", trang_thai="cho_hau_kiem"))
    d.commit(); d.expire_all()
    duoc, ly_do = AQ.duoc_tu_gui(d, datetime.now())
    assert duoc is False and "hết 2 lượt" in ly_do
    dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, HM); d.close()


# ---------- tắt khẩn ----------
def test_tat_khan_ha_moi_o_muc_3_xuong_2_ngay():
    d = db_()
    dat(AQ.CHU_QUAN_HOP_THU, "tin_khach", 3, dict(HM, so_luot_ngay=999))
    r = client.post("/api/v1/ai/pause", headers=login("tgd"),
                    json={"tam_dung": True, "ly_do": "khách phản ánh nội dung sai giá"})
    assert r.status_code == 200, r.text
    d.expire_all()
    assert AQ.muc_cua(d, AQ.CHU_QUAN_HOP_THU, "tin_khach") == 2
    duoc, ly_do = AQ.duoc_tu_gui(d, datetime.now())
    assert duoc is False and "tạm dừng" in ly_do
    b = client.get("/api/v1/ai/positions", headers=login("cntt")).json()
    assert b["tam_dung"] is True and "sai giá" in b["tam_dung_ly_do"]
    # mở lại
    assert client.post("/api/v1/ai/pause", headers=login("tgd"), json={"tam_dung": False}).status_code == 200
    d.expire_all()
    assert AQ.muc_cua(d, AQ.CHU_QUAN_HOP_THU, "tin_khach") == 3
    d.close()


def test_tat_khan_bat_buoc_co_ly_do():
    assert client.post("/api/v1/ai/pause", headers=login("tgd"),
                       json={"tam_dung": True, "ly_do": "  "}).status_code == 422


# ---------- quyền vào màn hình ----------
def test_chi_nam_vai_tro_xem_duoc_va_ba_vai_tro_sua_duoc():
    from app.services import access as AC
    assert set(AC.MENU_ROLES["/ai-roles"]) == set(AC.BASE_VIEW) | {"ptgd_mkt", "cntt"}
    for vai in ("nv_kd", "ketoan", "hcns", "tp_dh"):
        un = tk(vai)
        if not un: continue
        assert client.get("/api/v1/ai/positions", headers=login(un)).status_code == 403, f"{vai} không được vào"
    # Phó TGĐ Marketing XEM được nhưng KHÔNG đặt mức được – người chủ quản kênh không tự nới quyền cho mình
    mkt = tk("ptgd_mkt")
    if mkt:
        h = login(mkt)
        assert client.get("/api/v1/ai/positions", headers=h).status_code == 200
        assert client.put("/api/v1/ai/positions", headers=h,
                          json={"vai_tro": "nv_kd", "tac_vu": "tin_khach", "muc": 3, "han_muc": HM}).status_code == 403


def test_ban_kiem_soat_xem_duoc_khong_sua_duoc():
    bks = tk("bks")
    if not bks: pytest.skip("không có tài khoản Ban Kiểm soát")
    h = login(bks)
    assert client.get("/api/v1/ai/positions", headers=h).status_code == 200
    assert client.post("/api/v1/ai/pause", headers=h, json={"tam_dung": True, "ly_do": "thử"}).status_code == 403


# ---------- báo cáo ----------
def test_bao_cao_khong_bao_0_phan_tram_khi_chua_ai_hau_kiem():
    rp = client.get("/api/v1/ai/report?so_ngay=7", headers=login("cntt")).json()
    assert "ty_le_bi_sua" in rp and "cho_hau_kiem" in rp
    if rp["da_hau_kiem"] == 0:
        assert rp["ty_le_bi_sua"] is None, "0% đọc ra là 'chưa sai lần nào'"


def test_dat_muc_de_lai_vet_trong_nhat_ky():
    dat("nv_visa", "doc_chung_tu", 1, None)
    h = login("cntt")
    log = client.get("/api/v1/access/audit", headers=h).json()["rows"]
    assert any(r["action"] == "dat_quyen_ai" for r in log), "đổi quyền AI phải vào nhật ký bất biến"
    dat("nv_visa", "doc_chung_tu", 2, None)
