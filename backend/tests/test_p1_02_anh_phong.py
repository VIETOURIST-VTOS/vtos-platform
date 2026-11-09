# -*- coding: utf-8 -*-
"""P1-02 (Đề xuất hoàn thiện VTD v1.1; Chủ tịch giữ quyết định 05/11 «phòng chưa có ảnh thì lấy ảnh đại diện khách sạn»,
chọn «Giữ ảnh, ghi rõ nhãn» + cảnh báo trên crm, duyệt bản xem trước 09/11/2026).

Rà 09/11: chi_tiet_cong() gắn ảnh khách sạn vào p.anh kèm cờ anh_dai_dien, nhưng cổng lấy p.anh[0] làm «ảnh riêng» nên
nhãn «Ảnh khách sạn» có sẵn trong mã không bao giờ hiện — khách tưởng ảnh toàn cảnh là ảnh phòng."""
import os
from tests.test_at1_am_thuc import db  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, _ks, _mo_ban, _u

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p1_02_1_cong_hien_nhan_khi_dung_anh_thay():
    s = open(os.path.join(GOC, "web", "components", "cong", "KhachSanVtd.tsx"), encoding="utf-8").read()
    assert "const rieng = p.anh_dai_dien ? null : (p.anh?.[0] || aP[0]);" in s
    assert "Ảnh khách sạn · chưa có ảnh riêng của phòng" in s


def test_p1_02_2_crm_dem_phong_chua_anh_va_anh_nhom_khac(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    _mo_ban(db, k)                                 # một loại phòng đang bán + một ảnh đã duyệt (ảnh chung, chưa gắn phòng)
    r = S.ds_vtos(db, _u(db, "dh"), hom_nay=HN)
    o = next(d for d in r["khach_san"] if d["id"] == k.id)
    assert o["lp_ban"] == 1 and o["lp_chua_anh"] == 1
    from sqlalchemy import select
    from app.models.khach_san_vtd import AnhKhachSanVtd
    anh = db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id == k.id)).scalars().all()
    assert o["anh_khac"] == sum(1 for y in anh if y.trang_thai == "da_duyet" and (y.nhom or "khac") == "khac")
    # Gắn ảnh cho đúng loại phòng → hết cảnh báo phòng chưa có ảnh.
    lp_id = next(x for x in S._lp_cua(db, k.id) if x.dang_ban).id
    y = next(y for y in anh if y.trang_thai == "da_duyet")
    y.loai_phong_id, y.nhom = lp_id, "phong"
    db.flush()
    o2 = next(d for d in S.ds_vtos(db, _u(db, "dh"), hom_nay=HN)["khach_san"] if d["id"] == k.id)
    assert o2["lp_chua_anh"] == 0 and o2["anh_khac"] == o["anh_khac"] - (1 if (o["anh_khac"] > 0) else 0)


def test_p1_02_3_man_crm_co_canh_bao():
    s = open(os.path.join(GOC, "web", "app", "khach-san-vtd", "page.tsx"), encoding="utf-8").read()
    assert "loại phòng chưa có ảnh" in s and "ảnh nhóm «Khác»" in s and "Ảnh phòng đủ" in s
