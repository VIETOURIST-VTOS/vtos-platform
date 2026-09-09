"""API CRM: lead (nhập Excel/tay, danh sách, phân công, ghi chú), thống kê kênh × tháng, báo cáo lead & chuyển đổi (+Excel), Zalo (OA/ZNS, webhook, nhật ký)."""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Header, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth
from app.models.core import User, Booking
from app.models.crm import Lead, LeadChannelStat, ZaloMessage, LEAD_CHANNELS, LEAD_STATUS
from app.services import leads as L
from app.services import access as AC
from app.services import zalo as Z
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["crm"])
CRM_ROLES = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "tgd", "chutich", "cntt", "tp_dh", "nv_dh", "bks", "hcns")
EDIT_ROLES = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "cntt", "tgd")


class LeadIn(BaseModel):
    phone: str
    name: str = ""
    channel: str = "Khác"
    lead_month: str = ""
    received_at: str | None = None
    campaign: str = ""
    interest: str = ""
    note: str = ""
    sales_id: int | None = None
    status: str | None = None


class LeadPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    note: str | None = None
    sales_id: int | None = None
    interest: str | None = None


class StatIn(BaseModel):
    lead_month: str
    channel: str
    leads: int
    cost: float | None = None


class ZaloSendIn(BaseModel):
    text: str = ""
    purpose: str = "cham_soc"
    template_id: str = ""
    params: dict = {}
    phone: str = ""
    lead_id: int | None = None
    booking_id: int | None = None


@router.get("/leads/meta")
def meta(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"channels": LEAD_CHANNELS, "status": LEAD_STATUS, "zalo": Z.configured(db)}


@router.get("/leads")
def list_leads(month: str = "", channel: str = "", status: str = "", q: str = "", mine: bool = False, limit: int = 300, u: User = Depends(require_roles(*CRM_ROLES)), db: Session = Depends(get_db)):
    qs = select(Lead).order_by(desc(Lead.received_at), desc(Lead.id))
    if month: qs = qs.where(Lead.lead_month == month)
    if channel: qs = qs.where(Lead.channel == channel)
    if status: qs = qs.where(Lead.status == status)
    vis = AC.sales_ids_visible(db, u)
    if mine: qs = qs.where(Lead.sales_id == u.id)
    elif vis is not None: qs = qs.where(Lead.sales_id.in_(vis))   # NV KD: lead của mình; trưởng nhóm: của nhóm
    if q:
        like = f"%{q.strip()}%"; qs = qs.where((Lead.phone.ilike(like)) | (Lead.name.ilike(like)) | (Lead.interest.ilike(like)))
    rows = list(db.execute(qs.limit(min(limit, 2000))).scalars())
    cnt = dict(db.execute(select(Lead.status, func.count()).where(Lead.lead_month == month if month else True).group_by(Lead.status)).all())
    return {"rows": [L.lead_out(l, db) for l in rows], "counts": cnt}


@router.post("/leads", status_code=201)
def create_lead(data: LeadIn, u: User = Depends(require_roles(*EDIT_ROLES)), db: Session = Depends(get_db)):
    try: l, new = L.upsert_lead(db, u.username, data.model_dump())
    except ValueError as ex: raise HTTPException(422, str(ex))
    if not l.sales_id and u.role == "nv_kd": l.sales_id = u.id
    R.audit(db, u.username, u.role, "tao_lead" if new else "cap_nhat_lead", f"lead:{l.phone}", after={"kenh": l.channel, "thang": l.lead_month}); db.commit()
    return {"lead": L.lead_out(l, db), "message": ("Đã tạo lead " if new else "Đã cập nhật lead ") + l.phone}


@router.post("/leads/import")
async def import_leads(file: UploadFile = File(...), default_month: str = "", u: User = Depends(require_roles(*EDIT_ROLES)), db: Session = Depends(get_db)):
    data = await file.read()
    if not file.filename.lower().endswith((".xlsx", ".xlsm")): raise HTTPException(422, "Chỉ nhận tệp Excel .xlsx")
    out = L.import_xlsx(db, u.username, data, default_month)
    return {**out, "message": f"Nhập {out['rows']} dòng: {out['new']} lead mới, {out['updated']} cập nhật, {out['stats']} dòng thống kê kênh" + (f", {out['n_errors']} lỗi" if out["n_errors"] else "")}


