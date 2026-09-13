# -*- coding: utf-8 -*-
"""Đợt 3 của khối quyết toán — Đ-4 nhiều bên bán · Đ-6b hoàn tip · Đ-12 lãnh sự · Đ-5 dịch vụ lẻ.

Số dùng ở đây lấy nguyên từ hai tệp thật của phòng Điều hành và đã được cộng lại bằng tay trước khi
viết vào phép thử:

    AU.xlsx, sheet "CÔNG NỢ JTRAVEL 27.05"    tổng 168.955.150,6  · còn 138.955.150,6
    AU.xlsx, sheet "CÔNG NỢ VTOURIST 27.05"   tổng 277.000.584,33 · còn  99.673.516,33
    AU.xlsx, sheet "PHÍ LSQ"                  18 khách · 14.040.000 + 49.122.500 = 63.162.500

Một điều tệp này ghi lại để không ai làm lại: bản đề xuất 12/9 đòi hai bảng mới cho Đ-5. Đo lại
ngày 13/9 thì VTOS đã có đủ, nên Đ-5 làm bằng một bảng tổng hợp ĐỌC từ dữ liệu đang có. Phép thử
`test_d5_KHONG_dung_bang_moi_nao` canh đúng chỗ ấy.
"""
from datetime import date, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

import app.models.core  # noqa: F401
import app.models.lop3_tour  # noqa: F401
import app.models.vietrip  # noqa: F401
from app.db.session import Base
from app.models.lop3_tour import (BookingKhach, DeNghiLanhSu, DeNghiLanhSuDong, TourBenBan,
                                  TourBenBanDong)
from app.services import ben_ban_tour as BBT
from app.services import de_nghi_lanh_su as DNLS
from app.services import dich_vu_le_thang as DVL
from app.services import tip_tour as TIP
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


def _ben(db, ten, nl=None, nha=False, tour_id=TOUR):
    b = TourBenBan(tour_id=tour_id, ten_ben=ten, so_khach_nguoi_lon=nl,
                   la_vietourist=1 if nha else 0)
    db.add(b); db.flush()
    return b


def _dong(db, ben, noi_dung, don_gia, so_luong, loai="phan_bo", cach="moi_khach", tour_id=TOUR):
    d = TourBenBanDong(tour_id=tour_id, ben_ban_id=ben.id, noi_dung=noi_dung, loai=loai,
                       cach_chia=cach, don_gia=don_gia, so_luong=so_luong,
                       thanh_tien=BBT.thanh_tien_dong(don_gia, so_luong))
    db.add(d); db.flush()
    return d


def _khach(db, n, tour_id=TOUR):
    for i in range(n):
        db.add(BookingKhach(tour_id=tour_id, booking_id=1, ho_ten=f"KHACH {i}"))
    db.flush()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-4 · NHIỀU BÊN BÁN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_to_JTRAVEL_dung_nguyen_so_cua_tep_that(db):
    """Tám dòng của tờ J TRAVEL cộng lại đúng 168.955.150,6 và còn nợ 138.955.150,6."""
    j = _ben(db, "J TRAVEL", nl=3)
    # Chi phí chung HDV chia theo ĐẦU KHÁCH toàn chuyến: 30.979.080,84 × 3/30
    _dong(db, j, "Chi phí chung HDV", 30979080.83870968 / 30, 3, cach="chia_dau_khach")
    _dong(db, j, "Vé máy bay", 22425780.83870968, 3)
    _dong(db, j, "Landtour ADL", 27931000, 3)
    _dong(db, j, "TIP HDV hoàn cho JTR", -837000, 3, loai="hoan_tip")
    _dong(db, j, "VISA người lớn 4 pax", 3587000, 4)      # 4 suất cho bên có 3 khách – xem test dưới
    _dong(db, j, "VISA Premium 1pax", 1200000, 1)
    _dong(db, j, "Phí điều hành + Dịch thuật", 300000, 4)
    _dong(db, j, "Bảo hiểm", 183300, 3)
    _dong(db, j, "Đã cọc", 30000000, 1, loai="thanh_toan")

    x = BBT.bang(db, TOUR)["ben"][0]
    assert round(x["tong_phai_thu"], 1) == 168955150.6
    assert x["da_thanh_toan"] == 30000000
    assert round(x["con_phai_thu"], 1) == 138955150.6


