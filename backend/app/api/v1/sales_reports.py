"""API báo cáo bán hàng (danh mục như Vietrip) + xuất Excel; robot R9 giám sát bất thường."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth
from app.models.core import User
from app.services import sales_reports as SR

router = APIRouter(prefix="/api/v1", tags=["sales-reports"])
VIEW_ROLES = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "gd_kd", "nv_kd", "tp_dh", "nv_dh", "ketoan", "cntt", "bks", "hcns")


@router.get("/sales-reports")
def list_reports(u: User = Depends(current_user)):
    return [{"key": k, **v} for k, v in SR.REPORTS.items()]


def _params(from_: str | None, to: str | None, month: str | None) -> dict:
    return {"from": from_, "to": to, "month": month}


@router.get("/sales-reports/{key}")
def run_report(key: str, from_: str | None = Query(None, alias="from"), to: str | None = None, month: str | None = None, u: User = Depends(require_roles(*VIEW_ROLES)), db: Session = Depends(get_db)):
    if key not in SR.REPORTS: raise HTTPException(404, "Không có báo cáo")
    rep = SR.run(db, key, _params(from_, to, month))
    if u.role == "nv_kd":   # sale chỉ xem dòng của mình
        rep["summary"] = [r for r in rep["summary"] if r.get("sale", u.full_name) == u.full_name]
        rep["detail"] = [r for r in rep.get("detail", []) if r.get("sale", u.full_name) == u.full_name]
    return rep


@router.get("/sales-reports/{key}/xlsx")
def export_report(key: str, from_: str | None = Query(None, alias="from"), to: str | None = None, month: str | None = None, u: User = Depends(require_roles(*VIEW_ROLES)), db: Session = Depends(get_db)):
    if key not in SR.REPORTS: raise HTTPException(404, "Không có báo cáo")
    rep = SR.run(db, key, _params(from_, to, month))
    if u.role == "nv_kd":
        rep["summary"] = [r for r in rep["summary"] if r.get("sale", u.full_name) == u.full_name]; rep["detail"] = [r for r in rep.get("detail", []) if r.get("sale", u.full_name) == u.full_name]
    data = SR.to_xlsx(rep)
    name = f"VTOS_{key}_{month or from_ or ''}.xlsx".replace("--", "-")
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={name}"})


@router.post("/robot/r9")
def robot_r9_run(u: User = Depends(require_roles("chutich", "tgd", "bks", "cntt", "ketoan")), db: Session = Depends(get_db)):
    return SR.r9_run(db)


@router.post("/robot/r9/auto", dependencies=[Depends(robot_auth)])
def robot_r9_auto(db: Session = Depends(get_db)):
    return SR.r9_run(db)
