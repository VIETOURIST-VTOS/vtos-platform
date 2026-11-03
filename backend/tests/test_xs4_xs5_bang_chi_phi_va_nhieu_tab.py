# -*- coding: utf-8 -*-
"""XS-4 + XS-5 (03/11/2026) — hai chỗ làm màn Chủ tịch nói sai về đội xe.

Cả hai đo trên hệ thật sáng 03/11/2026, màn «Hiệu quả đội xe» của Chủ tịch:

  · «11 dòng sửa» — mà MƯỜI trong mười một là khối chi phí tháng dán dưới bảng chuyến
    (B.DƯỠNG T10, BÃI XE THÁNG 10, SIM DATA, CAMERA, BẢO HIỂM, THAY VỎ XE, CHI PHÍ LÃI VAY).
    Dòng thứ mười một — km đứt mạch 360 km của xe 50H-938.27 — là cảnh báo THẬT, và nó đang
    nằm lẫn giữa mười cái giả.

  · «Xe đang đi · hôm nay 0 / 11 xe» — trong khi có hai xe trên đường (Hòn Cò 02→04/11,
    Đà Lạt 01→03/11). Hai chuyến ấy nằm ở tab «QT tháng 11 2026», còn link CSV chỉ xuất
    được MỘT tab.

Khuôn CSV dưới đây chép đúng khuôn sheet thật, kể cả chỗ hàng tiêu đề của bảng chi phí
(«XE | SỐ TIỀN | HD SỐ») rơi trúng ba cột Ngày đi / Ngày về / Số ngày.
"""
import datetime as dt

from app.services import xe_theo_sheet as XS

DAU = (',,,,Màu vàng: chi phí hoàn cho lái xe,,,,,,\n'
       'XE SỐ,SỐ,Lái xe,Tên tour,Ngày đi,Ngày về,Số ngày,CTP,"Gửi xe +\nphí khác",Dầu,EPASS,D. Thu,'
       'Tổng Chi,Lợi nhuận,Km đầu,Km cuối,Tổng km ,SL lít,"Tiêu Hao\n100km",NOTE\n')

# Tab CŨ: hai chuyến đã xong, rồi khối chi phí tháng dán nối xuống.
TAB_CU = DAU + (
    'XE 1,01783,TÚ\n'
    ',50F01783,TÚ,Phan Thiết,28/10/2026,30/10/2026,3,600000,25000,4762770,858986,9600000,'
    '6246756,3353244,243244,243730,486,150,"30,8"\n'
    'XE 2,02259,HỒ\n'
    ',50F02259,HỒ,Phan Thiết,29/10/2026,31/10/2026,3,600000,25000,3997710,858986,8000000,'
    '5481696,2518304,256280,256716,436,126,"28,9"\n'
    'XE 11,94458,LONG\n'
    'B.DƯỠNG T10,,,B.DƯỠNG T10,XE,SỐ TIỀN,HD SỐ\n'
    ',,,,50F 01737,6891048,6267- VIỆT NHÂN\n'
    ',,,BÃI XE THÁNG 10,VIETRIP,2160000,50H49829- HD 4924\n'
    ',,,SIM DATA,50F01783,1600000,VIETEL 3271475\n'
    ',,,THAY VỎ XE,50H49829,30800000,9967\n'
    ',,,CHI PHÍ LÃI VAY,,,\n'
)

# Tab MỚI của tháng 11: chuyến ĐANG CHẠY nằm ở đây, và chưa có tiền vì chưa quyết toán.
TAB_MOI = DAU + (
    'XE 1,01783,TÚ\n'
    ',50F01783,TÚ,Mỹ Tho 1day,01/11/2026,01/11/2026,1,200000,30000,1593390,0,4000000,'
    '1823390,2176610,243730,243893,163,50,"30,7"\n'
    'XE 2,02259,HỒ\n'
    ',50F02259,HỒ,Hòn Cò,02/11/2026,04/11/2026,3,600000,,,,,600000,-600000,,,0,,#DIV/0!\n'
)

XE_VTOS = {XS.nam_so_cuoi(p): p for p in ("50F01783", "50F02259", "50H94458")}
HOM_NAY = dt.date(2026, 11, 3)


# ── XS-4 ─────────────────────────────────────────────────────────────────────────────────────

