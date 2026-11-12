"""VH-42 · Xử lý tại bàn (Chủ tịch chốt 13/11/2026: mọi vai chỉ làm việc trên bàn của mình).

Ô Công việc / Chờ duyệt: rê chuột là xổ, bấm một dòng mở «Xử lý tại bàn» nhúng màn gốc (không rời bàn);
thanh đầu nằm trên hàng nút ngang; việc của bàn /xe lên nút Công việc («chờ người khác» ẩn); ngăn kéo /xe
mở đúng trang con (Quyết toán không nhảy sang Hồ sơ xe); dòng quyết toán chuyến của Chủ tịch trỏ danh sách
tờ chờ Chủ tịch, không trỏ bàn GĐ đội xe."""
import os
import re

GOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _r(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_1_thanh_dau_nam_tren_hang_nut_dinh():
    css = _r("web", "app", "globals.css")
    top = re.search(r"\n\.top\{[^}]*\}", css).group(0)
    assert "z-index:15" in top
    assert "z-index:5;" in _r("web", "app", "xe", "page.tsx").split(".xe-nhom-dinh{", 1)[1].split("}", 1)[0] + ";"


def test_2_bam_dong_mo_tai_ban_khong_roi_ban():
    sh = _r("web", "components", "Shell.tsx")
    assert "e.preventDefault(); moTaiBan(href, label);" in sh
    assert 'aria-label="Xử lý tại bàn"' in sh and "<KhungNhung key={xuLy.href} toi={xuLy.href}" in sh
    assert 'if (e.pointerType === "mouse") datMo(true);' in sh            # rê chuột là xổ, chạm không bị đóng lại


def test_3_viec_cua_ban_len_nut_cong_viec_an_cho_nguoi_khac():
    sh = _r("web", "components", "Shell.tsx")
    assert '(viecBan || []).filter((v) => v.muc !== "trang")' in sh
    assert "+ ban.length;" in sh


def test_4_ngan_keo_quyet_toan_mo_dung_trang_con():
    s = _r("web", "app", "xe", "page.tsx")
    assert '"quyet-toan": { ten: "Quyết toán chuyến", toi: "/doi-xe?tab=quyettoan", nhan: "Mở màn Quyết toán xe", nhom: "finance", trang: "quyet-toan"' in s
    assert "setKeo(null); setNhom(k.nhom!); setTrang(k.trang!);" in s


def test_5_quyet_toan_chuyen_cua_chu_tich_khong_tro_ban_gd_doi_xe():
    d = _r("backend", "app", "services", "dashboard.py")
    assert '"href": "/doi-xe?tab=chuyen&cho=tgd"' in d and 'CHỦ TỊCH duyệt", "href": "/xe"' not in d
    w = _r("web", "app", "doi-xe", "page.tsx")
    assert 'get("cho") === "tgd") setChoTgd(true);' in w and '<QuyetToanChuyen tripId={t.id} toast={toast} />' in w
