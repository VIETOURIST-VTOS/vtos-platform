"""TC-99 · MÀN HÌNH KHÔNG ĐƯỢC KHẲNG ĐỊNH KHI CHƯA BIẾT, VÀ KHÔNG ĐƯỢC ĐỔ HẾT RA MỘT TRANG — 29/9/2026.

Vòng này sinh ra từ đợt rà giao diện bốn phòng (Marketing, Kinh doanh Lẻ, Kinh doanh Đoàn, Điều
hành) ngày 29/9/2026. Hai lỗi nặng tìm được cùng một gốc: MÀN HÌNH NÓI MỘT CÂU MÀ NÓ CHƯA CÓ QUYỀN
NÓI, hoặc nói tất cả những gì nó có bất kể người đọc có chịu nổi không.

MỘT · "KHÔNG CÓ PHIẾU NÀO" TRONG LÚC CÒN ĐANG HỎI.
    Cửa `/cham-soc` trả 1.267 phiếu, 776 KB, mất 12 giây. Suốt 12 giây ấy bảng in nguyên câu
    "Không có phiếu nào ở bộ lọc này." Câu ấy là một khẳng định về dữ liệu, nhưng lúc in ra thì
    chưa ai hỏi xong dữ liệu cả. Nhân viên mở lên, đọc, đóng trang, và tưởng hôm nay hết việc —
    trong khi 1.254 phiếu đang quá hạn liên hệ.

    Hai việc phải làm, và phải làm CẢ HAI:
      · màn hình phân biệt "đang tải" với "đã hỏi xong và không có gì";
      · máy chủ thôi hỏi cơ sở dữ liệu bốn lượt cho mỗi phiếu. Mười hai giây không phải là giá của
        1.267 dòng dữ liệu; nó là giá của hơn năm nghìn lượt truy vấn lẻ. Chỉ sửa màn hình thì
        người dùng vẫn ngồi chờ 12 giây, chỉ là chờ có chữ.

HAI · 6.682 DÒNG CHI TIẾT TRONG MỘT TRANG.
    `/sales-reports?mang=le`, báo cáo bán tour lẻ, kỳ 01–29/9/2026: bảng tổng hợp 56 dòng, bảng chi
    tiết 6.682 dòng, tất cả dựng thành thẻ HTML trong một màn hình — khoảng 900 KB văn bản. Mảng
    Đoàn cùng kỳ chỉ 85 dòng, nên suốt thời gian qua không ai gặp. Máy ở chi nhánh mở là đứng.

    Cắt bảng thì phải NÓI RA đã cắt và còn bao nhiêu, đúng như `/tours` và `/so-con-no` vẫn làm.
    Một bảng cắt âm thầm còn tệ hơn một bảng dài: người đọc cộng tay 300 dòng rồi tưởng đó là tổng.

BA · HAI CÁI NHÃN SAI (nhẹ, gộp chung vòng).
    `HrScreens` phục vụ cả Nhân sự lẫn Điều hành nhưng tiêu đề ghi cứng "Nhân sự – Lương (robot
    R6)"; người Điều hành vào bằng `/ops?tab=fleet` mở ĐÚNG tab Đội xe nhưng đọc tiêu đề lại tưởng
    mình lạc. Và `/visa` là màn hình duy nhất của bốn phòng không có <h1> nào.

CHỖ DỄ LÀM HỎNG KHI SỬA: gom truy vấn là một phép TỐI ƯU, nên nó phải cho ra ĐÚNG cùng một kết quả
với bản hỏi lẻ. Phép thử dưới đây so từng khoá một, không tin vào mắt người đọc diff.
"""
import os
import re
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_tc99.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import datetime as dt

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.api.v1 import cskh as API
from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.models.cskh import CareTicket, Complaint
from app.services import rules as R

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOM_NAY = dt.date.today()


