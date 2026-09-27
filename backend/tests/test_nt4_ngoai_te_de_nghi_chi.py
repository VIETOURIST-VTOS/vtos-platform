"""NT-4 · Ngoại tệ trên ĐỀ NGHỊ CHI, và chênh lệch tỷ giá đứng riêng — Chủ tịch chốt 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ NÀY LÀ TIỀN THẬT RỜI NGÂN HÀNG
═══════════════════════════════════════════════════════════════════════════════════════════════
Ngày 27/9/2026 mới sửa xong hai cửa ghi DÒNG GIÁ VỐN về một quy ước (NT-2, NT-3). Nhưng bảng
`payment_requests` — chỗ sinh ra lệnh chuyển tiền — vẫn chỉ có MỘT ô tiền: `amount`, đồng Việt Nam.
Trả nhà cung cấp 29.770,62 GBP thì người lập tự nhân tỷ giá ngoài hệ rồi gõ số VND vào, và số ngoại
tệ, tỷ giá, ngày tỷ giá không nằm ở đâu cả.

Hệ quả đo được trên `settlement.match_paid`: nó so số VND của lệnh chi với số VND của dòng, mà hai
số ấy dùng HAI tỷ giá khác nhau. Phần chênh tỷ giá chui vào cột "còn phải trả NCC" — hoặc hiện
thành "trả thừa". Người đọc màn hình không phân biệt được chuyến còn nợ NCC thật hay chỉ lệch tỷ giá.

═══════════════════════════════════════════════════════════════════════════════════════════════
CON SỐ CHỦ TỊCH QUYẾT
═══════════════════════════════════════════════════════════════════════════════════════════════
Land 692,34 GBP × 43 khách = 29.770,62 GBP.

    quyết toán  tỷ giá 36.000  →  nghĩa vụ            1.071.742.320 đ
    ngày chi    tỷ giá 36.200  →  ngân hàng trừ       1.077.696.444 đ
                                  chênh tỷ giá            5.954.124 đ

Chủ tịch chốt 27/9/2026: cột "đã thanh toán" ghi **1.071.742.320** (tỷ giá CỦA DÒNG). Nhà cung cấp
hết nợ khi nhận đủ 29.770,62 GBP; mua ngoại tệ giá nào là việc của mình với ngân hàng. Chênh 5.954.124
đứng RIÊNG, và đợt này chỉ ĐO — chưa hạch toán 635/515.
"""
import datetime as dt
import inspect

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.models.ops import PaymentRequest
from app.models.ty_gia import TyGia
from app.models.vietrip import TourCostLine
from app.services import ngoai_te_chi as NTC
from app.services import settlement as ST

HOM_NAY = dt.date.today()

GBP, PAX = 692.34, 43
TONG_NT = 29_770.62                  # 692,34 × 43
TG_QUYET_TOAN, TG_NGAY_CHI = 36_000.0, 36_200.0
NGHIA_VU = 1_071_742_320.0           # TONG_NT × 36.000
TIEN_THAT = 1_077_696_444.0          # TONG_NT × 36.200
CHENH = 5_954_124.0


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    s.add(User(username="nvdh", full_name="nvdh", role="nv_dh", password_hash="x"))
    s.commit()
    t = Tour(code="MICE-UK-01", name="UK", tour_type="doan_nuoc_ngoai", start_date=HOM_NAY,
             end_date=HOM_NAY, operator_id=1, status="ket_thuc", price_per_pax=0,
             planned_pax=PAX, seats_open=PAX)
    s.add(t); s.commit()
    return s, t


def _dong(db, t, **kw):
    """Dòng giá vốn ghi ĐÚNG quy ước đơn giá (cửa Điều hành, sau bản sửa 27/9/2026)."""
    d = dict(tour_id=t.id, line_no=len(db.execute(select(TourCostLine)).scalars().all()) + 1,
             description="Land tour", supplier_name="NCC UK", supplier_tax_code="UK123",
             cost_kind="theo_khach", tien_te="GBP", so_tien_goc=GBP, ty_gia=TG_QUYET_TOAN,
             ngay_ty_gia=HOM_NAY, qty=PAX, coef=1,
             unit_price=round(GBP * TG_QUYET_TOAN, 2), actual=NGHIA_VU,
             source="vtos", status="hd", updated_by="nvdh")
    d.update(kw)
    l = TourCostLine(**d)
    db.add(l); db.commit(); db.refresh(l)
    return l


