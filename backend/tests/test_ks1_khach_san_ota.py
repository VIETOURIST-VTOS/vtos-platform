# -*- coding: utf-8 -*-
"""KS-1 · Khách sạn qua OTA (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Bật OTA chỉ khi đủ bốn điều; chỉ Chủ tịch sửa / bật; đổi link = phiên bản mới, tự tắt.
  2. Link phải https, đúng tên miền / đường dẫn đã khai; chặn userinfo, cổng, #, host giả.
  3. Chuyển khách: OTA tắt thì không có link; bấm lặp cùng request_id = cùng lượt; khác OTA = 409;
     link đổi phiên bản thì lượt cũ không phát lại link cũ; trình duyệt không gửi được link.
  4. Ba cổng dùng được; tài khoản chưa duyệt / bị khoá thì không.
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 10, 28, 9, 0)
LINK = "https://expedia.com/affiliate/MMxo9Me"


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.models.khach_san_ota import PhapNhanHopDong, DoiTacOta
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("tgd", "tgd"), ("cntt", "cntt")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.add(PhapNhanHopDong(id=1, ma="INFINIS_CA", ten="THE INFINIS PATHWAY INC.", quoc_gia="Canada"))
    for i, (m, t) in enumerate((("expedia", "Expedia"), ("booking_com", "Booking.com"))):
        s.add(DoiTacOta(ma=m, ten=t, phap_nhan_id=1, thu_tu=i))
    s.commit()
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _ota(s, ma="expedia"):
    from app.models.khach_san_ota import DoiTacOta
    return s.execute(select(DoiTacOta).where(DoiTacOta.ma == ma)).scalars().one()


def _mo(s, ma="expedia", link=LINK, mien="expedia.com"):
    from app.services import khach_san_ota as S
    o = _ota(s, ma)
    S.sua(s, _u(s, "ct"), o.id, {"trang_thai": "da_duyet", "link": link, "ten_mien": mien, "da_kiem_link": True, "duoc_dung_web": True})
    return S.bat_tat(s, _u(s, "ct"), o.id, True)


def _tk(s, loai="khach_hang", trang_thai="hoat_dong"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai=loai, dien_thoai="0901234567", trang_thai=trang_thai)
    s.add(tk); s.commit()
    return tk


# ── 1 · BỐN ĐIỀU KIỆN, CHỈ CHỦ TỊCH ─────────────────────────────────────────────────────────

def test_bat_chi_khi_du_bon_dieu_va_chi_chu_tich(db):
    from app.services import khach_san_ota as S
    o = _ota(db)
    with pytest.raises(S.LoiOta) as ex:
        S.bat_tat(db, _u(db, "ct"), o.id, True)
    assert "hợp tác chưa được duyệt" in str(ex.value) and "chưa kiểm link" in str(ex.value)
    for ai in ("tgd", "cntt"):
        with pytest.raises(S.LoiOta) as ex:
            S.sua(db, _u(db, ai), o.id, {"trang_thai": "da_duyet"})
        assert ex.value.status == 403
    S.sua(db, _u(db, "ct"), o.id, {"trang_thai": "da_duyet", "link": LINK, "ten_mien": "expedia.com", "da_kiem_link": True})
    with pytest.raises(S.LoiOta):                                        # thiếu «được dùng trên web»
        S.bat_tat(db, _u(db, "ct"), o.id, True)
    S.sua(db, _u(db, "ct"), o.id, {"duoc_dung_web": True})
    assert S.bat_tat(db, _u(db, "ct"), o.id, True).bat is True


def test_doi_link_la_phien_ban_moi_tu_tat(db):
    from app.services import khach_san_ota as S
    o = _mo(db)
    pb = o.phien_ban
    o = S.sua(db, _u(db, "ct"), o.id, {"link": "https://expedia.com/affiliate/KHAC"})
    assert o.phien_ban == pb + 1 and o.bat is False and o.da_kiem_link is False
    o = S.sua(db, _u(db, "ct"), o.id, {"da_kiem_link": True})
    assert o.bat is False                                                 # không tự bật lại
    o2 = _mo(db)                                                          # mất điều kiện → tự tắt
    o2 = S.sua(db, _u(db, "ct"), o2.id, {"trang_thai": "tam_dung"})
    assert o2.bat is False


# ── 2 · LINK AN TOÀN ─────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("link", ["http://expedia.com/affiliate/x", "https://expedia.com.evil.test/affiliate/x",
                                  "https://expedia.com@evil.test/affiliate/x", "https://expedia.com:8443/affiliate/x",
                                  "https://expedia.com/affiliate/x#a", "javascript:alert(1)", "https://expedia.com\\@evil.test/x",
                                  "https://expedia.com/khac/x", "https://user@expedia.com/affiliate/x"])
def test_link_khong_an_toan_bi_chan(link):
    from app.services import khach_san_ota as S
    assert S.loi_link(link, "expedia.com", "/affiliate/") != ""


def test_link_dung_qua(db):
    from app.services import khach_san_ota as S
    assert S.loi_link(LINK, "expedia.com", "/affiliate/") == ""
    with pytest.raises(S.LoiOta):
        S.sua(db, _u(db, "ct"), _ota(db).id, {"link": "https://evil.test/a", "ten_mien": "expedia.com"})


# ── 3 · CHUYỂN KHÁCH ─────────────────────────────────────────────────────────────────────────

def test_chuyen_khach_mot_luot_mot_request(db):
    from app.services import khach_san_ota as S
    from app.models.khach_san_ota import LuotChuyenOta
    tk = _tk(db)
    rid = str(uuid.uuid4())
    with pytest.raises(S.LoiOta) as ex:                                   # OTA còn tắt
        S.chuyen(db, tk, "expedia", rid, {}, now=NOW)
    assert ex.value.status == 404
    assert S.ds_cong(db, tk) == []
    _mo(db)
    assert [o["ma"] for o in S.ds_cong(db, tk)] == ["expedia"]
    r = S.chuyen(db, tk, "expedia", rid, {"diem_den": "Đà Nẵng", "nhan_phong": "2026-11-12", "tra_phong": "2026-11-14"}, now=NOW)
    assert r["url"] == LINK and "Đà Nẵng" in r["chon_lai"]
    r2 = S.chuyen(db, tk, "expedia", rid, {}, now=NOW)                    # bấm lặp
    assert r2["luot_id"] == r["luot_id"]
    assert len(db.execute(select(LuotChuyenOta)).scalars().all()) == 1
    _mo(db, "booking_com", "https://www.booking.com/index.html?aid=1", "www.booking.com")
    with pytest.raises(S.LoiOta) as ex:                                   # cùng request, khác OTA
        S.chuyen(db, tk, "booking_com", rid, {}, now=NOW)
    assert ex.value.status == 409
    S.sua(db, _u(db, "ct"), _ota(db).id, {"link": "https://expedia.com/affiliate/MOI", "da_kiem_link": True})
    S.bat_tat(db, _u(db, "ct"), _ota(db).id, True)
    with pytest.raises(S.LoiOta) as ex:                                   # link đổi phiên bản → không phát link cũ
        S.chuyen(db, tk, "expedia", rid, {}, now=NOW)
    assert ex.value.status == 409
    with pytest.raises(S.LoiOta):
        S.chuyen(db, tk, "expedia", "khong-phai-uuid", {}, now=NOW)
    with pytest.raises(S.LoiOta):
        S.chuyen(db, tk, "expedia", str(uuid.uuid4()), {"nhan_phong": "2026-10-01"}, now=NOW)


def test_trinh_duyet_khong_gui_duoc_link(db):
    from app.api.v1.khach_san_ota import ChuyenIn
    assert "url" not in ChuyenIn.model_fields and "link" not in ChuyenIn.model_fields
    assert "tai_khoan_id" not in ChuyenIn.model_fields


# ── 4 · BA CỔNG ──────────────────────────────────────────────────────────────────────────────

def test_ba_cong_va_tai_khoan_chua_duyet(db):
    from app.services import khach_san_ota as S
    _mo(db)
    for loai in ("khach_hang", "doi_tac", "co_dong"):
        tk = _tk(db, loai)
        r = S.chuyen(db, tk, "expedia", str(uuid.uuid4()), {}, now=NOW)
        assert r["url"] == LINK
    for loai, tt in (("doi_tac", "cho_duyet"), ("co_dong", "ho_so"), ("khach_hang", "khoa")):
        with pytest.raises(S.LoiOta) as ex:
            S.ds_cong(db, _tk(db, loai, tt))
        assert ex.value.status == 403
    tk = S.thong_ke(db, 7, now=NOW + dt.timedelta(hours=1))
    assert tk["tong"] == 3 and tk["theo_cong"] == {"khach_hang": 1, "doi_tac": 1, "co_dong": 1}
