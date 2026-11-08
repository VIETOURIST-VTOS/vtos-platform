# -*- coding: utf-8 -*-
"""P0-02 (Chủ tịch duyệt bản xem trước 09/11/2026).

Rà ngày 09/11: crm ghi 44 khách sạn «Đang hiện», cổng khách hiện 36 cho 16–18/11. Đối chiếu sau P0-01: 36 đặt được
+ 8 «chưa mở bán» = 44 — tám khách sạn chưa có mùa giá phủ các đêm ấy, không phải lỗi đếm. Bảng khách sạn trên crm
thêm cột «Bán được trên cổng» để Điều hành thấy từng hồ sơ bán liền được đến ngày nào, và vì sao chưa bán được.
Chỉ xét GIÁ (gói đã duyệt, đang bán, của loại phòng đang bán); mỗi gói tự phủ đêm như gia_luu."""
import datetime as dt
import os
from types import SimpleNamespace as NS
from tests.test_at1_am_thuc import db  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, _ks, _mo_ban, _u

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = dt.date


def _m(tu, den):
    return NS(tu_ngay=tu, den_ngay=den)


def _g(id_, tt="da_duyet", ban=True):
    return NS(id=id_, trang_thai=tt, dang_ban=ban)


def _k(hien=True, ngung=False):
    return NS(hien_cong=hien, ngung=ngung)


LP = [NS(id=1, dang_ban=True)]


def test_p0_02_1_den_ngay_lien_va_canh_bao_30_ngay():
    from app.services.khach_san_vtd import ban_cong
    hn = D(2026, 11, 9)
    # hai mùa nối liền → gộp; khoảng hở sau 31/12 → dừng ở 31/12
    b = ban_cong(_k(), LP, {1: [_g(10)]}, {10: [_m(D(2026, 11, 1), D(2026, 11, 30)), _m(D(2026, 12, 1), D(2026, 12, 31)),
                                               _m(D(2027, 2, 1), D(2027, 3, 1))]}, hn)
    assert b == {"ma": "den", "den": "2026-12-31", "tu": None, "dem": 53, "thieu_30": False}
    b = ban_cong(_k(), LP, {1: [_g(10)]}, {10: [_m(D(2026, 11, 1), D(2026, 11, 15))]}, hn)
    assert b["ma"] == "den" and b["dem"] == 7 and b["thieu_30"] is True


def test_p0_02_2_moi_goi_tu_phu_dem_khong_ghep():
    from app.services.khach_san_vtd import ban_cong
    hn = D(2026, 11, 9)
    # gói A đến 20/11, gói B từ 21/11: không ghép — bán liền chỉ đến 20/11 (giống gia_luu)
    b = ban_cong(_k(), LP, {1: [_g(10), _g(11)]}, {10: [_m(D(2026, 11, 1), D(2026, 11, 20))],
                                                    11: [_m(D(2026, 11, 21), D(2027, 1, 31))]}, hn)
    assert b["den"] == "2026-11-20"


def test_p0_02_3_cac_ly_do_chua_ban():
    from app.services.khach_san_vtd import ban_cong
    hn = D(2026, 11, 9)
    mua = {10: [_m(D(2026, 11, 20), D(2026, 12, 31))]}
    assert ban_cong(_k(), LP, {1: [_g(10)]}, mua, hn)["ma"] == "tu_ngay"
    assert ban_cong(_k(), LP, {1: [_g(10)]}, mua, hn)["tu"] == "2026-11-20"
    assert ban_cong(_k(), LP, {1: [_g(10, "cho_duyet")]}, mua, hn)["ma"] == "chua_goi"
    assert ban_cong(_k(), LP, {1: [_g(10, ban=False)]}, mua, hn)["ma"] == "chua_goi"
    assert ban_cong(_k(), [NS(id=1, dang_ban=False)], {1: [_g(10)]}, mua, hn)["ma"] == "chua_goi"
    assert ban_cong(_k(), LP, {1: [_g(10)]}, {10: [_m(D(2026, 10, 1), D(2026, 10, 31))]}, hn)["ma"] == "het_gia"
    assert ban_cong(_k(hien=False), LP, {1: [_g(10)]}, mua, hn)["ma"] == "chua_hien"
    n = ban_cong(_k(ngung=True), LP, {1: [_g(10)]}, mua, hn)
    assert n["ma"] == "ngung" and n["thieu_30"] is False


def test_p0_02_4_bang_crm_tra_cot_ban_cong(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    _mo_ban(db, k)                                               # gói đã duyệt, mùa giá phủ tháng 12
    r = S.ds_vtos(db, _u(db, "dh"), hom_nay=HN)
    o = next(d for d in r["khach_san"] if d["id"] == k.id)
    assert o["ban_cong"]["den"] == "2026-12-31" and o["ban_cong"]["dem"] == 31


def test_p0_02_5_giao_dien_co_cot_va_loc():
    src = open(os.path.join(GOC, "web", "app", "khach-san-vtd", "page.tsx"), encoding="utf-8").read()
    assert "<th>Bán được trên cổng</th>" in src and "<BanCong b={h.ban_cong} />" in src
    assert "Thiếu giá ${BAN_NGAY} ngày tới" in src and "Chưa bán được (" in src
    assert 'colSpan={9}' in src
