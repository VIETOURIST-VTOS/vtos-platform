"""TC-109 · Kéo lead từ biểu mẫu quảng cáo Zalo về bảng dấu nguồn quảng cáo.

Zalo KHÔNG có cửa nhận chuyển đổi từ máy chủ như Meta và TikTok (đã tra tài liệu chính thức
07/10/2026). Nên vòng Zalo chỉ khép được nửa đầu: lấy lead kèm nguồn quảng cáo, không báo ngược
được doanh thu. Nửa ấy vẫn đáng làm – tháng 9/2026 Zalo là một kênh có thật trong báo cáo, và
hôm nay lead Zalo vào VTOS mà không mang theo dấu vết quảng cáo nào.

  C1  chưa cấu hình thì không gọi mạng
  C2  tìm số điện thoại: ưu tiên tiêu đề câu hỏi, rồi dò mẫu, và KHÔNG đoán bừa
  C3  ghi đúng nền tảng, mã lead, mã quảng cáo và mốc chạm
  C4  giữ NGUYÊN VĂN gói tin của Zalo
  C5  kéo lại cùng khoảng thời gian KHÔNG nhân đôi
  C6  phân trang: trang đầy thì đọc tiếp, trang vơi thì dừng
  C7  Zalo báo lỗi (ví dụ thiếu quyền quản lý ads) thì giữ nguyên văn, không nuốt
  C8  xin quá 30 ngày thì bị cắt xuống 30 – đó là hạn của Zalo
  C9  không đọc được số điện thoại thì VẪN ghi dấu, và đếm được
  C10 cửa cấu hình không lộ token, cửa kéo đứng sau khoá máy chủ
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc109.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "robot-tc109"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc109.db", "test_tc109.db-journal"):
    if os.path.exists(f): os.remove(f)

import json                                        # noqa: E402
from datetime import datetime, timedelta           # noqa: E402
import pytest                                      # noqa: E402
from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                           # noqa: E402
from app.core.config import settings               # noqa: E402
from app.services import zalo_form_ads as ZF       # noqa: E402

client = TestClient(app)
KHOA = {"X-Robot-Token": "robot-tc109"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(autouse=True)
def _don_dep():
    cu = {k: getattr(settings, k) for k in ("ZALO_FORM_IDS", "ZALO_OA_ACCESS_TOKEN")}
    yield
    ZF.dat_ham()
    for k, v in cu.items():
        setattr(settings, k, v)


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _bat_cau_hinh(forms="F1"):
    settings.ZALO_FORM_IDS = forms
    settings.ZALO_OA_ACCESS_TOKEN = "token-gia-cua-phep-thu"
    # Kho token nằm trong cơ sở dữ liệu; nạp mồi từ biến môi trường như services/zalo làm.
    db = _db()
    try:
        from app.services import zalo as Z
        r = Z.kho(db)
        r.access_token = "token-gia-cua-phep-thu"
        db.commit()
    finally:
        db.close()


class ZaloGia:
    """Đứng thay Zalo. `trang` là danh sách các trang trả về lần lượt."""

    def __init__(self, trang=None, loi=None, cau_hoi=None):
        self.trang = trang or []
        self.loi = loi
        self.cau_hoi = cau_hoi if cau_hoi is not None else [
            {"questionId": 1, "title": "Họ và tên"},
            {"questionId": 2, "title": "Số điện thoại"},
        ]
        self.goi = []

    def __call__(self, token, form_id, tu, den, offset, limit):
        self.goi.append({"form_id": form_id, "tu": tu, "den": den,
                         "offset": offset, "limit": limit})
        if self.loi is not None:
            return self.loi
        i = len(self.goi) - 1
        dong = self.trang[i] if i < len(self.trang) else []
        return {"error": 0, "data": {"total": sum(len(t) for t in self.trang),
                                     "questions": self.cau_hoi, "responses": dong}}


def _mot_dong(lead_id: str, sdt: str, ad_id: str = "AD9", ten: str = "Khach Zalo", lui_gio=1):
    t = int((datetime.now() - timedelta(hours=lui_gio)).timestamp())
    return {"submitTime": t, "leadId": lead_id, "adId": ad_id,
            "answers": [{"questionId": 1, "responses": [ten]},
                        {"questionId": 2, "responses": [sdt]}]}


def _dau_theo_ma(ma: str):
    from app.models.quang_cao import DauQuangCao
    from sqlalchemy import select
    db = _db()
    try:
        return db.execute(select(DauQuangCao).where(DauQuangCao.ma == ma)).scalars().first()
    finally:
        db.close()


def _keo(**kw):
    db = _db()
    try:
        return ZF.keo(db, **kw)
    finally:
        db.close()


_TOK: dict = {}


def _dn(u: str):
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


# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_c1_chua_cau_hinh_thi_khong_goi_mang():
    settings.ZALO_FORM_IDS = ""
    gia = ZaloGia()
    ZF.dat_ham(gia)

    kq = _keo()

    assert kq["san_sang"] is False
    assert "ZALO_FORM_IDS" in kq["thieu"]
    assert gia.goi == [], "Thiếu mã biểu mẫu mà vẫn gọi ra Zalo"


def test_c2_tim_so_dien_thoai_uu_tien_tieu_de_roi_moi_do_mau_va_khong_doan_bua():
    """Zalo KHÔNG nói câu hỏi nào là số điện thoại – chỉ có tiêu đề người dựng tự gõ.

    Nên phép tìm có ba bước, và bước cuối là CHỊU THUA chứ không đoán. Lấy nhầm mã số thuế hay
    số nhà làm số điện thoại thì dấu gắn sai khách, và sai đó không ai phát hiện ra.
    """
    ch = [{"questionId": 1, "title": "Họ và tên"},
          {"questionId": 2, "title": "Số điện thoại liên hệ"},
          {"questionId": 3, "title": "Ghi chú"}]

    # Bước 1 – đúng câu hỏi, dù câu khác cũng chứa chuỗi số dài.
    assert ZF.sdt_tu_cau_tra_loi(ch, [
        {"questionId": 3, "responses": ["123456789012"]},
        {"questionId": 2, "responses": ["0909 123 456"]}]) == "0909123456"

    # Bước 2 – tiêu đề lạ thì dò mẫu trên mọi câu trả lời.
    assert ZF.sdt_tu_cau_tra_loi(
        [{"questionId": 9, "title": "Thông tin"}],
        [{"questionId": 9, "responses": ["0912345678"]}]) == "0912345678"

    # Bước 3 – không có gì giống số điện thoại thì trả rỗng, KHÔNG bịa.
    assert ZF.sdt_tu_cau_tra_loi(ch, [{"questionId": 1, "responses": ["Nguyen Van A"]}]) == ""
    # Có chữ lẫn vào thì không phải số điện thoại mà là một câu có số.
    assert ZF._la_sdt("nha 12 ngo 345678901") == ""
    assert ZF._la_sdt("12345") == ""


def test_c3_ghi_dung_nen_tang_ma_lead_ma_quang_cao_va_moc_cham():
    _bat_cau_hinh()
    ZF.dat_ham(ZaloGia(trang=[[_mot_dong("ZL-1001", "0909200001", ad_id="AD-77")]]))

    kq = _keo(so_ngay=7)

    assert kq["san_sang"] is True and kq["moi"] == 1
    d = _dau_theo_ma("ZL-1001")
    assert d is not None
    assert d.nen_tang == "zalo"
    assert d.loai_ma == "leadgen_id"
    assert d.ma_mau_qc == "AD-77"
    assert d.sdt == "0909200001"
    assert d.nguon_ghi == "api_zalo_ads", "Kéo bằng API khác hẳn webhook – đừng gộp hai nguồn"
    assert d.cham_luc is not None, "submitTime phải thành mốc chạm, không được để rỗng"


def test_c4_giu_nguyen_van_goi_tin_cua_zalo():
    """Phép dò số điện thoại có thể sai; gói tin gốc thì không được mất.

    Giữ nguyên văn là thứ cho phép sửa lại phép dò sau này mà không phải gọi lại Zalo – mà gọi
    lại thì quá 30 ngày là không lấy được nữa.
    """
    _bat_cau_hinh()
    ZF.dat_ham(ZaloGia(trang=[[_mot_dong("ZL-1002", "0909200002", ten="Trần Thị B")]]))

    _keo()

    d = _dau_theo_ma("ZL-1002")
    goc = json.loads(d.than_nguyen_van)
    assert goc["leadId"] == "ZL-1002"
    assert goc["answers"][0]["responses"] == ["Trần Thị B"]


def test_c5_keo_lai_cung_khoang_thoi_gian_khong_nhan_doi():
    """leadId đổi theo TỪNG LẦN submit, nên nó là khoá chống trùng hoàn hảo."""
    _bat_cau_hinh()
    ZF.dat_ham(ZaloGia(trang=[[_mot_dong("ZL-1003", "0909200003")]]))
    a = _keo()
    ZF.dat_ham(ZaloGia(trang=[[_mot_dong("ZL-1003", "0909200003")]]))
    b = _keo()

    assert a["moi"] == 1
    assert b["moi"] == 0 and b["ket_qua"][0]["da_co"] == 1


def test_c6_phan_trang_trang_day_thi_doc_tiep_trang_voi_thi_dung():
    """Zalo chỉ trả tối đa 200 dòng một trang. Không phân trang là lặng lẽ mất từ dòng 201."""
    _bat_cau_hinh()
    day = [_mot_dong(f"ZL-P{i}", f"09091{i:05d}") for i in range(ZF.TOI_DA_MOI_TRANG)]
    voi = [_mot_dong("ZL-CUOI", "0909299999")]
    gia = ZaloGia(trang=[day, voi])
    ZF.dat_ham(gia)

    kq = _keo()

    assert len(gia.goi) == 2, "Trang đầy mà không đọc tiếp – mất dữ liệu từ dòng 201"
    assert gia.goi[0]["offset"] == 0 and gia.goi[1]["offset"] == ZF.TOI_DA_MOI_TRANG
    assert gia.goi[0]["limit"] == ZF.TOI_DA_MOI_TRANG
    assert kq["moi"] == ZF.TOI_DA_MOI_TRANG + 1
    assert _dau_theo_ma("ZL-CUOI") is not None


def test_c7_zalo_bao_loi_thi_giu_nguyen_van_khong_nuot():
    """Thiếu quyền quản lý ads là lỗi RẤT dễ gặp, vì nó khác quyền nhắn tin VTOS đang dùng.

    Nuốt lỗi thành một câu chung chung thì mất nửa ngày mới lần ra; giữ nguyên văn thì đọc một
    cái là biết.
    """
    _bat_cau_hinh()
    ZF.dat_ham(ZaloGia(loi={"error": -201, "message": "Access token không có quyền quản lý ads"}))

    kq = _keo()

    assert kq["so_form_loi"] == 1
    assert "quyền quản lý ads" in kq["ket_qua"][0]["loi"]
    assert "-201" in kq["ket_qua"][0]["loi"]


def test_c8_xin_qua_30_ngay_thi_bi_cat_xuong_30():
    """30 ngày là hạn CỦA ZALO, không phải lựa chọn của mình. Xin 90 thì Zalo từ chối cả lượt."""
    _bat_cau_hinh()
    gia = ZaloGia(trang=[[]])
    ZF.dat_ham(gia)

    kq = _keo(so_ngay=90)

    assert kq["so_ngay"] == ZF.HAN_CUA_SO_NGAY == 30
    khoang_ngay = (gia.goi[0]["den"] - gia.goi[0]["tu"]) / 86400
    assert 29.5 <= khoang_ngay <= 30.5


def test_c9_khong_doc_duoc_so_dien_thoai_thi_van_ghi_dau_va_dem_duoc():
    """Bỏ dòng đi là mất một lần chạm có thật. Ghi lại kèm số đếm thì sửa được sau."""
    _bat_cau_hinh()
    khong_sdt = {"submitTime": int(datetime.now().timestamp()), "leadId": "ZL-1009", "adId": "AD1",
                 "answers": [{"questionId": 1, "responses": ["Chi Lan"]}]}
    ZF.dat_ham(ZaloGia(trang=[[khong_sdt]]))

    kq = _keo()

    d = _dau_theo_ma("ZL-1009")
    assert d is not None and d.sdt == ""
    assert kq["ket_qua"][0]["khong_doc_duoc_sdt"] == 1


def test_c10_cua_cau_hinh_khong_lo_token_va_cua_keo_dung_sau_khoa_may_chu():
    _bat_cau_hinh(forms="F1,F2")
    assert client.get("/api/v1/dau-quang-cao/cau-hinh-zalo-form").status_code in (401, 403)

    r = client.get("/api/v1/dau-quang-cao/cau-hinh-zalo-form", headers=_dn("chutich"))

    assert r.status_code == 200
    j = r.json()
    assert j["co_token"] is True and j["ma_form"] == ["F1", "F2"] and j["so_form"] == 2
    assert "token-gia-cua-phep-thu" not in r.text, "Token lọt ra cửa xem cấu hình"
    assert "không có cửa nhận chuyển đổi" in j["luu_y"].lower() or "KHÔNG có cửa" in j["luu_y"]

    assert client.post("/api/v1/dau-quang-cao/keo-zalo-form").status_code in (401, 403)
    ZF.dat_ham(ZaloGia(trang=[[]]))
    assert client.post("/api/v1/dau-quang-cao/keo-zalo-form", headers=KHOA).status_code == 200
