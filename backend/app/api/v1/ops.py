"""API vận hành: báo cáo ngày (Điều 12), ca trực page, đề nghị chi – lệnh chi (R3), bảng dòng tiền tour."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Tour, User, ROLES
from app.models.hr import Employee
from app.models.ops import DailyReport, PageShift, PaymentRequest, DailyReportVersion, ReportExtraForm
from app.services import ops as O
from app.services import access as AC
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["van-hanh"])
MANAGERS = ("tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "ptgd_mkt", "tgd", "chutich", "hcns", "cntt", "bks")
DEPT_OF_ROLE = {"nv_kd": ("Kinh doanh Lẻ", "Kinh doanh Đoàn"), "nv_dh": ("Điều hành",)}


# ---------- Báo cáo ngày ----------
def report_out(r: DailyReport, users: dict) -> dict:
    u = users.get(r.user_id)
    p2 = O.parse_part2(r.part2_numbers)
    return {"id": r.id, "user_id": r.user_id, "user": u.full_name if u else r.user_id, "department": u.department if u else "", "role": u.role if u else "", "staff_code": u.staff_code if u else "",
            "department_name": O.DEPT_FORMS.get(u.department, {}).get("name", u.department) if u else "",
            "report_date": r.report_date, "part1_done": r.part1_done, "part2_numbers": r.part2_numbers, "part2": p2, "part3_issues": r.part3_issues, "part4_plan": r.part4_plan,
            "submitted_at": r.submitted_at, "on_time": r.on_time, "robot_score": r.robot_score, "robot_note": r.robot_note, "manager_score": r.manager_score,
            "manager_note": r.manager_note, "reviewed_by": r.reviewed_by, "reviewed_at": r.reviewed_at,
            # BC-1
            "first_submitted_at": r.first_submitted_at or r.submitted_at, "so_lan_nop": r.so_lan_nop or 1,
            "vuong_mac_cho": r.vuong_mac_cho or "", "vuong_mac_han": r.vuong_mac_han}


class ReportIn(BaseModel):
    report_date: date
    part1_done: str
    part2_numbers: str | dict = ""      # dict {nhãn: giá trị} theo mẫu phòng (form mới) hoặc văn bản (cũ)
    part3_issues: str = ""              # vướng mắc – đề xuất (Phần 4 của form)
    part4_plan: str                      # việc ngày mai (Phần 3 của form)
    department: str | None = None        # phòng của mẫu (mặc định theo hồ sơ)
    vuong_mac_cho: str = ""              # BC-1: phòng nhận vướng mắc
    vuong_mac_han: date | None = None    # BC-1: cần xong trước ngày


def _ngay_bao_cao(db: Session, u: User, d: date | None) -> date:
    """Ngày báo cáo mặc định: hôm nay giờ VN."""
    return d or O.gio_vn().date()


@router.get("/daily-reports/form")
def report_form(ngay: date | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Mẫu báo cáo của người đăng nhập (BC-1): mẫu chính + kiêm nhiệm, ô số đã giải ra (ngân hàng đọc
    danh mục tài khoản), hạn nộp và số giây còn lại theo GIỜ VIỆT NAM, báo cáo của ngày ấy, các lần
    nộp, và 7 ngày gần nhất."""
    import json
    from datetime import timedelta
    now = O.gio_vn()
    d = _ngay_bao_cao(db, u, ngay)
    mau = O.mau_cua(db, u)
    dept = mau[0]
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    r = db.execute(select(DailyReport).where(DailyReport.user_id == u.id, DailyReport.report_date == d)).scalars().first()
    users = {u.id: u}
    han = O.han_nop(db, d)
    lan = [] if r is None else [{"lan": v.lan, "luc": v.luc} for v in db.execute(
        select(DailyReportVersion).where(DailyReportVersion.report_id == r.id).order_by(DailyReportVersion.lan)).scalars()]
    return {"department": dept, "mau": mau,
            "forms": {k: {"name": v["name"], "fields": O.truong_cua(db, k), "hint": v["hint"],
                          "kiem_nhiem": k in O.MAU_KIEM_NHIEM} for k, v in O.DEPT_FORMS.items()},
            "khoa": {m: {f: O.khoa_o(m, dept, f) for f in O.truong_cua(db, m)} for m in mau},
            "khong_phat_sinh": O.KHONG_PHAT_SINH,
            "full_name": u.full_name, "staff_code": u.staff_code, "ngay": d,
            "deadline": O.han_chu(db, d), "han_luc": han, "bay_gio": now,
            "seconds_left": max(0, int((han - now).total_seconds())),
            "phai_nop": bool(e and O.phai_nop(e)),
            "today": report_out(r, users) if r else None, "lan_nop": lan,
            "bay_ngay": [O.trang_thai_ngay(db, e, u.id, d - timedelta(days=i), now) for i in range(1, 8)],
            "titles": O.PART_TITLES, "gioi_han_tep_mb": GIOI_HAN_TEP_MB}


