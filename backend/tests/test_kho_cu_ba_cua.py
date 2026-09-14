# -*- coding: utf-8 -*-
"""BA CỬA của kho quyết toán cũ T1–T6/2026 – TẢI · SOÁT · GHI.

Trước hôm nay, bộ đọc kho cũ, bộ chống trùng và phần ghi đều đã có và đều có phép thử. Nhưng cả ba
CHỈ CHẠY ĐƯỢC BẰNG DÒNG LỆNH, đầu vào là một tệp `du_lieu_nap.json` mà ai đó phải tạo ra trước.
Nhân viên Điều hành không dùng được — tức là theo ranh giới 09/9/2026 thì đây là việc CÒN THIẾU.

Tệp này canh cái cửa vừa dựng. Tám điều, và mỗi điều là một cách hỏng đã nghĩ ra trước:

  C1  SOÁT không ghi một dòng nào — đây là điều kiện để Chủ tịch dám bấm xem
  C2  mặc định KHÔNG ghi gì: thiếu bản đối chiếu H1 thì mọi tệp đều "cần người xác nhận"
  C3  bấm rõ mới ghi, và ghi đúng ba bảng
  C4  nạp LẠI cùng tệp KHÔNG nhân đôi — xoá đúng phần của nguồn mình rồi ghi lại
  C5  KHÔNG đụng doanh thu/giá vốn mức chuyến, kể cả khi tệp có số
  C6  tệp không có mã tour bị CHẶN, và chặn cả khi người bấm bỏ qua cảnh báo
  C7  chuyến chưa có phiếu đặt: dòng khách không ghi được thì phải NÓI RA, không im lặng
  C8  ba bảng đã có cửa — bộ kiểm "mọi bảng phải có cửa nhập" phải thấy
"""
import os
import sys
from datetime import date
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./test_khocu.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_khocu.db", "test_khocu.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                          # noqa: E402
from fastapi.testclient import TestClient              # noqa: E402
from sqlalchemy import func, select                    # noqa: E402

from app.db.session import SessionLocal                # noqa: E402
from app.main import app                               # noqa: E402
from app.models.core import Booking, Tour              # noqa: E402
from app.models.lop3_tour import BookingKhach, TourHdvChi   # noqa: E402
from app.models.vietrip import TourCostLine            # noqa: E402
from app.services import intake as I                   # noqa: E402
from app.services import intake_kho_cu as KC           # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _db():
    return SessionLocal()


# =============================================================================================
# Dựng tệp Excel KIỂU KHO CŨ – tên sheet tuỳ tiện, nhãn thì cố định
# =============================================================================================

def _tep(ma_tour="KC001.03100726", ten_sheet="PT14012022", khach=True, chi=True,
         so_dong_chi=3) -> bytes:
    """Một workbook giống kho cũ: tên sheet vô nghĩa, nhãn nằm rải rác.

    Cố ý đặt tên sheet là 'PT14012022' — một trong những tên thật đo được trên 604 tệp. Bộ đọc phải
    tìm ra bảng bằng NHÃN chứ không bằng tên sheet; đặt tên sheet là 'QUYẾT TOÁN' thì phép thử này
    không còn canh được điều ấy.
    """
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ten_sheet
    if ma_tour:
        ws["A1"], ws["B1"] = "Mã tour:", ma_tour
    ws["A2"], ws["B2"] = "Tên tour:", "NHA TRANG THỬ"
    ws["A3"], ws["B3"] = "Số khách:", 2
    ws["A4"], ws["B4"] = "Ngày đi:", "10/07/2026"
    ws["A5"], ws["B5"] = "Ngày về:", "12/07/2026"
    ws["A6"], ws["B6"] = "Hướng dẫn viên:", "Nguyễn Văn Thử"

    if khach:
        ws["A8"], ws["B8"], ws["C8"] = "STT", "TÊN KHÁCH HÀNG", "GIÁ BÁN"
        ws["A9"], ws["B9"], ws["C9"] = 1, "Trần Thị A", 5_000_000
        ws["A10"], ws["B10"], ws["C10"] = 2, "Lê Văn B", 5_000_000

    if chi:
        ws2 = wb.create_sheet("CTT")
        ws2["A1"], ws2["B1"], ws2["C1"] = "NGÀY", "NỘI DUNG", "ĐỐI TÁC"
        ws2["D1"], ws2["E1"], ws2["F1"] = "ĐƠN GIÁ", "SL", "THÀNH TIỀN"
        for i in range(so_dong_chi):
            r = 2 + i
            ws2[f"A{r}"] = "10/07/2026"
            ws2[f"B{r}"] = f"Khách sạn đêm {i + 1}"
            ws2[f"C{r}"] = "KS Mường Thanh"
            ws2[f"D{r}"] = 800_000
            ws2[f"E{r}"] = 1
            ws2[f"F{r}"] = 800_000

    b = BytesIO()
    wb.save(b)
    return b.getvalue()


