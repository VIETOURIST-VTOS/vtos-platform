# -*- coding: utf-8 -*-
"""TR-12 · BA CHỖ SỬA SAU MỘT NGÀY CHẠY THẬT CỦA TR-11.

TR-11 lên hệ thật ngày 13/11/2026 và bắt ngay 18 sản phẩm ghép lệch độ dài — nó làm đúng việc
của nó. Nhưng chính một ngày chạy thật ấy lộ ra ba chỗ TR-11 còn thiếu, và cả ba đều đo được
trên dữ liệu thật chứ không phải nghĩ ra:

  (A) CHẶN NGÀY MÀ KHÔNG CHẶN ĐÊM. Với tour trong nước, **3N2Đ và 3N3Đ là hai sản phẩm khác
      hẳn**: bản 3 đêm có thêm một đêm xe giường nằm, khác cả giờ đi, giá lẫn lịch trình.
      `DL001` («ĐÀ LẠT MỘNG MƠ», 3N2Đ, **9 chuyến đang mở bán**) có ứng viên hạng NHẤT là trang
      «Đà Lạt **3 Ngày 3 Đêm**» — TR-11 cho qua vì cùng 3 ngày.

  (B) BÁO OAN TOUR MỘT NGÀY. `NCT` («TOUR NAM CÁT TIÊN 1 NGÀY», 5 chuyến đang mở bán) bị ghi
      «Chưa có lịch theo ngày» dù có 1.942 ký tự nội dung. Một tour MỘT ngày thì không có
      «Ngày 1 / Ngày 2» nào để tách — chương trình của nó tự nhiên là một khối.

  (C) NHẦM LỖI DỮ LIỆU THÀNH LỖI GHÉP. `JP006` tên ghi «6N5D» mà cột `days` ghi 5; `MICEDL3N3D`
      tên ghi «3N3D» mà cột ghi 4. TR-11 gắn cho chúng nhãn «lệch số ngày», trông y hệt ghép
      sai — **suýt nữa bị gỡ link, mà link của chúng ĐÚNG**. Phải gọi đúng tên bệnh thì mới chữa
      đúng chỗ: sửa cột `days`, không phải đi ghép lại trang web.

Chạy trên số liệu bịa, nhưng ba ca A/B/C dựng lại đúng tên và đúng con số đã đo.
"""
from types import SimpleNamespace as SP

from app.services import tour_online as T


def sp(ten, days=None, do_dai="", diem_den="", link="", ma="X"):
    return SP(id=abs(hash(ten + ma)) % 100000, code=ma, name=ten, days=days, length_text=do_dai,
              diem_den=diem_den, link_web=link)


def w(ten, url=None):
    return {"ten": ten, "url": url or ("https://www.vietourist.com.vn/vn/tour/x/"
                                       + str(abs(hash(ten)) % 10**6) + ".html"),
            "anh": "", "muc": "", "goi_y_wellness": False}


# ══ A · ĐÊM CŨNG LÀ ĐIỀU KIỆN LOẠI ══════════════════════════════════════════════════════════

def test_tr12_1_doc_so_dem_tu_ten():
    assert T._so_dem("Tour Đà Lạt 3N2Đ") == 2
    assert T._so_dem("Tour Du Lịch Đà Lạt 3 Ngày 2 Đêm") == 2
    assert T._so_dem("Tour Du Lịch Đà Lạt 3 Ngày 3 Đêm") == 3
    assert T._so_dem("Tour Đà Lạt 3 Ngày") is None, "không ghi đêm thì phải là «không biết»"
    assert T._so_dem("") is None


def test_tr12_2_ca_that_dl001_khong_con_bi_gan_vao_ban_3_dem():
    """Ca (A), dựng lại nguyên văn. DL001 là 3N2Đ — trang 3N3Đ KHÔNG được nhận nó nữa."""
    ba_hai = w("Tour Du Lịch Đà Lạt 3 Ngày 2 Đêm: Thành Phố Ngàn Hoa")
    ba_ba = w("Tour Du Lịch Tết Âm Lịch 2027: Đà Lạt 3 Ngày 3 Đêm")
    dl001 = sp("ĐÀ LẠT MỘNG MƠ 3N2Đ", ma="DL001", diem_den="ĐÀ LẠT")
    assert T.so_ngay_sp(dl001) == 3 and T.so_dem_sp(dl001) == 2

    ra = {o["url"]: o["goi_y"] for o in T.goi_y_ghep([ba_hai, ba_ba], [dl001])}
    assert ra[ba_ba["url"]] is None, "bản 3 ĐÊM vẫn nhận tour 2 đêm — đúng lỗi TR-11 còn sót"
    assert ra[ba_hai["url"]] and ra[ba_hai["url"]]["ma"] == "DL001"


def test_tr12_3_chieu_nguoc_cung_chan_dem():
    ba_hai = w("Tour Du Lịch Đà Lạt 3 Ngày 2 Đêm: Thành Phố Ngàn Hoa")
    ba_ba = w("Tour Du Lịch Tết Âm Lịch 2027: Đà Lạt 3 Ngày 3 Đêm")
    dl001 = sp("ĐÀ LẠT MỘNG MƠ 3N2Đ", ma="DL001", diem_den="ĐÀ LẠT")
    uv = T.goi_y_web([ba_hai, ba_ba], [dl001])[0]["ung_vien"]
    assert [x["url"] for x in uv] == [ba_hai["url"]]


