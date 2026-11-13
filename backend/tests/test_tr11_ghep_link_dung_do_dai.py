# -*- coding: utf-8 -*-
"""TR-11 · GHÉP LINK TOUR WEB: ĐỘ DÀI LÀ ĐIỀU KIỆN LOẠI, VÀ GỢI Ý PHẢI ĐI ĐƯỢC CHIỀU NGƯỢC.

VÌ SAO CÓ VÒNG NÀY — hai ca có thật, đo trên hệ thống thật ngày 13/11/2026.

  (A) GỢI Ý SAI ĐÚNG VÀO CA ĐIỂM CAO NHẤT. Web cũ có 20 tour «Singapore – Malaysia». Với sản
      phẩm `SM001` («HÀ NỘI - SINGAPORE - MALAYSIA 5N4D»), bản cũ của `goi_y_ghep` chấm **1.00 —
      điểm tuyệt đối** cho trang «Singapore - Malaysia 4 NGÀY 3 ĐÊM Khởi Hành Từ Hà Nội», trong
      khi bản đúng «5 Ngày 4 Đêm KH Từ Hà Nội» nằm ngay cạnh trong cùng danh sách. Hai tên có
      cùng bộ từ sau khi `_tu` lọc bỏ «5n4d», nên khác biệt DUY NHẤT là số ngày — mà số ngày chỉ
      được cộng 0.15 điểm. Một khoản thưởng nhỏ không bao giờ thắng nổi một tên khớp hơn nửa từ.

  (B) GHÉP NHẦM ĐỘ DÀI KHÔNG AI THẤY ĐƯỢC. Trong 120 sản phẩm đã ghép link, 88 sản phẩm đọc
      được số ngày ở cả hai bên — **7 sản phẩm lệch**, và hai trong số đó đang mở bán:
      `TL001` (cổng ghi 2 NGÀY 1 ĐÊM, 2 chuyến mở, nội dung đọc từ trang La Ngâu **3N2Đ**) và
      `JP0013` (cổng ghi 6N5Đ, 3 chuyến mở, trang đã ghép có đúng **5 ngày** lịch trình).
      Màn hình hôm ấy ghi dòng `JP0013` là **«Đủ nội dung»** — vì mọi phép kiểm cũ chỉ hỏi «có
      hay không có», không phép nào hỏi «có ĐÚNG không».

Hậu quả của cả hai không phải là xấu mặt: khách đặt tour 5 ngày rồi đọc lịch trình, bảng giá và
«bao gồm» của tour 4 ngày — một lời hứa sai với người đã trả tiền.

Phép thử ở đây chạy trên SỐ LIỆU BỊA (không cần kho, không cần mạng), nhưng hai ca A và B dựng
lại đúng tên thật đã đo được, để chúng không quay lại.
"""
from types import SimpleNamespace as SP

from app.services import tour_online as T


def sp(ma, ten, days=None, do_dai="", diem_den="", link=""):
    """Sản phẩm giả — `goi_y_*` chỉ đọc đúng mấy thuộc tính này."""
    return SP(id=abs(hash(ma)) % 100000, code=ma, name=ten, days=days, length_text=do_dai,
              diem_den=diem_den, link_web=link)


def w(ten, url=None, anh=""):
    return {"ten": ten, "url": url or ("https://www.vietourist.com.vn/vn/tour/x/" + str(abs(hash(ten)) % 10**6) + ".html"),
            "anh": anh, "muc": "", "goi_y_wellness": False}


# ══ A · ĐỘ DÀI LÀ ĐIỀU KIỆN LOẠI ════════════════════════════════════════════════════════════

SAI = w("Tour Du Lịch Singapore - Malaysia 4 Ngày 3 Đêm Khởi Hành Từ Hà Nội")
DUNG = w("Tour Du Lịch Singapore - Malaysia 5 Ngày 4 Đêm KH Từ Hà Nội")
SM001 = sp("SM001", "HÀ NỘI - SINGAPORE - MALAYSIA 5N4D")


def test_tr11_1_ca_that_sm001_khong_con_bi_gan_vao_tour_4_ngay():
    """Ca (A), dựng lại nguyên văn. Trang 4 ngày KHÔNG được nhận SM001 nữa."""
    assert T._so_ngay(SM001.name) == 5, "đọc số ngày từ «5N4D» phải ra 5"
    assert T._so_ngay(SAI["ten"]) == 4 and T._so_ngay(DUNG["ten"]) == 5
    ra = {o["url"]: o["goi_y"] for o in T.goi_y_ghep([SAI, DUNG], [SM001])}
    assert ra[SAI["url"]] is None, "trang 4 ngày vẫn còn nhận tour 5 ngày — đúng lỗi 13/11/2026"
    assert ra[DUNG["url"]] and ra[DUNG["url"]]["ma"] == "SM001"


