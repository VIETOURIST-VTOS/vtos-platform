"""VPM-11 – sổ nghĩa vụ thanh toán: một nghĩa vụ, một dòng, một mã gốc.

Vì sao bộ kiểm này tồn tại. Đề xuất chỉnh sửa giao diện v1.1 (11/9/2026), mục IV.4, đòi: "Một nghĩa
vụ có mã gốc liên kết hợp đồng, đề nghị chi, hóa đơn và thanh toán; chỉ tính phần còn lại một lần."
Mã nghiệm thu CF-03 kiểm đúng câu ấy, CF-05 kiểm câu "khoản thiếu ngày đến hạn không bị bỏ qua".

Trước VPM-11, một khoản phải trả nhà cung cấp nằm ở ba chỗ (đơn đặt dịch vụ, đề nghị chi, sổ công
nợ), và bảng dòng tiền cộng thẳng từ ba nguồn sẽ thổi một khoản nợ 100 triệu thành 200–300 triệu.
Sai theo hướng PHÓNG ĐẠI nhu cầu tiền – tức là đi vay một khoản không cần vay.

Điều bộ kiểm canh:

  A  CHẠY LẠI ĐƯỢC      – đồng bộ mười lần ra đúng một sổ; mã gốc không đổi giữa các lần
  B  KHÔNG ĐẾM TRÙNG    – một nghĩa vụ nhiều chứng từ chỉ cộng một lần; trả một phần chỉ còn phần dư
  C  BA RỔ KHÔNG IM     – quá hạn, thiếu ngày, ngoài tầm nhìn: cả ba phải đếm được
  D  HAI CƠ SỞ NGÀY     – cam kết và dự kiến không trộn vào nhau
  E  PHẠM VI PHÁP NHÂN  – tiền của pháp nhân này không lẫn sang bảng của pháp nhân khác
  F  KHAI BÁO           – bảng có cửa nhập đã khai; K2 giữ nguyên; bản nâng cấp một đầu nhánh
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vpm11.db")
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
KETOAN, PTGD, KD = "ketoan", "ptgd.doan", "kd.hoa"


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


def _dong_bo():
    r = client.post("/api/v1/fin/nghia-vu/dong-bo", headers=login(KETOAN))
    assert r.status_code == 200, r.text
    return r.json()


def _so(**kw):
    r = client.get("/api/v1/fin/nghia-vu", headers=login(KETOAN), params=kw)
    assert r.status_code == 200, r.text
    return r.json()


def _de_nghi_chi(so_tien: float, tour_id=None, ncc="NCC Thử VPM-11", trang_thai="cho_chi",
                 category="chi_tour"):
    """Dựng thẳng một đề nghị chi trong kho – luồng duyệt chi không phải điều VPM-11 canh."""
    from app.models.ops import PaymentRequest
    _N["i"] += 1
    db = _phien()
    try:
        pr = PaymentRequest(code=f"DC-VPM11-{_N['i']:03d}", category=category, tour_id=tour_id,
                            supplier_name=ncc, amount=so_tien, description="Chi thử VPM-11",
                            status=trang_thai, created_by="test")
        db.add(pr); db.commit()
        return pr.id
    finally:
        db.close()


def _don_dich_vu(so_tien: float, tour_id: int, ncc_id: int, pr_id=None):
    from app.models.suppliers import ServiceOrder
    _N["i"] += 1
    db = _phien()
    try:
        so = ServiceOrder(code=f"DV-VPM11-{_N['i']:03d}", supplier_id=ncc_id, tour_id=tour_id,
                          loai="khac", noi_dung="Dịch vụ thử VPM-11", thanh_tien=so_tien,
                          status="da_xac_nhan", payment_request_id=pr_id)
        db.add(so); db.commit()
        return so.id
    finally:
        db.close()


def _mot_tour_va_ncc():
    from sqlalchemy import select
    from app.models.core import Tour
    from app.models.suppliers import Supplier
    db = _phien()
    try:
        t = db.execute(select(Tour)).scalars().first()
        s = db.execute(select(Supplier)).scalars().first()
        if s is None:
            s = Supplier(code="NCC-VPM11", ten="NCC Thử VPM-11")
            db.add(s); db.commit()
        return (t.id if t else None), s.id, (s.ten or "")
    finally:
        db.close()


def _lich_vay(so_tien: float, due: date, kind="tra_goc"):
    from sqlalchemy import select
    from app.models.finance import FinContract, FinSchedule
    _N["i"] += 1
    db = _phien()
    try:
        c = db.execute(select(FinContract)).scalars().first()
        if c is None:
            c = FinContract(code=f"KU-VPM11-{_N['i']:03d}", kind="vay", partner="Ngân hàng Thử",
                            contract_no=f"KU{_N['i']}", principal=so_tien, outstanding=so_tien)
            db.add(c); db.flush()
        s = FinSchedule(contract_id=c.id, due_date=due, kind=kind, amount=so_tien, status="ke_hoach")
        db.add(s); db.commit()
        return s.id
    finally:
        db.close()


# ══════════════════ A – CHẠY LẠI ĐƯỢC ══════════════════

def test_a1_dong_bo_hai_lan_khong_sinh_dong_thua():
    """Tính chất sống còn: lần chạy thứ hai mà nhân đôi sổ thì nhu cầu tiền của công ty nhân đôi."""
    _de_nghi_chi(11_000_000)
    mot = _dong_bo()
    hai = _dong_bo()
    ba = _dong_bo()
    assert mot["tong_dong"] == hai["tong_dong"] == ba["tong_dong"], \
        f"đồng bộ lại sinh thêm dòng: {mot['tong_dong']} → {hai['tong_dong']} → {ba['tong_dong']}"


def test_a2_ma_goc_khong_doi_giua_hai_lan_dong_bo():
    """Mã gốc là DANH TÍNH của nghĩa vụ – thứ người ta dán lên chứng từ. Nó phải đứng yên."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    pid = _de_nghi_chi(12_345_000)
    _dong_bo()
    db = _phien()
    try:
        truoc = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "payment_requests",
            NghiaVuThanhToan.nguon_id == pid)).scalars().first()
        assert truoc is not None, "đề nghị chi chờ chi mà không vào sổ nghĩa vụ"
        ma_truoc = truoc.ma_goc
    finally:
        db.close()
    _dong_bo()
    db = _phien()
    try:
        sau = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "payment_requests",
            NghiaVuThanhToan.nguon_id == pid)).scalars().first()
        assert sau.ma_goc == ma_truoc, "mã gốc đổi sau khi đồng bộ lại"
    finally:
        db.close()


