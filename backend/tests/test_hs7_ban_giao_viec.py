# -*- coding: utf-8 -*-
"""HS-7 — bàn giao việc đang mở: việc ĐANG MỞ đổi người, lịch sử Ở LẠI.

Phép thử nặng nhất ở đây là `test_hs7_2`: nó dựng cho người nghỉ CẢ HAI loại — một tour đang bán
với booking của nó, và một tour đã kết thúc với booking của nó — rồi đòi đúng cái thứ nhất đổi
người và đúng cái thứ hai không đổi. Một cửa bàn giao chuyển nhầm phần lịch sử thì doanh số kỳ đã
chốt đổi chủ, và không ai phát hiện cho tới kỳ đánh giá.

`test_hs7_1` là hàng rào cho tương lai: thêm một bảng mang khoá ngoại tới `users.id` mà quên phân
loại thì đỏ ở đây. Thiếu nó, bảng mới lặng lẽ KHÔNG được bàn giao, và chỗ sót chỉ lộ ra khi có
người đi tìm việc của người đã nghỉ và không thấy ai nhận.
"""
import os, sys, tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hs7.db")
for _f in (_DB, _DB + "-journal"):
    if os.path.exists(_f):
        try: os.remove(_f)
        except OSError: pass
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.core import Booking, ServiceRequest, Tour, User

client = TestClient(app)
MK = "bangiao_123456"
NGHI = NHAN = None          # id tài khoản người giao / người nhận
TOUR_MO = TOUR_DONG = None
BK_MO = BK_DONG = None


@pytest.fixture(scope="module", autouse=True)
def _dung_du_lieu():
    global client, NGHI, NHAN, TOUR_MO, TOUR_DONG, BK_MO, BK_DONG
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()

        for un, vai in (("hs7_hcns", "hcns"), ("hs7_nghi", "nv_kd"), ("hs7_nhan", "nv_kd")):
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thu {un}", role=vai, department="kd_le",
                            password_hash=hash_password(MK), active=True))
        db.flush()
        NGHI = db.execute(select(User).where(User.username == "hs7_nghi")).scalars().first().id
        NHAN = db.execute(select(User).where(User.username == "hs7_nhan")).scalars().first().id

        hom_nay = date.today()
        t_mo = Tour(code="HS7-MO", name="Tour dang ban", status="da_duyet",
                    tour_type="le_noi_dia",
                    start_date=hom_nay + timedelta(days=20), end_date=hom_nay + timedelta(days=23),
                    operator_id=NGHI)
        t_dong = Tour(code="HS7-DONG", name="Tour da ket thuc", status="ket_thuc",
                      tour_type="le_noi_dia",
                      start_date=hom_nay - timedelta(days=40), end_date=hom_nay - timedelta(days=37),
                      operator_id=NGHI)
        db.add_all([t_mo, t_dong]); db.flush()
        TOUR_MO, TOUR_DONG = t_mo.id, t_dong.id

        # Booking đòi `request_id`: mỗi booking sinh ra từ một yêu cầu dịch vụ.
        yc_mo = ServiceRequest(tour_id=t_mo.id, sales_id=NGHI, customer_name="Khach A",
                               customer_phone="0900000001", source="thu")
        yc_dong = ServiceRequest(tour_id=t_dong.id, sales_id=NGHI, customer_name="Khach B",
                                 customer_phone="0900000002", source="thu")
        db.add_all([yc_mo, yc_dong]); db.flush()
        b_mo = Booking(code="HS7-BK-MO", tour_id=t_mo.id, request_id=yc_mo.id,
                       customer_name="Khach A", customer_phone="0900000001",
                       source="thu", sales_id=NGHI, created_by=NGHI, cancelled=False)
        b_dong = Booking(code="HS7-BK-DONG", tour_id=t_dong.id, request_id=yc_dong.id,
                         customer_name="Khach B", customer_phone="0900000002",
                         source="thu", sales_id=NGHI, created_by=NGHI, cancelled=False)
        db.add_all([b_mo, b_dong]); db.flush()
        BK_MO, BK_DONG = b_mo.id, b_dong.id
        db.commit(); db.close()
        yield


def dang_nhap(un):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


