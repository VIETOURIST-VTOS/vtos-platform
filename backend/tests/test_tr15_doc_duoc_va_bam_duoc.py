# -*- coding: utf-8 -*-
"""TR-15 · BA CHỖ ĐO ĐƯỢC TRÊN BẢN CHẠY THẬT, KHÔNG PHẢI NHÌN BẰNG MẮT.

Soát kh.vietourist.vn ngày 14-11-2026 ở hai cỡ màn (máy tính và điện thoại 375px), bằng cách
đọc thẳng cây giao diện và tính lại từng con số. Ba chỗ dưới đây là ba chỗ chặn khách nhiều
nhất, và cả ba đều đo được chứ không phải chuyện thẩm mỹ.

  (1) NÚT VÀO ĐƯỜNG ĐẶT TOUR GẦN NHƯ VÔ HÌNH — 95/95 THẺ TOUR.
      «Xem ngày đi» (22 thẻ) và «Xem & gửi yêu cầu» (73 thẻ): chữ #23252C trên nền #14538D,
      tương phản 1,93:1. WCAG 2.1 (1.4.3) đòi 4,5:1. Đo cả trang: ĐÚNG 95 chỗ không đạt, và
      CẢ 95 đều là chính cái nút này — mọi chữ khác trên trang đều đạt.

      VÌ SAO, hỏi trình duyệt chứ không đoán: liệt kê mọi luật CSS trúng nút ấy thì ra ba cái —
          a {color: var(--navy)}              (0,0,1)
          #vtd-access a {color: inherit}      (1,0,1)  ← thắng, vì có ID
          .ksv-btn {color: #fff}              (0,1,0)
      TR-7 đổi nút thẻ tour từ <button> sang <a> để có link thật cho máy tìm kiếm; luật ép chữ
      trắng lại chỉ viết cho «button.ksv-btn», nên từ lúc ấy nút thừa hưởng màu chữ của trang.
      Đã soát trang khách sạn: KHÔNG dính, vì nó vẫn dùng <button> (0 thẻ a.ksv-btn).

  (2) iPHONE TỰ PHÓNG TO KHI KHÁCH BẤM VÀO Ô NHẬP. Safari phóng trang khi ô nhập có cỡ chữ
      dưới 16px — khách đang chọn ngày thì màn nhảy. Đo ở 375px: 5/5 ô nhập đều dưới 16px.

  (3) KHÔNG CÓ <h1>, KHÔNG CÓ <main>. Cả trang danh sách lẫn trang tour đều 0 thẻ h1 và 0 thẻ
      main. Người đọc màn hình mất lối nhảy thẳng vào nội dung; máy tìm kiếm mất tiêu đề chính.
      Trang tour có 6 thẻ h2 mà không có h1 nào đứng trên.

  (4) Ô TÍCH 18x18px trong bộ lọc. WCAG 2.2 (2.5.8) đòi vùng bấm tối thiểu 24x24px.

KHÔNG làm trong vòng này, nói rõ để không ai tưởng đã xong: 92/93 ảnh chưa khai kích thước.
Em đếm được con số ấy nhưng CHƯA đo được nó có thật sự làm trang giật khi tải hay không — các
khung ảnh có thể đã cố định sẵn chiều cao. Đo xong mới sửa, không sửa theo cảm giác.
"""
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"


def doc() -> str:
    return TEP.read_text(encoding="utf-8")


# ══ 1 · NÚT ĐẶT TOUR PHẢI ĐỌC ĐƯỢC ══════════════════════════════════════════════════════════

def test_tr15_1_ep_chu_trang_cho_nut_dang_the_a():
    """Phải thắng được «#vtd-access a {color:inherit}», tức phải có ID trong phép chọn."""
    s = doc()
    assert "#vtd-access .tra a.ksv-btn" in s, "thiếu phép chọn có ID thì luật cũ vẫn thắng"
    i = s.index("#vtd-access .tra a.ksv-btn")
    luat = s[i:s.index("}", i)]
    assert "color:#fff" in luat
    assert "-webkit-text-fill-color:#fff" in luat, \
        "chỉ đặt color là chưa đủ: -webkit-text-fill-color đè color bất kể thứ tự"


def test_tr15_2_nut_vien_khong_bi_ep_trang_theo():
    """Nút viền (.line) nền trong suốt — ép trắng là chữ trắng trên nền trắng, hỏng chiều kia."""
    s = doc()
    assert "a.ksv-btn.line" in s
    i = s.index("#vtd-access .tra a.ksv-btn.line")
    assert "var(--ksv-ink)" in s[i:s.index("}", i)]


def test_tr15_3_nut_du_cao_de_bam():
    s = doc()
    i = s.index("#vtd-access .tra a.ksv-btn")
    assert "min-height:44px" in s[i:s.index("}", i)]


# ══ 2 · Ô NHẬP TRÊN ĐIỆN THOẠI ══════════════════════════════════════════════════════════════

def test_tr15_4_o_nhap_16px_tren_dien_thoai():
    s = doc()
    assert "@media (max-width:640px){.tra input,.tra select,.tra textarea{font-size:16px}}" in s, \
        "dưới 16px là Safari phóng to trang ngay khi khách bấm vào ô"


# ══ 3 · KHUNG TRANG ═════════════════════════════════════════════════════════════════════════

def test_tr15_5_moi_man_khach_doc_deu_co_mot_h1():
    s = doc()
    assert s.count("<h1") == 2, "đúng hai màn khách đọc: trang danh sách và trang tour"
    assert '<h1 className="tra-ht">' in s, "trang danh sách lấy dòng tiêu đề của dải tìm làm h1"
    assert "<h1 style={{ margin: 0, fontSize: 26 }}>{sp.ten}</h1>" in s, "trang tour lấy tên tour"


def test_tr15_6_ten_tour_khong_con_la_h2():
    s = doc()
    assert "<h2 style={{ margin: 0, fontSize: 26 }}>{sp.ten}</h2>" not in s


def test_tr15_7_hai_man_ay_nam_trong_main():
    s = doc()
    assert s.count('<main className="ksv tra">') == 2
    assert s.count("</main>;") == 2, "mở bằng main thì phải đóng bằng main, không đóng bằng div"


def test_tr15_8_cac_man_phu_khong_tu_tien_them_main():
    """Một trang chỉ nên có MỘT vùng main. Các nhánh phụ (đơn, đã gửi, đặt chỗ, tour đoàn) giữ
    nguyên thẻ div — chúng là bước giữa chừng, không phải màn nội dung chính."""
    s = doc()
    assert s.count('<div className="ksv tra">') == 4


# ══ 4 · Ô TÍCH ══════════════════════════════════════════════════════════════════════════════

def test_tr15_9_o_tich_du_24px():
    s = doc()
    assert ".tra input[type=checkbox],.tra input[type=radio]{width:24px;height:24px" in s


# ══ 5 · KHÔNG LÀM HỎNG THỨ ĐANG CHẠY ════════════════════════════════════════════════════════

def test_tr15_10_duong_dat_cho_con_nguyen():
    s = doc()
    for can in ['id="tra-ngay"', "onClick={moDat}", "sp.mo_thanh_toan", 'className="tra-dates"',
                "setChon(c.tour_id)", 'className="tra-days"', "tra-dnoi", "csMuc"]:
        assert can in s, f"vòng giao diện làm mất {can}"


def test_tr15_11_chi_mot_nut_dat_cho():
    assert doc().count("onClick={moDat}") == 1
