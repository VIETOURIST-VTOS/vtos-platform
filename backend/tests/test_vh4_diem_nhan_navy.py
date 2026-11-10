# -*- coding: utf-8 -*-
"""VH-4 · /xe giữ giao diện đang có, thêm điểm nhấn navy sáng (Chủ tịch duyệt bản xem trước 10/11/2026).

Giữ bốn lời dặn của Chủ tịch:
  1. Năm nhóm là năm nút navy riêng, chữ không bị cắt (xuống hàng cả nút).
  2. «Việc cần xử lý» lên đầu tổng quan.
  3. Mỗi nút một chỗ: việc hàng đợi đã nói thì bảng sẵn sàng không nói lại; tờ trong «Chờ tôi ký» không
     hiện lại ở danh sách; cửa «Nhập báo cáo từng xe» không có nút thứ hai trong bảng sẵn sàng.
  4. Bớt ghi chú — nhưng chỉ ở /xe; màn Chủ tịch dùng chung khối hiệu quả vẫn giữ chú thích.
"""
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _w(*p):
    return open(os.path.join(GOC, "web", *p), encoding="utf-8").read()


def test_1_nam_nhom_la_nut_navy_khong_cat_chu():
    s = _w("app", "xe", "page.tsx")
    assert 'className="xe-nhom"' in s
    css = s.split("const RONG", 1)[1]
    assert re.search(r"\.xe-nhom\{display:flex;flex-wrap:wrap", css)
    assert "white-space:nowrap" in css and "--xe-nhan:#2c5fa2" in css


def test_2_viec_can_xu_ly_len_dau():
    s = _w("app", "xe", "page.tsx")
    tq = s.split("④ TỔNG QUAN", 1)[1]
    assert tq.index('className="xe-uu"') < tq.index("CUA_NHAP.map") < tq.index("<KhoiHieuQuaXe") < tq.index("<SanSangVanHanh")


def test_3_moi_nut_mot_cho():
    s = _w("app", "xe", "page.tsx")
    assert "TRUNG_SAN_SANG" in s and '"chi_phi_ky_thieu_nhom": ["ky"]'.replace('"chi_phi_ky_thieu_nhom"', "chi_phi_ky_thieu_nhom") in s
    assert 'khongNut={["bao-cao-xe"]}' in s
    assert '!daNoi.includes("ky")' in s                  # dòng «chưa nhập» không lặp việc chi phí kỳ
    ss = _w("components", "doixe", "SanSangVanHanh.tsx")
    assert "coNut" in ss and "!an.includes(x.ma)" in ss
    g = _w("components", "doixe", "TrangGon.tsx")
    bc = g.split("export function BaoCaoXeGon", 1)[1].split("export function", 1)[0]
    assert "!daKy.has(x.id)" in bc and "<ChoToiKy mo={mo} d={ky.d} />" in bc


def test_4_bot_ghi_chu_chi_o_xe():
    s = _w("app", "xe", "page.tsx")
    assert "<KhoiHieuQuaXe gon " in s
    assert "cửa này nặng" not in s and "Đây là số thật, không phải thiếu nguồn" not in s
    k = _w("components", "KhoiV14.tsx")
    assert "{!gon && <p className=\"muted v14-ghi\">" in k
    assert "Cập nhật hằng ngày" in k                     # màn Chủ tịch vẫn có câu này
