"""Đợt E2b-1 — hai vai không được kiêm nhau, và màn hình cho sổ tách bạch trách nhiệm.

  A. Cặp vai được khai đúng theo quyết định 10/10/2026, và nó là HCNS ↔ thủ quỹ.
  B. Phép đo bắt được một người hai tài khoản, và KHÔNG báo oan hai người khác nhau.
  C. Phép đo MÙ ở đúng chỗ đã ghi — thiếu mã nhân viên thì không ghép, và cờ nói ra điều đó.
  D. Năm cửa của Đợt E2a cộng cửa mới đều thuộc một màn hình thật, không mở lát quyền nào mới.
  E. Màn hình `/ket-so` thật sự gọi từng cửa — có cửa mà không ai bấm thì vẫn là việc còn thiếu.
  F. Bảng hai vai KHÔNG có cửa ghi: việc phải sửa là thu hồi quyền, không phải sửa sổ kế toán.

PHÉP THỬ NÀY KHÔNG XOÁ TÀI KHOẢN NÀO. Nó dựng tài khoản có mã nhân viên riêng rồi chỉ soi đúng
những mã ấy trong kết quả. Dọn sạch bảng `users` để phép thử dễ viết là cách làm một phép thử xanh
trên một cơ sở dữ liệu không giống thật — và chính bài học 08/9/2026 về chuyện ấy.
"""
import io
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_le2b1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_le2b1.db", "test_le2b1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                           # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402

from app.main import app                                # noqa: E402
from app.db.session import SessionLocal                 # noqa: E402
from app.models.core import ROLES, User                 # noqa: E402
from app.services import access as AC                   # noqa: E402
from app.services import ks_tach_nhiem as KTN           # noqa: E402

client = TestClient(app)

GOC = os.path.dirname(os.path.dirname(__file__))
TSX = os.path.normpath(os.path.join(GOC, "..", "web", "app", "ket-so", "page.tsx"))


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    return SessionLocal()


def _them(db, username, role, staff_code=""):
    u = db.query(User).filter(User.username == username).first()
    if u is None:
        u = User(username=username, full_name=username.upper(), role=role,
                 staff_code=staff_code, password_hash="x", active=True)
        db.add(u)
    else:
        u.role, u.staff_code, u.active = role, staff_code, True
    db.commit()
    return u


