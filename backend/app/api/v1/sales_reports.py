"""API báo cáo bán hàng (danh mục như Vietrip) + xuất Excel; robot R9 giám sát bất thường."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth
from app.models.core import User
from app.services import sales_reports as SR

router = APIRouter(prefix="/api/v1", tags=["sales-reports"])
VIEW_ROLES = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "tp_dh", "nv_dh", "ketoan", "cntt", "bks", "hcns")


@router.get("/sales-reports")
def list_reports(u: User = Depends(current_user)):
    ds = [{"key": k, **v} for k, v in SR.REPORTS.items()]
    if u.role in VAI_AN_GIA_VON:        # R5-20: mô tả không hứa cột người bán không được thấy
        for x in ds:
            x["desc"] = x.get("desc", "").replace("chi phí quyết toán, lợi nhuận, ", "")
    return ds


def _scope(db, u: User, rep: dict) -> None:
    """NV KD chỉ xem dòng của mình; trưởng nhóm xem dòng các sale trong nhóm."""
    from app.services import access as AC
    from sqlalchemy import select
    vis = AC.sales_ids_visible(db, u)
    if vis is None: return
    names = set(db.execute(select(User.full_name).where(User.id.in_(vis))).scalars())
    rep["summary"] = [r for r in rep["summary"] if r.get("sale", u.full_name) in names]
    rep["detail"] = [r for r in rep.get("detail", []) if r.get("sale", u.full_name) in names]


# R5-20 · NGƯỜI BÁN KHÔNG THẤY GIÁ VỐN (Chủ tịch quyết 25/9/2026 «Phòng kinh doanh lẻ gỡ hết, không liên
# quan giá vốn»; 14/11/2026 «1 ok»). Máy chủ cắt cột chi phí / lợi nhuận / biên trước khi trả — cả bản xem
# lẫn bản Excel — chứ không trả rồi giấu ở giao diện.
VAI_AN_GIA_VON = ("nv_kd", "tn_kd", "tp_kd")
KHOA_GIA_VON = ("cost", "profit", "margin")


def _an_gia_von(u: User, rep: dict) -> None:
    if u.role not in VAI_AN_GIA_VON:
        return
    cols = rep.get("columns") or {}
    for k in ("summary", "detail"):
        if k in cols:
            cols[k] = [c for c in cols[k] if c[0] not in KHOA_GIA_VON]
        rep[k] = [{x: v for x, v in r.items() if x not in KHOA_GIA_VON} for r in rep.get(k) or []]
    rep["total"] = {x: v for x, v in (rep.get("total") or {}).items() if x not in KHOA_GIA_VON}


def _params(from_: str | None, to: str | None, month: str | None, mang: str) -> dict:
    return {"from": from_, "to": to, "month": month, "mang": mang}


def _run(db, key: str, u: User, p: dict) -> dict:
    """Chạy báo cáo rồi thu hẹp theo quyền xem. Mảng gõ sai thì 422 chứ không lặng lẽ trả về toàn hệ thống –
    người dùng tưởng đang xem phòng mình mà thật ra đang xem tất cả là kiểu sai khó phát hiện nhất."""
    if key not in SR.REPORTS: raise HTTPException(404, "Không có báo cáo")
    try:
        rep = SR.run(db, key, p)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    _scope(db, u, rep)
    _an_gia_von(u, rep)
    return rep


@router.get("/sales-reports/{key}")
def run_report(key: str, from_: str | None = Query(None, alias="from"), to: str | None = None, month: str | None = None, mang: str = "", u: User = Depends(require_roles(*VIEW_ROLES)), db: Session = Depends(get_db)):
    return _run(db, key, u, _params(from_, to, month, mang))


@router.get("/sales-reports/{key}/xlsx")
def export_report(key: str, from_: str | None = Query(None, alias="from"), to: str | None = None, month: str | None = None, mang: str = "", u: User = Depends(require_roles(*VIEW_ROLES)), db: Session = Depends(get_db)):
    rep = _run(db, key, u, _params(from_, to, month, mang))
    data = SR.to_xlsx(rep)
    name = f"VTOS_{key}_{rep.get('mang') or 'toanhethong'}_{month or from_ or ''}.xlsx".replace("--", "-")
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={name}"})


@router.post("/robot/r9")
def robot_r9_run(u: User = Depends(require_roles("chutich", "tgd", "bks", "cntt", "ketoan")), db: Session = Depends(get_db)):
    return SR.r9_run(db)


@router.post("/robot/r9/auto", dependencies=[Depends(robot_auth)])
def robot_r9_auto(db: Session = Depends(get_db)):
    return SR.r9_run(db)
