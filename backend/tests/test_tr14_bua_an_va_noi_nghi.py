# -*- coding: utf-8 -*-
"""TR-14 · BỮA ĂN VÀ NƠI NGHỈ CỦA TỪNG NGÀY, VÀ NGÀY NẰM GỌN TRONG MỘT DÒNG.

VÌ SAO CÓ VÒNG NÀY. TR-13 lên bản chạy thật 14/11/2026. Soát lại trên CẢ 174 sản phẩm đang
bán — không lấy số IT báo, gọi thẳng cửa công khai và đếm:

    · 40 / 174 tour tách được lịch trình theo ngày (tổng 146 ngày)
    · 134 / 174 KHÔNG tách được; trong đó chỉ 6 cái còn khối chữ, tức 128 tour hiện đúng một
      câu «Chương trình chi tiết đang cập nhật»
    · trong 146 ngày tách được: ĐÚNG 0 ngày có bữa ăn, ĐÚNG 0 ngày có nơi nghỉ

Nghĩa là dải «Đêm N · nơi nghỉ» và các thẻ «Ăn trưa / Ăn tối» mà Chủ tịch duyệt KHÔNG hiện
được lần nào. TR-13 mới xong phần khung. Ba chỗ hỏng, ba chỗ sửa:

  (A) HAI CỬA TRẢ RỖNG CỨNG. `lich_trinh()` đọc từ web và từ chương trình sản phẩm đều trả
      `{**x, "bua": [], "khach_san": ""}` — không phải thiếu dữ liệu, mà là không ai đọc. Chữ
      nằm ngay trên tiêu đề ngày: «… NOVELA RESORT (Ăn Sáng + Trưa)».

  (B) NGÀY NẰM GỌN TRONG MỘT DÒNG DÀI. `tach_ngay` cũ đòi dòng mốc ngắn dưới 300 ký tự. Rất
      nhiều bài web gói NGUYÊN một ngày vào một dòng — HC001 («BIỂN CÀ NÁ - HÒN CÒ RESORT»,
      tour Chủ tịch gửi ảnh) là một — nên cả tour mất lịch trình.

  (C) BÀI GIỚI THIỆU TRÊN WEB CÓ MỐC NGÀY MÀ KHÔNG AI THỬ TÁCH. HC001 lại đúng ca này: bài có
      đủ «NGÀY 1:» và «NGÀY 2:», mà trang tour đổ ra một khối chữ liền.

Mọi chuỗi trong tệp này là CHỮ THẬT, chép từ bản đang chạy ngày 14/11/2026, không bịa.
"""
import re
import unicodedata

from app.services import tour_online as T


# ══ A · ĐỌC BỮA ĂN ══════════════════════════════════════════════════════════════════════════
# Sáu cách viết khác nhau trong cùng một kho dữ liệu — nên phải đọc bằng luật, không so chuỗi.

def test_tr14_1_sau_cach_viet_bua_an_deu_doc_duoc():
    assert T.doc_bua("TP.HCM - PHAN THIẾT - NOVELA RESORT (Ăn Sáng + Trưa)") == ["sáng", "trưa"]
    assert T.doc_bua("ĐÀ NẴNG CHÀO ĐÓN QUÝ KHÁCH ( Ăn Tối)") == ["tối"]
    assert T.doc_bua("SUN WORLD BA NA HILLS – ĐƯỜNG LÊN TIÊN CẢNH ( Ăn Sáng, Trưa)") == ["sáng", "trưa"]
    assert T.doc_bua("TP.HỒ CHÍ MINH - HÒN CÒ RESORT - TANYOLI MÔNG CỔ (Ăn trưa,tối)") == ["trưa", "tối"]
    assert T.doc_bua("NHA TRANG – TP.HCM (Ăn sáng,trưa)") == ["sáng", "trưa"]
    # BL001 viết KHÔNG có chữ «Ăn» — vẫn phải đọc ra
    assert T.doc_bua("TP. HỒ CHÍ MINH – KDL RỪNG MADAGUI – BẢO LỘC (Trưa, tối)") == ["trưa", "tối"]


