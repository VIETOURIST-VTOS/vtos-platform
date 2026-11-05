# -*- coding: utf-8 -*-
"""KS-14 · Đặt phòng khách sạn VTD có thanh toán (Chủ tịch duyệt bản xem thử 30/10/2026).

  1. Phòng trống: mặc định = số phòng/đêm; Điều hành sửa / đóng bán; đơn giữ 15 phút chiếm phòng, hết giờ thì nhả.
  2. QR: đúng mã + đúng số → máy khớp, đơn «Đã thanh toán», hạn chốt 2 giờ làm việc; Kế toán ghi sổ Nợ 1121 / Có 3388.
     Lệch số → Kế toán gán tay. Thẻ OnePay: thành công → đã thanh toán; đối soát ghi phí 6428.
  3. Hủy theo gói: trước hạn miễn phí → hoàn 100%; sau hạn → 0; TP / GĐ KD miễn phạt → hoàn đủ; hoàn hai người.
  4. Điều hành chốt (mã khách sạn) hoặc báo hết phòng → hoàn 100%. Kế toán chốt hoa hồng sau ngày trả phòng.
"""
import datetime as dt

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO, _ks, _mo_ban

NAY = dt.datetime(2026, 12, 1, 9, 0)          # thứ Ba


@pytest.fixture()
def k3(db):
    """Khách sạn đang hiện, Deluxe 3 phòng/đêm, gói «Có bữa sáng» miễn phí hủy trước 2 ngày; sổ kế toán sẵn."""
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.core import Company, User
    from app.services import accounting as ACC
    db.add(Company(code="VTD", name="CTCP Vietourist Holdings", kind="me"))
    db.add_all([User(username=t, full_name=t, role=v, password_hash="x") for t, v in (("tpkd", "tp_kd"), ("ct", "chutich"))])
    db.add_all([TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000001", ho_ten="Lan", trang_thai="hoat_dong"),
                TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000002", ho_ten="Bình", trang_thai="hoat_dong")])
    db.commit()
    ACC.seed_accounts(db)
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)
    return k, lp, g


def _tk(s, i=1):
    from app.models.cong_ngoai import TaiKhoanNgoai
    return s.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.dien_thoai == f"090100000{i}")).scalars().one()


def _dat(s, k, g, so=1, tk=None, now=NAY, **them):
    from app.services import don_ks_vtd as S
    d = S.dat(s, tk or _tk(s), k.id, {"vao": VAO, "ra": RA, "nguoi_lon": 2, "chon": [{"goi_id": g.id, "so": so}],
                                       "ho_ten": "Nguyễn Thị Lan", "lien_he": "0901 000 001", "dong_y": True, **them}, now)
    s.commit()
    return d


def _txn(s, so_tien, noi_dung, sid="T1"):
    from app.models.payments import BankTransaction
    t = BankTransaction(sepay_id=sid, transaction_date=NAY, transfer_type="in", amount=so_tien, content=noi_dung,
                        match_status="chua_khop")
    s.add(t); s.commit()
    return t


def _ct(s, ma):
    from app.models.accounting import JournalEntry
    e = s.execute(select(JournalEntry).where(JournalEntry.code == ma)).scalars().one()
    return sorted((l.account_code, int(l.debit), int(l.credit)) for l in e.lines)


def test_gio_lam_viec():
    from app.services import don_ks_vtd as S
    assert S.cong_gio_lam(dt.datetime(2026, 12, 1, 9, 0)) == dt.datetime(2026, 12, 1, 11, 0)
    assert S.cong_gio_lam(dt.datetime(2026, 12, 5, 17, 0)) == dt.datetime(2026, 12, 7, 9, 30)     # T7 17:00 → T2 9:30
    assert S.cong_gio_lam(dt.datetime(2026, 12, 6, 10, 0)) == dt.datetime(2026, 12, 7, 10, 0)     # Chủ nhật → T2
    assert S.cong_gio_lam(dt.datetime(2026, 12, 1, 22, 0)) == dt.datetime(2026, 12, 2, 10, 0)


