"""TC-82 · DÒNG VÍ DỤ TRÊN MÀN HÌNH TRỐNG — và vì sao KHÔNG nạp số nháp vào sổ.

Anh Tuấn chốt 24/9/2026: nhân viên Marketing cần thấy format phải điền trước khi gõ dòng đầu tiên.
Hai cách được đặt lên bàn, và cách bị loại đáng ghi lại đúng bằng cách được chọn.

CÁCH BỊ LOẠI — nạp vài dòng thật vào sổ cho màn hình trông có số. Nó hỏng theo một kiểu chỉ lộ ra
sau vài tháng: dòng nháp nạp vào rồi thì KHÔNG có cột nào đánh dấu nó là nháp. Ba tháng sau không
ai phân biệt được nó với dòng thật, bảng hiệu quả kênh cộng cả nó vào, và người đọc báo cáo không
có cách nào biết mình đang đọc một con số có lẫn đồ giả. Đúng thứ ranh giới 09/9/2026 cấm: phần
mềm viết cấu trúc và phép tính, KHÔNG bịa số liệu.

CÁCH ĐƯỢC CHỌN — dòng ví dụ sống trong mã màn hình, chỉ hiện khi bảng còn TRỐNG, có nhãn trên từng
dòng, và biến mất ngay khi có dòng thật đầu tiên. Không đi qua máy chủ, không vào bảng nào.

BỐN CHỖ PHÉP THỬ NÀY CANH:

 1. DÒNG VÍ DỤ ĐI VÀO CƠ SỞ DỮ LIỆU. Đây là cái phải không bao giờ xảy ra. Không có lời gọi ghi
    nào mang dữ liệu ví dụ, và hai bảng vẫn rỗng sau khi màn hình dựng xong.

 2. NHÃN CHỈ ĐẶT MỘT CHỖ Ở ĐẦU BẢNG. Người cuộn tới giữa bảng không thấy câu ấy nữa. Nhãn phải
    nằm trên TỪNG dòng.

 3. VÍ DỤ CÒN NẰM LẠI KHI ĐÃ CÓ DÒNG THẬT. Một dòng giả đứng cạnh dòng thật trong cùng một bảng
    là chỗ nguy hiểm nhất của cả cách làm này.

 4. SỐ TRONG VÍ DỤ TRÔNG NHƯ SỐ THẬT CỦA VIETOURIST. Ví dụ phải dạy được cách điền mà không ai
    chép nhầm thành số liệu — nên nó phải mang đủ ba trạng thái của ô tiền (rỗng / 0 / số dương)
    để dạy đúng luật khó nhất, chứ không phải một hàng số đẹp.
"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
TRANG = WEB / "app" / "bao-chi-kol" / "page.tsx"


def _ma() -> str:
    return TRANG.read_text(encoding="utf-8")


def test_vi_du_khong_bao_gio_di_qua_may_chu():
    """Cái phải không bao giờ xảy ra: một dòng ví dụ nằm lại trong sổ."""
    t = _ma()
    for hang in ("VI_DU_PR", "VI_DU_SU_KIEN", "VI_DU_KOL"):
        assert f"const {hang}" in t, f"Thiếu hằng {hang}"
        # Hằng dữ liệu ví dụ không được xuất hiện trong bất kỳ lời gọi ghi nào.
        for goi in re.findall(r'(?:post|api)\([^)]{0,400}\)', t, re.S):
            assert hang not in goi, f"{hang} lọt vào một lời gọi máy chủ: {goi[:120]}"


def test_vi_du_chi_hien_khi_bang_CON_TRONG():
    """Một dòng giả đứng cạnh dòng thật là chỗ nguy hiểm nhất của cả cách làm này."""
    t = _ma()
    # Cả ba khối ví dụ đều nằm sau một điều kiện "danh sách rỗng".
    assert "{!(pr.rows || []).length && <>" in t
    assert "{!(ds.rows || []).length && <>" in t
    # Không có chỗ nào render ví dụ mà không kèm điều kiện rỗng.
    for hang in ("VI_DU_PR", "VI_DU_SU_KIEN", "VI_DU_KOL"):
        for m in re.finditer(rf"{hang}[^\n]*\.map\(", t):
            truoc = t[max(0, m.start() - 400):m.start()]
            assert ".length && <>" in truoc, (
                f"{hang} được vẽ mà không có điều kiện bảng rỗng ngay trước đó")


def test_nhan_vi_du_nam_tren_TUNG_dong_chu_khong_chi_o_dau_bang():
    """Người cuộn tới giữa bảng không còn thấy câu ở đầu bảng nữa."""
    t = _ma()
    assert t.count('<Tag cls="grey">ví dụ</Tag>') >= 2, (
        "Mỗi bảng ví dụ phải có nhãn trên từng dòng, không chỉ một câu ở đầu")
    assert "BangTrong" in t, "Thiếu khung báo bảng trống"
    assert "không nằm trong sổ" in t


def test_vi_du_day_dung_ba_trang_thai_cua_o_tien():
    """Ví dụ phải dạy được luật khó nhất — rỗng khác 0 khác số dương."""
    t = _ma()
    i, j = t.index("const VI_DU_KOL"), t.index("/** Khung bao quanh")
    khoi = t[i:j]
    assert "luong_theo_doi: null" in khoi, "Thiếu ví dụ ô ĐỂ TRỐNG (chưa đo)"
    assert "gia_tham_khao: null" in khoi, "Thiếu ví dụ ô tiền ĐỂ TRỐNG (chưa có giá)"
    assert re.search(r"gia_tham_khao: \d", khoi), "Thiếu ví dụ ô tiền có số"
    assert "so_lan_chua_co_gia: 1" in khoi, (
        "Phải có một dòng cho thấy cột 'chưa có giá' đếm được — đó là cách người dùng hiểu "
        "vì sao tổng nhỏ hơn họ tưởng")


def test_vi_du_khong_dung_ten_that_cua_nhan_su_hay_doi_tac():
    """Ví dụ là ví dụ. Mượn tên người thật vào đây là mở đường cho người sau tưởng nó là số thật."""
    t = _ma()
    i, j = t.index("const VI_DU_PR"), t.index("/** Khung bao quanh")
    khoi = t[i:j]
    # Bốn cặp tài khoản trùng thật đang chờ xử lý (đo 19/9/2026) — không được xuất hiện ở đây.
    for ten in ("Vân Anh", "Thuỳ Trang", "Diệu Trinh", "Hoàng Anh"):
        assert ten not in khoi, f"Tên người thật {ten!r} không được dùng làm dữ liệu ví dụ"


def test_ma_nguon_ghi_lai_vi_sao_KHONG_nap_so_nhap_vao_so():
    """Không ghi lại thì vòng sau sẽ có người 'cho tiện' mà nạp thẳng vào bảng."""
    t = _ma()
    i = t.index("const VI_DU_PR")
    ghi_chu = t[max(0, i - 1400):i]
    assert "không nằm trong sổ" in t
    for y in ("KHÔNG có cột nào đánh dấu", "09/9/2026"):
        assert y in ghi_chu, f"Ghi chú thiếu ý: {y}"
