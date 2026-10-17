# -*- coding: utf-8 -*-
"""DX-5 · HAI CỬA NHẬP CÒN THIẾU CỦA ĐỘI XE, và CỜ «THUÊ XE NGOÀI» CỦA CHUYẾN BÁN — 17/10/2026.

Ba chuyện, mỗi chuyện là một cửa ghi đã có mà không ai với tới được:

  1. `POST /fleet/phat-tai-xe` và `POST /fleet/gia-dau` có từ đợt DX-3 (16/10), nhưng không màn nào
     gọi — `ks_cua_nhap.py` còn khai sai là «cả hai đều có màn hình nhập tay trên /doi-xe». Vòng này
     dựng bốn trang con dưới /doi-xe (Chủ tịch duyệt bản xem thử 16/10).
  2. Hai cột `tours.thue_xe_ngoai` / `ly_do_thue_ngoai` (Chủ tịch chốt khai ở CHUYẾN BÁN) sinh ra
     cùng vòng — và ban đầu cũng không có cửa ghi nào. Nay có `PUT /quyet-toan-lop3/{tid}/thue-xe-ngoai`.
  3. Cờ ấy và các chặng ô tô của tờ quyết toán (vòng XN-1) là HAI LỜI KHAI về cùng một chuyện, khác
     tầng. Chủ tịch chốt 17/10: giữ cả hai, và máy phải nói ra khi chúng nói ngược nhau.

KHÔNG HÀNG RÀO CŨ NÀO THẤY VÒNG NÀY: `test_man_hinh_co_cua_nhap` đọc màn từ GROUPS của Shell.tsx, mà
bốn trang con cố ý không có mục menu. Tệp này là hàng rào riêng của chúng.

  D1  bốn trang có thật, khai ở CẢ HAI chỗ của access.py (cái bẫy: thiếu chỗ thứ hai thì chính Giám
      đốc đội xe — người duy nhất ghi được phạt — không thấy màn, mà mọi phép thử khác vẫn xanh)
  D2  mỗi trang gọi đúng cửa của nó, trong nhóm /api/v1/fleet; ô Kỳ lương không chạy theo ô Ngày;
      ô giá dầu không tự điền giá cũ
  D3  Giám đốc đội xe gọi được ô chọn tài xế, ghi được phạt; kế toán ghi được giá dầu, không ghi phạt
  D4  migration nối đúng một đầu mạch, và mặc định boolean viết được trên PostgreSQL
  D5  cửa khai cờ thuê xe ngoài: mã lý do, xoá lý do khi «không thuê», tờ đã ký đòi lý do + dấu vết
  D6  hai lời khai nói ngược nhau thì máy nói ra — cả hai chiều
  D7  lời khai của ks_cua_nhap đã được sửa
Cuối tệp là bản tự phá.
"""
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_dx5.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dx5.db"):
    os.remove("test_dx5.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services import access as AC  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
BACKEND = GOC / "backend"
WEB = GOC / "web" / "app"
TRANG = {
    "/doi-xe/phat-tai-xe": WEB / "doi-xe" / "phat-tai-xe" / "page.tsx",
    "/doi-xe/phat-tai-xe/moi": WEB / "doi-xe" / "phat-tai-xe" / "moi" / "page.tsx",
    "/doi-xe/gia-dau": WEB / "doi-xe" / "gia-dau" / "page.tsx",
    "/doi-xe/gia-dau/moi": WEB / "doi-xe" / "gia-dau" / "moi" / "page.tsx",
}
MIGRATION = BACKEND / "alembic" / "versions" / "dx5_tours_thue_xe_ngoai.py"
MK = "Vtos@Demo#2026"
client = TestClient(app)
ID: dict = {}


def _co_web() -> bool:
    return all(p.exists() for p in TRANG.values())


def _ma(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


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
        for ten, vai in (("gdx_dx5", "gd_doi_xe"), ("kt_dx5", "ketoan"), ("dh_dx5", "nv_dh"),
                         ("tp_dx5", "tp_dh")):
            ID[ten] = _tao_nguoi(ten, vai)
        from app.models.core import Tour
        from app.models.hr import Employee, Vehicle
        db = _db()
        nv = Employee(code="NVDX5", full_name="Điều hành DX5", department="dieu_hanh")
        tx = Employee(code="TXDX5", full_name="Tài xế DX5", department="doi_xe", position="Tài xế")
        db.add_all([nv, tx]); db.flush()
        xe = Vehicle(plate="51B-555.01", code="DX501", seats=45, kind="noi_bo", active=True,
                     lifecycle="dang_khai_thac", op_right="so_huu")
        db.add(xe); db.flush()
        t = Tour(code="DX5-1017", name="Thử cờ thuê xe ngoài", tour_type="doan_noi_dia",
                 operator_id=nv.id, start_date=date(2026, 10, 10), end_date=date(2026, 10, 12))
        db.add(t); db.commit()
        ID.update(tour=t.id, xe=xe.id, tx=tx.id)
        db.close()
        yield


# ── D1 ───────────────────────────────────────────────────────────────────────────────────────
def test_d1_bon_trang_co_that_va_khai_ca_hai_cho():
    if not _co_web():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    for duong in TRANG:
        assert duong in AC.ALL_MENU_PATHS, f"{duong} chưa khai trong ALL_MENU_PATHS"
        assert duong in AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"], (
            f"{duong} không có trong danh sách CHO PHÉP của gd_doi_xe — Giám đốc đội xe, người duy "
            "nhất ghi được phiếu phạt, sẽ không thấy màn của chính mình")
    # Không có mục menu riêng: đi tới bằng thanh việc của /doi-xe (đúng khuôn trang con TM-1).
    assert not [d for d in TRANG if d in AC.MENU_ROLES]


# ── D2 ───────────────────────────────────────────────────────────────────────────────────────
def test_d2_moi_trang_goi_dung_cua_cua_no():
    if not _co_web():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = {d: _ma(p.read_text(encoding="utf-8")) for d, p in TRANG.items()}
    assert '"/fleet/phat-tai-xe?ky="' in src["/doi-xe/phat-tai-xe"]
    assert '"/fleet/phat-tai-xe", {' in src["/doi-xe/phat-tai-xe/moi"]
    assert '"/fleet/tai-xe-chon"' in src["/doi-xe/phat-tai-xe/moi"]
    assert '"/fleet/gia-dau"' in src["/doi-xe/gia-dau"]
    assert '"/fleet/gia-dau", {' in src["/doi-xe/gia-dau/moi"]
    for d, s in src.items():
        goi = re.findall(r'api(?:<[^>]*>)?\(\s*"(/[a-z0-9-]+)', s)
        ngoai = [g for g in goi if g != "/fleet"]
        assert not ngoai, f"{d} gọi nhóm {ngoai} — ngoài MAN_HINH_API của /doi-xe thì vai đội xe ăn 403"
    # Luật 1: Kỳ lương khai riêng — ô Ngày đổi thì KHÔNG được đổi theo ô Kỳ.
    moi = src["/doi-xe/phat-tai-xe/moi"]
    assert len(re.findall(r"setKy\(", moi)) == 1, "Kỳ lương chỉ được đổi từ chính ô Kỳ — không suy từ ngày"
    # Luật 5: không tự điền giá gần nhất vào ô giá dầu.
    assert len(re.findall(r"setGia\(", src["/doi-xe/gia-dau/moi"])) <= 2, (
        "màn ghi giá dầu có thêm chỗ đặt giá vào ô — đừng gợi một con số vào ô nhập")
    for d in ("/doi-xe/phat-tai-xe/moi", "/doi-xe/gia-dau/moi"):
        assert re.search(r"<ThanhViec\s+toanMan\b", src[d]), f"{d} phải toàn màn (không thanh dọc)"


# ── D3 ───────────────────────────────────────────────────────────────────────────────────────
def test_d3_vai_nao_ghi_duoc_gi():
    g = _h("gdx_dx5")
    r = client.get("/api/v1/fleet/tai-xe-chon", headers=g)
    assert r.status_code == 200, r.text
    assert all(set(x) == {"id", "ho_ten", "code"} for x in r.json()["rows"]), "ô chọn tài xế lộ thêm trường"
    r = client.post("/api/v1/fleet/phat-tai-xe", headers=g, json={
        "driver_id": ID["tx"], "ky": "2026-10", "ngay": "2026-10-09", "so_tien": 200000,
        "ly_do": "đi muộn giờ đón khách"})
    assert r.status_code in (200, 201), r.text
    kt = _h("kt_dx5")
    r = client.post("/api/v1/fleet/gia-dau", headers=kt, json={"ngay": "2026-10-11", "gia_lit": 19850})
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/v1/fleet/phat-tai-xe", headers=kt, json={
        "driver_id": ID["tx"], "ky": "2026-10", "ngay": "2026-10-09", "so_tien": 1, "ly_do": "x"})
    assert r.status_code == 403, "kế toán không ghi phạt — chỉ Giám đốc đội xe"


