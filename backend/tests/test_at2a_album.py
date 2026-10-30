# -*- coding: utf-8 -*-
"""AT-2a · Album ảnh nhà hàng (Chủ tịch + Điều hành chốt 29/10/2026).

  1. Chỉ Điều hành / Marketing tải; 10 MB/ảnh, 60 ảnh/nhà hàng; chỉ JPG/PNG/WEBP; tải lại đúng tệp cũ không tạo bản trùng.
  2. Máy tạo bản hiển thị + ảnh nhỏ (WEBP, bỏ EXIF), giữ bản gốc; cổng không bao giờ trả bản gốc.
  3. Ảnh mới «Nháp» → «Gửi duyệt» → TP Điều hành duyệt. Người tải / sửa không tự duyệt (trừ Chủ tịch, TGĐ).
     (Chủ tịch 29/10/2026: căn cứ quyền dùng chỉ còn là ghi chú nội bộ — không chặn duyệt, không chặn ra cổng.)
  4. Chỉ ảnh «Đã duyệt» của nhà hàng đang hiện ra cổng. Sửa chữ / căn cứ của ảnh đã duyệt → về «Chờ duyệt».
  5. Ảnh đơn cũ chuyển vào album: ảnh bìa, «Chờ duyệt», «Chưa xác minh» — thôi hiện, không tắt nhà hàng.
"""
from io import BytesIO

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import db, _u  # noqa: F401 — dùng chung fixture


def anh(so: int, kich=(64, 48), exif: bool = False) -> bytes:
    from PIL import Image
    im = Image.new("RGB", kich, ((so * 37) % 256, (so * 91) % 256, (so * 53) % 256))
    o = BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "MayAnhThu"          # hãng máy
        im.save(o, "JPEG", exif=ex)
    else:
        im.save(o, "JPEG")
    return o.getvalue()


def _nh(s, ten="Phở Hòa", hien=True):
    from app.services import nha_hang as N
    nh = N.luu_nha_hang(s, _u(s, "dh"), {"ten": ten, "tinh_thanh": "Hà Nội"})
    if hien:
        N.bat_hien(s, _u(s, "tp"), nh.id, True)
    return nh


def anh_da_duyet(s, nid: int, so: int, credit: str = "", nhom: str = "khong_gian") -> int:
    """Tải (NV ĐH) một ảnh — KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh, tải là hiện; trả id ảnh album."""
    from app.services import nha_hang as N
    x, _m = N.tai_anh_album(s, _u(s, "dh"), nid, f"a{so}.jpg", "image/jpeg", anh(so),
                            {"nhom": nhom, "can_cu": "vtd_chup", "credit": credit, "chu_thich": f"Ảnh {so}"})
    assert x.trang_thai == "da_duyet" and x.duyet_boi == "tu_dong"
    return x.id


