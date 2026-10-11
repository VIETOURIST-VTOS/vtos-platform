"""TRANG PHÂN HỆ /phan-he/<khoa> – anh Tuấn chốt phương án B ngày 13/9/2026.

Bấm một thanh phân hệ trên menu dọc thì mở mục lục đầy đủ của phân hệ ấy, dựng theo bản vẽ
"VTOS · Cấu trúc phân hệ đề xuất V1.3" (12/9/2026).

VÌ SAO CÓ TRANG NÀY thay vì nhồi cây v1.3 vào menu: v1.3 sâu bốn cấp và liệt kê 184 mục, VTOS thật
có 62 trang. Menu chốt tối đa hai cấp (§I.2) – nhồi vào là vừa phá đặc tả vừa dựng hơn một trăm
đường dẫn hỏng; ẩn phần chưa dựng đi thì không ai còn thấy hệ thống đang nợ những gì.

Phép thử ở đây canh HAI việc mà mắt người dễ bỏ sót khi cây dài:
  1. Mọi đường dẫn trong cây phải là màn hình CÓ THẬT – một mục lục trỏ vào hư không còn tệ hơn
     không có mục lục.
  2. Không màn hình nào của menu bị rơi khỏi cây – nếu rơi thì trang mục lục nói dối về quy mô
     phân hệ.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAY = os.path.join(ROOT, "web", "lib", "cay_phan_he.ts")
TRANG = os.path.join(ROOT, "web", "app", "phan-he", "[khoa]", "page.tsx")
# 11/10/2026 — TRANG nay chỉ còn là BỘ RẼ NHÁNH. Phần vẽ mục lục dọn sang một thành phần riêng,
# và mấy phép thử dưới đây đi theo nó, vì luật chúng canh là luật của MỤC LỤC chứ không phải của
# đường dẫn: "không gọi máy chủ", "ghi rõ mục nào còn nợ", "khoá chứ không giấu". Để chúng đọc
# TRANG thì từ hôm nay chúng soi nhầm chỗ — và một hàng rào soi nhầm chỗ mà vẫn xanh còn nguy
# hiểm hơn không có hàng rào.
MUC_LUC = os.path.join(ROOT, "web", "components", "MucLucPhanHe.tsx")
BANG = os.path.join(ROOT, "web", "components", "BangChiTieuPhong.tsx")
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")

TAM_KHOA = ["tongquan", "marketing", "khachhang", "vanhanh",
            "nhansu", "taichinh", "baocao", "quantri"]


def _cay():
    return open(CAY, encoding="utf-8").read()


def _shell():
    return open(SHELL, encoding="utf-8").read()


def _khong_ghi_chu(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S)


def _duong_dan(src):
    """Mọi href trong một tệp, đã bỏ tham số ?tab=… và neo #… để so với thư mục trang."""
    ra = set()
    for h in re.findall(r'href: "(/[^"]*)"', src):
        ra.add(h.split("?")[0].split("#")[0])
    return ra


