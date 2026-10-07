"""Sinh và quản hàng đợi chuyển đổi gửi ngược về nền tảng quảng cáo.

Tệp này KHÔNG gọi API của nền tảng nào. Nó chuẩn bị việc; bộ gửi của từng nền tảng là vòng sau,
và nó cần token mà hôm nay chưa ai dán. Tách hai phần có chủ ý: hàng đợi chạy và tích dữ liệu
được NGAY, còn bộ gửi thì chờ cấu hình — thay vì cả hai cùng chờ và mọi chuyển đổi phát sinh
trong lúc chờ đều mất.
"""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Booking
from app.models.crm import Lead
from app.models.quang_cao import DauQuangCao, ChuyenDoiGuiDi

# Quá hạn thì nền tảng từ chối, nên gửi muộn không chỉ vô ích mà còn làm bẩn bảng lỗi. Con số
# thận trọng: Google nhận chuyển đổi ngoại tuyến trong một cửa sổ tính bằng tháng, Meta và TikTok
# hẹp hơn. Lấy mốc chặt nhất cho cả ba thay vì ba mốc khác nhau — ba mốc thì ba chỗ phải nhớ.
HAN_NGAY = 60


def _booking_cua_lead(db: Session, l: Lead) -> Booking | None:
    """Booking đã chốt của một lead. Ưu tiên mã do người nhập, rồi tới dấu do robot đối chiếu gắn.

    Không tự tìm theo số điện thoại ở đây: việc ấy là `leads.match_conversions()`, nó có luật
    riêng và đã chạy. Dựng một đường khớp thứ hai ở đây là dựng một con số thứ hai cho cùng câu
    hỏi, và ngày hai con số lệch nhau thì không ai biết tin cái nào.
    """
    if getattr(l, "ma_booking", None):
        b = db.execute(select(Booking).where(Booking.code == l.ma_booking)).scalars().first()
        if b:
            return b
    if l.booking_id:
        return db.get(Booking, l.booking_id)
    return None


def khoa(nen_tang: str, ma_booking: str, dau_id: int) -> str:
    return f"{nen_tang}:{ma_booking}:{dau_id}"[:300]


def sinh(db: Session) -> dict:
    """Quét dấu đã khớp lead, lead đã chốt booking, rồi xếp một dòng cho mỗi nền tảng.

    BOOKING ĐÃ HUỶ THÌ KHÔNG SINH. Nhưng nếu một booking đã GỬI RỒI mới bị huỷ thì nền tảng vẫn
    đang giữ một chuyển đổi không có thật, và vòng này CHƯA đảo được nó — cần một lượt gửi "đảo
    chuyển đổi" mà ba nền tảng làm theo ba cách khác nhau. Chỗ thiếu ấy ghi ra đây và đếm được ở
    `bang_do()['da_gui_nhung_huy']`, thay vì để nó thành một sai lệch không ai biết.
    """
    moi = da_co = thieu = 0
    for d in db.execute(select(DauQuangCao).where(DauQuangCao.lead_id.is_not(None))).scalars():
        l = db.get(Lead, d.lead_id)
        if l is None:
            continue
        b = _booking_cua_lead(db, l)
        if b is None or b.cancelled:
            continue
        k = khoa(d.nen_tang, b.code, d.id)
        if db.execute(select(ChuyenDoiGuiDi)
                      .where(ChuyenDoiGuiDi.khoa_chong_trung == k)).scalars().first():
            da_co += 1
            continue
        co_tien = b.amount is not None
        if not co_tien:
            thieu += 1
        db.add(ChuyenDoiGuiDi(
            dau_id=d.id, lead_id=l.id, nen_tang=d.nen_tang, loai_ma=d.loai_ma, ma=d.ma,
            ma_booking=b.code, doanh_thu=b.amount, tien_te="VND",
            chot_luc=(l.converted_at or b.created_at),
            trang_thai=("cho_gui" if co_tien else "thieu_doanh_thu"),
            khoa_chong_trung=k))
        moi += 1
    if moi:
        db.commit()
    return {"moi": moi, "da_co": da_co, "thieu_doanh_thu": thieu}


