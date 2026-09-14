"""Sự cố tour – V7 Đợt 3 (10/9/2026).

Chốt chặn sống còn: bảng RIÊNG, không dùng lại `incidents`. `incidents` là hồ sơ kỷ luật nội bộ của một
nhân viên; sự cố tour là chuyện xảy ra với một chuyến, và phần lớn không có ai sai. Hai bảng nối được
với nhau bằng `incident_id` khi – và chỉ khi – xác định được lỗi thuộc về một người cụ thể.

  S1  bảng su_co_tour tồn tại và TÁCH HẲN khỏi incidents (không cột nào chung, không dữ liệu chuyển sang)
  S2  không có cột tiền nào trong cả hai bảng mới – chi phí đi qua đề nghị chi
  S3  sự cố không gắn chuyến thì không lập được
  S4  hạn xử lý lấy từ THAM SỐ theo mức, tính từ LÚC XẢY RA, và mức nặng hơn thì hạn NGẮN hơn
  S5  dòng xử lý đầu tiên cũng là lúc ghi nhận có người nhận việc
  S6  đóng hồ sơ phải có nhóm nguyên nhân, nguyên nhân viết ra và kết quả
  S7  gắn chứng từ khác nhóm "chi phí tour" thì chặn
  S8  người ghi được sự cố KHÔNG mặc nhiên đóng được hồ sơ
  S9  mở lại hồ sơ đã kết luận phải có lý do, và lý do nằm lại trong nhật ký xử lý
  S10 mức 3 đẩy cảnh báo lên Ban TGĐ ngay lúc ghi
  S11 quá hạn mà CHƯA AI NHẬN thì robot cảnh báo; đang xử lý mà lâu thì không
  S12 GĐ Đội xe và TP Hướng dẫn VÀO được màn hình nhưng KHÔNG cầm được danh sách khách
"""
import os, sys
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_v7_sc.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_v7_sc.db", "test_v7_sc.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def h_dong():
    """Tài khoản ĐÓNG được hồ sơ. Cố ý không dùng cntt: cntt ghi được nhưng không kết luận được –
    xem su_co_tour.DONG và phép thử S8."""
    for u in ("tp.dieuhanh", "tgd", "chutich"):
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        if r.status_code == 200:
            return login(u)
    pytest.skip("dữ liệu mẫu không có tài khoản nào đóng được hồ sơ sự cố")


def tour_id():
    if "tour" not in CTX:
        r = client.get("/api/v1/tours", headers=login("cntt")).json()["rows"]
        rows = r if isinstance(r, list) else r.get("rows", [])
        CTX["tour"] = rows[0]["id"]
    return CTX["tour"]


BASE = {"nhom": "xe", "muc": 2, "noi_xay_ra": "Đèo Hải Vân", "so_khach_anh_huong": 24,
        "mo_ta": "Tài xế gọi về: xe thủng lốp giữa đèo, khách ngồi trên xe chờ, chưa có xe thay."}


def tao(muc=2, **kw):
    d = dict(BASE, tour_id=tour_id(), muc=muc, **kw)
    r = client.post("/api/v1/su-co-tour", json=d, headers=login("cntt"))
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ------------------------------------------------------------------ S1, S2
def test_s1_bang_rieng_tach_han_khoi_bang_su_vu_nhan_su():
    """Hai bảng khác nhau, và bảng sự cố KHÔNG có employee_id bắt buộc như bảng kỷ luật.

    Phép thử này canh đúng quyết định 10/9/2026. Nếu mai kia ai đó "gộp cho gọn" thì câu hỏi "quý này
    bao nhiêu chuyến gặp sự cố" sẽ trả về lẫn cả số lần nhân viên bị lập biên bản.
    """
    from app.models.su_co_tour import SuCoTour
    from app.models.hr import Incident
    assert SuCoTour.__tablename__ == "su_co_tour" and Incident.__tablename__ == "incidents"
    cot_sc = set(SuCoTour.__table__.columns.keys())
    assert "tour_id" in cot_sc, "sự cố tour phải gắn chuyến"
    assert "employee_id" not in cot_sc, (
        "sự cố tour KHÔNG mang employee_id: phần lớn sự cố không có ai sai. Quy lỗi cho một người là "
        "lập Sự vụ ở bảng incidents rồi gắn số hiệu qua incident_id")
    assert SuCoTour.__table__.columns["tour_id"].nullable is False
    # Chân nối sang hai bảng kia phải CÓ và phải rỗng được.
    for c in ("incident_id", "complaint_id", "payment_request_id"):
        assert c in cot_sc and SuCoTour.__table__.columns[c].nullable


