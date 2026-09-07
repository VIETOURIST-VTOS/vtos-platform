"""Phản hồi & khiếu nại của khách hàng – Đợt 3.

Chốt chặn sống còn: màn hình này KHÔNG có ô số tiền bồi thường. Hướng xử lý có hoàn tiền thì phải gắn
số hiệu Đề nghị chi nhóm "hoan_tien" mới đóng được hồ sơ. Có ô số tiền ở đây là mở đường tiền thứ hai
song song với cổng chi – hai đường sẽ lệch nhau và con số nào là thật thì không ai biết.

  K1 thiếu nguyên văn lời khách hoặc thiếu đề nghị của khách → không lập được
  K2 khiếu nại chất lượng dịch vụ bắt buộc gắn chuyến
  K3 hạn phản hồi lấy từ THAM SỐ theo mức độ, không viết cứng
  K4 hướng xử lý có hoàn tiền mà chưa gắn đề nghị chi → không đóng được
  K5 gắn nhầm chứng từ khác nhóm hoàn tiền → chặn
  K6 khách chưa chấp nhận thì hồ sơ chưa đóng
  K7 mức 3: người xử lý không tự đóng, và phải đủ hai chữ ký
  K8 tái mở phải có lý do
  K9 quá hạn phản hồi thì robot cảnh báo, mức 3 leo thẳng lên Ban TGĐ
  K10 khách khiếu nại lần thứ hai trong 12 tháng được đánh dấu ngay trên hồ sơ
"""
import os, sys
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_kn.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_kn.db"): os.remove("test_kn.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}; CTX = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def booking_id():
    if "bk" not in CTX:
        r = client.get("/api/v1/bookings?limit=5", headers=login("cntt")).json()
        CTX["bk"] = r[0]["id"]
    return CTX["bk"]


BASE = {"source": "dien_thoai", "customer_name": "Nguyễn Văn A", "customer_phone": "0900000001",
        "nhom": "khac", "level": 1, "noi_dung": "Khách nói: xe đón trễ 40 phút, không ai báo trước.",
        "de_nghi_khach": "Khách yêu cầu xin lỗi bằng văn bản và giảm giá cho lần đi sau."}


def test_k1_thieu_nguyen_van_hoac_thieu_de_nghi_khach_thi_khong_lap_duoc():
    h = login("cntt")
    assert client.post("/api/v1/khieu-nai", json=dict(BASE, noi_dung=""), headers=h).status_code == 422
    r = client.post("/api/v1/khieu-nai", json=dict(BASE, de_nghi_khach=""), headers=h)
    assert r.status_code == 422 and "ĐỀ NGHỊ CỦA KHÁCH" in r.json()["detail"]
    assert client.post("/api/v1/khieu-nai", json=dict(BASE, level=9), headers=h).status_code == 422


def test_k2_khieu_nai_chat_luong_bat_buoc_gan_chuyen():
    h = login("cntt")
    r = client.post("/api/v1/khieu-nai", json=dict(BASE, nhom="hdv"), headers=h)
    assert r.status_code == 422 and "chuyến" in r.json()["detail"]
    r = client.post("/api/v1/khieu-nai", json=dict(BASE, nhom="hdv", booking_id=booking_id()), headers=h)
    assert r.status_code == 201
    # gắn chuyến thì hồ sơ tự lấy luôn mã tour – không bắt người dùng gõ lại
    assert r.json()["complaint"]["tour_code"]


def test_k3_han_phan_hoi_lay_tu_tham_so_theo_muc_do():
    h = login("cntt")
    m1 = client.post("/api/v1/khieu-nai", json=dict(BASE, level=1), headers=h).json()["complaint"]
    m3 = client.post("/api/v1/khieu-nai", json=dict(BASE, level=3, handler="tgd"), headers=h).json()["complaint"]
    CTX["m3"] = m3["id"]
    gio1 = (datetime.fromisoformat(m1["han_phan_hoi"]) - datetime.fromisoformat(m1["received_at"])).total_seconds() / 3600
    gio3 = (datetime.fromisoformat(m3["han_phan_hoi"]) - datetime.fromisoformat(m3["received_at"])).total_seconds() / 3600
    assert round(gio1) == 72 and round(gio3) == 4, f"mức 1 {gio1}h, mức 3 {gio3}h"


DONG = {"nguyen_nhan_nhom": "do_ta", "nguyen_nhan": "Nhà xe điều xe trễ, điều hành không báo khách.",
        "khach_chap_nhan": "co"}


def test_k4_hoan_tien_ma_chua_gan_de_nghi_chi_thi_khong_dong_duoc():
    h = login("cntt")
    c = client.post("/api/v1/khieu-nai", json=dict(BASE, level=1), headers=h).json()["complaint"]
    CTX["c1"] = c["id"]
    r = client.post(f"/api/v1/khieu-nai/{c['id']}/dong",
                    json=dict(DONG, huong_xu_ly=["hoan_mot_phan"]), headers=h)
    assert r.status_code == 422 and "Đề nghị chi" in r.json()["detail"]
    # xin lỗi suông thì đóng được ngay – không phải khiếu nại nào cũng có tiền
    r = client.post(f"/api/v1/khieu-nai/{c['id']}/dong", json=dict(DONG, huong_xu_ly=["xin_loi"]), headers=h)
    assert r.status_code == 200 and r.json()["complaint"]["status"] == "da_dong"


