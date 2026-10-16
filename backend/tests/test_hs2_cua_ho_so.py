# -*- coding: utf-8 -*-
"""HS-2 — cửa đọc hồ sơ nhân viên: che ở MÁY CHỦ, và phạm vi kiểm ở MÁY CHỦ.

HS-1 canh bảng quyền bằng phép tính thuần. Bộ này canh thứ HS-1 không với tới: điều gì THẬT SỰ
đi ra khỏi dây mạng. Một bảng quyền đúng mà cửa trả nhầm bản chưa che thì màn hình vẫn vẽ đúng —
người dùng thấy dấu chấm, còn giá trị thật nằm trong phản hồi, ai mở tab Network cũng đọc được.

Phép thử nặng nhất ở đây là `test_hs2_4`: nó tìm chuỗi CCCD thật trong TOÀN BỘ thân phản hồi,
không chỉ trong ô nó nghĩ là ô CCCD. Che sót một chỗ là lộ, và chỗ sót thường không phải chỗ đoán.
"""
import os, sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_hs2.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_hs2.db", "test_hs2.db-journal"):
    if os.path.exists(_f): os.remove(_f)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.core import User
from app.services.ho_so_nhan_vien import (
    NHOM_NHAY_CAM, NHOM_THEO_MA, PHAM_VI_THEO_CAY, PHAM_VI_THEO_PHONG, VAI_DUNG_DAU,
)

client = TestClient(app)
MK = "hoso2_123456"
CCCD = "079094001234"
MST = "8123456712"
SO_BHXH = "7912345456"
TK_NH = "19001234567841"
LUONG = 18_000_000.0

VAI_THU = ("chutich", "hcns", "cntt", "tp_dh", "nv_visa", "tgd")
DICH = None          # id tài khoản bị xem


@pytest.fixture(scope="module", autouse=True)
def _dung_du_lieu():
    global client, DICH
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.hr import Employee
        from app.models.hrm import EmployeeProfile
        db = SessionLocal()

        for vai in VAI_THU:
            un = f"hs2_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai,
                            department="dieu_hanh" if vai == "tp_dh" else "kiem_thu",
                            password_hash=hash_password(MK), active=True))
        # Người bị xem: phòng dieu_hanh — cùng phòng với tp_dh ở trên, để thử luật phạm vi yếu.
        t = db.execute(select(User).where(User.username == "hs2_muctieu")).scalars().first()
        if t is None:
            t = User(username="hs2_muctieu", full_name="Nguyen Thi Thu", role="nv_dh",
                     department="dieu_hanh", staff_code="HS2001",
                     password_hash=hash_password(MK), active=True)
            db.add(t); db.flush()
        e = db.execute(select(Employee).where(Employee.code == "HS2001")).scalars().first()
        if e is None:
            e = Employee(code="HS2001", full_name="Nguyen Thi Thu", department="dieu_hanh",
                         position="nv", title="CV Dieu hanh 2", contract_type="hdld",
                         start_date=date(2024, 1, 2), base_salary=LUONG, bhxh_base=9_000_000.0,
                         phone="0901234567", active=True)
            db.add(e); db.flush()
        e.user_id = t.id
        if db.execute(select(EmployeeProfile)
                      .where(EmployeeProfile.employee_id == e.id)).scalars().first() is None:
            db.add(EmployeeProfile(employee_id=e.id, dob=date(1994, 3, 14), gender="nu",
                                   id_number=CCCD, permanent_address="So 1 duong X phuong Y",
                                   tax_code=MST, social_insurance_no=SO_BHXH,
                                   bank_account=TK_NH, email="thu.nguyen@vietourist.com.vn"))
        db.commit()
        DICH = t.id
        db.close()
        yield


