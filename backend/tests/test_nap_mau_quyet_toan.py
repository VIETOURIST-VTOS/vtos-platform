"""Cửa nạp mẫu quyết toán tour – nhân viên Điều hành tự tải tệp đã điền lên.

Phép thử này dựng một tệp Excel ĐÚNG BỐ CỤC MẪU ngay trong bộ nhớ rồi cho bộ đọc ăn, nên nó canh được
cả ba tầng cùng lúc: đọc đúng cột, kiểm đúng lỗi, và ghi đúng bảng.

BA ĐIỀU QUAN TRỌNG NHẤT MÀ NÓ CANH

1. MÁY CỘNG LẠI, KHÔNG ĐỌC Ô TỔNG CỦA TỆP. Phép thử cố ý ghi một ô tổng SAI vào tệp rồi đòi hệ thống
   ra con số ĐÚNG. Trên tệp mẫu thật của Điều hành, ô tổng một nhóm chi ghi 3.990.000 trong khi năm
   dòng của chính nhóm ấy cộng lại được 4.200.000 – thiếu 210.000 đ mà mọi tầng vẫn cân.

2. DÒ CỘT THEO NHÃN. Mẫu nước ngoài có bốn cột ngoại tệ mà mẫu trong nước không có, nên cùng một
   nhãn nằm ở hai chữ cái cột khác nhau. Phép thử chạy cả hai bố cục.

3. NẠP LẠI LÀ THAY, KHÔNG CỘNG THÊM. Nạp cùng một tệp hai lần mà cộng dồn thì chuyến có hai lần giá
   vốn, và bảng vẫn cân nên không ai thấy.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_nap_mau.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_nap_mau.db"):
    os.remove("test_nap_mau.db")

from datetime import date                                           # noqa: E402
from io import BytesIO                                              # noqa: E402
import openpyxl                                                     # noqa: E402
from sqlalchemy import select                                        # noqa: E402
import pytest                                                       # noqa: E402
from app.db.session import SessionLocal, Base, engine                # noqa: E402
import app.models                                                    # noqa: E402,F401
from app.models.core import Booking, Tour, User                      # noqa: E402
from app.models.lop3_tour import (BookingKhach, TourDoanhThuDong,    # noqa: E402
                                  TourHdvChi, TourPhuongTien)
from app.models.vietrip import TourCostLine                          # noqa: E402
from app.services import nap_mau_quyet_toan as N                     # noqa: E402

_c = N._chu      # chuẩn hoá nhãn cột giống hệt bộ đọc – không tự viết lại cách cắt khoảng trắng

Base.metadata.create_all(engine)

MA = "TN-NAP-001"


def _tep(nn: bool, ma_tour: str = MA, tong_chi_sai: float = 999_999_999) -> bytes:
    """Dựng một tệp đúng bố cục mẫu. nn=True là mẫu nước ngoài (có cột ngoại tệ và sheet CHI THEO KHÁCH)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    ti = wb.create_sheet("THÔNG TIN")
    for r, (a, b) in enumerate([
        ("Mã tour", ma_tour), ("Tên tour", "CHUYẾN THỬ"), ("Số khách", 3),
        ("Hình thức", "nuoc_ngoai" if nn else "trong_nuoc"),
        ("Ngày khởi hành", date(2026, 7, 10)), ("Ngày kết thúc", date(2026, 7, 12)),
        ("Điều hành", "MÃ HUỆ LINH"), ("Sale phụ trách", "HIỆP"),
        ("Hướng dẫn viên / TL", "MINH CHIẾN"),
    ], start=3):
        ti.cell(r, 1, a); ti.cell(r, 2, b)

    kh = wb.create_sheet("KHÁCH")
    cot_kh = ["STT", "Nhóm khách", "Họ và tên", "Giới tính", "Ngày sinh", "Điện thoại", "Email",
              "Sale", "Giá bán", "Note", "Số hộ chiếu" if nn else "CCCD", "Mã đặt chỗ"]
    for j, n in enumerate(cot_kh, start=1):
        kh.cell(2, j, n)
    gia_nl = 53_900_000 if nn else 1_790_000
    for i, (nh, ten, dob, gia) in enumerate([
        ("tra_tien", "NGUOI LON A", date(1990, 1, 1), gia_nl),
        ("tra_tien", "TRE EM B", date(2018, 1, 1), round(gia_nl * (0.9 if nn else 0.8))),
        ("dai_ly", "KHACH DAI LY C", date(1985, 5, 5), None),
    ]):
        r = 3 + i
        for j, v in enumerate([i + 1, nh, ten, "M", dob, "0901234567", "", "HIỆP", gia,
                               "", "X123", "PNR1"], start=1):
            kh.cell(r, j, v)
    kh.cell(63, 1, "CỘNG")          # dòng CỘNG – bộ đọc phải dừng ở đây

    th = wb.create_sheet("THU")
    for j, n in enumerate(["Loại", "Nội dung", "Khách (STT)", "Đối tượng", "Đơn giá trước thuế",
                           "Số lượng", "Thành tiền trước thuế", "Thuế suất", "Tiền thuế",
                           "TỔNG THU", "Chứng từ (bắt buộc nếu ÂM)"], start=1):
        th.cell(2, j, n)
    for i, (loai, nd, stt, dg, ct) in enumerate([
        ("hop_dong", "GIÁ TOUR NL A", 1, gia_nl, ""),
        ("hop_dong", "GIÁ TOUR TE B", 2, round(gia_nl * (0.9 if nn else 0.8)), ""),
        ("thanh_ly", "HOÀN VÉ THAM QUAN", 1, -500_000, "BBTL 07/2026"),
    ]):
        r = 3 + i
        for j, v in enumerate([loai, nd, stt, "", dg, 1, 0, None, 0, 0, ct], start=1):
            th.cell(r, j, v)

    ch = wb.create_sheet("CHI")
    cot_ch = (["Ngày", "Mã khoản mục", "Nhóm", "Nội dung", "Đối tác", "MST đối tác", "Đối tượng",
               "Quy tắc phân bổ"]
              + (["Tiền tệ", "Số tiền gốc", "Tỷ giá", "Ngày tỷ giá"] if nn else [])
              + ["DỰ CHI (VND)", "THỰC CHI (VND)", "Chênh dự/thực", "Thuế suất", "Tiền thuế",
                 "Phần KHÔNG hoá đơn", "Số hoá đơn"])
    for j, n in enumerate(cot_ch, start=1):
        ch.cell(2, j, n)
    c = {n: j for j, n in enumerate(cot_ch, start=1)}
    dong_chi = [("lt_khach_san", "KS Sky Beach", 1_120_000),
                ("au_an_trua", "Ăn trưa Đồng Tiến", 805_000),
                ("au_an_trua", "Ăn trưa Marina", 1_260_000),
                ("bh_du_lich", "Bảo hiểm", 210_000)]
    for i, (ma, nd, tien) in enumerate(dong_chi):
        r = 3 + i
        ch.cell(r, c["Mã khoản mục"], ma)
        ch.cell(r, c["Nội dung"], nd)
        ch.cell(r, c["Quy tắc phân bổ"], "theo_doi_tuong")
        ch.cell(r, c["DỰ CHI (VND)"], tien)
        ch.cell(r, c["THỰC CHI (VND)"], tien)
        ch.cell(r, c["Thuế suất"], 0.08)
    if nn:      # một khoản ngoại tệ khai đủ tỷ giá và ngày tỷ giá
        r = 3 + len(dong_chi)
        ch.cell(r, c["Mã khoản mục"], "vc_xe_du_lich")
        ch.cell(r, c["Nội dung"], "Bus 50s")
        ch.cell(r, c["Quy tắc phân bổ"], "deu_khach_co_thu")
        ch.cell(r, c["Tiền tệ"], "EUR"); ch.cell(r, c["Số tiền gốc"], 100)
        ch.cell(r, c["Tỷ giá"], 30_500); ch.cell(r, c["Ngày tỷ giá"], date(2026, 7, 1))
    # Ô TỔNG CỐ Ý SAI – hệ thống phải bỏ qua nó và cộng lại từ dòng.
    ch.cell(93, c["Nội dung"], "CỘNG")
    ch.cell(93, c["THỰC CHI (VND)"], tong_chi_sai)

    pt = wb.create_sheet("PHƯƠNG TIỆN")
    for j, n in enumerate(["Loại", "Chặng", "Ngày", "Số hiệu / biển số", "Mã đặt chỗ",
                           "Nhà cung cấp", "MST", "Xe nhà?", "Số chỗ", "Số khách dùng",
                           "Thành tiền (VND)", "Dòng CHI tương ứng", "Ghi chú"], start=1):
        pt.cell(2, j, n)
    for j, v in enumerate(["may_bay" if nn else "o_to", "SGN-CDG" if nn else "HCM-NT",
                           date(2026, 7, 10), "9G1951", "PNR1", "VIETRIP", "", "x", 45, 3,
                           5_000_000, 1, ""], start=1):
        pt.cell(3, j, v)

    hv = wb.create_sheet("HDV")
    for j, n in enumerate(["Nội dung", "Tiền tệ", "Số gốc", "Tỷ giá", "Thực chi (VND)",
                           "Theo chiết tính", "VƯỢT", "Chứng từ", "Thu hộ khách?", "Duyệt",
                           "Lý do duyệt / từ chối"], start=1):
        hv.cell(3, j, n)
    for j, v in enumerate(["CTP HDV", "", 1_200_000, "", 1_200_000, 1_000_000, 0,
                           "phieu_thu", "", "da_duyet", "TP đã duyệt"], start=1):
        hv.cell(4, j, v)

    if nn:
        ck = wb.create_sheet("CHI THEO KHÁCH")
        for j, n in enumerate(["Khách (STT)", "Họ và tên", "Loại chi phí", "Nội dung",
                               "Nhà cung cấp", "MST", "Tiền tệ", "Số tiền gốc", "Tỷ giá",
                               "Thành tiền (VND)", "Số hoá đơn"], start=1):
            ck.cell(3, j, n)
        for j, v in enumerate([1, "NGUOI LON A", "ve_may_bay", "Vé SGN-CDG", "TURKISH", "",
                               "", None, None, 22_425_781, "HD001"], start=1):
            ck.cell(4, j, v)

    b = BytesIO(); wb.save(b)
    return b.getvalue()


