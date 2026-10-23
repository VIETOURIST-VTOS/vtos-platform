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
    VAI_GIAM_SAT_TOAN_HE,
)

client = TestClient(app)
MK = "hoso2_123456"
CCCD = "079094001234"
MST = "8123456712"
SO_BHXH = "7912345456"
TK_NH = "19001234567841"
LUONG = 18_000_000.0

# DON-MT 24/10/2026: them `bks` va `robot_ks` vao bo tai khoan thu. Dot nay mo
# NHOM 1 cho ca ba vai giam sat, nen phep thu phai do duoc ca ba - thieu tai
# khoan thi dong do la 401 chu khong phai mot cau tra loi ve quyen.
VAI_THU = ("chutich", "hcns", "cntt", "tp_dh", "nv_visa", "tgd", "bks", "robot_ks")
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
    for vai in ("nv_visa",):
        r = doc(vai)
        assert r.status_code == 403, f"{vai} phải bị chặn, nhận {r.status_code}"
    # ĐỢT DỌN-MT 24/10/2026 — `tgd` RỜI khỏi danh sách trên vì Chủ tịch ký 24/10 mở NHÓM 1
    # cho ba vai giám sát toàn hệ. KHÔNG bỏ trắng chỗ này: thay bằng một phép đo CHẶT HƠN —
    # mở được, và mở ra thì không được thấy một trường nào của nhóm đã khóa.
    #
    # `chutich` ĐỨNG RIÊNG và KHÔNG bị soi trường: ông vốn có `CO` ở cả 17 nhóm từ trước
    # đợt này — gộp ông vào phép soi dưới là phép thử tự nói sai về quyết định 15/10/2026.
    assert doc("chutich").status_code == 200, "Chủ tịch vốn đã xem được toàn bộ hồ sơ"
    for vai in ("tgd", "bks", "robot_ks"):
        r = doc(vai)
        assert r.status_code == 200, f"{vai} phải mở được hồ sơ, nhận {r.status_code}"
        for cam in ("id_number", "base_salary", "phone", "end_reason", "username"):
            assert f'"{cam}"' not in r.text, (
                f"{vai} thấy `{cam}` — trường của nhóm 1b/2b/3/4/5, vẫn chỉ Chủ tịch và HCNS")


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
    hs = r.json()["ho_so"]
    # HS-12 (18/10/2026) dựng nguồn cho sáu con số việc đang gánh: từ nay chúng PHẢI có mặt và
    # KHÔNG được nằm trong thieu_nguon. Phép canh chiều ngược lại ở test_hs12.
    for k in ("so_tour", "so_quyet_toan_giu", "so_booking", "so_visa", "so_phan_cong_kd"):
        assert k in hs and k not in thieu, f"{k} đã có nguồn (HS-12) mà vẫn báo thiếu"
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


# =============================================================================================
# HS-3 · cửa HIỆN một trường đang bị che
# =============================================================================================
HIEN = "/api/v1/employees/tai-khoan"


def hien(vai, truong, muc_dich="lam hop dong lao dong"):
    return client.post(f"{HIEN}/{DICH}/hien-truong",
                       json={"truong": truong, "muc_dich": muc_dich},
                       headers=dang_nhap(vai))


def test_hs3_1_hcns_hien_duoc_va_nhan_dung_gia_tri_that():
    """Che không phải là cấm. HCNS làm hợp đồng thì phải đọc được số CCCD thật — cái họ không
    được có là đọc nó mà không ai biết."""
    r = hien("hcns", "id_number"); assert r.status_code == 200, r.text
    d = r.json()
    assert d["gia_tri"] == CCCD and d["nhom"] == "4"
    r2 = hien("hcns", "base_salary", "tinh luong thang 10")
    assert r2.status_code == 200 and r2.json()["gia_tri"] == LUONG