def dang_nhap(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"hs2_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


DUONG = "/api/v1/employees/tai-khoan"


def doc(vai):
    return client.get(f"{DUONG}/{DICH}/ho-so-theo-vai", headers=dang_nhap(vai))


# ---------------------------------------------------------------------------------------------
def test_hs2_1_hai_luat_pham_vi_phu_kin_vai_dung_dau():
    """Mỗi vai đứng đầu phải thuộc ĐÚNG MỘT luật phạm vi. Thiếu thì vai ấy im lặng không có
    phạm vi nào; trùng thì luật nào chạy trước quyết định, và thứ tự ấy không ai khai ra."""
    assert set(PHAM_VI_THEO_CAY) | set(PHAM_VI_THEO_PHONG) == set(VAI_DUNG_DAU)
    assert not (set(PHAM_VI_THEO_CAY) & set(PHAM_VI_THEO_PHONG))


def test_hs2_2_moi_ma_nhay_cam_la_nhom_co_that():
    """Gõ nhầm một mã ở NHOM_NHAY_CAM thì nhóm ấy đọc không để lại vết, và không ai thấy."""
    for ma in NHOM_NHAY_CAM:
        assert ma in NHOM_THEO_MA, f"NHOM_NHAY_CAM có mã {ma!r} không tồn tại trong NHOM_TRUONG"


def test_hs2_3_chu_tich_thay_that_khong_che():
    """Quyền của Chủ tịch là toàn diện (15/10/2026): 17 nhóm, giá trị thật, không dấu chấm."""
    r = doc("chutich"); assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["nhom_thay"]) == len(NHOM_THEO_MA)
    assert all(n["quyen"] == "co" for n in d["nhom_thay"])
    assert d["ho_so"]["id_number"] == CCCD
    assert d["ho_so"]["base_salary"] == LUONG
    assert d["nhom_nhay_cam_da_doc"], "Chủ tịch đọc nhóm nhạy cảm thì vẫn phải để lại vết."


def test_hs2_4_hcns_khong_nhan_mot_chu_nao_cua_gia_tri_that():
    """Che là việc của máy chủ. Tìm chuỗi thật trong TOÀN BỘ thân phản hồi, không chỉ ở ô đoán."""
    r = doc("hcns"); assert r.status_code == 200, r.text
    than = r.text
    for bi_mat in (CCCD, MST, SO_BHXH, TK_NH, str(int(LUONG))):
        assert bi_mat not in than, f"{bi_mat!r} rời khỏi máy chủ trong phản hồi gửi HCNS"
    hs = r.json()["ho_so"]
    assert hs["id_number"] and hs["id_number"] != CCCD      # có ô, nhưng là bản đã che
    assert hs["base_salary"] == "•••"


def test_hs2_5_cntt_khong_co_khoa_chu_khong_phai_rong():
    """Nhóm bị từ chối phải BỎ HẲN khoá. Trả None thì màn hình in một ô trống, và một ô trống
    đọc giống 'người này chưa khai' — tức là nói sai về dữ liệu của người khác."""
    r = doc("cntt"); assert r.status_code == 200, r.text
    hs = r.json()["ho_so"]
    for k in ("id_number", "dob", "base_salary", "bank_account", "advance_limit",
              "diem_danh_gia", "nhat_ky_gia_tri", "ngay_cong_ky_nay"):
        assert k not in hs, f"CNTT không được thấy {k}, kể cả dưới dạng rỗng"
    assert hs["username"] == "hs2_muctieu"                  # nhóm 3 thì thấy
    assert "nhat_ky" in hs                                  # nhóm 10 thì thấy — chỉ tên trường
    assert all("truoc" not in x and "sau" not in x for x in hs["nhat_ky"])


def test_hs2_6_truong_phong_cung_phong_va_luat_yeu_phai_noi_ra():
    """Trưởng phòng Điều hành đọc được người CÙNG PHÒNG — qua HTTP thật, không phải gọi hàm —
    và cửa phải NÓI nó dựa vào luật nào."""
    r = doc("tp_dh"); assert r.status_code == 200, r.text
    d = r.json()
    assert d["trong_pham_vi"] is True
    assert d["luat_pham_vi"] == "cung_phong_luat_yeu"
    hs = d["ho_so"]
    assert hs["title"] == "CV Dieu hanh 2"                  # nhóm 1
    for k in ("id_number", "base_salary", "username", "advance_limit", "phone"):
        assert k not in hs, f"Trưởng phòng không được thấy {k}"


