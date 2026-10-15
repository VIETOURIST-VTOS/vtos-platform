# -*- coding: utf-8 -*-
"""DL-5 · Đổi xe / đổi tài xế trên một lệnh đã lập — tám luật Chủ tịch chốt 15/10/2026.

VÌ SAO CÓ CỬA NÀY. Đo lại phân hệ điều hành 15/10/2026: cửa sửa lệnh nhận đúng hai thứ, `status`
và `incident_note`. Xe hỏng trước giờ khởi hành thì Điều hành phải XOÁ lệnh rồi LẬP LẠI — mất dấu
lệnh cũ, mất dấu ai đã nhận, và tháng sau không ai trả lời được vì sao đổi.

Hai luật khó nhất, và là lý do tệp này dài hơn vẻ ngoài:

  1. ĐỔI XE thì xe mới phải TỰ ĐỨNG ĐƯỢC — nếu không thì cửa đổi thành cửa sau của cửa lập: lập
     bằng xe sạch rồi đổi sang xe hết đăng kiểm.
  2. ĐỔI TÀI XẾ thì KHÔNG ĐƯỢC LÀM LỆNH XẤU ĐI — chỉ chặn trên vi phạm MỚI sinh ra. Bắt người đổi
     tài xế lúc 10 giờ đêm gánh một lỗi giấy tờ của xe có từ trước là làm cửa ấy vô dụng.
"""
import os
import tempfile
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.hr import DispatchOrder, Employee, Vehicle, VehicleRate  # noqa: E402
from app.services import doi_xe_lenh as DX  # noqa: E402
from app.services import fleet as FL  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nen(db):
    """Hai xe nhà + một xe hợp tác, ba tài xế, một tour. Ngày đi đặt ở TƯƠNG LAI để các phép
    kiểm hạn giấy tờ không tự nhiên đỏ vì hôm nay đã qua ngày ấy."""
    tx1 = Employee(code="TX1", full_name="Lý Văn Sơn", department="doi_xe")
    tx2 = Employee(code="TX2", full_name="Nguyễn Văn Bền", department="doi_xe")
    tx3 = Employee(code="TX3", full_name="Phạm Văn Tới", department="doi_xe")
    dh = Employee(code="DH1", full_name="Điều hành viên", department="dieu_hanh")
    db.add_all([tx1, tx2, tx3, dh]); db.flush()
    v1 = Vehicle(plate="51B-456.78", code="XE0001", seats=45, kind="noi_bo",
                 driver_id=tx1.id, internal_rate_per_day=800_000)
    v2 = Vehicle(plate="51B-789.01", code="XE0002", seats=45, kind="noi_bo",
                 driver_id=tx2.id, internal_rate_per_day=900_000)
    # `kind` và `op_right` là HAI cột khác nhau và cả hai phải khai: giá đọc `kind` (xe hợp tác
    # ăn giá đối tác), còn bộ điều kiện phát lệnh đọc `op_right` – để `so_huu` mà không có tài xế
    # thì nó chặn ở mức BLOCK, đúng luật. Khai thiếu một trong hai là một hồ sơ xe sai, không
    # phải một cửa hỏng.
    vh = Vehicle(plate="51C-220.44", code="XE0003", seats=45, kind="hop_tac",
                 op_right="hop_tac", driver_id=None, internal_rate_per_day=1_000_000)
    db.add_all([v1, v2, vh]); db.flush()
    di = date.today() + timedelta(days=30)
    t = Tour(code="DL-0912", name="Đà Lạt", tour_type="doan_noi_dia", operator_id=dh.id,
             start_date=di, end_date=di + timedelta(days=2))
    db.add(t); db.flush()
    return {"v1": v1, "v2": v2, "vh": vh, "tx1": tx1, "tx2": tx2, "tx3": tx3, "t": t, "di": di}


def _lenh(db, n, trang_thai="da_xac_nhan", rate_id=None, gia=2_400_000):
    d = DispatchOrder(tour_id=n["t"].id, vehicle_id=n["v1"].id, driver_id=n["tx1"].id,
                      date_from=n["di"], date_to=n["di"] + timedelta(days=2),
                      rate_id=rate_id, internal_price=gia, created_by="gddx",
                      status=trang_thai)
    db.add(d); db.flush()
    return d


