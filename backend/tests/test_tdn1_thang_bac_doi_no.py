"""TDN-1 · Thang bậc đòi nợ khách — hàng rào, Chủ tịch quyết 25/9/2026, câu 5.

    Mảng ĐOÀN:  nhân viên sale đã bán  →  Sale Admin        →  Phó TGĐ Đoàn
    Mảng LẺ:    nhân viên sale đã bán  →  Trưởng phòng KD   →  Giám đốc KD

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN ĐIỀU PHÉP THỬ NÀY CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
 1. MỘT KHOẢN NỢ LÀ MỘT DÒNG. Đẩy lên bậc 2 không được sinh thêm cảnh báo — ba bản của cùng một
    vấn đề thì đóng một bản còn hai, và con số "bao nhiêu khoản đang trễ" đếm gấp ba.
 2. HAI MẢNG HAI THANG. Đây là toàn bộ nội dung câu trả lời của Chủ tịch; một thang chung là khai
    sai một nửa số khoản, và khai sai kiểu mỗi mảng nhìn riêng đều thấy hợp lý.
 3. VAI CÓ HAI NGƯỜI THÌ KHÔNG ĐOÁN. Chọn bừa người đầu danh sách là tạo ra một người chịu trách
    nhiệm giả — người ấy không biết mình vừa được giao một khoản nợ.
 4. CHẠY LẠI KHÔNG ĐỔI GÌ THÊM. Robot chạy mỗi giờ; một bộ quét cộng dồn sẽ nối thêm một dòng
    "[ĐẨY LÊN BẬC 2]" vào lời nhắn mỗi giờ cho tới khi không ai đọc nổi nó nữa.
"""
import datetime as dt
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Alert, AuditLog, Booking, Param, ServiceRequest, Tour, User
from app.services import rules as R
from app.services import thang_doi_no as TDN

HOM_NAY = dt.date.today()


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvkd", "nv_kd"), ("tpkd", "tp_kd"), ("gdkd", "gd_kd"),
                     ("sadmin", "sales_admin"), ("ptgd", "ptgd_doan"), ("nvdh", "nv_dh")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    R.clear_param_cache()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _moc(db, m2, m3):
    for k, v in (("no_khach_bac2_ngay", m2), ("no_khach_bac3_ngay", m3)):
        db.add(Param(key=k, value=str(v), label=k, unit="ngày",
                     effective_from=date(2026, 1, 1), status="active"))
    db.commit(); R.clear_param_cache()


def _no(db, ma="MICE-01", loai="doan_noi_dia", tre=0):
    """Một booking quá hạn thu `tre` ngày, kèm đúng cảnh báo mà robot sinh ra hôm nay."""
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=HOM_NAY + dt.timedelta(days=10),
             end_date=HOM_NAY + dt.timedelta(days=12), operator_id=_u(db, "nvdh").id,
             status="da_duyet", price_per_pax=10_000_000.0, planned_pax=10, seats_open=10)
    db.add(t); db.flush()
    r = ServiceRequest(tour_id=t.id, sales_id=_u(db, "nvkd").id, customer_name="Khách A",
                       customer_phone="0900000000", source="web", pax=2)
    db.add(r); db.flush()
    b = Booking(tour_id=t.id, request_id=r.id, created_by=_u(db, "nvdh").id,
                code=f"BK-{ma}", customer_name="Khách A", customer_phone="0900000000",
                source="web", pax=2,
                amount=20_000_000.0, paid=5_000_000.0, sales_id=_u(db, "nvkd").id,
                cancel_deadline=dt.datetime.now() - dt.timedelta(days=tre))
    db.add(b); db.flush()
    a = Alert(kind=TDN.KIND, level="red", ref=f"booking:{b.code}",
              message=f"{b.code} quá deadline hủy chỗ", to_roles="nv_kd,gd_kd,tp_dh,ketoan")
    db.add(a); db.commit(); db.refresh(a)
    return t, b, a


# ───────────────────────── bậc 1 ─────────────────────────

def test_tdn1_bac1_ve_dung_sale_da_ban_va_go_danh_sach_bon_vai():
    """Dòng sinh ra hôm nay mang `to_roles` bốn vai và chủ để trống — đúng trạng thái PQ-9 đo được.
    Lượt quét đầu tiên phải kéo nó về một người."""
    db = _db(); _moc(db, 3, 7)
    t, b, a = _no(db, tre=0)
    TDN.quet(db); db.refresh(a)
    assert a.nguoi_phu_trach == _u(db, "nvkd").id and a.bac == 1
    assert a.giao_luc is not None
    # `to_roles` KHÔNG bị thu về một vai: Điều hành và Kế toán vẫn phải thấy khoản nợ này.
    assert {"nv_kd", "tp_dh", "ketoan"} <= set(a.to_roles.split(","))


# ───────────────────────── hai mảng, hai thang ─────────────────────────