def _chi(db, t, **kw):
    """Lệnh chi ĐÃ CHI. `amount` là số VND máy nhân — không gõ tay."""
    d = dict(code=f"DC-{len(db.execute(select(PaymentRequest)).scalars().all()) + 1:04d}",
             category="chi_tour", tour_id=t.id, supplier_name="NCC UK", supplier_tax_code="UK123",
             tien_te="GBP", so_tien_ngoai_te=TONG_NT, ty_gia=TG_NGAY_CHI, ngay_ty_gia=HOM_NAY,
             amount=TIEN_THAT, description="Trả land UK", status="da_chi", created_by="nvdh")
    d.update(kw)
    p = PaymentRequest(**d)
    db.add(p); db.commit(); db.refresh(p)
    return p


# ═══════════════════ 1. CON SỐ CHỦ TỊCH QUYẾT — PHÉP THỬ QUAN TRỌNG NHẤT ═══════════════════

def test_nt4_da_tra_ghi_theo_TY_GIA_QUYET_TOAN_va_con_phai_tra_ve_0():
    """Nhà cung cấp nhận đủ 29.770,62 GBP thì hết nợ. "Còn phải trả" phải về 0, không phải âm."""
    db, t = _db()
    l = _dong(db, t)
    _chi(db, t)
    kq = ST.match_paid(db, t)
    db.refresh(l)

    assert l.paid == NGHIA_VU, "đã trả phải tính theo tỷ giá quyết toán, không phải tiền rời ngân hàng"
    assert round((l.actual or 0) - (l.paid or 0)) == 0, "còn phải trả NCC phải về 0"
    assert kq["chenh_ty_gia"] == CHENH == 5_954_124
    assert "LỖ tỷ giá" in kq["chenh_ty_gia_nhan_xet"]


def test_nt4_chenh_DUONG_la_LO_chenh_AM_la_LAI():
    """Dấu của con số phải đọc được mà không tra mã: dương = chi nhiều VND hơn nghĩa vụ = LỖ."""
    db, t = _db()
    _dong(db, t)
    _chi(db, t, ty_gia=35_800.0, amount=round(TONG_NT * 35_800.0, 2))
    kq = ST.match_paid(db, t)
    assert kq["chenh_ty_gia"] == -round(TONG_NT * 200), "tỷ giá chi THẤP hơn thì phải ra số âm"
    assert "LÃI tỷ giá" in kq["chenh_ty_gia_nhan_xet"]


def test_nt4_chua_hach_toan_635_515_dot_nay():
    """Chủ tịch chọn ĐO TRƯỚC (27/9/2026). Lời khai phải đi kèm con số, không để màn hình tự đoán."""
    db, t = _db()
    _dong(db, t); _chi(db, t)
    kq = ST.match_paid(db, t)
    assert "CHƯA hạch toán" in kq["chenh_ty_gia_nhan_xet"]


def test_nt4_chenh_in_ra_THEO_TUNG_DONG_khong_chi_mot_so_tong():
    """Một con số tổng không bấm vào được là một tin đồn: Kế toán phải biết dòng nào sinh ra nó."""
    db, t = _db()
    _dong(db, t); _chi(db, t)
    kq = ST.match_paid(db, t)
    assert len(kq["chenh_ty_gia_dong"]) == 1
    d = kq["chenh_ty_gia_dong"][0]
    assert d["dong"] == 1 and d["tien_te"] == "GBP"
    assert d["so_ngoai_te_da_tra"] == TONG_NT
    assert d["ty_gia_quyet_toan"] == TG_QUYET_TOAN
    assert d["chenh"] == CHENH


