"""R5-4 · Bàn GĐ Kinh doanh lẻ theo mẫu v32, GĐ KD vào /fit là gặp bàn — Chủ tịch 13/11/2026.

Canh: (1) /fit dựng bàn cho gd_kd, không thanh dọc, và trang hai tab cho vai khác;
(2) bàn có đủ sáu tab của v32 với lưới thẻ, bấm thẻ mở NGAY TRONG BÀN; (3) bảng chuyến có thanh
tiến độ, nhãn hòa vốn, nút Chi tiết và chỉ hiện 6 dòng đầu; (4) chip «Kinh doanh lẻ» của GĐ KD trỏ /fit.
"""
import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[2]
FIT = (GOC / "web/app/fit/page.tsx").read_text(encoding="utf-8")
BAN = (GOC / "web/components/BanGdKdLe.tsx").read_text(encoding="utf-8")
SHELL = (GOC / "web/components/Shell.tsx").read_text(encoding="utf-8")


def test_fit_dung_ban_cho_gd_kd():
    assert 'VAI_BAN_KD_LE.includes(vai) && !coXem' in FIT and "<Shell khongThanhBen><BanGdKdLe /></Shell>" in FIT
    assert "<KinhDoanhLe />" in FIT, "TP, trưởng nhóm, NV vẫn gặp trang hai tab"
    assert re.findall(r"^export ", FIT, re.M) == ["export "], "page.tsx chỉ export default"


def test_sau_tab_v32_va_mo_trong_ban():
    for ten in ("Tổng quan", "Bán hàng", "Khách & booking", "Chăm sóc", "Đội ngũ", "Chỉ tiêu & báo cáo"):
        assert f'ten: "{ten}"' in BAN
    assert "g5-luoi" in BAN and "<KhungNhung" in BAN
    assert "window.open(" not in BAN and "location.assign(t" not in BAN, "thẻ không được nhảy màn"


def test_bang_chuyen_du_cot_va_gon():
    # R5-14 (14/11/2026): bảng chuyến và phải thu của bàn GĐ nay là khối CHUNG trong BanKdKhung — kiểm ở đó.
    for chu in ("datViecBan(", "HOẠT ĐỘNG TOUR LẺ", "<BangThucBan", "<HangTien"):
        assert chu in BAN, chu
    KHUNG = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")
    for chu in ("hòa vốn", "bán đủ", "thiếu", "Chi tiết →", 'className="kh-bar"', "slice(0, 6)", "Xem thêm",
                "Phải thu khách"):
        assert chu in KHUNG, chu


def test_chip_gd_kd_tro_fit():
    assert 'VAI_BAN_KD_LE.includes(vai)) return "/fit"' in SHELL and 'return "/ban-kd-le"' not in SHELL
    assert 'path?.startsWith("/fit") ? "/fit"' in SHELL


def test_bo_viec_ket_qua_san_sang_khoi_ban():
    """Chủ tịch 13/11/2026: việc lên nút Công việc; bỏ Kết quả theo kỳ và Sẵn sàng bán."""
    for chu in ('aria-label="Việc cần xử lý"', 'aria-label="Kết quả theo kỳ"', 'aria-label="Sẵn sàng bán"'):
        assert chu not in BAN, chu
