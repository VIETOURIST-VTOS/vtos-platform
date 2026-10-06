"""TC-74 · NGƯỜI BÁN HÀNG — đối tác ngoài công ty, và quyền bán của người ngoài khối.

Anh Tuấn 19/9/2026, hai câu:
    "em tạo tên đối tác vào luôn"  — J TRAVEL, JTV, VTOURIST là "đối tác hợp tác bán tour ghép lẻ"
    "ngoài khối kinh doanh em mở thêm cho nhân viên sau này nhập tay vào, ví dụ hdv, dh..."

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
 1. ĐỐI TÁC TRỞ THÀNH MỘT TÀI KHOẢN ĐĂNG NHẬP. Trên máy thật 19/9 đã có sẵn một dòng `users` tên
    `ĐỐI_TÁC` mang vai `nv_kd` — ai đó phải lách vì hệ thống không có chỗ cho đối tác. Bảng
    `doi_tac_ban_hang` cố ý KHÔNG có cột mật khẩu và vai trò; phép thử ghim điều đó, vì thêm hai
    cột ấy là mở cửa hệ thống cho người ngoài công ty.

 2. DOANH THU ĐỐI TÁC CHUI VÀO CHỈ TIÊU NGƯỜI TIẾP NHẬN. `bookings.sales_id` NOT NULL nên booking
    của đối tác vẫn phải có một nhân viên đứng tên. Xét vai trước khi xét đối tác là tiền của J
    Travel rơi vào bảng xếp hạng của người tiếp nhận hồ sơ.

 3. "ĐỐI TÁC" BỊ GỘP VỚI "CHƯA BIẾT AI BÁN". Một bên đã biết, một bên chưa. Gộp thì câu hỏi "công
    ty bán qua đối tác bao nhiêu" không còn trả lời được — mà riêng bốn cái tên ấy đã gánh ~3,5 tỷ.

 4. Ô TICK KÉO NGƯỜI NGOÀI KHỐI VÀO BẢNG XẾP HẠNG. Quyền BÁN khác nghĩa vụ ĐẠT CHỈ TIÊU. Bật cho
    một hướng dẫn viên mà họ xuất hiện trong bảng chỉ tiêu kinh doanh là sai cả hai phía.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour, User
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.services import doanh_thu_kd as DT
from app.services import nguoi_ban_hang as NB


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_kd"):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _tour(db, ma, ket_thuc, loai="le_noi_dia"):
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=ket_thuc - dt.timedelta(days=2),
             end_date=ket_thuc, operator_id=1, status="ket_thuc", actual_revenue=0.0)
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien, doi_tac=None, tinh=True):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K " + ma, customer_phone="0900000000", source="thu",
                pax=2, amount=tien, counts_for_target=tinh, sla_minutes=0, sla_ok=True,
                doi_tac_id=doi_tac.id if doi_tac else None)
    db.add(b); db.commit()
    return b


# ── 1. Đối tác không phải tài khoản ────────────────────────────────────────────────────────────

def test_doi_tac_khong_co_mat_khau_va_vai_tro():
    """Hàng rào chắc nhất là KHÔNG CÓ GÌ ĐỂ CẤP — không cột mật khẩu, không cột vai trò."""
    cot = set(DoiTacBanHang.__table__.columns.keys())
    for cam in ("password_hash", "password", "role", "vai", "username", "active"):
        assert cam not in cot, (
            f"Cột {cam!r} biến đối tác thành một tài khoản đăng nhập. Đối tác là bên NGOÀI công ty; "
            "cho họ đăng nhập là mở cửa hệ thống chỉ để ghi nhận họ bán được mấy chuyến.")


def test_doi_tac_khong_xoa_chi_dong():
    db = _db(); hc = _u(db, "hcns", "hcns")
    d = NB.tao_doi_tac(db, hc, "jtv", "J Travel", "ghep_le", hieu_luc_tu=dt.date(2026, 1, 1))
    db.commit()
    assert d.ma == "JTV", "Mã phải chuẩn hoá về chữ hoa"
    NB.dong_doi_tac(db, hc, d.id, dt.date(2026, 6, 30), "Hết hợp đồng"); db.commit()
    assert db.get(DoiTacBanHang, d.id) is not None
    assert d.dang_hieu_luc(dt.date(2026, 6, 30)) is True
    assert d.dang_hieu_luc(dt.date(2026, 7, 1)) is False


def test_dong_doi_tac_phai_co_ly_do():
    db = _db(); hc = _u(db, "hcns", "hcns")
    d = NB.tao_doi_tac(db, hc, "JTV", "J Travel"); db.commit()
    with pytest.raises(ValueError):
        NB.dong_doi_tac(db, hc, d.id, dt.date(2026, 6, 30), "  ")


def test_ma_doi_tac_trung_bi_chan():
    db = _db(); hc = _u(db, "hcns", "hcns")
    NB.tao_doi_tac(db, hc, "JTV", "J Travel"); db.commit()
    with pytest.raises(ValueError) as e:
        NB.tao_doi_tac(db, hc, "jtv", "J Travel Viet Nam")
    assert "đã có" in str(e.value)


# ── 2 & 3. Bốn ngăn người bán ──────────────────────────────────────────────────────────────────

def test_doanh_thu_doi_tac_khong_vao_chi_tieu_nguoi_tiep_nhan():
    """Chỗ dễ sai nhất cả vòng: booking của đối tác VẪN có một nhân viên đứng tên ở sales_id."""
    db = _db(); hc = _u(db, "hcns", "hcns"); nv = _u(db, "chi", "nv_kd")
    d = NB.tao_doi_tac(db, hc, "JTV", "J Travel", hieu_luc_tu=dt.date(2026, 1, 1)); db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "B1", t, nv, 10_000_000)                 # nhân viên tự bán
    _bk(db, "B2", t, nv, 30_000_000, doi_tac=d)      # đối tác bán, chị Chi tiếp nhận

    kq = DT.thang(db, "2026-09")
    assert kq["tong_tinh_chi_tieu"] == 10_000_000, (
        "30 triệu của J Travel đang chui vào chỉ tiêu của người tiếp nhận hồ sơ.")
    assert kq["theo_ngan"]["doi_tac"]["tien"] == 30_000_000
    assert kq["theo_doi_tac"][0]["ten"] == "J Travel"


def test_doi_tac_khac_hoan_toan_voi_chua_biet_ai_ban():
    db = _db(); hc = _u(db, "hcns", "hcns"); nv = _u(db, "chi", "nv_kd"); kho = _u(db, "khocu", "nv_kd")
    d = NB.tao_doi_tac(db, hc, "JTV", "J Travel", hieu_luc_tu=dt.date(2026, 1, 1)); db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "B1", t, nv, 30_000_000, doi_tac=d)
    _bk(db, "KC-1", t, kho, 19_000_000, tinh=False)
    n = DT.thang(db, "2026-09")["theo_ngan"]
    assert n["doi_tac"]["tien"] == 30_000_000
    assert n["chua_ro"]["tien"] == 19_000_000, (
        "Gộp hai ngăn này thì câu hỏi 'công ty bán qua đối tác bao nhiêu' mất câu trả lời.")


def test_bon_ngan_roi_nhau_va_cong_du():
    """Điều kiện tồn tại của cả cấu trúc: bốn ngăn cộng lại bằng toàn bộ doanh thu của kỳ."""
    db = _db(); hc = _u(db, "hcns", "hcns")
    nv = _u(db, "chi", "nv_kd"); hdv = _u(db, "hdv1", "hdv"); kho = _u(db, "khocu", "nv_kd")
    NB.dat_quyen_ban(db, hc, hdv.id, True, "HDV bán thêm chỗ lẻ"); db.commit()
    d = NB.tao_doi_tac(db, hc, "JTV", "J Travel", hieu_luc_tu=dt.date(2026, 1, 1)); db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "B1", t, nv, 10_000_000)
    _bk(db, "B2", t, hdv, 4_000_000)
    _bk(db, "B3", t, nv, 30_000_000, doi_tac=d)
    _bk(db, "KC-1", t, kho, 19_000_000, tinh=False)

    kq = DT.thang(db, "2026-09"); n = kq["theo_ngan"]
    assert n["khoi_kd"]["tien"] == 10_000_000
    assert n["ngoai_khoi"]["tien"] == 4_000_000
    assert n["doi_tac"]["tien"] == 30_000_000
    assert n["chua_ro"]["tien"] == 19_000_000
    assert sum(v["tien"] for v in n.values()) == kq["tong_moi_ngan"] == 63_000_000
    assert kq["tong_tinh_chi_tieu"] == 10_000_000, "CHỈ ngăn đầu vào chỉ tiêu"


# ── 4. Quyền bán là dữ liệu, không phải tuple trong mã ─────────────────────────────────────────

def test_hdv_chua_bat_thi_nam_o_ngan_chua_ro():
    db = _db(); hdv = _u(db, "hdv1", "hdv")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "B1", t, hdv, 4_000_000)
    assert DT.thang(db, "2026-09")["theo_ngan"]["chua_ro"]["tien"] == 4_000_000


def test_bat_o_tick_khong_keo_nguoi_ngoai_khoi_vao_chi_tieu():
    """Quyền BÁN khác nghĩa vụ ĐẠT CHỈ TIÊU — bật ô tick không đưa ai vào bảng xếp hạng."""
    db = _db(); hc = _u(db, "hcns", "hcns"); hdv = _u(db, "hdv1", "hdv")
    NB.dat_quyen_ban(db, hc, hdv.id, True, "HDV bán thêm chỗ lẻ"); db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "B1", t, hdv, 4_000_000)
    kq = DT.thang(db, "2026-09")
    assert kq["theo_ngan"]["ngoai_khoi"]["tien"] == 4_000_000
    assert kq["tong_tinh_chi_tieu"] == 0
    assert kq["theo_nguoi"] == [], "Bảng xếp hạng kinh doanh chỉ gồm người khối Kinh doanh"


def test_khong_bat_o_tick_cho_nguoi_khoi_kinh_doanh():
    db = _db(); hc = _u(db, "hcns", "hcns"); nv = _u(db, "chi", "nv_kd")
    with pytest.raises(ValueError) as e:
        NB.dat_quyen_ban(db, hc, nv.id, True, "cho chắc")
    assert "đương nhiên" in str(e.value)


def test_doi_quyen_ban_phai_co_ly_do_va_phai_doi_that():
    db = _db(); hc = _u(db, "hcns", "hcns"); hdv = _u(db, "hdv1", "hdv")
    with pytest.raises(ValueError):
        NB.dat_quyen_ban(db, hc, hdv.id, True, "")
    NB.dat_quyen_ban(db, hc, hdv.id, True, "HDV bán thêm"); db.commit()
    with pytest.raises(ValueError) as e:
        NB.dat_quyen_ban(db, hc, hdv.id, True, "bật lại")
    assert "không có gì thay đổi" in str(e.value).lower()


def test_khong_con_danh_sach_vai_viet_chet_trong_doanh_thu():
    """Một luật, một chỗ. Bản chép thứ hai là cầm chắc ngày hai nơi trả lời khác nhau."""
    import inspect
    ma = inspect.getsource(DT)
    assert "VAI_KINH_DOANH" not in ma
    assert "NB.ngan_cua_nguoi" in ma, "Phải hỏi services/nguoi_ban_hang.py, không tự xét vai"


def test_ba_nhom_nhan_vien_roi_nhau():
    db = _db(); hc = _u(db, "hcns", "hcns")
    nv = _u(db, "chi", "nv_kd"); a = _u(db, "hdv1", "hdv"); b = _u(db, "dh1", "nv_dh")
    NB.dat_quyen_ban(db, hc, a.id, True, "bán thêm"); db.commit()
    r = NB.ai_duoc_ban(db)
    ten = lambda k: {x["tai_khoan"] for x in r[k]}
    assert ten("khoi_kinh_doanh") == {"chi"}
    assert ten("ngoai_khoi_duoc_ban") == {"hdv1"}
    assert "dh1" in ten("ngoai_khoi_chua_bat") and "hcns" in ten("ngoai_khoi_chua_bat")
    assert not (ten("khoi_kinh_doanh") & ten("ngoai_khoi_duoc_ban") & ten("ngoai_khoi_chua_bat"))


def test_booking_cua_doi_tac_van_co_nhan_vien_dung_ten():
    """Cột `sales_id` NOT NULL là cố ý: chuyến nào cũng phải có người trong công ty chịu trách nhiệm."""
    assert Booking.__table__.columns["sales_id"].nullable is False
    assert Booking.__table__.columns["doi_tac_id"].nullable is True
