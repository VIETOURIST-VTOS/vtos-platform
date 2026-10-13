# -*- coding: utf-8 -*-
"""Đợt E7 (13/10/2026) — HÓA ĐƠN PHÁT HÀNH ĐÚNG MỘT LẦN.

BỐN CHỖ HỎNG ĐO ĐƯỢC TRÊN main NGÀY 13/10/2026, và tệp này canh từng chỗ:

  1. `issue_invoice` đọc `inv.status` rồi ghi, KHÔNG khoá.
  2. Số cấp bằng `max(Invoice.number) + 1`, cột `number` KHÔNG có chỉ mục duy nhất cùng `series`.
     Hai lỗi trong một phép: hai lần gọi cùng lúc ra cùng một số, VÀ một tờ đã hủy mang số cuối
     thì số ấy được cấp lại.
  3. Nút trên màn hình không tự khoá.
  4. Không có trạng thái nào cho "đã gửi mà chưa biết kết quả".

ĐIỀU TỆP NÀY ĐO ĐƯỢC VÀ ĐIỀU NÓ KHÔNG ĐO ĐƯỢC — nói ra để không ai tưởng nó canh đủ:

  · ĐO ĐƯỢC: mã việc lặp lại không ra tờ thứ hai · chỉ mục duy nhất trên (ký hiệu, số) đổ khi
    có hai tờ cùng số · số đã cấp KHÔNG cấp lại dù tờ cũ bị hủy · trạng thái thứ tư và ba đường
    ra của cửa dò lại · sổ số nhảy nói đúng chỗ dãy số bị khuyết.
  · KHÔNG ĐO ĐƯỢC: `with_for_update` trong `cap_so`. SQLite chạy một tiến trình và bỏ qua câu
    khoá hàng ấy. Đó CHÍNH LÀ lý do đợt này đặt hàng rào thứ hai ở cơ sở dữ liệu thay vì tin vào
    một chỗ mà phép thử không soi tới — và phép thử `test_e7_6` đo đúng cái hàng rào thứ hai ấy.
"""
import os
import sys
import tempfile
from datetime import date, datetime

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e7.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                                   # noqa: E402
from sqlalchemy import select                                    # noqa: E402
from sqlalchemy.exc import IntegrityError                        # noqa: E402

from app.db.session import Base, SessionLocal, engine            # noqa: E402
from app.models.accounting import Account, Invoice               # noqa: E402
from app.models.core import User                                 # noqa: E402
from app.models.so_hoa_don import SoNhayHoaDon                   # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import hoa_don_so as HDS                       # noqa: E402

Base.metadata.create_all(engine)

# BA TÀI KHOẢN `on_invoice_issued` GHI VÀO. Nạp ở đây chứ không mượn bộ nạp danh mục đầy đủ: đợt
# này đo cửa PHÁT HÀNH, và một tệp phép thử phụ thuộc vào bộ nạp danh mục là một tệp đỏ theo mỗi
# lần ai đó sửa danh mục tài khoản.
with SessionLocal() as _s:
    for _ma, _ten, _loai in (("131", "Phải thu khách hàng", "TS"),
                             ("511", "Doanh thu bán hàng và cung cấp dịch vụ", "DT"),
                             ("3331", "Thuế GTGT phải nộp", "NV")):
        if not _s.get(Account, _ma):
            _s.add(Account(code=_ma, name=_ten, kind=_loai, is_detail=True))
    _s.commit()


def db_():
    return SessionLocal()


def _ketoan(db) -> User:
    u = db.execute(select(User).where(User.username == "e7_ketoan")).scalars().first()
    if not u:
        u = User(username="e7_ketoan", full_name="Kế toán E7", role="ketoan", password_hash="x")
        db.add(u); db.commit()
    return u


_dem = [0]


