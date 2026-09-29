# -*- coding: utf-8 -*-
"""ĐỌC ID BOOKING CÒN THIẾU — hàm đã lên hệ thật mà CHƯA TỪNG có một phép thử nào.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Ngày 29/9/2026, cửa `POST /import/vietrip/nap-bu/booking-cho-phieu-thu` trả 503 mọi lần gọi.
Nhật ký Render nói đúng một dòng:

    AttributeError: 'int' object has no attribute 'vietrip_id'

`select(MỘT CỘT)` cộng `.scalars()` trả về CHÍNH giá trị cột chứ không trả hàng ORM, nên
`{b.vietrip_id for b in ...}` nổ ngay dòng đầu của hàm.

Điều đáng nói không phải cái lỗi — nó là lỗi một dòng. Điều đáng nói là VÌ SAO nó lọt:
`id_booking_con_thieu` được viết ngày 26/9, gộp vào hệ thật, và **không có lấy một phép thử nào
gọi tới nó**. Bộ phép thử của TC-65 soi rất kỹ vòng lật trang của `nap_booking_theo_id` — chín
chỗ phá mã đều làm đỏ — nhưng nó truyền `db=None`, nên cả nhánh đọc cơ sở dữ liệu nằm ngoài tầm.

Một hàm có phép thử ở hàng xóm không phải là một hàm có phép thử. Bất kỳ phép thử nào GỌI hàm này
cũng đã bắt được lỗi, vì nó nổ ở dòng đầu tiên — nên tệp này dựng một cơ sở dữ liệu thật và gọi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import datetime as dt                                           # noqa: E402
from sqlalchemy import create_engine                            # noqa: E402
from sqlalchemy.orm import sessionmaker                         # noqa: E402

from app.db.session import Base                                 # noqa: E402
from app.models.core import Booking, Company, Tour, User       # noqa: E402
from app.models.vietrip import VtRecord                         # noqa: E402
from app.services import vietrip as VT                          # noqa: E402


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _phieu(db, bid, status="KC", applied=False):
    db.add(VtRecord(entity="receipt", vietrip_id=f"R{bid}", ref=str(bid), applied=applied,
                    raw={"BookingID": bid, "Status": status, "amount": 1000}))


def _booking_da_co(db, bid):
    """Một booking VTOS ĐÃ CÓ.

    Booking treo vào chuyến, chuyến treo vào pháp nhân và người điều hành — nên phải dựng cả ba.
    Dài dòng, nhưng dựng bằng chính khuôn thật thì phép thử mới nói được điều gì về hệ thật.
    """
    c = db.query(Company).first()
    if c is None:
        c = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
        db.add(c); db.commit()
    u = db.query(User).first()
    if u is None:
        u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
        db.add(u); db.commit()
    t = Tour(code=f"T{bid}", name=f"Chuyen {bid}", company_id=c.id, tour_type="le_noi_dia",
             start_date=dt.date(2026, 3, 1), end_date=dt.date(2026, 3, 5), operator_id=u.id)
    db.add(t); db.commit()
    db.add(Booking(vietrip_id=bid, code=f"B{bid}", customer_name="KHACH", customer_phone="0900000000",
                   source="vietrip", pax=1, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id))


def test_tra_ve_id_cua_phieu_treo():
    """Phép thử tối thiểu — và chính nó đủ để bắt lỗi 29/9, vì hàm nổ ở dòng đầu."""
    db = _db()
    _phieu(db, 95241); _phieu(db, 127507)
    db.commit()
    assert sorted(VT.id_booking_con_thieu(db)) == [95241, 127507]


def test_bo_qua_booking_VTOS_DA_CO():
    """Đây là dòng đã nổ: tập id đã có phải là tập SỐ, không phải tập hàng ORM.

    Nếu ai đó viết lại thành `{b.vietrip_id for b in ...}` thì hàm nổ; nếu viết đúng kiểu nhưng so
    sánh nhầm (ví dụ để id dạng chuỗi) thì phép thử này đỏ vì trả về thừa một id.

    VÀ ĐÂY LÀ CÁI BẪY, đo được khi thử phá mã: trả lại đúng lỗi cũ thì SÁU phép thử kia vẫn XANH,
    chỉ mình phép thử này đỏ. Lý do là bảng booking của chúng rỗng, nên vòng lặp không chạy lần nào
    và lỗi không kịp nổ. Trên hệ thật bảng ấy có 12.697 dòng nên nổ ngay yêu cầu đầu tiên. Nghĩa
    là: một phép thử gọi hàm này mà KHÔNG dựng sẵn booking thì không canh được gì cả.
    """
    db = _db()
    _booking_da_co(db, 95241)
    _phieu(db, 95241); _phieu(db, 127507)
    db.commit()
    assert VT.id_booking_con_thieu(db) == [127507], "đã có booking rồi mà vẫn đi kéo lại"


def test_chi_lay_phieu_DA_XAC_NHAN():
    """Phiếu chưa xác nhận vốn bị `apply_receipts` bỏ qua — kéo booking cho chúng là kéo thừa."""
    db = _db()
    _phieu(db, 111, status="CHO"); _phieu(db, 222, status="KC")
    db.commit()
    assert VT.id_booking_con_thieu(db) == [222]


def test_khong_tra_trung_id():
    """Một booking thường có NHIỀU phiếu thu (đặt cọc, thanh toán nốt)."""
    db = _db()
    _phieu(db, 333); _phieu(db, 333); _phieu(db, 333)
    db.commit()
    assert VT.id_booking_con_thieu(db) == [333]


def test_phieu_khong_co_ma_booking_thi_bo_qua():
    db = _db()
    db.add(VtRecord(entity="receipt", vietrip_id="R0", applied=False,
                    raw={"Status": "KC", "amount": 500}))
    _phieu(db, 444)
    db.commit()
    assert VT.id_booking_con_thieu(db) == [444]


def test_ton_trong_gioi_han():
    db = _db()
    for i in range(10):
        _phieu(db, 700 + i)
    db.commit()
    assert len(VT.id_booking_con_thieu(db, gioi_han=3)) == 3


def test_khong_doc_phieu_DA_AP():
    """Phiếu đã ánh xạ xong thì không còn treo — đi kéo booking cho nó là việc thừa."""
    db = _db()
    _phieu(db, 555, applied=True); _phieu(db, 666)
    db.commit()
    assert VT.id_booking_con_thieu(db) == [666]
