"""TC-83 · SỬA VÀ XOÁ HỒ SƠ TÀI KHOẢN — anh Tuấn chốt 24/9/2026.

    "NS, CT và TGĐ mới được sửa và xoá nhân sự"

BA DANH SÁCH VAI, và chỗ chúng khác nhau là chỗ đáng canh:

    gộp  →  chutich, tgd, hcns, cntt      (HC-NS được thêm vào ngày 24/9)
    sửa  →  hcns, chutich, tgd            (KHÔNG có cntt)
    xoá  →  hcns, chutich, tgd            (KHÔNG có cntt)

CNTT GỘP ĐƯỢC MÀ KHÔNG SỬA ĐƯỢC, và đó là quyết định có chủ chứ không phải sót. Gộp là DỌN DỮ
LIỆU — chuyển các dòng đang trỏ vào tài khoản này sang tài khoản kia, không đổi một chữ nào trong
hồ sơ ai. Sửa họ tên hay mã nhân viên là đổi HỒ SƠ NHÂN SỰ, và hồ sơ nhân sự là của HC-NS.

BẢY CHỖ PHÉP THỬ NÀY CANH:

 1. XOÁ MỘT TÀI KHOẢN CÒN DỮ LIỆU. Đo 19/9/2026: cả 24 tài khoản trùng đều đang giữ booking, kể
    cả 13 cái đã khoá. Xoá là 129 booking mất chủ, báo cáo doanh số hụt đúng phần ấy, và không ai
    biết vì sao. Chặn này KHÔNG có ngoại lệ cho vai nào, kể cả Chủ tịch.

 2. XOÁ RỒI MẤT DẤU NGƯỜI. Nhật ký nghiệp vụ ghi người làm bằng TÊN ĐĂNG NHẬP dạng chữ, nên xoá
    xong nhật ký vẫn chạy nhưng mỗi dòng trỏ tới một cái tên không tra ra ai. Bia mộ phải được ghi
    TRƯỚC khi xoá — ghi sau thì mất luôn dữ liệu cần ghi.

 3. DANH SÁCH CỘT CHÉP TAY. Bộ đếm "còn bao nhiêu dòng" phải đọc từ siêu dữ liệu, cùng bộ với
    phép gộp. Chép tay là cầm chắc ngày ai đó thêm cột thứ 24 và phép xoá lặng lẽ bỏ sót nó.

 4. Ô SỬA KHÔNG CÓ CỘT THẬT. Bản đầu của vòng này khai `email` và `phone`; bảng `users` không có
    hai cột ấy. Một ô người dùng gõ vào rồi mất chữ mà không báo lỗi là lỗi tệ nhất trong ba loại.

 5. MÃ NHÂN VIÊN ĐẶT TRÙNG. Mã nhân viên là thứ nhận ra người; hai tài khoản cùng mã là đúng cái
    mớ mà màn hình này sinh ra để dọn.

 6. NHẬT KÝ GHI TRẠNG THÁI SAU. Chụp `before` sau khi đã gán thì nhật ký nói dối — bài học TC-78.

 7. NỚI QUYỀN VÌ MỘT TIỀN TỐ MỚI. Ba cửa mới đặt dưới tiền tố sẵn có, nên bảng phạm vi vai trò
    KHÔNG được đổi một con số nào.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import AuditLog, Booking, Tour, User
from app.models.tai_khoan_da_xoa import TaiKhoanDaXoa
from app.services import gop_tai_khoan as GTK
from app.services import sua_xoa_tai_khoan as SX

GOC = Path(__file__).resolve().parents[1]
WEB = GOC.parents[0] / "web"


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_kd", ma="", mo=True):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x",
             staff_code=ma or None, active=mo)
    db.add(u); db.commit()
    return u


def _bk(db, ma, sale, huy=False):
    t = db.execute(select(Tour)).scalars().first()
    if t is None:
        t = Tour(code="T1", name="T1", tour_type="le_noi_dia",
                 start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 9, 5),
                 operator_id=1, status="ket_thuc", actual_revenue=0.0)
        db.add(t); db.commit()
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=sale.id, created_by=sale.id,
                customer_name="K", customer_phone="09", source="truc_tiep", pax=1,
                amount=1_000_000, cancelled=huy, counts_for_target=True,
                sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


# ═════════════════════════ XOÁ — BA ĐIỀU KIỆN ═════════════════════════

def test_con_du_lieu_thi_KHONG_xoa_duoc_ke_ca_chu_tich():
    """129 booking mất chủ là con số đo được ngày 19/9. Chặn này không có ngoại lệ cho vai nào."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    x = _u(db, "nv.thao", mo=False)
    _bk(db, "B1", x)
    kq = SX.co_the_xoa(db, ct, x.id)
    assert not kq["xoa_duoc"]
    assert kq["tong_dong_con_lai"] >= 1
    assert any("dòng dữ liệu trỏ tới" in c for c in kq["can_tro"])
    with pytest.raises(ValueError, match="dòng dữ liệu trỏ tới"):
        SX.xoa(db, ct, x.id, "dọn", xac_nhan=True)


