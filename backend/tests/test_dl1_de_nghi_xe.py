# -*- coding: utf-8 -*-
"""DL-1 · Đề nghị xe — mắt đầu của chuỗi điều xe Chủ tịch đặc tả ngày 11/10/2026.

    Điều hành ĐỀ NGHỊ xe  →  Giám đốc đội xe LẬP LỆNH  →  Tài xế NHẬN

Trước bản này chuỗi chỉ có mắt giữa: `POST /dispatch` cho cả Điều hành lẫn Giám đốc đội xe tự chọn
xe và phát lệnh. Người CẦN xe và người CÓ xe là hai vai; gộp lại thì không ai trả lời được câu "ai
quyết chiếc xe này đi chuyến này".

BA RANH GIỚI tệp này canh:

  1. CỬA CHẶN DUY NHẤT là dự toán tour đã duyệt. Chủ tịch quyết 11/10: chi phí xe đã nằm trong dự
     toán, nên KHÔNG thêm chữ ký nào nữa. Thêm một mắt duyệt là bắt mỗi chuyến chờ thêm một người.
  2. Đề nghị KHÔNG chọn xe, và tạo đề nghị KHÔNG tự sinh lệnh. Tự sinh thì chuỗi ba mắt rút lại
     thành một mắt và chữ "Giám đốc đội xe lập lệnh" mất nghĩa.
  3. Từ chối và huỷ BẮT BUỘC ghi lý do — vì lý do ấy chính là câu trả lời cho báo cáo đối chiếu
     tour/lượt xe tháng sau: vì sao chuyến này phải thuê xe ngoài.

VÀ MỘT ĐIỀU VỀ CHỖ HỞ CỐ Ý: `de_nghi_id` trên lệnh để RỖNG ĐƯỢC. Bắt buộc ngay thì mười tệp phép
kiểm của các làn khác đỏ, và Điều hành chưa kịp chuyển sang dùng cửa đề nghị. Chỗ hở ấy ĐẾM ĐƯỢC
bằng `lenh_khong_qua_de_nghi()`, cùng khuôn với `misa.thieu_tai_khoan()`. Một chỗ hở không đếm được
là một chỗ hở sẽ ở lại mãi.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_dl1.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
import inspect
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.core import Tour, User
from app.models.de_nghi_xe import DeNghiXe, DU_TOAN_DA_DUYET
from app.models.hr import DispatchOrder
from app.services import de_nghi_xe as DN


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _u(db, vai):
    """Tài khoản của một vai. Bản gieo demo không có mọi vai — lùi về `chutich` khi thiếu.

    Lùi về Chủ tịch là đúng về mặt quyền (vai nền có trong cả ba nhóm DE_NGHI/TU_CHOI/XEM), nên
    phép kiểm vẫn đo đúng LUẬT; phần "ai được bấm" do test_hai_nhom_ghi_hep_hon đo trên danh sách.
    """
    u = db.execute(select(User).where(User.role == vai)).scalars().first()
    return u or db.execute(select(User).where(User.role == "chutich")).scalars().first()


def _tour(db, status="da_duyet"):
    t = db.execute(select(Tour).order_by(Tour.id)).scalars().first()
    t.status = status
    if t.start_date is None:
        t.start_date = date.today() + timedelta(days=20)
    if t.end_date is None or t.end_date < t.start_date:
        t.end_date = t.start_date + timedelta(days=2)
    db.flush()
    return t


# ─────────────────────────────── Ranh giới 1: cửa chặn là dự toán đã duyệt
def test_du_toan_chua_duyet_thi_TU_CHOI_va_noi_ro_phai_lam_gi(_startup):
    with SessionLocal() as db:
        t = _tour(db, "cho_duyet")
        u = _u(db, "tp_dh")
        with pytest.raises(ValueError) as ex:
            DN.de_nghi(db, u, t.id, so_khach=30)
        msg = str(ex.value)
        assert "chưa được duyệt" in msg and "cho_duyet" in msg
        assert "duyệt dự toán trước" in msg, "lời chặn phải nói người dùng làm gì tiếp"
        db.rollback()


def test_moi_trang_thai_SAU_duyet_deu_de_nghi_duoc(_startup):
    """Không chỉ 'da_duyet': chuyến đã kết thúc hoặc đã đóng số thì dự toán cũng đã duyệt rồi."""
    with SessionLocal() as db:
        u = _u(db, "tp_dh")
        for st in DU_TOAN_DA_DUYET:
            t = _tour(db, st)
            d = DN.de_nghi(db, u, t.id, so_khach=30)
            assert d.trang_thai == "cho_lap_lenh", f"trạng thái {st} lẽ ra đề nghị được"
            db.rollback()


def test_khong_them_mat_duyet_nao_vao_chuoi():
    """Chủ tịch quyết 11/10: dự toán tour đã duyệt là ĐỦ, không thêm chữ ký."""
    from app.models.de_nghi_xe import TRANG_THAI
    assert "cho_duyet" not in TRANG_THAI and "cho_ky" not in TRANG_THAI, \
        "bảng trạng thái mọc một mắt duyệt — Chủ tịch đã quyết là không thêm chữ ký nào nữa"
    assert set(TRANG_THAI) == {"cho_lap_lenh", "da_lap_lenh", "tu_choi", "huy"}


# ─────────────────────────────── Ranh giới 2: không chọn xe, không tự lập lệnh
def test_bang_de_nghi_KHONG_co_cot_xe():
    """Chọn xe là việc của Giám đốc đội xe — chỉ người ấy biết xe nào đang ở đâu."""
    cot = {c.name for c in DeNghiXe.__table__.columns}
    assert not any("vehicle" in c or c == "bien_so" or c == "xe_id" for c in cot), \
        f"bảng đề nghị mọc cột xe: {sorted(cot)}"


def test_tao_de_nghi_KHONG_tu_sinh_lenh(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        truoc = len(db.execute(select(DispatchOrder)).scalars().all())
        DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        sau = len(db.execute(select(DispatchOrder)).scalars().all())
        assert sau == truoc, "tạo đề nghị mà tự sinh lệnh — chuỗi ba mắt rút thành một mắt"
        db.rollback()


def test_thieu_so_khach_thi_TU_CHOI(_startup):
    """Số khách là đầu vào của bộ gợi ý điều xe: thiếu nó thì nó đề xuất xe 29 chỗ cho đoàn 40."""
    with SessionLocal() as db:
        t = _tour(db)
        with pytest.raises(ValueError) as ex:
            DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=0)
        assert "số khách" in str(ex.value) and "số ghế" in str(ex.value)
        db.rollback()


# ─────────────────────────────── Ranh giới 3: lý do bắt buộc
def test_tu_choi_khong_ly_do_thi_TU_CHOI(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        for xau in ("", "   "):
            with pytest.raises(ValueError) as ex:
                DN.tu_choi(db, _u(db, "gd_doi_xe"), d.id, xau)
            assert "lý do" in str(ex.value)
        db.rollback()


def test_huy_khong_ly_do_thi_TU_CHOI(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        with pytest.raises(ValueError):
            DN.huy(db, _u(db, "tp_dh"), d.id, "")
        db.rollback()


def test_tu_choi_roi_thi_khong_doi_duoc_nua(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        DN.tu_choi(db, _u(db, "gd_doi_xe"), d.id, "hết xe, cả 11 xe đều bận")
        assert d.trang_thai == "tu_choi" and d.ly_do.startswith("hết xe")
        with pytest.raises(ValueError) as ex:
            DN.huy(db, _u(db, "tp_dh"), d.id, "đổi ý")
        assert "CHỜ LẬP LỆNH" in str(ex.value)
        db.rollback()


def test_khong_lap_lenh_cho_de_nghi_da_tu_choi(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        DN.tu_choi(db, _u(db, "gd_doi_xe"), d.id, "hết xe")
        with pytest.raises(ValueError) as ex:
            DN.danh_dau_da_lap_lenh(db, d.id, 1)
        assert "đã từ chối" in str(ex.value)
        db.rollback()


def test_mot_de_nghi_dan_toi_NHIEU_lenh_duoc(_startup):
    """Tour 50 khách cần hai xe — đánh dấu lần thứ hai không được báo lỗi."""
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=50, so_xe_can=2)
        DN.danh_dau_da_lap_lenh(db, d.id, 1)
        DN.danh_dau_da_lap_lenh(db, d.id, 2)      # không được nổ
        assert d.trang_thai == "da_lap_lenh"
        db.rollback()


# ─────────────────────────────── Quyền: hai nhóm ghi hẹp hơn nhóm xem
def test_hai_nhom_ghi_hep_hon_that_su_nhom_xem_va_khac_nhau_dung_cho():
    from app.api.v1 import de_nghi_xe as API
    assert set(API.DE_NGHI) < set(API.XEM)
    assert set(API.TU_CHOI) < set(API.XEM)
    assert "gd_doi_xe" in API.TU_CHOI and "gd_doi_xe" not in API.DE_NGHI, \
        "đội xe từ chối, không đề nghị — họ là người CÓ xe"
    assert "nv_dh" in API.DE_NGHI and "nv_dh" not in API.TU_CHOI, \
        "Điều hành đề nghị, không tự từ chối việc của mình"


def test_XEM_suy_tu_MENU_ROLES_chu_khong_go_lai():
    """Bài học LG1: một phép suy có TÊN, nhiều nơi cùng đọc.

    Bản đầu em gõ tay danh sách này và nó LỆCH thật — thừa `ptgd_doan` và `ketoan`, hai vai không
    có trong `MENU_ROLES` của màn hình. Khi ấy họ gọi được cửa mà không mở được trang.
    """
    from app.api.v1 import de_nghi_xe as API
    from app.services.access import MENU_ROLES
    assert API.XEM == MENU_ROLES["/lenh-dieu-xe"]
    src = inspect.getsource(API)
    assert 'XEM = MENU_ROLES["/lenh-dieu-xe"]' in src, "đang gõ lại danh sách thay vì suy từ bảng"


# ─────────────────────────────── Chỗ hở cố ý, và nó đếm được
def test_cho_ho_de_nghi_khong_bat_buoc_DEM_DUOC(_startup):
    with SessionLocal() as db:
        kq = DN.lenh_khong_qua_de_nghi(db)
        for k in ("tong_lenh", "khong_qua_de_nghi", "ty_le", "ghi_chu"):
            assert k in kq
        assert "về 0" in kq["ghi_chu"], "phải nói ra điều kiện để siết thành bắt buộc"
        db.rollback()


def test_lenh_co_de_nghi_thi_KHONG_bi_dem_la_thieu(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=30)
        truoc = DN.lenh_khong_qua_de_nghi(db)["khong_qua_de_nghi"]
        from app.models.hr import Vehicle
        v = db.execute(select(Vehicle)).scalars().first()
        e = db.execute(select(DispatchOrder)).scalars().first()
        db.add(DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=(e.driver_id if e else 1),
                             de_nghi_id=d.id, date_from=t.start_date, date_to=t.end_date))
        db.flush()
        assert DN.lenh_khong_qua_de_nghi(db)["khong_qua_de_nghi"] == truoc, \
            "lệnh CÓ đề nghị mà vẫn bị đếm là thiếu"
        db.rollback()


def test_lenh_khong_de_nghi_thi_BI_dem(_startup):
    with SessionLocal() as db:
        t = _tour(db)
        truoc = DN.lenh_khong_qua_de_nghi(db)["khong_qua_de_nghi"]
        from app.models.hr import Vehicle
        v = db.execute(select(Vehicle)).scalars().first()
        e = db.execute(select(DispatchOrder)).scalars().first()
        db.add(DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=(e.driver_id if e else 1),
                             de_nghi_id=None, date_from=t.start_date, date_to=t.end_date))
        db.flush()
        assert DN.lenh_khong_qua_de_nghi(db)["khong_qua_de_nghi"] == truoc + 1
        db.rollback()


# ─────────────────────────────── Bảng phải rỗng khi mới dựng
def test_bang_de_nghi_bat_dau_RONG(_startup):
    """Máy nạp sẵn một đề nghị là máy tự đề nghị hộ — rồi đội xe lập lệnh cho chuyến chưa ai hỏi."""
    with SessionLocal() as db:
        assert db.execute(select(DeNghiXe)).scalars().first() is None
        from app.services.ks_cua_nhap import CUA_TAY
        assert "fleet_vehicle_requests" in CUA_TAY


# ─────────────────────────────── Cửa chọn chuyến: chỉ bày ra thứ bấm được
def test_cua_chon_chuyen_CHI_bay_chuyen_da_duyet_du_toan(_startup):
    """Cửa bày ra chuyến chưa duyệt là cửa dạy người dùng rằng màn hình này hay báo lỗi."""
    with SessionLocal() as db:
        t = _tour(db, "cho_duyet")
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        assert t.id not in [x["id"] for x in ds], "chuyến chưa duyệt dự toán vẫn được bày ra"
        t.status = "da_duyet"; db.flush()
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        assert t.id in [x["id"] for x in ds]
        db.rollback()


def test_cua_chon_chuyen_KHONG_mang_mot_con_so_tien_nao(_startup):
    """Cùng lý do đã ghi cho `/fleet/de-lap-lenh`: mở cả cụm tour để lấy bốn cột lịch trình là nới
    hàng rào rộng hơn nhiều lần việc cần làm."""
    with SessionLocal() as db:
        t = _tour(db)
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        assert ds, "phải có ít nhất chuyến vừa dựng"
        cho_phep = {"id", "code", "name", "start_date", "end_date", "planned_pax", "status",
                    "da_co_de_nghi"}
        assert set(ds[0]) == cho_phep, f"cửa trả thêm cột ngoài danh sách đã chốt: {set(ds[0]) - cho_phep}"
        db.rollback()


def test_cua_chon_chuyen_DEM_de_nghi_dang_mo_nhung_KHONG_chan(_startup):
    """Một chuyến cần thêm xe thì đề nghị thêm — chỉ nói ra để không ai gửi trùng vì tưởng lần trước
    chưa gửi được."""
    with SessionLocal() as db:
        t = _tour(db)
        u = _u(db, "tp_dh")
        DN.de_nghi(db, u, t.id, so_khach=40)
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        dong = [x for x in ds if x["id"] == t.id][0]
        assert dong["da_co_de_nghi"] == 1
        DN.de_nghi(db, u, t.id, so_khach=40)      # vẫn gửi được: chuyến cần xe thứ hai
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        assert [x for x in ds if x["id"] == t.id][0]["da_co_de_nghi"] == 2
        db.rollback()


def test_de_nghi_da_tu_choi_KHONG_con_tinh_la_dang_mo(_startup):
    """Đội xe từ chối rồi mà cửa vẫn báo 'đã có đề nghị' thì Điều hành tưởng việc đang chạy."""
    with SessionLocal() as db:
        t = _tour(db)
        d = DN.de_nghi(db, _u(db, "tp_dh"), t.id, so_khach=40)
        DN.tu_choi(db, _u(db, "gd_doi_xe"), d.id, "Cả 11 xe nhà đều có lệnh ngày đó")
        ds = DN.tour_cho_de_nghi(db, t.start_date, t.end_date)
        assert [x for x in ds if x["id"] == t.id][0]["da_co_de_nghi"] == 0
        db.rollback()


def test_man_hinh_KHONG_phai_go_lai_danh_sach_vai(_startup):
    """Hai câu trả lời về quyền phải đến TỪ MÁY CHỦ.

    Nếu `page.tsx` tự viết danh sách vai để quyết hiện nút nào, thì ngày nào bảng vai đổi, người
    ĐƯỢC phép lại không thấy nút — và cái không thấy thì không ai báo lỗi.

    (Phần "XEM phải suy từ MENU_ROLES" đã có phép kiểm riêng ở
    `test_XEM_suy_tu_MENU_ROLES_chu_khong_go_lai` — kiểm ngược cho thấy một dòng `is` thêm ở đây
    KHÔNG đo gì mới: `tuple()` gọi lên một tuple trả về chính nó, nên dòng ấy xanh cả khi bị sửa.)
    """
    from app.api.v1 import de_nghi_xe as API
    src = inspect.getsource(API.meta)
    assert "toi_duoc_de_nghi" in src, "cửa meta phải trả lời 'tôi đề nghị được không'"
    assert "toi_duoc_tu_choi" in src, "cửa meta phải trả lời 'tôi từ chối được không'"
