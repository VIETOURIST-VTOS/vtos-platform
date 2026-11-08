# -*- coding: utf-8 -*-
"""P0-03 (Chủ tịch chọn «Sửa nhãn cho thống nhất», duyệt 09/11/2026).

KS-19 (05/11/2026) chốt: giá khách sạn VTD Điều hành nhập ĐÃ GỒM 8% VAT, máy không cộng thuế phí. Rà ngày 09/11:
màn crm Khách sạn VTD vẫn còn ba nhãn «chưa thuế phí» (dòng giới thiệu, ô giường phụ, tiêu đề cột mùa giá) cạnh
nhãn «ĐÃ GỒM 8% VAT» ở ô nhập mùa giá — người nhập dễ trừ VAT hai lần. Chỉ sửa chữ; cách tính tiền giữ nguyên."""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _doc(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def test_p0_03_1_man_crm_khong_con_nhan_chua_thue():
    src = _doc("web", "app", "khach-san-vtd", "page.tsx")
    assert "chưa thuế phí" not in src
    assert src.count("đã gồm 8% VAT") >= 3 and "ĐÃ GỒM 8% VAT" in src


def test_p0_03_2_may_van_khong_cong_thue():
    from app.services import khach_san_vtd as S
    assert S.VAT_PT == 8 and S.vat_trong(108_000) == 8_000      # VAT nằm TRONG giá, không cộng thêm
