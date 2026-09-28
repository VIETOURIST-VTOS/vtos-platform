"""TC-95 · MÃ KHẢO SÁT KHÔNG ĐƯỢC CHẾT TRONG HÀNG ĐỢI — 29/9/2026.

ĐO ĐƯỢC TRÊN MÁY CHỦ THẬT, không suy đoán. Bảng chỉ tiêu toàn công ty sáng 29/9 ghi:

    Tin Zalo đang kẹt chờ cấu hình ....... 401 tin ... phải xử lý
    Khách trả lời khảo sát sau tour ...... chưa có số
    Chuyến kết thúc không ai chấm điểm ... 231 chuyến

Hôm trước con số ấy là 200. Robot vẫn xếp thêm mỗi ngày, và chưa một tin nào tới khách: khách chưa
quan tâm OA nên không có `zalo_uid`, còn ZNS thì chưa có mẫu được Zalo duyệt.

HAI CHỖ HỎNG, và cả hai đều chỉ lộ ra khi nhìn theo thời gian:

 1. MÃ CHẾT TRONG HÀNG ĐỢI. Mỗi lời mời đeo một mã khảo sát hạn 14 ngày, sinh ra tại lúc XẾP chứ
    không phải lúc GỬI. Tin nằm chờ quá 14 ngày thì mã chết. Gửi nó đi lúc ấy còn tệ hơn không
    gửi: khách bị làm phiền, mở ra chỉ thấy "liên kết không đúng hoặc đã hết hiệu lực", mà bảng số
    vẫn ghi "đã gửi" nên tỷ lệ trả lời bị chia cho một tin không ai trả lời được.

 2. MẤT KHÁCH VĨNH VIỄN. `ma_khao_sat.care_id` là khoá DUY NHẤT — một phiếu một mã, đời đời. Luật
    cũ "phiếu đã có mã thì bỏ qua" nghĩa là 401 khách ấy không bao giờ được mời lại, kể cả sau khi
    mẫu ZNS đã duyệt xong. Hệ thống bỏ rơi họ trong im lặng, không dòng nào trên màn hình nói ra.

Bộ kiểm này canh ba luật, và luật thứ ba là luật dễ mất nhất khi ai đó "dọn dẹp" về sau.
"""
import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.models.cskh import CareTicket
from app.models.crm import ZaloMessage
from app.models.danh_gia import MaKhaoSat
from app.services import cskh as CS
from app.services import danh_gia as DG
from app.services import rules as R
from app.services import zalo as Z

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvdh", "nv_dh")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    R.seed_params(s)
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _chuyen(db):
    t = Tour(code="L1", name="Đà Lạt 3N2Đ", tour_type="le_noi_dia",
             start_date=HOM_NAY - dt.timedelta(days=5), end_date=HOM_NAY - dt.timedelta(days=2),
             operator_id=_u(db, "nvdh").id, status="ket_thuc", price_per_pax=5_000_000,
             fixed_cost=20_000_000, var_cost_per_pax=2_000_000, planned_pax=20, seats_open=20)
    db.add(t); db.commit(); return t


def _phieu(db, t, sdt="0900000001", ma_bk="BK1"):
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="Khách A",
                       customer_phone=sdt, source="web", pax=1)
    db.add(r); db.flush()
    b = Booking(code=ma_bk, tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                created_by=_u(db, "nvdh").id, customer_name="Khách A", customer_phone=sdt,
                source="web", pax=1, amount=5_000_000)
    db.add(b); db.flush()
    c = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Khách A", customer_phone=sdt,
                   owner_id=_u(db, "nvkd").id, han_lien_he=HOM_NAY + dt.timedelta(days=3))
    db.add(c); db.commit(); return c


def _ma(db) -> MaKhaoSat:
    return db.execute(select(MaKhaoSat)).scalars().first()


def _het_han(db, m, ngay=1):
    m.het_han = dt.datetime.now() - dt.timedelta(days=ngay)
    db.commit()


# ═════════════ LUẬT 1 · KHÔNG GỬI MỘT ĐƯỜNG DẪN ĐÃ CHẾT ═════════════
def test_tin_mang_ma_da_het_han_thi_KHONG_gui_di():
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    z = db.execute(select(ZaloMessage)).scalars().first()
    assert z is not None
    z.gui_tu_luc = None; db.commit()          # gỡ giờ hẹn để tin tới lượt gửi
    _het_han(db, _ma(db))

    r = Z.send_pending(db)
    assert r["sent"] == 0, "đã gửi một tin mà đường dẫn trong đó mở ra chỉ để báo lỗi"
    assert r["het_han"] == 1
    z = db.execute(select(ZaloMessage)).scalars().first()
    assert z.status == "het_han"
    assert "hết hạn" in (z.response or "")