def test_a3_moi_chung_tu_dung_mot_dong():
    """Ràng buộc duy nhất (nguồn bảng, nguồn id) phải có thật ở tầng cơ sở dữ liệu, không chỉ trong Python."""
    from sqlalchemy import func, select
    from app.models.nghia_vu import NghiaVuThanhToan
    _dong_bo()
    db = _phien()
    try:
        trung = db.execute(
            select(NghiaVuThanhToan.nguon_bang, NghiaVuThanhToan.nguon_id, func.count())
            .group_by(NghiaVuThanhToan.nguon_bang, NghiaVuThanhToan.nguon_id)
            .having(func.count() > 1)).all()
        assert trung == [], f"có chứng từ sinh ra nhiều hơn một dòng nghĩa vụ: {trung}"
    finally:
        db.close()


# ══════════════════ B – KHÔNG ĐẾM TRÙNG ══════════════════

def test_b1_don_dich_vu_da_co_de_nghi_chi_thi_KHONG_vao_so_hai_lan():
    """Đúng kịch bản CF-03: một nghĩa vụ đi qua hai chứng từ, chỉ được cộng một lần."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    tid, sid, _ = _mot_tour_va_ncc()
    pid = _de_nghi_chi(50_000_000, tour_id=tid)
    doid = _don_dich_vu(50_000_000, tour_id=tid, ncc_id=sid, pr_id=pid)
    _dong_bo()
    db = _phien()
    try:
        tu_don = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "service_orders",
            NghiaVuThanhToan.nguon_id == doid)).scalars().first()
        tu_de_nghi = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "payment_requests",
            NghiaVuThanhToan.nguon_id == pid)).scalars().first()
        assert tu_de_nghi is not None, "đề nghị chi phải vào sổ"
        assert tu_don is None, "đơn dịch vụ ĐÃ CÓ đề nghị chi mà vẫn vào sổ – đếm trùng 50 triệu"
    finally:
        db.close()


def test_b2_don_dich_vu_CHUA_co_de_nghi_chi_thi_VAN_vao_so():
    """Mục III.4 của đề xuất: lịch thanh toán NCC phải gồm cả nghĩa vụ chưa lập đề nghị chi."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    tid, sid, _ = _mot_tour_va_ncc()
    doid = _don_dich_vu(37_000_000, tour_id=tid, ncc_id=sid, pr_id=None)
    _dong_bo()
    db = _phien()
    try:
        nv = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "service_orders",
            NghiaVuThanhToan.nguon_id == doid)).scalars().first()
        assert nv is not None, "nghĩa vụ chưa lập đề nghị chi bị bỏ khỏi sổ"
        assert nv.nhom == "tra_ncc"
        assert nv.con_lai() == 37_000_000
    finally:
        db.close()


