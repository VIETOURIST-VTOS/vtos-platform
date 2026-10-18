# -*- coding: utf-8 -*-
"""QL-1 · Ô CẤP NGOẠI LỆ QUYỀN TRÊN /access — 17/10/2026 (Chủ tịch duyệt bản xem thử cùng ngày).

Chuyện đo được: `POST /access/grants` có từ lâu, nhưng màn hình chỉ liệt kê và thu hồi. Sáng 17/10
cấp quyền duyệt công bố nhận xét cho anh Thắng phải chạy lệnh tay trong trình duyệt — một cửa máy
chủ không có ô nhập là một việc còn thiếu (ranh giới Chủ tịch đặt 09/9: mỗi con số, mỗi quyền phải
có một cửa nhập cho người dùng).

  Q1  danh sách màn hình CẤP ĐƯỢC đến từ máy chủ, và máy chủ nhận đúng từng phần tử của nó
  Q2  cấp được cả hai loại bằng giá trị lấy từ danh sách ấy; luật 90 ngày vẫn ở máy chủ
  Q3  màn hình không gõ lại danh sách năng lực, và gửi đi đủ năm trường
  Q4  ô cấp mở TRÊN bảng tài khoản (bài học HS-8), và chỉ Chủ tịch/TGĐ thấy nút cấp
  Q5  khối «Ngoại lệ» không còn ẩn khi rỗng với Chủ tịch/TGĐ
Cuối tệp là bản tự phá: hàng rào không đỏ được là hàng rào rỗng.
"""
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ql1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ql1.db"):
    os.remove("test_ql1.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services import access as AC  # noqa: E402
from app.models.core import CAPABILITIES, GRANT_MAX_DAYS  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "access" / "page.tsx"
O_CAP = GOC / "web" / "components" / "CapNgoaiLe.tsx"
MK = "Vtos@Demo#2026"
client = TestClient(app)
ID: dict = {}


def _ma(src: str) -> str:
    """Bỏ chú thích — một chú thích nhắc tên cửa không phải là gọi cửa."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"\{\s*/\*.*?\*/\s*\}", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def _tao(username, role, ten):
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    db = SessionLocal()
    u = User(username=username, full_name=ten, role=role, staff_code=username.upper()[:8],
             password_hash=hash_password(MK), active=True, must_change_password=False)
    db.add(u); db.commit(); uid = u.id; db.close()
    return uid


def _h(u):
    r = client.post("/api/v1/auth/login", data={"username": u, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module", autouse=True)
def _dung():
    global client
    with TestClient(app) as c:
        client = c
        ID["ct"] = _tao("chutich_ql1", "chutich", "Chủ tịch QL1")
        ID["nhan"] = _tao("nhan_ql1", "tp_hd", "Người nhận QL1")
        yield


# ── Q1 ───────────────────────────────────────────────────────────────────────────────────────
def test_q1_danh_sach_man_hinh_den_tu_may_chu_va_khop_cua_cap():
    r = client.get("/api/v1/access/grants", headers=_h("chutich_ql1"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["capabilities"] == CAPABILITIES and d["max_days"] == GRANT_MAX_DAYS
    mh = d.get("man_hinh")
    assert mh, "GET /access/grants không trả danh sách màn hình — ô cấp loại «Màn hình» sẽ rỗng"
    assert set(mh) <= set(AC.ALL_MENU_PATHS), "trả ra màn hình mà cửa cấp sẽ từ chối"
    assert not [p for p in mh if "[" in p], "khuôn trang động không phải một màn hình cấp được"
    assert "/duyet-cong-bo" in mh and "/access" in mh


# ── Q2 ───────────────────────────────────────────────────────────────────────────────────────
def test_q2_cap_duoc_ca_hai_loai_va_luat_90_ngay_van_o_may_chu():
    h = _h("chutich_ql1")
    mh = client.get("/api/v1/access/grants", headers=h).json()["man_hinh"]
    den = (date.today() + timedelta(days=GRANT_MAX_DAYS)).isoformat()
    for kind, value in (("capability", "duyet_cong_bo_nhan_xet"), ("menu", mh[0])):
        r = client.post("/api/v1/access/grants", headers=h, json={
            "user_id": ID["nhan"], "kind": kind, "value": value, "to_date": den, "reason": "thử QL-1"})
        assert r.status_code == 201, (kind, r.text)
    qua = (date.today() + timedelta(days=GRANT_MAX_DAYS + 1)).isoformat()
    r = client.post("/api/v1/access/grants", headers=h, json={
        "user_id": ID["nhan"], "kind": "capability", "value": "bang_luong", "to_date": qua, "reason": "x"})
    assert r.status_code == 422, "máy chủ phải chặn quá hạn tối đa — màn hình không phải chỗ canh luật này"
    # Người nhận (tp_hd) không tự cấp được cho mình.
    r = client.post("/api/v1/access/grants", headers=_h("nhan_ql1"), json={
        "user_id": ID["nhan"], "kind": "capability", "value": "bang_luong", "to_date": den, "reason": "x"})
    assert r.status_code == 403


# ── Q3 ───────────────────────────────────────────────────────────────────────────────────────
def test_q3_o_cap_khong_go_lai_danh_sach_va_gui_du_truong():
    if not O_CAP.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = _ma(O_CAP.read_text(encoding="utf-8"))
    go_lai = [k for k in CAPABILITIES if f'"{k}"' in src or f"'{k}'" in src]
    assert not go_lai, f"ô cấp gõ cứng mã năng lực {go_lai} — phải đọc meta.capabilities từ máy chủ"
    for doc in ("meta?.capabilities", "meta?.man_hinh", "meta?.max_days"):
        assert doc in src, f"ô cấp không đọc {doc} từ máy chủ"
    m = re.search(r'api\("/access/grants",\s*\{\s*method:\s*"POST",\s*json:\s*\{([^}]*)\}', src, re.S)
    assert m, "ô cấp không gửi POST /access/grants"
    for t in ("user_id", "kind", "value", "to_date", "reason"):
        assert re.search(rf"\b{t}\b", m.group(1)), f"ô cấp không gửi trường {t}"
    assert "vo_han" not in m.group(1) and "to_date: null" not in m.group(1), (
        "ô cấp không được gửi lời cấp KHÔNG THỜI HẠN — Chủ tịch chốt không có ô ấy trên màn hình")


# ── Q4 ───────────────────────────────────────────────────────────────────────────────────────
def test_q4_o_cap_mo_tren_bang_va_chi_lanh_dao_thay_nut():
    if not TRANG.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = _ma(TRANG.read_text(encoding="utf-8"))
    o = src.find("<CapNgoaiLe")
    bang = src.find("<th>Mã NV</th>")
    assert o != -1, "màn /access không còn gắn ô cấp ngoại lệ"
    assert bang != -1 and o < bang, "ô cấp phải mở TRÊN bảng tài khoản — dưới bảng 121 dòng là không mở (HS-8)"
    assert re.search(r"capMo\s*&&\s*laLanhDao\b", src), "ô cấp phải chỉ dành cho Chủ tịch/TGĐ"
    nut = [m.start() for m in re.finditer(r">\s*(\+ )?Cấp ngoại lệ\s*<", src)]
    assert len(nut) >= 2, "thiếu nút cấp ở đầu khối hoặc trên từng dòng tài khoản"
    for i in nut:
        assert "laLanhDao &&" in src[max(0, i - 400):i], "nút cấp hiện cho vai không cấp được"


# ── Q5 ───────────────────────────────────────────────────────────────────────────────────────
def test_q5_khoi_ngoai_le_khong_an_khi_rong_voi_lanh_dao():
    if not TRANG.exists():
        pytest.skip("không có mã giao diện cạnh mã máy chủ")
    src = _ma(TRANG.read_text(encoding="utf-8"))
    assert "grants?.rows?.length > 0 && <>" not in src, "khối Ngoại lệ lại ẩn khi rỗng — mất lối vào cấp lần đầu"
    assert re.search(r"laLanhDao\s*\|\|\s*grants\.rows\?\.length\s*>\s*0", src)


# ── TỰ PHÁ ──────────────────────────────────────────────────────────────────────────────────
def test_ql1_tu_pha():
    if not (TRANG.exists() and O_CAP.exists()):
        pytest.skip("không có mã giao diện")
    src = _ma(TRANG.read_text(encoding="utf-8"))
    # Q4: dời ô cấp xuống dưới bảng thì vị trí phải đảo.
    khoi = re.search(r"\{capMo && laLanhDao.*?/>\}", src, re.S).group(0)
    doi = src.replace(khoi, "").replace("</tbody></table></div>", "</tbody></table></div>" + khoi, 1)
    assert doi.find("<CapNgoaiLe") > doi.find("<th>Mã NV</th>")
    # Q3: gõ cứng một mã năng lực vào ô cấp thì phải bị gọi tên.
    o = _ma(O_CAP.read_text(encoding="utf-8")) + '\nconst X = "bang_luong";'
    assert [k for k in CAPABILITIES if f'"{k}"' in o]
    # Q5: dựng lại điều kiện cũ thì phải bị bắt.
    assert "grants?.rows?.length > 0 && <>" in src.replace(
        "grants && (laLanhDao || grants.rows?.length > 0) && <>", "grants?.rows?.length > 0 && <>")