def test_s2_khong_cot_tien_nao_trong_hai_bang_moi():
    """Chi phí sự cố đi qua Đề nghị chi. Một ô số tiền ở đây là đường tiền thứ hai song song cổng chi."""
    from sqlalchemy import Numeric, Float
    from app.models.su_co_tour import SuCoTour, SuCoTourXuLy
    for bang in (SuCoTour, SuCoTourXuLy):
        for c in bang.__table__.columns:
            assert not isinstance(c.type, (Numeric, Float)), (
                f"{bang.__tablename__}.{c.name} là cột số thực – bảng sự cố không được giữ tiền")
        # so_khach_anh_huong là số nguyên và KHÔNG phải tiền; tên cột nào có 'tien'/'chi_phi' thì đỏ.
        for c in bang.__table__.columns:
            assert "tien" not in c.name and "chi_phi" not in c.name, f"{bang.__tablename__}.{c.name}"


# ------------------------------------------------------------------ S3, S4
def test_s3_khong_gan_chuyen_thi_khong_lap_duoc():
    r = client.post("/api/v1/su-co-tour", json=dict(BASE, tour_id=0), headers=login("cntt"))
    assert r.status_code == 422
    r2 = client.post("/api/v1/su-co-tour", json=dict(BASE, tour_id=tour_id(), mo_ta=" "),
                     headers=login("cntt"))
    assert r2.status_code == 422, "thiếu nguyên văn lời người báo thì không lập được"


def test_s4_han_lay_tu_tham_so_tinh_tu_luc_xay_ra_va_muc_nang_thi_han_ngan():
    xr = (datetime.now() - timedelta(hours=3)).replace(microsecond=0)
    h = login("cntt")
    i1 = tao(muc=1, xay_ra_luc=xr.isoformat())
    i3 = tao(muc=3, xay_ra_luc=xr.isoformat())
    a = client.get(f"/api/v1/su-co-tour/{i1}", headers=h).json()
    b = client.get(f"/api/v1/su-co-tour/{i3}", headers=h).json()
    h1 = datetime.fromisoformat(a["han_xu_ly"]); h3 = datetime.fromisoformat(b["han_xu_ly"])
    assert h3 < h1, "mức nặng hơn thì hạn phải NGẮN hơn – khách đang đứng ngoài đường"
    # Tính từ lúc xảy ra: mức 1 mặc định 24 giờ kể từ mốc ấy, KHÔNG phải 24 giờ kể từ lúc gõ vào máy.
    assert abs((h1 - (xr + timedelta(hours=24))).total_seconds()) < 90, (
        "hạn phải tính từ lúc xảy ra – tính từ lúc ghi thì báo muộn ba tiếng là tự dời hạn ba tiếng")
    assert b["qua_han"] is True, "mức 3 xảy ra 3 giờ trước, chưa ai nhận – phải là quá hạn"


def test_s4b_danh_sach_ncc_di_qua_meta_va_chi_gom_ma_va_ten():
    """Màn hình KHÔNG gọi thẳng nhóm API nhà cung cấp – nó nhận mã + tên qua meta.

    Gọi thẳng là mở cơ cấu chi phí nhà cung cấp cho khối Kinh doanh, vốn mở được màn hình này. Phép
    thử canh cả hai chiều: danh sách phải CÓ (không thì ô chọn thành ô chết), và mỗi phần tử chỉ được
    mang đúng ba khoá – thêm giá hay số tài khoản vào đây là làm đúng cái việc vừa tránh.
    """
    m = client.get("/api/v1/su-co-tour/meta", headers=login("cntt")).json()
    assert "nha_cung_cap" in m
    for x in m["nha_cung_cap"]:
        assert set(x) == {"id", "name", "code"}, f"meta lộ thêm trường: {set(x) - {'id', 'name', 'code'}}"
    if not m["nha_cung_cap"]:
        return
    ncc = m["nha_cung_cap"][0]
    sid = tao(supplier_id=ncc["id"])
    d = client.get(f"/api/v1/su-co-tour/{sid}", headers=login("cntt")).json()
    assert d["supplier_id"] == ncc["id"] and d["supplier_name"] == ncc["name"]
    # Nhà cung cấp không có thật thì chặn ngay lúc lập, không để hồ sơ trỏ vào khoảng không.
    assert client.post("/api/v1/su-co-tour", json=dict(BASE, tour_id=tour_id(), supplier_id=999_999),
                       headers=login("cntt")).status_code == 422