def test_du_tam_phan_he_va_dung_khoa_cua_menu():
    """Khoá của cây phải TRÙNG khoá menu, không phải một bộ tên khác.

    Lệch một chữ thì thanh phân hệ dẫn tới /phan-he/<khoa> không có thật và người dùng gặp trang
    "Không có phân hệ này" – lỗi chỉ lộ ra khi bấm đúng nhóm ấy.

    ══ TC-70 · 18/9/2026 — LUẬT ĐƯỢC NỚI, KHÔNG BỊ BỎ ═══════════════════════════════════════════
    BÊN CŨ (12/9): cây có ĐÚNG tám khoá, và tám khoá ấy trùng khít tám nhóm menu.
    BÊN MỚI (18/9): menu vẫn ĐÚNG TÁM NHÓM – chỗ ấy không đổi. Nhưng hai nhóm nay xổ ra thành năm
      phân hệ CON (Kinh doanh → lẻ, đoàn · Điều hành → tour, xe, HDV), nên tệp cây có thêm năm khoá
      nữa trong PHAN_HE_CON. Điều phải canh vẫn y nguyên về bản chất: MỌI khoá menu trỏ tới đều
      phải có thật trong cây, và mọi khoá trong cây đều phải tới được từ menu. Chỉ có điều nay
      "tới được" gồm cả đường đi qua bảng xổ ra.

    Con số tám không được nới: tám nhóm là đặc tả §I.2, còn năm phân hệ con là cấp DƯỚI nó.
    """
    cay = _cay()
    # Tách hai phần: CAY_PHAN_HE (cha) và PHAN_HE_CON (con). Cắt tại chỗ khai PHAN_HE_CON chứ
    # không dò cả tệp, nếu không `khoa:` của phần con lẫn vào phần cha và phép thử đếm ra 13.
    cat = cay.find("export const PHAN_HE_CON")
    assert cat > 0, "không tìm thấy khai báo PHAN_HE_CON – TC-70 đã bị gỡ mất?"
    khoa_cha = re.findall(r'khoa: "(\w+)"', cay[:cat])
    assert khoa_cha == TAM_KHOA, f"cây phân hệ cha có {khoa_cha}, phải đúng tám khoá {TAM_KHOA}"

    khoa_menu = re.findall(r'\{ key: "(\w+)", label:', _shell())
    assert khoa_menu == TAM_KHOA, f"menu có {khoa_menu}, lệch khoá với cây phân hệ"

    # Năm phân hệ con: khoá khai trong menu (`phans`) phải trùng khít khoá khai trong cây.
    con_cay = set(re.findall(r'\{ khoa: "(\w+)", cha: "(\w+)"', cay[cat:]))
    con_menu = set()
    for khoi in re.findall(r'phans:\s*\[(.*?)\]', _shell(), re.S):
        con_menu |= set(re.findall(r'\{ khoa: "(\w+)"', khoi))
    assert {k for k, _ in con_cay} == con_menu, (
        f"menu xổ ra {sorted(con_menu)} nhưng cây khai {sorted(k for k, _ in con_cay)} – "
        "lệch một khoá là một mục xổ ra dẫn tới trang 'Không có phân hệ này'")
    assert len(con_menu) == 5, f"phải đúng năm phân hệ con, đang có {len(con_menu)}: {sorted(con_menu)}"
    # Cha của mỗi phân hệ con phải là một trong tám khoá, không được trỏ vào hư không.
    for k, cha in con_cay:
        assert cha in TAM_KHOA, f"phân hệ con {k} khai cha '{cha}' không có trong tám phân hệ"


# TC-70 · 18/9/2026 — hai nhóm nay XỔ RA thay vì đi. Danh sách này là phần đảo của luật bên dưới:
# nhóm nào có tên ở đây thì KHÔNG được có href, nhóm nào không có tên ở đây thì BẮT BUỘC phải có.
NHOM_XO_RA = {
    "khachhang": ["kdle", "kddoan"],
    "vanhanh": ["dhtour", "dhxe", "hdv"],
}


