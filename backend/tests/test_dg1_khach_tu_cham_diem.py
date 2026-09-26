"""DG-1 · Khách tự chấm điểm sau tour — đề xuất tự động hoá CSKH 25/9/2026.

Ba nhóm phép thử, theo đúng ba thứ dễ hỏng nhất:

    1. CỬA RA ĐƯỜNG. Đây là cửa duy nhất của VTOS không cần đăng nhập. Mọi phép thử về nó đều hỏi
       một câu: "người lạ cầm đường dẫn này thì lấy được gì".
    2. RỖNG KHÁC 0. Khách bỏ qua mục nào thì mục ấy RỖNG — ghi 0 là hạ điểm trung bình của một
       người vì một chuyến không có người ấy.
    3. KHÔNG DỰNG LẠI LUẬT CŨ. Ngưỡng mở khiếu nại và luật tạo lead khách cũ đã có từ Đợt 4;
       `danh_gia.ghi_danh_gia` phải GỌI LẠI chúng, không chép.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.models.cskh import CareTicket, Complaint
from app.models.crm import Lead, ZaloMessage
from app.models.danh_gia import DanhGiaSauTour, MaKhaoSat
from app.models.hr import Employee, GuideAssignment
from app.services import cskh as CS
from app.services import danh_gia as DG

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvdh", "nv_dh"), ("tpkd", "tp_kd")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _chuyen(db, hdv=()):
    t = Tour(code="L1", name="Đà Lạt 3N2Đ", tour_type="le_noi_dia",
             start_date=HOM_NAY - dt.timedelta(days=5), end_date=HOM_NAY - dt.timedelta(days=2),
             operator_id=_u(db, "nvdh").id, status="ket_thuc", price_per_pax=5_000_000,
             fixed_cost=20_000_000, var_cost_per_pax=2_000_000, planned_pax=20, seats_open=20)
    db.add(t); db.flush()
    for ten in hdv:
        e = Employee(code=f"NS{len(ten):04d}{ten[:2]}", full_name=ten, department="dieu_hanh")
        db.add(e); db.flush()
        db.add(GuideAssignment(tour_id=t.id, guide_id=e.id, days=3, rate_per_day=500_000,
                               status="da_xac_nhan"))
    db.commit(); return t


def _phieu(db, t, sdt="0900000001"):
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="Khách A",
                       customer_phone=sdt, source="web", pax=1)
    db.add(r); db.flush()
    b = Booking(code="BK1", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                created_by=_u(db, "nvdh").id, customer_name="Khách A", customer_phone=sdt,
                source="web", pax=1, amount=5_000_000)
    db.add(b); db.flush()
    c = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Khách A", customer_phone=sdt,
                   owner_id=_u(db, "nvkd").id, han_lien_he=HOM_NAY + dt.timedelta(days=3))
    db.add(c); db.commit(); return c


# ───────────────────────── 1 · cửa ra đường ─────────────────────────

def test_dg1_ma_KHONG_suy_ra_duoc_tu_so_thu_tu():
    """Mã chạy theo số thứ tự thì ai cũng đọc được đánh giá của người khác bằng cách cộng một."""
    db = _db(); t = _chuyen(db)
    m1 = DG.sinh_ma(db, _phieu(db, t, "0900000001"))
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="B",
                       customer_phone="0900000002", source="web", pax=1)
    db.add(r); db.flush()
    b2 = Booking(code="BK2", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                 created_by=_u(db, "nvdh").id, customer_name="B", customer_phone="0900000002",
                 source="web", pax=1, amount=5_000_000)
    db.add(b2); db.flush()
    c2 = CareTicket(booking_id=b2.id, tour_id=t.id, customer_name="B", customer_phone="0900000002",
                    owner_id=_u(db, "nvkd").id, han_lien_he=HOM_NAY)
    db.add(c2); db.commit()
    m2 = DG.sinh_ma(db, c2)
    assert len(m1.ma) >= 20 and len(m2.ma) >= 20
    assert not m1.ma.isdigit() and abs(len(m1.ma) - len(m2.ma)) <= 2
    assert m1.ma != m2.ma


def test_dg2_mot_phieu_MOT_ma():
    """Hai mã cho một phiếu nghĩa là khách chấm được hai lần."""
    db = _db(); c = _phieu(db, _chuyen(db))
    assert DG.sinh_ma(db, c).ma == DG.sinh_ma(db, c).ma


def test_dg3_trang_cong_khai_KHONG_in_ra_gi_khach_chua_biet():
    """Mọi thứ in ở đây là in cho bất kỳ ai cầm được đường dẫn."""
    db = _db(); t = _chuyen(db, hdv=["Nguyễn Văn Hướng"])
    c = _phieu(db, t); m = DG.sinh_ma(db, c); db.commit()
    v = DG.mo_phieu(db, m.ma)
    day_du = str(v)
    assert "0900000001" not in day_du, "lộ số điện thoại"
    assert "5000000" not in day_du and "5_000_000" not in day_du, "lộ giá"
    assert "BK1" not in day_du, "lộ mã booking"
    assert v["tour_ten"] == "Đà Lạt 3N2Đ" and v["ten_khach"] == "Khách A"


def test_dg4_mot_ma_MOT_lan_ghi():
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    d = {"diem": [{"doi_tuong": "tour", "diem": 5}], "nhu_cau_tiep": "khong",
         "dong_y_dung_danh_gia": "co"}
    DG.ghi_danh_gia(db, m.ma, d)
    with pytest.raises(Exception):
        DG.ghi_danh_gia(db, m.ma, d)


def test_dg5_ma_het_han_thi_dong():
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c)
    m.het_han = dt.datetime.now() - dt.timedelta(minutes=1); db.commit()
    with pytest.raises(Exception):
        DG.mo_phieu(db, m.ma)


def test_dg6_ma_sai_va_ma_khong_co_nhan_CUNG_MOT_loi():
    """Nói khác nhau là chỉ cho người dò biết mã nào tồn tại."""
    db = _db()
    with pytest.raises(Exception) as e1:
        DG.mo_phieu(db, "khong-co-ma-nay")
    with pytest.raises(Exception) as e2:
        DG.mo_phieu(db, "")
    assert str(e1.value.detail) == str(e2.value.detail)


def test_dg7_dem_so_lan_mo_vi_do_la_thuoc_do_cua_moc_nghiem_thu():
    """Mốc 31/10 của đề xuất đòi biết khách có đọc tin không. `so_lan_mo` là thước đo ấy."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.mo_phieu(db, m.ma); DG.mo_phieu(db, m.ma)
    db.refresh(m)
    assert m.so_lan_mo == 2 and m.mo_lan_dau is not None


