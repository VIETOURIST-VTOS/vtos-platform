"""API Tài sản cố định & Công cụ dụng cụ – chi phí trả trước (phân hệ TSCĐ / CCDC như MISA)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.models.assets import (FixedAsset, PrepaidExpense, ASSET_KINDS, ASSET_STATUS, PREPAID_KINDS, PREPAID_STATUS)
from app.services import assets as AS

router = APIRouter(prefix="/api/v1", tags=["tai-san"])
READ = ("ketoan", "cntt", "tgd", "chutich", "bks", "ptgd_doan", "hcns")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(content: bytes, name: str) -> Response:
    return Response(content=content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


def asset_out(a: FixedAsset) -> dict:
    return {"id": a.id, "code": a.code, "name": a.name, "kind": a.kind, "kind_name": ASSET_KINDS.get(a.kind, {}).get("ten", a.kind),
            "group": a.group, "asset_account": a.asset_account, "depr_account": a.depr_account, "expense_account": a.expense_account,
            "partner_code": a.partner_code, "project_code": a.project_code, "department": a.department,
            "purchase_date": a.purchase_date, "start_date": a.start_date, "cost": a.cost, "depr_months": a.depr_months,
            "salvage": a.salvage, "monthly": AS.monthly_depreciation(a), "opening_accumulated": a.opening_accumulated,
            "opening_period": a.opening_period, "quantity": a.quantity, "status": a.status,
            "status_name": ASSET_STATUS.get(a.status, a.status), "disposed_date": a.disposed_date,
            "note": a.note, "source": a.source, "created_by": a.created_by}


def prepaid_out(p: PrepaidExpense) -> dict:
    return {"id": p.id, "code": p.code, "name": p.name, "kind": p.kind, "kind_name": PREPAID_KINDS.get(p.kind, {}).get("ten", p.kind),
            "asset_account": p.asset_account, "expense_account": p.expense_account, "partner_code": p.partner_code,
            "project_code": p.project_code, "department": p.department, "start_date": p.start_date,
            "amount": p.amount, "months": p.months, "monthly": AS.monthly_allocation(p),
            "opening_allocated": p.opening_allocated, "opening_period": p.opening_period, "quantity": p.quantity,
            "status": p.status, "status_name": PREPAID_STATUS.get(p.status, p.status), "note": p.note,
            "source": p.source, "created_by": p.created_by}


@router.get("/assets/meta")
def meta(u: User = Depends(require_roles(*READ))):
    """Danh mục loại TSCĐ / CCDC và trạng thái – để dựng form giống MISA."""
    return {"asset_kinds": ASSET_KINDS, "asset_status": ASSET_STATUS, "prepaid_kinds": PREPAID_KINDS, "prepaid_status": PREPAID_STATUS}


# ---------- Thẻ tài sản cố định ----------

class AssetIn(BaseModel):
    code: str = ""
    name: str
    kind: str = "huu_hinh"
    group: str = ""
    asset_account: str = ""
    depr_account: str = ""
    expense_account: str = ""
    partner_code: str = ""
    project_code: str = ""
    department: str = ""
    purchase_date: date | None = None
    start_date: date
    cost: float | None = None
    depr_months: int = 0
    salvage: float | None = None
    opening_accumulated: float | None = None
    opening_period: str = ""
    quantity: int = 1
    note: str = ""


@router.get("/fixed-assets")
def list_assets(status: str = "", department: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    # HÀNG RÀO SỔ THƯƠNG HIỆU (18/9/2026) – xem services/tai_san_thuong_hieu. Màn hình /tai-san là
    # danh sách thẻ TSCĐ của Kế toán; thẻ nhận diện chưa khai nguyên giá không thuộc về đây.
    from app.services.tai_san_thuong_hieu import loc_so_ke_toan
    q = loc_so_ke_toan(select(FixedAsset)).order_by(FixedAsset.code)
    if status:
        q = q.where(FixedAsset.status == status)
    if department:
        q = q.where(FixedAsset.department == department)
    return [asset_out(a) for a in db.execute(q).scalars()]


@router.post("/fixed-assets", status_code=201)
def add_asset(data: AssetIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        a = AS.create_asset(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return asset_out(a)


class DisposeIn(BaseModel):
    on: date
    reason: str = ""


@router.post("/fixed-assets/{aid}/dispose")
def dispose(aid: int, data: DisposeIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    a = db.get(FixedAsset, aid)
    if not a:
        raise HTTPException(404, "Không tìm thấy tài sản")
    try:
        AS.dispose_asset(db, u, a, data.on, data.reason)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return asset_out(a)


@router.get("/fixed-assets/depreciation")
def depreciation(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Bảng tính khấu hao TSCĐ của kỳ – xem trước trước khi ghi sổ."""
    return AS.depreciation_table(db, period)


@router.post("/fixed-assets/depreciation/{period}/post")
def post_depreciation(period: str, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        return AS.post_depreciation(db, u, period)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/fixed-assets/depreciation.xlsx")
def depreciation_xlsx(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    tab = AS.depreciation_table(db, period)
    return _xlsx(AS.depreciation_xlsx(tab), f"BANG_TINH_KHAU_HAO_{period.replace('-', '')}.xlsx")


# ---------- Công cụ dụng cụ / chi phí trả trước ----------

class PrepaidIn(BaseModel):
    code: str = ""
    name: str
    kind: str = "ccdc"
    asset_account: str = ""
    expense_account: str = ""
    partner_code: str = ""
    project_code: str = ""
    department: str = ""
    start_date: date
    amount: float | None = None
    months: int = 1
    opening_allocated: float | None = None
    opening_period: str = ""
    quantity: int = 1
    note: str = ""


@router.get("/prepaid")
def list_prepaid(status: str = "", kind: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(PrepaidExpense).order_by(PrepaidExpense.code)
    if status:
        q = q.where(PrepaidExpense.status == status)
    if kind:
        q = q.where(PrepaidExpense.kind == kind)
    return [prepaid_out(p) for p in db.execute(q).scalars()]


@router.post("/prepaid", status_code=201)
def add_prepaid(data: PrepaidIn, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        p = AS.create_prepaid(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return prepaid_out(p)


@router.get("/prepaid/allocation")
def allocation(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Bảng phân bổ chi phí trả trước / CCDC của kỳ."""
    return AS.allocation_table(db, period)


@router.post("/prepaid/allocation/{period}/post")
def post_allocation(period: str, u: User = Depends(require_roles("ketoan")), db: Session = Depends(get_db)):
    try:
        return AS.post_allocation(db, u, period)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/prepaid/allocation.xlsx")
def allocation_xlsx(period: str, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    tab = AS.allocation_table(db, period)
    return _xlsx(AS.allocation_xlsx(tab), f"BANG_PHAN_BO_CP_TRA_TRUOC_{period.replace('-', '')}.xlsx")
