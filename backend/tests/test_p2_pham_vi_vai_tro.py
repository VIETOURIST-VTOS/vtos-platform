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


# ============================ P13 – CHỐT SỐ, KHÔNG ĐỂ NỚI ÂM THẦM ============================
# Đo ngày 08/9/2026 sau khi màn hình kết sổ vào ma trận. Đây là số NHÓM API mỗi vai trò được chạm,
# không phải số đường dẫn – số đường dẫn đổi mỗi lần thêm một endpoint, số nhóm chỉ đổi khi có người
# quyết cho một vai trò thêm hoặc bớt một màn hình.
#
# Vì sao phải chốt: phép thử P2 chỉ canh tính NHẤT QUÁN – không nhóm mồ côi, bản đồ khớp giao diện,
# bốn vai trò hẹp không mất quyền. Không có gì cản một lần nới đưa Kế toán từ 78 lên 92, và loại việc
# đó đã xảy ra thật trong ngày: một vai trò được thêm vào một màn hình trong lúc gộp nhánh, không ai
# thấy cho tới khi một phép thử khác đỏ.
#
# Bảng này KHÔNG phải để đóng băng quyền. Nó để mỗi lần nới là một lần có người phải sửa bảng – tức là
# phải nhìn thấy mình đang nới cho ai, và ghi lại vì sao.
#
# Đo lại ngày 08/9/2026 sau khi gộp nhánh viết phần mềm vào main. Hai lý do, và chỉ hai:
#
#   1. +1 CHO CẢ HAI MƯƠI VAI TRÒ – nhóm "/api/v1/pham-vi" của P6 (phạm vi pháp nhân theo phiên đăng
#      nhập) nằm trong nhóm API chung, nên mọi vai trò đều chạm. Không ai được thêm màn hình nào.
#
#   2. +1 RIÊNG NĂM VAI TRÒ chutich, tgd, bks, cntt, ketoan – màn hình "Rà soát cột tiền"
#      (/api/v1/ra-soat-cot-tien) tách ra khỏi màn hình Kiểm soát.
#      Và ketoan ĐỒNG THỜI MẤT "/api/v1/kiem-soat": Chủ tịch quyết ngày 08/9/2026 rằng Kế toán không
#      xem màn hình Kiểm soát. Nên 78 → 79 là một lần bớt và hai lần thêm, không phải một lần nới.
#
# Nếu lần sau bảng này đỏ mà không giải thích được từng vai trò như trên thì đó là một lần nới nhầm.
PHAM_VI_DA_CHOT = {
    "chutich": 96, "tgd": 96, "bks": 96, "cntt": 94,
    "ketoan": 79, "tp_dh": 76, "ptgd_doan": 56, "nv_dh": 52, "hcns": 51, "gd_kd": 49,
    "ptgd_mkt": 37, "nv_kd": 37, "tn_kd": 37, "tp_kd": 37, "nv_mkt": 29,
    "gd_doi_xe": 23, "hanh_chinh": 23, "tp_hd": 21, "xe_hdv": 16, "nv_visa": 16,
}


def test_pham_vi_tung_vai_tro_dung_nhu_da_chot():
    """Lệch bảng này thì ĐỎ, và người sửa phải sửa cả bảng – đó chính là mục đích."""
    lech = []
    for vai in ROLES:
        thuc = len(AC.pham_vi_day_du(vai))
        chot = PHAM_VI_DA_CHOT.get(vai)
        if chot is None:
            lech.append(f"{vai}: vai trò mới, chưa có trong bảng chốt")
        elif thuc != chot:
            huong = "NỚI" if thuc > chot else "SIẾT"
            lech.append(f"{vai}: {huong} {chot} → {thuc}")
    assert not lech, ("Phạm vi vai trò đổi so với bảng đã chốt. Nếu đúng ý thì sửa PHAM_VI_DA_CHOT và "
                      f"ghi vì sao trong thông điệp ghi mã; nếu không thì đây là một lần nới nhầm: {lech}")


def test_bang_chot_phu_du_hai_muoi_vai_tro():
    """Thêm một vai trò mà quên chốt phạm vi thì vai trò đó nới bao nhiêu cũng không ai biết."""
    thieu = [v for v in ROLES if v not in PHAM_VI_DA_CHOT]
    thua = [v for v in PHAM_VI_DA_CHOT if v not in ROLES]
    assert not thieu and not thua, f"thiếu: {thieu} · thừa: {thua}"


def test_thu_tu_pham_vi_hop_ly():
    """Ba phép so bất biến: lãnh đạo rộng nhất, người ở hiện trường hẹp nhất, và không vai trò nghiệp
    vụ nào rộng bằng Chủ tịch. Ba câu này đúng bất kể con số thay đổi thế nào."""
    pv = {v: len(AC.pham_vi_day_du(v)) for v in ROLES}
    assert pv["chutich"] == pv["tgd"] == pv["bks"], "Chủ tịch, TGĐ và Ban Kiểm soát phải nhìn như nhau"
    assert pv["xe_hdv"] < pv["nv_dh"] < pv["tp_dh"], "người ở hiện trường phải hẹp hơn văn phòng"
    for vai in ("nv_kd", "nv_mkt", "hanh_chinh", "nv_visa", "xe_hdv", "gd_doi_xe", "tp_hd"):
        assert pv[vai] < pv["chutich"], f"{vai} rộng bằng Chủ tịch"