def test_tr14_2_cum_ngoac_khong_phai_bua_an_thi_khong_nhan():
    """Nhận bừa là bịa ra bữa ăn không có trong chương trình, và khách sẽ đòi đúng bữa ấy."""
    assert T.doc_bua("KHÁM PHÁ ĐÀ LẠT (Tango Your Life)") == []
    assert T.doc_bua("ĐÀ LẠT – THÀNH PHỐ MỘNG MƠ") == []
    assert T.doc_bua("CÔN ĐẢO (tự túc ăn uống)") == []


def test_tr14_3_cum_bua_an_bi_go_khoi_tieu_de():
    """Bữa đã thành thẻ riêng; để nguyên trong tiêu đề là in hai lần cùng một thứ."""
    assert T.bo_cum_bua("NHA TRANG – TP.HCM (Ăn sáng,trưa)") == "NHA TRANG – TP.HCM"
    assert T.bo_cum_bua("KHÁM PHÁ ĐÀ LẠT (Tango Your Life)") == "KHÁM PHÁ ĐÀ LẠT (Tango Your Life)"


# ══ B · ĐỌC NƠI NGHỈ ════════════════════════════════════════════════════════════════════════

def test_tr14_4_noi_nghi_doc_tu_tieu_de():
    assert T.doc_khach_san("TP.HCM - PHAN THIẾT - NOVELA RESORT (Ăn Sáng + Trưa)") == "NOVELA RESORT"
    assert T.doc_khach_san("TP.HỒ CHÍ MINH - HÒN CÒ RESORT - TANYOLI MÔNG CỔ (Ăn trưa,tối)") == "HÒN CÒ RESORT"


def test_tr14_5_noi_nghi_doc_tu_than_ngay_khi_tieu_de_khong_noi():
    nd = "Trưa: Quý khách dùng cơm. Nhận phòng khách sạn Sài Gòn - Ninh Chữ. Tự do tắm biển."
    assert T.doc_khach_san("ĐÀ LẠT - NHA TRANG", nd) == "khách sạn Sài Gòn - Ninh Chữ"


def test_tr14_6_khong_doan_ten_khach_san():
    """«Đang cập nhật» là sự thật; đoán tên khách sạn rồi in lên trang bán hàng thì không."""
    assert T.doc_khach_san("SUN WORLD BA NA HILLS – ĐƯỜNG LÊN TIÊN CẢNH") == ""
    assert T.doc_khach_san("ĐÀ LẠT – THÀNH PHỐ MỘNG MƠ", "Đoàn tham quan Thiền viện Trúc Lâm.") == ""
    # «nhận phòng» mà không nói chỗ nào thì vẫn là không biết
    assert T.doc_khach_san("ĐÀ LẠT", "Nhận phòng, tự do nghỉ ngơi.") == ""


def test_tr14_7_ngay_cuoi_khong_co_dem_nen_khong_co_noi_nghi():
    ds = [{"ngay": 1, "tieu_de": "TP.HCM - PHAN THIẾT - NOVELA RESORT (Ăn trưa)", "noi_dung": ""},
          {"ngay": 2, "tieu_de": "PHAN THIẾT - NOVELA RESORT - TP.HCM (Ăn sáng)", "noi_dung": ""}]
    ra = T.ngay_day_du(ds)
    assert ra[0]["khach_san"] == "NOVELA RESORT"
    assert ra[1]["khach_san"] == "", "ngày cuối không có đêm nào theo sau — vẽ ra là nói sai"


# ══ C · NGÀY NẰM GỌN TRONG MỘT DÒNG DÀI ═════════════════════════════════════════════════════

