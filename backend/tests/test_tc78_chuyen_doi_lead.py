"""TC-78 · CHUYỂN ĐỔI & PHỐI HỢP SALES — nhóm 2.6.

NĂM CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — đều là loại nhìn màn hình KHÔNG phát hiện được:

 1. "ĐÃ CHỐT NHƯNG KHÔNG RÕ NGÀY" BỊ NHÉT VÀO MỘT MỐC. Phép đối chiếu theo số điện thoại biết
    lead đã chốt mà không biết chốt lúc nào. Nhét vào ">90 ngày" cho gọn là bịa; xếp vào "≤30"
    cho đẹp lại càng bịa. Ngăn riêng, và nó phải cộng đủ vào tổng.

 2. LEAD CÒN ĐANG CHĂM SÓC BỊ GỘP VỚI LEAD ĐÃ MẤT. Gộp là kết luận thay cho tương lai của những
    lead còn mở — và nó làm tỷ lệ mất trông cao hơn thật.

 3. ĐỊNH NGHĨA "QUÁ HẠN" BỊ CHÉP SANG MỘT BẢN THỨ HAI. Định nghĩa ấy đã được dọn về một mối ngày
    18/9/2026 để chỗ đếm và chỗ đánh dấu dùng chung một luật. `test_dung_lai_may_han_cua_leads`
    đọc mã bằng cây cú pháp và đòi tệp này gọi `services/leads`, không tự định nghĩa lại.

 4. CỬA BÀN GIAO GHI NHẬT KÝ SAU KHI ĐÃ SỬA. Đọc trạng thái cũ sau khi đã gán giá trị mới thì cột
    "before" ghi lại đúng trạng thái SAU — nhật ký nói dối còn tệ hơn không có nhật ký. Lỗi này đã
    bắt được một lần ở cửa gộp tài khoản, nên ở đây có phép thử riêng.

 5. THỜI ĐIỂM "BÂY GIỜ" MỞ RA CỬA HTTP. Cho người gọi tự chọn thời điểm là cho họ chọn một mốc mà
    ở đó mình không quá hạn.
"""
import ast
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.models.crm import Lead, LeadBanGiao
from app.services import chuyen_doi_lead as CD

GOC = Path(__file__).resolve().parents[1]
T0 = dt.datetime(2026, 9, 1, 8, 0)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e, future=True)()
    from app.services import rules as R
    R.set_param(db, "lead_han_xu_ly_gio", "24") if hasattr(R, "set_param") else None
    return db


def _u(db, ten, vai="nv_kd"):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _lead(db, sdt, **kw):
    d = dict(phone=sdt, name="L" + sdt, channel="facebook", lead_month="2026-09",
             received_at=T0, status="moi")
    d.update(kw)
    l = Lead(**d)
    db.add(l); db.commit()
    return l


# ═════════════════════════ 2.6.1 — MỐC NGÀY ═════════════════════════

def test_xep_dung_moc_theo_so_ngay_tu_vao_so_den_chot():
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=T0 + dt.timedelta(days=10))
    _lead(db, "0900000002", booking_id=2, converted_at=T0 + dt.timedelta(days=45))
    _lead(db, "0900000003", booking_id=3, converted_at=T0 + dt.timedelta(days=80))
    _lead(db, "0900000004", booking_id=4, converted_at=T0 + dt.timedelta(days=200))
    n = CD.chuyen_doi_theo_moc(db, "2026-09")["theo_ngan"]
    assert (n["trong_30"], n["trong_60"], n["trong_90"], n["tren_90"]) == (1, 1, 1, 1)


def test_dung_moc_30_la_BAO_GOM_ngay_thu_30():
    """Ranh giới nằm ở đâu là thứ hai người đọc hiểu hai kiểu nếu không ai ghim. ≤30 là trong 30."""
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=T0 + dt.timedelta(days=30))
    _lead(db, "0900000002", booking_id=2, converted_at=T0 + dt.timedelta(days=31))
    n = CD.chuyen_doi_theo_moc(db, "2026-09")["theo_ngan"]
    assert (n["trong_30"], n["trong_60"]) == (1, 1)


def test_da_chot_khong_ro_ngay_KHONG_bi_nhet_vao_moc_nao():
    """Chỗ nguy hiểm số 1 ở đầu tệp."""
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=None)      # biết đã chốt, không biết lúc nào
    n = CD.chuyen_doi_theo_moc(db, "2026-09")["theo_ngan"]
    assert n["da_chot_khong_ro_ngay"] == 1
    assert n["trong_30"] == n["trong_60"] == n["trong_90"] == n["tren_90"] == 0