# ───────────────────────── 2 · rỗng khác 0 ─────────────────────────

def test_dg8_muc_khach_bo_qua_thi_RONG_chu_khong_phai_0():
    """Chuyến đi bộ không có tài xế. Ghi 0 thì điểm trung bình của tài xế tụt vì một chuyến không
    có tài xế nào."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 5},
                                        {"doi_tuong": "an_uong", "diem": None}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "co"})
    rows = list(db.execute(select(DanhGiaSauTour)).scalars())
    assert len(rows) == 1 and rows[0].doi_tuong == "tour", "mục bỏ trống không được sinh dòng 0"


def test_dg9_muc_bo_diem_nhung_CO_loi_thi_van_giu():
    """Khách không chấm sao nhưng viết một câu — câu ấy là thứ quý nhất của cả phiếu."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 4},
                                        {"doi_tuong": "an_uong", "diem": None,
                                         "nhan_xet": "Bữa trưa ngày 2 hơi ít"}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    x = db.execute(select(DanhGiaSauTour).where(DanhGiaSauTour.doi_tuong == "an_uong")).scalars().first()
    assert x is not None and x.diem is None and "Bữa trưa" in x.nhan_xet


def test_dg10_diem_chung_lam_tron_XUONG():
    """Làm tròn lên thì 2,5 thành 3 và vượt ngưỡng mở khiếu nại — một khách không hài lòng biến
    mất khỏi sổ vì một phép làm tròn."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "khach_san", "diem": 2},
                                        {"doi_tuong": "an_uong", "diem": 3}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    db.refresh(c)
    assert c.hai_long == 2, "2 và 3 phải ra 2, không phải 3"


# ───────────────────────── 3 · không dựng lại luật cũ ─────────────────────────

def test_dg11_diem_thap_van_tu_mo_ho_so_khieu_nai():
    """Luật của Đợt 4, gọi lại chứ không chép. Chép là tạo bản sao thứ hai của NGƯỠNG."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 2}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    kn = list(db.execute(select(Complaint)).scalars())
    assert len(kn) == 1 and kn[0].care_id == c.id