def test_nt4_khong_chenh_thi_khong_bay_ra_dong_nao():
    """Cùng tỷ giá thì không có gì để báo. Một bảng in cả phần đúng là một bảng không ai đọc hết."""
    db, t = _db()
    _dong(db, t)
    _chi(db, t, ty_gia=TG_QUYET_TOAN, amount=NGHIA_VU)
    kq = ST.match_paid(db, t)
    assert kq["chenh_ty_gia"] == 0 and kq["chenh_ty_gia_dong"] == []
    assert "Không có chênh lệch" in kq["chenh_ty_gia_nhan_xet"]


def test_nt4_tra_MOT_PHAN_thi_chenh_chi_tinh_tren_phan_da_tra():
    """Trả 10.000 GBP trong 29.770,62 GBP: chênh chỉ của 10.000 ấy, còn phải trả là phần GBP còn lại
    quy theo tỷ giá DÒNG — không phải phần VND còn lại của một phép trừ hai tỷ giá."""
    db, t = _db()
    l = _dong(db, t)
    _chi(db, t, so_tien_ngoai_te=10_000.0, amount=round(10_000.0 * TG_NGAY_CHI, 2))
    kq = ST.match_paid(db, t)
    db.refresh(l)
    assert l.paid == round(10_000.0 * TG_QUYET_TOAN)
    assert kq["chenh_ty_gia"] == round(10_000.0 * 200)
    assert round((l.actual or 0) - (l.paid or 0)) == round((TONG_NT - 10_000.0) * TG_QUYET_TOAN)


# ═══════════════════ 2. ĐƯỜNG CŨ KHÔNG ĐƯỢC ĐỔI ═══════════════════

def test_nt4_khoan_dong_VIET_NAM_khop_y_nhu_truoc():
    """Đại đa số khoản chi là VND. Bản sửa này không được chạm vào đường ấy."""
    db, t = _db()
    l = _dong(db, t, tien_te="", so_tien_goc=None, ty_gia=None, ngay_ty_gia=None,
              cost_kind="co_dinh", unit_price=54_000_000, actual=54_000_000, qty=PAX, coef=1)
    _chi(db, t, tien_te="", so_tien_ngoai_te=None, ty_gia=None, ngay_ty_gia=None,
         amount=54_000_000)
    kq = ST.match_paid(db, t)
    db.refresh(l)
    assert l.paid == 54_000_000 and kq["chenh_ty_gia"] == 0 and kq["matched"] == 1
    assert kq["canh_bao"] == []


def test_nt4_KHAC_dong_tien_thi_khop_theo_VND_va_PHAI_HIEN_RA():
    """Mua USD trả cho một dòng ghi GBP: không có phép quy đổi nào ở đây là đúng. Rơi về khớp theo
    VND thì được, nhưng im lặng làm thế là bịa một tỷ giá không ai khai."""
    db, t = _db()
    _dong(db, t)
    _chi(db, t, tien_te="USD", so_tien_ngoai_te=42_000.0, ty_gia=25_500.0,
         amount=round(42_000.0 * 25_500.0, 2))
    kq = ST.match_paid(db, t)
    assert kq["matched"] == 1
    assert kq["canh_bao"] and "khác đồng tiền" in kq["canh_bao"][0]
    assert "KHÔNG đo được" in kq["canh_bao"][0]
    assert kq["chenh_ty_gia"] == 0, "không được bịa một con số chênh khi không có tỷ giá chung"


def test_nt4_dong_ngoai_te_ma_lenh_chi_chi_co_VND_cung_phai_hien_ra():
    """Khoản chi lập TRƯỚC ngày 27/9/2026 nằm đúng hình này: dòng có GBP, lệnh chi chỉ có số VND đã
    gõ tay. Không truy lại được tỷ giá nào, nên phải nói ra chứ không lặng lẽ khớp."""
    db, t = _db()
    _dong(db, t)
    _chi(db, t, tien_te="", so_tien_ngoai_te=None, ty_gia=None, ngay_ty_gia=None, amount=TIEN_THAT)
    kq = ST.match_paid(db, t)
    assert kq["canh_bao"] and "khác đồng tiền" in kq["canh_bao"][0]


# ═══════════════════ 3. CỬA NHẬP: ĐỦ BỐN Ô, MÁY NHÂN ═══════════════════

def test_nt4_khoan_VND_di_dung_duong_cu():
    ra = NTC.chuan_hoa({"amount": 5_000_000})
    assert ra["tien_te"] == "" and ra["amount"] == 5_000_000
    assert ra["so_tien_ngoai_te"] is None and ra["ty_gia"] is None


