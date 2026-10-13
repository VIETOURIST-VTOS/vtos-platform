# -*- coding: utf-8 -*-
"""Đợt DỌN-2 (13/10/2026) — HAI CHÂN ĐÁO HẠN MANG HAI TÊN NGHIỆP VỤ.

VÌ SAO CÓ TỆP NÀY, và vì sao nó đến muộn hai đợt

Đợt E3 (12/10) dựng khoá chống ghi sổ hai lần: nguồn + mã nguồn + loại nghiệp vụ. Đáo hạn ngân
hàng là HAI bút toán cùng một khế ước và CỐ Ý mang cùng một `source_ref` — cổng đáo hạn nhìn
thấy hai chân là một cặp nhờ đúng điều đó. Hai chân ấy cùng khai `nghiep_vu="khe_uoc_vay"`, nên
khoá coi chân thứ hai là bản sao của chân thứ nhất và chặn nó lại: cửa `POST /fin/dao-han` rồi
ghi sổ hai kỳ hỏng từ 12/10/2026.

Đợt DỌN-1 (13/10) đã sửa đúng hướng — khai hai tên nghiệp vụ `tra_goc_vay` và
`nhan_giai_ngan_vay` — nhưng chỉ sửa chỗ GỌI trong một tệp phép thử, và kèm theo một câu nói
SAI gửi Chủ tịch: "hôm nay chưa chặn ai, đường bị chặn chỉ tồn tại trong phép thử". Có một cửa
thật, và nó đang hỏng.

Vì sao đo thiếu: tìm chữ `dao_han` trong `app/` chỉ ra cổng cảnh báo, không ra chỗ GHI. Chỗ ghi
nằm ở `vay_but_toan.xem_truoc`, đặt `source_ref` bằng một BIỂU THỨC ĐIỀU KIỆN — tìm theo một chữ
thì không thấy một biểu thức. Ghi lại để đợt sau đi tìm "ai đang đặt khoá này" thì tìm theo
NGƯỜI GỌI, không theo tên.

ĐIỀU TỆP NÀY CANH: hai chân ra hai khoá khác nhau · hai chân vẫn chung một `source_ref` để cổng
đáo hạn còn nhìn thấy cặp · loại kỳ khác không bị đổi tên · và không ngoại lệ nào được mở thêm.
"""
import os
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_don2.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                              # noqa: E402

from app.services import chung_tu_loai as CTL              # noqa: E402
from app.services import vay_but_toan as VBT               # noqa: E402


def test_don2_1_hai_chan_dao_han_ra_hai_khoa_khac_nhau():
    """ĐÚNG chỗ hỏng của cửa `POST /fin/dao-han`: cùng nguồn, cùng mã nguồn, khác nghiệp vụ."""
    ref = "dao_han:DH-V12-001"
    k_tra = CTL.khoa("khe_uoc_vay", ref, VBT.NGHIEP_VU_THEO_KY["tra_goc"])
    k_nhan = CTL.khoa("khe_uoc_vay", ref, VBT.NGHIEP_VU_THEO_KY["nhan_vay"])
    assert k_tra and k_nhan and k_tra != k_nhan, (k_tra, k_nhan)


def test_don2_2_hai_ten_nghiep_vu_phai_co_trong_danh_muc():
    """Gõ một tên chưa khai thì `post_entry` ném lỗi ngay lúc ghi sổ — khai đủ hay đừng khai."""
    for ma in set(VBT.NGHIEP_VU_THEO_KY.values()):
        assert CTL.nghiep_vu_hop_le(ma) == ma
        assert CTL.chung_tu_cua(ma) == "PKT"


def test_don2_3_loai_ky_khac_khong_bi_doi_ten():
    """Trả lãi không đi thành cặp nên không cần tách tên — đổi nó là đổi thừa."""
    assert "tra_lai" not in VBT.NGHIEP_VU_THEO_KY
    assert VBT.NGHIEP_VU_THEO_KY.get("tra_lai", "khe_uoc_vay") == "khe_uoc_vay"


def test_don2_4_moi_loai_ky_ghi_so_duoc_deu_co_ten_nghiep_vu_hop_le():
    """Quét `QUY_UOC_THEO_KY` chứ không liệt kê tay: thêm một loại kỳ mới là bị soi ngay."""
    for ky in VBT.QUY_UOC_THEO_KY:
        ma = VBT.NGHIEP_VU_THEO_KY.get(ky, "khe_uoc_vay")
        assert CTL.nghiep_vu_hop_le(ma) == ma, f"loại kỳ {ky} trỏ tới tên nghiệp vụ chưa khai"


def test_don2_5_van_chung_mot_source_ref_de_cong_dao_han_nhin_thay_cap():
    """Đợt này KHÔNG được chữa bằng cách tách `source_ref` — tách là làm mù cổng đáo hạn."""
    t = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "app", "services", "vay_but_toan.py"), encoding="utf-8").read()
    assert 'f"dao_han:{s.ma_dao_han}"' in t, \
        "Hai chân phải giữ CHUNG một source_ref; cổng đáo hạn nhận ra cặp nhờ đúng chỗ ấy"


def test_don2_6_khong_mo_ngoai_le_nao_moi():
    assert set(CTL.KHONG_KHOA_SU_KIEN) == {"", "quy_tac:"}, (
        "Đợt DỌN-2 sửa bằng cách gọi đúng tên, không bằng cách bỏ khoá: "
        + repr(sorted(CTL.KHONG_KHOA_SU_KIEN)))
