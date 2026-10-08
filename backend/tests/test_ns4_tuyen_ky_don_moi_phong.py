# -*- coding: utf-8 -*-
"""NS-4 · Tuyến ký đơn nghỉ cho CẢ MƯỜI MỘT phòng, và mặt sau của lần siết ấy.

Chủ tịch chốt 08/10/2026: "các trưởng phòng ký, và báo dữ liệu về cho HCNS, TGĐ / Chủ tịch". Hai vế,
và vế sau KHÔNG phải một chữ ký nữa — HCNS, TGĐ, Chủ tịch nằm trong `HR_READ` nên đã đọc được mọi đơn
từ trước.

BẢN NÀY SIẾT, KHÔNG NỚI, và đó là điều phải nói ra. Trước 08/10 chín phòng chạy bằng `KY_MAC_DINH`
bảy vai, nên HCNS, Giám đốc Kinh doanh và CNTT ký được đơn của gần như mọi phòng — và trên thực tế
HCNS là người bấm. Từ bản này mỗi phòng đúng MỘT vai ký, HCNS không còn ký.

MẶT SAU, VÀ NÓ LÀ CHỖ DỄ HỎNG NHẤT: một vai không tài khoản nào giữ thì đơn của cả phòng ấy nằm im
trong hàng đợi mà không dòng nào báo. Danh sách bảy vai cũ rộng thì sai người, nhưng không bao giờ
kẹt; danh sách một vai thì đúng người, và kẹt được. Đo trên bản demo lúc viết: `tp_kd` không tài khoản
nào giữ. Nên có `phong_khong_ai_giu_vai_ky()` và màn hình Nhân sự in nó lên.
"""
import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ns4.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ns4.db"):
    os.remove("test_ns4.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal              # noqa: E402
from app.models.core import User                     # noqa: E402
from app.models.hr import Employee, DEPARTMENTS      # noqa: E402
from app.services import hrm as H                    # noqa: E402

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "hop-dong-lao-dong" / "page.tsx"

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def test_moi_phong_dung_mot_vai_ky_va_khong_ai_tu_ky():
    """Phủ đủ mười một phòng, mỗi phòng một vai, và không phòng nào tự ký đơn của chính mình.

    Điều thứ ba là điều dễ bị bỏ qua nhất: nếu `hcns` ký đơn của phòng `hcns` thì người duy nhất của
    phòng ấy không có ai ký cho mình, và cả phòng dựa vào việc có người thứ hai cùng vai. Chủ tịch
    chốt TGĐ ký cho Kế toán và HCNS đúng vì lý do ấy.
    """
    assert set(H.TUYEN_KY_DON) == set(DEPARTMENTS), \
        f"thiếu/thừa phòng: {sorted(set(DEPARTMENTS) ^ set(H.TUYEN_KY_DON))}"
    nhieu = {p: v for p, v in H.TUYEN_KY_DON.items() if len(v) != 1}
    assert not nhieu, f"phòng có nhiều hơn một vai ký — mở người ký thay là việc cần người quyết: {nhieu}"
    # Vai ký của một phòng không được là vai mà chính phòng ấy mang tên (hcns ký hcns, ketoan ký ketoan).
    tu_ky = {p: v for p, v in H.TUYEN_KY_DON.items() if p in v}
    assert not tu_ky, f"phòng tự ký đơn của chính mình: {tu_ky}"


def test_bo_dem_phong_thieu_nguoi_giu_vai_that_su_nhin_thay():
    """Hỏi CÁI ĐẾM, không hỏi con số hôm nay.

    Một phép thử chỉ khẳng định "hôm nay có N phòng kẹt" thì ngày HCNS cấp xong tài khoản nó đỏ, và
    người sửa sẽ sửa con số. Phép thử này dựng một cảnh có thật — gỡ hết tài khoản của một vai ký —
    rồi hỏi bộ đếm có nhìn thấy không, và trả lại nguyên trạng.
    """
    with SessionLocal() as db:
        vai = H.TUYEN_KY_DON["dieu_hanh"][0]
        truoc = {x["phong"] for x in H.phong_khong_ai_giu_vai_ky(db)}
        assert "dieu_hanh" not in truoc, "bản demo vốn có tài khoản vai này, phép thử dựng sai cảnh"
        tk = list(db.execute(select(User).where(User.role == vai, User.active == True)).scalars())
        assert tk, f"bản demo không có tài khoản vai {vai}"
        for u in tk:
            u.active = False
        db.commit()
        try:
            sau = {x["phong"] for x in H.phong_khong_ai_giu_vai_ky(db)}
            assert "dieu_hanh" in sau, "gỡ hết tài khoản của vai ký mà bộ đếm vẫn im"
        finally:
            for u in tk:
                u.active = True
            db.commit()
        assert "dieu_hanh" not in {x["phong"] for x in H.phong_khong_ai_giu_vai_ky(db)}


def test_man_hinh_nhan_su_noi_ra_cho_ho():
    """Đếm được mà không ai thấy thì vẫn là im lặng — màn hình phải IN RA.

    So theo đường đầy đủ và theo tên trường máy chủ trả về, không so chuỗi khúc đầu: `"/hrm" in nguon`
    kiểu ấy đã lọt ba lần ở NS-2 và NS-3.
    """
    t = TRANG.read_text(encoding="utf-8")
    assert "phong_thieu_nguoi_giu_vai" in t, "màn hình Nhân sự chưa in ra phòng kẹt người ký"
    assert "phong_chua_chot_nguoi_ky" in t, "màn hình Nhân sự chưa in ra phòng chưa chốt người ký"
    assert re.search(r'api\(\s*"/hrm/meta"\s*\)', t), "màn hình chưa gọi đúng cửa /hrm/meta"


def _token(u: str) -> str:
    r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, f"{u}: {r.text}"
    return r.json()["access_token"]


def test_chay_that_dung_vai_ky_duoc_vai_cu_thi_khong():
    """Chạy thật trên dữ liệu thật: vai ký của phòng ký được, vai ký CŨ thì không còn.

    Vế thứ hai mới là vế đáng giá. Soi bảng luật chỉ bắt được chuyện ai đó sửa bảng; nó không bắt được
    chuyện bảng đổi mà `decide_leave` vẫn đọc danh sách cũ ở đâu đó. Hỏi thẳng máy chủ bằng tài khoản
    `hcns` — vai vừa MẤT quyền ký — và đòi 422.
    """
    h = {"Authorization": "Bearer " + _token("hcns")}
    emps = client.get("/api/v1/employees", headers=h).json()
    e = next(x for x in emps if x["department"] == "dieu_hanh" and x.get("position") != "tp")
    r = client.post("/api/v1/leaves", headers=h,
                    json={"employee_id": e["id"], "kind": "khong_luong",
                          "date_from": "2026-11-02", "date_to": "2026-11-02", "reason": "thử tuyến ký"})
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    assert r.json()["nguoi_ky"] == ["tp_dh"], r.json()["nguoi_ky"]

    xau = client.post(f"/api/v1/leaves/{lid}/decide", headers=h, json={"approve": True})
    assert xau.status_code == 422, f"HCNS vẫn ký được đơn phòng khác: {xau.status_code} {xau.text[:200]}"

    ky = {"Authorization": "Bearer " + _token("tp.dieuhanh")}
    tot = client.post(f"/api/v1/leaves/{lid}/decide", headers=ky, json={"approve": True, "note": "Đồng ý"})
    assert tot.status_code == 200 and tot.json()["status"] == "duyet", tot.text


def test_cua_meta_tra_ve_tuyen_ky_cho_man_hinh():
    """Màn hình lấy luật TỪ MÁY CHỦ, không khai lần thứ hai ở giao diện."""
    r = client.get("/api/v1/hrm/meta", headers={"Authorization": "Bearer " + _token("hcns")})
    assert r.status_code == 200, r.text
    kq = r.json()
    assert set(kq["tuyen_ky_don"]) == set(DEPARTMENTS)
    assert kq["phong_chua_chot_nguoi_ky"] == []
    assert isinstance(kq["phong_thieu_nguoi_giu_vai"], list)
