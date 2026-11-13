"""R5-14 · Chủ tịch duyệt 14/11/2026: «doanh thu và công nợ phải thu đang bị trùng lặp trên bàn GĐ và TP, thanh
công nợ phải thu quá dài, hình 3 làm nổi bật theo kiểu cảnh báo khẩn cấp»; «dùng màu hồng của logo thay cho đỏ»."""
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[2]
W = GOC / "web/components"
K = (W / "BanKdKhung.tsx").read_text(encoding="utf-8")


def test_khong_con_o_trung_tren_dai_viec():
    tp = (W / "BanTpKd.tsx").read_text(encoding="utf-8")
    assert 'nhan="Doanh thu phòng"' not in tp and 'nhan="Phải thu khách"' not in tp
    tn = (W / "BanTnKd.tsx").read_text(encoding="utf-8")
    assert 'nhan="Doanh thu nhóm"' not in tn and 'nhan="Doanh thu của tôi"' not in tn
    nv = (W / "BanNvKd.tsx").read_text(encoding="utf-8")
    assert 'nhan="Doanh thu của tôi"' not in nv and 'nhan="Khách còn nợ"' not in nv
    for t in (tp, tn, nv):
        assert 'className="g5-dai3"' in t


def test_thu_tu_khan_roi_tien_roi_doi_ngu():
    for f in ("BanTpKd", "BanGdKdLe"):
        t = (W / f"{f}.tsx").read_text(encoding="utf-8")
        a, b, c = t.index("<BangThucBan"), t.index("<HangTien"), t.index("<DoiNguVaNhom")
        assert a < b < c, f


def test_khan_mau_hong_logo_va_phai_thu_gon():
    i = K.index("export function BangThucBan"); khan = K[i:K.index("export default function BanKdKhung")]
    assert "var(--vtos-logo-hong)" in khan and "KHẨN · CHUYẾN CẦN THÚC BÁN" in khan and "còn ${n} ngày" in khan
    assert "#c62828" not in khan and "#e53935" not in khan
    j = K.index("export function KhoiPhaiThu"); pt = K[j:K.index("export function HangTien")]
    assert 'className="pt-chong"' in pt and "pt-nocu" in pt and "g5-han" not in pt, "một thanh chồng, không còn 7 thanh dài"