@pytest.fixture(scope="module", autouse=True)
def chuyen():
    db = SessionLocal()
    u = User(username="dh_nap", full_name="ĐH", role="nv_dh", password_hash="x")
    db.add(u); db.flush()
    for ma, ht in ((MA, "trong_nuoc"), ("NN-NAP-001", "nuoc_ngoai")):
        t = Tour(code=ma, name="CHUYẾN THỬ", tour_type="package", hinh_thuc=ht,
                 operator_id=u.id, start_date=date(2026, 7, 10), end_date=date(2026, 7, 12),
                 planned_pax=3)
        db.add(t); db.flush()
        db.add(Booking(code=f"BK-{ma}", tour_id=t.id, request_id=0, sales_id=u.id,
                       customer_name="ĐOÀN THỬ", customer_phone="0900000000", pax=3,
                       source="test", created_by="test"))
    db.commit(); db.close()


# ------------------------------------------------------------------ đọc

@pytest.mark.parametrize("nn", [False, True])
def test_doc_dung_ca_hai_bo_cuc(nn):
    """Hai mẫu khác số cột, nên cùng một nhãn nằm ở hai chữ cái cột khác nhau."""
    d = N.doc_tep(_tep(nn), "thử.xlsx")
    assert d["ma_tour"] == MA
    assert d["hinh_thuc"] == ("nuoc_ngoai" if nn else "trong_nuoc")
    assert len(d["khach"]) == 3           # dừng đúng ở dòng CỘNG, không đọc lố
    assert len(d["thu"]) == 3
    assert len(d["chi"]) == (5 if nn else 4)
    assert len(d["phuong_tien"]) == 1 and len(d["hdv_chi"]) == 1
    assert len(d["chi_khach"]) == (1 if nn else 0)