def test_chot_truoc_ngay_vao_so_thi_vao_ngan_khong_ro_chu_khong_am():
    """Dòng nạp ngược ngày. Không sửa hộ, không đoán — để nó hiện ra và có người đi soát."""
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=T0 - dt.timedelta(days=5))
    assert CD.chuyen_doi_theo_moc(db, "2026-09")["theo_ngan"]["da_chot_khong_ro_ngay"] == 1


def test_chua_chot_con_mo_khac_han_da_mat():
    """Chỗ nguy hiểm số 2 ở đầu tệp."""
    db = _db()
    _lead(db, "0900000001", status="dang_cham_soc")
    _lead(db, "0900000002", status="mat", ly_do_mat="gia")
    n = CD.chuyen_doi_theo_moc(db, "2026-09")["theo_ngan"]
    assert n["chua_chot_con_mo"] == 1 and n["da_mat"] == 1


def test_bay_ngan_roi_nhau_va_cong_du():
    """Điều kiện tồn tại của cả bảng: không lead nào ở hai ngăn, không lead nào rơi ra ngoài."""
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=T0 + dt.timedelta(days=5))
    _lead(db, "0900000002", booking_id=2, converted_at=None)
    _lead(db, "0900000003", status="mat", ly_do_mat="lich")
    _lead(db, "0900000004", status="dang_cham_soc")
    kq = CD.chuyen_doi_theo_moc(db, "2026-09")
    assert sum(kq["theo_ngan"].values()) == kq["tong_lead"] == 4


def test_cong_don_la_cong_don_that():
    db = _db()
    _lead(db, "0900000001", booking_id=1, converted_at=T0 + dt.timedelta(days=10))
    _lead(db, "0900000002", booking_id=2, converted_at=T0 + dt.timedelta(days=50))
    _lead(db, "0900000003", booking_id=3, converted_at=T0 + dt.timedelta(days=85))
    c = CD.chuyen_doi_theo_moc(db, "2026-09")["cong_don"]
    assert (c["den_30"], c["den_60"], c["den_90"]) == (1, 2, 3)


def test_chua_doi_chieu_thi_KHONG_XAC_DINH_chu_khong_phai_0_phan_tram():
    """0% đọc là "chạy mà không ra khách"; chưa xác định đọc là "chưa ai so sổ". Hai câu khác hẳn."""
    db = _db()
    _lead(db, "0900000001", status="dang_cham_soc")
    kq = CD.chuyen_doi_theo_moc(db, "2026-09")
    assert kq["ty_le_chot"] is None
    assert kq["da_doi_chieu"] is False
    assert "CHƯA XÁC ĐỊNH" in kq["canh_bao_chua_doi_chieu"]


def test_luon_noi_ro_KHONG_phai_ty_le_chot_chinh_thuc():
    """Hai con số gần giống nhau mà không ai ghi vì sao khác là một buổi họp mất nửa giờ."""
    assert "overview-v1" in CD.chuyen_doi_theo_moc(_db(), "2026-09")["co_so"]


# ═════════════════════════ 2.6.2 — TỒN ĐỌNG ═════════════════════════

def test_dung_lai_may_han_cua_leads_khong_dinh_nghia_lai():
    """Chỗ nguy hiểm số 3 ở đầu tệp. Đọc bằng cây cú pháp, không tìm chuỗi."""
    cay = ast.parse((GOC / "app" / "services" / "chuyen_doi_lead.py").read_text(encoding="utf-8"))
    nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            nhap.update(a.name for a in n.names)
    assert "leads" in nhap, "Phải gọi services/leads, không dựng lại phép tính hạn"
    tu_dinh_nghia = {n.name for n in ast.walk(cay)
                     if isinstance(n, ast.FunctionDef)} & {"qua_han", "han_hieu_luc",
                                                           "han_theo_quy_tac", "da_xu_ly"}
    assert not tu_dinh_nghia, (
        f"Tệp này tự định nghĩa lại {sorted(tu_dinh_nghia)} — định nghĩa quá hạn đã được dọn về "
        "một mối ngày 18/9/2026; chép lại là dựng lại đúng cái vừa dọn xong.")


