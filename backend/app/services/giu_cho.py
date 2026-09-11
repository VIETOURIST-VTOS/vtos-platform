"""Giữ chỗ có thời hạn — chỗ ngồi quay về tour khi không ai trả tiền cho nó.

Xem app/models/giu_cho.py để biết vì sao phân hệ này tồn tại và ba quyết định đã chốt. Tệp này giữ
các luật ấy:

  1. Chỉ booking CHƯA THU ĐỒNG NÀO mới hết hạn giữ chỗ. Có tiền vào là có cam kết.
  2. Hết hạn thì TRẢ CHỖ, KHÔNG huỷ booking. Robot không được xoá cam kết với khách.
  3. Gia hạn và khôi phục đều phải có người và có lý do; mỗi lần đều ghi lại và ĐẾM.
  4. Khôi phục chỉ được khi tour CÒN CHỖ. Hết chỗ mà vẫn cho khôi phục là bán trùng ghế.
"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Alert, Booking, Tour, User
from app.models.giu_cho import NhatKyGiuCho
from app.services import rules as R

GIA_HAN_ROLES = ("nv_dh", "tp_dh", "gd_kd", "tp_kd", "cntt", "tgd")

# Gia hạn quá số lần này thì vẫn cho, nhưng kêu lên. Không chặn: có tour khách thật sự cần chờ duyệt
# ngân sách nhiều vòng. Chặn ở đây chỉ đẩy Điều hành sang huỷ rồi tạo lại booking, và khi ấy hệ thống
# mất luôn dấu vết của cả chuỗi chờ đợi.
NGUONG_GIA_HAN = 3


def _ghi(db: Session, b: Booking, viec: str, han_cu, han_moi, boi: str, ly_do: str = "") -> NhatKyGiuCho:
    n = NhatKyGiuCho(booking_id=b.id, viec=viec, han_cu=han_cu, han_moi=han_moi,
                     so_cho=b.pax, boi=boi, ly_do=(ly_do or "")[:300])
    db.add(n)
    return n


def han_mac_dinh(db: Session, b: Booking, t: Tour | None = None) -> datetime:
    """Hạn giữ chỗ mặc định: từ lúc tạo booking cộng `han_giu_cho_gio`, nhưng KHÔNG muộn hơn deadline
    hủy chỗ của tour.

    Chặn trên là điều bắt buộc chứ không phải làm cho đẹp: hạn giữ chỗ muộn hơn deadline hủy chỗ thì
    chỗ ấy được giữ qua cả thời điểm tour đã đóng — lúc ấy Điều hành không còn cách nào bán lại.
    """
    gio = float(R.get_param(db, "han_giu_cho_gio"))
    han = (b.created_at or datetime.now()) + timedelta(hours=gio)
    if b.cancel_deadline and han > b.cancel_deadline:
        han = b.cancel_deadline
    return han


def dat_han(db: Session, b: Booking, t: Tour | None = None, boi: str = "he_thong") -> datetime:
    """Đặt hạn giữ chỗ lần đầu. Gọi khi tạo booking, và cho booking cũ chưa có hạn."""
    b.giu_cho_den = han_mac_dinh(db, b, t)
    _ghi(db, b, "dat_han", None, b.giu_cho_den, boi, "Đặt hạn giữ chỗ khi tạo booking")
    return b.giu_cho_den


def con_trong(db: Session, t: Tour) -> int:
    """Số chỗ còn trống của tour = chỗ mở bán − chỗ ĐANG được giữ.

    Booking đã hết hạn giữ chỗ không nằm trong `booked_pax` nữa, nên một booking đang xin quay lại
    không bị trừ hai lần.
    """
    mo = t.seats_open or t.planned_pax or 0
    dang_giu = R.booked_pax(t)
    return int(mo) - int(dang_giu)


# ---------- robot: trả chỗ về ----------
def het_han_giu_cho(db: Session) -> dict:
    """Robot: trả chỗ về tour cho những booking quá hạn giữ mà CHƯA THU ĐỒNG NÀO.

    Cũng đặt hạn cho các booking chưa có hạn (booking tạo trước 11/9/2026) — đặt xong mới tính đến
    chuyện hết hạn, không bao giờ trong cùng một lượt: một booking vừa được đặt hạn lần đầu mà lập tức
    bị tuyên hết hạn là cách chắc chắn nhất để trả về hàng loạt chỗ mà không ai kịp nhìn.
    """
    now = datetime.now()
    dat, het, ma_het = 0, 0, []

    q = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(
        Booking.cancelled == False, Booking.giu_cho_den == None,          # noqa: E711,E712
        Tour.start_date >= now.date())
    for b in db.execute(q).scalars():
        dat_han(db, b); dat += 1

    q2 = select(Booking).join(Tour, Tour.id == Booking.tour_id).where(
        Booking.cancelled == False, Booking.giu_cho_het == False,          # noqa: E712
        Booking.giu_cho_den != None, Booking.giu_cho_den < now,            # noqa: E711
        Tour.start_date >= now.date())
    for b in db.execute(q2).scalars():
        if (b.paid or 0) > 0:
            continue                      # luật 1: có tiền vào là có cam kết, không đụng tới
        b.giu_cho_het, b.giu_cho_het_luc = True, now
        _ghi(db, b, "het_han", b.giu_cho_den, None, "robot",
             f"Quá hạn giữ chỗ {b.giu_cho_den:%d/%m %H:%M} mà chưa thu đồng nào – trả {b.pax} chỗ về tour")
        het += 1; ma_het.append(b.code)
        ref = f"giucho:{b.code}"
        if not db.execute(select(Alert).where(Alert.kind == "het_han_giu_cho", Alert.ref == ref,
                                              Alert.resolved == False)).scalars().first():   # noqa: E712
            db.add(Alert(kind="het_han_giu_cho", level="warn", ref=ref,
                         message=(f"{b.code} ({b.customer_name}, {b.tour.code}) hết hạn giữ chỗ – đã trả "
                                  f"{b.pax} chỗ về tour. Booking VẪN CÒN: khách trả tiền thì khôi phục nếu còn chỗ."),
                         to_roles="nv_kd,gd_kd,nv_dh,tp_dh"))

    if het or dat:
        R.audit(db, "robot", "robot", "het_han_giu_cho", "robot",
                after={"dat_han": dat, "het_han": het, "booking": ma_het[:50]})
    db.commit()
    return {"dat_han": dat, "het_han": het, "booking": ma_het}


# ---------- người: gia hạn, khôi phục ----------
def gia_han(db: Session, u: User, b: Booking, den: datetime, ly_do: str) -> dict:
    if u.role not in GIA_HAN_ROLES:
        raise ValueError("Chỉ Điều hành / Kinh doanh cấp quản lý gia hạn được giữ chỗ")
    if b.cancelled:
        raise ValueError("Booking đã huỷ – gia hạn giữ chỗ không còn nghĩa gì")
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do gia hạn – một chỗ bị giữ thêm là một chỗ không bán cho khách khác")
    if den <= datetime.now():
        raise ValueError("Hạn mới phải ở tương lai")
    if b.cancel_deadline and den > b.cancel_deadline:
        raise ValueError(f"Hạn giữ chỗ không được muộn hơn deadline hủy chỗ "
                         f"{b.cancel_deadline:%d/%m/%Y %H:%M} – qua mốc ấy tour đã đóng, không bán lại được")

    t = db.get(Tour, b.tour_id)
    khoi_phuc_lai = bool(b.giu_cho_het)
    if khoi_phuc_lai:
        # Gia hạn cho một booking đã trả chỗ về = xin chỗ lại. Phải còn chỗ mới được.
        trong = con_trong(db, t) if t else 0
        if trong < b.pax:
            raise ValueError(f"Tour chỉ còn {trong} chỗ, booking cần {b.pax} – không khôi phục được. "
                             f"Muốn giữ thì Điều hành phải mở thêm chỗ hoặc sắp xếp lại tour.")
        b.giu_cho_het, b.giu_cho_het_luc = False, None

    han_cu = b.giu_cho_den
    b.giu_cho_den = den
    b.gia_han_lan = int(b.gia_han_lan or 0) + 1
    _ghi(db, b, "khoi_phuc" if khoi_phuc_lai else "gia_han", han_cu, den, u.username, ly_do)
    R.audit(db, u.username, u.role, "gia_han_giu_cho", f"booking:{b.code}",
            before={"han": han_cu.isoformat() if han_cu else None, "da_het_han": khoi_phuc_lai},
            after={"han": den.isoformat(), "lan_thu": b.gia_han_lan, "ly_do": ly_do.strip()})

    canh_bao = ""
    if b.gia_han_lan > NGUONG_GIA_HAN:
        canh_bao = (f"Booking này đã gia hạn {b.gia_han_lan} lần. Một chỗ giữ mãi dưới danh nghĩa hợp lệ "
                    f"vẫn là một chỗ không bán được – cân nhắc yêu cầu khách đặt cọc.")
    db.commit()
    return {"giu_cho_den": b.giu_cho_den, "gia_han_lan": b.gia_han_lan, "canh_bao": canh_bao,
            "message": (f"Đã khôi phục giữ chỗ tới {den:%d/%m %H:%M}" if khoi_phuc_lai
                        else f"Đã gia hạn giữ chỗ tới {den:%d/%m %H:%M}")}


def khoi_phuc(db: Session, u: User, b: Booking, ly_do: str) -> dict:
    """Khách trả tiền muộn (hoặc người quyết định): giữ lại chỗ, hạn tính lại từ bây giờ."""
    if not b.giu_cho_het:
        raise ValueError("Booking này đang giữ chỗ bình thường, không có gì để khôi phục")
    gio = float(R.get_param(db, "han_giu_cho_gio"))
    den = datetime.now() + timedelta(hours=gio)
    if b.cancel_deadline and den > b.cancel_deadline:
        den = b.cancel_deadline
    return gia_han(db, u, b, den, ly_do or "Khôi phục giữ chỗ")


# ---------- màn hình ----------
def bang(db: Session, b: Booking) -> dict:
    t = db.get(Tour, b.tour_id)
    ds = [{"id": n.id, "viec": n.viec, "han_cu": n.han_cu, "han_moi": n.han_moi, "so_cho": n.so_cho,
           "ly_do": n.ly_do, "boi": n.boi, "luc": n.luc}
          for n in db.execute(select(NhatKyGiuCho).where(NhatKyGiuCho.booking_id == b.id)
                              .order_by(NhatKyGiuCho.id)).scalars()]
    con = (datetime.now() - b.giu_cho_den).total_seconds() if b.giu_cho_den else None
    return {
        "booking_id": b.id, "code": b.code, "pax": b.pax,
        "giu_cho_den": b.giu_cho_den, "giu_cho_het": b.giu_cho_het, "giu_cho_het_luc": b.giu_cho_het_luc,
        "gia_han_lan": b.gia_han_lan, "da_thu": float(b.paid or 0),
        "cancel_deadline": b.cancel_deadline,
        "qua_han": bool(b.giu_cho_den and con is not None and con > 0 and not b.giu_cho_het),
        "cho_con_trong": con_trong(db, t) if t else None,
        "nhat_ky": ds,
        "ghi_chu_man_hinh": ("Hết hạn giữ chỗ KHÔNG phải huỷ booking: booking vẫn còn, chỉ là chỗ đã trả "
                             "về tour. Khách trả tiền muộn thì khôi phục – nếu tour còn chỗ."),
    }


def tong_hop(db: Session) -> dict:
    """Bao nhiêu chỗ đang bị giữ mà chưa có tiền, và bao nhiêu chỗ đã được trả về."""
    now = datetime.now()
    dang_giu_chua_thu = db.execute(
        select(func.coalesce(func.sum(Booking.pax), 0)).where(
            Booking.cancelled == False, Booking.giu_cho_het == False,     # noqa: E712
            func.coalesce(Booking.paid, 0) <= 0)).scalar() or 0
    sap_het = db.execute(
        select(func.count()).select_from(Booking).where(
            Booking.cancelled == False, Booking.giu_cho_het == False,     # noqa: E712
            Booking.giu_cho_den != None,                                   # noqa: E711
            Booking.giu_cho_den <= now + timedelta(hours=12),
            Booking.giu_cho_den > now)).scalar() or 0
    da_tra = db.execute(
        select(func.coalesce(func.sum(Booking.pax), 0)).where(
            Booking.cancelled == False, Booking.giu_cho_het == True)).scalar() or 0   # noqa: E712
    return {"cho_dang_giu_chua_thu": int(dang_giu_chua_thu), "booking_sap_het_han_12h": int(sap_het),
            "cho_da_tra_ve": int(da_tra)}
