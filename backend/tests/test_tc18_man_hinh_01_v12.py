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
    """TÁM THẺ → SÁU Ô LỚN + HÀNG THẺ NHỎ (TC-42, 16/9) → MỤC «VẬN HÀNH & CÔNG VIỆC» (TQ-1, 22/10)
    → KHỐI LỒNG + MỘT KHỐI VIỆC (QT-1 và QT-2, Chủ tịch chốt 23–24/10/2026).

    HAI NHÃN RỜI DANH SÁCH VÌ CHỦ TỊCH BẢO GỘP, KHÔNG PHẢI VÌ CHÚNG BIẾN MẤT.
      · «Quá hạn quyết toán» (QT-1) — Chủ tịch nhìn màn hình và hỏi hai ô «Quá hạn quyết toán»
        và «Chờ quyết toán» khác nhau chỗ nào. Đo ra: ô nhỏ là MỘT LÁT nằm trọn trong nhóm A của
        ô lớn (681 ⊂ 709 ⊂ 1.742 hôm đo), mà hai ô đứng cách nhau một hàng và không chỗ nào nói
        thế — đọc lướt thành hai cách đếm một việc. Nay nó là một dòng LỒNG trong khối «Quyết toán».
      · «Tồn đọng công việc» (QT-2) — gộp vào khối «Việc nghiêm trọng», vì hai khối trả lời cùng
        một câu hỏi và cùng đếm trên một tập hồ sơ.

    VÌ SAO KHÔNG CHỈ XOÁ HAI NHÃN KHỎI DANH SÁCH NÀY. Xoá là hạ cổng: ngày nào ai đó gỡ hẳn con
    số quá hạn, hoặc gỡ nhóm mức độ, khỏi màn hình thì bộ phép thử vẫn xanh và không ai biết màn
    hình vừa mất một con số. Đúng cái bẫy `test_xe_dang_di...` dựng ra để tránh khi TC-72 chuyển
    «Xe đang đi» đi chỗ khác. Nên phép thử ĐI THEO hai con số ấy tới CHỖ MỚI và canh ở đó.

    LUẬT CỦA TC-42 GIỮ NGUYÊN MỘT CHỮ: những con số để LIẾC thì không mang biểu đồ. Hai khối ưu
    tiên chỉ có một thanh cơ cấu (không trục, không kỳ) — không nhập bộ vẽ biểu đồ nào.
    """
    s = _ma(TRANG)
    vh = _ma(VH)
    assert "const the: The[]" not in s, "hàng thẻ cũ sống lại bên cạnh mục mới — một số hai chỗ (TC-40)"
    for can in ("Việc nghiêm trọng", "Quyết toán", "Tour đang bán", "Tour đang đi",
                "Sắp khởi hành", "Khách tiềm năng mới"):
        assert can in vh, f"mục Vận hành & công việc thiếu ô “{can}”"

    # ── «Quá hạn quyết toán» ở CHỖ MỚI: một dòng lồng trong khối Quyết toán ──────────────────
    assert "vh-trong" in vh, (
        "nhóm lồng (`vh-trong`) biến mất — khối Quyết toán trở lại kiểu danh sách phẳng, và lúc "
        "ấy không chỗ nào nói con số quá hạn nằm TRONG nhóm «Kết thúc · chờ ĐIỀU HÀNH».")
    # Canh Ô ĐỌC ĐƯỢC, không canh chuỗi `{so(cq.qua_han)}` chung chung: chuỗi ấy CÒN nằm trong
    # `aria-label` của thanh cơ cấu, nên gỡ hẳn dòng hiện số mà phép thử vẫn xanh. Chính bản đầu
    # của phép thử này mắc đúng lỗi ấy và lượt kiểm ngược bắt được — cùng hình dạng với lỗ `qt2_2`
    # mà làn R1 tìm ra hôm 24/10. Một phép thử canh chuỗi có mặt ở hai chỗ thì nó canh chỗ dễ hơn.
    assert '<span className="v">{so(cq.qua_han)}</span>' in vh, (
        "dòng HIỆN con số tour quá hạn không còn trên mục Vận hành (chuỗi trong aria-label không "
        "tính — người đọc không nhìn thấy nó). QT-1 chuyển con số này vào khối Quyết toán; mất ở "
        "đây là mất hẳn khỏi màn hình.")
    assert "<b>QUÁ HẠN</b>" in vh, "dòng quá hạn mất nhãn — còn số mà không ai biết số ấy đếm gì."
    assert 'href="/?xem=qua-han"' in vh, (
        "mất lối sang danh sách tour quá hạn. Con số còn trên màn mà không mở ra xem được thì "
        "Điều hành không biết phải đi đòi chuyến nào.")

    # ── «Tồn đọng công việc» ở CHỖ MỚI: gộp vào khối Việc nghiêm trọng ───────────────────────
    assert "(v.theo_muc || [])" in vh, (
        "cơ cấu theo mức độ — phần việc của khối Tồn đọng cũ — không còn được vẽ. QT-2 gộp nó "
        "vào khối Việc nghiêm trọng; gỡ ở đây là mất hẳn.")
    assert "{so(v.chua_anh_xa)}" in vh, (
        "số cảnh báo CHƯA xác định được hồ sơ biến mất. Đây là số KHÔNG nằm trong bất kỳ mức độ "
        "nào, nên bỏ nó đi là phần còn lại cộng không đủ mà màn hình vẫn trông bình thường.")
    assert '"/?xem=viec"' in vh, "mất lối sang danh sách toàn bộ công việc."

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
    """VH-24 (Chủ tịch 12/11/2026, chốt «1.1.1»): đầu trang chủ chỉ còn TÊN BÀN + ô ngày; việc chờ lên hai nút
    «Công việc» / «Chờ duyệt» trên thanh ngang (Shell + `GET /dashboard/dem`); bỏ «Quý và năm →» và nút In
    (in bằng Ctrl+P, kiểu in giữ nguyên). Luật cũ còn sống được canh lại ở `test_vh24_ban_chu_tich.py`.
    Ô chọn quý/năm vẫn phải có NGUỒN THẬT ở khối Kết quả kinh doanh (TC-44) — phần ấy không đổi."""
    import pathlib
    goc = pathlib.Path(ROOT)
    dau = _ma(DAU)
    assert "Quý và năm →" not in dau[dau.index("export function TieuDe"):], "«Quý và năm →» sống lại trên đầu trang (VH-24 đã bỏ)"
    khoi = (goc / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx").read_text(encoding="utf-8")
    assert '{ ma: "quy", ten: "Quý" }' in khoi, "ô chọn ba kỳ phải nằm ở khối Kết quả kinh doanh"
    assert "ket-qua-kinh-doanh?kind=" in khoi
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
    assert '"Bàn làm việc Chủ tịch HĐQT"' in s, "thiếu tên trang của bản Chủ tịch"
    # Không có nhánh nào lọc DỮ LIỆU theo vai. Đổi nhãn thì được, lọc số thì không.
    for xau in re.findall(r'vai === "\w+"', s):
        i = s.index(xau)
        doan = s[i: i + 200]
        assert "filter" not in doan and "slice(" not in doan, \
            f"đang cắt dữ liệu theo vai ở trình duyệt – việc ấy phải làm ở máy chủ: {doan[:120]}"


def test_khong_gioi_han_so_ho_so_can_quyet_dinh():
    """Anh Tuấn chốt 13/9: KHÔNG giới hạn hồ sơ chờ quyết. VH-24 (Chủ tịch 12/11/2026, chốt «1.1.1»): đầu trang chủ chỉ còn TÊN BÀN + ô ngày; việc chờ lên hai nút
    «Công việc» / «Chờ duyệt» trên thanh ngang (Shell + `GET /dashboard/dem`); bỏ «Quý và năm →» và nút In
    (in bằng Ctrl+P, kiểu in giữ nguyên). Luật cũ còn sống được canh lại ở `test_vh24_ban_chu_tich.py`.
    Nên chỗ canh đi theo danh sách: nút «Chờ duyệt» bày đủ, máy chủ không cắt."""
    import pathlib
    goc = pathlib.Path(ROOT)
    shell = (goc / "web" / "components" / "Shell.tsx").read_text(encoding="utf-8")
    than = shell[shell.index("function NutViec"):shell.index("// Trạng thái THU/BUNG")]
    assert "ds.map(" in than and "slice(" not in than, "nút «Chờ duyệt» phải bày TOÀN BỘ danh sách, không cắt"
    r = (goc / "backend" / "app" / "api" / "v1" / "routes.py").read_text(encoding="utf-8")
    ep = r[r.index("def dashboard_dem"):r.index('@router.get("/dashboard", tags')]
    assert "[:" not in ep, "cửa đếm không được cắt bớt danh sách việc"
