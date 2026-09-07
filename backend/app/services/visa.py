"""Nghiệp vụ phân hệ Visa: quy trình, checklist, tài liệu, công việc, lịch hẹn, kết quả, bàn giao.

Nguyên tắc xuyên suốt (mục 5.2 của đặc tả): KHÔNG có hàm nào cho phép đặt thẳng `current_stage`. Mỗi bước đi
tiếp bằng một hành động nghiệp vụ, và hành động đó tự kiểm tra điều kiện nghiệp vụ trước khi cho qua. Giao diện
và AI đều gọi cùng các hàm này nên không ai vượt được quy trình bằng cách gửi trạng thái tùy ý.
"""
import hashlib
import re
import secrets
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.core import User, Booking, Tour, Company
from app.models.visa import (VisaMarket, VisaFamilyGroup, VisaCase, VisaFormVersion, VisaConfirmation,
                             VisaChecklistTemplate, VisaChecklistItem, VisaDocument, VisaDocumentReview,
                             VisaWaiver, VisaTask, VisaApplication, VisaAppointment, VisaResult,
                             VisaHandover, VisaAccessLink, VisaAiSuggestion,
                             STAGES, STAGE_ORDER, DOC_SATISFIED, DEFAULT_COMPANY)
from app.services import rules as R
from app.services import storage as ST

MAX_DOC_BYTES = 15 * 1024 * 1024
# Trường form mà thay đổi thì phải xin khách xác nhận lại (mục 6.1).
CRITICAL_FIELDS = ("ho_ten", "ngay_sinh", "so_ho_chieu", "ngay_het_han_ho_chieu", "quoc_tich",
                   "ngay_du_kien_nhap_canh", "muc_dich_chuyen_di")


class VisaError(ValueError):
    """Vi phạm điều kiện nghiệp vụ – API trả 422 kèm thông điệp tiếng Việt."""


# ---------- Tiện ích ----------
def _now() -> datetime:
    return datetime.now()


def get_case(db: Session, case_id: int) -> VisaCase:
    c = db.get(VisaCase, case_id)
    if not c:
        raise VisaError("Không có hồ sơ Visa này")
    return c


def resolve_company(db: Session, company_id: int | None = None, company_code: str = "") -> int | None:
    """Pháp nhân chủ quản của hồ sơ: theo id, hoặc theo mã, mặc định là công ty mẹ trong danh mục pháp nhân."""
    if company_id:
        c = db.get(Company, company_id)
        if not c or not c.active:
            raise VisaError("Không có pháp nhân này trong danh mục, hoặc pháp nhân đã ngừng hoạt động")
        return c.id
    code = (company_code or DEFAULT_COMPANY).upper()
    c = db.execute(select(Company).where(Company.code == code)).scalar_one_or_none()
    if not c:
        c = db.execute(select(Company).where(Company.kind == "me")).scalars().first()
    return c.id if c else None


def _market(db: Session, code: str) -> VisaMarket:
    m = db.execute(select(VisaMarket).where(VisaMarket.code == code.upper())).scalar_one_or_none()
    if not m:
        raise VisaError(f"Chưa cấu hình thị trường {code} – khai báo tại Biểu mẫu & Checklist")
    return m


def stages_for(m: VisaMarket) -> list[str]:
    """Danh sách bước áp dụng cho một thị trường. Không sao chép cứng quy trình UK cho mọi thị trường."""
    skip = set(m.skip_stages or [])
    if not m.requires_biometrics:
        skip.add("sinh_trac_hoc")
    if not m.requires_appointment:
        skip.add("lich_hen")
    return [s for s in STAGE_ORDER if s not in skip]


def _next_stage(db: Session, c: VisaCase, after: str) -> str:
    seq = stages_for(_market(db, c.market_code))
    i = seq.index(after) if after in seq else -1
    return seq[i + 1] if 0 <= i < len(seq) - 1 else after


def _new_code(db: Session, prefix: str, model, field) -> str:
    n = db.execute(select(func.count(model.id))).scalar() or 0
    for i in range(n + 1, n + 500):
        code = f"{prefix}{i:05d}"
        if not db.execute(select(model.id).where(field == code)).first():
            return code
    raise VisaError("Không sinh được mã mới")


def _audit(db: Session, u: User, action: str, case: VisaCase, before=None, after=None):
    R.audit(db, u.username, u.role, action, f"visa:{case.case_code}", before=before, after=after)


# ---------- Phân quyền theo phạm vi (mục 9) ----------
LEADERSHIP = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt")
VISA_ALL = LEADERSHIP + ("cntt", "bks", "tp_dh", "ketoan")     # xem toàn bộ trong phạm vi công ty
VISA_STAFF = ("nv_visa", "nv_dh", "tp_dh")                       # người trực tiếp xử lý hồ sơ
REVIEWER_ROLES = LEADERSHIP + ("tp_dh", "cntt")                 # duyệt tài liệu / ngoại lệ
WAIVER_DECIDER = LEADERSHIP + ("tp_dh",)                        # quyết định miễn nộp
ASSIGNER_ROLES = LEADERSHIP + ("tp_dh", "gd_kd")


def can_see(u: User, c: VisaCase) -> bool:
    """Nhân viên chỉ thấy hồ sơ thuộc phạm vi được giao – kiểm ở backend, áp cho cả API, tải tệp, xuất báo cáo."""
    if u.role in VISA_ALL:
        return True
    return u.id in (c.sales_user_id, c.visa_owner_user_id, c.supervisor_user_id)


def ensure_see(u: User, c: VisaCase) -> VisaCase:
    if not can_see(u, c):
        raise VisaError("Hồ sơ này không thuộc phạm vi được giao của bạn")
    return c


def scope(u: User, q):
    if u.role in VISA_ALL:
        return q
    return q.where(or_(VisaCase.sales_user_id == u.id, VisaCase.visa_owner_user_id == u.id,
                       VisaCase.supervisor_user_id == u.id))


def _require(u: User, roles: tuple, what: str):
    if u.role not in roles:
        raise VisaError(f"Vai trò của bạn không được {what}")


def _editable(c: VisaCase):
    if c.lifecycle_status in ("CANCELLED", "CLOSED"):
        raise VisaError(f"Hồ sơ đang ở trạng thái {c.lifecycle_status} – không thao tác nghiệp vụ được nữa")
    if c.lifecycle_status == "ON_HOLD":
        raise VisaError(f"Hồ sơ đang tạm dừng ({c.hold_reason or 'không ghi lý do'}) – bỏ tạm dừng trước")


# ---------- Hạn xử lý ----------
def due_for(db: Session, c: VisaCase, kind: str) -> datetime | None:
    """Hạn theo loại bước, lấy từ cấu hình thị trường; không áp một số giờ cố định cho mọi nghiệp vụ.

    Nếu ngày đi đã gần thì hạn bị kéo sớm lại – không để công việc đến hạn sau khi khách đã bay."""
    m = _market(db, c.market_code)
    hours = (m.sla_hours or {}).get(kind)
    if hours is None:
        return None
    due = _now() + timedelta(hours=float(hours))
    if c.departure_date:
        latest = datetime.combine(c.departure_date, datetime.min.time()) - timedelta(days=1)
        due = min(due, latest)
    return due


def open_task(db: Session, u: User, c: VisaCase, kind: str, title: str,
              assignee_user_id: int | None = None, priority: str = "thuong") -> VisaTask:
    """Mở công việc cho bước hiện tại. Mỗi bước chỉ có một công việc đang mở cùng loại."""
    old = db.execute(select(VisaTask).where(VisaTask.case_id == c.id, VisaTask.kind == kind,
                                            VisaTask.status.in_(("open", "doing", "waiting")))).scalars().first()
    if old:
        return old
    t = VisaTask(case_id=c.id, kind=kind, title=title, assignee_user_id=assignee_user_id,
                 due_at=due_for(db, c, kind), priority=priority, created_by=u.username)
    db.add(t)
    return t


def _close_tasks(db: Session, c: VisaCase, kind: str, by: str):
    for t in db.execute(select(VisaTask).where(VisaTask.case_id == c.id, VisaTask.kind == kind,
                                               VisaTask.status.in_(("open", "doing", "waiting")))).scalars():
        t.status, t.done_at = "done", _now()
        t.evidence = t.evidence or f"tự đóng khi {by}"


def _advance(db: Session, u: User, c: VisaCase, from_stage: str, action: str, detail: dict):
    """Chuyển bước: đóng công việc của bước cũ, mở công việc bước mới, ghi nhật ký."""
    before = {"stage": c.current_stage}
    _close_tasks(db, c, from_stage, action)
    c.current_stage = _next_stage(db, c, from_stage)
    c.row_version += 1
    if c.current_stage != "dong_ho_so":
        open_task(db, u, c, c.current_stage, f"{STAGES[c.current_stage]} – {c.applicant_name}",
                  c.visa_owner_user_id or c.sales_user_id)
    _audit(db, u, f"visa_{action}", c, before=before, after={"stage": c.current_stage, **detail})


