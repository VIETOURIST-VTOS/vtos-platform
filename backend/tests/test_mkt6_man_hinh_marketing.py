"""MÀN HÌNH MARKETING & PR — phép thử cho phần GIAO DIỆN (18/9/2026)

Vòng CI của kho này chỉ chạy `next build` cho phần web: nó bắt lỗi kiểu và lỗi cú pháp, nhưng KHÔNG
bắt được chuyện một màn hình lặng lẽ vẽ sai nghĩa một con số. Bốn phép thử đầu tệp này đọc thẳng mã
nguồn .tsx bằng biểu thức chính quy — đúng cách mà `test_menu.py` và `test_man_hinh_co_cua_nhap.py`
đã làm với thanh điều hướng — để canh những chỗ mà "xanh CI" không nói lên điều gì.

VÌ SAO CẦN: ngày 18/9/2026, PR #94 sửa bốn chỗ trong `services/leads.py` cho ra đúng tỷ lệ chốt theo
quy tắc Chủ tịch ký (`overview-v1`). Một trong bốn chỗ là: CHƯA ĐỐI CHIẾU thì trả `None` chứ không
trả 0, vì "chưa ai so sổ" và "chạy mà không ra khách" là hai câu khác hẳn nhau. Công ấy mất sạch chỉ
bằng một dòng giao diện ép `null` thành 0 — và không phép thử nào của phía sổ nhìn thấy được. Phép
thử T3 dưới đây đứng đúng ở chỗ ấy.

MỖI ĐƯỜNG NỐI CÓ PHÉP THỬ Ở CẢ HAI ĐẦU. Phía sổ đã có
`tests/test_mkt5_ty_le_chot_leads.py::test_chua_doi_chieu_thi_ty_le_da_ky_la_KHONG_XAC_DINH_va_bao_cao_TU_KEU`.
Đây là đầu còn lại.
"""
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[2] / "web"
MKT = WEB / "app" / "marketing" / "page.tsx"
BANG = WEB / "components" / "BaoCaoChuyenDoi.tsx"
LEADS = WEB / "app" / "leads" / "page.tsx"


def doc(p: Path) -> str:
    if not p.exists():
        pytest.skip(f"Không tìm thấy {p} – cây web không có ở đây")
    return p.read_text(encoding="utf-8")


