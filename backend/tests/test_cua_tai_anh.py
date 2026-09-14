"""Cửa tải tệp/ảnh cho bốn màn hình có nghiệp vụ nhưng chưa có chỗ đưa bằng chứng vào (09/9/2026).

Bản rà form ngày 09/9 đếm được 50 màn hình, chỉ 18 có cửa tải tệp/ảnh. Bốn chỗ dưới đây là những chỗ
thiếu cửa dẫn tới hậu quả thật, không phải bất tiện:

  khieu_nai  – hồ sơ bồi thường không có ảnh khách gửi thì không khép được, mà tiền vẫn phải chi
  phieu_thu  – đối soát thu tiền lệch thì cần ủy nhiệm chi / biên lai gốc mới xử được
  but_toan   – "nhập là dùng luôn" đã bỏ khâu duyệt từng dòng; chứng từ gốc là thứ còn lại để truy ngược
  ket_so     – hồ sơ chốt kỳ; TÁCH khỏi but_toan vì id của nó là mã kỳ, không phải số bút toán
  noi_dung   – phân hệ nội dung mà không tải được ảnh là thiếu đúng cửa chính của nó

  TA1  bốn đối tượng đã đăng ký, và mỗi đối tượng khai đủ bốn dữ kiện
  TA2  nhóm hồ sơ của chúng có thật, kèm thời hạn lưu – không nhét bừa vào nhóm sẵn có
  TA3  tải ảnh vào hồ sơ khiếu nại rồi đọc lại được đúng hồ sơ đó
  TA4  tệp của hồ sơ này KHÔNG lẫn sang hồ sơ khác
  TA5  đối tượng chưa đăng ký thì bị từ chối, không im lặng nhận rồi để lạc
"""
import os, sys, io
os.environ["DATABASE_URL"] = "sqlite:///./test_cuaanh.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_cuaanh.db", "test_cuaanh.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

MOI = ("khieu_nai", "phieu_thu", "but_toan", "ket_so", "noi_dung")
client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        yield


def test_ta1_bon_doi_tuong_da_dang_ky_du_bon_du_kien():
    from app.models.attachments import DOI_TUONG_DAY_DU
    for k in MOI:
        assert k in DOI_TUONG_DAY_DU, f"“{k}” chưa đăng ký thì màn hình gắn tệp vào sẽ bị máy chủ từ chối"
        ten, phong, nhom, theo = DOI_TUONG_DAY_DU[k]
        assert ten and phong and nhom, f"“{k}” khai thiếu dữ kiện: {DOI_TUONG_DAY_DU[k]}"
        assert isinstance(theo, bool)


def test_ta2_nhom_ho_so_co_that_va_co_thoi_han_luu():
    """Nhét tệp vào một nhóm hồ sơ sẵn có cho tiện là làm hỏng thời hạn lưu của cả nhóm đó."""
    from app.models.attachments import DOI_TUONG_DAY_DU, NHOM_HO_SO
    for k in MOI:
        nhom = DOI_TUONG_DAY_DU[k][2]
        assert nhom in NHOM_HO_SO, f"“{k}” khai nhóm hồ sơ “{nhom}” không tồn tại"
        ten, han = NHOM_HO_SO[nhom]
        assert ten and han, f"nhóm “{nhom}” chưa có thời hạn lưu"


def test_ta3_tai_anh_vao_ho_so_khieu_nai_roi_doc_lai_duoc():
    """Đường đi thật: tải lên qua đúng đường dẫn màn hình dùng, rồi đọc lại bằng đúng câu hỏi màn hình hỏi."""
    h = login("chutich")
    r = client.post("/api/v1/tep", headers=h,
                    files={"tep": ("bang_chung_khach.png", b"\x89PNG\r\n\x1a\n" + b"0" * 200, "image/png")},
                    data={"doi_tuong": "khieu_nai", "doi_tuong_id": "9001", "loai": "hinh_anh"})
    assert r.status_code in (200, 201), r.text
    ds = client.get("/api/v1/tep?doi_tuong=khieu_nai&doi_tuong_id=9001", headers=h).json()
    assert len(ds) == 1 and ds[0]["ten_tep"] == "bang_chung_khach.png"
    assert ds[0]["doi_tuong_ten"] == "Khiếu nại khách hàng", "màn hình phải đọc ra tên tiếng Việt, không phải mã"