def test_tr11_2_ban_cu_that_su_chon_sai_nen_phep_thu_nay_co_nghia():
    """Chứng minh phép thử trên KHÔNG xanh sẵn: cách chấm cũ đúng là chọn trang sai.

    Không có phép này thì test_1 có thể xanh vì một lý do tình cờ, và hàng rào thành trang trí.
    """
    tp = T._tu(SM001.name)
    cu = lambda tw: len(tw & tp) / len(tw | tp)            # noqa: E731 — Jaccard thuần, đúng bản cũ
    d_sai, d_dung = cu(T._tu(SAI["ten"])), cu(T._tu(DUNG["ten"]))
    assert d_sai >= d_dung, "bản cũ phải chấm trang SAI cao hơn hoặc bằng — đó là lý do nó chọn nhầm"
    assert d_sai + 0.0 >= 0.99, "trang sai đạt điểm gần tuyệt đối ở bản cũ (đo được 1.00)"


def test_tr11_3_mot_ben_khong_doc_duoc_so_ngay_thi_van_duoc_xet():
    """Siết quá tay cũng hỏng: rất nhiều tên crm không ghi độ dài. Thiếu số thì KHÔNG loại."""
    kh = sp("DL001", "ĐÀ LẠT MỘNG MƠ")                      # không có số ngày ở đâu cả
    assert T.so_ngay_sp(kh) is None
    ra = T.goi_y_ghep([w("Tour Du Lịch Đà Lạt Mộng Mơ 3 Ngày 2 Đêm")], [kh])
    assert ra[0]["goi_y"] and ra[0]["goi_y"]["ma"] == "DL001"


def test_tr11_4_so_ngay_sp_doc_theo_thu_tu_tin_cay():
    assert T.so_ngay_sp(sp("A", "TÊN KHÔNG SỐ", days=4, do_dai="7 NGÀY")) == 4      # cột days thắng
    assert T.so_ngay_sp(sp("B", "ĐÀ LẠT 3N2Đ", do_dai="5 NGÀY")) == 3              # rồi tới tên
    assert T.so_ngay_sp(sp("C", "ĐÀ LẠT", do_dai="5 NGÀY 4 ĐÊM")) == 5             # rồi tới length_text
    assert T.so_ngay_sp(sp("D", "ĐÀ LẠT")) is None


# ══ B · MÀN HÌNH PHẢI NÓI RA KHI GHÉP LỆCH ══════════════════════════════════════════════════

def sp_nd(ten, lich_ngay, days=None):
    """Sản phẩm đã ghép link, web đọc về `lich_ngay` ngày."""
    return SP(name=ten, days=days, length_text="", program="", services="dịch vụ",
              noi_dung_web={"anh": ["a.jpg"], "lich_trinh": [{"ngay": i + 1} for i in range(lich_ngay)],
                            "bao_gom": ["Xe"], "khong_bao_gom": [], "quy_dinh": ""})


def test_tr11_5_ca_that_jp0013_tour_6_ngay_ghep_trang_5_ngay_phai_do():
    """Ca (B), dựng lại nguyên văn. Hôm 13/11 màn hình ghi dòng này là «Đủ nội dung»."""
    p = sp_nd("OSAKA – KYOTO – NÚI PHÚ SĨ – TOKYO - QUÝ 4", lich_ngay=5, days=6)
    thieu = T.thieu_noi_dung(p, chuyen=[])
    assert "lech_ngay" in thieu, "tour 6 ngày ghép trang 5 ngày mà vẫn được chấm đủ nội dung"
    assert "lech_ngay" in T.THIEU_ND, "phải có lời giải thích cho người đọc màn hình"


def test_tr11_6_ca_that_tl001_tour_2_ngay_ghep_trang_3_ngay_phai_do():
    p = sp_nd("HỒ ĐA MI - LA NGÂU - THÁC BẢO ĐẠI 2N1Đ", lich_ngay=3)
    assert T.so_ngay_sp(p) == 2, "đọc «2N1Đ» từ tên"
    assert "lech_ngay" in T.thieu_noi_dung(p, chuyen=[])


def test_tr11_7_ghep_dung_do_dai_thi_khong_duoc_keu():
    """Hàng rào kêu oan vài lần là hàng rào người ta thôi đọc."""
    assert "lech_ngay" not in T.thieu_noi_dung(sp_nd("TOUR 6 NGÀY", lich_ngay=6, days=6), chuyen=[])
    # web chưa đọc được lịch (0 ngày) → đã có cảnh báo «lich» lo việc ấy, không báo chồng
    assert "lech_ngay" not in T.thieu_noi_dung(sp_nd("TOUR 6 NGÀY", lich_ngay=0, days=6), chuyen=[])
    # sản phẩm không đọc được số ngày → không suy đoán
    assert "lech_ngay" not in T.thieu_noi_dung(sp_nd("ĐÀ LẠT MỘNG MƠ", lich_ngay=3), chuyen=[])


# ══ C · CHIỀU NGƯỢC: SẢN PHẨM → TRANG WEB ═══════════════════════════════════════════════════

