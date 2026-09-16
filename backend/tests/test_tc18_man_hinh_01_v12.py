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
    vt = {t: s.index(t) for t in ("<TieuDe", "<DongLoc", "<KhoiQuyetDinh", "<KhoiDongTien", "<HangThe")}
    thu_tu = sorted(vt, key=lambda t: vt[t])
    assert thu_tu == ["<TieuDe", "<DongLoc", "<KhoiQuyetDinh", "<KhoiDongTien", "<HangThe"], \
        f"thứ tự khối trên màn hình 01 lệch bản vẽ V1.2: {thu_tu}"


def test_sau_o_lon_va_nam_the_nho():
    """TÁM THẺ → SÁU Ô LỚN + NĂM THẺ NHỎ (anh Tuấn chốt 16/9/2026, TC-42).

    Bản V1.2 chốt tám thẻ ngang hàng nhau. Trên bản chạy thật, tám thẻ ngang hàng hoá ra là tám
    con số ngang hàng — mà chúng không ngang hàng: "doanh thu 4,3 tỷ" chỉ có nghĩa khi đặt cạnh kế
    hoạch và kỳ trước, còn "93 tour sắp khởi hành" thì đọc xong là xong.

    Nên phép thử này canh HAI nhóm, và canh rằng chúng không lẫn vào nhau. Sáu mục phải nghĩ thì
    phải có biểu đồ; năm mục chỉ để liếc thì KHÔNG được có, vì hình trên chúng kéo mắt khỏi sáu ô
    trên — đúng điều anh Tuấn chốt khi chọn "thẻ số nhỏ, một hàng, không biểu đồ".
    """
    s = _ma(TRANG)
    khoi = s[s.index("const the: The[] = ["): s.index("];", s.index("const the: The[] = ["))]
    nhan = re.findall(r'nhan: "([^"]+)"', khoi)
    assert len(nhan) == 5, f"hàng thẻ nhỏ phải đúng NĂM mục, đang có {len(nhan)}: {nhan}"
    for can in ("Tour đang bán", "Tour chờ quyết toán", "Tour sắp khởi hành",
                "Đội xe hôm nay", "Marketing & PR"):
        assert can in nhan, f"thiếu thẻ “{can}” trong hàng thẻ nhỏ"
    assert "xu_huong:" not in khoi, (
        "Năm thẻ nhỏ KHÔNG được mang biểu đồ — chúng là con số để liếc, và hình trên chúng kéo "
        "mắt khỏi sáu ô lớn phía trên."
    )
    # SỬA 16/9/2026 (TC-44): hai ô đầu gộp vào <KhoiKetQuaKinhDoanh — vẫn sáu con số.
    for o in ("<KhoiKetQuaKinhDoanh", "<KhoiDongTien",
              "<KhoiPhaiThu", "<KhoiPhaiTra", "<KhoiTonDongMuc"):
        assert o in s, f"thiếu ô lớn {o} — anh Tuấn chốt đúng sáu ô."


def test_the_chua_co_nguon_phai_co_cua_nhap():
    """Ranh giới 09/9/2026: mỗi con số cần MỘT CỬA cho người dùng đưa vào.

    Một ô trống không kèm cửa là việc còn thiếu, không phải một ô trống bình thường – và nếu không
    ghi ra thì không ai biết phải đi hỏi bộ phận nào.
    """
    s = _ma(TRANG)
    khoi = s[s.index("const the: The[] = ["): s.index("];", s.index("const the: The[] = ["))]
    for the in re.findall(r'\{ nhan: "[^"]+".*?\},\n', khoi, re.S):
        if re.search(r'so: null', the):
            assert "cua:" in the and "ai:" in the, \
                f"thẻ chưa có nguồn mà không chỉ ra cửa nhập và bộ phận:\n{the.strip()[:160]}"
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
    s = _ma(DAU)
    i = s.index("export function KhoiQuyetDinh")
    than = s[i: s.index("export function", i + 10)]
    assert "slice(" not in than, "khối Cần quyết định không được cắt bớt hồ sơ"
    assert "{co.length} hồ sơ đang chờ" in s, "phải đếm ra số hồ sơ đang chờ"
