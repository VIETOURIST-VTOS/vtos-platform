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
    """Chỗ hỏng số 2. Chuyến C có 999 đ doanh thu — không được lọt vào con số nào của mẹ.

    LUẬT NÀY KHÔNG BỊ ĐẢO và không bao giờ được đảo: pháp nhân KHÁC thì không phải Vietourist.
    TC-71 chỉ đổi cách xử chuyến có pháp nhân RỖNG (xem phép thử ngay dưới) — rỗng là chưa ai
    điền, còn 'của Vận tải Vietrip' là đã điền và điền một cái tên khác.

    Con số kỳ vọng đổi vì TC-71 kéo thêm chuyến D (pháp nhân rỗng, 77) và chuyến F (chưa đóng sổ,
    40) vào. Điều phép thử này canh vẫn y nguyên: 999 không được xuất hiện ở bất kỳ đâu.
    """
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    # 217 = A(100) + D(77, pháp nhân rỗng) + F(40, chưa đóng sổ). Lãi 136 = 40 + 76 + 20.
    assert r["doanh_thu"] == 217.0 and r["lai_tour"] == 136.0
    assert r["dt_thieu_gia_von"] == 50.0
    assert 999.0 not in (r["doanh_thu"], r["lai_tour"], r["dt_thieu_gia_von"],
                         r["dt_chua_gan_phap_nhan"], r["dt_da_dong_so"], r["dt_chua_dong_so"]), (
        "Doanh thu công ty con cộng vào Vietourist là số hợp nhất mang nhãn công ty mẹ."
    )
    # Và canh chặt hơn bằng phép trừ: tổng của mẹ phải KHÔNG chứa 999 dù cộng kiểu nào.
    assert r["dt_da_dong_so"] + r["dt_chua_dong_so"] == 217.0 + 50.0, (
        "Hai nửa của con số gộp phải cộng lại đúng bằng tổng doanh thu của tập chuyến thuộc mẹ "
        "(gồm cả phần thiếu giá vốn) — thừa ra là có chuyến của pháp nhân khác lọt vào."
    )


def test_chua_gan_phap_nhan_nay_QUY_VE_VIETOURIST_va_van_dem_duoc():
    """══ TC-71 · 19/9/2026 — LUẬT BỊ ĐẢO, ghi cả hai bên ══════════════════════════════════════

    BÊN CŨ (TC-47, 16/9 — tên phép thử cũ: `test_chuyen_chua_gan_phap_nhan_khong_gop_va_cung_
    khong_bien_mat`): chuyến chưa gán pháp nhân KHÔNG cộng vào Vietourist, chỉ ra một dòng riêng.
    Lý do — dẫn từ `services/pham_vi_phap_nhan` — vẫn đúng và vẫn đáng nhớ: đoán sai pháp nhân thì
    mọi con số tiền là của một công ty khác, mà nhìn thì không khác gì số đúng.

    BÊN MỚI (18/9): anh Tuấn — "7,26 tỷ em tự gắn pháp nhân cố định cho vietourist luôn". Đo trên
    sổ thật hôm ấy: cả 38 chuyến chưa gán đều là DỊCH VỤ LẺ (mã DVL-*, visa và dịch vụ khác), đã
    đóng sổ xong; và anh Tuấn đã chốt từ trước "gán hết cho Vietourist Holdings". Nên đây không
    phải máy đoán pháp nhân — đây là chép lại một quyết định đã có của người có thẩm quyền.

    HAI ĐIỀU BÊN MỚI VẪN PHẢI GIỮ, và phép thử này canh cả hai:
      1. VẪN ĐẾM ĐƯỢC. Một quy tắc mặc định mà không đếm được là quy tắc không ai kiểm tra lại
         được. `chua_gan_phap_nhan` giữ nguyên tên, đổi nghĩa thành "đang vào đây bằng mặc định".
      2. KHÔNG GHI VÀO CƠ SỞ DỮ LIỆU. Cột `company_id` của chuyến D phải vẫn RỖNG sau khi tính —
         nếu nó bị ghi thành id của mẹ thì đó là em nhập số liệu hộ, phạm ranh giới 09/9, và
         Hành chính mất luôn khả năng gắn đè.
    """
    db, me, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["chua_gan_phap_nhan"] == 1 and r["dt_chua_gan_phap_nhan"] == 77.0, (
        "Phần vào bằng quy tắc mặc định phải đếm được, kèm số tiền của nó."
    )
    assert r["doanh_thu"] == 217.0, "…và nay ĐÃ cộng vào Vietourist (100 + 77 + 40)."

    d = db.query(Tour).filter_by(code="D").one()
    assert d.company_id is None, (
        "Quy tắc mặc định chỉ GOM LÚC TÍNH, không được ghi vào cột. Ghi vào cột là nhập số liệu "
        "hộ (phạm ranh giới 09/9) và Hành chính mất đường gắn đè."
    )


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
    # LUẬT KHÔNG ĐỔI: chuyến G đóng số 30/8, Kế toán duyệt 12/9 → vẫn là doanh thu THÁNG 8.
    # Con số kỳ vọng đổi vì TC-71 kéo thêm D (77) và F (40) vào tháng 8: 100 + 200 + 77 + 40.
    assert t8["doanh_thu"] == 417.0, (
        "Doanh thu tháng 8 không được phụ thuộc vào tốc độ duyệt của Kế toán."
    )
    # Và canh thẳng vào chỗ dễ hỏng nhất: G phải nằm ở nửa ĐÃ ĐÓNG SỔ, không rơi sang nửa kia.
    assert t8["dt_da_dong_so"] == 427.0, "G (200) phải vào phần đã đóng sổ của tháng 8."
    assert t9["doanh_thu"] == 30.0 and t9["lai_tour"] == 20.0, "Tháng 9 chỉ có chuyến E."


