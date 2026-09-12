# -*- coding: utf-8 -*-
"""Đ-2 · Thuế GTGT ở mức chuyến, và ba tầng kết quả.

Phép thử này dựng lại BẰNG SỐ THẬT một tờ quyết toán có thật: đoàn Hồ Tràm 2N1Đ
(MICEHT2N1D.02110726, khởi hành 11/7/2026, 25 khách, sales Hoàng Hiệp, điều hành Mã Huệ Linh).

Vì sao dùng số thật chứ không số tròn cho dễ đọc: con số 2.009.333 đ là chênh giữa cách VTOS đang
tính và cách phòng Điều hành đang tính. Một phép thử với số tròn vẫn xanh khi phép tính sai lệch
vài phần trăm; phép thử với số thật thì không.

BỐN CHỖ CANH, và cả bốn đều sai theo CHIỀU NGUY HIỂM nếu bỏ — tức chiều làm lợi nhuận trông đẹp hơn:

  1. Không trừ thuế  → lãi cao hơn thật 14,5%.
  2. Kẹp thuế về 0    → chuyến âm thuế mất phần khấu trừ, tổng không khớp tờ khai kỳ.
  3. Coi chi không hoá đơn là có khấu trừ → thuế thấp giả, lãi cao giả.
  4. Tự áp 8% cho tour nước ngoài → sai theo chiều ngược (lãi teo), nhưng vẫn là bịa một con số
     thuế chưa ai xác nhận cách tính.
"""
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
import app.models.lop3_tour  # noqa: F401
import app.models.vietrip  # noqa: F401
from app.db.session import Base
from app.models.lop3_tour import TourDoanhThuDong
from app.models.vietrip import TourCostLine
from app.services import lai_lo_tour as LL
from app.services import thue_gtgt_chuyen as T


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    with Session(eng) as s:
        yield s


# ---- Số thật của đoàn Hồ Tràm, sheet "CHI THỰC TẾ" -------------------------------------------
HT_DOANH_THU = 92_855_000          # J10 – tổng thu đã gồm VAT
HT_VAT_RA = 6_878_148.148148147    # I10 – tổng thuế đầu ra của hai dòng doanh thu
HT_TONG_CHI = 76_972_600           # G33
HT_KHONG_HOA_DON = 11_150_000      # K33 – phần chi không có hoá đơn
HT_VAT_VAO = 4_868_814.814814815   # I33 – thuế đầu vào trên các dòng CÓ hoá đơn
HT_THUE = 2_009_333.333333332      # H38 = I10 - I33
HT_LAI_THAT = 13_873_066.666666668  # H39 – lợi nhuận theo cách phòng Điều hành tính


def _chuyen_ho_tram(db, tour_id=1):
    """Dựng lại đoàn Hồ Tràm: hai dòng doanh thu (người lớn 8%, trẻ em 8%) và các dòng chi."""
    db.add(TourDoanhThuDong(tour_id=tour_id, loai="hop_dong", noi_dung="NGƯỜI LỚN",
                            thanh_tien_truoc_thue=80_712_962.96296296, thue_suat=0.08,
                            tien_thue=6_457_037.037037036, thanh_tien=87_170_000))
    db.add(TourDoanhThuDong(tour_id=tour_id, loai="hop_dong", noi_dung="TRẺ EM",
                            thanh_tien_truoc_thue=5_263_888.888888889, thue_suat=0.08,
                            tien_thue=421_111.1111111111, thanh_tien=5_685_000))
    # Các dòng chi CÓ hoá đơn – tổng thuế đầu vào 4.868.814,81
    co_hd = [
        ("XE 29S – GOLDEN GROUP", 8_964_000, 663_999.9999999999, "HD 739"),
        ("EMERALD HỒ TRÀM", 32_650_000, 2_418_518.5185185187, "HD 1767"),
        ("Ăn sáng MEKONG LONG THÀNH", 1_860_000, 137_777.77777777775, "HD 7742"),
        ("Ăn trưa HƯƠNG PHONG", 4_500_000, 333_333.3333333333, "HD 00004574"),
        ("Ăn trưa LÀNG BÈ LONG SƠN", 4_000_000, 296_296.2962962963, "HD 1429"),
        ("Vé MINERA BÌNH CHÂU", 13_355_000, 989_259.2592592593, "HD 00017197"),
        ("Nón", 400_000, 29_629.629629629628, ""),
    ]
    for mo_ta, thuc_chi, vat, so_hd in co_hd:
        db.add(TourCostLine(tour_id=tour_id, description=mo_ta, actual=thuc_chi,
                            thue_suat=0.08, vat_hoa_don=vat, so_hoa_don=so_hd or None, status="hd"))
    # Các dòng chi KHÔNG hoá đơn – 11.150.000 đ, không sinh thuế đầu vào
    khong_hd = [("Ăn tối Cây Dương", 8_205_000), ("Ngủ + ăn sáng nội bộ", 600_000),
                ("Quà trưởng đoàn", 1_000_000), ("Banner + ship", 145_000), ("HDV", 1_200_000)]
    for mo_ta, tien in khong_hd:
        db.add(TourCostLine(tour_id=tour_id, description=mo_ta, actual=tien,
                            thue_suat=0.0, vat_hoa_don=0.0, khong_hoa_don=tien, status="hd"))
    db.commit()


