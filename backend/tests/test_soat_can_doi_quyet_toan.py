# -*- coding: utf-8 -*-
"""Đ-3 · Ba phép kiểm, dựng lại bằng ba lỗi THẬT của ba tệp thật.

Mỗi phép thử dưới đây tái tạo đúng cơ chế của một lỗi đã tìm được, không phải một tình huống bịa:

  K-a  châu Âu 6 nước  – vé + bảo hiểm trưởng đoàn nằm CẢ ở dòng riêng CẢ trong cột đã phân bổ,
                          hai đường cộng lệch 22.517.431 đ
  K-b  Nha Trang       – ô tổng khối trẻ em bỏ sót dòng vé Tháp Bà 210.000 đ
  K-c                   – cơ chế gây ra K-a: một khoản vừa đích danh vừa chia đều
"""
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
import app.models.lop3_tour  # noqa: F401
import app.models.quyet_toan  # noqa: F401
import app.models.vietrip  # noqa: F401
from app.db.session import Base
from app.models.lop3_tour import BookingKhach
from app.models.quyet_toan import TourSettlement, TourSettlementCostLine
from app.models.vietrip import TourCostLine
from app.services import soat_can_doi_quyet_toan as S

TOUR = 1


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


def _khach(db, n, tour_id=TOUR):
    for i in range(1, n + 1):
        db.add(BookingKhach(booking_id=1, tour_id=tour_id, stt=i, ho_ten=f"KHACH {i}",
                            nhom_khach="tra_tien", loai_tuoi="nguoi_lon", gia_ban=53_900_000))
    db.commit()


def _dong(db, mo_ta, tien, quy_tac="deu_khach_co_thu", ma="", tour_id=TOUR):
    d = TourCostLine(tour_id=tour_id, description=mo_ta, actual=tien,
                     quy_tac_phan_bo=quy_tac, ma_khoan_muc=ma or None, status="hd")
    db.add(d)
    db.commit()
    return d


# =============================================================================================
# K-a
# =============================================================================================

def test_ka_dat_khi_moi_dong_chi_duoc_chia_dung_mot_lan(db):
    _khach(db, 30)
    _dong(db, "Land", 822_277_241)
    _dong(db, "Phí TL (đã phân bổ)", 30_844_081)
    kq = S.ka_hai_chieu_cong(db, TOUR)
    assert kq["dat"], kq["chi_tiet"]
    assert abs(kq["chenh"]) <= S.NGUONG_LAM_TRON


def test_ka_BAT_duoc_co_che_da_lam_lech_22_517_431_cua_tep_chau_au(db):
    """Chi phí trưởng đoàn đã chia đều về 30 khách qua cột PHÍ TL. Nếu ai đó thêm MỘT DÒNG NỮA cho
    chính khoản ấy — đúng như dòng 54 của tệp — thì hai đường cộng lệch ngay.

    Ở Excel hai con số ấy nằm cách nhau bốn mươi dòng và không ai đặt cạnh nhau bao giờ.
    """
    _khach(db, 30)
    _dong(db, "Phí TL (đã phân bổ cho 30 khách)", 30_844_081)
    # Dòng thứ hai cho CÙNG khoản tiền ấy, khai không phân bổ nên không vào vế trái.
    _dong(db, "Vé + BH của trưởng đoàn", 22_517_431, quy_tac="khong_phan_bo")
    kq = S.ka_hai_chieu_cong(db, TOUR)
    # Dòng khong_phan_bo không nằm trong phép so – nhưng số tiền của nó phải HIỆN RA.
    assert kq["so_lieu"]["tong_khong_phan_bo"] == pytest.approx(22_517_431)

    # Còn nếu dòng thứ hai ấy cũng được chia đều (đúng kiểu trộn chi phí gốc với bảng phân bổ) thì
    # tổng theo khách phồng lên đúng 22.517.431 so với những gì thật sự được chia một lần.
    d = db.scalars(sa.select(TourCostLine).where(
        TourCostLine.description.like("Vé + BH%"))).first()
    d.quy_tac_phan_bo = "deu_khach_co_thu"
    db.commit()
    kq2 = S.ka_hai_chieu_cong(db, TOUR)
    assert kq2["so_lieu"]["tong_theo_khach"] - 30_844_081 == pytest.approx(22_517_431, abs=1)


