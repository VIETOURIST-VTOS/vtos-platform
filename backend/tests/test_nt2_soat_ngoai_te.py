"""NT-2 · Soát ngoại tệ trên dòng giá vốn — Chủ tịch quyết 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHUYỆN PHÉP THỬ NÀY CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
Bảng `tour_cost_lines` có HAI cửa ghi, và tới 27/9/2026 chúng hiểu ô "số tiền gốc" ngược nhau:

    settlement.py          so_tien_goc = ĐƠN GIÁ  → actual = goc × tỷ giá × số lượng × hệ số
    quyet_toan_lop3.py     so_tien_goc = TỔNG     → actual = goc × tỷ giá  (bỏ số lượng, hệ số)

Đo bằng đúng ví dụ mà chú thích trong `models/vietrip.py` tự nêu — land 692,34 GBP × 43 khách,
tỷ giá 36.000 — hai cửa lệch nhau **1.046.818.080 đ trên MỘT dòng**.

Chủ tịch chốt: "số tiền gốc" là ĐƠN GIÁ MỘT ĐƠN VỊ. Cửa lớp 3 là cửa sai.

Bộ soát này ĐO, không sửa. Bốn điều phải canh:

 1. Con số lệch phải ĐÚNG. Một bộ soát báo sai số lệch còn tệ hơn không có bộ soát — người ta sẽ
    đi sửa dữ liệu thật theo con số nó in ra.
 2. Nhóm "không phân biệt được" phải ĐỨNG RIÊNG, không gộp vào "đúng". Số lượng × hệ số = 1 thì
    hai quy ước cho cùng một số; dòng ấy hôm nay không sai nhưng KHÔNG chứng minh được gì, và
    ngày người ta sửa số lượng từ 1 lên 43 thì nó đi sai mà không ai chạm vào ô ngoại tệ.
 3. Bộ soát KHÔNG được sửa một dòng dữ liệu nào.
 4. Sổ RỖNG phải nói ra là rỗng. Một bảng toàn số 0 đọc y hệt "đã sạch".
"""
import datetime as dt

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.models.vietrip import TourCostLine
from app.services import soat_ngoai_te as NT

HOM_NAY = dt.date.today()

# Con số thật của tệp UK, chép từ chú thích trong models/vietrip.py.
GBP, PAX, TY_GIA = 692.34, 43, 36000.0
DUNG = 1_071_742_320.0        # 692,34 × 36.000 × 43
SAI = 24_924_240.0            # 692,34 × 36.000  (cửa lớp 3: số lượng biến mất)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    s.add(User(username="nvdh", full_name="nvdh", role="nv_dh", password_hash="x"))
    s.commit()
    t = Tour(code="MICE-UK-01", name="UK", tour_type="doan_nuoc_ngoai",
             start_date=HOM_NAY, end_date=HOM_NAY, operator_id=1, status="ket_thuc",
             price_per_pax=0, planned_pax=PAX, seats_open=PAX)
    s.add(t); s.commit()
    return s, t


def _dong(db, t, **kw):
    d = dict(tour_id=t.id, line_no=(len(db.execute(select(TourCostLine)).scalars().all()) + 1),
             description="Land tour", supplier_name="NCC UK", cost_kind="theo_khach",
             tien_te="GBP", so_tien_goc=GBP, ty_gia=TY_GIA, ngay_ty_gia=HOM_NAY,
             qty=PAX, coef=1, source="vtos", status="hd", updated_by="nvdh")
    d.update(kw)
    l = TourCostLine(**d)
    db.add(l); db.commit(); db.refresh(l)
    return l


# ───────────────────────── con số lệch phải đúng ─────────────────────────

def test_nt2_dong_ghi_theo_cua_dieu_hanh_la_DUNG():
    db, t = _db()
    l = _dong(db, t, unit_price=round(GBP * TY_GIA, 2), actual=DUNG)
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "dung" and kq["lech"] == 0.0
    assert NT.quy_uoc_don_gia(l) == "vnd"


def test_nt2_dong_ghi_theo_cua_lop3_bat_dung_so_lech():
    """Phép thử quan trọng nhất của tệp: con số bộ soát in ra là con số người ta sẽ đi sửa."""
    db, t = _db()
    l = _dong(db, t, unit_price=GBP, actual=SAI)      # lớp 3: unit_price giữ đồng GỐC
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "sai_bo_nhan"
    assert kq["actual_dung"] == DUNG
    assert kq["lech"] == round(DUNG - SAI) == 1_046_818_080
    assert NT.quy_uoc_don_gia(l) == "dong_goc"


