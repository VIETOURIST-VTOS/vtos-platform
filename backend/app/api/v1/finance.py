"""API ngân quỹ – tài chính: hợp đồng vay/đầu tư (3.9), lịch thu-trả, dự báo 13 tuần, báo cáo tài chính tuần."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User
from app.models.finance import FinContract, FinSchedule, CashPlanItem, CONTRACT_KINDS
from app.services import finance as F
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["tai-chinh"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks")
WRITE = ("ketoan",)


def c_out(c: FinContract) -> dict:
    return {"id": c.id, "code": c.code, "kind": c.kind, "kind_name": CONTRACT_KINDS.get(c.kind, c.kind), "entity": c.entity, "company_id": c.company_id, "loan_group": c.loan_group, "partner": c.partner, "contract_no": c.contract_no,
            "signed_on": c.signed_on, "principal": c.principal, "outstanding": c.outstanding, "interest_rate": c.interest_rate, "maturity": c.maturity, "collateral": c.collateral,
            "purpose": c.purpose, "owner": c.owner, "approval_ref": c.approval_ref, "related_party": c.related_party, "status": c.status, "note": c.note,
            "schedule": [{"id": s.id, "due_date": s.due_date, "kind": s.kind, "amount": s.amount, "status": s.status, "done_on": s.done_on, "bank_ref": s.bank_ref} for s in c.schedule]}


@router.get("/fin/meta")
def meta(u: User = Depends(current_user)):
    return {"kinds": CONTRACT_KINDS}


@router.get("/fin/contracts")
def contracts(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return [c_out(c) for c in db.execute(select(FinContract).order_by(FinContract.kind, desc(FinContract.id))).scalars()]


class ContractIn(BaseModel):
    kind: str
    entity: str = "Công ty mẹ"
    company_id: int | None = None
    loan_group: str = ""
    partner: str
    contract_no: str = ""
    signed_on: date | None = None
    principal: float
    outstanding: float = 0
    interest_rate: float = 0
    maturity: date | None = None
    collateral: str = ""
    purpose: str = ""
    owner: str = ""
    approval_ref: str = ""
    related_party: bool = False
    note: str = ""
    months: int = 0
    first_due: date | None = None


@router.post("/fin/contracts", status_code=201)
def create(data: ContractIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    d = data.model_dump(); months = d.pop("months"); first = d.pop("first_due")
    try:
        c = F.create_contract(db, u, d, months, first)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"contract": c_out(c), "message": f"Đã lập hồ sơ {c.code}" + (f" – {len(c.schedule)} dòng lịch" if c.schedule else "")}


class SchedIn(BaseModel):
    due_date: date
    kind: str
    amount: float


@router.post("/fin/contracts/{cid}/schedule", status_code=201)
def add_sched(cid: int, data: SchedIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = db.get(FinContract, cid)
    if not c: raise HTTPException(404, "Không có hợp đồng")
    if data.kind not in ("tra_goc", "tra_lai", "thu_hoi", "giai_ngan", "nhan_vay"): raise HTTPException(422, "Loại lịch không hợp lệ")
    db.add(FinSchedule(contract_id=c.id, **data.model_dump()))
    R.audit(db, u.username, u.role, "them_lich_tai_chinh", f"fin:{c.code}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã thêm dòng lịch"}


class SettleIn(BaseModel):
    done_on: date
    bank_ref: str = ""
    amount: float | None = None


@router.post("/fin/schedule/{sid}/settle")
def settle(sid: int, data: SettleIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    s = db.get(FinSchedule, sid)
    if not s: raise HTTPException(404, "Không có dòng lịch")
    try:
        F.settle(db, u, s, data.done_on, data.bank_ref, data.amount)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã ghi nhận {s.kind} {s.amount:,.0f} đ – dư nợ còn {s.contract.outstanding:,.0f} đ"}


@router.get("/fin/forecast")
def forecast(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return F.forecast_13w(db)


@router.get("/fin/weekly")
def weekly(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    F.mark_overdue(db)
    return F.weekly_finance(db)


@router.get("/fin/plan")
def plan(u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return [{"id": i.id, "due_date": i.due_date, "direction": i.direction, "category": i.category, "description": i.description, "amount": i.amount, "recurring_monthly": i.recurring_monthly}
            for i in db.execute(select(CashPlanItem).order_by(CashPlanItem.due_date)).scalars()]


class PlanIn(BaseModel):
    due_date: date
    direction: str
    category: str
    description: str
    amount: float
    recurring_monthly: bool = False


@router.post("/fin/plan", status_code=201)
def plan_add(data: PlanIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    if data.direction not in ("in", "out"): raise HTTPException(422, "direction: in/out")
    db.add(CashPlanItem(**data.model_dump(), created_by=u.username)); db.commit()
    return {"message": "Đã thêm khoản kế hoạch"}


@router.delete("/fin/plan/{pid}")
def plan_del(pid: int, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    i = db.get(CashPlanItem, pid)
    if i: db.delete(i); db.commit()
    return {"message": "Đã xóa"}


@router.get("/fin/vay-xe")
def vay_xe(u: User = Depends(require_roles(*READ, "tp_dh")), db: Session = Depends(get_db)):
    """Bản đồ khế ước vay ↔ xe thế chấp, cảnh báo đáo hạn và xe đã ra khỏi đội nhưng còn thế chấp."""
    return F.vay_xe(db)


class KheUocNapIn(BaseModel):
    contract_no: str
    partner: str
    entity: str = "Công ty mẹ"
    loan_group: str = "vay_xe_45cho"
    principal: float
    outstanding: float = 0
    interest_rate: float = 0
    signed_on: date | None = None
    maturity: date | None = None
    collateral: str = ""
    purpose: str = ""
    note: str = ""
    xe: list[str] = []


class NapVayIn(BaseModel):
    khe_uoc: list[KheUocNapIn]
    nguon: str = ""
    tao_xe_da_ban: list[dict] = []


@router.post("/fin/vay-xe/nap")
def nap_vay_xe(data: NapVayIn, u: User = Depends(require_roles("ketoan", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp hồ sơ khế ước vay từ bộ hồ sơ ngân hàng, kèm danh sách xe là tài sản bảo đảm.

    Khớp theo SỐ HỢP ĐỒNG: chạy lại lần hai chỉ cập nhật dư nợ/lãi suất/đáo hạn của khế ước đã có,
    không tạo bản ghi trùng. Biển số không tìm thấy trong danh mục xe được trả về để rà chứ không
    tự tạo xe – trừ những xe đã bán khai báo riêng ở `tao_xe_da_ban`, vì chính những xe đó mới là
    lý do phải theo dõi: xe đã ra khỏi đội nhưng hồ sơ vay vẫn ghi là tài sản bảo đảm.
    """
    from app.models.hr import Vehicle
    from app.models.fleet import Collateral
    from app.models.core import Company
    cty = {c.name.lower(): c.id for c in db.execute(select(Company)).scalars()}

    def tim_cty(ten: str) -> int | None:
        t = (ten or "").lower()
        for name, cid in cty.items():
            if t and (t in name or name in t): return cid
        return None

    tao_xe = []
    for x in data.tao_xe_da_ban:
        plate = (x.get("plate") or "").strip()
        if not plate: continue
        v = db.execute(select(Vehicle).where(Vehicle.plate == plate)).scalar_one_or_none()
        if v is None:
            v = Vehicle(plate=plate, seats=45, active=False, lifecycle="da_ban", source_note=x.get("note", ""))
            db.add(v); db.flush(); tao_xe.append(plate)
    db.flush()
    xe_map = {v.plate: v for v in db.execute(select(Vehicle)).scalars()}

    tao, cap_nhat, gan_xe, khong_thay_xe = [], [], 0, []
    for k in data.khe_uoc:
        c = db.execute(select(FinContract).where(FinContract.contract_no == k.contract_no, FinContract.kind == "vay")).scalar_one_or_none()
        d = k.model_dump(); plates = d.pop("xe")
        if c is None:
            c = FinContract(code=F.next_code(db), kind="vay", created_by=u.username, **d)
            if not c.outstanding: c.outstanding = c.principal
            db.add(c); db.flush(); tao.append(c.contract_no)
        else:
            for f in ("partner", "entity", "loan_group", "principal", "outstanding", "interest_rate", "signed_on", "maturity", "collateral", "purpose", "note"):
                if d.get(f) not in (None, "", 0): setattr(c, f, d[f])
            cap_nhat.append(c.contract_no)
        c.company_id = tim_cty(k.entity) or c.company_id
        for plate in plates:
            v = xe_map.get(plate)
            if v is None:
                khong_thay_xe.append(plate); continue
            da_co = db.execute(select(Collateral).where(Collateral.contract_id == c.id, Collateral.vehicle_id == v.id,
                                                        Collateral.den_ngay.is_(None))).scalar_one_or_none()
            if da_co is None:
                db.add(Collateral(contract_id=c.id, vehicle_id=v.id, nguon=data.nguon or "Hồ sơ khế ước ngân hàng")); gan_xe += 1
    R.audit(db, u.username, u.role, "nap_ho_so_khe_uoc_vay", "fin:vay-xe",
            after={"tao": tao, "cap_nhat": cap_nhat, "gan_xe": gan_xe, "nguon": data.nguon})
    db.commit()
    return {"tao_moi": tao, "cap_nhat": cap_nhat, "so_xe_gan_the_chap": gan_xe,
            "xe_da_ban_tao_moi": tao_xe, "bien_so_khong_co_trong_danh_muc": khong_thay_xe,
            "message": f"Đã nạp {len(tao)} khế ước mới, cập nhật {len(cap_nhat)} khế ước, gắn {gan_xe} xe vào tài sản bảo đảm"}


