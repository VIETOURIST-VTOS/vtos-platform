"""API hộp thư đa kênh: webhook Facebook Messenger (Page công ty), danh sách hội thoại, tin nhắn, trả lời, AI gợi ý, bật/tắt AI, robot R12."""
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth
from app.core.config import settings
from app.models.core import User
from app.models.crm import Conversation, Message
from app.services import inbox as IB
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["inbox"])
ROLES = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "tgd", "chutich", "cntt", "tp_dh", "nv_dh", "bks")


class ReplyIn(BaseModel):
    text: str


class AssignIn(BaseModel):
    sales_id: int | None = None
    ai_off: bool | None = None
    status: str | None = None


class SimIn(BaseModel):
    channel: str = "web"
    external_id: str
    name: str = ""
    text: str


@router.get("/facebook/webhook")
def fb_verify(hub_mode: str = Query("", alias="hub.mode"), hub_verify_token: str = Query("", alias="hub.verify_token"), hub_challenge: str = Query("", alias="hub.challenge")):
    if hub_mode == "subscribe" and hub_verify_token == settings.FB_VERIFY_TOKEN: return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Sai verify token")


@router.post("/facebook/webhook")
async def fb_webhook(request: Request, db: Session = Depends(get_db), x_hub_signature_256: str | None = Header(default=None)):
    body = await request.body()
    if not IB.fb_verify_signature(body, x_hub_signature_256 or ""): raise HTTPException(401, "Sai chữ ký Facebook")
    import json
    try: payload = json.loads(body.decode() or "{}")
    except ValueError: raise HTTPException(400, "JSON không hợp lệ")
    if payload.get("object") not in ("page", None): return {"ignored": True}
    return IB.fb_webhook(db, payload)


@router.get("/inbox/status")
def status(u: User = Depends(require_roles(*ROLES)), db: Session = Depends(get_db)):
    cnt = dict(db.execute(select(Conversation.status, func.count()).group_by(Conversation.status)).all())
    return {"facebook": bool(settings.FB_PAGE_ACCESS_TOKEN), "facebook_page_id": settings.FB_PAGE_ID, "fb_webhook_url": "/api/v1/facebook/webhook", "fb_verify_token_set": bool(settings.FB_VERIFY_TOKEN),
            "zalo": bool(settings.ZALO_OA_ACCESS_TOKEN), "ai": bool(settings.ANTHROPIC_API_KEY), "ai_on": R.get_param(db, "ai_tra_loi_bat") >= 1, "sla_minutes": IB.sla_minutes(db), "working_hours": IB.working_hours(),
            "counts": cnt, "overdue": db.execute(select(func.count()).select_from(Conversation).where(Conversation.unanswered == True)).scalar()}


@router.get("/inbox")
def list_conv(status: str = "", channel: str = "", q: str = "", mine: bool = False, limit: int = 100, u: User = Depends(require_roles(*ROLES)), db: Session = Depends(get_db)):
    qs = select(Conversation).order_by(desc(Conversation.unanswered), desc(Conversation.updated_at))
    if status: qs = qs.where(Conversation.status == status)
    if channel: qs = qs.where(Conversation.channel == channel)
    if mine: qs = qs.where(Conversation.sales_id == u.id)
    if q:
        like = f"%{q.strip()}%"; qs = qs.where((Conversation.customer_name.ilike(like)) | (Conversation.phone.ilike(like)) | (Conversation.external_id.ilike(like)))
    return [IB.conv_out(c, db) for c in db.execute(qs.limit(min(limit, 500))).scalars()]


def _c(db: Session, cid: int) -> Conversation:
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Không có hội thoại")
    return c


@router.get("/inbox/{cid}")
def get_conv(cid: int, u: User = Depends(require_roles(*ROLES)), db: Session = Depends(get_db)):
    c = _c(db, cid)
    return {**IB.conv_out(c, db), "messages": [IB.msg_out(m) for m in db.execute(select(Message).where(Message.conversation_id == c.id).order_by(Message.at, Message.id)).scalars()]}


@router.post("/inbox/{cid}/reply")
def reply(cid: int, data: ReplyIn, u: User = Depends(require_roles("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "tp_dh", "nv_dh", "tgd", "cntt")), db: Session = Depends(get_db)):
    try: m = IB.reply(db, u, _c(db, cid), data.text)
    except ValueError as ex: raise HTTPException(422, str(ex))
    return {"message": "Đã gửi" if m.status == "da_gui" else f"Gửi lỗi: {m.response[:120]}", "msg": IB.msg_out(m)}


@router.post("/inbox/{cid}/ai-draft")
def ai_draft(cid: int, u: User = Depends(require_roles(*ROLES)), db: Session = Depends(get_db)):
    text, src = IB.draft_reply(db, _c(db, cid)); return {"text": text, "source": src}


@router.post("/inbox/{cid}/assign")
def assign(cid: int, data: AssignIn, u: User = Depends(require_roles("nv_kd", "tn_kd", "tp_kd", "gd_kd", "ptgd_mkt", "tp_dh", "tgd", "cntt")), db: Session = Depends(get_db)):
    c = _c(db, cid)
    if data.sales_id is not None: c.sales_id = data.sales_id or None
    if data.ai_off is not None: c.ai_off = data.ai_off
    if data.status in ("mo", "dong"): c.status = data.status; c.unanswered = False if data.status == "dong" else c.unanswered
    R.audit(db, u.username, u.role, "cap_nhat_hoi_thoai", f"conv:{c.id}", after=data.model_dump(exclude_none=True)); db.commit()
    return IB.conv_out(c, db)


@router.post("/inbox/simulate", status_code=201)
def simulate(data: SimIn, u: User = Depends(require_roles("cntt", "ptgd_mkt", "gd_kd", "tp_kd", "tgd")), db: Session = Depends(get_db)):
    """Giả lập tin khách (kênh web / kiểm thử) – dùng khi chưa nối Facebook."""
    m = IB.inbound(db, data.channel, data.external_id, data.text, name=data.name)
    return {"message": "Đã ghi nhận tin khách", "msg": IB.msg_out(m) if m else None}


@router.post("/inbox/check")
def check(u: User = Depends(require_roles("cntt", "ptgd_mkt", "gd_kd", "tp_kd", "tp_dh", "tgd")), db: Session = Depends(get_db)):
    return IB.robot_check(db)


@router.post("/robot/inbox/check", dependencies=[Depends(robot_auth)])
def robot_check(db: Session = Depends(get_db)):
    return IB.robot_check(db)