# ═══════════════ LUẬT 1 · chỉ hai trạng thái đổi được
def test_trang_thai_doi_duoc_dung_hai_cai(db):
    """Hằng số đọc được, và phép thử đọc CHÍNH NÓ – thêm trạng thái mà quên thì chỗ này đỏ."""
    assert DX.TRANG_THAI_DOI_DUOC == ("cho_xac_nhan", "da_xac_nhan")


@pytest.mark.parametrize("tt", ["cho_xac_nhan", "da_xac_nhan"])
def test_hai_trang_thai_nay_doi_duoc(db, tt):
    n = _nen(db); d = _lenh(db, n, tt)
    kq = DX.doi_xe(db, d, n["v2"], "xe hỏng hộp số", "gddx")
    assert d.vehicle_id == n["v2"].id
    assert kq["truoc"]["xe"] == "51B-456.78" and kq["sau"]["xe"] == "51B-789.01"


def test_lenh_hoan_thanh_khong_doi_duoc_vi_da_sinh_chuyen(db):
    """Lệnh hoàn thành đã sinh một chuyến trong nhật trình (DL-3). Đổi xe lúc ấy là sửa lịch sử."""
    n = _nen(db); d = _lenh(db, n, "hoan_thanh")
    with pytest.raises(DX.KhongDoiDuoc) as e:
        DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert "hoàn thành" in str(e.value) and "nhật trình" in str(e.value)
    assert d.vehicle_id == n["v1"].id, "từ chối rồi mà vẫn đổi là tệ hơn cả không có cửa"


def test_lenh_da_huy_khong_doi_duoc(db):
    n = _nen(db); d = _lenh(db, n, "huy")
    with pytest.raises(DX.KhongDoiDuoc):
        DX.doi_tai_xe(db, d, n["tx3"], "tài xế nghỉ", "gddx")


# ═══════════════ LUẬT 2 · lý do bắt buộc
@pytest.mark.parametrize("ly_do", ["", "   ", "\n\t "])
def test_khong_co_ly_do_thi_khong_doi_duoc(db, ly_do):
    """Không có ô này thì đổi xe chỉ là một cách xoá dấu vết êm hơn xoá lệnh."""
    n = _nen(db); d = _lenh(db, n)
    with pytest.raises(DX.KhongDoiDuoc) as e:
        DX.doi_xe(db, d, n["v2"], ly_do, "gddx")
    assert "lý do" in str(e.value)
    assert d.vehicle_id == n["v1"].id


def test_doi_tai_xe_cung_bat_buoc_ly_do(db):
    n = _nen(db); d = _lenh(db, n)
    with pytest.raises(DX.KhongDoiDuoc):
        DX.doi_tai_xe(db, d, n["tx3"], "  ", "gddx")


def test_ly_do_duoc_cat_khoang_trang_va_ghi_lai(db):
    n = _nen(db); d = _lenh(db, n)
    kq = DX.doi_xe(db, d, n["v2"], "  xe hỏng hộp số  ", "gddx")
    assert kq["ly_do"] == "xe hỏng hộp số"


# ═══════════════ LUẬT 3 · đổi sang chính nó thì vô nghĩa
def test_doi_sang_chinh_xe_dang_co_bi_chan(db):
    n = _nen(db); d = _lenh(db, n)
    with pytest.raises(DX.KhongDoiDuoc) as e:
        DX.doi_xe(db, d, n["v1"], "nhầm", "gddx")
    assert "đang là xe" in str(e.value)


def test_doi_sang_chinh_tai_xe_dang_co_bi_chan(db):
    n = _nen(db); d = _lenh(db, n)
    with pytest.raises(DX.KhongDoiDuoc):
        DX.doi_tai_xe(db, d, n["tx1"], "nhầm", "gddx")


# ═══════════════ LUẬT 4 · xe mới phải tự đứng được
def test_xe_ngung_khai_thac_khong_nhan_duoc_lenh(db):
    """Cửa đổi KHÔNG được là cửa sau của cửa lập: lập bằng xe sạch rồi đổi sang xe không dùng được."""
    n = _nen(db); d = _lenh(db, n)
    n["v2"].lifecycle = "ngung"; db.flush()
    with pytest.raises(DX.ViPhamDieuKien) as e:
        DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert any(i["level"] == FL.BLOCK for i in e.value.vi_pham)
    assert d.vehicle_id == n["v1"].id


