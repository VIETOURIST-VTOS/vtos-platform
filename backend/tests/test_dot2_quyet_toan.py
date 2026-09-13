# -*- coding: utf-8 -*-
"""Đợt 2 của khối quyết toán — Đ-8 vé theo mã đặt chỗ · Đ-9 công nợ trưởng đoàn.

Hai mục này canh hai loại lỗi khác hẳn nhau:

  Đ-8  Một khối vé "trông cân" mà sai: hoàn vé ghi thành dòng vé âm, vé không có tên người, hoặc
       giữ 32 chỗ mà chỉ điền 30 tên rồi quá hạn xuất vé.

  Đ-9  Một tờ công nợ ra kết quả NGƯỢC CHIỀU mà mọi tổng vẫn cân — vì hai tệp mẫu của chính phòng
       Điều hành dùng hai quy ước dấu ngược nhau cho cùng một ý.

Số dùng ở đây lấy nguyên từ hai tệp thật (QuyetToan_27052026_UK và QUYẾT TOÁN TL châu Âu 27/05).
Số tròn vẫn xanh khi phép tính lệch vài phần trăm; số thật thì không.
"""
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
import app.models.lop3_tour  # noqa: F401
import app.models.vietrip  # noqa: F401
from app.db.session import Base
from app.models.lop3_tour import (LOAI_CONG_NO_TL, TourTlCongNo, TourVeKhach, TourVeMa,
                                  TourVeThanhToan)
from app.models.vietrip import TourCostLine
from app.services import cong_no_truong_doan as TLCN
from app.services import ve_may_bay as VMB
from app.services.rules import clear_param_cache

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
    clear_param_cache()
    with Session(eng) as s:
        yield s
    clear_param_cache()


def _ma(db, ma="2ZB8A1", cho=None, han=None, tour_id=TOUR):
    m = TourVeMa(tour_id=tour_id, ma_dat_cho=ma, hanh_trinh="SGN - LGW - SGN (RT)",
                 so_cho_giu=cho, han_xuat_ve=han)
    db.add(m); db.flush()
    return m


def _ve(db, ten, gia=None, loai="ve", ma_id=None, noi_dia=None, nang_hang=None,
        tien_te=None, ty_gia=None, ly_do=None, tour_id=TOUR):
    d = TourVeKhach(tour_id=tour_id, ve_ma_id=ma_id, ho_ten_ve=ten, loai=loai, gia_ve=gia,
                    gia_ve_noi_dia=noi_dia, phi_nang_hang=nang_hang,
                    tien_te=tien_te, ty_gia=ty_gia, ly_do=ly_do)
    d.thanh_tien = VMB.thanh_tien_dong(d)
    db.add(d); db.flush()
    return d


def _cn(db, loai, so_tien, tien_te="VND", ty_gia=None, noi_dung="", tour_id=TOUR, pc=None):
    d = TourTlCongNo(tour_id=tour_id, loai=loai, so_tien=so_tien, tien_te=tien_te,
                     ty_gia=ty_gia, noi_dung=noi_dung, phan_cong_id=pc)
    db.add(d); db.flush()
    return d


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-8 · VÉ MÁY BAY THEO MÃ ĐẶT CHỖ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_thanh_tien_dong_cong_bon_o_va_giu_rong_khac_khong():
    """Bốn ô rỗng thì thành tiền là CHƯA CÓ, không phải 0 đồng."""
    trong = TourVeKhach(tour_id=TOUR, loai="ve")
    assert VMB.thanh_tien_dong(trong) is None

    # PHAM DUNG trên tệp UK: giá vé 22.435.959, hoàn 9.210.459 ở cột vé nội địa -> 13.225.500
    d = TourVeKhach(tour_id=TOUR, loai="ve", gia_ve=22435959, gia_ve_noi_dia=-9210459)
    assert VMB.thanh_tien_dong(d) == 13225500.0

    # Một ô bằng 0 KHÁC bốn ô rỗng: người ta đã nhập, và số họ nhập là 0.
    assert VMB.thanh_tien_dong(TourVeKhach(tour_id=TOUR, loai="ve", gia_ve=0)) == 0.0


