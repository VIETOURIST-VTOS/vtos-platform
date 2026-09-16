# -*- coding: utf-8 -*-
"""TC-20 · Thẻ "Tồn đọng cần xử lý" và khối gom nhóm cảnh báo (13/9/2026).

BỐI CẢNH. Trên bản chạy thật ngày 13/9, thẻ "Tồn đọng cần xử lý" in số 60 trong khi dòng chữ nhỏ
ngay dưới nó ghi "1387 cảnh báo đỏ đang mở". Sáu mươi là SỐ DÒNG máy chủ gửi kèm màn hình (danh
sách đang bị cắt), không phải số tồn đọng. Con số nhỏ nằm ở chỗ to nhất màn hình, con số thật nằm
ở dòng chữ nhỏ – và không ai đọc màn hình theo kiểu ấy.

Loại lỗi này không tự lộ ra: cả hai số đều có thật, đều do máy chủ trả về, chỉ là lấy nhầm cái.
Nên phải có test canh, chứ mắt người soát lại lần sau sẽ bỏ qua y như lần đầu.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
KHOI = GOC / "web" / "components" / "KhoiTonDong.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _the_ton_dong(nguon: str) -> str:
    """Cắt đúng khai báo thẻ "Tồn đọng cần xử lý" trong mảng tám thẻ."""
    i = nguon.find('nhan: "Tồn đọng cần xử lý"')
    assert i > 0, 'Không tìm thấy thẻ "Tồn đọng cần xử lý" trong màn hình 01'
    return nguon[i:nguon.find("},", i) + 2]


def test_the_ton_dong_lay_tong_that_khong_lay_do_dai_danh_sach():
    """Con số to của thẻ phải là tổng thật của máy chủ, không phải len() của danh sách gửi kèm."""
    the = _the_ton_dong(_doc(TRANG))
    assert "so: dem(k.canh_bao_do)" in the, (
        "Thẻ Tồn đọng phải lấy `k.canh_bao_do` (tổng thật) làm con số chính.\n"
        f"Đang là:\n{the}"
    )
    assert not re.search(r"so:\s*dem\(\s*d\.alerts", the), (
        "Thẻ Tồn đọng đang lấy độ dài danh sách `d.alerts` làm con số chính. Đó là số dòng máy chủ "
        "gửi kèm trang này (đang cắt), không phải số tồn đọng – đúng lỗi đã lên bản chạy thật "
        "ngày 13/9 (in 60 trong khi thực tế 1387)."
    )


def test_the_ton_dong_van_co_cua_nhap_khi_rong():
    """Ranh giới 09/9: thẻ nào có thể rỗng thì phải chỉ ra bộ phận và cửa xem/nhập."""
    the = _the_ton_dong(_doc(TRANG))
    assert "cua:" in the and "ai:" in the, (
        "`k.canh_bao_do` có thể không được máy chủ gửi; khi ấy thẻ rỗng và bắt buộc phải kèm "
        "`cua:` (đường dẫn) và `ai:` (bộ phận phụ trách).\n" + the
    )


def test_khong_con_bang_canh_bao_phang_tren_man_hinh_01():
    """Bảng phẳng cũ đổ sáu mươi dòng gần giống hệt nhau – đã thay bằng khối gom nhóm.

    SỰ THẬT ĐỔI, LUẬT KHÔNG ĐỔI (15/9/2026). Luật vẫn là: KHÔNG đổ danh sách cảnh báo phẳng ra màn
    hình Chủ tịch. Trước đây luật ấy được giữ bằng cách thay bảng phẳng bằng khối gom nhóm; nay anh
    Tuấn chốt bỏ luôn cả khối gom nhóm khỏi màn hình 01, vì cùng dữ liệu ấy đã có ở thẻ chỉ tiêu
    "Tồn đọng cần xử lý" và ở biểu đồ theo bộ phận — ba chỗ nói một chuyện thì không chỗ nào còn
    đáng đọc. Khối vẫn còn nguyên trong KhoiTonDong.tsx và ở trang /alerts.
    """
    nguon = _doc(TRANG)
    assert "d.alerts.map" not in nguon, (
        "Màn hình 01 đổ thẳng `d.alerts.map` ra một bảng phẳng — đúng cái đã bỏ từ vòng TC-20."
    )
    assert "<KhoiTonDong" not in nguon, (
        "Khối gom nhóm đã chuyển khỏi màn hình 01 (anh Tuấn chốt 15/9/2026). Lắp lại là bày cùng "
        "một dữ liệu ở ba chỗ trên một trang."
    )
    # Khối KHÔNG bị xoá: mã còn nguyên để lắp vào trang Cảnh báo.
    assert KHOI.exists() and "gomTheoLoai" in _doc(KHOI)


def test_khoi_ton_dong_khong_tu_doan_bo_phan():
    """Gom theo `kind` là thứ máy chủ có; gom theo bộ phận là một tuyên bố nghiệp vụ chưa ai khai.

    Đoán bảng loại→bộ phận rồi hiển thị như thật là kiểu sai tệ nhất: nhìn vẫn hợp lý, nhưng đẩy
    việc sang nhầm phòng và không ai phát hiện. Màn hình phải nói ra là nó chưa gom theo bộ phận.
    """
    nguon = _doc(KHOI)
    assert "gomTheoLoai" in nguon, "Thiếu hàm gom nhóm theo loại cảnh báo"
    assert "chưa gom được theo bộ phận" in nguon, (
        "Khối phải ghi rõ trên màn hình rằng nó gom theo LOẠI chứ chưa gom theo BỘ PHẬN, và bảng "
        "khai loại→bộ phận là phần còn thiếu."
    )
    # Không được có sẵn một bảng ánh xạ loại → bộ phận do màn hình tự bịa.
    for pho in ("Kinh doanh\":", "Kế toán\":", "Điều hành\":"):
        assert pho not in nguon, (
            f"Khối đang tự khai ánh xạ loại cảnh báo → bộ phận ({pho}). Đó là tuyên bố nghiệp vụ, "
            "phải do máy chủ khai, không phải màn hình đoán."
        )


def test_khoi_ton_dong_noi_ra_khi_danh_sach_bi_cat():
    """Danh sách gửi kèm ít hơn tổng thật thì phải nói ra, kèm chỗ xem đủ."""
    nguon = _doc(KHOI)
    assert "cat" in nguon and "/alerts" in nguon, (
        "Khi `tong` lớn hơn số dòng gửi kèm, khối phải nói rõ đang xem bao nhiêu trên tổng bao "
        "nhiêu và dẫn sang trang /alerts."
    )


def test_luat_moi_khong_nam_duoi_khoi_tc4():
    """Nhắc lại luật vị trí: test_tc4_dien_thoai đọc bản điện thoại bằng rindex().

    Mọi @media (max-width:640px) mới phải nằm TRÊN khối TC-4, nếu không TC-4 đọc nhầm khối và đỏ
    với một thông báo lỗi nói về bảng trên điện thoại – rất khó lần ra nguyên nhân thật.
    """
    css = _doc(CSS)
    cuoi = css.rindex("@media (max-width:640px)")
    khoi_tc4 = css[cuoi:]
    assert "table.bang-doc" in khoi_tc4, (
        "Khối @media (max-width:640px) CUỐI CÙNG phải là khối TC-4 (bảng đọc trên điện thoại). "
        "Có luật điện thoại mới bị đặt xuống dưới nó."
    )
    assert ".td-vd" in css, "Thiếu luật trình bày cho khối Tồn đọng"
    assert css.index(".td-vd") < cuoi, ".td-vd phải được khai TRƯỚC khối TC-4"


def test_css_can_bang_ngoac():
    """Một dấu } thừa sẽ ĐÓNG SỚM và vô hiệu hoá âm thầm mọi luật phía sau (đã xảy ra 13/9)."""
    css = re.sub(r"/\*.*?\*/", "", _doc(CSS), flags=re.S)
    assert css.count("{") == css.count("}"), (
        f"globals.css lệch ngoặc: {css.count('{')} dấu mở, {css.count('}')} dấu đóng"
    )