def test_lenh_dang_sua_khong_tu_bao_minh_trung_lich_voi_minh(db):
    """`bo_qua_lenh=d.id`. Không bỏ qua chính nó thì không lệnh nào đổi xe được."""
    n = _nen(db); d = _lenh(db, n)
    # chính lệnh này đang giữ xe v1; đổi sang v2 rồi đổi NGƯỢC LẠI về v1 phải được
    DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    kq = DX.doi_xe(db, d, n["v1"], "xe cũ sửa xong rồi", "gddx")
    assert d.vehicle_id == n["v1"].id and kq["sau"]["xe"] == "51B-456.78"


# ═══════════════ LUẬT 5 · đổi tài xế KHÔNG được làm lệnh xấu đi
def test_doi_tai_xe_van_duoc_khi_xe_da_vuong_tu_truoc(db):
    """Xe vướng điều kiện từ trước thì đó không phải lỗi của người đổi tài xế lúc 10 giờ đêm."""
    n = _nen(db); d = _lenh(db, n)
    n["v1"].lifecycle = "ngung"; db.flush()          # lệnh đã xấu sẵn, do XE
    kq = DX.doi_tai_xe(db, d, n["tx3"], "tài xế xin nghỉ đột xuất", "gddx")
    assert d.driver_id == n["tx3"].id
    assert kq["truoc"]["tai_xe"] == "Lý Văn Sơn" and kq["sau"]["tai_xe"] == "Phạm Văn Tới"


def test_tai_xe_nghi_viec_khong_nhan_lenh_duoc(db):
    n = _nen(db); d = _lenh(db, n)
    n["tx3"].active = False; db.flush()
    with pytest.raises(DX.KhongDoiDuoc) as e:
        DX.doi_tai_xe(db, d, n["tx3"], "tài xế cũ bệnh", "gddx")
    assert "không còn hoạt động" in str(e.value)


def test_nguoi_ngoai_doi_xe_khong_lam_tai_xe_duoc(db):
    n = _nen(db); d = _lenh(db, n)
    ke_toan = Employee(code="KT1", full_name="Kế toán viên", department="ke_toan")
    db.add(ke_toan); db.flush()
    with pytest.raises(DX.KhongDoiDuoc) as e:
        DX.doi_tai_xe(db, d, ke_toan, "tài xế cũ bệnh", "gddx")
    assert "không thuộc đội xe" in str(e.value)


# ═══════════════ LUẬT 6 · tính lại giá, và MỘT phép tính dùng chung
def test_doi_sang_xe_hop_tac_thi_an_gia_doi_tac(db):
    """Xe hợp tác ăn `partner_price`, xe nhà ăn `internal_price` – hai con số khác nhau."""
    n = _nen(db)
    rt = VehicleRate(route="HCM-DL", days=3, internal_price=2_400_000, partner_price=3_100_000,
                     effective_from=date.today(), status="active")
    db.add(rt); db.flush()
    d = _lenh(db, n, rate_id=rt.id, gia=2_400_000)
    kq = DX.doi_xe(db, d, n["vh"], "hai xe nhà đều bận", "gddx")
    assert kq["truoc"]["gia_noi_bo"] == 2_400_000
    assert kq["sau"]["gia_noi_bo"] == 3_100_000
    assert d.internal_price == 3_100_000


def test_khong_co_tuyen_thi_tinh_theo_don_gia_ngay(db):
    n = _nen(db); d = _lenh(db, n, gia=None)
    DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert d.internal_price == 900_000 * 3, "3 ngày × đơn giá ngày của xe mới"


