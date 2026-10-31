# -*- coding: utf-8 -*-
"""KS-16f · Video khách sạn VTD và nhà hàng (Chủ tịch duyệt bản xem thử 31/10/2026).

  1. Tối đa 5 video / cơ sở, mỗi video ≤ 100 MB, MP4 / MOV / WebM; bắt buộc ghi nguồn + xác nhận quyền dùng.
  2. Tải theo từng phần 8 MB (gửi lại một phần = thay), thiếu phần không cho xong; xong là hiện; video đầu = giới thiệu.
  3. Người tải tự xóa; TP Điều hành / CT / TGĐ ẩn – xóa mọi video; người khác không.
  4. Mức chuẩn chỉ nhắc: KS tổng quan · phòng · trải nghiệm; NH không gian · món.
  5. Cổng: chỉ video đang hiện của cơ sở đang hiện; VTOS xem bằng vé ký ngắn hạn. Video phòng gắn vào đúng loại phòng.
"""
import datetime as dt

import pytest

from tests.test_at1_am_thuc import db, _u  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _anh, _ks, _mo_ban

MB = 1024 * 1024


@pytest.fixture()
def kho(tmp_path):
    from app.services import storage as ST
    ST._CACHE["s"] = ST.LocalStorage(str(tmp_path))
    yield ST._CACHE["s"]


def _tai(db, u, doi, oid, mb=10, **d):
    from app.services import video_dich_vu as V
    kt = int(mb * MB)
    v = V.bat_dau(db, u, doi, oid, {"ten_tep": d.pop("ten", "v.mp4"), "kich_thuoc": kt, "thoi_luong": 50, "nguon": "VTD quay",
                                    "xac_nhan_quyen": True, **d})
    con, so = kt, 1
    while con > 0:
        n = min(V.PHAN_BYTE, con)
        V.nhan_phan(db, u, v.id, so, b"x" * n)
        con -= n; so += 1
    return V.xong(db, u, v.id)


def test_tai_len_tung_phan_va_luat(db, kho):
    from app.services import video_dich_vu as V
    k = _ks(db)
    dh, kd, tp = _u(db, "dh"), _u(db, "kd"), _u(db, "tp")
    with pytest.raises(V.LoiVideo, match="quyền"):
        V.bat_dau(db, kd, "khach_san_vtd", k.id, {"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "x", "xac_nhan_quyen": True})
    for d, loi in (({"ten_tep": "a.avi", "kich_thuoc": MB}, "MP4"), ({"ten_tep": "a.mp4", "kich_thuoc": 101 * MB}, "100 MB"),
                   ({"ten_tep": "a.mp4", "kich_thuoc": MB}, "nguồn"), ({"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "KS gửi"}, "Xác nhận")):
        with pytest.raises(V.LoiVideo, match=loi):
            V.bat_dau(db, dh, "khach_san_vtd", k.id, d)
    v = V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "Sanh.MOV", "kich_thuoc": 20 * MB, "nguon": "KS gửi",
                                                 "xac_nhan_quyen": True, "loai": "tong_quan", "thoi_luong": 70})
    assert v.kieu == "video/quicktime" and v.trang_thai == "dang_tai"
    V.nhan_phan(db, dh, v.id, 1, b"a" * V.PHAN_BYTE)
    V.nhan_phan(db, dh, v.id, 3, b"c" * (4 * MB))
    with pytest.raises(V.LoiVideo, match="thiếu phần 2"):
        V.xong(db, dh, v.id)
    with pytest.raises(V.LoiVideo, match="Số phần"):
        V.nhan_phan(db, dh, v.id, 4, b"d")
    V.nhan_phan(db, dh, v.id, 2, b"z" * V.PHAN_BYTE)
    V.nhan_phan(db, dh, v.id, 2, b"b" * V.PHAN_BYTE)                         # gửi lại = thay phần cũ
    V.xong(db, dh, v.id)
    assert v.trang_thai == "hien" and v.la_gioi_thieu and v.kich_thuoc == 20 * MB
    with open(kho.duong_tep(v.khoa_luu), "rb") as f:
        noi = f.read()
    assert noi[:1] == b"a" and noi[V.PHAN_BYTE:V.PHAN_BYTE + 1] == b"b" and noi[-1:] == b"c"
    # mức chuẩn chỉ nhắc
    o = V.ds(db, dh, "khach_san_vtd", k.id)
    assert [c["co"] for c in o["chuan"]] == [True, False, False] and not o["du_chuan"]
    for i in range(4):
        _tai(db, dh, "khach_san_vtd", k.id, 1, loai="trai_nghiem")
    with pytest.raises(V.LoiVideo, match="đủ 5"):
        V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "x", "xac_nhan_quyen": True})
    # người khác không xóa được; người tải xóa được; TP Điều hành xóa mọi video
    ds_ = V._cua(db, "khach_san_vtd", k.id)
    with pytest.raises(V.LoiVideo, match="Chỉ người tải"):
        V.xoa(db, _u(db, "mkt"), ds_[1].id)
    V.xoa(db, dh, ds_[1].id)
    V.xoa(db, tp, v.id)                                                      # xóa video giới thiệu → video khác lên thay
    con = V._cua(db, "khach_san_vtd", k.id)
    assert len(con) == 3 and sum(x.la_gioi_thieu for x in con) == 1
    V.dat_gioi_thieu(db, dh, con[-1].id)
    assert V._cua(db, "khach_san_vtd", k.id)[0].id == con[-1].id
    V.huy(db, dh, V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "b.webm", "kich_thuoc": MB, "nguon": "x",
                                                           "xac_nhan_quyen": True}).id)
    assert len(V._cua(db, "khach_san_vtd", k.id)) == 3


