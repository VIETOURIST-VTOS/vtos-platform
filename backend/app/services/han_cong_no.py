# -*- coding: utf-8 -*-
"""KHỐI 05 CỦA BẢN VẼ V1.4 — Phải thu và Phải trả theo HẠN THANH TOÁN, năm nhóm không trùng nhau.

Vòng TC-23 (13/9/2026) dựng xong GIAO DIỆN hai khối này rồi để mỗi ô ghi "Chưa kết nối", vì lúc ấy
chưa rà ra nguồn số. Anh Tuấn kiểm lại 14/9 và nói thẳng: màn hình Chủ tịch vẫn chưa xong.

Rà lại thì nguồn số ĐÃ CÓ SẴN, không phải dựng gì mới: sổ nghĩa vụ thanh toán (VPM-11,
`nghia_vu_thanh_toan`) giữ đủ hướng thu/chi, ngày cam kết, số còn phải trả và pháp nhân chịu. Khối
dòng tiền bốn mốc vẫn đang đọc chính sổ ấy. Việc còn thiếu chỉ là PHÉP CHIA NHÓM THEO HẠN — đúng
phần việc "viết cấu trúc và phép tính", không cần thêm một cửa nhập nào.

═══════════════════════════════════════════════════════════════════════════════════════════════
NĂM ĐIỀU TỆP NÀY GIỮ
═══════════════════════════════════════════════════════════════════════════════════════════════

1. NĂM NHÓM KHÔNG TRÙNG NHAU, khác hẳn bảng dòng tiền bốn mốc LŨY KẾ ở khối 06. Ở đây một khoản
   rơi vào ĐÚNG MỘT nhóm, nên cộng năm nhóm ra đúng tổng công nợ; ở khối 06 cột 14 ngày đã chứa
   trọn cột 7 ngày, cộng lại là sai. Hai khối cạnh nhau trên cùng màn hình mà cộng theo hai luật
   khác nhau — nên luật phải viết ra, không để người đọc tự đoán.

2. MỐC THÁNG TÍNH THEO THÁNG LỊCH, không phải 60 hay 90 ngày. Anh Tuấn chốt điều này hai lần: ở
   khối Phải thu/Phải trả (13/9) và ở bốn mốc dòng tiền (14/9 — "ok em giữ theo lịch tháng"). Ngày
   31 cộng một tháng lịch rơi vào tháng chỉ có 28–30 ngày thì lùi về ngày cuối tháng ấy.

3. HẠN RƠI ĐÚNG NGÀY BÁO CÁO KHÔNG PHẢI LÀ QUÁ HẠN. Nó thuộc nhóm sắp đến hạn đầu tiên. Người ta
   còn cả ngày hôm nay để trả; xếp vào quá hạn là dán nhãn trễ cho một người chưa trễ.

4. RỖNG KHÁC KHÔNG — và đây là chỗ dễ sai nhất của khối này. Một nhóm không có khoản nào thì tổng
   bằng 0, và đó là con số ĐÚNG. Nhưng nếu cả sổ nghĩa vụ chưa có dòng nào (phép đồng bộ chưa chạy)
   thì mọi nhóm cũng ra 0 — và năm con số 0 ấy đọc y như "không nợ ai đồng nào", trong khi sự thật
   là "chưa ai nạp sổ". Nên trước khi cộng, hàm ĐẾM sổ: sổ rỗng thì trả `None` kèm lý do, không trả
   một hàng số 0.

5. KHOẢN CHƯA CÓ HẠN THEO DÕI RIÊNG. Không xếp vào "Dài hạn" cho gọn: "chưa ai điền ngày" và "đến
   hạn sau ba tháng" là hai việc khác hẳn nhau, và cái thứ nhất là việc phải đi đòi người nhập.
   Giao diện TC-23 đã hứa điều này ở dòng chú thích nhưng chưa có chỗ hiện — vòng này thêm chỗ.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nghia_vu import NHOM, TRANG_THAI_DONG, NghiaVuThanhToan, nhom_duoc_xem
from app.services import nghia_vu as NV

THU, CHI = "thu", "chi"

# Nhãn nhóm PHẢI KHỚP TỪNG CHỮ với PHAI_THU / PHAI_TRA trong web/components/KhoiV14.tsx: màn hình
# tra số theo đúng chuỗi này. Lệch một dấu là ô hiện "Chưa kết nối" trong khi máy chủ có số.
NHAN_THU = ("Quá hạn", "2 tuần", "4 tuần", "2 tháng", "Dài hạn")
NHAN_TRA = ("1 tuần", "2 tuần", "4 tuần", "3 tháng", "Dài hạn")

LY_DO_SO_RONG = ("Sổ nghĩa vụ thanh toán chưa có khoản nào — phép đồng bộ VPM-11 chưa chạy hoặc "
                 "chưa bộ phận nào nạp chứng từ.")


def cong_thang(d: date, n: int) -> date:
    """Cộng n THÁNG LỊCH. Ngày 31 rơi vào tháng ngắn hơn thì lùi về ngày cuối tháng ấy.

    Không dùng `timedelta(days=30*n)`: 30 ngày không phải một tháng, và cái sai ấy dồn lại thành
    vài ngày lệch ở mốc ba tháng — đủ để một khoản nhảy sang nhóm khác.
    """
    thang = d.month - 1 + n
    nam = d.year + thang // 12
    thang = thang % 12 + 1
    return date(nam, thang, min(d.day, calendar.monthrange(nam, thang)[1]))


def khoang_thu(hom_nay: date) -> list[tuple[str, date, date]]:
    """Năm khoảng của PHẢI THU. Liền nhau, không hở, không chồng."""
    m2 = cong_thang(hom_nay, 2)
    return [
        ("Quá hạn", date.min, hom_nay - timedelta(days=1)),
        ("2 tuần", hom_nay, hom_nay + timedelta(days=14)),
        ("4 tuần", hom_nay + timedelta(days=15), hom_nay + timedelta(days=28)),
        ("2 tháng", hom_nay + timedelta(days=29), m2),
        ("Dài hạn", m2 + timedelta(days=1), date.max),
    ]


def khoang_tra(hom_nay: date) -> list[tuple[str, date, date]]:
    """Năm khoảng của PHẢI TRẢ. Quá hạn KHÔNG nằm trong năm nhóm này — nó theo dõi riêng ở
    `qua_han`, vì một khoản đã trễ và một khoản sắp tới hạn khác hẳn nhau về mức khẩn."""
    m3 = cong_thang(hom_nay, 3)
    return [
        ("1 tuần", hom_nay, hom_nay + timedelta(days=7)),
        ("2 tuần", hom_nay + timedelta(days=8), hom_nay + timedelta(days=14)),
        ("4 tuần", hom_nay + timedelta(days=15), hom_nay + timedelta(days=28)),
        ("3 tháng", hom_nay + timedelta(days=29), m3),
        ("Dài hạn", m3 + timedelta(days=1), date.max),
    ]


def _huong_cua(ma_nhom: str) -> str:
    """Hướng thu/chi của một nhóm.

    Lấy từ bảng NHOM chứ không từ cột `huong` của từng dòng, và hai nguồn ấy KHÔNG THỂ lệch nhau:
    `nghia_vu._dat()` đặt `nv.huong = NHOM[nhom][0]` mỗi lần ghi. Đọc từ bảng cho phép dùng lại
    nguyên `NV.cong()` — hàm đã mang sẵn cả ba hàng rào (pháp nhân, loại tiền, nhóm theo vai).
    """
    return NHOM.get(ma_nhom, ("", ""))[0]


def _co_khoan_nao(db: Session, huong: str, vai_tro: str | None, loai_tien: str) -> bool:
    """Sổ có khoản nào đang mở theo hướng này không — dùng để phân biệt 'bằng 0' với 'chưa có sổ'.

    Đây là chỗ DUY NHẤT tệp này tự dựng câu truy vấn thay vì gọi `NV.cong()`, vì `cong()` bắt buộc
    phải có khoảng ngày còn câu hỏi ở đây không có ngày nào cả. Điều kiện lọc lấy đúng từ hằng số
    của làn kia (`TRANG_THAI_DONG`, `nhom_duoc_xem`) chứ không chép tay, và phép thử đối chiếu tổng
    của hai đường để bắt lệch nếu làn kia đổi luật.
    """
    nhom = [k for k in nhom_duoc_xem(vai_tro) if _huong_cua(k) == huong] if vai_tro else \
           [k for k in NHOM if _huong_cua(k) == huong]
    q = select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.ghi_nho == False,                                  # noqa: E712
        NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG),
        NghiaVuThanhToan.loai_tien == loai_tien,
        NghiaVuThanhToan.nhom.in_(sorted(nhom)))
    for nv in db.execute(q).scalars():
        if nv.con_lai() > 0:
            return True
    return False


def _chua_co_han(db: Session, huong: str, vai_tro: str | None, loai_tien: str) -> float:
    """Tổng khoản CHƯA CÓ NGÀY CAM KẾT. Không xếp vào Dài hạn — xem điều 5 ở đầu tệp."""
    nhom = [k for k in nhom_duoc_xem(vai_tro) if _huong_cua(k) == huong] if vai_tro else \
           [k for k in NHOM if _huong_cua(k) == huong]
    q = select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.ghi_nho == False,                                  # noqa: E712
        NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG),
        NghiaVuThanhToan.loai_tien == loai_tien,
        NghiaVuThanhToan.ngay_cam_ket.is_(None),
        NghiaVuThanhToan.nhom.in_(sorted(nhom)))
    return round(sum(max(nv.con_lai(), 0) for nv in db.execute(q).scalars()))


def _tong(db: Session, tu: date, den: date, huong: str, vai_tro: str | None, loai_tien: str) -> float:
    """Tổng một khoảng, theo hướng. `NV.cong()` trả theo NHÓM nên chỉ việc gộp các nhóm cùng hướng."""
    theo_nhom = NV.cong(db, tu, den, co_so_ngay="cam_ket", loai_tien=loai_tien, vai_tro=vai_tro)
    return round(sum(v for k, v in theo_nhom.items() if _huong_cua(k) == huong))


def theo_han(db: Session, huong: str, *, vai_tro: str | None = None,
             hom_nay: date | None = None, loai_tien: str = "VND") -> dict:
    """Khối 05a (huong="thu") hoặc 05b (huong="chi").

    Trả về `{"nhom": {nhãn: số|None}, "chua_co_han": số|None, "qua_han": số|None, "vi_sao": str}`.
    `qua_han` chỉ có nghĩa ở phía CHI — phía THU đã có nhóm "Quá hạn" trong năm nhóm.
    """
    hom_nay = hom_nay or date.today()
    khoang = khoang_thu(hom_nay) if huong == THU else khoang_tra(hom_nay)

    if not _co_khoan_nao(db, huong, vai_tro, loai_tien):
        # Sổ rỗng: trả RỖNG kèm lý do, không trả một hàng số 0 — xem điều 4 ở đầu tệp.
        return {"nhom": {nhan: None for nhan, _, _ in khoang},
                "chua_co_han": None, "qua_han": None, "vi_sao": LY_DO_SO_RONG}

    ra = {nhan: _tong(db, tu, den, huong, vai_tro, loai_tien) for nhan, tu, den in khoang}
    qh = (None if huong == THU
          else _tong(db, date.min, hom_nay - timedelta(days=1), huong, vai_tro, loai_tien))
    return {"nhom": ra, "chua_co_han": _chua_co_han(db, huong, vai_tro, loai_tien),
            "qua_han": qh, "vi_sao": ""}
