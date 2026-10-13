# -*- coding: utf-8 -*-
"""Đợt E5 (13/10/2026) — PHÂN BỔ TIỀN RA cho nghĩa vụ và đợt thanh toán.

VÌ SAO CÓ TỆP NÀY

Bảng `phan_bo_tien` dựng ngày 11/9/2026 cho đúng một việc: một khoản tiền VÀO chia cho nhiều
booking. Cột `booking_id` vì thế là cột BẮT BUỘC — và chính nó làm cả nửa kia của dòng tiền
không có chỗ ghi. Chi nhà cung cấp, lương, thuế, trả gốc vay đều không nói được "khoản tiền ra
này trả cho nghĩa vụ nào", trong khi sổ nghĩa vụ đã khai đủ 13 nhóm có cả bốn nhóm ấy.

ĐIỀU TỆP NÀY CANH

1. HAI NHÁNH, ĐÚNG MỘT NHÁNH ĐƯỢC ĐIỀN. Một dòng vừa có booking vừa có nghĩa vụ là một dòng
   không ai đọc được: tiền ấy đã trả cho ai?
2. BỐN CHỖ CHẶN CỨNG, và CHỈ bốn. Mỗi chỗ một phép thử, vì "chặn đúng chỗ" và "chặn nhiều chỗ"
   là hai việc khác nhau — chặn thừa thì người dùng đi vòng, và lúc ấy sổ mất dấu vết.
3. TRẢ DƯ KHÔNG CHẶN. Giữ đúng luật đang chạy của tiền vào.
4. TIỀN RA KHÔNG SINH PHIẾU THU. Phiếu thu là chứng từ mẫu 01-TT của tiền vào.
5. HUỶ TRẢ TIỀN LẠI cho đợt và nghĩa vụ. Huỷ mà không trả lại thì nghĩa vụ tưởng mình đã được
   trả, còn khoản tiền thì đã về số dư chưa phân bổ — hai sổ nói hai điều khác nhau.
6. ĐƯỜNG TIỀN VÀO KHÔNG ĐỔI MỘT CHỮ.
"""
import os
import sys
import tempfile
from datetime import date

# MỘT TỆP PHÉP THỬ, MỘT CƠ SỞ DỮ LIỆU RIÊNG — đúng lệ của kho này (xem `tests/run_all.sh`: mỗi tệp
# chạy một tiến trình). Đặt biến TRƯỚC khi nhập bất cứ mô-đun nào của ứng dụng, vì máy kết nối được
# dựng đúng một lần lúc nhập: tệp nào nhập trước thì máy bám theo cơ sở dữ liệu của tệp ấy.
#
# Đo được 13/10/2026: bản đầu của tệp này dùng `setdefault` nên khi chạy CHUNG MỘT TIẾN TRÌNH với
# `test_vpm5_phan_bo_tien.py` thì tệp kia đỏ 15 phép. Không phải lỗi của mã nghiệp vụ — là phép đo
# sai, vì hai tệp cùng giành một máy kết nối. Dù vậy vẫn sửa theo lệ, để tệp này còn an toàn nếu
# sau có người đưa nó vào cửa hẹp (cửa hẹp chạy nhiều tệp trong MỘT tiến trình).
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e5.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                              # noqa: E402
from sqlalchemy import select                              # noqa: E402

from app.db.session import Base, SessionLocal, engine        # noqa: E402
from app.models.core import User                             # noqa: E402
from app.models.nghia_vu import NghiaVuThanhToan, DotThanhToan   # noqa: E402
from app.models.payments import BankTransaction              # noqa: E402
from app.models.phan_bo_tien import PhanBoTien               # noqa: E402
from app.services import phan_bo_tien as PB                  # noqa: E402

Base.metadata.create_all(engine)


def db_():
    return SessionLocal()


def _nguoi(db):
    u = db.execute(select(User).where(User.username == "e5_ketoan")).scalars().first()
    if not u:
        u = User(username="e5_ketoan", full_name="Kế toán E5", role="ketoan", password_hash="x")
        db.add(u); db.commit()
    return u


_dem = [0]


def _nv(db, *, huong="chi", company_id=1, tong=1_000_000.0, trang_thai="du_kien", dot=None):
    _dem[0] += 1
    n = NghiaVuThanhToan(ma_goc=f"NV-E5-{_dem[0]:04d}", huong=huong, nhom="tra_ncc",
                         company_id=company_id, doi_tuong="NCC thử", noi_dung="E5",
                         tong_nghia_vu=tong, trang_thai=trang_thai,
                         nguon_bang="test_e5", nguon_id=str(_dem[0]), ngay_cam_ket=date.today())
    db.add(n); db.flush()
    d = None
    if dot:
        d = DotThanhToan(nghia_vu_id=n.id, so_thu_tu=1, so_tien=dot, ngay_han=date.today())
        db.add(d); db.flush()
    db.commit()
    return n, d