def _nhap(db, series="E7A") -> Invoice:
    """Một hóa đơn NHÁP. Không đi qua `create_invoice` vì phép đó cần booking và tham số thuế —
    đợt này đo cửa PHÁT HÀNH, không đo cửa lập nháp."""
    _dem[0] += 1
    inv = Invoice(series=series, customer_name="Khách E7 %d" % _dem[0],
                  pre_tax=1_000_000.0, vat_rate=0.1, vat=100_000.0, total=1_100_000.0,
                  status="nhap", created_by="e7_ketoan")
    db.add(inv); db.commit(); db.refresh(inv)
    return inv


class ProviderTreo:
    """Nhà cung cấp ĐỨT GIỮA ĐƯỜNG: `issue` nổ, `tra_cuu` trả về điều ta dặn trước."""
    name = "thu_treo"

    def __init__(self, tra_loi=HDS.CHUA_BIET):
        self.tra_loi, self.so_lan_goi = tra_loi, 0

    def issue(self, db, inv, so):
        self.so_lan_goi += 1
        raise RuntimeError("mạng đứt giữa đường")

    def tra_cuu(self, db, inv):
        if self.tra_loi == HDS.DA_RA:
            return HDS.DA_RA, inv.number, "CQT-%s-%07d" % (inv.series, inv.number)
        return self.tra_loi, 0, ""


def _dat_provider(p):
    cu = ACC.PROVIDER
    ACC.PROVIDER = p
    return cu


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. SỐ CẤP TỪ BẢNG SỐ NHẢY — chỉ tăng, không bao giờ lùi
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e7_1_bo_cap_so_khong_con_doc_max_cua_bang_hoa_don():
    """Đọc chính thân `LocalInvoiceProvider`: `max(Invoice.number)` còn ở đó là lỗi gốc còn sống."""
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services", "accounting.py")
    ma = open(p, encoding="utf-8").read()
    than = ma.split("class LocalInvoiceProvider")[1].split("def tra_cuu")[0]
    # Hỏi theo LỜI GỌI THẬT `func.max(...)`, không hỏi theo chữ "max(Invoice.number)": chữ ấy còn
    # nằm trong chú thích của chính đợt này, nói vì sao phép cũ sai. Bản đầu của phép thử này hỏi
    # theo chữ và ĐỎ NGAY — nó bắt đúng lời giải thích của chính nó. Ghi lại vì cái bẫy ấy rẻ ở
    # đây và đắt ở một phép thử đi canh chú thích thay vì canh mã.
    assert "func.max(Invoice.number)" not in than, "bộ cấp số vẫn cấp bằng max+1"


def test_e7_2_so_da_cap_KHONG_cap_lai_du_to_cu_bi_huy():
    """Đây là lỗi mà `max+1` không bao giờ thấy: tờ mang số cuối bị hủy thì `max` tụt xuống.

    Hai tờ khác nhau mang cùng một số, và tờ trước đã nằm trong tay khách.
    """
    db = db_()
    u = _ketoan(db)
    a = _nhap(db, "E7B")
    ACC.issue_invoice(db, u, a, "mv:e7-2-a")
    so_a = a.number
    ACC.cancel_invoice(db, u, a, "khách đổi tên công ty")
    assert a.status == "huy"

    b = _nhap(db, "E7B")
    ACC.issue_invoice(db, u, b, "mv:e7-2-b")
    assert b.number == so_a + 1, "số của tờ đã hủy bị cấp lại — hai tờ một số"
    assert db.get(SoNhayHoaDon, "E7B").so_cuoi == so_a + 1


def test_e7_3_ky_hieu_moi_bat_dau_tu_so_lon_nhat_da_tieu_trong_so():
    """Hóa đơn nhập từ sổ cũ SAU ngày di trú: bắt đầu từ 0 là cấp lại số đã in ra giấy."""
    db = db_()
    u = _ketoan(db)
    cu = Invoice(series="E7C", number=417, customer_name="Sổ cũ", status="da_phat_hanh",
                 total=1_000.0, issue_date=date(2026, 1, 5), created_by="nap_so_cu")
    db.add(cu); db.commit()
    assert db.get(SoNhayHoaDon, "E7C") is None
    moi = _nhap(db, "E7C")
    ACC.issue_invoice(db, u, moi, "mv:e7-3")
    assert moi.number == 418


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. CHỐNG PHÁT HÀNH HAI LẦN — hai hàng rào, hai tầng
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e7_4_ma_viec_lap_lai_KHONG_ra_to_thu_hai():
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db)
    ACC.issue_invoice(db, u, inv, "mv:e7-4")
    so = inv.number
    # Vế thứ nhất của phép chống: cửa API hỏi câu này TRƯỚC khi làm gì cả.
    lai = HDS.tim_theo_ma_viec(db, "mv:e7-4")
    assert lai is not None and lai.id == inv.id and lai.number == so
    assert len(db.execute(select(Invoice).where(Invoice.number == so,
                                                Invoice.series == inv.series)).scalars().all()) == 1


