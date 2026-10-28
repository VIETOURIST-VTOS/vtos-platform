"""KS-2 · Đối soát OTA — Kế toán nạp báo cáo, Chủ tịch duyệt lô, sổ hoa hồng USD."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.khach_san_ota import LoNapOta
from app.services import doi_soat_ota as S

router = APIRouter(prefix="/api/v1/doi-soat-ota", tags=["doi-soat-ota"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiDoiSoat as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("")
def tong_quan(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return S.tong_quan(db, u)


@router.post("/doc-thu")
async def doc_thu(ota_id: int = Form(...), tep: UploadFile = File(...), u: User = Depends(require_roles(*S.VAI_NAP)),
                  db: Session = Depends(get_db)):
    du_lieu = await tep.read(S.TEP_TOI_DA + 1)
    return _goi(S.doc_thu, db, u, ota_id, tep.filename or "", du_lieu)


@router.post("/lo")
async def gui_duyet(ota_id: int = Form(...), ky: str = Form(...), tep: UploadFile = File(...),
                    u: User = Depends(require_roles(*S.VAI_NAP)), db: Session = Depends(get_db)):
    du_lieu = await tep.read(S.TEP_TOI_DA + 1)
    lo = _goi(S.gui_duyet, db, u, ota_id, ky, tep.filename or "", du_lieu)
    return {"message": f"Đã gửi lô {lo.ma} cho Chủ tịch duyệt — chưa ghi sổ", "lo": S.lo_out(db, lo, u)}


@router.get("/lo/{lo_id}")
def xem_lo(lo_id: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    lo = db.get(LoNapOta, lo_id)
    if lo is None:
        raise HTTPException(404, "Không có lô này")
    return S.lo_out(db, lo, u, chi_tiet=True)


class XuLyIn(BaseModel):
    hanh_dong: str          # duyet / tu_choi
    ly_do: str = ""


@router.post("/lo/{lo_id}")
def xu_ly(lo_id: int, data: XuLyIn, u: User = Depends(require_roles(*S.VAI_DUYET)), db: Session = Depends(get_db)):
    if data.hanh_dong == "duyet":
        lo = _goi(S.duyet, db, u, lo_id)
        msg = f"Đã duyệt {lo.ma} và ghi sổ"
    elif data.hanh_dong == "tu_choi":
        lo = _goi(S.tu_choi, db, u, lo_id, data.ly_do)
        msg = f"Đã từ chối {lo.ma}"
    else:
        raise HTTPException(400, "Thao tác không hợp lệ")
    return {"message": msg, "lo": S.lo_out(db, lo, u, chi_tiet=True)}
