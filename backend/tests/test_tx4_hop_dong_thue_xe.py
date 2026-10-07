# -*- coding: utf-8 -*-
"""TX-4 · Hợp đồng thuê xe riêng — Chủ tịch chọn 07/10/2026.

> "Tạo hợp đồng thuê xe như một tour rút gọn, không sửa bảng `dispatch_orders`. Kèm theo phải có
> **cờ tách loại** trên tour, nếu không doanh thu thuê xe chạy lẫn vào doanh thu tour."

Hai câu ấy chia vòng này làm hai nửa, và nửa thứ hai mới là nửa khó.

NỬA DỄ — hình của hợp đồng. Không bảng mới, không cột mới, không bản nâng cấp: `tours.tour_type`
đã là `String(20)` và `thue_xe` là một giá trị mới chưa có dòng nào. Lệnh điều xe gắn vào được vì
đã có một chuyến đứng sau. Mọi cổng (biên kế hoạch, điểm dừng nghỉ) áp y như chuyến khác.

NỬA KHÓ — CỜ TÁCH LOẠI KHÔNG PHẢI MỘT GIÁ TRỊ, MÀ LÀ MỘT CÁCH HỎI. Trước vòng này câu hỏi "chuyến
này có phải tour trọn gói không" được hỏi ở 26 chỗ bằng đúng một hình: `tour_type != "non_package"`
— PHỦ ĐỊNH MỘT GIÁ TRỊ. Thêm `thue_xe` vào bảng mà không đổi hình ấy thì hợp đồng thuê xe TỰ ĐỘNG
chui vào doanh thu tour, quỹ thưởng Điều hành và chỉ tiêu doanh số của sale — không một dòng mã
nào phải sửa, và không một phép thử nào đỏ. Đúng thứ Chủ tịch dặn đừng để xảy ra.

Nên vòng này đổi câu hỏi từ phủ định sang KHẲNG ĐỊNH (`TOUR_TRON_GOI` / `KHONG_TRON_GOI`), và bộ
hàng rào này canh bảy điều — mỗi điều là một đường hợp đồng thuê xe có thể lẻn vào chỗ không phải
của nó.
"""
import os
import sys
import io
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.core import (TOUR_TYPES, TOUR_TRON_GOI, KHONG_TRON_GOI,   # noqa: E402
                             LOAI_CHUYEN_CU)
from app.services import segments as SEG                                # noqa: E402
from app.services import doanh_thu_kd as DT                             # noqa: E402
from app.services import ket_qua_that as KQT                            # noqa: E402
from app.services import lai_lo_tour as LL                              # noqa: E402

# Những tệp hỏi câu "có phải tour trọn gói không" để CỘNG TIỀN hoặc để XẾP LOẠI. Danh sách này là
# kết quả một lần rà tay 07/10/2026; phép thử ở dưới giữ cho kết quả ấy không mòn.
TEP_TIEN = (
    ("app", "services", "misa.py"),
    ("app", "services", "lai_lo_tour.py"),
    ("app", "services", "sales_reports.py"),
    ("app", "services", "rules.py"),
    ("app", "services", "ngoai_le.py"),
    ("app", "api", "v1", "routes.py"),
)


def _doc(*phan) -> str:
    return io.open(os.path.join(GOC, *phan), encoding="utf-8").read()


def test_tx4_1_hai_danh_sach_phu_kin_bang_loai_chuyen():
    """Phép thử QUAN TRỌNG NHẤT của tệp này, và nó phải đỏ ngay khi ai đó thêm loại chuyến thứ bảy.

    Thông điệp lỗi cố ý nói ra hai lựa chọn, vì người gặp nó là người vừa thêm một loại chuyến và
    đang ở đúng lúc phải trả lời: loại này CÓ phải một tour trọn gói không? Trả lời sai thì tiền
    chảy nhầm; không trả lời thì nó chảy nhầm mà không ai biết.
    """
    assert "thue_xe" in TOUR_TYPES, "mất giá trị thue_xe — hợp đồng thuê xe không còn chỗ đứng"
    chung = set(TOUR_TRON_GOI) & set(KHONG_TRON_GOI)
    assert not chung, f"một loại chuyến nằm ở CẢ HAI danh sách: {sorted(chung)}"
    thieu = set(TOUR_TYPES) - set(TOUR_TRON_GOI) - set(KHONG_TRON_GOI)
    assert not thieu, (
        f"Loại chuyến chưa ai xếp: {sorted(thieu)}. Mỗi loại phải nằm ở ĐÚNG MỘT trong hai danh "
        "sách của models/core.py. Là tour trọn gói (có giá một khách, có đoàn khách, cộng vào "
        "doanh thu tour và sinh quỹ thưởng Điều hành) thì khai vào TOUR_TRON_GOI; bán theo từng "
        "việc thì khai vào KHONG_TRON_GOI. Không khai là để nó tự chảy vào doanh thu tour.")
    # Giá trị khai mà KHÔNG có trong bảng nhãn thì chỉ chấp nhận khi nó được khai là GIÁ TRỊ CŨ,
    # kèm lý do. Không có ngoại lệ này thì người sau sẽ xoá `"package"` cho phép thử hết đỏ — và
    # xoá nó là làm mọi chuyến cũ biến mất khỏi doanh thu, một lần siết nhầm không ai nhìn ra.
    thua = (set(TOUR_TRON_GOI) | set(KHONG_TRON_GOI)) - set(TOUR_TYPES) - set(LOAI_CHUYEN_CU)
    assert not thua, f"danh sách khai loại chuyến không còn tồn tại và cũng không khai là cũ: {sorted(thua)}"
    assert "package" in TOUR_TRON_GOI, (
        "`package` là cách viết CŨ của 'tour trọn gói' — hơn hai mươi tệp phép thử dựng chuyến bằng "
        "giá trị ấy, và phép lọc cũ `!= \"non_package\"` vẫn nhận nó. Bỏ ra là làm mọi chuyến mang "
        "giá trị ấy biến mất khỏi doanh thu, quỹ thưởng và bản xuất MISA.")


