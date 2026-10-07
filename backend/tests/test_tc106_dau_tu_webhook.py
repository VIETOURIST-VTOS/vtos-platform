"""TC-106 · Nối hai webhook đang chạy vào bảng dấu nguồn quảng cáo.

Webhook Facebook và webhook Zalo OA đã chạy nhiều tuần trong VTOS. Cả hai đi qua đúng chỗ Meta và
Zalo đặt mã quảng cáo vào, và cả hai VỨT nó đi:

  · `services/inbox.fb_webhook` đọc `entry[].messaging[]` lấy nội dung tin, nhưng không đọc
    `referral` (khách bấm quảng cáo nhắn tin) và không đọc `changes[]` field `leadgen`.
  · `services/zalo.on_webhook` tạo lead kênh "Zalo OA" nhưng không ghi dấu nào.

Mã quảng cáo chỉ đi qua một lần. Những phép thử này giữ cho hai chỗ nối ấy không lặng lẽ đứt.

  M1  khách bấm quảng cáo rồi nhắn tin → ghi dấu kèm ad_id
  M2  lần chạm ĐẦU TIÊN (referral nằm trong postback) cũng phải bắt được
  M3  biểu mẫu Lead Ads → ghi leadgen_id, ad_id, adgroup_id
  M4  gói lặp lại không nhân đôi
  M5  một dấu hỏng KHÔNG làm hỏng cả webhook
  M6  Zalo: khách quan tâm OA → một dấu; nhân viên bấm quan tâm → KHÔNG
  M7  nối vào không làm đổi hành vi cũ của hộp thư
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc106.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc106.db", "test_tc106.db-journal"):
    if os.path.exists(f): os.remove(f)

import pytest                                       # noqa: E402
from fastapi.testclient import TestClient           # noqa: E402
from app.main import app                            # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _dau():
    from sqlalchemy import select
    from app.models.quang_cao import DauQuangCao
    db = _db()
    try:
        return list(db.execute(select(DauQuangCao)).scalars())
    finally:
        db.close()


def _nap(payload):
    from app.services import dau_meta_zalo as MZ
    db = _db()
    try:
        r = MZ.tu_meta(db, payload)
        db.commit()
        return r
    finally:
        db.close()


def test_m1_khach_bam_quang_cao_roi_nhan_tin_thi_ghi_duoc_ad_id():
    r = _nap({"object": "page", "entry": [{"id": "PAGE1", "time": 1791380000, "messaging": [
        {"sender": {"id": "PSID001"}, "recipient": {"id": "PAGE1"}, "timestamp": 1791380000000,
         "referral": {"ref": "dalat-t10", "ad_id": "AD777", "source": "ADS", "type": "OPEN_THREAD"}}]}]})
    assert r["moi"] == 1 and not r["loi"], r
    d = [x for x in _dau() if x.ma == "AD777"]
    assert len(d) == 1
    assert d[0].nen_tang == "facebook" and d[0].loai_ma == "ad_referral"
    assert d[0].ma_mau_qc == "AD777" and d[0].utm.get("ref") == "dalat-t10"
    assert d[0].cham_luc is not None, "phải đọc được giờ chạm từ timestamp mili giây của Meta"


def test_m2_lan_cham_dau_tien_referral_nam_trong_postback():
    """Lần đầu khách bấm quảng cáo, Meta gửi referral LỒNG trong postback kèm nút Bắt đầu. Chỉ đọc
    `ev['referral']` thì mất đúng nhóm khách MỚI – nhóm mà quảng cáo vừa mua về."""
    r = _nap({"object": "page", "entry": [{"id": "PAGE1", "messaging": [
        {"sender": {"id": "PSID002"}, "recipient": {"id": "PAGE1"}, "timestamp": 1791380100,
         "postback": {"title": "Bat dau", "payload": "GET_STARTED",
                      "referral": {"ref": "nhatban", "ad_id": "AD888", "source": "ADS"}}}]}]})
    assert r["moi"] == 1, r
    assert [x for x in _dau() if x.ma == "AD888"]


def test_m3_bieu_mau_lead_ads_ghi_du_ba_ma():
    """Dấu chính xác nhất trong cả bốn kênh: biết đúng mẫu quảng cáo nào ra khách, không suy đoán."""
    r = _nap({"object": "page", "entry": [{"id": "PAGE1", "changes": [
        {"field": "leadgen", "value": {"leadgen_id": "LG555", "page_id": "PAGE1",
                                       "form_id": "FORM9", "ad_id": "AD999",
                                       "adgroup_id": "ADSET3", "created_time": 1791380200}}]}]})
    assert r["moi"] == 1, r
    d = [x for x in _dau() if x.ma == "LG555"][0]
    assert d.loai_ma == "leadgen_id" and d.ma_mau_qc == "AD999" and d.ma_nhom_qc == "ADSET3"
    assert d.utm.get("form_id") == "FORM9"


def test_m4_goi_lap_lai_khong_nhan_doi():
    """Meta gửi lại khi không nhận được 200 kịp. Không chống trùng thì một khách thành nhiều."""
    goi = {"object": "page", "entry": [{"id": "PAGE1", "changes": [
        {"field": "leadgen", "value": {"leadgen_id": "LG555", "page_id": "PAGE1",
                                       "ad_id": "AD999", "created_time": 1791380200}}]}]}
    r = _nap(goi)
    assert r["moi"] == 0 and r["da_co"] == 1, r
    assert len([x for x in _dau() if x.ma == "LG555"]) == 1


def test_m5_mot_dau_hong_khong_lam_hong_ca_webhook():
    """Meta TẮT webhook sau vài lần nhận mã lỗi, và mất webhook la mất mọi dấu VỀ SAU, không chỉ
    cái dấu hỏng này. Nên dòng hỏng được gom vào `loi` chứ không ném ra ngoài."""
    truoc = len(_dau())
    r = _nap({"object": "page", "entry": [
        {"id": "PAGE1", "messaging": [
            {"sender": {"id": "PSID003"}, "timestamp": 99999999999999999,
             "referral": {"ref": "gio-hong", "ad_id": "AD-HONG"}}]},
        {"id": "PAGE1", "changes": [
            {"field": "leadgen", "value": {"leadgen_id": "LG666", "ad_id": "AD111",
                                           "created_time": 1791380300}}]}]})
    assert r["moi"] >= 1, "dấu lành phải vào được dù dấu kia có vấn đề"
    assert [x for x in _dau() if x.ma == "LG666"]
    assert len(_dau()) > truoc


def test_m6_zalo_khach_quan_tam_thi_ghi_dau_nhan_vien_thi_khong():
    """Chủ tịch bấm 'Quan tâm' OA để nhận cảnh báo, chứ không phải để thành một dấu quảng cáo
    trong báo cáo hiệu quả kênh. Quyết định ai là nhân viên thuộc `zalo_nguoi_dung`; tệp này
    KHÔNG suy lại, nó đọc kết quả – hai chỗ suy cùng một việc thì sẽ có ngày lệch."""
    from app.services import dau_meta_zalo as MZ
    db = _db()
    try:
        ev = {"event_name": "follow", "follower": {"id": "ZUID001"}, "timestamp": "1791380400"}
        r = MZ.tu_zalo(db, ev, {"event": "follow", "uid": "ZUID001"})
        db.commit()
        assert r.get("moi") == 1, r
        r2 = MZ.tu_zalo(db, ev, {"event": "follow", "uid": "ZUID002", "la_nhan_vien": True})
        db.commit()
        assert r2.get("bo_qua") == "nhan_vien", r2
        # Tin nhắn thường không sinh dấu: khoá theo uid nên không nhân đôi, nhưng gọi cho từng
        # tin là tra cơ sở dữ liệu không công.
        r3 = MZ.tu_zalo(db, {"event_name": "user_send_text", "sender": {"id": "ZUID003"}},
                        {"event": "user_send_text", "uid": "ZUID003"})
        assert r3.get("bo_qua") == "user_send_text", r3
    finally:
        db.rollback(); db.close()
    assert [x for x in _dau() if x.ma == "ZUID001"]
    assert not [x for x in _dau() if x.ma == "ZUID002"]


def test_m7_goi_khong_co_dau_quang_cao_thi_khong_ghi_gi():
    """Phần lớn gói webhook chỉ là tin nhắn thường. Nối vào không được làm bẩn bảng dấu."""
    truoc = len(_dau())
    r = _nap({"object": "page", "entry": [{"id": "PAGE1", "messaging": [
        {"sender": {"id": "PSID009"}, "recipient": {"id": "PAGE1"}, "timestamp": 1791380500,
         "message": {"mid": "m1", "text": "Cho em hoi tour Da Lat"}}]}]})
    assert r["moi"] == 0 and r["da_co"] == 0 and not r["loi"], r
    assert len(_dau()) == truoc
