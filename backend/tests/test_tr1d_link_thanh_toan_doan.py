# -*- coding: utf-8 -*-
"""TR-1d · Link thanh toán tour đoàn riêng (Chủ tịch duyệt bản xem thử 02/11/2026).

  1. Số tiền MÁY lấy: báo giá khách đã chốt → hợp đồng → phần còn thiếu của đợt. Thiếu căn cứ thì không tạo.
  2. Chỉ Sale Admin tạo / hủy; một đợt một link đang mở; hạn link = hạn đợt; công tắc chung tắt thì không tạo.
  3. Khách xem không đăng nhập: chỉ chuyển khoản (QR + chuyển tay), KHÔNG có thẻ.
  4. Tiền về «TD……» đúng số → phiếu thu tự động + link «đã trả» + email kèm hóa đơn PDF.
  5. Lệch số → «chờ Kế toán», không email; Kế toán gán tay xong mà đợt đủ → «đã trả» + email.
  6. Cửa API: Sale Admin đọc được hợp đồng; người khác không tạo được link.
"""
import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 11, 2, 9, 0)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import cong_khach as K
    from app.services import tour_online as TR
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("sa", "sales_admin"), ("kd", "nv_kd"), ("ct", "chutich"), ("kt", "ketoan"), ("dh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, department="", password_hash="x"))
    s.commit()
    monkeypatch.setattr(K, "tai_khoan_qr", lambda _db: SimpleNamespace(bank_name="Vietcombank", account_number="0071000123456",
                                                                       account_name="CONG TY CP VIETOURIST HOLDINGS"))
    gui = []
    monkeypatch.setattr(TR, "GUI_EMAIL", lambda to, tieu, noi, kem: gui.append((to, tieu, noi, kem)))
    s.gui = gui
    TR.bat_tt_chung(s, _u(s, "ct"), True, NOW)
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _hop_dong(s, chot=True, noi_booking=True, gia_tri=256_000_000):
    from app.models.ban_hang import BaoGia, HopDongKhach, LichThanhToanHD
    from app.models.core import Booking, Product, Tour
    p = Product(code="DN001", name="ĐÀ NẴNG – HỘI AN", tour_type="doan_noi_dia", days=4, length_text="4N3Đ", status="active")
    s.add(p); s.flush()
    t = Tour(code="DN001.121226", name="Đoàn Đà Nẵng – Hội An 4N3Đ", tour_type="doan_noi_dia", start_date=dt.date(2026, 12, 12),
             end_date=dt.date(2026, 12, 15), operator_id=_u(s, "dh").id, status="da_duyet", product_id=p.id, product_code=p.code)
    s.add(t); s.flush()
    b = Booking(code="BK26110201", tour_id=t.id, request_id=0, sales_id=_u(s, "kd").id, created_by=_u(s, "kd").id,
                customer_name="Công ty ABC", customer_phone="0905111222", source="doan", pax=32, amount=gia_tri,
                customer_email="ketoan@abc.vn")
    s.add(b); s.flush()
    bg = BaoGia(ma="BG-0918", mang="kd_doan", khach_ten="Công ty ABC", khach_email="ketoan@abc.vn",
                khach_dien_thoai="0905111222", trang_thai="khach_chot" if chot else "da_gui")
    s.add(bg); s.flush()
    hd = HopDongKhach(so_hop_dong="HĐK-0412", bao_gia_id=bg.id, booking_id=b.id if noi_booking else None, khach_ten="Công ty ABC",
                      gia_tri=gia_tri, trang_thai="da_ky", ngay_ky=dt.date(2026, 11, 1))
    s.add(hd); s.flush()
    dot = []
    for i, (ten, tien, han) in enumerate((("Đặt cọc 30%", 76_800_000, dt.date(2026, 11, 5)),
                                          ("50%", 128_000_000, dt.date(2026, 11, 20)),
                                          ("Còn lại 20%", 51_200_000, dt.date(2026, 12, 5))), 1):
        d = LichThanhToanHD(hop_dong_id=hd.id, dot=i, ten=ten, so_tien=tien, moc="co_dinh", han=han, han_goc=han)
        s.add(d); dot.append(d)
    s.commit()
    return hd, b, dot


def _txn(s, so, nd, sid):
    from app.models.payments import BankTransaction
    x = BankTransaction(sepay_id=sid, transaction_date=NOW, transfer_type="in", amount=so, content=nd, match_status="chua_khop")
    s.add(x); s.commit()
    return x


def test_luat_1_so_tien_tu_bao_gia_chot_va_dot(db):
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    l = TTD.tao(db, _u(db, "sa"), dot[0].id, now=NOW)
    assert l["ma"] == "TD000001" and l["so_tien"] == 76_800_000 and l["han"] == "2026-11-05"
    assert l["link"].endswith("/thanh-toan/TD000001") and l["email"] == "ketoan@abc.vn" and l["trang_thai"] == "mo"
    assert len(db.gui) == 1 and "TD000001" in db.gui[0][2] and db.gui[0][3] == []          # email link, không đính kèm


def test_luat_1b_thieu_can_cu_thi_khong_tao(db):
    from app.models.ban_hang import LichThanhToanHD
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db, chot=False)
    with pytest.raises(TTD.LoiTTD, match="khách đã chốt"):
        TTD.tao(db, _u(db, "sa"), dot[0].id, now=NOW)
    from app.models.ban_hang import BaoGia
    db.get(BaoGia, hd.bao_gia_id).trang_thai = "khach_chot"
    hd.booking_id = None; db.commit()
    with pytest.raises(TTD.LoiTTD, match="nối booking"):
        TTD.tao(db, _u(db, "sa"), dot[0].id, now=NOW)
    hd.booking_id = b.id; dot[0].so_tien = None; db.commit()
    with pytest.raises(TTD.LoiTTD, match="chưa có số tiền"):
        TTD.tao(db, _u(db, "sa"), dot[0].id, now=NOW)
    with pytest.raises(TTD.LoiTTD, match="hạn đã qua"):
        TTD.tao(db, _u(db, "sa"), dot[1].id, now=dt.datetime(2026, 11, 21, 8, 0))
    assert db.execute(select(LichThanhToanHD)).scalars().first() is not None


