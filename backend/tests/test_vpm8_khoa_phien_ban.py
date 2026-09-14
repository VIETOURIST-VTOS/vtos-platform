"""VPM-8 – khoá 409 phải có mặt ở MỌI cửa sửa của bảng đã khai, không chỉ ở hai chỗ.

Vì sao bộ kiểm này tồn tại: V10 (08/9/2026) dựng cột `phien_ban` và hàm `kiem_phien_ban`, rồi khai
mười hai bảng "có phiên bản". Đo lại ngày 11/9/2026: **20 bảng mang cột ấy, nhưng chỉ 2 cửa sửa gọi
kiểm** — dự toán tour và báo giá. Mười tám bảng còn lại mang một cột KHÔNG AI ĐỌC.

Đó là kiểu hỏng tệ hơn không làm gì: người đọc mã thấy cột `phien_ban` trong mô hình và tin rằng chỗ
ấy đã được canh, trong khi hai người sửa cùng một hồ sơ xe, một hồ sơ nhân sự, một số tài khoản nhà
cung cấp vẫn đè lên nhau lặng lẽ y như trước V10.

Bộ kiểm này hỏi hai câu, và câu thứ hai mới là câu thật:

  A  KHAI ĐỦ      – mọi bảng có cột `phien_ban` đều đã được xếp: hoặc có cửa sửa mang khoá, hoặc
                    được khai rõ là CHƯA CÓ CỬA SỬA kèm lý do, hoặc dùng khoá tên khác.
  B  KHOÁ THẬT SỰ CHẶN – gọi cửa sửa với số phiên bản CŨ thì máy chủ trả 409 kèm nội dung mới.
                    Đây là phép thử đi qua đường dẫn thật; khai trong bảng mà cửa không chặn thì đỏ.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm8.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
import ast
import pathlib

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
GOC = pathlib.Path(__file__).resolve().parents[1]


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _phien():
    from app.db.session import SessionLocal
    return SessionLocal()


# ══════════════════ A – KHAI ĐỦ, KHÔNG BỎ SÓT BẢNG NÀO ══════════════════
def _bang_co_cot_phien_ban() -> set[str]:
    import app.main  # noqa: F401 – nạp trọn mô hình
    from app.db.session import Base
    return {t for t, tb in Base.metadata.tables.items() if "phien_ban" in tb.columns}


def test_a1_moi_bang_co_cot_phien_ban_deu_duoc_XEP_MOT_CHO():
    """Thêm cột `phien_ban` vào một bảng mà không khai gì thêm = thêm một cột không ai đọc."""
    from app.services import ghi_mot_lan as GML
    co_cot = _bang_co_cot_phien_ban()
    da_xep = set(GML.CUA_SUA_CO_KHOA) | set(GML.CHUA_CO_CUA_SUA) | set(GML.KHOA_TEN_KHAC)
    thieu = sorted(co_cot - da_xep)
    assert not thieu, (
        "Bảng mang cột `phien_ban` mà chưa xếp vào đâu trong app/services/ghi_mot_lan.py: "
        f"{thieu}. Chọn một trong ba: khai cửa sửa vào CUA_SUA_CO_KHOA, hoặc khai lý do vào "
        "CHUA_CO_CUA_SUA nếu bảng chưa có cửa sửa, hoặc KHOA_TEN_KHAC nếu nó đã có khoá tên khác. "
        "Cột có mà không ai đọc thì tệ hơn không có cột – nó làm người đọc mã tin rằng chỗ ấy đã được canh.")


def test_a2_bang_khai_co_cua_sua_thi_bang_do_phai_co_cot():
    from app.services import ghi_mot_lan as GML
    co_cot = _bang_co_cot_phien_ban()
    sai = sorted(b for b in GML.CUA_SUA_CO_KHOA if b not in co_cot)
    assert not sai, f"Khai có cửa sửa mang khoá nhưng bảng không có cột phien_ban: {sai}"


def test_a3_moi_cua_sua_da_khai_deu_GOI_THAT_hai_ham_khoa():
    """Đọc bằng cây cú pháp, không phải tìm chuỗi trong cả tệp: hàm ĐƯỢC KHAI phải tự nó gọi cả
    `kiem_phien_ban` lẫn `tang_phien_ban`. Tìm chuỗi trong cả tệp thì một hàm khác trong cùng tệp có
    gọi là đủ làm phép thử xanh – đúng kiểu báo an toàn giả."""
    from app.services import ghi_mot_lan as GML
    thieu = []
    for bang, (tep, ham) in GML.CUA_SUA_CO_KHOA.items():
        p = GON = GOC / tep
        assert p.exists(), f"{bang}: khai cửa sửa ở {tep} nhưng không có tệp ấy"
        cay = ast.parse(GON.read_text(encoding="utf-8"))
        dinh = next((n for n in ast.walk(cay)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ham), None)
        assert dinh is not None, f"{bang}: không có hàm {ham}() trong {tep}"
        goi = {n.func.attr for n in ast.walk(dinh)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        con = [t for t in ("kiem_phien_ban", "tang_phien_ban") if t not in goi]
        if con:
            thieu.append(f"{bang} ({tep}::{ham}) thiếu {', '.join(con)}")
    assert not thieu, "Cửa sửa đã khai mà không gọi đủ hai hàm khoá:\n  " + "\n  ".join(thieu)


def test_a4_ly_do_chua_co_cua_sua_phai_viet_ra_bang_loi():
    """"Chưa có cửa sửa" là cách dễ nhất để một bảng được cho qua, nên phải viết ra vì sao."""
    from app.services import ghi_mot_lan as GML
    cut = sorted(b for b, ly in GML.CHUA_CO_CUA_SUA.items() if len((ly or "").strip()) < 15)
    assert not cut, f"Khai 'chưa có cửa sửa' mà lý do quá ngắn để đọc được: {cut}"


# ══════════════════ B – KHOÁ THẬT SỰ CHẶN (đi qua đường dẫn thật) ══════════════════
def _booking():
    ds = client.get("/api/v1/bookings", headers=login("ketoan")).json()
    con = [b for b in ds if not b.get("cancelled") and not b.get("locked")]
    if not con:
        pytest.skip("dữ liệu mẫu không có booking mở")
    return con[0]


def test_b1_BOOKING_gui_phien_ban_cu_thi_bi_tu_choi_409():
    """Đây đúng là ví dụ mà V10 nêu ra: sale sửa khách, kế toán sửa số tiền. Cột có từ 08/9 nhưng
    cửa này chưa bao giờ đọc nó – phép thử này là chỗ chứng minh nay nó có đọc."""
    b = _booking()
    r1 = client.put(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan"),
                    json={"phien_ban": b.get("phien_ban", 1), "care_note": "người thứ nhất sửa"})
    assert r1.status_code == 200, r1.text

    # Người thứ hai vẫn cầm bản cũ.
    r2 = client.put(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan"),
                    json={"phien_ban": b.get("phien_ban", 1), "care_note": "người thứ hai sửa"})
    assert r2.status_code == 409, f"người sau ghi đè được lên người trước: {r2.status_code}"
    d = r2.json()["detail"]
    assert d["gate"] == "LECH_PHIEN_BAN"
    assert d["noi_dung_moi"], "từ chối mà KHÔNG kèm nội dung mới – đẩy việc so sánh về phía người dùng"
    assert d["dang_co"] > d["gui_len"]


def test_b2_BOOKING_khong_gui_phien_ban_thi_van_cho_qua():
    """Màn hình cũ chưa kịp sửa vẫn phải dùng được. Siết toàn bộ giao diện trong một lần là cách
    chắc chắn để có một buổi sáng không ai làm việc được."""
    b = _booking()
    r = client.put(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan"),
                   json={"care_note": "màn hình cũ, không gửi phiên bản"})
    assert r.status_code == 200, r.text


def test_b3_BOOKING_phien_ban_tang_sau_moi_lan_sua():
    b = _booking()
    truoc = client.get(f"/api/v1/bookings/{b['id']}", headers=login("ketoan")).json()["phien_ban"]
    client.put(f"/api/v1/bookings/{b['id']}", headers=login("dh.lan"),
               json={"phien_ban": truoc, "care_note": "sửa lần nữa"})
    sau = client.get(f"/api/v1/bookings/{b['id']}", headers=login("ketoan")).json()["phien_ban"]
    assert sau == truoc + 1, f"phiên bản không tăng: {truoc} → {sau}"


_N = {"i": 0}


def _ncc():
    """Tự dựng nhà cung cấp qua đúng cửa tạo. KHÔNG bỏ qua khi dữ liệu mẫu trống: một phép thử
    bị bỏ qua là một phép thử không chứng minh gì, mà lại hiện màu xanh."""
    from app.models.suppliers import Supplier
    _N["i"] += 1
    r = client.post("/api/v1/ncc", headers=login("ketoan"),
                    json={"ten": f"NCC thử VPM-8 {_N['i']}", "loai": "khac", "note": "phép thử"})
    assert r.status_code in (200, 201), r.text
    sid = r.json().get("id") or r.json().get("ncc", {}).get("id")
    db = _phien()
    try:
        if sid is None:
            x = db.query(Supplier).order_by(Supplier.id.desc()).first()
            sid = x.id
        s = db.get(Supplier, sid)
        return s.id, int(s.phien_ban or 1)
    finally:
        db.close()


def test_b4_NHA_CUNG_CAP_gui_phien_ban_cu_thi_bi_tu_choi_409():
    """Lý do bảng này nằm trong danh sách, viết nguyên văn từ V10: 'số tài khoản nhà cung cấp –
    sửa đè là chuyển tiền nhầm chỗ'."""
    sid, pb = _ncc()
    r1 = client.put(f"/api/v1/ncc/{sid}", headers=login("ketoan"),
                    json={"phien_ban": pb, "note": "người thứ nhất"})
    assert r1.status_code == 200, r1.text
    r2 = client.put(f"/api/v1/ncc/{sid}", headers=login("ketoan"),
                    json={"phien_ban": pb, "note": "người thứ hai"})
    assert r2.status_code == 409, f"sửa đè được hồ sơ nhà cung cấp: {r2.status_code} {r2.text[:200]}"
    assert r2.json()["detail"]["gate"] == "LECH_PHIEN_BAN"


