# -*- coding: utf-8 -*-
"""PQ-2 · Thẻ "Luồng công việc" trên /access và bản Excel để ký.

Bảng LUONG_VIEC dựng ở PQ-1 chỉ có giá trị khi người có thẩm quyền NHÌN được nó. Một bảng đúng mà
không ai mở ra thì vẫn không trả lời được câu kiểm toán hỏi.

Phép thử đọc mã giao diện đều BỎ CHÚ THÍCH trước khi so khớp – ngày 09/9 hai đột biến lọt qua vì
phép thử đọc cả chú thích, mà chú thích lại nhắc đúng tên định danh vừa bị xoá khỏi mã.
"""
import re
from pathlib import Path

import pytest

from app.services import luong_viec as LV
from app.services import luong_viec_bao_cao as BC

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web" / "app" / "access" / "page.tsx"
API = GOC / "backend" / "app" / "api" / "v1" / "access.py"


def _khoi_hien_thi(src: str) -> str:
    """Chỉ phần VẼ RA MÀN HÌNH của thẻ, không phải phần nạp dữ liệu trong useEffect.

    Bản đầu cắt từ lần xuất hiện ĐẦU TIÊN của `tab === "luongviec"` – mà lần đầu tiên lại nằm ở
    useEffect, nên khối cắt được chỉ dài hai dòng và mọi phép so bên trong nó đều xanh vì không có
    gì để so. Một phép thử xanh vì không nhìn thấy gì thì vô dụng, và nó còn tệ hơn: nó làm người
    đọc tưởng chỗ ấy đã được canh.
    """
    dau = src.find('{tab === "luongviec" && lv && <>')
    assert dau > 0, "không tìm thấy khối hiển thị của thẻ Luồng công việc"
    cuoi = src.find('{tab === "gaps"', dau)
    assert cuoi > dau
    return src[dau:cuoi]


def _ma(src: str) -> str:
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


# ---------------------------------------------------------------------------------------------
# Nội dung trình bày
# ---------------------------------------------------------------------------------------------

def test_bao_cao_phu_du_moi_buoc_va_moi_nghiep_vu():
    d = BC.bao_cao()
    assert d["so_buoc"] == len(LV.LUONG_VIEC)
    assert {n["ma"] for n in d["nhom"]} == set(LV.NGHIEP_VU)
    assert sum(n["so_buoc"] for n in d["nhom"]) == d["so_buoc"]


def test_hien_TEN_vai_tro_chu_khong_hien_ma_may():
    """Người đọc trang này là Chủ tịch và kiểm toán viên, không phải người viết mã.

    Một ô ghi "ptgd_doan" thì họ không đoán ra; ghi "Phó TGĐ tour đoàn" thì đọc được ngay. Đây là
    khác biệt giữa một trang để RÀ SOÁT và một trang để lập trình viên tự xem.
    """
    d = BC.bao_cao()
    cau = " ".join(b["ai_duoc"] for n in d["nhom"] for b in n["buoc"])
    for ma_may in ("tp_dh", "nv_dh", "ptgd_doan", "ketoan", "chutich"):
        assert ma_may not in cau, f"còn lộ mã máy '{ma_may}' ra màn hình"
    assert "Trưởng phòng Điều hành" in cau and "Kế toán" in cau


def test_buoc_mot_cua_noi_ro_khong_ai_lam_thay_duoc():
    """Đây là câu quan trọng nhất trên cả trang – nó giải thích vì sao chức vụ không thay được việc."""
    d = BC.bao_cao()
    dong_so = [b for n in d["nhom"] for b in n["buoc"] if b["ma"] == "dong_so"][0]
    assert dong_so["mot_cua"] is True
    assert "không ai làm thay được" in dong_so["ai_duoc"]
    assert dong_so["chu_so_huu"] == "người điều hành chuyến"


def test_vai_tro_tinh_luc_chay_duoc_dien_giai_bang_loi():
    """Duyệt dự toán đổi người theo loại tour – viết cứng một bên là khai sai một nửa số chuyến."""
    d = BC.bao_cao()
    duyet = [b for n in d["nhom"] for b in n["buoc"] if b["ma"] == "duyet"][0]
    assert "tour lẻ" in duyet["ai_duoc"] and "tour đoàn" in duyet["ai_duoc"]
    assert "Tổng giám đốc" in duyet["ai_duoc"] and "Phó TGĐ tour đoàn" in duyet["ai_duoc"]


def test_moi_buoc_deu_mang_theo_ly_do_ra_toi_man_hinh():
    """Một danh sách quyền không có lý do thì người rà chỉ gật hoặc lắc được, không sửa được."""
    for n in BC.bao_cao()["nhom"]:
        for b in n["buoc"]:
            assert len(b["vi_sao"]) >= 30, f"{b['ma']}: ra tới màn hình mà mất lý do"
            assert b["nguon"], f"{b['ma']}: không nói luật nằm ở đâu"


def test_tra_cuu_nguoc_theo_vai_tro():
    t = BC.tra_cuu_vai_tro("ketoan")
    assert t["ten"] == "Kế toán" and t["so_buoc"] >= 5 and not t["khong_co_buoc_nao"]
    assert any("quyết toán" in b["ten"].lower() for b in t["buoc"])
    t = BC.tra_cuu_vai_tro("xe_hdv")
    assert t["khong_co_buoc_nao"], "Tài xế & HDV không đẩy bước nào – phải nói ra, không trả rỗng im lặng"


# ---------------------------------------------------------------------------------------------
# Bản Excel để ký
# ---------------------------------------------------------------------------------------------

