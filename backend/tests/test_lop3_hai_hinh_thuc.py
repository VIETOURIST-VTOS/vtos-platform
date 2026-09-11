"""Lớp 3: hai hình thức tour, dựng lại từ hai mẫu quyết toán thật.

Phép thử ở tệp trước dựng lại tour lẻ trong nước (Nha Trang). Tệp này dựng hai mẫu còn lại, vì mỗi
mẫu mang một thứ mà mẫu Nha Trang không có:

    ĐOÀN ĐÀ LẠT 3N3D 04.06 (trong nước, bán cho doanh nghiệp)
        * doanh thu là 4 DÒNG HỢP ĐỒNG cho 37 người, không phải 37 dòng khách
        * có VAT 8%: 100.592.592,59 trước thuế + 8.047.407,41 = 108.640.000
        * có DÒNG ÂM từ biên bản thanh lý: hoàn suất ăn −899.999, hoàn vé tham quan −539.999
        * HDV chi 3.696.000 trong khi công ty ứng 3.300.000 -> CÔNG TY nợ HDV 396.000

    SM000.05260226 (SIN/MAL, nước ngoài)
        * 22 khách của hai đại lý SGS và VV ngồi cùng chuyến mà doanh thu không thuộc Vietourist
        * toàn bộ chi phí chỉ chia cho 9 khách của Vietourist, không chia cho 31 người

Điểm chung của hai mẫu: chúng phá vỡ đúng những giả định mà một hệ thống dựng riêng cho tour lẻ nội
địa sẽ mặc nhiên coi là đúng – rằng số dòng doanh thu bằng số khách, rằng doanh thu không âm, rằng ai
ngồi trên xe thì người ấy trả tiền, và rằng HDV luôn là người nợ công ty.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lop3_hai.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lop3_hai.db"):
    os.remove("test_lop3_hai.db")

from datetime import date                                           # noqa: E402
import pytest                                                       # noqa: E402
from app.db.session import SessionLocal, Base, engine                # noqa: E402
import app.models                                                    # noqa: E402,F401
from app.models.core import Tour, Booking, User                      # noqa: E402
from app.models.lop3_tour import (BookingKhach, TourDoanhThuDong,    # noqa: E402
                                  TourHdvChi, TourPhuongTien, KhachChiPhi)
from app.models.vietrip import TourCostLine                          # noqa: E402
from app.services import gia_khach as G                              # noqa: E402

Base.metadata.create_all(engine)


def _nguoi(db, ten="dh_test", vai="nv_dh"):
    u = db.query(User).filter(User.username == ten).first()
    if not u:
        u = User(username=ten, full_name=ten, role=vai, password_hash="x")
        db.add(u); db.flush()
    return u


def _chuyen(db, ma, ten, hinh_thuc, di, ve, so_khach):
    u = _nguoi(db)
    t = Tour(code=ma, name=ten, tour_type="package", hinh_thuc=hinh_thuc, operator_id=u.id,
             start_date=di, end_date=ve, planned_pax=so_khach)
    db.add(t); db.flush()
    b = Booking(code=f"BK-{ma}", tour_id=t.id, request_id=0, sales_id=u.id,
                customer_name=ten, customer_phone="0900000000", pax=so_khach,
                source="test", created_by="test")
    db.add(b); db.flush()
    return t, b


# =============================================================================================
# ĐOÀN ĐÀ LẠT – trong nước, bán cho doanh nghiệp
# =============================================================================================

@pytest.fixture(scope="module")
def da_lat():
    db = SessionLocal()
    t, b = _chuyen(db, "MICEDL3N3D.04040626", "ĐOÀN ĐÀ LẠT 3N3D - CTY CP MINH HIỀN",
                   "trong_nuoc", date(2026, 6, 4), date(2026, 6, 7), 37)

    # Bốn dòng doanh thu cho 37 người – đúng như sheet QUYẾT TOÁN của tệp.
    for loai, nd, doi_tuong, don_gia, sl, ct in [
        ("hop_dong", "NGƯỜI LỚN", "nguoi_lon", 3185185.185185185, 25, ""),
        ("hop_dong", "TRẺ EM", "tre_em", 2229629.6296296297, 10, ""),
        ("thanh_ly", "HOÀN SUẤT ĂN NGÀY CUỐI", None, -166666.66666666666, 5, "BBTL 04.06"),
        ("thanh_ly", "HOÀN VÉ THAM QUAN", None, -499999.99999999994, 1, "BBTL 04.06"),
    ]:
        truoc = don_gia * sl
        thue = truoc * 0.08
        db.add(TourDoanhThuDong(tour_id=t.id, booking_id=b.id, loai=loai, noi_dung=nd,
                                doi_tuong=doi_tuong, don_gia_truoc_thue=don_gia, so_luong=sl,
                                thanh_tien_truoc_thue=truoc, thue_suat=0.08, tien_thue=thue,
                                thanh_tien=truoc + thue, chung_tu=ct))

    # Xe của Vietrip – công ty trong nhóm, nên là công nợ nội bộ chứ không phải chi cho bên thứ ba.
    dong_xe = TourCostLine(tour_id=t.id, line_no=1, description="VIETRIP 45s - 3N3D",
                           nhom="A. VẬN CHUYỂN", budget=18000000.0, actual=18000000.0,
                           thue_suat=0.08, vat_hoa_don=1333333.33, status="hd")
    db.add(dong_xe); db.flush()
    db.add(TourPhuongTien(tour_id=t.id, loai="o_to", chang="SG-DL-SG", so_hieu="45 chỗ",
                          nha_cung_cap="VIETRIP", xe_nha=1, so_cho=45, so_khach_su_dung=37,
                          don_gia=18000000.0, so_luong=1, thanh_tien=18000000.0,
                          dong_chi_phi_id=dong_xe.id))

    # Sáu khoản có hoàn tiền: dự chi khác thực chi. Đây là chỗ cột budget/actual cùng dòng phát huy.
    for nd, du, thuc in [
        ("Ăn sáng ĐỒI CHÈ CẦU ĐẤT", 3500000.0, 2900000.0),
        ("Ăn tối LEGUDA", 4620000.0, 4410000.0),
        ("Ăn trưa TÂM CHÂU BẢO LỘC", 4200000.0, 3600000.0),
        ("KDL CHUỒN CHUỒN", 2800000.0, 1740000.0),
        ("HOÀNG LONG OHAYO", 3080000.0, 2843500.0),
        ("NƯỚC GALA + TẶNG BIA", 2700000.0, 2125000.0),
    ]:
        db.add(TourCostLine(tour_id=t.id, description=nd, nhom="B. LAND TOUR",
                            budget=du, actual=thuc, thue_suat=0.08, status="hd"))

    # Banner và ăn nội bộ: thuế suất 0, và ăn nội bộ không có hoá đơn.
    db.add(TourCostLine(tour_id=t.id, description="BANNER CHỤP HÌNH", nhom="C. KHÁC",
                        budget=200000.0, actual=210470.0, thue_suat=0.0, status="hd"))
    db.add(TourCostLine(tour_id=t.id, description="NỘI BỘ ĂN Ở", nhom="C. KHÁC",
                        budget=800000.0, actual=800000.0, thue_suat=0.0,
                        khong_hoa_don=800000.0, status="hd"))

    # HDV: công ty ứng 3.300.000, HDV chi 3.696.000 -> công ty NỢ hdv 396.000.
    for nd, tien, ct in [("CÂY NẾN DOANH NGHIỆP", 500000.0, "phieu_thu"),
                         ("BÁNH KEM", 500000.0, "phieu_thu"),
                         ("CÂY VÂN TAY DOANH NGHIỆP", 1000000.0, "phieu_thu"),
                         ("QUÀ GALA", 500000.0, None),
                         ("NGỦ NỘI BỘ", 800000.0, "phieu_thu"),
                         ("NƯỚC TẶNG KHÁCH", 396000.0, "hoa_don")]:
        db.add(TourHdvChi(tour_id=t.id, noi_dung=nd, thanh_tien=tien, loai_chung_tu=ct))
    db.commit()
    yield t.id
    db.close()


def test_doan_ghi_doanh_thu_theo_dong_hop_dong_khong_theo_dau_khach(da_lat):
    """37 người nhưng chỉ 4 dòng doanh thu – và tổng phải ra đúng 108.640.000 của tệp."""
    db = SessionLocal()
    dong = list(db.query(TourDoanhThuDong).filter(TourDoanhThuDong.tour_id == da_lat))
    assert len(dong) == 4
    assert sum((d.so_luong or 0) for d in dong if d.loai == "hop_dong") == 35   # 25 NL + 10 TE

    truoc = sum(d.thanh_tien_truoc_thue for d in dong)
    thue = sum(d.tien_thue for d in dong)
    assert abs(truoc - 100592592.59) < 1.0
    assert abs(thue - 8047407.41) < 1.0
    assert abs((truoc + thue) - 108640000.0) < 1.0
    db.close()


def test_dong_thu_am_duoc_phep_va_phai_co_can_cu(da_lat):
    """Hoàn tiền theo biên bản thanh lý là số ÂM. Chặn số âm là buộc người ta trừ lén vào dòng dương."""
    db = SessionLocal()
    am = [d for d in db.query(TourDoanhThuDong).filter(TourDoanhThuDong.tour_id == da_lat)
          if (d.thanh_tien or 0) < 0]
    assert len(am) == 2
    assert abs(sum(d.thanh_tien for d in am) - (-1439999.99)) < 1.0
    # Mỗi dòng âm phải chỉ được ra căn cứ – nếu không thì không phân biệt được với gõ nhầm dấu.
    assert all(d.loai == "thanh_ly" and d.chung_tu for d in am)
    db.close()


def test_du_chi_va_thuc_chi_nam_cung_mot_dong_nen_so_duoc_tung_khoan(da_lat):
    """Sáu khoản có hoàn tiền. Cột budget/actual cùng dòng nên chênh lệch đọc ra ngay."""
    db = SessionLocal()
    dong = [d for d in db.query(TourCostLine).filter(TourCostLine.tour_id == da_lat)
            if d.budget is not None and d.actual is not None and d.budget != d.actual]
    hoan = {d.description: round(d.budget - d.actual) for d in dong if d.budget > d.actual}
    assert hoan["Ăn sáng ĐỒI CHÈ CẦU ĐẤT"] == 600000
    assert hoan["KDL CHUỒN CHUỒN"] == 1060000
    assert hoan["NƯỚC GALA + TẶNG BIA"] == 575000
    assert round(sum(hoan.values())) == 3281500
    # Banner thì ngược lại: thực chi CAO hơn dự chi.
    vuot = [d for d in dong if d.actual > d.budget]
    assert len(vuot) == 1 and round(vuot[0].actual - vuot[0].budget) == 10470
    db.close()


def test_thue_suat_khac_nhau_tren_cung_mot_chuyen(da_lat):
    """8% cho nhà hàng và lưu trú, 0% cho banner và ăn nội bộ – không lưu thuế suất thì mất bảng kê."""
    db = SessionLocal()
    dong = list(db.query(TourCostLine).filter(TourCostLine.tour_id == da_lat))
    assert {d.thue_suat for d in dong} == {0.08, 0.0}
    khong_hd = [d for d in dong if d.khong_hoa_don]
    assert len(khong_hd) == 1 and khong_hd[0].khong_hoa_don == 800000.0
    db.close()


def test_xe_nha_tach_khoi_chi_cho_ben_thu_ba(da_lat):
    """Xe Vietrip là công nợ NỘI BỘ. Hợp nhất báo cáo nhóm thì khoản ấy phải loại trừ."""
    db = SessionLocal()
    pt = db.query(TourPhuongTien).filter(TourPhuongTien.tour_id == da_lat).one()
    assert pt.xe_nha == 1 and pt.nha_cung_cap == "VIETRIP"
    assert pt.so_cho == 45 and pt.so_khach_su_dung == 37
    assert pt.dong_chi_phi_id is not None            # chặng nào cũng phải nối vào một dòng chi
    db.close()


def test_cong_ty_co_the_no_hdv_chu_khong_chi_mot_chieu(da_lat):
    """Chiều ngược của quy tắc: HDV chi 3.696.000, công ty ứng 3.300.000 -> công ty nợ HDV 396.000.

    Gộp 'vượt dự toán' với 'thừa/thiếu so với tiền ứng' làm một cột là có lúc đi đòi tiền người đang
    được công ty nợ.
    """
    db = SessionLocal()
    dong = list(db.query(TourHdvChi).filter(TourHdvChi.tour_id == da_lat))
    tong_chi = sum(d.thanh_tien for d in dong)
    assert tong_chi == 3696000.0
    con_lai = 3300000.0 - tong_chi
    assert con_lai == -396000.0                       # âm = công ty nợ HDV
    # Mỗi khoản phải nói rõ chứng từ; khoản không có chứng từ phải lộ ra chứ không im lặng.
    assert sum(1 for d in dong if not d.loai_chung_tu) == 1
    db.close()


# =============================================================================================
# SIN/MAL – nước ngoài, có khách của đại lý ngồi ghép
# =============================================================================================

@pytest.fixture(scope="module")
def sin_mal():
    db = SessionLocal()
    t, b = _chuyen(db, "SM000.05260226", "SINMAL 5N4D", "nuoc_ngoai",
                   date(2026, 2, 26), date(2026, 3, 2), 32)

    stt = 0
    # 9 khách thật của Vietourist (8 người lớn + 1 trẻ em), đúng như sheet qt.
    for gia in [11490000.0] * 2 + [11490000.0] * 2 + [10790000.0] * 4:
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"KHACH {stt}",
                            nhom_khach="tra_tien", ngay_sinh=date(1990, 1, 1), gia_ban=gia))
    stt += 1
    db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten="TRUONG NGOC THANH (CHD)",
                        nhom_khach="tra_tien", ngay_sinh=date(2018, 1, 1), gia_ban=10340000.0))
    # 22 khách của hai đại lý + 1 trưởng đoàn nội bộ – ngồi cùng chuyến, không mang doanh thu.
    for i in range(17):
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"SGS {i+1}",
                            nhom_khach="dai_ly", ngay_sinh=date(1990, 1, 1), gia_ban=0.0))
    for i in range(5):
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"VV {i+1}",
                            nhom_khach="dai_ly", ngay_sinh=date(1990, 1, 1), gia_ban=0.0))
    stt += 1
    db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten="TL VV - TRINH MAI ANH",
                        nhom_khach="noi_bo", ngay_sinh=date(1990, 1, 1), gia_ban=0.0))
    db.flush()

    # Phí TL: 1.627.884 chia đều cho khách CÓ THU. Tệp chia ra 180.876,13 mỗi khách -> mẫu số 9.
    db.add(TourCostLine(tour_id=t.id, description="PHÍ TL", nhom="C. KHÁC",
                        actual=1627884.0, quy_tac_phan_bo="deu_khach_co_thu", status="hd"))
    # Land bằng USD – tour nước ngoài phải khai tỷ giá và ngày tỷ giá.
    db.add(TourCostLine(tour_id=t.id, description="LAND SIN/MAL", nhom="A. LAND",
                        actual=42495705.0, tien_te="USD", so_tien_goc=1631.0,
                        ty_gia=26055.0, ngay_ty_gia=date(2026, 2, 20),
                        quy_tac_phan_bo="deu_khach_co_thu", status="hd"))

    for k in db.query(BookingKhach).filter(BookingKhach.tour_id == t.id):
        G.xac_dinh_khach(db, k, t.start_date, 11490000.0, t.hinh_thuc)
    db.commit()
    yield t.id
    db.close()


def test_khach_dai_ly_ngoi_ghep_khong_vao_mau_so_phan_bo(sin_mal):
    """32 người ngồi trên chuyến, nhưng chi phí chỉ chia cho 9 khách của Vietourist.

    Đây là chỗ hai cột nhom_khach và loai_tuoi phải tách rời. Nếu chỉ có một cột loại khách thì
    "người lớn của đại lý" và "người lớn của mình" lẫn vào nhau, và mẫu số thành 31 thay vì 9 –
    giá vốn mỗi khách sụt còn chưa tới một phần ba, chuyến báo lãi gấp bội.
    """
    db = SessionLocal()
    pb = G.phan_bo(db, sin_mal)
    assert pb["so_khach"] == 32                       # ghi hết, không bỏ ai

    co_thu = [d for d in pb["dong"] if d["thu"] > 0]
    assert len(co_thu) == 9

    def khoan(d, ten):
        return round(sum(x["so_tien"] for x in d["gom"] if x["noi_dung"] == ten), 2)

    # Phí TL 1.627.884 ÷ 9 = 180.876,00 – khớp con số 180.876,13 của tệp.
    assert abs(khoan(co_thu[0], "PHÍ TL") - 180876.0) < 1.0

    dai_ly = [d for d in pb["dong"] if d["nhom_khach"] == "dai_ly"]
    noi_bo = [d for d in pb["dong"] if d["nhom_khach"] == "noi_bo"]
    assert len(dai_ly) == 22 and len(noi_bo) == 1
    assert all(d["gia_von"] == 0 for d in dai_ly + noi_bo)
    db.close()


def test_tour_nuoc_ngoai_phai_khai_ty_gia_va_ngay_ty_gia(sin_mal):
    """Khoản ngoại tệ không khai ngày tỷ giá thì không bao giờ phân xử được số nào đúng.

    Tệp UK có HAI tỷ giá GBP khác nhau trong cùng một tệp (36.000 và 35.944); riêng trên giá land
    692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.
    """
    db = SessionLocal()
    t = db.get(Tour, sin_mal)
    assert t.hinh_thuc == "nuoc_ngoai"
    ngoai_te = [d for d in db.query(TourCostLine).filter(TourCostLine.tour_id == sin_mal)
                if d.tien_te]
    assert ngoai_te, "phải có ít nhất một khoản ngoại tệ"
    for d in ngoai_te:
        assert d.ty_gia and d.ngay_ty_gia, f"{d.description}: thiếu tỷ giá hoặc ngày tỷ giá"
        # Số VND phải khớp phép nhân, không phải một con số gõ rời.
        assert abs(float(d.actual) - float(d.so_tien_goc) * float(d.ty_gia)) < 1000
    db.close()


def test_hai_hinh_thuc_deu_dung_chung_mot_bo_bang(da_lat, sin_mal):
    """Một chuyến trong nước và một chuyến nước ngoài cùng nằm trên một bộ bảng.

    Đây là điều kiện để báo cáo lãi lỗ toàn công ty cộng được cả hai mà không phải cộng từ hai nguồn.
    """
    db = SessionLocal()
    assert db.get(Tour, da_lat).hinh_thuc == "trong_nuoc"
    assert db.get(Tour, sin_mal).hinh_thuc == "nuoc_ngoai"
    for tid in (da_lat, sin_mal):
        assert db.query(TourCostLine).filter(TourCostLine.tour_id == tid).count() > 0
    db.close()