def test_tai_gioi_han_va_chong_trung(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    d = {"nhom": "mon_an", "can_cu": "nha_hang", "can_cu_ghi_chu": "Email chị Lan 28/10"}
    with pytest.raises(N.LoiNhaHang):
        N.tai_anh_album(db, _u(db, "kd"), nh.id, "a.jpg", "image/jpeg", anh(1), d)        # Kinh doanh không tải
    with pytest.raises(N.LoiNhaHang, match="JPG"):
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.heic", "image/heic", anh(1), d)
    with pytest.raises(N.LoiNhaHang, match="10 MB"):
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", b"\xff" * (10 * 1024 * 1024 + 1), d)
    with pytest.raises(N.LoiNhaHang, match="nhóm"):
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", anh(1), {**d, "nhom": ""})
    with pytest.raises(N.LoiNhaHang, match="căn cứ"):
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", anh(1), {**d, "can_cu": "google"})
    with pytest.raises(N.LoiNhaHang, match="không mở được"):
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", b"khong phai anh", d)
    x, moi = N.tai_anh_album(db, _u(db, "mkt"), nh.id, "a.jpg", "image/jpeg", anh(1), d)
    assert moi and x.trang_thai == "da_duyet" and x.tai_boi == "mkt"                     # KS-16c: tải là hiện
    y, moi2 = N.tai_anh_album(db, _u(db, "dh"), nh.id, "a-ban-sao.jpg", "image/jpeg", anh(1), d)
    assert not moi2 and y.id == x.id                                                      # cùng nội dung → không trùng
    monkey = N.ANH_TOI_DA_SO
    try:
        N.ANH_TOI_DA_SO = 2
        N.tai_anh_album(db, _u(db, "dh"), nh.id, "b.jpg", "image/jpeg", anh(2), d)
        with pytest.raises(N.LoiNhaHang, match="đủ 2"):
            N.tai_anh_album(db, _u(db, "dh"), nh.id, "c.jpg", "image/jpeg", anh(3), d)
    finally:
        N.ANH_TOI_DA_SO = monkey


def test_ban_hien_thi_nhe_giu_goc_bo_exif(db):
    from PIL import Image
    from app.services import nha_hang as N
    nh = _nh(db)
    goc = anh(5, kich=(3000, 2000), exif=True)
    x, _m = N.tai_anh_album(db, _u(db, "dh"), nh.id, "to.jpg", "image/jpeg", goc, {"nhom": "khong_gian", "can_cu": "vtd_chup"})
    assert (x.rong, x.cao) == (3000, 2000)
    g, _a = N.tep_album(db, _u(db, "mkt"), x.id, "goc")
    assert g == goc                                                                        # bản gốc nguyên vẹn
    h, ah = N.tep_album(db, _u(db, "mkt"), x.id, "hien")
    n, _an = N.tep_album(db, _u(db, "mkt"), x.id, "nho")
    ih, inn = Image.open(BytesIO(h)), Image.open(BytesIO(n))
    assert ah.kieu_noi_dung == "image/webp" and max(ih.size) == 1600 and max(inn.size) == 480
    assert len(h) < len(goc) and not ih.getexif()                                          # nhẹ hơn, không còn EXIF


def test_bo_duyet_anh_nguoi_tai_tu_xoa(db):
    """KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh — tải là hiện; người tải tự xóa, TP Điều hành xóa mọi ảnh."""
    from app.services import nha_hang as N
    from app.models.nha_hang import AnhNhaHang
    nh = _nh(db)
    a, _ = N.tai_anh_album(db, _u(db, "dh"), nh.id, "a.jpg", "image/jpeg", anh(1), {"nhom": "mat_tien", "can_cu": "vtd_chup"})
    b, _ = N.tai_anh_album(db, _u(db, "mkt"), nh.id, "b.jpg", "image/jpeg", anh(2), {"nhom": "mon_an"})
    assert a.trang_thai == b.trang_thai == "da_duyet" and b.can_cu == "chua_xac_minh"
    assert N.anh_cho_duyet(db, _u(db, "tp"))["anh"] == []
    with pytest.raises(N.LoiNhaHang, match="người tải"):
        N.xoa_anh(db, _u(db, "mkt"), a.id)                                                  # không phải người tải
    N.xoa_anh(db, _u(db, "mkt"), b.id)                                                      # người tải tự xóa
    N.xoa_anh(db, _u(db, "tp"), a.id)                                                       # TP ĐH xóa mọi ảnh
    assert db.get(AnhNhaHang, a.id) is None and db.get(AnhNhaHang, b.id) is None


def test_cong_chi_anh_da_duyet(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.api.v1 import am_thuc as AM
    from app.services import nha_hang as N
    nh = _nh(db)
    p1 = anh_da_duyet(db, nh.id, 1, credit="Ảnh: Phở Hòa", nhom="mon_an")
    p2 = anh_da_duyet(db, nh.id, 2, nhom="mat_tien")
    N.dat_bia(db, _u(db, "dh"), p2)
    o = N.mot_nha_hang_cong(db, nh.id)[1]
    assert [x["id"] for x in o["album"]] == [p2, p1] and o["so_anh"] == 2                  # bìa trước
    assert o["anh"] == f"/api/v1/am-thuc/anh/nh/{p2}/hien" and o["album"][1]["credit"] == "Ảnh: Phở Hòa"
    assert "album" not in N.danh_sach_cong(db)["nha_hang"][0]                              # danh sách chỉ ảnh bìa
    app.dependency_overrides[get_db] = lambda: db
    AM._LUOT_ANH.clear()
    try:
        c = TestClient(app)
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p1}/hien").status_code == 200
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p1}/nho").headers["content-type"] == "image/webp"
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p1}/goc").status_code == 404                # bản gốc không ra cổng
        # KS-16c: sửa chú thích không còn phải duyệt lại — ảnh vẫn hiện
        x = N.sua_anh(db, _u(db, "dh"), p1, {"chu_thich": "Bún chả"})
        assert x.trang_thai == "da_duyet"
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p1}/hien").status_code == 200
        assert N.sua_anh(db, _u(db, "dh"), p2, {"nhom": "khong_gian"}).trang_thai == "da_duyet"
        N.an_anh(db, _u(db, "dh"), p2, True)
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p2}/hien").status_code == 404                # ẩn
        assert N.an_anh(db, _u(db, "dh"), p2, False).trang_thai == "da_duyet"            # bỏ ẩn là hiện lại
        p3 = anh_da_duyet(db, nh.id, 3)
        N.bat_hien(db, _u(db, "tp"), nh.id, False)
        assert c.get(f"/api/v1/am-thuc/anh/nh/{p3}/hien").status_code == 404                # nhà hàng tắt
    finally:
        app.dependency_overrides.pop(get_db, None); AM._LUOT_ANH.clear()