def test_khach_va_dong_thu_treo_dung_PHIEU_DAT_cua_minh():
    """Mỗi dòng khách vào ĐÚNG phiếu đặt của nó – không dồn hết về phiếu đầu tiên.

    ĐÂY LÀ LỖI ĐÃ ĐO ĐƯỢC TRÊN TỆP THẬT

    Bản đầu của bộ nạp lấy `Booking...order_by(Booking.id)).first()` rồi gán cho MỌI dòng khách và
    MỌI dòng thu. Trên tệp "QT TOUR NHA TRANG 10.07.26.xlsx": 42 khách thuộc 9 phiếu đặt của 10 sale
    khác nhau, tất cả bị dồn về một phiếu. Doanh thu theo sale sai, số "đã đóng" theo phiếu sai, hoa
    hồng sai – mà TỔNG của chuyến vẫn đúng, nên không nhìn bằng mắt mà thấy được.

    Phép thử dựng đúng hình ấy: hai phiếu đặt, ba khách chia về hai phiếu, rồi đòi từng khách nằm
    đúng chỗ.
    """
    ma = "TN-NAP-2BK"
    db = SessionLocal()
    u = db.scalars(select(User)).first()
    t = Tour(code=ma, name="HAI PHIẾU", tour_type="package", hinh_thuc="trong_nuoc",
             operator_id=u.id, start_date=date(2026, 7, 10), end_date=date(2026, 7, 12),
             planned_pax=3)
    db.add(t); db.flush()
    b1 = Booking(code="BK-AAA", tour_id=t.id, request_id=0, sales_id=u.id,
                 customer_name="KHÁCH A", customer_phone="0900000001", pax=2,
                 source="test", created_by="test")
    b2 = Booking(code="BK-BBB", tour_id=t.id, request_id=0, sales_id=u.id,
                 customer_name="KHÁCH B", customer_phone="0900000002", pax=1,
                 source="test", created_by="test")
    db.add_all([b1, b2]); db.commit()
    id1, id2 = b1.id, b2.id

    wb = openpyxl.load_workbook(BytesIO(_tep(False, ma_tour=ma)))
    kh = wb["KHÁCH"]
    c = {_c(kh.cell(2, j).value): j for j in range(1, kh.max_column + 1) if kh.cell(2, j).value}
    if "Mã booking" not in c:
        c["Mã booking"] = kh.max_column + 1
        kh.cell(2, c["Mã booking"], "Mã booking")
    for r, ma_bk in ((3, "BK-AAA"), (4, "BK-AAA"), (5, "BK-BBB")):
        kh.cell(r, c["Mã booking"], ma_bk)
    th = wb["THU"]
    ct = {_c(th.cell(2, j).value): j for j in range(1, th.max_column + 1) if th.cell(2, j).value}
    if "Mã booking" not in ct:
        ct["Mã booking"] = th.max_column + 1
        th.cell(2, ct["Mã booking"], "Mã booking")
    for r, ma_bk in ((3, "BK-AAA"), (4, "BK-BBB"), (5, "BK-AAA")):
        th.cell(r, ct["Mã booking"], ma_bk)
    b = BytesIO(); wb.save(b)

    d = N.doc_tep(b.getvalue(), "hai_bk.xlsx")
    k = N.kiem_mot(db, d)
    assert k["nang"] == [], k["nang"]
    N.nap_lo(db, [d], "thử", "hai_bk.xlsx")
    db.commit()

    ds = db.query(BookingKhach).filter(BookingKhach.tour_id == t.id).order_by(BookingKhach.stt).all()
    assert [x.booking_id for x in ds] == [id1, id1, id2], \
        "dòng khách bị dồn về một phiếu đặt thay vì treo đúng phiếu của mình"
    dt = db.query(TourDoanhThuDong).filter(TourDoanhThuDong.tour_id == t.id) \
           .order_by(TourDoanhThuDong.id).all()
    assert [x.booking_id for x in dt] == [id1, id2, id1]

    # Mã booking lạ thì CHẶN, không im lặng gán bừa.
    kh.cell(3, c["Mã booking"], "BK-KHONG-CO")
    b2_ = BytesIO(); wb.save(b2_)
    k2 = N.kiem_mot(db, N.doc_tep(b2_.getvalue(), "la.xlsx"))
    assert any("BK-KHONG-CO" in x for x in k2["nang"]), k2
    db.close()