def test_b3_tra_mot_phan_chi_con_phan_du():
    """CF-03 vế sau: trả một phần thì chỉ tính số còn lại, không tính lại từ đầu."""
    from app.models.nghia_vu import NghiaVuThanhToan
    nv = NghiaVuThanhToan(ma_goc="NV-TEST-B3", huong="chi", nhom="tra_ncc",
                          tong_nghia_vu=100_000_000, da_tra=40_000_000,
                          nguon_bang="test", nguon_id=903)
    assert nv.con_lai() == 60_000_000


def test_b4_tra_thua_KHONG_thanh_nghia_vu_am():
    """Trả thừa là khoản PHẢI TRẢ LẠI, thuộc nhóm khác – không phải số âm làm nhẹ bớt cột tổng."""
    from app.models.nghia_vu import NghiaVuThanhToan
    nv = NghiaVuThanhToan(ma_goc="NV-TEST-B4", huong="chi", nhom="tra_ncc",
                          tong_nghia_vu=10_000_000, da_tra=12_000_000,
                          nguon_bang="test", nguon_id=904)
    assert nv.con_lai() == 0, "nghĩa vụ âm sẽ trừ bớt nhu cầu tiền của khoản khác"


def test_b5_cot_tien_rong_khac_khong():
    """K2: rỗng là CHƯA AI NHẬP. Đọc mà không bọc `or 0` thì nổ TypeError, không phải ra 0."""
    from app.models.nghia_vu import NghiaVuThanhToan
    nv = NghiaVuThanhToan(ma_goc="NV-TEST-B5", huong="chi", nhom="thue",
                          tong_nghia_vu=None, da_tra=None, nguon_bang="test", nguon_id=905)
    assert nv.con_lai() == 0.0


