"""CHS-1 · Một chủ hồ sơ quyết toán — hàng rào, Chủ tịch quyết 25/9/2026, câu 4.

Câu hỏi 4 gửi Chủ tịch: *ai lập quyết toán tour đoàn?* — trả lời: **Sale Admin**. Và câu hỏi đi
kèm *ai bấm đóng số?* — trả lời: **chủ hồ sơ, ai soạn người ấy đóng**.

═══════════════════════════════════════════════════════════════════════════════════════════════
LẦN THAY ĐỔI NÀY LÀ MỘT LẦN NỚI, NÊN PHẢI CÓ PHÉP THỬ CANH
═══════════════════════════════════════════════════════════════════════════════════════════════
Trước hôm nay, cổng quyết toán so `u.id != t.operator_id` ở năm chỗ. Nới một cổng như thế là việc
dễ làm hỏng theo kiểu không ai thấy: chỉ cần thêm `or u.role == "sales_admin"` là xong việc trước
mắt — và từ lúc ấy BẤT KỲ Sale Admin nào cũng soạn được quyết toán của BẤT KỲ chuyến nào, kể cả
tour lẻ, kể cả chuyến của người khác. Con số quyết toán mất tên người chịu trách nhiệm, mà bảng
phân quyền vẫn cân.

Nên luật mới giữ nguyên "đúng một người", và những phép thử dưới đây canh đúng chỗ ấy:

  · vẫn đúng MỘT người — người thứ hai bị từ chối, kể cả khi đúng vai `sales_admin`;
  · tour LẺ không đổi gì — mặc định mảng Đoàn không được tràn sang;
  · dịch vụ lẻ (`non_package`) không đổi gì — `segments.mang_of` trả rỗng cho nó;
  · soạn và đóng là MỘT người — không có chuyện Sale Admin soạn rồi điều hành đóng;
  · đổi tham số KHÔNG lấy được hồ sơ đang soạn dở khỏi tay người đang soạn;
  · bàn giao KHÔNG chuyển thưởng chuyến.
"""
import datetime as dt
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import Gate as _GateDeps
from app.db.session import Base
from app.models.core import Param, Tour, User
from app.services import chu_ho_so as CHS
from app.services import rules as R
from app.services import settlement as ST
from app.services import tours as T

HOM_NAY = dt.date.today()

# Hai lớp Gate khác nhau trong kho: `api/deps.Gate` và `settlement.Gate` — cùng một nghĩa, cùng mã
# 422, nhưng là hai lớp. Bắt một lớp thôi thì phép thử xanh vì một lý do sai (ngoại lệ lọt ra
# ngoài pytest.raises trông y hệt "cổng đã chặn" khi nhìn vào bảng kết quả).
Gate = (_GateDeps, ST.Gate)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("nvdh", "nv_dh"), ("nvdh2", "nv_dh"), ("tpdh", "tp_dh"),
                     ("sadmin", "sales_admin"), ("sadmin2", "sales_admin"),
                     ("nvkd", "nv_kd"), ("ketoan", "ketoan"), ("ct", "chutich")):
        s.add(User(username=ten, full_name=ten, role=vai, password_hash="x"))
    s.commit()
    R.clear_param_cache()
    return s


def _u(db, ten):
    return db.execute(select(User).where(User.username == ten)).scalars().first()


def _dat_tham_so(db, gia_tri):
    db.add(Param(key="chu_ho_so_doan", value=gia_tri, label="Chủ hồ sơ quyết toán mảng Đoàn",
                 unit="tài khoản", effective_from=date(2026, 1, 1), status="active"))
    db.commit()
    R.clear_param_cache()
    CHS.quen_nho(db)          # phiên này đã hỏi tham số rồi; phép thử đổi giữa chừng thì phải quên


def _tour(db, ma="MICE-2610-01", loai="doan_noi_dia", trang_thai="ket_thuc"):
    t = Tour(code=ma, name=ma, tour_type=loai, start_date=HOM_NAY - dt.timedelta(days=5),
             end_date=HOM_NAY - dt.timedelta(days=2), operator_id=_u(db, "nvdh").id,
             status=trang_thai, price_per_pax=10_000_000.0, fixed_cost=20_000_000.0,
             var_cost_per_pax=6_000_000.0, planned_pax=10, seats_open=10, rest_stops="x")
    db.add(t); db.commit(); db.refresh(t)
    return t


