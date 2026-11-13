"""R5-17 · ô nhập «Gửi khách – hưởng hoa hồng» trên màn Dịch vụ lẻ (tiếp R5-16, Chủ tịch 14/11/2026)."""
import pathlib

P = (pathlib.Path(__file__).resolve().parents[2] / "web/app/non-package/page.tsx").read_text(encoding="utf-8")


def test_gui_khach_hien_o_doi_tac_va_so_tra_doi_tac():
    assert 'loaiMoi === "GUI_KHACH"' in P
    assert "Công ty đối tác nhận khách *" in P and 'name="supplier_name" required' in P
    assert "Trả đối tác (đ) *" in P and 'name="cost_amount"' in P
    assert "Giá khách trả (đ) *" in P