def test_to_VTOURIST_dung_nguyen_so_cua_tep_that(db):
    v = _ben(db, "VTOURIST", nl=5)
    _dong(db, v, "Chi phí chung HDV", 30979080.83870968 / 30, 5, cach="chia_dau_khach")
    _dong(db, v, "Vé máy bay", 22425780.83870968, 5)
    _dong(db, v, "Landtour ADL", 27931000, 5)
    _dong(db, v, "TIP HDV hoàn cho JTR", -837000, 5, loai="hoan_tip")
    _dong(db, v, "VISA người lớn 6 pax", 3587000, 6)
    _dong(db, v, "Phí điều hành + Dịch thuật", 300000, 6)
    _dong(db, v, "Bảo hiểm", 183300, 5)
    _dong(db, v, "Cọc lần 1", 20000000, 1, loai="thanh_toan")
    _dong(db, v, "Fullpay VMB", 157327068, 1, loai="thanh_toan")

    x = BBT.bang(db, TOUR)["ben"][0]
    assert round(x["tong_phai_thu"], 2) == 277000584.33
    assert x["da_thanh_toan"] == 177327068
    assert round(x["con_phai_thu"], 2) == 99673516.33


def test_ba_ben_cong_lai_bang_so_khach_tren_chuyen(db):
    """3 + 5 + 22 = 30, đúng đầu bảng «30A+1TL» của tệp."""
    _ben(db, "J TRAVEL", nl=3)
    _ben(db, "VTOURIST", nl=5)
    _ben(db, "VIETOURIST", nl=22, nha=True)
    _khach(db, 30)
    s = BBT.soat(db, TOUR)
    assert s["tong_khach_cac_ben"] == 30
    assert s["khach_tren_chuyen"] == 30
    assert s["duoc_dong_so"] is True


def test_so_khach_cac_ben_lech_danh_sach_khach_thi_CHAN(db):
    """Có người ngồi trên xe mà không thuộc bên nào – mọi phép chia đầu khách sai theo."""
    _ben(db, "J TRAVEL", nl=3)
    _ben(db, "VIETOURIST", nl=22, nha=True)
    _khach(db, 30)
    s = BBT.soat(db, TOUR)
    assert s["duoc_dong_so"] is False
    c = [x for x in s["chan"] if "lech" in x]
    assert len(c) == 1 and c[0]["lech"] == -5


def test_so_luong_dong_khac_so_khach_cua_ben_thi_CANH_BAO_chu_khong_chan(db):
    """Tờ thật: bên 3 khách mà dòng VISA ghi 4 suất. Chuyện ấy CÓ THẬT."""
    j = _ben(db, "J TRAVEL", nl=3)
    _dong(db, j, "VISA người lớn 4 pax", 3587000, 4)
    _khach(db, 3)
    s = BBT.soat(db, TOUR)
    assert s["duoc_dong_so"] is True
    c = [x for x in s["canh_bao"] if x.get("so_luong") == 4]
    assert len(c) == 1 and c[0]["so_khach"] == 3


def test_may_KHONG_tu_dien_so_luong_tu_so_khach(db):
    """Tự điền là biến một sự thật nghiệp vụ thành một lỗi lặng lẽ."""
    j = _ben(db, "J TRAVEL", nl=3)
    d = _dong(db, j, "VISA", 3587000, 4)
    db.refresh(d)
    assert d.so_luong == 4                       # giữ nguyên số người nhập
    assert d.thanh_tien == 4 * 3587000           # và nhân theo số ấy, không theo 3


def test_dong_chia_dau_khach_KHONG_bi_kieu_la_lech(db):
    """Dòng chia theo đầu khách có số lượng bằng số khách của bên – không được kêu."""
    j = _ben(db, "J TRAVEL", nl=3)
    _dong(db, j, "Chi phí chung HDV", 30979080.83870968 / 30, 3, cach="chia_dau_khach")
    _khach(db, 3)
    s = BBT.soat(db, TOUR)
    assert not [x for x in s["canh_bao"] if "so_luong" in x]


def test_hoan_tip_ghi_so_DUONG_thi_CHAN(db):
    """Khoản giảm trừ mang dấu dương làm nợ của đại lý phồng lên thay vì giảm đi."""
    j = _ben(db, "J TRAVEL", nl=3)
    _dong(db, j, "TIP HDV hoàn cho JTR", 837000, 3, loai="hoan_tip")
    s = BBT.soat(db, TOUR)
    assert s["duoc_dong_so"] is False
    assert any("DƯƠNG" in c["vi_sao"] for c in s["chan"])


