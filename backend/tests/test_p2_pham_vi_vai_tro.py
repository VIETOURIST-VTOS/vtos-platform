"""P2 – danh sách cho phép cho MỌI vai trò, suy từ ma trận menu.

Trước bản này chỉ 4 trong 20 vai trò có hàng rào ngoài; 16 vai trò còn lại không có hàng rào nào.
Nghĩa là thêm một endpoint mà quên khai quyền thì endpoint đó mở cho mọi người đăng nhập – và không
ai biết, vì không có gì báo. Chặn mặc định đảo chiều việc đó: nhóm API mới không gắn màn hình nào thì
KHÔNG ai vào được, và phép thử nói ra ngay chứ không để người dùng phát hiện bằng một lỗi 403 trên
hệ thống thật.

Bản đồ màn hình → API không khai bằng trí nhớ mà đo từ mã giao diện. Phép thử thứ hai canh để nó
không lệch khỏi giao diện sau mỗi lần sửa màn hình.
"""
import os, sys, re, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test_p2_pham_vi.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p2_pham_vi.db", "test_p2_pham_vi.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi import HTTPException
from app.main import app
from app.services import access as AC
from app.models.core import ROLES, User

WEB = pathlib.Path(__file__).resolve().parents[2] / "web"


def _nhom(path: str) -> str:
    return "/api/v1/" + path[len("/api/v1/"):].split("/")[0]


def test_khong_nhom_api_nao_mo_coi():
    """Nhóm API không vai trò nào chạm được là một phân hệ vừa bị khóa mà chưa ai biết."""
    nhom = {_nhom(r.path) for r in app.routes if getattr(r, "path", "").startswith("/api/v1/")}
    phu = set()
    for vai in ROLES:
        phu |= set(AC.pham_vi_day_du(vai))
    mo_coi = sorted(n for n in nhom if not any(n.startswith(x) or x.startswith(n) for x in phu))
    assert not mo_coi, ("Nhóm API không màn hình nào gọi tới, nên không vai trò nào vào được. Gắn vào "
                        f"MAN_HINH_API của đúng màn hình: {mo_coi}")


def test_ban_do_man_hinh_api_khong_lech_voi_giao_dien():
    """Bản đồ đo từ mã giao diện. Sửa màn hình để gọi thêm một nhóm API mà quên khai ở đây thì màn
    hình đó gãy trên hệ thống thật – phép thử này bắt trước khi đẩy."""
    if not WEB.exists():
        return
    thieu = []
    for p in sorted((WEB / "app").glob("*/page.tsx")):
        man = "/" + p.parent.name
        khai = set(AC.MAN_HINH_API.get(man, ()))
        if not khai:
            continue          # màn hình chưa gắn bản đồ thì phép thử mồ côi ở trên lo
        src = p.read_text(encoding="utf-8")
        goi = {"/api/v1/" + m.group(1) for m in
               re.finditer(r'(?:api(?:<[^>]*>)?|fetch)\(\s*[`"\'](?:/api/v1)?/([a-z0-9\-]+)', src)}
        goi.discard("/api/v1/api")           # lib/api.ts, không phải nhóm thật
        for g in sorted(goi - khai - set(AC.API_CHUNG)):
            thieu.append(f"{man} gọi {g} nhưng MAN_HINH_API không khai")
    assert not thieu, thieu


def test_khong_vai_tro_nao_bi_khoa_hoan_toan():
    """Vai trò không chạm được gì là vai trò đăng nhập vào và nhìn thấy hệ thống trống."""
    for vai in ROLES:
        pv = AC.pham_vi_day_du(vai)
        assert len(pv) >= len(AC.API_CHUNG), f"{vai} không có phạm vi nào"
        assert "/api/v1/auth" in pv, f"{vai} không gọi được /auth – không đăng nhập nổi"


def test_moi_man_hinh_tren_menu_deu_co_du_api_dang_sau():
    """Ẩn một cánh cửa thì đóng luôn phòng sau nó; mở cửa mà không mở phòng thì tệ hơn – người dùng
    bấm vào và nhận 403 mà không hiểu vì sao."""
    hong = []
    for man, vai_tro in AC.MENU_ROLES.items():
        for g in AC.MAN_HINH_API.get(man, ()):
            for vai in vai_tro:
                if not any(g.startswith(x) or x.startswith(g) for x in AC.pham_vi_day_du(vai)):
                    hong.append(f"{vai} thấy {man} trên menu nhưng không gọi được {g}")
    assert not hong, hong


def test_chan_mac_dinh_that_su_chan():
    """Nhân viên kinh doanh không có màn hình nào dùng tới bảng lương toàn công ty."""
    u = User(username="x", full_name="Thử", role="nv_kd", password_hash="")
    with pytest.raises(HTTPException) as ex:
        AC.check_restricted_scope(u, "/api/v1/payroll-runs/2026-08")
    assert ex.value.status_code == 403
    AC.check_restricted_scope(u, "/api/v1/bookings")        # màn hình của họ thì không được chặn


def test_bon_vai_tro_hep_khong_mat_quyen_dang_dung():
    """Danh sách khai tay cũ được CỘNG vào chứ không bị thay – thay thẳng là họ mất quyền đang dùng
    mà không ai báo."""
    for vai, cu in AC.RESTRICTED_API_PREFIXES.items():
        pv = AC.pham_vi_day_du(vai)
        mat = [x for x in cu if x not in pv]
        assert not mat, f"{vai} mất: {mat}"