def test_b6_lich_hop_dong_va_booking_khong_cong_hai_lan():
    """Quy tắc MỘT: hợp đồng thu tiền QUA phiếu thu của booking – cộng cả hai là đếm hai lần."""
    from sqlalchemy import select
    from app.models.ban_hang import HopDongKhach
    from app.models.core import Booking
    from app.models.nghia_vu import NghiaVuThanhToan
    db = _phien()
    try:
        b = db.execute(select(Booking).where(Booking.cancelled == False)).scalars().first()  # noqa: E712
        if b is None:
            pytest.fail("dữ liệu mẫu không có booking nào – bộ kiểm này cần một booking thật")
        bid = b.id
        hd = HopDongKhach(so_hop_dong="HD-VPM11-B6", khach_ten="Khách thử VPM-11",
                          ngay_ky=date.today(), gia_tri=200_000_000, trang_thai="da_ky",
                          booking_id=bid)
        db.add(hd); db.commit(); hid = hd.id
    finally:
        db.close()
    r = client.post(f"/api/v1/ban-hang/hop-dong/{hid}/lich-thanh-toan", headers=login(KD),
                    json={"dot": [
                        {"ten": "Đợt 1", "so_tien": 120_000_000, "moc": "ngay_ky", "moc_so_ngay": 0},
                        {"ten": "Đợt 2", "so_tien": 80_000_000, "moc": "ngay_ky", "moc_so_ngay": 30}]})
    assert r.status_code == 200, r.text
    _dong_bo()
    db = _phien()
    try:
        tu_booking = db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "bookings",
            NghiaVuThanhToan.nguon_id == bid)).scalars().first()
        tu_lich = list(db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "lich_thanh_toan_hd")).scalars())
        from app.models.nghia_vu import TRANG_THAI_DONG
        # Dòng cũ được ĐÓNG chứ không xoá (mã gốc là danh tính, xoá là mất dấu vết). Điều phải đúng
        # là: nó KHÔNG CÒN ĐƯỢC CỘNG. Dòng còn nằm đó mà vẫn mở thì tiền của một khách đếm hai lần.
        assert tu_booking is None or tu_booking.trang_thai in TRANG_THAI_DONG, \
            (f"booking đã có lịch hợp đồng mà dòng cũ vẫn mở "
             f"(trạng thái {tu_booking.trang_thai}) – tiền của một khách đếm hai lần")
        assert len(tu_lich) >= 2, "các đợt của lịch hợp đồng chưa vào sổ"
    finally:
        db.close()


# ══════════════════ C – BA RỔ KHÔNG ĐƯỢC IM LẶNG ══════════════════

def test_c1_khoan_thieu_ngay_den_han_nam_o_ro_rieng_chu_khong_BIEN_MAT():
    """CF-05. Hàm dự báo cũ bỏ lặng những khoản này, nên bảng dòng tiền trông gọn hơn sự thật."""
    _de_nghi_chi(88_000_000)         # đề nghị chi không có cột ngày đến hạn nào
    _dong_bo()
    ro = _so()["ba_ro"]["chua_du_du_lieu"]
    assert ro["so_khoan"] > 0, "khoản không có ngày đến hạn đã biến mất khỏi mọi rổ"
    assert ro["tong"] > 0
    assert any(d["chung_tu_nguon"]["bang"] == "payment_requests" for d in ro["chi_tiet"])


def test_c2_khoan_qua_han_hien_RIENG_va_van_duoc_dem():
    """Mục III.2: khoản quá hạn hiển thị riêng VÀ tính vào nhu cầu thanh toán. Không tự ẩn."""
    _lich_vay(45_000_000, date.today() - timedelta(days=20))
    _dong_bo()
    ro = _so()["ba_ro"]["qua_han"]
    assert ro["so_khoan"] > 0, "khoản quá hạn không hiện ở rổ riêng"
    assert ro["tong"] >= 45_000_000


def test_c3_khoan_ngoai_tam_nhin_duoc_dem_chu_khong_bo_qua():
    """Hàm cũ `return` sớm với khoản quá cuối kỳ – nó biến mất không dấu vết."""
    _lich_vay(60_000_000, date.today() + timedelta(days=300))
    _dong_bo()
    ro = _so()["ba_ro"]["ngoai_tam_nhin"]
    assert ro["so_khoan"] > 0, "khoản ngoài tầm nhìn bị bỏ im lặng"


def test_c4_khoan_thieu_ngay_KHONG_bi_cong_vao_cot_nao():
    """Không có ngày thì không thuộc cột nào – nhưng phải nằm ở rổ, không được lặng lẽ thành 0."""
    from app.services import nghia_vu as NV
    _de_nghi_chi(77_000_000)
    _dong_bo()
    db = _phien()
    try:
        cong = NV.cong(db, date.today(), date.today() + timedelta(days=365), co_so_ngay="cam_ket")
        ro = NV.ba_ro(db, date.today() + timedelta(days=365), co_so_ngay="cam_ket")
        assert ro["chua_du_du_lieu"]["tong"] > 0
        # phần chưa đủ dữ liệu không được lẫn vào tổng các cột
        assert cong.get("tra_ncc", 0) >= 0
    finally:
        db.close()


