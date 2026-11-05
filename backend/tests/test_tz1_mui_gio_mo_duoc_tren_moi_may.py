# -*- coding: utf-8 -*-
"""Đợt TZ-1 06/11/2026 — MỌI MÚI GIỜ HỆ THỐNG DÙNG PHẢI MỞ ĐƯỢC TRÊN MỌI MÁY.

HAI CÁI HÀNG RÀO ĐANG NÓI HAI CHUYỆN KHÁC NHAU, VÀ ĐÓ MỚI LÀ VẤN ĐỀ.

`app/services/ops.py` có `gio_vn()`, và hàm ấy gọi `ZoneInfo("Asia/Ho_Chi_Minh")`. Hàm viết
đúng — nó sinh ra ở Đợt KS-18 chính vì máy chủ từng chạy sai múi giờ, nên nó KHÔNG hỏi đồng hồ
máy. Nhưng `zoneinfo` của Python không mang theo bảng múi giờ: nó đi tìm bảng của hệ điều hành,
và nếu không thấy thì tìm gói `tzdata`.

  - Máy Linux của CI có bảng ấy sẵn  → `test_ops.py` XANH.
  - Máy Windows của Chủ tịch không có, và `tzdata` chưa được khai trong requirements → ĐỎ.

Nên cùng một dòng mã, cùng một commit, hai câu trả lời. Cái hàng rào chạy trước khi đẩy (bản
`.bat` trên máy Chủ tịch) là cửa thật — nó mà nói sai thì người bấm học cách bỏ qua màu đỏ, và
đó là lúc một cái đỏ THẬT đi lọt.

CÁCH SỬA LÀ MANG BẢNG MÚI GIỜ THEO MÃ, không phải dặn người ta cài tay: `tzdata` vào
`requirements.txt`, nên mọi máy — máy Chủ tịch, máy CI, máy chạy thật — đọc cùng một bảng.

LUẬT 1 TỰ ĐI TÌM, KHÔNG GÕ TAY DANH SÁCH. Bài học trả giá ba lần hôm 05/11: một phép đo tự liệt
kê nguồn sẽ bỏ sót, và bỏ sót thì nói ÍT hơn sự thật chứ không nói sai — nên nó không tự kêu lên.
"""
import datetime as _dt
import os
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

os.environ["DATABASE_URL"] = "sqlite:///./test_tz1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HAU_PHUONG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # backend/
GOC = os.path.dirname(HAU_PHUONG)
YEU_CAU = os.path.join(HAU_PHUONG, "requirements.txt")

# Tìm lời gọi `ZoneInfo` có khoá viết thẳng trong mã nguồn.
#
# BẢN ĐẦU CỦA KHUÔN NÀY TỰ BẮT CHÍNH LỜI CHÚ CỦA NÓ, và em đã tưởng là không. Chạy thử trên một
# cây giả 06/11/2026: dòng chú thích cũ ở đây viết ví dụ bằng ba dấu chấm, phép quét nhặt ba dấu
# chấm ấy thành một «khoá múi giờ» rồi báo đỏ về một thứ không có thật. Một luật đỏ vì chính nó
# thì người đọc sẽ học cách bỏ qua nó.
#
# Hai việc sửa, và cần cả hai:
#   - trong tệp này không viết ví dụ bằng khoá giả nữa (dùng dấu « » như dưới đây);
#   - và một cái rào hẹp: khoá múi giờ thật chỉ gồm chữ, số, `_`, `+`, `-`, `/`. Rào hẹp thế này
#     loại được ví dụ hỏng mà không loại nhầm một khoá thật nào — `UTC` không có gạch chéo vẫn
#     lọt, `Asia/Ho_Chi_Minh` vẫn lọt.
KHUON = re.compile(r"ZoneInfo\(\s*[\"']([^\"']+)[\"']")
KHOA_THAT = re.compile(r"^[A-Za-z0-9_+/-]+$")

# Thư mục KHÔNG quét: không phải mã của hệ thống.
BO_QUA = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", "_rac_khong_xoa_duoc"}


def _tep_python():
    for goc, thu_muc, tep in os.walk(HAU_PHUONG):
        thu_muc[:] = [t for t in thu_muc if t not in BO_QUA]
        for t in tep:
            if t.endswith(".py"):
                yield os.path.join(goc, t)


