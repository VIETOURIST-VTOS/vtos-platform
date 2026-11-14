# -*- coding: utf-8 -*-
"""R5-30 · ĐỘI XE TỰ NHẬN HỢP ĐỒNG THUÊ XE (Chủ tịch 14/11/2026: chọn phương án B; «CT duyệt, TGĐ thấy»).

Hợp đồng thuê xe riêng đã có từ 07/10/2026: một CHUYẾN RÚT GỌN loại `thue_xe` (một hợp đồng = một «khách»,
giá trọn hợp đồng ở `price_per_pax`). Trước vòng này chỉ Điều hành tạo được, và lệnh phải đi qua đề nghị xe
của Điều hành — nên khách thuê xe đội xe tự nhận vẫn phải nhờ Điều hành hai lần.

Nay Giám đốc đội xe (đúng người được lập lệnh — `fleet.chan_neu_khong_phai`):
  · tạo hợp đồng thuê xe NGAY TRÊN BÀN ĐỘI XE — chỉ loại `thue_xe`, không tạo được tour;
  · trình thẳng Chủ tịch duyệt (bỏ bước Trưởng phòng Điều hành) — `rules.approver_role` trả `chutich`
    cho hợp đồng của đội xe; TGĐ xem được, không duyệt;
  · duyệt xong bấm «Lập lệnh»: máy tạo MỘT đề nghị xe thay Điều hành (đúng số xe hợp đồng xin) rồi mở
    màn lập lệnh — nên mọi luật của lệnh (ngày trong hợp đồng, số lệnh ≤ số xe, chỉ GĐ lập) giữ nguyên.

Hợp đồng «của đội xe» = `tour_type == "thue_xe"` và người điều hành (`operator_id`) mang vai Giám đốc đội xe.
Số xe cần nằm ở `seats_open` (chuyến thuê xe không mở bán chỗ cho khách — `cong_khach.KHONG_BAN`); số khách
ở `vehicle_type` («29 khách»).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.services import rules as R

LOAI = "thue_xe"
VAI_DOI_XE = "gd_doi_xe"
TRANG_THAI = {"nhap": "Nháp", "cho_duyet": "Chờ Chủ tịch duyệt", "da_duyet": "Đã duyệt",
              "dang_chay": "Đang chạy", "ket_thuc": "Kết thúc", "khoa": "Đã khoá", "huy": "Đã huỷ"}


class LoiHopDong(ValueError):
    pass


def la_cua_doi_xe(t: Tour) -> bool:
    op = getattr(t, "operator", None)
    return t.tour_type == LOAI and op is not None and op.role == VAI_DOI_XE


def _chan(db: Session, u: User) -> None:
    from app.services import fleet as FL
    if u.role != VAI_DOI_XE:
        raise PermissionError("Chỉ Giám đốc đội xe tạo và trình hợp đồng thuê xe của đội xe.")
    FL.chan_neu_khong_phai(db, u, "tạo hợp đồng thuê xe của đội xe")


def tao(db: Session, u: User, *, ma: str, khach: str, lo_trinh: str, ngay_di: date, ngay_ve: date,
        so_xe: int, so_khach: int, gia: float, chi_phi: float, diem_dung: str) -> Tour:
    _chan(db, u)
    ma = (ma or "").strip().upper()
    if not ma or not (khach or "").strip():
        raise LoiHopDong("Phải ghi mã hợp đồng và khách thuê.")
    if db.execute(select(Tour).where(Tour.code == ma)).scalars().first():
        raise LoiHopDong(f"Mã {ma} đã có — chọn mã khác.")
    if ngay_ve < ngay_di:
        raise LoiHopDong("Ngày về trước ngày đi.")
    if so_xe <= 0 or so_khach <= 0:
        raise LoiHopDong("Số xe và số khách phải lớn hơn 0 — bộ gợi ý xe lọc theo số ghế.")
    if gia <= 0:
        raise LoiHopDong("Phải ghi giá trọn hợp đồng.")
    if chi_phi <= 0:
        raise LoiHopDong("Phải ghi chi phí dự kiến — không có giá vốn thì không tính được biên.")
    ten = khach.strip() + (f" · {lo_trinh.strip()}" if (lo_trinh or "").strip() else "")
    t = Tour(code=ma, name=ten[:200], tour_type=LOAI, start_date=ngay_di, end_date=ngay_ve, operator_id=u.id,
             price_per_pax=float(gia), fixed_cost=float(chi_phi), var_cost_per_pax=0, planned_pax=1,
             seats_open=int(so_xe), rest_stops=(diem_dung or "").strip(), status="nhap")
    t.planned_pax = 1                     # một hợp đồng = một «khách» (07/10/2026)
    db.add(t); db.flush()
    t.justification = ""
    _ghi_so_khach(t, so_khach)
    R.audit(db, u.username, u.role, "tao_hop_dong_thue_xe", f"tour:{t.code}",
            after={"khach": khach, "tu": str(ngay_di), "den": str(ngay_ve), "so_xe": so_xe, "gia": gia, "chi_phi": chi_phi})
    return t


def _ghi_so_khach(t: Tour, so_khach: int) -> None:
    """Số khách của hợp đồng — đầu vào của bộ gợi ý xe (lọc theo số ghế). Ghi vào ô «loại xe» của chuyến
    (`vehicle_type`, dạng «29 khách»): chuyến thuê xe không bán theo đầu người nên `planned_pax` phải giữ 1."""
    t.vehicle_type = f"{int(so_khach)} khách"


def so_khach(t: Tour) -> int:
    try:
        return int(str(getattr(t, "vehicle_type", "") or "").split()[0])
    except (ValueError, IndexError):
        return 0


def trinh(db: Session, u: User, t: Tour, giai_trinh: str = "") -> str:
    _chan(db, u)
    if not la_cua_doi_xe(t):
        raise LoiHopDong("Đây không phải hợp đồng thuê xe của đội xe.")
    if t.status != "nhap":
        raise LoiHopDong(f"Hợp đồng đang ở «{TRANG_THAI.get(t.status, t.status)}» — chỉ trình được bản nháp.")
    if not (t.rest_stops or "").strip():
        raise LoiHopDong("Phải ghi điểm dừng nghỉ (ĐH Điều 11).")
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
    if not c["complete"]:
        raise LoiHopDong("Chưa đủ giá và chi phí để tính biên.")
    if not c["pass_gate"]:
        if len((giai_trinh or "").strip()) < 30:
            raise LoiHopDong(f"Biên {c['margin'] * 100:.1f}% dưới ngưỡng {c['threshold'] * 100:.0f}% — phải giải trình "
                             "(tối thiểu 30 ký tự) để Chủ tịch xem khi duyệt.")
        t.justification = giai_trinh.strip()
    t.below_margin = not c["pass_gate"]
    t.status = "cho_duyet"                # bỏ bước Trưởng phòng Điều hành — Chủ tịch duyệt thẳng
    R.audit(db, u.username, u.role, "trinh_hop_dong_thue_xe", f"tour:{t.code}",
            after={"bien": c["margin"], "duoi_bien": t.below_margin})
    return "Đã trình Chủ tịch duyệt hợp đồng."


def danh_sach(db: Session) -> list[dict]:
    ds = [t for t in db.execute(select(Tour).where(Tour.tour_type == LOAI).order_by(Tour.start_date.desc())).scalars()
          if la_cua_doi_xe(t)]
    from app.models.de_nghi_xe import DeNghiXe
    ra = []
    for t in ds[:300]:
        c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
        dn = db.execute(select(DeNghiXe).where(DeNghiXe.tour_id == t.id)).scalars().first()
        ra.append({"id": t.id, "ma": t.code, "khach": t.name, "ngay_di": t.start_date, "ngay_ve": t.end_date,
                   "so_xe": t.seats_open or 1, "so_khach": so_khach(t), "gia": t.price_per_pax, "chi_phi": t.fixed_cost,
                   "bien": c["margin"] if c["complete"] else None, "duoi_bien": bool(t.below_margin),
                   "giai_trinh": t.justification, "diem_dung": t.rest_stops,
                   "trang_thai": t.status, "trang_thai_ten": TRANG_THAI.get(t.status, t.status),
                   "duyet_boi": t.approved_by, "de_nghi_id": dn.id if dn else None})
    return ra


def de_nghi_de_lap_lenh(db: Session, u: User, t: Tour) -> int:
    """Bấm «Lập lệnh»: có sẵn đề nghị của hợp đồng này thì dùng lại; chưa có thì tạo MỘT đề nghị thay Điều hành,
    đúng số xe hợp đồng xin. Trả mã đề nghị để màn lập lệnh điền sẵn."""
    from app.models.de_nghi_xe import DeNghiXe
    from app.services import de_nghi_xe as DN
    _chan(db, u)
    if not la_cua_doi_xe(t):
        raise LoiHopDong("Đây không phải hợp đồng thuê xe của đội xe.")
    cu = db.execute(select(DeNghiXe).where(DeNghiXe.tour_id == t.id)).scalars().first()
    if cu is not None:
        return cu.id
    d = DN.de_nghi(db, u, t.id, so_khach(t) or 1, 0, max(1, t.seats_open or 1),
                   "Hợp đồng thuê xe đội xe tự nhận (R5-30)", t.start_date, t.end_date)
    return d.id