def test_ka_do_khi_mot_khoan_bi_chia_nhieu_hon_so_tien_no_co(db):
    """Mô phỏng trực tiếp: vế trái phồng lên mà vế phải không đổi."""
    _khach(db, 10)
    _dong(db, "Land", 100_000_000)
    db.add(TourCostLine(tour_id=TOUR, description="Land (ghi lại lần hai)", actual=50_000_000,
                        quy_tac_phan_bo="deu_khach_co_thu", status="hd"))
    db.commit()
    kq = S.ka_hai_chieu_cong(db, TOUR)
    assert kq["dat"], "hai dòng riêng biệt thì vẫn khớp – K-a không bắt được trùng lặp ở mức nội dung"
    assert kq["muc"] == "do"


def test_ka_noi_ra_tien_chua_khai_quy_tac_chu_khong_im(db):
    """Chuyến khớp phép kiểm mà còn 50 triệu chưa khai quy tắc thì tờ quyết toán VẪN chưa xong."""
    _khach(db, 10)
    _dong(db, "Chưa biết chia thế nào", 50_000_000, quy_tac="")
    kq = S.ka_hai_chieu_cong(db, TOUR)
    assert kq["dat"]
    assert kq["so_lieu"]["tong_chua_khai_quy_tac"] == pytest.approx(50_000_000)
    assert kq["so_lieu"]["so_dong_chua_khai"] == 1


# =============================================================================================
# K-b
# =============================================================================================

def _nha_trang(db, o_tong_chi):
    """Sheet CTT của tệp Nha Trang 10/07/2026, rút gọn còn đúng phần cần soát.

    Khối thu «I/GIÁ TOUR» cộng đủ 71.165.000; khối chi «B. TRẺ EM» có NĂM dòng, cộng đủ 4.200.000
    — trong khi ô tổng của tệp viết =SUM(G23:G26), tức chỉ bốn dòng.
    """
    s = TourSettlement(ky="2026-07", ma_tour="NT001.03100726", gia_von=o_tong_chi,
                       doanh_thu=71_165_000)
    db.add(s)
    db.commit()
    for mo_ta, tien in [("NGƯỜI LỚN 1.790.000 × 33", 59_070_000),
                        ("TRẺ EM 1.500.000 × 7", 10_500_000),
                        ("CHARGE HỦY KHÁCH", 895_000),
                        ("PHỤ THU GHẾ 100.000 × 7", 700_000)]:
        db.add(TourSettlementCostLine(settlement_id=s.id, ve="thu", nhom="I. GIÁ TOUR",
                                      noi_dung=mo_ta, thanh_tien=tien))
    for mo_ta, tien in [("Lưu trú – ăn sáng trẻ em", 1_120_000), ("Ăn trưa ngày 1", 805_000),
                        ("Ăn trưa ngày 2", 1_260_000), ("Ăn trưa ngày 3", 805_000),
                        ("Tham quan Tháp Bà (trẻ em)", 210_000)]:
        db.add(TourSettlementCostLine(settlement_id=s.id, ve="chi", nhom="B. TRẺ EM",
                                      noi_dung=mo_ta, thanh_tien=tien))
    db.commit()
    return s


def test_kb_BAT_duoc_210_000_ma_o_tong_nha_trang_bo_sot(db):
    s = _nha_trang(db, o_tong_chi=3_990_000)     # =SUM(G23:G26) – bỏ dòng thứ năm
    kq = S.kb_cong_lai_tu_dong(db, s.id)
    assert not kq["dat"]
    assert kq["so_lieu"]["cong_lai_chi"] == pytest.approx(4_200_000)
    assert kq["so_lieu"]["o_tong_chi_cua_tep"] == pytest.approx(3_990_000)
    assert kq["so_lieu"]["chenh_chi"] == pytest.approx(210_000)


def test_kb_KHONG_chan_theo_dung_chot_12_9_cua_chu_tich(db):
    """Chủ tịch chốt «số chi tiết là số chốt». Nên chênh ở đây là CẢNH BÁO, không phải hàng rào."""
    s = _nha_trang(db, o_tong_chi=3_990_000)
    kq = S.kb_cong_lai_tu_dong(db, s.id)
    assert kq["muc"] == "vang"
    tong = S.soat(db, TOUR, s.id)
    assert tong["duoc_dong_so"] is True
    assert tong["so_canh_bao"] >= 1