DUONG = "/api/v1/bien-dong-ns/ban-giao-viec"


def goi(tu, den, ly_do="Nghi viec 31/10", xac_nhan=False, vai="hs7_hcns"):
    return client.post(DUONG, headers=dang_nhap(vai),
                       json={"tu_user_id": tu, "den_user_id": den,
                             "ly_do": ly_do, "xac_nhan": xac_nhan})


# ---------------------------------------------------------------------------------------------
def test_hs7_1_moi_khoa_ngoai_toi_users_deu_duoc_phan_loai():
    """28 cặp (bảng, cột) trỏ vào `users.id`, mỗi cặp phải nằm ĐÚNG MỘT nhóm.

    Không có hàng rào này thì một bảng mới sinh ra sẽ lặng lẽ KHÔNG được bàn giao — và im lặng là
    kiểu hỏng tệ nhất ở đây, vì nó trông y hệt "người ấy không có việc gì đang mở".
    """
    from app.services import ban_giao_viec as BG
    from app.services.gop_tai_khoan import cot_tro_toi_users

    tat_ca = set(cot_tro_toi_users())
    chuyen = set((b, c) for b, c, _, _ in BG.CHUYEN)
    giu, khong = set(BG.GIU), set(BG.KHONG_PHAI_VIEC)

    thieu = tat_ca - (chuyen | giu | khong)
    assert not thieu, (
        f"Chưa phân loại {sorted(thieu)}. Mỗi cột trỏ tới `users.id` phải nằm đúng một nhóm: "
        "CHUYEN (việc đang mở) · GIU (lịch sử, ở lại với tên người cũ) · KHONG_PHAI_VIEC.")
    thua = (chuyen | giu | khong) - tat_ca
    assert not thua, f"Phân loại {sorted(thua)} mà không còn cột nào như thế — dọn danh sách."

    for cap in sorted(tat_ca):
        o = [t for t, s in (("CHUYEN", chuyen), ("GIU", giu), ("KHONG_PHAI_VIEC", khong)) if cap in s]
        assert len(o) == 1, f"{cap} nằm ở {o} — phải đúng một nhóm, không hai, không không."


def test_hs7_2_viec_dang_mo_doi_nguoi_lich_su_o_lai():
    """Phép thử trung tâm của vòng. Cùng một người, hai tour, hai booking — một bên mở một bên
    đóng — và chỉ bên mở được đổi chủ."""
    from app.db.session import SessionLocal

    r = goi(NGHI, NHAN, xac_nhan=True)
    assert r.status_code == 200, r.text
    assert r.json()["da_chuyen"] is True

    db = SessionLocal()
    try:
        assert db.get(Tour, TOUR_MO).operator_id == NHAN, "Tour đang bán phải đổi người điều hành."
        assert db.get(Tour, TOUR_DONG).operator_id == NGHI, (
            "Tour ĐÃ KẾT THÚC bị đổi người — đó là viết lại lịch sử, và quyết toán của nó sẽ mang "
            "tên người chưa từng chạy tour ấy.")
        assert db.get(Booking, BK_MO).sales_id == NHAN, "Booking của tour đang bán phải đổi sale."
        assert db.get(Booking, BK_DONG).sales_id == NGHI, (
            "Booking của tour đã kết thúc bị đổi sale — doanh số kỳ đã chốt đổi chủ.")
        assert db.get(Booking, BK_MO).created_by == NGHI, (
            "`created_by` bị đổi — ai TẠO booking là một sự kiện đã xảy ra, không bàn giao được.")
    finally:
        db.close()