def test_mot_phieu_dat_thi_khong_bat_go_ma_booking():
    """Chuyến chỉ có MỘT phiếu đặt thì để trống 'Mã booking' là bình thường – không có chỗ nhầm.

    Bắt gõ ở cả trường hợp này là làm phiền chứ không phải bảo vệ, và một phép kiểm lúc nào cũng đỏ
    thì người ta học cách bỏ qua nó.
    """
    db = SessionLocal()
    d = N.doc_tep(_tep(False), "mot_bk.xlsx")     # MA gốc: fixture tạo đúng một phiếu đặt
    k = N.kiem_mot(db, d)
    assert k["nang"] == [], k["nang"]
    assert any("chỉ có một phiếu" in x for x in k["nhe"]), k["nhe"]
    db.close()


def test_dung_o_vach_CONG_du_chu_CONG_khong_nam_o_cot_bat_buoc():
    """Vạch kết thúc bảng phải được nhận ra dù chữ "CỘNG" nằm ở cột nào.

    ĐÂY LÀ MỘT LỖI ĐÃ XẢY RA THẬT, ĐO ĐƯỢC

    Bản đầu của bộ đọc chỉ nhìn chữ "CỘNG" ở đúng CỘT BẮT BUỘC. Trên mẫu do chính VTOS phát ra, chữ
    ấy nằm ở cột 1 của sheet KHÁCH trong khi cột bắt buộc là "Họ và tên" (cột 3) – nên vạch kết thúc
    không bao giờ được nhận ra, và bộ đọc đi thẳng xuống dòng VÍ DỤ mà mẫu để bên dưới. Kết quả: tải
    mẫu trống lên khi CHƯA ĐIỀN GÌ, hệ thống ghi một hành khách tên NGUYEN VAN A, giá bán 1.790.000 đ.

    Không ai gõ sai gì cả. Cái tệp và cái bộ đọc chỉ đơn giản là không khớp – và không có chỗ nào đỏ.
    """
    import openpyxl as O
    wb = O.load_workbook(BytesIO(_tep(False)))
    kh = wb["KHÁCH"]
    assert kh.cell(63, 1).value == "CỘNG"       # chữ CỘNG ở cột 1, cột bắt buộc là cột 3
    kh.cell(64, 1, "VÍ DỤ – XOÁ DÒNG NÀY TRƯỚC KHI DÙNG")
    for j, v in enumerate([1, "tra_tien", "NGUYEN VAN A", "M", date(1953, 4, 21), "0901234567",
                           "a@vidu.com", "PHƯƠNG NHI", 1_790_000, "", "079x", "PNRX"], start=1):
        kh.cell(65, j, v)
    b = BytesIO(); wb.save(b)

    d = N.doc_tep(b.getvalue(), "co_dong_ma.xlsx")
    assert len(d["khach"]) == 3, "bộ đọc đi lố qua dòng CỘNG và nuốt cả dòng ví dụ"
    assert all("NGUYEN VAN A" != (x.get("Họ và tên") or "") for x in d["khach"])
    # Và tổng thu không bị cộng thêm một vé ma.
    assert N._tong_thu(d) == 1_790_000 + round(1_790_000 * 0.8) - 500_000


