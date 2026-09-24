"""TC-85 · NGÕ CỤT TRÊN MÀN HÌNH GỘP — anh Tuấn 25/9/2026: "tại sao bị nhiều tài khoản ko xóa dc?"

Ảnh anh gửi: `phamthithuyvy2`, trạng thái **Đã khoá**, còn 2 dòng trỏ tới (`bookings.created_by` 1,
`bookings.sales_id` 1). Màn hình bảo "dùng nút GỘP để chuyển hết sang tài khoản giữ lại, xong thì
nút xoá mới sáng" — mà **không có nút gộp nào trên dòng ấy**. Câu hướng dẫn chỉ tới một nút không
tồn tại, và người đọc không còn đường nào đi tiếp.

HAI ĐIỀU KIỆN MÀN HÌNH TỰ THÊM, cả hai đều không có ở máy chủ:

  1. `t.dang_mo` — chỉ vẽ nút Gộp khi tài khoản thừa CÒN MỞ. `services/gop_tai_khoan.py` chưa bao
     giờ đọc `active` của bên bị gộp; nó chỉ đòi bên GIỮ LẠI còn mở, vì dồn dữ liệu vào một tài
     khoản chết mới là cái sai. Một tài khoản bị khoá tay trước đó mà vẫn còn dòng thì rơi vào
     ngõ cụt: còn dòng nên không xoá được, đã khoá nên không hiện nút gộp.

  2. `n.goi_y_giu` — chỉ vẽ nút Gộp khi máy đoán được giữ cái nào, tức đúng một tài khoản trong
     nhóm có mã nhân viên. Cả nhóm không ai có mã thì cả nhóm không gộp được dòng nào. Máy đoán
     không ra là giới hạn của máy, không phải của người: người vẫn biết rõ giữ cái nào.

CÁCH SỬA: bỏ điều kiện thứ nhất, và thay điều kiện thứ hai bằng nút "Giữ cái này" trên từng dòng.
Gợi ý của máy vẫn hiện và vẫn được dùng làm mặc định — người chọn thì thắng gợi ý. Bước xem trước
KHÔNG bỏ: gộp vẫn là việc một chiều.

CÁI KHÔNG ĐƯỢC NỚI: gộp VÀO một tài khoản đang khoá vẫn phải chặn. Hai luật ngược chiều nhau ở hai
đầu của cùng một phép gộp, nên phép thử dưới đây giữ CẢ HAI để lần sau không ai nới nhầm đầu.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour, User
from app.services import gop_tai_khoan as GTK

TRANG = Path(__file__).resolve().parents[2] / "web" / "app" / "gop-tai-khoan" / "page.tsx"


def _db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    return sessionmaker(bind=e)()


def _u(db, ten, ma="", mo=True):
    u = User(username=ten, full_name="Pham Thi Thuy Vy", role="nv_kd", password_hash="x",
             staff_code=ma, active=mo)
    db.add(u); db.commit()
    return u


def _bk(db, ma, u):
    t = Tour(code=ma, name=ma, tour_type="le_noi_dia", start_date=dt.date(2026, 9, 1),
             end_date=dt.date(2026, 9, 3), operator_id=u.id, status="ket_thuc")
    db.add(t); db.commit()
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="K", customer_phone="09", source="truc_tiep", pax=1,
                amount=1_000_000, sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


# ───────────────────────── máy chủ: hai đầu, hai luật ngược chiều ─────────────────────────

def test_tc85_1_gop_duoc_mot_tai_khoan_DA_KHOA():
    """Đúng trường hợp trong ảnh anh Tuấn gửi: bên bị gộp đã khoá mà vẫn còn dòng."""
    db = _db()
    giu = _u(db, "phamthithuyvy", ma="NV001")
    bo = _u(db, "phamthithuyvy2", mo=False)          # đã khoá, vẫn còn dòng
    _bk(db, "BK1", bo)
    boi = _u(db, "chutich1", ma="NV000"); boi.role = "chutich"; db.commit()

    r = GTK.gop(db, boi, giu.id, bo.id, "don tai khoan trung", xac_nhan=True)

    assert r["da_ghi"] is True
    assert r["tong_dong_se_chuyen"] >= 2, "phải chuyển cả created_by lẫn sales_id"
    con_lai = db.execute(select(Booking).where(Booking.sales_id == bo.id)).scalars().all()
    assert con_lai == [], "còn dòng trỏ vào tài khoản cũ thì nút xoá vẫn không sáng được"


def test_tc85_2_van_chan_gop_VAO_mot_tai_khoan_dang_khoa():
    """Đầu kia của cùng phép gộp. Nới đầu này là dồn dữ liệu vào chỗ không ai mở được."""
    db = _db()
    giu = _u(db, "tk_chet", mo=False)
    bo = _u(db, "tk_song")
    boi = _u(db, "chutich2", ma="NV000"); boi.role = "chutich"; db.commit()

    with pytest.raises(ValueError, match="khoá"):
        GTK.gop(db, boi, giu.id, bo.id, "thu", xac_nhan=True)


# ───────────────────────── màn hình: bỏ đúng hai điều kiện thừa ─────────────────────────

def test_tc85_3_nut_gop_khong_con_doi_tai_khoan_con_mo():
    ma = TRANG.read_text(encoding="utf-8")
    assert "t.dang_mo &&" not in ma, (
        "màn hình lại đòi tài khoản còn mở mới cho gộp — đó chính là ngõ cụt của 25/9/2026")
    assert "t.dang_mo ?" in ma, "vẫn phải in trạng thái Đang mở / Đã khoá cho người đọc"


def test_tc85_4_nguoi_tu_chon_duoc_tai_khoan_giu_lai():
    ma = TRANG.read_text(encoding="utf-8")
    assert "Giữ cái này" in ma, "máy đoán không ra thì người phải chỉ được"
    assert "chonGiu" in ma
    # Người chọn thắng gợi ý của máy, không phải ngược lại.
    assert "chonGiu[khoa] ?? n.goi_y_giu" in ma


def test_tc85_5_khoa_nhom_la_id_khong_phai_ho_ten():
    """Hai người trùng tên là đúng thứ màn hình này sinh ra để xử lý."""
    ma = TRANG.read_text(encoding="utf-8")
    assert "Math.min(...n.tai_khoan.map" in ma


def test_tc85_6_gop_van_di_qua_buoc_xem_truoc():
    ma = TRANG.read_text(encoding="utf-8")
    assert "onClick={() => xem(giu, t.id)}" in ma, "nút gộp phải mở xem trước, không ghi thẳng"
