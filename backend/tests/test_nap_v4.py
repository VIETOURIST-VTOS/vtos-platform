"""V4 – mười bốn bộ nạp phòng ban còn thiếu (lệnh giao việc 08/9/2026).

Bộ test này không kiểm "hàm chạy được". Nó canh đúng những chỗ mà một bộ nạp làm hỏng số của công ty
mà bảng vẫn trông hợp lý:

  1. Ô TRỐNG KHÔNG THÀNH SỐ 0. Kiểm trên cả bốn bảng mới: lead marketing, hoa hồng, thực lĩnh, thù lao
     hướng dẫn viên. Đây là quy tắc số 4 của lệnh, và là lỗi đã làm sổ báo lãi 100% trên 2,65 tỷ.
  2. NẠP HAI LẦN KHÔNG THÀNH HAI BẢN. Kiểm khóa chống trùng của từng bộ nạp bằng cách nạp lại đúng
     tệp cũ – cách người dùng thật làm hỏng dữ liệu, không phải cách lập trình viên tưởng tượng.
  3. HÓA ĐƠN TRÙNG SỐ CỦA HAI NHÀ CUNG CẤP LÀ HAI HÓA ĐƠN. Khóa phải là bộ ba MST + ký hiệu + số.
  4. CHI PHÍ CỦA CẢ ĐỘI KHÔNG GẮN VÀO MỘT CHIẾC. Lãi vay gán cho một xe là một báo cáo nói dối về
     chiếc xe đó và về cả 20 chiếc còn lại.
  5. KHÔNG NẠP ĐÈ LÊN CHỮ KÝ. Bảng lương kỳ đã có xác nhận của Kế toán thì từ chối; khấu hao kỳ mà
     VTOS tự tính được thì từ chối.
  6. BẢO HIỂM CHO CỘNG TÁC VIÊN LÀ MỘT CÂU HỎI, KHÔNG PHẢI MỘT DÒNG DỮ LIỆU.
  7. HẠN GIẤY TỜ ĐỂ TRỐNG NGHĨA LÀ CHƯA BIẾT, không phải còn hạn.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_napv4.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

MOI = ("nhien_lieu", "phi_cau_duong", "bao_duong", "dang_kiem", "chi_phi_ky_doi_xe",
       "chi_marketing_kenh", "doanh_so_tu_van_vien", "thu_lao_hdv", "hoa_don_dau_vao",
       "bao_hiem_ky", "bang_luong", "tai_san_co_dinh", "cong_cu_dung_cu", "khau_hao_ky")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def nap(db, loai, rows, boi="ketoan", bo_qua=False):
    from app.services import intake as IN
    return IN.nap(db, loai, rows, boi, bo_qua_dong_loi=bo_qua, ten_tep="test.xlsx", nguon="nap_tep")


def loi_dong(kq, i=0):
    return " · ".join(kq["dong"][i]["loi"])


# ====================== KHAI BÁO ======================
def test_du_muoi_bon_bo_nap_va_khai_bao_day_du():
    from app.services.intake import BO_NAP, VAI_TRO, PHONG_BAN
    from app.services.nhap_lieu import khai_bao_du
    for k in MOI:
        assert k in BO_NAP, f"thiếu bộ nạp {k}"
        assert khai_bao_du(BO_NAP[k]) == [], f"{k} khai thiếu"
        assert k in VAI_TRO and k in PHONG_BAN, f"{k} chưa khai vai trò / phòng ban"


def test_nhan_vien_khong_tai_tep_duoc_nhung_van_nhap_tay_duoc():
    """Quy tắc P4: tải tệp hàng loạt hẹp hơn nhập tay đúng một bậc, cho những bộ nạp chạm vào tiền."""
    from app.services.intake import duoc_nap, duoc_nap_tep
    assert duoc_nap("hoa_don_dau_vao", "ketoan") and duoc_nap_tep("hoa_don_dau_vao", "ketoan")
    assert not duoc_nap("hoa_don_dau_vao", "hcns")          # hóa đơn là sổ của Kế toán
    assert duoc_nap("bang_luong", "hcns")
    assert not duoc_nap("bang_luong", "ketoan")             # Kế toán xác nhận, không nhập hộ


# ====================== ĐỘI XE ======================
def _dau(ma="TD-001", **kw):
    return {"ma_gd": ma, "thoi_diem": "05/08/2026", "bien_so": "50F-009.60",
            "so_tien": "8.460.000", "lit": "423", "mo_ta": "Đổ dầu Petrolimex", **kw}


def test_nhien_lieu_nap_va_gan_dung_xe(db):
    kq = nap(db, "nhien_lieu", [_dau("TD-101")])
    assert kq["da_nap"] == 1, loi_dong(kq)
    from app.models.fleet import ExternalTxn
    t = db.execute(select(ExternalTxn).where(ExternalTxn.ma_gd == "TD-101")).scalars().first()
    assert t.source == "the_dau" and t.vehicle_id is not None and t.khop == "chua_khop"
    assert t.lit == 423


def test_nhien_lieu_nap_lai_khong_thanh_hai_ban(db):
    nap(db, "nhien_lieu", [_dau("TD-102")])
    lai = nap(db, "nhien_lieu", [_dau("TD-102")])
    assert lai["da_nap"] == 0 and lai["da_co"] == 1


def test_nhien_lieu_bien_la_van_ghi_nhung_bao_chua_gan_xe(db):
    kq = nap(db, "nhien_lieu", [_dau("TD-103", bien_so="99Z-999.99")])
    assert kq["da_nap"] == 1
    assert any("chưa nhận ra xe" in c.lower() for c in kq["dong"][0]["canh_bao"])


def test_nhien_lieu_khong_nap_giao_dich_khong_dong(db):
    kq = nap(db, "nhien_lieu", [_dau("TD-104", so_tien="0")])
    assert kq["da_nap"] == 0 and "lớn hơn 0" in loi_dong(kq)


def test_phi_cau_duong_di_vao_cung_bang_nhung_khac_nguon(db):
    nap(db, "phi_cau_duong", [{"ma_gd": "EP-201", "thoi_diem": "05/08/2026",
                               "bien_so": "50F-009.60", "so_tien": "1.180.000", "mo_ta": "Trạm Dầu Giây"}])
    from app.models.fleet import ExternalTxn
    t = db.execute(select(ExternalTxn).where(ExternalTxn.ma_gd == "EP-201")).scalars().first()
    assert t.source == "epass"
    # Cùng mã ở nguồn KHÁC vẫn là giao dịch khác – khóa là nguồn + mã, không phải mã một mình.
    assert nap(db, "nhien_lieu", [_dau("EP-201")])["da_nap"] == 1


def test_bao_duong_phai_quy_ve_mot_chiec(db):
    kq = nap(db, "bao_duong", [{"bien_so": "99Z-999.99", "ngay": "12/08/2026",
                                "noi_dung": "Thay dầu máy", "so_tien": "2.000.000"}])
    assert kq["da_nap"] == 0 and "không tìm thấy xe" in loi_dong(kq).lower()


def test_bao_duong_thieu_km_van_nap_nhung_canh_bao(db):
    kq = nap(db, "bao_duong", [{"bien_so": "50F-009.60", "ngay": "12/08/2026",
                                "noi_dung": "Thay lọc gió", "so_tien": "800.000"}])
    assert kq["da_nap"] == 1
    assert any("km" in c.lower() for c in kq["dong"][0]["canh_bao"])
    # Nạp lại đúng dòng đó: xe + ngày + nội dung là khóa.
    assert nap(db, "bao_duong", [{"bien_so": "50F-009.60", "ngay": "12/08/2026",
                                  "noi_dung": "Thay lọc gió", "so_tien": "800.000"}])["da_co"] == 1


def test_dang_kiem_khong_han_thi_khong_duoc_hieu_la_con_han(db):
    kq = nap(db, "dang_kiem", [{"bien_so": "50E-957.34", "so_giay": "AB-777"}])
    assert kq["da_nap"] == 1
    assert any("chưa đủ dữ liệu" in c for c in kq["dong"][0]["canh_bao"])
    from app.models.fleet import VehicleDocument
    g = db.execute(select(VehicleDocument).where(VehicleDocument.number == "AB-777")).scalars().first()
    assert g.expires_on is None and g.kind == "dang_kiem"


def test_dang_kiem_giay_moi_tat_giay_cu_nhung_khong_xoa(db):
    from app.models.fleet import VehicleDocument
    nap(db, "dang_kiem", [{"bien_so": "50E-955.31", "so_giay": "CU-1",
                           "ngay_cap": "01/01/2026", "ngay_het_han": "01/07/2026"}])
    nap(db, "dang_kiem", [{"bien_so": "50E-955.31", "so_giay": "MOI-1",
                           "ngay_cap": "01/07/2026", "ngay_het_han": "01/01/2027"}])
    cu = db.execute(select(VehicleDocument).where(VehicleDocument.number == "CU-1")).scalars().first()
    moi = db.execute(select(VehicleDocument).where(VehicleDocument.number == "MOI-1")).scalars().first()
    assert cu is not None and cu.active is False        # còn nguyên trong sổ, chỉ thôi hiệu lực
    assert moi.active is True


def test_chi_phi_ca_doi_khong_duoc_gan_vao_mot_chiec(db):
    kq = nap(db, "chi_phi_ky_doi_xe", [{"ky": "2026-08", "nhom": "lai_vay", "bien_so": "50F-009.60",
                                        "mo_ta": "Lãi vay tháng 8", "so_tien": "327.000.000"}])
    assert kq["da_nap"] == 0 and "CẢ ĐỘI" in loi_dong(kq)


def test_chi_phi_theo_xe_bat_buoc_co_bien_so(db):
    kq = nap(db, "chi_phi_ky_doi_xe", [{"ky": "2026-08", "nhom": "bao_hiem",
                                        "mo_ta": "Bảo hiểm", "so_tien": "12.000.000"}])
    assert kq["da_nap"] == 0 and "từng xe" in loi_dong(kq).lower()


def test_chi_phi_ky_nap_lai_khong_nhan_doi(db):
    r = {"ky": "2026-08", "nhom": "lai_vay", "mo_ta": "Lãi vay VPBank tháng 8", "so_tien": "327.000.000"}
    assert nap(db, "chi_phi_ky_doi_xe", [r])["da_nap"] == 1
    assert nap(db, "chi_phi_ky_doi_xe", [r])["da_co"] == 1


# ====================== MARKETING ======================
def test_marketing_o_lead_trong_khong_thanh_khong(db):
    kq = nap(db, "chi_marketing_kenh", [{"ky": "2026-08", "kenh": "facebook_ads",
                                         "chien_dich": "Hè 2026", "so_tien": "45.000.000"}])
    assert kq["da_nap"] == 1
    from app.models.nap_bo_sung import MktChannelSpend
    s = db.execute(select(MktChannelSpend).where(MktChannelSpend.chien_dich == "Hè 2026")).scalars().first()
    assert s.so_lead is None and s.luot_nhap is None       # CHƯA CÓ SỐ, không phải bằng 0
    assert any("chưa có số lead" in c.lower() for c in kq["dong"][0]["canh_bao"])


def test_marketing_kenh_ngoai_danh_muc_bi_chan(db):
    kq = nap(db, "chi_marketing_kenh", [{"ky": "2026-08", "kenh": "bao_tuong", "so_tien": "1.000.000"}])
    assert kq["da_nap"] == 0


def test_marketing_cung_ky_cung_kenh_khac_chien_dich_la_hai_dong(db):
    a = {"ky": "2026-09", "kenh": "google_ads", "chien_dich": "A", "so_tien": "10.000.000"}
    b = {**a, "chien_dich": "B"}
    assert nap(db, "chi_marketing_kenh", [a])["da_nap"] == 1
    assert nap(db, "chi_marketing_kenh", [b])["da_nap"] == 1
    assert nap(db, "chi_marketing_kenh", [a])["da_co"] == 1


# ====================== KINH DOANH ======================
def test_doanh_so_da_thu_khong_duoc_lon_hon_doanh_thu(db):
    kq = nap(db, "doanh_so_tu_van_vien", [{"ky": "2026-08", "ma_nv": "NS0002",
                                           "doanh_thu": "100.000.000",
                                           "doanh_thu_da_thu": "120.000.000"}])
    assert kq["da_nap"] == 0 and "lớn hơn doanh thu" in loi_dong(kq)


def test_doanh_so_hoa_hong_trong_van_la_trong(db):
    kq = nap(db, "doanh_so_tu_van_vien", [{"ky": "2026-08", "ma_nv": "NS0002",
                                           "so_booking": "12", "doanh_thu": "850.000.000"}])
    assert kq["da_nap"] == 1, loi_dong(kq)
    from app.models.nap_bo_sung import SalesByConsultant
    s = db.execute(select(SalesByConsultant).where(SalesByConsultant.ky == "2026-08")).scalars().first()
    assert s.hoa_hong is None and s.so_booking == 12


# ====================== HƯỚNG DẪN ======================
def _tour_thu(db, ma="V4-TOUR-1", ngay=3):
    from app.models.core import Tour, User
    t = db.execute(select(Tour).where(Tour.code == ma)).scalars().first()
    if t is None:
        u = db.execute(select(User)).scalars().first()
        d = date(2026, 8, 10)
        t = Tour(code=ma, name="Tour thử V4", tour_type="le_noi_dia", start_date=d,
                 end_date=d + timedelta(days=ngay - 1), operator_id=u.id, status="da_duyet")
        db.add(t); db.flush()
    return t


def test_thu_lao_hdv_khong_co_don_gia_thi_de_trong_chu_khong_tu_dien(db):
    _tour_thu(db, "V4-TOUR-1")
    kq = nap(db, "thu_lao_hdv", [{"ma_tour": "V4-TOUR-1", "the_so": "HDV-NĐ-2023-0451", "so_ngay": "3"}])
    assert kq["da_nap"] == 1, loi_dong(kq)
    assert "chưa có đơn giá" in kq["ket_qua"][0]["ket_qua"]
    from app.models.hr import GuideAssignment
    a = db.execute(select(GuideAssignment).order_by(GuideAssignment.id.desc())).scalars().first()
    assert a.rate_per_day == 0 and a.status == "da_xac_nhan"


def test_thu_lao_hdv_khong_duoc_dai_hon_chuyen(db):
    _tour_thu(db, "V4-TOUR-2", ngay=2)
    kq = nap(db, "thu_lao_hdv", [{"ma_tour": "V4-TOUR-2", "the_so": "HDV-NĐ-2023-0451", "so_ngay": "9"}])
    assert kq["da_nap"] == 0 and "lớn hơn độ dài chuyến" in loi_dong(kq)


def test_thu_lao_hdv_tour_khong_co_that_bi_chan(db):
    kq = nap(db, "thu_lao_hdv", [{"ma_tour": "KHONG-CO", "the_so": "HDV-NĐ-2023-0451", "so_ngay": "2"}])
    assert kq["da_nap"] == 0 and "không có tour" in loi_dong(kq).lower()


# ====================== KẾ TOÁN ======================
def _hd(**kw):
    d = {"mst_nguoi_ban": "0301234567", "ten_nguoi_ban": "Khách sạn ABC", "ky_hieu": "1C26TAA",
         "so_hoa_don": "00000042", "ngay_hd": "20/08/2026", "noi_dung": "Tiền phòng",
         "tien_truoc_thue": "10.000.000", "thue_suat": "8", "tien_thue": "800.000",
         "tong_tien": "10.800.000"}
    d.update(kw); return d


def test_hoa_don_cung_so_khac_nha_cung_cap_la_hai_hoa_don(db):
    assert nap(db, "hoa_don_dau_vao", [_hd()])["da_nap"] == 1
    assert nap(db, "hoa_don_dau_vao", [_hd(mst_nguoi_ban="0309999999",
                                           ten_nguoi_ban="Nhà hàng XYZ")])["da_nap"] == 1
    assert nap(db, "hoa_don_dau_vao", [_hd()])["da_co"] == 1


def test_hoa_don_tong_lech_thi_chan(db):
    kq = nap(db, "hoa_don_dau_vao", [_hd(so_hoa_don="00000043", tong_tien="99.000.000")])
    assert kq["da_nap"] == 0 and "lệch" in loi_dong(kq)


def test_hoa_don_nap_len_khong_tu_ghi_so(db):
    nap(db, "hoa_don_dau_vao", [_hd(so_hoa_don="00000044")])
    from app.models.nap_bo_sung import PurchaseInvoice
    h = db.execute(select(PurchaseInvoice).where(
        PurchaseInvoice.so_hoa_don == "00000044")).scalars().first()
    assert h.khop == "chua_khop" and h.entry_id is None and h.tour_id is None
    assert h.thue_suat == 0.08                              # "8" hiểu là 8%, không phải 800%


# ====================== HCNS ======================
def test_bao_hiem_khong_ghi_cho_cong_tac_vien(db):
    kq = nap(db, "bao_hiem_ky", [{"ky": "2026-08", "ma_nv": "NS0011", "muc_dong": "5.000.000"}], boi="hcns")
    assert kq["da_nap"] == 0 and "cộng tác viên" in loi_dong(kq)


def test_bao_hiem_ghi_duoc_cho_nguoi_co_hop_dong(db):
    kq = nap(db, "bao_hiem_ky", [{"ky": "2026-08", "ma_nv": "NS0013", "muc_dong": "7.000.000",
                                  "cty_dong": "1.610.000", "nld_dong": "735.000"}], boi="hcns")
    assert kq["da_nap"] == 1, loi_dong(kq)
    from app.models.nap_bo_sung import SocialInsurancePeriod
    b = db.execute(select(SocialInsurancePeriod).where(
        SocialInsurancePeriod.ky == "2026-08")).scalars().first()
    assert b.so_ngay_dong is None and b.trang_thai == "dang_dong"


def test_bang_luong_ky_da_ky_thi_tu_choi(db):
    from app.models.hr import PayrollRun
    db.add(PayrollRun(period="2026-07", status="kt_xac_nhan", rows=[], totals={}, inputs={}))
    db.flush()
    kq = nap(db, "bang_luong", [{"ky": "2026-07", "ma_nv": "NS0013", "cong_thuc_te": "26"}], boi="hcns")
    assert kq["da_nap"] == 0 and "chữ ký" in loi_dong(kq)


def test_bang_luong_ky_nhap_thi_ghi_vao_dau_vao_va_thuc_linh_trong_van_trong(db):
    kq = nap(db, "bang_luong", [{"ky": "2026-08", "ma_nv": "NS0013", "cong_thuc_te": "24",
                                 "cong_chuan": "26"}], boi="hcns")
    assert kq["da_nap"] == 1, loi_dong(kq)
    from app.models.hr import PayrollRun
    r = db.execute(select(PayrollRun).where(PayrollRun.period == "2026-08")).scalars().first()
    d = r.inputs["theo_ma_nv"]["NS0013"]
    assert d["cong_thuc_te"] == 24 and d["thuc_linh"] is None
    assert r.inputs["cong_chuan"] == 26
    # Nạp lại cùng người cùng kỳ: đã có, không ghi chồng.
    assert nap(db, "bang_luong", [{"ky": "2026-08", "ma_nv": "NS0013",
                                   "cong_thuc_te": "99"}], boi="hcns")["da_co"] == 1


# ====================== TÀI SẢN ======================
def _ts(ma="TSV4-1", **kw):
    d = {"ma_ts": ma, "ten": "Xe khách 45 chỗ", "loai": "huu_hinh", "nhom": "Phương tiện vận tải",
         "ngay_bat_dau_kh": "01/01/2026", "nguyen_gia": "3.200.000.000", "so_thang_kh": "120",
         # TSCD-1 (#735, 08/11/2026): «TK nguyên giá» là cột BẮT BUỘC, phải là tài khoản CHI TIẾT
         # của loại tài sản (2113 phương tiện vận tải) — thiếu thì dòng dừng ở «Thiếu tk nguyên giá»
         # trước khi tới luật đang đo.
         "tk_nguyen_gia": "2113"}
    d.update(kw); return d


def test_tai_san_luy_ke_phai_di_kem_ky(db):
    kq = nap(db, "tai_san_co_dinh", [_ts("TSV4-2", hao_mon_luy_ke="200.000.000")])
    assert kq["da_nap"] == 0 and "kỳ tương ứng" in loi_dong(kq)


def test_tai_san_luy_ke_khong_duoc_vuot_nguyen_gia(db):
    kq = nap(db, "tai_san_co_dinh", [_ts("TSV4-3", hao_mon_luy_ke="9.000.000.000",
                                         ky_so_du="2025-12")])
    assert kq["da_nap"] == 0 and "lớn hơn nguyên giá" in loi_dong(kq)


def test_tai_san_nap_chi_tao_moi(db):
    assert nap(db, "tai_san_co_dinh", [_ts("TSV4-1")])["da_nap"] == 1
    lai = nap(db, "tai_san_co_dinh", [_ts("TSV4-1", nguyen_gia="1")])
    assert lai["da_nap"] == 0 and lai["da_co"] == 1
    from app.models.assets import FixedAsset
    a = db.execute(select(FixedAsset).where(FixedAsset.code == "TSV4-1")).scalars().first()
    assert a.cost == 3_200_000_000 and a.asset_account == "2113"


def test_ccdc_da_phan_bo_khong_duoc_vuot_gia_tri(db):
    # CPTT-2 (#713): `tk_chi_phi` là cột BẮT BUỘC — thiếu nó thì dòng dừng ở lỗi «thiếu tk chi phí»
    # trước khi tới luật đang đo ở đây, nên phải có đủ cột.
    kq = nap(db, "cong_cu_dung_cu", [{"ma_ccdc": "CCV4-1", "ten": "Bộ lốp", "tk_chi_phi": "627",
                                      "ngay_bat_dau_pb": "01/08/2026", "gia_tri": "48.000.000",
                                      "so_ky_pb": "12", "da_phan_bo": "60.000.000",
                                      "ky_so_du": "2026-07"}])
    assert kq["da_nap"] == 0 and "lớn hơn giá trị" in loi_dong(kq)


def test_khau_hao_chi_nhan_ky_truoc_ky_vtos_tu_tinh(db):
    nap(db, "tai_san_co_dinh", [_ts("TSV4-9", ngay_bat_dau_kh="01/01/2026")])
    xau = nap(db, "khau_hao_ky", [{"ma_ts": "TSV4-9", "ky": "2026-03",
                                   "khau_hao_ky": "26.666.667"}])
    assert xau["da_nap"] == 0 and "VTOS tự tính" in loi_dong(xau)
    tot = nap(db, "khau_hao_ky", [{"ma_ts": "TSV4-9", "ky": "2025-12",
                                   "khau_hao_ky": "26.666.667", "luy_ke": "320.000.000"}])
    assert tot["da_nap"] == 1, loi_dong(tot)
    from app.models.assets import AssetDepreciation
    d = db.execute(select(AssetDepreciation).where(
        AssetDepreciation.period == "2025-12")).scalars().first()
    assert d.remaining == 3_200_000_000 - 320_000_000


def test_khau_hao_phai_co_the_tai_san_truoc(db):
    kq = nap(db, "khau_hao_ky", [{"ma_ts": "KHONG-CO", "ky": "2025-12", "khau_hao_ky": "1.000.000"}])
    assert kq["da_nap"] == 0 and "nạp thẻ tài sản trước" in loi_dong(kq)