def test_thay_anh_va_xep_thu_tu(db):
    from app.services import nha_hang as N
    from app.models.attachments import Attachment
    nh = _nh(db)
    p1 = anh_da_duyet(db, nh.id, 1)
    p2 = anh_da_duyet(db, nh.id, 2)
    with pytest.raises(N.LoiNhaHang, match="trùng"):
        N.thay_anh(db, _u(db, "dh"), p1, "x.jpg", "image/jpeg", anh(2))
    from app.models.nha_hang import AnhNhaHang
    cu = db.get(AnhNhaHang, p1).attachment_id
    x = N.thay_anh(db, _u(db, "dh"), p1, "moi.jpg", "image/jpeg", anh(7))
    assert x.id == p1 and x.trang_thai == "da_duyet" and x.attachment_id != cu and x.chu_thich == "Ảnh 1"
    assert db.get(Attachment, cu) is not None and not db.get(Attachment, cu).thu_hoi           # tệp cũ vẫn trong kho
    with pytest.raises(N.LoiNhaHang, match="không khớp"):
        N.xep_anh(db, _u(db, "dh"), nh.id, [p2])
    N.xep_anh(db, _u(db, "dh"), nh.id, [p2, p1])
    assert [a["id"] for a in N.album(db, _u(db, "dh"), nh.id)["anh"]] == [p2, p1]


def test_hoan_thien_trong_danh_sach(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    _nh(db, "Bún Chả", hien=False)
    p = anh_da_duyet(db, nh.id, 1)
    N.tai_anh_album(db, _u(db, "dh"), nh.id, "b.jpg", "image/jpeg", anh(2), {"nhom": "mon_an", "can_cu": "vtd_chup"})
    N.dat_bia(db, _u(db, "dh"), p)
    ds = {x["ten"]: x["anh_ht"] for x in N.danh_sach_vtos(db)["nha_hang"]}
    assert {k: ds["Phở Hòa"][k] for k in ("da_duyet", "cho_duyet", "nhap", "an", "co_bia")} == \
        {"da_duyet": 2, "cho_duyet": 0, "nhap": 0, "an": 0, "co_bia": True}                  # KS-16c: tải là hiện
    assert ds["Bún Chả"]["da_duyet"] == 0 and N.danh_sach_vtos(db)["so_anh_cho_duyet"] == 0


def test_chuyen_anh_don_cu_khong_tu_duyet(db):
    """Dữ liệu chuyển (mô phỏng câu lệnh của migration): ảnh cũ → bìa, Chờ duyệt, Chưa xác minh; không ra cổng,
    không tắt nhà hàng; TP ĐH không duyệt được cho tới khi có căn cứ."""
    from sqlalchemy import text
    from app.services import nha_hang as N
    from app.services import attachments as AT
    from app.models.nha_hang import NhaHang
    nh = _nh(db)
    a, _ = AT.dinh_kem(db, "am_thuc", f"nh{nh.id}", "cu.jpg", anh(4), kieu="image/jpeg", loai="hinh_anh", boi="dh")
    db.get(NhaHang, nh.id).anh_id, db.get(NhaHang, nh.id).anh_nguon = a.id, "TasteAtlas | ảnh"
    db.commit()
    db.execute(text(
        "INSERT INTO anh_nha_hang (nha_hang_id, attachment_id, hien_id, nho_id, rong, cao, nhom, chu_thich, mo_ta_thay_the, "
        "thu_tu, la_bia, can_cu, can_cu_ghi_chu, credit, trang_thai, ly_do_tra_lai, tai_boi, tai_luc, sua_boi, duyet_boi) "
        "SELECT id, anh_id, anh_id, anh_id, 0, 0, '', '', '', 0, 1, 'chua_xac_minh', "
        "SUBSTR('Chuyển từ ảnh đơn cũ · nguồn ghi: ' || COALESCE(anh_nguon, ''), 1, 300), '', 'cho_duyet', '', "
        "'chuyển dữ liệu', CURRENT_TIMESTAMP, '', '' FROM nha_hang WHERE anh_id IS NOT NULL"))
    db.commit()
    al = N.album(db, _u(db, "tp"), nh.id)["anh"]
    assert len(al) == 1 and al[0]["la_bia"] and al[0]["trang_thai"] == "cho_duyet" and al[0]["can_cu"] == "chua_xac_minh"
    assert "TasteAtlas" in al[0]["can_cu_ghi_chu"] and al[0]["nhom_ten"] == "Chưa phân nhóm"
    o = N.mot_nha_hang_cong(db, nh.id)[1]
    assert o["anh"] is None and o["album"] == []                                           # thôi hiện ảnh
    assert db.get(NhaHang, nh.id).hien_cong                                                # nhà hàng không bị tắt
    with pytest.raises(N.LoiNhaHang):
        N.anh_cong(db, a.id)                                                               # đường ảnh đơn cũ đóng
    assert "nhóm" in N.duyet_anh(db, _u(db, "tp"), [al[0]["id"]], True)["bo_qua"][0]["ly_do"]   # 29/10: chỉ còn chặn vì chưa chọn nhóm
