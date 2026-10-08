"""Nghiệp vụ hồ sơ nhân sự – hợp đồng – chấm công – người phụ thuộc (phân hệ Nhân sự kiểu MISA AMIS).

Ba việc HCNS làm hằng tháng mà VTOS chưa có, nay làm được ngay trên hệ thống:
  1. Hồ sơ & hợp đồng: hợp đồng nào sắp hết hạn, ai chưa có hợp đồng hiệu lực, ai thiếu hồ sơ định danh.
  2. Đơn từ & phép năm: nhân viên gửi đơn, quản lý duyệt; phép năm trừ tự động, không cho vượt quỹ phép.
  3. Bảng chấm công tháng: sinh từ đơn đã duyệt, HCNS chỉnh tay phần còn lại.

Câu thứ 3 trước ngày 08/10/2026 viết thêm bốn chữ "ra số công để tính lương", và đó là nói SAI: bảng
lương đọc `inputs["cong_thuc_te"]` do HCNS gõ tay, không đọc `attendance_days`. Hai nguồn, một nguồn
trả tiền. Xem `lech_cong()` ở cuối tệp – nó không nối hai nguồn lại (việc ấy là quyết định của người),
nó làm cho chỗ lệch đếm được.

Phép năm theo Bộ luật Lao động 2019 (Điều 113, 114): 12 ngày/năm với điều kiện làm việc bình thường,
cứ đủ 5 năm làm việc cho một người sử dụng lao động thì cộng thêm 1 ngày; năm đầu chưa đủ 12 tháng thì
tính theo tỷ lệ số tháng làm việc. Số ngày gốc lấy theo hợp đồng (annual_leave_days) nếu có ghi khác 12.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User
from app.models.hr import Employee, DEPARTMENTS
from app.models.hrm import (EmployeeProfile, LaborContract, Dependent, LeaveRequest, AttendanceDay,
                            CONTRACT_KINDS, CONTRACT_STATUS, LEAVE_KINDS, LEAVE_STATUS, ATT_KINDS)
from app.services import rules as R

# Giảm trừ gia cảnh – để ở tham số để Kế toán chỉnh khi Nhà nước thay đổi mức, không chôn cứng trong mã.
PIT_SELF_KEY, PIT_DEP_KEY = "giam_tru_ban_than", "giam_tru_nguoi_phu_thuoc"
PIT_SELF_DEFAULT, PIT_DEP_DEFAULT = 15_500_000.0, 6_200_000.0   # NQ 110/2025/UBTVQH15, từ kỳ tính thuế 2026


def _param(db: Session, key: str, default: float, on: date | None = None) -> float:
    try:
        return R.get_param(db, key, on=on)
    except KeyError:
        return default


def _cuoi_ky(period: str) -> date:
    """Ngày đầu tháng sau — mốc đọc tham số của một kỳ."""
    y, m = int(period[:4]), int(period[5:7])
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def _period_of(d: date) -> str:
    return f"{d:%Y-%m}"


def month_days(period: str) -> list[date]:
    y, m = int(period[:4]), int(period[5:7])
    first = date(y, m, 1)
    last = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


# ---------- Hợp đồng lao động ----------

def active_contract(db: Session, employee_id: int, on: date | None = None) -> LaborContract | None:
    """Hợp đồng đang hiệu lực tại một ngày (bản ký gần nhất còn hiệu lực)."""
    on = on or date.today()
    rows = db.execute(select(LaborContract).where(LaborContract.employee_id == employee_id,
                                                  LaborContract.status == "hieu_luc",
                                                  LaborContract.effective_from <= on)
                      .order_by(LaborContract.effective_from.desc(), LaborContract.id.desc())).scalars().all()
    for c in rows:
        if c.effective_to is None or c.effective_to >= on:
            return c
    return None


def contract_alerts(db: Session, within_days: int = 45, on: date | None = None) -> dict:
    """Cảnh báo hợp đồng: sắp hết hạn trong N ngày, đã hết hạn mà chưa ký lại, nhân sự chưa có hợp đồng."""
    on = on or date.today()
    limit = on + timedelta(days=within_days)
    emps = {e.id: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    expiring, expired, missing = [], [], []
    for eid, e in emps.items():
        c = active_contract(db, eid, on)
        if c is None:
            last = db.execute(select(LaborContract).where(LaborContract.employee_id == eid)
                              .order_by(LaborContract.effective_from.desc(), LaborContract.id.desc())).scalars().first()
            item = {"employee_id": eid, "code": e.code, "full_name": e.full_name, "department": e.department,
                    "contract_code": last.code if last else "", "effective_to": last.effective_to if last else None}
            (expired if last else missing).append(item)
            continue
        if c.effective_to and c.effective_to <= limit:
            expiring.append({"employee_id": eid, "code": e.code, "full_name": e.full_name, "department": e.department,
                             "contract_code": c.code, "kind": c.kind, "kind_name": CONTRACT_KINDS.get(c.kind, {}).get("ten", c.kind),
                             "effective_to": c.effective_to, "days_left": (c.effective_to - on).days})
    expiring.sort(key=lambda x: x["days_left"])
    return {"on": on, "within_days": within_days, "expiring": expiring, "expired": expired, "no_contract": missing,
            "counts": {"expiring": len(expiring), "expired": len(expired), "no_contract": len(missing)}}


def close_expired_contracts(db: Session, on: date | None = None) -> int:
    """Chuyển hợp đồng quá hạn sang trạng thái 'het_han' (chạy hằng ngày hoặc khi mở màn hình hợp đồng)."""
    on = on or date.today()
    n = 0
    for c in db.execute(select(LaborContract).where(LaborContract.status == "hieu_luc",
                                                    LaborContract.effective_to.isnot(None),
                                                    LaborContract.effective_to < on)).scalars():
        c.status, n = "het_han", n + 1
    if n:
        db.commit()
    return n


# ---------- Phép năm ----------

def annual_leave_entitlement(db: Session, e: Employee, year: int) -> float:
    """Quỹ phép năm: số ngày gốc theo hợp đồng (mặc định 12) + thâm niên mỗi đủ 5 năm 1 ngày;
    năm vào làm tính theo tỷ lệ số tháng còn lại của năm đó."""
    c = active_contract(db, e.id, date(year, 12, 31)) or active_contract(db, e.id, date(year, 1, 1))
    base = float(c.annual_leave_days) if c and c.annual_leave_days else 12.0
    start = e.start_date or (c.effective_from if c else None)
    if not start:
        return base
    seniority = max((date(year, 12, 31) - start).days // 365, 0)
    base += seniority // 5
    if start.year == year:                                   # năm đầu: theo tỷ lệ tháng làm việc
        months = 12 - start.month + 1
        return round(base * months / 12, 1)
    if start.year > year:
        return 0.0
    return base


def leave_used(db: Session, employee_id: int, year: int) -> float:
    """Số ngày phép năm đã dùng (đơn đã duyệt) trong năm."""
    got = db.execute(select(func.coalesce(func.sum(LeaveRequest.days), 0.0))
                     .where(LeaveRequest.employee_id == employee_id, LeaveRequest.kind == "phep_nam",
                            LeaveRequest.status == "duyet",
                            LeaveRequest.date_from >= date(year, 1, 1),
                            LeaveRequest.date_from <= date(year, 12, 31))).scalar() or 0.0
    return round(float(got), 1)


def leave_balance(db: Session, e: Employee, year: int) -> dict:
    ent = annual_leave_entitlement(db, e, year)
    used = leave_used(db, e.id, year)
    pending = db.execute(select(func.coalesce(func.sum(LeaveRequest.days), 0.0))
                         .where(LeaveRequest.employee_id == e.id, LeaveRequest.kind == "phep_nam",
                                LeaveRequest.status == "cho_duyet",
                                LeaveRequest.date_from >= date(year, 1, 1),
                                LeaveRequest.date_from <= date(year, 12, 31))).scalar() or 0.0
    return {"employee_id": e.id, "code": e.code, "full_name": e.full_name, "year": year,
            "entitlement": ent, "used": used, "pending": round(float(pending), 1), "remaining": round(ent - used, 1)}


# ---------- Đơn từ ----------
#
# AI KÝ ĐƠN CỦA AI — Chủ tịch quyết 30/9/2026, nhóm việc con người.
#
#     "Liên quan đến con người như nghỉ phép, ốm đau, vắng việc sẽ do Huấn duyệt, TGĐ và CT thấy."
#
# Trước bản này `decide_leave` không hỏi người ký là ai của người làm đơn: BẢY vai trong danh sách
# chữ ký cửa API đều ký được đơn của BẤT KỲ ai trong công ty. Một Trưởng phòng Kinh doanh ký được
# đơn nghỉ của một tài xế — không phải vì ai quyết thế, mà vì chưa ai hỏi câu ấy. Đơn vẫn chạy
# đúng suốt thời gian qua chỉ vì trên thực tế HCNS là người bấm.
#
# `TUYEN_KY_DON` là nơi câu hỏi ấy được trả lời, mỗi dòng một phòng, và CHỈ ghi những phòng đã có
# người quyết. Phòng chưa quyết thì giữ nguyên danh sách hôm nay (`KY_MAC_DINH`) — bản này sửa
# đúng chỗ Chủ tịch đã nói, không nhân tiện đặt luật cho chín phòng còn lại. Chỗ chưa quyết phải
# ĐẾM ĐƯỢC chứ không chìm đi, nên có `phong_chua_chot_nguoi_ky()` và một phép thử gọi nó.
#
# MỘT NGƯỜI KÝ, KHÔNG CÓ NGƯỜI KÝ THAY. Đội xe đúng một vai `gd_doi_xe`, như Chủ tịch nói. Hệ quả
# phải nói thẳng: Huấn nghỉ thì đơn của đội xe đứng lại. Mở người ký thay là nới quyền ký cho một
# vai khác — việc ấy cần người quyết, không phải việc phần mềm tự thêm cho tiện.
TUYEN_KY_DON = {
    # Chủ tịch quyết 30/9/2026 — một chữ ký của Giám đốc điều hành đội xe. TGĐ và Chủ tịch THẤY
    # (họ nằm trong HR_READ nên đọc được mọi đơn) nhưng KHÔNG ký ở đây.
    "doi_xe": ("gd_doi_xe",),
    # Hệ quả trực tiếp của lần tách vai 05/10/2026, đã ghi trong chính lý do tách (models/core.py):
    # "đơn của tài xế đi về Giám đốc đội xe, đơn của hướng dẫn viên đi về Trưởng phòng Hướng dẫn".
    "huong_dan": ("tp_hd",),

    # ---- Chủ tịch chốt 08/10/2026: CHÍN PHÒNG CÒN LẠI, mỗi phòng MỘT chữ ký ----
    #
    # Luật Chủ tịch: "các trưởng phòng ký, và báo dữ liệu về cho HCNS, TGĐ / Chủ tịch". Hai vế, và
    # vế sau KHÔNG phải một chữ ký nữa: HCNS, TGĐ, Chủ tịch nằm trong `HR_READ` nên đã đọc được mọi
    # đơn của mọi phòng từ trước — họ THẤY, không ký.
    #
    # BỐN PHÒNG KHÔNG CÓ VAI TRƯỞNG PHÒNG RIÊNG trong hệ thống (Visa, CNTT, Kế toán, HCNS chỉ có đúng
    # một vai cho cả phòng), nên "trưởng phòng ký" không chỉ ra được ai. Chủ tịch chỉ đích danh người
    # phụ trách thực tế và bản này ghi theo VAI của họ, không ghi tên người: một bảng luật ghi tên thì
    # ngày người ấy đổi việc, luật đi theo người thay vì theo chức.
    "kd_le": ("tp_kd",),
    "kd_doan": ("ptgd_doan",),         # phòng Đoàn do Phó TGĐ tour đoàn phụ trách
    "dieu_hanh": ("tp_dh",),
    "visa": ("tp_dh",),                # Ban Visa do Trưởng phòng Điều hành phụ trách (Chủ tịch 08/10)
    "marketing": ("ptgd_mkt",),
    "cntt": ("ptgd_mkt",),             # CNTT do Phó TGĐ Marketing phụ trách (Chủ tịch 08/10)
    "ketoan": ("tgd",),
    "hcns": ("tgd",),                  # không để HCNS tự ký đơn của phòng mình
    "ban_tgd": ("chutich",),
}

# Danh sách dự phòng cho một phòng CHƯA ai quyết người ký. Từ 08/10/2026 mọi phòng đang có đều đã
# được chỉ định, nên danh sách này không còn phòng nào dùng tới — GIỮ LẠI có chủ ý: ngày thêm phòng
# thứ mười hai, đơn của họ vẫn ký được bằng danh sách cũ thay vì rơi vào khoảng trống, và
# `phong_chua_chot_nguoi_ky()` đếm ra ngay để có người quyết.
#
# PHẢI NÓI RA MỘT HỆ QUẢ: bản này SIẾT, không nới. Trước 08/10 chín phòng chạy bằng danh sách dưới,
# nên HCNS, Giám đốc Kinh doanh và CNTT ký được đơn của gần như mọi phòng — và trên thực tế HCNS là
# người bấm. Từ bản này mỗi phòng chỉ một vai ký được, HCNS KHÔNG còn ký (họ đọc được tất cả qua
# `HR_READ`). Đó là đúng điều Chủ tịch quyết, nhưng người đang bấm hằng ngày sẽ thấy nút biến mất.
KY_MAC_DINH = ("hcns", "tgd", "chutich", "gd_kd", "ptgd_doan", "tp_kd", "cntt")


def nguoi_ky_don(phong: str) -> tuple[str, ...]:
    """Những vai trò ký được đơn của một người thuộc phòng này."""
    return TUYEN_KY_DON.get(phong) or KY_MAC_DINH


def phong_minh_ky(vai_tro: str) -> tuple[str, ...]:
    """Những phòng mà vai trò này là người ký — dùng để lọc hàng đợi duyệt."""
    return tuple(sorted(p for p, vais in TUYEN_KY_DON.items() if vai_tro in vais))


def phong_khong_ai_giu_vai_ky(db: Session) -> list[dict]:
    """Phòng ĐÃ chỉ định người ký mà KHÔNG tài khoản nào đang giữ vai ấy — đơn của họ không ai ký được.

    Sinh ra cùng bản 08/10/2026, và nó là mặt sau của chính bản ấy. Trước 08/10 chín phòng dùng danh
    sách `KY_MAC_DINH` bảy vai, nên gần như luôn có ai đó ký được — rộng thì sai người, nhưng không
    bao giờ kẹt. Nay mỗi phòng đúng MỘT vai, và một vai không ai giữ thì đơn của cả phòng ấy nằm im
    trong hàng đợi mà không một dòng nào báo. Đo trên bản demo lúc viết: `tp_kd` không tài khoản nào
    giữ, tức đơn của Kinh doanh Lẻ sẽ kẹt.

    KHÔNG tự chữa bằng cách thêm vai dự phòng: nới lại danh sách là xoá đúng quyết định vừa ký. Việc
    của hàm này là làm chỗ kẹt ĐẾM ĐƯỢC, cùng khuôn với `phong_chua_chot_nguoi_ky()` ngay dưới —
    chỗ thiếu là của HCNS đi cấp tài khoản, không phải của phần mềm đi đoán.
    """
    from app.models.core import User
    dang_giu = {u.role for u in db.execute(select(User).where(User.active == True)).scalars()}
    ra = []
    for phong, vais in TUYEN_KY_DON.items():
        thieu = [v for v in vais if v not in dang_giu]
        if len(thieu) == len(vais):          # KHÔNG một vai nào của phòng này có người giữ
            ra.append({"phong": phong, "phong_ten": DEPARTMENTS.get(phong, phong), "vai_ky": list(vais)})
    return ra


def phong_chua_chot_nguoi_ky() -> tuple[str, ...]:
    """Phòng còn đang chạy bằng danh sách cũ, chưa ai quyết người ký.

    KHÔNG phải lỗi, và cố ý không tự điền: đặt người ký cho một phòng là việc có người quyết.
    Trả ra đây để câu hỏi ấy còn đếm được thay vì chìm đi.
    """
    return tuple(p for p in DEPARTMENTS if p not in TUYEN_KY_DON)


def create_leave(db: Session, u: User, e: Employee, data: dict) -> LeaveRequest:
    kind = data.get("kind") or "phep_nam"
    if kind not in LEAVE_KINDS:
        raise ValueError(f"Loại đơn {kind} không hợp lệ")
    d1, d2 = data["date_from"], data.get("date_to") or data["date_from"]
    if d2 < d1:
        raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
    days = float(data.get("days") or ((d2 - d1).days + 1))
    if kind != "tang_ca" and days <= 0:
        raise ValueError("Số ngày nghỉ phải lớn hơn 0")
    if kind == "phep_nam":
        bal = leave_balance(db, e, d1.year)
        if days > (bal["remaining"] or 0) - bal["pending"]:
            raise ValueError(f"Vượt quỹ phép năm {d1.year}: còn {bal['remaining']:.1f} ngày "
                             f"(đang chờ duyệt {bal['pending']:.1f}), xin {days:.1f} ngày")
    r = LeaveRequest(employee_id=e.id, kind=kind, date_from=d1, date_to=d2, days=days,
                     ot_hours=float(data.get("ot_hours") or 0), reason=(data.get("reason") or "")[:300],
                     created_by=u.username)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "gui_don_nhan_su", f"don:{r.id}",
            after={"nhan_vien": e.code, "loai": kind, "tu": str(d1), "den": str(d2), "so_ngay": days})
    db.commit()
    return r


def decide_leave(db: Session, u: User, r: LeaveRequest, approve: bool, note: str = "") -> LeaveRequest:
    """Duyệt / từ chối đơn. Đơn đã duyệt sẽ tự ghi vào bảng chấm công những ngày tương ứng."""
    if r.status != "cho_duyet":
        raise ValueError(f"Đơn đã ở trạng thái '{LEAVE_STATUS.get(r.status, r.status)}'")
    e = db.get(Employee, r.employee_id)
    # Chặn nằm Ở ĐÂY, trong hàm, không chỉ ở chữ ký cửa API. Chữ ký cửa nói AI được gõ vào cửa này;
    # chỉ chỗ này nói người ấy được ký ĐƠN CỦA AI — và chỉ chỗ này còn đúng khi mai kia có một cửa
    # khác (robot, màn hình khác) gọi vào cùng hàm.
    ky_duoc = nguoi_ky_don(e.department if e else "")
    if u.role not in ky_duoc:
        raise ValueError(
            f"Vai trò '{u.role}' không ký được đơn của phòng "
            f"{DEPARTMENTS.get(e.department if e else '', '—')}: người ký là {', '.join(ky_duoc)}")
    # Người làm đơn không tự ký đơn của mình, kể cả khi họ đúng là vai được ký cho phòng ấy.
    if e is not None and e.user_id == u.id:
        raise ValueError("Không tự duyệt đơn của chính mình – đơn này phải do cấp trên ký")
    if approve and r.kind == "phep_nam":
        bal = leave_balance(db, e, r.date_from.year)
        if r.days > (bal["remaining"] or 0):
            raise ValueError(f"Không đủ phép năm: còn {bal['remaining']:.1f} ngày, đơn xin {r.days:.1f} ngày")
    r.status = "duyet" if approve else "tu_choi"
    r.approved_by, r.approved_at, r.decision_note = u.username, datetime.now(), note[:300]
    if approve and r.kind != "tang_ca":
        _apply_leave_to_attendance(db, r)
    R.audit(db, u.username, u.role, "duyet_don_nhan_su" if approve else "tu_choi_don_nhan_su", f"don:{r.id}",
            after={"nhan_vien": e.code if e else "", "loai": r.kind, "so_ngay": r.days, "ghi_chu": note})
    db.commit()
    return r


def _apply_leave_to_attendance(db: Session, r: LeaveRequest) -> None:
    """Ghi các ngày nghỉ đã duyệt vào bảng chấm công (nửa ngày thì công = 0,5)."""
    total_days = (r.date_to - r.date_from).days + 1
    half = r.days < total_days                              # xin ít ngày hơn khoảng ngày → coi là nghỉ nửa ngày
    work = 0.5 if half and total_days == 1 else 0.0
    kind = r.kind if r.kind in ATT_KINDS else "lam_viec"
    if r.kind == "cong_tac":
        kind, work = "cong_tac", 1.0                        # đi công tác vẫn tính đủ công
    for i in range(total_days):
        day = r.date_from + timedelta(days=i)
        row = db.execute(select(AttendanceDay).where(AttendanceDay.employee_id == r.employee_id,
                                                     AttendanceDay.day == day)).scalar_one_or_none()
        if row is None:
            row = AttendanceDay(employee_id=r.employee_id, day=day)
            db.add(row)
        row.kind, row.work, row.leave_id = kind, work, r.id
        row.note = (LEAVE_KINDS.get(r.kind, {}).get("ten", r.kind))[:200]


# ---------- Bảng chấm công ----------

def attendance_sheet(db: Session, period: str, department: str = "") -> dict:
    """Bảng chấm công tháng: mỗi nhân viên một dòng, ngày nào có bản ghi thì lấy, còn lại mặc định đi làm
    (trừ thứ Bảy/Chủ nhật) – giống cách MISA hiển thị lưới chấm công để HCNS soát và sửa tay."""
    days = month_days(period)
    q = select(Employee).where(Employee.active == True)
    if department:
        q = q.where(Employee.department == department)
    emps = list(db.execute(q.order_by(Employee.code)).scalars())
    ids = [e.id for e in emps]
    recs: dict[tuple[int, date], AttendanceDay] = {}
    if ids:
        for a in db.execute(select(AttendanceDay).where(AttendanceDay.employee_id.in_(ids),
                                                        AttendanceDay.day >= days[0], AttendanceDay.day <= days[-1])).scalars():
            recs[(a.employee_id, a.day)] = a
    rows = []
    for e in emps:
        cells, work, leave, unpaid, ot = [], 0.0, 0.0, 0.0, 0.0
        for d in days:
            a = recs.get((e.id, d))
            if a:
                k, w, o = a.kind, a.work, a.ot_hours
            elif d.weekday() >= 5:
                k, w, o = "le", 0.0, 0.0                     # cuối tuần: không tính công, HCNS sửa nếu có trực
            else:
                k, w, o = "lam_viec", 1.0, 0.0
            cells.append({"day": d.day, "kind": k, "work": w, "ot_hours": o})
            work += w; ot += o
            if k == "phep_nam":
                leave += 1
            elif k in ("khong_luong", "vang"):
                unpaid += 1
        rows.append({"employee_id": e.id, "code": e.code, "full_name": e.full_name, "department": e.department,
                     "cells": cells, "work_days": round(work, 1), "leave_days": leave, "unpaid_days": unpaid,
                     "ot_hours": round(ot, 1)})
    standard = sum(1 for d in days if d.weekday() < 5)
    return {"period": period, "days": [{"day": d.day, "weekday": d.weekday(), "weekend": d.weekday() >= 5} for d in days],
            "standard_days": standard, "rows": rows, "kinds": ATT_KINDS}


def set_attendance(db: Session, u: User, employee_id: int, day: date, kind: str, work: float, ot_hours: float, note: str) -> AttendanceDay:
    if kind not in ATT_KINDS:
        raise ValueError(f"Loại chấm công {kind} không hợp lệ")
    row = db.execute(select(AttendanceDay).where(AttendanceDay.employee_id == employee_id,
                                                 AttendanceDay.day == day)).scalar_one_or_none()
    if row is None:
        row = AttendanceDay(employee_id=employee_id, day=day)
        db.add(row)
    row.kind, row.work, row.ot_hours, row.note, row.updated_by = kind, float(work), float(ot_hours), note[:200], u.username
    db.commit()
    return row


# ---------- Bảng chấm công và bảng lương: hai nguồn, một nguồn trả tiền ----------

# Ba loại lệch, và chúng là ba CÂU HỎI khác nhau chứ không phải ba mức của một câu. Ô đếm ở dưới dựng
# TỪ bảng này chứ không gõ lại danh sách – đúng bài học TX-7 ngày 07/10: một ngày nào đó có người thêm
# loại thứ tư mà quên thêm ô đếm thì số không cộng đủ, và chẳng ai thấy.
LOAI_LECH_CONG = {
    "lech": "Số công HCNS gõ tay KHÁC số bảng chấm công cộng ra",
    "chua_nhap": "Phòng chấm công theo ngày mà chưa ai nhập số công – bảng lương tạm trả đủ tháng",
    "khong_tru": "Có ngày nghỉ không lương / không phép ĐÃ DUYỆT mà bảng lương không trừ gì",
}


def lech_cong(db: Session, period: str, inputs: dict | None = None) -> dict:
    """Bảng chấm công và con số công đã nhập vào bảng lương là HAI nguồn – và chỉ MỘT nguồn trả tiền.

    Đường đi của một ngày nghỉ đã duyệt: `decide_leave` → `_apply_leave_to_attendance` → `attendance_days`.
    Đường đi của TIỀN: bảng lương đọc `inputs["cong_thuc_te"]`, một từ điển HCNS gõ tay ở màn hình Lương.
    Hai đường ấy không gặp nhau ở đâu cả – không một dòng nào trong `services/hr.py` đọc `AttendanceDay`.
    Hệ quả: duyệt một đơn nghỉ không lương rồi không làm gì nữa thì bảng lương vẫn trả đủ công, và trước
    bản này KHÔNG CÓ DÒNG NÀO BÁO. Chính docstring đầu tệp này khai ngược lại – "bảng chấm công… ra số
    công để tính lương" – một câu khai một đường nối chưa bao giờ tồn tại; câu ấy đã sửa cùng bản này.

    Hàm này KHÔNG đổi nguồn trả tiền. Bảng nào thắng – bảng chấm công hay số HCNS gõ – là quyết định của
    Chủ tịch / Kế toán trưởng: lấy bảng chấm công làm căn cứ trả lương là đổi LUẬT TRẢ LƯƠNG, không phải
    đổi một dòng mã, và một phần mềm tự chọn cho tiện ở chỗ ấy là phần mềm trả lương sai mà không ai ký.
    Việc của hàm này là làm cho chỗ lệch ĐẾM ĐƯỢC và NÓI RA, cùng khuôn với `thieu_trong_o_dem` (TX-7),
    `misa.thieu_tai_khoan()` và `phong_chua_chot_nguoi_ky()` ngay trong tệp này.

    Chỉ soi người HỢP ĐỒNG LAO ĐỘNG: cộng tác viên và hướng dẫn viên hưởng thù lao theo chuyến quyết toán,
    không có số công nào để lệch.
    """
    # Nhập trong thân hàm, không nhập ở đầu tệp: `luong.py` đọc `rules` và `hr`, nhập vòng tròn nếu đặt trên.
    from app.services import luong as L

    sheet = attendance_sheet(db, period)
    da_nhap = {str(k): v for k, v in ((inputs or {}).get("cong_thuc_te") or {}).items()}
    emps = {e.id: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    dong: list[dict] = []
    for r in sheet["rows"]:
        e = emps.get(r["employee_id"])
        if e is None or e.contract_type != "hdld":
            continue
        chung = {"employee_id": e.id, "ma": e.code, "ho_ten": e.full_name, "phong": e.department,
                 "che_do_cong": L.che_do_cong(e), "cong_theo_bang": r["work_days"],
                 "ngay_khong_luong": r["unpaid_days"], "ngay_phep": r["leave_days"]}
        if L.che_do_cong(e) == L.CHAM_CONG:
            go = da_nhap.get(e.code)
            if go in (None, ""):
                dong.append({**chung, "loai": "chua_nhap", "cong_da_nhap": None,
                             "viec": "HCNS nhập số công của người này trước khi trình ký"})
            elif abs(float(go) - r["work_days"]) > 0.01:
                dong.append({**chung, "loai": "lech", "cong_da_nhap": float(go),
                             "viec": (f"Số gõ tay {float(go):g} công, bảng chấm công cộng ra "
                                      f"{r['work_days']:g} công – soát lại một trong hai")})
        elif r["unpaid_days"] > 0:
            dong.append({**chung, "loai": "khong_tru", "cong_da_nhap": None,
                         "viec": (f"{r['unpaid_days']:g} ngày không lương đã duyệt; phòng này trả lương "
                                  f"cố định nên bảng lương không trừ gì – cách trừ do người quyết")})
    return {"period": period, "loai": LOAI_LECH_CONG,
            "dem": {k: sum(1 for d in dong if d["loai"] == k) for k in LOAI_LECH_CONG},
            "so_dong": len(dong), "dong": dong}

# ---------- Người phụ thuộc & giảm trừ gia cảnh ----------

def dependents_of(db: Session, employee_id: int, period: str | None = None) -> list[Dependent]:
    rows = db.execute(select(Dependent).where(Dependent.employee_id == employee_id, Dependent.active == True)
                      .order_by(Dependent.id)).scalars().all()
    if not period:
        return rows
    return [d for d in rows
            if (not d.from_period or d.from_period <= period) and (not d.to_period or d.to_period >= period)]


def pit_deduction(db: Session, employee_id: int, period: str) -> dict:
    """Giảm trừ gia cảnh của một người trong kỳ: bản thân + số người phụ thuộc đang hiệu lực."""
    # Đọc mức giảm trừ ÁP CHO KỲ ẤY, không phải mức của hôm nay: bảng tham số có hiệu lực theo ngày,
    # nên một kỳ cũ tính lại phải ra đúng số của kỳ cũ. Trước 08/10/2026 hàm này gọi không kèm ngày.
    _on = _cuoi_ky(period)
    self_amt = _param(db, PIT_SELF_KEY, PIT_SELF_DEFAULT, on=_on)
    dep_amt = _param(db, PIT_DEP_KEY, PIT_DEP_DEFAULT, on=_on)
    deps = dependents_of(db, employee_id, period)
    return {"period": period, "self": self_amt, "dependent_rate": dep_amt, "dependents": len(deps),
            "dependent_total": round(dep_amt * len(deps), 0), "total": round(self_amt + dep_amt * len(deps), 0),
            "names": [d.full_name for d in deps]}


# ---------- Hồ sơ ----------

def profile_of(db: Session, employee_id: int) -> EmployeeProfile | None:
    return db.execute(select(EmployeeProfile).where(EmployeeProfile.employee_id == employee_id)).scalar_one_or_none()


PROFILE_REQUIRED = ("id_number", "dob", "permanent_address", "phone", "tax_code", "bank_account")


def save_profile(db: Session, u: User, employee_id: int, data: dict) -> EmployeeProfile:
    p = profile_of(db, employee_id)
    if p is None:
        p = EmployeeProfile(employee_id=employee_id)
        db.add(p)
    for k, v in data.items():
        if v is None or not hasattr(p, k) or k in ("id", "employee_id"):
            continue
        setattr(p, k, v)
    p.updated_by = u.username
    R.audit(db, u.username, u.role, "cap_nhat_ho_so_nhan_su", f"nv:{employee_id}", after={"truong": sorted(data.keys())})
    db.commit()
    return p


def profile_completeness(db: Session, employee_id: int) -> dict:
    """Mức độ đầy đủ hồ sơ – MISA có thanh '% hoàn thiện hồ sơ', ở đây liệt kê thẳng trường còn thiếu."""
    p = profile_of(db, employee_id)
    missing = [f for f in PROFILE_REQUIRED if not getattr(p, f, None)] if p else list(PROFILE_REQUIRED)
    return {"employee_id": employee_id, "has_profile": p is not None, "missing": missing,
            "percent": round(100 * (len(PROFILE_REQUIRED) - len(missing)) / len(PROFILE_REQUIRED))}


# ---------- Cột TNCN của bảng lương: nói ra nó đang gồm những ai, và bỏ sót ai ----------

def tncn_chua_tinh(db: Session, period: str, rows: list[dict] | None) -> dict:
    """Cột TNCN của bảng lương nghĩa là gì trong kỳ này — và hàm phải ĐỔI LỜI khi công tắc đổi.

    Trước 08/10/2026 câu trả lời chỉ có một vế: VTOS cộng TNCN đúng một chỗ (10% thù lao cộng tác
    viên), người hợp đồng lao động đi qua `row(e)` với `tncn: 0.0`, nên ô "Khoản trừ … TNCN x đ"
    là con số của RIÊNG cộng tác viên và số 0 của hơn trăm người chìm vào tổng.

    Từ bản KY-1 phép tính lũy tiến đã có (`services/thue_tncn.py`), nhưng nó chỉ chạy khi tham số
    `tncn_luy_tien_tu_ky` được ký. Nên hàm này có HAI lời, và chọn lời theo công tắc chứ không theo
    trí nhớ của người viết:

      · CHƯA BẬT — y như trước: đếm người HĐLĐ không bị khấu trừ, kèm `thieu_mst` và `co_npt` để
        lúc quyết thì biết nền dữ liệu đang ở đâu.
      · ĐÃ BẬT  — "tncn = 0" KHÔNG còn là chỗ thiếu: người có thu nhập dưới mức giảm trừ thì thuế
        bằng 0 một cách đúng đắn. Chỗ thiếu lúc ấy là chỗ KHÁC: người chưa có hợp đồng hiệu lực
        (chưa biết khấu trừ theo cách nào), người chưa có mã số thuế (khấu trừ rồi mà không khai
        được), người chưa có mức đóng BHXH (chưa trừ bảo hiểm nên thuế tạm tính cao hơn số phải
        nộp). Đếm đúng ba chỗ ấy, đừng đếm lại chỗ đã lành.

    Một hàm chỉ biết nói một lời sẽ nói sai vào đúng ngày hệ thống đổi — và nói sai một cách tự tin,
    vì nó vẫn in ra số.
    """
    from app.services import thue_tncn as TNCN
    rows = rows or []
    da_bat = TNCN.da_bat(db, period)
    ma_hdld = {e.code: e for e in db.execute(
        select(Employee).where(Employee.active == True, Employee.contract_type == "hdld")).scalars()}
    ho_so = {p.employee_id: p for p in db.execute(select(EmployeeProfile)).scalars()}
    npt: dict[int, int] = {}
    for d in db.execute(select(Dependent).where(Dependent.active == True)).scalars():
        npt[d.employee_id] = npt.get(d.employee_id, 0) + 1

    dong, ctv, chua_hd, thieu_bhxh = [], 0, 0, 0
    for r in rows:
        e = ma_hdld.get(str(r.get("ma") or ""))
        if e is None:
            if float(r.get("tncn") or 0) > 0:
                ctv += 1
            continue
        p = ho_so.get(e.id)
        d = {"ma": e.code, "ho_ten": e.full_name, "phong": e.department,
             "co_mst": bool(getattr(p, "tax_code", "")),
             "so_nguoi_phu_thuoc": npt.get(e.id, 0),
             "thue": round(float((r.get("tncn_luy_tien") or {}).get("thue") or 0))}
        if da_bat:
            cach = (r.get("tncn_luy_tien") or {}).get("cach")
            if cach == TNCN.CHUA_CO_HOP_DONG:
                chua_hd += 1
            if r.get("thieu_muc_bhxh"):
                thieu_bhxh += 1
            if cach == TNCN.CHUA_CO_HOP_DONG or not d["co_mst"] or r.get("thieu_muc_bhxh"):
                d["cach"] = cach
                dong.append(d)
        elif float(r.get("tncn") or 0) <= 0:
            dong.append(d)

    if da_bat:
        ghi_chu = (f"VTOS đang tự khấu trừ thuế TNCN lũy tiến cho người HĐLĐ từ kỳ "
                   f"{TNCN.ky_bat_dau(db)}. Số dưới đây là các hồ sơ CÒN HỞ khiến số khấu trừ chưa "
                   "chắc đúng — không phải những người có thuế bằng 0, vì thu nhập dưới mức giảm "
                   "trừ thì thuế bằng 0 là đúng. Thuế quyết toán theo năm.")
    else:
        ghi_chu = ("Cột TNCN của bảng lương chỉ gồm 10% khấu trừ thù lao cộng tác viên. VTOS CHƯA tự "
                   "khấu trừ thuế lũy tiến cho người hợp đồng lao động: phép tính đã dựng xong "
                   "(services/thue_tncn.py) nhưng công tắc là tham số 'tncn_luy_tien_tu_ky' đang để "
                   "trống — mở bằng hai chữ ký ở màn hình Tham số, và chỉ mở sau khi MISA đã dừng "
                   "khấu trừ cùng kỳ.")
    return {"period": period, "da_bat": da_bat, "ky_bat_dau": TNCN.ky_bat_dau(db),
            "so_nguoi_hdld_khong_tncn": len(dong),
            "so_nguoi_ctv_co_tncn": ctv,
            "thieu_mst": sum(1 for d in dong if not d["co_mst"]),
            "co_npt": sum(1 for d in dong if d["so_nguoi_phu_thuoc"] > 0),
            "chua_co_hop_dong": chua_hd, "thieu_muc_bhxh": thieu_bhxh,
            "tham_so_lac_hau": TNCN.tham_so_lac_hau(db, period),
            "ghi_chu": ghi_chu, "dong": dong}
