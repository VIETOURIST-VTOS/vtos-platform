"""Cửa nhập tay một dòng: có ở máy chủ từ đầu, đến 09/9/2026 không màn hình nào gọi.

Đây là dạng thiếu không hiện ra thành lỗi. Đường POST /api/v1/nap-du-lieu/nhap-mot-dong hoạt động
đúng, có phép thử riêng, và tài liệu gọi nó là "Cửa 1". Nhưng màn hình Nạp dữ liệu chỉ dựng ô tải
tệp. Hệ quả: 26 bộ nạp chỉ còn MỘT cửa. Muốn ghi một lần đăng kiểm, một phiếu bảo dưỡng, một hóa
đơn đầu vào, một kỳ bảo hiểm – nhân viên phải dựng một tệp Excel cho đúng một dòng. Thực tế thì họ
không dựng, và ô ấy nằm trống; đến cuối kỳ con số thiếu mà không ai biết thiếu ở đâu.

Chỗ đau nhất không phải sự bất tiện, mà là SÁU bộ nạp có vai trò chỉ được nhập tay chứ không được
tải tệp. Phân biệt ấy là có chủ đích: với dữ liệu chạm tiền, nhân viên nghiệp vụ gõ từng dòng thì
mỗi dòng có tên người và có bộ kiểm chạy ngay; đưa cả tệp thì một lần bấm là hàng trăm dòng. Nhưng
khi màn hình chỉ có cửa tệp, quy tắc ấy lặng lẽ đảo nghĩa: người được phép nhập tay hóa ra không
được nhập gì cả – vì cửa duy nhất tồn tại là cửa họ bị chặn.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_cua_nhap_tay.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cua_nhap_tay.db"): os.remove("test_cua_nhap_tay.db")
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User
from app.services import intake as IN

client = TestClient(app)
MK = "nhaptay123"
MAN_HINH = Path(__file__).resolve().parents[2] / "web" / "app" / "nap-du-lieu" / "page.tsx"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in ("nv_dh", "nv_mkt", "cntt"):
            un = f"nt_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"nt_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ma(src: str) -> str:
    """Bỏ chú thích, chỉ giữ mã chạy.

    Cần thiết vì hai đột biến đầu tiên đã lọt qua đúng vì lý do này: phép thử tìm chữ trong cả tệp,
    mà chính đoạn chú thích giải thích chỗ hỏng lại có nhắc tên đường "nhap-mot-dong". Nghĩa là phép
    thử đang canh "tệp có nhắc tới cửa này không" – câu ấy vẫn đúng sau khi cửa đã bị gỡ."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)      # gồm cả {/* ... */} trong JSX
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _chi_nhap_tay_duoc() -> dict:
    """Bộ nạp → những vai trò được NHẬP TAY nhưng không được TẢI TỆP. Đọc sống từ khai báo."""
    ra = {}
    for k in IN.BO_NAP:
        a = set(IN.VAI_TRO.get(k, IN.QUAN_TRI))
        b = set(IN.VAI_TRO_NAP_TEP.get(k, IN.QUAN_TRI))
        if a - b:
            ra[k] = sorted(a - b)
    return ra


def test_co_vai_tro_chi_duoc_nhap_tay_nen_thieu_cua_ay_la_khoa_cua_ho():
    """Nêu ra bằng số: bỏ cửa nhập tay không phải bớt tiện nghi, mà là khóa cửa của những vai trò này."""
    d = _chi_nhap_tay_duoc()
    assert d, ("Khai báo không còn bộ nạp nào phân biệt hai cửa. Nếu đó là quyết định thật thì sửa phép "
               "thử này kèm lý do – nhưng nó cũng làm mất căn cứ của phép thử dưới.")
    assert "chuyen_xe" in d and "nv_dh" in d["chuyen_xe"]


def test_man_hinh_nap_du_lieu_co_ca_hai_cua():
    """Màn hình phải gọi CẢ hai đường: nhap-mot-dong và kiem-tra-tep.

    Trước 09/9/2026 nó chỉ gọi đường thứ hai."""
    if not MAN_HINH.exists():
        return
    src = _ma(MAN_HINH.read_text(encoding="utf-8"))
    assert "nhap-mot-dong" in src, (
        "Màn hình Nạp dữ liệu không có cửa nhập tay. Những vai trò chỉ được nhập tay sẽ không nhập được "
        f"gì cả: {_chi_nhap_tay_duoc()}")
    assert "kiem-tra-tep" in src, "Mất cửa tải tệp"


