# -*- coding: utf-8 -*-
"""P1-01 (Đề xuất hoàn thiện VTD v1.1; Chủ tịch chọn «Tự tách đúng mục», 09/11/2026).

Rà 09/11: tour 6591 «ĐÀ LẠT - VĨNH HY» không có link web, nên tab Lịch trình trên kh.vietourist.vn hiện NGUYÊN VĂN ô
«Chương trình» của sản phẩm — ô ấy chứa «GIÁ TOUR BAO GỒM / KHÔNG BAO GỒM…», có dòng lặp («Xe du lịch đời mới…» hai
lần), không có mốc «Ngày 1, 2…»; «Giá bao gồm» thì «Đang cập nhật». Nay máy tách theo dòng tiêu đề mục; không sửa dữ
liệu gốc."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_p1_01.db")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from types import SimpleNamespace as NS

VB_6591 = """GIÁ TOUR BAO GỒM : 
-     Xe du lịch đời mới đưa đón đoàn suốt hành trình
-    Xe Du Lịch Đời Mới Đưa đón Đoàn Suốt Hành Trình
-      Ăn uống theo chương trình, theo ẩm thực địa phương.
     GIÁ TOUR KHÔNG BAO GỒM:
-      Chi phí cá nhân: giặt ủi, điện thoại
ĐIỀU KIỆN HỦY TOUR:
Hủy trước 7 ngày: 30%"""


def test_p1_01_1_ban_6591_tach_dung_muc_bo_dong_lap():
    from app.services.tour_online import tach_muc
    r = tach_muc(VB_6591)
    assert r["chuong_trinh"] == ""                                       # không còn gì để hiện ở «Lịch trình»
    assert r["bao_gom"] == ["Xe du lịch đời mới đưa đón đoàn suốt hành trình", "Ăn uống theo chương trình, theo ẩm thực địa phương."]
    assert r["khong_bao_gom"] == ["Chi phí cá nhân: giặt ủi, điện thoại"]
    assert r["quy_dinh"].startswith("ĐIỀU KIỆN HỦY TOUR:") and "30%" in r["quy_dinh"]


def test_p1_01_2_lich_ngay_khong_bi_dinh_quy_dinh_vao_ngay_cuoi():
    from app.services.tour_online import tach_muc, tach_ngay
    vb = "NGÀY 1: TP.HCM - ĐÀ LẠT\nSáng khởi hành\nLưu ý: mang áo khoác\nNGÀY 2: ĐÀ LẠT - VĨNH HY\nTham quan\nGIÁ TOUR BAO GỒM:\n- Xe\nLƯU Ý:\nMang CCCD"
    r = tach_muc(vb)
    ngay = tach_ngay(r["chuong_trinh"])
    assert [n["ngay"] for n in ngay] == [1, 2]
    assert "Lưu ý: mang áo khoác" in ngay[0]["noi_dung"]                  # «Lưu ý:» giữa ngày không phải tiêu đề mục
    assert ngay[1]["noi_dung"] == "Tham quan"                            # không dính «GIÁ TOUR BAO GỒM» vào ngày cuối
    assert r["bao_gom"] == ["Xe"] and r["quy_dinh"] == "LƯU Ý:\nMang CCCD"


def test_p1_01_3_lich_trinh_san_pham_dung_phan_chuong_trinh(monkeypatch):
    from app.services import tour_online as T
    p = NS(noi_dung_web={}, program=VB_6591)
    r = T.lich_trinh(None, p)
    # TR-21 · Trước đây dòng này so BẰNG NHAU cả cuốn từ điển. TR-18 thêm khoá «theo_chuyen»
    # (lịch trình này của riêng chuyến nào — rỗng là bản chung) để trang khách biết lúc nào
    # KHÔNG phải gọi lại máy chủ, và phép so bằng nhau đỏ ngay, dù không có gì sai. Nay soi
    # đúng ba điều P1-01 muốn canh: cổng hiện «Chương trình chi tiết đang cập nhật». Thêm
    # khoá mới thì không đỏ; đổi ba điều này thì vẫn đỏ.
    assert r["nguon"] == "van_ban" and r["ngay"] == [] and r["van_ban"] == ""
    p2 = NS(noi_dung_web={}, program="NGÀY 1: A\nx\nNGÀY 2: B\ny\nGIÁ TOUR BAO GỒM:\n- Xe")
    r2 = T.lich_trinh(None, p2)
    assert r2["nguon"] == "san_pham" and r2["ngay"][1]["noi_dung"] == "y"


def test_p1_01_4_chi_tiet_lay_muc_tach_khi_web_trong():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "services", "tour_online.py"),
               encoding="utf-8").read()
    i = src.index("def chi_tiet(")
    than = src[i:src.index("\ndef ", i + 10)]
    assert 'nd.get("bao_gom") or tm["bao_gom"]' in than and 'nd.get("quy_dinh") or tm["quy_dinh"]' in than


def test_p1_01_5_thieu_noi_dung_dung_nguon_cong_hien():
    from app.services.tour_online import thieu_noi_dung
    t_du, t_thieu = NS(id=1, price_chd=900_000), NS(id=2, price_chd=None)
    p6591 = NS(noi_dung_web={}, program=VB_6591, services="")
    assert thieu_noi_dung(p6591, [(t_du, 10)]) == ["anh", "lich"]               # bao gồm đã tách được từ chương trình
    p_web = NS(noi_dung_web={"anh": ["a.jpg"], "lich_trinh": [{"ngay": 1}], "bao_gom": ["Xe"]}, program="", services="")
    assert thieu_noi_dung(p_web, [(t_du, 5), (t_thieu, 5)]) == ["tre_em"]
    assert thieu_noi_dung(p_web, []) == []                                     # chưa có chuyến thì không xét giá trẻ em
    p_ct = NS(noi_dung_web={"anh": ["a.jpg"]}, program="", services="Xe, khách sạn")
    assert thieu_noi_dung(p_ct, [(t_du, 5)], co_ct_chuyen=True) == []          # chuyến đã có chương trình riêng


def test_p1_01_6_man_crm_co_cot_va_loc():
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = open(os.path.join(goc, "web", "app", "tour-online", "page.tsx"), encoding="utf-8").read()
    assert "<th>Nội dung trên cổng</th>" in s and '<NoiDungCong p={p}' in s
    assert 'loc === "thieu"' in s and "Thiếu nội dung (" in s
    src = open(os.path.join(goc, "backend", "app", "services", "tour_online.py"), encoding="utf-8").read()
    i = src.index("def ds_vtos(")
    assert "thieu_noi_dung(p, ch.get(p.id, [])" in src[i:src.index("\ndef ", i + 10)]
