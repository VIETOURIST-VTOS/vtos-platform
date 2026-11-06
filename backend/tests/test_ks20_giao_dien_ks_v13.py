# -*- coding: utf-8 -*-
"""KS-20 · Đợt 1 giao diện khách sạn theo bản xem trước «Đặt phòng VTD v1.3» (Chủ tịch duyệt 05/11/2026; nhắc làm
đúng bản 06/11/2026): trang kết quả + bộ lọc, máy tính và điện thoại."""
from pathlib import Path

TEP = Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "KhachSanVtd.tsx"


def _v():
    return TEP.read_text(encoding="utf-8")


def test_ks20_1_nen_sang_va_chu_be_vietnam_pro():
    v = _v()
    assert 'className="ksv ksv13"' in v and "Be Vietnam Pro" in v and "--ksv-accent:#14538D" in v


def test_ks20_2_thanh_tom_tat_va_sua_tim_kiem():
    v = _v()
    assert "ksv13-tt" in v and "Sửa tìm kiếm" in v and "{suaTim && thanhTim(\"ds\")}" in v


def test_ks20_3_sap_xep_la_thanh_tab_nam_muc():
    v = _v()
    for t in ("Phù hợp nhất", "Giá thấp nhất", "Hạng sao cao", "Đánh giá cao", "Gần trung tâm"):
        assert f'"{t}"' in v, t
    assert 'role="tablist"' in v


def test_ks20_4_ban_do_khu_vuc_va_google_maps():
    v = _v()
    assert "Bản đồ khu vực" in v and "Xem trên Google Maps" in v and "google.com/maps/search/?api=1" in v and "Xem bản đồ" in v


def test_ks20_5_dien_thoai_nhom_loc_gap_va_nut_xem_ket_qua():
    v = _v()
    assert "<details" in v and "đã chọn" in v and "Lọc khách sạn" in v and "Xem {loc2.length} kết quả" in v
    assert "#vtd-access .v3-app .ksv13 details.fsec" in v      # lớp trợ năng kẻ khung mọi <details> — ghi đè


def test_ks20_6_the_khach_san_theo_v13():
    v = _v()
    for chu in ("Xác nhận ngay khi thanh toán", "Mỗi đêm", "Đã gồm 8% VAT", "Chọn phòng", "Gói khớp bộ lọc"):
        assert chu in v, chu
    assert "ksv-banner" not in v.split('return <div className="ksv ksv13">')[1].split("</main>")[0]   # bỏ dải tối kiểu Agoda