def test_moi_thanh_phan_he_deu_bam_di_duoc():
    """Bấm vào một thanh phân hệ thì PHẢI xảy ra đúng một việc: đi tới trang, hoặc xổ ra phân hệ con.

    Bảng điều hành CHÍNH LÀ màn hình của phân hệ Tổng quan – dựng thêm một trang mục lục cho nó chỉ
    tổ thêm một cú bấm.

    ══ TC-70 · 18/9/2026 — LUẬT BỊ ĐẢO MỘT PHẦN, ghi cả hai bên ══════════════════════════════════
    BÊN CŨ (13/9): CẢ TÁM nhóm đều phải có `href`; "bấm vào thanh phân hệ mà không đi đâu cả" là
      lỗi. Lý do vẫn đúng và vẫn được canh cho sáu nhóm còn lại: một thanh trông bấm được mà bấm
      không ra gì thì người dùng tưởng phần mềm hỏng.
    BÊN MỚI (18/9): hai nhóm Kinh doanh và Điều hành KHÔNG có href, vì mỗi nhóm nay đại diện cho
      nhiều phòng chứ không phải một – "bấm là đi" đi đâu cũng sai một phòng. Nhưng bấm vào chúng
      VẪN xảy ra chuyện: bảng xổ ra. Cái bị cấm vẫn nguyên – bấm mà KHÔNG XẢY RA GÌ CẢ.

    Vì thế phép thử này canh hai chiều, không phải nới lỏng một chiều: nhóm thường thiếu href là
    lỗi, mà nhóm xổ ra CÓ href cũng là lỗi – có cả hai thì thanh vừa đi vừa bung, đúng thứ luật
    13/9 cấm và 18/9 vẫn cấm.
    """
    shell = _khong_ghi_chu(_shell())
    for khoa in TAM_KHOA:
        # ══ TC-69 · 18/9/2026 — NỚI KHUÔN DÒ, KHÔNG ĐỔI LUẬT ═══════════════════════════════════
        # Bản cũ đòi `icon` đứng NGAY SAU `label`. Từ 18/9 nhóm "nhansu" có thêm `label_ngan`
        # ("HC – NS") xen vào giữa, nên khuôn cũ trượt và phép thử báo "không có href" trong khi
        # href vẫn nằm nguyên đó – nó tố cáo sai, chứ mã không hỏng.
        # Khuôn mới cho phép bất kỳ thuộc tính nào nằm giữa `label` và `href`, nhưng `[^{}]*?`
        # KHÔNG cho phép vượt qua dấu ngoặc nhọn, nên nó không thể vơ nhầm `href` của nhóm kế tiếp.
        m = re.search(r'\{ key: "%s", label: "[^"]+",[^{}]*?href: "([^"]+)"' % khoa, shell)

        if khoa in NHOM_XO_RA:
            assert not m, (
                f"nhóm {khoa} xổ ra phân hệ con thì KHÔNG được có href – có cả hai là thanh vừa đi "
                f"vừa bung, đúng thứ luật 13/9 cấm")
            # Bấm vào phải xảy ra chuyện gì đó: đủ mục con, và mỗi mục trỏ đúng /phan-he/<khoa>.
            khoi = re.search(r'\{ key: "%s".*?phans:\s*\[(.*?)\]' % khoa, shell, re.S)
            assert khoi, f"nhóm {khoa} không có href mà cũng không có phans – bấm vào không ra gì"
            con = re.findall(r'\{ khoa: "(\w+)", label: "([^"]+)"', khoi.group(1))
            assert [k for k, _ in con] == NHOM_XO_RA[khoa], (
                f"nhóm {khoa} xổ ra {[k for k, _ in con]}, phải là {NHOM_XO_RA[khoa]}")
            for k, ten in con:
                assert ten.strip(), f"phân hệ con {k} không có nhãn – bảng xổ ra sẽ có một dòng trống"
            continue

        assert m, f"nhóm {khoa} không có href – bấm vào thanh phân hệ sẽ không đi đâu cả"
        mong = "/" if khoa == "tongquan" else f"/phan-he/{khoa}"
        assert m.group(1) == mong, f"nhóm {khoa} trỏ {m.group(1)}, phải là {mong}"


def test_moi_duong_dan_trong_cay_deu_co_trang_that():
    """Mục lục trỏ vào hư không còn tệ hơn không có mục lục.

    Mục CHƯA DỰNG thì để trống href và trang tự ghi "Chưa dựng" – đó là cách nói thật. Cái không
    chấp nhận được là một href trông như thật mà bấm vào ra 404.
    """
    thieu = []
    for h in sorted(_duong_dan(_cay())):
        if h == "/":
            continue
        thu_muc = os.path.join(ROOT, "web", "app", h.strip("/"))
        if not os.path.isfile(os.path.join(thu_muc, "page.tsx")):
            thieu.append(h)
    assert not thieu, f"cây phân hệ trỏ tới trang không tồn tại: {thieu}"