def test_hs2_6b_khac_phong_thi_rong_han_chu_khong_phai_ho_so_trang():
    """Ngoài phạm vi thì không thấy GÌ, và cửa trả 403 — không phải 200 với một hồ sơ đủ ô mà
    rỗng giá trị. Một hồ sơ trắng đọc giống 'người này chưa khai', tức là nói sai về người khác."""
    from app.db.session import SessionLocal
    from app.services import ho_so_nhan_vien as HSNV
    db = SessionLocal()
    try:
        xem = db.execute(select(User).where(User.username == "hs2_tp_dh")).scalars().one()
        la = db.execute(select(User).where(User.username == "hs2_cntt")).scalars().one()
        d = HSNV.doc_ho_so(db, xem, la)
        assert d["trong_pham_vi"] is False and d["luat_pham_vi"] == "khac_phong"
        assert d["ho_so"] == {} and d["nhom_thay"] == []
    finally:
        db.close()
    la_id = None
    with SessionLocal() as db2:
        la_id = db2.execute(select(User).where(User.username == "hs2_cntt")).scalars().one().id
    r = client.get(f"{DUONG}/{la_id}/ho-so-theo-vai", headers=dang_nhap("tp_dh"))
    assert r.status_code == 403


def test_hs2_7_vai_khong_khai_thi_403_chu_khong_phai_ho_so_rong():
    """Mặc định là từ chối, và từ chối phải nói thành 403. Trả 200 với hồ sơ rỗng thì màn hình
    vẽ một hồ sơ trắng, và người dùng tưởng hệ thống chưa có dữ liệu."""
    for vai in ("nv_visa", "tgd"):
        r = doc(vai)
        assert r.status_code == 403, f"{vai} phải bị chặn, nhận {r.status_code}"


def test_hs2_8_vet_doc_khong_mang_theo_mot_gia_tri_nao():
    """Nhật ký ghi TÊN NHÓM. Một bản ghi kiểm toán chứa CCCD là chỗ rò thứ hai, và chỗ ấy ai đọc
    được nhật ký cũng đọc được — rộng hơn hẳn nhóm được phép xem hồ sơ.

    Đọc THẲNG bảng `audit_log`, không qua `/access/audit`: cửa ấy lọc theo `HANH_DONG_QUYEN` và
    cố ý không chứa hành động này. Vết đọc hồ sơ là việc của NHẬT KÝ HỒ SƠ (nhóm 10), không phải
    của nhật ký cấp-thu quyền; nhét nó vào đấy là làm trôi mất thứ màn hình ấy sinh ra để nhìn.
    """
    import json
    from app.db.session import SessionLocal
    from app.models.core import AuditLog
    doc("chutich")
    db = SessionLocal()
    try:
        dong = list(db.execute(select(AuditLog)
                               .where(AuditLog.action == "doc_ho_so_nhan_vien")).scalars())
        assert dong, "Đọc nhóm nhạy cảm mà không có dòng nhật ký nào"
        than = json.dumps([{"before": r.before, "after": r.after, "entity": r.entity}
                           for r in dong], ensure_ascii=False, default=str)
        for bi_mat in (CCCD, MST, SO_BHXH, TK_NH, str(int(LUONG))):
            assert bi_mat not in than, f"{bi_mat!r} nằm trong nhật ký — nhật ký thành chỗ rò thứ hai"
    finally:
        db.close()

    # Và vết ấy phải đến được mắt người: nó nằm trong nhóm 10 của chính hồ sơ này.
    nk = doc("chutich").json()["ho_so"]["nhat_ky"]
    assert any(x["viec"] == "doc_ho_so_nhan_vien" for x in nk)


def test_hs2_9_thieu_nguon_phai_tu_to_cao():
    """Trường đã khai mà chưa có bảng nào sinh ra phải tự hiện tên ra ở mỗi lần gọi. Im lặng thì
    một ô trống trên màn hình trông y hệt một người chưa khai số liệu."""
    r = doc("chutich"); assert r.status_code == 200
    thieu = r.json()["thieu_nguon"]
    for k in ("so_tour", "so_booking", "so_lenh_xe", "so_visa", "so_phan_cong_kd"):
        assert k in thieu, f"{k} chưa có nguồn mà không được kê vào thieu_nguon"
    hs = r.json()["ho_so"]
    assert "so_dong_tro_toi" in hs and isinstance(hs["viec_dang_ganh"], list)
    for k in thieu:
        assert k not in hs, f"{k} vừa kê là thiếu nguồn vừa có mặt trong hồ sơ"


