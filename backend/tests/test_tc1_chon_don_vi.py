"""TC-1 · Nút chọn đơn vị: canh những ràng buộc mà lệnh giao việc đặt ra.

Nút chọn đơn vị trông như một việc giao diện. Nó không phải: mỗi chỗ dưới đây làm sai là biến nó
thành một lỗ quyền hoặc một chỗ mất việc của người dùng. Những chỗ ấy nằm ở mã GIAO DIỆN nên không
bộ kiểm máy chủ nào với tới – vì vậy có tệp này, đọc thẳng mã .tsx.

  Q1  quyền kiểm tại MÁY CHỦ – trình duyệt không tự lọc danh sách đơn vị theo vai trò
  Q2  đúng hai đường dẫn của hợp đồng, không có đường thứ ba
  Q3  không gửi mã đơn vị kèm từng truy vấn dữ liệu
  Q4  còn dữ liệu chưa lưu thì HỎI TRƯỚC khi đổi, không hỏi sau
  Q5  "Toàn công ty" là một KIỂU gửi lên máy chủ, trình duyệt không tự cộng
  Q6  dữ liệu giả phải có cờ bật và có dải cảnh báo nhìn thấy được
  Q8  ba kiểu lựa chọn của máy chủ đều có mặt, kể cả "chưa xác định pháp nhân"
  Q9  máy chủ chưa lưu được lựa chọn thì màn hình không hứa là đã nhớ

Q6 sinh từ ranh giới Chủ tịch 09/9/2026: robot viết cấu trúc, không nhập SỐ LIỆU. Một danh sách đơn
vị bịa ra nằm im trên màn hình là số liệu giả – ai chụp màn hình gửi đi thì nó thành số liệu thật.
Cờ làm nó không tự xuất hiện; dải cảnh báo làm nó không thể bị nhầm.

Q8 và Q9 sinh ngày 11/9 khi đọc `app/services/pham_vi_dang_xem.py`: mã máy chủ dựng lựa chọn thành
BA kiểu, còn thư giao hợp đồng chỉ nói `{ company_id }`. Một mình company_id không phân biệt được
"toàn phạm vi" với "hồ sơ chưa gán pháp nhân" – cùng là null, ra hai danh sách khác hẳn nhau.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")
NUT = os.path.join(WEB, "components", "ChonDonVi.tsx")
LIB = os.path.join(WEB, "lib", "phamvi.ts")
SHELL = os.path.join(WEB, "components", "Shell.tsx")

# Hợp đồng làn Phân quyền chốt 11/9/2026. Đổi hai dòng này là đổi hợp đồng – phải bàn với họ trước.
DUONG_DAN_DOC = "/api/v1/pham-vi/don-vi"
DUONG_DAN_DAT = "/api/v1/pham-vi/dang-xem"

# Ba kiểu lấy nguyên tên chuỗi của `pham_vi_dang_xem.CAC_KIEU`. Trình duyệt và máy chủ phải gọi
# cùng một tên, nếu không thì máy chủ trả 422 "kiểu không có trong hệ thống" mà không ai hiểu vì sao.
CAC_KIEU = ("toan_pham_vi", "don_vi", "chua_xac_dinh")


def _doc(p: str) -> str:
    assert os.path.exists(p), f"thiếu tệp {os.path.relpath(p, ROOT)}"
    return open(p, encoding="utf-8").read()


def _bo_chu_thich(src: str) -> str:
    """Bỏ chú thích trước khi soi mã: chú thích của tệp này NHẮC TÊN đúng những thứ bị cấm, nên soi
    cả chú thích thì phép thử tự đỏ vì chính lời giải thích vì sao nó phải xanh."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


# ------------------------------------------------------------------ Q1

def test_q1_trinh_duyet_khong_tu_loc_don_vi_theo_vai_tro():
    """Danh sách vẽ ra là danh sách máy chủ ĐÃ lọc. Lọc thêm ở trình duyệt nghĩa là dữ liệu đã rời
    máy chủ rồi mới bị giấu đi – đó là rò, không phải phân quyền."""
    ma = _bo_chu_thich(_doc(NUT)) + _bo_chu_thich(_doc(LIB))
    # KHÔNG cấm chữ "role" trơn: role="listbox" là thuộc tính trợ năng của HTML, không dính gì tới
    # phân quyền. Cấm nhầm nó thì phép thử buộc người viết bỏ trợ năng đi để làm xanh – đắt hơn
    # nhiều so với chỗ nó canh được.
    for cam in ("hidden_menus", "MENU_ROLES", "vai_tro", "TOAN_TAP_DOAN", "u.role", "user.role"):
        assert cam not in ma, (
            f"mã nút chọn đơn vị nhắc tới '{cam}' – nó đang tự quyết quyền ở trình duyệt. "
            f"Quyền kiểm tại máy chủ; ở đây chỉ vẽ lại danh sách nhận được.")


