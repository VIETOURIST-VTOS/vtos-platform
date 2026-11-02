# -*- coding: utf-8 -*-
"""KS-2 · Đối soát OTA (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Đọc đúng tệp báo cáo Expedia Creator Hub (cột thật); đọc thử không ghi gì.
  2. Kế toán nạp, Chủ tịch duyệt; người nạp không tự duyệt; chưa duyệt không chạm sổ; tệp đã nạp không nạp lại.
  3. Đổi trạng thái = phiên bản mới, sổ ghi phần chênh (chỉ ghi thêm); hủy → chênh âm.
  4. Hai dòng giống hệt (không mã) → #1, #2 và báo ra; không gộp.
  5. SubID: chỉ khi OTA cho phép; link gắn mã ngẫu nhiên; báo cáo có mã → nối về lượt; không có → không đoán.
  6. Tiền USD cent, không quy đổi.
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

NOW = dt.datetime(2026, 10, 28, 9, 0)
HEAD = ("Booked date,Booked product,Destination city,Brand,Affiliate link,Estimated commission (USD),Trip status,"
        "Payment status,Start date,End date,Trip element,Company,Destination country,Travelers,Transaction value (USD)\n")


def _csv(*dong: str, them_cot: str = "") -> bytes:
    h = HEAD if not them_cot else HEAD.rstrip("\n") + "," + them_cot + "\n"
    return (h + "\n".join(dong) + "\n").encode()


R1 = "2026-10-12,Hotel,Da Nang,Expedia,Expedia USA,7.46,Pending,Unpaid,2026-11-12,2026-11-14,Lodging,,Vietnam,2,186.40"
R2 = "2026-10-03,Hotel,Bangkok,Expedia,Expedia USA,9.60,Pending,Unpaid,2026-10-05,2026-10-07,Lodging,,Thailand,2,240.00"
R2_XONG = "2026-10-03,Hotel,Bangkok,Expedia,Expedia USA,9.60,Completed,Confirmed,2026-10-05,2026-10-07,Lodging,,Thailand,2,240.00"
R2_HUY = "2026-10-03,Hotel,Bangkok,Expedia,Expedia USA,0.00,Canceled,,2026-10-05,2026-10-07,Lodging,,Thailand,2,240.00"


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.models.khach_san_ota import PhapNhanHopDong, DoiTacOta
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("kt", "ketoan"), ("ktt", "ketoan_truong"), ("tgd", "tgd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.add(PhapNhanHopDong(id=1, ma="INFINIS_CA", ten="THE INFINIS PATHWAY INC.", quoc_gia="Canada"))
    s.add(DoiTacOta(id=1, ma="expedia", ten="Expedia", phap_nhan_id=1, trang_thai="da_duyet", link="https://expedia.com/affiliate/xKzmv5G",
                    ten_mien="expedia.com", duong_dan="/affiliate/", da_kiem_link=True, duoc_dung_web=True, bat=True,
                    quyen="AFFILIATE", moi_truong="thu"))   # SUA-5: hai điều kiện bật của KS-5
    s.commit()
    yield s
    s.close()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _nap_duyet(s, tep: bytes, ky="2026-10"):
    from app.services import doi_soat_ota as S
    lo = S.gui_duyet(s, _u(s, "kt"), 1, ky, "bao-cao.csv", tep, now=NOW)
    return S.duyet(s, _u(s, "ct"), lo.id, now=NOW)


# ── 1 · ĐỌC TỆP ─────────────────────────────────────────────────────────────────────────────

def test_doc_dung_tep_expedia_va_doc_thu_khong_ghi(db):
    from app.services import doi_soat_ota as S
    from app.models.khach_san_ota import DatPhongOta, LoNapOta
    r = S.doc_tep("x.csv", _csv(R1, R2, "Total,,,,,17.06,,,,,,,,,426.40"))
    assert len(r["dong"]) == 2 and r["loi"] == []
    d = r["dong"][0]
    assert d["hoa_hong_cent"] == 746 and d["gia_tri_cent"] == 18640 and d["ngay_den"] == "2026-11-12" and d["so_khach"] == 2
    t = S.doc_thu(db, _u(db, "kt"), 1, "x.csv", _csv(R1, R2))
    assert t["tom"]["moi"] == 2 and t["tom"]["chenh_hoa_hong_cent"] == 1706
    assert db.execute(select(DatPhongOta)).scalars().all() == [] and db.execute(select(LoNapOta)).scalars().all() == []
    with pytest.raises(S.LoiDoiSoat):
        S.doc_tep("x.csv", b"a,b,c\n1,2,3\n")                      # không phải báo cáo đặt phòng


# ── 2 · HAI NGƯỜI ───────────────────────────────────────────────────────────────────────────

def test_nap_duyet_hai_nguoi_va_khong_nap_lai(db):
    from app.services import doi_soat_ota as S
    from app.models.khach_san_ota import DatPhongOta, SoHoaHongOta
    with pytest.raises(S.LoiDoiSoat) as ex:
        S.gui_duyet(db, _u(db, "ct"), 1, "2026-10", "a.csv", _csv(R1), now=NOW)   # Chủ tịch không nạp
    assert ex.value.status == 403
    lo = S.gui_duyet(db, _u(db, "kt"), 1, "2026-10", "a.csv", _csv(R1), now=NOW)
    assert db.execute(select(DatPhongOta)).scalars().all() == []                    # chưa duyệt: chưa chạm sổ
    for ai in ("kt", "ktt", "tgd"):
        with pytest.raises(S.LoiDoiSoat) as ex:
            S.duyet(db, _u(db, ai), lo.id, now=NOW)
        assert ex.value.status == 403
    with pytest.raises(S.LoiDoiSoat):                                               # còn lô chờ → không nạp lô thứ hai
        S.gui_duyet(db, _u(db, "kt"), 1, "2026-10", "b.csv", _csv(R2), now=NOW)
    S.duyet(db, _u(db, "ct"), lo.id, now=NOW)
    assert db.execute(select(SoHoaHongOta.chenh_cent)).scalars().all() == [746]
    with pytest.raises(S.LoiDoiSoat):                                               # đúng tệp ấy: không nạp lại
        S.gui_duyet(db, _u(db, "kt"), 1, "2026-10", "a-copy.csv", _csv(R1), now=NOW)
    with pytest.raises(S.LoiDoiSoat):                                               # từ chối phải có lý do
        lo2 = S.gui_duyet(db, _u(db, "kt"), 1, "2026-10", "b.csv", _csv(R2), now=NOW)
        S.tu_choi(db, _u(db, "ct"), lo2.id, "")


def test_nguoi_nap_khong_tu_duyet(db):
    from app.services import doi_soat_ota as S
    from app.models.core import User
    db.add(User(username="ct2", full_name="CT", role="chutich", password_hash="x")); db.commit()
    from app.models.khach_san_ota import LoNapOta
    lo = LoNapOta(ma="T-1", doi_tac_ota_id=1, ky="2026-10", bam_tep="x", dong=[], loi=[], nap_boi="ct2", nap_luc=NOW, ket_qua={})
    db.add(lo); db.commit()
    with pytest.raises(S.LoiDoiSoat) as ex:
        S.duyet(db, _u(db, "ct2"), lo.id, now=NOW)
    assert ex.value.status == 403


# ── 3 · PHIÊN BẢN VÀ SỔ CHÊNH ───────────────────────────────────────────────────────────────

def test_doi_trang_thai_phien_ban_moi_so_ghi_chenh(db):
    from app.models.khach_san_ota import DatPhongOta, SoHoaHongOta
    from app.services import doi_soat_ota as S
    _nap_duyet(db, _csv(R1, R2))
    lo = _nap_duyet(db, _csv(R1, R2_XONG))
    assert lo.ket_qua["moi"] == 0 and lo.ket_qua["cap_nhat"] == 1 and lo.ket_qua["trung"] == 1
    dp = db.execute(select(DatPhongOta).where(DatPhongOta.thanh_pho == "Bangkok")).scalars().one()
    assert dp.phien_ban == 2 and dp.trang_thai_chuyen == "Completed"
    assert sum(db.execute(select(SoHoaHongOta.chenh_cent)).scalars().all()) == 1706     # đổi trạng thái, tiền không đổi
    _nap_duyet(db, _csv(R2_HUY))
    assert sum(db.execute(select(SoHoaHongOta.chenh_cent)).scalars().all()) == 746      # hủy → chênh âm 960
    t = S.tong_quan(db, _u(db, "ct"))
    m = t["so"][0]
    assert m["dat_phong"] == 1 and m["huy"] == 1 and m["uoc_tinh_cent"] == 746 and t["tien_te"] == "USD"


# ── 4 · DÒNG GIỐNG HỆT ──────────────────────────────────────────────────────────────────────

def test_hai_dong_giong_het_khong_gop(db):
    from app.services import doi_soat_ota as S
    from app.models.khach_san_ota import DatPhongOta
    r = S.doc_tep("x.csv", _csv(R1, R1))
    assert r["trung_trong_tep"] == 1 and r["dong"][0]["khoa"] != r["dong"][1]["khoa"]
    _nap_duyet(db, _csv(R1, R1))
    assert len(db.execute(select(DatPhongOta)).scalars().all()) == 2


# ── 5 · SUBID ───────────────────────────────────────────────────────────────────────────────

def test_subid_chi_khi_cho_phep_va_noi_dung_ma(db):
    from app.services import khach_san_ota as K
    from app.services import doi_soat_ota as S
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.khach_san_ota import DatPhongOta
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong"); db.add(tk); db.commit()
    r = K.chuyen(db, tk, "expedia", str(uuid.uuid4()), {}, now=NOW)
    assert r["url"] == "https://expedia.com/affiliate/xKzmv5G"                       # OTA chưa cho phép: không gắn
    with pytest.raises(K.LoiOta):
        K.sua(db, _u(db, "ct"), 1, {"subid_cho_phep": True})                           # bật thì phải có tên tham số
    with pytest.raises(K.LoiOta):
        K.sua(db, _u(db, "ct"), 1, {"subid_cho_phep": True, "subid_tham_so": "a&b=1"})
    K.sua(db, _u(db, "ct"), 1, {"subid_cho_phep": True, "subid_tham_so": "sid"})
    r = K.chuyen(db, tk, "expedia", str(uuid.uuid4()), {}, now=NOW)
    ma = r["url"].split("sid=")[1]
    assert r["url"].startswith("https://expedia.com/affiliate/xKzmv5G?sid=") and len(ma) == 8 and "0901" not in ma
    _nap_duyet(db, _csv(R1 + "," + ma, R2 + ",khongco", them_cot="SubID"))
    ds = {d.thanh_pho: d for d in db.execute(select(DatPhongOta)).scalars()}
    assert ds["Da Nang"].luot_id is not None and ds["Bangkok"].luot_id is None       # mã lạ: không đoán
    assert K.dat_phong_xac_minh(db, tk)[0]["thanh_pho"] == "Da Nang"
    assert "hoa_hong" not in str(K.dat_phong_xac_minh(db, tk))
    tk2 = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0909999999", trang_thai="hoat_dong"); db.add(tk2); db.commit()
    assert K.dat_phong_xac_minh(db, tk2) == []                                         # khách khác không thấy


def test_khong_subid_thi_khong_noi(db):
    from app.services import khach_san_ota as K
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.khach_san_ota import DatPhongOta
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong"); db.add(tk); db.commit()
    K.chuyen(db, tk, "expedia", str(uuid.uuid4()), {"diem_den": "Da Nang", "nhan_phong": "2026-11-12", "tra_phong": "2026-11-14"}, now=NOW)
    _nap_duyet(db, _csv(R1))                                                           # cùng ngày, cùng thành phố
    assert db.execute(select(DatPhongOta)).scalars().one().luot_id is None


def test_tat_subid_thi_khong_noi_du_ma_dung(db):
    from app.services import khach_san_ota as K
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.khach_san_ota import DatPhongOta
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901234567", trang_thai="hoat_dong"); db.add(tk); db.commit()
    K.sua(db, _u(db, "ct"), 1, {"subid_cho_phep": True, "subid_tham_so": "sid"})
    ma = K.chuyen(db, tk, "expedia", str(uuid.uuid4()), {}, now=NOW)["url"].split("sid=")[1]
    K.sua(db, _u(db, "ct"), 1, {"subid_cho_phep": False})
    _nap_duyet(db, _csv(R1 + "," + ma, them_cot="SubID"))
    assert db.execute(select(DatPhongOta)).scalars().one().luot_id is None