def test_tr11_8_chi_bay_san_pham_chua_ghep():
    da = sp("DA", "ĐÀ NẴNG - HỘI AN - BÀ NÀ", link="https://www.vietourist.com.vn/vn/tour/x/1.html")
    chua = sp("CH", "ĐÀ NẴNG - HỘI AN - BÀ NÀ")
    ma = {o["ma"] for o in T.goi_y_web([w("Tour Du Lịch Đà Nẵng: Đà Nẵng - Hội An - Bà Nà 3 Ngày 2 Đêm")], [da, chua])}
    assert ma == {"CH"}, "sản phẩm đã có link thì không phải việc của cửa này"


def test_tr11_9_khong_bay_trang_dang_thuoc_ve_san_pham_khac():
    """Bày một trang đã có chủ là dẫn người ta tới lỗi 409 «link đang ghép với…»."""
    t = w("Tour Du Lịch Đà Nẵng: Đà Nẵng - Hội An - Bà Nà 3 Ngày 2 Đêm")
    p = sp("MT001", "ĐÀ NẴNG - HỘI AN - BÀ NÀ")
    assert T.goi_y_web([t], [p])[0]["ung_vien"], "khi chưa ai giữ thì phải bày ra"
    assert T.goi_y_web([t], [p], da_ghep={t["url"]})[0]["ung_vien"] == []


def test_tr11_10_chac_doi_ca_diem_cao_VA_cach_biet():
    """«Chắc» mà không đòi cách biệt là lại rơi đúng vào bẫy 20 tour Singapore – Malaysia:
    hai biến thể của cùng một tuyến đứng sát nhau, chọn bừa một cái là sai một nửa số lần."""
    p = sp("MT001", "ĐÀ NẴNG - HỘI AN - BÀ NÀ", days=3)
    mot = T.goi_y_web([w("Tour Du Lịch Đà Nẵng - Hội An - Bà Nà 3 Ngày 2 Đêm")], [p])[0]
    assert mot["chac"] and mot["ung_vien"][0]["diem"] >= 0.80

    # hai trang na ná nhau, cùng độ dài → KHÔNG được chắc
    hai = T.goi_y_web([w("Tour Du Lịch Đà Nẵng - Hội An - Bà Nà 3 Ngày 2 Đêm"),
                       w("Tour Du Lịch Đà Nẵng - Hội An - Bà Nà 3 Ngày 2 Đêm Lễ 2/9")], [p])[0]
    assert len(hai["ung_vien"]) >= 2
    assert not hai["chac"], "hai biến thể sát điểm nhau mà vẫn báo «chắc»"


def test_tr11_11_do_dai_lech_thi_khong_lam_ung_vien_o_chieu_nguoc_nua():
    """Cùng luật với chiều xuôi — ca SM001, nhìn từ phía sản phẩm."""
    uv = T.goi_y_web([SAI, DUNG], [SM001])[0]["ung_vien"]
    assert [x["url"] for x in uv] == [DUNG["url"]]


def test_tr11_12_diem_den_bu_cho_ten_crm_qua_ngan():
    """«ĐÀ LẠT MỘNG MƠ» ↔ «Đà Lạt 3 Ngày 2 Đêm: Thành Phố Ngàn Hoa» — chữ chung chỉ có «đà lạt».
    Tên crm ngắn và đặt khác hẳn web là chuyện thường, nên điểm đến phải được tính vào."""
    t = w("Tour Du Lịch Đà Lạt 3 Ngày 2 Đêm: Thành Phố Ngàn Hoa - Thung Lũng Tình Yêu")
    khong = T.goi_y_web([t], [sp("DL001", "ĐÀ LẠT MỘNG MƠ")])[0]["ung_vien"]
    co = T.goi_y_web([t], [sp("DL001", "ĐÀ LẠT MỘNG MƠ",
                              diem_den="ĐÀ LẠT THUNG LŨNG TÌNH YÊU THÀNH PHỐ NGÀN HOA")])[0]["ung_vien"]
    assert len(co) >= len(khong), "thêm điểm đến mà ứng viên lại ít đi thì phép trộn điểm sai"
    if khong and co:
        assert co[0]["diem"] > khong[0]["diem"]


def test_tr11_13_ung_vien_qua_yeu_thi_khong_bay_ra():
    """Bày một gợi ý tồi tốn thì giờ người xem hơn là không bày gì."""
    uv = T.goi_y_web([w("Tour Du Lịch Châu Âu 5 Nước: Pháp - Bỉ - Hà Lan - Đức - Thụy Sĩ")],
                     [sp("NT001", "TOUR NHA TRANG 3 NGÀY 2 ĐÊM")])[0]["ung_vien"]
    assert uv == []
    assert 0 < T.NGUONG_UNG_VIEN < 1


def test_tr11_14_toi_da_ba_ung_vien_va_xep_theo_diem_giam_dan():
    p = sp("DL001", "ĐÀ LẠT MỘNG MƠ", diem_den="ĐÀ LẠT")
    web = [w(f"Tour Du Lịch Đà Lạt Mộng Mơ Bản {i}") for i in range(6)]
    uv = T.goi_y_web(web, [p])[0]["ung_vien"]
    assert len(uv) <= T.SO_UNG_VIEN == 3
    assert [x["diem"] for x in uv] == sorted((x["diem"] for x in uv), reverse=True)