# ------------------------------------------------------------------ Q2, Q3

def test_q2_dung_dung_hai_duong_dan_cua_hop_dong():
    lib = _doc(LIB)
    assert DUONG_DAN_DOC in lib, f"thiếu đường dẫn đọc {DUONG_DAN_DOC}"
    assert DUONG_DAN_DAT in lib, f"thiếu đường dẫn đặt {DUONG_DAN_DAT}"
    # Không có đường thứ ba dưới tiền tố pham-vi: hợp đồng chỉ có hai.
    duong = set(re.findall(r'"(/api/v1/pham-vi[^"]*)"', lib))
    thua = duong - {DUONG_DAN_DOC, DUONG_DAN_DAT}
    assert not thua, f"gọi đường dẫn ngoài hợp đồng: {sorted(thua)}"
    # PUT chứ không phải POST – đặt phạm vi là thay thế một giá trị, không phải tạo thêm bản ghi.
    assert 'method: "PUT"' in lib, "đặt đơn vị đang xem phải dùng PUT theo hợp đồng"


def test_q3_moi_lan_goi_may_chu_deu_di_qua_hai_hang_so_duong_dan():
    """Đổi đơn vị là MỘT lần PUT; từ đó máy chủ tự đọc phạm vi từ phiên.

    Nếu mỗi truy vấn mang theo mã đơn vị và máy chủ tin nó, thì sửa một con số trên đường dẫn là
    xem được công ty khác. Đây đúng là lý do làn Phân quyền đặt ràng buộc ấy.

    Cách canh: KHÔNG đếm số lần chữ company_id xuất hiện – nó là tên trường của cây đơn vị nên đếm
    kiểu ấy chỉ đo được độ dài tệp. Canh đúng chỗ có nghĩa: mọi lời gọi fetch phải lấy đường dẫn từ
    một trong hai hằng số, không có đường nào ghép chuỗi tại chỗ.
    """
    ma = _bo_chu_thich(_doc(NUT)) + _bo_chu_thich(_doc(LIB))
    for xau in ("company_id=", "?company_id", "&company_id", "don_vi_id=", "?cid", "&cid"):
        assert xau not in ma, f"có chỗ gắn '{xau}' vào truy vấn – phạm vi phải đọc từ phiên ở máy chủ"
    goi = re.findall(r"fetch\(\s*([^,\s)]+)", _bo_chu_thich(_doc(LIB)))
    assert goi, "không tìm thấy lời gọi fetch nào trong lớp gọi máy chủ"
    la = [g for g in goi if g not in ("DUONG_DAN", "DUONG_DAN_DAT")]
    assert not la, f"fetch tới đường dẫn ghép tại chỗ: {la} – phải dùng đúng hai hằng số của hợp đồng"
    # Nút chọn KHÔNG tự gọi máy chủ: mọi đường ra ngoài đi qua lib, nơi có hai hằng số ấy.
    assert "fetch(" not in _bo_chu_thich(_doc(NUT)), \
        "nút chọn tự gọi fetch – mọi lời gọi phải đi qua lib/phamvi.ts để còn canh được đường dẫn"


# ------------------------------------------------------------------ Q4

def test_q4_hoi_truoc_khi_doi_chu_khong_hoi_sau():
    """Thứ tự ở đây là toàn bộ giá trị của ràng buộc: hỏi SAU khi đã đổi thì việc đã mất rồi."""
    ma = _doc(NUT)
    assert "chuaLuu" in ma and "confirm(" in ma, "thiếu cửa hỏi khi còn dữ liệu chưa lưu"
    i_hoi = ma.index("confirm(")
    i_dat = ma.index("datDangXem(")
    assert i_hoi < i_dat, (
        "cửa hỏi nằm SAU lệnh đổi phạm vi – phải hỏi trước, vì hỏi sau thì phần đang gõ dở đã mất")
    # Người dùng trả lời "không" thì phải dừng hẳn, không đi tiếp.
    assert re.search(r"if\s*\(!ok\)\s*return;", ma), \
        "trả lời 'không' phải dừng hẳn việc đổi đơn vị"