def test_cua_lap_lenh_va_cua_doi_xe_dung_CHUNG_mot_phep_tinh_gia(db):
    """Không đếm dòng – đọc mã nguồn: `dispatch_create` phải GỌI `tinh_gia`, không chép lại nó."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    assert "tinh_gia" in src, "cửa lập lệnh không gọi phép tính chung"
    assert "partner_price" not in src, "cửa lập lệnh vẫn còn một bản chép tay của công thức giá"


# ═══════════════ LUẬT 7 · xoá dấu nhận và NÓI RA
def test_doi_xe_thi_xoa_dau_nhan_va_noi_ra(db):
    n = _nen(db); d = _lenh(db, n)
    d.nhan_luc = datetime.now(); d.nhan_boi = "tx1"; db.flush()
    kq = DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert d.nhan_luc is None, "lệnh đổi nội dung mà giữ dấu nhận cũ là giữ một chữ ký cho việc khác"
    assert kq["xoa_dau_nhan"] is True
    assert "nhận lại" in kq["noi"], "xoá âm thầm là bắt tài xế bấm lại mà không ai báo"


def test_chua_ai_nhan_thi_khong_bao_nham_la_da_xoa(db):
    n = _nen(db); d = _lenh(db, n)
    kq = DX.doi_tai_xe(db, d, n["tx3"], "tài xế bệnh", "gddx")
    assert kq["xoa_dau_nhan"] is False and "nhận lại" not in kq["noi"]


# ═══════════════ LUẬT 8 · tài xế đi theo xe, và giá KHÔNG theo người
def test_doi_xe_thi_tai_xe_doi_theo(db):
    n = _nen(db); d = _lenh(db, n)
    kq = DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert d.driver_id == n["tx2"].id
    assert kq["sau"]["tai_xe"] == "Nguyễn Văn Bền"


def test_xe_hop_tac_khong_co_tai_xe_thi_giu_nguoi_dang_co(db):
    """KHÔNG gắn bừa một người thứ hai – gắn bừa chỉ làm sổ trùng lịch thêm người không liên quan."""
    n = _nen(db); d = _lenh(db, n)
    DX.doi_xe(db, d, n["vh"], "hai xe nhà đều bận", "gddx")
    assert d.vehicle_id == n["vh"].id
    assert d.driver_id == n["tx1"].id


def test_doi_tai_xe_khong_dong_vao_xe_va_khong_dong_vao_gia(db):
    n = _nen(db); d = _lenh(db, n, gia=2_400_000)
    DX.doi_tai_xe(db, d, n["tx3"], "tài xế bệnh", "gddx")
    assert d.vehicle_id == n["v1"].id
    assert d.internal_price == 2_400_000, "giá tính theo xe và tuyến, không theo người lái"


# ═══════════════ Phiên bản, nhật ký, và cửa đọc
def test_moi_lan_doi_thi_phien_ban_tang(db):
    """Hai người cùng mở một lệnh rồi cùng đổi thì người sau phải bị chặn, không ghi đè im lặng.

    Đo qua `hr._doi` chứ không qua dịch vụ: khoá phiên bản nằm Ở CỬA, nơi nhận được bản người gọi
    đang cầm. Đo ở dịch vụ thì phép thử này xanh trong khi cửa thật chưa khoá gì.
    """
    from app.api.v1 import hr
    n = _nen(db); d = _lenh(db, n)
    truoc = d.phien_ban
    kq = hr._doi(db, d, None, lambda: DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx"))
    assert d.phien_ban == truoc + 1 and kq["phien_ban"] == truoc + 1
    hr._doi(db, d, d.phien_ban, lambda: DX.doi_tai_xe(db, d, n["tx3"], "tài xế bệnh", "gddx"))
    assert d.phien_ban == truoc + 2


def test_cam_ban_cu_thi_bi_chan_chu_khong_ghi_de(db):
    """Điều hành đang đổi xe vì xe hỏng, trong khi Giám đốc đội xe chốt lệnh ở màn hình bên cạnh."""
    from fastapi import HTTPException
    from app.api.v1 import hr
    n = _nen(db); d = _lenh(db, n)
    ban_nguoi_thu_hai_dang_cam = d.phien_ban
    hr._doi(db, d, None, lambda: DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx"))
    with pytest.raises(HTTPException) as e:
        hr._doi(db, d, ban_nguoi_thu_hai_dang_cam,
                lambda: DX.doi_tai_xe(db, d, n["tx3"], "tài xế bệnh", "nguoi_khac"))
    assert e.value.status_code == 409
    assert d.driver_id == n["tx2"].id, "bị chặn rồi mà vẫn ghi đè là tệ hơn không có khoá"


def test_dich_vu_KHONG_tu_tang_phien_ban(db):
    """Tăng ở cả dịch vụ lẫn cửa thì mỗi lần đổi nhảy hai số, và người cầm bản đúng bị chặn oan."""
    n = _nen(db); d = _lenh(db, n)
    truoc = d.phien_ban
    DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    assert d.phien_ban == truoc


def test_nhat_ky_mang_CA_cu_lan_moi_trong_MOT_dong(db):
    """Ghép hai dòng cạnh nhau để biết ai đổi xe gì sang xe gì là chỗ người ta ghép nhầm."""
    from app.models.core import AuditLog
    from sqlalchemy import select
    n = _nen(db); d = _lenh(db, n)
    DX.doi_xe(db, d, n["v2"], "xe hỏng hộp số", "gddx")
    db.flush()
    log = db.execute(select(AuditLog).where(AuditLog.action == "doi_xe")).scalars().all()
    assert len(log) == 1
    assert log[0].before["xe"] == "51B-456.78"
    assert log[0].after["xe"] == "51B-789.01"
    assert log[0].after["ly_do"] == "xe hỏng hộp số"
    assert log[0].actor == "gddx"


def test_nhat_ky_ghi_duoc_that_chu_khong_do_khi_ep_ra_JSON(db):
    """DL-4b đã đổ 500 đúng ở đây: ngày tháng lọt vào nhật ký rồi `json.dumps` ném lỗi."""
    import json
    from app.models.core import AuditLog
    from sqlalchemy import select
    from app.services import rules as R
    n = _nen(db); d = _lenh(db, n)
    DX.doi_xe(db, d, n["v2"], "xe hỏng", "gddx")
    db.flush()
    log = db.execute(select(AuditLog).where(AuditLog.action == "doi_xe")).scalars().first()
    json.dumps(log.before); json.dumps(log.after)
    R._canon({"before": log.before, "after": log.after})


def test_cua_doc_soat_doi_xe_khong_ghi_gi(db):
    n = _nen(db); d = _lenh(db, n)
    ra = DX.soat_doi_xe(db, d, n["v2"])
    assert ra["xe_cu"] == "51B-456.78" and ra["xe_moi"] == "51B-789.01"
    assert ra["tai_xe_doi_theo"] is True
    assert d.vehicle_id == n["v1"].id, "cửa ĐỌC mà ghi là cửa đọc hỏng"


def test_cua_doc_danh_sach_in_ca_xe_khong_nhan_duoc_kem_ly_do(db):
    """Lọc sẵn thì người điều hành không hiểu vì sao chiếc mình định lấy không có trong danh sách."""
    n = _nen(db); d = _lenh(db, n)
    n["v2"].lifecycle = "ngung"; db.flush()
    ds = DX.xe_thay_the_duoc(db, d)
    bien = {x["bien"] for x in ds}
    assert "51B-456.78" not in bien, "xe đang dùng không nằm trong danh sách thay thế"
    v2 = next(x for x in ds if x["bien"] == "51B-789.01")
    assert v2["nhan_duoc"] is False and v2["ly_do"], "không nhận được thì phải nói vì sao"


def test_cua_doc_danh_sach_tai_xe_bo_nguoi_dang_lai(db):
    n = _nen(db); d = _lenh(db, n)
    ds = DX.tai_xe_thay_the_duoc(db, d)
    ten = {x["ten"] for x in ds}
    assert "Lý Văn Sơn" not in ten
    assert {"Nguyễn Văn Bền", "Phạm Văn Tới"} <= ten


# ═══════════════ Hàng rào kiến trúc
def test_lenh_dieu_xe_da_vao_so_cac_bang_CO_KHOA_phien_ban(db):
    """DL-5 là cửa sửa THẬT đầu tiên của `dispatch_orders` – phải chuyển khỏi CHUA_CO_CUA_SUA."""
    from app.services import ghi_mot_lan as GML
    assert "dispatch_orders" in GML.CUA_SUA_CO_KHOA
    assert "dispatch_orders" not in GML.CHUA_CO_CUA_SUA


def test_hai_cua_ghi_deu_di_qua_mot_cho_soat_quyen():
    """Quyền đổi = quyền lập và chốt. Một cửa rộng hơn cửa kia là hàng rào cạnh đường vòng."""
    import inspect
    from app.api.v1 import hr
    for ten in ("dispatch_doi_xe", "dispatch_doi_tai_xe"):
        src = inspect.getsource(getattr(hr, ten))
        assert "_lenh_de_doi" in src, f"{ten} không đi qua chỗ soát quyền chung"
