"""R5-15 · Chủ tịch 14/11/2026: «hình 1 xoá; hình 2 và 3 kiểm tra lại cách thiết kế cho đẹp, dễ nhìn và chuyên
nghiệp hơn, lấy navy sáng làm điểm nhấn» — duyệt bản xem trước."""
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[2]
P = (GOC / "web/app/ban-tour-le/page.tsx").read_text(encoding="utf-8")
K = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")


def test_xoa_ghi_chu_dau_ban():
    assert "d?.ghi_pham_vi &&" not in K and "Doanh thu phòng = doanh thu chuyến Lẻ" not in K


def test_bang_gon_tam_cot_va_nhom_thang():
    th = P[P.index("<thead>"):P.index("</thead>")]
    import re
    assert len(re.findall(r"<th[ >]", th)) == 8
    assert 'className="thang"' in P and "THÁNG" in P


def test_khong_in_00_khi_chua_du_du_toan():
    # Lỗi cũ: `{r.hoa_von_khach ?? …}{chuaHoaVon && …}` in «0» rồi thêm «0» của biểu thức && → «00».
    assert "hoa_von_khach" not in P.split("export default")[0].split("const du =")[1]
    assert "Chưa có dự toán riêng — Điều hành nhập 3 con số dự toán" in P


def test_diem_nhan_navy_va_hong_logo():
    assert "var(--vtos-logo-hong)" in P and "linear-gradient(120deg,var(--n2),var(--n1))" in P
    assert "font-variant-numeric:tabular-nums" in P
    import re
    assert re.findall(r"^export ", P, re.M) == ["export "], "page.tsx chỉ export default"