@router.put("/leads/{lid}")
def patch_lead(lid: int, data: LeadPatch, u: User = Depends(require_roles(*EDIT_ROLES)), db: Session = Depends(get_db)):
    l = db.get(Lead, lid)
    if not l: raise HTTPException(404, "Không có lead")
    vis = AC.sales_ids_visible(db, u)
    if vis is not None and l.sales_id not in (None, *vis): raise HTTPException(403, "Lead của sale khác nhóm")
    d = data.model_dump(exclude_none=True)
    if "status" in d and d["status"] not in LEAD_STATUS: raise HTTPException(422, "Trạng thái không hợp lệ")
    for k, v in d.items(): setattr(l, k, v)
    if "note" in d or "status" in d: l.last_contact_at = __import__("datetime").datetime.now()
    R.audit(db, u.username, u.role, "cap_nhat_lead", f"lead:{l.phone}", after=d); db.commit()
    return L.lead_out(l, db)


@router.post("/leads/match")
def match(months: str = "", u: User = Depends(require_roles(*EDIT_ROLES, "tp_dh")), db: Session = Depends(get_db)):
    return L.match_conversions(db, months.split(",") if months else None)


@router.get("/leads/stats")
def stats(month: str = "", u: User = Depends(require_roles(*CRM_ROLES)), db: Session = Depends(get_db)):
    qs = select(LeadChannelStat).order_by(LeadChannelStat.lead_month, LeadChannelStat.channel)
    if month: qs = qs.where(LeadChannelStat.lead_month == month)
    return [{"id": s.id, "lead_month": s.lead_month, "channel": s.channel, "leads": s.leads, "cost": s.cost, "updated_by": s.updated_by} for s in db.execute(qs).scalars()]


@router.post("/leads/stats")
def set_stats(data: list[StatIn], u: User = Depends(require_roles(*EDIT_ROLES)), db: Session = Depends(get_db)):
    for s in data: L.set_stat(db, u.username, L.month_of(s.lead_month), L.canon_channel(s.channel), s.leads, s.cost)
    R.audit(db, u.username, u.role, "nhap_thong_ke_lead", "crm", after={"dong": len(data)}); db.commit()
    return {"message": f"Đã lưu {len(data)} dòng thống kê kênh × tháng"}


@router.get("/leads/conversion")
def conversion(month: str, lead_months: str = "", u: User = Depends(require_roles(*CRM_ROLES)), db: Session = Depends(get_db)):
    return L.conversion_report(db, month, lead_months.split(",") if lead_months else None)


@router.get("/leads/conversion/xlsx")
def conversion_xlsx(month: str, lead_months: str = "", u: User = Depends(require_roles(*CRM_ROLES)), db: Session = Depends(get_db)):
    data = L.to_xlsx(L.conversion_report(db, month, lead_months.split(",") if lead_months else None))
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=VTOS_Lead_Chuyen_doi_{month}.xlsx"})


# ---------- Zalo ----------
@router.get("/zalo/status")
def zalo_status(u: User = Depends(require_roles(*CRM_ROLES, "ketoan")), db: Session = Depends(get_db)):
    cnt = dict(db.execute(select(ZaloMessage.status, func.count()).group_by(ZaloMessage.status)).all())
    return {**Z.configured(db), "messages": cnt, "webhook_url": "/api/v1/zalo/webhook"}


@router.post("/zalo/send", status_code=201)
def zalo_send(data: ZaloSendIn, u: User = Depends(require_roles(*EDIT_ROLES, "tp_dh", "nv_dh", "ketoan")), db: Session = Depends(get_db)):
    lead = db.get(Lead, data.lead_id) if data.lead_id else None
    bk = db.get(Booking, data.booking_id) if data.booking_id else None
    phone = data.phone or (lead.phone if lead else "") or (bk.customer_phone if bk else "")
    uid = lead.zalo_uid if lead else ""
    if not uid and phone:
        other = db.execute(select(Lead).where(Lead.phone == Z.norm_phone(phone), Lead.zalo_uid != "")).scalars().first()
        if other: uid = other.zalo_uid
    if not (phone or uid): raise HTTPException(422, "Thiếu SĐT / lead / booking")
    if not data.text and not data.template_id and data.purpose not in Z.configured(db)["zns_templates"]: raise HTTPException(422, "Thiếu nội dung tin (hoặc mẫu ZNS cho mục đích này)")
    m = Z.queue(db, u.username, phone=phone, zalo_uid=uid, text=data.text, purpose=data.purpose, template=data.template_id, params=data.params, lead_id=data.lead_id, booking_id=data.booking_id)
    if lead: lead.last_contact_at = m.created_at
    R.audit(db, u.username, u.role, "gui_zalo", f"zalo:{m.id}", after={"kenh": m.kind, "sdt": m.phone[-4:], "muc_dich": m.purpose, "trang_thai": m.status}); db.commit()
    msg = {"da_gui": "Đã gửi Zalo", "loi": "Gửi lỗi – xem phản hồi", "cho_cau_hinh": "Đã xếp hàng – chưa cấu hình Zalo OA/ZNS (CNTT dán token vào Render)", "cho_gui": "Đang chờ gửi"}[m.status]
    return {"id": m.id, "status": m.status, "kind": m.kind, "response": m.response, "message": msg}


