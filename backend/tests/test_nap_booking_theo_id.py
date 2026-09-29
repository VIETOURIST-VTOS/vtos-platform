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
        # Đọc ĐÚNG `length` của đường dẫn chứ không dùng kích thước trang của riêng mình: máy chủ
        # thật trả đúng số dòng được hỏi, và một bản giả trả khác đi sẽ làm nhánh "trang vơi thì
        # dừng" xanh hoặc đỏ vì lý do không có thật.
        length = int(path.split("length=")[1].split("&")[0])
        lo = self.ids[start:start + min(self.moi_trang, length)]
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
    assert kq == {"can_tim": 0, "tim_thay": 0, "so_trang": 0, "con_thieu": [],
                  "bat_dau_tiep": None, "xong": True}
    assert c.goi == [], "không có gì để tìm mà vẫn gọi ra Vietrip"


def test_co_phanh_khong_lat_vo_han(gia):
    """Máy chủ trả trang đầy mãi mãi (id không bao giờ lùi qua mốc): phải dừng ở TRAN_TRANG_BOOKING.

    Từ 27/9/2026 mỗi LƯỢT gọi chỉ lật `TRANG_MOI_LUOT` trang, nên phanh tổng chỉ chạm được sau
    nhiều lượt. Phép thử gọi vòng như người gọi thật, và bắt hai điều: mỗi lượt đúng đáy của nó,
    và tổng số dòng lướt qua không vượt phanh.
    """
    class KhongBaoGioHet(GiaClient):
        def get(self, path, timeout=90):
            self.goi.append(path)
            return json.dumps({"data": [{"recID": 500000 + len(self.goi) * 1000 + i}
                                        for i in range(1000)]})
    dat, kho = gia
    c = dat(KhongBaoGioHet([]))

    bat_dau, tong_trang, luot = 0, 0, 0
    while luot < 100:
        kq = VC.nap_booking_theo_id(None, [1], bat_dau=bat_dau)
        tong_trang += kq["so_trang"]
        luot += 1
        assert kq["so_trang"] <= VC.TRANG_MOI_LUOT, "một lượt lật quá đáy của nó"
        if kq["xong"]:
            break
        bat_dau = kq["bat_dau_tiep"]

    assert kq["xong"] and kq["con_thieu"] == [1]
    assert tong_trang == VC.TRAN_TRANG_BOOKING, f"lướt {tong_trang} trang, phanh là {VC.TRAN_TRANG_BOOKING}"
    assert luot == VC.TRAN_TRANG_BOOKING // VC.TRANG_MOI_LUOT


def test_moi_luot_co_day_va_noi_ra_cho_di_tiep(gia):
    """PHÉP THỬ CHÍNH của lần sửa 27/9: một lượt gọi KHÔNG được lật quá đáy, và phải nói chỗ đi tiếp.

    Bản đầu lật tới 60 trang trong một lượt. Trên gói 0,5 CPU của Render, yêu cầu chạy dài như thế
    làm nhịp tim `/health` quá 5 giây, Render giết máy chủ, và yêu cầu ấy trả 503 — trông y hệt một
    lỗi mã. Đáy này là thứ ngăn chuyện đó.
    """
    dat, kho = gia
    c = dat(GiaClient(list(range(1, 60001)), moi_trang=1000))    # 60 trang, id 60000 → 1
    kq = VC.nap_booking_theo_id(None, [5])                       # id nhỏ nhất: phải lật gần hết

    assert kq["so_trang"] == VC.TRANG_MOI_LUOT
    assert kq["xong"] is False, "chưa tìm ra mà đã khai xong"
    assert kq["bat_dau_tiep"] == VC.TRANG_MOI_LUOT * 1000
    assert len(c.goi) == VC.TRANG_MOI_LUOT


def test_lam_theo_lo_ra_dung_ket_qua_nhu_lam_mot_luot(gia):
    """Chia lô rồi ghép lại phải BẰNG làm một hơi — nếu không thì chia lô là một cách mất dữ liệu.

    Đây là phép thử đã bắt lỗi ở TC-63, và nó lại bắt lỗi ngay lần chạy đầu ở đây: bản đầu của vòng
    lặp đưa lại DANH SÁCH GỐC cho mỗi lượt, nên lượt cuối khai thiếu cả ba id mà ba lượt trước đã
    lấy được. Cách gọi đúng là đưa lại `con_thieu` vừa nhận.
    """
    can = [5, 12000, 33000, 58000]
    dat, kho = gia

    dat(GiaClient(list(range(1, 60001)), moi_trang=1000))
    mot_hoi = VC.nap_booking_theo_id(None, can, trang_moi_luot=999)

    kho["da_upsert"].clear()
    dat(GiaClient(list(range(1, 60001)), moi_trang=1000))
    bat_dau, con, thay, trang = 0, list(can), 0, 0
    while True:
        kq = VC.nap_booking_theo_id(None, con, bat_dau=bat_dau)
        thay += kq["tim_thay"]; trang += kq["so_trang"]; con = kq["con_thieu"]
        if kq["xong"]:
            break
        bat_dau = kq["bat_dau_tiep"]

    assert thay == mot_hoi["tim_thay"] == 4
    assert trang == mot_hoi["so_trang"]
    assert con == mot_hoi["con_thieu"] == []
    assert len(kho["da_upsert"]) == 4


def test_con_thieu_tra_ve_DU_khong_cat_ngan(gia):
    """`con_thieu` là đầu vào của lượt sau, nên cắt ngắn nó là đánh rơi id thật.

    Trên hệ thật có 183 booking cần tìm. Bản đầu trả `sorted(con_tim)[:50]` cho gọn mắt — gọn mắt
    ở màn hình, nhưng vòng gọi tiếp đọc đúng khoá ấy, nên 133 id sẽ biến mất không một dòng báo.
    """
    dat, kho = gia
    dat(GiaClient(list(range(1, 1001)), moi_trang=1000))
    can = list(range(900001, 900081))                            # 80 id không có thật
    kq = VC.nap_booking_theo_id(None, can)
    assert len(kq["con_thieu"]) == 80, f"trả về {len(kq['con_thieu'])}/80 id — đã cắt ngắn"


def test_bat_dau_am_thi_ve_0_chu_khong_lui_nguoc(gia):
    """`bat_dau` bậy không được thành một cách đọc ngược danh sách."""
    dat, kho = gia
    c = dat(GiaClient(list(range(1, 3001)), moi_trang=1000))
    VC.nap_booking_theo_id(None, [2999], bat_dau=-500)
    assert "start=0" in c.goi[0], f"bắt đầu từ chỗ âm: {c.goi[0]}"


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
