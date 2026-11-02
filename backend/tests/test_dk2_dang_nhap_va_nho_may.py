# -*- coding: utf-8 -*-
"""DK-2 · Đăng nhập bằng mật khẩu, nhớ máy, quên mật khẩu (Chủ tịch chốt 01/11/2026).

Mỗi phép thử đo HAI CHIỀU. Những điều phải giữ:

  1. Mọi kiểu sai trả ĐÚNG MỘT câu — màn đăng nhập không được thành máy dò.
  2. Đúng mật khẩu nhưng máy LẠ thì KHÔNG vào thẳng: phải gõ mã.
  3. Máy ĐÃ NHỚ thì vào thẳng, không hỏi mã.
  4. Mã MỘT MÌNH không mở được gì — không có mật khẩu đúng trước thì không có mã nào được gửi.
  5. Dấu nhớ lưu dạng BĂM: dấu thô không nằm trong bảng.
  6. Nhớ tối đa 5 máy; máy thứ 6 đẩy máy cũ nhất ra.
  7. Đổi mật khẩu là QUÊN SẠCH mọi máy và tăng số phiên.
  8. Quên mật khẩu trả cùng một câu dù có tài khoản hay không.
  9. Phanh theo TÀI KHOẢN: sai 10 lần là khoá, đổi địa chỉ mạng cũng không lách được.
 10. Đối tác và cổ đông: máy lạ LUÔN hỏi mã, kể cả mật khẩu dài.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SUA-5 (02/11/2026): mật khẩu mẫu phải NGẮN HƠN MK_DU_DAI_KHOI_HOI (15). Bản cũ 20 ký tự nên khách
# hàng máy lạ được vào thẳng đúng theo luật «mật khẩu đủ dài khỏi hỏi mã» — phép thử 2 đỏ vì mẫu, không vì
# mã. Phép thử 10 giữ mật khẩu dài riêng để soát chiều ngược lại.
MK = "sen no thang7"
DT = "0912345678"


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


def _tao(moi, loai="khach_hang", dt=DT, mk=MK):
    from app.models.cong_ngoai import TaiKhoanNgoai
    C = moi["C"]
    s = moi["S"]()
    tk = TaiKhoanNgoai(loai=loai, ho_ten="Tran Van A", dien_thoai=dt,
                       trang_thai="hoat_dong" if loai == "khach_hang" else "ho_so",
                       mat_khau_bam=C.bam_mat_khau(mk), tao_luc=datetime.now())
    s.add(tk)
    s.commit()
    tid = tk.id
    s.close()
    return tid


def _vao(moi, dt=DT, mk=MK, loai="khach_hang", dau=""):
    return moi["c"].post("/api/v1/cong/dang-nhap",
                         json={"loai": loai, "lien_he": dt, "mat_khau": mk, "dau_nho": dau})


# ── 1 · một câu duy nhất cho mọi kiểu sai ──────────────────────────────────────────────────────

def test_dk2_1_moi_kieu_sai_tra_cung_mot_cau(moi):
    C = moi["C"]
    _tao(moi)
    _tao(moi, dt="0912345677", mk=MK)
    from app.models.cong_ngoai import TaiKhoanNgoai
    s = moi["S"]()
    s.add(TaiKhoanNgoai(loai="khach_hang", dien_thoai="0912345676", trang_thai="hoat_dong",
                        mat_khau_bam="", tao_luc=datetime.now()))      # tài khoản CHƯA có mật khẩu
    s.commit()
    s.close()
    cau = set()
    for dt, mk in ((DT, "mat khau sai hoan toan"),          # sai mật khẩu
                   ("0912000000", MK),                       # không có tài khoản
                   ("0912345676", MK)):                      # có tài khoản, chưa đặt mật khẩu
        r = _vao(moi, dt=dt, mk=mk)
        assert r.status_code == 401, r.text
        cau.add(r.text)
    assert len(cau) == 1, f"ba kiểu sai trả {len(cau)} câu khác nhau — màn này thành máy dò"
    assert C.SAI_DN in list(cau)[0]
    # và chiều ngược lại: đúng mật khẩu thì KHÔNG phải câu ấy
    assert _vao(moi).status_code == 200


# ── 2-3 · máy lạ phải gõ mã, máy quen thì không ───────────────────────────────────────────────

def test_dk2_2_may_la_thi_phai_go_ma(moi):
    _tao(moi)
    r = _vao(moi)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["xong"] is False and d.get("can_ma") is True, "máy lạ mà vào thẳng"
    assert "phien" not in d, "KHÔNG được cấp phiên khi chưa xác minh máy"
    assert moi["gui"], "phải gửi mã"


def test_dk2_3_may_da_nho_thi_vao_thang(moi):
    c = moi["c"]
    _tao(moi)
    k = _vao(moi).json()["khoa"]
    ma = moi["gui"][-1][2]
    r = c.post("/api/v1/cong/dang-nhap/xac-minh",
               json={"khoa": k, "ma": ma, "nho_may": True, "ten_may": "May nha"})
    assert r.status_code == 200, r.text
    dau = r.json()["dau_nho"]
    assert dau, "chọn nhớ máy thì phải có dấu nhớ"
    assert r.json()["phien"]
    truoc = len(moi["gui"])
    r2 = _vao(moi, dau=dau)
    assert r2.status_code == 200
    assert r2.json()["xong"] is True, "máy đã nhớ mà vẫn hỏi mã"
    assert r2.json()["phien"]
    assert len(moi["gui"]) == truoc, "máy đã nhớ mà vẫn gửi mã"
    # chiều ngược lại: dấu nhớ BỊA thì vẫn phải gõ mã
    assert _vao(moi, dau="dau-nho-bia-ra").json()["xong"] is False


# ── 4-5 · mã một mình không mở được gì; dấu nhớ lưu dạng băm ──────────────────────────────────

def test_dk2_4_ma_mot_minh_khong_mo_duoc_gi(moi):
    """Chủ tịch chốt 01/11: mã KHÔNG BAO GIỜ thay được mật khẩu. Sai mật khẩu thì không có mã
    nào được gửi — nên không có mã nào để gõ."""
    _tao(moi)
    r = _vao(moi, mk="mat khau sai hoan toan")
    assert r.status_code == 401
    assert not moi["gui"], "sai mật khẩu mà vẫn gửi mã — mã thành cửa vào"
    r2 = moi["c"].post("/api/v1/cong/dang-nhap/xac-minh", json={"khoa": "bia", "ma": "123456"})
    assert r2.status_code == 422


def test_dk2_5_dau_nho_luu_dang_bam(moi):
    from app.models.cong_ngoai import MayDaNho
    c = moi["c"]
    _tao(moi)
    k = _vao(moi).json()["khoa"]
    dau = c.post("/api/v1/cong/dang-nhap/xac-minh",
                 json={"khoa": k, "ma": moi["gui"][-1][2], "nho_may": True}).json()["dau_nho"]
    s = moi["S"]()
    m = s.execute(select(MayDaNho)).scalars().first()
    assert m is not None
    assert m.dau_bam != dau, "dấu nhớ THÔ nằm thẳng trong bảng"
    assert dau not in (m.dau_bam + m.ten_may + m.ip_cuoi)
    assert m.dau_bam == moi["C"]._bam_dau(dau)
    s.close()


# ── 6 · tối đa 5 máy ──────────────────────────────────────────────────────────────────────────

def test_dk2_6_nho_toi_da_nam_may(moi):
    from app.models.cong_ngoai import MayDaNho
    C, c = moi["C"], moi["c"]
    assert C.NHO_MAY_TOI_DA == 5 and C.NHO_MAY_NGAY == 90
    _tao(moi)
    for i in range(7):
        # SUA-5: bảy lần gửi mã cho cùng một liên hệ vượt phanh GUI_TOI_DA_MOI_GIO (5/giờ) — phanh ấy là
        # đúng. Phép thử này đo việc NHỚ MÁY, nên lùi giờ các mã đã gửi để mỗi vòng là một giờ khác.
        from app.models.cong_ngoai import MaXacThucNgoai
        s0 = moi["S"]()
        for m in s0.execute(select(MaXacThucNgoai)).scalars().all():
            m.tao_luc = m.tao_luc - timedelta(hours=2)
        s0.commit()
        s0.close()
        k = _vao(moi).json()["khoa"]
        r = c.post("/api/v1/cong/dang-nhap/xac-minh",
                   json={"khoa": k, "ma": moi["gui"][-1][2], "nho_may": True,
                         "ten_may": f"May {i}"})
        assert r.status_code == 200, r.text
        if i == 4:
            s = moi["S"]()
            assert len(s.execute(select(MayDaNho)).scalars().all()) == 5
            s.close()
    s = moi["S"]()
    ds = s.execute(select(MayDaNho)).scalars().all()
    assert len(ds) == 5, f"nhớ {len(ds)} máy, phải đúng 5"
    assert "May 0" not in [m.ten_may for m in ds], "máy cũ nhất phải bị đẩy ra"
    s.close()


# ── 7 · đổi mật khẩu là quên sạch máy ─────────────────────────────────────────────────────────

def test_dk2_7_dat_lai_mat_khau_quen_sach_may_va_tang_phien(moi):
    from app.models.cong_ngoai import MayDaNho, TaiKhoanNgoai
    C, c = moi["C"], moi["c"]
    tid = _tao(moi)
    k = _vao(moi).json()["khoa"]
    dau = c.post("/api/v1/cong/dang-nhap/xac-minh",
                 json={"khoa": k, "ma": moi["gui"][-1][2], "nho_may": True}).json()["dau_nho"]
    s = moi["S"]()
    phien_truoc = s.get(TaiKhoanNgoai, tid).phien
    assert len(s.execute(select(MayDaNho)).scalars().all()) == 1
    s.close()
    r = c.post("/api/v1/cong/quen-mat-khau/ma",
               json={"loai": "khach_hang", "lien_he": DT, "kenh": "zalo"})
    assert r.status_code == 200
    k2 = r.json()["khoa"]
    r2 = c.post("/api/v1/cong/quen-mat-khau/dat-lai",
                json={"khoa": k2, "ma": moi["gui"][-1][2], "mat_khau": "meo trang 2026"})
    assert r2.status_code == 200, r2.text
    s = moi["S"]()
    tk = s.get(TaiKhoanNgoai, tid)
    assert tk.phien == phien_truoc + 1, "đặt lại mật khẩu phải đăng xuất mọi nơi"
    assert not s.execute(select(MayDaNho)).scalars().all(), "phải quên sạch mọi máy"
    assert C.dung_mat_khau("meo trang 2026", tk.mat_khau_bam)
    assert not C.dung_mat_khau(MK, tk.mat_khau_bam), "mật khẩu cũ phải chết"
    s.close()
    # dấu nhớ cũ nay vô giá trị — vào lại phải gõ mã
    assert _vao(moi, mk="meo trang 2026", dau=dau).json()["xong"] is False


# ── 8 · quên mật khẩu không thành máy dò ──────────────────────────────────────────────────────

def test_dk2_8_quen_mat_khau_tra_cung_mot_cau(moi):
    C, c = moi["C"], moi["c"]
    _tao(moi)
    a = c.post("/api/v1/cong/quen-mat-khau/ma",
               json={"loai": "khach_hang", "lien_he": DT, "kenh": "zalo"})
    b = c.post("/api/v1/cong/quen-mat-khau/ma",
               json={"loai": "khach_hang", "lien_he": "0988000000", "kenh": "zalo"})
    assert a.status_code == b.status_code == 200
    assert a.json()["message"] == b.json()["message"] == C.CAU_QUEN
    assert b.json()["khoa"] == "", "liên hệ không có tài khoản thì không sinh mã nào"


# ── 9 · phanh theo TÀI KHOẢN ──────────────────────────────────────────────────────────────────

def test_dk2_9_phanh_theo_tai_khoan_doi_dia_chi_khong_lach_duoc(moi):
    C = moi["C"]
    assert C.DN_SAI_TOI_DA == 10 and C.DN_KHOA_PHUT == 15
    _tao(moi)
    for _ in range(C.DN_SAI_TOI_DA):
        assert _vao(moi, mk="sai hoan toan").status_code == 401
    r = _vao(moi)                      # mật khẩu ĐÚNG, nhưng đã bị khoá
    assert r.status_code == 429, "sai quá số lần mà vẫn cho thử tiếp"
    moi["C"].__dict__.setdefault("_", None)
    from app.models.cong_ngoai import TaiKhoanNgoai
    s = moi["S"]()
    tk = s.execute(select(TaiKhoanNgoai)).scalars().first()
    tk.dn_khoa_den = datetime.now() - timedelta(minutes=1)      # hết hạn khoá
    s.commit()
    s.close()
    assert _vao(moi).status_code == 200, "hết hạn khoá thì phải vào được"


# ── 10 · đối tác và cổ đông luôn hỏi mã ───────────────────────────────────────────────────────

def test_dk2_10_doi_tac_va_co_dong_may_la_luon_hoi_ma(moi):
    C = moi["C"]
    dai = "mot cau rat dai de nho ma kho doan"
    assert len(dai) >= C.MK_DU_DAI_KHOI_HOI
    _tao(moi, loai="khach_hang", dt="0912000001", mk=dai)
    assert _vao(moi, dt="0912000001", mk=dai).json()["xong"] is True, \
        "khách hàng mật khẩu đủ dài thì vào thẳng"
    for loai, dt in (("doi_tac", "0912000002"), ("co_dong", "0912000003")):
        _tao(moi, loai=loai, dt=dt, mk=dai)
        r = _vao(moi, dt=dt, mk=dai, loai=loai)
        assert r.status_code == 200, r.text
        assert r.json()["xong"] is False, f"{loai} mật khẩu dài mà vào thẳng — phải luôn hỏi mã"


# ── 11 · người dùng tự xem và tự gỡ máy ───────────────────────────────────────────────────────

def test_dk2_11_tu_xem_va_tu_go_may(moi):
    c = moi["c"]
    _tao(moi)
    k = _vao(moi).json()["khoa"]
    d = c.post("/api/v1/cong/dang-nhap/xac-minh",
               json={"khoa": k, "ma": moi["gui"][-1][2], "nho_may": True,
                     "ten_may": "May co quan"}).json()
    h = {"Authorization": "Bearer " + d["phien"]}
    r = c.get("/api/v1/cong/may", headers=h)
    assert r.status_code == 200, r.text
    ds = r.json()["dong"]
    assert len(ds) == 1 and ds[0]["ten_may"] == "May co quan"
    assert c.post(f"/api/v1/cong/may/{ds[0]['id']}/go", headers=h).status_code == 200
    assert c.get("/api/v1/cong/may", headers=h).json()["dong"] == []
    assert c.get("/api/v1/cong/may").status_code == 401, "không có phiên thì không xem được"