def test_nhieu_ben_ma_khong_ben_nao_la_vietourist_thi_CANH_BAO(db):
    """Để Vietourist là «phần còn lại» thì lúc số khách lệch, phần thiếu tự chảy vào nó."""
    _ben(db, "J TRAVEL", nl=3)
    _ben(db, "VTOURIST", nl=5)
    s = BBT.soat(db, TOUR)
    assert any("VIETOURIST" in c["vi_sao"] for c in s["canh_bao"])


def test_ben_chua_khai_khach_thi_KHONG_so_va_KHONG_chan(db):
    _ben(db, "J TRAVEL", nl=None)
    _khach(db, 30)
    s = BBT.soat(db, TOUR)
    assert s["tong_khach_cac_ben"] is None
    assert s["duoc_dong_so"] is True
    assert any("chưa khai số khách" in c["vi_sao"] for c in s["canh_bao"])


def test_thanh_tien_dong_giu_rong_khac_khong():
    assert BBT.thanh_tien_dong(None, 3) is None
    assert BBT.thanh_tien_dong(1000, None) is None
    assert BBT.thanh_tien_dong(0, 3) == 0.0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-6b · HOÀN TIP VỀ BÊN BÁN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_tip_hoan_khop_giua_HAI_tep_khac_nhau(db):
    """Tệp châu Âu ghi 3 €/khách/ngày × 9 ngày; tệp AU ghi hoàn 837.000/khách. 27 × 31.000 = 837.000."""
    j = _ben(db, "J TRAVEL", nl=3)
    _ben(db, "VIETOURIST", nl=22, nha=True)
    kq = BBT.xem_truoc_hoan_tip(db, TOUR, don_gia=3, don_vi="moi_khach_moi_ngay",
                                so_ngay=9, ty_gia=31000)
    theo = {x["ten_ben"]: x["so_tien_hoan"] for x in kq["theo_ben"]}
    assert theo["J TRAVEL"] == 3 * 837000        # 2.511.000 – đúng dòng của tệp AU
    assert "VIETOURIST" not in theo              # công ty không hoàn tiền cho chính mình
    assert kq["so_ben_bo_qua_vi_la_vietourist"] == 1
    assert j.id


def test_tip_hoan_hai_don_vi_ra_hai_ket_qua_khac_nhau(db):
    """Gõ đơn giá cả-chuyến vào ô mỗi-ngày là ra GẤP CHÍN LẦN. Đơn vị không có mặc định."""
    _ben(db, "J TRAVEL", nl=3)
    ca_chuyen = BBT.xem_truoc_hoan_tip(db, TOUR, don_gia=27, don_vi="moi_khach_ca_chuyen",
                                       so_ngay=9, ty_gia=31000)["tong_hoan"]
    moi_ngay = BBT.xem_truoc_hoan_tip(db, TOUR, don_gia=27, don_vi="moi_khach_moi_ngay",
                                      so_ngay=9, ty_gia=31000)["tong_hoan"]
    assert ca_chuyen == 3 * 837000
    assert moi_ngay == 9 * ca_chuyen


def test_tip_hoan_thieu_don_vi_thi_KHONG_TINH_chu_khong_doan(db):
    _ben(db, "J TRAVEL", nl=3)
    assert BBT.xem_truoc_hoan_tip(db, TOUR, don_gia=27, don_vi=None)["tong_hoan"] is None


def test_ham_chia_tip_van_la_MOT_cho_duy_nhat():
    """`ben_ban_tour` gọi lại `tip_tour.hoan_cho_ben_ban`, không viết một phép chia thứ hai."""
    import inspect
    ma = inspect.getsource(BBT.xem_truoc_hoan_tip)
    assert "TIP.hoan_cho_ben_ban" in ma
    assert TIP.hoan_cho_ben_ban(27, "moi_khach_ca_chuyen", None, {"X": 3}, 31000) == {"X": 2511000}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-12 · ĐỀ NGHỊ CHI PHÍ LÃNH SỰ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _to(db, **kw):
    t = DeNghiLanhSu(ngay=date(2026, 5, 20), thi_truong="SCHENGEN", **kw)
    db.add(t); db.flush()
    return t


