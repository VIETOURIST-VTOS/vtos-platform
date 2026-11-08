# -*- coding: utf-8 -*-
"""P0-05 (Đề xuất hoàn thiện VTD v1.1; Chủ tịch giữ luật cọc 28/10/2026 — lẻ 10%, đoàn 50% — và duyệt 09/11/2026).

Rà 09/11 trên kh.vietourist.vn/restaurant: cách trả, % cọc và luật hủy đã hiện trước nút gửi. Hai chỗ lệch:
  1. Điều kiện riêng của gói (phụ thu, điều kiện hủy) chỉ hiện ở bước chọn gói, không nhắc lại cạnh nút gửi.
  2. Màn sau khi gửi dùng nhãn xanh «✓ Đã gửi đặt bàn» — đọc như đã có bàn trong khi nhà hàng chưa nhận.
Luật cọc / hủy không đổi."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _src():
    return open(os.path.join(GOC, "web", "components", "cong", "NhaHangAgoda.tsx"), encoding="utf-8").read()


def test_p0_05_1_dieu_kien_goi_canh_nut_gui():
    s = _src()
    i, j = s.index('if (buoc === "dat" && nh && td)'), s.index("// ============================== 3–4")
    khoi = s[i:j]
    assert "Điều kiện của gói:" in khoi and "td.dieu_kien_huy" in khoi
    assert khoi.index("Điều kiện của gói:") > khoi.index("Gửi đặt bàn")    # trong khung tóm tắt, cùng bước gửi


def test_p0_05_2_sau_khi_gui_chua_phai_da_co_ban():
    s = _src()
    assert "✓ Đã gửi đặt bàn" not in s
    assert "Đã gửi · chờ nhà hàng nhận bàn" in s


def test_p0_05_3_luat_coc_giu_nguyen():
    from app.services.dat_ban import phai_tra
    ts = {"coc_le": 10, "coc_doan": 50}
    assert phai_tra(ts, 1_000_000, False, "coc") == (10, 100_000)
    assert phai_tra(ts, 1_000_000, True, "coc") == (50, 500_000)
    assert phai_tra(ts, 1_000_000, True, "du") == (100, 1_000_000)
