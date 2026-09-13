# -*- coding: utf-8 -*-
"""Đ-10 · Dự chi ↔ thực chi trên TỪNG DÒNG — và cả HAI chiều lệch.

Phép kiểm vượt dự toán đã tồn tại từ trước, nhưng nằm ở nhánh cũ `services/settlement.py:158-165`
và chỉ chạy cho màn hình `/tours`. Nhánh lớp 3 (`/quyet-toan-lop3`) — nơi Điều hành thật sự nhập
chiết tính theo dòng — chỉ cộng hai tổng `tong_du_chi` và `tong_thuc_chi` rồi thôi.

Hai nhánh quyết toán song song, mỗi nhánh có một nửa hàng rào: đúng kiểu sai mà cả đợt Kiểm soát
sinh ra để chặn. Tệp này đưa phép kiểm sang lớp 3 và bổ sung chiều còn thiếu.

--------------------------------------------------------------------------------------------------
VÌ SAO PHẢI CÓ CHIỀU NGƯỢC — THỰC CHI THẤP HƠN DỰ TOÁN CŨNG PHẢI GIẢI THÍCH
--------------------------------------------------------------------------------------------------

Đo trên đoàn Hồ Tràm 2N1Đ (MICEHT2N1D.02110726), ba dòng lệch xuống đáng kể:

    Ăn tối Cây Dương Hồ Tràm     dự  9.250.000  →  thực  8.205.000    −1.045.000  (−11%)
    Vé tham quan Minera          dự 15.000.000  →  thực 13.355.000    −1.645.000  (−11%)
    Banner + ship                dự    300.000  →  thực    145.000      −155.000  (−52%)

Thấp hơn dự toán có thể là **thương lượng tốt** — và đó là tin mừng, đáng ghi nhận. Cũng có thể là
**dịch vụ bị cắt bớt** so với chương trình đã bán cho khách — và đó là chuyện phải biết ngay, vì
khách đã trả tiền cho chương trình cũ.

Trên con số hai chuyện ấy GIỐNG HỆT NHAU. Chỉ một dòng chữ của người điều hành mới phân biệt được.

Nên yêu cầu ở đây là MỘT DÒNG GIẢI THÍCH, không phải một lời buộc tội — và mức là CẢNH BÁO, không
chặn đóng số. Chặn một chuyến vì nó tiết kiệm được tiền là cách nhanh nhất để người ta thôi ghi
dự toán.

Chiều VƯỢT thì khác: giữ nguyên mức CHẶN như nhánh cũ. Tiêu quá tiền mà không ai giải thích là
chuyện phải dừng lại, không phải chuyện để xem sau.

--------------------------------------------------------------------------------------------------
BA ĐIỀU CỐ Ý KHÔNG LÀM
--------------------------------------------------------------------------------------------------

1. KHÔNG coi dự toán rỗng là 0. Dòng chưa khai dự toán thì KHÔNG so — nó vào danh sách "chưa có dự
   toán để so" và hiện ra. Coi rỗng là 0 thì mọi dòng đều "vượt vô hạn", danh sách đầy rác, và
   người ta thôi đọc.

2. KHÔNG dùng một ngưỡng cho cả hai chiều bằng cách lấy trị tuyệt đối. Vượt và hụt là hai chuyện
   nghiệp vụ khác nhau, mức xử lý khác nhau, nên ngưỡng khai riêng.

3. KHÔNG chặn vì tổng chuyến lệch. Tổng lệch mà từng dòng đều có giải thích thì tờ quyết toán đã
   xong việc của nó; chặn thêm ở mức tổng là bắt người ta giải trình hai lần cho cùng một chuyện.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vietrip import TourCostLine
from app.services.rules import get_param

# Ngưỡng lệch. Dùng chung `nguong_bien` với nhánh cũ cho chiều VƯỢT — cùng một câu hỏi thì cùng một
# con số, không đẻ thêm tham số thứ hai nói cùng một điều.
KHOA_NGUONG_VUOT = "nguong_bien"
# Chiều HỤT khai riêng: nó là câu hỏi khác. Để 0.15 vì hụt vài phần trăm là chuyện thường của mọi
# chuyến (đổi nhà hàng, bớt một suất), còn hụt trên 15% thì thường là chương trình đã đổi.
KHOA_NGUONG_HUT = "nguong_hut_du_toan"

MUC = {"chan": "Chặn – phải giải trình trước khi đóng số",
       "canh_bao": "Cảnh báo – cần một dòng giải thích"}


def _nguong(db: Session, hom_nay: date | None = None) -> tuple[float, float]:
    return get_param(db, KHOA_NGUONG_VUOT, hom_nay), get_param(db, KHOA_NGUONG_HUT, hom_nay)


def soat_dong(db: Session, tour_id: int, hom_nay: date | None = None) -> dict:
    """So dự chi ↔ thực chi trên từng dòng chi phí còn hiệu lực của một chuyến.

    Trả về ba danh sách tách hẳn nhau, vì ba thứ ấy dẫn tới ba hành động khác nhau:
      * `vuot`          – chặn, phải giải trình
      * `hut`           – cảnh báo, cần một dòng chữ
      * `chua_co_du_toan` – không so được; hiện ra để người ta biết bảng này đang không phủ hết
    """
    ng_vuot, ng_hut = _nguong(db, hom_nay)
    ds = list(db.scalars(select(TourCostLine)
                         .where(TourCostLine.tour_id == tour_id, TourCostLine.status == "hd")
                         .order_by(TourCostLine.line_no, TourCostLine.id)))

    vuot, hut, chua = [], [], []
    tong_du = tong_thuc = 0.0
    for l in ds:
        thuc = None if l.actual is None else float(l.actual)
        du = None if l.budget is None else float(l.budget)
        if thuc is not None:
            tong_thuc += thuc
        if du is not None:
            tong_du += du

        # Rỗng ở BẤT KỲ vế nào thì không so. Dòng chưa nhập thực chi cũng chưa so được – nó chưa
        # phải "hụt 100%", nó là dòng chưa xong.
        if du is None or thuc is None or du == 0:
            chua.append({"dong_id": l.id, "line_no": l.line_no, "mo_ta": l.description,
                         "du_chi": du, "thuc_chi": thuc,
                         "vi_sao": ("chưa khai dự toán" if du is None
                                    else "chưa nhập thực chi" if thuc is None
                                    else "dự toán bằng 0")})
            continue

        lech = thuc - du
        ty_le = lech / du
        giai_thich = (l.note or "").strip()
        chung = {"dong_id": l.id, "line_no": l.line_no, "mo_ta": l.description,
                 "ma_khoan_muc": l.ma_khoan_muc, "nha_cung_cap": l.supplier_name,
                 "du_chi": du, "thuc_chi": thuc, "lech": round(lech, 2),
                 "ty_le": round(ty_le, 4), "giai_thich": giai_thich}
        if ty_le > ng_vuot and not giai_thich:
            vuot.append({**chung, "muc": "chan",
                         "can_lam": "Ghi lời giải trình vào ô Ghi chú của dòng này"})
        elif ty_le < -ng_hut and not giai_thich:
            hut.append({**chung, "muc": "canh_bao",
                        "can_lam": "Một dòng chữ: thương lượng được giá, hay dịch vụ đã đổi so với "
                                   "chương trình đã bán cho khách? Hai chuyện này nhìn trên con số "
                                   "giống hệt nhau."})

    return {
        "tour_id": tour_id, "so_dong": len(ds),
        "nguong_vuot": ng_vuot, "nguong_hut": ng_hut,
        "tong_du_chi": round(tong_du, 2) if any(l.budget is not None for l in ds) else None,
        "tong_thuc_chi": round(tong_thuc, 2) if any(l.actual is not None for l in ds) else None,
        "vuot": vuot, "hut": hut, "chua_co_du_toan": chua,
        # Chỉ chiều VƯỢT mới chặn. Xem phần đầu tệp.
        "duoc_dong_so": not vuot,
        "so_chan": len(vuot), "so_canh_bao": len(hut),
        "ghi_chu": ("Thực chi THẤP hơn dự toán cũng cần một dòng giải thích: thương lượng tốt và "
                    "dịch vụ bị cắt bớt nhìn trên con số giống hệt nhau. Cảnh báo, không chặn."),
    }
