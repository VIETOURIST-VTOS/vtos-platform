"""Hộp thư đa kênh + robot R12: nhận tin khách từ Facebook Messenger (Page công ty) / Zalo OA / web, gắn lead & sale, đồng hồ SLA;
sale trả lời từ VTOS; AI (Claude) trả lời thay khi sale trễ hạn, dựa trên dữ liệu VTOS (sản phẩm, lịch khởi hành, chỗ còn, chính sách cọc/hủy);
AI chấm câu trả lời của sale (sai giá, hứa giảm giá, thiếu thông tin). Không có ANTHROPIC_API_KEY → trả lời mẫu theo quy tắc."""
import json, hmac, hashlib, urllib.request, urllib.parse
from datetime import datetime, date, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.core import User, Tour, Product, Alert
from app.models.crm import Conversation, Message, Lead
from app.services import rules as R
from app.services import ai_log as AL
from app.services.zalo import norm_phone

GRAPH = "https://graph.facebook.com/v19.0"
AI_POLICY = ("Bạn là trợ lý tư vấn của Công ty CP Du lịch Vietourist (Vietourist Holdings). Trả lời ngắn gọn, lịch sự, tiếng Việt, xưng 'em' – gọi khách 'anh/chị'. "
             "CHỈ dùng thông tin trong DỮ LIỆU VTOS bên dưới: tên tour, ngày khởi hành, giá công bố, số chỗ còn, chính sách cọc/hủy. Không tự giảm giá, không hứa mã khuyến mãi, không cam kết ngoài dữ liệu. "
             "Nếu khách hỏi điều không có trong dữ liệu hoặc muốn đặt chỗ: xin tên + số điện thoại và nói tư vấn viên sẽ liên hệ trong ít phút. Kết thúc bằng 1 câu hỏi để tiếp tục cuộc trò chuyện. Tối đa 120 từ.")


# ---------- tiện ích ----------
def working_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now(); return 8 <= now.hour < 21


def sla_minutes(db: Session, now: datetime | None = None) -> int:
    return int(R.get_param(db, "sla_tra_loi_chat_phut" if working_hours(now) else "sla_tra_loi_ngoai_gio_phut"))


def get_or_create(db: Session, channel: str, external_id: str, page_id: str = "", name: str = "") -> Conversation:
    c = db.execute(select(Conversation).where(Conversation.channel == channel, Conversation.external_id == external_id)).scalars().first()
    if not c:
        c = Conversation(channel=channel, external_id=external_id, page_id=page_id, customer_name=name[:120]); db.add(c); db.flush()
        lead = db.execute(select(Lead).where(Lead.zalo_uid == external_id)).scalars().first() if channel == "zalo" else None
        if not lead:
            lead = Lead(phone=f"{channel[:2]}{external_id[-10:]}", name=name[:120], channel="Facebook" if channel == "facebook" else ("Zalo OA" if channel == "zalo" else "Đặt tour web"), lead_month=f"{datetime.now():%Y-%m}",
                        zalo_uid=external_id if channel == "zalo" else "", created_by="inbox")
            db.add(lead); db.flush()
        c.lead_id = lead.id
    elif name and not c.customer_name: c.customer_name = name[:120]
    return c


STALE_MINUTES = 120   # tin cũ hơn 2 giờ (nạp bù từ Graph) không tính SLA, không để AI trả lời