def _kh(db, to, ten, ns=None, lsq=2807000, co_ban=780000, sale=None, ben=None):
    d = DeNghiLanhSuDong(de_nghi_id=to.id, ho_ten=ten, ngay_sinh=ns, sale=sale,
                         ben_ban_id=ben, phi_tls_co_ban=co_ban, phi_lsq=lsq)
    d.thanh_tien = DNLS.thanh_tien_dong(d)
    db.add(d); db.flush()
    return d


def test_to_PHI_LSQ_dung_nguyen_so_cua_tep_that(db):
    """18 khách: 17 người nguyên giá + 1 cháu nửa giá = 49.122.500 phí LSQ, tổng 63.162.500."""
    t = _to(db)
    for i in range(17):
        _kh(db, t, f"KHACH {i}", ns=date(1980, 1, 1 + i % 28))
    _kh(db, t, "NGUYEN CAT MAI ANH", ns=date(2015, 10, 30), lsq=1403500)
    b = DNLS.bang(db, t.id)
    assert b["tong_phi_tls_co_ban"] == 14040000
    assert b["tong_phi_lsq"] == 49122500
    assert b["tong_thanh_toan"] == 63162500


def test_he_thong_KHONG_cai_moc_tuoi_nao():
    """Một cháu 11 tuổi trả nửa giá, một cháu 13 tuổi trả nguyên giá – mốc là quy định của LSQ."""
    import inspect
    ma = inspect.getsource(DNLS)
    for xau in ("tuoi <", "tuoi >", "age <", "age >", "< 12", "<= 12", "< 6", "years"):
        assert xau not in ma, f"mã có vẻ đang cài mốc tuổi: {xau!r}"
    assert "bang_gia" in ma          # và nói rõ biểu phí sống ở đâu


def test_mot_nguoi_dung_HAI_LAN_tren_cung_mot_to_thi_CHAN(db):
    """Nộp trùng thì chi trùng. Ở mức 2,8 triệu một suất, một dòng lặp là tiền thật đi ra."""
    t = _to(db)
    _kh(db, t, "TRAN SI THONG", ns=date(1980, 10, 18))
    _kh(db, t, " tran si  thong ", ns=date(1980, 10, 18))   # gõ khác hoa thường và thừa khoảng trắng
    s = DNLS.soat(db, t.id)
    assert s["duoc_trinh"] is False
    c = [x for x in s["chan"] if x.get("so_lan")]
    assert len(c) == 1 and c[0]["so_lan"] == 2
    assert c[0]["tong_tien"] == 2 * 3587000


def test_trung_ten_nhung_KHAC_ngay_sinh_thi_KHONG_bi_bao_trung(db):
    """Hai người trùng tên là chuyện bình thường – gộp nhầm họ còn tệ hơn bỏ sót."""
    t = _to(db)
    _kh(db, t, "NGUYEN VAN A", ns=date(1980, 1, 1))
    _kh(db, t, "NGUYEN VAN A", ns=date(1995, 6, 30))
    s = DNLS.soat(db, t.id)
    assert not [x for x in s["chan"] if x.get("so_lan")]


def test_thieu_ngay_sinh_thi_KHONG_doan_la_trung(db):
    """Thiếu một trong hai vế nhận dạng thì không nhận dạng được, và không được đoán."""
    t = _to(db)
    _kh(db, t, "NGUYEN VAN A", ns=None)
    _kh(db, t, "NGUYEN VAN A", ns=None)
    s = DNLS.soat(db, t.id)
    assert not [x for x in s["chan"] if x.get("so_lan")]
    assert len([x for x in s["canh_bao"] if "NGÀY SINH" in x["vi_sao"]]) == 2


def test_dong_khong_co_ten_thi_CHAN(db):
    t = _to(db)
    _kh(db, t, None)
    assert any("HỌ TÊN" in c["vi_sao"] for c in DNLS.soat(db, t.id)["chan"])


def test_ca_ba_o_phi_deu_rong_thi_CHAN(db):
    t = _to(db)
    _kh(db, t, "NGUYEN VAN A", ns=date(1980, 1, 1), lsq=None, co_ban=None)
    s = DNLS.soat(db, t.id)
    assert any("không đề nghị chi gì" in c["vi_sao"] for c in s["chan"])


