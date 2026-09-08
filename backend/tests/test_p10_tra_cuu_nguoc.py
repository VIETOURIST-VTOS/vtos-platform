"""P10 – tra cứu ngược: chọn một người, hiện họ làm được gì, và VÌ SAO.

Điều kiện nghiệm thu trong lệnh đợt 2 là một câu: chọn một nhân viên bất kỳ và trả lời được "vì sao
người này vào được màn hình đó" trong MỘT lần bấm. Tệp này canh đúng câu đó, và canh nó theo nghĩa
chặt: không phải "có trả về một chuỗi nào đó", mà là chuỗi ấy chỉ đúng vào dòng cho phép trong mã.

Phép thử quan trọng nhất ở đây là phép thử "không dòng nào bỏ trống lý do". Một bảng quyền không kèm
lý do vẫn trông như đã làm xong – người rà đọc thấy danh sách, gật đầu, và không phát hiện được rằng
mình không có cách nào biết quyền ấy từ đâu ra để mà bỏ đi.
"""
import os, sys

os.environ["DATABASE_URL"] = "sqlite:///./test_p10_tracuu.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p10_tracuu.db", "test_p10_tracuu.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, ROLES
from app.services import access as AC

client = TestClient(app)
MK = "tracuu123"
UID = {}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in ("cntt", "nv_kd", "xe_hdv", "hcns", "ketoan", "nv_visa"):
            un = f"tc_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            staff_code=f"TC{vai[:3]}", password_hash=hash_password(MK), active=True))
        db.commit()
        for vai in ("cntt", "nv_kd", "xe_hdv", "hcns", "ketoan", "nv_visa"):
            UID[vai] = db.execute(select(User).where(User.username == f"tc_{vai}")).scalars().first().id
        db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"tc_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def tra(vai_xem, uid):
    r = client.get(f"/api/v1/access/tra-cuu/{uid}", headers=login(vai_xem))
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- Điều kiện nghiệm thu ----------------
def test_moi_man_hinh_deu_tra_loi_duoc_cau_vi_sao():
    """Không dòng nào được bỏ trống lý do. Bảng quyền thiếu lý do vẫn trông như đã xong."""
    for vai in ("nv_kd", "xe_hdv", "hcns", "ketoan", "nv_visa", "cntt"):
        d = tra("cntt", UID[vai])
        for dong in d["man_hinh"]:
            assert dong.get("cau"), f"{vai}: màn hình {dong['path']} không có câu trả lời 'vì sao'"
            assert dong["nguon"] != "khong_ro", \
                f"{vai}: màn hình {dong['path']} không tìm ra dòng cho phép – ma trận đang lệch"


def test_ly_do_chi_dung_dong_trong_ma_tran_chu_khong_phai_cau_chung():
    """'Bạn có quyền' là câu vô dụng. Phải nói ra được dòng nào trong nguồn nào."""
    d = tra("cntt", UID["nv_kd"])
    theo = {x["path"]: x for x in d["man_hinh"]}
    assert "/bookings" in theo, "nhân viên kinh doanh phải thấy màn hình booking"
    x = theo["/bookings"]
    assert x["nguon"] == "ma_tran_menu"
    assert "MENU_ROLES['/bookings']" in x["dong"]
    assert "nv_kd" in x["dong"], "dòng dẫn chứng phải chứa chính vai trò đang tra"


def test_vai_tro_hep_noi_ro_la_danh_sach_khai_tay_chu_khong_phai_ma_tran():
    """Bảy vai trò hẹp KHÔNG lấy quyền từ MENU_ROLES. Nói nhầm nguồn thì người rà đi sửa nhầm chỗ và
    tưởng đã siết xong."""
    d = tra("cntt", UID["xe_hdv"])
    assert d["man_hinh"], "vai trò hẹp vẫn phải có màn hình"
    rieng = [x for x in d["man_hinh"] if x["path"] not in AC.MAN_HINH_KHONG_DUOC_AN]
    assert rieng, "vai trò hẹp phải có ít nhất một màn hình riêng của nghề"
    for dong in rieng:
        assert dong["nguon"] == "danh_sach_hep_khai_tay", \
            f"{dong['path']} khai nguồn {dong['nguon']}, trong khi xe_hdv nằm trong RESTRICTED_ROLE_MENUS"
        assert "RESTRICTED_ROLE_MENUS" in dong["dong"]


def test_vai_tro_hep_van_lam_duoc_hai_viec_cua_chinh_minh():
    """Hai việc mà một con người có tài khoản buộc phải tự làm được, dù vai trò hẹp tới đâu: đổi mật
    khẩu tạm do HCNS đặt, và xem phiếu lương của chính mình. Tài xế và HDV đều nằm trong bảng lương.

    Ba màn hình khác – trang chủ, cảnh báo, báo cáo công việc – KHÔNG nằm ở đây, và đó là chủ ý: bộ
    mẫu báo cáo ngày chỉ có bảy phòng văn phòng, đội xe và visa không phải nộp. Phép thử này từng
    khẳng định ngược lại và nó đã sai."""
    for vai in ("xe_hdv", "nv_visa"):
        d = tra("cntt", UID[vai])
        thay = {x["path"] for x in d["man_hinh"]}
        an = set(d["man_hinh_bi_an"])
        assert "/doi-mat-khau" in thay, f"{vai} không đổi được mật khẩu tạm"
        assert "/phieu-luong" in thay, f"{vai} không xem được phiếu lương của chính mình"
        assert "/reports" in an, f"{vai} thấy màn hình báo cáo ngày, trong khi phòng họ không phải nộp"


