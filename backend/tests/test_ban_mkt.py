# -*- coding: utf-8 -*-
"""MKT-1 · HÀNG RÀO CỦA HAI BÀN MARKETING — 09/11/2026.

Bốn điều đợt này hứa, và bốn phép thử dưới đây là chỗ đo chúng. Lời hứa không có phép thử đi kèm
thì nó chỉ đúng vào ngày người viết còn nhớ.

  1. BÀN KHÔNG CÓ CỬA GHI. Mọi ô chỉ dẫn sang màn hình nguồn.
  2. MỖI Ô DẪN TỚI MỘT TAB CÓ THẬT của màn `/marketing` — và tab ấy phải còn đó.
  3. BÀN NHÂN VIÊN CẮT THEO NGƯỜI GIỮ LEAD, không trả về cả phòng.
  4. HAI MÀN MỚI KHÔNG NỚI PHẠM VI CỦA AI — danh sách vai của chúng nằm gọn trong `/marketing`.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DICH_VU = GOC / "backend" / "app" / "services" / "ban_mkt.py"
CUA = GOC / "backend" / "app" / "api" / "v1" / "ban_mkt.py"
TRANG_MKT = GOC / "web" / "app" / "marketing" / "page.tsx"


def _ma(p: Path) -> str:
    """Bỏ chú thích và chuỗi tài liệu: một dòng chú thích nhắc `db.add` không phải là một cửa ghi."""
    src = p.read_text(encoding="utf-8")
    src = re.sub(r'(?s)""".*?"""', " ", src)
    src = re.sub(r"^\s*#.*$", " ", src, flags=re.M)
    return src


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · BÀN KHÔNG CÓ CỬA GHI
# ══════════════════════════════════════════════════════════════════════════════════════════════

GHI = ("db.add(", "db.commit(", "db.delete(", "db.flush(", ".post(", ".put(", ".patch(", ".delete(")


def test_ban_marketing_khong_co_cua_ghi():
    """Một bàn làm việc ghi được thì nó thôi là bàn làm việc.

    Luật này không phải của riêng đợt MKT-1: bộ máy bàn làm việc 12/10/2026 đã đặt nó, và lý do
    viết ở đó — duyệt hàng loạt từ một bảng tổng là thứ khó lùi nhất. Phép thử này giữ cho hai bàn
    Marketing không lặng lẽ mọc một nút duyệt vào một buổi chiều nào đó.
    """
    hong = []
    for p in (DICH_VU, CUA):
        src = _ma(p)
        for g in GHI:
            if g in src:
                hong.append(f"{p.name} có {g}")
    assert not hong, (
        "Bàn Marketing mọc cửa ghi: " + "; ".join(hong) +
        ". Bàn chỉ ĐỌC. Việc ghi đã có cửa riêng trên bảy tab của màn /marketing, với hàng rào của "
        "chúng — dựng cửa ghi thứ hai ở đây là tạo bản sao thứ hai của một luật, và bản sao nào rồi "
        "cũng lệch.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · MỖI Ô DẪN TỚI MỘT TAB CÓ THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _tab_cua_man_marketing() -> set[str]:
    """Đọc THẲNG danh sách tab từ màn hình, không chép tay sang đây.

    Chép tay thì ngày ai đó đổi tên một tab, bảng chép vẫn đúng và phép thử vẫn xanh, còn người
    bấm vào ô trên bàn thì rơi vào một tab không tồn tại.
    """
    src = TRANG_MKT.read_text(encoding="utf-8")
    khoi = re.search(r"const TABS[^=]*=\s*\[(.*?)\n\];", src, re.S)
    assert khoi, "không đọc được bảng TABS của web/app/marketing/page.tsx"
    return set(re.findall(r'\[\s*"([a-z0-9_]+)"', khoi.group(1)))


def _bi_danh_cua_man_marketing(tab: set[str]) -> set[str]:
    """MKT-11 · 12/11/2026 — ĐỌC THÊM PHÉP ÁNH XẠ `?tab=`, cũng THẲNG từ màn hình.

    Không phải mọi đường dẫn `?tab=` hợp lệ đều là một tab. Màn `/marketing` nhận
    `?tab=ngansach` rồi mở tab `chiendich` với ngăn `ngansach` — một đường dẫn sâu hai chiều,
    và chính thanh menu của công ty đang dùng nó: dòng «Kế hoạch & ngân sách» trong
    `components/Shell.tsx`, mà `test_menu.py` canh từng ký tự. Đọc mỗi bảng `TABS` thì hàng
    rào này chặn cả đường dẫn menu ấy.

    ĐỌC, KHÔNG CHÉP TAY — vì lý do hàm ngay trên đã viết: một bảng chép tay vẫn đúng vào
    ngày người ta đổi tên, và lúc ấy phép thử xanh còn người bấm rơi vào trang trống.

    VÀ SIẾT THÊM MỘT CHỖ: bí danh phải dẫn tới một tab CÓ THẬT. Trước 12/11/2026 không ai
    canh điều này, nên một bí danh trỏ vào tab đã đổi tên sẽ im lặng cho tới khi có người bấm.
    """
    src = TRANG_MKT.read_text(encoding="utf-8")
    cap = re.findall(
        r'if\s*\(\s*url\s*===\s*"([a-z0-9_]+)"\s*\)\s*\{\s*setTab\(\s*"([a-z0-9_]+)"\s*\)', src)
    lac = sorted({den for _, den in cap if den not in tab})
    assert not lac, (
        "Bí danh ?tab= của màn Marketing dẫn tới tab KHÔNG CÓ: " + ", ".join(lac) +
        f". Tab đang có: {', '.join(sorted(tab))}. Bí danh trỏ vào chỗ không có thì người bấm "
        "menu rơi vào trang trống, và không ai biết cho tới khi có người bấm.")
    return {bi for bi, _ in cap}


def test_moi_o_dan_toi_mot_tab_co_that():
    tab = _tab_cua_man_marketing()
    assert len(tab) >= 5, (
        f"chỉ đọc được {len(tab)} tab của màn Marketing — nghi là cách đọc bảng TABS đã hỏng, "
        "và một hàng rào quét trúng tập rỗng thì luôn xanh")

    src = _ma(DICH_VU)
    den = re.findall(r'"/marketing\?tab=([a-z0-9_]+)"', src)
    assert den, "không ô nào khai đường dẫn sang màn Marketing — bàn không có cửa đi thì nó là một bảng tin"

    # MKT-11 · 12/11/2026 — chỗ tới được gồm TAB và BÍ DANH, cả hai đọc thẳng từ màn hình.
    den_duoc = tab | _bi_danh_cua_man_marketing(tab)

    lac = sorted({t for t in den if t not in den_duoc})
    assert not lac, (
        "Các ô sau dẫn tới chỗ KHÔNG CÓ trên màn Marketing: " + ", ".join(lac) +
        f". Tab đang có: {', '.join(sorted(tab))}."
        f" Bí danh ?tab= đang có: {', '.join(sorted(den_duoc - tab)) or 'không có'}."
        " Hoặc sửa ô, hoặc tab đã bị đổi tên và phải sửa theo — đừng để người bấm vào ô rơi "
        "vào một trang trống.")


def test_moi_o_viec_deu_co_mot_cua_di_toi():
    """Ô không có cửa đi là một con số người đọc không làm gì được với nó.

    Đếm thô nhưng đủ: mỗi hàm dựng ô kết thúc bằng một `return _o(`, và mỗi ô phải có đúng một
    đường dẫn sang màn Marketing. Hai con số lệch nhau nghĩa là có ô mọc ra mà quên cửa.
    """
    src = _ma(DICH_VU)
    # Chỉ đếm ô THẬT: ô lỗi dựng trong `_chay` truyền khoá bằng BIẾN, nên nó không khớp mẫu này —
    # và đó là chủ ý, ô lỗi không có cửa đi vì chưa đọc được nó là việc gì.
    so_o = len(re.findall(r'_o\(\s*"', src))
    so_cua = len(re.findall(r'"/marketing\?tab=', src))
    assert so_o >= 5, f"chỉ thấy {so_o} ô — nghi là cách đọc đã hỏng"
    assert so_o == so_cua, (
        f"{so_o} ô nhưng chỉ {so_cua} cửa đi. Ô nào thiếu cửa thì người đọc thấy một con số rồi "
        "đứng đó — bàn làm việc phải đưa được người ta tới chỗ làm việc.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · BÀN NHÂN VIÊN CẮT THEO NGƯỜI GIỮ LEAD
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_o_lead_cat_theo_nguoi_dang_xem():
    """Chủ tịch chốt 09/11/2026: ô lead đếm ĐÚNG lead người đang xem giữ.

    Bỏ điều kiện `Lead.sales_id` đi thì bàn vẫn chạy, vẫn ra một con số trông hợp lý, và nhân viên
    sẽ đọc việc của cả phòng như việc của mình. Đó đúng là loại hỏng không ai phát hiện ra bằng mắt,
    nên nó cần một phép thử.
    """
    src = _ma(DICH_VU)
    assert "Lead.sales_id == u.id" in src, (
        "Ô «Lead nằm im quá hạn tôi giữ» không còn cắt theo `Lead.sales_id == u.id`. Bàn trả lời "
        "câu «sáng nay TÔI phải làm gì»; một con số gồm cả lead người khác giữ là con số người "
        "ngồi bàn không làm gì được với nó.")
    assert "LD.dem_qua_han(" in src, (
        "Ô lead không còn gọi `leads.dem_qua_han`. Định nghĩa «quá hạn» đã được dọn về một mối "
        "ngày 18/9/2026 — viết lại phép tính hạn ở đây là dựng chỗ thứ hai để hai bên lệch nhau.")


def test_o_mau_so_khong_cong_vao_tong():
    """«Chiến dịch đang chạy» là mẫu số để đọc bốn ô trên, không phải việc phải làm.

    Cộng nó vào tổng thì con số trên bàn nói sai, và một con số nói sai thì lần sau không ai tin
    con số trên bàn mình nữa.
    """
    from app.services import ban_mkt as S
    assert "chien_dich_dang_chay" in S.MAU_SO


def test_ky_truoc_khong_nhay_sang_thang_dang_chay():
    """Ô «kỳ chưa chốt số» hỏi về tháng ĐÃ ĐÓNG. Lỗi lệch tháng ở đây là loại hỏng vĩnh viễn số
    liệu của một kỳ — đúng cái `lich_chup.py` đã ghi lại ngày 16/9/2026."""
    from datetime import date

    from app.services import ban_mkt as S
    assert S.ky_truoc(date(2026, 1, 9)) == "2025-12"
    assert S.ky_truoc(date(2026, 11, 9)) == "2026-10"
    assert S.ky_truoc(date(2026, 3, 1)) == "2026-02"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · HAI MÀN MỚI KHÔNG NỚI PHẠM VI CỦA AI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_hai_ban_nam_gon_trong_vai_cua_man_marketing():
    """Đây là CẢ LẬP LUẬN của việc không dựng tiền tố API mới, nên nó phải đo được.

    Hai bàn gắn vào `/api/v1/marketing` thay vì mở một nhóm API riêng. Cách ấy không nới quyền của
    ai — nhưng chỉ ĐÚNG CHỪNG NÀO danh sách vai của hai bàn còn nằm gọn trong danh sách vai của
    `/marketing`. Ngày ai đó thêm một vai vào bàn mà quên thêm vào `/marketing`, vai ấy mở được màn
    hình và nhận 403 ở mọi ô — hoặc tệ hơn, có người sẽ "sửa" bằng cách mở rộng nhóm API.
    """
    from app.api.v1 import ban_mkt as C
    from app.services import access as AC

    cua_man = set(AC.MENU_ROLES["/marketing"])
    for ten, ds in (("XEM_PTGD", C.XEM_PTGD), ("XEM_NV", C.XEM_NV)):
        du = sorted(set(ds) - cua_man)
        assert not du, (
            f"{ten} có vai KHÔNG nằm trong danh sách vai của màn `/marketing`: {du}. "
            "Hai bàn dùng chung nhóm API `/api/v1/marketing` đúng vì mọi vai của chúng đã có nhóm "
            "ấy từ trước. Thêm một vai ngoài danh sách là làm lập luận ấy hết đúng — hoặc thêm vai "
            "vào dòng `/marketing`, hoặc dựng nhóm API riêng và ký lại phạm vi của MỌI vai.")
