# -*- coding: utf-8 -*-
"""QT-3 · Màn Chủ tịch chỉ dùng MỘT cách viết số (Chủ tịch chốt 24/10/2026).

VÌ SAO CÓ VÒNG NÀY. Quét màn thật ngày 24/10 thấy hai cách viết số đứng cạnh nhau:

  · «Hiệu quả đội xe»  : 37.3%  ·  43.6%  ·  27.1 L/100km  ·  10799 đ
  · «Kinh doanh Lẻ»    : 1250 chuyến          (ngay cạnh ô tiền 135,8 tỷ của chính nó)
  · 19 chỗ còn lại     : 176,3 tỷ  ·  26,7 tỷ  ·  8.030.563.416

Dấu chấm với dấu phẩy đảo vai giữa hai chuẩn, nên trên một màn hình tiền bạc người đọc phải tự
đoán dấu nào là gì. `10799 đ` nặng nhất: thiếu dấu phân nhóm thì đọc lướt dễ thành 107,99.

GỐC KHÔNG PHẢI THIẾU HÀM, MÀ LÀ QUÊN GỌI. Kho đã có `vnd()` ở `lib/api.ts` và `toLocaleString`
dùng ở mười chỗ. Ba chỗ trên nối thẳng số vào chuỗi mẫu (`${x}${duoi}`), và JS nối chuỗi thì in
theo chuẩn Mỹ. Một lỗi im lặng: không ai thấy nó cho tới khi đọc kỹ hai con số cạnh nhau.

  qt3_1  không khối nào của màn Chủ tịch nối thẳng số vào chuỗi nữa
  qt3_2  hàm `so()` của khối đội xe đi qua chuẩn Việt
  qt3_3  số chuyến của khối Kinh doanh đi qua chuẩn Việt
  qt3_4  bốn ô hàng «Hoạt động tour» xếp một hàng ngang, không rớt 3 + 1
  qt3_5  góc phải chỉ hiện khi số KHÔNG đáng tin, lúc bình thường trống hẳn
  qt3_6  dòng ghi chú dưới tiêu đề đã bỏ
  qt3_7  luật `.vh-hang.X` chết không được nằm lại — chỗ `qt2_6` cố ý không với tới

VỀ qt3_5 — VÌ SAO KHÔNG BỎ SẠCH GÓC PHẢI. Chủ tịch bảo bỏ dòng «Cập nhật … · Toàn bộ». Dòng ấy
làm HAI việc trong một chỗ: nói giờ cập nhật (bỏ), và báo khi số không đáng tin — «Số lưu đệm»
(cũ tới 5 phút), «Lỗi tải», «Chưa kết nối». Bỏ cả hai thì màn hình im lặng bày số cũ hoặc số
hỏng, trông y hệt số đúng. Nay lúc bình thường góc phải trống hẳn; chỉ có chuyện nó mới hiện.
Chủ tịch đã duyệt cách này 24/10.
"""
import io
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(GOC, "web", "components")
V14 = os.path.join(WEB, "KhoiV14.tsx")
KD = os.path.join(WEB, "KhoiKinhDoanh.tsx")
VH = os.path.join(WEB, "KhoiVanHanh.tsx")
CSS = os.path.join(WEB, "KhoiVanHanh.css")


def _doc(p: str) -> str:
    assert os.path.exists(p), f"Thiếu tệp {os.path.relpath(p, GOC)}"
    return io.open(p, encoding="utf-8").read()


def _bo_chu_thich(s: str) -> str:
    """Bỏ `/* … */` và `// …`. Soi CHỮ HIỆN LÊN MÀN thì phải bỏ chú thích, không thì mỗi lần ai đó
    viết một câu giải thích có ví dụ `37.3%` là hàng rào đỏ oan — và hàng rào đỏ oan sớm muộn bị
    tắt. Bài học đã ghi ở `test_le2b` và lặp lại ở `qt2_4`."""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return "\n".join(d for d in s.split("\n") if not d.lstrip().startswith("//"))


def test_qt3_1_khong_noi_thang_so_vao_chuoi_mau():
    """`${x}${duoi}` với x là số thì JS in chuẩn Mỹ. Đây là hình dạng đã gây ra cả bốn chỗ sai."""
    for p in (V14, KD):
        s = _bo_chu_thich(_doc(p))
        xau = re.findall(r"\$\{\s*x\s*\}\$\{\s*duoi\s*\}", s)
        assert not xau, (
            f"{os.path.basename(p)} còn nối thẳng số vào chuỗi mẫu. Đi qua "
            f'`toLocaleString("vi-VN")` thì màn hình mới có một cách viết số.')


def test_qt3_2_khoi_doi_xe_di_qua_chuan_viet():
    s = _bo_chu_thich(_doc(V14))
    i = s.find("const so = ")
    assert i >= 0, "không còn hàm `so()` của khối đội xe — xem lại, phép thử này mất việc"
    than = s[i:i + 420]
    assert 'toLocaleString("vi-VN"' in than, (
        "hàm `so()` không đi qua chuẩn Việt: Biên lợi nhuận, Công suất, Tiêu hao, Chi phí/km "
        "sẽ lại in `37.3%` và `10799 đ`")
    assert "maximumFractionDigits: 1" in than, (
        "thiếu `maximumFractionDigits: 1` — phần trăm và tiêu hao mất chữ số lẻ hoặc thừa ra")


