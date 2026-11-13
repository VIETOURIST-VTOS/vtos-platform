# -*- coding: utf-8 -*-
"""TR-15b · LUẬT CỦA TR-15 KHÔNG ĂN, VÀ SAI ĐÚNG CÁI BẪY TR-15 VỪA GỠ Ở NÚT.

Nghiệm thu TR-15 trên bản chạy thật ngày 14-11-2026, đo lại từng con số chứ không đọc báo cáo:

    nút vào đường đặt tour   1,93:1  →  7,92:1   ĐẠT   (95/95 nút, 0 cái không đạt)
    thẻ h1                   0       →  1        ĐẠT
    thẻ main                 0       →  1        ĐẠT
    ô tích trong bộ lọc      18x18   →  18x18    KHÔNG ĐẠT

Hỏi lại trình duyệt luật nào đang thắng ô tích ấy. Bốn luật trúng, hai luật đặt kích thước:

    .ksv-chk input, #vtd-access .ksv .ksv-chk input   {width:18px}   (1,2,1)  ← thắng
    .tra input[type=checkbox]                         {width:24px}   (0,2,1)

Luật cũ viết thành DANH SÁCH hai phép chọn, và phép chọn thứ hai có ID. Đã kiểm trên chính
trang đang chạy: `#vtd-access` CÓ THẬT và là tổ tiên của gốc trang tour, nên nhánh có ID mới
là nhánh trúng — điểm (1,2,1), đè luật (0,2,1) mà TR-15 vừa thêm.

Đó đúng là cái bẫy TR-15 vừa gỡ ở nút <a> một giờ trước: cùng một luật `#vtd-access ...` có ID
đè luật chỉ có lớp. Sang ô tích thì quên kiểm — tưởng `.tra` là đủ, tưởng chứ không đo.

BÀI HỌC GHI LẠI ĐỂ KHÔNG LẶP: phép thử của TR-15 đọc tệp mã và thấy luật CÓ MẶT nên xanh,
trong khi trên trang thật luật ấy thua. Đọc tệp chỉ chứng minh được «đã viết», không chứng
minh được «đã thắng». Với mọi luật phải đè một luật khác, đo bằng độ ưu tiên chứ không bằng
sự có mặt — đó là việc của phép thử 2 và 3 dưới đây.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"


def doc() -> str:
    return TEP.read_text(encoding="utf-8")


def diem(pc: str) -> tuple[int, int, int]:
    """Độ ưu tiên của một phép chọn CSS: (số ID, số lớp/thuộc tính/lớp-giả, số thẻ)."""
    pc = pc.strip()
    a = len(re.findall(r"#[\w-]+", pc))
    b = len(re.findall(r"\.[\w-]+", pc)) + len(re.findall(r"\[[^\]]+\]", pc)) + \
        len(re.findall(r":(?!:)[a-z-]+", pc))
    c = len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", pc))
    return (a, b, c)


def test_tr15b_1_co_nhanh_co_id_cho_o_tich():
    s = doc()
    assert "#vtd-access .ksv.tra input[type=checkbox]" in s
    assert "#vtd-access .ksv.tra input[type=radio]" in s


def test_tr15b_2_phai_thang_duoc_luat_cu_cua_he_thong():
    """Luật phải đè: `#vtd-access .ksv .ksv-chk input` = (1,2,1). Của mình phải LỚN HƠN,
    không được bằng — bằng thì phải trông vào thứ tự dòng, mà thứ tự dòng đổi lúc nào không
    ai biết khi hai tệp kiểu được nối lại với nhau."""
    cu = diem("#vtd-access .ksv .ksv-chk input")
    moi = diem("#vtd-access .ksv.tra input[type=checkbox]")
    assert cu == (1, 2, 1), cu
    assert moi == (1, 3, 1), moi
    assert moi > cu, "không thắng được thì ô tích vẫn 18px như trước"


def test_tr15b_3_nhanh_khong_id_van_con_cho_trang_khong_boc_vtd_access():
    """Giữ cả nhánh không ID: trang nào không bọc trong #vtd-access thì nhánh ấy mới trúng."""
    s = doc()
    assert ".tra input[type=checkbox],.tra input[type=radio]{width:24px;height:24px" in s


def test_tr15b_4_kich_thuoc_dung_24px():
    s = doc()
    i = s.index("#vtd-access .ksv.tra input[type=checkbox]")
    luat = s[i:s.index("}", i)]
    assert "width:24px" in luat and "height:24px" in luat, "WCAG 2.5.8 đòi tối thiểu 24x24"


def test_tr15b_5_khong_dong_vao_cai_TR15_da_lam_dung():
    """Nút đặt tour đã đo được 7,92:1 trên bản chạy — vòng này không được chạm vào nó."""
    s = doc()
    assert "#vtd-access .tra a.ksv-btn" in s
    i = s.index("#vtd-access .tra a.ksv-btn")
    assert "-webkit-text-fill-color:#fff" in s[i:s.index("}", i)]
    assert s.count('<main className="ksv tra">') == 2
    assert s.count("<h1") == 2
