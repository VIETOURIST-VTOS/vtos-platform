# -*- coding: utf-8 -*-
"""AT-2b · Món ăn và thực đơn nhà hàng (Chủ tịch chốt 29/10/2026).

  1. Món KHÔNG có giá. Tối đa 40 món, 6 món ★. Dị ứng chỉ trong 7 loại. Ảnh món = ảnh trong album của chính
     nhà hàng; cổng chỉ hiện ảnh đã duyệt. Nháp → gửi duyệt → TP ĐH duyệt, người thêm / sửa không tự duyệt.
     Sửa chữ / dị ứng / ảnh của món đã duyệt → «Chờ duyệt».
  2. Thực đơn 4 loại (gọi món, set menu, buffet, khách đoàn), mỗi lần tải là một phiên bản mới (v1.0, v1.1…), bản cũ
     giữ. Ảnh nhiều trang hoặc một PDF (máy tách trang). Căn cứ bắt buộc. Bản đang dùng = bản đã duyệt mới nhất đã
     tới ngày hiệu lực. Cổng chỉ trang của bản đang dùng; không bao giờ tệp gốc.
"""
import datetime as dt
from io import BytesIO

import pytest

from tests.test_at1_am_thuc import db, _u, HN  # noqa: F401
from tests.test_at2a_album import anh, anh_da_duyet, _nh


def _pdf(so_trang: int) -> bytes:
    from PIL import Image
    ims = [Image.new("RGB", (600, 800), (250, 245, 230 - i * 20)) for i in range(so_trang)]
    o = BytesIO()
    ims[0].save(o, "PDF", save_all=True, append_images=ims[1:])
    return o.getvalue()