DONG = {"description": "Xe 29 chỗ", "service_type": "VEHICLE", "cost_kind": "co_dinh",
        "supplier_name": "Nhà xe A", "unit_price": 5_000_000.0, "qty": 1, "coef": 1}


# ───────────────────── bậc 3: không khai gì thì luật cũ nguyên vẹn ─────────────────────

def test_chs1_chua_khai_tham_so_thi_van_la_nguoi_dieu_hanh():
    """Đường rơi cuối cùng. Đây là trạng thái của hệ thống ngay sau khi nâng cấp — chưa ai khai
    tham số, chưa chuyến nào có chủ chỉ định — và nó phải giống hệt luật cũ."""
    db = _db(); t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id
    ST.add_line(db, _u(db, "nvdh"), t, dict(DONG))
    with pytest.raises(Gate):
        ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))


def test_chs1_tour_le_khong_di_theo_mac_dinh_doan():
    """Tham số mảng Đoàn KHÔNG được tràn sang tour lẻ.

    Chủ tịch nói "tour đoàn thì mặc định về Sale Admin". Tour lẻ do Điều hành tạo lịch khởi hành
    và tự quyết toán — ranh giới ấy đã chốt ngày 25/9 ở phần ba con số, không nới thêm ở đây."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db, ma="LE-2610-01", loai="le_noi_dia")
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id
    with pytest.raises(Gate):
        ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))


def test_chs1_dich_vu_le_khong_di_theo_mac_dinh_doan():
    """`non_package` không thuộc mảng nào — `segments.mang_of` trả rỗng, nên bậc 2 không chạm tới.

    Dịch vụ lẻ dùng CHUNG bảng `tours` với chuyến đoàn, nên một luật khai theo bảng thay vì theo
    mảng sẽ lặng lẽ vơ cả nó vào. Đây đúng là cách câu 7 ngày 25/9 đã hở một lần rồi."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db, ma="DVL-2610-01", loai="non_package")
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id


# ───────────────────── bậc 2: mặc định mảng Đoàn ─────────────────────

def test_chs1_tour_doan_ve_sale_admin_khi_da_khai_tham_so():
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "sadmin").id
    ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))


def test_chs1_van_dung_MOT_nguoi_nguoi_dieu_hanh_bi_tu_choi():
    """Điểm quan trọng nhất của cả tệp: nới KHÔNG phải là mở cho cả hai.

    Khi hồ sơ đã về Sale Admin thì người điều hành chuyến KHÔNG còn soạn được. Nếu cả hai cùng
    soạn được thì con số lại không có tên một người — đúng thứ cổng 6 sinh ra để chặn."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    with pytest.raises(Gate) as e:
        ST.add_line(db, _u(db, "nvdh"), t, dict(DONG))
    assert "Một chủ hồ sơ" in str(e.value.detail["message"])


def test_chs1_sale_admin_khac_khong_soan_duoc():
    """Vai `sales_admin` không phải là chìa khoá — chỉ ĐÚNG tài khoản đã khai mới là chủ hồ sơ."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    with pytest.raises(Gate):
        ST.add_line(db, _u(db, "sadmin2"), t, dict(DONG))