class SaoKeDong(BaseModel):
    ke_uoc: str
    du_no: float = 0
    lai_suat: float | None = None
    dao_han: date | None = None
    giai_ngan: date | None = None
    muc_dich: str = ""
    loai: str = ""
    nhom: str = ""      # von_luu_dong / bds / khac → xếp vào "ngoài phạm vi theo dõi vay xe"


class SaoKeIn(BaseModel):
    ngan_hang: str = ""
    phap_nhan: str = ""
    den_ngay: date | None = None
    dong: list[SaoKeDong]


@router.post("/fin/doi-chieu-sao-ke")
def doi_chieu_sao_ke(data: SaoKeIn, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """So sao kê khoản vay của ngân hàng với khế ước đang theo dõi. Chỉ đọc và báo cáo, không sửa dữ liệu."""
    return F.doi_chieu_sao_ke(db, [d.model_dump() for d in data.dong], data.ngan_hang, data.den_ngay, data.phap_nhan)


class CapNhatSauDoiChieuIn(BaseModel):
    ngan_hang: str = ""
    den_ngay: date | None = None
    dong: list[SaoKeDong]


@router.post("/fin/cap-nhat-theo-sao-ke")
def cap_nhat_theo_sao_ke(data: CapNhatSauDoiChieuIn, u: User = Depends(require_roles("ketoan", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Ghi dư nợ / lãi suất / ngày đáo hạn theo sao kê cho những khế ước KHỚP MÃ.

    Chỉ chạm vào khế ước có mã trùng: dòng sao kê lạ không tự tạo khế ước mới, và khế ước không có trên
    sao kê không bị đóng – hai việc đó phải có người quyết định và có xác nhận của ngân hàng.
    """
    loans = {c.contract_no.strip(): c for c in
             db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars()
             if (c.contract_no or "").strip()}
    da_sua, bo_qua = [], []
    for d in data.dong:
        c = loans.get(d.ke_uoc.strip())
        if c is None: bo_qua.append(d.ke_uoc); continue
        thay_doi = {}
        if d.du_no and abs(c.outstanding - d.du_no) >= 1:
            thay_doi["du_no"] = [c.outstanding, d.du_no]; c.outstanding = d.du_no
        if d.lai_suat is not None and abs(c.interest_rate - d.lai_suat) >= 0.01:
            thay_doi["lai_suat"] = [c.interest_rate, d.lai_suat]; c.interest_rate = d.lai_suat
        if d.dao_han and c.maturity != d.dao_han:
            thay_doi["dao_han"] = [str(c.maturity or ""), str(d.dao_han)]; c.maturity = d.dao_han
        if thay_doi: da_sua.append({"ke_uoc": d.ke_uoc, "thay_doi": thay_doi})
    R.audit(db, u.username, u.role, "cap_nhat_khe_uoc_theo_sao_ke", f"fin:sao-ke:{data.ngan_hang}",
            after={"nguon": f"Sao kê {data.ngan_hang} đến {data.den_ngay}", "so_khe_uoc_sua": len(da_sua), "chi_tiet": da_sua})
    db.commit()
    return {"da_cap_nhat": da_sua, "khong_co_trong_he_thong": bo_qua,
            "message": f"Đã cập nhật {len(da_sua)} khế ước theo sao kê {data.ngan_hang}"}