# ── D4 ───────────────────────────────────────────────────────────────────────────────────────
def test_d4_migration_noi_dung_mot_dau_mach():
    src = MIGRATION.read_text(encoding="utf-8")
    assert re.search(r'^down_revision = "[0-9a-z_]+"', src, re.M), "down_revision còn để trống — đứt mạch"
    r = subprocess.run([sys.executable, "-m", "alembic", "heads"], cwd=BACKEND,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        pytest.skip("alembic không chạy được trong môi trường này")
    dau = [ln for ln in r.stdout.splitlines() if "(head)" in ln]
    assert len(dau) == 1, f"mạch migration có {len(dau)} đầu: {dau}"
    assert "server_default=sa.text(\"0\")" not in src and "sa.false()" in src, (
        "PostgreSQL từ chối DEFAULT 0 cho cột boolean — dùng sa.false()")


# ── D5 ───────────────────────────────────────────────────────────────────────────────────────
def _url():
    return f"/api/v1/quyet-toan-lop3/{ID['tour']}/thue-xe-ngoai"


def test_d5_cua_khai_co_thue_xe_ngoai():
    h = _h("dh_dx5")
    d = client.get(_url(), headers=h).json()
    assert d["thue_xe_ngoai"] is False and d["ly_do_thue_ngoai"] == ""
    from app.models.core import LY_DO_THUE_XE_NGOAI
    assert d["ly_do_chon"] == LY_DO_THUE_XE_NGOAI, "màn hình phải đọc danh sách lý do từ máy chủ"
    assert client.put(_url(), headers=h, json={"thue_xe_ngoai": True, "ly_do_thue_ngoai": "vi_thich"}).status_code == 422
    r = client.put(_url(), headers=h, json={"thue_xe_ngoai": True, "ly_do_thue_ngoai": "xe_nha_kin_lich"})
    assert r.status_code == 200 and r.json()["ly_do_thue_ngoai"] == "xe_nha_kin_lich"
    r = client.put(_url(), headers=h, json={"thue_xe_ngoai": False, "ly_do_thue_ngoai": "xe_nha_kin_lich"})
    assert r.json()["thue_xe_ngoai"] is False and r.json()["ly_do_thue_ngoai"] == "", (
        "«không thuê» không được mang theo một lý do cũ")
    assert client.put(_url(), headers=_h("gdx_dx5"), json={"thue_xe_ngoai": True}).status_code == 403


def test_d5_to_da_ky_doi_ly_do_va_de_dau_vet():
    from app.models.core import Tour
    db = _db(); t = db.get(Tour, ID["tour"]); t.closed_at = datetime.now(); db.commit(); db.close()
    try:
        tp = _h("tp_dx5")
        assert client.put(_url(), headers=tp, json={"thue_xe_ngoai": True}).status_code == 422
        r = client.put(_url(), headers=tp, json={"thue_xe_ngoai": True, "ly_do_thue_ngoai": "khach_chi_dinh",
                                               "ly_do_sua": "khách đổi ý chỉ định nhà xe"})
        assert r.status_code == 200, r.text
        dv = str(client.get(f"/api/v1/quyet-toan-lop3/{ID['tour']}/dau-vet", headers=tp).json())
        assert "thue_xe_ngoai" in dv, "sửa cờ trên tờ đã ký phải để dấu vết"
    finally:
        db = _db(); t = db.get(Tour, ID["tour"]); t.closed_at = None
        t.thue_xe_ngoai, t.ly_do_thue_ngoai = False, ""
        db.commit(); db.close()


# ── D6 ───────────────────────────────────────────────────────────────────────────────────────
def test_d6_hai_loi_khai_noi_nguoc_nhau_thi_may_noi_ra():
    h = _h("dh_dx5")
    pt = f"/api/v1/quyet-toan-lop3/{ID['tour']}/phuong-tien"
    assert client.get(_url(), headers=h).json()["lech"] is None, "chưa có chặng nào thì không có gì lệch"
    # Chiều 1: khai KHÔNG thuê, nhưng có chặng ô tô thuê ngoài.
    p1 = client.post(pt, headers=h, json={"loai": "o_to", "chang": "HCM – Đà Lạt", "so_hieu": "51B-999.99",
                                          "nha_cung_cap": "Nhà xe ngoài"}).json()["id"]
    d = client.get(_url(), headers=h).json()
    assert d["so_chang_thue_ngoai"] == 1 and d["lech"] and "KHÔNG thuê" in d["lech"]
    # Khai lại cờ thì hết lệch.
    d = client.put(_url(), headers=h, json={"thue_xe_ngoai": True, "ly_do_thue_ngoai": "xe_nha_kin_lich"}).json()
    assert d["lech"] is None
    # Chiều 2: khai CÓ thuê, nhưng mọi chặng ô tô là xe nhà.
    client.post(f"{pt}/{p1}/gan-xe", headers=h, json={"vehicle_id": ID["xe"]})
    d = client.get(_url(), headers=h).json()
    assert d["so_chang_thue_ngoai"] == 0 and d["lech"] and "xe nhà" in d["lech"]
    # Có thuê mà chưa chọn lý do: ghi được, nhưng máy nói ra.
    client.post(f"{pt}/{p1}/gan-xe", headers=h, json={"vehicle_id": None})
    d = client.put(_url(), headers=h, json={"thue_xe_ngoai": True, "ly_do_thue_ngoai": ""}).json()
    assert d["thue_xe_ngoai"] is True and d["lech"] and "chưa chọn lý do" in d["lech"]


def test_d6_man_hinh_hien_o_khai_va_cho_lech():
    form = GOC / "web" / "components" / "QuyetToanForm.tsx"
    if not form.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = _ma(form.read_text(encoding="utf-8"))
    assert re.search(r"/thue-xe-ngoai`,\s*\{\s*method:\s*\"PUT\"", src), "tờ quyết toán không có cửa khai cờ"
    assert "d.ly_do_chon" in src, "danh sách lý do phải đến từ máy chủ"
    assert "d.lech &&" in src, "chỗ lệch giữa hai lời khai không được hiện ra"
    # Gắn TRỰC TIẾP, không nằm sau một điều kiện: `{false && <ThueXeNgoai/>}` vẫn khớp tên mà ô không hiện.
    m = re.search(r"^\s*<ThueXeNgoai tourId=\{tourId\}", src, re.M)
    assert m, "ô khai cờ không được gắn trực tiếp vào tờ quyết toán"
    o, bang = m.start(), src.find('. Phương tiện`}')
    assert o != -1 and bang != -1 and o < bang, "ô khai cờ phải đứng ngay trên bảng Phương tiện"


# ── D7 ───────────────────────────────────────────────────────────────────────────────────────
def test_d7_loi_khai_cua_ks_cua_nhap_da_sua():
    src = (BACKEND / "app" / "services" / "ks_cua_nhap.py").read_text(encoding="utf-8")
    assert "cả hai đều có màn hình nhập tay trên /doi-xe" not in src
    assert "/doi-xe/phat-tai-xe" in src and "/doi-xe/gia-dau" in src


# ── TỰ PHÁ ──────────────────────────────────────────────────────────────────────────────────
def test_dx5_tu_pha():
    # D1: bỏ MAN_CON_DOI_XE khỏi danh sách cho phép của gd_doi_xe thì phải đỏ.
    cu = AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"]
    try:
        AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"] = tuple(p for p in cu if p not in AC.MAN_CON_DOI_XE)
        with pytest.raises(AssertionError):
            test_d1_bon_trang_co_that_va_khai_ca_hai_cho()
    finally:
        AC.RESTRICTED_ROLE_MENUS["gd_doi_xe"] = cu
    # D6: luật lệch nói «không có gì» thì phép thử phải đỏ.
    from app.services import xe_nha as XN
    goc = XN.lech_khai_thue_ngoai
    try:
        XN.lech_khai_thue_ngoai = lambda db, t: {**goc(db, t), "lech": None}
        with pytest.raises(AssertionError):
            test_d6_hai_loi_khai_noi_nguoc_nhau_thi_may_noi_ra()
    finally:
        XN.lech_khai_thue_ngoai = goc
