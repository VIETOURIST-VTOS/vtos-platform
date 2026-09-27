"""TC-86 · MỤC CÓ THAM SỐ TRÊN ĐƯỜNG DẪN MÀ MÀN HÌNH KHÔNG ĐỌC.

Rà cây phân hệ ngày 25/9/2026 (anh Tuấn: "em rà tiếp đi") tìm ra: mục 2.7.2 "Hiệu quả khách lẻ &
MICE" trỏ tới `/dong-gop-marketing?mang=le`, nhưng màn hình ấy khởi động với ô Luồng để TRỐNG và
chưa bao giờ đọc tham số trên đường dẫn. Hệ quả: 2.7.2 mở ra đúng bằng 2.7.1 và 2.7.3 — ba mục
khác tên, cùng một bảng số. Không có lỗi nào hiện ra; người bấm chỉ đơn giản không biết mình đang
xem cái gì, và một người tin rằng mình đang đọc riêng phần khách lẻ thì đọc sai con số.

ĐÂY LÀ MỘT LỚP LỖI, KHÔNG PHẢI MỘT CHỖ. Cây phân hệ có 34 mục mang tham số trên đường dẫn (?tab=,
?mang=, …). Mỗi mục như thế là một lời hứa: "bấm vào đây thì mở đúng phần này". Lời hứa ấy do HAI
tệp giữ — cây khai tham số, màn hình đọc tham số — và không có gì buộc hai bên đi cùng nhau. Đổi
tên khoá ở một bên là lời hứa gãy trong im lặng.

Nên phép thử này KHÔNG canh riêng mục 2.7.2. Nó đọc cây, lấy MỌI mục có tham số, rồi đòi màn hình
đích (hoặc một component nó nhập vào) có nhắc tới khoá ấy. Thô, nhưng bắt đúng kiểu hỏng đã xảy ra:
một bên khai, bên kia không biết.

CÒN MỘT CHỖ NỮA PHẢI CANH: giá trị lạ. `?mang=abc` gõ sai mà lọt xuống máy chủ thì bảng trả về
rỗng, và một màn hình rỗng trông y hệt "kỳ này không có doanh thu nào". Sai im lặng, lần thứ hai.
Nên màn hình chỉ nhận giá trị có trong danh sách của chính nó.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CAY = GOC / "web" / "lib" / "cay_phan_he.ts"
WEB = GOC / "web"


def _nut_co_tham_so():
    s = CAY.read_text(encoding="utf-8")
    ra = []
    for ma, ten, href in re.findall(
            r'ma:\s*"([^"]+)",\s*ten:\s*"([^"]+)"(?:,\s*href:\s*"([^"]+)")?', s):
        if href and "?" in href:
            duong, q = href.split("?", 1)
            ra.append((ma, ten, duong.rstrip("/"), q.split("=")[0]))
    return ra


def _ma_va_component(duong: str, sau=None) -> str:
    """Mã của trang, cộng mã các component nó nhập vào (đệ quy)."""
    if sau is None:
        sau = set()
    f = WEB / "app" / duong.lstrip("/") / "page.tsx"
    return _doc(f, sau)


def _doc(f: Path, sau: set) -> str:
    if not f.exists() or f in sau:
        return ""
    sau.add(f)
    s = f.read_text(encoding="utf-8")
    for ten in re.findall(r'from\s+"@/components/([A-Za-z0-9_]+)"', s):
        s += _doc(WEB / "components" / f"{ten}.tsx", sau)
    return s


def test_tc86_1_moi_muc_co_tham_so_deu_duoc_man_hinh_doc():
    hong = []
    for ma, ten, duong, khoa in _nut_co_tham_so():
        ma_nguon = _ma_va_component(duong)
        if not ma_nguon:
            hong.append(f"{ma} {ten}: khong tim thay trang {duong}")
        elif f'"{khoa}"' not in ma_nguon and f"'{khoa}'" not in ma_nguon:
            hong.append(f"{ma} {ten}: {duong} khong doc tham so '{khoa}'")
    assert not hong, "muc hua mo dung phan nao do ma man hinh khong doc tham so:\n  " + "\n  ".join(hong)


def test_tc86_2_muc_272_van_tro_dung_luong_khach_le():
    s = CAY.read_text(encoding="utf-8")
    assert "/dong-gop-marketing?mang=le" in s, "mat tham so thi 2.7.2 lai bang 2.7.1"


def test_tc86_3_man_hinh_chi_nhan_luong_co_that():
    """Giá trị lạ phải rơi về 'cả ba luồng', không được đẩy xuống máy chủ."""
    ma = (WEB / "app" / "dong-gop-marketing" / "page.tsx").read_text(encoding="utf-8")
    assert "URLSearchParams" in ma, "man hinh khong doc duong dan"
    assert "MANG.some" in ma, "nhan bua gia tri la thi bang rong trong nhu 'khong co doanh thu'"