def _dn(role: str) -> dict:
    """Đăng nhập bằng tài khoản demo của một vai.

    Cửa `/api/v1/auth/login` nhận FORM, không nhận JSON — gửi `json=` thì trả 422 và phép thử đỏ
    vì cách gọi chứ không vì mã. Dùng đúng cách các phép thử khác trong kho đã dùng.
    """
    r = client.post("/api/v1/auth/login",
                    data={"username": role, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, f"Không đăng nhập được vai {role}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ma(ra, ma_nguoi):
    return [x for x in ra if x["ma_nguoi"] == ma_nguoi]


# ─────────────────────────── A ───────────────────────────
def test_a1_cap_vai_duoc_khai_dung_quyet_dinh():
    cap = [c for c in KTN.CAP_VAI_KHONG_KIEM if c["ma"] == "hcns-vs-thu-quy"]
    assert cap, "Chưa khai cặp HCNS ↔ thủ quỹ (Chủ tịch chốt 10/10/2026)"
    c = cap[0]
    assert {c["vai_a"], c["vai_b"]} == {"hcns", "thu_quy"}
    assert "10/10/2026" in c["can_cu"], (
        "Cặp phải mang căn cứ có ngày — một quyết định không giải trình được thì không ai xem lại")


def test_a2_hai_vai_ay_co_that_trong_roles():
    """Khai một cặp vai không tồn tại là dựng một phép đo luôn trả 0 mà không ai biết vì sao."""
    for c in KTN.CAP_VAI_KHONG_KIEM:
        assert c["vai_a"] in ROLES, f"Vai `{c['vai_a']}` không có trong ROLES"
        assert c["vai_b"] in ROLES, f"Vai `{c['vai_b']}` không có trong ROLES"


# ─────────────────────────── B ───────────────────────────
def test_b1_bat_duoc_mot_nguoi_hai_tai_khoan():
    db = _db()
    _them(db, "le2b1_a_hcns", "hcns", staff_code="LE2B1-207")
    _them(db, "le2b1_a_quy", "thu_quy", staff_code="LE2B1-207")
    ra = _ma(KTN.hai_vai_trung_nguoi(db), "LE2B1-207")
    db.close()
    assert len(ra) == 1, f"Phải bắt được đúng một trường hợp cho mã này, nhận {ra}"
    assert ra[0]["tai_khoan"] == ["le2b1_a_hcns", "le2b1_a_quy"], (
        "Phải GỌI TÊN tài khoản, không chỉ đếm — một con số thì không ai biết đi tìm ai")
    assert ra[0]["vai_a"] != ra[0]["vai_b"]


def test_b2_khong_bao_oan_hai_nguoi_khac_nhau():
    db = _db()
    _them(db, "le2b1_b_hcns", "hcns", staff_code="LE2B1-301")
    _them(db, "le2b1_b_quy", "thu_quy", staff_code="LE2B1-302")
    ra = KTN.hai_vai_trung_nguoi(db)
    db.close()
    assert _ma(ra, "LE2B1-301") == [], "Hai mã nhân viên khác nhau là hai người"
    assert _ma(ra, "LE2B1-302") == []


def test_b3_mot_nguoi_mot_vai_khong_phai_vi_pham():
    db = _db()
    _them(db, "le2b1_c_quy", "thu_quy", staff_code="LE2B1-410")
    ra = KTN.hai_vai_trung_nguoi(db)
    db.close()
    assert _ma(ra, "LE2B1-410") == []


def test_b4_tai_khoan_da_tat_khong_tinh():
    """Tắt một trong hai tài khoản là cách HCNS sửa thật — phải được coi là đã sửa."""
    db = _db()
    _them(db, "le2b1_d_hcns", "hcns", staff_code="LE2B1-511")
    x = _them(db, "le2b1_d_quy", "thu_quy", staff_code="LE2B1-511")
    assert len(_ma(KTN.hai_vai_trung_nguoi(db), "LE2B1-511")) == 1
    x.active = False
    db.commit()
    ra = _ma(KTN.hai_vai_trung_nguoi(db), "LE2B1-511")
    db.close()
    assert ra == [], "Tắt một trong hai tài khoản là đã tách — không được báo tiếp"


# ─────────────────────────── C ───────────────────────────
def test_c1_mu_khi_thieu_ma_nhan_vien_va_khong_bao_oan():
    """Chỗ mù được ghi trong chú thích của hàm; phép thử này canh đúng chỗ ấy.

    Hai tài khoản KHÔNG có mã nhân viên, dù là của cùng một người thật, vẫn là hai `ma_nguoi`
    khác nhau (`u:<id>`), nên phép đo không ghép được. Đó KHÔNG phải lỗi sửa được bằng mã — nó
    chỉ bịt được bằng dữ liệu HCNS. Việc của phần mềm là không báo oan, và NÓI RA rằng mình mù.
    """
    db = _db()
    _them(db, "le2b1_e_hcns", "hcns", staff_code="")
    _them(db, "le2b1_e_quy", "thu_quy", staff_code="")
    ra = KTN.hai_vai_trung_nguoi(db)
    db.close()
    assert all(not x["ma_nguoi"].startswith("u:") for x in ra), (
        "Không có mã thì không ghép được — không được đoán rồi báo")


def test_c2_cua_noi_ra_rang_minh_mu():
    r = client.get("/api/v1/hach-toan/hai-vai-trung-nguoi",
                   headers=_dn("chutich"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert "mu_khi_thieu_ma_nv" in d, (
        "Con số 0 ở đây KHÔNG có nghĩa là sạch khi còn tài khoản chưa có mã nhân viên. "
        "Cửa phải nói ra điều đó, nếu không thì người đọc kết luận sai mà không có lỗi gì hiện ra.")
    assert "so_tai_khoan_thieu_ma_nv" in d
    if d["so_tai_khoan_thieu_ma_nv"] > 0:
        assert d["mu_khi_thieu_ma_nv"] is True


# ─────────────────────────── D ───────────────────────────
CUA_PHAI_CO = (
    "/api/v1/hach-toan/cap-tach-nhiem",
    "/api/v1/hach-toan/cap-tach-nhiem/nap-da-ky",
    "/api/v1/hach-toan/dau-chan",
    "/api/v1/hach-toan/thieu-ma-nhan-vien",
    "/api/v1/hach-toan/hai-vai-trung-nguoi",
)


def test_d1_cac_cua_nam_duoi_mot_man_hinh_that():
    """Mọi cửa của đợt này đi vào tiền tố `/api/v1/hach-toan` đã khai cho `/ket-so`.

    Không tự mở một lát quyền mới: `PHAM_VI_DA_CHOT` không đổi một số nào, vì không có nhóm API
    mới nào được thêm.
    """
    tien_to = AC.MAN_HINH_API.get("/ket-so") or ()
    assert "/api/v1/hach-toan" in tien_to
    for c in CUA_PHAI_CO:
        assert any(c.startswith(t) for t in tien_to), f"Cửa {c} không thuộc màn hình nào"


def test_d2_cua_moi_co_that_tren_router():
    """Đường trên router đã MANG SẴN tiền tố `/api/v1/hach-toan`, không phải đường tương đối.

    Bản đầu của phép thử này tìm `/hai-vai-trung-nguoi` và đỏ, trong khi cửa có thật — đỏ vì
    phép thử đoán sai hình dạng dữ liệu. Ghi lại vì đó là cái bẫy chung của mọi phép thử soi
    router: so bằng đường ĐẦY ĐỦ, và khi đỏ thì in ra cả tập để người đọc thấy ngay.
    """
    from app.api.v1 import hach_toan as HT
    duong = {r.path for r in HT.router.routes}
    assert "/api/v1/hach-toan/hai-vai-trung-nguoi" in duong, (
        f"Chưa có cửa mới. Đang có: {sorted(duong)}")


# ─────────────────────────── E ───────────────────────────
def test_e1_man_hinh_ket_so_goi_tung_cua():
    """Có cửa mà không ai bấm được thì vẫn là việc CÒN THIẾU — chính bài học của Đợt E2a.

    Đợt E2a dựng hai bảng, một bộ kiểm và năm cửa API rồi dừng, không màn hình nào; mức của hai
    cặp đã ký vì thế không ai đặt được dù Chủ tịch đã chọn mức. Phép thử này soi mã nguồn màn
    hình `/ket-so` tìm từng đường gọi. Soi theo chuỗi là thô, nhưng nó bắt đúng cái sai đã
    thật sự xảy ra một lần.
    """
    assert os.path.exists(TSX), f"Không thấy màn hình {TSX}"
    s = io.open(TSX, encoding="utf-8").read()
    for duong in ("/hach-toan/cap-tach-nhiem",
                  "/hach-toan/cap-tach-nhiem/nap-da-ky",
                  "/hach-toan/dau-chan/",
                  "/hach-toan/thieu-ma-nhan-vien",
                  "/hach-toan/hai-vai-trung-nguoi"):
        assert duong in s, f"Màn hình /ket-so chưa gọi `{duong}` — có số mà không có cửa bấm"


def test_e2_man_hinh_co_dung_thanh_phan():
    s = io.open(TSX, encoding="utf-8").read()
    assert "function TachNhiem()" in s
    assert "<TachNhiem />" in s, "Viết thành phần mà không đặt vào trang thì không ai thấy nó"


def test_e3_khong_an_nut_thay_hang_rao():
    """Giấu nút không phải một hàng rào — máy chủ mới là hàng rào.

    Ô chọn mức KHÔNG được khóa theo vai ở giao diện: ai bấm cũng gửi được, và máy chủ trả 403
    kèm lý do đọc được nếu đó là nới mà người bấm không có quyền ký. Cùng lựa chọn đã ghi cho
    cờ chiều phân tích của Đợt E1.
    """
    s = io.open(TSX, encoding="utf-8").read()
    i = s.find("function TachNhiem()")
    khoi = s[i:s.find("export default function Page()", i)]
    assert "kyDuoc" in khoi, "Phải NÓI cho người dùng biết ai ký được"
    assert "disabled={!kyDuoc}" not in khoi, (
        "Không khóa ô chọn theo vai: hàng rào ở máy chủ, giao diện chỉ nói ra")


# ─────────────────────────── F ───────────────────────────
def test_f1_bang_hai_vai_khong_co_cua_ghi():
    """Việc phải sửa là THU HỒI MỘT QUYỀN, không phải sửa một dòng trong sổ kế toán.

    Mở một cửa ghi ở đây là dựng con đường thứ hai để cấp hoặc gỡ quyền — con đường không đi
    qua màn hình phân quyền, không có người phê duyệt quyền, và không ai nghĩ tới khi rà soát.
    """
    from app.api.v1 import hach_toan as HT
    for r in HT.router.routes:
        if "hai-vai" in getattr(r, "path", ""):
            assert set(getattr(r, "methods", ()) or ()) <= {"GET", "HEAD"}, (
                f"Cửa {r.path} có phương thức ghi {r.methods} — bảng này chỉ được ĐỌC")


def test_f2_phep_do_khong_sua_du_lieu():
    db = _db()
    _them(db, "le2b1_f_hcns", "hcns", staff_code="LE2B1-700")
    _them(db, "le2b1_f_quy", "thu_quy", staff_code="LE2B1-700")
    truoc = {(x.username, x.role, x.active, x.staff_code) for x in db.query(User).all()}
    KTN.hai_vai_trung_nguoi(db)
    sau = {(x.username, x.role, x.active, x.staff_code) for x in db.query(User).all()}
    db.close()
    assert truoc == sau, "Phép đo không được đụng tới một dòng dữ liệu nào"

# ─────────────────────────── G ───────────────────────────
# CỬA MỞ, BIỂN ĐỀ ĐÓNG — nhóm phép thử sinh ra từ bản rà soát 10/10/2026.
#
# VTOS có HAI hàng rào, và chúng là hai danh sách độc lập:
#   · ngoài — ma trận menu (`MENU_ROLES`) suy ra tiền tố API cho từng vai (`pham_vi_day_du`);
#   · trong — `require_roles(...)` khai trên từng cửa.
# `pham_vi_day_du` đọc danh sách THỨ NHẤT và không đọc danh sách thứ hai. Nên đếm được 108
# màn hình cho một vai mà vai ấy vẫn nhận 403 ở mọi cửa — và đó đúng là việc đã xảy ra: bản
# đầu của Đợt E2b mở `/ket-so` cho ba vai mà không ai mở `XEM` trong `hach_toan.py`.
#
# `test_tc100` canh đúng MỘT màn hình (`/tai-xe`). Nhóm G này canh màn hình `/ket-so`, bằng
# ĐĂNG NHẬP THẬT: đếm menu không phải đo quyền đọc.
VAI_KHONG_DOC_DUOC_KET_SO = ("robot_ks",)
# `robot_ks` có `/ket-so` trong ma trận menu nhưng không có trong `XEM` — ĐO ĐƯỢC trên
# `origin/main` trước khi đợt này chạm vào, nên nó là chỗ CÒN LẠI của làn khác, không phải
# của đợt này. Khai ra để con số không im lặng: thêm một vai nữa vào đây thì phải có người
# giải thích, và phép thử dưới đây đỏ nếu ai mở menu mà quên mở cửa đọc.


def test_g1_moi_vai_thay_ket_so_deu_doc_duoc_ket_so():
    from app.api.v1.hach_toan import XEM
    vai = AC.MENU_ROLES.get("/ket-so", ())
    thieu = [v for v in vai if v not in XEM and v not in VAI_KHONG_DOC_DUOC_KET_SO]
    assert not thieu, (
        f"Các vai {thieu} thấy menu /ket-so nhưng không nằm trong danh sách vai đọc của "
        "`hach_toan.py` — cấp menu mà không cấp quyền đọc là cửa mở biển đề đóng. Chữa bằng "
        "cách gỡ màn hình khỏi vai, hoặc mở danh sách vai đọc — và cân nhắc hướng nào HẸP hơn.")


def test_g2_ba_vai_moi_khong_vai_nao_thay_menu_ma_khong_doc_duoc():
    """Nói riêng cho ba vai của đợt này, để thông điệp khi đỏ chỉ đúng chỗ phải sửa."""
    from app.api.v1.hach_toan import XEM
    for v in ("ketoan_truong", "ketoan_tt", "thu_quy"):
        thay = v in AC.MENU_ROLES.get("/ket-so", ())
        doc_duoc = v in XEM
        assert thay == doc_duoc, (
            f"Vai `{v}`: thấy menu /ket-so = {thay}, đọc được = {doc_duoc}. Hai con số này "
            "phải bằng nhau, nếu không thì người dùng bấm vào một màn hình rồi nhận 403.")


def test_g3_ke_toan_truong_doc_that_duoc_so_tach_nhiem():
    """Đăng nhập BẰNG VAI THẬT và gọi thật — không suy từ bảng.

    Đây là điều bản rà soát yêu cầu: "kiểm thử bằng từng vai thật, không chỉ đếm số menu".
    """
    db = _db()
    _them(db, "le2b1_ktt", "ketoan_truong", staff_code="LE2B1-KTT")
    from app.core.security import hash_password
    x = db.query(User).filter(User.username == "le2b1_ktt").first()
    x.password_hash = hash_password("Vtos@Demo#2026")
    db.commit()
    db.close()
    r = client.post("/api/v1/auth/login",
                    data={"username": "le2b1_ktt", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, f"Khong dang nhap duoc: {r.text}"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    for duong in ("/api/v1/hach-toan/cap-tach-nhiem",
                  "/api/v1/hach-toan/thieu-ma-nhan-vien",
                  "/api/v1/hach-toan/hai-vai-trung-nguoi"):
        rr = client.get(duong, headers=h)
        assert rr.status_code != 403, (
            f"Kế toán trưởng bị 403 ở `{duong}` — thấy menu mà không đọc được")
        assert rr.status_code == 200, f"{duong} tra {rr.status_code}: {rr.text}"


def test_g4_thu_quy_khong_doc_duoc_so_kiem_soat_ve_minh():
    """Và đó là chủ ý, không phải thiếu sót: người bị kiểm soát không mở sổ kiểm soát."""
    db = _db()
    _them(db, "le2b1_tq", "thu_quy", staff_code="LE2B1-TQ")
    from app.core.security import hash_password
    x = db.query(User).filter(User.username == "le2b1_tq").first()
    x.password_hash = hash_password("Vtos@Demo#2026")
    db.commit()
    db.close()
    r = client.post("/api/v1/auth/login",
                    data={"username": "le2b1_tq", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rr = client.get("/api/v1/hach-toan/cap-tach-nhiem", headers=h)
    assert rr.status_code == 403, (
        f"Thủ quỹ phải bị chặn ở sổ cấu hình hạch toán. Nhận {rr.status_code}")
    assert "thu_quy" not in AC.MENU_ROLES.get("/ket-so", ()), (
        "Bị chặn ở cửa thì cũng không được thấy menu — nếu không, người dùng bấm vào rồi nhận 403")


# ─────────────────────────── H ───────────────────────────
def test_h1_bo_dem_mu_phu_moi_vai_trong_cap():
    """Cờ "mù" phải đếm bằng danh sách vai RỘNG, không bằng `VAI_TIEN`.

    Lỗi bản đầu: cờ dùng `tai_khoan_thieu_ma_nv`, mà hàm ấy lọc theo `VAI_TIEN` — không có
    `hcns`. Thủ quỹ có mã, tài khoản HCNS cùng người chưa có mã → không ghép được VÀ cờ báo
    không mù. Màn hình hiện "Không trường hợp nào" trên một phép đo đang mù.
    """
    vai = KTN.vai_can_ma_de_phep_do_thay()
    for c in KTN.CAP_VAI_KHONG_KIEM:
        assert c["vai_a"] in vai, f"Vai `{c['vai_a']}` trong cặp mà không được đếm thiếu mã"
        assert c["vai_b"] in vai, f"Vai `{c['vai_b']}` trong cặp mà không được đếm thiếu mã"


def test_h2_hcns_thieu_ma_lam_co_mu_bat_len():
    db = _db()
    _them(db, "le2b1_g_hcns", "hcns", staff_code="")
    _them(db, "le2b1_g_quy", "thu_quy", staff_code="LE2B1-900")
    mu = KTN.thieu_ma_lam_mu_phep_do(db)
    cu = KTN.tai_khoan_thieu_ma_nv(db)
    db.close()
    assert any(x["username"] == "le2b1_g_hcns" for x in mu), (
        "Tài khoản HCNS thiếu mã phải được đếm là chỗ mù")
    assert not any(x["username"] == "le2b1_g_hcns" for x in cu), (
        "Và nó KHÔNG được vào danh sách vai bị chặn — mở danh sách chặn là chặn HCNS ở những "
        "bước họ không làm. Hai danh sách khác nhau, và cố ý khác nhau.")
