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
    #   không đổi: ptgd_mkt, nv_mkt, xe_hdv, nv_visa, robot_pq, robot_vpm
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
    "chutich": 110, "tgd": 110, "bks": 110, "cntt": 107,
    "ketoan": 94, "tp_dh": 86, "ptgd_doan": 66, "nv_dh": 60, "hcns": 57, "gd_kd": 58,
    # ptgd_mkt 38 → 39 ngày 09/9/2026: Chủ tịch chốt hai Phó TGĐ quản lý phòng của mình, nên màn hình
    # Nạp dữ liệu mở cho cả hai. Đúng MỘT tiền tố dôi ra – "/api/v1/nap-du-lieu"; tiền tố thứ hai của
    # màn hình ấy ("/api/v1/quyet-toan-tour") ông đã có sẵn từ màn hình Tour. ptgd_doan KHÔNG đổi số:
    # ông đã có cả hai tiền tố từ /doc-chung-tu và /tours – tức là trước bản này ông gọi được API nạp
    # dữ liệu mà không có màn hình nào để bấm, đúng loại lệch bản rà 09/9 đi tìm.
    "ptgd_mkt": 43, "nv_kd": 43, "tn_kd": 43, "tp_kd": 45, "nv_mkt": 31,
    # nv_visa 17 → 16 ngày 10/9/2026: SIẾT, và là lần siết có chủ ý. Chủ tịch chốt bộ phận Visa
    # THUỘC Phòng Điều hành, nên người chịu trách nhiệm về con số của Visa là Trưởng phòng Điều hành.
    # Chuyên viên visa rời màn hình /bao-cao – vẫn làm và vẫn thấy hồ sơ của mình ở màn hình Visa,
    # chỉ không còn cầm bản tổng hợp cả bộ phận. Đúng nguyên tắc "nhân viên trong phòng KHÔNG mặc
    # định xem báo cáo phòng"; dòng cũ là chỗ vá tạm khi Visa chưa có người phụ trách.
    "gd_doi_xe": 27, "hanh_chinh": 27, "tp_hd": 25, "xe_hdv": 16, "nv_visa": 18,
    # Vai trò máy – hẹp hơn cả tài xế, và đó là chủ ý: robot chỉ cần đúng bàn làm việc của nó.
    # robot_ks 17 → 96 ngày 09/9/2026: Chủ tịch quyết robot làm việc Ban Kiểm soát thì đọc được thứ
    # BKS đọc, nếu không nó chỉ kiểm tra lại chính báo cáo của mình. Bằng ĐÚNG bks, và chặn ghi bằng
    # READ_ONLY_ROLES. Đây là lần nới lớn nhất từ đầu đợt 2 – ghi ra đây để lần sau ai đọc cũng thấy.
    "robot_pq": 18, "robot_ks": 110, "robot_vpm": 17,
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
