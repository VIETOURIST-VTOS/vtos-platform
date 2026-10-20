# -*- coding: utf-8 -*-
"""Mục 3 · Công suất khai thác — mẫu số dừng ở hôm nay, và đếm ngày-xe từng chiếc. 21/10/2026.

VÌ SAO VÒNG NÀY CÓ MẶT. Sáng 21/10/2026 khối «Hiệu quả đội xe» trên màn hình Chủ tịch in công suất
kỳ 2026-10 là **33,7%**. Mở phép chia ra: 115 ngày khai thác chia cho 11 xe × 31 ngày = 341 ngày-xe.
Nhưng hôm ấy mới là ngày 20 — **11 ngày cuối tháng chưa tới**, và đội xe đang bị chia cho những ngày
chưa ai có cơ hội chạy. Đo lại trên 1→20/10: 115 / (11 × 20) = **52,3%**.

Sai 18,6 điểm phần trăm, và sai theo hướng XẤU ĐI. Hướng ấy nghe như "cẩn thận" nên không ai nghi —
nhưng nó là con số Chủ tịch đọc để kết luận đội xe đang nhàn, và một kết luận như thế đẻ ra quyết
định thật (bán xe, cắt tài xế). Một chỉ số sai theo hướng xấu vẫn là một chỉ số sai.

BA ĐIỀU PHÉP THỬ NÀY CANH:

  1. KỲ ĐANG CHẠY: mẫu dừng ở hôm nay. Đây là cả lý do vòng này tồn tại.
  2. KỲ ĐÃ QUA: KHÔNG đổi một chữ. `min` không được phép cắt gì khi cả kỳ nằm sau lưng — sửa chỗ
     này mà làm lệch số tháng 8 thì mọi báo cáo đã in ra đều hết khớp.
  3. ĐẾM NGÀY-XE TỪNG CHIẾC, không `số xe × số ngày kỳ`. Phép nhân phẳng cho một chiếc mua ngày 20
     cùng số ngày với một chiếc chạy suốt tháng.

Và một điều nữa, nhỏ mà dễ hỏng: QUÝ/NĂM phải cộng chính mẫu số của từng tháng, không nhân lại
`số xe × số ngày`. Nhân lại là dựng chỗ cho quý nói một công suất khác tháng, và lúc ấy không ai
biết màn nào đúng.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.services import hieu_qua_xe as HQ  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def hom_nay(monkeypatch):
    """Ghim hôm nay = 20/10/2026. Không ghim thì phép thử này đổi kết quả theo lịch."""
    def _ghim(ngay: date):
        monkeypatch.setattr(HQ, "_hom_nay", lambda: ngay)
    _ghim(date(2026, 10, 20))
    return _ghim


def _xe(db, bien, vao=date(2025, 1, 1), roi=None, cho=45):
    v = Vehicle(plate=bien, seats=cho, ngay_vao_doi=vao, ngay_roi_doi=roi)
    db.add(v); db.flush()
    return v


def _chuyen(db, v, ma, di, ve):
    t = Trip(ma_phieu=ma, vehicle_id=v.id, ngay_di=di, ngay_ve=ve, km_dau=1000, km_cuoi=1300,
             doanh_thu=1_000_000, ten_tour="thử")
    db.add(t); db.flush()
    return t


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 1 · KỲ ĐANG CHẠY — mẫu dừng ở hôm nay
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_ky_dang_chay_mau_dung_o_hom_nay_khong_tinh_ngay_chua_toi(db, hom_nay):
    _xe(db, "50F-001.01")
    # Hôm nay 20/10 → mẫu phải là 20 ngày-xe, không phải 31.
    assert HQ.ngay_xe_trong_doi(db, date(2026, 10, 1), date(2026, 10, 20)) == 20
    o = HQ.chi_so(db, "2026-10")
    assert o["_ngay_xe_mau"] == 20, "Mẫu số phải dừng ở hôm nay, không chia cho 11 ngày chưa tới"


def test_ky_chua_toi_tra_None_chu_khong_phai_0_phan_tram(db, hom_nay):
    _xe(db, "50F-001.01")
    o = HQ.chi_so(db, "2026-12")
    assert o["_ngay_xe_mau"] == 0, "Tháng chưa tới thì không có ngày-xe nào cả"
    # 0,0% đọc ra như một tháng đội xe nằm bãi. Chưa tới KHÁC nằm bãi.
    assert o["cong_suat_khai_thac"] is None


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 2 · KỲ ĐÃ QUA — không được đổi một chữ
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_ky_da_qua_khong_doi_gi_ca(db, hom_nay):
    _xe(db, "50F-001.01")
    _xe(db, "50F-002.02")
    # Tháng 8 nằm trọn sau lưng: hai xe × 31 ngày = 62, y như luật cũ.
    assert HQ.chi_so(db, "2026-08")["_ngay_xe_mau"] == 62


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 3 · ĐẾM NGÀY-XE TỪNG CHIẾC
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_xe_vao_doi_giua_ky_chi_gop_so_ngay_no_co_mat(db, hom_nay):
    _xe(db, "50F-001.01")                                   # cả kỳ: 20 ngày (tới hôm nay)
    _xe(db, "50F-002.02", vao=date(2026, 10, 11))           # từ 11/10: 10 ngày
    # Nhân phẳng sẽ ra 2 × 20 = 40. Đếm từng chiếc ra 30.
    assert HQ.chi_so(db, "2026-10")["_ngay_xe_mau"] == 30


def test_xe_ban_giua_ky_chi_gop_den_ngay_roi_doi(db, hom_nay):
    _xe(db, "50F-001.01")                                                     # 20 ngày
    _xe(db, "50F-002.02", roi=date(2026, 10, 5), cho=45)                      # 1→5/10: 5 ngày
    db.execute(Vehicle.__table__.update()
               .where(Vehicle.plate == "50F-002.02").values(lifecycle="da_ban"))
    assert HQ.chi_so(db, "2026-10")["_ngay_xe_mau"] == 25


def test_cong_suat_doc_duoc_tren_so_that(db, hom_nay):
    """Dáng của chính con số 21/10: 11 xe, 20 ngày, ra 220 ngày-xe chứ không 341."""
    for i in range(11):
        _xe(db, f"50F-{i:03d}.00")
    assert HQ.chi_so(db, "2026-10")["_ngay_xe_mau"] == 220


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 4 · QUÝ/NĂM cộng mẫu của từng tháng
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_quy_cong_mau_tung_thang_chu_khong_nhan_lai(db, hom_nay):
    a = _xe(db, "50F-001.01")
    _xe(db, "50F-002.02")
    _chuyen(db, a, "A1", date(2026, 10, 2), date(2026, 10, 5))     # 4 ngày khai thác

    # Quý 4 = T10 (20 ngày đã qua) + T11 + T12 (chưa tới) → mẫu chỉ còn phần của T10.
    thang = [HQ.chi_so(db, k)["_ngay_xe_mau"] for k in ("2026-10", "2026-11", "2026-12")]
    assert thang == [40, 0, 0], "Hai xe × 20 ngày đã qua của tháng 10, hai tháng sau chưa tới"

    ngay = sum((HQ.chi_so(db, k)["ngay_xe_hoat_dong"] or 0)
               for k in ("2026-10", "2026-11", "2026-12"))
    assert ngay > 0, "Phải có tử số, nếu không phép thử này không đo được gì"

    o = HQ._gop(db, ["2026-10", "2026-11", "2026-12"])
    assert o["cong_suat_khai_thac"] == round(ngay * 100 / sum(thang), 1), \
        "Quý phải chia cho ĐÚNG tổng mẫu của ba tháng, không nhân lại số xe × số ngày"

    # Và đây là chỗ luật cũ sẽ ĐỎ: nhân phẳng ra 2 × (31+30+31) = 184, công suất tụt gần năm lần.
    assert o["cong_suat_khai_thac"] != round(ngay * 100 / 184, 1)