def test_qt3_3_so_chuyen_di_qua_chuan_viet():
    s = _bo_chu_thich(_doc(KD))
    assert 'toLocaleString("vi-VN")' in s, "số chuyến không đi qua chuẩn Việt — `1250` thay vì `1.250`"
    for truong in ("chuyen_thang", "chuyen_nam"):
        assert re.search(r"\{\s*dem\(p\." + truong + r"\)\s*\}", s), (
            f"`p.{truong}` còn in thẳng, không qua hàm đếm")


def test_qt3_4_bon_o_mot_hang_ngang():
    """Chủ tịch 24/10: «xếp thành 1 hàng ngang cho 4 khung luôn». Bản cũ dùng `auto-fit` tối thiểu
    200px và chỉ ép bốn cột từ 1100px, nên ở bề ngang quanh 900–1100px nó rớt thành 3 + 1."""
    s = _doc(CSS)
    # Chỉ soái LUẬT `.h4`, không cấm chuỗi trên cả tệp: bản đầu cấm cả tệp nên đỏ vì một luật
    # KHÁC (`.h3`) — đỏ đúng một vấn đề thật nhưng không phải vấn đề nó định canh.
    for d in s.split("\n"):
        if ".vh-hang.h4" in d:
            assert "auto-fit" not in d, (
                "hàng bốn ô còn dùng `auto-fit` — sẽ lại rớt thành 3 + 1 ở bề ngang giữa: " + d.strip())
    assert re.search(r"min-width:\s*8[0-9]{2}px\)\s*\{\s*\.vh-hang\.h4\s*\{[^}]*repeat\(4,\s*1fr\)", s), (
        "không thấy nấc ép bốn cột quanh 860px")


def test_qt3_5_goc_phai_chi_hien_khi_so_khong_dang_tin():
    s = _bo_chu_thich(_doc(VH))
    assert "Cập nhật " not in s, "dòng «Cập nhật …» ở góc phải chưa bỏ"
    # `pham_vi` VẪN ĐƯỢC DÙNG ở chỗ khác (dòng «Đã gộp theo hồ sơ · toàn bộ» của danh sách
    # việc) và đó là chỗ đúng của nó. Bản đầu cấm cả tệp nên đỏ oan. Chỉ cấm đúng câu của dòng cũ.
    assert "Theo quyền của anh/chị" not in s, "còn câu «Theo quyền của anh/chị» của dòng mốc cũ"
    for canh in ("Chưa kết nối", "Lỗi tải", "Số lưu đệm"):
        assert canh in s, (
            f"mất cảnh báo «{canh}». Bỏ nó là màn hình im lặng bày số cũ hoặc số hỏng, "
            f"trông y hệt số đúng.")
    assert re.search(r"\{canhBao\s*&&", s), (
        "góc phải phải hiện CÓ ĐIỀU KIỆN — lúc bình thường trống hẳn")


def test_qt3_6_bo_dong_ghi_chu_duoi_tieu_de():
    s = _bo_chu_thich(_doc(VH))
    assert "tình trạng tour và nguồn khách" not in s, "dòng ghi chú dưới tiêu đề chưa bỏ"


def test_qt3_7_khong_luat_vh_hang_nao_chet():
    """Phần bù cho `qt2_6`, đặt ở tệp NÀY chứ không sửa tệp ấy — nói rõ vì sao.

    `qt2_6` rút tên lớp bằng tiền tố `vh-` / `c-`, nên hậu tố trong `.vh-hang.h3` không được rút
    ra và luật chết ấy nằm lại suốt từ QT-1 tới QT-3. Làn R1 khi soát chéo ĐÃ THẤY chỗ hở này và
    **cố ý không nới**: nới biểu thức của `qt2_6` ra sẽ kéo theo mọi lớp một chữ (`.v`, `.t`, `.qh`)
    mà nhiều cái dùng ở tệp khác — hàng rào đỏ oan là hàng rào sớm muộn bị tắt. Lý lẽ đó đúng.

    Nên phép thử này không nới `qt2_6`, mà canh riêng MỘT tiền tố duy nhất: `.vh-hang.X`. Hẹp
    như thế thì không chạm lớp một chữ nào, nên mối lo của R1 không xảy ra.

    ĐẶT Ở TỆP NÀY để không đụng `test_qt2_...py`: tệp ấy đang nằm trên nhánh QT-2 còn mở và làn R1
    vừa sửa. Hai nhánh cùng ghi một tệp là đụng nhau lúc gộp — đúng kiểu rối em vẫn cảnh báo.
    """
    tsx, css = _doc(VH), _doc(CSS)
    chet = [m.group(1) for m in re.finditer(r"\.vh-hang\.([a-z0-9-]+)", css)
            if f"vh-hang {m.group(1)}" not in tsx]
    assert not chet, (
        f"luật `.vh-hang` không còn ai dùng: {sorted(set(chet))}. Để lại thì lần sau có người "
        f"dựng lại hàng từ chính luật ấy.")
