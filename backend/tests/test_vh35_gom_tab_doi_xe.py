"""VH-35 · Gom tab bàn GĐ đội xe (Chủ tịch duyệt 12/11/2026).

Báo cáo & chi phí: bỏ tab «Báo cáo từng xe» và «Đề xuất chi» (hai nút lớn đầu bàn vào thẳng form — không
lặp nút); còn Quyết toán, Công nợ, Lãi lỗ, Xe thuê ngoài (đổi tên từ «Nhìn lại thuê xe ngoài»). «Xếp hạng xe & tài xế» về Xe & tài xế."""
import os
import re

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _xe():
    return open(os.path.join(GOC, "web", "app", "xe", "page.tsx"), encoding="utf-8").read()


def _nhom(s, ma, ke):
    return s[s.index(f'{{ ma: "{ma}",'):s.index(f'{{ ma: "{ke}",')]


def _tab_hien(khoi):
    return [m.group(2) for m in re.finditer(r'\{ ma: "([^"]+)", ten: "([^"]+)"[^\n]*\}', khoi) if "an: true" not in m.group(0)]


def test_1_bao_cao_chi_phi_con_bon_tab():
    s = _xe()
    tc = _nhom(s, "finance", "technical")
    assert _tab_hien(tc) == ["Quyết toán", "Công nợ", "Lãi lỗ đội xe", "Xe thuê ngoài"]
    # Hai trang vẫn còn (nút lớn mở tại chỗ) nhưng giấu khỏi thanh con.
    assert '{ ma: "bao-cao-xe", ten: "Báo cáo từng xe", toi: "/doi-xe?tab=chuyen", ghi: "Nhật trình chuyến", an: true }' in tc
    assert '{ ma: "de-xuat-chi", ten: "Đề xuất chi", toi: "/doi-xe?tab=giaodich", ghi: "Tab Đối soát nguồn ngoài", an: true }' in tc


def test_2_xep_hang_ve_xe_tai_xe():
    s = _xe()
    xe = _nhom(s, "fleet", "finance")
    assert _tab_hien(xe)[-1] == "Xếp hạng xe & tài xế"
    assert "Xếp hạng" not in _nhom(s, "finance", "technical")


def test_3_thanh_con_loc_trang_an_va_mac_dinh_trang_hien():
    s = _xe()
    assert "nhomMo.trang.filter((t) => !t.an).map((t) => (" in s
    assert "nhomMo.trang.find((t) => !t.an)" in s
    # Hai cửa nhập vẫn mở đúng trang ẩn.
    assert 'trang: "de-xuat-chi", mo: "de-xuat-chi"' in s and 'trang: "bao-cao-xe", mo: "phieu-chi-phi"' in s
