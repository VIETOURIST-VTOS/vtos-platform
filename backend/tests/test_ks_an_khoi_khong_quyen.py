"""KS-AN (08/11/2026) — bàn làm việc không bày khối mà vai trò không được xem.

Chủ tịch cho rà các bàn làm việc ngoài Chủ tịch / TGĐ (08/11): trên bàn PTGĐ, TP Điều hành, GĐ KD,
HCNS, CNTT, nhân viên Điều hành / Kinh doanh, khối «Doanh thu và lợi nhuận» hiện nhãn «Chưa kết
nối» kèm nguyên đường dẫn /api/v1/bao-cao/… (máy chủ trả 403), và khối «Báo cáo ngày» báo «máy
chủ chưa trả tỉ lệ» (máy chủ chỉ gửi cho Chủ tịch, TGĐ, HCNS). Người đọc tưởng hệ thống hỏng.
Chủ tịch duyệt «Ẩn hẳn khối».

Ẩn theo câu trả lời của máy chủ, không viết danh sách vai trò vào giao diện.
"""
import os
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _doc(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_ks_an_1_ket_qua_kinh_doanh_403_thi_khong_bay_khoi():
    src = _doc("web", "components", "KhoiKetQuaKinhDoanh.tsx")
    assert "e?.status === 403" in src
    assert "if (khong_quyen) return null;" in src
    # Lỗi khác 403 vẫn phải báo «Chưa kết nối».
    assert 'className="tag">Chưa kết nối</span> {loi}' in src
    # Ẩn đứng TRƯỚC nhánh «Chưa kết nối».
    assert src.index("if (khong_quyen) return null;") < src.index("if (loi || !d) {")


def test_ks_an_2_bao_cao_ngay_chi_bay_khi_may_chu_gui_truong():
    page = _doc("web", "app", "page.tsx")
    assert '{"bao_cao_ngay" in sec && <KhoiBaoCaoNgay' in page
    # Không viết cứng vai trò ở giao diện.
    i = page.index('"bao_cao_ngay" in sec')
    assert "role" not in page[i - 600:i + 200].split("*/")[-1]


def test_ks_an_3_may_chu_chi_gui_bao_cao_ngay_cho_ba_vai():
    dash = _doc("backend", "app", "services", "dashboard.py")
    assert 'if role in ("hcns", "chutich", "tgd"):' in dash
    i = dash.index('if role in ("hcns", "chutich", "tgd"):')
    assert 'sec["bao_cao_ngay"]' in dash[i:i + 1500]
    # Ngoài nhánh ấy không chỗ nào gán `bao_cao_ngay` (gán None sẽ làm khối hiện lại «Chưa kết nối»).
    assert dash.count('sec["bao_cao_ngay"]') == 1


def test_ks_an_4_luoi_gian_lap_cho_trong():
    css = _doc("web", "app", "globals.css")
    i = css.index(".mh01-hang-3{display:grid")
    assert "repeat(auto-fit" in css[i:i + 200]