def _cac_mui_gio():
    """{khoá múi giờ: [chỗ dùng]} — ĐI TÌM, không gõ tay."""
    ra = {}
    for duong in _tep_python():
        try:
            noi_dung = open(duong, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for i, dong in enumerate(noi_dung.split("\n"), 1):
            for khoa in KHUON.findall(dong):
                if not KHOA_THAT.match(khoa):
                    continue
                ra.setdefault(khoa, []).append(
                    os.path.relpath(duong, GOC).replace("\\", "/") + ":" + str(i))
    return ra


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_tz1_1_moi_mui_gio_he_thong_dung_deu_mo_duoc_tren_may_nay():
    """Mọi khoá múi giờ có trong mã PHẢI mở được NGAY TRÊN MÁY ĐANG CHẠY.

    Đỏ ở đây không có nghĩa là ai viết sai mã. Nó có nghĩa là máy này thiếu bảng múi giờ — và
    nếu nó thiếu thì phần mềm chạy trên nó cũng sẽ ngã đúng chỗ ấy, chỉ là ngã lúc có người dùng
    thật chứ không phải lúc chạy phép thử.
    """
    cho_dung = _cac_mui_gio()
    # Phép đo trống rỗng không được tính là phép đo đạt. Nếu một ngày nào đó không còn chỗ nào
    # gọi `ZoneInfo` nữa thì đây là một quyết định, phải nói ra ở sổ, chứ không phải một luật
    # lặng lẽ xanh vì không tìm thấy gì.
    assert cho_dung, (
        "KHÔNG tìm thấy chỗ nào gọi `ZoneInfo` với khoá viết thẳng trong backend — hoặc hệ thống đã bỏ hết "
        "múi giờ (phải nói ra ở sổ), hoặc phép quét này đã hỏng. Cả hai đều phải nhìn.")
    hong = []
    for khoa, cho in sorted(cho_dung.items()):
        try:
            ZoneInfo(khoa)
        except (ZoneInfoNotFoundError, ValueError) as e:
            hong.append("   " + khoa + "  (" + type(e).__name__ + ")\n      " + "\n      ".join(cho))
    assert not hong, (
        "MÁY NÀY KHÔNG MỞ ĐƯỢC " + str(len(hong)) + " MÚI GIỜ MÀ HỆ THỐNG ĐANG DÙNG:\n"
        + "\n".join(hong) +
        "\n\nNghĩa là bảng múi giờ không có mặt ở đây. Cách xử: `tzdata` phải nằm trong "
        "`backend/requirements.txt` VÀ đã được cài trên máy này (`pip install -r "
        "requirements.txt`). ĐỪNG đổi `ZoneInfo` sang giờ máy để hết đỏ — giờ máy là đúng thứ "
        "Đợt KS-18 đã bỏ đi vì máy chủ từng chạy sai múi giờ.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_tz1_2_bang_mui_gio_duoc_mang_theo_ma_chu_khong_dan_nguoi_ta_cai_tay():
    """`tzdata` phải được KHAI trong requirements, và phải NHẬP ĐƯỢC.

    Hai vế chứ không một. Khai mà không cài thì máy vẫn ngã; cài tay mà không khai thì máy sau
    lại ngã, và không ai biết vì sao máy này chạy được còn máy kia không.
    """
    assert os.path.exists(YEU_CAU), "khong thay backend/requirements.txt"
    dong = [d.split("#")[0].strip()
            for d in open(YEU_CAU, encoding="utf-8").read().split("\n")]
    assert any(re.match(r"(?i)^tzdata\b", d) for d in dong), (
        "`tzdata` chưa được khai trong `backend/requirements.txt`. Thiếu nó thì máy nào không "
        "có bảng múi giờ của hệ điều hành — Windows là một — sẽ đỏ, trong khi CI chạy Linux vẫn "
        "xanh. Hai cái hàng rào nói hai chuyện là lúc người bấm học cách bỏ qua màu đỏ.")
    try:
        import tzdata  # noqa: F401
    except ImportError:
        raise AssertionError(
            "`tzdata` đã khai trong requirements nhưng CHƯA CÀI trên máy này. Chạy "
            "`pip install -r backend/requirements.txt` rồi bấm lại.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_tz1_3_gio_vn_tra_ve_DUNG_gio_viet_nam_chu_khong_chi_la_khong_nga():
    """Không ngã chưa phải là đúng. Luật này đo con số.

    Việt Nam là UTC+7 quanh năm, không có giờ mùa hè — nên phép so này không có ngày nào lệch.
    Và nó đo rằng `gio_vn()` KHÔNG hỏi đồng hồ máy: dù máy đặt múi giờ nào, kết quả vẫn là UTC+7.
    """
    from app.services.ops import gio_vn
    ra = gio_vn()
    assert ra.tzinfo is None, (
        "`gio_vn()` phải trả về giờ TRẦN (naive) — cả hệ thống ghi sổ bằng giờ trần, một chỗ trả "
        "về giờ có múi sẽ làm phép trừ hai mốc thời gian nổ ở chỗ khác.")
    mong = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) + _dt.timedelta(hours=7)
    lech = abs((ra - mong).total_seconds())
    assert lech < 5, (
        "`gio_vn()` trả về " + ra.isoformat() + " nhưng giờ Việt Nam (UTC+7) là "
        + mong.isoformat() + " — lệch " + str(round(lech)) + " giây. Hoặc nó đang hỏi đồng hồ "
        "máy (đúng thứ Đợt KS-18 đã bỏ đi), hoặc bảng múi giờ trên máy này sai.")