def test_hs2_10_khong_co_tai_khoan_thi_404():
    r = client.get("/api/v1/access/users/99999999/ho-so-theo-vai", headers=dang_nhap("chutich"))
    assert r.status_code == 404


def test_hs2_11_cua_nay_phai_nam_sau_mot_tien_to_ca_tam_vai_deu_voi_toi():
    """HÀNG RÀO THỨ BA — cái đã chặn vòng trước, và là cái dễ hỏng lại nhất.

    `check_restricted_scope` chạy trong `current_user` cho MỌI đường dẫn: một vai chỉ chạm được
    nhóm API nằm sau MÀN HÌNH của vai ấy. Nó không biết gì về bảng quyền hồ sơ, nên bảng ấy đúng
    hết mà cửa vẫn 403 — và 403 ấy trông y hệt một quyết định có chủ.

    Phép thử ghim hai điều. Một: đường của cửa phải nằm sau một tiền tố mà CẢ TÁM vai đều có —
    ngày ai đó rút `/api/v1/employees` khỏi bản đồ của một vai đứng đầu thì đỏ ở đây, chứ không
    phải đỏ ở một trưởng phòng ngồi nhìn màn hình trắng. Hai: cửa KHÔNG được có bản thứ hai dưới
    `/api/v1/access` — hai cửa cùng một việc là hai hàng rào phải sửa cùng lúc.
    """
    from app.main import app as _app
    from app.services.access import pham_vi_day_du

    duong = [r.path for r in _app.routes
             if str(getattr(r, "path", "")).endswith("/ho-so-theo-vai")]
    assert len(duong) == 1, f"Phải có ĐÚNG MỘT cửa đọc hồ sơ theo vai, đang có: {duong}"
    d = duong[0]
    assert not d.startswith("/api/v1/access"), (
        "Cửa đọc hồ sơ không được nằm dưới /api/v1/access — không vai đứng đầu nào có tiền tố ấy "
        "trong bản đồ màn hình, và nới bản đồ là mở luôn màn quản trị Tài khoản.")

    for vai in ("chutich", "hcns", "cntt", "tp_dh", "tp_kd", "tp_hd", "gd_kd", "gd_doi_xe"):
        assert any(d.startswith(p) for p in pham_vi_day_du(vai)), (
            f"Vai {vai} không có tiền tố nào phủ {d} — hàng rào đường dẫn sẽ chặn trước khi "
            "bảng quyền hồ sơ kịp chạy, và lỗi ấy im lặng.")


def test_hs2_12_moi_truong_tra_ve_deu_thuoc_dung_mot_nhom():
    """Màn hình vẽ theo `nhom_thay[].truong`. Nếu một trường có trong `ho_so` mà không nhóm nào
    kê nó, màn hình KHÔNG vẽ nó — trường ấy biến mất trong im lặng, và im lặng là kiểu hỏng tệ
    nhất ở đây: người xem tưởng người kia chưa khai. Hai nhóm cùng kê một trường thì nó hiện hai
    lần, và hai ô cùng tên cạnh nhau làm người đọc tưởng có hai giá trị."""
    for vai in ("chutich", "hcns", "cntt"):
        d = doc(vai).json()
        dem: dict[str, int] = {}
        for n in d["nhom_thay"]:
            for t in n["truong"]:
                dem[t] = dem.get(t, 0) + 1
        for k in d["ho_so"]:
            assert dem.get(k) == 1, (
                f"Vai {vai}: trường {k!r} thuộc {dem.get(k, 0)} nhóm, phải đúng 1 — "
                "0 thì màn hình nuốt mất nó, 2 thì nó hiện hai lần.")
        for t in dem:
            assert t in d["ho_so"], f"Vai {vai}: nhóm kê trường {t!r} mà cửa không trả về"
