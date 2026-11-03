# -*- coding: utf-8 -*-
"""XS-6 (03/11/2026) — khối chi phí tháng trên sheet KHÔNG phải rác, và nó chưa vào sổ VTOS.

XS-4 vừa dạy bộ đọc bỏ qua khối ấy để thôi báo mười cảnh báo giả. Bỏ qua là đúng cho câu hỏi
«xe nào đang đi», nhưng đo trên hệ thật 03/11/2026 thì khối ấy mang **125.771.596 đ** chi phí
đội xe tháng 10, và sổ «Chi phí kỳ» của VTOS **không có một dòng nào** cho tháng 10.

Khuôn CSV dưới đây chép đúng khuôn sheet thật, kể cả chỗ hàng tiêu đề của bảng chi phí
(«XE / SỐ TIỀN / HD SỐ») rơi trúng ba cột Ngày đi / Ngày về / Số ngày của bảng chuyến, và kể cả
chỗ nhãn chỉ ghi ở dòng đầu rồi để trống các dòng xe bên dưới.
"""
from app.services import xe_theo_sheet as XS

DAU = ('XE SỐ,SỐ,Lái xe,Tên tour,Ngày đi,Ngày về,Số ngày,CTP,"Gửi xe +\nphí khác",Dầu,EPASS,D. Thu,'
       'Tổng Chi,Lợi nhuận,Km đầu,Km cuối,Tổng km ,SL lít,"Tiêu Hao\n100km",NOTE\n')

BANG = DAU + (
    'XE 1,01783,TÚ\n'
    ',50F01783,TÚ,Đà Lạt,20/10/2026,22/10/2026,3,600000,30000,5000000,700000,10000000,'
    '6330000,3670000,1000,1600,600,180,"30"\n'
    ',,,B.DƯỠNG T10,XE,SỐ TIỀN,HD SỐ\n'
    ',,,,50F 01737,6891048,6267- VIỆT NHÂN\n'
    ',,,,50H 93408,6891048,6268-VIỆT NHÂN\n'
    ',,,BÃI XE THÁNG 10,VIETRIP ,2160000,50H49829- HD 4924\n'
    ',,,,VTD+ NƯỚC,22930560, 4925-  10 XE VTD\n'
    ',,,SIM DATA ,50F01783,1600000,VIETEL 3271475\n'
    ',,,THAY VỎ XE ,50H49829,30800000,9967\n'
    ',,,CHI PHÍ LÃI VAY,,,\n'
)


def test_doc_duoc_khoi_chi_phi_va_khong_coi_la_chuyen():
    b = XS.doc_bang(BANG)
    assert len(b["chuyen"]) == 1, "khối chi phí tháng vẫn không được đếm thành chuyến (XS-4)"
    cp = b["chi_phi_thang"]
    assert [c["so_tien"] for c in cp] == [6891048, 6891048, 2160000, 22930560, 1600000, 30800000]
    assert sum(c["so_tien"] for c in cp) == 71272656
    # Dòng «CHI PHÍ LÃI VAY» không có số tiền → không tạo khoản rỗng.
    assert "CHI PHÍ LÃI VAY" not in [c["nhan"] for c in cp]


def test_nhan_mang_theo_cac_dong_xe_ben_duoi():
    """Sheet chỉ ghi nhãn ở dòng đầu; bảy dòng xe bên dưới để trống tên."""
    cp = XS.doc_bang(BANG)["chi_phi_thang"]
    assert [c["nhan"] for c in cp[:2]] == ["B.DƯỠNG T10", "B.DƯỠNG T10"]
    assert cp[0]["xe_ghi"] == "50F 01737" and cp[1]["xe_ghi"] == "50H 93408"
    assert cp[2]["nhan"] == "BÃI XE THÁNG 10" and cp[3]["nhan"] == "BÃI XE THÁNG 10"


def test_xep_dung_nhom_chi_phi_ky_cua_VTOS():
    from app.models.fleet import NHOM_CHI_PHI_KY
    assert XS.nhom_chi_phi("B.DƯỠNG T10") == "bao_duong"
    assert XS.nhom_chi_phi("BÃI XE THÁNG 10") == "bai_xe"
    assert XS.nhom_chi_phi("SIM DATA") == XS.nhom_chi_phi("CAMERA NĐ 10") == "quan_ly"
    assert XS.nhom_chi_phi("THAY VỎ XE") == XS.nhom_chi_phi("CÔNG THAY VỎ XE") == "tra_truoc"
    assert XS.nhom_chi_phi("BẢO HIEM XE") == XS.nhom_chi_phi("BH DS CARIVAL") == "bao_hiem"
    assert XS.nhom_chi_phi("CHI PHÍ LÃI VAY") == "lai_vay"
    # Mọi nhãn đã khai phải trỏ tới một nhóm CÓ THẬT — khai sai thì cửa nhập trả 422 và
    # người đọc chỉ thấy «nhập ở nhóm X» với X không tồn tại.
    for _, ma in XS.NHAN_CHI_PHI_THANG:
        assert ma in NHOM_CHI_PHI_KY, ma
    assert XS.nhom_chi_phi("MỘT KHOẢN LẠ") is None, "không khớp thì phải nói ra, không xếp bừa"


def test_ky_chi_lay_khi_nhan_noi_ra_thang():
    """KHÔNG đoán kỳ. Chạy thử trên số thật, lối lui «tháng phổ biến của các chuyến» đẩy 50,3 triệu
    sang tháng 9 chỉ vì bảng có một chuyến đi ngày 30/09."""
    cp = {c["nhan"]: c["ky"] for c in XS.doc_bang(BANG)["chi_phi_thang"]}
    assert cp["B.DƯỠNG T10"] == "2026-10"
    assert cp["BÃI XE THÁNG 10"] == "2026-10"
    assert cp["SIM DATA"] is None, "nhãn không ghi tháng thì KHÔNG đoán"
    assert cp["THAY VỎ XE"] is None


def test_nam_lay_tu_chuyen_va_bat_duoc_khoan_cua_nam_truoc():
    bang = DAU + ('XE 1,01783,TÚ\n'
                  ',50F01783,TÚ,Đà Lạt,05/01/2026,06/01/2026,2,200000,,,,5000000,,,,,,,\n'
                  ',,,B.DƯỠNG T12,XE,SỐ TIỀN,HD SỐ\n'
                  ',,,,50F01783,1000000,HD1\n')
    cp = XS.doc_bang(bang)["chi_phi_thang"]
    assert cp[0]["ky"] == "2025-12", "nhãn T12 trên bảng toàn chuyến tháng 1 là khoản của năm trước"


def test_gop_nhieu_tab_giu_nguyen_khoi_chi_phi():
    b1 = XS.doc_bang(BANG, kiem_chuoi=False)
    b2 = XS.doc_bang(DAU + 'XE 2,02259,HỒ\n,50F02259,HỒ,Hòn Cò,02/11/2026,04/11/2026,3,600000,,,,,,,,,,,\n',
                     kiem_chuoi=False)
    g = XS.gop_bang([b1, b2])
    assert len(g["chi_phi_thang"]) == 6, "gộp tab không được làm rơi khối chi phí"
