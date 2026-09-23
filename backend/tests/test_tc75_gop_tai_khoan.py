"""TC-75 · GỘP TÀI KHOẢN TRÙNG — anh Tuấn 19/9/2026: "và xoá trùng".

Đo trên máy thật cùng ngày: 220 tài khoản, 6 người có từ hai tài khoản trở lên, 24 dòng. Bốn cặp
đang mở cả hai và doanh số bị xẻ đôi — 129 booking, khoảng 269 triệu chạy sang tài khoản không có
mã nhân viên.

Anh Tuấn nói "xoá"; vòng này làm "chuyển rồi khoá". Lý do ghi đầy đủ ở đầu
`services/gop_tai_khoan.py`, tóm lại: cả 24 tài khoản ấy đều đang giữ booking, và nhật ký nghiệp vụ
ghi người làm bằng tên đăng nhập dạng chữ — xoá thì nhật ký không gãy, nó chỉ trỏ tới một cái tên
không còn tra ra ai. Im lặng mà sai là kiểu hỏng khó tìm nhất.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
 1. BỎ SÓT MỘT CỘT. Hơn hai chục cột khoá ngoại trỏ vào `users.id`, rải ở 11 tệp mô hình. Chép tay
    là cầm chắc ngày ai đó thêm cột mới và phép gộp lặng lẽ bỏ sót — bỏ sót nghĩa là tài khoản bị
    khoá trong khi vẫn còn dữ liệu trỏ vào, tức dữ liệu mồ côi mà không ai báo.

 2. KHOÁ TRƯỚC KHI CHUYỂN. Thứ tự ngược là doanh số nằm im trong một tài khoản chết mà giờ không ai
    mở ra được — tệ hơn lúc chưa làm gì.

 3. GHI THẬT KHI CHỈ ĐỊNH XEM. Gộp là việc MỘT CHIỀU, không có nút tách ngược. Mặc định phải là
    KHÔNG ghi.

 4. NHẬT KÝ NÓI DỐI. Chụp trạng thái "trước" sau khi đã sửa thì cột before ghi lại đúng trạng thái
    sau. Nhật ký sai tệ hơn không có nhật ký, vì người đọc tin nó.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import AuditLog, Booking, Tour, User
from app.services import gop_tai_khoan as GTK


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_kd", ma="", mo=True):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x", staff_code=ma, active=mo)
    db.add(u); db.commit()
    return u


def _tour(db, ma, op):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=dt.date(2026, 9, 1),
             end_date=dt.date(2026, 9, 3), operator_id=op.id, status="ket_thuc")
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien=1_000_000):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K", customer_phone="09", source="t", pax=1, amount=tien,
                sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


def _canh(db):
    """Hai tài khoản của cùng một người: `giu` có mã nhân viên, `bo` không."""
    db_ = db
    giu = _u(db_, "vananh", ma="269")
    bo = _u(db_, "vananh2")
    bo.full_name = giu.full_name = "Nguyễn Ngọc Vân Anh"
    db_.commit()
    return giu, bo


# ── 1. Không bỏ sót cột ────────────────────────────────────────────────────────────────────────

def test_tim_du_moi_cot_tro_toi_users():
    """Danh sách cột phải ĐỌC từ siêu dữ liệu, không gõ tay."""
    tim = set(GTK.cot_tro_toi_users())
    that = set()
    for bang in Base.metadata.sorted_tables:
        for cot in bang.columns:
            for fk in cot.foreign_keys:
                if fk.column.table.name == "users" and fk.column.name == "id":
                    that.add((bang.name, cot.name))
    that -= set(GTK.KHONG_CHUYEN)
    assert tim == that, f"Lệch: thiếu {that - tim}, thừa {tim - that}"
    assert len(tim) >= 20, ("Kho này có hơn hai chục cột trỏ vào users. Tìm ra quá ít nghĩa là phép "
                            f"dò hỏng chứ không phải kho ít cột: {sorted(tim)}")


def test_gop_chuyen_ca_nhung_cot_khong_phai_sales_id():
    """Không chỉ `bookings.sales_id` — `created_by` và mọi cột khác cũng phải theo."""
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo)                       # tours.operator_id trỏ vào `bo`
    b = _bk(db, "BK1", t, bo)                    # sales_id VÀ created_by đều trỏ vào `bo`
    GTK.gop(db, giu, giu.id, bo.id, "Trùng tài khoản", xac_nhan=True); db.commit()
    db.refresh(b); db.refresh(t)
    assert b.sales_id == giu.id
    assert b.created_by == giu.id, "created_by bị bỏ sót – chỉ chuyển sales_id là chuyển nửa vời"
    assert t.operator_id == giu.id, "tours.operator_id bị bỏ sót"


def test_sau_khi_gop_khong_con_dong_nao_tro_vao_tai_khoan_cu():
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); _bk(db, "BK1", t, bo); _bk(db, "BK2", t, bo)
    GTK.gop(db, giu, giu.id, bo.id, "Trùng", xac_nhan=True); db.commit()
    for bang, cot in GTK.cot_tro_toi_users():
        tb = Base.metadata.tables[bang]
        n = db.execute(select(func.count()).select_from(tb).where(tb.c[cot] == bo.id)).scalar_one()
        assert n == 0, f"Còn {n} dòng ở {bang}.{cot} trỏ vào tài khoản đã khoá – dữ liệu mồ côi"


# ── 2. Chuyển trước, khoá sau ──────────────────────────────────────────────────────────────────

def test_khoa_tai_khoan_thua_nhung_khong_xoa():
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); _bk(db, "BK1", t, bo)
    GTK.gop(db, giu, giu.id, bo.id, "Trùng", xac_nhan=True); db.commit()
    con = db.get(User, bo.id)
    assert con is not None, "Tài khoản phải còn trong bảng – nhật ký cần tra lại được"
    assert con.active is False
    assert "đã gộp vào" in con.full_name, "Tên phải nói rõ nó đã bị gộp, để không ai dùng nhầm"


def test_khong_gop_vao_mot_tai_khoan_dang_khoa():
    """Gộp vào tài khoản chết là dồn dữ liệu vào chỗ không ai mở được."""
    db = _db()
    khoa = _u(db, "cu", ma="1", mo=False); mo = _u(db, "moi")
    khoa.full_name = mo.full_name = "Một Người"; db.commit()
    with pytest.raises(ValueError) as e:
        GTK.gop(db, mo, khoa.id, mo.id, "thử", xac_nhan=True)
    assert "đang bị khoá" in str(e.value)


# ── 3. Một chiều thì mặc định là không làm gì ──────────────────────────────────────────────────

def test_mac_dinh_la_xem_truoc_khong_ghi():
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); b = _bk(db, "BK1", t, bo)
    kq = GTK.gop(db, giu, giu.id, bo.id, "Trùng")     # KHÔNG truyền xac_nhan
    assert kq["da_ghi"] is False
    assert kq["tong_dong_se_chuyen"] >= 3
    db.refresh(b); db.refresh(bo)
    assert b.sales_id == bo.id, "Xem trước mà đã ghi – mặc định của một việc một chiều phải là không làm gì"
    assert bo.active is True


def test_xem_truoc_dem_dung_so_dong():
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); _bk(db, "BK1", t, bo); _bk(db, "BK2", t, bo)
    xt = GTK.xem_truoc(db, giu.id, bo.id)
    theo = {(c["bang"], c["cot"]): c["so_dong"] for c in xt["chi_tiet"]}
    assert theo[("bookings", "sales_id")] == 2
    assert theo[("bookings", "created_by")] == 2
    assert theo[("tours", "operator_id")] == 1
    assert xt["tong_dong_se_chuyen"] == sum(theo.values())


def test_phai_co_ly_do_va_hai_tai_khoan_phai_khac_nhau():
    db = _db(); giu, bo = _canh(db)
    with pytest.raises(ValueError):
        GTK.gop(db, giu, giu.id, bo.id, "   ", xac_nhan=True)
    with pytest.raises(ValueError) as e:
        GTK.gop(db, giu, giu.id, giu.id, "Trùng", xac_nhan=True)
    assert "khác nhau" in str(e.value)


# ── 4. Nhật ký phải nói thật ───────────────────────────────────────────────────────────────────

def test_nhat_ky_ghi_trang_thai_TRUOC_khi_sua():
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); _bk(db, "BK1", t, bo)
    GTK.gop(db, giu, giu.id, bo.id, "Hai tài khoản một người", xac_nhan=True); db.commit()
    dong = db.execute(select(AuditLog).where(AuditLog.action == "gop_tai_khoan_trung")).scalars().first()
    assert dong is not None, "Gộp tài khoản phải để lại một dòng nhật ký"
    truoc = str(dong.before)
    assert "'dang_mo': True" in truoc, (
        "Nhật ký đang ghi trạng thái SAU vào cột before. Chụp trạng thái trước khi sửa – "
        "một nhật ký sai tệ hơn không có nhật ký, vì người đọc tin nó.")
    assert "đã gộp vào" not in truoc
    assert "Hai tài khoản một người" in str(dong.after)


# ── Bảng cặp trùng và gợi ý ────────────────────────────────────────────────────────────────────

def test_goi_y_giu_tai_khoan_co_ma_nhan_vien():
    """Bảng lương T08 làm chuẩn – anh Tuấn chốt 19/9. Tài khoản có mã là tài khoản khớp hồ sơ."""
    db = _db(); giu, bo = _canh(db)
    ds = GTK.cap_trung(db)
    assert len(ds) == 1
    assert ds[0]["goi_y_giu"] == giu.id
    assert "mã nhân viên" in ds[0]["vi_sao"]


def test_khong_goi_y_khi_ca_hai_deu_co_ma():
    """Hai mã khác nhau nghĩa là có thể hai người thật – máy không đoán."""
    db = _db()
    a = _u(db, "a", ma="10"); b = _u(db, "b", ma="11")
    a.full_name = b.full_name = "Trùng Tên"; db.commit()
    ds = GTK.cap_trung(db)
    assert ds[0]["goi_y_giu"] is None
    assert "người quyết" in ds[0]["vi_sao"]


def test_bo_dau_va_hoa_thuong_van_nhan_ra_trung():
    db = _db()
    a = _u(db, "a", ma="10"); b = _u(db, "b")
    a.full_name = "Quách Thị Thuỳ Trang"; b.full_name = "QUACH THI THUY TRANG"; db.commit()
    assert len(GTK.cap_trung(db)) == 1, "Khác dấu và khác hoa thường vẫn là một người"


def test_nguoi_khong_trung_thi_khong_liet_ke():
    db = _db(); _u(db, "a", ma="1"); _u(db, "b", ma="2")
    assert GTK.cap_trung(db) == []


def test_dem_so_dong_cua_tung_tai_khoan():
    """Con số này là thứ cho biết cái thừa có thật sự trống hay đang giữ dữ liệu."""
    db = _db(); giu, bo = _canh(db)
    t = _tour(db, "X", bo); _bk(db, "BK1", t, bo)
    tk = {x["tai_khoan"]: x["so_dong"] for x in GTK.cap_trung(db)[0]["tai_khoan"]}
    assert tk["vananh2"] >= 3 and tk["vananh"] == 0
