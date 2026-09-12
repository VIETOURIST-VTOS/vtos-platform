"""Hàng rào ngoài (check_restricted_scope) và hai chỗ nó chặn nhầm người nó sinh ra để bảo vệ.

Hàng rào suy phạm vi API của một vai trò từ ma trận menu: vai trò chỉ chạm được nhóm API nằm sau màn
hình của mình, còn lại chặn mặc định. Đúng cho phần lớn endpoint, nhưng nó mù ở hai chỗ:

  1. Endpoint TỰ LỌC theo người đăng nhập (phiếu lương, khoản lương treo, hồ sơ của chính mình) không
     nằm sau màn hình của vai trò nào – nó phục vụ chính người gọi. Hàng rào chặn nó là khóa người lao
     động khỏi tiền của họ.
  2. Endpoint có khoanh vùng BÊN TRONG theo phân công (hồ sơ visa của sales phụ trách): máy chủ khai
     nv_kd ở visa.READ và có ô phân công người bán, nhưng dòng /visa trong ma trận menu lại bỏ khối
     Kinh doanh. Hai cửa nói ngược nhau thì cửa nào cũng mất nghĩa.

Nới hàng rào là việc phải soi kỹ nhất trong cả hệ thống, nên mỗi lần nới ở đây đều đi kèm một phép thử
chứng minh nó KHÔNG nới quá – đó là các phép thử "chiều ngược" bên dưới.

  HR1 nhân viên kinh doanh xem được khoản lương treo của CHÍNH MÌNH
  HR2 nhưng vẫn KHÔNG chạm được endpoint bảng lương khác – hàng rào không bị nới cả cụm
  HR3 danh sách đường tự lọc đọc từ dấu hiệu trong mã, không khai tay, và hiện đúng ba đường
  HR4 so khớp đường chỉ khớp đúng số đoạn – không nới sang đường khác
  HR5 sales phụ trách mở được hồ sơ visa của mình, KHÔNG mở được hồ sơ người khác
  HR6 và vẫn KHÔNG xem được cơ cấu giá vốn của hồ sơ mình phụ trách
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_hrpv.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hrpv.db"): os.remove("test_hrpv.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}
DEP = str(date.today() + timedelta(days=60))


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _uid(username):
    return next(x["id"] for x in client.get("/api/v1/users", headers=login("chutich")).json()
                if x["username"] == username)


# ---------------- Endpoint tự lọc theo người đăng nhập ----------------

def test_hr1_nhan_vien_xem_duoc_khoan_luong_treo_cua_chinh_minh():
    """Khoản treo không hiện trên phiếu lương nào – đây là chỗ dễ mất tiền nhất mà không ai phát hiện."""
    r = client.get("/api/v1/payroll/khoan-treo", headers=login("kd.hoa"))
    assert r.status_code == 200, r.text
    kq = r.json()
    assert kq.get("chi_cua_toi") is True
    assert len({x["ma"] for x in kq["rows"]}) <= 1, "chỉ được thấy đúng mã nhân viên của chính mình"


def test_hr2_van_khong_cham_duoc_endpoint_bang_luong_khac():
    """Chiều ngược: nới cho một đường tự lọc KHÔNG được nới cả nhóm quanh nó.

    Gọi thẳng hàng rào chứ không qua HTTP. Qua HTTP thì mấy đường này còn một lớp chặn nữa ở thân hàm,
    nên vẫn 403 kể cả khi hàng rào đã thủng – phép thử sẽ xanh trong khi hàng rào hỏng. Đây đúng là lỗi
    phép thử mà bản nháp đầu của tệp này mắc phải.
    """
    from fastapi import HTTPException
    from app.services import access as AC
    from app.models.core import User
    nv = User(username="kiem_hang_rao", role="nv_kd", active=True)
    for duong in ("/api/v1/payroll-runs/2026-09",
                  "/api/v1/payroll-runs/2026-09/theo-phap-nhan",
                  "/api/v1/payroll/xung-dot-ho-so"):
        try:
            AC.check_restricted_scope(nv, duong)
        except HTTPException as ex:
            assert ex.status_code == 403
        else:
            raise AssertionError(f"hàng rào để lọt {duong} cho nhân viên kinh doanh")
    # còn đúng ba đường tự lọc thì phải đi lọt
    for duong in ("/api/v1/auth/me", "/api/v1/payroll/khoan-treo",
                  "/api/v1/payroll-runs/2026-09/phieu-luong"):
        AC.check_restricted_scope(nv, duong)


def test_hr3_duong_tu_loc_doc_tu_dau_hieu_trong_ma_khong_khai_tay():
    """Khai tay thì thêm endpoint mới là quên, mà quên ở đây nghĩa là khóa người dùng khỏi tiền của họ.

    DANH SÁCH NÀY KHOÁ CỨNG, VÀ ĐÓ LÀ CÓ Ý. Hàm `duong_tu_loc()` tự đọc dấu `loc_theo_nguoi_dung`
    trong mã nên nó không bao giờ quên; nhưng chính vì thế, gắn thêm một dấu ấy là NỚI hàng rào vai
    trò cho một đường mới mà không ai phải xin phép. Khoá cứng danh sách bắt người gắn dấu phải sửa
    phép thử này – và lúc sửa thì phải viết ra vì sao đường ấy được phép tự lọc.

    SÁU ĐƯỜNG, KHÔNG PHẢI BA. Bản đầu của phép thử này (làn Kiểm soát viết) khoá đúng ba đường – đúng
    tại thời điểm viết. Khi gộp vào `main` ngày 11/9/2026 thì đo được SÁU: làn Viết phần mềm đã thêm
    màn hình phiếu lương với ba đường `/api/v1/phieu-luong/*`, mỗi đường đều gắn `loc_theo_nguoi_dung`
    kèm câu giải thích của chính người gắn:

        · /api/v1/phieu-luong/khoan-treo   – "khoản lương treo – ai không xem được bảng lương thì
                                              chỉ thấy phần của chính mình"
        · /api/v1/phieu-luong/ky-cua-toi   – "danh sách kỳ lương của chính người đăng nhập"
        · /api/v1/phieu-luong/{period}     – "phiếu lương – phiếu của chính mình ai cũng xem được,
                                              phiếu người khác thì phải xem được bảng lương"

    Cả ba đều đúng kiểu tự lọc mà hàm này sinh ra để nhận. Robot A cập nhật con số ba → sáu khi gộp,
    KHÔNG nới phép thử thành "kiểm tính chất" – nới là bỏ đúng cái giá trị của nó. Làn Kiểm soát xem
    lại ba đường mới; nếu có đường nào không đáng tự lọc thì sửa ở endpoint, không sửa ở đây.
    """
    from app.services import access as AC
    ds = AC.duong_tu_loc()
    assert ds == {"/api/v1/auth/me",
                  "/api/v1/payroll/khoan-treo",
                  "/api/v1/payroll-runs/{period}/phieu-luong",
                  "/api/v1/phieu-luong/khoan-treo",
                  "/api/v1/phieu-luong/ky-cua-toi",
                  "/api/v1/phieu-luong/{period}"}, sorted(ds)
    # và mỗi đường đó phải THẬT SỰ tự lọc: gọi bằng tài khoản không có quyền bảng lương vẫn phải đi lọt
    assert client.get("/api/v1/auth/me", headers=login("kd.hoa")).status_code == 200


def test_hr4_so_khop_duong_khong_noi_sang_duong_khac():
    from app.services.access import _khop_duong
    assert _khop_duong("/api/v1/payroll-runs/2026-09/phieu-luong", "/api/v1/payroll-runs/{period}/phieu-luong")
    assert not _khop_duong("/api/v1/payroll-runs/2026-09/rows", "/api/v1/payroll-runs/{period}/phieu-luong")
    assert not _khop_duong("/api/v1/payroll/khoan-treo/tat-ca", "/api/v1/payroll/khoan-treo")
    assert not _khop_duong("/api/v1/payroll", "/api/v1/payroll/khoan-treo")


# ---------------- Hồ sơ visa của sales phụ trách ----------------

def test_hr5_sales_phu_trach_mo_duoc_ho_so_cua_minh_khong_mo_duoc_ho_so_nguoi_khac():
    """Ô phân công người bán chỉ có nghĩa khi người được phân công mở được hồ sơ đó."""
    r = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                    json={"applicant_name": "Khách của chị Hoa", "market_code": "UK",
                          "departure_date": DEP, "on_duplicate": "independent", "note": "kiểm hàng rào"})
    assert r.status_code == 201, r.text
    cid = r.json()["case"]["id"]; CTX["cid"] = cid
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                json={"sales_user_id": _uid("kd.hoa")})

    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("kd.hoa")).status_code == 200, \
        "sales được phân công mà không mở được hồ sơ thì ô phân công là ô chết"
    # chiều ngược – mở /visa cho khối Kinh doanh KHÔNG có nghĩa là mở mọi hồ sơ visa
    r2 = client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("kd.tuan"))
    assert r2.status_code in (403, 404), \
        f"sales KHÔNG được phân công vẫn mở được hồ sơ khách của người khác ({r2.status_code})"


def test_hr6_sales_van_khong_xem_duoc_co_cau_gia_von():
    """Thấy hồ sơ khách của mình là một chuyện; thấy giá vốn là chuyện khác."""
    assert client.get(f"/api/v1/visa/ho-so/{CTX['cid']}/thu-chi",
                      headers=login("kd.hoa")).status_code == 403
