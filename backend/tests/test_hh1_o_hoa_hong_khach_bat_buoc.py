"""HH-1 · Ô bắt buộc "hoa hồng dành cho khách" trên dự toán đoàn — hàng rào, 24/9/2026.

Mục 4.2 bản mô tả Sale Admin buộc kiểm hoa hồng và quà tặng dành cho khách đã được đưa vào giá vốn
của chính đoàn ấy chưa. Rủi ro thật, nói thẳng ra: người bán hứa miệng 5% cho khách rồi không ghi
vào dự toán, nên biên kế hoạch in ra đẹp hơn sự thật và cổng 10% mở cho một đoàn lẽ ra không qua.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO LÀ MỘT Ô BẮT BUỘC CHỨ KHÔNG PHẢI MỘT PHÉP TÍNH
═══════════════════════════════════════════════════════════════════════════════════════════════
Phần mềm không nhìn thấy một lời hứa chưa ai viết ra. Không có ô này thì chỗ trống và "không có
hoa hồng" trông giống hệt nhau, và người bỏ trống không phải nói dối lần nào. Có ô này thì bỏ
trống là KHÔNG CHUYỂN ĐƯỢC, còn ghi "không" trong khi đã hứa 5% là một câu nói dối có tên người
và có dấu thời gian.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ NÀY LÀ CHỖ CÁI Ô CÓ RĂNG — VÀ CŨNG LÀ CHỖ NÓ CÓ THỂ THÀNH TRANG TRÍ
═══════════════════════════════════════════════════════════════════════════════════════════════
`rules.calc` đọc giá vốn từ đúng hai con số người lập dự toán gõ (`fixed_cost`,
`var_cost_per_pax`); nó KHÔNG đọc các dòng chi phí chi tiết. Nghĩa là một ô nằm riêng, tự nó,
không chạm được vào cổng biên: người bán khai "có, 124 triệu" rồi vẫn gõ một giá vốn không chứa
124 triệu ấy, và cổng vẫn đo trên con số cũ.

Thứ làm cho nó có răng là `rules.bien_neu_hoa_hong_chua_vao`: một biên THỨ HAI đặt cạnh biên đã
nhập, tính với giả định khoản ấy chưa nằm trong giá vốn. Người ký nhìn thấy cả hai. Phép thử
`test_hh6` và `test_hh7` canh đúng chỗ ấy.

CÁI PHÉP THỬ NÀY KHÔNG CANH ĐƯỢC, nói ra để không ai tưởng đã canh: nó không biết 124 triệu kia
thật sự có nằm trong `fixed_cost` hay không. Không ai biết, kể cả người ký. Cái duy nhất hệ thống
làm được là đặt hai con số cạnh nhau và buộc có một người trả lời.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import Gate
from app.db.session import Base
from app.models.core import User
from app.services import rules as R
from app.services import tours as T

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("sadmin", "sales_admin"), ("nvdh", "nv_dh"),
                     ("tpdh", "tp_dh"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


class _Data:
    """Khuôn dữ liệu vào của `tours.create`. CỐ Ý để `hoa_hong_khach` mặc định RỖNG: tệp này là
    tệp đo chính cái ô ấy, nên nó phải bắt đầu từ trạng thái chưa ai trả lời."""
    def __init__(self, ma, loai="doan_noi_dia", **kw):
        self.code = ma
        self.name = kw.get("name", "Đoàn " + ma)
        self.tour_type = loai
        self.start_date = kw.get("start_date", HOM_NAY + dt.timedelta(days=20))
        self.end_date = kw.get("end_date", HOM_NAY + dt.timedelta(days=24))
        self.operator_id = kw.get("operator_id", 3)
        self.price_per_pax = kw.get("price_per_pax", 10_000_000.0)
        self.fixed_cost = kw.get("fixed_cost", 100_000_000.0)
        self.var_cost_per_pax = kw.get("var_cost_per_pax", 6_000_000.0)
        self.planned_pax = kw.get("planned_pax", 50)
        self.rest_stops = kw.get("rest_stops", "")
        self.company_id = None
        self.note = ""
        self.hoa_hong_khach = kw.get("hoa_hong_khach", "")
        self.hoa_hong_khach_tien = kw.get("hoa_hong_khach_tien", 0)


# ───────────────────────────── cổng chặn ─────────────────────────────

def test_hh1_bo_trong_thi_KHONG_chuyen_duoc():
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-101"))
    assert t.hoa_hong_khach == "", "chuyến mới phải ở trạng thái CHƯA TRẢ LỜI, không mặc định 'khong'"
    with pytest.raises(Gate) as e:
        T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t)
    assert "hoa hồng" in str(e.value.detail).lower(), "câu từ chối phải nói rõ thiếu ô nào"


def test_hh2_tra_loi_khong_thi_qua_duoc():
    """"khong" là một câu trả lời HỢP LỆ. Cổng này không phán đoàn có hoa hồng hay không — nó buộc
    phải có người trả lời."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-102", hoa_hong_khach="khong"))
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t)
    assert t.status == "nhap"


