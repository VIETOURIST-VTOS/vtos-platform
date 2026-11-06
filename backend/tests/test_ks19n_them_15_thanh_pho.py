# -*- coding: utf-8 -*-
"""KS-19n · thêm 15 điểm đến vào danh mục thành phố (Chủ tịch chọn «thêm theo thành phố» 06/11/2026) để Điều hành nhập
21 khách sạn 4–5★ còn thiếu điểm đến của đợt 34 tỉnh, thành. Lề cũ giữ nguyên: thành phố lớn, không phải tỉnh."""
import pytest

MOI = {"Bắc Ninh": "bac", "Thái Nguyên": "bac", "Lạng Sơn": "bac", "Hưng Yên": "bac", "Thái Bình": "bac", "Tam Đảo": "bac",
       "Việt Trì": "bac", "Sơn La": "bac", "Lai Châu": "bac", "Điện Biên Phủ": "bac", "Hà Tĩnh": "trung", "Lý Sơn": "trung",
       "Tây Ninh": "nam", "Biên Hòa": "nam", "Mỹ Tho": "nam"}


def test_ks19n_1_co_du_15_diem_dung_mien():
    from app.services.nha_hang import THANH_PHO
    for ten, mien in MOI.items():
        assert THANH_PHO[ten][0] == mien, ten
    assert len(THANH_PHO) == 47


@pytest.mark.parametrize("nguon,ra", [("Muong Thanh Luxury Bac Ninh, Bac Ninh", "Bắc Ninh"), ("Ky Anh, Ha Tinh", "Hà Tĩnh"),
                                      ("Bien Hoa, Dong Nai", "Biên Hòa"), ("My Tho, Tien Giang", "Mỹ Tho"),
                                      ("Viet Tri, Phu Tho", "Việt Trì"), ("Moc Chau, Son La", "Mộc Châu"),
                                      ("Dien Bien Phu", "Điện Biên Phủ"), ("Tam Dao, Vinh Phuc", "Tam Đảo")])
def test_ks19n_2_quy_dia_danh_nguon(nguon, ra):
    from app.services.nha_hang import tinh_tu_nguon
    assert tinh_tu_nguon(nguon) == ra


def test_ks19n_3_khach_san_nhan_diem_moi():
    from app.services.khach_san_vtd import THANH_PHO
    assert "Lý Sơn" in THANH_PHO and "Tây Ninh" in THANH_PHO
