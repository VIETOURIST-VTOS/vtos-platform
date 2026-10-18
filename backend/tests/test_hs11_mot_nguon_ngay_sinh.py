# -*- coding: utf-8 -*-
"""HS-11 — MỘT NGƯỜI, MỘT NGÀY SINH.

Phép thử nặng nhất ở đây là `test_hs11_4`: nó dựng sẵn một người có ngày sinh KHÁC NHAU ở hai
bảng, rồi bấm cửa chép, rồi đòi cửa ấy KHÔNG đụng tới người đó. Một cửa gộp dữ liệu mà tự chọn
bên nào thắng sẽ xoá mất ngày kia không còn dấu vết nào để lần lại — và sai kiểu ấy chỉ lộ ra
khi có người đi đòi hợp đồng hoặc sổ BHXH của chính mình.

`test_hs11_5` và `test_hs11_6` là hàng rào cho tương lai: thêm một màn hình đọc thẳng
`e.birth_date`, hoặc một cửa nạp gán lại vào cột cũ, thì đỏ ở đây. Thiếu chúng, hai nguồn lặng
lẽ mọc lại đúng như cách chúng đã mọc ra lần đầu.
"""
import os
import re
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hs11.db")
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
from app.models.core import User
from app.models.hr import Employee
from app.models.hrm import EmployeeProfile

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client = TestClient(app)
MK = "hs11_123456"
E_KHOP = E_LECH = E_CHI_NV = E_CHI_HS = None


@pytest.fixture(scope="module", autouse=True)
def _dung_du_lieu():
    global client, E_KHOP, E_LECH, E_CHI_NV, E_CHI_HS
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        db = SessionLocal()
        for un, vai in (("hs11_hcns", "hcns"), ("hs11_nv", "nv_kd"), ("hs11_ktt", "ketoan_truong")):
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thu {un}", role=vai, department="kd_le",
                            password_hash=hash_password(MK), active=True))
        db.flush()

        def nv(ma, ns_bang, ns_ho_so):
            e = Employee(code=ma, full_name=f"Nguoi {ma}", department="kd_le", position="nv",
                         office="hcm", contract_type="hdld", active=True, birth_date=ns_bang)
            db.add(e); db.flush()
            if ns_ho_so is not None:
                db.add(EmployeeProfile(employee_id=e.id, dob=ns_ho_so))
                db.flush()
            return e.id

        E_KHOP = nv("HS11-K", date(1990, 1, 1), date(1990, 1, 1))
        E_LECH = nv("HS11-L", date(1990, 1, 1), date(1991, 2, 2))      # HAI NGÀY KHÁC NHAU
        E_CHI_NV = nv("HS11-N", date(1992, 3, 3), None)                # chỉ bảng nhân sự có
        E_CHI_HS = nv("HS11-H", None, date(1993, 4, 4))                # chỉ hồ sơ có
        db.commit(); db.close()
        yield


def dang_nhap(un="hs11_hcns"):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ho_so(db, eid):
    return db.execute(select(EmployeeProfile)
                      .where(EmployeeProfile.employee_id == eid)).scalars().first()


