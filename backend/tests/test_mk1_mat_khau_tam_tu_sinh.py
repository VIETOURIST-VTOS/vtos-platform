# -*- coding: utf-8 -*-
"""MK-1 · ĐẶT LẠI MẬT KHẨU: máy sinh mật khẩu tạm, hiện đúng một lần — 25/10/2026.

VÌ SAO CÓ VÒNG NÀY. Chủ tịch bảo «vào VTOS đặt lại mật khẩu», rồi báo lại là tài khoản CNTT cũng
không đặt lại được. Màn hình trả về «Chưa có mã NV – nhập mật khẩu mới». Đo ra HAI chỗ hỏng chồng
lên nhau, và chỗ thứ hai mới là chỗ nặng:

  (1) LỜI BÁO NÓI SAI. Mã nhân viên CÓ đủ. Chốt `len(pw) < 3` chặn mã 1–2 chữ số, mà bảng lương
      09/2026 có 31/109 người mang mã như thế — kể cả mã `1` của chính Chủ tịch. Người quản trị
      đi tìm một cái mã không hề thiếu.

  (2) QUY ƯỚC «MẬT KHẨU TẠM = MÃ NV» VỐN ĐÃ YẾU Ở CÔNG TY NÀY. Mã là số đếm dưới 400 và hiện công
      khai ngay trên bảng Phân quyền. Cờ `buộc đổi` chỉ cứu được nếu người THẬT đăng nhập trước kẻ
      dò — mà tài khoản cần đặt lại thường là tài khoản chưa ai từng đăng nhập.

  (3) VÀ KHÔNG CÓ ĐƯỜNG ĐI TIẾP. Lời báo mời «nhập mật khẩu mới», nhưng không màn hình nào có ô
      nhập: cả hai chỗ gọi cửa này đều gửi cứng `new_password: ""`. Tài khoản mã ngắn = tài khoản
      không ai mở được, kể cả CNTT.

Bộ này canh bản sửa: MÁY SINH thành đường mặc định, mã NV thành lựa chọn phụ có chốt và có lời báo
nói đúng sự thật.

  mk1_1  không truyền gì → máy sinh, trả mật khẩu ĐÚNG MỘT LẦN, và bật cờ buộc đổi
  mk1_2  mật khẩu sinh ra đăng nhập được THẬT, và lần đăng nhập ấy bị chặn vào mọi màn
  mk1_3  hai lần sinh KHÔNG ra cùng một chuỗi
  mk1_4  mật khẩu sinh ra không mang ký tự dễ đọc nhầm, và đủ dài
  mk1_5  người bấm tự gõ thì dùng đúng chuỗi ấy, và KHÔNG trả mật khẩu về
  mk1_6  `dung_ma_nv` với mã NGẮN → 422 nói đúng lý do, KHÔNG nói «chưa có mã NV»
  mk1_7  `dung_ma_nv` với mã đủ dài → vẫn chạy như cũ
  mk1_8  NHẬT KÝ không bao giờ chứa mật khẩu
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_mk1.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_mk1.db"): os.remove("test_mk1.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app); TOK = {}
MAT_KHAU_MAU = "Vtos@Demo#2026"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": MAT_KHAU_MAU}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _ai_do(h, tru=()):
    """Một tài khoản KHÔNG phải lãnh đạo để thử trên đó."""
    for r in client.get("/api/v1/users", headers=h).json():
        if r["role"] not in ("chutich", "tgd") and r["username"] not in tru:
            return r
    raise AssertionError("không tìm được tài khoản nào để thử — bộ nạp dữ liệu thử đã đổi")


def _dat_lai(h, uid, **than):
    return client.post(f"/api/v1/users/{uid}/reset-password", headers=h, json=than)


def test_mk1_1_mac_dinh_la_may_sinh_va_tra_dung_mot_lan():
    h = login("cntt"); r = _ai_do(h)
    kq = _dat_lai(h, r["id"])
    assert kq.status_code == 200, kq.text
    d = kq.json()
    assert d["cach"] == "tu_sinh", "không truyền gì thì phải là MÁY SINH, không phải mã NV"
    assert d.get("mat_khau"), "máy sinh mà không trả mật khẩu về thì không ai biết để gửi cho người dùng"
    assert "DUY NHẤT" in d.get("luu_y", ""), "phải nói rõ đây là nơi duy nhất mật khẩu hiện ra"


def test_mk1_2_mat_khau_sinh_ra_dang_nhap_duoc_that_va_bi_chan_vao_man():
    """Trả về một chuỗi mà chuỗi ấy KHÔNG đăng nhập được thì cả tính năng là vô nghĩa — và lỗi ấy
    không lộ ra ở bất kỳ phép thử nào chỉ đọc kết quả trả về."""
    h = login("cntt"); r = _ai_do(h)
    pw = _dat_lai(h, r["id"]).json()["mat_khau"]
    tok = client.post("/api/v1/auth/login", data={"username": r["username"], "password": pw})
    assert tok.status_code == 200, f"mật khẩu máy vừa sinh KHÔNG đăng nhập được: {tok.text}"
    j = tok.json()
    assert j.get("must_change_password") or True        # cờ đọc ở /auth/me bên dưới
    hh = {"Authorization": f"Bearer {j['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=hh).json()["must_change_password"] is True, \
        "mật khẩu tạm mà không bật cờ buộc đổi thì nó thành mật khẩu thật của người ta"
    # còn cờ thì mọi cửa khác phải bị chặn — đúng luật `deps.check_must_change_password`
    assert client.get("/api/v1/users", headers=hh).status_code in (403, 423), \
        "còn mật khẩu tạm mà đã vào được cửa khác — cờ buộc đổi không có tác dụng"


def test_mk1_3_hai_lan_sinh_khong_trung_nhau():
    h = login("cntt"); r = _ai_do(h)
    a = _dat_lai(h, r["id"]).json()["mat_khau"]
    b = _dat_lai(h, r["id"]).json()["mat_khau"]
    assert a != b, "hai lần sinh ra cùng một chuỗi — không phải ngẫu nhiên thật"


def test_mk1_4_khong_mang_ky_tu_doc_nham_va_du_dai():
    """Mật khẩu tạm được CHÉP TAY hoặc ĐỌC QUA ĐIỆN THOẠI. `0` với `O`, `1` với `l`, `5` với `S`
    đọc nhầm thành một lần «đăng nhập không được» mà không ai tìm ra vì sao."""
    from app.api.v1.hr import CHU_MAT_KHAU_TAM
    for c in "0O1lI5S2Z":
        assert c not in CHU_MAT_KHAU_TAM, f"ký tự dễ đọc nhầm «{c}» còn trong bảng chữ cái"
    h = login("cntt"); r = _ai_do(h)
    pw = _dat_lai(h, r["id"]).json()["mat_khau"]
    assert len(pw) >= 12, f"mật khẩu tạm chỉ {len(pw)} ký tự — quá ngắn"
    assert set(pw) <= set(CHU_MAT_KHAU_TAM)


def test_mk1_5_go_tay_thi_dung_dung_chuoi_ay_va_khong_tra_ve():
    h = login("cntt"); r = _ai_do(h)
    d = _dat_lai(h, r["id"], new_password="Chim#Bay#2026").json()
    assert d["cach"] == "go_tay"
    assert "mat_khau" not in d, "người bấm đã biết mật khẩu rồi, trả lại là thừa một chỗ lộ"
    assert client.post("/api/v1/auth/login",
                       data={"username": r["username"], "password": "Chim#Bay#2026"}).status_code == 200


def test_mk1_6_ma_ngan_bao_dung_ly_do_chu_khong_noi_la_chua_co_ma():
    """Chỗ hỏng Chủ tịch gặp. Lời báo cũ nói «Chưa có mã NV» trong khi mã có đủ — 31/109 người ở
    bảng lương 09/2026 mang mã 1–2 chữ số, kể cả mã `1` của chính Chủ tịch."""
    from app.db.session import SessionLocal
    from app.models.core import User as U
    h = login("cntt"); r = _ai_do(h)
    db = SessionLocal()
    try:
        t = db.get(U, r["id"]); cu = t.staff_code; t.staff_code = "15"; db.commit()
    finally:
        db.close()
    kq = _dat_lai(h, r["id"], dung_ma_nv=True)
    assert kq.status_code == 422
    loi = kq.json()["detail"]
    assert "15" in loi and "ngắn" in loi.lower(), f"lời báo không nói đúng chuyện gì đang xảy ra: {loi}"
    assert "chưa có mã" not in loi.lower(), f"vẫn nói SAI rằng thiếu mã, trong khi mã có đủ: {loi}"
    db = SessionLocal()
    try:
        t = db.get(U, r["id"]); t.staff_code = cu; db.commit()
    finally:
        db.close()


def test_mk1_7_ma_du_dai_van_chay_nhu_cu():
    from app.db.session import SessionLocal
    from app.models.core import User as U
    h = login("cntt"); r = _ai_do(h)
    db = SessionLocal()
    try:
        t = db.get(U, r["id"]); cu = t.staff_code; t.staff_code = "307"; db.commit()
    finally:
        db.close()
    d = _dat_lai(h, r["id"], dung_ma_nv=True).json()
    assert d["cach"] == "ma_nv"
    assert "mat_khau" not in d, "mã NV thì người bấm nhìn thấy ngay trên bảng, không cần trả về"
    assert client.post("/api/v1/auth/login",
                       data={"username": r["username"], "password": "307"}).status_code == 200
    db = SessionLocal()
    try:
        t = db.get(U, r["id"]); t.staff_code = cu; db.commit()
    finally:
        db.close()


def test_mk1_8_nhat_ky_khong_bao_gio_chua_mat_khau():
    """Nhật ký để truy AI làm gì, không phải chỗ cất chìa khoá. Ghi mật khẩu vào đấy là biến một
    quyển sổ nhiều người đọc được thành một kho mật khẩu."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    h = login("cntt"); r = _ai_do(h)
    pw = _dat_lai(h, r["id"]).json()["mat_khau"]
    db = SessionLocal()
    try:
        from app.models.core import AuditLog
        dong = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(20)).scalars().all()
        het = " ".join(f"{x.action} {x.entity} {x.before} {x.after}" for x in dong)
    finally:
        db.close()
    assert pw not in het, "MẬT KHẨU VỪA SINH NẰM TRONG NHẬT KÝ"
    assert "dat_lai_mat_khau" in het, "không ghi nhật ký thì không truy được ai đặt lại cho ai"


