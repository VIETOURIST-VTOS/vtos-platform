# -*- coding: utf-8 -*-
"""PQ-9 · Giao chủ cho cảnh báo.

Đo bản đang chạy 11/9/2026: 1.703 cảnh báo, 1.557 chưa xử lý, 146 từng được xử lý — tỷ lệ 8,6%.
Con số ấy không đo sự lười; nó đo một danh sách người nhận không có chủ. Một cảnh báo đỏ "quá
deadline thu tiền" gửi cho "nv_kd,gd_kd,tp_dh,ketoan": mỗi người mở ra đều thấy ba người khác cũng
nhận được.

Ba thứ tệp này canh, theo đúng thứ tự dễ hỏng:

  1. to_roles KHÔNG ĐƯỢC ĐỘNG VÀO. Hai cột trả lời hai câu khác nhau – ai được báo tin, và ai phải
     trả lời. Gộp lại là mất đúng cái khác biệt vừa làm ra.
  2. Suy không ra thì ĐỂ TRỐNG VÀ ĐẾM, không đẩy bừa lên cấp trên cho đỡ trống.
  3. Không đè lên chủ đã có — kể cả khi luật suy ra người khác.
"""
from datetime import date, datetime, timedelta

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
import app.models.crm   # noqa: F401
import app.models.cskh  # noqa: F401
import app.models.hr    # noqa: F401
from app.models.core import Alert, Tour, Booking, User
from app.services import chu_canh_bao as CB


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _u(db, ten, vai="nv_dh"):
    x = User(username=ten, full_name=ten.upper(), role=vai, active=True, password_hash="x")
    db.add(x); db.flush(); return x


def _tour(db, ma, operator_id):
    from datetime import date as _d
    t = Tour(code=ma, name="T", tour_type="trong_nuoc", start_date=_d(2026, 9, 1),
             end_date=_d(2026, 9, 3), operator_id=operator_id)
    db.add(t); db.flush(); return t


def _booking(db, ma, sales_id):
    b = Booking(code=ma, tour_id=1, request_id=1, sales_id=sales_id, created_by=sales_id or 1,
                customer_name="X", customer_phone="0900000000", source="web")
    db.add(b); db.flush(); return b


def _cb(db, kind, ref, roles="nv_kd,gd_kd,tp_dh,ketoan", level="red"):
    a = Alert(kind=kind, level=level, ref=ref, message="x", to_roles=roles, resolved=False,
              created_at=datetime.now())
    db.add(a); db.flush(); return a


# ---------------------------------------------------------------------------------------------
# 1. Từng luật suy chủ – mỗi luật là một nhóm cảnh báo thật trên bản đang chạy
# ---------------------------------------------------------------------------------------------

def test_qua_han_quyet_toan_ve_nguoi_dieu_hanh_chuyen(db):
    """851 cái trên bản đang chạy – nhóm lớn nhất. ref là MÃ chuyến, không phải id."""
    dh = _u(db, "vinh", "nv_dh")
    _tour(db, "TK001.10290826", dh.id)
    a = _cb(db, "qua_han_qt", "TK001.10290826", roles="tp_dh,ketoan,tgd")
    assert CB.suy_chu(db, a) == (dh.id, "")


def test_qua_deadline_thu_ve_sale_phu_trach_booking(db):
    """251 cái. ref = booking:<mã>."""
    s = _u(db, "an", "nv_kd")
    _booking(db, "VT125209", s.id)
    db.flush()
    a = _cb(db, "qua_deadline_thu", "booking:VT125209")
    assert CB.suy_chu(db, a) == (s.id, "")


def test_bao_cao_ngay_ve_chinh_nguoi_thieu_bao_cao(db):
    """356 cái (206 đỏ + 150 vàng). ref = <mã NV>:<ngày> – người phải nộp chính là chủ."""
    from app.models.hr import Employee
    # HAI nhân viên, và người cần tìm KHÔNG phải người đầu bảng. Bản trước chỉ có một người, nên
    # một đột biến bỏ hẳn điều kiện lọc theo mã (lấy bừa nhân viên đầu tiên) vẫn ra đúng kết quả
    # và lọt qua cả bộ. Một phép thử chỉ có một ứng viên thì không phân biệt được chọn đúng với
    # chọn bừa — mà nhầm người ở đây nghĩa là nhắc báo cáo ngày sai người.
    khac = _u(db, "khac", "nv_dh")
    nv = _u(db, "linh", "nv_dh")
    db.add(Employee(code="NV001", full_name="KHAC", user_id=khac.id, active=True,
                    department="Điều hành", position="NV", start_date=date(2026, 1, 1)))
    db.add(Employee(code="NV007", full_name="LINH", user_id=nv.id, active=True,
                    department="Điều hành", position="NV", start_date=date(2026, 1, 1)))
    db.flush()
    for kind in ("bc_ngay_1", "bc_ngay_2"):
        a = _cb(db, kind, "NV007:2026-09-09", roles="hcns,tgd")
        assert CB.suy_chu(db, a) == (nv.id, ""), kind