def test_luat_2_quyen_mot_link_mot_dot_va_cong_tac(db):
    from app.services import thanh_toan_doan as TTD
    from app.services import tour_online as TR
    hd, b, dot = _hop_dong(db)
    for ai in ("kd", "ct", "kt"):
        with pytest.raises(TTD.LoiTTD) as e:
            TTD.tao(db, _u(db, ai), dot[1].id, now=NOW)
        assert e.value.status == 403
    l = TTD.tao(db, _u(db, "sa"), dot[1].id, gui_email=False, now=NOW)
    with pytest.raises(TTD.LoiTTD, match="hủy link cũ"):
        TTD.tao(db, _u(db, "sa"), dot[1].id, now=NOW)
    with pytest.raises(TTD.LoiTTD, match="lý do"):
        TTD.huy(db, _u(db, "sa"), l["ma"], "")
    assert TTD.huy(db, _u(db, "sa"), l["ma"], "Khách xin đổi đợt", NOW)["trang_thai"] == "huy"
    l2 = TTD.tao(db, _u(db, "sa"), dot[1].id, gui_email=False, now=NOW)
    assert l2["ma"] == "TD000002"
    assert TTD.trang_thai(TTD._link(db, l2["ma"]), dt.date(2026, 11, 21)) == "het_han"          # hạn link = hạn đợt
    TR.bat_tt_chung(db, _u(db, "ct"), False, NOW)
    with pytest.raises(TTD.LoiTTD, match="Công tắc"):
        TTD.tao(db, _u(db, "sa"), dot[2].id, now=NOW)