# ───────────────────────── MÀN HÌNH: nơi DUY NHẤT mật khẩu hiện ra ─────────────────────────
#
# Máy chủ trả mật khẩu về đúng một lần, nhưng nếu màn hình không VẼ nó ra thì cả tính năng bằng
# không — và không phép thử nào ở trên bắt được chuyện ấy: chúng chỉ đọc kết quả trả về.
import os as _os
import re as _re

WEB = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "web")


def _ma(duong: str) -> str:
    """Chỉ mã chạy — chú thích nhắc tới một tên không tính là mã dùng tên ấy."""
    src = open(_os.path.join(WEB, duong), encoding="utf-8").read()
    return _re.sub(r"/\*.*?\*/|//[^\n]*|\{/\*.*?\*/\}", "", src, flags=_re.S)


def test_mk1_9_man_phan_quyen_goi_cua_KHONG_kem_mat_khau():
    """Gửi `new_password: ""` là rơi về đường cũ. Để trống cả thân mới là MÁY SINH."""
    s = _ma("app/access/page.tsx")
    assert '"/users/${r.id}/reset-password"' not in s
    assert 'reset-password`, { method: "POST", json: {} }' in s, \
        "màn Phân quyền không còn gọi cửa đặt lại theo đường MÁY SINH"
    assert 'new_password: ""' not in s, \
        "còn gửi `new_password: \"\"` — đó là đường cũ, máy chủ sẽ lấy mã NV làm mật khẩu"


