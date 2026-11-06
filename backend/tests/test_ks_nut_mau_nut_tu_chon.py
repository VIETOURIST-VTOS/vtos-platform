"""KS-NUT · 07/11/2026 — anh Tuấn: "chọn cả A và B cho người dùng tự bấm điều khiển vào nút giao diện".

Bản xem thử «Navy bên trong VTOS» có hai phương án màu nút ở nền tối:
  A "navy" — nút / chip / nhãn đang chọn navy #14538D viền #5A9BD4 (mặc định);
  B "sang" — giữ xanh sáng #1E63C8.
Người dùng tự chọn trong bảng «Giao diện»; lựa chọn cất theo tài khoản (users.gd_mau_nut).
"""
import os, re, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ks_nut.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks_nut.db"):
    os.remove("test_ks_nut.db")
from fastapi.testclient import TestClient
from app.main import app

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W = os.path.join(ROOT, "web")
client = TestClient(app)


def _doc(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def _h():
    with client:
        pass
    tok = client.post("/api/v1/auth/login", data={"username": "chutich", "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_cua_ghi_nhan_hai_phuong_an_va_chan_gia_tri_la():
    with client:
        h = _h()
        me = client.get("/api/v1/auth/me", headers=h).json()
        assert me["giao_dien"]["mau_nut"] is None, "chưa chọn thì phải là None (rỗng khác mặc định)"
        assert me["giao_dien_mac_dinh"]["mau_nut"] == "navy", "mặc định là phương án A — navy đậm"
        for m in ("sang", "navy"):
            r = client.put("/api/v1/auth/giao-dien", headers=h, json={"mau_nut": m})
            assert r.status_code == 200 and r.json()["mau_nut"] == m, r.text
            assert client.get("/api/v1/auth/me", headers=h).json()["giao_dien"]["mau_nut"] == m
        assert client.put("/api/v1/auth/giao-dien", headers=h, json={"mau_nut": "do"}).status_code == 422
        # đổi nền không được xoá màu nút đã chọn
        client.put("/api/v1/auth/giao-dien", headers=h, json={"nen": "sang"})
        assert client.get("/api/v1/auth/me", headers=h).json()["giao_dien"]["mau_nut"] == "navy"
        # trả về mặc định xoá cả màu nút
        assert client.delete("/api/v1/auth/giao-dien", headers=h).json()["mau_nut"] is None
        assert client.get("/api/v1/auth/me", headers=h).json()["giao_dien"]["mau_nut"] is None


def test_ban_chuyen_doi_rong_khac_mac_dinh():
    v = os.path.join(ROOT, "backend", "alembic", "versions")
    ban = [f for f in os.listdir(v) if "mau_nut" in f]
    assert len(ban) == 1 and "giao_dien" not in ban[0]
    src = _doc(v, ban[0])
    assert 'server_default=""' in src and "gd_mau_nut" in src and 'down_revision = "ks20e1a3c5e7b9d135"' in src


def test_bang_giao_dien_co_hai_nut_mau_va_ve_truoc_khi_trang_ve():
    chon = _doc(W, "components", "ChonGiaoDien.tsx")
    assert '["navy", "Navy đậm"]' in chon and '["sang", "Xanh sáng"]' in chon
    assert "data-mau-nut" in chon and "mau_nut: m" in chon, "phải đặt lên <html> và ghi về máy chủ"
    lay = _doc(W, "app", "layout.tsx").split("<body>", 1)[0]
    assert "data-mau-nut" in lay, "kịch bản chống loé trong <head> phải đặt màu nút trước khi trang vẽ"


def test_mau_hai_phuong_an_dung_ban_xem_thu():
    tok = re.sub(r"/\*.*?\*/", "", _doc(W, "app", "tokens.css"), flags=re.S)
    m = re.search(r':root\[data-mau-nut="navy"\]:not\(\[data-nen="sang"\]\)\s*\{([^}]*)\}', tok)
    assert m, "thiếu khối màu của phương án A"
    assert re.search(r"--vtos-sky:\s*#14538D", m.group(1)) and re.search(r"--vtos-nut-vien:\s*#5A9BD4", m.group(1))
    assert re.search(r"--vtos-sky:\s*#1E63C8", tok), "phương án B giữ #1E63C8 ở :root"
    css = _doc(W, "app", "globals.css")
    assert "nav.tabs a.on{color:var(--navy);border-color:var(--vtos-tab-on)" in css, "tab đang chọn gạch #5A9BD4 thay vàng"
    assert "button.act{background:var(--navy2);color:#fff;border:1px solid var(--vtos-nut-vien)" in css
