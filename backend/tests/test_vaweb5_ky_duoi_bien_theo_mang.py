# -*- coding: utf-8 -*-
"""Đợt VA-WEB5 (13/10/2026) — CHUYẾN DƯỚI BIÊN KÝ THEO MẢNG, và chữ ký đã có phải đọc ra là đã có.

VÌ SAO CÓ TỆP NÀY

Đợt VA-WEB4 (12/10/2026) đi sửa đúng một bệnh: màn hình nói sai người ký. Nó sửa được ba cửa
chính sách, rồi mắc lại chính bệnh ấy ở cửa thứ tư — vì nó cho màn hình đọc bảng TĨNH
`VAI_KY_CAN["du_toan_duoi_bien"]` = (ptgd_doan, tgd), đúng cái dòng mà Đợt LG3 đã thay bằng
`can_ky_duoi_bien(mang)` ở cửa ký.

Đo được ngày 13/10/2026 trên chuyến **TL-BKK-1005** (Bangkok – Pattaya, tour LẺ nước ngoài,
dưới biên 10%, đang chờ duyệt). Màn hình chi tiết chuyến viết:

    "Chuyến dưới biên – cần đủ chữ ký theo luật: Phó TGĐ tour đoàn … · Tổng giám đốc …"

Luật LG3, Chủ tịch chốt 11/10/2026: chuyến dưới biên ký theo MẢNG — Đoàn thì P.TGĐ tour đoàn,
**Lẻ thì Giám đốc Kinh doanh**. Chuyến này mảng Lẻ, nên người phải ký là GĐ Kinh doanh.

LỖI THỨ HAI, tìm thấy trong lúc sửa lỗi thứ nhất: `da_ky_cua` chỉ đọc các cột `signed_<vai>`.
Bảng `tours` KHÔNG có cột `signed_gd_kd` — chữ ký của GĐ Kinh doanh nằm ở ô tên `nguoi_da_ky`
(Đợt LG3). Nên một chuyến lẻ mà GĐ Kinh doanh ĐÃ KÝ vẫn hiện ra là CHƯA KÝ. `tours.approve`
đọc đúng cả hai nguồn từ LG3; chỗ HIỆN thì chỉ đọc một. Lại đúng hình: chỗ CHẶN đúng, chỗ
HIỆN sai — và chỗ hiện sai là chỗ không có phép thử nào canh.

ĐIỀU TỆP NÀY CANH

1. Luật theo mảng: lẻ → GĐ Kinh doanh, đoàn → P.TGĐ tour đoàn, và vai đầu LUÔN là người đứng
   đầu phòng bán mảng ấy — so thẳng với `NGUOI_DUNG_DAU_PHONG` thay vì chép tay tên vai.
2. Chuyến không thuộc mảng nào thì NÓI RA, không đoán.
3. Chữ ký đọc đủ HAI nguồn, cho cả vai có cột lẫn vai không có cột.
4. Cửa ký và chỗ hiện phải gọi CHUNG một hàm — vế này mới là vế chặn đợt sau tái phạm, vì cả
   hai lỗi trên đều sinh ra từ việc có hai phép đọc riêng cho cùng một câu hỏi.
"""
import os
import re

import pytest

from app.models.core import ROLES
from app.services import chu_ky as CK

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HoSoGia:
    def __init__(self, **cot):
        for k, v in cot.items():
            setattr(self, k, v)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# LUẬT THEO MẢNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_vaweb5_1_chuyen_le_la_giam_doc_kinh_doanh():
    """ĐÚNG CHUYẾN TL-BKK-1005: mảng lẻ thì vai thứ nhất là GĐ Kinh doanh, KHÔNG phải P.TGĐ đoàn."""
    ra = CK.chu_ky_duoi_bien_de_hien("le", HoSoGia())
    assert [k["vai"] for k in ra] == ["gd_kd", "tgd"], ra
    assert "ptgd_doan" not in [k["vai"] for k in ra], \
        "Chuyến LẺ mà hiện P.TGĐ tour đoàn — đúng lỗi Đợt VA-WEB4 mắc ngày 12/10/2026"
    assert ra[0]["ten"] == ROLES["gd_kd"]


def test_vaweb5_2_chuyen_doan_van_la_ptgd_tour_doan():
    """Sửa mảng lẻ không được làm hỏng mảng đoàn."""
    ra = CK.chu_ky_duoi_bien_de_hien("doan", HoSoGia())
    assert [k["vai"] for k in ra] == ["ptgd_doan", "tgd"], ra


@pytest.mark.parametrize("mang", sorted(CK.PHONG_CUA_MANG))
def test_vaweb5_3_vai_dau_luon_la_nguoi_dung_dau_phong_ban(mang):
    """So thẳng với sổ người đứng đầu phòng, thay vì chép tay tên vai vào phép thử.

    Chép tay thì phép thử và mã cùng sai một kiểu nếu người viết hiểu sai luật — mà đó chính là
    chuyện đã xảy ra hôm qua.
    """
    ra = CK.chu_ky_duoi_bien_de_hien(mang, HoSoGia())
    phong = CK.PHONG_CUA_MANG[mang]
    assert ra[0]["vai"] == CK.NGUOI_DUNG_DAU_PHONG[phong]
    assert ra[-1]["vai"] == "tgd", "Vế thứ hai luôn là TGĐ"
    assert len(ra) == 2