def inbound(db: Session, channel: str, external_id: str, text: str, page_id: str = "", name: str = "", ext_msg_id: str = "", attachments: list | None = None, at: datetime | None = None) -> Message:
    c = get_or_create(db, channel, external_id, page_id, name)
    # So bằng ĐÚNG chuỗi đã lưu. Cột external_id chỉ 80 ký tự nên lúc ghi bị cắt bằng [:80], còn lúc
    # kiểm trùng lại so với chuỗi ĐẦY ĐỦ – mid của Facebook dài hơn 80 nên không bao giờ khớp, và mỗi
    # lượt kéo bù lại chèn thêm một bản của toàn bộ lịch sử hội thoại. Đây là lý do bảng messages có
    # 117.208 dòng cho khoảng 1.500 tin thật.
    ext = (ext_msg_id or "")[:80]
    if ext and db.execute(select(Message).where(Message.external_id == ext)).scalars().first(): return None
    m = Message(conversation_id=c.id, direction="in", sender="khach", sender_name=c.customer_name, text=(text or "")[:4000], attachments=attachments or [], external_id=ext)
    # Cột thời điểm của tin nhắn tên là `at`, không phải `created_at`. Gán nhầm tên thì Python tạo một
    # thuộc tính rời, không vào CSDL, nên mọi tin lịch sử kéo bù đều mang dấu thời gian "lúc nạp".
    if at: m.at = at
    db.add(m); now = datetime.now(); when = at or now
    if c.last_in_at is None or when >= c.last_in_at:
        c.last_in_at = when
        if now - when <= timedelta(minutes=STALE_MINUTES):
            c.unanswered = True; c.status = "cho_sale"; c.sla_due_at = when + timedelta(minutes=sla_minutes(db, when))
        else:   # tin cũ nạp bù: chỉ lưu lịch sử
            c.unanswered = False; c.sla_due_at = None
    import re
    mph = re.search(r"(?<!\d)(0\d{9}|84\d{9})(?!\d)", (text or "").replace(".", "").replace(" ", "")) or re.search(r"(?<!\d)(0\d{9})(?!\d)", text or "")
    ph = norm_phone(mph.group(1)) if mph else ""
    if len(ph) == 10 and ph.startswith("0") and not c.phone:
        c.phone = ph
        if c.lead_id:
            l = db.get(Lead, c.lead_id)
            if l and not l.phone.startswith("0") and not db.execute(select(Lead).where(Lead.phone == ph, Lead.lead_month == l.lead_month, Lead.channel == l.channel)).scalars().first(): l.phone = ph
    if c.lead_id:
        l = db.get(Lead, c.lead_id); l.last_contact_at = now; l.note = (l.note + "\n" if l.note else "") + f"[{now:%d/%m %H:%M} {channel}] {(text or '')[:200]}"
    db.commit(); db.refresh(m); return m


def _send(db: Session, c: Conversation, text: str, sender: str, sender_name: str) -> Message:
    m = Message(conversation_id=c.id, direction="out", sender=sender, sender_name=sender_name, text=text[:4000]); db.add(m); db.flush()
    try:
        if c.channel == "facebook": r = fb_send(c.external_id, text)
        elif c.channel == "zalo":
            from app.services import zalo as Z; r = Z.send_oa_text(db, c.external_id, text)
        else: r = {"skipped": "kênh web – hiển thị trên widget"}
        m.response = json.dumps(r, ensure_ascii=False)[:1500]
        m.status = "loi" if (r.get("error") not in (None, 0) or r.get("error_name")) else "da_gui"
        if isinstance(r.get("message_id"), str): m.external_id = r["message_id"][:80]
    except Exception as ex:
        m.status, m.response = "loi", str(ex)[:500]
    now = datetime.now(); c.last_out_at = now; c.unanswered = False; c.sla_due_at = None
    c.status = "ai_da_tra_loi" if sender == "ai" else "mo"
    if sender == "ai": c.ai_replies += 1
    db.commit(); db.refresh(m); return m


def reply(db: Session, u: User, c: Conversation, text: str) -> Message:
    if not text.strip(): raise ValueError("Nội dung trống")
    if not c.sales_id: c.sales_id = u.id
    m = _send(db, c, text.strip(), "sale", u.full_name)
    m.ai_review = review_reply(db, c, text.strip()); db.commit()
    R.audit(db, u.username, u.role, "tra_loi_khach", f"conv:{c.id}", after={"kenh": c.channel, "diem": m.ai_review.get("score")})
    return m


# ---------- Facebook Messenger ----------
def fb_verify_signature(body: bytes, sig: str) -> bool:
    if not settings.FB_APP_SECRET: return True
    mac = hmac.new(settings.FB_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + mac, sig or "")


