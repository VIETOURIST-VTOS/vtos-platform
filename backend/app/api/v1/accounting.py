"""API kế toán TT99: danh mục TK, chứng từ ghi sổ, sổ cái, cân đối phát sinh, hóa đơn điện tử, khóa kỳ."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import Booking, User
from app.models.accounting import Account, JournalEntry, Invoice, PeriodLock
from app.services import accounting as ACC
from app.services import rules as R_
from app.services import pham_vi_phap_nhan as PV
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["ke-toan"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks", "ptgd_doan", "hcns")


def entry_out(e: JournalEntry) -> dict:
    from app.services import dieu_chinh as _DC
    return {"id": e.id, "code": e.code, "entry_date": e.entry_date, "period": e.period, "description": e.description, "source_type": e.source_type,
            # Đợt E14: hai mốc, cộng con số kiểm toán hỏi — TÍNH LẠI lúc đọc chứ không lưu, vì
            # lưu thì nó đóng băng trong khi hai ngày kia còn sửa được lúc chứng từ chưa ghi sổ.
            "ky_goc": e.ky_goc, "ngay_phat_hien": e.ngay_phat_hien, "so_ngay_de_sua": _DC.so_ngay_de_sua(e),
            "source_ref": e.source_ref, "tour_id": e.tour_id, "status": e.status, "created_by": e.created_by, "posted_by": e.posted_by, "posted_at": e.posted_at,
            "reversed_by_id": e.reversed_by_id, "amount": sum((l.debit or 0) for l in e.lines),
            "lines": [{"id": l.id, "account": l.account_code, "debit": l.debit, "credit": l.credit, "partner": l.partner, "partner_code": l.partner_code, "project_code": l.project_code, "item_code": l.item_code, "bo_phan": l.bo_phan, "doc_no": l.doc_no, "booking_id": l.booking_id, "note": l.note} for l in e.lines]}


def invoice_out(i: Invoice, db: Session) -> dict:
    b = db.get(Booking, i.booking_id) if i.booking_id else None
    return {"id": i.id, "series": i.series, "number": i.number, "no": f"{i.series}-{i.number:07d}" if i.number else "", "issue_date": i.issue_date,
            "booking_id": i.booking_id, "booking_code": b.code if b else "", "tour_code": b.tour.code if b and b.tour else "",
            "customer_name": i.customer_name, "customer_tax_code": i.customer_tax_code, "customer_address": i.customer_address, "description": i.description,
            "pre_tax": i.pre_tax, "vat_rate": i.vat_rate, "vat": i.vat, "total": i.total, "status": i.status, "provider": i.provider, "provider_ref": i.provider_ref,
            "entry_id": i.entry_id, "created_by": i.created_by, "issued_by": i.issued_by, "issued_at": i.issued_at,
            # Đợt E7: màn hình cần biết tờ nào đang treo và treo từ lúc nào, để hiện màu vàng.
            "issue_sent_at": i.issue_sent_at}


@router.get("/accounts")
def accounts(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"code": a.code, "name": a.name, "kind": a.kind, "parent": a.parent, "level": a.level, "is_detail": a.is_detail, "bs_debit": a.bs_debit, "bs_credit": a.bs_credit, "pl_code": a.pl_code, "misa": a.misa}
            for a in db.execute(select(Account).order_by(Account.code)).scalars()]


# ---------- Chứng từ ----------
@router.get("/journal")
def journal(period: str | None = None, status: str | None = None, ky_goc: str | None = None, limit: int = 300, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(JournalEntry).order_by(desc(JournalEntry.entry_date), desc(JournalEntry.id))
    q = PV.loc(q, JournalEntry, u)           # P6: phạm vi pháp nhân của phiên đăng nhập
    if period: q = q.where(JournalEntry.period == period)
    if status: q = q.where(JournalEntry.status == status)
    # Đợt E14: câu thuyết minh BCTC hỏi mỗi lần lập báo cáo — "kỳ 09 bị sửa bởi những bút toán
    # nào". Không có bộ lọc này thì người lập phải đọc từng diễn giải để đoán.
    if ky_goc: q = q.where(JournalEntry.ky_goc == ky_goc)
    return [entry_out(e) for e in db.execute(q.limit(limit)).scalars()]


class LineIn(BaseModel):
    account: str
    debit: float | None = None
    credit: float | None = None
    partner: str = ""
    partner_code: str = ""
    project_code: str = ""
    item_code: str = ""
    bo_phan: str = ""
    doc_no: str = ""
    note: str = ""
    booking_id: int | None = None
    tour_id: int | None = None


class EntryIn(BaseModel):
    entry_date: date
    description: str
    lines: list[LineIn]
    tour_id: int | None = None
    post: bool = False
    # ĐỢT E14 13/10/2026 — Kế toán chọn ĐÂY LÀ BÚT TOÁN GÌ, và nếu là điều chỉnh thì khai hai mốc.
    # Danh sách cho phép hẹp đúng hai giá trị: cửa này là cửa lập tay, nó không được dùng để khai
    # một nghiệp vụ mà hệ thống tự sinh (thu tiền, hóa đơn, lương…) — khai tay một nghiệp vụ máy
    # sinh là dựng một chứng từ không có nghiệp vụ thật nào đứng sau.
    nghiep_vu: str = "but_toan_tay"
    ky_goc: str = ""
    ngay_phat_hien: date | None = None


# BẢNG, không phải bộ: khóa là thứ màn hình gửi lên, giá trị là tên nghiệp vụ được GHI VÀO SỔ.
# Hai thứ ấy hôm nay trùng nhau tứng chữ, nhưng chúng là HAI thứ: một cái là tên ô chọn trên
# màn hình, một cái là mã nằm trong sổ cái. Viết thành bảng thì phép thử `test_e3_3c` đọc được
# giá trị và đối chiếu vỉa `chung_tu_loai.NGHIEP_VU` — một bộ thì nó không đọc được, và cửa này
# truyền BIẾN vào `nghiep_vu=` nên nó phải để người khác đọc được.
NGHIEP_VU_LAP_TAY = {
    "but_toan_tay": "but_toan_tay",
    "dieu_chinh_ky_truoc": "dieu_chinh_ky_truoc",
}


@router.post("/journal", status_code=201)
def create_entry(data: EntryIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    if data.nghiep_vu not in NGHIEP_VU_LAP_TAY:
        raise HTTPException(422, f"Cửa lập tay chỉ nhận {' hoặc '.join(NGHIEP_VU_LAP_TAY)}. "
                                 f"Nghiệp vụ máy sinh phải đi đúng cửa của nó.")
    try:
        e = ACC.post_entry(db, u.username, u.role, data.entry_date, data.description, [l.model_dump() for l in data.lines], "thu_cong", "", data.tour_id, post=data.post, nghiep_vu=NGHIEP_VU_LAP_TAY[data.nghiep_vu],
                           ky_goc=data.ky_goc or None, ngay_phat_hien=data.ngay_phat_hien)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit(); db.refresh(e)
    return {"entry": entry_out(e), "message": f"Đã {'ghi sổ' if data.post else 'lập nháp'} {e.code}"}


@router.post("/journal/{eid}/post")
def post_entry(eid: int, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    e = db.get(JournalEntry, eid)
    if not e: raise HTTPException(404, "Không có chứng từ")
    from app.services import ks_tach_nhiem as _KTN_E2        # Đợt E2a
    _kq = _KTN_E2.kiem(db, f"ky:{e.period}", "ghi_so", u)
    if _kq["chan"]:
        raise HTTPException(422, {"gate": "TACH_NHIEM", "message": (
            _kq["vi_pham"][0]["thong_diep"] if _kq["vi_pham"] else _kq["thong_diep_thieu_ma"])})
    try:
        ACC.post_draft(db, u, e)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    _KTN_E2.ghi_buoc(db, f"ky:{e.period}", "ghi_so", u)
    db.commit()
    return {"message": f"Đã ghi sổ {e.code}"}


class ReasonIn(BaseModel):
    reason: str = ""


@router.post("/journal/{eid}/reverse")
def reverse(eid: int, data: ReasonIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    e = db.get(JournalEntry, eid)
    if not e: raise HTTPException(404, "Không có chứng từ")
    if not data.reason.strip(): raise HTTPException(422, "Phải ghi lý do đảo bút toán")
    try:
        r = ACC.reverse_entry(db, u, e, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"entry": entry_out(r), "message": f"Đã lập chứng từ đảo {r.code}"}


# ---------- Sổ sách ----------
@router.get("/ledger")
def ledger(account: str, period: str | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try:
        return ACC.ledger(db, account, period)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


@router.get("/trial-balance")
def trial_balance(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    rows = ACC.trial_balance(db, period)
    tot = {k: sum(r[k] for r in rows) for k in ("open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit")}
    return {"period": period, "rows": rows, "total": tot, "balanced": abs((tot["debit"] or 0) - (tot["credit"] or 0)) < 1 and abs(tot["close_debit"] - tot["close_credit"]) < 1}


# ---------- Hóa đơn điện tử ----------
@router.get("/invoices")
def invoices(status: str | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(Invoice).order_by(desc(Invoice.id))
    if status: q = q.where(Invoice.status == status)
    return [invoice_out(i, db) for i in db.execute(q).scalars()]


class InvoiceIn(BaseModel):
    booking_id: int
    vat_rate: float | None = None
    customer_tax_code: str = ""
    customer_address: str = ""
    description: str = ""


@router.post("/invoices", status_code=201)
def create_invoice(data: InvoiceIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    b = db.get(Booking, data.booking_id)
    if not b: raise HTTPException(404, "Không có booking")
    try:
        inv = ACC.create_invoice(db, u, b, data.vat_rate, data.customer_tax_code, data.customer_address, data.description)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"invoice": invoice_out(inv, db), "message": "Đã lập hóa đơn nháp – kiểm tra rồi phát hành"}


# ĐỢT E7 13/10/2026 — mã việc của MỘT lần bấm. Màn hình sinh một mã cho một lần bấm và gửi kèm;
# bấm hai lần gửi CÙNG một mã, và lần hai nhận lại ĐÚNG kết quả lần một.
class IssueIn(BaseModel):
    ma_viec: str = ""


@router.post("/invoices/{iid}/issue")
def issue(iid: int, data: IssueIn = IssueIn(), u: User = Depends(require_roles("ketoan")),
          db: Session = Depends(get_db)):
    from app.services import hoa_don_so as _HDS
    # CHỐNG GỌI HAI LẦN, vế thứ nhất: mã việc này phát hành rồi thì trả lại ĐÚNG kết quả lần ấy —
    # không phát hành lại, và cũng KHÔNG báo lỗi. Người bấm hai lần không làm gì sai và không cần
    # nhận một câu báo lỗi; họ cần thấy tờ hóa đơn của mình.
    cu = _HDS.tim_theo_ma_viec(db, data.ma_viec)
    if cu:
        return {"invoice": invoice_out(cu, db), "lap_lai": True,
                "message": f"Lần bấm này đã được xử lý rồi — hóa đơn {cu.series}-{cu.number:07d}. "
                           f"Không phát hành thêm tờ nào."}
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "Không có hóa đơn")
    try:
        ACC.issue_invoice(db, u, inv, data.ma_viec)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"invoice": invoice_out(inv, db), "message": f"Đã phát hành {inv.series}-{inv.number:07d}, mã tra cứu {inv.provider_ref}"}


@router.post("/invoices/{iid}/do-lai")
def do_lai_hoa_don(iid: int, u: User = Depends(require_roles("ketoan")),
                   db: Session = Depends(get_db)):
    """Hỏi nhà cung cấp xem tờ đang treo đã ra chưa. KHÔNG gửi lại, chỉ HỎI.

    Cùng vai với cửa phát hành: người phát hành là người đi hỏi. Nằm DƯỚI tiền tố `/invoices` đã
    khai nên PHẠM_VI_ĐÃ_CHỐT không đổi một số nào.
    """
    from app.services import hoa_don_so as _HDS
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "Không có hóa đơn")
    try:
        kq = _HDS.do_lai(db, u, inv)
    except _HDS.SaiPhatHanh as ex:
        raise HTTPException(422, str(ex))
    return {"invoice": invoice_out(inv, db), **kq}


@router.get("/invoices/so-nhay")
def so_nhay(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Sổ số hóa đơn: số cuối đã cấp của từng ký hiệu, và DÃY SỐ CÓ LIÊN TỤC KHÔNG."""
    from app.services import hoa_don_so as _HDS
    return _HDS.bang_so_nhay(db)


