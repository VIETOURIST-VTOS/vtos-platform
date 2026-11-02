# -*- coding: utf-8 -*-
"""NCC-1 · Cổng Nhà cung cấp (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Cửa vào: chỉ tài khoản NCC đã duyệt VÀ đã nối; gợi ý nối theo MST; chỉ TP ĐH / GĐ KD / CT / TGĐ nối.
  2. Đơn: chỉ đơn CỦA MÌNH, không nháp; xác nhận đổi NGAY sang «NCC đã xác nhận» kèm mã; từ chối cần lý do,
     đơn giữ nguyên.
  3. Giá: NCC chỉ đề xuất; TP ĐH duyệt mới áp dụng, dòng cũ hết hiệu lực; nhà hàng: duyệt ghi vào thực đơn.
  4. Công nợ: đơn đã xác nhận / đã dùng trừ đơn có phiếu chi «đã chi»; chiều NCC trả = None.
  5. Bản kê: chỉ Kế toán lập; NCC báo chênh lệch → chưa xác nhận được tới khi Kế toán trả lời; xác nhận thì khóa.
  6. Đề nghị: đi đúng bộ phận; người khác bộ phận không xử lý được.
  7. Đổi tài khoản: tạo yêu cầu hai người, số TK đang dùng KHÔNG đổi; thiếu văn bản bị chặn.
  8. Nhà hàng: chỉ đơn đặt bàn của nhà hàng mình; từ chối cần lý do; học liệu theo nhóm đối tác.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

PDF = b"%PDF-1.4 hop dong\n"


class _Kho:
    def __init__(self): self.d = {}
    def put(self, key, data, kieu=""):
        self.d[key] = data
        return type("L", (), {"key": key, "checksum": __import__("hashlib").sha256(data).hexdigest()})()
    def get(self, key): return self.d[key]


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import Tour, User
    from app.models.suppliers import ServiceOrder, Supplier
    from app.models.ops import PaymentRequest
    from app.services import storage as ST
    ST._CACHE["s"] = _Kho()
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("tpdh", "tp_dh"), ("nvdh", "nv_dh"), ("kt", "ketoan"), ("bks", "bks"), ("mkt", "nv_mkt")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.flush()
    op = s.execute(select(User).where(User.username == "nvdh")).scalars().one()
    t = Tour(code="PQ1120", name="Phú Quốc", tour_type="le", start_date=dt.date(2026, 11, 20), end_date=dt.date(2026, 11, 22), operator_id=op.id)
    s.add(t); s.flush()
    a = Supplier(code="NCC0017", ten="Resort Biển Xanh", loai="khach_san", ma_so_thue="0312345678", so_tai_khoan="0011001234",
                 ngan_hang="VCB", chu_tai_khoan="CTY BIEN XANH")
    b = Supplier(code="NCC0018", ten="Khách sạn Khác", loai="khach_san", ma_so_thue="0399999999")
    s.add_all([a, b]); s.flush()
    pr = PaymentRequest(code="DC-TEST-0451", category="chi_tour", tour_id=t.id, supplier_name=a.ten, amount=9000000,
                        description="x", status="da_chi", created_by="kt")
    s.add(pr); s.flush()
    for code, sup, st, tt, ngay, prid in (("DV-1", a.id, "da_gui", 14400000, dt.date(2026, 11, 20), None),
                                           ("DV-2", a.id, "da_xac_nhan", 9000000, dt.date(2026, 10, 28), pr.id),
                                           ("DV-3", a.id, "da_su_dung", 116000000, dt.date(2026, 10, 10), None),
                                           ("DV-4", a.id, "nhap", 1000, dt.date(2026, 11, 1), None),
                                           ("DV-5", b.id, "da_gui", 5000, dt.date(2026, 11, 1), None)):
        s.add(ServiceOrder(code=code, supplier_id=sup, tour_id=t.id, noi_dung=f"Dịch vụ {code}", ngay_su_dung=ngay,
                           thanh_tien=tt, status=st, payment_request_id=prid))
    s.commit()
    yield s
    s.close(); ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _ncc(s, code="NCC0017"):
    from app.models.suppliers import Supplier
    return s.execute(select(Supplier).where(Supplier.code == code)).scalars().one()


def _tk(s, mst="0312345678", tt="hoat_dong", loai_dt="ncc", sdt="0901234567", noi=True):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai="doi_tac", loai_doi_tac=loai_dt, dien_thoai=sdt, trang_thai=tt, ma_so_thue=mst, ho_ten="Lan")
    s.add(tk); s.commit()
    if noi:
        from app.services import cong_ncc as S
        S.noi(s, _u(s, "tpdh"), tk.id, _ncc(s).id); s.commit()
    return tk


def _don(s, code):
    from app.models.suppliers import ServiceOrder
    return s.execute(select(ServiceOrder).where(ServiceOrder.code == code)).scalars().one()


def test_cua_vao_va_noi(db):
    from app.services import cong_ncc as S
    tk = _tk(db, noi=False)
    with pytest.raises(S.LoiNcc) as ex:
        S.ncc_cua(db, tk)
    assert ex.value.status == 409
    assert [x["code"] for x in S.goi_y(db, tk)["khop"]] == ["NCC0017"]
    for ai in ("nvdh", "kt", "bks"):
        with pytest.raises(S.LoiNcc) as ex:
            S.noi(db, _u(db, ai), tk.id, _ncc(db).id)
        assert ex.value.status == 403
    S.noi(db, _u(db, "tpdh"), tk.id, _ncc(db).id); db.commit()
    assert S.ncc_cua(db, tk).code == "NCC0017"
    for loai_dt, tt in (("dai_ly", "hoat_dong"), ("ncc", "cho_duyet")):
        x = _tk(db, loai_dt=loai_dt, tt=tt, sdt="0902", noi=False); x.ncc_id = _ncc(db).id; db.commit()
        with pytest.raises(S.LoiNcc) as ex:
            S.ncc_cua(db, x)
        assert ex.value.status == 403


def test_don_chi_cua_minh_xac_nhan_va_tu_choi(db):
    from app.services import cong_ncc as S
    tk = _tk(db); s = _ncc(db)
    assert sorted(d["code"] for d in S.ds_don(db, s)) == ["DV-1", "DV-2", "DV-3"]     # không nháp, không đơn NCC khác
    with pytest.raises(S.LoiNcc) as ex:
        S.mot_don(db, s, _don(db, "DV-5").id)
    assert ex.value.status == 404
    with pytest.raises(S.LoiNcc, match="lý do"):
        S.phan_hoi_don(db, tk, s, _don(db, "DV-1").id, "tu_choi")
    r = S.phan_hoi_don(db, tk, s, _don(db, "DV-1").id, "tu_choi", ghi_chu="Hết phòng ngày 20/11"); db.commit()
    assert _don(db, "DV-1").status == "da_gui" and "từ chối" in r["status_ten"]
    assert S.don_bi_tu_choi(db)[0]["ly_do"] == "Hết phòng ngày 20/11"
    with pytest.raises(S.LoiNcc, match="mã"):
        S.phan_hoi_don(db, tk, s, _don(db, "DV-1").id, "xac_nhan")
    S.phan_hoi_don(db, tk, s, _don(db, "DV-1").id, "xac_nhan", ma="BX-77821"); db.commit()
    d = _don(db, "DV-1")
    assert d.status == "da_xac_nhan" and "BX-77821" in d.xac_nhan_ncc
    with pytest.raises(S.LoiNcc) as ex:
        S.phan_hoi_don(db, tk, s, d.id, "xac_nhan", ma="X")
    assert ex.value.status == 409
    S.phan_hoi_don(db, tk, s, d.id, "chung_tu", ten_tep="xn.pdf", kieu="application/pdf", data=PDF); db.commit()
    assert any(p["co_tep"] for p in S.mot_don(db, s, d.id)["phan_hoi"])


def test_gia_de_xuat_va_duyet(db):
    from app.services import cong_ncc as S
    tk = _tk(db); s = _ncc(db)
    x = S.de_xuat(db, tk, s, {"dich_vu": "Phòng Deluxe", "don_vi": "đêm", "gia": 1200000, "so_luong_mo": 10,
                              "tu_ngay": "2026-11-01", "den_ngay": "2026-12-31"}); db.commit()
    assert S.gia_dang_ap_dung(db, s) == []                                        # chưa duyệt thì chưa áp dụng
    with pytest.raises(S.LoiNcc) as ex:
        S.xu_ly_de_xuat(db, _u(db, "nvdh"), x.id, True)
    assert ex.value.status == 403
    S.xu_ly_de_xuat(db, _u(db, "tpdh"), x.id, True); db.commit()
    g = S.gia_dang_ap_dung(db, s)
    assert len(g) == 1 and g[0]["gia"] == 1200000
    x2 = S.de_xuat(db, tk, s, {"gia_ncc_id": g[0]["id"], "gia": 1250000, "tu_ngay": "2027-01-01"}); db.commit()
    with pytest.raises(S.LoiNcc, match="lý do"):
        S.xu_ly_de_xuat(db, _u(db, "tpdh"), x2.id, False)
    S.xu_ly_de_xuat(db, _u(db, "tpdh"), x2.id, True); db.commit()
    g2 = S.gia_dang_ap_dung(db, s)
    assert len(g2) == 1 and g2[0]["gia"] == 1250000                               # dòng cũ hết hiệu lực
    with pytest.raises(S.LoiNcc):
        S.de_xuat(db, tk, s, {"dich_vu": "X", "gia": 0})


def test_cong_no_hai_chieu(db):
    from app.services import cong_ncc as S
    s = _ncc(db)
    cn = S.cong_no(db, s)
    assert cn["vtd_phai_tra"] == 116000000                                        # DV-2 đã chi, DV-1 chưa xác nhận, DV-4 nháp
    assert cn["ncc_phai_tra"] is None
    assert {d["code"]: d["da_chi"] for d in cn["dong"]} == {"DV-2": True, "DV-3": False}


def test_ban_ke_chenh_lech_va_khoa(db):
    from app.services import cong_ncc as S
    tk = _tk(db); s = _ncc(db)
    with pytest.raises(S.LoiNcc) as ex:
        S.lap_ban_ke(db, _u(db, "tpdh"), s.id, "2026-10")
    assert ex.value.status == 403
    b = S.lap_ban_ke(db, _u(db, "kt"), s.id, "2026-10"); db.commit()
    assert b.tong == 125000000
    with pytest.raises(S.LoiNcc) as ex:
        S.lap_ban_ke(db, _u(db, "kt"), s.id, "2026-10")
    assert ex.value.status == 409
    dong = S.ds_ban_ke_cua(db, s)[0]["dong"]
    S.bao_chenh_lech(db, tk, s, b.id, dong[0]["id"], 120000000, "Thiếu 1 đêm"); db.commit()
    with pytest.raises(S.LoiNcc, match="chờ Kế toán"):
        S.xac_nhan_ban_ke(db, tk, s, b.id)
    S.tra_loi_chenh_lech(db, _u(db, "kt"), dong[0]["id"], "Đã đối chiếu: đoàn trả phòng sớm 1 đêm"); db.commit()
    S.xac_nhan_ban_ke(db, tk, s, b.id); db.commit()
    assert S.ds_ban_ke_cua(db, s)[0]["trang_thai"] == "da_xac_nhan"
    with pytest.raises(S.LoiNcc, match="khóa"):
        S.bao_chenh_lech(db, tk, s, b.id, dong[0]["id"], 1, "x")
    with pytest.raises(S.LoiNcc) as ex:
        S.xac_nhan_ban_ke(db, tk, _ncc(db, "NCC0018"), b.id)                      # NCC khác không đụng được
    assert ex.value.status == 404


def test_de_nghi_dung_bo_phan(db):
    from app.services import cong_ncc as S
    tk = _tk(db); s = _ncc(db)
    x = S.gui_de_nghi(db, tk, s, "thanh_toan", 116000000, "Đề nghị thanh toán DV-3"); db.commit()
    assert x.bo_phan == "ketoan" and x.ma == "DN-NCC-0001"
    with pytest.raises(S.LoiNcc) as ex:
        S.xu_ly_de_nghi(db, _u(db, "tpdh"), x.id, "xong", "ok")
    assert ex.value.status == 403
    with pytest.raises(S.LoiNcc, match="trả lời"):
        S.xu_ly_de_nghi(db, _u(db, "kt"), x.id, "dang_xu_ly", "")
    S.xu_ly_de_nghi(db, _u(db, "kt"), x.id, "dang_xu_ly", "Đã lập DC-TEST-0012, chờ TGĐ duyệt"); db.commit()
    assert S.ds_de_nghi_cua(db, s)[0]["tra_loi"].startswith("Đã lập")
    y = S.gui_de_nghi(db, tk, s, "dieu_chinh", None, "Đổi loại phòng đoàn PQ1120"); db.commit()
    S.xu_ly_de_nghi(db, _u(db, "nvdh"), y.id, "xong", "Đã đổi"); db.commit()


def test_doi_tai_khoan_hai_nguoi(db):
    from app.services import cong_ncc as S
    from app.models.suppliers import SupplierBankChange
    tk = _tk(db); s = _ncc(db)
    with pytest.raises(S.LoiNcc, match="văn bản"):
        S.doi_tai_khoan(db, tk, s, "999888777", "ACB", "CTY", "đổi", "", "", None)
    S.doi_tai_khoan(db, tk, s, "999888777", "ACB", "CTY BIEN XANH", "đổi NH", "vb.pdf", "application/pdf", PDF); db.commit()
    assert s.so_tai_khoan == "0011001234"                                          # chưa xác nhận: KHÔNG đổi
    c = db.execute(select(SupplierBankChange)).scalars().one()
    assert c.status == "cho_xac_nhan" and c.de_nghi_boi.startswith("cong:ncc-")
    assert S.ngan_hang(db, s)["dang_cho_doi"] is True and S.ngan_hang(db, s)["so_tai_khoan"].endswith("1234")


def test_nha_hang_va_hoc_lieu(db):
    from app.services import cong_ncc as S
    from app.models.nha_hang import NhaHang, ThucDonNhaHang
    from app.models.cong_khach import YeuCauKhach
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = _tk(db); s = _ncc(db)
    n = NhaHang(ma="NH01", ten="Bếp Việt"); khac = NhaHang(ma="NH02", ten="Quán khác")
    db.add_all([n, khac]); db.flush()
    td = ThucDonNhaHang(nha_hang_id=n.id, ten="Set Hương Việt", gia_nguoi_lon=350000, gia_tre_em=175000)
    db.add(td); db.flush()
    kh = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0911", trang_thai="hoat_dong"); db.add(kh); db.flush()
    y1 = YeuCauKhach(tai_khoan_id=kh.id, loai="nha_hang", nha_hang_id=n.id, thuc_don_id=td.id, so_khach=8, tre_em=2,
                     ngay_mong_muon=dt.date(2026, 11, 15), gio_den="18:30", dien_thoai="0911000000")
    y2 = YeuCauKhach(tai_khoan_id=kh.id, loai="nha_hang", nha_hang_id=khac.id, so_khach=2, dien_thoai="0911000000")
    db.add_all([y1, y2]); db.commit()
    assert S.don_dat_ban(db, s) == []                                             # chưa gắn nhà hàng
    S.gan_nha_hang(db, _u(db, "tpdh"), n.id, s.id); db.commit()
    ds = S.don_dat_ban(db, s)
    assert [x["id"] for x in ds] == [y1.id] and ds[0]["nguoi_lon"] == 6 and "dien_thoai" not in ds[0]
    with pytest.raises(S.LoiNcc, match="lý do"):
        S.xu_ly_dat_ban(db, tk, s, y1.id, False, "")
    with pytest.raises(S.LoiNcc) as ex:
        S.xu_ly_dat_ban(db, tk, s, y2.id, True, "")
    assert ex.value.status == 404
    S.xu_ly_dat_ban(db, tk, s, y1.id, True, ""); db.commit()
    assert db.get(YeuCauKhach, y1.id).nha_hang_tt == "nhan"
    x = S.de_xuat(db, tk, s, {"loai": "thuc_don", "thuc_don_id": td.id, "gia": 380000, "gia_tre_em": 190000}); db.commit()
    S.xu_ly_de_xuat(db, _u(db, "tpdh"), x.id, True); db.commit()
    assert db.get(ThucDonNhaHang, td.id).gia_nguoi_lon == 380000
    with pytest.raises(S.LoiNcc) as ex:
        S.dang_hoc_lieu(db, _u(db, "kt"), "Quy trình", "quy_trinh", ["ncc"], "a.pdf", "application/pdf", PDF)
    assert ex.value.status == 403
    S.dang_hoc_lieu(db, _u(db, "mkt"), "Quy trình phục vụ đoàn", "quy_trinh", ["ncc"], "a.pdf", "application/pdf", PDF)
    S.dang_hoc_lieu(db, _u(db, "mkt"), "Bộ bán tour", "san_pham", ["dai_ly"], "b.pdf", "application/pdf", PDF + b"2"); db.commit()
    hl = S.hoc_lieu_cho(db, "ncc")
    assert [h["tieu_de"] for h in hl] == ["Quy trình phục vụ đoàn"]
    with pytest.raises(S.LoiNcc):
        S.tep_hoc_lieu(db, S.hoc_lieu_cho(db, "dai_ly")[0]["id"], "ncc")
