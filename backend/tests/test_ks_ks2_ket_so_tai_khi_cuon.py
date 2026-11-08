"""KS-KS2 (08/11/2026) — trang Kết sổ: bốn khung dưới chỉ tải khi cuộn tới.

Chủ tịch chọn «Trang Kết sổ tải gọn» → «Cuộn tới mới tải». Đo crm thật sau #730: gọi riêng thì mỗi
bản xem trước ~2 giây, mở cả trang 5–6 giây — mười yêu cầu của trang đi cùng lúc, ba khung trên cùng
xếp hàng sau bốn khung dưới. Đo trên máy thử sau sửa: lúc mở chỉ còn ba yêu cầu của trang; bảy yêu
cầu của bốn khung dưới đi khi cuộn tới. Giao diện không đổi.
"""
import os
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _doc(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_ks_ks2_1_bon_khung_duoi_boc_trong_tai_khi_thay_va_cho_phan_tren():
    src = _doc("web", "app", "ket-so", "page.tsx")
    for ten in ("MucDoChan", "TachNhiem", "TienCapCha", "DoiChieuLaiLo"):
        assert f"<TaiKhiThay san={{san}} ten=" in src and f"><{ten} /></TaiKhiThay>" in src, ten
        assert f"\n      <{ten} />\n" not in src, ten          # không còn dựng trần ngay khi mở trang
    assert "const san = xongTren.tt && xongTren.tg && xongTren.gt" in src


def test_ks_ks2_2_khung_cho_dung_intersection_observer_va_du_phong():
    src = _doc("web", "components", "TaiKhiThay.tsx")
    assert "new IntersectionObserver" in src and 'rootMargin: "300px"' in src
    assert 'typeof IntersectionObserver === "undefined"' in src   # trình duyệt cũ: dựng ngay như cũ
    assert "if (thay || !san) return;" in src