def test_e7_5_phat_hanh_lai_mot_to_dang_treo_thi_BI_CHAN():
    """Tờ đang ở "đang phát hành" chỉ ra khỏi đó qua cửa dò lại, không qua cửa phát hành."""
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db)
    p = ProviderTreo()
    cu = _dat_provider(p)
    try:
        with pytest.raises(ValueError):
            ACC.issue_invoice(db, u, inv, "mv:e7-5")
        assert inv.status == "dang_phat_hanh"
        with pytest.raises(ValueError) as ex:
            ACC.issue_invoice(db, u, inv, "mv:e7-5-lan-hai")
        assert "DÒ LẠI" in str(ex.value)
        assert p.so_lan_goi == 1, "đã gửi lần thứ hai sang nhà cung cấp — đúng điều phải chặn"
    finally:
        _dat_provider(cu)


def test_e7_6_chi_muc_duy_nhat_do_khi_hai_to_cung_mot_so():
    """HÀNG RÀO THỨ HAI, ở tầng không đường nào lách được.

    Mã việc nằm ở màn hình, nên robot gọi thẳng API hay một bản vá sau này viết sai đều không đi
    qua nó. Phép thử này ghi thẳng vào bảng, bỏ qua mọi lớp dịch vụ — đúng cách một lỗi thật sẽ
    đi tới — và đòi cơ sở dữ liệu đổ.
    """
    db = db_()
    u = _ketoan(db)
    a = _nhap(db, "E7D")
    ACC.issue_invoice(db, u, a, "mv:e7-6")
    xau = Invoice(series="E7D", number=a.number, customer_name="Tờ trùng số",
                  status="da_phat_hanh", total=1.0, created_by="ke_di_tat")
    db.add(xau)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_e7_7_nhieu_to_NHAP_cung_ton_tai_duoc():
    """Chỉ mục duy nhất phải có ĐIỀU KIỆN `number > 0`.

    Mọi tờ nháp mang `number = 0`, nên một chỉ mục không điều kiện đổ ngay ở tờ nháp thứ hai —
    tức hàng rào chống trùng số lại chặn chính việc lập hóa đơn.
    """
    db = db_()
    a, b, c = _nhap(db, "E7E"), _nhap(db, "E7E"), _nhap(db, "E7E")
    assert (a.number, b.number, c.number) == (0, 0, 0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. TRẠNG THÁI THỨ TƯ VÀ CỬA DÒ LẠI — ba đường ra, và đường thứ ba là GIỮ NGUYÊN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e7_8_mang_dut_thi_to_nam_lai_o_dang_phat_hanh_va_so_da_tieu():
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db, "E7F")
    cu = _dat_provider(ProviderTreo())
    try:
        with pytest.raises(ValueError) as ex:
            ACC.issue_invoice(db, u, inv, "mv:e7-8")
        assert "ĐANG PHÁT HÀNH" in str(ex.value)
    finally:
        _dat_provider(cu)
    assert inv.status == "dang_phat_hanh"
    assert inv.number > 0, "tờ treo mà không có số thì khoảng trống nó để lại không quy về đâu"
    assert inv.issue_sent_at is not None
    assert inv.entry_id is None, "chưa biết tờ ấy đã ra mà đã ghi sổ"
    assert db.get(SoNhayHoaDon, "E7F").so_cuoi == inv.number


