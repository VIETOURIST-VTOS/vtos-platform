"""API dịch vụ lẻ – Non-package: tạo/sửa, danh sách + tổng hợp theo loại, in phiếu, chốt tháng (hủy dùng /bookings/{id}/cancel)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, Booking, SERVICE_KINDS
from app.services import nonpackage as NP
from app.services import access as AC

router = APIRouter(prefix="/api/v1", tags=["non-package"])


class NPIn(BaseModel):
    service_type: str = "OTHER"
    description: str = ""
    country: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    source: str = ""
    note: str = ""
    pax: int = 1
    amount: float | None = None
    discount: float | None = None
    cost_amount: float | None = None
    supplier_name: str = ""
    service_date: str | None = None
    sales_id: int | None = None
    counts_for_target: bool = True


class NPEdit(BaseModel):
    service_type: str | None = None
    description: str | None = None
    country: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    amount: float | None = None
    cost_amount: float | None = None
    supplier_name: str | None = None
    service_date: str | None = None


class MonthIn(BaseModel):
    month: str   # YYYY-MM


def _b(db: Session, bid: int) -> Booking:
    b = db.get(Booking, bid)
    if not b or not b.tour or b.tour.tour_type != "non_package": raise HTTPException(404, "Không có dịch vụ lẻ")
    return b


@router.get("/non-package")
def list_np(month: str = "", service_type: str = "", paid: str = "", q: str = "", limit: int = 500, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="dịch vụ lẻ")), db: Session = Depends(get_db)):
    rows = NP.list_rows(db, month, service_type, paid, q, min(limit, 2000))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: rows = [b for b in rows if b.sales_id in vis]
    return {"kinds": SERVICE_KINDS, "rows": [NP.row(b) for b in rows], "summary": NP.summary(rows)}


# KS-2: ba cửa dưới đây khai quyền ở THÂN HÀM còn chữ ký để trống, nên bộ kiểm quyền đọc ra "ai
# đăng nhập cũng gọi được". Người bị từ chối vẫn nhận 403, nhưng bản khai quyền nói sai — và bản
# khai sai là thứ người ta dùng để trả lời câu "ai làm được việc này".
@router.post("/non-package", status_code=201)
def create_np(data: NPIn, u: User = Depends(require_roles(*NP.CREATE_ROLES, mo_ta="tạo dịch vụ lẻ")), db: Session = Depends(get_db)):
    t, b = NP.create(db, u, data.model_dump())
    return {"row": NP.row(b), "message": f"Đã tạo dịch vụ lẻ {t.code} – booking {b.code} ({b.amount:,.0f} đ)"}


@router.put("/non-package/{bid}")
def edit_np(bid: int, data: NPEdit, u: User = Depends(require_roles(*NP.SUA_ROLES, mo_ta="sửa dịch vụ lẻ")), db: Session = Depends(get_db)):
    return NP.row(NP.update(db, u, _b(db, bid), data.model_dump(exclude_none=True)))


@router.get("/non-package/{bid}/print", response_class=HTMLResponse)
def print_np(bid: int, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="in phiếu dịch vụ lẻ")), db: Session = Depends(get_db)):
    return HTMLResponse(NP.print_html(_b(db, bid)))


@router.post("/non-package/close-month")
def close_month(data: MonthIn, u: User = Depends(require_roles(*NP.CHOT_THANG_ROLES, mo_ta="chốt dịch vụ lẻ tháng")), db: Session = Depends(get_db)):
    return NP.close_month(db, u, data.month)