def _lead():
    from app.models.crm import Lead
    _N["i"] += 1
    r = client.post("/api/v1/leads", headers=login("kd.hoa"),
                    json={"phone": f"09880{_N['i']:05d}", "name": "Khách thử VPM-8", "channel": "Khác"})
    assert r.status_code in (200, 201), r.text
    db = _phien()
    try:
        x = db.query(Lead).order_by(Lead.id.desc()).first()
        return x.id, int(x.phien_ban or 1)
    finally:
        db.close()


def test_b5_LEAD_gui_phien_ban_cu_thi_bi_tu_choi_409():
    lid, pb = _lead()
    r1 = client.put(f"/api/v1/leads/{lid}", headers=login("kd.hoa"),
                    json={"phien_ban": pb, "note": "người thứ nhất"})
    assert r1.status_code == 200, r1.text
    r2 = client.put(f"/api/v1/leads/{lid}", headers=login("kd.hoa"),
                    json={"phien_ban": pb, "note": "người thứ hai"})
    assert r2.status_code == 409, f"sửa đè được lead: {r2.status_code}"


def _san_pham():
    from app.models.core import Product
    _N["i"] += 1
    ma = f"PTVPM8{_N['i']:03d}"
    r = client.post("/api/v1/products", headers=login("tp.dieuhanh"),
                    json={"code": ma, "name": f"Sản phẩm thử VPM-8 {_N['i']}"})
    assert r.status_code in (200, 201), r.text
    db = _phien()
    try:
        p = db.query(Product).filter(Product.code == ma).first()
        return p.id, p.code, p.name, int(p.phien_ban or 1)
    finally:
        db.close()


