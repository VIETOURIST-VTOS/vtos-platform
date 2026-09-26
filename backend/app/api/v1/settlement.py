"""API quyết toán tour soạn trên VTOS: dòng chi phí (thêm/sửa/hủy), chứng từ theo dòng, khớp đã thanh toán, chấm quyết toán, Kế toán trả lại."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, toan_quyen
from app.models.core import User, Tour
from app.models.vietrip import TourCostLine
from app.services import settlement as ST
from app.services import access as AC

router = APIRouter(prefix="/api/v1", tags=["settlement"])


class LineIn(BaseModel):
    description: str
    service_type: str = "OTHER"
    cost_kind: str = "co_dinh"
    supplier_name: str
    supplier_tax_code: str = ""
    unit_price: float | None = None
    qty: float = 0
    coef: float = 1
    budget: float | None = None
    paid: float | None = None
    note: str = ""


class Reason(BaseModel):
    note: str = ""


class DocIn(BaseModel):
    name: str = ""
    data: str = ""       # data URL ảnh/PDF; rỗng = gỡ chứng từ


def _tour(db: Session, tid: int) -> Tour:
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    return t


def _line(db: Session, t: Tour, lid: int) -> TourCostLine:
    l = db.get(TourCostLine, lid)
    if not l or l.tour_id != t.id: raise HTTPException(404, "Không có dòng quyết toán")
    return l


@router.get("/tours/{tid}/settlement")
def get_settlement(tid: int, u: User = Depends(require_roles(*AC.COST_ROLES, mo_ta="quyết toán tour")), db: Session = Depends(get_db)):
    t = _tour(db, tid)
    return {"tour": t.code, "status": t.status, "version": t.settlement_version, "can_edit": ST.can_edit(db, u, t), "service_types": ST.SERVICE_TYPES,
            "lines": [ST.line_out(l) for l in ST.lines_of(db, t)], "summary": ST.summary(db, t), "checks": ST.checks(db, t)}


@router.post("/tours/{tid}/settlement/lines", status_code=201)
def add_line(tid: int, data: LineIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return ST.line_out(ST.add_line(db, u, _tour(db, tid), data.model_dump()))


@router.put("/tours/{tid}/settlement/lines/{lid}")
def update_line(tid: int, lid: int, data: LineIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid)
    return ST.line_out(ST.update_line(db, u, t, _line(db, t, lid), data.model_dump()))


@router.post("/tours/{tid}/settlement/lines/{lid}/cancel")
def cancel_line(tid: int, lid: int, data: Reason, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid); ST.cancel_line(db, u, t, _line(db, t, lid), data.note)
    return {"message": "Đã hủy dòng quyết toán"}


@router.post("/tours/{tid}/settlement/lines/{lid}/doc")
def set_doc(tid: int, lid: int, data: DocIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid); ST.set_doc(db, u, t, _line(db, t, lid), data.name, data.data)
    return {"message": "Đã gắn chứng từ" if data.data else "Đã gỡ chứng từ"}


@router.get("/tours/{tid}/settlement/lines/{lid}/doc")
def get_doc(tid: int, lid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid); l = _line(db, t, lid)
    if not l.doc_data: raise HTTPException(404, "Dòng chưa có chứng từ")
    import base64
    head, b64 = l.doc_data.split(",", 1); mime = head[5:].split(";")[0]
    return Response(content=base64.b64decode(b64), media_type=mime, headers={"Content-Disposition": f"inline; filename*=UTF-8''{l.doc_name or 'chung-tu'}"})


@router.post("/tours/{tid}/settlement/match-paid")
def match_paid(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid)
    if u.id != t.operator_id and u.role not in ("ketoan", "cntt", "tp_dh") and not toan_quyen(u): raise HTTPException(403, "Chỉ Điều hành chuyến / TP ĐH / Kế toán khớp thanh toán")
    return ST.match_paid(db, t)


@router.post("/tours/{tid}/kt-return")
def kt_return(tid: int, data: Reason, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": ST.kt_return(db, u, _tour(db, tid), data.note)}