# =============================================================================================
# 1. Dựng lại đúng con số của phòng Điều hành
# =============================================================================================

def test_vat_dau_ra_va_dau_vao_khop_to_quyet_toan_that(db):
    _chuyen_ho_tram(db)
    ra = T.vat_dau_ra_do_duoc(db, [1])[1]
    vao = T.vat_dau_vao(db, [1])[1]
    assert ra["vat_ra"] == pytest.approx(HT_VAT_RA, abs=1)
    assert vao["vat_vao"] == pytest.approx(HT_VAT_VAO, abs=1)
    assert vao["chi_khong_hoa_don"] == pytest.approx(HT_KHONG_HOA_DON, abs=1)


def test_thue_phat_sinh_bang_dung_2_009_333(db):
    _chuyen_ho_tram(db)
    kq = T.nhieu_chuyen(db, [{"tour_id": 1, "hinh_thuc": "trong_nuoc", "doanh_thu": HT_DOANH_THU}])[1]
    assert kq["co_so"] == "do_tu_dong_doanh_thu"
    assert kq["thue_gtgt"] == pytest.approx(HT_THUE, abs=1)


def test_lai_sau_thue_bang_dung_so_cua_dieu_hanh_va_thap_hon_cach_cu_14_phan_tram(db):
    """Đây là lý do tồn tại của cả Đ-2."""
    _chuyen_ho_tram(db)
    thue = T.nhieu_chuyen(db, [{"tour_id": 1, "hinh_thuc": "trong_nuoc",
                                "doanh_thu": HT_DOANH_THU}])[1]
    lai_gop = HT_DOANH_THU - HT_TONG_CHI               # cách VTOS tính trước 12/9
    tang = LL.ba_tang(lai_gop, thue["thue_gtgt"])
    assert tang["lai_gop_chuyen"] == pytest.approx(15_882_400, abs=1)
    assert tang["sau_thue_gtgt"] == pytest.approx(HT_LAI_THAT, abs=1)
    thua = tang["lai_gop_chuyen"] - tang["sau_thue_gtgt"]
    assert thua == pytest.approx(HT_THUE, abs=1)
    assert thua / tang["sau_thue_gtgt"] == pytest.approx(0.1448, abs=0.001), \
        "cách cũ báo lãi thừa khoảng 14,5% – nếu con số này đổi thì phép tính đã đổi"


def test_kiem_cheo_bang_duong_khac_ra_cung_mot_so(db):
    """Doanh thu TRƯỚC thuế trừ (chi phí − thuế đầu vào được khấu trừ) phải ra đúng lãi sau thuế.

    Hai đường tính ra cùng một số thì phép tính đúng; ra hai số thì một trong hai đường sai, và
    không có phép thử nào khác phát hiện được điều đó.
    """
    _chuyen_ho_tram(db)
    thue = T.nhieu_chuyen(db, [{"tour_id": 1, "hinh_thuc": "trong_nuoc",
                                "doanh_thu": HT_DOANH_THU}])[1]
    duong_mot = LL.ba_tang(HT_DOANH_THU - HT_TONG_CHI, thue["thue_gtgt"])["sau_thue_gtgt"]
    duong_hai = (HT_DOANH_THU - thue["vat_ra"]) - (HT_TONG_CHI - thue["vat_vao"])
    assert duong_mot == pytest.approx(duong_hai, abs=1)