def test_tx4_2_khong_con_cho_nao_hoi_bang_phep_phu_dinh():
    """`!= "non_package"` nghĩa là "mọi thứ trừ một cái" — đúng hôm nay, sai vào ngày có cái thứ ba.

    Phép thử đọc MÃ NGUỒN vì đây là một lỗi hình thức: chạy thử không bắt được, bởi mọi con số vẫn
    ra một giá trị trông hợp lý. Chỉ có chính dòng mã mới nói được là nó hỏi sai câu.
    """
    pham = []
    for tep in TEP_TIEN:
        s = _doc(*tep)
        for i, dong in enumerate(s.splitlines(), 1):
            if re.search(r'tour_type\s*!=\s*["\']non_package["\']', dong):
                pham.append(f"{'/'.join(tep)}:{i}")
    assert not pham, (
        "Còn chỗ hỏi 'có phải tour trọn gói không' bằng cách phủ định một giá trị. Đổi thành "
        f"`Tour.tour_type.in_(TOUR_TRON_GOI)`, nếu không loại chuyến mới sẽ tự chui vào: {pham}")


def test_tx4_3_quy_thuong_dieu_hanh_khong_roi_vao_ty_le_cua_phong_khac():
    """Chỗ lệch tiền thẳng và im lặng nhất — một `.get()` có giá trị rơi cuối cùng.

    `settlement_summary` tra tỷ lệ quỹ thưởng bằng một bảng keyed theo loại chuyến, và trước vòng
    này giá trị rơi là `"quy_dh_doan"` — tỷ lệ CAO NHẤT. Loại chuyến nào không có tên trong bảng
    đều ăn tỷ lệ của tour đoàn mà không ai gõ một con số nào.
    """
    s = _doc("app", "services", "rules.py")
    than = s[s.index("def settlement_summary("):]
    than = than[:than.index("\ndef ", 1)]
    bang = re.search(r'key = \{(.*?)\}\.get\(tour\.tour_type', than, re.S)
    assert bang, "không còn đọc được bảng tra tỷ lệ quỹ — nếu đổi hình thì sửa phép thử này kèm lý do"
    for loai in TOUR_TYPES:
        assert f'"{loai}"' in bang.group(1), (
            f"loại chuyến '{loai}' không có tên trong bảng tra tỷ lệ quỹ thưởng Điều hành, nên nó "
            "rơi vào giá trị mặc định. Khai đích danh — kể cả khi câu trả lời là KHÔNG CÓ QUỸ.")
    assert '"thue_xe": ""' in bang.group(1), (
        "hợp đồng thuê xe phải khai RỖNG: quỹ ấy trả cho việc điều hành một chuyến (dựng chương "
        "trình, gom nhà cung cấp, chạy đoàn), và cho thuê một chiếc xe không có việc ấy. Muốn có "
        "quỹ cho đội xe thì đó là một tham số mới và một quyết định riêng.")


def test_tx4_4_thue_xe_khong_thuoc_mang_kinh_doanh_nao():
    """Mảng Lẻ và mảng Đoàn là hai PHÒNG BÁN HÀNG. Thuê xe không phải hàng của phòng nào."""
    class _T:
        def __init__(self, loai, ma=""):
            self.tour_type, self.code = loai, ma

    assert SEG.mang_of(_T("thue_xe")) == "", "thuê xe bị xếp vào một mảng kinh doanh"
    assert SEG.mang_of(_T("thue_xe", "MICE-01")) == "doan", (
        "quy ước mã MICE vẫn phải thắng — nếu ai đó đặt mã MICE cho hợp đồng thuê xe thì đó là dữ "
        "liệu cần người sửa, và `segments.lech_quy_tac()` là chỗ nói ra")
    # Bộ lọc SQL của mảng Lẻ dựng từ danh sách DƯƠNG, nên thuê xe không lọt vào.
    assert "thue_xe" not in SEG.LE_TYPES and "thue_xe" not in SEG.DOAN_TYPES


