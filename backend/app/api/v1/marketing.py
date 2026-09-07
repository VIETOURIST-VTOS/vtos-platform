"""API Chiến dịch marketing (Đợt 1). Nhân viên Marketing hoặc AI đều điền cùng một biểu mẫu này."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, Product
from app.models.marketing import Campaign, CAMPAIGN_STATUS, MUC_TIEU, KENH, KENH_TEN
from app.services import marketing as MK
from app.services import rules as R
from app.services import ai_log as AL

router = APIRouter(prefix="/api/v1", tags=["marketing"])
XEM = ("ptgd_mkt", "nv_mkt", "chutich", "tgd", "gd_kd", "ketoan", "cntt", "bks")
LAP = ("ptgd_mkt", "nv_mkt", "cntt")


def out(db: Session, c: Campaign, kem_ket_qua: bool = True) -> dict:
    sp = db.get(Product, c.product_id) if c.product_id else None
    u = db.get(User, c.owner_id) if c.owner_id else None
    d = {"id": c.id, "code": c.code, "name": c.name, "objective": c.objective,
         "objective_ten": MUC_TIEU.get(c.objective, c.objective), "product_id": c.product_id,
         "san_pham": sp.name if sp else "", "mang": c.mang, "channels": c.channels or [],
         "kenh_ten": [KENH_TEN.get(k, k) for k in (c.channels or [])],
         "from_date": c.from_date, "to_date": c.to_date, "budget": c.budget,
         "target_leads": c.target_leads, "target_bookings": c.target_bookings,
         "owner_id": c.owner_id, "phu_trach": u.full_name if u else "", "company_id": c.company_id,
         "status": c.status, "status_ten": CAMPAIGN_STATUS.get(c.status, c.status),
         "evaluation": c.evaluation, "note": c.note, "nguon_tao": c.nguon_tao, "ai_ghi_chu": c.ai_ghi_chu,
         "created_by": c.created_by, "created_at": c.created_at,
         "approved_by": c.approved_by, "approved_at": c.approved_at,
         "chuyen_duoc": list(MK.CHUYEN.get(c.status, ()))}
    if kem_ket_qua: d["ket_qua"] = MK.ket_qua(db, c)
    return d


@router.get("/marketing/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return {"muc_tieu": MUC_TIEU, "kenh": KENH_TEN, "trang_thai": CAMPAIGN_STATUS,
            "mang": {"le": "Kinh doanh Lẻ", "doan": "Kinh doanh Đoàn (MICE)"}}


@router.get("/marketing/campaigns")
def danh_sach(status: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(Campaign).order_by(desc(Campaign.id))
    if status: q = q.where(Campaign.status == status)
    return [out(db, c) for c in db.execute(q).scalars()]


@router.get("/marketing/campaigns/lead-chua-gan")
def lead_chua_gan(thang: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Lead chưa gắn chiến dịch, gom theo ô chữ cũ. Hệ thống KHÔNG tự đoán chiến dịch cho lead cũ."""
    return MK.lead_chua_gan(db, thang)