# ══════════════════════════ dựng dữ liệu ══════════════════════════
def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvdh", "nv_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    R.seed_params(s)
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _phieu(db, n: int):
    """n phiếu, MỖI PHIẾU MỘT TOUR VÀ MỘT BOOKING RIÊNG.

    Dùng chung một tour thì bản cũ cũng chỉ hỏi tour đúng một lần – SQLAlchemy giữ đối tượng đã nạp
    trong phiên – và phép thử sẽ xanh cho cả bản chưa sửa. Mỗi phiếu một tour mới là hình đúng của
    dữ liệu thật: 1.267 phiếu của Vietourist nằm trên hàng trăm chuyến khác nhau.
    """
    for i in range(n):
        t = Tour(code=f"L{i}", name=f"Chuyến {i}", tour_type="le_noi_dia",
                 start_date=HOM_NAY - dt.timedelta(days=9), end_date=HOM_NAY - dt.timedelta(days=6),
                 operator_id=_u(db, "nvdh").id, status="ket_thuc", price_per_pax=5_000_000,
                 fixed_cost=1_000_000, var_cost_per_pax=2_000_000, planned_pax=10, seats_open=10)
        db.add(t); db.flush()
        r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name=f"Khách {i}",
                           customer_phone=f"09000000{i:02d}", source="web", pax=1)
        db.add(r); db.flush()
        b = Booking(code=f"BK{i}", tour_id=t.id, request_id=r.id, sales_id=_u(db, "nvkd").id,
                    created_by=_u(db, "nvdh").id, customer_name=f"Khách {i}",
                    customer_phone=f"09000000{i:02d}", source="web", pax=1, amount=5_000_000)
        db.add(b); db.flush()
        db.add(CareTicket(booking_id=b.id, tour_id=t.id, customer_name=f"Khách {i}",
                          customer_phone=f"09000000{i:02d}", owner_id=_u(db, "nvkd").id,
                          han_lien_he=HOM_NAY - dt.timedelta(days=1)))
    db.commit()


def _dem_truy_van(db, viec):
    """Đếm số câu lệnh thật sự gửi xuống cơ sở dữ liệu trong lúc `viec()` chạy."""
    dem = [0]
    bind = db.get_bind()

    def _ghi(conn, cursor, statement, parameters, context, executemany):
        dem[0] += 1

    event.listen(bind, "before_cursor_execute", _ghi)
    try:
        viec()
    finally:
        event.remove(bind, "before_cursor_execute", _ghi)
    return dem[0]


def _doc_ca_danh_sach(db):
    """Đúng những gì tuyến GET /cham-soc làm sau khi cắt dòng theo vai."""
    db.expunge_all()          # bỏ bộ nhớ đệm của phiên, nếu không thì bản cũ cũng trông như đã sửa
    phieu = list(db.execute(select(CareTicket).order_by(CareTicket.id)).scalars())
    ctx = API.cs_ctx(db, phieu)
    return [API.cs_out(db, t, ctx) for t in phieu]


# ═══════ LUẬT 1 · SỐ LƯỢT HỎI CSDL KHÔNG ĐƯỢC TĂNG THEO SỐ PHIẾU ═══════
def test_doc_danh_sach_cham_soc_khong_hoi_theo_tung_dong():
    it = _db(); _phieu(it, 3)
    nhieu = _db(); _phieu(nhieu, 15)

    n_it = _dem_truy_van(it, lambda: _doc_ca_danh_sach(it))
    n_nhieu = _dem_truy_van(nhieu, lambda: _doc_ca_danh_sach(nhieu))

    assert n_it == n_nhieu, (
        f"3 phiếu tốn {n_it} lượt hỏi, 15 phiếu tốn {n_nhieu} lượt — số lượt vẫn tăng theo số dòng. "
        "Đó đúng là chỗ làm cửa /cham-soc mất 12 giây với 1.267 phiếu.")
    assert n_nhieu <= 8, (
        f"đọc cả danh sách tốn {n_nhieu} lượt hỏi; cần một lượt cho phiếu và một lượt cho mỗi bảng "
        "tra kèm (tour, booking, người, khiếu nại), không hơn.")


def test_phieu_rong_khong_lam_no_ham_gom():
    db = _db()
    assert API.cs_ctx(db, []) == {"tour": {}, "booking": {}, "nguoi": {}, "khieu_nai": {}}


