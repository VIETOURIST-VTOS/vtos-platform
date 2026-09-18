# -*- coding: utf-8 -*-
"""TC-47 · DOANH THU VÀ LÃI LẤY TỪ SỔ QUYẾT TOÁN CỦA CHUYẾN ĐÃ ĐÓNG SỐ, PHẠM VI VIETOURIST.

    "doanh thu và lợi nhuận là lấy thực tế từ tour đã bán hoàn thành, không phải kế hoạch của
     HĐQT... bỏ Vietrip chỉ tập trung vào doanh thu và lợi nhuận của Vietourist, các cty con và
     cty liên kết chỉ vào mục hợp nhất BCTC"            — anh Tuấn, 16/9/2026

Ba lựa chọn anh chốt sau đó: mốc là **Điều hành đóng số**, lãi tour lấy từ **sổ quyết toán tour**,
lợi nhuận trước thuế chỉ phạm vi **Vietourist mẹ**.

══════════════════════════════════════════════════════════════════════════════════════════════
SÁU CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. GIÁ VỐN RỖNG ĐỌC THÀNH 0. Chuyến chưa ai nhập giá vốn báo lãi bằng đúng doanh thu, biên 100%.
   Bảng vẫn cân nên không ai nhìn ra. Đây là lỗi ĐANG SỐNG trong `rules.settlement_summary`
   (`cost = (tour.actual_cost or 0) + …`), và là lý do tồn tại của cả `models/quyet_toan.py`.
2. GỘP CÔNG TY CON VÀO. Một chuyến của Vietrip cộng vào doanh thu Vietourist thì con số trên màn
   hình Chủ tịch là số hợp nhất mang nhãn công ty mẹ — sai mà nhìn không khác gì đúng.
3. CHUYẾN CHƯA GÁN PHÁP NHÂN BIẾN MẤT. Không thuộc mẹ, nên bị lọc ra; nếu không có chỗ hiện thì
   doanh thu của nó rơi khỏi mọi con mắt. Luật `pham_vi_phap_nhan` số 2: không gộp im lặng, cũng
   không giấu.
4. MỐC VẪN LÀ NGÀY KẾ TOÁN XÁC NHẬN. Chuyến đóng số 30/8, Kế toán duyệt 12/9 thì rơi vào tháng 9 —
   doanh thu tháng 8 phụ thuộc tốc độ duyệt chứ không phụ thuộc việc bán được bao nhiêu.
5. DOANH THU CỘNG CẢ CHUYẾN THIẾU GIÁ VỐN CÒN LÃI THÌ KHÔNG. Mỗi con số đúng với chính nó, nhưng
   chúng đứng cạnh nhau trên một trục ngang và người đọc sẽ chia chúng — tử số của tập này chia
   cho mẫu số của tập kia. Đúng bài học TC-45: hai cuốn sổ cạnh nhau là lỗi dù không số nào sai.
6. LỢI NHUẬN TRƯỚC THUẾ VẪN CỘNG CẢ TẬP ĐOÀN. `journal_entries.company_id` đã có từ lâu và
   `pham_vi_phap_nhan.PHAI_LOC` đã khai bút toán ghi sổ là loại phải lọc, nhưng `income_statement`
   chưa lọc bao giờ.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
from app.services import ket_qua_that as KQ

GOC = Path(__file__).resolve().parents[2]
DICH_VU = GOC / "backend" / "app" / "services" / "ket_qua_that.py"
XU_HUONG = GOC / "backend" / "app" / "services" / "xu_huong.py"
BAO_CAO = GOC / "backend" / "app" / "services" / "reports.py"
KHOI = GOC / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_py(s: str) -> str:
    """Bỏ chuỗi tài liệu và chú thích — canh HÀNH VI, không canh chữ trong lời giải thích.

    Bài học TC-41: cấm một CHUỖI KÝ TỰ thì phép thử đỏ ngay trên chính đoạn chú thích giải thích
    vì sao chuỗi ấy bị cấm. Phải cấm một HÀNH VI.
    """
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


def _db():
    """Kho rỗng trong bộ nhớ, dựng ĐÚNG những bảng khai được — cùng cách với TC-44/45/46.

    Duyệt `tables.values()` chứ không `sorted_tables`: phép sắp xếp kia tự giải mọi khoá ngoại
    trước khi trả về, nên nó gãy ngay trước khi bộ lọc kịp chạy.
    """
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _so_gia():
    """Một tháng 8/2026 có đủ sáu tình huống — mỗi tình huống canh một chỗ hỏng ở đầu tệp."""
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    con = Company(code="VTR", name="Vận tải Vietrip", kind="con", active=True)
    db.add_all([me, con]); db.commit()
    u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
    db.add(u); db.commit()

    def them(code, cid, rev, cost, closed, status="da_dong_so", promo=None):
        db.add(Tour(code=code, name=code, tour_type="package",
                    start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 8, 3),
                    operator_id=u.id, status=status, actual_revenue=rev, actual_cost=cost,
                    promo_value=promo, closed_at=closed, company_id=cid))

    them("A", me.id, 100.0, 60.0, dt.datetime(2026, 8, 10))            # đủ số
    them("B", me.id, 50.0, None, dt.datetime(2026, 8, 11))             # thiếu giá vốn
    them("C", con.id, 999.0, 1.0, dt.datetime(2026, 8, 12))            # công ty con
    them("D", None, 77.0, 1.0, dt.datetime(2026, 8, 13))               # chưa gán pháp nhân
    them("E", me.id, 30.0, 10.0, dt.datetime(2026, 9, 1))              # tháng khác
    # Chuyến F: Kế toán ĐÃ TRẢ LẠI. `settlement.py` đặt `closed_at = None` cùng lúc với trạng thái
    # về `ket_thuc` — nên trong sổ thật, một chuyến chưa đóng số thì không có ngày đóng số. Dựng số
    # giả đúng như thế, chứ không dựng một chuyến "ket_thuc mà vẫn có closed_at": số giả không tồn
    # tại được ngoài đời chỉ dạy phép thử canh một tình huống không bao giờ xảy ra.
    them("F", me.id, 40.0, 20.0, None, "ket_thuc")
    db.commit()
    return db, me, u


# ═════════════════ 1 · RỖNG KHÁC KHÔNG ═════════════════

def test_gia_von_rong_thi_chuyen_ay_khong_co_lai_chu_khong_lai_bang_doanh_thu():
    """Chỗ hỏng số 1 — chỗ nguy hiểm nhất của cả vòng."""
    db, me, u = _so_gia()
    t = db.query(Tour).filter_by(code="B").one()
    assert KQ._lai(t) is None, (
        "Chuyến chưa ai nhập giá vốn phải KHÔNG CÓ lãi. Đọc rỗng thành 0 là báo lãi 100% trên "
        "toàn bộ doanh thu chuyến ấy, và bảng vẫn cân nên không ai nhìn ra."
    )
    du = db.query(Tour).filter_by(code="A").one()
    assert KQ._lai(du) == 40.0


def test_ma_nguon_khong_con_doc_gia_von_rong_thanh_khong():
    """Canh HÀNH VI: trong tệp này không được có `actual_cost or 0`.

    Cấm đúng cái biểu thức làm rỗng thành 0, chứ không cấm chữ "actual_cost" — hàm còn phải đọc
    cột ấy thì mới tính được.
    """
    ma = _ma_py(_doc(DICH_VU))
    assert not re.search(r"actual_cost\s+or\s+0", ma), (
        "`actual_cost or 0` là chính cái lỗi vòng này sinh ra để chữa."
    )
    assert "actual_cost is None" in ma, "Phải hỏi thẳng 'giá vốn có rỗng không'."


def test_khuyen_mai_van_la_mot_dong_gia_von():
    """`promo_value` rỗng thì coi là 0 — khác hẳn giá vốn rỗng.

    Mã khuyến mại không phát sinh là một sự thật ("không giảm giá đồng nào"), còn giá vốn không
    phát sinh thì không: mọi chuyến đều có giá vốn (chỉ đạo 08/9 của Chủ tịch).
    """
    db, me, u = _so_gia()
    t = db.query(Tour).filter_by(code="A").one()
    t.promo_value = 15.0; db.commit()
    assert KQ._lai(t) == 25.0, "Giá trị mã KM là một dòng giá vốn nội bộ (ĐC Điều 3)."


# ═════════════════ 2 và 3 · PHẠM VI PHÁP NHÂN ═════════════════

def test_chuyen_cua_cong_ty_con_khong_cong_vao_vietourist():
    """Chỗ hỏng số 2. Chuyến C có 999 đ doanh thu — không được lọt vào con số nào của mẹ."""
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["doanh_thu"] == 100.0 and r["lai_tour"] == 40.0
    assert r["dt_thieu_gia_von"] == 50.0
    assert 999.0 not in (r["doanh_thu"], r["lai_tour"], r["dt_thieu_gia_von"],
                         r["dt_chua_gan_phap_nhan"]), (
        "Doanh thu công ty con cộng vào Vietourist là số hợp nhất mang nhãn công ty mẹ."
    )


def test_chuyen_chua_gan_phap_nhan_khong_gop_va_cung_khong_bien_mat():
    """Chỗ hỏng số 3 — luật `pham_vi_phap_nhan` số 1 và số 2, cả hai cùng lúc."""
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["chua_gan_phap_nhan"] == 1 and r["dt_chua_gan_phap_nhan"] == 77.0, (
        "Chuyến chưa gán pháp nhân phải có chỗ hiện ra, kèm số tiền của nó."
    )
    assert r["doanh_thu"] == 100.0, "…nhưng không được cộng vào Vietourist."


def test_chua_co_cong_ty_me_thi_noi_ra_chu_khong_lay_cong_ty_dau_bang():
    """Đoán sai pháp nhân thì mọi con số tiền là của một công ty khác, mà nhìn thì y hệt."""
    db = _db()
    u = User(username="dh", full_name="ĐH", role="nv_dh", password_hash="x")
    db.add_all([Company(code="VTR", name="Vietrip", kind="con", active=True), u]); db.commit()
    assert KQ.cong_ty_me(db) is None
    r = KQ.thang(db, "2026-08")
    assert r["co_nguon"] is False, "Màn hình phải đọc được 'chưa có công ty mẹ trong danh mục'."


def test_cong_ty_me_da_tat_hoat_dong_khong_duoc_chon():
    db = _db()
    db.add(Company(code="CU", name="Pháp nhân cũ", kind="me", active=False)); db.commit()
    assert KQ.cong_ty_me(db) is None


# ═════════════════ 4 · MỐC LÀ NGÀY ĐÓNG SỐ ═════════════════

def test_moc_la_ngay_dong_so_khong_phai_ngay_ke_toan_xac_nhan():
    """Chỗ hỏng số 4. Đóng số 30/8, Kế toán duyệt 12/9 → vẫn là doanh thu THÁNG 8."""
    db, me, u = _so_gia()
    db.add(Tour(code="G", name="G", tour_type="package",
                start_date=dt.date(2026, 8, 20), end_date=dt.date(2026, 8, 25),
                operator_id=u.id, status="kt_xac_nhan", actual_revenue=200.0, actual_cost=120.0,
                closed_at=dt.datetime(2026, 8, 30), kt_confirmed_at=dt.datetime(2026, 9, 12),
                company_id=me.id))
    db.commit()
    t8 = KQ.thang(db, "2026-08")
    t9 = KQ.thang(db, "2026-09")
    assert t8["doanh_thu"] == 300.0, (
        "Doanh thu tháng 8 không được phụ thuộc vào tốc độ duyệt của Kế toán."
    )
    assert t9["doanh_thu"] == 30.0 and t9["lai_tour"] == 20.0, "Tháng 9 chỉ có chuyến E."


def test_chuyen_chua_dong_so_chua_tinh():
    """Chuyến F đã kết thúc hành trình nhưng Điều hành chưa bấm đóng số — chưa có số để tính."""
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["du_so"] == 1, "Chỉ chuyến A. Chuyến F còn ở 'ket_thuc'."


def test_ke_toan_tra_lai_thi_chuyen_roi_khoi_thang_va_man_hinh_noi_duoc_dieu_do():
    """Hệ quả phải chịu của mốc đóng số — và `da_khoa` là chỗ nói ra nó.

    `settlement.py` đặt `closed_at = None` khi Kế toán trả lại, nên chuyến rời khỏi tháng đã tính.
    Một tháng còn chuyến chưa khoá là một tháng con số còn nhúc nhích được.
    """
    db, me, u = _so_gia()
    assert KQ.thang(db, "2026-08")["da_khoa"] is False
    for t in db.query(Tour).filter(Tour.company_id == me.id).all():
        if t.closed_at and t.closed_at.month == 8:
            t.status = "khoa"
    db.commit()
    assert KQ.thang(db, "2026-08")["da_khoa"] is True

    t = db.query(Tour).filter_by(code="A").one()
    t.status, t.closed_at = "ket_thuc", None
    db.commit()
    assert KQ.thang(db, "2026-08")["doanh_thu"] is None, (
        "Chuyến bị trả lại phải rời khỏi tháng, không ở lại với con số cũ."
    )


def test_thang_rong_tra_none_chu_khong_tra_khong():
    """0 đồng và 'chưa ai đóng số' là hai việc khác hẳn nhau."""
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-07")
    assert r["doanh_thu"] is None and r["lai_tour"] is None
    assert r["du_so"] == 0


# ═════════════════ 5 · HAI HÌNH PHẢI NÓI VỀ CÙNG MỘT TẬP CHUYẾN ═════════════════

def test_doanh_thu_va_lai_tour_dung_cung_mot_tap_chuyen():
    """Chỗ hỏng số 5 — bài học TC-45 áp cho vòng này.

    Doanh thu 100 và lãi 40 cùng đến từ chuyến A. Nếu doanh thu cộng cả chuyến B (thiếu giá vốn)
    thành 150 thì biên đọc ra 27% trong khi biên thật của tập đang tính là 40%.
    """
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["doanh_thu"] == 100.0 and r["lai_tour"] == 40.0
    assert r["lai_tour"] / r["doanh_thu"] == 0.4


def test_phan_doanh_thu_bi_bo_ra_van_hien_duoc_thanh_khuc_mo():
    """Bỏ chuyến thiếu giá vốn ra khỏi cột chính là đúng — làm mất tiền của nó thì không."""
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["thieu_gia_von"] == 1 and r["dt_thieu_gia_von"] == 50.0


def test_khoi_man_hinh_ve_khuc_cho_va_noi_ten_bo_phan():
    """Màn hình phải bày phần còn thiếu, kèm bộ phận đi nhập — ranh giới 09/9."""
    ma = _doc(KHOI)
    assert "con_thieu" in ma, "Khối phải đọc dòng 'còn thiếu' mà máy chủ trả về."
    assert "Điều hành" in ma, "Phải nói rõ ai nhập giá vốn."


# ═════════════════ 6 · LỢI NHUẬN TRƯỚC THUẾ LỌC NGAY TRONG TRUY VẤN ═════════════════

def test_income_statement_nhan_pham_vi_phap_nhan():
    """Chỗ hỏng số 6, vế một: phải có cửa để lọc."""
    ma = _ma_py(_doc(BAO_CAO))
    assert "def income_statement(db: Session, period: str, company_id" in ma
    assert "JournalEntry.company_id == company_id" in ma, (
        "Lọc NGAY TRONG truy vấn, không cộng cả tập đoàn rồi trừ ra — cùng luật SEC-02."
    )


def test_mac_dinh_van_la_ca_tap_doan():
    """Thêm cửa lọc không được đổi ngầm số của bảng cân đối, lưu chuyển tiền và báo cáo hợp nhất."""
    ma = _ma_py(_doc(BAO_CAO))
    assert "company_id: int | None = None" in ma, (
        "Mặc định phải là None. Đổi ngầm phạm vi của những báo cáo không ai yêu cầu đổi là cách "
        "chắc chắn nhất để một con số đúng biến thành một con số sai mà không ai biết vì sao."
    )


def test_xu_huong_doc_loi_nhuan_theo_dung_pham_vi_me():
    """Chỗ hỏng số 6, vế hai: có cửa rồi thì phải đi qua cửa ấy."""
    ma = _ma_py(_doc(XU_HUONG))
    assert "company_id=me" in ma, (
        "Một con số của cả tập đoàn đứng dưới nhãn 'Vietourist' là sai tệ hơn một ô trống."
    )
    assert "_month_tours" not in ma, (
        "Phép tính cũ lọc theo ngày Kế toán xác nhận và không lọc pháp nhân — không còn dùng nữa."
    )


def test_khong_con_hai_cong_thuc_cho_cung_mot_cau_hoi():
    """Doanh thu tháng của công ty chỉ được tính ở ĐÚNG MỘT chỗ."""
    ma = _ma_py(_doc(XU_HUONG))
    # TC-64 (18/9/2026): thêm tham số `nho` — chỗ nhớ của MỘT lần dựng bảng, để một tháng không bị
    # hỏi ba lần (xem `ket_qua_kinh_doanh.bang`). Luật canh ở đây KHÔNG đổi: phải đi qua
    # `ket_qua_that`, không được tự viết truy vấn lần hai. Nên canh tiền tố của lời gọi.
    assert "KQ.thang(db, ky" in ma, "xu_huong phải đi qua ket_qua_that, không tự truy vấn."
    assert "settlement_summary" not in ma, (
        "`settlement_summary` là ống kính của quỹ thưởng (căn cứ là số Kế toán đã xác nhận), "
        "không phải ống kính 'công ty đang thế nào'. Hai câu hỏi khác nhau, hai phép tính khác "
        "nhau — nhưng mỗi câu chỉ một phép."
    )
