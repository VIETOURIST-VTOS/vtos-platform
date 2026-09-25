"""BCS-1 · Ba con số dự toán cho Kinh doanh Lẻ — Chủ tịch quyết 25/9/2026.

    "Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc bán."
    "Sales lẻ chỉ nhìn thấy dự toán 3 con số như trong file quyết toán tour của Điều hành."

Người bán cần biết chuyến còn lời bao nhiêu để trả lời khách xin giảm giá. Họ không cần biết công
ty mua của ai với giá nào. Ba con số là một BẢN TÓM TẮT; giá vốn là DANH SÁCH mình mua của ai —
hai thứ khác nhau, và ranh giới của Chủ tịch nằm đúng giữa chúng.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ HỞ TÌM RA KHI LÀM VIỆC NÀY, VÀ VÌ SAO NÓ KHÔNG AI THẤY
═══════════════════════════════════════════════════════════════════════════════════════════════
`GET /tours/{id}/detail` có một khối che ở GIỮA hàm. Nhưng `cost_lines`, `cost_total`,
`settlement_edit`, `payment_requests` và `audit` được gắn vào SAU khối ấy — nên chúng **chưa từng
bị che một lần nào**. Tên nhà cung cấp, đơn giá mua, số tiền đã chi đều nằm nguyên trong phản hồi
gửi cho Kinh doanh Lẻ.

Không ai thấy vì màn hình có che: tab "Chi NCC & quyết toán" bị ẩn khi `calc` rỗng. Nhưng màn hình
che không phải là cửa che — mở công cụ nhà phát triển của trình duyệt là đọc được. Đây là lý do
`che_gia_von` chạy ở BƯỚC CUỐI chứ không ở giữa hàm.
"""
import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour, User
from app.services import access as AC

HOM_NAY = dt.date.today()

LE = Tour(code="L1", name="Lẻ", tour_type="le_noi_dia", start_date=HOM_NAY, end_date=HOM_NAY,
          price_per_pax=3_000_000, fixed_cost=20_000_000, var_cost_per_pax=1_500_000, planned_pax=20)
