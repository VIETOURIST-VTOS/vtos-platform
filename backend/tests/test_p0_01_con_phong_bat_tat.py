# -*- coding: utf-8 -*-
"""P0-01 (Chủ tịch duyệt 09/11/2026 «Cho bật / tắt thật»).

Rà ngày 09/11: trên kh.vietourist.vn/hotel ô «Còn phòng đặt được» luôn được chọn và bấm không ăn — giao diện vẽ
`ck(true, () => {}, …)`. Máy chủ đã lọc sẵn khách sạn đặt được (KS-19), nên ô ấy chỉ là trang trí.

Nay: máy chủ trả thêm `khong_dat` — khách sạn đang hiện nhưng KHÔNG đặt được cho kỳ đã tìm, kèm lý do, bỏ giá và gói.
Bỏ chọn ô trên cổng thì hiện các thẻ ấy (mờ, nút «Xem ngày khác»); vẫn không đặt được từ thẻ ấy.
Kiểm theo từng đêm đã có sẵn (gia_luu: đêm thiếu mùa giá → không bán; con_phong: nhỏ nhất qua các đêm) — giữ nguyên.
"""
import os
from tests.test_at1_am_thuc import db  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _ks, _mo_ban

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p0_01_1_khong_du_phong_vao_khong_dat_khong_gia(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    _mo_ban(db, k)                                               # Deluxe 3 phòng
    r = S.tim(db, "Đà Nẵng", VAO, RA, 2, 0, 1, hom_nay=HN)
    assert [o["id"] for o in r["khach_san"]] == [k.id]
    assert k.id not in [o["id"] for o in r["khong_dat"]]         # đặt được thì không nằm ở danh sách kia
    r = S.tim(db, "Đà Nẵng", VAO, RA, 8, 0, 4, hom_nay=HN)       # 4 phòng > 3 phòng còn
    assert r["khach_san"] == []
    o = next(o for o in r["khong_dat"] if o["id"] == k.id)
    assert o["ly_do"] == "khong_du"
    assert o["gia_tu"] is None and o["goi_ban"] == [] and o["dat_ngay"] is False and o["het_phong"] is True
    assert r["tong"] == 0                                         # số đếm cũ chỉ tính khách sạn đặt được


def test_p0_01_2_chua_co_gia_ky_nay_la_chua_ban(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    _mo_ban(db, k)                                               # mùa giá chỉ phủ tháng 12
    import datetime as dt
    vao, ra = dt.date(2026, 12, 30), dt.date(2027, 1, 2)         # đêm 01/01 không có mùa giá
    r = S.tim(db, "Đà Nẵng", vao, ra, 2, 0, 1, hom_nay=HN)
    assert k.id not in [o["id"] for o in r["khach_san"]]
    assert next(o for o in r["khong_dat"] if o["id"] == k.id)["ly_do"] == "chua_ban"


def test_p0_01_3_ly_do_het_phong():
    from app.services import khach_san_vtd as S
    o = S._the_khong_dat({"id": 1, "ten": "A", "het_phong": True, "dat_ngay": True, "anh": [{"nho": "x"}, {"nho": "y"}],
                          "gia_tu": {"gia_dem": 1}, "goi_ban": [{"lp": 1}]})
    assert o["ly_do"] == "het" and o["gia_tu"] is None and o["goi_ban"] == [] and len(o["anh"]) == 1


def test_p0_01_4_giao_dien_o_loc_bat_tat_that():
    src = open(os.path.join(GOC, "web", "components", "cong", "KhachSanVtd.tsx"), encoding="utf-8").read()
    assert 'ck(true, () => {}, "Còn phòng đặt được"' not in src
    assert 'ck(conPhong, setConPhong, "Còn phòng đặt được"' in src
    i = src.index("{!conPhong && !banDo && khongDat.length > 0")
    khoi = src[i:src.index("</section>}", i)]
    assert "Xem ngày khác" in khoi and "Chọn phòng" not in khoi    # thẻ không đặt được không có nút đặt