def _gd(db, *, huong="out", so_tien=1_000_000.0, company_id=1):
    _dem[0] += 1
    t = BankTransaction(sepay_id=f"E5-{_dem[0]:05d}", amount=so_tien, transfer_type=huong,
                        content="thu nghiem E5", transaction_date=date.today(),
                        account_number="01811267101", match_status="cho_ke_toan")
    if hasattr(t, "company_id"):
        t.company_id = company_id
    db.add(t); db.commit()
    return t


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HAI NHÁNH
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e5_1_dong_nhanh_nghia_vu_khong_co_booking():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db); t = _gd(db)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 400_000}])
    pb = db.execute(select(PhanBoTien).where(PhanBoTien.bank_txn_id == t.id)).scalars().first()
    assert pb.booking_id is None and pb.nghia_vu_id == nv.id
    assert pb.nhanh() == "nghia_vu"
    db.close()


def test_e5_2_nhanh_doc_tu_du_lieu_chu_khong_tu_mot_cot_co():
    """Một cột cờ có thể nói `booking` trong khi `booking_id` rỗng; suy từ dữ liệu thì không."""
    assert PhanBoTien(booking_id=7).nhanh() == "booking"
    assert PhanBoTien(nghia_vu_id=9).nhanh() == "nghia_vu"
    assert PhanBoTien().nhanh() == ""


def test_e5_3_tien_ra_khong_sinh_phieu_thu():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db); t = _gd(db)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 100_000}])
    pb = db.execute(select(PhanBoTien).where(PhanBoTien.bank_txn_id == t.id)).scalars().first()
    assert pb.receipt_id is None, "Tiền ra mà sinh phiếu thu là dựng chứng từ ma"
    db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BỐN CHỖ CHẶN CỨNG — mỗi chỗ một phép thử
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e5_4_chan_nghia_vu_huong_thu():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db, huong="thu"); t = _gd(db)
    with pytest.raises(ValueError) as ex:
        PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 100_000}])
    assert "THU" in str(ex.value)
    db.close()


def test_e5_5_chan_nghia_vu_da_dong():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db, trang_thai="da_tra"); t = _gd(db)
    with pytest.raises(ValueError) as ex:
        PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 100_000}])
    assert "đã đóng" in str(ex.value)
    db.close()


def test_e5_6_chan_sai_phap_nhan_va_chan_ca_khi_chua_biet_phap_nhan():
    """Chưa biết pháp nhân thì CHẶN, không đoán — luật K2 ở chỗ tốn tiền nhất."""
    db = db_(); u = _nguoi(db)
    t = _gd(db, company_id=1)
    nv_khac, _ = _nv(db, company_id=2)
    nv_rong, _ = _nv(db, company_id=None)
    if getattr(t, "company_id", None) is not None:
        with pytest.raises(ValueError) as ex:
            PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv_khac.id, "so_tien": 100_000}])
        assert "pháp nhân" in str(ex.value)
    with pytest.raises(ValueError) as ex2:
        PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv_rong.id, "so_tien": 100_000}])
    assert "chưa xác định pháp nhân" in str(ex2.value)
    db.close()


def test_e5_7_chan_vuot_so_du_chua_phan_bo():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db); t = _gd(db, so_tien=500_000)
    with pytest.raises(ValueError) as ex:
        PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 600_000}])
    assert "vượt số dư" in str(ex.value)
    assert db.execute(select(PhanBoTien).where(PhanBoTien.bank_txn_id == t.id)).scalars().first() is None, \
        "Cả lô phải được kiểm TRƯỚC khi ghi dòng đầu tiên"
    db.close()


def test_e5_8_chan_dot_khong_thuoc_nghia_vu_da_chon():
    db = db_(); u = _nguoi(db)
    nv1, d1 = _nv(db, dot=500_000)
    nv2, _ = _nv(db)
    t = _gd(db)
    with pytest.raises(ValueError) as ex:
        PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv2.id, "dot_id": d1.id, "so_tien": 100_000}])
    assert "không thuộc nghĩa vụ" in str(ex.value)
    db.close()


