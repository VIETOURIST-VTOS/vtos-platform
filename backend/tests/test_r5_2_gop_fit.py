"""R5-2 · Gộp màn /kinh-doanh-le vào /fit — Chủ tịch chốt 13/11/2026.

Canh bốn điều:
    1. Chỉ phòng Kinh doanh lẻ (GĐ, TP, trưởng nhóm, NV) cùng bốn vai nền mở được /fit.
    2. /fit có hai tab; thân màn doanh thu là MỘT component dùng chung, không chép thành hai bản.
    3. /kinh-doanh-le không gãy: phần Lẻ chuyển sang /fit?xem=doanh-thu, phần Đoàn (?mang=doan) giữ nguyên.
    4. Bàn GĐ Kinh doanh lẻ trỏ /fit, không còn trỏ /kinh-doanh-le.
"""
import pathlib

from app.services import access as AC

GOC = pathlib.Path(__file__).resolve().parents[2]
FIT = (GOC / "web/app/fit/page.tsx").read_text(encoding="utf-8")
KDL = (GOC / "web/app/kinh-doanh-le/page.tsx").read_text(encoding="utf-8")
THAN = (GOC / "web/components/DoanhThuChiTieuKd.tsx").read_text(encoding="utf-8")
BAN = (GOC / "web/components/BanGdKdLe.tsx").read_text(encoding="utf-8")   # R5-4: thân bàn dời vào component


def test_chi_phong_kinh_doanh_le_mo_fit():
    assert set(AC.MENU_ROLES["/fit"]) == set(AC.BASE_VIEW) | {"gd_kd", "tp_kd", "tn_kd", "nv_kd"}
    for vai in ("ptgd_mkt", "hcns", "ketoan", "ptgd_doan", "sales_admin"):
        assert vai not in AC.MENU_ROLES["/fit"], f"{vai} không thuộc phòng Kinh doanh lẻ"
    assert AC.MAN_HINH_API["/fit"] == ("/api/v1/kinh-doanh",), "tab doanh thu gọi /kinh-doanh/*; KHÔNG cấp /bao-cao cho nhân viên"
    # Gõ thẳng đường dẫn cũng phải dừng: vai khác vẫn có /api/v1/bao-cao qua màn /bao-cao.
    assert 'includes("/fit")' in FIT


def test_fit_hai_tab_dung_chung_mot_than():
    assert "<DoanhThuChiTieuKd />" in FIT and '<TrangPhanHe khoa="kdle" khongThanh />' in FIT
    assert '"doanh-thu"' in FIT and "Bảng chỉ tiêu phòng" in FIT
    # Thân doanh thu chỉ ở component; trang không chép lại lời gọi cửa.
    assert 'api(`/kinh-doanh/thang' in THAN or "/kinh-doanh/thang" in THAN
    assert "/kinh-doanh/thang" not in FIT and "/kinh-doanh/thang" not in KDL
    assert "<Suspense" in FIT and "<Suspense" in KDL


def test_duong_cu_khong_gay():
    assert 'router.replace("/fit?xem=doanh-thu")' in KDL
    assert '=== "doan"' in KDL and "<DoanhThuChiTieuKd />" in KDL, "phần Đoàn giữ nguyên"


def test_ban_gd_tro_fit():
    assert '"/kinh-doanh-le"' not in BAN
    # R5-4: chỉ tiêu & doanh thu đặt THẲNG vào bàn (thân /fit), không nhúng /fit trong /fit.
    assert 'noi: "doanh-thu"' in BAN and 'noi: "bang"' in BAN
