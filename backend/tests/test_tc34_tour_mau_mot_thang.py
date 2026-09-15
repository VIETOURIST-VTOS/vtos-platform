# -*- coding: utf-8 -*-
"""TC-34 · Tour mẫu DL-0825 phải nằm GỌN trong một tháng — mọi ngày trong năm.

Ngày 15/9/2026 nhánh `main` đỏ mà không ai sửa gì: `test_hr.py::test_draft_from_seed` và
`::test_fleet_summary` cùng hỏng. Đo lại thì không phải lỗi mã — là lỗi LỊCH.

Dữ liệu mẫu rải bảy mốc của tour DL-0825 từ `today-20` tới `today-13`. Hai chỗ đọc tour ấy lấy kỳ
theo hai mốc khác nhau:

    bảng lương  `hr.month_tours`  → tháng của `kt_confirmed_at`        (today-14)
    đội xe      `fleet_summary`   → tháng của `DispatchOrder.date_to`  (theo ngày đi)

Khoảng tám ngày ấy bắc qua ranh giới tháng vào NGÀY 15–20 mỗi tháng, và lúc ấy hai chỗ nhìn vào
hai tháng khác nhau: bảng lương rỗng, doanh thu đội xe bằng 0, dù dữ liệu mẫu vẫn đủ.

Một bộ kiểm đỏ theo LỊCH chứ không theo MÃ là bộ kiểm tệ hơn không có: vài lần như thế thì không
ai phân biệt được "đỏ thật" với "đỏ tới ngày", và lúc có lỗi thật nó trôi qua.

Phép thử này chạy thử CẢ NĂM, không chỉ hôm nay — vì chạy hôm nay thì 80% số ngày nó xanh dù mã
vẫn sai, đúng cái bẫy đã để lọt lần trước.
"""
from datetime import date, timedelta

import pytest

from app.services.seed import neo_tour_mau

# Các mốc của tour mẫu, tính theo số ngày kể từ ngày neo. Giữ ĐÚNG thứ tự nghiệp vụ:
# đi → về → khóa sổ → Kế toán xác nhận → CNTT kiểm.
MOC = {"ngay_di": 4, "ngay_ve": 6, "khoa_so": 8, "kt_xac_nhan": 10, "cntt_kiem": 11}


def _ngay_trong_nam(nam: int):
    d = date(nam, 1, 1)
    while d.year == nam:
        yield d
        d += timedelta(days=1)


@pytest.mark.parametrize("nam", [2026, 2027, 2028])      # 2028 là năm nhuận
def test_moi_moc_cua_tour_mau_nam_trong_cung_mot_thang(nam):
    """Đây là phép thử chính. Lệch tháng một mốc là một bảng lương rỗng."""
    hong = []
    for hom_nay in _ngay_trong_nam(nam):
        neo = neo_tour_mau(hom_nay)
        thang = {(neo + timedelta(days=n)).strftime("%Y-%m") for n in MOC.values()}
        if len(thang) != 1:
            hong.append((hom_nay.isoformat(), sorted(thang)))
    assert not hong, (
        f"{len(hong)} ngày trong năm {nam} có tour mẫu bắc qua hai tháng. "
        f"Ví dụ: {hong[:3]}"
    )


@pytest.mark.parametrize("nam", [2026, 2027, 2028])
def test_thang_cua_tour_mau_dung_bang_ky_luong_ma_phep_thu_hr_tinh(nam):
    """`test_hr.py` tính kỳ lương bằng `today - 14`. Nếu tour mẫu không rơi đúng tháng ấy thì bảng
    lương của kỳ ấy rỗng — và đó chính là lỗi ngày 15/9/2026."""
    for hom_nay in _ngay_trong_nam(nam):
        ky_hr = (hom_nay - timedelta(days=14)).strftime("%Y-%m")
        neo = neo_tour_mau(hom_nay)
        kt = neo + timedelta(days=MOC["kt_xac_nhan"])
        assert kt.strftime("%Y-%m") == ky_hr, (
            f"{hom_nay}: kỳ test_hr tính là {ky_hr} nhưng Kế toán xác nhận tour mẫu ở "
            f"{kt:%Y-%m} — bảng lương kỳ ấy sẽ rỗng."
        )


@pytest.mark.parametrize("nam", [2026, 2027, 2028])
def test_moi_moc_deu_o_qua_khu(nam):
    """Tour mẫu là tour ĐÃ KHÓA. Một mốc rơi vào tương lai thì dữ liệu mẫu tự mâu thuẫn: chuyến
    chưa chạy mà Kế toán đã xác nhận."""
    for hom_nay in _ngay_trong_nam(nam):
        neo = neo_tour_mau(hom_nay)
        muon_nhat = neo + timedelta(days=max(MOC.values()))
        assert muon_nhat < hom_nay, f"{hom_nay}: mốc muộn nhất {muon_nhat} chưa xảy ra."


def test_thu_tu_nghiep_vu_khong_dao_lon():
    """Đi → về → khóa sổ → Kế toán xác nhận → CNTT kiểm. Đảo một bước là dữ liệu mẫu dạy sai quy
    trình cho mọi phép thử đọc nó."""
    thu_tu = ["ngay_di", "ngay_ve", "khoa_so", "kt_xac_nhan", "cntt_kiem"]
    so = [MOC[k] for k in thu_tu]
    assert so == sorted(so) and len(set(so)) == len(so), f"Thứ tự mốc sai: {list(zip(thu_tu, so))}"


def test_neo_luon_la_ngay_dau_thang():
    for hom_nay in _ngay_trong_nam(2026):
        assert neo_tour_mau(hom_nay).day == 1


def test_cach_cu_that_su_hong_o_ngay_15_den_20():
    """Canh ngược: chứng minh cách đếm lùi cũ (today-20 … today-13) ĐÚNG LÀ hỏng, và hỏng đúng
    những ngày nào. Không có phép thử này thì cách cũ có thể lặng lẽ quay lại.
    """
    hong = [d for d in _ngay_trong_nam(2026)
            if (d - timedelta(days=20)).month != (d - timedelta(days=13)).month]
    assert hong, "Cách cũ phải hỏng — nếu không thì phép thử này đã mất ý nghĩa."
    ngay = sorted({d.day for d in hong})
    assert ngay == [14, 15, 16, 17, 18, 19, 20], f"Khoảng hỏng của cách cũ: {ngay}"
    assert len(hong) == 84, f"Cách cũ hỏng {len(hong)} ngày/năm"