def test_khoi_theo_ma_do_may_cong_khong_co_o_cho_nguoi_go_tong(db):
    """Bảy dòng của mã 2ZB8A1 cộng lại đúng bằng con số tệp UK ghi ở khối trên."""
    m = _ma(db, "2ZB8A1", cho=7)
    for i in range(7):
        _ve(db, f"KHACH {i}", 22435959, ma_id=m.id)
    b = VMB.bang(db, TOUR)
    khoi = b["theo_ma"][0]
    assert khoi["tong_vnd"] == 7 * 22435959
    assert khoi["so_ve"] == 7
    assert khoi["con_thieu_ten"] == 0
    # Không có khoá nào cho người gõ tổng của một mã.
    assert "tong_nhap_tay" not in khoi and "tong_go" not in khoi


def test_giu_nhieu_cho_hon_so_ten_da_dien_thi_canh_bao_chu_khong_chan(db):
    """Giữ 32 chỗ, mới điền 30 tên – đó là việc phải làm, không phải lỗi."""
    m = _ma(db, "2ZB8A1", cho=32, han=date(2026, 12, 31))
    for i in range(30):
        _ve(db, f"KHACH {i}", 22435959, ma_id=m.id)
    s = VMB.soat(db, TOUR, hom_nay=date(2026, 9, 13))
    assert s["duoc_dong_so"] is True
    thieu = [c for c in s["canh_bao"] if c.get("con_thieu_ten")]
    assert len(thieu) == 1 and thieu[0]["con_thieu_ten"] == 2
    assert thieu[0]["qua_han"] is False


def test_qua_han_xuat_ve_ma_con_thieu_ten_thi_noi_ro_la_qua_han(db):
    m = _ma(db, "3EB620", cho=4, han=date(2026, 9, 1))
    _ve(db, "NGUYEN KIM HOA", 21927597, ma_id=m.id)
    s = VMB.soat(db, TOUR, hom_nay=date(2026, 9, 13))
    c = [x for x in s["canh_bao"] if x.get("qua_han")]
    assert len(c) == 1
    assert "QUÁ HẠN XUẤT VÉ" in c[0]["vi_sao"]


def test_chua_khai_so_cho_giu_thi_KHONG_kieu_la_thieu_ten(db):
    """Rỗng khác 0: chưa khai số chỗ giữ thì không so được, và không được kêu."""
    m = _ma(db, "3E45SN", cho=None)
    _ve(db, "LE TUAN KIET", 18781848, ma_id=m.id)
    b = VMB.bang(db, TOUR)
    assert b["theo_ma"][0]["con_thieu_ten"] is None
    s = VMB.soat(db, TOUR)
    assert not [x for x in s["canh_bao"] if "con_thieu_ten" in x]


def test_ve_khong_co_ten_khach_thi_CHAN(db):
    _ve(db, None, 22435959)
    s = VMB.soat(db, TOUR)
    assert s["duoc_dong_so"] is False
    assert any("TÊN KHÁCH" in c["vi_sao"] for c in s["chan"])


def test_hoan_ve_thieu_ly_do_thi_CHAN(db):
    _ve(db, "PHAM DUNG", -9210459, loai="hoan_ve")
    s = VMB.soat(db, TOUR)
    assert any("LÝ DO" in c["vi_sao"] for c in s["chan"])


def test_hoan_ve_mang_so_duong_thi_CHAN(db):
    """Hoàn vé là tiền chảy ngược về công ty – dấu dương làm nó cộng thêm vào giá vốn."""
    _ve(db, "PHAM DUNG", 9210459, loai="hoan_ve", ly_do="Khách huỷ chuyến")
    s = VMB.soat(db, TOUR)
    assert any("DƯƠNG" in c["vi_sao"] for c in s["chan"])


