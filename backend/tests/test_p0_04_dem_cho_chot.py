# -*- coding: utf-8 -*-
"""P0-04 (Đề xuất hoàn thiện VTD v1.1; Chủ tịch duyệt 09/11/2026).

Rà ngày 09/11: phần lõi đã đúng — thanh toán lưu riêng (ThanhToanKsVtd), IPN lặp không ghi thu hai lần, khách sạn từ chối
thì «KS hết phòng» hủy + hoàn 100%, và theo KS-19 khách trả đủ là máy tự xác nhận. Lệch ở crm: nút tab «Đơn đặt phòng
(N chờ chốt)» và chip «Chờ chốt với khách sạn (N)» chỉ đếm `da_tra`, bỏ sót đơn máy đã tự xác nhận mà Điều hành chưa
ghi mã khách sạn — trong khi danh sách bộ lọc cho_chot có cả hai. Nay đếm `dem.cho_chot` cùng một điều kiện."""
import os
from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401
from tests.test_ks20b_chia_phong import hai  # noqa: F401

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p0_04_1_dem_cho_chot_khop_danh_sach(db, hai):
    from app.services import don_ks_vtd as KV
    k, g, _fg = hai
    ds = []
    for i in range(3):
        ds.append(KV.dat(db, _tk(db), k.id, {"vao": VAO, "ra": RA, "chon": [{"goi_id": g.id, "so": 1}], "chia": [{"nl": 2}],
                                             "ho_ten": f"Khách {i}", "lien_he": "0901 000 00" + str(i), "dong_y": True}, NAY))
    ds[0].trang_thai = "da_tra"                                          # chờ Điều hành chốt (giường phụ / trẻ em)
    ds[1].trang_thai = "da_xac_nhan"                                     # máy tự xác nhận, chưa có mã khách sạn
    ds[2].trang_thai, ds[2].ma_xac_nhan_ks = "da_xac_nhan", "HTL-123"    # đã báo khách sạn xong
    db.commit()
    r = KV.ds_vtos(db, _u(db, "dh"), "cho_chot", now=NAY)
    ma = {d["ma"] for d in r["don"]}
    assert ds[0].ma in ma and ds[1].ma in ma and ds[2].ma not in ma
    assert r["dem"]["cho_chot"] == len(r["don"]) >= 2
    assert r["dem"]["cho_chot"] > r["dem"].get("da_tra", 0)             # trước P0-04 nút chỉ hiện số này


def test_p0_04_2_giao_dien_dung_dem_cho_chot():
    src = open(os.path.join(GOC, "web", "app", "khach-san-vtd", "page.tsx"), encoding="utf-8").read()
    assert "demDon.da_tra" not in src and "x.dem.da_tra" not in src
    assert "${demDon.cho_chot} chờ chốt" in src and "Chờ chốt với khách sạn (${x.dem.cho_chot || 0})" in src
    assert "Khách trả đủ là máy xác nhận và gửi phiếu ngay" in src
