# -*- coding: utf-8 -*-
"""NHÃN SỐ TRÊN BIỂU ĐỒ — Chủ tịch chốt 12/10/2026.

Hai việc, hai luật, và cả hai đều là loại hỏng KHÔNG BAO GIỜ TỰ LỘ RA: màn hình vẫn chạy, hình
vẫn đẹp, chỉ là con số không còn ở đó nữa. Không có hàng rào thì lần dọn mã sau ai đó gỡ đi mà
không ai biết — đúng như `nhan_so` suýt bị gỡ hồi tháng 9.

  (1) CỘT ĐỨNG — ghi số ở BỐN cột: đầu kỳ, cuối kỳ, cao nhất, thấp nhất.
  (2) ĐƯỜNG — mỗi chấm có nhãn hiện NGAY khi rê chuột, không phải `title` của trình duyệt.

VÌ SAO KHÔNG ĐẾM SỐ NHÃN TRÊN ẢNH: không dựng được trình duyệt ở đây, và một phép thử dựng
trình duyệt cho một luật mười dòng là cái giá không đáng. Nên soi MÃ — đúng lối mọi hàng rào giao
diện khác trong kho đang dùng.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
KHOI = GOC / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"
BIEUDO = GOC / "web" / "components" / "BieuDo.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _ma(p: Path) -> str:
    """Bỏ chú thích. Một chú thích nhắc tên `bd-cham-so` KHÔNG phải là một cái nhãn."""
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ═══════════════════════════ 1 · CỘT ĐỨNG ═══════════════════════════

def test_cot_dung_ghi_so_o_ca_cao_nhat_va_thap_nhat():
    """Bốn mốc, không phải hai. Mất hai mốc mới là mất đúng câu hỏi đầu tiên của người điều hành."""
    s = _ma(KHOI)
    i = s.index("const ghi = new Set<number>()")
    khoi = s[i:i + 700]
    assert "trong[0]" in khoi, "mất nhãn cột ĐẦU kỳ"
    assert "trong[trong.length - 1]" in khoi, "mất nhãn cột CUỐI kỳ"
    # Soi PHÉP SO, không soi tên hàm: `reduce` hay vòng lặp đều được, miễn là có so cả hai chiều.
    # (Và `reduce` thì KHÔNG được — `test_tc42_sau_o_lon` cấm nó trên tệp này; lý do ghi trong mã.)
    assert re.search(r">\s*gt\(", khoi), (
        "thiếu nhãn CAO NHẤT. Chủ tịch chốt 12/10/2026: chiều cao cột cho thấy cột nào cao, nhưng "
        "không cho biết CAO BAO NHIÊU — và đó đúng là lúc người ta phải rê chuột từng cột để đọc "
        "một con số lẽ ra đã nằm sẵn trên hình.")
    assert re.search(r"<\s*gt\(", khoi), "thiếu nhãn THẤP NHẤT"
    assert "reduce(" not in khoi, (
        "`test_tc42_sau_o_lon` cấm `reduce(` trên tệp này để màn hình không tự gộp số nghiệp vụ. "
        "Viết bằng vòng lặp thường.")


def test_bon_moc_gop_bang_Set_chu_khong_phai_mang():
    """Một tháng ăn hai danh hiệu thì ra MỘT nhãn.

    Tháng 10/2026 vừa là tháng cuối có số vừa là tháng thấp nhất. Dùng mảng thì hai nhãn vẽ chồng
    khít lên nhau thành một vệt chữ không đọc nổi — và lỗi ấy chỉ lộ ra ở đúng những tháng xấu,
    tức là đúng lúc người ta cần đọc con số nhất.
    """
    s = _ma(KHOI)
    assert "const ghi = new Set<number>()" in s, (
        "`ghi` phải là Set. Đổi sang mảng là mở lại cảnh hai nhãn chồng lên nhau ở tháng vừa là "
        "cuối kỳ vừa là thấp nhất.")


def test_chon_theo_VI_TRI_cot_chu_khong_theo_so_thang():
    """Nhãn phải tự chạy theo dữ liệu, không khoá cứng vào tháng nào.

    Khoá cứng "cột cuối là T10" thì sang tháng sau, khi T11 có chuyến khởi hành, hình vẫn ghi số ở
    T10 — sai, và sai im lặng. Chọn theo VỊ TRÍ trong danh sách `trong` thì không ai phải nhớ.
    """
    s = _ma(KHOI)
    i = s.index("const ghi = new Set<number>()")
    khoi = s[i:i + 700]
    assert not re.search(r"thang\s*===?\s*\d+", khoi), \
        "đang chọn cột theo SỐ THÁNG — nhãn sẽ đứng yên khi dữ liệu đi tiếp"


# ═══════════════════════════ 2 · ĐƯỜNG ═══════════════════════════

def test_moi_cham_tren_duong_co_nhan_hien_ngay():
    s = _ma(BIEUDO)
    assert "bd-cham-so" in s, (
        "mất nhãn hiện ngay trên chấm. Chủ tịch chốt 12/10/2026: `title` của trình duyệt phải giữ "
        "chuột một giây mới hiện, và trên điện thoại thì KHÔNG BAO GIỜ hiện — tức là với người xem "
        "trên máy, con số ấy coi như không tồn tại.")
    assert "tabIndex={0}" in s, "chấm phải tới được bằng bàn phím, nếu không nhãn chỉ dành cho chuột"


def test_title_cu_KHONG_bi_go_di():
    """Giữ `title` là có chủ ý, không phải sót.

    Nó là lối đọc của trình đọc màn hình và của người rê chuột theo thói quen cũ. Bỏ nó đi là đổi
    một chỗ dở lấy một chỗ MẤT — và trình đọc màn hình thì không ai thử lại sau khi dọn mã.
    """
    s = _ma(BIEUDO)
    i = s.index('className={"bd-cham "')
    assert "title=" in s[i:i + 500], "đã gỡ mất `title` của chấm — trình đọc màn hình không còn gì để đọc"


def test_vung_bat_chuot_rong_hon_cham():
    """Chấm 9px mà bắt đúng 9px là bắt người dùng nhắm."""
    css = re.sub(r"/\*.*?\*/", " ", CSS.read_text(encoding="utf-8"), flags=re.S)
    m = re.search(r"\.bd-cham::before\{([^}]*)\}", css)
    assert m, "thiếu vùng bắt chuột `.bd-cham::before`"
    r = re.search(r"width:\s*(\d+)px", m.group(1))
    assert r and int(r.group(1)) >= 20, \
        f"vùng bắt chuột chỉ {r.group(1) if r else '?'}px — phải từ 20px trở lên"
    assert "background" not in m.group(1), "vùng bắt chuột KHÔNG được vẽ gì: nó sẽ thành một chấm to"


def test_nhan_khong_bat_chuot():
    """Nhãn bắt chuột thì hình nhấp nháy.

    Con trỏ đi từ chấm lên nhãn, nhãn chui ra khỏi vùng của chấm và tự tắt, rồi lại hiện. Lỗi này
    nhìn ra ngay nhưng rất dễ dựng lại lúc dọn CSS, nên canh nó bằng một dòng.
    """
    css = re.sub(r"/\*.*?\*/", " ", CSS.read_text(encoding="utf-8"), flags=re.S)
    m = re.search(r"\.bd-cham-so\{([^}]*)\}", css)
    assert m, "thiếu định dạng `.bd-cham-so`"
    assert "pointer-events:none" in m.group(1).replace(" ", ""), \
        "nhãn phải `pointer-events:none`, nếu không hình sẽ nhấp nháy khi rê chuột"
    assert "visibility:hidden" in m.group(1).replace(" ", ""), (
        "nhãn phải ẩn bằng cả `visibility`, không chỉ `opacity`: chỉ mờ đi thì nó vẫn chiếm chỗ và "
        "vẫn bị trình đọc màn hình đọc.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 12/10/2026 · NS-2 — MỌI HÌNH CỘT ĐỨNG: BỐN SỐ CỐ ĐỊNH, CÁC THÁNG CÒN LẠI RÊ CHUỘT
#
# Chủ tịch, sau khi thấy hình Lợi nhuận từng tháng không có lấy một con số trong khi hình Doanh
# thu ngay trên nó có bốn: "trong các biểu đồ đứng em chọn 4 con số hiển thị, ngoài ra các tháng
# khác em thêm phần rê chuột hoặc chạm vào sẽ hiện ra."
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_hinh_hai_cot_KHONG_con_bi_cam_ghi_so():
    """Luật cũ `!ten_cot2` đã bỏ — nhưng bỏ bằng cách CHỮA, không phải bằng cách lờ đi.

    Luật cũ đúng ở chỗ nó sợ: hai con số cố định trên một tháng rộng hai chục pixel thì chồng
    nhau. Nó sai ở cách chữa — bỏ CẢ HAI, nên hình lợi nhuận trắng trơn. Cách chữa mới giữ được
    nỗi sợ ấy: ghi số cho đúng MỘT cột, và canh nhãn lệch sang tâm cột chính.
    """
    s = _ma(BIEUDO)
    i = s.index('{ghiSo &&')
    khoi = s[i:i + 260]
    assert "!ten_cot2" not in khoi, (
        "`!ten_cot2` quay lại trong điều kiện ghi nhãn — hình Lợi nhuận từng tháng sẽ trắng trơn "
        "trở lại, đúng chỗ Chủ tịch nêu ngày 12/10/2026.")
    assert 'ten_cot2 ? " trai"' in khoi, (
        "hình hai cột phải canh nhãn LỆCH sang cột chính. Căn giữa ô tháng thì nhãn rơi đúng vào "
        "KHE giữa hai cây cột, và người đọc không biết con số ấy nói về cột nào.")


def test_nhan_lech_co_dinh_dang_rieng():
    css = re.sub(r"/\*.*?\*/", " ", CSS.read_text(encoding="utf-8"), flags=re.S)
    assert re.search(r"\.bd-so\.trai\{[^}]*right:\s*calc\(50%", css), (
        "thiếu `.bd-so.trai` kéo mép phải về giữa ô — không có nó thì lớp `trai` không làm gì, và "
        "nhãn vẫn rơi vào khe giữa hai cột.")


def test_moi_thang_deu_co_nhan_re_chuot_ke_ca_thang_TRONG():
    """Tháng trống cũng phải có nhãn, và nó nói "chưa có số" chứ không nói 0.

    Bỏ nhãn ở tháng trống thì rê vào tháng 11 không ra gì — và người dùng không phân biệt được
    "hình hỏng" với "tháng chưa có số". Hai việc khác hẳn nhau.
    """
    s = _ma(BIEUDO)
    assert s.count('className="bd-cot-so') >= 2, (
        "phải có nhãn rê chuột cho CẢ hai nhánh: tháng có số và tháng trống")
    assert "chưa có số" in s, "tháng trống phải nói “chưa có số”, không được để trống hoặc hiện 0"


def test_nhan_re_chuot_liet_ke_du_cac_con_so_CUA_THANG():
    """Cột chính, khúc chờ, cột thứ hai — mỗi thứ một dòng, và KHÔNG cộng lại.

    Khúc chờ là doanh thu của chuyến chưa có giá vốn. Cộng nó vào con số đọc được là nói quá
    doanh thu đã ghi nhận — đúng cái bẫy `ket_qua_kinh_doanh.py` ghi lại ngày 08/10/2026.
    """
    s = _ma(BIEUDO)
    i = s.index('className="bd-cot-so" aria-hidden')
    khoi = s[i:i + 420]
    assert "cho > 0 &&" in khoi, "nhãn phải nói ra khúc chờ khi tháng ấy có khúc chờ"
    assert "g2 !== null &&" in khoi, "nhãn phải nói ra cột thứ hai khi hình có cột thứ hai"
    assert not re.search(r"d\.gt\s*\+\s*d\.cho", khoi), (
        "nhãn đang CỘNG khúc chờ vào cột chính — con số đọc được sẽ to hơn doanh thu đã ghi nhận")


def test_o_thang_toi_duoc_bang_ban_phim():
    s = _ma(BIEUDO)
    assert s.count("tabIndex={0}") >= 3, (
        "cả ô tháng có số, ô tháng trống và chấm trên đường đều phải tới được bằng Tab — nếu "
        "không, nhãn rê chuột chỉ dành cho người dùng chuột")


def test_nhan_cot_khong_bat_chuot_va_an_han_hoi():
    css = re.sub(r"/\*.*?\*/", " ", CSS.read_text(encoding="utf-8"), flags=re.S)
    m = re.search(r"\.bd-cot-so\{([^}]*)\}", css)
    assert m, "thiếu định dạng `.bd-cot-so`"
    than = m.group(1).replace(" ", "")
    assert "pointer-events:none" in than, "nhãn bắt chuột thì hình nhấp nháy khi con trỏ đi lên nó"
    assert "visibility:hidden" in than, (
        "ẩn bằng mỗi `opacity` thì trình đọc màn hình vẫn đọc đủ mười hai nhãn đang ẩn")
