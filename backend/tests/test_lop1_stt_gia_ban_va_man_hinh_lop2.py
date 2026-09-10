# -*- coding: utf-8 -*-
"""Lớp 1 thêm STT và Giá bán; màn hình lớp 2 gắn vào /lai-lo-tour chứ không dựng màn hình mới.

Ba phép thử ở đây đọc MÃ NGUỒN chứ không chạy hàm, vì thứ chúng canh là quyết định thiết kế, không
phải giá trị trả về:

  * STT do máy chủ đánh, tính từ đầu bảng – màn hình tự đánh số thì trang 3 lại bắt đầu từ 1.
  * Giá bán không được suy ra bằng doanh thu chia số khách – đó là một con số không có trong bảng
    giá nào và không ai đối chiếu được.
  * Màn hình chỉ dùng lớp CSS có thật.

Mọi phép thử đọc mã giao diện đều BỎ CHÚ THÍCH trước khi so khớp. Ngày 09/9 hai đột biến lọt qua vì
phép thử đọc cả tệp kèm chú thích, mà chú thích lại nhắc đúng tên định danh vừa bị xoá khỏi mã.
"""
import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web" / "app"
BE = GOC / "backend" / "app"


def _ma(src: str) -> str:
    """Bỏ chú thích //, /* */ và {/* */} để phép thử soi MÃ chứ không soi lời kể về mã."""
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _py(p: Path) -> str:
    src = p.read_text(encoding="utf-8")
    src = re.sub(r'"""RAW"""', " ", src)
    src = re.sub(r'"""(?:.|\n)*?"""', " ", src)
    src = re.sub(r"^\s*#.*$", " ", src, flags=re.M)
    return src


@pytest.mark.skipif(not (BE / "services" / "lai_lo_tour.py").exists(), reason="chưa có kho mã")
def test_stt_do_may_chu_danh_va_tinh_tu_dau_bang():
    """Trang 3 phải bắt đầu ở 401, không phải ở 1.

    Đây là chỗ sai rất dễ mắc và rất khó thấy: bảng có phân trang thật (1.258 tour, mỗi trang 200),
    nên đánh số ở màn hình thì mỗi trang lại từ 1 và người đọc tưởng bảng chỉ có 200 dòng.
    """
    src = _py(BE / "services" / "lai_lo_tour.py")
    assert re.search(r'enumerate\(rows,\s*start=bo_qua\s*\+\s*1\)', src), \
        "STT phải đánh từ bo_qua + 1, không phải từ 1"
    assert re.search(r'r\["stt"\]\s*=', src), "STT phải do máy chủ đặt vào từng dòng"


@pytest.mark.skipif(not (BE / "services" / "lai_lo_tour.py").exists(), reason="chưa có kho mã")
def test_gia_ban_khong_duoc_suy_ra_bang_doanh_thu_chia_so_khach():
    """Giá bán là giá NIÊM YẾT, không phải doanh thu bình quân đầu khách.

    Chuyến Nha Trang 10/07/2026: 33 người lớn 1.790.000 và 7 trẻ em 1.500.000, cộng phụ thu và
    charge huỷ. Chia doanh thu cho số khách ra 1.694.404 – một con số không nằm trong bảng giá nào,
    không tra được, và trông đủ hợp lý để không ai nghi ngờ. Rỗng thì người ta đi hỏi; một con số sai
    thì người ta dùng luôn.
    """
    src = _py(BE / "services" / "lai_lo_tour.py")
    dong_gia_ban = [l for l in src.splitlines() if '"gia_ban"' in l]
    assert dong_gia_ban, "lớp 1 phải có cột giá bán"
    ghep = " ".join(dong_gia_ban)
    assert "price_per_pax" in ghep, "giá bán lấy từ giá khai của tour"
    assert "/" not in ghep.split("price_per_pax")[0].split('"gia_ban"')[-1], \
        "không được chia gì ra để có giá bán"
    assert "so_khach" not in ghep, "giá bán không được dính tới số khách"


