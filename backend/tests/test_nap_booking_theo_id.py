# -*- coding: utf-8 -*-
"""Kéo booking còn thiếu THEO ID — gỡ 227 phiếu thu treo vì "chưa có booking".

VÌ SAO CÓ TỆP NÀY

Đo 26/9/2026 trên hệ thật: 227 phiếu thu/chi Vietrip nằm treo, tổng 1.519.979.111 đ, tất cả cùng
một lý do "chưa có booking". Cả 227 phiếu đều MANG mã booking — 183 booking khác nhau, id từ 95241
đến 127507 — chỉ là VTOS chưa có chúng, vì robot kéo booking theo NGÀY ĐẶT với cửa sổ 7 ngày còn
khách thì đặt tháng 3 trả tiền tháng 9.

Không có gì đỏ lên: bộ ánh xạ xếp chúng vào rổ "blocked" chứ không phải "lỗi". Một tỷ rưỡi nằm im
mà mọi con số trông vẫn bình thường.

PHÉP THỬ QUAN TRỌNG NHẤT là `test_dung_ngay_khi_lui_qua_id_nho_nhat`. Cửa `/api/booking/search`
không nhận bộ lọc nào ngoài khoảng ngày (đo 26/9: thử bookingID, recID, tourcode, search[value] —
cả bốn đều trả nguyên 122.783 dòng). Nên phải lật trang. Lật mà không biết dừng thì mỗi lần gọi
là 122.783 dòng kéo qua một máy chủ 512 MB vốn đã tự khởi động lại khi quá bộ nhớ.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json                                                     # noqa: E402
import pytest                                                   # noqa: E402
from app.services import vietrip_client as VC                   # noqa: E402


class GiaClient:
    """Giả cửa /api/booking/search: trả recID GIẢM DẦN, 1.000 dòng mỗi trang, như Vietrip thật."""

    def __init__(self, ids: list[int], moi_trang: int = 1000):
        self.ids = sorted(ids, reverse=True)
        self.moi_trang = moi_trang
        self.goi = []

    def get(self, path: str, timeout: int = 90) -> str:
        self.goi.append(path)
        start = int(path.split("start=")[1].split("&")[0])
        lo = self.ids[start:start + self.moi_trang]
        return json.dumps({"data": [{"recID": i, "tourcode": f"T{i}", "tenNguoiBook": "KHACH",
                                     "phone": "0900000000", "totalDue": 1000} for i in lo]})


@pytest.fixture()
def gia(monkeypatch):
    """Thay chỗ đăng nhập và chỗ ghi CSDL — phép thử này soi VÒNG LẬT TRANG, không soi hai thứ kia."""
    kho = {"da_upsert": []}
    monkeypatch.setattr(VC.VT, "upsert", lambda db, e, rows: kho["da_upsert"].extend(rows))
    def dat(c):
        monkeypatch.setattr(VC, "_dang_nhap", lambda: c)
        return c
    return dat, kho


def test_tim_thay_booking_o_trang_dau(gia):
    dat, kho = gia
    c = dat(GiaClient(list(range(1000, 3000)), moi_trang=1000))
    kq = VC.nap_booking_theo_id(None, [2999, 2500, 2100])
    assert kq["tim_thay"] == 3 and kq["con_thieu"] == []
    assert len(kho["da_upsert"]) == 3


def test_dung_ngay_khi_lui_qua_id_nho_nhat(gia):
    """Phép thử chính: lật tới trang chứa id nhỏ nhất là DỪNG, không quét nốt phần còn lại.

    Vietrip có 122.783 booking. Lật hết là kéo 123 trang qua một máy chủ 512 MB — đúng thứ đã làm
    40 tệp nạp hỏng 502 hôm 19/9.
    """
    dat, kho = gia
    c = dat(GiaClient(list(range(1, 10001)), moi_trang=1000))   # id 10000 → 1, tức 10 trang

    # MỘT id KHÔNG CÓ THẬT là điều kiện bắt buộc của phép thử này. Nếu tìm thấy hết thì vòng lặp
    # tự dừng vì `con_tim` rỗng, và nhánh "lùi qua id nhỏ nhất" không bao giờ được dùng tới —
    # bản đầu của phép thử này chỉ tìm hai id có thật, nên bỏ hẳn nhánh ấy đi mà nó vẫn xanh.
    kq = VC.nap_booking_theo_id(None, [9500, 999999])

    assert kq["tim_thay"] == 1 and kq["con_thieu"] == [999999]
    # Trang 1 phủ id 10000→9001, đã lùi qua 9500 nên phải dừng NGAY, không quét 9 trang còn lại.
    assert kq["so_trang"] == 1, f"lật {kq['so_trang']} trang – không biết dừng"
    assert len(c.goi) == 1


def test_id_khong_co_that_thi_noi_ra_chu_khong_im(gia):
    dat, kho = gia
    dat(GiaClient(list(range(1, 2001)), moi_trang=1000))
    kq = VC.nap_booking_theo_id(None, [1500, 999999])
    assert kq["tim_thay"] == 1
    assert 999999 in kq["con_thieu"], "id không tìm thấy phải được nêu tên"


def test_danh_sach_rong_thi_khong_goi_vietrip(gia):
    dat, kho = gia
    c = dat(GiaClient([1, 2, 3]))
    kq = VC.nap_booking_theo_id(None, [])
    assert kq == {"can_tim": 0, "tim_thay": 0, "so_trang": 0, "con_thieu": []}
    assert c.goi == [], "không có gì để tìm mà vẫn gọi ra Vietrip"


def test_co_phanh_khong_lat_vo_han(gia):
    """Máy chủ trả trang đầy mãi mãi (id không bao giờ lùi qua mốc): phải dừng ở TRAN_TRANG_BOOKING."""
    class KhongBaoGioHet(GiaClient):
        def get(self, path, timeout=90):
            self.goi.append(path)
            return json.dumps({"data": [{"recID": 500000 + len(self.goi) * 1000 + i}
                                        for i in range(1000)]})
    dat, kho = gia
    c = dat(KhongBaoGioHet([]))
    kq = VC.nap_booking_theo_id(None, [1])
    assert kq["so_trang"] == VC.TRAN_TRANG_BOOKING
    assert kq["con_thieu"] == [1]


def test_khong_truyen_khoang_ngay_nao(gia):
    """Cửa này lần theo ID, KHÔNG theo ngày — nên nó không chạm vào mốc 01/08/2026.

    Nếu một bản sửa sau này thêm bookingDateFrom vào đây thì mốc lại chặn mất booking tháng 3, và
    1,5 tỷ quay về chỗ treo cũ mà không ai hiểu vì sao.
    """
    dat, kho = gia
    c = dat(GiaClient(list(range(1, 2001))))
    VC.nap_booking_theo_id(None, [1500])
    assert c.goi, "chưa gọi lần nào"
    for p in c.goi:
        assert "bookingDate" not in p, f"đã lẻn khoảng ngày vào: {p}"
        assert "fromDate" not in p, f"đã lẻn khoảng ngày vào: {p}"
