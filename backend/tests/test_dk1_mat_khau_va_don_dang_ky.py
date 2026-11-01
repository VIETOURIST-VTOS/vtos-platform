# -*- coding: utf-8 -*-
"""DK-1 · Mật khẩu tài khoản ngoài + đơn đăng ký bốn bước (Chủ tịch chốt 01/11/2026).

Mỗi phép thử đo HAI CHIỀU: đúng thì qua, sai thì chặn. Phép thử chỉ đo một chiều là phép thử xanh
cả khi cửa hỏng.

  1. Tối thiểu 5 ký tự — 4 chặn, 5 qua.
  2. Tối đa 64 — 65 chặn, 64 qua.
  3. KHÔNG bắt viết hoa: mật khẩu toàn chữ thường phải QUA. Đây là phép thử giữ quyết định của
     Chủ tịch — ngày nào có người lén thêm luật trộn ký tự thì dòng này đỏ.
  4. Mật khẩu đã lộ bị chặn, và câu từ chối NÓI RÕ vì sao.
  5. Băm không cắt ở 72 byte — hai mật khẩu chỉ khác nhau sau byte thứ 72 phải khác băm.
  6. Thiếu bước nào thì bước 4 chặn bước ấy.
  7. Mật khẩu thô KHÔNG nằm trong bảng đơn, kể cả tạm.
  8. Đơn quá 24 giờ thì chết.
  9. Liên hệ đã có tài khoản thì bước 4 TỪ CHỐI — mã đúng không mở được tài khoản đã có.
 10. Đi hết bốn bước thì có tài khoản, có mật khẩu dùng được, và đơn biến mất.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def moi():
    import app.models  # noqa: F401
    from app.db.session import Base, get_db
    from app.main import app
    from app.services import cong_ngoai as C
    from app.api.v1 import cong_ngoai as A
    e = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    S = sessionmaker(bind=e)

    def _db():
        s = S()
        try:
            yield s
        finally:
            s.close()
    app.dependency_overrides[get_db] = _db
    gui = []
    goc_gui, goc_kenh = dict(C.GUI), C.kenh_san_sang
    C.GUI.update({"zalo": lambda db, lh, ma: gui.append(("zalo", lh, ma)),
                  "email": lambda db, lh, ma: gui.append(("email", lh, ma))})
    C.kenh_san_sang = lambda db=None: {
        k: {"ok": True, "ly_do": "", "ten": k.title(),
            "cho": "dien_thoai" if k == "zalo" else "email"} for k in ("zalo", "email")}
    A._LUOT.clear()
    yield {"c": TestClient(app), "S": S, "gui": gui, "C": C}
    app.dependency_overrides.pop(get_db, None)
    C.GUI.clear()
    C.GUI.update(goc_gui)
    C.kenh_san_sang = goc_kenh


def _ba_buoc(m, loai="khach_hang", dt="0912345678", em="", mk="hoa sen no thang bay"):
    c = m["c"]
    r = c.post("/api/v1/cong/dang-ky/lien-he",
               json={"loai": loai, "ho_ten": "Tran Van A", "dien_thoai": dt, "email": em})
    assert r.status_code == 200, r.text
    k = r.json()["khoa"]
    assert c.post("/api/v1/cong/dang-ky/mat-khau",
                  json={"khoa": k, "mat_khau": mk}).status_code == 200
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan",
                  json={"khoa": k, "dong_y_dieu_khoan": True}).status_code == 200
    return k


# ── 1-4 · luật mật khẩu, mỗi luật hai chiều ────────────────────────────────────────────────────

def test_dk1_1_toi_thieu_nam_ky_tu(moi):
    C = moi["C"]
    assert C.MK_TOI_THIEU == 5, "Chủ tịch chốt 5 ký tự ngày 01/11/2026"
    assert C.kiem_mat_khau("abcd") != "", "4 ký tự phải bị chặn"
    assert C.kiem_mat_khau("tribo") == "", "5 ký tự phải qua"


def test_dk1_2_toi_da_sau_muoi_tu(moi):
    C = moi["C"]
    assert C.MK_TOI_DA == 64
    assert C.kiem_mat_khau("x" * 64) == "", "64 ký tự phải qua"
    assert C.kiem_mat_khau("x" * 65) != "", "65 ký tự phải bị chặn"


def test_dk1_3_khong_bat_viet_hoa(moi):
    """Chủ tịch BỎ luật «phải có một chữ hoa» ngày 01/11/2026. Ai cũng viết hoa chữ đầu, nên nó
    làm mật khẩu khó nhớ mà không khó đoán. Dòng này đỏ nghĩa là có người lén thêm luật lại."""
    C = moi["C"]
    for mk in ("conmeotrang", "mua thu ha noi", "tribo"):
        assert C.kiem_mat_khau(mk) == "", f"«{mk}» toàn chữ thường, phải qua"
    nguon = open(C.__file__, encoding="utf-8").read()
    for cam in (".isupper()", "[A-Z]", "ký tự hoa", "chữ hoa và", "phải có hoa"):
        assert cam not in nguon, f"có luật trộn ký tự «{cam}» trong mã — Chủ tịch đã bỏ"


def test_dk1_4_mat_khau_da_lo_bi_chan_va_noi_ro_ly_do(moi):
    C = moi["C"]
    assert C.MK_DA_LO, "danh sách sàn không được rỗng"
    for mk in ("123456", "password", "matkhau", "qwerty"):
        loi = C.kiem_mat_khau(mk)
        assert loi != "", f"«{mk}» phải bị chặn"
        assert "lộ" in loi.lower(), f"câu từ chối phải nói rõ vì sao, đang là: {loi}"
    assert C.kiem_mat_khau("vietourist2026") != "", "mật khẩu chứa tên công ty phải bị chặn"
    assert C.kiem_mat_khau("mk0912345678", "0912345678") != "", "chứa số điện thoại phải bị chặn"
    assert C.kiem_mat_khau("tran van a oi", "", "Tran Van A") != "", "chứa họ tên phải bị chặn"


# ── 5 · băm không được cắt ở 72 byte ───────────────────────────────────────────────────────────

def test_dk1_5_bam_khong_cat_o_72_byte(moi):
    """bcrypt chỉ đọc 72 byte đầu. Tiếng Việt có dấu 3 byte một ký tự nên 64 ký tự có thể 192
    byte — không băm sha256 trước thì hai mật khẩu khác hẳn nhau sẽ cùng một băm."""
    C = moi["C"]
    a = "à" * 30 + "mot"          # 30*3 + 3 = 93 byte
    b = "à" * 30 + "hai"          # khác nhau ở byte 91-93, tức SAU byte thứ 72
    assert len(a.encode()) > 72 and len(b.encode()) > 72
    assert C.dung_mat_khau(a, C.bam_mat_khau(a)) is True
    assert C.dung_mat_khau(b, C.bam_mat_khau(b)) is True
    assert C.dung_mat_khau(b, C.bam_mat_khau(a)) is False, "bcrypt đang cắt ở 72 byte"
    assert C.dung_mat_khau("x", "") is False, "tài khoản chưa có mật khẩu thì không gì đúng"
    assert C.dung_mat_khau("", "") is False


# ── 6-8 · đơn đăng ký: thiếu bước nào thì chặn bước ấy ─────────────────────────────────────────

def test_dk1_6_thieu_buoc_nao_thi_chan_buoc_ay(moi):
    c = moi["c"]
    r = c.post("/api/v1/cong/dang-ky/lien-he",
               json={"loai": "khach_hang", "ho_ten": "Tran Van A", "dien_thoai": "0912345678"})
    k = r.json()["khoa"]
    # chưa đặt mật khẩu → không đồng ý điều khoản được, không gửi mã được
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan",
                  json={"khoa": k, "dong_y_dieu_khoan": True}).status_code == 422
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 422
    assert c.post("/api/v1/cong/dang-ky/mat-khau",
                  json={"khoa": k, "mat_khau": "hoa sen no"}).status_code == 200
    # có mật khẩu rồi nhưng CHƯA đồng ý điều khoản → vẫn không gửi mã được
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 422
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan",
                  json={"khoa": k, "dong_y_dieu_khoan": False}).status_code == 422
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan",
                  json={"khoa": k, "dong_y_dieu_khoan": True}).status_code == 200
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
    # ba bước xong mà chưa gõ mã thì VẪN chưa có tài khoản nào
    from app.models.cong_ngoai import TaiKhoanNgoai
    s = moi["S"]()
    assert s.execute(select(TaiKhoanNgoai)).scalars().first() is None
    s.close()


def test_dk1_7_mat_khau_tho_khong_nam_trong_bang_don(moi):
    from app.models.cong_ngoai import DonDangKy
    mk = "con meo trang nam 2026"
    _ba_buoc(moi, mk=mk)
    s = moi["S"]()
    d = s.execute(select(DonDangKy)).scalars().first()
    assert d is not None and d.mat_khau_bam
    for cot in ("khoa", "ho_ten", "dien_thoai", "email", "mat_khau_bam", "ma_khoa", "ip"):
        assert mk not in (getattr(d, cot) or ""), f"mật khẩu thô lọt vào cột {cot}"
    s.close()


def test_dk1_8_don_qua_han_thi_chet(moi):
    from app.models.cong_ngoai import DonDangKy
    C = moi["C"]
    k = _ba_buoc(moi)
    s = moi["S"]()
    d = s.execute(select(DonDangKy).where(DonDangKy.khoa == k)).scalars().first()
    assert C.DON_SONG_GIO == 24
    d.het_han = datetime.now() - timedelta(minutes=1)
    s.commit()
    s.close()
    r = moi["c"].post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"})
    assert r.status_code == 410, r.text


# ── 9-10 · bước cuối ───────────────────────────────────────────────────────────────────────────

def test_dk1_9_ma_dung_khong_mo_duoc_tai_khoan_da_co(moi):
    """Chủ tịch chốt 01/11/2026: mã một lần KHÔNG BAO GIỜ thay được mật khẩu. Nếu bước 4 đăng
    nhập hộ người đã có tài khoản thì cả điều 5 ấy thành vô nghĩa."""
    from app.models.cong_ngoai import TaiKhoanNgoai
    C = moi["C"]
    s = moi["S"]()
    s.add(TaiKhoanNgoai(loai="khach_hang", dien_thoai="0912345678", trang_thai="hoat_dong",
                        mat_khau_bam=C.bam_mat_khau("mat khau cu cua toi"), tao_luc=datetime.now()))
    s.commit()
    s.close()
    k = _ba_buoc(moi, mk="mat khau moi hoan toan")
    c = moi["c"]
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
    ma = moi["gui"][-1][2]
    r = c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": ma})
    assert r.status_code == 409, r.text
    assert "phien" not in r.text, "KHÔNG được cấp phiên"
    s = moi["S"]()
    ds = s.execute(select(TaiKhoanNgoai)).scalars().all()
    assert len(ds) == 1, "không được đẻ thêm tài khoản thứ hai"
    assert C.dung_mat_khau("mat khau cu cua toi", ds[0].mat_khau_bam), "mật khẩu cũ bị đổi"
    assert not C.dung_mat_khau("mat khau moi hoan toan", ds[0].mat_khau_bam)
    s.close()


def test_dk1_10_di_het_bon_buoc_thi_co_tai_khoan_co_mat_khau(moi):
    from app.models.cong_ngoai import TaiKhoanNgoai, DonDangKy
    C = moi["C"]
    mk = "hoa sen no thang bay"
    k = _ba_buoc(moi, mk=mk)
    c = moi["c"]
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
    ma = moi["gui"][-1][2]
    sai = "".join(str((int(x) + 1) % 10) for x in ma)      # chắc chắn KHÁC mã thật
    assert c.post("/api/v1/cong/dang-ky/xong",
                  json={"khoa": k, "ma": sai}).status_code == 422, "mã sai phải bị chặn"
    r = c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": ma})
    assert r.status_code == 200, r.text
    assert r.json()["phien"]
    s = moi["S"]()
    tk = s.execute(select(TaiKhoanNgoai)).scalars().first()
    assert tk is not None and tk.dien_thoai == "0912345678"
    assert tk.trang_thai == "hoat_dong"
    assert tk.dong_y_dieu_khoan_luc is not None
    assert tk.nhan_tin_quang_cao is False, "không bao giờ tự bật nhận quảng cáo"
    assert C.dung_mat_khau(mk, tk.mat_khau_bam), "mật khẩu đặt ở bước 2 phải dùng được"
    assert s.execute(select(DonDangKy)).scalars().first() is None, "đơn phải bị xoá"
    s.close()


def test_dk1_11_doi_tac_va_co_dong_tao_xong_van_phai_cho_duyet(moi):
    from app.models.cong_ngoai import TaiKhoanNgoai
    c = moi["c"]
    for loai, dt in (("doi_tac", "0912345671"), ("co_dong", "0912345672")):
        k = _ba_buoc(moi, loai=loai, dt=dt)
        assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
        ma = moi["gui"][-1][2]
        assert c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": ma}).status_code == 200
    s = moi["S"]()
    for loai in ("doi_tac", "co_dong"):
        tk = s.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.loai == loai)).scalars().first()
        assert tk.trang_thai == "ho_so", f"{loai} tạo xong phải là «Chưa gửi hồ sơ», không hoạt động ngay"
    s.close()
