"""P4 và P5 – quyền tách theo TỪNG CỬA nhập liệu, không phải theo màn hình.

Vì sao hai việc này nằm chung một tệp: cả hai đều sinh ra từ quyết định "nhập là dùng luôn, hậu kiểm
sau" của Chủ tịch ngày 08/9/2026. Bỏ khâu trưởng phòng duyệt từng dòng là bỏ một lớp chặn CÓ THẬT;
lớp còn lại — câu hỏi AI ĐƯỢC NHẬP — vì thế phải chặt hơn chứ không lỏng hơn.

P4: nhập tay sai một dòng thì sửa một dòng; tải tệp sai một lần là cả tệp vào bảng cùng lúc và dùng
    ngay. Hai việc khác hẳn nhau về hậu quả nên khác nhau về quyền.
P5: người vận hành mô hình đọc ảnh không được là người xác nhận kết quả của chính nó — nếu không thì
    không còn ai đứng ngoài để nói mô hình đọc sai.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_p4p5.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p4p5.db", "test_p4p5.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User
from app.services import intake as IN

client = TestClient(app)
MK = "cua123456"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in ("tp_dh", "nv_dh", "cntt", "ketoan", "hcns"):
            un = f"cua_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"cua_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------- P4 ----------------
def test_cua_tai_tep_khong_bao_gio_rong_hon_cua_nhap_tay():
    """Mọi bộ nạp: ai tải tệp được thì cũng nhập tay được, không có chiều ngược lại."""
    for loai in IN.BO_NAP:
        tay = set(IN.VAI_TRO.get(loai, IN.QUAN_TRI))
        tep = set(IN.VAI_TRO_NAP_TEP.get(loai, IN.QUAN_TRI))
        assert tep <= tay, f"{loai}: cửa tệp rộng hơn cửa tay"


def test_chi_siet_nhung_bo_nap_cham_thang_vao_tien():
    """Tiêu chí là DỮ LIỆU ĐI ĐÂU, không phải cấp bậc.

    Bản đầu của quy tắc siết mọi bộ nạp và lập tức chặn nhân viên kinh doanh nạp danh sách khách của
    chính mình – việc thường ngày. Chặn đi thì họ nhờ người khác nạp hộ, và nhật ký ghi sai tên người
    chịu trách nhiệm: đúng cái mà cả thiết kế ba cửa đang cố tránh."""
    assert IN.duoc_nap_tep("khach_hang", "nv_kd") is True      # danh mục, không chạm tiền
    assert IN.duoc_nap_tep("booking", "nv_kd") is True
    assert IN.duoc_nap_tep("quyet_toan_tour", "nv_dh") is False   # doanh thu – giá vốn
    assert IN.duoc_nap("quyet_toan_tour", "nv_dh") is True        # nhưng nhập tay vẫn được
    assert IN.duoc_nap_tep("quyet_toan_tour", "tp_dh") is True
    for loai in IN.BO_NAP_CHAM_TIEN:
        assert loai in IN.BO_NAP, f"khai siết cho bộ nạp không tồn tại: {loai}"


def test_api_chan_dung_cua_tai_tep():
    """Nhân viên điều hành gọi /nap thì bị chặn, nhưng /nhap-mot-dong thì không."""
    h = login("nv_dh")
    r = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "quyet_toan_tour", "rows": [{}], "ten_tep": "t.csv"})
    assert r.status_code == 403 and "tải tệp" in r.text, r.text
    r2 = client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=h,
                     json={"loai": "quyet_toan_tour", "row": {}, "cua": "nhap_tay"})
    assert r2.status_code != 403, r2.text      # sai dữ liệu thì 422, nhưng KHÔNG được là 403


def test_bang_bo_nap_noi_ro_ca_hai_cua():
    """Màn hình phải biết ai được tải tệp để không vẽ một cái nút bấm vào là 403."""
    ds = {b["ma"]: b for b in IN.danh_sach_bo_nap()}
    assert "vai_tro" in ds["chuyen_xe"] and "vai_tro_nap_tep" in ds["chuyen_xe"]


# ---------------- P5 ----------------
def test_cntt_khong_xac_nhan_duoc_so_may_doc():
    """CNTT vận hành mô hình nhưng không đứng tên con số nó đọc ra."""
    assert IN.duoc_nap("sao_ke_ngan_hang", "cntt") is True       # vẫn nhập tay/nạp được
    assert IN.duoc_xac_nhan_anh("sao_ke_ngan_hang", "cntt") is False
    assert IN.duoc_xac_nhan_anh("sao_ke_ngan_hang", "ketoan") is True

    r = client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=login("cntt"),
                    json={"loai": "sao_ke_ngan_hang", "row": {}, "cua": "doc_anh",
                          "tac_nhan": "doc_sao_ke_v1"})
    assert r.status_code == 403 and "CNTT" in r.text, r.text


def test_phong_khac_khong_xac_nhan_ho_so_cua_phong_kia():
    """Xác nhận phải là người của phòng SỞ HỮU con số."""
    assert IN.duoc_xac_nhan_anh("cham_cong", "ketoan") is False   # chấm công là của HCNS
    assert IN.duoc_xac_nhan_anh("cham_cong", "hcns") is True


def test_xac_nhan_anh_van_phai_ghi_ten_tac_vu_da_doc():
    """Không ghi tác vụ thì sau này không truy được con số do máy nào đọc."""
    r = client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=login("ketoan"),
                    json={"loai": "sao_ke_ngan_hang", "row": {}, "cua": "doc_anh", "tac_nhan": ""})
    assert r.status_code == 422 and "truy" in r.text
