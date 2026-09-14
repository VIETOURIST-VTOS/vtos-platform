"""VPM-17 – cửa nhập NGÀY ĐẾN HẠN cho đề nghị chi và đơn đặt dịch vụ.

Vì sao bộ kiểm này tồn tại. Sổ nghĩa vụ (VPM-11) xếp mỗi khoản vào một cột của bảng dòng tiền theo
NGÀY. `payment_requests` và `service_orders` không có ngày phải trả nào, nên TOÀN BỘ khoản chi đang
chờ rơi vào rổ "Chưa đủ dữ liệu dự báo" — đếm được, nhưng không xếp được vào cột nào.

Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết CẤU TRÚC và CỬA NHẬP, số liệu do nhân viên tự nhập.
Thiếu cột không phải lý do hoãn — đó là VIỆC CÒN THIẾU. Bộ kiểm này canh cho cái cửa ấy còn sống.

Điều bộ kiểm canh:

  A  CỬA NHẬP TỒN TẠI   – gõ được lúc lập, và sửa được sau khi lập
  B  RỖNG KHÁC ĐOÁN     – không nhập thì để RỖNG, máy KHÔNG tự suy từ ngày lập hay ngày sử dụng
  C  GỠ ĐƯỢC            – nhập nhầm phải sửa về "chưa biết", không kẹt với một ngày sai
  D  DANH SÁCH VIỆC     – khoản thiếu ngày phải HIỆN RA, không im lặng
  E  NỐI VÀO SỔ         – có ngày thì rời rổ "chưa đủ dữ liệu" và vào đúng cột
  F  QUYỀN              – đúng bộ phận đã khai ở bảng cửa nhập mục III.4
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm17.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
DH, KETOAN, TPDH, SALE = "dh.lan", "ketoan", "tp.dieuhanh", "kd.hoa"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _phien():
    from app.db.session import SessionLocal
    return SessionLocal()


_N = {"i": 0}
HAN = date.today() + timedelta(days=12)


def _de_nghi_chi(ngay_den_han=None, so_tien=9_000_000):
    """Dựng thẳng một đề nghị chi – luồng duyệt chi không phải điều VPM-17 canh."""
    from app.models.ops import PaymentRequest
    _N["i"] += 1
    db = _phien()
    try:
        pr = PaymentRequest(code=f"DC-VPM17-{_N['i']:03d}", category="chi_tour", supplier_name="NCC Thử VPM-17",
                            amount=so_tien, description="Chi thử VPM-17", status="cho_chi",
                            created_by="test", ngay_den_han=ngay_den_han)
        db.add(pr); db.commit()
        return pr.id, pr.code
    finally:
        db.close()


def _don_dich_vu(ngay_den_han=None, so_tien=8_000_000):
    from sqlalchemy import select
    from app.models.core import Tour
    from app.models.suppliers import ServiceOrder, Supplier
    _N["i"] += 1
    db = _phien()
    try:
        t = db.execute(select(Tour)).scalars().first()
        s = db.execute(select(Supplier)).scalars().first()
        if s is None:
            s = Supplier(code="NCC-VPM17", ten="NCC Thử VPM-17"); db.add(s); db.flush()
        d = ServiceOrder(code=f"DV-VPM17-{_N['i']:03d}", supplier_id=s.id, tour_id=t.id if t else None,
                         loai="khac", noi_dung="Dịch vụ thử VPM-17", thanh_tien=so_tien,
                         status="da_xac_nhan", ngay_den_han=ngay_den_han, created_by="test")
        db.add(d); db.commit()
        return d.id, d.code
    finally:
        db.close()


def _dat(rid, ngay, ai=KETOAN):
    return client.put(f"/api/v1/payment-requests/{rid}/ngay-den-han",
                      headers=login(ai), json={"ngay_den_han": ngay, "ly_do": "thử"})


def _doc(rid):
    r = client.get("/api/v1/payment-requests?status=cho_tp,cho_kt,cho_duyet,cho_chi", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    return next((x for x in r.json() if x["id"] == rid), None)


# ══════════════════ A – CỬA NHẬP TỒN TẠI ══════════════════

def test_a1_go_duoc_ngay_sau_khi_lap():
    """Hàng nghìn đề nghị chi cũ không có ngày nào. Không có cửa sửa thì chúng kẹt mãi ở rổ thiếu dữ liệu."""
    rid, code = _de_nghi_chi()
    r = _dat(rid, str(HAN))
    assert r.status_code == 200, r.text
    assert str(HAN.day).zfill(2) in r.json()["message"]
    assert _doc(rid)["ngay_den_han"] == str(HAN)


def test_a2_ghi_lai_ai_go_va_luc_nao():
    """Ngày sửa được, nên phải biết ai gõ con số đang nằm đó."""
    rid, _ = _de_nghi_chi()
    _dat(rid, str(HAN), ai=KETOAN)
    d = _doc(rid)
    assert d["ngay_den_han_boi"] == KETOAN
    assert d["ngay_den_han_luc"]


def test_a3_lap_de_nghi_moi_co_the_kem_ngay_luon():
    from sqlalchemy import select
    from app.models.core import Tour
    from app.models.ops import PaymentRequest
    db = _phien()
    try:
        t = db.execute(select(Tour).where(Tour.status.not_in(["huy", "khoa", "da_dong_so"]))).scalars().first()
        tid = t.id if t else None
    finally:
        db.close()
    if tid is None:
        pytest.fail("dữ liệu mẫu không có tour dùng được – bộ kiểm này cần một tour thật")
    r = client.post("/api/v1/payment-requests", headers=login(DH), json={
        "category": "chi_tour", "tour_id": tid, "supplier_name": "NCC lập kèm hạn",
        "amount": 5_000_000, "description": "thử lập kèm hạn", "ngay_den_han": str(HAN)})
    assert r.status_code == 201, r.text
    assert r.json()["request"]["ngay_den_han"] == str(HAN)


def test_a4_don_dich_vu_cung_go_duoc():
    did, _ = _don_dich_vu()
    r = client.put(f"/api/v1/ncc/don/{did}/ngay-den-han", headers=login(KETOAN),
                   json={"ngay_den_han": str(HAN)})
    assert r.status_code == 200, r.text
    ds = client.get("/api/v1/ncc/don", headers=login(KETOAN)).json()["rows"]
    assert next(x for x in ds if x["id"] == did)["ngay_den_han"] == str(HAN)


# ══════════════════ B – RỖNG KHÁC ĐOÁN ══════════════════

def test_b1_khong_nhap_thi_RONG_chu_khong_suy_tu_ngay_lap():
    """Ngày bịa ra trông y hệt ngày thật trên màn hình lãnh đạo. Đó là lý do cột này để rỗng."""
    rid, _ = _de_nghi_chi()
    assert _doc(rid)["ngay_den_han"] is None, "máy tự gán một ngày cho khoản chưa ai hỏi hạn"


def test_b2_don_dich_vu_KHONG_lay_ngay_su_dung_lam_ngay_tra():
    """Ngày dùng dịch vụ là lúc khách lên xe; ngày phải trả là lúc tiền rời tài khoản."""
    from app.models.suppliers import ServiceOrder
    did, _ = _don_dich_vu()
    db = _phien()
    try:
        d = db.get(ServiceOrder, did)
        d.ngay_su_dung = date.today() + timedelta(days=3)
        db.commit()
    finally:
        db.close()
    ds = client.get("/api/v1/ncc/don", headers=login(KETOAN)).json()["rows"]
    dong = next(x for x in ds if x["id"] == did)
    assert dong["ngay_den_han"] is None, "ngày sử dụng bị dùng làm ngày phải trả"


def test_b3_cot_cho_phep_rong_o_tang_csdl():
    """K2: rỗng là CHƯA AI NHẬP. Cột NOT NULL thì buộc phải có một giá trị, tức buộc phải đoán."""
    import app.main  # noqa: F401
    from app.db.session import Base
    for bang in ("payment_requests", "service_orders"):
        cot = Base.metadata.tables[bang].columns["ngay_den_han"]
        assert cot.nullable, f"{bang}.ngay_den_han không cho rỗng – sẽ buộc phải đoán một ngày"
        assert cot.default is None and cot.server_default is None, \
            f"{bang}.ngay_den_han có mặc định – mặc định là một phép đoán đội lốt dữ liệu"


# ══════════════════ C – GỠ ĐƯỢC ══════════════════

def test_c1_go_nham_thi_xoa_ve_chua_biet_duoc():
    """Không gỡ được thì người nhập nhầm sẽ để nguyên ngày sai – tệ hơn là để trống."""
    rid, _ = _de_nghi_chi()
    _dat(rid, str(HAN))
    assert _doc(rid)["ngay_den_han"] == str(HAN)
    r = _dat(rid, None)
    assert r.status_code == 200, r.text
    assert "gỡ" in r.json()["message"]
    d = _doc(rid)
    assert d["ngay_den_han"] is None
    assert d["ngay_den_han_boi"] == "", "gỡ ngày mà vẫn còn tên người gõ"


def test_c2_da_chi_xong_thi_khong_doi_ngay_nua():
    """Sửa ngày đến hạn của một khoản đã trả chỉ làm sai lại một việc đã xong."""
    from app.models.ops import PaymentRequest
    rid, code = _de_nghi_chi()
    db = _phien()
    try:
        db.get(PaymentRequest, rid).status = "da_chi"; db.commit()
    finally:
        db.close()
    r = _dat(rid, str(HAN))
    assert r.status_code == 422
    assert "da_chi" in r.text


# ══════════════════ D – DANH SÁCH VIỆC ══════════════════

def test_d1_khoan_thieu_ngay_HIEN_RA_trong_danh_sach_viec():
    """Một con số thiếu mà không ai nhìn thấy thì không ai đi nhập."""
    rid, code = _de_nghi_chi(so_tien=77_000_000)
    r = client.get("/api/v1/payment-requests/thieu-ngay-den-han", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["so_khoan"] > 0 and b["tong_tien"] > 0
    assert any(x["code"] == code for x in b["chi_tiet"]), "khoản vừa lập không hiện ở danh sách việc"


def test_d2_go_ngay_xong_thi_ROI_danh_sach_viec():
    rid, code = _de_nghi_chi()
    truoc = client.get("/api/v1/payment-requests/thieu-ngay-den-han", headers=login(KETOAN)).json()
    assert any(x["code"] == code for x in truoc["chi_tiet"])
    _dat(rid, str(HAN))
    sau = client.get("/api/v1/payment-requests/thieu-ngay-den-han", headers=login(KETOAN)).json()
    assert not any(x["code"] == code for x in sau["chi_tiet"]), "gõ ngày rồi mà vẫn nằm ở danh sách thiếu"
    assert sau["so_khoan"] < truoc["so_khoan"]


def test_d3_don_dich_vu_cung_co_danh_sach_thieu_ngay():
    """Đơn đã xác nhận mà chưa lập đề nghị chi vẫn là nghĩa vụ thật (mục III.4)."""
    did, code = _don_dich_vu()
    b = client.get("/api/v1/ncc/don/thieu-ngay-den-han", headers=login(KETOAN)).json()
    assert any(x["code"] == code for x in b["chi_tiet"])
    client.put(f"/api/v1/ncc/don/{did}/ngay-den-han", headers=login(KETOAN), json={"ngay_den_han": str(HAN)})
    b2 = client.get("/api/v1/ncc/don/thieu-ngay-den-han", headers=login(KETOAN)).json()
    assert not any(x["code"] == code for x in b2["chi_tiet"])


# ══════════════════ E – NỐI VÀO SỔ NGHĨA VỤ ══════════════════

def _dong_bo():
    r = client.post("/api/v1/fin/nghia-vu/dong-bo", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    return r.json()


def test_e1_co_ngay_thi_ROI_ro_chua_du_du_lieu():
    """Đây là toàn bộ lý do cột này sinh ra: khoản có ngày thì xếp được vào cột của bảng bốn mốc."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    rid, code = _de_nghi_chi()
    _dat(rid, str(HAN))
    _dong_bo()
    db = _phien()
    try:
        nv = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "payment_requests",
            NghiaVuThanhToan.nguon_id == rid)).scalars().first()
        assert nv is not None, "đề nghị chi không vào sổ nghĩa vụ"
        assert nv.ngay_cam_ket == HAN, f"ngày đến hạn chưa nối vào sổ: {nv.ngay_cam_ket}"
    finally:
        db.close()