def _tao_chuyen(ma: str, co_phieu_dat=True, doanh_thu=None, gia_von=None) -> int:
    from app.models.core import User
    db = _db()
    t = db.scalars(select(Tour).where(Tour.code == ma)).first()
    if t is None:
        dh = db.scalars(select(User).where(User.username == "dh.lan")).first()
        sale = db.scalars(select(User).where(User.username == "kd.hoa")).first()
        t = Tour(code=ma, name="Chuyến thử kho cũ", tour_type="le_noi_dia", status="ket_thuc",
                 start_date=date(2026, 7, 10), end_date=date(2026, 7, 12),
                 operator_id=dh.id, price_per_pax=5_000_000, planned_pax=2,
                 actual_revenue=doanh_thu, actual_cost=gia_von)
        db.add(t)
        db.flush()
        if co_phieu_dat:
            db.add(Booking(code=f"BKKC{t.id:04d}", tour_id=t.id, request_id=0, sales_id=sale.id,
                           created_by=dh.id, customer_name="Khách thử kho cũ",
                           customer_phone="0988000111", source="Zalo", pax=2,
                           amount=10_000_000))
        db.commit()
    tid = t.id
    db.close()
    return tid


def _dem(tid: int) -> dict:
    db = _db()
    ra = {
        "chi": db.scalar(select(func.count(TourCostLine.id))
                         .where(TourCostLine.tour_id == tid)) or 0,
        "khach": db.scalar(select(func.count(BookingKhach.id))
                           .where(BookingKhach.tour_id == tid)) or 0,
        "hdv": db.scalar(select(func.count(TourHdvChi.id))
                         .where(TourHdvChi.tour_id == tid)) or 0,
    }
    db.close()
    return ra


# =============================================================================================
# C1 · C2 — SOÁT không ghi, và mặc định không ghi
# =============================================================================================

def test_c1_cua_soat_khong_ghi_mot_dong_nao():
    """Nếu bước soát ghi dù chỉ một dòng thì nó không còn là bước soát nữa.

    Đây là điều kiện để người duyệt dám bấm xem: nhìn 604 tệp mà không sợ nhìn xong là dữ liệu đã
    vào sổ.
    """
    tid = _tao_chuyen("KC001.03100726")
    truoc = _dem(tid)
    rows = KC.doc_tep_lo(_tep(), "QT NHA TRANG 10.07.26.xlsx")
    db = _db()
    kq = I.kiem_tra(db, "kho_quyet_toan_cu", rows)
    db.rollback()
    db.close()
    assert kq["so_dong"] == 1
    assert _dem(tid) == truoc, "bước SOÁT đã ghi vào cơ sở dữ liệu – nó phải chỉ đọc"


def test_c2_mac_dinh_KHONG_ghi_gi_vi_thieu_ban_doi_chieu_H1():
    """Chưa có bản đối chiếu H1 thì mọi tệp mang cảnh báo 'không có số thứ hai để soát'.

    Nghĩa là mặc định KHÔNG tệp nào được ghi. Đây là hàng rào đang làm đúng việc, không phải chỗ
    hỏng: một lần nạp 604 tệp mà mặc định là ghi thì chỉ cần một lần bấm nhầm.
    """
    tid = _tao_chuyen("KC002.03100726")
    rows = KC.doc_tep_lo(_tep(ma_tour="KC002.03100726"), "t2.xlsx")

    db = _db()
    soat = KC.kiem_lo(db, rows)
    assert soat["chi_tiet"][0]["ro"] == "can_xac_nhan", soat["chi_tiet"][0]
    assert any("số thứ hai" in c for c in soat["chi_tiet"][0]["can_xac_nhan"]), \
        soat["chi_tiet"][0]["can_xac_nhan"]

    kq = KC.nap_lo(db, rows, "ketoan", "t2.xlsx", bo_qua_dong_loi=False)
    db.commit()
    db.close()
    assert kq["da_nap"] == 0, "mặc định mà đã ghi thì cái tick xác nhận không còn nghĩa gì"
    assert _dem(tid) == {"chi": 0, "khach": 0, "hdv": 0}


# =============================================================================================
# C3 · C4 · C5 — ghi khi được bấm, nạp lại không nhân đôi, không đụng tiền mức chuyến
# =============================================================================================

def test_c3_bam_ro_thi_ghi_va_ghi_dung_ba_bang():
    tid = _tao_chuyen("KC003.03100726")
    rows = KC.doc_tep_lo(_tep(ma_tour="KC003.03100726"), "t3.xlsx")
    db = _db()
    kq = KC.nap_lo(db, rows, "ketoan", "t3.xlsx", bo_qua_dong_loi=True)
    db.commit()
    db.close()
    assert kq["da_nap"] == 1, kq
    d = _dem(tid)
    assert d["chi"] == 3, f"ba dòng chi trong tệp phải vào đủ, đang có {d['chi']}"
    assert d["khach"] == 2, f"hai dòng khách phải vào đủ, đang có {d['khach']}"