def test_hs3_2_khong_khai_muc_dich_thi_khong_hien():
    """Ô trống hoặc một chữ cái không phải mục đích. Một nhật ký đầy dòng «x» là nhật ký không
    ai đọc — tức là vết có mà tác dụng thì không."""
    for md in ("", "   ", "x", "abc"):
        r = client.post(f"{HIEN}/{DICH}/hien-truong",
                        json={"truong": "id_number", "muc_dich": md},
                        headers=dang_nhap("hcns"))
        assert r.status_code == 422, f"mục đích {md!r} phải bị từ chối, nhận {r.status_code}"


def test_hs3_3_vai_khong_duoc_xem_nhom_ay_thi_cua_tu_choi():
    """CNTT không thấy nhóm 4. Cửa hiện KHÔNG được thành đường vòng quanh bảng quyền — nếu nó
    hiện được thì cả lớp che ở trên thành vô nghĩa, chỉ cần thêm một lần bấm."""
    r = hien("cntt", "id_number")
    assert r.status_code == 403, r.text
    assert CCCD not in r.text


def test_hs3_4_truong_von_thay_thang_thi_khong_di_qua_cua_nay():
    """Chủ tịch thấy nhóm 4 thẳng. Cho cửa này trả về nữa là mở lối thứ hai tới cùng một giá
    trị — hai lối thì phải rào hai chỗ, và quên một chỗ là hở."""
    r = hien("chutich", "id_number")
    assert r.status_code == 422 and "không bị che" in r.json()["detail"]


def test_hs3_5_truong_khong_co_that_thi_404_chu_khong_phai_500():
    r = hien("hcns", "khong_ton_tai_dau")
    assert r.status_code == 404


def test_hs3_6_vet_hien_truong_khong_mang_theo_gia_tri():
    """Nhật ký ghi TÊN TRƯỜNG và MỤC ĐÍCH. Bản ghi kiểm toán chứa CCCD là chỗ rò thứ hai, và nó
    RỘNG HƠN chỗ thứ nhất: ai đọc được nhật ký cũng đọc được, kể cả người không xem được nhóm 4."""
    import json
    from app.db.session import SessionLocal
    from app.models.core import AuditLog
    assert hien("hcns", "bank_account", "doi chieu tai khoan tra luong").status_code == 200
    db = SessionLocal()
    try:
        dong = list(db.execute(select(AuditLog)
                               .where(AuditLog.action == "hien_truong_ho_so")).scalars())
        assert dong, "Hiện một trường mà không có dòng nhật ký nào"
        than = json.dumps([{"b": r.before, "a": r.after, "e": r.entity} for r in dong],
                          ensure_ascii=False, default=str)
        for bi_mat in (CCCD, MST, SO_BHXH, TK_NH, str(int(LUONG))):
            assert bi_mat not in than, f"{bi_mat!r} nằm trong nhật ký hiện-trường"
        assert "muc_dich" in than and "truong" in than
    finally:
        db.close()


def test_hs3_7_cua_hien_khong_rong_hon_cua_doc():
    """Phép thử bắc cầu: với MỌI vai và MỌI trường, cửa hiện chỉ mở được đúng những trường mà
    cửa đọc đã trả về ở dạng ĐÃ CHE. Rộng hơn một trường thôi là lớp che thủng mà không ai thấy,
    vì màn hình vẫn vẽ ra dấu chấm."""
    from app.db.session import SessionLocal
    from app.services import ho_so_nhan_vien as HSNV
    db = SessionLocal()
    try:
        dich = db.get(User, DICH)
        for vai in ("chutich", "hcns", "cntt", "tp_dh", "nv_visa"):
            xem = db.execute(select(User).where(User.username == f"hs2_{vai}")).scalars().one()
            d = HSNV.doc_ho_so(db, xem, dich)
            che = {t for n in d["nhom_thay"] if n["quyen"] == "che" for t in n["truong"]}
            for n in HSNV.NHOM_TRUONG:
                for t in n["truong"]:
                    kq = HSNV.hien_truong(db, xem, dich, t)
                    if kq["duoc"]:
                        assert t in che, (
                            f"Vai {vai}: cửa hiện mở được {t!r} mà cửa đọc không hề che nó — "
                            "cửa hiện đang rộng hơn cửa đọc.")
    finally:
        db.close()