def test_tdn1_mang_doan_len_sale_admin_roi_ptgd_doan():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, ma="MICE-02", loai="doan_noi_dia", tre=4)
    TDN.quet(db); db.refresh(a)
    assert a.bac == 2 and "sales_admin" in a.to_roles and a.nguoi_phu_trach == _u(db, "sadmin").id

    db2 = _db(); _moc(db2, 3, 7)
    _, _, a2 = _no(db2, ma="MICE-03", loai="doan_noi_dia", tre=9)
    TDN.quet(db2); db2.refresh(a2)
    assert a2.bac == 3 and "ptgd_doan" in a2.to_roles and a2.nguoi_phu_trach == _u(db2, "ptgd").id


def test_tdn1_mang_le_len_tp_kd_roi_gd_kd():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, ma="LE-02", loai="le_noi_dia", tre=4)
    TDN.quet(db); db.refresh(a)
    assert a.bac == 2 and "tp_kd" in a.to_roles and a.nguoi_phu_trach == _u(db, "tpkd").id

    db2 = _db(); _moc(db2, 3, 7)
    _, _, a2 = _no(db2, ma="LE-03", loai="le_noi_dia", tre=9)
    TDN.quet(db2); db2.refresh(a2)
    assert a2.bac == 3 and a2.nguoi_phu_trach == _u(db2, "gdkd").id


def test_tdn1_hai_thang_khong_bao_gio_trung_nhau_o_bac_2_va_3():
    """Nếu một ngày ai đó "cho gọn" hai thang thành một thì phép thử này đỏ — chứ không phải chờ
    tới lúc một khoản nợ đoàn rơi vào bàn Trưởng phòng Kinh doanh Lẻ."""
    assert TDN.THANG["doan"][0] == TDN.THANG["le"][0] == "nv_kd"
    assert TDN.THANG["doan"][1] != TDN.THANG["le"][1]
    assert TDN.THANG["doan"][2] != TDN.THANG["le"][2]


def test_tdn1_ma_MICE_di_thang_doan_du_loai_chuyen_ghi_le():
    """Cùng luật nhận mảng với `segments` — hợp của hai quy tắc, chốt 07/9/2026."""
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, ma="MICE-99", loai="le_noi_dia", tre=4)
    TDN.quet(db); db.refresh(a)
    assert a.nguoi_phu_trach == _u(db, "sadmin").id


def test_tdn1_chuyen_khong_thuoc_mang_nao_van_co_nguoi_doi():
    """Dịch vụ lẻ và dữ liệu cũ chưa khai loại chuyến đi thang mảng Lẻ. Một khoản nợ không ai đòi
    vì ô loại chuyến để trống là cách tệ nhất để mất tiền."""
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, ma="DVL-01", loai="non_package", tre=4)
    TDN.quet(db); db.refresh(a)
    assert a.nguoi_phu_trach == _u(db, "tpkd").id


# ───────────────────────── một khoản nợ, một dòng ─────────────────────────

def test_tdn1_day_bac_KHONG_sinh_them_canh_bao():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, tre=4)
    TDN.quet(db)
    assert db.execute(select(Alert)).scalars().all().__len__() == 1


def test_tdn1_chay_lai_khong_cong_don_loi_nhan():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, tre=4)
    TDN.quet(db); db.refresh(a); mot_lan = a.message
    TDN.quet(db); TDN.quet(db); db.refresh(a)
    assert a.message == mot_lan, "mỗi lượt quét nối thêm một dòng vào lời nhắn"
    assert a.message.count("ĐẨY LÊN BẬC") == 1


def test_tdn1_chi_ghi_nhat_ky_o_dong_that_su_doi_bac():
    db = _db(); _moc(db, 3, 7)
    _no(db, tre=4)
    TDN.quet(db); TDN.quet(db); TDN.quet(db)
    vet = db.execute(select(AuditLog).where(AuditLog.action == "day_bac_doi_no")).scalars().all()
    assert len(vet) == 1, "mỗi lượt quét đẻ một trang nhật ký không tin nào"


def test_tdn1_bac_1_khong_ghi_nhat_ky_day_bac():
    """Bậc 1 là chỗ khoản nợ bắt đầu, không phải một lần đẩy lên."""
    db = _db(); _moc(db, 3, 7)
    _no(db, tre=0)
    TDN.quet(db)
    assert not db.execute(select(AuditLog).where(AuditLog.action == "day_bac_doi_no")).scalars().all()


# ───────────────────────── không đoán chủ ─────────────────────────

def test_tdn1_vai_co_hai_nguoi_thi_de_trong_chu_va_DEM_lai():
    db = _db(); _moc(db, 3, 7)
    db.add(User(username="sadmin2", full_name="sadmin2", role="sales_admin", password_hash="x"))
    db.commit()
    _, _, a = _no(db, ma="MICE-04", tre=4)
    kq = TDN.quet(db); db.refresh(a)
    assert a.nguoi_phu_trach is None and a.bac == 2
    assert "sales_admin" in a.to_roles, "vẫn phải gửi theo vai — không có chủ khác với không gửi ai"
    assert len(kq["khong_ro_chu"]) == 1 and "2 tài khoản" in kq["khong_ro_chu"][0]["ly_do"]