def test_kb_GIU_LAI_o_tong_cua_tep_chu_khong_xoa(db):
    """Ô tổng của tệp gốc là bằng chứng duy nhất còn lại của việc thiếu dòng. Đừng xoá nó."""
    s = _nha_trang(db, o_tong_chi=3_990_000)
    kq = S.kb_cong_lai_tu_dong(db, s.id)
    assert kq["so_lieu"]["o_tong_chi_cua_tep"] is not None


def test_kb_dat_khi_o_tong_khop_cong_du(db):
    s = _nha_trang(db, o_tong_chi=4_200_000)
    assert S.kb_cong_lai_tu_dong(db, s.id)["dat"]


def test_kb_o_tong_RONG_thi_khong_ket_luan(db):
    """Chưa ai điền ô tổng thì không có gì để so – không được coi là đạt vì khớp, cũng không đỏ."""
    s = _nha_trang(db, o_tong_chi=None)
    kq = S.kb_cong_lai_tu_dong(db, s.id)
    assert kq["so_lieu"]["o_tong_chi_cua_tep"] is None
    assert kq["dat"]


# =============================================================================================
# K-c
# =============================================================================================

def test_kc_do_khi_mot_khoan_vua_dich_danh_vua_chia_deu(db):
    """Vé máy bay là khoản mỗi khách một giá. Khai chia đều cho nó là mâu thuẫn ngay trên dòng."""
    _khach(db, 10)
    _dong(db, "Vé máy bay", 500_000_000, quy_tac="deu_khach_co_thu", ma="vc_ve_may_bay")
    kq = S.kc_mot_khoan_mot_cho(db, TOUR)
    assert not kq["dat"] and kq["muc"] == "do"
    assert kq["so_lieu"]["xung_dot"][0]["ma_khoan_muc"] == "vc_ve_may_bay"


def test_kc_dat_voi_khoan_chung_chia_deu_binh_thuong(db):
    _khach(db, 10)
    _dong(db, "Xe du lịch", 15_000_000, quy_tac="deu_khach_co_thu", ma="vc_xe_du_lich")
    assert S.kc_mot_khoan_mot_cho(db, TOUR)["dat"]


def test_kc_ma_la_thi_KHONG_ket_luan(db):
    """Chưa biết khoản mục là gì thì không kết luận nó đích danh hay không."""
    _khach(db, 10)
    _dong(db, "Khoản lạ", 1_000_000, quy_tac="deu_khach_co_thu", ma="khong_co_ma_nay")
    assert S.kc_mot_khoan_mot_cho(db, TOUR)["dat"]


def test_kc_chan_dong_so(db):
    _khach(db, 10)
    _dong(db, "Phí lãnh sự", 100_000_000, quy_tac="deu_khach_co_thu", ma="vs_phi_lsq")
    tong = S.soat(db, TOUR)
    assert tong["duoc_dong_so"] is False and tong["so_chan"] == 1


# =============================================================================================
# Giới hạn phải nói ra
# =============================================================================================

def test_bo_kiem_NOI_RA_gioi_han_cua_chinh_no(db):
    """Một bộ kiểm được tin quá mức là thứ làm người ta thôi tự nhìn."""
    _khach(db, 5)
    g = S.soat(db, TOUR)["gioi_han"]
    assert "KHÔNG bắt được" in g and "thuế" in g


def test_thieu_han_mot_dong_chi_thi_KHONG_phep_kiem_nao_bat_duoc(db):
    """Ghi lại bằng phép thử cái giá của lựa chọn «cộng lại từ dòng».

    Đây KHÔNG phải lỗi của bộ kiểm – đây là giới hạn đã biết, và nó phải hiện ra trong mã để làn
    sau không tưởng bộ kiểm này che hết mọi phía.
    """
    _khach(db, 10)
    _dong(db, "Land", 100_000_000)
    # Ai đó quên hẳn dòng khách sạn 50 triệu. Hai đường cộng vẫn khớp nhau tuyệt đối.
    kq = S.soat(db, TOUR)
    assert kq["duoc_dong_so"] is True
    assert all(k["dat"] for k in kq["phep_kiem"])
