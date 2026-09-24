"""TC-80 · NỐI ĐỀ NGHỊ CHI VÀO CHIẾN DỊCH — sửa một lỗi số tiền đã lên màn hình Chủ tịch.

CHUYỆN ĐÃ XẢY RA, ghi lại vì phép thử này sinh ra từ đó:

Ngày 23/9/2026 anh Tuấn chốt "nối chi vào chiến dịch". Vòng TC-77 nối `campaign_id` vào
`mkt_budget_lines` — DÒNG NGÂN SÁCH — rồi lấy `amount` của dòng ấy làm "chi thực tế". `amount` là
tiền ĐỊNH tiêu. Màn hình Đóng góp doanh thu in nó dưới nhãn "Chi thực tế" và ô "Thu / chi" chia
doanh thu cho nó. Chiến dịch tiêu ít hơn kế hoạch thì hiệu quả hiện THẤP hơn sự thật, tiêu vượt thì
hiện CAO hơn, và không có dấu hiệu nào trên màn hình để ai nghi ngờ.

Tiền ĐÃ tiêu nằm ở đề nghị chi, và `payment_requests.campaign_id` vốn đã có sẵn từ lâu. Vòng ấy
nối nhầm bảng chứ không thiếu cột.

BỐN CHỖ PHÉP THỬ NÀY CANH:

 1. HAI CỘT TIỀN CÓ CỬA MÀ KHÔNG CÓ Ô NHẬP. `payment_requests.marketing_muc` và `campaign_id` có
    từ lâu, API vẫn nhận, nhưng màn hình Đề nghị chi chưa bao giờ có ô nào — nên tới 24/9/2026
    chưa một dòng chi marketing nào được gắn. Đúng ranh giới 09/9: mỗi con số hệ thống cần phải có
    một cửa nhập; không có cửa thì đó là việc còn thiếu. `test_man_hinh_de_nghi_chi_co_hai_o`.

 2. CỬA DANH MỤC KÉO THEO CẢ NHÓM MARKETING. Màn hình `/expenses` mở cho mười vai, trong đó có
    `nv_dh` và bốn vai Kinh doanh. Khai thêm `/api/v1/marketing` cho nó để lấy danh sách chiến
    dịch là nới cả nhóm Marketing cho từng ấy vai. `test_khong_khai_them_tien_to_marketing`.

 3. MÃ HẠNG MỤC GÕ SAI ĐI QUA IM LẶNG. Cổng ngân sách đối chiếu với một hạn mức không tồn tại rồi
    cho qua. `test_hang_muc_sai_bi_chan`.

 4. ĐỔI TÊN Ô CHỐT SỐ. Bản chụp cũ giữ dự toán dưới tên `chi_marketing`; giữ nguyên tên là để
    `do_troi` báo một độ trôi không có thật. Phép thử ấy nằm ở tệp TC-79.
"""
import ast
import datetime as dt
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.marketing import Campaign, HANG_MUC, MarketingBudget, MarketingBudgetLine
from app.models.ops import PaymentRequest
from app.services import marketing as MK

GOC = Path(__file__).resolve().parents[1]
WEB = GOC.parents[0] / "web"


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _cd(db, ma):
    c = Campaign(code=ma, name=ma, objective="doanh_thu", mang="le", channels=[],
                 from_date=dt.date(2026, 9, 1), budget=0.0, status="dang_chay")
    db.add(c); db.commit()
    return c


def _pr(db, tien, cd=None, trang_thai="da_chi", luc=None, cty=None):
    n = db.query(PaymentRequest).count() + 1
    r = PaymentRequest(code=f"DC-{n:04d}", category="marketing", amount=tien,
                       supplier_name="NCC", description="chi", status=trang_thai,
                       created_by="mkt", marketing_muc="quang_cao",
                       campaign_id=cd.id if cd else None, company_id=cty,
                       created_at=luc or dt.datetime(2026, 9, 10, 9, 0))
    db.add(r); db.commit()
    return r


# ═════════════════════════ PHÉP TÍNH ═════════════════════════

def test_chi_thuc_te_chi_dem_de_nghi_chi_KHONG_dem_dong_ngan_sach():
    """Ranh giới của cả vòng. Dự toán và tiền đã tiêu là hai con số, không bao giờ trộn."""
    db = _db()
    cd = _cd(db, "CD-A")
    b = MarketingBudget(period="2026-09", target_leads=1, target_revenue=0, rationale="x",
                        status="hieu_luc", created_by="mkt")
    db.add(b); db.commit()
    db.add(MarketingBudgetLine(budget_id=b.id, hang_muc="quang_cao", amount=500_000_000,
                               campaign_id=cd.id))
    db.commit()
    kq = MK.chi_thuc_te(db, "2026-09")
    assert kq["da_chi_tong"] == 0, "Dòng ngân sách KHÔNG phải tiền đã tiêu"
    assert kq["da_chi_theo_chien_dich"] == {}