def test_q4b_khung_co_so_ghi_chua_luu_cho_man_hinh_dung():
    """Cửa hỏi chỉ có nghĩa khi màn hình nhập báo được rằng mình đang gõ dở."""
    sh = _doc(SHELL)
    assert "datChuaLuu" in sh, "Shell phải cung cấp datChuaLuu cho màn hình có biểu nhập gọi"
    assert "chuaLuu={" in sh, "Shell phải truyền cờ chưa-lưu xuống nút chọn đơn vị"


# ------------------------------------------------------------------ Q5

def test_q5_toan_cong_ty_gui_len_may_chu_va_trinh_duyet_khong_tu_cong():
    """"Toàn công ty gồm đơn vị trực thuộc" là việc gom của MÁY CHỦ theo cây parent_id.

    Trình duyệt cộng hộ là chỗ đẻ ra cộng trùng, và cộng trùng trong một bảng tiền thì không ai
    nhìn ra bằng mắt.
    """
    ma = _doc(NUT)
    assert re.search(r'"Toàn công ty",\s*TOAN_PHAM_VI,\s*null', ma), \
        '"Toàn công ty" phải gửi kiểu toan_pham_vi kèm mã đơn vị rỗng'
    than = _bo_chu_thich(ma)
    for cam in ("reduce(", ".sum", "tong +=", "cong +="):
        assert cam not in than, f"nút chọn đơn vị có phép cộng ('{cam}') – việc gom là của máy chủ"


# ------------------------------------------------------------------ Q6

def test_q6_du_lieu_gia_phai_co_co_bat_va_dai_canh_bao():
    lib, nut = _doc(LIB), _doc(NUT)
    assert "giaLapDonVi" in lib, "dữ liệu giả phải nằm sau một cờ bật, không tự xuất hiện"
    assert 'get("giaLapDonVi") === "1"' in lib, "cờ phải bật bằng tham số rõ ràng trên đường dẫn"
    assert "GIẢ LẬP" in nut, "bật cờ thì phải có dải cảnh báo nhìn thấy được trên màn hình"
    # Tên đơn vị giả phải tự mang nhãn, phòng khi ai đó chụp riêng một dòng.
    gia = re.findall(r'ten:\s*"([^"]*)"', lib)
    assert gia, "không tìm thấy cây đơn vị giả để kiểm nhãn"
    xau = [t for t in gia if "GIẢ LẬP" not in t]
    assert not xau, f"đơn vị giả thiếu nhãn trong chính tên: {xau}"


def test_q6b_chua_co_nguon_thi_khong_ve_gi_tren_thanh_ngang():
    """ĐỔI 12/9/2026 – anh Tuấn chốt: "xoá bỏ chữ Vietourist Holdings".

    BẢN CŨ của phép thử này đòi nút hiện chữ "Chưa có nguồn" kèm tên bộ phận chịu, theo ranh giới
    09/9 ("chưa có cửa thì nói ra, không hiện 0, không đoán"). Ranh giới ấy KHÔNG BỎ – nó vẫn áp cho
    mọi CON SỐ trên mọi màn hình, và các phép thử khác vẫn canh.

    Nhưng ô đơn vị trên thanh ngang không phải một con số: nó là một ô để ĐỔI đơn vị. Chưa có
    /pham-vi/don-vi thì không đổi được gì, nên ô ấy chỉ còn là chữ chiếm chỗ – mà điều nó nói (đang
    ở Holdings) thì logo bên trái đã nói rồi. Anh Tuấn xem trang thật và yêu cầu bỏ hẳn.

    Nay canh chiều ngược lại: KHÔNG vẽ gì, và không ai dựng lại nút chết ấy.
    """
    lib, nut = _doc(LIB), _doc(NUT)
    assert "chua_co_nguon" in lib and "chua_co_nguon" in nut, \
        "vẫn phải phân biệt 'máy chủ chưa dựng đường dẫn' với 'lỗi thật' – hai đường xử lý khác nhau"
    # Bóc chú thích trước: chính đoạn chú thích giải thích việc bỏ nút lại nhắc đúng chữ đang cấm.
    than = re.sub(r'/\*.*?\*/|//[^\n]*', '', nut, flags=re.S)
    i = than.index('kq?.tinh_trang === "chua_co_nguon"')
    nhanh = than[i:than.index('kq?.tinh_trang === "loi"')]
    assert "return null" in nhanh, "nhánh chưa có nguồn phải KHÔNG vẽ gì lên thanh ngang"
    assert "Chưa có nguồn" not in nhanh, "không dựng lại nút chết 'Chưa có nguồn · đơn vị'"
    # Nhánh LỖI THẬT thì vẫn phải nói ra – im lặng khi hỏng là chỗ người dùng tưởng hệ thống ổn.
    assert "Không đọc được đơn vị" in nut, "lỗi thật vẫn phải hiện, chỉ 'chưa dựng' mới im lặng"