def test_ngay_vao_so_khong_duoc_rong():
    """Bản đầu của vòng này có hẳn một ngăn "không rõ ngày vào sổ", và phép thử cho nó ĐỎ — vì
    trường hợp ấy không tồn tại: `leads.received_at` là cột NOT NULL.

    Đã gỡ ngăn ấy đi thay vì sửa phép thử cho xanh. Một ngăn cho trường hợp không thể xảy ra làm
    người đọc sau tin rằng nó có thật, rồi viết thêm một tầng xử lý nữa quanh nó — cùng lý lẽ đã
    ghi khi gỡ nhánh `end_date` rỗng ở TC-73.

    Phép thử này canh chính RÀNG BUỘC. Nếu một ngày ai đó nới cột ấy ra, nó gãy ở đây, và người
    nới phải quyết lead không có ngày vào sổ thì rơi vào ngăn nào — thay vì để máy tự đoán.
    """
    assert Lead.__table__.c["received_at"].nullable is False
    assert "khong_ro_ngay_vao_so" not in CD.ton_dong(_db(), bay_gio=T0)["theo_tuoi"]


def test_han_da_hen_thang_luat_chung():
    """Sales đã hứa một ngày cụ thể với khách thì đó mới là lời hứa có thật."""
    db = _db()
    _lead(db, "0900000001", han_xu_ly=(T0 + dt.timedelta(days=30)).date())
    kq = CD.ton_dong(db, bay_gio=T0 + dt.timedelta(days=10))
    r = kq["rows"][0]
    assert r["nguon_han"] == "da_hen"
    assert r["qua_han"] is False, "Quá 24 giờ nhưng chưa tới hạn đã hẹn thì chưa trễ"


def test_dem_qua_han_theo_luat_khi_khong_ai_hen():
    db = _db()
    _lead(db, "0900000001")
    kq = CD.ton_dong(db, bay_gio=T0 + dt.timedelta(days=3))
    assert kq["tong_qua_han"] == 1
    assert kq["rows"][0]["nguon_han"] == "theo_quy_tac"


def test_lead_da_co_nguoi_cham_thi_khong_con_tinh_qua_han():
    db = _db()
    _lead(db, "0900000001", last_contact_at=T0 + dt.timedelta(hours=2))
    assert CD.ton_dong(db, bay_gio=T0 + dt.timedelta(days=5))["tong_qua_han"] == 0


def test_lead_da_chot_hoac_da_mat_khong_nam_trong_ton_dong():
    db = _db()
    _lead(db, "0900000001", status="chot")
    _lead(db, "0900000002", status="mat", ly_do_mat="gia")
    assert CD.ton_dong(db, bay_gio=T0 + dt.timedelta(days=5))["tong_dang_mo"] == 0


def test_danh_sach_nguoi_nhan_di_kem_va_chi_ba_o():
    """Trả từ cửa này chứ không để màn hình đi hỏi /api/v1/users — khai nhóm ấy là cấp CẢ nhóm tài
    khoản cho mọi vai mở được màn hình. Và chỉ ba ô: danh sách tài khoản đầy đủ là một danh sách
    tài khoản."""
    db = _db()
    _u(db, "sale1"); _u(db, "mkt1", "nv_mkt")
    ds = CD.ton_dong(db, bay_gio=T0)["nguoi_nhan"]
    assert [x["tai_khoan"] for x in ds] == ["sale1"], "Chỉ vai Kinh doanh mới nhận được lead"
    assert set(ds[0]) == {"id", "ho_ten", "tai_khoan"}


# ═════════════════════════ 2.6.3 — LÝ DO MẤT ═════════════════════════

def test_dem_theo_ly_do_va_tach_rieng_phan_chua_ghi():
    db = _db()
    _lead(db, "0900000001", status="mat", ly_do_mat="gia")
    _lead(db, "0900000002", status="mat", ly_do_mat="gia")
    _lead(db, "0900000003", status="mat", ly_do_mat="lich")
    _lead(db, "0900000004", status="mat")                       # chưa ai ghi
    kq = CD.ly_do_mat(db, "2026-09")
    assert kq["tong_mat"] == 4
    assert kq["theo_ly_do"][0] == {"ma": "gia", "ten": "Giá cao hơn nơi khác", "so_lead": 2}
    assert kq["chua_ghi_ly_do"]["so_lead"] == 1