def test_mon_khong_gia_gioi_han_va_duyet(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    with pytest.raises(N.LoiNhaHang):
        N.luu_mon(db, _u(db, "kd"), nh.id, {"ten": "Phở"})                                      # Kinh doanh không sửa
    with pytest.raises(N.LoiNhaHang, match="dị ứng"):
        N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Phở", "di_ung": ["mè"]})
    m = N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Chả giò", "nhom": "khai_vi", "di_ung": ["gluten", "trung"], "gia": 99})
    assert m.trang_thai == "nhap" and not hasattr(m, "gia")
    assert "gia" not in N.ds_mon(db, _u(db, "mkt"), nh.id)["mon"][0]
    assert N.mon_cong(db, nh.id) == []                                                           # nháp chưa ra cổng
    assert N.gui_duyet_mon(db, _u(db, "dh"), nh.id) == 1
    r = N.duyet_mon(db, _u(db, "tp"), [m.id], True)
    assert r["da_doi"] == 1
    c = N.mon_cong(db, nh.id)
    assert c[0]["ten"] == "Chả giò" and c[0]["di_ung_ten"] == ["Gluten", "Trứng"] and "gia" not in c[0] and "tao_boi" not in c[0]
    # sửa mô tả món đã duyệt → về chờ duyệt, thôi hiện; đổi nhóm thì không
    assert N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Chả giò", "nhom": "mon_chinh", "di_ung": ["gluten", "trung"]}, m.id).trang_thai == "da_duyet"
    assert N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Chả giò", "nhom": "mon_chinh", "mo_ta": "Mới", "di_ung": ["gluten", "trung"]}, m.id).trang_thai == "cho_duyet"
    assert N.mon_cong(db, nh.id) == []
    r = N.duyet_mon(db, _u(db, "tp2"), [m.id], True)
    assert r["da_doi"] == 1
    # tự duyệt bị chặn
    m2 = N.luu_mon(db, _u(db, "tp"), nh.id, {"ten": "Cá kho"})
    N.gui_duyet_mon(db, _u(db, "tp"), nh.id)
    assert "không tự duyệt" in N.duyet_mon(db, _u(db, "tp"), [m2.id], True)["bo_qua"][0]["ly_do"]
    with pytest.raises(N.LoiNhaHang, match="lý do"):
        N.duyet_mon(db, _u(db, "tp2"), [m2.id], False)
    # giới hạn
    old = N.MON_TOI_DA
    try:
        N.MON_TOI_DA = 2
        with pytest.raises(N.LoiNhaHang, match="đủ 2"):
            N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Thêm"})
    finally:
        N.MON_TOI_DA = old


def test_noi_bat_toi_da_va_anh_mon(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    khac = _nh(db, "Quán Khác")
    p_khac = anh_da_duyet(db, khac.id, 9)
    with pytest.raises(N.LoiNhaHang, match="album của chính"):
        N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "X", "anh_id": p_khac})
    nhap, _ = N.tai_anh_album(db, _u(db, "dh"), nh.id, "m.jpg", "image/jpeg", anh(3), {"nhom": "mon_an", "can_cu": "vtd_chup"})
    m = N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Bún chả", "anh_id": nhap.id})
    N.gui_duyet_mon(db, _u(db, "dh"), nh.id); N.duyet_mon(db, _u(db, "tp"), [m.id], True)
    assert N.mon_cong(db, nh.id)[0]["anh"] == f"/api/v1/am-thuc/anh/nh/{nhap.id}/hien"
    ids = [N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": f"M{i}"}).id for i in range(6)]
    for i in ids:
        N.mon_noi_bat(db, _u(db, "dh"), i, True)
    with pytest.raises(N.LoiNhaHang, match="Tối đa 6"):
        N.mon_noi_bat(db, _u(db, "dh"), m.id, True)
    N.an_mon(db, _u(db, "dh"), ids[0], True)
    N.mon_noi_bat(db, _u(db, "dh"), m.id, True)                                                 # ẩn món ★ → trả chỗ
    assert N.ds_mon(db, _u(db, "dh"), nh.id)["mon"][0]["noi_bat"]


def test_thuc_don_phien_ban_va_hien_hanh(db, monkeypatch):
    from app.services import nha_hang as N
    from app.models.attachments import Attachment
    nh = _nh(db)
    with pytest.raises(N.LoiNhaHang, match="căn cứ"):
        N.tai_thuc_don(db, _u(db, "dh"), nh.id, "goi_mon", [("a.jpg", anh(1))], None, "")
    with pytest.raises(N.LoiNhaHang, match="loại"):
        N.tai_thuc_don(db, _u(db, "dh"), nh.id, "do_uong", [("a.jpg", anh(1))], None, "Email chị Lan 28/10")
    with pytest.raises(N.LoiNhaHang, match="PDF hoặc ảnh"):
        N.tai_thuc_don(db, _u(db, "dh"), nh.id, "goi_mon", [("a.docx", b"x")], None, "Email chị Lan 28/10")
    b1 = N.tai_thuc_don(db, _u(db, "dh"), nh.id, "goi_mon", [("t1.jpg", anh(1)), ("t2.jpg", anh(2))], "2026-10-28", "Zalo quản lý 28/10")
    assert (b1.so, b1.so_trang, b1.trang_thai) == (1, 2, "cho_duyet")
    assert N.thuc_don_cong(db, nh.id) == []
    with pytest.raises(N.LoiNhaHang):
        N.duyet_thuc_don(db, _u(db, "dh"), b1.id, True)                                         # NV ĐH không duyệt
    N.duyet_thuc_don(db, _u(db, "tp"), b1.id, True)
    c = N.thuc_don_cong(db, nh.id)
    assert c[0]["loai"] == "goi_mon" and c[0]["ban"] == "v1.0" and len(c[0]["trang"]) == 2
    # bản PDF mới, hiệu lực tương lai → v1.0 vẫn đang dùng tới ngày hiệu lực
    b2 = N.tai_thuc_don(db, _u(db, "dh"), nh.id, "goi_mon", [("menu.pdf", _pdf(3))], (HN + dt.timedelta(days=3)).isoformat(), "Email 29/10")
    assert (b2.so, b2.so_trang) == (2, 3)
    N.duyet_thuc_don(db, _u(db, "tp"), b2.id, True)
    td = N.ds_thuc_don(db, _u(db, "mkt"), nh.id)["loai"]["goi_mon"]
    assert {x["ten"]: x["trang_thai"] for x in td["ban"]} == {"v1.1": "cho_hieu_luc", "v1.0": "dang_dung"}
    monkeypatch.setattr(N, "_hom_nay", lambda: HN + dt.timedelta(days=3))
    td = N.ds_thuc_don(db, _u(db, "mkt"), nh.id)["loai"]["goi_mon"]
    assert {x["ten"]: x["trang_thai"] for x in td["ban"]} == {"v1.1": "dang_dung", "v1.0": "da_thay"}
    c = N.thuc_don_cong(db, nh.id)
    assert c[0]["ban"] == "v1.1" and len(c[0]["trang"]) == 3
    # cổng: trang bản cũ 404, trang bản đang dùng có; không bao giờ gốc
    t_cu = td["ban"][1]["trang"][0]["id"]
    t_moi = td["ban"][0]["trang"][0]["id"]
    with pytest.raises(N.LoiNhaHang):
        N.tep_trang(db, None, t_cu, "hien")
    data, a = N.tep_trang(db, None, t_moi, "hien")
    assert a.kieu_noi_dung == "image/webp" and data[:4] == b"RIFF"
    with pytest.raises(N.LoiNhaHang):
        N.tep_trang(db, None, t_moi, "goc")
    g, ag = N.tep_trang(db, _u(db, "mkt"), t_moi, "goc")
    assert ag.kieu_noi_dung == "application/pdf" and g[:4] == b"%PDF"
    assert db.get(Attachment, ag.id) is not None
    # trả lại cần lý do; PDF quá trang bị từ chối
    b3 = N.tai_thuc_don(db, _u(db, "dh"), nh.id, "buffet", [("b.jpg", anh(4))], None, "Email 29/10")
    with pytest.raises(N.LoiNhaHang, match="lý do"):
        N.duyet_thuc_don(db, _u(db, "tp"), b3.id, False)
    assert N.duyet_thuc_don(db, _u(db, "tp"), b3.id, False, "Ảnh mờ").trang_thai == "tra_lai"
    old = N.TD_TOI_DA_TRANG
    try:
        N.TD_TOI_DA_TRANG = 2
        with pytest.raises(N.LoiNhaHang, match="quá 2 trang"):
            N.tai_thuc_don(db, _u(db, "dh"), nh.id, "set_menu", [("m.pdf", _pdf(3))], None, "Email 29/10")
    finally:
        N.TD_TOI_DA_TRANG = old


def test_tu_duyet_thuc_don_bi_chan_va_cong_chi_tiet(db):
    from app.services import nha_hang as N
    nh = _nh(db)
    b = N.tai_thuc_don(db, _u(db, "tp"), nh.id, "set_menu", [("s.jpg", anh(5))], None, "Email 29/10")
    with pytest.raises(N.LoiNhaHang, match="không tự duyệt"):
        N.duyet_thuc_don(db, _u(db, "tp"), b.id, True)
    N.duyet_thuc_don(db, _u(db, "tp2"), b.id, True)
    m = N.luu_mon(db, _u(db, "dh"), nh.id, {"ten": "Gỏi cuốn", "nhom": "khai_vi"})
    N.gui_duyet_mon(db, _u(db, "dh"), nh.id); N.duyet_mon(db, _u(db, "tp"), [m.id], True)
    o = N.mot_nha_hang_cong(db, nh.id)[1]
    assert [x["ten"] for x in o["mon"]] == ["Gỏi cuốn"] and o["thuc_don_nh"][0]["loai"] == "set_menu"
    assert "mon" not in N.danh_sach_cong(db)["nha_hang"][0]                                    # danh sách không chở món
    cd = N.cho_duyet_noi_dung(db, _u(db, "mkt"))
    assert cd["mon"] == [] and cd["thuc_don"] == [] and cd["duoc_duyet"] is False
    ht = {x["ten"]: x["anh_ht"] for x in N.danh_sach_vtos(db)["nha_hang"]}["Phở Hòa"]
    assert ht["mon"] == 1 and ht["td"] == 1
