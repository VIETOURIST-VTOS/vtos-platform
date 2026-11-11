# -*- coding: utf-8 -*-
"""MKT-9 — DẤU LÀ MỘT PHẦN CỦA LỆNH KÝ, và một sổ cụm bỏ qua cho chỗ dấu không tách được.

TRƯỚC ĐỢT NÀY KHÔNG CÓ MỘT PHÉP THỬ NÀO CHẠM `tim_tu_do`. Bộ dò từ nhạy cảm chạy mười tám ngày
mà không hàng rào nào đọc nó, và chỗ hỏng chỉ lộ ra khi Chủ tịch mở màn hình bằng mắt ngày
11/11/2026 — mười sáu tin trong hàng đợi, cả mười sáu đều là báo sai.

Tệp này KHÔNG nằm trong 17 tệp của việc `hang-rao-gop` trên CI. Nó được chạy ở lượt hai của
vòng MKT-9, cùng chỗ `test_trang_phan_he` và `test_ban_mkt` đang chạy. Có nên đưa vào hàng rào
hay không là một quyết định để Chủ tịch chốt sau, không phải thứ đợt này tự nhận.

PHẦN ĐO ĐƯỢC NẰM Ở `test_16_tin_do_duoc_tren_ban_that_khong_con_bao_sai`: mười sáu tin ấy là
mười sáu tin THẬT, chép nguyên văn khỏi hàng đợi lúc 11/11/2026 (bỏ tên khách). Chúng ở đây để
con số 16 không phải một câu kể trong sổ mà là một thứ chạy lại được.
"""
from __future__ import annotations

import unicodedata

from app.services.loc_khung_hoang import DIEM_TU_DO, cham_diem, tim_tu_do
from app.services.rules import DEFAULT_PARAMS


def _ky(ten: str) -> list[str]:
    """Đọc giá trị ĐÃ KÝ của một tham số từ bảng mặc định, tách y như `loc_khung_hoang` tách."""
    for k, v, *_ in DEFAULT_PARAMS:
        if k == ten:
            return [unicodedata.normalize("NFC", x.strip().lower())
                    for x in str(v).split(",") if x.strip()]
    raise AssertionError("không thấy tham số %s trong DEFAULT_PARAMS" % ten)


DS = _ky("pr_tu_do")
BO = _ky("pr_cum_bo_qua")

# Mười sáu tin THẬT trong hàng đợi 7 ngày, đọc lúc 11/11/2026. Cả mười sáu đều vô hại.
MUOI_SAU_TIN = [
    "Điều kiện visa du lịch cần những gì",
    "Dự kiến nhóm chị đi Mũi né ngày 20;21;22/11 (thứ 6;7;cn)",
    "Có tua vĩnh hy hoặc bình hưng đi mùng 5 đến mùng 8 tháng 2 năm 2027 thì bảo chị",
    "Cô định đi 4 ngày3 đêm . Cô chú lớn tuổi . Dự kiến đi ngày 3/12. Cho hỏi có xe tốt hơn ko",
    "Khi nào có lịch 2027 báo chị nhé",
    "Dự kiến nhóm chị đi Mũi né ngày 20;21;22/11 (thứ 6;7;cn)",
    "Khi nào có lịch Đà Lạt - Phan Thiết Tết thì báo chị liền nha",
    "Khi nào có báo chị hay nha",
    "ngay 23/11, nếu tổ chức dc thì chi dky",
    "Cho chị chương trình và giá tour nha.Dự kiến đi vào tháng 12/2026",
    "Chụp từng tờ để xem, chứ ko mở đc . Thks em",
    "Dự kiến đi 3 người lớn!",
    "Theo dõi trang để khi nào có điều kiện thì mình đk",
    "Bên mình có tour nào đi trong ngày không ạ, dự kiến đi thứ 2 tuần sau xuất phát HCM",
    "Dự kiến đi hai người. Nếu ngày mai tua Nha Trang còn vé",
    "Tour CN về lại SG dự kiến mấy giờ ạ?",
]


def test_bon_tu_duoc_ky_co_dau_va_hai_muoi_tu_con_lai_khong():
    """Bốn từ đã ký lại có dấu, hai mươi từ còn lại cố ý để không dấu.

    Khoá con số này lại để một lần sửa danh sách sau là một lần sửa CÓ CHỦ Ý: thêm dấu cho một từ
    là siết nó, bỏ dấu đi là nới nó, và cả hai đều đổi những tin nào vào hàng đợi.
    """
    co_dau = [t for t in DS if unicodedata.normalize("NFD", t) != t or "đ" in t]
    assert sorted(co_dau) == ["báo chí", "kiện", "nhà báo", "tố"], co_dau
    assert len(DS) == 23, DS
    for t in ["lua dao", "to cao", "khieu nai", "luat su", "cong an", "tay chay", "scandal"]:
        assert t in DS, t


def test_tu_ky_co_dau_khop_dung_dau():
    """«kiện» bắt «khởi kiện», không bắt «dự kiến» hay «ý kiến» — khác dấu là khác từ."""
    assert tim_tu_do("Tôi sẽ khởi kiện công ty", DS) == ["kiện"]
    assert tim_tu_do("Dự kiến nhóm chị đi Mũi Né", DS) == []
    assert tim_tu_do("ý kiến của chị thế nào", DS) == []
    assert tim_tu_do("Khi nào có lịch thì báo chị nhé", DS) == []
    assert tim_tu_do("Báo chí sắp đăng vụ này", DS) == ["báo chí"]
    assert tim_tu_do("nhà bao nhiêu người đi", DS) == []
    assert tim_tu_do("một nhà báo gọi cho tôi", DS) == ["nhà báo"]