# =============================================================================================
# 2. Bốn hàng rào
# =============================================================================================

def test_chuyen_am_thue_KHONG_bi_kep_ve_0(db):
    """Thuế đầu vào lớn hơn đầu ra là khấu trừ THẬT, bù sang chuyến khác trong kỳ.

    Kẹp về 0 ở mức chuyến thì tổng thuế của mọi chuyến không bao giờ khớp tờ khai kỳ, và không ai
    tìm ra chênh ở đâu vì từng chuyến đều "đúng".
    """
    db.add(TourDoanhThuDong(tour_id=9, loai="hop_dong", thanh_tien_truoc_thue=10_000_000,
                            thue_suat=0.08, tien_thue=800_000, thanh_tien=10_800_000))
    db.add(TourCostLine(tour_id=9, description="Land lỗ", actual=30_000_000,
                        thue_suat=0.08, vat_hoa_don=2_400_000, so_hoa_don="HD 1", status="hd"))
    db.commit()
    kq = T.nhieu_chuyen(db, [{"tour_id": 9, "hinh_thuc": "trong_nuoc", "doanh_thu": 10_800_000}])[9]
    assert kq["thue_gtgt"] == pytest.approx(-1_600_000, abs=1)
    assert kq["thue_gtgt"] < 0, "ĐỪNG thêm max(0, …) ở đây – xem lý do trong docstring"


def test_chi_khong_hoa_don_KHONG_sinh_thue_dau_vao(db):
    """Chủ tịch 12/9: 'nếu đầu vào không đủ thì phải đóng 8% VAT chênh lệch'.

    Nếu phần không hoá đơn được coi như có khấu trừ thì thuế phát sinh của Hồ Tràm tụt từ 2.009.333
    xuống còn ~1.183.000, và lãi báo cao lên đúng phần chênh ấy.
    """
    _chuyen_ho_tram(db)
    vao = T.vat_dau_vao(db, [1])[1]
    assert vao["chi_khong_hoa_don"] == pytest.approx(HT_KHONG_HOA_DON, abs=1)
    # Thuế đầu vào KHÔNG được chứa 8% của phần không hoá đơn.
    neu_tinh_ca = HT_VAT_VAO + HT_KHONG_HOA_DON / 1.08 * 0.08
    assert vao["vat_vao"] < neu_tinh_ca - 500_000


# =============================================================================================
# 2b. TOUR NƯỚC NGOÀI — HOÁ ĐƠN HAI DÒNG (Chủ tịch chốt 12/9/2026)
# =============================================================================================
#
#   "thuế nước ngoài chia ra 2 loại: 1 là 0%, và khoản lợi nhuận là 8%. Ví dụ giá bán 1 tỷ, giá vốn
#    900 triệu = lợi nhuận 100 triệu; khi xuất hoá đơn cho khách hàng là 900 triệu 0% VAT, 100 triệu
#    8% VAT."

def test_nuoc_ngoai_tach_dung_hai_dong_theo_vi_du_cua_chu_tich(db):
    kq = T.nhieu_chuyen(db, [{"tour_id": 7, "hinh_thuc": "nuoc_ngoai",
                              "doanh_thu": 1_000_000_000, "gia_von": 900_000_000}])[7]
    assert kq["co_so"] == "nuoc_ngoai_hai_phan"
    d0, d8 = kq["hoa_don_hai_dong"]
    assert d0["so_tien"] == pytest.approx(900_000_000) and d0["thue_suat"] == 0.0
    assert d8["so_tien"] == pytest.approx(100_000_000) and d8["thue_suat"] == pytest.approx(0.08)
    # Giá bán niêm yết ĐÃ GỒM thuế (quy ước đọc từ chính mẫu Hồ Tràm: 3.790.000 / 1,08).
    assert d8["tien_thue"] == pytest.approx(100_000_000 - 100_000_000 / 1.08, abs=1)
    assert kq["vat_ra"] == pytest.approx(7_407_407, abs=2)


