"""Phiếu lương của chính người đăng nhập – lối vào cho MỌI vai trò (08/9/2026).

Vì sao có tệp này. Endpoint phiếu lương cá nhân đã có từ trước và ai đăng nhập cũng gọi được, nhưng
/payroll chỉ chuyển hướng sang /hr – mà /hr thì tài xế, hướng dẫn viên và chuyên viên visa không mở
được. Quyền có, dữ liệu có, chỉ thiếu cái cửa. Người lao động không xem được lương của chính mình là
chỗ khó chấp nhận nhất trong cả hệ thống.

Chỗ dễ sai khi sửa: để trang chạy được cho mọi vai trò thì phải mở một tiền tố API cho mọi vai trò.
Nếu mở nhầm /api/v1/payroll-runs – tiền tố chứa cả bảng lương TOÀN CÔNG TY – thì hàng rào ngoài của
bảng lương công ty bị hạ cho cả 20 vai trò, chỉ còn hàng rào trong đỡ. Tệp này canh đúng chỗ ấy: tiền
tố mở phải là /api/v1/phieu-luong, và tài xế phải bị chặn ở /api/v1/payroll-runs.
"""
import os, sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_phieu_luong.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_phieu_luong.db", "test_phieu_luong.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, ROLES
from app.models.hr import Employee
from app.services import access as AC

client = TestClient(app)
MK = "phieu123456"
P = f"{date.today() - timedelta(days=14):%Y-%m}"
MA_TX = "NS0013"      # tài xế có sẵn trong dữ liệu mẫu – dùng hồ sơ THẬT của bộ tính lương thay vì
                      # dựng một hồ sơ riêng, để phép thử đi qua đúng bộ lọc mà bảng lương thật dùng


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        # một tài xế THẬT: hồ sơ nhân sự có sẵn trong dữ liệu mẫu, nối thêm một tài khoản vai trò xe_hdv
        e = db.execute(select(Employee).where(Employee.code == MA_TX)).scalars().first()
        assert e is not None, f"dữ liệu mẫu không có hồ sơ {MA_TX}"
        u = db.execute(select(User).where(User.username == "pl_taixe")).scalars().first()
        if u is None:
            u = User(username="pl_taixe", full_name=e.full_name, role="xe_hdv",
                     department=e.department, staff_code=MA_TX, password_hash=hash_password(MK), active=True)
            db.add(u); db.commit(); db.refresh(u)
        e.user_id = u.id; db.commit()
        # một tài khoản KHÔNG có hồ sơ nhân sự – trạng thái phải nói ra, không được im lặng
        if db.execute(select(User).where(User.username == "pl_khong_ho_so")).scalars().first() is None:
            db.add(User(username="pl_khong_ho_so", full_name="Không hồ sơ", role="xe_hdv",
                        department="van_tai", staff_code="", password_hash=hash_password(MK), active=True))
            db.commit()
        db.close()
        # lập bảng lương kỳ P để có dòng của tài xế, rồi đưa ra khỏi trạng thái nháp – luồng ba bước
        # (Kế toán xác nhận → HCNS lập → TGĐ ký) đã có phép thử riêng ở test_hr, ở đây chỉ cần một kỳ
        # KHÔNG còn là nháp để phiếu cá nhân mở được.
        client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns", "Vtos@Demo#2026"))
        from app.db.session import SessionLocal as _SL
        from app.models.hr import PayrollRun as _PR
        _db = _SL()
        _run = _db.execute(select(_PR).where(_PR.period == P)).scalars().first()
        assert _run is not None, f"chưa lập được bảng lương kỳ {P}"
        assert any(r.get("ma") == MA_TX for r in (_run.rows or [])), \
            f"bảng lương kỳ {P} không có dòng của mã {MA_TX}"
        _run.status = "hcns_lap"; _db.commit(); _db.close()
        yield


def login(un, mk=MK):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": mk})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------- Tiền tố mở cho mọi người phải là tiền tố CHỈ chứa việc cá nhân ----------------
def test_moi_vai_tro_deu_cham_duoc_tien_to_phieu_luong_ca_nhan():
    for vai in ROLES:
        assert any(p.startswith("/api/v1/phieu-luong") for p in AC.pham_vi_day_du(vai)), \
            f"{vai} không chạm được phiếu lương của chính mình"


def test_khong_mo_tien_to_bang_luong_toan_cong_ty_cho_vai_tro_hep():
    """Nếu ai đó sửa cho tiện bằng cách khai /api/v1/payroll-runs vào màn hình của mọi người, hàng rào
    ngoài của bảng lương TOÀN CÔNG TY biến mất với cả 20 vai trò và chỉ còn hàng rào trong đỡ."""
    for vai in ("xe_hdv", "nv_visa", "nv_kd", "tp_hd", "gd_doi_xe"):
        cho = AC.pham_vi_day_du(vai)
        assert not any(p.startswith("/api/v1/payroll-runs") for p in cho), \
            f"{vai} chạm được tiền tố bảng lương toàn công ty"


