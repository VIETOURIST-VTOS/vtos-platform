"""TC-107 · Bộ gửi chuyển đổi ngược về Meta — mắt xích cuối của vòng tròn Facebook.

TC-103 bắt được cái chạm, TC-105 xếp hàng đợi, TC-106 nối webhook. Còn thiếu cái miệng: nói
ngược lại cho Meta "người bạn mang tới đã mua tour, trị giá bằng này tiền". Tháng 9/2026
Facebook là kênh doanh thu lớn nhất của Vietourist — 3,24 tỷ — và Meta không biết một đồng nào.

Mọi phép thử ở đây chạy bằng MÁY CHỦ GIẢ. Không một byte nào ra Internet: phép thử gọi mạng
thật thì hỏng theo đường truyền, và tệ hơn — nó bắn dữ liệu thử lên tài khoản quảng cáo thật.

  C1  CHƯA CÓ TOKEN thì không gọi mạng và KHÔNG đụng vào trạng thái dòng nào
  C2  số điện thoại Việt Nam phải có mã quốc gia 84 trước khi băm — bỏ số 0 mà quên 84 là
      khớp 0% mà Meta vẫn trả 200
  C3  mã lead của Meta KHÔNG được băm
  C4  `test_event_code` nằm NGANG HÀNG với `data`, không nằm trong từng sự kiện
  C5  quá 7 ngày thì đánh dấu `qua_han` và KHÔNG gửi
  C6  dòng của nền tảng khác nằm nguyên — không cướp việc của bộ gửi Google
  C7  `event_id` ổn định qua các lần chạy, nếu không Meta đếm một booking thành nhiều
  C8  gửi được thì ghi `da_gui`, doanh thu ĐẦY ĐỦ, tiền tệ VND
  C9  loại mã Meta không khớp được thì `bo_qua` CÓ GHI LÝ DO
  C10 cửa xem cấu hình không để lộ token, và đứng sau hàng rào vai trò
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc107.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "robot-tc107"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc107.db", "test_tc107.db-journal"):
    if os.path.exists(f): os.remove(f)

import hashlib                                      # noqa: E402
from datetime import date, datetime, timedelta      # noqa: E402
import pytest                                       # noqa: E402
from fastapi.testclient import TestClient           # noqa: E402
from app.main import app                            # noqa: E402
from app.core.config import settings                # noqa: E402
from app.services import gui_meta as GM             # noqa: E402

client = TestClient(app)
KHOA = {"X-Robot-Token": "robot-tc107"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(autouse=True)
def _don_dep():
    """Trả hàm gửi và cấu hình về nguyên trạng sau MỖI phép thử.

    `dat_ham` và `settings` là trạng thái toàn cục. Một phép thử quên trả lại thì phép thử sau
    chạy với máy chủ giả của phép thử trước — và nó sẽ XANH vì lý do sai.
    """
    cu = {k: getattr(settings, k) for k in
          ("FB_DATASET_ID", "FB_CAPI_TOKEN", "FB_CAPI_TEST_EVENT_CODE",
           "FB_CAPI_ACTION_SOURCE", "FB_CAPI_EVENT_NAME")}
    yield
    GM.dat_ham()
    for k, v in cu.items():
        setattr(settings, k, v)


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _bat_cau_hinh(ma_thu: str = ""):
    settings.FB_DATASET_ID = "1234567890"
    settings.FB_CAPI_TOKEN = "token-gia-cua-phep-thu"
    settings.FB_CAPI_TEST_EVENT_CODE = ma_thu


class MayChuGia:
    """Đứng thay Meta. Ghi lại từng gói nhận được để phép thử soi."""

    def __init__(self, ok: bool = True, loi: str = ""):
        self.ok, self.loi, self.goi = ok, loi, []

    def __call__(self, goi: dict) -> dict:
        self.goi.append(goi)
        if self.ok:
            return {"ok": True, "tra_loi": '{"events_received":1,"fbtrace_id":"gia"}'}
        return {"ok": False, "tra_loi": '{"error":{"message":"gia"}}', "loi": self.loi or "HTTP 400"}


_dem = {"n": 0}


def _dung(sdt: str, tien, loai_ma: str, ma: str, nen_tang: str = "facebook", lui_ngay: int = 0):
    """Một khách đã chốt tour, có dấu quảng cáo, đã xếp vào hàng đợi.

    Trả `(id dòng chuyển đổi, mã booking)`. Phải trả cả mã booking vì hàng đợi DÙNG CHUNG cho
    cả tệp: phép thử trước để lại dòng chờ, nên một phép thử nói "máy chủ giả không nhận gói
    nào" là nói sai — nó phải nói "không nhận gói nào CỦA BOOKING NÀY". Khẳng định rộng quá
    thì phép thử đỏ vì lý do sai, và lần sau người ta sẽ nới nó ra cho qua.
    """
    from app.models.core import Tour, Booking, User
    from app.models.crm import Lead
    from app.models.quang_cao import ChuyenDoiGuiDi
    from app.services import dau_quang_cao as DQ
    from app.services import chuyen_doi_di as CD
    _dem["n"] += 1
    ma_bk = f"BK107{_dem['n']:03d}"
    db = _db()
    try:
        u = db.query(User).filter(User.username == "nguoi_thu_107").first()
        if not u:
            from app.core.security import hash_password
            u = User(username="nguoi_thu_107", full_name="Nguoi thu 107", role="nv_kd",
                     password_hash=hash_password("Vtos@Demo#2026"), active=True)
            db.add(u); db.commit(); db.refresh(u)
        t = db.query(Tour).filter(Tour.code == "T107").first()
        if not t:
            t = Tour(code="T107", name="Tour thu TC-107", tour_type="le_noi_dia",
                     operator_id=u.id, start_date=date(2026, 11, 2),
                     end_date=date(2026, 11, 5), status="mo")
            db.add(t); db.commit(); db.refresh(t)
        chot = datetime.now() - timedelta(days=lui_ngay)
        b = Booking(code=ma_bk, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                    customer_name="Khach thu", customer_phone=sdt, source="vtos", pax=2,
                    amount=tien, cancelled=False)
        db.add(b); db.commit(); db.refresh(b)
        l = Lead(phone=sdt, name="Khach thu", channel="Facebook",
                 lead_month=f"{chot:%Y-%m}", booking_id=b.id, converted_at=chot,
                 status="chot", created_by="phepthu")
        db.add(l); db.commit(); db.refresh(l)
        DQ.ghi(db, {"nen_tang": nen_tang, "loai_ma": loai_ma, "ma": ma, "sdt": sdt,
                    "cham_luc": f"{chot:%Y-%m-%d %H:%M:%S}"})
        db.commit()
        CD.sinh(db)
        c = db.query(ChuyenDoiGuiDi).filter(ChuyenDoiGuiDi.ma_booking == ma_bk).first()
        return c.id, ma_bk
    finally:
        db.close()


def _dong(cid: int):
    from app.models.quang_cao import ChuyenDoiGuiDi
    db = _db()
    try:
        c = db.get(ChuyenDoiGuiDi, cid)
        return {"trang_thai": c.trang_thai, "lan_thu": c.lan_thu, "loi_cuoi": c.loi_cuoi,
                "khoa": c.khoa_chong_trung, "doanh_thu": c.doanh_thu}
    finally:
        db.close()


_TOK: dict = {}


def _dn(u: str):
    """Đăng nhập. Tệp này tắt seed nên tạo thẳng một tài khoản – giống test_tc103."""
    if u not in _TOK:
        from app.models.core import User
        from app.core.security import hash_password
        db = _db()
        try:
            if not db.query(User).filter(User.username == u).first():
                db.add(User(username=u, full_name=u, role=u,
                            password_hash=hash_password("Vtos@Demo#2026"), active=True))
                db.commit()
        finally:
            db.close()
        _TOK[u] = client.post("/api/v1/auth/login",
                              data={"username": u, "password": "Vtos@Demo#2026"}
                              ).json()["access_token"]
    return {"Authorization": f"Bearer {_TOK[u]}"}


def _goi_cua(gia, ma_bk: str) -> list:
    """Những gói máy chủ giả nhận được CHO RIÊNG booking này."""
    return [g for g in gia.goi if ma_bk in g["data"][0]["event_id"]]


def _chay(**kw):
    db = _db()
    try:
        return GM.gui(db, **kw)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_c1_chua_co_token_thi_khong_goi_mang_va_khong_doi_trang_thai_dong_nao():
    """Chốt an toàn số một của cả vòng.

    Nếu bộ gửi "cố thử xem sao" khi thiếu cấu hình, nó sẽ đánh dấu một loạt dòng là lỗi, và
    ngày token về thì chẳng ai biết những dòng ấy đáng lẽ gửi được. Không đổi trạng thái thì
    lượt chạy đầu tiên sau khi dán token cuốn hết — không phải nhớ gì thêm.
    """
    settings.FB_DATASET_ID = ""
    settings.FB_CAPI_TOKEN = ""
    cid, ma_bk = _dung("0909000001", 12_000_000, "leadgen_id", "7001")
    gia = MayChuGia()
    GM.dat_ham(gia)

    kq = _chay()

    assert kq["san_sang"] is False
    assert set(kq["thieu"]) == {"FB_DATASET_ID", "FB_CAPI_TOKEN"}
    assert gia.goi == [], "Thiếu cấu hình mà vẫn gọi ra Meta"
    assert _dong(cid)["trang_thai"] == "cho_gui", "Thiếu cấu hình mà đã đổi trạng thái dòng"
    assert kq["dang_cho"] >= 1


def test_c2_so_dien_thoai_viet_nam_phai_co_ma_quoc_gia_84_truoc_khi_bam():
    """Lỗi im lặng tệ nhất ở đây.

    Meta bảo "bỏ số 0 đứng đầu, và số phải có mã quốc gia". Làm nửa vế đầu mà quên vế sau thì
    `0909123456` thành `909123456`: Meta vẫn nhận, vẫn trả 200, và khớp được đúng 0%. Không có
    một thông báo lỗi nào trên đời báo chuyện đó — chỉ có báo cáo quảng cáo trống trơn.
    """
    dung = hashlib.sha256(b"84909123456").hexdigest()
    sai = hashlib.sha256(b"909123456").hexdigest()

    assert GM.bam_sdt("0909123456") == dung
    assert GM.bam_sdt("0909123456") != sai
    # Cùng một số viết bốn kiểu phải ra cùng một mã băm, nếu không Meta coi là bốn người.
    assert GM.bam_sdt("+84 909 123 456") == dung
    assert GM.bam_sdt("84909123456") == dung
    assert GM.bam_sdt("(090) 912-3456") == dung
    # Rỗng vào thì rỗng ra — KHÔNG băm chuỗi rỗng rồi gửi một mã băm vô nghĩa lên Meta.
    assert GM.bam_sdt("") == ""
    assert GM.bam_sdt("123") == ""


def test_c3_ma_lead_cua_meta_khong_duoc_bam():
    """`lead_id` do chính Meta cấp nên Meta đọc thẳng. Băm nó là khớp 0% mà vẫn trả 200."""
    from app.models.quang_cao import ChuyenDoiGuiDi, DauQuangCao
    cd = ChuyenDoiGuiDi(nen_tang="facebook", loai_ma="leadgen_id", ma="987654321",
                        ma_booking="BKX", doanh_thu=5_000_000, tien_te="VND",
                        chot_luc=datetime.now(), khoa_chong_trung="facebook:BKX:1")
    dau = DauQuangCao(nen_tang="facebook", loai_ma="leadgen_id", ma="987654321",
                      sdt="0909123456", khoa_chong_trung="k")

    goi = GM.goi_tin(cd, dau)
    nguoi = goi["data"][0]["user_data"]

    assert nguoi["lead_id"] == 987654321
    assert isinstance(nguoi["lead_id"], int), "Meta đòi số nguyên, không phải chuỗi"
    # Số điện thoại thì NGƯỢC LẠI – phải băm, không được gửi thô.
    assert nguoi["ph"] == [hashlib.sha256(b"84909123456").hexdigest()]
    assert "0909123456" not in str(goi), "Số điện thoại thô lọt ra ngoài gói gửi"


def test_c4_ma_thu_nam_ngang_hang_voi_data_khong_nam_trong_su_kien():
    """Đặt sai chỗ thì Meta vẫn nhận gói, nhưng Trình kiểm tra sự kiện không hiện gì — và CNTT
    sẽ đi tìm lỗi ở chỗ không có lỗi."""
    from app.models.quang_cao import ChuyenDoiGuiDi
    settings.FB_CAPI_TEST_EVENT_CODE = "TEST12345"
    cd = ChuyenDoiGuiDi(nen_tang="facebook", loai_ma="leadgen_id", ma="1", ma_booking="BKY",
                        doanh_thu=1_000_000, tien_te="VND", chot_luc=datetime.now(),
                        khoa_chong_trung="facebook:BKY:1")

    goi = GM.goi_tin(cd, None)

    assert goi["test_event_code"] == "TEST12345"
    assert "test_event_code" not in goi["data"][0]
    # Không bật mã thử thì KHÔNG có khoá ấy, chứ không phải khoá rỗng.
    settings.FB_CAPI_TEST_EVENT_CODE = ""
    assert "test_event_code" not in GM.goi_tin(cd, None)


def test_c5_qua_bay_ngay_thi_danh_dau_qua_han_va_khong_gui():
    """Meta chỉ nhận `event_time` trong 7 ngày. Gửi muộn không phải là kém chính xác — là bị
    TỪ CHỐI. Gửi để bị từ chối chỉ tổ làm bẩn bảng lỗi và che mất lỗi thật."""
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909000005", 30_000_000, "leadgen_id", "7005", lui_ngay=9)
    gia = MayChuGia()
    GM.dat_ham(gia)

    kq = _chay()

    assert _goi_cua(gia, ma_bk) == [], "Dòng quá hạn mà vẫn gửi lên Meta"
    d = _dong(cid)
    assert d["trang_thai"] == "qua_han"
    assert "7 ngày" in d["loi_cuoi"], "Quá hạn mà không ghi rõ lý do để sau này đếm được"
    assert kq["qua_han"] >= 1
    # Chưa tới hạn thì vẫn gửi bình thường — hàng rào không được chặn nhầm.
    cid2, _ = _dung("0909000006", 20_000_000, "leadgen_id", "7006", lui_ngay=3)
    GM.dat_ham(MayChuGia())
    _chay()
    assert _dong(cid2)["trang_thai"] == "da_gui"


def test_c6_khong_dung_vao_dong_cua_nen_tang_khac():
    """Bộ gửi Meta cầm nhầm một dòng gclid thì nó đánh dấu "bỏ qua" — tức là cướp việc của bộ
    gửi Google, và dòng ấy không bao giờ được gửi đi đâu nữa."""
    _bat_cau_hinh()
    cid_g, _ = _dung("0909000007", 40_000_000, "gclid", "Cj0KC-gia", nen_tang="google")
    gia = MayChuGia()
    GM.dat_ham(gia)

    _chay()

    assert _dong(cid_g)["trang_thai"] == "cho_gui", "Bộ gửi Meta đã đụng vào dòng của Google"
    assert all(g["data"][0]["event_id"].startswith("facebook:") for g in gia.goi)


def test_c7_event_id_on_dinh_qua_cac_lan_chay():
    """Lấy thời gian hiện tại làm `event_id` thì mỗi lần chạy lại ra một mã mới, Meta không loại
    trùng được, và một booking đếm thành nhiều. Mã phải suy từ dữ liệu, không từ đồng hồ."""
    from app.models.quang_cao import ChuyenDoiGuiDi
    cd = ChuyenDoiGuiDi(nen_tang="facebook", loai_ma="leadgen_id", ma="55", ma_booking="BKZ",
                        doanh_thu=9_000_000, tien_te="VND", chot_luc=datetime.now(),
                        khoa_chong_trung="facebook:BKZ:12")

    a = GM.goi_tin(cd, None)["data"][0]["event_id"]
    b = GM.goi_tin(cd, None)["data"][0]["event_id"]

    assert a == b == "facebook:BKZ:12"
    assert GM.CUA_SO_CHONG_TRUNG_GIO == 48, \
        "Cửa sổ loại trùng của Meta là 48 giờ – gửi lại muộn hơn thì bị đếm hai lần"


def test_c8_gui_duoc_thi_ghi_da_gui_voi_doanh_thu_day_du_va_vnd():
    """Mỗi nền tảng dự phần nhận giá trị ĐẦY ĐỦ, không chia — lý do đầy đủ ở docstring bảng
    `ChuyenDoiGuiDi`. Chia ra thì Meta ra giá thầu thấp hơn giá trị thật của khách."""
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909000008", 123_456_789, "leadgen_id", "7008")
    gia = MayChuGia()
    GM.dat_ham(gia)

    kq = _chay()

    assert kq["san_sang"] is True and kq["da_gui"] >= 1
    assert _dong(cid)["trang_thai"] == "da_gui"
    g = _goi_cua(gia, ma_bk)
    assert g, "Không thấy gói nào của booking này"
    sk = g[0]["data"][0]
    assert sk["custom_data"]["value"] == 123_456_789.0, "Doanh thu bị chia hoặc làm tròn"
    assert sk["custom_data"]["currency"] == "VND"
    assert sk["event_name"] == "Purchase"
    assert isinstance(sk["event_time"], int)
    assert sk["action_source"] in {"email", "website", "app", "phone_call", "chat",
                                   "physical_store", "system_generated",
                                   "business_messaging", "other"}


def test_c9_loai_ma_meta_khong_khop_duoc_thi_bo_qua_co_ghi_ly_do():
    """Bỏ qua CÓ GHI LÝ DO khác hẳn bỏ qua im lặng: cái sau thì sáu tháng nữa không ai biết vì
    sao thiếu, và con số chênh lệch lại thành một chỗ mù mới."""
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909000009", 7_000_000, "ma_khuyen_mai", "DHT9-123")
    gia = MayChuGia()
    GM.dat_ham(gia)

    _chay()

    d = _dong(cid)
    assert d["trang_thai"] == "bo_qua"
    assert "ma_khuyen_mai" in d["loi_cuoi"]
    assert _goi_cua(gia, ma_bk) == []


def test_c9b_gui_loi_thi_giu_dong_lai_de_gui_lai():
    """Lỗi KHÔNG xoá dòng. Xoá là mất tiền mà không ai đếm được."""
    _bat_cau_hinh()
    cid, _ = _dung("0909000010", 8_000_000, "leadgen_id", "7010")
    GM.dat_ham(MayChuGia(ok=False, loi="HTTP 400"))

    kq = _chay()

    d = _dong(cid)
    assert kq["loi"] >= 1
    assert d["trang_thai"] == "loi" and d["lan_thu"] == 1
    assert d["doanh_thu"] == 8_000_000


def test_c10_cua_cau_hinh_khong_lo_token_va_dung_sau_hang_rao_vai_tro():
    """Cửa này in ra màn hình cho người xem, nên nó chỉ được nói CÓ hay KHÔNG có token."""
    _bat_cau_hinh()
    assert client.get("/api/v1/dau-quang-cao/chuyen-doi/cau-hinh-meta").status_code in (401, 403)

    r = client.get("/api/v1/dau-quang-cao/chuyen-doi/cau-hinh-meta", headers=_dn("chutich"))

    assert r.status_code == 200
    j = r.json()
    assert j["co_token"] is True
    assert "token-gia-cua-phep-thu" not in r.text, "Token lọt ra cửa xem cấu hình"
    assert j["han_ngay"] == 7 and "sap_qua_han" in j
    # Cửa đẩy thì đứng sau khoá máy chủ, không phải sau đăng nhập người.
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/gui-meta").status_code in (401, 403)
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/gui-meta",
                       headers=KHOA).status_code == 200
