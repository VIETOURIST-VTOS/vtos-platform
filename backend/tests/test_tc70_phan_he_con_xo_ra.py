"""TC-70 · 18/9/2026 — KINH DOANH XỔ RA HAI, ĐIỀU HÀNH XỔ RA BA.

Anh Tuấn, 18/9/2026:
  "KINH DOANH: em tách ra cho anh khi rê chuột vào xổ ra kinh doanh lẻ và kinh doanh đoàn, click
   chuột vào đó sẽ ra màn hình riêng cho từng phân hệ riêng."
  "ĐIỀU HÀNH: rê chuột vào sẽ xổ ra đh tour / đh xe và HDV, 3 phân hệ sẽ ra 3 màn hình giao diện
   khác nhau."

Và ba lựa chọn anh chốt khi em hỏi lại:
  · Bấm thẳng vào chữ "Kinh doanh" / "Điều hành" thì CHỈ XỔ RA, không đi đâu.
  · Năm màn hình mới là MỤC LỤC phân hệ riêng từng phòng – không số liệu, đúng ranh giới 09/9.
  · Trên điện thoại: chạm lần 1 xổ ra, chạm lần 2 mới đi.

════════════════════════════════════════════════════════════════════════════════════════════════
PHÉP THỬ NÀY CANH CÁI GÌ

Việc dễ làm hỏng nhất ở đây KHÔNG phải cái xổ ra – hỏng cái ấy thì nhìn là thấy ngay. Nguy hiểm
là một NHÁNH LẶNG LẼ BIẾN MẤT: cây v1.3 của Kinh doanh có năm nhánh cấp một, của Điều hành có
mười. Năm phân hệ con chia nhau những nhánh ấy. Quên một nhánh thì nó không còn hiện ở bất kỳ màn
hình nào, và vì phân hệ cha đã mất lối vào từ menu nên không ai còn chỗ nào để thấy nó nữa. Nó
trông như chưa bao giờ tồn tại. Đó là kiểu hỏng không ai phát hiện ra.

Nên khẳng định nặng nhất ở đây là: HỢP của các `lay` phải PHỦ HẾT nhánh cấp một của cây cha.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAY = os.path.join(ROOT, "web", "lib", "cay_phan_he.ts")
SHELL = os.path.join(ROOT, "web", "components", "Shell.tsx")
CSS = os.path.join(ROOT, "web", "app", "globals.css")
TRANG = os.path.join(ROOT, "web", "app", "phan-he", "[khoa]", "page.tsx")
# 11/10/2026 — phần VẼ MỤC LỤC rời khỏi tệp trang, sang components/MucLucPhanHe.tsx: từ hôm nay
# `/phan-he/<khoa>` mở ra bảng chỉ tiêu của phòng, còn mục lục lùi về `?xem=muc-luc`. Dãy chip
# chuyển nhanh và cờ "dùng chung" là của MỤC LỤC, nên hai phép thử dưới đây đi theo nó. Luật
# không đổi một chữ; chỉ đổi chỗ soi, vì soi nhầm chỗ mà vẫn xanh là kiểu hỏng nguy hiểm nhất.
MUC_LUC = os.path.join(ROOT, "web", "components", "MucLucPhanHe.tsx")

NAM_KHOA = ["kdle", "kddoan", "dhtour", "dhxe", "hdv"]


def _doc(p):
    return open(p, encoding="utf-8").read()


def _khong_ghi_chu(s):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S)


def _khoi_cha(cay, khoa):
    """Cắt đúng khối khai báo của một phân hệ CHA trong CAY_PHAN_HE.

    Cắt từ `{ khoa: "<khoa>"` tới `{ khoa:` kế tiếp – hoặc tới chỗ khai PHAN_HE_CON nếu đây là
    phân hệ cuối. Không dùng đếm ngoặc vì cây lồng bốn cấp, đếm tay dễ sai hơn là cắt theo mốc.
    """
    i = cay.find(f'{{ khoa: "{khoa}"')
    assert i > 0, f"không tìm thấy phân hệ cha {khoa} trong cây"
    j = cay.find('{ khoa: "', i + 10)
    k = cay.find("export const PHAN_HE_CON", i)
    het = min(x for x in (j, k, len(cay)) if x > 0)
    return cay[i:het]


def _nhanh_cap_mot(khoi):
    """Mã các nhánh CẤP MỘT: hai đoạn số, có thể kèm MỘT chữ cái ("3.1", "4.10", "4.4b"). Mục con
    sâu hơn có ba đoạn trở lên ("3.3.1", "3.4.2.1") nên khuôn này không vơ nhầm chúng.

    CHỮ CÁI Ở CUỐI THÊM NGÀY 12/10/2026, và lý do đáng ghi lại vì nó là lỗi của chính phép thử
    này. Khuôn cũ chỉ đọc được mã hai đoạn SỐ, nên sáu nhánh mang mã kiểu "4.4b" vô hình với nó —
    kể cả nhánh "Hợp đồng thuê xe riêng" của Điều hành, nhánh chạy thật từ PR #211 mà không phân
    hệ con nào nhận. Tức là phép thử canh đúng kiểu hỏng ấy đã để lọt đúng kiểu hỏng ấy, suốt từ
    07/10 tới 12/10, và nó im lặng vì thứ nó không đọc được thì nó cũng không đếm thiếu.

    BÀI HỌC: một khuôn dò hẹp hơn dữ liệu thật thì phép thử vẫn XANH và vẫn VÔ DỤNG. Nên
    `test_khuon_do_doc_duoc_ca_ma_co_chu_cai` canh thẳng vào khuôn, để lần sau ai siết nó lại thì
    có người biết ngay thay vì biết sau năm ngày.
    """
    return re.findall(r'\bma: "(\d+\.\d+[a-z]?)"', khoi)


def _khai_phan_he_con(cay):
    """Đọc PHAN_HE_CON thành [(khoa, cha, [mã lấy], [mã dùng chung])]."""
    i = cay.find("export const PHAN_HE_CON")
    assert i > 0, "không có PHAN_HE_CON – TC-70 đã bị gỡ?"
    khoi = cay[i:cay.find("\n];", i)]
    ra = []
    for m in re.finditer(r'\{ khoa: "(\w+)", cha: "(\w+)",(.*?)\},', khoi, re.S):
        than = m.group(3)
        d_lay = re.search(r'lay:\s*\[(.*?)\]', than, re.S)
        d_chung = re.search(r'chung:\s*\[(.*?)\]', than, re.S)
        # Cùng khuôn với `_nhanh_cap_mot`: hai bên phải đọc được cùng một tập mã, nếu không thì
        # phép so "lấy đủ chưa" so hai danh sách được lọc bằng hai cái sàng khác nhau.
        lay = re.findall(r'"(\d+\.\d+[a-z]?)"', d_lay.group(1)) if d_lay else []
        chung = re.findall(r'"(\d+\.\d+[a-z]?)"', d_chung.group(1)) if d_chung else []
        ra.append((m.group(1), m.group(2), lay, chung))
    return ra


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  1. KHÔNG NHÁNH NÀO ĐƯỢC BIẾN MẤT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_hop_cua_cac_lay_phu_het_nhanh_cua_cay_cha():
    """Mỗi nhánh cấp một của cây cha phải có mặt ở ÍT NHẤT một phân hệ con.

    Đây là khẳng định quan trọng nhất của vòng này. Phân hệ cha mất lối vào từ thanh dọc, nên một
    nhánh không được phân hệ con nào nhận sẽ không còn chỗ nào hiện ra. Nó không báo lỗi, không để
    lại dấu vết – nó chỉ đơn giản là không tồn tại nữa với người dùng.
    """
    cay = _doc(CAY)
    khai = _khai_phan_he_con(cay)
    assert khai, "đọc PHAN_HE_CON ra rỗng – khuôn dò hỏng, không phải mã hỏng"
    theo_cha = {}
    for _, cha, lay, _c in khai:
        theo_cha.setdefault(cha, set()).update(lay)

    for cha, da_lay in theo_cha.items():
        co_that = set(_nhanh_cap_mot(_khoi_cha(cay, cha)))
        thieu = co_that - da_lay
        assert not thieu, (
            f"phân hệ {cha} có nhánh {sorted(thieu)} không phân hệ con nào nhận – "
            f"nhánh ấy biến mất khỏi mọi màn hình mà không ai hay")
        thua = da_lay - co_that
        assert not thua, (
            f"phân hệ con lấy mã {sorted(thua)} không có trong cây {cha} – "
            f"lúc dựng sẽ ném lỗi, màn hình trắng")


def test_khuon_do_doc_duoc_ca_ma_co_chu_cai():
    """Khuôn dò của chính bộ kiểm này phải đọc được MỌI mã cấp một đang có trong cây.

    Phép thử trên nó (`test_hop_cua_cac_lay_phu_het_nhanh_cua_cay_cha`) chỉ mạnh bằng cái sàng nó
    dùng: nhánh nào khuôn không đọc ra thì vừa không nằm trong "có thật" vừa không nằm trong "đã
    lấy", nên nó biến mất khỏi cả hai vế và phép trừ ra rỗng. Xanh, và vô dụng. Chuyện này đã xảy
    ra thật với mã "4.4b" từ 07/10 tới 12/10/2026.

    Nên đếm thẳng trên văn bản cây, bằng một khuôn ĐỘC LẬP với khuôn đang kiểm.
    """
    cay = _doc(CAY)
    for cha in ("khachhang", "vanhanh"):
        khoi = _khoi_cha(cay, cha)
        that = set(re.findall(r'\bma: "(\d+\.\d+[a-z]?)"', khoi))
        doc_ra = set(_nhanh_cap_mot(khoi))
        assert that == doc_ra, (
            f"khuôn dò bỏ sót mã {sorted(that - doc_ra)} của phân hệ {cha} – "
            f"mã nào khuôn không đọc được thì phép kiểm phủ nhánh không nhìn thấy nó")


def test_lay_ma_khong_co_that_thi_nem_loi_chu_khong_bo_qua_lang_le():
    """`cayCuaPhanHeCon` phải NÉM LỖI khi mã khai không có trong cây cha.

    Bỏ qua lặng lẽ thì nhánh biến mất mà màn hình vẫn dựng bình thường – đúng kiểu hỏng mà phép
    thử trên đang canh, nhưng xảy ra lúc chạy chứ không lúc đọc mã.
    """
    src = _khong_ghi_chu(_doc(CAY))
    assert "cayCuaPhanHeCon" in src, "thiếu hàm dựng khung nhìn của phân hệ con"
    than = src[src.find("export function cayCuaPhanHeCon"):]
    than = than[:than.find("\n}")]
    assert than.count("throw new Error") >= 2, (
        "phải ném lỗi cho CẢ HAI trường hợp: cha không có, và mã lấy không có trong cha")


def test_cay_cha_khong_bi_doi_khi_dung_khung_nhin():
    """Dựng khung nhìn KHÔNG được sửa cây gốc.

    Gắn cờ `chung` thẳng vào nhánh của cây cha thì nhánh ấy mang cờ vĩnh viễn: mở "Kinh doanh lẻ"
    trước rồi mở "Điều hành tour" sau, Điều hành cũng hiện cờ "dùng chung" dù nó chẳng chung với
    ai. Lỗi kiểu này chỉ hiện ra theo THỨ TỰ người dùng bấm, nên rất khó lần ra.
    """
    src = _khong_ghi_chu(_doc(CAY))
    than = src[src.find("export function cayCuaPhanHeCon"):]
    than = than[:than.find("\n}")]
    assert "{ ...nhanh" in than, "phải sao chép nhánh (`{ ...nhanh, chung: true }`) chứ không sửa tại chỗ"
    assert not re.search(r'nhanh\.chung\s*=', than), "gán thẳng vào nhánh gốc là sửa cây cha"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  2. THANH DỌC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_hai_nhom_xo_ra_dung_nam_phan_he_con():
    cay, shell = _doc(CAY), _doc(SHELL)
    khai = {k for k, _, _, _ in _khai_phan_he_con(cay)}
    assert khai == set(NAM_KHOA), f"cây khai {sorted(khai)}, phải là {NAM_KHOA}"
    for khoa in NAM_KHOA:
        assert f'khoa: "{khoa}"' in shell, f"thanh dọc không có lối vào phân hệ con {khoa}"


def test_nhom_xo_ra_la_nut_chu_khong_phai_duong_dan():
    """Nhóm không dẫn đi đâu thì phải là <button>.

    Một thẻ <a> không có đích nói dối với hai nhóm người dùng cùng lúc: người dùng bàn phím bấm
    Enter không đi đâu cả, và trình đọc màn hình xướng "liên kết" trong khi đây là nút mở bảng.
    `aria-haspopup` cùng `aria-expanded` là cách nói thật.
    """
    src = _doc(SHELL)
    assert 'className={"grp grp-xo"' in src or "grp grp-xo" in src, "nút xổ ra phải dùng lớp .grp-xo"
    assert 'aria-haspopup="menu"' in src, "nút xổ ra phải khai là nút mở bảng"
    assert "aria-expanded={mo}" in src, "phải nói ra bảng đang mở hay đóng"
    assert 'role="menuitem"' in src, "mỗi mục trong bảng phải khai vai trò của nó"


def test_nhom_xo_ra_van_sang_khi_dang_o_trong_phan_he_con():
    """Đứng ở /phan-he/dhxe thì thanh "Điều hành" phải sáng.

    Thiếu chỗ này thì vào một phân hệ con xong nhìn lên thanh dọc không thấy nhóm nào sáng – thanh
    dọc mất hẳn khả năng trả lời câu "tôi đang ở đâu trong hệ thống".
    """
    src = _khong_ghi_chu(_doc(SHELL))
    assert re.search(r'g\.phans\?\.some\(\(p\) => isOn\(`/phan-he/\$\{p\.khoa\}`, path\)\)', src), \
        "dangO phải tính cả các phân hệ con, không chỉ href của chính nhóm"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  3. BẢNG XỔ RA — hai cái bẫy đã đo được trong mockup 18/9
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_bang_xo_ra_phai_ra_ngoai_thanh_doc():
    """`aside.side` có `overflow-y:auto`. Bảng nằm bên trong thì phần thò ra bị CẮT MẤT.

    Không phải bị che – bị cắt. Người dùng không cuộn tới được, và trên máy có thanh cuộn mảnh thì
    nhìn cứ như bảng chỉ có một mục. Nên bảng đi qua cổng React ra thẳng <body>, đúng cách đã dùng
    cho bảng Giao diện của TC-67.
    """
    src = _doc(SHELL)
    assert "createPortal" in src, "bảng xổ ra phải qua cổng ra ngoài <aside>, nếu không bị cắt"
    assert 'import { createPortal } from "react-dom"' in src, "thiếu khai báo createPortal"
    css = _khong_ghi_chu(_doc(CSS))
    # Luật của .xo-bang KHÔNG được lồng trong aside.side: bảng đã ra ngoài <aside> rồi, viết lồng
    # thì luật không bao giờ khớp và bảng ra trần trụi không định dạng.
    assert re.search(r'(^|\n)\.xo-bang\{', css), ".xo-bang phải là luật ở cấp ngoài cùng"
    assert not re.search(r'aside\.side[^\n{]*\.xo-bang', css), \
        ".xo-bang viết lồng trong aside.side thì không bao giờ khớp – bảng đã ra ngoài <aside>"


def test_duoi_nguong_ngan_keo_thi_xo_tai_cho_khong_bay_ra_ngoai_man_hinh():
    """Trên điện thoại, bay sang phải là bay HẲN ra ngoài màn hình.

    Đo trong mockup 18/9: màn rộng 390px, thanh dọc chiếm gần hết, bảng rơi vào toạ độ 388px – tức
    mất hẳn, không phải khuất một phần. Dưới ngưỡng ngăn kéo thì bảng vẽ TẠI CHỖ.

    Hai con số phải TRÙNG nhau: `NGUONG_NGAN_KEO` trong Shell.tsx và số trong @media của CSS. Lệch
    nhau thì có một dải bề rộng mà JS tưởng đang xổ ra bên phải còn CSS tưởng đang vẽ tại chỗ –
    bảng sẽ nằm sai chỗ đúng trong dải ấy, và không ai nghĩ tới việc thử đúng bề rộng đó.
    """
    src = _khong_ghi_chu(_doc(SHELL))
    m = re.search(r'NGUONG_NGAN_KEO\s*=\s*(\d+)', src)
    assert m, "thiếu hằng số ngưỡng ngăn kéo – ngưỡng viết rải rác thì sớm muộn lệch nhau"
    nguong = m.group(1)
    assert f'`(max-width:${{NGUONG_NGAN_KEO}}px)`' in src, \
        "phải hỏi matchMedia bằng chính hằng số ấy, không gõ lại con số"

    css = _khong_ghi_chu(_doc(CSS))
    # globals.css có NHIỀU khối @media cùng ngưỡng 900px – phải dò hết chứ không lấy khối đầu.
    # Bản nháp đầu của phép thử này chỉ lấy khối đầu tiên và báo hỏng oan; ghi lại để lần sau ai
    # sửa khuôn dò thì biết vì sao nó viết bằng finditer.
    khoi = next((m.group(1) for m in
                 re.finditer(r'@media \(max-width:%spx\)\{(.*?)\n\}' % nguong, css, re.S)
                 if ".xo-bang" in m.group(1)), None)
    assert khoi, (
        f"CSS phải có @media (max-width:{nguong}px) đưa .xo-bang về vẽ tại chỗ – "
        f"ngưỡng trong Shell.tsx là {nguong}, hai bên phải trùng")
    assert "position:static" in khoi, \
        "dưới ngưỡng ngăn kéo, .xo-bang phải thôi fixed – fixed ở đó là bay ra ngoài màn hình"


def test_mo_co_do_tre_va_khong_dung_re_chuot_tren_man_cam_ung():
    """Trả lời đúng hai lý do đã khiến anh Tuấn bỏ lối rê chuột ngày 13/9/2026.

    (a) "Đưa chuột ngang qua thanh dọc để tới chỗ khác là bảng bật ra chắn đường" → độ trễ MỞ:
        chuột lướt qua thì chưa kịp mở, chuột dừng lại mới là ý định.
    (b) "Máy bảng không có rê chuột" → hỏi `hover: hover`. Màn cảm ứng vẫn bắn mouseenter GIẢ sau
        cú chạm, nên không hỏi thì bảng tự mở tự đóng loạn lên trên điện thoại.

    Bỏ một trong hai là dựng lại đúng cái phiền đã khiến luật cũ bị bỏ.
    """
    src = _khong_ghi_chu(_doc(SHELL))
    assert re.search(r"setTimeout\(\(\)\s*=>\s*datMo\(true\),\s*\d+\)", src), \
        "MỞ phải có độ trễ"
    assert re.search(r"setTimeout\(\(\)\s*=>\s*datMo\(false\),\s*\d+\)", src), \
        "ĐÓNG phải chậm – chuột cần đi qua khoảng trống giữa thanh dọc và bảng"
    assert '"(hover: hover)"' in src, "phải hỏi máy có chuột thật không"


def test_bam_ra_ngoai_va_phim_esc_deu_dong_duoc_bang():
    """Một bảng chỉ đóng được bằng cách rê chuột ra là một cái bẫy trên máy cảm ứng."""
    src = _khong_ghi_chu(_doc(SHELL))
    assert 'e.key === "Escape"' in src, "Esc phải đóng được bảng"
    assert "mousedown" in src, "bấm ra ngoài phải đóng bảng"


# ══════════════════════════════════════════════════════════════════════════════════════════════
#  4. TRANG PHÂN HỆ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_chip_chuyen_nhanh_thay_cha_bang_con():
    """Dãy chip dưới cùng phải khớp với thanh dọc, không khớp với CAY_PHAN_HE.

    Nếu chip vẫn liệt kê hai phân hệ cha thì người đang đứng ở "Điều hành xe" nhìn xuống không
    thấy chip nào sáng, và bấm chip "Điều hành" lại rơi về mục lục gộp mà menu đã bỏ lối vào.
    """
    src = _doc(MUC_LUC)
    assert "CHIP_PHAN_HE" in src, "phải dựng danh sách chip riêng, không map thẳng CAY_PHAN_HE"
    assert "PHAN_HE_CON" in src, "danh sách chip phải đọc PHAN_HE_CON để thay cha bằng con"
    assert "CHIP_PHAN_HE.map(" in src, "phần vẽ chip phải dùng danh sách đã thay, không dùng cây gốc"
    assert not re.search(r'\{CAY_PHAN_HE\.map\(', src), \
        "còn vẽ chip thẳng từ CAY_PHAN_HE – hai phân hệ cha sẽ lại hiện ra"


def test_muc_dung_chung_duoc_noi_ra():
    """Hộp thư và hồ sơ khách là của CẢ HAI phòng bán hàng. Trang phải nói ra.

    Không nói thì người sửa tưởng màn hình ấy của riêng phòng mình, sửa xong mới biết phòng bên
    cạnh cũng đổi theo.
    """
    trang = _doc(MUC_LUC)
    assert "m.chung" in trang, "mục lục phải vẽ cờ dùng chung"
    assert "dùng chung" in trang, "cờ phải ghi bằng chữ người đọc hiểu được"
    css = _khong_ghi_chu(_doc(CSS))
    assert ".cay-co.chung{" in css, "cờ dùng chung phải có định dạng riêng"
    # Dùng màu CẢNH BÁO, không phải màu thông tin: đây là chỗ người sửa cần dừng lại một nhịp.
    assert re.search(r'\.cay-co\.chung\{[^}]*--vtos-warning', css), \
        "cờ dùng chung nên mang màu cảnh báo – sửa màn hình này thì phòng bên cạnh cũng đổi"


def test_nam_nhanh_dung_chung_dung_la_nam_nhanh_da_chot():
    """Đúng BỐN nhánh dùng chung ở hai phòng bán hàng, không nhiều hơn.

    Khai thừa thì cờ "dùng chung" mất nghĩa – dán lên mọi thứ thì nó không còn cảnh báo ai.

    ══ MỘT LUẬT BỊ SỬA, GHI LẠI CẢ HAI BÊN ══
    18/9/2026 (TC-70), phép thử này chốt BA nhánh: 3.1 Hộp thư, 3.2 Khách hàng, 3.5 Chăm sóc khách
    hàng. Lý do vẫn nguyên giá trị và KHÔNG bị bãi: cờ "dùng chung" chỉ có ích khi nó hiếm.

    19/9/2026 (TC-73), anh Tuấn giao dựng bảng cơ cấu tổ chức khối Kinh doanh. Nhánh 3.6 vào danh
    sách dùng chung, thành bốn. Đây KHÔNG phải nới cho tiện: sơ đồ chi nhánh → phòng → team → người
    đúng nghĩa là của cả hai phòng, và màn hình có sẵn ô đổi mảng để mỗi phòng xem cây của mình.
    Nhét nó vào riêng một phòng là buộc phòng kia đi vòng qua menu của phòng bạn để xem sơ đồ của
    chính mình — đúng cái phiền mà cờ "dùng chung" sinh ra để tránh.

    19/9/2026 (TC-74), nhánh 3.7 "Người bán hàng" vào tiếp, thành NĂM. Đối tác ghép lẻ bán được cả
    tour lẻ lẫn chỗ trong đoàn, nên danh mục ấy đúng là của cả hai phòng.

    ══ CẢNH BÁO CHO NGƯỜI SỬA TIẾP ══
    Vòng trước đã viết "con số BỐN là một con số chốt, nhánh thứ năm phải qua đúng cửa này một lần
    nữa" — và đây chính là lần ấy, chỉ cách một vòng. Giờ 5 trên 7 nhánh của nhóm Kinh doanh là dùng
    chung, tức là DÙNG CHUNG đã thành thông lệ còn RIÊNG mới là ngoại lệ. Một cái cờ dán lên đa số
    thì không còn cảnh báo được ai.

    Nhánh thứ sáu KHÔNG nên đi tiếp đường này. Đến đó thì việc phải làm là ĐẢO cờ: đánh dấu hai
    nhánh RIÊNG (3.3 Lẻ, 3.4 Đoàn) thay vì đánh dấu phần dùng chung. Ghi lại ở đây để lần sau không
    ai phải nghĩ lại từ đầu, và để việc đảo cờ là một quyết định chứ không phải một lần nới nữa.
    """
    khai = {k: chung for k, _cha, _lay, chung in _khai_phan_he_con(_doc(CAY))}
    assert set(khai["kdle"]) == {"3.1", "3.2", "3.5", "3.6", "3.7"}, f'kdle khai chung {khai["kdle"]}'
    assert set(khai["kddoan"]) == {"3.1", "3.2", "3.5", "3.6", "3.7"}, f'kddoan khai chung {khai["kddoan"]}'
    for k in ("dhtour", "dhxe", "hdv"):
        assert not khai[k], f"{k} không dùng chung nhánh nào với ai – khai {khai[k]}"


def test_bang_xo_ra_khong_lap_lai_ten_nhom():
    """══ TC-72 · 19/9/2026 — anh Tuấn: "em xoá bỏ chữ kinh doanh và chữ điều hành, không lặp lại."

    Tên nhóm vốn hiện ở BA chỗ cùng một lúc: trên chính cái nút bên cạnh bảng, trong tooltip khi
    rê chuột, và ở dòng tiêu đề trong bảng. Ba lần cho một thông tin thì hai lần sau chỉ làm mắt
    người đọc phải lọc.

    XOÁ CẢ HAI ĐẦU — thẻ trong Shell.tsx và lớp `.xo-dau` trong globals.css. Để lại lớp mồ côi là
    để người sau đọc thấy rồi dựng lại cái thẻ đã bỏ, tưởng mình đang vá một chỗ thiếu.

    VÀ THÔNG TIN KHÔNG ĐƯỢC MẤT: `aria-label` trên `.xo-bang` vẫn xướng tên nhóm cho trình đọc
    màn hình. Bỏ chữ VẼ RA chứ không bỏ chữ NÓI RA — cùng nếp với TC-69 lúc rút "Nhân sự – Hành
    chính" thành "HC – NS".
    """
    shell = _doc(SHELL)
    assert 'className="xo-dau"' not in shell, (
        "dòng tiêu đề trong bảng xổ ra đã bỏ 19/9/2026 — nó lặp lại đúng chữ đã có trên nút "
        "bên cạnh và trong tooltip"
    )
    css = _khong_ghi_chu(_doc(CSS))
    assert ".xo-dau{" not in css, "lớp .xo-dau còn mồ côi trong CSS — xoá cả lớp, đừng để lại"
    # Bỏ chữ vẽ ra thì chữ nói ra PHẢI còn, nếu không người dùng trình đọc màn hình nghe được một
    # bảng không tên và không biết mình vừa mở nhóm nào.
    assert re.search(r'className="xo-bang"[^>]*aria-label=\{g\.label\}', shell), (
        "bảng xổ ra phải giữ aria-label mang tên nhóm — bỏ cả chữ vẽ lẫn chữ nói là làm mất "
        "thông tin, không phải làm gọn"
    )


def test_trang_phan_he_tra_duoc_ca_hai_loai_khoa():
    """`timPhanHe` phải trả lời được cả khoá cha lẫn khoá con.

    Nhờ vậy trang /phan-he/[khoa] không phải biết hai loại khoá là hai thứ khác nhau – thêm một
    phân hệ con sau này chỉ phải khai ở PHAN_HE_CON, không phải sửa trang.
    """
    src = _khong_ghi_chu(_doc(CAY))
    than = src[src.find("export function timPhanHe"):]
    than = than[:than.find("\n}")]
    assert "CAY_PHAN_HE.find" in than and "PHAN_HE_CON.find" in than, \
        "timPhanHe phải tra cả hai bảng"
    assert "cayCuaPhanHeCon" in than, "khoá con phải dựng ra cây, không trả về undefined"


def test_duong_dan_cu_cua_hai_phan_he_cha_van_song():
    """/phan-he/khachhang và /phan-he/vanhanh mất lối vào từ menu nhưng KHÔNG được chết.

    Ai đã lưu dấu trang, hoặc màn hình khác còn trỏ tới, thì vẫn phải mở được. Xoá đi là bẻ gãy
    một đường đang có mà chẳng được gì.
    """
    cay = _doc(CAY)
    for khoa in ("khachhang", "vanhanh"):
        assert f'{{ khoa: "{khoa}"' in cay, \
            f"đã xoá phân hệ cha {khoa} khỏi cây – dấu trang cũ sẽ ra trang 'Không có phân hệ này'"