# ---------- Tạo hồ sơ ----------
def find_possible_duplicates(db: Session, applicant_name: str, market_code: str, departure_date: date | None,
                             booking_id: int | None, company_id: int | None) -> list[VisaCase]:
    """Nghi trùng theo khách + thị trường + chuyến đi. KHÔNG dùng số điện thoại làm khóa duy nhất (mục 11.1)."""
    name = (applicant_name or "").strip().lower()
    q = select(VisaCase).where(VisaCase.company_id == company_id,
                               VisaCase.market_code == market_code.upper(),
                               VisaCase.lifecycle_status != "CANCELLED",
                               func.lower(VisaCase.applicant_name) == name)
    rows = list(db.execute(q).scalars())
    out = []
    for r in rows:
        same_trip = (booking_id and r.booking_id == booking_id) or (
            departure_date and r.departure_date and abs((r.departure_date - departure_date).days) <= 14)
        if same_trip:
            out.append(r)
    return out


def create_case(db: Session, u: User, data: dict, on_duplicate: str = "block") -> VisaCase:
    """Tạo hồ sơ. `on_duplicate`: block (mặc định) / open_existing / resubmit / independent.

    Hành vi chống trùng theo mục 11.1: không âm thầm tạo bản sao, cũng không âm thầm gộp – bắt người dùng chọn."""
    company = resolve_company(db, data.get("company_id"), data.get("company_code", ""))
    market = (data.get("market_code") or "").upper()
    _market(db, market)
    name = (data.get("applicant_name") or "").strip()
    if not name:
        raise VisaError("Thiếu tên đương đơn")
    dep = data.get("departure_date")
    booking_id = data.get("booking_id")
    if booking_id and not db.get(Booking, booking_id):
        raise VisaError("Không có booking này trong VTOS")
    if data.get("tour_id") and not db.get(Tour, data["tour_id"]):
        raise VisaError("Không có tour này trong VTOS")

    dups = find_possible_duplicates(db, name, market, dep, booking_id, company)
    if dups and on_duplicate == "block":
        raise VisaError("Có thể trùng hồ sơ đã tồn tại: " + ", ".join(d.case_code for d in dups) +
                        ". Chọn mở hồ sơ hiện có, tạo lần nộp mới có liên kết, hoặc tạo hồ sơ độc lập kèm lý do.")
    if dups and on_duplicate == "open_existing":
        return dups[0]
    if dups and on_duplicate == "independent" and not (data.get("cancellation_reason") or data.get("note")):
        raise VisaError("Tạo hồ sơ độc lập khi đang nghi trùng thì phải ghi lý do")

    c = VisaCase(
        case_code=_new_code(db, "HSV", VisaCase, VisaCase.case_code),
        company_id=company, applicant_name=name,
        applicant_dob=data.get("applicant_dob"), applicant_phone=data.get("applicant_phone", ""),
        applicant_email=data.get("applicant_email", ""),
        passport_last4=(data.get("passport_last4") or "")[-4:],
        passport_expiry=data.get("passport_expiry"),
        booking_id=booking_id, tour_id=data.get("tour_id"),
        family_group_id=data.get("family_group_id"), family_role=data.get("family_role", ""),
        market_code=market, visa_type=data.get("visa_type", ""),
        service_mode=data.get("service_mode") or ("TOUR_LINKED" if data.get("tour_id") else "STANDALONE"),
        departure_date=dep, return_date=data.get("return_date"),
        sales_user_id=data.get("sales_user_id") or (u.id if u.role.startswith("nv_kd") else None),
        source_system=data.get("source_system", ""), source_record_id=str(data.get("source_record_id") or ""),
        is_test=bool(data.get("is_test")), created_by=u.username)
    if dups and on_duplicate == "resubmit":
        c.previous_case_id, c.relationship_type = dups[0].id, "RESUBMIT"
    db.add(c)
    db.flush()
    build_checklist(db, c)
    open_task(db, u, c, "phan_cong", f"Phân công chuyên viên Visa – {c.applicant_name}")
    c.current_stage = "phan_cong"
    _audit(db, u, "visa_tao_ho_so", c, after={"thi_truong": market, "booking_id": booking_id,
                                              "nghi_trung": [d.case_code for d in dups]})
    return c


def assign(db: Session, u: User, c: VisaCase, visa_owner_user_id: int | None = None,
           supervisor_user_id: int | None = None, sales_user_id: int | None = None) -> VisaCase:
    _require(u, ASSIGNER_ROLES, "phân công hồ sơ Visa")
    _editable(c)
    before = {"visa_owner": c.visa_owner_user_id, "supervisor": c.supervisor_user_id, "sales": c.sales_user_id}
    for uid, field in ((visa_owner_user_id, "visa_owner_user_id"), (supervisor_user_id, "supervisor_user_id"),
                       (sales_user_id, "sales_user_id")):
        if uid is not None:
            if not db.get(User, uid):
                raise VisaError("Không có người dùng này")
            setattr(c, field, uid)
    if c.current_stage == "phan_cong" and c.visa_owner_user_id:
        _advance(db, u, c, "phan_cong", "phan_cong", {"visa_owner": c.visa_owner_user_id})
    else:
        c.row_version += 1
        _audit(db, u, "visa_chuyen_nguoi", c, before=before,
               after={"visa_owner": c.visa_owner_user_id, "supervisor": c.supervisor_user_id})
    return c


# ---------- Checklist ----------
def _applies(item: dict, c: VisaCase) -> bool:
    cond = item.get("dieu_kien") or {}
    if not cond:
        return True
    if "tuoi_duoi" in cond:
        if not c.applicant_dob:
            return True                       # chưa biết tuổi thì cứ đưa vào, người kiểm tra quyết định sau
        ref = c.departure_date or date.today()
        age = ref.year - c.applicant_dob.year - ((ref.month, ref.day) < (c.applicant_dob.month, c.applicant_dob.day))
        if age >= int(cond["tuoi_duoi"]):
            return False
    if "service_mode" in cond and c.service_mode != cond["service_mode"]:
        return False
    return True


def active_template(db: Session, market_code: str, visa_type: str = "") -> VisaChecklistTemplate | None:
    q = select(VisaChecklistTemplate).where(VisaChecklistTemplate.market_code == market_code.upper(),
                                            VisaChecklistTemplate.active == True)
    rows = sorted(db.execute(q).scalars(), key=lambda t: (t.visa_type == visa_type, t.version), reverse=True)
    return rows[0] if rows else None


def build_checklist(db: Session, c: VisaCase) -> list[VisaChecklistItem]:
    """Dựng checklist lần đầu cho hồ sơ theo mẫu đang hiệu lực."""
    tpl = active_template(db, c.market_code, c.visa_type)
    if not tpl:
        return []
    out = []
    for it in tpl.items or []:
        if not _applies(it, c):
            continue
        row = VisaChecklistItem(case_id=c.id, template_id=tpl.id, template_version=tpl.version,
                                key=it["key"], name=it.get("ten", it["key"]), description=it.get("mo_ta", ""),
                                required=bool(it.get("bat_buoc", True)))
        db.add(row)
        out.append(row)
    db.flush()
    return out


def resync_checklist(db: Session, u: User, c: VisaCase) -> dict:
    """Áp mẫu checklist phiên bản mới: GIỮ kết quả cũ cho mục không đổi, đánh dấu kiểm lại mục bị ảnh hưởng."""
    tpl = active_template(db, c.market_code, c.visa_type)
    if not tpl:
        raise VisaError("Chưa có mẫu checklist đang hiệu lực cho thị trường này")
    cur = {i.key: i for i in db.execute(select(VisaChecklistItem).where(VisaChecklistItem.case_id == c.id)).scalars()}
    added, recheck, na = [], [], []
    seen = set()
    for it in tpl.items or []:
        if not _applies(it, c):
            continue
        seen.add(it["key"])
        old = cur.get(it["key"])
        if not old:
            db.add(VisaChecklistItem(case_id=c.id, template_id=tpl.id, template_version=tpl.version,
                                     key=it["key"], name=it.get("ten", it["key"]),
                                     description=it.get("mo_ta", ""), required=bool(it.get("bat_buoc", True))))
            added.append(it["key"])
            continue
        changed = (old.name != it.get("ten", it["key"]) or old.description != it.get("mo_ta", "")
                   or old.required != bool(it.get("bat_buoc", True)))
        old.name, old.description = it.get("ten", it["key"]), it.get("mo_ta", "")
        old.required, old.template_version = bool(it.get("bat_buoc", True)), tpl.version
        if changed and old.status in ("ACCEPTED", "WAIVED"):
            old.needs_recheck = True          # nội dung yêu cầu đổi → kết quả cũ phải kiểm lại
            recheck.append(old.key)
    for key, old in cur.items():
        if key not in seen and old.status not in DOC_SATISFIED:
            old.status, old.required = "NOT_APPLICABLE", False
            na.append(key)
    _audit(db, u, "visa_dong_bo_checklist", c,
           after={"phien_ban": tpl.version, "them": added, "kiem_lai": recheck, "khong_ap_dung": na})
    return {"template_version": tpl.version, "them": added, "kiem_lai": recheck, "khong_ap_dung": na}


