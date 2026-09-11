# -*- coding: utf-8 -*-
"""PQ-9 · Giao chủ cho cảnh báo – một cảnh báo một người.

Đo bản đang chạy sáng 11/9/2026:

    1.703 cảnh báo · 1.310 đỏ · 1.557 chưa xử lý · 146 từng được xử lý
    sinh khoảng 218 cái mỗi ngày, cái cũ nhất từ 05/9

Chỗ hỏng không nằm ở số lượng. Nó nằm ở cột người nhận: một cảnh báo đỏ "quá deadline thu tiền"
gửi cho "nv_kd,gd_kd,tp_dh,ketoan". Gửi cho bốn vai trò là không gửi cho ai — mỗi người mở ra đều
thấy ba người khác cũng nhận được, nên việc chờ ở đó cho tới lúc không còn ai nhớ nó tồn tại.

Tỷ lệ 146 trên 1.703 không đo sự lười. Nó đo một danh sách người nhận không có chủ.

────────────────────────────────────────────────────────────────────────────────────────────────
CÁCH SUY RA CHỦ

Không hỏi thêm ai, và không thêm một bước nhập tay nào: mỗi cảnh báo đã trỏ tới một hồ sơ cụ thể
qua cột `ref`, và mỗi hồ sơ ấy vốn đã có người phụ trách. Việc phải làm chỉ là ĐỌC RA và GHI XUỐNG.

    qua_han_qt         ref = mã chuyến          → người điều hành chuyến
    qua_deadline_thu   ref = booking:<mã>       → sale phụ trách booking
    bc_ngay_1 / _2     ref = <mã NV>:<ngày>     → chính người đó
    cham_soc_qua_han   ref = cs:<id>            → người giữ phiếu chăm sóc
    sale_tra_loi_cham  ref = conv:<id>          → sale phụ trách hội thoại

`to_roles` GIỮ NGUYÊN. Hai cột trả lời hai câu khác nhau: ai được báo tin, và ai phải trả lời. Gộp
lại thì mất đúng cái khác biệt vừa làm ra.

Suy không ra thì để TRỐNG và đếm — không đẩy bừa lên cấp trên. Một cảnh báo dòng tiền gửi Ban lãnh
đạo vốn không có chủ đơn lẻ, gán đại cho một người là tạo ra một người chịu trách nhiệm giả.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Alert, Tour, Booking, User

# Lý do không suy được – mỗi lý do là một dòng đếm được, không phải một khoảng lặng.
KHONG_CO_LUAT = "loai_canh_bao_chua_khai_cach_suy_chu"
KHONG_TIM_THAY = "khong_tim_thay_ho_so_ma_ref_tro_toi"
HO_SO_CHUA_CO_CHU = "ho_so_da_tim_thay_nhung_chinh_no_cung_chua_co_chu"

# Loại cảnh báo CỐ Ý không có chủ đơn lẻ, kèm lý do. Bắt buộc viết lý do: "loại này không cần chủ"
# là lối thoát dễ nhất cho một loại chưa ai nghĩ tới cách giao.
CO_Y_KHONG_CHU = {
    "r9_chay_duoi_hoa_von": "chuyến chạy dưới hòa vốn là quyết định của Ban lãnh đạo, không phải "
                            "việc một người xử lý xong rồi đóng lại",
    "r9_gd_cho_khop": "giao dịch ngân hàng chờ khớp gửi cả tuyến kiểm soát; gán cho một người là "
                      "tạo ra một người chịu trách nhiệm giả cho việc cần nhiều mắt nhìn",
}


def _sau_dau(ref: str, dau: str) -> str:
    return ref.split(dau, 1)[1] if dau in ref else ""


def _tour_theo_ma(db: Session, ma: str) -> Tour | None:
    return db.execute(select(Tour).where(Tour.code == ma)).scalars().first()


def suy_chu(db: Session, a: Alert) -> tuple[int | None, str]:
    """(id người phụ trách, lý do nếu không suy được). Chỉ ĐỌC, không ghi gì.

    Tách riêng khỏi `giao` để phép thử soi được từng luật một, và để màn hình xem trước được kết
    quả trước khi bấm giao hàng loạt cho 1.557 dòng.
    """
    ref = (a.ref or "").strip()
    kind = (a.kind or "").strip()

    if kind in CO_Y_KHONG_CHU:
        return None, KHONG_CO_LUAT

    if kind == "qua_han_qt":
        t = _tour_theo_ma(db, ref)
        if t is None: return None, KHONG_TIM_THAY
        return (t.operator_id, "") if t.operator_id else (None, HO_SO_CHUA_CO_CHU)

    if kind == "qua_deadline_thu":
        ma = _sau_dau(ref, "booking:")
        if not ma: return None, KHONG_TIM_THAY
        b = db.execute(select(Booking).where(Booking.code == ma)).scalars().first()
        if b is None: return None, KHONG_TIM_THAY
        return (b.sales_id, "") if b.sales_id else (None, HO_SO_CHUA_CO_CHU)

    if kind in ("bc_ngay_1", "bc_ngay_2"):
        # ref = "<mã nhân viên>:<ngày>" – chính người thiếu báo cáo là người phải nộp.
        ma = ref.split(":", 1)[0]
        if not ma: return None, KHONG_TIM_THAY
        from app.models.hr import Employee
        e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
        if e is None: return None, KHONG_TIM_THAY
        return (e.user_id, "") if e.user_id else (None, HO_SO_CHUA_CO_CHU)

    if kind == "cham_soc_qua_han":
        sid = _sau_dau(ref, "cs:")
        if not sid.isdigit(): return None, KHONG_TIM_THAY
        from app.models.cskh import CareTicket
        c = db.get(CareTicket, int(sid))
        if c is None: return None, KHONG_TIM_THAY
        return (c.owner_id, "") if c.owner_id else (None, HO_SO_CHUA_CO_CHU)

    if kind == "sale_tra_loi_cham":
        cid = _sau_dau(ref, "conv:")
        if not cid.isdigit(): return None, KHONG_TIM_THAY
        from app.models.crm import Conversation
        c = db.get(Conversation, int(cid))
        if c is None: return None, KHONG_TIM_THAY
        return (c.sales_id, "") if c.sales_id else (None, HO_SO_CHUA_CO_CHU)

    return None, KHONG_CO_LUAT


def giao(db: Session, a: Alert) -> dict:
    """Giao MỘT cảnh báo chưa có chủ. Đã có chủ thì không đụng tới, kể cả khi luật suy ra người khác.

    Vì sao không đè: người phụ trách có thể đã được chuyển tay bằng quyết định của cấp quản lý, và
    một hàm chạy nền đè lên quyết định ấy thì quyết định kia chỉ sống tới vòng quét kế tiếp.
    """
    if a.nguoi_phu_trach:
        return {"da_giao": False, "ly_do": "da_co_chu", "nguoi": a.nguoi_phu_trach}
    uid, vi_sao = suy_chu(db, a)
    if uid is None:
        return {"da_giao": False, "ly_do": vi_sao, "nguoi": None}
    a.nguoi_phu_trach = uid
    a.giao_luc = datetime.now()
    return {"da_giao": True, "ly_do": "", "nguoi": uid}


def giao_het(db: Session, *, chi_chua_xu_ly: bool = True) -> dict:
    """Quét và giao. Đếm cả phần KHÔNG giao được, tách theo lý do.

    'Đã giao 0' mà không nói vì sao thì đọc ra giống hệt 'không còn gì để giao'.
    """
    q = select(Alert).where(Alert.nguoi_phu_trach.is_(None))
    if chi_chua_xu_ly:
        q = q.where(Alert.resolved == False)  # noqa: E712
    ds = list(db.execute(q.order_by(Alert.created_at, Alert.id)).scalars())
    da = 0
    ly_do: dict[str, int] = {}
    for a in ds:
        kq = giao(db, a)
        if kq["da_giao"]:
            da += 1
        else:
            ly_do[kq["ly_do"]] = ly_do.get(kq["ly_do"], 0) + 1
    return {"xet": len(ds), "da_giao": da, "khong_giao_duoc": ly_do,
            "con_chua_co_chu": len(ds) - da}


def bao_cao(db: Session) -> dict:
    """Ba con số phải nằm ngay trên màn hình, và con số thứ ba là con số quan trọng nhất."""
    def dem(*dk):
        q = select(func.count(Alert.id)).where(Alert.resolved == False)  # noqa: E712
        for d in dk: q = q.where(d)
        return int(db.execute(q).scalar() or 0)

    tong = dem()
    co_chu = dem(Alert.nguoi_phu_trach.isnot(None))
    rows = db.execute(
        select(Alert.nguoi_phu_trach, func.count(Alert.id))
        .where(Alert.resolved == False, Alert.nguoi_phu_trach.isnot(None))  # noqa: E712
        .group_by(Alert.nguoi_phu_trach)).all()
    ten = {u.id: u.full_name for u in db.execute(select(User)).scalars()}
    theo_loai = db.execute(
        select(Alert.kind, func.count(Alert.id))
        .where(Alert.resolved == False, Alert.nguoi_phu_trach.is_(None))  # noqa: E712
        .group_by(Alert.kind)).all()
    return {
        "chua_xu_ly": tong,
        "da_co_chu": co_chu,
        "chua_co_chu": tong - co_chu,
        "theo_nguoi": sorted(({"id": int(uid), "ten": ten.get(int(uid), f"#{uid}"), "so": int(n)}
                              for uid, n in rows), key=lambda x: -x["so"]),
        "chua_co_chu_theo_loai": sorted(({"loai": k, "so": int(n),
                                          "co_y": CO_Y_KHONG_CHU.get(k, "")} for k, n in theo_loai),
                                        key=lambda x: -x["so"]),
        "ghi_chu": ("Cột 'được báo tin' (to_roles) giữ nguyên và khác cột 'người phải trả lời'. "
                    "Chưa có chủ là một dòng riêng đếm được, không gộp vào ai và không đẩy lên cấp "
                    "trên cho đỡ trống."),
    }
