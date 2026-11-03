# -*- coding: utf-8 -*-
"""TR-4 · Bộ lọc tìm tour: «Giá mỗi khách» đủ 3 mức (thêm «Trên 5 triệu»), «Phương tiện» đủ 4 loại — Xe du lịch, Máy bay,
Tàu hỏa, Du thuyền (Chủ tịch 03/11/2026). Hai nhóm này luôn hiện đủ mức, mức chưa có tour thì mờ (số 0) thay vì biến mất.
Lọc giá dùng giá chuyến, tour chưa có lịch (TR-3) dùng giá tham khảo trên web."""
from pathlib import Path

TEP = Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "ToursAgoda.tsx"


def test_tr4_1_ten_phuong_tien_du_bon_loai():
    from app.models.tour_online import PHUONG_TIEN_TOUR
    assert PHUONG_TIEN_TOUR == {"xe": "Xe du lịch", "may_bay": "Máy bay", "tau_hoa": "Tàu hỏa", "du_thuyen": "Du thuyền"}
    s = TEP.read_text(encoding="utf-8")
    assert 'const PT: Record<string, string> = { xe: "Xe du lịch", may_bay: "Máy bay", tau_hoa: "Tàu hỏa", du_thuyen: "Du thuyền" };' in s


def test_tr4_2_hai_nhom_luon_hien_du_muc():
    s = TEP.read_text(encoding="utf-8")
    assert '["t5", "Trên 5 triệu", (g) => g > 5e6]' in s
    assert '"gia", true)}' in s and '"pt", true)}' in s, "giá và phương tiện phải hiện đủ mức"
    assert "const co = du ? muc : muc.filter(([, , f]) => dem(f, khoa) > 0);" in s, "các nhóm khác vẫn ẩn mức trống"


def test_tr4_3_loc_gia_dung_gia_tham_khao_khi_chua_co_lich():
    s = TEP.read_text(encoding="utf-8")
    assert "const giaLoc = (s: any): number | null => s.gia_tu ?? s.gia_tham_khao ?? null;" in s
    assert "s.gia_tu != null && f(s.gia_tu)" not in s
