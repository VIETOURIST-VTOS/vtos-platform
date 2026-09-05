"""API đồng bộ Vietrip → VTOS: nạp thô theo entity, xem trạng thái, ánh xạ sang nghiệp vụ, dòng chi phí tour."""
from fastapi import APIRouter, Depends, HTTPException, Header
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


# ---------- robot đồng bộ phía máy chủ (không cần trình duyệt) ----------
class SyncIn(BaseModel):
    from_date: str | None = None   # mặc định 7 ngày gần nhất
    to_date: str | None = None
    products: bool = False         # kéo lại 354 sản phẩm (chậm ~10 phút) – bật khi cần
    settlements_days: int = 10     # quét bảng quyết toán tour kết thúc trong N ngày


def _dates(data: SyncIn):
    from datetime import date as _d, timedelta
    t = _d.fromisoformat(data.to_date) if data.to_date else _d.today()
    f = _d.fromisoformat(data.from_date) if data.from_date else t - timedelta(days=7)
    return f, t


@router.post("/import/vietrip/sync")
def vietrip_sync(data: SyncIn, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    from app.services import vietrip_client as VC
    f, t = _dates(data)
    if not VC.start_background(f, t, data.products, data.settlements_days): raise HTTPException(409, "Robot đang chạy – xem trạng thái")
    R.audit(db, u.username, u.role, "chay_robot_vietrip", "vietrip", after={"tu": str(f), "den": str(t)}); db.commit()
    return {"message": f"Robot đồng bộ Vietrip đã chạy nền ({f} → {t}) – theo dõi ở Trạng thái robot"}


@router.post("/robot/vietrip/sync")
def robot_vietrip_sync(data: SyncIn, x_robot_token: str | None = Header(default=None)):
    """GitHub Actions / n8n gọi hằng ngày (X-Robot-Token)."""
    from app.core.config import settings
    from app.services import vietrip_client as VC
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    f, t = _dates(data)
    return {"started": VC.start_background(f, t, data.products, data.settlements_days), "from": str(f), "to": str(t)}


@router.get("/import/vietrip/robot-status")
def robot_status(u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    from app.services import vietrip_client as VC
    from app.core.config import settings
    return {**{k: v for k, v in VC.STATE.items() if k != "log"}, "log": VC.STATE["log"][-40:], "credentials_set": bool(settings.VIETRIP_PHONE and settings.VIETRIP_PASSWORD)}


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