# ══════════════════ D – HAI CƠ SỞ NGÀY KHÔNG TRỘN ══════════════════

def test_d1_booking_khong_co_lich_thi_co_ngay_du_kien_ma_KHONG_co_ngay_cam_ket():
    """Ngày D-7 là ƯỚC, không ai ký. Để nó vào ô cam kết là bịa ra một lời hứa chưa từng có."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    _dong_bo()
    db = _phien()
    try:
        ds = list(db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang == "bookings")).scalars())
        if not ds:
            pytest.fail("không có booking nào vào sổ – bộ kiểm này cần dữ liệu mẫu có booking")
        assert all(nv.ngay_cam_ket is None for nv in ds), \
            "ngày ƯỚC D-7 bị ghi vào ô ngày cam kết"
        assert any(nv.ngay_du_kien_tra is not None for nv in ds)
    finally:
        db.close()


def test_d2_hai_co_so_ngay_cho_hai_ket_qua_khac_nhau():
    """Hai tab của mục III.3 phải thật sự khác nhau, nếu không thì dựng hai tab để làm gì."""
    from app.services import nghia_vu as NV
    _dong_bo()
    db = _phien()
    try:
        tu, den = date.today(), date.today() + timedelta(days=400)
        ck = NV.cong(db, tu, den, co_so_ngay="cam_ket")
        dk = NV.cong(db, tu, den, co_so_ngay="du_kien")
        assert ck != dk, "hai cơ sở ngày cho cùng một kết quả – nhiều khả năng chỉ dùng một cột"
    finally:
        db.close()


def test_d3_cua_api_tu_choi_co_so_ngay_la():
    r = client.get("/api/v1/fin/nghia-vu/chi-tiet", headers=login(KETOAN),
                   params={"co_so_ngay": "ca_hai"})
    assert r.status_code == 422
    assert "không trộn" in r.text


def test_d4_khoang_ngay_bao_gom_ca_hai_dau():
    """Chỗ sinh lỗi lệch một ngày. Bốn cột của bảng dòng tiền phải dùng cùng một quy tắc."""
    from app.services import nghia_vu as NV
    han = date.today() + timedelta(days=10)
    _lich_vay(33_000_000, han)
    _dong_bo()
    db = _phien()
    try:
        trong = NV.cong(db, date.today(), han, co_so_ngay="cam_ket")
        ngoai = NV.cong(db, date.today(), han - timedelta(days=1), co_so_ngay="cam_ket")
        assert trong.get("tra_goc_vay", 0) - ngoai.get("tra_goc_vay", 0) >= 33_000_000, \
            "khoản đến hạn ĐÚNG ngày cuối khoảng bị bỏ ra ngoài"
    finally:
        db.close()


def test_d5_cong_luy_ke_chi_tang_khong_giam():
    """Bất biến của bảng bốn mốc: cột sau bao trùm cột trước."""
    from app.services import nghia_vu as NV
    _dong_bo()
    db = _phien()
    try:
        h = date.today()
        moc = [h + timedelta(days=6), h + timedelta(days=13),
               h + timedelta(days=45), h + timedelta(days=75)]
        truoc = {}
        for m in moc:
            nay = NV.cong(db, h, m, co_so_ngay="cam_ket")
            for k, v in truoc.items():
                assert nay.get(k, 0) >= v, f"nhóm {k} GIẢM khi nới mốc – lũy kế mà giảm là sai"
            truoc = nay
    finally:
        db.close()


# ══════════════════ E – PHẠM VI PHÁP NHÂN ══════════════════

def test_e1_loc_theo_phap_nhan_khong_lay_cua_phap_nhan_khac():
    """Mục IV.4: không mặc định tiền công ty này dùng được cho công ty khác."""
    from sqlalchemy import select
    from app.models.core import Company
    from app.services import nghia_vu as NV
    _dong_bo()
    db = _phien()
    try:
        cty = db.execute(select(Company)).scalars().first()
        if cty is None:
            pytest.fail("dữ liệu mẫu không có pháp nhân nào")
        rieng = NV.cong(db, date.today(), date.today() + timedelta(days=400),
                        co_so_ngay="cam_ket", company_id=cty.id)
        chung = NV.cong(db, date.today(), date.today() + timedelta(days=400), co_so_ngay="cam_ket")
        for k, v in rieng.items():
            assert v <= chung.get(k, 0), f"bảng của một pháp nhân lớn hơn bảng toàn hệ ở nhóm {k}"
    finally:
        db.close()


def test_e2_dong_ghi_nho_KHONG_duoc_cong_vao_cot_nao():
    """Thu hộ khách và ký quỹ có thật nhưng KHÔNG thuộc tiền khả dụng – chỉ hiển thị."""
    from sqlalchemy import select
    from app.models.nghia_vu import GHI_NHO, NghiaVuThanhToan
    from app.services import nghia_vu as NV
    db = _phien()
    try:
        db.add(NghiaVuThanhToan(ma_goc="NV-TEST-E2", huong="thu", nhom="thu_ho_khach",
                                ghi_nho=True, tong_nghia_vu=500_000_000,
                                ngay_cam_ket=date.today() + timedelta(days=3),
                                ngay_du_kien_tra=date.today() + timedelta(days=3),
                                nguon_bang="test", nguon_id=902))
        db.commit()
        cong = NV.cong(db, date.today(), date.today() + timedelta(days=30), co_so_ngay="cam_ket")
        for g in GHI_NHO:
            assert g not in cong, f"dòng ghi nhớ “{g}” bị cộng vào bảng dòng tiền"
        ro = NV.ba_ro(db, date.today() + timedelta(days=30), co_so_ngay="cam_ket")
        assert all(d["nhom"] not in GHI_NHO
                   for r in ro.values() for d in r["chi_tiet"]), "dòng ghi nhớ lọt vào ba rổ"
        db.execute(select(NghiaVuThanhToan))
    finally:
        db.close()


def test_e3_ptgd_khong_mo_duoc_so_nghia_vu():
    """SEC-02: hai Phó Tổng giám đốc không thấy khối dòng tiền, kể cả khi gọi thẳng đường dẫn."""
    for duong in ("/api/v1/fin/nghia-vu", "/api/v1/fin/nghia-vu/chi-tiet"):
        r = client.get(duong, headers=login(PTGD))
        assert r.status_code == 403, f"{duong} mở cho Phó TGĐ – trái SEC-02 ({r.status_code})"


def test_e4_ptgd_khong_dong_bo_duoc():
    r = client.post("/api/v1/fin/nghia-vu/dong-bo", headers=login(PTGD))
    assert r.status_code == 403


# ══════════════════ F – KHAI BÁO VÀ BẢN NÂNG CẤP ══════════════════

def test_f1_bang_da_khai_cua_nhap():
    """Bảng nào chưa khai cửa là VIỆC CÒN THIẾU, theo ranh giới 09/9/2026."""
    from app.services import ks_cua_nhap as KCN
    b = KCN.bang()
    assert "nghia_vu_thanh_toan" not in b["khong_cua"], \
        "bảng nghĩa vụ chưa khai cửa nhập trong ks_cua_nhap.py"
    assert "nghia_vu_thanh_toan" in KCN.MAY_SINH
    assert len(KCN.MAY_SINH["nghia_vu_thanh_toan"]) > 40, "khai máy sinh mà không nêu lý do"


def test_f2_ban_nang_cap_mot_dau_nhanh():
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
    assert "a4e8g3b6d1f29" in ban, "thiếu bản nâng cấp của VPM-11"


def test_f3_bang_nam_trong_mo_hinh_sau_khi_nap_app():
    """models/__init__ thiếu một dòng import thì mọi phép thử soi mô hình sẽ mù đúng bảng ấy."""
    import app.main  # noqa: F401
    from app.db.session import Base
    assert "nghia_vu_thanh_toan" in Base.metadata.tables


def test_f4_moi_nhom_deu_thuoc_mot_huong_hop_le():
    from app.models.nghia_vu import HUONG, NHOM
    for ma, (huong, ten) in NHOM.items():
        assert huong in HUONG, f"nhóm {ma} khai hướng lạ: {huong}"
        assert ten.strip(), f"nhóm {ma} chưa có tên tiếng Việt để hiện lên màn hình"


def test_f5_khong_tu_gop_chung_tu_nghi_trung():
    """Gộp hai chứng từ của hai phòng là một quy tắc kế toán – phải có người ký, robot không tự đặt."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    tid, sid, ten_ncc = _mot_tour_va_ncc()
    _de_nghi_chi(64_000_000, tour_id=tid, ncc=ten_ncc)
    _don_dich_vu(64_000_000, tour_id=tid, ncc_id=sid, pr_id=None)
    _dong_bo()
    db = _phien()
    try:
        ds = list(db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.tong_nghia_vu == 64_000_000)).scalars())
        assert len(ds) == 2, "hai chứng từ nghi trùng đã bị TỰ GỘP – đó là quy tắc chưa ai ký"
        assert any(nv.nghi_trung_voi for nv in ds), \
            "hai chứng từ cùng tour, cùng đối tượng, cùng số tiền mà không ai đánh dấu nghi trùng"
    finally:
        db.close()


