"""TC-67 · CHỌN NỀN VÀ CỠ CHỮ THEO TỪNG TÀI KHOẢN — anh Tuấn giao 18/9/2026, duyệt sau khi xem bản thử.

Năm mục anh giao, và phép thử nào canh mục nào:
  1. Nền navy mặc định, chữ trắng ngà, thân bài 16px, hộp sáng hơn nền
        → test_mac_dinh_la_navy_16px · test_hop_sang_hon_nen_o_ca_hai_ban
  2. Nút "Giao diện" với ba lựa chọn nền, thanh trượt 14–20, trả về mặc định
        → test_bang_chon_du_ba_num_van · test_bang_chon_khong_nam_trong_thanh_ngang
  3. Nhớ theo TÀI KHOẢN, giữ khi chuyển trang và đăng nhập lại
        → test_cat_o_may_chu_chu_khong_chi_trong_trinh_duyet · test_rong_khac_mac_dinh
  4. Áp dụng toàn hệ thống, tiêu đề giãn theo tỉ lệ, giữ thứ bậc
        → test_moi_co_chu_deu_quy_ve_mot_num_van (và test_bo_nhan_dien canh không còn px)
  5. To chữ thì nở hoặc xuống dòng, không cắt; bảng rộng cuộn ngang
        → test_bon_cho_khoa_cung_bang_px_da_duoc_coi · test_bang_rong_cuon_trong_long_bang

VÌ SAO PHẢI CÓ TỆP NÀY chứ không dựa vào các phép thử cũ: bốn chỗ hỏng dưới đây đều KHÔNG làm trang
vỡ, không sinh lỗi nào trong bảng điều khiển, và đều chỉ lộ ra khi có người mở đúng màn hình đó ở
đúng cỡ chữ đó:
  1. Ai đó thêm một `font-size:13px` mới → một chỗ trên màn hình không giãn theo người dùng.
  2. Ai đó điền sẵn "toi"/16 vào 103 tài khoản trong bản chuyển đổi → mất vĩnh viễn ranh giới giữa
     "chưa chọn" và "đã chọn nền tối".
  3. Ai đó gom bảng chọn vào trong `.top` cho gọn → hai nút biến mất ở nền sáng.
  4. Ai đó thêm @media (prefers-color-scheme) vào CSS → cướp mất lựa chọn của người đã chọn.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = os.path.join(ROOT, "web", "app", "globals.css")
TOKENS = os.path.join(ROOT, "web", "app", "tokens.css")
LAYOUT = os.path.join(ROOT, "web", "app", "layout.tsx")
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")
CHON = os.path.join(ROOT, "web", "components", "ChonGiaoDien.tsx")
BIEUDO = os.path.join(ROOT, "web", "components", "BieuDo.tsx")
ALEMBIC = os.path.join(ROOT, "backend", "alembic", "versions")


def _doc(p: str) -> str:
    return open(p, encoding="utf-8").read()


def _khong_chu_thich(s: str) -> str:
    return re.sub(r'/\*.*?\*/', '', s, flags=re.S)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# ĐO TƯƠNG PHẢN — tự tính, không tin con số ghi trong chú thích
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# Con số viết tay trong chú thích là thứ đúng vào ngày viết và không ai kiểm lại sau đó. Chính bộ
# màu sáng v1.0 (ghi ở đầu tokens.css, 12/9/2026) là bằng chứng: nó ghi đủ mã màu, trông rất chỉn
# chu, và HAI nấc chữ của nó nằm dưới ngưỡng WCAG AA — không ai phát hiện trong sáu ngày. Nên phép
# thử này tính lại từ chính mã màu trong tệp.

def _sang(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _do_sang(hx: str) -> float:
    hx = hx.lstrip("#")
    if len(hx) == 3:
        hx = "".join(k * 2 for k in hx)
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _sang(r) + 0.7152 * _sang(g) + 0.0722 * _sang(b)


def _tuong_phan(a: str, b: str) -> float:
    x, y = _do_sang(a), _do_sang(b)
    if x < y:
        x, y = y, x
    return (x + 0.05) / (y + 0.05)


def _bien(khoi: str) -> dict:
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(r'(--vtos-[a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*;',
                                 _khong_chu_thich(khoi))}


def _khoi_sang() -> str:
    m = re.search(r':root\[data-nen="sang"\]\s*\{(.*?)\n\}', _doc(TOKENS), re.S)
    assert m, 'tokens.css chưa có khối :root[data-nen="sang"]'
    return m.group(1)


def _khoi_toi() -> str:
    m = re.search(r'^:root\s*\{(.*?)\n\}', _doc(TOKENS), re.S | re.M)
    assert m, "tokens.css không còn khối :root gốc (bản tối)"
    return m.group(1)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 1 · MẶC ĐỊNH
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_mac_dinh_la_navy_16px():
    """Anh Tuấn: "Nền mặc định là navy đậm … cỡ chữ thân bài 16 px."

    Mặc định phải khai ở MÁY CHỦ (models/core.py) chứ không chỉ trong JavaScript: màn hình đọc
    mặc định từ máy chủ gửi xuống, nên đổi mặc định là đổi MỘT chỗ. Chép cứng vào JavaScript thì
    đổi một chỗ sót một chỗ, và hai chỗ ấy lệch nhau thì không ai báo.
    """
    core = _doc(os.path.join(ROOT, "backend", "app", "models", "core.py"))
    assert re.search(r'GIAO_DIEN_MAC_DINH_NEN\s*,\s*GIAO_DIEN_MAC_DINH_CO\s*=\s*"toi"\s*,\s*16', core), \
        "mặc định phải là nền tối + 16px, khai ở models/core.py"
    assert re.search(r'GIAO_DIEN_CO_MIN\s*,\s*GIAO_DIEN_CO_MAX\s*=\s*14\s*,\s*20', core), \
        "dải cỡ chữ phải là 14–20px đúng yêu cầu 18/9"

    # Và CSS phải rơi về 16px khi chưa ai đặt gì — kể cả khi JavaScript chưa chạy hoặc chạy hỏng.
    assert re.search(r'html\s*\{\s*font-size:\s*var\(--vtos-co-chu\s*,\s*16px\)', _doc(CSS)), \
        "globals.css phải có html{font-size:var(--vtos-co-chu,16px)} – lối lui khi JavaScript chưa chạy"


def test_hop_sang_hon_nen_o_ca_hai_ban():
    """Anh Tuấn: "các hộp nội dung sáng hơn nền một chút".

    Canh ở CẢ HAI bản. Ở bản tối điều này đúng từ 13/9 nên dễ tưởng là xong; ở bản sáng thì ngược
    chiều (nền xám nhạt, thẻ trắng) và rất dễ khai nhầm thành hai màu bằng nhau — lúc ấy mọi khung
    trên màn hình biến mất, chỉ còn chữ trôi trên một mảng trắng.
    """
    for ten, khoi in (("bản tối", _khoi_toi()), ("bản sáng", _khoi_sang())):
        b = _bien(khoi)
        nen, the = b.get("--vtos-surface"), b.get("--vtos-card")
        assert nen and the, f"{ten}: thiếu --vtos-surface hoặc --vtos-card"
        assert _do_sang(the) > _do_sang(nen), \
            f"{ten}: nền thẻ ({the}) phải SÁNG HƠN nền màn hình ({nen})"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 1 · TƯƠNG PHẢN — bản sáng phải qua ngưỡng trên CẢ BA nền của nó
# ═══════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("nac", ["--vtos-text", "--vtos-heading", "--vtos-text-mute",
                                 "--vtos-text-faint", "--vtos-navy"])
def test_ban_sang_moi_nac_chu_deu_qua_nguong_aa(nac):
    """Mỗi nấc chữ của bản sáng phải đạt 4,5 trên cả ba nền: thẻ, màn hình, và nền thông tin.

    ĐO TRÊN CẢ BA chứ không chỉ nền thẻ: đúng cái lỗi TC-64 vừa sửa ở bản tối là một nấc đạt trên
    nền thẻ nhưng trượt trên nền thông tin — và nền thông tin chính là nền của thẻ nhãn trạng thái,
    tức chỗ chữ nhỏ nhất trên màn hình.
    """
    b = _bien(_khoi_sang())
    mau = b.get(nac)
    assert mau, f"bản sáng thiếu {nac}"
    for ten_nen in ("--vtos-card", "--vtos-surface", "--vtos-info-bg"):
        nen = b.get(ten_nen)
        assert nen, f"bản sáng thiếu {ten_nen}"
        tp = _tuong_phan(mau, nen)
        assert tp >= 4.5, f"{nac} ({mau}) trên {ten_nen} ({nen}) chỉ đạt {tp:.2f} – dưới ngưỡng AA 4,5"


def test_ban_sang_giu_du_bon_nac_ro_ret():
    """Bốn nấc chữ phải RÕ RỆT, không được gộp lại.

    Đậm đều tất cả lên đen thì qua hết ngưỡng tương phản mà vẫn hỏng: không còn phân biệt được chữ
    chính với chữ phụ, và mọi màn hình đọc ra như một khối chữ phẳng. Phép thử trên chỉ canh "đủ
    sáng"; phép thử này canh "đủ khác nhau".
    """
    b = _bien(_khoi_sang())
    the = b["--vtos-card"]
    nac = [_tuong_phan(b[k], the) for k in
           ("--vtos-heading", "--vtos-text", "--vtos-text-mute", "--vtos-text-faint")]
    assert nac == sorted(nac, reverse=True), \
        f"thứ bậc bốn nấc chữ bị đảo: {[round(x, 2) for x in nac]} (tiêu đề phải đậm nhất)"
    assert nac[0] / nac[-1] >= 2.0, \
        f"nấc đậm nhất chỉ hơn nấc mờ nhất {nac[0] / nac[-1]:.2f} lần – bốn nấc gần như một"


def test_khong_chep_lai_hai_nac_hong_cua_ban_ghi_v1_0():
    """Bộ màu sáng v1.0 ghi ở đầu tokens.css có HAI nấc chữ dưới ngưỡng AA. Không được chép lại.

    #64798C đạt 3,89 và #94A5B4 đạt 2,43 trên nền thông tin — đúng loại lỗi TC-64 vừa sửa ở bản
    tối. Bản ghi v1.0 GIỮ NGUYÊN trong chú thích làm sử liệu (nó ghi cái đã chốt ngày 12/9), nhưng
    hai mã ấy không được xuất hiện trong khối đang chạy.

    Canh bằng CHÍNH HAI MÃ MÀU chứ không bằng ngưỡng: phép thử ngưỡng ở trên đã chặn rồi, nhưng nó
    chỉ nói "màu này tối quá". Phép thử này nói thẳng "đừng quay lại bản ghi cũ", nên người sửa đọc
    được lý do ngay trong lời báo lỗi thay vì đi dò lại từ đầu.
    """
    than = _khong_chu_thich(_khoi_sang()).upper()
    for xau in ("#64798C", "#94A5B4"):
        assert xau not in than, (
            f"{xau} là mã của bản ghi v1.0, nằm DƯỚI ngưỡng AA trên nền thông tin – "
            "đừng chép lại bộ cũ, xem chú thích ở khối bản sáng")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 2 · BẢNG CHỌN
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_bang_chon_du_ba_num_van():
    """Ba núm vặn anh Tuấn kê ra, thiếu cái nào cũng là thiếu một câu trả lời."""
    src = _doc(CHON)
    for ma in ("toi", "sang", "may"):
        assert f'"{ma}"' in src, f"thiếu lựa chọn nền {ma}"
    assert 'type="range"' in src and "CO_MIN" in src and "CO_MAX" in src, \
        "thiếu thanh trượt cỡ chữ"
    assert "A−" in src and "A+" in src, "thiếu hai nút A− / A+"
    assert re.search(r'\{co\}&nbsp;px|\{co\}\s*px', src), "phải hiện cỡ chữ đang dùng bằng số"
    assert "Trả về mặc định" in src, "thiếu nút trả về mặc định"


def test_bang_chon_khong_nam_trong_thanh_ngang():
    """BẢNG CHỌN PHẢI GẮN NGOÀI `.top`. Đây là lỗi đã mắc thật khi dựng bản xem thử 18/9.

    Để bảng bên trong thanh ngang thì nó ăn luật `.top .bar a,.top .bar button` — chữ trắng, nền
    trắng mờ. Trên nền TỐI không ai thấy gì lạ, nên lỗi lọt qua; ở nền SÁNG thì thành chữ trắng
    trên thẻ trắng và hai nút "Trắng sáng" với "Theo máy" biến mất hẳn khỏi màn hình.

    Canh bằng `createPortal` chứ không bằng vị trí dòng trong tệp: cách đặt có thể đổi, nhưng
    điều kiện "không nằm trong cây con của .top" thì không được đổi.
    """
    src = _doc(CHON)
    assert "createPortal" in src, \
        "bảng chọn phải gắn thẳng vào <body> bằng createPortal, không nằm trong .top"
    assert "document.body" in src, "createPortal phải trỏ vào document.body"
    # Shell chỉ dựng cái NÚT trong thanh; bảng thì không.
    shell = _doc(SHELL)
    assert "<ChonGiaoDien" in shell, "Shell.tsx chưa dựng nút Giao diện"
    assert "gd-bang" not in shell, \
        "Shell.tsx không được tự dựng bảng chọn trong thanh ngang – để ChonGiaoDien lo bằng portal"


def test_bang_chon_hien_dung_khi_duoc_mo():
    """`display:flex` đè mất thuộc tính `hidden` của trình duyệt, nên phải khai lại `[hidden]`.

    Không khai thì bảng chọn MỞ SẴN ngay khi tải trang, che mất góc trên bên phải của mọi màn
    hình. Lỗi này đã xảy ra thật ở bản xem thử 18/9 và chỉ lộ ra khi chụp ảnh màn hình.
    """
    css = _khong_chu_thich(_doc(CSS))
    assert re.search(r'\.gd-bang\[hidden\]\s*\{\s*display:\s*none', css), \
        ".gd-bang[hidden]{display:none} bị thiếu – bảng chọn sẽ mở sẵn khi tải trang"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 3 · CẤT THEO TÀI KHOẢN
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_cat_o_may_chu_chu_khong_chi_trong_trinh_duyet():
    """Chữ "đăng nhập lại" của anh Tuấn buộc lựa chọn phải nằm ở MÁY CHỦ.

    localStorage đi theo MÁY, không theo NGƯỜI: chỉnh ở máy tính thì mở điện thoại vẫn về mặc
    định, xoá bộ nhớ trình duyệt là mất, hai người dùng chung một máy thì đè lên nhau.
    Trình duyệt vẫn giữ một BẢN CHÉP để vẽ ngay khỏi loé nền — nhưng bản chép không phải bản cất.
    """
    core = _doc(os.path.join(ROOT, "backend", "app", "models", "core.py"))
    assert "gd_nen" in core and "gd_co_chu" in core, "bảng users thiếu hai cột giao diện"

    routes = _doc(os.path.join(ROOT, "backend", "app", "api", "v1", "routes.py"))
    assert re.search(r'@router\.put\("/auth/giao-dien"', routes), "thiếu cửa GHI giao diện"
    assert re.search(r'@router\.delete\("/auth/giao-dien"', routes), "thiếu cửa TRẢ VỀ mặc định"
    assert '"giao_dien"' in routes, "/auth/me phải gửi kèm giao diện của người đăng nhập"

    chon = _doc(CHON)
    assert "/auth/giao-dien" in chon, "màn hình phải ghi lựa chọn về máy chủ"


def test_cua_ghi_khong_nhan_id_nguoi_khac():
    """Cửa ghi giao diện KHÔNG được nhận mã người dùng — hàng rào nằm ở hình dạng của cửa.

    Một cửa nhận `user_id` rồi kiểm "có phải chính mình không" thì an toàn đúng đến lần sửa tiếp
    theo. Một cửa không có tham số ấy thì không có đường nào để đi sai, kể cả khi ai đó về sau sửa
    nhầm luật phân quyền.
    """
    routes = _doc(os.path.join(ROOT, "backend", "app", "api", "v1", "routes.py"))
    m = re.search(r'def dat_giao_dien\((.*?)\):', routes, re.S)
    assert m, "không tìm thấy hàm dat_giao_dien"
    tham_so = m.group(1)
    assert "user_id" not in tham_so and "username" not in tham_so, \
        f"cửa ghi giao diện không được nhận mã người dùng: {tham_so.strip()}"
    assert "current_user" in tham_so, "cửa ghi phải ghi cho chính người đang đăng nhập"


def test_cua_ghi_kiem_o_may_chu_chu_khong_tin_man_hinh():
    """Màn hình có thanh trượt 14–20, nhưng ai cũng gọi API bằng tay được.

    Và dải phải lấy từ CHÍNH hằng số mà mô hình dùng, không chép lại con số vào cửa: chép lại là
    ngày nào đó dải ở hai nơi lệch nhau, và cái lệch ấy chỉ lộ ra khi có người đặt được cỡ chữ mà
    màn hình không cho đặt.
    """
    routes = _doc(os.path.join(ROOT, "backend", "app", "api", "v1", "routes.py"))
    m = re.search(r'def dat_giao_dien\(.*?\n(?=\n\n@router)', routes, re.S)
    assert m, "không tìm thấy thân hàm dat_giao_dien"
    than = m.group(0)
    assert "GIAO_DIEN_NEN" in than, "cửa ghi phải kiểm nền theo bộ giá trị đã khai ở models"
    assert "GIAO_DIEN_CO_MIN" in than and "GIAO_DIEN_CO_MAX" in than, \
        "cửa ghi phải kiểm cỡ chữ theo dải đã khai ở models, không chép số vào đây"
    assert "422" in than, "sai giá trị thì phải trả lỗi, không im lặng nhận bừa"


def test_rong_khac_mac_dinh():
    """CHƯA CHỌN khác ĐÃ CHỌN NỀN TỐI — và bản chuyển đổi không được xoá mất ranh giới ấy.

    Hai điều này trông giống hệt nhau trên màn hình (cả hai ra nền tối) và khác hẳn nhau vào đúng
    cái ngày ai đó đổi mặc định của hệ thống: người chưa chọn phải đi theo mặc định mới, người đã
    chọn thì không. Điền sẵn "toi"/16 vào 103 tài khoản là xoá mất ranh giới ngay từ phút chạy bản
    chuyển đổi, và không cách nào lấy lại — vì không ai còn phân biệt được ai từng bấm.

    Đây cũng là lý do nút "Trả về mặc định" gọi cửa DELETE (xoá lựa chọn) chứ không gọi cửa PUT
    với giá trị mặc định: nút viết là "trả về mặc định" thì nó phải trả người dùng về trạng thái
    chưa chọn, chứ không đóng đinh họ vào hai con số của hôm nay.
    """
    ban = [f for f in os.listdir(ALEMBIC) if "giao_dien" in f]
    assert ban, "thiếu bản chuyển đổi alembic cho hai cột giao diện"
    src = _doc(os.path.join(ALEMBIC, ban[0]))
    assert re.search(r'server_default=""', src), \
        "gd_nen phải có server_default='' – rỗng nghĩa là CHƯA CHỌN"
    assert not re.search(r'server_default=["\']toi["\']', src), \
        'bản chuyển đổi KHÔNG được điền sẵn "toi" — xoá mất ranh giới chưa-chọn / đã-chọn'
    assert re.search(r'gd_co_chu.*nullable=True', src), \
        "gd_co_chu phải nullable – NULL nghĩa là CHƯA CHỌN"

    routes = _doc(os.path.join(ROOT, "backend", "app", "api", "v1", "routes.py"))
    m = re.search(r'def xoa_giao_dien\(.*?return\s*\{(.*?)\}', routes, re.S)
    assert m, "không tìm thấy cửa trả về mặc định"
    assert "None" in m.group(1), \
        "cửa trả về mặc định phải XOÁ lựa chọn (trả None), không ghi đè bằng giá trị mặc định"

    chon = _doc(CHON)
    assert re.search(r'"DELETE"', chon), \
        'nút "Trả về mặc định" phải gọi cửa DELETE, không gọi PUT với giá trị mặc định'


def test_ve_truoc_ghi_sau_nhung_phai_noi_khi_ghi_hong():
    """Màn hình đổi màu KHÔNG phải bằng chứng đã lưu.

    Màn hình vẽ trước rồi mới ghi về máy chủ — phải thế, vì chờ máy chủ trả lời rồi mới đổi màu
    thì người dùng bấm xong đợi nửa giây mới thấy gì và tưởng nút hỏng. Nhưng hệ quả là: cửa ghi
    hỏng thì người dùng VẪN thấy màn hình đổi và vẫn tưởng đã lưu, cho tới lần đăng nhập sau.
    Nên phải có một dòng nói thẳng ra. Một cái nút im lặng khi hỏng thì tệ hơn một cái nút báo hỏng.
    """
    src = _doc(CHON)
    m = re.search(r'catch\s*\{([^}]*)\}', src)
    assert m, "cửa ghi không có nhánh xử lý khi hỏng"
    assert re.search(r'catch\s*\{[^}]*setTrangThai[^}]*loi:\s*true', src, re.S), \
        "ghi hỏng thì phải báo cho người dùng, không im lặng"
    assert "gd-trangthai" in src and "gd-trangthai" in _doc(CSS), \
        "thiếu dòng trạng thái dưới đáy bảng chọn"


def test_ban_chep_trong_trinh_duyet_chay_truoc_khi_trang_ve():
    """Kịch bản chống loé nền phải nằm trong <head>, và phải bọc try/catch.

    Nằm sau thì vô nghĩa: trang đã vẽ xong bằng nền mặc định rồi mới nháy sang nền của người dùng.
    Không bọc try/catch thì máy chặn localStorage (chế độ riêng tư, chính sách máy công ty) là cả
    trang trắng — đây là đoạn mã chạy sớm nhất, nó hỏng thì không còn gì chạy nữa.
    """
    lay = _doc(LAYOUT)
    dau, than = lay.split("<body>", 1)
    assert "vtos_giao_dien" in dau, "kịch bản đặt nền phải nằm trong <head>, trước khi trang vẽ"
    m = re.search(r'vtos_giao_dien.*?catch', dau, re.S)
    assert m, "kịch bản đặt nền phải bọc try/catch – máy chặn localStorage thì trang vẫn phải mở"
    assert "prefers-color-scheme" in dau, \
        'kịch bản phải xử lý được nền "Theo máy" ngay từ nét vẽ đầu tiên'


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 4 · ÁP DỤNG TOÀN HỆ THỐNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_moi_co_chu_deu_quy_ve_mot_num_van():
    """115 khai báo cỡ chữ phải cùng nhân MỘT hệ số, nếu không thứ bậc vỡ khi kéo núm.

    Chia cho 14 chứ không phải 16, và con số 14 ấy là lời hứa kiểm được: thân bài TRƯỚC TC-67 là
    14px, nên khi người dùng để núm ở 14 thì mọi chữ ra ĐÚNG BẰNG bản cũ, không lệch một điểm ảnh.
    Nhờ vậy chứng minh được vòng này không đổi gì ngoài thứ được phép đổi.

    Mẫu số nào khác 14 lọt vào là một chỗ giãn sai nhịp so với phần còn lại — chữ to lên thì nó to
    ít hơn hoặc nhiều hơn, và thứ bậc trên màn hình lệch dần theo cỡ chữ.
    """
    src = _khong_chu_thich(_doc(CSS))
    mau = re.findall(r'font-size:\s*calc\(\s*[\d.]+\s*/\s*(\d+)\s*\*\s*1rem\s*\)', src)
    assert mau, "không tìm thấy khai báo cỡ chữ co giãn nào"
    lech = sorted({m for m in mau if m != "14"})
    assert not lech, f"có mẫu số khác 14: {lech} – mọi cỡ chữ phải cùng một hệ số"
    assert len(mau) >= 100, f"chỉ có {len(mau)} cỡ chữ co giãn – nghi còn chỗ chưa đổi"


def test_bon_cho_khoa_cung_bang_px_da_duoc_coi():
    """Bốn cái khung đựng chữ phải nở theo chữ, nếu không chữ to lên là bị cắt.

    Đây chính là chỗ mục 5 của anh Tuấn nói tới: "ô, hàng, nút tự giãn hoặc xuống dòng, không bị
    cắt chữ". Cỡ chữ đổi mà cái khung đứng nguyên thì chữ tràn ra ngoài khung rồi bị cắt — và nó
    chỉ lộ ra ở cỡ lớn, tức chỉ với đúng những người cần chữ lớn.
    """
    # ══ TC-69 (18/9/2026) NỚI MẪU TÌM, KHÔNG NỚI LUẬT ═══════════════════════════════════════
    # TRƯỚC: mẫu ghim cả CON SỐ (`calc(72/14`, `calc(252/14`).
    # TỪ NAY: mẫu chỉ ghim ĐƠN VỊ (`calc(<số>/14*1rem)`), còn con số để vòng khác chốt.
    #
    # Vì sao: luật của phép thử này là "không còn chỗ nào khoá cứng bằng px", chứ không phải
    # "thanh ngang phải cao đúng 72". Ghim con số vào đây nghĩa là mỗi lần anh Tuấn đổi bố cục thì
    # một phép thử về ĐƠN VỊ lại đỏ vì một lý do chẳng liên quan gì tới đơn vị — và người sửa sẽ
    # quen tay sửa con số trong phép thử cho hết đỏ, đến một ngày sửa luôn cả cái nó đang canh.
    # TC-69 hạ --top-h 72 → 64 và thanh dọc 252 → 232; hai con số ấy nay do
    # test_tc69_thanh_ngang_thap_va_thanh_doc_hep canh, đúng chỗ của chúng.
    src = _khong_chu_thich(_doc(CSS))
    for ten, mau in (("--top-h", r'--top-h:\s*calc\(\s*\d+\s*/\s*14\s*\*\s*1rem'),
                     ("thanh dọc", r'aside\.side\{flex:0 0 calc\(\s*\d+\s*/\s*14\s*\*\s*1rem'),
                     (".mh01-cuon", r'\.mh01-cuon\{max-height:calc\(\s*\d+\s*/\s*14\s*\*\s*1rem'),
                     (".kh-ly", r'\.kh-ly\{[^}]*max-width:calc\(\s*\d+\s*/\s*14\s*\*\s*1rem')):
        assert re.search(mau, src), f"{ten} vẫn khoá cứng bằng px – chữ to lên sẽ bị cắt"


def test_khoi_in_giay_thang_ca_hai_ban_mau():
    """Khối @media print phải thắng cả `:root[data-nen="sang"]`, không chỉ thắng `:root`.

    Không thì người đang để nền sáng in ra giấy bằng bảng màu MÀN HÌNH chứ không bằng bảng màu
    GIẤY — và bảng màu màn hình có `--vtos-text-mute` chỉ đạt 2,19 trên giấy trắng (đo ở TC-35).
    Độ ưu tiên chọn lọc của `:root[data-nen]` cao hơn `:root`, nên thứ tự dòng trong tệp không cứu
    được; phải nâng chính bộ chọn của khối in.
    """
    src = _doc(CSS)
    m = re.search(r'@media print\{(.*?)\n\}', src, re.S)
    assert m, "không tìm thấy khối @media print"
    assert re.search(r':root\s*,\s*:root\[data-nen\]\s*\{', m.group(1)), \
        '@media print phải khai `:root,:root[data-nen]{` để thắng cả bảng màu người dùng chọn'


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MỤC 5 · KHÔNG CẮT CHỮ, KHÔNG MẤT NÚT
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_bang_rong_cuon_trong_long_bang():
    """Anh Tuấn: "bảng rộng cho phép cuộn ngang trong vùng bảng" trên điện thoại.

    Chữ TRONG VÙNG BẢNG là điều kiện thật: một cái bảng làm cả trang cuộn ngang thì thanh ngang và
    menu trôi theo, và người dùng mất phương hướng. Cuộn phải bị nhốt trong khung của chính nó.
    """
    src = _khong_chu_thich(_doc(CSS))
    m = re.search(r'\.wrap\{([^}]*)\}', src)
    assert m and "overflow-x:auto" in m.group(1), ".wrap phải cuộn ngang trong lòng nó"
    assert re.search(r'html,body\{overflow-x:hidden\}', src), \
        "thân trang phải bị chặn cuộn ngang trên màn hình hẹp"


def test_nhan_truc_ngang_khong_bao_gio_bi_cat():
    """Nhãn tháng: thà hiện ít nhãn còn hơn hiện đủ mà ba cái cụt thành `T…`.

    LỖI NÀY CÓ SẴN TỪ TRƯỚC TC-67, đo bằng bản đối chứng chạy globals.css nguyên bản ở 14px: màn
    1280 đã cắt T10 T11 T12, màn 1024 cắt cả mười hai nhãn. Cỡ chữ 16px chỉ dịch ngưỡng từ 1280
    lên 1366. Ghi lại để vòng sau đừng tưởng đây là giá phải trả cho việc cho chọn cỡ chữ.

    NGƯỠNG TÍNH BẰNG `em` nên tự đi theo cỡ chữ — không phải nhớ ba ngưỡng cho ba cỡ.

    CHỈ ÁP CHO HÌNH TỪ 10 NHÃN TRỞ LÊN: hình bốn quý trong cùng bề rộng ấy thì bốn nhãn vẫn vừa,
    ẩn bớt ở đó là giấu đi thứ đang đọc được. Luật CSS không đếm được số cột nên BieuDo.tsx phải
    nói cho nó biết.
    """
    src = _khong_chu_thich(_doc(CSS))
    assert re.search(r'\.bd-nhanx\.dong-nhan\{[^}]*container-type:\s*inline-size', src), \
        "hàng nhãn chưa khai container-type – luật theo bề rộng không chạy"
    m = re.search(r'@container nhanx \(max-width:\s*(\d+)em\)\s*\{(.*?)\n\}', src, re.S)
    assert m, "thiếu luật ẩn nhãn khi hàng nhãn hẹp"
    assert "visibility:hidden" in m.group(2), "nhãn chẵn phải ẩn, không phải bị cắt"
    assert "overflow:visible" in m.group(2), \
        "nhãn lẻ phải được tràn sang chỗ vừa trống, nếu không nó vẫn cụt như cũ"

    bd = _doc(BIEUDO)
    assert re.search(r'diem\.length\s*>=\s*10\s*\?\s*" dong-nhan"', bd), \
        "BieuDo.tsx phải chỉ bật luật này cho hình từ 10 nhãn trở lên"