def checklist_summary(db: Session, case_id: int) -> dict:
    rows = list(db.execute(select(VisaChecklistItem).where(VisaChecklistItem.case_id == case_id)).scalars())
    req = [r for r in rows if r.required]
    ok = [r for r in req if r.status in DOC_SATISFIED and not r.needs_recheck]
    return {"bat_buoc": len(req), "da_chap_nhan": len(ok), "tong": len(rows),
            "con_thieu": [r.key for r in req if r not in ok]}


# ---------- Form khai ----------
def save_form(db: Session, u: User, c: VisaCase, data: dict) -> VisaFormVersion:
    """Lưu phiên bản form. Bản đã CONFIRMED không bị ghi đè – luôn sinh phiên bản mới và lưu khác biệt."""
    _editable(c)
    last = db.execute(select(VisaFormVersion).where(VisaFormVersion.case_id == c.id)
                      .order_by(VisaFormVersion.version.desc())).scalars().first()
    prev = last.data if last else {}
    changed = sorted({k for k in set(prev) | set(data) if prev.get(k) != data.get(k)})
    critical = any(k in CRITICAL_FIELDS for k in changed)
    v = VisaFormVersion(case_id=c.id, version=(last.version + 1 if last else 1), state="DRAFT",
                        data=data, changed_fields=changed, critical_changed=bool(last) and critical,
                        created_by=u.username)
    db.add(v)
    db.flush()
    if v.critical_changed:
        # Thay thông tin quan trọng ⇒ bản khách đã xác nhận không còn dùng được, phải xin xác nhận lại.
        open_task(db, u, c, "khach_xac_nhan", f"Xin khách xác nhận lại form v{v.version} – {c.applicant_name}",
                  c.visa_owner_user_id or c.sales_user_id, priority="cao")
        if c.current_stage in ("thu_thap_tai_lieu", "kiem_tra"):
            c.current_stage = "khach_xac_nhan"
    _audit(db, u, "visa_luu_form", c, after={"phien_ban": v.version, "truong_doi": changed,
                                             "doi_thong_tin_quan_trong": v.critical_changed})
    return v


def send_form(db: Session, u: User, c: VisaCase, version_id: int) -> VisaFormVersion:
    v = db.get(VisaFormVersion, version_id)
    if not v or v.case_id != c.id:
        raise VisaError("Không có phiên bản form này trong hồ sơ")
    if v.state == "CONFIRMED":
        raise VisaError("Phiên bản này khách đã xác nhận rồi")
    v.state = "SENT"
    if c.current_stage == "khai_thong_tin":
        _advance(db, u, c, "khai_thong_tin", "gui_form", {"form_version": v.version})
    else:
        _audit(db, u, "visa_gui_form", c, after={"form_version": v.version})
    return v


def confirm_form(db: Session, u: User, c: VisaCase, version_id: int, confirmed_by_name: str,
                 channel: str = "link", evidence: str = "", access_link_id: int | None = None) -> VisaConfirmation:
    """Khách xác nhận ĐÚNG một phiên bản. Xác nhận phiên bản cũ không có giá trị."""
    _editable(c)
    v = db.get(VisaFormVersion, version_id)
    if not v or v.case_id != c.id:
        raise VisaError("Không có phiên bản form này trong hồ sơ")
    newest = db.execute(select(VisaFormVersion).where(VisaFormVersion.case_id == c.id)
                        .order_by(VisaFormVersion.version.desc())).scalars().first()
    if newest and v.id != newest.id:
        raise VisaError(f"Form đã có phiên bản mới hơn (v{newest.version}) – phải xác nhận đúng phiên bản mới nhất")
    if v.state == "DRAFT":
        raise VisaError("Phiên bản này chưa gửi cho khách")
    v.state = "CONFIRMED"
    cf = VisaConfirmation(case_id=c.id, form_version_id=v.id, confirmed_by_name=confirmed_by_name,
                          channel=channel, evidence=evidence, access_link_id=access_link_id)
    db.add(cf)
    if c.current_stage == "khach_xac_nhan":
        _advance(db, u, c, "khach_xac_nhan", "khach_xac_nhan", {"form_version": v.version})
    else:
        _audit(db, u, "visa_khach_xac_nhan", c, after={"form_version": v.version})
    return cf


def confirmed_form(db: Session, case_id: int) -> VisaFormVersion | None:
    return db.execute(select(VisaFormVersion).where(VisaFormVersion.case_id == case_id,
                                                    VisaFormVersion.state.in_(("CONFIRMED", "USED")))
                      .order_by(VisaFormVersion.version.desc())).scalars().first()


# ---------- Tài liệu ----------
def add_document(db: Session, u: User, c: VisaCase, item_id: int | None, content: bytes,
                 file_name: str, content_type: str) -> VisaDocument:
    """Tải tài liệu. Nộp lại KHÔNG ghi đè: sinh phiên bản mới và bắt kiểm tra lại từ đầu."""
    _editable(c)
    if not content:
        raise VisaError("Tệp rỗng")
    if len(content) > MAX_DOC_BYTES:
        raise VisaError(f"Tệp vượt {MAX_DOC_BYTES // 1024 // 1024} MB")
    item = None
    if item_id:
        item = db.get(VisaChecklistItem, item_id)
        if not item or item.case_id != c.id:
            raise VisaError("Mục checklist không thuộc hồ sơ này")
    last = db.execute(select(VisaDocument).where(VisaDocument.case_id == c.id,
                                                 VisaDocument.checklist_item_id == item_id)
                      .order_by(VisaDocument.version.desc())).scalars().first()
    checksum = hashlib.sha256(content).hexdigest()
    doc = VisaDocument(case_id=c.id, checklist_item_id=item_id, version=(last.version + 1 if last else 1),
                       file_name=(file_name or "tai-lieu")[:255], content_type=content_type or "",
                       size_bytes=len(content), checksum=checksum, uploaded_by=u.username)
    db.add(doc)
    db.flush()
    # Tên tệp KHÔNG dùng làm định danh: đặt theo id + băm để khách không đoán được đường dẫn của hồ sơ khác.
    try:
        st = ST.put_document(c.id, doc.id, content, content_type)
    except ST.StorageError as ex:
        # Không ghi bản ghi tài liệu khi tệp chưa nằm an toàn trên kho – thà báo lỗi còn hơn để lại một dòng
        # trỏ vào chỗ trống rồi tới lúc nộp lãnh sự quán mới phát hiện mất tệp.
        db.rollback()
        raise VisaError(f"Chưa lưu được tệp nên chưa ghi nhận tài liệu. {ex}")
    doc.storage_path = st.key
    if last:
        last.superseded_by = doc.id
    if item:
        was = item.status
        item.status, item.current_document_id = "UPLOADED", doc.id
        item.needs_recheck = False
        item.reviewed_by, item.reviewed_at = "", None
        if was == "ACCEPTED":
            # Tài liệu đã duyệt mà bị thay thế thì phải quay lại kiểm tra (mục 6.3).
            open_task(db, u, c, "kiem_tra", f"Kiểm tra lại {item.name} (bản mới) – {c.applicant_name}",
                      c.visa_owner_user_id, priority="cao")
    _audit(db, u, "visa_tai_tai_lieu", c, after={"tai_lieu_id": doc.id, "muc": item.key if item else "",
                                                 "phien_ban": doc.version, "sha256": checksum[:16]})
    return doc


