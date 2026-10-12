# -*- coding: utf-8 -*-
"""HQ-1 · Hiệu quả đội xe: mẫu số công suất theo ĐỘI HÌNH TẠI KỲ, và km chạy rỗng.

Phép thử ở đây canh hai chỗ, và cả hai đều được KIỂM NGƯỢC (sửa hỏng luật thì phép thử phải đỏ):

  1. Mẫu số công suất không bao giờ nhỏ hơn số xe có chạy trong kỳ. Đây chính là mâu thuẫn đo được
     trên hệ thật ngày 13/10/2026 — màn hình in "14/12 xe có chạy trong kỳ".
  2. Km chạy rỗng là khoảng hở giữa hai chuyến liền nhau, và khoảng hở ÂM không được cộng.
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
from app.services import fleet_lai_lo as LL  # noqa: E402

KY = "2026-01"
D1, D2 = date(2026, 1, 1), date(2026, 1, 31)


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _xe(db, bien, vao=None, roi=None, lifecycle="dang_khai_thac"):
    v = Vehicle(plate=bien, ngay_vao_doi=vao, ngay_roi_doi=roi, lifecycle=lifecycle,
                active=(lifecycle == "dang_khai_thac"))
    db.add(v); db.flush()
    return v


def _chuyen(db, v, ma, di, ve, kd=None, kc=None, dt=0):
    t = Trip(ma_phieu=ma, vehicle_id=v.id, ngay_di=di, ngay_ve=ve,
             km_dau=kd, km_cuoi=kc, doanh_thu=dt, ten_tour="thử")
    db.add(t); db.flush()
    return t


# ═══════════════════ 1 · ĐỘI HÌNH TẠI KỲ ═══════════════════
def test_xe_da_ban_van_nam_trong_mau_so_cua_ky_no_con_chay(db):
    """Chiếc bán tháng 6 VẪN thuộc đội hình tháng 1. Đây là lỗi đã đo trên hệ thật."""
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _xe(db, "50F-034.37", vao=date(2025, 1, 1), roi=date(2026, 6, 30), lifecycle="da_ban")
    db.flush()
    dh = HQ.doi_hinh(db, D1, D2)
    assert dh["du_du_lieu"] is True
    assert dh["so_xe"] == 2, "xe bán tháng 6 phải còn trong đội hình tháng 1"


def test_xe_roi_doi_truoc_ky_thi_khong_con_trong_mau_so(db):
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _xe(db, "50F-034.37", vao=date(2025, 1, 1), roi=date(2025, 12, 31), lifecycle="da_ban")
    db.flush()
    assert HQ.doi_hinh(db, D1, D2)["so_xe"] == 1


def test_xe_vao_doi_sau_ky_thi_chua_tinh(db):
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _xe(db, "50H-944.58", vao=date(2026, 3, 1))
    db.flush()
    assert HQ.doi_hinh(db, D1, D2)["so_xe"] == 1


def test_thieu_ngay_vao_doi_thi_TRA_VE_TRONG_chu_khong_doan(db):
    """Chủ tịch chọn 13/10/2026: ẩn còn hơn hiện số sai."""
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _xe(db, "51B-123.45")                      # chưa ai khai ngày vào đội
    db.flush()
    dh = HQ.doi_hinh(db, D1, D2)
    assert dh["so_xe"] is None and dh["du_du_lieu"] is False
    assert any(x["xe"] == "51B-123.45" for x in dh["thieu"]), "phải nói RÕ xe nào còn thiếu"
    assert dh["bo_phan"] == "Đội xe" and dh["cua_nhap"]


def test_xe_da_ban_ma_khong_co_ngay_roi_la_ho_so_chua_du(db):
    _xe(db, "50F-034.37", vao=date(2025, 1, 1), lifecycle="da_ban")
    db.flush()
    dh = HQ.doi_hinh(db, D1, D2)
    assert dh["du_du_lieu"] is False
    assert "rời đội" in dh["thieu"][0]["thieu"]


def test_MAU_SO_KHONG_BAO_GIO_NHO_HON_SO_XE_CO_CHAY(db):
    """Mâu thuẫn "14/12" đo trên hệ thật 13/10/2026 — phép thử này là chỗ nó không tái diễn.

    KIỂM NGƯỢC: đổi `doi_hinh` về `len([v for v in xe if v.active])` (phép tính cũ) thì chiếc đã bán
    rơi khỏi mẫu trong khi vẫn có chuyến ở tử — phép thử này đỏ.
    """
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    b = _xe(db, "50F-034.37", vao=date(2025, 1, 1), roi=date(2026, 6, 30), lifecycle="da_ban")
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    _chuyen(db, b, "B1", date(2026, 1, 8), date(2026, 1, 9), 2000, 2400, 8_000_000)
    db.flush()
    bc = LL.bao_cao(db, KY)
    t = bc["tong"]
    assert t["so_xe_trong_doi"] is not None
    assert t["so_xe_khai_thac"] <= t["so_xe_trong_doi"], (
        f"{t['so_xe_khai_thac']}/{t['so_xe_trong_doi']} — tử không được lớn hơn mẫu")
    assert 0 < t["cong_suat"] <= 1


def test_bao_cao_de_trong_cong_suat_khi_doi_hinh_chua_du(db):
    a = _xe(db, "50F-017.37")                  # chưa khai ngày vào đội
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    t = LL.bao_cao(db, KY)["tong"]
    assert t["cong_suat"] is None, "chưa đủ dữ liệu thì KHÔNG được hiện một con số"
    assert t["cong_suat_thieu"] and t["cong_suat_thieu"]["bo_phan"] == "Đội xe"


# ═══════════════════ 2 · KM CHẠY RỖNG ═══════════════════
def test_km_chay_rong_la_khoang_ho_giua_hai_chuyen(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500)
    _chuyen(db, a, "A2", date(2026, 1, 10), date(2026, 1, 12), 1540, 1900)
    db.flush()
    r = HQ.km_chay_rong(db, D1, D2)
    assert r["km"] == 40 and r["so_khoang"] == 1


def test_khoang_ho_AM_khong_duoc_cong_va_phai_bao_ra(db):
    """Sổ ghi ngược thì khoảng hở âm. Cộng vào là biến lỗi nhập liệu thành chỉ số điều hành."""
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500)
    _chuyen(db, a, "A2", date(2026, 1, 10), date(2026, 1, 12), 1400, 1900)   # lùi 100 km
    db.flush()
    r = HQ.km_chay_rong(db, D1, D2)
    assert r["km"] == 0, "không cộng khoảng hở âm"
    assert r["so_lech"] == 1 and r["lech"][0]["ma_phieu"] == "A2", "và không im lặng bỏ qua nó"


def test_khoang_ho_cua_hai_xe_khac_nhau_khong_tron_vao_nhau(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    b = _xe(db, "50H-944.58", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500)
    _chuyen(db, b, "B1", date(2026, 1, 8), date(2026, 1, 9), 90000, 90400)
    db.flush()
    assert HQ.km_chay_rong(db, D1, D2)["km"] == 0, "hai xe khác nhau thì không có khoảng hở nào"


def test_khoang_ho_ngay_truoc_chuyen_dau_tien_cua_ky_van_duoc_dem(db):
    """Chuyến cuối tháng 12 → chuyến đầu tháng 1: quãng rỗng ấy thuộc kỳ tháng 1."""
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "T12", date(2025, 12, 28), date(2025, 12, 30), 800, 980)
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500)
    db.flush()
    assert HQ.km_chay_rong(db, D1, D2)["km"] == 20


def test_chuyen_thieu_km_thi_bo_qua_chu_khong_doc_ra_0(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), None, None)
    _chuyen(db, a, "A2", date(2026, 1, 10), date(2026, 1, 12), 1540, 1900)
    db.flush()
    r = HQ.km_chay_rong(db, D1, D2)
    assert r["km"] == 0 and r["so_khoang"] == 0 and r["so_lech"] == 0


# ═══════════════════ 3 · BỐN CHỈ SỐ CỦA KHỐI CHỦ TỊCH ═══════════════════
def test_bon_chi_so_dung_khuon_HieuQuaXe(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    _chuyen(db, a, "A2", date(2026, 1, 10), date(2026, 1, 12), 1540, 1900, 8_000_000)
    db.flush()
    o = HQ.chi_so(db, KY)
    assert set(("ngay_xe_hoat_dong", "cong_suat_khai_thac", "km_chay_rong",
                "chi_phi_moi_km", "da_chot")) <= set(o)
    assert o["ngay_xe_hoat_dong"] == 6                      # 3 ngày + 3 ngày, không trùng nhau
    assert o["cong_suat_khai_thac"] == round(6 * 100 / 31, 1)
    assert o["km_chay_rong"] == 40
    assert o["da_chot"] is False


def test_cong_suat_tinh_theo_PHAN_TRAM_0_100_dung_hop_dong_giao_dien(db):
    """KhoiV14.tsx khai rõ: `cong_suat_khai_thac` là phần trăm 0–100 và màn hình nối thêm dấu '%'.

    Trả tỷ lệ 0–1 ở đây thì khối in "0.2%" cho một tháng chạy 20% — sai hai chữ số.
    """
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    for i in range(10):                                     # 10 ngày chạy / 31 ngày
        _chuyen(db, a, f"A{i}", date(2026, 1, i + 1), date(2026, 1, i + 1), 1000 + i * 10,
                1005 + i * 10, 1_000_000)
    db.flush()
    cs = HQ.chi_so(db, KY)["cong_suat_khai_thac"]
    assert 30 < cs < 35, f"phải là phần trăm 0–100, nhận {cs}"


def test_chi_so_de_trong_cong_suat_khi_chua_du_doi_hinh_nhung_van_tra_ba_o_kia(db):
    """Một ô thiếu dữ liệu KHÔNG được kéo ba ô còn lại xuống theo."""
    a = _xe(db, "50F-017.37")                               # chưa khai ngày vào đội
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    _chuyen(db, a, "A2", date(2026, 1, 10), date(2026, 1, 12), 1540, 1900, 8_000_000)
    db.flush()
    o = HQ.chi_so(db, KY)
    assert o["cong_suat_khai_thac"] is None
    assert o["ngay_xe_hoat_dong"] == 6 and o["km_chay_rong"] == 40
    assert o["cong_suat_thieu"]["bo_phan"] == "Đội xe"


def test_ky_khong_co_chuyen_nao_thi_BO_TRONG_chu_khong_tra_0(db):
    """0 đọc ra là 'đội xe chạy 0 ngày'. Trống đọc ra là 'chưa có số' — hai chuyện khác nhau."""
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    db.flush()
    o = HQ.chi_so(db, "2026-03")
    assert o["ngay_xe_hoat_dong"] is None
    assert o["km_chay_rong"] is None
    assert o["chi_phi_moi_km"] is None


def test_theo_ky_quy_tinh_LAI_cong_suat_tren_tong_chu_khong_lay_trung_binh(db):
    """Trung bình của ba tỷ lệ có mẫu khác nhau là một con số không nghĩa gì."""
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 14), 1000, 1500, 9_000_000)   # 10 ngày
    _chuyen(db, a, "B1", date(2026, 2, 1), date(2026, 2, 2), 1500, 1700, 2_000_000)    # 2 ngày
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 2, 15))
    assert tk["thang"]["cong_suat_khai_thac"] == round(2 * 100 / 28, 1)
    assert tk["quy"]["cong_suat_khai_thac"] == round(12 * 100 / (31 + 28), 1)
    tb = (round(10 * 100 / 31, 1) + round(2 * 100 / 28, 1)) / 2
    assert abs(tk["quy"]["cong_suat_khai_thac"] - tb) > 0.5, "không được là trung bình cộng"


def test_theo_ky_tra_du_ba_khoa_thang_quy_nam(db):
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 2, 15))
    assert {"thang", "quy", "nam"} <= set(tk)
    for t in ("thang", "quy", "nam"):
        assert set(("nhan", "ngay_xe_hoat_dong", "cong_suat_khai_thac", "km_chay_rong",
                    "chi_phi_moi_km", "da_chot", "trong_vi_sao")) <= set(tk[t])


# ═══════════════════ 6 · KỲ MỞ SẴN VÀ LÝ DO KỲ TRỐNG (HQ-1c) ═══════════════════
#
# Đo trên hệ thật 13/10/2026 sau khi HQ-1b lên: máy chủ CÓ số (năm: 2.127 ngày · 56.927 km ·
# 10.064 đ/km) nhưng khối mở sẵn ở kỳ THÁNG, mà tháng 10 chưa ai nạp chuyến nào — nên Chủ tịch
# thấy bốn dấu gạch và kết luận "đội xe chưa lên màn hình". Sổ quyết toán xe chỉ chốt sau khi hết
# tháng, nên tháng đang chạy sẽ trống gần như suốt. Con số có thật mà vẫn bằng không có.
def test_mo_san_o_ky_HEP_NHAT_con_co_so(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    # mốc 15/02: tháng 2 rỗng, quý I có tháng 1 → mở ở quý, không nhảy thẳng lên năm
    assert HQ.theo_ky(db, date(2026, 2, 15))["mac_dinh"] == "quy"
    # mốc 15/01: chính tháng ấy có chuyến → mở ở tháng
    assert HQ.theo_ky(db, date(2026, 1, 15))["mac_dinh"] == "thang"
    # mốc 15/04: quý II rỗng, cả năm vẫn còn tháng 1 → mở ở năm
    assert HQ.theo_ky(db, date(2026, 4, 15))["mac_dinh"] == "nam"


def test_khong_ky_nao_co_so_thi_van_mo_o_thang(db):
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 4, 15))
    assert tk["mac_dinh"] == "thang"
    assert tk["thang"]["trong_vi_sao"]


def test_ky_trong_noi_RO_vi_sao_va_chi_ra_ky_con_so(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 4, 15))
    vs = tk["thang"]["trong_vi_sao"]
    assert "Tháng 04/2026" in vs and "chưa nạp chuyến nào" in vs
    assert "tháng 01/2026" in vs, f"phải chỉ ra kỳ mới nhất còn số, nhận: {vs}"
    assert tk["ky_moi_nhat_co_chuyen"] == "2026-01"


def test_ky_CO_so_thi_khong_co_ly_do_trong(db):
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 1, 15))
    assert tk["thang"]["trong_vi_sao"] is None
    assert tk["thang"]["nhan"] == "Tháng 01/2026"


def test_nhan_ky_noi_RO_dang_xem_khoang_nao(db):
    """Nhãn là chỗ chống đọc nhầm: "Năm" mà thật ra mới tới tháng 10 thì phải nói ra."""
    _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 10, 13))
    assert tk["nam"]["nhan"] == "Năm 2026 (T01–T10)"
    assert tk["quy"]["nhan"] == "Quý 4/2026 (đến hết tháng 10)"
    assert tk["thang"]["nhan"] == "Tháng 10/2026"


# ═══════════════════ 4 · CỬA NHẬP CHO HAI CỘT NGÀY ═══════════════════
def test_cua_ho_so_xe_co_du_hai_o_ngay(db):
    """Mở cột mà không mở cửa thì ô công suất ghi 'chưa đủ dữ liệu' vĩnh viễn."""
    from app.services.intake import BO_NAP
    cot = {c["key"] for c in BO_NAP["ho_so_xe"]["cot"]}
    assert {"ngay_vao_doi", "ngay_roi_doi"} <= cot


def test_cua_ho_so_xe_ghi_duoc_hai_ngay(db):
    from app.services.intake import BO_NAP
    bo = BO_NAP["ho_so_xe"]
    v = _xe(db, "50F-017.37")
    db.flush()
    r = {"bien_so": "50F-017.37", "ngay_vao_doi": "01/02/2025", "ngay_roi_doi": "30/06/2026"}
    loi, cb, trung = bo["kiem"](db, r)
    assert loi == [], loi
    bo["nap"](db, r, "chutich")
    db.refresh(v)
    assert v.ngay_vao_doi == date(2025, 2, 1) and v.ngay_roi_doi == date(2026, 6, 30)


def test_cua_chan_ngay_roi_truoc_ngay_vao(db):
    from app.services.intake import BO_NAP
    _xe(db, "50F-017.37"); db.flush()
    loi, cb, _ = BO_NAP["ho_so_xe"]["kiem"](
        db, {"bien_so": "50F-017.37", "ngay_vao_doi": "01/02/2026", "ngay_roi_doi": "01/01/2026"})
    assert any("trước ngày vào đội" in x for x in loi)


def test_cua_canh_bao_khi_vong_doi_va_ngay_roi_noi_nguoc_nhau(db):
    """Không chặn — nhưng không được im: danh mục và mẫu số đang nói hai chuyện khác nhau."""
    from app.services.intake import BO_NAP
    _xe(db, "50F-017.37"); db.flush()
    loi, cb, _ = BO_NAP["ho_so_xe"]["kiem"](
        db, {"bien_so": "50F-017.37", "ngay_vao_doi": "01/02/2025", "ngay_roi_doi": "30/06/2026"})
    assert loi == []
    assert any("vòng đời" in x for x in cb)


def test_cua_noi_ra_khi_xe_da_ban_chua_co_ngay_roi(db):
    from app.services.intake import BO_NAP
    _xe(db, "50F-034.37", lifecycle="da_ban"); db.flush()
    loi, cb, _ = BO_NAP["ho_so_xe"]["kiem"](db, {"bien_so": "50F-034.37"})
    assert any("KHÔNG tính" in x for x in cb)


# ═══════════════════ 5 · Ô TRỐNG PHẢI NÓI AI LÀM (HQ-1b) ═══════════════════
#
# Vòng HQ-1 TÍNH ĐÚNG lý do rồi giấu nó sau một dấu gạch dưới (`_cong_suat_thieu`) với lý lẽ "màn
# hình bỏ qua". Đo trên hệ thật ngay sau khi lên: khối Chủ tịch in ba ô có số và MỘT DẤU GẠCH NGANG
# ở ô công suất, không một chữ nào nói vì sao. Tính sẵn một câu trả lời rồi giấu đi thì cũng bằng
# không tính — nên nhóm phép thử này canh đúng chỗ ấy.
def test_chi_so_GUI_LY_DO_ra_ngoai_hop_dong_chu_khong_giau(db):
    a = _xe(db, "50F-017.37")                      # chưa khai ngày vào đội
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    o = HQ.chi_so(db, KY)
    assert o["cong_suat_khai_thac"] is None
    g = o["cong_suat_thieu"]
    assert g["bo_phan"] == "Đội xe" and g["cua_nhap"]
    assert [x["xe"] for x in g["thieu"]] == ["50F-017.37"]


def test_du_du_lieu_thi_KHONG_con_ly_do_nao(db):
    """Có lý do trong khi ô đã có số thì màn hình hiện 'chờ Đội xe' cạnh một con số thật."""
    a = _xe(db, "50F-017.37", vao=date(2025, 1, 1))
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    o = HQ.chi_so(db, KY)
    assert o["cong_suat_khai_thac"] is not None and o["cong_suat_thieu"] is None


def test_theo_ky_quy_nam_cung_mang_ly_do(db):
    a = _xe(db, "50F-017.37")
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 2, 15))
    for ten in ("thang", "quy", "nam"):
        assert tk[ten]["cong_suat_khai_thac"] is None, ten
        assert tk[ten]["cong_suat_thieu"]["bo_phan"] == "Đội xe", ten


def test_ly_do_cua_quy_TRUNG_ly_do_cua_thang(db):
    """Phép thử này thay cho một phép thử TRANG TRÍ, và lý do đáng ghi lại.

    Bản đầu em viết một phần "gộp danh sách xe của các kỳ con, mỗi xe một lần" và một phép thử canh
    nó. Kiểm ngược: phá phần gộp (chỉ lấy lý do của kỳ cuối) thì phép thử VẪN XANH. Vì `doi_hinh`
    liệt kê xe thiếu theo DANH MỤC XE chứ không theo kỳ, nên danh sách của mọi tháng luôn bằng nhau
    và không bộ dữ liệu nào làm chúng khác nhau được.

    Phép thử không thể đỏ là phép thử chưa được thử. Bỏ cả phần gộp lẫn phép thử ấy; giữ lại đúng
    cái bất biến có thật — và nếu ngày nào `doi_hinh` đổi sang lọc theo kỳ thì chính phép thử này đỏ.
    """
    a = _xe(db, "50F-017.37")
    b = _xe(db, "50H-944.58")
    _chuyen(db, a, "A1", date(2026, 1, 5), date(2026, 1, 7), 1000, 1500, 9_000_000)
    _chuyen(db, b, "B1", date(2026, 2, 5), date(2026, 2, 7), 2000, 2500, 9_000_000)
    db.flush()
    tk = HQ.theo_ky(db, date(2026, 2, 15))
    xe_thang = sorted(x["xe"] for x in tk["thang"]["cong_suat_thieu"]["thieu"])
    xe_quy = sorted(x["xe"] for x in tk["quy"]["cong_suat_thieu"]["thieu"])
    assert xe_thang == xe_quy == ["50F-017.37", "50H-944.58"]
