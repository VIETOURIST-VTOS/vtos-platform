# -*- coding: utf-8 -*-
"""CỬA TẢI BẢN ĐỐI CHIẾU H1/2026 – ghi tổng thu, tổng chi mức chuyến.

VÌ SAO CỬA NÀY TỒN TẠI

Hai cửa trước cố ý KHÔNG ghi tiền mức chuyến, và lý do đo được: bộ đọc 604 tệp Excel chỉ rút ra 90,7%
doanh thu và 71,1% giá vốn so với bản Kế toán đã chốt. Ghi `actual_cost` bằng con số kém 29% là làm
mọi chuyến trông lãi hơn thật gần một phần ba — và con số ấy chảy thẳng lên bảng Ban điều hành.

Bản đối chiếu H1 là chỗ duy nhất có số đúng ở mức chuyến: 624 chuyến, 97,5 tỷ doanh thu, 80,9 tỷ giá
vốn, đã đối với MISA.

  DC1  đọc đúng sheet 'DOI CHIEU TUNG TOUR', không lấy bừa sheet đầu (sheet đầu là bảng tóm tắt)
  DC2  ghép bằng TÊN TỆP qua sổ tệp↔chuyến — 507/624 dòng chỉ ghép được đường này
  DC3  ghép được cả khi ô 'Mã tour' thật ra là tên tệp
  DC4  ghi tổng thu / tổng chi vào chuyến, và chuyến của lô chuyển sang 'khoa'
  DC5  trạng thái là 'khoa', KHÔNG phải 'kt_xac_nhan' — không kế toán nào bấm cả
  DC6  KHÔNG đè số của chuyến không do lô tạo ra mà đã có tiền; xếp vào 'cần xác nhận'
  DC7  chuyến ngoài lô thì KHÔNG bị đổi trạng thái, kể cả khi người bấm ghi đè
  DC8  dòng không tìm được chuyến thì bỏ và nói ra, không tạo chuyến ma
  DC9  KHÔNG sinh bút toán kế toán — sổ H1 đã khoá và đã ra báo cáo bán niên
  DC10 nạp lại cùng bản thì THAY, không cộng dồn
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_dch1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_dch1.db", "test_dch1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import io                                                            # noqa: E402
from datetime import date                                            # noqa: E402

import pytest                                                        # noqa: E402
from openpyxl import Workbook                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.accounting import JournalEntry                        # noqa: E402
from app.models.core import Tour, User                                # noqa: E402
from app.models.kho_cu import KhoCuTepChuyen                          # noqa: E402
from app.services import intake_doi_chieu_h1 as DC                    # noqa: E402
from app.services import intake_tao_chuyen as TCN                     # noqa: E402

Base.metadata.create_all(engine)

TEP_LO = "QT NHA TRANG 05.01.26.xlsx"          # tệp đẻ ra chuyến của lô
TEP_MA = "QUYẾT TOÁN EU 5N 18.03.26 SGN.xlsx"  # dòng ghi tên tệp vào ô 'Mã tour'


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(KhoCuTepChuyen).delete()
    s.query(Tour).delete()
    s.query(User).delete()
    s.add(User(username=TCN.TAI_KHOAN_MAC_DINH, full_name="Điều hành Vietrip", role="nv_dh",
               password_hash=hash_password("x"), active=False))
    s.flush()
    dh = s.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).one()

    def _t(ma, cua_lo, thu=None, chi=None):
        return Tour(code=ma, name=ma, tour_type="ghep", start_date=date(2026, 1, 5),
                    end_date=date(2026, 1, 7), operator_id=dh.id, status="ket_thuc",
                    actual_revenue=thu, actual_cost=chi,
                    confirmed_by=(TCN.NGUON if cua_lo else "kd.hoa"),
                    approved_by=(TCN.NGUON if cua_lo else "tp.dh"))

    s.add_all([
        _t("NT001.03050126", True),                                   # chuyến của lô
        _t("EU005.03180326", True),                                   # chuyến của lô, ghép qua ô mã
        _t("VTR-9001", False, thu=500_000_000, chi=400_000_000),      # chuyến Vietrip, ĐÃ có tiền
    ])
    s.flush()
    for ma, tep in (("NT001.03050126", TEP_LO), ("EU005.03180326", TEP_MA)):
        t = s.query(Tour).filter(Tour.code == ma).one()
        s.add(KhoCuTepChuyen(khoa_tep=TCN.TC.khoa_tep(tep), ten_tep=tep, ma_tour=ma, tour_id=t.id))
    s.commit()
    yield s
    s.close()


def _tep(dong: list[tuple]) -> bytes:
    """Dựng một tệp đúng hình bản đối chiếu thật: sheet tóm tắt ĐỨNG TRƯỚC sheet cần đọc."""
    wb = Workbook()
    tt = wb.active
    tt.title = "TONG HOP"
    tt.append(["ĐỐI CHIẾU QUYẾT TOÁN H1/2026"])
    tt.append(["Mã tour", "Tổng thu (QT)"])        # bẫy: trông như tiêu đề, nhưng sai sheet
    tt.append(["BAY-NEU-DOC-NHAM", 999_999_999])

    ws = wb.create_sheet(DC.SHEET)
    ws.append(["ĐỐI CHIẾU TỪNG TOUR"])
    ws.append([])
    ws.append(["STT", "Nhóm", "Mã tour", "Tháng", "Nguồn số liệu", "File quyết toán",
               "Số khách", "Tổng thu (QT)", "Tổng chi (QT)"])
    for i, (nhom, ma, tep, kh, thu, chi) in enumerate(dong, 1):
        ws.append([i, nhom, ma, "T1", "File quyết toán", tep, kh, thu, chi])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


DONG = [
    ("Tour lẻ", "NT001.03050126", TEP_LO, 30, 1_200_000_000, 900_000_000),
    ("Tour lẻ", TEP_MA, "", 44, 2_400_000_000, 2_200_000_000),   # ô 'Mã tour' là TÊN TỆP
    ("Tour lẻ", "VTR-9001", "", 20, 111_000_000, 99_000_000),    # chuyến ngoài lô, đã có tiền
    ("MICE", "KHONG-CO-TEP-NAO", "Báo cáo doanh thu team đoàn", 10, 50_000_000, 40_000_000),
]


def _doc():
    return DC.doc_tep(_tep(DONG), "doi-chieu.xlsx")


def test_dc1_doc_dung_sheet_doi_chieu_khong_lay_bua_sheet_dau(db):
    """Tệp thật có 6 sheet và sheet đầu là bảng tóm tắt. Đọc nhầm nó thì ra một bảng số trông hợp lý
    mà sai hẳn tầng — loại sai không ai soi ra bằng mắt."""
    rows = _doc()
    assert len(rows) == 4
    assert all(r["ma_tour"] != "BAY-NEU-DOC-NHAM" for r in rows), \
        "đang đọc sheet tóm tắt chứ không đọc sheet đối chiếu"
    assert rows[0]["tong_thu"] == 1_200_000_000 and rows[0]["tong_chi"] == 900_000_000


def test_dc2_ghep_bang_TEN_TEP_qua_so_tep_chuyen(db):
    """507/624 dòng của bản thật chỉ ghép được đường này. Mã tour nằm bên trong tệp Excel, nên bản
    đối chiếu — vốn chỉ có tên tệp — không tự suy ra được."""
    kq = DC.kiem_lo(db, _doc())
    x = next(r for r in kq["chi_tiet"] if r["ma_tour"] == "NT001.03050126")
    assert x["duong_ghep"] == "so_tep" and x["ro"] == "nap_duoc"


def test_dc3_ghep_duoc_ca_khi_o_ma_tour_that_ra_la_ten_tep(db):
    kq = DC.kiem_lo(db, _doc())
    x = next(r for r in kq["chi_tiet"] if r["ma_tour"] == TEP_MA)
    assert x["ro"] == "nap_duoc" and x["ma_chuyen"] == "EU005.03180326"
    assert x["duong_ghep"] == "so_ma"


def test_dc4_ghi_tien_muc_chuyen_va_dong_khoa_chuyen_cua_lo(db):
    kq = DC.nap_lo(db, _doc(), boi="ketoan")
    db.commit()
    assert kq["da_nap"] == 2
    t = db.query(Tour).filter(Tour.code == "NT001.03050126").one()
    assert float(t.actual_revenue) == 1_200_000_000 and float(t.actual_cost) == 900_000_000
    assert t.status == "khoa", \
        "chuyến vẫn ở 'ket_thuc' – nó sẽ tiếp tục hiện đỏ 'quá hạn quyết toán' trên bảng Chủ tịch"


def test_dc5_trang_thai_la_khoa_KHONG_phai_ke_toan_da_xac_nhan(db):
    """'kt_xac_nhan' nghĩa là Kế toán đã xác nhận. Không kế toán nào bấm cả – máy ghi vào ô ấy là
    làm hệ thống ghi nhận một chữ ký không ai ký."""
    assert DC.TRANG_THAI_SAU_NAP == "khoa"
    DC.nap_lo(db, _doc(), boi="ketoan")
    db.commit()
    assert not db.query(Tour).filter(Tour.status == "kt_xac_nhan").count()


def test_dc6_KHONG_de_so_cua_chuyen_ngoai_lo_da_co_tien(db):
    """Đè lên số của hệ đang chạy là loại sai không lùi lại được."""
    kq = DC.kiem_lo(db, _doc())
    x = next(r for r in kq["chi_tiet"] if r["ma_tour"] == "VTR-9001")
    assert x["ro"] == "can_xac_nhan", "máy tự đè doanh thu của một chuyến Vietrip đang chạy"
    assert x["thu_dang_co"] == 500_000_000 and x["tong_thu"] == 111_000_000, \
        "không nêu cả hai con số thì người xác nhận lấy gì mà quyết"

    DC.nap_lo(db, _doc(), boi="ketoan")
    db.commit()
    t = db.query(Tour).filter(Tour.code == "VTR-9001").one()
    assert float(t.actual_revenue) == 500_000_000, "vẫn bị đè dù xếp vào rổ cần xác nhận"


def test_dc7_bam_de_thi_ghi_tien_nhung_KHONG_doi_trang_thai_chuyen_ngoai_lo(db):
    """Chuyến của hệ đang chạy có luồng trạng thái riêng – kéo nó sang 'khoa' là cắt ngang quy trình
    của người khác, và người ta mất chỗ để làm nốt."""
    DC.nap_lo(db, _doc(), boi="ketoan", bo_qua_dong_loi=True)
    db.commit()
    t = db.query(Tour).filter(Tour.code == "VTR-9001").one()
    assert float(t.actual_revenue) == 111_000_000, "bấm đè rồi mà không ghi"
    assert t.status == "ket_thuc", "đã kéo trạng thái của một chuyến không thuộc lô"


def test_dc8_dong_khong_tim_duoc_chuyen_thi_bo_va_NOI_RA(db):
    """14 dòng của bản thật lấy từ 'Báo cáo doanh thu team đoàn' – không có tệp quyết toán nào cả.
    Tạo chuyến ma cho chúng là đẻ ra 14 chuyến không ai nhận."""
    kq = DC.nap_lo(db, _doc(), boi="ketoan", bo_qua_dong_loi=True)
    db.commit()
    assert db.query(Tour).count() == 3, "đã tạo chuyến mới từ một dòng không ghép được"
    bo = [x for x in kq["chi_tiet_bo_qua"] if x["ma_tour"] == "KHONG-CO-TEP-NAO"]
    assert bo and bo[0]["ro"] == "khong_thay_chuyen"


def test_dc9_KHONG_sinh_but_toan_ke_toan(db):
    """Sổ H1/2026 đã khoá và đã ra báo cáo tài chính bán niên. Sinh bút toán bây giờ là ghi trùng
    doanh thu cả nửa năm, và không bảng nào kêu vì mọi tổng đều cộng từ dòng."""
    truoc = db.query(JournalEntry).count()
    DC.nap_lo(db, _doc(), boi="ketoan", bo_qua_dong_loi=True)
    db.commit()
    assert db.query(JournalEntry).count() == truoc, \
        "cửa này đã sinh bút toán – doanh thu H1 sẽ vào sổ lần thứ hai"


def test_dc10_nap_lai_thi_THAY_khong_cong_don(db):
    DC.nap_lo(db, _doc(), boi="ketoan")
    db.commit()
    DC.nap_lo(db, _doc(), boi="ketoan")
    db.commit()
    t = db.query(Tour).filter(Tour.code == "NT001.03050126").one()
    assert float(t.actual_revenue) == 1_200_000_000, "nạp hai lần thành doanh thu gấp đôi"
