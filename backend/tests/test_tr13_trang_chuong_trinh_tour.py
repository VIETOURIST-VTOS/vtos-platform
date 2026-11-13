# -*- coding: utf-8 -*-
"""TR-13 · TRANG CHƯƠNG TRÌNH TOUR VIẾT LẠI THEO LỐI CÁC HÃNG TOUR QUỐC TẾ.

Chủ tịch duyệt bản xem thử 14/11/2026. Bản xem thử dựng bằng nội dung thật của tour
«Biển Cà Ná – Hòn Cò Resort – Tanyoli» (HC001) và đối chiếu với cách một hãng bán tour ghép
đoàn nước ngoài trình bày cùng một thứ: lịch trình GẬP mặc định, mỗi ngày ghi rõ ngủ đâu ăn
mấy bữa, điều khoản tách khỏi phần quảng cáo.

Cửa hẹp không chạy được trình duyệt, nên các phép thử dưới đây ĐỌC THẲNG tệp giao diện —
cùng cách `test_dk3_man_dang_nhap.py` canh màn đăng nhập. Chúng không đo cái đẹp (không đo
được), chúng đo bốn điều đã quyết, để ngày nào có người gỡ ra thì dòng ấy đỏ:

  (1) Lịch trình phải GẬP được từng ngày. Trang cũ đổ hết chữ ra một mạch: tour 6 ngày thì
      khách phải cuộn qua toàn bộ ngày 1–5 mới thấy ngày 6, và không ai đọc hết.
  (2) Giữa hai ngày phải có dải «Đêm N · nơi nghỉ». «Ngủ đâu» là câu khách hỏi nhiều nhất;
      nó phải đọc được MÀ KHÔNG cần mở ngày ra.
  (3) Chính sách phải tách thành từng mục gập, và mỗi mục chỉ được dựng từ dữ liệu CÓ THẬT
      (`coc_pt`, `dong_so_truoc`, `quy_dinh`) — không bịa thêm điều khoản nào cho đẹp mục lục.
  (4) Nút «Mở tất cả các ngày» chỉ được có MỘT chỗ trên màn. Quy ước Chủ tịch 10/11/2026:
      các nút chức năng không được lặp lại trên cùng một màn hình.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"


def doc() -> str:
    return TEP.read_text(encoding="utf-8")


# ══ 1 · LỊCH TRÌNH GẬP TỪNG NGÀY ════════════════════════════════════════════════════════════

def test_tr13_1_moi_ngay_la_mot_nut_gap_duoc():
    s = doc()
    assert "setMoNgay" in s, "mất trạng thái gập của từng ngày — lịch trình lại đổ hết chữ ra"
    assert 'className="tra-dhead"' in s
    assert re.search(r'className="tra-dhead"[^>]*aria-expanded=\{mo\}', s), \
        "nút mở ngày phải khai aria-expanded, nếu không người đọc màn hình không biết nó gập được"


def test_tr13_2_ngay_dau_mo_san_nhung_khong_mo_het():
    """Mở sẵn ngày 1 để khách thấy ngay chương trình bắt đầu thế nào; các ngày sau gập."""
    s = doc()
    assert "useState<Record<number, boolean>>({ 1: true })" in s
    assert "setMoNgay({ 1: true })" in s, "mở tour khác mà không đặt lại thì ngày mở của tour cũ dính sang"


def test_tr13_3_chi_mot_nut_mo_tat_ca():
    """Quy ước Chủ tịch 10/11/2026 — mỗi nút một chỗ."""
    s = doc()
    assert s.count('className="tra-mo"') == 1, "nút «Mở tất cả» bị lặp trên cùng một màn"
    assert "Thu gọn tất cả" in s and "Mở tất cả các ngày" in s, "nút phải đổi chữ theo trạng thái"


# ══ 2 · DẢI «ĐÊM N · NƠI NGHỈ» GIỮA HAI NGÀY ════════════════════════════════════════════════

def test_tr13_4_co_dai_noi_giua_hai_ngay():
    s = doc()
    assert "tra-dnoi" in s, "mất dải «Đêm N» — khách phải mở từng ngày mới biết ngủ ở đâu"
    assert re.search(r"i < ngayLt\.length - 1 && n\.khach_san", s), \
        "dải đêm phải đứng GIỮA hai ngày và chỉ hiện khi ngày đó CÓ khách sạn thật"


def test_tr13_5_ngay_cuoi_khong_co_dai_dem():
    """Ngày cuối không có đêm nào theo sau. Vẽ ra là nói sai một điều không có thật."""
    s = doc()
    assert "i < ngayLt.length - 1" in s


# ══ 3 · ĐIỀU KHOẢN TÁCH MỤC, KHÔNG BỊA ══════════════════════════════════════════════════════

def test_tr13_6_chinh_sach_tach_thanh_tung_muc_gap():
    s = doc()
    assert "csMuc" in s and 'className="tra-cshead"' in s
    assert "setMoCs" in s


def test_tr13_7_moi_muc_chinh_sach_deu_dung_tu_du_lieu_that():
    """Bản xem thử của hãng nước ngoài có 5 mục; VTOS chỉ dựng được 2 từ dữ liệu đang có.
    Dựng đủ 5 cho đẹp mục lục nghĩa là bịa điều khoản — thứ ràng buộc hai bên khi có tranh chấp."""
    s = doc()
    i = s.index("const csMuc")
    j = s.index("return <div className=\"ksv tra\">", i)
    khoi = s[i:j]
    assert "sp.coc_pt" in khoi and "sp.dong_so_truoc" in khoi, "mục cọc phải đọc số thật của sản phẩm"
    assert "sp.quy_dinh" in khoi, "mục quy định phải đọc nguyên văn quy định đọc từ trang tour"
    assert "csMuc.push" in khoi
    # không có mục nào được viết sẵn nội dung dài — chỉ câu dự phòng một dòng khi KHÔNG có quy định
    assert khoi.count("csMuc.push") == 2


def test_tr13_8_tour_doan_khong_hien_dieu_khoan_coc():
    """Tour đoàn riêng báo giá theo yêu cầu, chưa có phần trăm cọc nào để nói."""
    s = doc()
    assert "if (!doan) csMuc.push" in s


# ══ 4 · GIỮ NGUYÊN ĐƯỜNG ĐẶT CHỖ ════════════════════════════════════════════════════════════

def test_tr13_9_duong_dat_cho_khong_bi_dong_vao():
    """Vòng này chỉ đổi cách trình bày. Mọi cửa và mọi nút của đường đặt chỗ phải còn nguyên."""
    s = doc()
    for can in ['id="tra-ngay"', "onClick={moDat}", "sp.mo_thanh_toan", 'className="tra-dates"',
                "setChon(c.tour_id)", "sp.bang_gia_web", "sp.bao_gom", "sp.khong_bao_gom",
                "sp.web_cap_nhat", "sp.link_web"]:
        assert can in s, f"vòng giao diện làm mất {can} — đó là đường đặt chỗ, không phải trang trí"


def test_tr13_10_chi_mot_nut_dat_cho_tren_man():
    s = doc()
    assert s.count("onClick={moDat}") == 1


# ══ 5 · MÀU NHẤN KHAI MỘT CHỖ ═══════════════════════════════════════════════════════════════

def test_tr13_11_navy_khai_mot_lan_bang_bien():
    """Chủ tịch chốt 14/11/2026: navy sáng làm điểm nhấn. Rải mã màu khắp nơi thì lần sau đổi
    màu phải đi sửa hàng chục chỗ và chắc chắn sót — khai một biến, dùng lại."""
    s = doc()
    assert "--tra-navy:#1a4fa3" in s
    # mã màu viết thẳng chỉ được nằm trong đúng dòng khai biến và vài chỗ nền chuyển sắc
    assert s.count("#1a4fa3") <= 2, "màu nhấn bị rải thành hằng số khắp bảng kiểu"