def test_nt4_VND_viet_thang_ten_cung_la_khoan_dong_Viet_Nam():
    assert NTC.chuan_hoa({"tien_te": "vnd", "amount": 100})["tien_te"] == ""


@pytest.mark.parametrize("thieu,tim", [
    ({"so_tien_ngoai_te": None}, "số tiền ngoại tệ"),
    ({"ty_gia": None}, "tỷ giá"),
    ({"ngay_ty_gia": None}, "ngày tỷ giá"),
    ({"so_tien_ngoai_te": 0}, "số tiền ngoại tệ"),
])
def test_nt4_khai_ngoai_te_thi_phai_du_BON_o(thieu, tim):
    d = {"tien_te": "GBP", "so_tien_ngoai_te": TONG_NT, "ty_gia": TG_NGAY_CHI,
         "ngay_ty_gia": HOM_NAY, "amount": 0}
    d.update(thieu)
    with pytest.raises(ValueError) as e:
        NTC.chuan_hoa(d)
    assert tim in str(e.value)


def test_nt4_MAY_NHAN_nguoi_khong_go_so_VND():
    ra = NTC.chuan_hoa({"tien_te": "GBP", "so_tien_ngoai_te": TONG_NT, "ty_gia": TG_NGAY_CHI,
                        "ngay_ty_gia": HOM_NAY, "amount": 0})
    assert ra["amount"] == TIEN_THAT
    assert ra["tien_te"] == "GBP"


def test_nt4_go_so_VND_lech_thi_CHAN_chu_khong_im_lang_ghi_de():
    """Im lặng lấy số của máy là chỗ người dùng tưởng hệ đã nhận con số của mình. Nói ra thì họ sửa."""
    with pytest.raises(ValueError) as e:
        NTC.chuan_hoa({"tien_te": "GBP", "so_tien_ngoai_te": TONG_NT, "ty_gia": TG_NGAY_CHI,
                       "ngay_ty_gia": HOM_NAY, "amount": 999_000_000})
    assert "máy nhân" in str(e.value)


def test_nt4_ma_dong_tien_sai_dang_thi_chan():
    with pytest.raises(ValueError) as e:
        NTC.chuan_hoa({"tien_te": "BANGANH", "so_tien_ngoai_te": 1, "ty_gia": 1,
                       "ngay_ty_gia": HOM_NAY})
    assert "ba chữ cái" in str(e.value)


def test_nt4_de_nghi_chi_KHONG_dung_ten_so_tien_goc():
    """`so_tien_goc` ở `tour_cost_lines` là ĐƠN GIÁ MỘT ĐƠN VỊ. Đề nghị chi không có số lượng — số
    của nó là TỔNG. Dùng lại đúng cái tên ấy cho một nghĩa khác là dựng lại đúng cái bẫy đã tốn hơn
    một tỷ đồng để phát hiện ngày 27/9/2026."""
    cot = set(PaymentRequest.__table__.columns.keys())
    assert "so_tien_goc" not in cot, "một cái tên, hai nghĩa — đúng cái bẫy vừa sửa"
    assert {"tien_te", "so_tien_ngoai_te", "ty_gia", "ngay_ty_gia"} <= cot


# ═══════════════════ 4. MỘT PHÉP NHÂN, MỘT CHỖ ═══════════════════

def test_nt4_calc_actual_mac_dinh_van_lam_tron_ve_DONG():
    """Đổi chữ ký hàm mà đổi luôn hành vi mặc định là làm vỡ 100+ nơi gọi trong im lặng."""
    assert ST.calc_actual("theo_khach", 1_000_000.4, 3, 1) == 3_000_001
    assert ST.calc_actual("co_dinh", 1_000_000.4, 43, 2) == 2_000_001


def test_nt4_tong_ngoai_te_giu_phan_le_cua_dong_goc():
    """29.770,62 GBP làm tròn về 29.771 là mất 0,62 GBP — nhân tỷ giá lên là hơn hai chục nghìn đồng
    lệch trên MỖI dòng."""
    db, t = _db()
    l = _dong(db, t)
    assert ST.tong_ngoai_te(l) == TONG_NT
    assert ST.tong_ngoai_te(l) != round(TONG_NT)


