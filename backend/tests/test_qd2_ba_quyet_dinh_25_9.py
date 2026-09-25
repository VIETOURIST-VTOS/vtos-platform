"""QĐ-2 · Ba quyết định của Chủ tịch ngày 25/9/2026 — hàng rào.

Ba câu trong bộ chín câu hỏi mặt cắt Kinh doanh ↔ Điều hành. Cả ba đều nhỏ về mã và đều là một
QUYẾT ĐỊNH, nên chúng cần phép thử canh — không phải để chặn ai sửa, mà để ngày có người sửa thì
họ phải đọc lý do trước.

    Câu 2 · Giữ chỗ 48 giờ → 4 giờ.
    Câu 6 · Mở khoá booking: GỠ Giám đốc và Trưởng phòng Kinh doanh, THÊM Sale Admin.
    Câu 8 · Cột "Quá SLA 2h" rời bảng điểm Sale, về bảng điểm Điều hành.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CÂU 6 VÀ CÂU 8 CẦN CANH HƠN CẢ
═══════════════════════════════════════════════════════════════════════════════════════════════
Cả hai đều là lần SIẾT — lấy đi một thứ người ta đang có. Một lần siết không có phép thử canh thì
ba tháng sau có người "sửa cho tiện" và không ai biết là đang mở lại một cánh cửa đã đóng có lý do.

Câu 8 đặc biệt dễ quay lại: cột ấy tiện cho người xem bảng bán hàng, và lần sau ai đó sẽ thêm lại
vì "sale cũng cần biết". Lý do gỡ không phải là sale không cần biết — mà là con số ấy đo việc của
người khác, và một thước đo đo sai người thì tệ hơn không đo.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.services import bookings as BK
from app.services import rules as R
from app.services import sales_reports as SR

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("gdkd", "gd_kd"),
                     ("sadmin", "sales_admin"), ("nvdh", "nv_dh"), ("tpdh", "tp_dh"),
                     ("cntt", "cntt"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


# ───────────────────────── câu 2 · giữ chỗ 4 giờ ─────────────────────────

def test_qd2a_han_giu_cho_la_4_gio():
    db = _db()
    assert float(R.get_param(db, "han_giu_cho_gio")) == 4.0, (
        "Chủ tịch quyết 25/9/2026: giữ chỗ 4 giờ, không còn 48")


def test_qd2b_han_canh_bao_KHONG_di_theo_han_giu_cho():
    """Hai con số TÁCH NHAU từ 25/9/2026, và lời khai cũ nói "bằng han_giu_cho_gio" đã sửa.

    Giữ một CHỖ NGỒI và xử lý một CẢNH BÁO là hai việc khác nhau: ghế không bán cho người khác thì
    càng ngắn càng tốt; còn hạn 4 giờ cho mọi cảnh báo thì cảnh báo tạo sau giờ chiều đều trễ ngay
    sáng hôm sau, và một bảng đỏ toàn bộ thì không còn chỉ được chỗ nào gấp.
    """
    db = _db()
    assert float(R.get_param(db, "canh_bao_han_mac_dinh_gio")) == 48.0
    nguon = open(R.__file__, encoding="utf-8").read()
    i = nguon.find('"canh_bao_han_mac_dinh_gio"')
    assert "bằng han_giu_cho_gio" not in nguon[i:i + 400], (
        "lời khai vẫn nói hai con số bằng nhau, trong khi chúng đã tách")


def test_qd2c_han_tinh_bang_GIO_DONG_HO_va_dieu_do_duoc_noi_ra():
    """Không phải giờ làm việc. Phép thử này không đòi đổi — nó khoá LỜI KHAI ở chỗ nói ra hệ quả,
    để người sửa con số 4 lần sau đọc được chuyện booking 16h30 hết hạn lúc 20h30 cùng ngày."""
    from app.services import giu_cho as GC
    nguon = open(GC.__file__, encoding="utf-8").read()
    assert "timedelta(hours=gio)" in nguon, "cách tính hạn đã đổi — xem lại lời khai ở rules.py"
    ghi = open(R.__file__, encoding="utf-8").read()
    i = ghi.find('"han_giu_cho_gio"')
    quanh = ghi[max(0, i - 1400):i]
    assert "giờ làm việc" in quanh or "GIỜ ĐỒNG HỒ" in quanh, (
        "lời khai không nói ra rằng hạn tính bằng giờ đồng hồ — đó là hệ quả xảy ra ngay đêm đầu tiên")


def test_qd2d_robot_van_chi_dung_booking_CHUA_THU_DONG_NAO():
    """Đây là thứ làm cho 4 giờ không thành mất khách. Nếu một ngày luật này mất thì 4 giờ trở
    thành nguy hiểm, và phép thử đỏ đúng lúc ấy."""
    from app.services import giu_cho as GC
    import re
    nguon = open(GC.__file__, encoding="utf-8").read()
    i = nguon.find("def het_han_giu_cho")
    than = re.sub(r'"""[\s\S]*?"""', "", nguon[i:nguon.find("\ndef ", i + 10)])
    assert "b.paid" in than and "continue" in than, (
        "robot không còn bỏ qua booking đã thu tiền — với hạn 4 giờ thì đó là mất chỗ của khách đã cọc")


# ───────────────────────── câu 6 · mở khoá booking ─────────────────────────

def test_qd6a_kinh_doanh_KHONG_con_mo_khoa_duoc():
    """Lần SIẾT. Mở khoá không phải xem — nó là quyền sửa số sau khi đã chốt."""
    for vai in ("gd_kd", "tp_kd", "nv_kd", "tn_kd"):
        assert vai not in BK.UNLOCK_ROLES, (
            f"{vai} mở khoá được booking đã chốt — Chủ tịch gỡ quyền ấy ngày 25/9/2026")


def test_qd6b_tp_dieu_hanh_va_sale_admin_mo_khoa_duoc():
    for vai in ("tp_dh", "sales_admin"):
        assert vai in BK.UNLOCK_ROLES


def test_qd6c_cong_endpoint_va_cong_than_ham_khai_GIONG_NHAU():
    """Bệnh KS-2: cửa này khai quyền ở thân hàm còn chữ ký endpoint để trống, nên bộ kiểm quyền đọc
    ra "ai đăng nhập cũng gọi được". Người bị từ chối vẫn nhận 403, nhưng bản khai quyền nói sai."""
    import re
    from app.api.v1 import routes as RT
    nguon = open(RT.__file__, encoding="utf-8").read()
    i = nguon.find('def unlock_booking')
    chu_ky = nguon[i:nguon.find("\n", nguon.find(":", i))]
    assert "require_roles" in chu_ky, "endpoint mở khoá vẫn để trống chữ ký — xem KS-2"
    assert "UNLOCK_ROLES" in chu_ky, "endpoint khai một danh sách RIÊNG — hai bảng rồi sẽ lệch"


def test_qd6d_cua_van_doi_ly_do():
    """Mở khoá mà không nói vì sao là mở khoá không ai truy được."""
    db = _db()
    from app.models.core import Booking, ServiceRequest, Tour
    t = Tour(code="T1", name="T1", tour_type="le_noi_dia", start_date=HOM_NAY, end_date=HOM_NAY,
             operator_id=_u(db, "nvdh").id, status="da_duyet", price_per_pax=1.0, planned_pax=1)
    db.add(t); db.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="x",
                       customer_phone="0900", source="web", pax=1)
    db.add(r); db.flush()
    b = Booking(code="BK1", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                created_by=_u(db, "nvdh").id,
                customer_name="x", customer_phone="0900", source="web", pax=1, amount=1.0, locked=True)
    db.add(b); db.commit()
    with pytest.raises(Exception):
        BK.unlock(db, _u(db, "tpdh"), b, "")


# ───────────────────────── câu 8 · cột SLA về đúng bảng ─────────────────────────

def test_qd8a_bang_diem_SALE_khong_con_cot_qua_SLA():
    """Con số do Điều hành gây ra. Một nhân viên Kinh doanh mang trên bảng điểm của mình một con số
    họ không làm gì để đổi được — thước đo ấy không đo ai cả."""
    nguon = open(SR.__file__, encoding="utf-8").read()
    i = nguon.find("def ban_tour_le")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    assert "sla_qua" not in than, "cột Quá SLA đã quay lại bảng điểm sale — đọc lý do ngay trên hàm"
    assert '"Quá SLA' not in than


def test_qd8b_cot_du_4_truong_thi_O_LAI():
    """Bốn trường ấy do CHÍNH SALE điền lúc gửi yêu cầu — đo đúng người, nên không gỡ theo."""
    nguon = open(SR.__file__, encoding="utf-8").read()
    i = nguon.find("def ban_tour_le")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    assert "du_4_truong" in than


def test_qd8c_bang_diem_DIEU_HANH_co_cot_qua_SLA():
    """Gỡ khỏi bảng này mà không dựng lại ở bảng kia là làm mất một thước đo, không phải sửa nó."""
    from app.services import bao_cao_phong as BC
    nguon = open(BC.__file__, encoding="utf-8").read()
    i = nguon.find("def _dieu_hanh")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    assert "booking_qua_sla" in than and "sla_ok" in than


def test_qd8d_du_lieu_sla_van_duoc_ghi_nhu_cu():
    """Lần này đổi chỗ HIỂN THỊ, không đổi việc ĐO. `bookings.sla_ok` vẫn ghi lúc tạo booking."""
    import re
    from app.services import tours as T
    nguon = open(T.__file__, encoding="utf-8").read()
    i = nguon.find("def create_booking")
    than = re.sub(r"#[^\n]*", "", nguon[i:nguon.find("\ndef ", i + 10)])
    assert "sla_ok=" in than and "sla_booking_phut" in than


def test_qd8e_bang_diem_sale_van_chay_duoc_tren_kho_rong():
    db = _db()
    r = SR.ban_tour_le(db, HOM_NAY, HOM_NAY)
    cot = [k for k, _ in r["columns"]["summary"]]
    assert "sla_qua" not in cot and "du_4_truong" in cot