def test_nt2_he_so_cung_duoc_tinh_khong_chi_so_luong():
    """2 đêm khách sạn cho 43 khách: hệ số cũng là một phép nhân bị bỏ."""
    db, t = _db()
    l = _dong(db, t, coef=2, unit_price=GBP, actual=SAI)
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "sai_bo_nhan" and kq["actual_dung"] == DUNG * 2


def test_nt2_dong_co_dinh_ghi_theo_calc_actual_van_la_DUNG():
    """`co_dinh` với `calc_actual` là chi phí cả đoàn — chỉ nhân hệ số, không nhân số khách."""
    db, t = _db()
    l = _dong(db, t, cost_kind="co_dinh", qty=PAX, coef=1,
              unit_price=round(GBP * TY_GIA, 2), actual=round(GBP * TY_GIA))
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "dung" and kq["phep_nhan"] == "theo_cost_kind"


def test_nt2_dong_lop3_co_cost_kind_SAI_van_phai_xep_la_DUNG():
    """Hàng rào của một lỗi bắt được ngày 27/9/2026, trong chính bộ soát này.

    Cửa `quyet_toan_lop3.py::/{tid}/chi` nhân `đơn giá × số lượng × hệ số` NHƯNG KHÔNG đặt
    `cost_kind`, nên mọi dòng nó ghi đều mang mặc định `"co_dinh"` — cột nói "đừng nhân số khách"
    trong khi cửa đã nhân. Bản đầu của bộ soát tin cột ấy, nên nó xếp NHẦM đúng nhóm dòng nó sinh
    ra để bắt: dòng ghi ĐÚNG quy ước bị gọi là `khong_khop_ca_hai`.

    Nay bộ soát thử CẢ HAI phép nhân và nói ra cái nào khớp."""
    db, t = _db()
    l = _dong(db, t, cost_kind="co_dinh", qty=PAX, coef=1,
              unit_price=round(GBP * TY_GIA, 2), actual=DUNG)
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "dung", "dòng lớp 3 ghi đúng quy ước bị xếp nhầm"
    assert kq["phep_nhan"] == "nhan_ca_so_luong"


# ───────────── nhóm "không phân biệt được" phải đứng riêng ─────────────

def test_nt2_nhan_bang_mot_thi_KHONG_goi_la_dung():
    """Một khách, hệ số 1 — hai quy ước cho cùng một số. Gộp vào `dung` là tự cho mình một bản đo
    đẹp hơn sự thật: dòng ấy không chứng minh được người nhập hiểu ô kia theo nghĩa nào."""
    db, t = _db()
    l = _dong(db, t, qty=1, coef=1, unit_price=round(GBP * TY_GIA, 2), actual=round(GBP * TY_GIA))
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "khong_phan_biet_duoc"
    assert kq["nhom"] != "dung"


# ───────────────────────── các nhóm còn lại ─────────────────────────

def test_nt2_thieu_ty_gia_thi_khong_quy_doi_duoc_chu_khong_phai_sai():
    db, t = _db()
    l = _dong(db, t, ty_gia=None, unit_price=GBP, actual=SAI)
    kq = NT.xep_loai(l)
    assert kq["nhom"] == "thieu_o" and kq["lech"] is None


def test_nt2_dong_kho_cu_ghi_thang_khong_khop_quy_uoc_nao():
    """Bộ nạp kho cũ ghi thẳng vào bảng, không đi qua cửa nào — phải hiện ra chứ không im."""
    db, t = _db()
    l = _dong(db, t, unit_price=123.0, actual=999_999.0, source="kho_cu")
    assert NT.xep_loai(l)["nhom"] == "khong_khop_ca_hai"


def test_nt2_dong_VND_khong_vao_so_soat():
    db, t = _db()
    _dong(db, t, tien_te="VND", so_tien_goc=None, ty_gia=None, unit_price=1000, actual=43000)
    _dong(db, t, tien_te=None, so_tien_goc=None, ty_gia=None, unit_price=1000, actual=43000)
    assert NT.bang(db)["tong_dong_ngoai_te"] == 0


# ───────────────────────── bảng tổng ─────────────────────────