def test_tu_ky_khong_dau_van_khop_moi_cach_go_dau():
    """Lỗ lệ của `bo_dau` được giữ nguyên: người đang bực gõ không dấu vẫn bắt được.

    Đây là nửa KHÔNG được mất của đợt này. Siết bằng dấu mà siết luôn cả nhóm từ không dấu thì
    bộ lọc chỉ còn bắt được những người còn đủ bình tĩnh để bật bộ gõ.
    """
    assert tim_tu_do("Công ty này lừa đảo", DS) == ["lua dao"]
    assert tim_tu_do("cong ty nay lua dao", DS) == ["lua dao"]
    assert tim_tu_do("Sẽ nhờ luật sư", DS) == ["luat su"]
    assert tim_tu_do("se nho luat su", DS) == ["luat su"]
    assert tim_tu_do("Đoàn bị bỏ rơi ở sân bay", DS) == ["bo roi"]
    assert tim_tu_do("nguoi ta ngo doc do an", DS) == ["ngo doc"]


def test_ranh_gioi_tu_van_con_hieu_luc():
    """«tố» không nằm trong «tốt»; khớp giữa chữ sinh ra một hàng đợi không ai mở."""
    assert tim_tu_do("Cho hỏi có xe tốt hơn không", DS) == []
    assert tim_tu_do("cháu vừa tốt nghiệp", DS) == []
    assert tim_tu_do("Tôi sẽ tố cáo lên công an", DS) == ["to cao", "cong an", "tố"]


def test_cum_bo_qua_huy_theo_cho_chu_khong_huy_ca_tin():
    """Chỗ dễ hỏng nhất của đợt này, và hỏng về phía nguy hiểm nếu làm sai.

    Một cụm bỏ qua chỉ huỷ lần khớp NẰM TRONG nó. Nếu nó huỷ cả tin thì ai biết luật chỉ cần gõ
    thêm hai chữ vô hại là tắt được bộ lọc — nên ca này giữ đúng điều ấy.
    """
    assert tim_tu_do("Điều kiện visa du lịch cần những gì", DS, BO) == []
    assert tim_tu_do("điều kiện gì, tôi sẽ khởi kiện", DS, BO) == ["kiện"]
    assert tim_tu_do("Tôi sẽ khởi kiện công ty", DS, BO) == ["kiện"]
    # Sổ rỗng thì bộ lọc chạy y như chưa có tham số này.
    assert tim_tu_do("Điều kiện visa du lịch cần những gì", DS, []) == ["kiện"]


def test_16_tin_do_duoc_tren_ban_that_khong_con_bao_sai():
    """CON SỐ CỦA ĐỢT NÀY: 16 trên 16 xuống 0, chấm lại bằng chính bộ lọc mới.

    Không tin nào trong mười sáu tin này có dốc hay quá hạn trả lời, nên điểm 0 nghĩa là chúng
    rơi hẳn khỏi hàng đợi ở ngưỡng đã ký là 2.
    """
    con_sai = [(t, tim_tu_do(t, DS, BO)) for t in MUOI_SAU_TIN if tim_tu_do(t, DS, BO)]
    assert con_sai == [], con_sai
    for t in MUOI_SAU_TIN:
        diem, ly_do = cham_diem(t, DS, cum_bo_qua_ds=BO)
        assert diem == 0, (t, diem, ly_do)


def test_tin_khung_hoang_that_van_dat_nguong():
    """Nửa còn lại của phép đo: siết xong thì tin thật vẫn phải vào.

    Ngưỡng đã ký là 2 và một từ đỏ cộng đúng 2, nên mỗi câu dưới đây tự nó đã đủ vào hàng đợi.
    """
    for s in ["Tôi sẽ khởi kiện công ty",
              "Công ty này lừa đảo, tôi đòi tiền",
              "cong ty nay lua dao",
              "Báo chí sắp đăng vụ này",
              "Tôi sẽ tố cáo lên công an",
              "Đoàn bị bỏ rơi ở sân bay",
              "Khách bị ngộ độc đồ ăn",
              "Sẽ nhờ luật sư",
              "se tay chay cong ty nay"]:
        diem, ly_do = cham_diem(s, DS, cum_bo_qua_ds=BO)
        assert diem >= DIEM_TU_DO, (s, diem, ly_do)
        assert any(l.startswith("Từ đỏ") for l in ly_do), (s, ly_do)


def test_cho_mat_da_biet_va_da_bao_chu_tich():
    """CHỖ MẤT, ghi ra đây để nó là một thứ đo được chứ không phải một câu hứa.

    Ký «kiện» có dấu thì một câu kiện tụng gõ KHÔNG DẤU không còn bắt được bằng chữ ấy. Đổi lại,
    nhóm từ không dấu còn nguyên, nên một tin thật gần như luôn vấp một từ khác — và tin dưới
    ngưỡng vẫn xem lại được bằng nút «Hạ ngưỡng xuống 1» trên màn hình.
    """
    assert tim_tu_do("toi se khoi kien cong ty", DS, BO) == []
    assert tim_tu_do("toi se kien, da nho luat su", DS, BO) == ["luat su"]
    assert tim_tu_do("toi se to cao cong ty nay", DS, BO) == ["to cao"]