def test_khong_man_hinh_nao_cua_menu_bi_rot_khoi_cay():
    """Menu và cây phải nói cùng một điều về quy mô phân hệ.

    Một màn hình có trong menu mà vắng trong cây nghĩa là trang mục lục đếm thiếu – anh Tuấn đọc
    "12/40 màn hình đã dựng" rồi tưởng còn nợ nhiều hơn thực tế.
    """
    trong_cay = _duong_dan(_cay())
    trong_menu = set()
    shell = _khong_ghi_chu(_shell())
    i = shell.index("export const GROUPS")
    # Dừng ở CA_NHAN: khối cá nhân (đổi mật khẩu, phiếu lương) nằm trên THANH NGANG, không thuộc
    # phân hệ nào – đòi nó có mặt trong cây là đòi sai chỗ.
    j = shell.index("const CA_NHAN")
    for m in re.finditer(r'\["[^"]+",\s*"(/[^"]+)"\]', shell[i:j]):
        trong_menu.add(m.group(1).split("?")[0].split("#")[0])
    thieu = sorted(trong_menu - trong_cay)
    assert not thieu, f"{len(thieu)} màn hình có trong menu nhưng vắng trong cây phân hệ: {thieu}"


def test_tab_khong_bao_gio_thanh_mot_man_hinh_rieng():
    """v1.3 ghi rõ "Tab / nhánh chi tiết": đây là tab BÊN TRONG một trang.

    Gắn href cho một tab là hứa một màn hình không tồn tại; và đếm nó vào tổng số màn hình thì con
    số "đã dựng / tổng" sai ngay từ mẫu số.
    """
    cay = _cay()
    # Đọc theo DÒNG chứ không theo khối: một mục cha có href hoàn toàn có thể chứa các tab bên
    # trong, nên bắt cả khối sẽ báo nhầm chính cái cấu trúc đúng.
    for dong in cay.splitlines():
        if "tab: true" in dong:
            assert "href:" not in dong, f"mục tab không được có đường dẫn riêng: {dong.strip()}"
    assert "if (!m.tab)" in open(MUC_LUC, encoding="utf-8").read() or "!m.tab" in cay, \
        "phép đếm phải loại tab ra khỏi tổng số màn hình"


def test_muc_luc_khong_hien_mot_con_so_nghiep_vu_nao():
    """Ranh giới 09/9/2026: Claude viết CẤU TRÚC, không nhập và không tải SỐ LIỆU.

    Mục lục không được gọi máy chủ – có gọi là bắt đầu hiện số, mà số trên một mục lục thì không
    có cửa nhập nào đứng sau.

    PHÉP THỬ NÀY ĐỔI CHỖ SOI, KHÔNG ĐỔI LUẬT (11/10/2026). Trước đây nó tên là
    `test_trang_phan_he_khong_hien_mot_con_so_nghiep_vu_nao` và soi `[khoa]/page.tsx`, vì hồi ấy
    trang phân hệ CHÍNH LÀ mục lục. Từ 11/10 trang ấy mở ra bảng chỉ tiêu của phòng, nên nó PHẢI
    gọi máy chủ; còn mục lục thì lùi sang `components/MucLucPhanHe.tsx`, nơi luật cũ vẫn đúng
    từng chữ.

    Đây là lý do mục lục được tách thành một tệp riêng thay vì ở chung một tệp với bảng: ở chung
    thì phép thử này buộc phải gỡ bỏ. Gỡ một hàng rào vì nó cản đường là cách hàng rào chết dần,
    nên vòng 11/10 chọn dọn mã cho vừa hàng rào chứ không dọn hàng rào cho vừa mã.
    """
    src = open(MUC_LUC, encoding="utf-8").read()
    for cam in ("api(", "fetch(", "useEffect"):
        assert cam not in src, f"mục lục phân hệ không được {cam} – đây là mục lục, không phải báo cáo"


def test_ghi_ro_muc_nao_con_no():
    """Ba trạng thái phải hiện thành chữ, không chỉ bằng màu: Đã có · Chưa dựng · Tab trong trang."""
    src = open(MUC_LUC, encoding="utf-8").read()
    for nhan in ("Đã có", "Chưa dựng", "Tab trong trang"):
        assert nhan in src, f"thiếu nhãn trạng thái “{nhan}”"