def test_c4_nap_LAI_cung_tep_KHONG_nhan_doi():
    """Nạp lại là THAY phần của nguồn mình, không cộng thêm.

    Đây là chỗ một cửa nạp hàng loạt hay hỏng nhất, và nó hỏng IM LẶNG: mọi bảng vẫn cân vì tổng
    nào cũng cộng từ dòng, chỉ có giá vốn gấp đôi.
    """
    tid = _tao_chuyen("KC004.03100726")
    rows = KC.doc_tep_lo(_tep(ma_tour="KC004.03100726"), "t4.xlsx")
    for _ in range(3):
        db = _db()
        KC.nap_lo(db, rows, "ketoan", "t4.xlsx", bo_qua_dong_loi=True)
        db.commit()
        db.close()
    d = _dem(tid)
    assert d["chi"] == 3, f"nạp ba lần mà có {d['chi']} dòng chi – đã nhân lên"
    assert d["khach"] == 2, f"nạp ba lần mà có {d['khach']} dòng khách – đã nhân lên"


def test_c5_KHONG_dung_den_doanh_thu_va_gia_von_MUC_CHUYEN():
    """Bộ đọc chỉ rút được 90,7% doanh thu và 71,1% giá vốn so với bản đối chiếu H1 (đo trên 594
    tệp), phần lệch gần hết ở tour châu Âu ghi bằng EUR/GBP.

    Ghi một con số kém 29% đè lên ô đang có là làm hỏng đúng thứ đang định sửa. Cửa này chỉ bổ sung
    DÒNG; tiền mức chuyến để nguyên cho bản đã chốt.
    """
    tid = _tao_chuyen("KC005.03100726", doanh_thu=99_000_000, gia_von=77_000_000)
    rows = KC.doc_tep_lo(_tep(ma_tour="KC005.03100726"), "t5.xlsx")
    db = _db()
    KC.nap_lo(db, rows, "ketoan", "t5.xlsx", bo_qua_dong_loi=True)
    db.commit()
    db.close()

    db = _db()
    t = db.get(Tour, tid)
    dt, gv = t.actual_revenue, t.actual_cost
    db.close()
    assert dt == 99_000_000, f"doanh thu mức chuyến bị đổi thành {dt}"
    assert gv == 77_000_000, f"giá vốn mức chuyến bị đổi thành {gv}"


def test_c5b_ket_qua_NOI_RA_rang_khong_ghi_tien_muc_chuyen():
    """Không đụng tới là đúng, nhưng im lặng không đụng tới thì người đọc tưởng đã cập nhật xong."""
    _tao_chuyen("KC006.03100726")
    rows = KC.doc_tep_lo(_tep(ma_tour="KC006.03100726"), "t6.xlsx")
    db = _db()
    kq = KC.nap_lo(db, rows, "ketoan", "t6.xlsx", bo_qua_dong_loi=True)
    db.commit()
    db.close()
    assert "khong_ghi_tien_muc_chuyen" in kq
    assert "90,7%" in kq["khong_ghi_tien_muc_chuyen"]


# =============================================================================================
# C6 — không có mã tour thì CHẶN, và chặn cả khi bỏ qua cảnh báo
# =============================================================================================

def test_c6_khong_co_ma_tour_thi_CHAN_va_bo_qua_canh_bao_cung_khong_cuu_duoc():
    """Bộ đọc cố ý KHÔNG suy mã tour từ tên tệp – tên tệp kho cũ đặt bằng tay ("QT TOUR NHA TRANG
    05.06.26"), suy ra là suy ra sai.

    Nên tệp không có nhãn 'Mã tour:' phải bị chặn hẳn. Đây là thứ DUY NHẤT ở mức nặng, và cái tick
    'nạp cả tệp có cảnh báo' không được phép cứu nó: quyết toán không gắn vào chuyến nào là quyết
    toán treo lơ lửng.
    """
    rows = KC.doc_tep_lo(_tep(ma_tour=""), "QT TOUR NHA TRANG 05.06.26.xlsx")
    db = _db()
    soat = KC.kiem_lo(db, rows)
    assert soat["chi_tiet"][0]["ro"] == "khong_thay_chuyen", soat["chi_tiet"][0]
    kq = KC.nap_lo(db, rows, "ketoan", "x.xlsx", bo_qua_dong_loi=True)
    db.commit()
    db.close()
    assert kq["da_nap"] == 0, "tệp không có mã tour đã lọt qua – cái tick không được cứu nó"
    assert kq["dong_loi"] == 1


