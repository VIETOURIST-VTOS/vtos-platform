# -*- coding: utf-8 -*-
"""AT-1 · Khám phá ẩm thực trên web VTD (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. «Hiện trên cổng» = hiện giới thiệu. Đặt bàn chỉ mở khi đủ 5 điều kiện máy tính: hợp đồng đã ký có tệp
     còn hiệu lực, đã gắn NCC, có thực đơn đang bán, liên hệ đã xác minh, hoa hồng đã khai. Không có nút bật tay.
  2. Nhập tệp: đọc thử không ghi gì; nhập thì bản ghi mới chưa hiện, mang nguồn; trùng chính xác tên + địa danh
     (bỏ dấu / khoảng trắng) thì bỏ qua, không tự gộp. Chỉ Điều hành.
  3. Hợp đồng: Điều hành ghi nhận đã ký + tải tệp vào hồ sơ NCC; bản mới thay bản cũ phải có lý do, bản cũ giữ.
     Tệp hợp đồng chỉ Điều hành / Kế toán / BKS mở.
  4. Bật hàng loạt vẫn giữ luật hai người. Nội dung món / điểm đến: Marketing viết, chỉ bản bật mới ra ngoài.
  5. Cửa công khai /api/v1/am-thuc: không đăng nhập, chỉ đọc, không lộ dữ liệu nội bộ, có phanh.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.test_dt2_dat_ban import _Kho

HN = dt.date(2026, 11, 1)


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import nha_hang as N, storage as ST
    ST._CACHE["s"] = _Kho()
    e = create_engine("sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("tp", "tp_dh"), ("tp2", "tp_dh"), ("kd", "nv_kd"), ("kt", "ketoan"), ("mkt", "nv_mkt")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(N, "_hom_nay", lambda: HN)
    yield s
    s.close(); ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


CSV = ("source_order,source_name,source_city,source_dishes\n"
       "1,Phở Hòa,Ho Chi Minh City,Phở bò\n"
       "2,Bún Chả Hương Liên,Hanoi,Bún chả\n"
       "3,  phở   hoà ,ho chi minh city,trùng\n"
       "4,,Hue,thiếu tên\n").encode()


def _hd(s, nid, **them):
    from app.services import nha_hang as N
    d = {"da_ky": True, "so_hd": "HD-01/2026", "ngay_ky": "2026-10-20", "tu_ngay": "2026-10-20", "hoa_hong_pct": "10", **them}
    return N.ghi_hop_dong(s, _u(s, "dh"), nid, d, "hd.pdf", "application/pdf", b"%PDF-1.4 hop dong da ky")


# ── 2 · nhập tệp ────────────────────────────────────────────────────────────────────────────────

def test_nhap_tep_doc_thu_roi_nhap_khong_gop(db):
    from app.services import nha_hang as N
    from app.models.nha_hang import NhaHang
    with pytest.raises(N.LoiNhaHang):
        N.nhap_tep(db, _u(db, "kd"), "ds.csv", CSV, "Danh mục thử")                    # Kinh doanh không nhập
    with pytest.raises(N.LoiNhaHang, match="nguồn"):
        N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "")
    r = N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=True)
    assert r["moi"] == 2 and r["trung"] == 1 and len(r["loi"]) == 1 and not r["da_nhap"]
    assert db.execute(select(NhaHang)).scalars().all() == []                            # đọc thử không ghi
    N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=False)
    ds = db.execute(select(NhaHang).order_by(NhaHang.id)).scalars().all()
    assert [(n.ten, n.tinh_thanh, n.dia_danh_nguon, n.hien_cong, n.nguon) for n in ds] == [
        ("Phở Hòa", "TP. Hồ Chí Minh", "Ho Chi Minh City", False, "Danh mục thử"),
        ("Bún Chả Hương Liên", "Hà Nội", "Hanoi", False, "Danh mục thử")]
    assert ds[0].nguon_ref == "1" and ds[0].mon_noi_bat == "Phở bò"
    r2 = N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=False)           # nhập lại: không nhân đôi
    assert r2["moi"] == 0 and len(db.execute(select(NhaHang)).scalars().all()) == 2
    with pytest.raises(N.LoiNhaHang, match="tiêu đề"):
        N.nhap_tep(db, _u(db, "dh"), "x.csv", b"a,b\n1,2\n", "X")


def test_nhap_json(db):
    from app.services import nha_hang as N
    js = '[{"name": "Bánh Xèo 46A", "city": "Saigon", "dishes": ["Bánh xèo", "Gỏi cuốn"]}]'.encode()
    r = N.nhap_tep(db, _u(db, "dh"), "ds.json", js, "JSON thử", thu=False)
    assert r["moi"] == 1 and r["mau"][0]["tinh"] == "TP. Hồ Chí Minh" and r["mau"][0]["mon"] == "Bánh xèo, Gỏi cuốn"


# ── 1 · năm điều kiện ───────────────────────────────────────────────────────────────────────────

def test_hien_gioi_thieu_nhung_chua_dat_khi_chua_du_dieu_kien(db):
    from app.services import nha_hang as N, cong_khach as K
    from app.models.suppliers import Supplier
    N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=False)
    n = N.danh_sach_vtos(db)["nha_hang"][0]
    N.bat_hien(db, _u(db, "tp"), n["id"], True)                                          # không cần thực đơn
    cong = N.danh_sach_cong(db)["nha_hang"]
    assert cong[0]["mo_dat"] is False and cong[0]["thuc_don"] == [] and cong[0]["gia_tu"] is None
    nh = N.mot_nha_hang_cong(db, n["id"])[0]

    def ok():
        return {x["ma"]: x["ok"] for x in N.dieu_kien_mo_dat(db, nh, None, HN)}
    assert not any(ok().values())
    with pytest.raises(N.LoiNhaHang, match="nhà cung cấp"):
        _hd(db, nh.id)                                                                    # chưa gắn NCC thì chưa lưu được hợp đồng
    sup = Supplier(code="NCC0101", ten="Phở Hòa", loai="nha_hang"); db.add(sup); db.flush()
    nh.supplier_id = sup.id; db.commit()
    td = N.luu_thuc_don(db, _u(db, "dh"), nh.id, {"ten": "Set phở", "gia_nguoi_lon": 120000})
    N.xac_minh_lien_he(db, _u(db, "dh"), nh.id, True)
    assert nh.hien_cong is False                                                          # thêm gói bán khi đang hiện → tự tắt (KH-2)
    N.bat_hien(db, _u(db, "tp"), nh.id, True)
    assert ok() == {"hop_dong": False, "ncc": True, "thuc_don": True, "lien_he": True, "hoa_hong": False}
    assert not N.mo_dat(db, nh, None, HN)
    yc = (nh.id, td.id, HN + dt.timedelta(days=3), "18:30", 2, 0, HN)
    with pytest.raises(N.LoiNhaHang, match="chưa mở đặt"):
        N.kiem_dat_ban(db, *yc)
    _hd(db, nh.id, hoa_hong_pct="")                                                       # hợp đồng không khai hoa hồng
    assert ok()["hop_dong"] and not ok()["hoa_hong"]
    _hd(db, nh.id, so_hd="HD-01b", ly_do="Bổ sung hoa hồng")
    assert all(ok().values())
    assert N.mo_dat(db, nh, None, HN)
    assert N.danh_sach_cong(db, chi_dat=True)["nha_hang"][0]["gia_tu"] == 120000
    assert N.kiem_dat_ban(db, *yc)[2] == 240000
    assert K is not None


def test_hop_dong_het_han_thi_dong_dat(db):
    from app.services import nha_hang as N
    from app.models.suppliers import Supplier
    nh = N.luu_nha_hang(db, _u(db, "dh"), {"ten": "Quán Biển", "tinh_thanh": "Nha Trang"})
    sup = Supplier(code="NCC0102", ten="Quán Biển", loai="nha_hang"); db.add(sup); db.flush()
    nh.supplier_id, nh.lien_he_xac_minh = sup.id, True; db.commit()
    N.luu_thuc_don(db, _u(db, "dh"), nh.id, {"ten": "Set", "gia_nguoi_lon": 300000})
    _hd(db, nh.id, den_ngay="2026-12-31")
    N.bat_hien(db, _u(db, "tp"), nh.id, True)
    assert N.mo_dat(db, nh, None, HN) and not N.mo_dat(db, nh, None, dt.date(2027, 1, 2))
    with pytest.raises(N.LoiNhaHang, match="sau ngày bắt đầu"):
        _hd(db, nh.id, tu_ngay="2026-12-01", den_ngay="2026-11-01", ly_do="Gia hạn")


# ── 3 · hợp đồng ────────────────────────────────────────────────────────────────────────────────

def test_hop_dong_phien_ban_va_quyen_xem_tep(db):
    from app.services import nha_hang as N
    from app.models.nha_hang import HopDongNhaHang
    from app.models.suppliers import Supplier
    nh = N.luu_nha_hang(db, _u(db, "dh"), {"ten": "Nhà hàng Sen"})
    sup = Supplier(code="NCC0103", ten="Sen", loai="nha_hang"); db.add(sup); db.flush()
    nh.supplier_id = sup.id; db.commit()
    for sai, loi in (({"da_ky": False}, "Đã ký"), ({"so_hd": ""}, "số hợp đồng"), ({"ngay_ky": ""}, "ngày ký"),
                     ({"hoa_hong_pct": "150"}, "0 đến 100")):
        with pytest.raises(N.LoiNhaHang, match=loi):
            _hd(db, nh.id, **sai)
    with pytest.raises(N.LoiNhaHang, match="tệp"):
        N.ghi_hop_dong(db, _u(db, "dh"), nh.id, {"da_ky": True, "so_hd": "X", "ngay_ky": "2026-10-20", "tu_ngay": "2026-10-20"}, "a.pdf", "", b"")
    with pytest.raises(N.LoiNhaHang):
        N.ghi_hop_dong(db, _u(db, "kd"), nh.id, {"da_ky": True}, "a.pdf", "", b"x")       # Kinh doanh không ghi
    h1 = _hd(db, nh.id, hoa_hong_pct="12,5")
    assert h1.hoa_hong_bps == 1250 and h1.phien_ban == 1
    with pytest.raises(N.LoiNhaHang, match="lý do"):
        _hd(db, nh.id, so_hd="HD-02")
    h2 = _hd(db, nh.id, so_hd="HD-02", hoa_hong_pct="", hoa_hong_co_dinh="50000", ly_do="Phụ lục đổi sang hoa hồng cố định")
    db.refresh(h1)
    assert h1.con_dung is False and h2.con_dung and h2.phien_ban == 2 and h2.thay_cho_id == h1.id
    assert len(db.execute(select(HopDongNhaHang)).scalars().all()) == 2                  # bản cũ không bị xóa
    assert N._hd_out(h2)["hoa_hong"] == "50.000 đ/đơn"
    data, a = N.tep_hop_dong(db, _u(db, "kt"), h2.id)
    assert data == b"%PDF-1.4 hop dong da ky" and a.doi_tuong == "nha_cung_cap" and a.doi_tuong_id == "NCC0103"
    for ai in ("kd", "mkt"):
        with pytest.raises(N.LoiNhaHang):
            N.tep_hop_dong(db, _u(db, ai), h2.id)
    vt = N.danh_sach_vtos(db)["nha_hang"][0]
    assert [h["so_hd"] for h in vt["hop_dong"]] == ["HD-02", "HD-01/2026"]


# ── 4 · bật hàng loạt, nội dung ─────────────────────────────────────────────────────────────────

def test_bat_hang_loat_giu_luat_hai_nguoi(db):
    from app.services import nha_hang as N
    from app.models.nha_hang import NhaHang
    N.nhap_tep(db, _u(db, "tp"), "ds.csv", CSV, "TP nhập", thu=False)                    # TP ĐH tự nhập
    ids = [n.id for n in db.execute(select(NhaHang)).scalars()]
    with pytest.raises(N.LoiNhaHang):
        N.hien_hang_loat(db, _u(db, "dh"), ids, True)                                     # NV ĐH không bật
    r = N.hien_hang_loat(db, _u(db, "tp"), ids, True)
    assert r["da_doi"] == 0 and len(r["bo_qua"]) == 2                                     # chính mình nhập → bỏ qua
    r = N.hien_hang_loat(db, _u(db, "tp2"), ids, True)
    assert r["da_doi"] == 2 and len(N.danh_sach_cong(db)["nha_hang"]) == 2


def test_noi_dung_marketing(db):
    from app.services import nha_hang as N
    with pytest.raises(N.LoiNhaHang):
        N.luu_noi_dung(db, _u(db, "dh"), {"loai": "mon", "ten": "Phở"})                   # Điều hành không viết nội dung
    with pytest.raises(N.LoiNhaHang, match="loại"):
        N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "x", "ten": "Phở"})
    a = N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "mon", "ten": "Phở", "tom_tat": "Món nước", "hien": True})
    N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "dac_san", "ten": "Nước mắm Phú Quốc", "tinh_thanh": "Phú Quốc", "hien": False})
    assert [x["ten"] for x in N.danh_sach_cong(db)["noi_dung"]] == ["Phở"]
    assert "sua_boi" not in N.danh_sach_cong(db)["noi_dung"][0]
    N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "mon", "ten": "Phở bò", "hien": False}, a.id)
    assert N.danh_sach_cong(db)["noi_dung"] == [] and len(N.ds_noi_dung(db)) == 2
    nh = N.luu_nha_hang(db, _u(db, "dh"), {"ten": "Bếp Mẹ"})
    N.luu_gioi_thieu(db, _u(db, "mkt"), nh.id, "VTD giới thiệu", "Cá kho")
    assert nh.mo_ta == "VTD giới thiệu" and nh.mon_noi_bat == "Cá kho"
    with pytest.raises(N.LoiNhaHang):
        N.luu_gioi_thieu(db, _u(db, "kd"), nh.id, "x", "")


# ── 5 · cửa công khai ───────────────────────────────────────────────────────────────────────────

def test_xem_phai_qua_otp_anh_chi_mo_muc_dang_hien(db):
    """Chủ tịch 28/10/2026: xem trang ẩm thực phải có phiên cổng (OTP Zalo / email, không tạo tài khoản).
    Cửa không phiên chỉ còn ảnh của mục đang hiện; không lộ dữ liệu nội bộ; có phanh."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.api.v1 import am_thuc as AM
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.services import nha_hang as N, cong_ngoai as C
    N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=False)
    nh = sorted(N.danh_sach_vtos(db)["nha_hang"], key=lambda x: x["ten"] != "Phở Hòa")
    N.luu_nha_hang(db, _u(db, "dh"), {"ten": nh[0]["ten"], "tinh_thanh": nh[0]["tinh_thanh"], "ghi_chu_noi_bo": "SĐT chủ 0909"}, nh[0]["id"])
    N.bat_hien(db, _u(db, "tp"), nh[0]["id"], True)
    a1 = N.gan_anh(db, _u(db, "dh"), "nha_hang", nh[0]["id"], "a.png", "image/png", PNG, "VTD chụp")
    a2 = N.gan_anh(db, _u(db, "dh"), "nha_hang", nh[1]["id"], "b.png", "image/png", PNG + b"x", "VTD chụp")
    tk = TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901999999", trang_thai="hoat_dong"); db.add(tk); db.commit()
    phien = {"Authorization": f"Bearer {C.cap_phien(tk)}"}
    app.dependency_overrides[get_db] = lambda: db
    AM._LUOT_ANH.clear()
    try:
        c = TestClient(app)
        assert c.get("/api/v1/cong/dat-ban/nha-hang").status_code == 401                # chưa OTP thì không xem
        assert c.get("/api/v1/am-thuc").status_code in (404, 405)                        # không còn danh sách công khai
        r = c.get("/api/v1/cong/dat-ban/nha-hang", params={"q": "pho hoa"}, headers=phien)
        assert r.status_code == 200 and [x["ten"] for x in r.json()["nha_hang"]] == ["Phở Hòa"]
        assert "0909" not in r.text and "ghi_chu_noi_bo" not in r.text and "hop_dong" not in r.text and "nguon_ref" not in r.text
        assert c.get(f"/api/v1/cong/dat-ban/nha-hang/{nh[1]['id']}", headers=phien).status_code == 404   # chưa bật
        assert c.get(f"/api/v1/cong/dat-ban/nha-hang/{nh[0]['id']}", headers=phien).json()["mo_dat"] is False
        assert c.get(f"/api/v1/am-thuc/anh/{a1}").status_code == 200
        assert c.get(f"/api/v1/am-thuc/anh/{a2}").status_code == 404                    # nhà hàng chưa hiện
        for _ in range(AM.TOI_DA_ANH - 2):
            c.get(f"/api/v1/am-thuc/anh/{a1}")
        assert c.get(f"/api/v1/am-thuc/anh/{a1}").status_code == 429
    finally:
        app.dependency_overrides.pop(get_db, None); AM._LUOT_ANH.clear()


