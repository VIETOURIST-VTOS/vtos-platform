"""API đồng bộ Vietrip → VTOS: nạp thô theo entity, xem trạng thái, ánh xạ sang nghiệp vụ, dòng chi phí tour."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, Tour
from app.models.vietrip import VtRecord, TourCostLine
from app.models.hr import Employee
from app.services import vietrip as VT
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["vietrip"])
SYNC_ROLES = ("cntt", "ketoan", "tgd", "chutich")


@router.get("/import/vietrip/status")
def status(u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    return VT.status_counts(db)


@router.post("/import/vietrip/apply")
def apply(limit: int = 400, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    try:
        return {"applied": VT.apply_all(db, u.username, limit=max(1, min(limit, 2000))), "message": "Đã ánh xạ dữ liệu Vietrip vào VTOS"}
    except Exception as e:   # trả lỗi có nội dung để robot/CNTT chẩn đoán (không lộ dữ liệu nhạy cảm)
        db.rollback()
        raise HTTPException(500, f"Ánh xạ lỗi: {type(e).__name__}: {str(e)[:600]}")


@router.delete("/import/vietrip/records/{entity}/{vietrip_id}")
def delete_record(entity: str, vietrip_id: str, u: User = Depends(require_roles("cntt")), db: Session = Depends(get_db)):
    """CNTT gỡ bản ghi nạp thử/nhầm: xóa bản ghi thô; với user → xóa hồ sơ nhân sự VT#### và khóa tài khoản tạo từ Vietrip (không xóa dữ liệu nghiệp vụ khác)."""
    r = db.execute(select(VtRecord).where(VtRecord.entity == entity, VtRecord.vietrip_id == vietrip_id)).scalars().first()
    if not r: raise HTTPException(404, "Không có bản ghi")
    removed = {"vt_record": vietrip_id}
    if entity == "user" and vietrip_id.isdigit():
        e = db.execute(select(Employee).where(Employee.code == f"VT{int(vietrip_id):04d}")).scalars().first()
        if e:
            usr = db.execute(select(User).where(User.id == e.user_id)).scalars().first()
            db.delete(e); removed["employee"] = e.code
            if usr and usr.username not in ("chutich", "tgd", "cntt", "ketoan"):
                usr.active = False; removed["user_locked"] = usr.username
    db.delete(r)
    R.audit(db, u.username, u.role, "dong_bo_vietrip_xoa", entity, after=removed); db.commit()
    return removed


@router.get("/import/vietrip/records")
def records(entity: str, limit: int = 50, unapplied: bool = False, u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    q = select(VtRecord).where(VtRecord.entity == entity).order_by(desc(VtRecord.on_date), desc(VtRecord.id))
    if unapplied: q = q.where(VtRecord.applied == False)
    return [{"id": r.id, "vietrip_id": r.vietrip_id, "ref": r.ref, "on_date": r.on_date, "amount": r.amount, "applied": r.applied, "apply_note": r.apply_note, "synced_at": r.synced_at, "raw": r.raw}
            for r in db.execute(q.limit(limit)).scalars()]


@router.get("/tours/{tid}/cost-lines")
def cost_lines(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    rows = db.execute(select(TourCostLine).where(TourCostLine.tour_id == tid).order_by(TourCostLine.line_no)).scalars().all()
    return {"tour": t.code, "rows": [{"id": l.id, "line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "supplier_name": l.supplier_name,
                                      "supplier_tax_code": l.supplier_tax_code, "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "actual": l.actual, "paid": l.paid, "note": l.note, "source": l.source} for l in rows],
            "total_actual": sum(l.actual for l in rows), "total_paid": sum(l.paid for l in rows)}


# đặt sau cùng để không nuốt /apply, /status, /records
class Batch(BaseModel):
    rows: list[dict]


@router.post("/import/vietrip/{entity}")
def ingest(entity: str, data: Batch, u: User = Depends(require_roles(*SYNC_ROLES)), db: Session = Depends(get_db)):
    try:
        new, upd = VT.upsert(db, entity, data.rows)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"entity": entity, "received": len(data.rows), "new": new, "updated": upd}


