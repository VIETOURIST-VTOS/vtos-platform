# -*- coding: utf-8 -*-
"""KS-6 · Đặt phòng đi theo đúng các bước của Agoda Demand API.

Sáu phép dưới đây không đụng cơ sở dữ liệu: năm phép đầu dựng một đơn giả, phép cuối soi NGUỒN.
Mỗi phép buộc một câu trong tài liệu Agoda thành một hàng rào chạy được.
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.models.don_khach_san_ota import (LY_DO_HUY, NGUON_SONG, NGUON_THU, TRANG_THAI_DON,
                                          TRANG_THAI_NGUON)
from app.services import don_khach_san_ota as D
from app.services import khach_san_ota as S

GOC_APP = Path(S.__file__).resolve().parents[1]
BAY_GIO = datetime(2026, 10, 29, 3, 30, 0)


class _Ota:
    def __init__(self, quyen="AFFILIATE,SEARCH,BOOK,CANCEL", moi_truong="that"):
        self.id, self.ma = 3, "agoda"
        self.quyen, self.moi_truong = quyen, moi_truong


class _Don:
    def __init__(self, **kw):
        self.id = 1
        self.the_tham_chieu = "VTD-2026-10-29-0001"
        self.ota_id, self.moi_truong = 3, "that"
        self.trang_thai, self.trang_thai_nguon = "da_hoi_gia", ""
        self.ma_tim, self.tim_luc = 633141408144250000, BAY_GIO - timedelta(minutes=10)
        self.ma_khoi, self.the_chao = "aBc_123-xyz=", ""
        self.ma_khach_san, self.ma_phong, self.ma_goi_gia = 7001, 9001, 11001
        self.kieu_thanh_toan = "merchant"
        self.ngay_nhan, self.ngay_tra = date(2026, 12, 20), date(2026, 12, 22)
        self.so_phong, self.nguoi_lon, self.tre_em, self.tuoi_tre_em = 1, 2, 0, ""
        self.nuoc_khach, self.ngon_ngu, self.tien_te = "VN", "vi-vn", "VND"
        self.gia_gom_thue, self.phu_thu = 2400000, ""
        self.ma_don_nguon, self.ma_hanh_trinh, self.dang_xu_ly, self.dat_luc = 0, 0, False, None
        self.so_xac_nhan_ks, self.tham_chieu_nguon = "", ""
        self.tham_chieu_huy, self.ly_do_huy, self.hoan_gom_thue, self.huy_luc = 0, 0, 0, None
        self.ghi_chu, self.sua_boi, self.sua_luc = "", "", None
        for k, v in kw.items():
            setattr(self, k, v)


def test_ks6_1_chua_du_dieu_kien_thi_khong_duoc_goi_dat():
    """Quyền BOOK, môi trường, thẻ tham chiếu, mã khối, và mã tìm còn hạn — thiếu cái nào cũng chặn."""
    assert D.thieu_de_dat(_Don(), _Ota(), BAY_GIO) == []

    assert "chưa ghi nhận nguồn cấp quyền BOOK" in D.thieu_de_dat(
        _Don(), _Ota(quyen="AFFILIATE,SEARCH"), BAY_GIO)
    assert "môi trường đang Tắt" in D.thieu_de_dat(_Don(), _Ota(moi_truong="tat"), BAY_GIO)
    assert "chưa có mã khối phòng" in D.thieu_de_dat(_Don(ma_khoi=""), _Ota(), BAY_GIO)
    assert "đơn này đã đặt rồi" in D.thieu_de_dat(_Don(ma_don_nguon=80000610), _Ota(), BAY_GIO)

    # Thẻ tham chiếu: thiếu nó thì một lần quá hạn là một lần không ai tra lại được.
    t = D.thieu_de_dat(_Don(the_tham_chieu="  "), _Ota(), BAY_GIO)
    assert any("thẻ tham chiếu" in x for x in t), t


def test_ks6_2_ma_tim_song_dung_mot_gio():
    """«The searchId is only valid for 1 hr» — quá giờ Agoda trả lỗi 912, lúc khách đang chờ."""
    assert D.con_han_ma_tim(_Don(tim_luc=BAY_GIO - timedelta(minutes=59)), BAY_GIO) is True
    assert D.con_han_ma_tim(_Don(tim_luc=BAY_GIO - timedelta(minutes=61)), BAY_GIO) is False
    assert D.con_han_ma_tim(_Don(ma_tim=0), BAY_GIO) is False
    assert "mã tìm đã quá một giờ — phải hỏi giá lại" in D.thieu_de_dat(
        _Don(tim_luc=BAY_GIO - timedelta(hours=2)), _Ota(), BAY_GIO)


def test_ks6_3_dieu_kien_phai_khop_y_nguyen_qua_ba_buoc():
    """Lệch một ô giữa hỏi giá và đặt thì đặt nhầm phòng khác với phòng khách đã xem giá."""
    don = _Don()
    assert D.lech_ba_buoc(don, {"ngay_nhan": "2026-12-20", "nguoi_lon": 2, "tien_te": "VND"}) == []

    l = D.lech_ba_buoc(don, {"ngay_nhan": "2026-12-21"})
    assert len(l) == 1 and "ngay_nhan" in l[0], l

    l2 = D.lech_ba_buoc(don, {"nguoi_lon": 3, "tien_te": "USD"})
    assert len(l2) == 2, l2
    assert set(D.PHAI_KHOP) >= {"ngay_nhan", "ngay_tra", "nuoc_khach", "tien_te", "ngon_ngu"}


def test_ks6_4_qua_han_dat_thi_khong_duoc_dat_lai_phai_tra_cuu():
    """«Should not immediately resend the same booking request.»

    Gửi lại cho chắc = khách bị tính tiền hai lần. Đường đúng là tra Booking List bằng thẻ.
    """
    don = _Don()
    assert D.dat_lai_duoc(don) is True
    D.ghi_qua_han_dat(don)
    assert don.trang_thai == "cho_tra_cuu"
    assert D.dat_lai_duoc(don) is False
    assert "đơn đã đóng" not in D.thieu_de_dat(don, _Ota(), BAY_GIO)

    # Tra được rồi thì chép kết quả vào đơn.
    don2 = _Don()
    D.ghi_dat_xong(don2, {"id": 80000610, "itineraryId": 123, "processing": True}, BAY_GIO)
    assert don2.ma_don_nguon == 80000610 and don2.dang_xu_ly is True
    assert don2.trang_thai == "da_dat" and don2.trang_thai_nguon == "BookingReceived"
    with pytest.raises(S.LoiOta):
        D.ghi_dat_xong(_Don(), {"processing": False}, BAY_GIO)

    # Số đưa cho khách: số xác nhận khách sạn trước, rồi tham chiếu nguồn, rồi mã đơn.
    assert D.so_de_doi_chieu(don2) == "80000610"
    don2.tham_chieu_nguon = "AG-77"
    assert D.so_de_doi_chieu(don2) == "AG-77"
    don2.so_xac_nhan_ks = "HCN-9"
    assert D.so_de_doi_chieu(don2) == "HCN-9"


def test_ks6_5_huy_dung_hai_buoc_va_ba_con_so_phai_khop():
    """«BookingID, Reference, and RefundRateInclusive must match to proceed.» Lệch là lỗi 914."""
    don = _Don(ma_don_nguon=80000610, trang_thai="da_dat", trang_thai_nguon="BookingConfirmed")
    truoc = date(2026, 12, 1)
    assert D.thieu_de_huy(don, _Ota(), truoc) == []

    assert "chưa ghi nhận nguồn cấp quyền CANCEL" in D.thieu_de_huy(
        don, _Ota(quyen="AFFILIATE,BOOK"), truoc)

    # «Cancellations are allowed up to 1 day before check-in» — từ đó trở đi phải có người thật.
    sat = date(2026, 12, 19)
    t = D.thieu_de_huy(don, _Ota(), sat)
    assert any("phải báo nguồn bằng người" in x for x in t), t

    xem = {"bookingId": 80000610, "reference": 4411, "refundInclusive": 1200000.0}
    assert D.lech_xac_nhan_huy(don, xem, dict(xem, cancelReason=14)) == []

    l = D.lech_xac_nhan_huy(don, xem, dict(xem, refundInclusive=1200001.0, cancelReason=14))
    assert len(l) == 1 and "tiền hoàn lệch" in l[0], l
    assert D.lech_xac_nhan_huy(don, xem, dict(xem, reference=1, cancelReason=14)) != []
    # Lý do huỷ phải là một mã CÓ THẬT trong bảng của nguồn, không phải số mình tự nghĩ ra.
    assert D.lech_xac_nhan_huy(don, xem, dict(xem, cancelReason=99)) != []
    assert 44 in LY_DO_HUY and 0 in LY_DO_HUY


def test_ks6_6_don_sandbox_va_BookingTest_khong_bao_gio_vao_bao_cao_tien():
    """Hai nguồn tiền ảo: đơn dựng trong Sandbox, và đơn Agoda đánh dấu `BookingTest`."""
    that = _Don(trang_thai="da_dat", trang_thai_nguon="BookingConfirmed")
    assert D.vao_bao_cao_tien(that) is True

    assert D.vao_bao_cao_tien(_Don(moi_truong="thu", trang_thai="da_dat",
                                   trang_thai_nguon="BookingConfirmed")) is False
    assert D.vao_bao_cao_tien(_Don(trang_thai="da_dat", trang_thai_nguon="BookingTest")) is False
    assert D.vao_bao_cao_tien(_Don(trang_thai="da_huy",
                                   trang_thai_nguon="BookingCancelled")) is False

    assert len(TRANG_THAI_NGUON) == 10, "Mười giá trị của Agoda, chép nguyên, không thêm bớt"
    assert "BookingTest" in NGUON_THU and "BookingConfirmed" in NGUON_SONG
    assert set(TRANG_THAI_DON) >= {"moi", "cho_tra_cuu", "da_dat", "da_huy"}

    # Trạng thái lạ phải ném, không được im lặng nhận bừa.
    with pytest.raises(S.LoiOta):
        D.nhan_trang_thai_nguon(_Don(), "DaXacNhan")
    d = _Don(ma_don_nguon=1, dang_xu_ly=True)
    D.nhan_trang_thai_nguon(d, "BookingCharged")
    assert d.trang_thai == "da_dat" and d.dang_xu_ly is False
    D.nhan_trang_thai_nguon(d, "BookingCancelledByCustomer")
    assert d.trang_thai == "da_huy"


def test_ks6_7_phan_don_khach_san_khong_cham_so_the_va_khong_chep_totalPayment():
    """Hai điều cấm của tài liệu, viết thành hàng rào chứ không phải lời hứa.

    1. Fulfill Assisted: «Agoda will directly charge your customers» — không ô nào nhận số thẻ.
    2. Book API: «Do not use the totalPayment rate» — không cột nào chép con số ấy, vì chép cả
       hai rồi sẽ có ngày ai đó cộng nhầm cột.
    """
    cam_the = re.compile(
        r"\b(card_number|cardnumber|credit_card|creditcard|creditCardInfo|the_tin_dung|so_the|"
        r"\bcvv\b|\bcvc\b|\bpan\b|expiry_month|expiry_year|expiryDate|card_holder|holderName)\b",
        re.I)
    cam_gia = re.compile(r"total_?payment", re.I)
    tep = [
        GOC_APP / "models" / "don_khach_san_ota.py",
        GOC_APP / "services" / "don_khach_san_ota.py",
    ]
    co = [p for p in tep if p.is_file()]
    assert len(co) == 2, "Thiếu tệp của phần đơn khách sạn: " + str([p.name for p in tep])

    dinh = []
    for p in co:
        for i, d in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if "KS-6" in d or d.strip().startswith("#"):
                continue
            if cam_the.search(d):
                dinh.append(f"THẺ  {p.name}:{i}: {d.strip()[:100]}")
            if cam_gia.search(d):
                dinh.append(f"GIÁ  {p.name}:{i}: {d.strip()[:100]}")
    assert not dinh, (
        "\n    " + "\n    ".join(dinh)
        + "\n\nMô hình đã chọn là Agoda Fulfill Assisted: AGODA thu tiền khách, Vietourist không "
          "bao giờ chạm vào số thẻ. Và giá để đặt là `rate.inclusive`, không phải `totalPayment` "
          "— tài liệu Book API cấm dùng con số ấy."
    )