def test_dg12_ho_so_tu_mo_mang_ten_SALE_DA_BAN_chu_khong_phai_robot():
    """Trước bản này `handler` nhận tên người đang gõ — đúng khi nhân viên gọi hộ, sai ngay khi
    khách TỰ chấm: lúc ấy người gõ là tài khoản máy."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 1}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    kn = db.execute(select(Complaint)).scalars().first()
    assert kn.handler == "nvkd", f"hồ sơ mang tên {kn.handler} – phải là sale đã bán"


def test_dg13_viec_goi_lai_CO_CHU_va_CO_HAN():
    """Bước 4 của đề xuất: "tự tạo phiếu việc cho sale đã bán tour; phải gọi khách trong 24 giờ".
    Hai chữ "cho sale" và "trong 24 giờ" chính là hai cột trước nay bỏ trống."""
    from app.models.core import Alert
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 2}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    a = db.execute(select(Alert).where(Alert.kind == "cham_soc_diem_thap")).scalars().first()
    assert a is not None, "không có việc nào được giao"
    assert a.nguoi_phu_trach == _u(db, "nvkd").id, "việc không có chủ"
    assert a.han_xu_ly is not None, "việc không có hạn"
    assert 23 <= (a.han_xu_ly - dt.datetime.now()).total_seconds() / 3600 <= 25


def test_dg14_khach_muon_di_tiep_van_tu_tao_lead_khach_cu():
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 5}],
                               "nhu_cau_tiep": "co", "dong_y_dung_danh_gia": "co"})
    l = db.execute(select(Lead)).scalars().first()
    assert l is not None and l.channel == "khach_cu" and l.sales_id == _u(db, "nvkd").id


def test_dg15_danh_gia_py_KHONG_chep_lai_nguong_mo_khieu_nai():
    """Đo bằng MÃ, không chỉ bằng kết quả: một ngưỡng chép sang đây sẽ không làm phép thử trên đỏ
    cho tới ngày có người sửa ngưỡng ở một nơi."""
    nguon = open(DG.__file__, encoding="utf-8").read()
    assert "cham_soc_hai_long_mo_kn" not in nguon, "ngưỡng mở khiếu nại bị chép sang danh_gia.py"
    assert "CS.ghi_ket_qua" in nguon, "không còn gọi lại luật cũ"


# ───────────────────────── xin phép dùng lời khách ─────────────────────────

def test_dg16_form_PHAI_hoi_cau_xin_phep():
    """Ô `dong_y_dung_danh_gia` có từ Đợt 4 với đúng lý do: chưa đồng ý thì tuyệt đối không đưa
    lời khách lên kênh truyền thông. Một form tự động bỏ câu này đi là lấy mất một quyền của khách
    bằng cách im lặng."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c); db.commit()
    with pytest.raises(Exception):
        DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "tour", "diem": 5}],
                                   "nhu_cau_tiep": "khong"})


# ───────────────────────── hướng dẫn viên ─────────────────────────

def test_dg17_chuyen_hai_HDV_thi_hien_TEN_TUNG_NGUOI():
    """Một ô "HDV" chung thì bảng điểm HDV không bao giờ cộng đúng, và người bị chấm oan không có
    cách nào cãi."""
    db = _db(); t = _chuyen(db, hdv=["Nguyễn Văn A", "Trần Thị B"])
    c = _phieu(db, t); m = DG.sinh_ma(db, c); db.commit()
    hdv = [x for x in DG.mo_phieu(db, m.ma)["muc"] if x["doi_tuong"] == "hdv"]
    assert len(hdv) == 2 and {x["ten"] for x in hdv} == {"Nguyễn Văn A", "Trần Thị B"}
    assert all(x["id"] for x in hdv), "mục HDV phải mang khoá của từng người"


