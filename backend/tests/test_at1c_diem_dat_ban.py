# -*- coding: utf-8 -*-
"""AT-1c · Đặt bàn qua Vietourist được tích điểm như tour (Chủ tịch chốt 28/10/2026).

  1. Đơn khách / cổ đông tự đặt, nhà hàng báo đã dùng, Kế toán chốt → cộng floor(B/10.000 × hệ số hạng);
     B = tiền đã trả qua Vietourist (cọc hoặc trả đủ) trừ phần đã hoàn. Chưa chốt thì chưa cộng.
  2. Đơn đại lý / CTV đặt hộ không cộng. Chạy lại không ghi thêm. Chi tiêu đặt bàn vào hạng.
"""
import datetime as dt

from sqlalchemy import select

from tests.test_dt2_dat_ban import NAY, _dat, _ncc, _nhan, _tk, _tra_qr, _u, db  # noqa: F401


def _dung_chot(s, d, bill):
    from app.services import dat_ban as S
    from app.models.cong_khach import YeuCauKhach
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(s, _tk(s, "0901000004"), _ncc(s), s.get(YeuCauKhach, d.yeu_cau_id).id, bill, 0, "", now=ve)
    s.commit()
    return ve


def test_diem_dat_ban(db, monkeypatch):
    from app.services import dat_ban as S, rewards as RW
    from app.models.rewards import SoDiem
    monkeypatch.setattr(RW, "hieu_luc_tu", lambda s: dt.date(2026, 1, 1))
    d = _nhan(db, _dat(db, nl=4, cach="du")); _tra_qr(db, d, sid="P1")            # 1.800.000 đ qua Vietourist
    dc = _nhan(db, _dat(db, nl=2, cach="coc")); _tra_qr(db, dc, sid="P2")          # cọc 90.000 đ
    dl = _nhan(db, _dat(db, tk="0901000003", ten_khach="Minh", dien_thoai="0901000001", dong_y_khach=True, nl=4, cach="du"))
    _tra_qr(db, dl, sid="P3")                                                        # đại lý đặt hộ — không cộng
    chu = "sdt:0901000001"
    ve = _dung_chot(db, d, 2_000_000); _dung_chot(db, dc, 900_000); _dung_chot(db, dl, 1_800_000)
    hn = ve.date() + dt.timedelta(days=1)
    RW.tinh(db, chu, hn)
    assert db.execute(select(SoDiem).where(SoDiem.chu == chu)).scalars().all() == []    # chưa chốt → chưa cộng
    for x in (d, dc, dl):
        S.kt_chot(db, _u(db, "kt"), x.id, 1_000_000, ve)
    db.commit()
    RW.tinh(db, chu, hn)
    dong = {r.dat_ban_id: r.so_diem for r in db.execute(select(SoDiem).where(SoDiem.chu == chu)).scalars()}
    assert dong == {d.id: 180, dc.id: 9}                                             # 1.800.000/10.000; 90.000/10.000
    RW.tinh(db, "sdt:0901000003", hn)                                                # tài khoản đại lý: không có điểm
    assert db.execute(select(SoDiem).where(SoDiem.chu == "sdt:0901000003")).scalars().all() == []
    RW.tinh(db, chu, hn)
    assert len(db.execute(select(SoDiem).where(SoDiem.chu == chu)).scalars().all()) == 2   # chạy lại không ghi
    assert RW.hang(db, chu, hn)["chi_tieu_12_thang"] == 1_890_000
    # hoàn một phần sau khi đã cộng → dòng trừ
    d.da_hoan_tien = 450_000; db.commit()
    RW.tinh(db, chu, hn)
    assert sum(r.so_diem for r in db.execute(select(SoDiem).where(SoDiem.chu == chu, SoDiem.dat_ban_id == d.id)).scalars()) == 135
    assert RW.tong_quan(db, [chu], hn)["kha_dung"] == 144
