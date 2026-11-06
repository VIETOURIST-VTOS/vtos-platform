# -*- coding: utf-8 -*-
"""KS-19o · bốn phép thử đỏ trên main sau 06/11/2026 (Chủ tịch: «sửa cả A, B, C» — sửa mọi phép thử đỏ).

  1. Link thanh toán đoàn: «hết hạn» xét theo NGÀY TIỀN VỀ, không theo lúc robot chạy. Tiền về trong hạn → khớp
     dù robot chạy sau hạn; tiền về sau hạn → «chờ Kế toán».
  2. KS-7 C2: bảng do bản nâng cấp sau đã bỏ (bao_gia_doan) không còn bị coi là «bảng không có mô hình».
  3. V9: bảng phụ bao_gia_thiet_ke khai cột tiền thẳng trong upgrade() để bộ đọc cột tiền thấy.
"""
import datetime as dt

from sqlalchemy import select

from tests.test_tr1d_link_thanh_toan_doan import NOW, _hop_dong, _u, db  # noqa: F401


def _txn_luc(s, so, nd, sid, luc):
    from app.models.payments import BankTransaction
    x = BankTransaction(sepay_id=sid, transaction_date=luc, transfer_type="in", amount=so, content=nd, match_status="chua_khop")
    s.add(x); s.commit()
    return x


def test_ks19o_1_tien_ve_sau_han_thi_cho_ke_toan(db):
    from app.services import payments as P
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    TTD.tao(db, _u(db, "sa"), dot[0].id, gui_email=False, now=NOW)        # đợt 1 hạn 05/11/2026
    x = _txn_luc(db, 76_800_000, "CK TD 000001", "S9", dt.datetime(2026, 11, 7, 10, 0))
    P.match_transaction(db, x); db.commit()
    assert x.match_status == "cho_ke_toan" and "het_han" in x.match_note


def test_ks19o_2_tien_ve_trong_han_robot_chay_tre_van_khop(db):
    from app.models.payments import Receipt
    from app.services import thanh_toan_doan as TTD
    hd, b, dot = _hop_dong(db)
    TTD.tao(db, _u(db, "sa"), dot[0].id, gui_email=False, now=NOW)
    x = _txn_luc(db, 76_800_000, "CK TD 000001", "S8", dt.datetime(2026, 11, 4, 16, 0))
    assert TTD.tu_khop(db, x, now=dt.datetime(2026, 11, 9, 8, 0))       # robot chạy sau hạn 4 ngày
    db.commit()
    assert x.match_status == "da_khop"
    assert db.execute(select(Receipt).where(Receipt.booking_id == b.id)).scalars().one()


def test_ks19o_3_bang_da_bo_khong_tinh_la_bang_tre():
    from tests.test_ks7_bang_khong_co_cua_mo_rong import _bang_do_migration_tao
    assert "bao_gia_doan" not in _bang_do_migration_tao()
    assert "bao_gia_thiet_ke" in _bang_do_migration_tao()


def test_ks19o_4_cot_tien_bang_phu_co_trong_ban_nang_cap():
    from tests.test_v9_cot_tien import cot_tien_trong_moi_ban_nang_cap
    c = cot_tien_trong_moi_ban_nang_cap()
    for cot in ("bien_pt", "he_so_te", "tong_von", "tong_ban", "gia_nl", "gia_te"):
        assert ("bao_gia_thiet_ke", cot) in c, cot