def test_to_visa_le_KHONG_can_tour(db):
    """Ép phải có tour là chặn đúng mảng visa lẻ – nơi những tờ này xuất hiện nhiều nhất."""
    t = _to(db, tour_id=None)
    _kh(db, t, "NGUYEN VAN A", ns=date(1980, 1, 1))
    s = DNLS.soat(db, t.id)
    assert s["tour_id"] is None
    assert s["duoc_trinh"] is True


def test_sale_la_ten_dai_ly_ma_chua_noi_ben_ban_thi_CANH_BAO(db):
    """Cột SALE của tệp thật có cả «JTRAVEL» – khoản phí ấy phải chảy về tờ công nợ của họ."""
    j = _ben(db, "J TRAVEL", nl=3)
    t = _to(db, tour_id=TOUR)
    _kh(db, t, "TRAN THI NU", ns=date(1981, 12, 20), sale="JTRAVEL")
    _kh(db, t, "NGUYEN VAN B", ns=date(1980, 1, 1), sale="THU HỒNG")   # sale là người, có dấu cách
    s = DNLS.soat(db, t.id)
    c = [x for x in s["canh_bao"] if x.get("sale")]
    assert len(c) == 1 and c[0]["sale"] == ["JTRAVEL"]
    assert j.id


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Đ-5 · DỊCH VỤ LẺ THEO THÁNG — MỘT CÁCH NHÌN, KHÔNG PHẢI MỘT SỔ MỚI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_d5_KHONG_dung_bang_moi_nao():
    """Bản đề xuất 12/9 đòi hai bảng mới. Đo lại 13/9: VTOS đã có đủ, nên KHÔNG dựng bảng nào.

    Phép thử này canh chính quyết định ấy. Nó đỏ khi ai đó dựng lại sổ thứ ba – và lúc ấy hãy đọc
    phần đầu `services/dich_vu_le_thang.py` trước khi sửa phép thử.
    """
    from app.db.session import Base as B
    for ten in ("dich_vu_le_thang", "dich_vu_le_dong"):
        assert ten not in B.metadata.tables, (
            f"Bảng {ten} đã được dựng lại. VTOS đã có /non-package làm đúng sổ ấy theo tháng, đã "
            "có bốn mã khoản mục cho bốn cột chi, và tour_cost_lines đã mang được ngoại tệ. Sổ thứ "
            "ba sẽ KHÔNG sinh bút toán, nên số của Kế toán tách làm hai nguồn.")


def _dich_vu_le(db, ma, ten_khach, gia_ban=None, chi=None, o_gop=None, ghi_chu="",
                huy=False, thang=6, nam=2026):
    """Dựng một dịch vụ lẻ đúng cách VTOS đang làm: chuyến non_package + booking + dòng chi phí."""
    from app.models.core import Booking, Tour
    from app.models.vietrip import TourCostLine
    t = Tour(code=ma, name=ten_khach, tour_type="non_package", operator_id=1,
             start_date=date(nam, thang, 15), end_date=date(nam, thang, 15))
    db.add(t); db.flush()
    b = Booking(code=f"B{ma}", tour_id=t.id, request_id=1, sales_id=1, created_by=1,
                customer_name=ten_khach, customer_phone="0900", source="test",
                care_note=ghi_chu, service_type="VISA", amount=gia_ban, cost_amount=o_gop,
                cancelled=huy, created_at=datetime(nam, thang, 15, 9, 0))
    db.add(b); db.flush()
    for ma_km, so_tien in (chi or []):
        db.add(TourCostLine(tour_id=t.id, description=ma_km, ma_khoan_muc=ma_km,
                            actual=so_tien, status="hd"))
    db.flush()
    return t, b


def test_d5_dung_lai_dung_hinh_to_VISA_THANG_06(db):
    """Tệp thật «THÁNG 06.2026»: giá bán 7.000.000, phí LSQ 4.000.000, phí ĐH 200.000,
    phí dịch thuật 100.000 – bốn cột chi đứng cạnh nhau trên một dòng khách."""
    _dich_vu_le(db, "KLE150626", "NGUYEN THU HUE", gia_ban=7000000, chi=[
        ("vs_phi_lsq", 4000000), ("hd_phi_dieu_hanh", 200000), ("vs_dich_thuat", 100000)])
    b = DVL.bang(db, 2026, 6)
    assert b["so_dong"] == 1
    d = b["dong"][0]
    assert d["tong_thu"] == 7000000
    assert d["phi_lsq"] == 4000000
    assert d["phi_dieu_hanh"] == 200000
    assert d["phi_dich_thuat"] == 100000
    assert d["phi_dich_vu_visa"] is None          # tệp không có khoản này – RỖNG, không phải 0
    assert d["tong_chi"] == 4300000
    assert d["lai"] == 2700000
    assert d["nguon_chi"] == "dong_chi_phi"