def test_tai_xe_bi_chan_that_o_bang_luong_toan_cong_ty():
    r = client.get(f"/api/v1/payroll-runs/{P}", headers=login("pl_taixe"))
    assert r.status_code == 403, f"tài xế mở được bảng lương toàn công ty: {r.status_code}"


# ---------------- Tài xế mở được phiếu của chính mình ----------------
def test_tai_xe_liet_ke_duoc_ky_luong_cua_minh():
    r = client.get("/api/v1/phieu-luong/ky-cua-toi", headers=login("pl_taixe"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["co_ho_so"] is True and d["ma_nv"] == MA_TX
    assert any(x["period"] == P for x in d["rows"]), f"không thấy kỳ {P} trong danh sách của tài xế"


def test_tai_xe_mo_duoc_phieu_luong_cua_chinh_minh():
    r = client.get(f"/api/v1/phieu-luong/{P}", headers=login("pl_taixe"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nhan_su"]["ma"] == MA_TX
    for k in ("thu_nhap", "khoan_tru", "thuc_nhan"):
        assert k in d, f"phiếu lương thiếu khối {k}"


def test_tai_xe_khong_xem_duoc_phieu_cua_nguoi_khac():
    """Cùng một endpoint, đổi mã nhân viên. Đây là chỗ một dòng lọc thiếu làm lộ lương cả công ty."""
    r = client.get(f"/api/v1/phieu-luong/{P}", params={"ma": "115"}, headers=login("pl_taixe"))
    assert r.status_code == 403, f"tài xế xem được phiếu người khác: {r.status_code}"


# ---------------- Trạng thái chưa xong phải nói ra ----------------
def test_tai_khoan_chua_gan_ho_so_duoc_bao_ro_chu_khong_tra_bang_rong():
    """Bảng rỗng không lời giải thích thì người lao động tưởng mình không có lương. Phải nói đúng việc
    cần làm và nói rõ họ không tự sửa được."""
    r = client.get("/api/v1/phieu-luong/ky-cua-toi", headers=login("pl_khong_ho_so"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["co_ho_so"] is False and d["rows"] == []
    assert "HCNS" in d["message"], "không chỉ ra ai là người sửa được"


def test_khong_dua_ban_nhap_robot_cho_nguoi_lao_dong():
    """Bản nháp là số robot tính chưa ai xác nhận. Đưa cho người lao động xem là tạo ra một con số họ
    nhớ mà công ty không đứng sau."""
    from app.db.session import SessionLocal
    from app.models.hr import PayrollRun
    db = SessionLocal()
    run = db.execute(select(PayrollRun).where(PayrollRun.period == P)).scalars().first()
    truoc = run.status
    run.status = "nhap"; db.commit()
    try:
        d = client.get("/api/v1/phieu-luong/ky-cua-toi", headers=login("pl_taixe")).json()
        assert not any(x["period"] == P for x in d["rows"]), "bản nháp lọt xuống người lao động"
        r = client.get(f"/api/v1/phieu-luong/{P}", headers=login("pl_taixe"))
        assert r.status_code == 422, f"mở thẳng đường dẫn vẫn đọc được bản nháp: {r.status_code}"
    finally:
        run.status = truoc; db.commit(); db.close()


# ---------------- Lối vào trên giao diện ----------------
def test_phieu_luong_khong_bi_an_khoi_menu_cua_bat_ky_vai_tro_nao():
    """Cả việc mở quyền lẫn việc dựng trang đều vô nghĩa nếu menu không có mục.

    Lưu ý đường dẫn: màn hình này là /phieu-luong, KHÔNG phải /payroll. /payroll đã có quyết định ngày
    07/9 rằng tài xế, HDV, chuyên viên visa và GĐ đội xe không được thấy – vì lúc ấy nó nghĩa là bảng
    lương công ty. Đổi nghĩa đường dẫn đó là lật lại quyết định ấy mà không ai nhìn ra."""
    assert "/phieu-luong" in AC.MAN_HINH_KHONG_DUOC_AN
    assert "/payroll" not in AC.MAN_HINH_KHONG_DUOC_AN, \
        "quyết định 07/9: bốn vai trò hẹp không thấy màn hình bảng lương công ty"
    from app.db.session import SessionLocal
    db = SessionLocal()
    for vai in ("xe_hdv", "nv_visa", "tp_hd", "gd_doi_xe", "nv_kd"):
        gia = User(id=0, username="x", full_name="x", role=vai, department="", staff_code="",
                   active=True, password_hash="")
        assert "/phieu-luong" in AC.menus_for(gia, None), f"{vai} không có mục phiếu lương trên menu"
        assert "/phieu-luong" not in AC.hidden_menus_for(gia, None), f"{vai}: hai danh sách nói ngược nhau"
    db.close()