def test_tai_cham_soc_dem_theo_so_dien_thoai():
    db = _db()
    _lead(db, "0900000001", status="mat", ly_do_mat="gia")
    _lead(db, "0900000001", status="chot", booking_id=7)         # cùng số, sau đó chốt
    _lead(db, "0900000002", status="mat", ly_do_mat="lich")
    kq = CD.ly_do_mat(db, "2026-09")["tai_cham_soc"]
    assert (kq["so_sdt_quay_lai"], kq["tren_tong_sdt_mat"]) == (1, 2)
    assert "SỐ ĐIỆN THOẠI" in kq["co_so"]


# ═════════════════════════ CỬA BÀN GIAO ═════════════════════════

def test_ban_giao_bat_buoc_ghi_ly_do():
    db = _db()
    boi = _u(db, "tp1", "tp_kd"); moi = _u(db, "sale2")
    l = _lead(db, "0900000001")
    with pytest.raises(ValueError, match="lý do"):
        CD.ban_giao(db, boi, l.id, den_nguoi_id=moi.id, ly_do="")


def test_ban_giao_phai_co_nguoi_moi_hoac_han_moi():
    db = _db()
    boi = _u(db, "tp1", "tp_kd")
    l = _lead(db, "0900000001")
    with pytest.raises(ValueError, match="người nhận mới hoặc hạn mới"):
        CD.ban_giao(db, boi, l.id, ly_do="dọn tồn")


def test_ban_giao_cho_chinh_nguoi_dang_giu_bi_chan():
    db = _db()
    boi = _u(db, "tp1", "tp_kd"); s = _u(db, "sale1")
    l = _lead(db, "0900000001", sales_id=s.id)
    with pytest.raises(ValueError, match="đang ở chính người này"):
        CD.ban_giao(db, boi, l.id, den_nguoi_id=s.id, ly_do="dọn tồn")


def test_ban_giao_cho_tai_khoan_da_khoa_bi_chan():
    db = _db()
    boi = _u(db, "tp1", "tp_kd"); moi = _u(db, "sale2")
    moi.active = False; db.commit()
    l = _lead(db, "0900000001")
    with pytest.raises(ValueError, match="bị khoá"):
        CD.ban_giao(db, boi, l.id, den_nguoi_id=moi.id, ly_do="dọn tồn")


def test_ban_giao_ghi_vao_so_ban_giao_san_co_chu_khong_dung_bang_thu_hai():
    db = _db()
    boi = _u(db, "tp1", "tp_kd"); cu = _u(db, "sale1"); moi = _u(db, "sale2")
    l = _lead(db, "0900000001", sales_id=cu.id)
    CD.ban_giao(db, boi, l.id, den_nguoi_id=moi.id, ly_do="nằm im 60 ngày")
    db.commit()
    ds = db.query(LeadBanGiao).filter(LeadBanGiao.lead_id == l.id).all()
    assert len(ds) == 1
    assert (ds[0].viec, ds[0].tu_nguoi, ds[0].den_nguoi) == ("giao_lai", "sale1", "sale2")
    assert db.get(Lead, l.id).sales_id == moi.id


def test_nhat_ky_ghi_trang_thai_TRUOC_khi_sua():
    """Chỗ nguy hiểm số 4 ở đầu tệp — lỗi này đã bắt được một lần ở cửa gộp tài khoản."""
    db = _db()
    from app.models.core import AuditLog
    boi = _u(db, "tp1", "tp_kd"); cu = _u(db, "sale1"); moi = _u(db, "sale2")
    l = _lead(db, "0900000001", sales_id=cu.id, han_xu_ly=dt.date(2026, 9, 10))
    CD.ban_giao(db, boi, l.id, den_nguoi_id=moi.id, han_moi=dt.date(2026, 9, 20),
                ly_do="đổi người và giãn hạn")
    db.commit()
    nk = db.query(AuditLog).filter(AuditLog.action == "ban_giao_lead").one()
    assert nk.before["nguoi"] == "sale1", "Cột before phải là người CŨ"
    assert nk.before["han"] == "2026-09-10", "Cột before phải là hạn CŨ"
    assert nk.after["nguoi"] == "sale2" and nk.after["han"] == "2026-09-20"


