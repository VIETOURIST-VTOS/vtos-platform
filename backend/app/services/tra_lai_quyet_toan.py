# -*- coding: utf-8 -*-
"""Chuyến bị Kế toán trả lại quyết toán — nhận ra được, không thêm trạng thái mới (19/10/2026).

Nút «Trả lại Điều hành sửa» có từ lâu (`settlement.kt_return`): chuyến về `ket_thuc`, tăng phiên
bản quyết toán, ghi sự kiện `kt_tra_lai` kèm lý do. Nhưng `ket_thuc` sau khi bị trả lại trông Y HỆT
`ket_thuc` chưa ai đóng số, nên Điều hành không biết chuyến nào bị trả, cũng không thấy lý do.

LUẬT NHẬN RA: chuyến đang `ket_thuc`, và trong lịch sử chuyến, sự kiện quyết toán GẦN NHẤT thuộc
cặp (đóng số, Kế toán trả lại) là `kt_tra_lai`. Đóng số lại thì sự kiện gần nhất thành `dong_so`
và chuyến tự ra khỏi danh sách. Đọc từ lịch sử đã ghi, nên các lần trả lại TRƯỚC hôm nay cũng hiện.

Không thêm trạng thái vào `TOUR_STATUS`: hàng chục chỗ đang so `status == "ket_thuc"` (hạn quyết
toán, ô bàn làm việc, cổng đóng số); một trạng thái mới là phải đi sửa hết các chỗ ấy, và sót một
chỗ là chuyến bị trả lại rơi khỏi hạn quyết toán.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, TourEvent

CAP = ("dong_so", "kt_tra_lai")


def dang_bi_tra_lai(db: Session, tour_ids: list[int] | None = None) -> dict[int, TourEvent]:
    """{tour_id: sự kiện kt_tra_lai gần nhất} cho những chuyến ĐANG ở trạng thái bị trả lại.
    Một lượt đọc cho mọi chuyến — không truy vấn trong vòng lặp."""
    q = select(Tour.id).where(Tour.status == "ket_thuc")
    if tour_ids is not None:
        q = q.where(Tour.id.in_(tour_ids))
    ids = list(db.execute(q).scalars())
    if not ids:
        return {}
    cuoi: dict[int, TourEvent] = {}
    for ev in db.execute(select(TourEvent).where(TourEvent.tour_id.in_(ids), TourEvent.step.in_(CAP))
                         .order_by(TourEvent.at, TourEvent.id)).scalars():
        cuoi[ev.tour_id] = ev
    return {tid: ev for tid, ev in cuoi.items() if ev.step == "kt_tra_lai"}


def mo_ta(ev: TourEvent | None, phien_ban: int | None = None) -> dict | None:
    if ev is None:
        return None
    return {"luc": ev.at.isoformat() if ev.at else None, "ai": ev.actor or "", "ly_do": ev.note or "",
            "phien_ban": phien_ban}


# ─────────────── PC-1 · chuông «Kế toán trả lại quyết toán» (Chủ tịch duyệt 19/10/2026) ───────────────
# Báo cho NGƯỜI GIỮ HỒ SƠ (đúng cổng `chu_ho_so`: tour đoàn → Sale Admin, tour lẻ → Điều hành, bàn
# giao thắng) và Trưởng phòng Điều hành. Người giữ hồ sơ là CHỦ của chuông (`nguoi_phu_trach`) — gửi
# cho hai vai mà không có chủ là gửi cho không ai (PQ-9). Tự tắt khi chuyến được đóng số lại.
CHUONG_TRA_LAI = "qt_tra_lai"


def bao_chuong_tra_lai(db: Session, t: Tour, ly_do: str) -> None:
    from app.models.core import User
    from app.services import chu_ho_so as CHS
    from app.services import cskh as CS
    chu_id = CHS.chu_ho_so(db, t)
    chu = db.get(User, chu_id) if chu_id else None
    vai = ["tp_dh"] + ([chu.role] if chu and chu.role and chu.role != "tp_dh" else [])
    tat_chuong_tra_lai(db, t, "Kế toán trả lại lần nữa — chuông mới thay chuông cũ")
    CS.giao_viec(db, CHUONG_TRA_LAI, f"tour:{t.code}",
                 f"Kế toán trả lại quyết toán {t.code} · «{(ly_do or '').strip()[:200]}»",
                 nguoi_id=chu_id, han_gio=None, roles=",".join(vai), level="warn")


def tat_chuong_tra_lai(db: Session, t: Tour, vi_sao: str) -> int:
    from datetime import datetime
    from app.models.core import Alert
    n = 0
    for a in db.execute(select(Alert).where(Alert.kind == CHUONG_TRA_LAI, Alert.ref == f"tour:{t.code}",
                                            Alert.resolved == False)).scalars():  # noqa: E712
        a.resolved, a.trang_thai = True, "dong"
        a.dong_luc, a.bang_chung = datetime.now(), f"Tự đóng: {vi_sao}"
        n += 1
    return n