DOAN = Tour(code="D1", name="Đoàn", tour_type="doan_noi_dia", start_date=HOM_NAY,
            end_date=HOM_NAY + dt.timedelta(days=2), price_per_pax=5_000_000,
            fixed_cost=30_000_000, var_cost_per_pax=2_000_000, planned_pax=30)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("gdkd", "gd_kd"), ("tnkd", "tn_kd"),
                     ("nvdh", "nv_dh"), ("hcns", "hcns"), ("ketoan", "ketoan"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _view():
    """Một bản `tour_view` rút gọn, đủ các khoá mà cửa chi tiết thật sự trả về."""
    return {
        "code": "L1", "price_per_pax": 3_000_000, "fixed_cost": 20_000_000,
        "var_cost_per_pax": 1_500_000, "calc": {"profit": 10_000_000, "margin": 0.16,
                                                "breakeven_pax": 14},
        "settlement": {"x": 1}, "actual_cost": 9, "promo_value": 1, "justification": "vì sao",
        "cost_lines": [{"supplier_name": "NCC A", "unit_price": 900_000}],
        "cost_total": {"actual": 900_000}, "settlement_edit": {"summary": {"actual": 900_000}},
        "payment_requests": [{"supplier_name": "NCC A", "amount": 900_000}],
        "audit": [{"action": "sua_du_toan", "before": {"fixed_cost": 1}}],
        "summary": {"revenue_booking": 60_000_000, "collected": 10_000_000,
                    "cost_actual": 900_000, "cost_paid": 900_000, "profit": 59_100_000,
                    "profit_state": "tam_tinh", "cost_basis": "quyet_toan", "warning": "…"},
        "bookings": [], "hoa_hong_khach_bien": None,
    }


# ───────────────────── bậc ba: mở ba con số ─────────────────────

def test_bcs1_kinh_doanh_LE_nhin_thay_ba_con_so_tren_tour_le():
    db = _db()
    for vai in ("nvkd", "tpkd", "gdkd", "tnkd"):
        v = AC.che_gia_von(_view(), _u(db, vai), LE, db)
        assert v["fixed_cost"] == 20_000_000, f"{vai} không thấy chi phí cố định"
        assert v["var_cost_per_pax"] == 1_500_000
        assert v["price_per_pax"] == 3_000_000


def test_bcs2_va_nhin_thay_LOI_NHUAN_BIEN_HOA_VON():
    """Chủ tịch chọn phương án "ba con số + lợi nhuận & biên" ngày 25/9: người bán trả lời khách
    xin giảm giá bằng chính con số ấy. Ba số máy tính RA TỪ ba con số dự toán, không thêm dữ liệu."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "nvkd"), LE, db)
    assert v["calc"] and v["calc"]["profit"] and v["calc"]["margin"] and v["calc"]["breakeven_pax"]


# ───────────────────── nhưng KHÔNG mở giá vốn ─────────────────────

def test_bcs3_KHONG_thay_dong_chi_phi_nha_cung_cap():
    """Đây là ranh giới "không liên quan giá vốn" của Chủ tịch. Ba con số là bản tóm tắt; dòng NCC
    là danh sách mình mua của ai với giá nào."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "nvkd"), LE, db)
    assert v["cost_lines"] == []
    assert v["payment_requests"] == []
    assert v["cost_total"] is None and v["settlement_edit"] is None and v["settlement"] is None


def test_bcs4_KHONG_thay_nhat_ky_sua_gia_von():
    """Nhật ký chép nguyên before/after của mỗi lần sửa dự toán — che bảng mà để hở nhật ký là
    che một nửa."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "nvkd"), LE, db)
    assert v["audit"] == []


def test_bcs5_KHONG_thay_chi_phi_THUC_TE_va_loi_nhuan_thuc_te():
    """Ba con số là DỰ TOÁN. Chi phí thực tế là kết quả của việc mua bán với NCC — cùng một loại
    thông tin với dòng NCC, chỉ ở dạng cộng gộp."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "nvkd"), LE, db)
    assert v["actual_cost"] is None and v["promo_value"] is None
    for k in ("cost_actual", "cost_paid", "profit", "profit_state", "cost_basis"):
        assert k not in v["summary"], f"summary còn để hở {k}"
    assert v["summary"]["revenue_booking"] == 60_000_000, "doanh thu booking là số của chính họ"
    assert v["summary"]["collected"] == 10_000_000


def test_bcs6_danh_sach_khoa_che_KHONG_giao_nhau():
    """Một khoá nằm ở cả hai danh sách là một khoá có hai luật — và luật nào thắng thì tuỳ thứ tự
    dòng lệnh, tức là tuỳ người sửa sau."""
    assert not (set(AC.CHE_GIA_VON) & set(AC.CHE_BA_CON_SO))


# ───────────────────── các bậc kia không xê dịch ─────────────────────

def test_bcs7_tren_chuyen_DOAN_kinh_doanh_van_thay_DU():
    """Lần nới này ở tour LẺ. Quyền của Kinh doanh Đoàn (24/9/2026) không đụng tới."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "nvkd"), DOAN, db)
    assert v["cost_lines"] and v["settlement"] and v["audit"]
    assert v["summary"]["profit"] == 59_100_000


def test_bcs8_HCNS_van_khong_thay_gi_ca():
    """HC-NS không thuộc khối Kinh doanh nên không lên bậc ba: họ mất cả ba con số."""
    db = _db()
    v = AC.che_gia_von(_view(), _u(db, "hcns"), LE, db)
    assert v["fixed_cost"] is None and v["var_cost_per_pax"] is None and v["calc"] is None
    assert v["cost_lines"] == []


def test_bcs9_dieu_hanh_va_ke_toan_khong_bi_che_gi():
    db = _db()
    for vai in ("nvdh", "ketoan", "ct"):
        v = AC.che_gia_von(_view(), _u(db, vai), LE, db)
        assert v["cost_lines"] and v["settlement_edit"] and v["actual_cost"] == 9


def test_bcs10_ba_bac_long_nhau_chu_khong_song_song():
    """Ai xem được bậc trên thì đương nhiên xem được bậc dưới. Ba vị từ song song rồi sẽ có một
    người ở bậc 2 mà không ở bậc 3 — và không ai biết điều đó có nghĩa gì."""
    db = _db()
    for vai in ("nvkd", "tpkd", "gdkd", "tnkd", "nvdh", "ketoan", "hcns", "ct"):
        u = _u(db, vai)
        for t in (LE, DOAN):
            if AC.can_see_cost_tren_chuyen(u, t):
                assert AC.can_see_du_toan_ba_con_so(u, t), f"{vai} ở bậc 2 mà không ở bậc 3"


# ───────────────────── tour lẻ: ai mở lịch khởi hành ─────────────────────

def test_bcs11_chi_DIEU_HANH_mo_lich_khoi_hanh_tour_le():
    """"Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc bán." Luật này đã có
    từ trước (ĐH Điều 2); phép thử canh nó ở đây để lần nới hôm nay không kéo theo cửa tạo."""
    import re
    from app.services import products as PS
    from app.services import tours as T
    nguon = re.sub(r"#[^\n]*", "", open(PS.__file__, encoding="utf-8").read())
    i = nguon.find("def open_tour")
    than = nguon[i:nguon.find("\ndef ", i + 10)]
    assert '"nv_dh", "tp_dh"' in than and '"nv_kd"' not in than, (
        "cửa mở chuyến từ sản phẩm đã cho Kinh doanh vào — tour lẻ là lịch của Điều hành")
    nguon2 = re.sub(r"#[^\n]*", "", open(T.__file__, encoding="utf-8").read())
    j = nguon2.find("def create(")
    than2 = nguon2[j:nguon2.find("\ndef ", j + 10)]
    assert "_la_doan" in than2, (
        "cửa tạo tour không còn phân biệt đoàn/lẻ — Kinh doanh chỉ được lập dự toán ĐOÀN")


def test_bcs12_lan_noi_nay_KHONG_dung_toi_cong_bien_va_hai_chu_ky():
    """Câu quan trọng nhất của tệp. Cho người bán nhìn thấy biên làm việc bớt biên có chủ ý dễ hơn
    — và thứ chặn điều đó không phải hàng rào xem, mà là cổng biên cộng hai chữ ký khi dưới biên."""
    from app.services import rules as R
    assert R.approver_role(LE) == "tgd"
    assert R.approver_role(DOAN) == "ptgd_doan"