def cho_gui(db: Session, gioi_han: int = 100, nen_tang: str = "") -> list[ChuyenDoiGuiDi]:
    """Việc bộ gửi lấy ra làm. Chỉ dòng CÓ doanh thu – xem vì sao ở docstring của bảng.

    `nen_tang` KHÔNG phải tiện nghi mà là hàng rào. Mỗi nền tảng có bộ gửi riêng, và bộ gửi
    Meta mà cầm nhầm một dòng gclid thì nó sẽ đánh dấu dòng ấy "bỏ qua" – tức là cướp việc
    của bộ gửi Google và dòng ấy không bao giờ được gửi đi đâu nữa. Lọc ở đây, một chỗ.
    """
    q = select(ChuyenDoiGuiDi).where(ChuyenDoiGuiDi.trang_thai == "cho_gui")
    if nen_tang.strip():
        q = q.where(ChuyenDoiGuiDi.nen_tang == nen_tang.strip().lower())
    return list(db.execute(q.order_by(ChuyenDoiGuiDi.id)
                           .limit(max(1, min(gioi_han, 1000)))).scalars())


def ghi_ket_qua(db: Session, cd: ChuyenDoiGuiDi, xong: bool, tra_loi: str = "",
                loi: str = "") -> ChuyenDoiGuiDi:
    """Bộ gửi báo lại. Lỗi KHÔNG xoá dòng – giữ lại để đếm được và để gửi lại."""
    cd.lan_thu = (cd.lan_thu or 0) + 1
    cd.tra_loi = str(tra_loi or "")[:4000]
    if xong:
        cd.trang_thai, cd.gui_luc, cd.loi_cuoi = "da_gui", datetime.now(), ""
    else:
        cd.trang_thai, cd.loi_cuoi = "loi", str(loi or "")[:2000]
    db.commit()
    return cd


def bang_do(db: Session) -> dict:
    """Bảng số của màn hình. RỖNG KHÁC KHÔNG ở mọi tỷ lệ."""
    theo_tt = {k: int(v) for k, v in db.execute(
        select(ChuyenDoiGuiDi.trang_thai, func.count())
        .group_by(ChuyenDoiGuiDi.trang_thai)).all()}
    tong = sum(theo_tt.values())
    da_gui = theo_tt.get("da_gui", 0)

    # Đã gửi rồi mà booking sau đó bị huỷ: nền tảng đang giữ một chuyển đổi không có thật. Vòng
    # này chưa đảo được, nên ít nhất phải ĐẾM ĐƯỢC. Một sai lệch đếm được là một sai lệch sửa
    # được; một sai lệch im lặng thì không.
    huy = [c.ma_booking for c in db.execute(
        select(ChuyenDoiGuiDi).where(ChuyenDoiGuiDi.trang_thai == "da_gui")).scalars()
        if (lambda b: b is not None and b.cancelled)(
            db.execute(select(Booking).where(Booking.code == c.ma_booking)).scalars().first())]

    return {"tong": tong, "theo_trang_thai": theo_tt,
            "ty_le_gui_duoc": (round(da_gui / tong, 3) if tong else None),
            "da_gui_nhung_huy": sorted(set(huy)),
            # Nhắc ngay trong dữ liệu, để màn hình nào in bảng này cũng phải in kèm câu cảnh báo.
            "luu_y": "Doanh thu của một booking được báo ĐẦY ĐỦ cho từng nền tảng có dự phần, "
                     "không chia. Tổng ba nền tảng vì thế có thể lớn hơn doanh thu thật – KHÔNG "
                     "cộng ba con số này lại. Câu hỏi 'kênh nào mang về bao nhiêu tiền' là việc "
                     "quy kết, thuộc một bảng khác."}