def test_phong_trong_giu_15_phut_va_dong_ban(db, k3):
    from app.services import don_ks_vtd as S
    k, lp, g = k3
    d = _dat(db, k, g, so=2)
    assert d.trang_thai == "cho_tra" and d.tong == 7_600_000 and d.giu_den == NAY + dt.timedelta(minutes=15)
    assert d.dong[0]["huy_han"] == "2026-12-16" and S.MA_RE.fullmatch(d.ma)
    assert S.con_phong(db, [lp], VAO, RA, NAY)[lp.id] == 1
    with pytest.raises(S.LoiDon, match="chỉ còn 1"):
        _dat(db, k, g, so=2, tk=_tk(db, 2))
    # hết 15 phút → phòng nhả
    assert S.con_phong(db, [lp], VAO, RA, NAY + dt.timedelta(minutes=16))[lp.id] == 3
    # Điều hành đóng bán đêm 19/12 → cả kỳ hết phòng; Kinh doanh không sửa được
    with pytest.raises(S.LoiDon):
        S.luu_phong_trong(db, _u(db, "kd"), lp.id, ["2026-12-19"], None, True, NAY)
    S.luu_phong_trong(db, _u(db, "dh"), lp.id, ["2026-12-19"], None, True, NAY)
    assert S.con_phong(db, [lp], VAO, RA, NAY + dt.timedelta(minutes=16))[lp.id] == 0
    b = S.bang_phong_trong(db, _u(db, "tp"), k.id, "2026-12-18", 3, NAY)
    assert [o["dong"] for o in b["phong"][0]["o"]] == [False, True, False] and b["phong"][0]["o"][0]["nhan"] == 2
    with pytest.raises(S.LoiDon, match="hết phòng"):
        _dat(db, k, g, so=1, tk=_tk(db, 2), now=NAY + dt.timedelta(minutes=16))
    S.luu_phong_trong(db, _u(db, "dh"), lp.id, ["2026-12-19"], 5, False, NAY)
    assert S.con_phong(db, [lp], VAO, RA, NAY + dt.timedelta(minutes=16))[lp.id] == 3     # min(3, 5, 3)


def test_qr_may_khop_ke_toan_ghi_so_va_gan_tay(db, k3):
    from app.services import don_ks_vtd as S
    from app.services import payments as P
    k, lp, g = k3
    d = _dat(db, k, g)
    t = _txn(db, d.tong, f"CK {d.ma} NGUYEN THI LAN")
    P.match_transaction(db, t); db.commit()
    assert t.match_status == "da_khop" and d.trang_thai == "da_xac_nhan"   # KS-19: đủ tiền là xác nhận
    assert d.han_chot is not None and d.han_chot > d.tra_luc
    tt = db.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    assert tt.trang_thai == "tu_khop" and not tt.but_toan
    with pytest.raises(S.LoiDon):
        S.kt_xac_nhan_qr(db, _u(db, "dh"), tt.id, NAY)
    S.kt_xac_nhan_qr(db, _u(db, "kt"), tt.id, NAY); db.commit()
    assert _ct(db, tt.but_toan) == [("1121", 3_800_000, 0), ("3388", 0, 3_800_000)]
    # đơn thứ hai chuyển thiếu → không tự khớp, Kế toán gán; vẫn chưa đủ → chuyển hoàn
    d2 = _dat(db, k, g, tk=_tk(db, 2))
    t2 = _txn(db, 3_000_000, f"{d2.ma}", sid="T2")
    P.match_transaction(db, t2); db.commit()
    assert t2.match_status == "cho_ke_toan" and d2.trang_thai == "cho_tra"
    assert [x["ma"] for x in S.giao_dich_cho(db, _u(db, "kt"), NAY)] == [d2.ma]
    S.kt_gan_qr(db, _u(db, "kt"), d2.id, t2.id, NAY); db.commit()
    assert S.da_tra(db, d2) == 3_000_000 and d2.trang_thai == "cho_tra"
    S.kt_chuyen_hoan(db, _u(db, "kt"), d2.id, "Khách chuyển thiếu tiền", NAY); db.commit()
    assert d2.trang_thai == "da_huy" and d2.so_hoan == 3_000_000 and d2.hoan_tt == "cho_sales"


def test_huy_theo_goi_va_hoan_hai_nguoi(db, k3):
    from app.services import don_ks_vtd as S
    from app.services import payments as P
    k, lp, g = k3
    d = _dat(db, k, g)
    assert S.ra_khach(db, d, NAY)["con_phai_tra"] == d.tong == 3_800_000    # KS-19g: nút «Trả ngay ₫ …» có số
    P.match_transaction(db, _txn(db, d.tong, d.ma)); db.commit()
    r = S.ra_khach(db, d, NAY)
    assert r["hoan_neu_huy"] == 3_800_000 and r["con_phai_tra"] == 0
    S.huy_boi_khach(db, _tk(db), d.ma, "Đổi kế hoạch", NAY); db.commit()
    assert d.trang_thai == "da_huy" and d.so_hoan == 3_800_000 and d.hoan_tt == "cho_sales"
    with pytest.raises(S.LoiDon, match="Sales"):
        S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 123", NAY)
    S.sales_xac_nhan_hoan(db, _u(db, "kd"), d.id, "", NAY)
    with pytest.raises(S.LoiDon, match="chưa ghi sổ"):
        S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 123", NAY)          # tiền vào chưa ghi sổ thì chưa hoàn
    tt = db.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    S.kt_xac_nhan_qr(db, _u(db, "kt"), tt.id, NAY)
    S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 123", NAY); db.commit()
    assert d.hoan_tt == "da_hoan" and d.da_hoan_tien == 3_800_000
    # đơn hủy SAU hạn miễn phí (17/12) → không hoàn; TP KD miễn phạt → hoàn đủ
    d2 = _dat(db, k, g, tk=_tk(db, 2))
    P.match_transaction(db, _txn(db, d2.tong, d2.ma, sid="T9")); db.commit()
    tre = dt.datetime(2026, 12, 17, 10, 0)
    S.huy_boi_khach(db, _tk(db, 2), d2.ma, "", tre); db.commit()
    assert d2.so_hoan == 0 and d2.hoan_tt == ""
    with pytest.raises(S.LoiDon):
        S.sales_mien_phat(db, _u(db, "kd"), d2.id, "Khách VIP ốm", tre)   # NV KD không miễn phạt
    S.sales_mien_phat(db, _u(db, "tpkd"), d2.id, "Khách VIP ốm", tre); db.commit()
    assert d2.so_hoan == 3_800_000 and d2.hoan_tt == "cho_chi"


