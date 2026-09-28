"""NT-5 · Cửa nắn dòng ngoại tệ thiếu tỷ giá — Chủ tịch quyết 27/9/2026, SAU KHI ĐÃ ĐO.

═══════════════════════════════════════════════════════════════════════════════════════════════
CỬA NÀY KHÔNG GIỐNG CÁI ĐÃ HÌNH DUNG TRƯỚC KHI ĐO
═══════════════════════════════════════════════════════════════════════════════════════════════
Sáng 27/9, khi chưa chạy `soat_ngoai_te` trên dữ liệu thật, cửa nắn được hình dung là "sửa từng
dòng đã ghi sai quy ước, mỗi dòng một người ký". Đo thật thì `sai_bo_nhan = 0` — KHÔNG dòng nào
ghi sai quy ước. Cả 61 dòng chỉ THIẾU TỶ GIÁ, nên `actual` = 0.

Việc thật là "nhập 11 con số tỷ giá rồi máy nhân lại", không phải "sửa 61 con số". Bộ phép thử
này canh đúng cái hình MỚI ấy, và canh bốn chỗ mà một cửa sửa tiền dễ bị nới nhất.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.models.ty_gia import TyGia
from app.models.vietrip import TourCostLine
from app.services import nan_ngoai_te as NAN

CUOI_THANG = dt.date(2026, 3, 31)
CAD, PAX, TY_GIA = 185.0, 1, 19_000.0


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    s.add_all([User(username="nvdh", full_name="NV Điều hành", role="nv_dh", password_hash="x"),
               User(username="tpdh", full_name="TP Điều hành", role="tp_dh", password_hash="x"),
               User(username="ketoan", full_name="Kế toán", role="ketoan", password_hash="x")])
    s.commit()
    t = Tour(code="DVL-VISA032026-025E", name="Visa Canada", tour_type="le_noi_dia",
             start_date=CUOI_THANG, end_date=CUOI_THANG, operator_id=1, status="ket_thuc",
             price_per_pax=0, planned_pax=PAX, seats_open=PAX)
    s.add(t); s.commit()
    return s, t


def _dong(db, t, **kw):
    """Hình THẬT của dòng kho cũ: có đồng tiền và đơn giá gốc, KHÔNG có tỷ giá, `actual` = 0."""
    d = dict(tour_id=t.id, line_no=len(db.execute(select(TourCostLine)).scalars().all()) + 1,
             description="Phí LSQ Phí (CAD) – NGUYEN TUYET NHI", supplier_name="",
             cost_kind="co_dinh", tien_te="CAD", so_tien_goc=CAD, ty_gia=None, ngay_ty_gia=None,
             qty=PAX, coef=1, unit_price=None, actual=0,
             source="kho_cu_h1_2026", status="hd", updated_by="chutich")
    d.update(kw)
    l = TourCostLine(**d)
    db.add(l); db.commit(); db.refresh(l)
    return l


def _so(db, **kw):
    d = dict(tien_te="CAD", ngay=CUOI_THANG, ty_gia=TY_GIA, nguon="Vietcombank",
             loai_gia="ban_ra", nguoi_nhap="ketoan")
    d.update(kw)
    r = TyGia(**d)
    db.add(r); db.commit(); db.refresh(r)
    return r


def _nguoi(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


# ═══════════════ 1. TỶ GIÁ LẤY TỪ SỔ — CỬA NÀY KHÔNG CÓ Ô GÕ TỶ GIÁ ═══════════════

def test_nt5_chua_co_ty_gia_trong_so_thi_KHONG_nan_duoc_va_noi_thieu_gi():
    """Ranh giới 09/9/2026: máy không gõ hộ số liệu. Chưa có tỷ giá thì dừng, và nói ra thiếu cặp
    (đồng tiền × ngày) nào — đếm CẶP chứ không đếm dòng."""
    db, t = _db()
    _dong(db, t); _dong(db, t)
    kq = NAN.xem_truoc(db)
    assert kq["dem"] == {"nan_duoc": 0, "vuong": 2}
    assert kq["dem_vuong"]["thieu_ty_gia"] == 2
    assert kq["can_ty_gia"] == [{"tien_te": "CAD", "ngay": "2026-03-31", "so_dong": 2}]


def test_nt5_cua_nan_KHONG_nhan_mot_ty_gia_go_thang():
    """Phép thử đọc chữ ký hàm: `nan_mot_dong` nhận `ty_gia_id` (một dòng CÓ THẬT trong sổ), không
    nhận một con số. Đổi thành số là mở đường cho 61 dòng mang 61 tỷ giá không ai truy được."""
    import inspect
    tham = inspect.signature(NAN.nan_mot_dong).parameters
    assert "ty_gia_id" in tham and "ty_gia" not in tham


def test_nt5_lay_ty_gia_cua_NGAY_KHAC_hoac_DONG_TIEN_KHAC_thi_chan():
    db, t = _db()
    l = _dong(db, t)
    khac_ngay = _so(db, ngay=dt.date(2026, 4, 30))
    khac_tien = _so(db, tien_te="USD", ty_gia=25_500.0)
    for r in (khac_ngay, khac_tien):
        with pytest.raises(Exception) as e:
            NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ")
        assert "ngày khác" in str(getattr(e.value, "detail", e.value)) or \
               "cần" in str(getattr(e.value, "detail", e.value))


def test_nt5_HAI_nguon_cung_ngay_thi_NGUOI_chon_may_khong_chon():
    """Sổ cho phép "Vietcombank bán ra" và "hợp đồng đối tác" khác nhau cùng ngày, và phải khác
    nhau. Máy lấy bừa một dòng là tự đặt ra một sự thật."""
    db, t = _db()
    _dong(db, t)
    _so(db, nguon="Vietcombank", ty_gia=19_000.0)
    _so(db, nguon="hợp đồng đối tác", ty_gia=19_120.0)
    kq = NAN.xem_truoc(db)
    assert kq["dem"]["nan_duoc"] == 0 and kq["dem_vuong"]["nhieu_nguon"] == 1
    assert len(kq["vuong"][0]["nguon_ty_gia"]) == 2


# ═══════════════ 2. CHUYẾN ĐÃ ĐÓNG SỐ — CỬA NÀY KHÔNG TỰ MỞ KHOÁ ═══════════════

def test_nt5_chuyen_da_dong_so_thi_KHONG_nan_lang_le():
    """Đo 27/9/2026: cả 61 dòng nằm trên chuyến `da_dong_so`. Tự mở khoá là xoá mất ranh giới giữa
    'số đang soạn' và 'số đã chốt' — thứ đắt nhất của cả phân hệ quyết toán."""
    db, t = _db()
    t.status = "da_dong_so"; db.commit()
    l = _dong(db, t); _so(db)
    kq = NAN.xem_truoc(db)
    assert kq["dem_vuong"]["chuyen_da_dong"] == 1
    assert "Kế toán" in kq["vuong"][0]["vuong_ten"]

    r = db.execute(select(TyGia)).scalars().first()
    with pytest.raises(Exception) as e:
        NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ")
    assert "trả lại" in str(getattr(e.value, "detail", e.value))
    db.refresh(l)
    assert l.actual == 0 and l.ty_gia is None, "đã chạm vào dòng của chuyến đã đóng số"


# ═══════════════ 3. MỘT CHỦ HỒ SƠ — KHÔNG THÊM NGOẠI LỆ THEO VAI TRÒ ═══════════════

def test_nt5_khong_phai_chu_ho_so_thi_khong_nan_duoc_KE_CA_Ke_toan():
    """Luật 'một chủ hồ sơ' 26/9/2026 không có đường thoát theo vai trò. Cửa nắn không được là
    ngoại lệ đầu tiên — nhất là khi nó sửa thẳng con số tiền."""
    db, t = _db()
    l = _dong(db, t); r = _so(db)
    for ai in ("tpdh", "ketoan"):
        with pytest.raises(Exception) as e:
            NAN.nan_mot_dong(db, _nguoi(db, ai), l, r.id, "nắn kho cũ")
        assert "chủ hồ sơ" in str(getattr(e.value, "detail", e.value))
    db.refresh(l)
    assert l.actual == 0


def test_nt5_khong_co_ly_do_thi_chan():
    db, t = _db()
    l = _dong(db, t); r = _so(db)
    with pytest.raises(Exception) as e:
        NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "   ")
    assert "lý do" in str(getattr(e.value, "detail", e.value))


# ═══════════════ 4. KHÔNG CHẠM DÒNG ĐÃ CÓ SỐ ═══════════════

@pytest.mark.parametrize("kw,vi_sao", [
    ({"actual": 1_000_000}, "dòng đã có số thực chi"),
    ({"ty_gia": 19_000.0}, "dòng đã có tỷ giá"),
    ({"so_tien_goc": None}, "dòng không có đơn giá đồng gốc"),
    ({"status": "huy"}, "dòng đã huỷ"),
    ({"tien_te": ""}, "dòng không khai ngoại tệ"),
])
def test_nt5_ngoai_pham_vi_thi_chan(kw, vi_sao):
    db, t = _db()
    l = _dong(db, t, **kw); r = _so(db)
    assert NAN.xem_truoc(db)["dem"]["nan_duoc"] == 0, vi_sao
    with pytest.raises(Exception) as e:
        NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ")
    assert "phạm vi" in str(getattr(e.value, "detail", e.value))


# ═══════════════ 5. NẮN ĐÚNG THÌ RA ĐÚNG SỐ, VÀ ĐỂ LẠI DẤU VẾT ═══════════════

def test_nt5_nan_xong_ra_dung_phep_nhan_va_dung_don_gia_VND():
    db, t = _db()
    l = _dong(db, t); r = _so(db)
    kq = NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ T1–T6/2026")
    db.refresh(l)
    assert l.ty_gia == TY_GIA and l.ngay_ty_gia == CUOI_THANG
    assert l.unit_price == round(CAD * TY_GIA, 2) == 3_515_000
    assert l.actual == 3_515_000
    assert kq["truoc"]["actual"] == 0 and kq["sau"]["actual"] == 3_515_000


def test_nt5_theo_khach_van_nhan_so_luong_dung_mot_luat_voi_calc_actual():
    db, t = _db()
    l = _dong(db, t, cost_kind="theo_khach", qty=43, coef=1)
    r = _so(db)
    NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn")
    db.refresh(l)
    assert l.actual == round(CAD * TY_GIA) * 43


def test_nt5_ghi_chu_noi_ro_TY_GIA_CUOI_THANG_khong_phai_ngay_khoi_hanh():
    """Chủ tịch chọn 'ngày khởi hành', nhưng đo ra 11 ngày đều là CUỐI THÁNG do bộ nạp đặt khi tệp
    gốc chỉ có tháng. Viết nhãn sai là để lại cho người ba tháng sau một câu trả lời sai cho câu
    hỏi 'con số này ở đâu ra'."""
    db, t = _db()
    l = _dong(db, t); r = _so(db)
    NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ")
    db.refresh(l)
    assert "tỷ giá cuối tháng" in l.note
    assert "khởi hành" not in l.note
    assert "Vietcombank" in l.note and "nắn kho cũ" in l.note
    assert l.updated_by == "nvdh"
    assert NAN.xem_truoc(db)["nhan_ngay"] == "tỷ giá cuối tháng"


def test_nt5_man_hinh_xem_truoc_cung_noi_dung_nhan_ay():
    db, t = _db()
    _dong(db, t); _so(db)
    kq = NAN.xem_truoc(db)
    assert "CUỐI THÁNG" in kq["luu_y"] and "không phải ngày khởi hành" in kq["luu_y"]
    assert kq["nan_duoc"][0]["nhan_ngay"] == "tỷ giá cuối tháng"


def test_nt5_de_lai_mot_dong_nhat_ky_KHONG_the_xoa():
    db, t = _db()
    l = _dong(db, t); r = _so(db)
    NAN.nan_mot_dong(db, _nguoi(db, "nvdh"), l, r.id, "nắn kho cũ")
    from app.models.core import AuditLog
    a = db.execute(select(AuditLog).where(AuditLog.action == "nan_ngoai_te")).scalars().all()
    assert len(a) == 1 and a[0].actor == "nvdh"


# ═══════════════ 6. XEM TRƯỚC LÀ CHỈ ĐỌC ═══════════════

def test_nt5_xem_truoc_KHONG_sua_mot_dong_du_lieu_nao():
    db, t = _db()
    l = _dong(db, t); _so(db)
    truoc = (l.actual, l.ty_gia, l.ngay_ty_gia, l.unit_price, l.note)
    NAN.xem_truoc(db)
    db.refresh(l)
    assert (l.actual, l.ty_gia, l.ngay_ty_gia, l.unit_price, l.note) == truoc


def test_nt5_xem_truoc_cong_TONG_DONG_GOC_de_biet_quy_mo():
    db, t = _db()
    _dong(db, t); _dong(db, t, tien_te="USD", so_tien_goc=4.0)
    kq = NAN.xem_truoc(db)
    assert kq["tong_dong_goc_chua_quy_doi"] == {"CAD": CAD, "USD": 4.0}


def test_nt5_so_RONG_phai_noi_ra_la_rong():
    db, _ = _db()
    assert "chưa chắc đã sạch" in NAN.xem_truoc(db)["luu_y"]


# ═══════════════ 7. VIỆC 4 — NHẮC, KHÔNG CHẶN (Chủ tịch chốt 27/9/2026) ═══════════════

def test_nt5_dong_viet_phep_tinh_ngoai_te_vao_MO_TA_thi_bi_NHAC():
    """Hình thật của 13 dòng tour ĐANG CHẠY, đo 27/9/2026: người nhập tự nhân ngoài hệ rồi gõ số
    VND, bốn ô ngoại tệ bỏ trống. Mỗi dòng như thế là một tỷ giá không ai truy được."""
    from app.services import settlement as ST
    db, t = _db()
    _dong(db, t, tien_te="", so_tien_goc=None, actual=117_036_500, unit_price=117_036_500,
          description="Tổng chi phí (bao gồm phụ thu): 4,341 USD x 26,500 + BANK FEE 2tr",
          source="vietrip")
    c = ST.checks(db, t)
    nhac = [x for x in c if "bốn ô ngoại tệ bỏ trống" in x["msg"]]
    assert len(nhac) == 1
    assert nhac[0]["level"] == "warn", "Chủ tịch chọn NHẮC, không CHẶN"
    assert "USD" in nhac[0]["msg"]


def test_nt5_nhac_KHONG_chan_dong_so():
    """`warn` không được biến thành `block`: chặn thì Điều hành kẹt ngay hôm sau với những dòng mô
    tả chỉ vô tình có ba chữ cái trùng mã đồng tiền."""
    from app.services import settlement as ST
    db, t = _db()
    _dong(db, t, tien_te="", so_tien_goc=None, actual=1_000_000, unit_price=1_000_000,
          description="Thanh toan 500 USD", source="vietrip")
    assert not [x for x in ST.checks(db, t) if x["level"] == "block"]


def test_nt5_dong_DA_khai_du_bon_o_thi_khong_bi_nhac():
    from app.services import settlement as ST
    db, t = _db()
    _dong(db, t, tien_te="USD", so_tien_goc=4.0, ty_gia=25_500.0, ngay_ty_gia=CUOI_THANG,
          unit_price=102_000, actual=102_000, description="Phí TLS/VFS Phí (USD)")
    assert not [x for x in ST.checks(db, t) if "bốn ô ngoại tệ bỏ trống" in x["msg"]]


def test_nt5_HKD_ho_kinh_doanh_khong_bi_nhac_oan():
    """Cùng luật với bộ soát: mã trùng chữ viết tắt tiếng Việt chỉ tính khi nằm trong MÔ TẢ."""
    from app.services import settlement as ST
    db, t = _db()
    _dong(db, t, tien_te="", so_tien_goc=None, actual=308_000, unit_price=28_000,
          description="Ăn sáng tại sân bay", supplier_name="HKD NHỮNG CHÀNG TRAI", source="vietrip")
    assert not [x for x in ST.checks(db, t) if "bốn ô ngoại tệ bỏ trống" in x["msg"]]