# ═══════ LUẬT 2 · GOM TRUY VẤN KHÔNG ĐƯỢC ĐỔI MỘT CHỮ NÀO CỦA KẾT QUẢ ═══════
def test_ban_gom_va_ban_hoi_le_ra_y_het_nhau():
    db = _db(); _phieu(db, 4)
    phieu = list(db.execute(select(CareTicket).order_by(CareTicket.id)).scalars())
    ctx = API.cs_ctx(db, phieu)
    for t in phieu:
        assert API.cs_out(db, t, ctx) == API.cs_out(db, t), \
            f"phiếu {t.id}: bản gom khác bản hỏi lẻ — tối ưu đã làm đổi dữ liệu"


def test_phieu_chua_gan_khieu_nai_va_chua_giao_ai_van_ra_o_trong():
    """Khoá rỗng phải cho ra chuỗi rỗng, KHÔNG được nổ và không được ra chữ 'None'."""
    db = _db(); _phieu(db, 1)
    t = db.execute(select(CareTicket)).scalars().first()
    t.owner_id = None; t.complaint_id = None; db.commit()
    ctx = API.cs_ctx(db, [t])
    ra = API.cs_out(db, t, ctx)
    assert ra["phu_trach"] == "" and ra["complaint_code"] == ""


def test_phieu_co_khieu_nai_thi_ban_gom_van_lay_duoc_ma():
    db = _db(); _phieu(db, 1)
    t = db.execute(select(CareTicket)).scalars().first()
    kn = Complaint(code="KN-9001", booking_id=t.booking_id, tour_id=t.tour_id,
                   customer_name=t.customer_name, customer_phone=t.customer_phone,
                   source="hotline", nhom="hdv", level=1, noi_dung="thử")
    db.add(kn); db.flush(); t.complaint_id = kn.id; db.commit()
    ctx = API.cs_ctx(db, [t])
    assert API.cs_out(db, t, ctx)["complaint_code"] == "KN-9001"


# ══════════════════════════ đọc màn hình ══════════════════════════
def _tsx(*phan) -> str:
    return open(os.path.join(GOC, *phan), encoding="utf-8").read()


def _bo_chu_thich(s: str) -> str:
    """Bỏ chú thích để hàng rào không bắt nhầm chính lời khai của vòng này.

    Bài học của TC-93: phép thử cấm một chuỗi rồi quét cả tệp, nên nó bắt luôn đoạn giải thích vì
    sao chuỗi ấy bị cấm.
    """
    return re.sub(r"\{/\*.*?\*/\}|/\*.*?\*/|//[^\n]*", "", s, flags=re.S)


# ═══════ LUẬT 3 · CHĂM SÓC: ĐANG TẢI KHÁC VỚI KHÔNG CÓ GÌ ═══════
def test_bang_cham_soc_phan_biet_dang_tai_voi_khong_co_phieu():
    ma = _bo_chu_thich(_tsx("web", "app", "cham-soc", "page.tsx"))
    assert "dangTai" in ma, "màn hình Chăm sóc chưa có cờ đang tải"
    assert re.search(r"\{dangTai\s*\n?\s*\?", ma), \
        "câu rỗng phải nằm ở nhánh SAU khi hết đang tải, không phải in vô điều kiện"
    i_tai = ma.index("Đang tải")
    i_rong = ma.index("Không có phiếu nào")
    assert i_tai < i_rong, "nhánh đang tải phải đứng trước nhánh không có phiếu"


def test_hang_rao_cham_soc_bat_duoc_ban_cu():
    """Tự kiểm: đưa đúng bản trước 29/9 vào thì hàng rào trên PHẢI đỏ."""
    cu = '{!ds.length && <tr><td colSpan={8} className="muted">Không có phiếu nào ở bộ lọc này.</td></tr>}'
    assert "dangTai" not in cu and not re.search(r"\{dangTai\s*\n?\s*\?", cu)


# ═══════ LUẬT 4 · BÁO CÁO BÁN HÀNG: CẮT BẢNG THÌ PHẢI NÓI RA ═══════
def test_bang_chi_tiet_bao_cao_ban_hang_bi_cat_va_noi_ra():
    ma = _bo_chu_thich(_tsx("web", "app", "sales-reports", "page.tsx"))
    assert "CT_TOI_DA" in ma, "chưa có mức trần số dòng chi tiết"
    assert "rep.detail.slice(0, CT_TOI_DA)" in ma, "bảng chi tiết vẫn dựng toàn bộ số dòng"
    assert not re.search(r"rep\.detail\.map\(", ma), \
        "còn một chỗ dựng thẳng rep.detail.map – đó là chỗ làm trang nặng 900 KB"
    assert "Đang hiện" in ma and "trong tổng số" in ma, \
        "cắt bảng mà không nói đã cắt: người đọc sẽ cộng tay phần thấy được rồi tưởng là tổng"
    assert "Xuất Excel" in ma, "phải chỉ chỗ lấy đủ dòng, nếu không cắt bảng là mất dữ liệu"