def test_cong_chi_video_dang_hien_va_gan_loai_phong(db, kho):
    from app.services import khach_san_vtd as S
    from app.services import video_dich_vu as V
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)
    dh = _u(db, "dh")
    with pytest.raises(V.LoiVideo, match="Loại phòng"):
        V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "x", "xac_nhan_quyen": True,
                                                 "loai": "phong", "loai_phong_id": 9999})
    v1 = _tai(db, dh, "khach_san_vtd", k.id, 1, loai="tong_quan", tieu_de="Toàn cảnh")
    v2 = _tai(db, dh, "khach_san_vtd", k.id, 1, loai="phong", loai_phong_id=lp.id)
    v3 = _tai(db, dh, "khach_san_vtd", k.id, 1, loai="trai_nghiem")
    V.an(db, dh, v3.id, True)
    V.anh_dai_dien(db, dh, v1.id, "f.jpg", _anh())
    ct = S.chi_tiet_cong(db, k.id, VAO, RA, 2, 0, 1, hom_nay=HN)
    assert ct["so_video"] == 2 and [x["id"] for x in ct["video"]] == [v1.id, v2.id]
    assert ct["video"][0]["la_gioi_thieu"] and ct["video"][0]["anh"] == f"/api/v1/ks-vtd-anh/video/{v1.id}/anh"
    assert "?t=" not in ct["video"][0]["xem"] and "nguon" not in ct["video"][0]
    assert [x["id"] for x in ct["phong"][0]["video"]] == [v2.id]
    # đường xem: cổng chỉ video đang hiện của KS đang hiện; video ẩn chỉ xem bằng vé VTOS
    assert V.tep_xem(db, v1.id, "khach_san_vtd")["duong"].endswith(".mp4")
    with pytest.raises(V.LoiVideo):
        V.tep_xem(db, v3.id, "khach_san_vtd")
    with pytest.raises(V.LoiVideo):
        V.tep_xem(db, v1.id, "nha_hang")
    noi = V.ds(db, dh, "khach_san_vtd", k.id)["video"]
    t = [x for x in noi if x["id"] == v3.id][0]["xem"].split("?t=")[1]
    assert V.tep_xem(db, v3.id, "khach_san_vtd", t)
    assert not V.ve_hop_le(v3.id, t, now=__import__("time").time() + V.HAN_LINK + 5) and not V.ve_hop_le(v1.id, t)
    data, a = V.tep_anh(db, v1.id, "khach_san_vtd")
    assert a.kieu_noi_dung == "image/webp" and data
    S.bat_hien(db, _u(db, "tp"), k.id, False)
    with pytest.raises(V.LoiVideo):
        V.tep_xem(db, v1.id, "khach_san_vtd")


def test_nha_hang_va_kho_s3_chuyen_huong(db, kho, monkeypatch):
    from tests.test_at2a_album import _nh
    from app.services import nha_hang as N
    from app.services import video_dich_vu as V
    nh = _nh(db)
    mkt = _u(db, "mkt")                                                     # Marketing tải được video nhà hàng như ảnh
    v = _tai(db, mkt, "nha_hang", nh.id, 1, loai="khong_gian")
    o = V.ds(db, _u(db, "tp"), "nha_hang", nh.id)
    assert [c["loai"] for c in o["chuan"]] == ["khong_gian", "mon"] and o["chuan"][0]["co"]
    with pytest.raises(V.LoiVideo, match="loại nội dung"):
        V.bat_dau(db, mkt, "nha_hang", nh.id, {"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "x", "xac_nhan_quyen": True,
                                              "loai": "phong"})
    _n, ct = N.mot_nha_hang_cong(db, nh.id)
    assert ct["so_video"] == 1 and ct["video"][0]["xem"] == f"/api/v1/am-thuc/video/{v.id}/xem"
    monkeypatch.setattr(kho, "link_tam", lambda key, giay=3600, kieu="": f"https://r2.example/{key}?sig=1")
    assert V.tep_xem(db, v.id, "nha_hang")["url"].startswith("https://r2.example/video/nha_hang/")


def test_duong_api_nam_trong_nhom_san_co():
    import app.main as m
    p = {r.path for r in m.app.routes}
    for x in ("/api/v1/khach-san-vtd/{kid:int}/video", "/api/v1/khach-san-vtd/video/{vid:int}/phan/{so:int}",
              "/api/v1/nha-hang/{nid:int}/video/bat-dau", "/api/v1/ks-vtd-anh/video/{vid:int}/xem",
              "/api/v1/am-thuc/video/{vid:int}/xem"):
        assert x in p