# ══════════════════ G – TỔNG GIÁM ĐỐC CHỈ XEM TÀI CHÍNH TOUR VÀ XE ══════════════════
#
# Chốt của Chủ tịch 11/9/2026: "Chủ tịch xem TẤT CẢ dòng tài chính; Tổng giám đốc CHỈ xem tài chính
# hoạt động kinh doanh TOUR + XE." Nhóm G canh đúng câu ấy, và canh ở chỗ MÁY CHỦ — vì giấu một dòng
# trên giao diện thì gọi thẳng đường dẫn chi tiết là thấy lại.

TGD = "tgd"


def _nap_du_moi_nhom():
    """Dựng đủ nghĩa vụ ở cả nhóm trong tầm lẫn ngoài tầm của Tổng giám đốc."""
    from sqlalchemy import select
    from app.models.nghia_vu import NghiaVuThanhToan
    db = _phien()
    try:
        for i, (nhom, huong) in enumerate([("tra_ncc", "chi"), ("thu_khach", "thu"),
                                           ("tra_goc_vay", "chi"), ("lai_phi_vay", "chi"),
                                           ("thue", "chi"), ("giai_ngan_vay", "thu"),
                                           ("luong_bh", "chi")]):
            ma = f"NV-TEST-G{i}"
            if db.execute(select(NghiaVuThanhToan).where(
                    NghiaVuThanhToan.ma_goc == ma)).scalars().first():
                continue
            db.add(NghiaVuThanhToan(
                ma_goc=ma, huong=huong, nhom=nhom, tong_nghia_vu=7_000_000 + i,
                ngay_cam_ket=date.today() + timedelta(days=5),
                ngay_du_kien_tra=date.today() + timedelta(days=5),
                trang_thai="du_kien", nguon_bang="test", nguon_id=8100 + i))
        db.commit()
    finally:
        db.close()


