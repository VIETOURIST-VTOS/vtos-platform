"""Kết nối Zalo: (1) OA – nhắn khách đã quan tâm OA (user_id) qua Open API v3; (2) ZNS – gửi mẫu đã duyệt theo SĐT (84…);
(3) webhook OA nhận follow / tin nhắn / chia sẻ SĐT → tạo lead kênh 'Zalo OA'. Không có token → tin xếp 'chờ cấu hình' để gửi tay/sau."""
import json, hmac, hashlib, urllib.request, urllib.parse
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.crm import Lead, ZaloMessage
from app.services import rules as R

OA_API = "https://openapi.zalo.me/v3.0/oa"
ZNS_API = "https://business.openapi.zalo.me/message/template"
OAUTH = "https://oauth.zaloapp.com/v4/oa/access_token"


def norm_phone(p: str) -> str:
    d = "".join(ch for ch in str(p or "") if ch.isdigit())
    if d.startswith("84") and len(d) >= 11: d = "0" + d[2:]
    if len(d) == 9 and not d.startswith("0"): d = "0" + d
    return d[:15]


def intl(p: str) -> str:
    d = norm_phone(p)
    return "84" + d[1:] if d.startswith("0") else d


def configured() -> dict:
    return {"oa": bool(settings.ZALO_OA_ACCESS_TOKEN), "zns_templates": dict(x.split(":", 1) for x in settings.ZALO_ZNS_TEMPLATES.split(",") if ":" in x), "webhook": bool(settings.ZALO_OA_SECRET_KEY),
            "refresh": bool(settings.ZALO_OA_REFRESH_TOKEN and settings.ZALO_APP_SECRET)}


def _post(url: str, body: dict, token: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "access_token": token}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def refresh_token() -> str:
    """Đổi refresh token lấy access token mới (hết hạn 25 giờ). Trả access token hoặc ''."""
    if not (settings.ZALO_OA_REFRESH_TOKEN and settings.ZALO_APP_ID and settings.ZALO_APP_SECRET): return ""
    data = urllib.parse.urlencode({"refresh_token": settings.ZALO_OA_REFRESH_TOKEN, "app_id": settings.ZALO_APP_ID, "grant_type": "refresh_token"}).encode()
    req = urllib.request.Request(OAUTH, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "secret_key": settings.ZALO_APP_SECRET}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode())
    if j.get("access_token"):
        settings.ZALO_OA_ACCESS_TOKEN = j["access_token"]
        if j.get("refresh_token"): settings.ZALO_OA_REFRESH_TOKEN = j["refresh_token"]
    return settings.ZALO_OA_ACCESS_TOKEN


def send_oa_text(uid: str, text: str) -> dict:
    return _post(f"{OA_API}/message/cs", {"recipient": {"user_id": uid}, "message": {"text": text[:2000]}}, settings.ZALO_OA_ACCESS_TOKEN)


def send_zns(phone: str, template_id: str, params: dict) -> dict:
    return _post(ZNS_API, {"phone": intl(phone), "template_id": str(template_id), "template_data": params, "tracking_id": f"vtos-{datetime.now():%Y%m%d%H%M%S}"}, settings.ZALO_OA_ACCESS_TOKEN)


def queue(db: Session, actor: str, *, phone: str = "", zalo_uid: str = "", text: str = "", purpose: str = "", template: str = "", params: dict | None = None, lead_id: int | None = None, booking_id: int | None = None, send_now: bool = True) -> ZaloMessage:
    """Tạo tin và gửi ngay nếu có cấu hình: có uid → OA text; không có uid nhưng có mẫu ZNS cho mục đích → ZNS theo SĐT; còn lại → chờ cấu hình."""
    cfg = configured(); kind = "oa" if zalo_uid else "zns"
    tid = template or cfg["zns_templates"].get(purpose, "")
    m = ZaloMessage(kind=kind, phone=norm_phone(phone), zalo_uid=zalo_uid, lead_id=lead_id, booking_id=booking_id, template_id=tid, params=params or {}, text=text, purpose=purpose, created_by=actor,
                    status="cho_gui" if (cfg["oa"] and (zalo_uid or tid)) else "cho_cau_hinh")
    db.add(m); db.flush()
    if send_now and m.status == "cho_gui": _send(m)
    return m