def review_document(db: Session, u: User, c: VisaCase, doc_id: int, decision: str, reason: str = "") -> VisaDocumentReview:
    """Người kiểm tra chấp nhận hoặc yêu cầu nộp lại. Đây là việc của chuyên viên, không phải của khách."""
    _require(u, REVIEWER_ROLES + ("nv_dh", "nv_visa"), "duyệt tài liệu")
    _editable(c)
    doc = db.get(VisaDocument, doc_id)
    if not doc or doc.case_id != c.id:
        raise VisaError("Tài liệu không thuộc hồ sơ này")
    if doc.superseded_by:
        raise VisaError("Bản này đã bị thay bằng phiên bản mới – kiểm bản mới nhất")
    if decision not in ("ACCEPTED", "NEEDS_REPLACEMENT"):
        raise VisaError("Quyết định phải là ACCEPTED hoặc NEEDS_REPLACEMENT")
    if decision == "NEEDS_REPLACEMENT" and not reason.strip():
        raise VisaError("Yêu cầu nộp lại thì phải ghi lý do để khách biết cần sửa gì")
    rv = VisaDocumentReview(document_id=doc.id, case_id=c.id, decision=decision,
                            reason=reason, reviewer=u.username)
    db.add(rv)
    item = db.get(VisaChecklistItem, doc.checklist_item_id) if doc.checklist_item_id else None
    if item:
        item.status = decision
        item.needs_recheck = False
        item.reviewed_by, item.reviewed_at = u.username, _now()
        item.note = reason
    _audit(db, u, "visa_kiem_tra_tai_lieu", c, after={"tai_lieu_id": doc.id, "quyet_dinh": decision, "ly_do": reason})
    return rv


def request_waiver(db: Session, u: User, c: VisaCase, item_id: int, reason: str) -> VisaWaiver:
    """Khách báo không nộp ⇒ chỉ là ĐỀ NGHỊ. Không tự thành đã miễn (nghiệm thu 4)."""
    _editable(c)
    if not (reason or "").strip():
        raise VisaError("Đề nghị miễn nộp phải có lý do")
    item = db.get(VisaChecklistItem, item_id)
    if not item or item.case_id != c.id:
        raise VisaError("Mục checklist không thuộc hồ sơ này")
    if db.execute(select(VisaWaiver).where(VisaWaiver.checklist_item_id == item.id,
                                           VisaWaiver.decision == "PENDING")).scalars().first():
        raise VisaError("Mục này đã có đề nghị miễn nộp đang chờ quyết định")
    w = VisaWaiver(case_id=c.id, checklist_item_id=item.id, reason=reason, requested_by=u.username)
    db.add(w)
    item.status = "WAIVER_REQUESTED"
    db.flush()
    open_task(db, u, c, "duyet_ngoai_le", f"Quyết định miễn nộp «{item.name}» – {c.applicant_name}",
              c.supervisor_user_id, priority="cao")
    _audit(db, u, "visa_de_nghi_mien_nop", c, after={"muc": item.key, "ly_do": reason})
    return w


def decide_waiver(db: Session, u: User, c: VisaCase, waiver_id: int, approve: bool, note: str = "") -> VisaWaiver:
    _require(u, WAIVER_DECIDER, "quyết định miễn nộp tài liệu")
    w = db.get(VisaWaiver, waiver_id)
    if not w or w.case_id != c.id:
        raise VisaError("Đề nghị không thuộc hồ sơ này")
    if w.decision != "PENDING":
        raise VisaError("Đề nghị này đã được quyết định")
    if not approve and not (note or "").strip():
        raise VisaError("Từ chối miễn nộp thì phải ghi lý do")
    w.decision = "APPROVED" if approve else "REJECTED"
    w.decided_by, w.decided_at, w.decision_note = u.username, _now(), note
    item = db.get(VisaChecklistItem, w.checklist_item_id)
    if item:
        item.status = "WAIVED" if approve else "MISSING"
        item.reviewed_by, item.reviewed_at, item.note = u.username, _now(), note
    _close_tasks(db, c, "duyet_ngoai_le", "quyết định miễn nộp")
    _audit(db, u, "visa_quyet_dinh_mien_nop", c, after={"muc": item.key if item else "", "duyet": approve, "ghi_chu": note})
    return w


# ---------- Chuyển bước có điều kiện ----------
def submit_for_review(db: Session, u: User, c: VisaCase) -> VisaCase:
    """Gửi kiểm tra: chỉ cần đã thu thập xong phần khách phải nộp; việc chấp nhận là của người kiểm tra."""
    _editable(c)
    if c.current_stage != "thu_thap_tai_lieu":
        raise VisaError(f"Hồ sơ đang ở bước «{STAGES.get(c.current_stage, c.current_stage)}», chưa tới bước gửi kiểm tra")
    s = checklist_summary(db, c.id)
    pending = [i.key for i in db.execute(select(VisaChecklistItem)
                                         .where(VisaChecklistItem.case_id == c.id,
                                                VisaChecklistItem.required == True,
                                                VisaChecklistItem.status.in_(("MISSING", "NEEDS_REPLACEMENT")))).scalars()]
    if pending:
        raise VisaError("Chưa nộp hoặc cần nộp lại các mục bắt buộc: " + ", ".join(pending))
    _advance(db, u, c, "thu_thap_tai_lieu", "gui_kiem_tra", {"checklist": s})
    return c


def pass_review(db: Session, u: User, c: VisaCase) -> VisaCase:
    """Xác nhận đã kiểm tra xong: mọi mục bắt buộc phải ACCEPTED, WAIVED (đã duyệt) hoặc NOT_APPLICABLE."""
    _require(u, REVIEWER_ROLES + ("nv_dh", "nv_visa"), "xác nhận kết quả kiểm tra hồ sơ")
    _editable(c)
    if c.current_stage != "kiem_tra":
        raise VisaError(f"Hồ sơ đang ở bước «{STAGES.get(c.current_stage, c.current_stage)}»")
    if not confirmed_form(db, c.id):
        raise VisaError("Chưa có phiên bản form nào được khách xác nhận")
    bad = [i.key for i in db.execute(select(VisaChecklistItem)
                                     .where(VisaChecklistItem.case_id == c.id,
                                            VisaChecklistItem.required == True)).scalars()
           if i.status not in DOC_SATISFIED or i.needs_recheck]
    if bad:
        raise VisaError("Còn mục bắt buộc chưa được chấp nhận hoặc phải kiểm lại: " + ", ".join(bad))
    _advance(db, u, c, "kiem_tra", "kiem_tra_dat", {"checklist": checklist_summary(db, c.id)})
    return c


def record_application(db: Session, u: User, c: VisaCase, reference_code: str, portal: str = "",
                       evidence: str = "", note: str = "") -> VisaApplication:
    """Ghi nhận đã khai/nộp hồ sơ chính thức. Hệ thống không tự nộp – chỉ lưu mã tham chiếu và bằng chứng."""
    _editable(c)
    if c.current_stage != "khai_ho_so":
        raise VisaError("Chưa qua bước kiểm tra nên chưa khai hồ sơ chính thức được")
    if not (reference_code or "").strip():
        raise VisaError("Phải có mã tham chiếu hồ sơ do hệ thống LSQ/ĐSQ cấp")
    exist = db.execute(select(VisaApplication).where(VisaApplication.case_id == c.id,
                                                     VisaApplication.reference_code == reference_code.strip())).scalars().first()
    if exist:
        return exist                                    # bấm lại / mạng gửi lại: không sinh bản ghi trùng
    fv = confirmed_form(db, c.id)
    if fv:
        fv.state = "USED"
    a = VisaApplication(case_id=c.id, reference_code=reference_code.strip(), portal=portal,
                        form_version_id=fv.id if fv else None, submitted_by=u.username,
                        evidence=evidence, note=note)
    db.add(a)
    _advance(db, u, c, "khai_ho_so", "khai_ho_so", {"ma_tham_chieu": a.reference_code})
    return a


def set_appointment(db: Session, u: User, c: VisaCase, starts_at: datetime, location: str,
                    timezone: str = "Asia/Ho_Chi_Minh", escort: str = "", confirmation_ref: str = "") -> VisaAppointment:
    _editable(c)
    ap = VisaAppointment(case_id=c.id, starts_at=starts_at, timezone=timezone, location=location,
                         escort=escort, confirmation_ref=confirmation_ref, created_by=u.username)
    db.add(ap)
    db.flush()
    if c.current_stage == "lich_hen":
        _advance(db, u, c, "lich_hen", "ghi_lich_hen", {"lich_hen_id": ap.id, "luc": starts_at.isoformat()})
    else:
        _audit(db, u, "visa_ghi_lich_hen", c, after={"lich_hen_id": ap.id, "luc": starts_at.isoformat()})
    return ap


def reschedule(db: Session, u: User, c: VisaCase, appointment_id: int, starts_at: datetime,
               reason: str, location: str = "", timezone: str = "") -> VisaAppointment:
    """Đổi lịch: lịch cũ giữ nguyên trạng thái RESCHEDULED, lịch mới trỏ về lịch cũ kèm người đổi và lý do."""
    _editable(c)
    old = db.get(VisaAppointment, appointment_id)
    if not old or old.case_id != c.id:
        raise VisaError("Lịch hẹn không thuộc hồ sơ này")
    if not (reason or "").strip():
        raise VisaError("Đổi lịch phải ghi lý do")
    if old.status in ("RESCHEDULED", "CANCELLED"):
        raise VisaError("Lịch này đã được đổi hoặc đã hủy")
    old.status = "RESCHEDULED"
    new = VisaAppointment(case_id=c.id, starts_at=starts_at, timezone=timezone or old.timezone,
                          location=location or old.location, escort=old.escort,
                          replaces_id=old.id, reschedule_reason=reason, created_by=u.username)
    db.add(new)
    db.flush()
    _audit(db, u, "visa_doi_lich_hen", c, before={"lich_cu": old.starts_at.isoformat()},
           after={"lich_moi": starts_at.isoformat(), "ly_do": reason, "nguoi_doi": u.username})
    return new


