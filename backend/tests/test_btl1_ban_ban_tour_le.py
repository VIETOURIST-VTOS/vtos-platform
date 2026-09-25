"""BTL-1 · Bàn bán tour lẻ — Chủ tịch quyết 25/9/2026.

    "Trên quyết toán tour đã có thông tin tour, dự toán 3 con số — nối cái này về cho PKDL."

Màn hình này là cái "nối về" ấy. Phép thử canh ba thứ, theo đúng thứ tự dễ hỏng:

    1. Nó chỉ chở BA CON SỐ. Không một tên nhà cung cấp, một đơn giá mua, một số đã chi nào lọt
       sang — vì đó là ranh giới "không liên quan giá vốn".
    2. Nó chỉ chở tour LẺ đang bán. Một tour đoàn lọt vào đây là phòng Lẻ nhìn thấy dự toán của
       phòng Đoàn, đúng chiều Chủ tịch bảo giữ nguyên.
    3. `None` KHÁC 0. Chuyến chưa có dự toán riêng thì lợi nhuận là RỖNG, không phải 0 — và không
       phải "biên 100%", đúng bệnh Ý kiến thẩm định 06/9/2026 đã bắt.
"""
import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.services import ban_tour_le as BTL

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("nvdh", "nv_dh"), ("sadmin", "sales_admin")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _tour(db, ma, loai="le_noi_dia", ngay=10, status="da_duyet",
          gia=5_000_000, fc=20_000_000, vc=2_000_000, cho=20):
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=HOM_NAY + dt.timedelta(days=ngay),
             end_date=HOM_NAY + dt.timedelta(days=ngay + 2), operator_id=_u(db, "nvdh").id,
             status=status, price_per_pax=gia, fixed_cost=fc, var_cost_per_pax=vc,
             planned_pax=cho, seats_open=cho)
    db.add(t); db.commit(); return t


def _ban(db, t, n):
    # Đánh số tiếp từ số booking đã có: gọi `_ban` hai lần trên cùng chuyến (bán thêm) là chuyện
    # phép thử làm thật, và bắt đầu lại từ 0 thì đụng ràng buộc mã duy nhất.
    bat_dau = len(t.bookings)
    for i in range(bat_dau, bat_dau + n):
        r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name=f"K{i}",
                           customer_phone=f"090000{i:04d}", source="web", pax=1)
        db.add(r); db.flush()
        db.add(Booking(code=f"{t.code}-B{i}", tour_id=t.id, request_id=r.id,
                       sales_id=_u(db, "nvkd").id, created_by=_u(db, "nvdh").id,
                       customer_name=f"K{i}", customer_phone=f"090000{i:04d}", source="web",
                       pax=1, amount=t.price_per_pax))
    db.commit()


# ───────────────────── 1 · chỉ ba con số ─────────────────────

def test_btl1_dong_chi_co_ba_con_so_va_so_tinh_ra_tu_chung():
    db = _db(); _tour(db, "L1")
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["gia_ban"] == 5_000_000 and r["chi_phi_co_dinh"] == 20_000_000
    assert r["chi_phi_theo_khach"] == 2_000_000
    assert r["hoa_von_khach"] and r["loi_nhuan_ke_hoach"] is not None and r["bien_ke_hoach"] is not None


def test_btl2_KHONG_mot_chu_nao_ve_nha_cung_cap_lot_sang():
    """Đây là phép thử quan trọng nhất của tệp. Bàn này mở cho cả phòng Kinh doanh Lẻ; một khoá
    thừa ở đây là giá mua của công ty phát cho bốn vai, và không ai bấm nút nào để nó xảy ra."""
    db = _db(); _tour(db, "L1")
    r = BTL.ban_lam_viec(db)["rows"][0]
    cam = ("supplier", "nha_cung_cap", "ncc", "cost_line", "unit_price", "actual", "paid",
           "chung_tu", "settlement", "quyet_toan", "but_toan", "payment_request")
    thua = [k for k in r for c in cam if c in k.lower()]
    assert not thua, f"dòng chở khoá thuộc giá vốn thật: {thua}"


def test_btl3_khong_doc_mot_dong_TourCostLine_nao():
    """Chặn bằng cách đo MÃ, không chỉ đo kết quả: một lần thêm `TourCostLine` vào đây sẽ không
    làm phép thử trên đỏ nếu người thêm cũng đặt tên khoá cho khéo."""
    nguon = open(BTL.__file__, encoding="utf-8").read()
    assert "TourCostLine" not in nguon and "settlement" not in nguon.replace("quyết toán", "")


# ───────────────────── 2 · chỉ tour lẻ đang bán ─────────────────────

def test_btl4_tour_DOAN_khong_lot_vao():
    """"Ý là PKDL, còn PKDĐ vẫn giữ nguyên." Chiều ngược lại cũng phải đúng: phòng Lẻ không nhìn
    sang dự toán của phòng Đoàn."""
    db = _db(); _tour(db, "L1"); _tour(db, "D1", loai="doan_noi_dia")
    ma = [r["code"] for r in BTL.ban_lam_viec(db)["rows"]]
    assert ma == ["L1"]


