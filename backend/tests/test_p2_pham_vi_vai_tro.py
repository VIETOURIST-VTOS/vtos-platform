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
# Chốt lại 08/9/2026 khi gộp nhánh robot-phanmem vào main. MỌI vai trò đều +2, ba vai trò kinh doanh
# +3, và ba dòng mới cho vai trò máy. Ghi rõ từng phần cộng thêm, vì đó là toàn bộ công dụng của bảng
# này – con số đổi mà không ai giải thích được thì lần sau người ta sửa số cho xanh rồi đi tiếp.
#
#   +1 mọi vai trò  /api/v1/pham-vi     – P6: ai cũng phải đọc được phạm vi pháp nhân của CHÍNH phiên
#                                          mình, nếu không màn hình không nói được họ đang xem dữ liệu
#                                          của công ty nào.
#   +1 mọi vai trò  /api/v1/phieu-luong – phiếu lương của chính mình; tiền tố này chỉ chứa endpoint tự
#                                          lọc về đúng người, KHÔNG chứa bảng lương toàn công ty.
#   +1 nv_kd/tn_kd/tp_kd  /api/v1/visa  – sales phụ trách mở được hồ sơ visa của khách MÌNH (1259841).
#
# Ba vai trò máy (P8) vào bảng ngay từ lần đầu: chốt sớm thì mọi lần nới sau đều phải giải thích.
#
# ĐO LẠI 08/9/2026 khi gộp main vào nhánh Đợt 2. Ba nhóm thay đổi, mỗi nhóm một lý do, và không vai
# trò nào đổi mà không thuộc một trong ba nhóm này:
#
#   +2  chutich, tgd, bks, cntt      – "/api/v1/ban-hang" (V6: bảng giá, báo giá, hợp đồng khách)
#                                       và "/api/v1/ra-soat-cot-tien" (bàn K1/K2 tách ra địa chỉ riêng)
#   +1  chín vai trò kinh doanh và điều hành – chỉ "/api/v1/ban-hang"
#   +1  ketoan                       – được "/api/v1/ban-hang" và "/api/v1/ra-soat-cot-tien", ĐỒNG THỜI
#                                       MẤT "/api/v1/kiem-soat" theo quyết định của Chủ tịch 08/9.
#                                       Hai thêm một bớt, không phải một lần nới.
#   +0  chín vai trò còn lại         – không ai trong số này liên quan tới bán hàng.
#
# SIẾT 09/9/2026 – sáu dòng khai tay THỪA bị bỏ, sáu vai trò giảm 1–2 nhóm mà KHÔNG mất quyền nào:
#   "/api/v1/auth/" ở 5 vai trò – mọi vai trò đã có "/api/v1/auth" qua API_CHUNG
#   "/api/v1/xe-hdv/" ở xe_hdv   – vai trò này đã suy được tiền tố ấy từ ma trận menu
# Hàng rào so bằng startswith nên tiền tố có dấu gạch cuối chỉ là bản sao hẹp hơn. Với gd_doi_xe và
# tp_hd thì dòng "/api/v1/xe-hdv" KHÔNG thừa – hai vai trò ấy lấy màn hình từ danh sách CHO PHÉP nên
# không suy ra được, bỏ đi là họ mất cả phân hệ xe & HDV.
#
# Hai lần đổi trên TRỰC GIAO nhau (một bên thêm phân hệ, một bên bỏ dòng thừa) nên con số dưới đây
# được ĐẾM LẠI TỪ MÃ, không phải cộng trừ tay hai bảng cũ.
PHAM_VI_DA_CHOT = {
    # +1 cho sáu vai trò ngày 09/9/2026 – nhóm "/api/v1/tong-dai" gắn vào màn hình /kiem-soat: nhật ký
    # NGUYÊN VĂN sự kiện tổng đài (P.A Việt Nam không công bố đặc tả webhook, nên VTOS nghe trước rồi mới
    # diễn giải). Cố ý KHÔNG gắn vào /inbox dù cuộc gọi rồi sẽ hiện ở hộp thư: gắn ở đó là mở tiền tố cho
    # mười ba vai trò trong khi chỉ bốn vai trò gọi được, và phần dôi ra vẫn là quyền đã cấp.
    # ĐẾM LẠI LẦN HAI khi gộp nhánh Đợt 2 vào (09/9/2026 tối). Nhánh ấy thêm ba màn hình có phạm vi
    # API riêng – /tu-dong-hoa (Lịch tự động hóa), /bao-cao (Báo cáo tự động theo phòng), và ba màn
    # hình V6 của chuỗi bán hàng. Bảng này lại được đếm từ mã đã hợp nhất, không cộng trừ tay.
    "chutich": 101, "tgd": 101, "bks": 101, "cntt": 98,
    "ketoan": 83, "tp_dh": 80, "ptgd_doan": 59, "nv_dh": 55, "hcns": 54, "gd_kd": 54,
    # ptgd_mkt 38 → 39 ngày 09/9/2026: Chủ tịch chốt hai Phó TGĐ quản lý phòng của mình, nên màn hình
    # Nạp dữ liệu mở cho cả hai. Đúng MỘT tiền tố dôi ra – "/api/v1/nap-du-lieu"; tiền tố thứ hai của
    # màn hình ấy ("/api/v1/quyet-toan-tour") ông đã có sẵn từ màn hình Tour. ptgd_doan KHÔNG đổi số:
    # ông đã có cả hai tiền tố từ /doc-chung-tu và /tours – tức là trước bản này ông gọi được API nạp
    # dữ liệu mà không có màn hình nào để bấm, đúng loại lệch bản rà 09/9 đi tìm.
    "ptgd_mkt": 42, "nv_kd": 40, "tn_kd": 40, "tp_kd": 42, "nv_mkt": 31,
    "gd_doi_xe": 25, "hanh_chinh": 24, "tp_hd": 23, "xe_hdv": 15, "nv_visa": 17,
    # Vai trò máy – hẹp hơn cả tài xế, và đó là chủ ý: robot chỉ cần đúng bàn làm việc của nó.
    # robot_ks 17 → 96 ngày 09/9/2026: Chủ tịch quyết robot làm việc Ban Kiểm soát thì đọc được thứ
    # BKS đọc, nếu không nó chỉ kiểm tra lại chính báo cáo của mình. Bằng ĐÚNG bks, và chặn ghi bằng
    # READ_ONLY_ROLES. Đây là lần nới lớn nhất từ đầu đợt 2 – ghi ra đây để lần sau ai đọc cũng thấy.
    "robot_pq": 17, "robot_ks": 101, "robot_vpm": 16,
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


def test_bang_chot_phu_du_moi_vai_tro():
    """Thêm một vai trò mà quên chốt phạm vi thì vai trò đó nới bao nhiêu cũng không ai biết.

    Tên cũ của phép thử này là "phủ đủ hai mươi vai trò". Bỏ con số ra khỏi tên khi thêm ba vai trò
    máy: một phép thử mang con số trong tên là một phép thử mà cách sửa nhanh nhất là đổi con số."""
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