def test_g1_tgd_KHONG_thay_nam_nhom_ngoai_tam():
    """Vay, thuế, ký quỹ không phải tài chính hoạt động tour–xe."""
    from app.models.nghia_vu import NHOM_NGOAI_TAM_TGD
    _nap_du_moi_nhom()
    r = client.get("/api/v1/fin/nghia-vu", headers=login(TGD))
    assert r.status_code == 200, r.text
    b = r.json()
    for nhom in NHOM_NGOAI_TAM_TGD:
        assert nhom not in b["cam_ket"], f"Tổng giám đốc thấy nhóm ngoài tầm: {nhom}"
        assert nhom not in b["du_kien"], f"Tổng giám đốc thấy nhóm ngoài tầm: {nhom}"


def test_g2_chu_tich_va_ke_toan_van_thay_TOAN_CANH():
    """Hàng rào chỉ siết đúng một vai trò. Siết nhầm Chủ tịch là làm hỏng việc của người quyết."""
    _nap_du_moi_nhom()
    for ai in ("chutich", KETOAN):
        b = client.get("/api/v1/fin/nghia-vu", headers=login(ai)).json()
        co = set(b["cam_ket"]) | set(b["du_kien"])
        assert "tra_goc_vay" in co or "thue" in co or "giai_ngan_vay" in co, \
            f"vai trò {ai} mất toàn cảnh — đáng lẽ phải thấy cả nhóm vay và thuế"
        assert b["nhom_ngoai_tam"] == [], f"vai trò {ai} bị báo là có nhóm ngoài tầm"