def test_b6_SAN_PHAM_gui_phien_ban_cu_thi_bi_tu_choi_409():
    pid, code, ten, pb = _san_pham()
    than = {"code": code, "name": ten}
    r1 = client.put(f"/api/v1/products/{pid}", headers=login("tp.dieuhanh"), json={**than, "phien_ban": pb})
    assert r1.status_code == 200, r1.text
    r2 = client.put(f"/api/v1/products/{pid}", headers=login("tp.dieuhanh"), json={**than, "phien_ban": pb})
    assert r2.status_code == 409, f"sửa đè được sản phẩm: {r2.status_code}"


def test_b7_tu_choi_luon_kem_NOI_DUNG_MOI_chu_khong_chi_bao_tai_lai():
    """Câu 'bản ghi đã đổi, tải lại đi' đẩy việc so sánh về phía người dùng đúng lúc họ vừa gõ xong.
    Luật của V10 là từ chối PHẢI kèm nội dung mới; VPM-8 giữ luật ấy ở mọi cửa mới gắn."""
    sid, pb = _ncc()
    client.put(f"/api/v1/ncc/{sid}", headers=login("ketoan"), json={"phien_ban": pb, "note": "x"})
    r = client.put(f"/api/v1/ncc/{sid}", headers=login("ketoan"), json={"phien_ban": pb, "note": "y"})
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d.get("noi_dung_moi"), "409 mà không kèm nội dung mới"
    assert "phien_ban" in d["noi_dung_moi"], "nội dung mới không nói bản hiện tại là bao nhiêu"
