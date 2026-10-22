# -*- coding: utf-8 -*-
"""TC-18 · Màn hình 01 dựng lại theo bản vẽ "Bảng điều hành Chủ tịch" V1.2 (13/9/2026).

Bản vẽ đổi ba việc so với màn hình cũ, và cả ba đều dễ trôi ngược lại nếu không có chốt chặn:

  1. THỨ TỰ. Việc cần quyết định lên TRƯỚC các con số. Mở màn hình ra là thấy việc chờ mình, rồi
     mới tới kết quả – không phải lướt qua ba hàng chỉ số mới gặp.
  2. TÁM THẺ thay ba hàng KPI nhồi. Mỗi thẻ: một số chính, một dòng so sánh, một dòng trạng thái.
  3. RỖNG KHÁC KHÔNG. Thẻ chưa có nguồn ghi "Chưa có nguồn" kèm CỬA NHẬP – đúng ranh giới 09/9:
     mỗi con số phải có một cửa cho người dùng đưa số vào; không có cửa thì đó là việc còn thiếu.

BẢN TGĐ (SEC-02) không phải màn hình thứ hai: cùng một trang, đổi tên trang theo vai, còn tập dòng
thì MÁY CHỦ cắt. Phép thử ở đây canh rằng trình duyệt không tự cắt – cắt ở trình duyệt nghĩa là dòng
vẫn đã rời khỏi máy chủ và ai mở công cụ nhà phát triển cũng đọc được.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAU = os.path.join(ROOT, "web", "components", "DauManHinh01.tsx")
TRANG = os.path.join(ROOT, "web", "app", "page.tsx")
VH = os.path.join(ROOT, "web", "components", "KhoiVanHanh.tsx")


def _doc(p):
    return open(p, encoding="utf-8").read()


def _ma(p):
    """Chỉ mã chạy – chú thích nhắc tới một tên không tính là mã dùng tên ấy."""
    return re.sub(r'/\*.*?\*/|//[^\n]*|\{/\*.*?\*/\}', '', _doc(p), flags=re.S)


def test_viec_can_quyet_dinh_dung_truoc_cac_con_so():
    """Thứ tự bản vẽ: tiêu đề → hàng lọc → Cần quyết định → tám thẻ → dòng tiền."""
    s = _ma(TRANG)
    # TC-42: `<TamThe` → `<HangThe`, và hàng thẻ nhỏ nay đứng SAU sáu ô lớn. Luật giữ nguyên —
    # tiêu đề, hàng lọc và khối "Cần quyết định" vẫn phải đứng trước mọi con số.
    #
    # TC-62 (18/9/2026): `<DongLoc` rời khỏi danh sách vì nó không còn tồn tại — anh Tuấn chốt
    # "gộp thành 1 thanh ngang", hàng lọc nhập vào `<TieuDe`. Luật vẫn nguyên một chữ: đầu trang
    # → việc cần quyết định → rồi mới tới con số. Mặt cũ của luật (hàng lọc là một khối riêng
    # đứng giữa `<TieuDe` và `<KhoiQuyetDinh`) được canh ngược lại ngay dưới đây.
    #
    # TC-65 (18/9/2026): `<KhoiQuyetDinh` cũng rời danh sách — anh Tuấn chốt "gom lại thành 1 thanh
    # ngang", hàng nút chờ quyết nhập thẳng vào `<TieuDe`. LUẬT VẪN NGUYÊN MỘT CHỮ: việc chờ mình
    # quyết phải đứng TRƯỚC mọi con số. Nay nó đứng trước theo nghĩa mạnh hơn — nó nằm trong chính
    # dòng đầu tiên của trang. Vế canh ngược ("không dựng lại khối riêng") ở ngay dưới.
    #
    # TQ-1 (22/10/2026): `<HangThe` → `<KhoiVanHanh`. Anh Tuấn duyệt bản vẽ Tổng quan Vận hành v1.1
    # — hàng thẻ tour và khối tồn đọng gộp thành MỘT mục, đứng đúng chỗ hàng thẻ cũ. Luật giữ
    # nguyên: đầu trang trước, con số sau.
    vt = {t: s.index(t) for t in ("<TieuDe", "<KhoiDongTien", "<KhoiVanHanh")}
    thu_tu = sorted(vt, key=lambda t: vt[t])
    assert thu_tu == ["<TieuDe", "<KhoiDongTien", "<KhoiVanHanh"], \
        f"thứ tự khối trên màn hình 01 lệch bản vẽ V1.2: {thu_tu}"
    assert "<KhoiQuyetDinh" not in s, (
        "`<KhoiQuyetDinh` sống lại thành khối riêng — hàng nút chờ quyết phải nằm trên thanh "
        "ngang đầu trang (TC-65)."
    )
    assert "quyet_dinh={d.approvals" in s, (
        "Thanh ngang không còn nhận danh sách hồ sơ chờ quyết — việc chờ Chủ tịch biến mất khỏi "
        "màn hình mà không lỗi nào báo."
    )
    assert "<DongLoc" not in s, (
        "`<DongLoc />` sống lại trên trang — đầu trang phải là MỘT thanh ngang (TC-62)."
    )


def test_sau_o_lon_va_muc_van_hanh():
    """TÁM THẺ → SÁU Ô LỚN + HÀNG THẺ NHỎ (TC-42, 16/9/2026) → MỤC «VẬN HÀNH & CÔNG VIỆC» (TQ-1).

    SỬA 22/10/2026 (TQ-1) — anh Tuấn duyệt bản vẽ Tổng quan Vận hành v1.1: hàng thẻ nhỏ và khối
    Tồn đọng gộp thành một mục, vì hai thứ ấy trả lời CÙNG một câu hỏi ("hôm nay vận hành có gì
    phải xử lý"). Mảng `const the: The[]` không còn — phép thử cũ đếm sáu nhãn trong mảng ấy nay
    canh thẳng mục mới.

    LUẬT CỦA TC-42 GIỮ NGUYÊN MỘT CHỮ: những con số để LIẾC thì không mang biểu đồ. Mục mới chỉ có
    một thanh cơ cấu mức độ (không trục, không kỳ) — không nhập bộ vẽ biểu đồ nào. «Xe đang đi» đã
    chuyển xuống khối đội xe từ TC-72 nên không còn trong danh sách.
    """
    s = _ma(TRANG)
    vh = _ma(VH)
    assert "const the: The[]" not in s, "hàng thẻ cũ sống lại bên cạnh mục mới — một số hai chỗ (TC-40)"
    for can in ("Việc nghiêm trọng", "Quá hạn quyết toán", "Tour đang bán", "Tour đang đi",
                "Sắp khởi hành", "Chờ quyết toán", "Tồn đọng công việc", "Khách tiềm năng mới"):
        assert can in vh, f"mục Vận hành & công việc thiếu ô “{can}”"
    assert "Xe đang đi" not in vh, (
        "«Xe đang đi» đã chuyển xuống khối Hiệu quả đội xe (TC-72). Để lại ở mục Vận hành là cùng "
        "một con số hiện ở hai chỗ — chỗ mới canh ở test_xe_dang_di_nam_o_khoi_hieu_qua_doi_xe.")
    assert "BieuDo" not in vh and "xu_huong" not in vh, (
        "Ô trong mục Vận hành KHÔNG mang biểu đồ — chúng là con số để liếc (TC-42)."
    )
    # Năm ô lớn còn lại + mục Vận hành giữ chỗ của ô thứ sáu (Tồn đọng).
    for o in ("<KhoiKetQuaKinhDoanh", "<KhoiDongTien",
              "<KhoiPhaiThu", "<KhoiPhaiTra", "<KhoiVanHanh"):
        assert o in s, f"thiếu khối {o} trên màn hình 01."


def test_xe_dang_di_nam_o_khoi_hieu_qua_doi_xe():
    """Chỗ MỚI của «Xe đang đi» sau TC-72 (20/10/2026) — phép thử này canh đúng chỗ ấy.

    Bỏ một con số khỏi chỗ cũ và đặt nó vào chỗ mới là HAI việc. Chỉ canh việc thứ nhất — tức là
    chỉ hạ số thẻ từ sáu xuống năm — là hạ cổng cho vừa dữ liệu: ngày nào ai đó gỡ hẳn ô ấy khỏi
    khối đội xe, cả bộ phép thử vẫn xanh và không ai biết màn hình đã mất một con số.
    """
    s = _ma(TRANG)
    assert "xe={sec.xe_hom_nay}" in s, (
        "page.tsx không còn truyền `xe` xuống KhoiHieuQuaXe — ô «Xe đang đi» mất nguồn.")
    khoi = _ma(os.path.join(ROOT, "web", "components", "KhoiV14.tsx"))
    assert "Xe đang đi" in khoi, (
        "Ô «Xe đang đi» không còn trong khối Hiệu quả đội xe. TC-72 chuyển nó xuống đây; mất ở "
        "đây là mất hẳn khỏi màn hình.")


def test_the_chua_co_nguon_phai_co_cua_nhap():
    """Ranh giới 09/9/2026: mỗi con số cần MỘT CỬA cho người dùng đưa vào.

    Một ô trống không kèm cửa là việc còn thiếu, không phải một ô trống bình thường – và nếu không
    ghi ra thì không ai biết phải đi hỏi bộ phận nào.

    SỬA 22/10/2026 (TQ-1): ô «Khách tiềm năng mới» chuyển vào mục Vận hành; nó vẫn rỗng, vẫn phải
    ghi bộ phận (Marketing) và cửa nhập — và vẫn KHÔNG được thay bằng 0.
    """
    vh = _ma(VH)
    k = vh[vh.index("Khách tiềm năng mới"):]
    k = k[:k.index("</section>")]
    assert "Chưa có nguồn" in k and "Marketing" in k, "ô rỗng phải ghi «Chưa có nguồn» và bộ phận"
    assert 'href="/leads?tab=leads"' in k, "ô rỗng phải chỉ ra cửa nhập"
    assert "the-cua" in _ma(DAU), "thẻ rỗng phải vẽ được đường dẫn cửa nhập"


def test_o_chon_ky_chi_mo_khi_co_so_that_dang_sau():
    """SỬA 16/9/2026 (TC-42) — QUYẾT ĐỊNH 13/9 BỊ THAY, VÀ ĐÂY LÀ LÝ DO.

    Bản 13/9 cấm ô chọn Tháng/Quý/Năm trên màn hình 01, vì lúc ấy máy chủ mới tính theo tháng: một
    ô chọn ba kỳ mà bấm vào lại báo "chưa có nguồn" là lời hứa suông ngay trên màn hình đầu tiên.
    Cái bị cấm là LỜI HỨA SUÔNG, không phải ô chọn.

    Nay `services/xu_huong.doc_theo_ky` cộng được quý và năm từ chính các tháng, nên đằng sau ô
    chọn có số thật — và anh Tuấn chốt 16/9 là "doanh thu và lợi nhuận phân ra theo tháng, quý,
    năm". Luật giữ nguyên, chỉ sự thật đổi.

    Phép thử nay canh đúng cái luật ấy: có ô chọn thì phải có nguồn, và hàng lọc vẫn phải chỉ ra
    chỗ xem báo cáo đầy đủ.
    """
    dau = _ma(DAU)
    assert "tenThang" in dau, "hàng lọc phải in tháng báo cáo lấy từ lịch máy"
    assert 'href="/phan-he/baocao"' in dau, "thiếu đường dẫn sang chỗ xem theo quý và năm"

    # SỬA 16/9/2026 lần hai (TC-44): ô chọn ba kỳ chuyển sang khối Kết quả kinh doanh, và cách nó
    # lấy số đổi hẳn — không còn chọn nhánh trong một gói `ba_ky` dựng sẵn, mà HỎI máy chủ đúng kỳ
    # đang chọn. Nhờ vậy lối lui về bộ số của tháng không còn chỗ tồn tại: gửi sai bề rộng thì máy
    # chủ từ chối bằng 422 chứ không trả bừa. Luật y nguyên, chỗ canh đi theo nó.
    import pathlib
    goc = pathlib.Path(ROOT)
    khoi = (goc / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx").read_text(encoding="utf-8")
    assert '{ ma: "quy", ten: "Quý" }' in khoi, "ô chọn ba kỳ phải nằm ở khối Kết quả kinh doanh"
    assert "ket-qua-kinh-doanh?kind=" in khoi, (
        "Mỗi kỳ phải HỎI máy chủ đúng kỳ ấy. Lấy chuỗi tháng làm lối lui cho quý là nói dối bằng "
        "giao diện — người đọc kết luận quý bằng tháng, chứ không kết luận là chưa có số."
    )
    kq = (goc / "backend" / "app" / "services" / "ket_qua_kinh_doanh.py").read_text(encoding="utf-8")
    assert "không phải bề rộng" in kq, "máy chủ phải TỪ CHỐI mã kỳ sai bề rộng, không đoán hộ"
    xh = (goc / "backend" / "app" / "services" / "xu_huong.py").read_text(encoding="utf-8")
    assert "def doc_theo_ky" in xh, "nguồn số của quý và năm phải có thật ở máy chủ"


def test_ngay_bao_cao_lay_theo_lich_may_va_khong_vo_hydration():
    """Anh Tuấn chốt: ngày báo cáo = hôm nay theo lịch live.

    Tính lúc dựng thì máy chủ và trình duyệt ra hai giá trị khác nhau và React kêu hydration
    mismatch – lỗi nằm im trong console, không ai thấy. Nên phải lấy trong useEffect.
    """
    s = _ma(DAU)
    assert "useEffect" in s and "new Date()" in s, "ngày báo cáo phải lấy từ lịch máy"
    m = re.search(r'export function useHomNay\(\).*?\n\}', s, re.S)
    assert m and "useEffect" in m.group(0), "ngày hôm nay phải đặt trong useEffect, không tính lúc dựng"


def test_ban_tgd_doi_ten_trang_chu_khong_cat_dong_o_trinh_duyet():
    """SEC-02: cắt dòng là việc của MÁY CHỦ.

    Trình duyệt được phép đổi CHỮ theo vai (tên trang, tên khối). Nó không được phép ẩn DỮ LIỆU
    theo vai: dòng bị ẩn ở đây thì vẫn đã rời khỏi máy chủ, và ai mở công cụ nhà phát triển cũng
    đọc được.
    """
    s = _ma(DAU)
    assert '"Bảng điều hành Tổng giám đốc"' in s, "thiếu tên trang của bản TGĐ"
    assert '"Bảng điều hành Chủ tịch"' in s, "thiếu tên trang của bản Chủ tịch"
    # Không có nhánh nào lọc DỮ LIỆU theo vai. Đổi nhãn thì được, lọc số thì không.
    for xau in re.findall(r'vai === "\w+"', s):
        i = s.index(xau)
        doan = s[i: i + 200]
        assert "filter" not in doan and "slice(" not in doan, \
            f"đang cắt dữ liệu theo vai ở trình duyệt – việc ấy phải làm ở máy chủ: {doan[:120]}"


def test_khong_gioi_han_so_ho_so_can_quyet_dinh():
    """Anh Tuấn chốt 13/9: KHÔNG giới hạn hồ sơ. Bản vẽ V1.2 ghi "tối đa 5", nhưng cắt ở năm nghĩa
    là hồ sơ thứ sáu nằm ngoài tầm mắt đúng người được quyền quyết nó – mà máy chủ chưa xếp thứ tự
    ưu tiên, nên "năm cái đầu" chỉ là năm cái ngẫu nhiên.

    SỬA 16/9/2026 (TC-41) — LUẬT GIỮ NGUYÊN, PHÉP SOÁT THU HẸP LẠI ĐÚNG CHỖ NÓ CANH.
    Bản cũ cấm chuỗi "slice(" trong TOÀN BỘ tệp DauManHinh01.tsx. Tệp ấy nay còn chứa
    `docHoKeHoach`, nơi kê tên hai pháp nhân đầu rồi đếm phần còn lại — một phép cắt hoàn toàn
    chính đáng trên một DÒNG CHỮ, không phải trên danh sách hồ sơ chờ quyết.

    Đây đúng kiểu phép soát tự bắt oan mình: nó cấm một chuỗi ký tự thay vì cấm một hành vi, nên
    lần đầu có người viết `slice` cho việc khác là nó báo đỏ. Nay chỉ soi THÂN HÀM KhoiQuyetDinh.
    """
    # TC-65 (18/9/2026) · CHỖ SOÁT ĐỔI, LUẬT KHÔNG ĐỔI. Hàng nút chờ quyết nhập vào `TieuDe`, nên
    # thân hàm phải soi là `TieuDe`. Và thẻ nhãn "{co.length} hồ sơ đang chờ" đã bỏ theo chốt của
    # anh Tuấn ("bỏ chữ chờ chủ tịch quyết") — nó đếm đúng số nút đứng ngay cạnh nó, tức nói lại
    # một điều mắt đã thấy. Luật CÒN NGUYÊN và là luật quan trọng hơn: KHÔNG CẮT BỚT hồ sơ.
    s = _ma(DAU)
    i = s.index("export function TieuDe")
    than = s[i: s.index("export function", i + 10)]
    assert "slice(" not in than, "hàng nút Cần quyết định không được cắt bớt hồ sơ"
    assert "cho.map(" in than, "phải bày TOÀN BỘ danh sách hồ sơ chờ quyết, không cắt"
    assert "hồ sơ đang chờ" not in s, (
        "Thẻ nhãn đếm hồ sơ sống lại — nó đếm đúng số nút đứng ngay cạnh (TC-65)."
    )
