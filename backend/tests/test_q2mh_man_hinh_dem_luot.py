"""HD-Q2mh — MÀN HÌNH cho cửa đếm lượt mở cửa đọc. Chủ tịch duyệt bố cục 16/10/2026.

Đợt HD-Q2a dựng bộ đếm và cửa API nhưng CỐ Ý chưa có màn hình: Chủ tịch dặn đổi giao diện thì phải
có bản xem thử duyệt trước. Đợt này là màn hình.

  A. Hai bảng khai quyền không được lệch nhau, và dòng mới không nới nhóm API cho ai.
  B. Menu và cửa mở CÙNG LÚC — mở một bên là «cửa mở, biển đề đóng» hoặc ngược lại.
  C. Màn hình không tự tính lại một con số nào.
  D. Ô trống đọc ra «chưa có số», không đọc ra 0.
  E. Robot nằm khối riêng, không trộn vào người.

BỐN CA C–E ĐỌC MÃ NGUỒN .tsx BẰNG CHUỖI, không bằng cây cú pháp — nói ra vì đó là giới hạn thật:
chúng bắt được việc ai đó GỠ BỎ một tính chất, không bắt được việc viết lại cùng ý bằng cú pháp
khác. Vẫn giữ, vì bộ phép thử của kho chạy bằng Python và không dựng được cây cú pháp TypeScript;
và vì ba tính chất ấy đều là thứ bị gỡ chứ không phải thứ bị viết lại.
"""
import os
import pathlib
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_q2mh.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_q2mh.db"):
    os.remove("test_q2mh.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1 import danh_gia as API  # noqa: E402
from app.main import app  # noqa: E402
from app.services import access as AC  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
MAN = "/dem-luot-doc"
GOC = pathlib.Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "dem-luot-doc" / "page.tsx"
SHELL = GOC / "web" / "components" / "Shell.tsx"
# Tên mang mã đợt — bài học HD-DG2: tên chung thì hai bộ chạy cùng lượt sập ở bước dựng.
AI = {"chutich": "chutich_q2mh", "tgd": "tgd_q2mh", "bks": "bks_q2mh", "cntt": "cntt_q2mh",
      # `robot_ks` nằm đây vì bất biến của kho: mọi màn hình mở cho BASE_VIEW, và robot Kiểm soát
      # ở trong đó. Ca b1 duyệt ĐÚNG danh sách vai đã khai chứ không duyệt một danh sách chép tay,
      # nên ngày ai thêm một vai mà quên dựng tài khoản thử thì ca ấy đỏ và nói ra — đã đỏ một lần
      # đúng như vậy khi `robot_ks` được thêm vào.
      "robot_ks": "robot_ks_q2mh",
      "nv_mkt": "nv_mkt_q2mh", "tp_hd": "tp_hd_q2mh"}


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import User
        with SessionLocal() as db:
            for vai, ten in AI.items():
                if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                    db.add(User(username=ten, full_name="Thử " + ten, role=vai,
                                department="Thử", password_hash=hash_password(MK)))
            db.commit()
        yield


def _h(vai):
    r = client.post("/api/v1/auth/login", data={"username": AI[vai], "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ═════════ A · hai bảng khai quyền không lệch ═════════

def test_a1_danh_sach_vai_cua_MAN_HINH_khop_dung_danh_sach_vai_cua_CUA():
    """Lệch một vai là hoặc màn hình trống, hoặc một lối vào API không ai thấy trên menu."""
    assert set(AC.MENU_ROLES[MAN]) == set(API.DEM_XEM), (
        set(AC.MENU_ROLES[MAN]) ^ set(API.DEM_XEM))


def test_a2_dong_moi_KHONG_noi_them_mot_nhom_API_nao_cho_ai():
    """Màn hình mới gắn vào nhóm API đã có. Bốn vai này đều đã chạm nhóm ấy qua /danh-gia, nên
    dòng này chỉ thêm một lối vào, không thêm một quyền."""
    assert AC.MAN_HINH_API[MAN] == ("/api/v1/danh-gia",)
    assert "/api/v1/danh-gia" in AC.MAN_HINH_API["/danh-gia"]
    for vai in AC.MENU_ROLES[MAN]:
        assert vai in AC.MENU_ROLES["/danh-gia"], (
            f"{vai} chạm được /api/v1/danh-gia CHỈ nhờ màn hình mới — đó là nới quyền, "
            f"không phải thêm lối vào")


# ═════════ B · menu và cửa mở cùng lúc ═════════

def test_b1_vai_thay_muc_menu_thi_goi_duoc_cua():
    for vai in AC.MENU_ROLES[MAN]:
        assert vai in AI, f"ca thử chưa dựng tài khoản cho vai {vai}"
        r = client.get("/api/v1/danh-gia/dem-luot", headers=_h(vai))
        assert r.status_code == 200, f"{vai}: {r.status_code} — {r.text[:140]}"


def test_b2_vai_khong_thay_muc_menu_thi_bi_chan_o_cua():
    for vai in ("nv_mkt", "tp_hd"):
        assert vai not in AC.MENU_ROLES[MAN]
        assert client.get("/api/v1/danh-gia/dem-luot", headers=_h(vai)).status_code == 403


def test_b3_co_muc_menu_tro_dung_duong_dan():
    s = SHELL.read_text(encoding="utf-8")
    assert f'"{MAN}"' in s, "khai quyền cho một màn hình không có lối vào trên menu"
    assert "Đếm lượt mở cửa đọc" in s


def test_b4_co_tep_trang():
    assert TRANG.exists(), f"thiếu {TRANG}"


# ═════════ C · màn hình không tự tính lại ═════════

def test_c1_man_hinh_dung_con_so_may_chu_tinh_chu_khong_chia_lai():
    """Tính lại ở màn hình là dựng công thức thứ hai, và ngày hai con số lệch nhau thì người dùng
    tin con số dễ đọc chứ không tin con số đúng."""
    s = TRANG.read_text(encoding="utf-8")
    assert "luot_moi_ngay" in s, "màn hình không dùng con số trung bình của máy chủ"
    for phep in ("so_luot / ", "so_luot/", "/ r.so_ngay", "/r.so_ngay", "so_dong / ", "so_dong/"):
        assert phep not in s, f"màn hình tự chia lại: {phep!r}"


# ═════════ D · chưa có số không phải là 0 ═════════

def test_d1_o_trong_doc_ra_chua_co_so_chu_khong_doc_ra_so_khong():
    s = TRANG.read_text(encoding="utf-8")
    assert '"—"' in s, "không có dấu gạch cho ô chưa có số"
    assert "chưa có số" in s.lower(), "màn hình không nói rõ ô trống nghĩa là chưa có số"
    assert "kq.luu_y" in s or "luu_y" in s, "không in lời lưu ý của máy chủ về ngày bắt đầu đếm"


# ═════════ E · robot để riêng ═════════

def test_e1_bang_nguoi_loai_robot_ra_va_robot_co_khoi_rieng():
    """Gộp lượt robot vào lượt người là biến một con robot thành một phòng ban chăm chỉ."""
    s = TRANG.read_text(encoding="utf-8")
    assert "!r.la_robot" in s, "bảng người không loại robot ra"
    assert "r.la_robot)" in s, "không có khối riêng cho robot"