def test_vaweb5_4_khong_thuoc_mang_nao_thi_noi_ra_chu_khong_doan():
    """Dịch vụ lẻ (non_package) không thuộc mảng nào. Đoán một phòng ở đây là đoán người chịu tiền."""
    with pytest.raises(ValueError) as ex:
        CK.chu_ky_duoi_bien_de_hien("", HoSoGia())
    assert "KHÔNG BIẾT" in str(ex.value)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỌC CHỮ KÝ — HAI NGUỒN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_vaweb5_5_vai_khong_co_cot_van_phai_doc_ra_da_ky():
    """CHÍNH LỖI THỨ HAI: `tours` không có cột `signed_gd_kd`, chữ ký nằm ở ô `nguoi_da_ky`."""
    t = HoSoGia(nguoi_da_ky="gd_kd:nam.nguyen")
    assert CK.da_ky_mot_vai(t, "gd_kd") is True
    ra = CK.chu_ky_duoi_bien_de_hien("le", t)
    assert ra[0]["da_ky"] is True, f"GĐ Kinh doanh đã ký mà vẫn hiện chưa ký: {ra}"
    assert ra[1]["da_ky"] is False, "TGĐ chưa ký thì phải nói là chưa"


def test_vaweb5_6_cot_cu_van_duoc_doc_ho_so_ky_do_giua_hai_dot():
    """Hồ sơ ký trước Đợt LG3 chỉ có cột boolean. Bỏ nguồn ấy là xoá một chữ ký đã có."""
    t = HoSoGia(signed_ptgd_doan=True, nguoi_da_ky="")
    assert CK.da_ky_mot_vai(t, "ptgd_doan") is True
    assert CK.da_ky_mot_vai(t, "tgd") is False
    ra = CK.chu_ky_duoi_bien_de_hien("doan", t)
    assert [k["da_ky"] for k in ra] == [True, False]


def test_vaweb5_7_khong_co_nguon_nao_thi_la_chua_ky():
    t = HoSoGia()
    assert CK.da_ky_mot_vai(t, "tgd") is False
    assert all(not k["da_ky"] for k in CK.chu_ky_duoi_bien_de_hien("le", t))


def test_vaweb5_8_ba_cua_chinh_sach_khong_bi_doi_hanh_vi():
    """Đợt này sửa cách ĐỌC chung, nên phải chứng minh ba cửa của VA-WEB4 vẫn y nguyên."""
    assert [k["vai"] for k in CK.chu_ky_de_hien("tham_so", HoSoGia(signed_chutich=True))] == ["chutich"]
    assert CK.chu_ky_de_hien("tham_so", HoSoGia(signed_chutich=True))[0]["da_ky"] is True
    assert [k["vai"] for k in CK.chu_ky_de_hien("quy_tac_hach_toan", HoSoGia())] == ["chutich", "tgd"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MỘT CÂU HỎI, MỘT PHÉP ĐỌC — vế chặn đợt sau tái phạm
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _doc(rel: str) -> str:
    return open(os.path.join(GOC, rel), encoding="utf-8").read()


def test_vaweb5_9_man_hinh_khong_con_doc_bang_tinh_cho_duoi_bien():
    """Bảng tĩnh `VAI_KY_CAN["du_toan_duoi_bien"]` đúng cho mảng Đoàn và SAI cho mảng Lẻ.

    Nó được giữ lại (phép thử LG2 đang canh dòng ấy), nhưng KHÔNG nơi nào được dùng nó để dựng
    dòng chữ ký cho một chuyến cụ thể.
    """
    t = _doc(os.path.join("backend", "app", "services", "tours.py"))
    assert 'chu_ky_de_hien("du_toan_duoi_bien"' not in t, (
        "tours.py đọc bảng tĩnh cho chuyến dưới biên — chuyến mảng Lẻ sẽ hiện sai người ký. "
        "Dùng `chu_ky_duoi_bien_de_hien(SEG.mang_of(t), t)`.")
    assert "_CK.chu_ky_duoi_bien_de_hien(" in t


def test_vaweb5_10_cua_ky_va_cho_hien_doc_chung_mot_ham():
    """Hai phép đọc riêng cho cùng một câu hỏi là nguồn của cả hai lỗi đợt này đi sửa."""
    t = _doc(os.path.join("backend", "app", "services", "tours.py"))
    assert "_CK.da_ky_mot_vai(t, v)" in t, "tours.approve phải dùng chung phép đọc chữ ký"
    assert not re.search(r"bool\(getattr\(t, f\"signed_\{v\}\"", t), \
        "tours.py còn một bản sao của phép đọc chữ ký trong thân hàm"


def test_vaweb5_11_man_hinh_phai_co_cho_noi_ra_khi_khong_biet_ai_ky():
    """Chuyến không thuộc mảng nào mà màn hình im lặng thì nó nằm chờ không ai biết chờ ai."""
    w = _doc(os.path.join("web", "app", "tours", "[id]", "page.tsx"))
    assert "chu_ky_duoi_bien_vuong" in w, "Màn hình chưa hiện câu vướng"
    assert w.index("chu_ky_duoi_bien_vuong") < w.index("KyO ky={t.chu_ky_duoi_bien}"), \
        "Câu vướng phải đứng TRƯỚC danh sách chữ ký"


def test_vaweb5_12_tour_view_tra_du_hai_o():
    """Đo chính cửa: `tour_view` phải gửi cả danh sách lẫn câu vướng, không thiếu ô nào."""
    t = _doc(os.path.join("backend", "app", "services", "tours.py"))
    assert '"chu_ky_duoi_bien_vuong"' in t
    assert "def _chu_ky_duoi_bien(" in t