def test_dang_mo_thi_khong_xoa_duoc():
    """Xoá thẳng một tài khoản đang mở là cắt ngang phiên làm việc của người đang dùng."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    x = _u(db, "nv.moi", mo=True)
    kq = SX.co_the_xoa(db, ct, x.id)
    assert not kq["xoa_duoc"]
    assert any("đang MỞ" in c for c in kq["can_tro"])


def test_khong_tu_xoa_chinh_minh():
    db = _db()
    ct = _u(db, "chutich", "chutich", mo=False)
    kq = SX.co_the_xoa(db, ct, ct.id)
    assert not kq["xoa_duoc"]
    assert any("chính mình" in c for c in kq["can_tro"])


def test_gop_TRUOC_roi_xoa_SAU_la_duong_di_dung():
    """Luồng thật đầu-cuối: gộp chuyển hết dữ liệu, tài khoản bỏ về 0 dòng, lúc ấy mới xoá được."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    giu = _u(db, "van.anh", ma="269")
    bo = _u(db, "vananh2")
    _bk(db, "B1", bo); _bk(db, "B2", bo)

    assert not SX.co_the_xoa(db, ct, bo.id)["xoa_duoc"], "Còn booking thì chưa xoá được"

    GTK.gop(db, ct, giu.id, bo.id, "trùng do đợt nạp 19/9", xac_nhan=True)
    db.commit()

    kq = SX.co_the_xoa(db, ct, bo.id)
    assert kq["xoa_duoc"], f"Gộp xong phải xoá được: {kq['can_tro']}"
    assert kq["tong_dong_con_lai"] == 0

    r = SX.xoa(db, ct, bo.id, "đã gộp xong, dọn tài khoản thừa", xac_nhan=True)
    db.commit()
    assert r["da_xoa"]
    assert db.get(User, bo.id) is None


def test_thieu_ly_do_thi_bi_chan():
    db = _db()
    ct = _u(db, "chutich", "chutich")
    x = _u(db, "trong", mo=False)
    with pytest.raises(ValueError, match="phải ghi lý do"):
        SX.xoa(db, ct, x.id, "   ", xac_nhan=True)


def test_mac_dinh_la_XEM_TRUOC_khong_ghi_gi():
    """Một thao tác không hoàn lại được thì bước mặc định phải là bước không làm gì."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    x = _u(db, "trong", mo=False)
    r = SX.xoa(db, ct, x.id, "dọn")           # xac_nhan mặc định False
    assert r["da_xoa"] is False
    assert db.get(User, x.id) is not None, "Xem trước mà đã xoá là hỏng cả cơ chế"
    assert db.execute(select(TaiKhoanDaXoa)).scalars().first() is None


# ═════════════════════════ BIA MỘ ═════════════════════════

def test_bia_mo_ghi_TRUOC_khi_xoa_va_giu_du_de_tra_nguoc():
    """Ghi sau khi xoá thì mất luôn dữ liệu cần ghi."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    x = _u(db, "nv.thao", vai="nv_mkt", ma="A77", mo=False)
    SX.xoa(db, ct, x.id, "trùng, đã gộp", xac_nhan=True)
    db.commit()
    b = db.execute(select(TaiKhoanDaXoa)).scalars().first()
    assert b is not None, "Không có bia mộ thì nhật ký cũ trỏ tới một cái tên không tra ra ai"
    assert (b.tai_khoan, b.ho_ten, b.ma_nv, b.vai) == ("nv.thao", "NV.THAO", "A77", "nv_mkt")
    assert b.xoa_boi == "chutich" and b.ly_do == "trùng, đã gộp"