def test_tx4_5_moi_bang_doanh_thu_co_ngan_rieng_cho_thue_xe():
    """Giữ nó trong một ngăn tên là "khác" vẫn là chạy lẫn — chỉ là lẫn ở chỗ khó thấy hơn."""
    assert "thue_xe" in DT.LUONG, "bảng doanh thu Kinh doanh chưa có luồng thuê xe"
    assert "thue_xe" in KQT.NGAN, "bảng Kết quả kinh doanh chưa có ngăn thuê xe"
    assert "dich_vu_le" in KQT.NGAN, (
        "ngăn 'khac' phải tách ra dịch vụ lẻ — gộp hai thứ khác nhau vào một ngăn tên là 'khác' "
        "thì con số tổng ở đầu màn hình không cộng ngược lại được từ các dòng bên dưới")

    class _T:
        tour_type, code = "thue_xe", "HDTX-01"
    assert DT.luong_cua(_T()) == "thue_xe", (
        "hợp đồng thuê xe bị gọi là dịch vụ lẻ — một lời nói sai, không phải một phép tính sai, "
        "và vì thế khó thấy hơn")
    assert LL.LOAI_DONG.get("thue_xe") == "thue_xe", "bảng Lãi lỗ tour dán nhãn sai cho dòng thuê xe"
    assert LL.LOAI_DONG.get("non_package") == "dich_vu_le"

    # Màn hình Chủ tịch phải IN ra đủ các ngăn, không chỉ hai. In thiếu thì phần chênh không có tên.
    dash = _doc("app", "services", "dashboard.py")
    than = dash[dash.index("def doanh_thu_phong("):]
    than = than[:than.index("\ndef ", 1)]
    assert "KQT.NGAN" in than, (
        "màn hình Chủ tịch còn in danh sách ngăn viết cứng; thêm một ngăn ở ket_qua_that thì màn "
        "hình đứng yên và hai con số trên cùng một màn hình thôi khớp nhau")


def test_tx4_6_khong_tinh_chi_tieu_doanh_so_va_khong_sinh_hoa_hong():
    """Chỉ tiêu doanh số dẫn thẳng tới tiền hoa hồng của một người thật — chặn hai lớp ở đây là rẻ."""
    s = _doc("app", "services", "sales_reports.py")
    than = s[s.index("def kinh_doanh("):]
    than = than[:than.index("\ndef ", 1)]
    assert "TOUR_TRON_GOI" in than, "khung truy vấn chỉ tiêu doanh số chưa lọc bằng danh sách dương"
    assert re.search(r"la_tour\s*=.*TOUR_TRON_GOI", than), (
        "mất lớp canh thứ hai ngay tại dòng cộng chỉ tiêu. `not is_doan(...)` là một phép NHỊ "
        "PHÂN: mọi thứ không phải đoàn đều rơi vào nhánh Lẻ, kể cả thứ không phải tour")


def test_tx4_7_hai_bang_loai_chuyen_may_chu_va_man_hinh_phai_khop():
    """Màn hình giữ một BẢN CHÉP của bảng loại chuyến. Lệch một khoá thì cột Loại chuyến hiện trống."""
    web = _doc("..", "web", "lib", "meta.ts")
    dong = [d for d in web.splitlines() if d.startswith("export const TOUR_TYPES")]
    assert len(dong) == 1, "không tìm thấy bảng loại chuyến ở màn hình"
    for loai in TOUR_TYPES:
        assert f"{loai}:" in dong[0], f"màn hình chưa biết loại chuyến “{loai}” – cột Loại chuyến sẽ trống"

    # Màn hình tạo chuyến phải đổi LỜI cho hợp đồng thuê xe, và KHÔNG được tự đặt luật.
    mh = _doc("..", "web", "app", "tours", "page.tsx")
    assert "laThueXe" in mh, "màn hình tạo chuyến chưa nhận ra hợp đồng thuê xe"
    assert "Giá thuê trọn hợp đồng" in mh, (
        "ô giá vẫn ghi 'giá bán / khách' cho hợp đồng thuê xe — người nhập sẽ gõ giá một người")
    assert 'd.planned_pax = 1' in mh, "thiếu quy ước một hợp đồng = một khách"
    assert "Điểm dừng nghỉ (bắt buộc)" in mh, (
        "bỏ ô điểm dừng nghỉ cho hợp đồng thuê xe là bỏ nhầm: ĐH Điều 11 là điều về giờ nghỉ của "
        "người lái, và máy chủ vẫn đòi ô ấy ở cổng trình")