def test_hs3_8_danh_sach_vai_o_cua_hien_phai_suy_tu_bang_va_khong_duoc_rong():
    """`VAI_CO_NHOM_CHE` khai ở chữ ký cửa `hien-truong` để MÁY đọc được — đường GHI nào cũng
    phải khai ở đó. Phép thử ghim hai chuyện.

    Một: nó phải SUY ra từ `NHOM_TRUONG`, không gõ tay. Gõ tay là bảng quyền có bản sao thứ hai,
    và ngày một nhóm mở dạng CHE cho vai nữa thì bảng đổi mà dòng khai ở cửa không — người vai
    ấy bấm «Hiện» nhận 403 không ai giải thích được.

    Hai: nó KHÔNG ĐƯỢC RỖNG. `require_roles()` không tham số không chặn ai, nên một bảng quyền
    lỡ không còn nhóm CHE nào sẽ lặng lẽ mở cửa này cho mọi người đăng nhập.
    """
    from app.services.ho_so_nhan_vien import CHE, NHOM_TRUONG, VAI_CO_NHOM_CHE
    mong = tuple(sorted({v for n in NHOM_TRUONG for v, q in n["quyen"].items() if q == CHE}))
    assert VAI_CO_NHOM_CHE == mong
    assert VAI_CO_NHOM_CHE, ("Không vai nào có nhóm CHE — require_roles() rỗng không chặn ai. "
                             "Bỏ hẳn cửa hiện-trường, đừng để nó mở toang.")


