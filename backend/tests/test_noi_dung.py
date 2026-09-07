"""Nội dung & thương hiệu – Đợt 5. Đây là SỔ DUYỆT, không phải thư viện ảnh.

Vietourist là công ty đại chúng (mã VTD, sàn UPCoM). Một bài đăng hứa "cam kết hoàn tiền 100%" hay một
con số tài chính đưa ra ngoài mà chưa ai duyệt là rủi ro pháp lý và rủi ro công bố thông tin. Chốt chặn
chữ ký thứ hai là LÝ DO TỒN TẠI của màn hình này; bỏ nó thì đây chỉ còn một danh sách bài đăng.

  D1 thiếu bản thảo / kênh / ngày dự kiến → không lập được
  D2 người soạn không tự duyệt nội dung của mình
  D3 nội dung thường: một chữ ký là duyệt xong
  D4 có cam kết với khách → chữ ký thứ nhất chỉ đưa sang "chờ chữ ký thứ hai"
  D5 vai trò được ký thứ hai lấy từ THAM SỐ, không viết cứng
  D6 không có đường dẫn bài đã đăng thì không chuyển sang "đã đăng"
  D7 sửa bản đang chờ duyệt thì chữ ký cũ bị xoá
  D8 gỡ nội dung phải ghi lý do
"""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_nd.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nd.db"): os.remove("test_nd.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}
HOM_NAY = f"{date.today():%Y-%m-%d}"
BASE = {"title": "Ưu đãi hè 2026 – Nha Trang", "loai": "bai_dang", "kenh": ["facebook", "zalo"],
        "ngay_du_kien": HOM_NAY, "ban_thao": "https://drive.example/ban-thao-1"}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def lap(soan="cntt", **kw):
    r = client.post("/api/v1/noi-dung", json=dict(BASE, **kw), headers=login(soan))
    assert r.status_code == 201, r.text
    n = r.json()["content"]
    client.post(f"/api/v1/noi-dung/{n['id']}/chuyen-trang-thai", json={"status": "cho_duyet"}, headers=login(soan))
    return n


def test_d1_thieu_ban_thao_kenh_hoac_ngay_thi_khong_lap_duoc():
    h = login("cntt")
    assert client.post("/api/v1/noi-dung", json=dict(BASE, ban_thao=""), headers=h).status_code == 422
    assert client.post("/api/v1/noi-dung", json=dict(BASE, kenh=[]), headers=h).status_code == 422
    assert client.post("/api/v1/noi-dung", json=dict(BASE, kenh=["bao_tuong"]), headers=h).status_code == 422
    assert client.post("/api/v1/noi-dung", json=dict(BASE, loai="tho"), headers=h).status_code == 422


def test_d2_nguoi_soan_khong_tu_duyet():
    # Phó TGĐ Marketing vừa soạn được vừa duyệt được – vẫn không tự ký bản của chính mình
    n = lap(soan="ptgd.mkt")
    r = client.post(f"/api/v1/noi-dung/{n['id']}/duyet", headers=login("ptgd.mkt"))
    assert r.status_code == 403 and "tự duyệt" in r.json()["detail"]
    # bản do cntt soạn thì cntt cũng không ký được – vai trò này không nằm trong nhóm duyệt nội dung
    CTX["thuong"] = lap()["id"]
    assert client.post(f"/api/v1/noi-dung/{CTX['thuong']}/duyet", headers=login("cntt")).status_code == 403


def test_d3_noi_dung_thuong_mot_chu_ky_la_duyet_xong():
    r = client.post(f"/api/v1/noi-dung/{CTX['thuong']}/duyet", headers=login("ptgd.mkt"))
    assert r.status_code == 200
    n = r.json()["content"]
    assert n["status"] == "da_duyet" and n["can_ky_2"] is False and n["approved_at"]


def test_d4_co_cam_ket_thi_chu_ky_thu_nhat_chi_dua_sang_cho_ky_2():
    n = lap(title="Cam kết hoàn tiền 100% nếu huỷ tour", co_cam_ket=True)
    assert n["can_ky_2"] is True
    CTX["camket"] = n["id"]
    r = client.post(f"/api/v1/noi-dung/{n['id']}/duyet", headers=login("ptgd.mkt"))
    assert r.status_code == 200 and r.json()["content"]["status"] == "cho_ky_2"
    assert "chữ ký" in r.json()["message"]