# ── AT-1c · thành phố, ảnh, «ăn ở đâu» ──────────────────────────────────────────────────────────

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def test_thanh_pho_anh_va_an_o_dau(db):
    from app.services import nha_hang as N
    N.nhap_tep(db, _u(db, "dh"), "ds.csv", CSV, "Danh mục thử", thu=False)
    nh = {x["ten"]: x for x in N.danh_sach_vtos(db)["nha_hang"]}
    pho = nh["Phở Hòa"]["id"]
    N.bat_hien(db, _u(db, "tp"), pho, True)
    # ảnh: bắt buộc nguồn, chỉ nhận ảnh, đúng vai
    with pytest.raises(N.LoiNhaHang, match="nguồn"):
        N.gan_anh(db, _u(db, "dh"), "nha_hang", pho, "a.png", "image/png", PNG, "")
    with pytest.raises(N.LoiNhaHang, match="ảnh"):
        N.gan_anh(db, _u(db, "dh"), "nha_hang", pho, "a.pdf", "application/pdf", b"%PDF-1.4 x", "VTD chụp")
    with pytest.raises(N.LoiNhaHang):
        N.gan_anh(db, _u(db, "kd"), "nha_hang", pho, "a.png", "image/png", PNG, "VTD chụp")
    aid = N.gan_anh(db, _u(db, "dh"), "nha_hang", pho, "a.png", "image/png", PNG, "Nhà hàng cấp quyền")
    data, _a = N.anh_cong(db, aid)
    assert data == PNG
    o = N.danh_sach_cong(db)["nha_hang"][0]
    assert o["anh"] == f"/api/v1/am-thuc/anh/{aid}" and o["anh_nguon"] == "Nhà hàng cấp quyền"
    bun = nh["Bún Chả Hương Liên"]["id"]
    aid2 = N.gan_anh(db, _u(db, "mkt"), "nha_hang", bun, "b.png", "image/png", PNG + b"2", "VTD chụp")
    with pytest.raises(N.LoiNhaHang):
        N.anh_cong(db, aid2)                                                          # nhà hàng chưa hiện → không ra ngoài
    # thành phố
    with pytest.raises(N.LoiNhaHang, match="thành phố"):
        N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "thanh_pho", "ten": "Tỉnh Lạ"})
    with pytest.raises(N.LoiNhaHang, match="ảnh"):
        N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "thanh_pho", "ten": "Pleiku", "tom_tat": "Phở khô", "hien": True})
    tp = N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "thanh_pho", "ten": "Pleiku", "tom_tat": "Phở khô"})
    N.gan_anh(db, _u(db, "mkt"), "noi_dung", tp.id, "p.png", "image/png", PNG + b"3", "Unsplash – Tác giả A")
    N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "thanh_pho", "ten": "Pleiku", "tom_tat": "Phở khô", "hien": True}, tp.id)
    ds = N.danh_sach_cong(db)
    tps = {x["ten"]: x for x in ds["thanh_pho"]}
    assert len(tps) == len(N.THANH_PHO) and tps["Pleiku"]["tom_tat"] == "Phở khô" and tps["Pleiku"]["anh"]
    assert tps["TP. Hồ Chí Minh"]["so_nha_hang"] == 1 and tps["Hà Nội"]["so_nha_hang"] == 0
    # món: nhóm hợp lệ, «ăn ở đâu» chỉ nhà hàng đang hiện
    with pytest.raises(N.LoiNhaHang, match="Nhóm"):
        N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "mon", "ten": "Phở", "nhom": "Lạ"})
    N.luu_noi_dung(db, _u(db, "mkt"), {"loai": "mon", "ten": "Phở bò", "ten_khac": "Beef pho", "nhom": "Món nước",
                                       "tinh_thanh": "Hà Nội", "nha_hang_ids": [bun, pho], "hien": True})
    mon = [x for x in N.danh_sach_cong(db)["noi_dung"] if x["loai"] == "mon"][0]
    assert [a["ten"] for a in mon["an_o_dau"]] == ["Phở Hòa"] and mon["ten_khac"] == "Beef pho"
    assert "nha_hang_ids" not in mon and "sua_boi" not in mon