def test_btl5_tour_le_mang_ma_MICE_la_tour_DOAN_nen_cung_khong_lot_vao():
    """Câu SQL lọc theo LOẠI chuyến, nhưng "đoàn hay lẻ" có định nghĩa duy nhất ở `segments`: hợp
    của loại chuyến VÀ quy ước mã MICE. Lọc một bước là tin câu SQL hơn tin luật."""
    db = _db(); _tour(db, "L1"); _tour(db, "MICE2609", loai="le_noi_dia")
    ma = [r["code"] for r in BTL.ban_lam_viec(db)["rows"]]
    assert ma == ["L1"], "tour mã MICE thuộc mảng Đoàn – không nằm trên bàn phòng Lẻ"


def test_btl6_chuyen_chua_duyet_va_chuyen_da_khoi_hanh_khong_nam_o_day():
    db = _db()
    _tour(db, "L1")
    _tour(db, "L2", status="nhap")
    _tour(db, "L3", ngay=-5)
    assert [r["code"] for r in BTL.ban_lam_viec(db)["rows"]] == ["L1"]


def test_btl7_sap_theo_ngay_khoi_hanh_gan_nhat():
    """Người bán đọc từ trên xuống và chuyến gấp nhất là chuyến cần bán trước."""
    db = _db(); _tour(db, "L9", ngay=30); _tour(db, "L1", ngay=3); _tour(db, "L5", ngay=12)
    assert [r["code"] for r in BTL.ban_lam_viec(db)["rows"]] == ["L1", "L5", "L9"]


# ───────────────────── 3 · rỗng khác 0 ─────────────────────

def test_btl8_chuyen_CHUA_co_du_toan_thi_loi_nhuan_RONG_chu_khong_phai_0():
    """Thiếu giá vốn mà in "0 đ · biên 100%" là đúng bệnh Ý kiến thẩm định 06/9/2026 đã bắt: cổng
    biên từng luôn báo ĐẠT vì giá vốn rỗng bị xử như 0."""
    db = _db(); _tour(db, "L1", fc=0, vc=0)
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["loi_nhuan_ke_hoach"] is None and r["bien_ke_hoach"] is None
    assert r["loi_nhuan_tai_so_dang_ban"] is None
    assert r["trang_thai_cong"] == "chua_du_co_so"


def test_btl9_hai_con_so_loi_nhuan_KHAC_nhau_va_deu_dung():
    """Lợi nhuận KẾ HOẠCH tính ở số khách dự toán; TẠI SỐ ĐANG BÁN tính ở số khách đã bán thật.
    In một số mà gọi tên số kia là cách nhanh nhất để mất lòng tin vào cả bảng."""
    db = _db(); t = _tour(db, "L1"); _ban(db, t, 8)
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["cho_da_ban"] == 8 and r["cho_con"] == 12
    assert r["loi_nhuan_ke_hoach"] == (5_000_000 - 2_000_000) * 20 - 20_000_000
    assert r["loi_nhuan_tai_so_dang_ban"] == (5_000_000 - 2_000_000) * 8 - 20_000_000


def test_btl10_con_thieu_de_hoa_von_dem_dung_va_khong_am():
    db = _db(); t = _tour(db, "L1"); _ban(db, t, 3)
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["hoa_von_khach"] == 7 and r["con_thieu_de_hoa_von"] == 4
    _ban(db, t, 9)
    r = BTL.ban_lam_viec(db)["rows"][0]
    assert r["cho_da_ban"] == 12 and r["con_thieu_de_hoa_von"] == 0, "bán quá hòa vốn không ra số âm"


# ───────────────────── cửa và quyền ─────────────────────

def test_btl11_cua_chi_DOC_khong_co_mot_lenh_ghi_nao():
    """Bàn làm việc chỉ đọc. Cửa ghi của vai này là cửa BÁN ở `/api/v1/requests`."""
    from app.api.v1 import ban_tour_le as API
    nguon = open(API.__file__, encoding="utf-8").read()
    assert "@router.post" not in nguon and "@router.put" not in nguon and "@router.delete" not in nguon


def test_btl12_danh_sach_vai_KHONG_co_phong_DOAN():
    from app.api.v1 import ban_tour_le as API
    for vai in ("sales_admin", "ptgd_doan"):
        assert vai not in API.XEM, f"{vai} thuộc phòng Đoàn – Chủ tịch nói giữ nguyên, không nới"
    for vai in ("nv_kd", "tn_kd", "tp_kd", "gd_kd"):
        assert vai in API.XEM


def test_btl13_hai_bang_khai_quyen_KHOP_nhau():
    """Danh sách vai của cửa API và dòng MENU_ROLES lệch nhau thì có vai thấy mục menu rồi bấm vào
    nhận 403, hoặc mở được màn hình mà không có mục menu."""
    from app.api.v1 import ban_tour_le as API
    from app.services import access as AC
    assert set(API.XEM) == set(AC.MENU_ROLES["/ban-tour-le"])


def test_btl14_loi_luu_y_di_CUNG_du_lieu_chu_khong_nam_trong_ma_man_hinh():
    """Màn hình có thể được viết lại; câu cảnh báo "đây không phải bằng chứng lãi lỗ" là một phần
    của con số, nên nó đi cùng con số."""
    db = _db(); _tour(db, "L1")
    luu_y = BTL.ban_lam_viec(db)["luu_y"]
    assert "dự toán" in luu_y.lower() and "quyết toán" in luu_y.lower()
