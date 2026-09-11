"""Lớp 3: giá theo tuổi và phân bổ chi phí về từng khách.

Phép thử này KHÔNG dùng dữ liệu bịa. Nó dựng lại đúng chuyến NT001.03100726 (NHA TRANG, 10–12/07/2026)
từ tệp quyết toán thật của Phòng Điều hành, rồi đòi phần mềm ra đúng những con số mà tệp ấy đã ra:

    Bảo hiểm   210.000 ÷ 42 =  5.000   mỗi khách, KỂ CẢ hai cháu em bé
    Nước suối  630.000 ÷ 40 = 15.750   chỉ khách có thu
    Phí TL   1.500.000 ÷ 40 = 37.500   chỉ khách có thu
    Land    48.310.000       -> 1.343.030,30 người lớn / 570.000 trẻ em

Bốn mẫu số khác nhau trong cùng một bảng, và tệp gốc không viết mẫu số nào ở đâu cả – chúng nằm trong
công thức Excel. Đó chính là thứ phải đưa ra thành dữ liệu khai báo được.

Ba phép thử cuối canh những chỗ dễ hỏng nhất, và mỗi chỗ đều là tiền thật:

  * Thiếu ngày sinh thì KHÔNG được mặc định thành người lớn. Tính nhầm em bé thành người lớn là thu
    thừa tiền của khách, và bảng vẫn cân nên không ai phát hiện.
  * Tuổi tính tại NGÀY KHỞI HÀNH, không phải hôm nay. Cháu 11 tuổi rưỡi lúc đi tour sẽ 12 tuổi khi kế
    toán mở lại tờ quyết toán ba tháng sau.
  * Dòng chi chưa khai quy tắc phân bổ thì KHÔNG chia và KHÔNG đoán – nó phải hiện ra ở
    'chua_khai_quy_tac'.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lop3.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lop3.db"):
    os.remove("test_lop3.db")

from datetime import date                                           # noqa: E402
import pytest                                                       # noqa: E402
from app.db.session import SessionLocal, Base, engine                # noqa: E402
import app.models                                                    # noqa: E402,F401
from app.models.core import Tour, Booking, User                      # noqa: E402
from app.models.lop3_tour import BookingKhach                        # noqa: E402
from app.models.vietrip import TourCostLine                          # noqa: E402
from app.services import gia_khach as G                              # noqa: E402
from app.services import rules as R                                  # noqa: E402

Base.metadata.create_all(engine)

NGAY_DI = date(2026, 7, 10)

# Chiết tính thật của chuyến, sheet CTT. Cột cuối là quy tắc phân bổ suy ra từ chính cột chi của
# sheet QT – xem docstring đầu tệp.
CHIET_TINH = [
    # (nội dung,            nhóm,              tiền,      đối tượng,   quy tắc)
    ("XE 45c",              "A. LAND TOUR",  15000000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("LƯU TRÚ",             "A. LAND TOUR",  13500000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("LƯU TRÚ (phòng lẻ)",  "A. LAND TOUR",   1300000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("Ăn trưa ngày 1",      "A. LAND TOUR",   3795000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("Ăn trưa ngày 2",      "A. LAND TOUR",   5940000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("Ăn trưa ngày 3",      "A. LAND TOUR",   3795000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("Tham quan",           "A. LAND TOUR",    990000.0, "nguoi_lon",  "theo_doi_tuong"),
    ("LƯU TRÚ trẻ em",      "B. TRẺ EM",      1120000.0, "tre_em",     "theo_doi_tuong"),
    ("Ăn trưa ngày 1 TE",   "B. TRẺ EM",       805000.0, "tre_em",     "theo_doi_tuong"),
    ("Ăn trưa ngày 2 TE",   "B. TRẺ EM",      1260000.0, "tre_em",     "theo_doi_tuong"),
    ("Ăn trưa ngày 3 TE",   "B. TRẺ EM",       805000.0, "tre_em",     "theo_doi_tuong"),
    ("Tham quan TE",        "B. TRẺ EM",       210000.0, "tre_em",     "theo_doi_tuong"),
    ("Nước suối",           "C. CHI PHÍ KHÁC", 630000.0, "chung",      "deu_khach_co_thu"),
    ("Bảo hiểm",            "C. CHI PHÍ KHÁC", 210000.0, "chung",      "deu_moi_khach"),
    ("HDV",                 "C. CHI PHÍ KHÁC", 1200000.0, "chung",     "deu_khach_co_thu"),
    ("Ăn nội bộ",           "C. CHI PHÍ KHÁC",  300000.0, "chung",     "deu_khach_co_thu"),
]


def _dung_chuyen(db, ma="NT001.03100726"):
    """33 người lớn, 7 trẻ em, 2 em bé – đúng thành phần chuyến Nha Trang.

    Hai em bé thu 0 đồng vì chuyến ấy chạy dưới quy tắc cũ (dưới 2 tuổi miễn phí). Từ
    11/9/2026 bậc em bé là 30% giá người lớn, nên chính hai cháu ấy nay đọc ra là bán dưới
    chuẩn – đó là điều phép thử soat_gia bên dưới canh.
    """
    dh = db.query(User).filter(User.username == "dh_test").first()
    if not dh:
        dh = User(username="dh_test", full_name="Điều hành thử", role="nv_dh", password_hash="x")
        db.add(dh); db.flush()
    t = Tour(code=ma, name="NHA TRANG", tour_type="package", hinh_thuc="trong_nuoc",
             operator_id=dh.id,
             start_date=NGAY_DI, end_date=date(2026, 7, 12), planned_pax=42)
    db.add(t); db.flush()
    b = Booking(code=f"BK-{ma}", tour_id=t.id, request_id=0, sales_id=dh.id, customer_name="ĐOÀN NHA TRANG",
                customer_phone="0900000000", pax=42, source="test", created_by="test")
    db.add(b); db.flush()

    stt = 0
    for _ in range(33):
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"NGƯỜI LỚN {stt}", nhom_khach="tra_tien",
                            ngay_sinh=date(1990, 1, 1), gia_ban=1790000.0))
    for _ in range(7):
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"TRẺ EM {stt}", nhom_khach="tra_tien",
                            ngay_sinh=date(2018, 1, 1), gia_ban=1500000.0))
    for _ in range(2):
        stt += 1
        db.add(BookingKhach(booking_id=b.id, tour_id=t.id, stt=stt, ho_ten=f"EM BÉ {stt}", nhom_khach="tra_tien",
                            ngay_sinh=date(2025, 1, 1), gia_ban=0.0))
    db.flush()

    for i, (nd, nhom, tien, dt, qt) in enumerate(CHIET_TINH, start=1):
        db.add(TourCostLine(tour_id=t.id, line_no=i, description=nd, nhom=nhom,
                            actual=tien, doi_tuong=dt, quy_tac_phan_bo=qt, status="hd"))
    db.flush()

    for k in db.query(BookingKhach).filter(BookingKhach.tour_id == t.id):
        G.xac_dinh_khach(db, k, t.start_date, 1790000.0, t.hinh_thuc)
    db.commit()
    return t


@pytest.fixture(scope="module")
def tour():
    db = SessionLocal()
    t = _dung_chuyen(db)
    yield t.id
    db.close()


# ------------------------------------------------------------------ tuổi và loại khách

def test_xep_loai_theo_nguong_cua_chu_tich():
    db = SessionLocal()
    # Dưới 2 -> em bé; 2 đến dưới 12 -> trẻ em; từ 12 -> người lớn. Ranh giới phải kiểm đúng ngày.
    assert G.xep_loai(db, date(2025, 1, 1), NGAY_DI)[0] == "em_be"        # 1 tuổi
    assert G.xep_loai(db, date(2024, 7, 11), NGAY_DI)[0] == "em_be"       # còn 1 ngày nữa mới tròn 2
    assert G.xep_loai(db, date(2024, 7, 10), NGAY_DI)[0] == "tre_em"      # tròn 2 tuổi đúng hôm đi
    assert G.xep_loai(db, date(2014, 7, 11), NGAY_DI)[0] == "tre_em"      # còn 1 ngày nữa mới tròn 12
    assert G.xep_loai(db, date(2014, 7, 10), NGAY_DI)[0] == "nguoi_lon"   # tròn 12 đúng hôm đi
    db.close()


def test_thieu_ngay_sinh_thi_khong_doan_thanh_nguoi_lon():
    """Mặc định thành người lớn là thu thừa tiền của khách, và bảng vẫn cân nên không ai thấy."""
    db = SessionLocal()
    loai, tuoi = G.xep_loai(db, None, NGAY_DI)
    assert loai is None and tuoi is None
    assert G.gia_chuan(db, None, 1790000.0, NGAY_DI, "trong_nuoc") is None
    db.close()


def test_tuoi_tinh_tai_ngay_khoi_hanh_khong_phai_hom_nay():
    """Cháu 11 tuổi rưỡi lúc đi tour sẽ 12 tuổi khi kế toán mở lại tờ đã ký ba tháng sau."""
    sinh = date(2014, 12, 1)
    assert G.tuoi_tai(sinh, NGAY_DI) == 11                  # lúc đi tour
    assert G.tuoi_tai(sinh, date(2026, 12, 15)) == 12       # lúc kế toán mở lại
    db = SessionLocal()
    assert G.xep_loai(db, sinh, NGAY_DI)[0] == "tre_em"
    db.close()


def test_gia_tre_em_theo_ty_le_da_chot():
    """Tỷ lệ là THAM SỐ, không phải hằng số trong mã.

    Chủ tịch chốt 0,75 ngày 10/9/2026 rồi đổi thành 0,90 ngày 11/9/2026 sau khi đối chiếu ba mẫu
    quyết toán thật. Phép thử này đọc tham số chứ không gán cứng con số, nên lần đổi chính sách sau
    sẽ không làm nó đỏ oan – mà vẫn canh đúng phép nhân.
    """
    db = SessionLocal()
    # Người lớn KHÔNG phụ thuộc hình thức – giá đầy đủ ở cả hai.
    assert G.gia_chuan(db, "nguoi_lon", 1790000.0, NGAY_DI, "trong_nuoc") == 1790000.0
    assert G.gia_chuan(db, "nguoi_lon", 1790000.0, NGAY_DI, "nuoc_ngoai") == 1790000.0

    for ht in ("trong_nuoc", "nuoc_ngoai"):
        te = R.get_param(db, f"ty_le_tre_em_{ht}", NGAY_DI)
        eb = R.get_param(db, f"ty_le_em_be_{ht}", NGAY_DI)
        assert G.gia_chuan(db, "tre_em", 1790000.0, NGAY_DI, ht) == round(1790000.0 * te, 2)
        assert G.gia_chuan(db, "em_be", 1790000.0, NGAY_DI, ht) == round(1790000.0 * eb, 2)

    # Em bé trong nước RẺ HƠN em bé nước ngoài. Đây là quan hệ nghiệp vụ, không phải hai con số rời:
    # tour nước ngoài có vé quốc tế, visa và bảo hiểm mà trẻ nhỏ vẫn trả gần bằng người lớn.
    assert (G.gia_chuan(db, "em_be", 1790000.0, NGAY_DI, "trong_nuoc")
            < G.gia_chuan(db, "em_be", 1790000.0, NGAY_DI, "nuoc_ngoai"))

    # THIẾU hình thức thì KHÔNG đoán. Đoán nhầm nước ngoài thành trong nước là hạ giá em bé xuống
    # một phần ba mà không ai bấm nút nào.
    assert G.gia_chuan(db, "em_be", 1790000.0, NGAY_DI, None) is None
    assert G.gia_chuan(db, "tre_em", 1790000.0, NGAY_DI, "") is None
    db.close()


def test_chuyen_nha_trang_ban_tre_em_khac_quy_tac(tour):
    """Chuyến thật bán trẻ em 1.500.000 – khác giá chuẩn, và phần mềm phải nói ra.

    Chiều của chênh lệch phụ thuộc tỷ lệ đang có hiệu lực, và chính chỗ ấy cho thấy vì sao tỷ lệ
    phải là tham số:

        tỷ lệ 0,75 -> chuẩn 1.342.500 -> bán CAO hơn chuẩn  157.500 đ/cháu (+1.102.500 đ)
        tỷ lệ 0,90 -> chuẩn 1.611.000 -> bán THẤP hơn chuẩn 111.000 đ/cháu (  -777.000 đ)

    Nên phép thử canh QUAN HỆ, không canh con số: đúng 7 trẻ em bị nêu, không dính người lớn nào,
    và tổng chênh bằng đúng 7 lần chênh của một cháu.
    """
    db = SessionLocal()
    kq = G.soat_gia(db, tour)
    chuan_te = round(1790000.0 * R.get_param(db, "ty_le_tre_em_trong_nuoc", NGAY_DI), 2)
    chuan_eb = round(1790000.0 * R.get_param(db, "ty_le_em_be_trong_nuoc", NGAY_DI), 2)
    assert kq["so_khach"] == 42
    assert kq["so_thieu_ngay_sinh"] == 0

    # 33 người lớn bán đúng chuẩn nên không ai trong số họ bị nêu. Còn lại đúng 9 người: 7 trẻ em bán
    # 1.500.000 và 2 em bé thu 0 đồng.
    assert kq["so_lech_gia"] == 9
    assert all(x["loai_tuoi"] in ("tre_em", "em_be") for x in kq["lech"])
    assert sum(1 for x in kq["lech"] if x["loai_tuoi"] == "tre_em") == 7
    assert sum(1 for x in kq["lech"] if x["loai_tuoi"] == "em_be") == 2

    # Hai cháu em bé chỉ thành "dưới chuẩn" TỪ 11/9/2026, khi Chủ tịch đổi bậc em bé từ miễn phí sang
    # 30%. Chuyến này đã quyết toán xong nên con số của nó không đổi; phép thử chỉ đang chứng minh
    # rằng từ nay những chuyến thu 0 đồng cho em bé sẽ hiện ra.
    assert round(kq["tong_lech_gia"]) == round((1500000.0 - chuan_te) * 7 + (0.0 - chuan_eb) * 2)
    db.close()


# ------------------------------------------------------------------ phân bổ chi phí

def test_bon_mau_so_khac_nhau_dung_nhu_tep_dieu_hanh(tour):
    """Bốn cột chi trong sheet QT chia theo bốn mẫu số khác nhau. Phần mềm phải ra đúng cả bốn."""
    db = SessionLocal()
    pb = G.phan_bo(db, tour)
    assert pb["so_khach"] == 42

    nl = [d for d in pb["dong"] if d["loai_tuoi"] == "nguoi_lon"]
    te = [d for d in pb["dong"] if d["loai_tuoi"] == "tre_em"]
    eb = [d for d in pb["dong"] if d["loai_tuoi"] == "em_be"]
    assert (len(nl), len(te), len(eb)) == (33, 7, 2)

    def khoan(d, ten):
        return round(sum(x["so_tien"] for x in d["gom"] if x["noi_dung"] == ten), 2)

    # Bảo hiểm: chia đều MỌI khách, kể cả hai cháu miễn phí -> 210.000 ÷ 42 = 5.000
    assert khoan(nl[0], "Bảo hiểm") == 5000.0
    assert khoan(eb[0], "Bảo hiểm") == 5000.0

    # Nước suối: chỉ khách CÓ THU -> 630.000 ÷ 40 = 15.750. Hai cháu miễn phí không chịu.
    assert khoan(nl[0], "Nước suối") == 15750.0
    assert khoan(eb[0], "Nước suối") == 0.0

    # Phí TL của tệp = HDV 1.200.000 + ăn nội bộ 300.000, chia đều 40 khách có thu = 37.500
    assert khoan(nl[0], "HDV") + khoan(nl[0], "Ăn nội bộ") == 37500.0
    assert khoan(eb[0], "HDV") == 0.0

    # Hai cháu miễn phí chỉ chịu đúng bảo hiểm, và lỗ đúng 5.000 – y như tệp gốc.
    assert eb[0]["gia_von"] == 5000.0
    assert eb[0]["thu"] == 0.0
    assert eb[0]["loi_nhuan"] == -5000.0
    db.close()


def test_land_chia_theo_doi_tuong_ra_dung_hai_con_so_cua_tep(tour):
    """Cột LAND của tệp có ĐÚNG HAI giá trị: 1.343.030,30 cho người lớn và 570.000 cho trẻ em."""
    db = SessionLocal()
    pb = G.phan_bo(db, tour)
    nl = [d for d in pb["dong"] if d["loai_tuoi"] == "nguoi_lon"][0]
    te = [d for d in pb["dong"] if d["loai_tuoi"] == "tre_em"][0]

    def land(d):
        bo = {"Nước suối", "Bảo hiểm", "HDV", "Ăn nội bộ"}
        return round(sum(x["so_tien"] for x in d["gom"] if x["noi_dung"] not in bo), 2)

    # Người lớn: nhóm A cộng lại 44.320.000 ÷ 33 = 1.343.030,30 – KHỚP ĐÚNG con số trong tệp.
    assert abs(land(nl) - 1343030.30) < 1.0

    # Trẻ em: đây là chỗ phần mềm RA KHÁC TỆP, và ra ĐÚNG.
    #
    #   nhóm B cộng lại đúng   4.200.000 ÷ 7 = 600.000   <- phần mềm
    #   nhóm B tệp ghi tổng    3.990.000 ÷ 7 = 570.000   <- tệp, thiếu dòng Tham quan Tháp Bà
    #
    # Chênh 30.000 đ mỗi cháu, 7 cháu là đúng 210.000 đ – khoản bị bỏ sót ở phép cộng nhóm B. Phần
    # mềm cộng lại từ dòng nên không thừa hưởng cái tổng sai ấy. Đây chính là nguyên tắc "máy chủ
    # cộng, người không gõ tổng" đo được thành tiền.
    assert abs(land(te) - 600000.0) < 1.0
    assert abs(land(te) * 7 - 3990000.0) == 210000.0
    db.close()


def test_dong_chua_khai_quy_tac_thi_khong_chia_va_khong_doan():
    """Không khai quy tắc thì phải HIỆN RA, không được lặng lẽ chia đều."""
    db = SessionLocal()
    t = _dung_chuyen(db, ma="NT-CHUA-KHAI")
    db.add(TourCostLine(tour_id=t.id, line_no=99, description="Khoản chưa ai xếp quy tắc",
                        actual=9_000_000.0, status="hd"))
    db.commit()

    pb = G.phan_bo(db, t.id)
    assert pb["tong_chua_khai"] == 9_000_000.0
    assert pb["chua_khai_quy_tac"][0]["noi_dung"] == "Khoản chưa ai xếp quy tắc"
    # Và nó KHÔNG được lẫn vào giá vốn của bất kỳ khách nào.
    assert all("Khoản chưa ai xếp quy tắc" not in [g["noi_dung"] for g in d["gom"]]
               for d in pb["dong"])
    db.close()


def test_khach_thieu_ngay_sinh_thi_bao_len_o_soat_gia():
    db = SessionLocal()
    t = _dung_chuyen(db, ma="NT-THIEU-NS")
    k = db.query(BookingKhach).filter(BookingKhach.tour_id == t.id).first()
    k.ngay_sinh = None
    k.loai_tuoi = None
    k.gia_chuan = None
    db.commit()

    kq = G.soat_gia(db, t.id)
    assert kq["so_thieu_ngay_sinh"] == 1
    assert "chưa có ngày sinh" in kq["canh_bao_ngay_sinh"]
    db.close()
