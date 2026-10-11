# -*- coding: utf-8 -*-
"""Xe đang trên đường thì KHÔNG được gợi ý điều tiếp — chỗ hở đo được ngày 11/10/2026.

CHỖ HỎNG GỐC. `kiem_tra_dieu_xe` chặn trùng lịch bằng `trung_lich()`, mà hàm ấy đọc bảng LỆNH điều
xe (`dispatch_orders`). Trong mã chỉ có ĐÚNG MỘT cửa tạo lệnh: màn hình điều xe nhập tay. Cửa nạp
hàng loạt — thứ đã nạp 1.051 lượt xe từ chín tệp quyết toán T1–T9/2026 — sinh ra `Trip` và không
sinh một lệnh nào.

Chủ tịch xác nhận 11/10/2026: **hiện Điều hành KHÔNG lập lệnh điều xe**, họ ghi nhật ký sau khi xe
chạy về. Nên đây không phải chỗ hở của dữ liệu lịch sử — nó đang sống: hệ thống tra lệnh, không thấy
lệnh nào, coi mọi xe rảnh suốt mọi ngày, và `goi_y_dieu_xe` gợi ý được một chiếc đang trên đường.

Và một quy ước Chủ tịch chốt cùng ngày, ba vế:

  1. Xe nhà chạy tour  → lượt xe nối vào tour (`Trip.tour_id` có giá trị)
  2. Xe nhà chạy cho thuê bên ngoài → lượt xe KHÔNG nối tour (`tour_id` rỗng)
  3. Cả đội bận, không đủ xe cho tour → mới thuê xe ngoài

Vế 2 là chỗ dễ sai nhất của phép đếm: `tour_id` rỗng KHÔNG phải thiếu dữ liệu, nó nghĩa là xe ấy
ĐANG BẬN đi kiếm tiền. Bỏ qua lượt cho thuê là báo chiếc xe ấy "đậu bãi" — và người điều hành đọc
một lần là mất niềm tin vào cả hệ thống.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_dx1.db")
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
from app.models.hr import Vehicle
from app.models.fleet import Trip
from app.services import fleet as FL

D1 = date.today() + timedelta(days=40)
D2 = D1 + timedelta(days=2)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _xe(db):
    return db.execute(select(Vehicle).where(Vehicle.active == True).order_by(Vehicle.id)).scalars().first()


def _luot(db, v, tour_id, d1=D1, d2=D2, ma="DX1-T1"):
    t = Trip(vehicle_id=v.id, tour_id=tour_id, ten_tour=("Tuyến thử" if tour_id else ""),
             ngay_di=d1, ngay_ve=d2, ma_phieu=ma, nguon="nhap_tay")
    db.add(t); db.flush()
    return t


# ─────────────────────────────────────────── Vế 1: xe chạy tour
def test_xe_dang_chay_tour_thi_bi_chan(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        truoc = FL.kiem_tra_dieu_xe(db, v, D1, D2)
        _luot(db, v, tour_id=1, ma="DX1-tour")
        sau = FL.kiem_tra_dieu_xe(db, v, D1, D2)
        ma_truoc = {i["code"] for i in truoc["items"]}
        ma_sau = {i["code"] for i in sau["items"]}
        assert "TRUNG_NHAT_KY" not in ma_truoc, "chưa có lượt nào mà đã báo trùng"
        assert "TRUNG_NHAT_KY" in ma_sau, "xe đã có lượt chạy tour chồng ngày mà không bị chặn"
        assert sau["muc"] == FL.BLOCK
        db.rollback()


# ─────────────────────────────────────────── Vế 2: xe chạy cho thuê ngoài
def test_xe_chay_CHO_THUE_NGOAI_cung_bi_chan_va_noi_ro_la_cho_thue(_startup):
    """Chủ tịch chốt 11/10: lượt không nối tour nghĩa là chạy cho thuê ngoài — xe ĐANG BẬN."""
    with SessionLocal() as db:
        v = _xe(db)
        _luot(db, v, tour_id=None, ma="DX1-chothue")
        kq = FL.kiem_tra_dieu_xe(db, v, D1, D2)
        item = next((i for i in kq["items"] if i["code"] == "TRUNG_NHAT_KY"), None)
        assert item is not None, "lượt cho thuê ngoài bị bỏ qua — xe đang kiếm tiền mà báo là rảnh"
        assert item["level"] == FL.BLOCK
        assert "CHO THUÊ NGOÀI" in item["msg"], \
            "phải nói rõ xe đang chạy cho thuê, không chỉ nói 'đã có lượt' — người đọc cần biết vì sao"
        db.rollback()


def test_trung_nhat_ky_dem_ca_hai_loai_luot(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        assert FL.trung_nhat_ky(db, v.id, D1, D2) == []
        _luot(db, v, tour_id=1, ma="DX1-a")
        _luot(db, v, tour_id=None, d1=D1 + timedelta(days=1), d2=D2 + timedelta(days=1), ma="DX1-b")
        assert len(FL.trung_nhat_ky(db, v.id, D1, D2)) == 2, "phải đếm cả lượt tour và lượt cho thuê"
        db.rollback()


def test_luot_khong_chong_ngay_thi_khong_chan(_startup):
    """Chặn quá tay cũng là một cách hỏng: xe rảnh mà báo bận thì cả đội đứng."""
    with SessionLocal() as db:
        v = _xe(db)
        _luot(db, v, tour_id=1, d1=D1 - timedelta(days=10), d2=D1 - timedelta(days=8), ma="DX1-xa")
        kq = FL.kiem_tra_dieu_xe(db, v, D1, D2)
        assert not any(i["code"] == "TRUNG_NHAT_KY" for i in kq["items"])
        db.rollback()


def test_luot_da_huy_thi_khong_tinh_la_ban(_startup):
    with SessionLocal() as db:
        v = _xe(db)
        t = _luot(db, v, tour_id=1, ma="DX1-huy")
        t.status = "huy"; db.flush()
        assert FL.trung_nhat_ky(db, v.id, D1, D2) == [], "lượt đã huỷ không phải xe đang chạy"
        db.rollback()


def test_luot_cho_xac_nhan_VAN_tinh_la_ban(_startup):
    """Chuyến chờ xác nhận là chuyến đã có người xếp. Điều xe ấy đi việc khác là tạo ra va chạm."""
    with SessionLocal() as db:
        v = _xe(db)
        t = _luot(db, v, tour_id=1, ma="DX1-cho")
        assert t.status == "cho_xac_nhan"
        assert len(FL.trung_nhat_ky(db, v.id, D1, D2)) == 1
        db.rollback()


# ─────────────────────────────────────────── Gợi ý điều xe không còn gợi ý xe trên đường
def test_goi_y_khong_con_goi_y_xe_dang_tren_duong(_startup):
    from app.services import fleet_ai as AI
    with SessionLocal() as db:
        v = _xe(db)
        truoc = AI.goi_y_dieu_xe(db, D1, D2)
        assert v.id in [p["vehicle_id"] for p in truoc.get("tat_ca", [])], \
            "cảnh dựng sai: xe này lẽ ra đang hợp lệ trước khi có lượt"
        _luot(db, v, tour_id=None, ma="DX1-gy")
        sau = AI.goi_y_dieu_xe(db, D1, D2)
        assert v.id not in [p["vehicle_id"] for p in sau.get("tat_ca", [])], \
            "vẫn gợi ý một chiếc xe đang trên đường"
        assert any(x["vehicle_id"] == v.id for x in sau["bi_loai"])
        db.rollback()


# ─────────────────────────────────────────── Số ghế: nói ra chỗ chưa khai
def test_ghe_mac_dinh_doc_tu_cot_chu_khong_go_cung_45():
    """Gõ cứng 45 thì ngày nào mô hình đổi mặc định, chỗ này lệch mà không ai biết."""
    from app.services import fleet_ai as AI
    assert AI.GHE_MAC_DINH == Vehicle.__table__.c.seats.default.arg
    src = inspect.getsource(AI)
    assert "v.seats == 45" not in src and "seats == 45" not in src, \
        "đang so với số 45 viết cứng thay vì đọc GHE_MAC_DINH"


def test_xe_chua_ai_xac_nhan_so_ghe_duoc_NOI_RA_chu_khong_im_lang(_startup):
    """Dấu hiệu "chưa biết số ghế" là KHÔNG CÓ NGƯỜI XÁC NHẬN, không phải con số bằng 45.

    HX-1 (11/10/2026) đổi cơ chế này, và lý do đáng ghi: bản DX-1 so `seats` với giá trị mặc định 45,
    nên nó gắn nhãn "chưa xác nhận" cho cả xe 45 chỗ THẬT và cái nhãn ấy không bao giờ tắt được.
    Chủ tịch chọn thêm hai cột `seats_xac_nhan_boi` / `_luc`, khác phương án Claude đề xuất.
    """
    from app.services import fleet_ai as AI
    with SessionLocal() as db:
        v = _xe(db)
        assert not (v.seats_xac_nhan_boi or "").strip(), "cảnh dựng sai: xe này lẽ ra chưa xác nhận"
        gy = AI.goi_y_dieu_xe(db, D1, D2, so_khach=20)
        assert v.plate in gy["chua_khai_ghe"], "xe chưa ai xác nhận số ghế mà không được nêu ra"
        # Xác nhận rồi thì HẾT bị nêu — kể cả khi số ghế vẫn đúng bằng 45.
        v.seats = AI.GHE_MAC_DINH
        v.seats_xac_nhan_boi = "gd_doi_xe"
        db.flush()
        gy2 = AI.goi_y_dieu_xe(db, D1, D2, so_khach=20)
        assert v.plate not in gy2["chua_khai_ghe"], \
            "xe 45 chỗ THẬT đã có người xác nhận mà vẫn bị gắn nhãn chưa biết"
        db.rollback()


def test_khong_hoi_so_ghe_thi_khong_canh_bao(_startup):
    """Không truyền số khách thì phép lọc ghế không chạy, nên không được bịa ra cảnh báo."""
    from app.services import fleet_ai as AI
    with SessionLocal() as db:
        gy = AI.goi_y_dieu_xe(db, D1, D2)
        assert gy["chua_khai_ghe"] == []
        db.rollback()