def test_may_chu_van_tra_du_dong_cho_ban_excel():
    """Mức trần là chuyện của TRÌNH DUYỆT. Máy chủ mà cũng cắt thì bản Excel thiếu dòng mà không ai
    biết – nên phép thử này canh rằng bản Excel lấy thẳng `rep["detail"]`, không qua mức trần nào."""
    ma = open(os.path.join(GOC, "backend", "app", "services", "sales_reports.py"),
              encoding="utf-8").read()
    assert 'sheet(wb.create_sheet(), "Chi tiết", rep["columns"]["detail"], rep["detail"])' in ma


def test_hang_rao_bao_cao_bat_duoc_ban_cu():
    cu = '<tbody>{rep.detail.map((r: any, i: number) =>'
    assert re.search(r"rep\.detail\.map\(", cu) and "CT_TOI_DA" not in cu


# ═══════ LUẬT 5 · MỘT MÀN HÌNH PHẢI NÓI ĐƯỢC NÓ LÀ MÀN HÌNH NÀO ═══════
def test_man_hinh_dung_chung_doi_tieu_de_theo_phan_he():
    ma = _bo_chu_thich(_tsx("web", "components", "HrScreens.tsx"))
    assert not re.search(r"<h1>Nhân sự – Lương \(robot R6\)</h1>", ma), \
        "tiêu đề vẫn ghi cứng: vào từ Điều hành cũng hiện chữ Nhân sự – Lương"
    assert re.search(r'<h1>\{scope === "ops"', ma), "tiêu đề chưa theo phân hệ đang vào"
    assert "Điều hành" in ma and "Nhân sự – Lương (robot R6)" in ma, \
        "phải còn đủ cả hai tiêu đề – đổi nhãn, không phải bỏ nhãn cũ"


def test_man_hinh_visa_co_tieu_de():
    ma = _bo_chu_thich(_tsx("web", "app", "visa", "page.tsx"))
    assert "<h1>" in ma, "/visa là màn hình duy nhất của bốn phòng không có tiêu đề"


def test_moi_man_hinh_cua_bon_phong_deu_co_tieu_de():
    """Canh rộng ra cả nhóm, để lần sau không phải rà bằng mắt nữa.

    Nhận cả <h1> lẫn <h2>: nhà này không thống nhất một thẻ — `/so-con-no` và `/lai-lo-tour` mở
    đầu bằng <h2> và vẫn đọc ra tên màn hình đàng hoàng. Điều phải canh là MÀN HÌNH CÓ TÊN, không
    phải nó dùng thẻ nào; siết về đúng một thẻ là một vòng khác, không phải vòng này."""
    thieu = []
    for duong in ("marketing", "noi-dung", "bao-chi-kol", "chuyen-doi-lead", "dong-gop-marketing",
                  "doi-soat-marketing", "cham-soc", "khieu-nai", "kinh-doanh-le", "sales-reports",
                  "bao-gia", "non-package", "bang-gia", "hop-dong-khach", "to-chuc-kd",
                  "nguoi-ban-hang", "tours", "products", "requests", "so-con-no", "su-co-tour",
                  "lai-lo-tour", "nha-cung-cap", "visa", "doi-xe", "lenh-dieu-xe",
                  "hieu-qua-doi-xe", "lai-lo-doi-xe", "huong-dan", "xe-hdv"):
        tep = os.path.join(GOC, "web", "app", duong, "page.tsx")
        if not os.path.exists(tep):
            continue
        ma = open(tep, encoding="utf-8").read()
        if "<h1" not in ma and "<h2" not in ma:
            thieu.append(duong)
    assert not thieu, f"màn hình không có tiêu đề: {', '.join(thieu)}"