def test_dg18_cham_HDV_ma_khong_chi_ro_nguoi_thi_TU_CHOI():
    db = _db(); c = _phieu(db, _chuyen(db, hdv=["A"])); m = DG.sinh_ma(db, c); db.commit()
    with pytest.raises(Exception):
        DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "hdv", "diem": 5}],
                                   "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})


def test_dg19_ten_doi_tuong_duoc_CHEP_LAI_luc_cham():
    """Hướng dẫn viên nghỉ việc và hồ sơ bị xoá thì điểm cũ vẫn phải đọc được là chấm cho ai —
    bài học của bia mộ tài khoản, TC-83."""
    db = _db(); t = _chuyen(db, hdv=["Nguyễn Văn A"]); c = _phieu(db, t)
    m = DG.sinh_ma(db, c); db.commit()
    e = db.execute(select(Employee)).scalars().first()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 5}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    x = db.execute(select(DanhGiaSauTour)).scalars().first()
    assert x.doi_tuong_ten == "Nguyễn Văn A"


# ───────────────────────── bảng điểm ─────────────────────────

def test_dg20_bang_diem_MAC_DINH_chi_cong_phan_khach_tu_cham():
    """Khi không còn bộ phận chăm sóc riêng, người ghi hộ chính là người bị chấm. Trộn hai loại số
    vào nhau thì bảng điểm không đo được ai."""
    db = _db(); t = _chuyen(db, hdv=["A"]); c = _phieu(db, t); m = DG.sinh_ma(db, c); db.commit()
    e = db.execute(select(Employee)).scalars().first()
    DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 2}],
                               "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "khong"})
    DG.ghi_ho(db, _u(db, "nvkd"), c, {"diem": [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 5,
                                                "doi_tuong_ten": "A"}]})
    tu, den = HOM_NAY - dt.timedelta(days=1), HOM_NAY + dt.timedelta(days=1)
    chi_khach = DG.bang_diem(db, "hdv", tu, den)["rows"][0]
    ca_hai = DG.bang_diem(db, "hdv", tu, den, chi_khach=False)["rows"][0]
    assert chi_khach["diem_tb"] == 2.0, "bảng mặc định đã lẫn điểm nhân viên ghi hộ"
    assert ca_hai["diem_tb"] == 3.5


def test_dg21_ghi_ho_de_lai_DAU_VET_la_nhan_vien_ghi():
    db = _db(); c = _phieu(db, _chuyen(db))
    DG.ghi_ho(db, _u(db, "nvkd"), c, {"diem": [{"doi_tuong": "tour", "diem": 4}]})
    x = db.execute(select(DanhGiaSauTour)).scalars().first()
    assert x.nguon == "nhan_vien" and x.nguoi_ghi == "nvkd"


def test_dg22_bang_diem_in_SO_LUOT_canh_diem_trung_binh():
    """Một bảng xếp hạng dựng trên mười lượt chấm không phải là một bảng xếp hạng."""
    db = _db(); c = _phieu(db, _chuyen(db))
    DG.ghi_ho(db, _u(db, "nvkd"), c, {"diem": [{"doi_tuong": "tour", "diem": 4}]})
    r = DG.bang_diem(db, "tour", HOM_NAY - dt.timedelta(days=1), HOM_NAY + dt.timedelta(days=1),
                     chi_khach=False)
    assert "so_luot" in r["rows"][0] and r["luu_y"]


# ───────────────────────── ba con số của báo cáo tuần ─────────────────────────

def test_dg23_chi_so_in_DU_BA_con_so():
    """Gọi điện thì "không nghe máy" là một kết quả có người ghi. Tin nhắn thì "không trả lời" chỉ
    là một dòng trống — nên ba con số phải đứng cạnh nhau."""
    db = _db(); c = _phieu(db, _chuyen(db)); DG.sinh_ma(db, c); db.commit()
    r = DG.chi_so(db, HOM_NAY - dt.timedelta(days=1), HOM_NAY + dt.timedelta(days=1))
    for k in ("tin_da_gui", "tin_loi", "khach_mo", "khach_tra_loi", "ty_le_tra_loi"):
        assert k in r, f"thiếu {k}"


