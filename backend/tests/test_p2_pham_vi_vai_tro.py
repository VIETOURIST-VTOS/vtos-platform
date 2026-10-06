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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGOẠI LỆ DUY NHẤT: nhóm API KHÔNG CẦN ĐĂNG NHẬP
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Một nhóm nằm ở đây KHÔNG phải vì nó bị quên, mà vì người dùng của nó không có tài khoản. Khai
# tên ra để nó là một QUYẾT ĐỊNH đọc được, chứ không phải một ô trống trong hàng rào.
#
# Thêm một dòng vào đây là mở thêm một cửa ra đường. Phép thử ngay dưới đòi mỗi dòng phải chứng
# minh được là nó THẬT SỰ không có hàng rào quyền — để không ai bỏ một nhóm bình thường vào đây
# cho qua phép thử.
CONG_KHAI = {
    "/api/v1/khao-sat": "Trang khách tự chấm điểm sau tour (đề xuất CSKH 25/9/2026). Khách không "
                        "có tài khoản VTOS, nên cửa này mở bằng MỘT MÃ DÙNG MỘT LẦN thay cho đăng "
                        "nhập. Hàng rào của nó là: mã sinh ngẫu nhiên không đoán được, một mã một "
                        "lần ghi, có hạn, có phanh số lần thử theo địa chỉ mạng, và trang chỉ in "
                        "ra những gì khách đã biết.",
}


def test_khong_nhom_api_nao_mo_coi():
    """Nhóm API không vai trò nào chạm được là một phân hệ vừa bị khóa mà chưa ai biết."""
    nhom = {_nhom(r.path) for r in app.routes if getattr(r, "path", "").startswith("/api/v1/")}
    phu = set()
    for vai in ROLES:
        phu |= set(AC.pham_vi_day_du(vai))
    mo_coi = sorted(n for n in nhom
                    if n not in CONG_KHAI
                    and not any(n.startswith(x) or x.startswith(n) for x in phu))
    assert not mo_coi, ("Nhóm API không màn hình nào gọi tới, nên không vai trò nào vào được. Gắn vào "
                        f"MAN_HINH_API của đúng màn hình: {mo_coi}. Nếu đây là cửa cho người KHÔNG "
                        "có tài khoản thì khai vào CONG_KHAI kèm lý do — và đọc phép thử ngay dưới.")


def test_nhom_cong_khai_dung_la_khong_co_hang_rao_quyen():
    """Canh chiều ngược lại: mỗi dòng trong CONG_KHAI phải THẬT SỰ không có hàng rào quyền.

    Không có phép thử này thì CONG_KHAI thành chỗ đổ rác — ai quên khai quyền cho một nhóm bình
    thường cũng bỏ tên vào đây là phép thử trên xanh lại, và hàng rào mất tác dụng đúng vào lúc
    nó đang làm việc của mình.
    """
    import inspect
    from app.api.deps import current_user, require_roles          # noqa: F401
    for nhom, ly_do in CONG_KHAI.items():
        assert len(ly_do) > 80, f"{nhom}: lý do quá ngắn để là một lý do thật"
        duong = [r for r in app.routes if getattr(r, "path", "").startswith(nhom + "/")
                 or getattr(r, "path", "") == nhom]
        assert duong, f"{nhom} khai là công khai nhưng không có đường nào — dòng thừa, xoá đi"
        for r in duong:
            ten = [p.name for p in inspect.signature(r.endpoint).parameters.values()]
            nguon = inspect.getsource(r.endpoint)
            assert "current_user" not in nguon and "require_roles" not in nguon, (
                f"{r.path} nằm trong CONG_KHAI nhưng CÓ hàng rào quyền – bỏ khỏi CONG_KHAI")
            assert "u" not in ten or "User" not in str(inspect.signature(r.endpoint)), (
                f"{r.path} nhận tham số người dùng – nó không phải cửa công khai")


def test_cua_cong_khai_co_phanh_so_lan_thu():
    """Cửa ra đường không có phanh là cửa người ta dội vào được. Phép thử này khoá cái phanh, vì
    nó là thứ dễ bị gỡ nhất khi ai đó sửa cho "chạy nhanh hơn lúc thử"."""
    from app.api.v1 import khao_sat_cong_khai as KS
    nguon = open(KS.__file__, encoding="utf-8").read()
    assert "_phanh(request)" in nguon, "cửa công khai không còn gọi phanh số lần thử"
    assert nguon.count("_phanh(request)") >= 2, "có đường không qua phanh"
    assert KS.TOI_DA_TRONG_CUA_SO <= 60, "phanh nới quá rộng – xem lại vì sao cần nới"