# ------------------------------------------------------------------ S5
def test_s5_dong_xu_ly_dau_tien_cung_la_luc_nhan_viec():
    sid = tao()
    h = login("cntt")
    truoc = client.get(f"/api/v1/su-co-tour/{sid}", headers=h).json()
    assert truoc["nhan_luc"] is None and truoc["trang_thai"] == "moi"
    assert client.post(f"/api/v1/su-co-tour/{sid}/xu-ly", json={"noi_dung": "Đã gọi xe thay từ Đà Nẵng"},
                       headers=h).status_code == 200
    sau = client.get(f"/api/v1/su-co-tour/{sid}", headers=h).json()
    assert sau["nhan_luc"] and sau["trang_thai"] == "dang_xu_ly" and sau["nguoi_xu_ly"] == "cntt"
    assert sau["qua_han"] is False, "đã có người nhận thì không còn là 'quá hạn chưa ai nhận'"
    assert len(sau["xu_ly"]) == 1
    # Dòng trống không được ghi – một dòng rỗng trong nhật ký xử lý không nói được gì.
    assert client.post(f"/api/v1/su-co-tour/{sid}/xu-ly", json={"noi_dung": "  "},
                       headers=h).status_code == 422


# ------------------------------------------------------------------ S6, S7, S8
def test_s6_dong_ho_so_phai_co_nguyen_nhan_va_ket_qua():
    sid = tao()
    h = login("cntt")
    client.post(f"/api/v1/su-co-tour/{sid}/xu-ly", json={"noi_dung": "Đã điều xe thay"}, headers=h)
    hd = h_dong()
    # thiếu nhóm nguyên nhân
    assert client.post(f"/api/v1/su-co-tour/{sid}/dong",
                       json={"nguyen_nhan_nhom": "", "nguyen_nhan": "x" * 30, "ket_qua": "xong"},
                       headers=hd).status_code == 422
    # nguyên nhân quá ngắn – "do khách quan" không phải một nguyên nhân
    assert client.post(f"/api/v1/su-co-tour/{sid}/dong",
                       json={"nguyen_nhan_nhom": "do_ncc", "nguyen_nhan": "do khách quan",
                             "ket_qua": "xong"}, headers=hd).status_code == 422
    # thiếu kết quả cho khách
    assert client.post(f"/api/v1/su-co-tour/{sid}/dong",
                       json={"nguyen_nhan_nhom": "do_ncc", "nguyen_nhan": "Lốp xe của nhà xe đã mòn quá hạn thay",
                             "ket_qua": ""}, headers=hd).status_code == 422
    ok = client.post(f"/api/v1/su-co-tour/{sid}/dong",
                     json={"nguyen_nhan_nhom": "do_ncc",
                           "nguyen_nhan": "Lốp xe của nhà xe đã mòn quá hạn thay, không kiểm trước chuyến",
                           "ket_qua": "Xe thay tới sau 55 phút, đoàn tới điểm nghỉ trễ 1 giờ, đã xin lỗi khách"},
                     headers=hd)
    assert ok.status_code == 200, ok.text
    d = client.get(f"/api/v1/su-co-tour/{sid}", headers=h).json()
    assert d["trang_thai"] == "dong" and d["nguyen_nhan_nhom"] == "do_ncc"


