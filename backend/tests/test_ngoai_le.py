"""Ngoại lệ cần xử lý – màn hình gom mọi lần một quy tắc bị bẻ.

Ba phép thử quan trọng nhất trong tệp này:
  - test_ngoai_le_khong_ai_ky_thi_cot_nguoi_quyet_phai_rong: không được điền đại một cái tên cho đẹp bảng.
  - test_khong_dong_duoc_ngoai_le_khong_ai_ky_neu_khong_neu_ten: đóng mà không có tên = xóa dấu vết.
  - test_moi_loai_ngoai_le_deu_co_bo_do: danh mục và bộ dò không được lệch nhau.
"""
import os, sys
from datetime import datetime, date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ngoai_le.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_ngoai_le.db", "test_ngoai_le.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.services import ngoai_le as NL
from app.models.core import User, Tour, UserGrant, AiRun, AiPause

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


def tk(role):
    db = db_()
    u = db.execute(select(User).where(User.role == role, User.active == True)).scalars().first()  # noqa: E712
    ra = u.username if u else None
    db.close(); return ra


def login(role):
    un = tk(role); assert un, f"không có tài khoản vai trò {role}"
    r = client.post("/api/v1/auth/login", data={"username": un, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ds(h, **q):
    r = client.get("/api/v1/ngoai-le", headers=h, params=q)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ danh mục
def test_moi_loai_ngoai_le_deu_co_bo_do():
    """Danh mục LOAI và các bộ dò phải khớp: một loại khai trong danh mục mà không bộ dò nào sinh ra
    được thì màn hình hứa nhiều hơn nó làm."""
    import inspect
    nguon = inspect.getsource(NL)
    for k in NL.LOAI:
        assert f'"{k}"' in nguon, f"loại {k} khai trong danh mục nhưng không xuất hiện ở bộ dò nào"
    for k, v in NL.LOAI.items():
        assert v["nhom"] in NL.NHOM, f"{k} thuộc nhóm không có tên"
        assert v["muc"] in NL.MUC
        assert v["quy_tac"].strip(), f"{k} không ghi rõ đang bẻ quy tắc nào"


def test_do_tim_khong_ghi_gi_vao_co_so_du_lieu():
    db = db_()
    truoc = len(db.execute(select(NL.NgoaiLeXuLy)).scalars().all())
    NL.do_tim(db)
    sau = len(db.execute(select(NL.NgoaiLeXuLy)).scalars().all())
    db.close()
    assert truoc == sau, "bộ dò phải chỉ đọc"


# ------------------------------------------------------------------ phân quyền
def test_phan_quyen_man_hinh():
    for vai in ("chutich", "ketoan", "cntt", "bks"):
        assert client.get("/api/v1/ngoai-le", headers=login(vai)).status_code == 200
    for vai in ("nv_kd", "hcns"):
        un = tk(vai)
        if not un: continue
        assert client.get("/api/v1/ngoai-le", headers=login(vai)).status_code == 403, \
            f"{vai} không được xem màn hình ngoại lệ"


def test_ban_kiem_soat_doc_duoc_nhung_khong_ghi_duoc():
    h = login("bks")
    assert client.get("/api/v1/ngoai-le", headers=h).status_code == 200
    r = client.post("/api/v1/ngoai-le/nhan", headers=h, json={"ma": "x#1"})
    assert r.status_code == 403


def test_chi_chu_tich_va_tgd_dong_duoc():
    h = login("ketoan")
    r = client.post("/api/v1/ngoai-le/dong", headers=h, json={"ma": "x#1"})
    assert r.status_code == 403, "Kế toán ghi được nhưng không đóng được"


# ------------------------------------------------------------------ nội dung
def _tao_tour_chien_luoc():
    db = db_()
    t = db.execute(select(Tour)).scalars().first()
    assert t is not None
    t.strategic = True; db.commit(); ma = t.code; db.close()
    return ma


def test_ngoai_le_khong_ai_ky_thi_cot_nguoi_quyet_phai_rong():
    """Cờ 'tour chiến lược' miễn chế tài dưới biên khi tính hoa hồng, nhưng không có màn hình nào bật nó
    và không có bản ghi ai bật. Màn hình phải nói thẳng là KHÔNG AI KÝ, không điền đại một cái tên."""
    ma_tour = _tao_tour_chien_luoc()
    d = ds(login("chutich"))
    r = [x for x in d["rows"] if x["loai"] == "tour_chien_luoc" and ma_tour in x["doi_tuong"]]
    assert r, "không dò ra cờ tour chiến lược"
    assert r[0]["nguoi_quyet"] == ""
    assert r[0]["thieu_chu_ky"] is True
    assert r[0]["muc"] == "do"
    assert d["tong_hop"]["khong_ai_ky"] >= 1


def test_ngoai_le_quyen_vo_han_bi_nang_len_muc_do():
    db = db_()
    u = db.execute(select(User).where(User.role == "hcns")).scalars().first()
    db.add(UserGrant(user_id=u.id, kind="capability", value="bang_luong", from_date=date.today(),
                     to_date=None, reason="Kiểm thử: quyền không thời hạn phải nổi lên đỏ",
                     granted_by="chutich", approved_by="chutich", active=True))
    db.commit(); db.close()
    d = ds(login("chutich"))
    r = [x for x in d["rows"] if x["loai"] == "ngoai_le_quyen"]
    assert r, "không dò ra ngoại lệ quyền"
    assert any(x["muc"] == "do" for x in r), "quyền KHÔNG THỜI HẠN phải là mức đỏ"
    assert all(x["nguoi_quyet"] for x in r), "ngoại lệ quyền luôn có người duyệt"


def test_ai_cho_hau_kiem_thanh_ngoai_le():
    db = db_()
    db.add(AiRun(tac_vu="tin_khach", muc=3, ref="conv:1", trang_thai="cho_hau_kiem",
                 ket_qua="kiểm thử", nguon="quy_tac"))
    db.commit(); db.close()
    d = ds(login("chutich"))
    assert any(x["loai"] == "ai_cho_hau_kiem" for x in d["rows"])


def test_tat_chan_giay_to_xe_la_ngoai_le_ban_kinh_rong():
    """Tham số xe_chan_khi_thieu_giay = 0 tắt kiểm tra giấy tờ cho MỌI lệnh điều xe."""
    d = ds(login("chutich"))
    r = [x for x in d["rows"] if x["loai"] == "tat_chan_giay_xe"]
    assert r, "đang để mặc định 0 mà không dò ra"
    assert r[0]["muc"] == "do"


# ------------------------------------------------------------------ vòng đời xử lý
def test_vong_doi_nhan_ghi_dong():
    h = login("chutich")
    d = ds(h)
    ma = next(x["ma"] for x in d["rows"] if x["nguoi_quyet"] and x["trang_thai"] == "chua")
    assert client.post("/api/v1/ngoai-le/nhan", headers=h, json={"ma": ma}).status_code == 200
    assert [x for x in ds(h)["rows"] if x["ma"] == ma][0]["trang_thai"] == "dang"

    # thiếu giải trình thì không đóng được
    r = client.post("/api/v1/ngoai-le/dong", headers=h, json={"ma": ma})
    assert r.status_code == 400 and "giải trình" in r.json()["detail"]

    client.post("/api/v1/ngoai-le/ghi", headers=h,
                json={"ma": ma, "giai_trinh": "Kiểm thử: đã rà soát lại toàn bộ chứng từ liên quan"})
    # có giải trình nhưng chưa ghi đã làm gì → vẫn chặn
    r = client.post("/api/v1/ngoai-le/dong", headers=h, json={"ma": ma})
    assert r.status_code == 400 and "tái diễn" in r.json()["detail"]

    r = client.post("/api/v1/ngoai-le/dong", headers=h,
                    json={"ma": ma, "ket_luan": "Đã bổ sung bước kiểm tra trước khi ký"})
    assert r.status_code == 200, r.text
    row = [x for x in ds(h)["rows"] if x["ma"] == ma][0]
    assert row["trang_thai"] == "dong" and row["dong_boi"]


def test_khong_dong_duoc_ngoai_le_khong_ai_ky_neu_khong_neu_ten():
    """Đóng một ngoại lệ mà hệ thống cho qua không ai ký, lại không nêu được tên ai chịu trách nhiệm,
    thì không phải là xử lý – đó là xóa dấu vết."""
    h = login("chutich")
    ma = next(x["ma"] for x in ds(h)["rows"] if x["thieu_chu_ky"] and x["trang_thai"] != "dong")
    client.post("/api/v1/ngoai-le/ghi", headers=h,
                json={"ma": ma, "giai_trinh": "Kiểm thử: ngoại lệ này không có chữ ký của ai",
                      "da_lam": "Đã mở phiếu theo dõi"})
    r = client.post("/api/v1/ngoai-le/dong", headers=h, json={"ma": ma})
    assert r.status_code == 400 and "chịu trách nhiệm" in r.json()["detail"]

    client.post("/api/v1/ngoai-le/ghi", headers=h, json={"ma": ma, "nguoi_chiu_trach_nhiem": "Trần Tuấn"})
    r = client.post("/api/v1/ngoai-le/dong", headers=h, json={"ma": ma})
    assert r.status_code == 200, r.text


def test_moi_thao_tac_deu_vao_nhat_ky_bat_bien():
    from app.models.core import AuditLog
    db = db_()
    hd = {a for a in db.execute(select(AuditLog.action)).scalars()}
    db.close()
    for a in ("nhan_ngoai_le", "ghi_ngoai_le", "dong_ngoai_le"):
        assert a in hd, f"thao tác {a} không để lại vết"


def test_mo_lai_phai_neu_ly_do():
    h = login("chutich")
    ma = next(x["ma"] for x in ds(h)["rows"] if x["trang_thai"] == "dong")
    assert client.post("/api/v1/ngoai-le/mo-lai", headers=h, json={"ma": ma, "ly_do": "ngắn"}).status_code == 400
    r = client.post("/api/v1/ngoai-le/mo-lai", headers=h,
                    json={"ma": ma, "ly_do": "Kiểm thử: có tình tiết mới cần xem lại"})
    assert r.status_code == 200, r.text
    assert [x for x in ds(h)["rows"] if x["ma"] == ma][0]["trang_thai"] == "dang"


def test_bo_loc_va_tong_hop_khop_nhau():
    h = login("chutich")
    d = ds(h)
    assert d["tong_hop"]["tong"] == len(d["rows"])
    mo = [x for x in d["rows"] if x["trang_thai"] != "dong"]
    assert d["tong_hop"]["chua_dong"] == len(mo)
    assert d["tong_hop"]["khong_ai_ky"] == len([x for x in mo if x["thieu_chu_ky"]])
    chi_thieu = ds(h, chi_thieu_chu_ky=True)
    assert all(x["thieu_chu_ky"] for x in chi_thieu["rows"])


def test_ma_ngoai_le_on_dinh_qua_hai_lan_do():
    db = db_()
    a = {x["ma"] for x in NL.do_tim(db)}
    b = {x["ma"] for x in NL.do_tim(db)}
    db.close()
    assert a == b and a, "mã ngoại lệ phải ổn định, nếu không việc xử lý sẽ mất dấu sau mỗi lần dò"


def test_menu_ngoai_le_theo_dung_ma_tran():
    from app.services.access import MENU_ROLES
    assert "/ngoai-le" in MENU_ROLES
    for vai in ("chutich", "tgd", "bks", "ketoan", "cntt", "tp_dh"):
        assert vai in MENU_ROLES["/ngoai-le"]
    for vai in ("nv_kd", "xe_hdv", "nv_visa", "hanh_chinh"):
        assert vai not in MENU_ROLES["/ngoai-le"], f"{vai} không được thấy màn hình rà ngoại lệ"


def test_cat_moi_loai_khong_lam_con_so_nho_di():
    """Cắt để nhìn được, không phải để báo cáo nhỏ đi: dù chỉ trả 1 dòng mỗi loại, tổng hợp vẫn đếm đủ."""
    h = login("chutich")
    day = ds(h, cat_moi_loai=0)
    cat = ds(h, cat_moi_loai=1)
    assert cat["tong_hop"]["tong"] == day["tong_hop"]["tong"]
    assert cat["tong_hop"]["khong_ai_ky"] == day["tong_hop"]["khong_ai_ky"]
    assert len(cat["rows"]) <= len(day["rows"])
    for loai, n in cat["tong_hop"]["theo_loai"].items():
        assert len([r for r in cat["rows"] if r["loai"] == loai]) <= 1
        if n > 1:
            assert cat["tong_hop"]["bi_cat"].get(loai) == n - 1
