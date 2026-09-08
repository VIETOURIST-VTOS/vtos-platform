"""Hạng giấy phép lái xe và số chỗ ngồi được phép điều khiển.

Vì sao phải có bảng này thay vì so chuỗi trong hàm kiểm: Việt Nam đang có HAI hệ hạng cùng lưu hành
trên đường, và chúng ĐẢO NGHĨA của chữ D.

    Luật cũ (Luật GTĐB 2008, giấy cấp trước 01/01/2025)
        D  – ô tô chở người 10 đến 30 chỗ (kể cả chỗ người lái)
        E  – ô tô chở người TRÊN 30 chỗ
        F/FC – kéo rơ moóc, cấp thêm trên nền hạng đã có

    Luật mới (Luật TTATGTĐB 2024, giấy cấp từ 01/01/2025)
        D1 – 8 đến 16 chỗ (không kể chỗ người lái)
        D2 – 17 đến 29 chỗ
        D  – TRÊN 29 chỗ          ← chữ D nay là hạng CAO NHẤT cho xe khách

Một chiếc 45 chỗ: hạng D theo luật CŨ thì KHÔNG được lái, hạng D theo luật MỚI thì ĐƯỢC. Cùng một
chữ cái, hai kết luận ngược nhau, và không có cách nào phân biệt ngoài NGÀY CẤP của tấm giấy.

Đây không phải chuyện lý thuyết. Trong 11 giấy phép Chủ tịch gửi ngày 08/9/2026 có đúng hai tấm ghi
hạng D, và cả hai đều cấp sau 01/01/2025 (một tấm 23/08/2025, một tấm 10/01/2026, đều do Cục Cảnh
sát giao thông cấp) – tức là hạng cao nhất, lái được xe 45 chỗ. Đọc theo luật cũ thì hệ thống sẽ
chặn oan hai tài xế đủ điều kiện; đọc theo luật mới cho MỌI tấm giấy thì hệ thống sẽ cho một tài xế
hạng D cũ (tối đa 30 chỗ) cầm lái xe 45 chỗ. Cả hai chiều đều sai, nên phải xét theo ngày cấp.

NGUYÊN TẮC KHI KHÔNG ĐỦ DỮ LIỆU: thiếu hạng, hoặc thiếu ngày cấp mà hạng là chữ D trần, thì kết
luận là CHƯA ĐỦ DỮ LIỆU – không phải "đạt". Đây đúng chỗ dễ mặc định thành "không sao" rồi để một
người không đủ hạng cầm lái 45 khách.
"""
from datetime import date

# Ngày Luật Trật tự an toàn giao thông đường bộ 2024 có hiệu lực.
LUAT_MOI_TU = date(2025, 1, 1)

# Số chỗ TỐI ĐA (kể cả chỗ người lái) mà từng hạng được phép điều khiển. None = không giới hạn.
HANG_CU = {"B1": 9, "B2": 9, "B": 9, "C": 9, "D": 30, "E": None, "F": None,
           "FB2": 9, "FC": 9, "FD": 30, "FE": None}
HANG_MOI = {"B": 9, "C1": 9, "C": 9, "D1": 17, "D2": 30, "D": None,
            "BE": 9, "C1E": 9, "CE": 9, "D1E": 17, "D2E": 30, "DE": None}
# Hạng không chở người (xe tải, mô tô) – có mặt trên giấy nhưng không cho quyền chở khách.
HANG_KHONG_CHO_KHACH = {"A", "A1", "A2", "A3", "A4", "B1"}


def tach_hang(hang: str) -> list[str]:
    """'A1, E, FC' → ['A1', 'E', 'FC']. Giấy ghi nhiều hạng thì lấy hạng RỘNG NHẤT ở nơi dùng."""
    return [p.strip().upper() for p in str(hang or "").replace("/", ",").split(",") if p.strip()]


def so_cho_toi_da(hang: str, ngay_cap: date | None) -> tuple[int | None, str]:
    """Số chỗ tối đa hạng này được lái, và lý do đọc như vậy.

    Trả về (so_cho, giai_thich). so_cho None nghĩa là KHÔNG GIỚI HẠN; ném KhongDuDuLieu-ish bằng cách
    trả về (-1, lý do) khi không kết luận được – gọi bên ngoài phải xử lý riêng, không được coi là đạt.
    """
    ds = tach_hang(hang)
    if not ds:
        return -1, "Giấy phép chưa ghi hạng"
    moi = ngay_cap is not None and ngay_cap >= LUAT_MOI_TU
    # Chữ D trần mà không biết ngày cấp thì KHÔNG đoán: luật cũ tối đa 30 chỗ, luật mới không giới hạn.
    if ngay_cap is None and "D" in ds:
        return -1, ("Giấy ghi hạng D nhưng chưa có ngày cấp. Hạng D theo luật cũ tối đa 30 chỗ, theo "
                    "luật mới (từ 01/01/2025) là hạng cao nhất – không có ngày cấp thì không đọc được "
                    "tấm giấy này thuộc hệ nào.")
    bang = HANG_MOI if moi else HANG_CU
    ten_luat = "Luật TTATGTĐB 2024" if moi else "Luật GTĐB 2008"
    tot_nhat, co_hang_khach = 0, False
    for h in ds:
        if h in HANG_KHONG_CHO_KHACH:
            continue
        if h not in bang:
            continue
        co_hang_khach = True
        v = bang[h]
        if v is None:
            return None, f"Hạng {h} theo {ten_luat}: không giới hạn số chỗ"
        tot_nhat = max(tot_nhat, v)
    if not co_hang_khach:
        return 0, (f"Các hạng trên giấy ({', '.join(ds)}) không cho phép chở người theo {ten_luat}")
    return tot_nhat, f"Hạng {'/'.join(ds)} theo {ten_luat}: tối đa {tot_nhat} chỗ"