def test_bia_mo_ghi_lai_da_gop_vao_ai_khi_suy_duoc():
    """Chỗ để người đọc nhật ký đi tiếp: dữ liệu của người này giờ nằm ở tài khoản nào."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    giu = _u(db, "van.anh", ma="269")
    bo = _u(db, "vananh2")
    _bk(db, "B1", bo)
    GTK.gop(db, ct, giu.id, bo.id, "trùng", xac_nhan=True); db.commit()
    SX.xoa(db, ct, bo.id, "dọn sau gộp", xac_nhan=True); db.commit()
    b = db.execute(select(TaiKhoanDaXoa)).scalars().first()
    assert b.da_gop_vao == "van.anh"


def test_bia_mo_KHONG_co_cua_xoa():
    """Bảng này mà xoá được thì nó không còn là chỗ tra ngược nào cả."""
    from app.main import app
    duong = [(r.path, m) for r in app.routes for m in getattr(r, "methods", [])]
    assert not [d for d in duong if "bia-mo" in d[0] and d[1] in ("DELETE", "PUT", "POST")]
    nguon = (GOC / "app" / "services" / "sua_xoa_tai_khoan.py").read_text(encoding="utf-8")
    assert "db.delete(TaiKhoanDaXoa" not in nguon


def test_ten_dang_nhap_KHONG_dat_duy_nhat_o_bia_mo():
    """Một tên đăng nhập có thể được cấp lại. Ràng buộc duy nhất sẽ chặn việc ghi lại sự thật."""
    db = _db()
    ct = _u(db, "chutich", "chutich")
    for lan in (1, 2):
        x = _u(db, "nv.thao", mo=False)
        SX.xoa(db, ct, x.id, f"lần {lan}", xac_nhan=True)
        db.commit()
    assert len(db.execute(select(TaiKhoanDaXoa)).scalars().all()) == 2


# ═════════════════════════ SỬA ═════════════════════════

def test_chi_sua_duoc_nhung_cot_users_THUC_SU_co():
    """Bản đầu khai `email` và `phone` — bảng `users` không có hai cột ấy.

    Một ô người dùng gõ vào rồi mất chữ mà không báo lỗi là lỗi tệ nhất trong ba loại: nó không
    đỏ ở đâu cả, và người dùng tưởng đã sửa xong.
    """
    for c in SX.O_SUA:
        assert hasattr(User, c), f"Ô sửa {c!r} không có cột thật trong users"
    assert "email" not in SX.O_SUA and "phone" not in SX.O_SUA


def test_khong_sua_duoc_vai_tro_va_mat_khau_o_cua_nay():
    """Hai lối vào cho cùng một việc là hai chỗ phải rào, và quên một chỗ là hở."""
    assert "role" not in SX.O_SUA
    assert "password_hash" not in SX.O_SUA
    assert "active" not in SX.O_SUA, "Khoá/mở tài khoản có cửa riêng ở màn hình phân quyền"


def test_ho_ten_rong_bi_chan():
    db = _db()
    hr = _u(db, "hcns", "hcns")
    x = _u(db, "ai.do")
    with pytest.raises(ValueError, match="không được để trống"):
        SX.sua(db, hr, x.id, {"full_name": "   "})


def test_ma_nhan_vien_dat_TRUNG_bi_chan():
    """Mã nhân viên là thứ nhận ra người — hai tài khoản cùng mã là đúng cái mớ màn hình này dọn."""
    db = _db()
    hr = _u(db, "hcns", "hcns")
    _u(db, "van.anh", ma="269")
    x = _u(db, "vananh2")
    with pytest.raises(ValueError, match="đã thuộc về"):
        SX.sua(db, hr, x.id, {"staff_code": "269"})


def test_sua_ghi_nhat_ky_trang_thai_TRUOC_khi_sua():
    """Bài học TC-78: gọi sau khi đã gán thì cột 'before' ghi lại đúng trạng thái SAU."""
    db = _db()
    hr = _u(db, "hcns", "hcns")
    x = _u(db, "ai.do")
    x.full_name = "TÊN CŨ"; db.commit()
    SX.sua(db, hr, x.id, {"full_name": "Tên Mới"})
    db.commit()
    d = db.execute(select(AuditLog).where(AuditLog.action == "sua_tai_khoan")).scalars().first()
    assert d.before["full_name"] == "TÊN CŨ"
    assert d.after["full_name"] == "Tên Mới"


def test_khong_doi_gi_thi_khong_ghi_nhat_ky():
    """Một nhật ký đầy dòng 'đã sửa' mà không sửa gì là một nhật ký không ai đọc nữa."""
    db = _db()
    hr = _u(db, "hcns", "hcns")
    x = _u(db, "ai.do")
    r = SX.sua(db, hr, x.id, {"full_name": x.full_name})
    db.commit()
    assert r["da_doi"] == []
    assert db.execute(select(AuditLog).where(AuditLog.action == "sua_tai_khoan")).scalars().first() is None


# ═════════════════════════ QUYỀN ═════════════════════════

def test_ba_danh_sach_vai_dung_nhu_anh_Tuan_chot_24_9():
    from app.api.v1.gop_tai_khoan import GOP, SUA, XOA
    assert set(SUA) == {"hcns", "chutich", "tgd"}, "Sửa: NS, CT, TGĐ — không có cntt"
    assert set(XOA) == {"hcns", "chutich", "tgd"}, "Xoá: NS, CT, TGĐ — không có cntt"
    assert set(GOP) == {"chutich", "tgd", "hcns", "cntt"}, "Gộp: thêm hcns, giữ cntt"
    assert "cntt" not in SUA and "cntt" not in XOA, (
        "CNTT gộp được mà không sửa được — gộp là dọn dữ liệu, sửa họ tên là đổi hồ sơ nhân sự")


def test_khong_sinh_tien_to_moi_nen_bang_pham_vi_khong_doi():
    """Ba cửa mới đặt dưới tiền tố sẵn có — phần dôi ra vẫn là quyền đã cấp."""
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/gop-tai-khoan"] == ("/api/v1/gop-tai-khoan",)


def test_ba_cua_moi_deu_co_that():
    from app.main import app
    duong = {(r.path, m) for r in app.routes for m in getattr(r, "methods", [])}
    assert ("/api/v1/gop-tai-khoan/ho-so/{uid}", "PUT") in duong
    assert ("/api/v1/gop-tai-khoan/co-the-xoa/{uid}", "GET") in duong
    assert ("/api/v1/gop-tai-khoan/{uid}", "DELETE") in duong
    assert ("/api/v1/gop-tai-khoan/bia-mo", "GET") in duong


# ═════════════════════════ ĐẾM DÒNG ═════════════════════════

def test_dem_dong_doc_tu_sieu_du_lieu_khong_chep_tay():
    """Cột khoá ngoại thứ 24 ai đó thêm tuần sau cũng phải tự được đếm."""
    nguon = (GOC / "app" / "services" / "sua_xoa_tai_khoan.py").read_text(encoding="utf-8")
    assert "cot_tro_toi_users" in nguon, "Phải dùng chung bộ đếm với phép gộp"
    db = _db()
    x = _u(db, "ai.do", mo=False)
    _bk(db, "B1", x)
    dong = SX.dem_dong_tro_toi(db, x.id)
    assert any(d["bang"] == "bookings" for d in dong)


# ═════════════════════════ MÀN HÌNH ═════════════════════════

def test_man_hinh_co_du_ba_nut_va_hien_theo_dung_vai():
    t = (WEB / "app" / "gop-tai-khoan" / "page.tsx").read_text(encoding="utf-8")
    assert '"hcns", "chutich", "tgd"' in t.replace("'", '"'), "Thiếu danh sách vai sửa/xoá"
    assert "co-the-xoa" in t, "Nút xoá phải hỏi máy chủ trước khi sáng"
    assert "/ho-so/" in t, "Thiếu cửa sửa hồ sơ"
    assert "bia-mo" in t, "Thiếu bảng tài khoản đã xoá"


def test_man_hinh_noi_ro_vi_sao_nut_xoa_dang_toi():
    """Một nút tối không nói vì sao là một nút người dùng bấm mãi rồi đi hỏi CNTT."""
    t = (WEB / "app" / "gop-tai-khoan" / "page.tsx").read_text(encoding="utf-8")
    assert "can_tro" in t, "Phải in ra câu giải thích của máy chủ"
    assert "Chưa xoá được" in t


def test_ma_nguon_ghi_lai_vi_sao_CNTT_gop_duoc_ma_khong_sua_duoc():
    """Một danh sách vai lệch nhau mà không ai ghi vì sao sẽ bị người sau 'dọn cho đều'."""
    n = (GOC / "app" / "api" / "v1" / "gop_tai_khoan.py").read_text(encoding="utf-8")
    assert "DỌN DỮ LIỆU" in n and "HỒ SƠ NHÂN SỰ" in n