def _send(m: ZaloMessage) -> None:
    try:
        r = send_oa_text(m.zalo_uid, m.text) if m.kind == "oa" else send_zns(m.phone, m.template_id, m.params)
        m.response = json.dumps(r, ensure_ascii=False)[:2000]
        ok = (r.get("error") in (0, None)) and not r.get("error_name")
        if not ok and r.get("error") in (-216, -124) and refresh_token():   # token hết hạn → làm mới và gửi lại 1 lần
            r = send_oa_text(m.zalo_uid, m.text) if m.kind == "oa" else send_zns(m.phone, m.template_id, m.params); ok = r.get("error") in (0, None); m.response = json.dumps(r, ensure_ascii=False)[:2000]
        m.status, m.sent_at = ("da_gui" if ok else "loi"), datetime.now()
    except Exception as ex:
        m.status, m.response = "loi", str(ex)[:500]


def send_pending(db: Session, limit: int = 100) -> dict:
    cfg = configured(); n = 0
    for m in db.execute(select(ZaloMessage).where(ZaloMessage.status.in_(["cho_gui", "cho_cau_hinh"])).order_by(ZaloMessage.id).limit(limit)).scalars():
        if not cfg["oa"]: break
        if m.kind == "zns" and not m.template_id: m.template_id = cfg["zns_templates"].get(m.purpose, "")
        if m.kind == "zns" and not m.template_id: continue
        _send(m); n += 1
    db.commit(); return {"sent": n}


def verify_signature(body: bytes, sig: str, ts: str) -> bool:
    if not settings.ZALO_OA_SECRET_KEY: return True
    mac = hashlib.sha256((settings.ZALO_APP_ID + body.decode() + ts + settings.ZALO_OA_SECRET_KEY).encode()).hexdigest()
    return hmac.compare_digest("mac=" + mac, sig or "") or hmac.compare_digest(mac, sig or "")


def on_webhook(db: Session, ev: dict) -> dict:
    """Sự kiện OA: follow → lead kênh Zalo OA (chưa có SĐT); user_send_text → cập nhật last_contact; user_submit_info (chia sẻ SĐT) → gắn SĐT vào lead."""
    name = ev.get("event_name") or ""; uid = str((ev.get("follower") or ev.get("sender") or {}).get("id") or ev.get("user_id") or "")
    if not uid: return {"ignored": True}
    if name in ("user_send_text", "user_send_image", "user_send_sticker"):
        try:
            from app.services import inbox as IB
            IB.inbound(db, "zalo", uid, (ev.get("message") or {}).get("text") or f"[{name}]", ext_msg_id=str((ev.get("message") or {}).get("msg_id") or ""))
        except Exception as ex: return {"inbox_error": str(ex)[:200]}
    lead = db.execute(select(Lead).where(Lead.zalo_uid == uid).order_by(Lead.id.desc())).scalars().first()
    month = f"{datetime.now():%Y-%m}"; out = {"event": name, "uid": uid}
    if name == "follow":
        if not lead:
            lead = Lead(phone=f"zalo{uid[-9:]}", name="", channel="Zalo OA", lead_month=month, zalo_uid=uid, zalo_follow=True, created_by="zalo"); db.add(lead); out["lead"] = "new"
        else: lead.zalo_follow = True
    elif name == "unfollow" and lead: lead.zalo_follow = False
    elif name in ("user_send_text", "user_send_image", "user_send_sticker"):
        if not lead:
            lead = Lead(phone=f"zalo{uid[-9:]}", channel="Zalo OA", lead_month=month, zalo_uid=uid, created_by="zalo"); db.add(lead); out["lead"] = "new"
        lead.last_contact_at = datetime.now()
        txt = (ev.get("message") or {}).get("text") or ""
        if txt: lead.note = (lead.note + "\n" if lead.note else "") + f"[{datetime.now():%d/%m %H:%M}] {txt[:300]}"
        ph = norm_phone("".join(ch for ch in txt if ch.isdigit()))
        if len(ph) == 10 and ph.startswith("0"): _attach_phone(db, lead, ph)
    elif name == "user_submit_info":
        info = ev.get("info") or {}; ph = norm_phone(info.get("phone") or "")
        if not lead:
            lead = Lead(phone=ph or f"zalo{uid[-9:]}", name=info.get("name") or "", channel="Zalo OA", lead_month=month, zalo_uid=uid, created_by="zalo"); db.add(lead); out["lead"] = "new"
        if ph: _attach_phone(db, lead, ph)
        if info.get("name") and not lead.name: lead.name = info["name"][:120]
    db.commit(); return out


def _attach_phone(db: Session, lead: Lead, ph: str) -> None:
    for other in db.execute(select(Lead).where(Lead.phone == ph, Lead.id != lead.id).order_by(Lead.id.desc())).scalars():
        if not other.zalo_uid: other.zalo_uid, other.zalo_follow = lead.zalo_uid, lead.zalo_follow
    dup = db.execute(select(Lead).where(Lead.phone == ph, Lead.lead_month == lead.lead_month, Lead.channel == lead.channel, Lead.id != lead.id)).scalars().first()
    if not dup: lead.phone = ph
