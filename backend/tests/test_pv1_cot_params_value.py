"""PV-1 · Cột `params.value` phải đủ chỗ cho tham số CÓ THẬT — 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHUYỆN ĐÃ XẢY RA
═══════════════════════════════════════════════════════════════════════════════════════════════
Làn CSKH thêm tham số `khao_sat_mau_tin` — mẫu tin nhắn Zalo gửi khách — dài **210 ký tự**, trên
một cột khai `String(200)`. Bản ấy gộp vào main đúng lúc CI chết vì hạn mức chi tiêu GitHub
Actions, nên hàng rào K11 không kêu được. CI sống lại thì **main đỏ, và mọi nhánh của mọi làn đỏ
theo** cho tới khi có người sửa.

K11 (`test_ks_do_dai`) đã bắt đúng chuyện ấy, và bộ phép thử này KHÔNG thay nó. Nó canh một chỗ
KHÁC mà hôm nay chưa ai canh:

    mô hình nói `String(500)` nhưng KHÔNG bản nâng cấp nào nới cột

Trên SQLite (máy lập trình) thiếu bản nâng cấp vẫn chạy được, vì SQLite không ép độ dài chuỗi.
Trên PostgreSQL (máy chạy thật) thì chèn một giá trị 210 ký tự vào cột 200 là LỖI — nên cái sai
ấy im lặng suốt vòng phát triển rồi nổ đúng lúc triển khai. Đây là hình y hệt V9 đã canh cho cột
TIỀN; cột CHUỖI thì chưa ai canh.
"""
import re
from pathlib import Path

from sqlalchemy import String

from app.models.core import Param

# Tham số dài nhất đang có THẬT trong mã, đo 27/9/2026. Con số này không phải để trang trí: nếu
# một ngày nó vượt 500 thì phép thử đỏ, và câu trả lời đúng lúc ấy là "thứ này đáng lẽ phải nằm ở
# một bảng riêng", chứ không phải "nới cột thêm lần nữa".
TRAN_HOP_LY = 500


def _do_dai_cot() -> int:
    kieu = Param.__table__.columns["value"].type
    assert isinstance(kieu, String), "cột `value` không còn là chuỗi"
    return kieu.length


def test_pv1_cot_value_du_cho_cho_tham_so_dai_nhat_trong_ma():
    """Đọc THẲNG danh sách tham số trong `rules.py`, không chép lại con số vào đây.

    Chép lại là tự tạo ra một bản sao thứ hai của sự thật, và bản sao ấy sẽ cũ đi."""
    from app.services import rules as R

    dai_nhat, ten = 0, ""
    for hang in (getattr(R, t) for t in dir(R) if t.isupper()):
        if not isinstance(hang, (list, tuple)):
            continue
        for d in hang:
            if isinstance(d, (list, tuple)) and len(d) >= 2 and isinstance(d[0], str) \
                    and isinstance(d[1], str) and len(d[1]) > dai_nhat:
                dai_nhat, ten = len(d[1]), d[0]

    assert dai_nhat <= _do_dai_cot(), (
        f"tham số `{ten}` dài {dai_nhat} ký tự, cột `params.value` chỉ {_do_dai_cot()}. "
        "Nới cột bằng một bản nâng cấp, ĐỪNG cắt câu chữ cho vừa cột: bảng tham số sinh ra để câu "
        "chữ nằm ngoài mã.")


def test_pv1_co_ban_nang_cap_noi_cot_dung_bang_do_dai_mo_hinh_khai():
    """Mô hình nói 500 mà không bản nâng cấp nào nới cột thì SQLite im lặng, PostgreSQL nổ lúc
    triển khai. Cùng một hình V9 đã canh cho cột TIỀN — cột CHUỖI thì chưa ai canh."""
    dai = _do_dai_cot()
    thu_muc = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    thay = False
    for tep in thu_muc.glob("*.py"):
        s = tep.read_text(encoding="utf-8")
        if "params" not in s or "alter_column" not in s:
            continue
        # Bắt cả hai lối viết: `type_=sa.String(500)` và `type_=String(500)`.
        if re.search(rf'type_=\s*(?:sa\.)?String\(\s*{dai}\s*\)', s) and '"value"' in s:
            thay = True
    assert thay, (f"mô hình khai `params.value` là String({dai}) nhưng không bản nâng cấp nào nới "
                  f"cột lên {dai} — SQLite không ép độ dài nên chỗ này im lặng ở máy lập trình và "
                  f"nổ trên PostgreSQL lúc triển khai")


def test_pv1_khong_noi_cot_vo_han():
    """500 là trần có chủ đích. Vượt nó nghĩa là thứ đang cất vào tham số đáng lẽ phải là một bảng
    riêng — và lúc ấy câu trả lời đúng không phải là nới cột thêm lần nữa."""
    assert _do_dai_cot() <= TRAN_HOP_LY