def test_chs1_mã_MICE_cung_la_mang_doan():
    """Hai quy tắc nhận mảng Đoàn (loại chuyến, hoặc mã bắt đầu bằng MICE) — lấy HỢP, như
    `segments` đã chốt ngày 07/9. Một tour MICE quên đặt loại chuyến vẫn phải về Sale Admin."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db, ma="MICE-2610-99", loai="le_noi_dia")
    assert CHS.chu_ho_so(db, t) == _u(db, "sadmin").id


# ───────────────────── tham số sai thì NÓI RA, không im ─────────────────────

def test_chs1_tham_so_tro_toi_tai_khoan_khong_co_thi_roi_ve_dieu_hanh_va_noi_ly_do():
    db = _db(); _dat_tham_so(db, "khong_co_ai")
    t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id
    nguoi, ly_do = CHS.nguoi_giu_ho_so_doan(db)
    assert nguoi is None and "không khớp tài khoản" in ly_do
    assert CHS.xem(db, t)["canh_bao_tham_so"]


def test_chs1_tham_so_khai_hai_nguoi_thi_tu_choi_doan_thay():
    """"Một chủ hồ sơ" mà tham số khai hai người là câu hỏi cấu hình chưa trả lời xong. Lấy bừa
    người đầu danh sách là đoán hộ một trách nhiệm."""
    db = _db(); _dat_tham_so(db, "sadmin, sadmin2")
    t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id
    assert "MỘT chủ" in CHS.nguoi_giu_ho_so_doan(db)[1]


def test_chs1_tham_so_tro_toi_vai_khong_duoc_giu_ho_so():
    db = _db(); _dat_tham_so(db, "nvkd")
    t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id
    assert "không\nđược giữ" in CHS.nguoi_giu_ho_so_doan(db)[1].replace(" ", "\n", 100) or \
           "không được giữ" in CHS.nguoi_giu_ho_so_doan(db)[1]


def test_chs1_tai_khoan_da_nghi_thi_khong_con_giu_ho_so():
    db = _db(); _dat_tham_so(db, "sadmin")
    u = _u(db, "sadmin"); u.active = False; db.commit()
    R.clear_param_cache(); CHS.quen_nho(db)
    t = _tour(db)
    assert CHS.chu_ho_so(db, t) == _u(db, "nvdh").id


# ───────────────────── đóng dấu ở lần ghi đầu ─────────────────────

def test_chs1_ghi_dong_dau_tien_dong_dau_ten_nguoi_ghi_len_chuyen():
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    assert t.chu_ho_so_id is None
    ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))
    db.refresh(t)
    assert t.chu_ho_so_id == _u(db, "sadmin").id


def test_chs1_doi_tham_so_khong_lay_duoc_ho_so_dang_soan_do():
    """Đây là hàng rào của rủi ro em đã nói ra trước khi Chủ tịch chọn cách làm này.

    Bậc 2 tính SỐNG, nên đổi một dòng tham số là chuyển chủ hàng trăm chuyến cùng lúc. Với chuyến
    chưa ai chạm vào thì không mất gì. Với chuyến đang soạn dở thì mất: người đang gõ bỗng nhiên
    bị từ chối ở giữa chừng, và hồ sơ của họ nằm trong tay người khác. Dấu đóng ở lần ghi đầu là
    thứ chặn đúng chỗ đó."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))

    _dat_tham_so(db, "sadmin2")           # đổi người giữ hồ sơ toàn mảng Đoàn
    db.refresh(t)
    assert CHS.chu_ho_so(db, t) == _u(db, "sadmin").id, "hồ sơ đang soạn dở bị lấy khỏi tay người soạn"
    ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))
    with pytest.raises(Gate):
        ST.add_line(db, _u(db, "sadmin2"), t, dict(DONG))


# ───────────────────── soạn và đóng là MỘT người ─────────────────────

class _DongSo:
    actual_revenue = 100_000_000.0
    actual_cost = 0.0
    promo_value = 0.0
    note = ""


