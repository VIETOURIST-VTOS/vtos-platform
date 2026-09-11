"""TC-1 · Nút chọn đơn vị: canh bốn ràng buộc mà lệnh giao việc đặt ra.

Nút chọn đơn vị trông như một việc giao diện. Nó không phải: bốn chỗ dưới đây, làm sai chỗ nào cũng
biến nó thành một lỗ quyền hoặc một chỗ mất việc của người dùng. Bốn chỗ ấy nằm ở mã GIAO DIỆN nên
không bộ kiểm máy chủ nào với tới – vì vậy có tệp này, đọc thẳng mã .tsx.

  Q1  quyền kiểm tại MÁY CHỦ – trình duyệt không tự lọc danh sách đơn vị theo vai trò
  Q2  đúng hai đường dẫn của hợp đồng, không có đường thứ ba
  Q3  không gửi company_id kèm từng truy vấn dữ liệu
  Q4  còn dữ liệu chưa lưu thì HỎI TRƯỚC khi đổi, không hỏi sau
  Q5  "Toàn công ty" gửi null, trình duyệt không tự cộng
  Q6  dữ liệu giả phải có cờ bật và có dải cảnh báo nhìn thấy được

Q6 sinh từ ranh giới Chủ tịch 09/9/2026: robot viết cấu trúc, không nhập SỐ LIỆU. Một danh sách đơn
vị bịa ra nằm im trên màn hình là số liệu giả – ai chụp màn hình gửi đi thì nó thành số liệu thật.
Cờ làm nó không tự xuất hiện; dải cảnh báo làm nó không thể bị nhầm.
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


def test_q3_khong_gui_company_id_kem_tung_truy_van():
    """Đổi đơn vị là MỘT lần PUT; từ đó máy chủ tự đọc phạm vi từ phiên.

    Nếu mỗi truy vấn mang theo mã đơn vị và máy chủ tin nó, thì sửa một con số trên đường dẫn là
    xem được công ty khác. Đây đúng là lý do làn Phân quyền đặt ràng buộc ấy.
    """
    ma = _bo_chu_thich(_doc(NUT)) + _bo_chu_thich(_doc(LIB))
    for xau in ("company_id=", "?company_id", "&company_id"):
        assert xau not in ma, f"có chỗ gắn '{xau}' vào truy vấn – phạm vi phải đọc từ phiên ở máy chủ"
    # company_id chỉ được xuất hiện đúng một chỗ: thân của lệnh PUT.
    # Đếm trên MÃ đã bỏ chú thích: phần giải thích ở đầu tệp nhắc tên company_id đúng để nói vì sao
    # không được gửi nó kèm truy vấn.
    assert _bo_chu_thich(_doc(LIB)).count("company_id") <= 3, \
        "company_id xuất hiện nhiều hơn mức cần cho thân lệnh PUT – kiểm lại xem có chỗ nào gửi kèm truy vấn"


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

def test_q5_toan_cong_ty_gui_null_va_trinh_duyet_khong_tu_cong():
    """"Toàn công ty gồm đơn vị trực thuộc" là việc gom của MÁY CHỦ theo cây parent_id.

    Trình duyệt cộng hộ là chỗ đẻ ra cộng trùng, và cộng trùng trong một bảng tiền thì không ai
    nhìn ra bằng mắt.
    """
    ma = _doc(NUT)
    assert re.search(r'chon\(null,\s*"Toàn công ty"\)', ma), '"Toàn công ty" phải gửi null'
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


def test_q6b_chua_co_nguon_thi_noi_ra_kem_bo_phan_chiu_trach_nhiem():
    """Ranh giới 09/9: chưa có cửa thì ghi "Chưa có nguồn" kèm bộ phận chịu – KHÔNG hiện 0, không đoán."""
    lib, nut = _doc(LIB), _doc(NUT)
    assert "chua_co_nguon" in lib and "chua_co_nguon" in nut, \
        "phải phân biệt 'máy chủ chưa dựng đường dẫn' với 'lỗi thật'"
    assert "Chưa có nguồn" in nut, "phải hiện đúng chữ 'Chưa có nguồn' theo ranh giới 09/9"
    assert "bo_phan" in nut, "phải nêu bộ phận chịu trách nhiệm, không chỉ nói là thiếu"


def test_q7_nut_chon_da_thay_o_select_bi_khoa_cu():
    sh = _doc(SHELL)
    assert "<ChonDonVi" in sh, "Shell phải gắn nút chọn đơn vị thật"
    assert "Chọn công ty / đơn vị – sắp có" not in sh, "ô select bị khoá cũ phải được gỡ"
