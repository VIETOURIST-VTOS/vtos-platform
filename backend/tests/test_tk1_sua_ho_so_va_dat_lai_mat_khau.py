"""TK-1 · Hai cửa máy chủ ĐÃ CÓ mà không màn hình nào gọi tới — 12/10/2026.

Chủ tịch đăng nhập bằng vai CNTT, vào Quản trị hệ thống → Tài khoản, và không tìm thấy nút nào để
sửa thông tin nhân viên hay đặt lại mật khẩu cho họ.

ĐO RA: không phải thiếu QUYỀN, mà thiếu CÁI NÚT.
  · `POST /users/{uid}/reset-password` có thật, `require_roles(*HR_WRITE)` tức hcns + cntt, đặt
    xong bắt đổi ở lần đăng nhập kế tiếp, có ghi nhật ký. Quét cả thư mục `web/`: KHÔNG một màn
    hình nào gọi nó. Thứ duy nhất đang có là nút "Nạp + đặt lại mật khẩu = mã NV" đặt lại cho CẢ
    danh sách — không ai dám bấm để giúp một người, nên không ai được giúp.
  · `PUT /employees/{eid}` nhận đủ mọi trường, kiểm phiên bản, tự ghi lịch sử điều chuyển. Màn
    hình chỉ gọi nó đúng một kiểu: {họ tên, phòng, active} để bấm Ngưng / Mở lại. Có biểu TẠO,
    không có biểu SỬA.

"Cửa mở mà người không với tới thì cửa ấy chưa tồn tại" — câu kho này đã ghi ngày 09/9/2026 cho
nhóm `/api/v1/tong-dai`. Bộ kiểm này canh để hai cửa ấy không rơi lại vào tình trạng cũ.
"""
import os, re

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACCESS = os.path.join(GOC, "web", "app", "access", "page.tsx")
HRS = os.path.join(GOC, "web", "components", "HrScreens.tsx")
HRPY = os.path.join(GOC, "backend", "app", "api", "v1", "hr.py")


