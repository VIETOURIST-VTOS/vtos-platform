"""Đợt C — lịch sử tổ chức theo thời gian, và hai màn hình HCNS còn thiếu.

  A. Đổi phòng là ghi một chặng; đổi lương thì không.
  B. Chặng đầu dựng lại từ hồ sơ cũ, mang cờ SUY RA và mang giá trị CŨ.
  C. Hai chặng không được phủ cùng một ngày — "ngày ấy người này ở đâu" chỉ có một câu trả lời.
  D. Trước lần điều chuyển đầu tiên, hệ thống trả lời KHÔNG BIẾT, không trả về phòng hiện tại.
  E. Tổng quan HCNS: chỉ đọc, và khối bảng lương không mở bằng cửa sau.
  F. Bảng mới có cửa; hai thẻ mới dùng lại đúng bộ vai đã ký của thẻ Hồ sơ nhân sự.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_lc1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lc1.db"):
    os.remove("test_lc1.db")

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


def _ds():
    r = client.get("/api/v1/employees", headers=login("hcns")).json()
    return r if isinstance(r, list) else (r.get("rows") or [])


def _mot(eid=None, phong=None):
    for e in _ds():
        if eid is not None and e["id"] == eid:
            return e
        if eid is None and (phong is None or e.get("department") == phong) and e.get("active", True):
            return e
    raise AssertionError(f"không tìm thấy hồ sơ (eid={eid}, phong={phong})")


def _sua(e, thay: dict):
    """PUT cần đủ trường bắt buộc của EmployeeIn, nên gửi lại hồ sơ hiện tại rồi đè phần đổi."""
    body = {"full_name": e["full_name"], "department": e["department"],
            "position": e.get("position") or "nv", "office": e.get("office") or "hcm",
            "contract_type": e.get("contract_type") or "hdld", "phien_ban": e.get("phien_ban")}
    body.update(thay)
    return client.put(f"/api/v1/employees/{e['id']}", json=body, headers=login("hcns"))


def _ls(eid):
    r = client.get(f"/api/v1/employees/{eid}/lich-su-to-chuc", headers=login("hcns"))
    assert r.status_code == 200, r.text
    return r.json()


# ───────────────────── A · khi nào thì ghi ─────────────────────
def test_a1_doi_luong_khong_sinh_chang():
    e = _mot(phong="kd_le")
    truoc = len(_ls(e["id"])["chang"])
    r = _sua(e, {"base_salary": float(e.get("base_salary") or 0) + 1})
    assert r.status_code == 200, r.text
    assert len(_ls(e["id"])["chang"]) == truoc, \
        "tăng lương không phải điều chuyển – ghi chặng ở đây làm lịch sử đầy dòng không mang tin"


def test_a2_doi_phong_sinh_chang():
    e = _mot(phong="kd_le")
    r = _sua(e, {"department": "dieu_hanh", "dieu_chuyen_ly_do": "Chuyển sang Điều hành"})
    assert r.status_code == 200, r.text
    assert "lịch sử tổ chức" in r.json()["message"], \
        "người bấm phải biết là vừa ghi một chặng lịch sử, không chỉ biết 'đã cập nhật'"
    d = _ls(e["id"])
    assert len(d["chang"]) == 2
    globals()["_EID"] = e["id"]


# ───────────────────── B · chặng đầu là SUY RA ─────────────────────
def test_b1_chang_dau_mang_co_suy_ra_va_gia_tri_CU():
    d = _ls(_EID)
    dau = d["chang"][0]
    assert dau["suy_ra"] is True, \
        "chặng dựng lại phải tự nói ra là dựng lại – trộn phỏng đoán vào bản ghi là tạo ra chứng cứ giả"
    assert dau["phong"] == "kd_le", \
        "chặng cũ phải mang phòng CŨ; mang phòng mới nghĩa là lịch sử ghi người này vốn đã ở đó từ đầu"
    assert d["chang"][-1]["phong"] == "dieu_hanh"
    assert d["chang"][-1]["suy_ra"] is False


# ───────────────────── C · hai chặng không phủ cùng một ngày ─────────────────────
def test_c1_chang_cu_ket_thuc_truoc_ngay_chang_moi_bat_dau():
    ch = _ls(_EID)["chang"]
    for a, b in zip(ch, ch[1:]):
        assert a["den_ngay"] is not None, "chặng trước phải được đóng"
        assert date.fromisoformat(a["den_ngay"]) < date.fromisoformat(b["tu_ngay"]), \
            "hai chặng phủ cùng một ngày thì câu 'ngày ấy người này ở đâu' có hai câu trả lời"


def test_c2_dieu_chuyen_lui_ngay_ghi_dung_ngay_do():
    """Lần điều chuyển ĐẦU TIÊN của một người, có hiệu lực lùi: ghi đúng ngày được chỉ định."""
    e = next(x for x in _ds() if x["id"] != _EID and x.get("active", True)
             and not _ls(x["id"])["chang"])
    lui = date.today() - timedelta(days=10)
    cu_phong = e["department"]
    moi_phong = "visa" if cu_phong != "visa" else "marketing"
    r = _sua(e, {"department": moi_phong, "dieu_chuyen_tu_ngay": str(lui),
                 "dieu_chuyen_ly_do": "Điều chuyển lùi hiệu lực"})
    assert r.status_code == 200, r.text
    ch = _ls(e["id"])["chang"]
    assert ch[-1]["tu_ngay"] == str(lui), \
        "điều chuyển có hiệu lực lùi mà ghi ngày hôm nay là ghi sai lịch sử"
    assert ch[-1]["phong"] == moi_phong
    assert ch[0]["phong"] == cu_phong and ch[0]["suy_ra"] is True


def test_c3_lui_som_hon_chang_dang_mo_thi_TU_CHOI():
    """Đóng chặng đang mở vào 'hôm trước' một ngày sớm hơn ngày nó bắt đầu sẽ cho một khoảng thời
    gian không tồn tại. Từ chối thay vì tự chữa: sửa lịch sử đã ghi là việc có chủ ý."""
    e = _mot(eid=_EID)
    qua_som = date.today() - timedelta(days=10)
    r = _sua(e, {"position": "tp", "dieu_chuyen_tu_ngay": str(qua_som),
                 "dieu_chuyen_ly_do": "Bổ nhiệm lùi hiệu lực"})
    assert r.status_code == 422, r.text
    assert "sớm hơn ngày bắt đầu chặng đang mở" in r.json()["detail"], \
        "thông điệp phải chỉ ra VÌ SAO từ chối và phải làm gì, không chỉ nói 'không hợp lệ'"


# ───────────────────── D · chưa biết thì nói chưa biết ─────────────────────
def test_d1_truoc_chang_dau_tien_tra_ve_khong_biet():
    from app.db.session import SessionLocal
    from app.services import to_chuc_lich_su as LS
    d = _ls(_EID)
    som = date.fromisoformat(d["chang"][0]["tu_ngay"]) - timedelta(days=1)
    with SessionLocal() as db:
        assert LS.tai_ngay(db, d["ma_nv"], som) is None, \
            "trả về phòng hiện tại ở đây là biến 'không biết' thành 'biết' – đúng lỗi bảng này sinh ra để chữa"


def test_d2_trong_mot_chang_tra_ve_dung_chang_do():
    from app.db.session import SessionLocal
    from app.services import to_chuc_lich_su as LS
    d = _ls(_EID)
    giua = date.fromisoformat(d["chang"][0]["tu_ngay"])
    with SessionLocal() as db:
        c = LS.tai_ngay(db, d["ma_nv"], giua)
    assert c is not None and c.phong == d["chang"][0]["phong"]


# ───────────────────── E · Tổng quan HCNS ─────────────────────
def test_e1_tong_quan_chi_doc_va_du_khoi():
    r = client.get("/api/v1/hr/tong-quan", headers=login("hcns"))
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("nhan_su", "ho_so_thieu", "hop_dong", "nghi_phep_cho_duyet", "su_vu_trong_thang",
              "lich_su_to_chuc"):
        assert k in d, f"thiếu khối {k}"
    assert d["nhan_su"]["tong"] == sum(g["tong"] for g in d["nhan_su"]["theo_phong"]), \
        "tổng không bằng tổng các phòng – hai phép đếm trên cùng một tập"
    assert "chưa có dữ liệu" in d["lich_su_to_chuc"]["ghi_chu"], \
        "chưa có dòng nào KHÁC với thiếu hồ sơ – màn hình phải nói ra, không để người đọc tự đoán"


def test_e2_khoi_bang_luong_khong_mo_bang_cua_sau():
    """Thẻ Tổng quan mở rộng hơn thẻ Bảng lương. In thẳng tổng thực nhận là mở lương cho Kế toán
    và các Trưởng phòng mà không ai ký cho điều đó."""
    r = client.get("/api/v1/hr/tong-quan", headers=login("ketoan"))
    if r.status_code == 403:
        return                      # Kế toán không mở được thẻ – cũng là một câu trả lời đúng
    j = r.json()
    if not j.get("co_bang_luong"):
        assert "bang_luong" not in j, "không mở được thẻ Bảng lương thì không được có khối lương"


def test_e3_hcns_thay_khoi_luong():
    d = client.get("/api/v1/hr/tong-quan", headers=login("hcns")).json()
    assert d["co_bang_luong"] is True
    assert "bang_luong" in d


# ───────────────────── F · cửa nhập và bộ vai ─────────────────────
def test_f1_bang_moi_co_cua():
    from app.services.ks_cua_nhap import CUA_TAY
    assert "lich_su_to_chuc" in CUA_TAY, \
        "cửa của bảng này là màn hình sửa hồ sơ nhân sự – một cửa, và cửa ấy ghi"


def test_f2_hai_the_moi_dung_lai_bo_vai_da_ky():
    from app.services.access import HR_TABS, HR_TAB_ROLES
    assert "tong_quan" in HR_TABS and "cham_cong" in HR_TABS
    assert HR_TAB_ROLES["tong_quan"] == HR_TAB_ROLES["employees"], \
        "khai một bộ vai MỚI ở đây là lần viết phần mềm tự đặt quyền"
    assert HR_TAB_ROLES["cham_cong"] == HR_TAB_ROLES["employees"]


def test_f3_khong_co_cua_ghi_rieng_cho_lich_su():
    """Hai đường đổi phòng thì đường nào quên ghi lịch sử là chỗ lịch sử thủng."""
    import app.api.v1.hr as A
    duong = [r.path for r in A.router.routes
             if "lich-su-to-chuc" in getattr(r, "path", "")
             and (getattr(r, "methods", set()) - {"GET", "HEAD", "OPTIONS"})]
    assert not duong, f"có cửa ghi riêng cho lịch sử tổ chức: {duong}"
