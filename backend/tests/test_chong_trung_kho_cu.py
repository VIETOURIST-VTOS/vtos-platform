# -*- coding: utf-8 -*-
"""Chống trùng khi nạp kho quyết toán cũ T1–T6/2026 vào VTOS.

VÌ SAO PHÉP THỬ NÀY TỒN TẠI

Chủ tịch chốt 11/9/2026: nạp trọn kho 604 tệp, nhưng KHÔNG được trùng với dữ liệu đang có. Kiểu
trùng nguy nhất không tự lộ ra: cộng thêm một bộ dòng chi vào chuyến đã có dòng chi thì giá vốn gấp
đôi và lợi nhuận âm, nhưng MỌI BẢNG VẪN CÂN – vì tổng nào trong hệ cũng cộng lại từ dòng. Không có
phép kiểm nào đỏ lên, không ai nhìn bằng mắt mà thấy.

BA ĐIỀU NÓ CANH

1. NẠP LẠI LÀ THAY. Nạp cùng một lô ba lần phải ra đúng một kết quả.
2. NGUỒN KHÁC THÌ DỪNG. Chuyến đã có giá vốn từ Vietrip thì bỏ qua chuyến ấy, và CHỈ chuyến ấy.
3. PHÂN BIỆT ĐƯỢC PHẦN CỦA CHÍNH MÌNH. Nếu không, sau lần nạp đầu chính dòng vừa ghi trở thành
   "dữ liệu đang có", lần sau bị chặn bằng cảnh báo do chính nó tạo ra, và người chạy sẽ bật cờ
   --ke-ca-canh-bao cho xong – rồi bật luôn cả lúc va chạm là thật.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_chong_trung.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_chong_trung.db"):
    os.remove("test_chong_trung.db")

from datetime import date                                           # noqa: E402
import pytest                                                       # noqa: E402
from sqlalchemy import func, select                                 # noqa: E402
from app.db.session import SessionLocal, Base, engine                # noqa: E402
import app.models                                                    # noqa: E402,F401
from app.models.core import Booking, Tour, User                      # noqa: E402
from app.models.lop3_tour import BookingKhach, TourHdvChi            # noqa: E402
from app.models.vietrip import TourCostLine                          # noqa: E402
from app.services import chong_trung_quyet_toan as CT                # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    u = s.scalars(select(User)).first()
    if u is None:
        u = User(username="kt", password_hash="x", role="cntt", full_name="KT")
        s.add(u); s.flush()
    for ma in ("KC-001", "KC-002"):
        if s.scalars(select(Tour).where(Tour.code == ma)).first():
            continue
        t = Tour(code=ma, name="CHUYẾN KHO CŨ", tour_type="package", operator_id=u.id,
                 start_date=date(2026, 3, 1), end_date=date(2026, 3, 3), planned_pax=2)
        s.add(t); s.flush()
        s.add(Booking(code=f"BK-{ma}", tour_id=t.id, request_id=0, sales_id=u.id,
                      customer_name="X", customer_phone="0900000000", pax=2,
                      source="test", created_by="test"))
    s.commit()
    yield s
    s.close()


def _tour(db, ma):
    return db.scalars(select(Tour).where(Tour.code == ma)).first()


# ------------------------------------------------------------------ vân tay

def test_ma_tour_go_khac_kieu_van_la_mot_chuyen():
    """'NT001.03100726', 'nt001.03100726' và 'NT001. 03100726' là MỘT chuyến.

    So bằng chuỗi thô thì ba cách gõ ấy thành ba chuyến, và chống trùng thành vô nghĩa đúng ở chỗ
    nó cần có tác dụng nhất.
    """
    a = CT.van_tay_chuyen({"ma_tour": "NT001.03100726"})
    b = CT.van_tay_chuyen({"ma_tour": "nt001.03100726"})
    c = CT.van_tay_chuyen({"ma_tour": "NT001. 03100726"})
    assert a == b == c


def test_khong_doc_duoc_gi_thi_MOI_TEP_MOT_DAU_RIENG():
    """Tệp không có mã, không ngày, không tiền thì KHÔNG được gom thành 'cùng một chuyến'.

    Bản đầu trả về cùng một chuỗi cho mọi tệp như thế, và 24 tệp khác hẳn nhau bị báo là trùng.
    Một phép kiểm báo trùng ở chỗ không trùng thì người ta học cách bỏ qua nó.
    """
    x = {"ma_tour": "", "ngay_di": None, "so_khach": None, "tong_thu": None, "ten_tep": "a.xlsx"}
    y = {**x, "ten_tep": "b.xlsx"}
    assert CT.van_tay_chuyen(x) != CT.van_tay_chuyen(y)


def test_ma_con_sot_tu_ban_mau_thi_KHONG_goi_la_trung_chuyen():
    """112 tệp cùng mã 'PT14012022' là mã còn sót trong bản mẫu, không phải 112 bản sao.

    Gọi đây là 'trùng chuyến, chọn một' là hướng người ta xoá 111 chuyến thật.
    """
    ds = [{"ma_tour": "PT14012022", "ten_tep": f"t{i}.xlsx", "tong_thu": 1000.0 * i,
           "van_tay_tep": f"bam{i}"} for i in range(12)]
    va = CT.trung_trong_lo(ds)
    assert len(va) == 1
    assert va[0]["kieu"] == "ma_tour_con_sot_tu_ban_mau"
    assert "gán lại mã tour thật" in va[0]["noi"]


def test_hai_tep_giong_het_nhau_thi_bao_la_mot_tep():
    ds = [{"ma_tour": "A1", "ten_tep": "x.xlsx", "van_tay_tep": "same", "tong_thu": 5.0},
          {"ma_tour": "A1", "ten_tep": "y.xlsx", "van_tay_tep": "same", "tong_thu": 5.0}]
    va = CT.trung_trong_lo(ds)
    assert any(x["kieu"] == "tep_giong_het" and x["muc"] == CT.NANG for x in va)


# ------------------------------------------------------------------ đối chiếu hệ thống

def test_chuyen_khong_co_trong_vtos_thi_chan(db):
    va = CT.doi_chieu_he_thong(db, {"ma_tour": "KHONG-CO"}, None)
    assert va and va[0]["muc"] == CT.NANG


def test_gia_von_tu_NGUON_KHAC_thi_phai_hoi_nguoi(db):
    """Đây là kiểu trùng nguy nhất – nó không tự lộ ra ở bất kỳ bảng nào."""
    t = _tour(db, "KC-001")
    db.add(TourCostLine(tour_id=t.id, line_no=1, description="Xe 45c",
                        actual=15_000_000, source="vietrip", status="hd"))
    db.commit()
    va = CT.doi_chieu_he_thong(db, {"ma_tour": "KC-001", "chi": []}, t.id)
    x = [v for v in va if v["kieu"] == "da_co_gia_von_nguon_khac"]
    assert x and x[0]["muc"] == CT.HOI
    assert "vietrip: 1 dòng" in x[0]["noi"]


def test_phan_cua_CHINH_MINH_thi_chi_la_NAP_LAI_khong_phai_va_cham(db):
    """Dòng do chính bộ nạp này ghi không được tính là 'dữ liệu đang có của nguồn khác'."""
    t = _tour(db, "KC-002")
    bk = db.scalars(select(Booking).where(Booking.tour_id == t.id)).first()
    db.add(TourCostLine(tour_id=t.id, line_no=1, description="Ăn trưa", actual=3_795_000,
                        source=CT.NGUON_CUA_TOI, status="hd"))
    db.add(BookingKhach(tour_id=t.id, booking_id=bk.id, ho_ten="A",
                        nguoi_sua=CT.NGUON_CUA_TOI))
    db.add(TourHdvChi(tour_id=t.id, noi_dung="Tháp Bà", thanh_tien=1_320_000,
                      nguoi_nhap=CT.NGUON_CUA_TOI))
    db.commit()
    va = CT.doi_chieu_he_thong(db, {"ma_tour": "KC-002", "chi": [{}],
                                    "khach": [{}], "hdv": {"dong": [{}]}}, t.id)
    assert not [v for v in va if v["muc"] in (CT.NANG, CT.HOI)], va
    assert any(v["kieu"] == "nap_lai" and v["muc"] == CT.NHE for v in va)


# ------------------------------------------------------------------ đối chiếu hai nguồn

def test_lech_voi_ban_da_chot_thi_HOI_chu_khong_chon_bua():
    d = {"tong_thu": 1_000_000.0, "tong_chi": 900_000.0, "chi": [], "thieu": []}
    va = CT.doi_chieu_ban_tong_hop(d, {"tong_thu": 1_000_000.0, "tong_chi": 900_000.0})
    assert va == []
    va = CT.doi_chieu_ban_tong_hop(d, {"tong_thu": 2_000_000.0, "tong_chi": 900_000.0})
    assert any(v["kieu"] == "lech_tong_thu" and v["muc"] == CT.HOI for v in va)


def test_khong_co_trong_ban_da_chot_thi_phai_co_nguoi_xac_nhan():
    va = CT.doi_chieu_ban_tong_hop({"tong_thu": 1.0, "tong_chi": 1.0}, None)
    assert va and va[0]["muc"] == CT.HOI


# ------------------------------------------------------------------ trùng trong chính tệp

def test_dong_chi_lap_thi_DANH_DAU_chu_khong_chan():
    """Tour thật có chi hai lần cùng một thứ. Chặn ở đây là chặn nhầm dữ liệu đúng."""
    d = {"chi": [{"noi_dung": "Ăn trưa", "doi_tac": "ĐỒNG TIẾN", "thanh_tien": 3_795_000.0, "_hang": 9},
                 {"noi_dung": "Ăn trưa", "doi_tac": "ĐỒNG TIẾN", "thanh_tien": 3_795_000.0, "_hang": 10},
                 {"noi_dung": "Bảo hiểm", "doi_tac": "", "thanh_tien": 210_000.0, "_hang": 11}]}
    va = CT.trung_trong_tep(d)
    assert len(va) == 1 and va[0]["muc"] == CT.NHE
    assert va[0]["hang"] == [9, 10]