def test_ta4_tep_cua_ho_so_nay_khong_lan_sang_ho_so_khac():
    """Lẫn hồ sơ là kiểu hỏng tệ nhất ở đây: ảnh của khách A xuất hiện trong hồ sơ bồi thường của khách B."""
    h = login("chutich")
    client.post("/api/v1/tep", headers=h,
                files={"tep": ("cua_ho_so_khac.png", b"\x89PNG\r\n\x1a\n" + b"1" * 200, "image/png")},
                data={"doi_tuong": "khieu_nai", "doi_tuong_id": "9002", "loai": "hinh_anh"})
    a = client.get("/api/v1/tep?doi_tuong=khieu_nai&doi_tuong_id=9001", headers=h).json()
    b = client.get("/api/v1/tep?doi_tuong=khieu_nai&doi_tuong_id=9002", headers=h).json()
    assert {x["ten_tep"] for x in a} == {"bang_chung_khach.png"}
    assert {x["ten_tep"] for x in b} == {"cua_ho_so_khac.png"}


def test_ta5_doi_tuong_chua_dang_ky_thi_bi_tu_choi():
    """Nhận rồi để lạc còn tệ hơn từ chối: người nạp tưởng đã có bằng chứng trong hồ sơ."""
    h = login("chutich")
    r = client.post("/api/v1/tep", headers=h,
                    files={"tep": ("x.png", b"\x89PNG\r\n\x1a\n" + b"2" * 100, "image/png")},
                    data={"doi_tuong": "khong_he_ton_tai", "doi_tuong_id": "1", "loai": "hinh_anh"})
    assert r.status_code >= 400, "đối tượng lạ phải bị từ chối"
    assert "khong_he_ton_tai" in r.text or "đối tượng" in r.text.lower()


def test_ta6_but_toan_va_ket_so_la_hai_khong_gian_id_rieng():
    """Hai đối tượng này cùng nhóm hồ sơ nhưng id KHÁC LOẠI: số bút toán vs mã kỳ "2026-09".

    Bản đầu em gộp chung một đối tượng cho gọn. Gộp thì hai không gian id nằm lẫn nhau, và đó đúng là
    cách hồ sơ chốt kỳ hiện ra bên trong một bút toán trùng số. Tách ra rồi thì chốt lại bằng phép thử.
    """
    from app.models.attachments import DOI_TUONG_DAY_DU
    assert "but_toan" in DOI_TUONG_DAY_DU and "ket_so" in DOI_TUONG_DAY_DU
    h = login("chutich")
    client.post("/api/v1/tep", headers=h,
                files={"tep": ("chung_tu_but_toan.pdf", b"%PDF-1.4\n" + b"a" * 200, "application/pdf")},
                data={"doi_tuong": "but_toan", "doi_tuong_id": "2026", "loai": "chung_tu"})
    client.post("/api/v1/tep", headers=h,
                files={"tep": ("bien_ban_chot_ky.pdf", b"%PDF-1.4\n" + b"b" * 200, "application/pdf")},
                data={"doi_tuong": "ket_so", "doi_tuong_id": "2026", "loai": "chung_tu"})
    bt = client.get("/api/v1/tep?doi_tuong=but_toan&doi_tuong_id=2026", headers=h).json()
    ks = client.get("/api/v1/tep?doi_tuong=ket_so&doi_tuong_id=2026", headers=h).json()
    assert {x["ten_tep"] for x in bt} == {"chung_tu_but_toan.pdf"}, \
        "cùng id 2026 nhưng khác đối tượng thì không được nhìn thấy nhau"
    assert {x["ten_tep"] for x in ks} == {"bien_ban_chot_ky.pdf"}
