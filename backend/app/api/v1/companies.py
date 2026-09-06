"""Danh mục pháp nhân và gắn công ty chủ quản cho xe / hướng dẫn viên.

Ý kiến thẩm định 06/9/2026 mục C1. Nguyên tắc: đội xe thuộc Công ty TNHH Vận tải Vietrip là pháp nhân
riêng; xe thuê ngoài không thuộc pháp nhân nào trong tập đoàn. Lệnh điều xe dùng xe của một pháp nhân
trong phạm vi hợp nhất là GIAO DỊCH NỘI BỘ, phải nhận diện để loại trừ khi lập báo cáo hợp nhất.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.core import User, Company, COMPANY_KINDS
from app.models.hr import Vehicle, Employee
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["companies"])
WRITE = ("cntt", "ketoan", "tgd", "chutich")


def out(c: Company) -> dict:
    return {"id": c.id, "code": c.code, "name": c.name, "tax_code": c.tax_code, "kind": c.kind,
            "kind_label": COMPANY_KINDS.get(c.kind, c.kind), "ownership_pct": c.ownership_pct,
            "parent_id": c.parent_id, "effective_from": c.effective_from, "active": c.active,
            "in_group": c.in_group(), "related_party": c.related_party(), "note": c.note}


@router.get("/companies")
def list_companies(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [out(c) for c in db.execute(select(Company).order_by(Company.kind, Company.code)).scalars()]


class CompanyIn(BaseModel):
    code: str
    name: str
    tax_code: str = ""
    kind: str = "con"
    ownership_pct: float = 0
    parent_id: int | None = None
    effective_from: date | None = None
    note: str = ""


@router.post("/companies", status_code=201)
def create_company(data: CompanyIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    if data.kind not in COMPANY_KINDS: raise HTTPException(422, "Loại pháp nhân không hợp lệ")
    if db.execute(select(Company).where(Company.code == data.code)).scalars().first():
        raise HTTPException(422, "Mã pháp nhân đã tồn tại")
    c = Company(**data.model_dump()); db.add(c); db.flush()
    R.audit(db, u.username, u.role, "tao_phap_nhan", f"company:{c.code}", after=out(c)); db.commit(); db.refresh(c)
    return out(c)


@router.put("/companies/{cid}")
def update_company(cid: int, data: CompanyIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if not c: raise HTTPException(404, "Không có pháp nhân")
    before = out(c)
    for k, v in data.model_dump().items(): setattr(c, k, v)
    R.audit(db, u.username, u.role, "sua_phap_nhan", f"company:{c.code}", before=before, after=out(c)); db.commit()
    return out(c)


class OwnerIn(BaseModel):
    company_id: int | None = None


@router.put("/vehicles/{vid}/company")
def set_vehicle_company(vid: int, data: OwnerIn, u: User = Depends(require_roles(*WRITE, "hcns", "tp_dh")), db: Session = Depends(get_db)):
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    if data.company_id and not db.get(Company, data.company_id): raise HTTPException(422, "Không có pháp nhân")
    before = v.company_id; v.company_id = data.company_id
    R.audit(db, u.username, u.role, "gan_chu_quan_xe", f"vehicle:{v.plate}", before={"company_id": before}, after={"company_id": v.company_id}); db.commit()
    return {"ok": True, "message": f"Đã gán công ty chủ quản cho xe {v.plate}"}


@router.put("/employees/{eid}/company")
def set_employee_company(eid: int, data: OwnerIn, u: User = Depends(require_roles(*WRITE, "hcns")), db: Session = Depends(get_db)):
    e = db.get(Employee, eid)
    if not e: raise HTTPException(404, "Không có nhân sự")
    if data.company_id and not db.get(Company, data.company_id): raise HTTPException(422, "Không có pháp nhân")
    before = e.company_id; e.company_id = data.company_id
    R.audit(db, u.username, u.role, "gan_chu_quan_nhan_su", f"employee:{e.code}", before={"company_id": before}, after={"company_id": e.company_id}); db.commit()
    return {"ok": True, "message": f"Đã gán công ty chủ quản cho {e.full_name}"}


@router.get("/companies/coverage")
def coverage(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bao nhiêu xe và HDV đã có công ty chủ quản – để biết còn phải gán tay bao nhiêu."""
    veh = list(db.execute(select(Vehicle)).scalars())
    hdv = [e for e in db.execute(select(Employee)).scalars() if e.card_no]
    cos = list(db.execute(select(Company)).scalars())
    return {"xe": {"tong": len(veh), "da_gan": sum(1 for v in veh if v.company_id), "chua_gan": sum(1 for v in veh if not v.company_id)},
            "hdv": {"tong": len(hdv), "da_gan": sum(1 for e in hdv if e.company_id), "chua_gan": sum(1 for e in hdv if not e.company_id)},
            "phap_nhan": {"tong": len(cos), "hop_nhat": sum(1 for c in cos if c.in_group()), "ben_lien_quan": sum(1 for c in cos if c.related_party()),
                          "thieu_mst": sum(1 for c in cos if not c.tax_code), "tam_ngung": sum(1 for c in cos if not c.active)}}

# ---------- Nạp danh sách tài xế – xe ----------
class DriverRow(BaseModel):
    full_name: str
    plate: str = ""
    birth_date: str | None = None
    phone: str = ""


class DriverBatch(BaseModel):
    rows: list[DriverRow]
    tao_xe_thieu: bool = False


@router.post("/drivers/reconcile")
def drivers_reconcile(data: DriverBatch, u: User = Depends(require_roles(*WRITE, "hcns", "tp_dh")), db: Session = Depends(get_db)):
    """Đối chiếu danh sách tài xế với dữ liệu đang có – chỉ đọc, xem trước khi nạp."""
    from app.services import drivers as D
    return D.reconcile(db, [r.model_dump() for r in data.rows])


@router.post("/drivers/apply")
def drivers_apply(data: DriverBatch, u: User = Depends(require_roles(*WRITE, "hcns")), db: Session = Depends(get_db)):
    from app.services import drivers as D
    return D.apply(db, [r.model_dump() for r in data.rows], u.username, u.role, data.tao_xe_thieu)
