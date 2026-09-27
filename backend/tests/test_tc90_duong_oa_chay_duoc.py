"""TC-90 · ROBOT CHĂM SÓC KHÔNG BAO GIỜ DÙNG ĐƯỜNG OA — nên không chạy thử được.

Đo ngày 27/9/2026: token Zalo OA còn sống, nhưng 200 lời mời chấm điểm đều là kênh `zns` và đều
kẹt chờ mẫu duyệt. Đọc mã ra lý do, và nó nằm ở một chỗ rất nhỏ:

    `zalo.queue` chọn kênh bằng đúng một dòng — `kind = "oa" if zalo_uid else "zns"`.

Robot chăm sóc gọi `queue` mà KHÔNG truyền `zalo_uid` và KHÔNG truyền `text`. Không truyền uid thì
mọi tin là ZNS, kể cả gửi cho khách ĐÃ quan tâm OA. Phép tra uid theo số điện thoại thì có thật —
nhưng nó nằm trong `api/v1/crm.py::zalo_send`, tức chỉ đường GỬI TAY mới tra, đường robot thì
không. Một luật, một nơi biết.

HAI ĐƯỜNG KHÁC NHAU Ở CHỖ AI GIỮ NỘI DUNG. ZNS: mẫu nằm bên Zalo, đã duyệt, mình đẩy tham số sang.
OA: mình tự soạn cả câu. Nên kể cả khi truyền uid, tin OA vẫn đi RỖNG nếu không soạn `text` —
robot cũ không soạn.

VÌ SAO ĐIỀU NÀY QUAN TRỌNG HƠN MỘT LỖI ĐỊNH TUYẾN: đường OA **không cần Zalo duyệt mẫu**. Nó là
đường duy nhất chạy thử được trong lúc mẫu ZNS còn đang đăng ký. Mở nó ra là mở cả khả năng thử.

PHÉP THỬ CANH NĂM CHỖ:
 1. Khách CÓ uid → tin đi đường OA và CÓ nội dung.
 2. Khách KHÔNG uid → vẫn ZNS như cũ, không đổi hành vi cũ.
 3. Mẫu chữ để trống → KHÔNG gửi tin OA rỗng; rơi về ZNS.
 4. Mẫu có chỗ điền lạ → không gửi câu vỡ cho khách.
 5. Phép tra uid CHỈ CÓ MỘT NƠI — đường tay và đường robot dùng chung.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Param, Tour, User
from app.models.crm import Lead, ZaloMessage
from app.models.cskh import CareTicket
from app.services import cskh as CS
from app.services import zalo as Z


@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _phieu(db, sdt="0987133383"):
    u = User(username="nv.a", full_name="NV A", role="nv_kd", password_hash="x")
    db.add(u); db.commit()
    t = Tour(code="TX1", name="Da Lat 3N2D", tour_type="le_noi_dia",
             start_date=dt.date.today() - dt.timedelta(days=4),
             end_date=dt.date.today() - dt.timedelta(days=1), operator_id=u.id, status="ket_thuc")
    db.add(t); db.commit()
    b = Booking(code="BKX1", tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="Tuan", customer_phone=sdt, source="truc_tiep", pax=1,
                amount=1_000_000, sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    db.add(CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Tuan", customer_phone=sdt,
                      owner_id=u.id, han_lien_he=dt.date.today(), status="moi"))
    db.commit()


def _co_oa(db, sdt="0987133383"):
    db.add(Lead(phone=Z.norm_phone(sdt), name="Tuan", channel="Zalo OA",
                lead_month=dt.date.today().strftime("%Y-%m"), zalo_uid="UID-TEST", created_by="zalo"))
    db.commit()


def _dat_mau(db, khoa, gia_tri):
    db.add(Param(key=khoa, value=gia_tri, label=khoa,
                 effective_from=dt.date.today() - dt.timedelta(days=1), status="active"))
    db.commit()


def _tin(db):
    return db.execute(select(ZaloMessage)).scalars().all()


def test_tc90_1_khach_da_quan_tam_oa_thi_di_duong_oa_va_co_noi_dung(db):
    _phieu(db); _co_oa(db)
    CS.gui_loi_moi_cham_diem(db)

    ds = _tin(db)
    assert len(ds) == 1
    assert ds[0].kind == "oa", "khach da quan tam OA ma van di ZNS - dung loi cua 200 tin ket"
    assert ds[0].zalo_uid == "UID-TEST"
    assert ds[0].text.strip(), "tin OA rong: co uid ma khong soan noi dung"
    assert "y-kien/" in ds[0].text, "tin phai mang duong dan trang khao sat"
    assert "Tuan" in ds[0].text and "Da Lat" in ds[0].text


def test_tc90_2_khach_chua_quan_tam_oa_thi_van_zns_nhu_cu(db):
    _phieu(db)
    CS.gui_loi_moi_cham_diem(db)
    ds = _tin(db)
    assert ds[0].kind == "zns"
    assert ds[0].params.get("ma_khao_sat"), "duong ZNS van phai day du tham so nhu cu"


def test_tc90_3_mau_de_trong_thi_khong_gui_tin_rong(db):
    _phieu(db); _co_oa(db)
    _dat_mau(db, "khao_sat_mau_tin", "")
    CS.gui_loi_moi_cham_diem(db)
    ds = _tin(db)
    assert ds[0].kind == "zns", "mau de trong la TAT duong OA, khong phai gui mot tin rong"


def test_tc90_4_mau_go_sai_cho_dien_thi_khong_gui_cau_vo(db):
    _phieu(db); _co_oa(db)
    _dat_mau(db, "khao_sat_mau_tin", "Chao {ten_khach}, xem {khong_co_cho_nay} nhe")
    CS.gui_loi_moi_cham_diem(db)
    ds = _tin(db)
    assert ds[0].kind == "zns", "mau go sai thi ro ngay cho nguoi khai, khong gui cau vo cho khach"


def test_tc90_5_phep_tra_uid_chi_co_mot_noi(db):
    _co_oa(db)
    assert Z.uid_theo_sdt(db, "0987133383") == "UID-TEST"
    assert Z.uid_theo_sdt(db, "0900000000") == ""
    crm = open("app/api/v1/crm.py", encoding="utf-8").read()
    assert "uid_theo_sdt" in crm, "duong gui tay phai dung chung phep tra, khong giu ban sao rieng"
    assert 'Lead.zalo_uid !=' not in crm, "con mot ban sao phep tra trong crm.py"