def test_dia_danh_nguon_quy_ve_thanh_pho():
    """29/10/2026: mọi địa danh trên danh mục nguồn đều quy về một thành phố ẩm thực; còn dấu mới phân biệt."""
    from app.services import nha_hang as N
    for nguon, tp in (("HO CHI MINH CITY", "TP. Hồ Chí Minh"), ("HANOI", "Hà Nội"), ("HUẾ", "Huế"), ("HỘI AN", "Hội An"),
                      ("ĐÀ NẴNG", "Đà Nẵng"), ("CẦN THƠ", "Cần Thơ"), ("NHA TRANG", "Nha Trang"), ("ĐÀ LẠT", "Đà Lạt"),
                      ("BUÔN MA THUỘT", "Buôn Ma Thuột"), ("HÀ GIANG", "Hà Giang"), ("PHAN THIẾT", "Phan Thiết – Mũi Né"),
                      ("QUI NHƠN", "Quy Nhơn"), ("QUẢNG NAM PROVINCE", "Hội An"), ("TRÀ VINH", "Trà Vinh"),
                      ("THẠNH XUÂN", "TP. Hồ Chí Minh"), ("MEKONG DELTA", "Cần Thơ"), ("Pleiku", "Pleiku"), ("Dong Hoi", "Đồng Hới")):
        assert N.tinh_tu_nguon(nguon) == tp, nguon
    assert N.tinh_tu_nguon("Thanh Xuân") == "Thanh Xuân"                              # quận Hà Nội: không đoán bừa
    assert N.tinh_tu_nguon("South Central Coast") == "South Central Coast"           # vùng lạ: giữ để Điều hành sửa