def test_luat_3_khach_xem_chi_chuyen_khoan(db):
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    l = TTD.tao(db, _u(db, "sa"), dot[0].id, gui_email=False, now=NOW)
    o = TTD.xem_cong(db, l["ma"].lower(), NOW.date())
    ck = o["chuyen_khoan"]
    assert o["trang_thai"] == "mo" and o["so_tien"] == 76_800_000 and o["so_dot"] == 3 and o["khach"] == "Công ty ABC"
    assert ck["so_tien"] == 76_800_000 and ck["noi_dung"] == "TD000001" and ck["payload"].startswith("000201")
    assert "the" not in o and "Visa" not in str(o)                                          # tour đoàn không có thẻ
    with pytest.raises(TTD.LoiTTD) as e:
        TTD.tai_hoa_don(db, l["ma"])
    assert e.value.status == 409
    with pytest.raises(TTD.LoiTTD) as e:
        TTD.xem_cong(db, "TD999999")
    assert e.value.status == 404


def test_luat_4_tien_ve_dung_so_phieu_thu_va_email_hoa_don(db):
    from app.models.payments import Receipt
    from app.services import payments as P
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    l = TTD.tao(db, _u(db, "sa"), dot[0].id, gui_email=False, now=NOW)
    x = _txn(db, 76_800_000, "CONG TY ABC CK TD 000001 dot 1", "S1")
    P.match_transaction(db, x); db.commit()
    r = db.execute(select(Receipt).where(Receipt.booking_id == b.id)).scalars().one()
    assert int(r.amount) == 76_800_000 and r.status == "tu_dong" and x.match_status == "da_khop"
    ll = TTD._link(db, l["ma"])
    assert ll.trang_thai == "da_tra" and ll.receipt_id == r.id
    assert len(db.gui) == 1 and db.gui[0][0] == "ketoan@abc.vn" and db.gui[0][3][0][2] == "application/pdf"
    assert db.gui[0][3][0][1][:5] == b"%PDF-" and TTD.tai_hoa_don(db, l["ma"])[:5] == b"%PDF-"
    assert TTD.xem_cong(db, l["ma"], NOW.date())["chuyen_khoan"] is None                     # đã trả: không hiện QR nữa
    with pytest.raises(TTD.LoiTTD, match="đã thu đủ"):
        TTD.tao(db, _u(db, "sa"), dot[0].id, now=NOW)


def test_luat_5_lech_so_cho_ke_toan_roi_gan_tay(db):
    from app.services import payments as P
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    l = TTD.tao(db, _u(db, "sa"), dot[0].id, gui_email=False, now=NOW)
    x = _txn(db, 70_000_000, "TD000001", "S2")
    P.match_transaction(db, x); db.commit()
    assert x.match_status == "cho_ke_toan" and x.booking_id == b.id and "TD000001" in x.match_note
    assert TTD._link(db, l["ma"]).trang_thai == "mo" and db.gui == []
    P.accountant_assign(db, _u(db, "kt"), x, b, "Khách chuyển thiếu")
    assert TTD._link(db, l["ma"]).trang_thai == "mo" and db.gui == []                         # đợt chưa đủ
    y = _txn(db, 6_800_000, "ABC chuyen bu", "S3")
    P.match_transaction(db, y); db.commit()
    P.accountant_assign(db, _u(db, "kt"), y, b, "Phần bù")
    assert TTD._link(db, l["ma"]).trang_thai == "da_tra" and len(db.gui) == 1                 # đợt đủ → đã trả + email


def test_luat_6_cua_api():
    import inspect
    from app.api.v1 import ban_hang as API
    src = inspect.getsource(API)
    assert 'XEM_HD = XEM + ("sales_admin",)' in src
    for ham in ("tao_link_tt", "huy_link_tt", "gui_lai_link_tt"):
        assert 'require_roles("sales_admin"' in inspect.getsource(getattr(API, ham))
    from app.api.v1 import cong_mo as MO
    assert all("GET" in (r.methods or set()) for r in MO.router.routes if "/tt-doan" in r.path)