# ---------------------------------------------------------------------------------------------
def test_hs11_1_cua_tao_va_sua_ghi_vao_HO_SO_chu_khong_vao_bang_nhan_su():
    """Màn hình vẫn có đúng một ô «Ngày sinh» — điều đổi là nó rơi vào đâu."""
    from app.db.session import SessionLocal
    h = dang_nhap()
    r = client.post("/api/v1/employees", headers=h, json={
        "code": "HS11-MOI", "full_name": "Nguoi moi", "department": "kd_le", "position": "nv",
        "birth_date": "1995-05-05", "phone": "0900000001"})
    assert r.status_code in (200, 201), r.text
    eid = r.json()["employee"]["id"]
    assert r.json()["employee"]["birth_date"], "Cửa đọc không trả lại ngày sinh vừa nhập."

    db = SessionLocal()
    try:
        e = db.get(Employee, eid)
        assert e.birth_date is None, (
            "Cửa tạo VẪN ghi vào `employees.birth_date` — đó là nguồn thứ hai mọc lại.")
        assert not e.phone, "Cửa tạo vẫn ghi vào `employees.phone`."
        pf = _ho_so(db, eid)
        assert pf is not None and pf.dob == date(1995, 5, 5), "Ngày sinh không vào hồ sơ cá nhân."
        assert pf.phone == "0900000001", "Điện thoại không vào hồ sơ cá nhân."
    finally:
        db.close()

    r = client.put(f"/api/v1/employees/{eid}", headers=h,
                   json={"full_name": "Nguoi moi", "department": "kd_le", "position": "nv",
                         "birth_date": "1996-06-06"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        assert db.get(Employee, eid).birth_date is None, "Cửa SỬA ghi vào bảng nhân sự."
        assert _ho_so(db, eid).dob == date(1996, 6, 6), "Cửa sửa không cập nhật hồ sơ."
    finally:
        db.close()


def test_hs11_2_soat_lech_chi_doc_va_phan_loai_dung():
    from app.db.session import SessionLocal
    from app.services import gop_ho_so_nv as GOP
    db = SessionLocal()
    try:
        kq = GOP.soat_lech(db)
        theo = {(d["employee_id"], d["truong"]): d for d in kq["rows"]}
        assert (E_LECH, "dob") in theo and theo[(E_LECH, "dob")]["trang_thai"] == "lech"
        assert theo[(E_CHI_NV, "dob")]["trang_thai"] == "chi_bang_nhan_su"
        assert theo[(E_CHI_HS, "dob")]["trang_thai"] == "chi_ho_so"
        assert (E_KHOP, "dob") not in theo, (
            "Người đã khớp vẫn nằm trong danh sách phải đi dọn — 121 dòng không có việc gì sẽ "
            "chôn mất mấy dòng có việc.")
        # chỉ đọc: không được sinh hồ sơ cho người chưa có
        assert _ho_so(db, E_CHI_NV) is None, "`soat_lech` đã GHI — nó chỉ được đọc."
    finally:
        db.close()


def test_hs11_3_xem_truoc_khong_ghi_gi_va_ke_ca_phan_o_lai():
    from app.db.session import SessionLocal
    from app.services import gop_ho_so_nv as GOP
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "hs11_hcns")).scalars().first()
        kq = GOP.chuyen_cho_trong(db, u, xac_nhan=False)
        assert kq["da_chep"] is False
        assert "o_lai" in kq and kq["o_lai"], (
            "Bản xem trước thiếu phần `o_lai`. Chỉ kê thứ sắp chép sẽ khiến người bấm tin rằng "
            "mọi thứ khác không tồn tại.")
        assert _ho_so(db, E_CHI_NV) is None, "Bản xem trước đã GHI."
        assert _ho_so(db, E_LECH).dob == date(1991, 2, 2), "Bản xem trước đã đổi ô đang lệch."
    finally:
        db.close()


def test_hs11_4_chep_o_trong_KHONG_DE_len_o_dang_khac_nhau():
    """Phép thử trung tâm của vòng."""
    from app.db.session import SessionLocal
    from app.services import gop_ho_so_nv as GOP
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "hs11_hcns")).scalars().first()
        kq = GOP.chuyen_cho_trong(db, u, xac_nhan=True)
        assert kq["da_chep"] is True
    finally:
        db.close()

    db = SessionLocal()
    try:
        assert _ho_so(db, E_CHI_NV).dob == date(1992, 3, 3), (
            "Ô hồ sơ còn TRỐNG mà không được chép — chép vào ô trống không đè lên ai, đó là phần "
            "cửa này phải làm.")
        assert _ho_so(db, E_LECH).dob == date(1991, 2, 2), (
            "Ô đang KHÁC NHAU bị ghi đè. Chọn hộ một ngày sinh là xoá mất ngày kia mà không còn "
            "dấu vết nào để lần lại — cửa này không được phép chọn.")
        assert db.get(Employee, E_LECH).birth_date == date(1990, 1, 1), (
            "Cột cũ bị xoá ở vòng này. Nó là bằng chứng để HCNS đối chiếu, phải còn nguyên cho "
            "tới khi danh sách lệch dọn xong.")
        assert _ho_so(db, E_CHI_HS).dob == date(1993, 4, 4)
    finally:
        db.close()