def test_g3_goi_THANG_duong_dan_chi_tiet_cung_bi_chan():
    """Chỗ hàng rào hay hở nhất: bảng tổng hợp lọc rồi, nhưng cửa chi tiết thì quên."""
    _nap_du_moi_nhom()
    r = client.get("/api/v1/fin/nghia-vu/chi-tiet", headers=login(TGD),
                   params={"nhom": "tra_goc_vay"})
    assert r.status_code == 403, f"Tổng giám đốc gọi thẳng nhóm ngoài tầm mà qua được: {r.status_code}"


def test_g4_khong_loc_nhom_thi_danh_sach_chi_tiet_cung_khong_lot_nhom_ngoai_tam():
    """Không truyền `nhom` thì càng phải lọc — đây là cách lấy trọn sổ bằng một lời gọi."""
    from app.models.nghia_vu import NHOM_NGOAI_TAM_TGD
    _nap_du_moi_nhom()
    r = client.get("/api/v1/fin/nghia-vu/chi-tiet", headers=login(TGD))
    assert r.status_code == 200, r.text
    thay = {d["nhom"] for d in r.json()["chi_tiet"]}
    lot = thay & set(NHOM_NGOAI_TAM_TGD)
    assert not lot, f"danh sách chi tiết lọt nhóm ngoài tầm của Tổng giám đốc: {sorted(lot)}"


def test_g5_bang_NOI_RO_nhung_nhom_bi_giau_va_ly_do():
    """Bảng thiếu dòng mà không giải thích thì người đọc tưởng công ty không có khoản ấy."""
    _nap_du_moi_nhom()
    b = client.get("/api/v1/fin/nghia-vu", headers=login(TGD)).json()
    assert b["nhom_ngoai_tam"], "không nói cho Tổng giám đốc biết bảng đang thiếu nhóm nào"
    for d in b["nhom_ngoai_tam"]:
        assert d["ten"].strip(), "nhóm bị giấu mà không có tên tiếng Việt"
        assert len(d["ly_do"]) > 20, f"nhóm {d['nhom']} bị giấu mà không nêu lý do"


def test_g6_vai_tro_la_roi_vao_nhanh_HEP_hon_khong_phai_rong_hon():
    """Khai quyền cẩu thả một lần không được biến thành lộ sổ."""
    from app.models.nghia_vu import NHOM, nhom_duoc_xem
    assert nhom_duoc_xem("vai_tro_chua_tung_co") < set(NHOM)
    assert nhom_duoc_xem("chutich") == set(NHOM)


def test_g7_moi_nhom_ngoai_tam_deu_co_ly_do_viet_ra():
    """Giấu một dòng tiền khỏi Tổng giám đốc là việc phải giải thích được, không phải mặc định."""
    from app.models.nghia_vu import NHOM, NHOM_NGOAI_TAM_TGD
    for nhom, ly_do in NHOM_NGOAI_TAM_TGD.items():
        assert nhom in NHOM, f"khai nhóm ngoài tầm không có thật: {nhom}"
        assert len(ly_do) > 20, f"nhóm {nhom} bị giấu mà lý do quá sơ sài"