def test_nt2_bang_cong_dung_va_chi_in_dong_can_nguoi_nhin():
    db, t = _db()
    _dong(db, t, unit_price=round(GBP * TY_GIA, 2), actual=DUNG)          # đúng
    _dong(db, t, unit_price=GBP, actual=SAI)                              # sai
    _dong(db, t, unit_price=GBP, actual=SAI)                              # sai
    b = NT.bang(db)
    assert b["tong_dong_ngoai_te"] == 3
    assert b["dem"]["dung"] == 1 and b["dem"]["sai_bo_nhan"] == 2
    assert b["tong_lech"] == round((DUNG - SAI) * 2)
    assert len(b["rows"]) == 2, "dòng đúng không được nằm trong danh sách phải nhìn"
    assert b["don_gia_dang_mang"] == {"vnd": 1, "dong_goc": 2,
                                      "khong_khop_ca_hai": 0, "khong_do_duoc": 0}


def test_nt2_so_RONG_phai_noi_ra_la_rong():
    db, _ = _db()
    b = NT.bang(db)
    assert b["tong_dong_ngoai_te"] == 0
    assert "chưa ai nhập" in b["luu_y"], "một bảng toàn số 0 đọc y hệt 'đã sạch'"


def test_nt2_bo_soat_KHONG_sua_mot_dong_du_lieu_nao():
    """Bộ soát chạy trên dữ liệu thật của công ty. Nó phải là chỉ-đọc, và phải chứng minh được."""
    db, t = _db()
    l = _dong(db, t, unit_price=GBP, actual=SAI)
    truoc = (l.actual, l.unit_price, l.so_tien_goc, l.ty_gia, l.qty, l.coef)
    NT.bang(db)
    db.refresh(l)
    assert (l.actual, l.unit_price, l.so_tien_goc, l.ty_gia, l.qty, l.coef) == truoc


def test_nt2_moi_nhom_deu_co_ten_bang_loi():
    """Mã nhóm in ra màn hình mà không có tên tiếng Việt thì người đọc phải đi tra mã nguồn."""
    db, t = _db()
    _dong(db, t, unit_price=GBP, actual=SAI)
    b = NT.bang(db)
    assert set(b["dem"]) == set(b["nhom_ten"])
    for ten in b["nhom_ten"].values():
        assert len(ten) >= 10
    assert all(r["nhom_ten"] for r in b["rows"])


def test_nt2_dung_chung_calc_actual_voi_cua_thuc():
    """Bộ soát phải hỏi CHÍNH hàm mà cửa ghi dùng, không chép lại phép nhân.

    Hai bản chép của một phép tính thì sớm muộn lệch nhau — và ngày chúng lệch, bộ soát sẽ báo
    sai chính cái nó sinh ra để canh. Phép nhân `theo_cost_kind` phải đi qua `calc_actual`; phép
    nhân thứ hai là của cửa lớp 3 và cố ý khai riêng (xem `phep_nhan`)."""
    import inspect
    than = inspect.getsource(NT.phep_nhan)
    assert "calc_actual" in than
    assert "theo_khach" not in than, "bộ soát đang tự phân biệt cách tính thay vì gọi calc_actual"


# ═════════ NGOẠI TỆ ẨN VÀ QUY MÔ CỦA NHÓM `thieu_o` — thêm 27/9/2026 sau lần đo THẬT ═════════
#
# Lần đo đầu tiên trên dữ liệu thật trả về 61 dòng, TẤT CẢ đều `thieu_o`, `tong_lech` = 0 và
# `actual` = 0. Hai chỗ hở lộ ra ngay từ con số ấy, và cả hai đều làm bảng đọc NHẸ HƠN sự thật:
#
#   1. `tong_lech` = 0 đọc y hệt "không mất gì", trong khi thật ra là "không đo được vì chưa có
#      tỷ giá" — mà 61 dòng ấy đang ghi giá vốn bằng 0.
#   2. Câu truy vấn chỉ lấy dòng CÓ ô `tien_te`. Kho cũ để đồng tiền trong CÂU MÔ TẢ, nên dòng nào
#      bộ nạp không điền được ô ấy thì bộ soát không thấy — và 61 là con số thấp hơn sự thật.

def test_nt2_chua_co_ty_gia_thi_CONG_SO_NGOAI_TE_de_biet_quy_mo():
    """`tong_lech` = 0 mà 61 dòng ghi giá vốn 0 là một bảng nói dối bằng cách im lặng."""
    db, t = _db()
    _dong(db, t, ty_gia=None, unit_price=None, actual=0)          # 692,34 × 43 khách
    _dong(db, t, ty_gia=None, cost_kind="co_dinh", coef=2, unit_price=None, actual=0)
    b = NT.bang(db)
    assert b["dem"]["thieu_o"] == 2 and b["tong_lech"] == 0
    assert b["chua_quy_doi"]["GBP"] == round(GBP * PAX + GBP * 2, 2)
    assert "đừng đọc" in b["luu_y"]