def test_cham_soc_va_hoi_thoai_ve_nguoi_dang_giu(db):
    from app.models.cskh import CareTicket
    from app.models.crm import Conversation
    o = _u(db, "mai", "nv_kd")
    db.add(CareTicket(id=177, booking_id=1, tour_id=1, owner_id=o.id,
                      han_lien_he=date(2026, 9, 5)))
    db.add(Conversation(id=230, channel="zalo", external_id="z1", sales_id=o.id))
    db.flush()
    assert CB.suy_chu(db, _cb(db, "cham_soc_qua_han", "cs:177"))[0] == o.id
    assert CB.suy_chu(db, _cb(db, "sale_tra_loi_cham", "conv:230"))[0] == o.id


# ---------------------------------------------------------------------------------------------
# 2. Suy không ra thì để trống và đếm
# ---------------------------------------------------------------------------------------------

def test_loai_co_y_khong_chu_thi_de_trong_chu_khong_day_len_cap_tren(db):
    """Gán đại cho một người là tạo ra một người chịu trách nhiệm giả."""
    _u(db, "sep", "tgd")
    a = _cb(db, "r9_chay_duoi_hoa_von", "tour:PT-DL-0912", roles="chutich,tgd,bks,ketoan,cntt")
    assert CB.giao(db, a)["da_giao"] is False
    assert a.nguoi_phu_trach is None


def test_moi_loai_co_y_khong_chu_deu_phai_viet_ly_do():
    """'Loại này không cần chủ' là lối thoát dễ nhất cho một loại chưa ai nghĩ tới cách giao."""
    assert CB.CO_Y_KHONG_CHU, "danh sách rỗng thì phép thử này không canh gì"
    for k, ly_do in CB.CO_Y_KHONG_CHU.items():
        assert len(ly_do) >= 40, f"{k}: khai cố ý mà không nói vì sao"


def test_ho_so_tim_thay_nhung_chua_co_chu_khac_voi_khong_tim_thay(db):
    """Hai lý do khác nhau dẫn tới hai việc phải làm khác nhau: một bên đi gán người phụ trách cho
    hồ sơ, một bên đi xem vì sao ref trỏ vào chỗ không có gì.

    Ví dụ lấy từ HỘI THOẠI chứ không từ chuyến, và đây là điều phép thử này dạy lại cho người đọc:
    tours.operator_id và bookings.sales_id đều NOT NULL, nên chuyến và booking không bao giờ rơi
    vào tình trạng "có hồ sơ mà chưa có chủ". Cột duy nhất cho phép để trống là conversations.
    sales_id – và đúng chỗ ấy, sáng 11/9/2026, có 100 trên 100 dòng bỏ trống.
    """
    from app.models.crm import Conversation
    db.add(Conversation(id=9, channel="zalo", external_id="z9", sales_id=None)); db.flush()
    assert CB.suy_chu(db, _cb(db, "sale_tra_loi_cham", "conv:9"))[1] == CB.HO_SO_CHUA_CO_CHU
    assert CB.suy_chu(db, _cb(db, "sale_tra_loi_cham", "conv:999"))[1] == CB.KHONG_TIM_THAY
    assert CB.suy_chu(db, _cb(db, "qua_han_qt", "KHONG_TON_TAI"))[1] == CB.KHONG_TIM_THAY


def test_loai_chua_khai_luat_thi_noi_ro_la_chua_khai(db):
    a = _cb(db, "mot_loai_moi_toanh", "x:1")
    assert CB.suy_chu(db, a) == (None, CB.KHONG_CO_LUAT)


def test_quet_dem_du_ly_do_chu_khong_tra_ve_0_im_lang(db):
    """'Đã giao 0' đọc ra giống hệt 'không còn gì để giao'. Hai thứ ấy phải phân biệt được."""
    for i in range(4):
        _cb(db, "mot_loai_moi_toanh", f"x:{i}")
    r = CB.giao_het(db)
    assert r["xet"] == 4 and r["da_giao"] == 0
    assert r["con_chua_co_chu"] == 4
    assert r["khong_giao_duoc"] == {CB.KHONG_CO_LUAT: 4}


# ---------------------------------------------------------------------------------------------
# 3. Không động vào to_roles, không đè lên chủ đã có
# ---------------------------------------------------------------------------------------------