def record_biometrics(db: Session, u: User, c: VisaCase, appointment_id: int, attended: bool, note: str = "") -> VisaAppointment:
    """Ghi nhận kết quả thực hiện. Lịch quá giờ mà chưa cập nhật KHÔNG tự coi là khách vắng mặt."""
    _editable(c)
    ap = db.get(VisaAppointment, appointment_id)
    if not ap or ap.case_id != c.id:
        raise VisaError("Lịch hẹn không thuộc hồ sơ này")
    if not attended and not (note or "").strip():
        raise VisaError("Ghi nhận khách không đến thì phải nêu rõ căn cứ")
    ap.status = "ATTENDED" if attended else "MISSED"
    ap.biometrics_done = bool(attended)
    ap.biometrics_note = note
    _close_tasks(db, c, "xac_minh_lich_hen", "cập nhật lịch hẹn")
    if attended and c.current_stage == "sinh_trac_hoc":
        _advance(db, u, c, "sinh_trac_hoc", "sinh_trac_hoc", {"lich_hen_id": ap.id})
    else:
        _audit(db, u, "visa_ghi_sinh_trac_hoc", c, after={"lich_hen_id": ap.id, "co_mat": attended, "ghi_chu": note})
    return ap


def record_result(db: Session, u: User, c: VisaCase, outcome: str, received_on: date, evidence: str = "",
                  visa_valid_from: date | None = None, visa_valid_to: date | None = None,
                  entries: str = "", refusal_reason: str = "") -> VisaResult:
    """Kết quả của RIÊNG hồ sơ này – không lây sang thành viên khác trong nhà (nghiệm thu 2)."""
    _editable(c)
    if outcome not in ("GRANTED", "REFUSED"):
        raise VisaError("Kết quả phải là GRANTED hoặc REFUSED")
    if outcome == "REFUSED" and not (refusal_reason or "").strip():
        raise VisaError("Ghi nhận từ chối thì phải nêu lý do theo thông báo của LSQ/ĐSQ")
    r = VisaResult(case_id=c.id, outcome=outcome, received_on=received_on, visa_valid_from=visa_valid_from,
                   visa_valid_to=visa_valid_to, entries=entries, refusal_reason=refusal_reason,
                   evidence=evidence, recorded_by=u.username)
    db.add(r)
    c.result_status = outcome
    if c.current_stage == "theo_doi_ket_qua":
        _advance(db, u, c, "theo_doi_ket_qua", "ghi_ket_qua", {"ket_qua": outcome})
    else:
        _audit(db, u, "visa_ghi_ket_qua", c, after={"ket_qua": outcome})
    return r


def record_handover(db: Session, u: User, c: VisaCase, direction: str, item_type: str, to_party: str,
                    from_party: str = "", quantity: int = 1, method: str = "", confirmed: bool = False,
                    evidence: str = "", note: str = "") -> VisaHandover:
    h = VisaHandover(case_id=c.id, direction=direction, item_type=item_type, quantity=quantity,
                     from_party=from_party, to_party=to_party, method=method, confirmed=confirmed,
                     evidence=evidence, recorded_by=u.username, note=note)
    db.add(h)
    db.flush()
    if confirmed and direction == "TRA_KHACH" and c.current_stage == "ban_giao":
        _advance(db, u, c, "ban_giao", "ban_giao", {"ban_giao_id": h.id})
    else:
        _audit(db, u, "visa_ghi_ban_giao", c, after={"chieu": direction, "loai": item_type, "da_xac_nhan": confirmed})
    return h


def close_case(db: Session, u: User, c: VisaCase) -> VisaCase:
    """Đóng hồ sơ: phải có kết quả, đã trả giấy tờ (có xác nhận), và không còn đề nghị ngoại lệ treo."""
    _require(u, REVIEWER_ROLES, "đóng hồ sơ Visa")
    if c.lifecycle_status == "CLOSED":
        return c
    _editable(c)
    if c.result_status == "NOT_AVAILABLE":
        raise VisaError("Chưa ghi nhận kết quả nên chưa đóng hồ sơ được")
    if not db.execute(select(VisaHandover).where(VisaHandover.case_id == c.id,
                                                 VisaHandover.direction == "TRA_KHACH",
                                                 VisaHandover.confirmed == True)).scalars().first():
        raise VisaError("Chưa có xác nhận trả giấy tờ cho khách")
    if db.execute(select(VisaWaiver).where(VisaWaiver.case_id == c.id, VisaWaiver.decision == "PENDING")).scalars().first():
        raise VisaError("Còn đề nghị miễn nộp chưa được quyết định")
    for t in db.execute(select(VisaTask).where(VisaTask.case_id == c.id,
                                               VisaTask.status.in_(("open", "doing", "waiting")))).scalars():
        t.status, t.done_at = "done", _now()
    c.lifecycle_status, c.current_stage = "CLOSED", "dong_ho_so"
    c.row_version += 1
    _audit(db, u, "visa_dong_ho_so", c, after={"ket_qua": c.result_status})
    return c


def hold(db: Session, u: User, c: VisaCase, reason: str) -> VisaCase:
    if not (reason or "").strip():
        raise VisaError("Tạm dừng phải ghi lý do")
    if c.lifecycle_status in ("CLOSED", "CANCELLED"):
        raise VisaError("Hồ sơ đã đóng hoặc đã hủy")
    c.lifecycle_status, c.hold_reason = "ON_HOLD", reason
    c.row_version += 1
    _audit(db, u, "visa_tam_dung", c, after={"ly_do": reason})
    return c


def resume(db: Session, u: User, c: VisaCase) -> VisaCase:
    if c.lifecycle_status != "ON_HOLD":
        raise VisaError("Hồ sơ không ở trạng thái tạm dừng")
    c.lifecycle_status, c.hold_reason = "ACTIVE", ""
    c.row_version += 1
    _audit(db, u, "visa_tiep_tuc", c)
    return c


def cancel(db: Session, u: User, c: VisaCase, reason: str) -> VisaCase:
    """Hủy MỘT hồ sơ. Không xóa dữ liệu, không đụng tới thành viên khác trong nhóm (nghiệm thu 10)."""
    _require(u, ASSIGNER_ROLES, "hủy hồ sơ Visa")
    if not (reason or "").strip():
        raise VisaError("Hủy hồ sơ phải ghi lý do")
    if c.lifecycle_status == "CLOSED":
        raise VisaError("Hồ sơ đã đóng")
    c.lifecycle_status, c.cancellation_reason = "CANCELLED", reason
    c.row_version += 1
    for t in db.execute(select(VisaTask).where(VisaTask.case_id == c.id,
                                               VisaTask.status.in_(("open", "doing", "waiting")))).scalars():
        t.status, t.done_at, t.waiting_reason = "cancelled", _now(), "hồ sơ bị hủy"
    _audit(db, u, "visa_huy_ho_so", c, after={"ly_do": reason})
    return c


def cancel_group_preview(db: Session, group_id: int) -> list[dict]:
    """Hủy cả nhóm phải liệt kê thành viên bị ảnh hưởng TRƯỚC khi làm (mục 9)."""
    rows = db.execute(select(VisaCase).where(VisaCase.family_group_id == group_id)).scalars()
    return [{"case_code": c.case_code, "ten": c.applicant_name, "giai_doan": c.current_stage,
             "trang_thai": c.lifecycle_status, "ket_qua": c.result_status} for c in rows]


def link_hr_visa_file(db: Session, u: User, c: VisaCase, hr_file_id: int | None) -> VisaCase:
    """Nối hồ sơ nghiệp vụ với bản ghi quỹ visa của Nhân sự (visa_files), hoặc gỡ nối khi truyền None.

    CỐ Ý không tự tạo/tự sửa bản ghi quỹ visa: đó là dữ liệu tính thù lao, thuộc phân hệ Nhân sự và có quy tắc
    riêng. Ở đây chỉ ghi nhận "hồ sơ này chính là hồ sơ kia" để hai bên đối chiếu được, không nhập liệu hai lần."""
    from app.models.hr import VisaFile
    if hr_file_id is not None and not db.get(VisaFile, hr_file_id):
        raise VisaError("Không có hồ sơ quỹ visa này trong phân hệ Nhân sự")
    if hr_file_id is not None:
        other = db.execute(select(VisaCase).where(VisaCase.hr_visa_file_id == hr_file_id,
                                                  VisaCase.id != c.id)).scalars().first()
        if other:
            raise VisaError(f"Bản ghi quỹ visa này đã nối với hồ sơ {other.case_code}")
    c.hr_visa_file_id = hr_file_id
    c.row_version += 1
    _audit(db, u, "visa_noi_quy_visa_nhan_su", c, after={"visa_file_id": hr_file_id})
    return c