def test_chuyen_chua_dong_so_NAY_DUOC_TINH_va_tach_rieng_duoc():
    """══ TC-71 · 19/9/2026 — LUẬT BỊ ĐẢO, ghi cả hai bên ══════════════════════════════════════

    BÊN CŨ (TC-47, 16/9 — tên cũ `test_chuyen_chua_dong_so_chua_tinh`): chuyến F đã kết thúc hành
    trình nhưng Điều hành chưa bấm đóng số thì CHƯA có số để tính. Lý do vẫn đúng: đóng số là lúc
    người điều hành chốt sổ quyết toán, trước đó con số còn nhúc nhích, và chỉ con số đã đóng mới
    khớp sổ kế toán.

    BÊN MỚI (18/9): anh Tuấn chọn "gộp thành một số". Đo trên sổ thật hôm ấy: 670 chuyến đã chạy
    xong, doanh thu thật 24,38 tỷ nằm trong máy mà không hiện ở đâu trên màn hình chủ tịch, chỉ vì
    chưa ai bấm đóng sổ. Tiền đã về mà lãnh đạo không thấy là kiểu mù tệ hơn con số nhúc nhích.

    ĐỔI LẠI PHẢI TRẢ ĐƯỢC HAI NỬA. Con số gộp không còn khớp sổ kế toán, nên `dt_da_dong_so` và
    `dt_chua_dong_so` là thứ giữ cho nó khỏi thành lời nói dối: ngày kiểm toán hỏi "85 hay 116"
    thì chỉ ra được chỗ chênh nằm ở đâu, chuyến nào. Thiếu hai khoá ấy thì luật mới KHÔNG được
    phép tồn tại.
    """
    db, _, _ = _so_gia()
    r = KQ.thang(db, "2026-08")
    assert r["du_so"] == 3, "A (đã đóng sổ), D (pháp nhân rỗng) và F (chưa đóng sổ) đều đủ số."
    assert r["chuyen_chua_dong_so"] == 1 and r["dt_chua_dong_so"] == 40.0, (
        "Phần chưa đóng sổ phải TÁCH RA ĐƯỢC. Gộp mà không tách được là con số không đối chiếu "
        "ngược về sổ kế toán được nữa."
    )
    assert r["chuyen_da_dong_so"] == 3 and r["dt_da_dong_so"] == 227.0, (
        "Phần đã đóng sổ (A 100 + B 50 + D 77) là con số KHỚP SỔ KẾ TOÁN, phải giữ nguyên vẹn."
    )


def test_chuyen_CHUA_KHOI_HANH_thi_van_khong_duoc_tinh():
    """Luật A chỉ kéo chuyến ĐÃ CHẠY. Chuyến của ngày mai mà đã cộng doanh thu là ghi nhận trước
    doanh thu — sai ở mọi chuẩn kế toán, và sai cả về lẽ thường.

    Đây là hàng rào của chính luật mới: nới "chưa đóng sổ cũng tính" mà không có hàng rào này thì
    cả lịch khởi hành năm 2027 nhảy vào doanh thu hôm nay.
    """
    db, me, u = _so_gia()
    mai = dt.date.today() + dt.timedelta(days=1)
    db.add(Tour(code="H", name="H", tour_type="package",
                start_date=mai, end_date=mai + dt.timedelta(days=2),
                operator_id=u.id, status="da_duyet", actual_revenue=5000.0, actual_cost=1.0,
                closed_at=None, company_id=me.id))
    db.commit()
    r = KQ.thang(db, f"{mai.year:04d}-{mai.month:02d}")
    assert (r["dt_chua_dong_so"] or 0) == 0.0, (
        "Chuyến chưa khởi hành không được cộng một đồng nào — đó là ghi nhận trước doanh thu."
    )


