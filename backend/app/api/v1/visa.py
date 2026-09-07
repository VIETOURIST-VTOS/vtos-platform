"""API phân hệ Visa (Điều hành ▸ Visa).

Quy ước: mọi thao tác đổi bước đi qua endpoint hành động riêng, KHÔNG có đường nào nhận thẳng `current_stage`.
Quyền được kiểm ở backend theo công ty và hồ sơ, kể cả khi gọi trực tiếp bằng đường dẫn hay tải tệp.
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles, current_user
from app.models.core import User
from app.models.visa import (VisaMarket, VisaChecklistTemplate, VisaFamilyGroup, VisaDocument, VisaCase,
                             STAGES, LIFECYCLE, RESULTS, SERVICE_MODES, DOC_STATUS, TASK_STATUS)
from app.services import visa as VS
from app.services import visa_finance as VF

# Lưu ý: phân hệ Nhân sự đã chiếm sẵn ĐÚNG ba đường "/api/v1/visa", "/api/v1/visa" (POST) và
# "/api/v1/visa/{vid}/complete" cho quỹ visa (thù lao người xử lý). Mọi đường của phân hệ này đều nằm sâu hơn
# một cấp (/visa/ho-so, /visa/danh-muc…) nên không đè lên nhau – test_visa kiểm tra điều đó bằng bảng định tuyến.
router = APIRouter(prefix="/api/v1/visa", tags=["visa"])

# Ai được vào phân hệ Visa. Kế toán và Ban Kiểm soát chỉ đọc phần cần cho nghiệp vụ của họ (mục 9);
# Ban Kiểm soát còn bị chặn ghi ở tầng deps.current_user nên không cần liệt kê lại ở đây.
READ = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "gd_kd", "tp_kd", "tn_kd", "nv_kd",
        "ketoan", "cntt", "bks", "hcns")
WRITE = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "cntt")


def _fail(ex: VS.VisaError):
    return HTTPException(422, str(ex))


def _case(db: Session, u: User, case_id: int) -> VisaCase:
    try:
        return VS.ensure_see(u, VS.get_case(db, case_id))
    except VS.VisaError as ex:
        raise HTTPException(404 if "Không có hồ sơ" in str(ex) else 403, str(ex))


def _run(db: Session, fn, *a, **k):
    try:
        out = fn(*a, **k)
        db.commit()
        return out
    except VS.VisaError as ex:
        db.rollback()
        raise _fail(ex)


# ---------- Danh mục ----------
@router.get("/danh-muc")
def catalog(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Từ điển để giao diện dựng bộ lọc và nhãn – không hardcode ở frontend."""
    return {"stages": STAGES, "lifecycle": LIFECYCLE, "results": RESULTS, "service_modes": SERVICE_MODES,
            "doc_status": DOC_STATUS, "task_status": TASK_STATUS,
            "markets": [{"code": m.code, "name": m.name, "visa_types": m.visa_types,
                         "requires_biometrics": m.requires_biometrics,
                         "requires_appointment": m.requires_appointment,
                         "stages": VS.stages_for(m), "active": m.active}
                        for m in db.execute(select(VisaMarket).order_by(VisaMarket.code)).scalars()]}


class MarketIn(BaseModel):
    code: str
    name: str
    visa_types: list = []
    requires_biometrics: bool = True
    requires_appointment: bool = True
    skip_stages: list[str] = []
    sla_hours: dict = {}
    active: bool = True


@router.post("/thi-truong", status_code=201)
def upsert_market(data: MarketIn, u: User = Depends(require_roles("chutich", "tgd", "tp_dh", "cntt")),
                  db: Session = Depends(get_db)):
    """Thêm/sửa thị trường bằng CẤU HÌNH – không sao chép cứng quy trình UK cho thị trường khác."""
    m = db.execute(select(VisaMarket).where(VisaMarket.code == data.code.upper())).scalar_one_or_none()
    if not m:
        m = VisaMarket(code=data.code.upper())
        db.add(m)
    for k, v in data.model_dump().items():
        if k != "code":
            setattr(m, k, v)
    db.commit()
    return {"code": m.code, "stages": VS.stages_for(m)}


