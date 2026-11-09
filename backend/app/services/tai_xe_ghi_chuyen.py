# -*- coding: utf-8 -*-
"""TÀI XẾ GHI CHUYẾN TRÊN ĐIỆN THOẠI — Chủ tịch duyệt bản xem trước 10/11/2026 (đội xe vào vận hành).

Luồng:  tài xế NHẬN lệnh → «Bắt đầu chuyến» (km lúc xuất bến, ảnh đồng hồ) → ghi từng lần đổ dầu, cầu
đường, gửi xe (kèm ảnh hoá đơn) → «Kết thúc chuyến» (km lúc về) → «Gửi cho Giám đốc đội xe».

Năm luật:
  1. Một lệnh một phiếu chuyến. Phiếu do tài xế mở GẮN SẴN lệnh, xe, tài xế, tour, ngày đi/về theo lệnh —
     tài xế không gõ lại những thứ lệnh đã nói.
  2. Phiếu nằm ở trạng thái «Nháp – tài xế đang ghi» (`nhap`, đã có sẵn trong TRIP_STATUS) và CHƯA vào
     lợi nhuận (`quyet_toan = False`). Vào lợi nhuận là việc của Chủ tịch khi duyệt tờ báo cáo xe.
  3. Tài xế KHÔNG ghi doanh thu và không thấy giá thuê nội bộ. Doanh thu là việc của Giám đốc đội xe.
  4. Gửi rồi thì tài xế không sửa được nữa (`cho_xac_nhan`). Giám đốc đội xe mở đúng phiếu ấy ở cửa
     nhập báo cáo xe bốn bước, kiểm số, thêm doanh thu rồi gửi Chủ tịch.
  5. Khoản từ ngưỡng chứng từ trở lên (B6) phải có ảnh hoá đơn hoặc số hoá đơn — cùng luật với cửa
     nhập của đội xe, không nới cho điện thoại.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.models.fleet import BEN_CHIU, COST_KINDS, TRA_BANG, Trip, TripCost
from app.models.hr import DispatchOrder, Vehicle
from app.services import rules as R

# Tài xế chỉ ghi các khoản phát sinh TRÊN ĐƯỜNG. Công tác phí theo ngày do đội xe tính theo lệnh; sửa chữa
# đi qua báo hỏng → đề nghị sửa chữa, không ghi tay ở đây.
KHOAN_TAI_XE = ("dau", "cau_duong", "giu_xe", "khac")
NGUON = "tai_xe"


class LoiGhiChuyen(ValueError):
    pass


def phieu_cua_lenh(db: Session, d: DispatchOrder) -> Trip | None:
    return db.execute(select(Trip).where(Trip.dispatch_id == d.id, Trip.status != "huy")
                      .order_by(Trip.id)).scalars().first()


def _cho_ghi(t: Trip | None) -> Trip:
    if t is None:
        raise LoiGhiChuyen("Chưa bắt đầu chuyến – bấm «Bắt đầu chuyến» và ghi km lúc xuất bến trước")
    if t.status != "nhap":
        raise LoiGhiChuyen("Phiếu chuyến đã gửi Giám đốc đội xe – tài xế không sửa được nữa. "
                           "Cần sửa thì báo Giám đốc đội xe.")
    return t


def bat_dau(db: Session, u: User, d: DispatchOrder, km_dau: int | None) -> Trip:
    if d.status == "huy":
        raise LoiGhiChuyen("Lệnh đã huỷ – không mở chuyến được")
    if d.nhan_luc is None:
        raise LoiGhiChuyen("Nhận lệnh trước rồi mới bắt đầu chuyến")
    if phieu_cua_lenh(db, d) is not None:
        raise LoiGhiChuyen("Lệnh này đã có phiếu chuyến – mở phiếu đang có để ghi tiếp")
    if km_dau is None or km_dau <= 0:
        raise LoiGhiChuyen("Ghi số km trên đồng hồ lúc xuất bến")
    t = db.get(Tour, d.tour_id) if d.tour_id else None
    tr = Trip(vehicle_id=d.vehicle_id, driver_id=d.driver_id, dispatch_id=d.id, tour_id=d.tour_id,
              ten_tour=(f"{t.code} · {t.name}" if t else "")[:160], ngay_di=d.date_from, ngay_ve=d.date_to,
              km_dau=km_dau, km_nguon="anh_dong_ho", status="nhap", quyet_toan=False, nguon=NGUON,
              created_by=u.username, note="Tài xế ghi trên điện thoại")
    db.add(tr); db.flush()
    R.audit(db, u.username, u.role, "tai_xe_bat_dau_chuyen", f"trip:{tr.id}",
            after={"lenh": d.id, "km_dau": km_dau})
    return tr


def them_khoan(db: Session, u: User, d: DispatchOrder, kind: str, so_tien: float, lit: float = 0,
               so_hoa_don: str = "", tra_bang: str = "tai_xe_tien_mat", co_anh: bool = False) -> TripCost:
    t = _cho_ghi(phieu_cua_lenh(db, d))
    if kind not in KHOAN_TAI_XE:
        raise LoiGhiChuyen(f"Tài xế ghi được: {', '.join(COST_KINDS[k] for k in KHOAN_TAI_XE)}")
    if not so_tien or so_tien <= 0:
        raise LoiGhiChuyen("Số tiền phải lớn hơn 0")
    if kind == "dau" and not (lit and lit > 0):
        raise LoiGhiChuyen("Đổ dầu phải ghi số lít – không có lít thì không tính được tiêu hao")
    if tra_bang not in TRA_BANG:
        raise LoiGhiChuyen(f"Trả bằng chỉ nhận: {', '.join(TRA_BANG.values())}")
    nguong = R.get_param(db, "xe_chung_tu_bat_buoc_tu")
    if so_tien >= (nguong or 0) and not co_anh and not (so_hoa_don or "").strip():
        raise LoiGhiChuyen(f"Khoản từ {nguong:,.0f} đ phải chụp hoá đơn hoặc ghi số hoá đơn (chặn cứng B6)")
    from app.api.v1.fleet import _mac_dinh_ben_chiu
    bc = _mac_dinh_ben_chiu(db, kind)
    c = TripCost(trip_id=t.id, kind=kind, amount=so_tien, lit=lit if kind == "dau" else 0,
                 ben_chiu=bc if bc in BEN_CHIU else "vietourist_tam_ung", tra_bang=tra_bang,
                 chung_tu=(so_hoa_don or "").strip()[:200], nguon=NGUON, created_by=u.username)
    db.add(c); db.flush()
    R.audit(db, u.username, u.role, "tai_xe_ghi_khoan", f"trip:{t.id}",
            after={"kind": kind, "so_tien": so_tien, "lit": lit, "co_anh": co_anh})
    return c


def xoa_khoan(db: Session, u: User, d: DispatchOrder, cid: int) -> None:
    t = _cho_ghi(phieu_cua_lenh(db, d))
    c = db.get(TripCost, cid)
    if c is None or c.trip_id != t.id or c.nguon != NGUON:
        raise LoiGhiChuyen("Không có dòng này trong phiếu của anh")
    db.delete(c)
    R.audit(db, u.username, u.role, "tai_xe_xoa_khoan", f"trip:{t.id}", after={"cost": cid})


def ket_thuc(db: Session, u: User, d: DispatchOrder, km_cuoi: int | None) -> Trip:
    t = _cho_ghi(phieu_cua_lenh(db, d))
    if km_cuoi is None or km_cuoi <= 0:
        raise LoiGhiChuyen("Ghi số km trên đồng hồ lúc về bến")
    if t.km_dau is not None and km_cuoi < t.km_dau:
        raise LoiGhiChuyen(f"Km lúc về ({km_cuoi:,}) nhỏ hơn km lúc đi ({t.km_dau:,}) – đọc lại đồng hồ")
    t.km_cuoi = km_cuoi
    t.status = "cho_xac_nhan"
    t.note = (t.note + f" · tài xế gửi {datetime.now():%d/%m %H:%M}")[:300]
    from app.services import fleet as FL
    kt = FL.kiem_chuyen(db, t)
    t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    R.audit(db, u.username, u.role, "tai_xe_gui_chuyen", f"trip:{t.id}", after={"km_cuoi": km_cuoi})
    return t


def ra(db: Session, d: DispatchOrder) -> dict:
    """Phiếu chuyến của lệnh, như tài xế được thấy: KHÔNG có doanh thu, không có giá thuê nội bộ."""
    t = phieu_cua_lenh(db, d)
    v = db.get(Vehicle, d.vehicle_id)
    if t is None:
        return {"lenh_id": d.id, "xe": v.plate if v else "", "chuyen": None, "chi_phi": [],
                "co_the_bat_dau": d.nhan_luc is not None and d.status != "huy",
                "khoan": {k: COST_KINDS[k] for k in KHOAN_TAI_XE}, "tra_bang": TRA_BANG}
    from app.models.attachments import Attachment
    anh = {}
    for a in db.execute(select(Attachment).where(Attachment.doi_tuong == "chuyen_xe",
                                                 Attachment.doi_tuong_id == str(t.id),
                                                 Attachment.thu_hoi.is_(False))).scalars():
        anh.setdefault(a.mo_ta or "", []).append(a.id)
    cps = db.execute(select(TripCost).where(TripCost.trip_id == t.id).order_by(TripCost.id)).scalars().all()
    return {"lenh_id": d.id, "xe": v.plate if v else "",
            "chuyen": {"id": t.id, "km_dau": t.km_dau, "km_cuoi": t.km_cuoi,
                       "km_chay": (t.km_cuoi - t.km_dau) if (t.km_dau is not None and t.km_cuoi is not None) else None,
                       "trang_thai": t.status, "da_gui": t.status != "nhap",
                       "anh_dong_ho": len(anh.get("dong_ho_dau", [])) + len(anh.get("dong_ho_cuoi", []))},
            "chi_phi": [{"id": c.id, "kind": c.kind, "ten": COST_KINDS.get(c.kind, c.kind), "so_tien": c.amount,
                         "lit": c.lit, "so_hoa_don": c.chung_tu, "tra_bang": TRA_BANG.get(c.tra_bang or "", ""),
                         "co_anh": bool(anh.get(f"khoan:{c.id}")), "cua_toi": c.nguon == NGUON}
                        for c in cps],
            "tong_tien": sum((c.amount or 0) for c in cps), "tong_lit": sum((c.lit or 0) for c in cps),
            "so_anh": sum(len(x) for x in anh.values()),
            "co_the_bat_dau": False, "khoan": {k: COST_KINDS[k] for k in KHOAN_TAI_XE}, "tra_bang": TRA_BANG}