def test_tr12_4_mot_ben_khong_ghi_dem_thi_khong_loai():
    """Siết theo thứ không đọc được là giết hết gợi ý đúng — rất nhiều tên chỉ ghi «3 Ngày»."""
    chi_ngay = w("Tour Du Lịch Đà Lạt 3 Ngày: Thành Phố Ngàn Hoa")
    dl = sp("ĐÀ LẠT MỘNG MƠ 3N2Đ", ma="DL001", diem_den="ĐÀ LẠT")
    assert T.goi_y_ghep([chi_ngay], [dl])[0]["goi_y"] is not None
    assert T._hop_ngay(3, 3, None, 2) and T._hop_ngay(3, 3, 2, None)
    assert not T._hop_ngay(3, 3, 3, 2)


# ══ B · TOUR MỘT NGÀY KHÔNG CÓ «NGÀY 1 / NGÀY 2» ════════════════════════════════════════════

def sp_nd(ten, lich_ngay=0, days=None, gioi_thieu="", chuong_trinh=""):
    return SP(name=ten, days=days, length_text="", program=chuong_trinh, services="dịch vụ",
              noi_dung_web={"anh": ["a.jpg"], "lich_trinh": [{"ngay": i + 1} for i in range(lich_ngay)],
                            "bao_gom": ["Xe"], "khong_bao_gom": [], "quy_dinh": "",
                            "gioi_thieu": gioi_thieu})


def test_tr12_5_ca_that_nct_tour_mot_ngay_khong_bi_bao_thieu_lich():
    """Ca (B). NCT có 1.942 ký tự nội dung mà vẫn bị đếm vào danh sách thiếu lịch."""
    p = sp_nd("TOUR NAM CÁT TIÊN 1 NGÀY", days=1, gioi_thieu="ĐIỂM NỔI BẬT: đạp xe xuyên rừng…")
    assert "lich" not in T.thieu_noi_dung(p, chuyen=[])


def test_tr12_6_mot_ngay_ma_KHONG_co_chu_thi_van_phai_bao():
    """Bỏ oan thì được, bỏ luôn cả ca thật thì không: một ngày mà trống trơn vẫn là thiếu."""
    p = sp_nd("TOUR NAM CÁT TIÊN 1 NGÀY", days=1)
    assert "lich" in T.thieu_noi_dung(p, chuyen=[])


def test_tr12_7_tour_nhieu_ngay_van_bi_bao_nhu_cu():
    p = sp_nd("TOUR ĐÀ LẠT 3 NGÀY", days=3, gioi_thieu="ĐIỂM NỔI BẬT: …")
    assert "lich" in T.thieu_noi_dung(p, chuyen=[]), "tour 3 ngày thì vẫn phải có lịch từng ngày"


# ══ C · CỘT `days` CHỌI VỚI TÊN SẢN PHẨM ════════════════════════════════════════════════════

def test_tr12_8_ca_that_jp006_cot_ngay_chong_lai_ten():
    """Ca (C). Tên ghi 6N5D, cột ghi 5 — lỗi DỮ LIỆU, phải gọi đúng tên để không đi gỡ nhầm link."""
    p = sp_nd("VT - OSAKA - KYOTO - FUJI - YAMANASHI - TOKYO - 6N5D - VNA", lich_ngay=6, days=5)
    th = T.thieu_noi_dung(p, chuyen=[])
    assert "ngay_vench" in th, "cột số ngày chọi với tên mà không ai được báo"
    assert "ngay_vench" in T.THIEU_ND


def test_tr12_9_ca_that_micedl3n3d():
    p = sp_nd("ĐÀ LẠT 3N3D", lich_ngay=3, days=4)
    assert "ngay_vench" in T.thieu_noi_dung(p, chuyen=[])


def test_tr12_10_ten_khop_cot_thi_khong_keu():
    assert "ngay_vench" not in T.thieu_noi_dung(sp_nd("ĐÀ LẠT 3N2D", lich_ngay=3, days=3), chuyen=[])
    # tên không ghi độ dài → không có gì để chọi
    assert "ngay_vench" not in T.thieu_noi_dung(sp_nd("ĐÀ LẠT MỘNG MƠ", lich_ngay=3, days=3), chuyen=[])
    # không có cột days → không suy đoán
    assert "ngay_vench" not in T.thieu_noi_dung(sp_nd("ĐÀ LẠT 3N2D", lich_ngay=3), chuyen=[])


def test_tr12_11_hai_canh_bao_doc_lap_nhau():
    """`lech_ngay` nói về LINK, `ngay_vench` nói về DỮ LIỆU. Một bản ghi có thể dính cả hai, và
    người đọc phải phân biệt được — đó là toàn bộ lý do tách làm hai nhãn."""
    p = sp_nd("ĐÀ LẠT 3N2D", lich_ngay=5, days=4)      # tên 3, cột 4, web 5
    th = T.thieu_noi_dung(p, chuyen=[])
    assert "lech_ngay" in th and "ngay_vench" in th