class TemplateIn(BaseModel):
    market_code: str
    visa_type: str = ""
    items: list


@router.post("/checklist-mau", status_code=201)
def add_template(data: TemplateIn, u: User = Depends(require_roles("chutich", "tgd", "tp_dh", "cntt")),
                 db: Session = Depends(get_db)):
    """Mẫu mới luôn là PHIÊN BẢN mới; mẫu cũ giữ lại để truy vết hồ sơ đã dùng nó."""
    old = VS.active_template(db, data.market_code, data.visa_type)
    for t in db.execute(select(VisaChecklistTemplate)
                        .where(VisaChecklistTemplate.market_code == data.market_code.upper(),
                               VisaChecklistTemplate.visa_type == data.visa_type)).scalars():
        t.active = False
    t = VisaChecklistTemplate(market_code=data.market_code.upper(), visa_type=data.visa_type,
                              version=(old.version + 1 if old else 1), items=data.items)
    db.add(t)
    db.commit()
    return {"id": t.id, "version": t.version, "so_muc": len(t.items or [])}


# ---------- Hồ sơ ----------
class CaseIn(BaseModel):
    applicant_name: str
    market_code: str
    company_id: int | None = None
    company_code: str = ""      # tiện dụng: nhập mã pháp nhân thay cho id
    applicant_dob: date | None = None
    applicant_phone: str = ""
    applicant_email: str = ""
    passport_last4: str = ""
    passport_expiry: date | None = None
    booking_id: int | None = None
    tour_id: int | None = None
    family_group_id: int | None = None
    family_role: str = ""
    visa_type: str = ""
    service_mode: str = ""
    departure_date: date | None = None
    return_date: date | None = None
    sales_user_id: int | None = None
    source_system: str = ""
    source_record_id: str = ""
    is_test: bool = False
    note: str = ""
    on_duplicate: str = "block"      # block / open_existing / resubmit / independent