@router.post("/invoices/{iid}/cancel")
def cancel(iid: int, data: ReasonIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv: raise HTTPException(404, "Không có hóa đơn")
    if not data.reason.strip(): raise HTTPException(422, "Phải ghi lý do hủy")
    try:
        ACC.cancel_invoice(db, u, inv, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": "Đã hủy hóa đơn" + (" và lập bút toán đảo" if inv.entry_id else "")}


# ---------- Khóa kỳ ----------
@router.get("/periods")
def periods(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    locks = {p.period: p for p in db.execute(select(PeriodLock)).scalars()}
    used = sorted(set(db.execute(select(JournalEntry.period).distinct()).scalars()) | set(locks) | {ACC.period_of(date.today())}, reverse=True)
    return [{"period": p, "locked": p in locks, "locked_by": locks[p].locked_by if p in locks else "", "locked_at": locks[p].locked_at if p in locks else None, "note": locks[p].note if p in locks else ""} for p in used]


class LockIn(BaseModel):
    note: str = ""


@router.post("/periods/{period}/lock")
def lock(period: str, data: LockIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    from app.services import ks_tach_nhiem as _KTN_E2        # Đợt E2a
    _kq = _KTN_E2.kiem(db, f"ky:{period}", "khoa_so_ky", u)
    if _kq["chan"]:
        raise HTTPException(422, {"gate": "TACH_NHIEM", "message": (
            _kq["vi_pham"][0]["thong_diep"] if _kq["vi_pham"] else _kq["thong_diep_thieu_ma"])})
    try:
        ACC.lock_period(db, u, period, data.note)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    _KTN_E2.ghi_buoc(db, f"ky:{period}", "khoa_so_ky", u)
    # Đợt E6: đóng vòng cho mọi đề nghị mở lại đang treo của kỳ này. Gọi Ở ĐÂY chứ không trong
    # `lock_period`: hàm kia là phép khóa kỳ chung, nó không phải biết gì về việc mở lại.
    from app.services import mo_lai_ky as _MLK
    _MLK.danh_dau_da_khoa_lai(db, period, u.username)
    db.commit()
    return {"message": f"Đã khóa kỳ {period}"}


# ── ĐỢT E6 13/10/2026 — MỞ LẠI KỲ ĐÃ KHÓA ────────────────────────────────────────────────────
# Ba cửa nằm DƯỚI tiền tố `/periods` đã khai, không xin tiền tố mới. Vai ở cửa TRÌNH là Kế toán
# trưởng và CNTT; vai ở cửa KÝ không viết tay ở đây mà do `mo_lai_ky.ky` hỏi bảng luật — cửa cho
# vào phòng, trong phòng còn một lần chặn nữa.
class MoLaiIn(BaseModel):
    ly_do: str = ""


@router.get("/periods/mo-lai")
def mo_lai_danh_sach(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Hồ sơ mở lại kỳ: đang chờ ký, đang mở lại, và những lần đã xong."""
    from app.models.mo_lai_ky import MoLaiKy
    from app.services import mo_lai_ky as _MLK
    ds = db.execute(select(MoLaiKy).order_by(MoLaiKy.id.desc())).scalars()
    return [_MLK.dong(d) for d in ds]


@router.post("/periods/{period}/mo-lai")
def de_nghi_mo_lai(period: str, data: MoLaiIn,
                   u: User = Depends(require_roles("ketoan_truong", "cntt")),
                   db: Session = Depends(get_db)):
    """Kế toán trưởng TRÌNH đề nghị mở lại. Cửa này KHÔNG mở gì cả — chỉ lập hồ sơ."""
    from app.services import mo_lai_ky as _MLK
    try:
        d = _MLK.de_nghi(db, u, period, data.ly_do)
    except _MLK.SaiMoLaiKy as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã trình Chủ tịch đề nghị mở lại kỳ {period}.", **_MLK.dong(d)}


@router.post("/periods/mo-lai/{mid}/ky")
def ky_mo_lai(mid: int, u: User = Depends(require_roles("chutich", "cntt")),
              db: Session = Depends(get_db)):
    """Chủ tịch KÝ — và đúng lúc này kỳ mới thật sự mở ra."""
    from app.models.mo_lai_ky import MoLaiKy
    from app.services import mo_lai_ky as _MLK
    d = db.get(MoLaiKy, mid)
    if not d: raise HTTPException(404, "Không có đề nghị này")
    try:
        return _MLK.ky(db, u, d)
    except _MLK.SaiMoLaiKy as ex:
        raise HTTPException(422, str(ex))


@router.post("/periods/mo-lai/{mid}/tu-choi")
def tu_choi_mo_lai(mid: int, data: MoLaiIn, u: User = Depends(require_roles("chutich", "cntt")),
                   db: Session = Depends(get_db)):
    """Từ chối cũng phải có lý do: người trình cần biết sửa gì để trình lại."""
    from app.models.mo_lai_ky import MoLaiKy
    from app.services import mo_lai_ky as _MLK
    d = db.get(MoLaiKy, mid)
    if not d: raise HTTPException(404, "Không có đề nghị này")
    try:
        return _MLK.tu_choi(db, u, d, data.ly_do)
    except _MLK.SaiMoLaiKy as ex:
        raise HTTPException(422, str(ex))


# ---------- BCTC & tờ khai thuế (robot R5/R7) ----------
from fastapi import Response
from app.services import reports as RP


@router.get("/reports/balance-sheet")
def balance_sheet(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.balance_sheet(db, period)


@router.get("/reports/income-statement")
def income_statement(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.income_statement(db, period)


@router.get("/reports/cash-flow")
def cash_flow(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.cash_flow(db, period)


@router.post("/reports/closing-entries/{period}")
def closing(period: str, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        es = RP.closing_entries_draft(db, u, period)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Robot đã lập {len(es)} chứng từ kết chuyển NHÁP kỳ {period} – Kế toán trưởng kiểm tra rồi ghi sổ", "entries": [entry_out(e) for e in es]}


@router.get("/tax/vat")
def vat(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.vat_return(db, period)


@router.get("/tax/pit")
def pit(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return RP.pit_return(db, period)


@router.get("/tax/{kind}/xml")
def tax_xml(kind: str, period: str, u: User = Depends(require_roles("ketoan", "cntt", "tgd")), db: Session = Depends(get_db)):
    ret = RP.vat_return(db, period) if kind == "vat" else RP.pit_return(db, period) if kind == "pit" else None
    if not ret: raise HTTPException(404, "Loại tờ khai: vat / pit")
    R_.audit(db, u.username, u.role, "xuat_xml_to_khai", f"tax:{kind}:{period}", after={"mau": ret["form"]}); db.commit()
    return Response(content=RP.to_xml(ret, tax_code=settings.COMPANY_TAX_CODE, company=settings.COMPANY_NAME), media_type="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="{kind}_{period}.xml"'})


# ---------- MISA ↔ VTOS (định hướng 06/9/2026) ----------
from fastapi import UploadFile, File, Form
from app.services import misa as MISA
from app.services import bctc as BCTC
from app.models.accounting import Partner, Project

MISA_WRITE = ("ketoan", "cntt")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content=content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/misa/trial-balance/preview")
async def misa_tb_preview(file: UploadFile = File(...), u: User = Depends(require_roles(*READ))):
    try: p = MISA.parse_trial_balance(await file.read())
    except ValueError as ex: raise HTTPException(422, str(ex))
    leafs = MISA.leaf_rows(p["rows"])
    return {"period": p["period"], "accounts": len(p["rows"]), "detail_accounts": len(leafs),
            "open_debit": sum(r["open_d"] for r in leafs), "open_credit": sum(r["open_c"] for r in leafs), "close_debit": sum(r["close_d"] for r in leafs), "close_credit": sum(r["close_c"] for r in leafs), "rows": p["rows"]}


@router.post("/misa/opening-balance")
async def misa_opening(file: UploadFile = File(...), objects: UploadFile | None = File(default=None), as_of: date = Form(...), column: str = Form("close"), replace: bool = Form(False),
                       u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try:
        return {"message": "Đã ghi số dư đầu kỳ từ MISA", **MISA.import_opening_balance(db, u, await file.read(), as_of, column, await objects.read() if objects else None, replace)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/kiem-toan-checkpoint")
async def misa_kiem_toan(column: str = Form("close"), replace: bool = Form(False),
                          bo_id: int | None = Form(None),
                          u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    """Chốt sổ theo BCTC đã kiểm toán/soát xét (thay vì số MISA thô) – dùng khi phát hiện số MISA chưa chuẩn.

    Đợt E16: bộ số đến từ một bản ĐÃ KÝ (`/misa/bo-so-kiem-toan`), không còn từ tệp trong kho mã.
    `bo_id` rỗng thì lấy bản đã ký có ngày số liệu mới nhất."""
    try:
        return {"message": "Đã chốt sổ theo BCTC kiểm toán/soát xét", **MISA.import_audited_checkpoint(db, u, column, replace, bo_id)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/partners")
async def misa_partners(file: UploadFile = File(...), kind: str = Form("auto"), u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã nạp danh mục đối tượng", **MISA.import_partners(db, await file.read(), kind)}
    except (ValueError, StopIteration) as ex: raise HTTPException(422, f"Không đọc được tệp danh mục: {ex}")


@router.post("/misa/projects")
async def misa_projects(file: UploadFile = File(...), u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã nạp danh mục công trình", **MISA.import_projects(db, await file.read())}
    except (ValueError, StopIteration) as ex: raise HTTPException(422, f"Không đọc được tệp công trình: {ex}")


@router.post("/misa/journal")
async def misa_journal(file: UploadFile = File(...), date_from: date | None = Form(None), date_to: date | None = Form(None), dry_run: bool = Form(False), limit: int | None = Form(None),
                       u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    try: return {"message": "Đã đọc sổ nhật ký chung" if dry_run else "Đã nạp sổ nhật ký chung MISA", **MISA.import_journal(db, u, await file.read(), date_from, date_to, dry_run, limit)}
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.post("/misa/reconcile")
async def misa_reconcile(file: UploadFile = File(...), column: str = Form("close"), u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    try: return MISA.reconcile(db, await file.read(), column)
    except ValueError as ex: raise HTTPException(422, str(ex))


@router.get("/misa/export/purchases.xlsx")
def misa_export_purchases(date_from: date, date_to: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_purchases(db, date_from, date_to), f"Import_MISA_MuaDichVu_{date_from:%d%m}_{date_to:%d%m%Y}.xlsx")


@router.get("/misa/export/projects.xlsx")
def misa_export_projects(date_from: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_projects(db, date_from), "Import_DanhMuc_CongTrinh_VTOS.xlsx")


@router.get("/misa/export/entries.xlsx")
def misa_export_entries(date_from: date, date_to: date, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return _xlsx(MISA.export_general_entries(db, date_from, date_to), f"Import_MISA_ButToan_{date_from:%d%m}_{date_to:%d%m%Y}.xlsx")


@router.get("/partners")
def partners(q: str = "", kind: str | None = None, limit: int = 30, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return MISA.partner_lookup(db, q, kind, limit)


@router.get("/partners/stats")
def partners_stats(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from sqlalchemy import func
    return {"partners": db.execute(select(func.count()).select_from(Partner)).scalar(), "customers": db.execute(select(func.count()).select_from(Partner).where(Partner.is_customer == True)).scalar(),
            "suppliers": db.execute(select(func.count()).select_from(Partner).where(Partner.is_supplier == True)).scalar(), "projects": db.execute(select(func.count()).select_from(Project)).scalar(),
            "projects_linked": db.execute(select(func.count()).select_from(Project).where(Project.tour_id != None)).scalar(),
            "misa_entries": db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.source_type == "misa")).scalar(),
            "opening_entries": [e.code for e in db.execute(select(JournalEntry).where(JournalEntry.source_type == "so_du_dau_ky", JournalEntry.status == "da_ghi_so")).scalars()]}


@router.get("/projects")
def projects(q: str = "", limit: int = 50, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = select(Project)
    if q: s = s.where((Project.code.ilike(f"%{q}%")) | (Project.name.ilike(f"%{q}%")))
    return [{"code": p.code, "name": p.name, "start_date": p.start_date, "end_date": p.end_date, "status": p.status, "tour_id": p.tour_id, "technical": p.technical} for p in db.execute(s.order_by(Project.code).limit(limit)).scalars()]


@router.get("/reports/bctc")
def bctc_report(upto: date, since: date | None = None, compare_upto: date | None = None,
                tu_ban_da_ky: bool = False, ky: str | None = None, company_id: int | None = None,
                u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Bộ BCTC TT99.

    ĐỢT R1 15/10/2026 — `tu_ban_da_ky=true` đọc BẢN ĐÃ KÝ của kỳ thay vì tính lại từ sổ.

    Vì sao cần cờ này: cửa chốt sổ kiểm toán ghi bút toán theo CHÊNH LỆCH, nên một bút toán đề
    ngày cũ chảy xuôi vào số dư của mọi ngày sau nó. Đo được 15/10/2026: sau khi nạp thêm mốc
    31/12/2025, chỉ tiêu 111 tại 30/06/2026 tụt 500 triệu. Bản đã ký là lát cắt của sổ tại ngày
    lập, và đó mới là con số đã phát hành.

    CHƯA CÓ BẢN NÀO ĐÃ KÝ thì NÉM, không lặng lẽ tính lại từ sổ: người bật cờ này đang hỏi "bản
    đã ký ghi gì", và trả lời bằng một con số tính lại là trả lời sai câu hỏi.
    """
    if tu_ban_da_ky:
        from app.services import bao_cao_da_lap as BBC
        b = BBC.ban_da_ky(db, "bctc", ky, company_id)
        if not b:
            raise HTTPException(404, "Chưa có bản báo cáo nào ĐÃ KÝ"
                                     + (f" cho kỳ {ky}" if ky else "")
                                     + ". Vào thẻ “BCTC TT99” → khung “Bản báo cáo đã lập”, bấm "
                                       "“Lập bản”, rồi “Trình”, rồi nhờ Chủ tịch HĐQT ký.")
        return BBC.du_lieu(b)
    r = BCTC.bctc(db, upto, since, compare_upto); r.pop("detail", None); return r


@router.get("/reports/bctc.xlsx")
def bctc_xlsx(upto: date, since: date | None = None, compare_upto: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    r = BCTC.bctc(db, upto, since, compare_upto)
    R_.audit(db, u.username, u.role, "xuat_bctc_tt99", f"bctc:{upto}", after={"since": str(r["since"])}); db.commit()
    return _xlsx(BCTC.bctc_xlsx(r), f"BCTC_TT99_{upto:%Y%m%d}.xlsx")


@router.get("/reports/vay-341")
def vay_341(upto: date, since: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    since = since or date(upto.year, 1, 1)
    return BCTC.loan_bank_detail_341(db, since, upto)


@router.get("/reports/vay-341.xlsx")
def vay_341_xlsx(upto: date, since: date | None = None, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    since = since or date(upto.year, 1, 1)
    r = BCTC.loan_bank_detail_341(db, since, upto)
    R_.audit(db, u.username, u.role, "xuat_chi_tiet_vay_341", f"vay341:{upto}", after={"since": str(since)}); db.commit()
    return _xlsx(BCTC.loan_bank_detail_xlsx(r), f"CHI_TIET_VAY_341_{since:%d%m}_{upto:%d%m%Y}.xlsx")


# ══ ĐỢT E16 14/10/2026 — BỘ SỐ BCTC KIỂM TOÁN: KẾ TOÁN TẢI LÊN, CHỦ TỊCH KÝ ═══════════════════
#
# Năm cửa, TẤT CẢ dưới tiền tố `/misa` ĐÃ khai trong `MAN_HINH_API["/accounting"]` — không xin
# tiền tố mới, nên PHẠM_VI_ĐÃ_CHỐT không đổi một số nào.
#
# Vai: cửa TẢI LÊN dùng đúng `MISA_WRITE` của chính tệp này (Kế toán + CNTT), như mọi cửa nạp MISA
# khác. Cửa KÝ và TỪ CHỐI cho Chủ tịch + CNTT vào phòng, còn AI ĐƯỢC KÝ thì `bo_so_kiem_toan.ky`
# hỏi bảng luật `chu_ky.VAI_KY_CAN` — hai lần chặn, và lần thứ hai mới là luật.
class BoSoTuChoiIn(BaseModel):
    ly_do: str = ""


@router.get("/misa/bo-so-kiem-toan/mau.xlsx")
def bskt_mau(u: User = Depends(require_roles(*READ))):
    """Mẫu Excel TRỐNG để Kế toán điền theo bản BCTC đã ký."""
    from app.services import bo_so_kiem_toan as BSKT
    return _xlsx(BSKT.mau_excel(), "Mau_bo_so_BCTC_kiem_toan.xlsx")


@router.get("/misa/bo-so-kiem-toan")
def bskt_danh_sach(company_id: int | None = None, u: User = Depends(require_roles(*READ)),
                   db: Session = Depends(get_db)):
    from app.services import bo_so_kiem_toan as BSKT
    ds = BSKT.danh_sach(db, u, company_id)
    dang_dung = BSKT.ban_da_ky(db)
    return {"rows": ds, "dang_dung": BSKT.mot_dong(dang_dung) if dang_dung else None}


@router.get("/misa/bo-so-kiem-toan/{bid}")
def bskt_chi_tiet(bid: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from app.models.bo_so_kiem_toan import BoSoKiemToan
    from app.services import bo_so_kiem_toan as BSKT
    b = db.get(BoSoKiemToan, bid)
    if not b: raise HTTPException(404, "Không có bộ số này")
    return BSKT.mot_dong(b, day_du=True)


@router.post("/misa/bo-so-kiem-toan")
async def bskt_tai_len(file: UploadFile = File(...), as_of: date = Form(...), ky: str = Form(""),
                       don_vi_kiem_toan: str = Form(""), so_bao_cao: str = Form(""),
                       ngay_bao_cao: date | None = Form(None), loai_bao_cao: str = Form("soat_xet"),
                       company_id: int | None = Form(None), ghi_chu: str = Form(""),
                       u: User = Depends(require_roles(*MISA_WRITE)), db: Session = Depends(get_db)):
    """Kế toán tải một bản bộ số lên. KHÔNG chốt sổ gì cả — chỉ lập hồ sơ, chờ Chủ tịch ký."""
    from app.services import bo_so_kiem_toan as BSKT
    try:
        b = BSKT.tai_len(db, u, await file.read(), file.filename or "", as_of, ky,
                         don_vi_kiem_toan, so_bao_cao, ngay_bao_cao, loai_bao_cao,
                         company_id, ghi_chu)
    except BSKT.SaiBoSo as ex:
        raise HTTPException(422, str(ex))
    return {"message": "Đã nhận bộ số — chờ Chủ tịch HĐQT ký. Chưa chốt sổ gì cả.",
            **BSKT.mot_dong(b)}


@router.post("/misa/bo-so-kiem-toan/{bid}/ky")
def bskt_ky(bid: int, u: User = Depends(require_roles("chutich", "cntt")),
            db: Session = Depends(get_db)):
    """Chủ tịch KÝ. Bộ số thành dùng được để chốt sổ — nhưng cửa này KHÔNG chốt sổ."""
    from app.models.bo_so_kiem_toan import BoSoKiemToan
    from app.services import bo_so_kiem_toan as BSKT
    b = db.get(BoSoKiemToan, bid)
    if not b: raise HTTPException(404, "Không có bộ số này")
    try:
        return BSKT.ky(db, u, b)
    except BSKT.SaiBoSo as ex:
        raise HTTPException(422, str(ex))


@router.post("/misa/bo-so-kiem-toan/{bid}/tu-choi")
def bskt_tu_choi(bid: int, data: BoSoTuChoiIn, u: User = Depends(require_roles("chutich", "cntt")),
                 db: Session = Depends(get_db)):
    """Từ chối cũng phải có lý do: người tải lên cần biết sửa gì để tải lại."""
    from app.models.bo_so_kiem_toan import BoSoKiemToan
    from app.services import bo_so_kiem_toan as BSKT
    b = db.get(BoSoKiemToan, bid)
    if not b: raise HTTPException(404, "Không có bộ số này")
    try:
        return BSKT.tu_choi(db, u, b, data.ly_do)
    except BSKT.SaiBoSo as ex:
        raise HTTPException(422, str(ex))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R1 15/10/2026 — BẢN BÁO CÁO ĐÃ LẬP
#
# Sáu cửa, đặt dưới tiền tố `/reports/` ĐÃ KHAI nên không đụng tới bảng phân quyền. Vai đọc dùng
# đúng `READ` của chính tệp này; vai lập/trình dùng đúng vai đang được phép xem màn hình Kế toán.
#
# LẬP và LƯU là MỘT bước ở đây (nút "Lập bản" sinh ra một bản `nhap`), còn TRÌNH và KÝ là hai
# bước riêng — đúng hình dáng Đợt E16. Màn hình không có nút nào gộp hai việc ấy lại.
#
# KHÔNG CÓ `ketoan_tt` Ở ĐÂY, và đó là một quyết định chứ không phải một chỗ quên: Đợt E2 chốt
# kế toán thanh toán làm chứng từ thanh toán, công nợ nhà cung cấp, sao kê và phân bổ tiền —
# "không khóa kỳ, không kết chuyển, không đảo bút toán". Lập bộ BCTC của cả pháp nhân là việc
# của Kế toán trưởng. `test_le2b` canh đúng điều này và đã ĐỎ khi em để lọt `ketoan_tt` vào đây.
# ══════════════════════════════════════════════════════════════════════════════════════════════
class BanBaoCaoLapIn(BaseModel):
    loai: str = "bctc"
    loai_ky: str = "tuy_chon"
    ky: str
    tu_ngay: date
    den_ngay: date
    so_sanh_den: date | None = None
    nguoi_dai_dien: str = ""
    ghi_chu: str = ""
    company_id: int | None = None


class BanBaoCaoTuChoiIn(BaseModel):
    ly_do: str


@router.get("/reports/ban-da-lap")
def bbc_danh_sach(loai: str = "bctc", company_id: int | None = None,
                  u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách bản đã lập, đã lọc theo phạm vi pháp nhân của người đang xem."""
    from app.services import bao_cao_da_lap as BBC
    return {"rows": BBC.danh_sach(db, u, loai, company_id)}


@router.get("/reports/ban-da-lap/{bid}")
def bbc_mot_ban(bid: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    from app.models.bao_cao_da_lap import BanBaoCao
    from app.services import bao_cao_da_lap as BBC
    b = db.get(BanBaoCao, bid)
    if not b: raise HTTPException(404, "Không có bản báo cáo này")
    return BBC.mot_ban(b, day_du=True)


@router.post("/reports/ban-da-lap")
def bbc_lap(data: BanBaoCaoLapIn,
            u: User = Depends(require_roles("ketoan", "ketoan_truong", "cntt")),
            db: Session = Depends(get_db)):
    """LẬP = tính bộ báo cáo tại THỜI ĐIỂM NÀY rồi đóng băng. Chưa phải lời khai: bản ở `nhap`."""
    from app.services import bao_cao_da_lap as BBC
    try:
        b = BBC.lap(db, u, loai=data.loai, loai_ky=data.loai_ky, ky=data.ky,
                    tu_ngay=data.tu_ngay, den_ngay=data.den_ngay, so_sanh_den=data.so_sanh_den,
                    nguoi_dai_dien=data.nguoi_dai_dien, ghi_chu=data.ghi_chu,
                    company_id=data.company_id)
    except BBC.SaiBanBaoCao as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã lập bản {b.ky} — {len(b.dong)} chỉ tiêu đã đóng băng. "
                       f"Bấm “Trình” khi muốn chuyển Chủ tịch ký.", "id": b.id}


@router.post("/reports/ban-da-lap/{bid}/trinh")
def bbc_trinh(bid: int,
              u: User = Depends(require_roles("ketoan", "ketoan_truong", "cntt")),
              db: Session = Depends(get_db)):
    from app.models.bao_cao_da_lap import BanBaoCao
    from app.services import bao_cao_da_lap as BBC
    b = db.get(BanBaoCao, bid)
    if not b: raise HTTPException(404, "Không có bản báo cáo này")
    try:
        return BBC.trinh(db, u, b)
    except BBC.SaiBanBaoCao as ex:
        raise HTTPException(422, str(ex))


@router.post("/reports/ban-da-lap/{bid}/ky")
def bbc_ky(bid: int, u: User = Depends(require_roles("chutich", "cntt")),
           db: Session = Depends(get_db)):
    """Chủ tịch KÝ. Từ đây màn hình đọc được SỐ CỦA BẢN thay vì tính lại từ sổ."""
    from app.models.bao_cao_da_lap import BanBaoCao
    from app.services import bao_cao_da_lap as BBC
    b = db.get(BanBaoCao, bid)
    if not b: raise HTTPException(404, "Không có bản báo cáo này")
    try:
        return BBC.ky(db, u, b)
    except BBC.SaiBanBaoCao as ex:
        raise HTTPException(422, str(ex))


@router.post("/reports/ban-da-lap/{bid}/tu-choi")
def bbc_tu_choi(bid: int, data: BanBaoCaoTuChoiIn,
                u: User = Depends(require_roles("chutich", "cntt")),
                db: Session = Depends(get_db)):
    from app.models.bao_cao_da_lap import BanBaoCao
    from app.services import bao_cao_da_lap as BBC
    b = db.get(BanBaoCao, bid)
    if not b: raise HTTPException(404, "Không có bản báo cáo này")
    try:
        return BBC.tu_choi(db, u, b, data.ly_do)
    except BBC.SaiBanBaoCao as ex:
        raise HTTPException(422, str(ex))


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R4c-3 02/11/2026 — MỘT CỬA ĐỌC: BÚT TOÁN ĐÃ GHI VÀO TÀI KHOẢN TIỀN CẤP CHA
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# Chủ tịch chốt 02/11/2026: KHÔNG sửa bút toán cũ. Sổ đã ghi là sổ đã ghi.
#
# Nên cửa này CHỈ ĐỌC — không nút sửa, không nút đảo, không sinh bút toán điều chỉnh. Nó chỉ ra
# CHỖ PHẢI NHÌN để Kế toán trưởng tự quyết từng khoản, đúng lẽ của `cap_dinh_khoan.ngoai_luat`.
#
# Vì sao cần một cửa riêng thay vì đọc `ngoai_luat`: `ngoai_luat` trả về CẶP định khoản đã gộp
# (331/112, bao nhiêu tiền), nó trả lời "cặp nào ngoài luật". Câu Kế toán trưởng hỏi ở đây khác:
# "CHỨNG TỪ NÀO đã ghi tiền ở cấp cha" — từng chứng từ, để đi tìm hồ sơ gốc. Một bảng gộp không
# trả lời được câu ấy.

# DOT TKC-1 06/11/2026 — HANG SO `TIEN_CAP_CHA` DA BO.
#
# No liet ke tay ba tai khoan tien, va mot danh sach go tay thi chi dung bang cai nguoi go nghi
# ra luc ay. Nay cua tu doc bang quan he cha–con cua `Account`, nen no dung ca khi Ke toan them
# mot tieu khoan moi — khong ai phai nho sua mot hang so o day nua.


# DOT DON-R4c3 04/11/2026 — DOI DUONG, KHONG DOI VIEC.
# Ban cu gan duong nay thang vao router `prefix="/api/v1"`, nen duong that la
# `/api/v1/tien-ghi-cap-cha` — MOT NHOM API rieng, khong man hinh nao khai trong
# MAN_HINH_API, nen hang rao `test_p2.test_khong_nhom_api_nao_mo_coi` do va khong vai nao
# cham duoc cua. Nay no nam duoi nhom `/api/v1/accounting`, nhom ma `/ket-so` DA khai san
# va cho den hom nay chua co mot duong nao.
@router.get("/accounting/tien-ghi-cap-cha")
def tien_ghi_cap_cha(tu: date | None = None, den: date | None = None, gioi_han: int = 500,
                     u: User = Depends(require_roles(*READ, mo_ta="bút toán ghi tiền ở cấp cha")),
                     db: Session = Depends(get_db)):
    """Từng dòng sổ có vế tiền là tài khoản CHA. CHỈ ĐỌC."""
    from app.models.accounting import JournalEntry as _JE, JournalLine as _JL

    # ĐỢT TKC-1 06/11/2026 — NỚI TỪ BA TÀI KHOẢN TIỀN RA MỌI TÀI KHOẢN CHA.
    #
    # Vì sao nới: câu Kế toán trưởng phải trả lời là «có chặn ghi vào tài khoản cha hay không»,
    # và câu ấy nói về MỌI tài khoản cha. Cửa cũ soi đúng ba tài khoản tiền (111/112/113), nên nó
    # trả lời một câu hẹp hơn câu được hỏi — mà một con số hẹp hơn câu hỏi thì dễ bị đọc như thể
    # nó là câu trả lời đầy đủ.
    #
    # TỰ ĐI TÌM, KHÔNG GÕ TAY: tài khoản cha là tài khoản được một tài khoản khác khai làm cha.
    # Đọc THẲNG từ bảng `Account` chứ không đọc cờ `is_detail`, vì cờ ấy chỉ được đặt trên đường
    # nạp danh mục MISA; một tài khoản thêm bằng đường khác vẫn mang `is_detail=True` dù nó đã có
    # con. Bảng quan hệ cha–con thì luôn đúng, nên nó là nguồn. (Luật 4 của đợt đo đúng chỗ lệch
    # này và NÓI RA, chứ không lặng lẽ chọn một bên.)
    cac_tk = db.execute(select(Account)).scalars().all()
    ten_tk = {a.code: (a.name or "") for a in cac_tk}
    lam_cha = {a.parent for a in cac_tk if a.parent}
    cha = sorted(c for c in lam_cha if c in ten_tk)
    so_con = {}
    for a in cac_tk:
        if a.parent:
            so_con[a.parent] = so_con.get(a.parent, 0) + 1

    q = (select(_JL, _JE).join(_JE, _JE.id == _JL.entry_id)
         .where(_JL.account_code.in_(cha))
         .order_by(_JE.entry_date.desc(), _JE.id.desc()))
    if tu:
        q = q.where(_JE.entry_date >= tu)
    if den:
        q = q.where(_JE.entry_date <= den)

    het = db.execute(q).all()
    dong = [{
        "chung_tu": e.code, "ngay": str(e.entry_date), "dien_giai": (e.description or "")[:160],
        "tai_khoan": l.account_code, "no": l.debit or 0, "co": l.credit or 0,
        "nguon": e.source_type or "", "trang_thai": e.status or "",
    } for l, e in het[:gioi_han]]

    # Gộp theo tài khoản. Bảng từng chứng từ bị cắt ở `gioi_han`, nên nếu chỉ có bảng ấy thì người
    # đọc sẽ cộng nhẩm một phần rồi tưởng là toàn bộ. Bảng gộp này đếm TRÊN TOÀN BỘ, không cắt.
    gop = {}
    for l, _e in het:
        g = gop.setdefault(l.account_code, {"tai_khoan": l.account_code,
                                            "ten": ten_tk.get(l.account_code, ""),
                                            "so_con": so_con.get(l.account_code, 0),
                                            "so_dong": 0, "no": 0, "co": 0})
        g["so_dong"] += 1
        g["no"] += l.debit or 0
        g["co"] += l.credit or 0
    theo_tk = sorted(gop.values(), key=lambda g: g["no"] + g["co"], reverse=True)
    for g in theo_tk:
        g["no"], g["co"] = round(g["no"], 0), round(g["co"], 0)

    # ĐỢT TKC-2 07/11/2026 — GỘP THEO ĐƯỜNG GHI. Nhịp 1 của ba nhịp Chủ tịch chốt 07/11/2026:
    # ĐO trên dữ liệu thật → NẮN từng đường ghi → mới BẬT CHẶN.
    #
    # Vì sao bảng này phải có, và vì sao bảng «theo tài khoản» ngay trên chưa đủ: bảng kia nói
    # «12 tài khoản cha đang có bút toán», còn nhịp 2 là sửa MÃ của từng đường ghi. Tài khoản
    # không cho biết phải sửa tệp nào; đường ghi thì cho.
    #
    # CỘT `ky_cuoi` LÀ CỘT ĐỂ QUYẾT, không phải để trang trí. Đường ghi còn ghi trong kỳ gần đây
    # thì VẪN ĐANG CHẠY — phải nắn mã trước khi bật chặn, không thì chặn là gãy. Đường ghi có kỳ
    # cuối đã lâu (số dư đầu kỳ, điều chỉnh kiểm toán) thì không còn ghi nữa, nó chỉ để lại SỐ CŨ
    # — và số cũ là việc Kế toán trưởng quyết riêng, không cần sửa một dòng mã nào. Nhờ cột này
    # mà nhịp 2 tự chia thành VIỆC SỬA MÃ và VIỆC DỌN SỐ, hai loại việc khác hẳn nhau.
    #
    # ĐẾM TRÊN TOÀN BỘ, KHÔNG CẮT Ở `gioi_han` — y như bảng theo tài khoản. Bảng từng chứng từ
    # bên dưới mới bị cắt; cộng nhẩm một bảng đã cắt rồi tưởng là toàn bộ chính là chỗ hỏng mà
    # bảng gộp của Đợt TKC-1 sinh ra để chặn.
    from app.services.chung_tu_loai import NGHIEP_VU as _NV
    gop_d = {}
    for l, e in het:
        k = (e.source_type or "", e.loai_nghiep_vu or "")
        g = gop_d.get(k)
        if g is None:
            g = gop_d[k] = {"nguon": k[0], "nghiep_vu": k[1],
                            "ten_nghiep_vu": (_NV.get(k[1]) or ("", ""))[0],
                            "so_dong": 0, "_ct": set(), "_tk": set(), "_ky": set(),
                            "no": 0, "co": 0}
        g["so_dong"] += 1
        g["_ct"].add(e.id)
        g["_tk"].add(l.account_code)
        if e.period:
            g["_ky"].add(e.period)
        g["no"] += l.debit or 0
        g["co"] += l.credit or 0
    theo_duong = []
    for g in gop_d.values():
        ky = sorted(g.pop("_ky"))
        theo_duong.append({**g, "so_chung_tu": len(g.pop("_ct")),
                           "tai_khoan": sorted(g.pop("_tk")),
                           "ky_dau": ky[0] if ky else "", "ky_cuoi": ky[-1] if ky else "",
                           "no": round(g["no"], 0), "co": round(g["co"], 0)})
    theo_duong.sort(key=lambda g: (-g["so_dong"], g["nguon"], g["nghiep_vu"]))

    # Cờ `is_detail` nói gì so với bảng quan hệ cha–con. Hai bên lệch nhau là một chuyện phải nói
    # ra: nó nghĩa là cờ ấy đã cũ, và bất cứ ai sau này viết phép chặn dựa vào cờ sẽ chặn sai chỗ.
    co_sai = sorted(a.code for a in cac_tk
                    if (a.code in lam_cha) != (a.is_detail is False))

    return {
        "tu": str(tu) if tu else None, "den": str(den) if den else None,
        "tai_khoan_cap_cha": cha,
        "so_tai_khoan_cha": len(cha),
        "so_tai_khoan_co_but_toan": len(theo_tk),
        "theo_tai_khoan": theo_tk,
        "theo_duong_ghi": theo_duong,
        "co_is_detail_lech": co_sai,
        "so_dong": len(het), "cat_bot": len(het) > gioi_han, "dong": dong,
        "so_tien": round(sum((l.debit or 0) + (l.credit or 0) for l, _ in het), 0),
        "ghi_chu": ("Mỗi dòng ở đây là tiền đã ghi vào một tài khoản CHA. Nó KHÔNG đương nhiên "
                    "sai số: số tiền đúng, chỉ ghi chưa đủ sâu, nên sổ chi tiết theo từng tài "
                    "khoản con không thấy nó, và phép đối chiếu bảng quy ước xếp nó vào rổ ngoài "
                    "luật. Cửa này CHỈ ĐỌC: không sửa, không đảo. Chủ tịch chốt 02/11/2026 để "
                    "nguyên bút toán cũ, Kế toán trưởng quyết từng khoản."),
    }


# ── ĐỢT R5b-1 02/11/2026 — CỬA ĐỐI CHIẾU LÃI LỖ TOUR: SỔ ↔ BẢNG TÍNH ────────────────────────
#
# Chủ tịch chốt 01/11/2026: *"số từ SỔ là số thật, bảng tính để cạnh để so, có cột lệch"*, và
# *"ghép theo mã tour, và nói ra bên nào thiếu"*. Và chốt thêm: ĐỢT NÀY KHÔNG ĐỔI CHUẨN 09/9 —
# bảng Lãi lỗ tour của Điều hành giữ nguyên quyết toán chi tiết; đây là một thẻ ĐỐI CHIẾU.
#
# ĐƯỜNG PHẢI NẰM DƯỚI `/accounting/` — sửa 06/11/2026, và đây là chỗ bản đầu sai.
#
# Bản 02/11 khai đường ở gốc, tức `/api/v1/` + tên cửa. Bộ định tuyến mang tiền tố `/api/v1`, nên
# đường thật thành MỘT NHÓM API RIÊNG mà không màn hình nào khai trong `MAN_HINH_API` — và lúc ấy
# KHÔNG VAI NÀO CHẠM ĐƯỢC CỬA. Đúng cái bẫy Đợt DỌN-R4c3 đã gỡ cho `tien-ghi-cap-cha` hôm 04/11.
#
# Lời chú cũ ở ngay chỗ này còn viết «không mở bộ định tuyến mới» — viết mà không đo, nên nó trấn
# an người đọc trong khi cửa đã khoá. Phép tự kiểm cũng hỏng theo: nó tìm chữ `APIRouter(` trong
# khối, mà nhóm API đâu có sinh ra từ `APIRouter(` — nó sinh ra từ ĐOẠN ĐẦU CỦA ĐƯỜNG. Một phép
# đo nhắm vào thứ dễ đo thay vì thứ nó nhận là đang đo thì xanh mà không bảo được gì.
#
# Nay cửa nằm dưới nhóm `/api/v1/accounting`, nhóm mà `/ket-so` ĐÃ khai sẵn. Không thêm một dòng
# nào vào `MAN_HINH_API` hay bảng ký quyền.
#
# BỘ VAI: `READ` của phân hệ kế toán, KHÔNG phải `lai_lo_tour.XEM`. Hai bộ ấy khác nhau có chủ ý
# — `lai_lo_tour.XEM` có Điều hành (`tp_dh`, `nv_dh`) vì lãi lỗ chuyến là số của họ; còn bảng
# ĐỐI CHIẾU VỚI SỔ là việc của Kế toán. Mở nó cho Điều hành là bày sổ kế toán ra một màn hình
# Điều hành, và đó là một quyền chưa ai ký. Chặn nằm ở đây, không ở menu.
#
# CHỈ ĐỌC. Không một đường ghi nào: đối chiếu là để NÓI RA chênh lệch, không để sửa cho khớp.
# Sửa bên nào cũng là đổi số liệu qua một cửa không có bộ kiểm — và sửa bên SỔ thì còn là ghi sổ
# không qua chứng từ.


@router.get("/accounting/doi-chieu-lai-lo")
def doi_chieu_lai_lo(tu: date, den: date, gioi_han: int = 500,
                     u: User = Depends(require_roles(*READ, mo_ta="đối chiếu lãi lỗ tour")),
                     db: Session = Depends(get_db)):
    """Bảng đối chiếu lãi lỗ tour: SỔ ↔ BẢNG TÍNH, ghép theo mã tour, có cột lệch.

    Lệch chỉ tính khi CÓ CẢ HAI BÊN; thiếu một bên là "chưa so được", một trạng thái thứ ba
    khác hẳn "khớp" và "lệch".
    """
    from app.services import doi_chieu_lai_lo as DCL
    if den < tu:
        raise HTTPException(422, "Ngày đến phải sau ngày từ")
    return DCL.doi_chieu(db, tu, den, gioi_han)