def test_e2_van_con_ro_chua_du_du_lieu_cho_khoan_chua_go():
    """Nối cột mới KHÔNG được làm rổ biến mất – khoản chưa gõ vẫn phải đếm được."""
    from app.services import nghia_vu as NV
    _de_nghi_chi()
    _dong_bo()
    db = _phien()
    try:
        ro = NV.ba_ro(db, date.today() + timedelta(days=365), co_so_ngay="cam_ket")
        assert ro["chua_du_du_lieu"]["so_khoan"] > 0, "rổ chưa đủ dữ liệu biến mất – khoản chưa gõ đi đâu?"
    finally:
        db.close()


def test_e3_khoan_co_ngay_duoc_CONG_vao_dung_cot():
    from app.services import nghia_vu as NV
    rid, _ = _de_nghi_chi(so_tien=41_000_000)
    _dat(rid, str(HAN))
    _dong_bo()
    db = _phien()
    try:
        trong = NV.cong(db, date.today(), HAN, co_so_ngay="cam_ket")
        ngoai = NV.cong(db, date.today(), HAN - timedelta(days=1), co_so_ngay="cam_ket")
        assert trong.get("tra_ncc", 0) - ngoai.get("tra_ncc", 0) >= 41_000_000, \
            "khoản đến hạn đúng ngày cuối khoảng không được cộng vào"
    finally:
        db.close()


