# -*- coding: utf-8 -*-
"""VB-1 · Vé máy bay qua OTA (Chủ tịch duyệt 28/10/2026: chỉ OTA, không hãng bay; trang công khai được bật,
ghi rõ chưa có hoa hồng; Chủ tịch nhập và bật; cổng Khách hàng và Cổ đông).

  1. Trang công khai: bật được chỉ với link đúng tên miền + đã kiểm; khách sạn KHÔNG dùng được trang công khai.
  2. Đổi loại link = phiên bản mới, tự tắt, phải kiểm lại; chỉ Chủ tịch.
  3. Cổng: Khách hàng, Cổ đông thấy OTA vé; Đối tác bị chặn; khách sạn và vé tách danh sách.
  4. Chuyển: lời nhắc không có câu hoa hồng với trang công khai, có khi là link hoa hồng; không gắn SubID
     vào trang công khai; ngày về trước ngày đi bị chặn; lượt ghi đúng sản phẩm, lịch sử tách theo sản phẩm.
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 10, 28, 9, 0)
DI = (NOW + dt.timedelta(days=50)).date().isoformat()
VE = (NOW + dt.timedelta(days=54)).date().isoformat()


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.models.khach_san_ota import DoiTacOta, PhapNhanHopDong
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("tgd", "tgd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.add(PhapNhanHopDong(id=1, ma="INFINIS_CA", ten="THE INFINIS PATHWAY INC.", quoc_gia="Canada"))
    s.add(DoiTacOta(id=1, ma="expedia", ten="Expedia", phap_nhan_id=1, thu_tu=1))
    s.add(DoiTacOta(id=2, ma="traveloka_ve", ten="Traveloka", san_pham="ve_may_bay", loai_link="cong_khai", thu_tu=11))
    s.add(DoiTacOta(id=3, ma="trip_com_ve", ten="Trip.com", san_pham="ve_may_bay", loai_link="cong_khai", thu_tu=12))
    s.commit()
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _tk(s, loai="khach_hang", tt="hoat_dong", sdt="0901234567"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai=loai, dien_thoai=sdt, trang_thai=tt)
    s.add(tk); s.commit()
    return tk


def _mo_ve(s, oid=2, link="https://www.traveloka.com/vi-vn/flight", mien="www.traveloka.com"):
    from app.services import khach_san_ota as S
    S.sua(s, _u(s, "ct"), oid, {"link": link, "ten_mien": mien})
    S.sua(s, _u(s, "ct"), oid, {"da_kiem_link": True})
    return S.bat_tat(s, _u(s, "ct"), oid, True)


def test_trang_cong_khai_bat_voi_link_va_kiem_khach_san_khong_dung_duoc(db):
    from app.services import khach_san_ota as S
    with pytest.raises(S.LoiOta, match="chưa kiểm link"):
        S.sua(db, _u(db, "ct"), 2, {"link": "https://www.traveloka.com/vi-vn/flight", "ten_mien": "www.traveloka.com"})
        S.bat_tat(db, _u(db, "ct"), 2, True)
    with pytest.raises(S.LoiOta):
        S.sua(db, _u(db, "ct"), 2, {"link": "https://traveloka.com.gia.vn/x"})
    o = _mo_ve(db)
    assert o.bat and S.dang_mo(o) and o.trang_thai == "chua_dang_ky" and not o.duoc_dung_web
    with pytest.raises(S.LoiOta, match="chỉ dùng cho vé máy bay"):
        S.sua(db, _u(db, "ct"), 1, {"loai_link": "cong_khai"})
    o1 = db.get(type(o), 1)
    o1.loai_link = "cong_khai"; o1.link = "https://expedia.com/x"; o1.ten_mien = "expedia.com"; o1.da_kiem_link = True
    assert "trang công khai chỉ dùng cho vé máy bay" in S.thieu_de_bat(o1)
    db.rollback()


def test_doi_loai_link_tu_tat_va_chi_chu_tich(db):
    from app.services import khach_san_ota as S
    o = _mo_ve(db)
    pb = o.phien_ban
    with pytest.raises(S.LoiOta) as ex:
        S.sua(db, _u(db, "tgd"), 2, {"loai_link": "hoa_hong"})
    assert ex.value.status == 403
    o = S.sua(db, _u(db, "ct"), 2, {"loai_link": "hoa_hong"})
    assert not o.bat and not o.da_kiem_link and o.phien_ban == pb + 1
    S.sua(db, _u(db, "ct"), 2, {"da_kiem_link": True})
    with pytest.raises(S.LoiOta, match="hợp tác chưa được duyệt"):
        S.bat_tat(db, _u(db, "ct"), 2, True)               # link hoa hồng: đủ bốn điều kiện như khách sạn


def test_cong_khach_co_dong_thay_doi_tac_bi_chan_va_tach_san_pham(db):
    from app.services import khach_san_ota as S
    _mo_ve(db)
    kh, cd = _tk(db), _tk(db, "co_dong", sdt="0902")
    assert [o["ma"] for o in S.ds_cong(db, kh, "ve_may_bay")] == ["traveloka_ve"]
    assert [o["ma"] for o in S.ds_cong(db, cd, "ve_may_bay")] == ["traveloka_ve"]
    assert S.ds_cong(db, kh, "ve_may_bay")[0]["co_hoa_hong"] is False
    assert S.ds_cong(db, kh) == []                        # danh sách khách sạn không lẫn OTA vé
    dt_ = _tk(db, "doi_tac", sdt="0903")
    with pytest.raises(S.LoiOta) as ex:
        S.ds_cong(db, dt_, "ve_may_bay")
    assert ex.value.status == 403
    with pytest.raises(S.LoiOta) as ex:
        S.chuyen(db, dt_, "traveloka_ve", str(uuid.uuid4()), {"ngay_di": DI}, now=NOW)
    assert ex.value.status == 403
    with pytest.raises(S.LoiOta):
        S.ds_cong(db, kh, "tau_hoa")


def test_chuyen_ve_loi_nhac_khong_subid_va_lich_su(db):
    from app.services import khach_san_ota as S
    from app.models.khach_san_ota import LuotChuyenOta
    o = _mo_ve(db)
    o.subid_cho_phep, o.subid_tham_so = True, "sid"; db.commit()          # cố tình bật SubID trên trang công khai
    kh = _tk(db)
    with pytest.raises(S.LoiOta, match="Ngày về"):
        S.chuyen(db, kh, "traveloka_ve", str(uuid.uuid4()), {"ngay_di": VE, "ngay_ve": DI}, now=NOW)
    with pytest.raises(S.LoiOta, match="em bé"):
        S.chuyen(db, kh, "traveloka_ve", str(uuid.uuid4()), {"nguoi_lon": 1, "em_be": 2}, now=NOW)
    r = S.chuyen(db, kh, "traveloka_ve", str(uuid.uuid4()),
                 {"diem_di": "Hà Nội (HAN)", "diem_den": "Phú Quốc (PQC)", "ngay_di": DI, "ngay_ve": VE,
                  "nguoi_lon": 2, "tre_em": 1, "hang_ve": "pho_thong"}, now=NOW)
    assert r["url"] == "https://www.traveloka.com/vi-vn/flight"           # không gắn SubID vào trang công khai
    assert "hoa hồng" not in r["loi_nhac"]
    assert r["chon_lai"].startswith("Hà Nội (HAN) → Phú Quốc (PQC)") and "1 trẻ em" in r["chon_lai"]
    l = db.execute(select(LuotChuyenOta)).scalars().one()
    assert l.san_pham == "ve_may_bay" and l.loai_link == "cong_khai" and l.diem_di == "Hà Nội (HAN)"
    assert len(S.lich_su(db, kh, "ve_may_bay")) == 1 and S.lich_su(db, kh) == []
    # Chủ tịch chuyển sang link hoa hồng đã duyệt → câu hoa hồng hiện
    S.sua(db, _u(db, "ct"), 3, {"link": "https://www.trip.com/flights/?Allianceid=1", "ten_mien": "trip.com, www.trip.com",
                               "loai_link": "hoa_hong", "trang_thai": "da_duyet", "phap_nhan_id": 1})
    S.sua(db, _u(db, "ct"), 3, {"da_kiem_link": True, "duoc_dung_web": True})
    S.bat_tat(db, _u(db, "ct"), 3, True)
    r2 = S.chuyen(db, kh, "trip_com_ve", str(uuid.uuid4()), {"ngay_di": DI}, now=NOW)
    assert "hoa hồng" in r2["loi_nhac"] and "một chiều" in r2["chon_lai"]
