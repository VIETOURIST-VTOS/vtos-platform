"""Menu nhóm nghiệp vụ – TÁM nhóm theo bản vẽ giao diện navy V1.2 (bản duyệt 12/9/2026).

Chốt chặn KỸ THUẬT, không đổi theo chỉ đạo nào: mọi màn hình có trong ma trận phân quyền phải nằm
trong một nhóm menu, nếu không người dùng không còn lối vào; và ngược lại, menu không được trỏ tới
đường dẫn không tồn tại.

Phần khẳng định SỐ NHÓM và TÊN NHÓM là ĐẶC TẢ tổ chức, thay đổi theo chỉ đạo. Lịch sử:
  06/9  8 nhóm theo bản đề xuất đầu tiên.
  07/9  10 nhóm: "Kinh doanh & Sản phẩm" tách đôi; xe và HDV rời "Điều hành".
        rồi 11 nhóm: thêm "Tài khoản của tôi" cho màn hình đổi mật khẩu.
  11/9  7 nhóm theo v1.1 §I.2: hai cấp, bỏ số thứ tự, Quản trị đặt cuối, ẩn mục chưa có trang.
  12/9  giữ 7 nhóm, ĐỔI TÊN theo bản vẽ giao diện (sáng).
        rồi 8 nhóm theo bản vẽ navy V1.2 (chiều): thêm "Marketing & PR" đứng thứ hai, Nhân sự lên
        trước Tài chính. Nhóm mới KHÔNG có mục nào mới – năm mục nhấc từ Kinh doanh sang.

Cái bẫy của lần xếp lại này, ghi ra để lần sau không mắc: v1.1 liệt kê mục con theo CHỨC NĂNG
NGHIỆP VỤ chứ không theo đường dẫn. "Dòng tiền", "Ngân sách", "Chỉ đạo & giao việc", "Phòng ban",
"Hiệu quả đơn vị" là tên NHÓM VIỆC – có cái chưa có trang. Khai một mục menu trỏ tới trang chưa
tồn tại thì cổng P11 đỏ ngay. Vì vậy menu chỉ GOM 53 đường dẫn đang có trong MENU_ROLES; mục nào
của v1.1 chưa có trang thì nằm trong CHUA_XAY, không vào menu.

Ba việc TC-2 đổi, và vì sao chúng KHÔNG làm vỡ chốt chặn kỹ thuật:

  1. Hai phòng Kinh doanh, và Xe với Hướng dẫn viên, thành MỤC CON chứ không bị trộn danh sách.
     Sáu đường dẫn ?mang=le / ?mang=doan vẫn phải có mặt – phép thử ở dưới vẫn canh đúng sáu cái đó.

  2. "Tài khoản của tôi" rời menu trái lên thanh ngang. Ba đường dẫn ấy nằm NGOÀI MENU_ROLES (chúng
     ở trong MAN_HINH_MOI_NGUOI), nên phép thử "mọi màn hình đều có lối vào" không đụng tới. Nhưng
     lối vào thì vẫn phải có thật, nên có một phép thử riêng cho khối cá nhân ở dưới.

  3. Mục chưa có trang bị ẩn khỏi menu, KHÔNG bị xoá khỏi mã: chúng chuyển vào hằng số CHUA_XAY.
     Giữ như vậy để lộ trình còn nợ có chỗ đọc được, và để phép thử vẫn canh được rằng một mục đã
     dựng xong thì phải RỜI khỏi CHUA_XAY và có đường dẫn thật – không ở cả hai trạng thái cùng lúc.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services import access as AC

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")

# Tên TÁM nhóm ĐÚNG THỨ TỰ, nhóm quản trị đặt cuối. Số nhóm, tên và thứ tự theo bản vẽ giao diện
# navy V1.2 anh Tuấn chốt chiều 12/9/2026 (tài liệu v1.2 §I.2 phải đính chính theo). Dấu nối là gạch
# ngang – (en dash); riêng "Marketing & PR" dùng & vì PR là chữ viết tắt.
TAM_NHOM = ("Tổng quan", "Marketing & PR", "Kinh doanh", "Điều hành",
            "Nhân sự – Hành chính", "Tài chính – Kế toán", "Báo cáo – Phân tích",
            "Quản trị hệ thống")

# Năm mục của nhóm Marketing & PR. Chúng KHÔNG phải mục mới: cả năm được nhấc từ nhóm Kinh doanh
# sang, đường dẫn giữ nguyên. Phép thử ở dưới canh đúng chuyện đó – nếu một ngày có ai thêm một mục
# thứ sáu trỏ tới trang chưa dựng thì cổng P11 bắt, còn nếu ai lặng lẽ trả một mục về Kinh doanh thì
# phép thử này bắt.
MARKETING_PR = (("Kế hoạch & ngân sách", "/marketing?tab=ngansach"),
                ("Chiến dịch", "/marketing"),
                ("Nội dung & thương hiệu", "/noi-dung"),
                ("Chăm sóc sau bán", "/cham-soc"),
                ("Phản hồi & khiếu nại", "/khieu-nai"))


def _doc() -> str:
    return open(SHELL, encoding="utf-8").read()


def _khoi(src: str, tu: str, den: str) -> str:
    return src[src.index(tu):src.index(den)]


def menu_paths():
    """(tập đường dẫn trong menu trái, khối mã của GROUPS). Bỏ phần ?tab= khi so sánh."""
    src = _doc()
    block = _khoi(src, "export const GROUPS", "export const CA_NHAN")
    hrefs = re.findall(r',\s*"(/[^"]*)"\]', block)
    return {h.split("?")[0] for h in hrefs}, block


def ca_nhan_paths():
    src = _doc()
    block = _khoi(src, "export const CA_NHAN", "const base =")
    return {h.split("?")[0] for h in re.findall(r',\s*"(/[^"]*)"\]', block)}, block


def chua_xay() -> list:
    src = _doc()
    dong = re.search(r'export const CHUA_XAY\s*=\s*\[(.*?)\];', src, re.S)
    assert dong, "không tìm thấy hằng số CHUA_XAY trong Shell.tsx"
    return re.findall(r'"([^"]+)"', dong.group(1))


# ------------------------------------------------------------------ chốt chặn kỹ thuật

def test_moi_man_hinh_deu_co_loi_vao():
    paths, _ = menu_paths()
    for p in AC.MENU_ROLES:
        assert p in paths, f"{p} có trong ma trận phân quyền nhưng không nằm trong nhóm menu nào"


def test_menu_khong_tro_toi_trang_khong_ton_tai():
    paths, _ = menu_paths()
    ca_nhan, _ = ca_nhan_paths()
    app_dir = os.path.join(ROOT, "web", "app")
    for p in paths | ca_nhan:
        d = app_dir if p == "/" else os.path.join(app_dir, p.strip("/"))
        assert os.path.exists(os.path.join(d, "page.tsx")), f"menu trỏ tới {p} nhưng không có trang"


def test_menu_khong_co_muc_thua_ngoai_ma_tran():
    """Chiều ngược lại của phép thử trên. Một mục trong menu mà không khai quyền ở đâu cả thì theo
    quy ước cũ của kho là "ai đăng nhập cũng thấy" – đúng cái hàng rào P2 dựng lên để chấm dứt."""
    paths, _ = menu_paths()
    thua = sorted(p for p in paths if p not in AC.MENU_ROLES and p not in AC.MAN_HINH_MOI_NGUOI)
    assert not thua, f"menu có mục không khai quyền ở MENU_ROLES lẫn MAN_HINH_MOI_NGUOI: {thua}"


def test_khoi_ca_nhan_co_du_ba_muc_va_khong_lot_vao_menu_trai():
    """Ba mục của chính người đăng nhập phải ở thanh ngang, và chỉ ở đó.

    Để chúng nằm cả hai nơi thì người dùng gặp cùng một mục hai lần mà không hiểu vì sao – và khi
    sửa một chỗ, chỗ kia lặng lẽ lệch đi.
    """
    ca_nhan, _ = ca_nhan_paths()
    assert ca_nhan == {"/reports", "/phieu-luong", "/doi-mat-khau"}, \
        f"khối cá nhân phải có đúng ba mục, đang có {sorted(ca_nhan)}"
    for p in ("/phieu-luong", "/doi-mat-khau"):
        assert p in AC.MAN_HINH_KHONG_DUOC_AN, \
            f"{p} nằm trên thanh ngang cho mọi vai trò nên phải có trong MAN_HINH_KHONG_DUOC_AN"


# ------------------------------------------------------------------ đặc tả v1.1 §I.2

def test_du_tam_nhom_dung_ten_va_dung_thu_tu():
    _, block = menu_paths()
    keys = re.findall(r'key:\s*"([a-z_]+)"', block)
    assert len(keys) == 8 and len(set(keys)) == 8, f"bản vẽ V1.2 yêu cầu đúng 8 nhóm, đang có {keys}"
    ten_nhom = re.findall(r'key:\s*"[a-z_]+",\s*label:\s*"([^"]+)"', block)
    assert tuple(ten_nhom) == TAM_NHOM, \
        f"tên hoặc thứ tự nhóm sai.\n  đang có : {ten_nhom}\n  phải là : {list(TAM_NHOM)}"
    assert ten_nhom[-1] == "Quản trị hệ thống", "v1.1 §I.2: nhóm quản trị phải đặt CUỐI"


def test_marketing_pr_nhan_dung_nam_muc_nhac_tu_kinh_doanh():
    """Nhóm thứ tám không được đẻ mục mới, và cũng không được để sót mục nào ở lại Kinh doanh.

    Hai chiều đều quan trọng. Thiếu một mục thì nhân viên Marketing mất lối vào màn hình của mình;
    thừa một mục trỏ trang chưa dựng thì người dùng gặp đường dẫn hỏng.
    """
    _, block = menu_paths()
    i = block.index('key: "marketing"')
    j = block.index('key: "khachhang"')
    assert i < j, "nhóm Marketing & PR phải đứng TRƯỚC Kinh doanh theo bản vẽ V1.2"
    khoi_mkt = block[i:j]
    for ten, path in MARKETING_PR:
        assert f'["{ten}", "{path}"]' in khoi_mkt, \
            f"mục {ten} phải nằm trong nhóm Marketing & PR, trỏ {path}"
    # Không mục nào trong năm mục ấy còn sót lại ở nhóm Kinh doanh
    khoi_kd = block[j:block.index('key: "vanhanh"')]
    for ten, _path in MARKETING_PR:
        assert f'["{ten}"' not in khoi_kd, f"{ten} còn nằm lại trong nhóm Kinh doanh – đã dời sang Marketing & PR"


def test_bo_so_thu_tu_nhom():
    """v1.1 §I.2 bỏ số thứ tự nhóm. Nhãn kiểu "1. Tổng quan" không được còn."""
    _, block = menu_paths()
    co_so = re.findall(r'label:\s*"(\d+\.[^"]*)"', block)
    assert not co_so, f"nhãn nhóm còn đánh số: {co_so}"


def test_toi_da_hai_cap():
    """Mục con không được chứa mục con. Ba cấp trong một thanh dọc là chỗ người dùng lạc."""
    _, block = menu_paths()
    assert "blocks:" in block, "cấu trúc phải khai bằng khoá blocks (giữ đúng thứ tự của v1.1)"
    # Mỗi mục con là { label: "...", items: [ ... ] }. Trong phần items KHÔNG được có label/items nữa.
    for m in re.finditer(r'\{ label: "([^"]+)", items: \[(.*?)\]\s*\}', block, re.S):
        ten, than = m.group(1), m.group(2)
        assert "items:" not in than, f"mục con {ten} chứa mục con – chỉ cho tối đa hai cấp"
        assert "blocks:" not in than, f"mục con {ten} chứa nhóm – chỉ cho tối đa hai cấp"


def test_hai_phong_kinh_doanh_mo_dung_mang_cua_minh():
    """Gộp hai phòng vào một NHÓM không được làm mất việc tách MẢNG đã chốt ngày 07/9."""
    _, block = menu_paths()
    for path in ("/tours?mang=le", "/requests?mang=le", "/bookings?mang=le",
                 "/tours?mang=doan", "/requests?mang=doan", "/bookings?mang=doan"):
        assert path in block, f"menu hai phòng kinh doanh phải trỏ {path}"
    for ten in ("Lẻ", "MICE"):
        assert f'{{ label: "{ten}"' in block, f"thiếu mục con {ten} theo v1.1 §I.2"


def test_bao_cao_hop_nhat_van_con_loi_vao():
    """Hai phòng vào báo cáo bán hàng của mình qua ?mang=. Nếu CHỈ có hai lối đó thì không còn đường
    nào tới con số HỢP NHẤT – nên nhóm Báo cáo phải giữ một lối vào không kèm tham số."""
    _, block = menu_paths()
    assert '["Kinh doanh", "/sales-reports"]' in block, \
        "nhóm Báo cáo phải có lối vào /sales-reports không kèm ?mang="


def test_khong_quay_lai_ten_cu():
    _, block = menu_paths()
    for cu in ("Robot báo cáo", "Tham số chính sách", "Báo cáo ngày",
               "Điều hành Holdings", "Kinh doanh Lẻ", "Vận tải & Hướng dẫn viên"):
        assert cu not in block, f"tên cũ '{cu}' còn trong menu – v1.1 §I.2 đã đặt tên khác"


# ------------------------------------------------------------------ mục chưa có trang

def test_muc_chua_co_trang_bi_an_chu_khong_phai_link_hong():
    """Ẩn chức năng "sắp có". Không còn mục nào trong menu để đường dẫn rỗng."""
    _, block = menu_paths()
    con_rong = re.findall(r'"([^"]+)",\s*""\]', block)
    assert not con_rong, f"còn mục để đường dẫn rỗng trong menu: {con_rong} – phải ẩn hẳn"
    assert "sắp có" not in block, "nhãn 'sắp có' không còn được hiện trong menu trái"


def test_lo_trinh_con_no_van_doc_duoc():
    """Ẩn khỏi menu KHÔNG có nghĩa là quên. Mục v1.1 có tên mà chưa có trang phải còn trong CHUA_XAY."""
    cx = chua_xay()
    for ten in ("Việc của tôi", "Chỉ đạo & giao việc", "Ngân sách", "Phòng ban",
                "Hiệu quả đơn vị", "Hồ sơ pháp lý & thuế", "Văn bản", "Nhật ký kỹ thuật"):
        assert ten in cx, f"{ten} phải còn trong CHUA_XAY để lộ trình còn nợ đọc được"


def test_da_xay_thi_phai_roi_khoi_chua_xay_va_tro_dung_man_hinh():
    """Không được ở cả hai trạng thái cùng lúc: vừa nằm trong CHUA_XAY vừa có đường dẫn thật."""
    _, block = menu_paths()
    cx = chua_xay()
    for ten, path in (("Tổ chức & đơn vị", "/companies"),
                      ("Tài khoản & phân quyền", "/access"), ("Vị trí AI & quyền hạn", "/ai-roles"),
                      ("Chiến dịch", "/marketing"), ("Kế hoạch & ngân sách", "/marketing?tab=ngansach"),
                      ("Nội dung & thương hiệu", "/noi-dung"), ("Chăm sóc sau bán", "/cham-soc"),
                      ("Phản hồi & khiếu nại", "/khieu-nai"),
                      ("Giá & chính sách bán", "/bang-gia"), ("Báo giá", "/bao-gia?mang=kd_le"),
                      ("Báo giá đoàn", "/bao-gia?mang=kd_doan"), ("Hợp đồng", "/hop-dong-khach"),
                      # V7 Đợt 3 (10/9/2026). Sự cố tour dùng BẢNG RIÊNG su_co_tour, không dùng lại
                      # bảng incidents – incidents là hồ sơ kỷ luật nhân viên, việc khác hẳn.
                      ("Sự cố tour", "/su-co-tour"), ("Hồ sơ kiểm toán", "/ho-so-kiem-toan"),
                      ("Dòng tiền", "/finance?tab=forecast")):
        assert ten not in cx, f"{ten} đã có màn hình, không được để trong CHUA_XAY"
        assert f'["{ten}", "{path}"]' in block, f"thiếu mục {ten} trỏ {path}"


# ------------------------------------------------------------------ thu / bung thanh dọc

def test_moi_nhom_deu_co_bieu_tuong_va_bieu_tuong_phai_co_chu_thich():
    """v1.1 §I.2: thu còn một cột biểu tượng, và "biểu tượng phải có chú thích".

    Một hàng biểu tượng không chú thích là một hàng phải đoán – và người đoán sai thì bấm nhầm vào
    nhóm khác rồi kết luận là phần mềm chậm.
    """
    src = _doc()
    _, block = menu_paths()
    # TC-69 · mẫu cho phép có `label_ngan` chen giữa `label` và `icon`. Luật không đổi — vẫn là
    # "tám nhóm đều phải có biểu tượng"; chỉ là thứ tự trường trong mã không còn cố định sau khi
    # nhóm Nhân sự có thêm nhãn ngắn cho thanh dọc.
    icons = re.findall(r'key:\s*"[a-z_]+",\s*label:\s*"[^"]+",(?:\s*label_ngan:\s*"[^"]*",)?\s*icon:\s*"([^"]+)"',
                       block)
    assert len(icons) == 8, f"phải đủ 8 biểu tượng cho 8 nhóm, đang có {len(icons)}: {icons}"
    assert all(i.strip() for i in icons), f"có biểu tượng rỗng: {icons}"
    # Nhãn nhóm phải đi vào title và aria-label, không được mất khi thu.
    assert 'title={g.label}' in src and 'aria-label={g.label}' in src, \
        "nút nhóm phải mang title và aria-label bằng nhãn nhóm – đó là 'chú thích' của biểu tượng"


def test_be_rong_thanh_doc_dung_dac_ta():
    """§I.2 cho một khoảng: rộng 224–256px, thu còn 56–64px.

    KHOẢNG TRÊN NỚI TỪ 240 LÊN 256px NGÀY 12/9/2026, vì đo được chứ không vì thấy chật.
    Anh Tuấn yêu cầu nhãn phân hệ to hơn (13→14px) và không được cắt chữ. Đo bằng Chromium với
    đúng phông Be Vietnam Pro 14px/500:

        Nhân sự – Hành chính   140,9px   ← nhãn dài nhất
        Báo cáo – Phân tích    126,1px
        Tài chính – Kế toán    121,4px

    Khung quanh chữ trong `aside.side .grp` là 106px (lề 16 + viền 2 + đệm 24 + biểu tượng 20 +
    hai khoảng hở 20 + mũi tên 12 + thanh cuộn 12). 140,9 + 106 = 247px.

    Nghĩa là 240px – mức trần cũ – THIẾU 7px và "Nhân sự – Hành chính" bị cắt bằng dấu ba chấm.
    Đặt 252px để còn dư một chút cho phông dự phòng khi Google Fonts chưa về.

    ══ ĐƠN VỊ ĐỔI 18/9/2026 (TC-67), KHOẢNG KHÔNG ĐỔI ═════════════════════════════════════════
    TRƯỚC:  `aside.side{flex:0 0 252px}` – con số cứng.
    TỪ NAY: `calc(252/14*1rem)` – rộng 252px ở cỡ chữ gốc, NỞ RA khi người dùng tăng cỡ chữ.

    Vì sao buộc phải nở: cả phép tính 247px trong tài liệu này dựa trên nhãn "Nhân sự – Hành chính"
    đo ở phông 14px. Người dùng kéo cỡ chữ lên 20 thì nhãn ấy rộng 201px, cần 307px – thanh dọc
    đứng nguyên 252px là nhãn bị cắt bằng dấu ba chấm, đúng cái mức trần 240px cũ từng gây ra.
    Đơn vị co giãn giữ nguyên TỈ LỆ ấy ở mọi cỡ, nên phép tính trên đúng cho cả ba cỡ.

    BỀ RỘNG KHI THU THÌ VẪN LÀ px, và đó là một quyết định chứ không phải chỗ bỏ sót: lúc thu,
    thanh dọc chỉ còn BIỂU TƯỢNG — các hình SVG 24×24 cố định, không có chữ nào. Cho nó nở theo cỡ
    chữ là chừa chỗ trống cho một thứ không tồn tại.

    ══ TC-69 · 18/9/2026 — NGƯỠNG DƯỚI TÍNH LẠI, PHÉP THỬ GIỮ NGUYÊN ═══════════════════════════
    TRƯỚC:  `rộng ≥ 247`, vì nhãn "Nhân sự – Hành chính" cần 140,9 + 106 = 247px.
    TỪ NAY: `rộng ≥ 228`, và HAI điều đã đổi nên con số cũ không còn đúng:

      1. VỎ BAO QUANH CHỮ KHÔNG PHẢI 106px MÀ LÀ 87px. Đo lại trực tiếp trên trang thật 18/9/2026
         (lấy bề rộng thanh trừ bề rộng ô nhãn) thay vì cộng tay từng phần như bản 12/9. Bản cũ
         cộng dư một thanh cuộn 12px luôn có mặt và một biểu tượng rộng hơn thực tế.

      2. NHÃN DÀI NHẤT KHÔNG CÒN LÀ "Nhân sự – Hành chính". Anh Tuấn 18/9 đổi chữ VẼ RA trên menu
         thành "HC – NS" (tên phân hệ giữ nguyên — xem `label_ngan` ở Shell.tsx). Nhãn dài nhất
         nay là "Báo cáo – Phân tích".

    ĐO VỚI PHÔNG DỰ PHÒNG, KHÔNG PHẢI PHÔNG THẬT — và đây là chỗ bản nháp của vòng này suýt sai.
    Lần đo đầu em để Be Vietnam Pro đã tải xong và kết luận 224px là đủ. Nhưng lúc Google Fonts
    chưa về — vài giây đầu mỗi lần mở, hoặc vĩnh viễn trên máy chặn phông ngoài — trình duyệt rơi
    về phông dự phòng, RỘNG HƠN 8%. Chính chú thích 12/9 ở trên đã dặn ("để còn dư một chút cho
    phông dự phòng"), và bản nháp đã bỏ qua nó.

    Bề rộng tối thiểu từng nhãn, đo ở cỡ chữ 14 với phông dự phòng rộng nhất (system-ui):
        225px  Báo cáo – Phân tích      ← nhãn dài nhất sau khi đổi
        220px  Tài chính – Kế toán
        212px  Quản trị hệ thống
        143px  HC – NS
    Chốt 232px: dư 7px trên trần 225. KHÔNG lấy sát 228 vì con số 225 đo trên Chromium/Linux, còn
    người dùng chạy Windows — "system-ui" ở đó là Segoe UI, bề rộng không giống hệt. 7px là khoảng
    dự phòng cho chỗ chênh ấy, không phải một con số cho đẹp.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    # Nhận cả hai cách viết; nhánh `px` giữ lại để bắt được nếu ai đó gõ ngược lại số cứng.
    m_rong = re.search(r'aside\.side\{flex:0 0 (?:calc\((\d+)/14\*1rem\)|(\d+)px)', css)
    m_thu = re.search(r'aside\.side\.thu\{flex:0 0 (\d+)px', css)
    assert m_rong, "không tìm thấy bề rộng thanh dọc trong globals.css"
    assert m_thu, "không tìm thấy bề rộng khi THU trong globals.css"
    rong, thu = int(m_rong.group(1) or m_rong.group(2)), int(m_thu.group(1))
    assert 224 <= rong <= 256, f"bề rộng {rong}px ngoài khoảng 224–256px của §I.2"
    assert rong >= 228, (
        f"bề rộng {rong}px CẮT nhãn 'Báo cáo – Phân tích' khi phông dự phòng chưa về "
        "(đo 18/9/2026: cần 225px, chốt 232px để dư 7px cho chênh lệch phông giữa Windows và Linux)")
    assert 56 <= thu <= 64, f"bề rộng khi thu {thu}px ngoài khoảng 56–64px của §I.2"


def test_thu_tu_thanh_ngang_theo_ban_ve():
    """Bản vẽ 12/9: Logo → Đơn vị → Tìm kiếm → Công việc → Chờ duyệt → Trợ lý AI → chuông → Tài khoản.

    Canh bằng VỊ TRÍ TƯƠNG ĐỐI trong mã chứ không bằng toạ độ: thứ tự các thẻ trong JSX chính là
    thứ tự người dùng nhìn thấy, và đó là thứ đã bị xếp sai một lần rồi (chuông đứng trước Trợ lý AI).
    """
    src = _doc()
    i = src.index('<span className="bar">')
    bar = src[i:src.index('<div className="shell">', i)]
    moc = ("<ChonDonVi", 'className="o-tim', ">Công việc<", ">Chờ duyệt<", ">Trợ lý AI<",
           'd="chuong"', 'className="who"')
    vi = []
    for m in moc:
        assert m in bar, f"thanh ngang thiếu {m}"
        vi.append(bar.index(m))
    assert vi == sorted(vi), f"thứ tự thanh ngang sai so với bản vẽ – vị trí đang là {vi}, mốc {moc}"


def test_o_tim_kiem_gian_rong_chu_khong_chot_cung():
    """Bản vẽ cho ô tìm kiếm ăn hết chỗ trống giữa ô đơn vị và cụm nút (flex:1), không chốt 260px."""
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    m = re.search(r'\.top \.bar \.o-tim\{[^}]*\}', css)
    assert m, "không tìm thấy quy tắc .o-tim trong globals.css"
    luat = m.group(0)
    assert "flex:1" in luat, f"ô tìm kiếm phải giãn theo bản vẽ, đang là: {luat[:120]}"
    assert not re.search(r'[;{]width:\d+px', luat), f"ô tìm kiếm còn chốt cứng bề rộng: {luat[:120]}"


def test_thanh_ngang_khong_xuong_hai_dong_o_man_rong():
    """Đo trên trang thật 12/9 sau TC-11: thanh ngang cao 120px thay vì 72px.

    Nguyên nhân: ô đơn vị hai dòng dài 249px, cộng với logo thì vượt bề ngang, mà .top đang cho phép
    xuống dòng – cả cụm nút rơi xuống hàng hai. Ở màn rộng thanh ngang phải là MỘT hàng; dưới 900px
    mới cho xuống dòng, vì ở đó xuống dòng là đúng.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    for ten, mau in ((".top", r'\.top\{[^}]*\}'), (".top .bar", r'\.top \.bar\{[^}]*\}')):
        m = re.search(mau, css)
        assert m, f"không tìm thấy quy tắc {ten}"
        assert "flex-wrap:nowrap" in m.group(0), \
            f"{ten} phải là một hàng ở màn rộng, đang là: {m.group(0)[:130]}"
    # Ô đơn vị đã BỎ HẲN 12/9 (anh Tuấn: "xoá bỏ chữ Vietourist Holdings") – canh để không ai
    # dựng lại một ô chữ không bấm được ở chỗ ấy.
    assert "o-donvi" not in css, "ô đơn vị đã bỏ khỏi thanh ngang, không được dựng lại"


def test_o_don_vi_khong_ve_gi_khi_chua_co_duong_dan():
    """Anh Tuấn chốt 12/9: bỏ hẳn ô đơn vị khỏi thanh ngang.

    Chưa có /pham-vi/don-vi thì KHÔNG vẽ gì – không nút chết, không chữ thay thế. Một ô không bấm
    được thì không phải công cụ, chỉ là chữ chiếm chỗ.
    """
    tsx = open(os.path.join(ROOT, "web", "components", "ChonDonVi.tsx"), encoding="utf-8").read()
    # BÓC CHÚ THÍCH TRƯỚC. Chính đoạn chú thích giải thích "đã bỏ nút Chưa có nguồn" lại chứa đúng
    # chuỗi mình đang cấm – đọc cả chú thích thì phép thử đỏ vì lời giải thích của chính nó.
    khong_chu_thich = re.sub(r'/\*.*?\*/|//[^\n]*', '', tsx, flags=re.S)
    i = khong_chu_thich.index('kq?.tinh_trang === "chua_co_nguon"')
    nhanh = khong_chu_thich[i:khong_chu_thich.index('kq?.tinh_trang === "loi"')]
    assert "return null" in nhanh, "nhánh chưa có nguồn phải KHÔNG vẽ gì"
    assert "Chưa có nguồn · đơn vị" not in nhanh, "không dựng lại nút chết cũ"
    # Ô chọn THẬT vẫn phải rút gọn tên – thanh ngang chật, chín pháp nhân đều mở đầu "Công ty ..."
    assert "tenNgan(" in tsx, "ô chọn đơn vị phải rút gọn tên pháp nhân"
    src = open(os.path.join(ROOT, "web", "lib", "ten_don_vi.ts"), encoding="utf-8").read()
    assert "export function tenNgan" in src, "thiếu hàm rút gọn tên pháp nhân"


def test_chieu_cao_thanh_ngang_trong_dac_ta():
    """§I.2: thanh ngang cao 64–72px. Bản vẽ vẽ 76px – ngoài khoảng, nên lấy biên trên 72px.

    ══ ĐƠN VỊ ĐỔI 18/9/2026 (TC-67), KHOẢNG KHÔNG ĐỔI ═════════════════════════════════════════
    TRƯỚC:  `--top-h:72px` – một con số cứng.
    TỪ NAY: `--top-h:calc(72/14*1rem)` – cao 72px ở cỡ chữ gốc, và NỞ RA khi người dùng tăng cỡ.

    Vì sao buộc phải nở: thanh ngang đựng chữ. Chữ to lên mà cái thanh đứng nguyên 72px thì chữ bị
    cắt ngang – đúng yêu cầu mục 5 của anh Tuấn ("không được cắt chữ, không mất nút"). Đo thật ở
    TC-67: thanh cao 72 → 82 → 103px theo ba cỡ 14/16/20, không cắt chữ ở khổ nào.

    §I.2 NÓI VỀ CỠ GỐC, và phép thử đọc đúng tử số ấy. Ở cỡ 20 thanh cao 103px, vượt khoảng 64–72
    – và đó KHÔNG phải vi phạm: khoảng ấy đặt ra cho bố cục mặc định, còn 103px là kết quả của
    việc người dùng cố ý xin chữ to hơn. Ràng một người cần chữ lớn vào một cái thanh 72px là
    chọn con số trong đặc tả thay vì chọn người đọc được màn hình.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    # Nhận cả hai cách viết; nhánh `px` giữ lại để bắt được nếu ai đó gõ ngược trở lại số cứng.
    m = re.search(r'--top-h:\s*(?:calc\(\s*(\d+)\s*/\s*14\s*\*\s*1rem\s*\)|(\d+)px)', css)
    assert m, "không tìm thấy --top-h trong globals.css"
    cao = int(m.group(1) or m.group(2))
    assert 64 <= cao <= 72, f"thanh ngang {cao}px (ở cỡ chữ gốc) ngoài khoảng 64–72px của §I.2"


def test_thanh_phan_he_chi_co_mot_hanh_vi_la_bam():
    """Mỗi thanh phân hệ làm ĐÚNG MỘT việc: hoặc đi, hoặc xổ ra. Không có thanh nào làm cả hai.

    ══ LỊCH SỬ, ghi đủ để lần sau không ai đi vòng lại ═══════════════════════════════════════════
      · 12/9 sáng – bấm thì GHIM MỞ danh sách mục con ngay dưới thanh.
      · 12/9 chiều – rê chuột thì XỔ RA một bảng bên cạnh; bấm vẫn ghim mở.
      · 13/9 – bỏ cả hai. Bấm là ĐI TỚI trang phân hệ, hết.
      · 18/9 – anh Tuấn: "Kinh doanh: rê chuột vào xổ ra kinh doanh lẻ và kinh doanh đoàn, click
        chuột vào sẽ ra 2 màn hình riêng biệt" và "Điều hành: rê chuột vào sẽ xổ ra ĐH tour / ĐH xe
        và HDV, 3 phân hệ sẽ ra 3 màn hình giao diện khác nhau."

    ══ BÊN CŨ (13/9) — hai lý do bỏ rê chuột, CẢ HAI VẪN ĐÚNG ════════════════════════════════════
      (a) "Đưa chuột ngang qua thanh dọc để tới chỗ khác là bảng bật ra chắn đường."
      (b) "Máy bảng không có rê chuột nên một nửa người dùng chưa từng thấy nó."

    ══ BÊN MỚI (18/9) — vì sao vẫn quay lại, và hai lý do trên được trả lời thế nào ═══════════════
    Cái đổi không phải là ý thích, mà là SỰ THẬT VỀ TỔ CHỨC: Kinh doanh nay là hai phòng (lẻ và
    đoàn), Điều hành là ba đơn vị (tour · xe – đã sang pháp nhân Vietrip · hướng dẫn viên – hưởng
    lương ở công ty mẹ). Một thanh đại diện cho nhiều phòng thì "bấm là đi" đi đâu cũng sai một
    phòng. Sáu nhóm còn lại vẫn "bấm là đi" y nguyên 13/9.
      (a) trả lời bằng ĐỘ TRỄ MỞ 140ms: chuột lướt qua thì chưa kịp mở; chuột dừng lại mới là ý
          định. Bỏ độ trễ ấy là dựng lại đúng cái phiền đã khiến luật cũ bị bỏ – nên nó được canh.
      (b) trả lời bằng `hover: hover`: máy cảm ứng KHÔNG đi đường rê chuột, mà chạm lần 1 xổ ra,
          chạm lần 2 đi. Và dưới 900px thì bảng xổ ngay tại chỗ chứ không bay sang phải – bay sang
          phải trên màn 390px là bay hẳn ra ngoài màn hình (đo 18/9: bảng rơi vào toạ độ 388px).

    Bảng xổ ra lần này KHÁC hẳn bảng đã gỡ 13/9: nó không chứa mục lục bốn cấp của v1.3, chỉ chứa
    2 hoặc 3 lối vào phân hệ con. Mục lục đầy đủ vẫn nằm ở trang phân hệ, đúng như 13/9 đã chốt.
    """
    src_that = _doc()
    src = re.sub(r'/\*.*?\*/|//[^\n]*', '', src_that, flags=re.S)

    # Tàn dư của lối GHIM MỞ 12/9 thì vẫn phải sạch – lối ấy chưa bao giờ được dựng lại.
    for tan_du in ("moBay", "dongBay", "khoiMuc", 'className="bay"', "bay-tat-ca", "opened"):
        assert tan_du not in src, f"còn tàn dư của lối ghim mở đã bỏ: {tan_du}"
    css = re.sub(r'/\*.*?\*/', '', open(os.path.join(ROOT, "web", "app", "globals.css"),
                                          encoding="utf-8").read(), flags=re.S)
    assert ".bay" not in css, "luật CSS của bảng xổ ra kiểu cũ còn sống dù không ai vẽ nó nữa"

    # MỖI NHÓM ĐÚNG MỘT HÀNH VI. Nhóm không có `phans` thì vẫn là đường dẫn thật (bấm giữa chuột
    # mở được tab mới); nhóm có `phans` thì là <button>, vì một thẻ <a> không có đích là nói dối
    # với bàn phím và với trình đọc màn hình.
    assert "<Link href={g.href!}" in src_that, \
        "nhóm KHÔNG xổ ra phải là đường dẫn thật – bấm giữa chuột, mở tab mới"
    assert "g.phans" in src_that, "phải có nhánh vẽ riêng cho nhóm xổ ra"
    assert 'aria-haspopup="menu"' in src_that and "aria-expanded={mo}" in src_that, \
        "nút xổ ra phải tự khai là nút mở bảng, nếu không trình đọc màn hình xướng sai"

    # Hai lý do của bên cũ được canh thành hai khẳng định, không phải chỉ ghi trong chú thích.
    assert re.search(r"setTimeout\(\(\) => datMo\(true\), \d+\)", src), \
        "MỞ phải có độ trễ – chuột lướt qua mà bảng bật ra chắn đường là đúng cái đã khiến luật " \
        "13/9 bỏ rê chuột"
    assert '"(hover: hover)"' in src, \
        "phải hỏi máy có chuột thật không; màn cảm ứng vẫn bắn mouseenter giả sau cú chạm"


def test_nho_trang_thai_theo_tung_nguoi_dung():
    """§I.2: nhớ trạng thái THU/BUNG của thanh dọc THEO TỪNG NGƯỜI DÙNG.

    Một máy dùng chung (máy quầy, máy điều hành) mà nhớ theo máy thì trạng thái của người trước đè
    lên người sau – và người sau tưởng menu hỏng.

    KHOA_MENU (nhóm nào đang ghim mở) đã bỏ ngày 13/9 cùng với lối ghim mở: bấm thanh phân hệ giờ
    là ĐI TỚI trang phân hệ, không còn trạng thái mở/đóng nào để nhớ.
    """
    src = _doc()
    assert "${KHOA_THU}_${u.username}" in src or "${KHOA_THU}_${user.username}" in src, \
        "KHOA_THU phải gắn tên đăng nhập vào khoá lưu, không lưu chung cho cả máy"
    assert "KHOA_MENU" not in re.sub(r'/\*.*?\*/|//[^\n]*', '', src, flags=re.S), \
        "KHOA_MENU là tàn dư của lối ghim mở đã bỏ – còn mã sống thì sớm muộn có người dùng lại"


def test_tong_quan_khong_con_muc_con_va_bam_thang_ve_trang_chu():
    """Anh Tuấn chốt 12/9 (chiều): "bỏ Bảng điều hành, không hiện lên ở thanh dọc này".

    Mục con cũ trỏ "/" – đúng trang mà chính thanh "Tổng quan" đại diện – nên nó chỉ là một dòng
    lặp lại tên nhóm. Bỏ mục con thì PHẢI có `href` thay thế, nếu không nhóm rỗng bị bộ lọc quyền
    loại khỏi menu và người dùng mất hẳn đường về bảng điều hành.
    """
    src = _doc()
    m = re.search(r'\{\s*key:\s*"tongquan".*?\n\s*\},', src, re.S)
    assert m, "không tìm thấy khai báo nhóm tongquan"
    khoi = m.group(0)
    assert "Bảng điều hành" not in khoi, "mục con 'Bảng điều hành' phải được bỏ khỏi nhóm Tổng quan"
    assert re.search(r'href:\s*"/"', khoi), "nhóm Tổng quan bỏ mục con thì phải có href:\"/\" để bấm thẳng"
    assert re.search(r'blocks:\s*\[\s*\]', khoi), "nhóm Tổng quan phải còn blocks rỗng, không mục con nào"
    # Nhóm Tổng quan không còn mục con nên dem == 0. Từ 13/9 không còn bộ lọc nào loại nhóm theo
    # dem nữa (tám phân hệ hiện đủ với mọi vai trò), nên chỉ cần canh rằng bộ lọc ấy không quay lại.
    assert "g.dem > 0 : duoc(g.href)" not in src, \
        "bộ lọc theo dem đã quay lại – nhóm Tổng quan (dem == 0) sẽ biến mất khỏi menu"
    # ══ TC-69 · 18/9/2026 — LUẬT NÀY ĐÃ BỊ ĐẢO, ghi cả hai bên ═══════════════════════════════
    # BÊN CŨ (12/9/2026): "Không mục con thì không vẽ mũi tên xổ – một mũi tên mở ra khoảng trắng
    #   là lời hứa suông." Khẳng định cũ là `g.dem > 0 && <span className="grp-mui"` PHẢI có mặt.
    # BÊN MỚI (18/9/2026): anh Tuấn bảo "bỏ đường gạch dưới chữ, mũi tên của 8 phân hệ này". Mũi
    #   tên bỏ hẳn cho MỌI nhóm, nên câu hỏi "có mục con hay không" không còn quyết định gì nữa.
    #
    # LÝ DO CŨ VẪN ĐÚNG, CHỈ LÀ KHÔNG CÒN ÁP DỤNG: nếu mai kia ai dựng lại mũi tên, thì nó vẫn
    # phải phụ thuộc `dem` chứ không được vẽ cho mọi nhóm. Nên khẳng định lật thành: mũi tên đã bỏ,
    # và nếu quay lại thì phải quay lại ĐÚNG cách cũ.
    assert 'className="grp-mui"' not in src, (
        "mũi tên đã bỏ 18/9/2026. Nếu dựng lại thì phải kèm điều kiện `g.dem > 0` như bản 12/9 — "
        "vẽ mũi tên cho nhóm không có mục con là mở ra một khoảng trắng.")


def test_khoi_logo_noi_len_khoi_thanh_ngang():
    """Anh Tuấn chốt 12/9 (chiều): "mở rộng khung logo hơn và làm cho nền nổi lên cao hơn".

    Đo tại chỗ sau khi sửa: khối logo 224×55px, thanh ngang vẫn 72px (đệm dọc .top phải giảm còn
    8px, vì 12+55+12 = 79px là vượt khoảng 64–72px của §I.2). Phép thử canh đúng phép tính ấy –
    ai nới đệm hay nới khung mà quên đo lại thanh ngang thì đỏ ở đây, không đỏ ngoài trang thật.
    """
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    m = re.search(r'\.top\{[^}]*\}', css)
    assert m, "không tìm thấy quy tắc .top"
    dem = re.search(r'padding:(\d+)px', m.group(0))
    assert dem, "không đọc được đệm dọc của .top"
    b = re.search(r'\.top \.brand\{[^}]*\}', css)
    assert b, "không tìm thấy quy tắc .top .brand"
    kb = b.group(0)
    mb = re.search(r'padding:(\d+)px (\d+)px', kb)
    assert mb, "không đọc được đệm của khối logo"
    assert int(mb.group(2)) >= 24, f"khung logo rộng {mb.group(2)}px mỗi bên – anh Tuấn yêu cầu mở rộng hơn"
    assert "box-shadow" in kb, "nền logo phải có bóng đổ thì mới nổi lên khỏi thanh navy"
    assert "inset 0 1px 0" in kb, "thiếu vệt sáng mép trên – khối phẳng lì thì không ra chiều cao"
    logo = re.search(r'\.brand-logo\{height:(\d+)px', css) or re.search(r'\.brand \.brand-logo\{height:(\d+)px', css)
    cao_logo = int(logo.group(1)) if logo else 28
    cao_khoi = int(dem.group(1)) * 0 + 2 * int(mb.group(1)) + cao_logo + 3 + 10 + 2  # viền 1px hai bên
    cao_thanh = 2 * int(dem.group(1)) + cao_khoi
    assert cao_thanh <= 72, (
        f"khối logo {cao_khoi}px + đệm {dem.group(1)}px hai đầu = thanh ngang {cao_thanh}px, "
        "vượt khoảng 64–72px của §I.2 – giảm đệm .top hoặc thu khối logo lại")


def test_globals_css_can_bang_ngoac():
    """Một dấu } thừa làm HỎNG IM LẶNG toàn bộ phần CSS phía sau nó.

    Chuyện thật, 13/9/2026: gỡ luật .bay bằng biểu thức chính quy, dòng đầu của một luật nhiều dòng
    bị xoá còn dòng cuối "…font-weight:600}" ở lại. Dấu } lạc ấy đóng sớm một khối, và MỌI luật viết
    sau đó – cả khối màn hình 01 vừa thêm – ngừng có tác dụng. Trình duyệt không báo gì, phép thử
    cũng không, chỉ có trang là trông sai. Đếm ngoặc là phép thử rẻ nhất bắt được đúng chuyện đó.
    """
    css = re.sub(r'/\*.*?\*/', '', open(os.path.join(ROOT, "web", "app", "globals.css"),
                                        encoding="utf-8").read(), flags=re.S)
    sau = 0
    for so_dong, dong in enumerate(css.split("\n"), 1):
        for ch in dong:
            if ch == "{":
                sau += 1
            elif ch == "}":
                sau -= 1
                assert sau >= 0, f"globals.css dòng {so_dong}: dấu }} thừa – mọi luật phía sau mất tác dụng"
    assert sau == 0, f"globals.css còn {sau} dấu {{ chưa đóng – phần cuối tệp không được áp dụng"