def test_d5_co_doanh_thu_ma_KHONG_co_dong_gia_von_nao_thi_CHAN(db):
    """Lãi của nó đang bằng đúng toàn bộ số thu, và con số ấy đi thẳng vào báo cáo tháng."""
    _dich_vu_le(db, "KLE160626", "TRAN VAN B", gia_ban=5000000)
    s = DVL.soat(db, 2026, 6)
    assert s["duoc_chot_thang"] is False
    c = [x for x in s["chan"] if x.get("ma") == "KLE160626"]
    assert len(c) == 1 and "KHÔNG có một dòng giá vốn nào" in c[0]["vi_sao"]


def test_d5_chua_khai_gia_ban_thi_tong_thu_CHUA_CO_chu_khong_bang_0(db):
    """Cố ý khác `nonpackage.summary()` – với một bảng SOÁT thì đọc rỗng thành 0 là làm biến mất
    đúng thứ cần soi."""
    _dich_vu_le(db, "KLE170626", "LE THI C", gia_ban=None,
                chi=[("vs_phi_lsq", 4000000)])
    b = DVL.bang(db, 2026, 6)
    d = b["dong"][0]
    assert d["tong_thu"] is None
    assert d["lai"] is None
    assert b["so_dong_chua_tinh_duoc_lai"] == 1
    s = DVL.soat(db, 2026, 6)
    assert any("CHƯA PHỦ HẾT" in c["vi_sao"] for c in s["canh_bao"])


def test_d5_khoan_ngoai_bon_cot_gom_vao_phi_khac_chu_khong_bien_mat(db):
    _dich_vu_le(db, "KLE180626", "PHAM VAN D", gia_ban=9000000, chi=[
        ("vs_phi_lsq", 4000000), ("qt_non", 50000)])
    d = DVL.bang(db, 2026, 6)["dong"][0]
    assert d["phi_khac"] == 50000
    assert d["tong_chi"] == 4050000          # cả hai đều nằm trong tổng chi


def test_d5_gia_von_lay_o_GOP_thi_CANH_BAO_va_bon_cot_rong(db):
    """Ô gộp không tách được bốn khoản và không đối chiếu được với hoá đơn đầu vào."""
    _dich_vu_le(db, "KLE190626", "VO THI E", gia_ban=6000000, o_gop=3000000)
    d = DVL.bang(db, 2026, 6)["dong"][0]
    assert d["nguon_chi"] == "o_gop"
    assert d["tong_chi"] == 3000000 and d["phi_lsq"] is None
    s = DVL.soat(db, 2026, 6)
    assert any("ô GỘP" in c["vi_sao"] for c in s["canh_bao"])
    assert s["duoc_chot_thang"] is True       # cảnh báo, không chặn


def test_d5_lo_ma_khong_giai_thich_thi_CANH_BAO(db):
    _dich_vu_le(db, "KLE200626", "HOANG VAN F", gia_ban=3000000,
                chi=[("vs_phi_lsq", 4000000)])
    s = DVL.soat(db, 2026, 6)
    assert any(x.get("lai") == -1000000 for x in s["canh_bao"])
    assert s["duoc_chot_thang"] is True


def test_d5_lo_co_giai_thich_thi_thoi_keu(db):
    _dich_vu_le(db, "KLE210626", "HOANG VAN G", gia_ban=3000000,
                chi=[("vs_phi_lsq", 4000000)], ghi_chu="Lãnh sự tăng phí sau khi đã báo giá")
    s = DVL.soat(db, 2026, 6)
    assert not [x for x in s["canh_bao"] if x.get("lai")]


def test_d5_dich_vu_da_HUY_khong_vao_tong_va_khong_bi_chan(db):
    _dich_vu_le(db, "KLE220626", "NGUYEN VAN H", gia_ban=5000000, huy=True)
    s = DVL.soat(db, 2026, 6)
    assert s["so_dong_huy"] == 1
    assert s["tong_thu"] is None
    assert s["duoc_chot_thang"] is True


