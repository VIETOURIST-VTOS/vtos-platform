# -*- coding: utf-8 -*-
"""NS-1b · Tuyến ký đơn nghỉ — chạy thật, không chỉ soi mã nguồn.

`test_ns1_don_nghi_doi_xe.py` soi NGUỒN: bảng luật khai đúng chưa, hàm có hỏi bảng ấy không, màn
hình có gọi đúng cửa không. Soi nguồn bắt được chuyện ai đó xoá dòng chặn, nhưng KHÔNG bắt được
chuyện dòng chặn còn nguyên mà không bao giờ chạy tới — nhánh chết là loại hỏng đã xảy ra thật
trong chính kho này (xem `hr.py::incidents`, mã chức danh bị viết vào chỗ chờ mã vai trò).

Nên tệp này gọi hàm thật, trên dữ liệu thật của bản demo, và hỏi đúng một câu: một người KHÔNG
phải người ký của phòng đó có ký được đơn không.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ns1b.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ns1b.db"):
    os.remove("test_ns1b.db")

from datetime import date                            # noqa: E402
import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal              # noqa: E402
from app.models.core import User                     # noqa: E402
from app.models.hr import Employee                   # noqa: E402
from app.models.hrm import LeaveRequest              # noqa: E402
from app.services import hrm as H                    # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


class _Gia:
    """Người dùng giả, đúng hai thuộc tính `decide_leave` đọc.

    Cố ý KHÔNG tạo tài khoản thật trong bản demo: thêm một dòng vào `seed.USERS` là đổi dữ liệu nền
    mà bốn làn cùng dùng, và vài phép thử khác đang đếm đúng số tài khoản ấy.
    """
    def __init__(self, role: str, uid: int = -1):
        self.role, self.id, self.username = role, uid, f"gia.{role}"


def _tai_xe_va_don():
    db = SessionLocal()
    e = db.execute(select(Employee).where(Employee.department == "doi_xe")).scalars().first()
    assert e is not None, "bản demo không còn nhân sự nào ở phòng Đội xe – phép thử này mất chỗ đứng"
    r = LeaveRequest(employee_id=e.id, kind="khong_luong", date_from=date(2026, 11, 3),
                     date_to=date(2026, 11, 3), days=1, reason="Việc nhà", created_by="phep_thu")
    db.add(r)
    db.commit()
    return db, e, r


def test_ns1b_1_nguoi_khong_phai_nguoi_ky_thi_khong_ky_duoc():
    """Trước 30/9/2026 BẢY vai ký được đơn của bất kỳ ai. Đây là phép thử giữ cho chuyện ấy không quay lại."""
    db, e, r = _tai_xe_va_don()
    try:
        for vai in ("tp_kd", "gd_kd", "ptgd_doan", "hcns", "tgd", "chutich"):
            with pytest.raises(ValueError) as ex:
                H.decide_leave(db, _Gia(vai), r, True, "")
            assert "không ký được đơn của phòng" in str(ex.value), str(ex.value)
            assert r.status == "cho_duyet", f"{vai} ký hụt mà đơn vẫn đổi trạng thái"
    finally:
        db.close()


def test_ns1b_2_giam_doc_doi_xe_ky_duoc_va_don_doi_trang_thai():
    db, e, r = _tai_xe_va_don()
    try:
        H.decide_leave(db, _Gia("gd_doi_xe"), r, True, "Đã sắp xếp người chạy thay")
        assert r.status == "duyet" and r.approved_by == "gia.gd_doi_xe"
        # Đơn đã quyết thì không ai quyết lại – kể cả đúng người ký.
        with pytest.raises(ValueError):
            H.decide_leave(db, _Gia("gd_doi_xe"), r, False, "đổi ý")
    finally:
        db.close()


def test_ns1b_3_khong_ai_tu_ky_don_cua_chinh_minh():
    """Kể cả khi đúng vai. Người ký của phòng mình cũng là người của phòng mình."""
    db, e, r = _tai_xe_va_don()
    try:
        u = db.execute(select(User)).scalars().first()
        e.user_id = u.id
        db.commit()
        with pytest.raises(ValueError) as ex:
            H.decide_leave(db, _Gia("gd_doi_xe", uid=u.id), r, True, "tự duyệt")
        assert "chính mình" in str(ex.value)
    finally:
        e.user_id = None
        db.commit()
        db.close()


def test_ns1b_4_cua_tu_choi_bat_buoc_ghi_ly_do():
    """Đòi ở MÁY CHỦ, không chỉ ở màn hình: màn hình nào cũng đi vòng được bằng một lời gọi thẳng."""
    db, e, r = _tai_xe_va_don()
    db.close()
    h = {"Authorization": "Bearer " + client.post(
        "/api/v1/auth/login", data={"username": "hcns", "password": "Vtos@Demo#2026"}).json()["access_token"]}
    kq = client.post(f"/api/v1/leaves/{r.id}/decide", headers=h, json={"approve": False, "note": "   "})
    assert kq.status_code == 422 and "lý do" in kq.json()["detail"]