def test_e7_9_do_lai_DA_RA_thi_ghi_so_va_khong_goi_lai_lan_nao():
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db, "E7G")
    p = ProviderTreo(HDS.DA_RA)
    cu = _dat_provider(p)
    try:
        with pytest.raises(ValueError):
            ACC.issue_invoice(db, u, inv, "mv:e7-9")
        kq = HDS.do_lai(db, u, inv)
    finally:
        _dat_provider(cu)
    assert kq["ket_qua"] == HDS.DA_RA
    assert inv.status == "da_phat_hanh"
    assert inv.entry_id is not None, "nhà cung cấp nói đã ra mà sổ không có bút toán nào"
    assert p.so_lan_goi == 1, "dò lại đã GỬI LẠI thay vì chỉ HỎI"


def test_e7_10_do_lai_CHUA_RA_thi_ve_nhap_va_so_da_cap_khong_tra_lai():
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db, "E7H")
    cu = _dat_provider(ProviderTreo(HDS.CHUA_RA))
    try:
        with pytest.raises(ValueError):
            ACC.issue_invoice(db, u, inv, "mv:e7-10")
        so_da_tieu = inv.number
        kq = HDS.do_lai(db, u, inv)
    finally:
        _dat_provider(cu)
    assert kq["ket_qua"] == HDS.CHUA_RA
    assert inv.status == "nhap" and inv.number == 0
    # SỐ ĐÃ CẤP KHÔNG TRẢ LẠI: trả lại là cấp một số cho hai tờ.
    assert db.get(SoNhayHoaDon, "E7H").so_cuoi == so_da_tieu
    bang = {b["series"]: b for b in HDS.bang_so_nhay(db)}["E7H"]
    assert so_da_tieu in bang["so_thieu"], "khoảng trống trong dãy số phải nhìn thấy được"


def test_e7_11_do_lai_CHUA_BIET_thi_GIU_NGUYEN():
    """Thà một tờ treo chờ hỏi lại còn hơn hai tờ đã gửi lên thuế."""
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db, "E7I")
    cu = _dat_provider(ProviderTreo(HDS.CHUA_BIET))
    try:
        with pytest.raises(ValueError):
            ACC.issue_invoice(db, u, inv, "mv:e7-11")
        kq = HDS.do_lai(db, u, inv)
    finally:
        _dat_provider(cu)
    assert kq["ket_qua"] == HDS.CHUA_BIET
    assert inv.status == "dang_phat_hanh" and inv.entry_id is None


def test_e7_12_do_lai_mot_to_khong_treo_thi_bi_chan():
    db = db_()
    u = _ketoan(db)
    inv = _nhap(db, "E7J")
    ACC.issue_invoice(db, u, inv, "mv:e7-12")
    with pytest.raises(HDS.SaiPhatHanh):
        HDS.do_lai(db, u, inv)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. SỔ SỐ NHẢY — câu kiểm toán luôn hỏi
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e7_13_day_so_lien_tuc_thi_bao_lien_tuc():
    db = db_()
    u = _ketoan(db)
    for i in range(3):
        ACC.issue_invoice(db, u, _nhap(db, "E7K"), "mv:e7-13-%d" % i)
    b = {x["series"]: x for x in HDS.bang_so_nhay(db)}["E7K"]
    assert (b["so_cuoi"], b["da_phat_hanh"], b["so_thieu_tong"]) == (3, 3, 0)


def test_e7_14_to_da_huy_van_giu_so_nen_day_so_KHONG_khuyet():
    """Một tờ đã hủy vẫn chiếm số của nó. Dãy số liên tục; cái khuyết là tờ không bao giờ ra."""
    db = db_()
    u = _ketoan(db)
    a = _nhap(db, "E7L")
    ACC.issue_invoice(db, u, a, "mv:e7-14")
    ACC.cancel_invoice(db, u, a, "khách trả lại dịch vụ")
    b = {x["series"]: x for x in HDS.bang_so_nhay(db)}["E7L"]
    assert (b["da_huy"], b["so_thieu_tong"]) == (1, 0)
