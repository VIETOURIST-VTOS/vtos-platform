# -*- coding: utf-8 -*-
"""DK-3 · Màn đăng nhập mới — phép thử ĐỌC THẲNG TỆP GIAO DIỆN.

Cửa hẹp không chạy được trình duyệt, nên những điều dưới đây đo bằng cách soi mã nguồn. Mỗi phép
thử đo HAI CHIỀU: thứ phải có thì phải có, thứ phải mất thì phải mất.

  1. Màn đăng nhập KHÔNG còn chỗ nào gọi `/xac-thuc` — điều 5 Chủ tịch chốt 01/11/2026.
  2. Có gọi `/dang-nhap`, và có ô MẬT KHẨU thật.
  3. Đủ năm cửa `/dang-ky/*` và hai cửa `/quen-mat-khau/*`.
  4. Có dòng chỉ đường cho TÀI KHOẢN CŨ chưa có mật khẩu.
  5. Dấu nhớ máy cất riêng từng cổng, và KHÔNG cất chung khoá với phiên.
  6. Không in mật khẩu mẫu nào ra màn (giữ luật của test_mat_khau_cong_khai).
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
MAN = GOC / "web" / "app" / "login" / "page.tsx"
LIB = GOC / "web" / "lib" / "cong.ts"


def _man() -> str:
    assert MAN.is_file(), f"không có {MAN}"
    return MAN.read_text(encoding="utf-8")


def test_dk3_1_man_dang_nhap_khong_con_cua_vao_bang_ma():
    """ĐIỀU 5: mã một lần không bao giờ thay được mật khẩu.

    Dòng này đỏ nghĩa là có người dán lại cửa đăng nhập bằng mã vào giao diện.
    """
    s = _man()
    assert 'goi("/xac-thuc"' not in s, (
        "màn đăng nhập gọi lại /xac-thuc — đó là cửa vào thẳng bằng mã một lần, Chủ tịch đã bỏ "
        "ngày 01/11/2026. Mã chỉ được dùng làm LỚP THỨ HAI: tạo tài khoản, xác minh máy lạ, "
        "đặt lại mật khẩu.")
    assert "/xac-thuc" not in s


def test_dk3_2_vao_bang_mat_khau():
    s = _man()
    assert 'goi("/dang-nhap"' in s, "không có cửa đăng nhập bằng mật khẩu"
    assert 'goi("/dang-nhap/xac-minh"' in s, "không có bước xác minh máy lạ"
    assert 'autoComplete="current-password"' in s, "không có ô mật khẩu để trình duyệt điền"
    assert "mat_khau:" in s, "không gửi mật khẩu lên máy chủ"


def test_dk3_3_du_bon_buoc_tao_tai_khoan_va_quen_mat_khau():
    s = _man()
    thieu = [c for c in ("/dang-ky/lien-he", "/dang-ky/mat-khau", "/dang-ky/dieu-khoan",
                         "/dang-ky/ma", "/dang-ky/xong",
                         "/quen-mat-khau/ma", "/quen-mat-khau/dat-lai") if c not in s]
    assert not thieu, "màn thiếu cửa: " + ", ".join(thieu)
    # mã nằm ở BƯỚC CUỐI: cửa gửi mã của luồng tạo phải đứng SAU cửa đặt mật khẩu trong mã nguồn
    assert s.index("/dang-ky/mat-khau") < s.index("/dang-ky/xong")


def test_dk3_4_noi_duong_cho_tai_khoan_cu_chua_co_mat_khau():
    """Tài khoản tạo trước DK-1 không có mật khẩu. Câu báo lỗi cố ý không nói vì sao (chống dò),
    nên MÀN phải nói trước — không thì khách cũ gõ mãi không vào và không ai hiểu vì sao."""
    s = _man()
    assert "Quên mật khẩu" in s, "không có đường đặt lại mật khẩu"
    assert re.search(r"[Tt]ài khoản cũ", s), (
        "màn không nói gì cho tài khoản cũ chưa có mật khẩu — họ sẽ gõ mãi không vào")


def test_dk3_5_dau_nho_may_rieng_tung_cong_va_khong_chung_voi_phien():
    assert LIB.is_file()
    s = LIB.read_text(encoding="utf-8")
    for ten in ("dauMay", "luuDauMay", "xoaDauMay", "KHOA_MAY_CONG"):
        assert ten in s, f"thiếu {ten} trong lib/cong.ts"
    assert "vtd_cong_may" in s and "vtd_cong_phien" in s
    assert "vtd_cong_may" != "vtd_cong_phien"
    assert "${KHOA_MAY_CONG}:${loai}" in s, "dấu nhớ phải tách theo từng cổng"
    m = _man()
    assert "luuDauMay(" in m and "xoaDauMay(" in m, "màn phải lưu và xoá được dấu nhớ"


def test_dk3_6_khong_in_mat_khau_mau_ra_man():
    """Cùng luật với tests/test_mat_khau_cong_khai.py — màn công khai không được mang mật khẩu."""
    s = _man().lower()
    for xau in ("mật khẩu mặc định", "mat khau mac dinh", "password123", "123456",
                "mật khẩu demo", "tài khoản thử:"):
        assert xau not in s, f"màn đăng nhập in «{xau}» — không được"