def test_s7_gan_chung_tu_khac_nhom_chi_phi_tour_thi_chan():
    """Chi phí sự cố là chi phí CỦA CHUYẾN. Gắn một khoản chi hành chính vào đây là làm giá vốn chuyến
    sai mà không ai thấy.

    Kiểm ở tầng dịch vụ chứ không qua màn hình: dữ liệu mẫu không chắc có sẵn đề nghị chi ngoài nhóm
    chi phí tour, mà một phép thử bỏ qua chính mình khi thiếu dữ liệu thì không canh được gì.
    """
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    from app.services import su_co_tour as SC
    with SessionLocal() as db:
        pr = PaymentRequest(code="DCTEST-9001", category="hanh_chinh", supplier_name="Văn phòng phẩm ABC",
                            amount=1_500_000, description="Mua giấy in", created_by="cntt")
        db.add(pr); db.flush()
        with pytest.raises(ValueError) as e:
            SC._kiem_chung_tu(db, pr.id)
        assert "Chi phí tour" in str(e.value)
        pr.category = "chi_tour"
        db.flush()
        SC._kiem_chung_tu(db, pr.id)      # cùng chứng từ, đúng nhóm thì qua
        db.rollback()


def test_s8_nguoi_ghi_duoc_khong_mac_nhien_dong_duoc():
    """Kết luận nguyên nhân kéo theo việc đòi nhà cung cấp hoặc lập sự vụ. Không để người vừa gây ra
    sự cố tự kết luận về nó."""
    from app.services import su_co_tour as SC
    assert set(SC.DONG) < set(SC.GHI) or all(v in SC.GHI for v in SC.DONG), \
        "danh sách đóng phải nằm trong danh sách ghi"
    assert len(SC.DONG) < len(SC.GHI), "đóng hồ sơ phải hẹp hơn ghi hồ sơ"
    for vai in ("nv_kd", "tn_kd", "nv_dh"):
        assert vai in SC.GHI and vai not in SC.DONG, f"{vai} ghi được nhưng không được tự kết luận"


# ------------------------------------------------------------------ S9
def test_s9_mo_lai_phai_co_ly_do_va_ly_do_nam_lai_trong_nhat_ky():
    sid = tao()
    h = login("cntt")
    hd = h_dong()
    client.post(f"/api/v1/su-co-tour/{sid}/xu-ly", json={"noi_dung": "Đã xử lý"}, headers=h)
    client.post(f"/api/v1/su-co-tour/{sid}/dong",
                json={"nguyen_nhan_nhom": "bat_kha_khang",
                      "nguyen_nhan": "Mưa lớn gây sạt lở, đường bị chặn trong hai giờ",
                      "ket_qua": "Đoàn đổi lộ trình, tới nơi trễ 2 giờ"}, headers=hd)
    # Người ghi được sự cố KHÔNG mở lại được hồ sơ đã kết luận – cùng hàng rào với việc đóng.
    assert client.post(f"/api/v1/su-co-tour/{sid}/mo-lai", json={"ly_do": "x" * 30},
                       headers=h).status_code == 403
    assert client.post(f"/api/v1/su-co-tour/{sid}/mo-lai", json={"ly_do": "nhầm"},
                       headers=hd).status_code == 422
    ly = "Khách gửi thêm ảnh cho thấy xe đã hỏng từ trước khi trời mưa"
    assert client.post(f"/api/v1/su-co-tour/{sid}/mo-lai", json={"ly_do": ly},
                       headers=hd).status_code == 200
    d = client.get(f"/api/v1/su-co-tour/{sid}", headers=h).json()
    assert d["trang_thai"] == "dang_xu_ly" and not d["closed_by"]
    assert any(ly in x["noi_dung"] for x in d["xu_ly"]), (
        "lý do mở lại phải nằm lại trong nhật ký xử lý, không chỉ trong nhật ký kiểm toán")


# ------------------------------------------------------------------ S10, S11
def test_s10_muc3_day_canh_bao_len_ban_tgd_ngay_luc_ghi():
    from app.db.session import SessionLocal
    from app.models.core import Alert
    from sqlalchemy import select
    sid = tao(muc=3, mo_ta="Khách bị ngã cầu thang khách sạn, xe cấp cứu đã tới, HDV đi cùng vào viện.")
    code = client.get(f"/api/v1/su-co-tour/{sid}", headers=login("cntt")).json()["code"]
    with SessionLocal() as db:
        a = db.execute(select(Alert).where(Alert.kind == "su_co_tour_muc3", Alert.ref == code)).scalars().first()
    assert a is not None, "sự cố mức 3 phải báo ngay, không chờ ai mở màn hình"
    assert a.level == "red" and "tgd" in a.to_roles and "chutich" in a.to_roles