def test_hh3_khai_co_ma_khong_ghi_so_tien_thi_van_chan():
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-103", hoa_hong_khach="co", hoa_hong_khach_tien=0))
    with pytest.raises(Gate):
        T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t)
    thieu = T._thieu_truong_de_chuyen(db, t)
    assert any("số tiền" in x for x in thieu)


def test_hh4_khai_co_kem_so_tien_thi_qua_duoc():
    db = _db()
    t = T.create(db, _u(db, "nvkd"),
                 _Data("MICE-2610-104", hoa_hong_khach="co", hoa_hong_khach_tien=124_000_000.0))
    T.chuyen_dieu_hanh(db, _u(db, "sadmin"), t)
    assert t.status == "nhap" and t.hoa_hong_khach_tien == 124_000_000.0


def test_hh5_tour_LE_khong_bi_doi_o_nay():
    """Cổng này là cổng của phòng Đoàn. Đòi ở tour lẻ là chặn một dây chuyền vì một câu hỏi không
    dành cho nó — và tour lẻ không có ai ở bước này để trả lời."""
    db = _db()
    t = T.create(db, _u(db, "nvdh"), _Data("LE-2610-105", loai="le_noi_dia"))
    assert t.status == "nhap"
    assert not any("hoa hồng" in x.lower() for x in T._thieu_truong_de_chuyen(db, t))


# ───────────────────────────── biên thứ hai ─────────────────────────────

def test_hh6_bien_thu_hai_tinh_dung_va_thap_hon_bien_da_nhap():
    """Doanh thu 500tr, giá vốn 400tr → biên 20%. Hoa hồng khách 50tr chưa vào → biên 10%."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"),
                 _Data("MICE-2610-106", price_per_pax=10_000_000.0, planned_pax=50,
                       fixed_cost=100_000_000.0, var_cost_per_pax=6_000_000.0,
                       hoa_hong_khach="co", hoa_hong_khach_tien=50_000_000.0))
    c = R.calc(t, 0.10)
    assert c["revenue"] == 500_000_000 and c["cost"] == 400_000_000
    assert abs(c["margin"] - 0.20) < 1e-9
    hh = R.bien_neu_hoa_hong_chua_vao(t, c)
    assert abs(hh["bien_neu_chua_vao"] - 0.10) < 1e-9
    assert abs(hh["lech"] - 0.10) < 1e-9
    assert hh["bien_neu_chua_vao"] < c["margin"], "biên thứ hai phải là CẬN DƯỚI, không bao giờ cao hơn"


def test_hh7_khong_khai_co_thi_tra_None_chu_khong_tra_0():
    """0 đọc như một biên bằng không; None đọc đúng là 'không có câu trả lời'. Một màn hình in 0%
    cho một đoàn chưa khai là nói với người ký rằng đoàn ấy hoà vốn."""
    db = _db()
    for khai, tien in (("", 0), ("khong", 0), ("co", 0)):
        t = T.create(db, _u(db, "nvkd"),
                     _Data(f"MICE-2610-10{7 if khai else 8}{tien}{khai or 'x'}",
                           hoa_hong_khach=khai, hoa_hong_khach_tien=tien))
        hh = R.bien_neu_hoa_hong_chua_vao(t, R.calc(t, 0.10))
        assert hh["bien_neu_chua_vao"] is None and hh["lech"] is None


def test_hh8_cai_o_KHONG_tu_cong_vao_gia_von():
    """Cộng sau lưng người lập dự toán thì hai màn hình in hai giá vốn khác nhau cho cùng một
    chuyến, và không ai biết con số nào là con số họ đã gõ."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"),
                 _Data("MICE-2610-109", hoa_hong_khach="co", hoa_hong_khach_tien=50_000_000.0))
    assert t.fixed_cost == 100_000_000.0, "giá vốn phải đúng con số người lập gõ"
    assert R.calc(t, 0.10)["cost"] == 400_000_000, "cổng biên vẫn đo trên giá vốn đã nhập"


