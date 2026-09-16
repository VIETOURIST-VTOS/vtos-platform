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
    vt = {t: s.index(t) for t in ("<TieuDe", "<DongLoc", "<KhoiQuyetDinh", "<TamThe", "<KhoiDongTien")}
    thu_tu = sorted(vt, key=lambda t: vt[t])
    assert thu_tu == ["<TieuDe", "<DongLoc", "<KhoiQuyetDinh", "<TamThe", "<KhoiDongTien"], \
        f"thứ tự khối trên màn hình 01 lệch bản vẽ V1.2: {thu_tu}"


def test_dung_tam_the_chi_tieu():
    """Tám thẻ, đúng tám – bản vẽ xếp hai hàng bốn thẻ."""
    s = _ma(TRANG)
    khoi = s[s.index("const tam: The[] = ["): s.index("];", s.index("const tam: The[] = ["))]
    nhan = re.findall(r'nhan: "([^"]+)"', khoi)
    assert len(nhan) == 8, f"bản vẽ chốt TÁM thẻ, đang có {len(nhan)}: {nhan}"
    for can in ("Doanh thu tháng", "Lợi nhuận trước thuế", "Tour đang bán", "Tour chờ quyết toán",
                "Tour sắp khởi hành", "Đội xe hôm nay", "Marketing & PR", "Tồn đọng cần xử lý"):
        assert can in nhan, f"thiếu thẻ “{can}” của bản vẽ V1.2"


def test_the_chua_co_nguon_phai_co_cua_nhap():
    """Ranh giới 09/9/2026: mỗi con số cần MỘT CỬA cho người dùng đưa vào.

    Một ô trống không kèm cửa là việc còn thiếu, không phải một ô trống bình thường – và nếu không
    ghi ra thì không ai biết phải đi hỏi bộ phận nào.
    """
    s = _ma(TRANG)
    khoi = s[s.index("const tam: The[] = ["): s.index("];", s.index("const tam: The[] = ["))]
    for the in re.findall(r'\{ nhan: "[^"]+".*?\},\n', khoi, re.S):
        if re.search(r'so: null', the):
            assert "cua:" in the and "ai:" in the, \
                f"thẻ chưa có nguồn mà không chỉ ra cửa nhập và bộ phận:\n{the.strip()[:160]}"
    assert "the-cua" in _ma(DAU), "thẻ rỗng phải vẽ được đường dẫn cửa nhập"


def test_man_hinh_01_chi_theo_thang_va_chi_duong_xem_quy_nam():
    """Anh Tuấn chốt 13/9: màn hình 01 chỉ hiển thị THÁNG; quý và năm xem ở báo cáo chi tiết.

    Không để một ô chọn có sẵn "Quý"/"Năm" mà bấm vào lại báo "chưa có nguồn" – đó là một lời hứa
    suông ngay trên màn hình đầu tiên. Thay bằng đường dẫn tới chỗ xem được thật.
    """
    dau, trang = _ma(DAU), _ma(TRANG)
    assert "tenThang" in dau, "hàng lọc phải in tháng báo cáo lấy từ lịch máy"
    assert 'href="/phan-he/baocao"' in dau, "thiếu đường dẫn sang chỗ xem theo quý và năm"
    for cam in ("theoQuy", 'value="quy"', "type Ky"):
        assert cam not in trang and cam not in dau, \
            f"còn tàn dư của ô chọn kỳ nhiều mức: {cam}"


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