def test_s11_robot_chi_canh_bao_su_co_chua_ai_nhan():
    from app.db.session import SessionLocal
    from app.models.core import Alert
    from app.models.su_co_tour import SuCoTour
    from app.services import su_co_tour as SC
    from sqlalchemy import select
    xr = (datetime.now() - timedelta(days=2)).replace(microsecond=0)
    chua_nhan = tao(muc=2, xay_ra_luc=xr.isoformat())
    dang_lam = tao(muc=2, xay_ra_luc=xr.isoformat())
    client.post(f"/api/v1/su-co-tour/{dang_lam}/xu-ly", json={"noi_dung": "Đang thương lượng với khách sạn"},
                headers=login("cntt"))
    with SessionLocal() as db:
        SC.robot_su_co(db); db.commit()
        ma_chua = db.get(SuCoTour, chua_nhan).code
        ma_dang = db.get(SuCoTour, dang_lam).code
        refs = {a.ref for a in db.execute(select(Alert).where(Alert.kind == "su_co_tour_qua_han")).scalars()}
        assert ma_chua in refs, "sự cố quá hạn mà chưa ai nhận thì phải báo"
        assert ma_dang not in refs, (
            "sự cố ĐANG được xử lý mà lâu là chuyện bình thường – một chuyến hỏng xe giữa đèo không "
            "xong trong hai tiếng. Thứ không bình thường là không ai cầm")
        # Chạy lần hai không nhân đôi cảnh báo đang mở.
        n = len(list(db.execute(select(Alert).where(Alert.kind == "su_co_tour_qua_han")).scalars()))
        SC.robot_su_co(db); db.commit()
        assert len(list(db.execute(select(Alert).where(Alert.kind == "su_co_tour_qua_han")).scalars())) == n


# ------------------------------------------------------------------ S12
def test_s12_doi_xe_va_huong_dan_vao_duoc_ma_khong_cam_danh_sach_khach():
    """Anh Tuấn chốt 10/9/2026: mở màn hình Sự cố tour cho GĐ Đội xe và TP Hướng dẫn.

    Mở màn hình KHÔNG phải là mở dữ liệu khách. Ranh giới cả ma trận giữ từ đầu với hai vai này là
    "không xem dữ liệu khách, booking" – và nó vẫn đứng: họ đọc được sự cố, ghi được sự cố, nhưng ô
    chọn booking trả về MÃ chứ không trả tên, và bốn nhóm API kia vẫn đóng.

    Người sửa xe không cần biết ai ngồi trên xe. Cần biết xe nào, chuyến nào, hỏng gì.
    """
    from app.services import access as AC
    from app.api.v1 import su_co_tour as API
    for vai in ("gd_doi_xe", "tp_hd"):
        assert vai in AC.MENU_ROLES["/su-co-tour"], f"{vai} phải mở được màn hình"
        # Hai vai này dùng DANH SÁCH CHO PHÉP – thiếu tên ở đó thì dòng menu trên chỉ nới quyền API
        # mà họ vẫn không thấy mục menu. Đúng cái bẫy bản đầu của đợt này mắc phải.
        assert "/su-co-tour" in AC.RESTRICTED_ROLE_MENUS[vai], (
            f"{vai} khai quyền màn hình mà không có trong danh sách cho phép – nới quyền mà không ai "
            "dùng được")
        assert vai not in API.KHACH, f"{vai} không được cầm tên khách"
        # Phạm vi API nới đúng MỘT nhóm, không kéo theo booking / khiếu nại / nhà cung cấp / chuyến.
        pv = set(AC.pham_vi_day_du(vai))
        assert "/api/v1/su-co-tour" in pv
        for cam in ("/api/v1/bookings", "/api/v1/khieu-nai", "/api/v1/suppliers", "/api/v1/payment-requests"):
            assert cam not in pv, f"{vai} không được chạm {cam} chỉ vì mở màn hình Sự cố tour"

    # Bản đồ màn hình → API phải khớp: đúng hai nhóm.
    assert set(AC.MAN_HINH_API["/su-co-tour"]) == {"/api/v1/su-co-tour", "/api/v1/tep"}


