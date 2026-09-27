# -*- coding: utf-8 -*-
"""Robot Vietrip KHÔNG được chạm vào tháng 1–7/2026.

VÌ SAO CÓ TỆP NÀY

Tháng 1 đến tháng 7/2026 trên VTOS là số CHỐT: 604 tệp quyết toán gốc của Điều hành, nạp qua cửa
có người ký, đóng số xong. Ngày 12/9/2026 Chủ tịch ra lệnh xoá phần Vietrip của khoảng ấy vì
"số trên Vietrip từ T1 đến T6 không chính xác". Ngày 26/9/2026 Chủ tịch chốt robot chỉ nạp từ
tháng 8 trở đi.

Robot chạy HAI LƯỢT MỖI NGÀY. Chỉ cần một lần gọi tay với `from_date` cũ, hoặc một lần sửa mã đặt
nhầm cửa sổ mặc định, là hai tháng số chốt bị đè bằng đúng nguồn đã bị bác — và không có gì đỏ lên.
Đó là hình dạng lỗi mà cả kho này được dựng ra để chặn: sai mà vẫn ra một con số trông bình thường.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest                                              # noqa: E402
from fastapi import HTTPException                          # noqa: E402
from app.api.v1.vietrip import MOC_SOM_NHAT, SyncIn, _dates  # noqa: E402


def test_moc_dung_ngay_chu_tich_chot():
    assert MOC_SOM_NHAT == date(2026, 8, 1)


def test_goi_voi_ngay_cu_bi_keo_ve_moc():
    """Truyền 01/01/2026 vào thì phải bị kéo về 01/08 — KHÔNG được kéo dữ liệu tháng 1."""
    f, t = _dates(SyncIn(from_date="2026-01-01", to_date="2026-09-26"))
    assert f == MOC_SOM_NHAT, "đã để lọt xuống trước mốc"
    assert t == date(2026, 9, 26)


def test_ca_khoang_nam_truoc_moc_thi_tu_choi_han():
    """T1–T7 trọn vẹn: không im lặng trả về khoảng rỗng, mà nói thẳng là không nạp."""
    with pytest.raises(HTTPException) as e:
        _dates(SyncIn(from_date="2026-01-01", to_date="2026-07-31"))
    assert e.value.status_code == 400
    assert "01/08/2026" in e.value.detail


def test_ngay_sau_moc_thi_giu_nguyen():
    f, t = _dates(SyncIn(from_date="2026-08-15", to_date="2026-09-26"))
    assert f == date(2026, 8, 15) and t == date(2026, 9, 26)


def test_khong_truyen_gi_thi_lay_bay_ngay_gan_nhat():
    """Cửa sổ mặc định của lịch chạy hai lượt/ngày: 7 ngày gần nhất, không đụng tới mốc."""
    f, t = _dates(SyncIn())
    assert t == date.today()
    assert f == max(MOC_SOM_NHAT, date.today() - timedelta(days=7))


def test_moc_chan_ca_khi_chi_truyen_from_date():
    f, t = _dates(SyncIn(from_date="2025-11-01"))
    assert f == MOC_SOM_NHAT


@pytest.mark.parametrize("ngay", ["2026-07-31", "2026-07-01", "2026-06-15", "2026-02-01"])
def test_moi_ngay_trong_T1_T7_deu_bi_keo_ve_moc(ngay):
    """Phải chặn MỌI ngày trong T1–T7, không riêng tháng 1.

    Phép thử đầu chỉ thử 01/01 — nên một bản sửa đặt mốc lệch 60 ngày vẫn xanh, trong khi nó để
    lọt nguyên tháng 6 và tháng 7. Tháng 7 là chỗ đau nhất: 37 tệp T7 vừa nạp xong qua cửa có
    người ký, đè lên là mất đúng phần mới làm.
    """
    f, t = _dates(SyncIn(from_date=ngay, to_date="2026-09-26"))
    assert f == MOC_SOM_NHAT, f"{ngay} lọt qua mốc, f = {f}"