def test_cay_giu_du_muc_cua_ban_ve_v13():
    """184 mã của v1.3 phải có mặt đủ, kể cả mục chưa dựng.

    Bỏ bớt mục chưa dựng cho cây gọn là xoá mất phần việc còn nợ – đúng thứ trang này sinh ra để
    giữ. Con số 184 là số dòng có mã trong bản vẽ v1.3 ngày 12/9/2026.
    """
    ma = re.findall(r'ma: "(\d[\d.]*)"', _cay())
    v13 = [m for m in ma if not m.startswith("0")]
    assert len(set(v13)) >= 184, f"cây chỉ còn {len(set(v13))} mục, bản vẽ v1.3 có 184"


def test_luat_dien_thoai_moi_khong_duoc_nam_duoi_khoi_tc4():
    """Cái bẫy đã sập một lần, 13/9/2026 – ghi lại để không sập lần hai.

    test_tc4_dien_thoai đọc bản điện thoại bằng rindex("@media (max-width:640px)"): nó lấy từ lần
    xuất hiện CUỐI CÙNG tới hết tệp. Thêm một khối 640px xuống cuối globals.css thì bốn phép thử
    TC-4 đỏ, mà thông báo lỗi lại nói về bảng trên điện thoại chứ không hé một chữ nào về vị trí –
    mất nửa giờ mới lần ra. Phép thử này nói thẳng nguyên nhân.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    i = css.rindex("@media (max-width:640px)")
    cuoi = css[i:]
    assert "table.bang-doc" in cuoi, (
        "khối @media (max-width:640px) CUỐI CÙNG của globals.css không còn là khối TC-4 – "
        "luật điện thoại mới phải đặt TRƯỚC nó, nếu không bốn phép thử TC-4 đỏ vì lý do khác hẳn")


def test_khoa_muc_khong_co_quyen_chu_khong_giau_di():
    """Anh Tuấn chốt 13/9/2026: ai cũng thấy đủ tám phân hệ, mục không có quyền thì KHOÁ lại.

    Lần đầu em làm ngược – ẩn hẳn mục không có quyền. Anh Tuấn đổi, và lý do đúng: giấu thì nhân
    viên không biết hệ thống có những gì, không biết phải xin quyền ở đâu, và tưởng phần mềm chưa
    làm chức năng ấy. Cái lộ ra chỉ là TÊN chức năng – trang này không gọi máy chủ, không có một
    con số nghiệp vụ nào (xem phép thử ở trên).

    Luật áp dụng cho MỌI vai trò, kể cả tài xế, hướng dẫn viên và chuyên viên visa.
    """
    src = open(MUC_LUC, encoding="utf-8").read()
    assert "hidden_menus" in src, "mục lục phân hệ phải đọc hidden_menus của phiên để biết mục nào khoá"
    assert "useShell" in src, "phải lấy người dùng từ Shell, không tự gọi máy chủ"
    assert "Không có quyền" in src, "thiếu nhãn khoá – mục không vào được phải nói ra bằng chữ"
    assert "Tài khoản & phân quyền" in src, "khoá thì phải chỉ chỗ xin quyền, nếu không người ta bế tắc"
    # Hàng chuyển nhanh KHÔNG được lọc: đủ tám phân hệ cho mọi vai là chính điều anh Tuấn chốt.
    assert "CAY_PHAN_HE.filter(" not in src, \
        "hàng chuyển nhanh đang lọc theo quyền – phải hiện đủ tám phân hệ cho mọi vai trò"
    ac = open(os.path.join(ROOT, "backend", "app", "services", "access.py"), encoding="utf-8").read()
    m = re.search(r'MAN_HINH_KHONG_DUOC_AN = \(([^)]*)\)', ac)
    assert m and "/phan-he/[khoa]" in m.group(1), (
        "trang phân hệ phải nằm trong MAN_HINH_KHONG_DUOC_AN – nếu không, ba vai bị giới hạn "
        "(tài xế, HDV, visa) vẫn bị ẩn mất trang mục lục")


def test_menu_giu_du_tam_phan_he_cho_moi_vai_tro():
    """Không nhóm nào rụng khỏi thanh dọc vì vai trò không có màn hình nào trong đó.

    Quyền vẫn nguyên ở hai chỗ khác: bảng xổ ra chỉ liệt kê màn hình vào được, và trang phân hệ
    khoá mục không có quyền.
    """
    src = re.sub(r'/\*.*?\*/|//[^\n]*', '', open(SHELL, encoding="utf-8").read(), flags=re.S)
    assert "filter((g) =>" not in src, \
        "bộ lọc nhóm đã quay lại – tám phân hệ phải hiện đủ với mọi vai trò"


def test_trang_phan_he_da_khai_quyen():
    """test_ai_log đòi mọi trang trong web/app phải khai quyền hoặc nằm trong danh sách mở.

    Trang này khai ở ALL_MENU_PATHS chứ không ở MENU_ROLES: nó không phải màn hình nghiệp vụ, nó chỉ
    liệt kê lại những màn hình người dùng vốn đã được thấy.
    """
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    ac = open(os.path.join(ROOT, "backend", "app", "services", "access.py"), encoding="utf-8").read()
    assert '"/phan-he/[khoa]"' in ac, "trang phân hệ chưa được khai trong ALL_MENU_PATHS"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 11/10/2026 — CỬA PHÂN HỆ MỞ RA BẢNG CHỈ TIÊU CỦA PHÒNG
#
# Chủ tịch: "vào phân hệ của từng phòng ban sẽ thấy được giao diện chính của các giám đốc và
# trưởng phòng thay vì mục lục như hiện tại." Bốn phép thử dưới đây canh bốn chỗ có thể hỏng âm
# thầm sau quyết định ấy.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def _bang_phong() -> dict[str, str]:
    """Đọc PHONG_CUA_PHAN_HE từ cay_phan_he.ts bằng chuỗi, không chạy TypeScript."""
    s = _cay()
    m = re.search(r"export const PHONG_CUA_PHAN_HE[^{]*\{(.*?)\n\};", s, re.S)
    assert m, "không tìm thấy PHONG_CUA_PHAN_HE trong web/lib/cay_phan_he.ts"
    return dict(re.findall(r'(\w+)\s*:\s*"([^"]+)"', m.group(1)))


def test_moi_phong_goc_co_dung_mot_cua_phan_he():
    """Hai chiều, và chiều thứ hai mới là chiều hay quên.

    Chiều dễ: mã phòng khai ở giao diện phải CÓ THẬT trong `bao_cao_phong.PHONG`. Gõ sai một chữ
    thì cửa phân hệ im lặng rơi về mục lục, và không ai biết vì nó trông y như một phân hệ cố ý
    không có bảng.

    Chiều khó: mọi phòng GỐC trong PHONG phải có đúng một cửa. Thêm một phòng mới vào PHONG mà
    quên mở cửa thì phòng ấy có bảng chỉ tiêu nhưng không có lối vào từ menu — thứ hỏng không bao
    giờ tự lộ ra, vì màn hình nào cũng chạy đúng, chỉ là không ai tới được.

    Bộ phận TRỰC THUỘC (ví dụ Visa thuộc Điều hành) KHÔNG cần cửa riêng: báo cáo của nó gộp vào
    phòng mẹ, đúng như `PHONG['visa']['thuoc']` khai.
    """
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    from app.services import bao_cao_phong as BC
    bang = _bang_phong()
    la = sorted(set(bang.values()) - set(BC.PHONG))
    assert not la, f"PHONG_CUA_PHAN_HE trỏ tới mã phòng không có thật trong bao_cao_phong.PHONG: {la}"
    thieu = sorted(set(BC.PHONG_GOC) - set(bang.values()))
    assert not thieu, (
        f"Phòng {thieu} có bảng chỉ tiêu nhưng KHÔNG có cửa phân hệ nào dẫn tới. Mở cửa bằng cách "
        "thêm một cặp vào PHONG_CUA_PHAN_HE trong web/lib/cay_phan_he.ts, hoặc nếu cố ý không mở "
        "thì ghi lý do vào khối chú thích ngay trên bảng ấy — đừng để im lặng.")
    trung = [v for v in set(bang.values()) if list(bang.values()).count(v) > 1]
    assert not trung, f"hai cửa phân hệ cùng trỏ vào một phòng: {sorted(trung)}"


def test_khoa_phan_he_trong_bang_phong_deu_co_that():
    """Khoá nào không khớp một phân hệ nào thì cặp ấy là mã chết — không bao giờ chạy tới."""
    s = _cay()
    co = set(re.findall(r'khoa:\s*"(\w+)"', s))
    la = sorted(set(_bang_phong()) - co)
    assert not la, f"PHONG_CUA_PHAN_HE khai khoá không có phân hệ nào mang tên ấy: {la}"


def test_bang_chi_tieu_chi_co_DUNG_MOT_BAN():
    """Hai cửa, một bảng. Chép bảng ra bản thứ hai là dựng cái đầu thứ hai cho một luật đã có chủ.

    Dấu hiệu đo được: chỉ DUY NHẤT tệp thành phần được gọi cửa `/bao-cao/ban-luu`. Ngày nào một
    màn hình khác tự gọi cửa ấy là ngày đã có bản chép thứ hai — và hai bản thì sớm muộn lệch
    nhau, rồi người dùng tin bản dễ đọc chứ không tin bản đúng.
    """
    goc = os.path.join(ROOT, "web")
    pham = []
    for d, _, fs in os.walk(goc):
        if "node_modules" in d or ".next" in d:
            continue
        for f in fs:
            if not f.endswith((".tsx", ".ts")):
                continue
            duong = os.path.join(d, f)
            if os.path.abspath(duong) == os.path.abspath(BANG):
                continue
            if "/bao-cao/ban-luu" in open(duong, encoding="utf-8").read():
                pham.append(os.path.relpath(duong, ROOT).replace(os.sep, "/"))
    assert not pham, (
        f"{pham} tự gọi cửa báo cáo thay vì dùng components/BangChiTieuPhong.tsx. "
        "Bảng chỉ tiêu phải có đúng một bản.")


def test_cua_phan_he_van_con_loi_vao_muc_luc_o_CA_HAI_DAU():
    """Chủ tịch chọn "cả hai" khi em hỏi đặt lối vào mục lục ở đâu (11/10/2026).

    Vì sao phải canh: mục lục là chỗ DUY NHẤT đọc được hệ thống còn nợ gì — bản vẽ v1.3 có 184
    mục, VTOS thật có ngót 80 trang. Bảng chỉ tiêu đẹp và hữu ích hơn hẳn, nên áp lực tự nhiên là
    gỡ nốt lối vào mục lục cho màn hình gọn. Gỡ xong thì phần nợ không biến mất, nó chỉ thành vô
    hình — và cái gì vô hình thì không ai đòi.

    Phép thử cũng canh chiều ngược: trang KHÔNG được tự quyết định ai xem được bảng nào. Nó chỉ
    được dựa vào hai câu trả lời của máy chủ — `hidden_menus` của phiên và danh sách phạm vi.
    Khai một danh sách vai trò ở đây là dựng bản sao thứ hai của bảng phân quyền.
    """
    src = open(TRANG, encoding="utf-8").read()
    assert src.count("<LoiVaoMucLuc") >= 2, (
        "trang phân hệ phải có lối vào mục lục ở CẢ hai đầu (trên tiêu đề và cuối trang)")
    assert "?xem=muc-luc" in src, "thiếu đường dẫn mở mục lục"
    assert "usePhamViBaoCao" in src and "hidden_menus" in src, (
        "trang phải hỏi máy chủ phạm vi nào được xem, và đọc hidden_menus để khỏi gọi một cửa "
        "chắc chắn 403")
    for vai in ("chutich", "tgd", "ptgd_doan", "ketoan", "hcns"):
        assert f'"{vai}"' not in src, (
            f"trang phân hệ đang khai tên vai trò “{vai}” — bảng vai trò chỉ được nằm ở máy chủ "
            "(bao_cao_phong.PHONG). Khai ở giao diện là dựng bản sao thứ hai, và hai bản sẽ lệch.")