def test_ke_toan_tra_lai_thi_chuyen_CHUYEN_SANG_NUA_CHUA_DONG_SO():
    """══ TC-71 · 19/9/2026 — LUẬT ĐỔI MỘT NỬA, ghi cả hai bên ═════════════════════════════════

    BÊN CŨ (TC-47, 16/9): Kế toán trả lại một chuyến thì `settlement.py` đặt `closed_at = None`,
    chuyến RỜI KHỎI tháng đã tính và tổng tháng ấy giảm xuống.

    BÊN MỚI (18/9): chuyến ấy không rời khỏi tháng nữa — nó CHUYỂN từ nửa "đã đóng sổ" sang nửa
    "chưa đóng sổ" của cùng tháng ấy, vì luật A nay tính cả phần chưa đóng sổ.

    Điều này thật ra LÀNH HƠN bên cũ, và đó là cái được không định trước của luật A: trước đây một
    chuyến bị trả lại làm tổng tháng tụt xuống mà trên màn hình không có gì giải thích. Nay tổng
    gộp đứng yên, chỉ có tỷ lệ giữa hai nửa đổi — và hai nửa ấy hiện ra chữ.

    `da_khoa` VẪN đúng và nay chặt hơn: còn chuyến chưa đóng sổ thì tháng CHƯA đứng yên, dù mọi
    chuyến đã đóng sổ đều đã khoá.
    """
    db, me, u = _so_gia()
    assert KQ.thang(db, "2026-08")["da_khoa"] is False

    # LỌC THEO `(me.id, None)` CHỨ KHÔNG CHỈ `me.id` — và đây chính là một hệ quả của luật B mà
    # bản nháp đầu của phép thử này bỏ sót: chuyến D pháp nhân rỗng nay THUỘC Vietourist, nên
    # chừng nào nó chưa khoá thì tháng vẫn chưa đứng yên. Quy một chuyến về Vietourist nghĩa là
    # nhận nó về đủ mọi mặt, không phải chỉ nhận phần doanh thu.
    for t in db.query(Tour).filter(Tour.company_id.in_([me.id]) | Tour.company_id.is_(None)).all():
        if t.closed_at and t.closed_at.month == 8:
            t.status = "khoa"
    db.commit()
    # Chuyến F (mẹ, chưa đóng sổ) vẫn nằm trong tháng 8, nên tháng CHƯA đứng yên.
    assert KQ.thang(db, "2026-08")["da_khoa"] is False, (
        "Còn chuyến chưa đóng sổ thì tháng chưa đứng yên — `da_khoa` phải nói ra điều đó."
    )
    f = db.query(Tour).filter_by(code="F").one()
    f.closed_at, f.status = dt.datetime(2026, 8, 20), "khoa"
    db.commit()
    assert KQ.thang(db, "2026-08")["da_khoa"] is True

    truoc = KQ.thang(db, "2026-08")
    t = db.query(Tour).filter_by(code="A").one()
    t.status, t.closed_at = "ket_thuc", None
    db.commit()
    sau = KQ.thang(db, "2026-08")
    assert sau["doanh_thu"] == truoc["doanh_thu"], (
        "Tổng GỘP không đổi khi Kế toán trả lại — chuyến chỉ đổi nửa, không rời tháng."
    )
    assert sau["dt_da_dong_so"] == truoc["dt_da_dong_so"] - 100.0, "A rời khỏi nửa đã đóng sổ."
    assert sau["dt_chua_dong_so"] == truoc["dt_chua_dong_so"] + 100.0, "…và sang nửa chưa đóng sổ."
    assert sau["da_khoa"] is False, "Trả lại một chuyến thì tháng thôi đứng yên."


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
    # TC-71 · LUẬT NÀY KHÔNG BỊ ĐẢO — chỉ con số kỳ vọng đổi vì tập chuyến rộng ra (thêm D và F).
    # Điều phải canh vẫn y nguyên: hai con số đến từ CÙNG MỘT TẬP. Nên phép thử nay canh bằng
    # CHÍNH ĐỊNH NGHĨA chứ không bằng một tỷ lệ gõ cứng — gõ cứng thì lần sau đổi fixture là lại
    # phải sửa con số, và người sửa không còn biết mình đang canh điều gì.
    assert r["doanh_thu"] == 217.0 and r["lai_tour"] == 136.0
    du = [t for t in db.query(Tour).all()
          if KQ._lai(t) is not None and t.company_id in (None, 1)
          and (t.closed_at or t.start_date).month == 8]
    assert r["doanh_thu"] == sum(float(t.actual_revenue) for t in du), (
        "Tử số và mẫu số phải đến từ cùng một tập chuyến, nếu không biên đọc ra là phép chia giữa "
        "tử của tập này và mẫu của tập kia."
    )
    assert r["lai_tour"] == sum(KQ._lai(t) for t in du)


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
