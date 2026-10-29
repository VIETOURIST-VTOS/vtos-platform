# -*- coding: utf-8 -*-
"""AT-3 · Đánh giá sao nhà hàng (Chủ tịch duyệt bản xem thử 29/10/2026).

  1. Chỉ NGƯỜI ĐẶT của đơn nhà hàng đã báo «khách đã dùng»; một bài / đơn; 30 ngày sau bữa ăn; sửa trong 7 ngày.
  2. Hiện ngay; tên che; dưới 3 bài không hiện điểm trung bình.
  3. Chỉ Marketing ẩn vì vi phạm (4 lý do, phải ghi); TP Điều hành xem lại; người ẩn không tự xem lại.
  4. Nhà hàng trả lời một lần, sửa trong 24 giờ; nhà hàng khác không thấy.
  5. Mức hoàn thiện thêm «Đánh giá khách» 10 điểm — chấm theo SỐ bài, không theo số sao; tổng vẫn 100.
"""
import datetime as dt
import io

import pytest

from tests.test_dt2_dat_ban import db, _u, _tk, _dat, _nhan, _tra_qr, _ncc  # noqa: F401


def _anh(i=1):
    from PIL import Image
    im = Image.new("RGB", (900, 600), (40 * i % 255, 90, 120))
    b = io.BytesIO(); im.save(b, "JPEG", quality=80)
    return b.getvalue()


def _them_vai(s):
    from app.models.core import User
    for ten, vai in (("mkt", "nv_mkt"), ("tpdh", "tp_dh")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()


def _da_dung(s, tk="0901000001", sid="A"):
    from app.models.cong_khach import YeuCauKhach
    from app.services import dat_ban as S
    d = _nhan(s, _dat(s, tk=tk, nl=2, cach="du"))
    _tra_qr(s, d, sid=sid)
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(s, _tk(s, "0901000004"), _ncc(s), s.get(YeuCauKhach, d.yeu_cau_id).id, 900000, 0, "", now=ve)
    s.commit()
    return d, ve


def test_1_chi_nguoi_dat_don_da_dung(db):
    from app.services import danh_gia_nh as DG
    from app.services import dat_ban as S
    d = _nhan(db, _dat(db, nl=2, cach="du"))
    with pytest.raises(DG.LoiDanhGia, match="đã đến dùng"):
        DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 5, "dong_y": True})
    _tra_qr(db, d, sid="X")
    from app.models.cong_khach import YeuCauKhach
    ve = S.gio_an(d) + dt.timedelta(hours=2)
    S.ncc_da_dung(db, _tk(db, "0901000004"), _ncc(db), db.get(YeuCauKhach, d.yeu_cau_id).id, 900000, 0, "", now=ve)
    db.commit()
    with pytest.raises(DG.LoiDanhGia, match="tài khoản của bạn"):
        DG.viet(db, _tk(db, "0901000002"), d.ma, {"diem": 5, "dong_y": True}, now=ve)        # người khác
    with pytest.raises(DG.LoiDanhGia, match="đồng ý"):
        DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 5}, now=ve)
    with pytest.raises(DG.LoiDanhGia, match="1 đến 5"):
        DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 0, "dong_y": True}, now=ve)
    tt = DG.trang_thai_don(db, d, ve)
    assert tt["duoc_viet"] and tt["bai"] is None
    g = DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 4, "diem_mon": 5, "diem_gia": "", "nhan_xet": " Ngon ", "dong_y": True},
                [("a.jpg", _anh())], now=ve)
    assert g.ten_hien == "Khách A***" and g.diem_gia is None and g.nhan_xet == "Ngon" and len(g.anh) == 1
    # sửa trong 7 ngày: thay hẳn, giữ ảnh cũ theo chỉ số
    g = DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 2, "nhan_xet": "Đổi ý", "dong_y": True}, [("b.png", _anh(2))], [0],
                now=ve + dt.timedelta(days=6))
    assert g.diem == 2 and g.sua_luc is not None and len(g.anh) == 2
    with pytest.raises(DG.LoiDanhGia, match="7 ngày"):
        DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 5, "dong_y": True}, now=ve + dt.timedelta(days=8))
    with pytest.raises(DG.LoiDanhGia, match="Tối đa 3"):
        DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 5, "dong_y": True}, [("c.jpg", _anh(3))] * 2, [0, 1], now=ve)
    # quá 30 ngày → đóng
    d2, ve2 = _da_dung(db, sid="B")
    with pytest.raises(DG.LoiDanhGia, match="30 ngày"):
        DG.viet(db, _tk(db, "0901000001"), d2.ma, {"diem": 5, "dong_y": True}, now=dt.datetime.combine(d2.ngay, dt.time()) + dt.timedelta(days=32))
    assert not DG.trang_thai_don(db, d2, dt.datetime.combine(d2.ngay, dt.time()) + dt.timedelta(days=32))["duoc_viet"]
    # danh sách «Đơn của tôi» mang trạng thái đánh giá
    assert "danh_gia" in S.ds_cua(db, _tk(db, "0901000001"), ve)[0]


