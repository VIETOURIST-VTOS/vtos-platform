# -*- coding: utf-8 -*-
"""KS-16l · Khách sạn lên cổng khi đủ hồ sơ + ảnh + giới thiệu, chưa cần loại phòng đang bán (Chủ tịch 01/11/2026).
Chưa có gói đặt được thì chưa book trên cổng — thẻ mang dat_ngay=False và link_ngoai (www.vietourist.vn/hotel)."""
import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _anh, _ks, _mo_ban


def test_bat_loat_va_link_ngoai(db):
    from app.services import khach_san_vtd as S
    a = _ks(db, "Khách sạn Không Phòng")
    x, _ = S.tai_anh(db, _u(db, "dh"), a.id, "a.jpg", _anh(), {"nhom": "mat_tien"})
    S.gui_duyet_anh(db, _u(db, "dh"), [x.id]); S.duyet_anh(db, _u(db, "tp"), [x.id], True)
    b = _ks(db, "Khách sạn Có Phòng")
    _mo_ban(db, b)                                         # đã bật hiện, có gói đặt được
    c = _ks(db, "Khách sạn Chưa Ảnh")
    assert all(d["ok"] for d in S.dieu_kien_hien(db, a))   # không còn điều kiện «loại phòng đang bán»
    with pytest.raises(S.LoiKhachSan):
        S.bat_hien_loat(db, _u(db, "dh"))                  # NV Điều hành không bật
    r = S.bat_hien_loat(db, _u(db, "tp"))
    assert r["bat"] == [a.ma] and c.ma not in r["bat"]
    from sqlalchemy import select
    from app.models.core import AuditLog
    nk = db.execute(select(AuditLog).where(AuditLog.action == "ks_vtd_bat_loat")).scalars().one()
    assert len(nk.entity) <= 60                         # cột entity String(60) — Postgres không cho dài hơn
    the = {k["ten"]: k for k in S.tim(db, "", VAO, RA, 2, 0, 1, HN)["khach_san"]}
    assert "Khách sạn Không Phòng" not in the            # KS-19 (Chủ tịch 05/11/2026): không đặt được thì không hiện
    assert the["Khách sạn Có Phòng"]["dat_ngay"] is True
    assert "Khách sạn Chưa Ảnh" not in the