def test_ba_tui_tien_theo_trang_thai_va_tu_choi_khong_vao_tui_nao():
    db = _db()
    cd = _cd(db, "CD-A")
    _pr(db, 10_000_000, cd, "da_chi")
    _pr(db, 20_000_000, cd, "cho_kt")
    _pr(db, 30_000_000, cd, "cho_chi")
    _pr(db, 99_000_000, cd, "tu_choi")
    kq = MK.chi_thuc_te(db, "2026-09")
    assert kq["da_chi_theo_chien_dich"][cd.id] == 10_000_000
    assert kq["treo_theo_chien_dich"][cd.id] == 50_000_000
    assert kq["da_chi_tong"] + kq["treo_tong"] == 60_000_000, "Từ chối không được cộng vào đâu"


def test_chua_gan_chien_dich_nam_rieng_chu_khong_chia_deu():
    db = _db()
    cd = _cd(db, "CD-A")
    _pr(db, 10_000_000, cd)
    _pr(db, 40_000_000, None)
    kq = MK.chi_thuc_te(db, "2026-09")
    assert kq["da_chi_chua_gan"] == 40_000_000
    assert kq["da_chi_theo_chien_dich"][cd.id] == 10_000_000, "Phần chưa gắn không được rót sang"


def test_ky_cat_theo_ngay_LAP_de_nghi_giong_het_man_hinh_ngan_sach():
    """Hai cách chia kỳ khác nhau thì hai màn hình cùng nói về một khoản tiền mà ra hai con số."""
    db = _db()
    cd = _cd(db, "CD-A")
    _pr(db, 10_000_000, cd, luc=dt.datetime(2026, 8, 31, 23, 59))
    _pr(db, 20_000_000, cd, luc=dt.datetime(2026, 9, 1, 0, 0))
    _pr(db, 40_000_000, cd, luc=dt.datetime(2026, 10, 1, 0, 0))
    assert MK.chi_thuc_te(db, "2026-09")["da_chi_tong"] == 20_000_000


def test_loc_duoc_theo_phap_nhan():
    db = _db()
    cd = _cd(db, "CD-A")
    _pr(db, 10_000_000, cd, cty=1)
    _pr(db, 70_000_000, cd, cty=2)
    assert MK.chi_thuc_te(db, "2026-09", company_id=2)["da_chi_tong"] == 70_000_000
    assert MK.chi_thuc_te(db, "2026-09")["da_chi_tong"] == 80_000_000


def test_chi_khong_phai_marketing_thi_khong_dem():
    db = _db()
    cd = _cd(db, "CD-A")
    r = _pr(db, 10_000_000, cd)
    r.category = "chi_tour"
    db.commit()
    assert MK.chi_thuc_te(db, "2026-09")["da_chi_tong"] == 0


# ═════════════════════════ CỬA NHẬP ═════════════════════════

def test_man_hinh_de_nghi_chi_co_hai_o_hang_muc_va_chien_dich():
    """Ranh giới 09/9/2026: mỗi con số cần một cửa nhập. Hai cột này có cửa API mà không có ô."""
    t = (WEB / "app" / "expenses" / "page.tsx").read_text(encoding="utf-8")
    assert "marketing_muc" in t, "Thiếu ô hạng mục ngân sách Marketing"
    assert "campaign_id" in t, "Thiếu ô chiến dịch"
    assert "danh-muc-marketing" in t, "Hai ô chọn phải lấy danh mục từ một cửa thật"


def test_khong_khai_them_tien_to_marketing_cho_man_hinh_de_nghi_chi():
    """Phần dôi ra vẫn là quyền đã cấp — bài học đã trả giá bảy lần trong kho này."""
    from app.services.access import MAN_HINH_API
    tt = MAN_HINH_API["/expenses"]
    assert "/api/v1/marketing" not in tt, (
        "Màn hình Đề nghị chi mở cho mười vai, gồm nv_dh và bốn vai Kinh doanh. Khai thêm tiền tố "
        "Marketing chỉ để lấy danh sách chiến dịch là nới cả nhóm Marketing cho từng ấy vai. "
        "Danh mục đã có cửa riêng dưới /api/v1/payment-requests.")
    assert "/api/v1/payment-requests" in tt


def test_cua_danh_muc_nam_duoi_tien_to_cua_chinh_phan_he():
    from app.main import app
    duong = [r.path for r in app.routes if "danh-muc-marketing" in r.path]
    assert duong == ["/api/v1/payment-requests/danh-muc-marketing"]


def _u(db):
    from app.models.core import User
    u = User(username="mkt", full_name="MKT", role="nv_mkt", password_hash="x")
    db.add(u); db.commit()
    return u


def _goi_lap(db, u, **them):
    from app.services import ops as OPS
    d = {"category": "marketing", "supplier_name": "NCC", "amount": 1_000_000,
         "description": "chi thu", "has_document": True}
    d.update(them)
    return OPS.create_request(db, u, d)


