"""Báo cáo tự động hiện trên màn hình VTOS, cắt theo phòng ban (quyết định Chủ tịch 09/9/2026).

    "Báo cáo của các phòng ban thì hiện lên cho trưởng phòng hoặc giám đốc; toàn công ty thì hiện
     lên cho Chủ tịch và TGĐ. Không cần gửi mail hay Zalo."
    "Không cần VIẾT báo cáo, mà HIỆN báo cáo lên màn hình – nên cần luồng logic, phép tính, cấu trúc."

Bộ kiểm này canh ba nhóm việc, và nhóm thứ hai là nhóm dễ hỏng nhất:

  B1 CẮT ĐÚNG NGƯỜI – trưởng phòng chỉ thấy phòng mình; nhân viên không thấy báo cáo phòng
  B2 CẤU TRÚC ĐỦ ĐỂ DÙNG – mỗi chỉ tiêu phải mang cách tính và nguồn, chỉ tiêu đỏ phải nói cần làm gì
  B3 RỖNG KHÔNG PHẢI 0 – và chỉ tiêu rỗng không bị tô cảnh báo

Vì sao B2 đáng có một bộ kiểm riêng: một chỉ tiêu thiếu cách tính vẫn hiện ra bình thường trên màn
hình, không lỗi, không đỏ. Nó chỉ hỏng ở chỗ người dùng không tin con số và thôi không dùng bảng –
mà điều đó không phép thử thông thường nào bắt được. Nên phải bắt bằng một điều kiện về CẤU TRÚC.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_bcp.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.services import bao_cao_phong as BP

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        if u is None: pytest.skip(f"dữ liệu mẫu không có vai trò {vai}")
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ══════════════════════════ B1 – CẮT ĐÚNG NGƯỜI ══════════════════════════
def test_chu_tich_va_tgd_xem_duoc_toan_cong_ty_va_moi_phong():
    for vai in ("chutich", "tgd"):
        ds = BP.pham_vi_duoc_xem(vai)
        assert BP.TOAN_CTY in ds
        assert set(BP.PHONG) <= set(ds), f"{vai} thiếu phòng: {set(BP.PHONG) - set(ds)}"


def test_truong_phong_chi_xem_phong_minh_khong_xem_toan_cong_ty():
    """Chỗ quan trọng: trưởng phòng KHÔNG xem báo cáo toàn công ty. Không phải vì giấu, mà vì bản
    toàn công ty gộp số của mọi phòng – đưa cho một trưởng phòng là đưa hiệu quả phòng khác."""
    cap = {"tp_dh": "dieu_hanh", "gd_kd": "kd_le", "gd_doi_xe": "doi_xe",
           "tp_hd": "huong_dan", "ketoan": "ketoan", "hcns": "hcns"}
    for vai, phong in cap.items():
        ds = BP.pham_vi_duoc_xem(vai)
        assert phong in ds, f"{vai} không xem được báo cáo phòng mình ({phong})"
        assert BP.TOAN_CTY not in ds, f"{vai} đang xem được báo cáo toàn công ty"


def test_nhan_vien_khong_xem_bao_cao_phong():
    """Mỗi người thấy VIỆC CỦA MÌNH là một chuyện; bản tổng hợp hiệu quả cả phòng là chuyện khác."""
    for vai in ("nv_kd", "nv_dh", "nv_mkt", "xe_hdv", "hanh_chinh"):
        assert BP.pham_vi_duoc_xem(vai) == [], f"{vai} đang xem được báo cáo phòng"


def test_ban_kiem_soat_xem_tat_ca():
    """Kiểm soát mà chỉ được xem bản tóm tắt do bên bị kiểm soát chọn thì không kiểm được gì."""
    ds = BP.pham_vi_duoc_xem("bks")
    assert BP.TOAN_CTY in ds and set(BP.PHONG) <= set(ds)


def test_may_chu_CHAN_khi_xin_bao_cao_ngoai_pham_vi():
    """Chặn ở MÁY CHỦ, không chặn ở màn hình: màn hình chỉ vẽ thứ máy chủ trả về, nên lọc ở giao
    diện nghĩa là ai mở công cụ nhà phát triển cũng đọc được hết."""
    h = login("tp_dh")
    assert client.get("/api/v1/bao-cao?pham_vi=dieu_hanh&kind=ngay", headers=h).status_code == 200
    for cam in ("toan_cty", "ketoan", "kd_le"):
        r = client.get(f"/api/v1/bao-cao?pham_vi={cam}&kind=ngay", headers=h)
        assert r.status_code == 403, f"tp_dh xin được báo cáo {cam}: {r.status_code}"


def test_vai_tro_khong_co_bao_cao_thi_khong_vao_duoc_man_hinh():
    """Đã sửa kỳ vọng sau khi bộ kiểm chỉ ra mâu thuẫn: chú thích nói 'vẫn vào được và màn hình báo
    rõ', mã thì chặn ở cửa màn hình. Chọn CHẶN – một mục menu chết làm người ta bấm lại mỗi tuần để
    xem đã có chưa. Vai trò không có báo cáo nào thì không thấy mục menu luôn."""
    from app.services import access as AC
    h = login("nv_kd")
    assert client.get("/api/v1/bao-cao/pham-vi", headers=h).status_code == 403
    assert "nv_kd" not in AC.MENU_ROLES["/bao-cao"]


def test_cua_man_hinh_va_bang_pham_vi_KHOP_nhau():
    """Lệch một vai trò thì hoặc có người mở được màn hình mà không có báo cáo nào (bấm vào thấy
    trống, tưởng hệ thống hỏng), hoặc có người có báo cáo mà không vào được cửa."""
    from app.services import access as AC
    cua = set(AC.MENU_ROLES["/bao-cao"])
    for vai in cua:
        if vai in ("robot_ks",):      # robot đọc qua API, không mở màn hình
            continue
        assert BP.pham_vi_duoc_xem(vai), f"{vai} mở được màn hình nhưng không có báo cáo nào"
    co_bao_cao = {v for cfg in BP.PHONG.values() for v in cfg["xem"]} | set(BP.XEM_TAT_CA)
    thieu = co_bao_cao - cua
    assert not thieu, f"có báo cáo nhưng không mở được cửa màn hình: {thieu}"


# ══════════════════════ B2 – CẤU TRÚC ĐỦ ĐỂ DÙNG ══════════════════════
def _moi_bao_cao():
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        for pv in [BP.TOAN_CTY] + list(BP.PHONG):
            for kind in ("ngay", "tuan", "thang"):
                yield pv, kind, BP.bao_cao(db, kind, pv)


def test_moi_pham_vi_va_moi_ky_deu_tinh_duoc():
    n = 0
    for pv, kind, b in _moi_bao_cao():
        assert b["chi_tieu"], f"{pv}/{kind} không có chỉ tiêu nào"
        n += 1
    assert n == (len(BP.PHONG) + 1) * 3


def test_moi_chi_tieu_deu_mang_CACH_TINH_va_NGUON():
    """Một chỉ tiêu thiếu cách tính vẫn hiện bình thường, không lỗi, không đỏ – nó chỉ hỏng ở chỗ
    người dùng thôi không tin con số. Phải bắt bằng điều kiện về cấu trúc."""
    for pv, kind, b in _moi_bao_cao():
        for x in b["chi_tieu"]:
            assert x["ten"], f"{pv}/{kind}/{x['ma']} thiếu tên"
            assert x["cong_thuc"], f"{pv}/{kind}/{x['ma']} ({x['ten']}) thiếu CÁCH TÍNH"
            assert x["nguon"], f"{pv}/{kind}/{x['ma']} ({x['ten']}) thiếu NGUỒN dữ liệu"
            assert x["muc"] in ("", "vang", "do")


def test_chi_tieu_DO_phai_noi_can_lam_gi():
    """Một con số đỏ mà không nói làm gì thì chỉ tạo lo lắng, không tạo hành động."""
    for pv, kind, b in _moi_bao_cao():
        for x in b["chi_tieu"]:
            if x["muc"] == "do" and not x["ma"].startswith("phong_"):
                assert x["viec"], f"{pv}/{kind}/{x['ma']} ({x['ten']}) đỏ nhưng không nói cần làm gì"


def test_ma_chi_tieu_khong_trung_nhau_trong_mot_bao_cao():
    """Trùng mã thì màn hình vẽ hai dòng cùng khóa – React mất dấu dòng nào là dòng nào khi mở/đóng."""
    for pv, kind, b in _moi_bao_cao():
        ma = [x["ma"] for x in b["chi_tieu"]]
        assert len(ma) == len(set(ma)), f"{pv}/{kind} trùng mã: {ma}"


def test_bao_cao_toan_cong_ty_DOC_LAI_ket_qua_bao_cao_phong_khong_tinh_lai():
    """Chủ tịch thấy 'Điều hành: 2 việc phải xử lý' thì mở báo cáo Điều hành phải thấy đúng 2 việc.

    Tính lại theo cách khác là cách chắc chắn để hai bản lệch nhau, và lúc lệch thì không ai biết
    bản nào đúng – đó là lúc người ta thôi dùng cả hai.
    """
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        cty = BP.bao_cao(db, "thang", BP.TOAN_CTY)
        theo_ma = {x["ma"]: x for x in cty["chi_tieu"]}
        for phong in BP.PHONG:
            dong = theo_ma.get(f"phong_{phong}")
            assert dong is not None, f"báo cáo công ty thiếu dòng của phòng {phong}"
            rieng = BP.bao_cao(db, "thang", phong)
            assert dong["gia_tri"] == rieng["so_viec_do"], (
                f"phòng {phong}: công ty nói {dong['gia_tri']} việc đỏ, "
                f"báo cáo phòng nói {rieng['so_viec_do']}")


def test_bao_cao_phong_va_cong_ty_dung_CUNG_mot_khoang_thoi_gian():
    """Khác khoảng thì mọi con số lệch nhau đều đổ được cho 'khác kỳ', và không ai đối chiếu nữa."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        for kind in ("ngay", "tuan", "thang"):
            cty = BP.bao_cao(db, kind, BP.TOAN_CTY)
            for phong in BP.PHONG:
                r = BP.bao_cao(db, kind, phong)
                assert (r["tu"], r["den"], r["ky"]) == (cty["tu"], cty["den"], cty["ky"])