def test_doi_han_trung_han_dang_co_bi_chan():
    db = _db()
    boi = _u(db, "tp1", "tp_kd")
    l = _lead(db, "0900000001", han_xu_ly=dt.date(2026, 9, 10))
    with pytest.raises(ValueError, match="trùng hạn"):
        CD.ban_giao(db, boi, l.id, han_moi=dt.date(2026, 9, 10), ly_do="giãn hạn")


# ═════════════════════════ CỬA GHI LÝ DO ═════════════════════════

def test_ghi_ly_do_chi_dien_cho_TRONG():
    db = _db()
    boi = _u(db, "mkt1", "nv_mkt")
    l = _lead(db, "0900000001", status="mat", ly_do_mat="gia")
    with pytest.raises(ValueError, match="đã có lý do"):
        CD.ghi_ly_do_mat(db, boi, l.id, "lich")


def test_ghi_ly_do_chi_cho_lead_da_danh_dau_mat():
    db = _db()
    boi = _u(db, "mkt1", "nv_mkt")
    l = _lead(db, "0900000001", status="dang_cham_soc")
    with pytest.raises(ValueError, match="đã đánh dấu không chốt"):
        CD.ghi_ly_do_mat(db, boi, l.id, "gia")


def test_ly_do_ngoai_danh_muc_bi_chan():
    db = _db()
    boi = _u(db, "mkt1", "nv_mkt")
    l = _lead(db, "0900000001", status="mat")
    with pytest.raises(ValueError, match="không hợp lệ"):
        CD.ghi_ly_do_mat(db, boi, l.id, "tu_nghi_ra")


def test_ly_do_khac_bat_buoc_ghi_ro():
    """Một ô 'khác' không bắt ghi rõ sẽ thành nơi chứa mọi thứ không ai phân loại nữa."""
    db = _db()
    boi = _u(db, "mkt1", "nv_mkt")
    l = _lead(db, "0900000001", status="mat")
    with pytest.raises(ValueError, match="ghi rõ"):
        CD.ghi_ly_do_mat(db, boi, l.id, "khac", "")
    CD.ghi_ly_do_mat(db, boi, l.id, "khac", "khách chuyển công tác")
    assert db.get(Lead, l.id).ly_do_mat == "khac"


# ═════════════════════════ CẤU TRÚC CỬA ═════════════════════════

def test_cua_dung_tien_to_rieng():
    from app.api.v1 import chuyen_doi_lead as API
    assert API.router.prefix == "/api/v1/chuyen-doi-lead"


def test_ghi_hep_hon_xem_va_KHONG_co_nv_kd():
    from app.api.v1 import chuyen_doi_lead as API
    assert set(API.GHI) < set(API.XEM)
    assert "nv_kd" not in API.GHI, (
        "Nhân viên kinh doanh tự chuyển lead đang nằm im của mình sang người khác là tự xoá dấu "
        "vết tồn đọng của chính mình — mà bảng 2.6.2 tồn tại chính để nhìn thấy dấu vết ấy.")
    assert "nv_mkt" in API.GHI, (
        "Người Marketing không nhận lead nên không có gì để giấu, mà họ lại là người ngồi nhìn "
        "bảng tồn đọng hằng ngày.")


def test_cua_ton_dong_khong_nhan_thoi_diem_tu_nguoi_goi():
    """Chỗ nguy hiểm số 5 ở đầu tệp."""
    cay = ast.parse((GOC / "app" / "api" / "v1" / "chuyen_doi_lead.py").read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "ton_dong")
    ten = {a.arg for a in ham.args.args + ham.args.kwonlyargs}
    assert "bay_gio" not in ten and "tinh_den" not in ten, (
        "Cho người gọi tự chọn thời điểm là cho họ chọn một mốc mà ở đó mình không quá hạn.")


def test_man_hinh_khai_dung_mot_nhom_cua():
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/chuyen-doi-lead"] == ("/api/v1/chuyen-doi-lead",)


def test_vong_nay_khong_them_bang_nao():
    """Nhóm 2.6 đọc dữ liệu đã có và ghi vào bảng đã có. Thêm bảng mới ở đây là dấu hiệu đã bỏ sót
    một bảng sẵn có — `lead_ban_giao` chính là bảng ấy, nó đã nhận dữ liệu từ đường nạp tệp suốt
    thời gian qua mà không màn hình nào đọc."""
    tep = list((GOC / "alembic" / "versions").glob("tc78*.py"))
    assert not tep, f"TC-78 không cần bản nâng cấp nào, nhưng thấy {[t.name for t in tep]}"
