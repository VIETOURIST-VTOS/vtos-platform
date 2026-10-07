"""TC-108 · Bộ gửi chuyển đổi ngược về TikTok (Events API 2.0, nguồn CRM).

Báo cáo Marketing tháng 9/2026 nói về TikTok đúng một câu: "data nhiều nhưng tỷ lệ chốt thấp
nhất". Đó là triệu chứng của việc nền tảng chỉ được cho biết "có người điền form" – nó đi mua
thêm đúng loại ấy, rẻ và không chốt. Vòng này đổi bài học.

  C1  chưa có token thì không gọi mạng và KHÔNG đụng vào trạng thái dòng nào
  C2  số điện thoại phải là E.164 CÓ dấu cộng, và PHẢI khác mã băm của Meta
  C3  mã lead TikTok không băm, và đi kèm tên hệ CRM
  C4  gói gửi đúng nguồn "crm" với tên sự kiện TUỲ CHỈNH lấy từ cấu hình
  C5  TikTok trả HTTP 200 kèm code khác 0 là LỖI, không được tính là đã gửi
  C6  không đụng vào dòng của nền tảng khác
  C7  event_id ổn định qua các lần chạy
  C8  gửi được thì ghi da_gui, doanh thu ĐẦY ĐỦ, tiền tệ VND
  C9  không có mã lead lẫn số điện thoại thì bỏ qua CÓ GHI LÝ DO
  C10 cửa xem cấu hình không lộ token, và đứng sau hàng rào vai trò
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc108.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "robot-tc108"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc108.db", "test_tc108.db-journal"):
    if os.path.exists(f): os.remove(f)

import hashlib, io, json                           # noqa: E402
from datetime import date, datetime, timedelta     # noqa: E402
import pytest                                      # noqa: E402
from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                           # noqa: E402
from app.core.config import settings               # noqa: E402
from app.services import gui_tiktok as GT          # noqa: E402
from app.services import gui_meta as GM            # noqa: E402

client = TestClient(app)
KHOA = {"X-Robot-Token": "robot-tc108"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(autouse=True)
def _don_dep():
    """Trả hàm gửi và cấu hình về nguyên trạng sau MỖI phép thử – trạng thái toàn cục."""
    cu = {k: getattr(settings, k) for k in
          ("TT_EVENT_SET_ID", "TT_ACCESS_TOKEN", "TT_EVENT_NAME", "TT_API_VERSION")}
    yield
    GT.dat_ham()
    for k, v in cu.items():
        setattr(settings, k, v)


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _bat_cau_hinh():
    settings.TT_EVENT_SET_ID = "CRM123456"
    settings.TT_ACCESS_TOKEN = "token-gia-cua-phep-thu"


class MayChuGia:
    """Đứng thay TikTok. Ghi lại từng gói nhận được để phép thử soi."""

    def __init__(self, ok: bool = True, loi: str = ""):
        self.ok, self.loi, self.goi = ok, loi, []

    def __call__(self, goi: dict) -> dict:
        self.goi.append(goi)
        if self.ok:
            return {"ok": True, "tra_loi": '{"code":0,"message":"OK"}'}
        return {"ok": False, "tra_loi": '{"code":40001}', "loi": self.loi or "TikTok code 40001"}


_dem = {"n": 0}


def _dung(sdt: str, tien, loai_ma: str, ma: str, nen_tang: str = "tiktok", lui_ngay: int = 0):
    """Một khách đã chốt tour, có dấu quảng cáo, đã xếp hàng đợi. Trả (id dòng, mã booking)."""
    from app.models.core import Tour, Booking, User
    from app.models.crm import Lead
    from app.models.quang_cao import ChuyenDoiGuiDi
    from app.services import dau_quang_cao as DQ
    from app.services import chuyen_doi_di as CD
    _dem["n"] += 1
    ma_bk = f"BK108{_dem['n']:03d}"
    db = _db()
    try:
        u = db.query(User).filter(User.username == "nguoi_thu_108").first()
        if not u:
            from app.core.security import hash_password
            u = User(username="nguoi_thu_108", full_name="Nguoi thu 108", role="nv_kd",
                     password_hash=hash_password("Vtos@Demo#2026"), active=True)
            db.add(u); db.commit(); db.refresh(u)
        t = db.query(Tour).filter(Tour.code == "T108").first()
        if not t:
            t = Tour(code="T108", name="Tour thu TC-108", tour_type="le_noi_dia",
                     operator_id=u.id, start_date=date(2026, 11, 10),
                     end_date=date(2026, 11, 13), status="mo")
            db.add(t); db.commit(); db.refresh(t)
        chot = datetime.now() - timedelta(days=lui_ngay)
        b = Booking(code=ma_bk, tour_id=t.id, request_id=0, sales_id=u.id, created_by=u.id,
                    customer_name="Khach thu", customer_phone=sdt, source="vtos", pax=2,
                    amount=tien, cancelled=False)
        db.add(b); db.commit(); db.refresh(b)
        l = Lead(phone=sdt, name="Khach thu", channel="TikTok",
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
                "doanh_thu": c.doanh_thu, "tra_loi": c.tra_loi}
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


def _xoa_sdt_cua_dau(cid: int):
    """Bỏ số điện thoại khỏi dấu – dựng lại tình huống dấu được gắn lead bằng tay."""
    from app.models.quang_cao import ChuyenDoiGuiDi, DauQuangCao
    db = _db()
    try:
        c = db.get(ChuyenDoiGuiDi, cid)
        d = db.get(DauQuangCao, c.dau_id)
        d.sdt = ""
        db.commit()
    finally:
        db.close()


def _goi_cua(gia, ma_bk: str) -> list:
    """Những gói máy chủ giả nhận được CHO RIÊNG booking này – hàng đợi dùng chung cả tệp."""
    return [g for g in gia.goi if ma_bk in g["data"][0]["event_id"]]


def _chay(**kw):
    db = _db()
    try:
        return GT.gui(db, **kw)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_c1_chua_co_token_thi_khong_goi_mang_va_khong_doi_trang_thai():
    settings.TT_EVENT_SET_ID = ""
    settings.TT_ACCESS_TOKEN = ""
    cid, _ = _dung("0909100001", 12_000_000, "leadgen_id", "tt-8001")
    gia = MayChuGia()
    GT.dat_ham(gia)

    kq = _chay()

    assert kq["san_sang"] is False
    assert set(kq["thieu"]) == {"TT_EVENT_SET_ID", "TT_ACCESS_TOKEN"}
    assert gia.goi == [], "Thiếu cấu hình mà vẫn gọi ra TikTok"
    assert _dong(cid)["trang_thai"] == "cho_gui"


def test_c2_so_dien_thoai_e164_co_dau_cong_va_khac_han_ma_bam_cua_meta():
    """Cái bẫy đắt nhất của cả hai vòng gửi.

    TikTok đòi "+84909123456", Meta đòi "84909123456". Dùng nhầm hàm của nhau thì KHÔNG nền
    tảng nào báo lỗi – cả hai vẫn nhận gói, vẫn trả thành công, và khớp được đúng 0%.

    Phép thử này cố ý khẳng định hai hàm cho ra hai kết quả KHÁC nhau, để lần "dọn dẹp" nào gộp
    chúng lại cũng làm đỏ ngay tại đây thay vì âm thầm làm hỏng việc đo lường.
    """
    dung = hashlib.sha256(b"+84909123456").hexdigest()

    assert GT.bam_sdt("0909123456") == dung
    assert GT.bam_sdt("+84 909 123 456") == dung
    assert GT.bam_sdt("84909123456") == dung
    assert GT.bam_sdt("") == "" and GT.bam_sdt("123") == ""

    assert GT.bam_sdt("0909123456") != GM.bam_sdt("0909123456"), \
        "Hàm băm của TikTok và của Meta PHẢI khác nhau – xem docstring"
    # Email thì ngược lại: hai nền tảng quy định y hệt, nên dùng chung một hàm là ĐÚNG.
    assert GT.bam_email(" ALICE@Gmail.com ") == GM.bam_email("alice@gmail.com")


def test_c3_ma_lead_tiktok_khong_bam_va_di_kem_ten_he_crm():
    from app.models.quang_cao import ChuyenDoiGuiDi, DauQuangCao
    _bat_cau_hinh()
    cd = ChuyenDoiGuiDi(nen_tang="tiktok", loai_ma="leadgen_id", ma="7312456789",
                        ma_booking="BKX", doanh_thu=5_000_000, tien_te="VND",
                        chot_luc=datetime.now(), khoa_chong_trung="tiktok:BKX:1")
    dau = DauQuangCao(nen_tang="tiktok", loai_ma="leadgen_id", ma="7312456789",
                      sdt="0909123456", khoa_chong_trung="k")

    sk = GT.goi_tin(cd, dau)["data"][0]

    assert sk["lead"]["lead_id"] == "7312456789"
    assert sk["lead"]["lead_event_source"] == "VTOS"
    assert sk["user"]["phone"] == hashlib.sha256(b"+84909123456").hexdigest()
    assert "0909123456" not in str(sk), "Số điện thoại thô lọt ra ngoài gói gửi"


def test_c4_goi_dung_nguon_crm_va_ten_su_kien_tuy_chinh():
    """Tài liệu TikTok: sự kiện CRM CHỈ ĐƯỢC mang tên tuỳ chỉnh, không dùng tên chuẩn."""
    from app.models.quang_cao import ChuyenDoiGuiDi
    _bat_cau_hinh()
    settings.TT_EVENT_NAME = "VTOS_ChotTour"
    cd = ChuyenDoiGuiDi(nen_tang="tiktok", loai_ma="leadgen_id", ma="1", ma_booking="BKY",
                        doanh_thu=1_000_000, tien_te="VND", chot_luc=datetime.now(),
                        khoa_chong_trung="tiktok:BKY:1")

    goi = GT.goi_tin(cd, None)

    assert goi["event_source"] == "crm"
    assert goi["event_source_id"] == "CRM123456"
    assert goi["data"][0]["event"] == "VTOS_ChotTour"
    assert goi["data"][0]["event"] not in {"Purchase", "CompletePayment", "PlaceAnOrder"}, \
        "Tên chuẩn không dùng được cho sự kiện CRM"
    assert isinstance(goi["data"][0]["event_time"], int)


def test_c5_tiktok_tra_200_kem_code_khac_0_van_phai_tinh_la_loi():
    """TikTok trả HTTP 200 cả khi hỏng; mã thật nằm ở khoá `code` trong thân.

    Tin vào mã HTTP là đánh dấu "đã gửi" cho những dòng TikTok đã từ chối, và bảng sẽ báo 100%
    thành công trong khi không có gì tới nơi. Đây là loại sai tệ nhất: nó tự khen mình.
    """
    import urllib.request

    class _TraVe(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _gia_200_nhung_hong(req, timeout=None):
        return _TraVe(json.dumps({"code": 40001, "message": "Invalid event_source_id"}).encode())

    that = urllib.request.urlopen
    urllib.request.urlopen = _gia_200_nhung_hong
    try:
        _bat_cau_hinh()
        kq = GT._bo_gui_that({"event_source": "crm", "data": []})
    finally:
        urllib.request.urlopen = that

    assert kq["ok"] is False, "HTTP 200 kèm code 40001 bị tính nhầm thành gửi thành công"
    assert "40001" in kq["loi"]
    assert "Invalid event_source_id" in kq["tra_loi"], "Phải giữ nguyên văn câu trả lời của TikTok"


def test_c6_khong_dung_vao_dong_cua_nen_tang_khac():
    _bat_cau_hinh()
    cid_fb, _ = _dung("0909100007", 40_000_000, "leadgen_id", "fb-999", nen_tang="facebook")
    gia = MayChuGia()
    GT.dat_ham(gia)

    _chay()

    assert _dong(cid_fb)["trang_thai"] == "cho_gui", "Bộ gửi TikTok đã đụng vào dòng Facebook"
    assert all(g["data"][0]["event_id"].startswith("tiktok:") for g in gia.goi)


def test_c7_event_id_on_dinh_qua_cac_lan_chay():
    from app.models.quang_cao import ChuyenDoiGuiDi
    _bat_cau_hinh()
    cd = ChuyenDoiGuiDi(nen_tang="tiktok", loai_ma="leadgen_id", ma="55", ma_booking="BKZ",
                        doanh_thu=9_000_000, tien_te="VND", chot_luc=datetime.now(),
                        khoa_chong_trung="tiktok:BKZ:12")

    a = GT.goi_tin(cd, None)["data"][0]["event_id"]
    b = GT.goi_tin(cd, None)["data"][0]["event_id"]

    assert a == b == "tiktok:BKZ:12"


def test_c8_gui_duoc_thi_ghi_da_gui_voi_doanh_thu_day_du_va_vnd():
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909100008", 123_456_789, "leadgen_id", "tt-8008")
    gia = MayChuGia()
    GT.dat_ham(gia)

    kq = _chay()

    assert kq["san_sang"] is True and kq["da_gui"] >= 1
    assert _dong(cid)["trang_thai"] == "da_gui"
    g = _goi_cua(gia, ma_bk)
    assert g, "Không thấy gói nào của booking này"
    pr = g[0]["data"][0]["properties"]
    assert pr["value"] == 123_456_789.0, "Doanh thu bị chia hoặc làm tròn"
    assert pr["currency"] == "VND"


def test_c9_khong_co_ma_lead_lan_so_dien_thoai_thi_bo_qua_co_ly_do():
    """Dấu không mang số điện thoại là trường hợp CÓ THẬT, không phải tình huống bịa.

    Cửa `POST /{did}/gan-lead` cho người gắn tay một dấu vào lead khi máy không khớp được –
    ví dụ khách gọi bằng số khác. Dấu ấy có lead, có booking, nên nó vào hàng đợi bình thường,
    nhưng bản thân nó không mang số nào để gửi cho TikTok.

    Chỗ dễ sai ở đây là băm đại một chuỗi rỗng rồi gửi đi: vừa vô nghĩa, vừa làm bẩn tỷ lệ
    khớp, mà TikTok vẫn trả thành công nên không ai biết.
    """
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909100009", 7_000_000, "ma_khuyen_mai", "DHT9-456")
    _xoa_sdt_cua_dau(cid)
    gia = MayChuGia()
    GT.dat_ham(gia)

    _chay()

    d = _dong(cid)
    assert d["trang_thai"] == "bo_qua"
    assert "ma_khuyen_mai" in d["loi_cuoi"]
    assert _goi_cua(gia, ma_bk) == []


def test_c9b_khong_co_ma_lead_nhung_co_so_dien_thoai_thi_VAN_gui():
    """Nguồn CRM của TikTok khớp được bằng số điện thoại đã băm, không bắt buộc phải có mã lead.
    Chặt hơn mức cần thiết ở đây là tự vứt đi những chuyển đổi khớp được."""
    _bat_cau_hinh()
    cid, ma_bk = _dung("0909100011", 15_000_000, "ad_referral", "ref-77")
    gia = MayChuGia()
    GT.dat_ham(gia)

    _chay()

    assert _dong(cid)["trang_thai"] == "da_gui"
    g = _goi_cua(gia, ma_bk)
    assert g and "lead" not in g[0]["data"][0], "Không có mã lead thì đừng bịa ra khoá lead"
    assert g[0]["data"][0]["user"]["phone"]


def test_c10_cua_cau_hinh_khong_lo_token_va_dung_sau_hang_rao_vai_tro():
    _bat_cau_hinh()
    assert client.get("/api/v1/dau-quang-cao/chuyen-doi/cau-hinh-tiktok").status_code in (401, 403)

    r = client.get("/api/v1/dau-quang-cao/chuyen-doi/cau-hinh-tiktok", headers=_dn("chutich"))

    assert r.status_code == 200
    j = r.json()
    assert j["co_token"] is True
    assert "token-gia-cua-phep-thu" not in r.text, "Token lọt ra cửa xem cấu hình"
    assert "dang_cho" in j and "cho_lau_nhat_ngay" in j
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/gui-tiktok").status_code in (401, 403)
    assert client.post("/api/v1/dau-quang-cao/chuyen-doi/gui-tiktok",
                       headers=KHOA).status_code == 200