# =============================================================================================
# C7 — chuyến chưa có phiếu đặt: nói ra, không im lặng
# =============================================================================================

def test_c7_chua_co_phieu_dat_thi_CUA_NAP_TU_DUNG_PHIEU_THEO_NGUOI_BAN():
    """13/9/2026 – phép thử này đổi chiều, và đổi vì một chỗ hỏng thật.

    Bản cũ chốt hành vi: chuyến chưa có phiếu đặt thì dòng khách KHÔNG treo vào đâu được, nên bỏ, và
    phải nói ra. "Nói ra" thì đúng, nhưng "bỏ" là sai — và nó sai to hơn vẻ ngoài: mọi chuyến do cửa
    tạo chuyến sinh ra đều không có phiếu đặt, nên nạp 604 tệp là bỏ TOÀN BỘ doanh thu, giữ lại toàn
    bộ chi phí. Bảng lãi lỗ khi ấy thấy giá vốn mà không thấy doanh thu: mỗi chuyến thành một khoản
    lỗ bằng đúng chi phí, và cộng vào lãi gộp toàn công ty.

    Nay cửa nạp tự dựng phiếu từ cột SALES của tệp, mỗi người bán một phiếu. Dòng khách vào đủ, và
    doanh thu về đúng người bán ra nó.
    """
    tid = _tao_chuyen("KC007.03100726", co_phieu_dat=False)
    rows = KC.doc_tep_lo(_tep(ma_tour="KC007.03100726"), "t7.xlsx")
    db = _db()
    kq = KC.nap_lo(db, rows, "ketoan", "t7.xlsx", bo_qua_dong_loi=True)
    db.commit()
    db.close()
    assert kq["da_nap"] == 1
    assert _dem(tid)["khach"] == 2, \
        "dòng khách vẫn rơi – cửa nạp chưa dựng phiếu đặt, và cả lô sẽ chỉ có chi phí"
    assert "mat_dong_khach_vi_chua_co_phieu_dat" not in kq
    assert _dem(tid)["chi"] == 3

    # Phiếu dựng ra phải mang nhãn nguồn của lô, để nút gỡ cả lô gỡ được đúng phần này.
    from app.models.core import Booking
    db = _db()
    ds = db.scalars(select(Booking).where(Booking.tour_id == tid)).all()
    assert ds and all(b.source == KC.NGUON for b in ds), \
        "phiếu không mang nhãn nguồn – gỡ lô sẽ để lại doanh thu ma trong báo cáo sales"
    db.close()


# =============================================================================================
# C8 — cửa đã khai, bộ kiểm phải thấy
# =============================================================================================

def test_c8_ba_bang_da_co_cua_va_bo_kiem_thay_duoc():
    """Khai `bang_dich` + `bang_phu` không phải cho đẹp: phép kiểm 'mọi bảng phải có một cửa nhập'
    đọc SỐNG từ chỗ ấy. Thiếu khai thì ba bảng bị báo là KHÔNG CÓ CỬA trong khi chúng có – và người
    đọc báo cáo sẽ đi dựng một cửa thứ hai cho thứ đã có cửa.
    """
    bo = I.BO_NAP["kho_quyet_toan_cu"]
    assert bo["bang_dich"] == "tour_cost_lines"
    # 13/9/2026: cửa này ghi thêm hai bảng nữa – `bookings` (phiếu đặt theo người bán, để doanh thu
    # chạy về báo cáo sales) và `kho_cu_nguoi_ban` (sổ gán tên người bán ↔ tài khoản). Khai thiếu thì
    # bộ kiểm báo chúng KHÔNG CÓ CỬA trong khi chúng có.
    assert set(bo["bang_phu"]) == {"booking_khach", "tour_hdv_chi", "bookings",
                                   "kho_cu_nguoi_ban"}
    assert bo["lo"] is True
    for khoa in ("kiem", "nap", "kiem_lo", "nap_lo", "doc_tep"):
        assert callable(bo[khoa]), f"bộ nạp thiếu khoá {khoa}"


def test_c8b_cua_tai_tep_HEP_hon_cua_nhap_tay_dung_mot_bac():
    """Quy tắc P4. Cửa này ghi vào 604 chuyến của sáu tháng đã khép sổ – nhân viên Điều hành gõ tay
    một tờ quyết toán của chính mình thì được, đổ một lượt vào lịch sử nửa năm thì không."""
    assert "kho_quyet_toan_cu" in I.BO_NAP_CHAM_TIEN
    ai = I.VAI_TRO_NAP_TEP["kho_quyet_toan_cu"]
    assert "nv_dh" not in ai, "nhân viên Điều hành không được đổ cả kho cũ vào sổ"
    assert "ketoan" in ai, "Kế toán giữ bản đối chiếu H1 – họ phải nạp được"
    assert "chutich" in ai