# ══════════════════════ B3 – RỖNG KHÔNG PHẢI 0 ══════════════════════
def test_gia_tri_RONG_khong_bi_to_canh_bao():
    """Một phòng chưa nhập liệu không phải một phòng đang có vấn đề. Tô nhầm màu vào ô rỗng là cách
    làm người ta thôi tin cả bảng."""
    for pv, kind, b in _moi_bao_cao():
        for x in b["chi_tieu"]:
            if x["gia_tri"] is None:
                assert x["muc"] == "", f"{pv}/{kind}/{x['ma']} rỗng nhưng đang tô mức '{x['muc']}'"


def test_ty_le_chot_bao_gia_RONG_khi_chua_gui_bao_gia_nao():
    """Mẫu số bằng 0 mà trả 0% là sai: 'chưa gửi báo giá nào' và 'gửi mà không ai chốt' ngược nhau."""
    from app.db.session import SessionLocal
    from app.models.ban_hang import BaoGia
    with SessionLocal() as db:
        co = db.execute(select(BaoGia)).scalars().first()
        b = BP.bao_cao(db, "ngay", "kd_le")
        ty = next(x for x in b["chi_tieu"] if x["ma"] == "ty_le_chot")
        if co is None:
            assert ty["gia_tri"] is None, "chưa có báo giá nào mà tỷ lệ chốt ra một con số"
        assert "RỖNG" in ty["cong_thuc"] or "rỗng" in ty["cong_thuc"]