def test_ve_mang_so_am_thi_CHAN_va_chi_duong_dan_sang_loai_hoan_ve(db):
    """Đây chính là cách tệp UK ghi khoản hoàn ở khối trên – một dòng âm không có tên loại."""
    _ve(db, "NGUYEN THI KIM MY", -9210459, loai="ve")
    s = VMB.soat(db, TOUR)
    c = [x for x in s["chan"] if "ÂM" in x["vi_sao"]]
    assert len(c) == 1
    assert "Hoàn vé" in c[0]["vi_sao"]


def test_phi_khac_khong_duoc_dem_la_mot_cai_ve(db):
    """Mẫu SIN/MAL: «Phí loby 350.000» nằm cùng bảng vé nhưng không phải một cái vé."""
    m = _ma(db, "KCLWRD", cho=1)
    _ve(db, "KHACH A", 18839340, ma_id=m.id)
    _ve(db, "Phí loby", 350000, loai="phi_khac", ma_id=m.id)
    b = VMB.bang(db, TOUR)
    khoi = b["theo_ma"][0]
    assert khoi["so_dong"] == 2
    assert khoi["so_ve"] == 1                    # phí không được đếm là vé
    assert khoi["tong_vnd"] == 18839340 + 350000  # nhưng tiền vẫn vào tổng
    assert khoi["con_thieu_ten"] == 0


def test_phi_khac_khong_can_ten_khach(db):
    """Một khoản phí lobby không có «người đi» – bắt nó khai tên khách là bắt gõ tên giả."""
    _ve(db, "Phí loby", 350000, loai="phi_khac")
    s = VMB.soat(db, TOUR)
    assert s["duoc_dong_so"] is True


def test_ngoai_te_thieu_ty_gia_thi_KHONG_lot_vao_tong_va_phai_keu(db):
    """Thiếu tỷ giá thì 450 USD không được lặng lẽ cộng vào như 450 đồng."""
    _ve(db, "KHACH A", 1000, tien_te="USD", ty_gia=None)
    _ve(db, "KHACH B", 22435959)
    b = VMB.bang(db, TOUR)
    assert b["tong_tien_ve_vnd"] == 22435959      # dòng USD KHÔNG lọt vào
    assert b["so_dong_chua_quy_duoc_vnd"] == 1
    s = VMB.soat(db, TOUR)
    assert any("TỶ GIÁ" in c["vi_sao"] for c in s["canh_bao"])
    assert s["duoc_dong_so"] is True              # cảnh báo, không chặn


def test_so_du_dai_ly_la_mot_so_du_KHONG_phai_mot_dang_thuc(db):
    """Đặt cọc 30% thì hai con số lệch 70% – đó là tình trạng ĐÚNG, không phải sai sót.

    Đây chính là chỗ bản đề xuất sáng 12/9 viết sai («Σ giá vé = Σ thanh toán, lệch là CHẶN»).
    """
    _ve(db, "KHACH A", 100_000_000)
    db.add(TourVeThanhToan(tour_id=TOUR, so_tien=30_000_000, ngay=date(2026, 5, 1)))
    db.flush()
    s = VMB.soat(db, TOUR)
    assert s["tong_tien_ve_vnd"] == 100_000_000
    assert s["tong_da_thanh_toan_vnd"] == 30_000_000
    assert s["con_no_dai_ly"] == 70_000_000
    assert s["duoc_dong_so"] is True
    assert not [c for c in s["chan"] if "thanh toán" in c["vi_sao"]]


def test_tra_thua_cho_dai_ly_ra_so_du_AM_chu_khong_bi_kep_ve_0(db):
    """Tiền thừa nằm ở đại lý là tiền của công ty đang nằm ngoài két – phải nhìn thấy."""
    _ve(db, "KHACH A", 50_000_000)
    db.add(TourVeThanhToan(tour_id=TOUR, so_tien=60_000_000))
    db.flush()
    assert VMB.bang(db, TOUR)["con_no_dai_ly"] == -10_000_000