def test_tdn1_vai_khong_co_ai_thi_de_trong_chu_va_DEM_lai():
    db = _db(); _moc(db, 3, 7)
    u = _u(db, "ptgd"); u.active = False; db.commit()
    _, _, a = _no(db, ma="MICE-05", tre=9)
    kq = TDN.quet(db); db.refresh(a)
    assert a.nguoi_phu_trach is None and "ptgd_doan" in a.to_roles
    assert "chưa có tài khoản" in kq["khong_ro_chu"][0]["ly_do"]


def test_tdn1_canh_bao_tro_toi_booking_khong_con_thi_dem_lai_chu_khong_im():
    """`bookings.sales_id` là cột KHÔNG RỖNG, nên "booking chưa có sale" không xảy ra được — đo
    lúc viết phép thử này. Chỗ thật sự mất chủ ở bậc 1 là cảnh báo trỏ tới một mã booking không
    còn: dữ liệu cũ nạp vào, mã gõ sai, hoặc booking bị dọn. Nhánh phòng thủ cho `sales_id` rỗng
    vẫn giữ trong mã (`chu_canh_bao` cũng giữ), nhưng phép thử phải canh chỗ chạm tới được."""
    db = _db(); _moc(db, 3, 7)
    _no(db, tre=0)
    db.add(Alert(kind=TDN.KIND, level="red", ref="booking:KHONG-CO",
                 message="mồ côi", to_roles="nv_kd,gd_kd"))
    db.commit()
    kq = TDN.quet(db)
    assert len(kq["khong_ro_chu"]) == 1
    assert "không tìm thấy booking" in kq["khong_ro_chu"][0]["ly_do"]


# ───────────────────────── mốc ngày ─────────────────────────

def test_tdn1_moc_roi_dung_ngay_la_DA_len_bac():
    """Mốc ở đây đếm từ một hạn ĐÃ QUA, khác quy ước của `han_cong_no` (hạn rơi đúng ngày báo cáo
    chưa phải quá hạn) — nên phải viết ra, không để người đọc tự suy."""
    assert TDN.bac_can_co(2, 3, 7) == 1
    assert TDN.bac_can_co(3, 3, 7) == 2
    assert TDN.bac_can_co(6, 3, 7) == 2
    assert TDN.bac_can_co(7, 3, 7) == 3
    assert TDN.bac_can_co(70, 3, 7) == 3


def test_tdn1_doi_moc_o_man_hinh_chinh_sach_la_doi_duoc_thang():
    """Hai con số ngày là THAM SỐ, không phải hằng số trong mã — Chủ tịch chỉ định người, còn mốc
    thì phòng ban chỉnh được mà không cần triển khai lại."""
    db = _db(); _moc(db, 1, 2)
    _, _, a = _no(db, ma="MICE-06", tre=2)
    TDN.quet(db); db.refresh(a)
    assert a.bac == 3 and a.nguoi_phu_trach == _u(db, "ptgd").id


def test_tdn1_canh_bao_da_dong_thi_khong_dung_toi():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, tre=9)
    a.resolved = True; db.commit()
    kq = TDN.quet(db); db.refresh(a)
    assert a.to_roles == "nv_kd,gd_kd,tp_dh,ketoan" and a.bac is None and kq["bac_3"] == 0


def test_tdn1_to_roles_chi_cong_them_KHONG_BAO_GIO_thu_hep():
    """Hàng rào của một lỗi em vừa gây ra rồi sửa, ngày 26/9/2026.

    Bản đầu đặt `to_roles = vai` — gọn, và sai. Phép thử `test_bookings` đỏ ngay: Trưởng phòng
    Điều hành mở bảng cảnh báo thì khoản nợ ĐÃ BIẾN MẤT, vì màn hình lọc theo vai. Một cảnh báo
    lặng lẽ rời khỏi bảng của hai bộ phận đang theo nó là kiểu hỏng không ai báo lỗi.

    PQ-9 tách hai cột đúng để tránh chuyện này: `nguoi_phu_trach` đổi theo bậc, `to_roles` thì
    cộng dồn."""
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, ma="MICE-07", tre=9)
    goc = set(a.to_roles.split(","))
    TDN.quet(db); db.refresh(a)
    nay = set(a.to_roles.split(","))
    assert goc <= nay, "leo bậc đã lấy mất người nhận tin"
    assert "ptgd_doan" in nay


def test_tdn1_bac_3_luon_la_mau_do():
    db = _db(); _moc(db, 3, 7)
    _, _, a = _no(db, tre=9)
    a.level = "warn"; db.commit()
    TDN.quet(db); db.refresh(a)
    assert a.level == "red"
