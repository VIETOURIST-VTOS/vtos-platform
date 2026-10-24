# -*- coding: utf-8 -*-
"""QT-2 · Một con số chỉ được nằm MỘT chỗ trên màn Chủ tịch (Chủ tịch chốt 24/10/2026).

VÌ SAO CÓ VÒNG NÀY. Sau khi QT-1 gộp hai ô quyết toán, Chủ tịch mở màn thật và chỗ lặp lộ ra ở
khối bên cạnh — lần này một phần do chính vòng QT-1 gây thêm:

  · `2.607` hiện BA lần: tiêu đề khối «Việc nghiêm trọng», rồi dòng con lặp lại ngay dưới nó
    (dòng ấy do QT-1 thêm vào), rồi «Nghiêm trọng 2.607 · 33%» trong khối «Tồn đọng công việc».
  · `7.816` hiện HAI lần: dòng «Tổng việc đang mở» của QT-1, và tiêu đề khối «Tồn đọng».
  · Hai con số cảnh báo đá nhau trên cùng màn: `4.854` (mức đỏ) và `10.087` (mọi mức), không chỗ
    nào nói chúng đếm hai thứ khác nhau.

Đúng điều Chủ tịch cấm ở TC-40: «các mục lặp lại thì bỏ hết». Vòng này gộp khối «Tồn đọng công
việc» vào khối «Việc nghiêm trọng» — cùng cách đã làm với «Chờ quyết toán» ở QT-1 — rồi xoá khối
cũ. «Khách tiềm năng mới» về làm ô thứ tư của hàng «Hoạt động tour».

BỘ NÀY SOI MÃ MÀN HÌNH, KHÔNG SOI PHÉP TÍNH. Đó là chỗ duy nhất bắt được lỗi này: cả hai khối
đều đọc đúng một nguồn `viec_van_hanh`, nên không phép tính nào sai — cái sai là BÀY HAI LẦN.
Một phép thử phép tính sẽ xanh suốt trong khi màn hình vẫn lặp.

  qt2_1  khối «Tồn đọng công việc» không được quay lại
  qt2_2  ba thứ của nó phải còn sống trong khối gộp, không rơi mất khi xoá
  qt2_3  không còn dòng lặp đúng con số của tiêu đề
  qt2_4  chữ «cảnh báo» phải đi kèm mức, để 4.854 không đá với 10.087
  qt2_5  lưới cũ `h2b` biến mất, «Khách tiềm năng mới» nằm trong hàng bốn ô
  qt2_6  không luật CSS nào chết sau khi xoá khối
"""
import io
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TSX = os.path.join(GOC, "web", "components", "KhoiVanHanh.tsx")
CSS = os.path.join(GOC, "web", "components", "KhoiVanHanh.css")


def _doc(p: str) -> str:
    assert os.path.exists(p), f"Thiếu tệp {os.path.relpath(p, GOC)}"
    return io.open(p, encoding="utf-8").read()