def test_nuoc_ngoai_KHONG_ap_8_phan_tram_len_toan_bo_doanh_thu(db):
    """Đây là chỗ sai hàng trăm triệu nếu làm tắt.

    Tệp UK 27/5 doanh thu 2.479.513.034 đ, giá vốn 2.253.432.408 đ. Áp 8% lên TOÀN BỘ doanh thu ra
    ~183,7 triệu tiền thuế; đúng cách thì chỉ phần chênh 226.080.626 đ chịu thuế.
    """
    kq = T.nhieu_chuyen(db, [{"tour_id": 8, "hinh_thuc": "nuoc_ngoai",
                              "doanh_thu": 2_479_513_034, "gia_von": 2_253_432_408}])[8]
    dung = kq["vat_ra"]
    neu_ap_toan_bo = 2_479_513_034 - 2_479_513_034 / 1.08
    assert dung == pytest.approx(226_080_626 - 226_080_626 / 1.08, abs=2)
    assert neu_ap_toan_bo - dung > 150_000_000, \
        "làm tắt ở đây là bịa ra hơn 150 triệu tiền thuế trên MỘT chuyến"


def test_nuoc_ngoai_chua_co_gia_von_thi_RONG_chu_khong_doan(db):
    """Chưa có giá vốn thì chưa biết ranh giới giữa hai dòng hoá đơn nằm ở đâu."""
    kq = T.nhieu_chuyen(db, [{"tour_id": 9, "hinh_thuc": "nuoc_ngoai",
                              "doanh_thu": 1_000_000_000, "gia_von": None}])[9]
    assert kq["thue_gtgt"] is None
    assert kq["co_so"] == "nuoc_ngoai_chua_co_gia_von"


def test_nuoc_ngoai_ban_duoi_gia_von_thi_KHONG_co_dong_thue_AM(db):
    """Hoá đơn không có dòng âm.

    Kẹp ở đây là ĐÚNG và khác hẳn chỗ cấm kẹp ở test_chuyen_am_thue: ở kia số âm là khấu trừ thật bù
    sang chuyến khác; ở đây chỉ là tờ hoá đơn có một dòng 0% thay vì hai. Lỗ vẫn là lỗ, vẫn hiện ở
    lãi gộp – nó chỉ không sinh ra thuế đầu ra âm.
    """
    kq = T.nhieu_chuyen(db, [{"tour_id": 10, "hinh_thuc": "nuoc_ngoai",
                              "doanh_thu": 900_000_000, "gia_von": 1_000_000_000}])[10]
    d0, d8 = kq["hoa_don_hai_dong"]
    assert d0["so_tien"] == pytest.approx(900_000_000)
    assert d8["so_tien"] == 0 and d8["tien_thue"] == 0
    assert kq["vat_ra"] == 0
    assert any("dưới giá vốn" in c for c in kq["canh_bao"])


def test_nuoc_ngoai_van_tru_thue_dau_vao(db):
    """Chi trong nước của tour nước ngoài (vé bay mua ở VN, bảo hiểm) vẫn có thuế đầu vào."""
    db.add(TourCostLine(tour_id=11, description="Vé máy bay mua tại VN", actual=500_000_000,
                        thue_suat=0.08, vat_hoa_don=37_037_037, so_hoa_don="HD 5", status="hd"))
    db.commit()
    kq = T.nhieu_chuyen(db, [{"tour_id": 11, "hinh_thuc": "nuoc_ngoai",
                              "doanh_thu": 1_000_000_000, "gia_von": 900_000_000}])[11]
    assert kq["vat_vao"] == pytest.approx(37_037_037)
    assert kq["thue_gtgt"] == pytest.approx(kq["vat_ra"] - 37_037_037)
    assert kq["thue_gtgt"] < 0, "chuyến này khấu trừ nhiều hơn phải nộp – số âm là thật"


