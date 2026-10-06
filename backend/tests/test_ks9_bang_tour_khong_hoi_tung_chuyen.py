# -*- coding: utf-8 -*-
"""BẢNG TOUR KHÔNG ĐƯỢC HỎI CƠ SỞ DỮ LIỆU MỘT LƯỢT CHO MỖI CHUYẾN.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Ngày 30/9/2026 robot Kiểm soát ghi `GET /api/v1/tours` chạy 16–30 giây trên hệ thật, và cửa ấy
nằm dưới cả màn hình Chủ tịch (13,5 giây) lẫn Bàn bán tour lẻ (18 giây) — ba màn hình chậm, một
nguyên nhân.

Đo bằng bộ đếm câu truy vấn, trên đúng đường mà cửa ấy đi:

     5 chuyến →   9 lượt truy vấn  (trong vòng lặp:  5)
    20 chuyến →  24 lượt truy vấn  (trong vòng lặp: 20)
    80 chuyến →  84 lượt truy vấn  (trong vòng lặp: 80)

ĐÚNG MỘT LƯỢT MỖI CHUYẾN. Lượt ấy là câu tra sản phẩm trong `rules.budget_of`. Màn hình mặc định
lấy 300 chuyến, nên mỗi lần mở bảng tour là 300 vòng đi–về tới cơ sở dữ liệu nằm ở máy khác.

Điều đáng ghi: KS-5 hồi 11/9 ĐÃ dọn N+1 ở chính cửa này — `t.operator`, `t.bookings`, `b.sales`
gom lại bằng `selectinload`, và chú thích của nó vẫn còn nguyên bên trên. Câu tra sản phẩm sót
lại vì nó KHÔNG phải một quan hệ ORM: `product_code` là một cột chữ, `selectinload` không với
tới. Dọn N+1 bằng `selectinload` chỉ dọn được phần đi qua quan hệ; phần tra cứu bằng TAY trong
thân hàm phải tự nạp lấy — và không có phép thử nào ĐẾM, nên phần sót không ai thấy suốt 19 ngày.

Nên phép thử ở đây ĐẾM, chứ không bấm giờ. Bấm giờ trên máy chạy phép thử là đo cái máy ấy; đếm
câu truy vấn thì đo đúng thứ sinh ra độ chậm và cho ra cùng một con số ở mọi máy.

Hai nửa phải giữ CÙNG LÚC, vì mỗi nửa một mình đều dễ:
  · nhanh  — số lượt truy vấn KHÔNG tăng theo số chuyến;
  · đúng   — con số dự toán ra y hệt lúc chưa nạp sẵn. Nhanh mà sai thì tệ hơn chậm.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import datetime as dt                                           # noqa: E402

from sqlalchemy import create_engine, event, select, desc       # noqa: E402
from sqlalchemy.orm import sessionmaker, selectinload           # noqa: E402

from app.db.session import Base                                 # noqa: E402
from app.models.core import Booking, Company, Product, Tour, User   # noqa: E402
from app.services import rules as R                             # noqa: E402
from app.services import tours as T                             # noqa: E402


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return e, sessionmaker(bind=e)()


def _dung(db, n: int, moi_chuyen_mot_san_pham: bool = True):
    """n chuyến, mỗi chuyến MỘT sản phẩm riêng — hình xấu nhất và cũng là hình thật.

    Nếu mọi chuyến dùng chung một sản phẩm thì một cái đệm theo khoá cũng đủ nhanh, và phép thử sẽ
    xanh với một cách sửa không chịu nổi dữ liệu thật.
    """
    c = Company(code="VTD", name="VTD", kind="me", active=True); db.add(c)
    u = User(username="dh", full_name="DH", role="nv_dh", password_hash="x"); db.add(u); db.commit()
    for i in range(n):
        db.add(Product(code=f"P{i}", name=f"SP{i}",
                       cost_lines=[{"kind": "co_dinh", "so_tien": 1000 + i},
                                   {"kind": "theo_khach", "don_gia": 10 + i, "sl": 1}]))
    db.commit()
    for i in range(n):
        t = Tour(code=f"T{i}", name=f"C{i}", company_id=c.id, tour_type="le_noi_dia",
                 start_date=dt.date(2026, 3, 1), end_date=dt.date(2026, 3, 5), operator_id=u.id,
                 product_code=f"P{i}" if moi_chuyen_mot_san_pham else "P0",
                 price_per_pax=100, planned_pax=10, status="da_duyet")
        db.add(t); db.commit()
        for k in range(3):
            db.add(Booking(code=f"B{i}-{k}", customer_name="K", customer_phone="0", source="web",
                           pax=2, tour_id=t.id, request_id=f"R{i}-{k}", sales_id=u.id,
                           created_by="dh", amount=100))
        db.commit()


def _cau_truy_van_tour(db):
    return (select(Tour).order_by(desc(Tour.start_date))
            .options(selectinload(Tour.operator),
                     selectinload(Tour.bookings).selectinload(Booking.sales)))


def _dem_mot_lo(n: int) -> tuple[int, int]:
    """(tổng lượt truy vấn của cả lô, số chuyến) — đi ĐÚNG đường của `GET /api/v1/tours`."""
    e, db = _db()
    _dung(db, n)
    qs = _cau_truy_van_tour(db)
    # Làm nóng đệm tham số trước khi đếm: `get_param` có đệm 60 giây dùng chung cả tiến trình, nên
    # nếu không hâm trước thì lô đầu tiên gánh hết phần đọc tham số và ba con số đo được sẽ lệch
    # nhau vì một lý do chẳng liên quan gì tới thứ đang đo.
    T.tour_view(db, db.query(Tour).first())
    R.quen_kho_san_pham(db)

    so = [0]

    @event.listens_for(e, "before_cursor_execute")
    def _dem(conn, cur, st, par, ctx, many):     # noqa
        so[0] += 1

    rows = list(db.execute(qs).scalars())
    truoc = so[0]
    R.nap_san_du_toan(db, rows)
    for t in rows:
        T.tour_view(db, t, kem_bookings=False)
    return so[0] - truoc, len(rows)


# ============================== 1. NHANH: KHÔNG TĂNG THEO SỐ CHUYẾN ==============================
def test_so_luot_truy_van_khong_tang_theo_so_chuyen():
    """PHÉP THỬ BẮT ĐÚNG LỖI GỐC.

    Trước khi sửa, ba con số này là 5 · 20 · 80 — tăng đúng bằng số chuyến. Sau khi sửa, cả ba
    phải bằng nhau: một câu nạp cả lô, rồi thôi.
    """
    do = {n: _dem_mot_lo(n)[0] for n in (5, 20, 80)}
    assert do[5] == do[20] == do[80], (
        f"Số lượt truy vấn tăng theo số chuyến: {do}. Với 300 chuyến trên màn hình thật, mỗi lượt "
        f"là một vòng đi–về tới cơ sở dữ liệu đặt ở máy khác.")
    assert do[80] <= 3, f"Nạp cả lô mà vẫn tốn {do[80]} lượt — nhiều hơn một câu là có chỗ còn sót"


def test_khong_nap_san_thi_phep_thu_nay_do_duoc():
    """TỰ KIỂM: dựng lại đúng cảnh cũ và đòi nó phải LỘ RA.

    Không có dòng này thì phép thử trên có thể xanh vì một lý do khác — ví dụ bộ đếm gắn nhầm chỗ
    và không đếm được gì cả. Ở đây bỏ bước nạp sẵn đi, và số lượt PHẢI tăng theo số chuyến.
    """
    def dem_khong_nap(n):
        e, db = _db()
        _dung(db, n)
        qs = _cau_truy_van_tour(db)
        T.tour_view(db, db.query(Tour).first())
        R.quen_kho_san_pham(db)
        so = [0]
        event.listen(e, "before_cursor_execute", lambda *a: so.__setitem__(0, so[0] + 1))
        rows = list(db.execute(qs).scalars())
        truoc = so[0]
        for t in rows:                      # CỐ Ý không gọi nap_san_du_toan
            T.tour_view(db, t, kem_bookings=False)
        return so[0] - truoc

    assert dem_khong_nap(20) > dem_khong_nap(5), (
        "Bộ đếm không thấy chênh lệch nào kể cả khi bỏ hẳn bước nạp sẵn — nó đang đếm nhầm chỗ, "
        "nên phép thử ở trên xanh mà không chứng minh được gì.")


# ============================== 2. ĐÚNG: CON SỐ KHÔNG ĐỔI ==============================
def test_con_so_du_toan_y_het_khi_nap_san():
    """Nhanh mà sai thì tệ hơn chậm. So từng chuyến, đường cũ với đường mới."""
    e, db = _db()
    _dung(db, 12)
    rows = list(db.execute(_cau_truy_van_tour(db)).scalars())

    R.quen_kho_san_pham(db)
    cu = [R.budget_of(db, t) for t in rows]
    R.nap_san_du_toan(db, rows)
    moi = [R.budget_of(db, t) for t in rows]

    assert cu == moi, f"Nạp sẵn làm ĐỔI con số dự toán:\n cũ  {cu}\n mới {moi}"
    assert {x[2] for x in moi} == {"san_pham"}, "Mất đường dự toán tham chiếu từ sản phẩm"


def test_chuyen_ngoai_lo_van_ra_dung_so():
    """Chuyến KHÔNG nằm trong lô đã nạp phải rơi về đường truy vấn cũ, không bị đọc thành “không có”.

    Đây là chỗ một cái đệm dễ nói dối nhất: kho có mặt nhưng không chứa khoá của chuyến này, và
    bản viết cẩu thả sẽ đọc “không thấy trong kho” thành “sản phẩm không tồn tại” — dự toán tụt về
    0 trong im lặng, biên lợi nhuận sai, cảnh báo dưới biên không nổ.
    """
    e, db = _db()
    _dung(db, 6)
    rows = list(db.execute(_cau_truy_van_tour(db)).scalars())
    R.quen_kho_san_pham(db)
    R.nap_san_du_toan(db, rows[:2])          # chỉ nạp 2 chuyến đầu
    for t in rows[2:]:
        f, v, nguon = R.budget_of(db, t)
        assert nguon == "san_pham" and (f > 0 or v > 0), (
            f"Chuyến {t.code} ngoài lô bị đọc thành không có dự toán: {(f, v, nguon)}")


def test_san_pham_khong_co_that_chi_tra_mot_lan():
    """“Đã tra, không có” khác “chưa tra”. Không phân biệt được thì mỗi chuyến thiếu sản phẩm lại
    đẻ ra một câu truy vấn — đúng cái việc vòng này sinh ra để bỏ."""
    e, db = _db()
    _dung(db, 4)
    for t in db.query(Tour).all():
        t.product_code = "KHONG-CO-MA-NAY"
    db.commit()
    rows = list(db.execute(_cau_truy_van_tour(db)).scalars())
    R.quen_kho_san_pham(db)
    R.nap_san_du_toan(db, rows)
    so = [0]
    event.listen(e, "before_cursor_execute", lambda *a: so.__setitem__(0, so[0] + 1))
    ra = [R.budget_of(db, t) for t in rows]
    assert so[0] == 0, f"Sản phẩm không tồn tại vẫn bị tra lại {so[0]} lần"
    assert {x[2] for x in ra} == {"chua_co"}, "Mất trạng thái “chưa có dự toán”"


def test_product_id_tro_vao_hang_da_xoa_van_tra_theo_ma():
    """`budget_of` hỏi CẢ HAI đường: id trước, không có thì tra theo mã. Nạp thiếu một đường là
    làm con số đổi, nên nạp sẵn phải mang theo cả hai."""
    e, db = _db()
    _dung(db, 3)
    for t in db.query(Tour).all():
        t.product_id = 9999                  # hàng không tồn tại
    db.commit()
    rows = list(db.execute(_cau_truy_van_tour(db)).scalars())
    R.quen_kho_san_pham(db)
    R.nap_san_du_toan(db, rows)
    for t in rows:
        f, v, nguon = R.budget_of(db, t)
        assert nguon == "san_pham", f"Mất đường tra theo mã khi product_id treo: {(f, v, nguon)}"


# ============================== 3. BỎ DANH SÁCH KHÁCH MÀ KHÔNG BỎ SỐ KHÁCH ==============================
def test_kem_bookings_false_khong_kem_danh_sach_khach():
    e, db = _db()
    _dung(db, 2)
    t = db.query(Tour).first()
    assert "bookings" not in T.tour_view(db, t, kem_bookings=False)
    assert "bookings" in T.tour_view(db, t), "Mặc định vẫn phải kèm — mọi nơi gọi cũ không được đổi"


def test_bo_danh_sach_khach_nhung_so_khach_van_dung():
    """`booked_pax` đọc `t.bookings` để đếm. Bỏ nhầm chỗ ấy thì số chỗ đã bán về 0 trên cả bảng,
    và điểm hoà vốn D-7 đọc sai theo."""
    e, db = _db()
    _dung(db, 2)
    t = db.query(Tour).first()
    co = T.tour_view(db, t)
    khong = T.tour_view(db, t, kem_bookings=False)
    assert khong["booked_pax"] == co["booked_pax"] == 6, khong["booked_pax"]
    assert khong["calc"] == co["calc"], "Bỏ danh sách khách làm đổi phép tính của chuyến"
