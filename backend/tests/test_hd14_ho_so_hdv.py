# -*- coding: utf-8 -*-
"""HD-14 — HỒ SƠ HƯỚNG DẪN VIÊN. Chủ tịch duyệt hai bản xem thử 17/10 và 20/10/2026.

Lát 1: tầng dịch vụ. Chưa có cửa và chưa có màn hình — cố ý, để lát này tự kiểm được một mình.

A. Ngưỡng hiện điểm: dưới ngưỡng thì KHÔNG có số điểm, nhưng số lượt vẫn thật.
B. Chỉ nhận xét ĐƯỢC HIỆN mới ra, và điều kiện ấy hỏi đúng một chỗ.
C. Nhãn người viết không bao giờ mang tên khách.
D. Không phải hướng dẫn viên thì không có hồ sơ.
E. Chưa có Đợt HD-13 thì phần trả về KHÔNG mang khoá tuyến.
F. Cửa đọc: chưa đăng nhập thì không vào được, vai không được mở thì 403, người không phải hướng
   dẫn viên thì 404 — không phải một trang rỗng.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd14.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd14.db"):
    os.remove("test_hd14.db")

import inspect  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.services import dong_y as DY  # noqa: E402
from app.services import ho_so_hdv as HS  # noqa: E402

ID: dict = {}
MK = "Vtos@Demo#2026"
# Tên mang mã đợt — bài học HD-DG2: tên chung thì hai bộ chạy cùng lượt sập ở bước dựng.
AI = {"tp_hd": "thang_hd14", "nv_mkt": "mkt_hd14"}
client = TestClient(app)


def _h(vai):
    r = client.post("/api/v1/auth/login", data={"username": AI[vai], "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _mot_danh_gia(db, guide_id, diem, nhan_xet, cong_khai):
    """Dựng một nhận xét, và nếu `cong_khai` thì đưa nó qua đủ hai cửa của Đợt HD-DG3.

    BA KHOÁ `care_id` / `booking_id` / `tour_id` ĐỀU BẮT BUỘC trong `models/danh_gia.py`. Bản
    đầu của tệp này bỏ trống hai trong ba, và cả mười một phép thử đỏ ở bước dựng cảnh bằng một
    lỗi NOT NULL trông như lỗi thật — 21/10/2026.
    """
    from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai

    dg = DanhGiaSauTour(care_id=ID["care"], booking_id=ID["booking"], tour_id=ID["tour"],
                        doi_tuong="hdv", doi_tuong_id=guide_id, doi_tuong_ten="", diem=diem,
                        nhan_xet=nhan_xet, nguon="khach", nguoi_ghi="",
                        tao_luc=datetime.now())
    db.add(dg)
    db.flush()
    if cong_khai:
        DY.ghi_tra_loi(db, dg, "co")
        r = db.query(DongYCongKhai).filter(DongYCongKhai.danh_gia_id == dg.id).first()
        r.duyet_boi = "chutich_hd14"
        r.duyet_luc = datetime.now()
        r.duyet_bang_quyen = "vai"
        r.duyet_ket_qua = "dang"
        db.flush()
        # Tiền đề của cả nhóm B: nếu bốn ô trên không đủ để `cong_khai_duoc` trả True thì phép thử
        # phải đỏ NGAY ĐÂY với lời báo rõ, chứ không đỏ ở một chỗ xa trông như lỗi khác.
        assert DY.cong_khai_duoc(r), (
            "Dựng dữ liệu sai: bốn ô duyệt chưa đủ để cong_khai_duoc() trả True. "
            "Đọc lại services/dong_y.cong_khai_duoc rồi sửa hàm dựng này, không sửa luật.")
    return dg


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.models.core import Booking, Tour, User
        from app.models.cskh import CareTicket
        from app.models.hr import Employee

        db = _db()
        for vai, ten in AI.items():
            if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                db.add(User(username=ten, full_name="Thử " + ten, role=vai,
                            department="Thử", password_hash=hash_password(MK)))
        db.commit()
        op = db.execute(select(User)).scalars().first()

        # DỰNG CHUYẾN RIÊNG mang mã đợt, không mượn chuyến của bộ gieo: bài học HD-DG2 — tên
        # chung thì hai bộ phép thử chạy cùng lượt giẫm lên nhau. Bộ cột tối thiểu dưới đây lấy
        # đúng theo `test_dg3_dong_y_cong_khai.py`, tệp đã chạy xanh trên CI.
        t = Tour(code="HD14-T", name="Chuyen thu HD14", tour_type="le_noi_dia",
                 operator_id=op.id, start_date=date(2026, 9, 12), end_date=date(2026, 9, 15))
        db.add(t)
        db.commit()
        ID["tour"] = t.id

        b = Booking(code="HD14-B", tour_id=t.id, customer_name="Khach HD14",
                    customer_phone="0900000914", pax=1, sales_id=op.id, created_by=op.id,
                    request_id=0, source="thu")
        db.add(b)
        db.commit()
        ID["booking"] = b.id

        ca = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Khach HD14",
                        customer_phone="0900000914", han_lien_he=date(2026, 9, 20))
        db.add(ca)
        db.commit()
        ID["care"] = ca.id

        # Ba người: một đủ ngưỡng, một chưa đủ, một KHÔNG phải hướng dẫn viên.
        du = Employee(code="HD14-DU", full_name="Hdv Du Nguong", department="huong_dan",
                      position="hdv", card_no="HDV-QT-2021-0001", card_type="quoc_te",
                      card_expiry=date.today() + timedelta(days=400), active=True)
        chua = Employee(code="HD14-CHUA", full_name="Hdv Chua Du", department="huong_dan",
                        position="hdv", active=True)
        khong = Employee(code="HD14-KTX", full_name="Nguoi Khong Phai Hdv",
                         department="ketoan", position="nv", active=True)
        db.add_all([du, chua, khong])
        db.flush()
        ID["du"], ID["chua"], ID["khong"] = du.id, chua.id, khong.id

        for i in range(HS.NGUONG_HIEN_DIEM + 2):
            _mot_danh_gia(db, du.id, 5 if i % 2 == 0 else 4,
                          f"Loi khen so {i}" if i < 3 else "", cong_khai=i < 3)
        _mot_danh_gia(db, du.id, 3, "Nhan xet KHONG duoc duyet", cong_khai=False)
        for i in range(3):
            _mot_danh_gia(db, chua.id, 4, f"Khen it {i}", cong_khai=True)
        db.commit()
        db.close()
        yield


# ── A ────────────────────────────────────────────────────────────────────────────────────────
def test_a1_duoi_nguong_thi_khong_co_diem_nhung_van_co_so_luot():
    db = _db()
    d = HS.diem_cua(db, ID["chua"])
    assert d["diem"] is None, "Dưới ngưỡng mà vẫn in điểm — ngưỡng không còn tác dụng."
    assert d["du_nguong"] is False
    assert d["so_luot"] == 3, "Giấu luôn số lượt thì người đọc không biết còn thiếu bao nhiêu."
    db.close()


def test_a2_du_nguong_thi_co_diem():
    db = _db()
    d = HS.diem_cua(db, ID["du"])
    assert d["du_nguong"] is True and d["diem"] is not None
    assert d["so_luot"] >= HS.NGUONG_HIEN_DIEM
    assert 1 <= d["diem"] <= 5
    db.close()


def test_a3_khong_bao_gio_tra_ve_0_thay_cho_chua_du():
    """0 điểm và «chưa đủ lượt» là hai chuyện khác nhau."""
    db = _db()
    assert HS.diem_cua(db, ID["chua"])["diem"] != 0
    db.close()


# ── B ────────────────────────────────────────────────────────────────────────────────────────
def test_b1_chi_nhan_xet_da_duyet_moi_hien():
    db = _db()
    ds = HS.nhan_xet_cong_khai(db, ID["du"])
    assert len(ds) == 3, f"Phải đúng 3 nhận xét được hiện, đang ra {len(ds)}."
    assert all("KHONG duoc duyet" not in x["nhan_xet"] for x in ds)
    db.close()


def test_b2_dich_vu_khong_tu_viet_lai_dieu_kien_cong_khai():
    """Hỏi `cong_khai_duoc`, không dựng cái đầu thứ hai — bài học KN-1."""
    # Soi MÃ THẬT, không soi lời giải thích: bài học 12/10 — một hàng rào quét chuỗi trên cả tệp
    # sẽ bắt luôn đoạn chú thích nói VÌ SAO không được làm thế, và thứ bị xoá đi đầu tiên luôn là
    # lời giải thích.
    ma = "\n".join(d.split("#")[0] for d in inspect.getsource(HS).splitlines())
    assert "cong_khai_duoc" in ma, "Phải gọi dong_y.cong_khai_duoc."
    for cam in ("duyet_ket_qua", "rut_luc", "go_luc", "tra_loi"):
        assert cam not in ma, (
            f"Tệp này đang tự đọc cột `{cam}` — tức là đang viết lại điều kiện công khai lần thứ "
            "hai. Hai bản thì sớm muộn lệch. Gọi dong_y.cong_khai_duoc().")


# ── C ────────────────────────────────────────────────────────────────────────────────────────
def test_c1_nhan_nguoi_viet_khong_mang_ten_khach():
    db = _db()
    for x in HS.nhan_xet_cong_khai(db, ID["du"]):
        assert "Khách đi tour" in x["nhan"], f"Nhãn lạ: {x['nhan']}"
        assert "Khach HD14" not in x["nhan"], "Nhãn đang mang tên khách."
    db.close()


# ── D ────────────────────────────────────────────────────────────────────────────────────────
def test_d1_khong_phai_hdv_thi_khong_co_ho_so():
    db = _db()
    assert HS.ho_so(db, ID["khong"]) is None
    assert HS.ho_so(db, 99999999) is None
    db.close()


def test_d2_ho_so_mot_nguoi_that_thi_du_bon_khoi():
    db = _db()
    h = HS.ho_so(db, ID["du"])
    assert h is not None
    for k in ("ho_ten", "the", "diem", "nhan_xet"):
        assert k in h
    assert h["the"]["trang_thai"] == "con_han"
    db.close()


def test_d3_chua_co_the_thi_chip_noi_dung_chua_co():
    db = _db()
    h = HS.ho_so(db, ID["chua"])
    assert h["the"]["trang_thai"] == "chua_co"
    db.close()


# ── E ────────────────────────────────────────────────────────────────────────────────────────
def test_e1_chua_co_hd13_thi_khong_co_khoa_tuyen():
    db = _db()
    h = HS.ho_so(db, ID["du"])
    for k in h.keys():
        assert "tuyen" not in k, (
            f"Phần trả về đang mang khoá `{k}`. Chưa có Đợt HD-13 thì không có khoá tuyến nào — "
            "một khối rỗng trông y như «chưa dẫn tuyến nào».")
    db.close()


def test_e2_danh_sach_co_du_nguoi_va_du_cot():
    db = _db()
    ds = HS.danh_sach(db)
    ma = {x["ma"] for x in ds}
    assert "HD14-DU" in ma and "HD14-CHUA" in ma
    assert "HD14-KTX" not in ma, "Người không phải hướng dẫn viên lọt vào danh sách."
    mot = [x for x in ds if x["ma"] == "HD14-CHUA"][0]
    assert mot["diem"] is None and mot["so_luot"] == 3
    db.close()


# ── F · CỬA ĐỌC ──────────────────────────────────────────────────────────────────────────────
def test_f1_chua_dang_nhap_thi_khong_doc_duoc():
    """Không đăng nhập phải bị CHẶN, không phải nhận một trang rỗng.

    Một cửa trả 200 kèm danh sách rỗng cho người lạ là cửa đã mở — chỉ là hôm nay chưa có gì rơi
    ra. Đó đúng là hình mà hàng rào này sinh ra để chặn.
    """
    for duong in ("/api/v1/huong-dan/ho-so", f"/api/v1/huong-dan/ho-so/{ID['du']}"):
        r = client.get(duong)
        assert r.status_code in (401, 403), f"{duong} trả {r.status_code} cho người chưa đăng nhập"


def test_f2_vai_khong_duoc_mo_thi_403():
    """Chủ tịch chốt 17/10/2026: phòng Hướng dẫn và Ban lãnh đạo. Nhân viên Marketing không nằm
    trong tập vai đã mở màn hình `/huong-dan`, nên cửa phải từ chối."""
    r = client.get("/api/v1/huong-dan/ho-so", headers=_h("nv_mkt"))
    assert r.status_code == 403, f"vai nv_mkt đọc được hồ sơ — trả {r.status_code}"


def test_f3_truong_phong_huong_dan_doc_duoc_danh_sach():
    r = client.get("/api/v1/huong-dan/ho-so", headers=_h("tp_hd"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nguong"] == HS.NGUONG_HIEN_DIEM
    ma = {x["ma"] for x in d["rows"]}
    assert "HD14-DU" in ma and "HD14-CHUA" in ma
    assert "HD14-KTX" not in ma


def test_f4_mot_ho_so_that_va_mot_ho_so_khong_co():
    h = _h("tp_hd")
    r = client.get(f"/api/v1/huong-dan/ho-so/{ID['du']}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ma"] == "HD14-DU"
    # Người không phải hướng dẫn viên, và một số hiệu không có ai — CẢ HAI đều 404.
    for eid in (ID["khong"], 99999999):
        r = client.get(f"/api/v1/huong-dan/ho-so/{eid}", headers=h)
        assert r.status_code == 404, (
            f"nhân sự {eid} trả {r.status_code}, phải là 404. Một trang rỗng nói «người này chưa "
            "có gì», còn sự thật là không có người này.")


def test_f5_cua_doc_khong_tra_ve_khoa_tuyen():
    """Nhóm E soi tầng dịch vụ; dòng này soi ĐÚNG CÁI RA KHỎI MÁY CHỦ — hai chỗ khác nhau."""
    r = client.get(f"/api/v1/huong-dan/ho-so/{ID['du']}", headers=_h("tp_hd"))
    for k in r.json().keys():
        assert "tuyen" not in k, f"cửa đọc đang trả khoá `{k}` khi Đợt HD-13 chưa có"
