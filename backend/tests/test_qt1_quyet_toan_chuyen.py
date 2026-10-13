# -*- coding: utf-8 -*-
"""QT-1 · Quyết toán chuyến Mẫu 2: hai tổng CỘNG RA, và chỗ tờ giấy tự mâu thuẫn.

Hai nhóm phép thử ở đây dựng từ HAI BỘ HỒ SƠ THẬT đo ngày 13/10/2026 — không phải ví dụ bịa:

  · 50F-046.22 · Di sản miền Trung · 06–12/10: tờ giấy ghi km đầu 197.935 trong khi ảnh đồng hồ
    và tin Zalo đều 197.435; km cuối 199.768. 199.768−197.435 = 2.333 đúng bằng "TỔNG KM TOUR"
    ghi trên chính tờ ấy. Lệch 500 km.
  · 50F-034.71 · Đà Lạt–Nha Trang · 07–11/10: ô "TỔNG TÀI XẾ CHI" viết tay 1.360.000 trong khi
    công thức in cạnh nó cho 360.000 — cộng nhầm cả công tác phí đã nằm ở tổng bên dưới.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip, TripCost  # noqa: E402
from app.services import quyet_toan_chuyen as QT  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _xe(db, bien="50F-034.71"):
    v = Vehicle(plate=bien)
    db.add(v); db.flush()
    return v


def _chuyen(db, v, kd=220216, kc=221192, **kw):
    t = Trip(ma_phieu=kw.pop("ma", "QT-1"), vehicle_id=v.id, ten_tour="Đà Lạt – Nha Trang",
             ngay_di=kw.pop("di", date(2026, 10, 7)), ngay_ve=kw.pop("ve", date(2026, 10, 11)),
             km_dau=kd, km_cuoi=kc, **kw)
    db.add(t); db.flush()
    return t


def _chi(db, t, kind, tien, tra_bang="", lit=0.0):
    c = TripCost(trip_id=t.id, kind=kind, amount=tien, tra_bang=tra_bang, lit=lit)
    db.add(c); db.flush()
    return c


def _bo_2(db):
    """Dựng đúng bộ hồ sơ 50F-034.71 ngày 07–11/10/2026."""
    v = _xe(db)
    t = _chuyen(db, v)
    _chi(db, t, "giu_xe", 360_000, "tai_xe_tien_mat")
    _chi(db, t, "cong_tac_phi", 1_000_000, "tai_khoan_cong_ty")
    _chi(db, t, "dau", 8_942_360, "the_cong_ty", lit=293.0)
    _chi(db, t, "cau_duong", 956_000, "tai_khoan_cong_ty")
    return t


# ═══════════════════ 1 · HAI TỔNG CỘNG RA ═══════════════════
def test_hai_tong_cong_ra_dung_bo_ho_so_that(db):
    """Đây đúng là ô mà tờ giấy thật ghi 1.360.000 thay vì 360.000."""
    t = _bo_2(db)
    g = QT.tong(db, t)
    assert g["tai_xe_chi"] == 360_000, "chỉ phí gửi xe — công tác phí KHÔNG phải tài xế ứng"
    assert g["cong_ty_chi"] == 1_000_000 + 8_942_360 + 956_000
    assert g["tong_chi_phi_tour"] == 11_258_360
    assert g["chua_khai_ai_tra"] == 0


def test_cong_tac_phi_khong_duoc_dem_vao_tai_xe_chi(db):
    """Lỗi thật của tờ giấy: cộng công tác phí vào 'tài xế chi' trong khi nó đã ở tổng bên dưới."""
    t = _bo_2(db)
    g = QT.tong(db, t)
    assert g["tai_xe_chi"] != 1_360_000
    assert g["tai_xe_chi"] + g["cong_ty_chi"] == g["tong_chi_phi_tour"], "không khoản nào đếm hai lần"


def test_khoan_chua_khai_ai_tra_KHONG_bi_don_vao_cong_ty(db):
    v = _xe(db); t = _chuyen(db, v)
    _chi(db, t, "giu_xe", 30_000, "tai_xe_tien_mat")
    _chi(db, t, "khac", 500_000)                       # chưa ai khai ai trả
    g = QT.tong(db, t)
    assert g["tai_xe_chi"] == 30_000 and g["cong_ty_chi"] == 0
    assert g["chua_khai_ai_tra"] == 500_000, "để riêng, không đoán về bên nào"
    assert g["tong_chi_phi_tour"] == 530_000, "vẫn nằm trong tổng chi phí tour"


def test_tam_ung_hoan_tra_KHONG_vao_tong_chi_phi_tour(db):
    """Tiền đi qua tay tài xế không phải chi phí của chuyến — cộng vào là đếm hai lần vào giá vốn."""
    v = _xe(db)
    t = _chuyen(db, v, tam_ung=2_000_000, hoan_tra=100_000, chi_them=50_000)
    _chi(db, t, "giu_xe", 360_000, "tai_xe_tien_mat")
    g = QT.tong(db, t)
    assert g["tong_chi_phi_tour"] == 360_000
    assert g["tai_xe_con_nhan"] == 360_000 + 50_000 - 2_000_000 - 100_000


# ═══════════════════ 2 · TỜ GIẤY TỰ MÂU THUẪN ═══════════════════
def test_km_tren_giay_lech_voi_km_dau_cuoi_thi_CHAN(db):
    """Bộ 50F-046.22: giấy ghi km đầu 197.935 nhưng tổng km 2.333 — lệch 500 km."""
    v = _xe(db, "50F-046.22")
    t = _chuyen(db, v, kd=197_935, kc=199_768, ma="QT-2",
                di=date(2026, 10, 6), ve=date(2026, 10, 12))
    _chi(db, t, "dau", 18_353_807, "the_cong_ty", lit=599.771)
    d = QT.kiem(db, t, km_tour_tren_giay=2333)
    do = [x for x in d if x["muc"] == "do" and x["o"] == "km"]
    assert do, "phải chặn: 199.768−197.935 = 1.833 ≠ 2.333 ghi trên giấy"
    assert "500" in do[0]["noi"], "phải nói RÕ lệch bao nhiêu km"


def test_km_dung_thi_khong_bao_gi(db):
    v = _xe(db, "50F-046.22")
    t = _chuyen(db, v, kd=197_435, kc=199_768, ma="QT-3")
    _chi(db, t, "dau", 18_353_807, "the_cong_ty", lit=599.771)
    assert QT.km_tour(t) == 2333
    assert [x for x in QT.kiem(db, t, km_tour_tren_giay=2333) if x["o"] == "km"] == []


def test_km_cuoi_nho_hon_km_dau_thi_chan(db):
    v = _xe(db); t = _chuyen(db, v, kd=221_192, kc=220_216)
    _chi(db, t, "dau", 1, "the_cong_ty")
    assert any(x["muc"] == "do" and x["o"] == "km" for x in QT.kiem(db, t))


def test_khong_co_khoan_chi_nao_thi_chan(db):
    v = _xe(db); t = _chuyen(db, v)
    assert any(x["muc"] == "do" and x["o"] == "chi_phi" for x in QT.kiem(db, t))


# ═══════════════════ 3 · TUYẾN KÝ BỐN BƯỚC ═══════════════════
def test_phai_gui_di_truoc_khi_ai_do_ky_duoc(db):
    t = _bo_2(db)
    assert t.qt_trang_thai == "nhap"
    assert QT.co_the_ky(t, "dieu_hanh", "tp_dh"), "tờ còn ở nháp thì chưa ký được"


def test_ky_dung_thu_tu_va_ghi_ai_ky_luc_nao(db):
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    assert t.qt_trang_thai == "cho_dieu_hanh"
    QT.ky(db, t, "dieu_hanh", "nv_dieu_hanh", "tp_dh")
    assert t.qt_trang_thai == "cho_ke_toan"
    assert t.qt_dieu_hanh == "nv_dieu_hanh" and t.qt_dieu_hanh_luc is not None
    QT.ky(db, t, "ke_toan", "chi_ketoan", "ketoan")
    QT.ky(db, t, "tgd", "anh_hieu", "tgd")
    assert t.qt_trang_thai == "da_duyet"
    assert [x["nguoi"] for x in QT.xem(db, t)["ky"]] == ["nv_dieu_hanh", "chi_ketoan", "anh_hieu"]


def test_KHONG_nhay_coc_duoc_buoc_ky(db):
    """Mỗi bước kiểm một thứ khác nhau — Kế toán ký trước Điều hành là ký một tờ chưa ai đối chiếu."""
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    assert QT.co_the_ky(t, "ke_toan", "ketoan"), "chưa tới lượt Kế toán"
    with pytest.raises(ValueError):
        QT.ky(db, t, "tgd", "anh_hieu", "tgd")


def test_sai_vai_thi_khong_ky_duoc(db):
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    assert QT.co_the_ky(t, "dieu_hanh", "ketoan"), "vai kế toán không ký bước điều hành"


def test_con_diem_CHAN_thi_khong_gui_di_duoc(db):
    v = _xe(db); t = _chuyen(db, v, kd=221_192, kc=220_216)
    _chi(db, t, "dau", 1, "the_cong_ty")
    with pytest.raises(ValueError):
        QT.gui_di(db, t, "doixe01")


def test_tra_lai_XOA_HET_chu_ky_da_co(db):
    """Giữ chữ ký cũ là giữ một chữ ký cho nội dung người ấy chưa từng đọc."""
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    QT.ky(db, t, "dieu_hanh", "nv_dieu_hanh", "tp_dh")
    QT.ky(db, t, "ke_toan", "chi_ketoan", "ketoan")
    QT.tra_lai(db, t, "Km đầu lệch với ảnh đồng hồ", "anh_hieu")
    assert t.qt_trang_thai == "tra_lai"
    assert t.qt_dieu_hanh == "" and t.qt_ke_toan == ""
    assert t.qt_dieu_hanh_luc is None and t.qt_ke_toan_luc is None
    assert "Km đầu lệch" in t.qt_tra_lai_ly_do and "anh_hieu" in t.qt_tra_lai_ly_do


def test_tra_lai_BAT_BUOC_co_ly_do(db):
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    with pytest.raises(ValueError):
        QT.tra_lai(db, t, "   ", "anh_hieu")


def test_tra_lai_roi_gui_lai_thi_di_lai_tu_dau(db):
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    QT.ky(db, t, "dieu_hanh", "nv_dieu_hanh", "tp_dh")
    QT.tra_lai(db, t, "sửa km", "chi_ketoan")
    QT.gui_di(db, t, "doixe01")
    assert t.qt_trang_thai == "cho_dieu_hanh"
    assert t.qt_tra_lai_ly_do == ""


def test_da_du_chu_ky_thi_khong_ky_them(db):
    t = _bo_2(db)
    QT.gui_di(db, t, "doixe01")
    for b, n, v in (("dieu_hanh", "a", "tp_dh"), ("ke_toan", "b", "ketoan"), ("tgd", "c", "tgd")):
        QT.ky(db, t, b, n, v)
    assert QT.co_the_ky(t, "tgd", "tgd")


# ═══════════════════ 4 · MỘT TỜ ĐỂ MÀN HÌNH IN RA ═══════════════════
def test_xem_tra_du_khuon_mau_2(db):
    t = _bo_2(db)
    o = QT.xem(db, t)
    for k in ("bien_so", "ten_tour", "hdv", "hanh_trinh", "ngay_di", "ngay_ve", "so_ngay",
              "km_dau", "km_cuoi", "km_tour", "tam_ung", "hoan_tra", "chi_them", "phu_thu",
              "bc_tinh_trang_xe", "tong", "qt_trang_thai", "ky", "diem_lech"):
        assert k in o, k
    assert o["so_ngay"] == 5 and o["km_tour"] == 976
    assert o["tong"]["tai_xe_chi"] == 360_000
    assert len(o["ky"]) == 3


# ───────────────────────────────────────────────────────────────────────────────────────────────
# CỬA KHAI `tra_bang`. Phép thử nhóm này không thử phép tính — nó thử rằng CÓ CHỖ ĐỂ KHAI.
#
# Vì sao tách riêng: bản đầu của QT-1 tính đúng cả hai tổng, in đúng lời chặn "x đ chưa khai ai
# trả", rồi dặn người đọc "mở từng dòng chi phí mà chọn" — trong khi `tra_bang` KHÔNG có cửa nào,
# không ở biểu nhập, không ở đường PUT, không ở dữ liệu trả về màn hình. Lời chặn ấy là một ngõ
# cụt: người đọc được bảo phải khai, mà không có chỗ nào để khai, nên con số "chưa khai" ở lại
# vĩnh viễn và hai tổng của Mẫu 2 vĩnh viễn không tách được. Một phép tính đúng mà không có cửa
# nhập thì bằng không có phép tính.
# ───────────────────────────────────────────────────────────────────────────────────────────────

def test_xem_tra_ve_TUNG_DONG_chi_phi_kem_o_khai_tra_bang(db):
    t = _bo_2(db)
    o = QT.xem(db, t)
    assert "chi_phi" in o, "Màn hình không nhận được dòng chi phí nào thì không có gì để khai"
    assert len(o["chi_phi"]) == o["tong"]["so_khoan"]
    for d in o["chi_phi"]:
        for k in ("id", "kind", "kind_ten", "amount", "tra_bang", "tra_bang_ten"):
            assert k in d, k
    # Và danh mục để chọn cũng phải đi kèm, nếu không màn hình lại chép lại một bảng thứ hai.
    assert set(o["tra_bang_danh_muc"]) == set(QT.TRA_BANG)


def test_khai_tra_bang_thi_so_CHUYEN_tu_chua_khai_sang_dung_tong(db):
    v = _xe(db)
    t = _chuyen(db, v)
    c = _chi(db, t, "giu_xe", 100_000)          # để trống: chưa khai
    assert QT.tong(db, t)["chua_khai_ai_tra"] == 100_000
    assert QT.tong(db, t)["tai_xe_chi"] == 0

    c.tra_bang = "tai_xe_tien_mat"; db.flush()   # đúng việc cửa sửa dòng chi phí làm
    g = QT.tong(db, t)
    assert g["chua_khai_ai_tra"] == 0 and g["tai_xe_chi"] == 100_000 and g["cong_ty_chi"] == 0

    c.tra_bang = "tai_khoan_cong_ty"; db.flush()
    g = QT.tong(db, t)
    assert g["chua_khai_ai_tra"] == 0 and g["tai_xe_chi"] == 0 and g["cong_ty_chi"] == 100_000
    # Tổng chi phí tour không đổi dù khai ai trả — đó là điều phải đúng, nếu không thì giá vốn
    # của chuyến phụ thuộc vào việc ai đó đã kịp khai hay chưa.
    assert g["tong_chi_phi_tour"] == 100_000


def test_khai_tra_bang_xong_thi_loi_canh_bao_TU_MAT(db):
    v = _xe(db)
    t = _chuyen(db, v)
    c = _chi(db, t, "giu_xe", 100_000)
    assert any(x["o"] == "tra_bang" for x in QT.kiem(db, t))
    c.tra_bang = "tai_xe_tien_mat"; db.flush()
    assert not any(x["o"] == "tra_bang" for x in QT.kiem(db, t)), \
        "Khai xong mà lời chặn còn ở lại thì người khai không biết mình đã xong"
