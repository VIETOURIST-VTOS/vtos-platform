# -*- coding: utf-8 -*-
"""P0-06 (Đề xuất hoàn thiện VTD v1.1; Chủ tịch duyệt bản xem trước 09/11/2026).

Rà 09/11 trên kh.vietourist.vn:
  1. Hộp «Đăng nhập để tiếp tục» ghi «mã gửi qua Zalo hoặc email, không cần mật khẩu» — sai: cửa đăng nhập là liên hệ
     + MẬT KHẨU; máy lạ mới gửi thêm mã (app/login: «Không có nút nào gửi mã để vào thẳng»).
  2. Đăng nhập xong chỉ về đúng trang, mất ngày / số khách / phòng, bàn, tour đang chọn và cả bản tự thiết kế tour.
Nay: lời hộp đúng cách đăng nhập; bốn màn ghi lựa chọn vào sessionStorage, trang đăng nhập đánh dấu «vừa đăng nhập»,
màn đích đọc lại đúng một lần trong 30 phút. Không gửi máy chủ, không lưu mật khẩu."""
import os

GOC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web")


def _doc(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_p0_06_1_loi_hop_dang_nhap_dung_cach_vao_that():
    s = _doc("components", "cong", "KhungRieng.tsx")
    assert "không cần mật khẩu" not in s
    assert "số điện thoại hoặc email và mật khẩu" in s and "lần đầu trên máy mới" in s
    assert "Không có nút nào gửi mã để vào thẳng" in _doc("app", "login", "page.tsx")   # cửa thật vẫn là mật khẩu


def test_p0_06_2_dang_nhap_xong_danh_dau_de_khoi_phuc():
    s = _doc("app", "login", "page.tsx")
    assert "luuPhienCong(r.phien); danhDauVuaDangNhap(); location.replace(veSauDangNhap())" in s
    lib = _doc("lib", "cong.ts")
    for t in ("export function nhoLuaChon", "export function layLuaChon", "export function danhDauVuaDangNhap", "NHO_PHUT = 30",
              "sessionStorage.removeItem(NHO_DN + trang); sessionStorage.removeItem(VUA_DN)"):
        assert t in lib, t
    assert "mat_khau" not in lib[lib.index("const NHO_DN"):lib.index("export function duongDangNhap")]


def test_p0_06_3_bon_man_ghi_va_doc_lai_lua_chon():
    for tep, khoa in (("KhachSanVtd.tsx", "hotel"), ("NhaHangAgoda.tsx", "restaurant"), ("ToursAgoda.tsx", "tours"),
                      ("TuThietKeTour.tsx", "tour-tk")):
        s = _doc("components", "cong", tep)
        assert f'nhoLuaChon("{khoa}"' in s and f'("{khoa}")' in s, tep
    # Ô đồng ý không được tự tick lại sau khi khôi phục.
    assert "dongy: false, dongy_khach: false" in _doc("components", "cong", "NhaHangAgoda.tsx")
    assert "dong_y: false" in _doc("components", "cong", "TuThietKeTour.tsx")