def test_khong_tin_o_tong_cua_tep_ma_cong_lai_tu_dong():
    """Tệp ghi ô tổng 999.999.999. Hệ thống phải ra con số thật, cộng từ bốn dòng."""
    d = N.doc_tep(_tep(False, tong_chi_sai=999_999_999), "thử.xlsx")
    assert N._tong_chi(d) == 1_120_000 + 805_000 + 1_260_000 + 210_000
    # Và tổng thu cũng cộng lại, kể cả dòng âm của thanh lý.
    assert N._tong_thu(d) == 1_790_000 + round(1_790_000 * 0.8) - 500_000


def test_tep_khong_phai_mau_thi_tu_choi_ngay():
    wb = openpyxl.Workbook(); wb.active.title = "Sheet1"
    b = BytesIO(); wb.save(b)
    with pytest.raises(ValueError, match="không phải mẫu quyết toán"):
        N.doc_tep(b.getvalue(), "linh tinh.xlsx")


# ------------------------------------------------------------------ kiểm

def test_ma_tour_khong_co_trong_he_thong_thi_chan_nap():
    db = SessionLocal()
    d = N.doc_tep(_tep(False, ma_tour="KHONG-CO-THAT"), "x.xlsx")
    k = N.kiem_mot(db, d)
    assert any("Không có chuyến mã" in m for m in k["nang"])
    db.close()