def test_d5_vai_tro_ky_thu_hai_lay_tu_tham_so():
    """Thu hẹp tham số còn mỗi Chủ tịch rồi thử ký bằng TGĐ: phải bị chặn.

    Phép thử này chứng minh danh sách vai trò ký thứ hai ĐỌC TỪ tham số chính sách chứ không nằm trong mã –
    Ban TGĐ đổi được người ký mà không phải sửa phần mềm và triển khai lại.
    """
    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    db = SessionLocal()
    db.add(Param(key="nd_vai_tro_ky_2", value="chutich", label="Vai trò ký thứ hai", unit="danh sách vai trò",
                 source="thử", status="active", effective_from=date.today()))
    db.commit(); R.clear_param_cache(); db.close()
    cid = CTX["camket"]
    r = client.post(f"/api/v1/noi-dung/{cid}/duyet", headers=login("tgd"))
    assert r.status_code == 403 and "Pháp chế" in r.json()["detail"]
    r = client.post(f"/api/v1/noi-dung/{cid}/duyet", headers=login("chutich"))
    assert r.status_code == 200 and r.json()["content"]["status"] == "da_duyet"
    assert r.json()["content"]["nguoi_duyet"] == "ptgd.mkt,chutich"


def test_d6_khong_co_duong_dan_bai_dang_thi_khong_chuyen_sang_da_dang():
    cid = CTX["camket"]; h = login("cntt")
    r = client.post(f"/api/v1/noi-dung/{cid}/chuyen-trang-thai", json={"status": "da_dang"}, headers=h)
    assert r.status_code == 422 and "đường dẫn" in r.json()["detail"]
    r = client.post(f"/api/v1/noi-dung/{cid}/chuyen-trang-thai",
                    json={"status": "da_dang", "link_dang": "https://facebook.com/vietourist/posts/123"}, headers=h)
    assert r.status_code == 200 and r.json()["content"]["status"] == "da_dang"
    # không nhảy cóc: đã đăng rồi thì không quay về nháp
    assert client.post(f"/api/v1/noi-dung/{cid}/chuyen-trang-thai", json={"status": "nhap"}, headers=h).status_code == 422


def test_d7_sua_ban_dang_cho_duyet_thi_chu_ky_cu_bi_xoa():
    n = lap(title="Bảng giá tour hè", co_so_lieu_tc=True)
    client.post(f"/api/v1/noi-dung/{n['id']}/duyet", headers=login("ptgd.mkt"))
    assert client.get(f"/api/v1/noi-dung/{n['id']}", headers=login("cntt")).json()["nguoi_duyet"] == "ptgd.mkt"
    # bản này có số liệu tài chính nên đang chờ chữ ký thứ hai; sửa bản thảo lúc này thì chữ ký thứ nhất
    # không còn nói về bản sắp đăng nữa – phải xoá và quay lại từ đầu
    assert client.get(f"/api/v1/noi-dung/{n['id']}", headers=login("cntt")).json()["status"] == "cho_ky_2"
    r = client.put(f"/api/v1/noi-dung/{n['id']}", json={"ban_thao": "https://drive.example/ban-thao-2"}, headers=login("cntt"))
    assert r.status_code == 200
    assert r.json()["content"]["nguoi_duyet"] == "" and r.json()["content"]["status"] == "cho_duyet"
    # và phải có đường rút hẳn bản thảo về Nháp khi người ký thứ hai không đồng ý
    n2 = lap(title="Thông cáo kết quả kinh doanh quý", co_so_lieu_tc=True)
    client.post(f"/api/v1/noi-dung/{n2['id']}/duyet", headers=login("ptgd.mkt"))
    r = client.post(f"/api/v1/noi-dung/{n2['id']}/chuyen-trang-thai", json={"status": "nhap"}, headers=login("cntt"))
    assert r.status_code == 200 and r.json()["content"]["status"] == "nhap"
    assert r.json()["content"]["nguoi_duyet"] == ""


def test_d8_go_noi_dung_phai_ghi_ly_do():
    cid = CTX["camket"]; h = login("cntt")
    assert client.post(f"/api/v1/noi-dung/{cid}/chuyen-trang-thai", json={"status": "go"}, headers=h).status_code == 422
    r = client.post(f"/api/v1/noi-dung/{cid}/chuyen-trang-thai",
                    json={"status": "go", "ly_do_go": "Chương trình khuyến mãi kết thúc sớm"}, headers=h)
    assert r.status_code == 200 and r.json()["content"]["ly_do_go"]