# ---------- Nhóm gia đình ----------
def create_group(db: Session, u: User, data: dict) -> VisaFamilyGroup:
    g = VisaFamilyGroup(code=_new_code(db, "VGF", VisaFamilyGroup, VisaFamilyGroup.code),
                        company_id=resolve_company(db, data.get("company_id"), data.get("company_code", "")),
                        name=data.get("name", ""), contact_name=data.get("contact_name", ""),
                        contact_phone=data.get("contact_phone", ""), contact_email=data.get("contact_email", ""),
                        booking_id=data.get("booking_id"),
                        contact_sees_members=bool(data.get("contact_sees_members")),
                        created_by=u.username)
    db.add(g)
    db.flush()
    R.audit(db, u.username, u.role, "visa_tao_nhom_gia_dinh", f"visa_nhom:{g.code}", after={"ten": g.name})
    return g


def add_to_group(db: Session, u: User, g: VisaFamilyGroup, c: VisaCase, role: str = "", main: bool = False) -> VisaCase:
    c.family_group_id, c.family_role = g.id, role
    if c.booking_id is None and g.booking_id:
        c.booking_id = g.booking_id          # chỉ điền khi trống – KHÔNG ghi đè liên kết riêng của thành viên
    if main:
        g.main_case_id = c.id
    c.row_version += 1
    _audit(db, u, "visa_them_vao_nhom", c, after={"nhom": g.code, "vai_tro": role, "duong_don_chinh": main})
    return c


# ---------- Liên kết cho khách ----------
def issue_link(db: Session, u: User, c: VisaCase, scopes: list[str], days: int = 14) -> tuple[VisaAccessLink, str]:
    """Sinh liên kết. Trả mã thô ĐÚNG MỘT LẦN cho người gọi; CSDL và nhật ký chỉ giữ băm."""
    bad = set(scopes) - {"view", "fill", "upload", "confirm"}
    if bad:
        raise VisaError("Quyền không hợp lệ: " + ", ".join(sorted(bad)))
    raw = secrets.token_urlsafe(32)
    link = VisaAccessLink(case_id=c.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                          scopes=sorted(set(scopes)), expires_at=_now() + timedelta(days=days),
                          created_by=u.username)
    db.add(link)
    db.flush()
    _audit(db, u, "visa_cap_lien_ket_khach", c, after={"quyen": link.scopes, "het_han": link.expires_at.isoformat()})
    return link, raw


def use_link(db: Session, raw_token: str, scope_needed: str) -> VisaAccessLink:
    """Kiểm quyền MỖI LẦN truy cập: hết hạn, thu hồi, sai phạm vi đều bị chặn (nghiệm thu 11)."""
    h = hashlib.sha256((raw_token or "").encode()).hexdigest()
    link = db.execute(select(VisaAccessLink).where(VisaAccessLink.token_hash == h)).scalar_one_or_none()
    if not link or link.revoked or link.expires_at < _now():
        raise VisaError("Liên kết không còn hiệu lực")
    if scope_needed not in (link.scopes or []):
        raise VisaError("Liên kết này không có quyền thực hiện thao tác đó")
    link.used_count += 1
    link.last_used_at = _now()
    return link


def revoke_link(db: Session, u: User, c: VisaCase, link_id: int) -> VisaAccessLink:
    link = db.get(VisaAccessLink, link_id)
    if not link or link.case_id != c.id:
        raise VisaError("Liên kết không thuộc hồ sơ này")
    link.revoked = True
    _audit(db, u, "visa_thu_hoi_lien_ket", c, after={"link_id": link.id})
    return link


# ---------- Công việc ----------
def update_task(db: Session, u: User, task_id: int, status: str = "", waiting_reason: str = "",
                assignee_user_id: int | None = None, evidence: str = "") -> VisaTask:
    t = db.get(VisaTask, task_id)
    if not t:
        raise VisaError("Không có công việc này")
    c = get_case(db, t.case_id)
    ensure_see(u, c)
    if status:
        if status not in ("open", "doing", "waiting", "done", "cancelled"):
            raise VisaError("Trạng thái công việc không hợp lệ")
        if status == "waiting" and not (waiting_reason or t.waiting_reason):
            raise VisaError("Chuyển sang chờ bên ngoài thì phải ghi lý do chờ")
        t.status = status
        if status == "done":
            t.done_at = _now()
    if waiting_reason:
        t.waiting_reason = waiting_reason
    if assignee_user_id is not None:
        _require(u, ASSIGNER_ROLES, "chuyển người nhận việc")
        t.assignee_user_id = assignee_user_id
    if evidence:
        t.evidence = evidence
    _audit(db, u, "visa_cap_nhat_cong_viec", c, after={"task_id": t.id, "trang_thai": t.status})
    return t


def sweep_overdue(db: Session) -> dict:
    """Robot: hai loại cảnh báo TÁCH BẠCH (mục 7) – việc nhân viên quá hạn, và nguy cơ trễ ngày đi / lịch hẹn.

    Lịch hẹn đã qua mà chưa cập nhật thì tạo công việc XÁC MINH, tuyệt đối không tự ghi khách vắng mặt."""
    now = _now()
    overdue = list(db.execute(select(VisaTask).where(VisaTask.due_at != None, VisaTask.due_at < now,
                                                     VisaTask.status.in_(("open", "doing")))).scalars())
    risk = []
    for c in db.execute(select(VisaCase).where(VisaCase.lifecycle_status == "ACTIVE",
                                               VisaCase.result_status == "NOT_AVAILABLE",
                                               VisaCase.departure_date != None)).scalars():
        if (c.departure_date - now.date()).days <= 14:
            risk.append({"case_code": c.case_code, "ten": c.applicant_name, "ngay_di": str(c.departure_date),
                         "giai_doan": c.current_stage, "con_lai_ngay": (c.departure_date - now.date()).days})
    unverified = []
    for ap in db.execute(select(VisaAppointment).where(VisaAppointment.status == "SCHEDULED",
                                                       VisaAppointment.starts_at < now)).scalars():
        c = db.get(VisaCase, ap.case_id)
        if not c or c.lifecycle_status != "ACTIVE":
            continue
        unverified.append({"case_code": c.case_code, "lich_hen_id": ap.id, "luc": ap.starts_at.isoformat()})
        old = db.execute(select(VisaTask).where(VisaTask.case_id == c.id, VisaTask.kind == "xac_minh_lich_hen",
                                                VisaTask.status.in_(("open", "doing", "waiting")))).scalars().first()
        if not old:
            db.add(VisaTask(case_id=c.id, kind="xac_minh_lich_hen",
                            title=f"Xác minh lịch hẹn đã qua – {c.applicant_name}",
                            assignee_user_id=c.visa_owner_user_id, priority="cao", created_by="robot"))
    return {"cong_viec_qua_han": [{"task_id": t.id, "case_id": t.case_id, "tieu_de": t.title,
                                   "han": t.due_at.isoformat()} for t in overdue],
            "nguy_co_tre_ngay_di": risk, "lich_hen_chua_xac_minh": unverified}


# ---------- Danh sách & bảng điều khiển ----------
def _case_row(db: Session, c: VisaCase, names: dict) -> dict:
    s = checklist_summary(db, c.id)
    nxt = db.execute(select(VisaTask).where(VisaTask.case_id == c.id,
                                            VisaTask.status.in_(("open", "doing", "waiting")))
                     .order_by(VisaTask.due_at.is_(None), VisaTask.due_at)).scalars().first()
    return {"id": c.id, "case_code": c.case_code, "company_id": c.company_id,
            "applicant_name": c.applicant_name, "family_group_id": c.family_group_id,
            "booking_id": c.booking_id, "tour_id": c.tour_id,
            "market_code": c.market_code, "visa_type": c.visa_type, "service_mode": c.service_mode,
            "departure_date": c.departure_date, "sales": names.get(c.sales_user_id, ""),
            "visa_owner": names.get(c.visa_owner_user_id, ""),
            "current_stage": c.current_stage, "stage_name": STAGES.get(c.current_stage, c.current_stage),
            "lifecycle_status": c.lifecycle_status, "result_status": c.result_status,
            "next_task": nxt.title if nxt else "", "due_at": nxt.due_at if nxt else None,
            "overdue": bool(nxt and nxt.due_at and nxt.due_at < _now()),
            "documents": f"{s['da_chap_nhan']}/{s['bat_buoc']}", "is_test": c.is_test,
            "row_version": c.row_version, "updated_at": c.updated_at}


