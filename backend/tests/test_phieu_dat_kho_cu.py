# -*- coding: utf-8 -*-
"""PHIẾU ĐẶT THEO NGƯỜI BÁN cho kho quyết toán cũ.

VÌ SAO KHỐI NÀY TỒN TẠI

Chủ tịch hỏi ngày 13/9/2026: "đẩy số lên quyết toán thì nó có chạy về các phòng ban không — doanh thu
cho sales đoàn, sales lẻ, báo cáo cho TP, GĐ, CT?". Rà ra thì KHÔNG, và lý do nằm gọn một chỗ: cửa
tạo chuyến sinh chuyến mà không sinh phiếu đặt, `booking_khach.booking_id` lại bắt buộc — nên toàn bộ
dòng khách của mọi chuyến mới bị bỏ lặng lẽ. Chỉ chi phí vào được.

Hậu quả không dừng ở "thiếu doanh thu". Bảng lãi lỗ thấy giá vốn mà không thấy doanh thu thì mỗi
chuyến thành một khoản LỖ bằng đúng chi phí, và số ấy cộng vào lãi gộp toàn công ty. Nạp 604 tệp kiểu
ấy là tự tay dựng một con số lỗ mấy chục tỷ không có thật.

  PD1  mỗi NGƯỜI BÁN một phiếu — chuyến ghép có khách của bốn người thì ra bốn phiếu
  PD2  doanh thu từng phiếu bằng đúng tổng của khách người ấy bán
  PD3  dòng khách treo vào ĐÚNG phiếu của người đã bán ra khách ấy
  PD4  tên chưa khớp được tài khoản: VẪN có phiếu, VẪN có doanh thu, nhưng KHÔNG vào chỉ tiêu ai
  PD5  tên người bán như trong tệp được GIỮ trên phiếu chưa gán — không giữ thì gán xong mất dấu
  PD6  nạp lại thì THAY, không nhân đôi
  PD7  nạp lại khi tệp không còn khách thì phiếu cũ phải biến mất theo
  PD8  gán tên xong, `gan_lai` chuyển phiếu về đúng người — mặc định chỉ xem trước
  PD9  mất tài khoản hệ thống thì rơi về ĐIỀU HÀNH CỦA CHUYẾN, cửa nạp vẫn chạy
  PD9b không còn chỗ đỗ nào thì KHÔNG dựng phiếu nào cả, kể cả phiếu đã khớp
  PD10 doanh thu lấy `tong_thu` (số chốt của dòng), không cộng chồng `gia_ban`
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_phieudat.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_phieudat.db", "test_phieudat.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from datetime import date                                            # noqa: E402

import pytest                                                        # noqa: E402

from app.core.security import hash_password                          # noqa: E402
from app.db.session import Base, SessionLocal, engine                 # noqa: E402
import app.models                                                     # noqa: E402,F401
from app.models.core import Booking, Tour, User                       # noqa: E402
from app.models.kho_cu import KhoCuNguoiBan                           # noqa: E402
from app.models.lop3_tour import BookingKhach                         # noqa: E402
from app.services import intake_tao_chuyen as TCN                     # noqa: E402
from app.services import khop_nguoi_ban as KN                         # noqa: E402
from app.services import phieu_dat_kho_cu as PD                       # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(BookingKhach).delete()
    s.query(Booking).delete()
    s.query(KhoCuNguoiBan).delete()
    s.query(Tour).delete()
    s.query(User).delete()
    # Tài khoản điều hành khoá – chỗ đỗ của dòng chưa gán được người bán.
    s.add(User(username=TCN.TAI_KHOAN_MAC_DINH, full_name="Điều hành Vietrip", role="nv_dh",
               password_hash=hash_password("x"), active=False))
    for u, ten in (("vananh", "Nguyễn Ngọc Vân Anh"), ("uyennhi", "Lê Thị Uyển Nhi")):
        s.add(User(username=u, full_name=ten, role="nv_kd", department="kd_le",
                   password_hash=hash_password("x"), active=True))
    s.flush()
    dh = s.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).one()
    s.add(Tour(code="NT001.03050126", name="NHA TRANG", tour_type="ghep",
               start_date=date(2026, 1, 5), end_date=date(2026, 1, 7),
               operator_id=dh.id, status="ket_thuc",
               confirmed_by=TCN.NGUON, approved_by=TCN.NGUON))
    s.commit()
    yield s
    s.close()


def _uid(db, u):
    return db.query(User).filter(User.username == u).one().id


def _tour(db):
    return db.query(Tour).filter(Tour.code == "NT001.03050126").one()


def _khach(sale, ten, tien):
    return {"ho_ten": ten, "sale": sale, "gia_ban": tien, "tong_thu": tien, "ma_dat_cho": ""}


# Một chuyến ghép thật: ba người bán, trong đó "MAI VIGO" là đầu mối ngoài, không có tài khoản.
LO = [
    _khach("NGUYỄN NGỌC VÂN ANH", "LÂM VIỆT HÙNG", 10_000_000),
    _khach("NGUYỄN NGỌC VÂN ANH", "TRẦN THỊ THU YẾN", 12_000_000),
    _khach("UYỂN NHI", "GIÁP TRUNG ĐÔNG", 9_000_000),
    _khach("MAI VIGO", "HUỲNH CÔNG TÂM", 8_000_000),
    _khach("", "LƯU KIỀU LIÊN", 7_000_000),        # tệp không ghi tên người bán
]


def _sinh(db, khach=None):
    KN.ghi_so(db, PD.dem_nguoi_ban([{"khach": khach if khach is not None else LO}]))
    kq = PD.sinh(db, _tour(db).id, khach if khach is not None else LO, boi="thu")
    db.commit()
    return kq


def test_pd1_moi_nguoi_ban_mot_phieu(db):
    """Cột SALES nằm ở TỪNG DÒNG KHÁCH, không ở đầu tệp. Gộp cả chuyến vào một phiếu là phải chọn
    một người để ghi tên – tức là gán doanh số của ba người cho một người."""
    kq = _sinh(db)
    assert kq["so_phieu"] == 4, "ba người bán + một nhóm không ghi tên phải ra bốn phiếu"
    ds = db.query(Booking).filter(Booking.tour_id == _tour(db).id).all()
    assert {b.sales_id for b in ds} == {
        _uid(db, "vananh"), _uid(db, "uyennhi"), _uid(db, TCN.TAI_KHOAN_MAC_DINH)}


def test_pd2_doanh_thu_tung_phieu_dung_phan_nguoi_ay_ban(db):
    _sinh(db)
    ds = {b.sales_id: b for b in db.query(Booking).all()}
    assert float(ds[_uid(db, "vananh")].amount) == 22_000_000, "hai khách của chị Vân Anh phải cộng lại"
    assert ds[_uid(db, "vananh")].pax == 2
    assert float(ds[_uid(db, "uyennhi")].amount) == 9_000_000
    tong = sum(float(b.amount or 0) for b in db.query(Booking).all())
    assert tong == 46_000_000, "tổng doanh thu chuyến không khớp – có khách rơi hoặc cộng hai lần"


def test_pd3_dong_khach_treo_vao_DUNG_phieu(db):
    """Đây là chỗ hỏng gốc: trước 13/9 toàn bộ dòng khách rơi vì chuyến không có phiếu nào."""
    from app.services import intake_kho_cu as IK

    kq = _sinh(db)
    for i, x in enumerate(LO, 1):
        db.add(BookingKhach(tour_id=_tour(db).id, booking_id=kq["theo_ten_nguoi_ban"][x["sale"]],
                            stt=i, ho_ten=x["ho_ten"], gia_ban=x["gia_ban"], nguoi_sua=IK.NGUON))
    db.commit()

    ds = {b.sales_id: b for b in db.query(Booking).all()}
    kh = db.query(BookingKhach).filter(
        BookingKhach.booking_id == ds[_uid(db, "vananh")].id).all()
    assert {k.ho_ten for k in kh} == {"LÂM VIỆT HÙNG", "TRẦN THỊ THU YẾN"}, \
        "khách bị treo sang phiếu của người bán khác – doanh số chạy nhầm người"
    assert db.query(BookingKhach).count() == 5, "có dòng khách không vào đâu cả"


def test_pd4_chua_gan_duoc_thi_van_co_doanh_thu_nhung_khong_vao_chi_tieu(db):
    """Chốt an toàn của cả khối. Bỏ dòng chưa gán là mất doanh thu thật của công ty; gán bừa cho ai
    đó là cộng nhầm chỉ tiêu và ra tiền thưởng. Cách đúng là giữ tiền, bỏ chỉ tiêu."""
    kq = _sinh(db)
    assert kq["chua_gan_dong"] == 2 and kq["chua_gan_tien"] == 15_000_000

    do = db.query(Booking).filter(
        Booking.sales_id == _uid(db, TCN.TAI_KHOAN_MAC_DINH)).all()
    assert len(do) == 2
    assert all(b.counts_for_target is False for b in do), \
        "dòng chưa biết của ai mà vẫn vào chỉ tiêu – sẽ cộng doanh số cho một tài khoản hệ thống"
    assert all(b.counts_for_target for b in db.query(Booking).filter(
        Booking.sales_id.in_([_uid(db, "vananh"), _uid(db, "uyennhi")])).all()), \
        "người đã khớp mà không được tính chỉ tiêu thì nạp lô này chẳng để làm gì"


def test_pd5_giu_ten_nguoi_ban_nhu_trong_tep_tren_phieu_chua_gan(db):
    """Không giữ tên thô thì sau khi người gán xong, không gì trên hệ biết phiếu ấy đáng lẽ của ai –
    và cách duy nhất còn lại là đọc lại 604 tệp Excel."""
    _sinh(db)
    do = db.query(Booking).filter(
        Booking.sales_id == _uid(db, TCN.TAI_KHOAN_MAC_DINH)).all()
    ten = {PD.ten_trong_phieu(b) for b in do}
    assert "MAI VIGO" in ten, "mất tên người bán trên phiếu chưa gán – gán xong không lần lại được"
    assert "" in ten, "nhóm tệp không ghi tên phải phân biệt được với nhóm có tên mà chưa khớp"


def test_pd6_nap_lai_thi_THAY_khong_nhan_doi(db):
    _sinh(db)
    n1 = db.query(Booking).count()
    _sinh(db)
    assert db.query(Booking).count() == n1, "nạp lại đẻ thêm phiếu – doanh thu chuyến nhân đôi"


def test_pd7_nap_lai_khi_tep_khong_con_khach_thi_phieu_cu_phai_bien_mat(db):
    """Chỗ này `phieu_dat_kho_cu.sinh` KHÔNG với tới được, vì nó chỉ chạy khi có dòng khách. Nên
    việc xoá phải nằm ở `_xoa_phan_cua_nguon` của cửa nạp."""
    from app.services import intake_kho_cu as IK

    _sinh(db)
    assert db.query(Booking).count() > 0
    IK._xoa_phan_cua_nguon(db, _tour(db).id)
    db.commit()
    assert db.query(Booking).count() == 0, \
        "phiếu của lần nạp trước ở lại – chuyến mang doanh thu của một tệp không còn tồn tại"
    assert db.query(BookingKhach).count() == 0, "dòng khách mồ côi trỏ vào phiếu đã xoá"


def test_pd8_gan_ten_xong_thi_chuyen_phieu_ve_dung_nguoi(db):
    _sinh(db)
    db.add(User(username="maivigo", full_name="Mai Vi Go", role="nv_kd", department="kd_le",
                password_hash=hash_password("x"), active=True))
    db.commit()
    KN.gan_tay(db, KN.chuan("MAI VIGO"), _uid(db, "maivigo"), boi="tp_dh")
    db.commit()

    xem = PD.gan_lai(db, boi="tp_dh")
    assert len(xem["doi_duoc"]) == 1 and xem["da_doi"] == 0, "mặc định phải là xem trước"
    assert xem["tien_ve_nguoi_that"] == 8_000_000
    assert db.query(Booking).filter(Booking.sales_id == _uid(db, "maivigo")).count() == 0

    PD.gan_lai(db, boi="tp_dh", xac_nhan=True)
    db.commit()
    b = db.query(Booking).filter(Booking.sales_id == _uid(db, "maivigo")).one()
    assert b.counts_for_target is True, "chuyển về người thật mà vẫn không tính chỉ tiêu"
    assert float(b.amount) == 8_000_000
    # Nhóm tệp không ghi tên vẫn phải ở lại chỗ đỗ – không có tên thì không gán cho ai được.
    assert len(PD.gan_lai(db, boi="tp_dh")["con_treo"]) == 1


def test_pd9_khong_co_tai_khoan_he_thong_thi_roi_ve_DIEU_HANH_CUA_CHUYEN(db):
    """Cửa nạp phải chạy được trên chuyến đã có sẵn trong VTOS mà không đòi ai dựng trước một tài
    khoản hệ thống. Chuyến nào cũng có điều hành, nên đó là chỗ đỗ tự nhiên — và doanh thu đỗ ở đó
    vẫn không vào chỉ tiêu của ai."""
    dh = db.query(User).filter(User.username == "uyennhi").one()     # đóng vai điều hành chuyến
    t = _tour(db)
    t.operator_id = dh.id
    db.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).delete()
    db.commit()

    kq = _sinh(db)
    assert not kq.get("loi") and kq["so_phieu"] == 4, "mất tài khoản hệ thống là cả cửa nạp đứng"
    do = [b for b in db.query(Booking).all() if not b.counts_for_target]
    assert len(do) == 2 and all(b.sales_id == dh.id for b in do)


def test_pd9b_khong_con_cho_do_nao_thi_KHONG_dung_phieu_nao(db):
    """Dựng một nửa là chuyến có doanh thu thiếu, mà bảng nào cũng cân vì tổng nào cũng cộng từ dòng
    – không ai nhìn ra."""
    t = _tour(db)
    t.operator_id = 999_999                                   # điều hành trỏ vào tài khoản không có
    db.query(User).filter(User.username == TCN.TAI_KHOAN_MAC_DINH).delete()
    db.commit()
    kq = PD.sinh(db, t.id, LO, boi="thu")
    assert kq["loi"].startswith("chua-co-tai-khoan")
    assert db.query(Booking).count() == 0, "dựng được phiếu của người đã khớp rồi bỏ dở phần còn lại"


def test_pd10_doanh_thu_lay_tong_thu_khong_cong_chong_gia_ban(db):
    """`gia_ban` là cột ĐẦU của khối THU (giá tour thuần); `tong_thu` đã gồm cả phụ thu và phí lãnh
    sự. Cộng cả hai là tính doanh thu hai lần cho phần phụ thu."""
    kh = [{"ho_ten": "A", "sale": "NGUYỄN NGỌC VÂN ANH", "gia_ban": 10_000_000,
           "tong_thu": 13_500_000, "ma_dat_cho": ""}]
    _sinh(db, kh)
    b = db.query(Booking).one()
    assert float(b.amount) == 13_500_000, "doanh thu không phải số chốt của dòng khách"
