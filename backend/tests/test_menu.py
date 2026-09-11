"""Menu nhóm nghiệp vụ – bảy nhóm theo v1.1 §I.2 "Menu trái rút gọn" (bản duyệt 11/9/2026).

Chốt chặn KỸ THUẬT, không đổi theo chỉ đạo nào: mọi màn hình có trong ma trận phân quyền phải nằm
trong một nhóm menu, nếu không người dùng không còn lối vào; và ngược lại, menu không được trỏ tới
đường dẫn không tồn tại.

Phần khẳng định SỐ NHÓM và TÊN NHÓM là ĐẶC TẢ tổ chức, thay đổi theo chỉ đạo. Lịch sử:
  06/9  8 nhóm theo bản đề xuất đầu tiên.
  07/9  10 nhóm: "Kinh doanh & Sản phẩm" tách đôi; xe và HDV rời "Điều hành".
        rồi 11 nhóm: thêm "Tài khoản của tôi" cho màn hình đổi mật khẩu.
  11/9  7 nhóm theo v1.1 §I.2: hai cấp, bỏ số thứ tự, Quản trị đặt cuối, ẩn mục chưa có trang.

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

# Tên bảy nhóm theo v1.1 §I.2, ĐÚNG THỨ TỰ. Quản trị đặt cuối.
BAY_NHOM = ("Tổng quan", "Khách hàng & Kinh doanh", "Vận hành", "Tài chính",
            "Nhân sự & Nội bộ", "Báo cáo", "Quản trị")


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

def test_du_bay_nhom_dung_ten_va_dung_thu_tu():
    _, block = menu_paths()
    keys = re.findall(r'key:\s*"([a-z_]+)"', block)
    assert len(keys) == 7 and len(set(keys)) == 7, f"v1.1 §I.2 yêu cầu đúng 7 nhóm, đang có {keys}"
    ten_nhom = re.findall(r'key:\s*"[a-z_]+",\s*label:\s*"([^"]+)"', block)
    assert tuple(ten_nhom) == BAY_NHOM, \
        f"tên hoặc thứ tự nhóm sai.\n  đang có : {ten_nhom}\n  phải là : {list(BAY_NHOM)}"
    assert ten_nhom[-1] == "Quản trị", "v1.1 §I.2: nhóm Quản trị phải đặt CUỐI"


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
    icons = re.findall(r'key:\s*"[a-z_]+",\s*label:\s*"[^"]+",\s*icon:\s*"([^"]+)"', block)
    assert len(icons) == 7, f"phải đủ 7 biểu tượng cho 7 nhóm, đang có {len(icons)}: {icons}"
    assert all(i.strip() for i in icons), f"có biểu tượng rỗng: {icons}"
    # Nhãn nhóm phải đi vào title và aria-label, không được mất khi thu.
    assert 'title={g.label}' in src and 'aria-label={g.label}' in src, \
        "nút nhóm phải mang title và aria-label bằng nhãn nhóm – đó là 'chú thích' của biểu tượng"


def test_be_rong_thanh_doc_dung_dac_ta():
    """§I.2 cho một khoảng, không cho một con số: rộng 224–240px, thu còn 56–64px."""
    css = open(os.path.join(ROOT, "web", "app", "globals.css"), encoding="utf-8").read()
    m_rong = re.search(r'aside\.side\{flex:0 0 (\d+)px', css)
    m_thu = re.search(r'aside\.side\.thu\{flex:0 0 (\d+)px', css)
    assert m_rong, "không tìm thấy bề rộng thanh dọc trong globals.css"
    assert m_thu, "không tìm thấy bề rộng khi THU trong globals.css"
    rong, thu = int(m_rong.group(1)), int(m_thu.group(1))
    assert 224 <= rong <= 240, f"bề rộng {rong}px ngoài khoảng 224–240px của §I.2"
    assert 56 <= thu <= 64, f"bề rộng khi thu {thu}px ngoài khoảng 56–64px của §I.2"


def test_nho_trang_thai_theo_tung_nguoi_dung():
    """§I.2: nhớ trạng thái mở/thu THEO TỪNG NGƯỜI DÙNG.

    Một máy dùng chung (máy quầy, máy điều hành) mà nhớ theo máy thì trạng thái của người trước đè
    lên người sau – và người sau tưởng menu hỏng.
    """
    src = _doc()
    for khoa in ("KHOA_MENU", "KHOA_THU"):
        assert f"${{{khoa}}}_${{u.username}}" in src or f"${{{khoa}}}_${{user.username}}" in src, \
            f"{khoa} phải gắn tên đăng nhập vào khoá lưu, không lưu chung cho cả máy"