HC001 = (
    "ĐIỂM NỔI BẬT: Biển Cà Ná là một bãi biển đẹp nổi tiếng thuộc tỉnh Ninh Thuận.\n"
    "ĐỊA ĐIỂM ĐÓN KHÁCH: Điểm đón: 7h15 - Nhà Văn Hóa Thanh Niên (Số 4 Phạm Ngọc Thạch, Quận 1)\n"
    "NGÀY 1: TP.HỒ CHÍ MINH - HÒN CÒ RESORT - TANYOLI MÔNG CỔ (Ăn trưa,tối) 07h15: Xe và hướng "
    "dẫn viên Vietourist đón Quý khách tại điểm hẹn. Đoàn khởi hành theo tuyến cao tốc Sài Gòn – "
    "Dầu Giây – Phan Thiết – Vĩnh Hảo. Trưa: Quý khách dùng cơm tại nhà hàng địa phương. Nhận "
    "phòng tại Hòn Cò Resort. Tự do tắm biển. Tối: Đoàn dùng bữa tối tại nhà hàng.\n"
    "NGÀY 2: CUNG ĐƯỜNG VEN BIỂN CÀ NÁ - TP. HỒ CHÍ MINH (Ăn sáng, trưa) Sáng: Quý khách dùng "
    "điểm tâm tại khách sạn, trả phòng. Chiều: về đến TP.HCM, kết thúc chuyến đi."
)


def test_tr14_8_ca_that_hc001_tach_duoc_hai_ngay():
    """Luật cũ «dòng mốc phải ngắn dưới 300» loại thẳng dòng này, nên CẢ tour mất lịch trình."""
    ds = T.tach_ngay(HC001)
    assert [x["ngay"] for x in ds] == [1, 2]


def test_tr14_9_tieu_de_khong_nuot_ca_than_ngay():
    ds = T.tach_ngay(HC001)
    assert ds[0]["tieu_de"] == "TP.HỒ CHÍ MINH - HÒN CÒ RESORT - TANYOLI MÔNG CỔ (Ăn trưa,tối)"
    assert ds[0]["noi_dung"].startswith("07h15:")
    assert ds[1]["noi_dung"].startswith("Sáng:")


def test_tr14_10_ca_that_hc001_ra_du_bua_an_va_noi_nghi():
    ra = T.ngay_day_du(T.tach_ngay(HC001))
    assert ra[0]["bua"] == ["trưa", "tối"] and ra[0]["khach_san"] == "HÒN CÒ RESORT"
    assert ra[1]["bua"] == ["sáng", "trưa"] and ra[1]["khach_san"] == ""
    assert ra[0]["tieu_de"] == "TP.HỒ CHÍ MINH - HÒN CÒ RESORT - TANYOLI MÔNG CỔ"


def test_tr14_11_ngay_khong_lien_tiep_van_bi_tu_choi():
    """Nới luật dòng dài KHÔNG được nới luôn luật «phải là 1..N liên tiếp» — đó là thứ duy nhất
    phân biệt một chương trình thật với một đoạn văn tình cờ nhắc tới «ngày 3»."""
    assert T.tach_ngay("NGÀY 1: Đi\nNGÀY 3: Về") == []
    assert T.tach_ngay("Không có mốc ngày nào trong đoạn văn này cả.") == []


# ══ D · GIAO DIỆN: ĐIỂM ĐẾN CHÉP LẠI TÊN TOUR ═══════════════════════════════════════════════

from pathlib import Path  # noqa: E402

TEP_GD = Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "ToursAgoda.tsx"


def test_tr14_12_o_diem_den_trung_ten_tour_thi_bo():
    """Đo trên bản chạy: HC001 in «BIỂN CÀ NÁ - HÒN CÒ RESORT - THẢO NGUYÊN TANYOLI» hai lần
    trên một màn — một ở tiêu đề, một ở ô Điểm đến. TR-7 đã có sẵn phép so cho thẻ danh sách;
    vòng TR-13 thêm ô mới mà quên áp vào."""
    s = TEP_GD.read_text(encoding="utf-8")
    assert 'sp.diem_den && !trungTen(sp.ten, sp.diem_den)' in s


def test_tr14_13_phep_so_ten_van_con_nguyen():
    s = TEP_GD.read_text(encoding="utf-8")
    assert "const trungTen = " in s and "const boDau = " in s