@router.get("/ho-so")
def list_cases(q: str = "", market_code: str = "", company_id: int | None = None, stage: str = "",
               lifecycle_status: str = "", result_status: str = "", service_mode: str = "",
               visa_owner_user_id: int | None = None, sales_user_id: int | None = None,
               since: date | None = None, upto: date | None = None, include_test: bool = False,
               limit: int = 200, offset: int = 0,
               u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return VS.list_cases(db, u, {"q": q, "market_code": market_code, "company_id": company_id,
                                 "stage": stage, "lifecycle_status": lifecycle_status,
                                 "result_status": result_status, "service_mode": service_mode,
                                 "visa_owner_user_id": visa_owner_user_id, "sales_user_id": sales_user_id,
                                 "since": since, "upto": upto, "include_test": include_test},
                         min(limit, 500), offset)


@router.get("/tong-quan")
def dashboard(market_code: str = "", company_id: int | None = None, include_test: bool = False,
              u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return VS.dashboard(db, u, {"market_code": market_code, "company_id": company_id,
                                "include_test": include_test})


@router.post("/ho-so", status_code=201)
def create_case(data: CaseIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    d = data.model_dump()
    on_dup = d.pop("on_duplicate")
    c = _run(db, VS.create_case, db, u, d, on_dup)
    return VS.case_detail(db, u, c)


@router.get("/ho-so/{case_id}")
def case_detail(case_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return VS.case_detail(db, u, _case(db, u, case_id))


@router.get("/ho-so/{case_id}/nhat-ky")
def case_audit(case_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return VS.case_audit(db, _case(db, u, case_id))


class CasePatch(BaseModel):
    row_version: int                          # bắt buộc – chống ghi đè âm thầm (mục 12)
    applicant_phone: str | None = None
    applicant_email: str | None = None
    applicant_dob: date | None = None
    passport_last4: str | None = None
    passport_expiry: date | None = None
    visa_type: str | None = None
    departure_date: date | None = None
    return_date: date | None = None
    booking_id: int | None = None
    tour_id: int | None = None


@router.patch("/ho-so/{case_id}")
def edit_case(case_id: int, data: CasePatch, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    if data.row_version != c.row_version:
        raise HTTPException(409, f"Hồ sơ đã được người khác cập nhật (bản {c.row_version}) – tải lại rồi sửa tiếp")
    before = {"visa_type": c.visa_type, "departure_date": str(c.departure_date)}
    for k, v in data.model_dump(exclude={"row_version"}).items():
        if v is not None:
            setattr(c, k, v)
    c.row_version += 1
    VS._audit(db, u, "visa_sua_ho_so", c, before=before, after={"visa_type": c.visa_type,
                                                               "departure_date": str(c.departure_date)})
    db.commit()
    return VS.case_detail(db, u, c)


class AssignIn(BaseModel):
    visa_owner_user_id: int | None = None
    supervisor_user_id: int | None = None
    sales_user_id: int | None = None


@router.post("/ho-so/{case_id}/phan-cong")
def assign(case_id: int, data: AssignIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.assign, db, u, c, data.visa_owner_user_id, data.supervisor_user_id, data.sales_user_id)
    return VS.case_detail(db, u, c)


# ---------- Form ----------
class FormIn(BaseModel):
    data: dict


@router.post("/ho-so/{case_id}/form", status_code=201)
def save_form(case_id: int, body: FormIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    v = _run(db, VS.save_form, db, u, c, body.data)
    return {"id": v.id, "version": v.version, "state": v.state, "truong_doi": v.changed_fields,
            "can_xac_nhan_lai": v.critical_changed}


@router.post("/ho-so/{case_id}/form/{version_id}/gui-khach")
def send_form(case_id: int, version_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    v = _run(db, VS.send_form, db, u, c, version_id)
    return {"id": v.id, "version": v.version, "state": v.state}


class ConfirmIn(BaseModel):
    form_version_id: int
    confirmed_by_name: str
    channel: str = "link"
    evidence: str = ""


@router.post("/ho-so/{case_id}/xac-nhan-form", status_code=201)
def confirm_form(case_id: int, body: ConfirmIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    cf = _run(db, VS.confirm_form, db, u, c, body.form_version_id, body.confirmed_by_name,
              body.channel, body.evidence)
    return {"id": cf.id, "form_version_id": cf.form_version_id, "luc": cf.confirmed_at}


# ---------- Checklist & tài liệu ----------
@router.post("/ho-so/{case_id}/dong-bo-checklist")
def resync(case_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    return _run(db, VS.resync_checklist, db, u, c)


@router.post("/ho-so/{case_id}/tai-lieu", status_code=201)
async def upload_document(case_id: int, file: UploadFile = File(...), checklist_item_id: int | None = Form(None),
                          u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    doc = _run(db, VS.add_document, db, u, c, checklist_item_id, await file.read(),
               file.filename or "", file.content_type or "")
    return {"id": doc.id, "version": doc.version, "sha256": doc.checksum, "dung_luong": doc.size_bytes}


@router.get("/luu-tru")
def storage_status(u: User = Depends(require_roles("chutich", "tgd", "tp_dh", "cntt", "bks")),
                   db: Session = Depends(get_db)):
    """Kho lưu tài liệu đang dùng có bền vững không, và các tệp đã nộp còn nguyên không.

    Để mở đầu mỗi ngày làm việc mà biết ngay: nếu "ben_vung" là false thì tuyệt đối chưa cho khách nộp
    hộ chiếu thật lên, vì lần deploy tới là mất."""
    return VS.storage_status(db)


@router.get("/tai-lieu/{doc_id}/tep")
def download_document(doc_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Tải tệp cũng phải qua kiểm quyền theo hồ sơ – không có đường vòng bằng id tài liệu."""
    doc = db.get(VisaDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Không có tài liệu này")
    _case(db, u, doc.case_id)
    from app.services import storage as ST
    try:
        data = ST.get_document(doc.storage_path, doc.checksum)
    except ST.StorageError as ex:
        # 410: tệp từng có nhưng nay không lấy được. Nói rõ để người dùng biết phải xin khách nộp lại,
        # thay vì tưởng hệ thống lỗi vặt rồi bấm lại mãi.
        raise HTTPException(410, f"Không lấy được tệp này. {ex}")
    return Response(content=data, media_type=doc.content_type or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'})


class ReviewIn(BaseModel):
    decision: str            # ACCEPTED / NEEDS_REPLACEMENT
    reason: str = ""


@router.post("/ho-so/{case_id}/tai-lieu/{doc_id}/kiem-tra", status_code=201)
def review_document(case_id: int, doc_id: int, body: ReviewIn,
                    u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    rv = _run(db, VS.review_document, db, u, c, doc_id, body.decision, body.reason)
    return {"id": rv.id, "quyet_dinh": rv.decision, "nguoi_kiem": rv.reviewer}


class WaiverIn(BaseModel):
    checklist_item_id: int
    reason: str


@router.post("/ho-so/{case_id}/ngoai-le", status_code=201)
def request_waiver(case_id: int, body: WaiverIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    w = _run(db, VS.request_waiver, db, u, c, body.checklist_item_id, body.reason)
    return {"id": w.id, "quyet_dinh": w.decision}


class WaiverDecideIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/ho-so/{case_id}/ngoai-le/{waiver_id}/quyet-dinh")
def decide_waiver(case_id: int, waiver_id: int, body: WaiverDecideIn,
                  u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    w = _run(db, VS.decide_waiver, db, u, c, waiver_id, body.approve, body.note)
    return {"id": w.id, "quyet_dinh": w.decision, "nguoi_quyet": w.decided_by}


# ---------- Chuyển bước ----------
@router.post("/ho-so/{case_id}/gui-kiem-tra")
def submit_for_review(case_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.submit_for_review, db, u, c)
    return {"giai_doan": c.current_stage}


@router.post("/ho-so/{case_id}/kiem-tra-dat")
def pass_review(case_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.pass_review, db, u, c)
    return {"giai_doan": c.current_stage}


class ApplicationIn(BaseModel):
    reference_code: str
    portal: str = ""
    evidence: str = ""
    note: str = ""


@router.post("/ho-so/{case_id}/khai-ho-so", status_code=201)
def record_application(case_id: int, body: ApplicationIn, u: User = Depends(require_roles(*WRITE)),
                       db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    a = _run(db, VS.record_application, db, u, c, body.reference_code, body.portal, body.evidence, body.note)
    return {"id": a.id, "ma_tham_chieu": a.reference_code, "giai_doan": c.current_stage}


class AppointmentIn(BaseModel):
    starts_at: datetime
    location: str = ""
    timezone: str = "Asia/Ho_Chi_Minh"
    escort: str = ""
    confirmation_ref: str = ""


@router.post("/ho-so/{case_id}/lich-hen", status_code=201)
def set_appointment(case_id: int, body: AppointmentIn, u: User = Depends(require_roles(*WRITE)),
                    db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    ap = _run(db, VS.set_appointment, db, u, c, body.starts_at, body.location, body.timezone,
              body.escort, body.confirmation_ref)
    return {"id": ap.id, "luc": ap.starts_at, "giai_doan": c.current_stage}


class RescheduleIn(BaseModel):
    starts_at: datetime
    reason: str
    location: str = ""
    timezone: str = ""


@router.post("/ho-so/{case_id}/lich-hen/{appointment_id}/doi-lich", status_code=201)
def reschedule(case_id: int, appointment_id: int, body: RescheduleIn,
               u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    ap = _run(db, VS.reschedule, db, u, c, appointment_id, body.starts_at, body.reason,
              body.location, body.timezone)
    return {"id": ap.id, "thay_cho_id": ap.replaces_id, "luc": ap.starts_at}


class BiometricsIn(BaseModel):
    attended: bool
    note: str = ""


@router.post("/ho-so/{case_id}/lich-hen/{appointment_id}/sinh-trac-hoc")
def record_biometrics(case_id: int, appointment_id: int, body: BiometricsIn,
                      u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    ap = _run(db, VS.record_biometrics, db, u, c, appointment_id, body.attended, body.note)
    return {"id": ap.id, "trang_thai": ap.status, "giai_doan": c.current_stage}


class ResultIn(BaseModel):
    outcome: str
    received_on: date
    evidence: str = ""
    visa_valid_from: date | None = None
    visa_valid_to: date | None = None
    entries: str = ""
    refusal_reason: str = ""


@router.post("/ho-so/{case_id}/ket-qua", status_code=201)
def record_result(case_id: int, body: ResultIn, u: User = Depends(require_roles(*WRITE)),
                  db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    r = _run(db, VS.record_result, db, u, c, body.outcome, body.received_on, body.evidence,
             body.visa_valid_from, body.visa_valid_to, body.entries, body.refusal_reason)
    return {"id": r.id, "ket_qua": r.outcome, "giai_doan": c.current_stage}


class HandoverIn(BaseModel):
    direction: str            # NHAN_TU_KHACH / TRA_KHACH / GUI_DOI_TAC / NHAN_DOI_TAC
    item_type: str
    to_party: str = ""
    from_party: str = ""
    quantity: int = 1
    method: str = ""
    confirmed: bool = False
    evidence: str = ""
    note: str = ""


@router.post("/ho-so/{case_id}/ban-giao", status_code=201)
def record_handover(case_id: int, body: HandoverIn, u: User = Depends(require_roles(*WRITE)),
                    db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    h = _run(db, VS.record_handover, db, u, c, body.direction, body.item_type, body.to_party,
             body.from_party, body.quantity, body.method, body.confirmed, body.evidence, body.note)
    return {"id": h.id, "da_xac_nhan": h.confirmed, "giai_doan": c.current_stage}


@router.post("/ho-so/{case_id}/dong-ho-so")
def close_case(case_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.close_case, db, u, c)
    return {"trang_thai": c.lifecycle_status, "giai_doan": c.current_stage}


class ReasonIn(BaseModel):
    reason: str


@router.post("/ho-so/{case_id}/tam-dung")
def hold(case_id: int, body: ReasonIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.hold, db, u, c, body.reason)
    return {"trang_thai": c.lifecycle_status}


@router.post("/ho-so/{case_id}/tiep-tuc")
def resume(case_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.resume, db, u, c)
    return {"trang_thai": c.lifecycle_status}


@router.post("/ho-so/{case_id}/huy")
def cancel(case_id: int, body: ReasonIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    _run(db, VS.cancel, db, u, c, body.reason)
    return {"trang_thai": c.lifecycle_status}


class HrLinkIn(BaseModel):
    hr_visa_file_id: int | None = None       # None = gỡ nối


@router.post("/ho-so/{case_id}/noi-quy-visa")
def link_hr(case_id: int, body: HrLinkIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Nối hồ sơ với bản ghi quỹ visa của phân hệ Nhân sự (bảng visa_files) để khỏi nhập số liệu hai lần.

    Không tự tạo, không tự sửa bản ghi quỹ visa – đó là dữ liệu tính thù lao, thuộc quy tắc của Nhân sự."""
    c = _case(db, u, case_id)
    _run(db, VS.link_hr_visa_file, db, u, c, body.hr_visa_file_id)
    return {"case_code": c.case_code, "hr_visa_file_id": c.hr_visa_file_id}


# ---------- Đợt 4: Tài chính, báo cáo, chuyển dữ liệu ----------

@router.get("/ho-so/{case_id}/thu-chi")
def case_finance(case_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Thu – chi liên quan tới hồ sơ, ĐỌC từ phân hệ Tài chính & Kế toán qua booking. Visa không có sổ riêng."""
    c = _case(db, u, case_id)
    try:
        return VF.finance_for_case(db, u, c)
    except VS.VisaError as ex:
        raise HTTPException(403 if "không được xem" in str(ex) else 422, str(ex))


class WeightIn(BaseModel):
    fee_weight: float | None = None      # None = chia đều


# Đặt trọng số là quyết định TÀI CHÍNH nên Kế toán phải làm được, dù Kế toán không nằm trong nhóm ghi nghiệp
# vụ Visa. Cổng vai trò thật nằm ở VF.MONEY_ROLES trong service; ở đây chỉ mở đủ rộng để service quyết định.
@router.post("/ho-so/{case_id}/trong-so-phi")
def set_weight(case_id: int, body: WeightIn, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Trọng số phân bổ phí gia đình (người lớn 1, trẻ em 0,5…). Để trống là chia đều."""
    c = _case(db, u, case_id)
    try:
        VF.set_fee_weight(db, u, c, body.fee_weight)
        db.commit()
    except VS.VisaError as ex:
        db.rollback()
        raise HTTPException(403 if "không được" in str(ex) else 422, str(ex))
    return {"case_code": c.case_code, "trong_so": c.fee_weight}


@router.get("/doi-chieu-phan-bo/{booking_id}")
def check_allocation(booking_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Nghiệm thu 14: tổng phân bổ của mọi hồ sơ cùng booking phải bằng đúng số của booking."""
    try:
        return VF.check_allocation(db, booking_id)
    except VS.VisaError as ex:
        raise HTTPException(422, str(ex))


@router.get("/bao-cao")
def visa_report(since: date | None = None, upto: date | None = None, market_code: str = "",
                company_id: int | None = None, include_test: bool = False,
                u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Báo cáo Visa: khối lượng, kết quả, thời gian xử lý theo thị trường và chuyên viên.

    Phần tiền chỉ hiện với vai trò được xem cơ cấu tiền – Kinh doanh không thấy giá vốn."""
    return VF.report(db, u, {"since": since, "upto": upto, "market_code": market_code,
                             "company_id": company_id, "include_test": include_test})


@router.post("/nap-visa-portal")
async def import_portal(file: UploadFile = File(...), apply: bool = False,
                        u: User = Depends(require_roles("chutich", "tgd", "tp_dh", "cntt")),
                        db: Session = Depends(get_db)):
    """Chuyển hồ sơ từ Visa Portal. MẶC ĐỊNH chỉ xem trước; ghi thật phải truyền apply=true."""
    try:
        out = VF.import_portal(db, u, await file.read(), file.filename or "", apply)
        if apply:
            db.commit()
        else:
            db.rollback()
        return out
    except VS.VisaError as ex:
        db.rollback()
        raise HTTPException(422, str(ex))


@router.get("/doi-chieu-chuyen-doi")
def reconcile(u: User = Depends(require_roles("chutich", "tgd", "tp_dh", "ketoan", "cntt", "bks")),
              db: Session = Depends(get_db)):
    """Báo cáo đối chiếu sau chuyển đổi: hồ sơ chưa ánh xạ, chưa gắn booking, trùng tên cần rà tay."""
    return VF.reconcile_portal(db)


# ---------- Nhóm gia đình ----------
class GroupIn(BaseModel):
    name: str
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    booking_id: int | None = None
    company_id: int | None = None
    company_code: str = ""
    contact_sees_members: bool = False


@router.post("/nhom-gia-dinh", status_code=201)
def create_group(data: GroupIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    g = _run(db, VS.create_group, db, u, data.model_dump())
    return {"id": g.id, "code": g.code, "name": g.name}


class GroupAddIn(BaseModel):
    case_id: int
    family_role: str = ""
    main: bool = False


@router.post("/nhom-gia-dinh/{group_id}/thanh-vien")
def add_member(group_id: int, body: GroupAddIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    g = db.get(VisaFamilyGroup, group_id)
    if not g:
        raise HTTPException(404, "Không có nhóm này")
    c = _case(db, u, body.case_id)
    _run(db, VS.add_to_group, db, u, g, c, body.family_role, body.main)
    return {"group": g.code, "case_code": c.case_code, "vai_tro": c.family_role}


@router.get("/nhom-gia-dinh/{group_id}/xem-truoc-huy")
def preview_group_cancel(group_id: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Bắt buộc xem danh sách thành viên bị ảnh hưởng trước khi hủy cả nhóm – không xóa hồ sơ để biểu diễn hủy."""
    return {"thanh_vien": VS.cancel_group_preview(db, group_id)}


# ---------- Công việc ----------
class TaskPatch(BaseModel):
    status: str = ""
    waiting_reason: str = ""
    assignee_user_id: int | None = None
    evidence: str = ""


@router.patch("/cong-viec/{task_id}")
def update_task(task_id: int, body: TaskPatch, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    t = _run(db, VS.update_task, db, u, task_id, body.status, body.waiting_reason,
             body.assignee_user_id, body.evidence)
    return {"id": t.id, "trang_thai": t.status, "han": t.due_at}


@router.get("/canh-bao")
def alerts(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Hai loại cảnh báo tách bạch: việc nhân viên quá hạn, và nguy cơ ảnh hưởng ngày đi / lịch hẹn."""
    out = VS.sweep_overdue(db)
    db.commit()
    return out


# ---------- Liên kết khách ----------
class LinkIn(BaseModel):
    scopes: list[str]
    days: int = 14


@router.post("/ho-so/{case_id}/lien-ket-khach", status_code=201)
def issue_link(case_id: int, body: LinkIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Mã thô chỉ trả về ĐÚNG LẦN NÀY; hệ thống và nhật ký chỉ giữ băm nên sau này không tra lại được."""
    c = _case(db, u, case_id)
    link, raw = _run(db, VS.issue_link, db, u, c, body.scopes, body.days)
    return {"id": link.id, "token": raw, "quyen": link.scopes, "het_han": link.expires_at,
            "luu_y": "Gửi cho khách ngay – mã này không hiển thị lại lần thứ hai."}


@router.post("/ho-so/{case_id}/lien-ket-khach/{link_id}/thu-hoi")
def revoke_link(case_id: int, link_id: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    link = _run(db, VS.revoke_link, db, u, c, link_id)
    return {"id": link.id, "thu_hoi": link.revoked}


# ---------- AI ----------
class AiSuggestIn(BaseModel):
    agent: str
    target: str = ""
    payload: dict = {}
    source_ref: str


@router.post("/ho-so/{case_id}/ai/de-xuat", status_code=201)
def ai_suggest(case_id: int, body: AiSuggestIn, u: User = Depends(require_roles(*WRITE)),
               db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    s = _run(db, VS.ai_suggest, db, u, c, body.agent, body.target, body.payload, body.source_ref)
    return {"id": s.id, "trang_thai": s.state}


class AiDecideIn(BaseModel):
    accept: bool


@router.post("/ho-so/{case_id}/ai/de-xuat/{suggestion_id}/quyet-dinh")
def ai_decide(case_id: int, suggestion_id: int, body: AiDecideIn,
              u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = _case(db, u, case_id)
    s = _run(db, VS.ai_decide, db, u, c, suggestion_id, body.accept)
    return {"id": s.id, "trang_thai": s.state, "nguoi_quyet": s.decided_by}