def test_nt4_co_dinh_khong_nhan_so_khach_KE_CA_o_dong_goc():
    """`co_dinh` là chi phí cả đoàn. Luật phép nhân phải giống nhau ở VND và ở đồng gốc, vì nó là
    MỘT luật — không phải hai bản chép."""
    db, t = _db()
    l = _dong(db, t, cost_kind="co_dinh", coef=2)
    assert ST.tong_ngoai_te(l) == round(GBP * 2, 2)


def test_nt4_tong_ngoai_te_goi_CHINH_calc_actual_khong_chep_lai_phep_nhan():
    than = inspect.getsource(ST.tong_ngoai_te)
    assert "calc_actual(" in than
    assert "theo_khach" not in than, "đang tự phân biệt cách tính thay vì gọi calc_actual"


# ═══════════════════ 5. SỔ TỶ GIÁ LÀ BẢN THAM CHIẾU, KHÔNG PHẢI QUAN TOÀ ═══════════════════

def test_nt4_so_chua_co_ngay_ay_thi_khop_la_None_khong_phai_False():
    """`None` (sổ chưa có) và `False` (sổ có, và lệch) là hai việc khác nhau. Gộp làm một thì màn
    hình báo "sai tỷ giá" cho một khoản chỉ đơn giản là chưa ai nhập sổ."""
    db, _ = _db()
    ra = NTC.doi_chieu_so_ty_gia(db, "GBP", HOM_NAY, TG_NGAY_CHI)
    assert ra["khop"] is None and ra["co_so"] is False
    assert "chưa có" in ra["loi_nhan"]


def test_nt4_so_khop_thi_im_lang():
    db, _ = _db()
    db.add(TyGia(tien_te="GBP", ngay=HOM_NAY, ty_gia=TG_NGAY_CHI, nguon="Vietcombank")); db.commit()
    ra = NTC.doi_chieu_so_ty_gia(db, "GBP", HOM_NAY, TG_NGAY_CHI)
    assert ra["khop"] is True and ra["loi_nhan"] == ""


def test_nt4_so_lech_thi_NOI_RA_nhung_KHONG_chan():
    db, _ = _db()
    db.add(TyGia(tien_te="GBP", ngay=HOM_NAY, ty_gia=36_000.0, nguon="Vietcombank")); db.commit()
    ra = NTC.doi_chieu_so_ty_gia(db, "GBP", HOM_NAY, TG_NGAY_CHI)
    assert ra["khop"] is False
    assert "Không chặn" in ra["loi_nhan"]
    assert ra["cac_nguon"][0]["ty_gia"] == 36_000.0


def test_nt4_HAI_nguon_khop_MOT_nguon_la_du():
    """Sổ cho phép hai nguồn khác nhau cùng ngày (`models/ty_gia.py` điểm 2). Khớp một nguồn là
    khai đúng — đòi khớp cả hai là đòi hai sự thật phải giống nhau."""
    db, _ = _db()
    db.add_all([TyGia(tien_te="GBP", ngay=HOM_NAY, ty_gia=36_000.0, nguon="Vietcombank"),
                TyGia(tien_te="GBP", ngay=HOM_NAY, ty_gia=TG_NGAY_CHI, nguon="hợp đồng đối tác")])
    db.commit()
    assert NTC.doi_chieu_so_ty_gia(db, "GBP", HOM_NAY, TG_NGAY_CHI)["khop"] is True


# ═══════════════════ 6. SỔ SOÁT ĐỀ NGHỊ CHI — CHỈ ĐỌC ═══════════════════

def test_nt4_so_RONG_phai_noi_ra_la_rong():
    db, _ = _db()
    b = NTC.bang(db)
    assert b["tong_de_nghi_chi_ngoai_te"] == 0
    assert "chưa ai nhập" in b["luu_y"], "một bảng toàn số 0 đọc y hệt 'đã sạch'"