def _names(db: Session) -> dict:
    return {u.id: u.full_name for u in db.execute(select(User)).scalars()}


def list_cases(db: Session, u: User, f: dict, limit: int = 200, offset: int = 0) -> dict:
    q = select(VisaCase)
    if f.get("company_id"):
        q = q.where(VisaCase.company_id == int(f["company_id"]))
    if f.get("market_code"):
        q = q.where(VisaCase.market_code == f["market_code"].upper())
    if f.get("service_mode"):
        q = q.where(VisaCase.service_mode == f["service_mode"])
    if f.get("stage"):
        q = q.where(VisaCase.current_stage == f["stage"])
    if f.get("lifecycle_status"):
        q = q.where(VisaCase.lifecycle_status == f["lifecycle_status"])
    if f.get("result_status"):
        q = q.where(VisaCase.result_status == f["result_status"])
    if f.get("visa_owner_user_id"):
        q = q.where(VisaCase.visa_owner_user_id == int(f["visa_owner_user_id"]))
    if f.get("sales_user_id"):
        q = q.where(VisaCase.sales_user_id == int(f["sales_user_id"]))
    if f.get("since"):
        q = q.where(VisaCase.departure_date >= f["since"])
    if f.get("upto"):
        q = q.where(VisaCase.departure_date <= f["upto"])
    if not f.get("include_test"):
        q = q.where(VisaCase.is_test == False)      # dữ liệu thử nghiệm KHÔNG lẫn vào số liệu vận hành
    if f.get("q"):
        kw = f"%{f['q'].strip().lower()}%"
        q = q.where(or_(func.lower(VisaCase.applicant_name).like(kw), func.lower(VisaCase.case_code).like(kw)))
    q = scope(u, q)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.order_by(VisaCase.updated_at.desc()).limit(limit).offset(offset)).scalars()
    names = _names(db)
    return {"total": total, "limit": limit, "offset": offset,
            "rows": [_case_row(db, c, names) for c in rows]}


def dashboard(db: Session, u: User, f: dict) -> dict:
    """Chỉ số KHÔNG cộng nhóm gia đình với thành viên thành một con số (mục 3.2)."""
    base = scope(u, select(VisaCase).where(VisaCase.lifecycle_status.in_(("ACTIVE", "ON_HOLD"))))
    if not f.get("include_test"):
        base = base.where(VisaCase.is_test == False)
    if f.get("market_code"):
        base = base.where(VisaCase.market_code == f["market_code"].upper())
    if f.get("company_id"):
        base = base.where(VisaCase.company_id == int(f["company_id"]))
    cases = list(db.execute(base).scalars())
    ids = [c.id for c in cases]
    now = _now()

    def n(pred):
        return sum(1 for c in cases if pred(c))

    open_tasks = list(db.execute(select(VisaTask).where(VisaTask.case_id.in_(ids or [0]),
                                                        VisaTask.status.in_(("open", "doing", "waiting")))).scalars()) if ids else []
    appts = list(db.execute(select(VisaAppointment).where(VisaAppointment.case_id.in_(ids or [0]),
                                                          VisaAppointment.status == "SCHEDULED")).scalars()) if ids else []
    # Trước đây chỗ này hỏi cơ sở dữ liệu MỘT LẦN CHO MỖI hồ sơ đã có kết quả. Vài nghìn hồ sơ là vài nghìn
    # lượt truy vấn cho một con số trên bảng điều khiển. Nay lấy một lần danh sách hồ sơ ĐÃ bàn giao rồi trừ ra.
    co_ket_qua = [c.id for c in cases if c.result_status != "NOT_AVAILABLE"]
    da_ban_giao = set()
    if co_ket_qua:
        da_ban_giao = {r[0] for r in db.execute(
            select(VisaHandover.case_id).where(VisaHandover.case_id.in_(co_ket_qua),
                                               VisaHandover.direction == "TRA_KHACH",
                                               VisaHandover.confirmed == True).distinct()).all()}
    done_no_handover = len([i for i in co_ket_qua if i not in da_ban_giao])
    return {
        "ho_so_ca_nhan_dang_xu_ly": len([c for c in cases if not c.family_group_id]),
        "ho_so_thuoc_nhom_dang_xu_ly": len([c for c in cases if c.family_group_id]),
        "so_nhom_gia_dinh": len({c.family_group_id for c in cases if c.family_group_id}),
        "chua_phan_cong": n(lambda c: not c.visa_owner_user_id),
        "cho_khach_bo_sung": n(lambda c: c.current_stage in ("khai_thong_tin", "khach_xac_nhan", "thu_thap_tai_lieu")),
        "cho_kiem_tra_noi_bo": n(lambda c: c.current_stage == "kiem_tra"),
        "tam_dung": n(lambda c: c.lifecycle_status == "ON_HOLD"),
        "lich_hen_sap_toi": len([a for a in appts if a.starts_at >= now]),
        "lich_da_qua_chua_xac_nhan": len([a for a in appts if a.starts_at < now]),
        "viec_qua_han": len([t for t in open_tasks if t.due_at and t.due_at < now]),
        "da_co_ket_qua_chua_ban_giao": done_no_handover,
        "ghi_chu": "Hồ sơ hủy và dữ liệu thử nghiệm không nằm trong các chỉ số trên.",
    }


def case_detail(db: Session, u: User, c: VisaCase) -> dict:
    names = _names(db)
    forms = list(db.execute(select(VisaFormVersion).where(VisaFormVersion.case_id == c.id)
                            .order_by(VisaFormVersion.version.desc())).scalars())
    items = list(db.execute(select(VisaChecklistItem).where(VisaChecklistItem.case_id == c.id)
                            .order_by(VisaChecklistItem.id)).scalars())
    docs = list(db.execute(select(VisaDocument).where(VisaDocument.case_id == c.id)
                           .order_by(VisaDocument.id.desc())).scalars())
    booking = db.get(Booking, c.booking_id) if c.booking_id else None
    tour = db.get(Tour, c.tour_id) if c.tour_id else None
    return {
        "case": _case_row(db, c, names),
        "applicant": {"ten": c.applicant_name, "ngay_sinh": c.applicant_dob, "dien_thoai": c.applicant_phone,
                      "email": c.applicant_email, "ho_chieu_4_so_cuoi": c.passport_last4,
                      "ho_chieu_het_han": c.passport_expiry},
        "quy_visa_nhan_su": c.hr_visa_file_id,
        "chuyen_di": {"booking": booking.code if booking else "", "tour": tour.code if tour else "",
                      "tour_ten": tour.name if tour else "", "ngay_di": c.departure_date, "ngay_ve": c.return_date},
        "quy_trinh": {"cac_buoc": stages_for(_market(db, c.market_code)), "hien_tai": c.current_stage},
        "form": [{"id": f.id, "version": f.version, "state": f.state, "truong_doi": f.changed_fields,
                  "doi_thong_tin_quan_trong": f.critical_changed, "nguoi_lap": f.created_by,
                  "luc": f.created_at} for f in forms],
        "checklist": [{"id": i.id, "key": i.key, "ten": i.name, "bat_buoc": i.required, "trang_thai": i.status,
                       "can_kiem_lai": i.needs_recheck, "nguoi_kiem": i.reviewed_by, "ghi_chu": i.note,
                       "tai_lieu_id": i.current_document_id} for i in items],
        "tai_lieu": [{"id": d.id, "muc_id": d.checklist_item_id, "version": d.version, "ten_tep": d.file_name,
                      "dung_luong": d.size_bytes, "sha256": d.checksum[:16], "nguoi_tai": d.uploaded_by,
                      "luc": d.uploaded_at, "da_thay_the": bool(d.superseded_by)} for d in docs],
        "ngoai_le": [{"id": w.id, "muc_id": w.checklist_item_id, "ly_do": w.reason, "nguoi_de_nghi": w.requested_by,
                      "quyet_dinh": w.decision, "nguoi_quyet": w.decided_by, "ghi_chu": w.decision_note}
                     for w in db.execute(select(VisaWaiver).where(VisaWaiver.case_id == c.id)).scalars()],
        "cong_viec": [{"id": t.id, "loai": t.kind, "tieu_de": t.title, "nguoi_nhan": names.get(t.assignee_user_id, ""),
                       "trang_thai": t.status, "han": t.due_at, "ly_do_cho": t.waiting_reason,
                       "qua_han": bool(t.due_at and t.due_at < _now() and t.status in ("open", "doing"))}
                      for t in db.execute(select(VisaTask).where(VisaTask.case_id == c.id).order_by(VisaTask.id)).scalars()],
        "khai_ho_so": [{"id": a.id, "ma_tham_chieu": a.reference_code, "cong": a.portal,
                        "nguoi_khai": a.submitted_by, "luc": a.submitted_at, "bang_chung": a.evidence}
                       for a in db.execute(select(VisaApplication).where(VisaApplication.case_id == c.id)).scalars()],
        "lich_hen": [{"id": a.id, "luc": a.starts_at, "mui_gio": a.timezone, "dia_diem": a.location,
                      "trang_thai": a.status, "sinh_trac_hoc": a.biometrics_done, "thay_cho_id": a.replaces_id,
                      "ly_do_doi": a.reschedule_reason, "nguoi_lap": a.created_by}
                     for a in db.execute(select(VisaAppointment).where(VisaAppointment.case_id == c.id)
                                         .order_by(VisaAppointment.id)).scalars()],
        "ket_qua": [{"id": r.id, "ket_qua": r.outcome, "ngay_nhan": r.received_on, "tu_ngay": r.visa_valid_from,
                     "den_ngay": r.visa_valid_to, "so_lan_nhap_canh": r.entries, "ly_do_tu_choi": r.refusal_reason,
                     "nguoi_nhap": r.recorded_by}
                    for r in db.execute(select(VisaResult).where(VisaResult.case_id == c.id)).scalars()],
        "ban_giao": [{"id": h.id, "chieu": h.direction, "loai": h.item_type, "so_luong": h.quantity,
                      "ben_giao": h.from_party, "ben_nhan": h.to_party, "da_xac_nhan": h.confirmed,
                      "luc": h.happened_at, "nguoi_ghi": h.recorded_by}
                     for h in db.execute(select(VisaHandover).where(VisaHandover.case_id == c.id)).scalars()],
        "lien_ket_khach": [{"id": l.id, "quyen": l.scopes, "het_han": l.expires_at, "thu_hoi": l.revoked,
                            "so_lan_dung": l.used_count} for l in
                           db.execute(select(VisaAccessLink).where(VisaAccessLink.case_id == c.id)).scalars()],
    }