def test_chs1_ai_soan_nguoi_ay_dong_dieu_hanh_khong_dong_thay():
    """Chủ tịch chọn "chủ hồ sơ — ai soạn người ấy đóng". Nên cổng đóng số đi theo cùng một hàm
    với cổng soạn: hai cổng đọc hai luật khác nhau là kiểu lệch không ai thấy cho tới lúc có
    người bấm."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    ST.add_line(db, _u(db, "sadmin"), t, dict(DONG))
    with pytest.raises(Gate) as e:
        T.close(db, _u(db, "nvdh"), t, _DongSo(), "")
    assert "Một chủ hồ sơ" in str(e.value.detail["message"])
    T.close(db, _u(db, "sadmin"), t, _DongSo(), "")
    db.refresh(t)
    assert t.status == "da_dong_so"


def test_chs1_bang_nut_va_cong_noi_cung_mot_cau():
    """Nút hiện ra mà bấm vào thì 422 là cách nhanh nhất để người dùng thôi tin vào màn hình."""
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    assert "close" in T.allowed_actions(db, t, _u(db, "sadmin"))
    assert "close" not in T.allowed_actions(db, t, _u(db, "nvdh"))
    assert "edit_settlement" in T.allowed_actions(db, t, _u(db, "sadmin"))
    assert "edit_settlement" not in T.allowed_actions(db, t, _u(db, "nvdh"))


# ───────────────────── bàn giao ─────────────────────

LY_DO = "Sale Admin nghỉ thai sản, hồ sơ chuyển cho điều hành chuyến gom nốt chứng từ"


def test_chs1_ban_giao_doi_chu_ho_so_va_khong_doi_thuong_chuyen():
    db = _db(); _dat_tham_so(db, "sadmin")
    t = _tour(db)
    op_cu = t.operator_id
    CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "nvdh2"), LY_DO)
    db.refresh(t)
    assert t.chu_ho_so_id == _u(db, "nvdh2").id
    assert t.operator_id == op_cu, "bàn giao hồ sơ đã chuyển luôn thưởng chuyến"
    ST.add_line(db, _u(db, "nvdh2"), t, dict(DONG))


def test_chs1_sale_admin_khong_tu_lay_ho_so_ve_tay_minh():
    """Trao đi được, LẤY VỀ thì không. Cho người nhận tự lấy là bỏ luôn ý nghĩa của bàn giao."""
    db = _db()
    t = _tour(db)                       # chưa khai tham số → chủ hồ sơ là nvdh
    with pytest.raises(Gate) as e:
        CHS.giao_ho_so(db, _u(db, "sadmin"), t, _u(db, "sadmin"), LY_DO)
    assert "Trưởng phòng Điều hành" in str(e.value.detail["message"])


def test_chs1_chu_ho_so_hien_tai_trao_di_duoc():
    db = _db(); t = _tour(db)
    CHS.giao_ho_so(db, _u(db, "nvdh"), t, _u(db, "sadmin"), LY_DO)
    db.refresh(t)
    assert t.chu_ho_so_id == _u(db, "sadmin").id


def test_chs1_khong_giao_cho_vai_khong_duoc_giu_ho_so():
    """Khối Kinh doanh không giữ hồ sơ quyết toán. Đây là cùng một ranh giới với câu 7 ngày 25/9:
    quyết toán là bảng "mình mua của ai, bao nhiêu" — số của bên đặt dịch vụ, không phải bên bán."""
    db = _db(); t = _tour(db)
    with pytest.raises(Gate) as e:
        CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "nvkd"), LY_DO)
    assert "nv_kd" in str(e.value.detail["message"])


def test_chs1_ban_giao_phai_co_ly_do():
    db = _db(); t = _tour(db)
    with pytest.raises(Gate) as e:
        CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "sadmin"), "chuyển")
    assert "lý do" in str(e.value.detail["message"])


def test_chs1_khong_ban_giao_ho_so_da_dong_so():
    db = _db(); t = _tour(db, trang_thai="da_dong_so")
    with pytest.raises(Gate) as e:
        CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "sadmin"), LY_DO)
    assert "đóng số" in str(e.value.detail["message"])


def test_chs1_ban_giao_de_lai_vet_trong_nhat_ky_va_dong_thoi_gian():
    from app.models.core import AuditLog
    db = _db(); t = _tour(db)
    CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "sadmin"), LY_DO)
    vet = db.execute(select(AuditLog).where(AuditLog.action == "giao_ho_so_quyet_toan")).scalars().all()
    assert len(vet) == 1
    assert "thuong_chuyen_van_thuoc" in (vet[0].after or {})


# ───────────────────── màn hình đọc được VÌ SAO là người này ─────────────────────

def test_chs1_man_hinh_doc_duoc_nguon_cua_chu_ho_so():
    """Một cái tên trơ trọi thì người đọc không biết sửa ở đâu: chỉ định riêng của chuyến và tham
    số mảng Đoàn sửa ở hai chỗ khác hẳn nhau."""
    db = _db(); t = _tour(db)
    assert CHS.xem(db, t)["nguon"] == "dieu_hanh_chuyen"
    _dat_tham_so(db, "sadmin"); db.refresh(t)
    assert CHS.xem(db, t)["nguon"] == "mac_dinh_doan"
    CHS.giao_ho_so(db, _u(db, "tpdh"), t, _u(db, "nvdh2"), LY_DO); db.refresh(t)
    v = CHS.xem(db, t)
    assert v["nguon"] == "chi_dinh" and v["chu_ho_so_ten"] == "nvdh2"
    assert v["thuong_chuyen_van_thuoc"] == "nvdh"
