"""Chăm sóc sau bán – Đợt 4.

Nguyên tắc: việc TỰ SINH từ tour đã kết thúc, không ai phải nhớ để nhập. Danh sách nhập tay sẽ đầy đủ
trong hai tuần đầu rồi thưa dần và bỏ hẳn – nên hệ thống cố tình không có đường tạo phiếu cho một khách lẻ.

  C1 phiếu tự sinh từ tour kết thúc, mỗi booking một phiếu, chạy lại không sinh trùng
  C2 không liên hệ được thì phải ghi lý do
  C3 liên hệ được thì phải chấm điểm và trả lời hai câu bắt buộc
  C4 điểm hài lòng dưới ngưỡng tham số → tự mở hồ sơ khiếu nại
  C5 khách còn nhu cầu → tự tạo lead khách cũ, gắn đúng nhân viên đã bán
  C6 hồ sơ tự mở KHÔNG đóng được khi chưa hỏi khách đề nghị của họ
  C7 chỉ số đo việc làm thật: tỷ lệ liên hệ được, số phiếu quá hạn
  C8 không có đường tạo phiếu chăm sóc cho một khách lẻ
  C9 KHÔNG mở phiếu cho toàn bộ lịch sử chuyến đã đóng – chỉ chuyến kết thúc gần đây
  C10 phiếu bù cho chuyến cũ KHÔNG được sinh ra đã quá hạn
  C11 phiếu lỡ sinh ra quá hạn thì robot vá lại hạn và gỡ cảnh báo giả xuống
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_cs.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cs.db"): os.remove("test_cs.db")
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


def test_c1_phieu_tu_sinh_tu_tour_ket_thuc_va_chay_lai_khong_trung():
    h = login("cntt")
    n1 = client.post("/api/v1/cham-soc/sinh-phieu", headers=h).json()["da_sinh"]
    assert n1 >= 1, "tour đã kết thúc mà không sinh phiếu nào thì cả phân hệ này vô nghĩa"
    ds = client.get("/api/v1/cham-soc", headers=h).json()
    assert len(ds) == n1
    # chạy lại: không sinh thêm phiếu nào
    assert client.post("/api/v1/cham-soc/sinh-phieu", headers=h).json()["da_sinh"] == 0
    assert len(client.get("/api/v1/cham-soc", headers=h).json()) == n1
    t = ds[0]; CTX["id"] = t["id"]
    assert t["phu_trach"], "phiếu phải giao sẵn cho nhân viên đã bán, không để trống chờ ai đó phân công"
    assert t["han_lien_he"] and t["status"] == "moi"


def test_c2_khong_lien_he_duoc_thi_phai_ghi_ly_do():
    h = login("cntt")
    r = client.put(f"/api/v1/cham-soc/{CTX['id']}", json={"hinh_thuc": "goi", "lien_he_duoc": "khong"}, headers=h)
    assert r.status_code == 422 and "lý do" in r.json()["detail"]


def test_c3_lien_he_duoc_thi_phai_cham_diem_va_tra_loi_hai_cau_bat_buoc():
    h = login("cntt"); i = CTX["id"]
    assert client.put(f"/api/v1/cham-soc/{i}", json={"hinh_thuc": "goi", "lien_he_duoc": "co"}, headers=h).status_code == 422
    assert client.put(f"/api/v1/cham-soc/{i}", json={"hinh_thuc": "goi", "lien_he_duoc": "co", "hai_long": 5},
                      headers=h).status_code == 422
    r = client.put(f"/api/v1/cham-soc/{i}", json={"hinh_thuc": "goi", "lien_he_duoc": "co", "hai_long": 5,
                                                  "nhu_cau_tiep": "khong"}, headers=h)
    # thiếu câu "đồng ý cho dùng đánh giá" – đưa nhận xét khách lên fanpage khi khách chưa đồng ý là dùng
    # thông tin cá nhân sai mục đích
    assert r.status_code == 422 and "đánh giá" in r.json()["detail"]
    assert client.put(f"/api/v1/cham-soc/{i}", json={"hinh_thuc": "khong_co", "lien_he_duoc": "co", "hai_long": 5,
                                                     "nhu_cau_tiep": "khong", "dong_y_dung_danh_gia": "co"},
                      headers=h).status_code == 422


def _them_phieu(n: int) -> list:
    """Thêm tour kết thúc + booking để có phiếu mà thử, vì dữ liệu mẫu chỉ có một chuyến đã kết thúc."""
    from app.db.session import SessionLocal
    from app.models.core import Tour, Booking, User
    from sqlalchemy import select
    db = SessionLocal()
    sale = db.execute(select(User).where(User.username == "kd.hoa")).scalars().first()
    dh = db.execute(select(User).where(User.username == "dh.lan")).scalars().first()
    t = Tour(code=f"CS-TEST-{n}", name="Chuyến thử chăm sóc", tour_type="le_noi_dia",
             start_date=date.today() - timedelta(days=6), end_date=date.today() - timedelta(days=4),
             operator_id=dh.id, price_per_pax=2_000_000, planned_pax=2, status="ket_thuc")
    db.add(t); db.flush()
    b = Booking(code=f"BKCS{n:04d}", tour_id=t.id, request_id=0, sales_id=sale.id, created_by=dh.id,
                customer_name=f"Khách thử {n}", customer_phone=f"09880000{n:02d}", source="Zalo",
                pax=2, amount=4_000_000)
    db.add(b); db.commit(); bid = b.id; db.close()
    return bid


def test_c4_diem_hai_long_thap_thi_tu_mo_ho_so_khieu_nai():
    h = login("cntt"); _them_phieu(1)
    client.post("/api/v1/cham-soc/sinh-phieu", headers=h)
    p = [x for x in client.get("/api/v1/cham-soc?status=moi", headers=h).json() if x["customer_name"] == "Khách thử 1"][0]
    r = client.put(f"/api/v1/cham-soc/{p['id']}", json={"hinh_thuc": "goi", "lien_he_duoc": "co", "hai_long": 2,
                                                        "diem_chua_hai_long": ["hdv", "xe"], "nhu_cau_tiep": "khong",
                                                        "dong_y_dung_danh_gia": "khong",
                                                        "ghi_chu": "Khách nói hướng dẫn viên bỏ đoàn buổi tối"}, headers=h)
    assert r.status_code == 200
    t = r.json()["ticket"]
    assert t["complaint_id"], "khách chấm 2/5 mà không ai lập hồ sơ thì lời đó chết ngay tại phiếu này"
    CTX["kn"] = t["complaint_id"]
    c = client.get(f"/api/v1/khieu-nai/{t['complaint_id']}", headers=h).json()
    assert c["source"] == "cham_soc" and c["level"] == 2 and c["nhom"] == "hdv"
    assert c["booking_id"] == t["booking_id"]
    assert "2/5" in c["noi_dung"]
    assert c["de_nghi_khach"] == "", "chưa ai hỏi khách đề nghị gì – bịa ra một đề nghị cho đủ ô là tệ hơn để trống"


def test_c5_khach_con_nhu_cau_thi_tu_tao_lead_khach_cu():
    h = login("cntt"); _them_phieu(2)
    client.post("/api/v1/cham-soc/sinh-phieu", headers=h)
    p = [x for x in client.get("/api/v1/cham-soc?status=moi", headers=h).json() if x["customer_name"] == "Khách thử 2"][0]
    r = client.put(f"/api/v1/cham-soc/{p['id']}", json={"hinh_thuc": "zalo", "lien_he_duoc": "co", "hai_long": 5,
                                                        "nhu_cau_tiep": "co", "dong_y_dung_danh_gia": "co",
                                                        "ghi_chu": "Muốn đi Nha Trang tháng sau"}, headers=h)
    assert r.status_code == 200
    t = r.json()["ticket"]
    assert t["lead_id"] and not t["complaint_id"]
    from app.db.session import SessionLocal
    from app.models.crm import Lead
    db = SessionLocal(); l = db.get(Lead, t["lead_id"])
    assert l.channel == "khach_cu" and l.sales_id == p["owner_id"], "lead khách cũ phải về đúng nhân viên đã bán"
    db.close()


def test_c6_ho_so_tu_mo_khong_dong_duoc_khi_chua_hoi_de_nghi_cua_khach():
    h = login("cntt")
    d = {"nguyen_nhan_nhom": "do_ta", "nguyen_nhan": "HDV rời đoàn không xin phép.",
         "huong_xu_ly": ["xin_loi"], "khach_chap_nhan": "co"}
    r = client.post(f"/api/v1/khieu-nai/{CTX['kn']}/dong", json=d, headers=h)
    assert r.status_code == 422 and "ĐỀ NGHỊ CỦA KHÁCH" in r.json()["detail"]
    r = client.post(f"/api/v1/khieu-nai/{CTX['kn']}/dong",
                    json=dict(d, de_nghi_khach="Khách đề nghị được xin lỗi và tặng voucher lần sau"), headers=h)
    assert r.status_code == 200 and r.json()["complaint"]["status"] == "da_dong"


def test_c7_chi_so_do_viec_lam_that():
    h = login("cntt")
    k = client.get("/api/v1/cham-soc/chi-so", headers=h).json()
    assert k["tong_phieu"] >= 3 and k["da_ghi"] >= 2
    assert k["chua_ghi"] == k["tong_phieu"] - k["da_ghi"]
    assert 0 < k["ty_le_lien_he"] <= 1 and k["hai_long_tb"] > 0
    assert k["lead_khach_cu"] >= 1 and k["khieu_nai_tu_mo"] >= 1


def test_c8_khong_co_duong_tao_phieu_cho_mot_khach_le():
    h = login("cntt")
    r = client.post("/api/v1/cham-soc", json={"booking_id": 1}, headers=h)
    assert r.status_code in (404, 405), "có nút thêm phiếu tay là mở đường cho một danh sách chỉ đầy đủ hai tuần đầu"


def test_c9_khong_mo_phieu_cho_toan_bo_lich_su_chuyen_da_dong():
    """Chuyến kết thúc từ lâu không tự sinh phiếu; muốn bù thì phải chỉ đích danh chuyến đó.

    Không có giới hạn này thì lần chạy đầu trên dữ liệu thật sẽ mở hàng nghìn việc, tất cả đều quá hạn
    liên hệ ngay từ lúc sinh ra – và con số "bao nhiêu phiếu chưa ai đụng tới" mất hết ý nghĩa.
    """
    from app.db.session import SessionLocal
    from app.models.core import Tour, Booking, User
    from sqlalchemy import select
    h = login("cntt")
    db = SessionLocal()
    sale = db.execute(select(User).where(User.username == "kd.hoa")).scalars().first()
    dh = db.execute(select(User).where(User.username == "dh.lan")).scalars().first()
    t = Tour(code="CS-TEST-CU", name="Chuyến đóng từ năm ngoái", tour_type="le_noi_dia",
             start_date=date.today() - timedelta(days=400), end_date=date.today() - timedelta(days=398),
             operator_id=dh.id, price_per_pax=1_000_000, planned_pax=1, status="ket_thuc")
    db.add(t); db.flush()
    db.add(Booking(code="BKCSCU01", tour_id=t.id, request_id=0, sales_id=sale.id, created_by=dh.id,
                   customer_name="Khách năm ngoái", customer_phone="0988000999", source="Zalo",
                   pax=1, amount=1_000_000))
    db.commit(); tid = t.id; db.close()
    assert client.post("/api/v1/cham-soc/sinh-phieu", headers=h).json()["da_sinh"] == 0
    # nhưng người phụ trách vẫn xin bù được cho đúng chuyến đó
    assert client.post(f"/api/v1/cham-soc/sinh-phieu?tour_id={tid}", headers=h).json()["da_sinh"] == 1


def test_c10_phieu_bu_cho_chuyen_cu_khong_duoc_sinh_ra_da_qua_han():
    """Hạn liên hệ đếm từ ngày muộn hơn giữa ngày kết thúc chuyến và hôm nay.

    C9 vừa bù phiếu cho một chuyến đóng cách đây 398 ngày. Nếu hạn đếm từ ngày kết thúc chuyến thì phiếu
    ấy sinh ra đã trễ 395 ngày: một món nợ hệ thống tự bịa ra rồi tự đi đòi, và bảng cảnh báo đầy những
    dòng không ai xử lý được vì không ai liên hệ được với khách trước khi phiếu tồn tại.
    """
    from app.db.session import SessionLocal
    from app.models.cskh import CareTicket
    from app.models.core import Tour
    from sqlalchemy import select
    db = SessionLocal()
    t = db.execute(select(Tour).where(Tour.code == "CS-TEST-CU")).scalars().first()
    p = db.execute(select(CareTicket).where(CareTicket.tour_id == t.id)).scalars().first()
    han = p.han_lien_he; db.close()
    assert han >= date.today(), f"phiếu bù sinh ra đã quá hạn: hạn {han}, hôm nay {date.today()}"


def test_c11_robot_va_lai_han_va_go_canh_bao_gia():
    """Phiếu lỡ mang hạn sớm hơn chính ngày nó được tạo thì robot phải vá, và rút cảnh báo dựng trên nó.

    Đây là vá cho dữ liệu đã lỡ sinh sai trước bản sửa, và là lý do bảng cảnh báo trên máy chủ thật đang
    đầy dòng cham_soc_qua_han. Phép thử dựng đúng cảnh báo cũ ấy rồi bắt robot dọn.

    Kiểm cả chiều ngược: phiếu quá hạn THẬT – hạn muộn hơn ngày tạo nhưng đã trôi qua – thì không được
    vá và cảnh báo phải giữ nguyên. Vá quá tay là xoá dấu vết trễ có thật.
    """
    from datetime import datetime
    from app.db.session import SessionLocal
    from app.services import cskh as CS
    from app.models.cskh import CareTicket
    from app.models.core import Alert, Tour
    from sqlalchemy import select
    db = SessionLocal()
    t = db.execute(select(Tour).where(Tour.code == "CS-TEST-CU")).scalars().first()
    tid = t.id
    p = db.execute(select(CareTicket).where(CareTicket.tour_id == tid)).scalars().first()
    pid = p.id
    p.han_lien_he = date.today() - timedelta(days=395); p.status = "moi"
    # đúng cảnh báo mà máy chủ thật đang treo
    db.add(Alert(kind="cham_soc_qua_han", level="warn", ref=f"cs:{tid}",
                 message="10 phiếu chăm sóc sau bán của chuyến CS-TEST-CU đã quá hạn liên hệ",
                 to_roles="gd_kd,tp_kd,ptgd_mkt"))
    db.commit()

    r = CS.robot_cskh(db)
    assert r["phieu_va_han"] >= 1, "phiếu mang hạn sớm hơn ngày nó ra đời mà robot không vá"
    db.expire_all()
    assert db.get(CareTicket, pid).han_lien_he >= date.today()
    assert r["canh_bao_go"] >= 1, "cảnh báo chỉ thêm mà không bao giờ tự rút thì bảng cảnh báo dài mãi"
    assert db.execute(select(Alert).where(Alert.kind == "cham_soc_qua_han", Alert.ref == f"cs:{tid}",
                                          Alert.resolved == False)).scalars().first() is None

    # chiều ngược: trễ thật thì phải để yên
    p2 = db.get(CareTicket, pid)
    p2.created_at = datetime.now() - timedelta(days=40)
    p2.han_lien_he = date.today() - timedelta(days=30)
    p2.status = "moi"; db.commit()
    r2 = CS.robot_cskh(db)
    db.expire_all()
    assert db.get(CareTicket, pid).han_lien_he == date.today() - timedelta(days=30), \
        "trễ thật mà bị vá hạn thì hệ thống đang xoá dấu vết chậm việc"
    assert db.execute(select(Alert).where(Alert.kind == "cham_soc_qua_han", Alert.ref == f"cs:{tid}",
                                          Alert.resolved == False)).scalars().first() is not None, \
        "phiếu trễ thật mà không có cảnh báo thì cả chỉ số chăm sóc thành vô nghĩa"
    db.close()