def _tao_tai_khoan(username, vai, ten):
    """Dữ liệu mẫu không có tài khoản gd_doi_xe và tp_hd (ghi nhận 08/9/2026), nên dựng tại chỗ.

    Bỏ qua phép thử vì thiếu tài khoản thì đúng chỗ cần canh nhất lại là chỗ không bao giờ chạy.
    """
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.core.security import hash_password
    from sqlalchemy import select
    with SessionLocal() as db:
        if db.execute(select(User).where(User.username == username)).scalars().first() is None:
            db.add(User(username=username, full_name=ten, role=vai, department="kiem_thu",
                        staff_code=username.upper()[:10], password_hash=hash_password("Vtos@Demo#2026"),
                        active=True))
            db.commit()
    r = client.post("/api/v1/auth/login", data={"username": username, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_s12b_o_chon_booking_giau_ten_khach_voi_vai_tro_khong_co_quyen():
    """Cùng một đường dẫn, hai vai trò, hai kết quả khác nhau – và khác đúng ở chỗ tên khách."""
    tid = tour_id()
    co = client.get(f"/api/v1/su-co-tour/chon/booking?tour_id={tid}", headers=login("cntt")).json()
    assert co["co_ten_khach"] is True

    for username, vai, ten in (("gd.doixe.v7", "gd_doi_xe", "GĐ đội xe kiểm thử V7"),
                               ("tp.huongdan.v7", "tp_hd", "TP Hướng dẫn kiểm thử V7")):
        h = _tao_tai_khoan(username, vai, ten)
        # 1. VÀO được màn hình và đọc được sự cố.
        ds = client.get("/api/v1/su-co-tour", headers=h)
        assert ds.status_code == 200, f"{vai} phải mở được màn hình: {ds.text}"
        m = client.get("/api/v1/su-co-tour/meta", headers=h).json()
        assert m["xem_duoc_ten_khach"] is False
        assert m["tours"], "vẫn phải chọn được chuyến – ô chọn rỗng là ô chết"
        assert m["nha_cung_cap"] is not None

        # 2. GHI được sự cố – đây là cả lý do mở màn hình cho họ.
        r = client.post("/api/v1/su-co-tour", json=dict(BASE, tour_id=tid, nhom="xe",
                                                        mo_ta=f"{ten} báo: xe nổ lốp, đang chờ xe thay."),
                        headers=h)
        assert r.status_code == 200, f"{vai} phải ghi được sự cố: {r.text}"

        # 3. KHÔNG cầm được tên khách, và không kết luận được hồ sơ.
        d = client.get(f"/api/v1/su-co-tour/chon/booking?tour_id={tid}", headers=h)
        assert d.status_code == 200, d.text
        j = d.json()
        assert j["co_ten_khach"] is False
        assert all("khach" not in x for x in j["rows"]), "ô chọn booking lộ tên khách cho vai trò hẹp"
        assert client.get("/api/v1/su-co-tour/chon/ket-luan", headers=h).status_code == 403
        assert client.post(f"/api/v1/su-co-tour/{r.json()['id']}/dong",
                           json={"nguyen_nhan_nhom": "do_ncc", "nguyen_nhan": "x" * 30,
                                 "ket_qua": "xong"}, headers=h).status_code == 403

        # 4. Bốn nhóm API kia vẫn đóng – hàng rào phạm vi P2 chặn ở vòng ngoài.
        #
        # Nhận 404 cũng là ĐÓNG: /api/v1/suppliers không phải đường dẫn đang có (nhà cung cấp phục vụ
        # ở tiền tố khác). Điều phép thử canh là "không mở ra", chứ không phải mã lỗi cụ thể – nên
        # nhận cả hai, và phép thử S12 ở trên đã kiểm thẳng tập phạm vi để không ai lách bằng cách
        # đổi tên đường dẫn.
        for cam in ("/api/v1/bookings", "/api/v1/khieu-nai", "/api/v1/suppliers", "/api/v1/tours"):
            ma = client.get(cam, headers=h).status_code
            assert ma in (403, 404), (
                f"{vai} chạm được {cam} (mã {ma}) chỉ vì mở màn hình Sự cố tour")