def test_tong_khoi_ve_lech_chiet_tinh_thi_canh_bao(db):
    _ve(db, "KHACH A", 100_000_000)
    db.add(TourCostLine(tour_id=TOUR, description="Vé máy bay", service_type="AIR",
                        actual=95_000_000, status="hd"))
    db.flush()
    s = VMB.soat(db, TOUR)
    c = [x for x in s["canh_bao"] if x.get("lech")]
    assert len(c) == 1 and c[0]["lech"] == 5_000_000
    assert s["duoc_dong_so"] is True


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-9 · CÔNG NỢ TRƯỞNG ĐOÀN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_to_UK_ba_dong_tien_ra_dung_ba_so_du_va_mot_so_gop(db):
    """Dựng lại nguyên tờ CongNo_HDV của QuyetToan_27052026_UK.

        GBP :  30,79 (TL trả dịch vụ)  −  126 (TL thu của khách)  =  −95,21
        USD :  450 (công tác phí)                                  =  +450
        quy về VND theo đúng hai tỷ giá ghi trên tờ (36.000 và 26.500):
               −95,21 × 36.000  = −3.427.560
               +450   × 26.500  = +11.925.000
               cộng              = +8.497.440   -> công ty còn phải trả TL
    """
    _cn(db, "tl_chi_ho", 30.79, "GBP", 36000, "Tổng dịch vụ thanh toán bằng TL")
    _cn(db, "tl_thu_ho_khach", -126, "GBP", 36000, "TL thu của khách – mua dùm vé tham quan")
    _cn(db, "cong_tac_phi", 450, "USD", 26500, "Công tác phí TL")

    s = TLCN.so_du(db, TOUR)
    theo = {x["tien_te"]: x for x in s["theo_tien_te"]}
    assert round(theo["GBP"]["so_du"], 2) == -95.21
    assert theo["GBP"]["so_du_vnd"] == -3427560.0
    assert theo["USD"]["so_du"] == 450.0
    assert theo["USD"]["so_du_vnd"] == 11925000.0
    assert s["so_du_vnd"] == 8497440.0
    assert s["ai_no_ai"] == "Công ty còn phải trả trưởng đoàn"
    # Hai vế NGƯỢC CHIỀU nhau – đó chính là lý do không được gộp sớm.
    assert theo["GBP"]["ai_no_ai"] == "Trưởng đoàn còn phải nộp lại"
    assert theo["USD"]["ai_no_ai"] == "Công ty còn phải trả trưởng đoàn"


def test_to_chau_AU_so_hoc_cua_chinh_no_chung_minh_dong_cuoi_ghi_nguoc_dau(db):
    """QUYẾT TOÁN TL châu Âu 27/05 ghi dòng cuối «CTY HOÀN TIỀN CHO TL  −60».

        CTP HDV 270 + city tax 120 + Riepilogo 480          = 870 €  (công ty nợ TL)
        trừ tiền tip nộp công ty 810 €                                (TL nợ công ty)
        còn lại  +60 €  ->  công ty trả TL 60 €, ĐÚNG như nhãn, NGƯỢC dấu tờ ghi.

    Nên khi chép tờ này vào hệ thống, dòng cuối phải đổi dấu. Phép thử này là chỗ ghi lại điều ấy.
    """
    _cn(db, "cong_tac_phi", 270, "EUR", 27000, "CTP HDV 9 ngày")
    _cn(db, "tl_chi_ho", 120, "EUR", 27000, "City tax tại Milan")
    _cn(db, "tl_chi_ho", 480, "EUR", 27000, "Riepilogo Paiale - NH Regina")
    _cn(db, "tip_nop_cong_ty", -810, "EUR", 27000, "Tiền tip nộp công ty 3€/pax/day × 9 × 30")

    s = TLCN.so_du(db, TOUR)
    eur = s["theo_tien_te"][0]
    assert eur["tien_te"] == "EUR"
    assert eur["so_du"] == 60.0
    assert s["ai_no_ai"] == "Công ty còn phải trả trưởng đoàn"


