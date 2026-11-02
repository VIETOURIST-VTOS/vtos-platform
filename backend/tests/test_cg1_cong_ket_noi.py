# -*- coding: utf-8 -*-
"""CG-1 · Cổng kết nối VTD — Chủ tịch duyệt bản xem thử 26/10/2026 (dựng từ bộ giao diện v3.2).

Điều phải giữ, mỗi điều một nhóm phép thử:
  1. Phiên cổng ngoài KHÔNG mở được cửa nội bộ nào, và phiên nhân viên không mở được cửa cổng ngoài.
  2. Mã một lần: lưu băm, dùng một lần, 5 phút, sai 5 lần là chết, 5 lần gửi mỗi giờ mỗi liên hệ.
     DK-4 (02/11/2026): mã chỉ còn là LỚP THỨ HAI — cửa /ma + /xac-thuc đã xoá, mọi phép thử đi qua
     bốn bước /dang-ky/*.
  3. Kênh chưa cấu hình thì nói ra (503), không giả vờ đã gửi; Zalo cần số điện thoại, Email cần email.
  4. Lần đầu phải đồng ý điều khoản; chưa đồng ý thì mã KHÔNG bị tiêu. Không tự bật nhận quảng cáo.
  5. Đối tác / cổ đông chỉ gửi hồ sơ; duyệt đúng người (NCC — TP ĐH / GĐ KD; đại lý, CTV — GĐ KD;
     cổ đông — IR); trả bổ sung, từ chối, khoá phải có lý do; khoá / đăng xuất làm phiên cũ chết ngay.
  6. Giao diện dựng từ đúng bản v3.2 đã sửa theo Chủ tịch.
"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

GOC = Path(__file__).resolve().parents[2]


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
    C.GUI.update({"zalo": lambda db, lh, ma: gui.append(("zalo", lh, ma)), "email": lambda db, lh, ma: gui.append(("email", lh, ma))})
    mo = {"zalo": True, "email": True}
    C.kenh_san_sang = lambda db=None: {k: {"ok": mo[k], "ly_do": "" if mo[k] else "chưa cấu hình", "ten": k.title(),
                                           "cho": "dien_thoai" if k == "zalo" else "email"} for k in mo}
    A._LUOT.clear()
    yield {"c": TestClient(app), "S": S, "gui": gui, "mo": mo}
    app.dependency_overrides.pop(get_db, None)
    C.GUI.clear(); C.GUI.update(goc_gui); C.kenh_san_sang = goc_kenh


def _nhan_vien(S, username, vai):
    from app.models.core import User
    from app.core.security import hash_password, create_token
    s = S()
    s.add(User(username=username, full_name=username.upper(), role=vai, password_hash=hash_password("x" * 12), active=True))
    s.commit(); s.close()
    return {"Authorization": f"Bearer {create_token(username, vai)}"}


MK = "sen no thang7"        # 13 ký tự: dưới ngưỡng «đủ dài khỏi hỏi mã» của DK-2


def _den_buoc_ma(m, loai="khach_hang", lh="0912345678"):
    """DK-4 (02/11/2026): cửa /ma + /xac-thuc đã xoá khỏi máy chủ. Tài khoản chỉ ra đời qua bốn bước
    /dang-ky/*. Hàm này đi ba bước đầu và trả khoá ĐƠN, chưa gửi mã."""
    c = m["c"]
    lien = {"email": lh} if "@" in lh else {"dien_thoai": lh}
    r1 = c.post("/api/v1/cong/dang-ky/lien-he", json={"loai": loai, "ho_ten": "Khach Thu", **lien})
    assert r1.status_code == 200, r1.text
    k = r1.json()["khoa"]
    assert c.post("/api/v1/cong/dang-ky/mat-khau", json={"khoa": k, "mat_khau": MK}).status_code == 200
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan", json={"khoa": k, "dong_y_dieu_khoan": True}).status_code == 200
    return k


def _dang_nhap(m, loai="khach_hang", lh="0912345678", kenh="zalo"):
    """Tạo tài khoản đủ bốn bước. Trả (câu gửi mã, câu tạo xong) — câu sau mang `phien` và `toi`."""
    c = m["c"]
    k = _den_buoc_ma(m, loai, lh)
    r = c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": kenh})
    assert r.status_code == 200, r.text
    r2 = c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": m["gui"][-1][2]})
    return r, r2


# ── 1 · hai thế giới phiên tách hẳn ─────────────────────────────────────────────────────────────

def test_phien_ngoai_khong_mo_cua_noi_bo_va_nguoc_lai(moi):
    _, r2 = _dang_nhap(moi)
    ngoai = {"Authorization": f"Bearer {r2.json()['phien']}"}
    c = moi["c"]
    assert c.get("/api/v1/cong/toi", headers=ngoai).status_code == 200
    for duong in ("/api/v1/auth/me", "/api/v1/tai-khoan-ngoai", "/api/v1/daily-reports/viec"):
        assert c.get(duong, headers=ngoai).status_code == 401, duong
    noi_bo = _nhan_vien(moi["S"], "ct", "chutich")
    assert c.get("/api/v1/cong/toi", headers=noi_bo).status_code == 401
    assert c.get("/api/v1/cong/toi").status_code == 401


# ── 2 · mã một lần ─────────────────────────────────────────────────────────────────────────────

def test_dk4_cua_vao_bang_ma_da_mat_khoi_may_chu(moi):
    """Điều 5 Chủ tịch chốt 01/11/2026: mã một lần KHÔNG BAO GIỜ thay được mật khẩu. DK-3 bỏ nó khỏi
    màn hình; DK-4 xoá nó khỏi máy chủ. Dòng này đỏ nghĩa là có người mở lại cửa tạo tài khoản
    không mật khẩu."""
    c = moi["c"]
    assert c.post("/api/v1/cong/ma", json={"loai": "khach_hang", "lien_he": "0912345678", "kenh": "zalo"}).status_code in (404, 405)
    assert c.post("/api/v1/cong/xac-thuc", json={"khoa": "x", "ma": "000000"}).status_code in (404, 405)
    assert moi["gui"] == [], "không được gửi mã nào qua cửa đã xoá"
    from app.services import cong_ngoai as C
    assert not hasattr(C, "xac_thuc"), "hàm tạo tài khoản bằng mã còn trong máy chủ"


def test_ma_luu_bam_dung_mot_lan(moi):
    r, r2 = _dang_nhap(moi)
    ma = moi["gui"][-1][2]
    assert len(ma) == 6 and ma.isdigit() and r2.status_code == 200
    from app.models.cong_ngoai import MaXacThucNgoai
    s = moi["S"]()
    row = s.execute(select(MaXacThucNgoai)).scalars().one()
    assert ma not in row.ma_bam and row.da_dung
    s.close()
    lai = moi["c"].post("/api/v1/cong/dang-ky/xong", json={"khoa": r.json()["khoa"], "ma": ma})
    assert lai.status_code in (410, 422) and lai.json()["detail"]["ma"] in ("don_het", "ma_het")
    assert "khoa" in r.json() and ma not in r.text, "mã thật không bao giờ trả về trình duyệt"


def test_sai_nam_lan_la_chet_va_het_han(moi):
    c = moi["c"]
    k = _den_buoc_ma(moi)
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
    dung = moi["gui"][-1][2]
    sai = "000000" if dung != "000000" else "111111"
    for i in range(5):
        x = c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": sai})
        assert x.status_code == 422
    assert c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": dung}).status_code == 422
    from app.services import cong_ngoai as C
    k2 = _den_buoc_ma(moi, lh="0987654321")
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k2, "kenh": "zalo"}).status_code == 200
    s = moi["S"]()
    with pytest.raises(C.LoiCong):
        C.dang_ky_xong(s, k2, moi["gui"][-1][2], now=datetime.now() + timedelta(minutes=6))
    s.close()


def test_toi_da_nam_lan_gui_moi_gio(moi):
    from app.services import cong_ngoai as C
    s = moi["S"]()
    for _ in range(5):
        C.gui_ma(s, "khach_hang", "0912 345 678", "zalo")
    with pytest.raises(C.LoiCong) as ex:
        C.gui_ma(s, "khach_hang", "+84912345678", "zalo")
    assert ex.value.status == 429, "cùng một số viết ba kiểu vẫn là một liên hệ"
    s.close()


def test_khong_thanh_may_do(moi):
    _dang_nhap(moi)                              # 0912345678 đã có tài khoản
    c = moi["c"]
    co = c.post("/api/v1/cong/dang-ky/lien-he", json={"loai": "khach_hang", "ho_ten": "Ai Do", "dien_thoai": "0912345678"}).json()
    chua = c.post("/api/v1/cong/dang-ky/lien-he", json={"loai": "khach_hang", "ho_ten": "Ai Do", "dien_thoai": "0909000111"}).json()
    assert set(co) == set(chua) and co["buoc"] == chua["buoc"] == 2


# ── 3 · kênh ──────────────────────────────────────────────────────────────────────────────────

def test_kenh_chua_cau_hinh_thi_noi_ra_va_khong_luu_ma(moi):
    moi["mo"]["zalo"] = False
    k = _den_buoc_ma(moi)
    r = moi["c"].post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"})
    assert r.status_code == 503 and r.json()["detail"]["ma"] == "kenh_chua_mo"
    assert moi["gui"] == []
    sai = moi["c"].post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "email"})
    assert sai.status_code == 422, "đơn chỉ có số điện thoại thì không nhận mã qua Email"


def test_gui_loi_thi_khong_co_ma_song(moi):
    from app.services import cong_ngoai as C
    from app.models.cong_ngoai import MaXacThucNgoai

    def hong(db, lh, ma):
        raise RuntimeError("máy chủ thư từ chối")
    C.GUI["email"] = hong
    k = _den_buoc_ma(moi, loai="co_dong", lh="a@b.vn")
    r = moi["c"].post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "email"})
    assert r.status_code == 502
    s = moi["S"](); assert s.execute(select(MaXacThucNgoai)).first() is None; s.close()


def test_kenh_that_doc_cau_hinh_khong_viet_cung():
    from app.services import cong_ngoai as C
    k = C.kenh_san_sang(None)
    assert set(k) == {"zalo", "email"} and all("ly_do" in v for v in k.values())
    src = (GOC / "backend/app/services/cong_ngoai.py").read_text(encoding="utf-8")
    assert "settings.SMTP_HOST" in src and 'MUC_ZNS = "ma_xac_thuc"' in src


# ── 4 · đồng ý điều khoản ─────────────────────────────────────────────────────────────────────

def test_chua_dong_y_thi_ma_khong_bi_tieu(moi):
    c = moi["c"]
    r1 = c.post("/api/v1/cong/dang-ky/lien-he", json={"loai": "khach_hang", "ho_ten": "Khach Thu", "dien_thoai": "0912345678"})
    k = r1.json()["khoa"]
    assert c.post("/api/v1/cong/dang-ky/mat-khau", json={"khoa": k, "mat_khau": MK}).status_code == 200
    r3 = c.post("/api/v1/cong/dang-ky/dieu-khoan", json={"khoa": k, "dong_y_dieu_khoan": False})
    assert r3.status_code == 422 and r3.json()["detail"]["ma"] == "can_dong_y"
    chan = c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"})
    assert chan.status_code == 422 and moi["gui"] == [], "chưa đồng ý thì chưa gửi mã nào"
    assert c.post("/api/v1/cong/dang-ky/dieu-khoan", json={"khoa": k, "dong_y_dieu_khoan": True}).status_code == 200
    assert c.post("/api/v1/cong/dang-ky/ma", json={"khoa": k, "kenh": "zalo"}).status_code == 200
    r4 = c.post("/api/v1/cong/dang-ky/xong", json={"khoa": k, "ma": moi["gui"][-1][2]})
    assert r4.status_code == 200
    toi = r4.json()["toi"]
    assert toi["trang_thai"] == "hoat_dong" and toi["nhan_tin_quang_cao"] is False
    assert "0912345678" not in r4.text, "liên hệ trả về đã che"


# ── 5 · đối tác / cổ đông ─────────────────────────────────────────────────────────────────────

def test_doi_tac_gui_ho_so_va_duyet_dung_nguoi(moi):
    c = moi["c"]
    _, r2 = _dang_nhap(moi, loai="doi_tac", lh="dl@daily.vn", kenh="email")
    ngoai = {"Authorization": f"Bearer {r2.json()['phien']}"}
    assert r2.json()["toi"]["trang_thai"] == "ho_so"
    assert c.post("/api/v1/cong/ho-so", json={"ho_ten": "A", "loai_doi_tac": "xx"}, headers=ngoai).status_code == 422
    h = c.post("/api/v1/cong/ho-so", json={"ho_ten": "Nguyễn A", "loai_doi_tac": "dai_ly", "ten_don_vi": "Đại lý B"}, headers=ngoai)
    assert h.status_code == 200 and h.json()["toi"]["trang_thai"] == "cho_duyet"
    assert c.post("/api/v1/cong/ho-so", json={"ho_ten": "x", "loai_doi_tac": "dai_ly", "ten_don_vi": "y"}, headers=ngoai).status_code == 422
    tid = h.json()["toi"]["id"]
    tp_dh, gd_kd, ir = _nhan_vien(moi["S"], "tp", "tp_dh"), _nhan_vien(moi["S"], "gd", "gd_kd"), _nhan_vien(moi["S"], "ir", "ir_phapche")
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "duyet"}, headers=tp_dh).status_code == 403, "đại lý do GĐ KD duyệt"
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "duyet"}, headers=ir).status_code == 403
    assert all(d["id"] != tid for d in c.get("/api/v1/tai-khoan-ngoai", headers=ir).json()["dong"]), "IR không thấy hồ sơ đối tác"
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "bo_sung"}, headers=gd_kd).status_code == 422, "trả bổ sung phải có lý do"
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "duyet"}, headers=gd_kd).status_code == 200
    assert c.get("/api/v1/cong/toi", headers=ngoai).json()["trang_thai"] == "hoat_dong"
    # khoá → phiên đang mở chết ngay
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "khoa", "ly_do": "Vi phạm hợp đồng"}, headers=gd_kd).status_code == 200
    assert c.get("/api/v1/cong/toi", headers=ngoai).status_code == 401
    x = c.post("/api/v1/cong/dang-nhap", json={"loai": "doi_tac", "lien_he": "dl@daily.vn", "mat_khau": MK})
    assert x.status_code == 403 and x.json()["detail"]["ma"] == "bi_khoa"


def test_co_dong_do_ir_xac_minh_va_khach_khong_tu_gui_ho_so(moi):
    c = moi["c"]
    _, r2 = _dang_nhap(moi, loai="co_dong", lh="0908111222")
    ngoai = {"Authorization": f"Bearer {r2.json()['phien']}"}
    assert c.post("/api/v1/cong/ho-so", json={"ho_ten": "C"}, headers=ngoai).status_code == 422, "cổ đông phải ghi CCCD/MSDN"
    h = c.post("/api/v1/cong/ho-so", json={"ho_ten": "C", "giay_to": "079000000001"}, headers=ngoai)
    tid = h.json()["toi"]["id"]
    gd_kd, ir = _nhan_vien(moi["S"], "gd", "gd_kd"), _nhan_vien(moi["S"], "ir", "ir_phapche")
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "duyet"}, headers=gd_kd).status_code == 403
    assert c.post(f"/api/v1/tai-khoan-ngoai/{tid}", json={"hanh_dong": "duyet"}, headers=ir).status_code == 200
    _, k = _dang_nhap(moi, lh="0907000000")
    kh = {"Authorization": f"Bearer {k.json()['phien']}"}
    assert c.post("/api/v1/cong/ho-so", json={"ho_ten": "K"}, headers=kh).status_code == 422


def test_dang_xuat_lam_chet_phien(moi):
    _, r2 = _dang_nhap(moi)
    ngoai = {"Authorization": f"Bearer {r2.json()['phien']}"}
    c = moi["c"]
    assert c.post("/api/v1/cong/dang-xuat", headers=ngoai).status_code == 200
    assert c.get("/api/v1/cong/toi", headers=ngoai).status_code == 401


def test_vai_xem_khop_bang_man_hinh():
    from app.services import cong_ngoai as C
    from app.services import access as AC
    assert set(C.VAI_XEM) == set(AC.MENU_ROLES["/tai-khoan-ngoai"])
    assert AC.MAN_HINH_API["/tai-khoan-ngoai"] == ("/api/v1/tai-khoan-ngoai",)


# ── 6 · giao diện ─────────────────────────────────────────────────────────────────────────────

def test_giao_dien_dung_ban_v32_da_sua():
    manh = (GOC / "web/components/cong/manh.ts").read_text(encoding="utf-8").replace('\\"', '"')
    # v3.4 (Chủ tịch chỉ định 26/10/2026): nhận diện gộp vào banner, Trái Đất + máy bay chuyển động có nút dừng
    for co in ("CÔNG TY CỔ PHẦN", "VIETOURIST<span>HOLDINGS</span>", "Khám phá · Kết nối · Đồng hành",
               "Chào mừng đến với hệ sinh thái số Vietourist.", "v5-earth", "v5-plane", "data-hero-motion", "/cong/earth.webp"):
        assert co in manh, co
    assert (GOC / "web/public/cong/earth.webp").exists()
    css = (GOC / "web/public/cong/vtd.css").read_text(encoding="utf-8")
    assert "is-paused .v5-plane{animation-play-state:paused}" in css and "prefers-reduced-motion" in css
    for bo in ("HỆ SINH THÁI VIETOURIST HOLDINGS", "Không gian dành cho đội ngũ", "Truy cập theo tài khoản và quyền của bạn",
               "Bản thiết kế v3.2", "VTD / CỔNG KẾT NỐI"):
        assert bo not in manh, bo
    for co in ('data-go-role="nhan-vien"', 'data-go-role="khach-hang"',
               'data-go-role="doi-tac"', 'data-go-role="co-dong"', "/cong/logo.png"):
        assert co in manh, co
    assert (GOC / "web/public/cong/vtd.css").exists() and (GOC / "web/public/cong/logo.png").exists()
    login = (GOC / "web/app/login/page.tsx").read_text(encoding="utf-8")
    # SUA-5 (02/11/2026): DK-3 (#609) đổi cổng ngoài sang đăng nhập bằng MẬT KHẨU + mã xác minh máy lạ —
    # đường cũ "/ma" và "/xac-thuc" không còn trên màn hình; soát đúng hai đường mới.
    for co in ('"/dang-nhap"', '"/dang-nhap/xac-minh"', "Zalo", "Email", "login(u.trim(), p)", "luuPhienCong"):
        assert co in login, co
    assert 'KHOA_PHIEN_CONG = "vtd_cong_phien"' in (GOC / "web/lib/cong.ts").read_text(encoding="utf-8")
