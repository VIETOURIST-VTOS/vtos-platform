# -*- coding: utf-8 -*-
"""ĐÓNG SỐ BÙ cho kho quyết toán cũ T1–T6/2026 — Chủ tịch ký thay các phòng ban.

    "Vì đây là nhập dữ liệu cũ lên hệ thống nên em để Chủ tịch ký thay toàn bộ các phòng ban luôn.
     Khi nào vào vận hành chính thức thì phòng nào ký phòng đó, đúng vai trò thiết lập."
                                                                    — anh Tuấn, 17/9/2026

VÌ SAO CÓ CỬA NÀY: đo 17/9/2026, màn hình Chủ tịch rỗng T1–T5 trong khi ≈36 tỷ đã nằm trong hệ.
456 chuyến T1–T5 không có `closed_at`, mà `ket_qua_that.thang()` lọc đúng theo cột ấy.

══════════════════════════════════════════════════════════════════════════════════════════════════
CHÍN CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════════
DB1  MỐC KỲ LẤY THEO NGÀY CHẠY LỆNH. Chép `closed_at = datetime.now()` từ cửa đóng số thật sang
     đây thì cả 36 tỷ của T1–T5 nhảy vào tháng bấm nút: cột tháng 9 phình lên nhìn y hệt một tháng
     bán tốt, còn năm tháng đầu năm VẪN rỗng. Đây là chỗ hỏng nguy hiểm nhất của cả tệp, vì sai
     kiểu ấy tệ hơn rỗng — rỗng thì người đọc biết là thiếu.
DB2  BẤM NHẦM LÀ GHI. Mặc định phải là XEM TRƯỚC.
DB3  KHÔNG CÓ DÒNG CHI PHÍ MÀ VẪN ĐÓNG. Ghi giá vốn 0 đồng, chuyến báo lãi bằng đúng toàn bộ doanh
     thu, biên 100%. Bảng vẫn cân nên không ai nhìn ra — đúng điều `ket_qua_that.py` sinh ra để
     chặn; cửa này không được phá nó từ đầu kia.
DB4  DOANH THU BẰNG 0 MÀ VẪN ĐÓNG. Ghi một khoản lỗ bằng đúng chi phí vào báo cáo Chủ tịch.
DB5  CHUYẾN CHƯA KẾT THÚC MÀ VẪN ĐÓNG. Hàng rào của cửa đóng số thật phải giữ nguyên.
DB6  ĐỤNG CHUYẾN VẬN HÀNH. Cửa này tồn tại cho ĐÚNG MỘT LÔ; chuyến nguồn khác không bao giờ động.
DB7  TỰ CỘNG LẠI DOANH THU. Bản nháp đầu cộng thẳng `bookings.amount` — thiếu trừ `discount`, thiếu
     luật bỏ phiếu đã huỷ và dòng chi đã huỷ. Hai phép cộng cho cùng một câu hỏi là hai con số sẽ
     lệch nhau vào ngày không ai để ý.
DB8  XEM TRƯỚC NÓI MỘT ĐẰNG, NÚT LÀM MỘT NẺO. Bài học vá 10b (3,86 tỷ mất im lặng).
DB9  NÚT GỠ GỠ LUÔN CHUYẾN ĐIỀU HÀNH ĐÃ ĐÓNG SỐ THẬT. Hai cửa cùng ghi vào một cột `closed_at`;
     đo 17/9 đã có 82 chuyến kho cũ mang `closed_at` thật, nên đây không phải giả định.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_dsbu.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_dsbu.db", "test_dsbu.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date, datetime, timedelta                        # noqa: E402

import pytest                                                         # noqa: E402

from app.core.security import hash_password                           # noqa: E402
from app.db.session import Base, SessionLocal, engine                  # noqa: E402
import app.models                                                      # noqa: E402,F401
from app.models.core import Booking, Company, Tour, User               # noqa: E402
from app.models.vietrip import TourCostLine                            # noqa: E402
from app.services import dong_so_kho_cu as DS                          # noqa: E402
from app.services import ket_qua_that as KQ                            # noqa: E402

Base.metadata.create_all(engine)

HOM_QUA = date.today() - timedelta(days=1)
MAI = date.today() + timedelta(days=1)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(TourCostLine).delete()
    s.query(Booking).delete()
    s.query(Tour).delete()
    s.query(User).filter(User.username.in_(("dh_bu", "sale_bu"))).delete()
    s.query(Company).delete()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    s.add(me)
    s.add_all([User(username="dh_bu", full_name="Điều hành", role="nv_dh",
                    password_hash=hash_password("x")),
               User(username="sale_bu", full_name="Sale", role="nv_kd",
                    password_hash=hash_password("x"))])
    s.commit()
    yield s
    s.close()


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# Dựng số giả BẰNG ĐÚNG THỨ CỬA NẠP KHO CŨ ĐỂ LẠI: chuyến mang `confirmed_by = NGUON`, có dòng
# khách và dòng chi, nhưng `actual_revenue` / `actual_cost` / `closed_at` đều rỗng. Dựng sẵn số
# quyết toán ở đây là dựng một tình huống không tồn tại ngoài đời.
# ─────────────────────────────────────────────────────────────────────────────────────────────────

def _chuyen(db, code, ket_thuc, nguon=DS.NGUON, status="ket_thuc", cty=True) -> Tour:
    u = db.query(User).filter_by(username="dh_bu").one()
    me = db.query(Company).filter_by(code="VTD").one()
    t = Tour(code=code, name=code, tour_type="package",
             start_date=ket_thuc - timedelta(days=2), end_date=ket_thuc,
             operator_id=u.id, status=status, confirmed_by=nguon,
             company_id=me.id if cty else None)
    db.add(t); db.commit()
    return t


def _khach(db, t: Tour, tien: float, giam: float = 0, huy: bool = False):
    s = db.query(User).filter_by(username="sale_bu").one()
    db.add(Booking(code=f"B{t.id}-{tien:.0f}-{int(huy)}", tour_id=t.id, request_id=0,
                   sales_id=s.id, created_by=s.id, customer_name="Khách", customer_phone="0900",
                   source="kho_cu", amount=tien, discount=giam, cancelled=huy))
    db.commit()


def _chi(db, t: Tour, tien: float, huy: bool = False):
    db.add(TourCostLine(tour_id=t.id, description="Chi", actual=tien,
                        status="huy" if huy else "hd"))
    db.commit()


def _mot_chuyen_du(db, code="T3", ket_thuc=date(2026, 3, 15), thu=100.0, von=60.0) -> Tour:
    t = _chuyen(db, code, ket_thuc)
    _khach(db, t, thu)
    _chi(db, t, von)
    return t


# ═════════════════ DB1 · MỐC KỲ — CHỖ HỎNG NGUY HIỂM NHẤT ═════════════════

def test_db1_tien_roi_vao_thang_cua_chuyen_khong_phai_thang_bam_nut(db):
    """Nếu ai đó "dọn cho gọn" `moc_ky()` thành `datetime.now()`, phép thử này phải đỏ.

    Canh CẢ HAI ĐẦU: tháng của chuyến phải có tiền, VÀ tháng chạy lệnh phải không có. Canh một đầu
    thôi thì một phép lọc hỏng theo kiểu "cộng vào cả hai tháng" vẫn xanh.
    """
    t = _mot_chuyen_du(db, ket_thuc=date(2026, 3, 15))
    DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit()

    db.refresh(t)
    assert t.closed_at == datetime(2026, 3, 15, 23, 59, 59), (
        "Mốc kỳ phải là CUỐI NGÀY KẾT THÚC CHUYẾN. Lấy theo ngày chạy lệnh thì cả ≈36 tỷ của "
        f"T1–T5 nhảy vào tháng bấm nút. Đang là {t.closed_at!r}."
    )

    assert KQ.thang(db, "2026-03")["doanh_thu"] == 100.0, (
        "Tháng 3 vẫn rỗng sau khi đóng số bù — đúng cái bệnh cửa này sinh ra để chữa.")

    thang_chay = f"{date.today():%Y-%m}"
    if thang_chay != "2026-03":
        assert KQ.thang(db, thang_chay)["doanh_thu"] is None, (
            f"Tiền của chuyến tháng 3 rơi vào tháng chạy lệnh ({thang_chay}). Một cột phình lên "
            "nhìn không khác gì một tháng bán tốt, và không có gì kêu lên.")


def test_db1b_moc_ky_doc_thang_tu_ngay_ket_thuc_cua_tung_chuyen(db):
    """Hai chuyến hai tháng khác nhau phải rơi vào hai tháng khác nhau — không dồn một chỗ."""
    _mot_chuyen_du(db, code="A1", ket_thuc=date(2026, 1, 20), thu=10.0, von=4.0)
    _mot_chuyen_du(db, code="A5", ket_thuc=date(2026, 5, 20), thu=50.0, von=20.0)
    DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit()

    assert KQ.thang(db, "2026-01")["doanh_thu"] == 10.0
    assert KQ.thang(db, "2026-05")["doanh_thu"] == 50.0
    assert KQ.thang(db, "2026-01")["lai_tour"] == 6.0


def test_db1c_chuyen_vat_qua_dau_thang_tinh_theo_NGAY_VE_khong_phai_ngay_di(db):
    """Chuyến đi 27/2 về 2/3 thuộc tháng 3.

    `moc_ky` đọc `end_date`. Đổi thành `start_date` thì phần lớn chuyến vẫn rơi đúng tháng — chỉ
    những chuyến vắt qua đầu tháng mới lệch, và đó đúng là loại lỗi không ai phát hiện ra bằng mắt.
    Quyết toán chốt khi chuyến kết thúc, nên tháng của nó là tháng về.
    """
    t = _chuyen(db, "VATTHANG", date(2026, 3, 2))
    t.start_date = date(2026, 2, 27); db.commit()
    _khach(db, t, 80.0); _chi(db, t, 30.0)

    DS.chay(db, boi="chutich", xac_nhan=True); db.commit(); db.refresh(t)

    assert t.closed_at == datetime(2026, 3, 2, 23, 59, 59)
    assert KQ.thang(db, "2026-03")["doanh_thu"] == 80.0
    assert KQ.thang(db, "2026-02")["doanh_thu"] is None, (
        "Chuyến về tháng 3 bị xếp vào tháng 2 — mốc kỳ đang đọc ngày đi thay vì ngày về.")


# ═════════════════ DB2 · MẶC ĐỊNH KHÔNG GHI GÌ ═════════════════

def test_db2_khong_xac_nhan_thi_khong_ghi_mot_dong_nao(db):
    t = _mot_chuyen_du(db)
    kq = DS.chay(db, boi="chutich")
    db.commit()
    db.refresh(t)

    assert kq["da_dong"] == 0
    assert t.closed_at is None and t.actual_revenue is None and t.status == "ket_thuc", (
        "Gọi thiếu `xac_nhan` mà vẫn ghi: một cú bấm nhầm đóng số cả lô.")
    assert DS.xem(db)["se_dong"] == 1


# ═════════════════ DB3–DB5 · BA CHUYẾN KHÔNG ĐƯỢC ĐÓNG ═════════════════

def test_db3_khong_co_dong_chi_phi_thi_khong_dong_va_noi_ra_vi_sao(db):
    """Đóng là ghi giá vốn 0 đồng, và chuyến ấy báo lãi 100% trên toàn bộ doanh thu."""
    t = _chuyen(db, "KHONGCHI", date(2026, 2, 10))
    _khach(db, t, 500.0)

    kq = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(t)

    assert t.closed_at is None and t.actual_cost is None
    assert kq["da_dong"] == 0 and kq["khong_dong_duoc"] == 1
    assert any("chi phí" in v for v in kq["vi_sao_khong_dong"]), (
        "Chuyến bị bỏ ra mà không nói vì sao thì người ký phải đi đoán. "
        f"Đang là {kq['vi_sao_khong_dong']!r}")


def test_db4_doanh_thu_bang_0_thi_khong_dong(db):
    """Đóng là ghi một khoản lỗ bằng đúng chi phí vào báo cáo Chủ tịch."""
    t = _chuyen(db, "KHONGTHU", date(2026, 2, 11))
    _chi(db, t, 70.0)

    kq = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(t)

    assert t.closed_at is None and kq["da_dong"] == 0
    assert any("doanh thu" in v for v in kq["vi_sao_khong_dong"])


def test_db5_chuyen_chua_ket_thuc_thi_khong_dong(db):
    t = _mot_chuyen_du(db, code="CHUAVE", ket_thuc=MAI)

    kq = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(t)

    assert t.closed_at is None and kq["da_dong"] == 0
    assert any("chưa kết thúc" in v for v in kq["vi_sao_khong_dong"])


def test_db5b_trang_thai_ngoai_buoc_quyet_toan_thi_khong_dong(db):
    """Chuyến còn ở bước bán (`moi`) chưa có gì để quyết toán."""
    t = _mot_chuyen_du(db, code="CONMOI", ket_thuc=HOM_QUA)
    t.status = "moi"; db.commit()

    kq = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(t)

    assert t.closed_at is None and kq["da_dong"] == 0
    assert any("trạng thái" in v for v in kq["vi_sao_khong_dong"])


# ═════════════════ DB6 · KHÔNG ĐỤNG CHUYẾN VẬN HÀNH ═════════════════

def test_db6_chuyen_khong_phai_kho_cu_thi_khong_bao_gio_dung_toi(db):
    """Cửa này tồn tại cho ĐÚNG MỘT LÔ. Nó không phải lối tắt của cửa đóng số thật."""
    that = _chuyen(db, "VANHANH", date(2026, 3, 15), nguon="dieu_hanh")
    _khach(db, that, 900.0); _chi(db, that, 100.0)
    _mot_chuyen_du(db, code="KHOCU", ket_thuc=date(2026, 3, 15))

    kq = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(that)

    assert kq["da_dong"] == 1, "Cửa bù phải chỉ đóng chuyến của kho cũ."
    assert that.closed_at is None and that.status == "ket_thuc", (
        "Cửa bù đã đóng số hộ một chuyến vận hành — đó là ký thay Điều hành ngoài phạm vi "
        "Chủ tịch đã chốt.")
    assert KQ.thang(db, "2026-03")["doanh_thu"] == 100.0


# ═════════════════ DB7 · DÙNG ĐÚNG PHÉP CỘNG CỦA HỆ ═════════════════

def test_db7_doanh_thu_tru_giam_gia_bo_phieu_huy_bo_dong_chi_huy(db):
    """Bản nháp đầu tự cộng `bookings.amount` — xanh với số giả đơn giản, sai với số thật.

    Số giả ở đây cố tình có đủ ba thứ mà phép cộng tay bỏ sót.
    """
    t = _chuyen(db, "DUPHEP", date(2026, 4, 10))
    _khach(db, t, 100.0, giam=30.0)          # còn 70
    _khach(db, t, 500.0, huy=True)           # phiếu huỷ – không cộng
    _chi(db, t, 20.0)
    _chi(db, t, 999.0, huy=True)             # dòng chi huỷ – không cộng

    DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(t)

    assert t.actual_revenue == 70.0, (
        f"Doanh thu phải là 100 − 30 = 70, bỏ phiếu đã huỷ. Đang là {t.actual_revenue}.")
    assert t.actual_cost == 20.0, (
        f"Giá vốn phải bỏ dòng chi đã huỷ. Đang là {t.actual_cost}.")


# ═════════════════ DB8 · XEM TRƯỚC KHÔNG ĐƯỢC NÓI DỐI ═════════════════

def test_db8_xem_truoc_noi_dung_con_so_ma_nut_se_lam(db):
    """Bài học vá 10b: bảng xem trước hứa 43 quyển, nút ghi 17 quyển, và không gì kêu lên.

    Số giả ở đây trộn đủ cả bốn loại: đóng được, thiếu chi, thiếu thu, chưa về.
    """
    _mot_chuyen_du(db, code="X1", ket_thuc=date(2026, 3, 1), thu=10.0, von=3.0)
    _mot_chuyen_du(db, code="X2", ket_thuc=date(2026, 4, 1), thu=20.0, von=5.0)
    k = _chuyen(db, "X3", date(2026, 4, 2)); _khach(db, k, 99.0)          # thiếu chi
    m = _chuyen(db, "X4", date(2026, 4, 3)); _chi(db, m, 9.0)             # thiếu thu
    _mot_chuyen_du(db, code="X5", ket_thuc=MAI)                          # chưa về

    truoc = DS.xem(db)
    sau = DS.chay(db, boi="chutich", xac_nhan=True)
    db.commit()

    assert truoc["se_dong"] == sau["da_dong"] == 2, (
        f"Xem trước hứa {truoc['se_dong']}, nút làm {sau['da_dong']}.")
    assert truoc["tong_doanh_thu"] == 30.0
    assert truoc["khong_dong_duoc"] == 3
    assert {k["ky"]: k["doanh_thu"] for k in truoc["theo_ky"]} == {"2026-03": 10.0,
                                                                  "2026-04": 20.0}, (
        "Bảng theo kỳ là thứ DUY NHẤT cho người ký thấy tiền sẽ rơi vào tháng nào trước khi ký.")
    assert KQ.thang(db, "2026-03")["doanh_thu"] == 10.0
    assert KQ.thang(db, "2026-04")["doanh_thu"] == 20.0


def test_db8b_chay_lan_hai_khong_dong_them_va_khong_nhan_doi_tien(db):
    t = _mot_chuyen_du(db, ket_thuc=date(2026, 3, 15))
    DS.chay(db, boi="chutich", xac_nhan=True); db.commit()
    lan2 = DS.chay(db, boi="chutich", xac_nhan=True); db.commit()

    db.refresh(t)
    assert lan2["da_dong"] == 0 and lan2["ung_vien"] == 0
    assert t.actual_revenue == 100.0
    assert KQ.thang(db, "2026-03")["du_so"] == 1


# ═════════════════ DB9 · NÚT GỠ ═════════════════

def test_db9_go_khong_dung_chuyen_dieu_hanh_da_dong_so_that(db):
    """Hai cửa cùng ghi vào một cột. Đo 17/9 đã có 82 chuyến kho cũ mang `closed_at` thật."""
    bu = _mot_chuyen_du(db, code="BU", ket_thuc=date(2026, 3, 15))
    that = _mot_chuyen_du(db, code="THAT", ket_thuc=date(2026, 3, 16))
    DS.chay(db, boi="chutich", xac_nhan=True); db.commit()

    # Điều hành đóng số chuyến THAT bằng cửa thật: mốc là lúc bấm, có micro-giây.
    that.closed_at = datetime.now()
    db.commit()

    xem = DS.go(db, boi="chutich")
    kq = DS.go(db, boi="chutich", xac_nhan=True)
    db.commit(); db.refresh(bu); db.refresh(that)

    assert xem["se_go"] == kq["da_go"] == 1, f"Xem trước hứa {xem['se_go']}, gỡ {kq['da_go']}."
    assert kq["giu_lai_do_dong_that"] == 1
    assert bu.closed_at is None and bu.status == "ket_thuc" and bu.actual_revenue is None
    assert that.closed_at is not None and that.status == "da_dong_so", (
        "Cửa gỡ đã kéo về một chuyến Điều hành đóng số thật — xoá công việc của người khác.")


def test_db9b_go_xong_chay_lai_duoc_va_ra_dung_nhu_lan_dau(db):
    t = _mot_chuyen_du(db, ket_thuc=date(2026, 3, 15))
    l1 = DS.chay(db, boi="chutich", xac_nhan=True); db.commit()
    DS.go(db, boi="chutich", xac_nhan=True); db.commit()
    l2 = DS.chay(db, boi="chutich", xac_nhan=True); db.commit()

    db.refresh(t)
    assert l1["da_dong"] == l2["da_dong"] == 1
    assert l1["tong_doanh_thu"] == l2["tong_doanh_thu"] == 100.0
    assert t.closed_at == datetime(2026, 3, 15, 23, 59, 59)


# ═════════════════ ĐẾM RIÊNG SỐ BÙ TRÊN MÀN HÌNH CHỦ TỊCH ═════════════════

def test_dem_rieng_so_vao_bang_cua_bu_de_nguoi_doc_biet_muc_tin(db):
    """Một tháng gần như toàn số bù là số nhập lại từ Excel, chưa qua vòng duyệt của Điều hành và
    Kế toán. Mức tin vào nó khác hẳn tháng vận hành thật, nên phải đếm riêng chứ không trộn vào."""
    _mot_chuyen_du(db, code="BU1", ket_thuc=date(2026, 3, 15), thu=10.0, von=3.0)
    that = _chuyen(db, "THAT1", date(2026, 3, 16), nguon="dieu_hanh")
    _khach(db, that, 20.0); _chi(db, that, 5.0)
    DS.chay(db, boi="chutich", xac_nhan=True)
    that.actual_revenue, that.actual_cost = 20.0, 5.0
    # Điều hành đóng số thật vài ngày sau chuyến: mốc là LÚC BẤM, có giờ phút và micro-giây.
    that.closed_at, that.status = datetime(2026, 3, 20, 10, 30, 15, 123456), "da_dong_so"
    db.commit()

    t3 = KQ.thang(db, "2026-03")
    assert t3["du_so"] == 2 and t3["dong_so_bu"] == 1, (
        f"Tháng 3 có 2 chuyến đủ số, 1 trong đó vào bằng cửa bù. Đang là {t3['dong_so_bu']}.")