def _bo_chu_thich(s: str) -> str:
    """Bỏ `/* ... */` và `// ...` trước khi soi CHỮ hiện lên màn hình.

    Bản đầu của `qt2_4` đỏ vì nó bắt chữ «cảnh báo» nằm trong chính đoạn chú thích đầu tệp —
    đỏ vì lời kể, không vì màn hình. Cùng bài học `test_le2b` đã ghi: soi mã thì phải bỏ chú thích,
    không thì mỗi lần ai đó viết một câu giải thích là hàng rào đỏ oan.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return "\n".join(d for d in s.split("\n") if not d.lstrip().startswith("//"))


def test_qt2_1_khoi_ton_dong_khong_quay_lai():
    s = _bo_chu_thich(_doc(TSX))
    assert "Tồn đọng công việc" not in s, (
        "Khối «Tồn đọng công việc» quay lại. Nó đếm CÙNG `viec_van_hanh` với khối «Việc nghiêm "
        "trọng», nên dựng lại nó là đưa 7.816 và 2.607 về nằm hai chỗ lần nữa.")


def test_qt2_2_ba_thu_cua_khoi_cu_khong_roi_mat():
    """Xoá một khối dễ làm rơi mất thứ chỉ nó mới có. Ba thứ này không có chỗ nào khác."""
    s = _bo_chu_thich(_doc(TSX))
    # ĐÒI CẢ ĐIỀU KIỆN LẪN CHỖ BÀY, không chỉ đòi chuỗi có mặt.
    # Bản đầu chỉ hỏi `"chua_anh_xa" in s`, và kiểm ngược cho thấy nó YẾU: đổi điều kiện
    # thành `{false &&` thì dòng ấy tắt hẳn trên màn hình mà phép thử vẫn xanh, vì chuỗi còn nằm
    # trong thân JSX. Một chuỗi còn trong tệp không có nghĩa là người dùng còn thấy nó.
    assert "v.chua_anh_xa > 0" in s, (
        "mất ĐIỀU KIỆN hiện dòng «cảnh báo chưa xác định được hồ sơ» — việc của CNTT bị ẩn")
    assert "so(v.chua_anh_xa)" in s, "mất chỗ BÀY con số cảnh báo chưa xác định được hồ sơ"
    assert "Xem toàn bộ công việc" in s, "mất đường đi tới danh sách đầy đủ"
    assert "gio(luc)" in s, "mất mốc dữ liệu — người đọc không biết số cũ hay mới"


def test_qt2_3_khong_con_dong_lap_dung_con_so_cua_tieu_de():
    """QT-1 đặt `<So v={do_}>` làm tiêu đề rồi lại kê `{so(do_)}` thành một dòng con ngay dưới.

    Cùng một biến, hai lần, cách nhau ba dòng — người đọc thấy 2.607 hai lần trong MỘT khối.
    Các dòng con nay đi từ `theo_muc`, nên `do_` chỉ còn được dùng cho tiêu đề.
    """
    s = _bo_chu_thich(_doc(TSX))
    assert s.count("{so(do_)}") == 0, (
        "còn một dòng kê lại đúng con số của tiêu đề khối. Dòng con phải lấy từ `theo_muc`.")
    assert "<So v={do_}" in s, "tiêu đề khối «Việc nghiêm trọng» phải vẫn là số việc mức đỏ"


def test_qt2_4_moi_con_so_canh_bao_phai_noi_ro_muc_nao():
    """4.854 là cảnh báo MỨC ĐỎ, 10.087 là MỌI MỨC. Hai con số ấy từng đứng cùng một màn mà
    không chỗ nào nói chúng đếm hai thứ khác nhau — đọc ra như mâu thuẫn.

    Chỉ soi ĐÚNG chỗ nguy hiểm: một CON SỐ đứng ngay cạnh chữ «cảnh báo». Tiêu đề cột bảng hay
    tên đường dẫn có chữ ấy thì không đếm gì, không lừa được ai.

    Bản đầu của phép thử này quét MỌI chữ «cảnh báo» và đỏ hai lần vì lý do không thật: một lần
    trúng đoạn chú thích đầu tệp, một lần trúng `<th>Loại cảnh báo</th>`. Hàng rào đỏ oan là hàng
    rào sớm muộn bị tắt, nên thu hẹp lại thay vì nới cổng.
    """
    s = _bo_chu_thich(_doc(TSX))
    # SỬA 24/10/2026 (soát chéo làn Phân quyền). Bản đầu nhận `v.canh_bao` vào «nguồn có mức»,
    # mà `v.canh_bao` CHÍNH LÀ con số MỌI MỨC — nó không mang mức nào. Nghĩa là đặt lại
    # `{so(v.canh_bao)} cảnh báo` ngay cạnh con số mức đỏ thì phép thử vẫn xanh, và đúng chuyện
    # 4.854 đá 10.087 lặp lại y nguyên. Hàng rào canh TÊN BIẾN chứ không canh ĐIỀU NÓ HỨA.
    CO_MUC = ("m.canh_bao", "v.chua_anh_xa")        # tự mang mức
    MOI_MUC = ("v.canh_bao",)                       # tổng mọi mức — phải CÓ CHỮ NÓI RÕ LÀ TỔNG
    CHU_TONG = ("việc đang mở", "mọi mức", "tổng")
    tim = list(re.finditer(r"\{so\(([^)]*)\)\}[^<{]{0,40}cảnh báo", s))
    assert tim, "không còn chỗ nào bày số cảnh báo — phép thử này mất việc, xem lại"
    for m in tim:
        bieu_thuc = m.group(1).strip()
        if any(n in bieu_thuc for n in CO_MUC):
            continue
        assert any(n in bieu_thuc for n in MOI_MUC), (
            f"con số cảnh báo `{bieu_thuc}` không đi từ nguồn nào biết mức. "
            f"Một con số cảnh báo không nói mức sẽ đá với con số cảnh báo của mức khác.")
        # Chữ dẫn phải nằm TRONG CÙNG MỘT THẺ với con số: cắt từ dấu `<` gần nhất phía trước.
        # Nhìn lui một số ký tự cố định thì vắt sang thẻ khác và nhặt nhầm chữ của dòng trên —
        # chính bản đầu của lần vá này mắc thế, kho giả bắt được.
        dau = s.rfind("<", 0, m.start())
        trong_the = s[dau if dau >= 0 else 0:m.start()].lower()
        assert any(c in trong_the for c in CHU_TONG), (
            f"`{bieu_thuc}` là cảnh báo của MỌI MỨC mà trong cùng thẻ không có chữ nào nói đó là "
            f"tổng (cần một trong {CHU_TONG}). Đặt nó cạnh một con số mức đỏ thì người đọc thấy "
            f"hai con số cảnh báo đá nhau — đúng chuyện 4.854 với 10.087.")


def test_qt2_5_luoi_cu_bien_mat_va_khach_tiem_nang_ve_hang_bon_o():
    s = _doc(TSX)
    assert "h2b" not in s, "lưới `h2b` của hai khối cũ vẫn còn — hàng rỗng hoặc một ô lẻ loi"
    assert 'vh-hang h4' in s, "hàng «Hoạt động tour» phải là bốn ô sau khi nhận «Khách tiềm năng mới»"
    i = s.index('vh-hang h4')
    j = s.index("</div>", s.index("Cửa nhập"))
    assert "Khách tiềm năng mới" in s[i:j], "«Khách tiềm năng mới» không nằm trong hàng bốn ô"


def test_qt2_6_khong_luat_css_nao_chet():
    """Xoá khối mà để luật CSS của nó nằm lại thì lần sau có người dựng lại khối từ chính luật ấy.
    «Mã chết vẫn là mã» — bài học đã ghi ở các vòng trước."""
    tsx, css = _doc(TSX), _doc(CSS)
    # SỬA 24/10/2026 (soát chéo làn Phân quyền). Bản đầu so CHUỖI CON (`c not in tsx`), nên một
    # lớp đã chết tên `vh-nhan` vẫn được coi là còn sống chỉ vì TSX có `vh-nhan2`. Nay cắt TSX
    # thành TỪ rồi so cả từ.
    # CHỖ CỐ Ý KHÔNG NỚI: biểu thức dưới vẫn dừng ở dấu chấm thứ hai, nên biến thể kiểu `h2b`
    # trong `.vh-hang.h2b` không được rút ra. Nới ra sẽ kéo theo mọi lớp một chữ (`.v`, `.t`,
    # `.qh`…) mà nhiều cái dùng ở tệp khác — hàng rào đỏ oan là hàng rào sớm muộn bị tắt.
    # `qt2_5` đã canh riêng `h2b` bằng tên.
    lop = sorted(set(re.findall(r"\.(vh-[a-z0-9-]+|c-[a-z0-9-]+)", css)))
    dung = set(re.findall(r"[A-Za-z0-9_-]+", tsx))
    chet = [c for c in lop if c not in dung]
    assert not chet, f"luật CSS không còn ai dùng: {chet}"