def test_nhom_api_tra_loi_bang_TEN_MAN_HINH_chu_khong_bang_ten_bien():
    """Người rà quyền không đọc mã. 'Vào được vì màn hình /bookings gọi tới nhóm này' là câu họ dùng
    được; 'MAN_HINH_API' một mình thì không."""
    d = tra("cntt", UID["nv_kd"])
    theo = {x["nhom"]: x for x in d["api"]}
    assert "/api/v1/bookings" in theo
    x = theo["/api/v1/bookings"]
    assert x["nguon"] in ("theo_man_hinh", "api_chung")
    assert x["cau"].startswith("Vào được vì màn hình ") or x["nguon"] == "api_chung"


def test_khong_nhom_api_nao_khong_ro_duong_vao():
    """Nhóm API vào được mà không truy ra đường nào dẫn tới là một quyền không ai nhìn thấy trên giao
    diện – đúng thứ P2 sinh ra để chống."""
    for vai in ROLES:
        for n in AC.pham_vi_day_du(vai):
            from app.services.tra_cuu_quyen import _nguon_api
            gia = User(id=0, username="x", full_name="x", role=vai, department="", staff_code="",
                       active=True, password_hash="")
            ly = _nguon_api(gia, n)
            assert ly["nguon"] != "khong_ro", f"{vai}: nhóm {n} không truy được đường vào"


# ---------------- Hai chiều của cùng một câu hỏi ----------------
def test_tra_theo_vai_tro_dem_dung_so_nguoi_dang_o_do():
    """Trước khi siết một vai trò phải biết siết trúng bao nhiêu người."""
    r = client.get("/api/v1/access/tra-cuu-vai-tro/nv_kd", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_nguoi"] == len(d["nguoi"]) >= 1
    assert all(p["full_name"] for p in d["nguoi"])


def test_vai_tro_khong_co_ai_van_tra_cuu_duoc_va_bi_bao():
    """Vai trò trống vẫn mở sẵn một bộ quyền. Trả 404 ở đây là giấu mất đúng thứ cần nhìn."""
    trong = [v for v in ROLES if not (v in ("nv_kd", "xe_hdv", "hcns", "ketoan", "nv_visa", "cntt"))]
    r = client.get(f"/api/v1/access/tra-cuu-vai-tro/{trong[0]}", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["so_nguoi"] == 0
    assert any("chưa có ai" in c for c in d["canh_bao"])
    assert d["man_hinh"], "vai trò trống vẫn phải hiện bộ quyền đang mở cho chỗ trống ấy"


# ---------------- Ai được tra ----------------
def test_tra_cuu_can_quyen_XEM_chu_khong_can_quyen_SUA():
    """HCNS và BKS phải tra được mà không cần quyền đổi vai trò. Buộc phải có quyền sửa mới tra được
    thì kỳ rà quyền hằng tháng chỉ hai người làm nổi – và rà bởi hai người là không rà."""
    r = client.get(f"/api/v1/access/tra-cuu/{UID['nv_kd']}", headers=login("hcns"))
    assert r.status_code == 200, r.text


def test_nguoi_khong_co_quyen_xem_thi_khong_tra_cuu_duoc_nguoi_khac():
    """Tra cứu ngược là bản đồ quyền của cả công ty. Mở cho mọi người là chỉ cho người muốn lách biết
    đúng cửa nào đang hở."""
    r = client.get(f"/api/v1/access/tra-cuu/{UID['ketoan']}", headers=login("nv_kd"))
    assert r.status_code == 403, f"nv_kd tra cứu được quyền người khác: {r.status_code}"


def test_tai_khoan_khong_co_thi_bao_404_chu_khong_tra_bang_rong():
    r = client.get("/api/v1/access/tra-cuu/999999", headers=login("cntt"))
    assert r.status_code == 404


# ---------------- Số đếm và cảnh báo ----------------
def test_so_dem_khop_voi_so_dong_that():
    d = tra("cntt", UID["ketoan"])
    assert d["dem"]["man_hinh"] == len(d["man_hinh"])
    assert d["dem"]["api"] == len(d["api"])
    assert d["dem"]["nang_luc"] == len(d["nang_luc"])


def test_pham_vi_phap_nhan_hien_ngay_trong_cung_mot_lan_bam():
    """P6 và P10 trả lời hai nửa của cùng một câu hỏi 'người này thấy được gì'. Tách ra hai màn hình
    là buộc người rà phải nhớ ghép lại, và họ sẽ không nhớ."""
    d = tra("cntt", UID["nv_kd"])
    assert "pham_vi_phap_nhan" in d
    assert "cau_hien_thi" in d["pham_vi_phap_nhan"]


def test_man_hinh_bi_an_va_man_hinh_thay_khong_giao_nhau():
    """Hai danh sách nói hai điều trái ngược về cùng một người là lỗi đã xảy ra một lần ở đợt 1."""
    for vai in ("nv_kd", "xe_hdv", "ketoan"):
        d = tra("cntt", UID[vai])
        thay = {x["path"] for x in d["man_hinh"]}
        an = set(d["man_hinh_bi_an"])
        assert not (thay & an), f"{vai}: {sorted(thay & an)} vừa thấy vừa bị ẩn"