def test_khoi_chi_phi_thang_khong_thanh_chuyen_va_khong_thanh_canh_bao():
    """Năm dòng chi phí tháng: không dòng nào là chuyến, không dòng nào vào «cần sửa»."""
    b = XS.doc_bang(TAB_CU)
    assert b["loi"] is None
    assert len(b["chuyen"]) == 2, "chỉ hai chuyến thật; khối chi phí tháng không phải chuyến"
    assert [t["tour"] for t in b["chuyen"]] == ["Phan Thiết", "Phan Thiết"]
    gia = [c for c in b["can_sua"]
           if c["loai"] == "thieu_ngay" and c.get("tour") in
           ("B.DƯỠNG T10", "BÃI XE THÁNG 10", "SIM DATA", "THAY VỎ XE", "CHI PHÍ LÃI VAY")]
    assert gia == [], f"khối chi phí tháng vẫn bị báo là chuyến thiếu ngày: {gia}"
    # Và khối «XE 11» không đếm được chuyến nào từ bảng chi phí ấy.
    xe11 = [k for k in b["khoi"] if k["khoi"] == "XE 11"][0]
    assert xe11["so_chuyen"] == 0


def test_chuyen_go_sai_ngay_ma_CO_tien_thi_van_bao():
    """Chỉ im lặng ở chỗ không có gì để mất — còn tiền hoặc km thì vẫn phải báo."""
    bang = DAU + ('XE 1,01783,TÚ\n'
                  ',50F01783,TÚ,Đà Lạt,31/9/2026,,3,600000,,5000000,,10000000,,,,,,,\n')
    b = XS.doc_bang(bang)
    assert len(b["chuyen"]) == 1
    assert [c["loai"] for c in b["can_sua"] if c["loai"] == "thieu_ngay"] == ["thieu_ngay"]


# ── XS-5 ─────────────────────────────────────────────────────────────────────────────────────

def test_mot_tab_thi_khong_thay_xe_dang_di():
    """Đúng cái màn Chủ tịch đang hiện: đọc một tab thì «đang đi» ra 0 — và 0 ấy sai."""
    b = XS.doc_bang(TAB_CU)
    assert XS.hom_nay(b, HOM_NAY, XE_VTOS)["dang_di"] == 0


def test_gop_hai_tab_thi_dem_dung_xe_dang_di():
    bs = [XS.doc_bang(TAB_CU, kiem_chuoi=False), XS.doc_bang(TAB_MOI, kiem_chuoi=False)]
    b = XS.gop_bang(bs)
    hn = XS.hom_nay(b, HOM_NAY, XE_VTOS)
    assert hn["dang_di"] == 1, "xe 02259 đi Hòn Cò 02→04/11, hôm nay 03/11 còn trên đường"
    assert [x["tour"] for x in hn["danh_sach"]] == ["Hòn Cò"]
    assert hn["danh_sach"][0]["trang_thai"] == "Đang trên đường"
    # Chuyến Mỹ Tho về hôm 01/11 thì KHÔNG còn là xe đang đi.
    assert "Mỹ Tho 1day" not in [x["tour"] for x in hn["danh_sach"]]


def test_gop_khong_nhan_doi_khoi_xe():
    """Xe có mặt ở cả hai tab vẫn là MỘT xe — mẫu số «trên N xe» không được phồng lên."""
    bs = [XS.doc_bang(TAB_CU, kiem_chuoi=False), XS.doc_bang(TAB_MOI, kiem_chuoi=False)]
    b = XS.gop_bang(bs)
    ten = [k["khoi"] for k in b["khoi"]]
    assert ten == ["XE 1", "XE 2", "XE 11"], ten
    assert len(ten) == len(set(ten)), "mỗi khối xe đúng một lần"
    xe1 = [k for k in b["khoi"] if k["khoi"] == "XE 1"][0]
    assert xe1["so_chuyen"] == 2, "một chuyến tab cũ + một chuyến tab mới"
    assert len(b["chuyen"]) == 4


def test_noi_km_chay_mot_lan_tren_bang_da_gop():
    """Chuyến cuối tab cũ phải nối được với chuyến đầu tab mới — km 243.730 → 243.730."""
    bs = [XS.doc_bang(TAB_CU, kiem_chuoi=False), XS.doc_bang(TAB_MOI, kiem_chuoi=False)]
    b = XS.gop_bang(bs)
    assert [c for c in b["can_sua"] if c["loai"] == "km_noi"] == [], \
        "km nối đúng giữa hai tab mà vẫn bị báo đứt mạch"
    # Và khi ĐỨT thật thì vẫn bắt được, dù đứt ở ranh giới hai tab.
    lech = TAB_MOI.replace(",243730,243893,", ",299999,300162,")
    b2 = XS.gop_bang([XS.doc_bang(TAB_CU, kiem_chuoi=False),
                      XS.doc_bang(lech, kiem_chuoi=False)])
    assert [c["loai"] for c in b2["can_sua"] if c["loai"] == "km_noi"] == ["km_noi"]


def test_cac_link_tach_theo_dong():
    assert XS.cac_link("") == []
    assert XS.cac_link("  https://a  ") == ["https://a"]
    assert XS.cac_link("https://a\n\nhttps://b\n") == ["https://a", "https://b"]