def test_excel_du_moi_buoc_va_co_hai_o_ky():
    """Bản không có ô ký thì không phải bản để ký – nó chỉ là một bảng in ra."""
    openpyxl = pytest.importorskip("openpyxl")
    import io
    wb = openpyxl.load_workbook(io.BytesIO(BC.xlsx()))
    ws = wb.active
    chu = "\n".join(str(ws.cell(r, c).value or "")
                    for r in range(1, ws.max_row + 1) for c in range(1, ws.max_column + 1))
    assert "Tổng giám đốc xác nhận" in chu and "Ký:" in chu
    for b in LV.LUONG_VIEC:
        assert b.ten in chu, f"bản Excel thiếu bước {b.ma}"
    assert "Vì sao chặn như vậy" in chu, "bản để ký phải mang theo lý do"


# ---------------------------------------------------------------------------------------------
# Cửa: có đường API và có nút trên màn hình
# ---------------------------------------------------------------------------------------------

@pytest.mark.skipif(not API.exists(), reason="chưa có kho mã")
def test_co_du_ba_duong_api_va_deu_khai_quyen():
    """Quyền gọi một đường mà không màn hình nào có nút gọi thì bằng không có quyền – và ngược lại."""
    src = API.read_text(encoding="utf-8")
    for duong in ('@router.get("/luong-viec")',
                  '@router.get("/luong-viec/vai-tro/{vai_tro}")',
                  '@router.get("/luong-viec.xlsx")'):
        assert duong in src, f"thiếu đường {duong}"
    khoi = src[src.find('@router.get("/luong-viec")'):src.find('@router.get("/accounts")')]
    assert khoi.count("require_roles(*XEM)") == 3, "có đường luồng việc chưa khai quyền ở chữ ký"
    assert "xuat_luong_cong_viec" in src, "xuất bản để ký mà không ghi nhật ký"


@pytest.mark.skipif(not WEB.exists(), reason="chưa có kho mã")
def test_man_hinh_co_the_va_co_nut_tai_ban_de_ky():
    """Màn hình phải có CỬA, không chỉ có dữ liệu.

    Ngày 09/9 đã có ca thật ở màn hình lệnh điều xe: mã đủ mọi thứ, chỉ sai chỗ đặt, và người dùng
    mở trang ra kết luận màn hình này chỉ để xem.
    """
    src = _ma(WEB.read_text(encoding="utf-8"))
    assert '["luongviec", "Luồng công việc"]' in src, "chưa thêm thẻ vào danh sách tab"
    assert 'api("/access/luong-viec")' in src, "mở thẻ mà không nạp dữ liệu"
    assert 'tab === "luongviec" && lv' in src, "không có khối hiển thị"
    assert "/access/luong-viec.xlsx" in src, "không có hàm tải bản để ký"
    # Phải NỐI vào một nút nằm TRONG khối của thẻ này. Bản đầu chỉ hỏi tên hàm có xuất hiện trong
    # tệp hay không – và một đột biến gỡ onClick khỏi nút đã lọt qua cả bộ, vì định nghĩa hàm vẫn
    # còn nguyên. Đúng cái bẫy mà chính tài liệu hàm này cảnh báo: mã có đủ mọi thứ, chỉ sai chỗ đặt.
    khoi = _khoi_hien_thi(src)
    assert "onClick={taiExcelLuongViec}" in khoi, "hàm tải có đó nhưng không nút nào gọi"
    assert "b.vi_sao" in khoi, "màn hình bỏ mất cột lý do"


@pytest.mark.skipif(not WEB.exists(), reason="chưa có kho mã")
def test_man_hinh_chi_dung_lop_css_co_that():
    """Lớp CSS bịa ra không lỗi, không cảnh báo – nó chỉ lặng lẽ không có tác dụng.

    Bản đầu của phép thử này đòi mọi lớp phải có trong globals.css, và đỏ ngay ở lớp "row" – vì
    globals.css KHÔNG khai .row, .act, .scroll hay .grey; chúng nằm ở nơi khác trong bộ giao diện.
    Phép thử ấy đo sai chỗ: nó không canh việc bịa lớp, nó canh việc lớp nằm đúng một tệp.

    Cách đo đúng, và hẹp đúng phạm vi phần mình thêm vào: lớp em dùng trong khối này phải là lớp
    ĐÃ CÓ MẶT ở nơi khác trong chính trang này. Dùng lại thì chắc chắn có thật; bịa ra một cái tên
    mới thì lộ ngay.
    """
    css = (GOC / "web" / "app" / "globals.css").read_text(encoding="utf-8")
    src = _ma(WEB.read_text(encoding="utf-8"))
    khoi = _khoi_hien_thi(src)
    ngoai_khoi = src.replace(khoi, " ")

    # Tag chỉ có bốn lớp trong globals.css. Bất cứ cls nào khác đều ra thẻ trơn, không màu.
    hop_le_tag = {"ok", "warn", "red", "navy", ""}
    assert ".tag" in css
    for cls in re.findall(r'<Tag cls="([a-z]*)"', khoi):
        assert cls in hop_le_tag, f'Tag cls="{cls}" không có trong globals.css'

    for cls in re.findall(r'className="([a-zA-Z0-9 _-]+)"', khoi):
        for x in cls.split():
            assert f'"{x}' in ngoai_khoi or f' {x}' in ngoai_khoi or f".{x}" in css, \
                f"lớp CSS chưa từng dùng ở đâu khác – nhiều khả năng là bịa: {x}"