@pytest.mark.skipif(not (WEB / "lai-lo-tour" / "page.tsx").exists(), reason="chưa có kho mã")
def test_man_hinh_khong_tu_danh_lai_so_thu_tu():
    """Màn hình hiển thị STT của máy chủ, không dùng chỉ số vòng lặp.

    Dùng index của .map() thì đúng ở trang 1 và sai ở mọi trang sau – kiểu sai chỉ lộ ra khi dữ liệu
    nhiều hơn một trang, tức là lộ ra ở khách hàng chứ không ở máy người viết.
    """
    src = _ma((WEB / "lai-lo-tour" / "page.tsx").read_text(encoding="utf-8"))
    assert "{r.stt}" in src, "phải hiện STT do máy chủ trả về"
    hang_stt = [l for l in src.splitlines() if "r.stt" in l]
    for l in hang_stt:
        assert "index" not in l and "+ 1" not in l, f"màn hình tự đánh số: {l.strip()}"


@pytest.mark.skipif(not (WEB / "lai-lo-tour" / "page.tsx").exists(), reason="chưa có kho mã")
def test_man_hinh_chi_dung_lop_css_co_that():
    """Lớp CSS bịa ra thì không lỗi, không cảnh báo – nó chỉ lặng lẽ không có tác dụng.

    Bản đầu của khối lớp 2 ngày 10/9 dùng ba lớp không tồn tại: 'warn-box' để đóng khung phát hiện,
    'bold' cho dòng tổng, và Tag 'green'. Trang vẫn chạy, vẫn hiện đủ số, chỉ có điều mọi dấu hiệu
    cảnh báo đều biến mất – tức là hỏng đúng phần mà khối ấy sinh ra để làm.

    Phép thử này đọc globals.css và bắt mọi lớp không có mặt trong đó. Nó cũng tha những lớp đã dùng
    từ trước (modal, box, row...) vì chúng được khai ở nơi khác – không mở rộng phạm vi sang mã của
    người khác, chỉ canh phần mình thêm vào.
    """
    css = (WEB / "globals.css").read_text(encoding="utf-8")
    src = _ma((WEB / "lai-lo-tour" / "page.tsx").read_text(encoding="utf-8"))

    # Tag chỉ có bốn lớp trong globals.css. Bất cứ cls nào khác đều ra thẻ trơn, không màu.
    hop_le_tag = {"ok", "warn", "red", "navy", ""}
    for cls in re.findall(r'<Tag cls="([a-z]*)"', src):
        assert cls in hop_le_tag, f'Tag cls="{cls}" không có trong globals.css'
    for cls in re.findall(r'<Tag cls=\{[^}]*\?\s*"([a-z]+)"', src):
        assert cls in hop_le_tag, f'Tag cls="{cls}" không có trong globals.css'

    # Ba lớp đã dùng sai một lần rồi – canh đích danh để không quay lại.
    for xau in ("warn-box", 'className="bold"', '<Tag cls="green"'):
        assert xau not in src, f"lớp không tồn tại: {xau}"

    assert ".gate" in css, "khối cảnh báo dùng .gate – lớp cảnh báo sẵn có của hệ thống"
    assert 'className="gate fail"' in src


@pytest.mark.skipif(not (WEB / "lai-lo-tour" / "page.tsx").exists(), reason="chưa có kho mã")
def test_khong_dung_them_mot_man_hinh_quyet_toan_thu_hai():
    """Bốn mặt của bản quyết toán phải nằm TRONG màn hình lãi lỗ, không thành trang riêng.

    lai_lo_tour.py sinh ra ngày 09/9 vì VTOS có bốn công thức lãi lỗ tour chạy song song cho ra bốn
    con số khác nhau. Một trang quyết toán hai lớp riêng là công thức thứ năm – và khó thấy hơn cả
    bốn cái trước, vì hai trang sẽ trông giống hệt nhau.
    """
    assert not (WEB / "quyet-toan-tour").exists(), \
        "không dựng trang quyết toán riêng – bốn mặt gắn vào /lai-lo-tour"
    src = _ma((WEB / "lai-lo-tour" / "page.tsx").read_text(encoding="utf-8"))
    assert "quyet_toan_dieu_hanh" in src
    assert "BanQuyetToan" in src
    # Bốn mặt, đủ cả bốn: thiếu mặt nào là mất hẳn một loại câu hỏi trả lời được.
    for mat in ("khach", "chiet_tinh", "hdv", "booking"):
        assert f'"{mat}"' in src, f"thiếu mặt {mat}"
    assert "mst_ncc" in src, "mặt chiết tính phải hiện MST – đó là lý do nó tồn tại"