def test_hs7_3_xem_truoc_khong_ghi_gi():
    """`xac_nhan=false` phải là bước KHÔNG LÀM GÌ, và phải kê cả phần Ở LẠI."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    truoc = db.get(Tour, TOUR_MO).operator_id
    db.close()

    r = goi(NHAN, NGHI, xac_nhan=False)       # đổi chiều, chỉ xem
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["da_chuyen"] is False
    assert "se_chuyen" in d and "o_lai" in d, (
        "Bản xem trước thiếu phần `o_lai`. Chỉ kê thứ sắp chuyển sẽ khiến người bấm tin rằng mọi "
        "thứ khác không tồn tại.")

    db = SessionLocal()
    assert db.get(Tour, TOUR_MO).operator_id == truoc, "Bản xem trước đã GHI — nó không được ghi."
    db.close()


def test_hs7_4_chan_dung_ba_cho():
    """Ba cách bấm sai, ba câu từ chối khác nhau — không gộp thành một câu chung chung."""
    assert goi(NGHI, NGHI, xac_nhan=True).status_code == 422, "Bàn giao cho chính mình phải bị chặn."
    assert goi(NGHI, NHAN, ly_do="", xac_nhan=True).status_code == 422, (
        "Bàn giao không ghi lý do phải bị chặn — người nhận cần biết vì sao việc đến tay mình.")

    from app.db.session import SessionLocal
    db = SessionLocal()
    u = db.get(User, NHAN); u.active = False; db.commit(); db.close()
    try:
        r = goi(NGHI, NHAN, xac_nhan=True)
        assert r.status_code == 422, (
            "Bàn giao vào tài khoản ĐÃ KHOÁ phải bị chặn — đó là giấu việc đi chứ không phải "
            "giao việc.")
    finally:
        db = SessionLocal(); u = db.get(User, NHAN); u.active = True; db.commit(); db.close()


def test_hs7_5_vai_khong_du_quyen_thi_khong_goi_duoc():
    """Đóng một người khỏi bảng lương và quyết việc của họ về tay ai là cùng một mức hệ quả."""
    r = client.post(DUONG, headers=dang_nhap("hs7_nghi"),
                    json={"tu_user_id": NGHI, "den_user_id": NHAN, "ly_do": "thu", "xac_nhan": True})
    assert r.status_code in (403, 422), (
        f"Vai nv_kd gọi được cửa bàn giao (mã {r.status_code}) — cửa phải khai đúng bộ vai `GHI`.")


def test_hs7_6_phan_cong_kd_dong_chang_cu_mo_chang_moi():
    """Sửa thẳng tên trên dòng phân công cũ thì doanh số THÁNG TRƯỚC cũng đổi chủ, vì báo cáo kỳ
    cũ đọc `tu_ngay`/`den_ngay`. Đóng–mở thì kỳ đã chốt giữ nguyên số."""
    from app.db.session import SessionLocal
    from app.models.to_chuc_kd import DonViKD, PhanCongKD

    db = SessionLocal()
    try:
        dv = db.execute(select(DonViKD).where(DonViKD.ma == "HS7DV")).scalars().first()
        if dv is None:
            # Dựng đơn vị thử thay vì bỏ qua: một phép thử bị skip trông y hệt một phép thử xanh
            # trong dòng tóm tắt, và chỗ nó canh thì không ai canh nữa.
            dv = DonViKD(ma="HS7DV", ten="Don vi thu HS7", cap="team",
                         hieu_luc_tu=date.today() - timedelta(days=365))
            db.add(dv); db.flush()
        cu = PhanCongKD(user_id=NGHI, don_vi_id=dv.id, vai="nv",
                        tu_ngay=date.today() - timedelta(days=60), den_ngay=None,
                        ly_do="thu", boi="hs7_hcns")
        db.add(cu); db.commit(); cu_id = cu.id
    finally:
        db.close()

    assert goi(NGHI, NHAN, xac_nhan=True).status_code == 200

    db = SessionLocal()
    try:
        cu = db.get(PhanCongKD, cu_id)
        assert cu.user_id == NGHI, "Dòng phân công CŨ bị đổi tên người — kỳ đã chốt sẽ đổi số."
        assert cu.den_ngay == date.today(), "Dòng phân công cũ chưa được đóng bằng ngày hôm nay."
        moi = db.execute(select(PhanCongKD).where(PhanCongKD.user_id == NHAN,
                                                  PhanCongKD.den_ngay.is_(None))).scalars().all()
        assert moi, "Không mở chặng mới cho người nhận — việc biến mất khỏi cả hai người."
        assert all(m.tu_ngay > date.today() for m in moi), (
            "Chặng mới bắt đầu từ hôm nay hoặc sớm hơn — chồng lên chặng cũ, một ngày hai chủ.")
    finally:
        db.close()
