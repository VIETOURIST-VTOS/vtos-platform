"""SC-1 · Trần bán và cửa mở thêm chỗ — hàng rào, 25/9/2026.

Chủ tịch quyết 25/9: *"Tạo form và quyền cho điều hành nhập số khách vào, sau khi duyệt dự toán sẽ
chặn số khách bán tối đa"*, và *"nếu mở thêm chỗ mà lợi nhuận tụt thì chặn ngay"*.

═══════════════════════════════════════════════════════════════════════════════════════════════
TRƯỚC NGÀY NÀY, HỆ THỐNG KHÔNG KIỂM SỨC CHỨA Ở ĐÂU CẢ TRÊN ĐƯỜNG BÁN
═══════════════════════════════════════════════════════════════════════════════════════════════
Cả `tours.create_request` lẫn `tours.create_booking` đều không gọi `giu_cho.con_trong()` một lần
nào, và `seats_open` chỉ được ĐỌC để hiển thị (`api/v1/products.py`, `inbox.py`, `sales_reports`).
Một tour 45 chỗ nhận booking thứ 46, 47, 100 — tuần tự, bình thường, không cần hai người bấm trùng
một giây. Đây không phải lỗi đua tranh; đây là một cổng chưa từng được dựng.

Chỗ DUY NHẤT trong cả kho có kiểm sức chứa là `giu_cho.gia_han` khi KHÔI PHỤC một chỗ đã hết hạn:
hàng rào dựng ở chiều quay lại, không dựng ở chiều bán ra. Hệ thống chặn người đã mất chỗ quay
lại, nhưng không chặn người mới lấy chỗ không còn.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA ĐIỀU PHÉP THỬ NÀY CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
 1. CHẶN Ở CHỖ CHIẾM CHỖ, CẢNH BÁO Ở CHỖ HỨA. Cửa tạo booking chặn cứng; cửa gửi yêu cầu chỉ
    cảnh báo, vì gửi yêu cầu chưa chiếm ghế và người bán cần biết trước khi hứa với khách.
 2. CHƯA KHAI SỐ CHỖ KHÁC VỚI HẾT CHỖ. Hơn 1.200 chuyến nhập từ Vietrip có thể không mang số
    chỗ; đọc "chưa khai" thành "0 chỗ" là chặn đứng việc bán của chúng trong một đêm.
 3. MỞ THÊM CHỖ MÀ LÃI ÍT ĐI THÌ CHẶN. Và chặn theo CẢ HAI con số, vì chúng đi ngược chiều nhau
    được: bán thêm 16 khách làm lợi nhuận tăng, xe to hơn làm biên tụt.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import Gate
from app.db.session import Base
from app.models.core import Alert, ServiceRequest, Tour, User
from app.services import rules as R
from app.services import tours as T
from fastapi import HTTPException

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("sadmin", "sales_admin"),
                     ("nvdh", "nv_dh"), ("tpdh", "tp_dh"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _tour(db, ma="LE-2610-401", cho=10, gia=10_000_000.0, fc=20_000_000.0, vc=6_000_000.0):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=HOM_NAY + dt.timedelta(days=20),
             end_date=HOM_NAY + dt.timedelta(days=24), operator_id=_u(db, "nvdh").id,
             status="da_duyet", price_per_pax=gia, fixed_cost=fc, var_cost_per_pax=vc,
             planned_pax=cho, seats_open=cho, rest_stops="x")
    db.add(t); db.commit(); db.refresh(t)
    return t


class _YC:
    def __init__(self, tour_id, pax):
        self.tour_id = tour_id; self.customer_name = "Khách"; self.customer_phone = "0900000000"
        self.source = "web"; self.care_note = "ghi chú chăm sóc"; self.pax = pax
        self.campaign_code = ""; self.promo_code = ""; self.discount = 0


def _ban(db, t, pax):
    """Gửi yêu cầu rồi tạo booking — đúng đường thật của hệ thống."""
    r = T.create_request(db, _u(db, "nvkd"), _YC(t.id, pax))
    return T.create_booking(db, _u(db, "nvdh"), r)


# ───────────────────────── cổng sức chứa ─────────────────────────

def test_sc1_ban_het_cho_thi_dung_lai():
    db = _db(); t = _tour(db, cho=10)
    _ban(db, t, 6)
    _ban(db, t, 4)
    with pytest.raises(Gate) as e:
        _ban(db, t, 1)
    assert "còn 0 chỗ" in str(e.value.detail["message"])


def test_sc2_khong_can_bam_trung_giay_van_chan():
    """Đây là điểm chính: lỗi cũ không phải lỗi đua tranh. Bán TUẦN TỰ cũng vượt được."""
    db = _db(); t = _tour(db, cho=3)
    _ban(db, t, 3)
    with pytest.raises(Gate):
        _ban(db, t, 1)


def test_sc3_cua_gui_yeu_cau_CANH_BAO_chu_khong_chan():
    """Gửi yêu cầu chưa chiếm ghế. Chặn ở đây là chặn nhầm chỗ: yêu cầu gửi lúc tour đầy vẫn có
    nghĩa nếu Điều hành định mở thêm chỗ, hoặc một booking khác sắp hết hạn giữ."""
    db = _db(); t = _tour(db, cho=2)
    _ban(db, t, 2)
    r = T.create_request(db, _u(db, "nvkd"), _YC(t.id, 1))     # KHÔNG ném lỗi
    assert r.id
    canh = db.execute(select(Alert).where(Alert.kind == "vuot_cho")).scalars().all()
    assert canh and "còn 0 chỗ" in canh[0].message
    assert "nv_dh" in canh[0].to_roles and "tp_dh" in canh[0].to_roles


def test_sc4_chua_khai_so_cho_thi_CHO_QUA_va_noi_ra():
    """Ghi chú 2 đầu tệp. `rỗng khác không` — chưa khai không phải là hết chỗ."""
    db = _db(); t = _tour(db, cho=0)
    t.planned_pax = 0; t.seats_open = 0; db.commit()
    assert T._tran_ban(t) is None
    qua, loi = T.kiem_suc_chua(db, t, 50)
    assert qua is True and "chưa khai số chỗ" in loi


def test_sc5_cho_da_het_han_giu_thi_duoc_ban_lai():
    """Booking hết hạn giữ chỗ đã trả ghế về tour (`rules.booked_pax` bỏ qua `giu_cho_het`), nên
    cổng phải thấy chỗ ấy trống. Nếu không thì robot trả chỗ về mà không ai bán lại được."""
    db = _db(); t = _tour(db, cho=2)
    b, _ = _ban(db, t, 2)
    b.giu_cho_het = True; db.commit()
    b2, _ = _ban(db, t, 2)
    assert b2.code != b.code


# ───────────────────────── cửa mở thêm chỗ ─────────────────────────

def test_sc6_mo_them_cho_binh_thuong_thi_qua_va_bien_TANG():
    """Giữ nguyên xe, bán thêm khách: chi phí cố định chia cho nhiều người hơn nên biên tăng."""
    db = _db(); t = _tour(db, cho=10)
    truoc = R.calc(t, 0.10)["margin"]
    T.mo_them_cho(db, _u(db, "nvdh"), t, 20, None, "Đổi sang xe 29 chỗ, giá thuê không đổi")
    assert t.seats_open == 20 and t.planned_pax == 20
    assert R.calc(t, 0.10)["margin"] > truoc


def test_sc7_mo_them_cho_ma_LOI_NHUAN_TUT_thi_CHAN():
    """Chủ tịch quyết 25/9: lợi nhuận tụt thì chặn ngay."""
    db = _db(); t = _tour(db, cho=10, gia=10_000_000.0, fc=20_000_000.0, vc=9_500_000.0)
    with pytest.raises(Gate) as e:
        T.mo_them_cho(db, _u(db, "nvdh"), t, 12, 200_000_000.0,
                      "Đổi sang xe 45 chỗ, giá thuê cao hơn nhiều")
    assert "KHÔNG mở được" in str(e.value.detail["message"])
    assert t.seats_open == 10, "từ chối rồi thì KHÔNG được để lại thay đổi nào trên chuyến"


def test_sc8_chan_theo_CA_HAI_con_so_chu_khong_mot():
    """Hai con số đi ngược chiều nhau được: bán thêm khách làm lợi nhuận TĂNG, xe đắt hơn làm biên
    TỤT. Chặn theo một con số thôi thì lần sau chuyện ngược lại xảy ra và cổng cho qua."""
    db = _db(); t = _tour(db, cho=10, gia=10_000_000.0, fc=10_000_000.0, vc=5_000_000.0)
    truoc = R.calc(t, 0.10)
    # 10 → 20 chỗ, chi phí cố định 10tr → 55tr: lợi nhuận TĂNG (40tr → 45tr) mà biên TỤT (40% → 22,5%)
    t2 = Tour(code="x", name="x", tour_type="le_noi_dia", start_date=t.start_date, end_date=t.end_date,
              operator_id=t.operator_id, price_per_pax=10_000_000.0, fixed_cost=55_000_000.0,
              var_cost_per_pax=5_000_000.0, planned_pax=20)
    sau = R.calc(t2, 0.10)
    assert sau["profit"] > truoc["profit"], "dựng ví dụ sai – lợi nhuận phải TĂNG"
    assert sau["margin"] < truoc["margin"], "dựng ví dụ sai – biên phải TỤT"
    with pytest.raises(Gate) as e:
        T.mo_them_cho(db, _u(db, "nvdh"), t, 20, 55_000_000.0, "Đổi xe to hơn, giá thuê tăng mạnh")
    assert "biên" in str(e.value.detail["message"])


def test_sc9_phai_ghi_ly_do():
    db = _db(); t = _tour(db, cho=10)
    with pytest.raises(Gate) as e:
        T.mo_them_cho(db, _u(db, "nvdh"), t, 20, None, "thêm")
    assert "vì sao" in str(e.value.detail["message"])


def test_sc10_chi_MO_THEM_khong_thu_hep():
    """Thu hẹp số chỗ dưới số đã bán là tạo ra booking không có ghế mà không cửa nào báo cho ai."""
    db = _db(); t = _tour(db, cho=10)
    with pytest.raises(Gate) as e:
        T.mo_them_cho(db, _u(db, "nvdh"), t, 5, None, "Đổi sang xe nhỏ hơn cho rẻ")
    assert "chỉ MỞ THÊM" in str(e.value.detail["message"])


def test_sc11_dung_ba_vai_mo_duoc():
    db = _db()
    for i, ten in enumerate(("nvdh", "tpdh", "sadmin")):
        t = _tour(db, ma=f"LE-2610-41{i}", cho=10)
        T.mo_them_cho(db, _u(db, ten), t, 20, None, "Khách đoàn xin thêm chỗ, xe còn ghế trống")
        assert t.seats_open == 20
    for ten in ("nvkd", "tpkd"):
        t = _tour(db, ma=f"LE-2610-42{ten}", cho=10)
        with pytest.raises(HTTPException):
            T.mo_them_cho(db, _u(db, ten), t, 20, None, "Khách xin thêm chỗ, xe còn ghế trống")


def test_sc12_chi_mo_cho_chuyen_DA_DUYET():
    """Trần bán là con số của dự toán ĐÃ DUYỆT. Chuyến chưa duyệt thì sửa thẳng trong dự toán —
    đi qua cửa này là đi vòng qua bước trình."""
    db = _db(); t = _tour(db, cho=10); t.status = "nhap"; db.commit()
    with pytest.raises(Gate) as e:
        T.mo_them_cho(db, _u(db, "nvdh"), t, 20, None, "Khách xin thêm chỗ, xe còn ghế trống")
    assert "đã duyệt" in str(e.value.detail["message"])


def test_sc13_mo_them_cho_xong_thi_ban_them_duoc():
    """Cả hai cửa phải nói chuyện với nhau: mở trần rồi mà cổng bán vẫn chặn thì cửa mở là vô nghĩa."""
    db = _db(); t = _tour(db, cho=2)
    _ban(db, t, 2)
    with pytest.raises(Gate):
        _ban(db, t, 1)
    T.mo_them_cho(db, _u(db, "sadmin"), t, 5, None, "Khách đoàn xin thêm ba chỗ, xe còn ghế trống")
    b, _ = _ban(db, t, 3)
    assert b.code


def test_sc14_de_lai_dau_vet():
    """Số chỗ nằm trong dự toán đã ký. Sửa nó mà không để lại vết thì người duyệt lần sau không
    biết mình đang nhìn con số của ai."""
    db = _db(); t = _tour(db, cho=10)
    T.mo_them_cho(db, _u(db, "tpdh"), t, 20, None, "Khách đoàn xin thêm chỗ, xe còn ghế trống")
    from app.models.core import AuditLog
    ban = db.execute(select(AuditLog).where(AuditLog.action == "mo_them_cho")).scalars().all()
    assert ban and ban[0].actor == "tpdh"


def test_sc15_cong_bien_va_hai_chu_ky_khong_bi_dung_toi():
    """Lần này đổi việc BÁN và việc MỞ CHỖ, không đổi việc DUYỆT."""
    nguon = open(R.__file__, encoding="utf-8").read()
    assert '("nguong_bien", "0.10"' in nguon
