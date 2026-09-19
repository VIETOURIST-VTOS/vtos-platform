"""TC-74 · DOANH THU TÍNH CHỈ TIÊU CỦA KHỐI KINH DOANH — anh Tuấn chốt 19/9/2026.

Hai lựa chọn của anh, và phép thử canh đúng hai lựa chọn ấy:

    "Lấy thẳng giá trị booking của người đó"                → không chia theo quyết toán
    "Ngày tour kết thúc, ví dụ khởi hành 28.9 kết thúc 3.10 → tính vào tháng 10"

Ví dụ thứ hai được dựng thành một phép thử nguyên văn: `test_vi_du_cua_anh_tuan_28_9_ket_thuc_3_10`.
Luật do người đặt ra bằng một ví dụ cụ thể thì ví dụ ấy phải nằm trong bộ thử, nếu không lần sửa sau
sẽ đúng theo chữ mà sai theo ý.

BỐN CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — đều là loại nhìn màn hình KHÔNG phát hiện được:

 1. DỊCH VỤ LẺ BIẾN MẤT. Cửa /tours giấu `non_package` khi không ai bảo khác; TC-71 đã sót đúng chỗ
    này và báo nhầm số. `test_khong_bo_sot_dich_vu_le` dựng một booking visa và đòi nó có mặt.

 2. TIỀN CỦA NGƯỜI CHƯA GÁN BỊ CỘNG CHO NGƯỜI KHÁC. 466 phiếu kho cũ mang `counts_for_target` tắt.
    Cộng nhầm tệ hơn để trống, nên chúng phải nằm riêng và KHÔNG vào tổng chỉ tiêu.

 3. CỘNG TRÙNG KHI LÊN CẤP. `theo_don_vi` cộng mỗi người vào cả team lẫn phòng lẫn chi nhánh — đúng
    ý, nhưng vì thế cộng các dòng ấy lại với nhau là ra số gấp ba. Phép thử ghim rằng tổng đúng là
    `tong_tinh_chi_tieu`, và ghim luôn quan hệ phòng = tổng các team.

 4. NHÃN CƠ SỞ BIẾN MẤT. Con số này cố ý không khớp màn hình Chủ tịch. Bỏ nhãn đi là để lại hai bảng
    nói hai số mà không ai biết vì sao — `test_luon_co_nhan_co_so_va_so_doi_chieu` không cho phép.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Booking, Tour, User
from app.services import doanh_thu_kd as DT
from app.services import to_chuc_kd as TC


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_kd"):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _tour(db, ma, ket_thuc, loai="le_noi_dia", trang_thai="ket_thuc", dt_qt=0.0, dong_luc=None):
    t = Tour(code=ma, name=ma, tour_type=loai,
             start_date=ket_thuc - dt.timedelta(days=2), end_date=ket_thuc,
             operator_id=1, status=trang_thai, actual_revenue=dt_qt, closed_at=dong_luc)
    db.add(t); db.commit()
    return t


def _bk(db, ma, t, u, tien, huy=False, tinh=True, khach=2):
    b = Booking(code=ma, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                customer_name="Khách " + ma, customer_phone="0900000000", source="thu",
                pax=khach, amount=tien,
                cancelled=huy, counts_for_target=tinh, sla_minutes=0, sla_ok=True)
    db.add(b); db.commit()
    return b


def _co_cau(db):
    """Chi nhánh CT → phòng CT-P → hai team, mỗi team một người."""
    hc = _u(db, "hcns", "hcns")
    ct = TC.tao_don_vi(db, hc, "CT", "Chi nhánh Cần Thơ", "chi_nhanh", hieu_luc_tu=dt.date(2026, 1, 1))
    p = TC.tao_don_vi(db, hc, "CT-P", "Phòng KDL", "phong", cha_id=ct.id, hieu_luc_tu=dt.date(2026, 1, 1))
    t1 = TC.tao_don_vi(db, hc, "CT-T1", "Team 1", "team", cha_id=p.id, hieu_luc_tu=dt.date(2026, 1, 1))
    t2 = TC.tao_don_vi(db, hc, "CT-T2", "Team 2", "team", cha_id=p.id, hieu_luc_tu=dt.date(2026, 1, 1))
    db.commit()
    return hc, ct, p, t1, t2


# ── Luật kỳ: ngày tour KẾT THÚC ────────────────────────────────────────────────────────────────

def test_vi_du_cua_anh_tuan_28_9_ket_thuc_3_10():
    """Nguyên văn ví dụ anh Tuấn đưa ra khi chốt luật: khởi hành 28/9, kết thúc 3/10 → tháng 10."""
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "X", dt.date(2026, 10, 3))
    assert t.start_date == dt.date(2026, 10, 1)      # tour 2 đêm, khởi hành trước ngày kết thúc
    t.start_date = dt.date(2026, 9, 28); db.commit()
    _bk(db, "BK1", t, u, 10_000_000)

    assert DT.thang(db, "2026-09")["tong_tinh_chi_tieu"] == 0, "Tháng khởi hành KHÔNG được ăn doanh thu"
    assert DT.thang(db, "2026-10")["tong_tinh_chi_tieu"] == 10_000_000


def test_ky_khong_doc_duoc_thi_bao_loi_ro_rang():
    db = _db()
    with pytest.raises(ValueError) as e:
        DT.thang(db, "thang 9")
    assert "2026-09" in str(e.value), "Báo lỗi phải chỉ ra dạng đúng, không chỉ nói là sai"


def test_ngay_ket_thuc_khong_duoc_rong():
    """Cả luật kỳ đứng trên cột này, nên ràng buộc của nó phải được canh.

    Ban đầu em viết một nhánh phòng thủ "chuyến thiếu ngày kết thúc thì không thuộc kỳ nào". Chạy
    thử mới thấy cột `tours.end_date` là NOT NULL — nhánh ấy không bao giờ chạy được, tức là mã
    chết. Bỏ mã chết đi và canh thẳng ràng buộc: hôm nào ai nới cột ra thì phép thử này gãy, và
    người nới phải trả lời "chuyến không có ngày kết thúc thì tính vào kỳ nào", chứ không để câu
    hỏi ấy rơi im lặng vào một nhánh mặc định.
    """
    assert Tour.__table__.columns["end_date"].nullable is False


# ── Luật số: giá trị booking, KHÔNG chia theo quyết toán ───────────────────────────────────────

def test_lay_gia_tri_booking_khong_lay_quyet_toan():
    """Chuyến quyết toán 100tr nhưng booking chỉ 70tr: chỉ tiêu ăn 70tr, đúng lựa chọn của anh Tuấn."""
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "X", dt.date(2026, 9, 10), dt_qt=100_000_000)
    _bk(db, "BK1", t, u, 70_000_000)
    assert DT.thang(db, "2026-09")["tong_tinh_chi_tieu"] == 70_000_000


def test_booking_huy_khong_tinh():
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, u, 10_000_000)
    _bk(db, "BK2", t, u, 99_000_000, huy=True)   # huỷ mà vẫn còn số tiền – phải lọc bằng CỜ
    assert DT.thang(db, "2026-09")["tong_tinh_chi_tieu"] == 10_000_000


def test_khong_bo_sot_dich_vu_le():
    """Cửa /tours giấu non_package mặc định. Tệp này đọc thẳng mô hình nên không được sót."""
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "DVL-VISA01", dt.date(2026, 9, 10), loai="non_package")
    _bk(db, "BK1", t, u, 8_000_000)
    kq = DT.thang(db, "2026-09")
    assert kq["tong_tinh_chi_tieu"] == 8_000_000, (
        "Dịch vụ lẻ bị sót – đúng lỗi đã mắc ở TC-71 khi đọc qua cửa /tours thay vì đọc mô hình.")


# ── Ba nhóm nằm ngoài chỉ tiêu, phải hiện ra ───────────────────────────────────────────────────

def test_chua_gan_nguoi_ban_khong_vao_chi_tieu_nhung_van_hien():
    db = _db(); u = _u(db, "chi"); kho = _u(db, "khocu")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, u, 10_000_000)
    _bk(db, "KC-1", t, kho, 19_000_000, tinh=False)
    kq = DT.thang(db, "2026-09")
    assert kq["tong_tinh_chi_tieu"] == 10_000_000
    assert kq["theo_ngan"]["chua_ro"] == {"so_booking": 1, "tien": 19_000_000}, (
        "Tiền chưa gán người bán phải HIỆN RA – cùng luật với 38 chuyến chưa gán pháp nhân ở TC-71.")


def test_nguoi_ngoai_khoi_chua_bat_quyen_ban_thi_vao_ngan_chua_ro():
    db = _db(); kd = _u(db, "chi"); dh = _u(db, "dieuhanh", "nv_dh")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, kd, 10_000_000)
    _bk(db, "BK2", t, dh, 4_000_000)
    kq = DT.thang(db, "2026-09")
    assert kq["tong_tinh_chi_tieu"] == 10_000_000
    # Người Điều hành CHƯA được bật ô "được bán hàng" nên rơi vào ngăn "chưa rõ", không phải
    # "ngoài khối". Đúng ý: ngăn "ngoài khối" chỉ dành cho người đã được HC-NS cho phép bán.
    assert kq["theo_ngan"]["chua_ro"]["tien"] == 4_000_000


def test_nguoi_chua_co_don_vi_khong_bi_nhet_tam_vao_dau():
    db = _db(); _co_cau(db); u = _u(db, "chi")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, u, 10_000_000)
    kq = DT.thang(db, "2026-09")
    assert kq["tong_tinh_chi_tieu"] == 10_000_000
    assert kq["chua_co_don_vi"]["so_nguoi"] == 1
    assert kq["theo_don_vi"] == [], "Chưa phân công thì không đơn vị nào được nhận tiền này"


# ── Cộng lên cấp, và cái bẫy cộng trùng ────────────────────────────────────────────────────────

def test_phong_bang_tong_cac_team_va_khong_cong_trung():
    db = _db(); hc, ct, p, t1, t2 = _co_cau(db)
    a, b = _u(db, "a"), _u(db, "b")
    TC.phan_cong(db, hc, a.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    TC.phan_cong(db, hc, b.id, t2.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, a, 30_000_000)
    _bk(db, "BK2", t, b, 20_000_000)

    kq = DT.thang(db, "2026-09")
    theo = {d["ma"]: d["tien"] for d in kq["theo_don_vi"]}
    assert theo["CT-T1"] == 30_000_000
    assert theo["CT-T2"] == 20_000_000
    assert theo["CT-P"] == 50_000_000, "Phòng phải bằng tổng các team"
    assert theo["CT"] == 50_000_000, "Chi nhánh phải bằng tổng các phòng"
    assert kq["tong_tinh_chi_tieu"] == 50_000_000, (
        "Tổng đúng là tong_tinh_chi_tieu. Cộng các dòng theo_don_vi lại với nhau ra 150tr – "
        "mỗi người đã được cộng vào cả team, phòng lẫn chi nhánh.")


def test_chuyen_team_giua_ky_tinh_theo_don_vi_cuoi_ky():
    """Một luật, viết một chỗ: đơn vị xét tại NGÀY CUỐI KỲ."""
    db = _db(); hc, ct, p, t1, t2 = _co_cau(db)
    a = _u(db, "a")
    TC.phan_cong(db, hc, a.id, t1.id, "nhan_vien", dt.date(2026, 1, 1), dt.date(2026, 9, 14))
    TC.phan_cong(db, hc, a.id, t2.id, "nhan_vien", dt.date(2026, 9, 15), ly_do="Chuyển team")
    db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))     # chuyến kết thúc 10/9, lúc ấy còn ở Team 1
    _bk(db, "BK1", t, a, 10_000_000)
    theo = {d["ma"]: d["tien"] for d in DT.thang(db, "2026-09")["theo_don_vi"]}
    assert theo.get("CT-T2") == 10_000_000, "Cuối tháng 9 người này ở Team 2 nên Team 2 nhận"
    assert "CT-T1" not in theo


# ── Phạm vi xem cắt ở máy chủ ──────────────────────────────────────────────────────────────────

def test_pham_vi_rong_khac_voi_xem_tat_ca():
    db = _db(); hc, ct, p, t1, t2 = _co_cau(db)
    a = _u(db, "a")
    TC.phan_cong(db, hc, a.id, t1.id, "nhan_vien", dt.date(2026, 1, 1)); db.commit()
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, a, 10_000_000)
    assert DT.thang(db, "2026-09", pham_vi=None)["tong_tinh_chi_tieu"] == 10_000_000
    assert DT.thang(db, "2026-09", pham_vi=[])["tong_tinh_chi_tieu"] == 0
    assert DT.thang(db, "2026-09", pham_vi=[t2.id])["tong_tinh_chi_tieu"] == 0
    assert DT.thang(db, "2026-09", pham_vi=[t1.id])["tong_tinh_chi_tieu"] == 10_000_000


# ── Nhãn cơ sở: điều kiện tồn tại của luật này ────────────────────────────────────────────────

def test_luon_co_nhan_co_so_va_so_doi_chieu():
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "X", dt.date(2026, 9, 10), trang_thai="da_dong_so", dt_qt=90_000_000,
              dong_luc=dt.datetime(2026, 9, 20, 10, 0))
    _bk(db, "BK1", t, u, 70_000_000)
    kq = DT.thang(db, "2026-09")
    assert "NGÀY TOUR KẾT THÚC" in kq["co_so"]
    assert "Chủ tịch" in kq["co_so"], "Nhãn phải nói thẳng là không khớp màn hình Chủ tịch"
    dc = kq["doi_chieu_quyet_toan"]
    assert dc["tien"] == 90_000_000 and dc["so_chuyen"] == 1
    assert kq["tong_tinh_chi_tieu"] == 70_000_000, (
        "Hai con số cố ý khác nhau. Phép thử này ghim cả hai cùng xuất hiện, để không ai lặng lẽ bỏ "
        "một cái đi cho 'gọn'.")


def test_doi_chieu_dung_lai_danh_sach_trang_thai_cua_man_hinh_chu_tich():
    """Không chép danh sách trạng thái sang đây – hai màn hình phải đổi cùng lúc."""
    import inspect
    from app.services import ket_qua_that as KQ
    ma = inspect.getsource(DT)
    assert "from app.services.ket_qua_that import DA_DONG_SO" in ma
    for tt in KQ.DA_DONG_SO:
        assert f'"{tt}"' not in ma, f"Trạng thái {tt!r} bị chép cứng vào doanh_thu_kd.py"


# ── Màn hình của một nhân viên ─────────────────────────────────────────────────────────────────

def test_man_hinh_nhan_vien_chi_thay_booking_cua_minh():
    db = _db(); a, b = _u(db, "a"), _u(db, "b")
    t = _tour(db, "X", dt.date(2026, 9, 10))
    _bk(db, "BK1", t, a, 10_000_000)
    _bk(db, "BK2", t, b, 20_000_000)
    kq = DT.cua_nguoi(db, a.id, "2026-09")
    assert kq["tien"] == 10_000_000 and kq["so_booking"] == 1
    assert all(d["user_id"] == a.id for d in kq["rows"])


# ── Ba luồng: điều kiện tồn tại của cả cấu trúc ────────────────────────────────────────────────

def test_ba_luong_roi_nhau_va_cong_du():
    """Lẻ + Đoàn + Dịch vụ lẻ = tổng. Không dòng nào ở hai luồng, không dòng nào rơi ra ngoài.

    Sai chỗ này thì màn hình Chủ tịch và hai màn hình phòng lệch nhau mà không ai tìm ra chỗ hụt.
    """
    db = _db(); u = _u(db, "chi")
    le = _tour(db, "LE1", dt.date(2026, 9, 10), loai="le_noi_dia")
    doan = _tour(db, "DN1", dt.date(2026, 9, 11), loai="doan_noi_dia")
    dvl = _tour(db, "DVL-VISA9", dt.date(2026, 9, 12), loai="non_package")
    _bk(db, "B1", le, u, 10_000_000)
    _bk(db, "B2", doan, u, 20_000_000)
    _bk(db, "B3", dvl, u, 5_000_000)

    kq = DT.thang(db, "2026-09")
    tl = kq["theo_luong"]
    assert tl["le"]["tien"] == 10_000_000
    assert tl["doan"]["tien"] == 20_000_000
    assert tl["dich_vu_le"]["tien"] == 5_000_000
    assert sum(v["tien"] for v in tl.values()) == kq["tong_tinh_chi_tieu"] == 35_000_000
    assert sum(v["so_booking"] for v in tl.values()) == 3


def test_tour_ma_mice_la_doan_du_loai_chuyen_ghi_khac():
    """Quy tắc mảng là HỢP của hai điều kiện – không chép lại, gọi thẳng segments."""
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "MICE-2609", dt.date(2026, 9, 10), loai="le_noi_dia")
    _bk(db, "B1", t, u, 7_000_000)
    assert DT.thang(db, "2026-09")["theo_luong"]["doan"]["tien"] == 7_000_000


def test_dich_vu_le_khong_bi_nhet_vao_mang_le():
    """segments.py chốt: dịch vụ lẻ không thuộc mảng nào, cả hai phòng đều bán được."""
    db = _db(); u = _u(db, "chi")
    t = _tour(db, "DVL-OTHER1", dt.date(2026, 9, 10), loai="non_package")
    _bk(db, "B1", t, u, 9_000_000)
    tl = DT.thang(db, "2026-09")["theo_luong"]
    assert tl["dich_vu_le"]["tien"] == 9_000_000
    assert tl["le"]["tien"] == 0, "Nhét dịch vụ lẻ vào Lẻ là gán doanh thu phòng Đoàn sang phòng Lẻ"


def test_loc_mot_luong_cho_man_hinh_tung_phong():
    db = _db(); u = _u(db, "chi")
    le = _tour(db, "LE1", dt.date(2026, 9, 10), loai="le_noi_dia")
    doan = _tour(db, "DN1", dt.date(2026, 9, 11), loai="doan_noi_dia")
    _bk(db, "B1", le, u, 10_000_000); _bk(db, "B2", doan, u, 20_000_000)
    assert DT.thang(db, "2026-09", luong="le")["tong_tinh_chi_tieu"] == 10_000_000
    assert DT.thang(db, "2026-09", luong="doan")["tong_tinh_chi_tieu"] == 20_000_000
    with pytest.raises(ValueError):
        DT.thang(db, "2026-09", luong="mice")


def test_khong_chep_luat_phan_mang_sang_day():
    """Một luật, một chỗ. Chép sang là cầm chắc ngày hai nơi nói khác nhau."""
    import inspect
    from app.services import segments as SEG
    ma = inspect.getsource(DT)
    assert "SEG.mang_of" in ma, "Phải gọi thẳng segments.mang_of()"
    for t in SEG.DOAN_TYPES + SEG.LE_TYPES + (SEG.MICE_PREFIX,):
        assert f'"{t}"' not in ma, f"Luật phân mảng ({t!r}) bị chép cứng vào doanh_thu_kd.py"


def test_dich_vu_le_van_cong_len_don_vi_cua_nguoi_ban():
    """Người bán ở cây Đoàn bán một dịch vụ lẻ thì tiền về đơn vị Đoàn của họ, không về Lẻ."""
    db = _db(); hc, ct, p, t1, t2 = _co_cau(db)
    dct = TC.tao_don_vi(db, hc, "D-CT", "Chi nhánh Cần Thơ (Đoàn)", "chi_nhanh", mang="doan",
                        hieu_luc_tu=dt.date(2026, 1, 1))
    db.commit()
    u = _u(db, "doan1")
    TC.phan_cong(db, hc, u.id, dct.id, "nhan_vien", dt.date(2026, 1, 1)); db.commit()
    t = _tour(db, "DVL-VISA9", dt.date(2026, 9, 10), loai="non_package")
    _bk(db, "B1", t, u, 6_000_000)
    theo = {d["ma"]: d["tien"] for d in DT.thang(db, "2026-09")["theo_don_vi"]}
    assert theo.get("D-CT") == 6_000_000