def test_dieu_hanh_chot_het_phong_va_ke_toan_chot(db, k3, monkeypatch):
    from app.services import don_ks_vtd as S
    from app.services import onepay as OP
    k, lp, g = k3
    d = _dat(db, k, g)
    # thẻ: OnePay báo thành công đúng số tiền
    monkeypatch.setattr(OP, "bat", lambda: True)
    monkeypatch.setattr(OP, "duong_thanh_toan", lambda *a, **kw: "https://onepay.test/pay")
    assert S.onepay_bat_dau(db, _tk(db), d.ma, "https://kh.vietourist.vn", "1.2.3.4", NAY) == "https://onepay.test/pay"
    t = db.execute(select(S.ThanhToanKsVtd).where(S.ThanhToanKsVtd.don_id == d.id)).scalars().one()
    assert S.cua_minh({"vpc_MerchTxnRef": t.ma_gd})
    monkeypatch.setattr(OP, "ket_qua", lambda p: {"hop_le": True, "ma_gd": t.ma_gd, "ma_kq": "0", "so_gd": "99",
                                                 "thanh_cong": True, "so_tien": int(t.so_tien)})
    S.onepay_ket_qua(db, {}, NAY + dt.timedelta(minutes=3))
    assert t.trang_thai == "thanh_cong" and d.trang_thai == "da_xac_nhan"   # KS-19
    S.kt_doi_soat(db, _u(db, "kt"), t.id, 76_000, NAY); db.commit()
    assert _ct(db, t.but_toan) == [("1121", 3_724_000, 0), ("3388", 0, 3_800_000), ("6428", 76_000, 0)]
    with pytest.raises(S.LoiDon):
        S.dh_xac_nhan(db, _u(db, "kd"), d.id, "BX-1", NAY)
    with pytest.raises(S.LoiDon, match="mã xác nhận"):
        S.dh_xac_nhan(db, _u(db, "dh"), d.id, "", NAY)
    S.dh_xac_nhan(db, _u(db, "dh"), d.id, "BXMK-88213", NAY); db.commit()
    assert d.trang_thai == "da_xac_nhan" and d.ma_xac_nhan_ks == "BXMK-88213"
    with pytest.raises(S.LoiDon, match="sau ngày"):
        S.kt_chot(db, _u(db, "kt"), d.id, 400_000, NAY)
    sau = dt.datetime(2026, 12, 22, 9, 0)
    with pytest.raises(S.LoiDon, match="0 –"):
        S.kt_chot(db, _u(db, "kt"), d.id, 9_000_000, sau)
    S.kt_chot(db, _u(db, "kt"), d.id, 400_000, sau); db.commit()
    assert d.phai_tra_ks == 3_400_000
    assert S.hang_ke_toan(db, _u(db, "kt"), sau)["phai_tra_ks"][0]["phai_tra"] == 3_400_000
    # khách sạn báo hết phòng → hoàn 100% kể cả gói không hoàn
    d2 = _dat(db, k, g, tk=_tk(db, 2))
    from app.services import payments as P
    P.match_transaction(db, _txn(db, d2.tong, d2.ma, sid="T5")); db.commit()
    S.dh_het_phong(db, _u(db, "dh"), d2.id, "Khách sạn báo hết Deluxe", NAY); db.commit()
    assert d2.trang_thai == "da_huy" and d2.so_hoan == 3_800_000 and d2.hoan_tt == "cho_sales"
    assert S.con_phong(db, [lp], VAO, RA, NAY)[lp.id] == 2           # đơn hủy trả phòng; đơn 1 vẫn giữ 1
