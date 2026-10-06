"""Phòng HDV Đợt 1 — yêu cầu HDV, hai mốc giờ, và cấm hai chuyến chồng giờ.

Chủ tịch chốt 06/10/2026, bộ này giữ đúng những điều ấy:

  A. Có chỗ chứa một chuyến CHƯA xếp được người, và đếm được phần còn thiếu.
  B. Chồng giờ là CẤM, không phải cảnh báo rồi vẫn ghi.
  C. Nối tiếp liền mạch (về đúng 18h, đi đúng 18h) KHÔNG phải chồng giờ.
  D. Thiếu giờ thì KHÔNG kết luận "đã kiểm, không trùng" — nó là việc còn thiếu và phải hiện ra.
  E. Gỡ giờ được, và gỡ xong thì quay lại danh sách việc còn thiếu.
  F. Từ chối thì không chiếm lịch nữa, nhưng yêu cầu phải thiếu người trở lại.
  G. Hai phiên cùng xếp một người vào một khoảng — chỉ một phiên vào được.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hdv1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hdv1.db"):
    os.remove("test_hdv1.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
ID = {}
# Dùng tài khoản CNTT để thử, KHÔNG phải vì nghiệp vụ mà vì ma trận quyền: nhóm API
# `/api/v1/guide-assignments` hiện chỉ mở cho `tp_hd` (Trưởng phòng Hướng dẫn) — mà vai trò ấy CHƯA
# CÓ TÀI KHOẢN nào trong hệ thống — cùng vài vai quản trị. Điều hành (`nv_dh`, `tp_dh`) là người sẽ
# gửi yêu cầu HDV hằng ngày thì hiện BỊ CHẶN. Khai quyền cho họ là việc của làn Phân quyền, không
# phải việc của bản ghi này; chỗ này chỉ ghi lại để người sau biết vì sao phép thử đăng nhập bằng CNTT.
AI = "cntt"
# Mốc giờ dùng chung: 20/11/2026, một ngày không lễ không Tết để đơn giá không nhân đôi.
D = datetime(2026, 11, 20, 6, 0)


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideRate

        db = SessionLocal()
        # `operator_id` là cột bắt buộc của chuyến – lấy một tài khoản có sẵn của bộ gieo demo thay vì
        # bịa một số: khoá ngoại trỏ tới hàng không tồn tại là một lỗi khác hẳn lỗi đang muốn thử.
        dh = db.execute(select(User).where(User.username == "tp.dieuhanh")).scalars().first()
        op_id = dh.id if dh else db.execute(select(User)).scalars().first().id
        # Hai chuyến và hai hướng dẫn viên. Dựng thẳng bằng mô hình chứ không qua cửa API: bộ này thử
        # phần GIỜ và phần CHẶN TRÙNG, không thử cửa tạo chuyến.
        t1 = Tour(code="HDV-T1", name="Đà Lạt 3 ngày", tour_type="le_noi_dia", operator_id=op_id, start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        t2 = Tour(code="HDV-T2", name="Nha Trang 3 ngày", tour_type="le_noi_dia", operator_id=op_id, start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([t1, t2])
        gr = GuideRate(route="Đà Lạt", days=3, rate_per_day=800_000,
                       effective_from=date(2026, 1, 1), status="active")
        db.add(gr)
        # Cổng 13 đòi thẻ HDV còn hạn, hội viên tổ chức nghề nghiệp và hợp đồng cộng tác. Dựng đủ
        # cho CẢ HAI người: nếu một người không qua cổng thì phép thử "hai người cùng một giờ vẫn
        # xếp được" sẽ đỏ vì lý do khác, và ta sẽ tưởng phép chặn trùng đang chặn nhầm.
        def _hdv(ma, ten):
            return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                            start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                            member_org=True, contract_type="ctv",
                            ctv_contract=True)
        e1, e2 = _hdv("HDVT01", "Nguyễn Văn A"), _hdv("HDVT02", "Trần Văn B")
        db.add_all([e1, e2])
        db.commit()
        ID.update(t1=t1.id, t2=t2.id, gr=gr.id, e1=e1.id, e2=e2.id)
        db.close()
        yield


def _lap_yc(**kw):
    than = {"tour_id": ID["t1"], "so_hdv": 1}
    than.update(kw)
    return client.post("/api/v1/guide-assignments/yeu-cau", json=than, headers=login(AI))


def _phan_cong(**kw):
    than = {"tour_id": ID["t1"], "guide_id": ID["e1"], "days": 3, "rate_per_day": 800_000}
    than.update(kw)
    return client.post("/api/v1/guide-assignments", json=than, headers=login(AI))


# ───────────────────────────── A · chỗ chứa cái chưa xếp được ─────────────────────────────
def test_a1_lap_duoc_yeu_cau_va_dem_duoc_phan_con_thieu():
    r = _lap_yc(so_hdv=2, bat_dau=D.isoformat(), ket_thuc=(D + timedelta(days=3)).isoformat())
    assert r.status_code == 201, r.text
    ID["yc"] = r.json()["id"]
    ds = client.get("/api/v1/guide-assignments/yeu-cau", headers=login(AI)).json()
    mine = [y for y in ds if y["id"] == ID["yc"]][0]
    assert mine["con_thieu"] == 2, "xin 2 người, chưa xếp ai thì còn thiếu đúng 2"
    assert mine["trang_thai"] == "moi"


def test_a2_xep_mot_nguoi_thi_con_thieu_mot_chu_khong_phai_da_du():
    r = _phan_cong(yeu_cau_id=ID["yc"], bat_dau=D.isoformat(),
                   ket_thuc=(D + timedelta(days=3)).isoformat())
    assert r.status_code == 201, r.text
    ds = client.get("/api/v1/guide-assignments/yeu-cau", headers=login(AI)).json()
    mine = [y for y in ds if y["id"] == ID["yc"]][0]
    assert mine["con_thieu"] == 1
    assert mine["trang_thai"] == "dang_xep", "xếp một phần KHÁC đã đủ – đây là chỗ màn hình hay báo sai"


def test_a3_so_hdv_khong_duong_thi_tu_choi():
    assert _lap_yc(so_hdv=0).status_code == 422


# ───────────────────────────── B · chồng giờ là cấm ─────────────────────────────
def test_b1_cung_nguoi_chong_gio_thi_tu_choi_va_noi_ro_chuyen_nao():
    r = _phan_cong(tour_id=ID["t2"], guide_id=ID["e1"],
                   bat_dau=(D + timedelta(days=1)).isoformat(),
                   ket_thuc=(D + timedelta(days=4)).isoformat())
    assert r.status_code == 422, r.text
    ct = r.json()["detail"]
    assert ct["gate"] == "TRUNG_GIO_HDV"
    assert "HDV-T1" in ct["message"], "phải nói ra chuyến đang chồng, không chỉ nói 'trùng lịch'"


def test_b2_nguoi_khac_cung_khoang_do_thi_xep_duoc():
    r = _phan_cong(tour_id=ID["t2"], guide_id=ID["e2"],
                   bat_dau=(D + timedelta(days=1)).isoformat(),
                   ket_thuc=(D + timedelta(days=4)).isoformat())
    assert r.status_code == 201, "cấm là cấm MỘT NGƯỜI hai chỗ, không phải cấm hai người một giờ"


def test_b3_tu_choi_roi_thi_khong_ghi_vao_so():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    n = len(db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == ID["t2"], GuideAssignment.guide_id == ID["e1"])).scalars().all())
    db.close()
    assert n == 0, "lần bị chặn ở b1 không được để lại một dòng nửa vời trong sổ"


# ───────────────────────────── C · nối tiếp liền mạch không phải chồng ─────────────────────────────
def test_c1_ve_dung_18h_di_dung_18h_khong_phai_chong_gio():
    from app.services.hdv import chong_gio
    a1, a2 = datetime(2026, 12, 1, 6), datetime(2026, 12, 1, 18)
    b1, b2 = datetime(2026, 12, 1, 18), datetime(2026, 12, 2, 18)
    assert chong_gio(a1, a2, b1, b2) is False, \
        "giao đoàn xong là hết việc; chặn ở đây thì người xếp lịch sẽ lùi giờ một phút để lách"


def test_c2_chong_nhau_mot_gio_thi_bat_duoc():
    from app.services.hdv import chong_gio
    assert chong_gio(datetime(2026, 12, 1, 6), datetime(2026, 12, 1, 18),
                     datetime(2026, 12, 1, 17), datetime(2026, 12, 2, 10)) is True


def test_c3_long_hoan_toan_trong_nhau_cung_la_chong():
    from app.services.hdv import chong_gio
    assert chong_gio(datetime(2026, 12, 1, 6), datetime(2026, 12, 5, 18),
                     datetime(2026, 12, 2, 8), datetime(2026, 12, 3, 8)) is True


# ───────────────────────────── D · thiếu giờ ≠ đã kiểm ─────────────────────────────
def test_d1_thieu_gio_thi_khong_so_duoc_chu_khong_phai_khong_chong():
    from app.services.hdv import chong_gio, khong_so_duoc
    assert khong_so_duoc(None, datetime(2026, 12, 1, 18)) is True
    assert chong_gio(None, None, datetime(2026, 12, 1, 6), datetime(2026, 12, 2, 6)) is False
    assert khong_so_duoc(datetime(2026, 12, 1, 18), datetime(2026, 12, 1, 6)) is True, \
        "kết thúc trước bắt đầu là gõ nhầm, phải nói ra chứ không coi là khoảng rỗng"


def test_d2_phan_cong_khong_gio_hien_o_danh_sach_viec_con_thieu():
    r = _phan_cong(tour_id=ID["t2"], guide_id=ID["e1"], days=2)
    assert r.status_code == 201, "cửa cũ chưa bắt buộc giờ – món nợ có chủ ý, xem chú thích AssignIn"
    ID["pc_khong_gio"] = None
    ds = client.get("/api/v1/guide-assignments/yeu-cau/thieu", headers=login(AI)).json()
    assert any(p["tour_code"] == "HDV-T2" for p in ds["phan_cong_chua_co_gio"]), \
        "một con số thiếu mà không ai nhìn thấy thì không ai đi nhập"


def test_d3_cot_gio_o_tang_csdl_phai_de_trong_duoc_va_khong_co_mac_dinh():
    from app.models.hr import GuideAssignment
    for ten in ("bat_dau", "ket_thuc", "gio_luc"):
        c = GuideAssignment.__table__.columns[ten]
        assert c.nullable is True, f"{ten} phải để trống được"
        assert c.default is None and c.server_default is None, \
            f"{ten} có mặc định thì 'chưa ai gõ' biến thành một giờ nào đó"


# ───────────────────────────── E · gỡ giờ được ─────────────────────────────
def test_e1_go_gio_thi_quay_lai_danh_sach_viec_con_thieu():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == ID["t1"], GuideAssignment.guide_id == ID["e1"])).scalars().first()
    aid, pb = a.id, a.phien_ban
    db.close()
    r = client.post(f"/api/v1/guide-assignments/{aid}/gio",
                    json={"phien_ban": pb, "bat_dau": None, "ket_thuc": None},
                    headers=login(AI))
    assert r.status_code == 200, r.text
    ds = client.get("/api/v1/guide-assignments/yeu-cau/thieu", headers=login(AI)).json()
    assert any(p["id"] == aid for p in ds["phan_cong_chua_co_gio"])


def test_e2_dat_lai_gio_trung_thi_van_bi_chan():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == ID["t1"], GuideAssignment.guide_id == ID["e1"])).scalars().first()
    aid, pb = a.id, a.phien_ban
    b = db.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == ID["t2"], GuideAssignment.guide_id == ID["e1"])).scalars().first()
    bid = b.id
    db.close()
    # cho bản ghi kia một khoảng giờ trước
    client.post(f"/api/v1/guide-assignments/{bid}/gio",
                json={"bat_dau": D.isoformat(), "ket_thuc": (D + timedelta(days=2)).isoformat()},
                headers=login(AI))
    r = client.post(f"/api/v1/guide-assignments/{aid}/gio",
                    json={"phien_ban": pb, "bat_dau": D.isoformat(),
                          "ket_thuc": (D + timedelta(days=3)).isoformat()},
                    headers=login(AI))
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "TRUNG_GIO_HDV"


def test_e3_ket_thuc_truoc_bat_dau_thi_tu_choi():
    r = _lap_yc(bat_dau=(D + timedelta(days=2)).isoformat(), ket_thuc=D.isoformat())
    assert r.status_code == 422


# ───────────────────────────── F · từ chối thì nhả lịch ─────────────────────────────
def test_f1_tu_choi_thi_khong_chiem_lich_va_yeu_cau_thieu_nguoi_tro_lai():
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.execute(select(GuideAssignment).where(
        GuideAssignment.yeu_cau_id == ID["yc"])).scalars().first()
    a.status = "tu_choi"
    db.commit()
    db.close()
    ds = client.get("/api/v1/guide-assignments/yeu-cau", headers=login(AI)).json()
    mine = [y for y in ds if y["id"] == ID["yc"]][0]
    assert mine["con_thieu"] == 2, \
        "người đã từ chối không tính là đã có – đây là chỗ màn hình báo 'đã đủ' cho chuyến không còn ai"


def test_f2_huy_yeu_cau_phai_ghi_ly_do():
    r = _lap_yc(so_hdv=1)
    yid = r.json()["id"]
    assert client.post(f"/api/v1/guide-assignments/yeu-cau/{yid}/huy", json={"ly_do": ""},
                       headers=login(AI)).status_code == 422
    assert client.post(f"/api/v1/guide-assignments/yeu-cau/{yid}/huy", json={"ly_do": "Khách huỷ đoàn"},
                       headers=login(AI)).status_code == 200


def test_f3_lech_phien_ban_thi_tra_409_kem_noi_dung_moi():
    r = _lap_yc(so_hdv=1)
    yid = r.json()["id"]
    r2 = client.post(f"/api/v1/guide-assignments/yeu-cau/{yid}/huy",
                     json={"phien_ban": 99, "ly_do": "thử"}, headers=login(AI))
    assert r2.status_code == 409
    assert r2.json()["detail"]["gate"] == "LECH_PHIEN_BAN"
    assert "noi_dung_moi" in r2.json()["detail"]


# ───────────────────────────── G · hai phiên cùng xếp một người ─────────────────────────────
def test_g1_hai_phien_cung_xep_mot_nguoi_chi_mot_phien_vao_duoc():
    """Đây là phép thử quan trọng nhất của Đợt 1.

    Hỏi-trước-rồi-ghi KHÔNG đủ: hai phiên cùng hỏi lúc chưa ai ghi, cả hai cùng thấy trống, cả hai
    cùng ghi. Ở đây dựng đúng cảnh ấy — phiên B chen vào SAU khi phiên A đã kiểm và TRƯỚC khi phiên A
    chốt — rồi đòi hệ thống vẫn chỉ cho đúng một bản ghi sống sót.
    """
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import Tour
    from app.models.hr import GuideAssignment
    from app.services import hdv as HDV

    db_a = SessionLocal()
    db_b = SessionLocal()
    from app.models.core import User as _U
    op_id = db_a.execute(select(_U)).scalars().first().id
    t3 = Tour(code="HDV-T3", name="Phan Thiết", tour_type="le_noi_dia", operator_id=op_id,
              start_date=date(2026, 12, 10), end_date=date(2026, 12, 12))
    db_a.add(t3)
    db_a.commit()
    # Giữ id ra biến NGAY: lớp 2 gọi db_a.rollback(), và sau rollback thì đối tượng t3 rời khỏi phiên –
    # đọc t3.id lúc ấy là một lỗi khác hẳn lỗi đang muốn thử.
    t3_id = t3.id
    bd, kt = datetime(2026, 12, 10, 6), datetime(2026, 12, 12, 18)

    # Phiên A kiểm: trống.
    assert HDV.dang_chiem_lich(db_a, ID["e2"], bd, kt) == []
    # Phiên B chen vào và CHỐT trước.
    b = GuideAssignment(tour_id=t3_id, guide_id=ID["e2"], days=3, rate_per_day=800_000,
                        bat_dau=bd, ket_thuc=kt, assigned_by="phien_b")
    db_b.add(b)
    db_b.commit()
    # Phiên A ghi rồi kiểm lại trước khi chốt – đây là lớp 2.
    a = GuideAssignment(tour_id=t3_id, guide_id=ID["e2"], days=3, rate_per_day=800_000,
                        bat_dau=bd, ket_thuc=kt, assigned_by="phien_a")
    db_a.add(a)
    db_a.flush()
    with pytest.raises(Exception) as e:
        HDV.canh_trung_sau_khi_ghi(db_a, a)
    assert "TRUNG_GIO_HDV" in str(e.value.detail)

    db_a.close()
    con = db_b.execute(select(GuideAssignment).where(
        GuideAssignment.tour_id == t3_id, GuideAssignment.guide_id == ID["e2"])).scalars().all()
    db_b.close()
    assert len(con) == 1, "hai phiên cùng xếp một người vào một khoảng – chỉ một phiên được vào sổ"