def test_q7_nut_chon_da_thay_o_select_bi_khoa_cu():
    sh = _doc(SHELL)
    assert "<ChonDonVi" in sh, "Shell phải gắn nút chọn đơn vị thật"
    assert "Chọn công ty / đơn vị – sắp có" not in sh, "ô select bị khoá cũ phải được gỡ"


# ------------------------------------------------------------------ Q8

def test_q8_du_ba_kieu_lua_chon_va_dung_ten_cua_may_chu():
    """`chua_xac_dinh` là mục dễ rơi nhất, vì nó không phải một đơn vị nên không nằm trong cây.

    Rơi nó đi thì hồ sơ chưa gán pháp nhân lại lẫn vào danh sách chung y như trước – không ai đếm
    được, nên không ai sửa. Máy chủ đã tách nó ra thành một kiểu riêng; giao diện phải có cửa vào.
    """
    lib, nut = _doc(LIB), _doc(NUT)
    for k in CAC_KIEU:
        assert f'"{k}"' in lib, f"thiếu kiểu '{k}' – tên chuỗi phải trùng CAC_KIEU của máy chủ"
    assert "CHUA_XAC_DINH" in nut, "nút chọn thiếu mục hồ sơ chưa gán pháp nhân"
    assert "Chưa xác định pháp nhân" in nut, "mục chưa gán pháp nhân phải có chữ người đọc hiểu"
    # Thân lệnh PUT mang kiểu, không chỉ mang mã đơn vị: một mình mã không nói được kiểu thứ ba.
    assert re.search(r"JSON\.stringify\(\{\s*kieu", lib), \
        "thân lệnh đặt phạm vi phải mang `kieu` – null của toan_pham_vi và của chua_xac_dinh khác nhau"


def test_q8b_ten_truong_cua_cay_don_vi_trung_voi_may_chu():
    """`cay()` trả về company_id/ten/ma/loai/hoat_dong/cap/con. Đặt tên khác ở trình duyệt thì màn
    hình trắng trơn vào đúng ngày làn Phân quyền bật đường dẫn lên – và không có lỗi nào hiện ra."""
    lib = _doc(LIB)
    kh = re.search(r"export type DonVi = \{(.*?)\n\};", lib, re.S)
    assert kh, "không tìm thấy kiểu DonVi"
    than = kh.group(1)
    for truong in ("company_id", "ten", "ma", "con"):
        assert re.search(rf"\b{truong}\??:", than), f"kiểu DonVi thiếu trường '{truong}' của máy chủ"


# ------------------------------------------------------------------ Q9

def test_q9_khong_hua_da_nho_khi_may_chu_chua_luu_duoc():
    """`KHO_LUU is None` hôm nay: máy chủ nhận lựa chọn nhưng KHÔNG giữ qua lần đăng nhập sau.

    `doc_chon()` nói thẳng điều ấy bằng `luu_tru="chua_co"` và nói để màn hình dùng. Không đọc cờ
    ấy thì nút chọn im lặng hứa một thứ máy chủ chưa giữ được – người dùng phát hiện vào hôm sau,
    khi mở máy lên thấy mình đang xem đơn vị khác.
    """
    nut = _doc(NUT)
    assert "luu_tru" in nut, "nút chọn phải đọc cờ luu_tru của máy chủ"
    assert re.search(r'luu_tru\s*===\s*"chua_co"', nut), \
        'phải xử riêng trường hợp luu_tru === "chua_co"'
    assert "đăng nhập lại" in nut, "phải nói thẳng rằng đăng nhập lại sẽ trở về mặc định"


def test_q9b_lua_chon_cu_ngoai_pham_vi_thi_noi_ra():
    """Người vừa bị thu quyền: máy chủ bỏ lựa chọn cũ và đưa về mặc định. Im lặng làm việc ấy thì
    họ tưởng mình vẫn đang xem đơn vị hôm qua, và đọc một bảng số của phạm vi khác."""
    nut = _doc(NUT)
    assert "ve_mac_dinh" in nut, "nút chọn phải đọc cờ ve_mac_dinh của máy chủ"
    assert "ra ngoài phạm vi" in nut, "phải nói rõ vì sao lựa chọn cũ bị bỏ"
