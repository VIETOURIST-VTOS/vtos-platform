"""Đóng số bù và gỡ phải làm THEO LÔ — và làm theo lô phải ra đúng kết quả như làm một lượt.

VÌ SAO CÓ TỆP NÀY

Đo 19/9/2026 trên hệ thật: gọi `/kho-cu/dong-so-bu/go` cho cả 476 chuyến thì cổng cắt giữa chừng
và trả về một trang HTML — trình duyệt chỉ thấy `Unexpected token '<'`. Giao dịch bị huỷ trọn nên
dữ liệu KHÔNG hỏng (kiểm lại: `se_go` vẫn 476, `da_go` vẫn 0), nhưng nút thì không bấm xong được,
và 2,63 tỷ giá vốn ảo vẫn nằm trên báo cáo.

Cửa đóng số nặng hơn cửa gỡ. Nó gọi `xem()` — một lần `ST.summary` mỗi chuyến — rồi trong vòng lặp
gọi lại `_soat_mot` (lần hai) và `ST.summary` (lần ba). BA lần chiết tính cho cùng một chuyến, tức
1.428 lần cho 476 chuyến, để ra đúng những con số đã có sẵn từ lần đầu.

Hai việc ở đây: chia lô, và thôi tính ba lần.

PHÉP THỬ QUAN TRỌNG NHẤT là `test_lam_theo_lo_ra_dung_ket_qua_nhu_lam_mot_luot`. Chia lô mà ra số
khác là tệ hơn không chia: nó hỏng ở chỗ không ai nghĩ để nhìn.
"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_dong_lo.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dong_lo.db"):
    os.remove("test_dong_lo.db")

import pytest                                                      # noqa: E402
from app.db.session import SessionLocal, Base, engine              # noqa: E402
import app.models                                                  # noqa: E402,F401
from app.models.core import Booking, Tour, User                    # noqa: E402
from app.models.lop3_tour import BookingKhach                      # noqa: E402
from app.models.vietrip import TourCostLine                        # noqa: E402
from app.services import dong_so_kho_cu as DS                      # noqa: E402

Base.metadata.create_all(engine)
SO_CHUYEN = 12


@pytest.fixture()
def db():
    s = SessionLocal()
    for M in (TourCostLine, BookingKhach, Booking, Tour):
        s.query(M).delete()
    s.commit()
    u = s.query(User).first()
    if u is None:
        u = User(username="dh_lo", full_name="ĐH", role="nv_dh", password_hash="x")
        s.add(u); s.flush()
    hom_qua = date.today() - timedelta(days=20)
    for i in range(SO_CHUYEN):
        t = Tour(code=f"LO-{i:03d}", name="CHUYẾN LÔ", tour_type="package",
                 operator_id=u.id, start_date=hom_qua, end_date=hom_qua + timedelta(days=2),
                 planned_pax=2, status="ket_thuc", confirmed_by=DS.NGUON)
        s.add(t); s.flush()
        # Doanh thu chuyến đọc từ `bookings.amount` (xem `settlement.summary`), không đọc từ
        # `gia_ban` của dòng khách — nên phiếu đặt phải mang số tiền, nếu không `xem()` xếp chuyến
        # vào rổ "doanh thu bằng 0" và không đóng được.
        s.add(Booking(code=f"BK-LO-{i:03d}", tour_id=t.id, request_id=0, sales_id=u.id,
                      created_by=u.id, customer_name="ĐOÀN", customer_phone="0900000000",
                      source=DS.NGUON, amount=1_000_000))
        s.add(TourCostLine(tour_id=t.id, line_no=1, description="XE", actual=400_000,
                           source=DS.NGUON, status="hd", updated_by=DS.NGUON))
    s.commit()
    yield s
    s.rollback(); s.close()


def _con_chua_dong(db):
    return db.query(Tour).filter(Tour.confirmed_by == DS.NGUON,
                                 Tour.closed_at.is_(None)).count()


# ------------------------------------------------------------------ chia lô

def test_mot_lo_chi_dong_dung_so_chuyen_cua_lo(db):
    kq = DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5); db.commit()
    assert kq["da_dong"] == 5
    assert kq["con_lai"] == SO_CHUYEN - 5
    assert _con_chua_dong(db) == SO_CHUYEN - 5


def test_goi_tiep_cho_toi_khi_con_lai_bang_khong(db):
    vong, tong = 0, 0
    while True:
        kq = DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5); db.commit()
        tong += kq["da_dong"]; vong += 1
        if kq["con_lai"] == 0 or vong > 10:
            break
    assert tong == SO_CHUYEN and _con_chua_dong(db) == 0
    assert vong == 3                      # 5 + 5 + 2


def test_lam_theo_lo_ra_dung_ket_qua_nhu_lam_mot_luot(db):
    """Phép thử chính. Chia lô mà ra số khác thì tệ hơn không chia."""
    while DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5)["con_lai"]:
        db.commit()
    db.commit()
    theo_lo = {t.code: (t.actual_revenue, t.actual_cost, t.closed_at, t.status)
               for t in db.query(Tour).filter(Tour.confirmed_by == DS.NGUON)}

    while DS.go(db, boi="chutich", xac_nhan=True, gioi_han=5)["con_lai"]:
        db.commit()
    db.commit()
    assert _con_chua_dong(db) == SO_CHUYEN

    DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=0)      # 0 = không chia lô
    db.commit()
    mot_luot = {t.code: (t.actual_revenue, t.actual_cost, t.closed_at, t.status)
                for t in db.query(Tour).filter(Tour.confirmed_by == DS.NGUON)}
    assert theo_lo == mot_luot


def test_go_cung_chia_lo(db):
    DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=0); db.commit()
    kq = DS.go(db, boi="chutich", xac_nhan=True, gioi_han=5); db.commit()
    assert kq["da_go"] == 5 and kq["con_lai"] == SO_CHUYEN - 5


def test_dung_giua_chung_thi_phan_da_lam_van_sach(db):
    DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5); db.commit()
    xong = db.query(Tour).filter(Tour.confirmed_by == DS.NGUON,
                                 Tour.closed_at.is_not(None)).all()
    assert len(xong) == 5
    for t in xong:                       # mỗi chuyến đã đóng phải đóng ĐỦ, không nửa vời
        assert t.status == DS.SAU_DONG
        assert t.closed_at == DS.moc_ky(t)
        assert t.actual_revenue and t.actual_cost


def test_xem_noi_ro_con_bao_nhieu_chua_xet(db):
    k = DS.xem(db, gioi_han=5)
    assert k["ung_vien"] == 5 and k["con_lai"] == SO_CHUYEN - 5


def test_khong_chia_lo_thi_lam_het(db):
    k = DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=0); db.commit()
    assert k["da_dong"] == SO_CHUYEN and k["con_lai"] == 0


# ------------------------------------------------------------------ thôi tính ba lần

def test_khong_chiet_tinh_lai_cho_moi_chuyen(db, monkeypatch):
    """Mỗi chuyến chỉ được gọi `ST.summary` MỘT lần trong một lần đóng số.

    Bản trước gọi ba lần: một ở `xem()`, một ở `_soat_mot` trong vòng lặp, một ở chính vòng lặp.
    Với 476 chuyến là 1.428 lần chiết tính — đủ để cổng cắt giữa chừng.
    """
    from app.services import settlement as ST
    dem = {"n": 0}
    that = ST.summary

    def dem_summary(db_, t):
        dem["n"] += 1
        return that(db_, t)

    monkeypatch.setattr(ST, "summary", dem_summary)
    DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=0)
    db.commit()
    assert dem["n"] == SO_CHUYEN, f"gọi {dem['n']} lần cho {SO_CHUYEN} chuyến"


# ------------------------------------------------------- con trỏ: chuyến Ở LẠI không làm kẹt vòng

def _bo_dong_chi(db, so_chuyen: int):
    """Làm cho `so_chuyen` chuyến ID NHỎ NHẤT không đóng được (mất hết dòng chi phí).

    Chọn id nhỏ nhất là có chủ ý: lô sắp theo `id`, nên chúng luôn đứng ĐẦU hàng — đúng chỗ tệ
    nhất, và đúng chỗ bản không có con trỏ sẽ kẹt.
    """
    ids = [t.id for t in db.query(Tour).filter(Tour.confirmed_by == DS.NGUON)
           .order_by(Tour.id).limit(so_chuyen)]
    db.query(TourCostLine).filter(TourCostLine.tour_id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return ids


def test_chuyen_khong_dong_duoc_o_dau_hang_khong_lam_ket_vong_lap(db):
    """3 chuyến đầu hàng không đóng được, lô 5 chuyến: vòng lặp PHẢI đi tới cuối.

    Không có con trỏ `bo_qua`, mỗi lần gọi lấy lại đúng 3 chuyến hỏng ấy cộng 2 chuyến mới, và khi
    chỉ còn chúng thì `da_dong` = 0 mà `con_lai` vẫn 3 — màn hình quay vòng không bao giờ dừng.
    """
    ket = _bo_dong_chi(db, 3)
    bo_qua, tong, vong = 0, 0, 0
    while vong < 10:
        kq = DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5, bo_qua=bo_qua)
        db.commit()
        tong += kq["da_dong"]
        bo_qua = kq["bo_qua_tiep"]
        vong += 1
        if kq["con_lai"] == 0:
            break
    assert kq["con_lai"] == 0, f"vòng lặp không dừng sau {vong} lần gọi"
    assert tong == SO_CHUYEN - 3
    assert bo_qua == 3                      # đúng 3 chuyến hỏng nằm lại dưới con trỏ
    con = db.query(Tour).filter(Tour.confirmed_by == DS.NGUON,
                                Tour.closed_at.is_(None)).all()
    assert {t.id for t in con} == set(ket)


def test_go_khong_ket_o_chuyen_dong_that(db):
    """Cửa gỡ: 3 chuyến Điều hành đã đóng THẬT đứng đầu hàng cũng không được làm kẹt vòng lặp.

    Đo 17/9/2026 trên hệ thật có 82 chuyến như thế — nhiều hơn một lô 50, nên đây không phải tình
    huống nghĩ ra: không có con trỏ thì lô đầu tiên đã kẹt và không bao giờ gỡ được chuyến nào.
    """
    DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=0); db.commit()
    that = [t.id for t in db.query(Tour).filter(Tour.confirmed_by == DS.NGUON)
            .order_by(Tour.id).limit(3)]
    for t in db.query(Tour).filter(Tour.id.in_(that)):
        t.closed_at = datetime.now()        # cửa THẬT: có micro-giây, không trúng moc_ky()
    db.commit()

    bo_qua, tong, vong = 0, 0, 0
    while vong < 10:
        kq = DS.go(db, boi="chutich", xac_nhan=True, gioi_han=5, bo_qua=bo_qua)
        db.commit()
        tong += kq["da_go"]
        bo_qua = kq["bo_qua_tiep"]
        vong += 1
        if kq["con_lai"] == 0:
            break
    assert kq["con_lai"] == 0, f"vòng lặp không dừng sau {vong} lần gọi"
    assert tong == SO_CHUYEN - 3
    assert bo_qua == 3
    for t in db.query(Tour).filter(Tour.id.in_(that)):
        assert t.status == DS.SAU_DONG and t.closed_at is not None   # không bị gỡ nhầm


def test_xem_cung_di_het_bang_con_tro(db):
    _bo_dong_chi(db, 3)
    bo_qua, thay, vong = 0, 0, 0
    while vong < 10:
        k = DS.xem(db, gioi_han=5, bo_qua=bo_qua)
        thay += k["ung_vien"]; bo_qua = k["bo_qua_tiep"]; vong += 1
        if k["con_lai"] == 0:
            break
    assert thay == SO_CHUYEN and bo_qua == SO_CHUYEN


# ------------------------------------------------------------------ thứ tự lô phải cố định

def test_cau_lay_lo_phai_sap_thu_tu():
    """`order_by(Tour.id)` là nền của cả việc chia lô — không có nó, `bo_qua` vô nghĩa.

    Phép thử này soi CÂU HỎI chứ không soi kết quả, và đó là chủ ý: SQLite (dùng khi chạy thử) quét
    bảng theo rowid nên vẫn ra đúng thứ tự dù thiếu `order_by` — tức là bỏ `order_by` đi thì mọi
    phép thử hành vi vẫn xanh, còn Postgres (hệ thật) thì đổi thứ tự sau mỗi lần UPDATE và lô sẽ
    lặp hoặc bỏ sót chuyến. Chỗ duy nhất bắt được sai sót ấy trên máy chạy thử là ở đây.
    """
    for cau in (DS._cau_ung_vien(5, 10), DS._cau_da_dong(5, 10)):
        sql = str(cau.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY" in sql.upper(), sql
        assert "LIMIT" in sql.upper() and "OFFSET" in sql.upper(), sql


def test_khong_chia_lo_thi_khong_gioi_han_va_khong_bo_qua():
    sql = str(DS._cau_ung_vien(0, 0).compile(compile_kwargs={"literal_binds": True})).upper()
    assert "LIMIT" not in sql and "OFFSET" not in sql


# ------------------------------------------------------------------ không rò việc bên trong

def test_ket_qua_tra_ra_khong_mang_theo_khoi_chiet_tinh(db):
    """`_sm` là việc bên trong, không được lọt ra câu trả lời của cửa.

    Nó được giữ lại để `chay()` khỏi chiết tính lần hai — nhưng một lô 50 chuyến mà mỗi chuyến
    gánh thêm một khối chiết tính thì câu trả lời phình ra vô ích, và một trường gạch dưới đã lọt
    ra ngoài thì sớm muộn có màn hình đọc nó.
    """
    for kq in (DS.xem(db, gioi_han=5),
               DS.chay(db, boi="chutich", xac_nhan=False, gioi_han=5),
               DS.chay(db, boi="chutich", xac_nhan=True, gioi_han=5)):
        assert kq["chi_tiet"], "phải có dòng để phép thử này có nghĩa"
        for h in kq["chi_tiet"]:
            assert "_sm" not in h, h.keys()
    db.rollback()