def test_2_hien_ngay_ten_che_duoi_3_bai_khong_diem(db):
    from app.services import danh_gia_nh as DG
    nid = None
    for i, sdt in enumerate(("0901000001", "0901000002", "0901000001")):
        d, ve = _da_dung(db, tk=sdt, sid=f"S{i}")
        DG.viet(db, _tk(db, sdt), d.ma, {"diem": (5, 4, 2)[i], "diem_mon": 5, "dong_y": True}, now=ve)
        nid = d.nha_hang_id
        t = DG.tom_tat(db, [nid])[nid]
        assert t["so_bai"] == i + 1 and (t["diem_tb"] is None) == (i < 2)
    c = DG.cong(db, nid)
    assert c["tom_tat"]["diem_tb"] == 3.7 and c["tom_tat"]["muc"]["diem_mon"] == 5.0 and c["tom_tat"]["muc"]["diem_gia"] is None
    assert [b["diem"] for b in DG.cong(db, nid, xep="thap")["bai"]] == [2, 4, 5]
    assert all("dien_thoai" not in b and "don_id" not in b and "an_boi" not in b for b in c["bai"])


def test_3_chi_marketing_an_vi_pham_tp_dh_xem_lai(db):
    from app.services import danh_gia_nh as DG
    _them_vai(db)
    d, ve = _da_dung(db)
    g = DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 1, "nhan_xet": "Gọi 0909xxx", "dong_y": True}, [("a.jpg", _anh())], now=ve)
    with pytest.raises(DG.LoiDanhGia, match="Marketing"):
        DG.an(db, _u(db, "tpdh"), g.id, "chui_boi", "xúc phạm nhân viên")
    with pytest.raises(DG.LoiDanhGia, match="lý do vi phạm"):
        DG.an(db, _u(db, "mkt"), g.id, "che", "khách chê món")                # chê không phải vi phạm
    with pytest.raises(DG.LoiDanhGia, match="Ghi thêm"):
        DG.an(db, _u(db, "mkt"), g.id, "thong_tin_ca_nhan", "")
    data, _a = DG.tep_anh(db, g.id, 0, "nho")
    assert data[:4] == b"RIFF"                                                # bản làm nhẹ WEBP, không bản gốc
    DG.an(db, _u(db, "mkt"), g.id, "anh_sai", "ảnh chụp hóa đơn", phan="anh:0")
    with pytest.raises(DG.LoiDanhGia):
        DG.tep_anh(db, g.id, 0, "hien")
    assert DG.cong(db, d.nha_hang_id)["tong"] == 1                            # ẩn ảnh: bài vẫn hiện
    DG.an(db, _u(db, "mkt"), g.id, "thong_tin_ca_nhan", "có số điện thoại")
    assert DG.cong(db, d.nha_hang_id)["tong"] == 0
    assert DG.ds_noi_bo(db, _u(db, "mkt"))["dem"]["cho_xem_lai"] == 1
    with pytest.raises(DG.LoiDanhGia, match="TP Điều hành"):
        DG.xem_lai(db, _u(db, "mkt"), g.id, False)
    DG.xem_lai(db, _u(db, "tpdh"), g.id, False)
    db.refresh(g)
    assert not g.an and not g.anh[0]["an"] and g.xem_lai == "hien" and DG.cong(db, d.nha_hang_id)["tong"] == 1
    assert DG.xuat_xlsx(db, _u(db, "tpdh"))[:2] == b"PK"


def test_4_nha_hang_tra_loi_mot_lan(db):
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.suppliers import Supplier
    from app.services import danh_gia_nh as DG
    d, ve = _da_dung(db)
    g = DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 2, "dong_y": True}, now=ve)
    tkn, ncc = _tk(db, "0901000004"), _ncc(db)
    l = DG.ds_ncc(db, ncc)
    assert l["bai"][0]["duoc_tra_loi"] and l["nha_hang"][0]["so_bai"] == 1
    t0 = dt.datetime.now()
    DG.tra_loi(db, tkn, ncc, g.id, "Cảm ơn anh chị", now=t0)
    DG.tra_loi(db, tkn, ncc, g.id, "Cảm ơn anh chị đã góp ý", now=t0 + dt.timedelta(hours=2))      # sửa trong 24 giờ
    with pytest.raises(DG.LoiDanhGia, match="24 giờ"):
        DG.tra_loi(db, tkn, ncc, g.id, "Lần nữa", now=t0 + dt.timedelta(hours=25))
    assert DG.cong(db, d.nha_hang_id)["bai"][0]["tra_loi"] == "Cảm ơn anh chị đã góp ý"
    khac = Supplier(code="NCC0099", ten="NCC khác", loai="nha_hang"); db.add(khac); db.flush()
    db.add(TaiKhoanNgoai(loai="doi_tac", loai_doi_tac="ncc", dien_thoai="0901000099", trang_thai="hoat_dong", ncc_id=khac.id)); db.commit()
    with pytest.raises(DG.LoiDanhGia, match="Không có"):
        DG.tra_loi(db, _tk(db, "0901000099"), khac, g.id, "Chen vào")
    assert DG.ds_ncc(db, khac)["bai"] == []


def test_5_muc_hoan_thien_them_danh_gia(db):
    from app.services import danh_gia_nh as DG
    from app.services import nha_hang as N
    assert sum(w for _m, _t, w, _tab in N.MUC_HT) == 100
    assert {m: w for m, _t, w, _tab in N.MUC_HT}["danh_gia"] == 10
    d, ve = _da_dung(db)
    nid = d.nha_hang_id
    truoc = {m["ma"]: m for m in N.diem_hoan_thien(db, [nid])[nid]["muc"]}["danh_gia"]
    DG.viet(db, _tk(db, "0901000001"), d.ma, {"diem": 1, "dong_y": True}, now=ve)        # 1 sao vẫn tính bài
    sau = {m["ma"]: m for m in N.diem_hoan_thien(db, [nid])[nid]["muc"]}["danh_gia"]
    assert truoc["diem"] == 0 and round(sau["diem"], 1) == 3.3 and not sau["dat"]
