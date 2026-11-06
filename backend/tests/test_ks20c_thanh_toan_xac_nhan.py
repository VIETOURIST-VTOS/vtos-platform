# -*- coding: utf-8 -*-
"""KS-20c · Đặt phòng VTD v1.3 đợt 3: thanh toán (D3), xác nhận (D4 / M3), Đơn của tôi + Hủy (M4).
Chủ tịch 06/11/2026: làm theo bản v1.3, giữ «Đặt giữ, trả sau» (ô voucher đã bỏ từ KS-19).

  1. Trang đơn cho biết hủy thì TỪNG gói / phòng hoàn bao nhiêu (cùng luật số hoàn cuối cùng).
  2. Đơn chưa trả thì không có bảng hoàn.
  3. Giao diện: bốn bước, khung xác nhận (Đơn của tôi / In phiếu / Chỉ đường), tab Sắp tới / Đã qua / Đã hủy, hỏi hủy có lý do.
"""
import datetime as dt
from pathlib import Path

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401
from tests.test_ks20b_chia_phong import _family, hai  # noqa: F401


def _goi_khong_hoan(s, k):
    from app.services import khach_san_vtd as S
    from tests.test_ks16k_gia_tre_em_agoda import _lp  # noqa: F401
    lp = S.luu_loai_phong(s, _u(s, "dh"), k.id, {"ten": "Superior", "toi_da_nguoi_lon": 2, "so_phong": 2})
    g = S.luu_goi(s, _u(s, "dh"), lp.id, {"ten": "Tiết kiệm", "bua_sang": False, "huy_truoc_ngay": None,
                                          "mua": [{"tu_ngay": "2026-12-01", "den_ngay": "2026-12-31", "gia_thuong": 800_000,
                                                   "gia_cuoi_tuan": 800_000, "gia_niem_yet": 900_000}]})
    S.gui_duyet_goi(s, _u(s, "dh"), g.id)
    S.duyet_goi(s, _u(s, "tp"), g.id, True)
    return g


def test_ks20c_1_hoan_tung_phong(db, hai):
    from app.models.don_ks_vtd import ThanhToanKsVtd
    from app.services import don_ks_vtd as KV
    k, g, fg = hai
    gk = _goi_khong_hoan(db, k)
    d = KV.dat(db, _tk(db), k.id, {"vao": VAO, "ra": RA, "chon": [{"goi_id": g.id, "so": 1}, {"goi_id": gk.id, "so": 1}],
                                    "chia": [{"nl": 2}, {"nl": 1}], "ho_ten": "Nguyễn Thị Lan", "lien_he": "0901 000 001",
                                    "dong_y": True}, NAY)
    r = KV.ra_khach(db, d, NAY)
    assert r["hoan_dong"] == []                                         # chưa trả → không có bảng hoàn
    db.add(ThanhToanKsVtd(don_id=d.id, kenh="qr", so_tien=int(d.tong), trang_thai="da_xac_nhan"))
    db.commit()
    r = KV.ra_khach(db, d, NAY)
    ds = {x["goi"]: x for x in r["hoan_dong"]}
    assert ds["Có bữa sáng"]["mien_phi"] and ds["Có bữa sáng"]["hoan"] == ds["Có bữa sáng"]["tien"] > 0
    assert not ds["Tiết kiệm"]["mien_phi"] and ds["Tiết kiệm"]["hoan"] == 0 and ds["Tiết kiệm"]["huy_han"] is None
    assert sorted(p for x in r["hoan_dong"] for p in x["phong"]) == [1, 2]
    assert r["hoan_neu_huy"] == ds["Có bữa sáng"]["hoan"]               # cùng luật với số hoàn cuối cùng
    sau_han = dt.datetime(2026, 12, 17, 9, 0)                            # hạn miễn phí hủy 16/12 đã qua
    r = KV.ra_khach(db, d, sau_han)
    assert all(x["hoan"] == 0 for x in r["hoan_dong"]) and r["hoan_neu_huy"] == 0


def test_ks20c_2_giao_dien():
    c = (Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "KhachSanVtd.tsx").read_text(encoding="utf-8")
    for t in ('["Chọn phòng", "Thông tin", "Thanh toán", "Xác nhận"]', "Thanh toán thành công = phòng được xác nhận ngay.",
              "Tích điểm VTD", "Xem trong Đơn của tôi", "/cong?tab=bookings", "In / lưu phiếu xác nhận (PDF)", "Chỉ đường Google Maps",
              '"Sắp tới"', '"Đã qua"', '"Đã hủy"', "Hoàn về tài khoản đã trả", "Lý do (không bắt buộc)", "Xác nhận hủy", "Giữ đơn",
              "hoan_dong", "Khách hủy · ${lyDo}", "ksv13-sheet", "Đặt giữ, trả trước"):
        assert t in c, t