@router.post("/daily-reports", status_code=201)
def submit(data: ReportIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    import json
    dept = data.department if data.department in O.DEPT_FORMS else O.dept_of_user(db, u)
    p2 = data.part2_numbers if isinstance(data.part2_numbers, dict) else O.parse_part2(data.part2_numbers)
    p2 = {k: str(v or "").strip() for k, v in p2.items()}
    try:
        r = O.submit_report(db, u, data.report_date, data.part1_done, json.dumps(p2, ensure_ascii=False), data.part3_issues, data.part4_plan,
                            vuong_mac_cho=data.vuong_mac_cho, vuong_mac_han=data.vuong_mac_han)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    subject, body = O.mail_text(u, dept, r.report_date, r.part1_done, p2, r.part4_plan, r.part3_issues, u.staff_code)
    dau = r.first_submitted_at or r.submitted_at
    trang = "đúng hạn" if r.on_time else "muộn"
    return {"message": f"Đã nộp báo cáo {r.report_date:%d/%m} lần {r.so_lan_nop or 1} lúc {r.submitted_at:%H:%M:%S} (giờ máy chủ) — "
                       f"lần đầu {dau:%H:%M %d/%m}, {trang}. Điểm nháp robot {r.robot_score:.0f}/10 ({r.robot_note})",
            "report": report_out(r, {u.id: u}), "mail_subject": subject, "mail_body": body}


class PreviewIn(ReportIn):
    pass


@router.post("/daily-reports/preview")
def preview(data: PreviewIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Xem trước 'Nội dung thư' đúng bố cục form Google (không lưu)."""
    dept = data.department if data.department in O.DEPT_FORMS else O.dept_of_user(db, u)
    p2 = data.part2_numbers if isinstance(data.part2_numbers, dict) else O.parse_part2(data.part2_numbers)
    subject, body = O.mail_text(u, dept, data.report_date, data.part1_done, p2, data.part4_plan, data.part3_issues, u.staff_code)
    return {"subject": subject, "body": body, "lines": body.count("\n") + 1}


@router.get("/daily-reports")
def list_reports(period: str | None = None, mine: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db)):
    users = {x.id: x for x in db.execute(select(User)).scalars()}
    q = select(DailyReport).order_by(desc(DailyReport.report_date), DailyReport.user_id)
    if mine or u.role not in MANAGERS:
        q = q.where(DailyReport.user_id == u.id)
    rows = [r for r in db.execute(q.limit(1000)).scalars() if not period or f"{r.report_date:%Y-%m}" == period]
    return [report_out(r, users) for r in rows]


class ReviewIn(BaseModel):
    score: float
    note: str = ""


@router.post("/daily-reports/{rid}/review")
def review(rid: int, data: ReviewIn, u: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    r = db.get(DailyReport, rid)
    if not r: raise HTTPException(404, "Không có báo cáo")
    try:
        O.review_report(db, u, r, data.score, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã chấm {data.score:g}/10"}


@router.get("/daily-reports/summary")
def summary(period: str, u: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    """Tổng hợp tháng theo người: số ngày nộp / ngày làm việc, đúng giờ, điểm bình quân, xếp loại A/B/C/D (nháp – cảnh báo sớm)."""
    y, m = map(int, period.split("-"))
    today = date.today()
    days = O.work_days_in(y, m, until=today if (y, m) == (today.year, today.month) else None)
    users = {x.id: x for x in db.execute(select(User)).scalars()}
    emps = O.nhan_vien_phai_nop(db)   # BC-1: mọi nhân viên văn phòng trừ HDV, tài xế, Ban TGĐ
    reports = [r for r in db.execute(select(DailyReport)).scalars() if f"{r.report_date:%Y-%m}" == period]
    out = []
    for e in emps:
        mine = [r for r in reports if r.user_id == e.user_id]
        grade, avg = O.monthly_grade(mine, len(days))
        out.append({"code": e.code, "name": e.full_name, "department": e.department, "submitted": len(mine), "work_days": len(days), "on_time": sum(1 for r in mine if r.on_time),
                    "reviewed": sum(1 for r in mine if r.reviewed_by), "avg": avg, "grade": grade, "missing": len(days) - len(mine)})
    out.sort(key=lambda r: (-r["avg"], r["name"]))
    return {"period": period, "work_days": len(days), "rows": out}


@router.post("/daily-reports/check-missing")
def check_missing(u: User = Depends(require_roles("cntt", "hcns", "tgd")), db: Session = Depends(get_db)):
    n = O.check_missing_reports(db)
    return {"message": f"Robot đã rà: {n} cảnh báo thiếu báo cáo ngày", "new_alerts": n}


# ---------- BC-1 · Kiêm nhiệm (Chủ tịch giao) ----------
GIOI_HAN_TEP_MB = 8
DOI_TUONG_TEP = "bao_cao_ngay"


@router.get("/daily-reports/kiem-nhiem")
def kiem_nhiem(u: User = Depends(require_roles("chutich")), db: Session = Depends(get_db)):
    """Danh sách nhân viên phải nộp và phần việc kiêm nhiệm đang giao. Chủ tịch giao (26/10/2026)."""
    dang = {}
    for x in db.execute(select(ReportExtraForm).where(ReportExtraForm.active == True)).scalars():   # noqa: E712
        dang.setdefault(x.employee_id, []).append(x.mau)
    return {"mau": [{"ma": k, "ten": v["name"]} for k, v in O.DEPT_FORMS.items()],
            "rows": [{"employee_id": e.id, "code": e.code, "name": e.full_name, "department": e.department,
                      "kiem_nhiem": sorted(dang.get(e.id, []))} for e in sorted(O.nhan_vien_phai_nop(db), key=lambda e: (e.department, e.full_name))]}


class KiemNhiemIn(BaseModel):
    employee_id: int
    mau: str
    bat: bool = True


@router.post("/daily-reports/kiem-nhiem")
def giao_kiem_nhiem(v: KiemNhiemIn, u: User = Depends(require_roles("chutich")), db: Session = Depends(get_db)):
    if v.mau not in O.DEPT_FORMS:
        raise HTTPException(422, "Mẫu không hợp lệ")
    e = db.get(Employee, v.employee_id)
    if e is None:
        raise HTTPException(404, "Không có nhân viên")
    x = db.execute(select(ReportExtraForm).where(ReportExtraForm.employee_id == e.id,
                                                 ReportExtraForm.mau == v.mau)).scalars().first()
    if x is None and v.bat:
        db.add(ReportExtraForm(employee_id=e.id, mau=v.mau, active=True, boi=u.username, luc=datetime.now()))
    elif x is not None:
        x.active, x.boi, x.luc = v.bat, u.username, datetime.now()
    R.audit(db, u.username, u.role, "giao_kiem_nhiem_bao_cao", f"employee:{e.code}", after={"mau": v.mau, "bat": v.bat})
    db.commit()
    return {"message": f"{'Đã giao' if v.bat else 'Đã bỏ'} phần «{O.DEPT_FORMS[v.mau]['name']}» cho {e.full_name}"}


# ---------- BC-1 · Phần 5 — Đính kèm ----------
# Quyền theo HỒ SƠ, không theo vai: tác giả và người quản lý xem được; chỉ tác giả gắn tệp. Kho tệp
# chung xếp các tệp này vào nhóm Nhân sự (dữ liệu cá nhân), nên cửa /tep chung không liệt kê chúng
# ra cho người ngoài.
def _bao_cao_duoc_xem(db: Session, u: User, rid: int) -> DailyReport:
    r = db.get(DailyReport, rid)
    if r is None:
        raise HTTPException(404, "Không có báo cáo")
    if r.user_id != u.id and u.role not in MANAGERS:
        raise HTTPException(403, "Chỉ người nộp và người quản lý xem được tệp của báo cáo này")
    return r


@router.get("/daily-reports/{rid}/tep")
def tep_bao_cao(rid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services import attachments as AT
    _bao_cao_duoc_xem(db, u, rid)
    return AT.danh_sach(db, DOI_TUONG_TEP, str(rid))


@router.post("/daily-reports/{rid}/tep", status_code=201)
async def gan_tep_bao_cao(rid: int, tep: UploadFile = File(...), u: User = Depends(current_user),
                          db: Session = Depends(get_db)):
    from app.services import attachments as AT
    from app.services.storage import StorageError
    r = db.get(DailyReport, rid)
    if r is None:
        raise HTTPException(404, "Không có báo cáo")
    if r.user_id != u.id:
        raise HTTPException(403, "Chỉ người nộp gắn tệp vào báo cáo của mình")
    if r.reviewed_by:
        raise HTTPException(422, "Báo cáo đã được trưởng phòng chấm – không gắn thêm tệp")
    data = await tep.read()
    if len(data) > GIOI_HAN_TEP_MB * 1024 * 1024:
        raise HTTPException(422, f"Tệp nặng {len(data)/1024/1024:.1f} MB — báo cáo ngày nhận tối đa {GIOI_HAN_TEP_MB} MB mỗi tệp.")
    try:
        a, moi = AT.dinh_kem(db, DOI_TUONG_TEP, str(rid), tep.filename or "tep", data, tep.content_type or "",
                             "chung_tu", "", u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    if moi:
        R.audit(db, u.username, u.role, "dinh_kem_bao_cao_ngay", f"report:{rid}", after={"ten_tep": a.ten_tep, "kich_thuoc": a.kich_thuoc})
    db.commit()
    return {**AT.ra(a), "moi": moi, "message": "Đã gắn tệp" if moi else "Tệp này đã có trong báo cáo"}


@router.get("/daily-reports/{rid}/tep/{aid}")
def tai_tep_bao_cao(rid: int, aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    from app.services.storage import StorageError
    _bao_cao_duoc_xem(db, u, rid)
    a = db.get(Attachment, aid)
    if a is None or a.doi_tuong != DOI_TUONG_TEP or a.doi_tuong_id != str(rid) or a.thu_hoi:
        raise HTTPException(404, "Không có tệp này trong báo cáo")
    try:
        data = AT.doc(db, a)
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{a.id}-{a.ten_tep}"'})


# ---------- Ca trực page ----------
@router.get("/page-shifts")
def shifts(period: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows = db.execute(select(PageShift).order_by(desc(PageShift.shift_date), PageShift.slot)).scalars().all()
    return [{"id": s.id, "shift_date": s.shift_date, "slot": s.slot, "employee_id": s.employee_id, "employee": emps.get(s.employee_id, ""), "assigned_by": s.assigned_by,
             "missed": s.missed, "missed_note": s.missed_note, "scanned_at": s.scanned_at, "responded": s.responded, "penalty": O.shift_penalty(s.missed)[0], "kicked": O.shift_penalty(s.missed)[1]}
            for s in rows if not period or f"{s.shift_date:%Y-%m}" == period]


class ShiftIn(BaseModel):
    shift_date: date
    slot: str
    employee_id: int


@router.post("/page-shifts", status_code=201)
def create_shift(data: ShiftIn, u: User = Depends(require_roles("gd_kd", "tp_kd", "cntt")), db: Session = Depends(get_db)):
    if data.slot not in ("sang", "chieu", "toi"): raise HTTPException(422, "Ca: sang / chieu / toi")
    s = PageShift(**data.model_dump(), assigned_by=u.username); db.add(s); db.flush()
    R.audit(db, u.username, u.role, "phan_ca_truc_page", f"shift:{s.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã phân ca"}


class ScanIn(BaseModel):
    missed: int
    note: str = ""


@router.post("/page-shifts/{sid}/scan")
def scan(sid: int, data: ScanIn, u: User = Depends(require_roles("cntt", "gd_kd", "tp_kd")), db: Session = Depends(get_db)):
    """Robot AI quét fanpage (hoặc CNTT nhập) số lượt sót > 5 phút của ca."""
    s = db.get(PageShift, sid)
    if not s: raise HTTPException(404, "Không có ca")
    s.missed, s.missed_note, s.scanned_at = max(0, data.missed), data.note, datetime.now()
    pen, kicked = O.shift_penalty(s.missed)
    R.audit(db, u.username, u.role, "quet_ca_truc_page", f"shift:{s.id}", after={"sot": s.missed, "phat": pen, "loai_ca": kicked}); db.commit()
    return {"message": f"Ca {s.shift_date:%d/%m} {s.slot}: {s.missed} lượt sót → chế tài {pen:,.0f} đ" + (" – loại khỏi ca tháng sau" if kicked else "")}


class RespondIn(BaseModel):
    text: str


@router.post("/page-shifts/{sid}/respond")
def respond(sid: int, data: RespondIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(PageShift, sid)
    if not s: raise HTTPException(404, "Không có ca")
    s.responded = data.text[:300]
    R.audit(db, u.username, u.role, "phan_hoi_ca_truc", f"shift:{s.id}", after={"noi_dung": s.responded}); db.commit()
    return {"message": "Đã ghi phản hồi"}


# ---------- Đề nghị chi – lệnh chi ----------
def pr_out(r: PaymentRequest, db: Session) -> dict:
    t = db.get(Tour, r.tour_id) if r.tour_id else None
    # Dòng "ai bấm tiếp" — phải nói ĐÚNG TÊN người đang được chờ, vì người đọc màn hình sẽ đi gõ
    # đúng người ấy. Marketing từ 23/9/2026 dừng ở một chữ ký của P.TGĐ Marketing; viết "TGĐ duyệt"
    # ở đó là chỉ sai người, và hồ sơ sẽ nằm chờ thêm một vòng vì gõ nhầm cửa.
    # Hỏi CHÍNH hàm mà bước duyệt hỏi. Bản trước suy từ `two_signatures` nên viết "TGĐ" cho mọi
    # khoản trong dự toán, kể cả khoản mà TGĐ không ký được — chỉ sai người, và hồ sơ nằm chờ
    # thêm một vòng vì gõ nhầm cửa, đúng điều ba dòng chú thích ngay trên đã cảnh báo.
    # Đợt F1b: Marketing thôi có nhánh riêng. Bước `cho_duyet` của nó nay là LỆNH CHI, do TGĐ
    # hoặc Chủ tịch ký theo mốc — còn chữ ký nội dung của P.TGĐ Marketing là bước `cho_tp`, và
    # dòng ấy đã do bảng `nxt` ngay dưới nói.
    ai_duyet = O.cap_duyet(db, r)["ai"] or "KHÔNG AI — chưa chốt ngưỡng duyệt chi"
    # Bước MỘT của Marketing là chữ ký nội dung của P.TGĐ Marketing, không phải "bộ phận xác
    # nhận" chung chung (Đợt F1b). Người đọc màn hình đi gõ đúng tên người trên dòng này.
    _buoc1 = ("P.TGĐ Marketing duyệt nội dung" if r.category == "marketing" else "Bộ phận xác nhận")
    nxt = {"cho_tp": _buoc1, "cho_kt": "Kế toán kiểm tra", "cho_duyet": ai_duyet + " ký lệnh chi", "cho_chi": "Kế toán chi trên ngân hàng",
           "da_chi": "Hoàn tất", "tu_choi": "Từ chối"}[r.status]
    return {"id": r.id, "code": r.code, "category": r.category, "tour_id": r.tour_id, "tour_code": t.code if t else "", "supplier_name": r.supplier_name, "supplier_tax_code": r.supplier_tax_code,
            "supplier_bank": r.supplier_bank, "amount": r.amount, "description": r.description, "has_document": r.has_document, "document_ref": r.document_ref, "has_invoice": r.has_invoice,
            "over_budget": r.over_budget, "two_signatures": r.two_signatures, "status": r.status, "next": nxt, "created_by": r.created_by, "created_at": r.created_at, "tp_by": r.tp_by,
            "kt_by": r.kt_by, "approved_by": r.approved_by, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "approved_at": r.approved_at, "reject_reason": r.reject_reason,
            "paid_at": r.paid_at, "paid_ref": r.paid_ref, "paid_method": r.paid_method, "entry_ids": r.entry_ids,
            "marketing_muc": r.marketing_muc, "campaign_id": r.campaign_id,
            # Mốc đã áp cho hồ sơ này. RỖNG = chưa chốt mốc lúc lập (hoặc khoản Marketing, nơi mốc
            # không áp) — màn hình phải hiện "chưa chốt", tuyệt đối không hiện số 0.
            "nguong_duyet_ap_dung": r.nguong_duyet_ap_dung,
            # Vai nào đang ở cấp duyệt của hồ sơ — màn hình ĐỌC ô này chứ không tự suy. Rỗng là
            # KHÔNG AI bấm được lúc này, và màn hình phải nói ra. Xem `services/ops.py::vai_ky_duoc`.
            "vai_ky_duoc": O.vai_ky_duoc(db, r),
            # VPM-17. Rỗng là CHƯA AI NHẬP – màn hình phải hiện "Chưa có hạn", tuyệt đối không hiện
            # ngày lập thay vào đó.
            "ngay_den_han": r.ngay_den_han, "ngay_den_han_boi": r.ngay_den_han_boi,
            "ngay_den_han_luc": r.ngay_den_han_luc,
            # Bốn ô ngoại tệ, 27/9/2026. `tien_te` rỗng = khoản đồng Việt Nam, KHÔNG phải "chưa nhập".
            # `amount` vẫn là cột VND duy nhất mọi màn hình cộng – bốn ô này nói nó từ đâu ra.
            "tien_te": r.tien_te, "so_tien_ngoai_te": r.so_tien_ngoai_te,
            "ty_gia": r.ty_gia, "ngay_ty_gia": r.ngay_ty_gia,
            "ngoai_te_loi_nhan": (f"{r.so_tien_ngoai_te:,.2f} {r.tien_te} × {r.ty_gia:,.2f}"
                                  if r.tien_te and r.so_tien_ngoai_te and r.ty_gia else "")}


@router.get("/payment-requests")
def list_pr(status: str | None = None, tour_id: int | None = None,
            u: User = Depends(require_roles(*AC.PAYMENT_REQUEST_ROLES, "tai_xe", mo_ta="đề nghị chi")),
            db: Session = Depends(get_db)):
    q = select(PaymentRequest).order_by(desc(PaymentRequest.id))
    q = PV.loc(q, PaymentRequest, u)         # P6: phạm vi pháp nhân của phiên đăng nhập
    # Bộ phận ngoài Điều hành chỉ thấy đề nghị MÌNH LẬP. `tai_xe` vào đây 05/10/2026 và đây là dòng
    # giữ cho việc mở cửa ấy không thành mở sổ chi toàn công ty: thiếu nó, một tài xế đăng nhập là
    # đọc được mọi khoản chi của mọi phòng.
    if u.role in ("gd_kd", "tp_kd", "ptgd_mkt", "hcns", "tai_xe"): q = q.where(PaymentRequest.created_by == u.username)
    if status: q = q.where(PaymentRequest.status.in_(status.split(",")))
    if tour_id: q = q.where(PaymentRequest.tour_id == tour_id)
    return [pr_out(r, db) for r in db.execute(q.limit(300)).scalars()]


class PRIn(BaseModel):
    category: str
    tour_id: int | None = None
    supplier_name: str
    supplier_tax_code: str = ""
    supplier_bank: str = ""
    amount: float = 0          # khoản ngoại tệ: để 0, máy nhân ra số VND
    description: str
    has_document: bool = False
    document_ref: str = ""
    has_invoice: bool = False
    # Chỉ dùng cho chi marketing: hạng mục ngân sách và chiến dịch. Có hai ô này thì màn hình ngân sách
    # mới biết hạng mục nào sắp vượt, và chiến dịch mới có chi phí thực tế.
    marketing_muc: str = ""
    campaign_id: int | None = None
    # VPM-17 – ngày đã hẹn trả nhà cung cấp. Để trống được: chưa hẹn được thì đừng đoán, khoản này
    # sẽ nằm ở danh sách còn thiếu ngày cho tới khi người lập quay lại gõ.
    ngay_den_han: date | None = None
    # BỐN Ô NGOẠI TỆ – Chủ tịch chốt 27/9/2026. Để trống cả bốn = khoản đồng Việt Nam (đại đa số).
    # Khai `tien_te` thì phải đủ ba ô còn lại, và `amount` KHÔNG gõ – máy nhân. Kiểm ở
    # `services/ngoai_te_chi.chuan_hoa`.
    tien_te: str = ""
    so_tien_ngoai_te: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None


@router.get("/payment-requests/danh-muc-marketing")
def pr_danh_muc_marketing(u: User = Depends(require_roles(*AC.PAYMENT_REQUEST_ROLES,
                                                          mo_ta="danh mục cho ô chi marketing")),
                          db: Session = Depends(get_db)):
    """Hạng mục ngân sách và danh sách chiến dịch, cho hai ô chọn của phiếu chi marketing.

    CỬA NÀY NẰM DƯỚI TIỀN TỐ CỦA CHÍNH PHÂN HỆ ĐỀ NGHỊ CHI, không phải `/api/v1/marketing`. Màn
    hình `/expenses` khai ba tiền tố (`cashflow`, `payment-requests`, `tours`); thêm
    `/api/v1/marketing` vào đó là nới CẢ NHÓM Marketing — hai mươi mấy cửa, gồm cả ngân sách, nội
    dung và sổ PR — cho mọi vai lập được đề nghị chi, trong đó có `nv_dh` và bốn vai Kinh doanh.
    Đúng cái bẫy đã ghi ở `/api/v1/tong-dai`, `/api/v1/so-con-no` và `/to-chuc-kd`: phần dôi ra vẫn
    là quyền đã cấp.

    Trả về ĐÚNG hai danh mục mà hai ô chọn cần, không trả gì thêm. Danh sách chiến dịch bị cắt theo
    phạm vi pháp nhân của người đang xem, cùng luật với bảng đề nghị chi ngay bên cạnh.
    """
    from app.models.marketing import Campaign, HANG_MUC

    q = select(Campaign).order_by(desc(Campaign.id))
    q = PV.loc(q, Campaign, u)
    return {
        "hang_muc": HANG_MUC,
        "chien_dich": [{"id": c.id, "ma": c.code, "ten": c.name}
                       for c in db.execute(q.limit(300)).scalars()],
        "ghi_chu": "Hai ô này chỉ dùng cho chi marketing. Để trống là CHƯA GẮN – khoản chi vẫn "
                   "lập được, nhưng nó nằm ở phần chưa gắn của bảng hiệu quả chiến dịch, và "
                   "chưa gắn hạng mục thì cổng ngân sách coi là ngoài dự toán.",
    }


@router.post("/payment-requests", status_code=201)
def create_pr(data: PRIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "ptgd_mkt", "hcns", "cntt", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "gd_doi_xe", "tai_xe")), db: Session = Depends(get_db)):
    try:
        r = O.create_request(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, {"gate": "CONG_14", "message": str(ex)} if "cổng 14" in str(ex) else str(ex))
    flags = []
    # Hai lý do KHÁC NHAU cùng dẫn tới hai chữ ký, nên nêu cả hai: vượt dự toán là chuyện của ngân sách,
    # còn vượt hạn mức là chuyện của số tiền. Gộp làm một thì người duyệt không biết mình đang duyệt gì.
    # 23/9/2026 — Marketing tách khỏi mạch này: một chữ ký cho mọi mức tiền (Chủ tịch chốt). Nên với
    # Marketing, "ngoài dự toán" là một lời BÁO chứ không còn là một cấp duyệt, và câu chữ phải nói
    # đúng thế — viết "→ 2 chữ ký" cho một hồ sơ chỉ cần một chữ ký là nói dối người đọc màn hình.
    # Lời báo tỷ giá, 27/9/2026. Sổ tỷ giá là BẢN THAM CHIẾU, không phải quan toà: lệch thì nói ra
    # cho người duyệt biết, KHÔNG chặn và không sửa. Tỷ giá của khoản này là tỷ giá ngày chuyển tiền
    # thật của khoản này – xem `models/ty_gia.py`.
    if r.tien_te:
        from app.services import ngoai_te_chi as NTC
        flags.append(f"{r.so_tien_ngoai_te:,.2f} {r.tien_te} × {r.ty_gia:,.2f} = {r.amount:,.0f}đ")
        so = NTC.doi_chieu_so_ty_gia(db, r.tien_te, r.ngay_ty_gia, r.ty_gia)
        if so["loi_nhan"]: flags.append(so["loi_nhan"])
    # NGOÀI DỰ TOÁN và MỐC TIỀN là hai lý do KHÁC NHAU, nên nói cả hai, mỗi lý do một câu.
    # Câu cũ ở đây viết "≥ hạn mức → 2 chữ ký" cho cờ `two_signatures`, mà cờ ấy nghĩa là
    # NGOÀI DỰ TOÁN — không phải một mốc tiền nào. Nhãn nói sai thì người đọc đi gõ sai người,
    # và lần ấy không ai thấy vì màn hình vẫn có một câu trông hợp lý.
    #
    # ĐỢT F1b — Marketing thôi có nhánh nhãn riêng: nó đi chung mốc, nên nói chung một câu. Riêng
    # lời báo "chưa ai giữ vai P.TGĐ Marketing" thì GIỮ, và ĐỔI CHỖ NÓ ĐỨNG: vai rỗng nay làm hồ
    # sơ đứng ở bước XÁC NHẬN NỘI DUNG, không phải bước duyệt. Lời báo chỉ sai bước là lời báo đẩy
    # người đọc đi tìm nhầm chỗ.
    if r.two_signatures: flags.append("NGOÀI DỰ TOÁN → cần CẢ HAI chữ ký Chủ tịch + TGĐ (cổng 15)")
    elif r.over_budget: flags.append("NGOÀI DỰ TOÁN (cổng 15)")
    if r.category == "marketing" and not O.ai_duyet_duoc_mkt(db):
        flags.append("CHƯA AI GIỮ VAI P.TGĐ MARKETING → hồ sơ này sẽ nằm chờ ngay ở bước xác nhận "
                     "nội dung, không ai bấm được")
    _cd = O.cap_duyet(db, r)
    if _cd["chua_chot"]:
        flags.append("CHƯA CHỐT NGƯỠNG DUYỆT CHI → hồ sơ này sẽ nằm chờ, không ai duyệt được "
                     f"(tham số `{O.NGUONG_CHU_TICH_KEY}`, hai chữ ký)")
    else:
        flags.append(("≥ " if _cd["tren_moc"] else "< ")
                     + f"{_cd['nguong']:,.0f}đ → {_cd['ai']} ký lệnh chi")
    return {"request": pr_out(r, db), "message": f"Đã lập {r.code}" + (" – " + "; ".join(flags) if flags else "")}


class StepIn(BaseModel):
    action: str          # confirm / check / approve / pay / reject
    reason: str = ""


@router.post("/payment-requests/{rid}/step")
def pr_step(rid: int, data: StepIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(PaymentRequest, rid)
    if not r: raise HTTPException(404, "Không có đề nghị chi")
    try:
        msg = O.step(db, u, r, data.action, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg, "request": pr_out(r, db)}


@router.get("/tours/{tid}/cashflow")
def cashflow(tid: int, u: User = Depends(require_roles(*AC.COST_ROLES, mo_ta="dòng tiền tour")), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    cf = O.tour_cashflow(db, t)
    cf["requests"] = [pr_out(r, db) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == tid).order_by(desc(PaymentRequest.id))).scalars()]
    return cf


@router.get("/cashflow")
def cashflow_all(u: User = Depends(require_roles(*MANAGERS, "ketoan", "nv_dh")), db: Session = Depends(get_db)):
    return [O.tour_cashflow(db, t) for t in db.execute(select(Tour).where(Tour.status.in_(["da_duyet", "ket_thuc", "da_dong_so", "kt_xac_nhan"])).order_by(Tour.start_date)).scalars()]


# ══════════════════════════════════════════════════════════════════════════════
# VPM-17 – CỬA NHẬP NGÀY ĐẾN HẠN CHO ĐỀ NGHỊ CHI
#
# Hai cửa, và cả hai đều cần thiết:
#   · cửa SỬA  – ngày hẹn với nhà cung cấp thay đổi là chuyện thường, và hàng nghìn đề nghị chi cũ
#                lập trước 11/9/2026 không có ngày nào cả; không có cửa sửa thì chúng nằm mãi ở rổ
#                "Chưa đủ dữ liệu dự báo" và bảng dòng tiền thiếu đúng phần quá khứ.
#   · cửa ĐẾM  – danh sách khoản CÒN THIẾU ngày. Một con số thiếu mà không ai nhìn thấy thì không ai
#                đi nhập. Danh sách này là việc của người lập, không phải việc của máy đoán hộ.
#
# Vai trò: đúng bảng "Cửa nhập và chủ quản số liệu" mục III.4 của Đề xuất chỉnh sửa giao diện v1.1 —
# dòng "Trả nhà cung cấp" ghi bộ phận nhập là ĐIỀU HÀNH + KẾ TOÁN. Lấy nguyên danh sách vai trò đã
# khai cho việc LẬP đề nghị chi, cộng Kế toán. Lane này không tự nghĩ ra vai trò mới.
# ══════════════════════════════════════════════════════════════════════════════

SUA_NGAY_DEN_HAN = ("nv_dh", "tp_dh", "ptgd_mkt", "hcns", "cntt",
                    "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "ketoan")


class NgayDenHanIn(BaseModel):
    # Cho phép GỠ ngày (gửi rỗng): nhập nhầm thì phải sửa lại được về "chưa biết", chứ không bị kẹt
    # với một ngày sai mà không xoá nổi. Gỡ xong khoản ấy quay lại danh sách còn thiếu — đúng chỗ của nó.
    ngay_den_han: date | None = None
    ly_do: str = ""


@router.put("/payment-requests/{rid}/ngay-den-han")
def dat_ngay_den_han(rid: int, data: NgayDenHanIn,
                     u: User = Depends(require_roles(*SUA_NGAY_DEN_HAN, mo_ta="ngày đến hạn đề nghị chi")),
                     db: Session = Depends(get_db)):
    """Gõ hoặc sửa ngày phải trả của một đề nghị chi."""
    r = db.get(PaymentRequest, rid)
    if not r: raise HTTPException(404, "Không có đề nghị chi")
    # Đã chi xong thì ngày đến hạn là chuyện của quá khứ; sửa nó chỉ làm sai lại một việc đã xong.
    if r.status in ("da_chi", "tu_choi"):
        raise HTTPException(422, f"Đề nghị chi {r.code} đã ở trạng thái “{r.status}” – không đổi ngày đến hạn nữa")
    truoc = r.ngay_den_han
    r.ngay_den_han = data.ngay_den_han
    r.ngay_den_han_boi = u.username if data.ngay_den_han else ""
    r.ngay_den_han_luc = datetime.now() if data.ngay_den_han else None
    R.audit(db, u.username, u.role, "dat_ngay_den_han_de_nghi_chi", f"pr:{r.code}",
            before={"ngay_den_han": str(truoc or "")},
            after={"ngay_den_han": str(data.ngay_den_han or ""), "ly_do": data.ly_do[:200]})
    db.commit()
    if data.ngay_den_han is None:
        return {"ngay_den_han": None,
                "message": f"Đã gỡ ngày đến hạn của {r.code} – khoản này quay lại danh sách chưa có hạn"}
    return {"ngay_den_han": r.ngay_den_han,
            "message": f"{r.code}: hạn trả {data.ngay_den_han:%d/%m/%Y}"}


@router.get("/payment-requests/thieu-ngay-den-han")
def thieu_ngay_den_han(u: User = Depends(require_roles(*AC.PAYMENT_REQUEST_ROLES,
                                                       mo_ta="đề nghị chi thiếu ngày đến hạn")),
                       db: Session = Depends(get_db)):
    """Danh sách việc: đề nghị chi đang chờ chi mà CHƯA ai gõ ngày phải trả.

    Đây là danh sách khiến con số thiếu hiện ra thay vì im lặng. Mỗi dòng ở đây là một khoản tiền
    hệ thống biết là phải trả nhưng không biết trả NGÀY NÀO – nên không xếp được vào cột nào của bảng
    dòng tiền bốn mốc.
    """
    q = select(PaymentRequest).where(
        PaymentRequest.status.in_(("cho_tp", "cho_kt", "cho_duyet", "cho_chi")),
        PaymentRequest.ngay_den_han.is_(None)).order_by(desc(PaymentRequest.amount))
    q = PV.loc(q, PaymentRequest, u)          # P6: phạm vi pháp nhân của phiên đăng nhập
    ds = list(db.execute(q.limit(300)).scalars())
    return {"so_khoan": len(ds),
            "tong_tien": float(round(sum((r.amount or 0) for r in ds))),
            "chi_tiet": [{"id": r.id, "code": r.code, "category": r.category,
                          "supplier_name": r.supplier_name, "amount": r.amount,
                          "description": r.description, "status": r.status,
                          "created_by": r.created_by, "created_at": r.created_at,
                          "tour_id": r.tour_id} for r in ds]}