def bo_chu_thich(src: str) -> str:
    """Bỏ chú thích /* */ và // trước khi tìm — nếu không thì chính những dòng giải thích trong tệp
    (vốn có nhắc tới `pct(`, `0%`, tên tab…) sẽ làm phép thử xanh hoặc đỏ sai."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# T1–T2 · MỘT ĐẦU, HAI NƠI GỌI
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_T1_ca_hai_man_hinh_cung_goi_MOT_bang_chuyen_doi():
    """Bảng lead → chuyển đổi xuất hiện ở hai màn hình. Chép mã sang là có HAI đầu, và ba tai nạn
    của kho này đều bắt đầu như thế: sửa một đầu, đầu kia lặng lẽ hiện số theo quy tắc cũ."""
    for p in (MKT, LEADS):
        src = bo_chu_thich(doc(p))
        # Đòi thẻ ĐƯỢC DỰNG RA (`<BaoCaoChuyenDoi`), không chỉ có tên xuất hiện đâu đó. Đột biến M8
        # của vòng 18/9 đã thoát đúng kẽ này: bỏ thẻ khỏi phần vẽ nhưng GIỮ dòng import, thế là chữ
        # "BaoCaoChuyenDoi" vẫn còn trong tệp và phép thử vẫn xanh trong khi bảng đã biến mất.
        assert "<BaoCaoChuyenDoi" in src, (
            f"{p.name} không DỰNG components/BaoCaoChuyenDoi.tsx (chỉ nhập khẩu thôi thì chưa đủ). "
            f"Màn hình cần bảng chuyển đổi thì phải gọi thành phần dùng chung, không vẽ bảng thứ hai.")


def test_T2_khong_man_hinh_nao_tu_ve_lai_bang_chuyen_doi():
    """Dấu hiệu của một bảng chép tay: màn hình tự lặp lại các khoá của báo cáo. Chỉ thành phần dùng
    chung mới được đụng vào những khoá ấy."""
    # Màn hình được phép ĐỌC vài khoá của báo cáo để dựng thẻ tổng quan hay bảng lệch; cái không
    # được phép là dựng lại CẢ bảng. Nhận ra bằng việc lặp `detail` — phần dài nhất, chép tay đau
    # nhất, và là phần chứa số điện thoại khách.
    for p in (MKT, LEADS):
        src = bo_chu_thich(doc(p))
        assert "rep.detail.map" not in src and "rep?.detail" not in src, (
            f"{p.name} đang tự dựng lại bảng chi tiết SĐT đã chốt. Bảng ấy thuộc "
            f"components/BaoCaoChuyenDoi.tsx — hai bản là hai đầu.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# T3 · CHƯA XÁC ĐỊNH KHÔNG ĐƯỢC HIỆN THÀNH 0%
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_T3_ty_le_theo_quy_tac_da_ky_khong_bi_ep_thanh_0_phan_tram():
    """`pct()` trong lib/api.ts viết là `((x || 0) * 100)` — nghĩa là nó BIẾN null THÀNH 0% một cách
    im lặng. Với `ty_le_chot_overview` thì đó là nói sai: `None` ở đây nghĩa là chưa ai chạy đối
    chiếu lead ↔ booking, không phải là chạy rồi mà không ra khách nào.

    Nên mọi chỗ in con số ấy phải đi qua `tyLe()`, hàm giữ đúng sự khác biệt. Phép thử này đỏ đúng
    vào ngày có người "đơn giản hoá" bằng cách gọi thẳng `pct`."""
    for p in (BANG, MKT):
        src = bo_chu_thich(doc(p))
        xau = re.findall(r"pct\(\s*[A-Za-z0-9_.?\[\]]*ty_le_chot_overview", src)
        assert not xau, (
            f"{p.name} gọi pct() thẳng lên ty_le_chot_overview: {xau}. pct() biến null thành 0%, "
            f"mà null ở đây là CHƯA XÁC ĐỊNH. Dùng tyLe() của components/BaoCaoChuyenDoi.tsx.")

    src = bo_chu_thich(doc(BANG))
    assert "chưa xác định" in src, (
        "Thành phần bảng chuyển đổi phải in ra chữ 'chưa xác định' cho trường hợp chưa đối chiếu. "
        "Không in ra thì người đọc không phân biệt được với 0%.")
    assert re.search(r"x\s*===\s*null\s*\|\|\s*x\s*===\s*undefined", src), (
        "tyLe() phải KIỂM TRA null/undefined tường minh. Viết `x ? ... : ...` là gộp 0 vào cùng một "
        "nhánh với null — đúng cái lỗi mà PR #94 vừa sửa ở phía sổ.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# T4 · HAI ĐƯỜNG DẪN CŨ CỦA MENU KHÔNG ĐƯỢC GÃY
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_T4_hai_duong_dan_cu_cua_menu_van_mo_dung_cho():
    """`test_menu.py` canh đúng từng ký tự hai dòng menu trỏ vào màn hình này:
           ["Kế hoạch & ngân sách", "/marketing?tab=ngansach"]
           ["Chiến dịch",           "/marketing"]
    Đổi bố cục màn hình mà quên hai dòng ấy thì menu vẫn bấm được nhưng ra sai chỗ — kiểu hỏng
    không ai báo lỗi, chỉ có người dùng đi lạc."""
    src = bo_chu_thich(doc(MKT))
    # Bám đúng DÒNG KHAI `tab`. Bản trước chỉ tìm chuỗi `useState("chiendich")`, mà `sub` bên dưới
    # cũng khai đúng chuỗi ấy — nên đổi mặc định của `tab` sang tab khác vẫn xanh (đột biến M4 thoát
    # đúng kẽ này ngày 18/9).
    m = re.search(r'\[\s*tab\s*,\s*setTab\s*\]\s*=\s*useState\(\s*"([a-z]+)"', src)
    assert m, "Không tìm thấy dòng khai trạng thái `tab` của màn hình Marketing"
    assert m.group(1) == "chiendich", (
        f"Menu nói mục này là 'Chiến dịch' và trỏ /marketing không tham số, nên tab mặc định phải là "
        f"chiendich; đang là '{m.group(1)}'. Đổi mặc định là việc HAI ĐẦU: phải sửa cả Shell.tsx và "
        f"test_menu.py trong cùng một lần.")
    assert re.search(r'url\s*===\s*"ngansach"', src), (
        "/marketing?tab=ngansach là một đường dẫn ĐANG CÓ trong menu — màn hình phải nhận nó và mở "
        "thẳng phần Ngân sách.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# T5–T7 · RANH GIỚI 09/9: SỐ PHẢI CÓ CỬA, KHÔNG CÓ CỬA THÌ NÓI LÀ CÒN THIẾU
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_T5_du_bay_man_hinh_theo_ban_ve_V3():
    src = bo_chu_thich(doc(MKT))
    khoi = src[src.index("const TABS"):src.index("];", src.index("const TABS"))]
    khoa = re.findall(r'\[\s*"([a-z]+)"', khoi)
    assert khoa == ["tongquan", "khach", "chuyendoi", "chiendich", "doisoat", "noidung", "thuonghieu"], \
        f"Bản vẽ V3.0 có bảy màn hình theo đúng thứ tự ấy; đang có {khoa}"


def test_T6_man_hinh_thuong_hieu_khong_bia_mot_con_so_nao():
    """Tab Thương hiệu & PR có HAI NỬA từ 18/9/2026, và luật của hai nửa khác nhau.

    LẬT LẠI CHÍNH PHÉP THỬ NÀY, cố ý và trong cùng một lần đẩy. Bản trước đòi tab này KHÔNG được
    hiện con số nào — đúng vào lúc nó chưa có sổ. Nay Chủ tịch đã chốt (18/9): sổ tài sản thương
    hiệu dùng chung bảng TSCĐ, và sổ ấy đã có cửa nhập cùng đường API. Giữ nguyên luật cũ là bắt
    một màn hình có sổ thật phải giả vờ chưa có.

    Luật mới, chặt hơn chứ không lỏng hơn:

      · NỬA CÓ SỔ  – mọi con số phải ĐỌC TỪ bản trả về của API (`th.dem`). Một con số viết thẳng
        vào mã là một con số không ai sửa được và không ai truy được nguồn.
      · NỬA CHƯA CÓ (theo dõi nhắc tên thương hiệu) – vẫn phải ghi "chưa có". Sổ hoạt động PR đã
        chuyển sang nửa CÓ SỔ cùng ngày; phần còn lại cần một cửa nhập hoặc một mối nối với dịch vụ đo
        bên ngoài, chưa có thì không được vẽ một con số nào.
    """
    src = bo_chu_thich(doc(MKT))
    # LẤY TỪ LẦN XUẤT HIỆN CUỐI CÙNG, không phải lần đầu. Chữ `tab === "thuonghieu"` còn nằm ở
    # chỗ khai danh sách tab phía trên; cắt từ đó thì khối này ôm luôn thẻ số của các tab khác, và
    # phép thử đi bắt nhầm người. (Bản trước không lộ ra vì nó chỉ đọc `so="…"`.)
    i = src.rindex('tab === "thuonghieu"')
    khoi = src[i:]

    # Nửa chưa có sổ: `so="…"` là chuỗi viết thẳng, và chuỗi ấy không được mang chữ số.
    so_chuoi = re.findall(r'so="([^"]*)"', khoi)
    assert so_chuoi, "phần việc còn thiếu đã biến mất khỏi màn hình"
    assert all(not re.search(r"\d", s) for s in so_chuoi), (
        f"Phần chưa có sổ đang hiện con số: {[s for s in so_chuoi if re.search(r'[0-9]', s)]}. "
        f"Chưa có sổ thì phải ghi là chưa có, không được bịa.")
    assert "chưa có" in khoi, "phần PR chưa có sổ phải nói thẳng ra."

    # Nửa có sổ: mọi `so={…}` phải chạm vào bản trả về của API, không được là một hằng số.
    so_bieu = re.findall(r"so=\{([^}]*)\}", khoi)
    assert so_bieu, "sổ tài sản thương hiệu chưa hiện thẻ số nào"
    # Hai sổ trên tab này: `th` (tài sản thương hiệu) và `pr` (hoạt động PR). Mọi thẻ số phải đọc
    # từ bản trả về của một trong hai, không được là một hằng số.
    for b in so_bieu:
        assert re.search(r"\b(th|pr)\.", b), \
            f"thẻ số {b!r} không đọc từ sổ nào – một con số viết thẳng vào màn hình"

    # Và màn hình phải thật sự gọi hai đường API ấy, chứ không chỉ khai hai biến tên là `th`, `pr`.
    for duong in ("/marketing/thuong-hieu", "/marketing/pr"):
        assert duong in src, f"màn hình chưa gọi đường API {duong}"


def test_T7_man_hinh_khong_khai_mau_rieng_mot_dong_nao():
    """Bộ nhận diện là MỘT nguồn duy nhất (app/tokens.css). Bản vẽ V3.0 anh Tuấn gửi là nền SÁNG,
    còn platform đã chốt nền TỐI từ 13/9/2026; dựng lại bảng màu của bản vẽ ngay trong màn hình là
    cách chắc chắn nhất để có hai bộ nhận diện phải sửa hai nơi mỗi lần đổi màu."""
    for p in (MKT, BANG):
        src = bo_chu_thich(doc(p))
        hex_ma = re.findall(r"#[0-9a-fA-F]{3,8}\b", src)
        assert not hex_ma, (
            f"{p.name} khai màu thẳng bằng mã hex: {hex_ma}. Màu phải lấy từ biến của tokens.css "
            f"(var(--vtos-…)) để bộ nhận diện chỉ có một nguồn.")
