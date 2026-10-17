# -*- coding: utf-8 -*-
"""XN-1 · Ô CHỌN XE NHÀ ở mục «Phương tiện» của tờ quyết toán — 17/10/2026.

Chuyện đo được: cột `tour_phuong_tien.vehicle_id` có từ lâu, cửa ghi nhận nó mà không soát, nhưng
màn hình KHÔNG có ô nào để chọn — người nhập chỉ gõ biển số chữ và tự đánh dấu «xe nhà». Đối chiếu
xe thuê ngoài (DX-2) vì thế phải đoán theo biển, và nhóm B «nghi khai nhầm» không có cửa nào để sửa.

Bốn điều Chủ tịch chốt, mỗi điều một phép thử:
  X1  xe thuê ngoài / xe hợp tác KHÔNG có trong danh sách chọn, và cửa ghi chặn nếu gửi lén
  X2  đã chọn xe nhà thì biển số, số chỗ, dấu «xe nhà» KHOÁ theo hồ sơ xe — máy chủ ghi đè
  X3  xe ngừng khai thác, đã bán: ẩn khỏi danh sách và không chọn mới được
  X4  có cửa GẮN TAY cho chặng đã nhập; tờ đã ký thì đòi lý do và để dấu vết; DX-2 nhóm B hết
      gọi tên chặng đã gắn, và không còn gọi nhầm xe hợp tác là «nghi khai nhầm»
  X5  màn hình: ô chọn đọc danh sách từ máy chủ, khoá đúng ba ô, có nút gắn tay; DX-2 trỏ đúng tab
Cuối tệp là bản tự phá.
"""
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_xn1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_xn1.db"):
    os.remove("test_xn1.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
FORM = GOC / "web" / "components" / "QuyetToanForm.tsx"
DOI_XE = GOC / "web" / "app" / "doi-xe" / "page.tsx"
MK = "Vtos@Demo#2026"
client = TestClient(app)
ID: dict = {}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _tao_nguoi(username, role):
    from app.models.core import User
    from app.core.security import hash_password
    db = _db()
    u = User(username=username, full_name=username, role=role, staff_code=username.upper()[:8],
             password_hash=hash_password(MK), active=True, must_change_password=False)
    db.add(u); db.commit(); i = u.id; db.close()
    return i


def _h(u):
    r = client.post("/api/v1/auth/login", data={"username": u, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module", autouse=True)
def _dung():
    global client
    with TestClient(app) as c:
        client = c
        _tao_nguoi("dh_xn1", "nv_dh")
        _tao_nguoi("tp_xn1", "tp_dh")
        from app.models.core import Tour
        from app.models.hr import Employee, Vehicle
        db = _db()
        nv = Employee(code="NVXN1", full_name="Điều hành XN1", department="dieu_hanh")
        db.add(nv); db.flush()
        xe = {
            "nha": Vehicle(plate="51B-900.01", code="XN01", seats=45, kind="noi_bo", active=True,
                           lifecycle="dang_khai_thac", op_right="so_huu"),
            "hop_tac": Vehicle(plate="51B-900.02", code="XN02", seats=29, kind="hop_tac", active=True,
                               lifecycle="dang_khai_thac", op_right="hop_tac"),
            "thue": Vehicle(plate="51B-900.03", code="XN03", seats=16, kind="noi_bo", active=True,
                            lifecycle="dang_khai_thac", op_right="thue"),
            "ban": Vehicle(plate="51B-900.04", code="XN04", seats=45, kind="noi_bo", active=True,
                           lifecycle="da_ban", op_right="so_huu"),
            "ngung": Vehicle(plate="51B-900.05", code="XN05", seats=45, kind="noi_bo", active=True,
                             lifecycle="ngung", op_right="so_huu"),
        }
        db.add_all(xe.values()); db.flush()
        for k, v in xe.items():
            ID[k] = v.id
        t = Tour(code="XN-1017", name="Thử ô chọn xe", tour_type="doan_noi_dia", operator_id=nv.id,
                 start_date=date(2026, 10, 10), end_date=date(2026, 10, 12))
        db.add(t); db.commit(); ID["tour"] = t.id; db.close()
        yield


def _url(p=""):
    return f"/api/v1/quyet-toan-lop3/{ID['tour']}/phuong-tien{p}"


def _chang(h, **kw):
    d = {"loai": "o_to", "chang": "HCM – Vũng Tàu", "ngay": "2026-10-10", **kw}
    return client.post(_url(), headers=h, json=d)


def _dong(h):
    r = client.get(_url(), headers=h)
    assert r.status_code == 200, r.text
    return r.json()


# ── X1 + X3 ──────────────────────────────────────────────────────────────────────────────────
def test_x1_x3_danh_sach_chi_co_xe_nha_dang_khai_thac():
    r = client.get("/api/v1/quyet-toan-lop3/xe-nha", headers=_h("dh_xn1"))
    assert r.status_code == 200, r.text
    ids = {x["id"] for x in r.json()["xe"]}
    assert ID["nha"] in ids
    for k in ("hop_tac", "thue", "ban", "ngung"):
        assert ID[k] not in ids, f"xe «{k}» không được hiện trong ô chọn xe nhà"


def test_x1_x3_cua_ghi_chan_xe_khong_chon_duoc():
    h = _h("dh_xn1")
    for k in ("hop_tac", "thue", "ban", "ngung"):
        r = _chang(h, vehicle_id=ID[k])
        assert r.status_code == 422, (k, r.text)
    assert _chang(h, loai="may_bay", vehicle_id=ID["nha"]).status_code == 422, "máy bay không phải xe nhà"
    # Thuê ngoài vẫn gõ tay được như cũ (điều 1: «khi nào thuê thì tự nhập tay»).
    assert _chang(h, so_hieu="51B-777.77", nha_cung_cap="Nhà xe ngoài").status_code == 200


# ── X2 ───────────────────────────────────────────────────────────────────────────────────────
def test_x2_chon_xe_nha_thi_khoa_bien_so_cho_va_dau_xe_nha():
    h = _h("dh_xn1")
    r = _chang(h, vehicle_id=ID["nha"], so_hieu="GÕ BẬY", so_cho=4, xe_nha=0)
    assert r.status_code == 200, r.text
    x = next(d for d in _dong(h)["dong"] if d["id"] == r.json()["id"])
    assert (x["so_hieu"], x["so_cho"], x["xe_nha"], x["vehicle_id"]) == ("51B-900.01", 45, 1, ID["nha"]), (
        "máy chủ phải ghi đè biển số, số chỗ và dấu xe nhà theo hồ sơ xe")
    assert x["goi_y_gan"] is None


# ── X4 ───────────────────────────────────────────────────────────────────────────────────────
def test_x4_gan_tay_chang_chi_co_bien_so():
    h = _h("dh_xn1")
    pid = _chang(h, so_hieu="51b 90001", nha_cung_cap="(nạp từ mẫu)").json()["id"]
    x = next(d for d in _dong(h)["dong"] if d["id"] == pid)
    assert x["vehicle_id"] is None and x["goi_y_gan"]["vehicle_id"] == ID["nha"], (
        "biển viết khác định dạng vẫn phải được chỉ đúng xe nhà để gắn")
    # Biển trùng xe hợp tác thì KHÔNG gợi ý gắn — đó đúng là thuê ngoài.
    p2 = _chang(h, so_hieu="51B-900.02").json()["id"]
    assert next(d for d in _dong(h)["dong"] if d["id"] == p2)["goi_y_gan"] is None
    assert client.post(_url(f"/{p2}/gan-xe"), headers=h, json={"vehicle_id": ID["hop_tac"]}).status_code == 422

    r = client.post(_url(f"/{pid}/gan-xe"), headers=h, json={"vehicle_id": ID["nha"], "phien_ban": x["phien_ban"]})
    assert r.status_code == 200, r.text
    assert (r.json()["so_hieu"], r.json()["xe_nha"]) == ("51B-900.01", 1)
    # Gửi lại bản cũ thì bị chặn — hai người cùng gắn một chặng không ghi đè lặng lẽ lên nhau.
    assert client.post(_url(f"/{pid}/gan-xe"), headers=h,
                       json={"vehicle_id": None, "phien_ban": x["phien_ban"]}).status_code == 409
    # Gỡ: giữ biển, bỏ dấu xe nhà.
    r = client.post(_url(f"/{pid}/gan-xe"), headers=h, json={"vehicle_id": None})
    assert r.status_code == 200 and r.json()["vehicle_id"] is None and r.json()["xe_nha"] == 0
    assert r.json()["so_hieu"] == "51B-900.01"
    # Xe NAY đã bán vẫn gắn được vào chặng ĐÃ chạy — chiếc xe khi ấy là xe nhà.
    p3 = _chang(h, so_hieu="51B-900.04").json()["id"]
    assert next(d for d in _dong(h)["dong"] if d["id"] == p3)["goi_y_gan"]["vehicle_id"] == ID["ban"]
    assert client.post(_url(f"/{p3}/gan-xe"), headers=h, json={"vehicle_id": ID["ban"]}).status_code == 200


def test_x4_to_da_ky_thi_doi_ly_do_va_de_dau_vet():
    from app.models.core import Tour
    h = _h("dh_xn1")
    pid = _chang(h, so_hieu="51B-900.01").json()["id"]
    db = _db(); t = db.get(Tour, ID["tour"]); t.closed_at = datetime.now(); db.commit(); db.close()
    try:
        assert _dong(h)["da_ky"] is True
        assert client.post(_url(f"/{pid}/gan-xe"), headers=h, json={"vehicle_id": ID["nha"]}).status_code == 403, (
            "tờ đã ký: nhân viên điều hành không sửa được")
        tp = _h("tp_xn1")
        assert client.post(_url(f"/{pid}/gan-xe"), headers=tp, json={"vehicle_id": ID["nha"]}).status_code == 422
        r = client.post(_url(f"/{pid}/gan-xe"), headers=tp,
                        json={"vehicle_id": ID["nha"], "ly_do_sua": "chặng này chạy xe nhà XN01"})
        assert r.status_code == 200, r.text
        dv = client.get(f"/api/v1/quyet-toan-lop3/{ID['tour']}/dau-vet", headers=tp).json()
        assert "vehicle_id" in str(dv), "gắn xe vào tờ đã ký phải để dấu vết"
    finally:
        db = _db(); t = db.get(Tour, ID["tour"]); t.closed_at = None; db.commit(); db.close()


def test_x4_dx2_nhom_B_chi_goi_xe_nha_va_het_goi_chang_da_gan():
    from app.services import doi_chieu_xe_ngoai as DX
    h = _h("dh_xn1")
    p_ht = _chang(h, so_hieu="51B 900 02").json()["id"]     # trùng xe hợp tác
    p_nha = _chang(h, so_hieu="51B-90001").json()["id"]     # trùng xe nhà
    db = _db()
    try:
        b = {c["chang_id"] for c in DX.soat(db, date(2026, 10, 1), date(2026, 10, 31))["b_nghi_khai_nham"]["danh_sach"]}
    finally:
        db.close()
    assert p_nha in b
    assert p_ht not in b, "biển trùng xe HỢP TÁC là thuê ngoài thật, không phải «nghi khai nhầm»"
    client.post(_url(f"/{p_nha}/gan-xe"), headers=h, json={"vehicle_id": ID["nha"]})
    db = _db()
    try:
        b = {c["chang_id"] for c in DX.soat(db, date(2026, 10, 1), date(2026, 10, 31))["b_nghi_khai_nham"]["danh_sach"]}
    finally:
        db.close()
    assert p_nha not in b, "đã gắn tay mà nhóm B vẫn gọi tên — cửa gắn không đóng được vòng"


# ── X5 ───────────────────────────────────────────────────────────────────────────────────────
def _ma(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def test_x5_man_hinh_co_o_chon_khoa_va_nut_gan():
    if not FORM.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = _ma(FORM.read_text(encoding="utf-8"))
    assert 'g("xe-nha")' in src, "ô chọn phải đọc danh sách xe từ máy chủ, không gõ cứng"
    assert re.search(r'khoa:\s*"vehicle_id",[^}]*kieu:\s*"xe"', src), "mục Phương tiện thiếu ô chọn xe nhà"
    for khoa, theo in (("so_hieu", "plate"), ("so_cho", "seats"), ("xe_nha", "co")):
        assert re.search(rf'khoa:\s*"{khoa}"[^}}]*theoXe:\s*"{theo}"', src), f"ô {khoa} không khoá theo xe đã chọn"
    assert "d.vehicle_id = xe ? xe.id : null" in src, "dòng gửi đi không mang vehicle_id"
    assert re.search(r"/phuong-tien/\$\{r\.id\}/gan-xe", src), "thiếu nút gắn tay ở dòng đã ghi"
    assert "goi_y_gan" in src
    if DOI_XE.exists():
        assert "?tab=lop3" in _ma(DOI_XE.read_text(encoding="utf-8")), (
            "DX-2 nhóm B phải mở thẳng tab quyết toán để gắn")


# ── TỰ PHÁ ──────────────────────────────────────────────────────────────────────────────────
def test_xn1_tu_pha():
    """Luật xe nhà là một hàm. Nới nó ra (coi mọi xe là chọn được) thì X1/X3 phải bắt được."""
    from app.services import xe_nha as XN
    from app.models.hr import Vehicle
    cu = XN.chon_duoc
    try:
        XN.chon_duoc = lambda v: True
        db = _db()
        try:
            ids = {v.id for v in XN.ds_chon_duoc(db)}
        finally:
            db.close()
        assert ID["hop_tac"] in ids and ID["ban"] in ids
    finally:
        XN.chon_duoc = cu
    assert not XN.la_xe_nha(Vehicle(plate="X", kind="hop_tac", op_right="so_huu"))
    assert not XN.la_xe_nha(Vehicle(plate="X", kind="noi_bo", op_right="thue"))
    if FORM.exists():
        src = _ma(FORM.read_text(encoding="utf-8")).replace('theoXe: "plate"', "")
        assert not re.search(r'khoa:\s*"so_hieu"[^}]*theoXe:\s*"plate"', src)