def test_chua_co_dong_doanh_thu_thi_SUY_va_noi_ro_la_suy(db):
    """Chuyến chưa nhập dòng doanh thu chi tiết vẫn ra được số thuế – nhưng phải mang nhãn 'suy ra'.

    Trộn số đo được với số suy ra dưới cùng một nhãn là tạo ra một con số không ai biết nên tin
    tới đâu.
    """
    db.add(TourCostLine(tour_id=5, description="Xe", actual=10_000_000,
                        thue_suat=0.08, vat_hoa_don=740_740.74, so_hoa_don="HD 9", status="hd"))
    db.commit()
    kq = T.nhieu_chuyen(db, [{"tour_id": 5, "hinh_thuc": "trong_nuoc", "doanh_thu": 21_600_000}])[5]
    assert kq["co_so"] == "suy_tu_thue_suat"
    assert kq["vat_ra"] == pytest.approx(21_600_000 - 21_600_000 / 1.08, abs=1)
    assert kq["thue_gtgt"] == pytest.approx(1_600_000 - 740_740.74, abs=1)


def test_dong_chi_chua_nhap_hoa_don_thi_NOI_RA_chu_khong_im(db):
    """Chưa nhập thuế trên hoá đơn thì thuế phát sinh đang CAO hơn thực tế. Người đọc phải biết."""
    db.add(TourCostLine(tour_id=6, description="Ăn", actual=5_000_000, status="hd"))
    db.commit()
    kq = T.nhieu_chuyen(db, [{"tour_id": 6, "hinh_thuc": "trong_nuoc", "doanh_thu": 10_800_000}])[6]
    assert any("chưa nhập thuế trên hoá đơn" in c for c in kq["canh_bao"])


# =============================================================================================
# 3. Ba tầng kết quả
# =============================================================================================

def test_ba_tang_co_nhan_pham_vi_va_tang_ba_RONG_kem_ly_do():
    t = LL.ba_tang(100_000_000, 8_000_000)
    assert t["lai_gop_chuyen"] == 100_000_000
    assert t["sau_thue_gtgt"] == 92_000_000
    assert t["sau_chi_phi_chung"] is None, "chưa có cơ sở phân bổ được ký thì phải RỖNG"
    assert set(t["nhan"]) == {"lai_gop_chuyen", "sau_thue_gtgt", "sau_chi_phi_chung"}
    assert "chưa" in t["ly_do_thieu"]["sau_chi_phi_chung"].lower()


def test_thieu_thue_thi_tang_hai_RONG_chu_khong_tut_bang_tang_mot():
    """Một ô 'sau thuế' mà chưa trừ thuế là ô nói dối đúng vào chỗ nó hứa."""
    t = LL.ba_tang(100_000_000, None)
    assert t["lai_gop_chuyen"] == 100_000_000
    assert t["sau_thue_gtgt"] is None
    assert t["ly_do_thieu"]["sau_thue_gtgt"]


def test_thieu_gia_von_thi_ca_ba_tang_deu_RONG():
    t = LL.ba_tang(None, 5_000_000)
    assert t["lai_gop_chuyen"] is None and t["sau_thue_gtgt"] is None


# =============================================================================================
# 4. Thuế suất là THAM SỐ, không viết cứng
# =============================================================================================

def test_thue_suat_lay_tu_tham_so_va_doi_duoc_theo_ngay(db):
    from app.models.core import Param
    assert T.thue_suat_ra(db) == pytest.approx(0.08)
    db.add(Param(key=T.KHOA_THUE_SUAT_RA, value="0.10", label="x",
                 effective_from=date(2027, 1, 1), status="active",
                 signed_chutich=True, signed_tgd=True))
    db.commit()
    from app.services.rules import clear_param_cache
    clear_param_cache()
    assert T.thue_suat_ra(db, date(2027, 6, 1)) == pytest.approx(0.10)
    assert T.thue_suat_ra(db, date(2026, 6, 1)) == pytest.approx(0.08), \
        "chuyến đã đi phải giữ nguyên thuế suất của ngày nó khởi hành"
    clear_param_cache()
