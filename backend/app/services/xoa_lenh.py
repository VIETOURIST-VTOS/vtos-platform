# -*- coding: utf-8 -*-
"""DL-4 — XOÁ MỘT LỆNH ĐIỀU XE CHƯA TỪNG CHẠY, và vì sao cửa này không mở rộng hơn thế.

Lệnh điều xe là chứng từ điều hành: nó nói ai cho xe nào chạy tour nào, ngày nào, giá bao nhiêu.
Một lệnh đã chạy thì phải ở lại trong sổ, kể cả khi chuyến ấy lỗ hay hỏng — xoá nó là xoá mất
câu trả lời cho câu hỏi «hôm ấy ai quyết». Nên tới 14/10/2026 phân hệ điều hành có cửa huỷ
(`status = huy`, dòng vẫn nằm đó) và KHÔNG có cửa xoá nào. Đúng.

Nguyên tắc ấy không phủ một trường hợp, và nó đang chặn một việc thật: **một lệnh tạo nhầm, chưa
từng thành chuyến, chưa ai nhận**. Đo trên hệ thật 14/10/2026: `51B-123.45` là một dòng xe mẫu,
không xoá được vì vướng đúng một lệnh — `DL-0825`, tài xế `Lý Văn Sơn`, 16–18/08/2026, và đó là
lệnh điều xe DUY NHẤT trong toàn hệ thống. Năm dấu hiệu đều chỉ về dữ liệu mẫu.

═══════════════════════════════════════════════════════════════════════════════════════════════
VƯỚNG LÀ DẤU VẾT CỦA VIỆC ĐÃ XẢY RA — KHÔNG PHẢI CHỮ TRÊN CỘT TRẠNG THÁI
═══════════════════════════════════════════════════════════════════════════════════════════════

Hai thứ chặn xoá, và chỉ hai:

  1. CÓ CHUYẾN MÓC VÀO LỆNH. Chuyến là cái đã chạy ngoài đời, có km, có dầu, có tiền.
  2. TÀI XẾ ĐÃ NHẬN LỆNH (`nhan_luc`). Đó là một con người đã bấm xác nhận vào một thời điểm.

`status` thì KHÔNG chặn, và đây là chỗ dễ làm sai nhất nên phải nói thẳng. `status = "hoan_thanh"`
chỉ là một chữ ai đó đặt vào cột; nó không chứng minh chuyến có thật. Chính `DL-0825` đang mang chữ
ấy mà không có lấy một chuyến nào. Chặn theo chữ thì cửa này vô dụng đúng ở trường hợp duy nhất cần
nó; nên cửa KHÔNG chặn theo chữ, mà **in cả nội dung lệnh ra** cho người sắp xoá nhìn tận mắt —
tour, xe, tài xế, ngày, giá, trạng thái — rồi bắt ghi lý do.

HÀNG RÀO ĐỌC TỪ METADATA, KHÔNG GÕ TAY. Đo 14/10/2026: đúng MỘT cột móc vào `dispatch_orders.id`
là `fleet_trips.dispatch_id`. Gõ tay một cái tên vào đây thì bảng thứ hai thêm vào tháng sau lọt
khỏi phép kiểm, và cửa xoá thành cửa tạo dòng mồ côi. Nên danh sách đọc từ chính `Base.metadata`
lúc chạy, và phép thử canh nó cũng KHÔNG đếm con số 1 — nó đối chiếu với chính metadata.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.hr import DispatchOrder

# Tên dễ đọc cho người, chỉ để in ra. Thiếu tên thì in tên bảng — không chặn.
TEN_BANG = {
    "fleet_trips": "chuyến trong nhật trình",
}


def _cot_moc_vao_lenh() -> list[tuple]:
    """Mọi (bảng, cột) có khoá ngoại tới `dispatch_orders.id`, đọc từ metadata lúc chạy."""
    ra = []
    for t in Base.metadata.sorted_tables:
        for c in t.columns:
            for fk in c.foreign_keys:
                if fk.column.table.name == "dispatch_orders":
                    ra.append((t, c))
    return ra


def _tom_tat(db: Session, d: DispatchOrder) -> dict:
    """Nội dung lệnh, in ra cho người sắp xoá nhìn tận mắt trước khi quyết."""
    from app.models.core import Tour
    from app.models.hr import Employee, Vehicle
    t = db.get(Tour, d.tour_id) if d.tour_id else None
    v = db.get(Vehicle, d.vehicle_id) if d.vehicle_id else None
    e = db.get(Employee, d.driver_id) if d.driver_id else None
    return {
        "id": d.id,
        "tour": (t.code if t else ""),
        "ten_tour": (t.name if t else ""),
        "xe": (v.plate if v else ""),
        "ma_xe": (v.code if v else ""),
        "tai_xe": (e.full_name if e else ""),
        "tu_ngay": d.date_from, "den_ngay": d.date_to,
        "gia_noi_bo": d.internal_price,
        "trang_thai": d.status,
        "nguoi_lap": d.created_by,
        "lap_luc": d.created_at,
        "tai_xe_nhan_luc": d.nhan_luc,
    }


def soat(db: Session, d: DispatchOrder) -> dict:
    """Những gì đang móc vào lệnh này. `xoa_duoc` True khi chưa có chuyến và chưa ai nhận."""
    vuong = []
    for t, c in _cot_moc_vao_lenh():
        n = db.execute(select(func.count()).select_from(t).where(c == d.id)).scalar() or 0
        if n:
            vuong.append({"bang": t.name, "ten": TEN_BANG.get(t.name, t.name), "so_dong": n})
    vuong.sort(key=lambda x: -x["so_dong"])

    # Dấu nhận của tài xế KHÔNG phải một bảng — nó là một cột trên chính lệnh, nên phép quét
    # khoá ngoại ở trên không thấy. Phải kiểm riêng, nếu không thì một lệnh đã có người nhận
    # vẫn lọt qua cửa.
    da_nhan = d.nhan_luc is not None
    noi = ("Chưa từng chạy — xoá được." if not vuong and not da_nhan else "")
    if vuong:
        noi = ("Không xoá được: lệnh này đã có " +
               ", ".join(f"{x['so_dong']} {x['ten']}" for x in vuong) +
               ". Lệnh đã thành chuyến thì ghi HUỶ, không xoá — xoá là mất dấu vết của chính "
               "chuyến ấy.")
    elif da_nhan:
        noi = ("Không xoá được: tài xế đã nhận lệnh này. Một người đã bấm xác nhận vào một thời "
               "điểm có thật — ghi HUỶ thì dấu ấy ở lại, xoá thì mất hẳn.")
    return {
        "lenh": _tom_tat(db, d),
        "xoa_duoc": (not vuong and not da_nhan),
        "vuong": vuong,
        "tai_xe_da_nhan": da_nhan,
        "noi": noi,
    }


def xoa(db: Session, d: DispatchOrder, ly_do: str) -> dict:
    """Xoá một lệnh chưa từng chạy. Trả về bản ghi ĐÃ XOÁ để nhật ký kiểm toán giữ lại.

    Bắt buộc lý do: một chứng từ điều hành biến mất mà không ai ghi vì sao là câu hỏi không có
    câu trả lời vào tháng sau. Trả về cả nội dung dòng: nhật ký giữ được thì xoá nhầm còn dựng
    lại được bằng tay.
    """
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do xoá.")
    s = soat(db, d)
    if not s["xoa_duoc"]:
        raise ValueError(s["noi"])
    truoc = {c.name: getattr(d, c.name) for c in DispatchOrder.__table__.columns}
    db.delete(d)
    db.flush()
    return {"da_xoa": truoc, "ly_do": ly_do.strip()[:300]}