def test_ma_KHONG_CON_TON_TAI_cung_la_duong_dan_chet():
    """Không phải tình huống lý thuyết: `sinh_ma` cấp lại mã cho phiếu có mã cũ đã chết, và lúc ấy
    chuỗi mã cũ nằm trong tin đang xếp hàng không còn trỏ vào đâu nữa."""
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    z = db.execute(select(ZaloMessage)).scalars().first()
    z.gui_tu_luc = None
    z.params = dict(z.params or {}, ma_khao_sat="ma-khong-co-that")
    db.commit()

    r = Z.send_pending(db)
    assert r["sent"] == 0 and r["het_han"] == 1


def test_tin_KHONG_phai_cham_soc_thi_khong_bi_dong_nham():
    """Luật này chỉ nói về tin chăm sóc. Chặn nhầm một tin nhắc cọc là làm mất tiền của công ty."""
    db = _db()
    Z.queue(db, "thu", phone="0900000009", purpose="nhac_coc", text="x", send_now=False)
    z = db.execute(select(ZaloMessage)).scalars().first()
    assert not Z._ma_khao_sat_da_het_han(db, z)


# ═════════════ LUẬT 2 · MÃ CHẾT CHƯA AI CHẠM THÌ ĐƯỢC CẤP LẠI ═════════════
def test_ma_het_han_chua_ai_cham_thi_duoc_cap_lai_va_phieu_duoc_moi_lai():
    db = _db(); c = _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    cu = _ma(db)
    ma_cu, id_cu = cu.ma, cu.id
    _het_han(db, cu)

    n = CS.gui_loi_moi_cham_diem(db)
    assert n == 1, "phiếu có mã đã chết mà vẫn bị coi là 'đã mời' — khách này mất vĩnh viễn"
    moi = _ma(db)
    assert moi.id == id_cu, "cấp lại phải sửa đúng dòng cũ – care_id là khoá duy nhất"
    assert moi.ma != ma_cu, "mã mới phải khác mã cũ"
    assert moi.het_han > dt.datetime.now(), "mã mới phải còn hạn"
    assert db.execute(select(MaKhaoSat).where(MaKhaoSat.care_id == c.id)).scalars().all().__len__() == 1


def test_ma_CON_SONG_thi_KHONG_cap_lai_va_khong_moi_lai():
    """Hai mã sống cùng lúc cho một phiếu nghĩa là khách chấm được hai lần."""
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    ma_cu = _ma(db).ma
    assert CS.gui_loi_moi_cham_diem(db) == 0
    assert _ma(db).ma == ma_cu


def test_khach_DA_CHAM_roi_thi_khong_bao_gio_moi_lai():
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    m = _ma(db); m.dung_luc = dt.datetime.now(); db.commit()
    _het_han(db, m)
    assert CS.gui_loi_moi_cham_diem(db) == 0, "hỏi lại người đã trả lời là làm phiền"
    assert _ma(db).ma == m.ma


def test_khach_DA_MO_ma_khong_cham_thi_cung_khong_duoi_theo():
    """Khách đã mở mà không chấm là một câu trả lời, dù không thành lời."""
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    m = _ma(db); m.so_lan_mo = 1; db.commit()
    _het_han(db, m)
    assert CS.gui_loi_moi_cham_diem(db) == 0
    assert _ma(db).ma == m.ma


# ═════════════ LUẬT 3 · TIN MANG THEO ĐƯỜNG DẪN ĐẦY ĐỦ ═════════════
def test_tin_gui_kem_ca_ma_VA_duong_dan_day_du():
    """Mẫu ZNS nào không gắn được tham số vào đường dẫn của nút thì dùng thẳng khoá `link`."""
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    p = db.execute(select(ZaloMessage)).scalars().first().params
    assert p["ma_khao_sat"]
    assert p["link"].endswith("/y-kien/" + p["ma_khao_sat"])
    assert p["link"].startswith("http")


# ═════════════ HÀNG RÀO TỰ KIỂM ═════════════
def test_phep_thu_nay_that_su_no():
    """Dựng lại đúng cảnh cũ: mã còn hạn thì tin PHẢI đi được. Nếu cảnh này cũng bị chặn thì luật
    trên đang chặn nhầm mọi thứ, và ba phép thử đầu xanh vì một lý do sai."""
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    z = db.execute(select(ZaloMessage)).scalars().first()
    z.gui_tu_luc = None; db.commit()
    assert _ma(db).het_han > dt.datetime.now()
    assert not Z._ma_khao_sat_da_het_han(db, z), "mã còn hạn mà bị coi là chết"
