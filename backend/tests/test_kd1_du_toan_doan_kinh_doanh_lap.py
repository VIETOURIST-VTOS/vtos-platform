"""KD-1 · Kinh doanh Đoàn tự lập dự toán, Sale Admin giữ cổng chuyển — hàng rào, 24/9/2026.

Chủ tịch quyết 24/9: Kinh doanh Đoàn lập dự toán đoàn (kể cả giá vốn), Sale Admin soát rồi mới
chuyển sang Phòng Điều hành. Đây là lần đầu vòng đời dự toán bị đụng tới kể từ khi dựng, nên phép
thử này canh nặng nhất ở chỗ ĐỪNG LÀM HỎNG CÁI CŨ.

    nhap_kd ──(Sale Admin chuyển)──> nhap ──> cho_xac_nhan ──> cho_duyet ──> da_duyet
       ▲                               │
       └──(Sale Admin trả lại)─────────┘

SÁU ĐIỀU PHÉP THỬ NÀY CANH:

 1. TOUR LẺ KHÔNG ĐỔI MỘT DÒNG. ĐH Điều 2 còn nguyên cho mảng lẻ: Kinh doanh không tạo được tour
    lẻ, và tour lẻ do Điều hành tạo vẫn vào thẳng `nhap`.
 2. BƯỚC MỚI NẰM TRƯỚC `nhap`, KHÔNG CẮM NGANG VÀO GIỮA. Chuyển xong phải đổ về đúng `nhap` —
    nếu nó nhảy thẳng sang `cho_xac_nhan` thì chuỗi cổng chặn có hai lối vào, và mọi phép thử
    đang canh chuỗi ấy trở nên vô nghĩa mà không ai biết.
 3. CỔNG CỦA SALE ADMIN LÀ CỔNG THẬT. Thiếu trường thì KHÔNG chuyển được — không phải một lời
    nhắc trên màn hình.
 4. CỔNG ẤY DÙNG LẠI ĐÚNG PHÉP TÍNH CỦA CỔNG BIÊN, không dựng phép kiểm thứ hai.
 5. TRẢ LẠI PHẢI CÓ LÝ DO. Cùng luật đã đặt cho nút đóng cảnh báo 11/9: đóng mà không nói dựa vào
    đâu thì nút đóng là nút giấu việc.
 6. SALE ADMIN VẪN KHÔNG DUYỆT ĐƯỢC. Phần V bản mô tả cấm đích danh, và chuyển ≠ duyệt.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import Gate
from app.db.session import Base
from app.models.core import User
from app.services import access as AC
from app.services import rules as R
from app.services import tours as T
from fastapi import HTTPException

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("sadmin", "sales_admin"),
                     ("nvdh", "nv_dh"), ("tpdh", "tp_dh"), ("ct", "chutich"), ("nvmkt", "nv_mkt")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    for k, v in (("nguong_bien", "0.10"), ("han_qt_doan", "7"), ("han_qt_le", "3")):
        R.set_param(s, k, v) if hasattr(R, "set_param") else None
    return s


def _u(db, ten):
    from sqlalchemy import select
    return db.execute(select(User).where(User.username == ten)).scalars().first()


class _Data:
    """Khuôn dữ liệu vào của `tours.create`, đúng những trường hàm ấy đọc."""
    def __init__(self, ma, loai="doan_noi_dia", **kw):
        self.code = ma
        self.name = kw.get("name", "Đoàn " + ma)
        self.tour_type = loai
        self.start_date = kw.get("start_date", HOM_NAY + dt.timedelta(days=20))
        self.end_date = kw.get("end_date", HOM_NAY + dt.timedelta(days=24))
        self.operator_id = kw.get("operator_id", 4)
        self.price_per_pax = kw.get("price_per_pax", 10_000_000.0)
        self.fixed_cost = kw.get("fixed_cost", 100_000_000.0)
        self.var_cost_per_pax = kw.get("var_cost_per_pax", 6_000_000.0)
        self.planned_pax = kw.get("planned_pax", 50)
        self.rest_stops = kw.get("rest_stops", "")
        self.company_id = None
        self.note = ""
        # Ô bắt buộc thêm ngày 24/9/2026 (xem test_hh1). Khuôn này mặc định TRẢ LỜI "khong" để mọi
        # phép thử bên dưới vẫn đo đúng thứ chúng được viết ra để đo — chuỗi trạng thái, cổng của
        # Sale Admin, luật toàn quyền — chứ không cùng đỏ vì một ô mới.
        # Phép thử của CHÍNH cái ô ấy nằm ở tệp riêng và cố ý bỏ trống nó.
        self.hoa_hong_khach = kw.get("hoa_hong_khach", "khong")
        self.hoa_hong_khach_tien = kw.get("hoa_hong_khach_tien", 0)


# ───────────────────────── 1 · tour lẻ không đổi một dòng ─────────────────────────

def test_kd1_kinh_doanh_KHONG_tao_duoc_tour_le():
    db = _db()
    with pytest.raises(HTTPException) as e:
        T.create(db, _u(db, "nvkd"), _Data("LE-2610-001", loai="le_noi_dia"))
    assert "ĐH Điều 2" in str(e.value.detail), "câu từ chối phải dẫn đúng điều đang chặn"


def test_kd1b_dieu_hanh_tao_tour_le_van_vao_thang_nhap():
    db = _db()
    t = T.create(db, _u(db, "nvdh"), _Data("LE-2610-002", loai="le_noi_dia"))
    assert t.status == "nhap", "tour lẻ không đi qua bước Kinh doanh soạn"


def test_kd1c_dieu_hanh_tao_tour_doan_cung_van_vao_thang_nhap():
    """Điều hành lập dự toán đoàn (đoàn cũ, đoàn họ tự dựng) thì không phải xin Sale Admin chuyển."""
    db = _db()
    t = T.create(db, _u(db, "nvdh"), _Data("MICE-2610-003"))
    assert t.status == "nhap"


# ───────────────────────── 2 · Kinh doanh Đoàn lập, đứng ở nhap_kd ─────────────────────────

def test_kd2_kinh_doanh_tao_duoc_tour_doan_va_dung_o_nhap_kd():
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-004"))
    assert t.status == T.NHAP_KD == "nhap_kd"


def test_kd2b_ca_bon_vai_khoi_kinh_doanh_deu_lap_duoc():
    db = _db()
    for i, vai in enumerate(("nvkd", "tpkd")):
        t = T.create(db, _u(db, vai), _Data(f"MICE-2610-01{i}"))
        assert t.status == T.NHAP_KD


def test_kd2c_vai_ngoai_khoi_kinh_doanh_khong_lap_duoc_tour_doan():
    db = _db()
    with pytest.raises(HTTPException):
        T.create(db, _u(db, "nvmkt"), _Data("MICE-2610-020"))


# ───────────────────────── 3 · cổng của Sale Admin là cổng thật ─────────────────────────

def _du_toan_kd(db, ma="MICE-2610-030", **kw):
    return T.create(db, _u(db, "nvkd"), _Data(ma, **kw))


def test_kd3_du_truong_thi_chuyen_duoc_va_do_ve_DUNG_trang_thai_nhap():
    db = _db()
    t = _du_toan_kd(db)
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "đủ trường")
    assert t.status == "nhap", (
        "chuyển xong phải đổ về ĐÚNG `nhap`. Nhảy thẳng sang cho_xac_nhan là mở lối vào thứ hai "
        "cho chuỗi cổng chặn, và mọi phép thử đang canh chuỗi ấy thành vô nghĩa"
    )


def test_kd4_thieu_gia_von_thi_KHONG_chuyen_duoc():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-031", fixed_cost=0.0, var_cost_per_pax=0.0)
    with pytest.raises(Gate) as e:
        T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    assert "giá vốn" in str(e.value.thong_diep if hasattr(e.value, "thong_diep") else e.value)
    assert t.status == T.NHAP_KD, "bị chặn thì trạng thái phải đứng yên"


def test_kd4b_cau_tu_choi_noi_RO_thieu_gi_chu_khong_noi_chung_chung():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-032", price_per_pax=0.0, planned_pax=0)
    with pytest.raises(Gate) as e:
        T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    nd = str(getattr(e.value, "thong_diep", e.value))
    assert "giá bán" in nd and "số khách" in nd, (
        f"câu từ chối phải gọi tên từng trường thiếu, nhận được: {nd!r}. "
        "Nói 'chưa đủ trường' mà không nói thiếu gì thì người nhận lại phải đoán"
    )


def test_kd5_cong_nay_dung_LAI_phep_tinh_cua_cong_bien_chu_khong_dung_phep_kiem_thu_hai():
    """Ghim CÁCH kiểm, không chỉ ghim kết quả — xem ghi chú 4 ở đầu tệp."""
    import re
    nguon = open(T.__file__, encoding="utf-8").read()
    i = nguon.find("def _thieu_truong_de_chuyen")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    than = re.sub(r'"""[\s\S]*?"""', "", than)
    assert "R.calc(" in than, "phải gọi lại R.calc – cùng phép tính mà cổng biên dùng"
    assert "nguong_bien" in than, "ngưỡng đọc từ tham số, không gõ cứng"


def test_kd5b_diem_dung_nghi_KHONG_bi_doi_o_cong_nay():
    """ĐH Điều 11 giao điểm dừng nghỉ cho Điều hành. Bắt Kinh doanh khai hộ là bắt người không
    biết phải đoán — và một trường khai cho có thì tệ hơn một trường còn trống."""
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-033", rest_stops="")
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    assert t.status == "nhap"


def test_kd5c_nhung_buoc_TRINH_thi_van_doi_diem_dung_nghi_nhu_cu():
    """Nới ở cổng Sale Admin KHÔNG được làm mỏng cổng trình của Điều hành."""
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-034", rest_stops="")
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    with pytest.raises(Gate) as e:
        T.submit(db, _u(db, "nvdh"), t)
    assert "điểm dừng nghỉ" in str(getattr(e.value, "thong_diep", e.value))


# ───────────────────────── 5 · trả lại phải có lý do ─────────────────────────

def test_kd6_tra_lai_khong_co_ly_do_thi_bi_chan():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-040")
    for xau in ("", "  ", "thiếu"):
        with pytest.raises(Gate):
            T.tra_lai_kinh_doanh(db, _u(db, "sadmin"), t, xau)
    assert t.status == T.NHAP_KD


def test_kd6b_tra_lai_co_ly_do_thi_giu_nguyen_trang_thai_nhap_kd():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-041")
    T.tra_lai_kinh_doanh(db, _u(db, "sadmin"), t, "Giá bán thấp hơn bảng giá đã duyệt, xem lại")
    assert t.status == T.NHAP_KD, "trả lại là trả về cho người soạn, không phải đẩy lùi một bước"


# ───────────────────────── 6 · ai được bấm hai cửa ấy ─────────────────────────

def test_kd7_chi_sale_admin_chuyen_duoc():
    db = _db()
    for i, vai in enumerate(("nvkd", "tpkd", "nvdh", "tpdh")):
        t = _du_toan_kd(db, ma=f"MICE-2610-05{i}")
        with pytest.raises(HTTPException):
            T.chuyen_dieu_hanh(db, _u(db, vai), t, "")
        assert t.status == T.NHAP_KD


def test_kd7b_chu_tich_di_qua_duoc_theo_luat_toan_quyen():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-060")
    T.chuyen_dieu_hanh(db, _u(db, "ct"), t, "")
    assert t.status == "nhap"


def test_kd8_sale_admin_VAN_khong_duyet_duoc_du_toan():
    """Phần V bản mô tả cấm đích danh. Chuyển ≠ duyệt, và phép thử này giữ ranh giới ấy."""
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-070", rest_stops="Trạm dừng Tân Phú")
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    T.submit(db, _u(db, "nvdh"), t)
    T.confirm(db, _u(db, "tpdh"), t)
    assert t.status == "cho_duyet"
    with pytest.raises((HTTPException, Gate)):
        T.approve(db, _u(db, "sadmin"), t)
    assert t.status == "cho_duyet", "Sale Admin duyệt được là mất luôn nguyên tắc bốn mắt"


def test_kd8b_ca_chuoi_sau_do_chay_nguyen_ven_toi_da_duyet():
    """Chuỗi cũ phải còn chạy hết. Đây là phép thử quan trọng nhất của cả tệp."""
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-080", rest_stops="Trạm dừng Tân Phú")
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t, "")
    T.submit(db, _u(db, "nvdh"), t)
    T.confirm(db, _u(db, "tpdh"), t)
    assert R.approver_role(t) == "ptgd_doan", "tour đoàn vẫn do P.TGĐ tour đoàn duyệt (Điều 4)"
    assert t.below_margin is False, "biên 40% thì không phải đường hai chữ ký"


# ───────────────────────── 7 · sửa trong bước nháp của Kinh doanh ─────────────────────────

def test_kd9_khoi_kinh_doanh_sua_duoc_trong_buoc_nhap_kd():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-090")

    class D:
        price_per_pax, fixed_cost, var_cost_per_pax, planned_pax = 12_000_000.0, 100_000_000.0, 6_000_000.0, 60
        rest_stops, justification, phien_ban = "", "", None
    T.edit(db, _u(db, "tpkd"), t, D())     # Trưởng phòng rà trước khi Sale Admin chuyển
    assert t.price_per_pax == 12_000_000.0


def test_kd9b_vai_ngoai_khoi_kinh_doanh_khong_sua_duoc_buoc_nhap_kd():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-091")

    class D:
        price_per_pax, fixed_cost, var_cost_per_pax, planned_pax = 1.0, 1.0, 1.0, 1
        rest_stops, justification, phien_ban = "", "", None
    with pytest.raises(HTTPException):
        T.edit(db, _u(db, "nvmkt"), t, D())


def test_kd10_hanh_dong_hien_ra_dung_nguoi_o_buoc_nhap_kd():
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-100")
    assert set(T.allowed_actions(db, t, _u(db, "sadmin"))) >= {"chuyen_dieu_hanh", "tra_lai_kinh_doanh"}
    assert "chuyen_dieu_hanh" not in T.allowed_actions(db, t, _u(db, "nvkd"))
    assert "edit" in T.allowed_actions(db, t, _u(db, "nvkd"))
    assert "submit" not in T.allowed_actions(db, t, _u(db, "nvkd")), (
        "Kinh doanh không trình thẳng – phải qua cổng Sale Admin"
    )


def test_kd11_gia_von_cua_doan_nay_nguoi_ban_xem_duoc():
    """Lập dự toán mà không nhìn thấy giá vốn thì không lập nổi — đây là chỗ nối với quyết định
    mở quyền ngày 24/9, có hàng rào riêng ở test_gv1."""
    db = _db()
    t = _du_toan_kd(db, ma="MICE-2610-110")
    assert AC.can_see_cost_tren_chuyen(_u(db, "nvkd"), t) is True