def _graph(method: str, path: str, body: dict | None = None) -> dict:
    if not settings.FB_PAGE_ACCESS_TOKEN: return {"error": -1, "message": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    url = f"{GRAPH}/{path}{'&' if '?' in path else '?'}access_token={urllib.parse.quote(settings.FB_PAGE_ACCESS_TOKEN)}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()).get("error", {"error": e.code})
        except Exception: return {"error": e.code}
    except Exception as ex: return {"error": -1, "message": str(ex)}


FB_FIELDS = "messages,messaging_postbacks,standby,messaging_handovers"


def fb_subscribe(fields: str = FB_FIELDS) -> dict:
    """Đăng ký app nhận webhook cho Page (kể cả standby khi app khác là Người nhận chính) – dùng token Page trên máy chủ, không cần thao tác trên Meta."""
    return _graph("POST", f"me/subscribed_apps?subscribed_fields={urllib.parse.quote(fields)}")


def fb_status() -> dict:
    me = _graph("GET", "me?fields=id,name")
    apps = _graph("GET", "me/subscribed_apps")
    return {"page": me, "subscribed_apps": apps.get("data", apps)}


def fb_take_thread_control(psid: str) -> dict:
    """Khi VTOS là Người nhận phụ (chatbot khác giữ hội thoại): xin quyền hội thoại trước khi trả lời (Handover Protocol)."""
    if not settings.FB_PAGE_ACCESS_TOKEN: return {"error": -1}
    body = json.dumps({"recipient": {"id": psid}, "metadata": "VTOS tra loi"}).encode()
    req = urllib.request.Request(f"{GRAPH}/me/take_thread_control?access_token={urllib.parse.quote(settings.FB_PAGE_ACCESS_TOKEN)}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()).get("error", {"error": e.code})
        except Exception: return {"error": e.code}
    except Exception as ex: return {"error": -1, "message": str(ex)}


def fb_send(psid: str, text: str, _retry: bool = True) -> dict:
    if not settings.FB_PAGE_ACCESS_TOKEN: return {"error": -1, "error_name": "chua_cau_hinh", "message": "Chưa có FB_PAGE_ACCESS_TOKEN"}
    body = json.dumps({"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": text[:2000]}}).encode()
    req = urllib.request.Request(f"{GRAPH}/me/messages?access_token={urllib.parse.quote(settings.FB_PAGE_ACCESS_TOKEN)}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: detail = json.loads(e.read().decode())
        except Exception: detail = {}
        err = (detail or {}).get("error", {}) if isinstance(detail, dict) else {}
        if _retry and (str(err.get("error_subcode") or "") in ("2018300", "2018065") or "thread" in str(err.get("message", "")).lower()):   # không giữ hội thoại (app khác là Người nhận chính) → xin quyền rồi gửi lại
            tc = fb_take_thread_control(psid)
            if tc.get("success"): return fb_send(psid, text, _retry=False)
            detail = {"detail": detail, "take_thread_control": tc}
        return {"error": e.code, "error_name": "http", "detail": detail}


def fb_profile(psid: str) -> str:
    if not settings.FB_PAGE_ACCESS_TOKEN: return ""
    try:
        with urllib.request.urlopen(f"{GRAPH}/{psid}?fields=first_name,last_name&access_token={urllib.parse.quote(settings.FB_PAGE_ACCESS_TOKEN)}", timeout=10) as r:
            j = json.loads(r.read().decode()); return f"{j.get('last_name', '')} {j.get('first_name', '')}".strip()
    except Exception: return ""


def outbound_external(db: Session, channel: str, external_id: str, text: str, page_id: str = "", ext_msg_id: str = "", app_id: str = "", at: datetime | None = None) -> Message | None:
    """Tin do Page gửi qua công cụ khác (chatbot, Fanpage inbox, app khác) – echo/standby: ghi nhận là đã trả lời để SLA không báo sai."""
    c = db.execute(select(Conversation).where(Conversation.channel == channel, Conversation.external_id == external_id)).scalars().first()
    if not c: return None
    ext = (ext_msg_id or "")[:80]      # xem ghi chú ở inbound(): phải so đúng chuỗi đã lưu
    if ext and db.execute(select(Message).where(Message.external_id == ext)).scalars().first(): return None
    who = "chatbot/app khác" if app_id and app_id != str(settings.FB_APP_ID or "") else "Page (ngoài VTOS)"
    m = Message(conversation_id=c.id, direction="out", sender="sale", sender_name=who, text=(text or "")[:4000], status="da_gui", external_id=ext)
    if at: m.at = at
    db.add(m); when = at or datetime.now()
    if c.last_out_at is None or when >= c.last_out_at: c.last_out_at = when
    if c.last_in_at is None or when >= c.last_in_at:   # Page trả lời sau tin khách → đã trả lời
        c.unanswered = False; c.sla_due_at = None
        if c.status == "cho_sale": c.status = "mo"
    db.commit(); db.refresh(m); return m


def fb_webhook(db: Session, payload: dict) -> dict:
    """Sự kiện Messenger: entry[].messaging[] (app là Người nhận chính) hoặc entry[].standby[] (app là Người nhận phụ – nhận bản sao mọi tin khi chatbot khác giữ hội thoại).
    Echo (tin do Page gửi qua app khác) được ghi nhận là đã trả lời."""
    n = 0; echoes = 0
    for entry in payload.get("entry") or []:
        page_id = str(entry.get("id") or "")
        for ev in (entry.get("messaging") or []) + (entry.get("standby") or []):
            msg = ev.get("message") or {}; pb = ev.get("postback") or {}
            sender = str((ev.get("sender") or {}).get("id") or ""); recipient = str((ev.get("recipient") or {}).get("id") or "")
            if msg.get("is_echo") or sender == page_id:
                if outbound_external(db, "facebook", recipient, msg.get("text") or ("[Page gửi tệp]" if msg.get("attachments") else ""), page_id, msg.get("mid") or "", str(msg.get("app_id") or "")): echoes += 1
                continue
            psid = sender
            if not psid: continue
            text = msg.get("text") or pb.get("title") or pb.get("payload") or ""
            atts = [{"type": a.get("type"), "url": (a.get("payload") or {}).get("url")} for a in msg.get("attachments") or []]
            if not text and atts: text = "[khách gửi " + ", ".join(a["type"] or "tệp" for a in atts) + "]"
            if not text: continue
            c = db.execute(select(Conversation).where(Conversation.channel == "facebook", Conversation.external_id == psid)).scalars().first()
            name = c.customer_name if c and c.customer_name else fb_profile(psid)
            if inbound(db, "facebook", psid, text, page_id, name, msg.get("mid") or "", atts): n += 1
    return {"received": n, "echoes": echoes}


# ---------- AI ----------
def knowledge(db: Session, text: str) -> str:
    """Dữ liệu VTOS liên quan câu hỏi: tour sắp khởi hành còn chỗ (30 ngày), sản phẩm khớp từ khóa, chính sách cọc/hủy."""
    today = date.today(); words = [w for w in "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower()).split() if len(w) >= 3]
    tours = list(db.execute(select(Tour).where(Tour.status == "da_duyet", Tour.tour_type.in_(["le_noi_dia", "le_nuoc_ngoai"]), Tour.start_date >= today, Tour.start_date <= today + timedelta(days=45)).order_by(Tour.start_date)).scalars())
    def hit(s: str) -> bool: s = s.lower(); return any(w in s for w in words)
    chosen = [t for t in tours if hit(t.name) or hit(t.code)] or tours[:12]
    lines = []
    for t in chosen[:12]:
        left = max(0, (t.seats_open or t.planned_pax) - R.booked_pax(t))
        lines.append(f"- {t.name} (mã {t.code}): khởi hành {t.start_date:%d/%m/%Y}, {t.days or ''} ngày, giá người lớn {(t.price_per_pax or 0):,.0f} đ" + (f", trẻ em {(t.price_chd or 0):,.0f} đ" if (t.price_chd or 0) else "") + f", còn {left} chỗ")
    prods = [p for p in db.execute(select(Product).where(Product.status == "active")).scalars() if hit(p.name) or hit(p.code)][:5]
    for p in prods: lines.append(f"- Sản phẩm {p.name} (mã {p.code}): {p.length_text or ''}, giá tham khảo {(p.reference_price or 0):,.0f} đ, cọc {p.deposit_pct:.0f}%, đóng tour trước {p.days_to_close} ngày")
    pol = f"Chính sách: cọc mặc định {R.get_param(db, 'coc_mac_dinh_pct'):.0f}% khi giữ chỗ, thanh toán đủ trước khởi hành {int(R.get_param(db, 'han_huy_cho_ngay'))} ngày; hủy sau hạn có thể mất phí, phần đã nộp được bảo lưu {int(R.get_param(db, 'bao_luu_han_ngay'))} ngày cho tour sau."
    return ("Tour sắp khởi hành:\n" + "\n".join(lines) if lines else "Hiện chưa có lịch khởi hành phù hợp trong 45 ngày tới.") + "\n" + pol


def _claude_chi_tiet(prompt: str, max_tokens: int = 400) -> tuple[str | None, int, int, str]:
    """(nội dung, token vào, token ra, lỗi). Trả cả lỗi để nhật ký AI ghi được lần gọi hỏng –
    một lần gọi hỏng vẫn là một lần phần mềm định làm thay người, và im lặng thì không ai biết."""
    if not settings.ANTHROPIC_API_KEY:
        return None, 0, 0, "chưa cấu hình ANTHROPIC_API_KEY"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(model=settings.ANTHROPIC_MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
        u = getattr(msg, "usage", None)
        return ("".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip(),
                int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0), "")
    except Exception as ex:  # noqa
        return None, 0, 0, f"{type(ex).__name__}: {ex}"


def _claude(prompt: str, max_tokens: int = 400) -> str | None:
    return _claude_chi_tiet(prompt, max_tokens)[0]


def history_text(db: Session, c: Conversation, n: int = 12) -> str:
    ms = list(db.execute(select(Message).where(Message.conversation_id == c.id).order_by(desc(Message.at)).limit(n)).scalars())[::-1]
    return "\n".join(f"{'Khách' if m.direction == 'in' else ('AI' if m.sender == 'ai' else 'Tư vấn viên')}: {m.text}" for m in ms)


def draft_reply(db: Session, c: Conversation, *, tu_dong: bool = False, boi: str = "") -> tuple[str, str]:
    """(nội dung, nguồn 'claude'|'quy_tac').

    tu_dong=True là robot tự gửi cho khách (mức 3) – ghi nhật ký ở trạng thái CHỜ HẬU KIỂM.
    tu_dong=False là người bấm xem nháp (mức 2) – nội dung chưa ra khỏi công ty nên không cần hậu kiểm.
    """
    last = db.execute(select(Message).where(Message.conversation_id == c.id, Message.direction == "in").order_by(desc(Message.at))).scalars().first()
    q = last.text if last else ""
    kb = knowledge(db, q)
    prompt = f"{AI_POLICY}\n\nDỮ LIỆU VTOS:\n{kb}\n\nHỘI THOẠI GẦN NHẤT:\n{history_text(db, c)}\n\nViết câu trả lời tiếp theo cho khách."
    out, t_in, t_ra, loi = _claude_chi_tiet(prompt)
    if not out:
        name = c.customer_name or "anh/chị"
        first = kb.split("\n")[1] if "\n" in kb and kb.startswith("Tour") else ""
        out = (f"Vietourist chào {name}! Em đã nhận được tin nhắn, tư vấn viên sẽ trả lời ngay trong ít phút. "
               + (f"Trong lúc chờ, tour gần nhất: {first[2:]}. " if first else "")
               + "Anh/chị cho em xin tên và số điện thoại để em hỗ trợ nhanh hơn nhé?")
        nguon = "quy_tac"
    else:
        nguon = "claude"
    # Cửa thứ hai (11/9/2026): xét NỘI DUNG chứ không chỉ xét vai trò. duoc_tu_gui() đã hỏi "vai trò
    # chủ quản hộp thư có được tự động không" trước khi vào đây – nhưng nó hỏi lúc chưa biết ai sẽ
    # thật sự viết ra câu này. Lời gọi mô hình hỏng thì đoạn trên rơi về câu dựng sẵn, và câu dựng
    # sẵn KHÔNG phải thứ mức 3 cấp phép. Xem ai_quyen.noi_dung_duoc_tu_gui().
    from app.services import ai_quyen as AQ
    tu_gui = tu_dong
    ly_do_ha = ""
    if tu_dong:
        tu_gui, ly_do_ha = AQ.noi_dung_duoc_tu_gui("tin_khach", nguon)

    # Vai trò phải được ghi lại. Bản cũ để trống phuc_vu_vai_tro ở mọi lượt tự gửi, nên nhật ký nói
    # được "AI đã gửi" mà không nói được "nhân danh quyền của ai" – câu thứ hai mới là câu mà người
    # hậu kiểm và kiểm toán cần.
    AL.ghi(db, tac_vu="tin_khach" if tu_gui else "tin_khach_nhap", muc=3 if tu_gui else 2,
           dau_vao=prompt, ket_qua=out, nguon=nguon,
           mo_hinh=settings.ANTHROPIC_MODEL if nguon == "claude" else "",
           ref=f"conv:{c.id}", nguoi=boi,
           vai_tro=AQ.CHU_QUAN_HOP_THU if tu_dong else "",
           trang_thai="cho_hau_kiem" if tu_gui else "khong_can",
           loi=(loi if nguon == "quy_tac" else "") or ly_do_ha)
    return out, nguon


def review_reply(db: Session, c: Conversation, text: str) -> dict:
    """AI chấm câu trả lời của sale: 1–10, cờ rủi ro (giảm giá tự ý, cam kết sai, thiếu thông tin, thái độ)."""
    out = _claude("Bạn là kiểm soát chất lượng tư vấn của Vietourist. Chấm câu trả lời của tư vấn viên dưới đây theo thang 1–10 và liệt kê rủi ro nếu có (tự ý giảm giá/hứa khuyến mãi, cam kết không có trong dữ liệu, thiếu lịch sự, không trả lời đúng câu hỏi, không xin SĐT). "
                  "Trả về JSON duy nhất: {\"score\": số, \"flags\": [\"...\"], \"note\": \"1 câu\"}.\n\nDỮ LIỆU VTOS:\n" + knowledge(db, text) + "\n\nHỘI THOẠI:\n" + history_text(db, c) + "\n\nCÂU TRẢ LỜI CẦN CHẤM:\n" + text, 200)
    if out:
        try:
            j = json.loads(out[out.index("{"): out.rindex("}") + 1])
            kq = {"score": int(j.get("score", 0)), "flags": list(j.get("flags", []))[:5], "note": str(j.get("note", ""))[:200], "by": "claude"}
            # Chấm điểm con người thì phải truy được: điểm này đi vào hồ sơ đánh giá tư vấn viên.
            AL.ghi(db, tac_vu="cham_diem", muc=1, dau_vao=text, ket_qua=json.dumps(kq, ensure_ascii=False),
                   nguon="claude", mo_hinh=settings.ANTHROPIC_MODEL, ref=f"conv:{c.id}")
            return kq
        except Exception: pass
    flags = []; low = text.lower()
    if any(k in low for k in ("giảm giá", "giảm thêm", "bớt", "khuyến mãi riêng", "giá đặc biệt")): flags.append("có thể tự ý giảm giá – cần mã KM được duyệt")
    if any(k in low for k in ("chắc chắn", "đảm bảo", "cam kết")): flags.append("cam kết mạnh – kiểm tra có đúng chính sách")
    kq = {"score": 7 if not flags else 4, "flags": flags, "note": "chấm theo quy tắc (chưa có Claude API)", "by": "quy_tac"}
    AL.ghi(db, tac_vu="cham_diem", muc=1, dau_vao=text, ket_qua=json.dumps(kq, ensure_ascii=False),
           nguon="quy_tac", ref=f"conv:{c.id}")
    return kq


# ---------- robot R12 ----------
def fb_poll(db: Session, limit: int = 25) -> dict:
    """Dự phòng khi webhook không tới: kéo hội thoại Messenger của Page qua Graph (pages_messaging) – tin khách → inbound, tin Page → đã trả lời. Trùng mid → bỏ qua."""
    if not settings.FB_PAGE_ACCESS_TOKEN: return {"skipped": "chưa có token"}
    page_id = str(settings.FB_PAGE_ID or "")
    r = _graph("GET", f"me/conversations?platform=messenger&limit={limit}&fields=updated_time,participants,messages.limit(10){{id,message,from,created_time,attachments}}")
    if "data" not in r: return {"error": r}
    n_in = n_out = 0
    for conv in r["data"]:
        parts = [p for p in (conv.get("participants") or {}).get("data", []) if str(p.get("id")) != page_id]
        if not parts: continue
        psid, name = str(parts[0]["id"]), parts[0].get("name") or ""
        msgs = sorted((conv.get("messages") or {}).get("data", []), key=lambda m: m.get("created_time") or "")
        for m in msgs:
            frm = str((m.get("from") or {}).get("id") or ""); mid = m.get("id") or ""
            text = m.get("message") or ""
            at = None
            try:
                ct = m.get("created_time") or ""
                at = datetime.strptime(ct[:19], "%Y-%m-%dT%H:%M:%S") if ct else None   # Graph trả UTC; máy chủ cũng chạy UTC (datetime.now)
            except ValueError: at = None
            atts = [{"type": a.get("mime_type", "file"), "url": (a.get("image_data") or {}).get("url") or a.get("file_url")} for a in (m.get("attachments") or {}).get("data", [])]
            if not text and atts: text = "[khách gửi tệp]" if frm != page_id else "[Page gửi tệp]"
            if not text: continue
            if frm == page_id:
                if outbound_external(db, "facebook", psid, text, page_id, mid, "poll", at): n_out += 1
            else:
                if inbound(db, "facebook", psid, text, page_id, name, mid, atts, at): n_in += 1
    return {"conversations": len(r["data"]), "new_in": n_in, "new_out": n_out}


def robot_check(db: Session) -> dict:
    """Hội thoại khách nhắn mà sale chưa trả lời quá SLA → AI trả lời thay, cảnh báo sale/TP.

    Từ 07/9/2026 việc AI CÓ ĐƯỢC TỰ GỬI hay không do bảng quyền AI theo vị trí quyết định, không còn do
    một tham số nằm lẫn trong bảng chính sách. Bảng đó kiểm bốn điều: mức của ô "gửi tin cho khách" có
    phải mức 3 không, hạn mức đã khai đủ chưa, đang trong khung giờ cho phép không, và hôm nay đã dùng
    hết số lượt chưa. Không đủ điều kiện thì AI vẫn soạn, nhưng để ở NHÁP – tư vấn viên bấm gửi.

    Tham số ai_tra_loi_bat cũ giữ lại làm công tắc tổng: tắt nó là tắt cả phần soạn nháp.
    """
    from app.services import ai_quyen as AQ
    now = datetime.now(); replied = 0; drafted = 0; alerts = 0
    poll = {}
    try: poll = fb_poll(db)
    except Exception as ex: poll = {"error": str(ex)[:200]}
    on = R.get_param(db, "ai_tra_loi_bat") >= 1
    tu_gui_duoc, ly_do = AQ.duoc_tu_gui(db, now)
    for c in db.execute(select(Conversation).where(Conversation.unanswered == True, Conversation.sla_due_at != None, Conversation.sla_due_at <= now, Conversation.status != "dong")).scalars():
        stale = c.last_in_at is None or now - c.last_in_at > timedelta(minutes=STALE_MINUTES)
        if on and not c.ai_off and c.ai_replies < 3 and not stale:
            if tu_gui_duoc:
                text, src = draft_reply(db, c, tu_dong=True)
                # Cửa thứ hai. Lời gọi mô hình hỏng → draft_reply trả về câu dựng sẵn theo quy tắc,
                # và câu ấy KHÔNG được tự gửi: mức 3 cấp cho câu trả lời của mô hình, ràng bởi
                # loai_noi_dung đã khai, chứ không cấp cho một câu cứng trong mã không biết khách
                # vừa hỏi gì. Bản trước gửi thẳng, nên càng hỏng thì càng gửi.
                duoc, vi_sao = AQ.noi_dung_duoc_tu_gui("tin_khach", src)
                if duoc:
                    _send(db, c, text, "ai", "Trợ lý AI Vietourist"); replied += 1
                    c.summary = (c.summary + " | " if c.summary else "") + f"{now:%d/%m %H:%M} AI trả lời thay ({src})"
                else:
                    drafted += 1
                    c.summary = (c.summary + " | " if c.summary else "") + f"{now:%d/%m %H:%M} AI soạn nháp – không tự gửi ({vi_sao[:80]})"
                # số lượt trong ngày đọc từ nhật ký AI, nên phải tính lại sau mỗi lần gửi: nếu không,
                # một vòng robot có 50 hội thoại sẽ gửi hết 50 dù hạn mức chỉ cho 30.
                tu_gui_duoc, ly_do = AQ.duoc_tu_gui(db, now)
            else:
                # AI vẫn soạn để tư vấn viên có sẵn nội dung, nhưng KHÔNG gửi ra ngoài công ty.
                draft_reply(db, c, tu_dong=False); drafted += 1
                c.summary = (c.summary + " | " if c.summary else "") + f"{now:%d/%m %H:%M} AI soạn nháp ({ly_do})"
        ref = f"conv:{c.id}"
        if not db.execute(select(Alert).where(Alert.kind == "sale_tra_loi_cham", Alert.ref == ref, Alert.resolved == False)).scalars().first():
            db.add(Alert(kind="sale_tra_loi_cham", level="warn", ref=ref, message=f"Khách {c.customer_name or c.external_id} ({c.channel}) chưa được trả lời sau {sla_minutes(db, now)} phút" + (" – AI đã trả lời thay" if on and not c.ai_off and tu_gui_duoc else ""), to_roles="nv_kd,gd_kd,ptgd_mkt,tp_dh")); alerts += 1
    db.commit()
    return {"ai_replied": replied, "ai_soan_nhap": drafted, "new_alerts": alerts,
            "tu_gui_duoc": tu_gui_duoc, "ly_do_khong_tu_gui": ly_do, "fb_poll": poll}


def conv_out(c: Conversation, db: Session | None = None) -> dict:
    s = db.get(User, c.sales_id) if (db and c.sales_id) else None
    last = db.execute(select(Message).where(Message.conversation_id == c.id).order_by(desc(Message.at))).scalars().first() if db else None
    return {"id": c.id, "channel": c.channel, "external_id": c.external_id, "customer_name": c.customer_name, "phone": c.phone, "lead_id": c.lead_id, "sales_id": c.sales_id, "sales_name": s.full_name if s else "",
            "status": c.status, "unanswered": c.unanswered, "last_in_at": c.last_in_at, "last_out_at": c.last_out_at, "sla_due_at": c.sla_due_at, "overdue": bool(c.unanswered and c.sla_due_at and datetime.now() > c.sla_due_at),
            "ai_replies": c.ai_replies, "ai_off": c.ai_off, "summary": c.summary, "last_text": last.text[:120] if last else "", "last_sender": last.sender if last else "", "updated_at": c.updated_at}


def msg_out(m: Message) -> dict:
    return {"id": m.id, "direction": m.direction, "sender": m.sender, "sender_name": m.sender_name, "text": m.text, "attachments": m.attachments, "status": m.status, "response": m.response[:200], "ai_review": m.ai_review, "at": m.at}


# ---------- dọn tin nhắn trùng ----------
def tin_trung(db: Session, xoa: bool = False) -> dict:
    """Đếm và (khi được yêu cầu) xoá tin nhắn bị chèn lặp bởi lỗi kiểm trùng của vòng kéo bù Facebook.

    Giữ lại BẢN ĐẦU TIÊN của mỗi nhóm (id nhỏ nhất) – bản đó là bản có mặt sớm nhất, và mọi bản sau chỉ
    là chính nó được chèn lại. Nhóm theo hội thoại + chiều + nội dung: không dùng external_id làm khoá
    nhóm được, vì chính chỗ đó là nơi hỏng.

    Mặc định CHỈ ĐẾM. Muốn xoá phải gọi lại với xoa=True – xoá tin của khách là việc không lùi lại được.
    """
    from sqlalchemy import func as _f, delete as _del
    q = (select(Message.conversation_id, Message.direction, Message.text,
                _f.count().label("n"), _f.min(Message.id).label("giu"))
         .group_by(Message.conversation_id, Message.direction, Message.text)
         .having(_f.count() > 1))
    nhom = db.execute(q).all()
    thua = sum(int(r.n) - 1 for r in nhom)
    tong = db.execute(select(_f.count()).select_from(Message)).scalar() or 0
    kq = {"tong_tin": int(tong), "so_nhom_trung": len(nhom), "so_ban_thua": thua,
          "con_lai_sau_khi_don": int(tong) - thua, "da_xoa": 0,
          "message": f"{thua:,} bản thừa trên tổng {tong:,} tin – còn lại {int(tong)-thua:,} tin thật"}
    if not xoa: return kq
    n = 0
    for r in nhom:      # xoá theo từng nhóm: một câu lệnh cho mỗi nhóm, không nạp tin vào bộ nhớ
        res = db.execute(_del(Message).where(Message.conversation_id == r.conversation_id,
                                             Message.direction == r.direction,
                                             Message.text == r.text, Message.id != r.giu))
        n += res.rowcount or 0
    db.commit()
    kq["da_xoa"] = n; kq["message"] = f"Đã xoá {n:,} bản trùng, giữ lại bản đầu tiên của mỗi nhóm"
    return kq