def test_nt4_bo_soat_KHONG_sua_mot_dong_du_lieu_nao():
    db, t = _db()
    p = _chi(db, t)
    truoc = (p.amount, p.so_tien_ngoai_te, p.ty_gia, p.tien_te, p.status)
    NTC.bang(db)
    db.refresh(p)
    assert (p.amount, p.so_tien_ngoai_te, p.ty_gia, p.tien_te, p.status) == truoc


def test_nt4_phep_nhan_lech_bi_bat_va_in_ra_so_dung():
    """Dòng ghi thẳng vào bảng (bộ nạp, sửa tay cơ sở dữ liệu) không đi qua cửa nhập. Con số bộ soát
    in ra là con số người ta sẽ đi sửa."""
    db, t = _db()
    _chi(db, t, amount=24_924_240.0)          # quên nhân số khách — đúng cái lỗi của cửa lớp 3 cũ
    b = NTC.bang(db)
    assert b["dem"]["phep_nhan_lech"] == 1 and b["dem"]["dung"] == 0
    assert b["rows"][0]["phep_nhan_dung"] == TIEN_THAT
    assert b["rows"][0]["nhom_ten"]


def test_nt4_khoan_VND_khong_vao_so_soat():
    db, t = _db()
    _chi(db, t, tien_te="", so_tien_ngoai_te=None, ty_gia=None, amount=5_000_000)
    assert NTC.bang(db)["tong_de_nghi_chi_ngoai_te"] == 0


def test_nt4_dong_dung_ma_ty_gia_LECH_SO_van_phai_hien_ra():
    """Phép nhân đúng không có nghĩa tỷ giá đúng. Đây là hai câu hỏi khác nhau và phải đo riêng."""
    db, t = _db()
    db.add(TyGia(tien_te="GBP", ngay=HOM_NAY, ty_gia=36_000.0, nguon="Vietcombank")); db.commit()
    _chi(db, t)
    b = NTC.bang(db)
    assert b["dem"]["dung"] == 1
    assert b["doi_chieu_so_ty_gia"]["lech"] == 1
    assert len(b["rows"]) == 1 and b["rows"][0]["so_ty_gia"]["khop"] is False


def test_nt4_moi_nhom_deu_co_ten_bang_loi():
    db, t = _db()
    _chi(db, t)
    b = NTC.bang(db)
    assert set(b["dem"]) == set(b["nhom_ten"])
    for ten in b["nhom_ten"].values():
        assert len(ten) >= 10


# ═══════════════════ 7. DÒNG KHAI NỬA VỜI KHÔNG ĐƯỢC XOÁ SỐ ĐÃ TRẢ ═══════════════════

def test_nt4_dong_khai_tien_te_ma_THIEU_don_gia_goc_khong_bi_xoa_so_da_tra():
    """Lỗi tự tìm thấy trước khi đẩy, 27/9/2026.

    Dòng kho cũ và dòng ghi thẳng vào bảng có `tien_te` nhưng `so_tien_goc` rỗng. Đi đường ngoại tệ
    với dòng ấy thì nghĩa vụ đồng gốc = 0, mọi lần trả lấy được 0, và `paid` bị ghi thành 0 — tức
    XOÁ con số đã trả đang nằm đó. Một bản sửa để đọc đúng hơn mà xoá dữ liệu tiền là bản sửa tệ hơn
    cái nó sửa.
    """
    db, t = _db()
    l = _dong(db, t, so_tien_goc=None)          # khai GBP mà không có đơn giá đồng gốc
    _chi(db, t)
    kq = ST.match_paid(db, t)
    db.refresh(l)
    assert l.paid and l.paid > 0, "đã xoá số đã trả của một dòng khai nửa vời"
    assert kq["canh_bao"] and "THIẾU đơn giá đồng gốc" in kq["canh_bao"][0]
    assert kq["chenh_ty_gia"] == 0, "không đo được thì không được bịa một con số chênh"


def test_nt4_lenh_chi_khai_tien_te_ma_thieu_so_goc_cung_roi_ve_duong_VND():
    db, t = _db()
    l = _dong(db, t)
    _chi(db, t, so_tien_ngoai_te=None, amount=TIEN_THAT)
    ST.match_paid(db, t)
    db.refresh(l)
    assert l.paid and l.paid > 0
