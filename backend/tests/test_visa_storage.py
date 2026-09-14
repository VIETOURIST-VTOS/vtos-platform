"""Kho lưu tài liệu hồ sơ Visa: chọn nền, đối chiếu băm khi đọc, và báo đúng khi kho không bền vững.

Vì sao phải có bộ test riêng: hộ chiếu và sao kê của khách mất là không lấy lại được. Chỗ nguy hiểm nhất
không phải lúc kho hỏng – lúc đó ai cũng thấy – mà là lúc hệ thống âm thầm ghi vào ổ tạm rồi báo "thành công".
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_visa_storage.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_visa_storage.db"): os.remove("test_visa_storage.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import storage as ST

client = TestClient(app); TOK = {}
DEP = str(date.today() + timedelta(days=90))


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield
    ST.reset_storage()


class FakeS3:
    """Kho đối tượng giả – cùng giao diện với S3Storage, để kiểm phần nghiệp vụ mà không cần mạng."""
    kind, durable = "s3", True

    def __init__(self):
        self.data: dict[str, bytes] = {}
        self.fail_put = False

    def put(self, key, data, content_type=""):
        if self.fail_put:
            raise ST.StorageError("Kho từ chối ghi (giả lập)")
        self.data[key] = data
        return ST.Stored(key=key, size=len(data), checksum=ST._sha(data))

    def get(self, key):
        if key not in self.data:
            raise ST.StorageError("Không có tệp này trên kho")
        return self.data[key]

    def exists(self, key):
        return key in self.data

    def describe(self):
        return {"kind": "s3", "durable": True, "noi_luu": "gia-lap/bucket", "canh_bao": ""}


def use(store):
    ST.reset_storage()
    ST._CACHE["s"] = store
    return store


def new_case_with_doc(name, store):
    h = login("tp.dieuhanh")
    c = client.post("/api/v1/visa/ho-so", headers=h,
                    json={"applicant_name": name, "market_code": "UK", "departure_date": DEP,
                          "applicant_dob": "1990-01-01", "is_test": True}).json()
    cid = c["case"]["id"]
    item = c["checklist"][0]["id"]
    r = client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu", headers=h,
                    files={"file": ("ho_chieu.pdf", b"noi dung that", "application/pdf")},
                    data={"checklist_item_id": str(item)})
    return cid, r


def test_chon_nen_theo_cau_hinh():
    """Đủ bucket + khóa thì tự dùng S3; ép s3 mà thiếu cấu hình thì báo lỗi ngay chứ không lặng lẽ ghi ổ tạm."""
    from app.core.config import settings
    goc = (settings.VISA_STORAGE, settings.S3_BUCKET, settings.S3_ACCESS_KEY_ID, settings.S3_SECRET_ACCESS_KEY)
    try:
        settings.VISA_STORAGE, settings.S3_BUCKET = "auto", ""
        settings.S3_ACCESS_KEY_ID = settings.S3_SECRET_ACCESS_KEY = ""
        ST.reset_storage()
        s = ST.build_storage()
        assert s.kind == "local" and s.durable is False          # máy lập trình: thư mục, và biết là không bền

        settings.VISA_STORAGE = "s3"
        with pytest.raises(ST.StorageError) as ex:
            ST.build_storage()
        assert "S3_BUCKET" in str(ex.value)                      # thiếu cấu hình là dừng, không âm thầm xuống local
    finally:
        (settings.VISA_STORAGE, settings.S3_BUCKET,
         settings.S3_ACCESS_KEY_ID, settings.S3_SECRET_ACCESS_KEY) = goc
        ST.reset_storage()


def test_khoa_luu_khong_lay_theo_ten_tep_khach_dat():
    """Khóa lưu sinh từ id hồ sơ + id tài liệu + băm, nên không đoán được tệp của hồ sơ khác."""
    k = ST.doc_key(12, 34, "a" * 64)
    assert k.startswith("visa/12/34-") and "ho_chieu" not in k and len(k.split("-")[-1]) == 16
    assert ST.doc_key(12, 34, "a" * 64) != ST.doc_key(12, 35, "a" * 64)


def test_nop_va_tai_lai_qua_kho_doi_tuong():
    """Vòng đầy đủ trên kho S3 giả: nộp lên kho, tải về đúng nội dung, tình trạng báo bền vững."""
    store = use(FakeS3())
    cid, r = new_case_with_doc("Kho S3 Binh Thuong", store)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert len(store.data) == 1 and list(store.data)[0].startswith(f"visa/{cid}/")
    tep = client.get(f"/api/v1/visa/tai-lieu/{doc['id']}/tep", headers=login("tp.dieuhanh"))
    assert tep.status_code == 200 and tep.content == b"noi dung that"
    tt = client.get("/api/v1/visa/luu-tru", headers=login("chutich")).json()
    assert tt["ben_vung"] is True and tt["thieu"] == 0 and tt["ok"] is True


def test_kho_tu_choi_ghi_thi_khong_ghi_nhan_tai_lieu():
    """Kho hỏng: KHÔNG được để lại bản ghi tài liệu trỏ vào chỗ trống."""
    store = use(FakeS3())
    store.fail_put = True
    cid, r = new_case_with_doc("Kho Tu Choi Ghi", store)
    assert r.status_code == 422 and "Chưa lưu được tệp" in r.json()["detail"]
    ct = client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("tp.dieuhanh")).json()
    assert ct["tai_lieu"] == []                                   # không có dòng tài liệu mồ côi
    assert ct["checklist"][0]["trang_thai"] == "MISSING"           # mục vẫn là chưa nộp, không phải "đã nộp"


def test_tep_bi_mat_thi_bao_410_va_tinh_trang_dem_dung():
    """Tệp biến mất khỏi kho (đúng cảnh ổ đĩa tạm bị xóa sau deploy): báo 410, và màn hình tình trạng đếm được."""
    store = use(FakeS3())
    cid, r = new_case_with_doc("Tep Bi Mat", store)
    doc = r.json()
    store.data.clear()                                            # deploy lại, ổ trống
    tep = client.get(f"/api/v1/visa/tai-lieu/{doc['id']}/tep", headers=login("tp.dieuhanh"))
    assert tep.status_code == 410
    tt = client.get("/api/v1/visa/luu-tru", headers=login("chutich")).json()
    assert tt["ok"] is False and tt["thieu"] >= 1 and doc["id"] in tt["tai_lieu_thieu"]
    assert "không còn trên kho" in tt["ket_luan"]


def test_noi_dung_lech_bam_thi_khong_tra_ve():
    """Tệp còn đó nhưng nội dung đã khác: KHÔNG trả về nội dung sai, dù người dùng có bấm lại bao nhiêu lần."""
    store = use(FakeS3())
    cid, r = new_case_with_doc("Lech Bam", store)
    doc = r.json()
    key = list(store.data)[0]
    store.data[key] = b"noi dung da bi thay"
    tep = client.get(f"/api/v1/visa/tai-lieu/{doc['id']}/tep", headers=login("tp.dieuhanh"))
    assert tep.status_code == 410 and "không khớp mã kiểm tra" in tep.json()["detail"]


def test_kho_khong_ben_vung_thi_phai_noi_ro():
    """Nền thư mục: vẫn chạy được cho máy lập trình, nhưng tình trạng phải nói thẳng là sẽ mất sau deploy."""
    import tempfile
    use(ST.LocalStorage(tempfile.mkdtemp()))
    cid, r = new_case_with_doc("Nen Thu Muc", None)
    assert r.status_code == 201
    tt = client.get("/api/v1/visa/luu-tru", headers=login("chutich")).json()
    assert tt["ben_vung"] is False
    assert "MẤT sau mỗi lần deploy" in tt["canh_bao"]
    assert "KHÔNG bền vững" in tt["ket_luan"]           # nói rõ chuyện sắp tới
    assert tt["ok"] is False                            # kho không bền vững thì không thể coi là "ổn"
    tep = client.get(f"/api/v1/visa/tai-lieu/{r.json()['id']}/tep", headers=login("tp.dieuhanh"))
    assert tep.status_code == 200                                  # vẫn đọc được khi tệp còn


def test_chi_lanh_dao_va_cntt_xem_duoc_tinh_trang_kho():
    """Tình trạng hạ tầng không phải việc của nhân viên nghiệp vụ."""
    assert client.get("/api/v1/visa/luu-tru", headers=login("dh.lan")).status_code == 403
    assert client.get("/api/v1/visa/luu-tru", headers=login("bks")).status_code == 200
