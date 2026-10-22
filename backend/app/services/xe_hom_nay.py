# -*- coding: utf-8 -*-
"""XE HÔM NAY — đang chạy bao nhiêu, nằm bãi bao nhiêu, bất thường bao nhiêu.

Anh Tuấn 16/9/2026, khi chốt thẻ "Tour đang chạy":

    "tour đang chạy là kết hợp với lịch của ngày hôm nay trùng với lịch khởi hành của tour để biết
     hôm nay tour đang đi là bao nhiêu, cũng như xe hôm nay đang chạy là bao nhiêu, nằm ở bãi là
     bao nhiêu... khi có lịch khởi hành cụ thể thì hệ thống sẽ tự nhận ra đang chạy là bao nhiêu"

Đúng một luật, áp cho hai đối tượng. Với tour thì lịch nằm ở `tours.start_date/end_date` — xem
`dem_tour.theo_giai_doan`. Với xe thì lịch nằm ở LỆNH ĐIỀU XE, và tệp này làm phần ấy.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO ĐỌC `dispatch_orders` CHỨ KHÔNG ĐỌC `fleet_trips`
═══════════════════════════════════════════════════════════════════════════════════════════════
Hai bảng đều có xe và có khoảng ngày, nên nhìn qua thì bảng nào cũng trả lời được. Nhưng chúng là
hai LOẠI dữ liệu khác nhau:

  · `dispatch_orders` là LỆNH — viết TRƯỚC chuyến đi, theo lịch khởi hành. Đúng thứ anh Tuấn mô tả.
  · `fleet_trips` là NHẬT TRÌNH — tài xế ghi TRONG hoặc SAU chuyến (trạng thái đầu tiên của nó tên
    là "Nháp – tài xế đang ghi"), kèm km đầu, km cuối, chi phí.

Hỏi "hôm nay xe nào đang đi" bằng nhật trình là hỏi một thứ chưa được viết xong: chuyến khởi hành
sáng nay có thể chưa có dòng nào trong `fleet_trips` cho tới lúc xe về. Con số sẽ luôn HỤT, và hụt
theo cách không ai phát hiện được — vì mỗi ngày nó vẫn ra một con số trông hợp lý.

═══════════════════════════════════════════════════════════════════════════════════════════════
NĂM LUẬT
═══════════════════════════════════════════════════════════════════════════════════════════════
1. ĐẾM XE, KHÔNG ĐẾM LỆNH. Một xe mang hai lệnh chồng ngày (một chuyến nối đuôi một chuyến, hoặc
   một lệnh sửa lại mà chưa huỷ lệnh cũ) vẫn là MỘT xe đang chạy. Đếm lệnh thì đội xe 30 chiếc có
   thể hiện ra 34 xe đang chạy, và không con số nào sai — chỉ là đếm nhầm đối tượng.

2. LỆNH ĐÃ HUỶ KHÔNG TÍNH. Mọi trạng thái khác đều tính, kể cả "chờ xác nhận": lệnh chờ xác nhận
   là chuyến ĐÃ ĐƯỢC XẾP, chỉ là Đội xe chưa bấm; xe ấy vẫn đang trên đường. Đòi "đã xác nhận" mới
   đếm là để một thao tác hành chính quyết định con số vận hành.

3. MẪU SỐ LÀ XE ĐIỀU ĐƯỢC, không phải mọi dòng trong bảng xe. Xe đã bán, xe ngừng khai thác, xe
   không có quyền khai thác thì không "nằm ở bãi" — chúng không còn là xe của mình. Gộp chúng vào
   là mỗi xe bán đi lại làm bãi xe đầy thêm một chiếc.

4. "Ở BÃI" LÀ HIỆU, KHÔNG PHẢI MỘT PHÉP ĐẾM THỨ HAI. Đếm riêng "xe không có lệnh nào hôm nay" thì
   hai con số dựng từ hai câu truy vấn, và ngày một bên đổi điều kiện là ngày chúng không còn cộng
   lại bằng tổng đội xe. Lấy hiệu thì sai lệch ấy không tồn tại được.

5. BẤT THƯỜNG ĐẾM XE, TRÊN LỆNH CỦA HÔM NAY. `incident_note` là chỗ Đội xe ghi sự cố của lệnh ấy.
   Xe có lệnh hôm nay và lệnh ấy có ghi chú sự cố thì là xe cần nhìn tới hôm nay — sự cố của một
   lệnh tháng trước không phải việc của bảng điều hành hôm nay.

RANH GIỚI 09/9 GIỮ NGUYÊN: tệp này không nhập số nào. Nó đọc lệnh điều xe do Đội xe nhập ở cửa
điều xe, và bảng xe do Hành chính nhập. Không có lệnh thì con số bằng 0 — và 0 ấy là SỐ THẬT
("hôm nay không điều xe nào"), khác hẳn "chưa có nguồn"; `co_nguon` nói ra sự khác nhau đó.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.hr import DispatchOrder, Vehicle

# Lệnh đã huỷ không tính. Khai ở đây, một chỗ — xem luật 2.
LENH_KHONG_TINH = ("huy",)

# Xe "điều được": còn là tài sản đang khai thác VÀ công ty có quyền điều. Hai điều kiện khác nhau
# và phải đủ cả hai — xem luật 3.
VONG_DOI_DIEU_DUOC = ("dang_khai_thac",)
QUYEN_KHONG_DIEU_DUOC = ("khong",)


def _xe_dieu_duoc(db: Session) -> int:
    return int(db.execute(
        select(func.count()).select_from(Vehicle).where(
            Vehicle.active.is_(True),
            Vehicle.lifecycle.in_(VONG_DOI_DIEU_DUOC),
            Vehicle.op_right.not_in(QUYEN_KHONG_DIEU_DUOC))).scalar() or 0)


def _co_lenh_bao_gio(db: Session) -> bool:
    """Bảng LỆNH ĐIỀU XE đã có lấy một dòng chưa (lệnh đã huỷ không tính).

    HQ-5 (23/10/2026) — vì sao cần một cờ thứ hai, bên cạnh `co_nguon`.

    `co_nguon` soi bảng XE: có 11 xe điều được thì nó bằng True, và màn hình in «0 xe đang đi».
    Nhưng đo trên hệ thật 23/10/2026: `dispatch_orders` RỖNG HOÀN TOÀN — chưa ai lập một lệnh điều
    xe nào, bao giờ. Lúc ấy con số 0 trên màn hình Chủ tịch nói «đã đếm và hôm nay không điều xe
    nào», trong khi sự thật là «chưa ai nhập cái bảng mà con số này đếm».

    Hai câu ấy dẫn tới hai việc khác hẳn nhau: câu thứ nhất là một ngày đội xe nghỉ, câu thứ hai là
    một cửa nhập chưa ai dùng. Màn hình nói câu thứ nhất thì không ai đi mở cửa thứ hai — và ô ấy
    sẽ in 0 mỗi ngày, mãi mãi, mà không ai biết nó đang đếm một cái bảng trống.

    Đây đúng là ranh giới 09/9 áp cho một bảng thứ hai: `co_nguon` đã phân biệt «0 thật» với «chưa
    có nguồn» cho bảng XE; cờ này làm cùng việc ấy cho bảng LỆNH. Có lệnh từ tháng trước mà hôm nay
    không có lệnh nào thì cờ vẫn True — và lúc ấy số 0 là số thật, đúng như cũ.
    """
    return bool(db.execute(
        select(DispatchOrder.id).where(
            DispatchOrder.status.not_in(LENH_KHONG_TINH)).limit(1)).first())


def _lenh_phu_ngay(hom_nay: date):
    """Điều kiện: lệnh phủ ngày ấy và chưa bị huỷ. Viết một lần, hai câu truy vấn dùng chung —
    hai bản chép thì ngày một bản đổi là ngày "đang chạy" và "bất thường" nói về hai tập xe."""
    return (DispatchOrder.date_from <= hom_nay,
            DispatchOrder.date_to >= hom_nay,
            DispatchOrder.status.not_in(LENH_KHONG_TINH))


def dem(db: Session, hom_nay: date) -> dict:
    """Bốn con số của đội xe trong ĐÚNG ngày ấy.

    `hom_nay` bắt buộc truyền vào, không tự đọc đồng hồ: mọi phép tính theo ngày đều phải thử được
    ở một ngày bất kỳ — cùng luật với `lich_chup` và `ket_qua_kinh_doanh`.
    """
    dieu_duoc = _xe_dieu_duoc(db)

    # DISTINCT trên vehicle_id — đếm XE, không đếm LỆNH (luật 1).
    dang_chay = int(db.execute(
        select(func.count(func.distinct(DispatchOrder.vehicle_id)))
        .where(*_lenh_phu_ngay(hom_nay))).scalar() or 0)

    bat_thuong = int(db.execute(
        select(func.count(func.distinct(DispatchOrder.vehicle_id)))
        .where(*_lenh_phu_ngay(hom_nay),
               DispatchOrder.incident_note != "")).scalar() or 0)

    return {
        "dieu_duoc": dieu_duoc,
        "dang_chay": dang_chay,
        # Hiệu, không phải phép đếm thứ hai (luật 4). `max(0, …)` chỉ để con số không âm khi bảng
        # xe và bảng lệnh lệch nhau — và lúc ấy `lech` nói ra, chứ không im lặng cắt đi.
        "o_bai": max(0, dieu_duoc - dang_chay),
        "bat_thuong": bat_thuong,
        # CỜ BÁO SỐ LỆCH: có xe đang chạy mà không nằm trong danh sách xe điều được. Nghĩa là một
        # lệnh đang trỏ tới chiếc xe đã bán, đã ngừng khai thác, hoặc đã tắt `active` — việc phải
        # đi hỏi Đội xe, không phải việc để hệ thống lặng lẽ làm tròn.
        "lech": max(0, dang_chay - dieu_duoc),
        # Có bảng xe chưa? Không có xe nào thì 0 là "chưa có nguồn", không phải "đội xe trống".
        "co_nguon": dieu_duoc > 0,
        # Có LỆNH chưa? Xem `_co_lenh_bao_gio`. Bảng lệnh trống thì 0 không phải một phép đếm, nó
        # là một cửa nhập chưa ai dùng — và màn hình phải nói ra chuyện ấy, không in con số 0.
        "co_lenh": _co_lenh_bao_gio(db),
    }