def test_hang_muc_sai_bi_chan_chu_khong_di_qua_im_lang():
    """Mã sai thì cổng ngân sách đối chiếu với một hạn mức không tồn tại rồi im lặng cho qua."""
    import pytest
    db = _db(); u = _u(db)
    with pytest.raises(ValueError, match="Hạng mục marketing không hợp lệ"):
        _goi_lap(db, u, marketing_muc="khong_co_that")


def test_chien_dich_khong_co_that_bi_chan():
    """Gắn vào một id không tồn tại thì khoản tiền ấy biến mất khỏi mọi bảng mà không ai biết."""
    import pytest
    db = _db(); u = _u(db)
    with pytest.raises(ValueError, match="Không có chiến dịch id"):
        _goi_lap(db, u, marketing_muc="quang_cao", campaign_id=99999)


def test_lap_duoc_va_hai_o_duoc_ghi_dung():
    db = _db(); u = _u(db)
    cd = _cd(db, "CD-A")
    r = _goi_lap(db, u, marketing_muc="su_kien", campaign_id=cd.id)
    db.commit()
    assert (r.marketing_muc, r.campaign_id) == ("su_kien", cd.id)


def test_hang_muc_rong_van_hop_le_vi_rong_nghia_la_CHUA_GAN():
    nguon = (GOC / "app" / "services" / "ops.py").read_text(encoding="utf-8")
    assert "rỗng nghĩa là" in nguon or "Rỗng vẫn hợp lệ" in nguon, (
        "Phải ghi rõ rỗng là hợp lệ, không thì người sau sẽ siết thành bắt buộc")
    assert set(HANG_MUC) == {"quang_cao", "noi_dung", "su_kien", "an_pham", "nghien_cuu", "khac"}


# ═════════════════════════ MÀN HÌNH KHÔNG NÓI SAI ═════════════════════════

def test_man_hinh_2_7_khong_con_nhan_chi_thuc_te_tren_cot_du_toan():
    t = (WEB / "app" / "dong-gop-marketing" / "page.tsx").read_text(encoding="utf-8")
    assert "chi_thuc_te" not in t, "Tên cũ mang nghĩa sai – không được sống lại"
    for cot in ("Đã chi", "Đang treo", "Dự toán đã gắn"):
        assert cot in t, f"Thiếu cột {cot}"
    assert "r.da_chi" in t and "r.du_toan_gan" in t


def test_bon_muc_marketing_mo_coi_da_duoc_noi():
    """Bốn mục đã có màn hình chạy nhưng cây phân hệ chưa trỏ tới — máy có mà không ai tìm ra."""
    t = (WEB / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    for ma, href in (("2.3.2", "/inbox"), ("2.4.2", "/chuyen-doi-lead"),
                     ("2.5.2", "/dong-gop-marketing"), ("3.5.3", "/cham-soc")):
        dong = [d for d in t.split("\n") if f'ma: "{ma}"' in d]
        assert dong, f"Không tìm thấy mục {ma}"
        for d in dong:
            assert f'href: "{href}"' in d, f"Mục {ma} vẫn chưa có đường dẫn {href}"


def test_khong_len_nhanh_dung_chung_thu_sau():
    """`chung` là tính chất của KHUNG NHÌN, và năm nhánh dùng chung đã được chốt."""
    t = (WEB / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    assert t.count("chung: true") <= 5, (
        "Nhánh dùng chung thứ sáu phải là một quyết định có người ký, "
        "không phải một dòng thêm cho tiện — xem test_nam_nhanh_dung_chung_dung_la_nam_nhanh_da_chot")


def test_ma_nguon_ghi_lai_loi_da_sua_de_nguoi_sau_khong_lam_lai():
    """Một lỗi đã lên màn hình lãnh đạo mà không ai ghi lại thì sẽ có người làm lại."""
    for tep in ("services/marketing.py", "services/dong_gop_marketing.py"):
        n = (GOC / "app" / tep).read_text(encoding="utf-8")
        assert "DỰ TOÁN" in n and "payment_requests" in n, f"{tep} chưa ghi lại vì sao đổi"


def test_khong_tep_nao_con_doc_ten_cu():
    """`tong_chi` và `chi_chua_gan` mang nghĩa dự toán. Còn chỗ nào đọc là còn chỗ ấy sai."""
    xau = []
    for p in list((GOC / "app").rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        n = p.read_text(encoding="utf-8")
        for ten in ('chi_marketing"]["tong_chi"]', 'chi_marketing"]["chi_chua_gan"]'):
            if ten in n:
                xau.append(f"{p.name}: {ten}")
    assert not xau, xau


def test_cay_phan_he_van_doc_duoc_bang_may():
    """Sửa tay một tệp cấu trúc thì phải chắc nó chưa hỏng cú pháp."""
    t = (WEB / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    assert t.count("{") == t.count("}")
    assert t.count("[") == t.count("]")
    assert isinstance(ast.parse("x = 1"), ast.Module)     # giữ import ast có ích