def test_nt2_dong_NOI_minh_la_ngoai_te_trong_mo_ta_ma_o_tien_te_bo_trong():
    """Hình thật của kho cũ: "Phí LSQ Phí (CAD) – NGUYEN TUYET NHI", ô `tien_te` rỗng."""
    db, t = _db()
    _dong(db, t, tien_te="", so_tien_goc=None, ty_gia=None,
          description="Phí LSQ Phí (CAD) – NGUYEN TUYET NHI", unit_price=0, actual=0)
    b = NT.bang(db)
    assert b["tong_dong_ngoai_te"] == 0, "dòng không khai tien_te thì không vào sổ xếp loại"
    assert b["ngoai_te_an"]["tong"] == 1
    assert b["ngoai_te_an"]["theo_dong_tien"] == {"CAD": 1}
    assert b["ngoai_te_an"]["rows"][0]["doan_la"] == "CAD"


def test_nt2_ngoai_te_an_KHONG_xep_loai_va_KHONG_ket_luan_sai():
    """Phép dò bằng câu chữ thì thô. Nó nói "cần người nhìn", không nói "dòng này sai"."""
    db, t = _db()
    _dong(db, t, tien_te="", so_tien_goc=None, ty_gia=None, description="Vé USD Airlines",
          unit_price=0, actual=0)
    r = NT.bang(db)["ngoai_te_an"]["rows"][0]
    assert "nhom" not in r and "lech" not in r and "actual_dung" not in r


@pytest.mark.parametrize("chu,thay", [
    ("Phí LSQ Phí (CAD)", "CAD"),
    ("Thanh toán USD cho NCC", "USD"),
    ("Land AUD 436.2", "AUD"),
    ("Xe đưa đón nội thành", ""),        # không có mã nào
    ("Khách sạn CADILLAC", ""),          # CAD nằm trong một từ dài hơn – không phải đồng tiền
    ("USDA chứng nhận", ""),
])
def test_nt2_do_ma_dong_tien_dung_nhu_MOT_TU_rieng(chu, thay):
    """“CADILLAC” chứa “CAD”. Dò bằng chuỗi con thì mỗi khách sạn thành một khoản ngoại tệ."""
    db, t = _db()
    l = _dong(db, t, description=chu, supplier_name="")
    assert NT.dong_tien_trong_chu(l) == thay


def test_nt2_dong_da_khai_tien_te_KHONG_bi_dem_hai_lan():
    db, t = _db()
    _dong(db, t, description="Land tour (GBP)")
    b = NT.bang(db)
    assert b["tong_dong_ngoai_te"] == 1 and b["ngoai_te_an"]["tong"] == 0


def test_nt2_dem_theo_trang_thai_de_biet_dong_nao_da_huy():
    """Một dòng đã huỷ không đi vào giá vốn. Gộp nó vào con số báo lên Chủ tịch là thổi phồng."""
    db, t = _db()
    _dong(db, t, unit_price=GBP, actual=SAI)
    _dong(db, t, unit_price=GBP, actual=SAI, status="huy")
    b = NT.bang(db)
    assert b["theo_trang_thai"] == {"hd": 1, "huy": 1}
    assert b["theo_nguon"] == {"vtos": 2}


def test_nt2_dem_CAP_dong_tien_x_ngay_chu_khong_dem_dong():
    """61 dòng của 10 chuyến chỉ cần chừng mươi con số tỷ giá, không phải 61 lần gõ. Đếm CẶP là
    cách duy nhất nói đúng khối lượng việc cho người sắp phải làm nó."""
    db, t = _db()
    _dong(db, t, ty_gia=None, unit_price=None, actual=0)
    _dong(db, t, ty_gia=None, unit_price=None, actual=0)       # cùng chuyến, cùng GBP → MỘT cặp
    b = NT.bang(db)
    assert b["can_ty_gia"] == [{"tien_te": "GBP", "ngay": HOM_NAY.isoformat()}]


def test_nt2_row_mang_TRANG_THAI_CHUYEN_va_NGAY_KHOI_HANH():
    """Chuyến đã đóng số thì KHÔNG ai được nắn lặng lẽ — người đọc bảng phải thấy điều đó ngay trên
    dòng, không phải đi mở từng chuyến."""
    db, t = _db()
    _dong(db, t, ty_gia=None, unit_price=None, actual=0)
    r = NT.bang(db)["rows"][0]
    assert r["trang_thai_chuyen"] == "ket_thuc"
    assert r["ngay_khoi_hanh"] == HOM_NAY
    assert r["trang_thai_dong"] == "hd"