@router.get("/zalo/messages")
def zalo_messages(status: str = "", limit: int = 100, u: User = Depends(require_roles(*CRM_ROLES, "ketoan")), db: Session = Depends(get_db)):
    qs = select(ZaloMessage).order_by(desc(ZaloMessage.id))
    if status: qs = qs.where(ZaloMessage.status == status)
    return [{"id": m.id, "kind": m.kind, "phone": m.phone, "zalo_uid": m.zalo_uid, "purpose": m.purpose, "template_id": m.template_id, "text": m.text, "status": m.status, "response": m.response[:200], "created_by": m.created_by, "created_at": m.created_at, "sent_at": m.sent_at, "lead_id": m.lead_id, "booking_id": m.booking_id}
            for m in db.execute(qs.limit(min(limit, 500))).scalars()]


@router.post("/zalo/send-pending")
def zalo_send_pending(u: User = Depends(require_roles("cntt", "ptgd_mkt", "gd_kd", "tp_kd", "tgd")), db: Session = Depends(get_db)):
    return Z.send_pending(db)


@router.post("/robot/zalo/send-pending", dependencies=[Depends(robot_auth)])
def robot_zalo_send_pending(db: Session = Depends(get_db)):
    return Z.send_pending(db)


# ---------- Uỷ quyền OA: một lần, do người có quyền quản trị OA bấm ----------
UY_QUYEN_ROLES = ("cntt", "tgd", "chutich")


@router.post("/zalo/uy-quyen/bat-dau")
def zalo_uy_quyen_bat_dau(u: User = Depends(require_roles(*UY_QUYEN_ROLES)), db: Session = Depends(get_db)):
    """Trả về đường dẫn để người quản trị OA bấm Đồng ý trên Zalo.

    KHÔNG tự mở, KHÔNG tự đồng ý: cấp quyền cho một ứng dụng dùng OA của công ty là việc của người.
    """
    duong, ma = Z.duong_uy_quyen(db, u.username)
    R.audit(db, u.username, u.role, "zalo_uy_quyen_bat_dau", "zalo_oa", after={"ma_chong_gia": ma[:8] + "…"})
    db.commit()
    return {"url": duong, "huong_dan": "Mở đường dẫn này bằng tài khoản Zalo có quyền quản trị OA, bấm Đồng ý. "
                                       "Zalo sẽ tự gọi ngược về VTOS và lưu token."}


@router.get("/zalo/uy-quyen/tra-ve")
def zalo_uy_quyen_tra_ve(code: str = "", state: str = "", oa_id: str = "", db: Session = Depends(get_db)):
    """Zalo gọi vào đây sau khi người quản trị bấm Đồng ý. KHÔNG có đăng nhập – nên phải kiểm mã chống giả mạo.

    Thiếu bước kiểm đó thì bất kỳ ai gọi đúng đường dẫn này cũng đặt được token cho hệ thống.
    """
    if not code: raise HTTPException(400, "Thiếu mã uỷ quyền")
    if not Z.kiem_ma_chong_gia(db, state):
        raise HTTPException(403, "Mã chống giả mạo không khớp – hãy bấm 'Bắt đầu uỷ quyền' trong VTOS rồi làm lại")
    try:
        kq = Z.doi_ma_uy_quyen(db, code, boi="uy_quyen_oa")
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if oa_id:
        Z.kho(db).oa_id = oa_id[:40]; db.commit()
    R.audit(db, "zalo", "he_thong", "zalo_uy_quyen_xong", "zalo_oa", after={"oa_id": oa_id, **kq})
    db.commit()
    return {"message": "Đã nhận quyền Zalo OA. Hộp thư đa kênh bắt đầu nhận tin khách nhắn vào OA.", **kq}