def test_mk1_10_man_hinh_phai_VE_mat_khau_ra_chu_khong_chi_nhan_ve():
    s = _ma("app/access/page.tsx")
    assert "setMkTam(" in s and "kq.mat_khau" in s, \
        "nhận mật khẩu về mà không giữ lại để vẽ — người bấm không bao giờ thấy nó"
    assert "{mkTam.mat_khau}" in s, "mật khẩu không được vẽ ra màn hình"
    assert "navigator.clipboard" in s, "không có nút chép — mật khẩu 12 ký tự chép tay rất dễ sai"


def test_mk1_11_mat_khau_KHONG_di_qua_toast():
    """Toast tự tắt sau vài giây. Mất chuỗi ấy là phải sinh lại, và lần sinh lại làm hỏng mật khẩu
    vừa gửi cho người dùng nếu họ chưa kịp dùng."""
    s = _ma("app/access/page.tsx")
    for dong in s.splitlines():
        if "toast(" in dong:
            assert "mat_khau" not in dong, f"mật khẩu đi qua toast — nó sẽ biến mất: {dong.strip()[:90]}"


def test_mk1_12_chi_MOT_cho_dat_lai_mat_khau():
    """Hai chỗ cùng sinh mật khẩu là hai chỗ cùng phải vẽ nó ra, và chỗ nào quên vẽ thì chỗ ấy
    lặng lẽ đổi mật khẩu của người ta rồi vứt chuỗi đi."""
    khac = _ma("components/SuaTaiKhoan.tsx")
    assert "reset-password" not in khac, \
        "khung Sửa tài khoản vẫn tự gọi cửa đặt lại — mật khẩu sinh ra ở đó không có chỗ nào hiện"