# ───────────────────────────── giữ câu trả lời ─────────────────────────────

def test_hh9_sua_dự_toan_ma_khong_gui_o_nay_thi_KHONG_xoa_cau_tra_loi():
    """Màn hình cũ chưa có ô này vẫn gửi chuỗi rỗng ở mọi lần sửa. Rỗng mà ghi đè thì một người
    sửa điểm dừng nghỉ sẽ lặng lẽ xoá câu trả lời của người khác."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-110", hoa_hong_khach="co",
                                           hoa_hong_khach_tien=30_000_000.0))

    class _Sua:
        phien_ban = None
        price_per_pax, fixed_cost, var_cost_per_pax, planned_pax = 10_000_000.0, 100_000_000.0, 6_000_000.0, 50
        rest_stops, justification = "Trạm Hải Dương", ""
        hoa_hong_khach, hoa_hong_khach_tien = "", 0

    T.edit(db, _u(db, "nvkd"), t, _Sua())
    assert t.hoa_hong_khach == "co" and t.hoa_hong_khach_tien == 30_000_000.0


def test_hh10_doi_tu_co_sang_khong_thi_so_tien_ve_RONG_chu_khong_ve_0():
    """Để lại 30 triệu dưới một câu trả lời "không" là để lại một con số mồ côi mà màn hình sau sẽ
    đọc ra theo cách của nó.

    Và nó về RỖNG chứ không về 0: 0 đồng đọc như "đã khai là 0", khác hẳn "không áp dụng". Đây là
    đúng chỗ hàng rào K2 (`test_kt12`) canh — một cột tiền mặc định 0 và không cho rỗng thì "chưa
    nhập" bị ghi thành 0, và không ai còn phân biệt được hai thứ ấy.
    """
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-111", hoa_hong_khach="co",
                                           hoa_hong_khach_tien=30_000_000.0))

    class _Sua:
        phien_ban = None
        price_per_pax, fixed_cost, var_cost_per_pax, planned_pax = 10_000_000.0, 100_000_000.0, 6_000_000.0, 50
        rest_stops, justification = "", ""
        hoa_hong_khach, hoa_hong_khach_tien = "khong", 0

    T.edit(db, _u(db, "nvkd"), t, _Sua())
    assert t.hoa_hong_khach == "khong" and t.hoa_hong_khach_tien is None


def test_hh11_gia_tri_la_bi_tu_choi_thang():
    """Một chuỗi không đọc được nằm trong cột này làm cổng chuyển đọc ra 'chưa trả lời' mãi mãi, và
    người dùng thấy mình đã điền rồi mà máy vẫn chặn."""
    db = _db()
    with pytest.raises(Gate):
        T.create(db, _u(db, "nvkd"), _Data("MICE-2610-112", hoa_hong_khach="co_le"))


# ───────────────────────────── để lại vết ─────────────────────────────

def test_hh12_cau_tra_loi_di_vao_nhat_ky_kiem():
    """Một ô bắt buộc mà không để lại vết đổi thì đổi lúc nào cũng được, và cái nó chặn chỉ còn là
    sự bất tiện."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-113", hoa_hong_khach="khong"))
    s = T.snap(t)
    assert "hoa_hong_khach" in s and "hoa_hong_khach_tien" in s


def test_hh13_man_hinh_doc_duoc_ca_hai_bien():
    """Người ký phải thấy CẢ HAI con số. Thiếu con số thứ hai thì cái ô chỉ còn là một lời khai
    không ai đối chiếu."""
    db = _db()
    t = T.create(db, _u(db, "nvkd"), _Data("MICE-2610-114", hoa_hong_khach="co",
                                           hoa_hong_khach_tien=50_000_000.0))
    v = T.tour_view(db, t)
    assert v["hoa_hong_khach"] == "co"
    assert v["hoa_hong_khach_bien"]["bien_neu_chua_vao"] is not None
    assert v["hoa_hong_khach_bien"]["bien_neu_chua_vao"] < v["calc"]["margin"]


def test_hh14_cong_bien_va_hai_chu_ky_khong_bi_dung_toi():
    """Lần thêm ô này đổi việc KHAI, không đổi việc DUYỆT."""
    nguon = open(R.__file__, encoding="utf-8").read()
    assert '("nguong_bien", "0.10"' in nguon, "ngưỡng biên kế hoạch phải còn nguyên 10%"
