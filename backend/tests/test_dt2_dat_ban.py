# -*- coding: utf-8 -*-
"""DT-2 · Đặt bàn nhà hàng có thanh toán (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Số phải trả trước do MÁY tính: lẻ cọc 10% / đoàn (≥10 khách, đặt sẵn menu) cọc 50% / trả đủ 100%.
  2. Người đặt: khách, cổ đông đã xác minh, đại lý, CTV đã nối; đối tác phải ghi tên khách + tick khách đồng ý.
  3. Chưa nhận bàn thì không có QR / thẻ; nhận → chờ trả có hạn; từ chối → không phải trả.
  4. Tiền QR: chỉ Kế toán gán, một giao dịch một lần; đủ → giữ bàn. Tiền thẻ: chỉ tin chữ ký OnePay,
     đúng số tiền, chạy lại không ghi thêm.
  5. Hủy: ≥24 giờ hoàn đủ; 3–24 giờ giữ 10%; <3 giờ / không đến: lẻ 10%, đoàn 50%; không giữ quá số đã trả;
     quá hạn trả thì không phạt. Miễn phạt chỉ TP / GĐ KD.
  6. Hoàn: Sales xác nhận → Kế toán ghi đã hoàn kèm chứng từ. Tiền về khi bàn không còn → tự thành khoản hoàn.
  7. Nhà hàng báo đã dùng (bàn đã giữ) → Kế toán chốt một lần → vào D06 của đối tác; đơn khách tự đặt thì không.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NAY = dt.datetime.now().replace(second=0, microsecond=0)
NGAY = (NAY + dt.timedelta(days=5)).date()


class _Kho:
    def __init__(self): self.d = {}
    def put(self, key, data, kieu=""):
        self.d[key] = data
        return type("L", (), {"key": key, "checksum": __import__("hashlib").sha256(data).hexdigest()})()
    def get(self, key): return self.d[key]


def hop_dong_mau(s, n, bps=1000, tu=dt.date(2026, 1, 1), den=None):
    """AT-1: hợp đồng đã ký + tệp (dữ liệu thử) để nhà hàng đủ điều kiện mở đặt bàn."""
    from app.models.attachments import Attachment
    from app.models.nha_hang import HopDongNhaHang
    a = Attachment(doi_tuong="nha_cung_cap", doi_tuong_id=f"NCC{n.id}", ten_tep="hd.pdf", checksum=f"{n.id:064d}", khoa_luu=f"k{n.id}", loai="hop_dong")
    s.add(a); s.flush()
    h = HopDongNhaHang(nha_hang_id=n.id, so_hd=f"HD-{n.ma}", ngay_ky=tu, tu_ngay=tu, den_ngay=den, hoa_hong_bps=bps,
                       attachment_id=a.id, con_dung=True, ghi_boi="nvdh")
    s.add(h); s.flush()
    return h


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.models.suppliers import Supplier
    from app.models.nha_hang import NhaHang, ThucDonNhaHang
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    from app.services import storage as ST
    ST._CACHE["s"] = _Kho()
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("kt", "ketoan"), ("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("nvdh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    sup = Supplier(code="NCC0042", ten="Nhà hàng Hương Biển", loai="nha_hang", ma_so_thue="0311111111")
    s.add(sup); s.flush()
    n = NhaHang(ma="NH001", ten="Hương Biển", tinh_thanh="Kiên Giang", hien_cong=True, supplier_id=sup.id,
                lien_he_xac_minh=True)
    s.add(n); s.flush()
    hop_dong_mau(s, n)                                           # AT-1: chỉ nơi đã ký hợp đồng mới đặt được
    s.add_all([ThucDonNhaHang(nha_hang_id=n.id, ten="Set hải sản", loai="set", gia_nguoi_lon=450000, gia_tre_em=225000),
               ThucDonNhaHang(nha_hang_id=n.id, ten="Gọi món", loai="goi_mon", gia_nguoi_lon=300000)])
    dl = DoiTacBanHang(ma="DL012", ten="Đại lý Sao Mai", loai="dai_ly", hieu_luc_tu=dt.date(2026, 1, 1))
    s.add(dl); s.flush()
    s.add_all([TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000001", ho_ten="Khách A", trang_thai="hoat_dong"),
               TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000002", ho_ten="Khách B", trang_thai="hoat_dong"),
               TaiKhoanNgoai(loai="doi_tac", loai_doi_tac="dai_ly", dien_thoai="0901000003", trang_thai="hoat_dong", doi_tac_id=dl.id),
               TaiKhoanNgoai(loai="doi_tac", loai_doi_tac="ncc", dien_thoai="0901000004", trang_thai="hoat_dong", ncc_id=sup.id),
               TaiKhoanNgoai(loai="co_dong", dien_thoai="0901000005", trang_thai="cho_xac_minh")])
    from app.models.core import Company
    from app.services import accounting as ACC
    s.add(Company(code="VTD", name="CTCP Vietourist Holdings", kind="me"))
    s.commit()
    ACC.seed_accounts(s)                                         # DT-3: tiền đặt bàn ghi sổ thu hộ
    yield s
    s.close(); ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _tk(s, sdt):
    from app.models.cong_ngoai import TaiKhoanNgoai
    return s.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.dien_thoai == sdt)).scalars().one()


def _td(s, loai="set"):
    from app.models.nha_hang import ThucDonNhaHang
    return s.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.loai == loai)).scalars().one()


def _dat(s, tk="0901000001", nl=2, te=0, cach="coc", loai="set", gio="18:30", ngay=NGAY, **them):
    from app.services import dat_ban as S
    td = _td(s, loai)
    d = {"nha_hang_id": td.nha_hang_id, "thuc_don_id": td.id, "ngay": ngay, "gio": gio, "nguoi_lon": nl, "tre_em": te,
         "cach_tt": cach, "dong_y_chinh_sach": True, **them}
    return S.tao(s, _tk(s, tk), d, NAY)


def _ncc(s):
    from app.models.suppliers import Supplier
    return s.execute(select(Supplier)).scalars().one()


def _nhan(s, d, nhan=True, now=NAY):
    from app.models.cong_khach import YeuCauKhach
    from app.services import cong_ncc as N
    y = s.get(YeuCauKhach, d.yeu_cau_id)
    N.xu_ly_dat_ban(s, _tk(s, "0901000004"), _ncc(s), y.id, nhan, "" if nhan else "Kín bàn")
    s.commit(); s.refresh(d)
    return d


def _txn(s, so_tien, noi_dung, sid="T1"):
    from app.models.payments import BankTransaction
    t = BankTransaction(sepay_id=sid, transaction_date=NAY, transfer_type="in", amount=so_tien, content=noi_dung,
                        match_status="cho_ke_toan")
    s.add(t); s.commit()
    return t


def _tra_qr(s, d, so_tien=None, sid="T1"):
    from app.services import dat_ban as S
    t = _txn(s, so_tien if so_tien is not None else int(d.phai_tra_truoc), f"CK {d.ma} chuyen", sid)
    S.kt_gan_qr(s, _u(s, "kt"), d.id, t.id, NAY); s.commit(); s.refresh(d)
    return t


# ---------------------------------------------------------------- 1. số phải trả
def test_1_so_phai_tra_do_may_tinh(db):
    d = _dat(db, nl=2, te=1)                       # 2×450k + 225k = 1.125.000 → cọc 10% = 112.500 → làm tròn lên 113.000
    assert int(d.tam_tinh) == 1125000 and d.ty_le_coc == 10 and int(d.phai_tra_truoc) == 113000 and not d.la_doan
    d2 = _dat(db, nl=10, cach="coc")               # đoàn 10 khách set menu → cọc 50%
    assert d2.la_doan and d2.ty_le_coc == 50 and int(d2.phai_tra_truoc) == 2250000
    d3 = _dat(db, nl=10, cach="du")
    assert int(d3.phai_tra_truoc) == 4500000
    d4 = _dat(db, nl=12, loai="goi_mon")            # gọi món không phải «đặt sẵn menu» → không là đoàn
    assert not d4.la_doan and d4.ty_le_coc == 10
    assert d.ma.startswith("NH") and len(d.ma) == 10


def test_1b_thieu_dieu_kien_bi_chan(db):
    from app.services import dat_ban as S
    with pytest.raises(S.LoiDatBan, match="cách thanh toán"):
        _dat(db, cach="")
    with pytest.raises(S.LoiDatBan, match="chính sách"):
        _dat(db, dong_y_chinh_sach=False)


# ---------------------------------------------------------------- 2. người đặt
def test_2_nguoi_dat(db):
    from app.services import dat_ban as S
    with pytest.raises(S.LoiDatBan, match="tên khách"):
        _dat(db, tk="0901000003")
    with pytest.raises(S.LoiDatBan, match="khách đã đồng ý"):
        _dat(db, tk="0901000003", ten_khach="Anh Minh", dien_thoai="0912345678")
    d = _dat(db, tk="0901000003", ten_khach="Anh Minh", dien_thoai="0912345678", dong_y_khach=True)
    assert d.nguon == "dai_ly" and d.doi_tac_id is not None and d.dien_thoai == "0912345678"
    with pytest.raises(S.LoiDatBan):
        _dat(db, tk="0901000004", ten_khach="X", dien_thoai="0912345678", dong_y_khach=True)    # tài khoản NCC
    with pytest.raises(S.LoiDatBan):
        _dat(db, tk="0901000005")                                                           # cổ đông chưa xác minh
    # khách không thấy đơn của người khác
    with pytest.raises(S.LoiDatBan):
        S.qr(db, _tk(db, "0901000002"), d.ma)


# ---------------------------------------------------------------- 3. nhận bàn rồi mới trả
def test_3_chua_nhan_khong_tra_nhan_co_han_tu_choi(db):
    from app.services import dat_ban as S
    from app.core.config import settings
    d = _dat(db)
    with pytest.raises(S.LoiDatBan):
        S.qr(db, _tk(db, "0901000001"), d.ma)
    _nhan(db, d)
    assert d.trang_thai == "cho_tra" and d.han_tra == S.gio_an(d) - dt.timedelta(hours=24)
    d2 = _nhan(db, _dat(db), nhan=False)
    assert d2.trang_thai == "tu_choi"
    settings.ONEPAY_MERCHANT = settings.ONEPAY_ACCESS_CODE = settings.ONEPAY_HASH_KEY = ""
    with pytest.raises(S.LoiDatBan, match="thẻ chưa mở"):
        S.onepay_bat_dau(db, _tk(db, "0901000001"), d.ma, "https://kh.vietourist.vn", "1.1.1.1", NAY)
    # quá hạn chưa trả → hết hạn
    S.cap_nhat(db, d, d.han_tra + dt.timedelta(minutes=1))
    assert d.trang_thai == "het_han"


# ---------------------------------------------------------------- 4. tiền vào
def test_4_qr_chi_ke_toan_mot_lan(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db))
    t = _txn(db, int(d.phai_tra_truoc), f"{d.ma}")
    with pytest.raises(S.LoiDatBan):
        S.kt_gan_qr(db, _u(db, "nvkd"), d.id, t.id, NAY)
    S.kt_gan_qr(db, _u(db, "kt"), d.id, t.id, NAY); db.commit(); db.refresh(d)
    assert d.trang_thai == "da_giu" and S.da_tra(db, d) == int(d.phai_tra_truoc) and t.match_status == "da_khop"
    with pytest.raises(S.LoiDatBan):
        S.kt_gan_qr(db, _u(db, "kt"), d.id, t.id, NAY)
    assert S.giao_dich_cho(db, NAY) == []


def test_4b_onepay_chi_tin_chu_ky(db):
    from app.services import dat_ban as S
    from app.services import onepay as OP
    from app.core.config import settings
    from urllib.parse import urlparse, parse_qs
    settings.ONEPAY_MERCHANT, settings.ONEPAY_ACCESS_CODE = "TESTONEPAY", "6BEB2546"
    settings.ONEPAY_HASH_KEY = "6D0870CDE5F24F34F3915FB0045120DB"
    try:
        d = _nhan(db, _dat(db))
        url = S.onepay_bat_dau(db, _tk(db, "0901000001"), d.ma, "https://kh.vietourist.vn", "1.1.1.1", NAY)
        q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        assert OP.kiem(q) and q["vpc_Amount"] == str(int(d.phai_tra_truoc) * 100)
        ve = {"vpc_MerchTxnRef": q["vpc_MerchTxnRef"], "vpc_Amount": q["vpc_Amount"], "vpc_TxnResponseCode": "0",
              "vpc_TransactionNo": "998877", "vpc_Merchant": "TESTONEPAY"}
        gia = {**ve, "vpc_SecureHash": "AB" * 32}
        assert S.onepay_ket_qua(db, gia, NAY) is None                 # chữ ký giả: không đổi gì
        db.refresh(d); assert d.trang_thai == "cho_tra"
        sai_tien = {**ve, "vpc_Amount": "100"}; sai_tien["vpc_SecureHash"] = OP.ky(sai_tien)
        that = {**ve}; that["vpc_SecureHash"] = OP.ky(that)
        S.onepay_ket_qua(db, that, NAY)
        S.onepay_ket_qua(db, that, NAY)                                 # chạy lại: không ghi thêm
        S.onepay_ket_qua(db, sai_tien, NAY)
        db.refresh(d)
        assert d.trang_thai == "da_giu" and S.da_tra(db, d) == int(d.phai_tra_truoc)
        # số tiền không khớp trên một giao dịch khác → thất bại
        d2 = _nhan(db, _dat(db))
        url2 = S.onepay_bat_dau(db, _tk(db, "0901000001"), d2.ma, "https://kh.vietourist.vn", "1.1.1.1", NAY)
        q2 = {k: v[0] for k, v in parse_qs(urlparse(url2).query).items()}
        x = {"vpc_MerchTxnRef": q2["vpc_MerchTxnRef"], "vpc_Amount": "100", "vpc_TxnResponseCode": "0"}
        x["vpc_SecureHash"] = OP.ky(x)
        S.onepay_ket_qua(db, x, NAY); db.refresh(d2)
        assert d2.trang_thai == "cho_tra" and S.da_tra(db, d2) == 0
    finally:
        settings.ONEPAY_MERCHANT = settings.ONEPAY_ACCESS_CODE = settings.ONEPAY_HASH_KEY = ""


# ---------------------------------------------------------------- 5. chính sách hủy
def test_5_chinh_sach_huy(db):
    from app.services import dat_ban as S
    tk = _tk(db, "0901000001")
    # trước ≥ 24 giờ → hoàn đủ
    d = _nhan(db, _dat(db, cach="du")); _tra_qr(db, d, sid="A")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "đổi lịch", S.gio_an(d) - dt.timedelta(hours=30))
    assert d.so_giu == 0 and d.so_hoan == int(d.tam_tinh) and d.hoan_tt == "cho_sales"
    # 3–24 giờ → giữ 10% bill
    d = _nhan(db, _dat(db, cach="du")); _tra_qr(db, d, sid="B")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=10))
    assert d.so_giu == 90000 and d.so_hoan == 810000
    # đoàn < 3 giờ → giữ 50%
    d = _nhan(db, _dat(db, nl=10, cach="du")); _tra_qr(db, d, sid="C")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=2))
    assert d.so_giu == 2250000 and d.so_hoan == 2250000
    # lẻ < 3 giờ → giữ 10%, và không giữ quá số đã cọc
    d = _nhan(db, _dat(db, nl=2, cach="coc")); _tra_qr(db, d, sid="D")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=1))
    assert d.so_giu == 90000 and d.so_hoan == 0 and d.hoan_tt == "khong_hoan"
    # đoàn cọc 50% hủy 10 giờ → chỉ giữ 10%
    d = _nhan(db, _dat(db, nl=10, cach="coc")); _tra_qr(db, d, sid="E")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=10))
    assert d.so_giu == 450000 and d.so_hoan == 2250000 - 450000
    # chưa trả đồng nào (nhà hàng chưa nhận) → không giữ gì (không giữ quá số đã trả)
    d = _dat(db, nl=10, cach="du")
    S.huy_boi_nguoi_dat(db, tk, d.ma, "", S.gio_an(d) - dt.timedelta(hours=1))
    assert d.so_giu == 0 and d.so_hoan == 0 and d.hoan_tt == ""
    # đã hủy rồi thì không hủy lại
    with pytest.raises(S.LoiDatBan):
        S.huy_boi_nguoi_dat(db, tk, d.ma, "", NAY)


def test_5b_mien_phat_chi_tp_kd_va_qua_han_khong_phat(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, nl=10, cach="du")); _tra_qr(db, d, sid="F")
    with pytest.raises(S.LoiDatBan, match="TP / GĐ"):
        S.sales_huy(db, _u(db, "nvkd"), d.id, "Nhà hàng mất điện", True, S.gio_an(d) - dt.timedelta(hours=1))
    S.sales_huy(db, _u(db, "tpkd"), d.id, "Nhà hàng mất điện", True, S.gio_an(d) - dt.timedelta(hours=1))
    assert d.so_giu == 0 and d.so_hoan == int(d.tam_tinh)
    # tiền về sau khi quá hạn → không phạt, thành khoản hoàn
    d2 = _nhan(db, _dat(db))
    S.cap_nhat(db, d2, d2.han_tra + dt.timedelta(minutes=5)); db.commit()
    assert d2.trang_thai == "het_han"
    t = _txn(db, int(d2.phai_tra_truoc), d2.ma, "G")
    S.kt_gan_qr(db, _u(db, "kt"), d2.id, t.id, d2.han_tra + dt.timedelta(hours=1)); db.commit(); db.refresh(d2)
    assert d2.trang_thai == "het_han" and d2.so_hoan == int(d2.phai_tra_truoc) and d2.hoan_tt == "cho_sales"
    # người đặt hủy đơn quá hạn đã trả muộn, sát giờ ăn → vẫn không phạt
    S.huy_boi_nguoi_dat(db, _tk(db, "0901000001"), d2.ma, "", S.gio_an(d2) - dt.timedelta(hours=1))
    assert d2.so_giu == 0 and d2.so_hoan == int(d2.phai_tra_truoc)


# ---------------------------------------------------------------- 6. hoàn tiền
def test_6_hoan_hai_buoc(db):
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, cach="du")); _tra_qr(db, d, sid="H")
    S.huy_boi_nguoi_dat(db, _tk(db, "0901000001"), d.ma, "", S.gio_an(d) - dt.timedelta(days=2))
    with pytest.raises(S.LoiDatBan):
        S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 123")               # chưa qua Sales
    with pytest.raises(S.LoiDatBan):
        S.sales_xac_nhan_hoan(db, _u(db, "kt"), d.id, "")
    S.sales_xac_nhan_hoan(db, _u(db, "nvkd"), d.id, "đã gọi khách")
    with pytest.raises(S.LoiDatBan, match="chứng từ"):
        S.kt_da_hoan(db, _u(db, "kt"), d.id, "")
    S.kt_da_hoan(db, _u(db, "kt"), d.id, "UNC 123")
    assert d.hoan_tt == "da_hoan"


# ---------------------------------------------------------------- 7. đã dùng, chốt, D06
def test_7_da_dung_chot_vao_d06(db):
    from app.services import dat_ban as S
    from app.services import hoa_hong_d06 as HH
    from app.models.cong_khach import YeuCauKhach
    ncc, tkn = _ncc(db), _tk(db, "0901000004")
    d = _nhan(db, _dat(db, tk="0901000003", ten_khach="Anh Minh", dien_thoai="0912345678", dong_y_khach=True, nl=10, cach="coc"))
    dk = _nhan(db, _dat(db, nl=2, cach="du"))                       # khách tự đặt — không vào D06
    y = db.get(YeuCauKhach, d.yeu_cau_id)
    with pytest.raises(S.LoiDatBan, match="bàn đã giữ"):
        S.ncc_da_dung(db, tkn, ncc, y.id, 4600000, 2350000, "", now=NAY)
    _tra_qr(db, d, sid="I"); _tra_qr(db, dk, sid="J")
    with pytest.raises(S.LoiDatBan, match="khách không đến"):
        S.ncc_khong_den(db, tkn, ncc, y.id, now=S.gio_an(d))          # chưa quá 30 phút
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(db, tkn, ncc, y.id, 4600000, 2350000, "gọi thêm nước", "bill.pdf", "application/pdf", b"%PDF-1.4 bill\n", now=ve)
    S.ncc_da_dung(db, tkn, ncc, db.get(YeuCauKhach, dk.yeu_cau_id).id, 900000, 0, "", now=ve)
    db.commit()
    assert d.trang_thai == "da_dung" and d.bill_attachment_id is not None
    with pytest.raises(S.LoiDatBan):
        S.kt_chot(db, _u(db, "nvkd"), d.id, 4600000, ve)
    S.kt_chot(db, _u(db, "kt"), d.id, 4600000, ve)
    S.kt_chot(db, _u(db, "kt"), dk.id, 900000, ve)
    with pytest.raises(S.LoiDatBan, match="khóa"):
        S.kt_chot(db, _u(db, "kt"), d.id, 1, ve)
    db.commit()
    ky = f"{max(d.ngay, ve.date()):%Y-%m}"
    ng = HH.nguon_thang(db, ky, ve.date())
    nguon = [x for v in ng["nhom"].values() for x in v]
    assert [x["booking"] for x in nguon] == [d.ma] and nguon[0]["doanh_so"] == 4600000
    assert ng["nhom"].get((d.doi_tac_id, 0))
    # nhà hàng thấy tiền Vietourist thu hộ
    th = {x["ma"]: x for x in S.thu_ho_ncc(db, ncc)}
    assert th[d.ma]["da_thu_ho"] == 2250000 and th[dk.ma]["thuoc_nha_hang"] == int(dk.tam_tinh)


def test_7b_khong_den_doan_giu_50(db):
    from app.services import dat_ban as S
    from app.models.cong_khach import YeuCauKhach
    d = _nhan(db, _dat(db, nl=10, cach="du")); _tra_qr(db, d, sid="K")
    S.ncc_khong_den(db, _tk(db, "0901000004"), _ncc(db), db.get(YeuCauKhach, d.yeu_cau_id).id,
                    now=S.gio_an(d) + dt.timedelta(minutes=40))
    assert d.trang_thai == "khong_den" and d.so_giu == 2250000 and d.so_hoan == 2250000 and d.hoan_tt == "cho_sales"
