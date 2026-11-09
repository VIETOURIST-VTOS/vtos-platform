# -*- coding: utf-8 -*-
"""XE-V33B · màn gọn từng trang con của /xe (Chủ tịch duyệt bản xem trước 10/11/2026).

  1. Trang con có màn gọn thì hiện màn gọn; «Mở…» mới mở màn chi tiết đang chạy (khung nhúng) tại chỗ.
  2. Màn gọn chỉ đọc cửa máy chủ đang có — không có phép tính tiền thứ hai trên màn hình.
  3. Danh sách chuyến trả trạng thái tờ báo cáo xe để màn gọn chia nhóm (đang nhập / chờ duyệt / trả lại / đã chốt).
  4. /doi-xe nhận `?xe=` để mở thẳng hồ sơ một xe.
"""
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _web(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_man_gon_noi_vao_trang_con():
    s = _web("app", "xe", "page.tsx")
    for ma in ("lich", "ho-so-xe", "bao-cao-xe", "quyet-toan", "cong-no", "bao-duong", "bao-hong", "dau"):
        assert f'"{ma}": (p) => <G.' in s, ma
    assert "setChiTiet(toi)" in s and "← Về màn gọn" in s
    assert "<KhungNhung key=" in s                     # chi tiết vẫn là màn đang chạy


def test_man_gon_chi_doc_cua_co_san():
    s = _web("components", "doixe", "TrangGon.tsx")
    cua = set(re.findall(r'useDoc<[^>]*>\(\s*[`"](/[a-z\-/]+)', s))
    assert cua == {"/fleet/lenh-dieu-xe", "/fleet/xe", "/fleet/chuyen", "/fleet/lai-lo", "/fleet/cong-no",
                   "/fleet/bao-duong/theo-xe", "/fleet/bao-hong", "/fleet/gia-dau", "/fleet/dinh-muc-dau"}, cua
    assert "method:" not in s                          # màn gọn không ghi gì
    assert "Chưa có số" in s and "Thiếu dữ liệu" in s and "Đang bị chặn" in s


def test_chuyen_tra_trang_thai_to():
    from app.api.v1 import fleet as F
    import inspect
    src = inspect.getsource(F._chuyen_out)
    for k in ('"qt_trang_thai"', '"qt_ten_trang_thai"', '"qt_tra_lai_ly_do"'):
        assert k in src, k
    from app.models.fleet import QT_TRANG_THAI
    assert QT_TRANG_THAI["cho_tgd"] == "Chờ Chủ tịch duyệt"


def test_doi_xe_nhan_xe():
    s = _web("app", "doi-xe", "page.tsx")
    assert 'get("xe")' in s and "api(`/fleet/xe/${xeId}`).then(setChon)" in s
