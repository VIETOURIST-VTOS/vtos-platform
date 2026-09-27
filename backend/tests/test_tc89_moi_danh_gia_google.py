"""TC-89 · MỜI KHÁCH 4–5 SAO VIẾT ĐÁNH GIÁ GOOGLE — bước 3 của đề xuất CSKH 25/9/2026.

Đề xuất viết: "Khách 4–5 sao: tự gửi link đánh giá Google Maps kèm ưu đãi lần sau."

HAI ĐIỀU KIỆN, VÀ CHÚNG KHÔNG PHẢI ĐỂ LỌC LẤY ĐIỂM ĐẸP:

  · Chỉ mời người đã chấm 4–5 sao. Mời một khách vừa chấm 2 sao đi viết đánh giá công khai là mời
    họ viết đúng điều họ vừa nói, ở chỗ ta không sửa được. Việc của khách chấm thấp là được gọi
    lại trong 24 giờ, không phải được đưa thêm một cái micro.
  · Chỉ mời SAU KHI họ đã chấm xong trong sổ của mình. Đổi thứ tự thì ta có đánh giá ngoài Google
    mà không có dữ liệu trong sổ để đối chiếu.

KHÔNG GỬI TIN THỨ HAI QUA ZALO cho việc này. Khách vừa bấm gửi đang ở trên trang khảo sát — hiện
lời mời ngay tại đó là chỗ duy nhất họ còn đang chú ý, và không tốn thêm một phí tin nào.

LINK LÀ THAM SỐ. Hồ sơ Google của công ty đổi được; một đường dẫn viết cứng trong mã thì ba tháng
sau chết mà không ai biết. Để trống tham số là cách TẮT bước này mà không phải sửa mã — phép thử
canh luôn cả đường tắt ấy, vì một công tắc không ai thử là một công tắc không chắc còn chạy.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour, User
from app.models.cskh import CareTicket
from app.services import danh_gia as DG
from app.services import rules as R


@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _phieu(db, ma="BK1"):
    u = User(username="nv.a", full_name="NV A", role="nv_kd", password_hash="x")
    db.add(u); db.commit()
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia",
             start_date=dt.date.today() - dt.timedelta(days=5),
             end_date=dt.date.today() - dt.timedelta(days=1), operator_id=u.id, status="ket_thuc")
    db.add(t); db.commit()
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="Khach", customer_phone="0900000001", source="truc_tiep",
                pax=1, amount=1_000_000, sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    c = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Khach",
                   customer_phone="0900000001", owner_id=u.id, han_lien_he=dt.date.today())
    db.add(c); db.commit()
    return c


def _gui(db, care, diem):
    m = DG.sinh_ma(db, care)
    return DG.ghi_danh_gia(db, m.ma, {
        "diem": [{"doi_tuong": "tour", "diem": diem, "nhan_xet": ""}],
        "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "co", "gop_y": ""})


def test_tc89_1_khach_5_sao_duoc_moi(db):
    ra = _gui(db, _phieu(db), 5)
    assert ra.get("link_danh_gia_google"), "khach hai long ma khong duoc moi thi bo mat buoc 3"
    assert "google.com/maps" in ra["link_danh_gia_google"]
    assert ra.get("loi_moi_danh_gia")


def test_tc89_2_khach_2_sao_KHONG_duoc_moi(db):
    ra = _gui(db, _phieu(db), 2)
    assert "link_danh_gia_google" not in ra, \
        "moi mot khach vua cham 2 sao di viet danh gia cong khai la moi ho noi lai dieu do o cho ta khong sua duoc"


def test_tc89_3_khach_4_sao_duoc_moi_vi_4_la_hai_long(db):
    assert _gui(db, _phieu(db), 4).get("link_danh_gia_google")


def test_tc89_4_de_trong_tham_so_la_tat_buoc_nay(db):
    """Công tắc tắt. Một công tắc không ai thử là một công tắc không chắc còn chạy."""
    from app.models.core import Param
    db.add(Param(key="link_danh_gia_google", value="", label="Link Google",
                 effective_from=dt.date.today() - dt.timedelta(days=1), status="active"))
    db.commit()

    ra = _gui(db, _phieu(db), 5)
    assert "link_danh_gia_google" not in ra, "de trong tham so phai TAT duoc buoc nay ma khong sua ma"
    assert ra.get("loi_cam_on"), "tat loi moi thi van phai cam on khach"


def test_tc89_5_link_khong_viet_cung_trong_ma(db):
    ma_nguon = open(DG.__file__, encoding="utf-8").read()
    assert "google.com/maps" not in ma_nguon, "duong dan phai nam o tham so, khong nam trong ma"
