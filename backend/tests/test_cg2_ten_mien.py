"""CG-2 · Bốn tên miền vietourist.vn vào thẳng đúng cổng (Chủ tịch chốt 27/10/2026).

crm → Nội bộ, kh → Khách hàng, dt → Đối tác, ir → Cổ đông. Trang đăng nhập đọc tên miền khi mở;
`?cong=` vẫn thắng; tên miền khác giữ trang bốn ô. Phép thử đọc thẳng mã nguồn web như test_cg1.
"""
import re
from pathlib import Path

TRANG = Path(__file__).resolve().parents[2] / "web" / "app" / "login" / "page.tsx"


def _src() -> str:
    return TRANG.read_text(encoding="utf-8")


def test_bon_ten_mien_dung_cong():
    s = _src()
    m = re.search(r"CONG_THEO_TEN_MIEN[^=]*=\s*\{(.*?)\};", s, re.S)
    assert m, "thiếu bảng tên miền → cổng"
    cap = dict(re.findall(r'"([a-z.]+)":\s*"(\w+)"', m.group(1)))
    assert cap == {"crm.vietourist.vn": "noi", "kh.vietourist.vn": "kh",
                   "dt.vietourist.vn": "dt", "ir.vietourist.vn": "cd",
                   # TM-1 (Chủ tịch 02/11/2026): vietourist.com.vn song song, cùng cổng
                   "crm.vietourist.com.vn": "noi", "kh.vietourist.com.vn": "kh",
                   "dt.vietourist.com.vn": "dt", "ir.vietourist.com.vn": "cd"}


def test_tham_so_cong_thang_ten_mien():
    s = _src()
    i_q, i_host = s.find('get("cong")'), s.find("CONG_THEO_TEN_MIEN[location.hostname")
    assert 0 < i_q < i_host, "?cong= phải xét trước tên miền"
    assert "else {" in s[i_q:i_host + 10]


def test_khong_xuat_khoi_trang():
    # Next.js app router không cho trang xuất tên lạ — xuất ra là next build hỏng.
    assert "export const CONG_THEO_TEN_MIEN" not in _src()