def test_hinh_thuc_lech_voi_chuyen_trong_he_thong_thi_chan():
    """Nạp mẫu nước ngoài vào một chuyến trong nước là sai tỷ lệ giá em bé từ 30% xuống 10%."""
    db = SessionLocal()
    d = N.doc_tep(_tep(True, ma_tour=MA), "x.xlsx")     # tệp nước ngoài, chuyến trong nước
    k = N.kiem_mot(db, d)
    assert any("hai hình thức dùng hai tỷ lệ giá khác nhau" in m for m in k["nang"])
    db.close()


def test_dong_thu_am_khong_chung_tu_thi_chan():
    db = SessionLocal()
    import openpyxl as X
    wb = X.load_workbook(BytesIO(_tep(False)))
    # openpyxl: cell(r, c, None) KHÔNG xoá ô – phải gán .value. Bản đầu của phép thử này viết
    # cell(5, 11, None) và nó im lặng không làm gì, nên phép thử xanh giả một lần.
    wb["THU"].cell(5, 11).value = None                   # xoá ô chứng từ của dòng âm
    b = BytesIO(); wb.save(b)
    k = N.kiem_mot(db, N.doc_tep(b.getvalue()))
    assert any("dòng thu ÂM không ghi chứng từ" in m for m in k["nang"])
    db.close()


def test_ma_khoan_muc_la_thi_chan():
    db = SessionLocal()
    import openpyxl as X
    wb = X.load_workbook(BytesIO(_tep(False)))
    wb["CHI"].cell(3, 2, "ma_bia_ra")
    b = BytesIO(); wb.save(b)
    k = N.kiem_mot(db, N.doc_tep(b.getvalue()))
    assert any("Mã khoản mục không có trong danh mục" in m for m in k["nang"])
    db.close()


def test_to_khai_sach_thi_khong_con_phat_hien_nang():
    db = SessionLocal()
    k = N.kiem_mot(db, N.doc_tep(_tep(False)))
    assert k["nang"] == [], k["nang"]
    db.close()


# ------------------------------------------------------------------ nạp

def test_nap_ghi_dung_sau_bang():
    db = SessionLocal()
    kq = N.nap_lo(db, N.doc_tep_lo(_tep(False), "thử.xlsx"), "dh_nap", "thử.xlsx")
    assert kq["da_nap"] == 1, kq.get("loi")
    tid = kq["ket_qua"][0]["tour_id"]

    assert db.query(BookingKhach).filter(BookingKhach.tour_id == tid).count() == 3
    assert db.query(TourDoanhThuDong).filter(TourDoanhThuDong.tour_id == tid).count() == 3
    assert db.query(TourCostLine).filter(TourCostLine.tour_id == tid).count() == 4
    assert db.query(TourPhuongTien).filter(TourPhuongTien.tour_id == tid).count() == 1
    assert db.query(TourHdvChi).filter(TourHdvChi.tour_id == tid).count() == 1

    # Mặc định của khoản mục được điền hộ – người nhập không gõ nhóm.
    ks = db.query(TourCostLine).filter(TourCostLine.tour_id == tid,
                                       TourCostLine.ma_khoan_muc == "lt_khach_san").one()
    assert ks.nhom and ks.nhom.startswith("B.")
    # HDV: vượt chiết tính do MÁY tính, không đọc ô VƯỢT của tệp (tệp ghi 0).
    h = db.query(TourHdvChi).filter(TourHdvChi.tour_id == tid).one()
    assert h.vuot == 200_000
    db.close()


def test_nap_lai_la_THAY_khong_cong_them():
    """Nạp cùng một chuyến lần thứ hai mà cộng dồn thì chuyến có hai lần giá vốn."""
    db = SessionLocal()
    for _ in range(2):
        N.nap_lo(db, N.doc_tep_lo(_tep(False), "thử.xlsx"), "dh_nap", "thử.xlsx")
    t = db.query(Tour).filter(Tour.code == MA).one()
    assert db.query(TourCostLine).filter(TourCostLine.tour_id == t.id).count() == 4
    assert db.query(BookingKhach).filter(BookingKhach.tour_id == t.id).count() == 3
    db.close()


def test_nap_chan_khi_con_phat_hien_nang():
    db = SessionLocal()
    kq = N.nap_lo(db, N.doc_tep_lo(_tep(False, ma_tour="KHONG-CO-THAT")), "dh_nap")
    assert kq["da_nap"] == 0
    assert "KHÔNG nạp gì cả" in kq["message"]
    db.close()


