"""Kho token Zalo OA – token sống trong cơ sở dữ liệu, không phải trong biến môi trường.

Vì sao tệp này tồn tại: Zalo cấp access token sống 25 giờ và refresh token ĐỔI MỚI sau mỗi lần dùng –
dùng xong cái cũ chết. Bản trước giữ token mới trong bộ nhớ, nên mỗi lần máy chủ khởi động lại (gói
Render miễn phí ngủ khi vắng khách) nó đọc lại refresh token CŨ từ biến môi trường, thứ Zalo đã vô hiệu
hoá. Nối xong chạy ngon đúng một ngày rồi Zalo OA lặng lẽ chết, không cảnh báo, tin khách nhắn vào không
ai thấy. Đó là loại lỗi tệ nhất: nó không kêu.

  ZT1 lần đầu: kho token lấy mồi từ biến môi trường, không để trống
  ZT2 đổi mã uỷ quyền thì token cặp mới GHI XUỐNG cơ sở dữ liệu, kèm hạn dùng
  ZT3 làm mới token thì refresh token MỚI ghi đè cái cũ – đây là điểm chết của bản trước
  ZT4 token đọc lại được sau khi khởi động lại tiến trình (biến môi trường đã cũ vẫn không sao)
  ZT5 làm mới thất bại thì DỰNG CẢNH BÁO ĐỎ, không chết trong im lặng
  ZT6 mã chống giả mạo: sai thì từ chối, đúng thì dùng được đúng một lần
  ZT7 đường uỷ quyền trỏ về domain đã xác thực, kèm đúng app_id và state
"""
import os, sys
from datetime import datetime
os.environ["DATABASE_URL"] = "sqlite:///./test_ztk.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ztk.db"): os.remove("test_ztk.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def test_zt1_lan_dau_lay_moi_tu_bien_moi_truong():
    from app.core.config import settings
    from app.services import zalo as Z
    settings.ZALO_OA_ACCESS_TOKEN = "AT_MOI"; settings.ZALO_OA_REFRESH_TOKEN = "RT_MOI"
    db = _db()
    r = Z.kho(db)
    assert r.access_token == "AT_MOI" and r.refresh_token == "RT_MOI"
    assert Z.token(db) == "AT_MOI"
    db.close()


def test_zt2_doi_ma_uy_quyen_ghi_token_xuong_co_so_du_lieu():
    from app.core.config import settings
    from app.services import zalo as Z
    settings.ZALO_APP_ID = "APPID"; settings.ZALO_APP_SECRET = "SECRET"
    goc = Z._goi_oauth
    Z._goi_oauth = lambda body: {"access_token": "AT1", "refresh_token": "RT1", "expires_in": "90000"}
    db = _db()
    try:
        kq = Z.doi_ma_uy_quyen(db, "MA_UY_QUYEN", boi="cntt")
        assert kq["ok"] and kq["co_refresh"]
    finally:
        Z._goi_oauth = goc
    db.expire_all()
    r = Z.kho(db)
    assert r.access_token == "AT1" and r.refresh_token == "RT1"
    assert r.het_han_luc is not None and r.het_han_luc > datetime.now(), "phải ghi hạn dùng, không thì không ai biết token sắp chết"
    db.close()


def test_zt3_lam_moi_thi_refresh_token_moi_ghi_de_cai_cu():
    """Điểm chết của bản trước. Zalo vô hiệu hoá refresh token vừa dùng; không ghi đè là lần sau cầm chuỗi đã chết."""
    from app.services import zalo as Z
    goc = Z._goi_oauth
    Z._goi_oauth = lambda body: {"access_token": "AT2", "refresh_token": "RT2", "expires_in": "90000"}
    db = _db()
    try:
        assert Z.refresh_token(db) == "AT2"
    finally:
        Z._goi_oauth = goc
    db.expire_all()
    r = Z.kho(db)
    assert r.access_token == "AT2"
    assert r.refresh_token == "RT2", "refresh token cũ vẫn nằm đó – lần khởi động sau hệ thống sẽ cầm chuỗi đã chết"
    assert r.so_lan_lam_moi >= 1
    db.close()


def test_zt4_token_song_qua_lan_khoi_dong_lai():
    """Giả lập khởi động lại: biến môi trường vẫn là chuỗi cũ, nhưng hệ thống phải đọc token từ CSDL."""
    from app.core.config import settings
    from app.services import zalo as Z
    settings.ZALO_OA_ACCESS_TOKEN = "AT_MOI"          # chuỗi cũ trong Render, đã lỗi thời
    settings.ZALO_OA_REFRESH_TOKEN = "RT_MOI"
    db = _db()
    assert Z.token(db) == "AT2", "đọc lại token từ biến môi trường là đúng cái bẫy phép thử này canh"
    assert Z.configured(db)["oa"] is True
    db.close()


def test_zt5_lam_moi_that_bai_thi_dung_canh_bao_do():
    from sqlalchemy import select
    from app.services import zalo as Z
    from app.models.core import Alert
    goc = Z._goi_oauth
    Z._goi_oauth = lambda body: {"error": -216, "error_name": "invalid_refresh_token"}
    db = _db()
    try:
        assert Z.refresh_token(db) == ""
    finally:
        Z._goi_oauth = goc
    a = db.execute(select(Alert).where(Alert.kind == "zalo_token_hong", Alert.resolved == False)).scalars().first()
    assert a is not None and a.level == "red", "token chết mà không ai được báo thì Zalo OA ngừng chạy trong im lặng"
    assert "chutich" in a.to_roles and "cntt" in a.to_roles
    assert Z.kho(db).loi_cuoi, "phải ghi lại lý do hỏng để người sau đọc còn hiểu"
    db.close()


def test_zt6_ma_chong_gia_sai_thi_tu_choi_dung_thi_dung_mot_lan():
    from app.services import zalo as Z
    db = _db()
    _, ma = Z.duong_uy_quyen(db, "cntt")
    assert not Z.kiem_ma_chong_gia(db, "ma-bia-dat"), "không kiểm thì ai gọi đúng đường dẫn cũng đặt được token"
    assert not Z.kiem_ma_chong_gia(db, "")
    assert Z.kiem_ma_chong_gia(db, ma)
    assert not Z.kiem_ma_chong_gia(db, ma), "một mã phải dùng được đúng một lần"
    db.close()


def test_zt7_duong_uy_quyen_tro_ve_domain_da_xac_thuc():
    from app.core.config import settings
    from app.services import zalo as Z
    db = _db()
    duong, ma = Z.duong_uy_quyen(db, "cntt")
    assert duong.startswith("https://oauth.zaloapp.com/v4/oa/permission?")
    assert f"app_id={settings.ZALO_APP_ID}" in duong
    assert ma in duong
    # domain trong đường trả về phải là domain đã xác thực với Zalo, nếu không Zalo chặn ngay bước mở trang
    assert "vtos.infinitytours.org" in Z.TRA_VE and Z.TRA_VE.startswith("https://")
    assert "vtos.infinitytours.org" in duong.replace("%3A", ":").replace("%2F", "/")
    db.close()


def test_zt8_tep_xac_thuc_tien_to_url_tra_dung_chuoi_cua_ung_dung():
    """Zalo bắt xác thực TIỀN TỐ URL /api/v1/zalo/ – tệp ấy phải do máy chủ trả, không phải giao diện.

    Chiều ngược quan trọng hơn: trả lại đúng chuỗi người gọi đưa vào thì BẤT KỲ ứng dụng Zalo nào cũng
    xác thực được tiền tố URL của công ty, tức là cướp được đường nhận uỷ quyền.
    """
    from app.api.v1.crm import ZALO_VERIFIER
    r = client.get(f"/api/v1/zalo/zalo_verifier{ZALO_VERIFIER}.html")
    assert r.status_code == 200 and r.text.strip() == ZALO_VERIFIER
    assert client.get("/api/v1/zalo/zalo_verifierCHUOI_BIA_DAT.html").status_code == 404
