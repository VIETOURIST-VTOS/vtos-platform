"""Danh mục pháp nhân và gắn công ty chủ quản cho hồ sơ (Ý kiến thẩm định 06/9/2026 – C1, Đợt 2 mục 2).

Pháp nhân đứng tên xe lấy từ giấy đăng ký xe, không suy từ cờ "xe nội bộ"; xe thuê ngoài không thuộc
pháp nhân nào trong tập đoàn. Lệnh điều xe dùng xe của một pháp nhân trong phạm vi hợp nhất là GIAO
DỊCH NỘI BỘ, phải nhận diện để loại trừ khi lập báo cáo hợp nhất.

Với hồ sơ nghiệp vụ (tour, booking, phiếu thu, đề nghị chi, chứng từ ghi sổ): rỗng nghĩa là CHƯA XÁC
ĐỊNH, không phải công ty mẹ – xem app/services/company_scope.py.
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
from app.services import company_scope as CS

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

# ---------- Công ty chủ quản của hồ sơ nghiệp vụ (Đợt 2 mục 2) ----------
SCOPE_WRITE = ("cntt", "ketoan", "tgd", "chutich", "tp_dh", "ptgd_doan")


@router.get("/companies/scope/coverage")
def scope_coverage(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Từng loại hồ sơ còn bao nhiêu bản ghi chưa xác định pháp nhân – đây là danh sách đối chiếu."""
    return CS.coverage(db)


@router.get("/companies/scope/{kind}/pending")
def scope_pending(kind: str, limit: int = 100, offset: int = 0, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if kind not in CS.KINDS: raise HTTPException(404, "Loại hồ sơ không hợp lệ")
    return CS.pending(db, kind, min(limit, 500), offset)


@router.post("/companies/scope/derive")
def scope_derive(u: User = Depends(require_roles(*SCOPE_WRITE)), db: Session = Depends(get_db)):
    """Suy pháp nhân từ hồ sơ cha đã xác định (booking ← tour, phiếu thu ← booking…).
    Không đụng tới hồ sơ đã có pháp nhân và không suy được cho tour."""
    return CS.derive(db, u)


class ScopeAssign(BaseModel):
    ids: list[int]
    company_id: int | None = None      # None = gỡ về "chưa xác định"


@router.post("/companies/scope/{kind}/assign")
def scope_assign(kind: str, data: ScopeAssign, u: User = Depends(require_roles(*SCOPE_WRITE)), db: Session = Depends(get_db)):
    if kind not in CS.KINDS: raise HTTPException(404, "Loại hồ sơ không hợp lệ")
    try:
        return CS.assign(db, kind, data.ids, data.company_id, u)
    except ValueError as e:
        raise HTTPException(422, str(e))


class TourScopeFilter(BaseModel):
    company_id: int
    nguon: str = ""                    # vietrip / vtos / rỗng = tất cả
    tu_ngay: date | None = None
    den_ngay: date | None = None
    loai: str = ""
    chi_chua_gan: bool = True


@router.post("/companies/scope/tour/assign-filter")
def scope_assign_tours(data: TourScopeFilter, u: User = Depends(require_roles(*SCOPE_WRITE)), db: Session = Depends(get_db)):
    """Gán pháp nhân cho một lô tour theo tiêu chí (nguồn, khoảng khởi hành, loại tour).
    Tiêu chí được ghi vào nhật ký để sau này truy lại được căn cứ."""
    try:
        return CS.assign_tours_by_filter(db, data.company_id, u, data.nguon, data.tu_ngay, data.den_ngay,
                                         data.loai, data.chi_chua_gan)
    except ValueError as e:
        raise HTTPException(422, str(e))


class HoSoScopeFilter(BaseModel):
    company_id: int
    tu_ky: str = ""            # 2026-01 (chứng từ ghi sổ)
    den_ky: str = ""
    nguon: str = ""            # source_type của chứng từ
    nhom: str = ""             # category của đề nghị chi
    khong_co_tour: bool = False
    chi_chua_gan: bool = True


@router.get("/companies/scope/{kind}/groups")
def scope_groups(kind: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Hồ sơ chưa xác định gom theo tiêu chí – để biết cần bao nhiêu lần gán, không phải bao nhiêu dòng."""
    if kind not in CS.KINDS: raise HTTPException(404, "Loại hồ sơ không hợp lệ")
    return CS.nhom_con_lai(db, kind)


@router.post("/companies/scope/{kind}/assign-batch")
def scope_assign_batch(kind: str, data: HoSoScopeFilter, u: User = Depends(require_roles(*SCOPE_WRITE)), db: Session = Depends(get_db)):
    """Gán theo lô cho chứng từ ghi sổ / đề nghị chi không gắn tour (chi hành chính, chứng từ nạp từ MISA)."""
    try:
        return CS.assign_by_filter(db, kind, data.company_id, u, data.tu_ky, data.den_ky, data.nguon,
                                   data.nhom, data.khong_co_tour, data.chi_chua_gan)
    except ValueError as e:
        raise HTTPException(422, str(e))


# ---------- Nạp danh sách tài xế – xe ----------
class DriverRow(BaseModel):
    full_name: str
    plate: str = ""
    birth_date: str | None = None
    phone: str = ""
    employee_code: str = ""      # chỉ đích danh hồ sơ khi có nhiều người trùng tên


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


class FleetRow(BaseModel):
    plate: str
    company_code: str = ""       # mã pháp nhân ĐỨNG TÊN trên giấy đăng ký xe
    phap_nhan: str = ""          # tên pháp nhân ghi trong hồ sơ nguồn (để đối chiếu)
    driver: str = ""
    seats: int = 0


class FleetBatch(BaseModel):
    rows: list[FleetRow]
    ngung_xe_ngoai_ds: bool = False


@router.post("/fleet/apply")
def fleet_apply(data: FleetBatch, u: User = Depends(require_roles(*WRITE, "hcns", "tp_dh")), db: Session = Depends(get_db)):
    """Chốt đội xe theo hồ sơ đăng ký xe: pháp nhân đứng tên, tài xế phụ trách, xe ngưng khai thác."""
    from app.services import drivers as D
    return D.fleet_apply(db, [r.model_dump() for r in data.rows], u.username, u.role, data.ngung_xe_ngoai_ds)


# ---------- P6: phạm vi pháp nhân của phiên đăng nhập ----------
@router.get("/pham-vi")
def pham_vi_phien(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Phiên này đang xem dữ liệu của ai, và còn bao nhiêu hồ sơ chưa xác định pháp nhân.

    Hai con số ở đây KHÔNG được cộng lại thành một. Đó là toàn bộ lý do endpoint này tồn tại: nếu
    màn hình chỉ hiện một tổng thì hồ sơ chưa xác định pháp nhân sẽ trôi vào con số của công ty mẹ
    và không ai còn nhìn ra. `dem()` trả về hai khoá riêng và cố tình không trả về khoá "tong".
    """
    from app.services import pham_vi_phap_nhan as PV
    dong = []
    for key, cfg in CS.KINDS.items():
        d = PV.dem(db, cfg["model"], u)
        dong.append({"kind": key, "label": cfg["label"], **d})
    return {"pham_vi": PV.mo_ta(db, u), "dong": dong,
            "chua_gan_tong": sum(d["chua_gan"] for d in dong),
            "ghi_chu": "Hồ sơ chưa xác định pháp nhân vẫn hiện trong danh sách và được đánh dấu "
                       "'chua_gan'. Nó không thuộc công ty mẹ – phải do Điều hành/Kế toán gán."}