def test_to_roles_giu_nguyen_sau_khi_giao(db):
    """Cột 'được báo tin' và cột 'người phải trả lời' trả lời hai câu khác nhau.

    Gộp lại – ví dụ thu to_roles về đúng một vai trò của người vừa nhận – là mất đúng cái khác biệt
    vừa làm ra: kế toán vẫn cần THẤY cảnh báo quá hạn thu dù người phải trả lời là sale.
    """
    s = _u(db, "an", "nv_kd")
    _booking(db, "VT1", s.id)
    a = _cb(db, "qua_deadline_thu", "booking:VT1", roles="nv_kd,gd_kd,tp_dh,ketoan")
    CB.giao(db, a)
    assert a.nguoi_phu_trach == s.id
    assert a.to_roles == "nv_kd,gd_kd,tp_dh,ketoan", "giao chủ xong lại sửa luôn danh sách báo tin"


def test_khong_de_len_chu_da_co(db):
    """Người phụ trách có thể đã được chuyển tay bằng quyết định của cấp quản lý. Một hàm chạy nền
    đè lên quyết định ấy thì quyết định kia chỉ sống tới vòng quét kế tiếp."""
    a_sale, nguoi_khac = _u(db, "an", "nv_kd"), _u(db, "binh", "nv_kd")
    _booking(db, "VT1", a_sale.id)
    a = _cb(db, "qua_deadline_thu", "booking:VT1")
    a.nguoi_phu_trach = nguoi_khac.id
    kq = CB.giao(db, a)
    assert kq["da_giao"] is False and kq["ly_do"] == "da_co_chu"
    assert a.nguoi_phu_trach == nguoi_khac.id


def test_ghi_lai_luc_giao(db):
    """Không có mốc giao thì không đo được 'giao rồi bao lâu chưa ai đụng' – đúng con số mà tỷ lệ
    146/1.703 đang thiếu để giải thích."""
    s = _u(db, "an", "nv_kd")
    _booking(db, "VT1", s.id)
    a = _cb(db, "qua_deadline_thu", "booking:VT1")
    CB.giao(db, a)
    assert a.giao_luc is not None


def test_quet_lai_lan_hai_khong_lam_gi_them(db):
    s = _u(db, "an", "nv_kd")
    for i in range(3):
        _booking(db, f"VT{i}", s.id)
    db.flush()
    for i in range(3):
        _cb(db, "qua_deadline_thu", f"booking:VT{i}")
    m = CB.giao_het(db); db.flush()
    hai = CB.giao_het(db)
    assert m["da_giao"] == 3
    assert hai["xet"] == 0 and hai["da_giao"] == 0


def test_canh_bao_da_xu_ly_khong_bi_quet_lai(db):
    s = _u(db, "an", "nv_kd")
    _booking(db, "VT1", s.id)
    a = _cb(db, "qua_deadline_thu", "booking:VT1")
    a.resolved = True; db.flush()
    assert CB.giao_het(db)["xet"] == 0


# ---------------------------------------------------------------------------------------------
# 4. Báo cáo: con số "chưa có chủ" phải nhìn thấy được
# ---------------------------------------------------------------------------------------------

def test_bao_cao_tach_ro_co_chu_va_chua_co_chu(db):
    s = _u(db, "an", "nv_kd")
    _booking(db, "VT1", s.id)
    _cb(db, "qua_deadline_thu", "booking:VT1")
    _cb(db, "r9_chay_duoi_hoa_von", "tour:X")
    _cb(db, "mot_loai_moi_toanh", "y:1")
    # Một cảnh báo ĐÃ XỬ LÝ, phải nằm ngoài mọi con số. Bản trước không có dòng nào như vậy, nên
    # một đột biến bỏ điều kiện resolved==False ra khỏi báo cáo đã lọt qua: báo cáo đếm cả việc đã
    # xong thì con số "chưa có chủ" phồng lên theo thời gian và không còn nói lên điều gì.
    xong = _cb(db, "mot_loai_moi_toanh", "z:1")
    xong.resolved = True; db.flush()
    CB.giao_het(db); db.flush()
    r = CB.bao_cao(db)
    assert r["chua_xu_ly"] == 3, "báo cáo đếm cả cảnh báo đã xử lý"
    assert r["da_co_chu"] == 1
    assert r["chua_co_chu"] == 2
    assert r["theo_nguoi"] == [{"id": s.id, "ten": "AN", "so": 1}]
    loai = {x["loai"]: x for x in r["chua_co_chu_theo_loai"]}
    assert loai["r9_chay_duoi_hoa_von"]["co_y"], "loại cố ý không chủ phải kèm lý do ra tới màn hình"
    assert loai["mot_loai_moi_toanh"]["co_y"] == "", "loại chưa khai luật không được trông như cố ý"