def test_hs11_5_khong_man_hinh_nao_duoc_doc_THANG_cot_cu():
    """Đọc thẳng `e.birth_date` ở một chỗ hiển thị nghĩa là chỗ ấy nói một con số khác với phần
    còn lại của hệ thống — và nó sẽ nói sai đúng với những người HCNS vừa cập nhật hồ sơ."""
    canh = ["backend/app/api/v1/hr.py", "backend/app/services/ho_so_nhan_vien.py"]
    xau = []
    # BỎ HẲN phần nằm TRONG lời gọi `doc(...)` rồi mới tìm, chứ không bỏ qua cả DÒNG có chữ
    # `GOP.doc`. Bản đầu của phép thử này viết kiểu bỏ-qua-cả-dòng, và phép thử ngược cho thấy nó
    # VẪN XANH khi `"birth_date": e.birth_date` nằm chung một dòng với một lời gọi `GOP.doc` khác
    # — tức là hàng rào tắt đúng ở dòng đông đúc nhất, nơi dễ lọt nhất.
    goi_doc = re.compile(r"_?GOP\.doc\([^)]*\)")
    for duong in canh:
        src = open(os.path.join(GOC, duong), encoding="utf-8").read()
        for so, dong in enumerate(src.splitlines(), start=1):
            t = goi_doc.sub("", dong.split("#")[0])
            if re.search(r"\be\.(birth_date|phone)\b", t):
                xau.append(f"{duong} dòng {so}: {dong.strip()[:90]}")
    assert not xau, (
        "ĐỌC THẲNG CỘT CŨ, không qua `gop_ho_so_nv.doc`:\n" + "\n".join("  · " + x for x in xau)
        + "\n\nLuật đọc là: hồ sơ cá nhân trước, cột cũ sau — và nó chỉ được viết ở MỘT chỗ.")


def test_hs11_6_hai_cua_nap_khong_duoc_gan_lai_vao_cot_cu():
    """Một cửa nạp gán lại `e.birth_date = ...` thì nguồn thứ hai mọc lại sau mỗi lần nạp tệp,
    và nó mọc lại IM LẶNG — không màn hình nào báo, không ai nhìn."""
    xau = []
    for duong in ("backend/app/services/intake_phong_ban.py", "backend/app/services/drivers.py"):
        src = open(os.path.join(GOC, duong), encoding="utf-8").read()
        for so, dong in enumerate(src.splitlines(), start=1):
            t = dong.split("#")[0]
            if re.search(r"\be\.(birth_date|phone)\s*=(?!=)", t) or \
               re.search(r"\b(birth_date|phone)\s*=\s*(_ngay|_dob|str)\(", t):
                xau.append(f"{duong} dòng {so}: {dong.strip()[:90]}")
    assert not xau, (
        "CỬA NẠP VẪN GHI VÀO BẢNG NHÂN SỰ:\n" + "\n".join("  · " + x for x in xau)
        + "\n\nNgày sinh và điện thoại chỉ ghi vào `employee_profiles`.")


def test_hs11_7_vai_khong_du_quyen_thi_khong_bam_duoc_cua_chep():
    r = client.post("/api/v1/hrm/lech-ho-so/chep-o-trong",
                    headers=dang_nhap("hs11_nv"), json={"xac_nhan": True})
    assert r.status_code in (403, 422), (
        f"Vai nv_kd bấm được cửa chép hồ sơ (mã {r.status_code}) — cửa phải khai đúng bộ "
        f"`HR_ADMIN`.")


def test_hs11_8_moi_cap_trung_deu_co_ten_tieng_viet_va_khai_du_ba_phan():
    """Thêm một cặp trùng mà quên khai tên thì bảng trên màn hình hiện ra một cột không nhãn, và
    HCNS không biết mình đang so cái gì với cái gì."""
    from app.services import gop_ho_so_nv as GOP
    assert GOP.CAP_TRUNG, "Danh sách cặp trùng rỗng."
    for cap in GOP.CAP_TRUNG:
        assert len(cap) == 3, f"{cap} phải là (cột bảng nhân sự, cột hồ sơ, tên tiếng Việt)."
        cot_nv, cot_hs, ten = cap
        assert hasattr(Employee, cot_nv), f"`employees` không có cột {cot_nv}"
        assert hasattr(EmployeeProfile, cot_hs), f"`employee_profiles` không có cột {cot_hs}"
        assert ten and ten[0].isupper(), f"{cap} thiếu tên tiếng Việt đọc được."


def test_hs11_9_ke_toan_khong_doc_duoc_danh_sach_lech():
    """Chủ tịch chốt 18/10/2026: danh sách lệch hồ sơ là việc của HCNS, ĐÓNG với Kế toán. Kế toán
    trưởng kế thừa Kế toán, và mọi cửa /hrm mở cho KTT phải nằm trong `CUA_LUONG_DA_KY` (test_lg5)
    — cửa này không nằm ở đó, nên nó phải đóng."""
    r = client.get("/api/v1/hrm/lech-ho-so", headers=dang_nhap("hs11_ktt"))
    assert r.status_code == 403, f"Kế toán trưởng đọc được danh sách lệch hồ sơ (mã {r.status_code})."
    assert client.get("/api/v1/hrm/lech-ho-so", headers=dang_nhap()).status_code == 200
