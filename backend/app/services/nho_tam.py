# -*- coding: utf-8 -*-
"""NHỚ TẠM — một chỗ nhớ kết quả của những cửa tính nặng, dùng chung cho cả hệ thống.

══════════════════════════════════════════════════════════════════════════════════════════════
TC-64 · VÌ SAO CÓ TỆP NÀY — ANH TUẤN QUAY MÀN HÌNH LẠI 18/9/2026: "kiểm tra lý do load rất chậm"
══════════════════════════════════════════════════════════════════════════════════════════════
Đo thật bằng trình duyệt, mỗi cửa gọi ba lần liên tiếp (18/9/2026, vtos.infinitytours.org):

    /bao-cao/ket-qua-kinh-doanh   2,19s   2,28s   1,66s
    /dong-tien/khung/1            1,83s   2,60s   0,87s
    /dashboard                    8,04s   0,25s   0,25s     ← đã có chỗ nhớ từ trước
    /alerts                       0,87s   0,95s   1,30s
    /auth/me                      0,46s   0,24s   0,23s

Trang HTML về trong 0,2 giây, nên chậm KHÔNG nằm ở mạng hay trình duyệt. Ba nguyên nhân:

 1. `ket-qua-kinh-doanh` hỏi cùng một câu ba lần. Nó đọc 12 tháng, và với MỖI tháng gọi
    `ket_qua_that.thang()` ba lượt riêng biệt (phần "còn thiếu", doanh thu, lợi nhuận tour) —
    cùng một tháng, cùng một câu hỏi, hỏi máy ba lần. Cộng 12 lượt dựng báo cáo kết quả kinh
    doanh đầy đủ và 12 lượt đọc kế hoạch: khoảng 60 lượt xuống cơ sở dữ liệu cho MỘT lần mở
    màn hình. Chỗ ấy chữa bằng cách nhớ trong PHẠM VI MỘT LẦN GỌI — xem `ket_qua_kinh_doanh.bang`.
 2. Máy chủ chỉ có nửa lõi CPU (gói Render 0,5 CPU / 512 MB). Mở màn hình bắn bảy cửa cùng lúc;
    hai cửa nặng ăn hết nửa lõi ấy nên `/dashboard` vốn chạy 0,25 giây bị XẾP HÀNG thành 8 giây.
    Con số 8,04s ở trên là nó đứng chờ, không phải nó chậm.
 3. `/dong-tien/meta` phải xong mới biết mã pháp nhân để gọi `/dong-tien/khung/1` — hai cửa nối
    đuôi nhau cộng thêm ~2,5 giây vào cuối.

Tệp này chữa nguyên nhân 2 và 3 CÙNG MỘT LÚC, mà không đụng tới tiền: hai cửa nặng thôi tính lại
từ đầu mỗi lần bấm F5, nên chúng không còn ăn hết nửa lõi CPU nữa, và chuỗi nối đuôi ở nguyên nhân
3 rút xuống còn hai lần đọc chỗ nhớ.

══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO MỘT TỆP CHUNG CHỨ KHÔNG BA CHỖ NHỚ RIÊNG
══════════════════════════════════════════════════════════════════════════════════════════════
`/dashboard` đã có một chỗ nhớ 5 phút viết thẳng trong api/v1/routes.py từ trước. Viết thêm hai
chỗ nhớ nữa, mỗi chỗ một kiểu, là ba bản chép của cùng một phép tính thời gian — và ba bản chép
thì sớm muộn lệch nhau (đúng lý lẽ đã dùng khi gom bốn bản vẽ biểu đồ về một bộ ở TC-40). Nên
`_DASH_CACHE` cũng chuyển sang dùng tệp này.

══════════════════════════════════════════════════════════════════════════════════════════════
BA LUẬT CỦA MỘT CHỖ NHỚ, VÀ VÌ SAO TỪNG LUẬT
══════════════════════════════════════════════════════════════════════════════════════════════
1. KHOÁ PHẢI MANG VAI TRÒ nếu con số đổi theo vai. SEC-02 nói máy chủ cắt tập dòng theo vai; một
   chỗ nhớ quên vai là cách chắc chắn nhất để Tổng giám đốc nhận lại đúng gói vừa dựng cho Chủ
   tịch. Hàm `khoa_vai` dưới đây bắt người gọi phải nêu vai ra.
2. PHẢI CÓ CỬA LÀM MỚI. Người vừa bấm "Chốt số dư" mà màn hình vẫn hiện số cũ suốt năm phút thì
   họ sẽ bấm lại lần nữa — và lần ấy mới là cái sai thật. Mọi cửa dùng chỗ nhớ đều nhận
   `refresh=true`, và cửa GHI nào đổi số thì tự gọi `xoa` đúng kho của nó.
3. KHÔNG NHỚ CÁI ĐANG LỖI. Một ngoại lệ không được ghi vào kho: nhớ một lỗi năm phút là biến một
   trục trặc thoáng qua thành năm phút hỏng. Nên `dat` chỉ được gọi sau khi đã có kết quả.

CHỖ NHỚ NÀY NẰM TRONG BỘ NHỚ CỦA MỘT TIẾN TRÌNH. Máy chủ chạy nhiều tiến trình thì mỗi tiến trình
một kho — không sai, chỉ là tỉ lệ trúng thấp hơn. Ghi ra đây để vòng sau không đi tìm một kho
chung tưởng tượng.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Hashable

# Năm phút — lấy đúng con số `/dashboard` đã dùng từ trước, không đặt một con số thứ hai.
SONG_GIAY = 300


class Kho:
    """Một kho nhớ tạm có tên. Tên chỉ để đọc nhật ký và để gỡ rối, không tham gia vào khoá."""

    def __init__(self, ten: str, song_giay: int = SONG_GIAY) -> None:
        self.ten = ten
        self.song_giay = song_giay
        self._o: dict[Hashable, tuple[float, Any]] = {}

    def lay(self, khoa: Hashable) -> Any | None:
        """Trả gói còn hạn, hoặc None. None nghĩa là 'chưa có / đã hết hạn', không phải 'rỗng'."""
        o = self._o.get(khoa)
        if o is None:
            return None
        if time.time() - o[0] >= self.song_giay:
            self._o.pop(khoa, None)
            return None
        return o[1]

    def dat(self, khoa: Hashable, gia_tri: Any) -> Any:
        """Ghi và TRẢ LẠI chính giá trị ấy, để chỗ gọi viết được `return kho.dat(k, tinh())`."""
        self._o[khoa] = (time.time(), gia_tri)
        return gia_tri

    def xoa(self, loc: Callable[[Hashable], bool] | None = None) -> int:
        """Xoá cả kho, hoặc chỉ những khoá mà `loc` nhận.

        Cửa GHI gọi hàm này. Ví dụ: chốt số dư của pháp nhân 3 thì xoá mọi khoá có 3 trong đó —
        không cần biết có bao nhiêu vai trò đã từng mở, vì khoá nào cũng mang mã pháp nhân.
        """
        if loc is None:
            n = len(self._o)
            self._o.clear()
            return n
        bo = [k for k in self._o if loc(k)]
        for k in bo:
            self._o.pop(k, None)
        return len(bo)

    def cac_khoa(self) -> list[Hashable]:
        """Khoá đang có — dùng cho vòng lặp robot dựng sẵn (xem `lam_moi_cache_nen`)."""
        return list(self._o.keys())

    def __len__(self) -> int:
        return len(self._o)


def khoa_vai(vai: str, *phan: Hashable) -> tuple:
    """Khoá của một gói ĐỔI THEO VAI. Bắt nêu vai ra thành một tham số riêng, chứ không để lẫn
    vào `phan`: quên một phần tử trong `phan` thì chỉ trúng ít đi, quên VAI thì lộ dữ liệu."""
    return (vai, *phan)