def test_k5_gan_nham_chung_tu_khac_nhom_hoan_tien_thi_chan():
    h = login("cntt")
    from app.db.session import SessionLocal
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    pr = PaymentRequest(code="DCTEST-9001", category="marketing", supplier_name="Đại lý quảng cáo",
                        amount=1_000_000, description="chi quảng cáo", status="da_chi", created_by="cntt")
    db.add(pr); db.commit(); pid = pr.id; db.close()
    c = client.post("/api/v1/khieu-nai", json=dict(BASE, level=2), headers=h).json()["complaint"]
    r = client.post(f"/api/v1/khieu-nai/{c['id']}/dong",
                    json=dict(DONG, huong_xu_ly=["hoan_toan_bo"], payment_request_id=pid), headers=h)
    assert r.status_code == 422 and "hoàn tiền" in r.json()["detail"]


def test_k6_khach_chua_chap_nhan_thi_ho_so_chua_dong():
    h = login("cntt")
    c = client.post("/api/v1/khieu-nai", json=dict(BASE, level=1), headers=h).json()["complaint"]
    r = client.post(f"/api/v1/khieu-nai/{c['id']}/dong",
                    json={"nguyen_nhan_nhom": "do_khach", "nguyen_nhan": "Khách nhầm giờ đón.",
                          "huong_xu_ly": ["khong_boi_thuong"], "khach_chap_nhan": "khong"}, headers=h)
    assert r.status_code == 422 and "chưa chấp nhận" in r.json()["detail"]


def test_k7_muc_3_nguoi_xu_ly_khong_tu_dong_va_phai_du_hai_chu_ky():
    cid = CTX["m3"]
    d = dict(DONG, huong_xu_ly=["xin_loi", "uu_dai"])
    # người xử lý là tgd → tgd không được tự đóng hồ sơ của mình
    r = client.post(f"/api/v1/khieu-nai/{cid}/dong", json=d, headers=login("tgd"))
    assert r.status_code == 403 and "vừa xử lý vừa đóng" in r.json()["detail"]
    # vai trò ngoài Ban TGĐ cũng không ký đóng được hồ sơ mức 3
    assert client.post(f"/api/v1/khieu-nai/{cid}/dong", json=d, headers=login("cntt")).status_code == 403
    r = client.post(f"/api/v1/khieu-nai/{cid}/dong", json=d, headers=login("chutich"))
    assert r.status_code == 200 and r.json()["complaint"]["status"] != "da_dong", "một chữ ký chưa đủ cho mức 3"
    # ký lại lần hai bằng chính người đó không được tính là chữ ký thứ hai
    assert client.post(f"/api/v1/khieu-nai/{cid}/dong", json=d, headers=login("chutich")).status_code == 422
    r = client.post(f"/api/v1/khieu-nai/{cid}/dong", json=d, headers=login("ptgd.mkt"))
    assert r.status_code == 200 and r.json()["complaint"]["status"] == "da_dong"
    assert r.json()["complaint"]["closed_by"].count(",") == 1


def test_k8_tai_mo_phai_co_ly_do():
    cid = CTX["c1"]; h = login("cntt")
    assert client.post(f"/api/v1/khieu-nai/{cid}/tai-mo", json={"ly_do": "  "}, headers=h).status_code == 422
    r = client.post(f"/api/v1/khieu-nai/{cid}/tai-mo", json={"ly_do": "Khách gọi lại, chưa nhận được thư xin lỗi"}, headers=h)
    assert r.status_code == 200 and r.json()["complaint"]["status"] == "tai_mo"
    assert r.json()["complaint"]["khach_chap_nhan"] == "", "tái mở mà giữ nguyên 'khách đã chấp nhận' là đóng lại được ngay mà không hỏi ai"


def test_k9_qua_han_phan_hoi_thi_robot_canh_bao_muc_3_leo_thang_ban_tgd():
    h = login("cntt")
    c = client.post("/api/v1/khieu-nai", json=dict(BASE, level=3, customer_phone="0900000777"), headers=h).json()["complaint"]
    from app.db.session import SessionLocal
    from app.models.cskh import Complaint
    from app.models.core import Alert
    from app.services import cskh as CS
    from sqlalchemy import select
    db = SessionLocal()
    row = db.get(Complaint, c["id"]); row.han_phan_hoi = datetime.now() - timedelta(hours=5); db.commit()
    CS.robot_cskh(db)
    a = db.execute(select(Alert).where(Alert.kind == "kn_qua_han", Alert.ref == c["code"])).scalars().first()
    assert a is not None, "quá hạn phản hồi mà im lặng là cách một khiếu nại mức 3 thành một bài báo"
    assert "chutich" in a.to_roles and "tgd" in a.to_roles
    db.close()
    assert client.get(f"/api/v1/khieu-nai/{c['id']}", headers=h).json()["qua_han"] is True


def test_k10_khach_khieu_nai_lan_thu_hai_trong_12_thang_duoc_danh_dau():
    h = login("cntt")
    sdt = "0911222333"
    a = client.post("/api/v1/khieu-nai", json=dict(BASE, customer_phone=sdt), headers=h).json()["complaint"]
    assert a["lan_khieu_nai_12_thang"] == 1
    b = client.post("/api/v1/khieu-nai", json=dict(BASE, customer_phone=sdt), headers=h).json()["complaint"]
    assert b["lan_khieu_nai_12_thang"] == 2, "khiếu nại lần hai là dấu hiệu vấn đề hệ thống, phải hiện ngay trên hồ sơ"