def test_bieu_nhap_tay_sinh_tu_khai_bao_chu_khong_viet_tay_danh_sach_cot():
    """Biểu phải đọc c.key / c.bat_buoc / c.kieu từ khai báo bộ nạp.

    Viết tay danh sách ô nhập thì lần thêm cột sau vào một bộ nạp, biểu vẫn cũ – và không ai nhận ra,
    vì tệp mẫu và bộ kiểm đều đã có cột mới, chỉ mỗi biểu nhập tay là không. Người dùng sẽ thấy dòng
    mình gõ bị báo thiếu một cột mà màn hình không có chỗ nào để điền.
    """
    if not MAN_HINH.exists():
        return
    src = _ma(MAN_HINH.read_text(encoding="utf-8"))
    i = src.find("nhap-mot-dong")
    assert i > 0
    for dau in ("c.key", "c.bat_buoc", "c.kieu", "chon.cot"):
        assert src.count(dau) >= 2, (
            f"biểu nhập tay chỉ đọc {dau} một lần hoặc không lần nào. Ô nhập phải sinh từ khai báo bộ "
            "nạp: mỗi cột cần cả tên khóa, cờ bắt buộc và kiểu ô – viết tay danh sách thì lần thêm cột "
            "sau vào một bộ nạp, biểu vẫn cũ và không ai nhận ra.")


def test_nv_dh_nhap_tay_duoc_nhat_trinh_chuyen_xe_du_khong_tai_tep_duoc():
    """Vế thật của chuyện: cùng một người, cùng một loại dữ liệu, hai cửa hai kết quả – và đó là đúng.

    Cửa tệp đóng với nhân viên nghiệp vụ cho dữ liệu chạm tiền; cửa gõ tay mở. Phép thử giữ cả hai vế,
    vì chỉ giữ một vế thì lần sửa sau sẽ hoặc mở toang cửa tệp, hoặc đóng nốt cửa tay.
    """
    h = login("nv_dh")
    r = client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=h,
                    json={"loai": "chuyen_xe", "row": {}, "cua": "nhap_tay"})
    assert r.status_code != 403, f"nv_dh bị chặn ở cửa nhập tay của chính phòng mình: {r.text}"

    # Bước KIỂM TRA tệp mở cho ông – nó không ghi gì, và đọc tệp của chính mình thì không lộ gì.
    r2 = client.post("/api/v1/nap-du-lieu/kiem-tra-tep", headers=h,
                     files={"tep": ("x.csv", b"a,b\n1,2\n", "text/csv")}, data={"loai": "chuyen_xe"})
    assert r2.status_code == 200, r2.text
    # Bước NẠP THẬT thì đóng: một lần bấm là hàng trăm dòng vào sổ, mà mỗi dòng không ai gõ.
    r3 = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                     json={"loai": "chuyen_xe", "rows": [{}], "ten_tep": "x.csv"})
    assert r3.status_code == 403, (
        "Cửa nạp tệp đang mở cho nhân viên nghiệp vụ ở một bộ nạp chạm tiền: "
        f"{r3.status_code} {r3.text[:200]}")


def test_cua_nhap_tay_khong_lam_lung_bo_kiem():
    """Nhập tay đi qua ĐÚNG bộ kiểm của nhập tệp – dòng rỗng phải bị chặn, không được lọt thành bản ghi trống."""
    h = login("cntt")
    r = client.post("/api/v1/nap-du-lieu/nhap-mot-dong", headers=h,
                    json={"loai": "nha_cung_cap", "row": {}, "cua": "nhap_tay"})
    assert r.status_code in (201, 422)
    if r.status_code == 201:
        assert r.json()["da_ghi"] is False, "dòng rỗng đã được ghi thành nhà cung cấp không tên"
        assert r.json()["loi"], "chưa ghi mà cũng không nói lý do"