def test_d5_chi_lay_dung_thang_duoc_hoi(db):
    _dich_vu_le(db, "KLE150626", "THANG SAU", gia_ban=1000000,
                chi=[("vs_phi_lsq", 1)], thang=6)
    _dich_vu_le(db, "KLE150726", "THANG BAY", gia_ban=2000000,
                chi=[("vs_phi_lsq", 1)], thang=7)
    assert DVL.bang(db, 2026, 6)["tong_thu"] == 1000000
    assert DVL.bang(db, 2026, 7)["tong_thu"] == 2000000


def test_d5_bon_cot_chi_deu_tro_vao_ma_khoan_muc_CO_THAT():
    """Bốn cột của tệp Excel phải ánh xạ vào danh mục khoản mục đang có, không phải mã bịa ra."""
    from app.services.khoan_muc_chi import KHOAN_MUC
    for khoa, nhan, mas in DVL.COT_CHI:
        for m in mas:
            assert m in KHOAN_MUC, f"cột «{nhan}» trỏ vào mã khoản mục không có thật: {m}"


def test_d5_khoan_ngoai_bon_cot_KHONG_bien_mat():
    """Gom vào «Phí khác» chứ không bỏ – một con số biến mất là cách lãi phồng lên lặng lẽ."""
    import inspect
    ma = inspect.getsource(DVL.bang)
    assert "MA_DA_XEP" in ma and "phi_khac" in ma


def test_d5_doc_tu_dung_hai_nguon_va_uu_tien_giong_nonpackage():
    """Giá vốn ưu tiên DÒNG CHI PHÍ, chỉ khi chưa có dòng nào mới dùng ô gộp của booking.

    Cùng thứ tự ưu tiên với `nonpackage.close_month` – hai chỗ đọc khác thứ tự là hai con số.
    """
    import inspect
    from app.services import nonpackage as NP
    ma_dvl = inspect.getsource(DVL.bang)
    ma_np = inspect.getsource(NP.close_month)
    assert "cost_amount" in ma_dvl and "TourCostLine" in inspect.getsource(DVL)
    assert "cost_amount" in ma_np


def test_d5_KHONG_co_cua_ghi_nao():
    """Thêm một cửa ghi thứ hai cho cùng một con số là mở đường cho hai con số.

    Đọc CÂY CÚ PHÁP chứ không tìm chuỗi: chính chú thích đầu tệp có nhắc tên các lệnh ghi, và một
    phép thử tìm chuỗi sẽ đỏ vì lời giải thích thay vì vì đoạn mã.
    """
    import ast
    import inspect
    cay = ast.parse(inspect.getsource(DVL))
    goi = {ast.unparse(n.func) for n in ast.walk(cay) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)}
    xau = {g for g in goi if g.split(".")[-1] in ("add", "commit", "delete", "add_all", "merge",
                                                  "flush", "execute")}
    assert not xau, f"tệp tổng hợp Đ-5 không được ghi gì: tìm thấy {sorted(xau)}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA và MẠCH NÂNG CẤP
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_cac_duong_moi_deu_co_mat():
    from app.api.v1 import quyet_toan_lop3 as R
    duong = {getattr(r, "path", "") for r in R.router.routes}
    for p in ("/ben-ban", "/ben-ban/dong", "/ben-ban/danh-muc", "/ben-ban/hoan-tip/xem-truoc",
              "/lanh-su", "/lanh-su/{did}/dong", "/dich-vu-le/{nam}/{thang}"):
        assert any(x.endswith(p) for x in duong), f"thiếu đường {p}"


def test_cua_ben_ban_chan_ngay_khi_hoan_tip_ghi_duong():
    import inspect
    from app.api.v1 import quyet_toan_lop3 as R
    ma = inspect.getsource(R.them_ben_ban_dong)
    assert "hoan_tip" in ma and "ÂM" in ma
    assert "thanh_tien" not in {k for k in R.BenBanDongVao.model_fields}


def test_mach_nang_cap_van_chi_co_MOT_dau_sau_dot_3():
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
    assert datetime  # noqa: B015 – giữ import cho các phép thử dựng dữ liệu ở trên