def test_bang_luong_chua_lap_la_RONG_khong_phai_0():
    from app.db.session import SessionLocal
    from app.models.hr import PayrollRun
    from datetime import date
    ky = f"{date.today():%Y-%m}"
    with SessionLocal() as db:
        co = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()
        x = next(x for x in BP.bao_cao(db, "thang", "hcns")["chi_tieu"] if x["ma"] == "bang_luong")
        if co is None:
            assert x["gia_tri"] is None, "chưa lập bảng lương mà giá trị ra 0 – hai chuyện khác nhau"


def test_km_doi_xe_chi_cong_chuyen_DA_DO():
    """Cộng km của những chuyến đã đo rồi gọi là 'tổng km' là sai – người đọc hiểu đó là tổng mọi chuyến.
    Nên tên chỉ tiêu phải nói rõ bao nhiêu chuyến đã đo."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        x = next(x for x in BP.bao_cao(db, "thang", "doi_xe")["chi_tieu"] if x["ma"] == "km")
    assert "đã đo" in x["ten"], "tên chỉ tiêu km phải nói rõ số chuyến đã đo"


def test_mot_phong_hong_khong_lam_chet_bao_cao_toan_cong_ty():
    """Báo cáo Chủ tịch mà trắng trang vì một phòng lỗi là mất luôn cả những phòng còn ổn."""
    from app.db.session import SessionLocal
    cu = BP.HAM["visa"]
    BP.HAM["visa"] = lambda db, tu, den: (_ for _ in ()).throw(RuntimeError("giả vờ hỏng"))
    try:
        with SessionLocal() as db:
            b = BP.bao_cao(db, "thang", BP.TOAN_CTY)
        dong = next(x for x in b["chi_tieu"] if x["ma"] == "phong_visa")
        assert dong["gia_tri"] is None and "KHÔNG lấy được số" in dong["ten"]
        assert any(x["ma"] == "phong_ketoan" for x in b["chi_tieu"]), "các phòng khác biến mất"
    finally:
        BP.HAM["visa"] = cu


# ══════════ B4 – NGOẠI LỆ THEO NGƯỜI (chỉ đạo 09/9: "tất cả báo cáo về TP Điều hành") ══════════
def _cap_nang_luc(username: str, ma: str, ngay: int = 90):
    from datetime import date, timedelta
    from app.db.session import SessionLocal
    from app.models.core import User, UserGrant
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.username == username)).scalars().first()
        db.add(UserGrant(user_id=u.id, kind="capability", value=ma,
                         from_date=date.today(), to_date=date.today() + timedelta(days=ngay),
                         reason="thử", granted_by="test", approved_by="chutich", active=True))
        db.commit()
        return u.id


def _go_nang_luc(uid: int):
    from app.db.session import SessionLocal
    from app.models.core import UserGrant
    with SessionLocal() as db:
        for g in db.execute(select(UserGrant).where(UserGrant.user_id == uid)).scalars():
            db.delete(g)
        db.commit()


def test_nang_luc_theo_nguoi_mo_moi_bao_cao_ma_KHONG_doi_vai_tro():
    """Chỉ đạo 09/9: tất cả báo cáo về Trưởng phòng Điều hành.

    Cấp bằng NĂNG LỰC THEO NGƯỜI chứ không sửa vai trò tp_dh. Sửa vai trò là mở cho mọi Trưởng phòng
    Điều hành từ nay về sau, kể cả người kế nhiệm mà chưa ai quyết định gì – đúng kiểu quyền nới ra
    một lần rồi ở lại vĩnh viễn.
    """
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.services import bao_cao_phong as B
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.role == "tp_dh",
                                          User.active == True)).scalars().first()
        if u is None: pytest.skip("dữ liệu mẫu không có tp_dh")
        ten = u.username
        # trước khi cấp: chỉ phòng mình
        assert B.pham_vi_cho_nguoi(db, u) == ["dieu_hanh"]

    uid = _cap_nang_luc(ten, B.NANG_LUC_MOI_PHONG)
    try:
        with SessionLocal() as db:
            u = db.get(User, uid)
            ds = B.pham_vi_cho_nguoi(db, u)
            assert B.TOAN_CTY in ds and set(B.PHONG) <= set(ds)
        # VAI TRÒ không đổi – người kế nhiệm không tự có quyền này
        assert B.pham_vi_duoc_xem("tp_dh") == ["dieu_hanh"], \
            "quyền đã rò từ một người sang cả vai trò"

        h = login("tp_dh")
        for pv in ["toan_cty", "ketoan", "kd_le", "doi_xe"]:
            r = client.get(f"/api/v1/bao-cao?pham_vi={pv}&kind=ngay", headers=h)
            assert r.status_code == 200, f"{pv}: {r.status_code} {r.text[:120]}"
        assert client.get("/api/v1/bao-cao/pham-vi", headers=h).json()["mo_rong_theo_nguoi"] is True
    finally:
        _go_nang_luc(uid)


def test_go_nang_luc_thi_pham_vi_thu_HEP_LAI_ngay():
    """Ngoại lệ hết hạn hoặc bị gỡ mà quyền vẫn còn thì cấp quyền có thời hạn thành vô nghĩa."""
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.services import bao_cao_phong as B
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.role == "tp_dh",
                                          User.active == True)).scalars().first()
        if u is None: pytest.skip("dữ liệu mẫu không có tp_dh")
        assert B.pham_vi_cho_nguoi(db, u) == ["dieu_hanh"]
    h = login("tp_dh")
    assert client.get("/api/v1/bao-cao?pham_vi=toan_cty&kind=ngay", headers=h).status_code == 403


def test_nang_luc_moi_phong_da_khai_trong_bang_nang_luc():
    """Không khai thì màn hình cấp quyền không cấp được, và người cấp phải sửa mã – tức là không cấp."""
    from app.models.core import CAPABILITIES
    from app.services import bao_cao_phong as B
    assert B.NANG_LUC_MOI_PHONG in CAPABILITIES