def _doc(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


# ═══════════════════════ A · ĐẶT LẠI MẬT KHẨU ═══════════════════════
def test_man_hinh_tai_khoan_co_nut_dat_lai_mat_khau():
    s = _doc(ACCESS)
    assert "reset-password" in s, (
        "màn hình Tài khoản không gọi cửa đặt lại mật khẩu — CNTT lại không có đường giúp một "
        "người quên mật khẩu, ngoài nút đặt lại cho CẢ danh sách ở màn hình Nhân sự")


def test_vai_thay_nut_dat_lai_mk_khop_dung_vai_may_chu_cho_phep():
    """LUẬT CHÍNH CỦA BỘ NÀY, và nó canh hai chiều.

    Màn hình hiện nút cho vai mà máy chủ từ chối → người bấm nhận 403 và không biết mình thiếu
    quyền hay hệ thống hỏng. Máy chủ mở cho vai mà màn hình giấu nút → quyền đã cấp nhưng không ai
    dùng được, đúng thứ đợt này đi chữa. Nên hai danh sách phải BẰNG NHAU, và ngày nào ai đổi một
    bên thì phép thử đỏ, buộc đổi nốt bên kia hoặc phải có người quyết.
    """
    may_chu = re.search(r'^HR_WRITE\s*=\s*\(([^)]*)\)', _doc(HRPY), re.M)
    assert may_chu, "không đọc được HR_WRITE trong hr.py"
    vai_may_chu = set(re.findall(r'"([a-z_]+)"', may_chu.group(1)))

    man_hinh = re.search(r'const\s+canDatLaiMK\s*=\s*\[([^\]]*)\]', _doc(ACCESS))
    assert man_hinh, "màn hình không khai danh sách vai được đặt lại mật khẩu (canDatLaiMK)"
    vai_man_hinh = set(re.findall(r'"([a-z_]+)"', man_hinh.group(1)))

    assert vai_man_hinh == vai_may_chu, (
        f"màn hình cho {sorted(vai_man_hinh)} thấy nút đặt lại mật khẩu, máy chủ cho "
        f"{sorted(vai_may_chu)} gọi cửa. Lệch nhau là một trong hai kiểu hỏng: nút bấm vào ra 403, "
        f"hoặc quyền đã cấp mà không có nút.")


def test_dat_lai_mat_khau_phai_hoi_lai_truoc_khi_lam():
    """Đặt lại mật khẩu của người khác là việc không lùi được: mật khẩu cũ mất ngay, và người ta
    đang đăng nhập dở sẽ bị đẩy ra. Bấm nhầm một dòng trong bảng vài trăm người là chuyện dễ."""
    s = _doc(ACCESS)
    # CẮT ĐÚNG KHỐI NÚT, không quét cả tệp. Bản đầu của phép thử này dò chuỗi "reset-password"
    # trên toàn tệp và vớ ngay đoạn CHÚ THÍCH giải thích vì sao có nút — rồi báo là nút không hỏi
    # lại. Lại đúng cái bệnh đã gặp hai lần hôm nay: hàng rào quét chữ phải neo vào CÚ PHÁP.
    # TR-10 · 13/11/2026 — CỬA HỎI ĐỔI CÁCH VIẾT, KHÔNG ĐỔI VIỆC: `window.confirm` (khoá cả
    # trang, và ngày 13/11 trình duyệt trả thẳng «prompt() is not supported») đổi sang
    # `await xacNhan(...)` vẽ trên trang, và `web/hang-rao/khong-hop-thoai-trinh-duyet.js` nay
    # cấm hẳn `confirm(`. Điều phép thử này canh vẫn y nguyên: nút KHÔNG LÙI ĐƯỢC thì phải hỏi
    # lại trước khi gọi cửa. Nhận cả hai cách viết, để nó đỏ vì thiếu CÂU HỎI chứ không vì một
    # cái tên hàm.
    khoi = re.search(r'canDatLaiMK && <button.*?</button>', s, re.S)
    assert khoi, "không tìm thấy khối nút đặt lại mật khẩu"
    assert re.search(r"xacNhan\(|(?:window\.)?confirm\(", khoi.group(0)), \
        "nút đặt lại mật khẩu không hỏi lại trước khi gọi cửa"
    assert "reset-password" in khoi.group(0), "nút không gọi cửa đặt lại mật khẩu"


# ═══════════════════════ B · SỬA HỒ SƠ ═══════════════════════
def test_man_hinh_nhan_su_co_bieu_sua_ho_so():
    s = _doc(HRS)
    assert "function SuaHoSo" in s, "không có biểu sửa hồ sơ nhân sự"
    assert re.search(r'post\(`/employees/\$\{sua\.id\}`', s), "biểu sửa không gọi cửa PUT /employees/{id}"


def _than_ham(ten: str, s: str) -> str:
    """Thân của một hàm cấp cao nhất, cắt tới `def` hoặc `@` tiếp theo ở cột 0.

    VÌ SAO PHẢI CẮT CHỨ KHÔNG DÒ CẢ TỆP — và đây là lần thứ TƯ trong ngày 12/10/2026 một hàng rào
    quét chuỗi bắt nhầm. Bản đầu của phép thử dưới đây hỏi `'"phien_ban": e.phien_ban' in hr.py`,
    tưởng là hỏi "cửa đọc đã trả số phiên bản ra chưa". Nó ra ĐÚNG, nhưng vì một dòng KHÁC HẲN:
    `update_employee` có `lambda: {**before, "phien_ban": e.phien_ban}` để dựng lời báo lệch phiên
    bản. Hai chỗ không liên quan gì nhau, mà phép thử coi là một — nên nó sẽ xanh mãi mãi và KHÔNG
    bao giờ nói ra rằng đầu máy chủ còn thiếu. Một hàng rào im lặng đúng vào chỗ nó sinh ra để canh
    thì tệ hơn là không có, vì người sau đọc thấy có phép thử rồi yên tâm.
    """
    m = re.search(r"^def %s\(" % re.escape(ten), s, re.M)
    if not m:
        return ""
    sau = s[m.start():]
    k = re.search(r"\n(?=@|def )", sau)
    return sau[:k.start()] if k else sau


def test_bieu_sua_gui_phien_ban_len():
    """ĐẦU MÀN HÌNH của phép kiểm lệch phiên bản — luôn bị canh.

    Hôm nay dòng này CHƯA có tác dụng: cửa đọc `emp_out` chưa trả `phien_ban` ra nên màn hình gửi
    lên một giá trị rỗng, và `kiem_phien_ban` rơi vào nhánh "chưa gửi thì cho qua". Đúng vì thế mà
    phép thử này cần thiết: một dòng chưa có tác dụng là thứ người dọn mã xoá đi đầu tiên, và xoá
    xong thì ngày đầu máy chủ làm xong, hàng rào chống hai người sửa đè nhau vẫn không chạy — không
    ai biết, vì chẳng có gì đỏ.
    """
    assert re.search(r"phien_ban:\s*sua\.phien_ban", _doc(HRS)), (
        "biểu sửa không gửi phiên bản lên. Dòng này trông như thừa chừng nào `emp_out` chưa trả "
        "`phien_ban` ra, nhưng nó là MỘT NỬA của hàng rào chống hai người sửa đè nhau — bỏ đi thì "
        "nửa kia làm xong cũng vô dụng.")


def test_neu_cua_doc_da_tra_phien_ban_thi_hai_dau_phai_khop():
    """ĐẦU MÁY CHỦ — còn NỢ, và chỗ phải thêm ghi thẳng ra đây.

    `kiem_phien_ban` có từ đợt VPM-8, nhưng nó CHỈ chạy khi màn hình gửi phiên bản lên, mà màn hình
    chỉ gửi được khi cửa đọc trả ra. Cửa đọc là `emp_out` trong `backend/app/api/v1/hr.py`, và tới
    12/10/2026 nó chưa trả. Thiếu đúng một khoá `"phien_ban": e.phien_ban`.

    VÌ SAO VÒNG TK-1 KHÔNG TỰ THÊM: tệp ấy đang bị làn Phân quyền giữ bằng một dòng việc còn mở
    (DL-1, PR #294 gộp 12/10). Lật dòng của làn khác khi việc còn nóng là đúng cái luật làn này tự
    đặt ở VA-MAIN8 và NS-1 cấm; khai thêm mà không lật thì hai làn cùng một tệp, đúng cái làm main
    đỏ 09/10. Nên món nợ được GHI RA chứ không làm liều.

    Phép thử này đọc THÂN của chính `emp_out`, không dò cả tệp — xem `_than_ham`. Chừng nào đầu máy
    chủ chưa có, nó không đòi gì; ngày ai thêm khoá ấy vào mà đầu màn hình đã bị xoá mất thì nó đỏ.
    """
    than = _than_ham("emp_out", _doc(HRPY))
    assert than, "không đọc được hàm `emp_out` trong hr.py — cửa đọc hồ sơ nhân sự đã đổi tên?"
    if '"phien_ban"' not in than:
        pytest.skip(
            "`emp_out` chưa trả `phien_ban` ra — món nợ đã ghi trong sổ làn Vòng, dòng TK-1. "
            "Thêm một khoá vào `emp_out` là hàng rào chống hai người sửa đè nhau bắt đầu chạy.")
    assert re.search(r"phien_ban:\s*sua\.phien_ban", _doc(HRS)), (
        "cửa đọc ĐÃ trả `phien_ban` ra mà biểu sửa không gửi lại — phép kiểm lệch phiên bản rơi "
        "vào nhánh bỏ qua, và hai người sửa cùng một hồ sơ vẫn đè nhau trong im lặng.")

def test_dieu_chuyen_phai_co_ly_do_truoc_khi_luu():
    """Máy chủ coi đổi phòng / chức danh / văn phòng là một lần ĐIỀU CHUYỂN và tự ghi vào lịch sử
    tổ chức. Ghi một chặng mới mà không có lý do là để lại một dòng lịch sử không ai giải thích
    được ba tháng sau."""
    s = _doc(HRS)
    assert re.search(r'const\s+doiToChuc\s*=', s), "biểu sửa không phát hiện trường hợp điều chuyển"
    assert re.search(r'thieuLyDo\s*=\s*doiToChuc\s*&&', s), "điều chuyển không bắt buộc ghi lý do"
    assert re.search(r'disabled=\{[^}]*thieuLyDo', s), "nút Lưu vẫn bấm được khi điều chuyển thiếu lý do"


def test_o_ngay_rong_khong_duoc_gui_chuoi_rong():
    """Máy chủ nhận `date | None`; chuỗi rỗng là 422. Gửi bừa thì người dùng thấy một lời báo lỗi
    kỹ thuật mà không hiểu mình làm sai gì."""
    s = _doc(HRS)
    for o in ("birth_date", "card_expiry"):
        assert re.search(r'if \(sua\.%s\) g\.%s' % (o, o), s), (
            f"ô ngày `{o}` gửi lên kể cả khi rỗng — máy chủ sẽ trả 422")