def test_mau_nuoc_ngoai_nap_duoc_ca_chi_theo_khach():
    db = SessionLocal()
    from app.models.lop3_tour import KhachChiPhi
    kq = N.nap_lo(db, N.doc_tep_lo(_tep(True, ma_tour="NN-NAP-001"), "nn.xlsx"), "dh_nap", "nn.xlsx")
    assert kq["da_nap"] == 1, kq.get("loi")
    tid = kq["ket_qua"][0]["tour_id"]
    assert db.query(KhachChiPhi).filter(KhachChiPhi.tour_id == tid).count() == 1
    # Khoản ngoại tệ: MÁY quy đổi 100 EUR × 30.500, không đọc ô VND của tệp.
    bus = db.query(TourCostLine).filter(TourCostLine.tour_id == tid,
                                        TourCostLine.ma_khoan_muc == "vc_xe_du_lich").one()
    assert bus.actual == 3_050_000
    db.close()

def test_o_cong_thuc_RONG_thi_van_tinh_lai_duoc_khoan_HDV():
    """Ô "Thực chi" của sheet HDV là CÔNG THỨC. Tệp nào đọc ra rỗng thì máy phải nhân lại.

    Tệp gửi lên có thể đã đi qua một phần mềm không tính lại công thức – Google Sheets xuất ra,
    LibreOffice chế độ nhanh, hoặc chính openpyxl. Bản đầu chỉ lùi về "số gốc × tỷ giá", nên với
    tour TRONG NƯỚC (không có ngoại tệ) cả khoản HDV biến mất: tiền ứng và phần vượt đều ra rỗng,
    không dòng nào báo lỗi.

    Đây đúng là điều tệp này tự nhận ở đầu trang: TIN DÒNG, KHÔNG TIN TỔNG.
    """
    import openpyxl as O
    wb = O.load_workbook(BytesIO(_tep(False)))
    hv = wb["HDV"]
    c = {_c(hv.cell(3, j).value): j for j in range(1, hv.max_column + 1) if hv.cell(3, j).value}
    for ten in ("Đơn giá", "Số lượng", "Tiền ứng"):
        if ten not in c:
            c[ten] = hv.max_column + 1
            hv.cell(3, c[ten], ten)
    hv.cell(4, c["Thực chi (VND)"]).value = None      # ô công thức đọc ra RỖNG
    hv.cell(4, c["Đơn giá"], 30_000)
    hv.cell(4, c["Số lượng"], 44)
    hv.cell(4, c["Tiền ứng"], 1_000_000)
    b = BytesIO(); wb.save(b)

    db = SessionLocal()
    d = N.doc_tep(b.getvalue(), "rong.xlsx")
    k = N.kiem_mot(db, d)
    assert k["nang"] == [], k["nang"]
    N.nap_lo(db, [d], "thử", "rong.xlsx"); db.commit()
    x = db.query(TourHdvChi).filter(TourHdvChi.tour_id == k["tour_id"]).first()
    assert x.thanh_tien == 1_320_000, "không nhân lại được 30.000 × 44 khi ô công thức rỗng"
    assert x.tien_ung == 1_000_000
    assert x.con_lai == -320_000, "ứng 1.000.000 − chi 1.320.000 = −320.000 (công ty nợ HDV)"
    db.close()


def test_khung_nap_doc_duoc_ket_qua_cua_bo_nap_nay():
    """kiem_lo phải trả đúng BA KHOÁ mà khung nạp đọc: so_dong, da_co, dong_loi.

    intake.nap() ghi nhật ký lô bằng chính ba khoá ấy. Bản đầu đặt tên "tong_dong" cho cùng một
    thứ, nên cửa TẢI TỆP LÊN nổ KeyError ngay trước lúc ghi nhật ký – tức là cửa ấy chưa bao giờ
    chạy thông, trong khi phép thử của riêng bộ nạp vẫn xanh vì nó gọi thẳng nap_lo() chứ không đi
    qua khung.
    """
    db = SessionLocal()
    k = N.kiem_lo(db, [N.doc_tep(_tep(False), "a.xlsx")])
    for khoa in ("so_dong", "da_co", "dong_loi"):
        assert khoa in k, f"khung nạp đọc kq['{khoa}'] – bộ nạp không trả khoá này"
    assert k["so_dong"] == 1 and k["da_co"] == 0
    db.close()