@router.get("/marketing/campaigns/{cid}")
def chi_tiet(cid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    c = db.get(Campaign, cid)
    if not c: raise HTTPException(404, "Không có chiến dịch")
    return out(db, c)


class CampaignIn(BaseModel):
    name: str
    objective: str
    product_id: int | None = None
    mang: str = "le"
    channels: list[str] = []
    from_date: date
    to_date: date | None = None
    budget: float = 0
    target_leads: int = 0
    target_bookings: int = 0
    owner_id: int | None = None
    company_id: int | None = None
    note: str = ""
    # "ai": bản do trợ lý AI soạn. Luôn dừng ở nháp và bắt buộc ghi căn cứ.
    nguon_tao: str = "nguoi"
    ai_ghi_chu: str = ""


@router.post("/marketing/campaigns", status_code=201)
def tao(data: CampaignIn, u: User = Depends(require_roles(*LAP)), db: Session = Depends(get_db)):
    try:
        c = MK.tao(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if c.nguon_tao == "ai":
        AL.ghi(db, tac_vu="vb_noi_bo", muc=2, nguon="tro_ly", vai_tro=u.role, nguoi=u.username,
               ref=f"campaign:{c.code}", ket_qua=f"Đề xuất chiến dịch {c.code} – {c.name}",
               trang_thai="cho_hau_kiem")
        db.commit()
    return {"campaign": out(db, c), "message":
            f"Đã lập chiến dịch {c.code} ở trạng thái Nháp"
            + (" – đề xuất do AI soạn, cần người có thẩm quyền xem lại và duyệt" if c.nguon_tao == "ai" else "")}


class SuaIn(BaseModel):
    name: str | None = None
    objective: str | None = None
    product_id: int | None = None
    mang: str | None = None
    channels: list[str] | None = None
    from_date: date | None = None
    to_date: date | None = None
    budget: float | None = None
    target_leads: int | None = None
    target_bookings: int | None = None
    owner_id: int | None = None
    company_id: int | None = None
    note: str | None = None
    evaluation: str | None = None


@router.put("/marketing/campaigns/{cid}")
def sua(cid: int, data: SuaIn, u: User = Depends(require_roles(*LAP, "tgd", "chutich")), db: Session = Depends(get_db)):
    c = db.get(Campaign, cid)
    if not c: raise HTTPException(404, "Không có chiến dịch")
    if c.status in ("ket_thuc", "da_danh_gia") and set(data.model_dump(exclude_unset=True)) - {"evaluation", "note"}:
        raise HTTPException(422, "Chiến dịch đã kết thúc – chỉ còn sửa được đánh giá và ghi chú")
    d = data.model_dump(exclude_unset=True)
    truoc = {k: str(getattr(c, k)) for k in d}
    for k, v in d.items(): setattr(c, k, v)
    try:
        MK.kiem_du_lieu({"objective": c.objective, "mang": c.mang, "channels": c.channels,
                         "product_id": c.product_id, "budget": c.budget, "target_leads": c.target_leads,
                         "target_bookings": c.target_bookings, "from_date": c.from_date, "to_date": c.to_date})
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "sua_chien_dich", f"campaign:{c.code}", before=truoc,
            after=data.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return {"campaign": out(db, c), "message": f"Đã cập nhật chiến dịch {c.code}"}


class ChuyenIn(BaseModel):
    status: str
    danh_gia: str = ""


@router.post("/marketing/campaigns/{cid}/chuyen-trang-thai")
def chuyen(cid: int, data: ChuyenIn, u: User = Depends(require_roles(*LAP, "ptgd_mkt", "tgd", "chutich")),
           db: Session = Depends(get_db)):
    c = db.get(Campaign, cid)
    if not c: raise HTTPException(404, "Không có chiến dịch")
    try:
        c = MK.chuyen_trang_thai(db, u, c, data.status, data.danh_gia)
    except PermissionError as ex:
        raise HTTPException(403, str(ex))
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"campaign": out(db, c), "message": f"Chiến dịch {c.code} → {CAMPAIGN_STATUS[c.status]}"}


class GanLeadIn(BaseModel):
    campaign_cu: str = ""       # gán theo ô chữ campaign cũ
    lead_ids: list[int] = []
    thang: str = ""


@router.post("/marketing/campaigns/{cid}/gan-lead")
def gan_lead(cid: int, data: GanLeadIn, u: User = Depends(require_roles(*LAP)), db: Session = Depends(get_db)):
    """Gán lead cũ vào chiến dịch – theo danh sách id, hoặc theo đúng ô chữ campaign cũ.

    Chỉ chạm lead CHƯA có chiến dịch. Gán đè lên lead đã gắn là làm sai số liệu của chiến dịch kia.
    """
    from app.models.crm import Lead
    from sqlalchemy import update
    c = db.get(Campaign, cid)
    if not c: raise HTTPException(404, "Không có chiến dịch")
    if not data.lead_ids and not data.campaign_cu:
        raise HTTPException(422, "Phải chọn danh sách lead hoặc nêu ô chữ chiến dịch cũ")
    q = update(Lead).where(Lead.campaign_id.is_(None))
    if data.lead_ids: q = q.where(Lead.id.in_(data.lead_ids))
    if data.campaign_cu: q = q.where(Lead.campaign == data.campaign_cu)
    if data.thang: q = q.where(Lead.lead_month == data.thang)
    n = db.execute(q.values(campaign_id=cid)).rowcount or 0
    R.audit(db, u.username, u.role, "gan_lead_vao_chien_dich", f"campaign:{c.code}",
            after={"so_lead": n, "theo_o_chu_cu": data.campaign_cu, "thang": data.thang})
    db.commit()
    return {"da_gan": n, "message": f"Đã gán {n} lead vào chiến dịch {c.code}"}


# ---------- Đợt 2: Kế hoạch & ngân sách ----------
from app.models.marketing import MarketingBudget, MarketingBudgetLine, HANG_MUC, BUDGET_STATUS


def b_out(db: Session, b: MarketingBudget, kem_bang: bool = True) -> dict:
    d = {"id": b.id, "period": b.period, "company_id": b.company_id, "target_leads": b.target_leads,
         "target_revenue": b.target_revenue, "rationale": b.rationale, "status": b.status,
         "status_ten": BUDGET_STATUS.get(b.status, b.status), "nguon_tao": b.nguon_tao,
         "ai_ghi_chu": b.ai_ghi_chu, "created_by": b.created_by, "created_at": b.created_at,
         "approved_by": b.approved_by, "approved_at": b.approved_at,
         "lines": [{"hang_muc": l.hang_muc, "ten": HANG_MUC.get(l.hang_muc, l.hang_muc),
                    "amount": l.amount, "note": l.note}
                   for l in db.execute(select(MarketingBudgetLine).where(MarketingBudgetLine.budget_id == b.id)).scalars()]}
    if kem_bang: d["bang"] = MK.bang_ngan_sach(db, b)
    return d


@router.get("/marketing/budgets")
def ds_ngan_sach(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return [b_out(db, b) for b in db.execute(select(MarketingBudget).order_by(desc(MarketingBudget.id))).scalars()]


@router.get("/marketing/budgets/hang-muc")
def ds_hang_muc(u: User = Depends(require_roles(*XEM, "nv_dh", "tp_dh"))):
    return HANG_MUC


@router.get("/marketing/budgets/{bid}")
def chi_tiet_ngan_sach(bid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    b = db.get(MarketingBudget, bid)
    if not b: raise HTTPException(404, "Không có ngân sách")
    return b_out(db, b)


class DongIn(BaseModel):
    hang_muc: str
    amount: float
    note: str = ""


class BudgetIn(BaseModel):
    period: str
    company_id: int | None = None
    target_leads: int = 0
    target_revenue: float = 0
    rationale: str = ""
    lines: list[DongIn] = []
    nguon_tao: str = "nguoi"
    ai_ghi_chu: str = ""


@router.post("/marketing/budgets", status_code=201)
def tao_ngan_sach(data: BudgetIn, u: User = Depends(require_roles(*LAP)), db: Session = Depends(get_db)):
    try:
        b = MK.tao_ngan_sach(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if b.nguon_tao == "ai":
        AL.ghi(db, tac_vu="vb_noi_bo", muc=2, nguon="tro_ly", vai_tro=u.role, nguoi=u.username,
               ref=f"mkt_budget:{b.id}", ket_qua=f"Đề xuất ngân sách marketing kỳ {b.period}",
               trang_thai="cho_hau_kiem")
        db.commit()
    return {"budget": b_out(db, b), "message":
            f"Đã lập ngân sách marketing kỳ {b.period} ở trạng thái Nháp"
            + (" – đề xuất do AI soạn, cần người có thẩm quyền duyệt" if b.nguon_tao == "ai" else "")}


@router.post("/marketing/budgets/{bid}/trinh")
def trinh(bid: int, u: User = Depends(require_roles(*LAP)), db: Session = Depends(get_db)):
    b = db.get(MarketingBudget, bid)
    if not b: raise HTTPException(404, "Không có ngân sách")
    if b.status != "nhap": raise HTTPException(422, "Chỉ trình được bản đang ở Nháp")
    b.status = "cho_duyet"
    R.audit(db, u.username, u.role, "trinh_ngan_sach_marketing", f"mkt_budget:{b.id}", after={"ky": b.period})
    db.commit()
    return {"budget": b_out(db, b), "message": f"Đã trình ngân sách kỳ {b.period}"}


@router.post("/marketing/budgets/{bid}/duyet")
def duyet(bid: int, u: User = Depends(require_roles("tgd", "chutich")), db: Session = Depends(get_db)):
    b = db.get(MarketingBudget, bid)
    if not b: raise HTTPException(404, "Không có ngân sách")
    if b.status != "cho_duyet": raise HTTPException(422, "Chỉ duyệt được bản đang chờ duyệt")
    try:
        b = MK.duyet_ngan_sach(db, u, b)
    except PermissionError as ex:
        raise HTTPException(403, str(ex))
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"budget": b_out(db, b), "message": f"Ngân sách kỳ {b.period} đã có hiệu lực"}