def test_e5_9_tra_du_thi_CANH_BAO_chu_khong_chan():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db, tong=100_000); t = _gd(db, so_tien=500_000)
    ra = PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 300_000}])
    assert ra["da_them"] == 1
    assert ra["canh_bao"] and "trả trước" in ra["canh_bao"][0]
    db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐÃ TRẢ, VÀ HUỶ THÌ TRẢ LẠI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e5_10_cong_vao_ca_dot_lan_nghia_vu():
    db = db_(); u = _nguoi(db)
    nv, d = _nv(db, tong=900_000, dot=900_000); t = _gd(db, so_tien=900_000)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "dot_id": d.id, "so_tien": 900_000}])
    db.refresh(nv); db.refresh(d)
    assert float(nv.da_tra) == 900_000 and float(d.da_tra) == 900_000
    assert d.da_tra_du() and nv.con_lai() == 0
    db.close()


def test_e5_11_huy_thi_tra_tien_lai_cho_dot_va_nghia_vu():
    """Huỷ mà không trả lại thì nghĩa vụ tưởng đã được trả, còn tiền đã về số dư — hai sổ lệch."""
    db = db_(); u = _nguoi(db)
    nv, d = _nv(db, tong=600_000, dot=600_000); t = _gd(db, so_tien=600_000)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "dot_id": d.id, "so_tien": 600_000}])
    pb = db.execute(select(PhanBoTien).where(PhanBoTien.bank_txn_id == t.id)).scalars().first()
    PB.huy_dong(db, u, pb, "ghi nhầm nghĩa vụ")
    db.refresh(nv); db.refresh(d)
    assert float(nv.da_tra or 0) == 0 and float(d.da_tra or 0) == 0
    assert PB.con_lai(db, t) == 600_000
    db.close()


def test_e5_12_huy_bat_buoc_co_ly_do():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db); t = _gd(db)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 50_000}])
    pb = db.execute(select(PhanBoTien).where(PhanBoTien.bank_txn_id == t.id)).scalars().first()
    with pytest.raises(ValueError):
        PB.huy_dong(db, u, pb, "   ")
    db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HAI ĐƯỜNG KHÔNG LẪN NHAU
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e5_13_cua_tien_ra_tu_choi_giao_dich_tien_vao_va_nguoc_lai():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db)
    t_vao = _gd(db, huong="in")
    with pytest.raises(ValueError) as ex:
        PB.phan_bo_ra(db, u, t_vao, [{"nghia_vu_id": nv.id, "so_tien": 10_000}])
    assert "chỉ phân bổ tiền RA" in str(ex.value).replace("Cửa này ", "")
    t_ra = _gd(db, huong="out")
    with pytest.raises(ValueError) as ex2:
        PB.phan_bo(db, u, t_ra, [{"booking_id": 1, "so_tien": 10_000}])
    assert "tiền VÀO" in str(ex2.value)
    db.close()


def test_e5_14_mot_khoan_chia_cho_nhieu_nghia_vu():
    db = db_(); u = _nguoi(db)
    a, _ = _nv(db, tong=300_000)
    b, _ = _nv(db, tong=200_000)
    t = _gd(db, so_tien=500_000)
    ra = PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": a.id, "so_tien": 300_000},
                                  {"nghia_vu_id": b.id, "so_tien": 200_000}])
    assert ra["da_them"] == 2 and ra["chua_phan_bo"] == 0
    db.close()


def test_e5_15_mot_dot_tra_bang_nhieu_khoan():
    db = db_(); u = _nguoi(db)
    nv, d = _nv(db, tong=500_000, dot=500_000)
    t1 = _gd(db, so_tien=200_000); t2 = _gd(db, so_tien=300_000)
    PB.phan_bo_ra(db, u, t1, [{"nghia_vu_id": nv.id, "dot_id": d.id, "so_tien": 200_000}])
    PB.phan_bo_ra(db, u, t2, [{"nghia_vu_id": nv.id, "dot_id": d.id, "so_tien": 300_000}])
    db.refresh(d)
    assert float(d.da_tra) == 500_000 and d.da_tra_du()
    db.close()


def test_e5_16_bang_noi_ro_dong_nao_thuoc_nhanh_nao():
    db = db_(); u = _nguoi(db)
    nv, _ = _nv(db); t = _gd(db)
    PB.phan_bo_ra(db, u, t, [{"nghia_vu_id": nv.id, "so_tien": 70_000, "ghi_chu": "đợt 1"}])
    b = PB.bang(db, t)
    assert b["dong"][0]["nhanh"] == "nghia_vu"
    assert b["dong"][0]["nghia_vu_ma"] == nv.ma_goc
    assert b["dong"][0]["booking_code"] == ""
    db.close()
