# -*- coding: utf-8 -*-
"""Tài xế NHẬN lệnh điều xe — mắt thứ ba, và là mắt cuối của chuỗi Chủ tịch đặc tả 11/10/2026.

    Điều hành ĐỀ NGHỊ xe  →  Giám đốc đội xe LẬP LỆNH  →  tài xế NHẬN

BỐN LUẬT CHỦ TỊCH CHỐT 12/10/2026, và mỗi luật có một chỗ duy nhất trong tệp này:

  1. TỪ CHỐI KHÔNG HUỶ LỆNH. Lệnh vẫn hiệu lực, hệ thống báo Giám đốc đội xe. Tài xế nói được
     "tôi không nhận được", nhưng không huỷ được việc của cấp trên.
  2. HẠN NHẬN = TRƯỚC GIỜ KHỞI HÀNH 24 GIỜ. Mốc neo vào CHUYẾN chứ không vào lúc lập lệnh: lệnh
     lập sớm một tháng thì hạn vẫn rơi đúng một ngày trước khi đi, còn kịp đổi người.
  3. SỬA LỆNH SAU KHI ĐÃ NHẬN  →  XOÁ DẤU NHẬN, tài xế phải nhận lại. Tài xế đồng ý với MỘT nội
     dung; nội dung đổi thì dấu đồng ý cũ không còn nghĩa gì.
  4. QUÁ HẠN KHÔNG CHẶN AI. Nó chỉ ĐẾM ĐƯỢC và nổi lên bàn làm việc của Giám đốc đội xe.

MỘT CHỖ HỆ THỐNG CHƯA CÓ, NÓI THẲNG RA CHỨ KHÔNG LÀM NGƠ: `dispatch_orders` chỉ lưu NGÀY đi
(`date_from: Date`), KHÔNG lưu giờ khởi hành. Nên "24 giờ trước giờ khởi hành" không tính đúng
được. Ở đây lấy mốc 00:00 của ngày đi rồi lùi 24 giờ — tức hạn rơi vào 00:00 ngày hôm trước, SỚM
HƠN mốc thật vài giờ. Lệch về phía an toàn: tài xế bị nhắc sớm hơn chứ không muộn hơn, và Giám đốc
đội xe thấy chỗ trống sớm hơn chứ không muộn hơn. Ngày nào lệnh có thêm giờ khởi hành thì sửa
ĐÚNG MỘT HÀM `han_nhan()` là xong — đó là lý do phép tính ấy không được gõ rải rác nơi khác.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import DispatchOrder, Employee
from app.services import rules as R

# Số giờ trước khi đi mà tài xế phải bấm nhận. Là HẰNG SỐ, không phải ô người dùng tự điền: hạn
# nhận là quy ước điều hành của cả đội xe, để mỗi lệnh một hạn thì không còn so được lệnh nào trễ.
HAN_GIO = 24

# Lệnh ở những trạng thái này thì KHÔNG còn chờ ai nhận nữa.
KHONG_CHO_NHAN = ("huy", "hoan_thanh")

CHUA_NHAN, DA_NHAN, TU_CHOI, QUA_HAN = "chua_nhan", "da_nhan", "tu_choi", "qua_han"
TEN = {
    CHUA_NHAN: "Chờ tài xế nhận",
    DA_NHAN: "Tài xế đã nhận",
    TU_CHOI: "Tài xế báo không nhận được",
    QUA_HAN: "Quá hạn mà tài xế chưa nhận",
}


def han_nhan(d: DispatchOrder) -> datetime | None:
    """Hạn tài xế phải bấm nhận. Rỗng khi lệnh chưa có ngày đi.

    CHỖ DUY NHẤT tính mốc này. Xem chú thích đầu tệp về việc lệnh chưa lưu giờ khởi hành.
    """
    if d.date_from is None:
        return None
    return datetime.combine(d.date_from, datetime.min.time()) - timedelta(hours=HAN_GIO)


def trang_thai_nhan(d: DispatchOrder, bay_gio: datetime | None = None) -> str:
    """Một lệnh đang ở đâu trong mắt thứ ba. Tính tại chỗ, KHÔNG lưu thành cột.

    Vì sao không lưu: "quá hạn" đổi theo đồng hồ chứ không theo một lần bấm nào, nên một cột lưu
    sẵn sẽ sai ngay phút sau khi ghi, trừ phi có người chạy nền cập nhật — và chỗ ấy là chỗ sẽ
    quên chạy. Cùng khuôn với `su_co_tour.qua_han()`.
    """
    if d.nhan_luc is not None:
        return DA_NHAN
    if (d.tu_choi_nhan_ly_do or "").strip():
        return TU_CHOI
    h = han_nhan(d)
    if h is not None and (bay_gio or datetime.now()) > h:
        return QUA_HAN
    return CHUA_NHAN


def _lenh(db: Session, did: int) -> DispatchOrder:
    d = db.get(DispatchOrder, did)
    if d is None:
        raise ValueError(f"Không có lệnh điều xe #{did}.")
    return d


def _la_tai_xe_cua_lenh(db: Session, u: User, d: DispatchOrder) -> bool:
    """Người đang đăng nhập CÓ PHẢI tài xế ghi trên lệnh này không.

    Nối qua `Employee.user_id` chứ không so tên: hai người trùng họ tên là chuyện có thật trong
    một công ty hơn trăm người, và một lệnh nhận nhầm người thì sáng hôm sau không có xe ra bến.
    """
    e = db.get(Employee, d.driver_id)
    return e is not None and e.user_id is not None and e.user_id == u.id


def nhan(db: Session, u: User, did: int) -> DispatchOrder:
    """Tài xế bấm NHẬN."""
    d = _lenh(db, did)
    if d.status in KHONG_CHO_NHAN:
        raise ValueError(f"Lệnh #{d.id} đang ở '{d.status}' – không còn chờ ai nhận.")
    if d.nhan_luc is not None:
        # Không coi là lỗi nặng, nhưng cũng không ghi đè dấu cũ: giờ nhận lần đầu là dữ liệu.
        raise ValueError(f"Lệnh #{d.id} đã được nhận lúc {d.nhan_luc:%d/%m %H:%M} rồi.")
    d.nhan_luc = datetime.now()
    d.nhan_boi = u.username
    # Nhận rồi thì lý do từ chối cũ (nếu có) hết hiệu lực — tài xế đổi ý là chuyện bình thường, và
    # để lại một lý do từ chối bên cạnh một dấu đã nhận là để lại hai câu nói ngược nhau.
    d.tu_choi_nhan_ly_do = ""
    db.flush()
    R.audit(db, u.username, u.role, "tai_xe_nhan_lenh", f"dispatch:{d.id}",
            after={"nhan_luc": d.nhan_luc.isoformat()})
    return d


def tu_choi(db: Session, u: User, did: int, ly_do: str) -> DispatchOrder:
    """Tài xế bấm KHÔNG NHẬN ĐƯỢC. Lệnh VẪN HIỆU LỰC (luật 1)."""
    d = _lenh(db, did)
    if d.status in KHONG_CHO_NHAN:
        raise ValueError(f"Lệnh #{d.id} đang ở '{d.status}' – không còn chờ ai nhận.")
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do không nhận được – đây là câu trả lời cho báo cáo đối "
                         "chiếu tour/lượt xe tháng sau.")
    d.tu_choi_nhan_ly_do = ly_do.strip()[:300]
    d.nhan_luc = None
    d.nhan_boi = ""
    db.flush()
    R.audit(db, u.username, u.role, "tai_xe_tu_choi_nhan_lenh", f"dispatch:{d.id}",
            after={"ly_do": d.tu_choi_nhan_ly_do})
    return d


def xoa_dau_nhan(db: Session, d: DispatchOrder, vi_sao: str, boi: str = "") -> bool:
    """LUẬT 3: lệnh bị SỬA thì dấu nhận cũ hết hiệu lực, tài xế phải nhận lại.

    Trả về True khi thật sự có dấu để xoá — để nơi gọi biết mà nói lại cho người sửa, thay vì âm
    thầm bắt tài xế bấm lần nữa mà không ai báo.
    """
    if d.nhan_luc is None and not (d.tu_choi_nhan_ly_do or "").strip():
        return False
    d.nhan_luc = None
    d.nhan_boi = ""
    d.tu_choi_nhan_ly_do = ""
    db.flush()
    R.audit(db, boi or "he_thong", "", "xoa_dau_nhan_lenh", f"dispatch:{d.id}",
            after={"vi_sao": vi_sao})
    return True


def _dong(db: Session, d: DispatchOrder, bay_gio: datetime, ten_xe: dict, ten_nv: dict) -> dict:
    tt = trang_thai_nhan(d, bay_gio)
    h = han_nhan(d)
    con = (h - bay_gio).total_seconds() / 3600 if h else None
    return {"id": d.id, "tour_id": d.tour_id, "vehicle_id": d.vehicle_id,
            "xe": ten_xe.get(d.vehicle_id, ""), "tai_xe": ten_nv.get(d.driver_id, ""),
            "ngay_di": d.date_from.isoformat() if d.date_from else None,
            "ngay_ve": d.date_to.isoformat() if d.date_to else None,
            "trang_thai_lenh": d.status,
            "trang_thai_nhan": tt, "trang_thai_nhan_ten": TEN[tt],
            "han_nhan": h.isoformat() if h else None,
            "con_lai_gio": (round(con, 1) if con is not None else None),
            "nhan_luc": d.nhan_luc.isoformat() if d.nhan_luc else None,
            "nhan_boi": d.nhan_boi, "tu_choi_nhan_ly_do": d.tu_choi_nhan_ly_do}


def can_giam_doc_xe_biet(db: Session) -> dict:
    """Những lệnh Giám đốc đội xe CẦN BIẾT: quá hạn chưa nhận, và tài xế đã báo không nhận được.

    Gộp hai nhóm vào MỘT cửa chứ không hai: với ông cả hai đều là một việc — "chuyến này chưa chắc
    có người lái". Tách ra là bắt ông mở hai chỗ để trả lời một câu hỏi.
    """
    from app.models.hr import Vehicle
    bay_gio = datetime.now()
    ten_xe = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    ten_nv = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    ds = [d for d in db.execute(select(DispatchOrder).where(
        DispatchOrder.status.notin_(KHONG_CHO_NHAN)).order_by(DispatchOrder.date_from)).scalars()]
    qua_han = [d for d in ds if trang_thai_nhan(d, bay_gio) == QUA_HAN]
    tu_choi_ds = [d for d in ds if trang_thai_nhan(d, bay_gio) == TU_CHOI]
    da_nhan = [d for d in ds if trang_thai_nhan(d, bay_gio) == DA_NHAN]
    return {
        "qua_han": [_dong(db, d, bay_gio, ten_xe, ten_nv) for d in qua_han],
        "tu_choi": [_dong(db, d, bay_gio, ten_xe, ten_nv) for d in tu_choi_ds],
        "dem": {"qua_han": len(qua_han), "tu_choi": len(tu_choi_ds), "da_nhan": len(da_nhan),
                "dang_cho": len(ds)},
        "han_gio": HAN_GIO,
        "ghi_chu": (f"Hạn nhận là {HAN_GIO} giờ trước ngày đi. Quá hạn KHÔNG huỷ lệnh và không "
                    "chặn ai – lệnh vẫn hiệu lực, đây chỉ là chỗ để Giám đốc đội xe thấy sớm."),
    }


def da_nhan_trong_tuan(db: Session, moc: date | None = None) -> int:
    """Đếm lệnh tài xế đã nhận trong 7 ngày gần nhất.

    Có mặt vì một lý do: con số "2 lệnh quá hạn" đứng một mình không nói được gì. 2 trên 13 là
    chuyện thường; 2 trên 3 là đội xe đang có vấn đề.
    """
    d2 = moc or date.today()
    d1 = d2 - timedelta(days=6)
    n = 0
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.nhan_luc.isnot(None))).scalars():
        if d1 <= d.nhan_luc.date() <= d2:
            n += 1
    return n