def test_dau_mau_thuan_voi_loai_khoan_thi_CHAN(db):
    """Chép nguyên dấu của tờ châu Âu vào – đây là lúc cái lưới phải bắt được."""
    _cn(db, "cong_tac_phi", -60, "EUR", 27000, "CTY HOÀN TIỀN CHO TL + CTP")
    s = TLCN.soat(db, TOUR)
    assert s["duoc_dong_so"] is False
    assert any("DƯƠNG" in c["vi_sao"] for c in s["chan"])
    # Câu quy ước phải đi kèm lời chặn, không bắt người ta đi tìm ở chỗ khác.
    assert any("nộp lại" in c["can_lam"].lower() for c in s["chan"])


def test_tip_nop_cong_ty_ghi_duong_cung_bi_CHAN(db):
    """Chiều ngược lại của cùng một lỗi: tiền TL nộp về mà ghi dấu dương."""
    _cn(db, "tip_nop_cong_ty", 810, "EUR", 27000)
    s = TLCN.soat(db, TOUR)
    assert any("ÂM" in c["vi_sao"] for c in s["chan"])


def test_moi_loai_khoan_deu_khai_chieu_va_khong_loai_nao_chieu_0():
    """Một loại khoản không khai chiều là một lỗ hổng của cả cái lưới."""
    for ma, (chieu, ten) in LOAI_CONG_NO_TL.items():
        assert chieu in (1, -1), f"loại {ma} khai chiều {chieu}"
        assert len(ten) > 15, f"loại {ma} mô tả quá ngắn để người nhập chọn đúng"


def test_loai_khong_co_trong_danh_muc_thi_CHAN(db):
    _cn(db, "linh_tinh", 100, "VND")
    s = TLCN.soat(db, TOUR)
    assert any("không có trong danh mục" in c["vi_sao"] for c in s["chan"])


def test_thieu_ty_gia_thi_so_gop_VND_KHONG_CO_chu_khong_bang_0(db):
    """450 USD nhân 0 bằng 0 và tờ vẫn cân – đúng kiểu sai mà không ai nhìn thấy."""
    _cn(db, "cong_tac_phi", 450, "USD", None)
    _cn(db, "tl_chi_ho", 1_000_000, "VND")
    s = TLCN.soat(db, TOUR)
    assert s["so_du_vnd"] is None
    assert s["ai_no_ai"] is None
    usd = [x for x in s["theo_tien_te"] if x["tien_te"] == "USD"][0]
    assert usd["so_du_vnd"] is None
    assert usd["so_du"] == 450.0        # số dư theo đồng tiền VẪN CÓ – vẫn đi trả được
    assert any("TỶ GIÁ" in c["vi_sao"] for c in s["canh_bao"])
    assert s["duoc_dong_so"] is True    # cảnh báo, không chặn


def test_hai_ty_gia_khac_nhau_cho_cung_mot_dong_tien_thi_CHAN(db):
    """Không có cách nào chọn hộ một cái đúng, nên không được chọn."""
    _cn(db, "cong_tac_phi", 450, "USD", 26500)
    _cn(db, "tl_chi_ho", 100, "USD", 25000)
    s = TLCN.soat(db, TOUR)
    assert any("HAI tỷ giá" in c["vi_sao"] for c in s["chan"])


def test_hai_truong_doan_thi_hai_to_khong_cong_chung(db):
    """Cộng chung hai người là mất đúng thông tin «ai nợ ai»."""
    _cn(db, "cong_tac_phi", 300, "VND", pc=11)
    _cn(db, "tip_nop_cong_ty", -500, "VND", pc=22)
    assert TLCN.so_du(db, TOUR)["so_du_vnd"] == -200          # gộp cả chuyến
    assert TLCN.so_du(db, TOUR, phan_cong_id=11)["so_du_vnd"] == 300
    assert TLCN.so_du(db, TOUR, phan_cong_id=22)["so_du_vnd"] == -500