def case_audit(db: Session, c: VisaCase, limit: int = 200) -> list[dict]:
    from app.models.core import AuditLog
    rows = db.execute(select(AuditLog).where(AuditLog.entity == f"visa:{c.case_code}")
                      .order_by(AuditLog.id.desc()).limit(limit)).scalars()
    return [{"ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action,
             "before": l.before, "after": l.after} for l in rows]


# ---------- Tình trạng kho lưu trữ ----------

def storage_status(db: Session, sample: int = 40) -> dict:
    """Kho đang dùng có bền vững không, và các tệp đã nộp còn nguyên không.

    Kiểm mẫu chứ không quét toàn bộ: đủ để phát hiện sớm "kho trống mà CSDL vẫn còn bản ghi" – dấu hiệu kinh
    điển của việc đang ghi vào ổ đĩa tạm. Ai đọc số này cũng nên hiểu: `thieu` > 0 nghĩa là tài liệu ĐÃ MẤT."""
    try:
        st = ST.storage()
        info = st.describe()
    except ST.StorageError as ex:
        return {"ok": False, "loi": str(ex), "ben_vung": False}
    total = int(db.execute(select(func.count(VisaDocument.id))).scalar() or 0)
    rows = list(db.execute(select(VisaDocument.id, VisaDocument.storage_path)
                           .order_by(VisaDocument.id.desc()).limit(sample)).all())
    missing = [i for i, key in rows if not key or not st.exists(key)]
    # Hai vấn đề này ĐỘC LẬP nhau và có thể cùng xảy ra, nên liệt kê đủ chứ không chọn một cái để báo:
    # kho không bền vững là chuyện tương lai (deploy tới sẽ mất), tệp thiếu là chuyện đã rồi.
    findings = []
    if not info["durable"]:
        findings.append("Kho hiện KHÔNG bền vững: tài liệu sẽ mất sau lần deploy tới.")
    if missing:
        findings.append(f"Có {len(missing)}/{len(rows)} tài liệu trong mẫu kiểm tra không còn trên kho.")
    return {"ok": bool(info["durable"]) and not missing,
            "ben_vung": info["durable"], "nen": info["kind"], "noi_luu": info["noi_luu"],
            "canh_bao": info["canh_bao"], "tong_tai_lieu": total, "da_kiem": len(rows),
            "thieu": len(missing), "tai_lieu_thieu": missing[:10],
            "ket_luan": " ".join(findings) or "Kho lưu trữ bền vững, mẫu kiểm tra còn đủ tệp."}


# ---------- AI (mục 10) ----------
def ai_suggest(db: Session, u: User, c: VisaCase, agent: str, target: str, payload: dict, source_ref: str = "") -> VisaAiSuggestion:
    """AI chỉ ĐỀ XUẤT. Không tự duyệt tài liệu, ngoại lệ, kết quả hay sinh trắc học; không tự điền chỗ thiếu."""
    if not source_ref:
        raise VisaError("Đề xuất của AI phải kèm tài liệu nguồn / vị trí tham chiếu")
    s = VisaAiSuggestion(case_id=c.id, agent=agent, target=target, payload=payload, source_ref=source_ref)
    db.add(s)
    db.flush()
    _audit(db, u, "visa_ai_de_xuat", c, after={"agent": agent, "target": target, "nguon": source_ref})
    return s


def ai_decide(db: Session, u: User, c: VisaCase, suggestion_id: int, accept: bool) -> VisaAiSuggestion:
    _require(u, REVIEWER_ROLES + ("nv_dh", "nv_visa"), "chấp nhận hoặc bác bỏ đề xuất của AI")
    s = db.get(VisaAiSuggestion, suggestion_id)
    if not s or s.case_id != c.id:
        raise VisaError("Đề xuất không thuộc hồ sơ này")
    if s.state != "NEW":
        raise VisaError("Đề xuất này đã được xử lý")
    s.state = "ACCEPTED" if accept else "REJECTED"
    s.decided_by, s.decided_at = u.username, _now()
    _audit(db, u, "visa_ai_quyet_dinh", c, after={"suggestion_id": s.id, "chap_nhan": accept})
    return s


# ---------- Dữ liệu cấu hình mẫu ----------
UK_CHECKLIST = [
    {"key": "ho_chieu", "ten": "Hộ chiếu gốc còn hạn ≥ 6 tháng", "bat_buoc": True},
    {"key": "anh_the", "ten": "Ảnh thẻ nền trắng 45x35mm", "bat_buoc": True},
    {"key": "cccd", "ten": "Căn cước công dân (2 mặt)", "bat_buoc": True},
    {"key": "ho_khau", "ten": "Giấy tờ cư trú / xác nhận thông tin cư trú", "bat_buoc": False},
    {"key": "chung_minh_cong_viec", "ten": "Giấy tờ chứng minh công việc", "bat_buoc": True},
    {"key": "chung_minh_tai_chinh", "ten": "Giấy tờ chứng minh tài chính", "bat_buoc": True},
    {"key": "lich_trinh", "ten": "Lịch trình chuyến đi và đặt phòng", "bat_buoc": True},
    {"key": "giay_khai_sinh", "ten": "Giấy khai sinh (đương đơn dưới 18 tuổi)", "bat_buoc": True,
     "dieu_kien": {"tuoi_duoi": 18}},
    {"key": "giay_dong_y_cha_me", "ten": "Giấy đồng ý cho đi của cha mẹ (đương đơn dưới 18 tuổi)",
     "bat_buoc": True, "dieu_kien": {"tuoi_duoi": 18}},
]


def seed_visa(db: Session) -> None:
    """Cấu hình khởi tạo: thị trường UK và mẫu checklist UK (mục 1 – phạm vi đầu tiên)."""
    if not db.execute(select(VisaMarket).where(VisaMarket.code == "UK")).scalars().first():
        db.add(VisaMarket(code="UK", name="Vương quốc Anh", requires_biometrics=True, requires_appointment=True,
                          visa_types=[{"code": "UK_STANDARD_VISITOR", "ten": "Standard Visitor"}],
                          sla_hours={"phan_cong": 8, "khai_thong_tin": 48, "khach_xac_nhan": 48,
                                     "thu_thap_tai_lieu": 120, "kiem_tra": 24, "khai_ho_so": 48,
                                     "lich_hen": 72, "sinh_trac_hoc": 24, "theo_doi_ket_qua": 480,
                                     "ban_giao": 72, "duyet_ngoai_le": 12}))
    if not db.execute(select(VisaChecklistTemplate).where(VisaChecklistTemplate.market_code == "UK")).scalars().first():
        db.add(VisaChecklistTemplate(market_code="UK", visa_type="", version=1, items=UK_CHECKLIST))
    db.commit()