# Zalo bắt xác thực quyền sở hữu TIỀN TỐ URL (không chỉ domain) trước khi nhận redirect_uri của luồng cấp
# quyền OA. Tiền tố ấy là /api/v1/zalo/ – nằm ở máy chủ chứ không ở giao diện, nên tệp xác thực phải do
# chính máy chủ trả. Chuỗi dưới đây KHÔNG phải bí mật: Zalo cấp công khai cho mỗi ứng dụng để chứng minh
# quyền sở hữu, và bản sao của nó đã nằm trong web/public từ lần xác thực domain.
ZALO_VERIFIER = "VyIH6BJWInypriytmjXq6m7usaBjZW0KE3Gs"


@router.get("/zalo/zalo_verifier{ma}.html", include_in_schema=False)
def zalo_verifier(ma: str):
    """Tệp Zalo tải về để đối chiếu. Trả đúng chuỗi của ứng dụng này, không phải chuỗi trên đường dẫn –
    trả lại thứ người gọi đưa vào thì bất kỳ ứng dụng nào cũng xác thực được tiền tố URL của công ty."""
    if ma != ZALO_VERIFIER:
        raise HTTPException(404, "Không có tệp này")
    return Response(content=ZALO_VERIFIER, media_type="text/html")


@router.get("/zalo/webhook")
def zalo_webhook_verify():
    return {"ok": True, "service": "VTOS Zalo OA webhook"}


@router.post("/zalo/webhook")
async def zalo_webhook(request: Request, db: Session = Depends(get_db), x_zevent_signature: str | None = Header(default=None)):
    body = await request.body()
    try: ev = __import__("json").loads(body.decode() or "{}")
    except ValueError: raise HTTPException(400, "JSON không hợp lệ")
    if not Z.verify_signature(body, x_zevent_signature or "", str(ev.get("timestamp") or "")): raise HTTPException(401, "Sai chữ ký Zalo")
    return Z.on_webhook(db, ev)


# ============================ TỔNG ĐÀI – NGHE TRƯỚC, HIỂU SAU ============================
# P.A Việt Nam có bốn API tổng đài nhưng không công bố đặc tả. Hai đường dẫn dưới đây KHÔNG diễn giải
# gì cả: một đầu nhận ghi nguyên văn, một đầu đọc để người viết phần diễn giải nhìn thấy dữ liệu thật.
# Xem ghi chú đầy đủ ở app/services/tong_dai.py.
@router.api_route("/tong-dai/cuoc-goi/{ma}", methods=["GET", "POST"])
async def tong_dai_nhan(ma: str, request: Request, nguon: str = "pavietnam",
                        db: Session = Depends(get_db)):
    """Đầu nhận công khai – tổng đài không gửi được chuỗi đăng nhập của VTOS, nên khoá nằm ở đường dẫn.

    Trả 200 kể cả khi ghi hỏng: nhà cung cấp thường TẮT webhook sau vài lần nhận mã lỗi, và mất webhook
    thì mất luôn cơ hội nhìn thấy giao thức. Lỗi ghi thì báo qua nhật ký kỹ thuật, không báo ra ngoài.
    """
    from app.services import tong_dai as TD
    if not TD.kiem_ma(ma):
        raise HTTPException(404, "Not Found")     # 404 chứ không 403: không xác nhận đường dẫn có tồn tại
    try:
        than = (await request.body()).decode("utf-8", "replace")
    except Exception:
        than = ""
    try:
        TD.ghi(db, nguon=nguon, phuong_thuc=request.method, duong_dan=str(request.url.path),
               chuoi_truy_van=str(request.url.query), than=than,
               dau_muc=dict(request.headers), ip=(request.client.host if request.client else ""))
        db.commit()
    except Exception:
        db.rollback()
    return {"ok": True}


@router.get("/tong-dai/su-kien")
def tong_dai_su_kien(limit: int = 50, nguon: str = "",
                     u: User = Depends(require_roles("cntt", "tgd", "chutich", "bks")),
                     db: Session = Depends(get_db)):
    """Tổng đài thật sự gửi gì sang. `khoa_thay` là đặc tả dựng lại từ quan sát – thứ nhà cung cấp không đưa."""
    from app.services import tong_dai as TD
    return TD.bang(db, limit, nguon)