def test_dong_rong_so_tien_thi_bao_chu_khong_coi_la_0(db):
    _cn(db, "cong_tac_phi", None, "USD", 26500, "Chưa biết bao nhiêu")
    s = TLCN.soat(db, TOUR)
    usd = s["theo_tien_te"][0]
    assert usd["so_dong_chua_co_so"] == 1
    assert usd["so_du"] == 0.0
    assert any("chưa nhập số tiền" in c["vi_sao"] for c in s["canh_bao"])


def test_quy_uoc_dau_di_kem_ket_qua_chu_khong_nam_o_tep_khac(db):
    """Một quy ước dấu viết ở hai chỗ là một quy ước sẽ có ngày lệch nhau."""
    s = TLCN.so_du(db, TOUR)
    assert "DƯƠNG" in s["quy_uoc_dau"] and "ÂM" in s["quy_uoc_dau"]
    assert "châu Âu" in s["quy_uoc_dau"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA – đường phải có mặt, và phải chặn NGAY TẠI CỬA chứ không đợi tới lúc đóng số
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_nam_duong_moi_deu_co_mat():
    from app.api.v1 import quyet_toan_lop3 as R
    duong = {getattr(r, "path", "") for r in R.router.routes}
    for p in ("/ve/ma", "/ve/khach", "/ve/thanh-toan", "/tl-cong-no", "/ve/loai",
              "/tl-cong-no/loai"):
        assert any(x.endswith(p) for x in duong), f"thiếu đường {p}"


def test_cua_cong_no_TL_chan_ngay_khi_dau_nguoc_chu_khong_doi_toi_luc_dong_so():
    """Người nhập phải biết lúc đang gõ, không phải lúc đi đóng số hai ngày sau.

    Đọc thẳng mã của cửa chứ không dựng máy chủ: phép thử này canh rằng lời chặn CÒN Ở CỬA, và một
    phép thử đọc chuỗi đủ để bắt lại đúng chuyện ấy mà chạy trong nửa giây.
    """
    import inspect
    from app.api.v1 import quyet_toan_lop3 as R
    ma = inspect.getsource(R.them_tl_cong_no)
    assert "chieu_cua_loai" in ma, "cửa không tra chiều dấu của loại khoản"
    assert "CAU_QUY_UOC" in ma, "lời chặn không kèm câu quy ước – bắt người ta đi tìm ở chỗ khác"


def test_cua_ve_chan_ngay_khi_hoan_ve_thieu_ly_do():
    import inspect
    from app.api.v1 import quyet_toan_lop3 as R
    ma = inspect.getsource(R.them_ve_khach)
    assert "hoan_ve" in ma and "LÝ DO" in ma


def test_cua_ve_KHONG_nhan_tham_so_thanh_tien():
    """Máy cộng, người không gõ tổng – kể cả tổng của một dòng."""
    from app.api.v1.quyet_toan_lop3 import VeKhachVao
    assert "thanh_tien" not in VeKhachVao.model_fields
    for o in ("gia_ve", "gia_ve_noi_dia", "phi_khac", "phi_nang_hang"):
        assert o in VeKhachVao.model_fields


def test_mach_nang_cap_van_chi_co_MOT_dau_sau_dot_2():
    """Đã gãy hai lần ngày 11/9, cả hai lần vì hai làn nối vào cùng một cha."""
    import pathlib
    import re
    goc = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    rev, cha = set(), set()
    for p in goc.glob("*.py"):
        s = p.read_text(encoding="utf-8", errors="replace")
        r = re.search(r'^revision(?::\s*str)?\s*=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision(?::\s*[^=]+)?\s*=\s*(?:["\']([^"\']+)["\']|None)', s, re.M)
        if r:
            rev.add(r.group(1))
        if d and d.group(1):
            cha.add(d.group(1))
    dau = rev - cha
    assert len(dau) == 1, f"Mạch nâng cấp có {len(dau)} đầu: {sorted(dau)}"
