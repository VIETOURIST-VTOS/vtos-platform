# -*- coding: utf-8 -*-
"""KS-16j · Form loại phòng + chính sách trẻ em kiểu Agoda (Chủ tịch duyệt bản xem thử 01/11/2026).

  1. Đặc điểm ngắn quá 300 ký tự → báo lỗi, không tự cắt; mô tả chi tiết ≤3.000.
  2. Số phòng VTD 0 lưu là 0; «Đang bán» cần ≥1. Trẻ em để trống = chưa xác nhận (None), khác 0.
  3. Nguồn & đối chiếu lưu nguyên; trạng thái Điều hành tự ghi, không chặn bán.
  4. (Chính sách trẻ em: xem KS-16k.)
"""
import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import _ks


def test_form_loai_phong(db):
    from app.services import khach_san_vtd as S
    k = _ks(db)
    u = _u(db, "dh")
    with pytest.raises(S.LoiKhachSan, match="412/300"):
        S.luu_loai_phong(db, u, k.id, {"ten": "Superior", "mo_ta": "x" * 412, "so_phong": 1})
    with pytest.raises(S.LoiKhachSan, match="≥ 1"):
        S.luu_loai_phong(db, u, k.id, {"ten": "Superior", "so_phong": 0})
    lp = S.luu_loai_phong(db, u, k.id, {"ten": "Superior Double Room", "mo_ta": "Cửa sổ mở được", "mo_ta_dai": "y" * 2500,
                                        "so_phong": 0, "dang_ban": False, "toi_da_tre_em": "", "tien_nghi": ["Máy lạnh", "Wifi", "Wifi"],
                                        "nguon": "agoda", "ky_doi_chieu": "10–11/12/2026", "ma_hang": "", "ten_tuong_duong": "Superior",
                                        "can_xac_nhan": ["ten_hang", "tre_em", "han_muc"], "ghi_chu_doi_chieu": "Cửa sổ mâu thuẫn",
                                        "trang_thai_dc": "dang_doi_chieu"})
    db.refresh(lp)
    assert lp.so_phong == 0 and lp.toi_da_tre_em is None and len(lp.mo_ta_dai) == 2500
    assert lp.tien_nghi == ["Máy lạnh", "Wifi"] and lp.nguon == "agoda" and lp.can_xac_nhan == ["ten_hang", "tre_em", "han_muc"]
    lp = S.luu_loai_phong(db, u, k.id, {"ten": "Superior Double Room", "so_phong": 0, "dang_ban": False, "toi_da_tre_em": 0}, lp.id)
    assert lp.toi_da_tre_em == 0                                  # 0 là «không nhận» — đã xác nhận
    with pytest.raises(S.LoiKhachSan, match="Nguồn"):
        S.luu_loai_phong(db, u, k.id, {"ten": "X1", "so_phong": 1, "nguon": "expedia"})
    with pytest.raises(S.LoiKhachSan, match="3000"):
        S.luu_loai_phong(db, u, k.id, {"ten": "X1", "so_phong": 1, "mo_ta_dai": "z" * 3001})
    v = S.mot_vtos(db, u, k.id)["loai_phong"][0]
    assert v["ky_doi_chieu"] == "" and v["trang_thai_dc"] == "" and v["toi_da_tre_em"] == 0

# Phần chính sách trẻ em / phụ thu: KS-16k thay cách tính theo Agoda YCS — xem test_ks16k_gia_tre_em_agoda.py