# =============================================================================================
# HS-4 · danh sách nhân viên trong phạm vi
# =============================================================================================
def test_hs4_1_truong_phong_thay_nguoi_cung_phong_va_biet_luat_nao():
    r = client.get("/api/v1/employees/phong-toi", headers=dang_nhap("tp_dh"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["luat_pham_vi"] == "cung_phong_luat_yeu"
    ten = {x["full_name"] for x in d["nguoi"]}
    assert "Nguyen Thi Thu" in ten, "Người cùng phòng dieu_hanh phải có trong danh sách"
    assert "Thử tp_dh" not in ten, "Không liệt kê chính mình trong danh sách nhân viên"


def test_hs4_2_danh_sach_khong_rong_hon_cua_doc():
    """Dòng danh sách phải đi qua cùng bảng quyền. Một cột lọt thêm ở đây là một cột lọt ra mà
    màn hình hồ sơ vẫn che đúng — chỗ hở ở bảng danh sách khó thấy hơn hẳn."""
    r = client.get("/api/v1/employees/phong-toi", headers=dang_nhap("tp_dh"))
    for x in r.json()["nguoi"]:
        for cam in ("id_number", "base_salary", "bank_account", "phone", "username",
                    "advance_limit", "diem_danh_gia", "nhat_ky"):
            assert cam not in x, f"Trưởng phòng không được thấy {cam} trên dòng danh sách"


def test_hs4_3_vai_khong_quan_ly_ai_thi_403():
    """Chủ tịch và HCNS nhìn toàn công ty — họ không có 'phòng của tôi'. Trả một danh sách rỗng
    sẽ đọc giống 'phòng bạn không có ai', mà đó là một câu sai."""
    for vai in ("hcns", "cntt", "nv_visa"):
        r = client.get("/api/v1/employees/phong-toi", headers=dang_nhap(vai))
        assert r.status_code == 403, f"{vai} nhận {r.status_code}"
    # ĐỢT DỌN-MT 24/10/2026 — `chutich` RỜI khỏi danh sách trên. Luật đã ký đòi bốn vai nền
    # xem được MỌI màn hình, và một mục menu dẫn tới 403 là món nợ `test_lg4` cấm; nên cửa
    # này mở cho bốn vai ấy. NHƯNG CÂU "PHÒNG CỦA TÔI" VẪN LÀ MỘT CÂU SAI VỚI HỌ — lý lẽ của
    # phép thử cũ không mất đi, nó chỉ đổi chỗ: cửa phải NÓI RA nó đang trả về toàn công ty.
    for vai in VAI_GIAM_SAT_TOAN_HE:
        r = client.get("/api/v1/employees/phong-toi", headers=dang_nhap(vai))
        assert r.status_code == 200, f"{vai} nhận {r.status_code}"
        assert r.json()["luat_pham_vi"] == "giam_sat_toan_he", (
            f"{vai} nhận một danh sách mà cửa không nói rõ đó là TOÀN CÔNG TY — "
            f"màn hình sẽ bày nó dưới nhãn phòng của tôi, và đó là một câu sai")


def test_hs4_4_moi_nguoi_trong_danh_sach_deu_mo_duoc_ho_so():
    """Phép thử bắc cầu giữa hai cửa: ai có tên trong danh sách thì bấm vào PHẢI mở được. Danh
    sách rộng hơn cửa đọc nghĩa là màn hình bày ra những dòng bấm vào chỉ nhận 403."""
    r = client.get("/api/v1/employees/phong-toi", headers=dang_nhap("tp_dh"))
    for x in r.json()["nguoi"]:
        h = client.get(f"{DUONG}/{x['user_id']}/ho-so-theo-vai", headers=dang_nhap("tp_dh"))
        assert h.status_code == 200, (
            f"{x['full_name']} có trong danh sách nhưng mở hồ sơ nhận {h.status_code}")


def test_hs5_moi_cua_ho_so_deu_khai_quyen_o_chu_ky_va_suy_tu_bang():
    """BÀI HỌC 16/10/2026 — và là lỗi của chính làn này.

    Vòng HS-2 đặt cửa ĐỌC dưới `current_user`, để hàng rào nằm trong thân hàm dịch vụ, vì nghĩ
    luật "khai quyền ở chỗ máy đọc được" chỉ áp cho đường GHI. Sai: `test_p1` và `test_p1b` áp
    cho MỌI đường và bắt đúng cửa ấy — nhưng hai phép thử đó nằm ở bộ `backend` 45 phút, không
    nằm trong bộ cổng 16 tệp, nên bốn vòng liền không ai thấy.

    Phép thử này nằm NGAY TRONG bộ của làn, để lần sau đỏ trong 20 giây chứ không đỏ sau 45 phút:
    mọi cửa hồ sơ phải khai vai ở chữ ký, và danh sách ấy phải SUY RA từ bảng quyền chứ không gõ
    tay — gõ tay là bảng quyền có bản sao thứ hai, và hai bản sẽ lệch.
    """
    from app.main import app as _app
    from app.services import ks_robot as KS
    from app.services.ho_so_nhan_vien import (CHE, NHOM_TRUONG, VAI_CO_NHOM_CHE,
                                              VAI_CO_TRONG_BANG, VAI_DUNG_DAU)

    assert VAI_CO_TRONG_BANG == tuple(sorted({v for n in NHOM_TRUONG for v in n["quyen"]}))
    assert VAI_CO_NHOM_CHE == tuple(sorted(
        {v for n in NHOM_TRUONG for v, q in n["quyen"].items() if q == CHE}))
    for ten, ds in (("VAI_CO_TRONG_BANG", VAI_CO_TRONG_BANG),
                    ("VAI_CO_NHOM_CHE", VAI_CO_NHOM_CHE),
                    ("VAI_DUNG_DAU", VAI_DUNG_DAU)):
        assert ds, f"{ten} rỗng — require_roles() không tham số thì không chặn ai"

    cua_ho_so = [r for r in _app.routes
                 if "/employees/tai-khoan" in str(getattr(r, "path", ""))
                 or str(getattr(r, "path", "")).endswith("/employees/phong-toi")]
    assert len(cua_ho_so) == 3, f"Phải có đúng ba cửa hồ sơ, đang có: {cua_ho_so}"
    for r in cua_ho_so:
        assert KS.chan_o_chu_ky(r), (
            f"{r.path} không khai vai ở chữ ký — bộ rà quyền sẽ phải đọc mã nguồn mới thấy, "
            "và đó đúng là thứ P1 cấm.")

    assert not [x for x in KS.endpoint_phai_doc_ma_nguon(_app)
                if "/employees/" in x], "Còn cửa hồ sơ phải đọc mã nguồn mới nhận ra quyền"
