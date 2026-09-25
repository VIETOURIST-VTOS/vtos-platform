"""NT-1 · Cửa nhập ngoại tệ trên dòng giá vốn — hàng rào, 25/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
ĐÂY LÀ MỘT CỬA, KHÔNG PHẢI MỘT CỘT MỚI — VÀ ĐÓ LÀ ĐIỂM CHÍNH
═══════════════════════════════════════════════════════════════════════════════════════════════
Bốn cột `tien_te`, `so_tien_goc`, `ty_gia`, `ngay_ty_gia` đã nằm trên `TourCostLine` từ lâu
(`models/vietrip.py:89-92`). Chỗ thiếu là `settlement.validate()` dựng dữ liệu từ một danh sách
trường cố định và bốn tên ấy không có trong danh sách — nên `add_line`/`update_line` chưa bao giờ
ghi chúng.

Hệ quả đo được: chuyến nước ngoài NẠP TỪ KHO CŨ có số gốc và tỷ giá (bộ nạp ghi thẳng vào bảng);
chuyến nước ngoài SOẠN MỚI trên VTOS thì không. Một sổ, hai loại dòng, và không có gì nói cho
người đọc biết mình đang nhìn loại nào.

Ranh giới Chủ tịch chốt 09/9/2026: mỗi con số cần một cửa nhập; không có cửa thì đó là việc còn
thiếu, không phải việc để bộ nạp làm hộ.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÀ MỘT ĐIỀU TỆP NÀY KHÔNG CANH ĐƯỢC, NÓI RA ĐỂ KHÔNG AI TƯỞNG ĐÃ CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
Nó không biết tỷ giá người nhập gõ có đúng tỷ giá ngày ấy hay không. Không ai biết — kể cả sổ tỷ
giá, vì sổ cũng do người nhập. Cái duy nhất hệ thống làm được là buộc ba con số đi cùng nhau và
để lại dấu vết, rồi làm lộ ra khi hai người khai hai tỷ giá khác nhau cho cùng một ngày. Việc ấy
thuộc sổ tỷ giá, không thuộc tệp này.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.models.vietrip import TourCostLine
from app.services import settlement as ST
from app.services.settlement import Gate   # settlement khai Gate RIÊNG, không dùng app.api.deps.Gate

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvdh", "nv_dh"), ("tpdh", "tp_dh"), ("ketoan", "ketoan")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _tour(db, ma="MICE-2610-301", trang_thai="da_duyet"):
    u = _u(db, "nvdh")
    t = Tour(code=ma, name=ma, tour_type="doan_nuoc_ngoai", start_date=HOM_NAY - dt.timedelta(days=10),
             end_date=HOM_NAY - dt.timedelta(days=5), operator_id=u.id, status=trang_thai,
             price_per_pax=20_000_000.0, planned_pax=30, settlement_version=1)
    db.add(t); db.commit(); db.refresh(t)
    return t


DONG = {"description": "Land Bangkok 4N3D", "service_type": "LAND", "cost_kind": "theo_khach",
        "supplier_name": "Siam Travel Co", "qty": 30, "coef": 1}


# ───────────────────────── đường VND: không đổi một dòng nào ─────────────────────────

def test_nt1_dong_tien_dong_khong_bi_doi_gi():
    """Tuyệt đại đa số dòng giá vốn là tiền đồng. Bắt chúng khai `tien_te = "VND"` là thêm một ô
    bắt buộc cho hàng nghìn dòng để phục vụ vài chục dòng."""
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "unit_price": 3_000_000})
    assert l.unit_price == 3_000_000 and l.actual == 90_000_000
    assert l.tien_te is None and l.so_tien_goc is None and l.ty_gia is None


def test_nt1b_khai_thang_VND_cung_khong_doi_gi():
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "unit_price": 3_000_000, "tien_te": "VND"})
    assert l.unit_price == 3_000_000
    assert l.tien_te is None, "khai VND thì không cần lưu gì — rỗng đọc đúng là 'tiền đồng'"


# ───────────────────────── đường ngoại tệ: đủ ba ô hoặc không qua ─────────────────────────

def test_nt2_khai_ngoai_te_du_ba_o_thi_qua_va_MAY_NHAN():
    """Người gõ số gốc và tỷ giá; số VND là số SUY RA. Gõ tay cả ba là mở đường cho ba con số
    không khớp nhau — chính câu `models/ty_gia.py` đã ghi."""
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "unit_price": 999,   # cố ý gõ sai
                                            "tien_te": "THB", "so_tien_goc": 4_500,
                                            "ty_gia": 700.0, "ngay_ty_gia": "2026-09-20"})
    assert l.tien_te == "THB" and float(l.so_tien_goc) == 4_500
    assert l.unit_price == 4_500 * 700, "đơn giá VND phải là số MÁY NHÂN, không phải số người gõ"
    assert l.actual == 4_500 * 700 * 30
    assert l.ngay_ty_gia == dt.date(2026, 9, 20)


@pytest.mark.parametrize("thieu,chu", [
    ({"so_tien_goc": 0}, "đồng gốc"),
    ({"ty_gia": 0}, "tỷ giá"),
    ({"ngay_ty_gia": ""}, "ngày tỷ giá"),
])
def test_nt3_khai_ngoai_te_ma_thieu_mot_o_thi_TU_CHOI(thieu, chu):
    """Một số tiền USD không có tỷ giá là con số không quy đổi được; một tỷ giá không có ngày là
    con số không kiểm lại được. Từ chối ngay tại cửa, đừng để nó nằm trong sổ."""
    db = _db(); t = _tour(db)
    d = {**DONG, "tien_te": "USD", "so_tien_goc": 1_200, "ty_gia": 25_400.0,
         "ngay_ty_gia": "2026-09-20", **thieu}
    with pytest.raises(Gate) as e:
        ST.add_line(db, _u(db, "nvdh"), t, d)
    assert chu in str(e.value.detail).lower() or chu in str(e.value.detail)


def test_nt4_ngay_ty_gia_doc_khong_ra_thi_tu_choi_chu_khong_doan():
    db = _db(); t = _tour(db)
    with pytest.raises(Gate) as e:
        ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "tien_te": "USD", "so_tien_goc": 1_200,
                                            "ty_gia": 25_400.0, "ngay_ty_gia": "20/09/2026"})
    assert "không đọc được" in str(e.value.detail)


def test_nt5_dong_tien_la_van_nhap_duoc():
    """`models/ty_gia.py` nói rõ danh sách đồng tiền là để GỢI Ý, không để chặn: gặp đồng lạ mà
    chặn là đẩy người dùng sang gõ tay ra ngoài hệ."""
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "tien_te": "mmk", "so_tien_goc": 2_000_000,
                                            "ty_gia": 0.012, "ngay_ty_gia": "2026-09-20"})
    assert l.tien_te == "MMK", "viết thường thì chuẩn hoá thành viết hoa, không từ chối"


# ───────────────────────── sửa dòng: đừng xoá trắng ─────────────────────────

def test_nt6_sua_dong_ma_khong_gui_o_ngoai_te_thi_KHONG_xoa_trang():
    """Màn hình cũ chưa có bốn ô này vẫn gửi lên form thiếu chúng ở mọi lần sửa. Rỗng mà ghi đè
    thì một người sửa ghi chú sẽ lặng lẽ xoá số gốc của người khác — cùng bài học với ô hoa hồng
    khách ngày 24/9."""
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "tien_te": "USD", "so_tien_goc": 1_200,
                                            "ty_gia": 25_400.0, "ngay_ty_gia": "2026-09-20"})
    ST.update_line(db, _u(db, "nvdh"), t, l, {**DONG, "unit_price": l.unit_price, "note": "đã đối chiếu"})
    assert l.tien_te == "USD" and float(l.so_tien_goc) == 1_200, "số gốc phải còn nguyên"


def test_nt7_doi_ty_gia_thi_don_gia_VND_tinh_lai():
    db = _db(); t = _tour(db)
    l = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "tien_te": "USD", "so_tien_goc": 1_000,
                                            "ty_gia": 25_000.0, "ngay_ty_gia": "2026-09-20"})
    assert l.unit_price == 25_000_000
    ST.update_line(db, _u(db, "nvdh"), t, l, {**DONG, "tien_te": "USD", "so_tien_goc": 1_000,
                                              "ty_gia": 25_400.0, "ngay_ty_gia": "2026-09-21"})
    assert l.unit_price == 25_400_000 and l.ngay_ty_gia == dt.date(2026, 9, 21)


# ───────────────────────── màn hình đọc được ─────────────────────────

def test_nt8_cua_doc_tra_ve_ca_bon_o_KE_CA_KHI_RONG():
    """Trả về cả khi rỗng để màn hình phân biệt "dòng tiền đồng" với "dòng ngoại tệ chưa ai khai"
    — hai thứ khác nhau, gộp lại thì không nhìn ra dòng nào cần đi hỏi."""
    db = _db(); t = _tour(db)
    vnd = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "unit_price": 1_000_000})
    usd = ST.add_line(db, _u(db, "nvdh"), t, {**DONG, "tien_te": "USD", "so_tien_goc": 100,
                                              "ty_gia": 25_400.0, "ngay_ty_gia": "2026-09-20"})
    for o in (ST.line_out(vnd), ST.line_out(usd)):
        for k in ("tien_te", "so_tien_goc", "ty_gia", "ngay_ty_gia"):
            assert k in o
    assert ST.line_out(vnd)["tien_te"] is None
    assert ST.line_out(usd)["tien_te"] == "USD" and ST.line_out(usd)["ty_gia"] == 25_400.0


# ───────────────────────── không phá luật đã có ─────────────────────────

def test_nt9_cong_MOT_CUA_khong_bi_dung_toi():
    """Lần mở cửa này đổi việc KHAI, không đổi việc AI ĐƯỢC KHAI."""
    db = _db(); t = _tour(db)
    with pytest.raises(Gate) as e:
        ST.add_line(db, _u(db, "tpdh"), t, {**DONG, "unit_price": 1_000_000})
    assert "Một cửa" in str(e.value.detail["message"])


def test_nt10_KHONG_tu_tra_so_ty_gia():
    """Sổ tỷ giá chỉ ĐIỀN SẴN vào form; máy không chọn hộ. Tỷ giá của một khoản là tỷ giá NGÀY CHI
    THẬT của khoản ấy — một sự thật đã xảy ra, không được sửa lùi khi sổ đổi. Luật ấy đã viết
    trong `models/ty_gia.py`; phép thử này canh chỗ không phá nó."""
    import re
    nguon = open(ST.__file__, encoding="utf-8").read()
    i = nguon.find("def _ngoai_te")
    than = re.sub(r'"""[\s\S]*?"""', "", nguon[i:nguon.find("\ndef validate", i)])
    than = re.sub(r"#[^\n]*", "", than)
    for cam in ("TyGia", "ty_gia_ngay", "tra_so_ty_gia"):
        assert cam not in than, f"cửa nhập tự tra sổ tỷ giá ({cam}) — máy đang chọn hộ người"


def test_nt11_bon_cot_van_la_bon_cot_cu_khong_phai_cot_moi():
    """Nếu một ngày ai đó thêm `loai_tien` hay `currency` bên cạnh `tien_te`, sẽ có hai cột cùng
    nói một việc và hai màn hình đọc hai cột khác nhau. Khoá tên lại."""
    cot = {c.name for c in TourCostLine.__table__.columns}
    for c in ("tien_te", "so_tien_goc", "ty_gia", "ngay_ty_gia"):
        assert c in cot
    for c in ("loai_tien", "currency", "exchange_rate"):
        assert c not in cot, f"cột {c} trùng nghĩa với cột đã có — kho này gọi nó là tien_te"