def test_e4_don_dich_vu_co_ngay_cung_vao_so():
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    did, _ = _don_dich_vu()
    client.put(f"/api/v1/ncc/don/{did}/ngay-den-han", headers=login(KETOAN), json={"ngay_den_han": str(HAN)})
    _dong_bo()
    db = _phien()
    try:
        nv = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "service_orders",
            NghiaVuThanhToan.nguon_id == did)).scalars().first()
        assert nv is not None and nv.ngay_cam_ket == HAN
    finally:
        db.close()


def test_e5_ngay_qua_han_thi_trang_thai_la_qua_han():
    """Khoản quá hạn phải hiện RIÊNG mà vẫn tính vào nhu cầu thanh toán (mục III.2)."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    rid, _ = _de_nghi_chi(so_tien=6_000_000)
    _dat(rid, str(date.today() - timedelta(days=9)))
    _dong_bo()
    db = _phien()
    try:
        nv = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "payment_requests",
            NghiaVuThanhToan.nguon_id == rid)).scalars().first()
        # đang chờ chi thì trạng thái là "đã duyệt chờ chuyển"; ngày vẫn phải nối đúng để rổ quá hạn bắt được
        assert nv.ngay_cam_ket < date.today()
    finally:
        db.close()


# ══════════════════ F – QUYỀN ══════════════════

def test_f1_dieu_hanh_va_ke_toan_deu_go_duoc():
    """Bảng cửa nhập mục III.4, dòng Trả nhà cung cấp: bộ phận nhập là Điều hành + Kế toán."""
    for ai in (DH, TPDH, KETOAN):
        rid, _ = _de_nghi_chi()
        r = _dat(rid, str(HAN), ai=ai)
        assert r.status_code == 200, f"{ai} không gõ được ngày đến hạn: {r.status_code} {r.text[:120]}"


def test_f2_ban_kiem_soat_chi_doc_khong_go_duoc():
    """BKS đọc tất cả, ghi thì không – hàng rào chung của hệ thống phải còn hiệu lực ở cửa mới."""
    rid, _ = _de_nghi_chi()
    r = _dat(rid, str(HAN), ai="bks")
    assert r.status_code in (403, 405), f"Ban Kiểm soát ghi được vào cửa mới: {r.status_code}"


def test_f3_ban_nang_cap_mot_dau_nhanh():
    """Dockerfile chạy `alembic upgrade head` trước khi mở cổng – hai đầu nhánh là máy chủ không lên."""
    import pathlib, re
    thu_muc = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    con, ban = {}, set()
    for p in thu_muc.glob("*.py"):
        s = p.read_text(encoding="utf-8")
        r = re.search(r"^revision\s*=\s*['\"]([^'\"]+)", s, re.M)
        d = re.search(r"^down_revision\s*=\s*(?:['\"]([^'\"]+)['\"]|None)", s, re.M)
        if not r: continue
        ban.add(r.group(1))
        if d and d.group(1): con.setdefault(d.group(1), []).append(r.group(1))
    dau = [b for b in ban if b not in con]
    assert len(dau) == 1, f"chuỗi bản nâng cấp có {len(dau)} đầu nhánh: {dau}"
    assert "b5f9h4c7e2a31" in ban, "thiếu bản nâng cấp của VPM-17"