def test_ban_do_man_hinh_api_khong_lech_voi_giao_dien():
    """Bản đồ đo từ mã giao diện. Sửa màn hình để gọi thêm một nhóm API mà quên khai ở đây thì màn
    hình đó gãy trên hệ thống thật – phép thử này bắt trước khi đẩy.

    06/10/2026 — ĐỔI CÁCH SO, và là một lần SIẾT chứ không phải nới. Bản cũ cắt đường gọi xuống còn
    ĐOẠN ĐẦU (`/api/v1/fleet`) rồi đòi đúng chuỗi ấy có trong bản đồ. Hệ quả: một màn hình chỉ cần
    MỘT nhánh con của phân hệ cũng buộc phải khai cả phân hệ — và bản đồ này chính là thứ `pham_vi_day_du`
    cộng ra, nên khai rộng ở đây là NỚI QUYỀN THẬT cho mọi vai trò thấy màn hình đó. Màn hình /xe-hdv
    của tài xế gọi đúng một cửa `/api/v1/fleet/bao-hong`; bắt nó khai `/api/v1/fleet` là trao cho tài xế
    hồ sơ xe, bảng giá và quyết toán chủ xe.

    Nay so bằng ĐƯỜNG ĐẦY ĐỦ: đường gọi được coi là đã khai khi có MỘT mục trong bản đồ là tiền tố của
    nó. `/api/v1/tours` vẫn phủ `/api/v1/tours/{id}/...` như trước, nhưng `/api/v1/fleet/bao-hong` thì
    KHÔNG phủ `/api/v1/fleet/xe` — tức là bản đồ nói được "màn hình này chỉ chạm nhánh ấy".
    """
    if not WEB.exists():
        return
    thieu = []
    for p in sorted((WEB / "app").glob("*/page.tsx")):
        man = "/" + p.parent.name
        khai = tuple(AC.MAN_HINH_API.get(man, ())) + tuple(AC.API_CHUNG)
        if not AC.MAN_HINH_API.get(man):
            continue          # màn hình chưa gắn bản đồ thì phép thử mồ côi ở trên lo
        src = p.read_text(encoding="utf-8")
        # Màn hình gọi qua `api("/x")` (bọc sẵn tiền tố) lẫn `fetch("/api/v1/x")` (viết đủ) – gom cả
        # hai về một dạng rồi mới so, chứ không thì "/api/v1/api/v1/..." lọt vào danh sách thiếu.
        goi = set()
        for m in re.finditer(r'(?:api(?:<[^>]*>)?|fetch)\(\s*[`"\'](?:/api/v1)?/([a-z0-9\-]+(?:/[a-z0-9\-]+)*)', src):
            duong = m.group(1)
            if duong == "api/v1" or duong == "api":
                continue      # đường dựng bằng biến (`/api/v1${path}`) – không đọc được từ chuỗi
            if duong.startswith("api/v1/"):
                duong = duong[len("api/v1/"):]
            if duong:
                goi.add("/api/v1/" + duong)
        for g in sorted(goi):
            if not any(g == k or g.startswith(k.rstrip("/") + "/") for k in khai):
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
#   "/api/v1/xe-hdv/" ở tai_xe   – vai trò này đã suy được tiền tố ấy từ ma trận menu
# Hàng rào so bằng startswith nên tiền tố có dấu gạch cuối chỉ là bản sao hẹp hơn. Với gd_doi_xe và
# tp_hd thì dòng "/api/v1/xe-hdv" KHÔNG thừa – hai vai trò ấy lấy màn hình từ danh sách CHO PHÉP nên
# không suy ra được, bỏ đi là họ mất cả phân hệ xe & HDV.
#
# Hai lần đổi trên TRỰC GIAO nhau (một bên thêm phân hệ, một bên bỏ dòng thừa) nên con số dưới đây
# được ĐẾM LẠI TỪ MÃ, không phải cộng trừ tay hai bảng cũ.
PHAM_VI_DA_CHOT = {
    # ĐÁNH GIÁ SAU TOUR (25/9/2026) – +1 cho MƯỜI BA vai: nhóm "/api/v1/danh-gia" gắn vào màn
    # hình mới /danh-gia (bảng điểm khách chấm cho chuyến, HDV, tài xế; ba con số đã gửi / đã
    # trả lời / không gửi được).
    #
    # nv_kd và tn_kd CÓ màn hình, nhưng chỉ dùng được một nửa: danh sách "khách chưa chấm" và cửa
    # ghi hộ cho khách của chính họ. BẢNG XẾP HẠNG HDV / tài xế thì không – đó là xếp hạng người
    # của phòng khác, và hàng rào nằm ở chữ ký cửa `bang-diem` (api/v1/danh_gia.XEM), không ở
    # màn hình. Mở màn hình mà một cửa trên đó trả 403 là chuyện BÌNH THƯỜNG và có chủ ý.
    #
    # Nhóm "/api/v1/khao-sat" KHÔNG cộng cho vai nào: đó là cửa công khai cho khách không có tài
    # khoản, khai ở CONG_KHAI đầu tệp này kèm phép thử riêng.
    # BÀN BÁN TOUR LẺ (25/9/2026) – +1 cho CHÍN vai: nhóm "/api/v1/ban-tour-le" gắn vào màn hình
    # mới /ban-tour-le (chuyến lẻ đang bán, mỗi dòng kèm ba con số dự toán và biên).
    #
    # Chín vai: bốn vai nền (chutich, tgd, bks, robot_ks), cộng TOÀN KHỐI KINH DOANH LẺ (gd_kd,
    # tp_kd, tn_kd, nv_kd) và cntt.
    #
    # KHÔNG có sales_admin, KHÔNG có ptgd_doan, KHÔNG có ketoan. Hai vai đầu thuộc phòng Đoàn và
    # Chủ tịch nói rõ ngày 25/9: "ý là PKDL, còn PKDĐ vẫn giữ nguyên" — bàn của họ là /sales-admin
    # và /ptgd-doan. Kế toán không có vì màn hình này KHÔNG có một con số quyết toán nào: mọi số ở
    # đây tính từ ba con số dự toán, và Kế toán đã đọc số thật ở bảng quyết toán.
    #
    # Đây là lần NỚI QUYỀN XEM GIÁ VỐN đầu tiên cho phòng Lẻ, nên nó hẹp đúng bằng ba con số:
    # không dòng nhà cung cấp, không đơn giá mua, không số đã chi. Xem test_bcs1 và
    # access.can_see_du_toan_ba_con_so.
    # TC-81 (24/9/2026) – +1 cho BẢY vai: nhóm "/api/v1/bao-chi-kol" gắn vào màn hình mới
    # /bao-chi-kol (sổ báo chí, sự kiện, phát ngôn + danh bạ KOL/KOC). Bảy vai: bốn vai nền, cộng
    # ptgd_mkt, nv_mkt, cntt. Không một vai Kinh doanh nào và không có ketoan: đây là sổ thương
    # hiệu, không phải sổ tiền — phần tiền của KOL đi đường đề nghị chi và Kế toán đọc nó ở màn
    # hình Ngân sách.
    #
    # ĐÚNG MỘT TIỀN TỐ DÔI RA, DÙ MÀN HÌNH KHAI HAI. Màn hình khai cả "/api/v1/marketing" để dùng
    # cửa đọc và cửa phát của sổ PR đã có sẵn, thay vì dựng cửa đọc thứ hai cho cùng một bảng. Bảy
    # vai này đều đã có nhóm Marketing từ màn hình /marketing, nên khai thêm KHÔNG nới cho ai —
    # đã đo bằng chính phép thử này chứ không suy luận: chạy trước khi sửa bảng, nó báo đúng +1.
    # Nếu một ngày danh sách vai của /bao-chi-kol rộng ra thì phải đo lại đúng chỗ này.
    # TC-75 (24/9/2026) – +1 cho BẢY vai trò: nhóm "/api/v1/gop-tai-khoan" gắn vào màn hình mới
    # /gop-tai-khoan (gộp hai tài khoản trùng của cùng một người).
    #
    # KHÔNG CÓ MỘT VAI KINH DOANH NÀO, và đó là điểm của cả vòng. Bảy vai: bốn vai nền (chutich,
    # tgd, bks, robot_ks), cộng hcns, ketoan, cntt. HC-NS và Kế toán ĐỌC được bảng cặp trùng – họ là
    # người phát hiện ra trùng khi đối chiếu bảng lương và công nợ. Nút GỘP thì hẹp hơn nữa
    # (chutich, tgd, cntt), khai riêng ở api/v1/gop_tai_khoan.py, vì gộp là việc MỘT CHIỀU: chuyển
    # 290 booking sang nhầm người rồi thì không có nút tách ra lại, phải gộp ngược từng bảng bằng tay.
    #
    # SỐ CỘNG LÊN TỪ NỀN CỦA NHÓM 2.8 NGAY DƯỚI, không phải từ nền ngày 19/9 khi vòng này viết xong:
    # tệp được dựng lại từ `git show origin/main` sau khi nhóm 2.6, 2.7, 2.8 đã vào main.
    # TC-74 (19/9/2026) – +1 cho MƯỜI BA vai trò: nhóm "/api/v1/nguoi-ban-hang" gắn vào màn hình mới
    # /nguoi-ban-hang (ai được đứng tên một booking: nhân viên khối Kinh doanh, người ngoài khối đã
    # mở quyền bán, và đối tác ngoài công ty).
    #
    # Mười hai vai giống TC-73, CỘNG `ketoan`. Kế toán có ở đây mà không có ở /to-chuc-kd, và đó là
    # chủ ý: đối tác là bên thứ ba có công nợ và hoá đơn nên Kế toán phải biết danh mục ấy; sơ đồ tổ
    # chức nội bộ thì không liên quan đến họ.
    #
    # SỐ CỘNG LÊN TỪ NỀN CỦA R1 NGAY DƯỚI, không phải từ nền cũ. Ghi ra vì em đã sai đúng chỗ này
    # một lần trong ngày: vòng trước em dựng tệp từ một bản `origin/main` đã cũ, nên khi gộp lên gốc
    # mới nó XOÁ mất phần R1 vừa thêm — mà git không báo xung đột, vì đó là một commit sạch.
    # NỐI ZALO (19/9/2026) – +1 cho MƯỜI vai trò: nhóm "/api/v1/zalo" gắn thêm vào màn hình
    # /doi-mat-khau, là màn hình MỌI NGƯỜI đều vào được. Mười ba vai còn lại không đổi vì họ đã có
    # nhóm ấy sẵn qua các màn hình CRM.
    #
    # VÌ SAO NỚI NÀY KHÔNG PHẢI MỘT LẦN NỚI NHẦM, và vì sao nó đúng là hình hai lớp rào của P2:
    #
    #   · Rào NGOÀI (bảng này) cắt theo MÀN HÌNH, nên nó thô: cho vào màn hình /doi-mat-khau là
    #     cho chạm tới cả nhóm "/api/v1/zalo".
    #   · Rào TRONG cắt theo VIỆC, và nó mới là rào thật. Mọi cửa Zalo có hậu quả ra ngoài đều
    #     khoá bằng require_roles ngay ở chữ ký hàm: /zalo/send, /zalo/send-pending,
    #     /zalo/uy-quyen/*, /zalo/messages, /zalo/status. Một tài xế hay một robot lọt qua rào
    #     ngoài vẫn không gửi được một tin Zalo nào.
    #
    # Ba cửa mới thật sự mở thêm cho mười vai này là ba cửa TỰ PHỤC VỤ: xin mã nối cho chính mình,
    # xem mình đã nối chưa, gỡ nối của chính mình. Cả ba đều khoá phạm vi ghi vào tài khoản đang
    # đăng nhập, và cố ý KHÔNG khai theo vai trò — vì không vai nào được nối hộ người khác.
    #
    # Đúng ra mà nói thì mười vai ấy PHẢI được nới: cảnh báo khủng hoảng gửi qua Zalo chỉ tới được
    # người đã nối máy, và một nhân viên không tự nối được máy của mình là một người vĩnh viễn
    # không nhận được cảnh báo nào.
    # TC-73 (19/9/2026) – +1 cho MƯỜI HAI vai trò: nhóm "/api/v1/to-chuc-kd" gắn vào màn hình mới
    # /to-chuc-kd – sơ đồ chi nhánh → phòng → team → người, mỗi phân công có ngày hiệu lực.
    #
    # Mười hai vai: bốn vai nền (chutich, tgd, bks, robot_ks), bốn vai Kinh doanh (gd_kd, tp_kd,
    # tn_kd, nv_kd), cộng hcns, hanh_chinh, ptgd_doan, cntt. Đúng bằng danh sách khai ở MENU_ROLES,
    # không dôi vai nào.
    #
    # ĐÚNG MỘT TIỀN TỐ, VÀ ĐÓ LÀ CHỖ SUÝT SAI. Bản đầu của vòng này màn hình còn gọi sang
    # "/api/v1/access" và "/api/v1/companies" chỉ để đổ hai ô chọn, và bộ đối chiếu bản đồ màn hình
    # bắt phải khai thêm hai tiền tố ấy – thành +3 cho cả mười hai vai, trong đó nv_kd được đọc danh
    # sách 220 tài khoản toàn công ty vì cần một ô chọn. Cách chữa KHÔNG phải khai thêm mà là bỏ hai
    # lời gọi: cửa "/to-chuc-kd/danh-muc" trả đúng hai danh sách ấy và chỉ trả cho vai được GHI.
    # Cùng bài học đã ghi ở "/api/v1/tong-dai" và "/api/v1/so-con-no": phần dôi ra vẫn là quyền đã cấp.
    # LỚP 3 QUYẾT TOÁN TOUR (11/9/2026) – +1 cho MƯỜI BỐN vai trò: nhóm "/api/v1/quyet-toan-lop3"
    # (dòng khách có ngày sinh, dòng doanh thu, phương tiện từng chặng, HDV chi, sổ dấu vết sửa sau
    # ký) gắn vào màn hình /tours, tức mục "Quyết toán tour" đã có sẵn trong menu.
    #
    # CỐ Ý KHÔNG dựng màn hình mới: menu đã có đúng một mục cho việc này, và thêm lối vào thứ hai cho
    # cùng một việc là cách chắc chắn để người dùng không biết nên bấm vào đâu. Hệ quả là bốn vai
    # Kinh doanh cũng được nới, vì họ xem được /tours để tra chuyến của booking mình.
    #
    # Phần giá vốn thì họ VẪN KHÔNG xem được: hàng rào trong là danh sách XEM của chính
    # app/api/v1/quyet_toan_lop3.py, và danh sách ấy không có vai Kinh doanh nào – cùng lý lẽ đã ghi
    # ở đoạn "/api/v1/lai-lo-tour" bên dưới. Đây đúng là kiểu hai lớp rào mà P2 thiết kế: rào ngoài
    # theo màn hình, rào trong theo việc.
    # ĐẾM LẠI TỪ MÃ ĐÃ HỢP NHẤT 10/9/2026 (gộp Đợt 2 + Lãi lỗ theo tour). Không cộng trừ tay hai bảng:
    # bảng này là kết quả gọi AC.pham_vi_day_du() trên chính mã trong lần gộp này.
    # +1 cho sáu vai trò ngày 09/9/2026 – nhóm "/api/v1/tong-dai" gắn vào màn hình /kiem-soat: nhật ký
    # NGUYÊN VĂN sự kiện tổng đài (P.A Việt Nam không công bố đặc tả webhook, nên VTOS nghe trước rồi mới
    # diễn giải). Cố ý KHÔNG gắn vào /inbox dù cuộc gọi rồi sẽ hiện ở hộp thư: gắn ở đó là mở tiền tố cho
    # mười ba vai trò trong khi chỉ bốn vai trò gọi được, và phần dôi ra vẫn là quyền đã cấp.
    #
    # +1 cho CHÍN vai trò ngày 09/9/2026 – nhóm "/api/v1/lai-lo-tour" gắn vào màn hình mới /lai-lo-tour
    # (bảng lãi lỗ theo tour và theo khách, Chủ tịch duyệt cấu trúc cùng ngày). Chín vai được nới:
    # chutich, tgd, bks, robot_ks, cntt, ketoan, tp_dh, ptgd_doan, nv_dh.
    #
    # Bốn vai Kinh doanh (gd_kd, tp_kd, tn_kd, nv_kd) CỐ Ý không có mặt, và đây là chỗ đáng ghi lại:
    # lãi lỗ tour là số quản trị, bên trong nó là GIÁ VỐN của chuyến. Sale cần doanh thu và công nợ
    # của booking mình phụ trách – hai thứ ấy họ đã có ở màn hình bán hàng. Cho thêm giá vốn chuyến là
    # nới quyền vượt quá việc, và một khi đã nới thì không ai thu lại nữa.
    # ĐẾM LẠI LẦN HAI khi gộp nhánh Đợt 2 vào (09/9/2026 tối). Nhánh ấy thêm ba màn hình có phạm vi
    # API riêng – /tu-dong-hoa (Lịch tự động hóa), /bao-cao (Báo cáo tự động theo phòng), và ba màn
    # hình V6 của chuỗi bán hàng. Bảng này lại được đếm từ mã đã hợp nhất, không cộng trừ tay.
    # ĐẾM LẠI NGÀY 11/9/2026 khi gộp làn V7 Đợt 3 lên nhánh chính. Hai màn hình mới /su-co-tour và
    # /ho-so-kiem-toan mang theo đúng hai nhóm API (/api/v1/su-co-tour, /api/v1/kiem-toan), và mỗi
    # vai chỉ nới đúng nhóm của màn hình mình mở được:
    #   +2  chutich, tgd, bks, robot_ks, cntt, ptgd_doan, tp_dh, ketoan  (mở được CẢ HAI)
    #   +1  nv_dh và bốn vai Kinh doanh, gd_doi_xe, tp_hd                (chỉ Sự cố tour)
    #   +1  hcns, hanh_chinh                                             (chỉ Hồ sơ kiểm toán)
    #   không đổi: ptgd_mkt, nv_mkt, tai_xe, hdv, nv_visa, robot_pq, robot_vpm
    #
    # KHÔNG nhóm nào khác dôi ra, và đó là chủ ý: mọi ô chọn của hai màn hình đi qua CHÍNH phân hệ ấy
    # (/su-co-tour/meta, /su-co-tour/chon/..., /kiem-toan/meta) thay vì gọi thẳng /api/v1/suppliers,
    # /api/v1/bookings hay /api/v1/companies. Gọi thẳng là nhân danh sách vai trò của phân hệ khác
    # lên – bài học vòng 1 của Sự cố tour ngày 10/9/2026.
    #
    # +1 NGÀY 11/9/2026 – Robot A, GD-1. Màn hình mới /dong-tien mang đúng nhóm "/api/v1/dong-tien"
    # (tiền khả dụng, bảng bốn mốc, số dư từng ngày, nghĩa vụ tiền). SÁU vai được nới đúng một nhóm:
    #
    #   chutich · ketoan · bks   – TOÀN CẢNH. Chủ tịch quyết 11/9: một bên lập số, một bên soát số;
    #                              không nhìn đủ thì không làm được việc.
    #   tgd                      – CHỈ tài chính hoạt động tour và xe. Hàng rào ngoài này mở cả nhóm;
    #                              việc cắt TỪNG DÒNG cho Tổng giám đốc là SEC-02 của làn Phân quyền.
    #                              Bảng của TGĐ không có ba dòng tiền khả dụng đầu kỳ, số dư dự kiến
    #                              cuối khoảng và thiếu so với mức dự phòng, và dòng đáy mang tên khác:
    #                              "Dòng tiền thuần từ hoạt động tour và xe".
    #   robot_ks                 – luật chung đã có: robot Kiểm soát xem được mọi màn hình, nếu không
    #                              thì nó giám sát mọi phòng trừ đúng phòng giữ tiền.
    #   cntt                     – vận hành.
    #
    # HAI PHÓ TỔNG GIÁM ĐỐC CỐ Ý KHÔNG CÓ MẶT – giữ nguyên như bản v1.1 của đề xuất giao diện. Nếu
    # lần đếm sau thấy ptgd_doan hoặc ptgd_mkt nhích lên thì đó là một lần nới nhầm, không phải bản này.
    #
    # Màn hình /dong-tien chưa dựng (thuộc Robot B, TC-1→TC-4) nên khai ở CHUA_CO_TRANG của
    # test_p11 kèm ngày dự kiến 30/9/2026.
    #
    # Bảng này là KẾT QUẢ GỌI AC.pham_vi_day_du() trên chính mã đã gộp, không cộng trừ tay.
    #
    # +1 NGÀY 16/9/2026 – TC-41. Màn hình mới /ke-hoach-thang mang đúng nhóm "/api/v1/ke-hoach"
    # (bảng chỉ tiêu một năm, ghi từng ô, số hợp nhất một tháng). SÁU vai được nới đúng một nhóm:
    #   chutich · tgd · bks · robot_ks · cntt · ketoan
    # Hẹp có chủ ý, và đây là chỗ dễ bị đòi nới nhất nên ghi lý do sẵn: chỉ tiêu tháng là thước đo
    # mà mọi phòng sẽ bị đo bằng nó. Trưởng phòng đọc chỉ tiêu của phòng mình ở báo cáo phòng; còn
    # BẢNG CHỈ TIÊU CẢ NĂM của cả tập đoàn thì không phải thứ mở rộng "cho tiện".
    #
    # Quyền GHI còn hẹp hơn nữa và KHÔNG nằm ở hàng rào này: tuple GHI trong api/v1/ke_hoach.py chỉ
    # có chutich, tgd, ketoan. Ban Kiểm soát đọc được thước đo nhưng không sửa được nó — đúng kiểu
    # hai lớp rào mà P2 thiết kế: rào ngoài theo màn hình, rào trong theo việc.
    # +1 cho CHÍN vai trò ngày 16/9/2026 – nhóm "/api/v1/ty-gia" gắn vào màn hình mới /ty-gia
    # (Sổ tỷ giá). Chủ tịch chốt cùng ngày: "tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo
    # form để nhân viên tự nhập tay và tải tệp/ảnh."
    #
    # Chín vai được nới: chutich, tgd, bks, robot_ks, cntt, ketoan, tp_dh, nv_dh, nv_visa.
    # Kế toán giữ sổ; Điều hành nhập tỷ giá của chuyến mình chi; Visa nhập tỷ giá phí lãnh sự.
    #
    # BỐN VAI KINH DOANH CỐ Ý KHÔNG CÓ MẶT, và bản đầu của vá này đã nới nhầm đúng chỗ ấy: nó gắn
    # "/api/v1/ty-gia" vào cả /tours, /non-package và /nap-du-lieu để form ngoại tệ tra được tỷ giá,
    # và thế là MƯỜI TÁM vai trò được nới thay vì chín. Tra tỷ giá từ biểu quyết toán là một việc
    # có thật, nhưng nó phải là một quyết định riêng có người ký, không phải hệ quả phụ của việc
    # thêm một màn hình. Phép thử này bắt được, và đó đúng là việc của nó.
    # ketoan 90 → 92 và gd_kd 56 → 57 NGÀY 18/9/2026 — anh Tuấn chốt cùng ngày, sau khi phép thử này
    # bắt được lần đẩy đầu tiên của không gian Marketing bảy màn hình.
    #
    # VÌ SAO NỚI: màn hình /marketing nay đọc cả sổ lead và sổ nội dung (bản vẽ V3.0), nên bản đồ
    # MAN_HINH_API của nó phải khai thêm "/api/v1/leads" và "/api/v1/noi-dung". Hàng rào ngoài suy từ
    # MENU_ROLES × bản đồ ấy, nên hai vai có /marketing mà thiếu sổ tương ứng thì nhích lên:
    #     ketoan  +2  — "/api/v1/leads" và "/api/v1/noi-dung" (ông có /marketing để đối chiếu chi phí
    #                   chiến dịch, nhưng không có /leads lẫn /noi-dung trong ma trận menu)
    #     gd_kd   +1  — chỉ "/api/v1/noi-dung"; "/api/v1/leads" ông đã có sẵn qua nhóm SALES
    #
    # HÔM NAY KHÔNG LỌT MỘT DÒNG DỮ LIỆU KHÁCH NÀO: hàng rào TRONG vẫn chặn — mọi tuyến lead khai
    # require_roles(*CRM_ROLES) và CRM_ROLES không có ketoan; mọi tuyến nội dung khai ND_XEM và ND_XEM
    # không có ketoan lẫn gd_kd. Cái mất là TẤM LƯỚI DỰ PHÒNG: mai kia ai thêm một tuyến dưới hai
    # nhóm ấy mà quên khai quyền thì hai vai này vào được, còn trước bản này thì không.
    #
    # ĐỔI LẠI, màn hình tự ẩn bốn tab đọc dữ liệu khách với vai không mở được /leads/meta (xem
    # web/app/marketing/page.tsx). Ẩn ở giao diện KHÔNG phải hàng rào và không được tính là hàng rào;
    # nó chỉ để Kế toán mở không gian Marketing ra không gặp bốn tab đỏ mà không hiểu vì sao.
    #
    # NẾU LẦN ĐẾM SAU THẤY MỘT VAI KHÁC NHÍCH LÊN thì đó là một lần nới nhầm, không phải bản này:
    # bản này nới đúng hai vai, đúng ba tiền tố, và cả ba đều đã kể tên ở trên.
    #
    # ══ +1 CHO CHÍN VAI NGÀY 19/9/2026 · TC-71 ════════════════════════════════════════════════
    # Nhóm "/api/v1/so-con-no" gắn vào màn hình mới /so-con-no (Sổ chuyến còn nợ: chuyến đã chạy
    # mà chưa đóng sổ). Chín vai được nới đúng một nhóm, và nhóm ấy chỉ có MỘT cửa GET:
    #   chutich · tgd · bks · robot_ks · cntt · ketoan · tp_dh · ptgd_doan · nv_dh
    # Đúng bằng danh sách của /lai-lo-tour, vì hai màn hình cùng nói về sổ quyết toán của chuyến.
    # Bốn vai Kinh doanh KHÔNG có mặt: giá vốn chuyến ngoài phạm vi của họ, y như /lai-lo-tour.
    #
    # VÌ SAO LÀ MỘT TIỀN TỐ RIÊNG CHỨ KHÔNG NẰM TRONG "/api/v1/bao-cao" — ghi lại vì đây là chỗ
    # bản nháp đầu đã làm sai và bộ kiểm này bắt được:
    #   Đặt cửa trong nhóm /bao-cao thì chỉ NỚI HAI VAI (nv_dh 59→60, cntt 105→106) thay vì chín,
    #   nghe thì ít hơn — nhưng hai vai ấy được nới TOÀN BỘ nhóm báo cáo, trong khi thứ họ cần
    #   đúng một cửa. Hàng rào trong của từng cửa /bao-cao vẫn giữ nên hôm nay chưa mở thêm gì,
    #   nhưng cửa /bao-cao nào thêm về sau sẽ tự mở cho họ mà không ai nhận ra.
    #   Đây đúng bài học đã ghi ở nhóm "/api/v1/tong-dai" ngày 09/9/2026: "gắn ở đó là mở tiền tố
    #   cho mười ba vai trò trong khi chỉ bốn vai gọi được, và PHẦN DÔI RA VẪN LÀ QUYỀN ĐÃ CẤP."
    #   Chín số +1 ở đây là cái giá ĐÚNG BẰNG phần cần, và đó là lý do chọn nó.
    # TC-76 (19/9/2026) – +1 cho MƯỜI HAI vai trò: nhóm "/api/v1/kinh-doanh" gắn vào màn hình mới
    # /kinh-doanh-le (doanh thu và chỉ tiêu Kinh doanh lẻ, xem xuống chi nhánh → phòng → team →
    # người).
    #
    # Mười hai vai giống TC-74, TRỪ `hanh_chinh`. Hành chính có ở /to-chuc-kd và /nguoi-ban-hang vì
    # họ là người GHI hai sổ ấy; còn doanh thu và chỉ tiêu thì họ không ghi và không đọc.
    #
    # RỘNG Ở ĐÂY KHÔNG CÓ NGHĨA LÀ AI CŨNG THẤY SỐ CỦA NGƯỜI KHÁC. Dòng đã được cắt ở MÁY CHỦ theo
    # phân công của chính người đăng nhập (to_chuc_kd.pham_vi_xem), trong truy vấn, trước khi gửi
    # xuống. Một nhân viên mở cửa này bằng tay cũng chỉ nhận về phần của mình. Đó là SEC-02, và nó
    # là lý do danh sách vai được phép rộng.
    # TC-77 (23/9/2026) – +1 cho CHÍN vai trò: nhóm "/api/v1/dong-gop-marketing" gắn vào màn hình
    # mới /dong-gop-marketing (tiền quảng cáo bỏ ra thu về bao nhiêu doanh thu).
    #
    # DANH SÁCH BẰNG ĐÚNG "/marketing", không rộng hơn một vai nào: ai lập được ngân sách thì xem
    # được kết quả của ngân sách ấy. Cố ý KHÔNG có SALES, dù bảng này đầy doanh thu — người bán
    # xem doanh số của mình ở /kinh-doanh-le; câu hỏi ở đây là câu hỏi của người tiêu tiền quảng
    # cáo, không phải của người bán hàng.
    #
    # Nhóm GHI còn hẹp hơn nữa (chutich, tgd, ptgd_mkt, nv_mkt, cntt) và nằm ở tầng cửa, nên
    # `ketoan` cùng `gd_kd` có mặt ở bảng này mà vẫn không gắn nguồn cho booking được.
    # TC-78 (23/9/2026) – +1 cho MƯỜI BA vai trò: nhóm "/api/v1/chuyen-doi-lead" gắn vào màn hình
    # mới /chuyen-doi-lead (nhóm 2.6 – quãng giữa Marketing và Sales).
    #
    # RỘNG HƠN /dong-gop-marketing MỘT CÁCH CÓ CHỦ Ý, và chỗ khác nhau đáng ghi: bảng 2.7 hỏi
    # "tiền quảng cáo thu về bao nhiêu" nên là việc của người tiêu tiền; ba câu của nhóm 2.6 hỏi
    # về QUÃNG GIỮA hai phòng, nên cả Marketing lẫn Kinh doanh phải nhìn cùng một bảng. Giấu nửa
    # bảng khỏi một bên là cách chắc chắn để mỗi phòng tự giữ một con số riêng rồi mang ra cãi.
    #
    # Nhóm GHI hẹp hơn hẳn và nằm ở tầng cửa: KHÔNG có `nv_kd`. Nhân viên kinh doanh có mặt ở
    # bảng này để nhìn, không để tự chuyển lead đang nằm im của mình sang người khác.
    # TC-79 (24/9/2026) – +1 cho CHÍN vai trò: nhóm "/api/v1/doi-soat-marketing" gắn vào màn hình
    # mới /doi-soat-marketing (nhóm 2.8 – bàn cân của phân hệ Marketing).
    #
    # BẰNG ĐÚNG danh sách vai của /dong-gop-marketing, không rộng hơn một vai nào: đây là câu hỏi
    # về SỐ của Marketing, không phải về việc của từng người bán — nên không có SALES, khác hẳn
    # nhóm 2.6 vốn hỏi về quãng giữa hai phòng.
    #
    # Nhóm CHỐT SỐ còn hẹp hơn nữa và nằm ở tầng cửa (chutich, tgd, ptgd_mkt, cntt): chốt số là
    # đặt một mốc mà mọi báo cáo sau đó đem ra so, nên `nv_mkt` có mặt ở bảng này mà không chốt
    # được — dù họ ghi được ở cả nhóm 2.6 lẫn 2.7.
    # ── 24/9/2026 · BÀN LÀM VIỆC P.TGĐ TOUR ĐOÀN — +1 cho ĐÚNG SÁU vai ──────────────────────
    # Nhóm "/api/v1/ptgd-doan" gắn vào màn hình mới /ptgd-doan: hàng đợi dự toán đoàn chờ ký.
    # Sáu vai: bốn vai nền (chutich, tgd, bks, robot_ks) + ptgd_doan + cntt. Đúng bằng danh sách
    # khai ở MENU_ROLES["/ptgd-doan"], không dôi vai nào.
    #
    # MỘT TIỀN TỐ RIÊNG, và đó là chỗ dễ sai. Gắn hàng đợi này vào "/api/v1/tours" cho tiện thì
    # số ở đây KHÔNG đổi một dòng nào — trông như không nới gì cả. Nhưng lúc ấy mọi cửa /tours
    # thêm về sau tự mở cho sáu vai này, và phần dôi ra vẫn là quyền đã cấp. Cùng bài học đã ghi
    # ở "/api/v1/so-con-no" ngày 18/9 và "/api/v1/tong-dai" ngày 09/9.
    #
    # Điều hành KHÔNG được +1: họ trình dự toán, không đứng cùng phía với người duyệt nó.
    #
    # +1 LẦN THỨ HAI ngày 24/9/2026 (vòng 3/3): "/api/v1/sales-admin" — bàn làm việc của Sale Admin
    # phòng Đoàn. Cũng là một nhóm API RIÊNG chỉ đọc, cùng lý do đã ghi ở dòng trên. Lần này
    # `sales_admin` và `ptgd_doan` cùng +1 với bốn vai nền; khối Kinh doanh KHÔNG được +1 vì màn
    # hình ấy là chỗ SOÁT hồ sơ của chính họ.
    # CÔNG NỢ VIETRIP (28/9/2026) – +1 cho CHÍN vai: nhóm "/api/v1/cong-no-vietrip" gắn vào màn
    # hình /cong-no có sẵn (ảnh chụp báo cáo công nợ 8h sáng từ Vietrip, 4 nhóm theo ngày khởi
    # hành). Đúng chín vai đã thấy màn hình /cong-no. sales_admin thấy màn hình nhưng cửa đọc
    # (api/v1/cong_no_vietrip.XEM) KHÔNG có vai ấy – khớp READ của /api/v1/cong-no; màn hình tự ẩn khối.
    # ĐƠN TỪ NHÂN SỰ (07/10/2026) – nhóm việc CON NGƯỜI Chủ tịch quyết 30/9. Màn hình /xe-hdv nay
    # gọi thêm "/api/v1/leaves" và "/api/v1/leave-balance", nên SÁU vai thấy màn hình ấy qua ma
    # trận menu cùng +2: tp_dh, nv_dh, tai_xe, hdv (và hai vai nền đã có sẵn cả hai nhóm).
    #
    # Hai NGƯỜI KÝ chỉ +1 ("/api/v1/leaves"), và khai tay ở RESTRICTED_API_PREFIXES vì hai vai này
    # lấy /xe-hdv từ danh sách CHO PHÉP chứ không từ ma trận. KHÔNG cho họ "/api/v1/leave-balance":
    # cửa ấy trả quỹ phép của CẢ CÔNG TY cho nhóm HR_READ và chỉ quỹ phép của chính mình cho người
    # khác — với người ký thì nó vừa thừa vừa vô dụng, nên không mở.
    "chutich": 123, "tgd": 123, "bks": 123, "cntt": 120,
    "ketoan": 100, "tp_dh": 91, "ptgd_doan": 73, "nv_dh": 64, "hcns": 63, "gd_kd": 65,
    # ── 24/9/2026 · VAI MỚI `sales_admin` (Sale Admin phòng Đoàn) ─────────────────────────────
    # Mở theo Bản mô tả công việc hiệu lực 01/9/2026. 34 nhóm API — HẸP HƠN nhân viên kinh doanh
    # (46), và đó là ĐÚNG hình của vị trí: chị ấy đọc sâu hơn ở phần hồ sơ, công nợ và quyết toán,
    # nhưng KHÔNG có nhóm nào để bán.
    #
    # Ba nhóm vị trí này CÓ mà nhân viên kinh doanh KHÔNG: "/api/v1/lai-lo-tour",
    # "/api/v1/so-con-no", "/api/v1/cong-no" — ba cửa của phần soát giá vốn, tiến độ quyết toán và
    # công nợ mà Phần IV bản mô tả giao. Đây là lần nới quyền xem giá vốn Chủ tịch quyết 24/9/2026;
    # hàng rào canh nó là test_sa7 trong test_sa1_vai_sales_admin.py.
    #
    # Và mọi thứ dẫn tới việc BÁN thì không có: không gửi được yêu cầu đặt dịch vụ, không giữ chỗ,
    # không mở màn hình nhà cung cấp. Hàng rào canh ba điều ấy là test_sa2, test_sa3, test_sa5.
    #
    # 34 → 35 ngày 24/9/2026: +1 cho chính bàn làm việc của mình ("/api/v1/sales-admin").
    "sales_admin": 36,
    # ptgd_mkt 38 → 39 ngày 09/9/2026: Chủ tịch chốt hai Phó TGĐ quản lý phòng của mình, nên màn hình
    # Nạp dữ liệu mở cho cả hai. Đúng MỘT tiền tố dôi ra – "/api/v1/nap-du-lieu"; tiền tố thứ hai của
    # màn hình ấy ("/api/v1/quyet-toan-tour") ông đã có sẵn từ màn hình Tour. ptgd_doan KHÔNG đổi số:
    # ông đã có cả hai tiền tố từ /doc-chung-tu và /tours – tức là trước bản này ông gọi được API nạp
    # dữ liệu mà không có màn hình nào để bấm, đúng loại lệch bản rà 09/9 đi tìm.
    "ptgd_mkt": 48, "nv_kd": 48, "tn_kd": 48, "tp_kd": 50, "nv_mkt": 36,
    # nv_visa 17 → 16 ngày 10/9/2026: SIẾT, và là lần siết có chủ ý. Chủ tịch chốt bộ phận Visa
    # THUỘC Phòng Điều hành, nên người chịu trách nhiệm về con số của Visa là Trưởng phòng Điều hành.
    # Chuyên viên visa rời màn hình /bao-cao – vẫn làm và vẫn thấy hồ sơ của mình ở màn hình Visa,
    # chỉ không còn cầm bản tổng hợp cả bộ phận. Đúng nguyên tắc "nhân viên trong phòng KHÔNG mặc
    # định xem báo cáo phòng"; dòng cũ là chỗ vá tạm khi Visa chưa có người phụ trách.
    # tai_xe và hdv: hai vai tách ra từ `xe_hdv` ngày 05/10/2026, mỗi vai giữ ĐÚNG con số 16 của vai cũ.
    # Bằng nhau là điều phải canh: tách vai là để tách TUYẾN KÝ, không phải để ai đó rộng thêm một cửa.
    #
    # 16 → 17 ngày 06/10/2026, CẢ HAI VAI, và là một lần NỚI có chủ ý: màn hình /xe-hdv nay gọi
    # /api/v1/payment-requests để tài xế lập đề nghị tạm ứng của chính mình (Chủ tịch quyết 05/10).
    # Tiền tố khai ở MÀN HÌNH nên cả hai vai cùng nhận — và hdv nhận một cánh cửa KHÓA: hai hàm
    # `list_pr` và `create_pr` đều không có `hdv` trong `require_roles`, nên bấm vẫn 403. Khai rộng
    # hơn cửa thật ở đúng chỗ này là có chủ ý: bảng phạm vi mô tả MÀN HÌNH chạm tới đâu, còn ai
    # bấm được thì là việc của hàm. Giữ hai con số bằng nhau để hàng rào test_tx1_3 còn canh được
    # rằng lần tách vai không lặng lẽ cho một bên rộng hơn bên kia.
    # +1 cho mười vai ngày 06/10/2026: màn hình /xe-hdv gọi thêm `/api/v1/fleet/bao-hong` (cửa báo
    # hư hỏng xe). Đây là một NHÁNH CON, không phải cả phân hệ đội xe — xem phép thử bản đồ màn
    # hình ở trên, nay so bằng đường đầy đủ nên bản đồ nói được "màn hình này chỉ chạm nhánh ấy".
    # Mười vai cùng +1 vì cả mười đều thấy màn hình /xe-hdv; không vai nào nhận thêm gì khác.
    "gd_doi_xe": 28, "hanh_chinh": 28, "tp_hd": 26, "tai_xe": 20, "hdv": 20, "nv_visa": 18,
    # Vai trò máy – hẹp hơn cả tài xế, và đó là chủ ý: robot chỉ cần đúng bàn làm việc của nó.
    # robot_ks 17 → 96 ngày 09/9/2026: Chủ tịch quyết robot làm việc Ban Kiểm soát thì đọc được thứ
    # BKS đọc, nếu không nó chỉ kiểm tra lại chính báo cáo của mình. Bằng ĐÚNG bks, và chặn ghi bằng
    # READ_ONLY_ROLES. Đây là lần nới lớn nhất từ đầu đợt 2 – ghi ra đây để lần sau ai đọc cũng thấy.
    "robot_pq": 18, "robot_ks": 123, "robot_vpm": 17,   # +2 ngày 24/9/2026, cùng bốn vai nền: /api/v1/ptgd-doan và /api/v1/sales-admin
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
    assert pv["tai_xe"] == pv["hdv"], "tách vai không được làm một trong hai rộng hơn vai kia"
    assert pv["tai_xe"] < pv["nv_dh"] < pv["tp_dh"], "người ở hiện trường phải hẹp hơn văn phòng"
    for vai in ("nv_kd", "nv_mkt", "hanh_chinh", "nv_visa", "tai_xe", "hdv", "gd_doi_xe", "tp_hd"):
        assert pv[vai] < pv["chutich"], f"{vai} rộng bằng Chủ tịch"