def test_dg24_mau_so_la_tin_DA_GUI_chu_khong_phai_tin_da_tao():
    """Tin không gửi được thì khách không có cơ hội trả lời; tính họ vào mẫu số là tự hạ điểm mình
    bằng một lỗi kỹ thuật."""
    db = _db(); c = _phieu(db, _chuyen(db)); m = DG.sinh_ma(db, c)
    db.add(ZaloMessage(kind="zns", phone="0900000001", purpose="cham_soc", status="da_gui",
                       booking_id=c.booking_id))
    db.add(ZaloMessage(kind="zns", phone="0900000002", purpose="cham_soc", status="loi",
                       booking_id=c.booking_id))
    m.dung_luc = dt.datetime.now(); db.commit()
    r = DG.chi_so(db, HOM_NAY - dt.timedelta(days=1), HOM_NAY + dt.timedelta(days=1))
    assert r["tin_da_gui"] == 1 and r["tin_loi"] == 1
    assert r["ty_le_tra_loi"] == 1.0, "tin lỗi không được nằm trong mẫu số"


# ───────────────────────── gửi tin ─────────────────────────

def test_dg25_robot_KHONG_sinh_ma_cho_phieu_khong_co_so_dien_thoai():
    """Sinh mã cho một phiếu không gửi được là tạo ra một con số "đã mời" không có thật, và tỷ lệ
    trả lời sẽ bị chia cho nó."""
    db = _db(); t = _chuyen(db)
    c = _phieu(db, t, sdt="");
    assert CS.gui_loi_moi_cham_diem(db) == 0
    assert db.execute(select(MaKhaoSat)).scalars().first() is None


def test_dg26_tin_duoc_HEN_GIO_chu_khong_gui_ngay():
    """Một tin chăm sóc đến lúc 2 giờ sáng làm hỏng đúng thiện chí mà nó đi xin."""
    db = _db(); _phieu(db, _chuyen(db))
    assert CS.gui_loi_moi_cham_diem(db) == 1
    z = db.execute(select(ZaloMessage)).scalars().first()
    assert z is not None and z.gui_tu_luc is not None
    assert z.gui_tu_luc > dt.datetime.now()
    assert z.gui_tu_luc.hour == 9 and z.gui_tu_luc.minute == 0


def test_dg27_chay_lai_KHONG_gui_trung():
    db = _db(); _phieu(db, _chuyen(db))
    assert CS.gui_loi_moi_cham_diem(db) == 1
    assert CS.gui_loi_moi_cham_diem(db) == 0


def test_dg28_nhac_DUNG_MOT_lan():
    """"Một lần" là luật, không phải lời khuyên — và nó được đo bằng chính sổ tin."""
    db = _db(); c = _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    m = db.execute(select(MaKhaoSat)).scalars().first()
    m.tao_luc = dt.datetime.now() - dt.timedelta(hours=72); db.commit()
    assert CS.nhac_chua_tra_loi(db) == 1
    assert CS.nhac_chua_tra_loi(db) == 0, "nhắc lần thứ hai"


def test_dg29_khach_da_tra_loi_thi_KHONG_nhac():
    db = _db(); c = _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    m = db.execute(select(MaKhaoSat)).scalars().first()
    m.tao_luc = dt.datetime.now() - dt.timedelta(hours=72)
    m.dung_luc = dt.datetime.now(); db.commit()
    assert CS.nhac_chua_tra_loi(db) == 0


def test_dg30_hang_doi_bo_qua_tin_CHUA_toi_gio():
    from app.services import zalo as Z
    db = _db(); _phieu(db, _chuyen(db))
    CS.gui_loi_moi_cham_diem(db)
    r = Z.send_pending(db)
    assert r["sent"] == 0, "tin hẹn giờ đã bị gửi sớm"
    z = db.execute(select(ZaloMessage)).scalars().first()
    assert z.status in ("cho_gui", "cho_cau_hinh")
